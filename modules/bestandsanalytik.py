"""
modules/bestandsanalytik.py — Mathematik auf dem BESTAND, streamlit-frei
(NEU 18.08.2026).

Abgegrenzt gegen `analytics.py`: Dort steht die Mathematik der ZEITREIHEN
(CAGR, Volatilität, Sharpe, Drawdown), die Tool *und* Broschüre teilen. Hier
steht, was auf den Einzeltiteln eines Stichtags rechnet — Gewichte je
Kategorie, Überschneidung zweier Depots, Liquidität.

WARUM STREAMLIT-FREI: Dieselbe Regel wie bei `formats.py` und
`anlagekriterien.py`. Die Bestands-Mathematik lag bisher ausschließlich in
`portfolioanalyse.py`, und die zieht Streamlit herein — jeder Prüfstein
musste deshalb die ganze Oberfläche mitladen. Was gerechnet wird, gehört an
einen Ort, den man ohne Oberfläche aufrufen kann.

HIER GEHÖREN AUF DAUER AUCH `build_allocation`, `get_bond_summary` und
`duration_info_aus_bestand` hin. Sie stehen noch in `portfolioanalyse.py`;
der Umzug war bewusst nicht Teil dieser Runde, damit die Änderung prüfbar
bleibt. Wer sie holt, findet hier den Platz dafür.

────────────────────────────────────────────────────────────────────────────
DAS ÜBERSCHNEIDUNGSMASS
────────────────────────────────────────────────────────────────────────────

    Überschneidung(A, B) = Σ min(w_A(i), w_B(i))    über alle Titel i

Das ist die etablierte Größe (die Gegenzahl zur *Active Share*) und im
Kundengespräch in einem Satz erklärbar: "Diese beiden Depots halten zu
69,6 % des Gewichts dieselben Titel."

WARUM NICHT DIE ZAHL DER GEMEINSAMEN TITEL: Zwei Depots können neun Titel
teilen, die zusammen 3 % wiegen — und zwei andere teilen drei Titel mit 40 %.
Eine Titelzahl beantwortet die Frage des Beraters nicht.

ZWEI EIGENSCHAFTEN, DIE MAN KENNEN MUSS:

1. **100 % sind unerreichbar.** Die Titelgewichte summieren sich je Portfolio
   auf 89,8 bis 98,2 % (am 18.08.2026 über alle 19 gemessen), der Rest ist
   Liquidität. Die Obergrenze eines Paares ist also `min(Σw_A, Σw_B)` und
   nicht 1,0. Bewusst NICHT wegnormiert: Eine Normierung auf "100 % = maximal
   möglich" würde zwei Depots mit viel Kasse ähnlicher aussehen lassen, als
   sie sind. Die Oberfläche sagt den Vorbehalt stattdessen dazu.

2. **Die Ebene entscheidet über die Zahl.** Dasselbe Maß auf gröberen
   Kategorien liefert zwangsläufig höhere Werte — bei vier Gattungen können
   sich zwei Depots kaum verfehlen. Am Paar *cVV ausgewogen* gegen
   *Comdirect 100* gemessen:

       Einzeltitel (166 Auspraegungen)   20,5 %
       Segment     ( 18)                 52,0 %
       Waehrung    (  6)                 60,6 %
       Region      ( 10)                 64,2 %
       Gattung     (  4)                 73,8 %

   ZAHLEN VERSCHIEDENER EBENEN DÜRFEN NICHT VERGLICHEN WERDEN. Wer "73,8 %"
   liest, ohne die Ebene zu kennen, hält zwei Depots für fast identisch, die
   auf Titelebene zu einem Fünftel übereinstimmen. Die Oberfläche nennt die
   Ebene deshalb immer mit.
"""

import numpy as np
import pandas as pd

# Die Spalte, in der das Gewicht steht — in `Daten_PF` dezimal, weil
# `portfolioanalyse.parse_pf_data` sie beim Einlesen durch 100 teilt.
GEWICHT_SPALTE = "Gewicht"

# Der fertig gelieferte Performancebeitrag (Gewicht x Wertentwicklung seit
# Jahresbeginn). Er wird NICHT hier gerechnet, sondern steht so in den
# Bestands-CSVs und ist additiv. `parse_pf_data` teilt auch ihn durch 100.
BEITRAG_SPALTE = "Performancebeitrag"

# Die Gattung ist die Ebene, INNERHALB derer ein Segment gelesen werden darf.
GATTUNG_SPALTE = "Gattung"

WERTPAPIER_SPALTE = "Wertpapier"
"""Klartextname des Titels. Ein Schluessel ist er NICHT — dafuer ist die WKN
da; derselbe Name kann in zwei Waehrungen gefuehrt sein."""

WKN_SPALTE = "WKN"
"""Der Titelschluessel dieser Datenquelle. Eine ISIN fuehren die CSVs nicht,
auch wenn `parse_pf_data` die Spalte vorsorglich aufraeumt."""

WP_PERF_SPALTE = "WP-Performance"
"""Wertentwicklung des Papiers selbst seit Jahresbeginn, UNGEWICHTET.

Nicht mit `BEITRAG_SPALTE` verwechseln: Diese Groesse ist NICHT additiv. Zwei
Papiere mit je 10 % Wertentwicklung ergeben nicht 20 % fuer das Depot — was
sich aufaddieren laesst, ist allein der Performancebeitrag."""

# Was in einer Kategoriespalte kein Schluessel ist, sondern ein Fehlwert.
_KEIN_SCHLUESSEL = ("", "nan", "none", "-")


def calc_liquidity(df: pd.DataFrame) -> float:
    """Liquiditaet = 1 minus Summe der Titelgewichte, nie negativ.

    UMGEZOGEN aus `portfolioanalyse.py` (18.08.2026), unveraendert. Sie wird
    jetzt an drei Stellen gebraucht (Ringe, Broschuere, Exposure-Vergleich),
    und eine zweite Kopie waere genau die Krankheit aus Backlog B/E/F.
    `portfolioanalyse` reicht den Namen per Zuweisung weiter.

    Der Boden bei 0.0 ist Absicht: Runden im Vorsystem kann die Summe minimal
    ueber 1.0 treiben, und eine negative Liquiditaet ist keine Aussage,
    sondern ein Artefakt.
    """
    total_weight = df[GEWICHT_SPALTE].sum()
    return max(0.0, 1.0 - total_weight)


def gewichte_je_kategorie(df: pd.DataFrame, spalte: str) -> pd.Series:
    """Gewicht je Auspraegung einer Spalte — aufgeraeumt und summiert.

    Args:
        df: Bestand einer Strategie (Ausgabe von `parse_pf_data`)
        spalte: z.B. "WKN", "Gattung", "Region", "Segment", "Währung"

    Returns:
        Series, Index = Auspraegung, Wert = Gewicht (dezimal). Leer, wenn die
        Spalte fehlt.

    DREI DINGE WERDEN AUFGERAEUMT, und jedes davon war schon einmal ein Fehler:

    1. DIE LEERE SCHLUSSZEILE. Jede CSV in `Daten_PF` endet mit einer Zeile
       ohne Werte. Am 17.08.2026 zaehlte "Anzahl Titel" sie mit und stand bei
       38 von 38 Dateien um genau 1 zu hoch. Zeilen ohne Kategorie fallen
       hier deshalb heraus.

    2. "nan" ALS TEXT. Die Dateien werden als Zeichenketten gelesen; ein
       fehlender Wert kommt als der String "nan" an und wuerde sonst zu einer
       eigenen Kategorie mit eigenem Balken (#41: "kein Wert" kommt in
       Finanzdaten oft nicht als NaN an).

    3. MEHRFACHE SCHLUESSEL. Auf Kategorieebene ist Summieren offensichtlich;
       auf WKN-Ebene ist es der Schutz davor, dass ein doppelt gefuehrter
       Titel beim Ueberschneidungsmass nur einmal zaehlt.
    """
    return _kategorie_summen(df, spalte, GEWICHT_SPALTE)


def _gueltige_schluessel(reihe: pd.Series) -> pd.Series:
    """Maske: welche Eintraege einer Kategoriespalte sind echte Schluessel?

    Erst die echten Fehlwerte, DANN die als Text getarnten. Die Reihenfolge
    ist nicht beliebig: `astype(str)` macht aus einem NA je nach
    pandas-Fassung entweder den String "nan" oder wieder ein NA — und ein NA
    ueberlebt den `isin`-Filter, weil `isin` fuer NA False liefert. Bis zum
    18.08.2026 hing das nur zufaellig daran, dass die leere Schlusszeile auch
    kein Gewicht traegt. Fuer "Waehrung" und "Marktrisikowert" gilt das nicht
    einmal sicher: `parse_pf_data` raeumt nur "Wertpapier", "WKN", "ISIN",
    "Segment", "Region", "Gattung" und "Portfolio Name" auf, diese beiden nicht.
    """
    echt = reihe.notna()
    text = reihe.astype(str).str.strip().str.lower()
    return echt & ~text.isin(_KEIN_SCHLUESSEL)


def _kategorie_summen(df: pd.DataFrame, spalte: str,
                      wert_spalte: str) -> pd.Series:
    """Summe einer Wertspalte je Auspraegung — der gemeinsame Rumpf.

    WARUM DAS HIER STEHT UND NICHT ZWEIMAL: Die drei Aufraeumregeln aus
    `gewichte_je_kategorie` gelten fuer JEDE Wertspalte. Waeren sie ein
    zweites Mal geschrieben worden, waere das dieselbe Krankheit wie in
    Backlog B/E/F — eine Funktion, die zweimal existiert und deren Kopien
    auseinanderlaufen. Aufgefallen ist die dort NIE durch verschiedene
    Formeln, sondern immer erst, als jemand die Kopien nebeneinanderlegte.
    """
    if spalte not in df.columns or wert_spalte not in df.columns:
        return pd.Series(dtype=float)
    d = df[[spalte, wert_spalte]].copy()
    d = d[_gueltige_schluessel(d[spalte])]
    if d.empty:
        return pd.Series(dtype=float)
    d[spalte] = d[spalte].astype(str).str.strip()
    d = d[d[wert_spalte].notna()]
    if d.empty:
        return pd.Series(dtype=float)
    return d.groupby(spalte)[wert_spalte].sum().astype(float)


def performancebeitrag_je_kategorie(df: pd.DataFrame, spalte: str,
                                    nur_gattung=None):
    """Performancebeitrag seit Jahresbeginn je Auspraegung einer Kategorie.

    Args:
        df: Bestand einer Strategie (Ausgabe von `parse_pf_data`), dezimal
        spalte: Kategoriespalte, in aller Regel "Segment"
        nur_gattung: wenn gesetzt, zaehlen nur Zeilen dieser Gattung

    Returns:
        (reihe, ohne_zuordnung, n_ohne)
            reihe           Series, Index = Auspraegung, Wert = Summe des
                            Beitrags (dezimal), ABSTEIGEND sortiert
            ohne_zuordnung  Summe der Beitraege, die keiner Auspraegung
                            zugeordnet werden konnten (dezimal)
            n_ohne          Zahl dieser Zeilen

    HIER WIRD NICHTS GERECHNET, NUR ZUSAMMENGEZAEHLT. Die Spalte
    `Performancebeitrag` kommt fertig aus der Quelle und ist additiv; sie ist
    NICHT das Produkt aus Stichtagsgewicht und Stichtagsperformance (am
    24.08.2026 gemessen: je Titel bis zu 0,48 Prozentpunkte Unterschied).
    Wer sie nachbauen will, rechnet etwas anderes aus.

    WARUM `nur_gattung` KEIN LUXUS IST: Die Spalte "Segment" traegt ZWEI
    Bedeutungen — bei Aktien Branchen, bei Renten Schuldnerklassen
    (Festlegung Philip, 18.08.2026; ausfuehrlich in `strategievergleich.py`).
    Am 24.08.2026 an *cVV ausgewogen* gemessen: "Eisen,Stahl,Rohstoffe" steht
    unter Aktien bei -0,159 % und unter Edelmetallen bei +0,574 %. Flach
    aggregiert kaeme +0,415 % heraus — eine Zahl, die es in keiner der beiden
    Gattungen gibt, und zwar mit dem FALSCHEN VORZEICHEN.

    DIE ZUSAGE, an die ein Pruefstein sich haelt:

        reihe.sum() + ohne_zuordnung == Summe des Beitrags der gezaehlten
                                        Zeilen

    `ohne_zuordnung` wird dabei EIGENSTAENDIG gebildet und nicht als Rest
    ausgerechnet — sonst waere die Zusage per Konstruktion wahr und der
    Pruefstein pruefte nichts.

    EIN FEHLWERT IST KEIN MESSWERT (#46): Fehlt die Spalte, ist der Bestand
    leer oder traegt die Gattung keine Zeile, kommt eine LEERE Reihe zurueck
    — nie eine Kategorie mit dem Wert 0.
    """
    if df is None or len(df) == 0:
        return pd.Series(dtype=float), 0.0, 0
    if spalte not in df.columns or BEITRAG_SPALTE not in df.columns:
        return pd.Series(dtype=float), 0.0, 0

    d = df
    if nur_gattung is not None:
        if GATTUNG_SPALTE not in df.columns:
            return pd.Series(dtype=float), 0.0, 0
        d = df[df[GATTUNG_SPALTE].astype(str).str.strip()
               == str(nur_gattung).strip()]
    if len(d) == 0:
        return pd.Series(dtype=float), 0.0, 0

    # Nur Zeilen, die ueberhaupt einen Beitrag tragen. Eine Zeile ohne
    # Beitrag geht niemandem verloren — sie traegt nichts bei, weder zu einer
    # Kategorie noch zu `ohne_zuordnung`. Die leere Schlusszeile jeder CSV
    # faellt genau hier heraus.
    mit_wert = d[d[BEITRAG_SPALTE].notna()]
    if mit_wert.empty:
        return pd.Series(dtype=float), 0.0, 0

    gueltig = _gueltige_schluessel(mit_wert[spalte])
    ohne_zuordnung = float(mit_wert.loc[~gueltig, BEITRAG_SPALTE].sum())
    n_ohne = int((~gueltig).sum())

    reihe = _kategorie_summen(mit_wert, spalte, BEITRAG_SPALTE)
    return reihe.sort_values(ascending=False), ohne_zuordnung, n_ohne


def titel_je_auspraegung(df: pd.DataFrame, spalte: str, wert,
                         nur_gattung=None) -> pd.DataFrame:
    """Die Einzeltitel hinter EINER Auspraegung einer Kategorie.

    Das Gegenstueck zu `performancebeitrag_je_kategorie`: Dort steht die
    Summe je Auspraegung, hier stehen die Zeilen, aus denen sie entsteht.
    Bewusst dieselbe Argumentfolge `(df, spalte, ..., nur_gattung)`, damit
    sich die beiden nebeneinanderlegen lassen — sonst waere die Zusage unten
    nicht nachpruefbar.

    Args:
        df: Bestand eines Stichtags (Ausgabe von `parse_pf_data`)
        spalte: die Kategoriespalte, z.B. "Segment"
        wert: die Auspraegung, deren Titel gesucht sind
        nur_gattung: falls gesetzt, nur Titel dieser Gattung

    Returns:
        DataFrame mit `wertpapier`, `wkn`, `gewicht`, `beitrag`,
        `wp_performance` (alles dezimal), absteigend nach `beitrag`.
        Bei leerem Ergebnis ein LEERER DataFrame MIT diesen Spalten — nie
        None, damit die Aufrufer nicht zwei Faelle unterscheiden muessen.

    DIE ZUSAGE, AUF DIE ES ANKOMMT:

        titel_je_auspraegung(df, "Segment", s, g)["beitrag"].sum()
        == performancebeitrag_je_kategorie(df, "Segment", g)[0][s]

    Sie haelt nur, solange BEIDE Funktionen dieselben Zeilen wegwerfen —
    Gattungsfilter, `notna` auf dem Beitrag und `_gueltige_schluessel`, und
    zwar in dieser Reihenfolge. Deshalb steht die Auswahl hier Schritt fuer
    Schritt neben der dortigen und nicht in einer eigenen Kurzfassung. Am
    24.08.2026 ueber 19 Strategien und 178 Gattung/Segment-Kombinationen
    gemessen: groesste Abweichung 3,5e-18.

    FEHLT `WP-Performance`, KOMMT EINE NaN-SPALTE UND KEINE NULL (#46): Eine
    Wertentwicklung von 0 % ist eine Aussage, eine fehlende ist keine.
    """
    spalten = ["wertpapier", "wkn", "gewicht", "beitrag", "wp_performance"]
    leer = pd.DataFrame({s: pd.Series(dtype=float) for s in spalten})

    if df is None or len(df) == 0:
        return leer
    if spalte not in df.columns or BEITRAG_SPALTE not in df.columns:
        return leer

    d = df
    if nur_gattung is not None:
        if GATTUNG_SPALTE not in df.columns:
            return leer
        d = df[df[GATTUNG_SPALTE].astype(str).str.strip()
               == str(nur_gattung).strip()]
    if len(d) == 0:
        return leer

    mit_wert = d[d[BEITRAG_SPALTE].notna()]
    if mit_wert.empty:
        return leer

    gueltig = _gueltige_schluessel(mit_wert[spalte])
    treffer = mit_wert[gueltig & (mit_wert[spalte].astype(str).str.strip()
                                  == str(wert).strip())]
    if treffer.empty:
        return leer

    def _spalte(name):
        if name in treffer.columns:
            return list(treffer[name])
        return [float("nan")] * len(treffer)

    raus = pd.DataFrame({
        "wertpapier": _spalte(WERTPAPIER_SPALTE),
        "wkn": _spalte(WKN_SPALTE),
        "gewicht": _spalte(GEWICHT_SPALTE),
        "beitrag": [float(v) for v in treffer[BEITRAG_SPALTE]],
        "wp_performance": _spalte(WP_PERF_SPALTE),
    })
    # mergesort ist stabil: Zwei Titel mit demselben Beitrag behalten die
    # Reihenfolge der Quelle und tauschen nicht bei jedem Neuzeichnen.
    return raus.sort_values("beitrag", ascending=False,
                            kind="mergesort").reset_index(drop=True)


def ueberlappung(a: pd.Series, b: pd.Series) -> float:
    """Summe der kleineren Gewichte ueber die gemeinsamen Schluessel.

    Args:
        a, b: Ausgaben von `gewichte_je_kategorie` derselben Ebene

    Returns:
        Anteil des Depotgewichts, den beide gemeinsam halten (dezimal).
        0.0, wenn es keinen gemeinsamen Schluessel gibt.

    SYMMETRISCH, und `ueberlappung(a, a)` ist die Summe von `a` — NICHT 1,0.
    Beides ist per Pruefstein festgenagelt; das zweite ist die knappste
    Formulierung des Vorbehalts aus dem Modul-Docstring.
    """
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return 0.0
    gemeinsam = a.index.intersection(b.index)
    if len(gemeinsam) == 0:
        return 0.0
    return float(np.minimum(a.reindex(gemeinsam).to_numpy(dtype=float),
                            b.reindex(gemeinsam).to_numpy(dtype=float)).sum())


def gemeinsame_schluessel(a: pd.Series, b: pd.Series) -> int:
    """Wie viele Schluessel beide fuehren — die Begleitzahl zur Ueberlappung.

    Sie steht in der Oberflaeche NEBEN dem Prozentwert und nicht statt
    seiner: Erst beide zusammen sagen, ob eine hohe Zahl aus wenigen schweren
    oder vielen leichten Titeln kommt.
    """
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return 0
    return int(len(a.index.intersection(b.index)))


# Was in der Gattungsspalte steht, wenn es zum Schluessel keinen Klartext
# gibt — auf groeberen Ebenen ist das der Normalfall, kein Fehler.
KEIN_KLARTEXT = "–"


def _klartext_spalte(df, schluessel_spalte, quelle):
    """{schluessel: Wert} aus einer Begleitspalte, ohne Fehlwerte."""
    if df is None or schluessel_spalte not in df.columns \
            or quelle not in df.columns:
        return {}
    d = df[[schluessel_spalte, quelle]].dropna()
    d = d.astype(str).apply(lambda sp: sp.str.strip())
    d = d[~d[quelle].str.lower().isin(_KEIN_SCHLUESSEL)]
    return dict(zip(d[schluessel_spalte], d[quelle]))


def _klartext_und_gattung(df_a, df_b, spalte):
    """(namen, gattungen) zu den Schluesseln — leer auf groeberen Ebenen.

    NUR AUF WKN-EBENE gibt es einen Klartextnamen und eine Gattung zum
    Schluessel. Auf groeberen Ebenen IST der Schluessel schon der Klartext
    ("Aktien", "Nordamerika") — eine Zuordnung Schluessel -> Wertpapier
    wuerde dort "Aktien" auf irgendeinen Wertpapiernamen abbilden, weil je
    Gattung viele Zeilen in Frage kommen und die letzte gewinnt. Genau so
    war `gemeinsame_titel` beim ersten Schreiben gebaut.

    HERAUSGELOEST am 24.08.2026, als `exklusive_titel` dazukam: Der Block
    lag als Closure in `gemeinsame_titel`. Ein zweites Mal geschrieben waere
    er dieselbe Krankheit wie in Backlog B/E/F — zwei Kopien, die
    auseinanderlaufen, ohne dass es jemandem auffaellt.

    `df_a` gewinnt bei Namensgleichheit, weil es die Bezugsstrategie ist.
    """
    if spalte != "WKN":
        return {}, {}
    namen = {**_klartext_spalte(df_b, spalte, "Wertpapier"),
             **_klartext_spalte(df_a, spalte, "Wertpapier")}
    gattungen = {**_klartext_spalte(df_b, spalte, "Gattung"),
                 **_klartext_spalte(df_a, spalte, "Gattung")}
    return namen, gattungen


def nicht_ueberlappung(a: pd.Series, b: pd.Series) -> float:
    """Der Teil des Depotgewichts von `a`, den `b` NICHT haelt.

        Nicht-Ueberschneidung(A, B) = Summe max(0, w_A(i) - w_B(i))

    ueber die Vereinigung der Schluessel. Fehlt ein Titel in `b`, zaehlt sein
    volles Gewicht; haelt `b` ihn kleiner, zaehlt die Differenz.

    NICHT SYMMETRISCH — und das ist keine Schwaeche, sondern die Aussage:
    Die Frage "was habe ich, das der andere nicht hat" hat eine Richtung. Am
    24.08.2026 gemessen: *cVV ausgewogen* haelt 25,30 % allein gegenueber
    *cVV defensiv plus*, umgekehrt sind es 24,34 %. Die Oberflaeche nennt die
    Gegenrichtung deshalb im Klartext, statt sie zu verschweigen.

    DIE ZUSAGE, die alles zusammenhaelt:

        nicht_ueberlappung(a, b) + ueberlappung(a, b) == a.sum()

    Damit haengt die neue Zahl an der vorhandenen UND am Investitionsgrad,
    den der Berater aus der Portfolioanalyse kennt — sie laesst sich am
    Bildschirm nachrechnen.

    WARUM NICHT die L1-Distanz `Summe |w_A - w_B|`: Die waere symmetrisch und
    als "Unterschied" ebenso denkbar — sie kann aber UEBER 100 % gehen; bei
    *cVV ausgewogen* gegen *Comdirect_100* sind es 148,7 %. Eine Prozentzahl
    ueber 100 neben einem Mass mit Deckel 100 ist ein Missverstaendnis mit
    Ansage. Verworfen am 24.08.2026, die Gegenprobe steht im Pruefstein.

    OBERGRENZE IST `a.sum()`, NICHT 1,0 — aus demselben Grund, aus dem die
    Ueberschneidung 100 % nicht erreicht: Die Titelgewichte summieren sich je
    Portfolio nur auf 90 bis 98 %, der Rest ist Liquiditaet.
    """
    if a is None or len(a) == 0:
        return 0.0
    if b is None or len(b) == 0:
        return float(a.sum())
    idx = a.index.union(b.index)
    av = a.reindex(idx).fillna(0.0).to_numpy(dtype=float)
    bv = b.reindex(idx).fillna(0.0).to_numpy(dtype=float)
    return float(np.maximum(av - bv, 0.0).sum())


def exklusive_schluessel(a: pd.Series, b: pd.Series) -> int:
    """Wie viele Schluessel traegt `a` staerker als `b`?

    Das Gegenstueck zu `gemeinsame_schluessel` und die Zahl der Zeilen, die
    `exklusive_titel` liefert. Sie steht hier und nicht in der Oberflaeche,
    damit beide Seiten dieselbe Zaehlweise benutzen.
    """
    if a is None or len(a) == 0:
        return 0
    if b is None or len(b) == 0:
        return int(len(a))
    idx = a.index.union(b.index)
    av = a.reindex(idx).fillna(0.0).to_numpy(dtype=float)
    bv = b.reindex(idx).fillna(0.0).to_numpy(dtype=float)
    return int((av > bv).sum())


def exklusive_titel(df_a, df_b, spalte: str = "WKN") -> pd.DataFrame:
    """Woraus setzt sich der exklusive Teil von A zusammen?

    Args:
        df_a: Bestand der BEZUGSSTRATEGIE
        df_b: Bestand der Gegenpartei
        spalte: Ebene, auf der verglichen wird

    Returns:
        DataFrame, absteigend nach "exklusiv", mit den Spalten
            schluessel, bezeichnung, gattung, gewicht_a, gewicht_b,
            exklusiv   max(0, gewicht_a - gewicht_b) — der BEITRAG
            art        "nur in A" (die Gegenpartei haelt ihn gar nicht)
                       oder "Uebergewicht" (sie haelt ihn, nur kleiner)

    Zeilen mit `exklusiv == 0` fallen heraus: Sie tragen nichts bei, und eine
    Aufstellung, deren Zeilen sich nicht auf ihre Summe addieren, beantwortet
    die Frage nicht, fuer die sie da ist.

    DIE ZUSAGE: `exklusive_titel(A, B)["exklusiv"].sum()`
                == `nicht_ueberlappung(gewichte(A), gewichte(B))`

    WAS HIER BEWUSST NICHT STEHT: die Titel, die nur die GEGENPARTEI haelt.
    Sie tragen 0 zur Zahl bei; sie aufzunehmen zerstoerte die Zusage oben und
    damit den Zusammenhang zwischen Balken und Tabelle. Wer sie sehen will,
    wechselt die Bezugsstrategie — dieselbe Funktion mit vertauschten
    Argumenten liefert sie.

    Das Gegenstueck ist `gemeinsame_titel`; die beiden teilen sich absichtlich
    den Aufbau, damit man sie nebeneinanderlegen kann.
    """
    leer = pd.DataFrame(columns=["schluessel", "bezeichnung", "gattung",
                                 "gewicht_a", "gewicht_b", "exklusiv", "art"])
    a = gewichte_je_kategorie(df_a, spalte)
    if a.empty:
        return leer
    b = gewichte_je_kategorie(df_b, spalte)
    namen, gattungen = _klartext_und_gattung(df_a, df_b, spalte)

    zeilen = []
    for schluessel, gewicht_a in a.items():
        gewicht_b = float(b.get(schluessel, 0.0)) if len(b) else 0.0
        beitrag = float(gewicht_a) - gewicht_b
        if beitrag <= 0:
            continue
        zeilen.append({
            "schluessel":  schluessel,
            "bezeichnung": namen.get(schluessel, schluessel),
            "gattung":     gattungen.get(schluessel, KEIN_KLARTEXT),
            "gewicht_a":   float(gewicht_a),
            "gewicht_b":   gewicht_b,
            "exklusiv":    beitrag,
            "art":         "nur in A" if gewicht_b == 0.0 else "Uebergewicht",
        })
    if not zeilen:
        return leer
    return (pd.DataFrame(zeilen)
            .sort_values("exklusiv", ascending=False)
            .reset_index(drop=True))


def gemeinsame_titel(df_a: pd.DataFrame, df_b: pd.DataFrame,
                     spalte: str = "WKN") -> pd.DataFrame:
    """Welche Titel halten beide Depots — und wie viel davon ist gemeinsam?

    Args:
        df_a, df_b: Bestaende zweier Strategien
        spalte: Schluesselspalte, in aller Regel "WKN"

    Returns:
        DataFrame, absteigend nach "gemeinsam"; Spalten:
            schluessel   der Wert der Schluesselspalte (WKN)
            bezeichnung  Klartextname des Wertpapiers
            gattung      Aktien / Renten / Edelmetalle / ...
            gewicht_a    Gewicht im ersten Depot (dezimal)
            gewicht_b    Gewicht im zweiten Depot
            gemeinsam    min(gewicht_a, gewicht_b) — der BEITRAG dieses Titels

    DIE ZUSAGE, DIE DIESE FUNKTION TRAEGT:

        gemeinsame_titel(a, b)["gemeinsam"].sum() == ueberlappung(A, B)

    Die Uebersicht sagt, DASS zwei Depots zu 69,56 % dasselbe halten; diese
    Funktion sagt, WORAUS sich das zusammensetzt — und beide Zahlen muessen
    exakt zusammenpassen, sonst zeigt die Ansicht zwei verschiedene
    Wahrheiten uebereinander. Der Pruefstein misst das ueber alle 171 Paare.

    KEINE KUERZUNG AUF "TOP N". Die fuenf groessten Beitraege machen am
    18.08.2026 nur 33 % der Ueberschneidung aus; eine gekuerzte Liste
    verschwiege zwei Drittel und waere wieder ein Aggregat, das nicht sagt,
    was es nicht enthaelt (#59). Wer weniger sehen will, sortiert oder
    filtert in der Tabelle.

    Der KLARTEXTNAME kommt aus dem ersten Depot und faellt auf das zweite
    zurueck: Dieselbe WKN kann in zwei Lieferungen unterschiedlich
    geschrieben sein, und der Schluessel ist die WKN, nicht der Name.
    """
    leer = pd.DataFrame(columns=["schluessel", "bezeichnung", "gattung",
                                 "gewicht_a", "gewicht_b", "gemeinsam"])
    a = gewichte_je_kategorie(df_a, spalte)
    b = gewichte_je_kategorie(df_b, spalte)
    gemeinsam = a.index.intersection(b.index)
    if len(gemeinsam) == 0:
        return leer

    namen, gattungen = _klartext_und_gattung(df_a, df_b, spalte)

    zeilen = []
    for schluessel in gemeinsam:
        wa, wb = float(a[schluessel]), float(b[schluessel])
        zeilen.append({
            "schluessel":  schluessel,
            "bezeichnung": namen.get(schluessel, schluessel),
            "gattung":     gattungen.get(schluessel, KEIN_KLARTEXT),
            "gewicht_a":   wa,
            "gewicht_b":   wb,
            "gemeinsam":   min(wa, wb),
        })
    return (pd.DataFrame(zeilen)
            .sort_values("gemeinsam", ascending=False)
            .reset_index(drop=True))


def kategorien_vereinigt(reihen: dict, spalte: str) -> list:
    """Alle Auspraegungen ueber MEHRERE Bestaende, nach Gesamtgewicht sortiert.

    Args:
        reihen: {label: Bestands-DataFrame}
        spalte: die Kategoriespalte

    Returns:
        Liste der Auspraegungen, schwerste zuerst.

    WARUM DIE KATEGORIEN UEBER ALLE STRATEGIEN GEMEINSAM BESTIMMT WERDEN:
    `portfolioanalyse.build_allocation` fasst Kategorien unter 3 % zu
    "Sonstige" zusammen — je Strategie einzeln. Fuer einen Ring ist das
    richtig, fuer einen VERGLEICH waere es fatal: Dieselbe Region stuende bei
    der einen Strategie als eigener Balken und waere bei der naechsten in
    "Sonstige" verschwunden, ohne dass man es sieht.

    Dieselbe Lehre wie bei der Farbskala der Heatmap (14.08.2026): Was
    verglichen werden soll, muss fest sein und darf nicht von den Daten der
    einzelnen Reihe abhaengen.
    """
    gesamt = {}
    for df in reihen.values():
        for schluessel, wert in gewichte_je_kategorie(df, spalte).items():
            gesamt[schluessel] = gesamt.get(schluessel, 0.0) + float(wert)
    return [k for k, _ in sorted(gesamt.items(), key=lambda p: -p[1])]
