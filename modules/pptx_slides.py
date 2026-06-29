"""
modules/pptx_slides.py — Slide-Befüllungs-Logik für die FFPB-Broschüre.

Domain-spezifische Funktionen für die drei Folien der Broschüre:
- Slide 7: Anlagevorschlag (Tabelle + Allokations-Ring)
- Slide 8: Performance (Kennzahlen + 2 Charts)
- Slide 9: Aktuelle Portfoliozusammenstellung (2 Ring-Charts)

Dieses Modul kennt die FFPB-Vorlage, die Shape-Namen, die Asset-Klassen-
Klassifizierung und die Tabellen-Layouts. Es nutzt aber NUR die generischen
Module pptx_helpers und pptx_charts — kein direkter Streamlit-Zugriff.

Architektur:
    pptx_helpers (Shape/Text/Table/Slide-Manipulation)
    pptx_charts  (Chart-XML mit Bug-Workaround)
        ↑
    pptx_slides  (DIESE Datei — Domain-Logik)
        ↑
    pptx_export  (Orchestrierung der Broschüre)
"""

import pandas as pd
from typing import Optional

from pptx.util import Pt

# Generische PPTX-Helpers (Shape-Lookup, Text, Tabellen)
try:
    from modules.pptx_helpers import (
        find_shape_by_name, replace_text_in_shape,
        set_cell_text, set_cell_text_preserve_format,
        clear_table, safe_float,
    )
except ImportError:
    from pptx_helpers import (
        find_shape_by_name, replace_text_in_shape,
        set_cell_text, set_cell_text_preserve_format,
        clear_table, safe_float,
    )

# Chart-Manipulation (XML-basiert, mit Bug-Workaround)
try:
    from modules.pptx_charts import (
        replace_chart_data, replace_chart_data_safe,
    )
except ImportError:
    from pptx_charts import (
        replace_chart_data, replace_chart_data_safe,
    )

# PNG-Ring-Charts (matplotlib) — Drop-In-Ersatz für native Donuts
# wo Labels garantiert außen platziert werden müssen (Slides 7+9)
try:
    from modules.png_charts import replace_donut_chart, FFPB_COLORS
except ImportError:
    from png_charts import replace_donut_chart, FFPB_COLORS

# Format-Helpers
try:
    from modules.formats import fmt_pct, fmt_ratio, fmt_date_de, PCT_FORMAT_CODE
except ImportError:
    from formats import fmt_pct, fmt_ratio, fmt_date_de, PCT_FORMAT_CODE


# ═══════════════════════════════════════════════════════════════════════════
# KONSTANTEN
# ═══════════════════════════════════════════════════════════════════════════

# ─── Strategienamen-Bereinigung ─────────────────────────────────────────────
STRATEGY_PREFIXES = ["cVV", "Muster", "Stiftung"]
"""Diese Präfixe werden in clean_strategy_name() vom Strategienamen entfernt."""

STRATEGIEENTWURF_TITLE = "Strategieentwurf im Rahmen einer Vermögensverwaltung"
"""Compliance-Anforderung Juni 2026: Slide 7 trägt diesen festen Titel
(statt 'Anlagevorschlag – Konservativ' o.ä.)."""


# ─── Shape-Namen in der Vorlage ─────────────────────────────────────────────
SHAPE_CHART_ALLOCATION = "C_Kennzahlen"    # Ring-Diagramm (Slides 7, 8)
SHAPE_TABLE = "T_Kennzahlen"               # Positionen-Tabelle (Slides 7, 8)
SHAPE_CHART_LEFT = "C_Kennzahlen1"         # Linkes Ring-Diagramm (Slides 9, 10)
SHAPE_CHART_RIGHT = "C_Kennzahlen2"        # Rechtes Ring-Diagramm (Slide 9)
SHAPE_TITLE = "Titel"
SHAPE_TITLE_ALT = "Titel 2"


# ─── Asset-Gruppen (Reihenfolge in Tabelle + Ring) ──────────────────────────
GROUP_AKTIEN = "AKTIEN"
GROUP_RENTEN = "RENTEN"
GROUP_EDELMETALLE = "EDELMETALLE"
GROUP_LIQUIDITAET = "LIQUIDITÄT"
GROUP_SONSTIGE = "SONSTIGE"

GROUP_ORDER = [GROUP_AKTIEN, GROUP_RENTEN, GROUP_EDELMETALLE, GROUP_LIQUIDITAET, GROUP_SONSTIGE]
"""Standard-Reihenfolge der Asset-Gruppen für Tabellen und Allokations-Ring."""


# ─── Tabellen-Spalten-Indizes (Anlagevorschlag-Tabelle, Slide 7) ────────────
# Die Tabelle hat 11 Spalten: 6 Daten-Spalten + 5 Spacer dazwischen
COL_WERTPAPIER = 0
COL_KUPON = 2
COL_FAELLIGKEIT = 4
COL_WKN = 6
COL_ANTEIL = 8
COL_RATING = 10

COL_SPACERS = [1, 3, 5, 7, 9]
"""Spalten-Indizes der Spacer-Spalten (immer leer)."""


# ─── Positionen-Verteilung auf Slides ───────────────────────────────────────
SLIDE_7_DATA_ROWS = 34
"""Slide 7: 36 Zeilen - 1 Header - 1 Summen-Zeile = 34 Daten-Zeilen."""

SLIDE_8_DATA_ROWS = 12
"""Slide 8: 14 Zeilen - 1 Header - 1 Summen-Zeile = 12 Daten-Zeilen.
Aktuell nicht mehr benötigt (Slide 8 ist Performance-Folie seit Juni 2026)."""


# ─── Ring-Chart Konsolidierung (Slide 9: Regionen + Branchen) ───────────────
SMALL_SEGMENT_THRESHOLD = 0.03
"""Kategorien unter 3% werden zu 'Sonstige' zusammengefasst."""

MAX_SEGMENTS_IN_CHART = 7
"""Maximal so viele Kategorien im Ring (alle weiteren → 'Sonstige').
Liquidität wird ggf. NACH dieser Konsolidierung angehängt."""


# ═══════════════════════════════════════════════════════════════════════════
# DOMAIN-HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def clean_strategy_name(name: str) -> str:
    """Bereinigt einen Strategienamen für die Anzeige in der Broschüre.

    - Entfernt die in STRATEGY_PREFIXES definierten Präfixe (z.B. 'cVV',
      'Muster', 'Stiftung') sowohl am Anfang als auch am Ende.
    - Ersetzt Underscores durch Leerzeichen (Datenquellen-Konvention: 
      `ETF_Wachstum` → `ETF Wachstum`).
    - Erster Buchstabe wird großgeschrieben.

    Examples:
        >>> clean_strategy_name("cVV Konservativ")
        'Konservativ'
        >>> clean_strategy_name("Stiftung Konservativ")
        'Konservativ'
        >>> clean_strategy_name("Muster Konservativ cVV")
        'Konservativ'
        >>> clean_strategy_name("ETF_Wachstum")
        'ETF Wachstum'
    """
    if not name:
        return ""
    # Underscores zu Leerzeichen — Datenquellen-Konvention
    cleaned = str(name).strip().replace("_", " ")
    # Mehrfach iterieren, falls mehrere Präfixe vorhanden sind
    changed = True
    while changed:
        changed = False
        for prefix in STRATEGY_PREFIXES:
            if cleaned.lower().startswith(prefix.lower() + " "):
                cleaned = cleaned[len(prefix) + 1:].strip()
                changed = True
                break
            if cleaned.lower().endswith(" " + prefix.lower()):
                cleaned = cleaned[:-len(prefix) - 1].strip()
                changed = True
                break
    # Ersten Buchstaben großschreiben
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def set_title_with_autoscale(title_shape, text: str):
    """Setzt einen Folien-Titel mit automatischer Schriftgrößen-Anpassung.

    Die Titel-Box ist nur ~0.39" hoch (1 Zeile) und ~10.67" breit.
    Bei langem Strategienamen würde der Text in 2 Zeilen umbrechen.

    Strategie (kombiniert):
    1. Manuelle, aggressive Schwellen (empirisch kalibriert in Juni 2026)
    2. Auto-Fit als zusätzliche Sicherheit (PowerPoint skaliert ggf. nach)

    Schwellen (für Standard-Bold-Schrift, 10.67" Box-Breite):
    - ≤ 66 Zeichen → Layout-Default (~32 pt)
    - 67-72 Zeichen → 26 pt
    - 73-80 Zeichen → 22 pt
    - 81-88 Zeichen → 20 pt
    - 89-96 Zeichen → 18 pt
    - 97-108 Zeichen → 16 pt
    - > 108 Zeichen → 14 pt
    """
    replace_text_in_shape(title_shape, text)

    char_count = len(text)
    if char_count <= 66:
        font_size_pt = None  # Layout-Default beibehalten
    elif char_count <= 72:
        font_size_pt = 26
    elif char_count <= 80:
        font_size_pt = 22
    elif char_count <= 88:
        font_size_pt = 20
    elif char_count <= 96:
        font_size_pt = 18
    elif char_count <= 108:
        font_size_pt = 16
    else:
        font_size_pt = 14

    tf = title_shape.text_frame

    if font_size_pt is not None:
        for para in tf.paragraphs:
            for run in para.runs:
                run.font.size = Pt(font_size_pt)

    # Auto-Fit aktivieren als Sicherheits-Netz
    try:
        from pptx.enum.text import MSO_AUTO_SIZE
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.word_wrap = True
    except Exception:
        pass  # Nicht verfügbar in alten python-pptx-Versionen


def safe_marktrisikowert(value) -> str:
    """Konvertiert die CSV-Spalte 'Marktrisikowert' zu einem Display-String.

    Float-Werte werden als Integer dargestellt (3.0 → '3'), damit in der
    Tabelle keine Nachkommastellen erscheinen. Fallback '-' bei None/NaN.
    """
    if value is None:
        return "-"
    try:
        if pd.isna(value):
            return "-"
    except (TypeError, ValueError):
        pass
    # Versuch: als ganze Zahl darstellen (3.0 → '3')
    try:
        return str(int(float(value)))
    except (ValueError, TypeError):
        s = str(value).strip()
        return s if s else "-"


def classify_gattung(gattung) -> str:
    """Ordnet eine Gattung einer der 5 Hauptgruppen zu.

    Heuristik:
    - "aktie" / "equity" → AKTIEN
    - "rente" / "anleihe" / "bond" → RENTEN
    - "edelmetall" / "gold" / "silber" → EDELMETALLE
    - "liquid" / "cash" → LIQUIDITÄT
    - sonst → SONSTIGE
    """
    if gattung is None:
        return GROUP_SONSTIGE
    try:
        if pd.isna(gattung):
            return GROUP_SONSTIGE
    except (TypeError, ValueError):
        pass
    g = str(gattung).lower()
    if "aktie" in g or "equity" in g:
        return GROUP_AKTIEN
    if "rente" in g or "anleihe" in g or "bond" in g:
        return GROUP_RENTEN
    if "edelmetall" in g or "gold" in g or "silber" in g:
        return GROUP_EDELMETALLE
    if "liquid" in g or "cash" in g:
        return GROUP_LIQUIDITAET
    return GROUP_SONSTIGE


def group_portfolio_positions(df: pd.DataFrame) -> dict:
    """Gruppiert Portfoliopositionen nach GROUP_ORDER.

    Innerhalb jeder Gruppe sind Positionen alphabetisch nach Wertpapier-Name
    sortiert (seit Juni 2026 — vorher Sortierung nach Gewicht).

    Positionen werden ausgefiltert wenn:
    - Kein Wertpapier-Name vorhanden ist
    - Gewicht = 0 oder NaN ist
    - Wertpapier-Name "nan", "NaT", "None" oder leer ist (Müll aus CSV)

    Wenn die Summe aller Position-Gewichte < 1.0 ist, wird die Differenz
    implizit als Liquidität ergänzt.

    Returns:
        {
            "AKTIEN": [{"wertpapier": ..., "wkn": ..., "gewicht": 0.02, ...}, ...],
            "RENTEN": [...],
            ...
        }
        Leere Gruppen werden weggelassen.
    """
    groups = {g: [] for g in GROUP_ORDER}

    # Junk-Strings die wir als "leer" behandeln
    JUNK_STRINGS = {"", "nan", "NaN", "NaT", "None", "null"}

    for _, row in df.iterrows():
        wertpapier = str(row.get("Wertpapier", "")).strip()
        gewicht = safe_float(row.get("Gewicht", 0.0), 0.0)

        # Müll-Zeilen rausfiltern
        if wertpapier in JUNK_STRINGS:
            continue
        if gewicht <= 0.0001:
            continue

        gruppe = classify_gattung(row.get("Gattung"))

        # WKN auch auf Müll checken
        wkn = str(row.get("WKN", "")).strip()
        if wkn in JUNK_STRINGS:
            wkn = ""

        pos = {
            "wertpapier": wertpapier,
            "wkn": wkn,
            "gewicht": gewicht,
            "kupon": row.get("Kupon"),
            "faelligkeit": row.get("Fälligkeit_parsed") if "Fälligkeit_parsed" in row.index else None,
            "rating": safe_marktrisikowert(row.get("Marktrisikowert")),
        }
        groups[gruppe].append(pos)

    # Innerhalb jeder Gruppe alphabetisch sortieren
    for g in groups:
        groups[g] = sorted(groups[g], key=lambda p: str(p["wertpapier"]).lower())

    # Liquidität aus Differenz berechnen (falls nicht explizit in Daten)
    if "Gewicht" in df.columns:
        total_weight = safe_float(df["Gewicht"].sum(skipna=True), 0.0)
    else:
        total_weight = 0.0
    liq_from_positions = sum(safe_float(p["gewicht"], 0.0) for p in groups[GROUP_LIQUIDITAET])
    implicit_liq = max(0.0, 1.0 - total_weight)
    if implicit_liq > 0.0001 and liq_from_positions < 0.0001:
        groups[GROUP_LIQUIDITAET].append({
            "wertpapier": "",
            "wkn": "",
            "gewicht": implicit_liq,
            "kupon": None,
            "faelligkeit": None,
            "rating": "",
        })

    # Leere Gruppen entfernen
    return {g: ps for g, ps in groups.items() if ps}


def distribute_positions_to_slides(groups: dict) -> list:
    """Verteilt gruppierte Positionen auf die Tabellen-Slides.

    Seit Juni 2026 (Performance-Folie als neue Slide 8):
    - Alle Positionen kommen auf Slide 7
    - Slide 8 ist jetzt die Performance-Folie (kein Überlauf von Anlagevorschlag mehr)
    - Bei mehr als SLIDE_7_DATA_ROWS Positionen werden Überschüssige im
      fill_table_with_positions automatisch abgeschnitten (Edge-Case)

    Reihenfolge der Zeilen:
    - Asset-Gruppen nach Gewicht absteigend (AKTIEN, RENTEN, EDELMETALLE, ...)
    - LIQUIDITÄT IMMER am Ende als eigene Zeile

    Returns: Liste mit 2 Einträgen:
        [
            {"rows": [...alle Positionen...], "is_last_slide": True},
            {"rows": [], "is_last_slide": False},
        ]
    """
    non_liq = [(n, ps) for n, ps in groups.items() if n != GROUP_LIQUIDITAET]
    non_liq.sort(
        key=lambda kv: sum(safe_float(p["gewicht"], 0.0) for p in kv[1]),
        reverse=True,
    )
    liq_positions = groups.get(GROUP_LIQUIDITAET, [])
    has_liq = bool(liq_positions) and sum(
        safe_float(p["gewicht"], 0.0) for p in liq_positions
    ) > 0.0001

    if not non_liq and not has_liq:
        return [
            {"rows": [], "is_last_slide": True},
            {"rows": [], "is_last_slide": False},
        ]

    all_rows = []
    for group_name, positions in non_liq:
        all_rows.append({"type": "group_header", "data": {"name": group_name}})
        for pos in positions:
            all_rows.append({"type": "position", "data": pos})

    if has_liq:
        total_liq = sum(safe_float(p["gewicht"], 0.0) for p in liq_positions)
        all_rows.append({
            "type": "liquidity",
            "data": {"name": GROUP_LIQUIDITAET, "liq_value": total_liq},
        })

    return [
        {"rows": all_rows, "is_last_slide": True},
        {"rows": [], "is_last_slide": False},
    ]


def remove_empty_table_rows(table):
    """Entfernt leere Daten-Zeilen aus der Anlagevorschlag-Tabelle.

    Eine Zeile gilt als 'leer' wenn alle relevanten Daten-Spalten leer sind
    (WERTPAPIER, KUPON, FÄLLIGKEIT, WKN, ANTEIL, RATING).
    Header (Zeile 0) bleibt immer erhalten.

    WICHTIG: Anschließend muss fit_shape_to_table aufgerufen werden, damit
    die Shape-Höhe an die jetzt geringere Zeilenanzahl angepasst wird
    (sonst stretcht LibreOffice die verbleibenden Zeilen).
    """
    n_rows = len(table.rows)
    if n_rows <= 1:
        return

    indices_to_remove = []
    for i in range(1, n_rows):  # Header (Zeile 0) immer behalten
        row = table.rows[i]
        is_empty = True
        for col_idx in [COL_WERTPAPIER, COL_KUPON, COL_FAELLIGKEIT, COL_WKN, COL_ANTEIL, COL_RATING]:
            text = row.cells[col_idx].text_frame.text.strip()
            # NBSP wird auch als leer betrachtet
            if text and text != "\u00a0":
                is_empty = False
                break
        if is_empty:
            indices_to_remove.append(i)

    if not indices_to_remove:
        return

    # Aus dem XML entfernen — rückwärts, damit Indizes vorderer Zeilen stabil bleiben
    from pptx.oxml.ns import qn
    tbl_elem = table._tbl
    tr_elements = tbl_elem.findall(qn('a:tr'))

    for idx in sorted(indices_to_remove, reverse=True):
        tr_to_remove = tr_elements[idx]
        tbl_elem.remove(tr_to_remove)


def fit_shape_to_table(table_shape, max_row_scale: float = 3.0):
    """Passt die Höhe der Tabellen-Shape an die Zeilenanzahl an.

    Bei vielen Zeilen (Tabelle füllt den verfügbaren Platz von Natur aus):
    Shape-Höhe exakt auf Summe der Zeilenhöhen (+ kleiner Puffer).

    Bei wenigen Zeilen (Tabelle wäre sonst klein und oben angeklebt):
    Zeilenhöhen proportional vergrößern, sodass die Tabelle den verfügbaren
    Platz besser nutzt. Maximum: `max_row_scale` × Originalhöhe pro Zeile.

    Hintergrund: Sonst stretcht LibreOffice/PowerPoint die Zeilen automatisch
    wenn Shape-Höhe größer als Zeilensumme ist — wir wollen aber kontrollieren
    wie das passiert, nicht den Renderer das tun lassen.

    Args:
        table_shape: Die Tabellen-Shape (mit .table-Property)
        max_row_scale: Maximaler Skalierungsfaktor pro Zeile (Default 3.0).
            Bei 0.142" Original = max 0.426" je Zeile. Verhindert übergroße
            Zeilen bei sehr wenigen Positionen.
    """
    table = table_shape.table

    # Verfügbarer Raum auf dem Slide (bis Footer bei 6.60")
    MAX_TABLE_BOTTOM_INCH = 6.60
    SHAPE_PADDING_EMU = 50000  # ~0.05" Puffer für Rahmen
    shape_top_inch = table_shape.top / 914400
    max_available_h_emu = int((MAX_TABLE_BOTTOM_INCH - shape_top_inch) * 914400)

    # Aktuelle Summe der Zeilenhöhen
    total_row_h = sum(row.height for row in table.rows)

    # Wenn Tabelle deutlich kleiner als verfügbar → Zeilen proportional vergrößern
    # Schwellwert: nur skalieren wenn aktuell <70% Auslastung der verfügbaren Höhe
    if total_row_h < max_available_h_emu * 0.7 and total_row_h > 0:
        # Ziel-Höhe: max verfügbar (minus Puffer), aber max max_row_scale × aktuell
        target_h = min(
            max_available_h_emu - SHAPE_PADDING_EMU,
            int(total_row_h * max_row_scale)
        )
        scale = target_h / total_row_h
        # Jede Zeilenhöhe proportional skalieren
        for row in table.rows:
            row.height = int(row.height * scale)
        # Neue Summe berechnen
        total_row_h = sum(row.height for row in table.rows)

    # Shape-Höhe auf die (ggf. skalierte) Summe der Zeilenhöhen setzen
    table_shape.height = total_row_h + SHAPE_PADDING_EMU


def adjust_table_shape_height(prs, table_shape, n_data_rows: int, needs_summary: bool):
    """Passt die Höhe der Tabellen-Shape an die tatsächlich benötigte Zeilenanzahl an.

    Kann die Shape auch vergrößern (nach unten), aber nur bis max. 6.60" Bottom
    (vor Footer bei 6.76").

    Args:
        prs: Presentation
        table_shape: Die Tabellen-Shape
        n_data_rows: Anzahl Daten-Zeilen die wir befüllen (inkl. Gruppen-Header)
        needs_summary: True wenn Summen-Zeile benötigt wird
    """
    ORIGINAL_HEADER_H = 0.236
    ORIGINAL_DATA_ROW_H = 0.142
    ORIGINAL_SUMMARY_H = 0.142
    MAX_TABLE_BOTTOM = 6.60  # inches

    n_buffer_rows = 2 if needs_summary else 0

    needed_h = ORIGINAL_HEADER_H + (n_data_rows * ORIGINAL_DATA_ROW_H) + (n_buffer_rows * ORIGINAL_DATA_ROW_H)
    if needs_summary:
        needed_h += ORIGINAL_SUMMARY_H

    shape_top_inch = table_shape.top / 914400
    shape_current_h_inch = table_shape.height / 914400
    max_available_h = MAX_TABLE_BOTTOM - shape_top_inch

    new_h_inch = min(needed_h, max_available_h)

    # Nur ändern wenn Änderung signifikant (>0.05" Differenz)
    if abs(new_h_inch - shape_current_h_inch) > 0.05:
        table_shape.height = int(new_h_inch * 914400)


def consolidate_small_segments(agg_series: pd.Series,
                                threshold: float = SMALL_SEGMENT_THRESHOLD,
                                max_segments: int = MAX_SEGMENTS_IN_CHART) -> pd.Series:
    """Fasst kleine Kategorien zu 'Sonstige' zusammen.

    Regel:
    - Alle Kategorien unter threshold werden zu 'Sonstige' gruppiert
    - Wenn nach Konsolidierung noch mehr als max_segments Kategorien da sind,
      werden die kleinsten zusätzlich in Sonstige verschoben bis max_segments
      erreicht ist

    Args:
        agg_series: Pandas Series (Index = Kategorie-Name, Werte = Gewicht)
        threshold: Schwellwert für 'kleine' Kategorie
        max_segments: Maximale Anzahl Segmente im Chart

    Returns:
        Konsolidierte Series, absteigend sortiert.
    """
    agg = agg_series.sort_values(ascending=False)

    big = agg[agg >= threshold]
    small = agg[agg < threshold]

    # Maximale Anzahl Segmente beachten
    if len(big) > max_segments - 1:  # -1 weil Platz für 'Sonstige' nötig
        keep = big.head(max_segments - 1)
        move_to_small = big.tail(len(big) - (max_segments - 1))
        big = keep
        small = pd.concat([small, move_to_small])

    # Sonstige zusammenfassen
    if len(small) > 0:
        sonstige_sum = small.sum()
        if sonstige_sum > 0.0001:
            existing = float(big["Sonstige"]) if "Sonstige" in big.index else 0.0
            big["Sonstige"] = existing + sonstige_sum
            big = big.sort_values(ascending=False)

    return big


def build_ring_series(df: pd.DataFrame, dim_col: str) -> pd.Series:
    """Baut die Werte-Serie für einen Ring auf Slide 9 (Regionen oder Branchen).

    - Aggregiert 'Gewicht' nach `dim_col` (z.B. 'Region' oder 'Segment')
    - Positionen ohne Eintrag in `dim_col` werden ignoriert (z.B. Liquidität
      hat typischerweise keine Region/Branche zugeordnet)
    - Konsolidiert kleine Kategorien zu 'Sonstige'
    - Hängt anschließend die Summe der NICHT klassifizierten Gewichte als
      Kategorie 'Liquidität' an — damit der Ring auf 100% summiert.

    Liquidität wird nach der Konsolidierung angehängt, damit sie NICHT in
    'Sonstige' einsortiert wird, auch wenn sie unter dem 3%-Threshold liegt.
    """
    if dim_col not in df.columns or "Gewicht" not in df.columns:
        return pd.Series(dtype=float)

    # Normalisierung: leere/NaN-Strings als Platzhalter
    col = df[dim_col].astype(str).replace(["nan", "NaT", "None"], "")
    has_value = col.str.strip() != ""
    classified = df[has_value]
    unclassified_weight = float(df.loc[~has_value, "Gewicht"].sum())

    if classified.empty:
        return pd.Series(dtype=float)

    agg = classified.groupby(col[has_value])["Gewicht"].sum()
    agg = agg[agg > 0.0001]
    if agg.empty:
        return pd.Series(dtype=float)

    agg = consolidate_small_segments(agg)

    # Liquidität / nicht-klassifiziertes Gewicht als eigenes Segment am Ende
    if unclassified_weight > 0.0001:
        agg["Liquidität"] = unclassified_weight

    return agg


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE-BEFÜLLUNG (Hauptfunktionen pro Folie)
# ═══════════════════════════════════════════════════════════════════════════

def fill_table_with_positions(table, slide_data: dict, total_weight: float = 1.0,
                              shape_height: int = 0):
    """Befüllt die Anlagevorschlag-Tabelle (Slide 7) mit Positionen.

    Die Tabellen-Struktur der Vorlage bleibt UNVERÄNDERT (keine Zeilen entfernt,
    keine Höhen geändert). Nicht benötigte Zeilen bleiben leer sichtbar.

    Args:
        table: Die Tabelle (shape.table)
        slide_data: {"rows": [...], "is_last_slide": bool}
        total_weight: Summe aller Gewichte (für Summen-Zeile, default 100%)
        shape_height: Höhe der Tabellen-Shape in EMU (aus Kompat-Gründen in der
                      Signatur belassen, wird nicht mehr verwendet)
    """
    n_rows_initial = len(table.rows)
    rows = slide_data["rows"]
    is_last = slide_data["is_last_slide"]

    # Summen-Zeile ist immer die letzte Zeile in der Vorlage
    summary_row_idx = n_rows_initial - 1
    max_data_rows = n_rows_initial - 2

    # Erst alle Datenzeilen leeren (nur Spalten 0, 2, 4, 6, 8, 10 - Spacer bleiben)
    for row_idx in range(1, n_rows_initial):
        row = table.rows[row_idx]
        for col_idx in [COL_WERTPAPIER, COL_KUPON, COL_FAELLIGKEIT, COL_WKN, COL_ANTEIL, COL_RATING]:
            set_cell_text(row.cells[col_idx], "")

    # Zeilen befüllen
    for i, row_def in enumerate(rows):
        if i >= max_data_rows:
            break  # Kein Platz mehr

        target_row_idx = i + 1  # +1 weil Zeile 0 der Tabellen-Header ist
        row = table.rows[target_row_idx]

        if row_def["type"] in ("group_header", "liquidity"):
            # Gruppen-Header: Name in Spalte 0, alle anderen leer, fett
            name = row_def["data"]["name"]
            set_cell_text(row.cells[COL_WERTPAPIER], name, is_bold=True)
            # Bei RENTEN: "KUPON" und "FÄLLIGKEIT" als Sub-Header in Spalten 2 und 4
            if name == GROUP_RENTEN:
                set_cell_text(row.cells[COL_KUPON], "KUPON", is_bold=True)
                set_cell_text(row.cells[COL_FAELLIGKEIT], "FÄLLIGKEIT", is_bold=True)
            # Bei LIQUIDITÄT: Wert direkt in der Header-Zeile
            if name == GROUP_LIQUIDITAET and "liq_value" in row_def["data"]:
                set_cell_text(row.cells[COL_ANTEIL], fmt_pct(row_def["data"]["liq_value"]), is_bold=True)

        elif row_def["type"] == "position":
            data = row_def["data"]
            # Alle Felder einer Position: explizit NICHT BOLD
            set_cell_text(row.cells[COL_WERTPAPIER], data["wertpapier"], is_bold=False)
            set_cell_text(row.cells[COL_WKN], data["wkn"], is_bold=False)
            set_cell_text(row.cells[COL_ANTEIL], fmt_pct(data["gewicht"]), is_bold=False)
            set_cell_text(row.cells[COL_RATING], data.get("rating", "-"), is_bold=False)
            # Kupon (nur wenn vorhanden)
            if data.get("kupon") is not None and not pd.isna(data["kupon"]) and data["kupon"] != 0:
                set_cell_text(row.cells[COL_KUPON], fmt_pct(data["kupon"]), is_bold=False)
            else:
                set_cell_text(row.cells[COL_KUPON], "", is_bold=False)
            # Fälligkeit (nur wenn vorhanden)
            if data.get("faelligkeit") is not None and not pd.isna(data["faelligkeit"]):
                set_cell_text(row.cells[COL_FAELLIGKEIT], fmt_date_de(data["faelligkeit"]), is_bold=False)
            else:
                set_cell_text(row.cells[COL_FAELLIGKEIT], "", is_bold=False)

    # Summen-Zeile: nur auf letzter Slide
    summary_row = table.rows[summary_row_idx]
    for col_idx in [COL_WERTPAPIER, COL_KUPON, COL_FAELLIGKEIT, COL_WKN, COL_ANTEIL, COL_RATING]:
        set_cell_text(summary_row.cells[col_idx], "")

    if is_last:
        set_cell_text(summary_row.cells[COL_ANTEIL], fmt_pct(total_weight))

    # WICHTIG: Tabellen-Struktur der Vorlage bleibt UNVERÄNDERT.
    # Frühere Versuche, leere Zeilen zu entfernen, haben LibreOffice
    # zum Vergrößern der Zeilen veranlasst → Überlauf am Slide-Rand.


def fill_anlagevorschlag_slides(prs, slide_7_idx: int,
                                 df: pd.DataFrame, strategy_name: str,
                                 eval_date=None):
    """Befüllt Slide 7 (Anlagevorschlag/Strategieentwurf) mit Portfolio-Daten.

    Seit Juni 2026 (Performance-Folie als Slide 8): Es gibt nur noch EINE
    Anlagevorschlag-Slide. Alle Positionen kommen auf Slide 7, dynamisch
    geschrumpft durch remove_empty_table_rows + fit_shape_to_table.

    Args:
        prs: Presentation
        slide_7_idx: 0-indexed Index der Anlagevorschlag-Slide
        df: DataFrame mit Positionen (Wertpapier, WKN, Gewicht, Gattung, Kupon,
            Fälligkeit_parsed, Marktrisikowert)
        strategy_name: Name der Strategie für den Titel (schon bereinigt)
        eval_date: Auswertungsdatum (für Source-Annotation im Ring-Chart).
            Optional — falls None, wird kein Datum gezeigt.
    """
    # 1. Daten vorbereiten
    groups = group_portfolio_positions(df)
    slide_distribution = distribute_positions_to_slides(groups)

    # 2. Allokations-Daten für Ring-Chart (nach Gruppen)
    alloc_labels = []
    alloc_values = []
    for g in GROUP_ORDER:
        if g in groups:
            total = sum(safe_float(p["gewicht"], 0.0) for p in groups[g])
            if total > 0.0001:
                alloc_labels.append(g)
                alloc_values.append(float(total))

    # Gesamt-Gewicht (für Summen-Zeile)
    total_weight = sum(alloc_values)

    # 3. Slide 7 befüllen
    slide_7 = prs.slides[slide_7_idx]
    # Titel: Strategieentwurf-Hinweis (Email-Anforderung Juni 2026, Compliance)
    title = find_shape_by_name(slide_7, SHAPE_TITLE_ALT) or find_shape_by_name(slide_7, SHAPE_TITLE)
    if title:
        set_title_with_autoscale(title, f"{STRATEGIEENTWURF_TITLE} - {strategy_name}")
    # Ring-Chart: matplotlib-PNG mit Labels außen (statt nativer Donut,
    # weil PowerPoint die Labels bei großen Segmenten innen platziert)
    chart = find_shape_by_name(slide_7, SHAPE_CHART_ALLOCATION)
    if chart:
        total = sum(alloc_values)
        if total > 0:
            percent_labels = [
                f"{v/total*100:.2f}%".replace(".", ",")
                for v in alloc_values
            ]
            source_text = (
                f"Quelle: Eigene Berechnung Stand: {fmt_date_de(eval_date)}"
                if eval_date is not None
                else "Quelle: Eigene Berechnung"
            )
            replace_donut_chart(
                slide_7, SHAPE_CHART_ALLOCATION,
                values=list(alloc_values),
                item_labels=list(alloc_labels),
                percent_labels=percent_labels,
                colors=FFPB_COLORS[:len(alloc_values)],
                banner_text="AKTUELLE STRUKTUR",
                source_text=source_text,
            )
    # Tabelle befüllen
    table_shape = find_shape_by_name(slide_7, SHAPE_TABLE)
    if table_shape:
        fill_table_with_positions(table_shape.table, slide_distribution[0], total_weight,
                                  shape_height=table_shape.height)
        # Leere Zeilen entfernen
        remove_empty_table_rows(table_shape.table)
        # Shape-Höhe an verbleibende Zeilen anpassen
        fit_shape_to_table(table_shape)


def fill_kennzahlen_table(table, kz: dict):
    """Befüllt die KENNZAHLEN-Tabelle auf der Performance-Folie.

    Tabellen-Layout (7 rows × 5 cols, mit Spacer-Spalten):
      Row 0: Header   (KENNZAHLEN | _ | REFERENZ | _ | BENCHMARK)
      Row 1: leer/Spacer
      Row 2: Performance p.a.
      Row 3: Volatilität
      Row 4: Sharpe Ratio
      Row 5: Max Drawdown
      Row 6: leer/Spacer

    Wert-Spalten: 2 (REFERENZ), 4 (BENCHMARK)
    """
    metric_rows = [
        ("performance_pa_ref",  "performance_pa_bench",   2, True),   # row 2, Prozent
        ("volatilitaet_ref",    "volatilitaet_bench",     3, True),   # row 3, Prozent
        ("sharpe_ref",          "sharpe_bench",           4, False),  # row 4, Dezimal
        ("max_drawdown_ref",    "max_drawdown_bench",     5, True),   # row 5, Prozent
    ]
    for ref_key, bench_key, row_idx, is_pct in metric_rows:
        if row_idx >= len(table.rows):
            continue
        row = table.rows[row_idx]
        ref_val = kz.get(ref_key)
        bench_val = kz.get(bench_key)
        if is_pct:
            ref_str = fmt_pct(ref_val)
            bench_str = fmt_pct(bench_val)
        else:
            ref_str = fmt_ratio(ref_val)
            bench_str = fmt_ratio(bench_val)
        # Spalte 2 = REFERENZ, Spalte 4 = BENCHMARK
        set_cell_text_preserve_format(row.cells[2], ref_str)
        set_cell_text_preserve_format(row.cells[4], bench_str)


def fill_performance_slide(prs, slide_idx: int, strategy_name: str,
                            performance_data: Optional[dict] = None):
    """Befüllt die Performance-Slide (Slide 8: Anlagestrategie Wertentwicklung).

    Args:
        prs: Presentation
        slide_idx: 0-indexed Index der Performance-Slide
        strategy_name: Name der Strategie für den Titel
        performance_data: Dict mit Performance-Daten (siehe
            modules.analytics.compute_performance_data). Wenn None: nur Titel
            wird gesetzt, Charts/Tabelle bleiben mit Vorlagen-Platzhaltern.
    """
    slide = prs.slides[slide_idx]

    # Titel anpassen: "{Strategy} | Wertentwicklung (mit Benchmark)"
    title = find_shape_by_name(slide, "Titel")
    if title and title.has_text_frame:
        new_title = f"{strategy_name} | Wertentwicklung (mit Benchmark)"
        replace_text_in_shape(title, new_title)

    if performance_data is None:
        return  # Phase 1: nur Titel setzen

    # ── KENNZAHLEN-Tabelle befüllen ──
    kz = performance_data.get("kennzahlen", {})
    tab = find_shape_by_name(slide, "Tabelle")
    if tab and tab.has_table:
        fill_kennzahlen_table(tab.table, kz)

    # ── PERFORMANCE P.A. Chart (Säulen) ──
    pa = performance_data.get("performance_pa", {})
    chart_links = find_shape_by_name(slide, "Diagramm links")
    if chart_links and chart_links.has_chart and pa.get("jahre"):
        replace_chart_data_safe(
            chart_links,
            categories=[str(y) for y in pa["jahre"]],
            series_data=[
                ("Referenzportfolio", pa.get("referenz", [])),
                ("Benchmark", pa.get("benchmark", [])),
            ],
            data_label_format=PCT_FORMAT_CODE,
        )

    # ── WERTENTWICKLUNG Chart (Linien) ──
    we = performance_data.get("wertentwicklung", {})
    chart_rechts = find_shape_by_name(slide, "Diagramm rechts")
    if chart_rechts and chart_rechts.has_chart and we.get("dates"):
        replace_chart_data_safe(
            chart_rechts,
            categories=we["dates"],
            series_data=[
                ("Referenzportfolio", we.get("referenz", [])),
                ("Benchmark", we.get("benchmark", [])),
            ],
            data_label_format=None,  # Linien-Chart hat keine Daten-Labels
        )


def fill_zusammenstellung_slide(prs, slide_idx: int, df: pd.DataFrame,
                                 strategy_name: str, eval_date=None):
    """Befüllt Slide 9 mit 2 Ringen: Regionen (links) + Branchen/Segment (rechts).

    Kleine Kategorien (<3%) werden zu "Sonstige" zusammengefasst, maximal 8
    Segmente angezeigt. Nicht-klassifizierte Positionen (typischerweise
    Liquidität) erscheinen als eigenes Segment "Liquidität", damit der Ring
    auf 100% summiert.

    Args:
        prs: Presentation
        slide_idx: 0-indexed Slide-Position
        df: Portfolio-DataFrame
        strategy_name: bereinigter Strategiename
        eval_date: Auswertungsdatum für Source-Annotation. Optional.
    """
    slide = prs.slides[slide_idx]

    # Titel
    title = find_shape_by_name(slide, SHAPE_TITLE) or find_shape_by_name(slide, SHAPE_TITLE_ALT)
    if title:
        replace_text_in_shape(title, f"Aktuelle Portfoliozusammenstellung – {strategy_name}")

    # Defensive Vorbereitung: Gewicht muss sauberer Float sein
    df_clean = df.copy()
    if "Gewicht" in df_clean.columns:
        df_clean["Gewicht"] = pd.to_numeric(df_clean["Gewicht"], errors="coerce").fillna(0.0).astype(float)

    # Source-Text einmal vorberechnen (gleich für beide Ringe)
    source_text = (
        f"Quelle: Eigene Berechnung Stand: {fmt_date_de(eval_date)}"
        if eval_date is not None
        else "Quelle: Eigene Berechnung"
    )

    # Regionen (links) — matplotlib-PNG-Ring mit Labels außen
    region_agg = build_ring_series(df_clean, "Region")
    if not region_agg.empty and find_shape_by_name(slide, SHAPE_CHART_LEFT):
        values = [float(v) for v in region_agg.values]
        total = sum(values)
        if total > 0:
            percent_labels = [
                f"{v/total*100:.2f}%".replace(".", ",") for v in values
            ]
            replace_donut_chart(
                slide, SHAPE_CHART_LEFT,
                values=values,
                item_labels=region_agg.index.tolist(),
                percent_labels=percent_labels,
                colors=FFPB_COLORS[:len(values)],
                banner_text="REGIONEN",
                source_text=source_text,
            )

    # Segmente/Branchen (rechts) — matplotlib-PNG-Ring mit Labels außen
    segment_agg = build_ring_series(df_clean, "Segment")
    if not segment_agg.empty and find_shape_by_name(slide, SHAPE_CHART_RIGHT):
        values = [float(v) for v in segment_agg.values]
        total = sum(values)
        if total > 0:
            percent_labels = [
                f"{v/total*100:.2f}%".replace(".", ",") for v in values
            ]
            replace_donut_chart(
                slide, SHAPE_CHART_RIGHT,
                values=values,
                item_labels=segment_agg.index.tolist(),
                percent_labels=percent_labels,
                colors=FFPB_COLORS[:len(values)],
                banner_text="Branchen",
                source_text=source_text,
            )
