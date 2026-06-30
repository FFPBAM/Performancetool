"""PNG-basierte Ring-Charts mit Labels außen — Voll-Komposition.

Dieses Modul ersetzt PowerPoint-native Ring-Charts (Donuts) durch EIN einziges,
in matplotlib gerendertes PNG, das die komplette Komposition enthält:
- Banner oben (dunkelblau, weißer Titel)
- großer, mittiger Donut mit Labels außen + Leader-Linien mit Punkten
- Legende unten links (Farbquadrat + Text pro Item)
- Quelle unten rechts

Hintergrund: PowerPoints native Ring-Charts platzieren Datenbeschriftungen bei
großen Segmenten (>50%) trotz `dLblPos="outEnd"` innen — Microsofts
"smart auto-placement" lässt sich nicht per Property abschalten. matplotlib
gibt uns volle Kontrolle über Label-Positionen UND den Stil (Leader-Punkte).

Designentscheidung (Juni 2026): Die GESAMTE Komposition wird als ein PNG
gerendert und füllt die Original-Chart-Box passgenau aus. Das PNG-Seiten-
verhältnis wird exakt auf das Box-Seitenverhältnis gerendert (keine
`bbox_inches="tight"`-Beschneidung), sodass das Bild verzerrungsfrei die volle
Box ausfüllt — kein Oval mehr, kein Sub-Layout aus einzelnen Shapes, die
verrutschen könnten.

Hauptfunktion: `replace_donut_chart(slide, shape_name, ...)`.
"""
from __future__ import annotations

import io
from typing import Sequence

import matplotlib
matplotlib.use("Agg")  # Headless rendering (Streamlit Cloud)
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle


# ────────────────────────────────────────────────────────────────────────────
# FFPB-Farbpalette (aus der Vorlage extrahiert)
# ────────────────────────────────────────────────────────────────────────────
FFPB_COLORS = [
    "#1F3A5F",  # Dunkelblau (primär)
    "#7FA8C8",  # Hellblau
    "#C8A45C",  # Gold
    "#D5E0EB",  # Hellblau-grau (pale)
    "#A8A8A8",  # Grau (für "Sonstige")
    "#5E7A99",  # Mittelblau
    "#E5B97F",  # Hellgold
    "#3D5778",  # Dunkelgrau-blau
]
FFPB_DARKBLUE = "#1F3A5F"  # Banner-Hintergrund


# ────────────────────────────────────────────────────────────────────────────
# PNG-Rendering (Voll-Komposition)
# ────────────────────────────────────────────────────────────────────────────
def _render_donut_png(
    values: Sequence[float],
    item_labels: Sequence[str],
    percent_labels: Sequence[str],
    colors: Sequence[str],
    banner_text: str,
    source_text: str,
    box_aspect: float = 1.0,
    dpi: int = 200,
) -> bytes:
    """Rendert die komplette Donut-Komposition als ein PNG.

    Die Arrays `values`, `item_labels`, `percent_labels` und `colors` sind
    PARALLEL: Index i beschreibt dasselbe Segment (Wert, Legenden-Label,
    Prozent-Label, Farbe).

    Args:
        values: Numerische Werte pro Segment (Summe egal, relativ berechnet).
        item_labels: Legenden-Texte (z.B. "AKTIEN", "RENTEN").
        percent_labels: Vorformatierte Prozent-Strings (z.B. "38,90%").
        colors: Hex-Farben pro Segment (parallel zu values/item_labels).
        banner_text: Titel im Banner oben.
        source_text: Quellen-Annotation unten rechts.
        box_aspect: Seitenverhältnis (Breite/Höhe) der Ziel-Chart-Box. Das PNG
            wird in genau diesem Verhältnis gerendert, damit es die Box
            verzerrungsfrei ausfüllt.
        dpi: Render-Auflösung.

    Returns:
        PNG-Bytes (transparenter Hintergrund), Seitenverhältnis == box_aspect.
    """
    n = len(values)
    colors = list(colors)[:n]

    base_h = 5.0
    fig_w = base_h * max(0.45, float(box_aspect))  # Schutz gegen extreme Hochformate
    fig_h = base_h
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_alpha(0)

    # ── Banner oben (volle Breite) ──
    banner_h = 0.085  # Anteil der Figurhöhe
    fig.patches.append(Rectangle(
        (0, 1 - banner_h), 1, banner_h, transform=fig.transFigure,
        facecolor=FFPB_DARKBLUE, edgecolor="none", zorder=1,
    ))
    fig.text(0.028, 1 - banner_h / 2, banner_text, ha="left", va="center",
             color="white", fontsize=13, fontweight="bold", zorder=2)

    # ── Donut-Achse: volle Breite, zwischen Banner und Legenden-Zone ──
    legend_zone = 0.20  # unterer Anteil für Legende + Quelle
    ax = fig.add_axes([0.0, legend_zone, 1.0, 1 - banner_h - legend_zone], zorder=1)
    ax.set_aspect("equal")
    ax.axis("off")
    wedges, _ = ax.pie(
        list(values), colors=colors, startangle=90, counterclock=False,
        radius=1.0, wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.5),
    )

    # Labels außen mit Leader-Linie + Punkt
    r_ring, r_dot = 1.02, 1.22
    for wedge, lbl in zip(wedges, percent_labels):
        ang = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)
        c, s = np.cos(ang), np.sin(ang)
        ax.plot([r_ring * c, r_dot * c], [r_ring * s, r_dot * s],
                color="black", lw=1.1, zorder=3)
        ax.plot([r_dot * c], [r_dot * s], marker="o", color="black",
                markersize=4, zorder=4)
        ha = "left" if c >= 0 else "right"
        x_text = r_dot * c + (0.05 if c >= 0 else -0.05)
        ax.text(x_text, r_dot * s, lbl, ha=ha, va="center",
                fontsize=12, fontweight="bold", color="#1A1A1A", zorder=4)

    # Datengrenzen mit Rand für die Labels (Donut bleibt durch 'equal' rund)
    ax.set_xlim(-1.78, 1.78)
    ax.set_ylim(-1.45, 1.45)

    # ── Legende unten links ──
    row_h = 0.05
    sq_h = 0.032
    sq_w = sq_h * fig_h / fig_w  # in Figur-Koordinaten quadratisch halten
    leg_bottom = 0.025
    for i, (lbl, col) in enumerate(zip(item_labels, colors)):
        y = leg_bottom + (n - 1 - i) * row_h  # erstes Item oben
        fig.patches.append(Rectangle(
            (0.03, y), sq_w, sq_h, transform=fig.transFigure,
            facecolor=col, edgecolor="none", zorder=2,
        ))
        fig.text(0.03 + sq_w + 0.012, y + sq_h / 2, lbl, ha="left", va="center",
                 fontsize=10.5, fontweight="bold", color="black", zorder=2)

    # ── Quelle unten rechts ──
    fig.text(0.975, 0.04, source_text, ha="right", va="center",
             fontsize=8, color="#555555", zorder=2)

    buf = io.BytesIO()
    # WICHTIG: KEIN bbox_inches="tight" — sonst würde das PNG beschnitten und
    # das Seitenverhältnis verändert. Wir wollen exakt fig_w:fig_h = box_aspect.
    fig.savefig(buf, format="png", dpi=dpi, transparent=True)
    plt.close(fig)
    return buf.getvalue()


# ────────────────────────────────────────────────────────────────────────────
# Slide-Manipulation
# ────────────────────────────────────────────────────────────────────────────
def _remove_shape(slide, shape) -> None:
    """Entfernt eine Shape vom Slide."""
    sp = shape._element
    sp.getparent().remove(sp)


# ────────────────────────────────────────────────────────────────────────────
# Hauptfunktion
# ────────────────────────────────────────────────────────────────────────────
def replace_donut_chart(
    slide,
    chart_shape_name: str,
    *,
    values: Sequence[float],
    item_labels: Sequence[str],
    percent_labels: Sequence[str],
    colors: Sequence[str] | None = None,
    banner_text: str,
    source_text: str,
) -> None:
    """Ersetzt einen nativen Donut-Chart durch EIN PNG (Voll-Komposition).

    Drop-In-Ersatz für die Ring-Charts. Ablauf:
    1. Chart-Shape finden, Position + Größe merken.
    2. Chart-Shape entfernen (entfernt damit native Banner/Source mit).
    3. Komplette Komposition (Banner + Donut + Legende + Quelle) als ein PNG
       rendern — im Seitenverhältnis der Box.
    4. PNG passgenau in die Original-Box einfügen (verzerrungsfrei, da
       PNG-Seitenverhältnis == Box-Seitenverhältnis).

    Args:
        slide: Die Slide.
        chart_shape_name: Name der zu ersetzenden Chart-Shape
            (z.B. "C_Kennzahlen", "C_Kennzahlen1", "C_Kennzahlen2").
        values: Numerische Werte pro Segment.
        item_labels: Legenden-Labels (z.B. "Global", "Index"), parallel zu values.
        percent_labels: Vorformatierte Prozent-Strings (z.B. "57,03%").
        colors: Hex-Farben pro Segment. Default: FFPB_COLORS.
        banner_text: Text im Banner oben.
        source_text: Quellen-Annotation unten rechts.

    Raises:
        ValueError: Wenn Shape nicht gefunden.
    """
    # Chart-Shape finden
    chart_shape = None
    for sh in slide.shapes:
        if sh.name == chart_shape_name:
            chart_shape = sh
            break
    if chart_shape is None:
        raise ValueError(f"Shape '{chart_shape_name}' nicht gefunden auf Slide")

    # Bounding-Box merken
    cx, cy = chart_shape.left, chart_shape.top
    cw, ch = chart_shape.width, chart_shape.height

    if colors is None:
        colors = FFPB_COLORS[: len(values)]

    box_aspect = cw / ch if ch else 1.0

    # Original entfernen
    _remove_shape(slide, chart_shape)

    # Voll-Komposition rendern (PNG-Seitenverhältnis == Box-Seitenverhältnis)
    png_bytes = _render_donut_png(
        values=values,
        item_labels=list(item_labels),
        percent_labels=list(percent_labels),
        colors=list(colors),
        banner_text=banner_text,
        source_text=source_text,
        box_aspect=box_aspect,
    )

    # PNG passgenau in die Original-Box einfügen (füllt sie komplett, ohne Verzerrung)
    slide.shapes.add_picture(io.BytesIO(png_bytes), cx, cy, cw, ch)
