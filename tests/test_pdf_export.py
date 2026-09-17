# -*- coding: utf-8 -*-
"""PDF-Quelle der Broschuere — ohne "Ihre Ansprechpartner fuer den Vertrieb".

WARUM ES DIESE SUITE GIBT (17.09.2026): Die Broschuere soll zusaetzlich als PDF
herausgehen, und zwar aus DERSELBEN gebauten PowerPoint, nur ohne die Folie mit
den Vertriebs-Ansprechpartnern (im PDF lassen sich deren Fotos nicht
austauschen). `modules/pdf_export.pptx_fuer_pdf` entfernt die Folie und zieht
zwei Dinge nach, die sonst still falsch waeren:
  - die Seitenzahlen unten (beim Bau als FESTER Text geschrieben, #pptx_helpers)
  - die EINGETIPPTEN Seitenzahlen im Inhaltsverzeichnis

Schritte:
  1  Erkennung ueber alle sechs Vorlagen: nur cVV (F30) und FFPB (F21)
  2  cVV bauen -> PDF-Quelle: 36 Folien, keine Vertriebsfolie, Nummern = Position
  3  Inhaltsverzeichnis: jede Zahl zeigt im PDF auf DIESELBE Folie wie in der
     PowerPoint; das Impressum steht in der PowerPoint auf 36 (Vorlagen-
     korrektur 17.09.2026, vorher stand dort 34)
  4  Paket-Integritaet der PDF-Quelle (L1-L6 aus test_pptx_integritaet)
  5  Familien ohne Vertriebsfolie: Bytes unveraendert
  6  GEGENPROBE: ohne das Nachziehen muessen 2 und 3 rot werden

    python tests/test_pdf_export.py [ausgabeordner]

Die PDF-Quelle bitte stichprobenartig in ECHTEM PowerPoint ansehen (#16/#28).
"""

import glob
import io
import os
import re
import sys
import tempfile
import traceback

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
sys.path.insert(0, os.path.join(WURZEL, "tests"))
os.chdir(WURZEL)

try:
    from pptx import Presentation
except ImportError as ex:
    print("UEBERSPRUNGEN — Abhaengigkeit fehlt: %s" % ex)
    sys.exit(0)

try:
    import test_export_smoke as SMOKE
    import test_pptx_integritaet as INTEGRITAET
    from modules import pdf_export
    from modules.portfolioanalyse import (
        FAMILIE_ALLE_STRATEGIEN, _familien_portfolios, duration_info_aus_bestand,
    )
except ImportError as ex:
    print("UEBERSPRUNGEN — Abhaengigkeit fehlt: %s" % ex)
    sys.exit(0)

# Erwartung je Vorlage — gemessen am 17.09.2026. Eine neue Vertriebsfolie in
# einer anderen Vorlage soll hier AUFFALLEN (und dann bewusst eingetragen
# werden), nicht still mitlaufen.
ERWARTET = {
    "Vorlage_cVV_Infoboard.pptx": [30],
    "Vorlage_FFPB.pptx": [21],
    "Vorlage_ESG.pptx": [],
    "Vorlage_ETF.pptx": [],
    "Vorlage_Thema.pptx": [],
    "Vorlage_comdirect.pptx": [],
}

EINTRAG = re.compile(r"^(.*?)\s*\t\s*(\d+)\s*$")


def _titel(prs):
    """Titeltext je Folie (Layoutname, wenn die Folie keinen Titel hat)."""
    raus = []
    for folie in prs.slides:
        t = folie.shapes.title
        text = t.text_frame.text.strip() if t is not None and t.has_text_frame else ""
        raus.append(text or "[%s]" % folie.slide_layout.name)
    return raus


def _inhalt(prs):
    """{Eintrag: Seitenzahl} aus der Inhaltsverzeichnis-Folie."""
    raus = {}
    for folie in prs.slides:
        if folie.slide_layout.name != pdf_export.INHALT_LAYOUT:
            continue
        for shape in folie.shapes:
            if not shape.has_text_frame:
                continue
            for absatz in shape.text_frame.paragraphs:
                m = EINTRAG.match("".join(r.text for r in absatz.runs))
                if m:
                    raus[m.group(1).strip()] = int(m.group(2))
    return raus


def schritt1_erkennung():
    print("\n1. Vertriebsfolie je Vorlage")
    fehler = 0
    gefunden = {os.path.basename(p): p for p in glob.glob("Vorlage/*.pptx")}
    for name, soll in sorted(ERWARTET.items()):
        if name not in gefunden:
            print("   FEHLER — %s fehlt im Ordner Vorlage/" % name)
            fehler += 1
            continue
        ist = pdf_export.vertriebsfolien(gefunden[name])
        ok = ist == soll
        fehler += 0 if ok else 1
        print("   %-5s %-28s %s%s" % ("OK" if ok else "FEHLER", name, ist,
                                      "" if ok else "  (soll %s)" % soll))
    for name in sorted(set(gefunden) - set(ERWARTET)):
        print("   FEHLER — neue Vorlage %s ist in ERWARTET nicht eingetragen" % name)
        fehler += 1
    return fehler


def pruefe_folien(pptx, pdf):
    """Schritt 2 als Funktion — die Gegenprobe ruft sie mit Fehlbau auf."""
    fehler = 0
    p_pptx = Presentation(io.BytesIO(pptx))
    p_pdf = Presentation(io.BytesIO(pdf))
    n_pptx, n_pdf = len(p_pptx.slides), len(p_pdf.slides)
    if n_pdf != n_pptx - 1:
        print("   FEHLER — %d Folien, erwartet %d" % (n_pdf, n_pptx - 1))
        fehler += 1
    rest = [i for i, f in enumerate(p_pdf.slides, 1)
            if f.slide_layout.name == pdf_export.VERTRIEB_LAYOUT]
    if rest:
        print("   FEHLER — Vertriebsfolie noch an Position %s" % rest)
        fehler += 1
    namen = set(SMOKE.pptx_export.SHAPE_FOLIENNUMMER_NAMES)
    falsch = []
    for i, folie in enumerate(p_pdf.slides, 1):
        for shape in folie.shapes:
            if shape.name in namen and shape.has_text_frame:
                if shape.text_frame.text.strip() != str(i):
                    falsch.append((i, shape.text_frame.text.strip()))
                break
    if falsch:
        print("   FEHLER — Seitenzahl != Position: %s" % falsch[:6])
        fehler += 1
    if not fehler:
        print("   OK — %d -> %d Folien, keine Vertriebsfolie, "
              "Seitenzahlen lueckenlos" % (n_pptx, n_pdf))
    return fehler


def pruefe_inhalt(pptx, pdf):
    """Schritt 3 als Funktion — die Gegenprobe ruft sie mit Fehlbau auf."""
    fehler = 0
    p_pptx = Presentation(io.BytesIO(pptx))
    p_pdf = Presentation(io.BytesIO(pdf))
    t_pptx, t_pdf = _titel(p_pptx), _titel(p_pdf)
    i_pptx, i_pdf = _inhalt(p_pptx), _inhalt(p_pdf)
    if not i_pptx or set(i_pptx) != set(i_pdf):
        print("   FEHLER — Inhaltsverzeichnis nicht lesbar oder Eintraege "
              "verschieden: %s / %s" % (sorted(i_pptx), sorted(i_pdf)))
        return 1
    for eintrag, alt in i_pptx.items():
        neu = i_pdf[eintrag]
        ziel_pptx = t_pptx[alt - 1] if 0 < alt <= len(t_pptx) else None
        ziel_pdf = t_pdf[neu - 1] if 0 < neu <= len(t_pdf) else None
        if ziel_pptx != ziel_pdf:
            print("   FEHLER — '%s': PowerPoint %d -> '%s', PDF %d -> '%s'"
                  % (eintrag, alt, ziel_pptx, neu, ziel_pdf))
            fehler += 1
    impressum = "Rechtliche Hinweise und Impressum"
    if impressum in i_pptx:
        pos = i_pptx[impressum]
        layout = p_pptx.slides[pos - 1].slide_layout.name
        if layout != "Impressum":
            print("   FEHLER — PowerPoint: '%s' zeigt auf Folie %d (Layout "
                  "'%s') statt aufs Impressum" % (impressum, pos, layout))
            fehler += 1
    if not fehler:
        print("   OK — %d Eintraege zeigen im PDF auf dieselbe Folie; "
              "Standorte %s->%s, Impressum %s->%s"
              % (len(i_pptx), i_pptx.get("Unsere Standorte"),
                 i_pdf.get("Unsere Standorte"), i_pptx.get(impressum),
                 i_pdf.get(impressum)))
    return fehler


def main():
    ausgabe = (sys.argv[1] if len(sys.argv) > 1
               else tempfile.mkdtemp(prefix="ffpb_pdf_"))
    os.makedirs(ausgabe, exist_ok=True)
    fehler = 0

    fehler += schritt1_erkennung()

    print("\n2. cVV-Broschuere -> PDF-Quelle")
    try:
        d = SMOKE._daten()
        portfolios, fehlend = _familien_portfolios(
            FAMILIE_ALLE_STRATEGIEN["CVV"], d["namen"], d["d2c"], d["pf_data"],
            duration_info_aus_bestand)
        if fehlend:
            print("   UEBERSPRUNGEN — fehlende Daten: %s" % ", ".join(fehlend))
            return 1 if fehler else 0
        ziel, _groesse, meldungen = SMOKE._bauen(portfolios, "CVV", d, ausgabe,
                                                 "CVV.pptx")
        if meldungen:
            print("   FEHLER — Build-Meldungen: %s" % meldungen)
            fehler += 1
        with open(ziel, "rb") as fh:
            pptx = fh.read()
        pdf, entfernt, hinweise = pdf_export.pptx_fuer_pdf(pptx)
        if entfernt != [30] or hinweise:
            print("   FEHLER — entfernt %s (soll [30]), Hinweise %s"
                  % (entfernt, hinweise))
            fehler += 1
        pdf_pfad = os.path.join(ausgabe, "CVV_ohne_Vertrieb.pptx")
        with open(pdf_pfad, "wb") as fh:
            fh.write(pdf)
        fehler += pruefe_folien(pptx, pdf)

        print("\n3. Inhaltsverzeichnis")
        fehler += pruefe_inhalt(pptx, pdf)

        print("\n4. Paket-Integritaet der PDF-Quelle")
        befunde = INTEGRITAET.pruefe_paket(pdf_pfad)
        if befunde:
            for b in befunde[:8]:
                print("   FEHLER — %s" % (b,))
            fehler += 1
        else:
            print("   OK — L1-L6 sauber")

        print("\n5. Familien ohne Vertriebsfolie bleiben unberuehrt")
        for name, soll in sorted(ERWARTET.items()):
            if soll:
                continue
            with open(os.path.join("Vorlage", name), "rb") as fh:
                roh = fh.read()
            raus, entf, hinw = pdf_export.pptx_fuer_pdf(roh)
            ok = raus is roh and entf == [] and hinw == []
            fehler += 0 if ok else 1
            print("   %-5s %s" % ("OK" if ok else "FEHLER", name))

        print("\n6. Gegenprobe: ohne Nachziehen muss 2 und 3 rot werden")
        echt = (pdf_export.update_slide_numbers,
                pdf_export._inhaltsverzeichnis_nachziehen)
        pdf_export.update_slide_numbers = lambda prs, *a, **k: None
        pdf_export._inhaltsverzeichnis_nachziehen = lambda *a, **k: None
        try:
            kaputt, _e, _h = pdf_export.pptx_fuer_pdf(pptx)
            print("   (erwartete Fehlermeldungen:)")
            rot2 = pruefe_folien(pptx, kaputt)
            rot3 = pruefe_inhalt(pptx, kaputt)
        finally:
            (pdf_export.update_slide_numbers,
             pdf_export._inhaltsverzeichnis_nachziehen) = echt
        if rot2 and rot3:
            print("   OK — beide Pruefungen schlagen ohne Nachziehen an")
        else:
            print("   FEHLER — Gegenprobe greift nicht (Schritt 2: %d, "
                  "Schritt 3: %d)" % (rot2, rot3))
            fehler += 1
    except Exception:
        traceback.print_exc()
        fehler += 1

    print()
    print("Ausgabe: %s" % ausgabe)
    if fehler:
        print("FEHLGESCHLAGEN — %d Fehler" % fehler)
        return 1
    print("BESTANDEN — PDF-Quelle ohne Vertriebsfolie, Nummern und "
          "Inhaltsverzeichnis stimmen, Gegenprobe greift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
