# modules/chart_dynamik.py  (bzw. Funktionen in pptx_charts.py)
"""Dynamische, datenbasierte Chart-Skalierung — native PP, kein Bild.
Aufruf jeweils NACH dem Daten-Schreiben (replace_chart_data)."""
import math
import datetime as dt

_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
def _q(t): return f"{{{_C}}}{t}"

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


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
                                 gap_in=0.14, min_gap_deg=24.0, rand_in=0.12,
                                 tangential_in=0.14):
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

    # 2b) RING an den verfügbaren vertikalen Raum ZWISCHEN Überschrift und
    #     Legende anpassen (Größe + Lage). Die Legende sitzt bei diesen Ringen
    #     unten im Rahmen und schiebt den Ring hoch; gleichzeitig soll oben Luft
    #     zur Überschrift bleiben. Wir lesen die Legenden-Oberkante, verkleinern
    #     den Ring wenn nötig und zentrieren ihn im freien Bereich → Labels oben
    #     wie unten mit Abstand, konsistente Größe.
    legend = root.find(".//" + _q("legend"))
    leg_y = None
    if legend is not None:
        lm = legend.find(".//" + _q("manualLayout"))
        if lm is not None and lm.find(_q("y")) is not None:
            leg_y = float(lm.find(_q("y")).get("val"))
    legend_top = (leg_y * frame_h_in) if leg_y is not None else frame_h_in * 0.97
    kopf_rand = 0.15          # Luft zur Überschrift oben
    label_pad = 0.52          # vertikale Ausdehnung Label + Rand (inkl. De-overlap-Spreizung)
    R_ziel = min(R_out, 0.27 * frame_h_in)     # Grundverkleinerung großer Ringe
    # so weit verkleinern, dass Ring + Labels zwischen Kopf und Legende passen
    for _ in range(20):
        lo = kopf_rand + R_ziel + label_pad          # min. mögliche Zentrum-y
        hi = legend_top - R_ziel - label_pad         # max. mögliche Zentrum-y
        if hi >= lo:
            break
        R_ziel *= 0.94
    new_cy = min(max(frame_h_in / 2.0, lo), hi) if hi >= lo else (lo + hi) / 2.0
    if R_ziel < R_out - 1e-3 or abs(new_cy - cy) > 1e-3:
        faktor = R_ziel / R_out
        cxf = px + pw / 2.0                       # horizontales Zentrum halten
        pw2, ph2 = pw * faktor, ph * faktor
        px2 = cxf - pw2 / 2.0
        py2 = (new_cy / frame_h_in) - ph2 / 2.0   # vertikal neu setzen
        for tag, val in (("x", px2), ("y", py2), ("w", pw2), ("h", ph2)):
            e = pa.find(_q(tag))
            if e is not None:
                e.set("val", f"{val:.5f}")
        left, right = px2 * frame_w_in, (px2 + pw2) * frame_w_in
        top, bot = py2 * frame_h_in, (py2 + ph2) * frame_h_in
        cx, cy = (left + right) / 2.0, (top + bot) / 2.0
        R_out = min(right - left, bot - top) / 2.0

    hs_el = root.find(".//" + _q("holeSize"))
    hole = float(hs_el.get("val")) / 100.0 if hs_el is not None else 0.5
    band_center = R_out * (1 + hole) / 2.0     # PP-Default-Radius der Labels
    # gap_in = gewünschte SICHTBARE Freiheit zwischen Text-Innenkante und Ring.
    # Die nötige radiale Distanz der Label-MITTE hängt vom Winkel ab, weil der
    # Text waagerecht ist: seitlich ragt die halbe Breite zum Ring, oben/unten
    # nur die halbe Höhe. R_target wird deshalb pro Label in Schritt 5 berechnet.
    HALB_W, HALB_H = 0.33, 0.10                # halbe Text-Box (Zoll, ~"29,60%")
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
    #    damit große Ringe nicht abgeschnitten werden. PLUS ein tangentialer
    #    Versatz (seitlich zur Radial-Richtung), damit KEIN Label exakt auf der
    #    radialen Linie zu seinem Segment sitzt → PowerPoint zeichnet dann für
    #    JEDES Label einen Leader-Strich (auch freistehende Segmente).
    ziel = []
    for i in range(len(mids)):
        la = math.radians(label_ang[i])
        sx, sy = math.sin(la), -math.cos(la)          # radial nach außen
        tsx, tsy = math.cos(la), math.sin(la)         # tangential (im Uhrzeigersinn)
        # radiale Ausdehnung der (waagerechten) Text-Box in Blickrichtung:
        # seitlich zählt die Breite, oben/unten die Höhe.
        radial_extent = HALB_W * abs(sx) + HALB_H * abs(sy)
        r_target_i = R_out + gap_in + radial_extent    # → Innenkante = R_out+gap_in
        r_use = r_target_i
        if sx > 1e-6:    r_use = min(r_use, (frame_w_in - rand_in - cx) / sx)
        elif sx < -1e-6: r_use = min(r_use, (rand_in - cx) / sx)
        if sy > 1e-6:    r_use = min(r_use, (frame_h_in - rand_in - cy) / sy)
        elif sy < -1e-6: r_use = min(r_use, (rand_in - cy) / sy)
        r_use = max(r_use, R_out + 0.05)              # nie innerhalb des Rings
        tx = cx + r_use * sx + tangential_in * tsx
        ty = cy + r_use * sy + tangential_in * tsy
        ziel.append([tx, ty])

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

    # 6b) LEADER-GARANTIE: jedes Label muss einen Mindest-Seitenabstand
    #     (senkrecht zur radialen Linie seines Segments) haben, sonst zeichnet
    #     PowerPoint keinen Strich. Wir schieben zu radial-nahe Labels
    #     tangential weg — danach nochmal Überlappung auflösen.
    min_tang = 0.20
    for _durchlauf in range(6):
        for i in range(len(ziel)):
            md = math.radians(mids[i])
            perp_x, perp_y = math.cos(md), math.sin(md)   # senkrecht zur Radial-Richtung
            lvx, lvy = ziel[i][0] - cx, ziel[i][1] - cy
            d_perp = lvx * perp_x + lvy * perp_y
            if abs(d_perp) < min_tang:
                richtung = 1.0 if d_perp >= 0 else -1.0
                korr = (min_tang - abs(d_perp)) * richtung
                nx = ziel[i][0] + korr * perp_x
                ny = ziel[i][1] + korr * perp_y
                # im Rahmen halten
                ziel[i][0] = max(rand_in, min(frame_w_in - rand_in, nx))
                ziel[i][1] = max(rand_in, min(frame_h_in - rand_in, ny))
        # Überlappung erneut auflösen (Tangential-Schub kann welche erzeugt haben)
        for _ in range(60):
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

    # 6c) MINDEST-RING-ABSTAND: kein Label darf dem Ring zu nah kommen
    #     (die vertikale De-overlap kann Labels zum Ring drücken). Zu nahe
    #     Labels werden radial nach außen geschoben (im Rahmen gehalten).
    min_clear = 0.12
    for _ in range(4):
        for i in range(len(ziel)):
            lvx, lvy = ziel[i][0] - cx, ziel[i][1] - cy
            rad = math.hypot(lvx, lvy) or 1e-6
            pa_ang = math.atan2(lvx, -lvy)                      # Positionswinkel
            rext = 0.33 * abs(math.sin(pa_ang)) + 0.10 * abs(math.cos(pa_ang))
            inner = rad - rext - R_out
            if inner < min_clear:
                schub = min_clear - inner
                ziel[i][0] = max(rand_in, min(frame_w_in - rand_in, ziel[i][0] + schub * lvx / rad))
                ziel[i][1] = max(rand_in, min(frame_h_in - rand_in, ziel[i][1] + schub * lvy / rad))

    # 7) Offsets schreiben (Nullpunkt = Ring-Band-Mitte des Segments; so
    #    rechnet PowerPoint den manualLayout-Offset bei vorhandenem
    #    manualLayout — empirisch bestätigt).
    import copy
    from lxml import etree
    dlbls = {int(d.find(_q("idx")).get("val")): d
             for d in root.iter(_q("dLbl")) if d.find(_q("idx")) is not None}

    # WICHTIG: Hat das Portfolio MEHR Segmente als die Vorlage Label-Elemente
    # (dLbl), so haben die zusätzlichen Segmente KEIN dLbl → PowerPoint setzt
    # sie auf die Default-Position (ins Loch). Deshalb für jedes fehlende
    # Segment ein dLbl aus einem vorhandenen KLONEN und einfügen.
    if dlbls:
        referenz = dlbls[min(dlbls)]
        container = referenz.getparent()
        for i in range(len(vals)):
            if i not in dlbls:
                neu = copy.deepcopy(referenz)
                neu.find(_q("idx")).set("val", str(i))
                # direkt hinter das Referenz-dLbl einsortieren (bleibt in der
                # dLbl-Gruppe vor den gemeinsamen dLbls-Eigenschaften)
                container.insert(list(container).index(referenz) + 1, neu)
                dlbls[i] = neu

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
    for idx, d in list(dlbls.items()):
        if idx >= len(vals):
            d.getparent().remove(d)
    return {"segmente": len(vals), "R_out": round(R_out, 3)}


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



# ─────────────────────────────────────────────────────────────────────────
# Segmentfarben, Führungslinien und Label-Farben (NEU 10.07.2026)
#
# PROBLEM: Die <c:dPt>-Farben der Vorlage hängen am INDEX, nicht am Namen.
# Die CVV-Vorlage hatte EDELMETALLE/RENTEN/LIQUIDITÄT (gold/blau/hellblau);
# nach dem Befüllen steht AKTIEN auf idx 0 und erbt Gold. Die Farbe muss
# deshalb datenbasiert je ASSETKLASSE gesetzt werden.
#
# Die Palette stammt aus den Vorlagen selbst (nicht erfunden):
#   14355C dunkelblau · 66A4CE hellblau · 9FD0EF helleres blau
#   BB9256 gold       · 808080 grau
# ─────────────────────────────────────────────────────────────────────────

ASSET_FARBEN = {
    "AKTIEN":       "14355C",   # dunkelblau
    "RENTEN":       "66A4CE",   # hellblau
    "EDELMETALLE":  "BB9256",   # gold
    "LIQUIDITÄT":   "9FD0EF",   # noch helleres blau
    "SONSTIGE":     "808080",   # grau
}

# Schriftfarbe der Prozent-Labels: IMMER Schwarz, unabhängig vom Segment.
# (Anforderung 10.07.2026 — die Zuordnung Label→Segment läuft über Position
# und Führungslinie, NICHT über die Schriftfarbe. Farbe gehört an den Ring.)
LABEL_SCHRIFTFARBE = "000000"

LEADER_GRAU = "A6A6A6"          # dezentes Grau für die Führungslinien
LEADER_BREITE_EMU = 9525        # 0.75 pt

_KERNKLASSEN = {"AKTIEN", "RENTEN", "EDELMETALLE", "LIQUIDITÄT"}
_FILL_TAGS = ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")


def _kategorien(ser):
    """Liest die Kategorienamen (idx-Reihenfolge) einer Serie."""
    cat = ser.find(_q("cat"))
    if cat is None:
        return []
    namen = {}
    for pt in cat.iter(_q("pt")):
        try:
            i = int(pt.get("idx"))
        except (TypeError, ValueError):
            continue
        v = pt.find(_q("v"))
        if v is not None and v.text:
            namen[i] = v.text.strip()
    return [namen.get(i, "") for i in range(max(namen) + 1)] if namen else []


def _ist_assetklassen_ring(kategorien):
    """True, wenn ALLE Kategorien Assetklassen sind und mindestens eine
    Kernklasse dabei ist.

    Damit fassen wir die Sektoren- und Regionen-Ringe der Themen-Broschüren
    NICHT an — deren Kategorien ("Informationstechnologie", "Nordamerika", …)
    stehen nicht in der Palette. Selbstselektierende Regel, kein Schalter.
    """
    if not kategorien:
        return False
    oben = [k.strip().upper() for k in kategorien if k.strip()]
    if not oben:
        return False
    return all(k in ASSET_FARBEN for k in oben) and any(k in _KERNKLASSEN for k in oben)


def _setze_fill(spPr, hexfarbe):
    """Ersetzt die Füllung eines <c:spPr> durch solidFill(hexfarbe).

    Schema-Reihenfolge in CT_ShapeProperties: (xfrm, geometry, FILL, ln, …).
    Die Füllung wird deshalb VOR ein evtl. vorhandenes <a:ln> gesetzt.
    """
    from lxml import etree
    for tag in _FILL_TAGS:
        for el in spPr.findall(_A + tag):
            spPr.remove(el)
    fill = etree.Element(_A + "solidFill")
    clr = etree.SubElement(fill, _A + "srgbClr")
    clr.set("val", hexfarbe)
    ln = spPr.find(_A + "ln")
    if ln is not None:
        ln.addprevious(fill)
    else:
        spPr.insert(0, fill)


def ring_segmentfarben(chart):
    """Setzt die Segmentfarben eines Assetklassen-Rings NAMENSBASIERT.

    Ohne diesen Schritt erbt jedes Segment die Farbe des Vorlagen-<c:dPt> an
    seiner INDEX-Position — dann ist z.B. AKTIEN gold statt dunkelblau.

    Rührt Ringe an, deren Kategorien KEINE Assetklassen sind, nicht an.
    Returns: dict {kategorie: hexfarbe} der gesetzten Segmente (leer = nichts getan).
    """
    from copy import deepcopy
    from lxml import etree
    root = _root(chart)
    ser = root.find(".//" + _q("ser"))
    if ser is None:
        return {}
    kats = _kategorien(ser)
    if not _ist_assetklassen_ring(kats):
        return {}

    vorhandene = {}
    for dpt in ser.findall(_q("dPt")):
        i = dpt.find(_q("idx"))
        if i is not None:
            vorhandene[int(i.get("val"))] = dpt
    if not vorhandene:
        return {}
    muster = vorhandene[min(vorhandene)]

    gesetzt = {}
    for i, name in enumerate(kats):
        schluessel = name.strip().upper()
        farbe = ASSET_FARBEN.get(schluessel)
        if not farbe:
            continue
        dpt = vorhandene.get(i)
        if dpt is None:
            # Vorlage hat weniger dPt als Segmente → aus einem vorhandenen
            # klonen (gleiche Falle wie bei den <c:dLbl>, siehe TW #26).
            dpt = deepcopy(muster)
            dpt.find(_q("idx")).set("val", str(i))
            letztes = ser.findall(_q("dPt"))[-1]
            letztes.addnext(dpt)
            vorhandene[i] = dpt
        spPr = dpt.find(_q("spPr"))
        if spPr is None:
            spPr = etree.SubElement(dpt, _q("spPr"))
        _setze_fill(spPr, farbe)
        gesetzt[name] = farbe

    # Überzählige dPt (Vorlage hatte mehr Segmente als jetzt) entfernen —
    # sonst färbt PowerPoint nicht existierende Punkte.
    for i, dpt in list(vorhandene.items()):
        if i >= len(kats):
            ser.remove(dpt)
    return gesetzt


def ring_leaderlines(chart, farbe=LEADER_GRAU, breite_emu=LEADER_BREITE_EMU):
    """Färbt die Führungslinien dezent (Default: Grau 0.75pt) statt Schwarz.

    ACHTUNG (OOXML-Grenze): <c:leaderLines> gilt für die GANZE Serie — eine
    Führungslinie pro Segment einzufärben ist im Chart-XML NICHT möglich.
    Die farbliche Zuordnung übernimmt deshalb der Labeltext (ring_label_farben).

    Schema-Reihenfolge in CT_DLbls: … showLeaderLines, dann leaderLines.
    """
    from lxml import etree
    root = _root(chart)
    ser = root.find(".//" + _q("ser"))
    if ser is None:
        return False
    dLbls = ser.find(_q("dLbls"))
    if dLbls is None:
        return False

    sll = dLbls.find(_q("showLeaderLines"))
    if sll is None:
        sll = etree.SubElement(dLbls, _q("showLeaderLines"))
    sll.set("val", "1")

    for el in dLbls.findall(_q("leaderLines")):
        dLbls.remove(el)
    ll = etree.SubElement(dLbls, _q("leaderLines"))
    spPr = etree.SubElement(ll, _q("spPr"))
    ln = etree.SubElement(spPr, _A + "ln")
    ln.set("w", str(int(breite_emu)))
    fill = etree.SubElement(ln, _A + "solidFill")
    clr = etree.SubElement(fill, _A + "srgbClr")
    clr.set("val", farbe)
    return True


def ring_label_schriftfarbe(chart, farbe=LABEL_SCHRIFTFARBE):
    """Setzt die Schriftfarbe ALLER Prozent-Labels einheitlich (Default schwarz).

    Die Vorlagen setzen keine explizite Textfarbe (die Labels erben Schwarz aus
    dem Theme). Wir setzen sie trotzdem explizit — dann bleibt der Text schwarz,
    egal welches Theme die Vorlage mitbringt.

    Die Schriftfarbe hängt bewusst NICHT von der Segmentfarbe ab: Die Zuordnung
    Label→Segment erfolgt über die Position und die Führungslinie. Farbe gehört
    an den Ring, nicht an die Zahl.
    """
    from lxml import etree
    root = _root(chart)
    ser = root.find(".//" + _q("ser"))
    if ser is None:
        return 0
    dLbls = ser.find(_q("dLbls"))
    if dLbls is None:
        return 0

    n = 0
    for dLbl in dLbls.findall(_q("dLbl")):
        if dLbl.find(_q("idx")) is None:
            continue
        # CT_DLbl-Reihenfolge: idx, layout, tx, numFmt, spPr, txPr, dLblPos, …
        txPr = dLbl.find(_q("txPr"))
        if txPr is None:
            txPr = etree.Element(_q("txPr"))
            etree.SubElement(txPr, _A + "bodyPr")
            etree.SubElement(txPr, _A + "lstStyle")
            p = etree.SubElement(txPr, _A + "p")
            pPr = etree.SubElement(p, _A + "pPr")
            etree.SubElement(pPr, _A + "defRPr")
            etree.SubElement(p, _A + "endParaRPr")
            spPr = dLbl.find(_q("spPr"))
            (spPr.addnext(txPr) if spPr is not None
             else dLbl.find(_q("idx")).addnext(txPr))
        for rpr in txPr.iter(_A + "defRPr"):
            for tag in _FILL_TAGS:
                for el in rpr.findall(_A + tag):
                    rpr.remove(el)
            fill = etree.Element(_A + "solidFill")
            clr = etree.SubElement(fill, _A + "srgbClr")
            clr.set("val", farbe)
            rpr.insert(0, fill)
        n += 1
    return n


def _kleine_segmente(chart, schwelle=0.08):
    """Anzahl Segmente unter `schwelle` (Anteil). Für adaptives Entzerren."""
    root = _root(chart)
    vals = [float(v.text) for v in root.iter(_q("v"))
            if v.getparent().getparent().tag == _q("numCache") and v.text]
    ser = root.find(".//" + _q("ser"))
    val = ser.find(_q("val")) if ser is not None else None
    if val is None:
        return 0
    zahlen = [float(v.text) for v in val.iter(_q("v")) if v.text]
    s = sum(zahlen)
    if s <= 0:
        return 0
    return sum(1 for z in zahlen if z / s < schwelle)

def nachbearbeiten(prs, hole_size=79, label_gap_in=0.14,
                   min_gap_deg=24.0, min_gap_deg_klein=32.0,
                   leader_farbe=LEADER_GRAU,
                   label_schriftfarbe=LABEL_SCHRIFTFARBE):
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
    stat = {"ringe": 0, "linien": 0, "ringe_gefaerbt": 0, "labels_schwarz": 0}
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_chart", False):
                continue
            chart = shape.chart
            typ = chart.chart_type.name if chart.chart_type else ""
            try:
                if "DOUGHNUT" in typ:
                    ring_holesize(chart, hole_size)

                    # NEU 10.07.2026 — Segmentfarben NAMENSBASIERT setzen.
                    # Gibt {} zurück, wenn es kein Assetklassen-Ring ist
                    # (Sektoren/Regionen bleiben damit unangetastet).
                    gesetzt = ring_segmentfarben(chart)
                    if gesetzt:
                        stat["ringe_gefaerbt"] += 1

                    # Rahmenmaße in Zoll (EMU/914400) für die geometrische
                    # Label-Platzierung.
                    _fw = shape.width / 914400.0
                    _fh = shape.height / 914400.0

                    # Adaptives Entzerren: NUR bei Assetklassen-Ringen mit
                    # mehreren kleinen Segmenten (dort drängeln sich die
                    # Labels oben). Sektoren-Ringe behalten min_gap_deg=24.
                    _gap = min_gap_deg
                    if gesetzt and _kleine_segmente(chart) >= 2:
                        _gap = min_gap_deg_klein

                    ring_labels_aussen_dynamisch(chart, _fw, _fh,
                                                 gap_in=label_gap_in,
                                                 min_gap_deg=_gap)

                    # Führungslinien dezent grau statt schwarz; Labeltext in
                    # der Segmentfarbe (einzige native Zuordnungsmöglichkeit).
                    if leader_farbe:
                        ring_leaderlines(chart, farbe=leader_farbe)
                    if label_schriftfarbe:
                        stat["labels_schwarz"] += ring_label_schriftfarbe(
                            chart, farbe=label_schriftfarbe)
                    stat["ringe"] += 1
                elif "LINE" in typ and _hat_dateax(chart):
                    datumsachse_an_daten(chart)
                    stat["linien"] += 1
            except Exception:
                # Ein einzelnes problematisches Chart darf den Export nie
                # abbrechen — schlimmstenfalls bleibt dieses Chart wie gehabt.
                pass
    return stat
