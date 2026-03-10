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


def to_decimal_interval(series_float: pd.Series) -> np.ndarray:
    x = series_float.to_numpy(dtype=float)
    ax = np.nan_to_num(np.abs(x), nan=0.0)
    if ax.max() > 1.0 or np.median(ax) > 0.2:
        x = x / 100.0
    return x


def calc_period_return(returns_decimal: np.ndarray) -> float:
    """Berechnet die kumulierte Rendite einer Periode aus täglichen Renditen."""
    return float(np.prod(1.0 + returns_decimal) - 1.0)


def calc_period_return_after_fee(returns_decimal: np.ndarray, fee_pa_decimal: float) -> float:
    """Kumulierte Rendite nach Kosten."""
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    return float(np.prod(1.0 + (returns_decimal - e)) - 1.0)


# -----------------------------
# Performance-Blöcke berechnen
# -----------------------------
def compute_bar_data(df: pd.DataFrame, fee_dec: float, mode: str,
                     custom_start: dt.date = None, custom_end: dt.date = None) -> pd.DataFrame:
    """
    mode: 'Kalenderjahre' | 'Quartale' | 'Benutzerdefiniert'
    Gibt DataFrame mit Spalten: label, ret_port_after, ret_bm
    """
    rows = []

    if mode == "Kalenderjahre":
        years = sorted(df.index.year.unique())
        for y in years:
            mask = df.index.year == y
            sub = df.loc[mask]
            if len(sub) == 0:
                continue
            rp = sub["ret_port"].fillna(0.0).to_numpy(dtype=float)
            rb = sub["ret_bm"].fillna(0.0).to_numpy(dtype=float)
            rows.append({
                "label": str(y),
                "ret_port_after": calc_period_return_after_fee(rp, fee_dec) * 100,
                "ret_bm": calc_period_return(rb) * 100 if sub["ret_bm"].notna().any() else None,
            })

    elif mode == "Quartale":
        df2 = df.copy()
        df2["year"] = df2.index.year
        df2["quarter"] = df2.index.quarter
        groups = df2.groupby(["year", "quarter"])
        for (y, q), sub in groups:
            if len(sub) == 0:
                continue
            rp = sub["ret_port"].fillna(0.0).to_numpy(dtype=float)
            rb = sub["ret_bm"].fillna(0.0).to_numpy(dtype=float)
            rows.append({
                "label": f"{y} Q{q}",
                "ret_port_after": calc_period_return_after_fee(rp, fee_dec) * 100,
                "ret_bm": calc_period_return(rb) * 100 if sub["ret_bm"].notna().any() else None,
            })

    elif mode == "Benutzerdefiniert":
        if custom_start is None or custom_end is None:
            return pd.DataFrame(columns=["label", "ret_port_after", "ret_bm"])
        mask = (df.index.date >= custom_start) & (df.index.date <= custom_end)
        sub = df.loc[mask]
        if len(sub) == 0:
            return pd.DataFrame(columns=["label", "ret_port_after", "ret_bm"])
        rp = sub["ret_port"].fillna(0.0).to_numpy(dtype=float)
        rb = sub["ret_bm"].fillna(0.0).to_numpy(dtype=float)
        rows.append({
            "label": f"{custom_start.strftime('%d.%m.%Y')} – {custom_end.strftime('%d.%m.%Y')}",
            "ret_port_after": calc_period_return_after_fee(rp, fee_dec) * 100,
            "ret_bm": calc_period_return(rb) * 100 if sub["ret_bm"].notna().any() else None,
        })

    return pd.DataFrame(rows)


def build_bar_chart(bar_df: pd.DataFrame, title: str) -> go.Figure:
    """Erstellt die gruppierte Balken-Grafik im Stil des Referenzbildes."""
    GOLD = "#A07840"
    LIGHTBLUE = "#AED6F1"

    fig = go.Figure()

    # Portfolio nach Kosten
    colors_port = [GOLD if v >= 0 else GOLD for v in bar_df["ret_port_after"]]
    fig.add_trace(go.Bar(
        name="Musterdepot (nach Kosten)",
        x=bar_df["label"],
        y=bar_df["ret_port_after"],
        marker_color=GOLD,
        text=[f"{v:.2f}%" for v in bar_df["ret_port_after"]],
        textposition="outside",
        textfont=dict(size=11, color="#333333"),
    ))

    # Benchmark
    if "ret_bm" in bar_df.columns and bar_df["ret_bm"].notna().any():
        fig.add_trace(go.Bar(
            name="Benchmark",
            x=bar_df["label"],
            y=bar_df["ret_bm"].fillna(0),
            marker_color=LIGHTBLUE,
            text=[f"{v:.2f}%" if pd.notna(v) else "" for v in bar_df["ret_bm"]],
            textposition="outside",
            textfont=dict(size=11, color="#333333"),
        ))

    # Nulllinie
    fig.add_hline(y=0, line_color="#555555", line_width=1)

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="white"), x=0, xanchor="left"),
        paper_bgcolor="#1E3A5F",
        plot_bgcolor="#1E3A5F",
        barmode="group",
        bargap=0.25,
        bargroupgap=0.05,
        height=420,
        xaxis=dict(
            tickfont=dict(color="white", size=12),
            showgrid=False,
            zeroline=False,
            linecolor="#555555",
        ),
        yaxis=dict(
            tickformat=".2f",
            ticksuffix="%",
            tickfont=dict(color="white", size=11),
            gridcolor="#2E4A6F",
            zeroline=False,
        ),
        legend=dict(
            font=dict(color="white", size=11),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            y=-0.15,
        ),
        margin=dict(t=50, b=60, l=60, r=20),
    )
    return fig


# -----------------------------
# Data loading
# -----------------------------
@st.cache_data(show_spinner=False)
def load_mapping(mapping_path: str) -> pd.DataFrame:
    m = pd.read_excel(mapping_path).round(6)
    return m


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
    vv = pd.read_csv(
        path,
        comment="#",
        encoding="ISO-8859-1",
        delimiter=";",
        decimal=",",
        thousands=".",
        dtype=str
    )
    return vv


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
            vv["Performance [%] (Intervall)"].astype(str).str.replace(",", ".").astype(float)
        )
        ret_port = to_decimal_interval(vv.loc[1:, "Performance [%] (Intervall)"])
        ret_bm = None
        if "Benchmark Performance [%] (Intervall)" in vv.columns:
            vv["Benchmark Performance [%] (Intervall)"] = (
                vv["Benchmark Performance [%] (Intervall)"].astype(str).str.replace(",", ".").astype(float)
            )
            ret_bm = to_decimal_interval(vv.loc[1:, "Benchmark Performance [%] (Intervall)"])
        fee_default = None
        try:
            fee_default = float(mapping.loc[mapping["Inhaber"] == portfolio, "Honorarsatz Standard"].values[0])
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


# ---------------------------------------------------------------------------
# LOGIN AUTHENTICATION
# ---------------------------------------------------------------------------
def check_login():
    USERS = st.secrets["passwords"]
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    def verify_password():
        username = st.session_state.get("username_input", "")
        password = st.session_state.get("password_input", "")
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            return True
        return False

    if not st.session_state.logged_in:
        st.title("Ausschüttungs-VV Rechner | Fürst Fugger Privatbank")
        st.write("Bitte melden Sie sich an, um fortzufahren.")
        st.text_input("Benutzername", key="username_input")
        st.text_input("Passwort", type="password", key="password_input")
        if st.button("Einloggen"):
            if verify_password():
                st.success("Erfolgreich eingeloggt!")
                st.rerun()
            else:
                st.error("❌ Falscher Benutzername oder Passwort")
        return False
    else:
        with st.sidebar:
            st.write(f"👤 Angemeldet als: **{st.session_state.username}**")
            if st.button("Ausloggen"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.rerun()
        return True


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Performance Index (100) – Streamlit", layout="wide")
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
        st.error(f"Keine Dateien gefunden für Tag {date_tag}. Pattern: *_{date_tag}_*.CSV")
        st.stop()

    data = build_portfolio_timeseries(files, mapping)

    portfolios = sorted(list(data.keys()))
    portfolio_sel = st.selectbox("Portfolio auswählen", portfolios)

    show_vorkosten = st.checkbox("Vor Kosten anzeigen", value=True)
    show_benchmark = st.checkbox("Benchmark anzeigen", value=True)

    fee_default_dec = float(data[portfolio_sel]["fee_default"].iloc[0]) if len(data[portfolio_sel]) else 0.0
    fee_default_pct = fee_default_dec * 100.0

    fee_pct = st.number_input(
        "Kosten p.a. (%)",
        min_value=0.0,
        max_value=20.0,
        value=float(round(fee_default_pct, 4)),
        step=0.05,
        help="Eingabe in Prozent p.a. (z.B. 1,55). Intern wird /100 gerechnet."
    )
    fee_dec = fee_pct / 100.0

df = data[portfolio_sel].copy()

# Zeitraum-Filter
min_d, max_d = df.index.min().date(), df.index.max().date()
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    start_date = st.date_input("Start", value=min_d, min_value=min_d, max_value=max_d)
with col2:
    end_date = st.date_input("Ende", value=max_d, min_value=min_d, max_value=max_d)

if start_date > end_date:
    st.error("Startdatum darf nicht nach dem Enddatum liegen.")
    st.stop()

df = df.loc[(df.index.date >= start_date) & (df.index.date <= end_date)].copy()

# --- Liniengrafik (Index 100) ---
ret_port = df["ret_port"].to_numpy(dtype=float)
idx_after = make_index_after_fee(ret_port, fee_pa_decimal=fee_dec, startwert=100.0)
idx_before = make_index_from_returns(ret_port, startwert=100.0)
x_dates = [df.index.min() - pd.Timedelta(days=1)] + list(df.index)

fig = go.Figure()
fig.add_trace(go.Scatter(x=x_dates, y=idx_after, mode="lines", name="Portfolio – nach Kosten"))
if show_vorkosten:
    fig.add_trace(go.Scatter(x=x_dates, y=idx_before, mode="lines", name="Portfolio – vor Kosten"))
if show_benchmark and df["ret_bm"].notna().any():
    ret_bm = df["ret_bm"].fillna(0.0).to_numpy(dtype=float)
    idx_bm = make_index_from_returns(ret_bm, startwert=100.0)
    fig.add_trace(go.Scatter(x=x_dates, y=idx_bm, mode="lines", name="Benchmark"))

fig.update_layout(
    height=550,
    xaxis_title="Datum",
    yaxis_title="Index (Start 100)",
    legend_title_text="Reihen",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# =============================================================
# BALKEN-GRAFIK: Performance p.a. im Benchmarkvergleich
# =============================================================
st.markdown("---")
st.subheader("Performance im Benchmarkvergleich (blockweise)")

bar_col1, bar_col2 = st.columns([1, 3])

with bar_col1:
    bar_mode = st.radio(
        "Zeitraum-Modus",
        options=["Kalenderjahre", "Quartale", "Benutzerdefiniert"],
        index=0,
    )

    custom_start_bar = None
    custom_end_bar = None
    if bar_mode == "Benutzerdefiniert":
        custom_start_bar = st.date_input(
            "Von", value=start_date, min_value=min_d, max_value=max_d, key="bar_start"
        )
        custom_end_bar = st.date_input(
            "Bis", value=end_date, min_value=min_d, max_value=max_d, key="bar_end"
        )

with bar_col2:
    bar_df = compute_bar_data(
        df,
        fee_dec=fee_dec,
        mode=bar_mode,
        custom_start=custom_start_bar,
        custom_end=custom_end_bar,
    )

    if bar_df.empty:
        st.info("Keine Daten für den gewählten Zeitraum.")
    else:
        title_map = {
            "Kalenderjahre": "PERFORMANCE P.A. (NACH KOSTEN) IM BENCHMARKVERGLEICH – KALENDERJAHRE",
            "Quartale": "PERFORMANCE (NACH KOSTEN) IM BENCHMARKVERGLEICH – QUARTALE",
            "Benutzerdefiniert": "PERFORMANCE (NACH KOSTEN) IM BENCHMARKVERGLEICH – BENUTZERDEFINIERT",
        }
        bar_fig = build_bar_chart(bar_df, title=title_map[bar_mode])
        st.plotly_chart(bar_fig, use_container_width=True)

        # Tabelle darunter (optional)
        with st.expander("Tabelle anzeigen"):
            display_df = bar_df.copy()
            display_df["ret_port_after"] = display_df["ret_port_after"].map(lambda x: f"{x:.2f}%")
            if "ret_bm" in display_df.columns:
                display_df["ret_bm"] = display_df["ret_bm"].map(
                    lambda x: f"{x:.2f}%" if pd.notna(x) else "–"
                )
            display_df.columns = ["Zeitraum", "Portfolio nach Kosten", "Benchmark"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

with st.expander("Details / Debug"):
    st.write("Gefundene Dateien:", len(files))
    st.write("Kosten p.a. (dezimal):", fee_dec)
    st.dataframe(df.head(10))
