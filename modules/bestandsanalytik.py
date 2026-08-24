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

    def _klartext(df, quelle):
        """{schluessel: Wert} aus einer Begleitspalte, ohne Fehlwerte."""
        if spalte not in df.columns or quelle not in df.columns:
            return {}
        d = df[[spalte, quelle]].dropna()
        d = d.astype(str).apply(lambda sp: sp.str.strip())
        d = d[~d[quelle].str.lower().isin(("", "nan", "none", "-"))]
        return dict(zip(d[spalte], d[quelle]))

    # NUR AUF WKN-EBENE gibt es einen Klartextnamen und eine Gattung zum
    # Schluessel. Auf groeberen Ebenen IST der Schluessel schon der Klartext
    # ("Aktien", "Nordamerika") — eine Zuordnung Schluessel -> Wertpapier
    # wuerde dort "Aktien" auf irgendeinen Wertpapiernamen abbilden, weil je
    # Gattung viele Zeilen in Frage kommen und die letzte gewinnt. Genau so
    # war diese Funktion beim ersten Schreiben gebaut.
    if spalte == "WKN":
        namen = {**_klartext(df_b, "Wertpapier"), **_klartext(df_a, "Wertpapier")}
        gattungen = {**_klartext(df_b, "Gattung"), **_klartext(df_a, "Gattung")}
    else:
        namen, gattungen = {}, {}

    zeilen = []
    for schluessel in gemeinsam:
        wa, wb = float(a[schluessel]), float(b[schluessel])
        zeilen.append({
            "schluessel":  schluessel,
            "bezeichnung": namen.get(schluessel, schluessel),
            "gattung":     gattungen.get(schluessel, "–"),
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
