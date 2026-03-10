import os
import glob
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def annual_fee_to_daily_drag(fee_pa_decimal: float) -> float:
    """1,55 % p.a. → täglicher Drag als Dezimal."""
    return (1.0 + fee_pa_decimal) ** (1 / 365) - 1


def make_index_from_returns(d_returns: np.ndarray, startwert: float = 100.0) -> np.ndarray:
    """Kumulierter Index aus täglichen Dezimal-Renditen."""
    idx = np.empty(len(d_returns) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(d_returns, start=1):
        idx[i] = idx[i - 1] * (1.0 + d)
    return idx


def make_index_after_fee(d_returns: np.ndarray, fee_pa_decimal: float,
                         startwert: float = 100.0) -> np.ndarray:
    """Kumulierter Index nach täglichem Gebühren-Drag."""
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    idx = np.empty(len(d_returns) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(d_returns, start=1):
        idx[i] = idx[i - 1] * (1.0 + (d - e))
    return idx


def to_decimal_interval(series: pd.Series) -> np.ndarray:
    """Heuristik: Prozentpunkte → Dezimal falls nötig."""
    x = series.to_numpy(dtype=float)
    ax = np.nan_to_num(np.abs(x), nan=0.0)
    if ax.max() > 1.0 or np.median(ax) > 0.2:
        x = x / 100.0
    return x


def calc_period_return(returns: np.ndarray) -> float:
    return float(np.prod(1.0 + returns) - 1.0)


def calc_period_return_after_fee(returns: np.ndarray, fee_pa_decimal: float) -> float:
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    return float(np.prod(1.0 + (returns - e)) - 1.0)


# ─────────────────────────────────────────────
# BALKEN-DATEN BERECHNEN
# ─────────────────────────────────────────────

def compute_bar_data(df: pd.DataFrame, fee_dec: float, mode: str,
                     custom_start: dt.date = None,
                     custom_end: dt.date = None) -> pd.DataFrame:
    """
    Gibt DataFrame: label | ret_port_after (%) | ret_bm (%)
    """
    rows = []

    if mode == "Kalenderjahre":
        for y in sorted(df.index.year.unique()):
            sub = df[df.index.year == y]
            if sub.empty:
                continue
            rp = sub["ret_port"].fillna(0.0).to_numpy(dtype=float)
            rb = sub["ret_bm"].fillna(0.0).to_numpy(dtype=float)
            has_bm = sub["ret_bm"].notna().any()
            rows.append({
                "label": str(y),
                "ret_port_after": calc_period_return_after_fee(rp, fee_dec) * 100,
                "ret_bm": calc_period_return(rb) * 100 if has_bm else None,
            })

    elif mode == "Quartale":
        tmp = df.copy()
        tmp["_y"] = tmp.index.year
        tmp["_q"] = tmp.index.quarter
        for (y, q), sub in tmp.groupby(["_y", "_q"]):
            if sub.empty:
                continue
            rp = sub["ret_port"].fillna(0.0).to_numpy(dtype=float)
            rb = sub["ret_bm"].fillna(0.0).to_numpy(dtype=float)
            has_bm = sub["ret_bm"].notna().any()
            rows.append({
                "label": f"{y} Q{q}",
                "ret_port_after": calc_period_return_after_fee(rp, fee_dec) * 100,
                "ret_bm": calc_period_return(rb) * 100 if has_bm else None,
            })

    elif mode == "Benutzerdefiniert":
        if custom_start is None or custom_end is None:
            return pd.DataFrame(columns=["label", "ret_port_after", "ret_bm"])
        mask = (df.index.date >= custom_start) & (df.index.date <= custom_end)
        sub = df[mask]
        if sub.empty:
            return pd.DataFrame(columns=["label", "ret_port_after", "ret_bm"])
        rp = sub["ret_port"].fillna(0.0).to_numpy(dtype=float)
        rb = sub["ret_bm"].fillna(0.0).to_numpy(dtype=float)
        has_bm = sub["ret_bm"].notna().any()
        label = (f"{custom_start.strftime('%d.%m.%Y')} – "
                 f"{custom_end.strftime('%d.%m.%Y')}")
        rows.append({
            "label": label,
            "ret_port_after": calc_period_return_after_fee(rp, fee_dec) * 100,
            "ret_bm": calc_period_return(rb) * 100 if has_bm else None,
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# BALKEN-GRAFIK BAUEN
# ─────────────────────────────────────────────

def build_bar_chart(bar_df: pd.DataFrame, title: str) -> go.Figure:
    GOLD      = "#B8973A"
    LIGHTBLUE = "#A8CBE8"
    BG        = "#1B3A5C"

    fig = go.Figure()

    port_vals = bar_df["ret_port_after"].tolist()
    fig.add_trace(go.Bar(
        name="Portfolio (nach Kosten)",
        x=bar_df["label"],
        y=port_vals,
        marker_color=GOLD,
        text=[f"{v:+.2f}%" for v in port_vals],
        textposition="outside",
        textfont=dict(size=12, color="white"),
        cliponaxis=False,
    ))

    if "ret_bm" in bar_df.columns and bar_df["ret_bm"].notna().any():
        bm_vals = bar_df["ret_bm"].tolist()
        fig.add_trace(go.Bar(
            name="Benchmark",
            x=bar_df["label"],
            y=bm_vals,
            marker_color=LIGHTBLUE,
            text=[f"{v:+.2f}%" if pd.notna(v) else "" for v in bm_vals],
            textposition="outside",
            textfont=dict(size=12, color="white"),
            cliponaxis=False,
        ))

    fig.add_hline(y=0, line_color="white", line_width=1)

    all_vals = port_vals + (bar_df["ret_bm"].dropna().tolist()
                            if "ret_bm" in bar_df.columns else [])
    y_min = min(all_vals) * 1.4 if min(all_vals) < 0 else -2
    y_max = max(all_vals) * 1.4 if max(all_vals) > 0 else 2

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=13, color="white"),
            x=0, xanchor="left",
        ),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        barmode="group",
        bargap=0.30,
        bargroupgap=0.05,
        height=460,
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
        margin=dict(t=55, b=70, l=65, r=25),
    )
    return fig


# ─────────────────────────────────────────────
# DATEN LADEN
# ─────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_mapping(mapping_path: str) -> pd.DataFrame:
    return pd.read_excel(mapping_path).round(6)


@st.cache_data(show_spinner=True)
def load_all_csvs(data_folder: str, date_tag: str,
                  exclude_substrings: list) -> list:
    pattern = os.path.join(data_folder, f"*_{date_tag}_*.CSV")
    files = glob.glob(pattern)
    return [p for p in files
            if not any(sub in os.path.basename(p)
                       for sub in exclude_substrings)]


def read_one_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(
        path, comment="#", encoding="ISO-8859-1",
        delimiter=";", decimal=",", thousands=".", dtype=str,
    )


def parse_dates_col(vv: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(vv["Datum"], format="%d.%m.%Y", errors="raise")


@st.cache_data(show_spinner=True)
def build_portfolio_timeseries(files: list, mapping: pd.DataFrame) -> dict:
    out = {}
    for path in files:
        try:
            vv        = read_one_csv(path)
            portfolio = vv.loc[0, "Portfolio Name"]
            dates     = parse_dates_col(vv)

            vv["Performance [%] (Intervall)"] = (
                vv["Performance [%] (Intervall)"]
                .astype(str).str.replace(",", ".").astype(float)
            )
            ret_port = to_decimal_interval(
                vv.loc[1:, "Performance [%] (Intervall)"])

            ret_bm  = None
            bm_col  = "Benchmark Performance [%] (Intervall)"
            if bm_col in vv.columns:
                vv[bm_col] = (vv[bm_col].astype(str)
                              .str.replace(",", ".").astype(float))
                ret_bm = to_decimal_interval(vv.loc[1:, bm_col])

            try:
                fee_default = float(
                    mapping.loc[mapping["Inhaber"] == portfolio,
                                "Honorarsatz Standard"].values[0])
            except Exception:
                fee_default = 0.0

            idx = dates.iloc[1:].reset_index(drop=True)
            df  = pd.DataFrame(index=idx)
            df.index.name  = "Datum"
            df["ret_port"]    = ret_port
            df["ret_bm"]      = (ret_bm if (ret_bm is not None
                                            and len(ret_bm) == len(df))
                                 else np.nan)
            df["fee_default"] = fee_default
            out[portfolio]    = df.sort_index()

        except Exception as e:
            st.warning(f"⚠️ Datei übersprungen: {os.path.basename(path)}\n{e}")

    return out


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

def check_login() -> bool:
    USERS = st.secrets.get("passwords", {})

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username  = ""

    if not st.session_state.logged_in:
        st.title("Performance-Tool | Fürst Fugger Privatbank")
        st.write("Bitte melden Sie sich an.")
        st.text_input("Benutzername", key="username_input")
        st.text_input("Passwort", type="password", key="password_input")
        if st.button("Einloggen"):
            u = st.session_state.username_input
            p = st.session_state.password_input
            if u in USERS and USERS[u] == p:
                st.session_state.logged_in = True
                st.session_state.username  = u
                st.rerun()
            else:
                st.error("❌ Falscher Benutzername oder Passwort")
        return False

    with st.sidebar:
        st.write(f"👤 **{st.session_state.username}**")
        if st.button("Ausloggen"):
            st.session_state.logged_in = False
            st.rerun()
    return True


# ─────────────────────────────────────────────
# HAUPT-APP
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Performance Index – Fürst Fugger",
    layout="wide",
)

# Login-Guard – einkommentieren falls benötigt:
# if not check_login():
#     st.stop()

st.title("Performance Index (Start = 100)")

MAPPING_PATH       = r"Mapping_Honorarsatz.xlsx"
DATA_FOLDER        = r"Daten"
EXCLUDE_SUBSTRINGS = ["Stiftung"]
heute_tag          = dt.date.today().strftime("%y%m%d")

# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Einstellungen")

    date_tag = st.text_input("Date-Tag (yyMMdd)", value=heute_tag)

    mapping = load_mapping(MAPPING_PATH)
    files   = load_all_csvs(DATA_FOLDER, date_tag, EXCLUDE_SUBSTRINGS)

    if not files:
        st.error(f"Keine CSV-Dateien für Tag '{date_tag}' gefunden.")
        st.stop()

    data = build_portfolio_timeseries(files, mapping)

    if not data:
        st.error("Keine Portfolio-Daten geladen.")
        st.stop()

    portfolios    = sorted(data.keys())
    portfolio_sel = st.selectbox("Portfolio", portfolios)

    st.markdown("---")
    show_vorkosten = st.checkbox("Vor Kosten zeigen",  value=True)
    show_benchmark = st.checkbox("Benchmark zeigen",   value=True)

    st.markdown("---")
    fee_default_dec = (float(data[portfolio_sel]["fee_default"].iloc[0])
                       if not data[portfolio_sel].empty else 0.0)
    fee_pct = st.number_input(
        "Kosten p.a. (%)",
        min_value=0.0, max_value=20.0,
        value=float(round(fee_default_dec * 100, 4)),
        step=0.05,
        help="z.B. 1.55 für 1,55 % p.a.",
    )
    fee_dec = fee_pct / 100.0

# ── Portfolio-Daten ────────────────────────────────────────
df_full = data[portfolio_sel].copy()

if df_full.empty:
    st.error("Das gewählte Portfolio enthält keine Daten.")
    st.stop()

min_d = df_full.index.min().date()
max_d = df_full.index.max().date()

# ── Zeitraum-Filter ────────────────────────────────────────
c1, c2, _ = st.columns([1, 1, 2])
with c1:
    start_date = st.date_input("Start", value=min_d,
                               min_value=min_d, max_value=max_d)
with c2:
    end_date   = st.date_input("Ende",  value=max_d,
                               min_value=min_d, max_value=max_d)

if start_date > end_date:
    st.error("Startdatum darf nicht nach dem Enddatum liegen.")
    st.stop()

df = df_full.loc[
    (df_full.index.date >= start_date) &
    (df_full.index.date <= end_date)
].copy()

if df.empty:
    st.warning("Für den gewählten Zeitraum sind keine Daten vorhanden.")
    st.stop()

# ── LINIENGRAFIK ───────────────────────────────────────────
st.subheader("📈 Performance-Index (Start = 100)")

ret_port   = df["ret_port"].fillna(0.0).to_numpy(dtype=float)
idx_after  = make_index_after_fee(ret_port, fee_pa_decimal=fee_dec)
idx_before = make_index_from_returns(ret_port)
x_dates    = [df.index.min() - pd.Timedelta(days=1)] + list(df.index)

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=x_dates, y=idx_after, mode="lines",
    name="Portfolio – nach Kosten",
    line=dict(color="#B8973A", width=2),
))
if show_vorkosten:
    fig_line.add_trace(go.Scatter(
        x=x_dates, y=idx_before, mode="lines",
        name="Portfolio – vor Kosten",
        line=dict(color="#E8C870", width=2, dash="dot"),
    ))
if show_benchmark and df["ret_bm"].notna().any():
    ret_bm = df["ret_bm"].fillna(0.0).to_numpy(dtype=float)
    idx_bm = make_index_from_returns(ret_bm)
    fig_line.add_trace(go.Scatter(
        x=x_dates, y=idx_bm, mode="lines",
        name="Benchmark",
        line=dict(color="#A8CBE8", width=2),
    ))

fig_line.update_layout(
    height=500,
    xaxis_title="Datum",
    yaxis_title="Index (Start = 100)",
    legend_title_text="",
    hovermode="x unified",
    margin=dict(t=30, b=40, l=60, r=20),
)
st.plotly_chart(fig_line, use_container_width=True)

# ── BALKEN-GRAFIK ──────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Performance im Benchmarkvergleich (blockweise)")

left, right = st.columns([1, 3])

with left:
    bar_mode = st.radio(
        "Zeitraum-Einteilung",
        options=["Kalenderjahre", "Quartale", "Benutzerdefiniert"],
        index=0,
    )
    custom_start_bar = None
    custom_end_bar   = None
    if bar_mode == "Benutzerdefiniert":
        custom_start_bar = st.date_input(
            "Von", value=start_date,
            min_value=min_d, max_value=max_d, key="bar_von",
        )
        custom_end_bar = st.date_input(
            "Bis", value=end_date,
            min_value=min_d, max_value=max_d, key="bar_bis",
        )

with right:
    bar_df = compute_bar_data(
        df, fee_dec=fee_dec, mode=bar_mode,
        custom_start=custom_start_bar,
        custom_end=custom_end_bar,
    )

    if bar_df.empty:
        st.info("Keine Daten für diesen Zeitraum.")
    else:
        titel = {
            "Kalenderjahre":     "PERFORMANCE P.A. (NACH KOSTEN) IM BENCHMARKVERGLEICH",
            "Quartale":          "PERFORMANCE QUARTALE (NACH KOSTEN) IM BENCHMARKVERGLEICH",
            "Benutzerdefiniert": "PERFORMANCE (NACH KOSTEN) IM BENCHMARKVERGLEICH – BENUTZERDEFINIERT",
        }[bar_mode]

        st.plotly_chart(
            build_bar_chart(bar_df, titel),
            use_container_width=True,
        )

        with st.expander("🔢 Tabelle anzeigen"):
            disp = bar_df.copy()
            disp["ret_port_after"] = disp["ret_port_after"].map(
                lambda x: f"{x:+.2f}%")
            if "ret_bm" in disp.columns:
                disp["ret_bm"] = disp["ret_bm"].map(
                    lambda x: f"{x:+.2f}%" if pd.notna(x) else "–")
            disp.columns = ["Zeitraum", "Portfolio nach Kosten", "Benchmark"]
            st.dataframe(disp, use_container_width=True, hide_index=True)

# ── DEBUG ──────────────────────────────────────────────────
with st.expander("🔍 Details / Debug"):
    st.write(f"Portfolios geladen: {len(data)}")
    st.write(f"Dateien gefunden: {len(files)}")
    st.write(f"Kosten p.a. (dezimal): {fee_dec:.4f}")
    st.write(f"Datenpunkte im gewählten Zeitraum: {len(df)}")
    st.dataframe(df.head(10))
