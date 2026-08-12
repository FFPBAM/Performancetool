"""
modules/analytics.py — Performance-Berechnungs-Funktionen für die Broschüre.

Eine zentrale Stelle für alle Berechnungen (CAGR, Volatilität, Sharpe Ratio,
Max Drawdown, Kalenderjahres-Returns, Wertentwicklungs-Index). Beide Konsumenten
nutzen es:
- streamlit_app.py: für die UI-Kennzahlen-Anzeige (Tab 1: Performance)
- pptx_export.py: für die Performance-Folie der Broschüre

Eingabe-Format (überall identisch):
- Tagesrenditen als DEZIMAL (0.005 = 0,5%) — NICHT als Prozent (0.5)
- Honorarsätze als DEZIMAL (0.01023 = 1,023%)
- Risikofreier Zins als ANNUALISIERTER DEZIMAL (0.04 = 4% p.a.)

Diese Datei hat KEINE Imports von Streamlit oder python-pptx.
Sie kann unverändert in lokalen Python-Skripten genutzt werden.

Mathematische Konventionen:
- Annualisierungs-Basis: 365 Tage (Kalendertage, nicht Handelstage)
- Sharpe Ratio: Excess-Return-Variante nach Sharpe (1994) — tägliche Excess Returns
- Drawdown: (idx / cummax(idx)) - 1 — negativ
"""

from typing import Optional, Sequence

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Sätze: annualisiert → täglich (365-Kalendertage-Basis)
# ─────────────────────────────────────────────────────────────────────────────

def annual_to_daily_rate(annual_rate):
    """Rechnet einen annualisierten Satz auf den Tagessatz um.

    Formel: daily = (1 + annual)^(1/365) - 1

    Nimmt einen einzelnen Wert ODER eine Reihe: Der Honorarsatz ist eine
    Zahl, der risikofreie Zins kommt als Zeitreihe (ein annualisierter Wert
    je Tag). Die Umrechnung ist in beiden Fällen dieselbe.

    ZUSAMMENGEFÜHRT 12.08.2026 (Backlog E): Diese drei Zeilen standen an
    vier Stellen — hier, in `calc_sharpe_excess` und zweimal in
    `streamlit_app.py` (`aggregate_rf_geometric`, `make_index_from_rf`).
    Formelgleich, und damit dasselbe Risiko wie bei der Honorar-Mathematik:
    Eine Korrektur an einer Stelle hätte die anderen drei nicht erreicht.

    WARUM DER HONORARSATZ TROTZDEM SEINEN EIGENEN NAMEN BEHÄLT: Die
    Mathematik ist identisch, die Größen sind es nicht. Ein Honorar wird
    ABGEZOGEN, ein Zins wird GUTGESCHRIEBEN. Wer im Code
    `annual_to_daily_rate(fee)` liest, sieht dem Aufruf das Vorzeichen nicht
    mehr an — deshalb ruft `annual_fee_to_daily_drag` diese Funktion nur auf,
    statt zu verschwinden.

    Args:
        annual_rate: Annualisierter Satz als Dezimal (0.03 = 3 % p.a.),
            einzeln oder als Sequence/Array/Series.

    Returns:
        Tagessatz — als np.float64 bei einem Einzelwert, sonst als Array.

    Examples:
        >>> round(float(annual_to_daily_rate(0.03)), 10)
        8.09863e-05
    """
    return (1.0 + np.asarray(annual_rate, dtype=float)) ** (1.0 / 365.0) - 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Kosten-Modellierung (Honorarsatz → tägliche Belastung)
# ─────────────────────────────────────────────────────────────────────────────

def annual_fee_to_daily_drag(fee_pa_decimal: float) -> float:
    """Wandelt einen jährlichen Honorarsatz in eine äquivalente tägliche Belastung.

    Formel: daily = (1 + fee_pa)^(1/365) - 1

    Args:
        fee_pa_decimal: Honorarsatz p.a. als Dezimal (z.B. 0.012 für 1,2% p.a.)

    Returns:
        Tägliche Belastung als Dezimal.

    Examples:
        >>> round(annual_fee_to_daily_drag(0.012), 8)
        3.268e-05
    """
    # Dieselbe Umrechnung wie beim risikofreien Zins (siehe dort), aber mit
    # sprechendem Namen: Diese Größe wird abgezogen, nicht gutgeschrieben.
    # Bit-identisch zur früheren Fassung `(1.0 + fee) ** (1 / 365) - 1`
    # (12.08.2026 an allen vorkommenden Sätzen nachgemessen).
    return float(annual_to_daily_rate(fee_pa_decimal))


def calc_daily_returns_after_fee(d_returns_decimal: Sequence[float],
                                  fee_pa_decimal: float) -> np.ndarray:
    """Subtrahiert die tägliche Honorar-Belastung von Brutto-Tagesrenditen.

    Returns:
        Array von Netto-Tagesrenditen (nach Kosten).
    """
    arr = np.asarray(d_returns_decimal, dtype=float)
    return arr - annual_fee_to_daily_drag(fee_pa_decimal)


def calc_period_return(returns: Sequence[float]) -> float:
    """Geometrische Periodenrendite aus Tagesrenditen.

    Formel: Π(1 + r_t) - 1

    Examples:
        >>> round(calc_period_return([0.01, 0.01, -0.02]), 6)
        -0.000302

    (Der Wert stand bis 12.08.2026 als -0.000198 hier — schlicht falsch
    gerechnet: 1,01 × 1,01 × 0,98 = 0,999698. Der Code war immer richtig,
    nur das Beispiel nicht. Aufgefallen beim Schreiben von
    tests/test_analytics.py; Doctests laufen hier sonst nicht mit.)
    """
    return float(np.prod(1.0 + np.asarray(returns, dtype=float)) - 1.0)


def calc_period_return_after_fee(returns: Sequence[float],
                                  fee_pa_decimal: float) -> float:
    """Geometrische Periodenrendite nach Kosten."""
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    arr = np.asarray(returns, dtype=float)
    return float(np.prod(1.0 + (arr - e)) - 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Index-Aufbau (Performance-Index aus Tagesrenditen)
# ─────────────────────────────────────────────────────────────────────────────

def make_index_from_returns(d_returns_decimal: Sequence[float],
                            startwert: float = 100.0) -> np.ndarray:
    """Baut einen Index aus Tagesrenditen.

    idx[0] = startwert; idx[i] = idx[i-1] * (1 + r[i-1])

    Returns:
        Array mit len(returns)+1 Werten (inklusive Startwert).
    """
    arr = np.asarray(d_returns_decimal, dtype=float)
    idx = np.empty(len(arr) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(arr, start=1):
        idx[i] = idx[i-1] * (1.0 + d)
    return idx


def make_index_after_fee(d_returns_decimal: Sequence[float],
                         fee_pa_decimal: float,
                         startwert: float = 100.0) -> np.ndarray:
    """Baut einen Index aus Tagesrenditen NACH Kosten.

    Die tägliche Honorar-Belastung wird täglich vom Brutto-Return abgezogen
    (Zinseszinseffekt taggenau).
    """
    arr = np.asarray(d_returns_decimal, dtype=float)
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    idx = np.empty(len(arr) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(arr, start=1):
        idx[i] = idx[i-1] * (1.0 + (d - e))
    return idx


# ─────────────────────────────────────────────────────────────────────────────
# Risiko-/Rendite-Kennzahlen
# ─────────────────────────────────────────────────────────────────────────────

def calc_cagr(idx_after: Sequence[float], n_days: int) -> Optional[float]:
    """Compound Annual Growth Rate (CAGR) aus einem Index.

    Formel: (idx[-1] / idx[0])^(365/n_days) - 1

    Args:
        idx_after: Index-Reihe (z.B. aus `make_index_after_fee`)
        n_days: Zeitraum in Tagen (Kalendertage)

    Returns:
        CAGR als Dezimal, oder None bei degeneriertem Input.
    """
    if n_days <= 0 or len(idx_after) == 0 or idx_after[0] == 0:
        return None
    return (idx_after[-1] / idx_after[0]) ** (365.0 / n_days) - 1.0


def calc_vola(daily_returns_after_fee: Sequence[float]) -> Optional[float]:
    """Annualisierte Volatilität: std(tagesrenditen) × √365.

    Stichproben-Standardabweichung (ddof=1).
    """
    arr = np.asarray(daily_returns_after_fee, dtype=float)
    if len(arr) < 2:
        return None
    return float(np.std(arr, ddof=1) * np.sqrt(365))


def drawdown_from_index(idx: Sequence[float]) -> np.ndarray:
    """Drawdown-Serie: (idx / cummax(idx)) - 1. Negative Werte."""
    arr = np.asarray(idx, dtype=float)
    peak = np.maximum.accumulate(arr)
    return (arr / peak) - 1.0


def calc_max_drawdown(idx_after: Sequence[float]) -> Optional[float]:
    """Maximaler Drawdown als negativer Dezimal-Wert (-0.16 = -16%)."""
    arr = np.asarray(idx_after, dtype=float)
    if len(arr) == 0:
        return None
    dd = drawdown_from_index(arr)
    return float(np.min(dd))


def has_benchmark(ret_bm) -> bool:
    """Prüft, ob eine ECHTE Benchmark-Zeitreihe vorliegt.

    WARUM NICHT `notna().any()` (BUGFIX 07.08.2026):
    Infront liefert für Strategien ohne Vergleichsmaßstab keine leere Spalte,
    sondern eine mit lauter NULLEN gefüllte. `notna().any()` ist dort True
    (0.0 ist nicht NaN) — die Null-Reihe wurde deshalb als Benchmark
    durchgerechnet. Betroffen sind "Muster SCHWEIZ Aktien" und "Muster
    SCHWEIZ Substanz"; im Mapping_Namen.xlsx (Spalte D) steht bei beiden
    ausdrücklich "Haben keine Benchmark".

    Folgen vor dem Fix (an echten Daten reproduziert):
        performance_pa_bench      0,00 %
        volatilitaet_bench        0,00 %
        sharpe_bench            -67,48      ← in einer Kundenbroschüre
        max_drawdown_bench        0,00 %
        Linien-Chart: flache Benchmark bei 100 %

    Eine Benchmark gilt als vorhanden, sobald mindestens ein Wert ungleich
    null ist. Einzelne Null-Tage (Wochenenden — rund 29 % aller Zeilen) sind
    dagegen völlig normal und bleiben unberührt.

    Args:
        ret_bm: Benchmark-Tagesrenditen (Series, Array oder Liste)

    Returns:
        True, wenn mindestens ein Wert vorhanden UND ungleich null ist.
    """
    werte = pd.Series(ret_bm).dropna()
    if werte.empty:
        return False
    return bool((werte != 0).any())


def calc_sharpe_excess(daily_returns_after_fee: Sequence[float],
                       rf_annual_series: Sequence[float]) -> Optional[float]:
    """Sharpe Ratio nach Sharpe (1994) — tägliche Excess Returns.

    Schritte:
        1. Tagessatz aus annualisiertem rf: daily_rf = (1+rf)^(1/365) - 1
        2. Excess: ret_port_nach_Kosten - daily_rf
        3. Sharpe_daily = mean(excess) / std(excess, ddof=1)
        4. Annualisierung: × √365

    Args:
        daily_returns_after_fee: Netto-Tagesrenditen (nach Kosten)
        rf_annual_series: Annualisierter rf pro Tag (Series oder Array)

    Returns:
        Annualisierte Sharpe Ratio als float, oder None bei degeneriertem Input.
    """
    rp = pd.Series(daily_returns_after_fee).to_numpy(dtype=float)
    if rp.size < 2:
        return None
    rf_ser = pd.Series(rf_annual_series).reset_index(drop=True)
    # Längen angleichen
    if len(rf_ser) != len(rp):
        if len(rf_ser) > len(rp):
            rf_ser = rf_ser.iloc[:len(rp)]
        else:
            rf_ser = rf_ser.reindex(range(len(rp)))
    rf_ann = rf_ser.fillna(0.0).to_numpy(dtype=float)
    daily_rf = annual_to_daily_rate(rf_ann)
    mask = ~np.isnan(rp)
    if mask.sum() < 2:
        return None
    excess = rp[mask] - daily_rf[mask]
    mu = float(np.mean(excess))
    sd = float(np.std(excess, ddof=1))
    # NICHT auf exakte Null pruefen (korrigiert 12.08.2026). Bei lauter
    # Nullen liefert numpy sauber 0.0, bei KONSTANTEN Renditen ungleich null
    # dagegen eine Reststreuung von rund 2e-19 — und mu/sd wird dann zu einer
    # Zahl der Groessenordnung 1e16. Die stuende als "Sharpe Ratio" in einer
    # Kundenbroschuere, wie schon einmal die -67,48 (Transferwissen #41).
    # Alles unter 1e-12 Tagesstreuung ist keine Streuung mehr, sondern
    # Rechenrauschen: das waere eine Schwankung von 0,0000000001 % am Tag.
    if not np.isfinite(sd) or sd < 1e-12:
        return None
    return (mu / sd) * np.sqrt(365.0)


# ─────────────────────────────────────────────────────────────────────────────
# High-Level: Performance-Daten für die Broschüre
# ─────────────────────────────────────────────────────────────────────────────

JAHR_RAND_TOLERANZ_TAGE = 3
"""Wieviele Tage an JEDEM Rand eines Kalenderjahres fehlen dürfen, damit es
noch als vollständig gilt (12.08.2026).

Am Jahresende gab es diese Toleranz schon immer — `last_full_year` unten
verlangt Daten "mindestens bis 28.12.", lässt also den 29./30./31. offen.
Die Regel gilt jetzt spiegelbildlich am Jahresanfang: die Reihe muss
spätestens am 4. Januar beginnen. Grund ist derselbe wie am Jahresende —
Feiertage. Eine Strategie, deren erster Kurs am 02.01. steht, hat das Jahr
vollständig durchlaufen; ihr Jahr deshalb zu verwerfen wäre falsch.

Drei Tage und nicht mehr: Der 06.01. ist in Teilen Deutschlands Feiertag,
liegt aber schon jenseits dessen, was man "Jahresanfang" nennen kann."""


def _ist_volles_jahr(sub: pd.DataFrame, jahr: int) -> bool:
    """Deckt `sub` (die Zeilen EINES Kalenderjahres) das Jahr wirklich ab?

    Der Säulen-Chart der Broschüre trägt die Überschrift "PERFORMANCE P.A.
    (NACH KOSTEN) IM BENCHMARKVERGLEICH". Ein Balken darunter behauptet also
    eine JAHRESrendite. Bis zum 12.08.2026 prüfte die Schleife nur
    `sub.empty` — ein angebrochenes Auflagejahr wurde damit als voller
    Jahresbalken gezeichnet. An "Muster FFPB Pro" (Auflage 01.09.2023) stand
    so ein 122-Tage-Wert von +3,23 % als "2023" neben den echten Jahren 2024
    und 2025; betroffen waren 7 der 19 Strategien. Das ist keine Kosmetik,
    sondern eine falsche Sachaussage in einem Kundendokument.

    Geprüft werden BEIDE Ränder, und zwar aus `sub` selbst statt aus dem
    Anfang der Gesamtreihe: So greift die Regel auch bei einem Loch mitten in
    der Historie und nicht nur beim Auflagejahr.

    Prüfstein: tests/test_kalenderjahre.py
    """
    if sub.empty:
        return False
    tol = pd.Timedelta(days=JAHR_RAND_TOLERANZ_TAGE)
    beginnt_rechtzeitig = sub.index.min() <= pd.Timestamp(jahr, 1, 1) + tol
    endet_rechtzeitig = sub.index.max() >= pd.Timestamp(jahr, 12, 31) - tol
    return bool(beginnt_rechtzeitig and endet_rechtzeitig)


def compute_performance_data(timeseries_df: pd.DataFrame,
                             fee_dec: float,
                             n_years_bar_chart: int = 5) -> dict:
    """Berechnet alle Performance-Daten für die Performance-Folie der Broschüre.

    Args:
        timeseries_df: DataFrame mit DatumsIndex und Spalten:
            - 'ret_port' (Tagesrendite Portfolio, dezimal)
            - 'ret_bm'   (Tagesrendite Benchmark, dezimal) — optional
            - 'rf'       (Annualisierter risikofreier Zins, dezimal) — optional
        fee_dec: Honorarsatz p.a. als Dezimal (z.B. 0.01023 für 1,023% inkl MwSt)
        n_years_bar_chart: GRÖSSE DES FENSTERS für den Säulen-Chart (Default: 5)
            — betrachtet werden die letzten 5 abgeschlossenen Kalenderjahre,
            nicht die letzten 5 gelieferten Balken. Siehe "jahre" unten.

    Returns:
        Dict im Format das die Performance-Folie erwartet:
        {
            "has_benchmark": True/False,
            "kennzahlen": {
                "performance_pa_ref", "performance_pa_bench",
                "volatilitaet_ref", "volatilitaet_bench",
                "sharpe_ref", "sharpe_bench",
                "max_drawdown_ref", "max_drawdown_bench",
            },
            "performance_pa": {"jahre": [...], "referenz": [...], "benchmark": [...]},
            "wertentwicklung": {"dates": [...], "referenz": [...], "benchmark": [...]},
        }

        OHNE Benchmark (has_benchmark=False) sind die "bench"-Kennzahlen None
        UND die beiden "benchmark"-Listen LEER — es gibt dann nichts zu
        zeichnen. Wer daraus Chart-Serien baut, darf die Benchmark-Serie in
        diesem Fall nicht anlegen (siehe pptx_slides).

        ZUSAGE für "performance_pa.jahre" (12.08.2026): Die Liste enthält
        AUSSCHLIESSLICH Kalenderjahre, die die Zeitreihe vollständig abdeckt
        (siehe _ist_volles_jahr). Sie ist damit oft KÜRZER als
        n_years_bar_chart und im Grenzfall LEER — nämlich dann, wenn die
        Strategie noch kein volles Kalenderjahr hinter sich hat. Wer sie
        weiterverarbeitet, muss den leeren Fall behandeln; in der Broschüre
        tut das pptx_export._build_we_data mit einer sichtbaren Warnung.

        Bei leerem DataFrame: Dict mit leeren Sub-Dicts.
    """
    df = timeseries_df.copy()
    if df.empty:
        return {"has_benchmark": False, "kennzahlen": {},
                "performance_pa": {}, "wertentwicklung": {}}

    rp = df["ret_port"].to_numpy(float)
    # has_benchmark statt notna().any(): eine Spalte aus lauter Nullen ist
    # KEINE Benchmark — siehe Docstring dort (Bugfix 07.08.2026).
    has_bm = "ret_bm" in df.columns and has_benchmark(df["ret_bm"])
    rb = df["ret_bm"].fillna(0.0).to_numpy(float) if has_bm else None
    has_rf = "rf" in df.columns and df["rf"].notna().any()
    rf = df["rf"] if has_rf else pd.Series([0.0] * len(rp))

    # ── KENNZAHLEN ──
    n_days = len(rp)
    ia_ref = make_index_after_fee(rp, fee_dec, 100.0)
    draf_ref = calc_daily_returns_after_fee(rp, fee_dec)
    cagr_ref = calc_cagr(ia_ref, n_days)
    vola_ref = calc_vola(draf_ref)
    sharpe_ref = calc_sharpe_excess(draf_ref, rf) if has_rf else None
    mdd_ref = calc_max_drawdown(ia_ref)

    if has_bm:
        ib_bench = make_index_from_returns(rb, 100.0)
        cagr_bench = calc_cagr(ib_bench, n_days)
        vola_bench = calc_vola(rb)
        sharpe_bench = calc_sharpe_excess(rb, rf) if has_rf else None
        mdd_bench = calc_max_drawdown(ib_bench)
    else:
        cagr_bench = vola_bench = sharpe_bench = mdd_bench = None

    kennzahlen = {
        "performance_pa_ref":   cagr_ref,
        "performance_pa_bench": cagr_bench,
        "volatilitaet_ref":     vola_ref,
        "volatilitaet_bench":   vola_bench,
        "sharpe_ref":           sharpe_ref,
        "sharpe_bench":         sharpe_bench,
        "max_drawdown_ref":     mdd_ref,
        "max_drawdown_bench":   mdd_bench,
    }

    # ── PERFORMANCE P.A. (Säulen-Chart, letzte n_years vollständige Jahre) ──
    end_date = df.index.max()
    current_year = end_date.year
    # "Vollständig" = mindestens bis 28.12. Daten vorhanden
    last_full_year = current_year if (end_date.month == 12 and end_date.day >= 28) else current_year - 1
    target_years = list(range(last_full_year - n_years_bar_chart + 1, last_full_year + 1))

    jahre = []
    pa_ref = []
    pa_bench = []
    for year in target_years:
        sub = df[df.index.year == year]
        # Nicht `sub.empty`, sondern "deckt das Jahr ab" (12.08.2026): ein
        # angebrochenes Auflagejahr ist kein Kalenderjahr und darf nicht als
        # Jahresbalken erscheinen. Begründung und Messwerte: _ist_volles_jahr.
        if not _ist_volles_jahr(sub, year):
            continue
        rp_y = sub["ret_port"].fillna(0.0).to_numpy(float)
        ref_year = calc_period_return_after_fee(rp_y, fee_dec)
        jahre.append(year)
        pa_ref.append(ref_year)
        if has_bm:
            rb_y = sub["ret_bm"].fillna(0.0).to_numpy(float)
            pa_bench.append(calc_period_return(rb_y))

    # Ohne Benchmark bleibt die Liste LEER (11.08.2026) — vorher stand hier
    # je Jahr eine 0.0. Die Kennzahlen zeigten dank has_benchmark zwar "–",
    # der Säulen-Chart der Broschüre bekam aber eine Serie aus lauter Nullen
    # und zeichnete Null-Balken neben das Musterdepot (an "Muster SCHWEIZ
    # Substanz" am echten Artefakt reproduziert). Eine leere Liste ist die
    # ehrliche Antwort: es gibt nichts zu zeichnen. Wer die Serie befüllt,
    # prüft has_benchmark — siehe pptx_slides.
    performance_pa = {
        "jahre":    jahre,
        "referenz": pa_ref,
        "benchmark": pa_bench,
    }

    # ── WERTENTWICKLUNG (Linien-Chart, gesamte Zeitreihe) ──
    # Index startet bei 1.0 (=100%) zum Auflagedatum (= erster Tag - 1)
    start_date = df.index.min() - pd.Timedelta(days=1)
    dates = [start_date.date()] + [d.date() for d in df.index]
    wert_ref = list((ia_ref / 100.0).astype(float))
    if has_bm:
        ib_bench_norm = make_index_from_returns(rb, 100.0) / 100.0
        wert_bench = list(ib_bench_norm.astype(float))
    else:
        # Ohne Benchmark leer statt einer Reihe aus lauter 1.0 (11.08.2026) —
        # die hätte im Linien-Chart eine schnurgerade 100-%-Linie gezeichnet.
        wert_bench = []

    wertentwicklung = {
        "dates":     dates,
        "referenz":  wert_ref,
        "benchmark": wert_bench,
    }

    return {
        "has_benchmark":   has_bm,
        "kennzahlen":      kennzahlen,
        "performance_pa":  performance_pa,
        "wertentwicklung": wertentwicklung,
    }
