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
    has_benchmark, heatmap_kennzahlen, monats_durchschnitt, monatsrenditen,
    monatsrenditen_differenz, risiko_perioden, rollierende_vola,
)
from modules.formats import (
    EMPTY_VALUE, MONATSNAMEN_KURZ, fmt_pct, fmt_ratio, monat_kurz, monat_lang,
)
from modules.shared import (
    FFPB_PALETTE, HEATMAP_GRENZE_ABSOLUT, HEATMAP_GRENZE_DIFFERENZ,
    HEATMAP_SKALA, HEATMAP_TEXT,
)

# Spaltenkopf der Jahresspalte. Sie ist bewusst KEINE eingefärbte Zelle:
# Ein Jahreswert ist betragsmäßig ein Vielfaches eines Monatswerts und würde
# die Farbskala der Monate plattdrücken.
JAHR_SPALTE = "Jahr"

# Beschriftung der Durchschnittszeile. Ein Zeichen, damit die y-Achse nicht
# durch eine lange Zeile aus dem Raster faellt.
DURCHSCHNITT_ZEILE = "Ø"

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


def _colorbar(grenze: float) -> dict:
    """Waagerechte Farblegende unter der Matrix.

    Die Enden tragen "≤" und "≥" (NEU 14.08.2026): Werte jenseits der Grenze
    sättigen aus, und das gehört benannt statt verschwiegen. Rund 15 % der
    Monate liegen über ±3 % — ohne diese beiden Zeichen sähe es so aus, als
    wäre der dunkelste Ton der Höchstwert.
    """
    halb = grenze / 2.0
    return dict(
        orientation="h", x=0.5, xanchor="center", y=-0.18, yanchor="top",
        len=0.55, thickness=12, outlinewidth=0,
        ticks="outside", ticklen=4, tickfont=dict(size=10),
        tickvals=[-grenze * 100, -halb * 100, 0.0, halb * 100, grenze * 100],
        # Alle fuenf Beschriftungen durch fmt_pct: Eine von Hand gesetzte
        # Null ("0 %") stand sonst als einzige mit anderem Abstand da.
        ticktext=[f"≤ {fmt_pct(-grenze, 1)}", fmt_pct(-halb, 1),
                  fmt_pct(0.0, 1), fmt_pct(halb, 1),
                  f"≥ {fmt_pct(grenze, 1)}"],
    )


def _heatmap_figur(daten: dict, grenze: float, titel_hover: str) -> go.Figure:
    """Baut die Heatmap-Figur aus einer Monatsmatrix."""
    renditen, vollst = daten["renditen"], daten["vollstaendig"]
    # Jüngstes Jahr oben — die Leserichtung jedes Factsheets.
    jahre = sorted(renditen.index, reverse=True)
    schnitt = monats_durchschnitt(daten)
    hat_schnitt = not schnitt["monate"].empty

    z, texte, hover, zeilen = [], [], [], []

    def _zeile(beschriftung, werte, vollmaske, hover_kopf):
        z_zeile, t_zeile, h_zeile = [], [], []
        for monat in range(1, 13):
            wert = werte.loc[monat]
            voll = bool(vollmaske(monat))
            z_zeile.append(None if pd.isna(wert) else float(wert) * 100.0)
            t_zeile.append(_zellentext(wert, voll))
            if pd.isna(wert):
                h_zeile.append(f"{monat_lang(monat)} {hover_kopf}<br>keine Daten")
            else:
                zusatz = "" if voll else "<br>angebrochener Monat"
                h_zeile.append(f"{monat_lang(monat)} {hover_kopf}<br>"
                               f"{titel_hover}: {fmt_pct(wert)}{zusatz}")
        # Die Jahresspalte bleibt ohne Füllung (z = None) und ohne Text;
        # ihr Wert kommt als Annotation. Grund: Eine Zelle mit fehlendem
        # z-Wert rendert je nach Plotly-Fassung ihren Text nicht mit.
        z.append(z_zeile + [None])
        texte.append(t_zeile + [""])
        hover.append(h_zeile + [""])
        zeilen.append(beschriftung)

    for jahr in jahre:
        _zeile(str(jahr), renditen.loc[jahr],
               lambda m, j=jahr: vollst.loc[j, m], str(jahr))

    if hat_schnitt:
        # Die Ø-Zeile besteht nur aus vollen Jahren — jeder ihrer Werte ist
        # damit vollstaendig und traegt kein Sternchen.
        _zeile(DURCHSCHNITT_ZEILE, schnitt["monate"], lambda m: True,
               f"Ø {schnitt['jahre'][0]}–{schnitt['jahre'][-1]}")

    fig = go.Figure(go.Heatmap(
        z=z,
        x=list(MONATSNAMEN_KURZ) + [JAHR_SPALTE],
        y=zeilen,
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
        showscale=True,
        colorbar=_colorbar(grenze),
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
    if hat_schnitt and schnitt["jahr"] is not None:
        fig.add_annotation(
            x=JAHR_SPALTE, y=DURCHSCHNITT_ZEILE,
            text=f"<b>{_zellentext(schnitt['jahr'], True)}</b>",
            showarrow=False, font=dict(size=11), xanchor="center",
        )

    fig.update_layout(
        height=max(240, 30 * len(zeilen) + 150),
        margin=dict(l=10, r=10, t=10, b=60),
        xaxis=dict(side="top", fixedrange=True, showgrid=False, ticks=""),
        yaxis=dict(fixedrange=True, showgrid=False, ticks=""),
        separators=",.",
    )
    return fig


def _heatmap_tabelle(daten: dict) -> pd.DataFrame:
    """Dieselben Zahlen als kopierbare Tabelle.

    Aus einem Plotly-Chart bekommt man Werte nicht heraus; Berater ziehen sie
    aber gern nach Excel. Dasselbe Muster wie beim Balken-Chart.
    """
    renditen, vollst = daten["renditen"], daten["vollstaendig"]
    schnitt = monats_durchschnitt(daten)
    spalten = [JAHR_SPALTE] + list(MONATSNAMEN_KURZ) + ["Gesamt"]

    def _text(wert, voll):
        gesetzt = _zellentext(wert, voll)
        return gesetzt if gesetzt else EMPTY_VALUE

    # Ueber monat_kurz() und nicht MONATSNAMEN_KURZ[monat - 1]: Die Spalten
    # muessen exakt denen der Heatmap entsprechen, und die Index-Arithmetik
    # ist genau die Stelle, an der ein Off-by-one entstuende.
    zeilen = []
    for jahr in sorted(renditen.index, reverse=True):
        zeile = {JAHR_SPALTE: str(jahr)}
        for monat in range(1, 13):
            zeile[monat_kurz(monat)] = _text(
                renditen.loc[jahr, monat], bool(vollst.loc[jahr, monat]))
        zeile["Gesamt"] = _text(daten["jahr"].loc[jahr],
                                bool(daten["jahr_vollstaendig"].loc[jahr]))
        zeilen.append(zeile)

    if not schnitt["monate"].empty:
        zeile = {JAHR_SPALTE: DURCHSCHNITT_ZEILE}
        for monat in range(1, 13):
            zeile[monat_kurz(monat)] = _text(schnitt["monate"].loc[monat], True)
        zeile["Gesamt"] = _text(schnitt["jahr"], True)
        zeilen.append(zeile)

    return pd.DataFrame(zeilen, columns=spalten)


def _kennzeile(daten: dict, ist_differenz: bool) -> str:
    """Die Zeile unter der Heatmap — fällt vollständig aus der Matrix ab."""
    k = heatmap_kennzahlen(daten)
    if not k["anzahl"]:
        return "Kein vollständiger Monat im Zeitraum."

    def _monat(eintrag):
        # Im Fliesstext der ausgeschriebene Name: "April 2020" liest sich,
        # "Apr 2020" stolpert. In den Spaltenkoepfen bleibt es kurz.
        (jahr, monat), wert = eintrag
        return f"{monat_lang(monat)} {jahr}, {fmt_pct(wert)}"

    # Eine Nachkommastelle bei der Quote: "66,19 %" ist Scheingenauigkeit.
    quote = fmt_pct(k["anteil_positiv"], 1)
    teile = [f"{k['anzahl']} volle Monate"]
    if ist_differenz:
        # Die Trefferquote ist die Frage, die jeder als Erstes an eine
        # Differenz-Matrix stellt.
        teile.append(f"Trefferquote {quote} ({k['positiv']} von {k['anzahl']})")
    else:
        teile.append(f"{k['positiv']} positiv ({quote})")
    teile.append(f"bester: {_monat(k['bester'])}")
    teile.append(f"schlechtester: {_monat(k['schlechtester'])}")
    return " · ".join(teile)


def _hat_unvollstaendige(daten: dict) -> bool:
    r, v = daten["renditen"], daten["vollstaendig"]
    for jahr in r.index:
        for monat in r.columns:
            if pd.notna(r.loc[jahr, monat]) and not bool(v.loc[jahr, monat]):
                return True
    return False


def _zeichne_matrix(daten, grenze, hover_titel, ist_differenz, schluessel):
    """Chart, Kennzeile, Fußnoten und der Haken für die Tabelle."""
    if daten["renditen"].empty or not daten["renditen"].notna().any().any():
        st.caption("Für diese Auswahl gibt es keine Monatsrenditen.")
        return
    st.plotly_chart(_heatmap_figur(daten, grenze, hover_titel),
                    config={"displayModeBar": False}, key=schluessel)
    st.caption(_kennzeile(daten, ist_differenz))

    if _hat_unvollstaendige(daten):
        # Seit der Zeitraum-Kopplung (14.08.2026) kann ein angebrochener
        # Monat auch vom RAND DES ZEITRAUMS kommen, nicht mehr nur von der
        # Auflage oder vom laufenden Monat. Die Fußnote muss das nennen.
        st.caption(
            f"{UNVOLLSTAENDIG} = angebrochener Monat (Auflage, Rand des "
            "Zeitraums oder laufender Monat). Zählt in den Kennzahlen nicht "
            "mit.")

    schnitt = monats_durchschnitt(daten)
    if not schnitt["monate"].empty:
        jahre = schnitt["jahre"]
        spanne = (f"{jahre[0]}" if len(jahre) == 1
                  else f"{jahre[0]}–{jahre[-1]}")
        st.caption(
            f"{DURCHSCHNITT_ZEILE} = geometrisches Mittel über die "
            f"{len(jahre)} vollständigen Kalenderjahre ({spanne}). "
            "Angebrochene Jahre bleiben außen vor, damit für jeden Monat "
            "dieselben Jahre zugrunde liegen.")

    if st.checkbox("Tabelle anzeigen", value=False, key=f"tbl_{schluessel}",
                   help="Blendet dieselben Zahlen als Tabelle ein — zum "
                        "Herauskopieren."):
        st.dataframe(_heatmap_tabelle(daten), hide_index=True)


def _zuschnitt(ts_df, von, bis):
    """Reihe auf den gewählten Zeitraum kürzen; None heißt „offenes Ende"."""
    if ts_df is None or len(ts_df) == 0:
        return ts_df
    von = pd.Timestamp(von) if von is not None else None
    bis = pd.Timestamp(bis) if bis is not None else None
    # .loc-Slicing auf einem sortierten DatetimeIndex versteht None auf
    # beiden Seiten und liefert dann den jeweiligen Rand der Reihe.
    return ts_df.loc[von:bis]


def zeige_monatsheatmap(label, ts_df, fee_dec,
                        gegen_benchmark=False, benchmark_name="Benchmark",
                        vergleich=None, mwst_suffix="", schluessel="p1",
                        von=None, bis=None):
    """Monatsrenditen-Heatmap einer Strategie, wahlweise mit Differenzen.

    Args:
        label: Anzeigename der Strategie
        ts_df: Zeitreihe, bereits durch `historie_beschneiden` gelaufen —
            aber NICHT auf den Zeitraum geschnitten (siehe unten)
        fee_dec: Honorarsatz p.a. dezimal, inkl. MwSt-Faktor
        gegen_benchmark: zusätzliche Matrix gegen die eigene Benchmark
        benchmark_name: Anzeigename der Benchmark
        vergleich: (label, ts_df, fee_dec) der Vergleichsstrategie oder None
        mwst_suffix: Textbaustein " (exkl. MwSt.)" für die Beschriftung
        schluessel: Suffix für die Plotly-Keys (mehrere Charts je Seite)
        von, bis: Zeitraum-Grenzen; None heißt „Rand der jeweiligen Reihe"

    DER ZUSCHNITT PASSIERT HIER UND NICHT VORHER (14.08.2026). Die Heatmap
    folgt seit der Sichtprüfung dem oben gewählten Zeitraum — aber sie
    bekommt die UNGESCHNITTENE Reihe und schneidet selbst. Der Grund ist der
    Inner-Join in `streamlit_app.py`: Sobald das Vergleichsportfolio aktiv
    ist, sind `df1`/`df2` dort auf die gemeinsamen Handelstage reduziert, und
    `mind` ist die Schnittmenge beider Historien. "Muster ausgewogen cVV"
    (ab 2009) gegen "Comdirect 100" (ab 2024) verlöre bei „Seit Auflage"
    fünfzehn Jahre, ohne dass die Auswahl das nahelegt.

    Mit `von=None` beginnt deshalb JEDE Reihe an ihrem eigenen ersten Monat.
    """
    ts_df = _zuschnitt(ts_df, von, bis)
    if ts_df is None or len(ts_df) == 0:
        st.markdown("---")
        st.subheader("Monatsrenditen")
        st.caption(f"Für {label} liegen im gewählten Zeitraum keine Daten.")
        return

    st.markdown("---")
    st.subheader("Monatsrenditen")
    st.caption(f"{ts_df.index.min():%m/%Y} – {ts_df.index.max():%m/%Y}, "
               f"nach Kosten{mwst_suffix}.")

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
                "Geometrisch gerechnet, damit die Monate einer Zeile genau "
                f"den Jahreswert ergeben. Die Strategie steht nach "
                f"Kosten{mwst_suffix}, die Benchmark ohne — das Honorar "
                "steckt also in der Differenz.")
            _zeichne_matrix(diff, HEATMAP_GRENZE_DIFFERENZ,
                            f"{label} gegen {benchmark_name}",
                            True, f"heat_bm_{schluessel}")

    if vergleich is not None:
        v_label, v_df, v_fee = vergleich
        v_df = _zuschnitt(v_df, von, bis)
        st.markdown(f"**Differenz zu {v_label}**")
        if v_df is None or len(v_df) == 0:
            st.caption(f"Für {v_label} liegen im gewählten Zeitraum keine "
                       "Daten.")
            return
        v_matrix = monatsrenditen(v_df, v_fee)
        diff = monatsrenditen_differenz(absolut, v_matrix)
        st.caption(
            f"Nur Monate, in denen beide Strategien vollständig liefen — "
            f"{v_label} beginnt {v_df.index.min():%m/%Y}. Beide nach "
            f"Kosten{mwst_suffix}; bei unterschiedlichen Honorarsätzen steckt "
            "der Unterschied mit in der Differenz.")
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

    FOLGT BEWUSST NICHT DEM GEWÄHLTEN ZEITRAUM (14.08.2026), anders als die
    Heatmap darüber. Zwei Gründe, beide zwingend:

    - Die ZEILEN der Tabelle SIND die Zeiträume. Eine "10 Jahre"-Zeile
      innerhalb einer Drei-Jahres-Auswahl wäre in sich widersprüchlich.
    - Der Vola-Chart braucht ein Jahr Vorlauf, bevor der erste Punkt
      entsteht. Bei der Auswahl "1 Jahr" bliebe er komplett leer.

    Wer das später angleichen will, muss zuerst diese beiden Fragen
    beantworten — sonst wird es keine Verbesserung, sondern ein leerer Block.
    """
    st.markdown("---")
    st.subheader("Risiko im Überblick")
    st.caption("Immer über die volle Historie — die Zeilen der Tabelle sind "
               "selbst die Zeiträume. Die Auswahl oben wirkt hier nicht.")

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
