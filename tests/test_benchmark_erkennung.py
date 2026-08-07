"""Regressionstest: Benchmark-Erkennung (Bugfix 07.08.2026).

Prueft an den ECHTEN CSVs in Daten/, dass
  1. Strategien mit reiner Null-Benchmark ("Haben keine Benchmark" laut
     Mapping_Namen.xlsx Spalte D) KEINE Benchmark-Kennzahlen mehr liefern,
  2. alle uebrigen Strategien ihre Benchmark unveraendert behalten.

Hintergrund: Infront liefert fuer Strategien ohne Vergleichsmassstab keine
leere, sondern eine mit Nullen gefuellte Spalte. Der fruehere Test
notna().any() war dort True — die Broschuere zeigte daraufhin eine flache
0-%-Benchmark samt Kennzahlen (Sharpe -67,48 bei Muster SCHWEIZ Aktien).

BEWUSST ohne pytest und ohne Streamlit, damit er in der eingeschraenkten
Firmenumgebung laeuft. Es genuegen pandas und numpy:

    python tests/test_benchmark_erkennung.py

Rueckgabewert 0 = bestanden, 1 = fehlgeschlagen (fuer spaetere Automatisierung).
"""

import glob
import os
import re
import sys

import pandas as pd

# Projektwurzel in den Suchpfad, egal aus welchem Verzeichnis aufgerufen wird
WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

from modules.analytics import compute_performance_data, has_benchmark  # noqa: E402

DATEN = os.path.join(WURZEL, "Daten")
SPALTE_BM = "Benchmark Performance [%] (Intervall)"

# Diese beiden tragen im Mapping_Namen.xlsx (Spalte D) ausdruecklich
# "Haben keine Benchmark"; ihre CSV-Spalte besteht komplett aus Nullen.
OHNE_BENCHMARK = {"Muster SCHWEIZ Aktien", "Muster SCHWEIZ Substanz"}

# Beliebiger Honorarsatz — fuer die Benchmark-Erkennung ohne Belang.
FEE_TEST = 0.0119


def neuester_tag():
    """Groesster yyMMdd-Tag in den Dateinamen (wie detect_newest_date_tag)."""
    tags = set()
    muster = os.path.join(DATEN, "*.CSV"), os.path.join(DATEN, "*.csv")
    for pfad in {p for m in muster for p in glob.glob(m)}:
        treffer = re.search(r"_(\d{6})_", os.path.basename(pfad))
        if treffer:
            tags.add(treffer.group(1))
    return max(tags) if tags else None


def lade_zeitreihe(pfad):
    """Baut dasselbe DataFrame, das build_portfolio_timeseries erzeugt."""
    vv = pd.read_csv(pfad, comment="#", encoding="ISO-8859-1", delimiter=";",
                     decimal=",", thousands=".", dtype=str)

    def spalte(name):
        if name not in vv.columns:
            return None
        return pd.to_numeric(
            vv.loc[1:, name].astype(str).str.replace(",", "."),
            errors="coerce").to_numpy(dtype=float)

    daten = pd.to_datetime(vv["Datum"], format="%d.%m.%Y")
    df = pd.DataFrame(index=daten.iloc[1:].reset_index(drop=True))
    df.index.name = "Datum"
    df["ret_port"] = spalte("Performance [%] (Intervall)")
    for quelle, ziel in ((SPALTE_BM, "ret_bm"), ("Risiko freier Zins", "rf")):
        werte = spalte(quelle)
        if werte is not None:
            df[ziel] = werte
    return str(vv.loc[0, "Portfolio Name"]).strip(), df


def main():
    tag = neuester_tag()
    if tag is None:
        print(f"FEHLER: keine CSVs in {DATEN} gefunden")
        return 1

    dateien = sorted(glob.glob(os.path.join(DATEN, f"*_{tag}_*.CSV")))
    if not dateien:
        print(f"FEHLER: keine Dateien fuer Tag {tag}")
        return 1

    print(f"Datenstand {tag} — {len(dateien)} Strategien\n")
    kopf = f"{'Strategie':30s} {'erkannt':>8s} {'erwartet':>9s} {'BM p.a.':>9s}  Ergebnis"
    print(kopf)
    print("-" * len(kopf))

    fehler = []
    for pfad in dateien:
        name, df = lade_zeitreihe(pfad)
        erkannt = "ret_bm" in df.columns and has_benchmark(df["ret_bm"])
        erwartet = name not in OHNE_BENCHMARK

        kennzahlen = compute_performance_data(df, FEE_TEST).get("kennzahlen", {})
        bench_pa = kennzahlen.get("performance_pa_bench")

        # Zwei Zusicherungen: die Erkennung stimmt UND die Kennzahlen
        # passen dazu (Benchmark vorhanden <=> Kennzahl vorhanden).
        ok = erkannt == erwartet and (bench_pa is not None) == erwartet
        if not ok:
            fehler.append(name)

        anzeige = "-" if bench_pa is None else f"{bench_pa * 100:.2f}%"
        print(f"{name[:30]:30s} {str(erkannt):>8s} {str(erwartet):>9s} "
              f"{anzeige:>9s}  {'OK' if ok else 'FEHLER'}")

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — falsches Verhalten bei: {', '.join(fehler)}")
        return 1

    ohne = len(OHNE_BENCHMARK)
    print(f"BESTANDEN: alle {len(dateien)} Strategien verhalten sich wie erwartet")
    print(f"  {ohne} ohne Benchmark  -> Kennzahlen None, Folie zeigt '-'")
    print(f"  {len(dateien) - ohne} mit Benchmark   -> unveraendert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
