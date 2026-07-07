# modules/download_helfer.py
"""
Neuer-Tab-Download für die PowerPoint-Broschüre (NEU 07.07.2026).

HINTERGRUND (Firmen-Gateway Atruvia / Skyhigh):
    st.download_button lädt die Datei über einen In-Page-Mechanismus
    (Fetch/Blob im aktuellen Tab). Das Atruvia-Gateway scannt den Download,
    liefert währenddessen eine `progress.htm` aus — und weil der In-Page-
    Mechanismus diese Zwischenseite als "die Datei" speichert, bekommt der
    Nutzer die progress.htm statt der PPTX. Der Scan wird nie sichtbar fertig.

    IT-Vorgabe: Den Scanner NICHT umgehen, sondern den Download in einem
    NEUEN TAB als echte Navigation ausführen. Dann zeigt Atruvia seine
    Scan-Status-Seite in diesem Tab an, und nach Abschluss lädt die echte
    Datei herunter (Standard-Atruvia-Verhalten).

LÖSUNG:
    Eine echte, im Browser navigierbare URL erzeugen und per Link mit
    target="_blank" öffnen. Streamlit hat dafür bereits den Core-Endpoint
    `/media/<id>.<ext>` (denselben, den st.download_button intern nutzt) —
    er liefert die Datei mit KORREKTEM Content-Type aus
    (application/vnd…presentation), nicht als text/plain wie das optionale
    Static-Serving. Damit navigiert der neue Tab sauber auf die Datei, das
    Gateway greift, und der Download endet als gültige PPTX.

    → KEINE config.toml-Änderung nötig (der /media-Endpoint ist immer aktiv).

⚠️ ANNAHME / RISIKO (bewusst markiert):
    Diese Funktion nutzt INTERNE Streamlit-APIs
    (streamlit.runtime.get_instance().media_file_mgr.add). Diese sind nicht
    Teil der offiziell stabilen API und können sich bei einem Streamlit-
    Update ändern — und die Community Cloud zieht Updates automatisch
    (siehe Transferwissen #20). Deshalb:
      1. Der Aufruf ist in try/except gekapselt und gibt bei JEDEM Problem
         None zurück (kein Crash).
      2. Der aufrufende Code MUSS als Fallback den klassischen
         st.download_button behalten (siehe Integrations-Snippet unten).
    Verifiziert gegen Streamlit 1.59.0 (add()-Signatur inkl.
    is_for_static_download; Endpoint MEDIA_ENDPOINT = "/media").
"""

from __future__ import annotations

# MIME-Type der PPTX (OpenXML). Damit liefert der /media-Endpoint die Datei
# mit korrektem Content-Type aus → der neue Tab lädt sie als Datei herunter
# (statt Binärmüll als Text zu rendern).
PPTX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.presentation"
)


def medien_download_url(daten: bytes, dateiname: str,
                        mimetype: str = PPTX_MIMETYPE) -> str | None:
    """Registriert `daten` im Streamlit-Media-Manager und gibt eine echte,
    im Browser navigierbare URL (z.B. "/media/<hash>.pptx") zurück.

    Diese URL kann in einem Link mit target="_blank" geöffnet werden → der
    neue Tab navigiert echt auf die Datei (Gateway-Scan sichtbar), der
    Download endet als gültige PPTX.

    Returns:
        Die URL (str) bei Erfolg, sonst None. Bei None MUSS der aufrufende
        Code auf den klassischen st.download_button zurückfallen.
    """
    try:
        # Import bewusst LOKAL (interne API) — hält den Modulkopf sauber und
        # verhindert, dass ein etwaiger künftiger Import-Fehler die ganze
        # App beim Start reißt.
        from streamlit import runtime

        instanz = runtime.get_instance()
        if instanz is None:
            return None

        # add() liefert die persistente Download-URL. is_for_static_download=
        # True entkoppelt die Datei von einer Widget-Lebensdauer (wie es
        # st.download_button intern tut). coordinates ist nur ein
        # Identitäts-String; die Deduplizierung erfolgt ohnehin über den
        # Inhalts-Hash.
        url = instanz.media_file_mgr.add(
            daten,
            mimetype,
            coordinates="download_helfer/pptx",
            file_name=dateiname,
            is_for_static_download=True,
        )
        # Plausibilität: erwartet wird etwas wie "/media/<hash>.pptx".
        if isinstance(url, str) and url:
            return url
        return None
    except Exception:
        # Jeder Fehler (API-Änderung nach Streamlit-Update, kein Runtime-
        # Kontext, …) → None. Der Aufrufer nutzt dann den Fallback-Button.
        return None
