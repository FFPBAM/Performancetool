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
    DATA_FOLDER, DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS,
    PDF_FONT, PDF_FONT_BOLD,
    fmt_date_de, fmt_pct_de, fmt_eur_de,
    detect_newest_date_tag, get_logo_aspect, get_logo_path,
    csv_name_to_display, load_mapping,
    load_all_csvs, build_portfolio_timeseries,
)
from modules.download_helfer import medien_download_url, download_bereich

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

    for col in ["Gewicht", "Performancebeitrag", "WP-Performance", "Kupon", "Rendite"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("%", "").str.replace(",", ".").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0
    if "Auswertungsdatum" in df.columns:
        df["Auswertungsdatum"] = pd.to_datetime(df["Auswertungsdatum"], format="%d.%m.%Y", errors="coerce")
    if "Fälligkeit" in df.columns:
        df["Fälligkeit_parsed"] = pd.to_datetime(df["Fälligkeit"], format="%d.%m.%Y", errors="coerce")
    # Duration ist eine JAHRES-Zahl (z.B. 3,96), KEIN Prozentwert → nicht /100.
    # "-" und leere Werte werden zu NaN (Nicht-Anleihen).
    if "Duration" in df.columns:
        df["Duration"] = pd.to_numeric(
            df["Duration"].astype(str).str.replace(",", ".").str.strip(),
            errors="coerce")
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
def duration_info_aus_bestand(df: pd.DataFrame) -> dict:
    """Duration + Rendite eines Portfolios anleihe-gewichtet aus den
    Titeldaten (NEU 03.07.2026 — ersetzt den früheren Duration-Ordner).

    Nutzt get_bond_summary (dieselbe Variante-B-Gewichtung wie ⌀ Kupon:
    normiert auf die Anleihen-Gewichtssumme). Verifiziert gegen die
    Tool-Werte "Muster defensiv cVV": Duration 3,96 / Rendite 3,28 %.

    Returns:
        {"duration": float|None, "rendite": float|None} — gleiches Format
        wie zuvor der Duration-Ordner, damit Anzeige UND PPTX-Export
        unverändert damit arbeiten.
    """
    bs = get_bond_summary(df)
    if bs is None:
        return {"duration": None, "rendite": None}
    return {"duration": bs.get("avg_duration"), "rendite": bs.get("avg_rendite")}



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
    # Gattung robust als normale Strings (Arrow-String-dtype kann bei
    # verketteten .str-Ops Probleme machen).
    gattung = df["Gattung"].astype("object").astype(str).str.lower()
    bonds = df[gattung.str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty:
        return None

    # Alle rechen-relevanten Spalten EINMAL deterministisch in float wandeln
    # (03.07.2026). Grund: unter Python 3.14 / pandas-Arrow-Backend sind die
    # Spalten teils Arrow-Strings — dann macht z.B. bonds["Gewicht"].sum()
    # eine String-VERKETTUNG statt Summe ("Can only string multiply…" bzw.
    # "could not convert string to float"). Betrifft total_weight,
    # Fälligkeits-Gewichte UND die gewichteten Mittel.
    def _to_float_series(col):
        werte = []
        for x in col.tolist():
            if x is None or (isinstance(x, float) and np.isnan(x)):
                werte.append(np.nan); continue
            if isinstance(x, (int, float)):
                werte.append(float(x)); continue
            t = str(x).replace("%", "").replace(",", ".").strip()
            werte.append(float(t) if t not in ("", "-", "nan", "None", "<NA>")
                         else np.nan)
        return pd.Series(werte, index=col.index, dtype="float64")

    for _c in ("Gewicht", "Kupon", "Rendite", "Duration"):
        if _c in bonds.columns:
            bonds[_c] = _to_float_series(bonds[_c])

    summary = {"count": len(bonds)}

    # Anleihe-gewichtete Mittelwerte (Variante B: normiert auf die
    # Gewichtssumme der Anleihen, NICHT aufs Gesamtdepot). Verifiziert
    # 03.07.2026 gegen die Tool-Werte "Muster defensiv cVV":
    # Duration 3,96 ✓, Rendite 3,28 %, Kupon 2,71 %. Nur Titel mit
    # vorhandenem Wert gehen ein (Gewichtssumme titelweise gebildet),
    # damit ein einzelner fehlender Wert das Mittel nicht verzerrt.
    def _gewichtetes_mittel(spalte: str):
        if spalte not in bonds.columns:
            return None
        w = bonds["Gewicht"]
        v = bonds[spalte]
        mask = v.notna() & w.notna()
        if not mask.any():
            return None
        w_sum = w[mask].sum()
        if w_sum <= 0:
            return None
        return float((w[mask] * v[mask]).sum() / w_sum)

    summary["avg_kupon"]    = _gewichtetes_mittel("Kupon")
    summary["avg_duration"] = _gewichtetes_mittel("Duration")
    summary["avg_rendite"]  = _gewichtetes_mittel("Rendite")
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
# ─────────────────────────────────────────────────────────────────────────────
# Vorlagen-Familien (NEU 06.07.2026): Steuert, welche PowerPoint-Vorlage +
# Folienstruktur eine Strategie bekommt. Die Zuordnung kommt aus der
# Mapping-Spalte "Powerpoint Familie" (leer = Standard-Broschüre).
#
# Variante A (familiengesteuert): Der Berater wählt NUR die Strategie; die
# Familie im Mapping bestimmt automatisch die Vorlage — keine zusätzliche
# Auswahl, keine Fehlbedienung möglich.
#
# WICHTIG für Rückwärtskompatibilität: Ist die Familie leer/unbekannt ODER
# fehlt die Vorlagen-Datei, wird template_path/template_config = None
# durchgereicht → exakt der bisherige Standard-Export (Vorlage_FFPB.pptx).
# ─────────────────────────────────────────────────────────────────────────────

SPALTE_PP_FAMILIE = "Powerpoint Familie"


def _folien_config(folien, rollen_optionen=None, entfernen=None):
    """Baut ein ``template_config`` aus einer GEORDNETEN Folienliste.

    Idee: Man beschreibt die Broschüre Folie für Folie in Reihenfolge — die
    Folienposition ergibt sich automatisch aus dem Listenindex (Position =
    Index + 1). Kommt eine statische Folie dazu, fügt man EINEN Eintrag ein;
    alle folgenden Positionen verschieben sich von allein. Kein Umnummerieren.

    Jeder Eintrag ist ein Tupel (das Label am Ende ist REINE Dokumentation und
    fließt NICHT in die Logik ein — ein Tippfehler im Label kann die
    Generierung also nie brechen):

        ("S", "Label")            – statische Folie (Generator fasst sie nie an)
        ("<rolle>", n, "Label")   – dynamische Folie der Strategie n (0-basiert)
        ("<rolle>", "*", "Label") – Einmal-Folie (läuft einmal für alle Strategien)

    Rollen wie im Export-Dispatch: anlagevorschlag, wertentwicklung, performance,
    zusammenstellung, rollierend, einzeltitel_themen (dynamisch) bzw.
    uebersicht, vergleich (einmal).

    Erzeugt EXAKT die Struktur, die pptx_export.generate_portfolioanalyse_pptx
    schon versteht (erwartete_folien / feste_bloecke / einmal_folien /
    rollen_optionen / entfernen) — der Export bleibt unangetastet.
    """
    feste = {}    # strategie-index (int) -> {rolle: 1-indexierte Position}
    einmal = {}   # rolle -> 1-indexierte Position
    for i, eintrag in enumerate(folien):
        pos = i + 1
        rolle = eintrag[0]
        if str(rolle).upper() == "S":          # statische Folie -> ueberspringen
            continue
        strat = eintrag[1]
        if strat == "*":
            einmal[rolle] = pos
        else:
            feste.setdefault(int(strat), {})[rolle] = pos

    if feste:
        # Liste in Strategie-Reihenfolge 0,1,2,... (fehlende Indizes -> leerer Block)
        feste_bloecke = [feste.get(k, {}) for k in range(max(feste) + 1)]
    else:
        feste_bloecke = []

    cfg = {
        "erwartete_folien": len(folien),
        "entfernen": list(entfernen or []),
        "feste_bloecke": feste_bloecke,
        "rollen_optionen": dict(rollen_optionen or {}),
    }
    # einmal_folien NUR anlegen, wenn es Einmal-Folien gibt.
    if einmal:
        cfg["einmal_folien"] = einmal
    return cfg

# Struktur-Block der THEMEN-Broschüren (Pro / Pro Dividende / Offensiv teilen
# sich diese eine Vorlage + Struktur). Verifiziert an der echten Vorlage:
# 21 Folien, dynamischer Block F10-F13 mit den Rollen einzeltitel_themen /
# zusammenstellung / wertentwicklung / rollierend.
_THEMA_CONFIG = {
    "block_reihenfolge": ["einzeltitel_themen", "zusammenstellung",
                          "wertentwicklung", "rollierend"],
    "block_positionen": {
        "einzeltitel_themen": 10,
        "zusammenstellung": 11,
        "wertentwicklung": 12,
        "rollierend": 13,
    },
    "erwartete_folien": 21,
    "entfernen": [],
}

# Struktur der CVV-Broschüre ("cVV Infoboard", NEU 09.07.2026).
#
# BESONDERHEIT gegenüber allen anderen Familien: Die Vorlage enthält die
# Folien ALLER FÜNF Strategien bereits fertig vorgebaut — jede mit ihrem
# eigenen, STARREN Anlagekriterien-Kasten (Folien 7/9/11/13/15) und der
# zugehörigen Wertentwicklungs-Folie (8/10/12/14/16). Der Block darf deshalb
# NICHT dupliziert werden (sonst bekämen alle Strategien den Kasten der
# ersten). Stattdessen: "feste_bloecke" → pptx_export befüllt an festen
# Vorlagen-Positionen, ohne _normalisiere_vorlage/_vervielfaeltige_block.
#
# Verifiziert an der echten Vorlage (37 Folien):
#   F7/9/11/13/15 : Titel + Anlagekriterien-Kasten + C_Kennzahlen (Ring)
#                   + T_Kennzahlen (11 Spalten, wie Standard-Anlagevorschlag)
#   F8/10/12/14/16: Diagramm rechts/links + Kennzahlen-Tabelle
#                   (identisch zur Rolle "wertentwicklung")
#   F17 (8x13) und F19 (Linien-Chart, 5 Serien) werden NOCH NICHT befüllt
#   (Stufe 2/3) und zeigen bis dahin die Vorlagen-Daten.
_CVV_STRATEGIEN = [
    "cVV konservativ",
    "cVV defensiv",
    "cVV defensiv plus",
    "cVV ausgewogen",
    "cVV dynamic",
]
"""Feste Reihenfolge der CVV-Strategien — MUSS zur Foliennummerierung der
Vorlage passen (Konservativ=F7, Defensiv=F9, Defensiv Plus=F11,
Ausgewogen=F13, Dynamic=F15). Namen wie in der Mapping-Spalte
'Strategie auswählen'."""

_CVV_CONFIG = {
    "erwartete_folien": 37,
    "entfernen": [],
    # Ein Eintrag je Strategie, in der Reihenfolge von _CVV_STRATEGIEN.
    # Werte sind 1-indexierte Vorlagen-Positionen.
    "feste_bloecke": [
        {"anlagevorschlag": 7,  "wertentwicklung": 8},
        {"anlagevorschlag": 9,  "wertentwicklung": 10},
        {"anlagevorschlag": 11, "wertentwicklung": 12},
        {"anlagevorschlag": 13, "wertentwicklung": 14},
        {"anlagevorschlag": 15, "wertentwicklung": 16},
    ],
    # Vorlagenspezifische Optionen je Rolle:
    # - titel_text="": Vorlagen-Titel ("Anlagestrategie Konservativ") behalten,
    #   statt ihn durch "Strategieentwurf …" zu ersetzen.
    # - max_bottom_inch=6.20: die blaue Abschlusslinie liegt bei 6.38"
    #   (Standard-Vorlage: 6.60").
    # - original_row_h_inch=0.192: die CVV-Tabelle hat höhere Zeilen als die
    #   Standard-Vorlage (0.1424"); sonst greift die Stauchungs-Untergrenze
    #   zu früh und die Tabelle läuft über die Abschlusslinie.
    "rollen_optionen": {
        "anlagevorschlag": {"titel_text": "", "max_bottom_inch": 6.20,
                            "original_row_h_inch": 0.192},
    },
    # Folien, die EINMAL für alle fünf Strategien laufen (nicht je Strategie):
    # F17 = "Wertentwicklung der klassischen Vermögensverwaltungsstrategien",
    # Zeiträume YTD/1/3/5/10 Jahre in den Zeilen, Strategien in den Spalten.
    # Quelle: compute_rollierend_data() je Strategie — dieselbe Mathematik wie
    # die Themen-Broschüren-Tabelle (Konsistenz-Doktrin).
    # F19 = Linien-Chart "Klassische VV Strategien im Vergleich (nach Kosten)",
    # 5 Serien, Index 100 je Strategie ab ihrem EIGENEN Start (Dynamic beginnt
    # später → Lücke, keine Nulllinie).
    "einmal_folien": {"uebersicht": 17, "vergleich": 19},
}

# Struktur der ESG-Broschüre ("ESG Infoboard", NEU 10.07.2026).
#
# Gleicher Bauplan wie CVV (feste Blöcke, Kästen unterscheiden sich je
# Strategie), aber VIER Strategien und OHNE Vergleichs-Linienchart.
# Verifiziert an der echten Vorlage (39 Folien):
#   F16/18/20/22 : Titel + Anlagekriterien-Kasten + C_Kennzahlen (Ring)
#                  + T_Kennzahlen (11 Spalten)
#   F17/19/21/23 : Rolle "wertentwicklung"
#   F24          : Übersichtstabelle 8x11, Strategien in den Spalten 4/6/8/10
_ESG_STRATEGIEN = [
    "ESG defensiv",
    "ESG defensiv+",      # Folientitel: "ESG Defensiv Plus"
    "ESG ausgewogen",
    "ESG offensiv",
]
"""Feste Reihenfolge — MUSS zur Foliennummerierung passen (Defensiv=F16,
Defensiv Plus=F18, Ausgewogen=F20, Offensiv=F22). Namen wie in der
Mapping-Spalte 'Strategie auswählen'."""

_ESG_CONFIG = {
    "erwartete_folien": 39,
    "entfernen": [],
    "feste_bloecke": [
        {"anlagevorschlag": 16, "wertentwicklung": 17},
        {"anlagevorschlag": 18, "wertentwicklung": 19},
        {"anlagevorschlag": 20, "wertentwicklung": 21},
        {"anlagevorschlag": 22, "wertentwicklung": 23},
    ],
    "rollen_optionen": {
        # Abschlusslinie bei 6.38", Zeilenhöhe 0.192" — wie CVV.
        "anlagevorschlag": {"titel_text": "", "max_bottom_inch": 6.20,
                            "original_row_h_inch": 0.192},
        # NUR VIER Strategien → eine Wertspalte weniger als bei CVV.
        "uebersicht": {"spalten": [4, 6, 8, 10]},
    },
    "einmal_folien": {"uebersicht": 24},
}

# Struktur der ETF-Broschüre ("ETF Infoboard", NEU 20.07.2026).
#
# Gleicher Bauplan wie ESG (feste Blöcke, kein Vergleichs-Linienchart), aber
# ZWEI Strategien. BESONDERHEIT: Die ETF-T_Kennzahlen-Tabelle hat nur 7 Spalten
# (WERTPAPIER/WKN/Anteil/Marktrisikowert) OHNE KUPON/FÄLLIGKEIT — ETFs sind
# keine Renten. Deshalb bekommt die Rolle "anlagevorschlag" ein eigenes
# spalten_map (Schema siehe pptx_slides.DEFAULT_SPALTEN_MAP); die restliche
# Fill-Logik ist identisch.
# Verifiziert an der echten Vorlage (35 Folien):
#   F16/18 : Titel + Anlagekriterien-Kasten + C_Kennzahlen (Ring)
#            + T_Kennzahlen (7 Spalten, mit Marktrisikowert)
#   F17/19 : Rolle "wertentwicklung" (Diagramm links/rechts + Kennzahlen)
#   F20    : Übersichtstabelle 8x8, Strategien in den Spalten 4/6
_ETF_STRATEGIEN = [
    "ETF_ausgewogen",
    "ETF_Wachstum",
]
"""Feste Reihenfolge — MUSS zur Foliennummerierung passen (Ausgewogen=F16,
Wachstum=F18). Namen wie in der Mapping-Spalte 'Strategie auswählen'."""

_ETF_CONFIG = {
    "erwartete_folien": 35,
    "entfernen": [],
    "feste_bloecke": [
        {"anlagevorschlag": 16, "wertentwicklung": 17},
        {"anlagevorschlag": 18, "wertentwicklung": 19},
    ],
    "rollen_optionen": {
        # titel_text="": Vorlagen-Titel ("Anlagestrategie ESG-ETF Ausgewogen")
        #   behalten. max_bottom_inch/row_h an der ETF-Vorlage kalibrieren.
        # spalten_map: 7-Spalten-Layout OHNE Kupon/Fälligkeit (ETF-spezifisch).
        "anlagevorschlag": {
            "titel_text": "", "max_bottom_inch": 6.20,
            "original_row_h_inch": 0.34,
            "spalten_map": {
                "wertpapier": 0, "kupon": None, "faelligkeit": None,
                "wkn": 2, "anteil": 4, "rating": 6, "spacers": [1, 3, 5],
            },
        },
        # NUR ZWEI Strategien → Ausgewogen=Spalte 4, Wachstum=Spalte 6.
        "uebersicht": {"spalten": [4, 6]},
    },
    "einmal_folien": {"uebersicht": 20},
}

# Struktur der comdirect-Broschüre ("Klassische Portfolioverwaltung", NEU 21.07.2026).
#
# Gleicher Bauplan wie ESG/CVV (feste Blöcke), aber DREI Strategien und
# BESONDERS EINFACH: T_Kennzahlen ist 11-spaltig (Standard-Layout → KEIN
# spalten_map nötig) und es gibt KEINE dynamische Vergleichsfolie (F5 =
# statische Strategie-Beschreibung, F21 = Firmen-AuM-Wachstum → beide statisch,
# also KEIN einmal_folien). Damit ist es eine reine Config-Ergänzung.
# Verifiziert an der echten Vorlage (27 Folien):
#   F6/8/10 : Titel "Anlagestrategie Portfolioverwaltung 30/70/100"
#             + Anlagekriterien-Kasten + C_Kennzahlen (Ring)
#             + T_Kennzahlen (11 Spalten, mit Marktrisikowert)
#   F7/9/11 : Rolle "wertentwicklung" (Diagramm links/rechts + Kennzahlen)
_COMDIRECT_STRATEGIEN = [
    "Comdirect_30",
    "Comdirect_70",
    "Comdirect_100",
]
"""Feste Reihenfolge — MUSS zur Foliennummerierung passen (30=F6, 70=F8,
100=F10). Namen wie in der Mapping-Spalte 'Strategie auswählen'."""

_COMDIRECT_CONFIG = _folien_config(
    # Broschüre Folie für Folie (Position = Listenindex+1). Neue statische
    # Folie? Einfach EINEN ("S", "…")-Eintrag an der richtigen Stelle einfügen —
    # alle folgenden Positionen verschieben sich von allein. Labels sind reine
    # Doku (Titel der echten Vorlagenfolien), ändern die Logik nicht.
    folien=[
        ("S", "Titelseite – Unabhängig. Werteorientiert. Persönlich."),
        ("S", "Unsere Portfolioverwaltung"),
        ("S", "Vermögenserhalt und langfristiges Wachstum"),
        ("S", "Aufteilung zur Risikobegrenzung"),
        ("S", "Die drei klassischen Strategien (Übersicht)"),
        ("anlagevorschlag", 0, "PV 30 – Anlagestrategie (Ring + Positionen)"),
        ("wertentwicklung", 0, "PV 30 – Performance"),
        ("anlagevorschlag", 1, "PV 70 – Anlagestrategie (Ring + Positionen)"),
        ("wertentwicklung", 1, "PV 70 – Performance"),
        ("anlagevorschlag", 2, "PV 100 – Anlagestrategie (Ring + Positionen)"),
        ("wertentwicklung", 2, "PV 100 – Performance"),
        ("S", "Verwaltungsvergütung"),
        ("S", "Transaktionskosten"),
        ("S", "Unser Honorar"),
        ("S", "Steuerlicher Hinweis zum Honorar"),
        ("S", "Langfristiger Vermögenserhalt"),
        ("S", "Die optimale Vermögensverwaltungsstrategie"),
        ("S", "Zinsänderungsrisiko"),
        ("S", "Kombination verschiedener Anlageklassen"),
        ("S", "Regelmäßige Berichte"),
        ("S", "Wesentliche Finanzkennzahlen (AuM-Wachstum)"),
        ("S", "Individuell. Unabhängig. Vertrauensvoll."),
        ("S", "Anschreiben"),
        ("S", "Kluge Investitionen (ländlicher Grundbesitz)"),
        ("S", "Risikohinweise"),
        ("S", "Rechtliche Hinweise und Impressum"),
        ("S", "Stand / Rückseite"),
    ],
    # titel_text="": Vorlagen-Titel behalten. max_bottom_inch/row_h an der
    # Vorlage gemessen (Tabelle endet bei 6.36", Zeilenhöhe ~0.21") — nach
    # echtem Deploy ggf. feinjustieren. KEIN spalten_map (11 Spalten wie ESG).
    rollen_optionen={
        "anlagevorschlag": {"titel_text": "", "max_bottom_inch": 6.20,
                            "original_row_h_inch": 0.21},
    },
)

# Familie → (Vorlagen-Dateiname im Ordner Vorlage/, template_config).
# Nur Familien mit EIGENER Vorlage hier eintragen. Familien ohne Eintrag
# (oder leere Familie) → Standard-Vorlage (Vorlage_FFPB.pptx, config None).
VORLAGEN_FAMILIEN = {
    "Thema": ("Vorlage_Thema.pptx", _THEMA_CONFIG),
    "CVV": ("Vorlage_cVV_Infoboard.pptx", _CVV_CONFIG),
    "ESG": ("Vorlage_ESG.pptx", _ESG_CONFIG),
    "ETF": ("Vorlage_ETF.pptx", _ETF_CONFIG),
    "comdirect": ("Vorlage_comdirect.pptx", _COMDIRECT_CONFIG),
}

# Familien, deren Broschüre IMMER alle Strategien enthält (Variante A).
# Wählt der Berater eine davon, lädt die App automatisch alle — in dieser
# Reihenfolge. Neue Familie? Nur hier und in VORLAGEN_FAMILIEN eintragen.
FAMILIE_ALLE_STRATEGIEN = {
    "CVV": _CVV_STRATEGIEN,
    "ESG": _ESG_STRATEGIEN,
    "ETF": _ETF_STRATEGIEN,
    "comdirect": _COMDIRECT_STRATEGIEN,
}


# ══════════════════════════════════════════════════════════════════════════
#  AUSGABE-DATEINAMEN DER BROSCHÜRE — hier frei anpassbar
# ══════════════════════════════════════════════════════════════════════════
# Der Name der heruntergeladenen PowerPoint wird aus diesen drei Dicts gebaut.
# NUR HIER etwas ändern — der restliche Code bleibt gleich.
#
# Auflösung in dieser Reihenfolge (erster Treffer gewinnt):
#   1. EXPORT_NAME_STRATEGIE[<Strategie>]   – einzelne Strategie (höchste Prio)
#   2. EXPORT_NAME_FAMILIE[<Familie>]        – ganze Familie
#   3. EXPORT_NAME_DEFAULT                   – alles ohne eigenen Eintrag
#
# Platzhalter im Muster:  {datum}  {strategie}  {familie}
# Die Endung ".pptx" wird AUTOMATISCH angehängt — NICHT ins Muster schreiben.
#
# Datum: standardmäßig EXPORT_DATUM_FORMAT (strftime). Ein Eintrag kann ein
# eigenes Format bekommen, indem statt "Muster" ein Tupel ("Muster", "%Y%m%d")
# angegeben wird (siehe comdirect). {datum} = Auswertungsdatum der Portfolio-
# analyse; fehlt es, wird der Date-Tag aus dem UI (yyMMdd) eingesetzt.

EXPORT_DATUM_FORMAT = "%d.%m.%Y"          # z.B. 07.07.2026

EXPORT_NAME_DEFAULT = "Portfolioanalyse_{strategie}_{datum}"

# Ganze Familie → ein Name (Wert = "Muster" ODER ("Muster", "datumsformat")).
EXPORT_NAME_FAMILIE = {
    "CVV":       "cVV Broschüre_Infoboard_{datum}",
    "ETF":       "ETF Broschüre Infoboard {datum}",
    "ESG":       "ESG Broschüre Inforboard{datum}",
    "comdirect": ("Klassische Portfolioverwaltung_{datum}", "%Y%m%d"),
    "Thema":     "{strategie} Broschüre_{datum}",   # → "Pro Broschüre_…", "Pro Dividende Broschüre_…"
}

# Einzelne Strategie → eigener Name (schlägt die Familie). Beispiel: die
# Thema-Strategie heißt "Offensiv", der Broschürenname soll aber "Offensive"
# sein. Weitere Ausnahmen einfach hier ergänzen.
EXPORT_NAME_STRATEGIE = {
    "Offensiv": "Offensive Broschüre_{datum}",
}
# ══════════════════════════════════════════════════════════════════════════


def _familien_portfolios(strategien, display_names_pf, display_to_csv_pf,
                         pf_data, duration_info_fn):
    """Stellt ALLE Portfolios einer Broschüren-Familie in fester Reihenfolge
    zusammen (generisch seit 10.07.2026, vorher _cvv_portfolios).

    CVV- und ESG-Broschüren sind Gesamtdokumente über alle Strategien ihrer
    Familie. Der Berater wählt nur EINE — geladen werden trotzdem alle
    ("Variante A": keine Zusatzauswahl, keine Fehlbedienung). Fehlt eine, gibt
    es eine klare Diagnose statt einer halben Broschüre.

    Args:
        strategien: Namen in der Reihenfolge der VORLAGEN-Folien.
                    MUSS zur Foliennummerierung passen.

    Returns:
        (portfolios, fehlende) — portfolios: Liste von
        (display_name, df, auswertungsdatum, duration_info).
    """
    def _norm_s(s):
        return "".join(str(s).lower().split())

    vorhanden = {_norm_s(n): n for n in display_names_pf}
    portfolios, fehlende = [], []
    for wunsch in strategien:
        treffer = vorhanden.get(_norm_s(wunsch))
        if treffer is None:
            fehlende.append(wunsch)
            continue
        csv_name = display_to_csv_pf.get(treffer)
        df = pf_data.get(csv_name) if csv_name else None
        if df is None or getattr(df, "empty", True):
            fehlende.append(wunsch)
            continue
        ad = (df["Auswertungsdatum"].iloc[0]
              if "Auswertungsdatum" in df.columns and df["Auswertungsdatum"].notna().any()
              else None)
        portfolios.append((treffer, df, ad, duration_info_fn(df)))
    return portfolios, fehlende


def _finde_familie_spalte(name_mapping):
    """Findet die 'Powerpoint Familie'-Spalte tolerant (egal ob 'PowerPoint
    Familie', Extra-/fehlende Leerzeichen, Groß-/Kleinschreibung, Umbrüche).
    Returns den echten Spaltennamen oder None."""
    def _norm(s):
        # alle Whitespaces (auch Umbrüche/doppelte) zu einem Space, klein
        return " ".join(str(s).split()).strip().lower()
    ziel = _norm(SPALTE_PP_FAMILIE)  # "powerpoint familie"
    for col in name_mapping.columns:
        if _norm(col) == ziel:
            return col
    return None


def _familie_fuer_strategie(name_mapping, display_name):
    """Liest die 'Powerpoint Familie' einer Strategie aus dem Mapping.
    Toleriert abweichende Spalten-Schreibweisen und Wert-Groß/Kleinschreibung.
    Returns den KANONISCHEN Familien-String (Schlüssel aus VORLAGEN_FAMILIEN,
    z.B. 'Thema') oder '' wenn leer/nicht vorhanden."""
    try:
        spalte = _finde_familie_spalte(name_mapping)
        if spalte is None:
            return ""
        col_display = name_mapping.columns[0]
        treffer = name_mapping.loc[
            name_mapping[col_display].astype(str).str.strip() == str(display_name).strip(),
            spalte]
        if treffer.empty:
            return ""
        wert = treffer.iloc[0]
        if wert is None or (isinstance(wert, float) and pd.isna(wert)):
            return ""
        wert = " ".join(str(wert).split()).strip()  # Whitespace normalisieren
        if wert.lower() in ("", "nan", "none"):
            return ""
        # Wert case-insensitiv auf den kanonischen Familien-Schlüssel abbilden
        # (damit "thema"/"THEMA" den Eintrag "Thema" trifft).
        for kanon in VORLAGEN_FAMILIEN:
            if wert.lower() == kanon.lower():
                return kanon
        return wert  # unbekannte Familie (z.B. CVV ohne Vorlage) unverändert
    except Exception:
        return ""


def _vorlage_fuer_familie(familie):
    """Familie → (template_path|None, template_config|None).

    Gibt (None, None) zurück, wenn die Familie leer/unbekannt ist ODER die
    Vorlagen-Datei nicht gefunden wird → Standard-Export (rückwärtskompatibel).

    Der Pfad wird vom funktionierenden Standard-TEMPLATE_PATH abgeleitet
    (gleiches Verzeichnis wie Vorlage_FFPB.pptx), damit er in JEDER
    Ausführungsumgebung (Streamlit Cloud, lokal) am selben Ort sucht wie die
    Standard-Vorlage — statt relativ zum aktuellen Arbeitsverzeichnis.
    """
    if not familie or familie not in VORLAGEN_FAMILIEN:
        return None, None
    dateiname, config = VORLAGEN_FAMILIEN[familie]
    import os as _os
    kandidaten = []
    # 1) Neben der Standard-Vorlage (identisches Verzeichnis wie TEMPLATE_PATH)
    try:
        from modules.pptx_export import TEMPLATE_PATH as _std
    except Exception:
        try:
            from pptx_export import TEMPLATE_PATH as _std
        except Exception:
            _std = _os.path.join("Vorlage", "Vorlage_FFPB.pptx")
    kandidaten.append(_os.path.join(_os.path.dirname(_std), dateiname))
    # 2) Relativ zum App-Root (klassisch)
    kandidaten.append(_os.path.join("Vorlage", dateiname))
    # 3) Relativ zu diesem Modul (falls CWD abweicht)
    kandidaten.append(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                    "..", "Vorlage", dateiname))
    for pfad in kandidaten:
        if _os.path.exists(pfad):
            return pfad, config
    # Keiner existiert → Standard (kein Crash). Der aufrufende Code meldet das.
    return None, None


def _export_name_saeubern(name: str) -> str:
    """Entfernt NUR dateisystem-illegale Zeichen (\\ / : * ? " < > |) und
    verdichtet Mehrfach-Leerzeichen. Punkte und Leerzeichen bleiben ERHALTEN
    (die konfigurierten Namen nutzen genau die). Der clientseitige Download
    (download_helfer.py) übernimmt den Namen anschließend unverändert."""
    import re as _re
    name = _re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = _re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "Broschuere"


def _export_dateiname(name_mapping, strategie, datum, fallback_tag) -> str:
    """Baut den Dateinamen der exportierten Broschüre aus der Konfiguration
    oben (EXPORT_NAME_STRATEGIE / EXPORT_NAME_FAMILIE / EXPORT_NAME_DEFAULT).

    strategie   : gewählte Strategie (Anzeigename = pf_sel_1)
    datum       : Auswertungsdatum (date/Timestamp) ODER None
    fallback_tag: Ersatz-Datumsstring (yyMMdd aus dem UI), falls kein
                  Auswertungsdatum vorliegt

    Rückgabe inkl. ".pptx". Bricht NIE hart ab — bei defektem Muster
    (z.B. unbekannter Platzhalter) wird auf den Default zurückgefallen.
    """
    familie = ""
    try:
        familie = _familie_fuer_strategie(name_mapping, strategie) or ""
    except Exception:
        familie = ""

    eintrag = (EXPORT_NAME_STRATEGIE.get(strategie)
               or EXPORT_NAME_FAMILIE.get(familie)
               or EXPORT_NAME_DEFAULT)
    if isinstance(eintrag, (tuple, list)) and len(eintrag) >= 2:
        muster, datum_fmt = eintrag[0], eintrag[1]
    else:
        muster, datum_fmt = eintrag, EXPORT_DATUM_FORMAT

    if datum is not None:
        try:
            datum_str = datum.strftime(datum_fmt)
        except Exception:
            datum_str = str(fallback_tag)
    else:
        datum_str = str(fallback_tag)

    try:
        name = muster.format(datum=datum_str, strategie=strategie, familie=familie)
    except Exception:
        # Defektes Muster (unbekannter Platzhalter o.ä.) → sicherer Default
        name = EXPORT_NAME_DEFAULT.format(datum=datum_str, strategie=strategie,
                                          familie=familie)
    return _export_name_saeubern(name) + ".pptx"


def _render_familien_hinweis(name_mapping, strategie):
    """Zeigt NUR bei Familien-Strategien einen Hinweis, dass die Broschüre immer
    ALLE Strategien der Familie enthält — auch wenn nur eine ausgewählt ist.
    Kontextbezogen (nennt Familie + alle Strategien). Bei Einzel-Strategien
    (keine Familie in FAMILIE_ALLE_STRATEGIEN) wird nichts angezeigt."""
    import streamlit as st
    try:
        familie = _familie_fuer_strategie(name_mapping, strategie) or ""
    except Exception:
        familie = ""
    strategien = FAMILIE_ALLE_STRATEGIEN.get(familie)
    if not strategien:
        return
    liste = ", ".join(strategien)
    st.info(
        f'ℹ️ **{familie}-Broschüre:** Enthält immer **alle '
        f'{len(strategien)} Strategien** der {familie}-Familie ({liste}) — '
        f'auch wenn oben nur „{strategie}“ ausgewählt ist.'
    )


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
    # Duration/Rendite anleihe-gewichtet aus den Titeln (Duration-Ordner
    # entfällt seit 03.07.2026).
    dur_1 = duration_info_aus_bestand(df_pf_1)

    show_compare_pf = st.checkbox("Vergleichsportfolio anzeigen", value=False, key="pf_compare")
    pf_sel_2 = csv_name_2 = df_pf_2 = dur_2 = None
    if show_compare_pf:
        pf_sel_2 = st.selectbox("Vergleichsportfolio auswählen", display_names_pf, key="pf_sel_2")
        csv_name_2 = display_to_csv_pf[pf_sel_2]; df_pf_2 = pf_data[csv_name_2]
        dur_2 = duration_info_aus_bestand(df_pf_2)

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

    # Cache-Key aus aktueller Auswahl (ändert sich → Cache ungültig → Download-Button verschwindet)
    compare_key = pf_sel_2 if (show_compare_pf and df_pf_2 is not None) else "single"
    current_key = f"{pf_sel_1}|{compare_key}|{date_tag_pf}|{anlagevolumen}|{show_ytd}|{pf_brutto_mwst}|{_familie_fuer_strategie(name_mapping, pf_sel_1)}"

    # Cache invalidieren wenn Auswahl geändert wurde
    if st.session_state.get("pf_export_key") != current_key:
        st.session_state.pop("pf_pptx_bytes", None)
        st.session_state.pop("pf_pptx_build_errors", None)
        st.session_state["pf_export_key"] = current_key

    # ── PowerPoint Export (einziger Export) ──
    if True:
        if "pf_pptx_bytes" not in st.session_state:
            # Button zum Generieren
            if st.button("📊 PowerPoint erstellen", key="pf_pptx_btn", use_container_width=True,
                         help="Exportiert die Portfolioanalyse in die Corporate-Vorlage (Folien 7-10)."):
                portfolios = [(pf_sel_1, df_pf_1, ad1, dur_1)]
                if show_compare_pf and df_pf_2 is not None:
                    portfolios.append((pf_sel_2, df_pf_2, ad2, dur_2))

                # ── CVV: IMMER alle fünf Strategien (NEU 09.07.2026) ────────
                # Die CVV-Vorlage ist ein Gesamtdokument über alle fünf
                # klassischen VV-Strategien mit fest vorgebauten Folien. Die
                # Vergleichsauswahl wird hier bewusst ignoriert.
                # name_mapping ist bereits geladen (oben in der Ansicht)
                _fam_vorab = _familie_fuer_strategie(name_mapping, pf_sel_1)
                _alle = FAMILIE_ALLE_STRATEGIEN.get(_fam_vorab)
                if _alle:
                    _fam_pfs, _fehlend = _familien_portfolios(
                        _alle, display_names_pf, display_to_csv_pf, pf_data,
                        duration_info_aus_bestand)
                    if _fehlend:
                        st.error(
                            f"❌ {_fam_vorab}-Broschüre: Für diese Strategien fehlen "
                            f"die Portfolio-Daten: {', '.join(_fehlend)}.\n\n"
                            f"Die Broschüre enthält immer alle {len(_alle)} Strategien — "
                            "bitte die fehlenden CSVs in `Daten_PF/` ergänzen.")
                        st.stop()
                    portfolios = _fam_pfs

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
                    # Duration: dur_info ist das Dict aus
                    # duration_info_aus_bestand ({"duration", "rendite"},
                    # anleihe-gewichtet aus den Titeln).
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
                        # Familie der gewählten Strategie bestimmt die Vorlage
                        # (Variante A). Leere/unbekannte Familie oder fehlende
                        # Vorlagen-Datei → (None, None) = Standard-Export.
                        _familie = _familie_fuer_strategie(name_mapping, pf_sel_1)
                        _tpl_path, _tpl_cfg = _vorlage_fuer_familie(_familie)
                        if _familie and not _tpl_path:
                            pptx_diag.append(
                                f"Familie '{_familie}' hat (noch) keine Vorlage "
                                f"im Ordner Vorlage/ — Standard-Broschüre verwendet.")
                        st.session_state["pf_pptx_bytes"] = generate_portfolioanalyse_pptx(
                            portfolios, anlagevolumen,
                            performance_inputs=performance_inputs,
                            template_path=_tpl_path, template_config=_tpl_cfg,
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
                    # Bei "Package not found" gezielt diagnostizieren: existiert
                    # die Datei am Ladeort wirklich, wie groß ist sie (ein
                    # Git-LFS-Zeiger ist nur ~130 Bytes!), was liegt im Ordner?
                    import os as _osd
                    diag = [f"❌ Fehler beim PowerPoint-Export: {e}"]
                    try:
                        _p = locals().get("_tpl_path")
                        if _p:
                            if _osd.path.exists(_p):
                                _sz = _osd.path.getsize(_p)
                                diag.append(f"Datei {_p} existiert, Größe {_sz} Bytes.")
                                if _sz < 5000:
                                    diag.append("⚠️ Sehr klein — das ist vermutlich ein "
                                                "Git-LFS-Zeiger statt der echten PPTX. "
                                                "Die Vorlage muss als normale Binärdatei "
                                                "(nicht über Git LFS) im Repo liegen.")
                            else:
                                _dir = _osd.path.dirname(_p) or "."
                                vorhanden = _osd.listdir(_dir) if _osd.path.isdir(_dir) else "Ordner fehlt"
                                diag.append(f"Datei {_p} NICHT am Ladeort. Im Ordner "
                                            f"'{_dir}' liegt: {vorhanden}")
                    except Exception:
                        pass
                    st.error("\n\n".join(diag))
        else:
            # Diagnose aus dem letzten Export-Lauf anzeigen (überlebt st.rerun)
            for _diag_msg in st.session_state.get("pf_pptx_build_errors", []):
                st.warning(f"⚠️ {_diag_msg}")

            # Dateiname aus der konfigurierbaren Sektion oben (EXPORT_NAME_*).
            # Familie/Strategie/Datum werden dort zum finalen Namen aufgelöst;
            # ad1 = Auswertungsdatum, date_tag_pf = Fallback (yyMMdd aus UI).
            _dateiname = _export_dateiname(name_mapping, pf_sel_1, ad1, date_tag_pf)
            # Kompletter Download-Bereich (Neuer-Tab-Varianten für den
            # Atruvia-Gateway-Scan + klassischer In-Page-Fallback) liegt in
            # modules/download_helfer.py → download_bereich(). Künftige
            # Anpassungen am Download passieren NUR dort, nicht hier.
            download_bereich(st.session_state["pf_pptx_bytes"], _dateiname)
        # Kontextbezogener Familien-Hinweis (immer unter dem Button).
        _render_familien_hinweis(name_mapping, pf_sel_1)

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

        # Duration/Rendite bevorzugt aus den TITELN (get_bond_summary, seit
        # 03.07.2026, anleihe-gewichtet, verifiziert gegen Tool: 3,96 / 3,28%);
        # duration_info aus dem Duration-Ordner nur als Fallback, falls die
        # Titel keine Duration/Rendite tragen (Abwärtskompatibilität).
        dur_val = bond_summary.get("avg_duration")
        if dur_val is None and duration_info is not None:
            dur_val = duration_info.get("duration")
        ren_val = bond_summary.get("avg_rendite")
        if ren_val is None and duration_info is not None:
            ren_val = duration_info.get("rendite")

        # Anzahl Kennzahlen-Spalten dynamisch
        has_duration = dur_val is not None
        has_rendite = ren_val is not None
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
                    help="Gewichteter Durchschnittskupon aller Anleihen im Portfolio "
                         "(gewichtet nach Anleihe-Gewicht).")
            else:
                st.metric("⌀ Kupon", "–")
            col_idx += 1
        if has_duration:
            with bcols[col_idx]:
                st.metric("Duration (Portfolio)", f"{dur_val:.2f}".replace(".", ","),
                    help="Anleihe-gewichtete Duration des Rentenportfolios. Misst die "
                         "Zinssensitivität: Um wie viel Prozent der Rentenwert fällt, "
                         "wenn das Zinsniveau um 1 Prozentpunkt steigt. Einheit: Jahre.")
                col_idx += 1
        if has_rendite:
            with bcols[col_idx]:
                st.metric("Rendite (Portfolio)", fmt_pct_de(ren_val),
                    help="Anleihe-gewichtete Rendite bis Fälligkeit (Yield to Maturity): "
                         "erwartete jährliche Rendite, wenn alle Anleihen bis zur "
                         "Fälligkeit gehalten werden.")

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
