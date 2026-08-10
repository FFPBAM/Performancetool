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

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Zeile(n) mit Piktogrammen in "
              f"sichtbarem Text")
        print("Hinweis: In Kommentaren und Docstrings sind sie erlaubt.")
        return 1
    print(f"BESTANDEN — {geprueft} Dateien, keine Piktogramme in der "
          f"Oberflaeche")
    return 0


if __name__ == "__main__":
    sys.exit(main())
