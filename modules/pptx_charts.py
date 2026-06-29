"""
modules/pptx_charts.py — Chart-Manipulation für PPTX-Vorlagen.

Pure Chart-Mechanik OHNE Domain-Wissen. Wird von der Broschüre genutzt,
um Vorlagen-Charts (Ring-Diagramme, Säulen-Charts, Linien-Charts) mit
echten Daten zu befüllen.

Was hier hingehört:
- XML-basierte Chart-Datenersetzung (robust gegen externe Excel-Referenzen)
- Der python-pptx `chart.replace_data()` Bug-Workaround (3 Bugs!)
- Format-Code-Wiederherstellung für Daten-Labels

Was hier NICHT hingehört:
- Konkrete Charts der Performance-/Anlagevorschlag-/Portfolio-Folie (→ pptx_slides.py)
- Slide-Manipulation (→ pptx_helpers.py)

Diese Datei hat KEINE Imports von Streamlit oder pptx_export.
Sie kann unverändert in lokalen Python-Skripten genutzt werden.

═══════════════════════════════════════════════════════════════════════════
WICHTIG: python-pptx `chart.replace_data()` ist VERSEUCHT
═══════════════════════════════════════════════════════════════════════════
Bei Charts mit embedded Excel-Workbook (Standard bei Vorlagen-Charts aus
PowerPoint) treten drei Bugs auf, die das PPTX beim Öffnen "reparieren"
lassen (oder Format-Codes ruinieren):

Bug 1: Embedded Excel wird NICHT aktualisiert → Diskrepanz → Reparieren-Dialog.
       Fix: <c:externalData> Element entfernen.

Bug 2: `style*.xml` der Chart wird mit ZIP-Header überschrieben (Binärmüll
       statt XML) → Reparieren-Dialog.
       Fix: Style/Color-Parts vor replace_data sichern, danach wiederherstellen.

Bug 3: Format-Codes der Daten-Labels werden auf "General" zurückgesetzt
       → 0.05 zeigt sich als "0.05" statt "5,00%".
       Fix: Format-Code via <c:numFmt> wiederherstellen.

Lösung in EINER Funktion: `replace_chart_data_safe()`. Diese sollte
*immer* statt `chart.replace_data()` direkt verwendet werden.
═══════════════════════════════════════════════════════════════════════════
"""

from typing import Optional

from lxml import etree
from pptx.chart.data import CategoryChartData


# ─────────────────────────────────────────────────────────────────────────────
# XML-Namespaces
# ─────────────────────────────────────────────────────────────────────────────

NS_CHART = {
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
}
"""XML-Namespace für DrawingML Chart-Elemente."""

_CHART_NS_URI = "http://schemas.openxmlformats.org/drawingml/2006/chart"


# ─────────────────────────────────────────────────────────────────────────────
# XML-basierte Chart-Datenersetzung (für Ring-Charts ohne Bug-Workaround)
# ─────────────────────────────────────────────────────────────────────────────

def replace_chart_data(chart_shape, categories: list, values: list,
                       series_name: str = "Anteil"):
    """Ersetzt die Daten eines bestehenden Charts direkt in der Chart-XML.

    Arbeitet auf den Cache-Elementen (<c:strCache>, <c:numCache>) der Chart-XML.
    Robust gegen externe Excel-Referenzen — diese werden nicht angetastet.

    Geeignet für Ring-Diagramme mit einer einzigen Datenreihe. Für Charts mit
    mehreren Series und Daten-Labels (z.B. Säulen-Chart auf Performance-Folie)
    nutze stattdessen `replace_chart_data_safe()`.

    Args:
        chart_shape: Das Chart-Shape (shape.has_chart == True)
        categories: Liste der Kategorie-Namen (z.B. ["Aktien", "Renten"])
        values: Liste der zugehörigen Werte (z.B. [0.75, 0.17])
        series_name: Name der Datenreihe (wird in <c:tx> geschrieben falls vorhanden)

    Raises:
        ValueError: wenn len(categories) != len(values)
    """
    if len(categories) != len(values):
        raise ValueError(
            f"Kategorien ({len(categories)}) und Werte ({len(values)}) "
            f"müssen gleiche Länge haben"
        )

    chart = chart_shape.chart
    chart_xml = chart._chartSpace

    # Kategorien aktualisieren
    cat_elem = chart_xml.find('.//c:cat', NS_CHART)
    if cat_elem is not None:
        update_cache_elements(cat_elem, categories, is_numeric=False)

    # Werte aktualisieren
    val_elem = chart_xml.find('.//c:val', NS_CHART)
    if val_elem is not None:
        update_cache_elements(val_elem, values, is_numeric=True)


def update_cache_elements(parent, new_values, is_numeric: bool):
    """Updated die <c:pt>-Elemente im Cache eines <c:cat> oder <c:val> Elements.

    Fügt bei Bedarf neue Punkte hinzu oder entfernt überzählige.
    Aktualisiert auch <c:ptCount>.

    Args:
        parent: <c:cat> oder <c:val> Element
        new_values: Liste der neuen Werte
        is_numeric: True für numCache (Zahlen), False für strCache (Strings)
    """
    # Cache-Element finden (strCache oder numCache)
    if is_numeric:
        cache = parent.find('.//c:numCache', NS_CHART)
        if cache is None:
            cache = parent.find('.//c:numRef/c:numCache', NS_CHART)
    else:
        cache = parent.find('.//c:strCache', NS_CHART)
        if cache is None:
            cache = parent.find('.//c:strRef/c:strCache', NS_CHART)

    if cache is None:
        # Kein Cache vorhanden — für unseren Use-Case (Charts aus PPTX-Vorlage)
        # ist der Cache immer vorhanden. Im Edge-Case einfach no-op.
        return

    # ptCount aktualisieren
    pt_count = cache.find('c:ptCount', NS_CHART)
    if pt_count is not None:
        pt_count.set('val', str(len(new_values)))

    # Bestehende <c:pt>-Elemente entfernen
    for pt in cache.findall('c:pt', NS_CHART):
        cache.remove(pt)

    # Neue <c:pt>-Elemente hinzufügen
    for idx, val in enumerate(new_values):
        pt = etree.SubElement(cache, f'{{{_CHART_NS_URI}}}pt')
        pt.set('idx', str(idx))
        v_el = etree.SubElement(pt, f'{{{_CHART_NS_URI}}}v')
        if is_numeric:
            v_el.text = f"{float(val)}"
        else:
            v_el.text = str(val)


# ─────────────────────────────────────────────────────────────────────────────
# python-pptx `chart.replace_data()` BUG-WORKAROUND
# ─────────────────────────────────────────────────────────────────────────────

def replace_chart_data_safe(chart_shape, categories: list, series_data: list,
                            data_label_format: Optional[str] = None):
    """Ersetzt Chart-Daten — Workaround für drei python-pptx Bugs.

    Bug 1: `chart.replace_data()` updated das embedded Excel-Workbook NICHT
        → PowerPoint-Reparieren-Dialog.
        Fix: <c:externalData>-Element entfernen, sodass PowerPoint nur die
        Chart-XML nutzt.

    Bug 2: `chart.replace_data()` überschreibt `style*.xml` mit ZIP-Header
        (Binärmüll) → Reparieren-Dialog.
        Fix: Style/Color-Parts der Chart vor replace_data sichern, danach
        wiederherstellen.

    Bug 3: `chart.replace_data()` setzt Format-Codes auf "General" zurück
        → Daten-Labels zeigen 0.05 statt 5,00%.
        Fix: Format-Code via <c:numFmt> wiederherstellen.

    Args:
        chart_shape: Chart-Shape mit has_chart=True
        categories: Liste der Kategorien (Strings oder Datumangaben)
        series_data: Liste von (series_name, values) Tupeln
        data_label_format: Format-Code für Daten-Labels (z.B. "0.00%").
            None = Format-Codes nicht ändern.
    """
    chart = chart_shape.chart
    chart_part = chart.part

    # ─── BUG 2 FIX: Sichere alle "Hilfs-Parts" der Chart (style, colors) ───
    backup_parts = {}  # partname -> (part_obj, blob)
    for rel_id, rel in chart_part.rels.items():
        try:
            reltype = rel.reltype
        except Exception:
            continue
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
    chart_xml = chart._chartSpace
    ext_data = chart_xml.find(".//c:externalData", NS_CHART)
    if ext_data is not None:
        ext_data.getparent().remove(ext_data)

    # ─── BUG 3 FIX: Format-Codes wiederherstellen ───
    if data_label_format:
        restore_data_label_format(chart_shape, data_label_format)


def restore_data_label_format(chart_shape, format_code: str):
    """Setzt den Format-Code der Daten-Labels in allen Series eines Charts.

    `chart.replace_data()` setzt Format-Codes auf "General" zurück, was dazu
    führt dass z.B. der Wert 0.05 als "0.05" statt "5,00%" angezeigt wird.
    Diese Funktion stellt den ursprünglichen Format-Code wieder her, indem
    sie <c:numFmt> innerhalb von <c:dLbls> setzt.

    Args:
        chart_shape: Das Chart-Shape
        format_code: Format-Code (z.B. "0.00%", "0.0", "#,##0")
    """
    chart_xml = chart_shape.chart._chartSpace

    for ser in chart_xml.findall(".//c:ser", NS_CHART):
        # <c:dLbls> Element finden
        dlbls = ser.find("c:dLbls", NS_CHART)
        if dlbls is None:
            continue  # Keine Daten-Labels in dieser Series

        # <c:numFmt> innerhalb dLbls finden oder anlegen
        num_fmt = dlbls.find("c:numFmt", NS_CHART)
        if num_fmt is None:
            num_fmt = etree.SubElement(dlbls, f"{{{_CHART_NS_URI}}}numFmt")
            # numFmt muss am Anfang von dLbls stehen (vor anderen Properties)
            dlbls.insert(0, num_fmt)
        num_fmt.set("formatCode", format_code)
        num_fmt.set("sourceLinked", "0")


# ─────────────────────────────────────────────────────────────────────────────
# Alternative: In-place Chart-Update (behält Format-Codes erhalten)
# ─────────────────────────────────────────────────────────────────────────────

def update_chart_values_inplace(chart_shape, categories: list, series_data: list):
    """Aktualisiert Categories und Values aller Series direkt in der Chart-XML.

    Im Gegensatz zu `chart.replace_data()` bleiben die Format-Codes
    (z.B. "0.00%" für Daten-Labels) erhalten. Geeignet für Säulen-Charts wo
    die Anzahl der Series und Datenpunkte feststeht und zum Chart-Template
    passt (z.B. 5 Jahre × 2 Series für Performance p.a.).

    Falls die Anzahl der Series oder Datenpunkte NICHT zum Template passt,
    wird automatisch auf `chart.replace_data()` zurückgegriffen — aber dann
    ohne die Bug-Workarounds. Für sichere Daten-Ersetzung mit Bug-Workaround
    nutze stattdessen `replace_chart_data_safe()`.

    Args:
        chart_shape: Das Chart-Shape
        categories: Liste der Kategorien (Strings), z.B. ["2021", ..., "2025"]
        series_data: Liste von (series_name, values) Tupeln
    """
    chart = chart_shape.chart
    chart_xml = chart._chartSpace

    ser_elements = chart_xml.findall(".//c:ser", NS_CHART)
    if len(ser_elements) != len(series_data):
        # Anzahl Series stimmt nicht überein → fallback auf replace_data
        cd = CategoryChartData()
        cd.categories = categories
        for name, vals in series_data:
            cd.add_series(name, vals)
        chart.replace_data(cd)
        return

    for ser_elem, (series_name, values) in zip(ser_elements, series_data):
        # Series-Name (c:tx//c:v) setzen
        tx_v = ser_elem.find(".//c:tx//c:v", NS_CHART)
        if tx_v is not None:
            tx_v.text = series_name
        # Categories (c:cat//c:pt/c:v) und Values (c:val//c:pt/c:v) updaten
        cat_pts = ser_elem.findall(".//c:cat//c:pt/c:v", NS_CHART)
        val_pts = ser_elem.findall(".//c:val//c:pt/c:v", NS_CHART)
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
            pt_count = ser_elem.find(f".//c:{tag}//c:ptCount", NS_CHART)
            if pt_count is not None:
                pt_count.set("val", str(len(values) if tag == "val" else len(categories)))
