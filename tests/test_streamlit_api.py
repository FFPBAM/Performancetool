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

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} veraltete(r) Aufruf(e)")
        return 1
    print(f"BESTANDEN — {geprueft} Dateien, keine abgekuendigten Parameter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
