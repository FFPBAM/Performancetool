# modules/pptx_export.py
"""
PowerPoint-Export für Performance und Portfolioanalyse.

Nutzt eine Corporate-Vorlage (Vorlage/Vorlage_FFPB.pptx) und befüllt sie
mit den Daten aus dem Streamlit-Tool.

Öffentliche API:
- generate_portfolioanalyse_pptx(...) -> bytes
- generate_performance_pptx(...) -> bytes  (später)

Wichtigste Mechanik:
- Die Vorlage enthält benannte Shapes (C_Kennzahlen, T_Kennzahlen, C_Kennzahlen1, C_Kennzahlen2)
- Wir finden diese Shapes per Name und tauschen Inhalte aus
- Für Vergleichsportfolios werden Slides 7-10 dupliziert
"""

import os
import io
import copy
import datetime as dt
from typing import Optional

import pandas as pd
from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.chart.data import CategoryChartData
from lxml import etree

# Format-Helpers + Konstanten (Single Source of Truth — siehe modules/formats.py)
try:
    from modules.formats import fmt_pct, fmt_ratio, fmt_date_de, PCT_FORMAT_CODE
except ImportError:
    # Fallback für lokalen Skript-Aufruf (ohne modules/-Prefix im sys.path)
    from formats import fmt_pct, fmt_ratio, fmt_date_de, PCT_FORMAT_CODE

# Generische PPTX-Helpers (Shape-Lookup, Text, Tabellen, Vorlage, Slide-Manipulation)
try:
    from modules.pptx_helpers import (
        find_shape_by_name, replace_text_in_shape,
        set_cell_text, set_cell_text_preserve_format,
        clear_table, safe_float, load_template,
        duplicate_slide, clone_chart_part, move_slide, remove_slide,
        save_and_reload, update_quelle_datum, update_slide_numbers,
    )
except ImportError:
    from pptx_helpers import (
        find_shape_by_name, replace_text_in_shape,
        set_cell_text, set_cell_text_preserve_format,
        clear_table, safe_float, load_template,
        duplicate_slide, clone_chart_part, move_slide, remove_slide,
        save_and_reload, update_quelle_datum, update_slide_numbers,
    )

# Chart-Manipulation (XML-basierte Datenersetzung + python-pptx Bug-Workaround)
try:
    from modules.pptx_charts import (
        NS_CHART,
        replace_chart_data, update_cache_elements,
        replace_chart_data_safe, restore_data_label_format,
        update_chart_values_inplace,
    )
except ImportError:
    from pptx_charts import (
        NS_CHART,
        replace_chart_data, update_cache_elements,
        replace_chart_data_safe, restore_data_label_format,
        update_chart_values_inplace,
    )

# Slide-Befüllungs-Logik (Domain: Anlagevorschlag, Performance, Portfoliozusammenstellung)
try:
    from modules.pptx_slides import (
        # Konstanten
        STRATEGY_PREFIXES, STRATEGIEENTWURF_TITLE,
        SHAPE_CHART_ALLOCATION, SHAPE_TABLE, SHAPE_CHART_LEFT, SHAPE_CHART_RIGHT,
        SHAPE_TITLE, SHAPE_TITLE_ALT,
        GROUP_AKTIEN, GROUP_RENTEN, GROUP_EDELMETALLE, GROUP_LIQUIDITAET,
        GROUP_SONSTIGE, GROUP_ORDER,
        COL_WERTPAPIER, COL_KUPON, COL_FAELLIGKEIT, COL_WKN, COL_ANTEIL,
        COL_RATING, COL_SPACERS,
        SLIDE_7_DATA_ROWS, SLIDE_8_DATA_ROWS,
        SMALL_SEGMENT_THRESHOLD, MAX_SEGMENTS_IN_CHART,
        # Public API: clean_strategy_name (kein Underscore-Prefix)
        clean_strategy_name,
        # Funktionen (werden über Wrapper unten weiterhin als _xxx exponiert)
        set_title_with_autoscale, safe_marktrisikowert, classify_gattung,
        group_portfolio_positions, distribute_positions_to_slides,
        remove_empty_table_rows, fit_shape_to_table, adjust_table_shape_height,
        consolidate_small_segments, build_ring_series,
        fill_table_with_positions, fill_anlagevorschlag_slides,
        fill_kennzahlen_table, fill_performance_slide,
        fill_zusammenstellung_slide,
    )
except ImportError:
    from pptx_slides import (
        STRATEGY_PREFIXES, STRATEGIEENTWURF_TITLE,
        SHAPE_CHART_ALLOCATION, SHAPE_TABLE, SHAPE_CHART_LEFT, SHAPE_CHART_RIGHT,
        SHAPE_TITLE, SHAPE_TITLE_ALT,
        GROUP_AKTIEN, GROUP_RENTEN, GROUP_EDELMETALLE, GROUP_LIQUIDITAET,
        GROUP_SONSTIGE, GROUP_ORDER,
        COL_WERTPAPIER, COL_KUPON, COL_FAELLIGKEIT, COL_WKN, COL_ANTEIL,
        COL_RATING, COL_SPACERS,
        SLIDE_7_DATA_ROWS, SLIDE_8_DATA_ROWS,
        SMALL_SEGMENT_THRESHOLD, MAX_SEGMENTS_IN_CHART,
        clean_strategy_name,
        set_title_with_autoscale, safe_marktrisikowert, classify_gattung,
        group_portfolio_positions, distribute_positions_to_slides,
        remove_empty_table_rows, fit_shape_to_table, adjust_table_shape_height,
        consolidate_small_segments, build_ring_series,
        fill_table_with_positions, fill_anlagevorschlag_slides,
        fill_kennzahlen_table, fill_performance_slide,
        fill_zusammenstellung_slide,
    )


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
TEMPLATE_PATH = os.path.join("Vorlage", "Vorlage_FFPB.pptx")

# Slide-Positionen in der Vorlage (1-indexed)
SLIDE_ANLAGEVORSCHLAG_1 = 7    # Aktien + Allokations-Ring
SLIDE_ANLAGEVORSCHLAG_2 = 8    # Renten/Edelmetalle/Liquidität
SLIDE_ZUSAMMENSTELLUNG_1 = 9   # Regionen + Branchen (2 Ringe)
SLIDE_ZUSAMMENSTELLUNG_2 = 10  # Währungen (1 Ring)

# Konstanten kommen aus modules/pptx_slides.py (siehe Import-Block oben):
# - STRATEGY_PREFIXES, STRATEGIEENTWURF_TITLE
# - SHAPE_CHART_ALLOCATION, SHAPE_TABLE, SHAPE_CHART_LEFT, SHAPE_CHART_RIGHT, SHAPE_TITLE, SHAPE_TITLE_ALT
# - GROUP_*, GROUP_ORDER
# - COL_*, COL_SPACERS
# - SMALL_SEGMENT_THRESHOLD, MAX_SEGMENTS_IN_CHART
# - SLIDE_7_DATA_ROWS, SLIDE_8_DATA_ROWS

# Foliennummer-Shape-Namen (uneinheitlich in der Vorlage):
# - Die meisten Slides nutzen "Foliennummer"
# - Slides 7, 8, 10 nutzen "Foliennummernplatzhalter 1" (anderer Layout-Master)
# Slides ohne eines dieser Shapes (Cover, Sub-Cover, Impressum) behalten keine Seitenzahl.
SHAPE_FOLIENNUMMER_NAMES = (
    "Foliennummer",
    "Foliennummernplatzhalter 1",
    "Slide Number",
    "Folienzahl",
)


# ---------------------------------------------------------------------------
# Strategienamen-Konvertierung
# ---------------------------------------------------------------------------
# clean_strategy_name kommt aus modules/pptx_slides.py (via Import oben).
# Die Funktion ist Public und wird intern in generate_portfolioanalyse_pptx aufgerufen.


# ---------------------------------------------------------------------------
# Shape-Helpers
# ---------------------------------------------------------------------------
def _find_shape_by_name(slide, name: str):
    """Wrapper für pptx_helpers.find_shape_by_name."""
    return find_shape_by_name(slide, name)


def _replace_text_in_shape(shape, new_text: str):
    """Wrapper für pptx_helpers.replace_text_in_shape."""
    return replace_text_in_shape(shape, new_text)


# ---------------------------------------------------------------------------
# Slide-Duplikation (für Vergleichsportfolio)
# ---------------------------------------------------------------------------
def _duplicate_slide(prs, source_idx: int):
    """Wrapper für pptx_helpers.duplicate_slide."""
    return duplicate_slide(prs, source_idx)


def _clone_chart_part(prs, source_chart_part):
    """Wrapper für pptx_helpers.clone_chart_part."""
    return clone_chart_part(prs, source_chart_part)


# Re wird in _clone_chart_part benutzt
import re


# ---------------------------------------------------------------------------
# Chart-Befüllung — Wrapper für pptx_charts (Backwards-Compat)
# ---------------------------------------------------------------------------
# _NS_CHART als Alias auf NS_CHART aus pptx_charts (Backwards-Compat,
# falls anderer Code im Modul es noch direkt referenziert)
_NS_CHART = NS_CHART


def _replace_chart_data(chart_shape, categories: list, values: list, series_name: str = "Anteil"):
    """Wrapper für pptx_charts.replace_chart_data."""
    return replace_chart_data(chart_shape, categories, values, series_name)


def _update_cache_elements(parent, new_values, is_numeric: bool):
    """Wrapper für pptx_charts.update_cache_elements."""
    return update_cache_elements(parent, new_values, is_numeric)


# ---------------------------------------------------------------------------
# Tabellen-Befüllung
# ---------------------------------------------------------------------------
def _set_cell_text(cell, text: str, is_bold: bool = None):
    """Wrapper für pptx_helpers.set_cell_text."""
    return set_cell_text(cell, text, is_bold)


def _clear_table(table, keep_header_rows: int = 1):
    """Wrapper für pptx_helpers.clear_table."""
    return clear_table(table, keep_header_rows)


# ---------------------------------------------------------------------------
# Template laden
# ---------------------------------------------------------------------------
def _load_template() -> Presentation:
    """Wrapper für pptx_helpers.load_template. Nutzt das modul-lokale TEMPLATE_PATH."""
    return load_template(TEMPLATE_PATH)


# ---------------------------------------------------------------------------
# Formatierungs-Helpers — Wrapper für modules.formats (Backwards-Compat)
# ---------------------------------------------------------------------------
def _fmt_pct(value) -> str:
    """Wrapper für formats.fmt_pct. Behält die alte Signatur für internen Code bei."""
    return fmt_pct(value)


def _fmt_date_de(value) -> str:
    """Wrapper für formats.fmt_date_de."""
    return fmt_date_de(value)


# ---------------------------------------------------------------------------
# Gattungs-Klassifizierung
# ---------------------------------------------------------------------------
# Gruppen-Namen wie sie auf den Slides erscheinen sollen (GROSSBUCHSTABEN)
GROUP_AKTIEN = "AKTIEN"
GROUP_RENTEN = "RENTEN"
GROUP_EDELMETALLE = "EDELMETALLE"
GROUP_LIQUIDITAET = "LIQUIDITÄT"
GROUP_SONSTIGE = "SONSTIGE"

# Reihenfolge der Gruppen auf den Slides (nach Priorität der Vorlage)
GROUP_ORDER = [GROUP_AKTIEN, GROUP_RENTEN, GROUP_EDELMETALLE, GROUP_LIQUIDITAET, GROUP_SONSTIGE]


def _safe_float(value, default: float = 0.0) -> float:
    """Wrapper für pptx_helpers.safe_float."""
    return safe_float(value, default)


def _set_title_with_autoscale(title_shape, text: str):
    """Wrapper für pptx_slides.set_title_with_autoscale."""
    return set_title_with_autoscale(title_shape, text)


def _safe_marktrisikowert(value):
    """Wrapper für pptx_slides.safe_marktrisikowert."""
    return safe_marktrisikowert(value)


def _classify_gattung(gattung):
    """Wrapper für pptx_slides.classify_gattung."""
    return classify_gattung(gattung)


def _group_portfolio_positions(df: pd.DataFrame):
    """Wrapper für pptx_slides.group_portfolio_positions."""
    return group_portfolio_positions(df)


# ---------------------------------------------------------------------------
# Positionen-Verteilung auf Slides
# ---------------------------------------------------------------------------
# Maximal verfügbare Zeilen pro Slide (ohne Header, ohne Summen-Zeile)
# Slide 7: 36 Zeilen - 1 Header - 1 Summen-Zeile = 34. 1 davon ist Gruppen-Header = 33 Positionen max
# Slide 8: 14 Zeilen - 1 Header - 1 Summen-Zeile = 12 Zeilen für Gruppen+Positionen
SLIDE_7_DATA_ROWS = 34   # Zeilen 1-34, Zeile 35 = Summe
SLIDE_8_DATA_ROWS = 12   # Zeilen 1-12, Zeile 13 = Summe


def _distribute_positions_to_slides(groups: dict):
    """Wrapper für pptx_slides.distribute_positions_to_slides."""
    return distribute_positions_to_slides(groups)
# ---------------------------------------------------------------------------
# Tabellen-Befüllung
# ---------------------------------------------------------------------------
# Spalten-Mapping (welche Spalte enthält was)
COL_WERTPAPIER = 0
COL_KUPON = 2
COL_FAELLIGKEIT = 4
COL_WKN = 6
COL_ANTEIL = 8
COL_RATING = 10

# Spalten die immer leer bleiben (Layout-Spacer)
COL_SPACERS = [1, 3, 5, 7, 9]


def _fill_table_with_positions(table, slide_data: dict, total_weight: float = 1.0, shape_height: int = 0):
    """Wrapper für pptx_slides.fill_table_with_positions."""
    return fill_table_with_positions(table, slide_data, total_weight, shape_height)

    # ── Tabellen-Struktur der Vorlage UNVERÄNDERT lassen ──
    # Früher wurden hier überzählige leere Zeilen entfernt (_optimize_table_layout),
    # das hat aber die Shape-Höhe geschrumpft und LibreOffice zum Vergrößern
    # der verbleibenden Zeilen gebracht → Überlauf am unteren Slide-Rand.
    # Die Vorlage ist mit ihren Zeilenhöhen exakt auf die Slide-Höhe kalibriert,
    # also lassen wir ungefüllte Zeilen einfach leer stehen. Das ergibt zwar
    # visuell einen leeren Bereich zwischen letztem Eintrag und Summenzeile,
    # rendert aber korrekt ohne Überlauf.


# ---------------------------------------------------------------------------
# Slide-Befüllung – Anlagevorschlag (Slides 7+8)
# ---------------------------------------------------------------------------
def _fill_anlagevorschlag_slides(prs, slide_7_idx: int, df: pd.DataFrame, strategy_name: str):
    """Wrapper für pptx_slides.fill_anlagevorschlag_slides."""
    return fill_anlagevorschlag_slides(prs, slide_7_idx, df, strategy_name)


def _fill_performance_slide(prs, slide_idx: int, strategy_name: str, performance_data=None):
    """Wrapper für pptx_slides.fill_performance_slide."""
    return fill_performance_slide(prs, slide_idx, strategy_name, performance_data)


def _replace_chart_data_safe(chart_shape, categories: list, series_data: list,
                              data_label_format: Optional[str] = None):
    """Wrapper für pptx_charts.replace_chart_data_safe.

    Behält die Signatur des bisherigen Aufrufstellen-Codes. Die volle
    Bug-Workaround-Logik (3 Bugs!) lebt jetzt in modules/pptx_charts.py.
    """
    return replace_chart_data_safe(chart_shape, categories, series_data, data_label_format)


def _restore_data_label_format(chart_shape, format_code: str):
    """Wrapper für pptx_charts.restore_data_label_format."""
    return restore_data_label_format(chart_shape, format_code)


def _fill_kennzahlen_table(table, kz: dict):
    """Wrapper für pptx_slides.fill_kennzahlen_table."""
    return fill_kennzahlen_table(table, kz)


def _fmt_pct(val) -> str:
    """Wrapper für formats.fmt_pct (zweite Definition — überschrieb historisch die erste)."""
    return fmt_pct(val)


def _fmt_ratio(val) -> str:
    """Wrapper für formats.fmt_ratio."""
    return fmt_ratio(val)


def _set_cell_text_preserve_format(cell, text: str):
    """Wrapper für pptx_helpers.set_cell_text_preserve_format."""
    return set_cell_text_preserve_format(cell, text)


def _update_chart_values_inplace(chart_shape, categories: list, series_data: list):
    """Wrapper für pptx_charts.update_chart_values_inplace."""
    return update_chart_values_inplace(chart_shape, categories, series_data)


# ─────────────────────────────────────────────────────────────────────────
# Performance-Berechnungs-Funktionen (Duplikate aus streamlit_app.py)
# Werden hier dupliziert, damit pptx_export.py unabhängig vom Streamlit-Code
# ist. Wenn die Funktionen in streamlit_app.py angepasst werden, müssen sie
# hier nachgezogen werden.
# ─────────────────────────────────────────────────────────────────────────
import numpy as _np

def _annual_fee_to_daily_drag(fee_pa_decimal):
    return (1.0 + fee_pa_decimal) ** (1 / 365) - 1


def _make_index_from_returns(d_returns_decimal, startwert=100.0):
    idx = _np.empty(len(d_returns_decimal) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(d_returns_decimal, start=1):
        idx[i] = idx[i-1] * (1.0 + d)
    return idx


def _make_index_after_fee(d_returns_decimal, fee_pa_decimal, startwert=100.0):
    e = _annual_fee_to_daily_drag(fee_pa_decimal)
    idx = _np.empty(len(d_returns_decimal) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(d_returns_decimal, start=1):
        idx[i] = idx[i-1] * (1.0 + (d - e))
    return idx


def _calc_daily_returns_after_fee(d_returns_decimal, fee_pa_decimal):
    return d_returns_decimal - _annual_fee_to_daily_drag(fee_pa_decimal)


def _calc_cagr(idx_after, n_days):
    if n_days <= 0 or idx_after[0] == 0:
        return None
    return (idx_after[-1] / idx_after[0]) ** (365.0 / n_days) - 1.0


def _calc_vola(daily_returns_after_fee):
    if len(daily_returns_after_fee) < 2:
        return None
    return float(_np.std(daily_returns_after_fee, ddof=1) * _np.sqrt(365))


def _drawdown_from_index(idx):
    peak = _np.maximum.accumulate(idx)
    return (idx / peak) - 1.0


def _calc_max_drawdown(idx_after):
    dd = _drawdown_from_index(idx_after)
    return float(_np.min(dd))


def _calc_sharpe_excess(daily_returns_after_fee, rf_annual_series):
    """Sharpe Ratio nach Sharpe (1994), tägliche Excess Returns."""
    rp = pd.Series(daily_returns_after_fee).to_numpy(dtype=float)
    if rp.size < 2:
        return None
    rf_ser = pd.Series(rf_annual_series).reset_index(drop=True)
    if len(rf_ser) != len(rp):
        if len(rf_ser) > len(rp):
            rf_ser = rf_ser.iloc[:len(rp)]
        else:
            rf_ser = rf_ser.reindex(range(len(rp)))
    rf_ann = rf_ser.fillna(0.0).to_numpy(dtype=float)
    daily_rf = (1.0 + rf_ann) ** (1.0/365.0) - 1.0
    mask = ~_np.isnan(rp)
    if mask.sum() < 2:
        return None
    excess = rp[mask] - daily_rf[mask]
    mu = float(_np.mean(excess))
    sd = float(_np.std(excess, ddof=1))
    if sd == 0:
        return None
    return (mu / sd) * _np.sqrt(365.0)


def _calc_period_return(returns):
    return float(_np.prod(1.0 + returns) - 1.0)


def _calc_period_return_after_fee(returns, fee_pa_decimal):
    e = _annual_fee_to_daily_drag(fee_pa_decimal)
    return float(_np.prod(1.0 + (returns - e)) - 1.0)


def compute_performance_data(timeseries_df: pd.DataFrame, fee_dec: float,
                             n_years_bar_chart: int = 5) -> dict:
    """
    Berechnet alle Performance-Daten für die Performance-Folie (Slide 8).

    Diese Funktion ist seit Juni 2026 ein Wrapper — die eigentliche Berechnungs-Logik
    lebt jetzt zentral in `modules/analytics.py` und wird auch vom Streamlit-Performance-Tab
    genutzt. So gibt es nur EINE Stelle für die Mathematik.

    Args:
        timeseries_df: DataFrame mit Spalten 'ret_port', 'ret_bm', 'rf'. Index = Datum.
        fee_dec: Honorarsatz p.a. als Dezimal (z.B. 0.01023 für 1,023% inkl. MwSt).
        n_years_bar_chart: Anzahl Jahre für Säulen-Chart (Default: 5).

    Returns: Dict mit Keys 'kennzahlen', 'performance_pa', 'wertentwicklung'.
             Siehe modules/analytics.py für Details.
    """
    # Lazy import: bricht modules/analytics.py weg, schlägt erst hier auf.
    from modules.analytics import compute_performance_data as _ac
    return _ac(timeseries_df, fee_dec, n_years_bar_chart)


def _remove_empty_table_rows(table):
    """Wrapper für pptx_slides.remove_empty_table_rows."""
    return remove_empty_table_rows(table)


def _fit_shape_to_table(table_shape):
    """Wrapper für pptx_slides.fit_shape_to_table."""
    return fit_shape_to_table(table_shape)


def _adjust_table_shape_height(prs, table_shape, n_data_rows: int, needs_summary: bool):
    """Wrapper für pptx_slides.adjust_table_shape_height."""
    return adjust_table_shape_height(prs, table_shape, n_data_rows, needs_summary)


# ---------------------------------------------------------------------------
# Slide-Befüllung – Aktuelle Portfoliozusammenstellung (Slide 9)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Slide 9: Aktuelle Portfoliozusammenstellung (Regionen + Branchen)
# ---------------------------------------------------------------------------

# Kleine Segmente unter diesem Schwellwert werden zu "Sonstige" zusammengefasst
SMALL_SEGMENT_THRESHOLD = 0.03  # 3%
# Maximal so viele Kategorien in der klassifizierten Aggregation (alle weiteren
# → "Sonstige"). Liquidität wird ggf. NACH dieser Konsolidierung angehängt,
# sodass der Ring am Ende bis zu MAX_SEGMENTS_IN_CHART+1 Segmente haben kann.
MAX_SEGMENTS_IN_CHART = 7


def _consolidate_small_segments(agg_series: pd.Series, threshold: float = SMALL_SEGMENT_THRESHOLD, max_segments: int = MAX_SEGMENTS_IN_CHART):
    """Wrapper für pptx_slides.consolidate_small_segments."""
    return consolidate_small_segments(agg_series, threshold, max_segments)


def _build_ring_series(df: pd.DataFrame, dim_col: str):
    """Wrapper für pptx_slides.build_ring_series."""
    return build_ring_series(df, dim_col)


def _fill_zusammenstellung_slide(prs, slide_idx: int, df: pd.DataFrame, strategy_name: str):
    """Wrapper für pptx_slides.fill_zusammenstellung_slide."""
    return fill_zusammenstellung_slide(prs, slide_idx, df, strategy_name)


# ---------------------------------------------------------------------------
# Slide-Manipulation: Wrapper für pptx_helpers
# ---------------------------------------------------------------------------
def _update_quelle_datum(prs, datum_str: str):
    """Wrapper für pptx_helpers.update_quelle_datum."""
    return update_quelle_datum(prs, datum_str)


def _update_slide_numbers(prs):
    """Wrapper für pptx_helpers.update_slide_numbers — übergibt die lokal
    konfigurierten SHAPE_FOLIENNUMMER_NAMES (Single Source of Truth)."""
    return update_slide_numbers(prs, SHAPE_FOLIENNUMMER_NAMES)


def _move_slide(prs, from_idx: int, to_idx: int):
    """Wrapper für pptx_helpers.move_slide."""
    return move_slide(prs, from_idx, to_idx)


def _remove_slide(prs, slide_idx: int):
    """Wrapper für pptx_helpers.remove_slide."""
    return remove_slide(prs, slide_idx)


def _save_and_reload(prs) -> Presentation:
    """Wrapper für pptx_helpers.save_and_reload."""
    return save_and_reload(prs)


# ---------------------------------------------------------------------------
# Portfolioanalyse-Export (Hauptfunktion)
# ---------------------------------------------------------------------------
def _build_perf_data(performance_inputs, idx: int) -> Optional[dict]:
    """
    Helfer: Berechnet performance_data Dict aus performance_inputs[idx].

    Returns None wenn keine Daten oder ungültige Eingabe — dann zeigt die
    Performance-Folie die Vorlagen-Platzhalter.
    """
    if not performance_inputs or idx >= len(performance_inputs):
        return None
    pi = performance_inputs[idx]
    if pi is None:
        return None
    ts = pi.get("timeseries_df")
    fee = pi.get("fee_dec", 0.0)
    if ts is None or len(ts) == 0:
        return None
    try:
        return compute_performance_data(ts, fee)
    except Exception:
        return None


def generate_portfolioanalyse_pptx(
    portfolios: list,   # Liste von (display_name, df, auswertungsdatum, dur_info)
    anlagevolumen: float = 0.0,
    performance_inputs: Optional[list] = None,
) -> bytes:
    """
    Erstellt eine PPTX mit der Corporate-Vorlage und befüllt die Slides 7-9
    (bzw. 7-9 + Duplikate bei Vergleichsportfolio) mit den Portfolio-Daten.

    Slide-Layout (seit Juni 2026):
    - Slide 7: Anlagevorschlag/Strategieentwurf
    - Slide 8: Performance/Wertentwicklung
    - Slide 9: Aktuelle Portfoliozusammenstellung
    - Bei 2 Portfolios: Duplikate dieser drei Slides für Portfolio 2

    Args:
        portfolios: Liste von Tupeln (display_name, df, auswertungsdatum, duration_info)
        anlagevolumen: Aktuell nicht verwendet, ggf. für Zukunftsfeatures
        performance_inputs: Optional Liste mit Performance-Daten (eine Dict pro Portfolio
                            in gleicher Reihenfolge wie `portfolios`). Format pro Eintrag:
                            {
                                "timeseries_df": pd.DataFrame,  # ret_port, ret_bm, rf
                                "fee_dec": 0.01023,             # effektiver Honorar inkl MwSt
                            }
                            Wenn None oder ein Eintrag None ist: Slide 8 zeigt die
                            Vorlagen-Platzhalter (nur Titel wird gesetzt).

    Returns:
        PPTX-Bytes
    """
    prs = _load_template()

    # ════════════════════════════════════════════════════════════════════════
    # NEUER SLIDE-LAYOUT (Juni 2026):
    #   Slide 7 = Anlagevorschlag/Strategieentwurf (Index 6)
    #   Slide 8 = Performance/Wertentwicklung (Index 7)     ← NEU (war Slide 10)
    #   Slide 9 = Aktuelle Portfoliozusammenstellung (Index 8)
    # ════════════════════════════════════════════════════════════════════════
    # Vorlage v5 hat 25 Slides mit dieser Original-Reihenfolge:
    #   Index 6: Slide 7  (Anlagevorschlag)
    #   Index 7: Slide 8  (Anlagevorschlag-Teil-2)  ← wird ENTFERNT
    #   Index 8: Slide 9  (Portfoliozusammenstellung)
    #   Index 9: Slide 10 (Performance/Wertentwicklung) ← wird zur NEUEN Slide 8
    #   Index 10: Slide 11 (Währungen)  ← wird ENTFERNT
    #
    # Operationen (in dieser Reihenfolge):
    #   1. Index 7 entfernen (alte Anlagevorschlag-Teil-2)
    #      → Performance rutscht von Index 9 → 8, Währungen von 10 → 9
    #   2. Index 9 entfernen (Währungen)
    #      → Reihenfolge: 6=Anlagevorschlag, 7=Portfolio, 8=Performance
    #   3. Move Index 8 (Performance) → Index 7 (vor Portfolio)
    #      → Endreihenfolge: 6=Anlagevorschlag, 7=Performance, 8=Portfolio
    _remove_slide(prs, 7)         # alte Anlagevorschlag-Teil-2 entfernen
    _remove_slide(prs, 9)         # Währungen entfernen (war Index 10, jetzt 9)
    _move_slide(prs, 8, 7)        # Performance vor Portfolio verschieben
    prs = _save_and_reload(prs)   # IDs aufräumen

    # Portfolio(s) befüllen
    if len(portfolios) == 1:
        # Einzelnes Portfolio:
        #   Slide 7 (Index 6) = Anlagevorschlag (mit Strategieentwurf-Titel)
        #   Slide 8 (Index 7) = Performance (mit Strategy-Name im Titel)
        #   Slide 9 (Index 8) = Portfolio-Zusammenstellung
        display_name, df, _, _ = portfolios[0]
        strategy_name = clean_strategy_name(display_name)
        perf_data = _build_perf_data(performance_inputs, 0)
        _fill_anlagevorschlag_slides(prs, 6, df, strategy_name)
        _fill_performance_slide(prs, 7, strategy_name, performance_data=perf_data)
        _fill_zusammenstellung_slide(prs, 8, df, strategy_name)

    elif len(portfolios) == 2:
        # Vergleichsportfolio: Portfolio 1 in Index 6-8, Portfolio 2 als Duplikate
        # an Index 9-11. Endreihenfolge: Anlagevorschlag, Performance, Zusammenstellung
        # pro Portfolio.
        display_name_1, df_1, _, _ = portfolios[0]
        display_name_2, df_2, _, _ = portfolios[1]
        strategy_name_1 = clean_strategy_name(display_name_1)
        strategy_name_2 = clean_strategy_name(display_name_2)
        perf_data_1 = _build_perf_data(performance_inputs, 0)
        perf_data_2 = _build_perf_data(performance_inputs, 1)

        # Schritt 1: Portfolio 1 in Original-Slides (Index 6, 7, 8)
        _fill_anlagevorschlag_slides(prs, 6, df_1, strategy_name_1)
        _fill_performance_slide(prs, 7, strategy_name_1, performance_data=perf_data_1)
        _fill_zusammenstellung_slide(prs, 8, df_1, strategy_name_1)

        # Schritt 2: Drei Duplikate von Slides 7, 8, 9 (Index 6, 7, 8) anlegen
        _duplicate_slide(prs, 6)
        _duplicate_slide(prs, 8)
        _duplicate_slide(prs, 10)

        # Schritt 3: Save/Load nach Duplikation
        prs = _save_and_reload(prs)

        # Schritt 4: Umsortieren
        xml_slides = prs.slides._sldIdLst
        slide_elements = list(xml_slides)

        new_order = list(range(6))
        new_order += [6, 8, 10]
        new_order += [7, 9, 11]
        new_order += list(range(12, len(slide_elements)))

        for elem in slide_elements:
            xml_slides.remove(elem)
        for idx in new_order:
            xml_slides.append(slide_elements[idx])

        # Schritt 5: Save/Load nach Reorder
        prs = _save_and_reload(prs)

        # Schritt 6: Portfolio 2 in Duplikate (Index 9, 10, 11)
        _fill_anlagevorschlag_slides(prs, 9, df_2, strategy_name_2)
        _fill_performance_slide(prs, 10, strategy_name_2, performance_data=perf_data_2)
        _fill_zusammenstellung_slide(prs, 11, df_2, strategy_name_2)

    else:
        raise ValueError(f"Erwarte 1 oder 2 Portfolios, erhalten: {len(portfolios)}")

    # Quelle-Datum aktualisieren auf das Auswertungsdatum des ersten Portfolios.
    # Steht statisch in den Chart-Annotationen (drawing*.xml) der Vorlage als
    # "Quelle: Eigene Berechnung Stand: 12.02.2026" — muss auf das echte
    # Auswertungsdatum aktualisiert werden.
    if portfolios and portfolios[0][2] is not None:
        datum_obj = portfolios[0][2]
        try:
            if hasattr(datum_obj, 'strftime'):
                datum_str = datum_obj.strftime("%d.%m.%Y")
                _update_quelle_datum(prs, datum_str)
        except Exception:
            pass

    # Foliennummern dynamisch setzen (NACH allen Add/Remove/Duplicate-Operationen,
    # VOR dem Speichern). Korrigiert die statischen Werte aus der Vorlage
    # (Slide 7 hat z.B. "13", soll aber "7" sein nach Renumber).
    _update_slide_numbers(prs)

    # Speichern
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()
