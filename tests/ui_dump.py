"""Werkzeug, kein Test: zieht den sichtbaren Zustand der Oberflaeche ab.

Fuer Broschueren gibt es den rekursiven ZIP-Vergleich als Beweis, dass ein
Umbau nichts veraendert hat. Fuer die Oberflaeche gab es bis zum 12.08.2026
nichts Vergleichbares — dieses Skript schliesst die Luecke:

    python tests/ui_dump.py vorher.json      # vor dem Umbau
    ... umbauen ...
    python tests/ui_dump.py nachher.json     # danach
    fc vorher.json nachher.json              # (oder git diff --no-index)

Abgezogen werden alle Kennzahlen (st.metric), Captions, Markdown-Bloecke,
Ueberschriften und Tabellen der Standard-Ansicht. Sind beide Dateien
zeichengleich, zeigt die Oberflaeche dasselbe wie vorher.

ZWEITE ANSICHT (17.08.2026): Bis dahin erfasste das Skript ausschliesslich die
Performance-Ansicht — fuer die Portfolioanalyse gab es also gar keinen
Vorher/Nachher-Beweis, obwohl dort Einzeltitel-Tabelle, Ringe und
Anleihen-Block haengen. Ein zweites Argument waehlt die Ansicht:

    python tests/ui_dump.py vorher_pf.json portfolio

Ohne das Argument bleibt alles wie bisher (Ansicht "Performance"), damit
aeltere Dumps weiter vergleichbar sind.

GRENZEN — ehrlich gesagt: Erfasst wird nur, was OHNE Interaktion gerendert
wird. Wer einen Bedienpfad prueft (Zeitraum umstellen, Vergleich einschalten),
braucht zusaetzlich eine AppTest-Suite, die klickt — siehe test_bedienung.py.

Braucht streamlit und die echten Daten. Fehlt etwas davon, bricht es mit
einer klaren Meldung ab statt stillschweigend eine leere Datei zu schreiben.
"""

import json
import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    print("ABBRUCH — streamlit ist nicht installiert.")
    sys.exit(2)


# Die Ansicht haengt an session_state["nav_view"] (segmented_control in
# streamlit_app.py). Die Namen stehen dort als _VIEW_PERF/_VIEW_PF; hier
# bewusst als Klartext, damit das Werkzeug nichts aus der App importieren muss.
ANSICHTEN = {"performance": "Performance", "portfolio": "Portfolioanalyse"}


def dump(ziel, ansicht="performance"):
    at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                           default_timeout=400)
    # Der Login wird uebersprungen; secrets muessen trotzdem gesetzt sein,
    # sonst bricht check_login ab, bevor irgendetwas gerendert wird.
    at.secrets["passwords"] = {"t": "t"}
    at.session_state["logged_in"] = True
    at.session_state["username"] = "t"
    if ansicht != "performance":
        at.session_state["nav_view"] = ANSICHTEN[ansicht]
    at.run()

    daten = {
        "exceptions": [str(e.value)[:300] for e in at.exception],
        "metrics": [{"label": m.label, "value": str(m.value)} for m in at.metric],
        "captions": [c.value for c in at.caption],
        "markdown": [m.value for m in at.markdown],
        "subheader": [s.value for s in at.subheader],
    }
    try:
        daten["dataframes"] = [df.value.to_json() for df in at.dataframe]
    except Exception as ex:
        daten["dataframes"] = [f"NICHT LESBAR: {type(ex).__name__}: {ex}"]

    # sort_keys + feste Einrueckung: Die Datei muss zwischen zwei Laeufen
    # zeichengleich sein, sonst taugt der Vergleich nichts.
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"{len(daten['metrics'])} Kennzahlen, {len(daten['captions'])} Captions, "
          f"{len(daten['markdown'])} Markdown-Bloecke, "
          f"{len(daten['dataframes'])} Tabellen -> {ziel}")
    if daten["exceptions"]:
        print("ACHTUNG — die App warf beim Rendern:")
        for e in daten["exceptions"]:
            print("   " + e)
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    _ansicht = sys.argv[2].lower() if len(sys.argv) > 2 else "performance"
    if _ansicht not in ANSICHTEN:
        print(f"ABBRUCH — unbekannte Ansicht {_ansicht!r}, "
              f"moeglich: {', '.join(sorted(ANSICHTEN))}")
        sys.exit(2)
    sys.exit(dump(sys.argv[1], _ansicht))
