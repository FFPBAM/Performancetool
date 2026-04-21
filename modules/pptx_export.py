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

    Args:
        cell: Die Zelle
        text: Der neue Text
        is_bold: Wenn explizit True/False: setzt Bold-Formatierung.
                 Wenn None: behält vorherige Formatierung bei.
    """
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
            "rating": "-",  # TODO: bei Bedarf echtes Rating
        }
        groups[gruppe].append(pos)

    # Nach Gewicht absteigend sortieren innerhalb jeder Gruppe
    # WICHTIG: _safe_float stellt sicher dass alle Keys saubere floats sind
    for g in groups:
        groups[g] = sorted(groups[g], key=lambda p: _safe_float(p["gewicht"], 0.0), reverse=True)

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
    Verteilt gruppierte Positionen auf 2 Slides (Slide 7 und Slide 8).

    Logik (Variante X+):
    - Slide 7 zeigt die größte Gruppe (typischerweise AKTIEN oder RENTEN).
      → Gruppen-Header + bis zu 33 Positionen dieser Gruppe
      → Keine Summen-Zeile
    - Slide 8 zeigt:
      → OPTIONAL: Fortsetzung der größten Gruppe (wenn >33 Positionen)
        mit "FORTSETZUNG"-Header
      → Alle übrigen Gruppen (RENTEN + EDELMETALLE + LIQUIDITÄT oder was auch immer)
      → Summen-Zeile am Ende (100%)
    - Bei Portfolios mit >12 Positionen auf Slide 8 wird abgeschnitten (sehr selten
      bei Musterportfolios mit max. ~35 Titeln).

    Returns: Liste mit 2 Einträgen (je eine Slide-Definition):
        [
            {"rows": [...], "is_last_slide": False},  # Slide 7
            {"rows": [...], "is_last_slide": True},   # Slide 8 mit Summen-Zeile
        ]
    """
    # Alle Gruppen nach Gesamtgewicht absteigend
    ordered_groups = sorted(
        groups.items(),
        key=lambda kv: sum(_safe_float(p["gewicht"], 0.0) for p in kv[1]),
        reverse=True,
    )

    if not ordered_groups:
        return [
            {"rows": [], "is_last_slide": True},
            {"rows": [], "is_last_slide": True},
        ]

    # Größte Gruppe → Slide 7
    biggest_name, biggest_positions = ordered_groups[0]
    max_on_slide_7 = SLIDE_7_DATA_ROWS - 1  # -1 für Gruppen-Header

    slide_7_rows = [{"type": "group_header", "data": {"name": biggest_name}}]
    for pos in biggest_positions[:max_on_slide_7]:
        slide_7_rows.append({"type": "position", "data": pos})

    # Überlauf: Wenn die größte Gruppe mehr Positionen hat als auf Slide 7 passen,
    # kommen die restlichen auf Slide 8 unter "FORTSETZUNG {GRUPPE}"
    overflow_positions = biggest_positions[max_on_slide_7:]

    # Slide 8 aufbauen
    slide_8_rows = []

    # 1. Fortsetzung der größten Gruppe (falls nötig)
    if overflow_positions:
        slide_8_rows.append({
            "type": "group_header",
            "data": {"name": f"{biggest_name} (Fortsetzung)"}
        })
        for pos in overflow_positions:
            slide_8_rows.append({"type": "position", "data": pos})

    # 2. Alle anderen Gruppen
    for group_name, positions in ordered_groups[1:]:
        if group_name == GROUP_LIQUIDITAET:
            # Liquidität: Wert in den Gruppen-Header, keine separate Position
            total_liq = sum(_safe_float(p["gewicht"], 0.0) for p in positions)
            slide_8_rows.append({
                "type": "group_header",
                "data": {"name": group_name, "liq_value": total_liq}
            })
        else:
            slide_8_rows.append({"type": "group_header", "data": {"name": group_name}})
            for pos in positions:
                slide_8_rows.append({"type": "position", "data": pos})

    return [
        {"rows": slide_7_rows, "is_last_slide": False},
        {"rows": slide_8_rows, "is_last_slide": True},
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

    Nach dem Befüllen werden leere Zeilen (zwischen letzter Datenzeile und Summen-Zeile)
    entfernt, sodass die Tabelle in die vorgesehene Shape-Höhe passt.

    Args:
        table: Die Tabelle (shape.table)
        slide_data: {"rows": [...], "is_last_slide": bool}
        total_weight: Summe aller Gewichte (für Summen-Zeile, default 100%)
        shape_height: Höhe der Tabellen-Shape in EMU (für Maximum-Berechnung)
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

    # Ursprüngliche Zeilenhöhen merken (für spätere Skalierung)
    original_header_height = table.rows[0].height
    original_data_row_height = table.rows[1].height if n_rows_initial > 1 else 0
    original_summary_height = table.rows[summary_row_idx].height

    # Gesamthöhe der Datenzeilen (ohne Header, ohne Summen-Zeile)
    original_data_total_height = sum(
        table.rows[i].height for i in range(1, summary_row_idx)
    )

    # Anzahl der tatsächlich zu befüllenden Zeilen
    n_filled = min(len(rows), max_data_rows)

    # Zeilen befüllen
    for i, row_def in enumerate(rows):
        if i >= max_data_rows:
            break  # Kein Platz mehr

        target_row_idx = i + 1  # +1 weil Zeile 0 der Tabellen-Header ist
        row = table.rows[target_row_idx]

        if row_def["type"] == "group_header":
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

    # ── Leere Zeilen entfernen wenn möglich ──
    _optimize_table_layout(table, n_filled, is_last,
                           original_data_total_height, original_data_row_height,
                           shape_height)


def _optimize_table_layout(table, n_filled: int, is_last: bool,
                           original_data_total_height: int,
                           original_data_row_height: int,
                           shape_height: int = 0):
    """
    Optimiert die Tabellen-Darstellung nach dem Befüllen:
    - Entfernt überzählige leere Zeilen
    - Behält die Original-Zeilenhöhen bei (KEINE Skalierung!)
    - Berechnet die Maximal-Zeilenzahl so, dass die Tabelle IMMER in die
      ursprüngliche Shape-Höhe passt (auch beim Render-Verhalten von LibreOffice/
      PowerPoint, die die Zeilenhöhen oft als Minimum interpretieren).

    Args:
        table: Die Tabelle
        n_filled: Anzahl tatsächlich befüllter Datenzeilen (inkl. Gruppen-Header)
        is_last: True wenn diese Tabelle die Summen-Zeile zeigt
        original_data_total_height: Summe der Original-Höhen aller Datenzeilen
        original_data_row_height: Original-Höhe einer einzelnen Datenzeile
        shape_height: Höhe der Tabellen-Shape (für Maximum-Berechnung)
    """
    n_rows_current = len(table.rows)
    summary_idx = n_rows_current - 1
    # Datenzeilen: von 1 bis summary_idx-1 (inklusive)
    n_data_slots = summary_idx - 1

    # Wie viele leere Zeilen gibt's?
    n_empty = n_data_slots - n_filled

    if n_empty <= 0:
        return  # Tabelle voll oder überfüllt - nichts zu tun

    # ── Effective-Height-Berechnung ──
    # PowerPoint/LibreOffice interpretieren die Zeilenhöhe oft als Minimum,
    # nicht als fester Wert. Typischerweise rendern Zeilen ca. 1.6x höher
    # als angegeben. Wir rechnen defensiv damit.
    EFFECTIVE_ROW_HEIGHT_FACTOR = 1.6
    effective_row_h = original_data_row_height * EFFECTIVE_ROW_HEIGHT_FACTOR

    if shape_height > 0 and effective_row_h > 0:
        # Wieviele Datenzeilen passen maximal?
        # Header+Summe brauchen zusammen ca. 3 Zeilen-Äquivalente (defensiv)
        max_fitting_rows = int(shape_height / effective_row_h) - 3
        # Minimum: Wir behalten mindestens n_filled Zeilen
        target_n_rows = max(n_filled, min(max_fitting_rows, n_data_slots))
    else:
        # Fallback ohne shape_height: behalte n_filled + 2 Puffer
        target_n_rows = min(n_filled + 2, n_data_slots)

    # Wie viele Zeilen müssen wir entfernen?
    n_to_remove = n_data_slots - target_n_rows

    if n_to_remove <= 0:
        return

    # Leere Zeilen entfernen: von unten (direkt vor Summen-Zeile)
    # Die zu behaltenden sind Zeilen 1..target_n_rows (inkl)
    # Also die Zeilen (target_n_rows+1)..(summary_idx-1) werden entfernt
    start_remove_idx = 1 + target_n_rows  # erste zu entfernende Zeile

    tbl = table._tbl
    tr_elements = tbl.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}tr")

    rows_to_delete = []
    for i in range(start_remove_idx, start_remove_idx + n_to_remove):
        if i < len(tr_elements):
            rows_to_delete.append(tr_elements[i])

    for tr in rows_to_delete:
        tr.getparent().remove(tr)

    # Zeilenhöhen werden NICHT verändert - sie bleiben wie in der Vorlage!


# ---------------------------------------------------------------------------
# Slide-Befüllung – Anlagevorschlag (Slides 7+8)
# ---------------------------------------------------------------------------
def _fill_anlagevorschlag_slides(prs, slide_7_idx: int, slide_8_idx: int,
                                  df: pd.DataFrame, strategy_name: str):
    """
    Befüllt Slide 7 (Aktien-Seite) und Slide 8 (Renten-Fortsetzung) mit Portfolio-Daten.

    Args:
        prs: Presentation
        slide_7_idx: 0-indexed Index der ersten Anlagevorschlag-Slide
        slide_8_idx: 0-indexed Index der zweiten Anlagevorschlag-Slide
        df: DataFrame mit Positionen (Wertpapier, WKN, Gewicht, Gattung, Kupon, Fälligkeit_parsed)
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
    # Titel
    title = _find_shape_by_name(slide_7, SHAPE_TITLE_ALT) or _find_shape_by_name(slide_7, SHAPE_TITLE)
    if title:
        _replace_text_in_shape(title, f"Anlagevorschlag – {strategy_name}")
    # Ring-Chart
    chart = _find_shape_by_name(slide_7, SHAPE_CHART_ALLOCATION)
    if chart:
        _replace_chart_data(chart, alloc_labels, alloc_values)
    # Tabelle
    table_shape = _find_shape_by_name(slide_7, SHAPE_TABLE)
    if table_shape:
        _fill_table_with_positions(table_shape.table, slide_distribution[0], total_weight,
                                   shape_height=table_shape.height)

    # 4. Slide 8 befüllen
    slide_8 = prs.slides[slide_8_idx]
    # Titel
    title = _find_shape_by_name(slide_8, SHAPE_TITLE_ALT) or _find_shape_by_name(slide_8, SHAPE_TITLE)
    if title:
        _replace_text_in_shape(title, f"Anlagevorschlag – {strategy_name}")
    # Ring-Chart (identisch wie Slide 7)
    chart = _find_shape_by_name(slide_8, SHAPE_CHART_ALLOCATION)
    if chart:
        _replace_chart_data(chart, alloc_labels, alloc_values)
    # Tabelle
    table_shape = _find_shape_by_name(slide_8, SHAPE_TABLE)
    if table_shape:
        _fill_table_with_positions(table_shape.table, slide_distribution[1], total_weight,
                                   shape_height=table_shape.height)


# ---------------------------------------------------------------------------
# Slide-Befüllung – Aktuelle Portfoliozusammenstellung (Slide 9)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Slide 9: Aktuelle Portfoliozusammenstellung (Regionen + Branchen)
# ---------------------------------------------------------------------------

# Kleine Segmente unter diesem Schwellwert werden zu "Sonstige" zusammengefasst
SMALL_SEGMENT_THRESHOLD = 0.03  # 3%
# Maximal so viele Segmente im Ring-Chart (alle weiteren → "Sonstige")
MAX_SEGMENTS_IN_CHART = 8


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
    
    # Sonstige zusammenfassen
    if len(small) > 0:
        sonstige_sum = small.sum()
        if sonstige_sum > 0.0001:
            big["Sonstige"] = sonstige_sum
    
    return big


def _fill_zusammenstellung_slide(prs, slide_idx: int, df: pd.DataFrame, strategy_name: str):
    """
    Befüllt Slide 9 mit 2 Ringen: Regionen (links) + Branchen/Segment (rechts).
    
    Kleine Kategorien (<3%) werden zu "Sonstige" zusammengefasst, maximal 8 Segmente
    werden angezeigt. Das verhindert überlappende Labels im Ring-Chart.
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
    if "Region" in df_clean.columns and "Gewicht" in df_clean.columns:
        df_clean["Region"] = df_clean["Region"].astype(str).replace(["nan", "NaT", "None"], "")
        region_df = df_clean[df_clean["Region"].str.strip() != ""]
        if not region_df.empty:
            region_agg = region_df.groupby("Region")["Gewicht"].sum()
            region_agg = region_agg[region_agg > 0.0001]
            # Konsolidierung: kleine Regionen zu "Sonstige"
            region_agg = _consolidate_small_segments(region_agg)
            if not region_agg.empty:
                chart_left = _find_shape_by_name(slide, SHAPE_CHART_LEFT)
                if chart_left:
                    _replace_chart_data(
                        chart_left,
                        region_agg.index.tolist(),
                        [float(v) for v in region_agg.values]
                    )

    # Segmente/Branchen (rechts)
    if "Segment" in df_clean.columns and "Gewicht" in df_clean.columns:
        df_clean["Segment"] = df_clean["Segment"].astype(str).replace(["nan", "NaT", "None"], "")
        segment_df = df_clean[df_clean["Segment"].str.strip() != ""]
        if not segment_df.empty:
            segment_agg = segment_df.groupby("Segment")["Gewicht"].sum()
            segment_agg = segment_agg[segment_agg > 0.0001]
            # Konsolidierung: kleine Branchen zu "Sonstige"
            segment_agg = _consolidate_small_segments(segment_agg)
            if not segment_agg.empty:
                chart_right = _find_shape_by_name(slide, SHAPE_CHART_RIGHT)
                if chart_right:
                    _replace_chart_data(
                        chart_right,
                        segment_agg.index.tolist(),
                        [float(v) for v in segment_agg.values]
                    )


# ---------------------------------------------------------------------------
# Slide entfernen (Slide 10 Währungen wird weggelassen)
# ---------------------------------------------------------------------------
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
def generate_portfolioanalyse_pptx(
    portfolios: list,   # Liste von (display_name, df, auswertungsdatum, dur_info)
    anlagevolumen: float = 0.0,
) -> bytes:
    """
    Erstellt eine PPTX mit der Corporate-Vorlage und befüllt die Slides 7-9
    (bzw. 7-9 + Duplikate bei Vergleichsportfolio) mit den Portfolio-Daten.

    Struktur:
    - 1 Portfolio: Slides 1-9 (+ Slide 10 entfernt, + Slides 11-24)
    - 2 Portfolios: Slides 1-6, dann je 3 Slides pro Portfolio (= 7 Slides),
      dann Slides 11-24

    Args:
        portfolios: Liste von Tupeln (display_name, df, auswertungsdatum, duration_info)
        anlagevolumen: Aktuell nicht verwendet, ggf. für Zukunftsfeatures

    Returns:
        PPTX-Bytes
    """
    prs = _load_template()

    # Slide 10 (Währungen) entfernen - wir haben keine Währungs-Daten
    # 0-indexed: Slide 10 = Index 9
    _remove_slide(prs, 9)
    # Nach dem Entfernen: Save/Load-Zyklus um interne Slide-IDs aufzuräumen
    # (verhindert 'Duplicate name' Warnungen beim späteren Speichern)
    prs = _save_and_reload(prs)
    # Nach Reload: Slides 7, 8, 9 sind Portfolioanalyse-Slides (wie vorher)

    # Portfolio(s) befüllen
    if len(portfolios) == 1:
        # Einzelnes Portfolio: Slides 7, 8, 9 befüllen
        display_name, df, _, _ = portfolios[0]
        strategy_name = clean_strategy_name(display_name)
        _fill_anlagevorschlag_slides(prs, 6, 7, df, strategy_name)
        _fill_zusammenstellung_slide(prs, 8, df, strategy_name)

    elif len(portfolios) == 2:
        # ========================================================
        # Vergleichsportfolio: 
        # Ziel-Reihenfolge der Slides: 
        #   1-6 = Intro (statisch)
        #   7-9 = Portfolio 1 (Anlagevorschlag1, Anlagevorschlag2, Zusammenstellung)
        #   10-12 = Portfolio 2 (Duplikate, befüllt mit P2)
        #   13-25 = Honorar, Bank etc. (statisch)
        # ========================================================
        display_name_1, df_1, _, _ = portfolios[0]
        display_name_2, df_2, _, _ = portfolios[1]
        strategy_name_1 = clean_strategy_name(display_name_1)
        strategy_name_2 = clean_strategy_name(display_name_2)

        # Schritt 1: Portfolio 1 in Originale (Slides 7, 8, 9 = Index 6, 7, 8)
        _fill_anlagevorschlag_slides(prs, 6, 7, df_1, strategy_name_1)
        _fill_zusammenstellung_slide(prs, 8, df_1, strategy_name_1)

        # Schritt 2: Drei Duplikate von Slides 7, 8, 9 anlegen
        # _duplicate_slide fügt direkt hinter der Quelle ein, was die Indizes verschiebt.
        _duplicate_slide(prs, 6)   # Slide 7' an Index 7, alle weiteren +1
        _duplicate_slide(prs, 8)   # Slide 8 ist jetzt 8, Duplikat an Index 9
        _duplicate_slide(prs, 10)  # Slide 9 ist jetzt 10, Duplikat an Index 11
        # Aktuelle Reihenfolge: [0..5]=Intro, 6=S7, 7=NEW_7, 8=S8, 9=NEW_8, 10=S9, 11=NEW_9, 12..=Rest

        # Schritt 3: Save/Load-Zyklus nach Duplikation
        # (stellt sicher dass alle internen Slide-IDs konsistent sind)
        prs = _save_and_reload(prs)

        # Schritt 4: Umsortieren zu: [0..5]=Intro, 6=S7, 7=S8, 8=S9, 9=NEW_7, 10=NEW_8, 11=NEW_9, 12..=Rest
        xml_slides = prs.slides._sldIdLst
        slide_elements = list(xml_slides)

        new_order = list(range(6))        # 0..5 (Intro, unverändert)
        new_order += [6, 8, 10]           # S7, S8, S9 (P1)
        new_order += [7, 9, 11]           # NEW_7, NEW_8, NEW_9 (werden zu P2)
        new_order += list(range(12, len(slide_elements)))  # Rest

        for elem in slide_elements:
            xml_slides.remove(elem)
        for idx in new_order:
            xml_slides.append(slide_elements[idx])

        # Schritt 5: Nach Umsortierung nochmal Save/Load für saubere IDs
        prs = _save_and_reload(prs)

        # Schritt 6: Portfolio 2 in Duplikate befüllen (jetzt an Indizes 9, 10, 11)
        _fill_anlagevorschlag_slides(prs, 9, 10, df_2, strategy_name_2)
        _fill_zusammenstellung_slide(prs, 11, df_2, strategy_name_2)

    else:
        raise ValueError(f"Erwarte 1 oder 2 Portfolios, erhalten: {len(portfolios)}")

    # Speichern
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()
