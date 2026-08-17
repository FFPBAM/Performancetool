"""Prueft die Bedienelemente aus der Bedienbarkeits-Durchsicht (11.08.2026).

Alle Pruefungen laufen am LAUFENDEN Programm per AppTest — nicht am
Quelltext. Was hier gruen ist, hat ein Nutzer auch wirklich vor sich.

Geprueft wird:
  1. Zeitraum-Schnellwahl rechnet richtig (1/3/5/10 Jahre, Seit Auflage) und
     die Kalenderfelder erscheinen nur auf Wunsch.
  2. Der PDF-Weg ist weg — keine Schaltflaeche, keine Funktion, kein
     reportlab/matplotlib in requirements.txt.
  3. Die Benchmark-Zusammensetzung steht genau EINMAL.
  4. Das Logo steht auf dem Anmeldebildschirm.
  5. Der Datenstand steht oben, nicht nur als Fussnote.

    python tests/test_bedienung.py     (braucht streamlit)
"""

import os
import re
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)


def _app(angemeldet=True):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                           default_timeout=400)
    at.secrets["passwords"] = {"t": "t"}
    if angemeldet:
        at.session_state["logged_in"] = True
        at.session_state["username"] = "t"
    return at


def _ss(at, key, default=None):
    """session_state von AppTest kennt kein .get() — daher dieser Zugriff."""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def _captions(at):
    return [c.value for c in at.caption]


def _zeitraum_aus_caption(at):
    """Die Zeitspanne steht als Caption 'TT.MM.JJJJ – TT.MM.JJJJ'."""
    for t in _captions(at):
        m = re.fullmatch(r"(\d{2}\.\d{2}\.\d{4})\s+–\s+(\d{2}\.\d{2}\.\d{4})",
                         t.strip())
        if m:
            return m.group(1), m.group(2)
    return None, None


def pruefe_zeitraum():
    print("1. Zeitraum-Schnellwahl")
    import datetime as dt
    fehler = 0
    at = _app()
    at.run()
    if at.exception:
        for e in at.exception:
            print(f"   FEHLER — App warf: {str(e.value)[:200]}")
        return 1

    # Vorbelegung: Seit Auflage, Kalenderfelder ausgeblendet
    if _ss(at, "p_zeitraum") != "Seit Auflage":
        print(f"   FEHLER — Vorbelegung ist "
              f"{_ss(at, 'p_zeitraum')!r}, erwartet 'Seit Auflage'")
        fehler += 1
    # Praefix statt exaktem Schluessel: die Kalenderfelder tragen seit
    # 11.08.2026 einen Zaehler im Key (p_sd_0, p_sd_1, ...), damit der
    # Zuruecksetzen-Knopf sie neu erzeugen kann (Transferwissen #4).
    if any(d.key and d.key.startswith(("p_sd", "p_ed")) for d in at.date_input):
        print("   FEHLER — Kalenderfelder stehen da, obwohl 'Eigener "
              "Zeitraum' aus ist")
        fehler += 1
    start, ende = _zeitraum_aus_caption(at)
    if not start:
        print("   FEHLER — keine Zeitraum-Zeile gefunden")
        return fehler + 1
    print(f"   Seit Auflage: {start} – {ende}")

    # Schnellwahl rechnet: 3 Jahre -> Start liegt ~3 Jahre vor dem Ende
    for wahl, jahre in (("3 Jahre", 3), ("1 Jahr", 1), ("10 Jahre", 10)):
        at.session_state["p_zeitraum"] = wahl
        at.run()
        if at.exception:
            print(f"   FEHLER — {wahl}: {str(at.exception[0].value)[:160]}")
            fehler += 1
            continue
        s, e = _zeitraum_aus_caption(at)
        if not s:
            print(f"   FEHLER — {wahl}: keine Zeitraum-Zeile")
            fehler += 1
            continue
        sd = dt.datetime.strptime(s, "%d.%m.%Y").date()
        ed = dt.datetime.strptime(e, "%d.%m.%Y").date()
        tage = (ed - sd).days
        soll = jahre * 365
        # Toleranz: Schaltjahre, und bei jungen Strategien greift der erste
        # Datenpunkt (dann ist der Zeitraum KUERZER — das ist korrekt).
        if tage > soll + 4:
            print(f"   FEHLER — {wahl}: {tage} Tage, erwartet hoechstens "
                  f"{soll + 4}")
            fehler += 1
        else:
            print(f"   {wahl:10s}: {s} – {e}  ({tage} Tage)")

    # Eigener Zeitraum blendet die Kalenderfelder ein
    at.session_state["p_zeitraum"] = "Seit Auflage"
    at.session_state["p_zeit_frei"] = True
    at.run()
    keys = {d.key for d in at.date_input if d.key}
    if not (any(k.startswith("p_sd") for k in keys)
            and any(k.startswith("p_ed") for k in keys)):
        print(f"   FEHLER — Kalenderfelder fehlen trotz 'Eigener Zeitraum' "
              f"(gefunden: {keys})")
        fehler += 1
    else:
        print("   Eigener Zeitraum: Kalenderfelder erscheinen")

    fehler += _pruefe_zuruecksetzen(at)
    return fehler


def _pruefe_zuruecksetzen(at):
    """Der Zuruecksetzen-Knopf im eigenen Zeitraum (NEU 11.08.2026).

    Geprueft wird die WIRKUNG, nicht nur die Existenz: Datum verstellen,
    Knopf druecken, danach muss wieder der Wert der Schnellwahl dastehen.
    Vorausgesetzt wird ein Lauf mit eingeschaltetem 'Eigener Zeitraum'.
    """
    import datetime as dt
    print("   Zuruecksetzen-Knopf")

    knopf = next((b for b in at.button if b.key == "p_zeit_reset"), None)
    if knopf is None:
        print(f"      FEHLER — kein Knopf 'p_zeit_reset' "
              f"(vorhanden: {[b.key for b in at.button]})")
        return 1

    feld_start = next((d for d in at.date_input
                       if d.key and d.key.startswith("p_sd")), None)
    if feld_start is None:
        print("      FEHLER — kein Startdatum-Feld")
        return 1
    vorgabe = feld_start.value

    # Startdatum bewusst verstellen (ein Jahr spaeter, aber nicht ueber das Ende)
    feld_ende = next((d for d in at.date_input
                      if d.key and d.key.startswith("p_ed")), None)
    verstellt = min(vorgabe + dt.timedelta(days=365),
                    feld_ende.value - dt.timedelta(days=1))
    feld_start.set_value(verstellt).run()
    ist = next(d.value for d in at.date_input
               if d.key and d.key.startswith("p_sd"))
    if ist != verstellt:
        print(f"      FEHLER — Verstellen wirkte nicht ({ist} statt {verstellt})")
        return 1

    # Knopf druecken -> zurueck auf die Vorgabe der Schnellwahl
    next(b for b in at.button if b.key == "p_zeit_reset").click().run()
    danach = next(d.value for d in at.date_input
                  if d.key and d.key.startswith("p_sd"))
    if danach != vorgabe:
        print(f"      FEHLER — nach dem Zuruecksetzen {danach}, "
              f"erwartet {vorgabe}")
        return 1
    print(f"      OK — {vorgabe} -> verstellt {verstellt} -> "
          f"zurueckgesetzt {danach}")
    return 0


def pruefe_kein_pdf():
    print("\n2. PDF-Weg ist entfernt")
    fehler = 0
    at = _app()
    at.run()
    beschriftungen = [b.label for b in at.button]
    pdf_knoepfe = [b for b in beschriftungen if "pdf" in b.lower()]
    if pdf_knoepfe:
        print(f"   FEHLER — PDF-Schaltflaeche vorhanden: {pdf_knoepfe}")
        fehler += 1

    with open(os.path.join(WURZEL, "streamlit_app.py"), encoding="utf-8") as fh:
        quelle = fh.read()
    for muster in ("generate_perf_pdf", "reportlab", "_mpl_line_chart"):
        if muster in quelle:
            print(f"   FEHLER — '{muster}' steht noch in streamlit_app.py")
            fehler += 1

    with open(os.path.join(WURZEL, "requirements.txt"), encoding="utf-8") as fh:
        req = fh.read().lower()
    for paket in ("reportlab", "matplotlib"):
        if paket in req:
            print(f"   FEHLER — '{paket}' steht noch in requirements.txt")
            fehler += 1

    if not fehler:
        print("   OK — keine PDF-Schaltflaeche, keine Reste, "
              "requirements bereinigt")
    return fehler


def pruefe_benchmark_einmal():
    print("\n3. Benchmark-Zusammensetzung genau einmal")
    fehler = 0
    at = _app()
    at.run()
    texte = _captions(at) + [m.value for m in at.markdown]
    treffer = [t for t in texte if "Zusammensetzung Benchmark" in t]
    # Vorbelegung: Benchmark AN und Balken-Chart AN — frueher erschien sie
    # dadurch doppelt.
    if len(treffer) != 1:
        print(f"   FEHLER — {len(treffer)}x gefunden, erwartet genau 1")
        for t in treffer:
            print(f"          {t.strip()[:80]}")
        fehler += 1
    else:
        print(f"   OK — 1x: {treffer[0].strip()[:70]}")

    # Benchmark AUS: dann gehoert sie an den Balken-Chart
    at.session_state["p_bm"] = False
    at.run()
    texte = _captions(at) + [m.value for m in at.markdown]
    treffer = [t for t in texte if "Zusammensetzung Benchmark" in t]
    if len(treffer) != 1:
        print(f"   FEHLER — ohne Benchmark-Schalter {len(treffer)}x, "
              f"erwartet 1")
        fehler += 1
    else:
        print("   OK — auch ohne Benchmark-Schalter genau 1x")
    return fehler


def pruefe_auftritt():
    print("\n4. Auftritt: Logo und Datenstand")
    fehler = 0
    # Logo auf dem Anmeldebildschirm
    at = _app(angemeldet=False)
    at.run()
    # Der Elementname heisst in Streamlit 1.61 "image". "imgs" liefert eine
    # LEERE LISTE statt eines Fehlers — deshalb wird auf Inhalt geprueft und
    # nicht auf das blosse Gelingen des Aufrufs.
    bilder = []
    for typ in ("image", "imgs"):
        try:
            gefunden = list(at.get(typ))
        except Exception:
            continue
        if gefunden:
            bilder = gefunden
            break
    if not bilder:
        print("   FEHLER — kein Bild auf dem Anmeldebildschirm")
        fehler += 1
    else:
        print(f"   OK — Logo auf dem Anmeldebildschirm ({len(bilder)} Bild)")

    # Datenstand oben
    at2 = _app()
    at2.run()
    stand = [c for c in _captions(at2) if c.strip().startswith("Datenstand")]
    if not stand:
        print("   FEHLER — keine Datenstand-Zeile oben")
        fehler += 1
    else:
        print(f"   OK — {stand[0].strip()}")
    return fehler


def main():
    # Verfuegbarkeitsprobe ohne Import: Der Test braucht streamlit.testing,
    # laedt es aber erst in _app(). find_spec statt "import ... # noqa",
    # weil pyflakes kein noqa kennt und den Namen sonst zu Recht als
    # unbenutzt meldet (12.08.2026).
    from importlib import util as _util
    try:
        vorhanden = _util.find_spec("streamlit.testing.v1") is not None
    except (ImportError, ValueError):
        vorhanden = False
    if not vorhanden:
        print("UEBERSPRUNGEN — streamlit.testing.v1 nicht verfuegbar")
        return 0

    fehler = (pruefe_zeitraum() + pruefe_kein_pdf()
              + pruefe_benchmark_einmal() + pruefe_auftritt())
    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — Bedienelemente verhalten sich wie abgestimmt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
