"""Prueft, dass in den sichtbaren Texten der App keine Piktogramme stehen.

REGEL (festgelegt mit Philip am 10.08.2026):
    Ueberschriften, Hinweise, Schaltflaechen und Disclaimer der App tragen
    KEINE Emoji. Fuer eine Privatbank mit gehobener Kundschaft wirken sie
    unpassend — die Ergebnisse dieses Tools gehen ins Kundengespraech.

    Betroffen waren 59 Zeilen in fuenf Dateien: Navigations-Beschriftungen
    ("Performance", "Portfolioanalyse"), alle st.subheader, Hinweis- und
    Quellenzeilen, Schaltflaechen und Download-Beschriftungen.

WAS GEPRUEFT WIRD — und was bewusst NICHT:
    Geprueft werden nur Zeilen mit CODE. Kommentare und Docstrings duerfen
    Piktogramme enthalten: die sieht kein Nutzer, und in der Projektdoku
    steht das Warnzeichen bewusst vor wichtigen Fallstricken.

    Erkannt werden echte Piktogramme (U+1F300–U+1FAFF) sowie Zeichen mit
    Emoji-Variantenselektor (U+FE0F) — also auch Warnzeichen und Pfeile in
    Emoji-Darstellung. Typografische Zeichen wie der Pfeil in Kommentaren
    oder Gedankenstriche sind ausdruecklich erlaubt.

    python tests/test_keine_piktogramme.py     (braucht kein einziges Paket)
"""

import os
import sys
import unicodedata

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VS16 = "️"      # Variantenselektor: erzwingt Emoji- statt Textdarstellung

# Diese Dateien liefern die sichtbare Oberflaeche.
DATEIEN = [
    "streamlit_app.py",
    os.path.join("modules", "shared.py"),
    os.path.join("modules", "portfolioanalyse.py"),
    os.path.join("modules", "download_helfer.py"),
    os.path.join("modules", "portfolio_builder.py"),
]


def _piktogramme(zeile):
    """Alle Emoji einer Zeile — Piktogramm-Bereich oder Emoji-Variante."""
    gefunden = []
    for i, ch in enumerate(zeile):
        if 0x1F300 <= ord(ch) <= 0x1FAFF:
            gefunden.append(ch)
        elif i + 1 < len(zeile) and zeile[i + 1] == VS16:
            gefunden.append(ch + VS16)
    return gefunden


def _pruefe_gerenderte_app():
    """Zusatzprüfung: die App hochfahren und die GERENDERTEN Texte ansehen.

    Die Quelltextprüfung oben findet nur, was im Code steht. Piktogramme
    könnten auch aus Daten kommen (Mapping-Spalten, CSV-Werte) oder aus
    Vorgaben Dritter. Deshalb hier zusätzlich der Blick auf das, was der
    Nutzer wirklich sieht — in BEIDEN Ansichten.

    Braucht streamlit; ohne wird übersprungen.
    """
    print("\nZusatzprüfung: gerenderte Oberfläche (AppTest)")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0

    at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                           default_timeout=300)
    at.secrets["passwords"] = {"testnutzer": "nur-fuer-den-test"}
    at.session_state["logged_in"] = True
    at.session_state["username"] = "testnutzer"

    fehler = 0
    for ansicht in ("Performance", "Portfolioanalyse"):
        if ansicht != "Performance":
            at.session_state["nav_view"] = ansicht
        try:
            at.run()
        except Exception as ex:
            print(f"   UEBERSPRUNGEN ({ansicht}) — {ex}")
            return 0
        if at.exception:
            for ex in at.exception:
                print(f"   FEHLER — {ansicht} warf: {str(ex.value)[:200]}")
            return 1

        texte = []
        for sammlung in (at.markdown, at.subheader, at.header, at.title,
                         at.caption, at.info, at.warning, at.success,
                         at.error):
            texte += [e.value for e in sammlung if e.value]
        gefunden = sorted({z for t in texte for z in _piktogramme(t)})
        if gefunden:
            fehler += len(gefunden)
            print(f"   FEHLER — {ansicht}: {''.join(gefunden)}")
            for t in texte:
                if _piktogramme(t):
                    print(f"          {t.strip()[:88]}")
        else:
            print(f"   OK — {ansicht}: {len(texte)} Textbausteine, "
                  f"kein Piktogramm")
    return fehler


def main():
    fehler = 0
    geprueft = 0
    for rel in DATEIEN:
        pfad = os.path.join(WURZEL, rel)
        if not os.path.exists(pfad):
            print(f"   HINWEIS — {rel} fehlt, uebersprungen")
            continue
        with open(pfad, encoding="utf-8") as fh:
            zeilen = fh.readlines()
        treffer = []
        for nr, zeile in enumerate(zeilen, 1):
            if zeile.lstrip().startswith("#"):
                continue                      # Kommentar: nicht sichtbar
            gef = _piktogramme(zeile)
            if gef:
                treffer.append((nr, gef, zeile.strip()[:88]))
        geprueft += 1
        if not treffer:
            print(f"OK  {rel}")
            continue
        fehler += len(treffer)
        print(f"\n{rel}:")
        for nr, gef, text in treffer:
            namen = ", ".join(unicodedata.name(g[0], "?") for g in gef)
            print(f"   FEHLER Zeile {nr}: {''.join(gef)}  ({namen})")
            print(f"          {text}")

    fehler += _pruefe_gerenderte_app()

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Fund(e) mit Piktogrammen in "
              f"sichtbarem Text")
        print("Hinweis: In Kommentaren und Docstrings sind sie erlaubt.")
        return 1
    print(f"BESTANDEN — {geprueft} Dateien, keine Piktogramme in der "
          f"Oberflaeche")
    return 0


if __name__ == "__main__":
    sys.exit(main())
