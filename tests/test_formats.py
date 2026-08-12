"""Pruefstein fuer modules/formats.py — Zahlen und Datumsangaben im Text.

formats.py entscheidet, wie Zahlen in der Broschuere DASTEHEN. Bis 12.08.2026
hatte das Modul keinen einzigen Test, obwohl jede Kennzahl jeder Kundenfolie
durch diese vier Funktionen laeuft.

Der wichtigste Teil ist Schritt 2: Ein Fehlwert muss als "–" erscheinen und
darf NIE als "nan", "None" oder "NaT" in ein Kundendokument geraten
(Transferwissen #46 — ein Fehlwert darf nicht wie ein Messwert aussehen).
Genau daran hat es gefehlt: fmt_date_de(float('nan')) lieferte woertlich
"nan", eine leere Excel-Zelle kommt naemlich als NaN an und nicht als None.

Laeuft OHNE jede Installation. Schritt 5 braucht pandas und ueberspringt
sich sonst selbst.

    python tests/test_formats.py
"""

import datetime as dt
import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

from modules.formats import (  # noqa: E402
    DATE_FORMAT_DE, DISCLAIMER_PERFORMANCE, EMPTY_VALUE, PCT_FORMAT_CODE,
    QUELLE_PREFIX, fmt_date_de, fmt_pct, fmt_ratio, quelle_text,
)


def _pruefe(bezeichnung, ist, soll):
    if ist == soll:
        print(f"    OK — {bezeichnung}: {ist!r}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {ist!r} statt {soll!r}")
    return 1


def schritt1_prozent_und_ratio():
    print("Schritt 1 — deutsche Notation (Komma, nicht Punkt)")
    f = 0
    f += _pruefe("fmt_pct(0.0523)", fmt_pct(0.0523), "5,23%")
    f += _pruefe("fmt_pct(0.05, decimals=1)", fmt_pct(0.05, decimals=1), "5,0%")
    f += _pruefe("fmt_pct(0)", fmt_pct(0), "0,00%")
    f += _pruefe("fmt_pct(-0.1638)", fmt_pct(-0.1638), "-16,38%")
    f += _pruefe("fmt_pct(1.5)", fmt_pct(1.5), "150,00%")
    # Kaufmaennisch runden ist NICHT garantiert (Python rundet zur geraden
    # Zahl); geprueft wird deshalb nur, dass ueberhaupt gerundet wird.
    f += _pruefe("fmt_pct(0.056789, decimals=3)", fmt_pct(0.056789, decimals=3),
                 "5,679%")
    f += _pruefe("fmt_ratio(0.43)", fmt_ratio(0.43), "0,43")
    f += _pruefe("fmt_ratio(-1.236)", fmt_ratio(-1.236), "-1,24")
    f += _pruefe("fmt_ratio(-67.4812)", fmt_ratio(-67.4812), "-67,48")
    f += _pruefe("fmt_ratio(2, decimals=0)", fmt_ratio(2, decimals=0), "2")
    # Zahl als String darf nicht durchfallen — CSV-Daten kommen so an.
    f += _pruefe("fmt_pct('0.05')", fmt_pct("0.05"), "5,00%")
    return f


def schritt2_fehlwerte():
    print("Schritt 2 — ein Fehlwert wird '–', niemals 'nan'/'None'/'NaT'")
    f = 0
    nan = float("nan")
    faelle = [
        ("fmt_pct(None)", fmt_pct(None)),
        ("fmt_pct(nan)", fmt_pct(nan)),
        ("fmt_pct('keine Zahl')", fmt_pct("keine Zahl")),
        ("fmt_ratio(None)", fmt_ratio(None)),
        ("fmt_ratio(nan)", fmt_ratio(nan)),
        ("fmt_ratio('keine Zahl')", fmt_ratio("keine Zahl")),
        ("fmt_date_de(None)", fmt_date_de(None)),
        ("fmt_date_de(nan)", fmt_date_de(nan)),
    ]
    for bezeichnung, ist in faelle:
        f += _pruefe(bezeichnung, ist, EMPTY_VALUE)

    # Der Fehlwert ist der Gedankenstrich, nicht der Bindestrich. Beide sehen
    # in Fliesstext aehnlich aus, im Kundendokument ist nur einer richtig.
    f += _pruefe("EMPTY_VALUE ist ein Gedankenstrich", EMPTY_VALUE, "–")
    if EMPTY_VALUE == "-":
        print("    FEHLER — EMPTY_VALUE ist ein einfacher Bindestrich")
        f += 1
    return f


def schritt3_datum():
    print("Schritt 3 — Datum als DD.MM.YYYY")
    f = 0
    f += _pruefe("fmt_date_de(date(2026,6,19))",
                 fmt_date_de(dt.date(2026, 6, 19)), "19.06.2026")
    f += _pruefe("fmt_date_de(datetime(2026,1,5,14,30))",
                 fmt_date_de(dt.datetime(2026, 1, 5, 14, 30)), "05.01.2026")
    # Fuehrende Nullen: eine Broschuere mit "5.1.2026" faellt sofort auf.
    f += _pruefe("fmt_date_de(date(2026,1,5)) hat fuehrende Nullen",
                 fmt_date_de(dt.date(2026, 1, 5)), "05.01.2026")
    # Bereits formatierte Strings werden durchgereicht (dokumentiert).
    f += _pruefe("fmt_date_de('19.06.2026')", fmt_date_de("19.06.2026"),
                 "19.06.2026")
    f += _pruefe("DATE_FORMAT_DE", DATE_FORMAT_DE, "%d.%m.%Y")
    return f


def schritt4_texte():
    print("Schritt 4 — Quelle-Zeile und Disclaimer")
    f = 0
    f += _pruefe("quelle_text(date(2026,6,19))",
                 quelle_text(dt.date(2026, 6, 19)),
                 "Quelle: Eigene Berechnung, Stand 19.06.2026")
    # Auch hier darf kein Fehlwert durchschlagen.
    f += _pruefe("quelle_text(None)", quelle_text(None),
                 QUELLE_PREFIX + EMPTY_VALUE)
    f += _pruefe("PCT_FORMAT_CODE", PCT_FORMAT_CODE, "0.00%")

    # Compliance-Anker: Der Disclaimer steht auf jeder Kundenfolie. Geprueft
    # wird nicht der Wortlaut (der gehoert der Vorlage), sondern dass die
    # beiden Pflichtaussagen nicht stillschweigend verschwinden.
    pflicht = ["Wertentwicklung in der Vergangenheit",
               "keine Garantie für eine zukünftige Wertentwicklung",
               "nach Kosten berechnet"]
    for satz in pflicht:
        if satz in DISCLAIMER_PERFORMANCE:
            print(f"    OK — Disclaimer enthaelt '{satz[:40]}…'")
        else:
            print(f"    FEHLER — Disclaimer enthaelt NICHT '{satz}'")
            f += 1
    return f


def schritt5_pandas_fehlwerte():
    print("Schritt 5 — pandas-Fehlwerte (NaT) werden ebenfalls zu '–'")
    try:
        import pandas as pd
    except ImportError:
        print("    UEBERSPRUNGEN — pandas nicht installiert")
        return 0
    f = 0
    f += _pruefe("fmt_date_de(pd.NaT)", fmt_date_de(pd.NaT), EMPTY_VALUE)
    f += _pruefe("fmt_date_de(pd.Timestamp('2026-06-19'))",
                 fmt_date_de(pd.Timestamp("2026-06-19")), "19.06.2026")
    f += _pruefe("fmt_pct(pd.NA-artig: float('nan'))",
                 fmt_pct(float("nan")), EMPTY_VALUE)
    return f


def schritt6_streamlitfrei():
    print("Schritt 6 — formats.py bleibt frei von Streamlit und python-pptx")
    pfad = os.path.join("modules", "formats.py")
    with open(pfad, encoding="utf-8") as fh:
        zeilen = [z.strip() for z in fh if z.strip().startswith(("import ",
                                                                "from "))]
    verboten = [z for z in zeilen
                if "streamlit" in z or "pptx" in z or "pandas" in z]
    if verboten:
        print("    FEHLER — verbotene Importe:")
        for z in verboten:
            print(f"      ! {z}")
        print("    formats.py wird auch ohne Oberflaeche gebraucht (Batch).")
        return 1
    print(f"    OK — {len(zeilen)} Import(e), keiner davon verboten: "
          f"{', '.join(zeilen)}")
    return 0


def main():
    print("Pruefstein: modules/formats.py\n")
    fehler = 0
    for schritt in (schritt1_prozent_und_ratio, schritt2_fehlwerte,
                    schritt3_datum, schritt4_texte, schritt5_pandas_fehlwerte,
                    schritt6_streamlitfrei):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — Zahlen, Datumsangaben und Fehlwerte sehen aus wie vorgesehen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
