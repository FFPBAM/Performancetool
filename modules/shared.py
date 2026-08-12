# modules/shared.py
"""Gemeinsame Funktionen für Performance- und Portfolioanalyse-Seiten."""

import os
import re
import glob
import hmac
import math
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image as PILImage

from modules import anlagekriterien as _kriterien
from modules import formats as _formats


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
LOGO_FILENAME = "Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg"

# Name des Tools — EINE Quelle für Login, Browser-Tab und Kopfzeile.
# 10.08.2026: Vorher standen an diesen drei Stellen drei verschiedene Namen
# ("Performance VV Rechner | Fürst Fugger Privatbank" im Login,
# "FFPB – Performance & Portfolioanalyse" im Tab, "Fürst Fugger Privatbank –
# Vermögensverwaltung" in der Kopfzeile). Der Login-Titel nannte zudem nur
# die halbe Anwendung — die Portfolioanalyse ist ein gleichwertiger Bereich —
# und "Rechner" untertreibt: das Tool erzeugt die fertigen Kundenbroschüren.
# Der neue Name benennt genau die beiden Bereiche der Navigation.
APP_NAME  = "Performance & Portfolioanalyse"
BANK_NAME = "Fürst Fugger Privatbank"
APP_TITLE = f"{APP_NAME} | {BANK_NAME}"

# Corporate Colors (Fürst Fugger Privatbank) — gilt für ALLE Tabs.
# Stand: Juni 2026. Performance-Tab wurde von alten Theme-Farben auf Corporate umgestellt.
FFPB_DARK     = "#003460"   # Fuggerblau (vorher #1B3A5C)
FFPB_GOLD     = "#C3A069"   # Fuggergold (vorher #B8973A)
FFPB_BLUE2    = "#4A7FAA"   # Mittelblau (vorher #2C5F8A)
FFPB_SAND     = "#D4BD8A"   # Sand (neu)
FFPB_LIGHT    = "#7FABC8"   # Hellblau (vorher #A8CBE8)

# Erweiterte Corporate-Palette (für PDF-Linien-Charts, Reihenfolge wie Portfolioanalyse RING_COLORS)
FFPB_PALETTE = [
    "#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8",
    "#8B7340", "#A8CBE8", "#5C6B3C", "#E8D5B0", "#2C5F8A",
    "#C4C4C4", "#3A7CA5", "#F0C070", "#6A9BC3", "#2A4A6C",
]

MAPPING_PATH      = "Mapping_Honorarsatz.xlsx"
NAME_MAPPING_PATH = "Mapping_Namen.xlsx"
# Anlagekriterien: Pfad und Spalten kommen aus dem UI-freien Modul, damit
# App und Broschüren-Export garantiert dieselben verwenden.
ANLAGEKRITERIEN_PATH = _kriterien.PFAD
KRITERIEN_SPALTEN = _kriterien.SPALTEN
KRITERIEN_KEY_SPALTE = _kriterien.KEY_SPALTE
DATA_FOLDER       = "Daten"
DATA_FOLDER_PF    = "Daten_PF"
DURATION_FOLDER   = "Duration"
ZIELDATEN_FOLDER  = "Zieldaten"
EXCLUDE_SUBSTRINGS = ["Stiftung"]

# ENTFERNT 11.08.2026: Hier stand die PDF-Schriftregistrierung
# (FONT_DIR/PDF_FONT/PDF_FONT_BOLD/_register_pdf_fonts) für reportlab.
# Mit dem Wegfall der PDF-Ausgabe in der Performance-Ansicht — die
# Portfolioanalyse hatte ihre schon im Juli verloren — erzeugt das Tool
# überhaupt keine PDFs mehr; Kundendokumente entstehen ausschließlich als
# PowerPoint. Damit sind reportlab UND matplotlib aus requirements.txt
# verschwunden. Der Ordner `fonts/` bleibt liegen: die Schriftdateien
# gehören zum Corporate Design und kosten nichts.


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------
def check_login() -> bool:
    USERS = st.secrets["passwords"]
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    def verify_password() -> bool:
        username = st.session_state.get("username_input", "").strip()
        password = st.session_state.get("password_input", "")
        if username not in USERS:
            return False
        # hmac.compare_digest statt "==" (07.08.2026): vergleicht in
        # konstanter Zeit und verrät damit nicht über die Antwortdauer,
        # wie viele Zeichen des Passworts bereits stimmen. Der normale
        # ==-Vergleich bricht beim ersten falschen Zeichen ab.
        erwartet = str(USERS[username]).encode("utf-8")
        eingabe = str(password).encode("utf-8")
        if hmac.compare_digest(erwartet, eingabe):
            st.session_state.logged_in = True
            st.session_state.username = username
            return True
        return False

    if not st.session_state.logged_in:
        # Logo über dem Titel (11.08.2026): Es lag im Repo und wurde
        # ausschließlich in die frühere PDF-Ausgabe eingebettet — in der
        # Oberfläche tauchte es nie auf. Der Anmeldebildschirm ist die erste
        # Seite, die ein Berater sieht.
        logo = get_logo_path()
        if logo:
            st.image(logo, width=260)
        st.title(APP_TITLE)
        st.write("Bitte melden Sie sich an, um fortzufahren.")
        st.text_input("Benutzername", key="username_input")
        st.text_input("Passwort", type="password", key="password_input")
        if st.button("Einloggen"):
            if verify_password():
                st.success("Erfolgreich eingeloggt!")
                st.rerun()
            else:
                st.error("Benutzername oder Passwort stimmt nicht. "
                         "Bitte erneut versuchen.")
        return False

    with st.sidebar:
        st.write(f"Angemeldet als: **{st.session_state.username}**")
        if st.button("Ausloggen"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
    return True


# ---------------------------------------------------------------------------
# Formatting Helpers
#
# ZUSAMMENGEFUEHRT 12.08.2026 (Backlog F): Hier standen eigene Fassungen von
# fmt_date_de und fmt_pct_de — formatgleich zu modules/formats.py, aber
# ungehaertet. Gemessen wurde:
#
#     Eingabe        formats        shared (vorher)
#     None           '–'            'None'
#     pd.NaT         '–'            ValueError   ← Absturz der Ansicht
#     float('nan')   '–'            'nan'
#
# fmt_date_de wird an 23 Stellen aufgerufen (Auflagedatum, Drawdown-Daten,
# Quelle-Zeile), fmt_pct_de an 29. Ein NaT aus einer unvollstaendigen
# Zeitreihe hat also nicht "–" angezeigt, sondern die Seite abgeraeumt.
#
# Die Namen bleiben (sie stehen an 60 Aufrufstellen), die Herkunft ist jetzt
# modules/formats.py — dieselbe Quelle, aus der auch die Broschuere liest.
# Damit koennen Tool und Kundendokument dieselbe Zahl nicht mehr
# unterschiedlich schreiben.
# ---------------------------------------------------------------------------
# Bewusst als Zuweisung und nicht als "from … import fmt_date_de": So ist
# sichtbar, dass shared diese Namen nur WEITERREICHT, und pyflakes haelt sie
# nicht faelschlich fuer unbenutzt (es kennt kein noqa).
EMPTY_VALUE = _formats.EMPTY_VALUE
fmt_date_de = _formats.fmt_date_de
fmt_pct_de = _formats.fmt_pct


def fmt_eur_de(v) -> str:
    """Euro-Betrag in deutscher Notation: 1.234,56 €

    Kein Gegenstueck in formats.py — die Broschuere weist keine Betraege aus,
    nur Prozente. Die Fehlwert-Behandlung ist trotzdem dieselbe (#46/#47):
    ein fehlender Betrag darf nicht als "nan €" in der Oberflaeche stehen.
    """
    if v is None:
        return EMPTY_VALUE
    try:
        v = float(v)
    except (TypeError, ValueError):
        return EMPTY_VALUE
    if math.isnan(v):
        return EMPTY_VALUE
    formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} €"


# ---------------------------------------------------------------------------
# Auto-detect newest date tag
# ---------------------------------------------------------------------------
def detect_newest_date_tag(data_folder: str, exclude_substrings: list = None) -> str:
    if exclude_substrings is None:
        exclude_substrings = EXCLUDE_SUBSTRINGS
    # Case-insensitive: .CSV und .csv
    all_csvs = glob.glob(os.path.join(data_folder, "*.CSV")) + glob.glob(os.path.join(data_folder, "*.csv"))
    all_csvs = list(set(all_csvs))
    tags = set()
    pattern = re.compile(r"_(\d{6})_")
    for f in all_csvs:
        basename = os.path.basename(f)
        if any(sub in basename for sub in exclude_substrings):
            continue
        m = pattern.search(basename)
        if m:
            tags.add(m.group(1))
    if not tags:
        return dt.date.today().strftime("%y%m%d")
    return max(tags)


# ---------------------------------------------------------------------------
# Name Mapping
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_mapping(mapping_path: str = MAPPING_PATH) -> pd.DataFrame:
    return pd.read_excel(mapping_path).round(6)

@st.cache_data(show_spinner=False)
def load_name_mapping(path: str = NAME_MAPPING_PATH) -> pd.DataFrame:
    return pd.read_excel(path)


@st.cache_data(show_spinner=False)
def load_anlagekriterien(path: str = ANLAGEKRITERIEN_PATH) -> pd.DataFrame:
    """Anlagekriterien je Strategie — hier NUR der Streamlit-Cache.

    Die Logik steht in ``modules/anlagekriterien.py``, weil ``pptx_export.py``
    sie ebenfalls braucht und bewusst streamlit-frei bleibt (Batch-Fähigkeit,
    Doku Abschnitt 13). Zwei Loader wären genau die Duplizierung, an der die
    Codebasis früher krankte.
    """
    return _kriterien.lade(path)


_MD_SONDERZEICHEN = ("\\", "*", "_", "`", "[", "]", "#")


def markdown_escapen(text: str) -> str:
    """Entschärft Markdown-Sonderzeichen in Werten aus der Konfiguration.

    Die Werte kommen aus einer Excel, die von Hand gepflegt wird. Ein
    Sternchen oder Unterstrich darin würde `st.markdown` sonst als Formatierung
    lesen und Text verschlucken.
    """
    text = str(text)
    for z in _MD_SONDERZEICHEN:
        text = text.replace(z, "\\" + z)
    return text


def zeige_anlagekriterien(strategie: str, kriterien: pd.DataFrame,
                          mit_strategiename: bool = False) -> bool:
    """Zeigt die Anlagekriterien einer Strategie. No-op ohne Kriterien.

    GEBAUT AUS NATIVEN STREAMLIT-BAUSTEINEN (überarbeitet 10.08.2026).

    Die erste Fassung war ein HTML-Block mit eigener heller Fläche und
    Fuggerblau als Textfarbe. Im **Dark Mode** stand damit ein greller weißer
    Kasten mitten in der dunklen App — der Block arbeitete gegen das Theme
    statt sich einzufügen.

    Naheliegender Reparaturversuch wäre `var(--background-color)` gewesen.
    Geprüft und verworfen: Streamlit 1.61 stellt **keine** Theme-CSS-Variablen
    bereit (weder in `static/css` noch im JS-Bundle nachweisbar) — die
    Variable wäre still ins Leere gelaufen und der Kasten hätte je nach
    Browser gar keinen Hintergrund gehabt.

    Deshalb jetzt ohne eine Zeile eigenes CSS:
      `st.container(border=True)` liefert Fläche und Rahmen aus dem aktiven
      Theme, `st.caption` die gedämpfte Beschriftung, fettes `st.markdown` den
      Wert. Hell wie dunkel korrekt, ohne dass wir Farben pflegen.

    Die Gestaltungsidee aus Variante B bleibt erhalten: **keine Symbole**
    (ein Häkchen würde „erfüllt" behaupten, hier steht aber eine REGEL), die
    Bezeichnung tritt zurück, der Wert ist die Hauptsache.

    Bewusst NICHT `st.metric`: In der Portfolioanalyse steht direkt darüber
    die Kennzahlen-Zeile aus `st.metric`. Gleiche Optik würde verwischen, was
    das Portfolio IST und was die Strategie ERLAUBT.

    mit_strategiename=True setzt den Namen in die Überschrift — nötig, sobald
    auf einer Seite MEHRERE Blöcke stehen (Portfolio + Vergleichsportfolio),
    sonst wäre nicht erkennbar, welcher zu welcher Strategie gehört.

    Returns: True, wenn etwas gezeichnet wurde.
    """
    paare = anlagekriterien_fuer(strategie, kriterien)
    if not paare:
        return False

    titel = "Anlagekriterien"
    if mit_strategiename:
        titel = f"Anlagekriterien — {strategie}"

    # OHNE Rahmen (Wunsch Philip, 10.08.2026): Die graue Umrandung von
    # `border=True` legte eine zusätzliche Linie um den Block, die im
    # Seitenfluss unruhig wirkte. Die Gliederung tragen die Überschriften
    # darüber und darunter — der Kasten braucht keine eigene Kante.
    # Der Container bleibt (ohne Rahmen), damit Titel und Spalten als eine
    # Einheit zusammenbleiben.
    with st.container(border=False):
        st.markdown(f"**{markdown_escapen(titel)}**")
        spalten = st.columns(len(paare))
        for spalte, (bez, wert) in zip(spalten, paare):
            with spalte:
                st.caption(markdown_escapen(bez))
                st.markdown(f"**{markdown_escapen(wert)}**")
    return True


def anlagekriterien_fuer(strategie: str, kriterien: pd.DataFrame):
    """Kriterien EINER Strategie als [(Bezeichnung, Wert), …].
    Durchreiche auf ``modules.anlagekriterien.fuer`` — siehe dort."""
    return _kriterien.fuer(strategie, kriterien)

def build_name_lookups(name_mapping: pd.DataFrame, available_csv_names: set):
    """Baut Lookup-Dicts aus dem Name-Mapping.
    Returns: (display_names_ordered, display_to_csv, display_to_benchmark)
    """
    col_display = name_mapping.columns[0]
    col_csv_key = name_mapping.columns[1]
    col_bench   = name_mapping.columns[3]

    filtered = name_mapping[name_mapping[col_csv_key].isin(available_csv_names)].copy()
    display_names_ordered = filtered[col_display].tolist()
    display_to_csv = dict(zip(filtered[col_display], filtered[col_csv_key]))
    display_to_benchmark = dict(zip(filtered[col_display], filtered[col_bench]))

    return display_names_ordered, display_to_csv, display_to_benchmark


def csv_name_to_display(csv_name: str, name_mapping: pd.DataFrame) -> str:
    """Wandelt einen CSV-Portfolio-Namen in den Anzeigenamen um."""
    col_display = name_mapping.columns[0]
    col_csv_key = name_mapping.columns[1]
    match = name_mapping.loc[name_mapping[col_csv_key] == csv_name, col_display]
    if not match.empty:
        return match.iloc[0]
    return csv_name


# ---------------------------------------------------------------------------
# Logo Helper
# ---------------------------------------------------------------------------
def get_logo_aspect(logo_path: str = None) -> float:
    if logo_path is None:
        logo_path = LOGO_FILENAME
    if logo_path and os.path.exists(logo_path):
        img = PILImage.open(logo_path)
        w, h = img.size
        return h / w
    return 0.3

def get_logo_path() -> str:
    return LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else None


# ---------------------------------------------------------------------------
# Performance-CSV Loading & Timeseries-Build (für Performance-Tab + PPTX-Export)
# ---------------------------------------------------------------------------
def to_decimal_interval(series_float):
    """Interval-Performance zu Dezimal: 1.5 → 0.015 (wenn >1.0); 0.015 bleibt."""
    x = series_float.to_numpy(dtype=float)
    ax = np.nan_to_num(np.abs(x), nan=0.0)
    if ax.max() > 1.0 or np.median(ax) > 0.2:
        x = x / 100.0
    return x


def read_one_csv(path):
    """Liest eine FFPB-Portfolio-CSV (ISO-8859-1, semicolon, German decimals)."""
    return pd.read_csv(path, comment="#", encoding="ISO-8859-1", delimiter=";",
                       decimal=",", thousands=".", dtype=str)


def parse_dates_col(vv):
    return pd.to_datetime(vv["Datum"], format="%d.%m.%Y", errors="raise")


def extract_benchmark_name(vv):
    for c in ["Benchmark Name", "Benchmark", "Benchmarkname",
              "Benchmark Name ", "Benchmark-Bezeichnung"]:
        if c in vv.columns:
            v = vv.loc[0, c]
            if pd.notna(v) and str(v).strip():
                return str(v).strip()
    return "Benchmark"


@st.cache_data(show_spinner=True)
def load_all_csvs(data_folder, date_tag, exclude_substrings):
    """Lädt alle Performance-CSVs für einen date_tag aus dem data_folder.

    Sucht .CSV UND .csv (07.08.2026): Streamlit Cloud läuft auf Linux und
    unterscheidet Groß-/Kleinschreibung — eine klein geschriebene Datei wäre
    dort stillschweigend verschwunden, während detect_newest_date_tag ihren
    Tag trotzdem gefunden hätte. Ergebnis wäre die irreführende Meldung
    "Keine Dateien für Tag X" gewesen, obwohl die Datei vorhanden ist.
    Unter Windows liefern beide Muster dieselben Treffer → set() dedupliziert.
    """
    files = set()
    for endung in ("CSV", "csv"):
        files.update(glob.glob(os.path.join(data_folder, f"*_{date_tag}_*.{endung}")))
    return sorted(p for p in files
                  if not any(sub in os.path.basename(p) for sub in exclude_substrings))


@st.cache_data(show_spinner=True)
def build_portfolio_timeseries(files, mapping):
    """Baut Zeitreihen-Dict {csv_name: DataFrame mit ret_port, ret_bm, rf, fee_default} aus den CSVs."""
    out = {}
    for path in files:
        vv = read_one_csv(path)
        pn = vv.loc[0, "Portfolio Name"]
        bn = extract_benchmark_name(vv)
        dates = parse_dates_col(vv)
        vv["Performance [%] (Intervall)"] = vv["Performance [%] (Intervall)"].astype(str).str.replace(",", ".").astype(float)
        rp = to_decimal_interval(vv.loc[1:, "Performance [%] (Intervall)"])
        rb = None
        if "Benchmark Performance [%] (Intervall)" in vv.columns:
            vv["Benchmark Performance [%] (Intervall)"] = vv["Benchmark Performance [%] (Intervall)"].astype(str).str.replace(",", ".").astype(float)
            rb = to_decimal_interval(vv.loc[1:, "Benchmark Performance [%] (Intervall)"])
        # Risikofreier Zins (annualisiert, dezimal)
        rf_arr = None
        if "Risiko freier Zins" in vv.columns:
            try:
                vv["Risiko freier Zins"] = vv["Risiko freier Zins"].astype(str).str.replace(",", ".").astype(float)
                rf_raw = vv.loc[1:, "Risiko freier Zins"].to_numpy(dtype=float)
                if np.nanmedian(np.abs(rf_raw[~np.isnan(rf_raw)])) > 1.0:
                    rf_raw = rf_raw / 100.0
                rf_arr = rf_raw
            except Exception:
                rf_arr = None
        try:
            fd = float(mapping.loc[mapping["Inhaber"] == pn, "Honorarsatz Standard"].values[0])
        except Exception:
            fd = 0.0
        idx = dates.iloc[1:].reset_index(drop=True)
        df = pd.DataFrame(index=idx)
        df.index.name = "Datum"
        df["ret_port"] = rp
        df["ret_bm"] = rb if (rb is not None and len(rb) == len(df)) else np.nan
        df["rf"] = rf_arr if (rf_arr is not None and len(rf_arr) == len(df)) else np.nan
        df["fee_default"] = fd
        df = df.sort_index()
        df.attrs["benchmark_name"] = bn
        out[pn] = df
    return out
