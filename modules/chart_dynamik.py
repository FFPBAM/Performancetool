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
    from lxml import etree
    ax = root.find(".//" + _q("dateAx"))
    if ax is None:
        return None
    scaling = ax.find(_q("scaling"))
    for tag, val in (("max", hi), ("min", lo)):   # max VOR min (Schema-Reihenfolge)
        el = scaling.find(_q(tag))
        if el is None:
            el = etree.SubElement(scaling, _q(tag))
        el.set("val", str(int(val)))
    # majorTimeUnit an die Zeitspanne anpassen: bei langen Historien Jahres-
    # statt Monatsticks (sonst hunderte Gitterlinien).
    spanne_jahre = (hi - lo) / 365.0
    mtu = ax.find(_q("majorTimeUnit"))
    if mtu is not None:
        mtu.set("val", "years" if spanne_jahre > 5 else "months")

    # ── Y-ACHSE (valAx) datenbasiert skalieren ──────────────────────────────
    # Feste Vorlagen-Grenzen (z.B. 0.8-1.4) schneiden stark gestiegene
    # Strategien (Offensiv: Index bis 2.8) oben ab → halber Chart leer.
    yvals = [float(v.text) for v in root.find(".//" + _q("val")).iter(_q("v")) if v.text]
    if yvals:
        import math as _m
        dmin, dmax = min(yvals), max(yvals)
        ymin = _m.floor(dmin * 10) / 10.0          # z.B. 0.897 -> 0.8
        ymax = _m.ceil(dmax * 10) / 10.0           # z.B. 2.872 -> 2.9
        vax = root.find(".//" + _q("valAx"))
        if vax is not None:
            vsc = vax.find(_q("scaling"))
            for tag, val in (("max", ymax), ("min", ymin)):
                el = vsc.find(_q(tag))
                if el is None:
                    el = etree.SubElement(vsc, _q(tag))
                el.set("val", f"{val:.2f}")
    return (lo, hi)


def ring_labels_aussen_dynamisch(chart, frame_w_in, frame_h_in,
                                 gap_in=0.25, min_gap_deg=24.0, rand_in=0.12):
    """Platziert die Ring-Datenlabels GEOMETRISCH exakt außerhalb des Rings.

    Liest die echte Ring-Geometrie aus dem plotArea-Layout des Charts
    (Mittelpunkt, Außenradius) und setzt jedes Label an eine berechnete
    Zielposition knapp außerhalb (gap_in Zoll). Der manualLayout-Offset wird
    als (Ziel − PP-Default) berechnet, wobei der Default (Band-Mitte) aus der
    holeSize abgeleitet wird — dadurch landet das Label in PowerPoint exakt
    am Ziel, unabhängig davon wie dünn der Ring ist.

    Selbstkalibrierend pro Chart: funktioniert für jede Segmentzahl und jede
    Plot-Größe (die drei Themen-Ringe haben unterschiedlich große Plots!).
    Zu dicht stehende Labels werden über einen Mindest-Winkelabstand
    (min_gap_deg) auseinandergespreizt → keine Überlappung.

    frame_w_in / frame_h_in = Breite/Höhe des Chart-Rahmens in Zoll
    (aus dem Shape; in nachbearbeiten() automatisch übergeben).
    """
    root = _root(chart)
    # 1) plotArea inner-Rechteck (Bruchteile des Rahmens)
    pa = root.find(".//" + _q("plotArea") + "/" + _q("layout") + "/" + _q("manualLayout"))
    if pa is None:
        return None
    def _g(tag):
        e = pa.find(_q(tag)); return float(e.get("val")) if e is not None else None
    px, py, pw, ph = _g("x"), _g("y"), _g("w"), _g("h")
    if None in (px, py, pw, ph):
        return None
    # 2) Ring-Geometrie in Zoll
    left, right = px * frame_w_in, (px + pw) * frame_w_in
    top, bot = py * frame_h_in, (py + ph) * frame_h_in
    cx, cy = (left + right) / 2.0, (top + bot) / 2.0
    R_out = min(right - left, bot - top) / 2.0
    hs_el = root.find(".//" + _q("holeSize"))
    hole = float(hs_el.get("val")) / 100.0 if hs_el is not None else 0.5
    band_center = R_out * (1 + hole) / 2.0     # PP-Default-Radius der Labels
    R_target = R_out + gap_in                  # knapp außerhalb
    # 3) Segment-Mittelwinkel (Grad, im Uhrzeigersinn ab 12 Uhr)
    val_block = root.find(".//" + _q("val"))
    if val_block is None:
        return None
    vals = [float(v.text) for v in val_block.iter(_q("v")) if v.text]
    total = sum(vals) or 1.0
    fsa_el = root.find(".//" + _q("firstSliceAng"))
    fsa = float(fsa_el.get("val")) if fsa_el is not None else 0.0
    mids, kum = [], 0.0
    for v in vals:
        f = v / total; mids.append(fsa + (kum + f / 2) * 360); kum += f
    # 4) Label-Winkel mit Mindest-Winkelabstand spreizen (gegen Überlappung)
    order = sorted(range(len(mids)), key=lambda i: mids[i] % 360)
    ang = [mids[i] % 360 for i in order]
    for _ in range(200):
        bewegt = False
        for k in range(len(ang)):
            k2 = (k + 1) % len(ang)
            gap = (ang[k2] - ang[k]) % 360
            if 0 < gap < min_gap_deg:
                push = (min_gap_deg - gap) / 2
                ang[k] = (ang[k] - push) % 360
                ang[k2] = (ang[k2] + push) % 360
                bewegt = True
        if not bewegt:
            break
    label_ang = [0.0] * len(mids)
    for si, i in enumerate(order):
        label_ang[i] = ang[si]
    # 5) Zielpositionen (absolut, in Zoll) berechnen — mit Rand-Begrenzung,
    #    damit große Ringe nicht abgeschnitten werden.
    ziel = []
    for i in range(len(mids)):
        la = math.radians(label_ang[i])
        sx, sy = math.sin(la), -math.cos(la)
        r_use = R_target
        if sx > 1e-6:    r_use = min(r_use, (frame_w_in - rand_in - cx) / sx)
        elif sx < -1e-6: r_use = min(r_use, (rand_in - cx) / sx)
        if sy > 1e-6:    r_use = min(r_use, (frame_h_in - rand_in - cy) / sy)
        elif sy < -1e-6: r_use = min(r_use, (rand_in - cy) / sy)
        r_use = max(r_use, R_out + 0.05)      # nie innerhalb des Rings
        ziel.append([cx + r_use * sx, cy + r_use * sy])

    # 6) ADAPTIVE Überlappungs-Auflösung im ABSOLUTEN Raum — garantiert, dass
    #    sich keine zwei Zahlen überlappen, egal wie die Segmente verteilt
    #    sind. Zu dicht stehende Labels werden vertikal auseinandergedrängt
    #    (Zahlen sind waagerechter Text → Überlappung ist v.a. vertikal),
    #    dabei im Rahmen gehalten. min_v/min_h ≈ halbe Label-Höhe/-Breite.
    min_v, min_h = 0.205, 0.60
    for _ in range(120):
        bewegt = False
        reihenfolge = sorted(range(len(ziel)), key=lambda i: ziel[i][1])
        for a in range(len(reihenfolge)):
            for b in range(a + 1, len(reihenfolge)):
                i, j = reihenfolge[a], reihenfolge[b]
                if abs(ziel[i][1] - ziel[j][1]) < min_v and abs(ziel[i][0] - ziel[j][0]) < min_h:
                    schub = (min_v - abs(ziel[i][1] - ziel[j][1])) / 2.0 + 0.005
                    hoch, runter = (i, j) if ziel[i][1] <= ziel[j][1] else (j, i)
                    ziel[hoch][1] = max(rand_in, ziel[hoch][1] - schub)
                    ziel[runter][1] = min(frame_h_in - rand_in, ziel[runter][1] + schub)
                    bewegt = True
        if not bewegt:
            break

    # 7) Offsets schreiben (Nullpunkt = Ring-Band-Mitte des Segments; so
    #    rechnet PowerPoint den manualLayout-Offset bei vorhandenem
    #    manualLayout — empirisch bestätigt).
    from lxml import etree
    dlbls = {int(d.find(_q("idx")).get("val")): d
             for d in root.iter(_q("dLbl")) if d.find(_q("idx")) is not None}
    for i in range(len(mids)):
        md = math.radians(mids[i])
        tx, ty = ziel[i]
        dx, dy = cx + band_center * math.sin(md), cy - band_center * math.cos(md)
        ox, oy = (tx - dx) / frame_w_in, (ty - dy) / frame_h_in
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
            e = ml.find(_q(tag))
            if e is None:
                e = etree.SubElement(ml, _q(tag))
            e.set("val", f"{val:.4f}")
    # überzählige Label-Slots (idx >= Segmentzahl) entfernen
    for idx, d in dlbls.items():
        if idx >= len(vals):
            d.getparent().remove(d)
    return {"segmente": len(vals), "R_out": round(R_out, 3), "R_target": round(R_target, 3)}


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


def nachbearbeiten(prs, hole_size=79, label_gap_in=0.25):
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
                    # Rahmenmaße in Zoll (EMU/914400) für die geometrische
                    # Label-Platzierung.
                    _fw = shape.width / 914400.0
                    _fh = shape.height / 914400.0
                    ring_labels_aussen_dynamisch(chart, _fw, _fh, gap_in=label_gap_in)
                    stat["ringe"] += 1
                elif "LINE" in typ and _hat_dateax(chart):
                    datumsachse_an_daten(chart)
                    stat["linien"] += 1
            except Exception:
                # Ein einzelnes problematisches Chart darf den Export nie
                # abbrechen — schlimmstenfalls bleibt dieses Chart wie gehabt.
                pass
    return stat
