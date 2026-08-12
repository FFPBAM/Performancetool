"""Prueft, dass die Honorar-Mathematik nur EINMAL im Repo steht.

Warum das einen eigenen Pruefstein bekommt: Der Honorarabzug bestimmt die
Zahlen im Tool UND in der Broschuere. Bis 12.08.2026 hatte
modules/pptx_export.py eigene Kopien (_annual_fee_to_daily_drag,
_make_index_after_fee). Sie waren formelgleich — genau deshalb fiel niemandem
auf, dass es zwei gab. Wer die Formel in analytics korrigiert haette, haette
die Broschuere NICHT mitkorrigiert, und die geht zum Kunden. Derselbe
Mechanismus hat den SCHWEIZ-Honorarfehler getragen (STATUS.md, 11.08.2026).

Drei Schritte:
  1. Quelltext: die Formel steht nur in modules/analytics.py   (ohne Pakete)
  2. Identitaet: pptx_export nutzt genau das analytics-Objekt   (+ pandas/pptx)
  3. Zahlen: der Honorarabzug rechnet wie dokumentiert          (+ pandas)

    python tests/test_kosten_mathematik.py

Schritt 1 laeuft ohne jede Installation und ist der eigentliche Waechter.
"""

import os
import re
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

# Die eine erlaubte Heimat der Kosten-Mathematik.
QUELLE = os.path.join("modules", "analytics.py")

# Eine Zeile ist verdaechtig, wenn sie die 365-Tage-Basis UND einen
# Honorar-Begriff enthaelt. Der risikofreie Zins nutzt dieselbe 365-Basis
# (analytics.py und streamlit_app.py), ist aber eine ANDERE Groesse — er
# faellt durch das Fehlen der Honorar-Begriffe nicht auf.
HONORAR = re.compile(r"fee|honorar|drag", re.IGNORECASE)


def _py_dateien():
    raus = [os.path.join("streamlit_app.py")]
    for name in sorted(os.listdir("modules")):
        if name.endswith(".py"):
            raus.append(os.path.join("modules", name))
    return [p for p in raus if os.path.exists(p) and p != QUELLE]


def schritt1_quelltext():
    print("Schritt 1 — die Formel steht nur in modules/analytics.py")
    treffer = []
    for pfad in _py_dateien():
        with open(pfad, encoding="utf-8") as f:
            for nr, zeile in enumerate(f, start=1):
                # Kommentare duerfen die alten Namen erwaehnen (Historie).
                if zeile.lstrip().startswith("#"):
                    continue
                if "365" in zeile and HONORAR.search(zeile):
                    treffer.append(f"{pfad}:{nr}: {zeile.strip()}")

    # Gegenprobe: in analytics MUSS sie stehen, sonst prueft der Test nichts.
    with open(QUELLE, encoding="utf-8") as f:
        quelle_ok = any("365" in z and HONORAR.search(z) for z in f)

    if not quelle_ok:
        print(f"    FEHLER — in {QUELLE} steht keine Honorar-Formel mehr.")
        print("    Entweder wurde sie verschoben (dann diesen Test nachziehen)")
        print("    oder sie ist verlorengegangen.")
        return 1
    print(f"    OK — {QUELLE} enthaelt die Formel")

    if treffer:
        print(f"    FEHLER — {len(treffer)} weitere Fundstelle(n):")
        for t in treffer:
            print(f"      ! {t}")
        print("    Die Kosten-Mathematik gehoert ausschliesslich nach")
        print("    modules/analytics.py — von dort importieren, nicht kopieren.")
        return 1
    print(f"    OK — keine zweite Fundstelle in {len(_py_dateien())} Dateien")
    return 0


def schritt2_identitaet():
    print("Schritt 2 — pptx_export nutzt genau das analytics-Objekt")
    try:
        from modules import analytics, pptx_export
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — Abhaengigkeit fehlt: {ex}")
        return 0

    fehler = 0
    for name in ("annual_fee_to_daily_drag", "make_index_after_fee"):
        aus_export = getattr(pptx_export, name, None)
        aus_analytics = getattr(analytics, name)
        if aus_export is None:
            print(f"    FEHLER — pptx_export kennt {name} nicht (Import fehlt?)")
            fehler += 1
        elif aus_export is not aus_analytics:
            print(f"    FEHLER — pptx_export.{name} ist eine EIGENE Funktion, "
                  f"nicht die aus analytics")
            fehler += 1
        else:
            print(f"    OK — {name} ist dasselbe Objekt")

    # Die alten Kopien duerfen nicht wieder auftauchen.
    for alt in ("_annual_fee_to_daily_drag", "_make_index_after_fee"):
        if hasattr(pptx_export, alt):
            print(f"    FEHLER — die alte Kopie {alt} ist zurueck")
            fehler += 1
    return 1 if fehler else 0


def schritt3_zahlen():
    print("Schritt 3 — der Honorarabzug rechnet wie dokumentiert")
    try:
        from modules.analytics import (annual_fee_to_daily_drag,
                                       make_index_after_fee)
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — Abhaengigkeit fehlt: {ex}")
        return 0

    fehler = 0

    # 1,55 % p.a. — der Satz der beiden SCHWEIZ-Strategien (11.08.2026).
    drag = annual_fee_to_daily_drag(0.0155)
    erwartet = (1.0155) ** (1 / 365) - 1
    if abs(drag - erwartet) > 1e-15:
        print(f"    FEHLER — Tagesbelastung {drag!r} statt {erwartet!r}")
        fehler += 1
    else:
        print(f"    OK — 1,55 % p.a. ergeben {drag*10000:.4f} Basispunkte/Tag")

    # Ein Jahr ohne Marktbewegung muss exakt das Honorar kosten.
    idx = make_index_after_fee([0.0] * 365, 0.0155, startwert=100.0)
    if len(idx) != 366:
        print(f"    FEHLER — {len(idx)} Werte statt 366 (n+1 inkl. Startwert)")
        fehler += 1
    verlust = 100.0 - float(idx[-1])
    if not (1.50 < verlust < 1.56):
        print(f"    FEHLER — 365 Nulltage kosten {verlust:.4f} statt ~1,53")
        fehler += 1
    else:
        print(f"    OK — 365 Nulltage kosten {verlust:.4f} von 100")

    # Startwert 1.0 ist der Pfad der Wertentwicklungs-Folie.
    idx1 = make_index_after_fee([0.0] * 10, 0.0155, startwert=1.0)
    idx100 = make_index_after_fee([0.0] * 10, 0.0155, startwert=100.0)
    if abs(float(idx1[-1]) * 100.0 - float(idx100[-1])) > 1e-10:
        print("    FEHLER — Startwert 1.0 und 100.0 skalieren nicht gleich")
        fehler += 1
    else:
        print("    OK — Startwert 1.0 und 100.0 skalieren identisch")

    # Ohne Honorar darf nichts abgezogen werden.
    if abs(annual_fee_to_daily_drag(0.0)) > 1e-18:
        print("    FEHLER — 0 % Honorar erzeugt eine Belastung")
        fehler += 1
    else:
        print("    OK — 0 % Honorar kostet nichts")

    return 1 if fehler else 0


def main():
    print("Pruefstein: Honorar-Mathematik nur an EINER Stelle\n")
    fehler = schritt1_quelltext()
    print()
    fehler += schritt2_identitaet()
    print()
    fehler += schritt3_zahlen()
    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Schritt(e)")
        return 1
    print("BESTANDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
