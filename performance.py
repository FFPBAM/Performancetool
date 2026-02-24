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
    """
    fee_pa_decimal: z.B. 0.0155 für 1,55% p.a.
    returns: täglicher Gebühren-Drag e (dezimal)
    """
    return (1.0 + fee_pa_decimal) ** (1 / 365) - 1


def make_index_from_returns(d_returns_decimal: np.ndarray, startwert: float = 100.0) -> np.ndarray:
    """
    d_returns_decimal: tägliche Renditen als Dezimalwerte (0.003 = 0,3%)
    """
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
    """
    Robust: Wenn Werte eher wie Prozentpunkte aussehen (z.B. 0.30 für 0,30%),
    dann teilen wir durch 100. Wenn sie schon dezimal sind (0.003), lassen wir sie.
    """
    x = series_float.to_numpy(dtype=float)

    # Heuristik: typische Tagesrenditen liegen i.d.R. |d| < 0.2 (20%) dezimal.
    # Wenn max(|d|) > 1, ist es fast sicher in Prozentpunkten.
    # Wenn median(|d|) > 0.2, ebenfalls sehr wahrscheinlich Prozentpunkte.
    ax = np.nan_to_num(np.abs(x), nan=0.0)
    if ax.max() > 1.0 or np.median(ax) > 0.2:
        x = x / 100.0
    return x


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

# Einlesen der CSV Musterporfolien
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
    # "Datum" im Format "11.03.2024"
    return pd.to_datetime(vv["Datum"], format="%d.%m.%Y", errors="raise")


@st.cache_data(show_spinner=True)
def build_portfolio_timeseries(files: list[str], mapping: pd.DataFrame) -> dict:
    """
    Rückgabe:
      dict[portfolio] = DataFrame(index=Datum, cols=["ret_port", "ret_bm", "fee_default"])
      ret_* als Dezimal-Intervallrenditen (täglich)
    """
    out = {}

    for path in files:
        vv = read_one_csv(path)

        portfolio = vv.loc[0, "Portfolio Name"]

        # Datum
        dates = parse_dates_col(vv)

        # Portfolio-Intervallrendite
        vv["Performance [%] (Intervall)"] = (
            vv["Performance [%] (Intervall)"].astype(str).str.replace(",", ".").astype(float)
        )
        # ab Zeile 1 (dein Code)
        ret_port = to_decimal_interval(vv.loc[1:, "Performance [%] (Intervall)"])

        # Benchmark-Intervallrendite (falls vorhanden)
        ret_bm = None
        if "Benchmark Performance [%] (Intervall)" in vv.columns:
            vv["Benchmark Performance [%] (Intervall)"] = (
                vv["Benchmark Performance [%] (Intervall)"].astype(str).str.replace(",", ".").astype(float)
            )
            ret_bm = to_decimal_interval(vv.loc[1:, "Benchmark Performance [%] (Intervall)"])

        # Default Fee aus Mapping (Honorarsatz Standard ist bereits dezimal: 0.0155)
        fee_default = None
        try:
            fee_default = float(mapping.loc[mapping["Inhaber"] == portfolio, "Honorarsatz Standard"].values[0])
        except Exception:
            fee_default = 0.0

        # Align lengths:
        # dates enthält alle Zeilen inkl. Zeile 0, ret_* ist ab Zeile 1 -> daher dates[1:]
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
st.set_page_config(page_title="Performance Index (100) – Streamlit", layout="wide")
st.title("Performance Index (Start 100) – nach Kosten / vor Kosten / Benchmark")



# ---------------------------------------------------------------------------
# LOGIN AUTHENTICATION
# ---------------------------------------------------------------------------

def check_login():
    """
    Login-Authentifizierung mit Streamlit Secrets.
    Gibt True zurück wenn der Benutzer eingeloggt ist.
    """
    import streamlit as st
    
    # Secrets laden (Benutzername und Passwörter)
    USERS = st.secrets["passwords"]
    
    # Session State initialisieren
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
    
    # Login-Funktion
    def verify_password():
        username = st.session_state.get("username_input", "")
        password = st.session_state.get("password_input", "")
        
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            return True
        return False
    
    # Login-Interface
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
        # Logout-Button in der Sidebar
        with st.sidebar:
            st.write(f"👤 Angemeldet als: **{st.session_state.username}**")
            if st.button("Ausloggen"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.rerun()
        
        return True

# Paths anpassen
MAPPING_PATH = r"Mapping_Honorarsatz.xlsx"
DATA_FOLDER = r"Daten"

exclude_substrings = [
    "Stiftung"
]

# Datetag wie bei dir: yyMMdd
heute_tag = dt.date.today().strftime("%y%m%d")

with st.sidebar:
    st.header("Einstellungen")

    # optional: Datumstag überschreiben
    date_tag = st.text_input("Date-Tag (yyMMdd)", value=heute_tag)

    mapping = load_mapping(MAPPING_PATH)
    files = load_all_csvs(DATA_FOLDER, date_tag, exclude_substrings)

    if len(files) == 0:
        st.error(f"Keine Dateien gefunden für Tag {date_tag}. Pattern: *_{date_tag}_*.CSV")
        st.stop()

    data = build_portfolio_timeseries(files, mapping)

    portfolios = sorted(list(data.keys()))
    portfolio_sel = st.selectbox("Portfolio auswählen", portfolios)
    # neu
    portfolio_sel2 = st.selectbox("Vergleichsportfolio auswählen", portfolios)

    show_vorkosten = st.checkbox("Vor Kosten anzeigen", value=True)
    show_benchmark = st.checkbox("Benchmark anzeigen", value=True)

    # Fee Input: Berater gibt 1,55 ein -> intern /100
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

# Indexreihen berechnen (auf gefiltertem Zeitraum)
ret_port = df["ret_port"].to_numpy(dtype=float)
idx_after = make_index_after_fee(ret_port, fee_pa_decimal=fee_dec, startwert=100.0)
idx_before = make_index_from_returns(ret_port, startwert=100.0)

# Datum-Achse: Index hat +1 Punkt (Startwert), deshalb Datum um einen Startpunkt ergänzen
x_dates = [df.index.min() - pd.Timedelta(days=1)] + list(df.index)

fig = go.Figure()
fig.add_trace(go.Scatter(x=x_dates, y=idx_after, mode="lines", name=f"{portfolio_sel} – nach Kosten"))
fig.add_trace(go.Scatter(x=x_dates, y=idx_after, mode="lines", name=f"{portfolio_sel2} – nach Kosten"))

if show_vorkosten:
    fig.add_trace(go.Scatter(x=x_dates, y=idx_before, mode="lines", name=f"{portfolio_sel} – vor Kosten"))
    fig.add_trace(go.Scatter(x=x_dates, y=idx_before, mode="lines", name=f"{portfolio_sel2} – vor Kosten")

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

with st.expander("Details / Debug"):
    st.write("Gefundene Dateien:", len(files))
    st.write("Kosten p.a. (dezimal):", fee_dec)
    st.dataframe(df.head(10))


