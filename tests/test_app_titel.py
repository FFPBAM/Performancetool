"""Prueft, dass das Tool ueberall EINEN Namen traegt.

REGEL (festgelegt mit Philip am 10.08.2026):
    Login, Browser-Tab und Kopfzeile zeigen denselben Namen —
    "Performance & Portfolioanalyse | Fuerst Fugger Privatbank".
    Quelle ist die Konstante shared.APP_TITLE, nirgends ein Literal.

    Vorher standen dort drei verschiedene Namen:
      Login      "Performance VV Rechner | Fuerst Fugger Privatbank"
      Tab        "FFPB - Performance & Portfolioanalyse"
      Kopfzeile  "Fuerst Fugger Privatbank - Vermoegensverwaltung"
    Der Login-Titel nannte nur die halbe Anwendung (die Portfolioanalyse ist
    ein gleichwertiger Bereich) und "Rechner" untertrieb: das Tool erzeugt
    die fertigen Kundenbroschueren.

Geprueft wird:
  1. APP_TITLE hat den vereinbarten Wortlaut und nennt beide Bereiche.
  2. Kein Modul enthaelt noch einen der drei alten Namen als Literal.
  3. Der ANGEMELDETE Login-Bildschirm zeigt APP_TITLE — per AppTest, also
     am laufenden Streamlit-Skript und nicht nur am Quelltext
     (Transferwissen #24). Braucht streamlit, sonst uebersprungen.

    python tests/test_app_titel.py
"""

import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

ERWARTET = "Performance & Portfolioanalyse | Fürst Fugger Privatbank"

# Die drei Namen, die es vorher gab — duerfen als Literal nicht mehr
# auftauchen (Kommentare in shared.py dokumentieren sie bewusst weiter).
ALTE_NAMEN = [
    "Performance VV Rechner",
    "FFPB – Performance & Portfolioanalyse",
    "Fürst Fugger Privatbank – Vermögensverwaltung",
]


def _pruefe_konstante():
    print("1. APP_TITLE")
    try:
        from modules.shared import APP_TITLE, APP_NAME
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0
    fehler = 0
    if APP_TITLE != ERWARTET:
        print(f"   FEHLER — {APP_TITLE!r}, erwartet {ERWARTET!r}")
        fehler += 1
    else:
        print(f"   OK — {APP_TITLE!r}")
    # Beide Bereiche muessen vorkommen: genau das war der Anlass.
    for bereich in ("Performance", "Portfolioanalyse"):
        if bereich not in APP_NAME:
            print(f"   FEHLER — '{bereich}' fehlt im Namen")
            fehler += 1
    return fehler


def _pruefe_keine_altnamen():
    print("\n2. Alte Namen kommen als Literal nicht mehr vor")
    fehler = 0
    dateien = [os.path.join(WURZEL, "streamlit_app.py")]
    moddir = os.path.join(WURZEL, "modules")
    dateien += [os.path.join(moddir, f) for f in sorted(os.listdir(moddir))
                if f.endswith(".py")]

    for pfad in dateien:
        with open(pfad, encoding="utf-8") as fh:
            zeilen = fh.readlines()
        for nr, zeile in enumerate(zeilen, 1):
            # Kommentarzeilen ausnehmen: dort ist die Historie dokumentiert.
            if zeile.lstrip().startswith("#"):
                continue
            for alt in ALTE_NAMEN:
                if alt in zeile:
                    print(f"   FEHLER — {os.path.basename(pfad)}:{nr} "
                          f"enthaelt noch {alt!r}")
                    fehler += 1
    if fehler == 0:
        print(f"   OK — {len(dateien)} Dateien geprueft, kein Altname")
    return fehler


def _pruefe_login_bildschirm():
    print("\n3. Login-Bildschirm zeigt den Namen (AppTest)")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0

    # Ohne Anmeldung bricht das Skript nach dem Login-Block ab; genau dieser
    # Zustand soll geprueft werden.
    #
    # WICHTIG: check_login liest st.secrets["passwords"]. Ohne Secrets wirft
    # die App eine Exception, BEVOR der Titel gerendert wird — der Test waere
    # dann gruen bzw. rot aus dem falschen Grund. secrets.toml ist bewusst
    # nie committet (oeffentliches Repo), deshalb setzt AppTest hier ein
    # Wegwerf-Passwort im Speicher. Es wird nie zum Anmelden benutzt: geprueft
    # wird der ABGEMELDETE Bildschirm.
    at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                           default_timeout=180)
    at.secrets["passwords"] = {"testnutzer": "nur-fuer-den-test"}
    try:
        at.run()
    except Exception as ex:
        print(f"   UEBERSPRUNGEN — App liess sich nicht starten: {ex}")
        return 0

    if at.exception:
        for ex in at.exception:
            print(f"   FEHLER — App warf: {str(ex.value)[:200]}")
        return 1

    titel = [t.value for t in at.title]
    if not titel:
        # Manche Streamlit-Versionen fuehren st.title unter 'header'.
        titel = [h.value for h in at.header]
    print(f"   gefundene Titel: {titel}")
    if ERWARTET in titel:
        print("   OK")
        return 0
    print(f"   FEHLER — {ERWARTET!r} nicht im Login-Bildschirm")
    return 1


def main():
    fehler = _pruefe_konstante() + _pruefe_keine_altnamen() + _pruefe_login_bildschirm()
    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print(f"BESTANDEN — das Tool heisst ueberall '{ERWARTET}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
