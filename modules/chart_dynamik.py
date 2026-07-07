# modules/chart_dynamik.py  (bzw. Funktionen in pptx_charts.py)
"""Dynamische, datenbasierte Chart-Skalierung — native PP, kein Bild.
Aufruf jeweils NACH dem Daten-Schreiben (replace_chart_data)."""
import math
import datetime as dt

_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
def _q(t): return f"{{{_C}}}{t}"


def _root(chart):
    # python-pptx: chart._chartSpace ist der lxml-Wurzelknoten des Charts
    return chart._chartSpace


def datumsachse_an_daten(chart, auf_monat_runden=True):
    """Setzt die Datums-Achse (dateAx) einer Linie auf die tatsächliche
    Datenspanne, statt fixer Vorlagengrenzen. Behebt Leerraum vor/nach der
    Kurve. auf_monat_runden = saubere Monatsticks (Monatsanfang/-anfang+1)."""
    root = _root(chart)
    cats = [float(v.text) for v in root.iter(_q("v"))
            if v.getparent().getparent().tag == _q("cat") or
               v.getparent().getparent().getparent().tag == _q("cat")]
    # robuster: Kategorien gezielt aus dem cat-Block holen
    cat_block = root.find(".//" + _q("cat"))
    if cat_block is None:
        return None
    cats = [float(v.text) for v in cat_block.iter(_q("v")) if v.text]
    if not cats:
        return None
    lo, hi = min(cats), max(cats)
    if auf_monat_runden:
        def to_d(n): return dt.date(1899, 12, 30) + dt.timedelta(days=int(n))
        def to_s(d): return (d - dt.date(1899, 12, 30)).days
        lo = to_s(to_d(lo).replace(day=1))
        d_hi = to_d(hi).replace(day=1) + dt.timedelta(days=32)
        hi = to_s(d_hi.replace(day=1))
    ax = root.find(".//" + _q("dateAx"))
    if ax is None:
        return None
    scaling = ax.find(_q("scaling"))
    from lxml import etree
    for tag, val in (("max", hi), ("min", lo)):   # max VOR min (Schema-Reihenfolge)
        el = scaling.find(_q(tag))
        if el is None:
            el = etree.SubElement(scaling, _q(tag))
        el.set("val", str(int(val)))
    return (lo, hi)


def ring_labels_aussen_dynamisch(chart, radius=0.06, aspect=1.0):
    """Positioniert die Datenlabels eines Doughnut-Rings radial außen —
    berechnet aus dem tatsächlichen Segment-Mittelwinkel, damit die Zahlen
    IMMER am richtigen Segment sitzen (unabhängig von den Anteilen).
    Zusätzlich einfache Kollisionsvermeidung: liegen zwei benachbarte Labels
    zu dicht, werden sie leicht auseinandergeschoben.
    """
    from lxml import etree
    # x_scale = H/B: manualLayout-x ist Bruchteil der BREITE, y der HÖHE.
    # Bei breiterem Rahmen (aspect>1) muss x gestaucht werden, sonst
    # schießen die seitlichen Labels zu weit raus.
    x_scale = 1.0 / aspect if aspect else 1.0
    root = _root(chart)
    val_block = root.find(".//" + _q("val"))
    if val_block is None:
        return None
    vals = [float(v.text) for v in val_block.iter(_q("v")) if v.text]
    total = sum(vals) or 1.0
    fsa_el = root.find(".//" + _q("firstSliceAng"))
    fsa = float(fsa_el.get("val")) if fsa_el is not None else 0.0

    # Mittelwinkel je Segment (Grad, im Uhrzeigersinn ab 12 Uhr)
    mids, kum = [], 0.0
    for v in vals:
        frac = v / total
        mids.append(fsa + (kum + frac / 2.0) * 360.0)
        kum += frac

    # Positionen berechnen (Offset vom Default = Segment-Mittelpunkt am Ring)
    pos = []
    for theta in mids:
        r = math.radians(theta)
        pos.append([radius * x_scale * math.sin(r), -radius * math.cos(r)])

    # ── Überlappungs-Auflösung (damit ALLE Zahlen sichtbar bleiben) ──
    # Labels sind waagerechter Text; Überlappung ist v.a. VERTIKAL. Wir
    # drängen zu dicht stehende Labels iterativ in y auseinander. min_v/min_h
    # ~ halbe Label-Höhe/-Breite als Bruchteil des Rahmens (5.24x4.55in).
    min_v, min_h = 0.052, 0.135
    for _ in range(80):
        bewegt = False
        reihenfolge = sorted(range(len(pos)), key=lambda i: pos[i][1])
        for a in range(len(reihenfolge)):
            for b in range(a + 1, len(reihenfolge)):
                i, j = reihenfolge[a], reihenfolge[b]
                dy = pos[j][1] - pos[i][1]
                dx = pos[j][0] - pos[i][0]
                if abs(dy) < min_v and abs(dx) < min_h:
                    schub = (min_v - abs(dy)) / 2.0 + 0.002
                    if pos[i][1] <= pos[j][1]:
                        pos[i][1] -= schub; pos[j][1] += schub
                    else:
                        pos[i][1] += schub; pos[j][1] -= schub
                    bewegt = True
        if not bewegt:
            break

    # Offsets begrenzen, damit KEIN Label über den Rahmenrand geschoben wird
    # (sonst schneidet PowerPoint es ab → "Label verschwindet"). Grenzen als
    # Bruchteil des Rahmens, konservativ.
    MAX_X, MAX_Y = 0.145, 0.115
    for p in pos:
        p[0] = max(-MAX_X, min(MAX_X, p[0]))
        p[1] = max(-MAX_Y, min(MAX_Y, p[1]))

    # in die dLbl schreiben (nur vorhandene idx = echte Segmente)
    dlbls = {int(d.find(_q("idx")).get("val")): d
             for d in root.iter(_q("dLbl")) if d.find(_q("idx")) is not None}
    for i, (ox, oy) in enumerate(pos):
        d = dlbls.get(i)
        if d is None:
            continue
        layout = d.find(_q("layout"))
        if layout is None:
            layout = etree.Element(_q("layout")); d.insert(1, layout)
        ml = layout.find(_q("manualLayout"))
        if ml is None:
            ml = etree.SubElement(layout, _q("manualLayout"))
        for tag, val in (("x", ox), ("y", oy)):
            el = ml.find(_q(tag))
            if el is None:
                el = etree.SubElement(ml, _q(tag))
            el.set("val", f"{val:.4f}")
    # überzählige Label-Slots (idx >= Anzahl Segmente) entfernen
    for idx, d in dlbls.items():
        if idx >= len(vals):
            d.getparent().remove(d)
    return list(zip(range(len(mids)), [round(m % 360, 1) for m in mids]))


def ring_holesize(chart, hole=79):
    """Setzt die Ring-Dicke (holeSize = Lochanteil in %). 79 ≈ dünner
    Original-Look aus dem Excel-Makro-PP (Referenz gemessen: ~77 %).
    ACHTUNG: LibreOffice IGNORIERT holeSize beim Rendern (immer ~50 %) —
    nur in echtem PowerPoint sichtbar. Der XML-Wert ist maßgeblich."""
    root = _root(chart)
    hs = root.find(".//" + _q("holeSize"))
    if hs is not None:
        hs.set("val", str(int(hole)))
        return int(hole)
    return None


def _hat_dateax(chart):
    return _root(chart).find(".//" + _q("dateAx")) is not None


def nachbearbeiten(prs, hole_size=79, ring_label_radius=0.06):
    """EINE Funktion, die alle Charts einer fertigen Präsentation
    datenbasiert nachzieht — am Ende von generate_portfolioanalyse_pptx
    aufrufen, DIREKT VOR prs.save(...).

    Pro Chart-Typ:
      • Doughnut (Ringe): holeSize=hole_size (dünner Original-Look) +
        Außen-Labels radial aus dem Segmentwinkel.
      • Linie MIT Datums-Achse (Wertentwicklung): Achse auf die echte
        Datenspanne (kein Leerraum). Balken (catAx) bleiben unberührt.

    Rührt NICHTS an der Download-Logik an — arbeitet nur an Chart-XML.
    Gibt eine kleine Statistik zurück (für optionales Logging).
    """
    stat = {"ringe": 0, "linien": 0}
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_chart", False):
                continue
            chart = shape.chart
            typ = chart.chart_type.name if chart.chart_type else ""
            try:
                if "DOUGHNUT" in typ:
                    ring_holesize(chart, hole_size)
                    # aspect = Breite/Höhe des Chart-Rahmens → korrekte x-Stauchung
                    _asp = (shape.width / shape.height) if shape.height else 1.0
                    ring_labels_aussen_dynamisch(chart, radius=ring_label_radius, aspect=_asp)
                    stat["ringe"] += 1
                elif "LINE" in typ and _hat_dateax(chart):
                    datumsachse_an_daten(chart)
                    stat["linien"] += 1
            except Exception:
                # Ein einzelnes problematisches Chart darf den Export nie
                # abbrechen — schlimmstenfalls bleibt dieses Chart wie gehabt.
                pass
    return stat
