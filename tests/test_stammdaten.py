"""Prueft die Mapping-Dateien als STAMMDATEN — Struktur, Schluessel, Namen.

HINTERGRUND (23.09.2026):
    Philip hat die ESG-Benchmarks in Mapping_Namen.xlsx geaendert; die
    Aenderung kam ohne Codeaenderung in den Broschueren an. Daraus die Frage,
    ob auch die NAMEN so zusammenhaengen. Die Antwort war: nur halb.

    Der Code griff bis heute POSITIONELL auf Mapping_Namen.xlsx zu —
    columns[0] (Anzeigename), columns[1] (CSV-Portfolioname), columns[3]
    (Benchmark). Das haelt genau so lange, wie niemand eine Spalte einfuegt,
    loescht oder verschiebt. Danach liest der Code lautlos die falsche Spalte
    weiter: keine Exception, keine Meldung, nur falscher Text in der
    Kundenbroschuere. Aufgefallen ist es bei der Frage, ob die tote Spalte
    "Duration" weg kann — sie steht an Position 2, und ihr Wegfall haette die
    Familien-Spalte zur Benchmark gemacht.

    Schritt 7 ist genau dieser Fall, und er ist der Grund fuer diesen Test:
    Auf dem Stand vor dem 23.09.2026 ist er ROT.

ZWEI SCHLUESSEL, NICHT EINER — der haeufigste Denkfehler an dieser Datei:
    Spalte A "Strategie auswaehlen"  = Anzeigename ("cVV konservativ")
    Spalte B "CSV-Portfolioname"      = Schluessel aus dem Bestandssystem
                                       ("Muster konservativ cVV").
    B kommt aus dem Bestandssystem und ist NICHT frei waehlbar. B schliesst
    die CSV-Dateien auf, Mapping_Honorarsatz ("Inhaber") und HISTORIE_AB.
    A schliesst die Anlagekriterien auf und ist Schluessel vieler
    Code-Konstanten.

    UND B IST NICHT DAS DATEINAMEN-PRAEFIX: zwei Strategien tragen einen
    Schraegstrich ("ETF Muster 100/100 offensiv"), der im Dateinamen zu "_"
    wird. Schritt 4 oeffnet deshalb die CSV und liest die Spalte
    "Portfolio Name" — wer gegen Dateinamen joint, haette zwei falsche
    Treffer und wuesste es nicht.

Geprueft wird:
  1. Struktur beider Dateien: Pflichtspalten unter EXAKTEM Namen, Zeilen da.
  2. Schluessel-Hygiene: A und B eindeutig, ohne Leerzeichen am Rand.
  3. Es gibt genau EINE Stammdaten-Datei; die drei Vorgaenger sind weg.
  4. B <-> "Portfolio Name" aus dem CSV-INHALT (Daten/ und Daten_PF/).
  5. Anlagekriterien vollstaendig (SCHWEIZ = bekannte Luecke).
  6. Namen <-> Code: jeder Strategiename, den der Code hart fuehrt, existiert
     im Mapping. Das faengt eine Umbenennung, die sonst still bliebe.
  7. Positions-Unabhaengigkeit: eine eingefuegte Spalte darf nichts aendern.
  8. Eine Strategie ohne CSV wird beim Namen genannt statt lautlos aus dem
     Auswahlfeld zu fallen.
  9. honorarsatz(): ein FEHLENDER Satz ist nicht dasselbe wie eingetragene
     0 % — sonst gibt es entweder Falschmeldungen oder stille Bruttozahlen.
 10. Nur modules/stammdaten.py liest eine Mapping-Datei (Syntaxbaum).
 11. Kein positioneller Spaltenzugriff, auch nicht ueber ein Alias.
 12. Gegenproben — jeder der Schritte 2, 6 und der Spaltenzugriff werden
     absichtlich verletzt und muessen anschlagen.

    python tests/test_stammdaten.py

Schritte 1-3 und 6 brauchen nur pandas. Schritt 4 braucht zusaetzlich die
echten Daten, Schritte 7 und 8 zusaetzlich streamlit (fuer modules.shared).
Fehlt etwas davon, wird der Schritt uebersprungen statt zu scheitern.
"""

import contextlib
import io
import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

try:
    import pandas as pd
except ImportError:
    print("UEBERSPRUNGEN — pandas nicht installiert")
    sys.exit(0)

from modules import stammdaten as stamm                        # noqa: E402

DATEI = os.path.join(WURZEL, stamm.PFAD)

# Die drei Vorgaengerdateien. Sie sind mit Etappe 4 entfernt worden und
# duerfen nicht zurueckkommen: Eine Mapping-Datei, die niemand liest, laedt
# dazu ein, sie zu pflegen und sich zu wundern, warum nichts passiert.
VORGAENGER = ("Mapping_Namen.xlsx", "Mapping_Honorarsatz.xlsx",
              "Mapping_Anlagekriterien.xlsx")

# Bekannte Luecke, kein Fehler: die beiden SCHWEIZ-Strategien stehen bewusst
# nicht in den Anlagekriterien — die Werte muessen aus dem Haus kommen.
# Dasselbe Muster wie NOCH_OFFEN in test_anlagekriterien.py.
KRITERIEN_NOCH_OFFEN = {"Schweiz_aktienorientiert", "Schweiz_substanzorientiert"}


def _werte(df, spalte):
    """Spaltenwerte als Liste von Strings, so wie der Code sie vergleicht."""
    return [str(v) for v in df[stamm.spalte(df, spalte)].tolist()]


# ─────────────────────────────────────────────────────────────────────────
# 1. Struktur
# ─────────────────────────────────────────────────────────────────────────
def _pruefe_struktur(sd):
    print("1. Struktur: Pflichtspalten unter exaktem Namen")
    fehler = 0
    for f in stamm.fehlende_spalten(sd, stamm.PFLICHT):
        fehler += 1
        print(f"   FEHLER — Pflichtspalte '{f}' fehlt")
    if len(sd) == 0:
        fehler += 1
        print("   FEHLER — keine Datenzeilen")
    # Die Kriterien-Spalten sind KEINE Pflicht (eine Strategie ohne Kasten ist
    # ein gueltiger Zustand), muessen aber existieren — sonst faellt der
    # Kasten ueberall weg, ohne dass es jemand merkt.
    for s in (stamm.SP_ANZEIGENAME, *stamm.SP_KRITERIEN):
        if stamm.finde_spalte(sd, s) is None:
            fehler += 1
            print(f"   FEHLER — Kriterien-Spalte '{s}' fehlt")
    if not fehler:
        print(f"   OK — {len(sd)} Zeilen, {len(sd.columns)} Spalten "
              f"aus {stamm.PFAD}")
    tot = [s for s in stamm.ENTFALLENE_SPALTEN
           if stamm.finde_spalte(sd, s) is not None]
    if tot:
        print(f"   Hinweis — {', '.join(tot)} steht noch in der Datei, "
              f"wird aber von keiner Codezeile gelesen")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 2. Schluessel-Hygiene
# ─────────────────────────────────────────────────────────────────────────
def _pruefe_schluessel_hygiene(namen):
    print("\n2. Schluessel-Hygiene: eindeutig, kein Leerzeichen am Rand")
    fehler = 0
    for spalte in (stamm.SP_ANZEIGE, stamm.SP_CSV_NAME):
        werte = _werte(namen, spalte)
        doppelt = {w for w in werte if werte.count(w) > 1}
        if doppelt:
            fehler += len(doppelt)
            print(f"   FEHLER — '{spalte}' doppelt: {sorted(doppelt)}")
        leer = [w for w in werte if not w.strip() or w.lower() == "nan"]
        if leer:
            fehler += len(leer)
            print(f"   FEHLER — '{spalte}': {len(leer)} leere Zelle(n)")
        rand = [w for w in werte if w != w.strip()]
        if rand:
            fehler += len(rand)
            # Der Vergleich in build_name_lookups ist exakt — ein Leerzeichen
            # am Rand laesst die Strategie lautlos aus dem Dropdown fallen.
            print(f"   FEHLER — '{spalte}' mit Leerzeichen am Rand: "
                  f"{[repr(w) for w in rand]}")
    if not fehler:
        print(f"   OK — {len(namen)} Zeilen, beide Schluessel sauber")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 3. B <-> Honorarsatz
# ─────────────────────────────────────────────────────────────────────────
def _pruefe_vorgaenger_weg():
    """Eine Datei, und nur diese eine.

    Bis zur Zusammenlegung standen die Stammdaten in drei Dateien. Ab
    Etappe 4 gibt es nur noch eine; die alten sind aus dem Repo entfernt.
    Dieser Schritt haelt beides fest — dass die neue da ist und dass keine
    der alten zurueckkommt. Eine Datei, die niemand liest, ist keine
    harmlose Altlast: Sie sieht aus wie eine Quelle.
    """
    print("\n3. Eine Stammdaten-Datei, und die Vorgaenger sind weg")
    fehler = 0
    if not os.path.exists(DATEI):
        fehler += 1
        print(f"   FEHLER — {stamm.PFAD} fehlt. Ohne sie hat die App keine "
              f"Stammdaten; eine Rueckfallebene gibt es seit Etappe 4 nicht "
              f"mehr.")
    else:
        print(f"   OK — {stamm.PFAD} vorhanden, Blatt '{stamm.BLATT}'")
    zurueck = [d for d in VORGAENGER if os.path.exists(os.path.join(WURZEL, d))]
    for d in zurueck:
        fehler += 1
        print(f"   FEHLER — {d} liegt wieder im Repo. Sie wird von keiner "
              f"Codezeile gelesen und gehoert entfernt, sonst pflegt sie "
              f"jemand ins Leere.")
    if not zurueck:
        print(f"   OK — keine der {len(VORGAENGER)} Vorgaengerdateien "
              f"liegt noch im Repo")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 4. B <-> CSV-Inhalt
# ─────────────────────────────────────────────────────────────────────────
def _csv_portfolionamen(ordner):
    """Liest 'Portfolio Name' aus dem INHALT jeder CSV des Ordners.

    Bewusst nicht aus dem Dateinamen: "ETF Muster 100/100 offensiv" heisst
    im Dateinamen "ETF Muster 100_100 offensiv".
    """
    namen = set()
    if not os.path.isdir(ordner):
        return None
    for datei in sorted(os.listdir(ordner)):
        if not datei.lower().endswith(".csv"):
            continue
        if any(sub in datei for sub in ("Stiftung",)):
            continue
        pfad = os.path.join(ordner, datei)
        try:
            kopf = pd.read_csv(pfad, comment="#", encoding="ISO-8859-1",
                               delimiter=";", decimal=",", thousands=".",
                               dtype=str, nrows=1)
        except Exception as ex:
            print(f"   FEHLER — {datei} nicht lesbar: {ex}")
            continue
        if "Portfolio Name" in kopf.columns and len(kopf):
            namen.add(str(kopf.loc[0, "Portfolio Name"]).strip())
    return namen


def _pruefe_csv_join(namen):
    print("\n4. CSV-Portfolioname <-> Spalte 'Portfolio Name' im CSV-Inhalt")
    b = {w.strip() for w in _werte(namen, stamm.SP_CSV_NAME)}
    fehler = 0
    gefunden = 0
    for ordner in ("Daten", "Daten_PF"):
        aus_csv = _csv_portfolionamen(ordner)
        if aus_csv is None:
            print(f"   UEBERSPRUNGEN — Ordner {ordner}/ fehlt")
            continue
        if not aus_csv:
            print(f"   UEBERSPRUNGEN — {ordner}/ enthaelt keine lesbaren CSV")
            continue
        gefunden += 1
        for waise in sorted(aus_csv - b):
            fehler += 1
            print(f"   FEHLER — {ordner}/: '{waise}' steht in keiner "
                  f"Mapping-Zeile -> faellt aus der Auswahl")
        for ohne in sorted(b - aus_csv):
            fehler += 1
            print(f"   FEHLER — '{ohne}' hat keine CSV in {ordner}/ "
                  f"-> verschwindet lautlos aus dem Dropdown")
        if not fehler:
            print(f"   OK — {ordner}/: {len(aus_csv)} Portfolios, deckungsgleich")
    if not gefunden:
        return 0
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 5. Anlagekriterien
# ─────────────────────────────────────────────────────────────────────────
def _pruefe_anlagekriterien(sd):
    """Welche Strategien haben einen Kriterien-Kasten?

    Ein Schluessel ins Leere ist seit der Zusammenlegung unmoeglich — die
    Kriterien stehen in derselben Zeile. Geblieben ist die Frage nach der
    VOLLSTAENDIGKEIT: eine neue Luecke muss auffallen, die bekannte nicht.
    """
    print("\n5. Anlagekriterien: erfasst und bekannte Luecke")
    sp_a = stamm.spalte(sd, stamm.SP_ANZEIGE)
    sp_n = stamm.spalte(sd, stamm.SP_ANZEIGENAME)
    fehler = 0
    ohne = sorted(str(r[sp_a]).strip() for _, r in sd.iterrows()
                  if pd.isna(r[sp_n]) or not str(r[sp_n]).strip())
    for s in [x for x in ohne if x not in KRITERIEN_NOCH_OFFEN]:
        fehler += 1
        print(f"   FEHLER — '{s}' hat keine Anlagekriterien "
              f"(neue Luecke, nicht die bekannte)")
    for s in sorted(KRITERIEN_NOCH_OFFEN):
        if s not in ohne:
            print(f"   Hinweis — '{s}' hat jetzt Kriterien; die bekannte "
                  f"Luecke ist geschlossen und kann aus dem Test raus")
    if not fehler:
        print(f"   OK — {len(sd) - len(ohne)} von {len(sd)} erfasst, "
              f"bekannte Luecke: {', '.join(sorted(KRITERIEN_NOCH_OFFEN))}")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 6. Namen <-> Code
# ─────────────────────────────────────────────────────────────────────────
def _pruefe_code_schluessel(namen):
    print("\n6. Strategienamen im Code existieren im Mapping")
    try:
        from modules import vorlagen_config as vc
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0

    anzeige = {w.strip() for w in _werte(namen, stamm.SP_ANZEIGE)}
    csv_namen = {w.strip() for w in _werte(namen, stamm.SP_CSV_NAME)}

    # (Beschreibung, Schluessel, Vergleichsmenge, Menge-Name)
    quellen = [("VORLAGEN_STRATEGIE", set(vc.VORLAGEN_STRATEGIE), anzeige, "Anzeigename"),
               ("EXPORT_NAME_STRATEGIE", set(vc.EXPORT_NAME_STRATEGIE), anzeige, "Anzeigename"),
               # HISTORIE_AB ist als einzige auf den CSV-Namen verschluesselt.
               ("HISTORIE_AB", set(vc.HISTORIE_AB), csv_namen, "CSV-Portfolioname")]
    for familie, liste in vc.FAMILIE_ALLE_STRATEGIEN.items():
        quellen.append((f"FAMILIE_ALLE_STRATEGIEN['{familie}']",
                        set(liste), anzeige, "Anzeigename"))

    fehler = 0
    for bezeichnung, schluessel, menge, mengenname in quellen:
        for s in sorted(schluessel - menge):
            fehler += 1
            print(f"   FEHLER — {bezeichnung}: '{s}' ist kein "
                  f"{mengenname} im Mapping")
    if not fehler:
        print(f"   OK — {sum(len(q[1]) for q in quellen)} Code-Schluessel "
              f"aus {len(quellen)} Konstanten loesen auf")

    # Die Familien selbst muessen der Code-Welt bekannt sein. "CVV" hat
    # bewusst keine eigene Familien-Vorlage, steht aber in VORLAGEN_FAMILIEN.
    familien = {w.strip() for w in _werte(namen, stamm.SP_FAMILIE) if w.strip()}
    bekannt = {k.lower() for k in vc.VORLAGEN_FAMILIEN}
    for f in sorted(familien):
        if f.lower() not in bekannt:
            fehler += 1
            print(f"   FEHLER — Familie '{f}' kennt VORLAGEN_FAMILIEN nicht")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 7. Positions-Unabhaengigkeit — DER Schritt, der vorher rot war
# ─────────────────────────────────────────────────────────────────────────
def _pruefe_positionsunabhaengig(namen):
    print("\n7. Eine eingefuegte Spalte darf die Zuordnung nicht verschieben")
    try:
        from modules.shared import build_name_lookups, csv_name_to_display
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0

    csv_namen = set(_werte(namen, stamm.SP_CSV_NAME))
    vorher_n, vorher_c, vorher_b = build_name_lookups(namen, csv_namen)

    # Die Verschiebung wird IM SPEICHER erzeugt — die Excel-Datei wird nicht
    # angefasst (sie gehoert Philip). Position 2 ist die Stelle, an der heute
    # "Duration" steht: genau dort wuerde ein Loeschen oder Einfuegen wirken.
    verschoben = namen.copy()
    verschoben.insert(2, "Testspalte", "x")

    nachher_n, nachher_c, nachher_b = build_name_lookups(verschoben, csv_namen)

    fehler = 0
    if vorher_n != nachher_n:
        fehler += 1
        print("   FEHLER — Anzeigenamen aendern sich mit der Spaltenposition")
    if vorher_c != nachher_c:
        fehler += 1
        print("   FEHLER — CSV-Zuordnung aendert sich mit der Spaltenposition")
    if vorher_b != nachher_b:
        fehler += 1
        abweichend = [k for k in vorher_b if vorher_b.get(k) != nachher_b.get(k)]
        print(f"   FEHLER — BENCHMARK-Text aendert sich mit der "
              f"Spaltenposition ({len(abweichend)} Strategien)")
        for k in abweichend[:2]:
            print(f"            '{k}': {str(vorher_b[k])[:40]!r} "
                  f"-> {str(nachher_b[k])[:40]!r}")

    probe = sorted(csv_namen)[0]
    if csv_name_to_display(probe, namen) != csv_name_to_display(probe, verschoben):
        fehler += 1
        print("   FEHLER — csv_name_to_display haengt an der Spaltenposition")

    if not fehler:
        print(f"   OK — {len(vorher_n)} Strategien, Ergebnis identisch "
              f"trotz eingefuegter Spalte")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 8. Eine Strategie ohne CSV wird benannt
# ─────────────────────────────────────────────────────────────────────────
def _pruefe_ohne_csv(namen):
    print("\n8. Eine Strategie ohne CSV wird benannt, nicht verschluckt")
    try:
        from modules import shared
    except ImportError as ex:          # streamlit/pandas fehlt -> ueberspringen
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0
    if not hasattr(shared, "strategien_ohne_csv"):
        # KEIN Ueberspringen: die Funktion ist unsere eigene. Waere sie weg,
        # verschwaenden Strategien wieder lautlos aus der Auswahl.
        print("   FEHLER — shared.strategien_ohne_csv fehlt (zurueckgebaut?)")
        return 1
    strategien_ohne_csv = shared.strategien_ohne_csv
    build_name_lookups = shared.build_name_lookups

    alle = set(_werte(namen, stamm.SP_CSV_NAME))
    fehler = 0

    offen = strategien_ohne_csv(namen, alle)
    if offen:
        fehler += len(offen)
        print(f"   FEHLER — ohne CSV: {offen}")
    else:
        print(f"   OK — alle {len(namen)} Zeilen haben eine CSV")

    # Gegenprobe: eine CSV wegnehmen. Die Strategie muss beim NAMEN genannt
    # werden — und weiterhin aus der Auswahl fallen, denn ohne Daten ist sie
    # nicht rechenbar. Gemeldet werden soll sie, nicht angeboten.
    sp_a = stamm.spalte(namen, stamm.SP_ANZEIGE)
    sp_b = stamm.spalte(namen, stamm.SP_CSV_NAME)
    opfer_csv = sorted(alle)[0]
    erwartet = str(namen.loc[namen[sp_b].astype(str) == opfer_csv, sp_a].iloc[0])
    rest = alle - {opfer_csv}

    gemeldet = strategien_ohne_csv(namen, rest)
    if list(gemeldet) != [erwartet]:
        fehler += 1
        print(f"   FEHLER — erwartet ['{erwartet}'], gemeldet {gemeldet}")
    else:
        print(f"   OK — Gegenprobe: '{erwartet}' wird beim Namen genannt")

    dn, _, _ = build_name_lookups(namen, rest)
    if erwartet in dn:
        fehler += 1
        print("   FEHLER — Strategie ohne Daten steht trotzdem in der Auswahl")
    else:
        print("   OK — und faellt weiterhin aus der Auswahl (Filter bleibt)")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 9. honorarsatz(): fehlend ist nicht dasselbe wie 0 %
# ─────────────────────────────────────────────────────────────────────────
def _pruefe_honorarsatz(honorar):
    print("\n9. honorarsatz(): ein fehlender Satz ist nicht 0 %")
    fehler = 0
    sp_i = stamm.spalte(honorar, stamm.SP_INHABER, stamm.DATEI_HONORAR)
    sp_s = stamm.spalte(honorar, stamm.SP_SATZ, stamm.DATEI_HONORAR)
    inhaber = str(honorar[sp_i].iloc[0])

    satz, gefunden = stamm.honorarsatz(honorar, inhaber)
    if not gefunden or satz <= 0:
        fehler += 1
        print(f"   FEHLER — '{inhaber}': {satz!r}, gefunden={gefunden}")
    else:
        print(f"   OK — '{inhaber}': {satz * 100:.4f} % p.a., gefunden=True")

    satz, gefunden = stamm.honorarsatz(honorar, "Diesen Namen gibt es nicht")
    if gefunden or satz != 0.0:
        fehler += 1
        print(f"   FEHLER — unbekannter Name liefert {satz!r}/{gefunden}")
    else:
        print("   OK — unbekannter Name: 0.0 und gefunden=False")

    # Der feine, aber entscheidende Unterschied (Audit 14.08.2026): Ein
    # EINGETRAGENER Satz von 0 % ist eine Angabe, kein Ausfall. Wer beides
    # gleich behandelt, erzeugt entweder Falschmeldungen oder verschluckt
    # den echten Fall.
    null = honorar.copy()
    null.loc[null.index[0], sp_s] = 0.0
    satz, gefunden = stamm.honorarsatz(null, inhaber)
    if satz != 0.0 or not gefunden:
        fehler += 1
        print(f"   FEHLER — eingetragene 0 %: {satz!r}/{gefunden}")
    else:
        print("   OK — eingetragene 0 % gilt als gefunden (keine Falschmeldung)")

    satz, gefunden = stamm.honorarsatz(None, inhaber)
    if gefunden or satz != 0.0:
        fehler += 1
        print(f"   FEHLER — ohne Mapping: {satz!r}/{gefunden}")
    else:
        print("   OK — ohne Mapping: 0.0 und gefunden=False")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 10. EIN Lesepfad — maschinell gehalten
# ─────────────────────────────────────────────────────────────────────────
def _read_excel_stellen(quelle, name):
    """Alle Aufrufe von read_excel im Syntaxbaum, als (Zeile, Datei)."""
    import ast
    treffer = []
    for k in ast.walk(ast.parse(quelle, filename=name)):
        if not isinstance(k, ast.Call):
            continue
        f = k.func
        wie = (f.attr if isinstance(f, ast.Attribute)
               else f.id if isinstance(f, ast.Name) else None)
        if wie == "read_excel":
            treffer.append((k.lineno, name))
    return treffer


def _pruefe_ein_lesepfad():
    """Nur EIN Modul darf eine Mapping-Datei lesen.

    Die Hausregel lautet "Loader oder Mathematik nie duplizieren". Bis zum
    23.09.2026 stand sie nur in der Doku — und war zweimal gebrochen: die
    Honorarsatz-Suche gab es doppelt, die Anlagekriterien hatten einen
    eigenen Loader. Ein Satz in einer Datei haelt niemanden auf, ein Test
    schon.
    """
    print("\n10. Nur modules/stammdaten.py liest eine Mapping-Datei")
    ordner = os.path.join(WURZEL, "modules")
    fehler = 0
    gefunden = []
    for datei in sorted(os.listdir(ordner)):
        if not datei.endswith(".py"):
            continue
        quelle = io.open(os.path.join(ordner, datei), encoding="utf-8").read()
        for zeile, _ in _read_excel_stellen(quelle, datei):
            gefunden.append((datei, zeile))
    fremd = [(d, z) for d, z in gefunden if d != "stammdaten.py"]
    for d, z in fremd:
        fehler += 1
        print(f"   FEHLER — {d}:{z} liest selbst eine Excel. Der Lesepfad "
              f"gehoert in stammdaten.lade().")
    if not fremd:
        eigene = len([1 for d, _ in gefunden if d == "stammdaten.py"])
        print(f"   OK — {eigene} Aufruf(e), alle in stammdaten.py")

    # Gegenprobe: Die Suche muss einen eingebauten Verstoss auch finden.
    probe = "import pandas as pd\nx = pd.read_excel('irgendwas.xlsx')\n"
    if len(_read_excel_stellen(probe, "<probe>")) != 1:
        fehler += 1
        print("   FEHLER — die Syntaxbaum-Suche findet einen eingebauten "
              "Verstoss nicht; sie misst nichts")
    else:
        print("   OK — Gegenprobe: ein eingebauter Verstoss wird gefunden")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 11. Positioneller Spaltenzugriff — maschinell ausgeschlossen
# ─────────────────────────────────────────────────────────────────────────
def _positionelle_zugriffe(quelle, name):
    """Numerischer Zugriff auf eine Spaltenliste, als (Objekt, Zeile).

    Erkennt BEIDE Schreibweisen:
        df.columns[3]
        cols = df.columns ... cols[3]
    Die zweite ist die gefaehrliche: Sie sieht nicht nach Spaltenzugriff aus
    und ist beim Umbau am 23.09.2026 durchs Raster gefallen.
    """
    import ast
    baum = ast.parse(quelle, filename=name)
    aliase = {}
    for k in ast.walk(baum):
        if (isinstance(k, ast.Assign)
                and isinstance(k.value, ast.Attribute)
                and k.value.attr == "columns"):
            for z in k.targets:
                if isinstance(z, ast.Name):
                    aliase[z.id] = k.lineno
    treffer = []
    for k in ast.walk(baum):
        if not isinstance(k, ast.Subscript):
            continue
        if not (isinstance(k.slice, ast.Constant)
                and isinstance(k.slice.value, int)):
            continue
        ziel = k.value
        if isinstance(ziel, ast.Attribute) and ziel.attr == "columns":
            basis = (ziel.value.id if isinstance(ziel.value, ast.Name)
                     else "?")
            treffer.append((f"{basis}.columns", k.lineno))
        elif isinstance(ziel, ast.Name) and ziel.id in aliase:
            treffer.append((ziel.id, k.lineno))
    return treffer


# Bewusst erlaubt: eine PowerPoint-Tabelle hat echte Spaltenobjekte, dort ist
# der Index die natuerliche Adresse. Wer einen Eintrag hinzufuegt, hat sich
# das ueberlegt — genau das ist der Zweck der Liste.
POSITIONELL_ERLAUBT = {("test_ytd_kachel.py", "tab.columns")}


def _pruefe_kein_positioneller_zugriff():
    """Spalten werden ueber ihren NAMEN gelesen, nicht ueber ihre Position.

    Am 23.09.2026 zweimal schmerzhaft gelernt: Erst stand der Inhalt der
    Duration-Spalte in der Benchmark-Fussnote, dann — nach dem Umbau — der
    HONORARSATZ, weil ``nm_cols = name_mapping.columns`` mit ``nm_cols[3]``
    beim Umstellen uebersehen wurde. Beide Male war nichts zu sehen ausser
    einem falschen Text im Kundendokument.
    """
    print("\n11. Kein positioneller Spaltenzugriff (auch nicht per Alias)")
    fehler = 0
    gefunden = []
    for ordner in ("modules", "tests"):
        wurz = os.path.join(WURZEL, ordner)
        for datei in sorted(os.listdir(wurz)):
            if not datei.endswith(".py"):
                continue
            quelle = io.open(os.path.join(wurz, datei), encoding="utf-8").read()
            for objekt, zeile in _positionelle_zugriffe(quelle, datei):
                if (datei, objekt) in POSITIONELL_ERLAUBT:
                    continue
                gefunden.append((datei, objekt, zeile))
    for datei, objekt, zeile in gefunden:
        fehler += 1
        print(f"   FEHLER — {datei}:{zeile} greift positionell zu "
              f"({objekt}[...]). Spalten ueber den NAMEN lesen.")
    if not gefunden:
        print(f"   OK — keiner, ausser {len(POSITIONELL_ERLAUBT)} "
              f"ausdruecklich erlaubten")

    # Gegenprobe: beide Schreibweisen muessen gefunden werden.
    probe = ("a = df.columns[3]\n"
             "cols = other.columns\n"
             "b = cols[0]\n")
    if len(_positionelle_zugriffe(probe, "<probe>")) != 2:
        fehler += 1
        print("   FEHLER — die Suche findet die eingebauten Verstoesse "
              "nicht; sie misst nichts")
    else:
        print("   OK — Gegenprobe: direkter UND per Alias versteckter "
              "Zugriff werden gefunden")
    return fehler


# ─────────────────────────────────────────────────────────────────────────
# 12. Gegenproben — misst der Test wirklich?
# ─────────────────────────────────────────────────────────────────────────
def _gegenproben(namen):
    print("\n12. Gegenproben: absichtlich verletzen, muss anschlagen")
    fehler = 0

    # (a) Ein Leerzeichen am Rand muss Schritt 2 melden.
    kaputt = namen.copy()
    sp_a = stamm.spalte(kaputt, stamm.SP_ANZEIGE)
    kaputt.loc[kaputt.index[0], sp_a] = str(kaputt.loc[kaputt.index[0], sp_a]) + " "
    if _still(_pruefe_schluessel_hygiene, kaputt) == 0:
        fehler += 1
        print("   FEHLER — Leerzeichen am Rand blieb unbemerkt")
    else:
        print("   OK — Leerzeichen am Rand wird gemeldet")

    # (b) Eine umbenannte Strategie muss Schritt 6 melden.
    kaputt = namen.copy()
    kaputt.loc[kaputt.index[0], sp_a] = "Voellig neuer Name"
    if _still(_pruefe_code_schluessel, kaputt) == 0:
        fehler += 1
        print("   FEHLER — Umbenennung blieb unbemerkt")
    else:
        print("   OK — Umbenennung wird gemeldet")

    # (c) Eine umbenannte SPALTE muss werfen, nicht still None liefern.
    kaputt = namen.rename(columns={stamm.spalte(namen, stamm.SP_BENCHMARK): "Benchmarkk"})
    try:
        stamm.spalte(kaputt, stamm.SP_BENCHMARK)
        fehler += 1
        print("   FEHLER — fehlende Spalte wurde nicht gemeldet")
    except stamm.StammdatenFehler as ex:
        if stamm.SP_BENCHMARK in str(ex) and stamm.DATEI_STRATEGIEN in str(ex):
            print("   OK — fehlende Spalte wirft und nennt Datei und Spalte")
        else:
            fehler += 1
            print(f"   FEHLER — Meldung nennt nicht Datei und Spalte: {ex}")

    return fehler


def _still(funktion, *args):
    """Ruft eine Pruefung auf, ohne ihre Ausgabe mitzudrucken — sonst stuenden
    in den Gegenproben Zeilen, die wie echte Fehler aussehen."""
    with contextlib.redirect_stdout(io.StringIO()):
        return funktion(*args)


# ─────────────────────────────────────────────────────────────────────────
def main():
    # EIN Ladeaufruf — genau der, den auch die App nimmt. Der Test prueft
    # damit den echten Lesepfad und nicht eine eigene Nachbildung.
    sd = stamm.lade()
    if sd is None or sd.empty:
        print(f"FEHLER: Keine Stammdaten ladbar — weder {stamm.PFAD} noch "
              f"die drei Vorgaengerdateien.")
        return 1
    honorar = stamm.honorar_frame(sd)

    fehler = (_pruefe_struktur(sd)
              + _pruefe_schluessel_hygiene(sd)
              + _pruefe_vorgaenger_weg()
              + _pruefe_csv_join(sd)
              + _pruefe_anlagekriterien(sd)
              + _pruefe_code_schluessel(sd)
              + _pruefe_positionsunabhaengig(sd)
              + _pruefe_ohne_csv(sd)
              + _pruefe_honorarsatz(honorar)
              + _pruefe_ein_lesepfad()
              + _pruefe_kein_positioneller_zugriff()
              + _gegenproben(sd))

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print(f"BESTANDEN — {len(sd)} Strategien, Stammdaten konsistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
