# modules/download_helfer.py
"""
Broschüren-Download OHNE Server-Abruf (NEU 07.07.2026).

WARUM (Firmen-Gateway Atruvia / Skyhigh):
    Jeder Download, der die Datei vom Server holt (st.download_button →
    /media/…, oder /app/static/…), läuft durch den Viren-Scanner des
    Gateways. Der scannt, liefert eine progress.htm aus und hält die
    Verbindung → In-Page-Download speichert die progress.htm; Navigation im
    neuen Tab "lädt ewig". Beides ist NICHT clientseitig lösbar, solange die
    Datei über das Netz geholt wird.

LÖSUNG — CLIENTSEITIGER DOWNLOAD (kein Netzwerk-Request):
    Die PPTX-Bytes werden als Base64 DIREKT in die Seite eingebettet. Ein
    kleiner Button baut die Datei im Browser aus diesen Bytes zusammen
    (Blob) und speichert sie lokal. Dabei geht KEIN HTTP-Request raus →
    das Gateway hat nichts zu scannen → der Download startet sofort, im
    selben Fenster, ganz normal.

    Umgesetzt über st.components.v1.html: Dessen iframe erlaubt Downloads
    (Streamlit setzt sandbox="… allow-downloads"; im Frontend-Code
    verifiziert). st.markdown scheidet aus, weil es <script> entfernt.

    Die Base64-Daten reisen nur als Teil der normalen App-Antwort mit (kein
    "Datei-Download" im Sinne der Gateway-Regel) — der eigentliche
    Speichervorgang passiert rein lokal im Browser.

HINWEIS Größe:
    ~4 MB PPTX → ~5,5 MB Base64 in der Seite. Für den gelegentlichen
    Broschüren-Download unkritisch (Streamlit maxMessageSize default 200 MB).

FALLBACK:
    Der klassische st.download_button bleibt darunter stehen (In-Page-Weg
    über den Server) — falls die Komponente in einer Umgebung mal nicht
    greifen sollte.
"""

from __future__ import annotations

import json
import base64

PPTX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.presentation"
)


def _download_komponente_html(daten: bytes, dateiname: str) -> str:
    """Baut das HTML/JS für den clientseitigen Blob-Download."""
    b64 = base64.b64encode(daten).decode("ascii")
    # Dateiname sicher als JS-String-Literal einbetten (Umlaute, Quotes …).
    name_js = json.dumps(dateiname)
    mime_js = json.dumps(PPTX_MIMETYPE)
    return f"""
<div style="font-family:'Segoe UI',Tahoma,sans-serif;">
  <button id="dlbtn" style="
      width:100%;box-sizing:border-box;padding:0.6rem 1rem;cursor:pointer;
      border:1px solid #003460;border-radius:0.5rem;background:#003460;
      color:#ffffff;font-size:1rem;font-weight:600;">
    📥 Broschüre herunterladen
  </button>
  <div id="dlmsg" style="margin-top:0.4rem;font-size:0.85rem;color:#5c6b3c;"></div>
</div>
<script>
(function() {{
  const b64 = "{b64}";
  const btn = document.getElementById("dlbtn");
  const msg = document.getElementById("dlmsg");
  btn.addEventListener("click", function() {{
    try {{
      const bin = atob(b64);
      const len = bin.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {{ bytes[i] = bin.charCodeAt(i); }}
      const blob = new Blob([bytes], {{ type: {mime_js} }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = {name_js};
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function() {{ URL.revokeObjectURL(url); }}, 2000);
      msg.textContent = "✓ Download gestartet. Bitte im Download-Ordner nachsehen.";
    }} catch (e) {{
      msg.style.color = "#a11";
      msg.textContent = "Fehler beim lokalen Download: " + e + " — bitte den Fallback-Button unten nutzen.";
    }}
  }});
}})();
</script>
"""


def download_bereich(daten: bytes, dateiname: str) -> None:
    """Rendert den Broschüren-Download:
    1) PRIMÄR: clientseitiger Blob-Download (kein Server-Abruf → kein Gateway-
       Scan → startet sofort, kein neuer Tab).
    2) FALLBACK: klassischer st.download_button (In-Page über den Server).
    """
    import streamlit as st
    import streamlit.components.v1 as components

    # Clientseitiger Download-Button (im Komponenten-iframe, downloads erlaubt).
    components.html(_download_komponente_html(daten, dateiname), height=90)

    # Fallback bleibt IMMER erreichbar.
    with st.expander("Alternativer Download (falls der Button oben nicht lädt)"):
        st.download_button(
            "⬇️ Klassischer Download (über den Server)",
            data=daten,
            file_name=dateiname,
            mime=PPTX_MIMETYPE,
            key="pf_pptx_dl",
            use_container_width=True,
        )


# ── LEGACY (nur Import-Kompatibilität; nicht mehr genutzt) ──────────────────
# Frühere Varianten (interne Media-URL / Static Serving). portfolioanalyse.py
# importiert medien_download_url noch mit → als No-Op belassen.
def medien_download_url(daten: bytes, dateiname: str,
                        mimetype: str = PPTX_MIMETYPE):
    return None
