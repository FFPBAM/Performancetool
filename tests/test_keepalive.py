"""Pruefstein fuer die Keep-Alive-Sperre (NEU 18.08.2026, nach einem Ausfall).

`streamlit_app.py` re-assigniert am Skriptanfang ALLE session_state-Keys,
damit Auswahlen den Ansichtswechsel ueberleben (Transferwissen #19). Fuer
Widgets, deren Zustand nicht geschrieben werden darf, ist genau das verboten
— und der Fehler ist heimtueckisch:

    Die ZUWEISUNG geht durch und markiert den Key als "per API gesetzt".
    Erst das spaetere ANLEGEN des Widgets wirft
    StreamlitValueAssignmentNotAllowedError.

Der Traceback zeigt deshalb auf das Widget und nicht auf die Ursache, und das
try/except im Keep-Alive hilft nicht: Es umschliesst die Zuweisung, nicht das
Widget. Wer ein solches Widget einbaut, MUSS seinen Key in
`_KEEPALIVE_SPERRE` eintragen.

WARUM DIESER PRUEFSTEIN STATISCH IST UND KEIN APPTEST:

Am 18.08.2026 hat der Ueberschneidungs-Chart des Strategievergleichs die
laufende Cloud-App angehalten — er lief mit `on_select="rerun"` und war damit
ein Widget, ohne in der Sperrliste zu stehen. Die Falle war VORHER benannt
und mit einem AppTest ueber vier Laeufe geprueft; der meldete "kein Absturz",
und dieses Ergebnis wurde als Beleg in Commit und Dokumentation geschrieben.

Danach nachgestellt: AppTest reproduziert diese Klasse NICHT. Vier Varianten
probiert — Ansicht ueber session_state gesetzt, Navigation bedient, Ansicht
gewechselt und zurueck, Bedienelement im Tab angefasst — keine loest den
Fehler aus, der in der Cloud sofort kommt. Der Zustand, den das Keep-Alive
braucht, entsteht in der Testumgebung nicht auf demselben Weg.

Ein Verhaltenstest kann diese Regel also nicht absichern. Was bleibt, ist die
Regel selbst, und die laesst sich am SYNTAXBAUM pruefen: Jedes Widget mit
`key=`, dessen Zustand nicht geschrieben werden darf, muss in der Sperrliste
nachweisbar sein.

  1. Die Sperrliste ist lesbar und enthaelt nur Zeichenketten
  2. Jedes Trigger-Widget mit Key steht drin
  3. Kein Key in der Liste ist verwaist
  4. Kein Trigger-Widget traegt einen berechneten Key

SCHRITT 4 GIBT ES, WEIL EIN BERECHNETER KEY NICHT PRUEFBAR IST. Ein
`key=f"knopf_{suffix}"` laesst sich mit keinem statischen Mittel gegen die
Liste halten — und ein nicht pruefbares Trigger-Widget ist dieselbe Falle
noch einmal. Wer so etwas braucht, sperrt die ganze Praefix-Familie und
vermerkt es hier.

Braucht kein einziges Paket — nur den Syntaxbaum.

    python tests/test_keepalive.py
"""

import ast
import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

APP = "streamlit_app.py"

# Widgets, deren Zustand NICHT geschrieben werden darf. Zwei Sorten:
#
#  a) Ausloeser — sie melden ein Ereignis, keinen Wert. Ein persistierender
#     Zustand liesse den Klick "haengen".
#  b) Ansichten mit Auswahl — sie werden erst durch `on_select` zum Widget.
#     Das ist der Fall, der am 18.08.2026 die App angehalten hat: Bis dahin
#     war `st.plotly_chart` in diesem Projekt immer nur eine Zeichnung.
AUSLOESER = {
    "button", "download_button", "form_submit_button", "link_button",
    "chat_input", "feedback",
}
MIT_AUSWAHL = {
    "plotly_chart", "dataframe", "data_editor", "altair_chart",
    "vega_lite_chart", "map", "pydeck_chart", "image",
}

# `on_select="ignore"` ist die Vorgabe und macht aus einem Chart KEIN Widget.
KEINE_AUSWAHL = {"ignore", None}


def _quelldateien():
    """streamlit_app.py und alle aktiven Module."""
    dateien = [APP]
    fuer_module = os.path.join(WURZEL, "modules")
    for name in sorted(os.listdir(fuer_module)):
        if not name.endswith(".py") or name == "__init__.py":
            continue
        # portfolio_builder ist seit Juni 2026 nicht mehr importiert
        # (Compliance-Entscheidung) und liegt nur noch da.
        if name == "portfolio_builder.py":
            continue
        dateien.append(os.path.join("modules", name))
    return dateien


def _baum(pfad):
    with open(os.path.join(WURZEL, pfad), encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=pfad)


def sperrliste():
    """Die Menge aus `_KEEPALIVE_SPERRE` in streamlit_app.py, oder None."""
    for knoten in ast.walk(_baum(APP)):
        if not isinstance(knoten, ast.Assign):
            continue
        ziele = [z.id for z in knoten.targets if isinstance(z, ast.Name)]
        if "_KEEPALIVE_SPERRE" not in ziele:
            continue
        if not isinstance(knoten.value, ast.Set):
            return None
        werte = []
        for element in knoten.value.elts:
            if not isinstance(element, ast.Constant) or not isinstance(
                    element.value, str):
                return None
            werte.append(element.value)
        return werte
    return None


def trigger_widgets():
    """Alle Aufrufe von Widgets, deren Zustand nicht geschrieben werden darf.

    Returns:
        Liste von (datei, zeile, funktion, key). `key` ist None, wenn keiner
        gesetzt ist, und der Text "<berechnet>", wenn er kein Literal ist.
    """
    gefunden = []
    for pfad in _quelldateien():
        for knoten in ast.walk(_baum(pfad)):
            if not isinstance(knoten, ast.Call):
                continue
            name = getattr(knoten.func, "attr", None)
            if name is None:
                continue

            schluesselworte = {kw.arg: kw.value for kw in knoten.keywords}

            ist_trigger = name in AUSLOESER
            if name in MIT_AUSWAHL and "on_select" in schluesselworte:
                wert = schluesselworte["on_select"]
                if not (isinstance(wert, ast.Constant)
                        and wert.value in KEINE_AUSWAHL):
                    ist_trigger = True
            if not ist_trigger:
                continue

            if "key" not in schluesselworte:
                key = None            # ohne Key kein session_state-Eintrag
            else:
                wert = schluesselworte["key"]
                key = (wert.value if isinstance(wert, ast.Constant)
                       and isinstance(wert.value, str) else "<berechnet>")
            gefunden.append((pfad, knoten.lineno, name, key))
    return gefunden


# ─────────────────────────────────────────────────────────────────────────────

def schritt1_liste():
    print("Schritt 1 — die Sperrliste ist lesbar")
    liste = sperrliste()
    if liste is None:
        print("    FEHLER — `_KEEPALIVE_SPERRE` fehlt in streamlit_app.py oder "
              "ist keine Menge aus Zeichenketten. Ohne sie kann dieser "
              "Pruefstein nichts halten.")
        return 1
    if len(liste) != len(set(liste)):
        print(f"    FEHLER — doppelte Eintraege: {liste}")
        return 1
    print(f"    OK — {len(liste)} Eintraege: {sorted(liste)}")
    return 0


def schritt2_alle_gesperrt():
    print("Schritt 2 — jedes Trigger-Widget mit Key steht in der Sperrliste")
    liste = sperrliste()
    if liste is None:
        print("    UEBERSPRUNGEN — Sperrliste nicht lesbar (siehe Schritt 1)")
        return 0
    f = 0
    mit_key = [w for w in trigger_widgets() if w[3] not in (None, "<berechnet>")]
    for pfad, zeile, name, key in mit_key:
        if key in liste:
            print(f"    OK — {key!r} ({name}, {pfad}:{zeile})")
        else:
            print(f"    FEHLER — {key!r} fehlt in _KEEPALIVE_SPERRE "
                  f"({name}, {pfad}:{zeile}). Die App stuerzt beim zweiten "
                  "Rendern dieses Widgets ab (#19).")
            f += 1
    if not mit_key:
        print("    FEHLER — gar kein Trigger-Widget gefunden; prueft dieser "
              "Schritt ueberhaupt etwas?")
        f += 1
    return f


def schritt3_keine_verwaisten():
    print("Schritt 3 — kein Eintrag in der Sperrliste ist verwaist")
    liste = sperrliste()
    if liste is None:
        print("    UEBERSPRUNGEN — Sperrliste nicht lesbar")
        return 0
    vorhanden = {w[3] for w in trigger_widgets()}
    verwaist = [k for k in liste if k not in vorhanden]
    if verwaist:
        # Kein Absturzrisiko, aber eine Liste mit toten Eintraegen wird nicht
        # mehr gelesen — und diese hier MUSS gelesen werden. Am 11.08.2026
        # standen "reset_sd"/"reset_ed" darin, deren Schaltflaechen laengst
        # ersetzt waren.
        print(f"    FEHLER — {verwaist} steht in der Sperrliste, aber es gibt "
              "kein Widget dazu")
        return 1
    print(f"    OK — alle {len(liste)} Eintraege haben ein Widget")
    return 0


def schritt4_keine_berechneten_keys():
    print("Schritt 4 — kein Trigger-Widget traegt einen berechneten Key")
    f = 0
    for pfad, zeile, name, key in trigger_widgets():
        if key == "<berechnet>":
            print(f"    FEHLER — {name} in {pfad}:{zeile} hat einen "
                  "berechneten Key; er laesst sich gegen keine Liste halten")
            f += 1
    if not f:
        print("    OK — alle Keys sind Literale und damit pruefbar")

    # Ein Trigger-Widget OHNE Key ist harmlos (es landet nicht im
    # session_state), aber es lohnt sich zu wissen, dass es sie gibt.
    ohne = [(p, z, n) for p, z, n, k in trigger_widgets() if k is None]
    if ohne:
        print(f"    HINWEIS — {len(ohne)} Trigger-Widget(e) ohne Key, damit "
              f"unbetroffen: {[f'{n} ({p}:{z})' for p, z, n in ohne]}")
    return f


def main():
    print("Pruefstein: Keep-Alive-Sperre\n")
    fehler = 0
    for schritt in (schritt1_liste, schritt2_alle_gesperrt,
                    schritt3_keine_verwaisten, schritt4_keine_berechneten_keys):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — jedes Trigger-Widget mit Key ist gesperrt, die Liste "
          "hat keine Leichen, und alle Keys sind pruefbar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
