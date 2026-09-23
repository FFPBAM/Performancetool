# modules/anlagekriterien.py
"""Anlagekriterien je Strategie — EINE Quelle für Tool UND Broschüre.

Die Kriterien standen bis zum 10.08.2026 nur statisch in den PPTX-Vorlagen,
je Familie unterschiedlich geschrieben. Seit dem 23.09.2026 stehen sie als
vier Spalten in ``Mapping_Strategien.xlsx``, in derselben Zeile wie der Rest
der Stammdaten. Sie speisen beides:

    Excel ─┬─► Banner im Streamlit-Tool      (shared.zeige_anlagekriterien)
           └─► Kasten auf der Struktur-Folie (pptx_slides.fill_anlagekriterien_slide)

DIESES MODUL LIEST KEINE DATEI MEHR (23.09.2026):
    Das Laden liegt in ``modules/stammdaten.py`` — dort steht das einzige
    ``pd.read_excel`` auf eine Mapping-Datei im ganzen Projekt, und ein
    Prüfstein hält das per Syntaxbaum fest. Hier bleibt die AUSWERTUNG:
    welche Spalten gedruckt werden und wie eine Zeile zu Paaren wird. Die
    Funktionen nehmen den Frame als Argument und sind damit rein.

    Streamlit-frei bleibt es aus dem alten Grund: ``pptx_export.py`` soll
    ohne Streamlit aus einem Batch-Skript laufen können (Abschnitt 13 der
    Projektdoku).
"""

import pandas as pd

KEY_SPALTE = "Strategie auswählen"     # wie in Mapping_Namen.xlsx
ANZEIGE_SPALTE = "Anzeigename"         # Kopfzeile des Kastens in der Broschüre

# Die vier Kriterien in der Reihenfolge der Vorlagen-Tabelle (Zeile 1–4).
# Die Spaltennamen der Excel sind GLEICHZEITIG die gedruckten Beschriftungen —
# keine zweite Liste, die auseinanderlaufen kann.
SPALTEN = ("Anlageregion", "Aktienanteil",
           "Anleihenanteil / Liquidität", "Fremdwährungen")


def _zeile(strategie, kriterien):
    if kriterien is None or getattr(kriterien, "empty", True) or not strategie:
        return None
    if KEY_SPALTE not in kriterien.columns:
        return None
    treffer = kriterien.loc[
        kriterien[KEY_SPALTE].astype(str).str.strip() == str(strategie).strip()]
    return None if treffer.empty else treffer.iloc[0]


def fuer(strategie: str, kriterien: pd.DataFrame):
    """Kriterien EINER Strategie als geordnete Liste [(Bezeichnung, Wert), …].

    Gibt [] zurück, wenn die Strategie keinen Kasten hat — das ist der
    Normalfall für die Familie 'Thema' und kein Fehler.
    """
    zeile = _zeile(strategie, kriterien)
    if zeile is None:
        return []
    paare = []
    for spalte in SPALTEN:
        if spalte not in kriterien.columns:
            continue
        wert = zeile[spalte]
        if pd.isna(wert) or not str(wert).strip():
            continue
        paare.append((spalte, str(wert).strip()))
    return paare


def anzeigename(strategie: str, kriterien: pd.DataFrame):
    """Name für die Kopfzeile des Kastens ('Anlagekriterien | <Name>').

    None, wenn die Strategie nicht erfasst ist — die Aufrufstelle lässt die
    Vorlagen-Kopfzeile dann unangetastet.
    """
    zeile = _zeile(strategie, kriterien)
    if zeile is None or ANZEIGE_SPALTE not in kriterien.columns:
        return None
    wert = zeile[ANZEIGE_SPALTE]
    if pd.isna(wert) or not str(wert).strip():
        return None
    return str(wert).strip()
