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
    BAND_MIN_JAHRE, RISIKO_PERIODEN, ROLL_FENSTER_TAGE, bandbreite,
    calc_daily_returns_after_fee, has_benchmark, heatmap_kennzahlen,
    monats_durchschnitt, monatsrenditen, monatsrenditen_differenz,
    risiko_perioden, rollierende_vola,
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

# Die beiden Ansichten derselben Daten. "Jahr für Jahr" beantwortet „wie lief
# jeder Monat?", "Bandbreite" beantwortet „ist dieser März ungewöhnlich?".
ANSICHT_JAHRE = "Jahr für Jahr"
ANSICHT_BAND = "Bandbreite"
ANSICHTEN = (ANSICHT_JAHRE, ANSICHT_BAND)

# Kachelhöhe in Pixeln, je weniger Zeilen desto größer (siehe _zeilenhoehe).
ZEILE_HOEHE_MIN = 30.0
ZEILE_HOEHE_MAX = 80.0


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


def _zeilenhoehe(anzahl: int) -> float:
    """Höhe einer Kachelzeile in Pixeln — je weniger Zeilen, desto höher.

    Bei zwei Zeilen (Zeitraum „1 Jahr") war die Matrix vorher ein flacher
    Streifen aus sehr breiten, sehr niedrigen Kacheln. Die Höhe wächst
    deshalb umgekehrt zur Zeilenzahl, gedeckelt bei ZEILE_HOEHE_MAX.

    Der Deckel ist nicht willkürlich: Bei dreizehn Spalten auf voller
    Streamlit-Breite ist eine Spalte rund 75 px breit. Bei 80 px Höhe wird
    die Kachel also annähernd quadratisch — darüber kippte sie ins Stehende
    und die Matrix läge quer.
    """
    if anzahl <= 0:
        return ZEILE_HOEHE_MAX
    return min(ZEILE_HOEHE_MAX, max(ZEILE_HOEHE_MIN, 600.0 / anzahl))


def _zeile(beschriftung, werte, voll_je_monat, hover_je_monat,
           jahr_wert=None, jahr_voll=True):
    """Eine Zeile der Heatmap, unabhängig davon, was sie bedeutet.

    Getrennt von `_heatmap_figur` (14.08.2026), damit die zweite Ansicht
    keine zweite Zeichenmaschine braucht: Eine Zeile ist einfach ein Satz
    Monatswerte plus die Frage, was im Hover steht.

    Args:
        beschriftung: y-Achsen-Beschriftung ("2026", "5J-Hoch", "Ø")
        werte: Series index 1..12, Dezimal
        voll_je_monat: callable(monat) -> bool, steuert das Sternchen
        hover_je_monat: callable(monat, wert) -> str
        jahr_wert: Wert der Jahresspalte oder None
        jahr_voll: ob der Jahreswert vollständig ist
    """
    return {
        "label": beschriftung, "werte": werte, "voll": voll_je_monat,
        "hover": hover_je_monat, "jahr_wert": jahr_wert, "jahr_voll": jahr_voll,
    }


def _zeilen_jahr_fuer_jahr(daten: dict, titel_hover: str) -> list:
    """Ein Jahr je Zeile, jüngstes oben, darunter die Ø-Zeile."""
    renditen, vollst = daten["renditen"], daten["vollstaendig"]
    zeilen = []

    def _hover(kopf):
        def _machen(monat, wert):
            if pd.isna(wert):
                return f"{monat_lang(monat)} {kopf}<br>keine Daten"
            return (f"{monat_lang(monat)} {kopf}<br>"
                    f"{titel_hover}: {fmt_pct(wert)}")
        return _machen

    for jahr in sorted(renditen.index, reverse=True):
        zeilen.append(_zeile(
            str(jahr), renditen.loc[jahr],
            lambda m, j=jahr: bool(vollst.loc[j, m]),
            _hover(str(jahr)),
            jahr_wert=daten["jahr"].loc[jahr],
            jahr_voll=bool(daten["jahr_vollstaendig"].loc[jahr]),
        ))

    schnitt = monats_durchschnitt(daten)
    if not schnitt["monate"].empty:
        # Die Ø-Zeile besteht nur aus vollen Jahren — jeder ihrer Werte ist
        # damit vollstaendig und traegt kein Sternchen.
        spanne = f"{schnitt['jahre'][0]}–{schnitt['jahre'][-1]}"
        zeilen.append(_zeile(
            DURCHSCHNITT_ZEILE, schnitt["monate"], lambda m: True,
            _hover(f"Ø {spanne}"), jahr_wert=schnitt["jahr"], jahr_voll=True,
        ))
    return zeilen


def _zeilen_bandbreite(daten: dict, band: dict, titel_hover: str) -> list:
    """Hoch / Mittel / Tief des Fensters, darunter das laufende Jahr.

    Reihenfolge wie bei Bloomberg: erst das Band, dann die Zeile, die man
    dagegen liest.
    """
    n = len(band["jahre"])
    praefix = f"{n}J"
    aktuell = band["aktuelles_jahr"]
    renditen, vollst = daten["renditen"], daten["vollstaendig"]

    def _hover_extrem(art, werte, wann):
        def _machen(monat, wert):
            if pd.isna(wert):
                return f"{monat_lang(monat)}<br>keine Daten"
            jahr = wann.loc[monat]
            zusatz = f" ({jahr})" if jahr is not None else ""
            return (f"{monat_lang(monat)}<br>{art} der {n} Jahre: "
                    f"{fmt_pct(wert)}{zusatz}")
        return _machen

    def _hover_mittel(monat, wert):
        if pd.isna(wert):
            return f"{monat_lang(monat)}<br>keine Daten"
        quote = band["trefferquote"].loc[monat]
        anteil = ("" if pd.isna(quote) else
                  f"<br>in {round(quote * n)} von {n} Jahren positiv")
        return f"{monat_lang(monat)}<br>Mittel: {fmt_pct(wert)}{anteil}"

    def _hover_aktuell(monat, wert):
        if pd.isna(wert):
            return f"{monat_lang(monat)} {aktuell}<br>noch kein Wert"
        lage = ""
        hoch, tief = band["hoch"].loc[monat], band["tief"].loc[monat]
        if pd.notna(hoch) and wert > hoch:
            lage = f"<br>über dem {n}-Jahres-Hoch"
        elif pd.notna(tief) and wert < tief:
            lage = f"<br>unter dem {n}-Jahres-Tief"
        return (f"{monat_lang(monat)} {aktuell}<br>"
                f"{titel_hover}: {fmt_pct(wert)}{lage}")

    return [
        _zeile(f"{praefix}-Hoch", band["hoch"], lambda m: True,
               _hover_extrem("Höchster", band["hoch"], band["hoch_wann"]),
               jahr_wert=band["hoch_jahr"]),
        _zeile(f"{praefix}-Mittel", band["mittel"], lambda m: True,
               _hover_mittel, jahr_wert=band["mittel_jahr"]),
        _zeile(f"{praefix}-Tief", band["tief"], lambda m: True,
               _hover_extrem("Niedrigster", band["tief"], band["tief_wann"]),
               jahr_wert=band["tief_jahr"]),
        _zeile(str(aktuell), renditen.loc[aktuell],
               lambda m: bool(vollst.loc[aktuell, m]), _hover_aktuell,
               jahr_wert=daten["jahr"].loc[aktuell],
               jahr_voll=bool(daten["jahr_vollstaendig"].loc[aktuell])),
    ]


def _heatmap_figur(zeilen: list, grenze: float) -> go.Figure:
    """Zeichnet, was sie bekommt — ohne zu wissen, was die Zeilen bedeuten."""
    z, texte, hover, beschriftungen = [], [], [], []

    for zl in zeilen:
        z_zeile, t_zeile, h_zeile = [], [], []
        for monat in range(1, 13):
            wert = zl["werte"].loc[monat]
            voll = bool(zl["voll"](monat))
            z_zeile.append(None if pd.isna(wert) else float(wert) * 100.0)
            t_zeile.append(_zellentext(wert, voll))
            h_zeile.append(zl["hover"](monat, wert))
        # Die Jahresspalte bleibt ohne Füllung (z = None) und ohne Text;
        # ihr Wert kommt als Annotation. Grund: Eine Zelle mit fehlendem
        # z-Wert rendert je nach Plotly-Fassung ihren Text nicht mit.
        z.append(z_zeile + [None])
        texte.append(t_zeile + [""])
        hover.append(h_zeile + [""])
        beschriftungen.append(zl["label"])

    hoehe_zeile = _zeilenhoehe(len(zeilen))
    schrift = min(16.0, max(11.0, hoehe_zeile / 5.0))

    fig = go.Figure(go.Heatmap(
        z=z,
        x=list(MONATSNAMEN_KURZ) + [JAHR_SPALTE],
        y=beschriftungen,
        text=texte,
        texttemplate="%{text}",
        textfont=dict(size=schrift, color=HEATMAP_TEXT),
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
    for zl in zeilen:
        wert = zl["jahr_wert"]
        if wert is None or pd.isna(wert):
            continue
        fig.add_annotation(
            x=JAHR_SPALTE, y=zl["label"],
            text=f"<b>{_zellentext(wert, zl['jahr_voll'])}</b>",
            showarrow=False, font=dict(size=schrift), xanchor="center",
        )

    fig.update_layout(
        height=round(len(zeilen) * hoehe_zeile + 150),
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


def _kennzeile_band(daten: dict, band: dict) -> str:
    """Die Zeile unter der Bandbreite — beantwortet, wofür sie gebaut ist.

    Genannt werden die Monate in Worten statt durch Symbole: „über dem Hoch"
    ist eine Aussage, kein Dreieck.
    """
    n = len(band["jahre"])
    aktuell = band["aktuelles_jahr"]
    zeile = daten["renditen"].loc[aktuell]
    voll = daten["vollstaendig"].loc[aktuell]

    ueber, unter, ueber_mittel, gezaehlt = [], [], 0, 0
    for monat in range(1, 13):
        wert = zeile.loc[monat]
        if pd.isna(wert) or not bool(voll.loc[monat]):
            continue
        gezaehlt += 1
        hoch, tief = band["hoch"].loc[monat], band["tief"].loc[monat]
        mittel = band["mittel"].loc[monat]
        if pd.notna(hoch) and wert > hoch:
            ueber.append(monat_lang(monat))
        elif pd.notna(tief) and wert < tief:
            unter.append(monat_lang(monat))
        if pd.notna(mittel) and wert > mittel:
            ueber_mittel += 1

    if not gezaehlt:
        return f"Für {aktuell} liegt noch kein vollständiger Monat vor."

    teile = [f"{aktuell} gegen {n} Jahre"]
    if ueber:
        teile.append("über dem Hoch: " + ", ".join(ueber))
    if unter:
        teile.append("unter dem Tief: " + ", ".join(unter))
    if not ueber and not unter:
        teile.append("kein Monat außerhalb der Bandbreite")
    teile.append(f"{ueber_mittel} von {gezaehlt} Monaten über dem Mittel")
    return " · ".join(teile)


def _zeichne_matrix(daten, grenze, hover_titel, ist_differenz, schluessel,
                    ansicht=ANSICHT_JAHRE, band_jahre=None):
    """Chart, Kennzeile, Fußnoten und der Haken für die Tabelle."""
    if daten["renditen"].empty or not daten["renditen"].notna().any().any():
        st.caption("Für diese Auswahl gibt es keine Monatsrenditen.")
        return

    band = bandbreite(daten, band_jahre) if ansicht == ANSICHT_BAND else None
    if ansicht == ANSICHT_BAND and not band["jahre"]:
        volle = int(daten["jahr_vollstaendig"].sum())
        st.caption(
            f"Die Bandbreite braucht mindestens {BAND_MIN_JAHRE} "
            f"abgeschlossene Kalenderjahre vor dem laufenden — hier "
            f"{'ist es nur eines' if volle == 1 else f'sind es {volle}'}. "
            "Bei einem einzigen Jahr wären Hoch, Mittel und Tief dieselbe "
            f"Zahl. Die Ansicht „{ANSICHT_JAHRE}“ zeigt die Daten trotzdem.")
        return

    if band is not None:
        zeilen = _zeilen_bandbreite(daten, band, hover_titel)
    else:
        zeilen = _zeilen_jahr_fuer_jahr(daten, hover_titel)

    st.plotly_chart(_heatmap_figur(zeilen, grenze),
                    config={"displayModeBar": False}, key=schluessel)

    if band is not None:
        st.caption(_kennzeile_band(daten, band))
    else:
        st.caption(_kennzeile(daten, ist_differenz))

    if _hat_unvollstaendige(daten):
        # Seit der Zeitraum-Kopplung (14.08.2026) kann ein angebrochener
        # Monat auch vom RAND DES ZEITRAUMS kommen, nicht mehr nur von der
        # Auflage oder vom laufenden Monat. Die Fußnote muss das nennen.
        st.caption(
            f"{UNVOLLSTAENDIG} = angebrochener Monat (Auflage, Rand des "
            "Zeitraums oder laufender Monat). Zählt in den Kennzahlen nicht "
            "mit.")

    if band is not None:
        jahre = band["jahre"]
        st.caption(
            f"Bandbreite über die {len(jahre)} abgeschlossenen Kalenderjahre "
            f"{jahre[0]}–{jahre[-1]}; {band['aktuelles_jahr']} ist bewusst "
            "nicht darin enthalten, sonst verglichen sich die Zahlen mit sich "
            "selbst. In den Zeilen Hoch und Tief steht je Monat das Extrem "
            "**dieses Monats**, in der Jahresspalte das Extrem **des "
            "Jahres** — beides sind Extreme, sie stammen aber nicht "
            "zwangsläufig aus demselben Jahr. Nur die Mittel-Zeile ergibt "
            "verkettet ihren Jahreswert.")
    else:
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
                        von=None, bis=None,
                        band_von=None, band_bis=None, band_jahre=None):
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
        von, bis: Zeitraum-Grenzen für „Jahr für Jahr"; None heißt „Rand der
            jeweiligen Reihe"
        band_von, band_bis, band_jahre: eigenes Fenster für die Bandbreite

    DER ZUSCHNITT PASSIERT HIER UND NICHT VORHER (14.08.2026). Die Heatmap
    folgt seit der Sichtprüfung dem oben gewählten Zeitraum — aber sie
    bekommt die UNGESCHNITTENE Reihe und schneidet selbst. Der Grund ist der
    Inner-Join in `streamlit_app.py`: Sobald das Vergleichsportfolio aktiv
    ist, sind `df1`/`df2` dort auf die gemeinsamen Handelstage reduziert, und
    `mind` ist die Schnittmenge beider Historien. "Muster ausgewogen cVV"
    (ab 2009) gegen "Comdirect 100" (ab 2024) verlöre bei „Seit Auflage"
    fünfzehn Jahre, ohne dass die Auswahl das nahelegt.

    Mit `von=None` beginnt deshalb JEDE Reihe an ihrem eigenen ersten Monat.

    WARUM DIE BANDBREITE EIN EIGENES FENSTER BRAUCHT: Sie denkt in ganzen
    KALENDERJAHREN, der Zuschnitt oben in Tagen. Bei „5 Jahre" schneidet der
    tagbasierte Zuschnitt am 21.07.2021 — 2021 ist damit unvollständig und
    fiele aus dem Band, das dann nur vier Jahre hätte, obwohl „5J" darüber
    stünde. Deshalb bekommt sie `band_jahre` und schneidet allenfalls nach
    `band_von`/`band_bis` (nur beim eigenen Zeitraum gesetzt).
    """
    voll_df = ts_df
    ts_df = _zuschnitt(ts_df, von, bis)
    if ts_df is None or len(ts_df) == 0:
        st.markdown("---")
        st.subheader("Monatsrenditen")
        st.caption(f"Für {label} liegen im gewählten Zeitraum keine Daten.")
        return

    st.markdown("---")
    st.subheader("Monatsrenditen")

    if "p_heat_ansicht" not in st.session_state:
        st.session_state["p_heat_ansicht"] = ANSICHT_JAHRE
    # required=True: Ein Klick auf das aktive Segment darf nicht abwaehlen,
    # sonst gaebe es den Zustand "keine Ansicht gewaehlt" (wie bei p_zeitraum).
    ansicht = st.segmented_control(
        "Ansicht", list(ANSICHTEN), key="p_heat_ansicht", required=True,
        label_visibility="collapsed",
        help=(f"„{ANSICHT_JAHRE}“ zeigt jedes Jahr als eigene Zeile. "
              f"„{ANSICHT_BAND}“ stellt dem laufenden Jahr Hoch, Mittel und "
              "Tief der Vorjahre gegenüber — je Kalendermonat."))

    # Die beiden Ansichten rechnen auf verschieden geschnittenen Reihen: „Jahr
    # für Jahr" auf dem tagbasierten Zuschnitt, die Bandbreite auf dem eigenen
    # Fenster (siehe Docstring). Ab hier arbeitet alles auf `basis`.
    band = ansicht == ANSICHT_BAND
    basis = _zuschnitt(voll_df, band_von, band_bis) if band else ts_df
    v_von, v_bis = (band_von, band_bis) if band else (von, bis)

    st.caption(f"{basis.index.min():%m/%Y} – {basis.index.max():%m/%Y}, "
               f"nach Kosten{mwst_suffix}.")

    absolut = monatsrenditen(basis, fee_dec)
    _zeichne_matrix(absolut, HEATMAP_GRENZE_ABSOLUT, label,
                    False, f"heat_abs_{schluessel}",
                    ansicht=ansicht, band_jahre=band_jahre)

    if gegen_benchmark:
        st.markdown(f"**Differenz zur Benchmark ({benchmark_name})**")
        if not ("ret_bm" in basis.columns and has_benchmark(basis["ret_bm"])):
            st.caption(
                f"Für {label} ist kein Vergleichsmaßstab (Benchmark) "
                "hinterlegt — es gibt deshalb keine Differenz zu zeigen.")
        else:
            bm = monatsrenditen(basis, 0.0, spalte="ret_bm", nach_kosten=False)
            diff = monatsrenditen_differenz(absolut, bm)
            st.caption(
                "Geometrisch gerechnet, damit die Monate einer Zeile genau "
                f"den Jahreswert ergeben. Die Strategie steht nach "
                f"Kosten{mwst_suffix}, die Benchmark ohne — das Honorar "
                "steckt also in der Differenz.")
            _zeichne_matrix(diff, HEATMAP_GRENZE_DIFFERENZ,
                            f"{label} gegen {benchmark_name}",
                            True, f"heat_bm_{schluessel}",
                            ansicht=ansicht, band_jahre=band_jahre)

    if vergleich is not None:
        v_label, v_df, v_fee = vergleich
        v_df = _zuschnitt(v_df, v_von, v_bis)
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
                        f"heat_cmp_{schluessel}",
                        ansicht=ansicht, band_jahre=band_jahre)


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
