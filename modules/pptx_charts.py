"""
modules/pptx_charts.py — Chart-Manipulation für PPTX-Vorlagen.

Pure Chart-Mechanik OHNE Domain-Wissen. Wird von der Broschüre genutzt,
um Vorlagen-Charts (Ring-Diagramme, Säulen-Charts, Linien-Charts) mit
echten Daten zu befüllen.

Was hier hingehört:
- XML-basierte Chart-Datenersetzung (robust gegen externe Excel-Referenzen)
- Der python-pptx `chart.replace_data()` Bug-Workaround (4 Bugs!)
- Format-Code-Wiederherstellung für Daten-Labels UND Achsen

Was hier NICHT hingehört:
- Konkrete Charts der Performance-/Anlagevorschlag-/Portfolio-Folie (→ pptx_slides.py)
- Slide-Manipulation (→ pptx_helpers.py)

Diese Datei hat KEINE Imports von Streamlit oder pptx_export.
Sie kann unverändert in lokalen Python-Skripten genutzt werden.

═══════════════════════════════════════════════════════════════════════════
WICHTIG: python-pptx `chart.replace_data()` ist VERSEUCHT
═══════════════════════════════════════════════════════════════════════════
Bei Charts mit embedded Excel-Workbook (Standard bei Vorlagen-Charts aus
PowerPoint) treten Bugs auf, die das PPTX beim Öffnen "reparieren" lassen
(oder Format-Codes ruinieren):

Bug 1: Embedded Excel wird NICHT aktualisiert → Diskrepanz → Reparieren-Dialog.
       Fix: <c:externalData> Element entfernen.

Bug 2: `style*.xml` der Chart wird mit ZIP-Header überschrieben (Binärmüll
       statt XML) → Reparieren-Dialog.
       Fix: Style/Color-Parts vor replace_data sichern, danach wiederherstellen.

Bug 3: Format-Codes der Daten-Labels werden auf "General" zurückgesetzt
       → 0.05 zeigt sich als "0.05" statt "5,00%".
       Fix: Format-Code via <c:numFmt> in <c:dLbls> wiederherstellen.

Bug 4 (Juni 2026, neu entdeckt): Format-Code der ACHSE (nicht nur der
       Daten-Labels!) wird ebenfalls auf "General"/sourceLinked=1
       zurückgesetzt — UNABHÄNGIG von Bug 3. Effekt: Daten-Labels zeigen
       korrekt "27,63%", die Achsen-Beschriftung daneben aber Rohwerte wie
       "0.25" statt "25%". Bewiesen an echter kaputter Chart-XML (Slide 8,
       Performance-p.a.-Säulen-Chart): <c:valAx><c:numFmt
       formatCode="General" sourceLinked="1"/>, während der danebenliegende
       (korrekt aussehende) Linien-Chart formatCode="0%" sourceLinked="0"
       hatte. Fix: Format-Code via <c:numFmt> in <c:valAx>/<c:catAx>
       wiederherstellen (restore_axis_number_format).

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
                            data_label_format: Optional[str] = None,
                            value_axis_format: Optional[str] = None,
                            category_axis_format: Optional[str] = None):
    """Ersetzt Chart-Daten — Workaround für die python-pptx Bugs (siehe Modul-Docstring).

    Bug 1: `chart.replace_data()` updated das embedded Excel-Workbook NICHT
        → PowerPoint-Reparieren-Dialog.
        Fix: <c:externalData>-Element entfernen, sodass PowerPoint nur die
        Chart-XML nutzt.

    Bug 2: `chart.replace_data()` überschreibt `style*.xml` mit ZIP-Header
        (Binärmüll) → Reparieren-Dialog.
        Fix: Style/Color-Parts der Chart vor replace_data sichern, danach
        wiederherstellen.

    Bug 3: `chart.replace_data()` setzt Format-Codes der DATEN-LABELS auf
        "General" zurück → Daten-Labels zeigen 0.05 statt 5,00%.
        Fix: Format-Code via <c:numFmt> in <c:dLbls> wiederherstellen.

    Bug 4 (Juni 2026): `chart.replace_data()` kann UNABHÄNGIG davon auch das
        Format-Code der ACHSE zurücksetzen → Achsen-Beschriftung zeigt 0.25
        statt 25%, obwohl die Daten-Labels korrekt sind.
        Fix: Format-Code via <c:numFmt> in <c:valAx>/<c:catAx> wiederherstellen.

    Args:
        chart_shape: Chart-Shape mit has_chart=True
        categories: Liste der Kategorien (Strings oder Datumangaben)
        series_data: Liste von (series_name, values) Tupeln
        data_label_format: Format-Code für Daten-Labels (z.B. "0.00%").
            None = Format-Codes nicht ändern.
        value_axis_format: Format-Code für die Werteachse (z.B. "0%").
            None = Achsen-Format nicht ändern (Default — nur explizit setzen
            wenn das Chart bekanntermaßen betroffen ist, siehe Bug 4).
        category_axis_format: Format-Code für die Kategorie-Achse.
            None = nicht ändern (seltener Bedarf, z.B. bei Datums-Achsen).
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

    # ─── BUG 3 FIX: Format-Codes der Daten-Labels wiederherstellen ───
    if data_label_format:
        restore_data_label_format(chart_shape, data_label_format)

    # ─── BUG 4 FIX: Format-Codes der Achsen wiederherstellen ───
    if value_axis_format:
        restore_axis_number_format(chart_shape, value_axis_format, axis="val")
    if category_axis_format:
        restore_axis_number_format(chart_shape, category_axis_format, axis="cat")


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


def restore_axis_number_format(chart_shape, format_code: str, axis: str = "val"):
    """Setzt den Format-Code einer Chart-Achse (NEU, Juni 2026 — Bug 4 Fix).

    Hintergrund: `chart.replace_data()` kann NICHT NUR das Format der
    Daten-Labels auf "General"/sourceLinked=1 zurücksetzen (dafür gibt es
    bereits restore_data_label_format), sondern UNABHÄNGIG davon auch das
    Format der Werteachse selbst — mit dem Effekt, dass die Daten-Labels
    korrekt "27,63%" zeigen, die Achsen-Beschriftung daneben aber Rohwerte
    wie "0.25" statt "25%". Betraf konkret den Performance-p.a.-Säulen-Chart
    (Slide 8) — bewiesen an echter, kaputter Chart-XML:
    <c:valAx><c:numFmt formatCode="General" sourceLinked="1"/>, während der
    danebenliegende (korrekt aussehende) Linien-Chart
    formatCode="0%" sourceLinked="0" hatte.

    Juli 2026: axis="cat" deckt jetzt auch <c:dateAx> ab (Datums-Achsen bei
    Linien-Charts sind technisch KEINE catAx — falls replace_data dort je
    das Format resettet, greift derselbe Restore).

    Args:
        chart_shape: Das Chart-Shape
        format_code: Format-Code für die Achse (z.B. "0%")
        axis: "val" für Werteachse (c:valAx, Default), "cat" für
            Kategorie-Achse (c:catAx und c:dateAx)
    """
    chart_xml = chart_shape.chart._chartSpace
    tags = ["valAx"] if axis == "val" else ["catAx", "dateAx"]
    for tag in tags:
        for ax_elem in chart_xml.findall(f".//c:{tag}", NS_CHART):
            num_fmt = ax_elem.find("c:numFmt", NS_CHART)
            if num_fmt is None:
                num_fmt = etree.SubElement(ax_elem, f"{{{_CHART_NS_URI}}}numFmt")
                # numFmt muss laut OOXML-Schema direkt nach c:axPos stehen
                # (vor c:majorGridlines/c:title/... ), sonst PowerPoint-Reparieren-Dialog.
                axpos = ax_elem.find("c:axPos", NS_CHART)
                if axpos is not None:
                    axpos.addnext(num_fmt)
            num_fmt.set("formatCode", format_code)
            num_fmt.set("sourceLinked", "0")


def set_value_axis_min_auto(chart_shape):
    """Entfernt eine fixe Untergrenze (<c:min>) der Werteachse → Auto-Skalierung.

    ACHTUNG (Erkenntnis 02.07.2026): Auto-Skalierung ist bei Linien-Charts
    RENDERER-ABHÄNGIG — PowerPoint wählt bei Indizes, die weit über 100%
    laufen (z.B. 100%→500%), als Auto-Minimum gerne 0% und staucht damit die
    Kurve. Für deterministisches Verhalten stattdessen set_value_axis_min()
    mit datenbasiertem Wert nutzen. Diese Funktion bleibt für Fälle erhalten,
    in denen echtes Auto gewünscht ist.

    Idempotent: kein <c:min> vorhanden → no-op. <c:max> bleibt unangetastet.
    """
    chart_xml = chart_shape.chart._chartSpace
    for ax_elem in chart_xml.findall(".//c:valAx", NS_CHART):
        scaling = ax_elem.find("c:scaling", NS_CHART)
        if scaling is None:
            continue
        mn = scaling.find("c:min", NS_CHART)
        if mn is not None:
            scaling.remove(mn)


def set_value_axis_min(chart_shape, min_value: float):
    """Setzt eine EXPLIZITE Untergrenze der Werteachse (NEU 02.07.2026).

    Hintergrund: Die Linien-Charts der Broschüre zeigen Indizes (Start 1.0).
    Eine im Template hartcodierte Untergrenze (70%) passt nicht für alle
    Strategien; PowerPoint-Auto wählt bei großen Spannen dagegen oft 0% und
    staucht die Kurve. Lösung: Untergrenze DATENBASIERT setzen (Aufrufer
    berechnet z.B. Datenminimum, abgerundet auf 10%-Schritt) — identisches,
    vorhersagbares Rendering in PowerPoint UND LibreOffice.

    Args:
        chart_shape: Chart-Shape
        min_value: Achsen-Minimum als Dezimalwert (z.B. 0.8 für 80%)
    """
    chart_xml = chart_shape.chart._chartSpace
    for ax_elem in chart_xml.findall(".//c:valAx", NS_CHART):
        scaling = ax_elem.find("c:scaling", NS_CHART)
        if scaling is None:
            continue
        mn = scaling.find("c:min", NS_CHART)
        if mn is None:
            mn = etree.SubElement(scaling, f"{{{_CHART_NS_URI}}}min")
            # Schema-Reihenfolge in c:scaling: logBase?, orientation?, max?, min?
            # → min gehört ans ENDE von scaling; SubElement hängt hinten an: ok.
        mn.set("val", repr(float(min_value)))


def set_date_axis_base_unit(chart_shape, unit: str = "days"):
    """Setzt die Basis-Zeiteinheit der Datumsachse (NEU 03.07.2026).

    Hintergrund: Ein Vorlagen-Chart, das mit MONATS-Daten gebaut wurde,
    trägt <c:dateAx><c:baseTimeUnit val="months"/>. Befüllt man es mit
    TAGES-Daten, bündelt PowerPoint alle Punkte eines Monats an derselben
    Achsenposition → die Linie springt vertikal und wirkt "nicht
    kontinuierlich". TÜCKISCH: LibreOffice ignoriert baseTimeUnit
    weitgehend — im LO-Render sieht die Linie korrekt aus, der Fehler
    zeigt sich NUR in PowerPoint (bewiesen 03.07.2026 am Offensiv-Export:
    F8-Linie zerhackt, F9 mit identischen Daten aber baseTimeUnit="days"
    kontinuierlich).

    Regel: baseTimeUnit muss zur Granularität der eingefüllten Daten
    passen — bei Tagesdaten immer "days" setzen.

    Args:
        chart_shape: Chart-Shape
        unit: "days" | "months" | "years"
    """
    chart_xml = chart_shape.chart._chartSpace
    for ax_elem in chart_xml.findall(".//c:dateAx", NS_CHART):
        btu = ax_elem.find("c:baseTimeUnit", NS_CHART)
        if btu is None:
            btu = etree.SubElement(ax_elem, f"{{{_CHART_NS_URI}}}baseTimeUnit")
            # OOXML-Schema: baseTimeUnit steht nach c:lblOffset bzw. c:auto
            anchor = ax_elem.find("c:lblOffset", NS_CHART)
            if anchor is None:
                anchor = ax_elem.find("c:auto", NS_CHART)
            if anchor is not None:
                anchor.addnext(btu)
        btu.set("val", unit)


def set_series_line_width(chart_shape, width_pt: float):
    """Setzt die Linienstärke ALLER Serien eines Charts (NEU 03.07.2026).

    Anlass: Das cVV-Linien-Chart hat 0,75pt (für 211 Monatspunkte
    ausgelegt), die Performance-Folie 1,5pt — mit 6000+ Tagespunkten
    wirkt die dünne Linie unruhig und beide Folien sehen bei identischen
    Daten unterschiedlich aus. Defensive Implementierung: nur vorhandene
    <a:ln>-Elemente in ser/spPr werden angepasst (keine neuen angelegt —
    Serien ohne explizite Linie behalten das Theme-Default).

    Args:
        chart_shape: Chart-Shape
        width_pt: Linienstärke in Punkt (1 pt = 12700 EMU)
    """
    NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    chart_xml = chart_shape.chart._chartSpace
    for ser in chart_xml.findall(".//c:ser", NS_CHART):
        sppr = ser.find("c:spPr", NS_CHART)
        if sppr is None:
            continue
        ln = sppr.find(f"{{{NS_A}}}ln")
        if ln is not None:
            ln.set("w", str(int(round(width_pt * 12700))))


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


# ─────────────────────────────────────────────────────────────────────────
# Linien-Chart mit LÜCKEN und variabler Punktzahl (NEU 10.07.2026)
#
# update_chart_values_inplace() überschreibt nur VORHANDENE <c:pt>-Elemente —
# es kann weder wachsen noch schrumpfen noch Lücken lassen. Für die
# CVV-Vergleichsfolie (F19) brauchen wir beides:
#   • variable Punktzahl (Monatswerte seit 2009, wächst mit jedem Monat)
#   • LÜCKEN: Strategien mit späterem Start haben keine frühen Werte.
#     Im Chart-XML wird das über FEHLENDE <c:pt idx="…"> gelöst
#     (nicht über 0 oder leere Werte!) zusammen mit dispBlanksAs="gap".
# ─────────────────────────────────────────────────────────────────────────

_C_NS = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
_A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _cq(tag):
    return _C_NS + tag


def _numcache_neu_aufbauen(num_ref, werte_nach_idx: dict, ptcount: int,
                           format_code: str):
    """Baut den <c:numCache> eines <c:numRef> komplett neu auf.

    werte_nach_idx: {index: wert} — nur diese Indizes bekommen ein <c:pt>.
    Fehlende Indizes bleiben LEER → PowerPoint zeichnet dort nichts
    (dispBlanksAs="gap"). Das ist der Mechanismus für später startende Reihen.
    """
    from lxml import etree
    cache = num_ref.find(_cq("numCache"))
    if cache is None:
        cache = etree.SubElement(num_ref, _cq("numCache"))
    for kind in list(cache):
        cache.remove(kind)
    fc = etree.SubElement(cache, _cq("formatCode"))
    fc.text = format_code
    pc = etree.SubElement(cache, _cq("ptCount"))
    pc.set("val", str(int(ptcount)))
    for i in sorted(werte_nach_idx):
        pt = etree.SubElement(cache, _cq("pt"))
        pt.set("idx", str(int(i)))
        v = etree.SubElement(pt, _cq("v"))
        wert = werte_nach_idx[i]
        v.text = f"{float(wert):.6f}" if isinstance(wert, float) else str(wert)
    return cache


def set_line_series_sparse(chart_shape, kategorien, serien,
                           cat_format_code="m/d/yyyy",
                           val_format_code="0.00%"):
    """Schreibt Kategorien und Werte eines Linien-Charts mit Lücken.

    Args:
        kategorien: Liste der X-Werte (Excel-Seriennummern für eine dateAx).
        serien: Liste (in Reihenfolge der <c:ser> im Chart!) von
            (name_oder_None, {kategorie_index: wert}).
            name=None → Serienname der Vorlage bleibt stehen.
            Ein Index, der fehlt, erzeugt eine LÜCKE.

    Setzt zusätzlich dispBlanksAs="gap", damit PowerPoint Lücken nicht als
    Null interpretiert.

    Returns: Anzahl beschriebener Serien (0 = Chart passte nicht).
    """
    from lxml import etree
    chart = chart_shape.chart
    root = chart._chartSpace
    ser_elems = root.findall(".//" + _cq("ser"))
    if not ser_elems or len(ser_elems) != len(serien):
        return 0

    n = len(kategorien)
    kat_nach_idx = {i: k for i, k in enumerate(kategorien)}

    for ser, (name, werte) in zip(ser_elems, serien):
        if name:
            tx_v = ser.find(".//" + _cq("tx") + "//" + _cq("v"))
            if tx_v is not None:
                tx_v.text = str(name)
        cat = ser.find(_cq("cat"))
        if cat is not None:
            ref = cat.find(_cq("numRef"))          # explizit: lxml-Elemente
            if ref is not None:                    # nie per "or" testen!
                _numcache_neu_aufbauen(ref, kat_nach_idx, n, cat_format_code)
        val = ser.find(_cq("val"))
        if val is not None:
            ref = val.find(_cq("numRef"))
            if ref is not None:
                _numcache_neu_aufbauen(ref, werte, n, val_format_code)

    # Lücken als Lücken zeichnen, nicht als Null
    plot = root.find(".//" + _cq("chart"))
    if plot is not None:
        for el in plot.findall(_cq("dispBlanksAs")):
            plot.remove(el)
        dba = etree.SubElement(plot, _cq("dispBlanksAs"))
        dba.set("val", "gap")
    return len(ser_elems)


def set_series_line_colors(chart_shape, farben_nach_name: dict,
                           breite_emu: int = None):
    """Setzt die Linienfarbe je Serie NAMENSBASIERT (statt Theme-Akzent).

    Die CVV-Vorlage nutzt schemeClr accent1..5 — das sind die Office-Standard-
    farben (Blau/Orange/Grau/Gelb), nicht das Corporate Design. Farben werden
    deshalb explizit als srgbClr gesetzt.

    Serien, deren Name nicht im Dict steht, bleiben unangetastet.
    Returns: Anzahl gefärbter Serien.
    """
    from lxml import etree
    root = chart_shape.chart._chartSpace
    n = 0
    for ser in root.findall(".//" + _cq("ser")):
        tx_v = ser.find(".//" + _cq("tx") + "//" + _cq("v"))
        name = tx_v.text.strip() if (tx_v is not None and tx_v.text) else None
        farbe = farben_nach_name.get(name)
        if not farbe:
            continue
        spPr = ser.find(_cq("spPr"))
        if spPr is None:
            spPr = etree.Element(_cq("spPr"))
            tx = ser.find(_cq("tx"))
            (tx.addnext(spPr) if tx is not None else ser.insert(0, spPr))
        ln = spPr.find(_A_NS + "ln")
        if ln is None:
            ln = etree.SubElement(spPr, _A_NS + "ln")
        if breite_emu:
            ln.set("w", str(int(breite_emu)))
        # vorhandene Füllungen der Linie entfernen (schemeClr/srgbClr/noFill)
        for tag in ("noFill", "solidFill", "gradFill", "pattFill"):
            for el in ln.findall(_A_NS + tag):
                ln.remove(el)
        fill = etree.Element(_A_NS + "solidFill")
        clr = etree.SubElement(fill, _A_NS + "srgbClr")
        clr.set("val", farbe)
        ln.insert(0, fill)
        n += 1
    return n
