"""Prueft die Familien-Konfigurationen (_folien_config).

Zwei Zusicherungen:

  1. AEQUIVALENZ — die am 07.08.2026 auf _folien_config umgestellte
     Themen-Konfiguration erzeugt exakt dasselbe template_config wie die
     frueher handgeschriebene Dict-Form. Das Original steht unten als
     Referenz und darf NICHT angepasst werden, wenn ein Test fehlschlaegt;
     dann stimmt die neue Konfiguration nicht.

  2. STIMMIGKEIT — jede Familie passt zu ihrer echten Vorlagendatei:
     Folienzahl laut Konfiguration == Folienzahl der PPTX, und die
     Foliennummern liegen im gueltigen Bereich.

Teil 1 laeuft ueberall. Teil 2 braucht python-pptx und wird sonst
uebersprungen (nicht als Fehler gewertet).

    python tests/test_folien_config.py
"""

import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

# _folien_config kommt aus seiner Heimat und nicht ueber den Re-Export in
# portfolioanalyse (12.08.2026): Es ist ein privater Helfer der Konfiguration,
# und ein privater Name gehoert nicht durch ein UI-Modul weitergereicht.
# VORLAGEN_FAMILIEN bleibt bewusst ueber portfolioanalyse — so prueft der Test
# genau den Weg, den auch der Export nimmt. Genau deshalb zieht dieser Test
# streamlit herein: portfolioanalyse ist ein UI-Modul.
#
# ABBRUCH -> UEBERSPRUNGEN (12.08.2026): Bis heute war dies der einzige Test,
# der ohne streamlit mit einem ModuleNotFoundError abbrach statt sich sauber
# zu ueberspringen. In einer Umgebung ohne Pakete sah das aus wie ein echter
# Fehlschlag. Alle anderen Suiten machen es so wie hier jetzt auch.
try:
    from modules.portfolioanalyse import VORLAGEN_FAMILIEN  # noqa: E402
    from modules.vorlagen_config import _folien_config  # noqa: E402
except ImportError as ex:
    print(f"UEBERSPRUNGEN — Abhaengigkeit fehlt: {ex}")
    sys.exit(0)

# ── Referenz: die handgeschriebene Fassung vor der Umstellung ────────────
THEMA_ORIGINAL = {
    "block_reihenfolge": ["einzeltitel_themen", "zusammenstellung",
                          "wertentwicklung", "rollierend"],
    "block_positionen": {
        "einzeltitel_themen": 10,
        "zusammenstellung": 11,
        "wertentwicklung": 12,
        "rollierend": 13,
    },
    "erwartete_folien": 21,
    "entfernen": [],
}


def pruefe_thema_aequivalenz():
    """Die neue Thema-Konfiguration muss die alte exakt reproduzieren."""
    neu = VORLAGEN_FAMILIEN["Thema"][1]
    fehler = []
    for schluessel, erwartet in THEMA_ORIGINAL.items():
        ist = neu.get(schluessel)
        if ist != erwartet:
            fehler.append(f"    {schluessel}: erwartet {erwartet!r}, ist {ist!r}")

    # Der Dupliziermodus darf KEINE feste_bloecke enthalten — sonst wuerde
    # pptx_export auf den Festmodus umschalten und nicht mehr duplizieren.
    if neu.get("feste_bloecke"):
        fehler.append(f"    feste_bloecke muss leer/fehlen, ist {neu['feste_bloecke']!r}")

    print("1. Thema-Konfiguration identisch zur handgeschriebenen Fassung")
    if fehler:
        print("   FEHLER:")
        print("\n".join(fehler))
        return False
    print("   OK — block_reihenfolge, block_positionen, erwartete_folien, "
          "entfernen stimmen ueberein")
    print("   OK — kein feste_bloecke (Dupliziermodus bleibt erhalten)")
    return True


def pruefe_modus_wachen():
    """Die Schutzabfragen im Dupliziermodus muessen greifen."""
    faelle = [
        ("mehrere Strategien im Dupliziermodus",
         dict(modus="dupliziert",
              folien=[("S", "x"), ("wertentwicklung", 0, "a"),
                      ("wertentwicklung", 1, "b")])),
        ("Block nicht zusammenhaengend",
         dict(modus="dupliziert",
              folien=[("wertentwicklung", 0, "a"), ("S", "dazwischen"),
                      ("rollierend", 0, "b")])),
        ("unbekannter Modus",
         dict(modus="quatsch", folien=[("S", "x")])),
    ]
    print("\n2. Schutzabfragen von _folien_config")
    ok = True
    for name, kwargs in faelle:
        try:
            _folien_config(**kwargs)
        except ValueError:
            print(f"   OK — '{name}' wird abgefangen")
        else:
            print(f"   FEHLER — '{name}' haette einen ValueError ausloesen muessen")
            ok = False
    return ok


def pruefe_gegen_vorlagen():
    """Folienzahl und Positionen muessen zur echten PPTX passen."""
    print("\n3. Konfiguration gegen die echten Vorlagen")
    try:
        from pptx import Presentation
    except ImportError:
        print("   UEBERSPRUNGEN — python-pptx nicht installiert")
        return True

    ok = True
    for familie, (dateiname, cfg) in sorted(VORLAGEN_FAMILIEN.items()):
        pfad = os.path.join(WURZEL, "Vorlage", dateiname)
        if not os.path.exists(pfad):
            print(f"   {familie:10s} UEBERSPRUNGEN — {dateiname} fehlt")
            continue
        echt = len(Presentation(pfad).slides)
        erwartet = cfg.get("erwartete_folien")

        positionen = []
        for block in cfg.get("feste_bloecke") or []:
            positionen.extend(block.values())
        positionen.extend((cfg.get("block_positionen") or {}).values())
        positionen.extend((cfg.get("einmal_folien") or {}).values())

        probleme = []
        if echt != erwartet:
            probleme.append(f"Vorlage hat {echt} Folien, Konfiguration erwartet {erwartet}")
        ausserhalb = [p for p in positionen if not 1 <= p <= echt]
        if ausserhalb:
            probleme.append(f"Positionen ausserhalb der Vorlage: {sorted(ausserhalb)}")

        if probleme:
            ok = False
            print(f"   {familie:10s} FEHLER — {'; '.join(probleme)}")
        else:
            modus = "dupliziert" if cfg.get("block_positionen") else "fest"
            print(f"   {familie:10s} OK — {echt} Folien, {len(positionen)} dynamische "
                  f"Positionen, Modus {modus}")
    return ok


def main():
    ergebnisse = [pruefe_thema_aequivalenz(),
                  pruefe_modus_wachen(),
                  pruefe_gegen_vorlagen()]
    print()
    if all(ergebnisse):
        print("BESTANDEN")
        return 0
    print("FEHLGESCHLAGEN")
    return 1


if __name__ == "__main__":
    sys.exit(main())
