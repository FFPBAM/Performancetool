# streamlit_app.py
import os
import glob
import datetime as dt
import locale

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
        st.title("Performance VV Rechner | Fürst Fugger Privatbank")
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

    with st.sidebar:
        st.write(f"👤 Angemeldet als: **{st.session_state.username}**")
        if st.button("Ausloggen"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    return True


# ---------------------------------------------------------------------------
# Helpers: Deutsches Datumsformat
# ---------------------------------------------------------------------------
def fmt_date_de(d) -> str:
    """Formatiert ein date/Timestamp-Objekt als dd.mm.yyyy."""
    if isinstance(d, pd.Timestamp):
        return d.strftime("%d.%m.%Y")
    if isinstance(d, dt.date):
        return d.strftime("%d.%m.%Y")
    return str(d)


def parse_date_de(s: str) -> dt.date | None:
    """Parst einen String im Format dd.mm.yyyy zu einem date-Objekt."""
    s = s.strip()
    try:
        return dt.datetime.strptime(s, "%d.%m.%Y").date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Helpers: Index / Gebühren / Drawdown
# ---------------------------------------------------------------------------
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


def index_to_volume(idx: np.ndarray, volume: float) -> np.ndarray:
    """Rechnet Index (Basis 100) in Euro-Beträge um: volume * (idx / 100)."""
    return volume * (idx / 100.0)


def drawdown_from_index(idx: np.ndarray) -> np.ndarray:
    peak = np.maximum.accumulate(idx)
    return (idx / peak) - 1.0


def to_decimal_interval(series_float: pd.Series) -> np.ndarray:
    x = series_float.to_numpy(dtype=float)
    ax = np.nan_to_num(np.abs(x), nan=0.0)
    if ax.max() > 1.0 or np.median(ax) > 0.2:
        x = x / 100.0
    return x


# ---------------------------------------------------------------------------
# Helpers: Performance-Tabelle (rollierend)
# ---------------------------------------------------------------------------
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
        (since_label or f"Wertentwicklung seit: {fmt_date_de(first_ts)}", first_ts),
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


# ---------------------------------------------------------------------------
# Helpers: Balken-Chart (blockweise Performance)
# ---------------------------------------------------------------------------
def calc_period_return(returns: np.ndarray) -> float:
    return float(np.prod(1.0 + returns) - 1.0)


def calc_period_return_after_fee(returns: np.ndarray, fee_pa_decimal: float) -> float:
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    return float(np.prod(1.0 + (returns - e)) - 1.0)


def compute_bar_data(
    df: pd.DataFrame,
    fee_dec: float,
    mode: str,
    label: str,
    custom_start: dt.date = None,
    custom_end: dt.date = None,
) -> pd.DataFrame:
    rows = []

    def _add_row(period_label: str, sub: pd.DataFrame):
        if sub.empty:
            return
        rp = sub["ret_port"].fillna(0.0).to_numpy(dtype=float)
        rb = sub["ret_bm"].fillna(0.0).to_numpy(dtype=float)
        has_bm = sub["ret_bm"].notna().any()
        rows.append({
            "label": period_label,
            f"{label} (nach Kosten)": calc_period_return_after_fee(rp, fee_dec) * 100,
            "ret_bm_raw": calc_period_return(rb) * 100 if has_bm else None,
        })

    if mode == "Kalenderjahre":
        for y in sorted(df.index.year.unique()):
            _add_row(str(y), df[df.index.year == y])

    elif mode == "Quartale":
        tmp = df.copy()
        tmp["_y"] = tmp.index.year
        tmp["_q"] = tmp.index.quarter
        for (y, q), sub in tmp.groupby(["_y", "_q"]):
            _add_row(f"{y} Q{q}", sub)

    elif mode == "Benutzerdefiniert":
        if custom_start is None or custom_end is None:
            return pd.DataFrame()
        mask = (df.index.date >= custom_start) & (df.index.date <= custom_end)
        lbl = f"{fmt_date_de(custom_start)} – {fmt_date_de(custom_end)}"
        _add_row(lbl, df[mask])

    return pd.DataFrame(rows)


def build_bar_chart(
    bar_df1: pd.DataFrame,
    label_1: str,
    bench_name_1: str,
    bar_df2: pd.DataFrame | None = None,
    label_2: str | None = None,
    bench_name_2: str | None = None,
    title: str = "",
) -> go.Figure:
    COLOR_PORT1 = "#B8973A"
    COLOR_PORT2 = "#2C5F8A"
    COLOR_BM1   = "#A8CBE8"
    COLOR_BM2   = "#7FB5D5"
    BG          = "#1B3A5C"

    fig = go.Figure()

    col_port1 = f"{label_1} (nach Kosten)"

    if col_port1 in bar_df1.columns:
        vals1 = bar_df1[col_port1].tolist()
        fig.add_trace(go.Bar(
            name=f"{label_1} (nach Kosten)",
            x=bar_df1["label"],
            y=vals1,
            marker_color=COLOR_PORT1,
            text=[f"{v:+.2f}%" for v in vals1],
            textposition="outside",
            textfont=dict(size=11, color="white"),
            cliponaxis=False,
        ))

    if "ret_bm_raw" in bar_df1.columns and bar_df1["ret_bm_raw"].notna().any():
        bm_vals1 = bar_df1["ret_bm_raw"].tolist()
        fig.add_trace(go.Bar(
            name=bench_name_1,
            x=bar_df1["label"],
            y=bm_vals1,
            marker_color=COLOR_BM1,
            text=[f"{v:+.2f}%" if pd.notna(v) else "" for v in bm_vals1],
            textposition="outside",
            textfont=dict(size=11, color="white"),
            cliponaxis=False,
        ))

    if bar_df2 is not None and label_2 is not None:
        col_port2 = f"{label_2} (nach Kosten)"
        if col_port2 in bar_df2.columns:
            vals2 = bar_df2[col_port2].tolist()
            fig.add_trace(go.Bar(
                name=f"{label_2} (nach Kosten)",
                x=bar_df2["label"],
                y=vals2,
                marker_color=COLOR_PORT2,
                text=[f"{v:+.2f}%" for v in vals2],
                textposition="outside",
                textfont=dict(size=11, color="white"),
                cliponaxis=False,
            ))

        if (bench_name_2 and bench_name_2 != bench_name_1
                and "ret_bm_raw" in bar_df2.columns
                and bar_df2["ret_bm_raw"].notna().any()):
            bm_vals2 = bar_df2["ret_bm_raw"].tolist()
            fig.add_trace(go.Bar(
                name=bench_name_2,
                x=bar_df2["label"],
                y=bm_vals2,
                marker_color=COLOR_BM2,
                text=[f"{v:+.2f}%" if pd.notna(v) else "" for v in bm_vals2],
                textposition="outside",
                textfont=dict(size=11, color="white"),
                cliponaxis=False,
            ))

    fig.add_hline(y=0, line_color="white", line_width=1)

    all_vals = []
    for col in [col_port1] + ([f"{label_2} (nach Kosten)"] if label_2 else []):
        src = bar_df1 if col == col_port1 else (bar_df2 if bar_df2 is not None else pd.DataFrame())
        if col in src.columns:
            all_vals += src[col].dropna().tolist()
    if "ret_bm_raw" in bar_df1.columns:
        all_vals += bar_df1["ret_bm_raw"].dropna().tolist()
    if bar_df2 is not None and "ret_bm_raw" in bar_df2.columns:
        all_vals += bar_df2["ret_bm_raw"].dropna().tolist()

    if all_vals:
        y_min = min(all_vals) * 1.45 if min(all_vals) < 0 else -2
        y_max = max(all_vals) * 1.45 if max(all_vals) > 0 else 2
    else:
        y_min, y_max = -10, 10

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=13, color="white"),
            x=0, xanchor="left",
        ),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        barmode="group",
        bargap=0.28,
        bargroupgap=0.05,
        height=480,
        xaxis=dict(
            tickfont=dict(color="white", size=12),
            showgrid=False,
            zeroline=False,
            linecolor="#3A5A7C",
        ),
        yaxis=dict(
            range=[y_min, y_max],
            tickformat=".1f",
            ticksuffix="%",
            tickfont=dict(color="white", size=11),
            gridcolor="#2A4A6C",
            zeroline=False,
        ),
        legend=dict(
            font=dict(color="white", size=11),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            y=-0.18,
        ),
        margin=dict(t=55, b=75, l=65, r=25),
    )
    return fig


# ---------------------------------------------------------------------------
# Benchmark-Zusammensetzung anzeigen
# ---------------------------------------------------------------------------
def show_benchmark_composition(
    display_name: str,
    benchmark_text: str | None,
    display_name_2: str | None = None,
    benchmark_text_2: str | None = None,
):
    """Zeigt die Benchmark-Zusammensetzung unter einem Chart an."""
    if benchmark_text and str(benchmark_text).strip() and str(benchmark_text).strip().lower() not in ("", "nan", "haben keine benchmark"):
        st.caption(f"**Zusammensetzung Benchmark {display_name}:** {benchmark_text}")
    if display_name_2 and benchmark_text_2 and str(benchmark_text_2).strip() and str(benchmark_text_2).strip().lower() not in ("", "nan", "haben keine benchmark"):
        st.caption(f"**Zusammensetzung Benchmark {display_name_2}:** {benchmark_text_2}")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_mapping(mapping_path: str) -> pd.DataFrame:
    return pd.read_excel(mapping_path).round(6)


@st.cache_data(show_spinner=False)
def load_name_mapping(path: str) -> pd.DataFrame:
    """
    Lädt Mapping_Namen.xlsx mit Spalten:
    - Spalte A: 'Strategie auswählen' (Anzeigename)
    - Spalte B: 'Honorarsatz Mapping' (CSV-Schlüssel = Portfolio Name)
    - Spalte D: 'Benchmark' (Benchmark-Zusammensetzung als Text)
    """
    df = pd.read_excel(path)
    return df


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
        df["ret_bm"] = ret_bm if (ret_bm is not None and len(ret_bm) == len(df)) else np.nan
        df["fee_default"] = fee_default
        df = df.sort_index()
        df.attrs["benchmark_name"] = bench_name

        out[portfolio] = df

    return out


# =============================================================================
# STREAMLIT UI
# =============================================================================
st.set_page_config(page_title="Performances Vergleich unserer VVs", layout="wide")

if not check_login():
    st.stop()

st.title("Performancevergleich – Fürst Fugger Privatbank")

MAPPING_PATH      = r"Mapping_Honorarsatz.xlsx"
NAME_MAPPING_PATH = r"Mapping_Namen2.xlsx"
DATA_FOLDER       = r"Daten"
exclude_substrings = ["Stiftung"]
heute_tag = dt.date.today().strftime("%y%m%d")

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Einstellungen")

    date_tag = st.text_input("Date-Tag (yyMMdd)", value=heute_tag)

    mapping      = load_mapping(MAPPING_PATH)
    name_mapping = load_name_mapping(NAME_MAPPING_PATH)
    files        = load_all_csvs(DATA_FOLDER, date_tag, exclude_substrings)

    if len(files) == 0:
        st.error(f"Keine Dateien gefunden für Tag {date_tag}. Pattern: *_{date_tag}_*.CSV")
        st.stop()

    data = build_portfolio_timeseries(files, mapping)

    # ── Name-Mapping aufbauen ──────────────────────────────────────────────
    # Spalte A = Anzeigename, Spalte B = CSV-Schlüssel (Portfolio Name)
    col_display = name_mapping.columns[0]   # "Strategie auswählen"
    col_csv_key = name_mapping.columns[1]   # "Honorarsatz Mapping"
    col_bench   = name_mapping.columns[3]   # "Benchmark" (Spalte D)

    # Nur Zeilen behalten, deren CSV-Schlüssel auch in den geladenen Daten vorhanden sind
    available_csv_names = set(data.keys())
    name_mapping_filtered = name_mapping[
        name_mapping[col_csv_key].isin(available_csv_names)
    ].copy()

    # Reihenfolge aus der Excel beibehalten
    display_names_ordered = name_mapping_filtered[col_display].tolist()

    # Lookup-Dicts: Anzeigename <-> CSV-Schlüssel, Anzeigename -> Benchmark-Text
    display_to_csv = dict(zip(
        name_mapping_filtered[col_display],
        name_mapping_filtered[col_csv_key]
    ))
    display_to_benchmark = dict(zip(
        name_mapping_filtered[col_display],
        name_mapping_filtered[col_bench]
    ))

    if len(display_names_ordered) == 0:
        st.error("Keine Portfolios aus Mapping_Namen.xlsx konnten den geladenen CSV-Daten zugeordnet werden.")
        st.stop()

    # ── Portfolio-Auswahl (Anzeigenamen, Reihenfolge aus Excel) ────────────
    display_sel_1 = st.selectbox("Portfolio auswählen", display_names_ordered)
    portfolio_sel = display_to_csv[display_sel_1]

    show_compare  = st.checkbox("Vergleichsportfolio anzeigen", value=False)
    portfolio_sel2 = None
    display_sel_2  = None
    if show_compare:
        display_sel_2 = st.selectbox("Vergleichsportfolio auswählen", display_names_ordered)
        portfolio_sel2 = display_to_csv[display_sel_2]

    show_vorkosten = st.checkbox("Vor Kosten anzeigen",                   value=True)
    show_benchmark = st.checkbox("Benchmark anzeigen",                    value=True)
    show_drawdown  = st.checkbox("Drawdown (nach Kosten) anzeigen",       value=False)
    show_table     = st.checkbox("Tabelle: Wertentwicklung rollierend",   value=True)
    show_bar       = st.checkbox("Balken-Chart: Performance blockweise",  value=True)

    # ── Anlagevolumen (optional) ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("Anlagevolumen")
    anlagevolumen = st.number_input(
        "Anlagevolumen in € (optional)",
        min_value=0.0,
        max_value=1_000_000_000.0,
        value=0.0,
        step=10_000.0,
        format="%.2f",
        help="Wenn ein Volumen > 0 eingegeben wird, zeigt der Chart die Wertentwicklung in Euro an. Sonst Index ab 100."
    )
    use_volume = anlagevolumen > 0

    st.markdown("---")

    # ── Kosten Portfolio 1 ─────────────────────────────────────────────────
    fee_default_dec_1 = float(data[portfolio_sel]["fee_default"].iloc[0]) if len(data[portfolio_sel]) else 0.0
    fee_pct_1 = st.number_input(
        f"Kosten p.a. (%) – {display_sel_1}",
        min_value=0.0, max_value=20.0,
        value=float(round(fee_default_dec_1 * 100, 4)),
        step=0.05,
        help="Eingabe in Prozent p.a. (z.B. 1,55)."
    )
    fee_dec_1 = fee_pct_1 / 100.0

    # ── Kosten Portfolio 2 (nur wenn Vergleich aktiv) ──────────────────────
    fee_dec_2 = None
    fee_pct_2 = None
    if show_compare and portfolio_sel2:
        fee_default_dec_2 = float(data[portfolio_sel2]["fee_default"].iloc[0]) if len(data[portfolio_sel2]) else 0.0
        fee_pct_2 = st.number_input(
            f"Kosten p.a. (%) – {display_sel_2}",
            min_value=0.0, max_value=20.0,
            value=float(round(fee_default_dec_2 * 100, 4)),
            step=0.05,
            help="Eingabe in Prozent p.a. (z.B. 1,55)."
        )
        fee_dec_2 = fee_pct_2 / 100.0


# ── Anzeigenamen für Charts / Tabellen ─────────────────────────────────────
label_1 = display_sel_1
label_2 = display_sel_2 if (show_compare and display_sel_2) else None


# ── Daten vorbereiten / Zeitraum (deutsches Datumsformat) ──────────────────
df1 = data[portfolio_sel].copy()
min_d, max_d = df1.index.min().date(), df1.index.max().date()

st.markdown("#### Zeitraum auswählen")
col1, col2 = st.columns(2)
with col1:
    start_input = st.text_input(
        "Start (dd.mm.yyyy)",
        value=fmt_date_de(min_d),
        key="start_date_input"
    )
with col2:
    end_input = st.text_input(
        "Ende (dd.mm.yyyy)",
        value=fmt_date_de(max_d),
        key="end_date_input"
    )

start_date = parse_date_de(start_input)
end_date   = parse_date_de(end_input)

if start_date is None:
    st.error(f"Ungültiges Startdatum: '{start_input}'. Bitte im Format dd.mm.yyyy eingeben.")
    st.stop()
if end_date is None:
    st.error(f"Ungültiges Enddatum: '{end_input}'. Bitte im Format dd.mm.yyyy eingeben.")
    st.stop()

# Auf verfügbaren Bereich klemmen
start_date = max(start_date, min_d)
end_date   = min(end_date, max_d)

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
        st.error("Kein gemeinsamer Datumsbereich zwischen Portfolio und Vergleichsportfolio.")
        st.stop()

    df1 = joined[["ret_port_1", "ret_bm_1"]].rename(columns={"ret_port_1": "ret_port", "ret_bm_1": "ret_bm"})
    df2 = joined[["ret_port_2", "ret_bm_2"]].rename(columns={"ret_port_2": "ret_port", "ret_bm_2": "ret_bm"})


# ── Indexberechnung ────────────────────────────────────────────────────────
startwert = anlagevolumen if use_volume else 100.0

ret1         = df1["ret_port"].to_numpy(dtype=float)
idx_after_1  = make_index_after_fee(ret1, fee_dec_1, startwert=startwert)
idx_before_1 = make_index_from_returns(ret1, startwert=startwert)

idx_after_2  = None
idx_before_2 = None
if df2 is not None:
    ret2         = df2["ret_port"].to_numpy(dtype=float)
    idx_after_2  = make_index_after_fee(ret2, float(fee_dec_2), startwert=startwert)
    idx_before_2 = make_index_from_returns(ret2, startwert=startwert)

x_dates = [df1.index.min() - pd.Timedelta(days=1)] + list(df1.index)

# Für rollierende Tabelle immer Index-Basis 100 (unabhängig vom Volumen)
ret1_for_table = df1["ret_port"].to_numpy(dtype=float)
s_before_1_tbl = pd.Series(make_index_from_returns(ret1_for_table, 100.0), index=pd.to_datetime(x_dates))
s_after_1_tbl  = pd.Series(make_index_after_fee(ret1_for_table, fee_dec_1, 100.0), index=pd.to_datetime(x_dates))
s_before_2_tbl = None
s_after_2_tbl  = None
if df2 is not None:
    ret2_for_table = df2["ret_port"].to_numpy(dtype=float)
    s_before_2_tbl = pd.Series(make_index_from_returns(ret2_for_table, 100.0), index=pd.to_datetime(x_dates))
    s_after_2_tbl  = pd.Series(make_index_after_fee(ret2_for_table, float(fee_dec_2), 100.0), index=pd.to_datetime(x_dates))

bench_name_1 = data[portfolio_sel].attrs.get("benchmark_name", "Benchmark")
bench_name_2 = data[portfolio_sel2].attrs.get("benchmark_name", "Benchmark") if (show_compare and portfolio_sel2) else None

# Benchmark-Texte aus Mapping
bench_text_1 = display_to_benchmark.get(display_sel_1, "")
bench_text_2 = display_to_benchmark.get(display_sel_2, "") if display_sel_2 else ""


# ── Chart: Index / Volumen ─────────────────────────────────────────────────
if use_volume:
    st.subheader(f"📈 Wertentwicklung in Euro (Anlagevolumen: {anlagevolumen:,.2f} €)")
    y_label = "Wert in €"
else:
    st.subheader("📈 Performance-Index (Start = 100)")
    y_label = "Index (Start 100)"

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=x_dates, y=idx_after_1, mode="lines",
    name=f"{label_1} – nach Kosten ({fee_pct_1:.2f}%)"
))

if idx_after_2 is not None:
    fig.add_trace(go.Scatter(
        x=x_dates, y=idx_after_2, mode="lines",
        name=f"{label_2} – nach Kosten ({(fee_pct_2 or 0.0):.2f}%)"
    ))

if show_vorkosten:
    fig.add_trace(go.Scatter(x=x_dates, y=idx_before_1, mode="lines",
                             name=f"{label_1} – vor Kosten"))
    if idx_before_2 is not None:
        fig.add_trace(go.Scatter(x=x_dates, y=idx_before_2, mode="lines",
                                 name=f"{label_2} – vor Kosten"))

if show_benchmark and df1["ret_bm"].notna().any():
    ret_bm_1 = df1["ret_bm"].fillna(0.0).to_numpy(dtype=float)
    idx_bm_1 = make_index_from_returns(ret_bm_1, startwert=startwert)
    fig.add_trace(go.Scatter(x=x_dates, y=idx_bm_1, mode="lines",
                             name=f"Benchmark {label_1}: {bench_name_1}"))

    if df2 is not None and df2["ret_bm"].notna().any():
        ret_bm_2 = df2["ret_bm"].fillna(0.0).to_numpy(dtype=float)
        idx_bm_2 = make_index_from_returns(ret_bm_2, startwert=startwert)
        fig.add_trace(go.Scatter(x=x_dates, y=idx_bm_2, mode="lines",
                                 name=f"Benchmark {label_2}: {bench_name_2}"))

# Deutsches Datumsformat auf der X-Achse
fig.update_layout(
    height=550,
    xaxis_title="Datum",
    xaxis=dict(
        tickformat="%d.%m.%Y",
    ),
    yaxis_title=y_label,
    yaxis=dict(
        tickformat=",.2f" if use_volume else None,
    ),
    legend_title_text="Reihen",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ── Benchmark-Zusammensetzung unter dem Linien-Chart ───────────────────────
if show_benchmark:
    show_benchmark_composition(
        display_name=label_1,
        benchmark_text=bench_text_1,
        display_name_2=label_2,
        benchmark_text_2=bench_text_2,
    )


# ── Drawdown Chart ─────────────────────────────────────────────────────────
if show_drawdown:
    fig_dd = go.Figure()
    # Drawdown immer auf Basis des Index (nicht Volumen), da es relativ ist
    dd_idx_1 = make_index_after_fee(ret1, fee_dec_1, startwert=100.0)
    dd1 = drawdown_from_index(dd_idx_1)
    fig_dd.add_trace(go.Scatter(x=x_dates, y=dd1, mode="lines",
                                name=f"{label_1} – Drawdown (nach Kosten)"))
    if df2 is not None and idx_after_2 is not None:
        dd_idx_2 = make_index_after_fee(ret2, float(fee_dec_2), startwert=100.0)
        dd2 = drawdown_from_index(dd_idx_2)
        fig_dd.add_trace(go.Scatter(x=x_dates, y=dd2, mode="lines",
                                    name=f"{label_2} – Drawdown (nach Kosten)"))
    fig_dd.update_layout(
        height=350,
        xaxis_title="Datum",
        xaxis=dict(tickformat="%d.%m.%Y"),
        yaxis_title="Drawdown (dezimal, z.B. -0,12 = -12%)",
        hovermode="x unified",
    )
    st.plotly_chart(fig_dd, use_container_width=True)


# ── Tabelle: Wertentwicklung rollierend ────────────────────────────────────
if show_table:
    since_label = f"Wertentwicklung seit: {fmt_date_de(df1.index.min())}"
    df_roll = build_rolling_table(
        idx_before_1=s_before_1_tbl,
        idx_after_1=s_after_1_tbl,
        label_1=label_1,
        idx_before_2=s_before_2_tbl,
        idx_after_2=s_after_2_tbl,
        label_2=label_2,
        since_label=since_label
    )
    st.subheader("📋 Wertentwicklung rollierend")
    st.dataframe(df_roll, use_container_width=True)


# ── Balken-Chart: Performance blockweise ───────────────────────────────────
if show_bar:
    st.markdown("---")
    st.subheader("📊 Performance im Benchmarkvergleich (blockweise)")

    bar_left, bar_right = st.columns([1, 3])

    with bar_left:
        bar_mode = st.radio(
            "Zeitraum-Einteilung",
            options=["Kalenderjahre", "Quartale", "Benutzerdefiniert"],
            index=0,
        )
        custom_start_bar = None
        custom_end_bar   = None
        if bar_mode == "Benutzerdefiniert":
            custom_start_input = st.text_input(
                "Von (dd.mm.yyyy)", value=fmt_date_de(start_date), key="bar_von"
            )
            custom_end_input = st.text_input(
                "Bis (dd.mm.yyyy)", value=fmt_date_de(end_date), key="bar_bis"
            )
            custom_start_bar = parse_date_de(custom_start_input)
            custom_end_bar   = parse_date_de(custom_end_input)
            if custom_start_bar is None or custom_end_bar is None:
                st.error("Bitte gültige Daten im Format dd.mm.yyyy eingeben.")

    titel_map = {
        "Kalenderjahre":     "PERFORMANCE P.A. (NACH KOSTEN) IM BENCHMARKVERGLEICH",
        "Quartale":          "PERFORMANCE QUARTALE (NACH KOSTEN) IM BENCHMARKVERGLEICH",
        "Benutzerdefiniert": "PERFORMANCE (NACH KOSTEN) IM BENCHMARKVERGLEICH – BENUTZERDEFINIERT",
    }

    def _render_bar(df_src, fee, label, bench_name, container):
        bar_df = compute_bar_data(
            df_src, fee_dec=fee, mode=bar_mode, label=label,
            custom_start=custom_start_bar, custom_end=custom_end_bar,
        )
        if bar_df.empty:
            container.info(f"Keine Daten für {label}.")
            return
        bar_fig = build_bar_chart(
            bar_df1=bar_df,
            label_1=label,
            bench_name_1=bench_name,
            title=f"{titel_map[bar_mode]} – {label}",
        )
        container.plotly_chart(bar_fig, use_container_width=True)
        with container.expander("🔢 Tabelle anzeigen"):
            col_p = f"{label} (nach Kosten)"
            disp = bar_df[["label", col_p, "ret_bm_raw"]].copy()
            disp[col_p]        = disp[col_p].map(lambda x: f"{x:+.2f}%")
            disp["ret_bm_raw"] = disp["ret_bm_raw"].map(
                lambda x: f"{x:+.2f}%" if pd.notna(x) else "–")
            disp.columns = ["Zeitraum", f"{label} nach Kosten", bench_name]
            container.dataframe(disp, use_container_width=True, hide_index=True)

    with bar_right:
        # ── Chart Portfolio 1 ──
        _render_bar(df1, fee_dec_1, label_1, bench_name_1, st.container())

        # ── Benchmark-Zusammensetzung unter Balken-Chart Portfolio 1 ──
        if show_benchmark:
            show_benchmark_composition(
                display_name=label_1,
                benchmark_text=bench_text_1,
            )

        # ── Chart Portfolio 2 (nur wenn Vergleich aktiv) ──
        if df2 is not None and fee_dec_2 is not None and portfolio_sel2:
            st.markdown("---")
            _render_bar(df2, fee_dec_2, label_2, bench_name_2 or "Benchmark", st.container())

            # ── Benchmark-Zusammensetzung unter Balken-Chart Portfolio 2 ──
            if show_benchmark:
                show_benchmark_composition(
                    display_name=label_2,
                    benchmark_text=bench_text_2,
                )


# ── Debug ──────────────────────────────────────────────────────────────────
with st.expander("Details / Debug"):
    st.write("Gefundene Dateien:", len(files))
    st.write("Zeitraum:", fmt_date_de(start_date), "bis", fmt_date_de(end_date))
    st.write(f"Kosten {label_1} (dezimal):", fee_dec_1)
    if df2 is not None:
        st.write(f"Kosten {label_2} (dezimal):", fee_dec_2)
    st.write("Benchmark-Name 1:", bench_name_1)
    st.write("Benchmark-Text 1:", bench_text_1)
    if df2 is not None:
        st.write("Benchmark-Name 2:", bench_name_2)
        st.write("Benchmark-Text 2:", bench_text_2)
    st.write(f"Anlagevolumen: {anlagevolumen:,.2f} €" if use_volume else "Anlagevolumen: nicht gesetzt (Index 100)")
    st.write("Rows Portfolio 1:", len(df1))
    if df2 is not None:
        st.write("Rows Portfolio 2:", len(df2))
    st.dataframe(df1.head(10))
