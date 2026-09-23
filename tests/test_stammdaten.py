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
    Spalte B "Honorarsatz Mapping"   = CSV-PORTFOLIONAME ("Muster konservativ
                                       cVV"), trotz des Spaltenkopfs.
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
  3. B <-> Mapping_Honorarsatz["Inhaber"], BEIDSEITIG vollstaendig.
  4. B <-> "Portfolio Name" aus dem CSV-INHALT (Daten/ und Daten_PF/).
  5. Anlagekriterien-Schluessel sind in A bekannt (SCHWEIZ = bekannte Luecke).
  6. Namen <-> Code: jeder Strategiename, den der Code hart fuehrt, existiert
     im Mapping. Das faengt eine Umbenennung, die sonst still bliebe.
  7. Positions-Unabhaengigkeit: eine eingefuegte Spalte darf nichts aendern.
  8. Gegenproben — jeder der Schritte 2, 6 und der Spaltenzugriff werden
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

NAMEN = os.path.join(WURZEL, stamm.DATEI_STRATEGIEN)
HONORAR = os.path.join(WURZEL, stamm.DATEI_HONORAR)
KRITERIEN = os.path.join(WURZEL, "Mapping_Anlagekriterien.xlsx")

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
def _pruefe_struktur(namen, honorar):
    print("1. Struktur: Pflichtspalten unter exaktem Namen")
    fehler = 0
    for df, pflicht, datei in ((namen, stamm.PFLICHT_STRATEGIEN, stamm.DATEI_STRATEGIEN),
                               (honorar, stamm.PFLICHT_HONORAR, stamm.DATEI_HONORAR)):
        fehlt = stamm.fehlende_spalten(df, pflicht, datei)
        if fehlt:
            fehler += len(fehlt)
            for f in fehlt:
                print(f"   FEHLER — {datei}: Spalte '{f}' fehlt")
        if len(df) == 0:
            fehler += 1
            print(f"   FEHLER — {datei}: keine Datenzeilen")
    if not fehler:
        print(f"   OK — {stamm.DATEI_STRATEGIEN} {len(namen)} Zeilen, "
              f"{stamm.DATEI_HONORAR} {len(honorar)} Zeilen")
    # Tote Spalten NICHT als Fehler, aber benennen: wer hier joint, joint ins
    # Leere. "Honorarsatz Brutto" ist zusaetzlich veraltet (comdirect).
    for datei, df in ((stamm.DATEI_STRATEGIEN, namen), (stamm.DATEI_HONORAR, honorar)):
        tot = [s for s in stamm.TOTE_SPALTEN.get(datei, ())
               if stamm.finde_spalte(df, s) is not None]
        if tot:
            print(f"   Hinweis — {datei}: {', '.join(tot)} "
                  f"wird von keiner Codezeile gelesen")
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
def _pruefe_honorar_join(namen, honorar):
    print("\n3. CSV-Portfolioname <-> Mapping_Honorarsatz['Inhaber']")
    b = {w.strip() for w in _werte(namen, stamm.SP_CSV_NAME)}
    inhaber = {w.strip() for w in _werte(honorar, stamm.SP_INHABER)}
    fehler = 0
    for fehlend in sorted(b - inhaber):
        fehler += 1
        # Genau dieser Fall lief bis zum Audit 14.08.2026 still auf 0 %.
        print(f"   FEHLER — '{fehlend}' hat keine Zeile im Honorarsatz-Mapping")
    for waise in sorted(inhaber - b):
        fehler += 1
        print(f"   FEHLER — '{waise}' steht im Honorarsatz-Mapping, "
              f"aber in keiner Strategie")
    if not fehler:
        print(f"   OK — {len(b)} Namen, beidseitig vollstaendig")
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
def _pruefe_anlagekriterien(namen):
    print("\n5. Anlagekriterien-Schluessel sind im Mapping bekannt")
    if not os.path.exists(KRITERIEN):
        print("   UEBERSPRUNGEN — Mapping_Anlagekriterien.xlsx fehlt")
        return 0
    krit = pd.read_excel(KRITERIEN)
    a = {w.strip() for w in _werte(namen, stamm.SP_ANZEIGE)}
    schluessel = {str(v).strip() for v in krit[stamm.SP_ANZEIGE].tolist()}
    fehler = 0
    for waise in sorted(schluessel - a):
        fehler += 1
        print(f"   FEHLER — Anlagekriterien kennen '{waise}', "
              f"das Mapping nicht")
    offen = sorted(a - schluessel)
    unerwartet = [s for s in offen if s not in KRITERIEN_NOCH_OFFEN]
    for s in unerwartet:
        fehler += 1
        print(f"   FEHLER — '{s}' hat keine Anlagekriterien "
              f"(neue Luecke, nicht die bekannte)")
    if not fehler:
        print(f"   OK — {len(schluessel)} erfasst, bekannte Luecke: "
              f"{', '.join(sorted(KRITERIEN_NOCH_OFFEN))}")
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
# 8. Gegenproben — misst der Test wirklich?
# ─────────────────────────────────────────────────────────────────────────
def _gegenproben(namen):
    print("\n8. Gegenproben: absichtlich verletzen, muss anschlagen")
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
    for pfad in (NAMEN, HONORAR):
        if not os.path.exists(pfad):
            print(f"FEHLER: {pfad} fehlt")
            return 1
    namen = pd.read_excel(NAMEN)
    honorar = pd.read_excel(HONORAR)

    fehler = (_pruefe_struktur(namen, honorar)
              + _pruefe_schluessel_hygiene(namen)
              + _pruefe_honorar_join(namen, honorar)
              + _pruefe_csv_join(namen)
              + _pruefe_anlagekriterien(namen)
              + _pruefe_code_schluessel(namen)
              + _pruefe_positionsunabhaengig(namen)
              + _gegenproben(namen))

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print(f"BESTANDEN — {len(namen)} Strategien, Stammdaten konsistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
