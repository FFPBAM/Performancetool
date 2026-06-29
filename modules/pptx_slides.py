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

    Entfernt die in STRATEGY_PREFIXES definierten Präfixe (z.B. 'cVV',
    'Muster', 'Stiftung') sowohl am Anfang als auch am Ende. Erste
    Buchstabe wird groß geschrieben.

    Examples:
        >>> clean_strategy_name("cVV Konservativ")
        'Konservativ'
        >>> clean_strategy_name("Stiftung Konservativ")
        'Konservativ'
        >>> clean_strategy_name("Muster Konservativ cVV")
        'Konservativ'
    """
    if not name:
        return ""
    cleaned = str(name).strip()
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


def fit_shape_to_table(table_shape):
    """Passt die Höhe der Tabellen-Shape an die Summe der Zeilenhöhen an.

    Wichtig weil LibreOffice/PowerPoint die Zeilen automatisch vergrößern,
    wenn die Summe aller Zeilenhöhen kleiner ist als die Shape-Höhe. Wenn
    wir die Shape auf die korrekte Größe setzen, bleiben die Zeilen in
    ihrer ursprünglichen Höhe (0.142") und die Tabelle ragt nicht über
    den Footer.
    """
    table = table_shape.table
    total_row_h = sum(row.height for row in table.rows)
    # Shape-Höhe auf diese Summe setzen (+ kleiner Puffer für Rahmen, ~0.02")
    table_shape.height = total_row_h + 50000


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
