"""
modules/farben.py — die festen Farben der Assetklassen, streamlit-frei
(NEU 18.08.2026).

Die Farben der Assetklassen sind im Corporate Design **fest vergeben**: Aktien
dunkelblau, Renten hellblau, Edelmetalle gold. Sie hängen an der KATEGORIE und
nicht an ihrer Größe — auf der Webseite der Bank, in der Broschüre und ab
heute auch im Tool.

Dieses Modul ist der eine Ort dafür. Es zieht weder Streamlit noch lxml
herein, damit **beide** Seiten es erreichen: der PowerPoint-Export
(`chart_dynamik`, `pptx_slides`) und die Oberfläche (`portfolioanalyse`,
`strategievergleich`).

────────────────────────────────────────────────────────────────────────────
DIE GESCHICHTE DAZU, WEIL SIE SICH WIEDERHOLT HAT
────────────────────────────────────────────────────────────────────────────

**10.07.2026, Broschüre.** Die `<c:dPt>`-Farben einer PowerPoint-Vorlage
hängen am INDEX, nicht am Namen. Die cVV-Vorlage führt EDELMETALLE an
Position 0; nach dem Befüllen stand dort AKTIEN und erbte Gold. Gelöst mit
`chart_dynamik.ring_segmentfarben`, die die Farben datenbasiert je
Assetklasse setzt.

**18.08.2026, Tool.** Derselbe Fehler an anderer Stelle, gemeldet von Philip:
Im Ring „Allokation nach Gattung" bekam die GRÖSSTE Gattung immer Fuggerblau,
weil `build_ring_chart` nach Gewicht sortiert und die Palette dann der Reihe
nach vergibt. Die Lösung von damals war nur nicht erreichbar — sie lag in
einem Modul des Export-Pfads.

Die Lehre steht in `PROJEKT_DOKUMENTATION.md` als Transferwissen: Eine
Festlegung, die an zwei Stellen gilt, braucht einen Ort, den beide erreichen.
Sonst wird sie an der einen gepflegt und an der anderen neu erfunden.

────────────────────────────────────────────────────────────────────────────
ZWEI SCHREIBWEISEN, UND DAS IST KEIN VERSEHEN
────────────────────────────────────────────────────────────────────────────

    ASSET_FARBEN   "14355C"     ohne Doppelkreuz  — so will es OOXML
                                (<a:srgbClr val="14355C"/>)
    gattung_farbe  "#14355C"    mit Doppelkreuz   — so will es Plotly

Ein `#` im XML fällt nicht auf: PowerPoint zeigt dann irgendetwas, und kein
Test sieht es, weil die Datei gültig bleibt. Deshalb liefert die Tabelle die
rohe Form, und wer für die Oberfläche etwas braucht, geht über
`gattung_farbe`.
"""

# ── Die Palette ────────────────────────────────────────────────────────────
# Sie stammt aus den VORLAGEN selbst und ist nicht erfunden. Am 18.08.2026
# über 22 Ring-Charts in sechs Vorlagen positionsunabhängig nachgemessen:
# In der ESG-Vorlage steht EDELMETALLE an Position 0, in der FFPB-Vorlage
# AKTIEN — und jede Kategorie behält trotzdem ihre Farbe.
#
# Werte OHNE Doppelkreuz (siehe Modul-Docstring).
ASSET_FARBEN = {
    "AKTIEN":       "14355C",   # dunkelblau
    "RENTEN":       "66A4CE",   # hellblau
    "EDELMETALLE":  "BB9256",   # gold
    "LIQUIDITÄT":   "9FD0EF",   # noch helleres blau
    "SONSTIGE":     "808080",   # grau
}

# ANMERKUNG ZUR LIQUIDITÄT: Die Vorlagen ESG, ETF, cVV und comdirect führen
# 9FD0EF, die Vorlagen FFPB und Thema dagegen D1E9F8. Die Tabelle
# normalisiert seit dem 10.07.2026 auf 9FD0EF; das ist eine bestehende
# Festlegung und wird hier übernommen, nicht neu entschieden. Der Prüfstein
# kennt die Abweichung namentlich, damit sie nicht als Fehler erscheint.

GROUP_AKTIEN = "AKTIEN"
GROUP_RENTEN = "RENTEN"
GROUP_EDELMETALLE = "EDELMETALLE"
GROUP_LIQUIDITAET = "LIQUIDITÄT"
GROUP_SONSTIGE = "SONSTIGE"

# Die vier echten Klassen — "SONSTIGE" ist der Auffangkorb und zählt nicht
# dazu. `chart_dynamik` entscheidet damit, ob ein Ring ein Assetklassen-Ring
# ist.
KERNKLASSEN = {GROUP_AKTIEN, GROUP_RENTEN, GROUP_EDELMETALLE,
               GROUP_LIQUIDITAET}


def klassifiziere_gattung(gattung) -> str:
    """Ordnet eine Gattung einer der fünf Hauptgruppen zu.

    Heuristik über Teilzeichenketten:
        "aktie" / "equity"                  -> AKTIEN
        "rente" / "anleihe" / "bond"        -> RENTEN
        "edelmetall" / "gold" / "silber"    -> EDELMETALLE
        "liquid" / "cash"                   -> LIQUIDITÄT
        sonst                               -> SONSTIGE

    UMGEZOGEN aus `pptx_slides.classify_gattung` (18.08.2026), unverändert.
    Dort heißt sie weiterhin so und wird von hier durchgereicht.

    ACHTUNG — DIESE FUNKTION TAUGT NICHT ALS FILTER FÜR ANDERE DIMENSIONEN.
    Die Teilzeichenketten treffen auch Werte, die gar keine Gattungen sind.
    Am 18.08.2026 an den echten Daten gemessen:

        Segment "Rentenfonds"              -> RENTEN
        Segment "Immobilien-Aktien/Fonds"  -> AKTIEN

    Wer daraus eine Regel „färbe alles, was wie eine Assetklasse aussieht"
    baut, färbt Segment-Ringe in Assetklassen-Farben. Die Entscheidung, ob
    feste Farben gelten, gehört deshalb an die DIMENSION und nicht an die
    einzelne Kategorie — im Export über `chart_dynamik._ist_assetklassen_ring`
    (alle Kategorien müssen Assetklassen sein), in der Oberfläche über den
    bekannten Spaltennamen.
    """
    if gattung is None:
        return GROUP_SONSTIGE
    try:
        # pandas ist hier bewusst NICHT importiert — das Modul soll ohne
        # Fremdpakete auskommen. NaN erkennt man auch so: es ist der einzige
        # Wert, der sich selbst ungleich ist.
        if gattung != gattung:
            return GROUP_SONSTIGE
    except (TypeError, ValueError):
        pass
    g = str(gattung).lower()
    if "aktie" in g or "equity" in g:
        return GROUP_AKTIEN
    if "rente" in g or "anleihe" in g or "bond" in g:
        return GROUP_RENTEN
    if "edelmetall" in g or "gold" in g or "silber" in g:
        return GROUP_EDELMETALLE
    if "liquid" in g or "cash" in g:
        return GROUP_LIQUIDITAET
    return GROUP_SONSTIGE


def gattung_farbe(wert) -> str:
    """Feste Farbe einer Assetklasse als "#RRGGBB" — für Plotly.

    Liefert IMMER eine Farbe: Was sich keiner Klasse zuordnen lässt, wird
    grau (SONSTIGE). Ein Fehlwert bekommt damit dieselbe Farbe wie eine
    ausdrücklich als „Sonstige" ausgewiesene Position — das ist hier richtig,
    weil beide dasselbe bedeuten: keine der vier Klassen.

    NUR AUF DER GATTUNGS-DIMENSION AUFRUFEN, siehe Warnung bei
    `klassifiziere_gattung`.
    """
    return "#" + ASSET_FARBEN[klassifiziere_gattung(wert)]
