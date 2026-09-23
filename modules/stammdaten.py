# modules/stammdaten.py
"""Spaltennamen der Mapping-Dateien — EINE Stelle, an der sie stehen.

Bis zum 23.09.2026 griffen drei Module positionell auf `Mapping_Namen.xlsx`
zu: `columns[0]` (Anzeigename), `columns[1]` (CSV-Portfolioname),
`columns[3]` (Benchmark). Das funktioniert genau so lange, wie niemand eine
Spalte einfügt, löscht oder verschiebt. Danach liest der Code lautlos die
falsche Spalte weiter — keine Exception, keine Meldung, nur falsche Texte in
der Kundenbroschüre. Aufgefallen ist die Falle bei der Frage, ob man die
tote Spalte „Duration" entfernen kann: Sie steht an Position 2, und ihr
Wegfall hätte die Familien-Spalte zur Benchmark gemacht.

Deshalb stehen die Spaltennamen ab jetzt hier, und der Zugriff läuft über
`spalte()`. Fehlt eine Spalte, WIRFT das — eine Stelle, die den Dateinamen
und den Spaltennamen ausspricht, ist besser als ein stiller Fehlgriff.

WARUM DIESES MODUL STREAMLIT-FREI IST:
    Dasselbe Argument wie bei ``modules/anlagekriterien.py``: der
    Broschüren-Export (``pptx_export.py``) soll ohne Streamlit aus einem
    Batch-Skript laufen können. Der ``@st.cache_data``-Deckel liegt allein
    in ``shared.py``; hier steht nur das Wissen, wie die Spalten heißen.

ZUM LESEN DER DATEI selbst sagt dieses Modul (Stand Etappe 1) noch nichts —
das Laden bleibt vorerst in ``shared.py`` bzw. ``anlagekriterien.py``.
"""

DATEI_STRATEGIEN = "Mapping_Namen.xlsx"
DATEI_HONORAR = "Mapping_Honorarsatz.xlsx"

# ── Mapping_Namen.xlsx ──────────────────────────────────────────────────
# ACHTUNG bei Spalte B: Sie heißt „Honorarsatz Mapping", enthält aber den
# CSV-PORTFOLIONAMEN ("Muster konservativ cVV"). Der steht wortgleich in der
# CSV-Spalte „Portfolio Name", ist der Schlüssel zu Mapping_Honorarsatz
# (Spalte „Inhaber") und der Schlüssel von HISTORIE_AB. Er kommt aus dem
# Bestandssystem und ist NICHT frei wählbar. Der Spaltenkopf ist irreführend,
# bleibt aber unverändert — er steht in einer Datei, die Philip pflegt.
SP_ANZEIGE = "Strategie auswählen"      # Anzeigename, Dropdown + Code-Konstanten
SP_CSV_NAME = "Honorarsatz Mapping"     # CSV-Portfolioname (siehe oben)
SP_DURATION = "Duration"                # wird von KEINER Codezeile gelesen
SP_BENCHMARK = "Benchmark"              # Freitext für die ***-Fußnote (F8)
SP_FAMILIE = "Powerpoint Familie"       # steuert Vorlage und Config

# ── Mapping_Honorarsatz.xlsx ────────────────────────────────────────────
SP_INHABER = "Inhaber"                  # = SP_CSV_NAME der anderen Datei
SP_SATZ = "Honorarsatz Standard"        # Nettosatz p.a., dezimal

# Spalten, ohne die der jeweilige Lesepfad nicht arbeiten kann.
PFLICHT_STRATEGIEN = (SP_ANZEIGE, SP_CSV_NAME, SP_BENCHMARK, SP_FAMILIE)
PFLICHT_HONORAR = (SP_INHABER, SP_SATZ)

# Von keiner Codezeile gelesen (nachgewiesen am 23.09.2026). Stehen hier
# NICHT als Fundgrube, sondern damit der Prüfstein sie benennen kann, wenn
# jemand später doch darauf zu joinen versucht.
TOTE_SPALTEN = {
    DATEI_STRATEGIEN: (SP_DURATION,),
    # „Honorarsatz Brutto“ ist zusätzlich VERALTET: bei drei Zeilen ist der
    # Wert nicht das 1,19-fache des Standardsatzes, sondern rechnet sich auf
    # einen anderen Nettosatz zurück. Philip hat am 23.09.2026 bestätigt:
    # „Honorarsatz Standard“ ist richtig. Die Spalte fällt mit den anderen.
    DATEI_HONORAR: ("Portfolioname", "Honorarsatz Brutto"),
}


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


def spalte(df, wunsch, datei=DATEI_STRATEGIEN):
    """Wie ``finde_spalte``, wirft aber statt None zurückzugeben.

    Die Meldung nennt Datei und Spalte beim Namen, weil derjenige, der sie
    liest, die Excel vor sich hat und nicht den Quelltext.
    """
    treffer = finde_spalte(df, wunsch)
    if treffer is None:
        vorhanden = ", ".join(str(c) for c in getattr(df, "columns", []))
        raise StammdatenFehler(
            f"Spalte „{wunsch}“ fehlt in {datei}. Vorhanden sind: {vorhanden}")
    return treffer


def fehlende_spalten(df, pflicht, datei=DATEI_STRATEGIEN):
    """Alle fehlenden Pflichtspalten auf einmal — für den Prüfstein, der
    nicht beim ersten Treffer aufhören soll."""
    return [w for w in pflicht if finde_spalte(df, w) is None]

