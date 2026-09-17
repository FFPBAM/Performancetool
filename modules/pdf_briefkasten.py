# modules/pdf_briefkasten.py
"""
PDF-Briefkasten — die App laesst die PDF-Umwandlung von echtem PowerPoint
machen (Neubau 17.09.2026, freundliche Fassung).

WARUM ES DAS GIBT: Das PDF der Broschuere soll so aussehen wie
"Speichern unter -> PDF" in Desktop-PowerPoint. Auf Streamlit Cloud (Linux)
gibt es kein PowerPoint; LibreOffice zeichnet die Ringe falsch. Also wandelt
ein Buero-PC mit PowerPoint um (Dienst-Skript liegt NICHT im Repo, sondern
lokal auf jenem PC), und GitHub dient als Briefkasten dazwischen. Der Dienst
horcht, weil der PC hinter der Firewall nicht angerufen werden kann.

SICHERHEIT (nach dem Vorfall vom 17.09.2026 bewusst so gebaut):
  - Betriebsdetails (privates Repo, Zugangsschluessel, HMAC-Geheimnis) stehen
    NICHT im Code, sondern in den Streamlit-Secrets ([pdf_briefkasten]). Ohne
    diese Secrets ist der Weg still aus — die App faellt dann auf die
    vorbereitete PowerPoint zurueck.
  - JEDER Auftrag wird signiert (HMAC-SHA256 ueber die .pptx-Bytes). Der Dienst
    oeffnet nur korrekt signierte Dateien. Ein gestohlener GitHub-Schluessel
    allein reicht damit nicht, um eine fremde Datei unterzuschieben.

ABLAUF (Namen sind das Protokoll — der Dienst liest dieselben; das Format ist
in tests/test_pdf_briefkasten.py gegen die Dienst-Regex geprueft):
    App    laedt  <auftrag>.sig    hoch   (HMAC-Hex, zuerst)
    App    laedt  <auftrag>.pptx   hoch
    Dienst holt   beide, prueft die Signatur, wandelt um
    Dienst laedt  <auftrag>.pdf    hoch   (oder <auftrag>.fehler.txt)
    App    holt   <auftrag>.pdf,   loescht sie
    Dienst legt jede Minute lebenszeichen-<unixzeit>.txt ab und raeumt die
    alten weg — daran erkennt die App VOR dem Hochladen, ob jemand da ist.

Nur Standardbibliothek (urllib, hmac), damit requirements.txt unberuehrt
bleibt. Streamlit-frei wie `pptx_export`.
"""

import hashlib
import hmac
import json
import secrets as _zufall
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
UPLOAD = "https://uploads.github.com"
RELEASE_TAG = "auftraege"

LEBENSZEICHEN_PRAEFIX = "lebenszeichen-"
LEBENSZEICHEN_MAX_ALTER_S = 180
"""Aelter als das -> Dienst gilt als nicht erreichbar. Der Dienst meldet sich
jede Minute; drei Minuten lassen zwei verpasste Meldungen zu."""

WARTEN_MAX_S = 300
"""Fuenf Minuten (Philip: Wartezeit ist fuer den Berater nicht kritisch).
Gemessen sind 13-20 s; der grosse Puffer faengt einen PC ab, der gerade ein
Update installiert oder einen Auftrag vor diesem abarbeitet."""

ABFRAGE_ALLE_S = 3.0

PPTX_TYP = ("application/vnd.openxmlformats-officedocument."
            "presentationml.presentation")


class BriefkastenFehler(Exception):
    """Fehler mit einem Satz, der so in der Oberflaeche stehen kann."""


def signatur(pptx_bytes: bytes, geheim: str) -> str:
    """HMAC-SHA256 ueber die .pptx-Bytes, Hex. Muss Zeichen fuer Zeichen zu
    dem passen, was der Dienst rechnet (pdf_dienst.ps1 -> Signatur-Hex):
    Schluessel = das Geheimnis als UTF-8, Ausgabe klein geschrieben."""
    return hmac.new(geheim.encode("utf-8"), pptx_bytes, hashlib.sha256).hexdigest()


class _OhneWeiterleitung(urllib.request.HTTPRedirectHandler):
    """Der Download eines Anhangs leitet auf eine signierte Speicher-URL um.
    urllib wuerde den Authorization-Header dorthin mitnehmen — der Speicher
    lehnt zwei Anmeldeverfahren gleichzeitig ab. Deshalb die Weiterleitung
    selbst ausfuehren, ohne Schluessel."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _anfrage(cfg, methode, url, daten=None, kopf=None, erwarte_json=True):
    h = {
        "Authorization": "Bearer %s" % cfg["token"],
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ffpb-performancetool",
    }
    h.update(kopf or {})
    req = urllib.request.Request(url, data=daten, headers=h, method=methode)
    try:
        with urllib.request.urlopen(req, timeout=60) as antwort:
            inhalt = antwort.read()
    except urllib.error.HTTPError as ex:
        if ex.code == 401:
            raise BriefkastenFehler(
                "PDF-Dienst: Zugangsschlüssel ungültig oder abgelaufen "
                "(GitHub 401) — Schlüssel erneuern.") from ex
        if ex.code == 404 and methode == "GET" and "/releases/tags/" in url:
            raise
        raise BriefkastenFehler(
            "PDF-Dienst: GitHub antwortet mit %s %s." % (ex.code, ex.reason)) from ex
    except urllib.error.URLError as ex:
        raise BriefkastenFehler(
            "PDF-Dienst: GitHub nicht erreichbar (%s)." % ex.reason) from ex
    if not erwarte_json or not inhalt:
        return inhalt
    return json.loads(inhalt)


def release_id(cfg) -> int:
    """Id des Ablage-Releases; legt ihn beim ersten Mal an."""
    try:
        return _anfrage(cfg, "GET", "%s/repos/%s/releases/tags/%s"
                        % (API, cfg["repo"], RELEASE_TAG))["id"]
    except urllib.error.HTTPError as ex:
        if ex.code != 404:
            raise
    neu = _anfrage(cfg, "POST", "%s/repos/%s/releases" % (API, cfg["repo"]),
                   daten=json.dumps({
                       "tag_name": RELEASE_TAG,
                       "name": "PDF-Aufträge (Ablage, nicht löschen)",
                       "body": "Ablage des PDF-Briefkastens. Anhänge kommen "
                               "und gehen automatisch.",
                   }).encode("utf-8"),
                   kopf={"Content-Type": "application/json"})
    return neu["id"]


def anhaenge(cfg, rid) -> list:
    return _anfrage(cfg, "GET", "%s/repos/%s/releases/%s/assets?per_page=100"
                    % (API, cfg["repo"], rid))


def hochladen(cfg, rid, name, daten, typ):
    return _anfrage(cfg, "POST", "%s/repos/%s/releases/%s/assets?name=%s"
                    % (UPLOAD, cfg["repo"], rid, urllib.parse.quote(name)),
                    daten=daten, kopf={"Content-Type": typ})


def herunterladen(cfg, anhang_id) -> bytes:
    opener = urllib.request.build_opener(_OhneWeiterleitung)
    req = urllib.request.Request(
        "%s/repos/%s/releases/assets/%s" % (API, cfg["repo"], anhang_id),
        headers={"Authorization": "Bearer %s" % cfg["token"],
                 "Accept": "application/octet-stream",
                 "User-Agent": "ffpb-performancetool"})
    try:
        with opener.open(req, timeout=60) as antwort:
            return antwort.read()
    except urllib.error.HTTPError as ex:
        if ex.code not in (301, 302, 303, 307, 308):
            raise BriefkastenFehler(
                "PDF-Dienst: Download fehlgeschlagen (%s)." % ex.code) from ex
        ziel = ex.headers.get("Location")
    with urllib.request.urlopen(ziel, timeout=120) as antwort:
        return antwort.read()


def loeschen(cfg, anhang_id):
    _anfrage(cfg, "DELETE", "%s/repos/%s/releases/assets/%s"
             % (API, cfg["repo"], anhang_id), erwarte_json=False)


def lebenszeichen_alter(liste) -> float:
    """Sekunden seit dem juengsten Lebenszeichen; None, wenn keins da ist.

    Die Zeit steht im Namen (vom Dienst gesetzt), nicht im created_at von
    GitHub — so misst die App mit der Uhr des Dienstes gegen die eigene.
    """
    zeiten = []
    for a in liste:
        name = a.get("name", "")
        if name.startswith(LEBENSZEICHEN_PRAEFIX) and name.endswith(".txt"):
            try:
                zeiten.append(int(name[len(LEBENSZEICHEN_PRAEFIX):-4]))
            except ValueError:
                pass
    if not zeiten:
        return None
    return time.time() - max(zeiten)


def neuer_auftrag() -> str:
    """Auftragsname: UTC-Zeit + 8 Hex-Zeichen, z.B. 20260917-082256-00b0757a.

    Der Dienst nimmt NUR Dateien an, die auf `$AuftragMuster` in pdf_dienst.ps1
    passen — wer das Format hier aendert, aendert es dort mit
    (tests/test_pdf_briefkasten.py prueft beides gegeneinander).
    """
    return "%s-%s" % (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
                      _zufall.token_hex(4))


def dienst_erreichbar(cfg) -> bool:
    """True, wenn ein frisches Lebenszeichen im Briefkasten liegt. Fuer die
    Oberflaeche, um den PDF-Knopf gar nicht erst als "sofort"-Weg anzubieten,
    wenn niemand da ist. Fehler werden als "nicht erreichbar" gewertet."""
    try:
        alter = lebenszeichen_alter(anhaenge(cfg, release_id(cfg)))
    except BriefkastenFehler:
        return False
    return alter is not None and alter <= LEBENSZEICHEN_MAX_ALTER_S


def pdf_anfordern(cfg, pptx_bytes, warten_max_s=WARTEN_MAX_S,
                  abfrage_alle_s=ABFRAGE_ALLE_S, fortschritt=None) -> bytes:
    """Legt die PDF-Quelle (signiert) in den Briefkasten und wartet auf das PDF.

    Args:
        cfg: {"repo": "...", "token": "...", "hmac": "..."}
        pptx_bytes: die PowerPoint, die umgewandelt werden soll
            (in der App: die bereinigte `pdf_export.pptx_fuer_pdf(...)`-Fassung)
        fortschritt: optional f(text) fuer eine Statuszeile

    Raises:
        BriefkastenFehler — mit einem Satz fuer die Oberflaeche. Der eigene
        Auftrag wird dabei wieder aus dem Briefkasten entfernt.
    """
    def melde(text):
        if fortschritt:
            fortschritt(text)

    rid = release_id(cfg)
    alter = lebenszeichen_alter(anhaenge(cfg, rid))
    if alter is None or alter > LEBENSZEICHEN_MAX_ALTER_S:
        seit = ("nie" if alter is None else "vor %d Minuten" % (alter // 60))
        raise BriefkastenFehler(
            "Der PDF-Dienst ist gerade nicht erreichbar (letztes Lebenszeichen: "
            "%s). Bitte die PowerPoint herunterladen und in PowerPoint über "
            "„Speichern unter → PDF“ sichern." % seit)

    auftrag = neuer_auftrag()
    melde("Auftrag wird übermittelt …")
    # Signatur ZUERST hochladen, dann die .pptx: der Dienst verarbeitet einen
    # Auftrag erst, wenn beide da sind — so kann er nie eine unsignierte Datei
    # sehen.
    sig = signatur(pptx_bytes, cfg["hmac"]).encode("ascii")
    eigene = [hochladen(cfg, rid, auftrag + ".sig", sig, "text/plain"),
              hochladen(cfg, rid, auftrag + ".pptx", pptx_bytes, PPTX_TYP)]

    start = time.time()
    try:
        while time.time() - start < warten_max_s:
            time.sleep(abfrage_alle_s)
            namen = {a["name"]: a for a in anhaenge(cfg, rid)
                     if a.get("state") == "uploaded"}
            if auftrag + ".pdf" in namen:
                melde("PDF wird abgeholt …")
                a = namen[auftrag + ".pdf"]
                daten = herunterladen(cfg, a["id"])
                loeschen(cfg, a["id"])
                if not daten.startswith(b"%PDF"):
                    raise BriefkastenFehler(
                        "PDF-Dienst: Die zurückgelieferte Datei ist kein PDF.")
                return daten
            if auftrag + ".fehler.txt" in namen:
                a = namen[auftrag + ".fehler.txt"]
                text = herunterladen(cfg, a["id"]).decode("utf-8", "replace")
                loeschen(cfg, a["id"])
                raise BriefkastenFehler(
                    "PDF-Dienst meldet einen Fehler: %s" % text.strip()[:300])
            melde("PowerPoint wandelt um … (%d s)" % (time.time() - start))
        raise BriefkastenFehler(
            "Der PDF-Dienst hat nicht innerhalb von %d Sekunden geantwortet. "
            "Bitte später erneut versuchen oder die PowerPoint selbst als PDF "
            "speichern." % warten_max_s)
    finally:
        # Liegen die eigenen Anhaenge (.sig/.pptx) noch da, nicht als Leiche
        # zuruecklassen.
        try:
            offen = {a["id"] for a in anhaenge(cfg, rid)}
            for e in eigene:
                if e and e.get("id") in offen:
                    loeschen(cfg, e["id"])
        except BriefkastenFehler:
            pass
