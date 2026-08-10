"""Prueft die Anlagekriterien-Konfiguration (Mapping_Anlagekriterien.xlsx).

HINTERGRUND (10.08.2026):
    Der Anlagekriterien-Kasten stand bisher NUR statisch in den PPTX-Vorlagen
    — je Familie unterschiedlich geschrieben, mit Tippfehlern ("FPFB Strategie
    30", "AUsgewogen") und uneinheitlicher Prozent-Schreibweise. Er wandert
    jetzt in eine Excel, die BEIDE Ausgaben speist: den Banner im Streamlit-
    Tool und den Kasten auf der Struktur-Folie der Broschuere.

    Weil damit eine einzige Datei bestimmt, was Kunden gedruckt bekommen,
    prueft dieser Test sie streng.

Geprueft wird:
  1. Die Excel existiert und hat die erwarteten Spalten.
  2. Jede Strategie ist im Namens-Mapping bekannt (kein Schluessel ins Leere).
  3. Die Spalte 'Familie' stimmt mit Mapping_Namen.xlsx ueberein — sie ist
     bewusst doppelt gefuehrt (Lesbarkeit in Excel) und wird hier festgenagelt,
     damit sie nicht auseinanderlaeuft.
  4. Genau die 14 Strategien mit Kasten sind erfasst; die Thema-Familie NICHT
     (dort gibt es keinen Kasten — bewusste Entscheidung).
  5. Kein Feld ist leer.
  6. Schreibweisen sind einheitlich: 'mind.' statt 'min.', Prozent mit
     Leerzeichen, kein doppelter Leerraum.
  7. anlagekriterien_fuer() liefert die vier Kriterien in Vorlagen-Reihenfolge
     und [] fuer Strategien ohne Kasten.

    python tests/test_anlagekriterien.py     (braucht pandas + streamlit)
"""

import os
import re
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

import pandas as pd                                            # noqa: E402

EXCEL = os.path.join(WURZEL, "Mapping_Anlagekriterien.xlsx")
NAMEN = os.path.join(WURZEL, "Mapping_Namen.xlsx")

KEY = "Strategie auswählen"
KRITERIEN = ["Anlageregion", "Aktienanteil",
             "Anleihenanteil / Liquidität", "Fremdwährungen"]

# Die 14 Strategien MIT Kasten. Thema (Offensiv, Pro, Pro Dividende, die
# beiden SCHWEIZ-Strategien) hat bewusst keinen.
ERWARTET = [
    "cVV konservativ", "cVV defensiv", "cVV defensiv plus",
    "cVV ausgewogen", "cVV dynamic",
    "ESG defensiv", "ESG defensiv+", "ESG ausgewogen", "ESG offensiv",
    "ETF_ausgewogen", "ETF_Wachstum",
    "Comdirect_30", "Comdirect_70", "Comdirect_100",
]
OHNE_KASTEN = ["Offensiv", "Pro", "Pro Dividende",
               "Schweiz_substanzorientiert", "Schweiz_aktienorientiert"]


def _pruefe_struktur(df):
    print("1. Aufbau der Excel")
    fehler = 0
    soll = [KEY, "Familie", "Anzeigename"] + KRITERIEN
    fehlend = [s for s in soll if s not in df.columns]
    if fehlend:
        print(f"   FEHLER — Spalten fehlen: {fehlend}")
        fehler += 1
    else:
        print(f"   OK — {len(df.columns)} Spalten, {len(df)} Zeilen")
    return fehler


def _pruefe_schluessel(df, namen):
    print("\n2. Jede Strategie ist im Namens-Mapping bekannt")
    fehler = 0
    bekannt = set(namen[KEY].astype(str).str.strip())
    for s in df[KEY].astype(str).str.strip():
        if s not in bekannt:
            print(f"   FEHLER — '{s}' steht nicht in Mapping_Namen.xlsx")
            fehler += 1
    if not fehler:
        print(f"   OK — alle {len(df)} Schluessel gefunden")
    return fehler


def _pruefe_familie(df, namen):
    print("\n3. Spalte 'Familie' deckt sich mit Mapping_Namen.xlsx")
    fehler = 0
    soll = dict(zip(namen[KEY].astype(str).str.strip(),
                    namen["Powerpoint Familie"].astype(str).str.strip()))
    for _, z in df.iterrows():
        s = str(z[KEY]).strip()
        ist = str(z["Familie"]).strip()
        if soll.get(s, "") != ist:
            print(f"   FEHLER — {s}: Excel sagt '{ist}', "
                  f"Mapping sagt '{soll.get(s, '')}'")
            fehler += 1
    if not fehler:
        print("   OK — keine Abweichung")
    return fehler


def _pruefe_umfang(df):
    print("\n4. Genau die 14 Strategien mit Kasten (Thema bleibt aussen vor)")
    fehler = 0
    ist = list(df[KEY].astype(str).str.strip())
    fehlend = [s for s in ERWARTET if s not in ist]
    zuviel = [s for s in ist if s not in ERWARTET]
    if fehlend:
        print(f"   FEHLER — fehlen: {fehlend}")
        fehler += 1
    for s in zuviel:
        if s in OHNE_KASTEN:
            print(f"   FEHLER — '{s}' gehoert zur Thema-Familie und hat "
                  f"KEINEN Kasten in der Vorlage")
        else:
            print(f"   FEHLER — unbekannte Strategie '{s}'")
        fehler += 1
    if not fehler:
        print(f"   OK — {len(ist)} Strategien, Thema korrekt ausgenommen")
    return fehler


def _pruefe_vollstaendig(df):
    print("\n5. Kein Feld leer")
    fehler = 0
    for _, z in df.iterrows():
        for sp in ["Anzeigename"] + KRITERIEN:
            wert = z.get(sp)
            if pd.isna(wert) or not str(wert).strip():
                print(f"   FEHLER — {z[KEY]}: '{sp}' ist leer")
                fehler += 1
    if not fehler:
        print(f"   OK — {len(df) * 5} Felder gefuellt")
    return fehler


def _pruefe_schreibweise(df):
    print("\n6. Einheitliche Schreibweise")
    fehler = 0
    for _, z in df.iterrows():
        for sp in KRITERIEN:
            w = str(z[sp])
            if re.search(r"\bmin\.(?!\w)", w):
                print(f"   FEHLER — {z[KEY]} / {sp}: 'min.' statt 'mind.' ({w!r})")
                fehler += 1
            if re.search(r"\d%", w):
                print(f"   FEHLER — {z[KEY]} / {sp}: Prozent ohne "
                      f"Leerzeichen ({w!r})")
                fehler += 1
            if "  " in w or w != w.strip():
                print(f"   FEHLER — {z[KEY]} / {sp}: ueberfluessiger "
                      f"Leerraum ({w!r})")
                fehler += 1
    # Tippfehler, die es in den Vorlagen gab — duerfen nicht zurueckkehren
    alle = " ".join(df.astype(str).values.ravel())
    for tippfehler in ("FPFB", "AUsgewogen"):
        if tippfehler in alle:
            print(f"   FEHLER — Tippfehler '{tippfehler}' ist zurueck")
            fehler += 1
    if not fehler:
        print("   OK — keine Abweichung")
    return fehler


def _pruefe_zugriff(df):
    print("\n7. anlagekriterien_fuer() liefert die richtige Reihenfolge")
    try:
        from modules.shared import anlagekriterien_fuer
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0
    fehler = 0
    paare = anlagekriterien_fuer("cVV defensiv plus", df)
    bez = [b for b, _ in paare]
    if bez != KRITERIEN:
        print(f"   FEHLER — Reihenfolge {bez}, erwartet {KRITERIEN}")
        fehler += 1
    else:
        print(f"   OK — cVV defensiv plus: "
              f"{', '.join(f'{b}={w}' for b, w in paare)}")
    for s in OHNE_KASTEN:
        if anlagekriterien_fuer(s, df):
            print(f"   FEHLER — '{s}' sollte KEINE Kriterien liefern")
            fehler += 1
    if not fehler:
        print(f"   OK — {len(OHNE_KASTEN)} Thema-Strategien liefern korrekt []")
    for leer in ("", None, "Gibt es nicht"):
        if anlagekriterien_fuer(leer, df):
            print(f"   FEHLER — {leer!r} sollte [] liefern")
            fehler += 1
    return fehler


def main():
    if not os.path.exists(EXCEL):
        print(f"FEHLER: {EXCEL} fehlt")
        return 1
    df = pd.read_excel(EXCEL)
    namen = pd.read_excel(NAMEN)

    fehler = (_pruefe_struktur(df)
              + _pruefe_schluessel(df, namen)
              + _pruefe_familie(df, namen)
              + _pruefe_umfang(df)
              + _pruefe_vollstaendig(df)
              + _pruefe_schreibweise(df)
              + _pruefe_zugriff(df))

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print(f"BESTANDEN — {len(df)} Strategien, Konfiguration konsistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
