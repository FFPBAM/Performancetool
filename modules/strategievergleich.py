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
from modules.formats import fmt_pct
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


def zeige_strategievergleich(reihen_alle, familien_reihenfolge=()):
    """Die Ansicht. `reihen_alle` ist (label, ts_df, fee_dec, familie) je Strategie."""
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
                               key="sv_periode")
    with spalte_x:
        x_groesse = st.radio("Risikomaß auf der X-Achse", X_ACHSEN,
                             horizontal=True, key="sv_xachse")

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

    st.caption("Gerechnet wird je Strategie mit ihrem hinterlegten "
               "Honorarsatz, nach Kosten — wie in der Broschüre. Das "
               "Honorarfeld der Performance-Ansicht wirkt hier nicht.")

    if fig is not None and st.checkbox("Tabelle anzeigen", key="sv_tabelle"):
        st.dataframe(_tabelle_zum_anzeigen(tabelle, x_groesse),
                     width="stretch", height="content", hide_index=True)
