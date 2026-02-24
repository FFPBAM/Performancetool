# streamlit_app.py
import os
import glob
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# LOGIN AUTHENTICATION
# ---------------------------------------------------------------------------
def check_login() -> bool:
    """
    Login-Authentifizierung mit Streamlit Secrets.
    Erwartet in .streamlit/secrets.toml:
    [passwords]
    user1 = "pass1"
    user2 = "pass2"
    """
    USERS = st.secrets["passwords"]

    # Session State initialisieren
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    def verify_password() -> bool:
        username = st.session_state.get("username_input", "").strip()
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

    # Logout-Button in der Sidebar
    with st.sidebar:
        st.write(f"👤 Angemeldet als: **{st.session_state.username}**")
        if st.button("Ausloggen"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    return True


# -----------------------------
# Helpers: Index / Gebühren / Drawdown
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
    """
    Robust: Wenn Werte eher wie Prozentpunkte aussehen (z.B. 0.30 für 0,30%),
    dann teilen wir durch 100. Wenn sie schon dezimal sind (0.003), lassen wir sie.
    """
    x = series_float.to_numpy(dtype=float)
    ax = np.nan_to_num(np.abs(x), nan=0.0)

    if ax.max() > 1.0 or np.median(ax) > 0.2:
        x = x / 100.0
    return x


# -----------------------------
# Helpers: Performance-Tabelle (rollierend)
# -----------------------------
def _asof_value(series: pd.Series, target_ts: pd.Timestamp):
    s = series.dropna()
    if s.empty:
        return None
    if target_ts < s.index.min():
        return None
    return float(s.asof(target_ts))


def period_return(series_idx: pd.Series, start_ts: pd.Timestamp, end_ts: pd.Timestamp):
    v_end = _asof_value(series_idx, end_ts)
    v_start = _asof_value(series_idx, start_ts)
    if v_end is None or v_start is None or v_start == 0:
        return None
    return (v_end / v_start) - 1.0


def build_rolling_table(
    idx_before_1: pd.Series,
    idx_after_1: pd.Series,
    label_1: str,
    idx_before_2: pd.Series | None = None,
    idx_after_2: pd.Series | None = None,
    label_2: str | None = None,
    since_label: str | None = None
) -> pd.DataFrame:
    end_ts = idx_after_1.dropna().index.max()
    if pd.isna(end_ts):
        return pd.DataFrame()

    year_start = pd.Timestamp(end_ts.year, 1, 1)
    first_ts = idx_after_1.dropna().index.min()

    periods = [
        ("ytd", year_start),
        ("1 Jahre", end_ts - pd.DateOffset(years=1)),
        ("3 Jahre", end_ts - pd.DateOffset(years=3)),
        ("5 Jahre", end_ts - pd.DateOffset(years=5)),
        ("10 Jahre", end_ts - pd.DateOffset(years=10)),
        (since_label or f"Wertentwicklung seit: {first_ts.strftime('%d.%m.%Y')}", first_ts),
    ]

    rows = []
    for pname, start_ts in periods:
        r = {"Wertentwicklung rollierend": pname}

        r[(label_1, "Performance vor Kosten")] = period_return(idx_before_1, start_ts, end_ts)
        r[(label_1, "Performance nach Kosten")] = period_return(idx_after_1, start_ts, end_ts)

        if idx_before_2 is not None and idx_after_2 is not None and label_2:
            r[(label_2, "Performance vor Kosten")] = period_return(idx_before_2, start_ts, end_ts)
            r[(label_2, "Performance nach Kosten")] = period_return(idx_after_2, start_ts, end_ts)

        rows.append(r)

    df = pd.DataFrame(rows)
    base_cols = ["Wertentwicklung rollierend"]
    multi_cols = [c for c in df.columns if c not in base_cols]
    df = df[base_cols + multi_cols]

    def fmt(x):
        if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
            return "-"
        return f"{x * 100:.3f}%".replace(".", ",")

    df_show = df.copy()
    for c in multi_cols:
        df_show[c] = df_show[c].apply(fmt)

    return df_show


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
    files = [p for p in files if not any(sub in os.path.basename(p) for sub in exclude_substrings)]
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


def extract_benchmark_name(vv: pd.DataFrame) -> str:
    candidates = ["Benchmark Name", "Benchmark", "Benchmarkname", "Benchmark Name ", "Benchmark-Bezeichnung"]
    for c in candidates:
        if c in vv.columns:
            val = vv.loc[0, c]
            if pd.notna(val) and str(val).strip():
                return str(val).strip()
    return "Benchmark"


@st.cache_data(show_spinner=True)
def build_portfolio_timeseries(files: list[str], mapping: pd.DataFrame) -> dict:
    out = {}

    for path in files:
        vv = read_one_csv(path)

        portfolio = vv.loc[0, "Portfolio Name"]
        bench_name = extract_benchmark_name(vv)

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
        df = df.sort_index()
        df.attrs["benchmark_name"] = bench_name

        out[portfolio] = df

    return out


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Performance Index (100)", layout="wide")

# ✅ Login MUSS vor der restlichen App-Logik passieren
if not check_login():
    st.stop()

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

    show_compare = st.checkbox("Vergleichsportfolio anzeigen", value=False)
    portfolio_sel2 = None
    if show_compare:
        portfolio_sel2 = st.selectbox("Vergleichsportfolio auswählen", portfolios)

    show_vorkosten = st.checkbox("Vor Kosten anzeigen", value=True)
    show_benchmark = st.checkbox("Benchmark anzeigen", value=True)
    show_drawdown = st.checkbox("Drawdown (nach Kosten) anzeigen", value=False)
    show_table = st.checkbox("Tabelle: Wertentwicklung rollierend anzeigen", value=True)

    # Kosten Portfolio 1
    fee_default_dec_1 = float(data[portfolio_sel]["fee_default"].iloc[0]) if len(data[portfolio_sel]) else 0.0
    fee_default_pct_1 = fee_default_dec_1 * 100.0
    fee_pct_1 = st.number_input(
        f"Kosten p.a. (%) – {portfolio_sel}",
        min_value=0.0,
        max_value=20.0,
        value=float(round(fee_default_pct_1, 4)),
        step=0.05,
        help="Eingabe in Prozent p.a. (z.B. 1,55). Intern wird /100 gerechnet."
    )
    fee_dec_1 = fee_pct_1 / 100.0

    # Kosten Portfolio 2 (nur wenn Vergleich)
    fee_dec_2 = None
    fee_pct_2 = None
    if show_compare and portfolio_sel2:
        fee_default_dec_2 = float(data[portfolio_sel2]["fee_default"].iloc[0]) if len(data[portfolio_sel2]) else 0.0
        fee_default_pct_2 = fee_default_dec_2 * 100.0
        fee_pct_2 = st.number_input(
            f"Kosten p.a. (%) – {portfolio_sel2}",
            min_value=0.0,
            max_value=20.0,
            value=float(round(fee_default_pct_2, 4)),
            step=0.05,
            help="Eingabe in Prozent p.a. (z.B. 1,55). Intern wird /100 gerechnet."
        )
        fee_dec_2 = fee_pct_2 / 100.0


# -----------------------------
# Daten vorbereiten / Zeitraum
# -----------------------------
df1 = data[portfolio_sel].copy()

min_d, max_d = df1.index.min().date(), df1.index.max().date()
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start", value=min_d, min_value=min_d, max_value=max_d)
with col2:
    end_date = st.date_input("Ende", value=max_d, min_value=min_d, max_value=max_d)

if start_date > end_date:
    st.error("Startdatum darf nicht nach dem Enddatum liegen.")
    st.stop()

df1 = df1.loc[(df1.index.date >= start_date) & (df1.index.date <= end_date)].copy()

df2 = None
if show_compare and portfolio_sel2:
    df2_raw = data[portfolio_sel2].copy()
    df2_raw = df2_raw.loc[(df2_raw.index.date >= start_date) & (df2_raw.index.date <= end_date)].copy()

    joined = (
        df1[["ret_port", "ret_bm"]]
        .rename(columns={"ret_port": "ret_port_1", "ret_bm": "ret_bm_1"})
        .join(
            df2_raw[["ret_port", "ret_bm"]].rename(columns={"ret_port": "ret_port_2", "ret_bm": "ret_bm_2"}),
            how="inner"
        )
    )

    if joined.empty:
        st.error("Kein gemeinsamer Datumsbereich zwischen Portfolio und Vergleichsportfolio im gewählten Zeitraum.")
        st.stop()

    df1 = joined[["ret_port_1", "ret_bm_1"]].rename(columns={"ret_port_1": "ret_port", "ret_bm_1": "ret_bm"})
    df2 = joined[["ret_port_2", "ret_bm_2"]].rename(columns={"ret_port_2": "ret_port", "ret_bm_2": "ret_bm"})


# -----------------------------
# Indexberechnung (je Portfolio eigener Kostensatz)
# -----------------------------
ret1 = df1["ret_port"].to_numpy(dtype=float)
idx_after_1 = make_index_after_fee(ret1, fee_dec_1, startwert=100.0)
idx_before_1 = make_index_from_returns(ret1, startwert=100.0)

idx_after_2 = None
idx_before_2 = None
if df2 is not None:
    ret2 = df2["ret_port"].to_numpy(dtype=float)
    idx_after_2 = make_index_after_fee(ret2, float(fee_dec_2), startwert=100.0)
    idx_before_2 = make_index_from_returns(ret2, startwert=100.0)

x_dates = [df1.index.min() - pd.Timedelta(days=1)] + list(df1.index)

s_before_1 = pd.Series(idx_before_1, index=pd.to_datetime(x_dates))
s_after_1 = pd.Series(idx_after_1, index=pd.to_datetime(x_dates))

s_before_2 = None
s_after_2 = None
if idx_before_2 is not None and idx_after_2 is not None:
    s_before_2 = pd.Series(idx_before_2, index=pd.to_datetime(x_dates))
    s_after_2 = pd.Series(idx_after_2, index=pd.to_datetime(x_dates))


# -----------------------------
# Chart: Index (100)
# -----------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=x_dates, y=idx_after_1, mode="lines",
    name=f"{portfolio_sel} – nach Kosten ({fee_pct_1:.2f}%)"
))

if idx_after_2 is not None:
    fig.add_trace(go.Scatter(
        x=x_dates, y=idx_after_2, mode="lines",
        name=f"{portfolio_sel2} – nach Kosten ({(fee_pct_2 or 0.0):.2f}%)"
    ))

if show_vorkosten:
    fig.add_trace(go.Scatter(x=x_dates, y=idx_before_1, mode="lines", name=f"{portfolio_sel} – vor Kosten"))
    if idx_before_2 is not None:
        fig.add_trace(go.Scatter(x=x_dates, y=idx_before_2, mode="lines", name=f"{portfolio_sel2} – vor Kosten"))

if show_benchmark and df1["ret_bm"].notna().any():
    bench_name_1 = data[portfolio_sel].attrs.get("benchmark_name", "Benchmark")
    ret_bm_1 = df1["ret_bm"].fillna(0.0).to_numpy(dtype=float)
    idx_bm_1 = make_index_from_returns(ret_bm_1, startwert=100.0)
    fig.add_trace(go.Scatter(x=x_dates, y=idx_bm_1, mode="lines", name=f"Benchmark {portfolio_sel}: {bench_name_1}"))

    if df2 is not None and df2["ret_bm"].notna().any():
        bench_name_2 = data[portfolio_sel2].attrs.get("benchmark_name", "Benchmark")
        ret_bm_2 = df2["ret_bm"].fillna(0.0).to_numpy(dtype=float)
        idx_bm_2 = make_index_from_returns(ret_bm_2, startwert=100.0)
        fig.add_trace(go.Scatter(x=x_dates, y=idx_bm_2, mode="lines", name=f"Benchmark {portfolio_sel2}: {bench_name_2}"))

fig.update_layout(
    height=550,
    xaxis_title="Datum",
    yaxis_title="Index (Start 100)",
    legend_title_text="Reihen",
    hovermode="x unified",
)

st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# Drawdown Chart (optional)
# -----------------------------
if show_drawdown:
    fig_dd = go.Figure()

    dd1 = drawdown_from_index(idx_after_1)
    fig_dd.add_trace(go.Scatter(x=x_dates, y=dd1, mode="lines", name=f"{portfolio_sel} – Drawdown (nach Kosten)"))

    if idx_after_2 is not None:
        dd2 = drawdown_from_index(idx_after_2)
        fig_dd.add_trace(go.Scatter(x=x_dates, y=dd2, mode="lines", name=f"{portfolio_sel2} – Drawdown (nach Kosten)"))

    fig_dd.update_layout(
        height=350,
        xaxis_title="Datum",
        yaxis_title="Drawdown (dezimal, z.B. -0.12 = -12%)",
        hovermode="x unified",
    )
    st.plotly_chart(fig_dd, use_container_width=True)


# -----------------------------
# Tabelle: Wertentwicklung rollierend (optional)
# -----------------------------
if show_table:
    since_label = f"Wertentwicklung seit: {df1.index.min().strftime('%d.%m.%Y')}"

    df_roll = build_rolling_table(
        idx_before_1=s_before_1,
        idx_after_1=s_after_1,
        label_1=portfolio_sel,
        idx_before_2=s_before_2,
        idx_after_2=s_after_2,
        label_2=portfolio_sel2 if (show_compare and portfolio_sel2) else None,
        since_label=since_label
    )

    st.subheader("Wertentwicklung rollierend")
    st.dataframe(df_roll, use_container_width=True)


# -----------------------------
# Debug
# -----------------------------
with st.expander("Details / Debug"):
    st.write("Gefundene Dateien:", len(files))
    st.write("Zeitraum:", start_date, "bis", end_date)
    st.write(f"Kosten {portfolio_sel} (dezimal):", fee_dec_1)
    if df2 is not None:
        st.write(f"Kosten {portfolio_sel2} (dezimal):", fee_dec_2)
    st.write("Benchmark-Name 1:", data[portfolio_sel].attrs.get("benchmark_name", "Benchmark"))
    if df2 is not None:
        st.write("Benchmark-Name 2:", data[portfolio_sel2].attrs.get("benchmark_name", "Benchmark"))
    st.write("Rows Portfolio 1:", len(df1))
    if df2 is not None:
        st.write("Rows Portfolio 2:", len(df2))
    st.dataframe(df1.head(10))
