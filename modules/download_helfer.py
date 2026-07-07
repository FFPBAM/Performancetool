# modules/download_helfer.py
"""
Neuer-Tab-Download für die PowerPoint-Broschüre (NEU 07.07.2026).

HINTERGRUND (Firmen-Gateway Atruvia / Skyhigh):
    st.download_button lädt die Datei über einen In-Page-Mechanismus
    (Fetch/Blob im aktuellen Tab). Das Atruvia-Gateway scannt den Download,
    liefert währenddessen eine `progress.htm` aus — und weil der In-Page-
    Mechanismus diese Zwischenseite als "die Datei" speichert, bekommt der
    Nutzer die progress.htm statt der PPTX.

    IT-Vorgabe: Den Scanner NICHT umgehen, sondern den Download in einem
    NEUEN TAB als echte Navigation ausführen. Dann zeigt Atruvia seine
    Scan-Status-Seite in diesem Tab an, und nach Abschluss lädt die echte
    Datei herunter.

LÖSUNG:
    Eine echte, im Browser navigierbare URL erzeugen (der Core-Endpoint
    `/media/<id>.<ext>`, den auch st.download_button intern nutzt) und per
    Link mit target="_blank" öffnen. Der Endpoint liefert die Datei mit
    korrektem Content-Type UND als echten Download aus (im Streamlit-Code
    verifiziert: Content-Disposition: attachment). KEINE config.toml-
    Änderung nötig.

⚠️ COMMUNITY-CLOUD-PFAD (Grund für das "ewige Laden", 07.07.2026):
    media_file_mgr.add() liefert die URL als "/media/<id>.pptx" (domain-
    absolut). Auf Streamlit Community Cloud wird die Datei extern aber unter
    dem Präfix "/~/+" serviert, also "/~/+/media/<id>.pptx" (so in Philips
    Übergabe beobachtet). Ein neuer Tab, der "/media/..." OHNE Präfix
    ansteuert, trifft nicht den Media-Handler, sondern bootet die App neu
    → der Tab lädt endlos.
    → Deshalb testet download_bereich() BEIDE Varianten (A = roh,
      B = mit "/~/+"-Präfix). Sobald klar ist, welche lädt, bleibt nur die.

⚠️ ANNAHME / RISIKO (bewusst markiert):
    medien_download_url() nutzt INTERNE Streamlit-APIs
    (streamlit.runtime.get_instance().media_file_mgr.add). Nicht Teil der
    stabilen API; kann bei einem Streamlit-Update brechen (die Cloud zieht
    Updates automatisch, siehe Transferwissen #20). Deshalb: try/except →
    None; der klassische st.download_button bleibt IMMER als Fallback.
    Verifiziert gegen Streamlit 1.59.0.
"""

from __future__ import annotations

PPTX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.presentation"
)


def medien_download_url(daten: bytes, dateiname: str,
                        mimetype: str = PPTX_MIMETYPE) -> str | None:
    """Registriert `daten` im Streamlit-Media-Manager und gibt die echte,
    im Browser navigierbare URL zurück (z.B. "/media/<hash>.pptx").

    Returns die URL (str) bei Erfolg, sonst None. Bei None MUSS der
    aufrufende Code auf den klassischen st.download_button zurückfallen.
    """
    try:
        from streamlit import runtime
        instanz = runtime.get_instance()
        if instanz is None:
            return None
        url = instanz.media_file_mgr.add(
            daten,
            mimetype,
            coordinates="download_helfer/pptx",
            file_name=dateiname,
            is_for_static_download=True,
        )
        if isinstance(url, str) and url:
            return url
        return None
    except Exception:
        return None


def _button_link_html(href: str, label: str) -> str:
    """Ein als Streamlit-Button gestylter HTML-Anker, der IMMER in einem
    neuen Tab öffnet (target="_blank"). Echter Anker statt st.link_button,
    damit garantiert exakt dieser href genutzt wird (keine URL-Normalisierung).
    """
    return (
        f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
        f'style="display:block;box-sizing:border-box;width:100%;'
        f'text-align:center;padding:0.5rem 0.75rem;margin:0.15rem 0;'
        f'border:1px solid rgba(49,51,63,0.2);border-radius:0.5rem;'
        f'background:#fff;color:#003460;font-weight:600;'
        f'text-decoration:none;">{label}</a>'
    )


def download_bereich(daten: bytes, dateiname: str) -> None:
    """Rendert den kompletten Download-Bereich der Broschüre.

    STAND 07.07.2026 — DIAGNOSE-MODUS: Zeigt zwei Neuer-Tab-Varianten
    (A = Standardpfad, B = mit Community-Cloud-Präfix "/~/+") plus den
    klassischen In-Page-Download als Fallback. Sobald klar ist, welche
    Variante lädt, wird der Bereich auf die eine Variante reduziert.
    """
    import streamlit as st

    url = medien_download_url(daten, dateiname)

    if url:
        # Variante B: mit Community-Cloud-Präfix. Nur ergänzen, wenn die URL
        # wie erwartet mit "/media/" beginnt (sonst unverändert lassen).
        url_b = ("/~/+" + url) if url.startswith("/media/") else url

        st.caption("🔧 **Download-Test (Gateway-Diagnose):** Bitte **A** und **B** "
                   "je in einem neuen Tab öffnen. Gesucht ist die Variante, die eine "
                   "**öffenbare .pptx** lädt (statt endlos zu laden oder die App neu "
                   "zu starten).")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(_button_link_html(url, "📥 A) Standardpfad"),
                        unsafe_allow_html=True)
        with c2:
            st.markdown(_button_link_html(url_b, "📥 B) mit /~/+ Präfix"),
                        unsafe_allow_html=True)
        st.caption(f"A = `{url}`  ·  B = `{url_b}`")
        st.markdown("---")

    # FALLBACK / KLASSISCH — bleibt IMMER stehen (funktioniert für den
    # direkten Download-Pfad; nur der Gateway-Scan kann hier die progress.htm
    # erzeugen). Auch aktiv, wenn medien_download_url None lieferte.
    st.download_button(
        "⬇️ Klassischer Download (In-Page, Fallback)",
        data=daten,
        file_name=dateiname,
        mime=PPTX_MIMETYPE,
        key="pf_pptx_dl",
        use_container_width=True,
    )
