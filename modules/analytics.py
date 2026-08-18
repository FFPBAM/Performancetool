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

from modules.vorlagen_config import HISTORIE_AB


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
    """Wandelt einen jährlichen Honorarsatz in die tägliche Belastung.

    Formel: daily = 1 - (1 - fee_pa)^(1/365)

    Die Zusage dieser Formel: Ein Jahr ohne Marktbewegung kostet EXAKT den
    Honorarsatz. Weil der Wert täglich SUBTRAHIERT wird, muss er so gewählt
    sein, dass sich die 365 Abzüge zu genau `fee_pa` multiplizieren:

        (1 - d)^365 = 1 - f      <=>     d = 1 - (1 - f)^(1/365)

    KORRIGIERT AM 14.08.2026 (Audit-Befund B3). Vorher stand hier
    `(1 + f)^(1/365) - 1` — dieselbe Umrechnung wie beim risikofreien Zins,
    und genau das war der Fehler: `annual_to_daily_rate` beantwortet die
    Frage „welcher Tagessatz wächst über 365 Tage auf 1 + f?" und passt
    damit zu einer GUTSCHRIFT, die aufgezinst wird. Das Honorar wird
    abgezogen. Aufzinsen und Abziehen sind nicht symmetrisch, deshalb kam
    zu wenig heraus:

        Satz p.a.   d (alt)       effektiv alt   d (neu)       effektiv neu
        0,85 %      2,31895e-05      0,8429 %    2,33869e-05      0,8500 %
        1,20 %      3,26816e-05      1,1858 %    3,30750e-05      1,2000 %
        1,25 %      3,40349e-05      1,2346 %    3,44618e-05      1,2500 %
        1,40 %      3,80909e-05      1,3807 %    3,86264e-05      1,4000 %
        1,55 %      4,21409e-05      1,5264 %    4,27974e-05      1,5500 %
        1,60 %      4,34896e-05      1,5749 %    4,41891e-05      1,6000 %

    Das sind alle sechs im Bestand vorkommenden Sätze; die Spalte „effektiv
    neu" trifft jeden davon auf die vierte Nachkommastelle genau — das ist
    die Zusage von oben, nachgerechnet.

    Über 17 Jahre summiert sich der Unterschied bei 1,55 % auf 31,3
    Basispunkte (kumuliertes Honorar 23,010 % alt gegen 23,323 % neu) —
    klein, aber systematisch und immer zugunsten des Hauses. Genau deshalb
    war es nicht aufgefallen.

    Args:
        fee_pa_decimal: Honorarsatz p.a. als Dezimal (z.B. 0.012 für 1,2 %)

    Returns:
        Tägliche Belastung als Dezimal.

    Raises:
        ValueError: bei einem Satz von 100 % p.a. oder mehr — dort ist die
            Formel nicht definiert. Über die Oberfläche unerreichbar (das
            Eingabefeld deckelt bei 20 %), aber ein stiller Ersatzwert wäre
            hier genau die Tarnung, die Befund B6 ausgelöst hat (#57).

    Examples:
        >>> round(annual_fee_to_daily_drag(0.012), 12)
        3.3075018e-05

    Prüfstein: tests/test_kosten_mathematik.py
    """
    f = float(fee_pa_decimal)
    if f >= 1.0:
        raise ValueError(
            f"Honorarsatz {f:.4f} (= {f * 100:.2f} % p.a.) ist nicht "
            "darstellbar: Ab 100 % p.a. bliebe kein Vermögen übrig.")
    return float(1.0 - (1.0 - f) ** (1.0 / 365.0))


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

    √365 und nicht √252, weil die Reihen KALENDERTÄGLICH und lückenlos sind:
    Am Wochenende läuft die Kuponabgrenzung des Anleihenteils weiter, die
    Zeilen sind also keine leeren Platzhalter. Die Herleitung samt Messung
    steht bei `ROLL_FENSTER_TAGE`. Dies hier ist die EINZIGE Stelle im
    Projekt, an der √365 überhaupt gerechnet wird — wer die Konvention
    ändern will, ändert sie hier und nirgends sonst.
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


# ─────────────────────────────────────────────────────────────────────────────
# Historien-Beginn
# ─────────────────────────────────────────────────────────────────────────────

def historie_beschneiden(ts_df, csv_name):
    """Beschneidet eine Performance-Zeitreihe auf ihren Historien-Beginn
    (Konfiguration in HISTORIE_AB).

    Hintergrund: Die klassischen cVV-Datenreihen liefern als erste
    Datenpunkte den 30.12. und 31.12.2008 — zwei Tage. Ungefiltert schrieb
    die Broschüre daraus "Wertentwicklung seit 2008 kumuliert" und
    suggerierte einen Track Record über 2008, den es nicht gibt. Fachlich
    beginnt er am 01.01.2009; der 31.12.2008 ist nur der Schlussstand, auf
    den indexiert wird.

    Der Schlüssel ist der CSV-PORTFOLIONAME, nicht die Familie: "Offensiv"
    liegt in der Familie Thema, nutzt aber die Reihe "Muster offensiv cVV"
    (früher eine cVV-Strategie) und ist deshalb genauso betroffen — während
    Pro und Pro Dividende derselben Familie es nicht sind.

    HIERHER VERSCHOBEN 14.08.2026 (vorher `portfolioanalyse.py`): Die Regel
    griff nur im Broschüren-Export, weil sie in einem Streamlit-Modul lag.
    Die Monatsrenditen-Heatmap braucht sie ebenfalls — ohne sie stünde bei
    den fünf cVV-Strategien eine Zelle "Dez 2008" mit genau EINEM Tag
    (gemessen 14.08.2026: +0,13 / +0,16 / +0,27 / +0,30 / −0,01 %). Eine
    Regel, die nur an einem von zwei Orten greift, ist dieselbe Krankheit
    wie eine Formel, die zweimal existiert.

    Args:
        ts_df: Zeitreihe mit Datums-Index (oder None)
        csv_name: CSV-Portfolioname, z.B. "Muster offensiv cVV"

    Returns:
        Die beschnittene Zeitreihe — oder das Original, wenn die Reihe
        keinen Eintrag hat, kein Index vorliegt oder nach dem Beschneiden
        nichts übrig bliebe.
    """
    ab = HISTORIE_AB.get(csv_name or "")
    if not ab or ts_df is None or len(ts_df) == 0:
        return ts_df
    gekuerzt = ts_df.loc[ts_df.index >= pd.Timestamp(ab)]
    return gekuerzt if len(gekuerzt) else ts_df


# ─────────────────────────────────────────────────────────────────────────────
# Monatsrenditen (Heatmap)
# ─────────────────────────────────────────────────────────────────────────────

MONAT_RAND_TOLERANZ_TAGE = 3
"""Wieviele Tage an JEDEM Rand eines Kalendermonats fehlen dürfen, damit er
noch als vollständig gilt (14.08.2026).

Dasselbe Maß und derselbe Grund wie bei `JAHR_RAND_TOLERANZ_TAGE`: Feiertage
verschieben den ersten und letzten Kurs eines Monats. Die Performance-CSVs
sind zwar kalendertäglich und lückenlos (Wochenenden tragen Rendite 0), aber
die Toleranz kostet nichts und fängt eine künftige Lieferung ab, die nur
Handelstage führt.

Drei Tage sind bei einem Monat verhältnismäßig mehr als bei einem Jahr. Das
ist beabsichtigt: Ein Monat, dem mehr als drei Tage an einem Rand fehlen,
ist kein Monat mehr — gemessen am 14.08.2026 liegen die echten Auflagemonate
allesamt deutlich darüber (9 bis 26 fehlende Tage)."""


def _ist_voller_monat(sub: pd.DataFrame, jahr: int, monat: int) -> bool:
    """Deckt `sub` (die Zeilen EINES Kalendermonats) den Monat wirklich ab?

    Der Zwilling zu `_ist_volles_jahr`, eine Ebene feiner — und aus demselben
    Anlass. Eine Zelle der Monatsrenditen-Heatmap behauptet eine
    MONATSrendite. Ohne diese Prüfung stünde dort der Auflagemonat als
    vollwertiger Monat: "Muster FFPB Pro Dividende" hätte für 10/2024 zehn
    Tage (−2,25 %) neben echten Monaten gezeigt, die comdirect-Familie
    zwanzig Tage für 03/2024. Und der LAUFENDE Monat ist immer angebrochen —
    bei "Muster FFPB Pro" stand am Datenstand 21.07.2026 ein 21-Tage-Wert von
    −7,54 %, der ungekennzeichnet wie ein voller Monat ausgesehen hätte.

    Das ist Transferwissen #51 ("Es gibt Daten" ist nicht "der Zeitraum ist
    abgedeckt"), angewandt auf Monate statt auf Jahre.

    Geprüft werden BEIDE Ränder und zwar aus `sub` selbst — so greift die
    Regel auch bei einem Loch mitten in der Historie, nicht nur am Anfang
    und Ende der Reihe.

    Prüfstein: tests/test_monatsrenditen.py
    """
    if sub.empty:
        return False
    tol = pd.Timedelta(days=MONAT_RAND_TOLERANZ_TAGE)
    anfang = pd.Timestamp(jahr, monat, 1)
    ende = anfang + pd.offsets.MonthEnd(0)
    beginnt_rechtzeitig = sub.index.min() <= anfang + tol
    endet_rechtzeitig = sub.index.max() >= ende - tol
    return bool(beginnt_rechtzeitig and endet_rechtzeitig)


def _leere_monatsmatrix() -> dict:
    """Die Rückgabeform von `monatsrenditen` ohne einen einzigen Datenpunkt."""
    spalten = list(range(1, 13))
    return {
        "renditen":          pd.DataFrame(columns=spalten, dtype=float),
        "vollstaendig":      pd.DataFrame(columns=spalten, dtype=bool),
        "jahr":              pd.Series(dtype=float),
        "jahr_vollstaendig": pd.Series(dtype=bool),
    }


def monatsrenditen(timeseries_df: pd.DataFrame,
                   fee_dec: float = 0.0,
                   spalte: str = "ret_port",
                   nach_kosten: bool = True) -> dict:
    """Monatsrenditen einer Zeitreihe als Jahre-×-Monate-Matrix.

    Args:
        timeseries_df: Zeitreihe mit Datums-Index (Spalten ret_port/ret_bm)
        fee_dec: Honorarsatz p.a. als Dezimal — nur wirksam bei nach_kosten
        spalte: "ret_port" (Strategie) oder "ret_bm" (Benchmark)
        nach_kosten: True für die Strategie, False für die Benchmark.
            Die Benchmark läuft IMMER brutto — sie trägt kein Honorar.

    Returns:
        dict mit
          "renditen":          DataFrame, index=Jahre, columns=1..12, Dezimal
          "vollstaendig":      DataFrame gleicher Form, bool
          "jahr":              Series je Jahr, Dezimal
          "jahr_vollstaendig": Series je Jahr, bool

    Ein Monat ohne Daten bleibt `NaN` und wird NIEMALS zu `0.0` — sonst
    sähe eine Lücke wie ein Nullmonat aus (Transferwissen #46). Aus
    demselben Grund liefert ein Monat, dessen Werte allesamt fehlen (etwa
    `ret_bm` ohne Benchmark), `NaN` statt der 0,0, die `np.prod` über lauter
    Nullen ergäbe.

    Der JAHRESWERT wird direkt über alle Tage des Kalenderjahrs gerechnet,
    nicht aus den Monatswerten verkettet. Beides ist geometrisch identisch,
    solange alle vorhandenen Monate gezeigt werden — und genau das tut die
    Heatmap (angebrochene eingeschlossen, gekennzeichnet). Die Zeile stimmt
    damit rechnerisch mit ihrer Jahresspalte überein.
    """
    if (timeseries_df is None or len(timeseries_df) == 0
            or spalte not in timeseries_df.columns):
        return _leere_monatsmatrix()

    df = timeseries_df.sort_index()
    jahre = sorted({int(j) for j in df.index.year})
    spalten = list(range(1, 13))
    renditen = pd.DataFrame(np.nan, index=jahre, columns=spalten, dtype=float)
    vollstaendig = pd.DataFrame(False, index=jahre, columns=spalten, dtype=bool)

    def _wert(reihe: pd.Series) -> Optional[float]:
        if reihe.isna().all():
            return None
        arr = reihe.fillna(0.0).to_numpy(dtype=float)
        return (calc_period_return_after_fee(arr, fee_dec) if nach_kosten
                else calc_period_return(arr))

    for (jahr, monat), sub in df.groupby([df.index.year, df.index.month]):
        jahr, monat = int(jahr), int(monat)
        wert = _wert(sub[spalte])
        if wert is not None:
            renditen.loc[jahr, monat] = wert
        vollstaendig.loc[jahr, monat] = _ist_voller_monat(sub, jahr, monat)

    jahr_wert = pd.Series(np.nan, index=jahre, dtype=float)
    jahr_voll = pd.Series(False, index=jahre, dtype=bool)
    for jahr, sub in df.groupby(df.index.year):
        jahr = int(jahr)
        wert = _wert(sub[spalte])
        if wert is not None:
            jahr_wert.loc[jahr] = wert
        jahr_voll.loc[jahr] = _ist_volles_jahr(sub, jahr)

    return {
        "renditen":          renditen,
        "vollstaendig":      vollstaendig,
        "jahr":              jahr_wert,
        "jahr_vollstaendig": jahr_voll,
    }


def monatsrenditen_differenz(a: dict, b: dict) -> dict:
    """Geometrische Monatsdifferenz zweier Matrizen: (1+a)/(1+b) − 1.

    GEOMETRISCH und nicht arithmetisch (Festlegung Philip, 14.08.2026):
    Nur so verketten sich die zwölf Monatswerte einer Zeile EXAKT zur
    Jahres-Überrendite in der Jahresspalte. Beispiel — zwei Monate,
    Strategie je +10 %, Benchmark je +5 %:

        geometrisch   1,10/1,05 − 1 = +4,76 % je Monat
                      1,0476² − 1   = +9,75 %   = 1,21/1,1025 − 1   stimmt
        arithmetisch  10,00 − 5,00  = +5,00 PP je Monat
                      Summe         = +10,00 PP ≠ +9,75 %           passt nicht

    Gerechnet wird NUR, wo beide Monate vollständig sind. Das ist der
    Unterschied zur absoluten Heatmap, und er ist Absicht: Ein angebrochener
    Monat ist für sich eine wahre Aussage über seine Tage — die Differenz
    eines vollen gegen einen angebrochenen Monat ist eine falsche. Damit
    entfällt beim Vergleich zweier Strategien automatisch der Bereich, in
    dem die jüngere noch nicht lief.

    Der JAHRESWERT ist hier die Verkettung der gültigen Monatsdifferenzen
    und wird NICHT direkt gerechnet — sonst widerspräche die Jahresspalte
    ihrer eigenen Zeile, sobald ein Monat entfallen ist.
    """
    ra, rb = a["renditen"], b["renditen"]
    if ra.empty or rb.empty:
        return _leere_monatsmatrix()

    jahre = sorted(set(ra.index) & set(rb.index))
    if not jahre:
        return _leere_monatsmatrix()

    spalten = list(range(1, 13))
    ra = ra.loc[jahre, spalten]
    rb = rb.loc[jahre, spalten]
    gueltig = (a["vollstaendig"].loc[jahre, spalten]
               & b["vollstaendig"].loc[jahre, spalten]
               & ra.notna() & rb.notna())

    nenner = 1.0 + rb
    # Eine Benchmark-Monatsrendite von exakt −100 % kommt nicht vor, wuerde
    # hier aber durch null teilen. Lieber ein Fehlwert als eine Unendlichkeit.
    gueltig = gueltig & (nenner.abs() > 1e-12)
    diff = ((1.0 + ra) / nenner - 1.0).where(gueltig)

    jahr_wert = pd.Series(np.nan, index=jahre, dtype=float)
    jahr_voll = pd.Series(False, index=jahre, dtype=bool)
    for jahr in jahre:
        zeile = diff.loc[jahr].dropna()
        if zeile.empty:
            continue
        jahr_wert.loc[jahr] = float(np.prod(1.0 + zeile.to_numpy(dtype=float)) - 1.0)
        jahr_voll.loc[jahr] = bool(len(zeile) == 12)

    return {
        "renditen":          diff,
        "vollstaendig":      gueltig,
        "jahr":              jahr_wert,
        "jahr_vollstaendig": jahr_voll,
    }


def monats_durchschnitt(daten: dict, nur_jahre=None) -> dict:
    """Geometrisches Mittel je Kalendermonat über die VOLLSTÄNDIGEN Jahre.

    Beantwortet die Frage, die eine Monats-Heatmap unweigerlich auslöst:
    „Ist der September historisch schwach?"

    Args:
        daten: Rückgabe von `monatsrenditen` oder `monatsrenditen_differenz`
        nur_jahre: optionale Einschränkung auf bestimmte Jahre — für die
            Mittel-Zeile der Bandbreiten-Ansicht, die nur ihr Fenster
            mitteln darf. Die Liste kann die Auswahl nur VERKLEINERN, nie
            erweitern: Unvollständige Jahre bleiben auch dann draußen, wenn
            sie hier aufgeführt sind. Sonst ließe sich die Zusage unten
            (Zeile verkettet sich zur Jahresspalte) von außen aushebeln.

    Returns:
        dict mit
          "monate": Series, index=1..12, Dezimal (leer, wenn kein volles Jahr)
          "jahr":   float oder None — das durchschnittliche Kalenderjahr
          "jahre":  Liste der einbezogenen Jahre

    WARUM NUR VOLLSTÄNDIGE KALENDERJAHRE, und warum geometrisch: Aus beidem
    zusammen folgt eine Eigenschaft, die diese Zeile erst brauchbar macht —
    sie verkettet sich exakt zu ihrer eigenen Jahresspalte, genau wie jede
    andere Zeile der Matrix.

        Ø_m = (Π_y (1 + r_{y,m}))^(1/N) − 1

        Π_m (1 + Ø_m) = (Π_y Π_m (1 + r_{y,m}))^(1/N)
                      = (Π_y (1 + R_y))^(1/N)
                      = 1 + Ø_Jahr

    Der Beweis hängt daran, dass für ALLE ZWÖLF Monate dieselbe Jahresmenge
    zugrunde liegt. Nimmt man angebrochene Jahre hinzu, hat der Januar
    plötzlich mehr Beobachtungen als der Dezember, die Umformung bricht, und
    die Zeile widerspräche ihrer Summenspalte. Deshalb die Beschränkung.

    Bleibt kein vollständiges Kalenderjahr übrig, ist die Rückgabe leer und
    die Zeile entfällt in der Darstellung — kein Durchschnitt ist besser als
    ein Durchschnitt aus einem halben Jahr.
    """
    leer = {"monate": pd.Series(dtype=float), "jahr": None, "jahre": []}
    renditen, vollstaendig = daten["renditen"], daten["vollstaendig"]
    if renditen.empty:
        return leer

    volle = [int(j) for j in renditen.index
             if bool(daten["jahr_vollstaendig"].loc[j])]
    if not volle:
        return leer

    # Sicherheitsnetz: In einem als vollstaendig geltenden Kalenderjahr muss
    # jeder der zwoelf Monate vorhanden UND vollstaendig sein. Sonst waere die
    # Jahresmenge je Monat doch verschieden.
    volle = [j for j in volle
             if bool(vollstaendig.loc[j].all())
             and bool(renditen.loc[j].notna().all())]
    if nur_jahre is not None:
        erlaubt = {int(j) for j in nur_jahre}
        volle = [j for j in volle if j in erlaubt]
    if not volle:
        return leer

    n = len(volle)
    monate = pd.Series(np.nan, index=list(range(1, 13)), dtype=float)
    for monat in range(1, 13):
        werte = renditen.loc[volle, monat].to_numpy(dtype=float)
        wachstum = float(np.prod(1.0 + werte))
        if wachstum <= 0:
            continue
        monate.loc[monat] = wachstum ** (1.0 / n) - 1.0

    jahres_werte = daten["jahr"].loc[volle].to_numpy(dtype=float)
    wachstum_jahr = float(np.prod(1.0 + jahres_werte))
    jahr = wachstum_jahr ** (1.0 / n) - 1.0 if wachstum_jahr > 0 else None

    return {"monate": monate, "jahr": jahr, "jahre": volle}


BAND_JAHRE = 5
"""Länge des Vergleichsfensters der Bandbreiten-Ansicht in Kalenderjahren.

FEST und ausdrücklich NICHT an die Zeitraum-Schnellwahl gekoppelt
(Festlegung Philip, 14.08.2026): Die Zeilen heißen „5J Hoch/Mittel/Tief",
und eine Beschriftung, die eine Zahl behauptet, muss sie halten können. Die
Vorlage aus Bloomberg („5 Yr High") arbeitet ebenfalls mit einem festen
Fenster."""

BAND_DUENN_UNTER = 3
"""Ab wieviel Vergleichsjahren die Bandbreite ohne Vorbehalt trägt.

Darunter wird trotzdem gerechnet — mit dem, was da ist, und ehrlich
beschriftet (bei einem Jahr heißt die Zeile „1J Hoch"). Es erscheint aber ein
Hinweis: Bei einem einzigen Jahr sind Hoch, Mittel und Tief dieselbe Zahl,
bei zweien ist die Spanne der Abstand von genau zwei Beobachtungen.

Betroffen sind heute "Comdirect 100/70/30" und "Muster FFPB Pro Dividende"
(Auflage 2024, nur 2025 ist ein abgeschlossenes Vergleichsjahr)."""


def _leere_bandbreite() -> dict:
    spalten = list(range(1, 13))
    leer_f = pd.Series(np.nan, index=spalten, dtype=float)
    leer_o = pd.Series([None] * 12, index=spalten, dtype=object)
    return {
        "hoch":           leer_f.copy(),
        "mittel":         leer_f.copy(),
        "tief":           leer_f.copy(),
        "anzahl":         pd.Series(0, index=spalten, dtype=int),
        "hoch_wann":      leer_o.copy(),
        "tief_wann":      leer_o.copy(),
        "mittel_geo":     leer_f.copy(),
        "trefferquote":   leer_f.copy(),
        "jahre":          [],
        "aktuelles_jahr": None,
    }


def bandbreite(daten: dict, band_jahre: int = BAND_JAHRE) -> dict:
    """Hoch, Mittel und Tief je Kalendermonat über ein festes Jahresfenster.

    Die Saisonalitäts-Ansicht nach Bloomberg-Vorbild (dort „SEAG"): Statt
    jedes Jahr als eigene Zeile zeigt sie das historische Band je Monat und
    darunter das laufende Jahr. Sie beantwortet eine andere Frage als die
    Jahr-für-Jahr-Matrix — nicht „wie lief jeder Monat?", sondern „ist der
    laufende März ungewöhnlich, gemessen an allen bisherigen Märzen?".

    Args:
        daten: Rückgabe von `monatsrenditen` oder `monatsrenditen_differenz`
        band_jahre: Länge des Fensters; Vorgabe `BAND_JAHRE`

    Returns:
        dict mit "hoch"/"mittel"/"tief" (Series 1..12, Dezimal), "anzahl"
        (Beobachtungen je Monat), "hoch_wann"/"tief_wann" (das Jahr des
        Extrems), "mittel_geo" (das geometrische Mittel zum Vergleich),
        "trefferquote", "jahre" und "aktuelles_jahr".

    DAS LAUFENDE JAHR GEHÖRT NICHT IN SEIN EIGENES BAND. Bloombergs „5 Yr"
    meint die fünf Jahre DAVOR. Die unterste Zeile der Darstellung ist das
    jüngste Jahr der Matrix; das Band bildet sich aus den letzten
    `band_jahre` Kalenderjahren STRIKT davor. Bei Datenstand 07/2026 also
    Band 2021–2025 und Zeile 2026 — nicht 2022–2026. Sonst vergliche sich das
    Jahr mit sich selbst und zöge sein eigenes Hoch oder Tief mit: Ein
    Rekordmonat läge per Definition nie „über dem Hoch", weil er das Hoch
    selbst wäre. (Transferwissen #53)

    ARITHMETISCHES MITTEL, Summe durch Anzahl gültiger Werte (Festlegung
    Philip, 14.08.2026, und die Konvention bei Bloomberg wie TradingView).
    Bis dahin wurde geometrisch gemittelt — das war nötig, solange die
    Ansicht eine „Jahr"-Spalte hatte, zu der sich die Zeile verketten musste.
    Diese Spalte gibt es hier nicht mehr, also fällt der Grund weg. Das
    geometrische Mittel wird als "mittel_geo" mitgeliefert, damit der Hover
    beide nennen kann: Die Ø-Zeile der anderen Ansicht rechnet weiterhin
    geometrisch, und ein unerklärter Unterschied zwischen zwei Ansichten
    desselben Werkzeugs wäre schlimmer als eine Zahl mehr im Hover.

    JE MONAT TOLERANT: Jeder Kalendermonat rechnet mit den Werten, die er
    hat. Fehlt ein einzelner März, rechnet März mit den übrigen Jahren
    weiter, statt die ganze Spalte fallen zu lassen. Auch das kam mit dem
    Wegfall der Jahresspalte: Vorher mussten alle zwölf Monate dieselbe
    Jahresmenge haben, damit die Verkettung aufging.

    Was NICHT tolerant ist: Ein **angebrochener** Monat geht nicht ein. Ein
    Zwanzig-Tage-März ist kein Märzwert, und als Extremwert wäre er
    irreführend — dieselbe Regel wie überall sonst (#51).
    """
    renditen, vollstaendig = daten["renditen"], daten["vollstaendig"]
    if renditen.empty:
        return _leere_bandbreite()

    alle = sorted(int(j) for j in renditen.index)
    aktuell = alle[-1]

    # Die letzten `band_jahre` Kalenderjahre STRIKT vor dem laufenden. Ein
    # Jahr muss hier NICHT vollstaendig sein - es genuegt, dass es einzelne
    # vollstaendige Monate beisteuert.
    fenster = [j for j in alle if j < aktuell][-int(band_jahre):]
    if not fenster:
        return _leere_bandbreite()

    spalten = list(range(1, 13))
    hoch = pd.Series(np.nan, index=spalten, dtype=float)
    tief = pd.Series(np.nan, index=spalten, dtype=float)
    mittel = pd.Series(np.nan, index=spalten, dtype=float)
    mittel_geo = pd.Series(np.nan, index=spalten, dtype=float)
    anzahl = pd.Series(0, index=spalten, dtype=int)
    hoch_wann = pd.Series([None] * 12, index=spalten, dtype=object)
    tief_wann = pd.Series([None] * 12, index=spalten, dtype=object)
    treffer = pd.Series(np.nan, index=spalten, dtype=float)

    for monat in spalten:
        gueltig = [j for j in fenster
                   if bool(vollstaendig.loc[j, monat])
                   and pd.notna(renditen.loc[j, monat])]
        if not gueltig:
            continue
        werte = renditen.loc[gueltig, monat].astype(float)
        anzahl.loc[monat] = len(werte)
        hoch.loc[monat] = float(werte.max())
        tief.loc[monat] = float(werte.min())
        hoch_wann.loc[monat] = int(werte.idxmax())
        tief_wann.loc[monat] = int(werte.idxmin())
        mittel.loc[monat] = float(werte.mean())
        wachstum = float(np.prod(1.0 + werte.to_numpy()))
        if wachstum > 0:
            mittel_geo.loc[monat] = wachstum ** (1.0 / len(werte)) - 1.0
        treffer.loc[monat] = float((werte > 0).sum()) / float(len(werte))

    # "jahre" nennt die Jahre, die tatsaechlich etwas beigesteuert haben -
    # nicht das nominelle Fenster. Sonst behauptete die Beschriftung "5J",
    # wo nur drei Jahre Werte lieferten.
    beitragend = sorted({int(j) for monat in spalten
                         for j in fenster
                         if bool(vollstaendig.loc[j, monat])
                         and pd.notna(renditen.loc[j, monat])})

    return {
        "hoch":           hoch,
        "mittel":         mittel,
        "tief":           tief,
        "anzahl":         anzahl,
        "hoch_wann":      hoch_wann,
        "tief_wann":      tief_wann,
        "mittel_geo":     mittel_geo,
        "trefferquote":   treffer,
        "jahre":          beitragend,
        "aktuelles_jahr": aktuell,
    }


def heatmap_kennzahlen(daten: dict) -> dict:
    """Kennzahlen über die VOLLSTÄNDIGEN Monate einer Matrix.

    Bewusst nur über vollständige Monate: Ein Zehn-Tage-Monat als
    "schlechtester Monat" wäre irreführend, und er verzerrte den Anteil
    positiver Monate.

    Returns:
        dict mit "anzahl", "positiv", "anteil_positiv", "bester",
        "schlechtester" — die letzten beiden als ((jahr, monat), wert).
        Bei keinem einzigen vollständigen Monat: "anzahl" 0, Rest None.
    """
    r, v = daten["renditen"], daten["vollstaendig"]
    paare = []
    for jahr in r.index:
        for monat in r.columns:
            wert = r.loc[jahr, monat]
            if bool(v.loc[jahr, monat]) and pd.notna(wert):
                paare.append(((int(jahr), int(monat)), float(wert)))

    if not paare:
        return {"anzahl": 0, "positiv": 0, "anteil_positiv": None,
                "bester": None, "schlechtester": None}

    positiv = sum(1 for _, w in paare if w > 0)
    return {
        "anzahl":         len(paare),
        "positiv":        positiv,
        "anteil_positiv": positiv / len(paare),
        "bester":         max(paare, key=lambda p: p[1]),
        "schlechtester":  min(paare, key=lambda p: p[1]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Risiko: rollierende Volatilität, Kennzahlen je Zeitraum, Tracking Error
# ─────────────────────────────────────────────────────────────────────────────

ROLL_FENSTER_TAGE = 365
"""Fensterbreite der rollierenden Kennzahlen in ZEILEN (14.08.2026).

Die Performance-CSVs sind kalendertäglich und lückenlos — nachgemessen über
alle 19 Strategien: kein fehlender Tag, kein NaN. 365 Zeilen sind deshalb
exakt ein Kalenderjahr; es braucht keine Schätzung über Handelstage, wie sie
ein 252-Tage-Fenster erforderte. Prüfstein: tests/test_risiko.py, Schritt 6
— er hält genau diese Voraussetzung fest.

HIER STAND BIS ZUM AUDIT (14.08.2026) EINE FALSCHE BEGRÜNDUNG: die
Wochenenden trügen Rendite 0, "rund 29 % aller Zeilen", und √365 sei deshalb
eine hingenommene Ungenauigkeit. Gemessen an den echten Daten:

    Anteil exakter Nullen in ret_port  Median 0,00 %, nur 1 von 19 über 25 %
    Wochenendsatz Comdirect 30/70/100  1,925 % / 0,543 % / 0,000 % p.a.
    Anleihenquote ihrer Benchmark        85 %  /   50 %  /   15 %
    Korrelation Wochenendanteil/Vola   -0,66 (je defensiver, desto mehr)
    Wochenendsatz je negativ?          nie, auch 2015-2022 nicht (rf < 0)

Die Wochenendwerte sind die KUPONABGRENZUNG des Anleihenteils. Deshalb
bleiben sie positiv, wenn der Leitzins es nicht ist, und deshalb ordnen sie
sich nach der Anleihenquote. Nur die 29 % stimmten — das ist der Anteil der
Wochenend-ZEILEN (2/7 = 28,6 %), nicht der Anteil der Nullen.

Damit ist die Reihe eine ECHTE Kalendertagreihe und √365 die dazu passende
Konvention, keine Ungenauigkeit. √252 gehört zu einer Handelstagreihe, die
hier nicht vorliegt. Nebenbei bleibt es dieselbe Basis, auf der `calc_vola`
und die Kennzahlen-Kachel rechnen — zwei verschiedene Volatilitäten auf
einem Bildschirm wären ohnehin nicht vertretbar.

ACHTUNG BEI EINER KÜNFTIGEN LIEFERUNG: Kämen die Daten nur noch für
Handelstage, wäre diese Begründung hinfällig — 365 Zeilen wären dann rund
1,4 Jahre und √365 deutlich zu hoch. Schritt 6 schlägt in dem Fall an.

Für ret_bm gilt die alte Aussage weiter und zu Recht: Der Index steht am
Wochenende still (28,6 bis 30,6 % Nullen, an 100 % der Wochenenden). Siehe
`has_benchmark` — dort ist sie richtig und muss stehen bleiben."""


def rollierende_vola(daily_returns_after_fee: Sequence[float],
                     fenster: int = ROLL_FENSTER_TAGE) -> np.ndarray:
    """Rollierende annualisierte Volatilität, Fenster in Zeilen.

    Formelgleich zu `calc_vola`: std(ddof=1) × √365. Der letzte Wert ist
    damit die Volatilität der letzten `fenster` Tage, und ein Fenster über
    die gesamte Reihe trifft exakt die Kennzahlen-Kachel. Prüfstein:
    tests/test_risiko.py, Schritt 1.

    Returns:
        Array in der Länge der Eingabe. Die ersten `fenster - 1` Werte sind
        NaN (das Fenster ist noch nicht voll) — ist die Reihe kürzer als das
        Fenster, sind es alle. Das ist der ehrliche Zustand und kein Fehler:
        Eine Strategie, die noch kein Jahr läuft, HAT keine Ein-Jahres-Vola.
    """
    arr = np.asarray(daily_returns_after_fee, dtype=float)
    if arr.size == 0:
        return np.array([], dtype=float)
    fenster = max(2, int(fenster))
    reihe = pd.Series(arr).rolling(fenster).std(ddof=1) * np.sqrt(365.0)
    return reihe.to_numpy(dtype=float)


RISIKO_PERIODEN = ("YTD", "1 Jahr", "3 Jahre", "5 Jahre", "10 Jahre", "Seit Auflage")


def _perioden_start(end_ts: pd.Timestamp, bezeichnung: str):
    """Startzeitpunkt einer Periode; None steht für "seit Auflage".

    YTD beginnt am 31.12. des VORJAHRS und nicht am 01.01. — sonst ginge der
    erste Handelstag des Jahres verloren. Dieselbe Konvention wie in
    `build_rolling_table` und `compute_rollierend_data`.
    """
    if bezeichnung == "Seit Auflage":
        return None
    if bezeichnung == "YTD":
        return pd.Timestamp(end_ts.year - 1, 12, 31)
    return end_ts - pd.DateOffset(years=int(bezeichnung.split()[0]))


def risiko_perioden(timeseries_df: pd.DataFrame, fee_dec: float = 0.0) -> pd.DataFrame:
    """Volatilität, Max Drawdown und Sharpe Ratio je Zeitraum.

    EINE Funktion für beide Tabellen der Oberfläche (Risiko-Block und
    Drawdown-Block). Die Aufteilung dort ist reine Darstellung — die
    Rechnung darf nicht zweimal existieren.

    Returns:
        DataFrame, index=RISIKO_PERIODEN, Spalten "rendite" (CAGR nach
        Kosten), "vola", "max_dd", "sharpe", "te" (Tracking Error) und
        "ir" (Information Ratio).
        Die letzten beiden bleiben leer, wenn keine echte Benchmark
        vorliegt — `has_benchmark` entscheidet, nicht `notna` (#41).
        Fehlwert ist durchgehend `np.nan`, nie 0.0 und nie None — die
        Bausteine liefern teils None, teils NaN, und ein Mischmasch aus
        beidem zwingt jede Aufrufstelle zu zwei Abfragen. `pd.isna()` und
        `formats.fmt_pct` behandeln NaN korrekt als Fehlwert.

    Reicht eine Periode weiter zurück als die Historie, bleibt sie
    durchgehend leer — es steht dort NICHT ein still gekürzter Wert. Ein
    "10 Jahre"-Feld, das in Wahrheit zwei Jahre zeigt, ist derselbe Fehler
    wie ein Rumpfjahr als Jahresbalken. Die Grenze ist dieselbe wie in
    `build_rolling_table`: Der Startzeitpunkt muss vom synthetischen
    Indexbeginn (erster Tag minus einen Tag) gedeckt sein.
    """
    spalten = ["rendite", "vola", "max_dd", "sharpe", "te", "ir"]
    ergebnis = pd.DataFrame(np.nan, index=list(RISIKO_PERIODEN),
                            columns=spalten, dtype=float)
    if timeseries_df is None or len(timeseries_df) == 0:
        return ergebnis

    df = timeseries_df.sort_index()
    end_ts = df.index.max()
    indexbeginn = df.index.min() - pd.Timedelta(days=1)
    # EINMAL ueber die ganze Reihe entschieden und nicht je Periode: Eine
    # Strategie hat eine Benchmark oder sie hat keine. Waere die Frage je
    # Periode gestellt, koennte ein Zeitraum ohne Kursbewegung der Benchmark
    # sie fuer diesen Zeitraum "verschwinden" lassen.
    hat_bm = "ret_bm" in df.columns and has_benchmark(df["ret_bm"])

    for bez in RISIKO_PERIODEN:
        start = _perioden_start(end_ts, bez)
        if start is None:
            sub = df
        else:
            if start < indexbeginn:
                continue          # Historie deckt die Periode nicht ab
            sub = df.loc[df.index > start]
        if len(sub) < 2:
            continue

        rp = sub["ret_port"].fillna(0.0).to_numpy(dtype=float)
        netto = calc_daily_returns_after_fee(rp, fee_dec)
        rbm = (sub["ret_bm"].fillna(0.0).to_numpy(dtype=float)
               if hat_bm else None)
        # EINE Indexreihe fuer Rendite UND Drawdown. Zwei getrennte Aufrufe
        # waeren formelgleich - und genau das ist die Gefahr (Backlog B):
        # Wer spaeter den einen anfasst, vergisst den anderen, und die
        # Punktwolke zeigte Rendite und Risiko aus zwei verschiedenen Reihen.
        idx_nach = make_index_after_fee(rp, fee_dec, 100.0)
        werte = {
            # n_days = len(rp), also die ZEILENZAHL - dieselbe Konvention wie
            # in `compute_performance_data`. Sie traegt, weil die Reihen
            # kalendertaeglich und lueckenlos sind; test_risiko Schritt 6
            # misst genau diese Voraussetzung. Eine eigene Konvention hier
            # haette bedeutet, dass die Punktwolke eine andere Rendite zeigt
            # als die Kennzahlen-Kachel derselben Strategie - schlimmer als
            # jede Lehrbuch-Ungenauigkeit (#52).
            "rendite": calc_cagr(idx_nach, len(rp)),
            "vola":   calc_vola(netto),
            "max_dd": calc_max_drawdown(idx_nach),
            "sharpe": (calc_sharpe_excess(netto, sub["rf"])
                       if "rf" in sub.columns and sub["rf"].notna().any() else None),
            "te":     tracking_error(netto, rbm) if hat_bm else None,
            "ir":     information_ratio(netto, rbm) if hat_bm else None,
        }
        for name, wert in werte.items():
            # None der Bausteine auf NaN vereinheitlichen (siehe Docstring)
            if wert is not None:
                ergebnis.loc[bez, name] = float(wert)

    return ergebnis


def _aktivrendite_taeglich(r_port_after_fee: Sequence[float],
                           r_bm: Sequence[float]) -> np.ndarray:
    """Tägliche Aktivrendite, geometrisch: (1+r_p)/(1+r_b) − 1.

    Geometrisch und nicht arithmetisch — dieselbe Definition wie in der
    Differenz-Heatmap, damit Tracking Error und Matrix dieselbe Größe
    beschreiben.
    """
    rp = np.asarray(r_port_after_fee, dtype=float)
    rb = np.asarray(r_bm, dtype=float)
    n = min(rp.size, rb.size)
    if n == 0:
        return np.array([], dtype=float)
    rp, rb = rp[:n], rb[:n]
    nenner = 1.0 + rb
    with np.errstate(divide="ignore", invalid="ignore"):
        aktiv = (1.0 + rp) / nenner - 1.0
    aktiv[np.abs(nenner) < 1e-12] = np.nan
    return aktiv


def tracking_error(r_port_after_fee: Sequence[float],
                   r_bm: Sequence[float]) -> Optional[float]:
    """Annualisierter Tracking Error: std(Aktivrendite, ddof=1) × √365.

    Null ist ein gültiges Ergebnis (die Strategie bildet die Benchmark
    exakt nach) und wird deshalb als 0.0 zurückgegeben, nicht als None.
    Erst die Information Ratio muss damit umgehen.
    """
    aktiv = _aktivrendite_taeglich(r_port_after_fee, r_bm)
    aktiv = aktiv[~np.isnan(aktiv)]
    if aktiv.size < 2:
        return None
    sd = float(np.std(aktiv, ddof=1))
    if not np.isfinite(sd):
        return None
    return sd * np.sqrt(365.0)


def information_ratio(r_port_after_fee: Sequence[float],
                      r_bm: Sequence[float]) -> Optional[float]:
    """Annualisierte Aktivrendite geteilt durch den Tracking Error.

    Der Guard prüft `te < 1e-12` und NICHT `te == 0` — Transferwissen #47.
    Bei zwei praktisch gleichen Reihen lässt numpy eine Reststreuung um
    1e-19 stehen; ein Test auf exakte Null griffe dort nicht und die
    Information Ratio käme als Zahl der Größenordnung 1e16 heraus. Genau
    dieser Fehler stand als Sharpe Ratio schon einmal in einer Broschüre.
    """
    te = tracking_error(r_port_after_fee, r_bm)
    if te is None or te < 1e-12:
        return None
    aktiv = _aktivrendite_taeglich(r_port_after_fee, r_bm)
    aktiv = aktiv[~np.isnan(aktiv)]
    if aktiv.size < 2:
        return None
    wachstum = float(np.prod(1.0 + aktiv))
    if wachstum <= 0:
        return None
    aktiv_pa = wachstum ** (365.0 / aktiv.size) - 1.0
    return aktiv_pa / te
