# modules/portfolioanalyse.py
"""Portfolioanalyse: Bestands- und Allokationsübersicht."""

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
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, PageBreak, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white

from modules.shared import (
    FFPB_DARK, FFPB_GOLD, FFPB_LIGHT, FFPB_BLUE2,
    DATA_FOLDER, DATA_FOLDER_PF, DURATION_FOLDER, EXCLUDE_SUBSTRINGS,
    PDF_FONT, PDF_FONT_BOLD,
    fmt_date_de, fmt_pct_de, fmt_eur_de,
    detect_newest_date_tag, get_logo_aspect, get_logo_path,
    csv_name_to_display, load_mapping,
    load_all_csvs, build_portfolio_timeseries,
)


# ---------------------------------------------------------------------------
# Ring-Chart Farben (Corporate: Fuggerblau #003460, Fuggergold #C3A069)
# ---------------------------------------------------------------------------
RING_COLORS = [
    "#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8",
    "#8B7340", "#A8CBE8", "#5C6B3C", "#E8D5B0", "#2C5F8A",
    "#C4C4C4", "#3A7CA5", "#F0C070", "#6A9BC3", "#2A4A6C",
]
SONSTIGE_THRESHOLD = 0.03  # Kategorien unter 3% → "Sonstige"


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def load_pf_csvs(data_folder: str, date_tag: str) -> list:
    files = []
    for ext in ["*.CSV", "*.csv"]:
        all_files = glob.glob(os.path.join(data_folder, ext))
        for f in all_files:
            if date_tag in os.path.basename(f):
                files.append(f)
    return list(set(files))


def read_pf_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(
        path, comment="#", encoding="ISO-8859-1",
        delimiter=";", decimal=",", thousands=".", dtype=str
    )


def parse_pf_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Alle String-Spalten bereinigen (trim, nan-safe)
    for col in ["Wertpapier", "WKN", "ISIN", "Segment", "Region", "Gattung", "Portfolio Name"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("nan", np.nan)

    for col in ["Gewicht", "Performancebeitrag", "WP-Performance", "Kupon"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("%", "").str.replace(",", ".").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0
    if "Auswertungsdatum" in df.columns:
        df["Auswertungsdatum"] = pd.to_datetime(df["Auswertungsdatum"], format="%d.%m.%Y", errors="coerce")
    if "Fälligkeit" in df.columns:
        df["Fälligkeit_parsed"] = pd.to_datetime(df["Fälligkeit"], format="%d.%m.%Y", errors="coerce")
    return df


@st.cache_data(show_spinner=True)
def build_pf_data(files: list[str]) -> dict:
    out = {}
    for path in files:
        df = read_pf_csv(path)
        if "Portfolio Name" not in df.columns or df.empty:
            continue
        portfolio_name = df["Portfolio Name"].iloc[0].strip()
        df = parse_pf_data(df)
        out[portfolio_name] = df
    return out


# ---------------------------------------------------------------------------
# Duration Loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_duration_data(duration_folder: str, name_mapping: pd.DataFrame) -> dict:
    """
    Lädt die neueste Duration-Datei und gibt ein Dict zurück:
    {csv_portfolio_name: {"duration": float, "rendite": float}}
    Zuordnung über Spalte C (Duration-Name) im Mapping.
    """
    # Neueste Datei finden
    all_files = glob.glob(os.path.join(duration_folder, "*.CSV")) + \
                glob.glob(os.path.join(duration_folder, "*.csv"))
    if not all_files:
        return {}

    # Nach Zeitstempel im Namen sortieren (neueste zuerst)
    tag_pattern = re.compile(r"_(\d{6})_(\d{4})")
    def _sort_key(f):
        m = tag_pattern.search(os.path.basename(f))
        return m.group(1) + m.group(2) if m else "000000_0000"
    all_files.sort(key=_sort_key, reverse=True)
    newest = all_files[0]

    # CSV lesen
    try:
        df = pd.read_csv(newest, comment="#", encoding="ISO-8859-1",
                         delimiter=";", decimal=",", thousands=".", dtype=str)
    except Exception:
        # Auch Tab-getrennt oder Excel probieren
        try:
            df = pd.read_csv(newest, comment="#", encoding="UTF-8",
                             delimiter="\t", decimal=",", thousands=".", dtype=str)
        except Exception:
            return {}

    if "Wertpapier" not in df.columns or "Duration" not in df.columns:
        return {}

    # Rendite parsen
    if "Rendite" in df.columns:
        df["Rendite"] = df["Rendite"].astype(str).str.replace("%", "").str.replace(",", ".").str.strip()
        df["Rendite"] = pd.to_numeric(df["Rendite"], errors="coerce") / 100.0
    df["Duration"] = pd.to_numeric(df["Duration"].astype(str).str.replace(",", "."), errors="coerce")

    # Mapping: Spalte C (Duration-Name) → Spalte B (CSV-Key)
    col_csv_key = name_mapping.columns[1]   # "Honorarsatz Mapping"
    col_duration = name_mapping.columns[2]  # "Duration" (Spalte C)
    duration_to_csv = dict(zip(name_mapping[col_duration], name_mapping[col_csv_key]))

    result = {}
    for _, row in df.iterrows():
        dur_name = str(row["Wertpapier"]).strip()
        csv_name = duration_to_csv.get(dur_name)
        if csv_name:
            entry = {"duration": row["Duration"] if pd.notna(row["Duration"]) else None}
            if "Rendite" in df.columns:
                entry["rendite"] = row["Rendite"] if pd.notna(row["Rendite"]) else None
            else:
                entry["rendite"] = None
            result[csv_name] = entry
    return result


# ---------------------------------------------------------------------------
# Berechnungen
# ---------------------------------------------------------------------------
def calc_liquidity(df: pd.DataFrame) -> float:
    total_weight = df["Gewicht"].sum()
    return max(0.0, 1.0 - total_weight)


def build_allocation(df: pd.DataFrame, group_col: str, sonstige_threshold: float = SONSTIGE_THRESHOLD) -> pd.DataFrame:
    """Aggregiert Gewichte nach Gruppierung + Liquidität. Kleine Kategorien → Sonstige."""
    if group_col not in df.columns:
        return pd.DataFrame()
    agg = df.groupby(group_col)["Gewicht"].sum().reset_index()
    agg.columns = [group_col, "Gewicht"]
    agg = agg.sort_values("Gewicht", ascending=False).reset_index(drop=True)

    # Kleine Positionen zusammenfassen
    big = agg[agg["Gewicht"] >= sonstige_threshold]
    small = agg[agg["Gewicht"] < sonstige_threshold]
    if len(small) > 1:
        sonstige_weight = small["Gewicht"].sum()
        sonstige_row = pd.DataFrame([{group_col: "Sonstige", "Gewicht": sonstige_weight}])
        agg = pd.concat([big, sonstige_row], ignore_index=True)
    elif len(small) == 1:
        agg = pd.concat([big, small], ignore_index=True)
    else:
        agg = big.reset_index(drop=True)

    # Liquidität
    liq = calc_liquidity(df)
    if liq > 0.0001:
        agg = pd.concat([agg, pd.DataFrame([{group_col: "Liquidität", "Gewicht": liq}])], ignore_index=True)

    return agg


def build_grouped_title_table(df: pd.DataFrame, anlagevolumen: float = 0.0, show_ytd: bool = False):
    """
    Baut Tabellen-Daten gruppiert nach Gattung auf.
    Returns: list of (gattung_name, display_dataframe)
    """
    if "Gattung" not in df.columns:
        return []

    base_cols = ["Wertpapier", "WKN", "Gewicht", "Segment", "Region"]
    has_kupon = "Kupon" in df.columns and df["Kupon"].notna().any() and (df["Kupon"] != 0).any()
    has_faelligkeit = "Fälligkeit_parsed" in df.columns and df["Fälligkeit_parsed"].notna().any()
    has_perf = show_ytd and "WP-Performance" in df.columns and df["WP-Performance"].notna().any()
    has_beitrag = show_ytd and "Performancebeitrag" in df.columns and df["Performancebeitrag"].notna().any()
    use_volume = anlagevolumen > 0

    groups = []
    gattung_order = df.groupby("Gattung")["Gewicht"].sum().sort_values(ascending=False).index.tolist()

    for gattung in gattung_order:
        sub = df[df["Gattung"] == gattung].copy()
        sub = sub.sort_values("Gewicht", ascending=False)

        available = [c for c in base_cols if c in sub.columns]
        result = sub[available].copy()

        # Anleihen-spezifische Spalten nur bei Renten
        is_bond = "rente" in gattung.lower() or "anleihe" in gattung.lower() or "bond" in gattung.lower()
        if is_bond and has_kupon:
            result["Kupon"] = sub["Kupon"]
        if is_bond and has_faelligkeit:
            result["Fälligkeit"] = sub["Fälligkeit_parsed"].apply(lambda x: fmt_date_de(x) if pd.notna(x) else "–")
        if has_perf:
            result["Wertpapier-Performance (YTD)"] = sub["WP-Performance"]
        if has_beitrag:
            result["Performancebeitrag (YTD)"] = sub["Performancebeitrag"]
        if use_volume:
            result["Investiert (€)"] = sub["Gewicht"] * anlagevolumen

        # Formatieren
        disp = result.copy()
        if "Gewicht" in disp.columns:
            disp["Gewicht"] = disp["Gewicht"].apply(lambda x: fmt_pct_de(x) if isinstance(x, (int, float)) and not pd.isna(x) else "–")
        if "Kupon" in disp.columns:
            disp["Kupon"] = disp["Kupon"].apply(lambda x: fmt_pct_de(x) if isinstance(x, (int, float)) and not pd.isna(x) and x != 0 else "–")
        if "Wertpapier-Performance (YTD)" in disp.columns:
            disp["Wertpapier-Performance (YTD)"] = disp["Wertpapier-Performance (YTD)"].apply(lambda x: fmt_pct_de(x) if isinstance(x, (int, float)) and not pd.isna(x) else "–")
        if "Performancebeitrag (YTD)" in disp.columns:
            disp["Performancebeitrag (YTD)"] = disp["Performancebeitrag (YTD)"].apply(lambda x: fmt_pct_de(x) if isinstance(x, (int, float)) and not pd.isna(x) else "–")
        if "Investiert (€)" in disp.columns:
            disp["Investiert (€)"] = disp["Investiert (€)"].apply(lambda x: fmt_eur_de(x) if isinstance(x, (int, float)) and not pd.isna(x) else "–")

        # Gattung-Gewicht für Header
        gattung_weight = sub["Gewicht"].sum()
        groups.append((gattung, gattung_weight, disp))

    # Liquidität
    liq = calc_liquidity(df)
    if liq > 0.0001:
        liq_data = {"Wertpapier": "Liquidität", "Gewicht": fmt_pct_de(liq)}
        if use_volume:
            liq_data["Investiert (€)"] = fmt_eur_de(liq * anlagevolumen)
        groups.append(("💰 Liquidität", liq, pd.DataFrame([liq_data])))

    return groups


def get_top_holdings(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Top N Positionen nach Gewicht."""
    return df.nlargest(n, "Gewicht")[["Wertpapier", "WKN", "Gewicht", "Gattung"]].copy()


def get_top_flop(df: pd.DataFrame, col: str, n: int = 5):
    valid = df[df[col].notna() & (df[col] != 0)].copy()
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame()
    top = valid.nlargest(n, col)[["Wertpapier", "WKN", "Gewicht", col]].copy()
    flop = valid.nsmallest(n, col)[["Wertpapier", "WKN", "Gewicht", col]].copy()
    return top, flop


def get_bond_summary(df: pd.DataFrame) -> dict:
    bonds = df[df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty:
        return None
    summary = {"count": len(bonds)}
    if "Kupon" in bonds.columns and bonds["Kupon"].notna().any():
        w = bonds["Gewicht"].fillna(0); k = bonds["Kupon"].fillna(0)
        summary["avg_kupon"] = float((w * k).sum() / w.sum()) if w.sum() > 0 else None
    else:
        summary["avg_kupon"] = None
    if "Fälligkeit_parsed" in bonds.columns and bonds["Fälligkeit_parsed"].notna().any():
        faell = bonds[bonds["Fälligkeit_parsed"].notna()].copy()
        faell["Jahr"] = faell["Fälligkeit_parsed"].dt.year
        summary["faelligkeit"] = faell.groupby("Jahr")["Gewicht"].sum().reset_index()
        summary["faelligkeit"].columns = ["Jahr", "Gewicht"]
    else:
        summary["faelligkeit"] = None
    summary["total_weight"] = float(bonds["Gewicht"].sum())
    return summary


# ---------------------------------------------------------------------------
# Ring-Diagramm (Plotly) – Labels außerhalb, Corporate Design
# ---------------------------------------------------------------------------
def build_ring_chart(alloc_df: pd.DataFrame, group_col: str, title: str) -> go.Figure:
    # Absteigend sortieren (größter Block zuerst)
    sorted_df = alloc_df.sort_values("Gewicht", ascending=False).reset_index(drop=True)
    labels = sorted_df[group_col].tolist()
    values = sorted_df["Gewicht"].tolist()
    total = sum(values) if sum(values) > 0 else 1.0

    # Kleine Segmente leicht herausziehen
    pull = [0.03 if v / total < 0.05 else 0 for v in values]

    # Labels: außerhalb, unter 3% ausblenden
    text_info = []
    for v in values:
        pct = v / total
        if pct >= 0.03:
            text_info.append(f"{pct:.1%}".replace(".", ","))
        else:
            text_info.append("")

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(
            colors=RING_COLORS[:len(sorted_df)],
            line=dict(color="white", width=2),
        ),
        textinfo="text",
        text=text_info,
        textposition="outside",
        textfont=dict(size=13, color="#333333"),
        pull=pull,
        hovertemplate="<b>%{label}</b><br>Gewicht: %{percent}<extra></extra>",
        sort=False,
        rotation=90,
        direction="clockwise",
    )])

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=13, color="#003460"), x=0.5, xanchor="center"),
        height=420,
        showlegend=True,
        legend=dict(
            font=dict(size=10),
            orientation="h",
            y=-0.15,
            x=0.5,
            xanchor="center",
        ),
        margin=dict(t=50, b=80, l=40, r=40),
        uniformtext=dict(minsize=11, mode="hide"),
    )
    return fig


# ---------------------------------------------------------------------------
# Top 5 Holdings Säulendiagramm (Plotly)
# ---------------------------------------------------------------------------
TOP5_COLORS = ["#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8"]


def build_top5_bar_chart(top5: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure(data=[go.Bar(
        x=top5["Wertpapier"],
        y=top5["Gewicht"] * 100,
        marker_color=TOP5_COLORS[:len(top5)],
        text=[f"{v*100:.1f}%" for v in top5["Gewicht"]],
        textposition="outside",
        textfont=dict(size=11),
    )])
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=13, color="#003460")),
        height=350,
        xaxis=dict(tickfont=dict(size=10), tickangle=-25),
        yaxis=dict(title="Gewicht (%)", ticksuffix="%"),
        margin=dict(t=50, b=80, l=50, r=20),
    )
    return fig


# ---------------------------------------------------------------------------
# Ring-Diagramm für PDF (matplotlib)
# ---------------------------------------------------------------------------
def _mpl_ring_chart(alloc_df, group_col, title):
    # Absteigend sortieren
    sorted_df = alloc_df.sort_values("Gewicht", ascending=False).reset_index(drop=True)
    labels = sorted_df[group_col].tolist()
    sizes = sorted_df["Gewicht"].tolist()
    total = sum(sizes) if sum(sizes) > 0 else 1.0
    colors = RING_COLORS[:len(sorted_df)]

    fig, ax = plt.subplots(figsize=(5, 4))

    # Kleine Segmente herausziehen
    explode = [0.03 if s / total < 0.05 else 0 for s in sizes]

    # Labels: Name + Prozent für >= 3%, leer für < 3%
    def _make_label(pct):
        return f"{pct:.1f}%" if pct >= 3.0 else ""

    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct=_make_label, startangle=90, colors=colors,
        pctdistance=1.15, explode=explode, counterclock=False,
        wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2))
    for t in autotexts: t.set_fontsize(9); t.set_color("#333333")
    ax.set_title(title, fontsize=11, fontweight="bold", color="#003460", pad=10)

    # Legende horizontal unten
    ax.legend(labels, loc="upper center", bbox_to_anchor=(0.5, -0.05),
              fontsize=7, ncol=min(len(labels), 3), frameon=False)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig); buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Streamlit Rendering
# ---------------------------------------------------------------------------
def render_portfolioanalyse(name_mapping: pd.DataFrame, anlagevolumen: float = 0.0):
    use_volume = anlagevolumen > 0

    # ── Daten laden ──
    auto_tag_pf = detect_newest_date_tag(DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS)
    date_tag_pf = auto_tag_pf
    with st.sidebar:
        st.markdown("---")
        st.subheader("📊 Portfolioanalyse")
        show_ytd = st.checkbox("YTD Performance anzeigen", value=False, key="pf_show_ytd")
        pf_brutto_mwst = st.checkbox("Bruttohonorar (inkl. 19% MwSt.)", value=False, key="pf_mwst",
            help="Aktiviert MwSt für die Performance-Kennzahlen auf Slide 8 der PowerPoint.")
        show_adv_pf = st.checkbox("Erweiterte Einstellungen", value=False, key="adv_pf")
        if show_adv_pf:
            date_tag_pf = st.text_input("Date-Tag Portfolioanalyse (yyMMdd)", value=auto_tag_pf,
                help="Neuester Tag automatisch erkannt. Nur ändern um auf ältere Stände zuzugreifen.", key="pf_date_tag")

    pf_files = load_pf_csvs(DATA_FOLDER_PF, date_tag_pf)
    if not pf_files:
        st.warning(f"Keine Portfolioanalyse-Dateien für Tag {date_tag_pf} in {DATA_FOLDER_PF}/ gefunden.")
        show_debug = st.checkbox("🔍 Debug anzeigen", value=False, key="pf_debug")
        if show_debug:
            import glob as g
            af = g.glob(os.path.join(DATA_FOLDER_PF, "*"))
            st.write("Dateien:", [os.path.basename(f) for f in af] if af else "Ordner leer/nicht vorhanden")
        return

    pf_data = build_pf_data(pf_files)
    if not pf_data:
        st.warning("Keine Portfolioanalyse-Daten geladen."); return

    # Duration-Daten laden
    duration_data = load_duration_data(DURATION_FOLDER, name_mapping)

    # Name-Mapping
    available_pf_names = set(pf_data.keys())
    col_display = name_mapping.columns[0]; col_csv_key = name_mapping.columns[1]
    filtered = name_mapping[name_mapping[col_csv_key].isin(available_pf_names)].copy()
    if filtered.empty:
        display_names_pf = sorted(list(available_pf_names))
        display_to_csv_pf = {n: n for n in display_names_pf}
    else:
        display_names_pf = filtered[col_display].tolist()
        display_to_csv_pf = dict(zip(filtered[col_display], filtered[col_csv_key]))

    # Portfolio-Auswahl
    pf_sel_1 = st.selectbox("Portfolio auswählen", display_names_pf, key="pf_sel_1")
    csv_name_1 = display_to_csv_pf[pf_sel_1]; df_pf_1 = pf_data[csv_name_1]
    dur_1 = duration_data.get(csv_name_1)

    show_compare_pf = st.checkbox("Vergleichsportfolio anzeigen", value=False, key="pf_compare")
    pf_sel_2 = csv_name_2 = df_pf_2 = dur_2 = None
    if show_compare_pf:
        pf_sel_2 = st.selectbox("Vergleichsportfolio auswählen", display_names_pf, key="pf_sel_2")
        csv_name_2 = display_to_csv_pf[pf_sel_2]; df_pf_2 = pf_data[csv_name_2]
        dur_2 = duration_data.get(csv_name_2)

    # Auswertungsdatum
    ad1 = df_pf_1["Auswertungsdatum"].iloc[0] if "Auswertungsdatum" in df_pf_1.columns and df_pf_1["Auswertungsdatum"].notna().any() else None
    ad2 = None
    if df_pf_2 is not None and "Auswertungsdatum" in df_pf_2.columns and df_pf_2["Auswertungsdatum"].notna().any():
        ad2 = df_pf_2["Auswertungsdatum"].iloc[0]

    auswertung_str = fmt_date_de(ad1) if ad1 else date_tag_pf

    # Hinweis + Quelle oben
    st.caption("⚠️ **Hinweise:** Siehe Disclaimer unten!")
    st.caption(f"📊 **Quelle:** Infront & eigene Berechnungen, Stand: {auswertung_str}")

    st.info(f"📅 **Momentaufnahme per {auswertung_str}** – "
            f"Die dargestellten Daten zeigen den Portfoliobestand zu einem Stichtag.")

    # Render
    _render_single_portfolio(pf_sel_1, df_pf_1, ad1, anlagevolumen, use_volume, show_ytd, dur_1, suffix="pf1")
    if show_compare_pf and df_pf_2 is not None:
        st.markdown("---")
        _render_single_portfolio(pf_sel_2, df_pf_2, ad2, anlagevolumen, use_volume, show_ytd, dur_2, suffix="pf2")

    # Disclaimer
    st.markdown("---")
    st.markdown("##### Disclaimer")
    st.markdown(
        "Die dargestellten Daten zeigen den Portfoliobestand zu einem bestimmten Stichtag. "
        "Die tatsächlichen Gewichtungen können zum Zeitpunkt der Betrachtung durch Käufe, Verkäufe "
        "und Kursveränderungen bereits abweichen, da keine Live-Daten verwendet werden. "
        "Auch die Zuordnung zu Gattungen, Segmenten und Regionen basiert auf der zum Stichtag "
        "gültigen Klassifizierung und kann sich durch Umstrukturierungen oder Neuzuordnungen verändern."
    )
    st.markdown(
        "Diese Portfolioanalyse dient ausschließlich der unverbindlichen Veranschaulichung der "
        "Vermögensverwaltungsstrategien im Kundengespräch. Alle Angaben sind ohne Gewähr."
    )
    st.markdown(f"**Quelle:** Infront & eigene Berechnungen, Stand: {auswertung_str}")
    st.markdown("**Ansprechpartner:** PBAM")

    # Export: PDF und PowerPoint nebeneinander
    # Pattern: Session-State Cache für Export-Daten, verhindert Re-Generierung bei jedem Rerun.
    # Cache-Key enthält die aktuelle Auswahl - bei Änderungen wird alter Cache invalidiert.
    st.markdown("---")

    # Cache-Key aus aktueller Auswahl (ändert sich → Cache ungültig → Download-Button verschwindet)
    compare_key = pf_sel_2 if (show_compare_pf and df_pf_2 is not None) else "single"
    current_key = f"{pf_sel_1}|{compare_key}|{date_tag_pf}|{anlagevolumen}|{show_ytd}|{pf_brutto_mwst}"

    # Cache invalidieren wenn Auswahl geändert wurde
    if st.session_state.get("pf_export_key") != current_key:
        st.session_state.pop("pf_pdf_bytes", None)
        st.session_state.pop("pf_pptx_bytes", None)
        st.session_state.pop("pf_pptx_build_errors", None)
        st.session_state["pf_export_key"] = current_key

    exp_col1, exp_col2 = st.columns(2)

    # ── PDF Export ──
    with exp_col1:
        if "pf_pdf_bytes" not in st.session_state:
            # Button zum Generieren
            if st.button("📄 PDF erstellen", key="pf_pdf_btn", use_container_width=True):
                portfolios = [(pf_sel_1, df_pf_1, ad1, dur_1)]
                if show_compare_pf and df_pf_2 is not None:
                    portfolios.append((pf_sel_2, df_pf_2, ad2, dur_2))
                with st.spinner("PDF wird erstellt..."):
                    st.session_state["pf_pdf_bytes"] = generate_pf_pdf(
                        portfolios, anlagevolumen, use_volume, show_ytd
                    )
                st.rerun()
        else:
            # Download-Button mit gecachten Bytes
            st.download_button(
                "⬇️ PDF herunterladen",
                data=st.session_state["pf_pdf_bytes"],
                file_name=f"Portfolioanalyse_{pf_sel_1}_{fmt_date_de(ad1) if ad1 else date_tag_pf}.pdf",
                mime="application/pdf",
                key="pf_pdf_dl",
                use_container_width=True,
            )

    # ── PowerPoint Export ──
    with exp_col2:
        if "pf_pptx_bytes" not in st.session_state:
            # Button zum Generieren
            if st.button("📊 PowerPoint erstellen", key="pf_pptx_btn", use_container_width=True,
                         help="Exportiert die Portfolioanalyse in die Corporate-Vorlage (Folien 7-10)."):
                portfolios = [(pf_sel_1, df_pf_1, ad1, dur_1)]
                if show_compare_pf and df_pf_2 is not None:
                    portfolios.append((pf_sel_2, df_pf_2, ad2, dur_2))

                # ── Performance-Inputs für die Folien 8+9 zusammenbauen ──
                # Priorität 1: aus session_state (gefüllt vom Performance-Tab)
                # Priorität 2 (Fallback): direkt aus CSV laden, falls User den
                # Performance-Tab nie geöffnet hat oder dort kein passendes
                # Portfolio drin ist.
                perf_timeseries = st.session_state.get("perf_timeseries", {})
                perf_d2c = st.session_state.get("perf_d2c", {})
                mwst_faktor_pf = 1.19 if pf_brutto_mwst else 1.0
                try:
                    mapping_pf = load_mapping()
                except Exception:
                    mapping_pf = None

                # NEU (Juli 2026): Benchmark-Texte für die ***-Fußnote der
                # Wertentwicklungs-Folie (Folie 8). Primär aus session_state
                # (vom Performance-Tab: st.session_state["perf_d2b"] = d2b),
                # Fallback direkt aus dem Name-Mapping (Spalte D).
                perf_d2b = st.session_state.get("perf_d2b", {})
                if not perf_d2b:
                    try:
                        nm_cols = name_mapping.columns
                        if len(nm_cols) >= 4:
                            perf_d2b = dict(zip(name_mapping[nm_cols[0]], name_mapping[nm_cols[3]]))
                    except Exception:
                        perf_d2b = {}

                # Fallback-Loader: wenn session_state leer ist, lade Performance-CSVs direkt
                fallback_loaded = False
                if not perf_timeseries:
                    try:
                        perf_date_tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
                        perf_files = load_all_csvs(DATA_FOLDER, perf_date_tag, EXCLUDE_SUBSTRINGS)
                        if perf_files and mapping_pf is not None:
                            perf_timeseries = build_portfolio_timeseries(perf_files, mapping_pf)
                            fallback_loaded = True
                    except Exception as ex:
                        st.warning(f"Performance-Daten konnten nicht geladen werden: {ex}")

                performance_inputs = []
                missing_csv_names = []
                for pf_name, df_pf, _ad, _dur in portfolios:
                    # csv_name auflösen: erst über perf_d2c (vom Performance-Tab),
                    # fallback auf display_to_csv_pf (lokales Mapping)
                    csv_n = perf_d2c.get(pf_name) or display_to_csv_pf.get(pf_name)
                    ts_df = perf_timeseries.get(csv_n) if csv_n else None
                    if ts_df is None or len(ts_df) == 0:
                        missing_csv_names.append((pf_name, csv_n))
                    # Honorarsatz aus mapping (Default, dezimal) × MwSt-Faktor
                    fee_dec = 0.0
                    if mapping_pf is not None and csv_n is not None:
                        try:
                            fee_dec = float(mapping_pf.loc[mapping_pf["Inhaber"] == csv_n,
                                                          "Honorarsatz Standard"].values[0]) * mwst_faktor_pf
                        except Exception:
                            fee_dec = 0.0

                    # NEU (Juli 2026): Zusatzdaten für die Wertentwicklungs-Folie
                    # (Folie 8) — beide optional, fehlend → "–" bzw.
                    # Vorlagen-Fußnote bleibt.
                    # Duration: dur_info ist das Dict aus load_duration_data
                    # ({"duration": float|None, "rendite": float|None}).
                    duration_val = _dur.get("duration") if isinstance(_dur, dict) else None
                    # Benchmark-Text: Mapping Spalte D; Platzhalter-Werte filtern
                    bm_text = perf_d2b.get(pf_name)
                    if bm_text is not None:
                        bm_text = str(bm_text).strip()
                        if bm_text.lower() in ("", "nan", "none", "haben keine benchmark"):
                            bm_text = None

                    performance_inputs.append({
                        "timeseries_df": ts_df,
                        "fee_dec": fee_dec,
                        "duration": duration_val,
                        "benchmark_text": bm_text,
                    })

                # Wenn Daten fehlen, Diagnose PERSISTENT machen (NEU Juli 2026):
                # st.warning direkt vor st.rerun() wird vom Rerun weggewischt —
                # deshalb in session_state sammeln und nach dem Rerun anzeigen.
                pptx_diag = []
                if missing_csv_names:
                    diag = ", ".join([f"'{pn}' → '{cn}'" for pn, cn in missing_csv_names])
                    pptx_diag.append(
                        f"Performance-Daten für {diag} fehlen — Folien 8+9 zeigen Platzhalter. "
                        f"Verfügbar in session_state: {len(perf_timeseries)} Portfolios, "
                        f"davon: {list(perf_timeseries.keys())[:5]}{'…' if len(perf_timeseries) > 5 else ''}. "
                        f"Fallback-Load aktiv: {fallback_loaded}."
                    )

                try:
                    with st.spinner("PowerPoint wird erstellt..."):
                        from modules import pptx_export as _pptx_export_mod
                        from modules.pptx_export import generate_portfolioanalyse_pptx
                        st.session_state["pf_pptx_bytes"] = generate_portfolioanalyse_pptx(
                            portfolios, anlagevolumen, performance_inputs=performance_inputs
                        )
                        # NEU (Juli 2026): Berechnungsfehler aus dem Export
                        # (z.B. Kennzahlen-Berechnung der Folie 8 geworfen →
                        # Folie zeigt Platzhalter) sichtbar machen statt still
                        # zu verschlucken.
                        pptx_diag.extend(_pptx_export_mod.LAST_BUILD_ERRORS)
                    st.session_state["pf_pptx_build_errors"] = pptx_diag
                    st.rerun()
                except FileNotFoundError as e:
                    st.error(f"❌ Vorlage nicht gefunden: {e}\n\nBitte `Vorlage_FFPB.pptx` im Ordner `Vorlage/` im Repo ablegen.")
                except Exception as e:
                    st.error(f"❌ Fehler beim PowerPoint-Export: {e}")
        else:
            # Diagnose aus dem letzten Export-Lauf anzeigen (überlebt st.rerun)
            for _diag_msg in st.session_state.get("pf_pptx_build_errors", []):
                st.warning(f"⚠️ {_diag_msg}")
            # Download-Button mit gecachten Bytes
            st.download_button(
                "⬇️ PowerPoint herunterladen",
                data=st.session_state["pf_pptx_bytes"],
                file_name=f"Portfolioanalyse_{pf_sel_1}_{fmt_date_de(ad1) if ad1 else date_tag_pf}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key="pf_pptx_dl",
                use_container_width=True,
            )


def _render_single_portfolio(label, df, auswertungsdatum, anlagevolumen, use_volume, show_ytd, duration_info, suffix="pf1"):
    st.subheader(f"📊 {label}")

    # ── Kennzahlen ──
    liq = calc_liquidity(df); n_titel = len(df); total_weight = df["Gewicht"].sum()
    kcols = st.columns(4 if use_volume else 3)
    with kcols[0]: st.metric("Anzahl Titel", n_titel)
    with kcols[1]: st.metric("Investitionsgrad", fmt_pct_de(total_weight),
        help="Anteil des Portfolios, der in Wertpapiere investiert ist.")
    with kcols[2]: st.metric("Liquidität", fmt_pct_de(liq),
        help="Nicht investierter Anteil (100% − Investitionsgrad).")
    if use_volume:
        with kcols[3]: st.metric("Liquidität in €", fmt_eur_de(liq * anlagevolumen))

    # ── Ring-Diagramme (3 nebeneinander, volle Breite) ──
    st.markdown("---")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        alloc_g = build_allocation(df, "Gattung")
        if not alloc_g.empty: st.plotly_chart(build_ring_chart(alloc_g, "Gattung", "Allokation nach Gattung"), use_container_width=True, config={"displayModeBar": False}, key=f"ring_g_{suffix}")
    with rc2:
        alloc_r = build_allocation(df, "Region")
        if not alloc_r.empty: st.plotly_chart(build_ring_chart(alloc_r, "Region", "Allokation nach Region"), use_container_width=True, config={"displayModeBar": False}, key=f"ring_r_{suffix}")
    with rc3:
        alloc_s = build_allocation(df, "Segment")
        if not alloc_s.empty: st.plotly_chart(build_ring_chart(alloc_s, "Segment", "Allokation nach Segment"), use_container_width=True, config={"displayModeBar": False}, key=f"ring_s_{suffix}")

    # ── Einzeltitel-Bereich ──
    st.markdown("---")

    # ── Top 5 Holdings (Säulendiagramm, immer sichtbar) ──
    top5 = get_top_holdings(df, n=5)
    if not top5.empty:
        fig_top5 = build_top5_bar_chart(top5, "Top 5 Holdings (nach Gewicht)")
        st.plotly_chart(fig_top5, use_container_width=True, config={"displayModeBar": False}, key=f"top5_{suffix}")

    # ── Einzeltitel-Tabelle (gruppiert nach Gattung) ──
    st.markdown("**Einzeltitel-Übersicht**")
    grouped = build_grouped_title_table(df, anlagevolumen if use_volume else 0.0, show_ytd)
    for i, (gattung_name, gattung_weight, disp_df) in enumerate(grouped):
        if gattung_name.startswith("💰"):
            st.markdown(f"**{gattung_name}** ({fmt_pct_de(gattung_weight)})")
        else:
            st.markdown(f"**📋 {gattung_name}** – {fmt_pct_de(gattung_weight)}")
        st.dataframe(disp_df, use_container_width=True, hide_index=True, key=f"tbl_{suffix}_{i}")

    # ── Top/Flop Performancebeitrag (nur wenn YTD aktiv) ──
    if show_ytd and "Performancebeitrag" in df.columns and df["Performancebeitrag"].notna().any():
        st.markdown("---")
        tc, fc = st.columns(2)
        top, flop = get_top_flop(df, "Performancebeitrag", n=5)
        with tc:
            st.markdown("**🏆 Top 5 Performancebeitrag (YTD)**")
            if not top.empty:
                td = top.copy(); td["Gewicht"] = td["Gewicht"].apply(fmt_pct_de)
                td["Performancebeitrag"] = td["Performancebeitrag"].apply(fmt_pct_de)
                st.dataframe(td, use_container_width=True, hide_index=True, key=f"top5ytd_{suffix}")
        with fc:
            st.markdown("**📉 Flop 5 Performancebeitrag (YTD)**")
            if not flop.empty:
                fd = flop.copy(); fd["Gewicht"] = fd["Gewicht"].apply(fmt_pct_de)
                fd["Performancebeitrag"] = fd["Performancebeitrag"].apply(fmt_pct_de)
                st.dataframe(fd, use_container_width=True, hide_index=True, key=f"flop5ytd_{suffix}")

        st.caption(
            "**Performancebeitrag:** Gewichteter Beitrag des Titels zur Gesamtperformance des Portfolios seit Jahresbeginn. "
            "**Wertpapier-Performance:** Individuelle Wertentwicklung des Wertpapiers seit Jahresbeginn, unabhängig von der Gewichtung. "
            "Beide Werte sind eine Momentaufnahme zum Stichtag. Historische Wertentwicklung ist kein verlässlicher Indikator für zukünftige Ergebnisse."
        )

    # ── Anleihen-Detail + Duration ──
    bond_summary = get_bond_summary(df)
    if bond_summary is not None:
        st.markdown("---")
        st.markdown("**🏦 Anleihen-Detail**")

        # Anzahl Kennzahlen-Spalten dynamisch
        has_duration = duration_info is not None and duration_info.get("duration") is not None
        has_rendite = duration_info is not None and duration_info.get("rendite") is not None
        n_bond_cols = 3 + (1 if has_duration else 0) + (1 if has_rendite else 0)

        bcols = st.columns(n_bond_cols)
        col_idx = 0
        with bcols[col_idx]: st.metric("Anzahl Anleihen", bond_summary["count"]); col_idx += 1
        with bcols[col_idx]:
            st.metric("Gewicht Anleihen", fmt_pct_de(bond_summary["total_weight"]),
                help="Gesamtgewicht aller Anleihen im Portfolio."); col_idx += 1
        with bcols[col_idx]:
            if bond_summary["avg_kupon"] is not None:
                st.metric("⌀ Kupon (gewichtet)", fmt_pct_de(bond_summary["avg_kupon"]),
                    help="Gewichteter Durchschnittskupon aller Anleihen im Portfolio.")
            else:
                st.metric("⌀ Kupon", "–")
            col_idx += 1
        if has_duration:
            with bcols[col_idx]:
                st.metric("Duration (Portfolio)", f"{duration_info['duration']:.2f}".replace(".", ","),
                    help="Die Duration misst die Zinssensitivität des Anleihenportfolios. "
                         "Sie gibt an, um wie viel Prozent der Portfoliowert fällt, "
                         "wenn das Zinsniveau um 1 Prozentpunkt steigt. "
                         "Einheit: Jahre (modifizierte Duration).")
                col_idx += 1
        if has_rendite:
            with bcols[col_idx]:
                st.metric("Rendite (Portfolio)", fmt_pct_de(duration_info["rendite"]),
                    help="Die Portfoliorendite (Yield to Maturity) gibt die erwartete jährliche "
                         "Rendite an, wenn alle Anleihen bis zur Fälligkeit gehalten werden.")

        if bond_summary["faelligkeit"] is not None and not bond_summary["faelligkeit"].empty:
            st.markdown("**Fälligkeitsstruktur**")
            faell = bond_summary["faelligkeit"]
            fig_f = go.Figure(data=[go.Bar(
                x=faell["Jahr"].astype(str), y=faell["Gewicht"],
                marker_color=FFPB_GOLD,
                text=[fmt_pct_de(v) for v in faell["Gewicht"]], textposition="outside")])
            fig_f.update_layout(height=300, xaxis_title="Fälligkeitsjahr", yaxis_title="Gewicht",
                yaxis=dict(tickformat=".1%"), margin=dict(t=30, b=40, l=50, r=20))
            st.plotly_chart(fig_f, use_container_width=True, config={"displayModeBar": False}, key=f"faell_{suffix}")


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------
def generate_pf_pdf(portfolios, anlagevolumen, use_volume, show_ytd):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        topMargin=15*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    st_t = ParagraphStyle("PFT", parent=styles["Title"], fontName=PDF_FONT_BOLD, textColor=HexColor(FFPB_DARK), fontSize=16, spaceAfter=6)
    st_s = ParagraphStyle("PFS", parent=styles["Heading2"], fontName=PDF_FONT_BOLD, textColor=HexColor(FFPB_DARK), fontSize=12, spaceAfter=4, spaceBefore=10)
    st_n = ParagraphStyle("PFN", parent=styles["Normal"], fontName=PDF_FONT, textColor=HexColor("#333333"), fontSize=9, leading=12)
    st_sm = ParagraphStyle("PFSM", parent=styles["Normal"], fontName=PDF_FONT, textColor=HexColor("#666666"), fontSize=7.5, leading=10)
    st_g = ParagraphStyle("PFG", parent=styles["Heading3"], fontName=PDF_FONT_BOLD, textColor=HexColor(FFPB_GOLD), fontSize=10, spaceAfter=2, spaceBefore=6)

    logo_path = get_logo_path(); la = get_logo_aspect(logo_path)
    story = []

    if logo_path:
        lw = 50*mm; story.append(RLImage(logo_path, width=lw, height=lw*la)); story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Portfolioanalyse", st_t))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor(FFPB_DARK)))
    story.append(Spacer(1, 3*mm))

    # Quelle
    first_ad_meta = portfolios[0][2] if portfolios else None
    story.append(Paragraph(f"<b>Quelle:</b> Infront &amp; eigene Berechnungen, Stand: {fmt_date_de(first_ad_meta) if first_ad_meta else ''}", st_sm))
    story.append(Spacer(1, 3*mm))

    for item in portfolios:
        label, df, auswertungsdatum = item[0], item[1], item[2]
        dur_info = item[3] if len(item) > 3 else None

        story.append(Paragraph(f"<b>{label}</b>", st_s))
        if auswertungsdatum:
            story.append(Paragraph(f"Momentaufnahme per {fmt_date_de(auswertungsdatum)}", st_n))
        story.append(Spacer(1, 2*mm))

        liq = calc_liquidity(df); tw = df["Gewicht"].sum()
        meta = [f"Titel: {len(df)}", f"Investitionsgrad: {fmt_pct_de(tw)}", f"Liquidität: {fmt_pct_de(liq)}"]
        if use_volume: meta += [f"Volumen: {fmt_eur_de(anlagevolumen)}", f"Liq. €: {fmt_eur_de(liq*anlagevolumen)}"]
        if dur_info and dur_info.get("duration"):
            meta.append(f"Duration: {dur_info['duration']:.2f}".replace(".", ","))
        if dur_info and dur_info.get("rendite"):
            meta.append(f"Rendite: {fmt_pct_de(dur_info['rendite'])}")
        story.append(Paragraph(" | ".join(meta), st_n))
        story.append(Spacer(1, 4*mm))

        # Ring-Diagramme (kompakter)
        for gc, ct in [("Gattung", f"Allokation nach Gattung – {label}"), ("Region", f"Allokation nach Region – {label}"), ("Segment", f"Allokation nach Segment – {label}")]:
            alloc = build_allocation(df, gc)
            if not alloc.empty:
                story.append(RLImage(_mpl_ring_chart(alloc, gc, ct), width=100*mm, height=85*mm))
                story.append(Spacer(1, 2*mm))

        story.append(PageBreak())

        # Einzeltitel gruppiert
        if logo_path:
            lws = 35*mm; story.append(RLImage(logo_path, width=lws, height=lws*la)); story.append(Spacer(1, 3*mm))
        story.append(Paragraph(f"Einzeltitel – {label}", st_s))

        grouped = build_grouped_title_table(df, anlagevolumen if use_volume else 0.0, show_ytd)
        for gname, gw, disp in grouped:
            story.append(Paragraph(f"<b>{gname}</b> – {fmt_pct_de(gw)}", st_g))
            header = list(disp.columns)
            tdata = [header] + disp.fillna("–").values.tolist()
            nc = len(header)

            # Intelligente Spaltenbreiten
            total_w = 170*mm
            col_widths = []
            for col_name in header:
                cn = col_name.lower()
                if "wertpapier" in cn or "name" in cn:
                    col_widths.append(3.0)  # Breit
                elif "segment" in cn or "region" in cn:
                    col_widths.append(2.0)  # Mittel
                elif "fälligkeit" in cn or "performance" in cn or "performancebeitrag" in cn:
                    col_widths.append(1.5)
                else:
                    col_widths.append(1.0)  # Schmal (WKN, Gewicht, Kupon)
            total_ratio = sum(col_widths)
            col_widths = [total_w * (w / total_ratio) for w in col_widths]

            t = Table(tdata, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), HexColor(FFPB_DARK)), ("TEXTCOLOR", (0,0), (-1,0), white),
                ("FONTSIZE", (0,0), (-1,-1), 6), ("FONTNAME", (0,0), (-1,0), PDF_FONT_BOLD),
                ("ALIGN", (2,0), (-1,-1), "RIGHT"), ("ALIGN", (0,0), (1,-1), "LEFT"),
                ("GRID", (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, HexColor("#F5F5F5")]),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2)]))
            story.append(t); story.append(Spacer(1, 2*mm))

        story.append(PageBreak())

    # ── Disclaimer ──
    if logo_path:
        lws = 35*mm; story.append(RLImage(logo_path, width=lws, height=lws*la)); story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Disclaimer", st_s))
    story.append(Spacer(1, 3*mm))

    # Auswertungsdatum aus erstem Portfolio für Quellenangabe
    first_ad = portfolios[0][2] if portfolios else None
    ad_str = fmt_date_de(first_ad) if first_ad else ""

    disclaimer_pf = [
        "Die dargestellten Daten zeigen den Portfoliobestand zu einem bestimmten Stichtag. "
        "Die tatsächlichen Gewichtungen können zum Zeitpunkt der Betrachtung durch Käufe, Verkäufe "
        "und Kursveränderungen bereits abweichen, da keine Live-Daten verwendet werden. "
        "Auch die Zuordnung zu Gattungen, Segmenten und Regionen basiert auf der zum Stichtag "
        "gültigen Klassifizierung und kann sich durch Umstrukturierungen oder Neuzuordnungen verändern.",

        "Diese Portfolioanalyse dient ausschließlich der unverbindlichen Veranschaulichung der "
        "Vermögensverwaltungsstrategien im Kundengespräch. Alle Angaben sind ohne Gewähr.",
    ]
    for txt in disclaimer_pf:
        story.append(Paragraph(txt, st_n))
        story.append(Spacer(1, 2*mm))

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"<b>Quelle:</b> Infront &amp; eigene Berechnungen, Stand: {ad_str}", st_n))
    story.append(Paragraph("<b>Ansprechpartner:</b> PBAM", st_n))

    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#CCCCCC")))
    story.append(Paragraph(f"Erstellt am {fmt_date_de(dt.date.today())} | Fürst Fugger Privatbank", st_sm))
    doc.build(story); buf.seek(0)
    return buf.getvalue()
