# streamlit_app.py
import os
import glob
import datetime as dt
from datetime import timedelta

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# -----------------------------
# Helpers: Index-Berechnung
# -----------------------------
def annual_fee_to_daily_drag(fee_pa_decimal: float) -> float:
    return (1.0 + fee_pa_decimal) ** (1 / 365) - 1


def make_index_from_returns(d_returns_decimal: np.ndarray, startwert: float = 100.0) -> np.ndarray:
    idx = np.empty(len(d_returns_decimal) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(d_returns_decimal, start=1):
        idx[i] = idx[i - 1] * (1.0 + d)
    return idx


def make_index_after_fee(d_returns_decimal: np.ndarray, fee_pa_decimal: float, startwert: float = 100.0) -> np.ndarray:
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    idx = np.empty(len(d_returns_decimal) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(d_returns_decimal, start=1):
        idx[i] = idx[i - 1] * (1.0 + (d - e))
    return idx


def drawdown_from_index(idx: np.ndarray) -> np.ndarray:
    peak = np.maximum.accumulate(idx)
    return (idx / peak) - 1.0


def to_decimal_interval(series_float: pd.Series) -> np.ndarray:
    x = series_float.to_numpy(dtype=float)
    ax = np.nan_to_num(np.abs(x), nan=0.0)

    if ax.max() > 1.0 or np.median(ax) > 0.2:
        x = x / 100.0

    return x


# -----------------------------
# Data loading
# -----------------------------
@st.cache_data(show_spinner=False)
def load_mapping(mapping_path: str) -> pd.DataFrame:
    return pd.read_excel(mapping_path).round(6)


@st.cache_data(show_spinner=True)
def load_all_csvs(data_folder: str, date_tag: str, exclude_substrings: list[str]) -> list[str]:
    pattern = os.path.join(data_folder, f"*_{date_tag}_*.CSV")
    files = glob.glob(pattern)
    files = [
        p for p in files
        if not any(sub in os.path.basename(p) for sub in exclude_substrings)
    ]
    return files


def read_one_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(
        path,
        comment="#",
        encoding="ISO-8859-1",
        delimiter=";",
        decimal=",",
        thousands=".",
        dtype=str
    )


def parse_dates_col(vv: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(vv["Datum"], format="%d.%m.%Y", errors="raise")


@st.cache_data(show_spinner=True)
def build_portfolio_timeseries(files: list[str], mapping: pd.DataFrame) -> dict:

    out = {}

    for path in files:
        vv = read_one_csv(path)
        portfolio = vv.loc[0, "Portfolio Name"]
        dates = parse_dates_col(vv)

        vv["Performance [%] (Intervall)"] = (
            vv["Performance [%] (Intervall)"]
            .astype(str).str.replace(",", ".").astype(float)
        )

        ret_port = to_decimal_interval(vv.loc[1:, "Performance [%] (Intervall)"])

        ret_bm = None
        if "Benchmark Performance [%] (Intervall)" in vv.columns:
            vv["Benchmark Performance [%] (Intervall)"] = (
                vv["Benchmark Performance [%] (Intervall)"]
                .astype(str).str.replace(",", ".").astype(float)
            )
            ret_bm = to_decimal_interval(vv.loc[1:, "Benchmark Performance [%] (Intervall)"])

        try:
            fee_default = float(
                mapping.loc[mapping["Inhaber"] == portfolio, "Honorarsatz Standard"].values[0]
            )
        except Exception:
            fee_default = 0.0

        idx = dates.iloc[1:].reset_index(drop=True)
        df = pd.DataFrame(index=idx)
        df.index.name = "Datum"

        df["ret_port"] = ret_port

        if ret_bm is not None and len(ret_bm) == len(df):
            df["ret_bm"] = ret_bm
        else:
            df["ret_bm"] = np.nan

        df["fee_default"] = fee_default

        out[portfolio] = df.sort_index()

    return out


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Performance Index (100)", layout="wide")
st.title("Performance Index (Start 100) – nach Kosten / vor Kosten / Benchmark")

MAPPING_PATH = r"Mapping_Honorarsatz.xlsx"
DATA_FOLDER = r"Daten"
exclude_substrings = ["Stiftung"]

heute_tag = dt.date.today().strftime("%y%m%d")

with st.sidebar:

    st.header("Einstellungen")

    date_tag = st.text_input("Date-Tag (yyMMdd)", value=heute_tag)

    mapping = load_mapping(MAPPING_PATH)
    files = load_all_csvs(DATA_FOLDER, date_tag, exclude_substrings)

    if len(files) == 0:
        st.error(f"Keine Dateien gefunden für Tag {date_tag}")
        st.stop()

    data = build_portfolio_timeseries(files, mapping)

    portfolios = sorted(list(data.keys()))

    portfolio_sel = st.selectbox("Portfolio auswählen", portfolios)

    show_compare = st.checkbox("Vergleichsportfolio anzeigen", value=False)

    portfolio_sel2 = None
    if show_compare:
        portfolio_sel2 = st.selectbox("Vergleichsportfolio auswählen", portfolios)

    show_vorkosten = st.checkbox("Vor Kosten anzeigen", value=True)
    show_benchmark = st.checkbox("Benchmark anzeigen", value=True)
    show_drawdown = st.checkbox("Drawdown (nach Kosten) anzeigen", value=False)

    fee_default_dec = float(data[portfolio_sel]["fee_default"].iloc[0])
    fee_default_pct = fee_default_dec * 100.0

    fee_pct = st.number_input(
        "Kosten p.a. (%)",
        min_value=0.0,
        max_value=20.0,
        value=float(round(fee_default_pct, 4)),
        step=0.05,
    )

    fee_dec = fee_pct / 100.0


# -----------------------------
# Daten vorbereiten
# -----------------------------
df1 = data[portfolio_sel].copy()

min_d, max_d = df1.index.min().date(), df1.index.max().date()

col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input("Start", value=min_d, min_value=min_d, max_value=max_d)

with col2:
    end_date = st.date_input("Ende", value=max_d, min_value=min_d, max_value=max_d)

if start_date > end_date:
    st.error("Startdatum darf nicht nach Enddatum liegen.")
    st.stop()

df1 = df1.loc[(df1.index.date >= start_date) & (df1.index.date <= end_date)]

df2 = None

if show_compare and portfolio_sel2:

    df2_raw = data[portfolio_sel2].copy()
    df2_raw = df2_raw.loc[(df2_raw.index.date >= start_date) & (df2_raw.index.date <= end_date)]

    joined = (
        df1[["ret_port", "ret_bm"]]
        .rename(columns={"ret_port": "ret_port_1", "ret_bm": "ret_bm_1"})
        .join(
            df2_raw[["ret_port"]].rename(columns={"ret_port": "ret_port_2"}),
            how="inner"
        )
    )

    df1 = joined[["ret_port_1", "ret_bm_1"]].rename(
        columns={"ret_port_1": "ret_port", "ret_bm_1": "ret_bm"}
    )

    df2 = joined[["ret_port_2"]].rename(
        columns={"ret_port_2": "ret_port"}
    )


# -----------------------------
# Indexberechnung
# -----------------------------
ret1 = df1["ret_port"].to_numpy(dtype=float)
idx_after_1 = make_index_after_fee(ret1, fee_dec)
idx_before_1 = make_index_from_returns(ret1)

idx_after_2 = None
idx_before_2 = None

if df2 is not None:
    ret2 = df2["ret_port"].to_numpy(dtype=float)
    idx_after_2 = make_index_after_fee(ret2, fee_dec)
    idx_before_2 = make_index_from_returns(ret2)

x_dates = [df1.index.min() - pd.Timedelta(days=1)] + list(df1.index)


# -----------------------------
# Index Chart
# -----------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(x=x_dates, y=idx_after_1,
                         mode="lines",
                         name=f"{portfolio_sel} – nach Kosten"))

if idx_after_2 is not None:
    fig.add_trace(go.Scatter(x=x_dates, y=idx_after_2,
                             mode="lines",
                             name=f"{portfolio_sel2} – nach Kosten"))

if show_vorkosten:
    fig.add_trace(go.Scatter(x=x_dates, y=idx_before_1,
                             mode="lines",
                             name=f"{portfolio_sel} – vor Kosten"))
    if idx_before_2 is not None:
        fig.add_trace(go.Scatter(x=x_dates, y=idx_before_2,
                                 mode="lines",
                                 name=f"{portfolio_sel2} – vor Kosten"))

if show_benchmark and df1["ret_bm"].notna().any():
    ret_bm = df1["ret_bm"].fillna(0.0).to_numpy(dtype=float)
    idx_bm = make_index_from_returns(ret_bm)
    fig.add_trace(go.Scatter(x=x_dates, y=idx_bm,
                             mode="lines",
                             name="Benchmark"))

fig.update_layout(
    height=550,
    xaxis_title="Datum",
    yaxis_title="Index (Start 100)",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# Drawdown Chart (optional)
# -----------------------------
if show_drawdown:

    fig_dd = go.Figure()

    dd1 = drawdown_from_index(idx_after_1)
    fig_dd.add_trace(go.Scatter(x=x_dates, y=dd1,
                                mode="lines",
                                name=f"{portfolio_sel} – Drawdown"))

    if idx_after_2 is not None:
        dd2 = drawdown_from_index(idx_after_2)
        fig_dd.add_trace(go.Scatter(x=x_dates, y=dd2,
                                    mode="lines",
                                    name=f"{portfolio_sel2} – Drawdown"))

    fig_dd.update_layout(
        height=350,
        xaxis_title="Datum",
        yaxis_title="Drawdown",
        hovermode="x unified"
    )

    st.plotly_chart(fig_dd, use_container_width=True)


# -----------------------------
# Debug
# -----------------------------
with st.expander("Details / Debug"):
    st.write("Gefundene Dateien:", len(files))
    st.write("Kosten p.a. (dezimal):", fee_dec)
    st.write("Zeitraum:", start_date, "bis", end_date)
    st.write("Rows Portfolio 1:", len(df1))
    if df2 is not None:
        st.write("Rows Portfolio 2:", len(df2))
    st.dataframe(df1.head())
