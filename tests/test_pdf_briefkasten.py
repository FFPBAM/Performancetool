# -*- coding: utf-8 -*-
"""PDF-Briefkasten und PDF-Button — ohne Netz, ohne PowerPoint.

WARUM ES DIESE SUITE GIBT (17.09.2026): Das PDF der Broschuere entsteht auf
einem Buero-PC mit echtem PowerPoint; App und Dienst tauschen Dateien ueber
Release-Anhaenge im privaten Repo FFPBAM/pdf-briefkasten aus
(`modules/pdf_briefkasten.py` <-> `pdf_dienst/pdf_dienst.ps1`). Der echte Weg
ist am 17.09.2026 durchgemessen worden (STATUS.md); diese Suite haelt die
REGELN fest, damit sie ohne Netz und ohne PC pruefbar bleiben.

Schritte:
  1  Protokoll: App und Dienst sprechen dieselben Namen (Auftragsmuster aus der
     .ps1 gegen den Namen, den die App erzeugt; Release-Tag; Lebenszeichen;
     .fehler.txt; "uploaded"-Regel auf BEIDEN Seiten)
  2  Lebenszeichen: fehlt/zu alt -> klare Meldung, KEIN Auftrag hochgeladen
  3  Normalfall mit simuliertem Dienst: PDF kommt zurueck, erst bei "uploaded"
     abgeholt (der Dienst meldet es zuerst als "starter" — genau der Fehler
     vom 17.09.2026), Briefkasten danach leer
  4  Fehlerfaelle: .fehler.txt, Zeitueberschreitung, kein PDF — jeweils
     Meldung und kein zurueckgelassener Auftrag
  5  Oberflaeche (AppTest): zwei Buttons, Tooltip bei cVV nennt die Folie,
     bei ESG neutral, ohne Secrets gesperrt; Klick liefert pf_pdf_bytes,
     ein Dienstfehler steht als Meldung da und die PowerPoint bleibt

    python tests/test_pdf_briefkasten.py
"""

import os
import re
import sys
import time
import traceback

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

try:
    from modules import pdf_briefkasten as BK
except ImportError as ex:
    print("UEBERSPRUNGEN — Abhaengigkeit fehlt: %s" % ex)
    sys.exit(0)

PS1 = os.path.join(WURZEL, "pdf_dienst", "pdf_dienst.ps1")
CFG = {"repo": "FFPBAM/pdf-briefkasten", "token": "attrappe"}


# ── Simulierter Briefkasten mit Dienst ───────────────────────────────────────

class Kasten:
    """Ersetzt die fuenf API-Funktionen von pdf_briefkasten im Speicher.

    modus: "ok"      Dienst wandelt um (PDF erst "starter", dann "uploaded")
           "fehler"  Dienst legt <auftrag>.fehler.txt ab
           "stumm"   Dienst antwortet nie
           "kaputt"  Dienst liefert etwas, das kein PDF ist
    """

    def __init__(self, modus="ok", lebenszeichen_alter_s=10):
        self.modus = modus
        self.naechste_id = 100
        self.anhaenge = {}
        self.abgeholt_bei_starter = 0
        self.hochgeladen = []
        if lebenszeichen_alter_s is not None:
            self._neu("lebenszeichen-%d.txt" % (time.time() - lebenszeichen_alter_s),
                      b"pc")

    def _neu(self, name, daten, state="uploaded"):
        self.naechste_id += 1
        self.anhaenge[self.naechste_id] = {"id": self.naechste_id, "name": name,
                                           "state": state, "daten": daten}
        return self.anhaenge[self.naechste_id]

    # -- API-Ersatz --
    def release_id(self, cfg):
        return 1

    def anhaenge_liste(self, cfg, rid):
        self._dienst_arbeitet()
        return [{k: v for k, v in a.items() if k != "daten"}
                for a in self.anhaenge.values()]

    def hochladen(self, cfg, rid, name, daten, typ):
        self.hochgeladen.append(name)
        a = self._neu(name, daten)
        return {k: v for k, v in a.items() if k != "daten"}

    def herunterladen(self, cfg, anhang_id):
        a = self.anhaenge[anhang_id]
        if a["state"] != "uploaded":
            self.abgeholt_bei_starter += 1
        return a["daten"]

    def loeschen(self, cfg, anhang_id):
        self.anhaenge.pop(anhang_id, None)

    # -- der simulierte Dienst --
    def _dienst_arbeitet(self):
        for a in list(self.anhaenge.values()):
            if a["name"].endswith(".pdf") and a["state"] == "starter":
                a["state"] = "uploaded"
        if self.modus == "stumm":
            return
        for a in list(self.anhaenge.values()):
            if not a["name"].endswith(".pptx"):
                continue
            auftrag = a["name"][:-5]
            self.loeschen(None, a["id"])
            if self.modus == "ok":
                self._neu(auftrag + ".pdf", b"%PDF-1.7 attrappe", state="starter")
            elif self.modus == "kaputt":
                self._neu(auftrag + ".pdf", b"<html>kein pdf</html>")
            elif self.modus == "fehler":
                self._neu(auftrag + ".fehler.txt", "PowerPoint hing".encode("utf-8"))

    def rest(self):
        return [a["name"] for a in self.anhaenge.values()
                if not a["name"].startswith(BK.LEBENSZEICHEN_PRAEFIX)]


def _mit_kasten(kasten, aufruf):
    namen = ("release_id", "anhaenge", "hochladen", "herunterladen", "loeschen")
    echt = {n: getattr(BK, n) for n in namen}
    BK.release_id = kasten.release_id
    BK.anhaenge = kasten.anhaenge_liste
    BK.hochladen = kasten.hochladen
    BK.herunterladen = kasten.herunterladen
    BK.loeschen = kasten.loeschen
    try:
        return aufruf()
    finally:
        for n, f in echt.items():
            setattr(BK, n, f)


# ── Schritte ─────────────────────────────────────────────────────────────────

def schritt1_protokoll():
    print("1. App und Dienst sprechen dasselbe Protokoll")
    fehler = 0
    with open(PS1, encoding="ascii") as fh:
        ps = fh.read()

    m = re.search(r"\$AuftragMuster\s*=\s*'([^']+)'", ps)
    if not m:
        print("   FEHLER — $AuftragMuster in pdf_dienst.ps1 nicht gefunden")
        return 1
    muster = re.compile(m.group(1))
    beispiel = BK.neuer_auftrag() + ".pptx"
    if not muster.match(beispiel):
        print("   FEHLER — der Dienst wuerde den App-Auftrag %r ignorieren "
              "(Muster %s)" % (beispiel, m.group(1)))
        fehler += 1

    pruefungen = [
        ('$ReleaseTag = "%s"' % BK.RELEASE_TAG, "Release-Tag"),
        ('"%s$unix.txt"' % BK.LEBENSZEICHEN_PRAEFIX, "Lebenszeichen-Name"),
        ('"$auftrag.fehler.txt"', "Fehlerdatei"),
        ('"$auftrag.pdf"', "PDF-Name"),
        ('$a.state -ne "uploaded"', "Dienst fasst nur fertige Uploads an"),
    ]
    for text, was in pruefungen:
        if text not in ps:
            print("   FEHLER — %s: %r fehlt in pdf_dienst.ps1" % (was, text))
            fehler += 1
    with open(os.path.join(WURZEL, "modules", "pdf_briefkasten.py"),
              encoding="utf-8") as fh:
        if 'a.get("state") == "uploaded"' not in fh.read():
            print("   FEHLER — die App fasst nicht nur fertige Uploads an")
            fehler += 1
    if not fehler:
        print("   OK — Auftrag %r passt aufs Dienst-Muster; Tag, Lebenszeichen, "
              "Fehlerdatei und uploaded-Regel auf beiden Seiten" % beispiel)
    return fehler


def schritt2_lebenszeichen():
    print("\n2. Ohne frisches Lebenszeichen: Meldung, kein Auftrag")
    fehler = 0
    for titel, alter in (("keins", None),
                         ("zu alt", BK.LEBENSZEICHEN_MAX_ALTER_S + 60)):
        kasten = Kasten("ok", lebenszeichen_alter_s=alter)
        try:
            _mit_kasten(kasten, lambda: BK.pdf_anfordern(
                CFG, b"PK", warten_max_s=1, abfrage_alle_s=0))
            print("   FEHLER — %s: kein Fehler gemeldet" % titel)
            fehler += 1
        except BK.BriefkastenFehler as ex:
            if "nicht erreichbar" not in str(ex) or kasten.hochgeladen:
                print("   FEHLER — %s: %r, hochgeladen %s"
                      % (titel, str(ex)[:80], kasten.hochgeladen))
                fehler += 1
            else:
                print("   OK — %s: „%s…“" % (titel, str(ex)[:60]))
    return fehler


def schritt3_normalfall():
    print("\n3. Normalfall: PDF zurueck, erst bei 'uploaded' abgeholt, Kasten leer")
    kasten = Kasten("ok")
    stationen = []
    pdf = _mit_kasten(kasten, lambda: BK.pdf_anfordern(
        CFG, b"PK\x03\x04", warten_max_s=5, abfrage_alle_s=0,
        fortschritt=stationen.append))
    fehler = 0
    if not pdf.startswith(b"%PDF"):
        print("   FEHLER — kein PDF zurueck: %r" % pdf[:20])
        fehler += 1
    if kasten.abgeholt_bei_starter:
        print("   FEHLER — %d-mal abgeholt, bevor der Upload fertig war "
              "(state 'starter') — der 404 vom 17.09.2026"
              % kasten.abgeholt_bei_starter)
        fehler += 1
    if kasten.rest():
        print("   FEHLER — im Briefkasten liegt noch: %s" % kasten.rest())
        fehler += 1
    if not stationen:
        print("   FEHLER — keine Fortschrittsmeldung")
        fehler += 1
    if not fehler:
        print("   OK — PDF erhalten, nie im Zustand 'starter' abgeholt, "
              "Kasten leer, %d Fortschrittsmeldungen" % len(stationen))
    return fehler


def schritt4_fehlerfaelle():
    print("\n4. Fehlerfaelle: Meldung und kein zurueckgelassener Auftrag")
    fehler = 0
    faelle = [("fehler", "PowerPoint hing", 5), ("stumm", "nicht innerhalb", 0.05),
              ("kaputt", "kein PDF", 5)]
    for modus, erwartet, warten in faelle:
        kasten = Kasten(modus)
        try:
            _mit_kasten(kasten, lambda: BK.pdf_anfordern(
                CFG, b"PK", warten_max_s=warten, abfrage_alle_s=0.001))
            print("   FEHLER — %s: kein Fehler gemeldet" % modus)
            fehler += 1
            continue
        except BK.BriefkastenFehler as ex:
            text = str(ex)
        ok = erwartet in text and not kasten.rest()
        fehler += 0 if ok else 1
        print("   %-5s %-7s „%s…“%s" % (
            "OK" if ok else "FEHLER", modus, text[:58],
            "" if not kasten.rest() else "  Rest: %s" % kasten.rest()))
    return fehler


def schritt5_oberflaeche():
    print("\n5. Oberflaeche (AppTest)")
    try:
        from streamlit.testing.v1 import AppTest
        from modules import pdf_export, pptx_export
        from modules import portfolioanalyse as PA
    except ImportError as ex:
        print("   UEBERSPRUNGEN — %s" % ex)
        return 0

    with open(os.path.join(WURZEL, "streamlit_app.py"), encoding="utf-8") as fh:
        m = re.search(r'^_VIEW_PF\s*=\s*"([^"]*)"', fh.read(), re.M)
    ansicht = m.group(1) if m else "Portfolioanalyse"

    def app(strategie, mit_secrets=True):
        at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                               default_timeout=400)
        at.secrets["passwords"] = {"t": "t"}
        if mit_secrets:
            at.secrets["pdf_briefkasten"] = dict(CFG)
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
    # a) Buttons und Tooltip je Familie
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
        pptx, pdf = knopf(at, "pf_pptx_btn"), knopf(at, "pf_pdf_btn")
        if pptx is None or pdf is None:
            print("   FEHLER — %s: Buttons fehlen (pptx %s, pdf %s)"
                  % (strategie, pptx is not None, pdf is not None))
            fehler += 1
            continue
        if pdf.help != soll_hilfe or pdf.disabled:
            print("   FEHLER — %s: Tooltip %r, gesperrt %s"
                  % (strategie, pdf.help, pdf.disabled))
            fehler += 1
        else:
            print("   OK — %s: beide Buttons, Tooltip %s" % (
                strategie, "nennt die Vertriebsfolie"
                if soll_hilfe == pdf_export.HINWEIS_VERTRIEB else "neutral"))

    # b) ohne Secrets: gesperrt, mit Ausweichweg im Tooltip
    at = app("ESG defensiv", mit_secrets=False)
    pdf = knopf(at, "pf_pdf_btn")
    if pdf is None or not pdf.disabled or pdf.help != PA.PDF_NICHT_EINGERICHTET:
        print("   FEHLER — ohne Secrets: Button %s, gesperrt %s, Tooltip %r"
              % (pdf is not None, getattr(pdf, "disabled", None),
                 getattr(pdf, "help", None)))
        fehler += 1
    else:
        print("   OK — ohne Secrets: PDF-Button gesperrt, Tooltip nennt den Ausweichweg")

    # c) Klick: Normalfall und Dienstfehler (Bau, Folie-raus, Dienst als Attrappen)
    echt = (pptx_export.generate_portfolioanalyse_pptx, pdf_export.pptx_fuer_pdf,
            BK.pdf_anfordern)
    aufrufe = []
    pptx_export.generate_portfolioanalyse_pptx = lambda *a, **k: b"PK\x03\x04-attrappe"
    pdf_export.pptx_fuer_pdf = lambda b: (aufrufe.append(b) or (b, [30], []))
    try:
        BK.pdf_anfordern = lambda cfg, quelle, **k: b"%PDF-attrappe"
        at = app("ESG defensiv")
        knopf(at, "pf_pdf_btn").click().run()
        if (at.exception or ss(at, "pf_pdf_bytes") != b"%PDF-attrappe"
                or ss(at, "pf_pptx_bytes") is None or knopf(at, "pf_pdf_btn")):
            print("   FEHLER — Klick: Ausnahme %s, pdf %r, pptx %s, Button noch da %s"
                  % (bool(at.exception), ss(at, "pf_pdf_bytes"),
                     ss(at, "pf_pptx_bytes") is not None,
                     knopf(at, "pf_pdf_btn") is not None))
            fehler += 1
        elif aufrufe != [b"PK\x03\x04-attrappe"]:
            print("   FEHLER — die PDF-Quelle kam nicht aus der gebauten PowerPoint")
            fehler += 1
        else:
            print("   OK — Klick baut die PowerPoint, entfernt die Folie und "
                  "liefert das PDF (Button wird zum Download)")

        def dienst_weg(cfg, quelle, **k):
            raise BK.BriefkastenFehler("Der PDF-Dienst ist gerade nicht erreichbar (Test).")
        BK.pdf_anfordern = dienst_weg
        at = app("ESG defensiv")
        knopf(at, "pf_pdf_btn").click().run()
        meldungen = [e.value for e in at.error]
        if (at.exception or ss(at, "pf_pdf_bytes") is not None
                or ss(at, "pf_pptx_bytes") is None
                or not any("nicht erreichbar (Test)" in str(t) for t in meldungen)
                or knopf(at, "pf_pdf_btn") is None):
            print("   FEHLER — Dienstfehler: Ausnahme %s, Meldungen %s, pptx %s"
                  % (bool(at.exception), meldungen, ss(at, "pf_pptx_bytes") is not None))
            fehler += 1
        else:
            print("   OK — Dienstfehler: Meldung steht da, PowerPoint bleibt, "
                  "PDF-Button fuer neuen Versuch da")
    finally:
        (pptx_export.generate_portfolioanalyse_pptx, pdf_export.pptx_fuer_pdf,
         BK.pdf_anfordern) = echt
    return fehler


def main():
    fehler = 0
    for schritt in (schritt1_protokoll, schritt2_lebenszeichen, schritt3_normalfall,
                    schritt4_fehlerfaelle, schritt5_oberflaeche):
        try:
            fehler += schritt()
        except Exception:
            traceback.print_exc()
            fehler += 1
    print()
    if fehler:
        print("FEHLGESCHLAGEN — %d Fehler" % fehler)
        return 1
    print("BESTANDEN — Protokoll, Lebenszeichen, Normal- und Fehlerfaelle, "
          "Oberflaeche")
    return 0


if __name__ == "__main__":
    sys.exit(main())
