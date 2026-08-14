"""
modules/formats.py — Single Source of Truth für Format-Helpers und Text-Konstanten
der PPTX-Broschüre.

Was hier hingehört:
- Format-Helpers (Prozent, Ratio, Datum) — deutsche Notation
- PPTX-interne Format-Codes (für Chart-Daten-Labels via numFmt)
- Datums-Patterns (strftime)
- Disclaimer-Texte (aktuell aus Vorlage; bei Bedarf vom Code überschreibbar)
- Quelle-Datum-Format

Was hier NICHT hingehört:
- Farben (in der Vorlage, siehe Doku §10.3)
- Layout / Shape-Größen (in der Vorlage)
- Berechnungs-Logik (in analytics.py — folgt in Schritt 2)

Diese Datei hat KEINE Imports von Streamlit oder python-pptx.
Sie kann unverändert in lokalen Python-Skripten genutzt werden.
"""

import math


# ─────────────────────────────────────────────────────────────────────────────
# PPTX-interne Format-Codes (für <c:numFmt> in Chart-XML)
# ─────────────────────────────────────────────────────────────────────────────

PCT_FORMAT_CODE = "0.00%"
"""Format-Code für Daten-Labels in Säulen-/Balken-Charts (z.B. '5,23%')."""


# ─────────────────────────────────────────────────────────────────────────────
# Datums-Format
# ─────────────────────────────────────────────────────────────────────────────

DATE_FORMAT_DE = "%d.%m.%Y"
"""Deutsches Datum: 19.06.2026"""


MONATSNAMEN_KURZ = ("Jan", "Feb", "März", "Apr", "Mai", "Jun",
                    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")
"""Monatskuerzel fuer die Spaltenkoepfe der Monatsrenditen-Heatmap.

Fest verdrahtet und NICHT ueber strftime("%b") erzeugt: Das Ergebnis von
%b haengt an der Locale des Rechners und liefert auf einem englisch
eingestellten System "Mar" statt "März". Eine Broschuerenbank zeigt deutsche
Monatsnamen, unabhaengig davon, wie der Server konfiguriert ist.

"März" ausgeschrieben statt "Mrz" (Philip, 14.08.2026). Die Spalte wird
dadurch einen Schritt breiter als die uebrigen elf — das ist in Kauf
genommen, weil "Mrz" wie ein Tippfehler aussieht."""


MONATSNAMEN_LANG = ("Januar", "Februar", "März", "April", "Mai", "Juni",
                    "Juli", "August", "September", "Oktober", "November",
                    "Dezember")
"""Ausgeschriebene Monatsnamen fuer FLIESSTEXTE.

Getrennt von den Kuerzeln, weil beide unterschiedliche Aufgaben haben: In
einer Spaltenueberschrift zaehlt die Breite, in einem Satz die Lesbarkeit.
"bester Monat: April 2020" liest sich, "bester Monat: Apr 2020" stolpert."""


def monat_kurz(monat: int) -> str:
    """Monatsnummer 1-12 zum deutschen Kuerzel; ausserhalb: Fehlwert."""
    return _monat_name(monat, MONATSNAMEN_KURZ)


def monat_lang(monat: int) -> str:
    """Monatsnummer 1-12 zum ausgeschriebenen Namen; ausserhalb: Fehlwert."""
    return _monat_name(monat, MONATSNAMEN_LANG)


def _monat_name(monat, namen):
    # bool ZUERST abfangen: In Python ist isinstance(True, int) wahr, True
    # waere sonst der Januar und False ein Fehlwert statt beides ein Fehlwert.
    if isinstance(monat, bool) or not isinstance(monat, int):
        return EMPTY_VALUE
    if 1 <= monat <= 12:
        return namen[monat - 1]
    return EMPTY_VALUE


# ─────────────────────────────────────────────────────────────────────────────
# Quelle-Text (auf jeder dynamischen Folie unten rechts)
# ─────────────────────────────────────────────────────────────────────────────

QUELLE_PREFIX = "Quelle: Eigene Berechnung, Stand "
"""Wird durch das aktuelle Datum ergänzt: 'Quelle: Eigene Berechnung, Stand 19.06.2026'"""


def quelle_text(date_value) -> str:
    """Baut den vollständigen Quelle-Text mit Datum.

    Args:
        date_value: datetime/Timestamp/date → wird zu DD.MM.YYYY formatiert

    Returns: 'Quelle: Eigene Berechnung, Stand 19.06.2026'
    """
    return QUELLE_PREFIX + fmt_date_de(date_value)


# ─────────────────────────────────────────────────────────────────────────────
# Disclaimer-Texte (aus Vorlage extrahiert — Stand Juni 2026)
# ─────────────────────────────────────────────────────────────────────────────

DISCLAIMER_PERFORMANCE = (
    "Die aufgeführten Zahlen beziehen sich auf die Wertentwicklung in der Vergangenheit. "
    "Wert und Erträge einer Vermögensanlage können steigen oder fallen. "
    "Eine positive Entwicklung in der Vergangenheit ist keine Garantie für eine zukünftige Wertentwicklung. "
    "Der unterjährige Performance Ausweis erfolgt vor Kosten (ab 30.06. abzüglich halbjährigen Honorarsatz). "
    "Die weiteren Performance Angaben wurden nach Kosten berechnet. "
    "Sowohl das VV Honorar als auch fremde Spesen und evtl. Produktkosten wurden berücksichtigt. "
    "Die Inflation kann negative Auswirkungen auf den Wert und die nominale Rendite Ihres Anlagevermögens haben. "
    "So kann insbesondere bei risikofreien Anlagen ein Wertverlust dadurch eintreten, "
    "dass die negative Auswirkung der Inflation die nominale Rendite übersteigt. "
    "Auch eine geringe Anlagedauer und die Gesamtkosten- und Gebühren können negativ "
    "das Risiko-Rendite-Verhältnis beeinflussen."
)
"""Disclaimer auf der Performance-Folie (Slide 8 nach Reorder)."""


# ─────────────────────────────────────────────────────────────────────────────
# Format-Helpers (Zahlen → deutsche Strings)
# ─────────────────────────────────────────────────────────────────────────────

# Konstante für "kein Wert verfügbar" — em-dash (–) für visuelle Klarheit
EMPTY_VALUE = "–"


def fmt_pct(value, decimals: int = 2) -> str:
    """Formatiert einen dezimalen Wert als deutschen Prozent-String.

    Args:
        value: Dezimalwert (0.0523 → '5,23%')
        decimals: Nachkommastellen (default: 2)

    Returns:
        Formatierter String oder '–' bei None/NaN.

    Examples:
        >>> fmt_pct(0.0523)
        '5,23%'
        >>> fmt_pct(0.05, decimals=1)
        '5,0%'
        >>> fmt_pct(None)
        '–'
        >>> fmt_pct(float('nan'))
        '–'
    """
    if value is None:
        return EMPTY_VALUE
    try:
        v = float(value)
        if math.isnan(v):
            return EMPTY_VALUE
        return f"{v * 100:.{decimals}f}%".replace(".", ",")
    except (TypeError, ValueError):
        return EMPTY_VALUE


def fmt_ratio(value, decimals: int = 2) -> str:
    """Formatiert einen Ratio-Wert (z.B. Sharpe) als deutsche Dezimalzahl.

    Args:
        value: Dezimalwert (0.43 → '0,43')
        decimals: Nachkommastellen (default: 2)

    Returns:
        Formatierter String oder '–' bei None/NaN.

    Examples:
        >>> fmt_ratio(0.43)
        '0,43'
        >>> fmt_ratio(-1.236)
        '-1,24'
        >>> fmt_ratio(None)
        '–'
    """
    if value is None:
        return EMPTY_VALUE
    try:
        v = float(value)
        if math.isnan(v):
            return EMPTY_VALUE
        return f"{v:.{decimals}f}".replace(".", ",")
    except (TypeError, ValueError):
        return EMPTY_VALUE


def fmt_date_de(value) -> str:
    """Formatiert ein Datum als 'DD.MM.YYYY'.

    Args:
        value: datetime, Timestamp, date oder bereits formatierter String

    Returns:
        'DD.MM.YYYY' oder '–' bei None.

    Examples:
        >>> import datetime
        >>> fmt_date_de(datetime.date(2026, 6, 19))
        '19.06.2026'
        >>> fmt_date_de(None)
        '–'
    """
    if value is None:
        return EMPTY_VALUE
    try:
        # Ein Fehlwert darf nie wie ein Datum aussehen (Transferwissen #46).
        # Eine leere Zelle kommt aus Excel/pandas als float('nan') an, nicht
        # als None — ohne diesen Zweig stand in der Broschüre wörtlich "nan"
        # (gefunden 12.08.2026 beim Schreiben von tests/test_formats.py).
        if isinstance(value, float) and math.isnan(value):
            return EMPTY_VALUE
        # pandas/numpy NaT-Check ohne pandas-Import (für Streamlit-freie Nutzung)
        if hasattr(value, '__class__') and value.__class__.__name__ in ('NaTType', 'NaT'):
            return EMPTY_VALUE
        if hasattr(value, 'strftime'):
            return value.strftime(DATE_FORMAT_DE)
        # Schon ein String? Durchreichen
        return str(value)
    except Exception:
        return EMPTY_VALUE
