# modules/shared.py
"""Gemeinsame Funktionen für Performance- und Portfolioanalyse-Seiten."""

import os
import re
import glob
import io
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image as PILImage


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
LOGO_FILENAME = "Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg"
FFPB_DARK     = "#1B3A5C"
FFPB_GOLD     = "#B8973A"
FFPB_LIGHT    = "#A8CBE8"
FFPB_BLUE2    = "#2C5F8A"

MAPPING_PATH      = "Mapping_Honorarsatz.xlsx"
NAME_MAPPING_PATH = "Mapping_Namen.xlsx"
DATA_FOLDER       = "Daten"
DATA_FOLDER_PF    = "Daten_PF"
DURATION_FOLDER   = "Duration"
ZIELDATEN_FOLDER  = "Zieldaten"
EXCLUDE_SUBSTRINGS = ["Stiftung"]


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
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            return True
        return False

    if not st.session_state.logged_in:
        st.title("Performance VV Rechner | Fürst Fugger Privatbank")
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
def detect_newest_date_tag(data_folder: str, exclude_substrings: list[str] | None = None) -> str:
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
def get_logo_aspect(logo_path: str | None = None) -> float:
    if logo_path is None:
        logo_path = LOGO_FILENAME
    if logo_path and os.path.exists(logo_path):
        img = PILImage.open(logo_path)
        w, h = img.size
        return h / w
    return 0.3

def get_logo_path() -> str | None:
    return LOGO_FILENAME if os.path.exists(LOGO_FILENAME) else None
