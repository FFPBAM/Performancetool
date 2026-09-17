# modules/pdf_briefkasten.py
"""
PDF-Briefkasten — die App laesst die PDF-Umwandlung von echtem PowerPoint
machen (NEU 17.09.2026).

WARUM ES DAS GIBT: Das PDF der Broschuere soll so aussehen wie
"Speichern unter -> PDF" in Desktop-PowerPoint. Auf Streamlit Cloud (Linux)
gibt es kein PowerPoint; LibreOffice zeichnet die Ringe falsch (Probe
17.09.2026), Microsoft 365 scheitert an der IT. Also wandelt ein Buero-PC mit
PowerPoint um (`pdf_dienst/pdf_dienst.ps1`), und GitHub dient als Briefkasten
dazwischen.

WARUM RELEASE-ANHAENGE UND KEINE COMMITS: Eine Datei, die committet und
wieder geloescht wird, bleibt fuer immer in der Git-Historie. Anhaenge an
einem Release lassen sich hochladen und loeschen, ohne Spuren. Das Repo
`FFPBAM/pdf-briefkasten` ist privat und hat genau einen Release (Tag
`auftraege`), der nur als Ablage dient.

ABLAUF (Namen sind das Protokoll — der Dienst liest dieselben):
    App    laedt  <auftrag>.pptx   hoch
    Dienst holt   <auftrag>.pptx,  loescht sie, wandelt um
    Dienst laedt  <auftrag>.pdf    hoch   (oder <auftrag>.fehler.txt)
    App    holt   <auftrag>.pdf,   loescht sie
    Dienst legt jede Minute lebenszeichen-<unixzeit>.txt ab und raeumt die
    alten weg — daran erkennt die App VOR dem Hochladen, ob jemand da ist.

Nur Standardbibliothek (urllib), damit requirements.txt unberuehrt bleibt.
Streamlit-frei wie `pptx_export`.
"""

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

WARTEN_MAX_S = 120
ABFRAGE_ALLE_S = 2.0

PPTX_TYP = ("application/vnd.openxmlformats-officedocument."
            "presentationml.presentation")


class BriefkastenFehler(Exception):
    """Fehler mit einem Satz, der so in der Oberflaeche stehen kann."""


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
        "User-Agent": "ffpb-pdf-briefkasten",
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
                "(GitHub 401) — Schlüssel erneuern, siehe STATUS.md.") from ex
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
                 "User-Agent": "ffpb-pdf-briefkasten"})
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
    GitHub — so misst die App mit der Uhr des Dienstes gegen die eigene, und
    ein falsch gehender PC-Takt faellt als "zu alt" auf statt still.
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


def pdf_anfordern(cfg, pptx_bytes, warten_max_s=WARTEN_MAX_S,
                  abfrage_alle_s=ABFRAGE_ALLE_S, fortschritt=None) -> bytes:
    """Legt die PDF-Quelle in den Briefkasten und wartet auf das PDF.

    Args:
        cfg: {"repo": "FFPBAM/pdf-briefkasten", "token": "..."}
        pptx_bytes: die PowerPoint, die umgewandelt werden soll
            (in der App: `pdf_export.pptx_fuer_pdf(...)[0]`)
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

    auftrag = "%s-%s" % (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
                         _zufall.token_hex(4))
    melde("Auftrag wird übermittelt …")
    eigener = hochladen(cfg, rid, auftrag + ".pptx", pptx_bytes, PPTX_TYP)

    start = time.time()
    try:
        while time.time() - start < warten_max_s:
            time.sleep(abfrage_alle_s)
            # Nur fertig hochgeladene Anhaenge: GitHub listet sie schon
            # waehrend des Uploads (state "starter"), herunterladen geht
            # dann noch nicht (404) — am 17.09.2026 so im Durchstich passiert.
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
        # Liegt der eigene Auftrag noch da (Zeitueberschreitung, Fehler),
        # nicht als Leiche zuruecklassen.
        try:
            if any(a["id"] == eigener["id"] for a in anhaenge(cfg, rid)):
                loeschen(cfg, eigener["id"])
        except BriefkastenFehler:
            pass
