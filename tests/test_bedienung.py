"""Prueft die Bedienelemente aus der Bedienbarkeits-Durchsicht (11.08.2026).

Alle Pruefungen laufen am LAUFENDEN Programm per AppTest — nicht am
Quelltext. Was hier gruen ist, hat ein Nutzer auch wirklich vor sich.

Geprueft wird:
  1. Zeitraum-Schnellwahl rechnet richtig (1/3/5/10 Jahre, Seit Auflage) und
     die Datumsfelder erscheinen nur auf Wunsch — mit DEUTSCHEN Monatsnamen.
  1b. Es gibt im ganzen Repo kein st.date_input mehr (Quelltext-Pruefung).
  2. Der PDF-Weg ist weg — keine Schaltflaeche, keine Funktion, kein
     reportlab/matplotlib in requirements.txt.
  3. Die Benchmark-Zusammensetzung steht genau EINMAL.
  4. Das Logo steht auf dem Anmeldebildschirm.
  5. Der Datenstand steht oben, nicht nur als Fussnote.

    python tests/test_bedienung.py     (braucht streamlit)
"""

import ast
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
    # Praefix statt exaktem Schluessel: die Datumsfelder tragen seit
    # 11.08.2026 einen Zaehler im Key (p_sd_0, p_sd_1, ...), damit der
    # Zuruecksetzen-Knopf sie neu erzeugen kann (Transferwissen #4).
    # Seit 17.08.2026 sind es Auswahlfelder statt eines Kalenders, weil
    # st.date_input sein Popover nur auf Englisch zeigt — der Key heisst
    # jetzt p_sd_0_tag / p_sd_0_monat / p_sd_0_jahr.
    if any(s.key and s.key.startswith(("p_sd", "p_ed")) for s in at.selectbox):
        print("   FEHLER — Datumsfelder stehen da, obwohl 'Eigener "
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

    # Eigener Zeitraum blendet die Datumsfelder ein
    at.session_state["p_zeitraum"] = "Seit Auflage"
    at.session_state["p_zeit_frei"] = True
    at.run()
    keys = {s.key for s in at.selectbox if s.key}
    fehlend = [t for t in ("p_sd", "p_ed")
               if not all(any(k.startswith(t) and k.endswith(teil)
                              for k in keys)
                          for teil in ("_tag", "_monat", "_jahr"))]
    if fehlend:
        print(f"   FEHLER — Datumsfelder unvollstaendig fuer {fehlend} "
              f"(gefunden: {sorted(keys)})")
        fehler += 1
    else:
        print("   Eigener Zeitraum: Tag/Monat/Jahr erscheinen")

    fehler += _pruefe_monatsnamen_deutsch(at)
    fehler += _pruefe_zuruecksetzen(at)
    return fehler


def _pruefe_monatsnamen_deutsch(at):
    """Der eigentliche Punkt aus dem Kollegen-Feedback vom 17.08.2026.

    st.date_input zeigte sein Kalender-Popover ausschliesslich auf Englisch
    ("August 2026", "Su Mo Tu We Th Fr Sa"). Das war keine Fehlkonfiguration:
    Streamlit 1.61 liefert im Frontend nur die englische Sprachdatei aus, und
    einen Sprachparameter gibt es nicht. Ersetzt durch Auswahlfelder mit den
    Monatsnamen aus formats.MONATSNAMEN_LANG.

    Geprueft wird die ANZEIGE, nicht der gespeicherte Wert: Die Auswahlfelder
    tragen intern die Monatsnummer (`.value` ist 7) und zeigen den Namen ueber
    format_func (`.options` ist "Juli"). Ein Test auf den Wert waere gruen,
    waehrend am Bildschirm "July" steht.

    Zwei Faelle, weil die Randjahre bewusst NICHT alle zwoelf Monate
    anbieten: Im Anfangsjahr 2008 beginnt die Historie im Dezember, im
    Endjahr 2026 endet sie im Juli. Erst ein Jahr mitten drin zeigt alle
    zwoelf — und nur dort laesst sich "alle Monate deutsch" pruefen.
    """
    print("   Monatsnamen auf Deutsch")
    from modules.formats import MONATSNAMEN_LANG
    ENGLISCH = ("January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November",
                "December")

    def _monatsfeld():
        return next((s for s in at.selectbox
                     if s.key and s.key.startswith("p_ed")
                     and s.key.endswith("_monat")), None)

    feld = _monatsfeld()
    if feld is None:
        print("      FEHLER — kein Monatsfeld gefunden")
        return 1

    gezeigt = [str(o) for o in feld.options]
    fremd = [g for g in gezeigt if g not in MONATSNAMEN_LANG]
    if fremd:
        englisch = [g for g in fremd if g in ENGLISCH]
        print(f"      FEHLER — Monatsnamen, die nicht aus MONATSNAMEN_LANG "
              f"stammen: {fremd}"
              + (f" (englisch: {englisch})" if englisch else ""))
        return 1
    print(f"      OK — Endjahr: {len(gezeigt)} Monate, alle deutsch "
          f"({gezeigt[0]} … {gezeigt[-1]})")

    # Jahr mitten in der Historie -> alle zwoelf Monate muessen erscheinen.
    jahr_feld = next((s for s in at.selectbox
                      if s.key and s.key.startswith("p_ed")
                      and s.key.endswith("_jahr")), None)
    mitte = [int(o) for o in jahr_feld.options][1:-1]
    if not mitte:
        print("      UEBERSPRUNGEN — kein Jahr ohne Randbeschneidung")
        return 0
    jahr_feld.set_value(mitte[len(mitte) // 2]).run()
    gezeigt = [str(o) for o in _monatsfeld().options]
    if list(gezeigt) != list(MONATSNAMEN_LANG):
        print(f"      FEHLER — im Jahr {mitte[len(mitte) // 2]} lautet die "
              f"Auswahl {gezeigt}, erwartet alle zwoelf deutschen Monate")
        return 1
    print(f"      OK — Jahr {mitte[len(mitte) // 2]}: alle zwoelf Monate "
          f"({gezeigt[0]} … {gezeigt[-1]})")
    return 0


def pruefe_balken_zeitraum():
    """Die ZWEITE Stelle mit Datumsfeldern: Balken-Chart, "Benutzerdefiniert".

    Gemeldet war nur der Zeitraum oben. Betroffen waren aber alle vier Felder
    der Ansicht — und dieser Bedienpfad war bis 17.08.2026 von keinem Test
    beruehrt. Hier steht er in einer Spalte von einem Viertel Breite, die
    Felder sind deshalb gestapelt (untereinander=True).
    """
    print("1d. Balken-Chart, eigener Zeitraum")
    at = _app()
    at.session_state["p_bar"] = True
    at.run()

    radio = next((r for r in at.radio if r.key == "p_bm_r"), None)
    if radio is None:
        print("   FEHLER — kein Zeitraum-Radio am Balken-Chart")
        return 1
    radio.set_value("Benutzerdefiniert").run()
    if at.exception:
        print(f"   FEHLER — {str(at.exception[0].value)[:200]}")
        return 1

    from modules.formats import MONATSNAMEN_LANG
    fehler = 0
    for praefix in ("p_bv", "p_bb"):
        keys = {s.key for s in at.selectbox if s.key and s.key.startswith(praefix)}
        fehlend = [t for t in ("_tag", "_monat", "_jahr")
                   if not any(k.endswith(t) for k in keys)]
        if fehlend:
            print(f"   FEHLER — {praefix}: {fehlend} fehlen (da: {sorted(keys)})")
            fehler += 1
            continue
        monat = next(s for s in at.selectbox if s.key == f"{praefix}_monat")
        fremd = [str(o) for o in monat.options if str(o) not in MONATSNAMEN_LANG]
        if fremd:
            print(f"   FEHLER — {praefix}: fremde Monatsnamen {fremd}")
            fehler += 1
            continue
        print(f"   OK — {praefix}: Tag/Monat/Jahr, Monate deutsch "
              f"({str(monat.options[0])} …)")
    return fehler


def pruefe_datum_optionen():
    """Die rechnende Haelfte der Datumsauswahl, ohne Oberflaeche.

    Hier sitzen die Faelle, die am Bildschirm niemand systematisch durchklickt:
    Schaltjahr, beide Raender des Datenbereichs und der Monatswechsel, bei dem
    ein gespeicherter 31. verschwinden wuerde.
    """
    print("1c. Zulaessige Jahre/Monate/Tage")
    import datetime as dt
    from modules.shared import datum_auswahl_optionen
    fehler = 0

    def _ist(was, ist, soll):
        nonlocal fehler
        if ist == soll:
            print(f"   OK — {was}: {ist}")
        else:
            print(f"   FEHLER — {was}: {ist} statt {soll}")
            fehler += 1

    mind, maxd = dt.date(2008, 12, 30), dt.date(2026, 7, 21)

    jahre, _, _ = datum_auswahl_optionen(mind, maxd)
    _ist("Jahre von/bis", (jahre[0], jahre[-1]), (2008, 2026))

    # Am unteren Rand darf es nur Dezember geben, und erst ab dem 30.
    _, monate, _ = datum_auswahl_optionen(mind, maxd, jahr=2008)
    _ist("Monate im Anfangsjahr 2008", monate, [12])
    _, _, tage = datum_auswahl_optionen(mind, maxd, jahr=2008, monat=12)
    _ist("Tage im Dezember 2008", (tage[0], tage[-1]), (30, 31))

    # Am oberen Rand endet der Juli 2026 am 21.
    _, monate, _ = datum_auswahl_optionen(mind, maxd, jahr=2026)
    _ist("Monate im Endjahr 2026", (monate[0], monate[-1]), (1, 7))
    _, _, tage = datum_auswahl_optionen(mind, maxd, jahr=2026, monat=7)
    _ist("Tage im Juli 2026", (tage[0], tage[-1]), (1, 21))

    # Schaltjahr: 2024 hat einen 29. Februar, 2023 nicht.
    _, _, tage = datum_auswahl_optionen(mind, maxd, jahr=2024, monat=2)
    _ist("Februar 2024 (Schaltjahr)", tage[-1], 29)
    _, _, tage = datum_auswahl_optionen(mind, maxd, jahr=2023, monat=2)
    _ist("Februar 2023", tage[-1], 28)

    # Ein Monat mitten drin ist vollstaendig.
    _, _, tage = datum_auswahl_optionen(mind, maxd, jahr=2020, monat=1)
    _ist("Januar 2020", (tage[0], tage[-1]), (1, 31))

    # Vertauschte Raender duerfen nicht in eine leere Auswahl laufen.
    jahre, _, _ = datum_auswahl_optionen(maxd, mind)
    _ist("vertauschte Raender", (jahre[0], jahre[-1]), (2008, 2026))

    # Ein einziger moeglicher Tag: mind == maxd.
    tag = dt.date(2026, 7, 21)
    jahre, monate, tage = datum_auswahl_optionen(tag, tag, jahr=2026, monat=7)
    _ist("mind == maxd", (jahre, monate, tage), ([2026], [7], [21]))

    return fehler


def pruefe_kein_date_input():
    """Kein st.date_input mehr — die Zusage 'alle vier, nicht nur die gemeldete'.

    Gemeldet war der Zeitraum. Betroffen waren aber alle VIER Datumsfelder der
    Performance-Ansicht: Start/Ende im eigenen Zeitraum und Von/Bis am
    Balken-Chart. Ohne diese Pruefung baut jemand beim naechsten Mal wieder
    ein st.date_input ein, und die Ansicht ist an einer Stelle wieder
    englisch — ohne dass es auffaellt.

    Quelltext-Pruefung per AST, weil ein Widget, das nicht gerendert wird,
    per AppTest gar nicht sichtbar ist.
    """
    print("1b. Kein st.date_input mehr im Repo")
    dateien = [os.path.join(WURZEL, "streamlit_app.py")]
    modul_ordner = os.path.join(WURZEL, "modules")
    for name in sorted(os.listdir(modul_ordner)):
        if name.endswith(".py"):
            dateien.append(os.path.join(modul_ordner, name))

    treffer = []
    for pfad in dateien:
        with open(pfad, encoding="utf-8") as f:
            baum = ast.parse(f.read())
        for knoten in ast.walk(baum):
            if (isinstance(knoten, ast.Call)
                    and isinstance(knoten.func, ast.Attribute)
                    and knoten.func.attr == "date_input"):
                treffer.append(f"{os.path.basename(pfad)}:{knoten.lineno}")

    if treffer:
        print(f"   FEHLER — {len(treffer)} Aufruf(e) von st.date_input:")
        for t in treffer:
            print(f"      ! {t}")
        print("   Streamlit zeigt den Kalender nur auf Englisch — bitte "
              "shared.datum_waehler_de benutzen.")
        return 1
    print(f"   OK — {len(dateien)} Dateien, kein st.date_input")
    return 0


def _pruefe_zuruecksetzen(at):
    """Der Zuruecksetzen-Knopf im eigenen Zeitraum (NEU 11.08.2026).

    Geprueft wird die WIRKUNG, nicht nur die Existenz: Datum verstellen,
    Knopf druecken, danach muss wieder der Wert der Schnellwahl dastehen.
    Vorausgesetzt wird ein Lauf mit eingeschaltetem 'Eigener Zeitraum'.
    """
    print("   Zuruecksetzen-Knopf")

    def _jahr_feld(t):
        """Das Jahresfeld ist der Teil, der sich gefahrlos verstellen laesst.

        Tag und Monat sind in ihren Optionen an die Raender gebunden; das Jahr
        ist die Achse, auf der eine Verstellung immer moeglich ist, solange
        die Historie mehr als ein Jahr umfasst.
        """
        return next((s for s in at.selectbox
                     if s.key and s.key.startswith(t)
                     and s.key.endswith("_jahr")), None)

    knopf = next((b for b in at.button if b.key == "p_zeit_reset"), None)
    if knopf is None:
        print(f"      FEHLER — kein Knopf 'p_zeit_reset' "
              f"(vorhanden: {[b.key for b in at.button]})")
        return 1

    feld_start = _jahr_feld("p_sd")
    if feld_start is None:
        print("      FEHLER — kein Startjahr-Feld")
        return 1
    vorgabe = feld_start.value

    # ACHTUNG: .options liefert die BESCHRIFTUNGEN (Strings), .value den
    # Rohwert (int). Ohne die Umwandlung vergleicht man '2008' mit 2008,
    # setzt das Feld auf den String und wundert sich, dass sich nichts
    # aendert — beim Bau genau so passiert (17.08.2026).
    moeglich = [int(o) for o in feld_start.options if int(o) != vorgabe]
    if not moeglich:
        print(f"      UEBERSPRUNGEN — nur ein Jahr waehlbar ({vorgabe})")
        return 0
    verstellt = moeglich[0]

    feld_start.set_value(verstellt).run()
    ist = _jahr_feld("p_sd").value
    if ist != verstellt:
        print(f"      FEHLER — Verstellen wirkte nicht ({ist} statt {verstellt})")
        return 1

    # Knopf druecken -> zurueck auf die Vorgabe der Schnellwahl. Der Weg dahin
    # sind Zaehler-Keys (#4, Loesung A): p_sd_0_jahr wird zu p_sd_1_jahr, und
    # das frische Widget uebernimmt seine Vorbelegung.
    next(b for b in at.button if b.key == "p_zeit_reset").click().run()
    danach = _jahr_feld("p_sd").value
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
    # Die Quelltext-Pruefung laeuft ZUERST und ohne jedes Paket. Sie ist die
    # einzige hier, die auch in einer nackten Umgebung etwas beweist — und
    # genau die, die einen Rueckfall auf st.date_input verhindert.
    fehler = pruefe_kein_date_input()
    print()
    fehler += pruefe_datum_optionen()
    print()

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
        print("UEBERSPRUNGEN — streamlit.testing.v1 nicht verfuegbar; "
              "die Quelltext-Pruefung oben ist gelaufen")
        return 1 if fehler else 0

    fehler += (pruefe_zeitraum() + pruefe_balken_zeitraum() + pruefe_kein_pdf()
               + pruefe_benchmark_einmal() + pruefe_auftritt())
    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — Bedienelemente verhalten sich wie abgestimmt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
