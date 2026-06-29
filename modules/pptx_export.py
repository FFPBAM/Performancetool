# modules/pptx_export.py
"""
PowerPoint-Export für Performance und Portfolioanalyse.

Nutzt eine Corporate-Vorlage (Vorlage/Vorlage_FFPB.pptx) und befüllt sie
mit den Daten aus dem Streamlit-Tool.

Öffentliche API:
- generate_portfolioanalyse_pptx(...) -> bytes
- generate_performance_pptx(...) -> bytes  (später)

Wichtigste Mechanik:
- Die Vorlage enthält benannte Shapes (C_Kennzahlen, T_Kennzahlen, C_Kennzahlen1, C_Kennzahlen2)
- Wir finden diese Shapes per Name und tauschen Inhalte aus
- Für Vergleichsportfolios werden Slides 7-10 dupliziert
"""

import os
import io
import copy
import datetime as dt
from typing import Optional

import pandas as pd
from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.chart.data import CategoryChartData
from lxml import etree


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
TEMPLATE_PATH = os.path.join("Vorlage", "Vorlage_FFPB.pptx")

# Strategienamen-Präfixe die entfernt werden (am Anfang oder am Ende)
STRATEGY_PREFIXES = ["cVV", "Muster", "Stiftung"]

# Slide-Positionen in der Vorlage (1-indexed)
SLIDE_ANLAGEVORSCHLAG_1 = 7    # Aktien + Allokations-Ring
SLIDE_ANLAGEVORSCHLAG_2 = 8    # Renten/Edelmetalle/Liquidität
SLIDE_ZUSAMMENSTELLUNG_1 = 9   # Regionen + Branchen (2 Ringe)
SLIDE_ZUSAMMENSTELLUNG_2 = 10  # Währungen (1 Ring)

# Shape-Namen in der Vorlage
SHAPE_CHART_ALLOCATION = "C_Kennzahlen"    # Ring-Diagramm (Slides 7, 8)
SHAPE_TABLE = "T_Kennzahlen"               # Positionen-Tabelle (Slides 7, 8)
SHAPE_CHART_LEFT = "C_Kennzahlen1"         # Linkes Ring-Diagramm (Slides 9, 10)
SHAPE_CHART_RIGHT = "C_Kennzahlen2"        # Rechtes Ring-Diagramm (Slide 9)
SHAPE_TITLE = "Titel"
SHAPE_TITLE_ALT = "Titel 2"

# Strategieentwurf-Titel für Slide 7 (Email-Anforderung Juni 2026, Compliance)
# Ersetzt den dynamischen "Anlagevorschlag – <Strategie>"-Titel ausschließlich
# auf Slide 7. Slide 8 (zweite Anlagevorschlag-Folie) behält den dynamischen Titel.
STRATEGIEENTWURF_TITLE = "Strategieentwurf im Rahmen einer Vermögensverwaltung"

# Foliennummer-Shape-Namen (uneinheitlich in der Vorlage):
# - Die meisten Slides nutzen "Foliennummer"
# - Slides 7, 8, 10 nutzen "Foliennummernplatzhalter 1" (anderer Layout-Master)
# Slides ohne eines dieser Shapes (Cover, Sub-Cover, Impressum) behalten keine Seitenzahl.
SHAPE_FOLIENNUMMER_NAMES = (
    "Foliennummer",
    "Foliennummernplatzhalter 1",
    "Slide Number",
    "Folienzahl",
)


# ---------------------------------------------------------------------------
# Strategienamen-Konvertierung
# ---------------------------------------------------------------------------
def clean_strategy_name(name: str) -> str:
    """
    Entfernt Präfixe (cVV, Muster, Stiftung) vom Anfang ODER Ende und
    kapitalisiert den ersten Buchstaben.

    Beispiele:
        'cVV konservativ'          -> 'Konservativ'
        'Muster konservativ cVV'   -> 'Konservativ'
        'Stiftung konservativ'     -> 'Konservativ'
        'Pro'                      -> 'Pro'
        'Dividende'                -> 'Dividende'
    """
    if not name:
        return ""

    name = name.strip()

    # Präfixe entfernen (am Anfang UND am Ende, beliebig oft)
    changed = True
    while changed:
        changed = False
        for prefix in STRATEGY_PREFIXES:
            if name.startswith(prefix + " "):
                name = name[len(prefix) + 1:].strip()
                changed = True
            if name.endswith(" " + prefix):
                name = name[:-len(prefix) - 1].strip()
                changed = True

    if not name:
        return ""

    # Erster Buchstabe groß, Rest wie ist (oder komplett groß wenn alles groß war)
    return name[0].upper() + name[1:]


# ---------------------------------------------------------------------------
# Shape-Helpers
# ---------------------------------------------------------------------------
def _find_shape_by_name(slide, name: str):
    """Findet ein Shape auf einer Slide anhand seines Namens. Gibt None zurück falls nicht gefunden."""
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    return None


def _replace_text_in_shape(shape, new_text: str):
    """Ersetzt den Text in einem Text-Shape. Behält Formatierung des ersten Runs bei."""
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
        # Alle weiteren Runs entfernen
        for run in p.runs[1:]:
            r = run._r
            r.getparent().remove(r)


# ---------------------------------------------------------------------------
# Slide-Duplikation (für Vergleichsportfolio)
# ---------------------------------------------------------------------------
def _duplicate_slide(prs, source_idx: int):
    """
    Dupliziert eine Slide samt Chart-Teilen und Image-Referenzen.
    Die Charts werden dabei so kopiert, dass Änderungen am Duplikat
    NICHT das Original überschreiben.

    Fügt die neue Slide direkt hinter die Quelle ein.
    Returns: Die neue Slide.
    """
    from copy import deepcopy
    from pptx.opc.packuri import PackURI

    source = prs.slides[source_idx]

    # Neue Slide mit gleichem Layout anlegen
    new_slide = prs.slides.add_slide(source.slide_layout)

    # Alle Shapes entfernen die beim Layout-Add automatisch kamen
    for shape in list(new_slide.shapes):
        sp = shape._element
        sp.getparent().remove(sp)

    # Mapping alte rId → neue rId für Duplikate
    rid_map = {}

    for rel in list(source.part.rels.values()):
        if "chart" in rel.reltype:
            # Chart-Part duplizieren (eigener Part mit neuer Datei-URI)
            new_chart_part = _clone_chart_part(prs, rel.target_part)
            new_rel_id = new_slide.part.relate_to(new_chart_part, rel.reltype)
            rid_map[rel.rId] = new_rel_id
        elif "image" in rel.reltype:
            # Image-Part wiederverwenden – Bilder werden nicht modifiziert
            new_rel_id = new_slide.part.relate_to(rel.target_part, rel.reltype)
            rid_map[rel.rId] = new_rel_id

    # Shapes kopieren und rId-Referenzen patchen
    R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    for shape in source.shapes:
        el = shape.element
        new_el = deepcopy(el)

        # Alle r:id / r:embed / r:link Attribute im XML durchgehen und mappen
        for attr in ["id", "embed", "link"]:
            attr_name = R_NS + attr
            for el_with_rid in new_el.iter():
                if attr_name in el_with_rid.attrib:
                    old_rid = el_with_rid.attrib[attr_name]
                    if old_rid in rid_map:
                        el_with_rid.attrib[attr_name] = rid_map[old_rid]

        new_slide.shapes._spTree.insert_element_before(new_el, "p:extLst")

    # Die neue Slide ist aktuell am Ende – verschieben hinter die Quelle
    xml_slides = prs.slides._sldIdLst
    slides = list(xml_slides)
    new_slide_element = slides[-1]
    xml_slides.remove(new_slide_element)
    xml_slides.insert(source_idx + 1, new_slide_element)

    return new_slide


def _clone_chart_part(prs, source_chart_part):
    """
    Erstellt eine tiefe Kopie eines Chart-Parts mit eigener URI.
    Kopiert auch die Sub-Relationships (z.B. embeddings zu XLSX).
    """
    from copy import deepcopy
    from pptx.opc.packuri import PackURI

    package = source_chart_part.package

    # Neue URI finden (nächste freie chartN.xml)
    existing_nums = set()
    for part in package.iter_parts():
        partname_str = str(part.partname)
        m = re.search(r'/ppt/charts/chart(\d+)\.xml$', partname_str)
        if m:
            existing_nums.add(int(m.group(1)))
    n = 1
    while n in existing_nums:
        n += 1
    new_partname = PackURI(f"/ppt/charts/chart{n}.xml")

    # Chart-Part-Klasse nutzen und neuen Part mit neuer URI erstellen
    # Signatur: Part.load(partname, content_type, package, blob)
    chart_part_cls = type(source_chart_part)
    new_chart_part = chart_part_cls.load(
        new_partname,
        source_chart_part.content_type,
        package,
        source_chart_part.blob,
    )

    # Sub-Relationships kopieren (z.B. Excel-Embedding)
    for rel in source_chart_part.rels.values():
        if rel.is_external:
            new_chart_part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
        else:
            new_chart_part.relate_to(rel.target_part, rel.reltype)

    return new_chart_part


# Re wird in _clone_chart_part benutzt
import re


# ---------------------------------------------------------------------------
# Chart-Befüllung (Ring-Diagramme) – XML-basiert (robust gegen externe Excel-Refs)
# ---------------------------------------------------------------------------
_NS_CHART = {
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
}


def _replace_chart_data(chart_shape, categories: list, values: list, series_name: str = "Anteil"):
    """
    Ersetzt die Daten eines bestehenden Charts in der Vorlage.
    Arbeitet direkt auf der Chart-XML (robust gegen externe Excel-Referenzen).

    Args:
        chart_shape: Das Chart-Shape (shape.has_chart == True)
        categories: Liste der Kategorie-Namen (z.B. ["Aktien", "Renten", "Edelmetalle"])
        values: Liste der zugehörigen Werte (z.B. [0.75, 0.17, 0.05])
        series_name: Name der Datenreihe (wird in <c:tx> geschrieben falls vorhanden)
    """
    if len(categories) != len(values):
        raise ValueError(f"Kategorien ({len(categories)}) und Werte ({len(values)}) müssen gleiche Länge haben")

    chart = chart_shape.chart
    chart_xml = chart._chartSpace
    ns = _NS_CHART

    # Alle Kategorien <c:pt><c:v>...</c:v></c:pt> finden
    cat_refs = chart_xml.findall('.//c:cat//c:strRef', ns) + chart_xml.findall('.//c:cat//c:strCache', ns)
    val_refs = chart_xml.findall('.//c:val//c:numRef', ns) + chart_xml.findall('.//c:val//c:numCache', ns)

    # Wir arbeiten auf den *Cache-Einträgen*, da strRef intern einen strCache hat.
    # Einfacher: wir suchen direkt alle cat/pt und val/pt Elemente.

    # === Kategorien aktualisieren ===
    cat_elem = chart_xml.find('.//c:cat', ns)
    if cat_elem is not None:
        _update_cache_elements(cat_elem, categories, is_numeric=False)

    # === Werte aktualisieren ===
    val_elem = chart_xml.find('.//c:val', ns)
    if val_elem is not None:
        _update_cache_elements(val_elem, values, is_numeric=True)


def _update_cache_elements(parent, new_values, is_numeric: bool):
    """
    Updated die <c:pt>-Elemente im Cache eines <c:cat> oder <c:val> Elements.
    Fügt bei Bedarf neue Punkte hinzu oder entfernt überzählige.
    """
    ns = _NS_CHART
    c_ns = 'http://schemas.openxmlformats.org/drawingml/2006/chart'

    # Cache-Element finden (strCache oder numCache)
    if is_numeric:
        cache = parent.find('.//c:numCache', ns)
        if cache is None:
            cache = parent.find('.//c:numRef/c:numCache', ns)
    else:
        cache = parent.find('.//c:strCache', ns)
        if cache is None:
            cache = parent.find('.//c:strRef/c:strCache', ns)

    if cache is None:
        # Kein Cache vorhanden – wir müssen ihn ggf. anlegen. Für unseren Use-Case
        # (Charts aus PPTX-Vorlage) ist der Cache immer vorhanden.
        return

    # ptCount aktualisieren
    pt_count = cache.find('c:ptCount', ns)
    if pt_count is not None:
        pt_count.set('val', str(len(new_values)))

    # Bestehende <c:pt>-Elemente entfernen
    for pt in cache.findall('c:pt', ns):
        cache.remove(pt)

    # Neue <c:pt>-Elemente hinzufügen
    for idx, val in enumerate(new_values):
        pt = etree.SubElement(cache, f'{{{c_ns}}}pt')
        pt.set('idx', str(idx))
        v_el = etree.SubElement(pt, f'{{{c_ns}}}v')
        if is_numeric:
            v_el.text = f"{float(val)}"
        else:
            v_el.text = str(val)


# ---------------------------------------------------------------------------
# Tabellen-Befüllung
# ---------------------------------------------------------------------------
def _set_cell_text(cell, text: str, is_bold: bool = None):
    """
    Setzt den Text einer Tabellenzelle.

    WICHTIG: Leere Strings werden zu NBSP (U+00A0) konvertiert. Grund:
    Die Vorlage verwendet in nicht-befüllten Zellen ebenfalls NBSP als
    Platzhalter. Lässt man die Zelle mit leerem <a:t/> zurück, rendert
    LibreOffice sie mit Default-Font-Metriken (größere Zeilenhöhe), was
    die gesamte Tabelle vertikal streckt und zu Überlauf auf Slide 7 führt.

    Args:
        cell: Die Zelle
        text: Der neue Text (leer → NBSP)
        is_bold: Wenn explizit True/False: setzt Bold-Formatierung.
                 Wenn None: behält vorherige Formatierung bei.
    """
    # Leere Zellen auf NBSP setzen (siehe Docstring oben)
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


def _clear_table(table, keep_header_rows: int = 1):
    """Leert alle Zellen einer Tabelle ab der angegebenen Start-Zeile (Header bleibt)."""
    for row_idx in range(keep_header_rows, len(table.rows)):
        for cell in table.rows[row_idx].cells:
            _set_cell_text(cell, "")


# ---------------------------------------------------------------------------
# Template laden
# ---------------------------------------------------------------------------
def _load_template() -> Presentation:
    """Lädt die PPTX-Vorlage. Raises FileNotFoundError wenn nicht vorhanden."""
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Vorlage nicht gefunden: {TEMPLATE_PATH}\n"
            f"Bitte 'Vorlage_FFPB.pptx' im Ordner 'Vorlage/' ablegen."
        )
    return Presentation(TEMPLATE_PATH)


# ---------------------------------------------------------------------------
# Formatierungs-Helpers
# ---------------------------------------------------------------------------
def _fmt_pct(value) -> str:
    """0.02 → '2,00%', NaN/None → '-'"""
    if value is None or pd.isna(value):
        return "-"
    try:
        return f"{float(value) * 100:.2f}".replace(".", ",") + "%"
    except (ValueError, TypeError):
        return "-"


def _fmt_date_de(value) -> str:
    """datetime → '01.11.2028', None → '-'"""
    if value is None or pd.isna(value):
        return "-"
    try:
        if hasattr(value, 'strftime'):
            return value.strftime("%d.%m.%Y")
        return str(value)
    except Exception:
        return "-"


# ---------------------------------------------------------------------------
# Gattungs-Klassifizierung
# ---------------------------------------------------------------------------
# Gruppen-Namen wie sie auf den Slides erscheinen sollen (GROSSBUCHSTABEN)
GROUP_AKTIEN = "AKTIEN"
GROUP_RENTEN = "RENTEN"
GROUP_EDELMETALLE = "EDELMETALLE"
GROUP_LIQUIDITAET = "LIQUIDITÄT"
GROUP_SONSTIGE = "SONSTIGE"

# Reihenfolge der Gruppen auf den Slides (nach Priorität der Vorlage)
GROUP_ORDER = [GROUP_AKTIEN, GROUP_RENTEN, GROUP_EDELMETALLE, GROUP_LIQUIDITAET, GROUP_SONSTIGE]


def _safe_float(value, default: float = 0.0) -> float:
    """
    Konvertiert einen Wert zu float. NaN, NaT, None, ungültige Werte → default (0.0).
    Wichtig: Verhindert TypeError beim Vergleich/Sortieren gemischter Typen.
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


def _set_title_with_autoscale(title_shape, text: str):
    """
    Setzt den Titel-Text auf Folie 7 und passt die Schriftgröße dynamisch
    an die Textlänge an, damit der gesamte Titel auf EINE Zeile passt.

    Hintergrund:
    Die Titel-Box ist nur ~0.39" hoch (1 Zeile) und ~10.67" breit.
    Bei langem Strategienamen würde der Text in 2 Zeilen umbrechen.

    Strategie (kombiniert):
    1. Manuelle, aggressive Schwellen (empirisch kalibriert in Juni 2026)
    2. Auto-Fit als zusätzliche Sicherheit (PowerPoint skaliert ggf. nach)

    Schwellen (für Standard-Bold-Schrift, 10.67" Box-Breite):
    - ≤ 66 Zeichen → Layout-Default (~32 pt)
    - 67-72 Zeichen → 26 pt
    - 73-80 Zeichen → 22 pt
    - 81-88 Zeichen → 20 pt
    - 89-96 Zeichen → 18 pt
    - 97-108 Zeichen → 16 pt
    - > 108 Zeichen → 14 pt
    """
    # Text setzen (existierender Helper)
    _replace_text_in_shape(title_shape, text)

    # Schriftgröße basierend auf Textlänge
    char_count = len(text)
    if char_count <= 66:
        font_size_pt = None  # Layout-Default beibehalten
    elif char_count <= 72:
        font_size_pt = 26
    elif char_count <= 80:
        font_size_pt = 22
    elif char_count <= 88:
        font_size_pt = 20
    elif char_count <= 96:
        font_size_pt = 18
    elif char_count <= 108:
        font_size_pt = 16
    else:
        font_size_pt = 14

    tf = title_shape.text_frame

    if font_size_pt is not None:
        for para in tf.paragraphs:
            for run in para.runs:
                run.font.size = Pt(font_size_pt)

    # Auto-Fit aktivieren als Sicherheits-Netz
    # PowerPoint reduziert die Schriftgröße weiter, falls der Text immer noch nicht passt.
    try:
        from pptx.enum.text import MSO_AUTO_SIZE
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.word_wrap = True
    except Exception:
        pass  # Nicht verfügbar in alten python-pptx-Versionen


def _safe_marktrisikowert(value) -> str:
    """
    Konvertiert einen Wert aus der CSV-Spalte 'Marktrisikowert' zu einem String.
    Fallback zu '-' wenn None, NaN, leer, oder ungültiger Typ.
    Float-Werte werden als Integer dargestellt (3.0 → '3'), damit in der
    Tabelle keine Nachkommastellen erscheinen.
    """
    if value is None:
        return "-"
    try:
        if pd.isna(value):
            return "-"
    except (TypeError, ValueError):
        pass
    # Versuch: als ganze Zahl darstellen (3.0 → '3')
    try:
        return str(int(float(value)))
    except (ValueError, TypeError):
        # Fallback: String trimmen
        s = str(value).strip()
        return s if s else "-"


def _classify_gattung(gattung) -> str:
    """Ordnet eine Gattung einer der 5 Hauptgruppen zu."""
    if gattung is None:
        return GROUP_SONSTIGE
    try:
        if pd.isna(gattung):
            return GROUP_SONSTIGE
    except (TypeError, ValueError):
        pass
    g = str(gattung).lower()
    if "aktie" in g or "equity" in g:
        return GROUP_AKTIEN
    if "rente" in g or "anleihe" in g or "bond" in g:
        return GROUP_RENTEN
    if "edelmetall" in g or "gold" in g or "silber" in g:
        return GROUP_EDELMETALLE
    if "liquid" in g or "cash" in g:
        return GROUP_LIQUIDITAET
    return GROUP_SONSTIGE


def _group_portfolio_positions(df: pd.DataFrame) -> dict:
    """
    Gruppiert Portfoliopositionen nach GROUP_ORDER.
    Innerhalb jeder Gruppe sind Positionen nach Gewicht absteigend sortiert.

    Positionen werden ausgefiltert wenn:
    - Kein Wertpapier-Name vorhanden ist
    - Gewicht = 0 oder NaN ist
    - Wertpapier-Name "nan", "NaT", "None" oder leer ist (Müll aus CSV)

    Returns:
        {
            "AKTIEN": [{"wertpapier": ..., "wkn": ..., "gewicht": 0.02, ...}, ...],
            "RENTEN": [...],
            ...
        }
        Leere Gruppen werden weggelassen.
    """
    groups = {g: [] for g in GROUP_ORDER}

    # Junk-Strings die wir als "leer" behandeln
    JUNK_STRINGS = {"", "nan", "NaN", "NaT", "None", "null"}

    for _, row in df.iterrows():
        wertpapier = str(row.get("Wertpapier", "")).strip()
        gewicht = _safe_float(row.get("Gewicht", 0.0), 0.0)

        # Müll-Zeilen rausfiltern
        if wertpapier in JUNK_STRINGS:
            continue
        if gewicht <= 0.0001:
            continue

        gruppe = _classify_gattung(row.get("Gattung"))

        # WKN auch auf Müll checken
        wkn = str(row.get("WKN", "")).strip()
        if wkn in JUNK_STRINGS:
            wkn = ""

        pos = {
            "wertpapier": wertpapier,
            "wkn": wkn,
            "gewicht": gewicht,
            "kupon": row.get("Kupon"),  # kann NaN sein, wird beim Formatieren behandelt
            "faelligkeit": row.get("Fälligkeit_parsed") if "Fälligkeit_parsed" in row.index else None,
            "rating": _safe_marktrisikowert(row.get("Marktrisikowert")),  # CSV-Spalte 'Marktrisikowert' (3-6), Fallback '-'
        }
        groups[gruppe].append(pos)

    # Innerhalb jeder Gruppe alphabetisch nach Wertpapier-Name sortieren
    # (anstelle der früheren Sortierung nach Gewicht — auf Wunsch des Anforderers, Juni 2026)
    for g in groups:
        groups[g] = sorted(groups[g], key=lambda p: str(p["wertpapier"]).lower())

    # Liquidität aus Differenz berechnen (falls nicht explizit in Daten)
    if "Gewicht" in df.columns:
        # skipna=True ist default, aber explizit zur Sicherheit
        total_weight = _safe_float(df["Gewicht"].sum(skipna=True), 0.0)
    else:
        total_weight = 0.0
    liq_from_positions = sum(_safe_float(p["gewicht"], 0.0) for p in groups[GROUP_LIQUIDITAET])
    implicit_liq = max(0.0, 1.0 - total_weight)
    if implicit_liq > 0.0001 and liq_from_positions < 0.0001:
        groups[GROUP_LIQUIDITAET].append({
            "wertpapier": "",  # Liquidität braucht keinen Namen in der Zeile
            "wkn": "",
            "gewicht": implicit_liq,
            "kupon": None,
            "faelligkeit": None,
            "rating": "",
        })

    # Leere Gruppen entfernen
    return {g: ps for g, ps in groups.items() if ps}


# ---------------------------------------------------------------------------
# Positionen-Verteilung auf Slides
# ---------------------------------------------------------------------------
# Maximal verfügbare Zeilen pro Slide (ohne Header, ohne Summen-Zeile)
# Slide 7: 36 Zeilen - 1 Header - 1 Summen-Zeile = 34. 1 davon ist Gruppen-Header = 33 Positionen max
# Slide 8: 14 Zeilen - 1 Header - 1 Summen-Zeile = 12 Zeilen für Gruppen+Positionen
SLIDE_7_DATA_ROWS = 34   # Zeilen 1-34, Zeile 35 = Summe
SLIDE_8_DATA_ROWS = 12   # Zeilen 1-12, Zeile 13 = Summe


def _distribute_positions_to_slides(groups: dict) -> list:
    """
    Verteilt gruppierte Positionen auf Slide 7 (Anlagevorschlag).

    Seit Juni 2026 (Performance-Folie als neue Slide 8):
    - Alle Positionen kommen auf Slide 7
    - Slide 8 ist jetzt die Performance-Folie (kein Überlauf von Anlagevorschlag mehr)
    - Bei mehr als SLIDE_7_DATA_ROWS (34) Positionen werden die Überschüssigen
      in _fill_table_with_positions automatisch abgeschnitten (Edge-Case)

    Reihenfolge der Zeilen:
    - Asset-Gruppen nach Gewicht absteigend (AKTIEN, RENTEN, EDELMETALLE, ...)
    - LIQUIDITÄT IMMER am Ende als eigene Zeile

    Returns: Liste mit 2 Einträgen (Slide 7 voll, Slide 8 leer):
        [
            {"rows": [...alle Positionen...], "is_last_slide": True},
            {"rows": [], "is_last_slide": False},
        ]
    """
    # 1. Gruppen nach Gewicht sortieren, LIQUIDITÄT explizit ans Ende
    non_liq = [(n, ps) for n, ps in groups.items() if n != GROUP_LIQUIDITAET]
    non_liq.sort(
        key=lambda kv: sum(_safe_float(p["gewicht"], 0.0) for p in kv[1]),
        reverse=True,
    )
    liq_positions = groups.get(GROUP_LIQUIDITAET, [])
    has_liq = bool(liq_positions) and sum(
        _safe_float(p["gewicht"], 0.0) for p in liq_positions
    ) > 0.0001

    if not non_liq and not has_liq:
        return [
            {"rows": [], "is_last_slide": True},
            {"rows": [], "is_last_slide": False},
        ]

    # 2. Alle nicht-LIQ-Gruppen in flache Zeilen-Liste expandieren
    all_rows = []
    for group_name, positions in non_liq:
        all_rows.append({"type": "group_header", "data": {"name": group_name}})
        for pos in positions:
            all_rows.append({"type": "position", "data": pos})

    # 3. LIQUIDITÄT als EIGENE Zeile am Ende
    if has_liq:
        total_liq = sum(_safe_float(p["gewicht"], 0.0) for p in liq_positions)
        all_rows.append({
            "type": "liquidity",
            "data": {"name": GROUP_LIQUIDITAET, "liq_value": total_liq},
        })

    # Alles auf Slide 7, Slide 8 (Performance) bleibt unangetastet
    return [
        {"rows": all_rows, "is_last_slide": True},   # Slide 7: alle Positionen + Summe
        {"rows": [], "is_last_slide": False},        # Slide 8: leer (= Performance-Folie)
    ]
# ---------------------------------------------------------------------------
# Tabellen-Befüllung
# ---------------------------------------------------------------------------
# Spalten-Mapping (welche Spalte enthält was)
COL_WERTPAPIER = 0
COL_KUPON = 2
COL_FAELLIGKEIT = 4
COL_WKN = 6
COL_ANTEIL = 8
COL_RATING = 10

# Spalten die immer leer bleiben (Layout-Spacer)
COL_SPACERS = [1, 3, 5, 7, 9]


def _fill_table_with_positions(table, slide_data: dict, total_weight: float = 1.0,
                               shape_height: int = 0):
    """
    Befüllt eine Tabelle (Slide 7 oder 8) mit Positionen.

    Die Tabellen-Struktur der Vorlage bleibt UNVERÄNDERT (keine Zeilen entfernt,
    keine Höhen geändert). Nicht benötigte Zeilen bleiben leer sichtbar.

    Args:
        table: Die Tabelle (shape.table)
        slide_data: {"rows": [...], "is_last_slide": bool}
        total_weight: Summe aller Gewichte (für Summen-Zeile, default 100%)
        shape_height: Höhe der Tabellen-Shape in EMU (wird nicht mehr verwendet,
                      aus Kompat-Gründen in der Signatur belassen)
    """
    n_rows_initial = len(table.rows)
    rows = slide_data["rows"]
    is_last = slide_data["is_last_slide"]

    # Summen-Zeile ist immer die letzte Zeile in der Vorlage
    summary_row_idx = n_rows_initial - 1
    # Datenzeilen gehen von 1 bis n_rows-2
    max_data_rows = n_rows_initial - 2

    # Erst alle Datenzeilen leeren (nur Spalten 0, 2, 4, 6, 8, 10 - Spacer bleiben)
    for row_idx in range(1, n_rows_initial):
        row = table.rows[row_idx]
        for col_idx in [COL_WERTPAPIER, COL_KUPON, COL_FAELLIGKEIT, COL_WKN, COL_ANTEIL, COL_RATING]:
            _set_cell_text(row.cells[col_idx], "")

    # Zeilen befüllen
    for i, row_def in enumerate(rows):
        if i >= max_data_rows:
            break  # Kein Platz mehr

        target_row_idx = i + 1  # +1 weil Zeile 0 der Tabellen-Header ist
        row = table.rows[target_row_idx]

        if row_def["type"] in ("group_header", "liquidity"):
            # Gruppen-Header: Name in Spalte 0, alle anderen leer
            # Explizit BOLD für Headers
            name = row_def["data"]["name"]
            _set_cell_text(row.cells[COL_WERTPAPIER], name, is_bold=True)
            # Bei RENTEN: "KUPON" und "FÄLLIGKEIT" als Sub-Header in Spalten 2 und 4
            if name == GROUP_RENTEN:
                _set_cell_text(row.cells[COL_KUPON], "KUPON", is_bold=True)
                _set_cell_text(row.cells[COL_FAELLIGKEIT], "FÄLLIGKEIT", is_bold=True)
            # Bei LIQUIDITÄT: Wert direkt in der Header-Zeile (nicht als separate Position)
            if name == GROUP_LIQUIDITAET and "liq_value" in row_def["data"]:
                _set_cell_text(row.cells[COL_ANTEIL], _fmt_pct(row_def["data"]["liq_value"]), is_bold=True)

        elif row_def["type"] == "position":
            data = row_def["data"]
            # Alle Felder einer Position: explizit NICHT BOLD
            # (verhindert dass bei Zeilen die ursprünglich Header waren, die Formatierung hängen bleibt)
            _set_cell_text(row.cells[COL_WERTPAPIER], data["wertpapier"], is_bold=False)
            _set_cell_text(row.cells[COL_WKN], data["wkn"], is_bold=False)
            _set_cell_text(row.cells[COL_ANTEIL], _fmt_pct(data["gewicht"]), is_bold=False)
            _set_cell_text(row.cells[COL_RATING], data.get("rating", "-"), is_bold=False)
            # Kupon (nur wenn vorhanden)
            if data.get("kupon") is not None and not pd.isna(data["kupon"]) and data["kupon"] != 0:
                _set_cell_text(row.cells[COL_KUPON], _fmt_pct(data["kupon"]), is_bold=False)
            else:
                _set_cell_text(row.cells[COL_KUPON], "", is_bold=False)
            # Fälligkeit (nur wenn vorhanden)
            if data.get("faelligkeit") is not None and not pd.isna(data["faelligkeit"]):
                _set_cell_text(row.cells[COL_FAELLIGKEIT], _fmt_date_de(data["faelligkeit"]), is_bold=False)
            else:
                _set_cell_text(row.cells[COL_FAELLIGKEIT], "", is_bold=False)

    # Summen-Zeile: nur auf letzter Slide
    summary_row = table.rows[summary_row_idx]
    # Alle Summen-Zellen leeren
    for col_idx in [COL_WERTPAPIER, COL_KUPON, COL_FAELLIGKEIT, COL_WKN, COL_ANTEIL, COL_RATING]:
        _set_cell_text(summary_row.cells[col_idx], "")

    if is_last:
        # 100,00% in der Anteil-Spalte der Summen-Zeile
        _set_cell_text(summary_row.cells[COL_ANTEIL], _fmt_pct(total_weight))

    # ── Tabellen-Struktur der Vorlage UNVERÄNDERT lassen ──
    # Früher wurden hier überzählige leere Zeilen entfernt (_optimize_table_layout),
    # das hat aber die Shape-Höhe geschrumpft und LibreOffice zum Vergrößern
    # der verbleibenden Zeilen gebracht → Überlauf am unteren Slide-Rand.
    # Die Vorlage ist mit ihren Zeilenhöhen exakt auf die Slide-Höhe kalibriert,
    # also lassen wir ungefüllte Zeilen einfach leer stehen. Das ergibt zwar
    # visuell einen leeren Bereich zwischen letztem Eintrag und Summenzeile,
    # rendert aber korrekt ohne Überlauf.


# ---------------------------------------------------------------------------
# Slide-Befüllung – Anlagevorschlag (Slides 7+8)
# ---------------------------------------------------------------------------
def _fill_anlagevorschlag_slides(prs, slide_7_idx: int,
                                  df: pd.DataFrame, strategy_name: str):
    """
    Befüllt Slide 7 (Anlagevorschlag/Strategieentwurf) mit Portfolio-Daten.

    Seit Juni 2026 (Performance-Folie als Slide 8): Es gibt nur noch EINE
    Anlagevorschlag-Slide. Alle Positionen kommen auf Slide 7, dynamisch
    geschrumpft durch _remove_empty_table_rows + _fit_shape_to_table.

    Args:
        prs: Presentation
        slide_7_idx: 0-indexed Index der Anlagevorschlag-Slide
        df: DataFrame mit Positionen (Wertpapier, WKN, Gewicht, Gattung, Kupon, Fälligkeit_parsed, Marktrisikowert)
        strategy_name: Name der Strategie für den Titel (schon konvertiert)
    """
    # 1. Daten vorbereiten
    groups = _group_portfolio_positions(df)
    slide_distribution = _distribute_positions_to_slides(groups)

    # 2. Allokations-Daten für Ring-Chart (nach Gruppen)
    alloc_labels = []
    alloc_values = []
    for g in GROUP_ORDER:
        if g in groups:
            total = sum(_safe_float(p["gewicht"], 0.0) for p in groups[g])
            if total > 0.0001:
                alloc_labels.append(g)
                alloc_values.append(float(total))

    # Gesamt-Gewicht (für Summen-Zeile)
    total_weight = sum(alloc_values)

    # 3. Slide 7 befüllen
    slide_7 = prs.slides[slide_7_idx]
    # Titel: Strategieentwurf-Hinweis (Email-Anforderung Juni 2026, Compliance)
    # Format: "Strategieentwurf im Rahmen einer Vermögensverwaltung - <Strategiename>"
    # Schriftgröße wird dynamisch angepasst, damit der Titel auf eine Zeile passt.
    title = _find_shape_by_name(slide_7, SHAPE_TITLE_ALT) or _find_shape_by_name(slide_7, SHAPE_TITLE)
    if title:
        _set_title_with_autoscale(title, f"{STRATEGIEENTWURF_TITLE} - {strategy_name}")
    # Ring-Chart
    chart = _find_shape_by_name(slide_7, SHAPE_CHART_ALLOCATION)
    if chart:
        _replace_chart_data(chart, alloc_labels, alloc_values)
    # Tabelle befüllen
    table_shape = _find_shape_by_name(slide_7, SHAPE_TABLE)
    if table_shape:
        _fill_table_with_positions(table_shape.table, slide_distribution[0], total_weight,
                                   shape_height=table_shape.height)
        # Leere Zeilen entfernen (Striche unter der Tabelle eliminieren)
        _remove_empty_table_rows(table_shape.table)
        # NACH dem Befüllen + Bereinigen: Shape-Höhe an verbleibende Zeilen anpassen
        _fit_shape_to_table(table_shape)


def _fill_performance_slide(prs, slide_idx: int, strategy_name: str,
                             performance_data: Optional[dict] = None):
    """
    Befüllt die Performance-Slide (Slide 8: Anlagestrategie Wertentwicklung).

    Args:
        prs: Presentation
        slide_idx: 0-indexed Index der Performance-Slide
        strategy_name: Name der Strategie für den Titel
        performance_data: Dict mit Performance-Daten (siehe `_compute_performance_data`).
                          Wenn None: Nur Titel wird gesetzt, Charts/Tabelle bleiben mit
                          Vorlagen-Platzhaltern (Phase-1-Verhalten).
    """
    slide = prs.slides[slide_idx]

    # Titel anpassen: "{Strategy} | Wertentwicklung (mit Benchmark)"
    title = _find_shape_by_name(slide, "Titel")
    if title and title.has_text_frame:
        new_title = f"{strategy_name} | Wertentwicklung (mit Benchmark)"
        _replace_text_in_shape(title, new_title)

    if performance_data is None:
        return  # Phase 1: nur Titel setzen

    # ── KENNZAHLEN-Tabelle befüllen ──
    kz = performance_data.get("kennzahlen", {})
    tab = _find_shape_by_name(slide, "Tabelle")
    if tab and tab.has_table:
        _fill_kennzahlen_table(tab.table, kz)

    # ── PERFORMANCE P.A. Chart (Säulen) ──
    pa = performance_data.get("performance_pa", {})
    chart_links = _find_shape_by_name(slide, "Diagramm links")
    if chart_links and chart_links.has_chart and pa.get("jahre"):
        _replace_chart_data_safe(
            chart_links,
            categories=[str(y) for y in pa["jahre"]],
            series_data=[
                ("Referenzportfolio", pa.get("referenz", [])),
                ("Benchmark", pa.get("benchmark", [])),
            ],
            data_label_format="0.00%",
        )

    # ── WERTENTWICKLUNG Chart (Linien) ──
    we = performance_data.get("wertentwicklung", {})
    chart_rechts = _find_shape_by_name(slide, "Diagramm rechts")
    if chart_rechts and chart_rechts.has_chart and we.get("dates"):
        _replace_chart_data_safe(
            chart_rechts,
            categories=we["dates"],
            series_data=[
                ("Referenzportfolio", we.get("referenz", [])),
                ("Benchmark", we.get("benchmark", [])),
            ],
            data_label_format=None,  # Linien-Chart hat keine Daten-Labels
        )


def _replace_chart_data_safe(chart_shape, categories: list, series_data: list,
                              data_label_format: Optional[str] = None):
    """
    Ersetzt Chart-Daten — workaround für python-pptx Bugs:

    Bug 1: `chart.replace_data()` updated das embedded Excel-Workbook NICHT
    → Diskrepanz → PowerPoint-Reparieren-Dialog.
    Fix: Nach replace_data() das <c:externalData>-Element entfernen, sodass
    PowerPoint nur die Chart-XML nutzt.

    Bug 2: `chart.replace_data()` überschreibt die Chart-style.xml-Datei mit
    einem ZIP-Header (style7.xml wird zu Binärmüll) → PowerPoint-Reparieren-
    Dialog auch hier.
    Fix: Vor replace_data() ALLE Style/Color-Parts der Chart-Part sichern und
    nach replace_data() wieder zurücksetzen.

    Bug 3: `chart.replace_data()` setzt Format-Codes auf "General" zurück
    → Daten-Labels zeigen "0.05" statt "5,00%".
    Fix: Nach replace_data() den ursprünglichen Format-Code wiederherstellen.

    Args:
        chart_shape: Chart-Shape mit has_chart=True
        categories: Liste der Kategorien (Strings oder Datumangaben)
        series_data: Liste von (series_name, values) Tupeln
        data_label_format: Format-Code für Daten-Labels (z.B. "0.00%"). None = nicht ändern.
    """
    from pptx.chart.data import CategoryChartData

    chart = chart_shape.chart
    chart_part = chart.part

    # ─── BUG 2 FIX: Sichere alle "Hilfs-Parts" der Chart (style, colors) ───
    # Diese Parts sind in den Chart-Rels referenziert und können von python-pptx
    # versehentlich überschrieben werden.
    backup_parts = {}  # partname -> (part_obj, blob)
    for rel_id, rel in chart_part.rels.items():
        try:
            reltype = rel.reltype
        except Exception:
            continue
        # Wir backuppen alles außer dem Chart selbst und externen OLE-Objekten
        if 'chartStyle' in reltype or 'chartColorStyle' in reltype:
            try:
                target = rel.target_part
                backup_parts[str(target.partname)] = (target, bytes(target.blob))
            except Exception:
                pass

    # ─── replace_data ausführen ───
    cd = CategoryChartData()
    cd.categories = categories
    for name, vals in series_data:
        cd.add_series(name, vals)
    chart.replace_data(cd)

    # ─── BUG 2 FIX: Style/Color-Parts aus Backup wiederherstellen ───
    for partname, (part_obj, blob) in backup_parts.items():
        try:
            part_obj._blob = blob
        except Exception:
            pass

    # ─── BUG 1 FIX: <c:externalData> entfernen ───
    ns_uri = "http://schemas.openxmlformats.org/drawingml/2006/chart"
    ns = {"c": ns_uri}
    chart_xml = chart._chartSpace
    ext_data = chart_xml.find(".//c:externalData", ns)
    if ext_data is not None:
        ext_data.getparent().remove(ext_data)

    # ─── BUG 3 FIX: Format-Codes wiederherstellen ───
    if data_label_format:
        _restore_data_label_format(chart_shape, data_label_format)


def _restore_data_label_format(chart_shape, format_code: str):
    """
    Setzt den Format-Code der Daten-Labels in allen Series eines Charts.

    `chart.replace_data()` setzt Format-Codes auf "General" zurück, was dazu führt
    dass z.B. der Wert 0.05 als "0.05" statt "5,00%" angezeigt wird. Diese Funktion
    stellt den ursprünglichen Format-Code wieder her.
    """
    from lxml import etree
    ns_uri = "http://schemas.openxmlformats.org/drawingml/2006/chart"
    ns = {"c": ns_uri}
    chart_xml = chart_shape.chart._chartSpace

    for ser in chart_xml.findall(".//c:ser", ns):
        # <c:dLbls> Element finden oder anlegen
        dlbls = ser.find("c:dLbls", ns)
        if dlbls is None:
            continue  # Keine Daten-Labels in dieser Series

        # <c:numFmt> innerhalb dLbls finden oder anlegen
        num_fmt = dlbls.find("c:numFmt", ns)
        if num_fmt is None:
            num_fmt = etree.SubElement(dlbls, f"{{{ns_uri}}}numFmt")
            # numFmt muss am Anfang von dLbls stehen (vor anderen Properties)
            dlbls.insert(0, num_fmt)
        num_fmt.set("formatCode", format_code)
        num_fmt.set("sourceLinked", "0")


def _fill_kennzahlen_table(table, kz: dict):
    """
    Befüllt die KENNZAHLEN-Tabelle auf der Performance-Folie.

    Tabellen-Layout (7 rows × 5 cols, aber Spacer-Spalten dazwischen):
      Row 0: Header   (KENNZAHLEN | _ | REFERENZ | _ | BENCHMARK)
      Row 1: Performance p.a.
      Row 2: Volatilität
      Row 3: Sharpe Ratio
      Row 4: Max Drawdown
      Rows 5-6: ggf. leer/Spacer

    Wert-Spalten: 2 (REFERENZ), 4 (BENCHMARK)
    """
    metric_rows = [
        ("performance_pa_ref",  "performance_pa_bench",   2, True),   # row 2, Prozent-Format
        ("volatilitaet_ref",    "volatilitaet_bench",     3, True),   # row 3, Prozent
        ("sharpe_ref",          "sharpe_bench",           4, False),  # row 4, Dezimal
        ("max_drawdown_ref",    "max_drawdown_bench",     5, True),   # row 5, Prozent
    ]
    for ref_key, bench_key, row_idx, is_pct in metric_rows:
        if row_idx >= len(table.rows):
            continue
        row = table.rows[row_idx]
        ref_val = kz.get(ref_key)
        bench_val = kz.get(bench_key)
        if is_pct:
            ref_str = _fmt_pct(ref_val)
            bench_str = _fmt_pct(bench_val)
        else:
            ref_str = _fmt_ratio(ref_val)
            bench_str = _fmt_ratio(bench_val)
        # Spalte 2 = REFERENZ, Spalte 4 = BENCHMARK
        _set_cell_text_preserve_format(row.cells[2], ref_str)
        _set_cell_text_preserve_format(row.cells[4], bench_str)


def _fmt_pct(val) -> str:
    """Formatiert einen dezimalen Wert (z.B. 0.0523) als Prozent (5,23 %)."""
    if val is None:
        return "–"
    try:
        v = float(val)
        if v != v:  # NaN check
            return "–"
        return f"{v*100:.2f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "–"


def _fmt_ratio(val) -> str:
    """Formatiert einen Ratio-Wert (z.B. Sharpe 0.43) als Dezimalzahl (0,43)."""
    if val is None:
        return "–"
    try:
        v = float(val)
        if v != v:
            return "–"
        return f"{v:.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "–"


def _set_cell_text_preserve_format(cell, text: str):
    """
    Setzt den Text einer Tabellen-Zelle und erhält das Format des ersten Runs.

    Im Gegensatz zu `_set_cell_text` (das alle Runs durch einen neuen leeren Run
    ersetzt) bleibt hier die Font-Formatierung (Größe, Farbe, Bold) erhalten —
    wichtig für die KENNZAHLEN-Tabelle wo das Vorlagen-Styling (z.B. fett, weiß
    auf blauem Header) nicht überschrieben werden soll.
    """
    if not cell.text_frame.paragraphs:
        # Fallback: kein Paragraph → normales _set_cell_text Verhalten
        _set_cell_text(cell, text)
        return
    para = cell.text_frame.paragraphs[0]
    # Erste Run finden — wenn keine da, lege eine an
    if not para.runs:
        _set_cell_text(cell, text)
        return
    # Erste Run behält ihr Format, alle weiteren Runs löschen
    runs = list(para.runs)
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    # Weitere Paragraphs löschen
    for p in cell.text_frame.paragraphs[1:]:
        p._p.getparent().remove(p._p)


def _update_chart_values_inplace(chart_shape, categories: list, series_data: list):
    """
    Aktualisiert Categories und Values aller Series direkt in der Chart-XML.

    Im Gegensatz zu `chart.replace_data()` bleiben die Format-Codes (z.B. "0.00%"
    für Daten-Labels) erhalten. Wird verwendet für den Säulen-Chart in der
    Performance-Folie wo die Daten-Labels prozent-formatiert sein müssen.

    Anzahl der Series und Datenpunkte muss zum Chart-Template passen
    (5 Jahre × 2 Series für Performance p.a.).

    Args:
        chart_shape: Das Chart-Shape
        categories: Liste der Kategorien (Strings), z.B. ["2021", ..., "2025"]
        series_data: Liste von (series_name, values) Tupeln
    """
    chart = chart_shape.chart
    chart_xml = chart._chartSpace
    ns = _NS_CHART

    ser_elements = chart_xml.findall(".//c:ser", ns)
    if len(ser_elements) != len(series_data):
        # Anzahl Series stimmt nicht überein → fallback auf replace_data
        from pptx.chart.data import CategoryChartData
        cd = CategoryChartData()
        cd.categories = categories
        for name, vals in series_data:
            cd.add_series(name, vals)
        chart.replace_data(cd)
        return

    for ser_elem, (series_name, values) in zip(ser_elements, series_data):
        # Series-Name (c:tx//c:v) setzen
        tx_v = ser_elem.find(".//c:tx//c:v", ns)
        if tx_v is not None:
            tx_v.text = series_name
        # Categories (c:cat//c:pt/c:v) und Values (c:val//c:pt/c:v) updaten
        cat_pts = ser_elem.findall(".//c:cat//c:pt/c:v", ns)
        val_pts = ser_elem.findall(".//c:val//c:pt/c:v", ns)
        for i, cat in enumerate(categories):
            if i < len(cat_pts):
                cat_pts[i].text = str(cat)
        for i, val in enumerate(values):
            if i < len(val_pts):
                try:
                    val_pts[i].text = f"{float(val):.6f}"
                except (TypeError, ValueError):
                    val_pts[i].text = "0"
        # ptCount aktualisieren (falls vorhanden)
        for tag in ("cat", "val"):
            pt_count = ser_elem.find(f".//c:{tag}//c:ptCount", ns)
            if pt_count is not None:
                pt_count.set("val", str(len(values) if tag == "val" else len(categories)))


# ─────────────────────────────────────────────────────────────────────────
# Performance-Berechnungs-Funktionen (Duplikate aus streamlit_app.py)
# Werden hier dupliziert, damit pptx_export.py unabhängig vom Streamlit-Code
# ist. Wenn die Funktionen in streamlit_app.py angepasst werden, müssen sie
# hier nachgezogen werden.
# ─────────────────────────────────────────────────────────────────────────
import numpy as _np

def _annual_fee_to_daily_drag(fee_pa_decimal):
    return (1.0 + fee_pa_decimal) ** (1 / 365) - 1


def _make_index_from_returns(d_returns_decimal, startwert=100.0):
    idx = _np.empty(len(d_returns_decimal) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(d_returns_decimal, start=1):
        idx[i] = idx[i-1] * (1.0 + d)
    return idx


def _make_index_after_fee(d_returns_decimal, fee_pa_decimal, startwert=100.0):
    e = _annual_fee_to_daily_drag(fee_pa_decimal)
    idx = _np.empty(len(d_returns_decimal) + 1, dtype=float)
    idx[0] = startwert
    for i, d in enumerate(d_returns_decimal, start=1):
        idx[i] = idx[i-1] * (1.0 + (d - e))
    return idx


def _calc_daily_returns_after_fee(d_returns_decimal, fee_pa_decimal):
    return d_returns_decimal - _annual_fee_to_daily_drag(fee_pa_decimal)


def _calc_cagr(idx_after, n_days):
    if n_days <= 0 or idx_after[0] == 0:
        return None
    return (idx_after[-1] / idx_after[0]) ** (365.0 / n_days) - 1.0


def _calc_vola(daily_returns_after_fee):
    if len(daily_returns_after_fee) < 2:
        return None
    return float(_np.std(daily_returns_after_fee, ddof=1) * _np.sqrt(365))


def _drawdown_from_index(idx):
    peak = _np.maximum.accumulate(idx)
    return (idx / peak) - 1.0


def _calc_max_drawdown(idx_after):
    dd = _drawdown_from_index(idx_after)
    return float(_np.min(dd))


def _calc_sharpe_excess(daily_returns_after_fee, rf_annual_series):
    """Sharpe Ratio nach Sharpe (1994), tägliche Excess Returns."""
    rp = pd.Series(daily_returns_after_fee).to_numpy(dtype=float)
    if rp.size < 2:
        return None
    rf_ser = pd.Series(rf_annual_series).reset_index(drop=True)
    if len(rf_ser) != len(rp):
        if len(rf_ser) > len(rp):
            rf_ser = rf_ser.iloc[:len(rp)]
        else:
            rf_ser = rf_ser.reindex(range(len(rp)))
    rf_ann = rf_ser.fillna(0.0).to_numpy(dtype=float)
    daily_rf = (1.0 + rf_ann) ** (1.0/365.0) - 1.0
    mask = ~_np.isnan(rp)
    if mask.sum() < 2:
        return None
    excess = rp[mask] - daily_rf[mask]
    mu = float(_np.mean(excess))
    sd = float(_np.std(excess, ddof=1))
    if sd == 0:
        return None
    return (mu / sd) * _np.sqrt(365.0)


def _calc_period_return(returns):
    return float(_np.prod(1.0 + returns) - 1.0)


def _calc_period_return_after_fee(returns, fee_pa_decimal):
    e = _annual_fee_to_daily_drag(fee_pa_decimal)
    return float(_np.prod(1.0 + (returns - e)) - 1.0)


def compute_performance_data(timeseries_df: pd.DataFrame, fee_dec: float,
                             n_years_bar_chart: int = 5) -> dict:
    """
    Berechnet alle Performance-Daten für die Performance-Folie (Slide 8).

    Diese Funktion ist seit Juni 2026 ein Wrapper — die eigentliche Berechnungs-Logik
    lebt jetzt zentral in `modules/analytics.py` und wird auch vom Streamlit-Performance-Tab
    genutzt. So gibt es nur EINE Stelle für die Mathematik.

    Args:
        timeseries_df: DataFrame mit Spalten 'ret_port', 'ret_bm', 'rf'. Index = Datum.
        fee_dec: Honorarsatz p.a. als Dezimal (z.B. 0.01023 für 1,023% inkl. MwSt).
        n_years_bar_chart: Anzahl Jahre für Säulen-Chart (Default: 5).

    Returns: Dict mit Keys 'kennzahlen', 'performance_pa', 'wertentwicklung'.
             Siehe modules/analytics.py für Details.
    """
    # Lazy import: bricht modules/analytics.py weg, schlägt erst hier auf.
    from modules.analytics import compute_performance_data as _ac
    return _ac(timeseries_df, fee_dec, n_years_bar_chart)


def _remove_empty_table_rows(table):
    """
    Entfernt leere Daten-Zeilen aus der Tabelle. Header und gefüllte Zeilen bleiben.

    Eine Zeile gilt als 'leer' wenn alle relevanten Daten-Spalten leer sind
    (WERTPAPIER, KUPON, FÄLLIGKEIT, WKN, ANTEIL, RATING).

    Wird nach _fill_table_with_positions aufgerufen um die hässlichen Striche
    unterhalb der echten Positionen zu eliminieren. Die Summenzeile bleibt
    erhalten wenn sie befüllt ist (enthält "100,00%"), sonst wird auch sie
    entfernt.

    WICHTIG: Anschließend muss _fit_shape_to_table aufgerufen werden, damit
    die Tabellen-Shape-Höhe an die jetzt geringere Zeilenanzahl angepasst wird
    (sonst stretcht LibreOffice die verbleibenden Zeilen).
    """
    n_rows = len(table.rows)
    if n_rows <= 1:
        return

    indices_to_remove = []
    for i in range(1, n_rows):  # Header (Zeile 0) immer behalten
        row = table.rows[i]
        is_empty = True
        for col_idx in [COL_WERTPAPIER, COL_KUPON, COL_FAELLIGKEIT, COL_WKN, COL_ANTEIL, COL_RATING]:
            text = row.cells[col_idx].text_frame.text.strip()
            # NBSP wird auch als leer betrachtet
            if text and text != "\u00a0":
                is_empty = False
                break
        if is_empty:
            indices_to_remove.append(i)

    if not indices_to_remove:
        return

    # Aus dem XML entfernen — rückwärts, damit Indizes vorderer Zeilen stabil bleiben
    from pptx.oxml.ns import qn
    tbl_elem = table._tbl
    tr_elements = tbl_elem.findall(qn('a:tr'))

    for idx in sorted(indices_to_remove, reverse=True):
        tr_to_remove = tr_elements[idx]
        tbl_elem.remove(tr_to_remove)


def _fit_shape_to_table(table_shape):
    """
    Passt die Höhe der Tabellen-Shape an die Summe der Zeilenhöhen an.
    
    Das ist WICHTIG weil LibreOffice/PowerPoint die Zeilen automatisch vergrößern,
    wenn die Summe aller Zeilenhöhen kleiner ist als die Shape-Höhe. Wenn wir die
    Shape auf die korrekte Größe setzen, bleiben die Zeilen in ihrer ursprünglichen
    Höhe (0.142") und die Tabelle ragt nicht über den Footer.
    """
    table = table_shape.table
    # Summe aller Zeilenhöhen berechnen
    total_row_h = sum(row.height for row in table.rows)
    
    # Shape-Höhe auf diese Summe setzen (+ kleiner Puffer für Rahmen)
    # 0.02" (~50000 EMU) Puffer
    table_shape.height = total_row_h + 50000


def _adjust_table_shape_height(prs, table_shape, n_data_rows: int, needs_summary: bool):
    """
    Passt die Höhe der Tabellen-Shape an die tatsächlich benötigte Zeilenanzahl an.
    
    Das ist WICHTIG weil LibreOffice/PowerPoint die Zeilen automatisch vergrößern,
    wenn die Summe aller Zeilenhöhen kleiner ist als die Shape-Höhe. Wenn wir die
    Shape auf die korrekte Größe setzen, bleiben die Zeilen in ihrer ursprünglichen
    Höhe (0.142").
    
    Kann die Shape auch vergrößern (nach unten), aber nur bis max. 6.60" Bottom
    (vor Footer bei 6.76").
    
    Args:
        prs: Presentation
        table_shape: Die Tabelle-Shape
        n_data_rows: Anzahl Datenzeilen die wir tatsächlich befüllen (inkl. Gruppen-Header)
        needs_summary: True wenn Summen-Zeile benötigt wird
    """
    ORIGINAL_HEADER_H = 0.236
    ORIGINAL_DATA_ROW_H = 0.142
    ORIGINAL_SUMMARY_H = 0.142
    MAX_TABLE_BOTTOM = 6.60  # inches - max. Bottom-Position (vor Footer bei 6.76")
    
    # Benötigte Höhe berechnen (Summe aller XML-Zeilenhöhen):
    # Header + (n Datenzeilen) + (ggf. Summen-Zeile)
    # Nach _optimize_table_layout sind leere Zeilen entfernt, nur noch n_filled + evtl. 1-2 Puffer
    # Wir brauchen Puffer: auch leere Zeilen bleiben als Buffer übrig
    
    n_buffer_rows = 2 if needs_summary else 0
    xml_rows_estimate = 1 + n_data_rows + n_buffer_rows + (1 if needs_summary else 0)
    
    needed_h = ORIGINAL_HEADER_H + (n_data_rows * ORIGINAL_DATA_ROW_H) + (n_buffer_rows * ORIGINAL_DATA_ROW_H)
    if needs_summary:
        needed_h += ORIGINAL_SUMMARY_H
    
    # Aktuelle Shape-Position
    shape_top_inch = table_shape.top / 914400
    shape_current_h_inch = table_shape.height / 914400
    
    # Maximal verfügbare Höhe (bis Footer-Margin)
    max_available_h = MAX_TABLE_BOTTOM - shape_top_inch
    
    # Neue Höhe: So groß wie benötigt, aber nie über max_available
    new_h_inch = min(needed_h, max_available_h)
    
    # Nur ändern wenn Änderung signifikant (>0.05" Differenz)
    if abs(new_h_inch - shape_current_h_inch) > 0.05:
        table_shape.height = int(new_h_inch * 914400)


# ---------------------------------------------------------------------------
# Slide-Befüllung – Aktuelle Portfoliozusammenstellung (Slide 9)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Slide 9: Aktuelle Portfoliozusammenstellung (Regionen + Branchen)
# ---------------------------------------------------------------------------

# Kleine Segmente unter diesem Schwellwert werden zu "Sonstige" zusammengefasst
SMALL_SEGMENT_THRESHOLD = 0.03  # 3%
# Maximal so viele Kategorien in der klassifizierten Aggregation (alle weiteren
# → "Sonstige"). Liquidität wird ggf. NACH dieser Konsolidierung angehängt,
# sodass der Ring am Ende bis zu MAX_SEGMENTS_IN_CHART+1 Segmente haben kann.
MAX_SEGMENTS_IN_CHART = 7


def _consolidate_small_segments(agg_series: pd.Series, threshold: float = SMALL_SEGMENT_THRESHOLD,
                                max_segments: int = MAX_SEGMENTS_IN_CHART) -> pd.Series:
    """
    Fasst kleine Kategorien zu "Sonstige" zusammen.
    
    Regel:
    - Alle Kategorien unter threshold werden zu "Sonstige" gruppiert
    - Wenn nach Konsolidierung noch mehr als max_segments Kategorien da sind,
      werden die kleinsten zusätzlich in Sonstige verschoben bis max_segments erreicht ist
    
    Args:
        agg_series: Pandas Series (Index = Kategorie-Name, Werte = Gewicht)
        threshold: Schwellwert für "kleine" Kategorie
        max_segments: Maximale Anzahl Segmente im Chart
    
    Returns:
        Konsolidierte Series, absteigend sortiert
    """
    agg = agg_series.sort_values(ascending=False)
    
    # Große Kategorien (≥ threshold)
    big = agg[agg >= threshold]
    small = agg[agg < threshold]
    
    # Maximale Anzahl Segmente beachten
    if len(big) > max_segments - 1:  # -1 weil wir Platz für "Sonstige" brauchen
        # Die kleinsten der "big" werden auch zu "Sonstige"
        keep = big.head(max_segments - 1)
        move_to_small = big.tail(len(big) - (max_segments - 1))
        big = keep
        small = pd.concat([small, move_to_small])
    
    # Sonstige zusammenfassen. Falls in den Daten bereits ein Eintrag
    # "Sonstige" existiert (z.B. Branche "Sonstige" aus dem Portfolio),
    # wird der kleine-Kategorien-Sammelbetrag AUFADDIERT statt überschrieben.
    if len(small) > 0:
        sonstige_sum = small.sum()
        if sonstige_sum > 0.0001:
            existing = float(big["Sonstige"]) if "Sonstige" in big.index else 0.0
            big["Sonstige"] = existing + sonstige_sum
            # Nach dem Update nochmal sortieren, damit Sonstige an der
            # richtigen Stelle der Reihenfolge landet
            big = big.sort_values(ascending=False)

    return big


def _build_ring_series(df: pd.DataFrame, dim_col: str) -> pd.Series:
    """
    Baut die Werte-Serie für einen Ring auf Slide 9 (Regionen oder Branchen).

    - Aggregiert `Gewicht` nach `dim_col` (z.B. "Region" oder "Segment")
    - Positionen ohne Eintrag in `dim_col` werden ignoriert (z.B. Liquidität
      hat typischerweise keine Region/Branche zugeordnet)
    - Konsolidiert kleine Kategorien zu "Sonstige"
    - Hängt anschließend die Summe der NICHT in der Aggregation enthaltenen
      Gewichte als Kategorie "Liquidität" an — damit der Ring auf 100%
      summiert und keine Label-Lücke am oberen Rand entsteht.
      Das greift zuverlässig auch wenn Liquidität (oder andere nicht-
      klassifizierte Positionen) in der Rohdaten keine Region/Branche haben.

    Liquidität wird nach der Konsolidierung angehängt, damit sie NICHT in
    "Sonstige" einsortiert wird, auch wenn sie unter dem 3%-Threshold liegt.
    """
    if dim_col not in df.columns or "Gewicht" not in df.columns:
        return pd.Series(dtype=float)

    # Normalisierung: leere/NaN-Strings als Platzhalter
    col = df[dim_col].astype(str).replace(["nan", "NaT", "None"], "")
    has_value = col.str.strip() != ""
    classified = df[has_value]
    unclassified_weight = float(df.loc[~has_value, "Gewicht"].sum())

    if classified.empty:
        return pd.Series(dtype=float)

    agg = classified.groupby(col[has_value])["Gewicht"].sum()
    agg = agg[agg > 0.0001]
    if agg.empty:
        return pd.Series(dtype=float)

    agg = _consolidate_small_segments(agg)

    # Liquidität / nicht-klassifiziertes Gewicht als eigenes Segment am Ende
    if unclassified_weight > 0.0001:
        agg["Liquidität"] = unclassified_weight

    return agg


def _fill_zusammenstellung_slide(prs, slide_idx: int, df: pd.DataFrame, strategy_name: str):
    """
    Befüllt Slide 9 mit 2 Ringen: Regionen (links) + Branchen/Segment (rechts).

    Kleine Kategorien (<3%) werden zu "Sonstige" zusammengefasst, maximal 8 Segmente
    werden angezeigt. Das verhindert überlappende Labels im Ring-Chart.
    Nicht-klassifizierte Positionen (typischerweise Liquidität) erscheinen als
    eigenes Segment "Liquidität", damit der Ring auf 100% summiert.
    """
    slide = prs.slides[slide_idx]

    # Titel
    title = _find_shape_by_name(slide, SHAPE_TITLE) or _find_shape_by_name(slide, SHAPE_TITLE_ALT)
    if title:
        _replace_text_in_shape(title, f"Aktuelle Portfoliozusammenstellung – {strategy_name}")

    # Defensive Vorbereitung: Gewicht muss sauberer Float sein, keine NaN, keine NaT
    df_clean = df.copy()
    if "Gewicht" in df_clean.columns:
        df_clean["Gewicht"] = pd.to_numeric(df_clean["Gewicht"], errors="coerce").fillna(0.0).astype(float)

    # Regionen (links)
    region_agg = _build_ring_series(df_clean, "Region")
    if not region_agg.empty:
        chart_left = _find_shape_by_name(slide, SHAPE_CHART_LEFT)
        if chart_left:
            _replace_chart_data(
                chart_left,
                region_agg.index.tolist(),
                [float(v) for v in region_agg.values]
            )

    # Segmente/Branchen (rechts)
    segment_agg = _build_ring_series(df_clean, "Segment")
    if not segment_agg.empty:
        chart_right = _find_shape_by_name(slide, SHAPE_CHART_RIGHT)
        if chart_right:
            _replace_chart_data(
                chart_right,
                segment_agg.index.tolist(),
                [float(v) for v in segment_agg.values]
            )


# ---------------------------------------------------------------------------
# Foliennummern dynamisch setzen
# ---------------------------------------------------------------------------
def _update_quelle_datum(prs, datum_str: str):
    """
    Aktualisiert das 'Quelle: Eigene Berechnung Stand: XX.XX.XXXX' Datum in allen
    Chart-Annotationen (drawing*.xml parts) auf das aktuelle Auswertungsdatum.

    Die Quelle-Zeile steht statisch in den drawing-Parts der Vorlage (im Chart-
    Annotation-Layer der Ring-Charts). Diese können nicht über die normale
    python-pptx-Slide-API erreicht werden — wir müssen über prs.part.package
    iterieren und direkt das _blob setzen.

    Args:
        prs: Presentation-Objekt
        datum_str: Datum im Format 'DD.MM.YYYY' (z.B. '17.06.2026')
    """
    if not datum_str:
        return
    package = prs.part.package
    for part in package.iter_parts():
        pn = str(part.partname)
        if not pn.startswith("/ppt/drawings/drawing"):
            continue
        try:
            xml = part.blob.decode('utf-8')
        except Exception:
            continue
        if 'Quelle: Eigene Berechnung Stand:' not in xml:
            continue
        new_xml = re.sub(
            r'(Quelle: Eigene Berechnung Stand: )\d{2}\.\d{2}\.\d{4}',
            f'\\g<1>{datum_str}',
            xml
        )
        if new_xml != xml:
            part._blob = new_xml.encode('utf-8')


def _update_slide_numbers(prs):
    """
    Setzt die Foliennummer auf jeder Slide auf die korrekte 1-indexed Position.

    HINTERGRUND:
    Die Vorlage hat statische Seitenzahlen (Slides 7-9 zeigen z.B. "13"-"15",
    weil der Designer eine Lücke für dynamische Folien angenommen hat). Nach
    Add/Remove/Duplicate-Operationen stimmen diese Werte nicht mehr — daher
    nach allen Slide-Manipulationen einmal alle Foliennummern auf die korrekte
    Position überschreiben.

    Slides ohne Foliennummer-Shape (Cover, Sub-Cover, Impressum) bleiben
    unverändert — das ist gewollt: solche Slides sollen keine Seitenzahl tragen.

    Sollte als LETZTER Schritt vor `prs.save()` aufgerufen werden.
    """
    for idx, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if shape.name in SHAPE_FOLIENNUMMER_NAMES and shape.has_text_frame:
                _replace_text_in_shape(shape, str(idx))
                break


# ---------------------------------------------------------------------------
# Slide entfernen (Slide 10 Währungen wird weggelassen)
# ---------------------------------------------------------------------------
def _move_slide(prs, from_idx: int, to_idx: int):
    """
    Verschiebt eine Slide innerhalb der Präsentation von from_idx zu to_idx.

    Args:
        prs: Presentation-Objekt
        from_idx: 0-basierte Position der Slide, die verschoben werden soll
        to_idx: 0-basierte Ziel-Position (vor Reordering)

    Realisiert via direkter Manipulation von <p:sldIdLst> in presentation.xml.
    """
    xml_slides = prs.slides._sldIdLst
    slides = list(xml_slides)
    if from_idx < 0 or from_idx >= len(slides):
        raise IndexError(f"_move_slide: from_idx {from_idx} out of range (max {len(slides)-1})")
    if to_idx < 0 or to_idx >= len(slides):
        raise IndexError(f"_move_slide: to_idx {to_idx} out of range (max {len(slides)-1})")
    target = slides[from_idx]
    xml_slides.remove(target)
    xml_slides.insert(to_idx, target)


def _remove_slide(prs, slide_idx: int):
    """Entfernt eine Slide an gegebener Position (0-indexed)."""
    xml_slides = prs.slides._sldIdLst
    slides_list = list(xml_slides)
    slide_elem = slides_list[slide_idx]
    rId = slide_elem.rId
    prs.part.drop_rel(rId)
    xml_slides.remove(slide_elem)


def _save_and_reload(prs) -> Presentation:
    """
    Speichert die Präsentation in Memory und lädt sie neu.
    Das räumt interne Slide-IDs auf (wichtig nach remove/duplicate Operationen).
    """
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return Presentation(buf)


# ---------------------------------------------------------------------------
# Portfolioanalyse-Export (Hauptfunktion)
# ---------------------------------------------------------------------------
def _build_perf_data(performance_inputs, idx: int) -> Optional[dict]:
    """
    Helfer: Berechnet performance_data Dict aus performance_inputs[idx].

    Returns None wenn keine Daten oder ungültige Eingabe — dann zeigt die
    Performance-Folie die Vorlagen-Platzhalter.
    """
    if not performance_inputs or idx >= len(performance_inputs):
        return None
    pi = performance_inputs[idx]
    if pi is None:
        return None
    ts = pi.get("timeseries_df")
    fee = pi.get("fee_dec", 0.0)
    if ts is None or len(ts) == 0:
        return None
    try:
        return compute_performance_data(ts, fee)
    except Exception:
        return None


def generate_portfolioanalyse_pptx(
    portfolios: list,   # Liste von (display_name, df, auswertungsdatum, dur_info)
    anlagevolumen: float = 0.0,
    performance_inputs: Optional[list] = None,
) -> bytes:
    """
    Erstellt eine PPTX mit der Corporate-Vorlage und befüllt die Slides 7-9
    (bzw. 7-9 + Duplikate bei Vergleichsportfolio) mit den Portfolio-Daten.

    Slide-Layout (seit Juni 2026):
    - Slide 7: Anlagevorschlag/Strategieentwurf
    - Slide 8: Performance/Wertentwicklung
    - Slide 9: Aktuelle Portfoliozusammenstellung
    - Bei 2 Portfolios: Duplikate dieser drei Slides für Portfolio 2

    Args:
        portfolios: Liste von Tupeln (display_name, df, auswertungsdatum, duration_info)
        anlagevolumen: Aktuell nicht verwendet, ggf. für Zukunftsfeatures
        performance_inputs: Optional Liste mit Performance-Daten (eine Dict pro Portfolio
                            in gleicher Reihenfolge wie `portfolios`). Format pro Eintrag:
                            {
                                "timeseries_df": pd.DataFrame,  # ret_port, ret_bm, rf
                                "fee_dec": 0.01023,             # effektiver Honorar inkl MwSt
                            }
                            Wenn None oder ein Eintrag None ist: Slide 8 zeigt die
                            Vorlagen-Platzhalter (nur Titel wird gesetzt).

    Returns:
        PPTX-Bytes
    """
    prs = _load_template()

    # ════════════════════════════════════════════════════════════════════════
    # NEUER SLIDE-LAYOUT (Juni 2026):
    #   Slide 7 = Anlagevorschlag/Strategieentwurf (Index 6)
    #   Slide 8 = Performance/Wertentwicklung (Index 7)     ← NEU (war Slide 10)
    #   Slide 9 = Aktuelle Portfoliozusammenstellung (Index 8)
    # ════════════════════════════════════════════════════════════════════════
    # Vorlage v5 hat 25 Slides mit dieser Original-Reihenfolge:
    #   Index 6: Slide 7  (Anlagevorschlag)
    #   Index 7: Slide 8  (Anlagevorschlag-Teil-2)  ← wird ENTFERNT
    #   Index 8: Slide 9  (Portfoliozusammenstellung)
    #   Index 9: Slide 10 (Performance/Wertentwicklung) ← wird zur NEUEN Slide 8
    #   Index 10: Slide 11 (Währungen)  ← wird ENTFERNT
    #
    # Operationen (in dieser Reihenfolge):
    #   1. Index 7 entfernen (alte Anlagevorschlag-Teil-2)
    #      → Performance rutscht von Index 9 → 8, Währungen von 10 → 9
    #   2. Index 9 entfernen (Währungen)
    #      → Reihenfolge: 6=Anlagevorschlag, 7=Portfolio, 8=Performance
    #   3. Move Index 8 (Performance) → Index 7 (vor Portfolio)
    #      → Endreihenfolge: 6=Anlagevorschlag, 7=Performance, 8=Portfolio
    _remove_slide(prs, 7)         # alte Anlagevorschlag-Teil-2 entfernen
    _remove_slide(prs, 9)         # Währungen entfernen (war Index 10, jetzt 9)
    _move_slide(prs, 8, 7)        # Performance vor Portfolio verschieben
    prs = _save_and_reload(prs)   # IDs aufräumen

    # Portfolio(s) befüllen
    if len(portfolios) == 1:
        # Einzelnes Portfolio:
        #   Slide 7 (Index 6) = Anlagevorschlag (mit Strategieentwurf-Titel)
        #   Slide 8 (Index 7) = Performance (mit Strategy-Name im Titel)
        #   Slide 9 (Index 8) = Portfolio-Zusammenstellung
        display_name, df, _, _ = portfolios[0]
        strategy_name = clean_strategy_name(display_name)
        perf_data = _build_perf_data(performance_inputs, 0)
        _fill_anlagevorschlag_slides(prs, 6, df, strategy_name)
        _fill_performance_slide(prs, 7, strategy_name, performance_data=perf_data)
        _fill_zusammenstellung_slide(prs, 8, df, strategy_name)

    elif len(portfolios) == 2:
        # Vergleichsportfolio: Portfolio 1 in Index 6-8, Portfolio 2 als Duplikate
        # an Index 9-11. Endreihenfolge: Anlagevorschlag, Performance, Zusammenstellung
        # pro Portfolio.
        display_name_1, df_1, _, _ = portfolios[0]
        display_name_2, df_2, _, _ = portfolios[1]
        strategy_name_1 = clean_strategy_name(display_name_1)
        strategy_name_2 = clean_strategy_name(display_name_2)
        perf_data_1 = _build_perf_data(performance_inputs, 0)
        perf_data_2 = _build_perf_data(performance_inputs, 1)

        # Schritt 1: Portfolio 1 in Original-Slides (Index 6, 7, 8)
        _fill_anlagevorschlag_slides(prs, 6, df_1, strategy_name_1)
        _fill_performance_slide(prs, 7, strategy_name_1, performance_data=perf_data_1)
        _fill_zusammenstellung_slide(prs, 8, df_1, strategy_name_1)

        # Schritt 2: Drei Duplikate von Slides 7, 8, 9 (Index 6, 7, 8) anlegen
        _duplicate_slide(prs, 6)
        _duplicate_slide(prs, 8)
        _duplicate_slide(prs, 10)

        # Schritt 3: Save/Load nach Duplikation
        prs = _save_and_reload(prs)

        # Schritt 4: Umsortieren
        xml_slides = prs.slides._sldIdLst
        slide_elements = list(xml_slides)

        new_order = list(range(6))
        new_order += [6, 8, 10]
        new_order += [7, 9, 11]
        new_order += list(range(12, len(slide_elements)))

        for elem in slide_elements:
            xml_slides.remove(elem)
        for idx in new_order:
            xml_slides.append(slide_elements[idx])

        # Schritt 5: Save/Load nach Reorder
        prs = _save_and_reload(prs)

        # Schritt 6: Portfolio 2 in Duplikate (Index 9, 10, 11)
        _fill_anlagevorschlag_slides(prs, 9, df_2, strategy_name_2)
        _fill_performance_slide(prs, 10, strategy_name_2, performance_data=perf_data_2)
        _fill_zusammenstellung_slide(prs, 11, df_2, strategy_name_2)

    else:
        raise ValueError(f"Erwarte 1 oder 2 Portfolios, erhalten: {len(portfolios)}")

    # Quelle-Datum aktualisieren auf das Auswertungsdatum des ersten Portfolios.
    # Steht statisch in den Chart-Annotationen (drawing*.xml) der Vorlage als
    # "Quelle: Eigene Berechnung Stand: 12.02.2026" — muss auf das echte
    # Auswertungsdatum aktualisiert werden.
    if portfolios and portfolios[0][2] is not None:
        datum_obj = portfolios[0][2]
        try:
            if hasattr(datum_obj, 'strftime'):
                datum_str = datum_obj.strftime("%d.%m.%Y")
                _update_quelle_datum(prs, datum_str)
        except Exception:
            pass

    # Foliennummern dynamisch setzen (NACH allen Add/Remove/Duplicate-Operationen,
    # VOR dem Speichern). Korrigiert die statischen Werte aus der Vorlage
    # (Slide 7 hat z.B. "13", soll aber "7" sein nach Renumber).
    _update_slide_numbers(prs)

    # Speichern
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()
