# modules/anlagekriterien.py
"""Anlagekriterien je Strategie — EINE Quelle für Tool UND Broschüre.

Die Kriterien standen bis zum 10.08.2026 nur statisch in den PPTX-Vorlagen,
je Familie unterschiedlich geschrieben. Jetzt liegen sie in
``Mapping_Anlagekriterien.xlsx`` und speisen beides:

    Excel ─┬─► Banner im Streamlit-Tool      (shared.zeige_anlagekriterien)
           └─► Kasten auf der Struktur-Folie (pptx_slides.fill_anlagekriterien_slide)

WARUM DIESES MODUL STREAMLIT-FREI IST:
    ``pptx_export.py`` hat bewusst KEINE Streamlit-Abhängigkeit — der
    Broschüren-Export soll auch aus einem Batch-Skript heraus laufen können
    (Abschnitt 13 der Projektdoku). Läge das Laden nur in ``shared.py``
    (dort mit ``@st.cache_data``), zöge der Export Streamlit herein.
    Deshalb steht die reine Logik hier; ``shared.py`` legt für die App nur
    den Cache darum. Kopiert wird nichts — genau daran krankte die Codebasis
    früher (zwei Loader, elf Mathe-Kopien).
"""

import os

import pandas as pd

PFAD = "Mapping_Anlagekriterien.xlsx"

KEY_SPALTE = "Strategie auswählen"     # wie in Mapping_Namen.xlsx
ANZEIGE_SPALTE = "Anzeigename"         # Kopfzeile des Kastens in der Broschüre

# Die vier Kriterien in der Reihenfolge der Vorlagen-Tabelle (Zeile 1–4).
# Die Spaltennamen der Excel sind GLEICHZEITIG die gedruckten Beschriftungen —
# keine zweite Liste, die auseinanderlaufen kann.
SPALTEN = ("Anlageregion", "Aktienanteil",
           "Anleihenanteil / Liquidität", "Fremdwährungen")


def leer() -> pd.DataFrame:
    """Leerer, aber strukturell gültiger DataFrame."""
    return pd.DataFrame(columns=[KEY_SPALTE, ANZEIGE_SPALTE, *SPALTEN])


def lade(pfad: str = PFAD) -> pd.DataFrame:
    """Liest die Konfiguration. Fehlt die Datei, kommt ein LEERER DataFrame
    zurück statt einer Exception: Banner und Kasten entfallen dann still,
    App und Export laufen weiter."""
    if not os.path.exists(pfad):
        return leer()
    return pd.read_excel(pfad)


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
