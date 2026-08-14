"""Pruefstein fuer modules/analytics.py — die zentrale Berechnungsstelle.

analytics.py rechnet fuer BEIDE Konsumenten: die Kennzahlen im Tool und die
Zahlen in der Kundenbroschuere. Bis 12.08.2026 gab es keinen Test, der die
Funktionen einzeln prueft — nur zwei Suiten, die compute_performance_data an
echten Daten mitzogen (test_benchmark_erkennung, test_benchmark_charts).
Die pruefen, ob die 19 echten Strategien sich richtig verhalten; dieser hier
prueft die Bausteine gegen von Hand nachrechenbare Zahlen. Beides wird
gebraucht: Der eine faellt aus, wenn sich die Daten aendern, der andere,
wenn sich die Mathematik aendert.

  1. Bausteine gegen bekannte Werte
  2. Degenerierte Eingaben liefern None statt zu stuerzen
  3. has_benchmark — eine Spalte aus Nullen ist KEINE Benchmark
  4. compute_performance_data haelt seinen Vertrag (Laengen, leere Listen)
  5. analytics.py bleibt frei von Streamlit und python-pptx

Braucht nur numpy und pandas — kein Streamlit, kein python-pptx.

    python tests/test_analytics.py
"""

import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

try:
    import numpy as np
    import pandas as pd
except ImportError as ex:
    print(f"UEBERSPRUNGEN — {ex}")
    sys.exit(0)

from modules.analytics import (  # noqa: E402
    annual_fee_to_daily_drag, annual_to_daily_rate, calc_cagr,
    calc_daily_returns_after_fee, calc_max_drawdown, calc_period_return,
    calc_period_return_after_fee, calc_sharpe_excess, calc_vola,
    compute_performance_data, drawdown_from_index, has_benchmark,
    make_index_after_fee, make_index_from_returns,
)

TOLERANZ = 1e-9


def _nah(bezeichnung, ist, soll, toleranz=TOLERANZ):
    if ist is None:
        print(f"    FEHLER — {bezeichnung}: None statt {soll}")
        return 1
    if abs(float(ist) - float(soll)) <= toleranz:
        print(f"    OK — {bezeichnung} = {float(ist):.10g}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {float(ist):.10g} statt {float(soll):.10g}")
    return 1


def _ist(bezeichnung, ist, soll):
    if ist == soll:
        print(f"    OK — {bezeichnung}: {ist!r}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {ist!r} statt {soll!r}")
    return 1


def schritt1_bausteine():
    print("Schritt 1 — Bausteine gegen von Hand nachrechenbare Werte")
    f = 0

    # Index: +10 %, dann -10 % → 100 → 110 → 99. Der bekannteste Denkfehler
    # der Finanzmathematik (99, nicht 100) ist damit festgenagelt.
    idx = make_index_from_returns([0.10, -0.10], 100.0)
    f += _ist("make_index_from_returns Laenge", len(idx), 3)
    f += _nah("idx[0] (Startwert)", idx[0], 100.0)
    f += _nah("idx[1] nach +10 %", idx[1], 110.0)
    f += _nah("idx[2] nach -10 %", idx[2], 99.0)

    # Geometrische Periodenrendite (Doctest-Wert aus dem Modul)
    # 1,01 × 1,01 × 0,98 = 0,999698. Der Docstring behauptete bis 12.08.2026
    # -0.000198 — der Code war richtig, das Beispiel nicht.
    f += _nah("calc_period_return([0.01, 0.01, -0.02])",
              calc_period_return([0.01, 0.01, -0.02]), -0.000302, 1e-9)
    f += _nah("calc_period_return([]) — leere Periode",
              calc_period_return([]), 0.0)

    # CAGR: aus 100 werden in 365 Tagen 110 → exakt 10 % p.a.
    f += _nah("calc_cagr([100, 110], 365)", calc_cagr([100.0, 110.0], 365), 0.10)
    # Halbes Jahr mit +10 % annualisiert auf (1,1)^2 - 1 = 21 %
    f += _nah("calc_cagr([100, 110], 182.5)",
              calc_cagr([100.0, 110.0], 182.5), 0.21, 1e-9)

    # Volatilitaet: eine konstante Reihe schwankt nicht.
    f += _nah("calc_vola([0.001] * 10)", calc_vola([0.001] * 10), 0.0)
    reihe = [0.01, -0.01, 0.02, -0.02, 0.0]
    f += _nah("calc_vola(reihe) = std(ddof=1) * sqrt(365)",
              calc_vola(reihe), float(np.std(reihe, ddof=1) * np.sqrt(365)))

    # Drawdown: 100 → 120 → 90 heisst -25 % vom Hoechststand, nicht -10 %.
    dd = drawdown_from_index([100.0, 120.0, 90.0])
    f += _nah("drawdown am Hoch", dd[1], 0.0)
    f += _nah("drawdown nach dem Fall", dd[2], -0.25)
    f += _nah("calc_max_drawdown([100, 120, 90])",
              calc_max_drawdown([100.0, 120.0, 90.0]), -0.25)
    # Eine nur steigende Reihe hat keinen Drawdown.
    f += _nah("calc_max_drawdown(steigend)",
              calc_max_drawdown([100.0, 101.0, 102.0]), 0.0)

    # Annualisierter Satz → Tagessatz (Backlog E, 12.08.2026). 365 Tage
    # aufgezinst muessen wieder den Jahressatz ergeben — sonst stimmt die
    # Basis nicht (Kalendertage, nicht Handelstage).
    tag = float(annual_to_daily_rate(0.03))
    f += _nah("annual_to_daily_rate(0.03)", tag, 8.098629905317623e-05, 1e-18)
    f += _nah("365 Tage zurueckgerechnet", (1 + tag) ** 365 - 1, 0.03, 1e-12)
    f += _nah("0 % ergibt 0", float(annual_to_daily_rate(0.0)), 0.0)
    # HIER STAND BIS ZUM AUDIT (14.08.2026) DAS GEGENTEIL:
    #
    #   "Derselbe Wert wie beim Honorar — die Mathematik ist identisch, nur
    #    die Groesse ist eine andere (der eine Satz wird abgezogen, der
    #    andere gutgeschrieben)."
    #
    # In diesem "nur" steckte Audit-Befund B3. Aufzinsen und Abziehen sind
    # NICHT symmetrisch:
    #
    #   Gutschrift (rf):  (1 + d)^365 = 1 + r   ->  d = (1+r)^(1/365) - 1
    #   Belastung (Fee):  (1 - d)^365 = 1 - f   ->  d = 1 - (1-f)^(1/365)
    #
    # Der rf-Tagessatz wird zwar auch subtrahiert (Excess Return), aber er
    # muss sich als ZINS aufzinsen — deshalb bleibt dort (1+r).
    #
    # Die beiden MUESSEN jetzt auseinanderlaufen. Liefen sie wieder gleich,
    # waere die alte Formel zurueck.
    drag_f = annual_fee_to_daily_drag(0.0155)
    rate_f = float(annual_to_daily_rate(0.0155))
    f += _ist("Fee-Drag und rf-Umrechnung sind verschieden",
              drag_f != rate_f, True)
    f += _nah("Fee-Drag 1,55 %", drag_f, 1.0 - (1.0 - 0.0155) ** (1 / 365), 1e-18)
    # Die Zusage der Fee-Formel: 365 Abzuege ergeben exakt den Jahressatz.
    f += _nah("365 Abzuege ergeben den Satz", 1.0 - (1.0 - drag_f) ** 365,
              0.0155, 1e-12)
    # Und die Zusage der rf-Formel bleibt das Aufzinsen (schon oben geprueft).
    f += _nah("rf-Satz zinst sich auf", (1 + rate_f) ** 365 - 1, 0.0155, 1e-12)
    # Reihe statt Einzelwert: der rf kommt als Zeitreihe.
    reihe_tag = annual_to_daily_rate([0.03, 0.0, 0.025])
    f += _ist("Reihe bleibt eine Reihe", len(reihe_tag), 3)
    f += _nah("Reihe[0] == Einzelwert", reihe_tag[0], tag, 0.0)

    # Nach-Kosten-Renditen: jeder Tag traegt denselben Abzug.
    netto = calc_daily_returns_after_fee([0.01, 0.02], 0.0155)
    drag = 1.0 - (1.0 - 0.0155) ** (1 / 365)
    f += _nah("calc_daily_returns_after_fee[0]", netto[0], 0.01 - drag)
    f += _nah("calc_daily_returns_after_fee[1]", netto[1], 0.02 - drag)

    # Konsistenz: Periodenrendite nach Kosten == Index-Endstand nach Kosten.
    # Zwei Wege durch dieselbe Mathematik; laufen sie auseinander, weichen
    # Kennzahlen-Tabelle und Chart der Broschuere voneinander ab.
    r = [0.004, -0.002, 0.001, 0.003, -0.005] * 20
    idx_af = make_index_after_fee(r, 0.0155, 100.0)
    f += _nah("Periodenrendite == Index-Endstand",
              calc_period_return_after_fee(r, 0.0155),
              idx_af[-1] / idx_af[0] - 1.0, 1e-12)
    return f


def schritt2_degeneriert():
    print("Schritt 2 — degenerierte Eingaben liefern None statt zu stuerzen")
    # Warum das zaehlt: Eine Kennzahl, die None ist, zeigt die Oberflaeche als
    # "–" an. Eine Exception dagegen reisst den ganzen Export mit — mitten im
    # Kundentermin.
    f = 0
    f += _ist("calc_cagr([], 365)", calc_cagr([], 365), None)
    f += _ist("calc_cagr([100, 110], 0)", calc_cagr([100.0, 110.0], 0), None)
    f += _ist("calc_cagr([100, 110], -5)", calc_cagr([100.0, 110.0], -5), None)
    f += _ist("calc_cagr mit Startwert 0", calc_cagr([0.0, 110.0], 365), None)
    f += _ist("calc_vola([])", calc_vola([]), None)
    f += _ist("calc_vola([0.01]) — ein Wert schwankt nicht",
              calc_vola([0.01]), None)
    f += _ist("calc_max_drawdown([])", calc_max_drawdown([]), None)
    f += _ist("calc_sharpe_excess mit einem Wert",
              calc_sharpe_excess([0.01], [0.0]), None)
    # Konstante Renditen: numpy laesst eine Reststreuung von ~2e-19 stehen,
    # und mu/sd wurde dadurch bis 12.08.2026 zu 8,4e16 — als "Sharpe Ratio"
    # in einer Kundenbroschuere. Beide Faelle muessen None liefern.
    f += _ist("calc_sharpe_excess ohne Streuung (konstant, ungleich null)",
              calc_sharpe_excess([0.001] * 10, [0.0] * 10), None)
    f += _ist("calc_sharpe_excess ohne Streuung (lauter Nullen)",
              calc_sharpe_excess([0.0] * 10, [0.0] * 10), None)

    # rf kuerzer als die Renditen: wird aufgefuellt, nicht abgebrochen.
    wert = calc_sharpe_excess([0.01, -0.01, 0.02, 0.0], [0.02, 0.02])
    if wert is None:
        print("    FEHLER — kuerzere rf-Reihe liefert None statt eines Wertes")
        f += 1
    else:
        print(f"    OK — kuerzere rf-Reihe wird aufgefuellt: {wert:.6f}")

    # rf laenger: wird abgeschnitten.
    wert2 = calc_sharpe_excess([0.01, -0.01, 0.02, 0.0], [0.02] * 99)
    if wert2 is None:
        print("    FEHLER — laengere rf-Reihe liefert None statt eines Wertes")
        f += 1
    else:
        print(f"    OK — laengere rf-Reihe wird abgeschnitten: {wert2:.6f}")

    # Sharpe ohne risikofreien Zins = mean/std annualisiert.
    r = [0.01, -0.01, 0.02, 0.0, 0.005]
    erwartet = (np.mean(r) / np.std(r, ddof=1)) * np.sqrt(365.0)
    f += _nah("Sharpe bei rf=0", calc_sharpe_excess(r, [0.0] * len(r)),
              erwartet, 1e-9)
    return f


def schritt3_has_benchmark():
    print("Schritt 3 — eine Spalte aus Nullen ist KEINE Benchmark")
    # Der Fehler, der Sharpe -67,48 in eine Kundenbroschuere gebracht hat
    # (07.08.2026). test_benchmark_erkennung prueft das an den 19 echten
    # Strategien, hier steht der Vertrag der Funktion selbst.
    f = 0
    f += _ist("lauter Nullen", has_benchmark(pd.Series([0.0] * 100)), False)
    f += _ist("leere Reihe", has_benchmark(pd.Series([], dtype=float)), False)
    f += _ist("nur NaN", has_benchmark(pd.Series([np.nan] * 10)), False)
    f += _ist("Nullen mit einem echten Wert",
              has_benchmark(pd.Series([0.0] * 99 + [0.004])), True)
    f += _ist("auch ein negativer Wert zaehlt",
              has_benchmark(pd.Series([0.0] * 99 + [-0.004])), True)
    # Wochenenden sind rund 29 % Nullen — das ist normal und darf nicht
    # dazu fuehren, dass eine echte Benchmark verworfen wird.
    wochen = [0.001, 0.002, -0.001, 0.0005, 0.001, 0.0, 0.0] * 20
    f += _ist("echte Reihe mit Wochenend-Nullen",
              has_benchmark(pd.Series(wochen)), True)
    f += _ist("Liste statt Series", has_benchmark([0.0, 0.0, 0.003]), True)
    return f


def _testreihe(mit_benchmark=True, benchmark_nullen=False, mit_rf=True,
               start="2021-01-01", ende="2023-12-31"):
    """Deterministische Zeitreihe — bewusst ohne Zufall, damit der Test
    jedes Mal dieselben Zahlen prueft."""
    idx = pd.date_range(start, ende, freq="D")
    n = len(idx)
    ret_port = np.array([0.0004 * ((i % 7) - 3) + 0.0002 for i in range(n)])
    daten = {"ret_port": ret_port}
    if mit_benchmark:
        if benchmark_nullen:
            # Genau das liefert Infront fuer die SCHWEIZ-Strategien.
            daten["ret_bm"] = np.zeros(n)
        else:
            daten["ret_bm"] = np.array(
                [0.0003 * ((i % 5) - 2) + 0.00015 for i in range(n)])
    if mit_rf:
        daten["rf"] = np.full(n, 0.03)
    return pd.DataFrame(daten, index=idx)


def schritt4_vertrag():
    print("Schritt 4 — compute_performance_data haelt seinen Vertrag")
    f = 0

    # ── Fall A: mit echter Benchmark ───────────────────────────────────
    df = _testreihe()
    e = compute_performance_data(df, 0.0155)
    f += _ist("A has_benchmark", e["has_benchmark"], True)
    pa, we = e["performance_pa"], e["wertentwicklung"]
    f += _ist("A Jahre (volle Kalenderjahre)", pa["jahre"], [2021, 2022, 2023])
    f += _ist("A Laenge referenz == Laenge jahre",
              len(pa["referenz"]), len(pa["jahre"]))
    f += _ist("A Laenge benchmark == Laenge jahre",
              len(pa["benchmark"]), len(pa["jahre"]))
    # Chart-Konsistenz: Datums- und Werteliste MUESSEN gleich lang sein,
    # sonst verschiebt sich die Linie gegen die Zeitachse.
    f += _ist("A Laenge dates == Laenge referenz",
              len(we["dates"]), len(we["referenz"]))
    f += _ist("A Laenge dates == Zeilen + 1", len(we["dates"]), len(df) + 1)
    f += _ist("A Laenge benchmark == Laenge dates",
              len(we["benchmark"]), len(we["dates"]))
    f += _nah("A Wertentwicklung startet bei 1.0", we["referenz"][0], 1.0)
    f += _ist("A erster Datumspunkt = Tag vor dem ersten Datensatz",
              we["dates"][0], (df.index.min() - pd.Timedelta(days=1)).date())
    for k in ("performance_pa_ref", "volatilitaet_ref", "sharpe_ref",
              "max_drawdown_ref", "performance_pa_bench", "volatilitaet_bench",
              "sharpe_bench", "max_drawdown_bench"):
        if e["kennzahlen"].get(k) is None:
            print(f"    FEHLER — A Kennzahl {k} ist None, obwohl alles da ist")
            f += 1
    print("    OK — A alle acht Kennzahlen sind belegt")

    # Jahreswert stimmt mit der Einzelrechnung ueberein.
    jahr = df[df.index.year == 2022]["ret_port"].to_numpy(float)
    f += _nah("A Jahresrendite 2022 == calc_period_return_after_fee",
              pa["referenz"][1], calc_period_return_after_fee(jahr, 0.0155),
              1e-12)

    # ── Fall B: Benchmark-Spalte aus lauter Nullen (SCHWEIZ) ───────────
    print()
    e = compute_performance_data(_testreihe(benchmark_nullen=True), 0.0155)
    f += _ist("B has_benchmark bei Null-Spalte", e["has_benchmark"], False)
    f += _ist("B Saeulen-Chart: benchmark ist LEER",
              e["performance_pa"]["benchmark"], [])
    f += _ist("B Linien-Chart: benchmark ist LEER",
              e["wertentwicklung"]["benchmark"], [])
    for k in ("performance_pa_bench", "volatilitaet_bench", "sharpe_bench",
              "max_drawdown_bench"):
        f += _ist(f"B {k}", e["kennzahlen"][k], None)
    # Die Referenz-Seite darf davon voellig unberuehrt bleiben.
    if e["kennzahlen"]["performance_pa_ref"] is None:
        print("    FEHLER — B die eigene Performance fehlt ebenfalls")
        f += 1
    else:
        print("    OK — B die eigene Performance bleibt unberuehrt")

    # ── Fall C: gar keine Benchmark-Spalte ─────────────────────────────
    print()
    e = compute_performance_data(_testreihe(mit_benchmark=False), 0.0155)
    f += _ist("C has_benchmark ohne Spalte", e["has_benchmark"], False)
    f += _ist("C benchmark-Liste leer", e["wertentwicklung"]["benchmark"], [])

    # ── Fall D: ohne risikofreien Zins gibt es keine Sharpe Ratio ──────
    print()
    e = compute_performance_data(_testreihe(mit_rf=False), 0.0155)
    f += _ist("D sharpe_ref ohne rf", e["kennzahlen"]["sharpe_ref"], None)
    if e["kennzahlen"]["volatilitaet_ref"] is None:
        print("    FEHLER — D ohne rf fehlt auch die Volatilitaet")
        f += 1
    else:
        print("    OK — D Volatilitaet braucht keinen rf")

    # ── Fall E: leerer DataFrame stuerzt nicht ─────────────────────────
    print()
    leer = pd.DataFrame({"ret_port": []},
                        index=pd.DatetimeIndex([], name="Datum"))
    e = compute_performance_data(leer, 0.0155)
    f += _ist("E has_benchmark", e["has_benchmark"], False)
    f += _ist("E kennzahlen", e["kennzahlen"], {})
    f += _ist("E performance_pa", e["performance_pa"], {})
    f += _ist("E wertentwicklung", e["wertentwicklung"], {})

    # ── Fall F: Honorar senkt die ausgewiesene Rendite ─────────────────
    print()
    df = _testreihe()
    ohne = compute_performance_data(df, 0.0)["kennzahlen"]["performance_pa_ref"]
    mit = compute_performance_data(df, 0.0155)["kennzahlen"]["performance_pa_ref"]
    if ohne is None or mit is None:
        print("    FEHLER — F Kennzahl fehlt")
        f += 1
    elif mit >= ohne:
        print(f"    FEHLER — F mit Honorar {mit:.4%} >= ohne {ohne:.4%}")
        f += 1
    else:
        # "->" statt "→": U+2192 gibt es in cp1252 nicht, und die Windows-
        # Konsole schreibt in cp1252. Die Suite ist daran mit
        # UnicodeEncodeError ABGEBROCHEN, statt ihr Ergebnis zu melden —
        # ausgerechnet in der letzten Zeile des letzten bestandenen Schritts
        # (12.08.2026). Andere Sonderzeichen (—, ≤) sind in cp1252 enthalten
        # und deshalb unauffaellig; Pfeile sind es nicht.
        print(f"    OK — F Honorar kostet Rendite: {ohne:.4%} -> {mit:.4%}")
    return f


def schritt5_streamlitfrei():
    print("Schritt 5 — analytics.py bleibt frei von Streamlit und python-pptx")
    pfad = os.path.join("modules", "analytics.py")
    with open(pfad, encoding="utf-8") as fh:
        zeilen = [z.strip() for z in fh
                  if z.strip().startswith(("import ", "from "))]
    verboten = [z for z in zeilen if "streamlit" in z or "pptx" in z]
    if verboten:
        print("    FEHLER — verbotene Importe:")
        for z in verboten:
            print(f"      ! {z}")
        print("    Beide Konsumenten brauchen analytics — auch der Batch ohne UI.")
        return 1
    print(f"    OK — {len(zeilen)} Import(e): {', '.join(zeilen)}")
    return 0


def schritt6_umrechnung_nur_einmal():
    print("Schritt 6 — die 365-Umrechnung steht nur in analytics.py")
    # Backlog E (12.08.2026): `(1 + x) ** (1/365) - 1` stand an vier Stellen
    # — zweimal in analytics.py und zweimal in streamlit_app.py. Formelgleich
    # und damit dasselbe Risiko wie bei der Honorar-Mathematik: Eine
    # Korrektur haette die anderen drei nicht erreicht.
    import re
    muster = re.compile(r"\*\*\s*\(?\s*1(\.0)?\s*/\s*365")
    erlaubt = os.path.join("modules", "analytics.py")

    dateien = [os.path.join("streamlit_app.py")]
    for name in sorted(os.listdir("modules")):
        if name.endswith(".py"):
            dateien.append(os.path.join("modules", name))

    treffer = []
    in_erlaubter_datei = 0
    for pfad in dateien:
        with open(pfad, encoding="utf-8") as fh:
            for nr, zeile in enumerate(fh, start=1):
                if zeile.lstrip().startswith("#") or not muster.search(zeile):
                    continue
                if os.path.normpath(pfad) == os.path.normpath(erlaubt):
                    in_erlaubter_datei += 1
                else:
                    treffer.append(f"{pfad}:{nr}: {zeile.strip()}")

    # SEIT DEM AUDIT (14.08.2026) SIND ES ZWEI, und das ist richtig so:
    #   annual_to_daily_rate      (1 + r)^(1/365) - 1   Gutschrift, rf
    #   annual_fee_to_daily_drag  1 - (1 - f)^(1/365)   Belastung, Honorar
    # Vorher delegierte die zweite an die erste - genau darin steckte
    # Befund B3. Es sind zwei verschiedene Fragen, also zwei Formeln.
    # Entscheidend bleibt, dass BEIDE nur hier stehen: Der Wert unten
    # ("treffer") muss leer sein.
    ERWARTET = 2
    if in_erlaubter_datei != ERWARTET:
        print(f"    FEHLER — in {erlaubt} steht die Umrechnung "
              f"{in_erlaubter_datei}× statt genau {ERWARTET}×")
        return 1
    print(f"    OK — {erlaubt} enthaelt sie genau {ERWARTET}× "
          "(Gutschrift und Belastung, bewusst getrennt)")

    if treffer:
        print(f"    FEHLER — {len(treffer)} weitere Fundstelle(n):")
        for t in treffer:
            print(f"      ! {t}")
        print("    annual_to_daily_rate aus modules/analytics.py benutzen.")
        return 1
    print(f"    OK — keine zweite Fundstelle in {len(dateien)} Dateien")
    return 0


def main():
    print("Pruefstein: modules/analytics.py\n")
    fehler = 0
    for schritt in (schritt1_bausteine, schritt2_degeneriert,
                    schritt3_has_benchmark, schritt4_vertrag,
                    schritt5_streamlitfrei, schritt6_umrechnung_nur_einmal):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — Bausteine, Grenzfaelle und der Vertrag stimmen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
