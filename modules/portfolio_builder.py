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
    build_allocation, build_ring_chart, get_bond_summary,
    build_grouped_title_table, build_top5_bar_chart, get_top_holdings,
    load_pf_csvs, build_pf_data, RING_COLORS,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_TITEL = 50
CASH_PCT = 0.05
TOP5_COLORS = ["#1B3A5C", "#6A9BC3", "#B8973A", "#C4B78C", "#A8CBE8"]

SCHNELLZUGRIFFE = {
    "Rein Aktien":       {"Assetklasse": ["Aktien"]},
    "Rein Renten":       {"Assetklasse": ["Renten"]},
    "Multi-Asset":       {"Assetklasse": ["Aktien", "Renten"]},
    "High Yield (Kupon >3%)": {"Assetklasse": ["Renten"], "kupon_min": 0.03},
    "Kurze Duration (<3J)":   {"Assetklasse": ["Renten"], "duration_max": 3.0},
    "Lange Duration (>5J)":   {"Assetklasse": ["Renten"], "duration_min": 5.0},
    "Europa-Fokus":      {"Region": ["Deutschland", "Europa ohne Deutschland"]},
    "Nordamerika-Fokus": {"Region": ["Nordamerika"]},
    "Niedriges Risiko (≤3)":  {"mrw_max": 3},
}


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def load_zieldaten(folder):
    all_files = glob.glob(os.path.join(folder, "*.CSV")) + glob.glob(os.path.join(folder, "*.csv"))
    if not all_files:
        return pd.DataFrame()

    tag_pattern = re.compile(r"_(\d{6})_(\d{4})")
    def _sort_key(f):
        m = tag_pattern.search(os.path.basename(f))
        return m.group(1) + m.group(2) if m else "000000_0000"
    all_files.sort(key=_sort_key, reverse=True)

    df = pd.read_csv(all_files[0], comment="#", encoding="ISO-8859-1",
                     delimiter=";", decimal=",", thousands=".", dtype=str)

    # Alle String-Spalten bereinigen
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
            # "nan" Strings zu echtem NaN
            df[col] = df[col].replace("nan", np.nan)

    # Numerische Spalten parsen
    if "Kupon" in df.columns:
        df["Kupon_num"] = df["Kupon"].astype(str).str.replace("%", "").str.replace(",", ".").str.strip()
        df["Kupon_num"] = pd.to_numeric(df["Kupon_num"], errors="coerce") / 100.0
    else:
        df["Kupon_num"] = np.nan

    if "Duration" in df.columns:
        df["Duration_num"] = pd.to_numeric(df["Duration"].astype(str).str.replace(",", "."), errors="coerce")
    else:
        df["Duration_num"] = np.nan

    if "Marktrisikowert" in df.columns:
        df["MRW_num"] = pd.to_numeric(df["Marktrisikowert"], errors="coerce")
    else:
        df["MRW_num"] = np.nan

    if "Fälligkeit" in df.columns:
        df["Fälligkeit_parsed"] = pd.to_datetime(df["Fälligkeit"], format="%d.%m.%Y", errors="coerce")

    return df


def _init_session_state():
    if "builder_portfolio" not in st.session_state:
        st.session_state.builder_portfolio = {}  # {WKN: gewicht_dezimal}

def _reset_portfolio():
    st.session_state.builder_portfolio = {}
    st.session_state.pop("builder_loaded_mp", None)
    st.session_state.pop("builder_loaded_mp_date", None)
    if "builder_multiselect" in st.session_state:
        del st.session_state["builder_multiselect"]


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------
def apply_filters(df, filters):
    result = df.copy()
    if filters.get("Assetklasse"):
        result = result[result["Assetklasse"].isin(filters["Assetklasse"])]
    if filters.get("Region"):
        result = result[result["Region"].isin(filters["Region"])]
    if filters.get("Segment"):
        result = result[result["Segment"].isin(filters["Segment"])]
    if filters.get("Masterlistenzuordnung"):
        result = result[result["Masterlistenzuordnung"].isin(filters["Masterlistenzuordnung"])]
    if filters.get("kupon_min") is not None:
        result = result[result["Kupon_num"] >= filters["kupon_min"]]
    if filters.get("duration_min") is not None:
        result = result[result["Duration_num"] >= filters["duration_min"]]
    if filters.get("duration_max") is not None:
        result = result[result["Duration_num"] <= filters["duration_max"]]
    if filters.get("mrw_max") is not None:
        result = result[result["MRW_num"] <= filters["mrw_max"]]
    return result


# ---------------------------------------------------------------------------
# Analyse-DataFrame bauen
# ---------------------------------------------------------------------------
def build_builder_analysis_df(selected_wkns, universe):
    rows = []
    for wkn, weight in selected_wkns.items():
        match = universe[universe["WKN"] == wkn]
        if match.empty:
            continue
        row = match.iloc[0]
        entry = {
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
        }
        rows.append(entry)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def calc_weighted_duration(df):
    bonds = df[df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty or bonds["Duration_num"].isna().all():
        return None
    w = bonds["Gewicht"].fillna(0); d = bonds["Duration_num"].fillna(0)
    return float((w * d).sum() / w.sum()) if w.sum() > 0 else None


def calc_weighted_kupon(df):
    bonds = df[df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty or bonds["Kupon"].isna().all():
        return None
    w = bonds["Gewicht"].fillna(0); k = bonds["Kupon"].fillna(0)
    return float((w * k).sum() / w.sum()) if w.sum() > 0 else None


# ---------------------------------------------------------------------------
# WKN-Matching Helper
# ---------------------------------------------------------------------------
def _normalize_wkn(val):
    """Normalisiert WKN: Strip, Uppercase, None-safe."""
    if val is None or pd.isna(val):
        return ""
    return str(val).strip().upper()


def _build_wkn_lookup(universe):
    """Baut ein Lookup {normalisierte_WKN: original_WKN} aus dem Universum."""
    lookup = {}
    if "WKN" in universe.columns:
        for _, row in universe.iterrows():
            orig = str(row["WKN"]).strip()
            normed = orig.upper()
            if normed and normed != "NAN":
                lookup[normed] = orig
    return lookup


# ---------------------------------------------------------------------------
# Streamlit Rendering
# ---------------------------------------------------------------------------
def render_portfolio_builder(name_mapping, anlagevolumen=0.0):
    _init_session_state()
    use_volume = anlagevolumen > 0

    st.caption("⚠️ Das Portfolio wird nur in der aktuellen Sitzung gespeichert. Bei Logout geht es verloren. Bitte vorher als CSV exportieren.")

    # ── Daten laden ──
    universe = load_zieldaten(ZIELDATEN_FOLDER)
    if universe.empty:
        st.warning(f"Keine Zieldaten in {ZIELDATEN_FOLDER}/ gefunden.")
        return

    # WKN-Lookup für robustes Matching
    wkn_lookup = _build_wkn_lookup(universe)

    st.success(f"📂 Anlageuniversum: **{len(universe)} Titel** geladen")

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 1: SCHNELLZUGRIFFE & MUSTERPORTFOLIO (zuerst, damit Portfolio geladen wird)
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("### ⚡ Schnellzugriffe & Vorlagen")

    sz_cols = st.columns(5)
    sz_names = list(SCHNELLZUGRIFFE.keys())
    for i, name in enumerate(sz_names):
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

    # Musterportfolio
    auto_tag_pf = detect_newest_date_tag(DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS)
    pf_files = load_pf_csvs(DATA_FOLDER_PF, auto_tag_pf)
    pf_data = build_pf_data(pf_files) if pf_files else {}

    col_display = name_mapping.columns[0]
    col_csv_key = name_mapping.columns[1]
    available_mp = set(pf_data.keys())
    filtered_mp = name_mapping[name_mapping[col_csv_key].isin(available_mp)]
    mp_names = ["-- Kein Musterportfolio --"] + filtered_mp[col_display].tolist()
    mp_to_csv = dict(zip(filtered_mp[col_display], filtered_mp[col_csv_key]))

    mp_sel = st.selectbox("📦 Musterportfolio als Startpunkt laden", mp_names, key="builder_mp")
    if st.button("📥 Musterportfolio laden", key="load_mp"):
        if mp_sel != "-- Kein Musterportfolio --":
            csv_name = mp_to_csv.get(mp_sel)
            if csv_name and csv_name in pf_data:
                mp_df = pf_data[csv_name]
                new_portfolio = {}
                not_found = []

                for _, row in mp_df.iterrows():
                    titel_name = str(row["Wertpapier"]).strip() if "Wertpapier" in mp_df.columns else "?"
                    gewicht = float(row["Gewicht"]) if "Gewicht" in mp_df.columns and pd.notna(row["Gewicht"]) else 0.0

                    matched_wkn = None
                    if "WKN" in mp_df.columns:
                        wkn_raw = _normalize_wkn(row["WKN"])
                        if wkn_raw in wkn_lookup:
                            matched_wkn = wkn_lookup[wkn_raw]
                    if matched_wkn is None and "Name" in universe.columns:
                        name_match = universe[universe["Name"].str.upper() == titel_name.upper()]
                        if not name_match.empty:
                            matched_wkn = str(name_match.iloc[0]["WKN"]).strip()

                    if matched_wkn:
                        new_portfolio[matched_wkn] = gewicht
                    else:
                        not_found.append(titel_name)

                st.session_state.builder_portfolio = new_portfolio
                # Multiselect-Key löschen damit er beim Rerun neu mit den richtigen Defaults rendert
                if "builder_multiselect" in st.session_state:
                    del st.session_state["builder_multiselect"]
                # Merken welches Musterportfolio geladen wurde
                st.session_state.builder_loaded_mp = mp_sel
                st.session_state.builder_loaded_mp_date = auto_tag_pf

                if new_portfolio:
                    st.success(f"✅ {len(new_portfolio)} von {len(mp_df)} Titeln aus **{mp_sel}** geladen")
                if not_found:
                    st.warning(f"⚠️ {len(not_found)} Titel nicht im Universum: {', '.join(not_found[:10])}")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 2: SUCHE (Multiselect über gesamtes Universum)
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 🔎 Titel suchen & hinzufügen")

    # Optionen bauen
    universe_sorted = universe.sort_values("Name")
    all_option_labels = (
        universe_sorted["Name"].fillna("") + "  (" +
        universe_sorted["WKN"].fillna("") + " | " +
        universe_sorted["ISIN"].fillna("") + ")"
    ).tolist()
    all_option_wkns = universe_sorted["WKN"].tolist()
    all_label_to_wkn = dict(zip(all_option_labels, all_option_wkns))
    all_wkn_to_label = dict(zip(all_option_wkns, all_option_labels))

    # Bereits im Portfolio → als Default im Multiselect
    current_wkns = set(st.session_state.builder_portfolio.keys())
    current_labels = [all_wkn_to_label[wkn] for wkn in current_wkns if wkn in all_wkn_to_label]

    selected_labels = st.multiselect(
        "Name, WKN oder ISIN eingeben – durchsucht das gesamte Universum",
        options=all_option_labels,
        default=current_labels,
        key="builder_multiselect",
        help=f"Maximal {MAX_TITEL} Titel. Tippen Sie um zu suchen."
    )

    # Auswahl-Änderungen verarbeiten – NUR neue hinzufügen / abgewählte entfernen
    # Bestehende Gewichte werden NICHT angetastet
    selected_wkns_new = {all_label_to_wkn[lbl] for lbl in selected_labels if lbl in all_label_to_wkn}
    visible_wkns = set(all_label_to_wkn.values())

    # Entfernen: nur was der User aktiv abgewählt hat
    for wkn in list(current_wkns):
        if wkn in visible_wkns and wkn not in selected_wkns_new:
            st.session_state.builder_portfolio.pop(wkn, None)

    # Hinzufügen: nur neue Titel, mit Gewicht 0.0 (bestehende Gewichte bleiben)
    for wkn in selected_wkns_new:
        if wkn not in st.session_state.builder_portfolio:
            if len(st.session_state.builder_portfolio) >= MAX_TITEL:
                st.error(f"⛔ Maximum von {MAX_TITEL} Titeln erreicht!")
                break
            st.session_state.builder_portfolio[wkn] = 0.0

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 3: FILTER (optional, zum Einschränken der Übersichtstabelle)
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 🔍 Universum filtern (optional)")

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        f_asset = st.multiselect("Assetklasse", sorted(universe["Assetklasse"].dropna().unique().tolist()), key="f_asset")
    with f_col2:
        f_region = st.multiselect("Region", sorted(universe["Region"].dropna().unique().tolist()), key="f_region")
    with f_col3:
        f_segment = st.multiselect("Segment", sorted(universe["Segment"].dropna().unique().tolist()), key="f_segment")
    with f_col4:
        f_ml = st.multiselect("Masterlistenzuordnung", sorted(universe["Masterlistenzuordnung"].dropna().unique().tolist()), key="f_ml")

    with st.expander("📐 Erweiterte Filter"):
        ef1, ef2, ef3, ef4 = st.columns(4)
        with ef1: f_kmin = st.number_input("Kupon min (%)", 0.0, 20.0, step=0.5, key="f_kmin")
        with ef2: f_dmin = st.number_input("Duration min (J)", 0.0, 30.0, step=0.5, key="f_dmin")
        with ef3: f_dmax = st.number_input("Duration max (J)", 0.0, 30.0, step=0.5, key="f_dmax")
        with ef4: f_mrw = st.number_input("Risiko max", 1, 7, step=1, key="f_mrw")

    filters = {}
    if f_asset: filters["Assetklasse"] = f_asset
    if f_region: filters["Region"] = f_region
    if f_segment: filters["Segment"] = f_segment
    if f_ml: filters["Masterlistenzuordnung"] = f_ml
    if f_kmin > 0: filters["kupon_min"] = f_kmin / 100.0
    if f_dmin > 0: filters["duration_min"] = f_dmin
    if f_dmax < 30: filters["duration_max"] = f_dmax
    if f_mrw < 7: filters["mrw_max"] = f_mrw

    filtered = apply_filters(universe, filters)

    with st.expander(f"📋 Gefilterte Titel anzeigen ({len(filtered)} von {len(universe)})"):
        show_cols = ["Name", "WKN", "ISIN", "Assetklasse", "Segment", "Region", "Kupon", "Duration", "Marktrisikowert"]
        avail = [c for c in show_cols if c in filtered.columns]
        st.dataframe(filtered[avail].head(200), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 4: MEIN PORTFOLIO
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📊 Mein Portfolio")

    # Hinweis welches Musterportfolio geladen wurde
    if st.session_state.get("builder_loaded_mp"):
        tag = st.session_state.get("builder_loaded_mp_date", "")
        st.caption(f"📦 Basis: **{st.session_state.builder_loaded_mp}** (Portfolioanalyse-Stand: {tag})")

    portfolio = st.session_state.builder_portfolio
    n_titel = len(portfolio)

    if n_titel == 0:
        st.info("Noch keine Titel ausgewählt. Nutzen Sie die Suche oben, einen Schnellzugriff oder laden Sie ein Musterportfolio.")
        return

    st.caption(f"**{n_titel} Titel** ausgewählt (max. {MAX_TITEL})")

    btn1, btn2, btn3 = st.columns(3)
    with btn1:
        if st.button("⚖️ Gleichgewichten", key="equalize", use_container_width=True):
            w = (1.0 - CASH_PCT) / n_titel
            for wkn in portfolio:
                portfolio[wkn] = w
            st.session_state.builder_portfolio = portfolio
            st.rerun()
    with btn2:
        if st.button("🔄 Portfolio zurücksetzen", key="reset_pf", use_container_width=True):
            _reset_portfolio()
            st.rerun()
    with btn3:
        pass

    # Gewicht-Editor
    pf_rows = []
    for wkn, weight in portfolio.items():
        match = universe[universe["WKN"] == wkn]
        if match.empty:
            continue
        row = match.iloc[0]
        pf_rows.append({
            "Name": str(row["Name"]) if "Name" in row.index and pd.notna(row["Name"]) else "",
            "WKN": wkn,
            "ISIN": str(row["ISIN"]) if "ISIN" in row.index and pd.notna(row["ISIN"]) else "",
            "Assetklasse": str(row["Assetklasse"]) if "Assetklasse" in row.index and pd.notna(row["Assetklasse"]) else "",
            "Gewicht (%)": round(weight * 100, 2),
        })

    if not pf_rows:
        st.warning("Keine gültigen Titel im Portfolio. Möglicherweise stimmen die WKNs nicht überein.")
        # Debug
        with st.expander("🔍 Debug: Portfolio-WKNs"):
            st.write("WKNs im Portfolio:", list(portfolio.keys())[:10])
            st.write("WKNs im Universum (Beispiel):", universe["WKN"].head(10).tolist())
        return

    pf_df = pd.DataFrame(pf_rows)

    edited_pf = st.data_editor(
        pf_df,
        column_config={
            "Gewicht (%)": st.column_config.NumberColumn("Gewicht (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f"),
        },
        disabled=["Name", "WKN", "ISIN", "Assetklasse"],
        hide_index=True, use_container_width=True, key="builder_pf_editor"
    )

    if edited_pf is not None:
        for _, row in edited_pf.iterrows():
            wkn = row["WKN"]
            if wkn in st.session_state.builder_portfolio:
                st.session_state.builder_portfolio[wkn] = row["Gewicht (%)"] / 100.0

    total_weight = sum(st.session_state.builder_portfolio.values())
    cash_weight = max(0.0, 1.0 - total_weight)

    sc1, sc2, sc3 = st.columns(3)
    with sc1: st.metric("Investiert", fmt_pct_de(total_weight))
    with sc2: st.metric("💰 Liquidität", fmt_pct_de(cash_weight))
    with sc3:
        ok = abs(total_weight + cash_weight - 1.0) < 0.001
        st.metric("Summe", f"{'🟢' if ok else '🔴'} {fmt_pct_de(total_weight + cash_weight)}")

    if total_weight > (1.0 - CASH_PCT + 0.001):
        st.warning(f"⚠️ Investitionsgrad übersteigt {fmt_pct_de(1.0 - CASH_PCT)}. Cash-Minimum: {fmt_pct_de(CASH_PCT)}.")

    # CSV Export
    st.markdown("---")
    if st.button("⬇️ Portfolio als CSV exportieren", key="csv_export", use_container_width=True):
        exp = edited_pf.copy() if edited_pf is not None else pf_df.copy()
        cash_row = pd.DataFrame([{"Name": "Liquidität", "WKN": "", "ISIN": "", "Assetklasse": "Cash", "Gewicht (%)": round(cash_weight * 100, 2)}])
        exp = pd.concat([exp, cash_row], ignore_index=True)
        st.download_button("⬇️ CSV herunterladen", exp.to_csv(index=False, sep=";", decimal=","),
            f"Portfolio_Builder_{dt.date.today().strftime('%Y%m%d')}.csv", "text/csv", key="csv_dl")

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 5: STRUKTURANALYSE
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📊 Strukturanalyse")

    analysis_df = build_builder_analysis_df(st.session_state.builder_portfolio, universe)
    if analysis_df.empty:
        st.info("Bitte erst Gewichte vergeben (Gleichgewichten).")
        return

    w_duration = calc_weighted_duration(analysis_df)
    w_kupon = calc_weighted_kupon(analysis_df)

    kc = st.columns(5 if use_volume else 4)
    with kc[0]: st.metric("Anzahl Titel", n_titel)
    with kc[1]: st.metric("Investitionsgrad", fmt_pct_de(total_weight), help="In Wertpapiere investiert.")
    with kc[2]: st.metric("Liquidität", fmt_pct_de(cash_weight), help="Nicht investierter Anteil.")
    with kc[3]:
        if w_duration is not None:
            st.metric("⌀ Duration (gew.)", f"{w_duration:.2f}".replace(".", ","), help="Gewichtete Duration aller Anleihen.")
        elif w_kupon is not None:
            st.metric("⌀ Kupon (gew.)", fmt_pct_de(w_kupon), help="Gewichteter Durchschnittskupon.")
        else:
            avg_mrw = analysis_df["Marktrisikowert"].mean()
            st.metric("Ø Risiko", f"{avg_mrw:.1f}".replace(".", ",") if pd.notna(avg_mrw) else "–", help="Durchschnittlicher Marktrisikowert.")
    if use_volume:
        with kc[4]: st.metric("Investiert (€)", fmt_eur_de(total_weight * anlagevolumen))

    # Anleihen-Detail
    has_bonds = analysis_df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False).any()
    if has_bonds:
        st.markdown("---")
        st.markdown("**🏦 Anleihen-Detail**")
        bond_rows = analysis_df[analysis_df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)]
        n_bc = 2 + (1 if w_duration is not None else 0) + (1 if w_kupon is not None else 0)
        bc = st.columns(max(n_bc, 2))
        ci = 0
        with bc[ci]: st.metric("Anzahl Anleihen", len(bond_rows)); ci += 1
        with bc[ci]: st.metric("Gewicht Anleihen", fmt_pct_de(bond_rows["Gewicht"].sum())); ci += 1
        if w_duration is not None:
            with bc[min(ci, len(bc)-1)]: st.metric("⌀ Duration (gew.)", f"{w_duration:.2f}".replace(".", ","), help="Gewichtete Duration. Zinssensitivität."); ci += 1
        if w_kupon is not None:
            with bc[min(ci, len(bc)-1)]: st.metric("⌀ Kupon (gew.)", fmt_pct_de(w_kupon), help="Gewichteter Durchschnittskupon.")

    # Ring-Diagramme
    st.markdown("---")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        ag = build_allocation(analysis_df, "Gattung")
        if not ag.empty: st.plotly_chart(build_ring_chart(ag, "Gattung", "Allokation nach Gattung"), use_container_width=True)
    with rc2:
        ar = build_allocation(analysis_df, "Region")
        if not ar.empty: st.plotly_chart(build_ring_chart(ar, "Region", "Allokation nach Region"), use_container_width=True)
    with rc3:
        aseg = build_allocation(analysis_df, "Segment")
        if not aseg.empty: st.plotly_chart(build_ring_chart(aseg, "Segment", "Allokation nach Segment"), use_container_width=True)

    # Top 5
    st.markdown("---")
    top5 = get_top_holdings(analysis_df, n=5)
    if not top5.empty:
        st.plotly_chart(build_top5_bar_chart(top5, "Top 5 Holdings (nach Gewicht)"), use_container_width=True)

    # Gruppierte Tabelle
    st.markdown("**Einzeltitel-Übersicht**")
    grouped = build_grouped_title_table(analysis_df, anlagevolumen if use_volume else 0.0, show_ytd=False)
    for gname, gw, disp in grouped:
        if gname.startswith("💰"):
            st.markdown(f"**{gname}** ({fmt_pct_de(gw)})")
        else:
            st.markdown(f"**📋 {gname}** – {fmt_pct_de(gw)}")
        st.dataframe(disp, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════
    # BEREICH 6: VERGLEICH MIT MUSTERPORTFOLIO
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 🔄 Vergleich mit Musterportfolio")
    if pf_data:
        vgl_names = ["-- Kein Vergleich --"] + filtered_mp[col_display].tolist()
        vgl_sel = st.selectbox("Musterportfolio zum Vergleich", vgl_names, key="builder_vgl")

        if vgl_sel != "-- Kein Vergleich --":
            vgl_csv = mp_to_csv.get(vgl_sel)
            if vgl_csv and vgl_csv in pf_data:
                vgl_df = pf_data[vgl_csv]
                st.markdown(f"**{vgl_sel}**")
                vgl_liq = max(0, 1.0 - vgl_df["Gewicht"].sum())
                vc = st.columns(3)
                with vc[0]: st.metric("Anzahl Titel", len(vgl_df))
                with vc[1]: st.metric("Investitionsgrad", fmt_pct_de(vgl_df["Gewicht"].sum()))
                with vc[2]: st.metric("Liquidität", fmt_pct_de(vgl_liq))

                vrc1, vrc2, vrc3 = st.columns(3)
                with vrc1:
                    vag = build_allocation(vgl_df, "Gattung")
                    if not vag.empty: st.plotly_chart(build_ring_chart(vag, "Gattung", f"Gattung – {vgl_sel}"), use_container_width=True)
                with vrc2:
                    var = build_allocation(vgl_df, "Region")
                    if not var.empty: st.plotly_chart(build_ring_chart(var, "Region", f"Region – {vgl_sel}"), use_container_width=True)
                with vrc3:
                    vas = build_allocation(vgl_df, "Segment")
                    if not vas.empty: st.plotly_chart(build_ring_chart(vas, "Segment", f"Segment – {vgl_sel}"), use_container_width=True)
    else:
        st.info("Keine Musterportfolios verfügbar.")
