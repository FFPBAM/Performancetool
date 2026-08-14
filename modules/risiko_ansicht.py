"""
modules/risiko_ansicht.py — Darstellung der Monatsrenditen-Heatmap und des
Risiko-Blocks in der Performance-Ansicht (NEU 14.08.2026).

Dieses Modul ZEICHNET nur. Jede Zahl kommt aus `modules/analytics.py`, jede
Formatierung aus `modules/formats.py`. Hier steht keine Mathematik — sonst
gäbe es sie zweimal, und die beiden Fassungen liefen auseinander (die Lehre
aus Backlog B, E, F).

Aufgerufen wird es aus `streamlit_app.py` mit je einer Zeile, nach dem
Vorbild von `shared.zeige_anlagekriterien`. Die Performance-Ansicht ist
ansonsten inline; sie hat bereits über 900 Zeilen, und diese drei Blöcke
hätten sie um ein Viertel verlängert.

DREI HAUSREGELN, die hier besonders wehtun und deshalb oben stehen:

1. KEIN eigenes CSS, kein `unsafe_allow_html`, keine festen
   Hintergrundfarben für Flächen, die das Streamlit-Theme trägt. Der
   Präzedenzfall steht im Docstring von `shared.zeige_anlagekriterien`: Eine
   erste Fassung mit hellem HTML-Kasten wurde im Dark Mode zu einem grellen
   weißen Block, und `var(--background-color)` gibt es in Streamlit 1.61
   nachweislich nicht. Eingefärbt werden hier ausschließlich die ZELLEN der
   Heatmap — Achsen, Ticks und Schrift der Charts bleiben unangetastet und
   folgen damit dem Theme.

2. FARBE TRÄGT DIE AUSSAGE NIE ALLEIN. In jeder Zelle steht die Zahl. Aus
   demselben Grund sind die Ampel-Symbole aus `st.metric` geflogen.

3. EIN FEHLWERT SIEHT NICHT WIE EIN MESSWERT AUS. Ein fehlender Monat bleibt
   leer und wird nicht zu 0,00 % (Transferwissen #46). Alle Zahlen laufen
   deshalb über `formats.fmt_pct` / `fmt_ratio`, die bei None und NaN ein
   "–" liefern.
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from modules.analytics import (
    RISIKO_PERIODEN, ROLL_FENSTER_TAGE, calc_daily_returns_after_fee,
    has_benchmark, heatmap_kennzahlen, monatsrenditen,
    monatsrenditen_differenz, risiko_perioden, rollierende_vola,
)
from modules.formats import MONATSNAMEN_KURZ, fmt_pct, fmt_ratio, monat_kurz
from modules.shared import (
    FFPB_PALETTE, HEATMAP_GRENZE_ABSOLUT, HEATMAP_GRENZE_DIFFERENZ,
    HEATMAP_SKALA, HEATMAP_TEXT,
)

# Spaltenkopf der Jahresspalte. Sie ist bewusst KEINE eingefärbte Zelle:
# Ein Jahreswert ist betragsmäßig ein Vielfaches eines Monatswerts und würde
# die Farbskala der Monate plattdrücken.
JAHR_SPALTE = "Jahr"

# Kennzeichen für einen angebrochenen Monat. Kein Piktogramm — die
# Oberfläche ist frei davon, und ein Sternchen mit Fußnote ist ohnehin die
# Schreibweise, die ein Berater aus jedem Factsheet kennt.
UNVOLLSTAENDIG = "*"


# ─────────────────────────────────────────────────────────────────────────────
# Heatmap
# ─────────────────────────────────────────────────────────────────────────────

def _zellentext(wert, vollstaendig: bool) -> str:
    """Zellbeschriftung: eine Nachkommastelle, deutsches Komma, Vorzeichen.

    Eine Stelle und nicht zwei: Bei dreizehn Spalten nebeneinander entscheidet
    die Breite über die Lesbarkeit. Der genaue Wert steht im Hover.
    """
    if wert is None or pd.isna(wert):
        return ""
    text = f"{float(wert) * 100:+.1f}".replace(".", ",")
    return text + ("" if vollstaendig else UNVOLLSTAENDIG)


def _heatmap_figur(daten: dict, grenze: float, titel_hover: str) -> go.Figure:
    """Baut die Heatmap-Figur aus einer Monatsmatrix."""
    renditen, vollst = daten["renditen"], daten["vollstaendig"]
    # Jüngstes Jahr oben — die Leserichtung jedes Factsheets.
    jahre = sorted(renditen.index, reverse=True)

    z, texte, hover = [], [], []
    for jahr in jahre:
        z_zeile, t_zeile, h_zeile = [], [], []
        for monat in range(1, 13):
            wert = renditen.loc[jahr, monat]
            voll = bool(vollst.loc[jahr, monat])
            z_zeile.append(None if pd.isna(wert) else float(wert) * 100.0)
            t_zeile.append(_zellentext(wert, voll))
            if pd.isna(wert):
                h_zeile.append(f"{monat_kurz(monat)} {jahr}<br>keine Daten")
            else:
                zusatz = "" if voll else "<br>angebrochener Monat"
                h_zeile.append(f"{monat_kurz(monat)} {jahr}<br>"
                               f"{titel_hover}: {fmt_pct(wert)}{zusatz}")
        # Die Jahresspalte bleibt ohne Füllung (z = None) und ohne Text;
        # ihr Wert kommt als Annotation. Grund: Eine Zelle mit fehlendem
        # z-Wert rendert je nach Plotly-Fassung ihren Text nicht mit.
        z.append(z_zeile + [None])
        texte.append(t_zeile + [""])
        h_zeile.append("")
        hover.append(h_zeile)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=list(MONATSNAMEN_KURZ) + [JAHR_SPALTE],
        y=[str(j) for j in jahre],
        text=texte,
        texttemplate="%{text}",
        textfont=dict(size=11, color=HEATMAP_TEXT),
        customdata=hover,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=HEATMAP_SKALA,
        zmid=0.0,
        zmin=-grenze * 100.0,
        zmax=grenze * 100.0,
        xgap=2, ygap=2,
        showscale=False,
    ))

    # Jahreswerte als Annotationen — garantiert farblos und damit ohne
    # Einfluss auf die Skala der Monate.
    for jahr in jahre:
        wert = daten["jahr"].loc[jahr]
        if pd.isna(wert):
            continue
        voll = bool(daten["jahr_vollstaendig"].loc[jahr])
        fig.add_annotation(
            x=JAHR_SPALTE, y=str(jahr),
            text=f"<b>{_zellentext(wert, voll)}</b>",
            showarrow=False, font=dict(size=11), xanchor="center",
        )

    fig.update_layout(
        height=max(220, 30 * len(jahre) + 110),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(side="top", fixedrange=True, showgrid=False, ticks=""),
        yaxis=dict(fixedrange=True, showgrid=False, ticks=""),
        separators=",.",
    )
    return fig


def _kennzeile(daten: dict, ist_differenz: bool) -> str:
    """Die Zeile unter der Heatmap — fällt vollständig aus der Matrix ab."""
    k = heatmap_kennzahlen(daten)
    if not k["anzahl"]:
        return "Kein vollständiger Monat im Zeitraum."

    def _monat(eintrag):
        (jahr, monat), wert = eintrag
        return f"{monat_kurz(monat)} {jahr} mit {fmt_pct(wert)}"

    teile = [f"{k['anzahl']} vollständige Monate"]
    if ist_differenz:
        # Die Trefferquote ist die Frage, die jeder als Erstes an eine
        # Differenz-Matrix stellt.
        teile.append(f"Trefferquote {fmt_pct(k['anteil_positiv'])} — in "
                     f"{k['positiv']} von {k['anzahl']} Monaten besser")
    else:
        teile.append(f"{k['positiv']} davon positiv "
                     f"({fmt_pct(k['anteil_positiv'])})")
    teile.append(f"bester Monat {_monat(k['bester'])}")
    teile.append(f"schlechtester {_monat(k['schlechtester'])}")
    return " · ".join(teile)


def _hat_unvollstaendige(daten: dict) -> bool:
    r, v = daten["renditen"], daten["vollstaendig"]
    for jahr in r.index:
        for monat in r.columns:
            if pd.notna(r.loc[jahr, monat]) and not bool(v.loc[jahr, monat]):
                return True
    return False


def _zeichne_matrix(daten, grenze, hover_titel, ist_differenz, schluessel):
    """Chart, Kennzeile und Sternchen-Fußnote einer Matrix."""
    if daten["renditen"].empty or not daten["renditen"].notna().any().any():
        st.caption("Für diese Auswahl gibt es keine Monatsrenditen.")
        return
    st.plotly_chart(_heatmap_figur(daten, grenze, hover_titel),
                    config={"displayModeBar": False}, key=schluessel)
    st.caption(_kennzeile(daten, ist_differenz))
    if _hat_unvollstaendige(daten):
        st.caption(
            f"Mit {UNVOLLSTAENDIG} gekennzeichnete Felder umfassen weniger "
            "als den vollen Kalendermonat — der Auflagemonat der Strategie "
            "und der laufende Monat. Sie zählen in den Kennzahlen dieser "
            "Zeile nicht mit.")


def zeige_monatsheatmap(label, ts_df, fee_dec,
                        gegen_benchmark=False, benchmark_name="Benchmark",
                        vergleich=None, mwst_suffix="", schluessel="p1"):
    """Monatsrenditen-Heatmap einer Strategie, wahlweise mit Differenzen.

    Args:
        label: Anzeigename der Strategie
        ts_df: UNGESCHNITTENE Zeitreihe (siehe Hinweis unten), bereits durch
            `historie_beschneiden` gelaufen
        fee_dec: Honorarsatz p.a. dezimal, inkl. MwSt-Faktor
        gegen_benchmark: zusätzliche Matrix gegen die eigene Benchmark
        benchmark_name: Anzeigename der Benchmark
        vergleich: (label, ts_df, fee_dec) der Vergleichsstrategie oder None
        mwst_suffix: Textbaustein " (exkl. MwSt.)" für die Beschriftung
        schluessel: Suffix für die Plotly-Keys (mehrere Charts je Seite)

    WARUM DIE UNGESCHNITTENE REIHE: Die Heatmap zeigt bewusst die volle
    Historie und folgt NICHT der Zeitraum-Schnellwahl (Festlegung Philip,
    14.08.2026). Zwei Gründe. Erstens Compliance: die gesamte Historie zeigen,
    kein Cherry-Picking. Zweitens würde ein Zuschnitt an beiden Rändern
    künstliche Rumpfmonate erzeugen, die mit der Strategie nichts zu tun
    haben. Entscheidend ist der zweite Effekt: Sobald das Vergleichsportfolio
    aktiv ist, schneidet `streamlit_app.py` beide Reihen per Inner-Join auf
    die gemeinsamen Handelstage — "Muster ausgewogen cVV" gegen
    "Comdirect 100" verlöre so fünfzehn Jahre.
    """
    st.markdown("---")
    st.subheader("Monatsrenditen")
    st.caption(
        f"Volle Historie seit {ts_df.index.min():%m/%Y}, unabhängig vom "
        f"oben gewählten Zeitraum. Werte nach Kosten{mwst_suffix}.")

    absolut = monatsrenditen(ts_df, fee_dec)
    _zeichne_matrix(absolut, HEATMAP_GRENZE_ABSOLUT, label,
                    False, f"heat_abs_{schluessel}")

    if gegen_benchmark:
        st.markdown(f"**Differenz zur Benchmark ({benchmark_name})**")
        if not ("ret_bm" in ts_df.columns and has_benchmark(ts_df["ret_bm"])):
            st.caption(
                f"Für {label} ist kein Vergleichsmaßstab (Benchmark) "
                "hinterlegt — es gibt deshalb keine Differenz zu zeigen.")
        else:
            bm = monatsrenditen(ts_df, 0.0, spalte="ret_bm", nach_kosten=False)
            diff = monatsrenditen_differenz(absolut, bm)
            st.caption(
                "Geometrisch gerechnet, damit sich die Monate einer Zeile "
                "exakt zur Jahresspalte verketten. Die Strategie steht nach "
                f"Kosten{mwst_suffix}, die Benchmark trägt keine — die "
                "Differenz enthält also das Honorar.")
            _zeichne_matrix(diff, HEATMAP_GRENZE_DIFFERENZ,
                            f"{label} gegen {benchmark_name}",
                            True, f"heat_bm_{schluessel}")

    if vergleich is not None:
        v_label, v_df, v_fee = vergleich
        st.markdown(f"**Differenz zu {v_label}**")
        v_matrix = monatsrenditen(v_df, v_fee)
        diff = monatsrenditen_differenz(absolut, v_matrix)
        st.caption(
            f"Nur Monate, in denen beide Strategien vollständig liefen — "
            f"{v_label} beginnt {v_df.index.min():%m/%Y}. Beide nach "
            f"Kosten{mwst_suffix}; laufen unterschiedliche Honorarsätze, "
            "steckt der Unterschied mit in der Differenz.")
        _zeichne_matrix(diff, HEATMAP_GRENZE_DIFFERENZ,
                        f"{label} gegen {v_label}", True,
                        f"heat_cmp_{schluessel}")


# ─────────────────────────────────────────────────────────────────────────────
# Risiko im Überblick
# ─────────────────────────────────────────────────────────────────────────────

def _vola_figur(reihen):
    """Linien-Chart der rollierenden Volatilität; None, wenn nichts zu zeigen."""
    fig = go.Figure()
    etwas_gezeichnet = False

    for label, ts_df, fee_dec, bm_name, mit_bm in reihen:
        netto = calc_daily_returns_after_fee(
            ts_df["ret_port"].fillna(0.0).to_numpy(dtype=float), fee_dec)
        werte = rollierende_vola(netto) * 100.0
        if np.isfinite(werte).any():
            fig.add_trace(go.Scatter(x=list(ts_df.index), y=werte,
                                     mode="lines", name=label))
            etwas_gezeichnet = True
        if mit_bm:
            bm_werte = rollierende_vola(
                ts_df["ret_bm"].fillna(0.0).to_numpy(dtype=float)) * 100.0
            if np.isfinite(bm_werte).any():
                fig.add_trace(go.Scatter(x=list(ts_df.index), y=bm_werte,
                                         mode="lines",
                                         name=f"BM {label}: {bm_name}"))
                etwas_gezeichnet = True

    if not etwas_gezeichnet:
        return None

    fig.update_layout(
        height=350,
        xaxis_title="Datum", xaxis=dict(tickformat="%d.%m.%Y"),
        yaxis_title="Volatilität p.a.", yaxis=dict(ticksuffix=" %"),
        hovermode="x unified", colorway=FFPB_PALETTE, separators=",.",
    )
    return fig


def _perioden_tabelle(reihen, spalten):
    """Formatierte Perioden-Tabelle je Strategie.

    `spalten` ist eine Liste (schluessel, ueberschrift, formatierer).
    Eine Spalte entfällt ganz, wenn sie für keine Zeile einen Wert hat —
    eine Spalte aus lauter "–" ist keine Information, sondern Ballast.
    """
    ausgabe = []
    for label, ts_df, fee_dec in reihen:
        tab = risiko_perioden(ts_df, fee_dec)
        nutzbar = [(s, u, f) for s, u, f in spalten if tab[s].notna().any()]
        zeilen = []
        for bez in RISIKO_PERIODEN:
            zeile = {"Zeitraum": bez}
            for schluessel, ueberschrift, formatierer in nutzbar:
                zeile[ueberschrift] = formatierer(tab.loc[bez, schluessel])
            zeilen.append(zeile)
        ausgabe.append((label, pd.DataFrame(zeilen)))
    return ausgabe


def zeige_risiko_ueberblick(reihen, mwst_suffix=""):
    """Rollierende Volatilität als Chart plus Kennzahlen je Zeitraum.

    Args:
        reihen: Liste (label, ts_df, fee_dec, benchmark_name, mit_benchmark)
        mwst_suffix: Textbaustein für die Beschriftung
    """
    st.markdown("---")
    st.subheader("Risiko im Überblick")

    fig = _vola_figur(reihen)
    if fig is None:
        st.caption(
            f"Für eine rollierende Volatilität braucht es mindestens "
            f"{ROLL_FENSTER_TAGE} Tage Historie. Die gewählte Strategie ist "
            "dafür noch zu jung.")
    else:
        st.caption(
            f"Volatilität der jeweils letzten {ROLL_FENSTER_TAGE} Tage, "
            f"annualisiert und nach Kosten{mwst_suffix}. Die Linie beginnt "
            "deshalb ein Jahr nach Auflage. Die Benchmark trägt keine Kosten.")
        st.plotly_chart(fig, config={"displayModeBar": False}, key="vola_roll")

    spalten = [
        ("vola",   "Volatilität p.a.",  fmt_pct),
        ("sharpe", "Sharpe Ratio",      fmt_ratio),
        ("te",     "Tracking Error",    fmt_pct),
        ("ir",     "Information Ratio", fmt_ratio),
    ]
    schlicht = [(label, df, fee) for label, df, fee, _, _ in reihen]
    for label, tabelle in _perioden_tabelle(schlicht, spalten):
        st.markdown(f"**{label}**")
        st.dataframe(tabelle, hide_index=True)

    st.caption(
        "Ein Zeitraum, der weiter zurückreicht als die Historie der "
        "Strategie, bleibt leer — dort steht bewusst kein gekürzter Wert. "
        "Tracking Error ist die Schwankungsbreite der Rendite gegenüber der "
        "Benchmark, die Information Ratio setzt die Mehrrendite dazu ins "
        "Verhältnis; beide entfallen ohne hinterlegte Benchmark.")


def zeige_drawdown_tabelle(reihen):
    """Maximaler Drawdown je Zeitraum — Ergänzung zum Drawdown-Chart.

    Args:
        reihen: Liste (label, ts_df, fee_dec)
    """
    spalten = [("max_dd", "Max. Drawdown", fmt_pct)]
    for label, tabelle in _perioden_tabelle(reihen, spalten):
        st.markdown(f"**Max. Drawdown je Zeitraum – {label}**")
        st.dataframe(tabelle, hide_index=True)
    st.caption(
        "Jeweils der tiefste Rückgang vom Höchststand innerhalb des "
        "Zeitraums, nach Kosten. Reicht ein Zeitraum weiter zurück als die "
        "Historie, bleibt er leer.")
