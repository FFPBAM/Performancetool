# modules/stammdaten.py
"""Die Stammdaten der Strategien — EINE Datei, EIN Lesepfad, EINE Stelle
für die Spaltennamen.

Bis zum 23.09.2026 lagen die Stammdaten in DREI Excel-Dateien
(`Mapping_Namen.xlsx`, `Mapping_Honorarsatz.xlsx`,
`Mapping_Anlagekriterien.xlsx`) mit zwei verschiedenen Join-Schlüsseln, und
der Code griff auf die erste davon POSITIONELL zu: `columns[0]`,
`columns[1]`, `columns[3]`. Das hielt genau so lange, wie niemand eine
Spalte einfügte, löschte oder verschob. Aufgefallen ist die Falle bei der
Frage, ob man die tote Spalte „Duration" entfernen kann: Sie stand an
Position 2, und ihr Wegfall hätte die Familien-Spalte zur Benchmark
gemacht — lautlos, bis in die Kundenbroschüre.

Jetzt gibt es `Mapping_Strategien.xlsx`, Blatt „Strategien": eine Zeile je
Strategie, zehn Spalten, alles nebeneinander. Der Zugriff läuft über
`spalte()`; fehlt eine Spalte, WIRFT das und nennt Datei und Spalte beim
Namen.

VORGESCHICHTE:
    Zwischen dem Aufnehmen der neuen Datei und dem Entfernen der alten gab
    es eine Rückfallebene, die den Frame aus den drei Vorgängerdateien baute.
    Sie ist mit Etappe 4 entfallen, nachdem beide Wege nachweislich dasselbe
    lieferten und die alten Dateien aus dem Repo verschwunden sind.

WARUM DIESES MODUL STREAMLIT-FREI IST:
    Dasselbe Argument wie zuvor bei ``modules/anlagekriterien.py``: der
    Broschüren-Export (``pptx_export.py``) soll ohne Streamlit aus einem
    Batch-Skript laufen können. Der ``@st.cache_data``-Deckel liegt allein
    in ``shared.py``; hier steht die Logik.

EIN LESEPFAD:
    ``lade()`` ist das einzige ``pd.read_excel`` auf eine Mapping-Datei im
    ganzen Projekt. Das ist keine Absichtserklärung, sondern geprüft —
    ``tests/test_stammdaten.py`` liest dafür den Syntaxbaum aller Module.
"""

import os

import pandas as pd

PFAD = "Mapping_Strategien.xlsx"
BLATT = "Strategien"

# Für Fehlermeldungen: der Name der Datei, die der Leser vor sich hat.
# Beide Namen zeigen auf dieselbe Datei; sie bleiben, weil Aufrufer und
# Prüfsteine sie kennen.
DATEI_STRATEGIEN = PFAD
DATEI_HONORAR = PFAD

# ── Die Spalten von Mapping_Strategien.xlsx ─────────────────────────────
SP_ANZEIGE = "Strategie auswählen"       # Anzeigename, Auswahlfeld + Code
SP_CSV_NAME = "CSV-Portfolioname"        # Schlüssel aus dem Bestandssystem
SP_FAMILIE = "Powerpoint Familie"        # steuert Vorlage und Config
SP_SATZ = "Honorarsatz Standard"         # Nettosatz p.a., dezimal
SP_ANZEIGENAME = "Anzeigename"           # Kopfzeile des Kriterien-Kastens
SP_BENCHMARK = "Benchmark"               # Freitext für die ***-Fußnote (F8)

# ACHTUNG zu SP_CSV_NAME: Der Wert kommt aus dem Bestandssystem und ist NICHT
# frei wählbar. Er steht wortgleich in der CSV-Spalte „Portfolio Name" und
# ist der Schlüssel von HISTORIE_AB. Bis zum 23.09.2026 hieß die Spalte
# „Honorarsatz Mapping" — ein irreführender Kopf, denn ein Honorarschlüssel
# stand dort nie.

# Die vier Kriterien in der Reihenfolge der Vorlagen-Tabelle. Die
# Spaltennamen SIND die gedruckten Beschriftungen — keine zweite Liste, die
# auseinanderlaufen kann. (Übernommen aus anlagekriterien.SPALTEN.)
SP_KRITERIEN = ("Anlageregion", "Aktienanteil",
                "Anleihenanteil / Liquidität", "Fremdwährungen")

ALLE_SPALTEN = (SP_ANZEIGE, SP_CSV_NAME, SP_FAMILIE, SP_SATZ, SP_ANZEIGENAME,
                *SP_KRITERIEN, SP_BENCHMARK)

# Ohne diese vier kann der Lesepfad nicht arbeiten. Die Kriterien-Spalten
# gehören NICHT dazu: Eine Strategie ohne Kriterien ist ein gültiger Zustand
# (beide SCHWEIZ), ihr Kasten bleibt dann weg.
PFLICHT = (SP_ANZEIGE, SP_CSV_NAME, SP_FAMILIE, SP_BENCHMARK)

# Rückwärtskompatible Namen — der Honorarsatz-Frame trägt weiter die
# Spaltenköpfe der alten Datei, damit `build_portfolio_timeseries` und sechs
# Prüfsteine unverändert bleiben. Siehe `honorar_frame()`.
SP_INHABER = "Inhaber"
PFLICHT_STRATEGIEN = PFLICHT
PFLICHT_HONORAR = (SP_INHABER, SP_SATZ)

# Entfallen mit der Zusammenlegung, weil sie von keiner Codezeile gelesen
# wurden (nachgewiesen am 23.09.2026): „Duration" und „Familie" (eine
# Dublette von „Powerpoint Familie") sowie „Portfolioname" und „Honorarsatz
# Brutto". Die Brutto-Spalte war zusätzlich VERALTET: bei drei Zeilen war der
# Wert nicht das 1,19-fache des Standardsatzes. Philip hat am 23.09.2026
# bestätigt, dass „Honorarsatz Standard" richtig ist.
ENTFALLENE_SPALTEN = ("Duration", "Familie", "Portfolioname",
                      "Honorarsatz Brutto")


class StammdatenFehler(Exception):
    """Eine erwartete Spalte fehlt. Bewusst KEIN KeyError: Aufrufstellen, die
    einen KeyError abfangen, um über eine fehlende ZEILE hinwegzugehen,
    sollen diesen Fehler nicht mitverschlucken."""


def _norm(s):
    """Whitespace verdichten und kleinschreiben — damit „PowerPoint  Familie"
    und „powerpoint familie" denselben Treffer ergeben."""
    return " ".join(str(s).split()).strip().lower()


def finde_spalte(df, wunsch):
    """Den echten Spaltennamen tolerant suchen. Returns None, wenn es ihn
    nicht gibt — für Aufrufer, die eine fehlende Spalte selbst behandeln."""
    if df is None:
        return None
    ziel = _norm(wunsch)
    for col in getattr(df, "columns", []):
        if _norm(col) == ziel:
            return col
    return None


def spalte(df, wunsch, datei=None):
    """Wie ``finde_spalte``, wirft aber statt None zurückzugeben.

    Die Meldung nennt Datei und Spalte beim Namen, weil derjenige, der sie
    liest, die Excel vor sich hat und nicht den Quelltext.
    """
    treffer = finde_spalte(df, wunsch)
    if treffer is None:
        vorhanden = ", ".join(str(c) for c in getattr(df, "columns", []))
        raise StammdatenFehler(
            f"Spalte „{wunsch}“ fehlt in {datei or PFAD}. "
            f"Vorhanden sind: {vorhanden}")
    return treffer


def fehlende_spalten(df, pflicht=PFLICHT, datei=None):
    """Alle fehlenden Pflichtspalten auf einmal — für den Prüfstein, der
    nicht beim ersten Treffer aufhören soll."""
    return [w for w in pflicht if finde_spalte(df, w) is None]


def leer():
    """Leerer, aber strukturell gültiger Frame."""
    return pd.DataFrame(columns=list(ALLE_SPALTEN))


def lade(pfad=PFAD):
    """Die Stammdaten aller Strategien, eine Zeile je Strategie.

    Fehlt die Datei, kommt ein LEERER Frame statt einer Exception: Die
    Oberfläche meldet dann „Keine Portfolios zugeordnet", statt beim Start
    abzustürzen. Das ist Absicht — eine fehlende Datei ist ein Betriebs-
    problem, kein Programmfehler, und ein Absturz hilft dabei niemandem.

    Das ist das EINZIGE ``pd.read_excel`` auf eine Mapping-Datei im Projekt;
    ``tests/test_stammdaten.py`` Schritt 10 hält das per Syntaxbaum fest.
    """
    if not os.path.exists(pfad):
        return leer()
    df = pd.read_excel(pfad, sheet_name=BLATT)
    if df is None or getattr(df, "empty", True):
        return leer()
    return df


def honorar_frame(df):
    """Der Honorarsatz als eigener Frame, mit den Spaltenköpfen der alten
    Datei (``Inhaber`` / ``Honorarsatz Standard``).

    Warum die alten Namen: ``build_portfolio_timeseries`` und sechs
    Prüfsteine greifen namentlich darauf zu. Eine Projektion kostet nichts
    und hält die Zusammenlegung von diesen Stellen fern — es entsteht KEIN
    zweiter Lesepfad, der Frame stammt aus demselben ``lade()``.
    """
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame(columns=[SP_INHABER, SP_SATZ])
    return pd.DataFrame({
        SP_INHABER: df[spalte(df, SP_CSV_NAME)],
        SP_SATZ: df[spalte(df, SP_SATZ)],
    })


def honorarsatz(mapping, csv_name):
    """Nettosatz p.a. (dezimal) zu einem CSV-Portfolionamen.

    Returns: ``(satz, gefunden)``.

    ``gefunden=False`` heisst: Es gibt KEINE Zeile im Mapping. Der Satz ist
    dann ``0.0`` und damit **geraten** — die Aufrufstelle muss das melden,
    sonst laufen Bruttozahlen unter der Beschriftung "nach Kosten" (Audit
    14.08.2026). Ein GEFUNDENER Satz von 0,0 ist etwas anderes und liefert
    ``gefunden=True``.

    Die MwSt bleibt aussen vor: Der Performance-Pfad legt den Nettosatz in
    die Zeitreihe, der Broschüren-Pfad multipliziert selbst. Wer hier
    multiplizierte, hätte den Faktor zweimal drin.

    EINE Funktion für BEIDE Pfade (23.09.2026): Bis dahin stand die Suche
    zweimal im Repo — in ``shared.build_portfolio_timeseries`` sorgfältig
    mit Merkfeld, im Broschüren-Pfad als ``except Exception: fee_dec = 0.0``.
    Dieselbe fehlende Zeile wurde im Tool gemeldet und in der Kundenbroschüre
    verschluckt. Genau davor warnt die Regel "Loader oder Mathematik nie
    duplizieren".
    """
    if mapping is None or not csv_name:
        return 0.0, False
    if not {SP_INHABER, SP_SATZ} <= set(getattr(mapping, "columns", [])):
        return 0.0, False
    treffer = mapping.loc[mapping[SP_INHABER] == csv_name, SP_SATZ]
    if not len(treffer):
        return 0.0, False
    wert = pd.to_numeric(treffer.iloc[0], errors="coerce")
    if pd.isna(wert):
        return 0.0, False
    return float(wert), True
