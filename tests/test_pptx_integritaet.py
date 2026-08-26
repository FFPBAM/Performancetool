# -*- coding: utf-8 -*-
"""Paket-Integritaet der gebauten Broschueren — die Schichten aus #16.

WARUM ES DIESE SUITE GIBT (26.08.2026): Ein Testuser meldete Broschueren, die
sich herunterladen, aber nicht oeffnen liessen ("PowerPoint kann ... leider
nicht lesen"). Vier vorhandene Suiten bauten dieselben Dateien und meldeten
gruen — weil sie alle mit python-pptx zurueckgelesen haben. python-pptx ist
TOLERANT gegen die eigene Korruption (#16): Es oeffnet die kaputte Datei
klaglos, PowerPoint verweigert sie.

Die Ursache war eine 1:n-Beziehung, die 1:1 sein muss: Beim Duplizieren einer
Folie (Familie "Thema", Vergleichsportfolio) teilten sich zwei Chart-Parts
DASSELBE chartUserShapes-Drawing, dieselbe eingebettete Excel-Mappe und
dieselben style/colors-Teile, statt eigene Kopien zu bekommen
(`pptx_helpers.clone_chart_part`). Schritt 1 prueft genau das mit L5.

Geprueft wird OHNE python-pptx-Semantik, direkt am ZIP und am XML:
  L1  das Archiv ist unversehrt              (zipfile.testzip)
  L2  jeder XML-Teil parst                   (findet ZIP-Muell aus #12 Bug 2)
  L3  [Content_Types].xml deckt jeden Teil
  L4  jedes Relationship-Ziel existiert
  L5  Chart-Sub-Teile gehoeren zu GENAU EINEM Chart   <- der gemeldete Fehler
  L6  keine nan/inf als xsd:double im XML

Schritt 2 ist die GEGENPROBE: Sie stellt das alte Teilen-statt-Kopieren im
Arbeitsspeicher wieder her und verlangt, dass L5 dann ROT wird. Ein Test, der
nur gruen ist, beweist nichts.

    python tests/test_pptx_integritaet.py [ausgabeordner]

NICHT geprueft werden kann hier, ob PowerPoint die Datei wirklich oeffnet —
das geht nur per COM auf einem Rechner mit Office und ist deshalb Werkzeug,
nicht Pruefstein (#16, Layer 6). Nach Aenderungen am Bau bitte stichprobenartig
in ECHTEM PowerPoint oeffnen.
"""

import collections
import os
import posixpath
import re
import sys
import tempfile
import traceback
import zipfile

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
sys.path.insert(0, os.path.join(WURZEL, "tests"))
os.chdir(WURZEL)

try:
    from lxml import etree
except ImportError:
    print("UEBERSPRUNGEN — lxml nicht installiert")
    sys.exit(0)

try:
    import test_export_smoke as SMOKE
    from modules import pptx_helpers
    from modules.portfolioanalyse import (
        VORLAGEN_FAMILIEN, FAMILIE_ALLE_STRATEGIEN, _familien_portfolios,
        _familie_fuer_strategie, duration_info_aus_bestand,
    )
except ImportError as ex:
    print("UEBERSPRUNGEN — Abhaengigkeit fehlt: %s" % ex)
    sys.exit(0)

R_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CT_NS = "{http://schemas.openxmlformats.org/package/2006/content-types}"

# Sub-Teile eines Charts. Jeder davon gehoert zu GENAU EINEM Chart — so liegt es
# in allen sechs Vorlagen, und so verlangt es PowerPoint.
SUB_PRAEFIXE = ("ppt/drawings/", "ppt/embeddings/", "ppt/charts/")

# Beide SCHWEIZ-Strategien: Sie laufen unter der Familie "Thema" und werden vom
# Smoke-Test deshalb NIE gebaut (der nimmt per next() die erste Thema-Strategie
# und kennt in Teil 2 nur Offensiv/Pro/Pro Dividende). Genau eine von ihnen war
# die gemeldete kaputte Datei.
SCHWEIZ = ["Schweiz_aktienorientiert", "Schweiz_substanzorientiert"]

NICHT_ENDLICH = re.compile(rb'val="(-?(?:nan|inf|NaN|Infinity)[^"]*)"', re.I)


def _eltern_je_teil(z, namen):
    """{Zielteil: [Elternteile]} ueber das ganze Paket."""
    eltern = collections.defaultdict(list)
    for n in namen:
        if not n.endswith(".rels"):
            continue
        elter = posixpath.basename(n)[:-5] or "/"
        basis = posixpath.dirname(posixpath.dirname(n))
        for rel in etree.fromstring(z.read(n)).findall(R_NS + "Relationship"):
            if rel.get("TargetMode") == "External":
                continue
            ziel = posixpath.normpath(posixpath.join(basis, rel.get("Target")))
            eltern[ziel].append(elter)
    return eltern


def pruefe_paket(pfad):
    """Gibt eine Liste von Befunden zurueck — leer heisst sauber."""
    befunde = []
    z = zipfile.ZipFile(pfad)
    namen = z.namelist()

    # L1 — Archiv unversehrt
    kaputt = z.testzip()
    if kaputt:
        return ["L1 Archiv beschaedigt ab '%s'" % kaputt]

    # L2 — jeder XML-Teil parst; ZIP-Muell in XML ist #12 Bug 2
    for n in namen:
        if not (n.endswith(".xml") or n.endswith(".rels")):
            continue
        roh = z.read(n)
        if roh[:2] == b"PK":
            befunde.append("L2 %s: ZIP-Header statt XML (#12 Bug 2)" % n)
            continue
        try:
            etree.fromstring(roh)
        except Exception as ex:
            befunde.append("L2 %s: nicht parsbar — %s" % (n, str(ex)[:80]))

    # L3 — Content-Types decken jeden Teil
    ct = etree.fromstring(z.read("[Content_Types].xml"))
    defaults = set()
    for dflt in ct.findall(CT_NS + "Default"):
        defaults.add((dflt.get("Extension") or "").lower())
    overrides = set()
    for ovr in ct.findall(CT_NS + "Override"):
        overrides.add((ovr.get("PartName") or "").lstrip("/"))
    for n in namen:
        if n == "[Content_Types].xml":
            continue
        if n not in overrides and n.rsplit(".", 1)[-1].lower() not in defaults:
            befunde.append("L3 %s: kein Content-Type" % n)
    for p in sorted(overrides - set(namen)):
        befunde.append("L3 Override ohne Datei: %s" % p)

    # L4 — Relationship-Ziele existieren
    eltern = _eltern_je_teil(z, namen)
    for ziel in sorted(eltern):
        if ziel not in namen:
            befunde.append("L4 totes Relationship-Ziel: %s" % ziel)

    # L5 — Chart-Sub-Teile gehoeren zu GENAU EINEM Chart.
    # Der Pruefstein fuer den Fehler vom 26.08.2026: clone_chart_part hat die
    # Sub-Parts geteilt statt kopiert. python-pptx stoert das nicht,
    # PowerPoint verweigert die Datei.
    for ziel, wer in sorted(eltern.items()):
        if not ziel.startswith(SUB_PRAEFIXE):
            continue
        chart_eltern = sorted(set(e for e in wer if e.startswith("chart")))
        if len(chart_eltern) > 1:
            befunde.append(
                "L5 %s haengt an %d Charts (%s) — muss 1:1 sein"
                % (ziel, len(chart_eltern), ", ".join(chart_eltern)))

    # L6 — nan/inf als xsd:double
    for n in namen:
        if not n.endswith(".xml"):
            continue
        treffer = NICHT_ENDLICH.findall(z.read(n))
        if treffer:
            befunde.append(
                "L6 %s: %d nicht-endliche Zahl(en), z.B. val=%s"
                % (n, len(treffer), treffer[0].decode("ascii", "replace")))
    return befunde


def _faelle(d):
    """(Bezeichnung, portfolios, familie) — alle Familien, SCHWEIZ, Duplikate."""
    raus = []
    for familie in sorted(VORLAGEN_FAMILIEN):
        strategie = next((n for n in d["namen"]
                          if _familie_fuer_strategie(d["nm"], n) == familie), None)
        if strategie is None:
            continue
        alle = FAMILIE_ALLE_STRATEGIEN.get(familie)
        if alle:
            portfolios, fehlend = _familien_portfolios(
                alle, d["namen"], d["d2c"], d["pf_data"], duration_info_aus_bestand)
            if fehlend:
                continue
        else:
            portfolios = [SMOKE._portfolio(strategie, d)]
        raus.append((familie, portfolios, familie))

    for name in SCHWEIZ:
        if name in d["d2c"]:
            raus.append((name, [SMOKE._portfolio(name, d)], "Thema"))

    vorhanden = [n for n in SMOKE.THEMA_STRATEGIEN if n in d["d2c"]]
    for anzahl in (2, 3):
        if len(vorhanden) >= anzahl:
            raus.append(("Thema x%d" % anzahl,
                         [SMOKE._portfolio(n, d) for n in vorhanden[:anzahl]],
                         "Thema"))

    # Der gemeldete Fall im Wortlaut: SCHWEIZ mit Vergleichsportfolio.
    if SCHWEIZ[0] in d["d2c"] and "Pro" in d["d2c"]:
        raus.append(("%s + Vergleich" % SCHWEIZ[0],
                     [SMOKE._portfolio(SCHWEIZ[0], d), SMOKE._portfolio("Pro", d)],
                     "Thema"))
    return raus


def _geteilt_wie_frueher(prs, source_chart_part):
    """Die Fassung vor dem 26.08.2026 — Sub-Parts per Referenz statt Kopie."""
    paket = source_chart_part.package
    neu = type(source_chart_part).load(
        pptx_helpers._naechste_partname(paket, source_chart_part.partname),
        source_chart_part.content_type, paket, source_chart_part.blob)
    for rel in source_chart_part.rels.values():
        if rel.is_external:
            neu.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
        else:
            neu.relate_to(rel.target_part, rel.reltype)
    return neu


def main():
    ausgabe = (sys.argv[1] if len(sys.argv) > 1
               else tempfile.mkdtemp(prefix="ffpb_integritaet_"))
    os.makedirs(ausgabe, exist_ok=True)

    d = SMOKE._daten()
    faelle = _faelle(d)
    print("Datenstand %s — %d Faelle, Ausgabe: %s\n" % (d["tag"], len(faelle), ausgabe))

    fehler = 0

    # ── Schritt 1: bauen und die Schichten pruefen ──────────────────────
    print("Schritt 1 — Broschueren bauen, Schichten L1-L6 pruefen")
    print("%-34s %6s  Befund" % ("Fall", "Teile"))
    print("-" * 74)
    for bezeichnung, portfolios, familie in faelle:
        datei = re.sub(r"[^A-Za-z0-9_+-]", "_", bezeichnung) + ".pptx"
        try:
            ziel, _groesse, _meld = SMOKE._bauen(portfolios, familie, d, ausgabe, datei)
        except Exception as ex:
            fehler += 1
            print("%-34s %6s  BAU GESCHEITERT: %s: %s"
                  % (bezeichnung, "-", type(ex).__name__, ex))
            traceback.print_exc()
            continue
        befunde = pruefe_paket(ziel)
        teile = len(zipfile.ZipFile(ziel).namelist())
        if befunde:
            fehler += 1
            print("%-34s %6d  %d BEFUND(E)" % (bezeichnung, teile, len(befunde)))
            for b in befunde[:6]:
                print("    ! %s" % b)
            if len(befunde) > 6:
                print("    ! … und %d weitere" % (len(befunde) - 6))
        else:
            print("%-34s %6d  sauber" % (bezeichnung, teile))

    # ── Schritt 2: Gegenprobe ───────────────────────────────────────────
    # Der alte Fehler wird im Arbeitsspeicher wiederhergestellt (Sub-Parts
    # teilen statt kopieren). Faellt L5 dann NICHT an, misst der Test nichts.
    print("\nSchritt 2 — Gegenprobe: altes Teilen-statt-Kopieren zurueckdrehen")
    # WICHTIG: nur die Familie "Thema" dupliziert Folien (Modus "dupliziert").
    # CVV/ESG/ETF/comdirect fuehren zwar mehrere Strategien, haben ihre Folien
    # aber fest in der Vorlage — dort laeuft clone_chart_part gar nicht, und die
    # Gegenprobe bliebe wirkungslos.
    dupl = next((f for f in faelle if f[2] == "Thema" and len(f[1]) > 1), None)
    if dupl is None:
        print("  UEBERSPRUNGEN — kein Duplikat-Fall (Thema, >1 Strategie)")
    else:
        original = pptx_helpers.clone_chart_part
        pptx_helpers.clone_chart_part = _geteilt_wie_frueher
        try:
            ziel, _g, _m = SMOKE._bauen(dupl[1], dupl[2], d, ausgabe,
                                        "_gegenprobe.pptx")
            befunde = [b for b in pruefe_paket(ziel) if b.startswith("L5")]
        finally:
            pptx_helpers.clone_chart_part = original
        if befunde:
            print("  OK — L5 schlaegt an: %d geteilte Sub-Teile" % len(befunde))
            print("       z.B. %s" % befunde[0])
        else:
            fehler += 1
            print("  FEHLGESCHLAGEN — L5 bleibt still, obwohl der Fehler drin "
                  "ist. Der Pruefstein misst nicht, was er messen soll.")

    print()
    if fehler:
        print("FEHLGESCHLAGEN — %d Fall/Faelle" % fehler)
        return 1
    print("BESTANDEN — alle Pakete strukturell sauber, Gegenprobe greift")
    print("Hinweis: stichprobenartig in ECHTEM PowerPoint oeffnen (#16, Layer 6).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
