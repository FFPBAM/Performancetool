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

import hashlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.analytics import (RISIKO_PERIODEN, _perioden_start,
                              deckt_zeitraum_ab, risiko_perioden)
from modules.bestandsanalytik import (
    GEWICHT_SPALTE, calc_liquidity, exklusive_schluessel, exklusive_titel,
    gemeinsame_schluessel, gemeinsame_titel, gewichte_je_kategorie,
    kategorien_vereinigt, nicht_ueberlappung, ueberlappung,
)
from modules.auswahl import gewaehlter_balkenname
from modules.farben import gattung_farbe
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

# ── Der frei gewählte Zeitraum (NEU 24.08.2026) ────────────────────────────
# EIGEN ist eine KENNUNG und bewusst KEIN Eintrag in PERIODEN.
#
# Der Grund ist ein Zaun um `analytics._perioden_start`: Die Funktion liest die
# Jahreszahl aus dem Label (`int(bezeichnung.split()[0])`). Ein Label wie
# „Eigener Zeitraum“ ergäbe dort einen ValueError mitten in der Rechnung.
# Statt das mit einem Kommentar zu verbieten, kann es gar nicht passieren:
# Die Kennung steht nicht in der Auswahlliste, die Kalenderfelder erscheinen
# über ein eigenes Häkchen daneben — dasselbe Muster wie im Performance-Reiter.
#
# Als Nebenwirkung bleibt die Vorbelegung „3 Jahre“ unberührt, und der
# vorhandene Prüfstein auf den „Nicht gezeigt“-Satz greift weiter.
EIGEN = "Eigener Zeitraum"


# ── Ebenen der Überschneidung ──────────────────────────────────────
# Anzeigename -> Spalte in den Bestandsdaten. Dieselbe Rechnung auf gröberer
# Ebene liefert zwangsläufig höhere Werte (siehe `bestandsanalytik`), deshalb
# steht die gewählte Ebene immer im Titel und in der Caption.
# ── Die beiden Ansichten der Überschneidung (NEU 24.08.2026) ───────────────
# Dieselbe Bauform wie der X-Achsen-Umschalter: zwei Sichten auf dieselben
# Bestände, die verschiedene Fragen stellen.
#
#   „Gemeinsam“           Was halten beide? — Summe der kleineren Gewichte.
#   „Nur im Bezugsdepot“  Was hält die Bezugsstrategie allein? — Summe der
#                         Übergewichte gegenüber der Gegenpartei.
#
# Die beiden ergänzen sich zum investierten Gewicht der Bezugsstrategie; die
# Herleitung steht bei `bestandsanalytik.nicht_ueberlappung`. WICHTIG für die
# Lesart: Die Überschneidung ist symmetrisch, die Nicht-Überschneidung NICHT.
# Deshalb nennt die Oberfläche die Gegenrichtung ausdrücklich.
UE_GEMEINSAM = "Gemeinsam"
UE_EXKLUSIV = "Nur im Bezugsdepot"
UE_ANSICHTEN = (UE_GEMEINSAM, UE_EXKLUSIV)

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
# Auf dieser Achse gelten die festen Assetklassen-Farben aus
# `modules/farben.py`; auf allen anderen die Palette. Siehe die Begruendung
# bei `_ring_farben` in portfolioanalyse.py - die Klassifizierung wuerde
# sonst Segment-Werte wie "Rentenfonds" mitfaerben.
ACHSE_GATTUNG = "Gattung"
EXPOSURE_ACHSEN = (ACHSE_GATTUNG, "Region", "Währung", ACHSE_SEGMENT)

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


def _fenster(reihen, periode, von, bis):
    """(von, bis) des Zeitfensters — oder None, wenn `risiko_perioden` selbst
    zuschneidet.

    DIE EINZIGE STELLE, an der sich entscheidet, welcher Weg genommen wird.
    Solange sie `None` liefert, und NUR dann, wird `.loc[periode]` erreicht —
    damit kann ein Label, das `_perioden_start` nicht kennt, dort gar nicht
    ankommen.
    """
    if periode == GEMEINSAM:
        return gemeinsamer_beginn(reihen), None
    if periode == EIGEN:
        return (pd.Timestamp(von) if von is not None else None,
                pd.Timestamp(bis) if bis is not None else None)
    return None


def kennzahlen_je_strategie(reihen, periode, von=None, bis=None):
    """Eine Zeile je Strategie: Rendite, beide Risikomaße, Familie, Abdeckung.

    Args:
        reihen: Sequenz von (label, ts_df, fee_dec, familie)
        periode: ein Eintrag aus PERIODEN oder die Kennung EIGEN
        von, bis: nur bei EIGEN — die Ränder des gewählten Fensters

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
    if periode not in RISIKO_PERIODEN and periode not in (GEMEINSAM, EIGEN):
        # LIEBER LAUT ALS FALSCH: Ein unbekanntes Label liefe sonst in
        # `risiko_perioden(...).loc[periode]` und käme dort als KeyError
        # heraus — an einer Stelle, die nichts mit der Ursache zu tun hat.
        raise ValueError(f"Unbekannter Zeitraum: {periode!r}")

    spalten = ["rendite", "vola", "max_dd", "familie", "jahre", "beginn",
               "abgedeckt"]
    if not reihen:
        return pd.DataFrame(columns=spalten)

    fenster = _fenster(reihen, periode, von, bis)

    zeilen = {}
    for label, ts_df, fee_dec, familie in reihen:
        if fenster is None:
            # Feste Periode: `risiko_perioden` schneidet selbst zu UND
            # entscheidet selbst über die Abdeckung.
            werte = risiko_perioden(ts_df, fee_dec).loc[periode]
        else:
            f_von, f_bis = fenster
            teil = ts_df
            if f_von is not None:
                teil = teil.loc[teil.index >= f_von]
            if f_bis is not None:
                teil = teil.loc[teil.index <= f_bis]
            # HIER STECKT DER STILLE DATENVERLUST, gegen den
            # `deckt_zeitraum_ab` gebaut ist: Ohne diese Frage lieferte eine
            # Strategie, die erst MITTEN im Fenster beginnt, brav eine Zahl —
            # nur über einen kürzeren Zeitraum als verlangt. In der
            # Punktwolke stünde sie dann neben Strategien mit voller
            # Historie, ohne dass irgendetwas darauf hinwiese.
            if deckt_zeitraum_ab(ts_df, f_von, f_bis):
                werte = risiko_perioden(teil, fee_dec).loc["Seit Auflage"]
            else:
                werte = pd.Series(np.nan, index=["rendite", "vola", "max_dd",
                                                 "sharpe", "te", "ir"])
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
            "beginn":    (pd.Timestamp(ts_df.index.min())
                          if ts_df is not None and len(ts_df) else pd.NaT),
            "abgedeckt": abgedeckt,
        }
    return pd.DataFrame.from_dict(zeilen, orient="index")[spalten]


def xachsen_hinweis(x_groesse: str) -> str:
    """Ein Satz, der sagt, was gerade auf der X-Achse steht.

    WARUM DAS NOETIG WURDE (24.08.2026): Der Schalter traegt seit dem Umzug
    `label_visibility="collapsed"` — die beiden nackten Woerter
    "Volatilitaet" und "Max Drawdown" stuenden sonst ohne Zusammenhang ueber
    der Grafik und saehen aus wie ein Filter. Der Satz nennt zusaetzlich die
    LESERICHTUNG; ohne sie muss man raten, ob links besser oder schlechter
    ist. Der Vergleich der beiden Groessen steht weiterhin im `help` des
    Schalters, wo man ihn sucht, wenn man ihn braucht.

    ALS FUNKTION und nicht als f-String an der Aufrufstelle (#55): Ein
    Wortlaut, der inline gebaut wird, ist fuer keinen Pruefstein erreichbar.
    Genau daran ist am 14.08.2026 ein Fehler lange unbemerkt geblieben.
    """
    if x_groesse == X_DRAWDOWN:
        return ("Auf der X-Achse steht der **grösste Rückgang** vom "
                "Höchststand bis zum Tiefpunkt des Zeitraums. Je weiter "
                "links, desto flacher ist die Strategie gefallen.")
    return ("Auf der X-Achse steht die **Schwankungsbreite** der "
            "Wertentwicklung, annualisiert. Je weiter links, desto ruhiger "
            "war der Weg.")


def zeitraum_grenzen(reihen):
    """(frühester, spätester) Tag über die gewählten Reihen, als `date`.

    DIE VEREINIGUNG und nicht der Schnitt: Ein Fenster, das nur ein Teil der
    Auswahl abdeckt, muss WÄHLBAR sein — sonst liefe die Regel „wer den
    Zeitraum nicht abdeckt, wird namentlich genannt“ ins Leere, weil man
    einen solchen Zeitraum gar nicht erst einstellen könnte.
    """
    raender = [(pd.Timestamp(ts.index.min()), pd.Timestamp(ts.index.max()))
               for _, ts, _, _ in reihen if ts is not None and len(ts)]
    if not raender:
        return None, None
    return (min(r[0] for r in raender).date(),
            max(r[1] for r in raender).date())


def eigener_zeitraum_vorschlag(reihen, periode):
    """Vorbelegung der Kalenderfelder aus der aktuellen Schnellwahl.

    Wer das Häkchen setzt, will in aller Regel den gerade gewählten Zeitraum
    verschieben und nicht bei null anfangen. Der Vorschlag ist deshalb genau
    der Zeitraum, der eben noch gezeigt wurde.

    KEINE ZWEITE RECHENREGEL: Der Beginn kommt aus `analytics._perioden_start`,
    also aus derselben Funktion, die auch die festen Perioden schneidet. Das
    „+ 1 Tag“ übersetzt deren Konvention (`index > start`) in die Konvention
    der Kalenderfelder (`index >= von`); bei kalendertäglichen, lückenlosen
    Reihen ist das dasselbe Fenster.
    """
    mind, maxd = zeitraum_grenzen(reihen)
    if maxd is None:
        return None, None
    if periode == GEMEINSAM:
        von = gemeinsamer_beginn(reihen)
        return ((von.date() if von is not None else mind), maxd)
    start = _perioden_start(pd.Timestamp(maxd), periode)
    if start is None:
        return mind, maxd
    return max(mind, (start + pd.Timedelta(days=1)).date()), maxd


def leer_hinweis(periode) -> str:
    """Was dasteht, wenn kein einziger Punkt übrig bleibt.

    ZWEI FASSUNGEN, weil eine Anweisung falsch sein kann: Bei einer festen
    Periode hilft „einen kürzeren wählen“ — die Auswahl reicht weiter zurück
    als die Historien. Bei einem selbst gewählten Fenster ist genau das die
    verkehrte Anweisung: Es kann VOR dem Beginn aller Strategien liegen oder
    zu kurz für eine Kennzahl sein, und in beiden Fällen macht ein noch
    kürzerer Zeitraum es schlimmer.
    """
    if periode == EIGEN:
        return ("Im gewählten Fenster hat keine der Strategien eine "
                "vollständige Historie. Entweder beginnt es vor der ältesten "
                "Auswahl, oder es umfasst zu wenige Tage für eine Kennzahl.")
    return ("Für den gewählten Zeitraum hat keine der gewählten Strategien "
            "eine vollständige Historie. Bitte einen kürzeren Zeitraum "
            "wählen.")


def zeitraum_text(reihen, periode, von=None, bis=None):
    """Verortet den gewählten Zeitraum in Klartext — oder "" wenn nichts geht.

    Ohne diesen Satz stünde über der Punktwolke nur ein Etikett wie
    "3 Jahre", und der Berater müsste raten, ab wann gezählt wird. Dieselbe
    Rolle wie `risiko_ansicht.zeitraum_hinweis` bei den beiden Tabellen.
    """
    enden = [pd.Timestamp(ts.index.max()) for _, ts, _, _ in reihen
             if ts is not None and len(ts)]
    if not enden:
        return ""
    letzter = max(enden)
    if periode == EIGEN:
        if von is None or bis is None:
            return ""
        a, b = pd.Timestamp(von), pd.Timestamp(bis)
        if a > b:
            return ""
        return (f"Eigener Zeitraum: {a:%d.%m.%Y} bis {b:%d.%m.%Y} — "
                f"{_zahl((b - a).days / 365.25)} Jahre.")
    if periode == GEMEINSAM:
        anfang = gemeinsamer_beginn(reihen)
        if anfang is None:
            return ""
        return (f"Gemeinsamer Zeitraum der Auswahl: {anfang:%d.%m.%Y} bis "
                f"{letzter:%d.%m.%Y} — "
                f"{_zahl((letzter - anfang).days / 365.25)} Jahre.")
    return (f"Gezählt wird taggenau ab dem Datenstand {letzter:%d.%m.%Y} — "
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
    # Der Beginn steht mit dabei, seit es den eigenen Zeitraum gibt
    # (24.08.2026): Bei „3 Jahre“ genügt die Länge, um zu verstehen, warum
    # eine Strategie fehlt. Bei einem frei gewählten Fenster ist die
    # nützliche Tatsache das ANFANGSDATUM — daran sieht man sofort, wie weit
    # man den Regler zurückschieben darf.
    teile = []
    for name, zeile in fehlend.iterrows():
        beginn = zeile.get("beginn")
        wann = (f", ab {pd.Timestamp(beginn):%d.%m.%Y}"
                if beginn is not None and pd.notna(beginn) else "")
        teile.append(f"{name} ({_zahl(zeile['jahre'])} J{wann})")
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

def ueberschneidung_tabelle(bestaende, bezug, spalte,
                            ansicht=UE_GEMEINSAM):
    """Wie stark ueberschneidet sich `bezug` mit jedem anderen Bestand?

    Args:
        bestaende: {Anzeigename: Bestands-DataFrame}
        bezug: Anzeigename der Bezugsstrategie
        spalte: Spaltenname der Ebene (aus EBENEN)

    Returns:
        DataFrame, index = die uebrigen Strategien, absteigend nach "anteil";
        Spalten "anteil" (dezimal) und "schluessel" (Anzahl der gezaehlten
        Titel bzw. Kategorien). Leer, wenn `bezug` fehlt.

    `ansicht` hat einen VORGABEWERT, damit die vorhandenen Aufrufe und ihre
    Pruefsteine unveraendert weitergelten. Bei UE_EXKLUSIV traegt "anteil"
    die Nicht-Ueberschneidung und "schluessel" die Zahl der Uebergewichte.

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
        if ansicht == UE_EXKLUSIV:
            zeilen[name] = {"anteil": nicht_ueberlappung(a, b),
                            "schluessel": exklusive_schluessel(a, b)}
        else:
            zeilen[name] = {"anteil": ueberlappung(a, b),
                            "schluessel": gemeinsame_schluessel(a, b)}
    if not zeilen:
        return pd.DataFrame(columns=["anteil", "schluessel"])
    return (pd.DataFrame.from_dict(zeilen, orient="index")
            .sort_values("anteil", ascending=False))


# ── Geometrie der beiden Balken-Charts ─────────────────────────────────────
# Gemeldet am 18.08.2026 aus dem Gegentest: Bei zwei Strategien und der
# Aufteilung "Segment innerhalb Aktien" ueberdeckte die Legende die
# Achsenbeschriftung "Anteil am Depot". Nachgemessen:
#
#   Hoehe 220 px (Untergrenze), oberer Rand 30, unterer Rand NICHT gesetzt
#   -> Plotly-Standard 80  =>  Zeichenflaeche 110 px
#   Legende bei y = -0,12  =>  13 px darunter, im Band des Achsentitels
#   11 Segmente, fuenf davon ueber 18 Zeichen -> mehrere Legendenzeilen
#
# ZWEI URSACHEN, die zusammenwirkten:
#
# 1. `y = -0,12` ist relativ zur ZEICHENFLAECHE. Bei 110 px sind das 13 px,
#    bei 760 px waeren es 91 - der Abstand schrumpfte also genau dann, wenn
#    er am meisten gebraucht wird: bei WENIGEN Strategien.
# 2. Die Legende waechst nach unten, und niemand reservierte Platz.
#
# Dazu ein struktureller Mangel: Die alte `_balkenhoehe` kannte nur die Zahl
# der BALKEN. Die Zahl der SEGMENTE bestimmt den Platzbedarf mit, ging aber
# nirgends ein.
#
# WARUM DAS HIER EINE RECHNUNG IST UND KEINE SCHAETZUNG: Die naheliegende
# Loesung waere "schaetze, wie viele Legendeneintraege in eine Zeile passen" -
# also eine Annahme ueber Zeichenbreiten, und damit genau das, was CLAUDE.md
# seit dem 17.08.2026 verbietet. Plotly 6.9 macht sie ueberfluessig:
#
#   legend.entrywidthmode="fraction", entrywidth=1/3
#       -> GENAU drei Eintraege je Zeile. Die Zeilenzahl ist ceil(n/3),
#          exakt statt geraten.
#   legend.yref="container", yanchor="bottom", y=0
#       -> die Legende haengt am Rand der FIGUR statt an der Zeichenflaeche.
#          Ursache 1 kann damit nicht zurueckkommen.
#
# Drei je Zeile sind so gewaehlt, dass die laengste Beschriftung im Bestand
# ("Banken,Versicherer,Finanzdienstl.", 33 Zeichen) bequem passt.
LEGENDE_JE_ZEILE = 3

# Die EINE verbleibende Pixelannahme, und sie wird hier benannt statt
# versteckt: die Hoehe einer Legendenzeile. Sie ist beherrschbar, weil die
# Schriftgroesse der Legende ausdruecklich gesetzt wird (LEGENDE_SCHRIFT) -
# anders als bei `st.dataframe`, wo die Zeilenhoehe Streamlit gehoert und
# eine Annahme darueber beim naechsten Update still kippt (17.08.2026).
# Grosszuegig gewaehlt, nicht knapp.
LEGENDE_ZEILE_PX = 26
LEGENDE_SCHRIFT = 12

# Platz fuer Achsenbeschriftung und Achsentitel unterhalb der Zeichenflaeche.
ACHSE_UNTEN_PX = 58
RAND_OBEN_PX = 30

# AUSDRUECKLICHE LUFT zwischen Achsentitel und Legende. Ohne sie ginge die
# Rechnung zwar auf, aber knapp: Der Achsentitel sitzt rund 50 px unter der
# Zeichenflaeche, die Legende waechst von unten - bei vier Legendenzeilen
# blieben acht Pixel dazwischen. Genau diese Enge war der gemeldete Fehler,
# und ein Abstand, der sich rechnerisch gerade so ausgeht, ist keiner.
LEGENDE_ABSTAND_PX = 12

# Feste Hoehe je Balken statt einer Mindesthoehe fuer die ganze Figur
# (Philip, 18.08.2026): Zwei Strategien ergaben vorher zwei fette Kloetze auf
# 110 px Zeichenflaeche. Mit Deckel nach dem Vorbild der Heatmap
# (`risiko_ansicht._zeilenhoehe`): Wuerde die Zeichenflaeche zu hoch, schrumpft
# die Hoehe je Balken - bis zu einem Boden, unter dem nichts mehr lesbar ist.
BALKEN_HOEHE_PX = 44
BALKEN_HOEHE_MIN_PX = 26
ZEICHENFLAECHE_MAX_PX = 700


def balkenhoehe_je_zeile(anzahl):
    """Hoehe EINES Balkens. Konstant, bis der Deckel greift."""
    if anzahl <= 0:
        return BALKEN_HOEHE_PX
    if anzahl * BALKEN_HOEHE_PX <= ZEICHENFLAECHE_MAX_PX:
        return float(BALKEN_HOEHE_PX)
    return max(float(BALKEN_HOEHE_MIN_PX), ZEICHENFLAECHE_MAX_PX / anzahl)


def legendenzeilen(eintraege):
    """Wie viele Zeilen die Legende belegt - exakt, nicht geschaetzt."""
    if eintraege <= 0:
        return 0
    return -(-int(eintraege) // LEGENDE_JE_ZEILE)   # aufgerundete Division


def balken_geometrie(balken, legendeneintraege=0):
    """(hoehe, rand_unten) fuer ein waagerechtes Balken-Chart.

    Args:
        balken: Zahl der Strategien, also der Balken
        legendeneintraege: Zahl der Legendeneintraege; 0 heisst keine Legende

    Returns:
        (hoehe_px, rand_unten_px). `rand_unten` reserviert den Platz fuer
        Achsentitel UND Legende - der Achsentitel liegt darin oberhalb der
        Legende, und beide koennen sich nicht mehr ueberdecken.

    Beide Balken-Charts des Tabs nutzen dieselbe Rechnung. Die
    Ueberschneidung hat keine Legende (`showlegend=False`), also
    `legendeneintraege=0` - dieselbe Formel, ein Summand faellt weg.
    """
    zeilen = legendenzeilen(legendeneintraege)
    rand_unten = ACHSE_UNTEN_PX
    if zeilen:
        rand_unten += LEGENDE_ABSTAND_PX + zeilen * LEGENDE_ZEILE_PX
    zeichenflaeche = max(1, balken) * balkenhoehe_je_zeile(balken)
    return int(round(RAND_OBEN_PX + zeichenflaeche + rand_unten)), int(rand_unten)


def legenden_layout():
    """Die Legende unter dem Chart, am Rand der FIGUR verankert.

    yref="container" ist der Kern: Damit haengt die Legende am unteren Rand
    der Figur und nicht an der Zeichenflaeche, deren Hoehe je nach Zahl der
    Strategien zwischen 88 und 700 px schwankt. Der frueher benutzte
    Paper-Bezug (`y=-0.12`) machte den Abstand genau dort klein, wo er
    gebraucht wurde.
    """
    return dict(orientation="h", yref="container", yanchor="bottom", y=0,
                xref="paper", xanchor="left", x=0,
                entrywidthmode="fraction", entrywidth=1.0 / LEGENDE_JE_ZEILE,
                font=dict(size=LEGENDE_SCHRIFT))


def ueberschneidung_figur(tabelle, bezug, ebene, ansicht=UE_GEMEINSAM):
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

    exklusiv = ansicht == UE_EXKLUSIV
    fig = go.Figure(go.Bar(
        x=werte, y=namen, orientation="h",
        # Zwei Farben aus derselben Corporate-Palette, damit die Ansichten
        # unterscheidbar bleiben. Die FARBE TRAEGT DIE AUSSAGE NIE ALLEIN —
        # Schalter, Achsentitel, Kernsatz und Hover sagen alle dasselbe.
        marker=dict(color=FFPB_PALETTE[1] if exklusiv else FFPB_PALETTE[0]),
        # NUR DER PROZENTWERT am Balken (18.08.2026). Vorher stand dort
        # zusaetzlich die Zahl der gemeinsamen Titel — bei 18 Balken zwei
        # Angaben je Zeile, das wirkte unruhig. Die Zahl steht jetzt im Hover
        # und in der Ueberschrift des Drilldowns.
        text=[f"{w:.1f} %".replace(".", ",") for w in werte],
        textposition="outside", cliponaxis=False,
        # customdata traegt den NAMEN und die Zahl: den Namen braucht die
        # Klick-Auswahl (siehe `_gewaehlte_gegenpartei`), die Zahl der Hover.
        customdata=[[n, k] for n, k in zip(namen, schluessel)],
        hovertemplate=("<b>%{y}</b><br>"
                       + ("Nur im Bezugsdepot" if exklusiv
                          else "Überschneidung")
                       + ": %{x:.2f} %<br>"
                       + ("davon abweichend: " if exklusiv else "gemeinsam: ")
                       + "%{customdata[1]} " + einheit + "<extra></extra>"),
    ))
    hoehe, rand_unten = balken_geometrie(len(namen))
    fig.update_layout(
        height=hoehe,
        # Kurzer Achsentitel (18.08.2026): Der lange Satz gehoert unter das
        # Chart, nicht an die Achse.
        xaxis=dict(type="linear", ticksuffix=" %",
                   title=("Depotgewicht nur im Bezugsdepot" if exklusiv
                          else "gemeinsames Depotgewicht"),
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
        separators=",.", margin=dict(t=RAND_OBEN_PX, b=rand_unten),
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
    # AUF DER GATTUNGS-ACHSE liegen die Farben fest (18.08.2026). Auch die
    # Liquiditaet bekommt dort ihre kanonische Farbe statt des gedaempften
    # Grau: Sie IST auf dieser Achse eine Assetklasse und kein Sammelposten.
    # Auf den anderen Achsen bleibt sie grau, weil sie dort neben Kategorien
    # steht, zu denen sie nicht gehoert.
    fest = (achse == ACHSE_GATTUNG)

    fig = go.Figure()
    farb_index = 0
    for spalte in tabelle.columns:
        beschriftung = str(spalte)
        if fest and spalte != REST_OHNE_ANGABE:
            farbe = gattung_farbe(spalte)
        elif spalte in REST_FARBEN:
            farbe = REST_FARBEN[spalte]
        else:
            farbe = FFPB_PALETTE[farb_index % len(FFPB_PALETTE)]
            farb_index += 1
        werte = (tabelle[spalte] * 100.0).tolist()
        fig.add_trace(go.Bar(
            x=werte, y=namen, orientation="h", name=beschriftung,
            marker=dict(color=farbe),
            hovertemplate=("<b>%{y}</b><br>" + beschriftung
                           + ": %{x:.2f} %<extra></extra>"),
        ))
    hoehe, rand_unten = balken_geometrie(len(namen), len(tabelle.columns))
    fig.update_layout(
        barmode="stack",
        height=hoehe,
        xaxis=dict(type="linear", ticksuffix=" %", range=[0, 100],
                   title="Anteil am Depot"),
        # automargin: siehe `ueberschneidung_figur` — der linke Rand muss
        # sich nach den Strategienamen richten duerfen.
        yaxis=dict(type="category", categoryorder="array",
                   categoryarray=list(reversed(namen)), title=None,
                   automargin=True),
        separators=",.", margin=dict(t=RAND_OBEN_PX, b=rand_unten),
        legend=legenden_layout(),
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

    # EINE HALBE SPALTE, kein zweispaltiges Paar mehr (24.08.2026): Der
    # X-Achsen-Schalter ist nach unten gewandert, direkt ueber die Grafik —
    # dieselbe Anordnung wie bei der Heatmap im Performance-Reiter, die
    # dieselbe Aufgabe loest. Das Zeitraum-Feld bleibt trotzdem halbbreit;
    # ueber die ganze Seite gezogen sieht ein Dropdown mit sechs Eintraegen
    # aus, als haette es mehr zu sagen, als es hat.
    spalte_zeit, spalte_frei = st.columns([3, 1], vertical_alignment="bottom")
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
    with spalte_frei:
        # DASSELBE MUSTER WIE IM PERFORMANCE-REITER (`p_zeit_frei`): ein
        # Haekchen neben der Schnellwahl, das Kalenderfelder einblendet —
        # und KEIN weiterer Eintrag im Dropdown. Der Grund steht bei der
        # Kennung EIGEN oben: So kann ein Label, das `_perioden_start` nicht
        # lesen kann, dort gar nicht erst ankommen.
        eigener = st.checkbox(
            "Eigener Zeitraum", value=False, key="sv_zeit_frei",
            help="Blendet Kalenderfelder für Start und Ende ein.")

    reihen = [r for r in reihen_alle if r[0] in wahl]
    if not reihen:
        st.info("Keine Strategie gewählt — bitte mindestens eine auswählen.")
        return

    von = bis = None
    wirksam = periode
    if eigener:
        wirksam = EIGEN
        mind, maxd = zeitraum_grenzen(reihen)
        sd_vor, ed_vor = eigener_zeitraum_vorschlag(reihen, periode)

        # ZAEHLER-KEYS (#4): `st.session_state["sv_sd"] = ...` wirft bei einem
        # aktiven Widget eine StreamlitAPIException. Ein NEUER Key erzeugt
        # dagegen ein neues Widget, das seinen `value=`-Vorgabewert
        # uebernimmt — so setzt „Zuruecksetzen“ die Felder zurueck.
        if "sv_zeit_zaehler" not in st.session_state:
            st.session_state["sv_zeit_zaehler"] = 0
        n = st.session_state["sv_zeit_zaehler"]

        c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
        with c1:
            von = st.date_input("Start", value=sd_vor, min_value=mind,
                                max_value=maxd, format="DD.MM.YYYY",
                                key=f"sv_sd_{n}")
        with c2:
            bis = st.date_input("Ende", value=ed_vor, min_value=mind,
                                max_value=maxd, format="DD.MM.YYYY",
                                key=f"sv_ed_{n}")
        with c3:
            if st.button("Zurücksetzen", key="sv_zeit_reset", width="stretch",
                         help="Setzt Start und Ende auf die Schnellwahl "
                              "links zurück."):
                st.session_state["sv_zeit_zaehler"] += 1
                st.rerun()

        if von and bis and von > bis:
            # `return` und NICHT `st.stop()`: Diese Ansicht ist eine Funktion
            # innerhalb der Seite. `st.stop()` risse auch alles darunter weg,
            # und der Berater saehe eine halb leere Seite statt einer
            # Meldung, die sagt, was zu tun ist.
            st.error("Das Startdatum liegt nach dem Enddatum. Bitte den "
                     "Zeitraum korrigieren.")
            return

    tabelle = kennzahlen_je_strategie(reihen, wirksam, von=von, bis=bis)

    # Die Zeitraum-Caption bleibt BEIM ZEITRAUM-FELD und wandert nicht mit
    # nach unten: Jede Caption steht neben dem Bedienelement, das sie
    # erklaert. Zwei graue Zeilen gesammelt vor der Grafik waeren ein Block,
    # den niemand liest.
    hinweis = zeitraum_text(reihen, wirksam, von=von, bis=bis)
    if hinweis:
        st.caption(hinweis)

    # ── Der X-Achsen-Schalter, direkt ueber der Grafik ───────────────────
    #
    # segmented_control statt radio (18.08.2026, Philip): Die Heatmap
    # schaltet ihre zwei Ansichten genauso um, und zwei Bauformen für
    # dieselbe Aufgabe sehen ungleichmäßig aus. Seit dem 24.08.2026 steht er
    # auch an derselben STELLE wie dort — unter der Auswahl, ueber der
    # Grafik.
    #
    # required=True ist dabei nicht Kosmetik, sondern der Grund, warum
    # dieser Baustein hier überhaupt trägt: Ohne ihn lässt sich das
    # aktive Segment abwählen, und es gäbe den Zustand „keine X-Achse
    # gewählt" — denselben Fehler hat `p_zeitraum` schon einmal gehabt.
    #
    # ACHTUNG BEI KUENFTIGEN UMBAUTEN: `x_groesse` wird unten von
    # `punktwolke_figur` UND `_tabelle_zum_anzeigen` gelesen. Das Widget
    # muss im Quelltext vor beiden stehen. Wer es nach unten schoebe und
    # den Wert stattdessen aus `st.session_state` holte, bekaeme beim ersten
    # Lauf nach dem Umschalten die VORHERIGE Auswahl gezeichnet — lautlos.
    # Schritt 6 des Pruefsteins nagelt die Reihenfolge deshalb fest.
    if "sv_xachse" not in st.session_state:
        st.session_state["sv_xachse"] = X_VOLA
    x_groesse = st.segmented_control(
        "Risikomaß auf der X-Achse", list(X_ACHSEN), key="sv_xachse",
        required=True, label_visibility="collapsed",
        help=(f"„{X_VOLA}“ fragt, wie ruhig der Weg war — {X_DRAWDOWN} "
              "fragt, wie weh der schlimmste Moment tat."))
    st.caption(xachsen_hinweis(x_groesse))

    fig = punktwolke_figur(tabelle, x_groesse)

    if fig is None:
        st.warning(leer_hinweis(wirksam))
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


def auswahl_kennung(optionen):
    """Kurze, stabile Kennung einer Optionsmenge.

    Sie wird an den Widget-Schluessel gehaengt: Aendert sich die Menge, ist
    der Schluessel ein anderer, und Streamlit legt ein NEUES Widget an - eines,
    das gar keinen alten Wert tragen kann.

    SORTIERT, damit blosses Umsortieren keine neue Kennung ergibt. Die
    Reihenfolge der Strategien folgt der Auswahl des Beraters; sie kann sich
    aendern, ohne dass sich die MENGE aendert, und dann soll das Feld stehen
    bleiben.

    Leere Menge -> "leer", damit auch dieser Fall einen Schluessel hat.
    """
    if not optionen:
        return "leer"
    roh = "|".join(str(o) for o in sorted(optionen, key=str))
    return hashlib.blake2s(roh.encode("utf-8"), digest_size=4).hexdigest()


def auswahl_uebernehmen(vorher, optionen):
    """Welcher Wert soll im neuen Auswahlfeld stehen?

    Der bisherige, wenn es ihn noch gibt - sonst der erste. `None` bei leerer
    Optionsmenge.

    ENTSCHIEDEN (Philip, 18.08.2026): Wer von 19 Strategien auf die fuenf
    cVV-Reihen reduziert und "cVV konservativ" behaelt, soll seinen Bezug
    nicht verlieren. Wer ihn wegnimmt, bekommt sofort etwas Gueltiges statt
    einer leeren Ansicht.
    """
    if not optionen:
        return None
    return vorher if vorher in optionen else optionen[0]


def _waehle_gueltig(basis, optionen, beschriftung, hilfe=None):
    """Auswahlfeld, dessen Wert nicht ungueltig werden KANN.

    DER VORGAENGER RAEUMTE AUF UND HAT NICHT GETRAGEN. Er las den Wert aus
    dem session_state, verglich ihn mit den Optionen und loeschte den
    Schluessel, wenn er nicht mehr passte. Am 18.08.2026 gemeldet: Nach dem
    Reduzieren der Strategieauswahl auf zwei stand im Feld "Bezugsstrategie"
    weiter "cVV konservativ", und der Abschnitt zeigte keine Daten.

    Der Fehler war nicht die Bedingung, sondern die ANNAHME dahinter - dass
    ein geloeschter Schluessel geloescht bleibt. Ueber Streamlits
    Widget-Zustand laesst sich das von aussen nicht zusichern, und AppTest
    kann es nicht nachstellen: Drei Bedienwege probiert, in der Testumgebung
    griff der alte Schutz jedes Mal. Dieselbe Feststellung wie beim
    Keep-Alive am selben Vormittag (#64).

    JETZT STRUKTURELL: Der Widget-Schluessel traegt eine Kennung der
    Optionsmenge. Aendert sich die Menge, ist es ein anderes Widget, und ein
    Widget ohne Vorgeschichte kann keinen alten Wert zeigen. Dasselbe Muster
    wie beim Strategien-Mehrfachfeld darueber (#4, Loesung A).

    `index` UND NICHT eine Zuweisung an den session_state: `index` wirkt nur
    bei der ERSTEN Instanziierung eines Schluessels - also genau dann, wenn
    die Optionsmenge neu ist. Bei unveraenderten Optionen bleibt die Wahl des
    Beraters unangetastet. Und es wird nie ein Widget-Schluessel zugewiesen,
    womit die Falle aus #4 gar nicht erst auftreten kann.

    Der Merker (`<basis>_zuletzt`) ist ein GEWOEHNLICHER Schluessel und kein
    Widget-Schluessel. Das Keep-Alive darf ihn re-assignieren, und genau das
    soll es: Er ueberlebt damit den Ansichtswechsel.
    """
    if not optionen:
        return None
    merker = f"{basis}_zuletzt"
    start = auswahl_uebernehmen(st.session_state.get(merker), optionen)
    wahl = st.selectbox(beschriftung, optionen,
                        index=optionen.index(start),
                        key=f"{basis}_{auswahl_kennung(optionen)}", help=hilfe)
    st.session_state[merker] = wahl
    return wahl


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
    # DIE AUFLOESUNG SELBST STEHT SEIT DEM 24.08.2026 IN modules/auswahl.py.
    # Die Portfolioanalyse braucht dieselbe Mechanik fuer den Klick auf ein
    # Segment; zwei Kopien waeren genau die Krankheit, an der diese Codebasis
    # schon viermal gelitten hat (CLAUDE.md, "Wo was hingehoert"). Name,
    # Signatur und Verhalten dieser Funktion bleiben unveraendert — die
    # bestehenden Faelle in tests/test_strategievergleich.py sind damit der
    # Pruefstein der Delegation.
    return gewaehlter_balkenname(auswahl, list(tabelle.index))


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


def _drilldown_tabelle(bestaende, bezug, gegen, ebene,
                       ansicht=UE_GEMEINSAM):
    """Die Aufstellung hinter dem angeklickten Balken.

    Alle Zahlen sind FERTIG FORMATIERTE Zeichenketten aus `formats.fmt_pct` —
    deutsche Notation, Fehlwert "–", eine einzige Quelle. `st.column_config`
    waere die naheliegende Alternative und formatiert englisch.

    BEI UE_EXKLUSIV stehen hier NUR die Positionen der Bezugsstrategie. Was
    ausschliesslich die Gegenpartei haelt, fehlt bewusst: Diese Zeilen tragen
    0 zur Zahl im Balken bei, und eine Tabelle, deren Summe nicht die Zahl
    darueber ergibt, beantwortet die Frage nicht, fuer die sie da ist. Wer
    die andere Richtung sehen will, wechselt die Bezugsstrategie — der Satz
    unter dem Kernsatz sagt das und nennt die Summe.
    """
    exklusiv = ansicht == UE_EXKLUSIV
    if exklusiv:
        roh = exklusive_titel(bestaende[bezug], bestaende[gegen],
                              EBENEN[ebene])
        wert_spalte, wert_titel = "exklusiv", "nur hier"
    else:
        roh = gemeinsame_titel(bestaende[bezug], bestaende[gegen],
                               EBENEN[ebene])
        wert_spalte, wert_titel = "gemeinsam", "gemeinsam"
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
    if exklusiv:
        # "nur in A" heisst in der Anzeige "nur hier": Der Berater sieht
        # keinen Buchstaben A, sondern den Namen der Bezugsstrategie.
        spalten["Art"] = ["nur hier" if a == "nur in A" else "Übergewicht"
                          for a in roh["art"]]
    spalten[wert_titel] = [fmt_pct(v) for v in roh[wert_spalte]]
    return pd.DataFrame(spalten)


def ue_ansicht_hinweis(ansicht) -> str:
    """Ein Satz, der sagt, was gerade gezaehlt wird.

    Der Schalter traegt `label_visibility="collapsed"`; ohne diesen Satz
    stuenden zwei Woerter ueber dem Chart, deren Bedeutung man raten muesste.
    """
    if ansicht == UE_EXKLUSIV:
        return ("Gezählt wird, was die Bezugsstrategie **mehr** hält als die "
                "jeweils andere — je länger der Balken, desto weniger haben "
                "die beiden miteinander zu tun.")
    return ("Gezählt wird das jeweils **kleinere** der beiden Gewichte — je "
            "länger der Balken, desto ähnlicher sind sich die beiden.")


def ue_kernsatz(bezug, gegen, anteil, anzahl, ebene, ansicht) -> str:
    """Die Aussage des angeklickten Balkens in einem Satz."""
    einheit = ("Titel" if ebene == EBENE_TITEL else "Kategorien").lower()
    if ansicht == UE_EXKLUSIV:
        return (f"**{bezug}** hält **{fmt_pct(anteil)}** des Depotgewichts, "
                f"das **{gegen}** nicht hält — verteilt auf {int(anzahl)} "
                f"{einheit}.")
    return (f"**{bezug}** und **{gegen}** halten zu **{fmt_pct(anteil)}** "
            f"des Depotgewichts dasselbe — {int(anzahl)} gemeinsame "
            f"{einheit}.")


def ue_gegenrichtung_satz(bezug, gegen, wert_zurueck) -> str:
    """Nennt die andere Richtung — die Asymmetrie wird sichtbar statt versteckt.

    WARUM DER SATZ NOETIG IST: Die Überschneidung ist symmetrisch, die
    Nicht-Überschneidung nicht. Am 24.08.2026 gemessen: *cVV ausgewogen* hält
    25,30 % allein gegenüber *cVV defensiv plus*, umgekehrt sind es 24,34 %.
    Ohne diesen Hinweis läse man die Zahl als Eigenschaft des Paares und
    verstünde nicht, warum sie sich beim Wechsel der Bezugsstrategie ändert.
    Er erspart zugleich ein zweites Bedienelement.
    """
    return (f"Umgekehrt hält **{gegen}** {fmt_pct(wert_zurueck)} seines "
            f"Gewichts, das **{bezug}** nicht hält. Die Bezugsstrategie links "
            "tauscht die Richtung.")


def ue_summen_caption(anzahl, anteil, ansicht) -> str:
    """Der Satz unter der Aufstellung: die Zeilen ergeben die Zahl oben."""
    if ansicht == UE_EXKLUSIV:
        return (f"Die {anzahl} Beiträge summieren sich auf die "
                f"{fmt_pct(anteil)} oben — je Eintrag das Übergewicht der "
                "Bezugsstrategie. Was ausschließlich die andere Strategie "
                "hält, steht hier nicht; dafür die Bezugsstrategie wechseln.")
    return (f"Die {anzahl} Beiträge summieren sich auf die {fmt_pct(anteil)} "
            "oben — es ist je Eintrag das kleinere der beiden Gewichte.")


def ue_vorbehalt(stichtag_satz, ansicht) -> str:
    """Der gesammelte Hinweisblock unter dem Abschnitt.

    EIN Block statt drei einzelner Captions (18.08.2026): Drei graue Absätze
    hintereinander lesen sich wie Kleingedrucktes.
    """
    # DER WORTLAUT DER GEMEINSAM-FASSUNG BLEIBT UNVERAENDERT. Er wurde am
    # 18.08.2026 ausdruecklich als verstaendlich abgenommen; beim Umbau auf
    # zwei Ansichten stand hier kurz "desto hoeher faellt die
    # Ueberschneidung zwangslaeufig aus" — eine Verbesserung, die niemand
    # bestellt hatte, und der ui_dump-Vergleich hat sie gemeldet. Die
    # exklusive Fassung braucht ein eigenes Subjekt, weil "sie" dort auf
    # die falsche Groesse zeigte.
    ebenen_satz = (
        "Die Zahlen verschiedener **Ebenen** sind nicht vergleichbar: Je "
        "gröber die Ebene, desto höher fällt "
        + ("die Nicht-Überschneidung" if ansicht == UE_EXKLUSIV else "sie")
        + " zwangsläufig aus — dasselbe Paar liest sich auf Titelebene "
          "als 20,5 % und auf Gattungsebene als 73,8 %.  \n")
    if ansicht == UE_EXKLUSIV:
        return (stichtag_satz
                + " Gerechnet wird als Summe der Übergewichte gegenüber der "
                  "anderen Strategie. Zusammen mit der Überschneidung ergibt "
                  "das genau das investierte Gewicht der Bezugsstrategie — "
                  "die beiden Ansichten sind zwei Hälften derselben Zahl.  \n"
                + ebenen_satz
                + "**0 % sind nicht erreichbar**: Zwei Depots halten "
                  "unterschiedlich viel Kasse, und die zählt hier nicht mit. "
                  "Die Obergrenze ist das investierte Gewicht der "
                  "Bezugsstrategie, nicht 100 %.")
    return (stichtag_satz
            + " Gerechnet wird als Summe des jeweils kleineren Gewichts, die "
              "Gegengröße zur Active Share.  \n"
            + ebenen_satz
            + "**100 % sind nicht erreichbar**: Die Titelgewichte machen je "
              "nach Strategie nur 90 bis 98 % aus, der Rest ist Liquidität "
              "und zählt hier nicht mit.")


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

    # ── Der Umschalter, unter der Auswahl und ueber der Grafik ──────────
    # Dieselbe Stelle und dieselbe Bauform wie beim X-Achsen-Schalter und bei
    # der Heatmap. required=True: Ohne ihn liesse sich das aktive Segment
    # abwaehlen, und es gaebe den Zustand "keine Ansicht gewaehlt".
    if "sv_ue_ansicht" not in st.session_state:
        st.session_state["sv_ue_ansicht"] = UE_GEMEINSAM
    ansicht = st.segmented_control(
        "Ansicht", list(UE_ANSICHTEN), key="sv_ue_ansicht", required=True,
        label_visibility="collapsed",
        help=("„Gemeinsam“ fragt, wie ähnlich sich zwei Depots sind — "
              "„Nur im Bezugsdepot“ fragt, was der Kunde zusätzlich bekäme. "
              "Zusammen ergeben sie das investierte Gewicht."))
    st.caption(ue_ansicht_hinweis(ansicht))

    tabelle = ueberschneidung_tabelle(bestaende, bezug, EBENEN[ebene], ansicht)
    fig = ueberschneidung_figur(tabelle, bezug, ebene, ansicht)
    if fig is None:
        st.caption("Keine Vergleichsstrategie vorhanden.")
        return

    # on_select macht das Chart selbst zur Navigation — ein Klick auf einen
    # Balken oeffnet den Drilldown darunter. Bewusst KEIN zusaetzliches
    # Auswahlfeld: Es waere ein Bedienelement mehr fuer dieselbe Sache.
    #
    # DER KEY BLEIBT UEBER BEIDE ANSICHTEN DERSELBE, und das ist Absicht:
    # `gewaehlte_gegenpartei` loest ueber den NAMEN auf und nicht ueber den
    # Balkenindex. Beim Umschalten dreht sich die Reihenfolge — das gewaehlte
    # Paar bleibt trotzdem stehen. Genau dafuer wurde die Funktion gebaut.
    auswahl = st.plotly_chart(fig, config={"displayModeBar": False},
                              key="sv_ue_chart", on_select="rerun",
                              selection_mode="points")

    gegen = gewaehlte_gegenpartei(auswahl, tabelle)
    zeile = tabelle.loc[gegen]

    st.markdown(ue_kernsatz(bezug, gegen, zeile["anteil"],
                            zeile["schluessel"], ebene, ansicht))
    if ansicht == UE_EXKLUSIV:
        zurueck = nicht_ueberlappung(
            gewichte_je_kategorie(bestaende[gegen], EBENEN[ebene]),
            gewichte_je_kategorie(bestaende[bezug], EBENEN[ebene]))
        st.caption(ue_gegenrichtung_satz(bezug, gegen, zurueck))
    st.caption("Ein Klick auf einen Balken zeigt die Aufstellung dieses Paares.")

    anzeige = _drilldown_tabelle(bestaende, bezug, gegen, ebene, ansicht)
    if anzeige is not None:
        st.dataframe(anzeige, width="stretch", height="content",
                     hide_index=True)
        st.caption(ue_summen_caption(len(anzeige), zeile["anteil"], ansicht))

    st.caption(ue_vorbehalt(_stichtag_text(auswertungsdatum), ansicht))


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
