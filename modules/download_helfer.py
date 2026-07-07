# modules/download_helfer.py
"""
Broschüren-Download über Streamlits offizielles STATIC FILE SERVING
(NEU 07.07.2026, ersetzt den fragilen Media-URL-Weg).

WARUM (Firmen-Gateway Atruvia / Skyhigh):
    st.download_button lädt über einen In-Page-Mechanismus (Fetch/Blob). Das
    Gateway schiebt beim Scan eine progress.htm dazwischen, die als "Datei"
    gespeichert wird → der Nutzer bekommt progress.htm statt der PPTX.
    IT-Vorgabe: NICHT den Scanner umgehen, sondern den Download als echte
    Navigation in einem NEUEN TAB ausführen — dort zeigt Atruvia seinen
    Scan-Status, nach Abschluss lädt die echte Datei.

WARUM STATIC SERVING (statt der internen Media-URL):
    Der erste Versuch nutzte die interne Media-URL (/media/<id>.pptx). Auf
    Streamlit Community Cloud trifft dieser Pfad NICHT den Media-Handler,
    sondern bootet die App neu → der neue Tab "lädt ewig" (im Deploy-Log
    bewiesen: Aufruf von /media/… startete die App).
    Static File Serving ist der robuste Weg:
      • Offizielle, STABILE API (kein internes streamlit.runtime nötig).
      • FESTER, vorhersagbarer Pfad:  /app/static/<datei>
      • Die Datei liegt echt auf der Platte → kann nicht "nicht gefunden"
        werden (anders als die session-flüchtige Media-Datei).
      • .pptx wird mit KORREKTEM Content-Type ausgeliefert (in Streamlit
        1.59.0 verifiziert: guess_content_type → application/vnd…presentation),
        d.h. der neue Tab lädt eine öffenbare Datei statt Text-Müll.
      • Max. Dateigröße 200 MB (unsere Broschüre ~4 MB) — unkritisch.

VORAUSSETZUNG:
    In  .streamlit/config.toml  muss stehen:
        [server]
        enableStaticServing = true
    Der Ordner  static/  wird von diesem Modul bei Bedarf selbst angelegt
    (neben streamlit_app.py, dort erwartet Streamlit ihn).

HINWEIS Content-Disposition:
    Static Serving setzt KEIN "attachment" — der Download-Dateiname ergibt
    sich aus dem letzten URL-Segment. Deshalb schreiben wir die Datei unter
    static/<token>/<schöner_name>.pptx: der <token>-Unterordner macht die URL
    eindeutig (keine Kollision bei mehreren Beratern gleichzeitig), der
    Dateiname bleibt sauber und landet genau so im Download.
"""

from __future__ import annotations

import os
import re
import time
import uuid
import hashlib

PPTX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.presentation"
)

# static/ liegt neben dem Entrypoint (streamlit_app.py im Repo-Root). Dieses
# Modul liegt in modules/ → Repo-Root ist genau eine Ebene höher.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATIC_DIR = os.path.join(_REPO_ROOT, "static")
_URL_PREFIX = "/app/static"  # externer Pfad (Community Cloud: baseUrlPath leer)


def _sanitize(name: str) -> str:
    """Dateinamen URL-/dateisystem-sicher machen, .pptx sicherstellen."""
    name = str(name).strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not name.lower().endswith(".pptx"):
        name += ".pptx"
    return name or "Broschuere.pptx"


def _cleanup_old(max_alter_sekunden: int = 2 * 3600) -> None:
    """Alte Token-Ordner entfernen, damit die (ephemere) Platte nicht
    vollläuft. Fehler werden bewusst geschluckt (Aufräumen ist Best-Effort)."""
    try:
        if not os.path.isdir(_STATIC_DIR):
            return
        jetzt = time.time()
        for eintrag in os.listdir(_STATIC_DIR):
            pfad = os.path.join(_STATIC_DIR, eintrag)
            try:
                if os.path.isdir(pfad) and (jetzt - os.path.getmtime(pfad)) > max_alter_sekunden:
                    for f in os.listdir(pfad):
                        try:
                            os.remove(os.path.join(pfad, f))
                        except Exception:
                            pass
                    os.rmdir(pfad)
            except Exception:
                pass
    except Exception:
        pass


def statische_download_url(daten: bytes, dateiname: str) -> str | None:
    """Schreibt `daten` nach static/<token>/<dateiname> und gibt die echte,
    im neuen Tab navigierbare URL '/app/static/<token>/<dateiname>' zurück.

    Returns die URL oder None (dann Fallback auf st.download_button).
    """
    try:
        safe = _sanitize(dateiname)
        token = uuid.uuid4().hex[:12]
        ordner = os.path.join(_STATIC_DIR, token)
        os.makedirs(ordner, exist_ok=True)
        with open(os.path.join(ordner, safe), "wb") as fh:
            fh.write(daten)
        _cleanup_old()
        return f"{_URL_PREFIX}/{token}/{safe}"
    except Exception:
        return None


def _url_datei_existiert(url: str) -> bool:
    """Prüft, ob die Datei zu einer zuvor erzeugten /app/static-URL noch auf
    der Platte liegt (die Cloud kann zwischendurch neu gestartet haben)."""
    try:
        rel = url[len(_URL_PREFIX) + 1:]  # "token/name.pptx"
        return os.path.isfile(os.path.join(_STATIC_DIR, *rel.split("/")))
    except Exception:
        return False


def _button_link_html(href: str, label: str) -> str:
    """Als Streamlit-Button gestylter HTML-Anker, der IMMER in einem neuen
    Tab öffnet (target="_blank"). Echter Anker (kein st.link_button), damit
    garantiert exakt dieser href genutzt wird. BEWUSST OHNE download-Attribut:
    so navigiert der Tab echt auf die URL → das Gateway kann seine
    Scan-Status-Seite zeigen (genau das wollte die IT)."""
    return (
        f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
        f'style="display:block;box-sizing:border-box;width:100%;'
        f'text-align:center;padding:0.55rem 0.75rem;margin:0.15rem 0;'
        f'border:1px solid rgba(49,51,63,0.2);border-radius:0.5rem;'
        f'background:#ffffff;color:#003460;font-weight:600;'
        f'text-decoration:none;">{label}</a>'
    )


def download_bereich(daten: bytes, dateiname: str) -> None:
    """Rendert den kompletten Broschüren-Download:
    1) PRIMÄR: Link, der die Broschüre im NEUEN TAB über /app/static öffnet
       (Gateway-Scan sichtbar) — die Datei wird pro Inhalt nur EINMAL auf die
       Platte geschrieben (Cache über session_state, Hash-basiert).
    2) FALLBACK: klassischer In-Page-Download (bleibt immer erreichbar).
    """
    import streamlit as st

    # Datei nur einmal pro Inhalt schreiben (nicht bei jedem Rerun neu).
    h = hashlib.md5(daten).hexdigest()[:12]
    cache = st.session_state.get("_static_dl_cache")
    url = None
    if cache and cache.get("hash") == h and cache.get("url") and _url_datei_existiert(cache["url"]):
        url = cache["url"]
    if url is None:
        url = statische_download_url(daten, dateiname)
        if url:
            st.session_state["_static_dl_cache"] = {"hash": h, "url": url}

    if url:
        st.markdown(
            _button_link_html(url, "📥 Broschüre herunterladen (öffnet neuen Tab)"),
            unsafe_allow_html=True,
        )
        st.caption("Öffnet einen neuen Tab. Dort läuft der Viren-Scan des "
                   "Firmen-Gateways sichtbar durch; danach startet der Download "
                   "automatisch.")
        st.markdown("---")

    # FALLBACK / KLASSISCH — bleibt IMMER stehen (funktioniert für den
    # direkten Download-Pfad; nur der Gateway-Scan kann hier die progress.htm
    # erzeugen). Auch aktiv, wenn statische_download_url None lieferte.
    st.download_button(
        "⬇️ Klassischer Download (In-Page, Fallback)",
        data=daten,
        file_name=dateiname,
        mime=PPTX_MIMETYPE,
        key="pf_pptx_dl",
        use_container_width=True,
    )


# ── LEGACY (nicht mehr genutzt, nur Import-Kompatibilität) ──────────────────
# Frühere interne Media-URL-Variante. portfolioanalyse.py importiert den Namen
# noch mit; deshalb hier als No-Op-kompatible Funktion belassen. Nicht mehr
# verwenden — der Community-Cloud-Pfad /media/… bootet die App (siehe oben).
def medien_download_url(daten: bytes, dateiname: str,
                        mimetype: str = PPTX_MIMETYPE) -> str | None:
    return None
