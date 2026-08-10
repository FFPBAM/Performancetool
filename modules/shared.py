# modules/shared.py
"""Gemeinsame Funktionen für Performance- und Portfolioanalyse-Seiten."""

import os
import re
import glob
import io
import hmac
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image as PILImage


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
DATA_FOLDER       = "Daten"
DATA_FOLDER_PF    = "Daten_PF"
DURATION_FOLDER   = "Duration"
ZIELDATEN_FOLDER  = "Zieldaten"
EXCLUDE_SUBSTRINGS = ["Stiftung"]

# PDF Font
FONT_DIR = "fonts"
PDF_FONT = "Helvetica"
PDF_FONT_BOLD = "Helvetica-Bold"

def _register_pdf_fonts():
    global PDF_FONT, PDF_FONT_BOLD
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        regular = os.path.join(FONT_DIR, "segoeui.ttf")
        bold = os.path.join(FONT_DIR, "segoeuib.ttf")
        if os.path.exists(regular):
            pdfmetrics.registerFont(TTFont("SegoeUI", regular))
            PDF_FONT = "SegoeUI"
            if os.path.exists(bold):
                pdfmetrics.registerFont(TTFont("SegoeUI-Bold", bold))
                PDF_FONT_BOLD = "SegoeUI-Bold"
            else:
                PDF_FONT_BOLD = "SegoeUI"
    except Exception:
        pass

_register_pdf_fonts()


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
        st.title(APP_TITLE)
        st.write("Bitte melden Sie sich an, um fortzufahren.")
        st.text_input("Benutzername", key="username_input")
        st.text_input("Passwort", type="password", key="password_input")
        if st.button("Einloggen"):
            if verify_password():
                st.success("Erfolgreich eingeloggt!")
                st.rerun()
            else:
                st.error("❌ Falscher Benutzername oder Passwort")
        return False

    with st.sidebar:
        st.write(f"👤 Angemeldet als: **{st.session_state.username}**")
        if st.button("Ausloggen"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
    return True


# ---------------------------------------------------------------------------
# Formatting Helpers
# ---------------------------------------------------------------------------
def fmt_date_de(d) -> str:
    if isinstance(d, pd.Timestamp):
        return d.strftime("%d.%m.%Y")
    if isinstance(d, dt.date):
        return d.strftime("%d.%m.%Y")
    return str(d)

def fmt_pct_de(v: float, decimals: int = 2) -> str:
    return f"{v * 100:.{decimals}f}%".replace(".", ",")

def fmt_eur_de(v: float) -> str:
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
