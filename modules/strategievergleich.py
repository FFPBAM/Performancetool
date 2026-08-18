"""
modules/strategievergleich.py — dritte Ansicht: die Strategien im
Risiko-Rendite-Raum (NEU 18.08.2026).

Die beiden bestehenden Ansichten zeigen IMMER eine Strategie (plus optional
ein Vergleichsportfolio). Die Frage, die im Kundengespräch als nächstes kommt
— "und wo steht diese Strategie im Vergleich zu unseren anderen?" — konnte
das Werkzeug bis heute nicht beantworten.

Dieses Modul ZEICHNET nur. Jede Zahl kommt aus `modules/analytics.py`
(`risiko_perioden`), jede Formatierung aus `modules/formats.py`. Hier steht
keine Mathematik — die Lehre aus Backlog B, E und F.

WAS DIESE ANSICHT NICHT IST: eine Effizienzlinie nach Markowitz. Sie
POSITIONIERT die Strategien, sie optimiert nicht. Eine Effizienzlinie
bräuchte eine Kovarianzmatrix und die Annahme, dass man beliebig zwischen den
Strategien mischen kann — und sie suggeriert das dann auch. Ein Kunde bekommt
EINE Vermögensverwaltung, keinen Mix aus dreien (Doku §10.9). Entschieden mit
Philip am 18.08.2026; wer die Linie später doch will, klärt vorher, was sie
dem Berater sagen soll.

────────────────────────────────────────────────────────────────────────────
DIE ZENTRALE ENTSCHEIDUNG DIESER ANSICHT IST DER ZEITRAUM
────────────────────────────────────────────────────────────────────────────

Die 19 Strategien haben zwischen 1,7 und 17,6 Jahren Historie. Eine
Punktwolke, die jede Strategie "seit Auflage" einzeichnet, zeigt deshalb
nicht, welche besser ist, sondern WANN SIE AUFGELEGT WURDE: Die alten Reihen
tragen Finanzkrise, Corona und 2022 mit, die jungen nur den Aufschwung seit
2023. Gemessen am 18.08.2026:

    cVV dynamic     seit Auflage Rang  4  |  über 3 gemeinsame Jahre Rang 14
    cVV ausgewogen  seit Auflage Rang 11  |  über 3 gemeinsame Jahre Rang  5

Beim Max Drawdown ist es schärfer, weil er ein EINZELEREIGNIS ist und nicht
mit der Zeit skaliert — ein langer Track Record wird dort bestraft:
cVV konservativ zeigt -14,02 % seit Auflage und -3,67 % über drei Jahre.

FESTGELEGT (Philip, 18.08.2026): Gemeinsamer Zeitraum. Wer ihn nicht
vollständig abdeckt, wird NICHT GEZEICHNET, sondern unter dem Chart
namentlich mit seiner tatsächlichen Historie genannt. Ein Punkt, der
stillschweigend einen kürzeren Zeitraum zeigt als seine Nachbarn, ist
derselbe Fehler wie ein Rumpfjahr als Jahresbalken (#51) und wie ein
Teilaggregat neben seiner Gesamtgröße (#59).

Die Regel musste dafür NICHT gebaut werden: `analytics.risiko_perioden` setzt
sie seit dem 14.08.2026 um ("Historie deckt die Periode nicht ab" -> die
Zeile bleibt leer statt gekürzt zu rechnen), und `tests/test_risiko.py`
Schritt 3 nagelt sie fest. Diese Ansicht liest den Fehlwert nur aus.

"SEIT AUFLAGE" GIBT ES HIER DESHALB NICHT. An seiner Stelle steht der
LÄNGSTE GEMEINSAME ZEITRAUM der aktuellen Auswahl. Am 18.08.2026 gemessen:

    nur die CVV-Familie          -> 7,8 Jahre (cVV dynamic ab 10/2018)
    CVV + comdirect              -> 2,4 Jahre (comdirect ab 03/2024)
    alle 19                      -> 1,7 Jahre (Pro Dividende ab 10/2024)

Die Zahl folgt also der JÜNGSTEN Reihe der Auswahl, und der Hinweis über dem
Chart nennt sie. Das ist die einzige Sicht, die "so lange wie möglich"
liefert, ohne Zeiträume zu mischen — und die letzte Zeile ist zugleich der
Grund, warum die Ansicht mit "3 Jahre" startet und nicht hiermit.

DREI HAUSREGELN, wie in `risiko_ansicht.py`:

1. KEIN eigenes CSS, kein `unsafe_allow_html`, keine festen Hintergrundfarben.
   Achsen, Ticks und Schrift folgen dem Streamlit-Theme, damit die Ansicht in
   Light und Dark gleichermaßen lesbar bleibt.
2. FARBE TRÄGT DIE AUSSAGE NIE ALLEIN. Die Familie ist die Farbe, aber jeder
   Punkt trägt zusätzlich SEINEN NAMEN — immer, unabhängig davon, wie viele
   Punkte im Chart stehen (Philip, 18.08.2026). Eine erste Fassung ließ die
   Namen ab 13 Punkten in den Hover wandern, damit sie einander nicht
   überdecken; im Kundengespräch ist eine unbeschriftete Punktwolke aber
   wertlos — dort wird auf den Bildschirm gezeigt und nicht mit der Maus
   darüber gefahren. Die Tabelle unter dem Chart nennt zusätzlich jede Zahl
   im Klartext.
3. EIN FEHLWERT SIEHT NICHT WIE EIN MESSWERT AUS. Eine nicht abgedeckte
   Strategie bekommt keinen Punkt bei 0/0, sondern gar keinen — und einen
   Satz, der sie beim Namen nennt.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.analytics import RISIKO_PERIODEN, risiko_perioden
from modules.bestandsanalytik import (
    GEWICHT_SPALTE, calc_liquidity, gemeinsame_schluessel, gemeinsame_titel,
    gewichte_je_kategorie, kategorien_vereinigt, ueberlappung,
)
from modules.formats import fmt_date_de, fmt_pct
from modules.shared import FFPB_PALETTE

# ── Die beiden Risikomaße auf der X-Achse ──────────────────────────────────
# Aufgebaut wie der Umschalter der Heatmap: zwei Ansichten derselben Daten,
# die verschiedene Fragen stellen. Volatilität fragt "wie ruhig war der Weg?",
# Max Drawdown fragt "wie weh tat der schlimmste Moment?".
X_VOLA = "Volatilität"
X_DRAWDOWN = "Max Drawdown"
X_ACHSEN = (X_VOLA, X_DRAWDOWN)

_X_SPALTE = {X_VOLA: "vola", X_DRAWDOWN: "max_dd"}

# ── Zeiträume ──────────────────────────────────────────────────────────────
# Dieselben festen Perioden wie die Risiko-Tabelle (RISIKO_PERIODEN), damit
# eine Zahl in beiden Ansichten dasselbe bedeutet — NUR "Seit Auflage" ist
# ersetzt, siehe Modul-Docstring.
GEMEINSAM = "Längster gemeinsamer Zeitraum"
PERIODEN = tuple(p for p in RISIKO_PERIODEN if p != "Seit Auflage") + (GEMEINSAM,)


# ── Ebenen der Überschneidung ──────────────────────────────────────
# Anzeigename -> Spalte in den Bestandsdaten. Dieselbe Rechnung auf gröberer
# Ebene liefert zwangsläufig höhere Werte (siehe `bestandsanalytik`), deshalb
# steht die gewählte Ebene immer im Titel und in der Caption.
EBENE_TITEL = "Einzeltitel (WKN)"
EBENEN = {
    EBENE_TITEL: "WKN",
    "Gattung":   "Gattung",
    "Region":    "Region",
    "Segment":   "Segment",
    "Währung":   "Währung",
}

# ── Achsen des Exposure-Vergleichs ───────────────────────────────
# "Segment" steht bewusst am Ende und wird anders behandelt als die anderen:
# Die Spalte trägt ZWEI Bedeutungen. Aktien tragen dort Branchen
# ("Informationstechnologie"), Renten Schuldnerklassen ("Corporates",
# "Financials"). Am 18.08.2026 gemessen: "Financials" sind 23 Renten-, "Banken,
# Versicherer, Finanzdienstl." 42 Aktienpositionen — flach nebeneinander sähen
# sie aus wie zwei Branchen, dabei ist es dasselbe Kreditrisiko in zwei Formen.
# Deshalb IMMER innerhalb einer Gattung (Festlegung Philip, 18.08.2026).
ACHSE_SEGMENT = "Segment"
EXPOSURE_ACHSEN = ("Gattung", "Region", "Währung", ACHSE_SEGMENT)

# DER MARKTRISIKOWERT FEHLT HIER BEWUSST (Philip, 18.08.2026) — er war
# gebaut und ist wieder ausgebaut worden. Die Spalte liegt in den
# Bestandsdaten und ließe sich je Strategie aufteilen; sie taugt aber nicht
# für das Kundengespräch, weil das Haus sie im Asset Management SELBST
# festlegt. Eine Kennzahl, die man vergibt, sieht neben gemessenen Größen
# aus wie eine Beobachtung — und wäre damit dieselbe Art Fehler wie ein
# Fehlwert, der wie ein Messwert aussieht (#46/B6), nur eine Ebene höher.
# Wer sie doch will, klärt vorher, welche Frage sie beantworten soll.

# Die drei Sammelposten am Ende jedes Balkens. Sie sind KEINE Kategorien der
# Daten, sondern die ehrliche Antwort auf "was fehlt zu 100 %" (#59) — und sie
# bekommen deshalb gedämpfte Farben statt einer aus der Palette.
REST_LIQUIDITAET = "Liquidität"
REST_OHNE_ANGABE = "ohne Angabe"
REST_ANDERE_GATTUNG = "übrige Gattungen"
REST_FARBEN = {
    REST_LIQUIDITAET:    "#B9C2CC",
    REST_OHNE_ANGABE:    "#D8D2C6",
    REST_ANDERE_GATTUNG: "#E4E4E4",
}

# Unterhalb dieses Gewichts gilt ein Rest als Rundungsrauschen und wird nicht
# als eigenes Segment gezeichnet. 0,05 Prozentpunkte — die Gewichte kommen mit
# drei Nachkommastellen aus dem Vorsystem, ein echter Posten ist immer größer.
REST_SCHWELLE = 0.0005


def gemeinsamer_beginn(reihen):
    """Frühester Tag, den ALLE übergebenen Reihen abdecken; None bei leer.

    Das MAXIMUM der Anfänge, nicht das Minimum — gesucht ist der Tag, ab dem
    jede Reihe Daten hat. Genau diese Verwechslung hätte die Heatmap am
    14.08.2026 fünfzehn Jahre gekostet (siehe `zeitraum_fuer_heatmap`).
    """
    anfaenge = [pd.Timestamp(ts.index.min()) for _, ts, _, _ in reihen
                if ts is not None and len(ts)]
    return max(anfaenge) if anfaenge else None


def _jahre(ts_df):
    """Länge der Historie in Jahren (Kalendertage / 365,25)."""
    if ts_df is None or len(ts_df) < 2:
        return 0.0
    return (ts_df.index.max() - ts_df.index.min()).days / 365.25


def _zahl(wert, stellen=1):
    """Deutsche Dezimalschreibweise für eine blanke Zahl (kein Prozentwert)."""
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        return "–"
    if not np.isfinite(zahl):
        return "–"
    return f"{zahl:.{stellen}f}".replace(".", ",")


def kennzahlen_je_strategie(reihen, periode):
    """Eine Zeile je Strategie: Rendite, beide Risikomaße, Familie, Abdeckung.

    Args:
        reihen: Sequenz von (label, ts_df, fee_dec, familie)
        periode: ein Eintrag aus PERIODEN

    Returns:
        DataFrame, index = label, Spalten "rendite", "vola", "max_dd",
        "familie", "jahre", "abgedeckt". Fehlwert ist durchgehend NaN.

    KEINE EIGENE MATHEMATIK. Für die festen Perioden liest die Funktion die
    Zeile aus `risiko_perioden`. Für den gemeinsamen Zeitraum schneidet sie
    die Reihen zu und liest dann dieselbe Funktion mit "Seit Auflage" —
    "seit Auflage einer zugeschnittenen Reihe" IST der Wert über das Fenster.
    Damit gelten die Abdeckungsregel und die CAGR-Konvention in beiden Fällen
    unverändert, statt ein zweites Mal zu entstehen.
    """
    spalten = ["rendite", "vola", "max_dd", "familie", "jahre", "abgedeckt"]
    if not reihen:
        return pd.DataFrame(columns=spalten)

    von = gemeinsamer_beginn(reihen) if periode == GEMEINSAM else None

    zeilen = {}
    for label, ts_df, fee_dec, familie in reihen:
        if periode == GEMEINSAM:
            teil = ts_df.loc[ts_df.index >= von] if von is not None else ts_df
            werte = risiko_perioden(teil, fee_dec).loc["Seit Auflage"]
        else:
            werte = risiko_perioden(ts_df, fee_dec).loc[periode]
        # Abgedeckt heißt: ALLE drei Größen liegen vor. Ein Punkt mit Rendite,
        # aber ohne Risiko hätte keine X-Koordinate — er wäre kein Punkt.
        abgedeckt = bool(pd.notna(werte["rendite"])
                         and pd.notna(werte["vola"])
                         and pd.notna(werte["max_dd"]))
        zeilen[label] = {
            "rendite":   float(werte["rendite"]) if pd.notna(werte["rendite"]) else np.nan,
            "vola":      float(werte["vola"]) if pd.notna(werte["vola"]) else np.nan,
            "max_dd":    float(werte["max_dd"]) if pd.notna(werte["max_dd"]) else np.nan,
            "familie":   familie or "",
            "jahre":     _jahre(ts_df),
            "abgedeckt": abgedeckt,
        }
    return pd.DataFrame.from_dict(zeilen, orient="index")[spalten]


def zeitraum_text(reihen, periode):
    """Verortet den gewählten Zeitraum in Klartext — oder "" wenn nichts geht.

    Ohne diesen Satz stünde über der Punktwolke nur ein Etikett wie
    "3 Jahre", und der Berater müsste raten, ab wann gezählt wird. Dieselbe
    Rolle wie `risiko_ansicht.zeitraum_hinweis` bei den beiden Tabellen.
    """
    enden = [pd.Timestamp(ts.index.max()) for _, ts, _, _ in reihen
             if ts is not None and len(ts)]
    if not enden:
        return ""
    bis = max(enden)
    if periode == GEMEINSAM:
        von = gemeinsamer_beginn(reihen)
        if von is None:
            return ""
        return (f"Gemeinsamer Zeitraum der Auswahl: {von:%d.%m.%Y} bis "
                f"{bis:%d.%m.%Y} — {_zahl((bis - von).days / 365.25)} Jahre.")
    return (f"Gezählt wird taggenau ab dem Datenstand {bis:%d.%m.%Y} — "
            f"„{periode}“ meint den Zeitraum bis dorthin.")


def nicht_gezeigt_text(tabelle):
    """Nennt die ausgelassenen Strategien beim Namen — oder "" wenn keine.

    EIN AGGREGAT MUSS SAGEN, WAS ES NICHT ENTHÄLT (#59). Eine Punktwolke, aus
    der fünf von neunzehn Strategien wortlos verschwinden, behauptet eine
    Vollständigkeit, die sie nicht hat.
    """
    if tabelle.empty:
        return ""
    fehlend = tabelle[~tabelle["abgedeckt"].astype(bool)]
    if fehlend.empty:
        return ""
    teile = [f"{name} ({_zahl(zeile['jahre'])} J)"
             for name, zeile in fehlend.iterrows()]
    return ("Nicht gezeigt, weil die Historie den Zeitraum nicht abdeckt: "
            + ", ".join(teile) + ".")


def punktwolke_figur(tabelle, x_groesse):
    """Risiko-Rendite-Punktwolke; None, wenn keine Strategie übrig bleibt.

    Je Familie eine Spur, damit die Legende die Familien nennt und man sie
    einzeln aus- und einblenden kann.

    DIE ACHSENTYPEN WERDEN AUSDRÜCKLICH GESETZT. Am 14.08.2026 hat plotly den
    Typ einer Achse geraten und die Bandbreiten-Ansicht dabei auf einen
    Streifen zusammenfallen lassen — die Prüfsteine waren grün, weil sie die
    DATEN lasen und nicht die Figur (#54). Was hier gesetzt ist, liest
    Schritt 4 des Prüfsteins nach.

    DER DRAWDOWN WIRD ALS BETRAG AUFGETRAGEN. Sonst liefe die Achse von -30 %
    nach 0, und "weiter rechts" hieße in der einen Ansicht mehr Risiko und in
    der anderen weniger. Zwei Ansichten mit gegenläufiger Leserichtung sind
    schlimmer als eine fehlende Ansicht.
    """
    if tabelle.empty:
        return None
    gezeigt = tabelle[tabelle["abgedeckt"].astype(bool)]
    if gezeigt.empty:
        return None

    spalte = _X_SPALTE[x_groesse]

    fig = go.Figure()
    # Reihenfolge der Familien festhalten (dict.fromkeys statt set), damit
    # Legende und Farbzuordnung bei gleicher Auswahl gleich bleiben.
    for familie in dict.fromkeys(gezeigt["familie"]):
        teil = gezeigt[gezeigt["familie"] == familie]
        namen = list(teil.index)
        fig.add_trace(go.Scatter(
            x=(teil[spalte].abs() * 100.0).tolist(),
            y=(teil["rendite"] * 100.0).tolist(),
            # Namen IMMER am Punkt, nie nur im Hover (Philip, 18.08.2026) —
            # Begründung oben in Hausregel 2.
            mode="markers+text",
            text=namen,
            textposition="top center",
            textfont=dict(size=11),
            # Ein Name am Rand darf nicht an der Zeichenfläche abgeschnitten
            # werden; ohne das verliert der äußerste Punkt seine Beschriftung,
            # und ausgerechnet der ist der interessanteste.
            cliponaxis=False,
            name=familie or "ohne Familie",
            marker=dict(size=13, line=dict(width=1)),
            customdata=namen,
            hovertemplate=("<b>%{customdata}</b><br>"
                           "Rendite p.a.: %{y:.2f} %<br>"
                           + x_groesse + ": %{x:.2f} %<extra></extra>"),
        ))

    fig.update_layout(
        height=520,
        xaxis=dict(type="linear", ticksuffix=" %",
                   title=f"{x_groesse} — mehr Risiko nach rechts"),
        yaxis=dict(type="linear", ticksuffix=" %",
                   title="Rendite p.a. (nach Kosten)"),
        colorway=FFPB_PALETTE,
        separators=",.",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(t=60),
    )
    return fig


def _tabelle_zum_anzeigen(tabelle, x_groesse):
    """Dieselben Zahlen als Tabelle — Farbe trägt die Aussage nie allein."""
    gezeigt = tabelle[tabelle["abgedeckt"].astype(bool)]
    spalte = _X_SPALTE[x_groesse]
    gezeigt = gezeigt.iloc[gezeigt[spalte].abs().to_numpy().argsort()]
    return pd.DataFrame({
        "Strategie":    list(gezeigt.index),
        "Familie":      [f or "–" for f in gezeigt["familie"]],
        "Rendite p.a.": [fmt_pct(v) for v in gezeigt["rendite"]],
        "Volatilität":  [fmt_pct(v) for v in gezeigt["vola"]],
        "Max Drawdown": [fmt_pct(v) for v in gezeigt["max_dd"]],
        "Historie (J)": [_zahl(v) for v in gezeigt["jahre"]],
    })


# ===========================================================================
# ABSCHNITT 2: UEBERSCHNEIDUNG
# ===========================================================================

def ueberschneidung_tabelle(bestaende, bezug, spalte):
    """Wie stark ueberschneidet sich `bezug` mit jedem anderen Bestand?

    Args:
        bestaende: {Anzeigename: Bestands-DataFrame}
        bezug: Anzeigename der Bezugsstrategie
        spalte: Spaltenname der Ebene (aus EBENEN)

    Returns:
        DataFrame, index = die uebrigen Strategien, absteigend nach "anteil";
        Spalten "anteil" (dezimal) und "schluessel" (Anzahl gemeinsamer Titel
        bzw. Kategorien). Leer, wenn `bezug` fehlt.

    KEINE EIGENE MATHEMATIK - beides kommt aus `bestandsanalytik`.
    """
    if bezug not in bestaende:
        return pd.DataFrame(columns=["anteil", "schluessel"])
    a = gewichte_je_kategorie(bestaende[bezug], spalte)
    zeilen = {}
    for name, df in bestaende.items():
        if name == bezug:
            continue
        b = gewichte_je_kategorie(df, spalte)
        zeilen[name] = {"anteil": ueberlappung(a, b),
                        "schluessel": gemeinsame_schluessel(a, b)}
    if not zeilen:
        return pd.DataFrame(columns=["anteil", "schluessel"])
    return (pd.DataFrame.from_dict(zeilen, orient="index")
            .sort_values("anteil", ascending=False))


def _balkenhoehe(anzahl):
    """Hoehe der Balken-Charts - mitwachsend, aber gedeckelt."""
    return int(min(760, max(220, 120 + anzahl * 30)))


def ueberschneidung_figur(tabelle, bezug, ebene):
    """Waagerechte Balken, groesste Ueberschneidung oben; None wenn leer.

    ACHSENTYPEN WERDEN GESETZT, nicht geraten (#54) - die y-Achse traegt
    Strategienamen und muss "category" sein, sonst entscheidet Plotly anhand
    der Werte. Bei Namen wie "Comdirect_100" ist das kein theoretisches
    Risiko.

    Die Reihenfolge wird ausdruecklich gesetzt (`categoryorder="array"`): Bei
    waagerechten Balken zeichnet Plotly den ERSTEN Eintrag unten, die Tabelle
    kommt aber absteigend herein. Genau diese Umkehrung hat am 14.08.2026 die
    Heatmap ein halbes Jahr lang verkehrt herum gezeigt.
    """
    if tabelle is None or tabelle.empty:
        return None
    namen = list(tabelle.index)
    werte = (tabelle["anteil"] * 100.0).tolist()
    schluessel = tabelle["schluessel"].tolist()
    einheit = "Titel" if ebene == EBENE_TITEL else "Kategorien"

    fig = go.Figure(go.Bar(
        x=werte, y=namen, orientation="h",
        marker=dict(color=FFPB_PALETTE[0]),
        # NUR DER PROZENTWERT am Balken (18.08.2026). Vorher stand dort
        # zusaetzlich die Zahl der gemeinsamen Titel — bei 18 Balken zwei
        # Angaben je Zeile, das wirkte unruhig. Die Zahl steht jetzt im Hover
        # und in der Ueberschrift des Drilldowns.
        text=[f"{w:.1f} %".replace(".", ",") for w in werte],
        textposition="outside", cliponaxis=False,
        # customdata traegt den NAMEN und die Zahl: den Namen braucht die
        # Klick-Auswahl (siehe `_gewaehlte_gegenpartei`), die Zahl der Hover.
        customdata=[[n, k] for n, k in zip(namen, schluessel)],
        hovertemplate=("<b>%{y}</b><br>Überschneidung: %{x:.2f} %<br>"
                       "gemeinsam: %{customdata[1]} " + einheit
                       + "<extra></extra>"),
    ))
    fig.update_layout(
        height=_balkenhoehe(len(namen)),
        # Kurzer Achsentitel (18.08.2026): Der lange Satz gehoert unter das
        # Chart, nicht an die Achse.
        xaxis=dict(type="linear", ticksuffix=" %",
                   title="gemeinsames Depotgewicht",
                   range=[0, max(100.0, (max(werte) * 1.25) if werte else 0.0)]),
        # automargin=True UND KEIN festes `l` im margin (18.08.2026): Beides
        # gehoert zusammen. Ein `margin=dict(l=10)` nagelt den linken Rand
        # fest, und Plotly kann ihn danach nicht mehr fuer die Beschriftungen
        # aufweiten — "Schweiz_substanzorientiert" (26 Zeichen) wurde
        # abgeschnitten. Am Figur-Objekt war davon nichts zu sehen, erst am
        # gerenderten Bild (#54). Gemeldet von Philip an der HTML-Vorschau.
        yaxis=dict(type="category", categoryorder="array",
                   categoryarray=list(reversed(namen)), title=None,
                   automargin=True),
        separators=",.", margin=dict(t=30),
        showlegend=False,
    )
    return fig


# ===========================================================================
# ABSCHNITT 3: EXPOSURE
# ===========================================================================

def exposure_tabelle(bestaende, spalte, nur_gattung=None):
    """Gewicht je Kategorie und Strategie - jede Zeile summiert auf 1,0.

    Args:
        bestaende: {Anzeigename: Bestands-DataFrame}
        spalte: Kategoriespalte
        nur_gattung: bei "Segment" die Gattung, auf die eingeschraenkt wird

    Returns:
        DataFrame, index = Strategie, Spalten = Kategorien in fester
        Reihenfolge, dahinter die Sammelposten. Werte dezimal.

    JEDE ZEILE SUMMIERT AUF 1,0, UND DAS IST DER EIGENTLICHE PUNKT. Die
    Titelgewichte allein ergeben nur 89,8 bis 98,2 % (ueber alle 19 gemessen);
    ein Balken, der bei 94 % endet und trotzdem wie ein volles Depot aussieht,
    behauptet eine Vollinvestition, die es nicht gibt. Die Differenz wird
    deshalb BENANNT statt weggelassen (#59, dieselbe Klasse wie das still
    fehlende Rentengewicht im Faelligkeits-Chart):

        Liquiditaet        1 minus Summe der Titelgewichte
        ohne Angabe        Titel, die in dieser Spalte nichts stehen haben
        uebrige Gattungen  bei "Segment": alles ausserhalb der Gattung

    DIE KATEGORIEN SIND UEBER ALLE STRATEGIEN FEST (`kategorien_vereinigt`).
    Eine je Strategie gebildete "Sonstige"-Gruppe - wie sie
    `portfolioanalyse.build_allocation` fuer die Ringe baut - waere hier
    falsch: Dieselbe Region stuende bei der einen Strategie als eigener Balken
    und waere bei der naechsten unsichtbar.
    """
    if not bestaende:
        return pd.DataFrame()

    if nur_gattung is not None:
        gefiltert = {}
        for name, df in bestaende.items():
            if "Gattung" in df.columns:
                maske = df["Gattung"].astype(str).str.strip() == nur_gattung
                gefiltert[name] = df[maske]
            else:
                gefiltert[name] = df.iloc[0:0]
    else:
        gefiltert = dict(bestaende)

    kategorien = kategorien_vereinigt(gefiltert, spalte)

    zeilen = {}
    for name, df_voll in bestaende.items():
        df_teil = gefiltert[name]
        gewichte = gewichte_je_kategorie(df_teil, spalte)
        zeile = {k: float(gewichte.get(k, 0.0)) for k in kategorien}

        gesamt_titel = float(df_voll[GEWICHT_SPALTE].sum())
        teil_titel = float(df_teil[GEWICHT_SPALTE].sum()) if len(df_teil) else 0.0
        zugeordnet = sum(zeile.values())

        # Reihenfolge der Sammelposten ist die Reihenfolge im Balken.
        if nur_gattung is not None:
            zeile[REST_ANDERE_GATTUNG] = max(0.0, gesamt_titel - teil_titel)
        zeile[REST_OHNE_ANGABE] = max(0.0, teil_titel - zugeordnet)
        zeile[REST_LIQUIDITAET] = calc_liquidity(df_voll)
        zeilen[name] = zeile

    tabelle = pd.DataFrame.from_dict(zeilen, orient="index")
    # Sammelposten unter der Schwelle fallen weg - sonst truege die Legende
    # Eintraege, die niemand sieht.
    for rest in (REST_ANDERE_GATTUNG, REST_OHNE_ANGABE, REST_LIQUIDITAET):
        if rest in tabelle.columns and tabelle[rest].max() < REST_SCHWELLE:
            tabelle = tabelle.drop(columns=[rest])
    return tabelle


def exposure_figur(tabelle, achse):
    """Gestapelte 100-%-Balken, eine Zeile je Strategie; None wenn leer.

    Wie bei der Ueberschneidung wird die Kategorienreihenfolge der y-Achse
    ausdruecklich gesetzt, damit die erste Strategie oben steht (#54).
    """
    if tabelle is None or tabelle.empty:
        return None
    namen = list(tabelle.index)
    fig = go.Figure()
    farb_index = 0
    for spalte in tabelle.columns:
        if spalte in REST_FARBEN:
            farbe = REST_FARBEN[spalte]
            beschriftung = str(spalte)
        else:
            farbe = FFPB_PALETTE[farb_index % len(FFPB_PALETTE)]
            farb_index += 1
            beschriftung = str(spalte)
        werte = (tabelle[spalte] * 100.0).tolist()
        fig.add_trace(go.Bar(
            x=werte, y=namen, orientation="h", name=beschriftung,
            marker=dict(color=farbe),
            hovertemplate=("<b>%{y}</b><br>" + beschriftung
                           + ": %{x:.2f} %<extra></extra>"),
        ))
    fig.update_layout(
        barmode="stack",
        height=_balkenhoehe(len(namen)),
        xaxis=dict(type="linear", ticksuffix=" %", range=[0, 100],
                   title="Anteil am Depot"),
        # automargin: siehe `ueberschneidung_figur` — der linke Rand muss
        # sich nach den Strategienamen richten duerfen.
        yaxis=dict(type="category", categoryorder="array",
                   categoryarray=list(reversed(namen)), title=None,
                   automargin=True),
        separators=",.", margin=dict(t=30),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0),
    )
    return fig


def zeige_strategievergleich(reihen_alle, familien_reihenfolge=(),
                             bestaende=None, auswertungsdatum=None):
    """Die Ansicht mit ihren drei Abschnitten.

    Args:
        reihen_alle: (label, ts_df, fee_dec, familie) je Strategie
        familien_reihenfolge: kanonische Reihenfolge der Familien
        bestaende: {label: Bestands-DataFrame} aus `Daten_PF`, oder None
        auswertungsdatum: Stichtag der Bestandsdaten

    ZWEI DATENQUELLEN, UND DAS MUSS MAN SEHEN: Die Punktwolke rechnet auf den
    Zeitreihen und zeigt einen ZEITRAUM. Ueberschneidung und Exposure rechnen
    auf den Einzeltiteln und zeigen einen STICHTAG. Beide Abschnitte nennen
    ihr Auswertungsdatum deshalb ausdruecklich.

    FEHLEN DIE BESTANDSDATEN, FAELLT NUR DER UNTERE TEIL AUS. Die Punktwolke
    haengt an einer anderen Quelle und darf nicht mit verschwinden - ein
    fehlender Ordner ist kein Grund, eine funktionierende Ansicht abzuschalten.
    """
    st.subheader("Strategien im Risiko-Rendite-Vergleich")

    if not reihen_alle:
        st.info("Keine Strategien geladen.")
        return

    familien = list(dict.fromkeys(f for _, _, _, f in reihen_alle if f))
    if familien_reihenfolge:
        bekannt = [f for f in familien_reihenfolge if f in familien]
        familien = bekannt + [f for f in familien if f not in bekannt]

    # ── Auswahl ──
    # Die Familien SETZEN die Auswahl, danach ist sie einzeln veränderbar.
    # Bewusst KEIN Knopf: Ein `st.button` müsste in `_KEEPALIVE_SPERRE` in
    # streamlit_app.py eingetragen werden, sonst stürzt die Seite ab (#19) —
    # ein Mehrfachfeld tut hier dasselbe ohne diese Falle.
    links, rechts = st.columns([2, 3])
    with links:
        fam_wahl = st.multiselect(
            "Familien", familien, default=list(familien), key="sv_familien",
            help="Setzt die Auswahl rechts. Danach lassen sich einzelne "
                 "Strategien abwählen.")
    vorschlag = [lbl for lbl, _, _, fam in reihen_alle if fam in fam_wahl]
    with rechts:
        # Der Key hängt an der Familienwahl: Ein NEUER Key erzeugt ein
        # frisches Widget mit seinem Default. Nur so setzt die Familienwahl
        # die Strategieauswahl überhaupt neu — `st.session_state[key] = ...`
        # wirft bei einem aktiven Widget (#4, Lösung A: Kennungs-Keys).
        wahl = st.multiselect(
            "Strategien", [lbl for lbl, _, _, _ in reihen_alle],
            default=vorschlag,
            key="sv_strategien_" + "|".join(sorted(fam_wahl)),
            help="Jede gewählte Strategie ist ein Punkt im Chart.")

    spalte_zeit, spalte_x = st.columns(2)
    with spalte_zeit:
        # VORBELEGUNG "3 Jahre" und NICHT der gemeinsame Zeitraum, obwohl der
        # zuerst naheliegt: Ueber alle 19 Strategien sind das nur 1,7 Jahre,
        # weil "Pro Dividende" erst im Oktober 2024 aufgelegt wurde (am
        # 18.08.2026 gemessen). Eine Punktwolke ueber 1,7 Jahre sagt ueber
        # Risiko nichts, und sie waere das erste, was der Berater sieht.
        # "3 Jahre" zeigt 14 der 19 Strategien; die fuenf uebrigen stehen
        # namentlich darunter, statt stillschweigend zu fehlen.
        periode = st.selectbox("Zeitraum", PERIODEN,
                               index=PERIODEN.index("3 Jahre"),
                               key="sv_periode",
                               help="Gerechnet wird je Strategie mit ihrem "
                                    "hinterlegten Honorarsatz, nach Kosten — "
                                    "wie in der Broschüre. Das Honorarfeld "
                                    "der Performance-Ansicht wirkt hier "
                                    "nicht.")
    with spalte_x:
        # segmented_control statt radio (18.08.2026, Philip): Die Heatmap
        # schaltet ihre zwei Ansichten genauso um, und zwei Bauformen für
        # dieselbe Aufgabe sehen ungleichmäßig aus.
        #
        # required=True ist dabei nicht Kosmetik, sondern der Grund, warum
        # dieser Baustein hier überhaupt trägt: Ohne ihn lässt sich das
        # aktive Segment abwählen, und es gäbe den Zustand „keine X-Achse
        # gewählt" — denselben Fehler hat `p_zeitraum` schon einmal gehabt.
        if "sv_xachse" not in st.session_state:
            st.session_state["sv_xachse"] = X_VOLA
        x_groesse = st.segmented_control(
            "Risikomaß auf der X-Achse", list(X_ACHSEN), key="sv_xachse",
            required=True,
            help=(f"„{X_VOLA}“ fragt, wie ruhig der Weg war — {X_DRAWDOWN} "
                  "fragt, wie weh der schlimmste Moment tat."))

    reihen = [r for r in reihen_alle if r[0] in wahl]
    if not reihen:
        st.info("Keine Strategie gewählt — bitte mindestens eine auswählen.")
        return

    tabelle = kennzahlen_je_strategie(reihen, periode)
    fig = punktwolke_figur(tabelle, x_groesse)

    hinweis = zeitraum_text(reihen, periode)
    if hinweis:
        st.caption(hinweis)

    if fig is None:
        st.warning("Für den gewählten Zeitraum hat keine der gewählten "
                   "Strategien eine vollständige Historie. Bitte einen "
                   "kürzeren Zeitraum wählen.")
    else:
        st.plotly_chart(fig, config={"displayModeBar": False}, key="sv_wolke")

    fehlt = nicht_gezeigt_text(tabelle)
    if fehlt:
        st.caption(fehlt)

    # Der Honorar-Hinweis stand bis 18.08.2026 als vierte Caption unter dem
    # Chart. Er ist eine Eigenschaft der Rechnung und keine Aussage ueber das
    # Ergebnis — er steht jetzt im `help` des Zeitraum-Feldes, wo man ihn
    # sucht, wenn man ihn braucht.

    if fig is not None and st.checkbox("Tabelle anzeigen", key="sv_tabelle"):
        st.dataframe(_tabelle_zum_anzeigen(tabelle, x_groesse),
                     width="stretch", height="content", hide_index=True)

    # ---- Abschnitt 2 und 3: die Bestandsdaten ----
    if bestaende:
        gewaehlt = {n: bestaende[n] for n in wahl if n in bestaende}
        _zeige_ueberschneidung(gewaehlt, auswertungsdatum)
        _zeige_exposure(gewaehlt, auswertungsdatum)
    else:
        st.markdown("---")
        st.caption("Überschneidung und Exposure brauchen die Bestandsdaten "
                   "aus dem Ordner Daten_PF. Für diesen Datenstand sind sie "
                   "nicht geladen; die Punktwolke oben ist davon unberührt.")


def _stichtag_text(auswertungsdatum):
    """Nennt den Stichtag der Bestandsdaten — oder sagt, dass er fehlt."""
    if auswertungsdatum is None:
        return "Bestand zum letzten gelieferten Stichtag."
    return f"Bestand zum {fmt_date_de(auswertungsdatum)}."


def _waehle_gueltig(schluessel, optionen, beschriftung, hilfe=None):
    """Auswahlfeld, das einen ungueltig gewordenen Wert vorher aufraeumt.

    Die Strategieauswahl oben veraendert die Optionen dieser Felder. Bleibt
    im session_state ein Wert stehen, den es nicht mehr gibt, wirft Streamlit
    beim Anlegen des Widgets. Der Key wird deshalb VOR dem Rendern geleert -
    das ist erlaubt, solange das Widget in diesem Lauf noch nicht existiert
    (#4: nach dem Anlegen wuerde dieselbe Zuweisung werfen).
    """
    if st.session_state.get(schluessel) not in optionen:
        st.session_state.pop(schluessel, None)
    return st.selectbox(beschriftung, optionen, key=schluessel, help=hilfe)


def gewaehlte_gegenpartei(auswahl, tabelle):
    """Welche Zeile hat der Klick getroffen? Fallback: die staerkste.

    Args:
        auswahl: Rueckgabe von `st.plotly_chart(..., on_select="rerun")`
            oder None
        tabelle: die aktuelle Ausgabe von `ueberschneidung_tabelle`

    Returns:
        Ein Name aus `tabelle.index`, nie etwas anderes. Bei leerer Tabelle
        None.

    ES WIRD UEBER DEN NAMEN AUFGELOEST, NICHT UEBER DEN INDEX. Wechselt die
    Ebene oder die Strategieauswahl, zeigt derselbe Balkenindex auf eine
    ANDERE Strategie — der Drilldown zeigte dann Titel eines Depots, das
    niemand angeklickt hat. Dieselbe Klasse wie ein Auswahlfeld-Wert, der ins
    Leere laeuft (#53).

    Ein Name, den es nicht mehr gibt, faellt deshalb auf die staerkste
    Ueberschneidung zurueck. Damit gibt es AUCH KEINEN LEEREN ZUSTAND: Wer
    nie klickt, sieht trotzdem die interessanteste Zeile.
    """
    if tabelle is None or tabelle.empty:
        return None
    kandidat = None
    punkte = []
    try:
        punkte = list((auswahl or {}).get("selection", {}).get("points", []))
    except Exception:
        punkte = []
    if punkte:
        punkt = punkte[0]
        # `y` traegt bei waagerechten Balken die Kategorie; `customdata[0]`
        # ist der Ersatzweg, falls Plotly die Achse anders zurueckmeldet.
        kandidat = punkt.get("y")
        if kandidat not in tabelle.index:
            daten = punkt.get("customdata")
            if isinstance(daten, (list, tuple)) and daten:
                kandidat = daten[0]
    if kandidat in tabelle.index:
        return kandidat
    return tabelle.index[0]


# EIN BEITRAGSBALKEN STAND HIER UND IST WIEDER WEG (Philip, 18.08.2026).
#
# Die Tabelle trug rechts eine Spalte mit einem Balken aus Blockzeichen,
# proportional zum groessten Beitrag. Die Idee war, Groessenverhaeltnisse
# sichtbar zu machen, ohne eine zweite Zahlenformatierung einzufuehren
# (`st.column_config` formatiert englisch oder nach Browser-Locale).
#
# Am Bildschirm las sich das Ergebnis nicht als Balken, sondern als
# schwarzer Klotz — Philip: "was ist das? Der kann auch weg." Und er hat
# recht: Ein Block aus U+2588 ist kein Diagramm, sondern eine Textur. Die
# Zahlen daneben sagen dasselbe, ruhiger und ohne Erklaerungsbedarf.
#
# Wer Groessenverhaeltnisse doch zeigen will, faengt nicht wieder bei
# Textzeichen an: Die Tabelle ist absteigend sortiert, und darueber steht das
# Chart, das genau dafuer da ist.


def _drilldown_tabelle(bestaende, bezug, gegen, ebene):
    """Die gemeinsamen Titel als anzeigefertige Tabelle.

    Alle Zahlen sind FERTIG FORMATIERTE Zeichenketten aus `formats.fmt_pct` —
    deutsche Notation, Fehlwert "–", eine einzige Quelle (siehe
    `beitragsbalken`).
    """
    roh = gemeinsame_titel(bestaende[bezug], bestaende[gegen], EBENEN[ebene])
    if roh.empty:
        return None

    spalten = {}
    if ebene == EBENE_TITEL:
        spalten["Wertpapier"] = list(roh["bezeichnung"])
        spalten["WKN"] = list(roh["schluessel"])
        spalten["Gattung"] = list(roh["gattung"])
    else:
        spalten[ebene] = list(roh["schluessel"])
    spalten[bezug] = [fmt_pct(v) for v in roh["gewicht_a"]]
    spalten[gegen] = [fmt_pct(v) for v in roh["gewicht_b"]]
    spalten["gemeinsam"] = [fmt_pct(v) for v in roh["gemeinsam"]]
    return pd.DataFrame(spalten)


def _zeige_ueberschneidung(bestaende, auswertungsdatum):
    """Abschnitt 2 - wie viel halten zwei Strategien gemeinsam?"""
    st.markdown("---")
    st.subheader("Überschneidung der Strategien")

    if len(bestaende) < 2:
        st.info("Für eine Überschneidung braucht es mindestens zwei "
                "gewählte Strategien.")
        return

    namen = list(bestaende)
    links, rechts = st.columns(2)
    with links:
        bezug = _waehle_gueltig(
            "sv_ue_bezug", namen, "Bezugsstrategie",
            "Gegen diese Strategie werden alle anderen verglichen.")
    with rechts:
        ebene = _waehle_gueltig(
            "sv_ue_ebene", list(EBENEN), "Ebene",
            "Auf welcher Ebene gilt etwas als gemeinsam gehalten.")

    tabelle = ueberschneidung_tabelle(bestaende, bezug, EBENEN[ebene])
    fig = ueberschneidung_figur(tabelle, bezug, ebene)
    if fig is None:
        st.caption("Keine Vergleichsstrategie vorhanden.")
        return

    # on_select macht das Chart selbst zur Navigation — ein Klick auf einen
    # Balken oeffnet den Drilldown darunter. Bewusst KEIN zusaetzliches
    # Auswahlfeld: Es waere ein Bedienelement mehr fuer dieselbe Sache.
    auswahl = st.plotly_chart(fig, config={"displayModeBar": False},
                              key="sv_ue_chart", on_select="rerun",
                              selection_mode="points")

    einheit = "Titel" if ebene == EBENE_TITEL else "Kategorien"
    gegen = gewaehlte_gegenpartei(auswahl, tabelle)
    zeile = tabelle.loc[gegen]

    st.markdown(
        f"**{bezug}** und **{gegen}** halten zu "
        f"**{fmt_pct(zeile['anteil'])}** des Depotgewichts dasselbe — "
        f"{int(zeile['schluessel'])} gemeinsame {einheit.lower()}.")
    st.caption("Ein Klick auf einen Balken zeigt die Aufstellung dieses Paares.")

    anzeige = _drilldown_tabelle(bestaende, bezug, gegen, ebene)
    if anzeige is not None:
        st.dataframe(anzeige, width="stretch", height="content",
                     hide_index=True)
        st.caption(f"Die {len(anzeige)} Beiträge summieren sich auf die "
                   f"{fmt_pct(zeile['anteil'])} oben — es ist je Eintrag das "
                   "kleinere der beiden Gewichte.")

    # EIN Hinweisblock statt drei einzelner Captions (18.08.2026): Drei graue
    # Absaetze hintereinander lesen sich wie Kleingedrucktes. Der Wortlaut ist
    # unveraendert — er wurde ausdruecklich als verstaendlich abgenommen.
    st.caption(
        _stichtag_text(auswertungsdatum)
        + " Gerechnet wird als Summe des jeweils kleineren Gewichts, die "
          "Gegengröße zur Active Share.  \n"
        + "Die Zahlen verschiedener **Ebenen** sind nicht vergleichbar: Je "
          "gröber die Ebene, desto höher fällt sie zwangsläufig aus — "
          "dasselbe Paar liest sich auf Titelebene als 20,5 % und auf "
          "Gattungsebene als 73,8 %.  \n"
        + "**100 % sind nicht erreichbar**: Die Titelgewichte machen je nach "
          "Strategie nur 90 bis 98 % aus, der Rest ist Liquidität und zählt "
          "hier nicht mit.")


def _zeige_exposure(bestaende, auswertungsdatum):
    """Abschnitt 3 - die Aufteilung aller gewaehlten Strategien nebeneinander."""
    st.markdown("---")
    st.subheader("Exposure im Vergleich")

    if not bestaende:
        return

    links, rechts = st.columns(2)
    with links:
        achse = _waehle_gueltig(
            "sv_ex_achse", list(EXPOSURE_ACHSEN), "Aufteilung nach",
            "Jeder Balken ist eine Strategie und summiert sich auf 100 %.")

    nur_gattung = None
    if achse == ACHSE_SEGMENT:
        gattungen = kategorien_vereinigt(bestaende, "Gattung")
        if not gattungen:
            st.caption("Keine Gattungen in den Bestandsdaten.")
            return
        with rechts:
            nur_gattung = _waehle_gueltig(
                "sv_ex_gattung", gattungen, "innerhalb der Gattung",
                "Segment wird nur innerhalb einer Gattung gezeigt — die "
                "Spalte trägt für Aktien und Renten verschiedene "
                "Bedeutungen.")

    tabelle = exposure_tabelle(bestaende, achse, nur_gattung)
    fig = exposure_figur(tabelle, achse)
    if fig is None:
        st.caption("Für die gewählte Aufteilung liegen keine Daten vor.")
        return

    st.plotly_chart(fig, config={"displayModeBar": False}, key="sv_ex_chart")

    st.caption(_stichtag_text(auswertungsdatum)
               + " Jeder Balken summiert sich auf 100 % — die Liquidität "
                 "ist als eigenes Segment ausgewiesen und nicht weggelassen.")

    if achse == ACHSE_SEGMENT:
        st.caption(f"Gezeigt wird das Segment **innerhalb** der Gattung "
                   f"{nur_gattung}; der Rest des Depots steht als "
                   f"„{REST_ANDERE_GATTUNG}“ daneben. Grund: Die Spalte trägt "
                   "zwei Bedeutungen — Aktien tragen Branchen, Renten "
                   "Schuldnerklassen. „Financials“ sind Anleihen von Banken, "
                   "„Banken, Versicherer, Finanzdienstl.“ sind deren Aktien.")

    if achse == "Region":
        st.caption("Vorbehalt: Es gibt kein Look-through in Fonds und ETFs. "
                   "„Europa“ sind ausschließlich Fonds, ETFs und Zertifikate, "
                   "„Europa ohne Deutschland“ ausschließlich Einzeltitel. Der "
                   "ausgewiesene Deutschland-Anteil ist damit eher zu niedrig, "
                   "weil das Deutschland-Gewicht innerhalb der Europa-ETFs "
                   "nicht sichtbar wird.")

    if achse in (ACHSE_SEGMENT, "Region"):
        st.caption("Bei den ETF-Strategien stehen nur 8 bzw. 9 Positionen im "
                   "Bestand. Ihre Aufteilung zeigt deshalb die Fondsstruktur "
                   "und nicht das Marktexposure.")

    if st.checkbox("Tabelle anzeigen", key="sv_ex_tabelle"):
        anzeige = tabelle.copy()
        for spalte in anzeige.columns:
            anzeige[spalte] = [fmt_pct(v) for v in anzeige[spalte]]
        anzeige.insert(0, "Strategie", list(tabelle.index))
        st.dataframe(anzeige, width="stretch", height="content",
                     hide_index=True)
