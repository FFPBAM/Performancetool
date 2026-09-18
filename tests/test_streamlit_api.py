"""Prueft, dass keine veralteten Streamlit-Parameter im Code stehen.

HINTERGRUND (11.08.2026):
    `use_container_width` ist abgekuendigt. Streamlit warnt bei JEDEM Aufruf
    (das flutet das Deploy-Log) und wird den Parameter in einer kuenftigen
    Version entfernen — dann bricht die App beim naechsten Cloud-Update,
    genau wie beim Ausfall vom 06.07.2026 (Transferwissen #20).

    Umgestellt wurden 33 Aufrufe. Die Regel ergibt sich aus den echten
    Signaturen von Streamlit 1.61:

      dataframe / plotly_chart / data_editor   Default ist bereits "stretch"
          use_container_width=True   -> ersatzlos gestrichen
      button / download_button                 Default ist "content"
          use_container_width=True   -> width="stretch"

NACHTRAG 18.09.2026 — `st.components.v1.html` ist ebenfalls abgekuendigt
    ("will be removed after 2026-06-01"). Der Broschueren-Download
    (modules/download_helfer.py) laeuft jetzt ueber `st.iframe`. Schritt 2
    sichert zu, dass dabei das Element entsteht, auf dem der clientseitige
    Download (Gateway, Transferwissen #25) beruht — braucht Streamlit, wird
    ohne das Paket uebersprungen.

WARUM ALS TEST UND NICHT NUR IM CHANGELOG:
    Der Parameter ist bequem und steht in jeder aelteren Anleitung im Netz.
    Ohne Sperre schleicht er sich beim naechsten Copy-Paste zurueck.

    python tests/test_streamlit_api.py     (braucht kein einziges Paket)
"""

import glob
import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Abgekuendigter Parameter -> was stattdessen zu nehmen ist
VERBOTEN = {
    "use_container_width":
        'width="stretch"/"content" — bei dataframe/plotly_chart/data_editor '
        'ist "stretch" bereits Default, dort ersatzlos streichen',
    # Das Custom-Components-Modul selbst bleibt erlaubt (declare_component) —
    # verboten sind nur seine beiden abgekuendigten Kurzformen.
    "components.html(":
        "st.iframe(html, height=...) — siehe modules/download_helfer.py",
    "components.iframe(":
        "st.iframe(url, height=...)",
}


def _dateien():
    yield os.path.join(WURZEL, "streamlit_app.py")
    for p in sorted(glob.glob(os.path.join(WURZEL, "modules", "*.py"))):
        yield p


def main():
    fehler = 0
    geprueft = 0
    for pfad in _dateien():
        if not os.path.exists(pfad):
            continue
        geprueft += 1
        rel = os.path.relpath(pfad, WURZEL)
        with open(pfad, encoding="utf-8") as fh:
            zeilen = fh.readlines()
        for nr, zeile in enumerate(zeilen, 1):
            # Kommentare und Doku duerfen den Namen nennen — dieser Test
            # selbst und der Changelog erklaeren die Umstellung ja.
            if zeile.lstrip().startswith("#"):
                continue
            for param, statt in VERBOTEN.items():
                if param in zeile:
                    fehler += 1
                    print(f"   FEHLER {rel}:{nr} — '{param}' ist abgekuendigt")
                    print(f"          {zeile.strip()[:90]}")
                    print(f"          stattdessen: {statt}")

    # Gegenprobe: Die Suche muss die alte Zeile aus download_helfer finden,
    # sonst prueft sie nichts.
    alt = "    components.html(_download_komponente_html(daten, dateiname, art), height=90)"
    if not any(param in alt for param in VERBOTEN):
        fehler += 1
        print("   FEHLER — die Gegenprobe greift nicht: die alte Aufrufzeile "
              "wuerde nicht erkannt")
    else:
        print("   OK — Gegenprobe: die alte Aufrufzeile wuerde erkannt")

    fehler += schritt2_download_iframe()

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print(f"BESTANDEN — {geprueft} Dateien, keine abgekuendigten Aufrufe, "
          "Download-iframe wie zugesichert")
    return 0


def schritt2_download_iframe():
    """Der Download-Baustein erzeugt genau das iframe, das der Blob-Download
    braucht (gemessen 18.09.2026 gegen die alte Fassung, Streamlit 1.61):

      - Elementtyp "iframe" mit dem HTML als srcdoc (kein src — ein src
        waere ein Server-Abruf, und genau den scannt das Gateway)
      - feste Hoehe 90, Breite "stretch" (wie components.html)
      - `overflow: hidden` im HTML, weil st.iframe immer scrolling=True
        setzt; die alte Fassung hatte scrolling=False
      - der Knopf samt Download-Skript steckt im srcdoc

    Die Sandbox (allow-scripts, allow-downloads) setzt das Frontend fuer
    jedes iframe-Element gleich; sie steht nicht im Element und ist hier
    nicht pruefbar — dafuer bleibt die Probe im Firmennetz.
    """
    print("Schritt 2 — Download-Baustein erzeugt das zugesicherte iframe")
    try:
        from streamlit.delta_generator import DeltaGenerator
    except ImportError:
        print("   UEBERSPRUNGEN — streamlit nicht installiert")
        return 0
    sys.path.insert(0, WURZEL)
    from modules.download_helfer import download_bereich

    gefangen = []
    orig = DeltaGenerator._enqueue

    def fang(self, delta_type, element_proto, *a, **kw):
        gefangen.append((delta_type, element_proto, kw.get("layout_config")))
        return orig(self, delta_type, element_proto, *a, **kw)

    DeltaGenerator._enqueue = fang
    try:
        download_bereich(b"PK Testinhalt", "Test_16.09.2026.pptx", "pptx")
    finally:
        DeltaGenerator._enqueue = orig

    iframes = [(p, lc) for t, p, lc in gefangen if t == "iframe"]
    if len(iframes) != 1:
        print(f"   FEHLER — {len(iframes)} iframe-Elemente statt 1")
        return 1
    proto, layout = iframes[0]
    f = 0
    pruefungen = [
        ("HTML steht als srcdoc", bool(proto.srcdoc)),
        ("kein src (kein Server-Abruf)", not proto.src),
        ("Hoehe 90", layout is not None and layout.height == 90),
        ("Breite stretch", layout is not None and layout.width == "stretch"),
        ("overflow: hidden gegen den Scrollbalken",
         "overflow: hidden" in proto.srcdoc),
        ("Knopf und Blob-Download im srcdoc",
         'id="dlbtn"' in proto.srcdoc and "createObjectURL" in proto.srcdoc),
    ]
    for text, ok in pruefungen:
        print(f"   {'OK' if ok else 'FEHLER'} — {text}")
        f += 0 if ok else 1
    return f


if __name__ == "__main__":
    sys.exit(main())
