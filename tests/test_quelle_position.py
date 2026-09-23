"""Regressionstest: die Quellenangabe darf nicht im Disclaimer liegen (12.08.2026).

GEMELDET wurde eine Folie — die Wertentwicklungs-Folie der Offensiv-Broschuere:
"Quelle: Eigene Berechnung, Stand 20.07.2026" wird vom Disclaimer-Fliesstext
ueberdruckt. NACHGEMESSEN am PowerPoint-Rendering waren es alle: In allen sechs
Vorlagen liegt die Textbox "Quelle" auf den Emu identisch bei

    Quelle   23,30-28,10 x 13,89-14,19 cm
    Fussnote 12,50-28,10 x 11,16-16,20 cm     <- die Quelle liegt DARIN

und der Disclaimer reicht gerendert bis 14,47 cm. Betroffen sind 16 Folien:

    Vorlage_cVV_Infoboard.pptx   F8, F10, F12, F14, F16
    Vorlage_ESG.pptx             F17, F19, F21, F23
    Vorlage_comdirect.pptx       F7, F9, F11
    Vorlage_ETF.pptx             F17, F19
    Vorlage_Thema.pptx           F12          (Offensiv, Pro, Pro Dividende)
    Vorlage_FFPB.pptx            F11

Alle 16 tragen die Rolle "wertentwicklung" und laufen durch EINE Funktion,
pptx_slides.fill_wertentwicklung_slide — deshalb genuegt dort eine Korrektur
(WE_QUELLE_TOP_CM).

ZWEI URSACHEN, die sich addieren:

  1. Die Vorlagen-Position der Quelle liegt im Fussnotenfeld. Das faellt nicht
     auf, solange der Disclaimer kurz genug bleibt — er ist es nie gewesen.
  2. Der Disclaimer ist in der Vorlage HART umbrochen: Die Absaetze sind von
     Hand auf die Boxbreite gebrochen (laengste Vorlagenzeile 149 Zeichen bei
     6 pt). WE_DISCLAIMER_REPLACEMENTS ersetzte einen davon durch 189 Zeichen
     — der Absatz bricht um, ALLES darunter rutscht eine Zeile tiefer. Der
     Kommentar ueber der Konstanten versprach seit Juli 2026, die Ersatztexte
     seien "auf aehnliche Laenge kalibriert, damit das Layout haelt".
     Gemessen hat das nie jemand. Schritt 2 misst es.

Geprueft wird in drei Schritten:

  Schritt 1 — an allen sechs VORLAGEN: der Fussnoten-Textblock wird mit den
                     echten Ersatztexten nachgerechnet, und WE_QUELLE_TOP_CM
                     muss darunter liegen. Eine neue Vorlage mit laengerem
                     Disclaimer faellt hier auf.
  Schritt 2 — jeder Ersatztext passt in eine Zeile (WE_FUSSNOTE_ZEILE_MAX).
                     Das ist der Test, der den Fehler verhindert haette.
  Schritt 3 (+ streamlit) — am ECHTEN Artefakt: je Familie eine gebaute
                     Broschuere; auf jeder Wertentwicklungs-Folie liegt die
                     Quelle vollstaendig unter dem Disclaimer, ist nicht leer
                     und traegt das Stand-Datum.

Die Konstanten liegen in pptx_slides, das pandas und python-pptx hereinzieht —
ohne die beiden ueberspringt sich die Suite ganz. Fehlt nur streamlit, laufen
Schritt 1 und 2 und Schritt 3 wird uebersprungen.

    python tests/test_quelle_position.py [ausgabeordner]

Rueckgabewert 0 = bestanden, 1 = fehlgeschlagen.
"""

import importlib.util
import math
import os
import sys
import tempfile

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
sys.path.insert(0, os.path.join(WURZEL, "tests"))
os.chdir(WURZEL)   # Vorlage/ und Daten/ werden relativ geladen

try:
    from modules.pptx_slides import (                              # noqa: E402
        SHAPE_WE_FUSSNOTE, SHAPE_WE_QUELLE,
        WE_DISCLAIMER_REPLACEMENTS, WE_FUSSNOTE_ZEILE_MAX, WE_QUELLE_TOP_CM,
        WE_TABELLE_KOSTENREGEL, WE_TABELLE_KOSTENREGEL_NEU,
        WE_FOOTNOTE_STAR1_NEW, WE_FOOTNOTE_STAR1_PREFIX,
        WE_FOOTNOTE_STAR2_NEW, WE_FOOTNOTE_STAR2_PREFIX,
    )
except ImportError as ex:
    # pptx_slides zieht pandas und python-pptx herein. Ohne die beiden ist
    # hier nichts zu messen — ueberspringen statt scheitern.
    print(f"UEBERSPRUNGEN — Abhaengigkeit fehlt: {ex}")
    sys.exit(0)

# Unsere EIGENEN Konstanten getrennt holen. Fehlt ein Paket, wird oben
# uebersprungen — das ist Hausregel. Fehlt dagegen eine dieser Konstanten,
# ist die comdirect-Ersetzung zurueckgebaut und der Disclaimer traegt wieder
# die alte Kostenregel. Das muss ROT werden, nicht gruen.
from modules import pptx_slides as _slides                         # noqa: E402

_FEHLEND = [n for n in ("WE_DISCLAIMER_FLIESSTEXT", "WE_DISCLAIMER_ANFANG")
            if not hasattr(_slides, n)]
if _FEHLEND:
    print(f"FEHLGESCHLAGEN — modules/pptx_slides.py fehlt: "
          f"{', '.join(_FEHLEND)} (zurueckgebaut?)")
    sys.exit(1)
WE_DISCLAIMER_FLIESSTEXT = _slides.WE_DISCLAIMER_FLIESSTEXT
WE_DISCLAIMER_ANFANG = _slides.WE_DISCLAIMER_ANFANG

EMU_PRO_CM = 360000

# ── Rendering-Kennwerte, am Artefakt gemessen (nicht geschaetzt) ────────────
# Quelle: Thema.pptx F12, von PowerPoint 16.0 als PNG mit 1920x1225 px
# ausgegeben (Folie 29,0 x 18,5 cm) und zeilenweise vermessen. Die erste
# Textzeile beginnt 0,06 cm unter der Boxoberkante; von der ersten bis zur
# dreizehnten Zeile sind es 3,04 cm, also 0,2533 cm Zeilenabstand (6 pt,
# Zeilenabstand 100 %). Die Unterlaenge der Glyphen kommt unten drauf.
ZEILENHOEHE_CM = 0.2533
ERSTE_ZEILE_CM = 0.06
GLYPHENHOEHE_CM = 0.21

# Mindestabstand zwischen Disclaimer-Unterkante und Quellenzeile. Weniger
# waere zwar kollisionsfrei, sieht aber nach Versehen aus.
MINDESTABSTAND_CM = 0.15

# Die Kostenregel, die seit Juli 2026 gilt — und die, die sie abgeloest hat.
# Beide stehen hier als Konstante, damit Schritt 3 sie an JEDER gebauten
# Wertentwicklungs-Folie pruefen kann: Eine Broschuere darf die alte Regel
# nicht mehr tragen und muss die neue nennen.
ALTE_KOSTENREGEL = "erfolgt vor Kosten"
NEUE_KOSTENREGEL = "taggenau abgezogen"

VORLAGEN = [
    "Vorlage_cVV_Infoboard.pptx", "Vorlage_ESG.pptx", "Vorlage_comdirect.pptx",
    "Vorlage_ETF.pptx", "Vorlage_Thema.pptx", "Vorlage_FFPB.pptx",
]

# So viele Folien mit Quelle UND Disclaimer traegt jede Vorlage. Sinkt eine
# Zahl, ist eine Folie aus der Vorlage verschwunden — dann greift die
# Korrektur dort nicht mehr, ohne dass irgendetwas scheitern wuerde.
#
# Vorlage_FFPB.pptx hat ZWEI: F11 ist die Wertentwicklungs-Folie (betroffen),
# F10 die Performance-Folie. Deren Disclaimer ist kuerzer (9 Zeilen bis
# 13,45 cm), die Quelle steht dort bei 13,89 cm also frei — sie wird bewusst
# NICHT verschoben. Geprueft wird die Zusage ("Quelle unter dem Disclaimer"),
# nicht eine feste Koordinate.
FOLIEN_SOLL = {
    "Vorlage_cVV_Infoboard.pptx": 5, "Vorlage_ESG.pptx": 4,
    "Vorlage_comdirect.pptx": 3, "Vorlage_ETF.pptx": 2,
    "Vorlage_Thema.pptx": 1, "Vorlage_FFPB.pptx": 2,
}


def _cm(emu):
    return None if emu is None else emu / EMU_PRO_CM


def _we_folien(prs):
    """Alle Folien, die eine Quellenangabe UND einen Disclaimer tragen.

    Erkannt wird an den beiden Shapes statt an einer Folienliste: So findet
    der Test sie auch in einer gebauten Broschuere, in der die Themen-Folien
    vervielfaeltigt wurden und die Positionen sich verschoben haben — und er
    findet eine neue Folie, die dieselbe Konstellation erbt, ohne dass jemand
    daran denkt, hier eine Nummer nachzutragen.
    """
    raus = []
    for nr, slide in enumerate(prs.slides, start=1):
        namen = {sh.name: sh for sh in slide.shapes}
        if SHAPE_WE_FUSSNOTE in namen and SHAPE_WE_QUELLE in namen:
            raus.append((nr, namen[SHAPE_WE_FUSSNOTE], namen[SHAPE_WE_QUELLE]))
    return raus


def _fussnote_unterkante(fussnote):
    """Untere Kante des gerenderten Fussnotentextes in cm.

    Der Disclaimer ist hart umbrochen; jeder Absatz belegt eine Zeile, ein zu
    langer Absatz bricht zusaetzlich um. Leere Absaetze zaehlen mit — sie
    erzeugen eine Leerzeile.
    """
    zeilen = 0
    for para in fussnote.text_frame.paragraphs:
        zeilen += max(1, math.ceil(len(para.text) / WE_FUSSNOTE_ZEILE_MAX))
    return (_cm(fussnote.top) + ERSTE_ZEILE_CM
            + (zeilen - 1) * ZEILENHOEHE_CM + GLYPHENHOEHE_CM), zeilen


# ───────────────────────────── Schritt 1 ──────────────────────────────────

def _ersatztexte_anwenden(fussnote):
    """Schreibt die Vorlagen-Fussnote so um, wie der Export es tut.

    Bewusst ueber die PRODUKTIVE Funktion und die produktiven Konstanten —
    eine Nachbildung wuerde genau das nicht messen, worauf es ankommt.
    Die ***-Zeile bleibt Vorlagentext: Ihre echte Laenge haengt an der
    Strategie und wird in Schritt 3 am Artefakt geprueft.
    """
    from modules.pptx_slides import replace_paragraph_text_by_prefix
    tf = fussnote.text_frame
    replace_paragraph_text_by_prefix(tf, WE_FOOTNOTE_STAR1_PREFIX,
                                     WE_FOOTNOTE_STAR1_NEW)
    replace_paragraph_text_by_prefix(tf, WE_FOOTNOTE_STAR2_PREFIX,
                                     WE_FOOTNOTE_STAR2_NEW)
    for prefix, neu in WE_DISCLAIMER_REPLACEMENTS:
        replace_paragraph_text_by_prefix(tf, prefix, neu)


def _pruefe_vorlagen():
    print("1. Vorlagen: liegt WE_QUELLE_TOP_CM unter dem Disclaimer?")
    if importlib.util.find_spec("pptx") is None:
        print("   UEBERSPRUNGEN — python-pptx nicht installiert")
        return 0
    from pptx import Presentation

    kopf = (f"   {'Vorlage':28s} {'Fo':>3s} {'Zeilen':>6s} {'Unterkante':>10s} "
            f"{'Quelle neu':>10s} {'Luft':>6s}  Ergebnis")
    print(kopf)
    print("   " + "-" * (len(kopf) - 3))

    fehler = 0
    for datei in VORLAGEN:
        pfad = os.path.join("Vorlage", datei)
        if not os.path.exists(pfad):
            print(f"   {datei:28s} UEBERSPRUNGEN (nicht vorhanden)")
            continue
        folien = _we_folien(Presentation(pfad))
        soll = FOLIEN_SOLL.get(datei)
        if soll is not None and len(folien) != soll:
            fehler += 1
            print(f"   {datei:28s} FEHLER: {len(folien)} statt {soll} "
                  f"Wertentwicklungs-Folien")
        for nr, fussnote, quelle in folien:
            _ersatztexte_anwenden(fussnote)
            unten, zeilen = _fussnote_unterkante(fussnote)
            luft = WE_QUELLE_TOP_CM - unten
            maengel = []
            if luft < MINDESTABSTAND_CM:
                maengel.append(f"nur {luft:.2f} cm Abstand zum Disclaimer "
                               f"(mindestens {MINDESTABSTAND_CM:.2f})")
            # Die Box darf nicht in die Foliennummer oder aus der Folie laufen.
            unterkante_quelle = WE_QUELLE_TOP_CM + _cm(quelle.height)
            if unterkante_quelle > 17.0:
                maengel.append(f"Quelle endet bei {unterkante_quelle:.2f} cm "
                               f"— zu nah an der Foliennummer")
            ok = not maengel
            fehler += 0 if ok else 1
            print(f"   {datei:28s} {nr:3d} {zeilen:6d} {unten:10.2f} "
                  f"{WE_QUELLE_TOP_CM:10.2f} {luft:6.2f}  "
                  f"{'OK' if ok else 'FEHLER'}")
            for m in maengel:
                print(f"        {m}")
    return fehler


# ───────────────────────────── Schritt 2 ──────────────────────────────────

def _vorlagen_absatzlaenge(prefix):
    """Laenge des laengsten Vorlagen-Absatzes, der mit `prefix` beginnt."""
    from pptx import Presentation
    laengste = 0
    for datei in VORLAGEN:
        pfad = os.path.join(WURZEL, "Vorlage", datei)
        if not os.path.exists(pfad):
            continue
        for folie in Presentation(pfad).slides:
            for shape in folie.shapes:
                if not shape.has_text_frame:
                    continue
                for absatz in shape.text_frame.paragraphs:
                    if absatz.text.strip().startswith(prefix):
                        laengste = max(laengste, len(absatz.text))
    return laengste


def _pruefe_tabellensatz():
    """Passt der Ersatz auf der Tabellen-Folie in seine Box?

    Diese Folien haben kein Shape "Quelle", also auch keine Nachbarschaft,
    die man messen koennte — hier zaehlt allein die Boxhoehe. Der Ersatz ist
    mit 255 Zeichen laenger als der Vorlagentext (211); genau die
    Konstellation, gegen die diese Suite gebaut wurde. Nachgemessen statt
    behauptet: Die urspruengliche Fassung liess den Zusatz "(keine
    halbjaehrliche Beruecksichtigung)" weg und begruendete das mit dem
    Umbruch — die Messung hat das widerlegt.
    """
    if importlib.util.find_spec("pptx") is None:
        print("   WE_TABELLE_KOSTENREGEL_NEU     UEBERSPRUNGEN (python-pptx)")
        return 0
    from pptx import Presentation

    fehler = 0
    engste = None
    for datei in VORLAGEN:
        pfad = os.path.join(WURZEL, "Vorlage", datei)
        if not os.path.exists(pfad):
            continue
        for folie in Presentation(pfad).slides:
            for shape in folie.shapes:
                if not getattr(shape, "has_text_frame", False):
                    continue
                if WE_TABELLE_KOSTENREGEL not in shape.text_frame.text:
                    continue
                breite = _cm(shape.width)
                hoehe = _cm(shape.height)
                # Zeichen je Zeile skalieren mit der Breite: 149 Zeichen
                # passen in 15,60 cm (WE_FUSSNOTE_ZEILE_MAX).
                je_zeile = max(1, int(WE_FUSSNOTE_ZEILE_MAX * breite / 15.60))
                neu_text = shape.text_frame.text.replace(
                    WE_TABELLE_KOSTENREGEL, WE_TABELLE_KOSTENREGEL_NEU)
                zeilen = sum(max(1, math.ceil(len(p) / je_zeile))
                             for p in neu_text.split("\n"))
                gebraucht = zeilen * ZEILENHOEHE_CM
                if engste is None or breite < engste[0]:
                    engste = (breite, hoehe, je_zeile, zeilen, gebraucht, datei)
    if engste is None:
        print("   WE_TABELLE_KOSTENREGEL_NEU     FEHLER — kein Vorlagen-Absatz "
              "enthaelt den Satz; die Ersetzung liefe ins Leere")
        return 1
    breite, hoehe, je_zeile, zeilen, gebraucht, datei = engste
    ok = gebraucht <= hoehe
    fehler += 0 if ok else 1
    print(f"   WE_TABELLE_KOSTENREGEL_NEU  {len(WE_TABELLE_KOSTENREGEL_NEU):4d} "
          f"Zeichen  {'OK' if ok else 'PASST NICHT'}")
    print(f"        engste Box {datei} {breite:.2f}x{hoehe:.2f} cm, "
          f"~{je_zeile} Zeichen/Zeile -> {zeilen} Zeilen = {gebraucht:.2f} cm")
    return fehler


def _pruefe_zeilenlaengen():
    """Passt jeder Ersatztext dorthin, wo er landet?

    ZWEI MASSSTAEBE, weil die Vorlagen zwei Bauarten haben:

      * HAND-UMBROCHEN (fuenf Vorlagen): Die Absaetze sind von Hand auf die
        Boxbreite verteilt, die laengste Zeile hat 149 Zeichen. Ein laengerer
        Ersatz bricht still um und schiebt alles darunter eine Zeile tiefer.
      * FLIESSEND (comdirect): EIN Absatz von 651 Zeichen, der von selbst
        umbricht. Die 149er-Regel beschreibt hier nichts. Massstab ist der
        VORLAGENTEXT — wird der Ersatz laenger, waechst der Block nach unten
        und schiebt die Quellenangabe weg.
    """
    print("\n2. Ersatztexte: passt jeder dorthin, wo er landet?")
    fehler = 0
    for name, text in (("WE_FOOTNOTE_STAR1_NEW", WE_FOOTNOTE_STAR1_NEW),
                       ("WE_FOOTNOTE_STAR2_NEW", WE_FOOTNOTE_STAR2_NEW)):
        ok = len(text) <= WE_FUSSNOTE_ZEILE_MAX
        fehler += 0 if ok else 1
        print(f"   {name:30s} {len(text):4d} / {WE_FUSSNOTE_ZEILE_MAX}  "
              f"{'OK' if ok else 'ZU LANG'}")

    fehler += _pruefe_tabellensatz()

    hat_pptx = importlib.util.find_spec("pptx") is not None
    for i, (prefix, neu) in enumerate(WE_DISCLAIMER_REPLACEMENTS):
        name = f"WE_DISCLAIMER_REPLACEMENTS[{i}]"
        if prefix in WE_DISCLAIMER_FLIESSTEXT:
            if not hat_pptx:
                print(f"   {name:30s} {len(neu):4d} / ?    UEBERSPRUNGEN "
                      "(python-pptx fehlt)")
                continue
            grenze = _vorlagen_absatzlaenge(prefix)
            if not grenze:
                fehler += 1
                print(f"   {name:30s} FEHLER — kein Vorlagen-Absatz beginnt "
                      f"mit {prefix!r}; die Ersetzung liefe ins Leere")
                continue
            ok = len(neu) <= grenze
            fehler += 0 if ok else 1
            print(f"   {name:30s} {len(neu):4d} / {grenze:4d}  "
                  f"{'OK (fliessend)' if ok else 'LAENGER ALS DIE VORLAGE'}")
            if not ok:
                print("        der Block waechst nach unten und schiebt "
                      "die Quellenangabe weg")
            continue
        ok = len(neu) <= WE_FUSSNOTE_ZEILE_MAX
        fehler += 0 if ok else 1
        print(f"   {name:30s} {len(neu):4d} / {WE_FUSSNOTE_ZEILE_MAX}  "
              f"{'OK' if ok else 'ZU LANG'}")
        if not ok:
            print(f"        bricht um — alles darunter rutscht eine Zeile "
                  f"tiefer: {neu[:70]}...")
    return fehler


# ───────────────────────────── Schritt 3 ──────────────────────────────────

def _pruefe_datei(pfad, etikett, stand):
    """Misst jede Wertentwicklungs-Folie einer gebauten Broschuere."""
    from pptx import Presentation

    geprueft = fehler = 0
    for nr, fussnote, quelle in _we_folien(Presentation(pfad)):
        geprueft += 1
        unten, zeilen = _fussnote_unterkante(fussnote)
        oben_q = _cm(quelle.top)
        text = quelle.text_frame.text.strip()
        maengel = []
        if oben_q < unten + MINDESTABSTAND_CM:
            maengel.append(f"Quelle bei {oben_q:.2f} cm, Disclaimer reicht "
                           f"bis {unten:.2f} cm")
        if not text:
            maengel.append("Quellenangabe ist leer")
        elif stand and stand not in text:
            maengel.append(f"Stand-Datum fehlt: {text!r}")
        # Die KOSTENREGEL im Disclaimer (23.09.2026). Bis dahin trugen die
        # drei comdirect-Folien weiter den Vorlagentext "erfolgt vor Kosten"
        # — im Widerspruch zur **-Zeile derselben Fussnote, und zwar weil ein
        # Bindestrich den Anker verfehlte. Lautlos, fast vierzehn Monate.
        fu_text = fussnote.text_frame.text
        if ALTE_KOSTENREGEL in fu_text:
            maengel.append(f"Disclaimer traegt noch die alte Kostenregel "
                           f"({ALTE_KOSTENREGEL!r})")
        if NEUE_KOSTENREGEL not in fu_text:
            maengel.append(f"Disclaimer nennt den taggenauen Abzug nicht "
                           f"({NEUE_KOSTENREGEL!r})")
        # Absicht: Hier wird NICHT die Absatzlaenge geprueft. Die Vorlagen
        # tragen selbst Absaetze ueber der Zeilenbreite (237 bzw. 254
        # Zeichen) — das ist gewollter Vorlagentext, der sauber umbricht,
        # und _fussnote_unterkante rechnet den Umbruch mit. Die Laengen der
        # vom CODE geschriebenen Zeilen misst Schritt 2.
        ok = not maengel
        fehler += 0 if ok else 1
        print(f"   {etikett:12s} {nr:3d} {zeilen:6d} {unten:10.2f} "
              f"{oben_q:10.2f} {oben_q - unten:6.2f}  "
              f"{'OK' if ok else 'FEHLER'}")
        for m in maengel:
            print(f"        {m}")
    return geprueft, fehler


# Die Themen-Duplikation gehoert dazu: Dort entstehen die Wertentwicklungs-
# Folien erst beim Bauen (Offensiv ist die gemeldete), und SCHWEIZ ist der
# Fall OHNE Benchmark — dort faellt die ***-Zeile weg, die Fussnote wird also
# kuerzer als in allen anderen Broschueren.
THEMA_ZUSATZ = [
    ("Thema x3", ["Offensiv", "Pro", "Pro Dividende"]),
    ("SCHWEIZ", ["Schweiz_substanzorientiert"]),
]


def _pruefe_artefakt(ausgabe):
    print("\n3. Wirkung am echten Artefakt (gebaute Broschueren)")
    if importlib.util.find_spec("pptx") is None:
        print("   UEBERSPRUNGEN — python-pptx nicht installiert")
        return 0
    try:
        from modules.portfolioanalyse import (
            VORLAGEN_FAMILIEN, FAMILIE_ALLE_STRATEGIEN, _familien_portfolios,
            _familie_fuer_strategie, duration_info_aus_bestand,
        )
        # Datenbeschaffung und Bau kommen aus dem Export-Smoketest — damit
        # laeuft diese Suite ueber denselben Pfad wie die Oberflaeche.
        from test_export_smoke import _daten, _portfolio, _bauen
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0

    d = _daten()
    kopf = (f"   {'Broschuere':12s} {'Fo':>3s} {'Zeilen':>6s} {'Unterkante':>10s} "
            f"{'Quelle':>10s} {'Luft':>6s}  Ergebnis")
    print(kopf)
    print("   " + "-" * (len(kopf) - 3))

    fehler = geprueft = 0

    def _lauf(portfolios, familie, dateiname, etikett):
        nonlocal fehler, geprueft
        ziel, _gr, meldungen = _bauen(portfolios, familie, d, ausgabe, dateiname)
        for m in meldungen:
            print(f"   ! BUILD-FEHLER {etikett}: {m[:90]}")
            fehler += 1
        # Der erwartete Datenstand: das Auswertungsdatum des ersten Portfolios,
        # genau wie pptx_export._stand_str ihn bildet.
        ad = portfolios[0][2]
        stand = ad.strftime("%d.%m.%Y") if hasattr(ad, "strftime") else None
        n, f = _pruefe_datei(ziel, etikett, stand)
        geprueft += n
        fehler += f

    for familie in sorted(VORLAGEN_FAMILIEN):
        strategie = next((n for n in d["namen"]
                          if _familie_fuer_strategie(d["nm"], n) == familie), None)
        if strategie is None:
            print(f"   {familie:12s} UEBERSPRUNGEN (keine Strategie in den Daten)")
            continue
        alle = FAMILIE_ALLE_STRATEGIEN.get(familie)
        if alle:
            portfolios, fehlend = _familien_portfolios(
                alle, d["namen"], d["d2c"], d["pf_data"], duration_info_aus_bestand)
            if fehlend:
                print(f"   {familie:12s} UEBERSPRUNGEN (fehlende Daten: "
                      f"{', '.join(fehlend)})")
                continue
        else:
            portfolios = [_portfolio(strategie, d)]
        _lauf(portfolios, familie, f"{familie}.pptx", familie)

    for etikett, namen in THEMA_ZUSATZ:
        fehlend = [n for n in namen if n not in d["d2c"]]
        if fehlend:
            print(f"   {etikett:12s} UEBERSPRUNGEN (nicht in den Daten: "
                  f"{', '.join(fehlend)})")
            continue
        _lauf([_portfolio(n, d) for n in namen], "Thema",
              f"Thema_{etikett.replace(' ', '_')}.pptx", etikett)

    if not geprueft:
        print("   UEBERSPRUNGEN — keine Wertentwicklungs-Folie gefunden")
    else:
        print(f"\n   {geprueft} Wertentwicklungs-Folien geprueft")
    return fehler


# ───────────────────────────── Schritt 4 ──────────────────────────────────

def _disclaimer(fussnote):
    """Der Disclaimer einer Fussnote, zu EINEM Fliesstext zusammengefuegt.

    Die Vorlagen sind unterschiedlich gebaut — fuenf brechen den Disclaimer
    von Hand auf Zeilen um, comdirect fuehrt ihn als einen Absatz. Verglichen
    werden soll aber die AUSSAGE, nicht die Bauart. Deshalb:

      * ab dem Absatz sammeln, der mit WE_DISCLAIMER_ANFANG beginnt,
      * Trennstriche am Zeilenende aufloesen ("Auswirkun-" + "gen"),
      * geschuetzte Leerzeichen und Mehrfach-Leerraum vereinheitlichen.

    Returns None, wenn die Fussnote keinen Disclaimer traegt.
    """
    teile, gefunden = [], False
    for absatz in fussnote.text_frame.paragraphs:
        if not gefunden:
            if absatz.text.strip().startswith(WE_DISCLAIMER_ANFANG):
                gefunden = True
            else:
                continue
        teile.append(absatz.text)
    if not gefunden:
        return None
    text = ""
    for stueck in teile:
        if text.endswith("-") and stueck[:1].islower():
            text = text[:-1] + stueck     # Trennstrich faellt weg
        else:
            text += stueck
    return " ".join(text.replace("\xa0", " ").split())


def _pruefe_disclaimer_gleich(ausgabe):
    """Sagt der Disclaimer in JEDER Familie dasselbe?

    Auftrag Philip, 23.09.2026: "den Disclaimer der comdirect kannst du
    gleichschalten mit dem Rest, es werden ja hier auch taegliche Daten
    verwendet." Genau das misst dieser Schritt — nicht, dass eine Ersetzung
    lief, sondern dass am Ende ueberall dasselbe steht.

    Er haette den alten Fehler gefunden: Ein Bindestrich liess den Anker bei
    comdirect ins Leere laufen, und niemand erfuhr davon.
    """
    print("\n4. Sagt der Disclaimer in jeder Familie dasselbe?")
    if importlib.util.find_spec("pptx") is None:
        print("   UEBERSPRUNGEN — python-pptx nicht installiert")
        return 0
    from pptx import Presentation
    import glob

    dateien = sorted(glob.glob(os.path.join(ausgabe, "*.pptx")))
    if not dateien:
        print("   UEBERSPRUNGEN — keine gebauten Broschueren gefunden")
        return 0

    gesehen = {}
    for pfad in dateien:
        etikett = os.path.splitext(os.path.basename(pfad))[0]
        for nr, fussnote, _q in _we_folien(Presentation(pfad)):
            text = _disclaimer(fussnote)
            if text is None:
                print(f"   FEHLER — {etikett} F{nr}: kein Disclaimer, der mit "
                      f"{WE_DISCLAIMER_ANFANG!r} beginnt")
                return 1
            gesehen.setdefault(text, []).append(f"{etikett} F{nr}")

    if len(gesehen) == 1:
        text, wo = next(iter(gesehen.items()))
        print(f"   OK — {len(wo)} Folien aus {len(dateien)} Broschueren, "
              f"wortgleich ({len(text)} Zeichen)")
        return 0

    print(f"   FEHLER — {len(gesehen)} verschiedene Fassungen:")
    for i, (text, wo) in enumerate(sorted(gesehen.items(),
                                          key=lambda p: -len(p[1])), start=1):
        print(f"     ({i}) {len(wo):2d} Folien: {', '.join(wo[:4])}"
              f"{' …' if len(wo) > 4 else ''}")
        print(f"         {text[:150]}...")
    # Die erste Abweichung benennen, statt den Leser zwei Bloecke vergleichen
    # zu lassen.
    fassungen = list(gesehen)
    a, b = fassungen[0], fassungen[1]
    for i, (za, zb) in enumerate(zip(a, b)):
        if za != zb:
            print(f"   erste Abweichung bei Zeichen {i}: "
                  f"{a[max(0, i-40):i+40]!r}")
            print(f"                              gegen "
                  f"{b[max(0, i-40):i+40]!r}")
            break
    return len(gesehen) - 1


# ───────────────────────────── Schritt 5 ──────────────────────────────────

# Was in keiner fertigen Broschuere mehr stehen darf. Das erste Muster ist
# eine Sachaussage ueber Kosten, die seit Juli 2026 falsch ist; die uebrigen
# sind Schreibweisen, die Philip am 23.09.2026 fuer alle Familien
# angeglichen hat. "VV Honorar" steht mit auf der Liste, obwohl niemand
# danach gefragt hat: Es kam nur in den beiden ersetzten Saetzen vor und
# verschwindet mit ihnen — wer den Satz spaeter aendert, soll es merken.
ALTLASTEN = [
    ("erfolgt vor Kosten", "alte Kostenregel"),
    ("Performance Angaben", "Deppenleerzeichen"),
    ("Gesamtkosten- und Gebühren", "Ergaenzungsstrich ins Leere"),
    ("VV Honorar", "fehlender Bindestrich"),
]


def _altlasten_im_dokument(pfad):
    """Alle Altlasten-Treffer einer Broschuere, als (Folie, Muster).

    Liest ueber `pptx_slides._textrahmen` — also DIESELBE Traversierung, die
    auch `wortlaut_angleichen` benutzt, samt Gruppen und Tabellenzellen. Mit
    einer eigenen Schleife haette der Pruefstein einen anderen blinden Fleck
    als der Durchgang und koennte dessen Luecke nicht finden. Genau daran ist
    die Sache heute schon zweimal vorbeigelaufen.
    """
    from pptx import Presentation
    from modules.pptx_slides import _textrahmen
    treffer = []
    for nr, folie in enumerate(Presentation(pfad).slides, start=1):
        for rahmen in _textrahmen(folie.shapes):
            text = rahmen.text
            for muster, _grund in ALTLASTEN:
                if muster in text:
                    treffer.append((nr, muster))
    return treffer


def _pruefe_altlasten(ausgabe):
    """Ueber ALLE Folien, nicht nur ueber die Wertentwicklungs-Folie.

    Genau daran ist es zweimal gescheitert: Die Pruefsteine sahen nur die
    Folien mit einem Shape "Quelle". Die Tabellen-Folie hat keines — dort
    stand die alte Kostenregel mitten im Absatz und ueberlebte jede
    Korrektur. Eine Broschuere sagte auf der einen Folie "nach Kosten" und
    auf der anderen "vor Kosten".

    Deshalb schaut dieser Schritt in JEDES Textfeld JEDER Folie.
    """
    print("\n5. Keine Altlast auf irgendeiner Folie")
    if importlib.util.find_spec("pptx") is None:
        print("   UEBERSPRUNGEN — python-pptx nicht installiert")
        return 0
    import glob

    dateien = sorted(glob.glob(os.path.join(ausgabe, "*.pptx")))
    if not dateien:
        print("   UEBERSPRUNGEN — keine gebauten Broschueren gefunden")
        return 0

    grund = dict(ALTLASTEN)
    fehler = 0
    for pfad in dateien:
        for nr, muster in _altlasten_im_dokument(pfad):
            fehler += 1
            print(f"   FEHLER — {os.path.basename(pfad)} F{nr}: "
                  f"{muster!r} — {grund[muster]}")
    if not fehler:
        print(f"   OK — {len(dateien)} Broschueren, keines der "
              f"{len(ALTLASTEN)} Muster kommt noch vor")

    # Gegenprobe: Die Suche muss einen eingebauten Verstoss auch finden.
    # Dafuer reicht der Vorlagentext selbst — er traegt sie alle noch.
    vorlage = os.path.join(WURZEL, "Vorlage", "Vorlage_cVV_Infoboard.pptx")
    if os.path.exists(vorlage):
        in_vorlage = {m for _nr, m in _altlasten_im_dokument(vorlage)}
        if len(in_vorlage) < 3:
            fehler += 1
            print(f"   FEHLER — die Suche findet in der UNveraenderten Vorlage "
                  f"nur {len(in_vorlage)} Muster; sie misst nichts")
        else:
            print(f"   OK — Gegenprobe: in der unveraenderten Vorlage findet "
                  f"sie {len(in_vorlage)} der {len(ALTLASTEN)} Muster")
    return fehler


def main():
    ausgabe = (sys.argv[1] if len(sys.argv) > 1
               else tempfile.mkdtemp(prefix="ffpb_quelle_"))
    os.makedirs(ausgabe, exist_ok=True)

    fehler = (_pruefe_vorlagen() + _pruefe_zeilenlaengen()
              + _pruefe_artefakt(ausgabe)
              + _pruefe_disclaimer_gleich(ausgabe)
              + _pruefe_altlasten(ausgabe))
    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — die Quellenangabe steht auf jeder Wertentwicklungs-Folie")
    print("            unter dem Disclaimer, jeder Ersatztext passt dorthin,")
    print("            wo er landet, der Disclaimer sagt in jeder Familie")
    print("            dasselbe, und keine Folie traegt noch eine Altlast.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
