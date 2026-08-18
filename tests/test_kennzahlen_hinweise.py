"""Pruefstein fuer die Hinweistexte der Kennzahlen-Kacheln (NEU 18.08.2026).

Die Kacheln im Performance-Reiter tragen je einen Text hinter dem Fragezeichen
(`st.metric(..., help=...)` in `display_metrics`). Zwei davon sind eine ZUSAGE
und kein beliebiger Begleittext:

  Calmar  Der Satz muss vollstaendig sein. Vorher stand dort "Je hoeher, desto
          besser die risikoadjustierte Rendite" — ohne Verb und ohne Bezug,
          worauf sich "hoeher" bezieht.

  Sharpe  Der Text muss sagen, WELCHER risikofreie Zins gemeint ist. Er nannte
          ihn dreimal, ohne ihn je zu benennen; im Kundengespraech ist genau
          das die Rueckfrage. Und er trug die interne Abkuerzung "rf", die in
          der Oberflaeche nirgends eingefuehrt wird.

DIE HERKUNFT DES ZINSSATZES IST GEMESSEN, NICHT ANGENOMMEN. Die CSV-Spalte
heisst schlicht "Risiko freier Zins" (modules/shared.py) und nennt keine
Quelle. Belegt wurde die Zuordnung an den echten Daten: Das Tief der Reihe
liegt bei -0,605 % am 14.12.2021, das Hoch bei 4,002 % am 19.10.2023 — die
Extremwerte des 3-MONATS-Euribor. Die Laufzeit ist damit unterscheidbar:
1M lag im Hoch bei rund 3,86 %, 6M bei rund 4,2 %. Wer den Text aendert,
aendert eine belegte Sachaussage.

WARUM STATISCH UND KEIN APPTEST: Es geht um Wortlaut, nicht um Verhalten. Der
Syntaxbaum sagt ihn zu, ohne dass ein Paket installiert sein muss — dieselbe
Bauform wie test_keepalive.py.

  1. Der abgestimmte Wortlaut steht so im Quelltext
  2. Die Zusage dahinter, unabhaengig vom Satzbau

SCHRITT 2 GIBT ES, WEIL SCHRITT 1 ZU VIEL PRUEFT. Ein Test auf den exakten
Satz schlaegt schon bei einem eingefuegten Komma an. Er ist trotzdem richtig
so — der Wortlaut ist abgestimmt —, aber die eigentliche fachliche Zusage
(Euribor genannt, kein "rf") soll den Umbau eines Satzes ueberleben.

Findet der Pruefstein seinen Gegenstand nicht, ist das ein FEHLER und kein
"uebersprungen" (Transferwissen #65): Eine fehlende Funktion ist ein
gebrochener Vertrag, kein Umgebungsproblem.

Braucht kein einziges Paket — nur den Syntaxbaum.

    python tests/test_kennzahlen_hinweise.py
"""

import ast
import os
import re
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

APP = "streamlit_app.py"
FUNKTION = "display_metrics"

# Der abgestimmte Wortlaut (Philip/Michael, 18.08.2026). SOLLWERT AUS DER
# ZUSAGE, NICHT AUS DER MESSUNG (Transferwissen #58): Diese beiden Zeichenketten
# sind das, was vereinbart wurde — sie sind nicht aus der Anzeige abgeschrieben.
SOLL = {
    "Calmar Ratio":
        "CAGR / |Max Drawdown|. Je höher der Wert, desto besser ist die "
        "risikoadjustierte Rendite.",
    "Sharpe Ratio":
        "Sharpe Ratio nach Sharpe (1994): Mittelwert der täglichen "
        "Überrenditen (Portfolio − risikofreier Zins) geteilt durch deren "
        "Standardabweichung, anschließend × √365 annualisiert. Misst die "
        "Mehrrendite über den risikofreien Zins pro Risikoeinheit; als "
        "risikofreier Zins dient der 3-Monats-Euribor.",
}

# Die Zusage hinter dem Wortlaut.
ZINS_NAME = "3-Monats-Euribor"
# Die nackte Abkuerzung, die nicht mehr vorkommen darf. Als Wortgrenze, damit
# "rf" in einem groesseren Wort (etwa "Bedarf") nicht faelschlich anschlaegt.
ABKUERZUNG = re.compile(r"\brf\b")

# Die Texte tragen Zeichen, die eine alte Windows-Konsole nicht kann
# (U+2212 MINUS, U+221A WURZEL). Ohne das hier stuerbe der Pruefstein
# ausgerechnet dann, wenn er etwas zu melden hat.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _sicher(text):
    """Text so, dass ihn auch eine Konsole ohne Unicode ausgeben kann."""
    kodierung = getattr(sys.stdout, "encoding", None) or "ascii"
    return text.encode(kodierung, errors="replace").decode(kodierung, "replace")


def _baum(pfad):
    with open(os.path.join(WURZEL, pfad), encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=pfad)


def _text(knoten):
    """Der Wert eines help=-Arguments, oder '<berechnet>' bei einem f-String."""
    if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
        return knoten.value
    if isinstance(knoten, ast.JoinedStr):
        return "<berechnet>"
    return "<berechnet>"


def kachel_hinweise():
    """{Kachelname: (zeile, hilfetext)} aus display_metrics.

    Returns:
        dict, oder None wenn die Funktion selbst nicht gefunden wurde.
    """
    ziel = None
    for knoten in ast.walk(_baum(APP)):
        if isinstance(knoten, ast.FunctionDef) and knoten.name == FUNKTION:
            ziel = knoten
            break
    if ziel is None:
        return None

    gefunden = {}
    for knoten in ast.walk(ziel):
        if not isinstance(knoten, ast.Call):
            continue
        if getattr(knoten.func, "attr", None) != "metric":
            continue
        if not knoten.args:
            continue
        erstes = knoten.args[0]
        if not (isinstance(erstes, ast.Constant)
                and isinstance(erstes.value, str)):
            continue
        hilfe = None
        for kw in knoten.keywords:
            if kw.arg == "help":
                hilfe = _text(kw.value)
        gefunden[erstes.value] = (knoten.lineno, hilfe)
    return gefunden


def schritt1_wortlaut():
    print("Schritt 1 — der abgestimmte Wortlaut steht so im Quelltext")
    kacheln = kachel_hinweise()

    # Kein "uebersprungen": Wer den Gegenstand verliert, hat einen Fehler
    # gefunden und keinen Grund zum Schweigen (#65).
    if kacheln is None:
        print(f"    FEHLER — Funktion '{FUNKTION}' gibt es in {APP} nicht "
              "mehr. Der Pruefstein hat seinen Gegenstand verloren.")
        return 1

    f = 0
    for name, soll in SOLL.items():
        if name not in kacheln:
            print(f"    FEHLER — Kachel '{name}' kommt in {FUNKTION} nicht "
                  "(mehr) vor.")
            f += 1
            continue
        zeile, ist = kacheln[name]
        if ist is None:
            print(f"    FEHLER — '{name}' ({APP}:{zeile}) hat gar keinen "
                  "Hinweistext.")
            f += 1
        elif ist == "<berechnet>":
            print(f"    FEHLER — '{name}' ({APP}:{zeile}) baut seinen "
                  "Hinweistext zusammen; er ist so nicht zusagbar.")
            f += 1
        elif ist != soll:
            print(f"    FEHLER — '{name}' ({APP}:{zeile}) weicht ab.")
            print(f"             SOLL: {_sicher(soll)}")
            print(f"             IST : {_sicher(ist)}")
            f += 1
        else:
            print(f"    OK — '{name}' ({APP}:{zeile}) wortgleich")
    return f


def schritt2_zusage():
    print("Schritt 2 — die Zusage dahinter, unabhaengig vom Satzbau")
    kacheln = kachel_hinweise()
    if kacheln is None or "Sharpe Ratio" not in kacheln:
        print(f"    FEHLER — Kachel 'Sharpe Ratio' in {FUNKTION} nicht "
              "gefunden.")
        return 1

    zeile, ist = kacheln["Sharpe Ratio"]
    if not isinstance(ist, str) or ist == "<berechnet>":
        print(f"    FEHLER — 'Sharpe Ratio' ({APP}:{zeile}) hat keinen "
              "lesbaren Hinweistext.")
        return 1

    f = 0
    if ZINS_NAME not in ist:
        print(f"    FEHLER — der Sharpe-Hinweis ({APP}:{zeile}) nennt den "
              f"risikofreien Zins nicht beim Namen ('{ZINS_NAME}' fehlt). "
              "Ohne ihn kann ein Berater die Kennzahl nicht einordnen.")
        f += 1
    else:
        print(f"    OK — '{ZINS_NAME}' wird genannt")

    if ABKUERZUNG.search(ist):
        print(f"    FEHLER — der Sharpe-Hinweis ({APP}:{zeile}) traegt noch "
              "die Abkuerzung 'rf'. Sie ist Code-Jargon und wird in der "
              "Oberflaeche nirgends eingefuehrt.")
        f += 1
    else:
        print("    OK — keine nackte Abkuerzung 'rf' im Text")
    return f


def main():
    print("Pruefstein: Hinweistexte der Kennzahlen-Kacheln\n")
    fehler = 0
    for schritt in (schritt1_wortlaut, schritt2_zusage):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — beide Hinweistexte stehen im abgestimmten Wortlaut, "
          "und der risikofreie Zins ist benannt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
