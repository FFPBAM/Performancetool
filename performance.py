# streamlit_app.py
import os
import re
import glob
import io
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, PageBreak, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from PIL import Image as PILImage


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
LOGO_FILENAME = "Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg"
FFPB_DARK     = "#1B3A5C"
FFPB_GOLD     = "#B8973A"
FFPB_LIGHT    = "#A8CBE8"
FFPB_BLUE2    = "#2C5F8A"


# ---------------------------------------------------------------------------
# LOGIN AUTHENTICATION
# ---------------------------------------------------------------------------
def check_login() -> bool:
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
    if isinstance(d, pd.Timestamp):
        return d.strftime("%d.%m.%Y")
    if isinstance(d, dt.date):
        return d.strftime("%d.%m.%Y")
    return str(d)


def fmt_pct_de(v: float, decimals: int = 2) -> str:
    """Formatiert einen Dezimalwert als Prozentzahl mit Komma."""
    return f"{v * 100:.{decimals}f}%".replace(".", ",")


def fmt_eur_de(v: float) -> str:
    """Formatiert Euro-Beträge mit Tausenderpunkt und Komma."""
    # z.B. 523456.78 -> "523.456,78 €"
    formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} €"


# ---------------------------------------------------------------------------
# Helpers: Auto-detect newest date tag
# ---------------------------------------------------------------------------
def detect_newest_date_tag(data_folder: str, exclude_substrings: list[str]) -> str:
    all_csvs = glob.glob(os.path.join(data_folder, "*.CSV"))
    tags = set()
    pattern = re.compile(r"_(\d{6})_")
    for f in all_csvs:
        basename = os.path.basename(f)
        if any(sub in basename for sub in exclude_substrings):
            continue
        m = pattern.search(basename)
        if m:
            tags.add(m.group(1))
    if not tags:
        return dt.date.today().strftime("%y%m%d")
    return max(tags)


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
# Helpers: Kennzahlen
# ---------------------------------------------------------------------------
def calc_cagr(idx_after: np.ndarray, n_days: int) -> float | None:
    """CAGR = (Endwert / Startwert)^(365/Tage) - 1"""
    if n_days <= 0 or idx_after[0] == 0:
        return None
    return (idx_after[-1] / idx_after[0]) ** (365.0 / n_days) - 1.0


def calc_vola(daily_returns_after_fee: np.ndarray) -> float | None:
    """Annualisierte Volatilität = Std(Tagesrenditen) × √365"""
    if len(daily_returns_after_fee) < 2:
        return None
    return float(np.std(daily_returns_after_fee, ddof=1) * np.sqrt(365))


def calc_daily_returns_after_fee(d_returns_decimal: np.ndarray, fee_pa_decimal: float) -> np.ndarray:
    """Tagesrenditen nach Kosten."""
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    return d_returns_decimal - e


def calc_max_drawdown(idx_after: np.ndarray, dates_list):
    """Gibt (max_dd_value, max_dd_date) zurück. max_dd_value ist negativ."""
    dd = drawdown_from_index(idx_after)
    min_idx = np.argmin(dd)
    return float(dd[min_idx]), dates_list[min_idx]


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
    idx_before_1, idx_after_1, label_1,
    idx_before_2=None, idx_after_2=None, label_2=None,
    since_label=None
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
# Helpers: Balken-Chart
# ---------------------------------------------------------------------------
def calc_period_return(returns: np.ndarray) -> float:
    return float(np.prod(1.0 + returns) - 1.0)


def calc_period_return_after_fee(returns: np.ndarray, fee_pa_decimal: float) -> float:
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    return float(np.prod(1.0 + (returns - e)) - 1.0)


def compute_bar_data(df, fee_dec, mode, label, custom_start=None, custom_end=None):
    rows = []

    def _add_row(period_label, sub):
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


def build_bar_chart(bar_df1, label_1, bench_name_1,
                    bar_df2=None, label_2=None, bench_name_2=None, title=""):
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
            name=f"{label_1} (nach Kosten)", x=bar_df1["label"], y=vals1,
            marker_color=COLOR_PORT1,
            text=[f"{v:+.2f}%" for v in vals1], textposition="outside",
            textfont=dict(size=11, color="white"), cliponaxis=False,
        ))

    if "ret_bm_raw" in bar_df1.columns and bar_df1["ret_bm_raw"].notna().any():
        bm_vals1 = bar_df1["ret_bm_raw"].tolist()
        fig.add_trace(go.Bar(
            name=bench_name_1, x=bar_df1["label"], y=bm_vals1,
            marker_color=COLOR_BM1,
            text=[f"{v:+.2f}%" if pd.notna(v) else "" for v in bm_vals1],
            textposition="outside", textfont=dict(size=11, color="white"), cliponaxis=False,
        ))

    if bar_df2 is not None and label_2 is not None:
        col_port2 = f"{label_2} (nach Kosten)"
        if col_port2 in bar_df2.columns:
            vals2 = bar_df2[col_port2].tolist()
            fig.add_trace(go.Bar(
                name=f"{label_2} (nach Kosten)", x=bar_df2["label"], y=vals2,
                marker_color=COLOR_PORT2,
                text=[f"{v:+.2f}%" for v in vals2], textposition="outside",
                textfont=dict(size=11, color="white"), cliponaxis=False,
            ))
        if (bench_name_2 and bench_name_2 != bench_name_1
                and "ret_bm_raw" in bar_df2.columns and bar_df2["ret_bm_raw"].notna().any()):
            bm_vals2 = bar_df2["ret_bm_raw"].tolist()
            fig.add_trace(go.Bar(
                name=bench_name_2, x=bar_df2["label"], y=bm_vals2,
                marker_color=COLOR_BM2,
                text=[f"{v:+.2f}%" if pd.notna(v) else "" for v in bm_vals2],
                textposition="outside", textfont=dict(size=11, color="white"), cliponaxis=False,
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
        title=dict(text=f"<b>{title}</b>", font=dict(size=13, color="white"), x=0, xanchor="left"),
        paper_bgcolor=BG, plot_bgcolor=BG,
        barmode="group", bargap=0.28, bargroupgap=0.05, height=480,
        xaxis=dict(tickfont=dict(color="white", size=12), showgrid=False, zeroline=False, linecolor="#3A5A7C"),
        yaxis=dict(range=[y_min, y_max], tickformat=".1f", ticksuffix="%",
                   tickfont=dict(color="white", size=11), gridcolor="#2A4A6C", zeroline=False),
        legend=dict(font=dict(color="white", size=11), bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.18),
        margin=dict(t=55, b=75, l=65, r=25),
    )
    return fig


# ---------------------------------------------------------------------------
# Benchmark-Zusammensetzung
# ---------------------------------------------------------------------------
def show_benchmark_composition(display_name, benchmark_text,
                               display_name_2=None, benchmark_text_2=None):
    if benchmark_text and str(benchmark_text).strip() and str(benchmark_text).strip().lower() not in ("", "nan", "haben keine benchmark"):
        st.caption(f"**Zusammensetzung Benchmark {display_name}:** {benchmark_text}")
    if display_name_2 and benchmark_text_2 and str(benchmark_text_2).strip() and str(benchmark_text_2).strip().lower() not in ("", "nan", "haben keine benchmark"):
        st.caption(f"**Zusammensetzung Benchmark {display_name_2}:** {benchmark_text_2}")


# ---------------------------------------------------------------------------
# Kennzahlen-Anzeige (Streamlit)
# ---------------------------------------------------------------------------
def display_metrics(label, cagr, vola, endwert, use_volume):
    """Zeigt Kennzahlen für ein Portfolio als st.metric-Zeile an."""
    cols = st.columns(4 if use_volume else 3)
    with cols[0]:
        st.metric(
            label=f"⌀ Rendite p.a. (CAGR) – {label}",
            value=fmt_pct_de(cagr) if cagr is not None else "–"
        )
    with cols[1]:
        st.metric(
            label=f"Volatilität p.a. – {label}",
            value=fmt_pct_de(vola) if vola is not None else "–"
        )
    if use_volume and endwert is not None:
        with cols[2]:
            st.metric(
                label=f"Endwert nach Kosten – {label}",
                value=fmt_eur_de(endwert)
            )


def display_drawdown_metrics(label, max_dd_val, max_dd_date):
    """Zeigt Max-Drawdown Kennzahl an."""
    st.markdown(
        f"**Max. Drawdown {label}:** {fmt_pct_de(max_dd_val)} am {fmt_date_de(max_dd_date)}"
    )


# ---------------------------------------------------------------------------
# PDF EXPORT (matplotlib + reportlab)
# ---------------------------------------------------------------------------
def _get_logo_aspect(logo_path):
    if logo_path and os.path.exists(logo_path):
        img = PILImage.open(logo_path)
        w, h = img.size
        return h / w
    return 0.3


def _mpl_line_chart(x_dates, traces, y_label, title, use_volume):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor(FFPB_DARK)
    ax.set_facecolor(FFPB_DARK)

    colors = [FFPB_GOLD, FFPB_BLUE2, "#E8A838", "#5BA0D0", FFPB_LIGHT, "#7FB5D5", "#C4C4C4", "#F0C070"]
    for i, (label, y_vals) in enumerate(traces):
        ax.plot(x_dates, y_vals, label=label, color=colors[i % len(colors)], linewidth=1.3)

    ax.set_title(title, color="white", fontsize=11, fontweight="bold", loc="left")
    ax.set_ylabel(y_label, color="white", fontsize=9)
    ax.tick_params(colors="white", labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=30)
    for spine in ax.spines.values():
        spine.set_color("#3A5A7C")
    ax.grid(axis="y", color="#2A4A6C", linewidth=0.5)
    ax.legend(fontsize=7, facecolor=FFPB_DARK, edgecolor="#3A5A7C", labelcolor="white", loc="upper left")

    if use_volume:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f} €"))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf


def _mpl_drawdown_chart(x_dates, traces, title):
    fig, ax = plt.subplots(figsize=(10, 3))
    fig.patch.set_facecolor(FFPB_DARK)
    ax.set_facecolor(FFPB_DARK)

    colors = [FFPB_GOLD, FFPB_BLUE2]
    for i, (label, y_vals) in enumerate(traces):
        ax.fill_between(x_dates, y_vals, alpha=0.3, color=colors[i % len(colors)])
        ax.plot(x_dates, y_vals, label=label, color=colors[i % len(colors)], linewidth=1.2)

    ax.set_title(title, color="white", fontsize=11, fontweight="bold", loc="left")
    ax.set_ylabel("Drawdown", color="white", fontsize=9)
    ax.tick_params(colors="white", labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))
    fig.autofmt_xdate(rotation=30)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0%}"))
    for spine in ax.spines.values():
        spine.set_color("#3A5A7C")
    ax.grid(axis="y", color="#2A4A6C", linewidth=0.5)
    ax.legend(fontsize=7, facecolor=FFPB_DARK, edgecolor="#3A5A7C", labelcolor="white")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf


def _mpl_bar_chart(bar_df, label, bench_name, title):
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(FFPB_DARK)
    ax.set_facecolor(FFPB_DARK)

    labels = bar_df["label"].tolist()
    col_port = f"{label} (nach Kosten)"
    port_vals = bar_df[col_port].tolist() if col_port in bar_df.columns else []
    bm_vals = bar_df["ret_bm_raw"].tolist() if "ret_bm_raw" in bar_df.columns else []
    has_bm = any(pd.notna(v) for v in bm_vals)

    x = np.arange(len(labels))
    width = 0.35

    if port_vals:
        offset = -width / 2 if has_bm else 0
        bars1 = ax.bar(x + offset, port_vals, width if has_bm else width * 1.5,
                       label=f"{label} (nach Kosten)", color=FFPB_GOLD)
        for bar, v in zip(bars1, port_vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:+.2f}%", ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=7, color="white")

    if has_bm:
        bm_clean = [v if pd.notna(v) else 0 for v in bm_vals]
        bars2 = ax.bar(x + width / 2, bm_clean, width,
                       label=bench_name, color=FFPB_LIGHT)
        for bar, v, orig in zip(bars2, bm_clean, bm_vals):
            if pd.notna(orig):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        f"{v:+.2f}%", ha="center", va="bottom" if v >= 0 else "top",
                        fontsize=7, color="white")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8, color="white", rotation=30, ha="right")
    ax.set_title(title, color="white", fontsize=10, fontweight="bold", loc="left")
    ax.axhline(y=0, color="white", linewidth=0.5)
    ax.tick_params(colors="white", labelsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
    for spine in ax.spines.values():
        spine.set_color("#3A5A7C")
    ax.grid(axis="y", color="#2A4A6C", linewidth=0.5)
    ax.legend(fontsize=7, facecolor=FFPB_DARK, edgecolor="#3A5A7C", labelcolor="white")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_pdf(
    logo_path, label_1, label_2,
    bench_name_1, bench_name_2,
    bench_text_1, bench_text_2,
    fee_pct_1, fee_pct_2,
    anlagevolumen, use_volume,
    start_date, end_date,
    x_dates, line_traces, y_label,
    show_drawdown, dd_traces,
    show_table, df_roll,
    show_bar, bar_data_list,
    metrics_data,
):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "FFPBTitle", parent=styles["Title"],
        textColor=HexColor(FFPB_DARK), fontSize=16, spaceAfter=6,
    )
    style_subtitle = ParagraphStyle(
        "FFPBSub", parent=styles["Heading2"],
        textColor=HexColor(FFPB_DARK), fontSize=12, spaceAfter=4, spaceBefore=10,
    )
    style_normal = ParagraphStyle(
        "FFPBNormal", parent=styles["Normal"],
        textColor=HexColor("#333333"), fontSize=9, leading=12,
    )
    style_small = ParagraphStyle(
        "FFPBSmall", parent=styles["Normal"],
        textColor=HexColor("#666666"), fontSize=7.5, leading=10,
    )

    logo_aspect = _get_logo_aspect(logo_path)
    story = []

    # ── Logo (Seite 1) ──
    if logo_path and os.path.exists(logo_path):
        logo_w = 50 * mm
        logo_h = logo_w * logo_aspect
        story.append(RLImage(logo_path, width=logo_w, height=logo_h))
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Performancevergleich", style_title))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor(FFPB_DARK)))
    story.append(Spacer(1, 3 * mm))

    # ── Meta-Infos ──
    meta_lines = [f"<b>Portfolio:</b> {label_1}"]
    if label_2:
        meta_lines.append(f"<b>Vergleichsportfolio:</b> {label_2}")
    meta_lines.append(f"<b>Zeitraum:</b> {fmt_date_de(start_date)} – {fmt_date_de(end_date)}")
    meta_lines.append(f"<b>Kosten {label_1}:</b> {fee_pct_1:.2f}% p.a.")
    if label_2 and fee_pct_2 is not None:
        meta_lines.append(f"<b>Kosten {label_2}:</b> {fee_pct_2:.2f}% p.a.")
    if use_volume:
        meta_lines.append(f"<b>Anlagevolumen:</b> {fmt_eur_de(anlagevolumen)}")

    for line in meta_lines:
        story.append(Paragraph(line, style_normal))
    story.append(Spacer(1, 4 * mm))

    # ── Kennzahlen ──
    story.append(Paragraph("Kennzahlen", style_subtitle))
    for m in metrics_data:
        line_parts = [f"<b>{m['label']}:</b>"]
        if m.get("cagr") is not None:
            line_parts.append(f"⌀ Rendite p.a. (CAGR): {fmt_pct_de(m['cagr'])}")
        if m.get("vola") is not None:
            line_parts.append(f"Volatilität p.a.: {fmt_pct_de(m['vola'])}")
        if use_volume and m.get("endwert") is not None:
            line_parts.append(f"Endwert nach Kosten: {fmt_eur_de(m['endwert'])}")
        if m.get("max_dd_val") is not None:
            line_parts.append(f"Max. Drawdown: {fmt_pct_de(m['max_dd_val'])} am {fmt_date_de(m['max_dd_date'])}")
        story.append(Paragraph(" | ".join(line_parts), style_normal))
    story.append(Spacer(1, 5 * mm))

    # ── Line Chart ──
    story.append(Paragraph("Performance-Index", style_subtitle))
    line_title = f"Wertentwicklung in Euro (Anlagevolumen: {fmt_eur_de(anlagevolumen)})" if use_volume else "Performance-Index (Start = 100)"
    line_buf = _mpl_line_chart(x_dates, line_traces, y_label, line_title, use_volume)
    story.append(RLImage(line_buf, width=170 * mm, height=80 * mm))
    story.append(Spacer(1, 2 * mm))

    if bench_text_1 and str(bench_text_1).strip().lower() not in ("", "nan", "haben keine benchmark"):
        story.append(Paragraph(f"<b>Zusammensetzung Benchmark {label_1}:</b> {bench_text_1}", style_small))
    if label_2 and bench_text_2 and str(bench_text_2).strip().lower() not in ("", "nan", "haben keine benchmark"):
        story.append(Paragraph(f"<b>Zusammensetzung Benchmark {label_2}:</b> {bench_text_2}", style_small))

    # ── Drawdown ──
    if show_drawdown and dd_traces:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Drawdown (nach Kosten)", style_subtitle))
        dd_buf = _mpl_drawdown_chart(x_dates, dd_traces, "Drawdown (nach Kosten)")
        story.append(RLImage(dd_buf, width=170 * mm, height=60 * mm))

    # ── Rollierende Tabelle ──
    if show_table and df_roll is not None and not df_roll.empty:
        story.append(PageBreak())

        if logo_path and os.path.exists(logo_path):
            logo_w_small = 35 * mm
            story.append(RLImage(logo_path, width=logo_w_small, height=logo_w_small * logo_aspect))
            story.append(Spacer(1, 3 * mm))

        story.append(Paragraph("Wertentwicklung rollierend", style_subtitle))
        story.append(Spacer(1, 2 * mm))

        header = [str(c) if isinstance(c, str) else f"{c[0]}\n{c[1]}" for c in df_roll.columns]
        table_data = [header] + df_roll.values.tolist()

        col_count = len(header)
        first_col_w = 45 * mm
        remaining_w = (170 * mm - first_col_w)
        other_col_w = remaining_w / max(col_count - 1, 1)
        col_widths = [first_col_w] + [other_col_w] * (col_count - 1)

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(FFPB_DARK)),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#F5F5F5")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)

    # ── Balken-Charts ──
    if show_bar and bar_data_list:
        story.append(PageBreak())

        if logo_path and os.path.exists(logo_path):
            logo_w_small = 35 * mm
            story.append(RLImage(logo_path, width=logo_w_small, height=logo_w_small * logo_aspect))
            story.append(Spacer(1, 3 * mm))

        story.append(Paragraph("Performance im Benchmarkvergleich (blockweise)", style_subtitle))

        for bar_df, bar_label, bar_bench, bar_title, bar_bench_text in bar_data_list:
            if bar_df.empty:
                continue
            bar_buf = _mpl_bar_chart(bar_df, bar_label, bar_bench, bar_title)
            story.append(Spacer(1, 3 * mm))
            story.append(RLImage(bar_buf, width=170 * mm, height=75 * mm))
            story.append(Spacer(1, 2 * mm))

            if bar_bench_text and str(bar_bench_text).strip().lower() not in ("", "nan", "haben keine benchmark"):
                story.append(Paragraph(f"<b>Zusammensetzung Benchmark {bar_label}:</b> {bar_bench_text}", style_small))

    # ── Footer ──
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#CCCCCC")))
    story.append(Paragraph(
        f"Erstellt am {fmt_date_de(dt.date.today())} | Fürst Fugger Privatbank",
        style_small
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_mapping(mapping_path):
    return pd.read_excel(mapping_path).round(6)


@st.cache_data(show_spinner=False)
def load_name_mapping(path):
    return pd.read_excel(path)


@st.cache_data(show_spinner=True)
def load_all_csvs(data_folder, date_tag, exclude_substrings):
    pattern = os.path.join(data_folder, f"*_{date_tag}_*.CSV")
    files = glob.glob(pattern)
    files = [p for p in files if not any(sub in os.path.basename(p) for sub in exclude_substrings)]
    return files


def read_one_csv(path):
    return pd.read_csv(path, comment="#", encoding="ISO-8859-1", delimiter=";", decimal=",", thousands=".", dtype=str)


def parse_dates_col(vv):
    return pd.to_datetime(vv["Datum"], format="%d.%m.%Y", errors="raise")


def extract_benchmark_name(vv):
    candidates = ["Benchmark Name", "Benchmark", "Benchmarkname", "Benchmark Name ", "Benchmark-Bezeichnung"]
    for c in candidates:
        if c in vv.columns:
            val = vv.loc[0, c]
            if pd.notna(val) and str(val).strip():
                return str(val).strip()
    return "Benchmark"


@st.cache_data(show_spinner=True)
def build_portfolio_timeseries(files, mapping):
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
NAME_MAPPING_PATH = r"Mapping_Namen.xlsx"
DATA_FOLDER       = r"Daten"
exclude_substrings = ["Stiftung"]

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Einstellungen")

    auto_tag = detect_newest_date_tag(DATA_FOLDER, exclude_substrings)
    date_tag = st.text_input("Date-Tag (yyMMdd)", value=auto_tag,
                             help="Wird automatisch auf den neuesten verfügbaren Tag gesetzt.")

    mapping      = load_mapping(MAPPING_PATH)
    name_mapping = load_name_mapping(NAME_MAPPING_PATH)
    files        = load_all_csvs(DATA_FOLDER, date_tag, exclude_substrings)

    if len(files) == 0:
        st.error(f"Keine Dateien gefunden für Tag {date_tag}. Pattern: *_{date_tag}_*.CSV")
        st.stop()

    data = build_portfolio_timeseries(files, mapping)

    # ── Name-Mapping ───────────────────────────────────────────────────────
    col_display = name_mapping.columns[0]
    col_csv_key = name_mapping.columns[1]
    col_bench   = name_mapping.columns[3]

    available_csv_names = set(data.keys())
    name_mapping_filtered = name_mapping[
        name_mapping[col_csv_key].isin(available_csv_names)
    ].copy()

    display_names_ordered = name_mapping_filtered[col_display].tolist()
    display_to_csv = dict(zip(name_mapping_filtered[col_display], name_mapping_filtered[col_csv_key]))
    display_to_benchmark = dict(zip(name_mapping_filtered[col_display], name_mapping_filtered[col_bench]))

    if len(display_names_ordered) == 0:
        st.error("Keine Portfolios aus Mapping_Namen.xlsx konnten den geladenen CSV-Daten zugeordnet werden.")
        st.stop()

    display_sel_1 = st.selectbox("Portfolio auswählen", display_names_ordered)
    portfolio_sel = display_to_csv[display_sel_1]

    show_compare = st.checkbox("Vergleichsportfolio anzeigen", value=False)
    portfolio_sel2 = None
    display_sel_2 = None
    if show_compare:
        display_sel_2 = st.selectbox("Vergleichsportfolio auswählen", display_names_ordered)
        portfolio_sel2 = display_to_csv[display_sel_2]

    show_vorkosten = st.checkbox("Vor Kosten anzeigen",                   value=True)
    show_benchmark = st.checkbox("Benchmark anzeigen",                    value=True)
    show_drawdown  = st.checkbox("Drawdown (nach Kosten) anzeigen",       value=False)
    show_table     = st.checkbox("Tabelle: Wertentwicklung rollierend",   value=True)
    show_bar       = st.checkbox("Balken-Chart: Performance blockweise",  value=True)

    # ── Anlagevolumen ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Anlagevolumen")
    anlagevolumen = st.number_input(
        "Anlagevolumen in € (optional)",
        min_value=0.0, max_value=1_000_000_000.0, value=0.0, step=10_000.0,
        format="%.2f",
        help="Wenn > 0: Chart zeigt Wertentwicklung in Euro. Sonst Index ab 100."
    )
    use_volume = anlagevolumen > 0

    st.markdown("---")

    # ── Kosten ─────────────────────────────────────────────────────────────
    fee_default_dec_1 = float(data[portfolio_sel]["fee_default"].iloc[0]) if len(data[portfolio_sel]) else 0.0
    fee_pct_1 = st.number_input(
        f"Kosten p.a. (%) – {display_sel_1}",
        min_value=0.0, max_value=20.0,
        value=float(round(fee_default_dec_1 * 100, 4)), step=0.05,
        help="Eingabe in Prozent p.a. (z.B. 1,55)."
    )
    fee_dec_1 = fee_pct_1 / 100.0

    fee_dec_2 = None
    fee_pct_2 = None
    if show_compare and portfolio_sel2:
        fee_default_dec_2 = float(data[portfolio_sel2]["fee_default"].iloc[0]) if len(data[portfolio_sel2]) else 0.0
        fee_pct_2 = st.number_input(
            f"Kosten p.a. (%) – {display_sel_2}",
            min_value=0.0, max_value=20.0,
            value=float(round(fee_default_dec_2 * 100, 4)), step=0.05,
        )
        fee_dec_2 = fee_pct_2 / 100.0


# ── Labels ─────────────────────────────────────────────────────────────────
label_1 = display_sel_1
label_2 = display_sel_2 if (show_compare and display_sel_2) else None


# ── Zeitraum ──────────────────────────────────────────────────────────────
df1 = data[portfolio_sel].copy()
min_d, max_d = df1.index.min().date(), df1.index.max().date()

st.markdown("#### Zeitraum auswählen")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Start", value=min_d, min_value=min_d, max_value=max_d,
        format="DD.MM.YYYY", key="start_date_picker"
    )
with col2:
    end_date = st.date_input(
        "Ende", value=max_d, min_value=min_d, max_value=max_d,
        format="DD.MM.YYYY", key="end_date_picker"
    )

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

idx_after_2 = idx_before_2 = None
if df2 is not None:
    ret2         = df2["ret_port"].to_numpy(dtype=float)
    idx_after_2  = make_index_after_fee(ret2, float(fee_dec_2), startwert=startwert)
    idx_before_2 = make_index_from_returns(ret2, startwert=startwert)

x_dates = [df1.index.min() - pd.Timedelta(days=1)] + list(df1.index)

# Für rollierende Tabelle immer Basis 100
ret1_t = df1["ret_port"].to_numpy(dtype=float)
s_before_1_tbl = pd.Series(make_index_from_returns(ret1_t, 100.0), index=pd.to_datetime(x_dates))
s_after_1_tbl  = pd.Series(make_index_after_fee(ret1_t, fee_dec_1, 100.0), index=pd.to_datetime(x_dates))
s_before_2_tbl = s_after_2_tbl = None
if df2 is not None:
    ret2_t = df2["ret_port"].to_numpy(dtype=float)
    s_before_2_tbl = pd.Series(make_index_from_returns(ret2_t, 100.0), index=pd.to_datetime(x_dates))
    s_after_2_tbl  = pd.Series(make_index_after_fee(ret2_t, float(fee_dec_2), 100.0), index=pd.to_datetime(x_dates))

bench_name_1 = data[portfolio_sel].attrs.get("benchmark_name", "Benchmark")
bench_name_2 = data[portfolio_sel2].attrs.get("benchmark_name", "Benchmark") if (show_compare and portfolio_sel2) else None

bench_text_1 = display_to_benchmark.get(display_sel_1, "")
bench_text_2 = display_to_benchmark.get(display_sel_2, "") if display_sel_2 else ""


# ── Kennzahlen berechnen ──────────────────────────────────────────────────
n_days_1 = len(ret1)
daily_ret_af_1 = calc_daily_returns_after_fee(ret1, fee_dec_1)
cagr_1  = calc_cagr(idx_after_1, n_days_1)
vola_1  = calc_vola(daily_ret_af_1)
endwert_1 = float(idx_after_1[-1]) if use_volume else None

# Drawdown-Kennzahlen (immer berechnen, nur anzeigen wenn aktiviert)
# Für Drawdown Basis 100 verwenden (relativ)
idx_af_1_100 = make_index_after_fee(ret1, fee_dec_1, startwert=100.0)
max_dd_val_1, max_dd_date_1 = calc_max_drawdown(idx_af_1_100, x_dates)

cagr_2 = vola_2 = endwert_2 = max_dd_val_2 = max_dd_date_2 = None
if df2 is not None:
    n_days_2 = len(ret2)
    daily_ret_af_2 = calc_daily_returns_after_fee(ret2, float(fee_dec_2))
    cagr_2  = calc_cagr(idx_after_2, n_days_2)
    vola_2  = calc_vola(daily_ret_af_2)
    endwert_2 = float(idx_after_2[-1]) if use_volume else None

    idx_af_2_100 = make_index_after_fee(ret2, float(fee_dec_2), startwert=100.0)
    max_dd_val_2, max_dd_date_2 = calc_max_drawdown(idx_af_2_100, x_dates)

# Metrics-Daten für PDF sammeln
metrics_data = [{
    "label": label_1,
    "cagr": cagr_1,
    "vola": vola_1,
    "endwert": endwert_1,
    "max_dd_val": max_dd_val_1 if show_drawdown else None,
    "max_dd_date": max_dd_date_1 if show_drawdown else None,
}]
if df2 is not None and label_2:
    metrics_data.append({
        "label": label_2,
        "cagr": cagr_2,
        "vola": vola_2,
        "endwert": endwert_2,
        "max_dd_val": max_dd_val_2 if show_drawdown else None,
        "max_dd_date": max_dd_date_2 if show_drawdown else None,
    })


# ── Kennzahlen über dem Linien-Chart ──────────────────────────────────────
st.subheader("📊 Kennzahlen (nach Kosten)")
display_metrics(label_1, cagr_1, vola_1, endwert_1, use_volume)
if df2 is not None and label_2:
    display_metrics(label_2, cagr_2, vola_2, endwert_2, use_volume)


# ── Chart: Index / Volumen ─────────────────────────────────────────────────
if use_volume:
    st.subheader(f"📈 Wertentwicklung in Euro (Anlagevolumen: {fmt_eur_de(anlagevolumen)})")
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

fig.update_layout(
    height=550,
    xaxis_title="Datum",
    xaxis=dict(tickformat="%d.%m.%Y"),
    yaxis_title=y_label,
    yaxis=dict(tickformat=",.2f" if use_volume else None),
    legend_title_text="Reihen",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

if show_benchmark:
    show_benchmark_composition(label_1, bench_text_1, label_2, bench_text_2)


# ── Drawdown ───────────────────────────────────────────────────────────────
if show_drawdown:
    # ── Max Drawdown Kennzahlen über dem Chart ──
    st.markdown("---")
    display_drawdown_metrics(label_1, max_dd_val_1, max_dd_date_1)
    if df2 is not None and label_2:
        display_drawdown_metrics(label_2, max_dd_val_2, max_dd_date_2)

    fig_dd = go.Figure()
    dd1 = drawdown_from_index(idx_af_1_100)
    fig_dd.add_trace(go.Scatter(x=x_dates, y=dd1, mode="lines",
                                name=f"{label_1} – Drawdown (nach Kosten)"))
    if df2 is not None:
        dd2 = drawdown_from_index(idx_af_2_100)
        fig_dd.add_trace(go.Scatter(x=x_dates, y=dd2, mode="lines",
                                    name=f"{label_2} – Drawdown (nach Kosten)"))
    fig_dd.update_layout(
        height=350, xaxis_title="Datum",
        xaxis=dict(tickformat="%d.%m.%Y"),
        yaxis_title="Drawdown", hovermode="x unified",
    )
    st.plotly_chart(fig_dd, use_container_width=True)


# ── Rollierende Tabelle ───────────────────────────────────────────────────
df_roll = None
if show_table:
    since_label = f"Wertentwicklung seit: {fmt_date_de(df1.index.min())}"
    df_roll = build_rolling_table(
        idx_before_1=s_before_1_tbl, idx_after_1=s_after_1_tbl, label_1=label_1,
        idx_before_2=s_before_2_tbl, idx_after_2=s_after_2_tbl, label_2=label_2,
        since_label=since_label
    )
    st.subheader("📋 Wertentwicklung rollierend")
    st.dataframe(df_roll, use_container_width=True)


# ── Balken-Chart ───────────────────────────────────────────────────────────
bar_data_list_for_pdf = []

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
        custom_start_bar = custom_end_bar = None
        if bar_mode == "Benutzerdefiniert":
            custom_start_bar = st.date_input(
                "Von", value=start_date, min_value=min_d, max_value=max_d,
                format="DD.MM.YYYY", key="bar_von"
            )
            custom_end_bar = st.date_input(
                "Bis", value=end_date, min_value=min_d, max_value=max_d,
                format="DD.MM.YYYY", key="bar_bis"
            )

    titel_map = {
        "Kalenderjahre":     "PERFORMANCE P.A. (NACH KOSTEN) IM BENCHMARKVERGLEICH",
        "Quartale":          "PERFORMANCE QUARTALE (NACH KOSTEN) IM BENCHMARKVERGLEICH",
        "Benutzerdefiniert": "PERFORMANCE (NACH KOSTEN) IM BENCHMARKVERGLEICH – BENUTZERDEFINIERT",
    }

    def _render_bar(df_src, fee, label, bench_name, bench_text, container):
        bar_df = compute_bar_data(
            df_src, fee_dec=fee, mode=bar_mode, label=label,
            custom_start=custom_start_bar, custom_end=custom_end_bar,
        )
        if bar_df.empty:
            container.info(f"Keine Daten für {label}.")
            return
        bar_title = f"{titel_map[bar_mode]} – {label}"
        bar_data_list_for_pdf.append((bar_df, label, bench_name, bar_title, bench_text))

        bar_fig = build_bar_chart(bar_df1=bar_df, label_1=label, bench_name_1=bench_name, title=bar_title)
        container.plotly_chart(bar_fig, use_container_width=True)
        with container.expander("🔢 Tabelle anzeigen"):
            col_p = f"{label} (nach Kosten)"
            disp = bar_df[["label", col_p, "ret_bm_raw"]].copy()
            disp[col_p]        = disp[col_p].map(lambda x: f"{x:+.2f}%")
            disp["ret_bm_raw"] = disp["ret_bm_raw"].map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "–")
            disp.columns = ["Zeitraum", f"{label} nach Kosten", bench_name]
            container.dataframe(disp, use_container_width=True, hide_index=True)

    with bar_right:
        _render_bar(df1, fee_dec_1, label_1, bench_name_1, bench_text_1, st.container())
        if show_benchmark:
            show_benchmark_composition(label_1, bench_text_1)

        if df2 is not None and fee_dec_2 is not None and portfolio_sel2:
            st.markdown("---")
            _render_bar(df2, fee_dec_2, label_2, bench_name_2 or "Benchmark", bench_text_2 or "", st.container())
            if show_benchmark:
                show_benchmark_composition(label_2, bench_text_2)


# ── PDF Download Button ───────────────────────────────────────────────────
st.markdown("---")

# Sammle Line-Traces für PDF
pdf_line_traces = []
pdf_line_traces.append((f"{label_1} – nach Kosten ({fee_pct_1:.2f}%)", idx_after_1))
if idx_after_2 is not None:
    pdf_line_traces.append((f"{label_2} – nach Kosten ({(fee_pct_2 or 0.0):.2f}%)", idx_after_2))
if show_vorkosten:
    pdf_line_traces.append((f"{label_1} – vor Kosten", idx_before_1))
    if idx_before_2 is not None:
        pdf_line_traces.append((f"{label_2} – vor Kosten", idx_before_2))
if show_benchmark and df1["ret_bm"].notna().any():
    ret_bm_1_pdf = df1["ret_bm"].fillna(0.0).to_numpy(dtype=float)
    idx_bm_1_pdf = make_index_from_returns(ret_bm_1_pdf, startwert=startwert)
    pdf_line_traces.append((f"Benchmark {label_1}: {bench_name_1}", idx_bm_1_pdf))
    if df2 is not None and df2["ret_bm"].notna().any():
        ret_bm_2_pdf = df2["ret_bm"].fillna(0.0).to_numpy(dtype=float)
        idx_bm_2_pdf = make_index_from_returns(ret_bm_2_pdf, startwert=startwert)
        pdf_line_traces.append((f"Benchmark {label_2}: {bench_name_2}", idx_bm_2_pdf))

# Drawdown Traces
pdf_dd_traces = []
if show_drawdown:
    pdf_dd_traces.append((f"{label_1} – Drawdown", drawdown_from_index(idx_af_1_100)))
    if df2 is not None:
        pdf_dd_traces.append((f"{label_2} – Drawdown", drawdown_from_index(idx_af_2_100)))

# Logo-Pfad
logo_path = LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else None

if st.button("📄 PDF Report erstellen"):
    with st.spinner("PDF wird erstellt..."):
        pdf_bytes = generate_pdf(
            logo_path=logo_path,
            label_1=label_1, label_2=label_2,
            bench_name_1=bench_name_1, bench_name_2=bench_name_2,
            bench_text_1=bench_text_1, bench_text_2=bench_text_2,
            fee_pct_1=fee_pct_1, fee_pct_2=fee_pct_2,
            anlagevolumen=anlagevolumen, use_volume=use_volume,
            start_date=start_date, end_date=end_date,
            x_dates=x_dates,
            line_traces=pdf_line_traces, y_label=y_label,
            show_drawdown=show_drawdown, dd_traces=pdf_dd_traces,
            show_table=show_table, df_roll=df_roll,
            show_bar=show_bar, bar_data_list=bar_data_list_for_pdf,
            metrics_data=metrics_data,
        )

    filename = f"Performance_{label_1}_{fmt_date_de(start_date)}-{fmt_date_de(end_date)}.pdf"
    st.download_button(
        label="⬇️ PDF herunterladen",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
    )
    st.success("PDF erfolgreich erstellt!")


# ── Debug ──────────────────────────────────────────────────────────────────
with st.expander("Details / Debug"):
    st.write("Gefundene Dateien:", len(files))
    st.write("Auto-Tag:", auto_tag)
    st.write("Zeitraum:", fmt_date_de(start_date), "bis", fmt_date_de(end_date))
    st.write(f"Kosten {label_1} (dezimal):", fee_dec_1)
    if df2 is not None:
        st.write(f"Kosten {label_2} (dezimal):", fee_dec_2)
    st.write("Benchmark-Name 1:", bench_name_1)
    st.write("Benchmark-Text 1:", bench_text_1)
    if df2 is not None:
        st.write("Benchmark-Name 2:", bench_name_2)
        st.write("Benchmark-Text 2:", bench_text_2)
    st.write(f"Anlagevolumen: {fmt_eur_de(anlagevolumen)}" if use_volume else "Anlagevolumen: nicht gesetzt (Index 100)")
    st.write("CAGR 1:", fmt_pct_de(cagr_1) if cagr_1 else "–")
    st.write("Vola 1:", fmt_pct_de(vola_1) if vola_1 else "–")
    st.write(f"Max DD 1: {fmt_pct_de(max_dd_val_1)} am {fmt_date_de(max_dd_date_1)}")
    st.write("Rows Portfolio 1:", len(df1))
    if df2 is not None:
        st.write("Rows Portfolio 2:", len(df2))
    st.dataframe(df1.head(10))
