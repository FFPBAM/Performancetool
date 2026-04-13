# modules/portfolio_builder.py
"""Portfolio Builder: Individuelles Portfolio zusammenstellen."""

import os
import re
import glob
import io
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from modules.shared import (
    FFPB_DARK, FFPB_GOLD, FFPB_LIGHT, FFPB_BLUE2,
    ZIELDATEN_FOLDER, DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS,
    fmt_date_de, fmt_pct_de, fmt_eur_de,
    detect_newest_date_tag,
)
from modules.portfolioanalyse import (
    build_allocation, build_ring_chart,
    build_grouped_title_table, build_top5_bar_chart, get_top_holdings,
    load_pf_csvs, build_pf_data,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_TITEL = 50
CASH_PCT = 0.05

SCHNELLZUGRIFFE = {
    "Rein Aktien":       {"Assetklasse": ["Aktien"]},
    "Rein Renten":       {"Assetklasse": ["Renten"]},
    "Multi-Asset":       {"Assetklasse": ["Aktien", "Renten"]},
    "High Yield (Kupon >3%)": {"Assetklasse": ["Renten"], "kupon_min": 0.03},
    "Kurze Duration (<3J)":   {"Assetklasse": ["Renten"], "duration_max": 3.0},
    "Lange Duration (>5J)":   {"Assetklasse": ["Renten"], "duration_min": 5.0},
    "Europa-Fokus":      {"Region": ["Deutschland", "Europa ohne Deutschland"]},
    "Nordamerika-Fokus": {"Region": ["Nordamerika"]},
    "Niedriges Risiko (Marktrisikowert ≤3)":  {"mrw_max": 3},
}


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def load_zieldaten(folder):
    all_files = glob.glob(os.path.join(folder, "*.CSV")) + glob.glob(os.path.join(folder, "*.csv"))
    if not all_files:
        return pd.DataFrame(), ""
    tag_pattern = re.compile(r"_(\d{6})_(\d{4})")
    def _sort_key(f):
        m = tag_pattern.search(os.path.basename(f))
        return m.group(1) + m.group(2) if m else "000000_0000"
    all_files.sort(key=_sort_key, reverse=True)
    newest_file = all_files[0]

    # Datum aus Dateiname extrahieren
    m = tag_pattern.search(os.path.basename(newest_file))
    file_date = m.group(1) if m else ""  # z.B. "260323"

    df = pd.read_csv(newest_file, comment="#", encoding="ISO-8859-1",
                     delimiter=";", decimal=",", thousands=".", dtype=str)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
            # Leere Werte, "-" und "nan" zu echtem NaN
            df[col] = df[col].replace(["nan", "-", "–", ""], np.nan)
    if "Kupon" in df.columns:
        df["Kupon_num"] = pd.to_numeric(df["Kupon"].astype(str).str.replace("%","").str.replace(",",".").str.strip(), errors="coerce") / 100.0
    else:
        df["Kupon_num"] = np.nan
    if "Duration" in df.columns:
        df["Duration_num"] = pd.to_numeric(df["Duration"].astype(str).str.replace(",","."), errors="coerce")
    else:
        df["Duration_num"] = np.nan
    if "Marktrisikowert" in df.columns:
        df["MRW_num"] = pd.to_numeric(df["Marktrisikowert"], errors="coerce")
    else:
        df["MRW_num"] = np.nan
    if "Fälligkeit" in df.columns:
        # Zuerst NaN-sichere Kopie, dann mehrere Formate probieren
        faell_raw = df["Fälligkeit"].copy()
        # Format 1: dd.mm.yyyy
        parsed = pd.to_datetime(faell_raw, format="%d.%m.%Y", errors="coerce")
        # Format 2: yyyy-mm-dd (falls ISO-Format)
        mask_nat = parsed.isna() & faell_raw.notna()
        if mask_nat.any():
            parsed2 = pd.to_datetime(faell_raw[mask_nat], format="%Y-%m-%d", errors="coerce")
            parsed.loc[mask_nat] = parsed2
        # Format 3: dd/mm/yyyy
        mask_nat = parsed.isna() & faell_raw.notna()
        if mask_nat.any():
            parsed3 = pd.to_datetime(faell_raw[mask_nat], format="%d/%m/%Y", errors="coerce")
            parsed.loc[mask_nat] = parsed3
        # Format 4: freies Parsen als Fallback
        mask_nat = parsed.isna() & faell_raw.notna()
        if mask_nat.any():
            parsed4 = pd.to_datetime(faell_raw[mask_nat], errors="coerce", dayfirst=True)
            parsed.loc[mask_nat] = parsed4
        df["Fälligkeit_parsed"] = parsed
    else:
        # Spaltenname könnte leicht abweichen
        for alt_name in ["Faelligkeit", "Fälligkeitsdatum", "Maturity", "fälligkeit"]:
            if alt_name in df.columns:
                df["Fälligkeit_parsed"] = pd.to_datetime(df[alt_name], errors="coerce", dayfirst=True)
                break
    return df, file_date


def _init_session_state():
    if "builder_portfolio" not in st.session_state:
        st.session_state.builder_portfolio = {}

def _reset_portfolio():
    st.session_state.builder_portfolio = {}
    st.session_state.pop("builder_loaded_mp", None)
    st.session_state.pop("builder_loaded_mp_date", None)

def _add_to_portfolio(wkn, weight=0.0):
    if len(st.session_state.builder_portfolio) >= MAX_TITEL:
        return False
    if wkn not in st.session_state.builder_portfolio:
        st.session_state.builder_portfolio[wkn] = weight
    return True

def _remove_from_portfolio(wkn):
    st.session_state.builder_portfolio.pop(wkn, None)


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------
def apply_filters(df, filters):
    result = df.copy()
    if filters.get("Assetklasse"): result = result[result["Assetklasse"].isin(filters["Assetklasse"])]
    if filters.get("Region"): result = result[result["Region"].isin(filters["Region"])]
    if filters.get("Segment"): result = result[result["Segment"].isin(filters["Segment"])]
    if filters.get("Masterlistenzuordnung"): result = result[result["Masterlistenzuordnung"].isin(filters["Masterlistenzuordnung"])]
    if filters.get("kupon_min") is not None: result = result[result["Kupon_num"] >= filters["kupon_min"]]
    if filters.get("duration_min") is not None: result = result[result["Duration_num"] >= filters["duration_min"]]
    if filters.get("duration_max") is not None: result = result[result["Duration_num"] <= filters["duration_max"]]
    if filters.get("mrw_max") is not None: result = result[result["MRW_num"] <= filters["mrw_max"]]
    return result


# ---------------------------------------------------------------------------
# Analyse-DataFrame
# ---------------------------------------------------------------------------
def build_builder_analysis_df(selected_wkns, universe):
    rows = []
    for wkn, weight in selected_wkns.items():
        match = universe[universe["WKN"] == wkn]
        if match.empty:
            continue
        row = match.iloc[0]
        rows.append({
            "Wertpapier": str(row["Name"]) if "Name" in row.index and pd.notna(row["Name"]) else "",
            "WKN": wkn,
            "ISIN": str(row["ISIN"]) if "ISIN" in row.index and pd.notna(row["ISIN"]) else "",
            "Gewicht": weight,
            "Segment": str(row["Segment"]) if "Segment" in row.index and pd.notna(row["Segment"]) else "",
            "Region": str(row["Region"]) if "Region" in row.index and pd.notna(row["Region"]) else "",
            "Gattung": str(row["Assetklasse"]) if "Assetklasse" in row.index and pd.notna(row["Assetklasse"]) else "",
            "Kupon": float(row["Kupon_num"]) if "Kupon_num" in row.index and pd.notna(row["Kupon_num"]) else np.nan,
            "Duration_num": float(row["Duration_num"]) if "Duration_num" in row.index and pd.notna(row["Duration_num"]) else np.nan,
            "Fälligkeit_parsed": row["Fälligkeit_parsed"] if "Fälligkeit_parsed" in row.index and pd.notna(row["Fälligkeit_parsed"]) else pd.NaT,
            "Marktrisikowert": float(row["MRW_num"]) if "MRW_num" in row.index and pd.notna(row["MRW_num"]) else np.nan,
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def calc_weighted_duration(df):
    bonds = df[df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty or bonds["Duration_num"].isna().all(): return None
    w = bonds["Gewicht"].fillna(0); d = bonds["Duration_num"].fillna(0)
    return float((w * d).sum() / w.sum()) if w.sum() > 0 else None

def calc_weighted_kupon(df):
    bonds = df[df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty or bonds["Kupon"].isna().all(): return None
    w = bonds["Gewicht"].fillna(0); k = bonds["Kupon"].fillna(0)
    return float((w * k).sum() / w.sum()) if w.sum() > 0 else None


def _show_builder_disclaimer(zm_hint):
    """Zeigt den Disclaimer am Ende des Builders."""
    st.markdown("---")
    st.markdown("##### Disclaimer")
    st.markdown(
        "Das zusammengestellte Portfolio stellt eine simulierte Zusammensetzung dar und spiegelt keine "
        "tatsächliche Vermögensverwaltung wider. Die angezeigten Gewichtungen, Kennzahlen und Allokationen "
        "basieren auf den zum Stichtag verfügbaren Stammdaten des Anlageuniversums."
    )
    st.markdown(
        "Die Zuordnung von Titeln zu Segmenten, Regionen und Assetklassen sowie die Masterlistenzuordnung "
        "können sich jederzeit ändern. Vor der Umsetzung ist die aktuelle Zulassung und Klassifizierung "
        "der Titel zu prüfen. Die Anforderungen der Produktgovernance (Zielmarktprüfung) sind einzuhalten "
        "und Kunden entsprechend zu informieren."
    )
    st.markdown(
        "Die Portfoliozusammenstellung dient ausschließlich der unverbindlichen Veranschaulichung im "
        "Beratungsgespräch und stellt keine Anlageberatung oder -empfehlung dar. Alle Angaben sind ohne Gewähr."
    )
    st.markdown(f"**Quelle:** Infront & eigene Berechnungen, Stand: {zm_hint}")
    st.markdown("**Ansprechpartner:** PBAM")


# ---------------------------------------------------------------------------
# Streamlit Rendering
# ---------------------------------------------------------------------------
def render_portfolio_builder(name_mapping, anlagevolumen=0.0):
    _init_session_state()
    use_volume = anlagevolumen > 0

    st.caption("⚠️ Ihr Portfolio wird nur in der aktuellen Sitzung gespeichert. Bitte vor dem Ausloggen als CSV exportieren.")

    universe, zielmarkt_date = load_zieldaten(ZIELDATEN_FOLDER)
    if universe.empty:
        st.warning(f"Keine Zieldaten in {ZIELDATEN_FOLDER}/ gefunden.")
        return

    # WKN-Lookup (normalisiert → original)
    wkn_lookup = {}
    for _, r in universe.iterrows():
        w = str(r["WKN"]).strip().upper()
        if w and w != "NAN":
            wkn_lookup[w] = str(r["WKN"]).strip()

    # Zielmarkt-Datum formatieren
    zm_hint = ""
    if zielmarkt_date and len(zielmarkt_date) == 6:
        zm_hint = f"{zielmarkt_date[4:6]}.{zielmarkt_date[2:4]}.20{zielmarkt_date[0:2]}"

    st.success(f"📂 Anlageuniversum: **{len(universe)} Titel** geladen (Stand: {zm_hint})")

    # Hinweis + Quelle oben
    st.caption("⚠️ **Hinweise:** Siehe Disclaimer unten!")
    st.caption(f"📊 **Quelle:** Infront & eigene Berechnungen, Stand: {zm_hint}")

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 1: MUSTERPORTFOLIO & SCHNELLZUGRIFFE
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("### ⚡ Schnellzugriffe")

    sz_cols = st.columns(5)
    for i, name in enumerate(SCHNELLZUGRIFFE.keys()):
        with sz_cols[i % 5]:
            if st.button(name, key=f"sz_{i}", use_container_width=True):
                preset = SCHNELLZUGRIFFE[name]
                st.session_state["f_asset"] = preset.get("Assetklasse", [])
                st.session_state["f_region"] = preset.get("Region", [])
                st.session_state["f_segment"] = []
                st.session_state["f_kmin"] = float(preset.get("kupon_min", 0) * 100) if preset.get("kupon_min") else 0.0
                st.session_state["f_dmin"] = float(preset.get("duration_min", 0.0))
                st.session_state["f_dmax"] = float(preset.get("duration_max", 30.0))
                st.session_state["f_mrw"] = int(preset.get("mrw_max", 7))
                st.session_state["f_ml"] = []
                st.rerun()

    # Musterportfolio laden
    auto_tag_pf = detect_newest_date_tag(DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS)
    pf_files = load_pf_csvs(DATA_FOLDER_PF, auto_tag_pf)
    pf_data = build_pf_data(pf_files) if pf_files else {}

    col_display_nm = name_mapping.columns[0]
    col_csv_key_nm = name_mapping.columns[1]
    available_mp = set(pf_data.keys())
    filtered_mp = name_mapping[name_mapping[col_csv_key_nm].isin(available_mp)]
    mp_names = ["-- Kein Musterportfolio --"] + filtered_mp[col_display_nm].tolist()
    mp_to_csv = dict(zip(filtered_mp[col_display_nm], filtered_mp[col_csv_key_nm]))

    mp_sel = st.selectbox("📦 Musterportfolio als Startportfolio laden", mp_names, key="builder_mp")
    if st.button("📥 Startportfolio übernehmen", key="load_mp"):
        if mp_sel != "-- Kein Musterportfolio --":
            csv_name = mp_to_csv.get(mp_sel)
            if csv_name and csv_name in pf_data:
                mp_df = pf_data[csv_name]
                new_portfolio = {}
                not_found = []
                for _, row in mp_df.iterrows():
                    titel = str(row["Wertpapier"]).strip() if "Wertpapier" in mp_df.columns else "?"
                    gew = float(row["Gewicht"]) if "Gewicht" in mp_df.columns and pd.notna(row["Gewicht"]) else 0.0
                    matched = None
                    if "WKN" in mp_df.columns:
                        w = str(row["WKN"]).strip().upper()
                        if w in wkn_lookup:
                            matched = wkn_lookup[w]
                    if matched is None and "Name" in universe.columns:
                        nm = universe[universe["Name"].str.upper() == titel.upper()]
                        if not nm.empty:
                            matched = str(nm.iloc[0]["WKN"]).strip()
                    if matched:
                        new_portfolio[matched] = gew
                    else:
                        not_found.append(titel)
                st.session_state.builder_portfolio = new_portfolio
                st.session_state.builder_loaded_mp = mp_sel
                st.session_state.builder_loaded_mp_date = auto_tag_pf
                if new_portfolio:
                    st.success(f"✅ {len(new_portfolio)} von {len(mp_df)} Titeln aus **{mp_sel}** geladen")
                if not_found:
                    st.warning(f"⚠️ {len(not_found)} nicht gefunden: {', '.join(not_found[:8])}")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 2: FILTER (über der Suche, standardmäßig offen)
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 🔍 Anlageuniversum filtern")

    f1, f2, f3, f4 = st.columns(4)
    with f1: st.multiselect("Assetklasse", sorted(universe["Assetklasse"].dropna().unique().tolist()), key="f_asset", placeholder="z.B. Aktien, Renten...")
    with f2: st.multiselect("Region", sorted(universe["Region"].dropna().unique().tolist()), key="f_region", placeholder="z.B. Nordamerika, Europa...")
    with f3: st.multiselect("Segment", sorted(universe["Segment"].dropna().unique().tolist()), key="f_segment", placeholder="z.B. Technologie, Pharma...")
    with f4: st.multiselect("Masterlistenzuordnung", sorted(universe["Masterlistenzuordnung"].dropna().unique().tolist()), key="f_ml", placeholder="z.B. Vermögensverwaltung+Beratung")

    show_adv_filters = st.checkbox("Erweiterte Filter anzeigen", value=False, key="adv_filters")
    if show_adv_filters:
        ef1, ef2, ef3, ef4 = st.columns(4)
        with ef1: st.number_input("Kupon min (%)", 0.0, 20.0, value=0.0, step=0.5, key="f_kmin")
        with ef2: st.number_input("Duration min (J)", 0.0, 30.0, value=0.0, step=0.5, key="f_dmin")
        with ef3: st.number_input("Duration max (J)", 0.0, 30.0, value=30.0, step=0.5, key="f_dmax")
        with ef4: st.number_input("Risiko max", 1, 7, value=7, step=1, key="f_mrw")

    # Gefilterte Übersichtstabelle
    filters = {}
    fa = st.session_state.get("f_asset", [])
    fr = st.session_state.get("f_region", [])
    fs = st.session_state.get("f_segment", [])
    fm = st.session_state.get("f_ml", [])
    fkm = st.session_state.get("f_kmin", 0.0)
    fdm = st.session_state.get("f_dmin", 0.0)
    fdx = st.session_state.get("f_dmax", 30.0)
    fmr = st.session_state.get("f_mrw", 7)
    if fa: filters["Assetklasse"] = fa
    if fr: filters["Region"] = fr
    if fs: filters["Segment"] = fs
    if fm: filters["Masterlistenzuordnung"] = fm
    if fkm > 0: filters["kupon_min"] = fkm / 100.0
    if fdm > 0: filters["duration_min"] = fdm
    if fdx < 30: filters["duration_max"] = fdx
    if fmr < 7: filters["mrw_max"] = fmr

    filtered = apply_filters(universe, filters)
    st.caption(f"📋 {len(filtered)} Titel gefunden")

    show_table = st.checkbox("Gefilterte Titel anzeigen", value=False, key="show_filtered_table")
    if show_table:
        show_cols = ["Name", "WKN", "ISIN", "Assetklasse", "Segment", "Region", "Kupon", "Duration", "Fälligkeit", "Marktrisikowert"]
        st.dataframe(filtered[[c for c in show_cols if c in filtered.columns]].head(200),
                     use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 3: TITEL HINZUFÜGEN (Multiselect – nur zum Hinzufügen!)
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("### 🔎 Titel suchen & zum Portfolio hinzufügen")

    # Aktive Filter auf Suchoptionen anwenden
    active_filters = {}
    f_asset_active = st.session_state.get("f_asset", [])
    f_region_active = st.session_state.get("f_region", [])
    f_segment_active = st.session_state.get("f_segment", [])
    f_ml_active = st.session_state.get("f_ml", [])
    f_kmin_active = st.session_state.get("f_kmin", 0.0)
    f_dmin_active = st.session_state.get("f_dmin", 0.0)
    f_dmax_active = st.session_state.get("f_dmax", 30.0)
    f_mrw_active = st.session_state.get("f_mrw", 7)

    if f_asset_active: active_filters["Assetklasse"] = f_asset_active
    if f_region_active: active_filters["Region"] = f_region_active
    if f_segment_active: active_filters["Segment"] = f_segment_active
    if f_ml_active: active_filters["Masterlistenzuordnung"] = f_ml_active
    if f_kmin_active > 0: active_filters["kupon_min"] = f_kmin_active / 100.0
    if f_dmin_active > 0: active_filters["duration_min"] = f_dmin_active
    if f_dmax_active < 30: active_filters["duration_max"] = f_dmax_active
    if f_mrw_active < 7: active_filters["mrw_max"] = f_mrw_active

    if active_filters:
        search_universe = apply_filters(universe, active_filters)
        st.caption(f"🔍 Suche eingeschränkt auf **{len(search_universe)} Titel** – Filter oben sind aktiv")
    else:
        search_universe = universe
        st.caption("Durchsucht das gesamte Anlageuniversum. Über die Filter oben können Sie einschränken.")

    search_sorted = search_universe.sort_values("Name")
    search_options = (
        search_sorted["Name"].fillna("") + "  (" +
        search_sorted["WKN"].fillna("") + " | " +
        search_sorted["ISIN"].fillna("") + ")"
    ).tolist()
    search_wkns = search_sorted["WKN"].tolist()
    label_to_wkn = dict(zip(search_options, search_wkns))

    new_titles = st.multiselect(
        "Titel suchen und hinzufügen",
        options=search_options,
        default=[],
        key="builder_add_titles",
        placeholder="z.B. Microsoft, A14Y6F oder US02079K3059...",
        help=f"Maximal {MAX_TITEL} Titel. Ausgewählte werden zum Portfolio hinzugefügt."
    )

    if new_titles:
        for lbl in new_titles:
            wkn = label_to_wkn.get(lbl)
            if wkn:
                _add_to_portfolio(wkn, 0.0)
        if st.button("✅ Ausgewählte Titel ins Portfolio übernehmen", key="confirm_add", use_container_width=True):
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 4: MEIN PORTFOLIO
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📊 Ihr Portfolio")

    if st.session_state.get("builder_loaded_mp"):
        st.caption(f"📦 Basis: **{st.session_state.builder_loaded_mp}** (Stand: {st.session_state.get('builder_loaded_mp_date', '')})")

    portfolio = st.session_state.builder_portfolio
    n_titel = len(portfolio)

    if n_titel == 0:
        st.info("Noch keine Titel im Portfolio. Nutzen Sie die Suche, einen Schnellzugriff oder laden Sie ein Musterportfolio als Startpunkt.")
        _show_builder_disclaimer(zm_hint)
        return

    st.caption(f"**{n_titel} Titel** (max. {MAX_TITEL})")

    # Cash-Anteil & Buttons
    cash_col, eq_col, reset_col = st.columns([1, 1, 1])
    with cash_col:
        cash_pct_input = st.number_input(
            "💰 Cash-Anteil (%)", min_value=0.0, max_value=50.0,
            value=float(st.session_state.get("builder_cash_pct", CASH_PCT * 100)),
            step=1.0, key="builder_cash_pct",
            help="Gewünschter Cash-Anteil. Beim Gleichverteilen wird der Rest gleichmäßig auf alle Titel aufgeteilt."
        )
    with eq_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(f"⚖️ Gewichte gleichverteilen", key="equalize", use_container_width=True):
            cash_dec = cash_pct_input / 100.0
            w = (1.0 - cash_dec) / n_titel
            for wkn in portfolio:
                portfolio[wkn] = w
            st.rerun()
    with reset_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Alles zurücksetzen", key="reset_pf", use_container_width=True):
            _reset_portfolio()
            st.rerun()

    st.caption("ℹ️ Die Differenz zu 100% wird automatisch als Cash-Position (Liquidität) ausgewiesen. "
               "Passen Sie einzelne Gewichte frei an – der Cash-Anteil ergibt sich als Residual.")

    # Portfolio-Tabelle mit Gewichten und ❌-Button pro Zeile
    pf_rows = []
    for wkn, weight in portfolio.items():
        match = universe[universe["WKN"] == wkn]
        if match.empty:
            continue
        row = match.iloc[0]
        assetklasse = str(row["Assetklasse"]) if "Assetklasse" in row.index and pd.notna(row["Assetklasse"]) else ""
        is_bond = "rente" in assetklasse.lower() or "anleihe" in assetklasse.lower()

        entry = {
            "Name": str(row["Name"]) if "Name" in row.index and pd.notna(row["Name"]) else "",
            "WKN": wkn,
            "Assetklasse": assetklasse,
            "Gewicht (%)": round(weight * 100, 2),
        }

        # Kupon, Duration, Fälligkeit für alle Titel (bei Aktien bleiben sie leer)
        kupon = float(row["Kupon_num"]) if "Kupon_num" in row.index and pd.notna(row["Kupon_num"]) else None
        dur = float(row["Duration_num"]) if "Duration_num" in row.index and pd.notna(row["Duration_num"]) else None
        faell = row["Fälligkeit_parsed"] if "Fälligkeit_parsed" in row.index and pd.notna(row["Fälligkeit_parsed"]) else None

        entry["Kupon"] = fmt_pct_de(kupon) if kupon is not None else "–"
        entry["Duration"] = f"{dur:.2f}".replace(".", ",") if dur is not None else "–"
        entry["Fälligkeit"] = fmt_date_de(faell) if faell is not None else "–"

        pf_rows.append(entry)

    if not pf_rows:
        st.warning("Keine gültigen Titel gefunden.")
        _show_builder_disclaimer(zm_hint)
        return

    pf_df = pd.DataFrame(pf_rows)

    # Editierbarer Gewicht-Editor mit Entfernen-Spalte
    pf_df.insert(0, "🗑️", False)

    edited_pf = st.data_editor(
        pf_df,
        column_config={
            "🗑️": st.column_config.CheckboxColumn("🗑️", help="Anhaken zum Entfernen", default=False),
            "Gewicht (%)": st.column_config.NumberColumn("Gewicht (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f"),
        },
        disabled=["Name", "WKN", "Assetklasse", "Kupon", "Duration", "Fälligkeit"],
        hide_index=True, use_container_width=True, key="builder_pf_editor"
    )

    # Gewichte zurückschreiben + angehakte Titel entfernen
    titles_to_remove = []
    if edited_pf is not None:
        for _, row in edited_pf.iterrows():
            wkn = row["WKN"]
            if row["🗑️"]:
                titles_to_remove.append(wkn)
            elif wkn in st.session_state.builder_portfolio:
                st.session_state.builder_portfolio[wkn] = row["Gewicht (%)"] / 100.0

    if titles_to_remove:
        for wkn in titles_to_remove:
            _remove_from_portfolio(wkn)
        st.rerun()

    # Summen
    total_weight = sum(st.session_state.builder_portfolio.values())
    cash_weight = max(0.0, 1.0 - total_weight)

    s1, s2, s3 = st.columns(3)
    with s1: st.metric("Investiert", fmt_pct_de(total_weight))
    with s2: st.metric("💰 Cash (Residual)", fmt_pct_de(cash_weight))
    with s3:
        ok = abs(total_weight + cash_weight - 1.0) < 0.001
        st.metric("Summe", f"{'🟢' if ok else '🔴'} {fmt_pct_de(total_weight + cash_weight)}")

    if total_weight > 1.0:
        st.error(f"⛔ Die Summe der Gewichte übersteigt 100%. Bitte einzelne Positionen reduzieren.")

    # Excel Export
    st.markdown("---")
    if st.button("⬇️ Portfolio als Excel speichern", key="csv_export", use_container_width=True):
        exp = edited_pf.copy() if edited_pf is not None else pf_df.copy()

        # 🗑️-Spalte entfernen
        if "🗑️" in exp.columns:
            exp = exp.drop(columns=["🗑️"])

        # "–" durch leere Strings ersetzen für saubere Excel-Ausgabe
        exp = exp.replace("–", "")

        # Cash-Zeile
        cash_row_data = {"Name": "Liquidität", "WKN": "", "Assetklasse": "Cash", "Gewicht (%)": round(cash_weight * 100, 2)}
        for col in exp.columns:
            if col not in cash_row_data:
                cash_row_data[col] = ""
        exp = pd.concat([exp, pd.DataFrame([cash_row_data])], ignore_index=True)

        # Als Excel schreiben
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
            exp.to_excel(writer, index=False, sheet_name="Portfolio")
        excel_buf.seek(0)

        st.download_button(
            "⬇️ Excel herunterladen",
            excel_buf.getvalue(),
            f"Portfolio_{dt.date.today().strftime('%Y%m%d')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="xlsx_dl"
        )

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 5: STRUKTURANALYSE
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📊 Portfoliostruktur")

    analysis_df = build_builder_analysis_df(st.session_state.builder_portfolio, universe)
    if analysis_df.empty:
        st.info("Bitte erst Gewichte vergeben – nutzen Sie 'Gewichte gleichverteilen' oder passen Sie die Gewichte manuell an.")
        _show_builder_disclaimer(zm_hint)
        return

    w_dur = calc_weighted_duration(analysis_df)
    w_kup = calc_weighted_kupon(analysis_df)

    n_kc = 4 if use_volume else 3
    kc = st.columns(n_kc)
    with kc[0]: st.metric("Anzahl Titel", n_titel)
    with kc[1]: st.metric("Investitionsgrad", fmt_pct_de(total_weight))
    with kc[2]: st.metric("Liquidität", fmt_pct_de(cash_weight))
    if use_volume:
        with kc[3]: st.metric("Investiert (€)", fmt_eur_de(total_weight * anlagevolumen))

    # Anleihen-Detail
    has_bonds = analysis_df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False).any()
    if has_bonds:
        st.markdown("**🏦 Anleihen-Detail**")
        bond_rows = analysis_df[analysis_df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)]
        nc = 2 + (1 if w_dur else 0) + (1 if w_kup else 0)
        bc = st.columns(max(nc, 2))
        ci = 0
        with bc[ci]: st.metric("Anzahl Anleihen", len(bond_rows)); ci += 1
        with bc[ci]: st.metric("Gewicht Anleihen", fmt_pct_de(bond_rows["Gewicht"].sum())); ci += 1
        if w_dur:
            with bc[min(ci,len(bc)-1)]:
                st.metric("⌀ Duration (gewichtet)", f"{w_dur:.2f}".replace(".",","),
                    help="Gewichtete durchschnittliche Duration aller Anleihen im Portfolio. "
                         "Berechnung: Summe(Gewicht × Duration) / Summe(Gewichte der Anleihen). "
                         "Die Duration misst die Zinssensitivität – sie gibt an, um wie viel Prozent "
                         "der Portfoliowert fällt, wenn das Zinsniveau um 1 Prozentpunkt steigt.")
                ci += 1
        if w_kup:
            with bc[min(ci,len(bc)-1)]:
                st.metric("⌀ Kupon (gewichtet)", fmt_pct_de(w_kup),
                    help="Gewichteter Durchschnittskupon aller Anleihen im Portfolio.")

        # Fälligkeitsstruktur
        if "Fälligkeit_parsed" in bond_rows.columns and bond_rows["Fälligkeit_parsed"].notna().any():
            faell = bond_rows[bond_rows["Fälligkeit_parsed"].notna()].copy()
            faell["Jahr"] = faell["Fälligkeit_parsed"].dt.year
            faell_agg = faell.groupby("Jahr")["Gewicht"].sum().reset_index()
            faell_agg.columns = ["Jahr", "Gewicht"]
            if not faell_agg.empty:
                st.markdown("**Fälligkeitsstruktur**")
                fig_f = go.Figure(data=[go.Bar(
                    x=faell_agg["Jahr"].astype(str),
                    y=faell_agg["Gewicht"],
                    marker_color=FFPB_GOLD,
                    text=[fmt_pct_de(v) for v in faell_agg["Gewicht"]],
                    textposition="outside",
                )])
                fig_f.update_layout(
                    height=300, xaxis_title="Fälligkeitsjahr", yaxis_title="Gewicht",
                    yaxis=dict(tickformat=".1%"), margin=dict(t=30, b=40, l=50, r=20))
                st.plotly_chart(fig_f, use_container_width=True)

    # Ring-Diagramme
    st.markdown("---")
    r1, r2, r3 = st.columns(3)
    with r1:
        ag = build_allocation(analysis_df, "Gattung")
        if not ag.empty: st.plotly_chart(build_ring_chart(ag, "Gattung", "Gattung"), use_container_width=True)
    with r2:
        ar = build_allocation(analysis_df, "Region")
        if not ar.empty: st.plotly_chart(build_ring_chart(ar, "Region", "Region"), use_container_width=True)
    with r3:
        aseg = build_allocation(analysis_df, "Segment")
        if not aseg.empty: st.plotly_chart(build_ring_chart(aseg, "Segment", "Segment"), use_container_width=True)

    # Top 5
    st.markdown("---")
    top5 = get_top_holdings(analysis_df, n=5)
    if not top5.empty:
        st.plotly_chart(build_top5_bar_chart(top5, "Top 5 Holdings"), use_container_width=True)

    # Gruppierte Tabelle
    st.markdown("**Einzeltitel-Übersicht**")
    grouped = build_grouped_title_table(analysis_df, anlagevolumen if use_volume else 0.0, show_ytd=False)
    for gname, gw, disp in grouped:
        st.markdown(f"**{'💰' if gname.startswith('💰') else '📋'} {gname}** – {fmt_pct_de(gw)}")
        st.dataframe(disp, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 6: VERGLEICH MIT MUSTERPORTFOLIO
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 🔄 Ihr Portfolio im Vergleich")
    if pf_data:
        vgl_names = ["-- Kein Vergleich --"] + filtered_mp[col_display_nm].tolist()
        vgl_sel = st.selectbox("Vergleich mit Musterportfolio", vgl_names, key="builder_vgl")
        if vgl_sel != "-- Kein Vergleich --":
            vgl_csv = mp_to_csv.get(vgl_sel)
            if vgl_csv and vgl_csv in pf_data:
                vgl_df = pf_data[vgl_csv]
                st.markdown(f"**{vgl_sel}**")
                vl = max(0, 1.0 - vgl_df["Gewicht"].sum())
                vc = st.columns(3)
                with vc[0]: st.metric("Titel", len(vgl_df))
                with vc[1]: st.metric("Investiert", fmt_pct_de(vgl_df["Gewicht"].sum()))
                with vc[2]: st.metric("Liquidität", fmt_pct_de(vl))
                vr1, vr2, vr3 = st.columns(3)
                with vr1:
                    vg = build_allocation(vgl_df, "Gattung")
                    if not vg.empty: st.plotly_chart(build_ring_chart(vg, "Gattung", f"Gattung – {vgl_sel}"), use_container_width=True)
                with vr2:
                    vr = build_allocation(vgl_df, "Region")
                    if not vr.empty: st.plotly_chart(build_ring_chart(vr, "Region", f"Region – {vgl_sel}"), use_container_width=True)
                with vr3:
                    vs = build_allocation(vgl_df, "Segment")
                    if not vs.empty: st.plotly_chart(build_ring_chart(vs, "Segment", f"Segment – {vgl_sel}"), use_container_width=True)
    else:
        st.info("Keine Musterportfolios verfügbar.")

    _show_builder_disclaimer(zm_hint)
