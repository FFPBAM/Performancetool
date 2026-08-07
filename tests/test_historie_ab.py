"""Prueft den Historien-Beginn je Datenreihe (HISTORIE_AB).

REGEL (festgelegt mit Philip am 07.08.2026):
    Die klassischen cVV-Datenreihen liefern als erste Datenpunkte den
    30.12. und 31.12.2008 — zwei Tage. Daraus "Wertentwicklung seit 2008"
    zu schreiben suggeriert einen Track Record ueber 2008, den es nicht
    gibt. Gerechnet und ausgewiesen wird deshalb ab dem 01.01.2009; der
    31.12.2008 bleibt als Indexbasis (100 %) stehen.

    Der Schluessel ist die DATENREIHE, nicht die Familie: "Offensiv" liegt
    in der Familie Thema, nutzt aber "Muster offensiv cVV" (frueher eine
    cVV-Strategie) und ist genauso betroffen — Pro und Pro Dividende
    derselben Familie dagegen nicht.

Geprueft wird:
  1. jeder HISTORIE_AB-Eintrag existiert wirklich in den Daten
     (faengt Tippfehler und spaetere Umbenennungen durch Infront ab)
  2. konfigurierte Reihen beginnen danach am hinterlegten Datum
  3. alle uebrigen Reihen bleiben unveraendert
  4. die Beschriftung leitet sich korrekt ab: auflage_jahr == 2009

Braucht nur pandas — laeuft ohne Streamlit-Umgebung:

    python tests/test_historie_ab.py
"""

import glob
import os
import re
import sys

import pandas as pd

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

from modules.vorlagen_config import HISTORIE_AB               # noqa: E402

DATEN = os.path.join(WURZEL, "Daten")


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

    reihen = {}
    for pfad in sorted(glob.glob(os.path.join(DATEN, f"*_{tag}_*.CSV"))):
        name, df = _zeitreihe(pfad)
        reihen[name] = df

    fehler = 0

    # ── 1. Konfiguration zeigt auf existierende Reihen ───────────────────
    print("1. Konfigurierte Datenreihen existieren")
    unbekannt = [k for k in HISTORIE_AB if k not in reihen]
    if unbekannt:
        fehler += len(unbekannt)
        print(f"   FEHLER — nicht in den Daten: {', '.join(unbekannt)}")
        print("   (Tippfehler, oder Infront hat die Reihe umbenannt)")
    else:
        print(f"   OK — alle {len(HISTORIE_AB)} Eintraege gefunden")

    # ── 2. + 3. Wirkung je Reihe ─────────────────────────────────────────
    print(f"\n2. Wirkung auf alle {len(reihen)} Datenreihen")
    print(f"   {'Datenreihe':28s} {'vorher':12s} {'nachher':12s} Ergebnis")
    print("   " + "-" * 70)
    for name in sorted(reihen):
        df = reihen[name]
        vorher = df.index.min()
        nachher = historie_beschneiden(df, name).index.min()
        soll_ab = HISTORIE_AB.get(name)
        if soll_ab:
            # Konfiguriert: muss genau am Stichtag beginnen (oder spaeter,
            # falls die Reihe ohnehin erst danach anfaengt)
            erwartet = max(pd.Timestamp(soll_ab), vorher)
        else:
            erwartet = vorher            # unberuehrt
        ok = nachher == erwartet
        if not ok:
            fehler += 1
        marke = "  <- beschnitten" if nachher != vorher else ""
        print(f"   {name[:28]:28s} {str(vorher.date()):12s} "
              f"{str(nachher.date()):12s} {'OK' if ok else 'FEHLER'}{marke}")

    # ── 4. Beschriftung der Wertentwicklungs-Folie ───────────────────────
    print("\n3. Beschriftung leitet sich korrekt ab")
    try:
        from modules.pptx_export import compute_wertentwicklung_data
        for name in ("Muster konservativ cVV", "Muster offensiv cVV"):
            if name not in reihen:
                continue
            df = reihen[name]
            roh = compute_wertentwicklung_data(df, 0.0119)["auflage_jahr"]
            neu = compute_wertentwicklung_data(
                historie_beschneiden(df, name), 0.0119)["auflage_jahr"]
            ok = roh == 2008 and neu == 2009
            if not ok:
                fehler += 1
            print(f"   {name:28s} 'seit {roh}' -> 'seit {neu}'  "
                  f"{'OK' if ok else 'FEHLER'}")
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — konfigurierte Reihen ab 01.01.2009, alle anderen unveraendert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
