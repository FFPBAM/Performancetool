# tests/test_pdf_briefkasten.py
"""
Vertragstest App <-> PDF-Dienst (Neubau 17.09.2026).

Der Dienst liegt aus Sicherheitsgruenden NICHT im Repo (lokal auf dem
Standalone-Buero-PC). Dieser Test haelt trotzdem die zwei Vertraege fest, an
denen App (Python) und Dienst (PowerShell) auseinanderlaufen koennten:

  1. Das AUFTRAGSFORMAT: `neuer_auftrag()` muss auf die Regex `$AuftragMuster`
     in pdf_dienst.ps1 passen (hier als Konstante gespiegelt). Passt es nicht,
     ignoriert der Dienst jeden Auftrag stillschweigend.
  2. Die SIGNATUR: `signatur()` muss Zeichen fuer Zeichen dasselbe liefern wie
     `Signatur-Hex` im Dienst. Als fester Pruefvektor dient ein am 17.09.2026
     mit PowerShell (HMACSHA256) erzeugter Wert — laufen die beiden
     Implementierungen auseinander, lehnt der Dienst jeden Auftrag ab.

Reines python (kein pytest, keine Installation noetig):
    python tests/test_pdf_briefkasten.py
"""

import os
import re
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

from modules import pdf_briefkasten as BK

# Kopie von $AuftragMuster aus pdf_dienst.ps1 (der Dienst liegt nicht im Repo).
DIENST_AUFTRAG_MUSTER = r'^(\d{8}-\d{6}-[0-9a-f]{8})\.(pptx|sig)$'

# Fester Pruefvektor, mit PowerShell erzeugt (Schluessel + Inhalt als UTF-8):
#   HMACSHA256(Key="0123456789abcdef", "testinhalt") -> Hex, klein
DIENST_HMAC_SCHLUESSEL = "0123456789abcdef"
DIENST_HMAC_INHALT = b"testinhalt"
DIENST_HMAC_ERWARTET = "208c7004560b0c4d34e30900c6b525634a0bb4ee9df5d61b2f5b8323893ef463"


def test_auftragsformat():
    print("\n1. Auftragsformat passt zur Dienst-Regex")
    fehler = 0
    for _ in range(200):
        auftrag = BK.neuer_auftrag()
        for endung in (".pptx", ".sig"):
            if not re.match(DIENST_AUFTRAG_MUSTER, auftrag + endung):
                print("   FEHLER — %r passt nicht auf die Dienst-Regex" % (auftrag + endung))
                fehler += 1
        # Der Dienst nimmt als EINGABE nur .pptx/.sig; .pdf ist die Antwort.
        if re.match(DIENST_AUFTRAG_MUSTER, auftrag + ".pdf"):
            print("   FEHLER — .pdf wuerde faelschlich als Eingabe gelten")
            fehler += 1
    if not fehler:
        print("   OK — 200 Auftraege, .pptx und .sig passen, .pdf nicht")
    return fehler


def test_signatur():
    print("\n2. Signatur stimmt mit dem Dienst ueberein (fester PowerShell-Vektor)")
    fehler = 0
    ist = BK.signatur(DIENST_HMAC_INHALT, DIENST_HMAC_SCHLUESSEL)
    if ist != DIENST_HMAC_ERWARTET:
        print("   FEHLER — Signatur weicht ab:\n     App:    %s\n     Dienst: %s"
              % (ist, DIENST_HMAC_ERWARTET))
        fehler += 1
    if len(ist) != 64 or any(c not in "0123456789abcdef" for c in ist):
        print("   FEHLER — Signatur ist kein 64-stelliges Kleinbuchstaben-Hex: %r" % ist)
        fehler += 1
    # Anderer Schluessel -> andere Signatur (sonst waere die Pruefung wertlos).
    if BK.signatur(DIENST_HMAC_INHALT, "anderer") == ist:
        print("   FEHLER — Signatur haengt nicht vom Schluessel ab")
        fehler += 1
    # Deterministisch.
    if BK.signatur(DIENST_HMAC_INHALT, DIENST_HMAC_SCHLUESSEL) != ist:
        print("   FEHLER — Signatur ist nicht deterministisch")
        fehler += 1
    if not fehler:
        print("   OK — HMAC-SHA256 identisch zum Dienst, schluesselabhaengig, deterministisch")
    return fehler


def main():
    print("Vertragstest App <-> PDF-Dienst")
    fehler = test_auftragsformat() + test_signatur()
    print()
    if fehler:
        print("FEHLGESCHLAGEN — %d Fehler" % fehler)
        return 1
    print("BESTANDEN — Auftragsformat und Signatur passen zum Dienst")
    return 0


if __name__ == "__main__":
    sys.exit(main())
