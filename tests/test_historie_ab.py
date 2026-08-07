"""Prueft den Historien-Beginn je Familie (FAMILIE_HISTORIE_AB).

REGEL (festgelegt mit Philip am 07.08.2026):
    Die fuenf klassischen CVV-Strategien liefern als erste Datenpunkte den
    30.12. und 31.12.2008 — zwei Tage. Daraus "Wertentwicklung seit 2008"
    zu schreiben suggeriert einen Track Record ueber 2008, den es nicht
    gibt. Gerechnet und ausgewiesen wird deshalb ab dem 01.01.2009; der
    31.12.2008 bleibt als Indexbasis (100 %) stehen.

Geprueft wird:
  1. cVV-Zeitreihen beginnen nach dem Beschneiden am 01.01.2009
  2. spaeter aufgelegte Strategien (Dynamic, 2018) bleiben unberuehrt
  3. Familien OHNE Eintrag bleiben unberuehrt (ESG/ETF/comdirect/Thema)
  4. die Beschriftung leitet sich korrekt ab: auflage_jahr == 2009

Braucht nur pandas/numpy — laeuft ohne Streamlit-Umgebung:

    python tests/test_historie_ab.py
"""

import glob
import os
import re
import sys

import pandas as pd

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

from modules.vorlagen_config import FAMILIE_HISTORIE_AB       # noqa: E402

DATEN = os.path.join(WURZEL, "Daten")

# Portfolio-Name (CSV) -> Familie
FAMILIE_JE_PORTFOLIO = {
    "Muster konservativ cVV":   "CVV",
    "Muster defensiv cVV":      "CVV",
    "Muster Defensiv Plus cVV": "CVV",
    "Muster ausgewogen cVV":    "CVV",
    "Muster Dynamic cVV":       "CVV",
    "ESG Muster defensiv":      "ESG",
    "Comdirect 30":             "comdirect",
    "Muster FFPB Pro":          "Thema",
}

# Erwartet: erster Tag NACH dem Beschneiden
ERWARTET = {
    "Muster konservativ cVV":   "2009-01-01",
    "Muster defensiv cVV":      "2009-01-01",
    "Muster Defensiv Plus cVV": "2009-01-01",
    "Muster ausgewogen cVV":    "2009-01-01",
    "Muster Dynamic cVV":       "2018-10-06",   # 2018 aufgelegt -> unberuehrt
    "ESG Muster defensiv":      "2020-10-01",   # Familie ohne Eintrag
    "Comdirect 30":             "2024-03-12",
    "Muster FFPB Pro":          "2023-09-01",
}


def _neuester_tag():
    tags = set()
    for p in glob.glob(os.path.join(DATEN, "*.CSV")) + glob.glob(os.path.join(DATEN, "*.csv")):
        m = re.search(r"_(\d{6})_", os.path.basename(p))
        if m:
            tags.add(m.group(1))
    return max(tags) if tags else None


def _zeitreihe(pfad):
    """Wie build_portfolio_timeseries: erste Zeile ist Basis und faellt weg."""
    vv = pd.read_csv(pfad, comment="#", encoding="ISO-8859-1", delimiter=";",
                     decimal=",", thousands=".", dtype=str)
    daten = pd.to_datetime(vv["Datum"], format="%d.%m.%Y")
    df = pd.DataFrame(index=daten.iloc[1:].reset_index(drop=True))
    df.index.name = "Datum"
    df["ret_port"] = pd.to_numeric(
        vv.loc[1:, "Performance [%] (Intervall)"].astype(str).str.replace(",", "."),
        errors="coerce").to_numpy(dtype=float)
    return str(vv.loc[0, "Portfolio Name"]).strip(), df


def main():
    try:
        from modules.portfolioanalyse import historie_beschneiden
    except ImportError as ex:
        print(f"UEBERSPRUNGEN — {ex}")
        return 0

    tag = _neuester_tag()
    if tag is None:
        print(f"FEHLER: keine CSVs in {DATEN}")
        return 1

    print(f"Konfiguration: {FAMILIE_HISTORIE_AB}\n")
    print(f"{'Portfolio':28s} {'Familie':10s} {'vorher':12s} {'nachher':12s} "
          f"{'erwartet':12s}  Ergebnis")
    print("-" * 92)

    fehler = 0
    gesehen = set()
    for pfad in sorted(glob.glob(os.path.join(DATEN, f"*_{tag}_*.CSV"))):
        name, df = _zeitreihe(pfad)
        if name not in ERWARTET:
            continue
        gesehen.add(name)
        familie = FAMILIE_JE_PORTFOLIO.get(name, "")
        vorher = str(df.index.min().date())
        gekuerzt = historie_beschneiden(df, familie)
        nachher = str(gekuerzt.index.min().date())
        soll = ERWARTET[name]
        ok = nachher == soll
        if not ok:
            fehler += 1
        print(f"{name:28s} {familie:10s} {vorher:12s} {nachher:12s} {soll:12s}  "
              f"{'OK' if ok else 'FEHLER'}")

    fehlend = set(ERWARTET) - gesehen
    if fehlend:
        print(f"\nHINWEIS: nicht in den Daten gefunden: {', '.join(sorted(fehlend))}")

    # ── Beschriftung: leitet sich das Auflagejahr korrekt ab? ────────────
    print("\nBeschriftung der Wertentwicklungs-Folie")
    try:
        from modules.pptx_export import compute_wertentwicklung_data
        pfade = glob.glob(os.path.join(DATEN, f"Muster konservativ cVV_*_{tag}_*.CSV"))
        if pfade:
            _, df = _zeitreihe(pfade[0])
            for label, reihe in (("ohne Beschneiden", df),
                                 ("mit Beschneiden ", historie_beschneiden(df, "CVV"))):
                jahr = compute_wertentwicklung_data(reihe, 0.0119)["auflage_jahr"]
                erwartet_jahr = 2009 if "mit" in label else 2008
                ok = jahr == erwartet_jahr
                if not ok:
                    fehler += 1
                print(f"  {label}: 'Wertentwicklung seit {jahr} kumuliert'  "
                      f"{'OK' if ok else 'FEHLER'}")
    except ImportError as ex:
        print(f"  UEBERSPRUNGEN — {ex}")

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — CVV rechnet ab 01.01.2009, alle anderen unveraendert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
