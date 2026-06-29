"""
modules/pptx_helpers.py — Generische PPTX-Helper-Funktionen.

Pure PPTX-Mechanik OHNE Domain-Wissen (keine Performance/Anlagevorschlag/
Portfolio-Logik). Diese Helper sind die Bausteine, mit denen die höheren
Module (pptx_charts, pptx_slides, pptx_export) arbeiten.

Was hier hingehört:
- Shape-Lookup nach Namen
- Text-Manipulation in Shapes und Tabellen-Zellen
- Tabellen leeren / Header behalten
- PPTX-Vorlage laden
- Pure Daten-Konvertierungs-Helper

Was hier NICHT hingehört:
- Chart-Manipulation (→ pptx_charts.py, Schritt 7)
- Slide-Befüllung mit Domain-Daten (→ pptx_slides.py, Schritt 8)
- Slide-Duplikation / Reorder (→ separates Modul, Schritt 6c)

Diese Datei hat KEINE Imports von Streamlit.
Sie kann unverändert in lokalen Python-Skripten genutzt werden.
"""

import os
from typing import Optional

import pandas as pd
from pptx import Presentation


# ─────────────────────────────────────────────────────────────────────────────
# Default-Vorlage
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TEMPLATE_PATH = os.path.join("Vorlage", "Vorlage_FFPB.pptx")
"""Pfad zur Standard-Vorlage. Kann pro Aufruf von load_template() überschrieben werden."""


# ─────────────────────────────────────────────────────────────────────────────
# Shape-Lookup
# ─────────────────────────────────────────────────────────────────────────────

def find_shape_by_name(slide, name: str):
    """Findet ein Shape auf einer Slide anhand seines Namens.

    Args:
        slide: pptx.slide.Slide
        name: Shape-Name wie er in PowerPoint vergeben wurde (z.B. "Tabelle", "Diagramm links")

    Returns:
        Das Shape-Objekt oder None falls nicht gefunden.
    """
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Text-Manipulation in Shapes
# ─────────────────────────────────────────────────────────────────────────────

def replace_text_in_shape(shape, new_text: str):
    """Ersetzt den Text in einem Text-Shape (z.B. Placeholder).

    Behält die Formatierung des ersten Runs bei (Schriftart, Größe, Farbe).
    Alle weiteren Paragraphen und Runs werden entfernt.

    Args:
        shape: Shape mit has_text_frame=True
        new_text: Neuer Text

    No-op wenn das Shape kein text_frame hat.
    """
    if not shape.has_text_frame:
        return
    tf = shape.text_frame
    # Alle Paragraphen außer dem ersten löschen
    while len(tf.paragraphs) > 1:
        p = tf.paragraphs[-1]._p
        p.getparent().remove(p)
    # Im ersten Paragraphen: ersten Run behalten, Text ersetzen, Rest löschen
    p = tf.paragraphs[0]
    if len(p.runs) == 0:
        p.text = new_text
    else:
        p.runs[0].text = new_text
        for run in p.runs[1:]:
            r = run._r
            r.getparent().remove(r)


# ─────────────────────────────────────────────────────────────────────────────
# Tabellen-Zellen-Text
# ─────────────────────────────────────────────────────────────────────────────

def set_cell_text(cell, text: str, is_bold: Optional[bool] = None):
    """Setzt den Text einer Tabellenzelle.

    WICHTIG: Leere Strings werden zu NBSP (U+00A0) konvertiert. Grund:
    Die Vorlage verwendet in nicht-befüllten Zellen ebenfalls NBSP als
    Platzhalter. Lässt man die Zelle mit leerem <a:t/> zurück, rendert
    LibreOffice sie mit Default-Font-Metriken (größere Zeilenhöhe), was
    die gesamte Tabelle vertikal streckt und zu Überlauf führen kann.

    Args:
        cell: Die Zelle
        text: Der neue Text (leer → NBSP)
        is_bold: Wenn explizit True/False: setzt Bold-Formatierung.
                 Wenn None: behält vorherige Formatierung bei.
    """
    # Leere Zellen auf NBSP setzen
    if text == "":
        text = "\u00A0"

    tf = cell.text_frame
    # Alle Paragraphen außer dem ersten löschen
    while len(tf.paragraphs) > 1:
        p = tf.paragraphs[-1]._p
        p.getparent().remove(p)
    p = tf.paragraphs[0]
    if len(p.runs) == 0:
        p.text = text
        # Bold explizit setzen wenn gewünscht
        if is_bold is not None and p.runs:
            p.runs[0].font.bold = is_bold
    else:
        p.runs[0].text = text
        # Bold explizit setzen wenn gewünscht
        if is_bold is not None:
            p.runs[0].font.bold = is_bold
        for run in p.runs[1:]:
            r = run._r
            r.getparent().remove(r)


def set_cell_text_preserve_format(cell, text: str):
    """Setzt Zellen-Text und erhält das Format des ersten Runs.

    Im Gegensatz zu `set_cell_text` (das alle Runs durch einen neuen leeren Run
    ersetzt) bleibt hier die Font-Formatierung (Größe, Farbe, Bold) erhalten —
    wichtig für gestylte Tabellen-Zellen (z.B. fett, weiß auf blauem Header).

    Args:
        cell: Die Zelle
        text: Der neue Text
    """
    if not cell.text_frame.paragraphs:
        # Fallback: kein Paragraph → normales set_cell_text Verhalten
        set_cell_text(cell, text)
        return
    para = cell.text_frame.paragraphs[0]
    if not para.runs:
        set_cell_text(cell, text)
        return
    # Erste Run behält ihr Format, alle weiteren Runs löschen
    runs = list(para.runs)
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    # Weitere Paragraphs löschen
    for p in cell.text_frame.paragraphs[1:]:
        p._p.getparent().remove(p._p)


# ─────────────────────────────────────────────────────────────────────────────
# Tabellen-Operationen
# ─────────────────────────────────────────────────────────────────────────────

def clear_table(table, keep_header_rows: int = 1):
    """Leert alle Zellen einer Tabelle ab der angegebenen Start-Zeile.

    Args:
        table: pptx.table.Table
        keep_header_rows: Anzahl der Header-Zeilen die behalten werden (default: 1)
    """
    for row_idx in range(keep_header_rows, len(table.rows)):
        for cell in table.rows[row_idx].cells:
            set_cell_text(cell, "")


# ─────────────────────────────────────────────────────────────────────────────
# Daten-Konvertierung
# ─────────────────────────────────────────────────────────────────────────────

def safe_float(value, default: float = 0.0) -> float:
    """Konvertiert einen Wert zu float. NaN, NaT, None, ungültige Werte → default.

    Wichtig: Verhindert TypeError beim Vergleich/Sortieren gemischter Typen.

    Args:
        value: Beliebiger Wert
        default: Rückgabewert bei ungültigem Input (default: 0.0)

    Returns:
        Float-Wert oder default.
    """
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Template laden
# ─────────────────────────────────────────────────────────────────────────────

def load_template(path: Optional[str] = None) -> Presentation:
    """Lädt eine PPTX-Vorlage.

    Args:
        path: Pfad zur PPTX-Datei. None = DEFAULT_TEMPLATE_PATH.

    Returns:
        pptx.Presentation Objekt.

    Raises:
        FileNotFoundError: wenn die Datei nicht existiert.
    """
    template_path = path if path is not None else DEFAULT_TEMPLATE_PATH
    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"Vorlage nicht gefunden: {template_path}\n"
            f"Bitte 'Vorlage_FFPB.pptx' im Ordner 'Vorlage/' ablegen."
        )
    return Presentation(template_path)
