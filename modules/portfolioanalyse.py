# modules/portfolioanalyse.py
"""Portfolioanalyse: Bestands- und Allokationsübersicht."""

import os
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
    DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS,
    fmt_date_de, fmt_pct_de, fmt_eur_de,
    detect_newest_date_tag, get_logo_aspect, get_logo_path,
    csv_name_to_display,
)


# ---------------------------------------------------------------------------
# Ring-Chart Farben
# ---------------------------------------------------------------------------
RING_COLORS = [
    "#B8973A", "#2C5F8A", "#A8CBE8", "#7FB5D5", "#1B3A5C",
    "#E8A838", "#5BA0D0", "#C4C4C4", "#3A7CA5", "#D4A84B",
    "#8FBDD3", "#4A6E8C", "#F0C070", "#6A9BC3", "#2A4A6C",
]


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def load_pf_csvs(data_folder: str, date_tag: str) -> list[str]:
    """Findet alle Portfolioanalyse-CSVs für den gegebenen Date-Tag."""
    files = []
    # Suche case-insensitive: .CSV und .csv
    for ext in ["*.CSV", "*.csv"]:
        all_files = glob.glob(os.path.join(data_folder, ext))
        for f in all_files:
            basename = os.path.basename(f)
            if date_tag in basename:
                files.append(f)
    # Deduplizieren
    files = list(set(files))
    return files


def read_pf_csv(path: str) -> pd.DataFrame:
    """Liest eine Portfolioanalyse-CSV ein."""
    df = pd.read_csv(
        path, comment="#", encoding="ISO-8859-1",
        delimiter=";", decimal=",", thousands=".", dtype=str
    )
    return df


def parse_pf_data(df: pd.DataFrame) -> pd.DataFrame:
    """Parst und bereinigt die Portfolioanalyse-Daten."""
    df = df.copy()

    # Prozent-Spalten parsen
    for col in ["Gewicht", "Performancebeitrag", "WP-Performance", "Kupon"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace("%", "").str.replace(",", ".").str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0

    # Auswertungsdatum parsen
    if "Auswertungsdatum" in df.columns:
        df["Auswertungsdatum"] = pd.to_datetime(
            df["Auswertungsdatum"], format="%d.%m.%Y", errors="coerce"
        )

    # Fälligkeit parsen (kann "-" oder ein Datum sein)
    if "Fälligkeit" in df.columns:
        df["Fälligkeit_parsed"] = pd.to_datetime(
            df["Fälligkeit"], format="%d.%m.%Y", errors="coerce"
        )

    return df


@st.cache_data(show_spinner=True)
def build_pf_data(files: list[str]) -> dict[str, pd.DataFrame]:
    """Lädt alle PF-CSVs und gibt ein Dict {Portfolio Name: DataFrame} zurück."""
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
# Berechnungen
# ---------------------------------------------------------------------------
def calc_liquidity(df: pd.DataFrame) -> float:
    """Liquidität = 1.0 - Summe(Gewicht)."""
    total_weight = df["Gewicht"].sum()
    return max(0.0, 1.0 - total_weight)


def build_allocation(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Aggregiert Gewichte nach einer Gruppierungsspalte + Liquidität."""
    if group_col not in df.columns:
        return pd.DataFrame()
    agg = df.groupby(group_col)["Gewicht"].sum().reset_index()
    agg.columns = [group_col, "Gewicht"]
    agg = agg.sort_values("Gewicht", ascending=False).reset_index(drop=True)

    # Liquidität hinzufügen
    liq = calc_liquidity(df)
    if liq > 0.0001:
        liq_row = pd.DataFrame([{group_col: "Liquidität", "Gewicht": liq}])
        agg = pd.concat([agg, liq_row], ignore_index=True)

    return agg


def build_title_table(df: pd.DataFrame, anlagevolumen: float = 0.0) -> pd.DataFrame:
    """Baut die Einzeltitel-Tabelle auf."""
    cols = ["Wertpapier", "WKN", "Gewicht", "Gattung", "Segment", "Region"]

    # Optional: Performance-Spalten
    has_perf = "WP-Performance" in df.columns and df["WP-Performance"].notna().any()
    has_beitrag = "Performancebeitrag" in df.columns and df["Performancebeitrag"].notna().any()

    # Anleihen-Spalten
    has_kupon = "Kupon" in df.columns and df["Kupon"].notna().any() and (df["Kupon"] != 0).any()
    has_faelligkeit = "Fälligkeit_parsed" in df.columns and df["Fälligkeit_parsed"].notna().any()

    available_cols = [c for c in cols if c in df.columns]
    result = df[available_cols].copy()

    if has_kupon:
        result["Kupon"] = df["Kupon"]
    if has_faelligkeit:
        result["Fälligkeit"] = df["Fälligkeit_parsed"].apply(
            lambda x: fmt_date_de(x) if pd.notna(x) else "–"
        )
    if has_perf:
        result["WP-Performance (YTD)"] = df["WP-Performance"]
    if has_beitrag:
        result["Performancebeitrag (YTD)"] = df["Performancebeitrag"]

    # Investierter Betrag wenn Volumen eingegeben
    if anlagevolumen > 0:
        result["Investiert (€)"] = df["Gewicht"] * anlagevolumen

    # Liquiditäts-Zeile
    liq = calc_liquidity(df)
    if liq > 0.0001:
        liq_row = {c: "" for c in result.columns}
        liq_row["Wertpapier"] = "💰 Liquidität"
        liq_row["Gewicht"] = liq
        if anlagevolumen > 0:
            liq_row["Investiert (€)"] = liq * anlagevolumen
        result = pd.concat([result, pd.DataFrame([liq_row])], ignore_index=True)

    return result


def format_title_table(df: pd.DataFrame) -> pd.DataFrame:
    """Formatiert die Einzeltitel-Tabelle für die Anzeige."""
    display = df.copy()
    if "Gewicht" in display.columns:
        display["Gewicht"] = display["Gewicht"].apply(
            lambda x: fmt_pct_de(x) if isinstance(x, (int, float)) and not pd.isna(x) else str(x)
        )
    if "Kupon" in display.columns:
        display["Kupon"] = display["Kupon"].apply(
            lambda x: fmt_pct_de(x) if isinstance(x, (int, float)) and not pd.isna(x) and x != 0 else "–"
        )
    if "WP-Performance (YTD)" in display.columns:
        display["WP-Performance (YTD)"] = display["WP-Performance (YTD)"].apply(
            lambda x: fmt_pct_de(x) if isinstance(x, (int, float)) and not pd.isna(x) else "–"
        )
    if "Performancebeitrag (YTD)" in display.columns:
        display["Performancebeitrag (YTD)"] = display["Performancebeitrag (YTD)"].apply(
            lambda x: fmt_pct_de(x) if isinstance(x, (int, float)) and not pd.isna(x) else "–"
        )
    if "Investiert (€)" in display.columns:
        display["Investiert (€)"] = display["Investiert (€)"].apply(
            lambda x: fmt_eur_de(x) if isinstance(x, (int, float)) and not pd.isna(x) else "–"
        )
    return display


def get_top_flop(df: pd.DataFrame, col: str, n: int = 5):
    """Gibt Top-N und Flop-N nach einer Spalte zurück."""
    valid = df[df[col].notna() & (df[col] != 0)].copy()
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame()
    top = valid.nlargest(n, col)[["Wertpapier", "WKN", "Gewicht", col]].copy()
    flop = valid.nsmallest(n, col)[["Wertpapier", "WKN", "Gewicht", col]].copy()
    return top, flop


def get_bond_summary(df: pd.DataFrame) -> dict | None:
    """Berechnet Anleihen-Kennzahlen (nur wenn Anleihen vorhanden)."""
    bonds = df[df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty:
        return None

    summary = {"count": len(bonds)}

    # Gewichteter Durchschnittskupon
    if "Kupon" in bonds.columns and bonds["Kupon"].notna().any():
        w = bonds["Gewicht"].fillna(0)
        k = bonds["Kupon"].fillna(0)
        if w.sum() > 0:
            summary["avg_kupon"] = float((w * k).sum() / w.sum())
        else:
            summary["avg_kupon"] = None
    else:
        summary["avg_kupon"] = None

    # Fälligkeitsstruktur
    if "Fälligkeit_parsed" in bonds.columns and bonds["Fälligkeit_parsed"].notna().any():
        faell = bonds[bonds["Fälligkeit_parsed"].notna()].copy()
        faell["Jahr"] = faell["Fälligkeit_parsed"].dt.year
        faell_agg = faell.groupby("Jahr")["Gewicht"].sum().reset_index()
        faell_agg.columns = ["Jahr", "Gewicht"]
        summary["faelligkeit"] = faell_agg
    else:
        summary["faelligkeit"] = None

    summary["total_weight"] = float(bonds["Gewicht"].sum())
    return summary


# ---------------------------------------------------------------------------
# Ring-Diagramm (Plotly)
# ---------------------------------------------------------------------------
def build_ring_chart(alloc_df: pd.DataFrame, group_col: str, title: str) -> go.Figure:
    """Erstellt ein Ring-Diagramm für eine Allokation."""
    fig = go.Figure(data=[go.Pie(
        labels=alloc_df[group_col],
        values=alloc_df["Gewicht"],
        hole=0.5,
        marker=dict(colors=RING_COLORS[:len(alloc_df)]),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>Gewicht: %{percent}<extra></extra>",
    )])
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=13), x=0.5, xanchor="center"),
        height=420,
        showlegend=True,
        legend=dict(font=dict(size=10), orientation="h", y=-0.15),
        margin=dict(t=50, b=60, l=20, r=20),
    )
    return fig


# ---------------------------------------------------------------------------
# Ring-Diagramm für PDF (matplotlib)
# ---------------------------------------------------------------------------
def _mpl_ring_chart(alloc_df: pd.DataFrame, group_col: str, title: str):
    """Matplotlib Ring-Chart → PNG BytesIO."""
    fig, ax = plt.subplots(figsize=(6, 5))
    labels = alloc_df[group_col].tolist()
    sizes = alloc_df["Gewicht"].tolist()
    colors = RING_COLORS[:len(alloc_df)]

    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct="%1.1f%%",
        startangle=90, colors=colors, pctdistance=0.8,
        wedgeprops=dict(width=0.4, edgecolor="white", linewidth=1.5),
    )
    for t in autotexts:
        t.set_fontsize(8)

    ax.set_title(title, fontsize=11, fontweight="bold", pad=15)
    ax.legend(labels, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Streamlit Rendering
# ---------------------------------------------------------------------------
def render_portfolioanalyse(name_mapping: pd.DataFrame, anlagevolumen: float = 0.0):
    """Hauptfunktion: Rendert die Portfolioanalyse-Seite."""

    use_volume = anlagevolumen > 0

    # ── Daten laden ──
    auto_tag_pf = detect_newest_date_tag(DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS)
    with st.sidebar:
        st.markdown("---")
        st.subheader("📊 Portfolioanalyse")
        date_tag_pf = st.text_input(
            "Date-Tag Portfolioanalyse (yyMMdd)", value=auto_tag_pf,
            help="Automatisch neuester Tag aus Daten_PF/.",
            key="pf_date_tag"
        )
        show_ytd = st.checkbox("YTD Performance anzeigen", value=False, key="pf_show_ytd")

    pf_files = load_pf_csvs(DATA_FOLDER_PF, date_tag_pf)
    if not pf_files:
        st.warning(f"Keine Portfolioanalyse-Dateien für Tag {date_tag_pf} in {DATA_FOLDER_PF}/ gefunden.")
        # Debug-Info
        with st.expander("🔍 Debug: Dateien im Ordner"):
            import glob as g
            all_in_folder = g.glob(os.path.join(DATA_FOLDER_PF, "*"))
            if all_in_folder:
                st.write("Dateien gefunden:", [os.path.basename(f) for f in all_in_folder])
            else:
                st.write(f"Ordner '{DATA_FOLDER_PF}/' ist leer oder existiert nicht.")
                st.write(f"Aktuelles Verzeichnis: {os.getcwd()}")
                st.write(f"Ordner existiert: {os.path.exists(DATA_FOLDER_PF)}")
        return

    pf_data = build_pf_data(pf_files)
    if not pf_data:
        st.warning("Keine Portfolioanalyse-Daten geladen.")
        return

    # Name-Mapping anwenden
    available_pf_names = set(pf_data.keys())
    col_display = name_mapping.columns[0]
    col_csv_key = name_mapping.columns[1]
    filtered = name_mapping[name_mapping[col_csv_key].isin(available_pf_names)].copy()

    if filtered.empty:
        # Fallback: CSV-Namen direkt verwenden
        display_names_pf = sorted(list(available_pf_names))
        display_to_csv_pf = {n: n for n in display_names_pf}
    else:
        display_names_pf = filtered[col_display].tolist()
        display_to_csv_pf = dict(zip(filtered[col_display], filtered[col_csv_key]))

    # ── Portfolio-Auswahl ──
    pf_sel_1 = st.selectbox("Portfolio auswählen", display_names_pf, key="pf_sel_1")
    csv_name_1 = display_to_csv_pf[pf_sel_1]
    df_pf_1 = pf_data[csv_name_1]

    # Vergleichsportfolio
    show_compare_pf = st.checkbox("Vergleichsportfolio anzeigen", value=False, key="pf_compare")
    pf_sel_2 = csv_name_2 = df_pf_2 = None
    if show_compare_pf:
        pf_sel_2 = st.selectbox("Vergleichsportfolio auswählen", display_names_pf, key="pf_sel_2")
        csv_name_2 = display_to_csv_pf[pf_sel_2]
        df_pf_2 = pf_data[csv_name_2]

    # ── Auswertungsdatum ──
    auswertungsdatum_1 = None
    if "Auswertungsdatum" in df_pf_1.columns and df_pf_1["Auswertungsdatum"].notna().any():
        auswertungsdatum_1 = df_pf_1["Auswertungsdatum"].iloc[0]
    auswertungsdatum_2 = None
    if df_pf_2 is not None and "Auswertungsdatum" in df_pf_2.columns and df_pf_2["Auswertungsdatum"].notna().any():
        auswertungsdatum_2 = df_pf_2["Auswertungsdatum"].iloc[0]

    st.info(
        f"📅 **Momentaufnahme per {fmt_date_de(auswertungsdatum_1) if auswertungsdatum_1 else date_tag_pf}** – "
        f"Die dargestellten Daten zeigen den Portfoliobestand zu einem Stichtag."
    )

    # ── Render für 1 oder 2 Portfolios ──
    if show_compare_pf and df_pf_2 is not None:
        col_left, col_right = st.columns(2)
        with col_left:
            _render_single_portfolio(pf_sel_1, df_pf_1, auswertungsdatum_1, anlagevolumen, use_volume, show_ytd)
        with col_right:
            _render_single_portfolio(pf_sel_2, df_pf_2, auswertungsdatum_2, anlagevolumen, use_volume, show_ytd)
    else:
        _render_single_portfolio(pf_sel_1, df_pf_1, auswertungsdatum_1, anlagevolumen, use_volume, show_ytd)

    # ── PDF Export ──
    st.markdown("---")
    if st.button("📄 PDF Portfolioanalyse erstellen", key="pf_pdf_btn"):
        portfolios = [(pf_sel_1, df_pf_1, auswertungsdatum_1)]
        if show_compare_pf and df_pf_2 is not None:
            portfolios.append((pf_sel_2, df_pf_2, auswertungsdatum_2))

        with st.spinner("PDF wird erstellt..."):
            pdf_bytes = generate_pf_pdf(portfolios, anlagevolumen, use_volume, show_ytd)

        datum_str = fmt_date_de(auswertungsdatum_1) if auswertungsdatum_1 else date_tag_pf
        st.download_button(
            label="⬇️ PDF herunterladen",
            data=pdf_bytes,
            file_name=f"Portfolioanalyse_{pf_sel_1}_{datum_str}.pdf",
            mime="application/pdf",
            key="pf_pdf_download"
        )
        st.success("PDF erfolgreich erstellt!")


def _render_single_portfolio(label, df, auswertungsdatum, anlagevolumen, use_volume, show_ytd):
    """Rendert die Analyse für ein einzelnes Portfolio."""

    st.subheader(f"📊 {label}")

    # ── Kennzahlen ──
    liq = calc_liquidity(df)
    n_titel = len(df)
    total_weight = df["Gewicht"].sum()

    kcols = st.columns(4 if use_volume else 3)
    with kcols[0]:
        st.metric("Anzahl Titel", n_titel)
    with kcols[1]:
        st.metric("Investitionsgrad", fmt_pct_de(total_weight),
                  help="Anteil des Portfolios, der in Wertpapiere investiert ist.")
    with kcols[2]:
        st.metric("Liquidität", fmt_pct_de(liq),
                  help="Nicht investierter Anteil des Portfolios (100% − Investitionsgrad).")
    if use_volume:
        with kcols[3]:
            st.metric("Liquidität in €", fmt_eur_de(liq * anlagevolumen))

    # ── Ring-Diagramme ──
    st.markdown("---")
    ring_col1, ring_col2, ring_col3 = st.columns(3)

    with ring_col1:
        alloc_gattung = build_allocation(df, "Gattung")
        if not alloc_gattung.empty:
            fig_g = build_ring_chart(alloc_gattung, "Gattung", "Allokation nach Gattung")
            st.plotly_chart(fig_g, use_container_width=True)

    with ring_col2:
        alloc_region = build_allocation(df, "Region")
        if not alloc_region.empty:
            fig_r = build_ring_chart(alloc_region, "Region", "Allokation nach Region")
            st.plotly_chart(fig_r, use_container_width=True)

    with ring_col3:
        alloc_segment = build_allocation(df, "Segment")
        if not alloc_segment.empty:
            fig_s = build_ring_chart(alloc_segment, "Segment", "Allokation nach Segment")
            st.plotly_chart(fig_s, use_container_width=True)

    # ── Einzeltitel-Tabelle ──
    st.markdown("---")
    st.markdown("**Einzeltitel-Übersicht**")
    title_df = build_title_table(df, anlagevolumen if use_volume else 0.0)

    # YTD-Spalten entfernen wenn nicht gewünscht
    if not show_ytd:
        for c in ["WP-Performance (YTD)", "Performancebeitrag (YTD)"]:
            if c in title_df.columns:
                title_df = title_df.drop(columns=[c])

    display_df = format_title_table(title_df)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Top/Flop (nur wenn YTD aktiv) ──
    if show_ytd and "Performancebeitrag" in df.columns and df["Performancebeitrag"].notna().any():
        st.markdown("---")
        top_col, flop_col = st.columns(2)
        top, flop = get_top_flop(df, "Performancebeitrag", n=5)

        with top_col:
            st.markdown("**🏆 Top 5 Performancebeitrag (YTD)**")
            if not top.empty:
                top_disp = top.copy()
                top_disp["Gewicht"] = top_disp["Gewicht"].apply(fmt_pct_de)
                top_disp["Performancebeitrag"] = top_disp["Performancebeitrag"].apply(fmt_pct_de)
                st.dataframe(top_disp, use_container_width=True, hide_index=True)

        with flop_col:
            st.markdown("**📉 Flop 5 Performancebeitrag (YTD)**")
            if not flop.empty:
                flop_disp = flop.copy()
                flop_disp["Gewicht"] = flop_disp["Gewicht"].apply(fmt_pct_de)
                flop_disp["Performancebeitrag"] = flop_disp["Performancebeitrag"].apply(fmt_pct_de)
                st.dataframe(flop_disp, use_container_width=True, hide_index=True)

    # ── Anleihen-Detail ──
    bond_summary = get_bond_summary(df)
    if bond_summary is not None:
        st.markdown("---")
        st.markdown("**🏦 Anleihen-Detail**")
        bcols = st.columns(3)
        with bcols[0]:
            st.metric("Anzahl Anleihen", bond_summary["count"])
        with bcols[1]:
            st.metric("Gewicht Anleihen", fmt_pct_de(bond_summary["total_weight"]),
                      help="Gesamtgewicht aller Anleihen im Portfolio.")
        with bcols[2]:
            if bond_summary["avg_kupon"] is not None:
                st.metric("⌀ Kupon (gewichtet)", fmt_pct_de(bond_summary["avg_kupon"]),
                          help="Gewichteter Durchschnittskupon aller Anleihen.")
            else:
                st.metric("⌀ Kupon", "–")

        if bond_summary["faelligkeit"] is not None and not bond_summary["faelligkeit"].empty:
            st.markdown("**Fälligkeitsstruktur**")
            faell = bond_summary["faelligkeit"]
            fig_f = go.Figure(data=[go.Bar(
                x=faell["Jahr"].astype(str),
                y=faell["Gewicht"],
                marker_color=FFPB_GOLD,
                text=[fmt_pct_de(v) for v in faell["Gewicht"]],
                textposition="outside",
            )])
            fig_f.update_layout(
                height=300,
                xaxis_title="Fälligkeitsjahr",
                yaxis_title="Gewicht",
                yaxis=dict(tickformat=".1%"),
                margin=dict(t=30, b=40, l=50, r=20),
            )
            st.plotly_chart(fig_f, use_container_width=True)


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------
def generate_pf_pdf(portfolios, anlagevolumen, use_volume, show_ytd):
    """Erzeugt PDF für die Portfolioanalyse."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        topMargin=15*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle("PFTitle", parent=styles["Title"],
        textColor=HexColor(FFPB_DARK), fontSize=16, spaceAfter=6)
    style_subtitle = ParagraphStyle("PFSub", parent=styles["Heading2"],
        textColor=HexColor(FFPB_DARK), fontSize=12, spaceAfter=4, spaceBefore=10)
    style_normal = ParagraphStyle("PFNormal", parent=styles["Normal"],
        textColor=HexColor("#333333"), fontSize=9, leading=12)
    style_small = ParagraphStyle("PFSmall", parent=styles["Normal"],
        textColor=HexColor("#666666"), fontSize=7.5, leading=10)

    logo_path = get_logo_path()
    logo_aspect = get_logo_aspect(logo_path)
    story = []

    # Logo
    if logo_path:
        lw = 50*mm
        story.append(RLImage(logo_path, width=lw, height=lw*logo_aspect))
        story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Portfolioanalyse", style_title))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor(FFPB_DARK)))
    story.append(Spacer(1, 3*mm))

    for label, df, auswertungsdatum in portfolios:
        story.append(Paragraph(f"<b>{label}</b>", style_subtitle))
        if auswertungsdatum:
            story.append(Paragraph(
                f"Momentaufnahme per {fmt_date_de(auswertungsdatum)}", style_normal))
        story.append(Spacer(1, 2*mm))

        # Kennzahlen
        liq = calc_liquidity(df)
        total_weight = df["Gewicht"].sum()
        meta = [
            f"Anzahl Titel: {len(df)}",
            f"Investitionsgrad: {fmt_pct_de(total_weight)}",
            f"Liquidität: {fmt_pct_de(liq)}",
        ]
        if use_volume:
            meta.append(f"Anlagevolumen: {fmt_eur_de(anlagevolumen)}")
            meta.append(f"Liquidität: {fmt_eur_de(liq * anlagevolumen)}")
        story.append(Paragraph(" | ".join(meta), style_normal))
        story.append(Spacer(1, 4*mm))

        # Ring-Diagramme
        for group_col, chart_title in [
            ("Gattung", "Allokation nach Gattung"),
            ("Region", "Allokation nach Region"),
            ("Segment", "Allokation nach Segment"),
        ]:
            alloc = build_allocation(df, group_col)
            if not alloc.empty:
                ring_buf = _mpl_ring_chart(alloc, group_col, chart_title)
                story.append(RLImage(ring_buf, width=120*mm, height=100*mm))
                story.append(Spacer(1, 3*mm))

        story.append(PageBreak())

        # Einzeltitel-Tabelle
        if logo_path:
            lw_s = 35*mm
            story.append(RLImage(logo_path, width=lw_s, height=lw_s*logo_aspect))
            story.append(Spacer(1, 3*mm))

        story.append(Paragraph(f"Einzeltitel – {label}", style_subtitle))
        title_df = build_title_table(df, anlagevolumen if use_volume else 0.0)
        if not show_ytd:
            for c in ["WP-Performance (YTD)", "Performancebeitrag (YTD)"]:
                if c in title_df.columns:
                    title_df = title_df.drop(columns=[c])
        disp = format_title_table(title_df)

        # DataFrame → reportlab Table
        header = list(disp.columns)
        tdata = [header] + disp.fillna("–").values.tolist()
        n_cols = len(header)
        col_w = (170*mm) / n_cols
        t = Table(tdata, colWidths=[col_w]*n_cols, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), HexColor(FFPB_DARK)),
            ("TEXTCOLOR", (0,0), (-1,0), white),
            ("FONTSIZE", (0,0), (-1,-1), 6),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (2,0), (-1,-1), "RIGHT"),
            ("ALIGN", (0,0), (1,-1), "LEFT"),
            ("GRID", (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, HexColor("#F5F5F5")]),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ]))
        story.append(t)
        story.append(PageBreak())

    # Footer
    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#CCCCCC")))
    story.append(Paragraph(
        f"Erstellt am {fmt_date_de(dt.date.today())} | Fürst Fugger Privatbank", style_small))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
