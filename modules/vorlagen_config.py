"""
modules/vorlagen_config.py — Bauplan der PowerPoint-Broschueren.

HIER wird konfiguriert, welche Vorlage eine Strategie bekommt und wie ihre
Broschuere aufgebaut ist. Wer eine Folie einfuegt, eine Familie ergaenzt
oder einen Dateinamen aendert, aendert NUR diese Datei — der uebrige Code
bleibt unberuehrt.

Herausgeloest aus portfolioanalyse.py am 07.08.2026 (vorher standen die
rund 520 Zeilen Konfiguration mitten in der Streamlit-Ansicht). Inhalt und
Reihenfolge sind unveraendert uebernommen; tests/test_folien_config.py
belegt, dass dabei dieselben template_config-Strukturen entstehen.

Die Datei hat BEWUSST keine Importe — kein Streamlit, kein pandas, kein
python-pptx. Sie laesst sich damit aus jedem Kontext lesen, auch aus
Skripten ohne Streamlit-Umgebung.

Was hier hingehoert:
  - _folien_config()          Folienliste -> template_config
  - die Familien-Configs      _THEMA_CONFIG, _CVV_CONFIG, ...
  - VORLAGEN_FAMILIEN         Familie -> (Vorlagendatei, Config)
  - FAMILIE_ALLE_STRATEGIEN   Familien, deren Broschuere immer alle enthaelt
  - EXPORT_NAME_*             Dateinamen der fertigen Broschuere

Was hier NICHT hingehoert:
  - Zugriff auf das Mapping (-> _familie_fuer_strategie in portfolioanalyse)
  - Pfadaufloesung der Vorlagen (-> _vorlage_fuer_familie ebenda)
  - alles mit Streamlit-Bezug
"""

# ─────────────────────────────────────────────────────────────────────────────
# Vorlagen-Familien (NEU 06.07.2026): Steuert, welche PowerPoint-Vorlage +
# Folienstruktur eine Strategie bekommt. Die Zuordnung kommt aus der
# Mapping-Spalte "Powerpoint Familie" (leer = Standard-Broschüre).
#
# Variante A (familiengesteuert): Der Berater wählt NUR die Strategie; die
# Familie im Mapping bestimmt automatisch die Vorlage — keine zusätzliche
# Auswahl, keine Fehlbedienung möglich.
#
# WICHTIG für Rückwärtskompatibilität: Ist die Familie leer/unbekannt ODER
# fehlt die Vorlagen-Datei, wird template_path/template_config = None
# durchgereicht → exakt der bisherige Standard-Export (Vorlage_FFPB.pptx).
# ─────────────────────────────────────────────────────────────────────────────

SPALTE_PP_FAMILIE = "Powerpoint Familie"


def _folien_config(folien, rollen_optionen=None, entfernen=None, modus="fest"):
    """Baut ein ``template_config`` aus einer GEORDNETEN Folienliste.

    Idee: Man beschreibt die Broschüre Folie für Folie in Reihenfolge — die
    Folienposition ergibt sich automatisch aus dem Listenindex (Position =
    Index + 1). Kommt eine statische Folie dazu, fügt man EINEN Eintrag ein;
    alle folgenden Positionen verschieben sich von allein. Kein Umnummerieren.

    Jeder Eintrag ist ein Tupel (das Label am Ende ist REINE Dokumentation und
    fließt NICHT in die Logik ein — ein Tippfehler im Label kann die
    Generierung also nie brechen):

        ("S", "Label")            – statische Folie (Generator fasst sie nie an)
        ("<rolle>", n, "Label")   – dynamische Folie der Strategie n (0-basiert)
        ("<rolle>", "*", "Label") – Einmal-Folie (läuft einmal für alle Strategien)

    Rollen wie im Export-Dispatch: anlagevorschlag, wertentwicklung, performance,
    zusammenstellung, rollierend, einzeltitel_themen (dynamisch) bzw.
    uebersicht, vergleich (einmal).

    ── DIE ZWEI MODI (WICHTIG) ──────────────────────────────────────────────

    ``modus="fest"`` (Default, Infoboard-Vorlagen: CVV/ESG/ETF/comdirect)
        Die Vorlage enthält die Folien ALLER Strategien bereits vorgebaut,
        oft mit strategiespezifischen Inhalten (z.B. der starre
        Anlagekriterien-Kasten der CVV-Vorlage). Es wird NICHTS dupliziert,
        nur an festen Positionen befüllt → ``feste_bloecke``.
        Die Folienliste nennt hier jede Strategie einzeln (0, 1, 2, …).

    ``modus="dupliziert"`` (Themen-Vorlage)
        Die Vorlage enthält den dynamischen Block genau EINMAL; der Export
        vervielfältigt ihn für so viele Strategien, wie übergeben werden
        → ``block_positionen`` + ``block_reihenfolge``.
        Die Folienliste nennt deshalb nur Strategie 0 — das ist die Vorlage
        des Blocks, nicht "nur die erste Strategie".

    Den Modus zu verwechseln ist die gefährliche Variante: Eine Vorlage mit
    nur einem Block auf "fest" zu stellen liefert für jede weitere Strategie
    stillschweigend KEINE Folien (der Export protokolliert es lediglich in
    LAST_BUILD_ERRORS) — der Berater bekäme eine unvollständige Broschüre,
    ohne dass etwas abstürzt.

    Erzeugt EXAKT die Struktur, die pptx_export.generate_portfolioanalyse_pptx
    schon versteht — der Export bleibt unangetastet.

    Raises:
        ValueError: bei unbekanntem Modus, oder wenn eine dupliziert-Config
            mehr als eine Strategie nennt bzw. ihr Block nicht zusammenhängt.
    """
    if modus not in ("fest", "dupliziert"):
        raise ValueError(f"_folien_config: unbekannter modus {modus!r} "
                         f"(erlaubt: 'fest', 'dupliziert')")

    feste = {}    # strategie-index (int) -> {rolle: 1-indexierte Position}
    einmal = {}   # rolle -> 1-indexierte Position
    for i, eintrag in enumerate(folien):
        pos = i + 1
        rolle = eintrag[0]
        if str(rolle).upper() == "S":          # statische Folie -> ueberspringen
            continue
        strat = eintrag[1]
        if strat == "*":
            einmal[rolle] = pos
        else:
            feste.setdefault(int(strat), {})[rolle] = pos

    cfg = {
        "erwartete_folien": len(folien),
        "entfernen": list(entfernen or []),
        "rollen_optionen": dict(rollen_optionen or {}),
    }

    if modus == "dupliziert":
        # Nur Strategie 0 darf vorkommen — sie beschreibt den Block, den der
        # Export dann je Strategie dupliziert.
        fremde = sorted(k for k in feste if k != 0)
        if fremde:
            raise ValueError(
                f"_folien_config(modus='dupliziert'): die Folienliste nennt "
                f"die Strategie-Indizes {fremde}. Im Dupliziermodus beschreibt "
                f"Strategie 0 den Block, der vervielfältigt wird — weitere "
                f"Indizes gehören nicht in die Liste.")
        block = feste.get(0, {})
        if not block:
            raise ValueError("_folien_config(modus='dupliziert'): kein "
                             "dynamischer Block in der Folienliste gefunden.")
        # Reihenfolge = Reihenfolge in der Liste; Positionen müssen lückenlos
        # aufeinanderfolgen, weil der Export den Block als Ganzes kopiert.
        reihenfolge = sorted(block, key=lambda r: block[r])
        positionen = [block[r] for r in reihenfolge]
        if positionen != list(range(positionen[0], positionen[0] + len(positionen))):
            raise ValueError(
                f"_folien_config(modus='dupliziert'): der dynamische Block "
                f"muss zusammenhängend sein, gefunden wurden die Positionen "
                f"{positionen}. Statische Folien dürfen nicht dazwischen liegen.")
        cfg["block_reihenfolge"] = reihenfolge
        cfg["block_positionen"] = dict(block)
    else:
        if feste:
            # Liste in Strategie-Reihenfolge 0,1,2,… (fehlende Indizes -> leerer Block)
            cfg["feste_bloecke"] = [feste.get(k, {}) for k in range(max(feste) + 1)]
        else:
            cfg["feste_bloecke"] = []

    # einmal_folien NUR anlegen, wenn es Einmal-Folien gibt.
    if einmal:
        cfg["einmal_folien"] = einmal
    return cfg

# Struktur-Block der THEMEN-Broschüren (Pro / Pro Dividende / Offensiv teilen
# sich diese eine Vorlage + Struktur). Verifiziert an der echten Vorlage:
# 21 Folien, dynamischer Block F10-F13.
#
# ALS EINZIGE FAMILIE IM DUPLIZIERMODUS (siehe _folien_config): Die Vorlage
# enthält den Block genau EINMAL, der Export vervielfältigt ihn je Strategie.
# Deshalb steht unten nur Strategie 0 — sie beschreibt den Block, nicht "die
# erste Strategie". Das ist nötig, weil "Thema" NICHT in
# FAMILIE_ALLE_STRATEGIEN steht: Der Berater wählt hier eine Strategie und
# kann ein Vergleichsportfolio zuschalten, die Folienzahl steht also erst zur
# Laufzeit fest. Auf "fest" umgestellt bekäme das Vergleichsportfolio
# stillschweigend keine Folien.
#
# Umgestellt am 07.08.2026 von der handgeschriebenen Dict-Form auf
# _folien_config — erzeugt beweisbar dasselbe template_config (siehe
# tests/test_folien_config.py), aber in derselben lesbaren Folienliste wie
# alle anderen Familien.
_THEMA_CONFIG = _folien_config(
    modus="dupliziert",
    folien=[
        ("S", "UNABHÄNGIG. WERTEORIENTIERT. PERSÖNLICH."),
        ("S", "Unsere Strategie PRO"),
        ("S", "Unsere Strategie PRO (Fortsetzung)"),
        ("S", "Aktien – die guten Jahre überwiegen"),
        ("S", "Die Fallstricke des typischen Investors"),
        ("S", "Durchhalten zahlt sich aus"),
        ("S", "Gute Jahre überwiegen"),
        ("S", "Krise als Chance"),
        ("S", "Basis unserer Investmententscheidungen"),
        ("einzeltitel_themen", 0, "Einzeltitel (Tabelle + Assetklassen-Ring)"),
        ("zusammenstellung", 0, "Aktuelle Portfoliozusammenstellung (Regionen + Branchen)"),
        ("wertentwicklung", 0, "Anlagestrategie … | Wertentwicklung"),
        ("rollierend", 0, "Wertentwicklung der Strategie … (rollierend)"),
        ("S", "Unser Honorar"),
        ("S", "Unser Honorar (Tabelle)"),
        ("S", "Unsere Bank in Zahlen"),
        ("S", "Unsere Standorte"),
        ("S", "Unsere Standorte (Fortsetzung)"),
        ("S", "Risikohinweise"),
        ("S", "Rechtliche Hinweise und Impressum"),
        ("S", "www.fuggerbank.de"),
    ],
)

# Struktur der CVV-Broschüre ("cVV Infoboard", NEU 09.07.2026).
#
# BESONDERHEIT gegenüber allen anderen Familien: Die Vorlage enthält die
# Folien ALLER FÜNF Strategien bereits fertig vorgebaut — jede mit ihrem
# eigenen, STARREN Anlagekriterien-Kasten (Folien 7/9/11/13/15) und der
# zugehörigen Wertentwicklungs-Folie (8/10/12/14/16). Der Block darf deshalb
# NICHT dupliziert werden (sonst bekämen alle Strategien den Kasten der
# ersten). Stattdessen: "feste_bloecke" → pptx_export befüllt an festen
# Vorlagen-Positionen, ohne _normalisiere_vorlage/_vervielfaeltige_block.
#
# Verifiziert an der echten Vorlage (37 Folien):
#   F7/9/11/13/15 : Titel + Anlagekriterien-Kasten + C_Kennzahlen (Ring)
#                   + T_Kennzahlen (11 Spalten, wie Standard-Anlagevorschlag)
#   F8/10/12/14/16: Diagramm rechts/links + Kennzahlen-Tabelle
#                   (identisch zur Rolle "wertentwicklung")
#   F17 (8x13) und F19 (Linien-Chart, 5 Serien) werden NOCH NICHT befüllt
#   (Stufe 2/3) und zeigen bis dahin die Vorlagen-Daten.
_CVV_STRATEGIEN = [
    "cVV konservativ",
    "cVV defensiv",
    "cVV defensiv plus",
    "cVV ausgewogen",
    "cVV dynamic",
]
"""Feste Reihenfolge der CVV-Strategien — MUSS zur Foliennummerierung der
Vorlage passen (Konservativ=F7, Defensiv=F9, Defensiv Plus=F11,
Ausgewogen=F13, Dynamic=F15). Namen wie in der Mapping-Spalte
'Strategie auswählen'."""

_CVV_CONFIG = _folien_config(
    # Broschüre Folie für Folie (Position = Listenindex+1). Neue statische
    # Folie? Einfach EINEN ("S", "…")-Eintrag einfügen — Positionen
    # verschieben sich automatisch. Labels = echte Vorlagentitel (nur Doku).
    folien=[
        ("S", "Titelseite – Unabhängig. Werteorientiert. Persönlich."),
        ("S", "Unsere Vermögensverwaltung"),
        ("S", "Vermögenserhalt und langfristiges Wachstum"),
        ("S", "Aufteilung zur Risikobegrenzung"),
        ("S", "Strategie-Einführung (Risikoklassen)"),
        ("S", "Unsere fünf klassischen Strategien (Übersicht)"),
        ("anlagevorschlag", 0, "Konservativ – Struktur (Ring + Positionen)"),
        ("wertentwicklung", 0, "Konservativ – Performance"),
        ("anlagevorschlag", 1, "Defensiv – Struktur"),
        ("wertentwicklung", 1, "Defensiv – Performance"),
        ("anlagevorschlag", 2, "Defensiv Plus – Struktur"),
        ("wertentwicklung", 2, "Defensiv Plus – Performance"),
        ("anlagevorschlag", 3, "Ausgewogen – Struktur"),
        ("wertentwicklung", 3, "Ausgewogen – Performance"),
        ("anlagevorschlag", 4, "Dynamic – Struktur"),
        ("wertentwicklung", 4, "Dynamic – Performance"),
        ("uebersicht", "*", "Wertentwicklung-Vergleich (Tabelle, alle 5)"),
        ("S", "Größte Monatsverluste (Übersicht)"),
        ("vergleich", "*", "Klassische VV Strategien im Vergleich (Linien-Chart)"),
        ("S", "Exklusive Erweiterung mit individuellen Kriterien"),
        ("S", "all-in-fee-Honorar"),
        ("S", "Honorar (inkl. USt.)"),
        ("S", "Steuerlicher Hinweis zum Honorar"),
        ("S", "Langfristiger Vermögenserhalt"),
        ("S", "Die optimale Vermögensverwaltungsstrategie"),
        ("S", "Zinsänderungsrisiko"),
        ("S", "Kombination verschiedener Anlageklassen"),
        ("S", "Regelmäßige Berichte"),
        ("S", "Wesentliche Finanzkennzahlen (AuM-Wachstum)"),
        ("S", "Ansprechpartner Private Banking"),
        ("S", "Standort Friedrichsplatz"),
        ("S", "Standort Theodor-Heuss-Str."),
        ("S", "Individuell. Unabhängig. Vertrauensvoll."),
        ("S", "Anschreiben"),
        ("S", "Kluge Investitionen (ländlicher Grundbesitz)"),
        ("S", "Stand"),
        ("S", "Rückseite / Stand"),
    ],
    rollen_optionen={
        "anlagevorschlag": {"titel_text": "", "max_bottom_inch": 6.20,
                            "original_row_h_inch": 0.192},
    },
)


# Struktur der ESG-Broschüre ("ESG Infoboard", NEU 10.07.2026).
#
# Gleicher Bauplan wie CVV (feste Blöcke, Kästen unterscheiden sich je
# Strategie), aber VIER Strategien und OHNE Vergleichs-Linienchart.
# Verifiziert an der echten Vorlage (39 Folien):
#   F16/18/20/22 : Titel + Anlagekriterien-Kasten + C_Kennzahlen (Ring)
#                  + T_Kennzahlen (11 Spalten)
#   F17/19/21/23 : Rolle "wertentwicklung"
#   F24          : Übersichtstabelle 8x11, Strategien in den Spalten 4/6/8/10
_ESG_STRATEGIEN = [
    "ESG defensiv",
    "ESG defensiv+",      # Folientitel: "ESG Defensiv Plus"
    "ESG ausgewogen",
    "ESG offensiv",
]
"""Feste Reihenfolge — MUSS zur Foliennummerierung passen (Defensiv=F16,
Defensiv Plus=F18, Ausgewogen=F20, Offensiv=F22). Namen wie in der
Mapping-Spalte 'Strategie auswählen'."""

_ESG_CONFIG = _folien_config(
    # Broschüre Folie für Folie (Position = Listenindex+1). Neue statische
    # Folie? Einfach EINEN ("S", "…")-Eintrag einfügen — Positionen
    # verschieben sich automatisch. Labels = echte Vorlagentitel (nur Doku).
    folien=[
        ("S", "Titelseite"),
        ("S", "ESG Basisinformationen"),
        ("S", "ESG Kriterien"),
        ("S", "ESG Basis-Informationen"),
        ("S", "Governance"),
        ("S", "MSCI Abdeckung"),
        ("S", "ESG-Vermögensverwaltungen"),
        ("S", "Normbasierte Ausschlüsse"),
        ("S", "17 Ziele (Bildquelle)"),
        ("S", "Nachhaltigkeits- und Investmentkonzept"),
        ("S", "Nachhaltigkeitsprozess / Offenlegungsverordnung"),
        ("S", "Leitfaden (Bildquelle)"),
        ("S", "Umwelt"),
        ("S", "Anlagerichtlinien"),
        ("S", "Unsere ESG-Strategien"),
        ("anlagevorschlag", 0, "ESG Defensiv – Struktur"),
        ("wertentwicklung", 0, "ESG Defensiv – Performance"),
        ("anlagevorschlag", 1, "ESG Defensiv Plus – Struktur"),
        ("wertentwicklung", 1, "ESG Defensiv Plus – Performance"),
        ("anlagevorschlag", 2, "ESG Ausgewogen – Struktur"),
        ("wertentwicklung", 2, "ESG Ausgewogen – Performance"),
        ("anlagevorschlag", 3, "ESG Offensiv – Struktur"),
        ("wertentwicklung", 3, "ESG Offensiv – Performance"),
        ("uebersicht", "*", "Wertentwicklung-Vergleich (Tabelle, alle 4)"),
        ("S", "Standorte (Titel)"),
        ("S", "Unsere Standorte"),
        ("S", "Unsere Standorte"),
        ("S", "Anlage"),
        ("S", "Kombination verschiedener Anlageklassen"),
        ("S", "Konservativer Baustein"),
        ("S", "Vermögensverwaltungsbericht"),
        ("S", "Steuerservice"),
        ("S", "Honorarübersicht"),
        ("S", "Risikohinweise"),
        ("S", "Rechtliche Hinweise und Impressum"),
        ("S", "Unser Reporting"),
        ("S", "Rechtliche Hinweise und Impressum"),
        ("S", "Meinungsäußerungen (Disclaimer)"),
        ("S", "Vielen Dank"),
    ],
    rollen_optionen={
        "anlagevorschlag": {"titel_text": "", "max_bottom_inch": 6.20,
                            "original_row_h_inch": 0.192},
        "uebersicht": {"spalten": [4, 6, 8, 10]},
    },
)


# Struktur der ETF-Broschüre ("ETF Infoboard", NEU 20.07.2026).
#
# Gleicher Bauplan wie ESG (feste Blöcke, kein Vergleichs-Linienchart), aber
# ZWEI Strategien. BESONDERHEIT: Die ETF-T_Kennzahlen-Tabelle hat nur 7 Spalten
# (WERTPAPIER/WKN/Anteil/Marktrisikowert) OHNE KUPON/FÄLLIGKEIT — ETFs sind
# keine Renten. Deshalb bekommt die Rolle "anlagevorschlag" ein eigenes
# spalten_map (Schema siehe pptx_slides.DEFAULT_SPALTEN_MAP); die restliche
# Fill-Logik ist identisch.
# Verifiziert an der echten Vorlage (35 Folien):
#   F16/18 : Titel + Anlagekriterien-Kasten + C_Kennzahlen (Ring)
#            + T_Kennzahlen (7 Spalten, mit Marktrisikowert)
#   F17/19 : Rolle "wertentwicklung" (Diagramm links/rechts + Kennzahlen)
#   F20    : Übersichtstabelle 8x8, Strategien in den Spalten 4/6
_ETF_STRATEGIEN = [
    "ETF_ausgewogen",
    "ETF_Wachstum",
]
"""Feste Reihenfolge — MUSS zur Foliennummerierung passen (Ausgewogen=F16,
Wachstum=F18). Namen wie in der Mapping-Spalte 'Strategie auswählen'."""

_ETF_CONFIG = _folien_config(
    # Broschüre Folie für Folie (Position = Listenindex+1). Neue statische
    # Folie? Einfach EINEN ("S", "…")-Eintrag einfügen — Positionen
    # verschieben sich automatisch. Labels = echte Vorlagentitel (nur Doku).
    folien=[
        ("S", "Titelseite"),
        ("S", "ESG Basisinformationen"),
        ("S", "ESG Basis-Informationen"),
        ("S", "ESG Kriterien"),
        ("S", "Governance"),
        ("S", "MSCI Abdeckung"),
        ("S", "ESG-Vermögensverwaltungen"),
        ("S", "Normbasierte Ausschlüsse"),
        ("S", "Investmentprozess und Risiken"),
        ("S", "Nachhaltigkeits- und Investmentkonzept"),
        ("S", "Nachhaltigkeitsprozess / Offenlegungsverordnung"),
        ("S", "Leitfaden (Bildquelle)"),
        ("S", "Umwelt"),
        ("S", "Anlagerichtlinien"),
        ("S", "Unsere ESG-ETF Strategien"),
        ("anlagevorschlag", 0, "ESG-ETF Ausgewogen – Struktur"),
        ("wertentwicklung", 0, "ESG-ETF Ausgewogen – Performance"),
        ("anlagevorschlag", 1, "ESG-ETF Wachstum – Struktur"),
        ("wertentwicklung", 1, "ESG-ETF Wachstum – Performance"),
        ("uebersicht", "*", "Wertentwicklung-Vergleich (Tabelle, beide)"),
        ("S", "Standorte (Titel)"),
        ("S", "Unsere Standorte"),
        ("S", "Unsere Standorte"),
        ("S", "Anlage"),
        ("S", "Kombination verschiedener Anlageklassen"),
        ("S", "Konservativer Baustein"),
        ("S", "Vermögensverwaltungsbericht"),
        ("S", "Steuerservice"),
        ("S", "Honorarübersicht"),
        ("S", "Honorarbelastung"),
        ("S", "Unser Reporting"),
        ("S", "Rechtliche Hinweise und Impressum"),
        ("S", "Risikohinweise"),
        ("S", "Rechtliche Hinweise und Impressum"),
        ("S", "Vielen Dank"),
    ],
    rollen_optionen={
        "anlagevorschlag": {
            "titel_text": "", "max_bottom_inch": 6.20,
            "original_row_h_inch": 0.34,
            "spalten_map": {
                "wertpapier": 0, "kupon": None, "faelligkeit": None,
                "wkn": 2, "anteil": 4, "rating": 6, "spacers": [1, 3, 5],
            },
        },
        "uebersicht": {"spalten": [4, 6]},
    },
)


# Struktur der comdirect-Broschüre ("Klassische Portfolioverwaltung", NEU 21.07.2026).
#
# Gleicher Bauplan wie ESG/CVV (feste Blöcke), aber DREI Strategien und
# BESONDERS EINFACH: T_Kennzahlen ist 11-spaltig (Standard-Layout → KEIN
# spalten_map nötig) und es gibt KEINE dynamische Vergleichsfolie (F5 =
# statische Strategie-Beschreibung, F21 = Firmen-AuM-Wachstum → beide statisch,
# also KEIN einmal_folien). Damit ist es eine reine Config-Ergänzung.
# Verifiziert an der echten Vorlage (27 Folien):
#   F6/8/10 : Titel "Anlagestrategie Portfolioverwaltung 30/70/100"
#             + Anlagekriterien-Kasten + C_Kennzahlen (Ring)
#             + T_Kennzahlen (11 Spalten, mit Marktrisikowert)
#   F7/9/11 : Rolle "wertentwicklung" (Diagramm links/rechts + Kennzahlen)
_COMDIRECT_STRATEGIEN = [
    "Comdirect_30",
    "Comdirect_70",
    "Comdirect_100",
]
"""Feste Reihenfolge — MUSS zur Foliennummerierung passen (30=F6, 70=F8,
100=F10). Namen wie in der Mapping-Spalte 'Strategie auswählen'."""

_COMDIRECT_CONFIG = _folien_config(
    # Broschüre Folie für Folie (Position = Listenindex+1). Neue statische
    # Folie? Einfach EINEN ("S", "…")-Eintrag an der richtigen Stelle einfügen —
    # alle folgenden Positionen verschieben sich von allein. Labels sind reine
    # Doku (Titel der echten Vorlagenfolien), ändern die Logik nicht.
    folien=[
        ("S", "Titelseite – Unabhängig. Werteorientiert. Persönlich."),
        ("S", "Unsere Portfolioverwaltung"),
        ("S", "Vermögenserhalt und langfristiges Wachstum"),
        ("S", "Aufteilung zur Risikobegrenzung"),
        ("S", "Die drei klassischen Strategien (Übersicht)"),
        ("anlagevorschlag", 0, "PV 30 – Anlagestrategie (Ring + Positionen)"),
        ("wertentwicklung", 0, "PV 30 – Performance"),
        ("anlagevorschlag", 1, "PV 70 – Anlagestrategie (Ring + Positionen)"),
        ("wertentwicklung", 1, "PV 70 – Performance"),
        ("anlagevorschlag", 2, "PV 100 – Anlagestrategie (Ring + Positionen)"),
        ("wertentwicklung", 2, "PV 100 – Performance"),
        ("S", "Verwaltungsvergütung"),
        ("S", "Transaktionskosten"),
        ("S", "Unser Honorar"),
        ("S", "Steuerlicher Hinweis zum Honorar"),
        ("S", "Langfristiger Vermögenserhalt"),
        ("S", "Die optimale Vermögensverwaltungsstrategie"),
        ("S", "Zinsänderungsrisiko"),
        ("S", "Kombination verschiedener Anlageklassen"),
        ("S", "Regelmäßige Berichte"),
        ("S", "Wesentliche Finanzkennzahlen (AuM-Wachstum)"),
        ("S", "Individuell. Unabhängig. Vertrauensvoll."),
        ("S", "Anschreiben"),
        ("S", "Kluge Investitionen (ländlicher Grundbesitz)"),
        ("S", "Risikohinweise"),
        ("S", "Rechtliche Hinweise und Impressum"),
        ("S", "Stand / Rückseite"),
    ],
    # titel_text="": Vorlagen-Titel behalten. max_bottom_inch/row_h an der
    # Vorlage gemessen (Tabelle endet bei 6.36", Zeilenhöhe ~0.21") — nach
    # echtem Deploy ggf. feinjustieren. KEIN spalten_map (11 Spalten wie ESG).
    rollen_optionen={
        "anlagevorschlag": {"titel_text": "", "max_bottom_inch": 6.20,
                            "original_row_h_inch": 0.21},
    },
)

# Familie → (Vorlagen-Dateiname im Ordner Vorlage/, template_config).
# Nur Familien mit EIGENER Vorlage hier eintragen. Familien ohne Eintrag
# (oder leere Familie) → Standard-Vorlage (Vorlage_FFPB.pptx, config None).
VORLAGEN_FAMILIEN = {
    "Thema": ("Vorlage_Thema.pptx", _THEMA_CONFIG),
    "CVV": ("Vorlage_cVV_Infoboard.pptx", _CVV_CONFIG),
    "ESG": ("Vorlage_ESG.pptx", _ESG_CONFIG),
    "ETF": ("Vorlage_ETF.pptx", _ETF_CONFIG),
    "comdirect": ("Vorlage_comdirect.pptx", _COMDIRECT_CONFIG),
}

# Familien, deren Broschüre IMMER alle Strategien enthält (Variante A).
# Wählt der Berater eine davon, lädt die App automatisch alle — in dieser
# Reihenfolge. Neue Familie? Nur hier und in VORLAGEN_FAMILIEN eintragen.
FAMILIE_ALLE_STRATEGIEN = {
    "CVV": _CVV_STRATEGIEN,
    "ESG": _ESG_STRATEGIEN,
    "ETF": _ETF_STRATEGIEN,
    "comdirect": _COMDIRECT_STRATEGIEN,
}


# ══════════════════════════════════════════════════════════════════════════
#  AUSGABE-DATEINAMEN DER BROSCHÜRE — hier frei anpassbar
# ══════════════════════════════════════════════════════════════════════════
# Der Name der heruntergeladenen PowerPoint wird aus diesen drei Dicts gebaut.
# NUR HIER etwas ändern — der restliche Code bleibt gleich.
#
# Auflösung in dieser Reihenfolge (erster Treffer gewinnt):
#   1. EXPORT_NAME_STRATEGIE[<Strategie>]   – einzelne Strategie (höchste Prio)
#   2. EXPORT_NAME_FAMILIE[<Familie>]        – ganze Familie
#   3. EXPORT_NAME_DEFAULT                   – alles ohne eigenen Eintrag
#
# Platzhalter im Muster:  {datum}  {strategie}  {familie}
# Die Endung ".pptx" wird AUTOMATISCH angehängt — NICHT ins Muster schreiben.
#
# Datum: standardmäßig EXPORT_DATUM_FORMAT (strftime). Ein Eintrag kann ein
# eigenes Format bekommen, indem statt "Muster" ein Tupel ("Muster", "%Y%m%d")
# angegeben wird (siehe comdirect). {datum} = Auswertungsdatum der Portfolio-
# analyse; fehlt es, wird der Date-Tag aus dem UI (yyMMdd) eingesetzt.

EXPORT_DATUM_FORMAT = "%d.%m.%Y"          # z.B. 07.07.2026

EXPORT_NAME_DEFAULT = "Portfolioanalyse_{strategie}_{datum}"

# Ganze Familie → ein Name (Wert = "Muster" ODER ("Muster", "datumsformat")).
EXPORT_NAME_FAMILIE = {
    "CVV":       "cVV Broschüre_Infoboard_{datum}",
    "ETF":       "ETF Broschüre Infoboard {datum}",
    "ESG":       "ESG Broschüre Inforboard{datum}",
    "comdirect": ("Klassische Portfolioverwaltung_{datum}", "%Y%m%d"),
    "Thema":     "{strategie} Broschüre_{datum}",   # → "Pro Broschüre_…", "Pro Dividende Broschüre_…"
}

# Einzelne Strategie → eigener Name (schlägt die Familie). Beispiel: die
# Thema-Strategie heißt "Offensiv", der Broschürenname soll aber "Offensive"
# sein. Weitere Ausnahmen einfach hier ergänzen.
EXPORT_NAME_STRATEGIE = {
    "Offensiv": "Offensive Broschüre_{datum}",
}
# ══════════════════════════════════════════════════════════════════════════
