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

import math

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from modules.analytics import (
    BAND_DUENN_UNTER, BAND_JAHRE, RISIKO_PERIODEN, ROLL_FENSTER_TAGE,
    _perioden_start,
    bandbreite, calc_daily_returns_after_fee, has_benchmark,
    heatmap_kennzahlen, monats_durchschnitt, monatsrenditen,
    monatsrenditen_differenz, risiko_perioden, rollierende_vola,
)
from modules.formats import (
    EMPTY_VALUE, MONATSNAMEN_KURZ, fmt_date_de, fmt_pct, fmt_ratio,
    monat_kurz, monat_lang,
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

# Untergrenze der datengetriebenen Farbskala (siehe _grenze_aus_daten).
BAND_GRENZE_MIN = 0.01


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


def _zellentext_band(wert, vollstaendig: bool) -> str:
    """Zellbeschriftung der Bandbreite: zwei Stellen, KEIN Pluszeichen.

    Abweichend von der Jahr-für-Jahr-Ansicht (Festlegung Philip, 14.08.2026,
    nach der Bloomberg-Vorlage). Zwei Stellen sind hier bezahlbar, weil die
    Ansicht nur zwölf Spalten hat statt dreizehn; und ohne Pluszeichen liest
    sich eine Zahlenkolonne ruhiger, weil nur die Minuszeichen hervortreten.
    """
    if wert is None or pd.isna(wert):
        return ""
    text = f"{float(wert) * 100:.2f}".replace(".", ",")
    return text + ("" if vollstaendig else UNVOLLSTAENDIG)


def _grenze_aus_daten(zeilen: list) -> float:
    """Symmetrische Skalengrenze aus den gezeigten Werten (Dezimal).

    Die Bandbreite färbt datengetrieben statt fest (Festlegung Philip,
    14.08.2026): Ihre Zeilen sind Extremwerte, die bei festen ±3 % fast
    durchgehend aussättigen und dann keine Abstufung mehr zeigen.

    Aufgerundet auf halbe Prozentpunkte, damit die Legende glatte Zahlen
    trägt. Untergrenze ±1 %: Eine sehr ruhige Reihe bekäme sonst für
    Zehntelprozente volle Farbe und sähe dramatischer aus, als sie ist.
    """
    werte = []
    for zl in zeilen:
        for monat in range(1, 13):
            wert = zl["werte"].loc[monat]
            if pd.notna(wert):
                werte.append(abs(float(wert)))
    if not werte:
        return BAND_GRENZE_MIN
    aufgerundet = math.ceil(max(werte) * 200.0) / 200.0   # halbe Prozentpunkte
    return max(BAND_GRENZE_MIN, aufgerundet)


def _colorbar(grenze: float, gesaettigt: bool = True) -> dict:
    """Waagerechte Farblegende unter der Matrix.

    Bei fester Skala tragen die Enden "≤" und "≥": Werte jenseits der Grenze
    sättigen aus, und das gehört benannt statt verschwiegen — ohne diese
    beiden Zeichen sähe es so aus, als wäre der dunkelste Ton der Höchstwert.

    Bei einer aus den Daten abgeleiteten Skala (`gesaettigt=False`) entfallen
    sie, weil dort nichts abgeschnitten wird: Die Grenze IST der größte
    vorkommende Betrag.
    """
    halb = grenze / 2.0
    links, rechts = fmt_pct(-grenze, 1), fmt_pct(grenze, 1)
    return dict(
        orientation="h", x=0.5, xanchor="center", y=-0.18, yanchor="top",
        len=0.55, thickness=12, outlinewidth=0,
        ticks="outside", ticklen=4, tickfont=dict(size=10),
        tickvals=[-grenze * 100, -halb * 100, 0.0, halb * 100, grenze * 100],
        # Alle fuenf Beschriftungen durch fmt_pct: Eine von Hand gesetzte
        # Null ("0 %") stand sonst als einzige mit anderem Abstand da.
        ticktext=[f"≤ {links}" if gesaettigt else links,
                  fmt_pct(-halb, 1), fmt_pct(0.0, 1), fmt_pct(halb, 1),
                  f"≥ {rechts}" if gesaettigt else rechts],
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


def _monatszeitraum(ts_df, jahr, monat):
    """(Stand vor dem Monat, letzter Tag im Monat) als Text — für den Hover.

    Eine Monatsrendite misst vom SCHLUSS des Vormonats bis zum Schluss des
    Monats: Die erste Tagesrendite des März ist die vom 28.02.-Schluss auf
    den 01.03.-Schluss. Der Hover nennt deshalb den letzten Datenpunkt VOR
    dem Monat, nicht den ersten IM Monat — sonst suggerierte er einen um
    einen Tag zu kurzen Zeitraum.
    """
    if ts_df is None or len(ts_df) == 0:
        return None
    anfang = pd.Timestamp(int(jahr), int(monat), 1)
    ende = anfang + pd.offsets.MonthEnd(0)
    im_monat = ts_df.loc[anfang:ende]
    if len(im_monat) == 0:
        return None
    davor = ts_df.loc[:anfang - pd.Timedelta(days=1)]
    stand = davor.index.max() if len(davor) else None
    letzter = im_monat.index.max()
    if stand is None:
        return f"bis {fmt_date_de(letzter)}"
    return f"{fmt_date_de(stand)} – {fmt_date_de(letzter)}"


def _zeilen_bandbreite(daten: dict, band: dict, titel_hover: str,
                       ts_df=None) -> list:
    """Hoch / Mittel / Tief des Fensters, darunter das laufende Jahr.

    Reihenfolge wie bei Bloomberg: erst das Band, dann die Zeile, die man
    dagegen liest. Keine Jahresspalte — die Vorlage hat zwölf Spalten.
    """
    jahre = band["jahre"]
    n = len(jahre)
    praefix = f"{n}J"
    aktuell = band["aktuelles_jahr"]
    renditen, vollst = daten["renditen"], daten["vollstaendig"]
    spanne = f"{jahre[0]}–{jahre[-1]}" if n > 1 else f"{jahre[0]}"

    def _hover_extrem(art, wann):
        def _machen(monat, wert):
            if pd.isna(wert):
                return f"{monat_lang(monat)}<br>keine Vergleichswerte"
            jahr = wann.loc[monat]
            zeilen = [f"<b>{monat_lang(monat)} — {art} von {spanne}</b>",
                      f"Rendite: {fmt_pct(wert)}"]
            if jahr is not None:
                zeilen.append(f"Jahr: {jahr}")
                zeitraum = _monatszeitraum(ts_df, jahr, monat)
                if zeitraum:
                    zeilen.append(f"Zeitraum: {zeitraum}")
            return "<br>".join(zeilen)
        return _machen

    def _hover_mittel(monat, wert):
        if pd.isna(wert):
            return f"{monat_lang(monat)}<br>keine Vergleichswerte"
        anz = int(band["anzahl"].loc[monat])
        geo = band["mittel_geo"].loc[monat]
        quote = band["trefferquote"].loc[monat]
        zeilen = [f"<b>{monat_lang(monat)} — Mittel {spanne}</b>",
                  f"Durchschnitt: {fmt_pct(wert)} (arithmetisch)"]
        if pd.notna(geo):
            # Die Ø-Zeile der anderen Ansicht rechnet geometrisch. Beide
            # Zahlen hier zu nennen ist billiger als ein unerklaerter
            # Unterschied zwischen zwei Ansichten desselben Werkzeugs.
            zeilen.append(f"geometrisch: {fmt_pct(geo)}")
        zeilen.append(f"Anzahl Werte: {anz}")
        if pd.notna(quote):
            zeilen.append(f"davon positiv: {round(quote * anz)}")
        return "<br>".join(zeilen)

    def _hover_aktuell(monat, wert):
        if pd.isna(wert):
            return f"{monat_lang(monat)} {aktuell}<br>noch kein Wert"
        zeilen = [f"<b>{monat_lang(monat)} {aktuell}</b>",
                  f"{titel_hover}: {fmt_pct(wert)}"]
        zeitraum = _monatszeitraum(ts_df, aktuell, monat)
        if zeitraum:
            zeilen.append(f"Zeitraum: {zeitraum}")
        if not bool(vollst.loc[aktuell, monat]):
            zeilen.append("angebrochener Monat")
        hoch, tief = band["hoch"].loc[monat], band["tief"].loc[monat]
        if pd.notna(hoch) and wert > hoch:
            zeilen.append(f"<b>über dem {praefix}-Hoch</b>")
        elif pd.notna(tief) and wert < tief:
            zeilen.append(f"<b>unter dem {praefix}-Tief</b>")
        return "<br>".join(zeilen)

    return [
        _zeile(f"{praefix} Hoch", band["hoch"], lambda m: True,
               _hover_extrem("Hoch", band["hoch_wann"])),
        _zeile(f"{praefix} Mittel", band["mittel"], lambda m: True,
               _hover_mittel),
        _zeile(f"{praefix} Tief", band["tief"], lambda m: True,
               _hover_extrem("Tief", band["tief_wann"])),
        _zeile(str(aktuell), renditen.loc[aktuell],
               lambda m: bool(vollst.loc[aktuell, m]), _hover_aktuell),
    ]


def _heatmap_figur(zeilen: list, grenze: float, mit_jahresspalte: bool = True,
                   zellentext=None, gesaettigt: bool = True) -> go.Figure:
    """Zeichnet, was sie bekommt — ohne zu wissen, was die Zeilen bedeuten.

    Args:
        zeilen: Liste von `_zeile`-Dicts, in LESERICHTUNG (erste Zeile oben)
        grenze: Skalengrenze als Dezimal, symmetrisch um null
        mit_jahresspalte: 13. Spalte „Jahr"; die Bandbreite hat sie nicht
        zellentext: Formatierer(wert, vollstaendig) -> str; None nimmt den
            Standard mit Vorzeichen und einer Nachkommastelle
        gesaettigt: ob Werte jenseits der Grenze abgeschnitten werden — nur
            dann trägt die Legende „≤" und „≥"

    ZWEI DINGE, DIE HIER NICHT DEM ZUFALL ÜBERLASSEN WERDEN (14.08.2026,
    nach einem Renderfehler in der Bandbreiten-Ansicht):

    1. **Der Achsentyp wird gesetzt, nicht geraten.** Ohne `type="category"`
       entscheidet Plotly anhand der Werte. Die Bandbreite hatte y-Labels wie
       ["17J-Hoch", "17J-Mittel", "17J-Tief", "2026"] — drei echte Strings
       und einen zahlartigen. Sobald "2026" als Zahl gelesen wird, spannt die
       Achse bis 2026 und die vier Kategorien fallen zu einem Streifen am
       unteren Rand zusammen. Genau so sah es aus.

    2. **Annotationen sitzen auf INDIZES, nicht auf Beschriftungen.** Ein
       `y="2026"` verlangt von Plotly eine zweite Namensauflösung gegen die
       Kategorienliste — und die kann scheitern, ohne dass jemand es merkt.
       Ein `y=2` kann das nicht. Dieselbe Klasse wie das nicht greifende
       `majorTimeUnit` (#49).

    REIHENFOLGE: Bei `go.Heatmap` gehört `z[0]` zu `y[0]`, und das wird
    UNTEN gezeichnet. `zeilen` kommt aber in Leserichtung herein (erste Zeile
    oben). Deshalb wird hier einmal umgedreht — bewusst und an genau einer
    Stelle, statt die Aufrufer rückwärts denken zu lassen.
    """
    if zellentext is None:
        zellentext = _zellentext

    spalten = list(MONATSNAMEN_KURZ)
    if mit_jahresspalte:
        spalten = spalten + [JAHR_SPALTE]

    # Von oben nach unten gedacht, von unten nach oben gezeichnet.
    von_unten = list(reversed(zeilen))

    z, texte, hover, beschriftungen = [], [], [], []
    for zl in von_unten:
        z_zeile, t_zeile, h_zeile = [], [], []
        for monat in range(1, 13):
            wert = zl["werte"].loc[monat]
            voll = bool(zl["voll"](monat))
            z_zeile.append(None if pd.isna(wert) else float(wert) * 100.0)
            t_zeile.append(zellentext(wert, voll))
            h_zeile.append(zl["hover"](monat, wert))
        if mit_jahresspalte:
            # Die Jahresspalte bleibt ohne Füllung (z = None) und ohne Text;
            # ihr Wert kommt als Annotation. Grund: Eine Zelle mit fehlendem
            # z-Wert rendert je nach Plotly-Fassung ihren Text nicht mit.
            z_zeile.append(None)
            t_zeile.append("")
            h_zeile.append("")
        z.append(z_zeile)
        texte.append(t_zeile)
        hover.append(h_zeile)
        beschriftungen.append(zl["label"])

    hoehe_zeile = _zeilenhoehe(len(zeilen))
    schrift = min(16.0, max(11.0, hoehe_zeile / 5.0))

    fig = go.Figure(go.Heatmap(
        z=z,
        x=spalten,
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
        colorbar=_colorbar(grenze, gesaettigt),
    ))

    # Jahreswerte als Annotationen — garantiert farblos und damit ohne
    # Einfluss auf die Skala der Monate. y ist der INDEX in `beschriftungen`.
    if mit_jahresspalte:
        for i, zl in enumerate(von_unten):
            wert = zl["jahr_wert"]
            if wert is None or pd.isna(wert):
                continue
            fig.add_annotation(
                x=len(spalten) - 1, y=i,
                text=f"<b>{zellentext(wert, zl['jahr_voll'])}</b>",
                showarrow=False, font=dict(size=schrift), xanchor="center",
            )

    fig.update_layout(
        height=round(len(zeilen) * hoehe_zeile + 150),
        margin=dict(l=10, r=10, t=10, b=60),
        xaxis=dict(type="category", categoryorder="array",
                   categoryarray=spalten, side="top",
                   fixedrange=True, showgrid=False, ticks=""),
        yaxis=dict(type="category", categoryorder="array",
                   categoryarray=beschriftungen,
                   fixedrange=True, showgrid=False, ticks=""),
        separators=",.",
    )
    return fig


def _zeilen_tabelle(zeilen: list, mit_jahresspalte: bool = True,
                    zellentext=None) -> pd.DataFrame:
    """Dieselben Zahlen als kopierbare Tabelle.

    Aus einem Plotly-Chart bekommt man Werte nicht heraus; Berater ziehen sie
    aber gern nach Excel. Dasselbe Muster wie beim Balken-Chart.

    Gebaut aus DENSELBEN `zeilen` wie die Figur (14.08.2026), nicht aus den
    Rohdaten: Vorher gab es zwei Wege zu denselben Zahlen, und der zweite
    hätte jede Änderung an der Zeilenzusammenstellung verpasst.

    Ueber monat_kurz() und nicht MONATSNAMEN_KURZ[monat - 1]: Die Spalten
    muessen exakt denen der Heatmap entsprechen, und die Index-Arithmetik ist
    genau die Stelle, an der ein Off-by-one entstuende.
    """
    if zellentext is None:
        zellentext = _zellentext
    spalten = [""] + list(MONATSNAMEN_KURZ)
    if mit_jahresspalte:
        spalten = spalten + ["Gesamt"]

    def _text(wert, voll):
        gesetzt = zellentext(wert, voll)
        return gesetzt if gesetzt else EMPTY_VALUE

    ausgabe = []
    for zl in zeilen:
        zeile = {"": zl["label"]}
        for monat in range(1, 13):
            zeile[monat_kurz(monat)] = _text(zl["werte"].loc[monat],
                                             bool(zl["voll"](monat)))
        if mit_jahresspalte:
            zeile["Gesamt"] = _text(zl["jahr_wert"], zl["jahr_voll"])
        ausgabe.append(zeile)

    return pd.DataFrame(ausgabe, columns=spalten)


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
                    ansicht=ANSICHT_JAHRE, ts_df=None):
    """Chart, Kennzeile, Fußnoten und der Haken für die Tabelle."""
    if daten["renditen"].empty or not daten["renditen"].notna().any().any():
        st.caption("Für diese Auswahl gibt es keine Monatsrenditen.")
        return

    band = bandbreite(daten) if ansicht == ANSICHT_BAND else None
    if band is not None and not band["jahre"]:
        st.caption(
            "Für die Bandbreite fehlt ein abgeschlossenes Vergleichsjahr vor "
            f"dem laufenden. Die Ansicht „{ANSICHT_JAHRE}“ zeigt die Daten "
            "trotzdem.")
        return

    if band is not None:
        zeilen = _zeilen_bandbreite(daten, band, hover_titel, ts_df)
        grenze = _grenze_aus_daten(zeilen)
        figur = _heatmap_figur(zeilen, grenze, mit_jahresspalte=False,
                               zellentext=_zellentext_band, gesaettigt=False)
    else:
        zeilen = _zeilen_jahr_fuer_jahr(daten, hover_titel)
        figur = _heatmap_figur(zeilen, grenze)

    st.plotly_chart(figur, config={"displayModeBar": False}, key=schluessel)

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
        spanne = f"{jahre[0]}–{jahre[-1]}" if len(jahre) > 1 else f"{jahre[0]}"
        teile = [
            f"Vergleichsfenster: die letzten {BAND_JAHRE} Kalenderjahre vor "
            f"{band['aktuelles_jahr']}, hier {spanne} mit {len(jahre)} "
            f"{'Jahr' if len(jahre) == 1 else 'Jahren'} verwertbarer Daten. "
            f"{band['aktuelles_jahr']} ist bewusst nicht enthalten — sonst "
            "verglichen sich die Zahlen mit sich selbst.",
            "Mittel = arithmetischer Durchschnitt der gültigen Werte je "
            "Monat. Jeder Monat rechnet für sich; fehlt ein einzelner, fällt "
            "nur er weg.",
            f"Die Farbskala läuft hier symmetrisch bis {fmt_pct(grenze, 1)} "
            "und richtet sich nach den gezeigten Werten — sie ist deshalb "
            "zwischen zwei Strategien nicht vergleichbar.",
            "Die Zeitraum-Auswahl oben wirkt in dieser Ansicht nicht.",
        ]
        if len(jahre) < BAND_DUENN_UNTER:
            teile.insert(1, (
                f"**Nur {len(jahre)} Vergleichsjahr"
                f"{'' if len(jahre) == 1 else 'e'}** — "
                + ("Hoch, Mittel und Tief sind damit dieselbe Zahl; eine "
                   "Bandbreite entsteht erst ab zwei Jahren."
                   if len(jahre) == 1 else
                   "die Spanne ist der Abstand von zwei Beobachtungen und "
                   "trägt noch wenig.")))
        for teil in teile:
            st.caption(teil)
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
        st.dataframe(_zeilen_tabelle(zeilen, mit_jahresspalte=band is None,
                                     zellentext=(_zellentext_band if band
                                                 else _zellentext)),
                     hide_index=True)


def zeitraum_fuer_heatmap(jahre, eigener, sd, ed, maxd):
    """Zeitraum-Grenzen der Ansicht „Jahr für Jahr" aus der Schnellwahl.

    Args:
        jahre: Anzahl Jahre aus der Schnellwahl; None für „Seit Auflage"
        eigener: True, wenn der Nutzer eigene Kalenderdaten eingetragen hat
        sd, ed: diese eigenen Daten
        maxd: letzter Datenpunkt (Datenstand)

    Returns:
        (von, bis, gerundet) — `von`/`bis` als date oder None,
        `gerundet` sagt, ob auf ganze Kalenderjahre ausgerichtet wurde.

    WARUM AUF KALENDERJAHRE GERUNDET WIRD (14.08.2026, Philip gemeldet):
    Vorher rechnete die Ableitung `maxd − N Jahre`. Bei Datenstand 21.07.2026
    schnitt „3 Jahre" damit am 21.07.2023 — Januar bis Juni 2023 fielen aus
    der Matrix, Juli 2023 blieb als Elf-Tage-Rumpfmonat stehen. Sechs leere
    Kacheln, und zwar bei JEDER Schnellwahl, weil der Schnitt immer im selben
    Monat landet wie der Datenstand.

    Eine leere Kachel bedeutet in dieser Matrix aber schon etwas: „die
    Strategie lief da noch nicht" (bei comdirect vor 03/2024). Hier bedeutete
    dieselbe Kachel „es gibt Daten, der Zeitraum blendet sie aus" — zwei
    Bedeutungen, ein Aussehen. Dieselbe Klasse wie ein Fehlwert, der aussieht
    wie ein Messwert (#46).

    Der Zuschnitt auf den Jahresanfang kostet nichts: gleiche Zeilenzahl
    (nachgemessen für 1/3/5/10 Jahre), null Lücken, und das älteste Jahr
    zählt danach als vollständig in die Ø-Zeile.

    In Kauf genommen: „3 Jahre" zeigt 01/2023–07/2026, also ein halbes Jahr
    mehr als die Kennzahlen darüber, die taggenau rechnen. Deshalb liefert
    die Funktion `gerundet` mit — die Oberfläche sagt es dann dazu.

    EIN EIGENER ZEITRAUM WIRD WÖRTLICH GENOMMEN. Wer zwei Kalenderdaten
    eintippt, meint genau diese; entstehen dabei Randmonate, ist das die
    Folge der eigenen Eingabe und keine Überraschung.

    NICHT auf den Datenbeginn geklemmt: `_zuschnitt` schneidet ohnehin nur,
    was vorhanden ist, und eine jüngere Strategie beginnt weiterhin an ihrem
    eigenen ersten Monat.

    Diese Ableitung stand bis zum 14.08.2026 INLINE in `streamlit_app.py` und
    war damit für keinen Prüfstein erreichbar — obwohl zehn Testschritte auf
    dieser Heatmap liegen. Genau deshalb ist der Fehler durchgerutscht.
    Prüfstein: tests/test_monatsrenditen.py
    """
    if eigener:
        return sd, ed, False
    if jahre is None:
        return None, None, False
    erstes_jahr = pd.Timestamp(maxd).year - int(jahre)
    return pd.Timestamp(erstes_jahr, 1, 1).date(), None, True


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
                        von=None, bis=None, gerundet=False):
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
            jeweiligen Reihe". Die Bandbreite ignoriert sie (siehe unten).

    DER ZUSCHNITT PASSIERT HIER UND NICHT VORHER (14.08.2026). Die Heatmap
    folgt seit der Sichtprüfung dem oben gewählten Zeitraum — aber sie
    bekommt die UNGESCHNITTENE Reihe und schneidet selbst. Der Grund ist der
    Inner-Join in `streamlit_app.py`: Sobald das Vergleichsportfolio aktiv
    ist, sind `df1`/`df2` dort auf die gemeinsamen Handelstage reduziert, und
    `mind` ist die Schnittmenge beider Historien. "Muster ausgewogen cVV"
    (ab 2009) gegen "Comdirect 100" (ab 2024) verlöre bei „Seit Auflage"
    fünfzehn Jahre, ohne dass die Auswahl das nahelegt.

    Mit `von=None` beginnt deshalb JEDE Reihe an ihrem eigenen ersten Monat.

    DIE BANDBREITE IGNORIERT DEN ZEITRAUM (Festlegung Philip, 14.08.2026).
    Sie nimmt immer die letzten `BAND_JAHRE` Kalenderjahre vor dem laufenden
    und rechnet auf der ungeschnittenen Reihe. Grund: Ihre Zeilen heißen
    „5J Hoch/Mittel/Tief", und eine Beschriftung, die eine Zahl behauptet,
    muss sie halten können. Ein tagbasierter Zuschnitt bei „5 Jahre" schnitte
    am 21.07.2021 — 2021 wäre unvollständig und das Band hätte vier Jahre.
    Eine Caption sagt in der Ansicht ausdrücklich, dass die Auswahl oben hier
    nicht wirkt.
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

    # „Jahr für Jahr" rechnet auf dem Zeitraum-Zuschnitt, die Bandbreite auf
    # der vollen Reihe (siehe Docstring). Ab hier arbeitet alles auf `basis`.
    band = ansicht == ANSICHT_BAND
    basis = voll_df if band else ts_df
    v_von, v_bis = (None, None) if band else (von, bis)

    # Der Rundungshinweis ist nicht kosmetisch: Der Kennzahlen-Block oben
    # nennt seinen eigenen Zeitraum (taggenau). Ohne diesen Satz stuenden
    # zwei verschiedene Spannen unkommentiert untereinander.
    zusatz = ("" if band or not gerundet else
              " Die Auswahl oben ist hier auf ganze Kalenderjahre gerundet, "
              "damit keine angeschnittenen Jahreszeilen entstehen.")
    st.caption(f"{basis.index.min():%m/%Y} – {basis.index.max():%m/%Y}, "
               f"nach Kosten{mwst_suffix}.{zusatz}")

    absolut = monatsrenditen(basis, fee_dec)
    _zeichne_matrix(absolut, HEATMAP_GRENZE_ABSOLUT, label,
                    False, f"heat_abs_{schluessel}",
                    ansicht=ansicht, ts_df=basis)

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
                            ansicht=ansicht, ts_df=basis)

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
                        ansicht=ansicht, ts_df=v_df)


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


def zeitraum_hinweis(reihen):
    """Ein Satz, der die festen Perioden der Tabellen konkret verortet.

    Args:
        reihen: Liste, deren zweites Element je Eintrag die Zeitreihe ist —
            passt auf die 3er- wie auf die 5er-Form von `_analyse_reihen`.

    Returns:
        Der Hinweissatz, oder "" wenn keine Reihe Daten hat.

    WARUM ES DIESEN SATZ GIBT (Audit-Befund B4, 14.08.2026): Auf einem
    Bildschirm bedeutet „3 Jahre" an drei Stellen drei verschiedene Spannen.

        Kennzahlen-Block   21.07.2023   taggenau ab Datenstand
        Heatmap            01.01.2023   auf Kalenderjahre gerundet
        Risiko/Drawdown    22.07.2023   taggenau, eigene feste Perioden

    Keine davon ist falsch, und die Heatmap nennt ihre Rundung bereits. Was
    fehlte, war die dritte Angabe: Die Tabellen sagten zwar, dass die
    Auswahl oben nicht wirkt — aber nicht, worauf sie sich stattdessen
    beziehen. Eine Zahl, die der Zahl daneben widerspricht, ohne dass
    jemand den Unterschied benennt, ist genau das Muster aus #52.

    Die Periodengrenze kommt aus `_perioden_start`, damit hier keine zweite
    Fassung derselben Logik entsteht.

    Prüfstein: tests/test_risiko.py, Schritt 7
    """
    staende = [df.index.max() for _, df, *_ in reihen
               if df is not None and len(df)]
    if not staende:
        return ""
    stand = max(staende)
    beginn = _perioden_start(stand, "3 Jahre") + pd.Timedelta(days=1)
    return (f" Gezählt wird taggenau ab dem Datenstand "
            f"{stand:%d.%m.%Y} — „3 Jahre“ meint hier "
            f"{beginn:%d.%m.%Y} bis {stand:%d.%m.%Y}.")


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
               "selbst die Zeiträume. Die Auswahl oben wirkt hier nicht."
               + zeitraum_hinweis(reihen))

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
        "Verhältnis; beide entfallen ohne hinterlegte Benchmark. "
        "**Beide vergleichen die Strategie nach Kosten mit der Benchmark "
        "ohne Kosten** — so, wie der Kunde es erlebt. Das Honorar steckt "
        "damit in der Mehrrendite und drückt die Information Ratio; als "
        "Maß für die reine Managementleistung fiele sie günstiger aus.")


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
        "Historie, bleibt er leer. Die Zeilen sind selbst die Zeiträume; "
        "die Auswahl oben wirkt hier nicht."
        + zeitraum_hinweis(reihen))
