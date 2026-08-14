"""Regressionstest: JEDE Strategie hat einen Honorarsatz (NEU 11.08.2026).

Hintergrund: Die beiden SCHWEIZ-Strategien fehlten in
Mapping_Honorarsatz.xlsx — 17 Zeilen bei 19 Strategien in den Daten. Das
faellt nicht auf, weil der Loader den Fehlschlag ABFING:

    try:
        fd = float(mapping.loc[mapping["Inhaber"] == pn,
                               "Honorarsatz Standard"].values[0])
    except Exception:
        fd = 0.0                      # <- stilles Null-Honorar

Folge: Die App zeigte fuer beide Strategien "nach Kosten"-Zahlen, in denen
gar keine Kosten steckten — und niemand sah eine Fehlermeldung.

STAND 14.08.2026 (Audit, Befund B6): Das blanke except ist raus. Der
Rueckfall auf 0,0 BLEIBT, damit die App weiterlaeuft und der Berater den
Satz im Eingabefeld ueberschreiben kann — aber die Zeitreihe vermerkt ihn
jetzt in `attrs["honorar_gefunden"]`, und die Oberflaeche macht daraus eine
Fehlermeldung mit Strategienamen. Schritt 4 haelt genau das fest.

Warum das wichtiger ist, als es klingt: Gemessen an echten Daten weist
"Muster ausgewogen cVV" ohne seinen 1,55-%-Satz 6,90 % statt 5,27 % p.a.
aus — 1,63 Prozentpunkte zu hoch, und zwar in der schmeichelnden Richtung.

Geprueft wird gegen die ECHTEN Daten:
  1. Jede Strategie in Daten/ hat eine Zeile im Honorar-Mapping.
  2. Kein Satz ist 0 oder unplausibel (erwartet: 0,5 % bis 3 % p.a.).
  3. Die beiden SCHWEIZ-Strategien stehen auf 1,55 % netto
     (Festlegung Philip, 11.08.2026).
  4. Ein FEHLENDER Satz ist von einem echten 0 % unterscheidbar.

Braucht pandas + streamlit (der Loader liegt in modules/shared.py).

    python tests/test_honorarsatz.py

Rueckgabewert 0 = bestanden, 1 = fehlgeschlagen.
"""

import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

try:
    from modules.shared import (
        DATA_FOLDER, EXCLUDE_SUBSTRINGS, detect_newest_date_tag,
        load_all_csvs, load_mapping, build_portfolio_timeseries,
        strategien_ohne_honorarsatz,
    )
except ImportError as ex:
    print(f"UEBERSPRUNGEN — Abhaengigkeit fehlt: {ex}")
    sys.exit(0)

# Plausibilitaetsfenster: alles ausserhalb ist mit Sicherheit ein Datenfehler
# (Tippfehler in der Excel, Prozent statt Dezimal, fehlende Zeile).
MIN_SATZ = 0.005      # 0,5 % p.a.
MAX_SATZ = 0.03       # 3,0 % p.a.

SOLL_SCHWEIZ = {
    "Muster SCHWEIZ Substanz": 0.0155,
    "Muster SCHWEIZ Aktien":   0.0155,
}


def schritt4_ausfall_ist_sichtbar(mapping, tag):
    """Ist ein FEHLENDER Satz von einem echten 0 % unterscheidbar?

    Bis zum Audit (14.08.2026) war er das nicht: Der Loader fing den
    Fehlschlag ab und setzte 0,0 — auf dem Bildschirm nicht von einer
    Angabe zu unterscheiden, weil der Satz in einem Eingabefeld steht.
    Die Zahlen darunter waren dann brutto und trotzdem als "nach Kosten"
    beschriftet.

    Gemessen an echten Daten: Ohne den 1,55-%-Satz weist "Muster ausgewogen
    cVV" 6,90 % statt 5,27 % p.a. aus — 1,63 Prozentpunkte zu hoch.

    Dieser Schritt entfernt die Mapping-Zeile ABSICHTLICH und verlangt, dass
    die Zeitreihe den Ausfall vermerkt. Er ist die Gegenprobe zu Schritt 1:
    Der prueft, dass heute nichts fehlt — dieser prueft, dass ein Fehlen
    morgen AUFFAELLT.
    """
    print()
    print("SCHRITT 4 — ein fehlender Satz muss sich vermerken")
    opfer = "Muster ausgewogen cVV"
    files = load_all_csvs(DATA_FOLDER, tag, EXCLUDE_SUBSTRINGS)
    f = 0

    voll = build_portfolio_timeseries(files, mapping)
    if opfer not in voll:
        print(f"    UEBERSPRUNGEN — {opfer} nicht in den Daten")
        return 0
    if voll[opfer].attrs.get("honorar_gefunden") is not True:
        print(f"    FEHLER — {opfer} gilt als ohne Satz, obwohl das Mapping "
              "eine Zeile hat")
        f += 1
    else:
        print(f"    OK — {opfer} mit Mapping-Zeile: honorar_gefunden=True, "
              f"Satz {float(voll[opfer]['fee_default'].iloc[0]) * 100:.4f} %")

    ohne = build_portfolio_timeseries(
        files, mapping[mapping["Inhaber"] != opfer])
    d = ohne[opfer]
    if d.attrs.get("honorar_gefunden") is not False:
        print(f"    FEHLER — Mapping-Zeile entfernt, aber honorar_gefunden="
              f"{d.attrs.get('honorar_gefunden')!r} — der Ausfall bliebe "
              "unsichtbar und die Zahlen waeren still brutto")
        f += 1
    else:
        print("    OK — ohne Mapping-Zeile: honorar_gefunden=False "
              f"(Satz faellt auf {float(d['fee_default'].iloc[0]) * 100:.4f} %, "
              "die Oberflaeche meldet es)")

    # Die Funktion, aus der die Oberflaeche ihre Meldung baut. Sie liegt
    # ausdruecklich NICHT inline im Renderpfad, damit sie hier greifbar ist.
    faelle = (
        ("alles in Ordnung",       [("A", voll[opfer])],                 []),
        ("Satz fehlt",             [("A", d)],                          ["A"]),
        ("nur das zweite fehlt",   [("A", voll[opfer]), ("B", d)],      ["B"]),
        ("kein Vergleich gewaehlt", [("A", voll[opfer]), (None, None)],  []),
        ("beide betroffen",        [("A", d), ("B", d)],           ["A", "B"]),
    )
    for bez, eingabe, soll in faelle:
        ist = strategien_ohne_honorarsatz(eingabe)
        if ist != soll:
            print(f"    FEHLER — {bez}: {ist} statt {soll}")
            f += 1
        else:
            print(f"    OK — {bez}: {ist}")
    return f


def main():
    mapping = load_mapping()
    tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
    if tag is None:
        print(f"FEHLER: keine CSVs in {DATA_FOLDER}")
        return 1
    ts = build_portfolio_timeseries(
        load_all_csvs(DATA_FOLDER, tag, EXCLUDE_SUBSTRINGS), mapping)

    print(f"Datenstand {tag} — {len(ts)} Strategien, "
          f"{len(mapping)} Zeilen im Honorar-Mapping\n")
    kopf = f"{'Strategie':30s} {'Satz p.a.':>10s} {'im Mapping':>11s}  Ergebnis"
    print(kopf)
    print("-" * len(kopf))

    fehler = 0
    inhaber = set(mapping["Inhaber"].astype(str))
    for name in sorted(ts):
        satz = float(ts[name]["fee_default"].iloc[0])
        gelistet = name in inhaber
        ok = gelistet and MIN_SATZ <= satz <= MAX_SATZ
        soll = SOLL_SCHWEIZ.get(name)
        if soll is not None and abs(satz - soll) > 1e-9:
            ok = False
        fehler += 0 if ok else 1
        print(f"{name[:30]:30s} {satz * 100:9.4f}% {str(gelistet):>11s}  "
              f"{'OK' if ok else 'FEHLER'}")
        if not ok:
            if not gelistet:
                print(f"{'':30s} -> keine Zeile in Mapping_Honorarsatz.xlsx; "
                      f"der Loader faellt still auf 0 % zurueck")
            elif soll is not None:
                print(f"{'':30s} -> erwartet {soll * 100:.4f}%")
            else:
                print(f"{'':30s} -> ausserhalb {MIN_SATZ * 100:.2f}–"
                      f"{MAX_SATZ * 100:.2f}%")

    fehler += schritt4_ausfall_ist_sichtbar(mapping, tag)

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Strategie(n) ohne plausiblen Satz")
        return 1
    print(f"BESTANDEN — alle {len(ts)} Strategien haben einen Honorarsatz "
          f"zwischen {MIN_SATZ * 100:.2f} % und {MAX_SATZ * 100:.2f} % p.a.")
    print("            SCHWEIZ Substanz und Aktien stehen auf 1,5500 % netto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
