"""Pruefstein fuer die Oberflaechen-Konfiguration (NEU 18.08.2026).

`.streamlit/config.toml` ist die einzige Datei dieses Projekts, deren Fehler
sich NICHT bemerkbar machen: Wird sie nicht gelesen, sieht die App aus wie
eine App ohne Konfiguration — also normal. Genau das ist passiert. Der Ordner
hiess von Anfang an `streamlit/` ohne Punkt, Streamlit hat ihn stillschweigend
ignoriert, und `toolbarMode = "minimal"` war monatelang wirkungslos, ohne dass
es jemandem auffiel (Transferwissen #23, repariert 07.08.2026).

Dieselbe Klasse Fehler traf am 18.08.2026 das Theme, nur umgekehrt: Es gab
GAR KEINS. Die App lief seit jeher mit Streamlits Standard-Akzentfarbe
#FF4B4B — einem grellen Korallenrot auf Auswahl-Chips, Kontrollkaestchen,
Fokusrahmen und aktiven Segmenten, quer durch alle drei Ansichten. In einem
Werkzeug mit Fuggerblau und Fuggergold war das nie beabsichtigt; ein Standard
sieht eben aus wie eine Festlegung.

  1. Der Ordner traegt den Punkt, die Datei ist gueltiges TOML
  2. STREAMLIT LIEST SIE WIRKLICH — die Werte kommen aus DIESER Datei
  3. Die Farben stimmen mit modules/shared.py ueberein
  4. Hell und Dunkel bleiben beide moeglich
  5. Die Schrift kommt aus dem Theme, nicht mehr aus einem CSS-Block

SCHRITT 2 IST DER EIGENTLICHE. `config.get_where_defined` nennt die Datei,
aus der ein Wert stammt. Steht dort `<default>`, wurde die Konfiguration
nicht gelesen — und genau das ist der Fehler von 2026, den niemand sehen
konnte. Ein Test auf den blossen INHALT der Datei haette ihn nicht gefunden.

    python tests/test_theme.py
"""

import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

KONFIG_ORDNER = ".streamlit"
KONFIG = os.path.join(KONFIG_ORDNER, "config.toml")


def _ist(bezeichnung, ist, soll):
    if ist == soll:
        print(f"    OK — {bezeichnung}: {ist!r}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {ist!r} statt {soll!r}")
    return 1


def schritt1_datei():
    print("Schritt 1 — Ordner mit Punkt, gueltiges TOML")
    f = 0

    if not os.path.isdir(os.path.join(WURZEL, KONFIG_ORDNER)):
        print(f"    FEHLER — Ordner {KONFIG_ORDNER} fehlt")
        return 1
    print(f"    OK — {KONFIG_ORDNER} vorhanden (mit Punkt)")

    # Der Zwilling ohne Punkt darf NICHT existieren: Streamlit liest ihn
    # nicht, aber wer ihn sieht, haelt ihn fuer die Konfiguration.
    if os.path.isdir(os.path.join(WURZEL, "streamlit")):
        print("    FEHLER — es gibt zusaetzlich einen Ordner 'streamlit' "
              "OHNE Punkt; Streamlit liest ihn nicht (#23)")
        f += 1
    else:
        print("    OK — kein verwechselbarer Ordner ohne Punkt")

    try:
        import tomllib
    except ImportError:
        print("    UEBERSPRUNGEN — tomllib erst ab Python 3.11")
        return f
    try:
        with open(os.path.join(WURZEL, KONFIG), "rb") as fh:
            daten = tomllib.load(fh)
    except Exception as ex:
        print(f"    FEHLER — {KONFIG} ist kein gueltiges TOML: {ex}")
        return f + 1
    print(f"    OK — {KONFIG} parst, Abschnitte: {sorted(daten)}")

    if "theme" not in daten:
        print("    FEHLER — kein [theme]-Abschnitt")
        f += 1
    return f


def schritt2_wird_gelesen():
    print("Schritt 2 — Streamlit liest die Datei WIRKLICH (der #23-Test)")
    try:
        from streamlit import config
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — {ex}")
        return 0
    config.get_config_options()

    f = 0
    erwartet = os.path.join(WURZEL, KONFIG)
    for schluessel in ("theme.primaryColor", "theme.font", "theme.baseRadius",
                       "theme.dark.primaryColor", "client.toolbarMode"):
        woher = config.get_where_defined(schluessel)
        if woher == erwartet:
            print(f"    OK — {schluessel} kommt aus {KONFIG}")
        else:
            print(f"    FEHLER — {schluessel} kommt aus {woher!r}. "
                  "Wird die Konfiguration ueberhaupt gelesen? (#23)")
            f += 1
    return f


def schritt3_farben():
    print("Schritt 3 — die Farben stimmen mit modules/shared.py ueberein")
    try:
        from streamlit import config
        from modules.shared import (THEME_AKZENT_DUNKEL, THEME_AKZENT_HELL,
                                    THEME_SCHRIFT)
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — {ex}")
        return 0
    config.get_config_options()

    f = 0
    # Gross-/Kleinschreibung der Hex-Werte ist egal, der Wert nicht.
    f += _ist("theme.primaryColor == THEME_AKZENT_HELL",
              str(config.get_option("theme.primaryColor")).upper(),
              THEME_AKZENT_HELL.upper())
    f += _ist("theme.dark.primaryColor == THEME_AKZENT_DUNKEL",
              str(config.get_option("theme.dark.primaryColor")).upper(),
              THEME_AKZENT_DUNKEL.upper())
    f += _ist("theme.font == THEME_SCHRIFT",
              config.get_option("theme.font"), THEME_SCHRIFT)

    # DAS ROT DARF NICHT ZURUECKKOMMEN. Streamlits Vorgabe ist #FF4B4B; wer
    # das Theme entfernt, bekommt sie wieder, ohne dass es nach einem Fehler
    # aussieht. Deshalb steht sie hier namentlich.
    for schluessel in ("theme.primaryColor", "theme.dark.primaryColor"):
        wert = str(config.get_option(schluessel) or "").upper()
        if wert.startswith("#FF"):
            print(f"    FEHLER — {schluessel} ist {wert}: das sieht nach "
                  "Streamlits Standardrot aus, nicht nach Fuggerblau")
            f += 1
    if not f:
        print("    OK — kein Streamlit-Rot mehr im Akzent")
    return f


def schritt4_hell_und_dunkel():
    print("Schritt 4 — Hell und Dunkel bleiben beide moeglich")
    try:
        from streamlit import config
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — {ex}")
        return 0
    config.get_config_options()

    f = 0
    # `base` wuerde eine der beiden Fassungen erzwingen. Die Ansichten sind
    # ausdruecklich fuer beide gebaut (Sichtpruefungsliste in STATUS.md), und
    # ein Berater soll seine Einstellung behalten duerfen.
    if config.get_option("theme.base") is not None:
        print(f"    FEHLER — theme.base ist gesetzt "
              f"({config.get_option('theme.base')!r}) und erzwingt eine Fassung")
        f += 1
    else:
        print("    OK — theme.base nicht gesetzt, die Wahl bleibt beim Nutzer")

    # Der Dunkel-Akzent muss ein ANDERER sein als der helle: Dunkles
    # Fuggerblau verschwaende auf dunklem Grund.
    hell = str(config.get_option("theme.primaryColor") or "").upper()
    dunkel = str(config.get_option("theme.dark.primaryColor") or "").upper()
    if not dunkel:
        print("    FEHLER — kein eigener Akzent fuer den Dunkelmodus")
        f += 1
    elif hell == dunkel:
        print(f"    FEHLER — Hell und Dunkel tragen denselben Akzent {hell}")
        f += 1
    else:
        print(f"    OK — Hell {hell}, Dunkel {dunkel}")
    return f


def schritt5_kein_css_mehr():
    print("Schritt 5 — die Schrift kommt aus dem Theme, nicht aus CSS")
    f = 0
    with open(os.path.join(WURZEL, "streamlit_app.py"), encoding="utf-8") as fh:
        quelle = fh.read()

    # ZWEI MECHANISMEN FUER DIESELBE SACHE waeren das Problem: Ein
    # CSS-`!important` gewinnt gegen das Theme, und wer die Schrift aendert,
    # aendert sie dann an der falschen Stelle.
    if "font-family" in quelle:
        print("    FEHLER — in streamlit_app.py steht noch ein "
              "font-family-CSS; es gewinnt gegen theme.font")
        f += 1
    else:
        print("    OK — kein font-family-CSS mehr in streamlit_app.py")

    if "unsafe_allow_html" in quelle:
        print("    HINWEIS — es gibt noch unsafe_allow_html in "
              "streamlit_app.py; bitte pruefen, wofuer")
    return f


def main():
    print("Pruefstein: Oberflaechen-Konfiguration und Theme\n")
    fehler = 0
    for schritt in (schritt1_datei, schritt2_wird_gelesen, schritt3_farben,
                    schritt4_hell_und_dunkel, schritt5_kein_css_mehr):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — die Konfiguration wird gelesen, der Akzent ist "
          "Fuggerblau, und Hell wie Dunkel bleiben moeglich")
    return 0


if __name__ == "__main__":
    sys.exit(main())
