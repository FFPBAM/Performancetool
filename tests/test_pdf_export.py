# -*- coding: utf-8 -*-
"""PDF-Fassung der Broschuere — ohne "Ihre Ansprechpartner fuer den Vertrieb".

WARUM ES DIESE SUITE GIBT (17.09.2026): Die Broschuere soll zusaetzlich als PDF
herausgehen, und zwar aus DERSELBEN gebauten PowerPoint, nur ohne die Folie mit
den Vertriebs-Ansprechpartnern (im PDF lassen sich deren Fotos nicht
austauschen). Die App liefert dafuer eine vorbereitete PowerPoint, die der
Berater in PowerPoint als PDF speichert. `modules/pdf_export.pptx_fuer_pdf`
entfernt die Folie und zieht zwei Dinge nach, die sonst still falsch waeren:
  - die Seitenzahlen unten (beim Bau als FESTER Text geschrieben, #pptx_helpers)
  - die EINGETIPPTEN Seitenzahlen im Inhaltsverzeichnis
und entfernt Diagramm-Verknuepfungen auf externe Mappen.

Schritte:
  1  Erkennung ueber alle sechs Vorlagen: nur cVV (F30) und FFPB (F21)
  2  cVV bauen -> PDF-Quelle: 36 Folien, keine Vertriebsfolie, Nummern = Position
  3  Inhaltsverzeichnis: jede Zahl zeigt im PDF auf DIESELBE Folie wie in der
     PowerPoint; das Impressum steht in der PowerPoint auf 36 (Vorlagen-
     korrektur 17.09.2026, vorher stand dort 34)
  4  Paket-Integritaet der PDF-Quelle (L1-L6 aus test_pptx_integritaet)
  5  Alle Vorlagen: externe Verknuepfungen (Netzlaufwerk) entfernt, Folien nur
     wo noetig, Paket intakt (Sicherheitspruefung 17.09.2026)
  6  GEGENPROBE: ohne das Nachziehen muessen 2 und 3 rot werden
  7  Waechter: PDF-Dienst abgesichert — Dienst-Skripte off-repo, keine
     Geheimnisse/Betriebsdetails im Code (nur in den Secrets), Auftraege per
     HMAC signiert, saubere Rueckfallebene auf die vorbereitete PowerPoint
  8  Oberflaeche (AppTest): zwei Buttons, Tooltip je Familie, Klick liefert die
     PDF-Fassung mit Download und Anleitung, Fehlerfall laesst die PowerPoint

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
    # Strategie-spezifische Thema-Vorlagen (NEU 17.09.2026, nur andere F2/F3):
    "Vorlage_Thema_Offensiv.pptx": [],
    "Vorlage_Thema_ProDividende.pptx": [],
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

        print("\n5. Vorlagen frei von externen Verknuepfungen, PDF-Fassung "
              "ebenso, Folien nur wo noetig, Paket intakt")
        # Sicherheitspruefung 17.09.2026 (B-03): Die Vorlagen trugen
        # Diagramm-Verknuepfungen auf einen internen Server (c:externalData,
        # oleObject External). Sie sind aus den Vorlagen entfernt, damit KEINE
        # gebaute Broschuere sie mehr traegt; die PDF-Fassung raeumt zusaetzlich
        # auf, falls eine Vorlage doch wieder eine bekommt.
        if pdf_export.externe_verknuepfungen(pdf):
            print("   FEHLER — cVV-PDF-Fassung traegt externe Verknuepfungen")
            fehler += 1
        for name, soll in sorted(ERWARTET.items()):
            with open(os.path.join("Vorlage", name), "rb") as fh:
                roh = fh.read()
            vorher = len(pdf_export.externe_verknuepfungen(roh))
            if vorher:
                print("   FEHLER — %s traegt %d externe Verknuepfung(en) "
                      "(gehoert bereinigt, B-03)" % (name, vorher))
                fehler += 1
            raus, entf, hinw = pdf_export.pptx_fuer_pdf(roh)
            ziel = os.path.join(ausgabe, "quelle_" + name)
            with open(ziel, "wb") as fh:
                fh.write(raus)
            n_roh = len(Presentation(io.BytesIO(roh)).slides)
            n_raus = len(Presentation(io.BytesIO(raus)).slides)
            probleme = []
            if entf != soll:
                probleme.append("entfernt %s statt %s" % (entf, soll))
            if n_raus != n_roh - len(soll):
                probleme.append("Folien %d -> %d" % (n_roh, n_raus))
            if pdf_export.externe_verknuepfungen(raus):
                probleme.append("externe Verknuepfungen uebrig")
            if hinw:
                probleme.append("Hinweise %s" % hinw)
            if not vorher and not soll and raus is not roh:
                probleme.append("ohne Anlass veraendert")
            befunde = INTEGRITAET.pruefe_paket(ziel) if raus is not roh else []
            if befunde:
                probleme.append("Integritaet: %s" % befunde[:2])
            fehler += 1 if probleme else 0
            print("   %-5s %-28s extern %d -> 0%s" % (
                "OK" if not probleme else "FEHLER", name, vorher,
                "" if not probleme else "  " + "; ".join(probleme)))

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

    for schritt in (schritt7_dienst_abgesichert, schritt8_oberflaeche):
        try:
            fehler += schritt()
        except Exception:
            traceback.print_exc()
            fehler += 1

    print()
    print("Ausgabe: %s" % ausgabe)
    if fehler:
        print("FEHLGESCHLAGEN — %d Fehler" % fehler)
        return 1
    print("BESTANDEN — PDF-Fassung ohne Vertriebsfolie und externe Verknuepfungen, "
          "Nummern und Inhaltsverzeichnis stimmen, Gegenprobe greift, PDF-Dienst "
          "abgesichert, Oberflaeche")
    return 0


def schritt7_dienst_abgesichert():
    """Waechter (Neubau 17.09.2026): Der PDF-Dienst (ein Standalone-Buero-PC
    wandelt via PowerPoint um, GitHub dient als Briefkasten) ist bewusst
    zurueckgeholt — mit Auflagen. Dieser Schritt haelt sie fest, damit sie nicht
    still verfallen. Grund: Der fruehere Entwurf wurde vom Virenschutz als
    Schadsoftware eingestuft; und die BaFin-Brille verlangt, dass nichts, was im
    OEFFENTLICHEN Repo liegt, Schaden anrichten kann.
      - Die Dienst-Skripte liegen NICHT im Repo (sondern lokal auf dem PC).
      - Betriebsdetails (privates Repo, Token) stehen NICHT im Code, sondern
        in den Secrets — kein Token- oder Repo-Literal im Quelltext.
      - Jeder Auftrag wird signiert (HMAC); die App faellt sauber auf die
        vorbereitete PowerPoint zurueck, wenn der Dienst fehlt."""
    print("\n7. PDF-Dienst abgesichert (Skripte off-repo, Secrets, HMAC, Rueckfall)")
    fehler = 0

    # a) Keine Dienst-Skripte im Repo.
    if os.path.exists(os.path.join(WURZEL, "pdf_dienst")):
        print("   FEHLER — Ordner pdf_dienst ist im Repo (gehoert lokal auf den PC)")
        fehler += 1
    ps1 = [os.path.relpath(os.path.join(w, d), WURZEL)
           for w, _o, dateien in os.walk(WURZEL)
           if ".git" not in w and ".venv" not in w
           for d in dateien if d.lower().endswith((".ps1", ".psm1", ".bat", ".cmd", ".vbs"))]
    if ps1:
        print("   FEHLER — Skripte im Repo: %s" % ps1)
        fehler += 1

    # b) Keine Geheimnisse/Betriebsdetails hartkodiert.
    for rel in ("modules/pdf_briefkasten.py", "modules/portfolioanalyse.py"):
        with open(os.path.join(WURZEL, rel), encoding="utf-8") as fh:
            quelle = fh.read()
        # Kein Token-Literal und kein hartkodierter Repo-Pfad (Repo kommt aus
        # den Secrets). "FFPBAM/" faengt jeden FFPBAM-Pfad, ohne den privaten
        # Repo-Namen selbst hier hinzuschreiben (Befund B-10).
        for verboten in ("github_pat_", "FFPBAM/"):
            if verboten in quelle:
                print("   FEHLER — %s enthaelt %r (gehoert in die Secrets)" % (rel, verboten))
                fehler += 1

    # c) Signatur (HMAC) und Rueckfallebene vorhanden.
    with open(os.path.join(WURZEL, "modules", "pdf_briefkasten.py"), encoding="utf-8") as fh:
        bk = fh.read()
    if "hmac" not in bk or "def signatur" not in bk:
        print("   FEHLER — pdf_briefkasten.py signiert die Auftraege nicht (HMAC fehlt)")
        fehler += 1
    with open(os.path.join(WURZEL, "modules", "portfolioanalyse.py"), encoding="utf-8") as fh:
        pa = fh.read()
    if 'st.secrets["pdf_briefkasten"]' not in pa:
        print("   FEHLER — portfolioanalyse.py liest den Dienst-Zugang nicht aus den Secrets")
        fehler += 1
    if "BriefkastenFehler" not in pa:
        print("   FEHLER — portfolioanalyse.py faengt den Dienst-Ausfall nicht ab (keine Rueckfallebene)")
        fehler += 1

    if not fehler:
        print("   OK — Skripte off-repo, keine Geheimnisse im Code, HMAC + Rueckfallebene da")
    return fehler


def schritt8_oberflaeche():
    print("\n8. Oberflaeche (AppTest)")
    try:
        from streamlit.testing.v1 import AppTest
        from modules import pptx_export
        from modules import portfolioanalyse as PA
    except ImportError as ex:
        print("   UEBERSPRUNGEN — %s" % ex)
        return 0

    with open(os.path.join(WURZEL, "streamlit_app.py"), encoding="utf-8") as fh:
        m = re.search(r'^_VIEW_PF\s*=\s*"([^"]*)"', fh.read(), re.M)
    ansicht = m.group(1) if m else "Portfolioanalyse"

    def app(strategie):
        at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                               default_timeout=400)
        at.secrets["passwords"] = {"t": "t"}
        at.session_state["logged_in"] = True
        at.session_state["username"] = "t"
        at.session_state["nav_view"] = ansicht
        at.session_state["pf_sel_1"] = strategie
        at.run()
        return at

    def knopf(at, key):
        return next((b for b in at.button if b.key == key), None)

    def ss(at, key):
        try:
            return at.session_state[key]
        except (KeyError, AttributeError):
            return None

    fehler = 0
    for strategie, soll_hilfe in (("cVV konservativ", pdf_export.HINWEIS_VERTRIEB),
                                  ("ESG defensiv", pdf_export.HINWEIS_OHNE_VERTRIEB)):
        at = app(strategie)
        if at.exception:
            print("   FEHLER — %s: App warf %s" % (strategie, at.exception[0].value))
            fehler += 1
            continue
        if ss(at, "pf_sel_1") != strategie:
            print("   UEBERSPRUNGEN — %r nicht in den Daten" % strategie)
            continue
        pptx_k, pdf_k = knopf(at, "pf_pptx_btn"), knopf(at, "pf_pdf_btn")
        if pptx_k is None or pdf_k is None or pdf_k.disabled or pdf_k.help != soll_hilfe:
            print("   FEHLER — %s: Buttons %s/%s, gesperrt %s, Tooltip %r" % (
                strategie, pptx_k is not None, pdf_k is not None,
                getattr(pdf_k, "disabled", None), getattr(pdf_k, "help", None)))
            fehler += 1
        else:
            print("   OK — %s: beide Buttons, Tooltip %s" % (
                strategie, "nennt die Vertriebsfolie"
                if soll_hilfe == pdf_export.HINWEIS_VERTRIEB else "neutral"))

    echt = (pptx_export.generate_portfolioanalyse_pptx, pdf_export.pptx_fuer_pdf)
    aufrufe = []
    pptx_export.generate_portfolioanalyse_pptx = lambda *a, **k: b"PK\x03\x04-attrappe"
    try:
        pdf_export.pptx_fuer_pdf = lambda b: (aufrufe.append(b) or (b"PK\x03\x04-fassung", [30], []))
        at = app("ESG defensiv")
        knopf(at, "pf_pdf_btn").click().run()
        downloads = [d.key for d in at.get("download_button")]
        texte = " ".join(str(c.value) for c in at.caption)
        if (at.exception or ss(at, "pf_pdf_bytes") != b"PK\x03\x04-fassung"
                or ss(at, "pf_pptx_bytes") is None or knopf(at, "pf_pdf_btn")
                or "pf_pdf_dl" not in downloads or PA.PDF_ANLEITUNG not in texte
                or aufrufe != [b"PK\x03\x04-attrappe"]):
            print("   FEHLER — Klick: Ausnahme %s, Fassung %r, Downloads %s, Anleitung %s, Quelle %s"
                  % (bool(at.exception), ss(at, "pf_pdf_bytes"), downloads,
                     PA.PDF_ANLEITUNG in texte, aufrufe))
            fehler += 1
        else:
            print("   OK — Klick baut die PowerPoint, bereitet die PDF-Fassung daraus "
                  "vor, Download + Anleitung stehen da")

        def kaputt(b):
            raise ValueError("Test-Fehler")
        pdf_export.pptx_fuer_pdf = kaputt
        at = app("ESG defensiv")
        knopf(at, "pf_pdf_btn").click().run()
        meldungen = " ".join(str(e.value) for e in at.error)
        if (at.exception or ss(at, "pf_pdf_bytes") is not None
                or ss(at, "pf_pptx_bytes") is None or "Test-Fehler" not in meldungen
                or knopf(at, "pf_pdf_btn") is None):
            print("   FEHLER — Fehlerfall: Ausnahme %s, Meldungen %r" % (bool(at.exception), meldungen))
            fehler += 1
        else:
            print("   OK — Fehlerfall: Meldung steht da, PowerPoint bleibt, "
                  "neuer Versuch moeglich")
    finally:
        pptx_export.generate_portfolioanalyse_pptx, pdf_export.pptx_fuer_pdf = echt
    return fehler


if __name__ == "__main__":
    sys.exit(main())
