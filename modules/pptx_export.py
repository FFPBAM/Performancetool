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
- Für Vergleichsportfolios werden die 4 dynamischen Slides dupliziert

⚠️ WICHTIG (Juli 2026): Diese Version setzt die NEUE Vorlage mit 26 Slides
voraus (Wertentwicklungs-Folie aus der alten cVV-Broschüre an Template-
Position 11). Mit der alten 25-Slide-Vorlage crasht der Export bewusst
früh mit einer klaren Fehlermeldung (siehe _EXPECTED_TEMPLATE_SLIDES).
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

# Slide-Befüllungs-Logik (Domain: Anlagevorschlag, Wertentwicklung, Performance,
# Portfoliozusammenstellung)
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
        # Public API: clean_strategy_name (kein Underscore-Prefix)
        clean_strategy_name,
        # Funktionen (werden über Wrapper unten weiterhin als _xxx exponiert)
        set_title_with_autoscale, safe_marktrisikowert, classify_gattung,
        group_portfolio_positions, distribute_positions_to_slides,
        remove_empty_table_rows, fit_shape_to_table, adjust_table_shape_height,
        consolidate_small_segments, build_ring_series,
        fill_table_with_positions, fill_anlagevorschlag_slides,
        fill_kennzahlen_table, fill_performance_slide,
        fill_wertentwicklung_slide,
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
        clean_strategy_name,
        set_title_with_autoscale, safe_marktrisikowert, classify_gattung,
        group_portfolio_positions, distribute_positions_to_slides,
        remove_empty_table_rows, fit_shape_to_table, adjust_table_shape_height,
        consolidate_small_segments, build_ring_series,
        fill_table_with_positions, fill_anlagevorschlag_slides,
        fill_kennzahlen_table, fill_performance_slide,
        fill_wertentwicklung_slide,
        fill_zusammenstellung_slide,
    )


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
TEMPLATE_PATH = os.path.join("Vorlage", "Vorlage_FFPB.pptx")

_EXPECTED_TEMPLATE_SLIDES = 26
"""Erwartete Slide-Anzahl der Vorlage (seit Juli 2026: 26, mit der
Wertentwicklungs-Folie an Template-Position 11). Schutz gegen den
klassischen Deploy-Fehler 'Code neu, Vorlage alt' — bei Mismatch würden
die hartcodierten Indizes unten die FALSCHEN Folien entfernen/befüllen."""

# Slide-Positionen in der Vorlage (1-indexed, Stand Juli 2026 / 26 Slides):
#   Position 7  = Anlagevorschlag (Aktien + Allokations-Ring)
#   Position 8  = Anlagevorschlag-Teil-2       ← wird beim Export ENTFERNT
#   Position 9  = Portfoliozusammenstellung (Regionen + Branchen)
#   Position 10 = Performance/Wertentwicklung (mit Benchmark)
#   Position 11 = Wertentwicklung/Kurzübersicht (NEU — alte cVV-Folie)
#   Position 12 = Währungen                     ← wird beim Export ENTFERNT
SLIDE_ANLAGEVORSCHLAG_1 = 7
SLIDE_ANLAGEVORSCHLAG_2 = 8
SLIDE_ZUSAMMENSTELLUNG_1 = 9
SLIDE_PERFORMANCE = 10
SLIDE_WERTENTWICKLUNG = 11
SLIDE_WAEHRUNGEN = 12

# Foliennummer-Shape-Namen (uneinheitlich in der Vorlage):
# - Die meisten Slides nutzen "Foliennummer"
# - Slides 7, 8, 10 nutzen "Foliennummernplatzhalter 1" (anderer Layout-Master)
# - Die neue Wertentwicklungs-Folie (cVV-Import) nutzt "Foliennummer"
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
    """Wrapper für pptx_helpers.load_template. Nutzt das modul-lokale TEMPLATE_PATH.

    NEU (Juli 2026): prüft die Slide-Anzahl gegen _EXPECTED_TEMPLATE_SLIDES —
    ein Mismatch bedeutet fast immer 'Code und Vorlage nicht gemeinsam
    deployed' (der klassische Deploy-Fehler, siehe Projektdoku Transferwissen
    #11) und würde sonst später still die falschen Folien treffen.
    """
    prs = load_template(TEMPLATE_PATH)
    n = len(prs.slides)
    if n != _EXPECTED_TEMPLATE_SLIDES:
        raise ValueError(
            f"Vorlage hat {n} Slides, erwartet werden {_EXPECTED_TEMPLATE_SLIDES}. "
            f"Vermutlich wurde die neue Vorlage (mit Wertentwicklungs-Folie an "
            f"Position 11) nicht zusammen mit diesem Code deployed — bitte "
            f"Vorlage/Vorlage_FFPB.pptx im Repo aktualisieren."
        )
    return prs


# ---------------------------------------------------------------------------
# Formatierungs-Helpers — Wrapper für modules.formats (Backwards-Compat)
# ---------------------------------------------------------------------------
def _fmt_pct(value) -> str:
    """Wrapper für formats.fmt_pct. Behält die alte Signatur für internen Code bei."""
    return fmt_pct(value)


def _fmt_date_de(value) -> str:
    """Wrapper für formats.fmt_date_de."""
    return fmt_date_de(value)


def _fmt_ratio(val) -> str:
    """Wrapper für formats.fmt_ratio."""
    return fmt_ratio(val)


# ---------------------------------------------------------------------------
# Weitere Wrapper (Backwards-Compat für Alt-Aufrufer)
# ---------------------------------------------------------------------------
def _set_title_with_autoscale(title_shape, text: str):
    """Wrapper für pptx_slides.set_title_with_autoscale."""
    return set_title_with_autoscale(title_shape, text)


def _safe_float(value, default: float = 0.0) -> float:
    """Wrapper für pptx_helpers.safe_float."""
    return safe_float(value, default)


def _safe_marktrisikowert(value):
    """Wrapper für pptx_slides.safe_marktrisikowert."""
    return safe_marktrisikowert(value)


def _classify_gattung(gattung):
    """Wrapper für pptx_slides.classify_gattung."""
    return classify_gattung(gattung)


def _group_portfolio_positions(df: pd.DataFrame):
    """Wrapper für pptx_slides.group_portfolio_positions."""
    return group_portfolio_positions(df)


def _distribute_positions_to_slides(groups: dict):
    """Wrapper für pptx_slides.distribute_positions_to_slides."""
    return distribute_positions_to_slides(groups)


def _fill_table_with_positions(table, slide_data: dict, total_weight: float = 1.0, shape_height: int = 0):
    """Wrapper für pptx_slides.fill_table_with_positions."""
    return fill_table_with_positions(table, slide_data, total_weight, shape_height)


def _fill_anlagevorschlag_slides(prs, slide_7_idx: int, df: pd.DataFrame,
                                  strategy_name: str, eval_date=None):
    """Wrapper für pptx_slides.fill_anlagevorschlag_slides."""
    return fill_anlagevorschlag_slides(prs, slide_7_idx, df, strategy_name,
                                        eval_date=eval_date)


def _fill_performance_slide(prs, slide_idx: int, strategy_name: str, performance_data=None):
    """Wrapper für pptx_slides.fill_performance_slide."""
    return fill_performance_slide(prs, slide_idx, strategy_name, performance_data)


def _fill_wertentwicklung_slide(prs, slide_idx: int, strategy_name: str, we_data=None):
    """Wrapper für pptx_slides.fill_wertentwicklung_slide (NEU Juli 2026)."""
    return fill_wertentwicklung_slide(prs, slide_idx, strategy_name, we_data)


def _replace_chart_data_safe(chart_shape, categories: list, series_data: list,
                              data_label_format: Optional[str] = None):
    """Wrapper für pptx_charts.replace_chart_data_safe.

    Behält die Signatur des bisherigen Aufrufstellen-Codes. Die volle
    Bug-Workaround-Logik (4 Bugs!) lebt jetzt in modules/pptx_charts.py.
    """
    return replace_chart_data_safe(chart_shape, categories, series_data, data_label_format)


def _restore_data_label_format(chart_shape, format_code: str):
    """Wrapper für pptx_charts.restore_data_label_format."""
    return restore_data_label_format(chart_shape, format_code)


def _fill_kennzahlen_table(table, kz: dict):
    """Wrapper für pptx_slides.fill_kennzahlen_table."""
    return fill_kennzahlen_table(table, kz)


def _set_cell_text_preserve_format(cell, text: str):
    """Wrapper für pptx_helpers.set_cell_text_preserve_format."""
    return set_cell_text_preserve_format(cell, text)


def _update_chart_values_inplace(chart_shape, categories: list, series_data: list):
    """Wrapper für pptx_charts.update_chart_values_inplace."""
    return update_chart_values_inplace(chart_shape, categories, series_data)


def _remove_empty_table_rows(table):
    """Wrapper für pptx_slides.remove_empty_table_rows."""
    return remove_empty_table_rows(table)


def _fit_shape_to_table(table_shape):
    """Wrapper für pptx_slides.fit_shape_to_table."""
    return fit_shape_to_table(table_shape)


def _adjust_table_shape_height(prs, table_shape, n_data_rows: int, needs_summary: bool):
    """Wrapper für pptx_slides.adjust_table_shape_height."""
    return adjust_table_shape_height(prs, table_shape, n_data_rows, needs_summary)


def _consolidate_small_segments(agg_series: pd.Series, threshold: float = None, max_segments: int = None):
    """Wrapper für pptx_slides.consolidate_small_segments."""
    kwargs = {}
    if threshold is not None:
        kwargs["threshold"] = threshold
    if max_segments is not None:
        kwargs["max_segments"] = max_segments
    return consolidate_small_segments(agg_series, **kwargs)


def _build_ring_series(df: pd.DataFrame, dim_col: str):
    """Wrapper für pptx_slides.build_ring_series."""
    return build_ring_series(df, dim_col)


def _fill_zusammenstellung_slide(prs, slide_idx: int, df: pd.DataFrame,
                                  strategy_name: str, eval_date=None):
    """Wrapper für pptx_slides.fill_zusammenstellung_slide."""
    return fill_zusammenstellung_slide(prs, slide_idx, df, strategy_name,
                                        eval_date=eval_date)


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


# ─────────────────────────────────────────────────────────────────────────
# Performance-Berechnungs-Funktionen
# Historische Duplikate aus streamlit_app.py — die zentrale Mathematik lebt
# inzwischen in modules/analytics.py (siehe compute_performance_data unten).
# Die lokalen _calc_*-Helfer bleiben für compute_wertentwicklung_data und
# als Fallback erhalten.
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
    Berechnet alle Performance-Daten für die Performance-Folie.

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


def compute_wertentwicklung_data(timeseries_df: pd.DataFrame, fee_dec: float,
                                 duration: Optional[float] = None,
                                 benchmark_text: Optional[str] = None) -> dict:
    """
    Berechnet die Daten für die Wertentwicklungs-/Kurzübersichts-Folie
    (NEU Juli 2026 — die aus dem alten VBA-Tool übernommene cVV-Folie).

    HINWEIS ARCHITEKTUR: Die Kennzahlen-Mathematik gehört perspektivisch nach
    modules/analytics.py (zentrale Berechnungs-Stelle). Sie liegt vorerst
    hier, weil analytics.py in dieser Session nicht angefasst wurde — beim
    nächsten analytics-Update bitte umziehen.

    Kennzahlen-Definitionen (abgeleitet aus den Fußnoten der Original-Folie):

    1. "Wertentwicklung seit {Auflagejahr} kumuliert*"
       Fußnote *: "nach Kosten bis zum 31.12. des Vorjahres"
       → Kumulierte Rendite NACH Kosten von Auflage bis zum letzten
         Datenpunkt <= 31.12. des Vorjahres. None wenn die Strategie erst
         im laufenden Jahr aufgelegt wurde (dann zeigt die Folie "–").

    2. "Rendite p.a. seit {Auflagejahr} nach Kosten"
       → Annualisierung (365-Tage-Basis, konsistent zu analytics.py) der
         Kennzahl 1 über denselben Zeitraum (Auflage → 31.12. Vorjahr).

    3. "Wertentwicklung seit 01.01.{Jahr}**"
       → YTD-Rendite NACH Kosten mit taggenauem Honorarabzug — identische
         Konvention wie alle übrigen Tool-Kennzahlen (Juli 2026, Philip:
         "die Performance aus dem Tool wird nach Kosten angezeigt und
         täglich abgezogen"). Die alte VBA-Regel "vor Kosten, ab 30.06.
         abzüglich halbjährigen Honorarsatz" wurde damit VERWORFEN; die
         zugehörigen statischen Texte der Vorlage (Fußnote ** und
         Disclaimer-Satz) werden von fill_wertentwicklung_slide dynamisch
         auf die Tool-Konvention umgeschrieben.

    4. "Duration" — wird NICHT hier berechnet, sondern durchgereicht
       (kommt aus den Duration-CSVs / dur_info im Portfolioanalyse-Tab).
       None → Folie zeigt "–" (z.B. reine Aktien-Strategien).

    Chart-Daten (Balken + Linie) kommen 1:1 aus compute_performance_data
    (modules/analytics.py) — identische Datenbasis wie die Performance-Folie:
    Balken = volle Kalenderjahre nach Kosten (max. 5), Linie = gesamte
    Historie als Index (Start 1.0) nach Kosten.

    Args:
        timeseries_df: DataFrame mit Spalten 'ret_port', 'ret_bm', 'rf'
            (Tagesrenditen dezimal), Index = Datum.
        fee_dec: Effektiver Honorarsatz p.a. dezimal (ggf. inkl. MwSt —
            gleiche Konvention wie compute_performance_data).
        duration: Gewichtete Portfolio-Duration (oder None).
        benchmark_text: Benchmark-Zusammensetzung für die ***-Fußnote
            (aus Mapping_Namen.xlsx Spalte D), oder None.

    Returns:
        Dict mit Keys: auflage_jahr, laufendes_jahr, kum_nach_kosten,
        pa_nach_kosten, ytd, duration, benchmark_text, performance_pa,
        wertentwicklung.
    """
    ts = timeseries_df.sort_index()
    dates = pd.to_datetime(ts.index)
    r = pd.to_numeric(ts["ret_port"], errors="coerce").fillna(0.0).to_numpy(dtype=float)

    first_date = dates[0]
    last_date = dates[-1]
    auflage_jahr = int(first_date.year)
    laufendes_jahr = int(last_date.year)

    drag = _annual_fee_to_daily_drag(fee_dec)

    # ── Kennzahl 1 + 2: kumuliert / p.a. bis 31.12. des Vorjahres ──
    cutoff = pd.Timestamp(laufendes_jahr - 1, 12, 31)
    mask_hist = dates <= cutoff
    kum_nach_kosten = None
    pa_nach_kosten = None
    if mask_hist.any():
        r_af = r[mask_hist] - drag
        kum_nach_kosten = float(_np.prod(1.0 + r_af) - 1.0)
        n_days = int((dates[mask_hist][-1] - first_date).days)
        if n_days > 0:
            pa_nach_kosten = (1.0 + kum_nach_kosten) ** (365.0 / n_days) - 1.0

    # ── Kennzahl 3: YTD nach Kosten (taggenauer Honorarabzug, Tool-Konvention) ──
    ytd = None
    ytd_start = pd.Timestamp(laufendes_jahr, 1, 1)
    mask_ytd = dates >= ytd_start
    if mask_ytd.any():
        r_af_ytd = r[mask_ytd] - drag
        ytd = float(_np.prod(1.0 + r_af_ytd) - 1.0)

    # ── Chart-Daten: identische Basis wie Performance-Folie ──
    charts = compute_performance_data(timeseries_df, fee_dec)

    return {
        "auflage_jahr": auflage_jahr,
        "laufendes_jahr": laufendes_jahr,
        "kum_nach_kosten": kum_nach_kosten,
        "pa_nach_kosten": pa_nach_kosten,
        "ytd": ytd,
        "duration": duration,
        "benchmark_text": benchmark_text,
        "performance_pa": charts.get("performance_pa", {}),
        "wertentwicklung": charts.get("wertentwicklung", {}),
    }


# ---------------------------------------------------------------------------
# Portfolioanalyse-Export (Hauptfunktion)
# ---------------------------------------------------------------------------
LAST_BUILD_ERRORS: list = []
"""Diagnose (NEU Juli 2026): Fehler, die beim Berechnen der Folien-Daten
aufgetreten sind. Wird von generate_portfolioanalyse_pptx zu Beginn geleert.
Hintergrund: _build_perf_data/_build_we_data fangen Exceptions bewusst ab
(eine kaputte Kennzahl soll nicht den ganzen Export crashen — die Folie
zeigt dann Platzhalter). Vorher passierte das STILL und war im UI nicht
diagnostizierbar ("Folie wird nicht befüllt, aber kein Fehler"). Jetzt
sammelt diese Liste die Fehlermeldungen; der Aufrufer (portfolioanalyse.py)
zeigt sie nach dem Export als Warnung an."""


def _record_build_error(context: str, exc: Exception):
    import traceback
    LAST_BUILD_ERRORS.append(
        f"{context}: {type(exc).__name__}: {exc}"
    )
    # Voller Traceback zusätzlich in die Server-Logs (streamlit-Konsole)
    traceback.print_exc()


def _build_perf_data(performance_inputs, idx: int) -> Optional[dict]:
    """
    Helfer: Berechnet performance_data Dict aus performance_inputs[idx].

    Returns None wenn keine Daten oder ungültige Eingabe — dann zeigt die
    Performance-Folie die Vorlagen-Platzhalter. Berechnungsfehler landen
    in LAST_BUILD_ERRORS (siehe oben) statt still verschluckt zu werden.
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
    except Exception as exc:
        _record_build_error(f"Performance-Folie, Portfolio {idx + 1}", exc)
        return None


def _build_we_data(performance_inputs, idx: int) -> Optional[dict]:
    """
    Helfer (NEU Juli 2026): Berechnet das we_data-Dict für die
    Wertentwicklungs-Folie aus performance_inputs[idx].

    Nutzt dieselbe Zeitreihe/fee wie die Performance-Folie, zusätzlich die
    OPTIONALEN Keys "duration" und "benchmark_text" im performance_inputs-
    Eintrag (siehe Snippet für portfolioanalyse.py). Fehlen die Keys, zeigt
    die Folie an den Stellen "–" bzw. behält die Vorlagen-Fußnote —
    vollständig rückwärtskompatibel zu Alt-Aufrufern.

    Returns None wenn keine Daten — dann zeigt die Folie Vorlagen-Platzhalter
    (nur der Titel wird gesetzt).
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
        return compute_wertentwicklung_data(
            ts, fee,
            duration=pi.get("duration"),
            benchmark_text=pi.get("benchmark_text"),
        )
    except Exception as exc:
        _record_build_error(f"Wertentwicklungs-Folie, Portfolio {idx + 1}", exc)
        return None


def generate_portfolioanalyse_pptx(
    portfolios: list,   # Liste von (display_name, df, auswertungsdatum, dur_info)
    anlagevolumen: float = 0.0,
    performance_inputs: Optional[list] = None,
) -> bytes:
    """
    Erstellt eine PPTX mit der Corporate-Vorlage und befüllt die Slides 7-10
    (bzw. 7-10 + Duplikate bei Vergleichsportfolio) mit den Portfolio-Daten.

    Slide-Layout (seit Juli 2026 — Wertentwicklungs-Folie NEU als Folie 8):
    - Slide 7:  Anlagevorschlag/Strategieentwurf
    - Slide 8:  Wertentwicklung/Kurzübersicht (NEU — alte cVV-Folie)
    - Slide 9:  Performance/Wertentwicklung (mit Benchmark)
    - Slide 10: Aktuelle Portfoliozusammenstellung
    - Bei 2 Portfolios: Duplikate dieser VIER Slides für Portfolio 2

    Args:
        portfolios: Liste von Tupeln (display_name, df, auswertungsdatum, duration_info)
        anlagevolumen: Aktuell nicht verwendet, ggf. für Zukunftsfeatures
        performance_inputs: Optional Liste mit Performance-Daten (ein Dict pro Portfolio
                            in gleicher Reihenfolge wie `portfolios`). Format pro Eintrag:
                            {
                                "timeseries_df": pd.DataFrame,  # ret_port, ret_bm, rf
                                "fee_dec": 0.01023,             # effektiver Honorar inkl MwSt
                                # NEU Juli 2026 (beide optional):
                                "duration": 4.24,               # gewichtete Duration oder None
                                "benchmark_text": "50% iBoxx ...",  # für ***-Fußnote
                            }
                            Wenn None oder ein Eintrag None ist: Folie 8+9 zeigen die
                            Vorlagen-Platzhalter (nur Titel werden gesetzt).

    Returns:
        PPTX-Bytes
    """
    LAST_BUILD_ERRORS.clear()  # Diagnose-Liste pro Export frisch (siehe oben)
    prs = _load_template()

    # ════════════════════════════════════════════════════════════════════════
    # SLIDE-LAYOUT (Juli 2026 — Vorlage hat jetzt 26 Slides):
    #   Ziel-Reihenfolge im Export:
    #     Slide 7  = Anlagevorschlag/Strategieentwurf (Index 6)
    #     Slide 8  = Wertentwicklung/Kurzübersicht (Index 7)   ← NEU (cVV-Folie)
    #     Slide 9  = Performance/Wertentwicklung mit BM (Index 8)
    #     Slide 10 = Aktuelle Portfoliozusammenstellung (Index 9)
    # ════════════════════════════════════════════════════════════════════════
    # Vorlage (26 Slides) hat diese Original-Reihenfolge:
    #   Index 6:  Slide 7  (Anlagevorschlag)
    #   Index 7:  Slide 8  (Anlagevorschlag-Teil-2)   ← wird ENTFERNT
    #   Index 8:  Slide 9  (Portfoliozusammenstellung)
    #   Index 9:  Slide 10 (Performance/Wertentwicklung mit BM)
    #   Index 10: Slide 11 (Wertentwicklung/Kurzübersicht — NEU)
    #   Index 11: Slide 12 (Währungen)                ← wird ENTFERNT
    #
    # Operationen (in dieser Reihenfolge):
    #   1. Index 7 entfernen (alte Anlagevorschlag-Teil-2)
    #      → [6=AV, 7=Zus, 8=Perf, 9=NEU, 10=Währungen, ...]
    #   2. Index 10 entfernen (Währungen)
    #      → [6=AV, 7=Zus, 8=Perf, 9=NEU]
    #   3. Move Index 9 (NEU) → Index 7
    #      → [6=AV, 7=NEU, 8=Zus, 9=Perf]
    #   4. Move Index 9 (Perf) → Index 8
    #      → [6=AV, 7=NEU, 8=Perf, 9=Zus]   ← Endreihenfolge
    _remove_slide(prs, 7)         # alte Anlagevorschlag-Teil-2 entfernen
    _remove_slide(prs, 10)        # Währungen entfernen (war Index 11, nach Op1 = 10)
    _move_slide(prs, 9, 7)        # Wertentwicklungs-Folie an Position 8 (Index 7)
    _move_slide(prs, 9, 8)        # Performance an Position 9 (Index 8), Zus. rutscht auf 9
    prs = _save_and_reload(prs)   # IDs aufräumen

    # Portfolio(s) befüllen
    if len(portfolios) == 1:
        # Einzelnes Portfolio:
        #   Slide 7  (Index 6) = Anlagevorschlag (mit Strategieentwurf-Titel)
        #   Slide 8  (Index 7) = Wertentwicklung/Kurzübersicht (NEU)
        #   Slide 9  (Index 8) = Performance (mit Strategy-Name im Titel)
        #   Slide 10 (Index 9) = Portfolio-Zusammenstellung
        display_name, df, eval_date, _dur = portfolios[0]
        strategy_name = clean_strategy_name(display_name)
        perf_data = _build_perf_data(performance_inputs, 0)
        we_data = _build_we_data(performance_inputs, 0)
        _fill_anlagevorschlag_slides(prs, 6, df, strategy_name, eval_date=eval_date)
        _fill_wertentwicklung_slide(prs, 7, strategy_name, we_data=we_data)
        _fill_performance_slide(prs, 8, strategy_name, performance_data=perf_data)
        _fill_zusammenstellung_slide(prs, 9, df, strategy_name, eval_date=eval_date)

    elif len(portfolios) == 2:
        # Vergleichsportfolio: Portfolio 1 in Index 6-9, Portfolio 2 als Duplikate
        # an Index 10-13. Endreihenfolge: Anlagevorschlag, Wertentwicklung,
        # Performance, Zusammenstellung pro Portfolio.
        display_name_1, df_1, eval_date_1, _dur1 = portfolios[0]
        display_name_2, df_2, eval_date_2, _dur2 = portfolios[1]
        strategy_name_1 = clean_strategy_name(display_name_1)
        strategy_name_2 = clean_strategy_name(display_name_2)
        perf_data_1 = _build_perf_data(performance_inputs, 0)
        perf_data_2 = _build_perf_data(performance_inputs, 1)
        we_data_1 = _build_we_data(performance_inputs, 0)
        we_data_2 = _build_we_data(performance_inputs, 1)

        # Schritt 1: Portfolio 1 in Original-Slides (Index 6, 7, 8, 9)
        _fill_anlagevorschlag_slides(prs, 6, df_1, strategy_name_1, eval_date=eval_date_1)
        _fill_wertentwicklung_slide(prs, 7, strategy_name_1, we_data=we_data_1)
        _fill_performance_slide(prs, 8, strategy_name_1, performance_data=perf_data_1)
        _fill_zusammenstellung_slide(prs, 9, df_1, strategy_name_1, eval_date=eval_date_1)

        # Schritt 2: VIER Duplikate der Slides an Index 6, 8, 10, 12 anlegen.
        # duplicate_slide fügt das Duplikat direkt HINTER der Quelle ein,
        # dadurch verschieben sich die Folge-Indizes nach jedem Aufruf:
        #   Start:   [6=AV, 7=NEU, 8=Perf, 9=Zus]
        #   dup(6):  [6=AV, 7=AV', 8=NEU, 9=Perf, 10=Zus]
        #   dup(8):  [6=AV, 7=AV', 8=NEU, 9=NEU', 10=Perf, 11=Zus]
        #   dup(10): [6=AV, 7=AV', 8=NEU, 9=NEU', 10=Perf, 11=Perf', 12=Zus]
        #   dup(12): [..., 12=Zus, 13=Zus']
        _duplicate_slide(prs, 6)
        _duplicate_slide(prs, 8)
        _duplicate_slide(prs, 10)
        _duplicate_slide(prs, 12)

        # Schritt 3: Save/Load nach Duplikation
        prs = _save_and_reload(prs)

        # Schritt 4: Umsortieren
        #   Ist:  [6=AV, 7=AV', 8=NEU, 9=NEU', 10=Perf, 11=Perf', 12=Zus, 13=Zus']
        #   Soll: [6=AV, 7=NEU, 8=Perf, 9=Zus, 10=AV', 11=NEU', 12=Perf', 13=Zus']
        xml_slides = prs.slides._sldIdLst
        slide_elements = list(xml_slides)

        new_order = list(range(6))
        new_order += [6, 8, 10, 12]     # Portfolio 1: AV, NEU, Perf, Zus
        new_order += [7, 9, 11, 13]     # Portfolio 2: AV', NEU', Perf', Zus'
        new_order += list(range(14, len(slide_elements)))

        for elem in slide_elements:
            xml_slides.remove(elem)
        for idx in new_order:
            xml_slides.append(slide_elements[idx])

        # Schritt 5: Save/Load nach Reorder
        prs = _save_and_reload(prs)

        # Schritt 6: Portfolio 2 in Duplikate (Index 10, 11, 12, 13)
        _fill_anlagevorschlag_slides(prs, 10, df_2, strategy_name_2, eval_date=eval_date_2)
        _fill_wertentwicklung_slide(prs, 11, strategy_name_2, we_data=we_data_2)
        _fill_performance_slide(prs, 12, strategy_name_2, performance_data=perf_data_2)
        _fill_zusammenstellung_slide(prs, 13, df_2, strategy_name_2, eval_date=eval_date_2)

    else:
        raise ValueError(f"Erwarte 1 oder 2 Portfolios, erhalten: {len(portfolios)}")

    # Quelle-Datum aktualisieren auf das Auswertungsdatum des ersten Portfolios.
    # Steht statisch in den Chart-Annotationen (drawing*.xml) der Vorlage als
    # "Quelle: Eigene Berechnung Stand: 12.02.2026" — muss auf das echte
    # Auswertungsdatum aktualisiert werden. Deckt auch die "Quelle"-Textbox
    # der neuen Wertentwicklungs-Folie ab (gleiches "Stand ..."-Muster).
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
