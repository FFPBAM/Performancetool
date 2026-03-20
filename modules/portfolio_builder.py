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
CASH_PCT = 0.05  # 5% Cash fix
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
def load_zieldaten(folder: str) -> pd.DataFrame:
    """Lädt die neueste Zieldaten-CSV."""
    all_files = glob.glob(os.path.join(folder, "*.CSV")) + glob.glob(os.path.join(folder, "*.csv"))
    if not all_files:
        return pd.DataFrame()

    # Neueste nach Zeitstempel im Namen
    tag_pattern = re.compile(r"_(\d{6})_(\d{4})")
    def _sort_key(f):
        m = tag_pattern.search(os.path.basename(f))
        return m.group(1) + m.group(2) if m else "000000_0000"
    all_files.sort(key=_sort_key, reverse=True)

    df = pd.read_csv(all_files[0], comment="#", encoding="ISO-8859-1",
                     delimiter=";", decimal=",", thousands=".", dtype=str)

    # Parsen
    if "Kupon" in df.columns:
        df["Kupon_num"] = df["Kupon"].astype(str).str.replace("%", "").str.replace(",", ".").str.strip()
        df["Kupon_num"] = pd.to_numeric(df["Kupon_num"], errors="coerce") / 100.0
    else:
        df["Kupon_num"] = np.nan

    if "Duration" in df.columns:
        df["Duration_num"] = pd.to_numeric(
            df["Duration"].astype(str).str.replace(",", "."), errors="coerce"
        )
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
    """Initialisiert Session-State für den Builder."""
    if "builder_portfolio" not in st.session_state:
        st.session_state.builder_portfolio = {}  # {ISIN: gewicht_dezimal}
    if "builder_initialized" not in st.session_state:
        st.session_state.builder_initialized = True


def _reset_portfolio():
    st.session_state.builder_portfolio = {}


# ---------------------------------------------------------------------------
# Filter-Logik
# ---------------------------------------------------------------------------
def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Wendet Filter auf das Universum an."""
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
    if filters.get("kupon_max") is not None:
        result = result[result["Kupon_num"] <= filters["kupon_max"]]
    if filters.get("duration_min") is not None:
        result = result[result["Duration_num"] >= filters["duration_min"]]
    if filters.get("duration_max") is not None:
        result = result[result["Duration_num"] <= filters["duration_max"]]
    if filters.get("mrw_max") is not None:
        result = result[result["MRW_num"] <= filters["mrw_max"]]

    return result


# ---------------------------------------------------------------------------
# Portfolio-Analyse (Strukturanalyse)
# ---------------------------------------------------------------------------
def build_builder_analysis_df(selected_isins: dict, universe: pd.DataFrame) -> pd.DataFrame:
    """
    Baut einen DataFrame für die Analyse, ähnlich dem Format aus der Portfolioanalyse.
    selected_isins: {ISIN: gewicht_dezimal}
    """
    rows = []
    for isin, weight in selected_isins.items():
        match = universe[universe["ISIN"] == isin]
        if match.empty:
            continue
        row = match.iloc[0]
        entry = {
            "Wertpapier": str(row["Name"]) if "Name" in row.index and pd.notna(row["Name"]) else "",
            "WKN": str(row["WKN"]) if "WKN" in row.index and pd.notna(row["WKN"]) else "",
            "ISIN": isin,
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


def calc_weighted_duration(df: pd.DataFrame):
    """Gewichtete Duration des Portfolios (nur Anleihen). Returns float or None."""
    bonds = df[df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty or bonds["Duration_num"].isna().all():
        return None
    w = bonds["Gewicht"].fillna(0)
    d = bonds["Duration_num"].fillna(0)
    if w.sum() == 0:
        return None
    return float((w * d).sum() / w.sum())


def calc_weighted_kupon(df: pd.DataFrame):
    """Gewichteter Durchschnittskupon (nur Anleihen). Returns float or None."""
    bonds = df[df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)].copy()
    if bonds.empty or bonds["Kupon"].isna().all():
        return None
    w = bonds["Gewicht"].fillna(0)
    k = bonds["Kupon"].fillna(0)
    if w.sum() == 0:
        return None
    return float((w * k).sum() / w.sum())


# ---------------------------------------------------------------------------
# Streamlit Rendering
# ---------------------------------------------------------------------------
def render_portfolio_builder(name_mapping: pd.DataFrame, anlagevolumen: float = 0.0):
    """Hauptfunktion: Rendert den Portfolio-Builder Tab."""
    _init_session_state()
    use_volume = anlagevolumen > 0

    # Hinweis
    st.caption("⚠️ Das zusammengestellte Portfolio wird nur in der aktuellen Sitzung gespeichert. Bei Logout oder Seitenwechsel geht es verloren.")

    # ── Daten laden ──
    universe = load_zieldaten(ZIELDATEN_FOLDER)
    if universe.empty:
        st.warning(f"Keine Zieldaten in {ZIELDATEN_FOLDER}/ gefunden.")
        return

    st.success(f"📂 Anlageuniversum: {len(universe)} Titel geladen")

    # ── Schnellzugriffe ──
    st.markdown("### ⚡ Schnellzugriffe")
    sz_cols = st.columns(5)
    sz_names = list(SCHNELLZUGRIFFE.keys())
    for i, name in enumerate(sz_names):
        with sz_cols[i % 5]:
            if st.button(name, key=f"sz_{i}", use_container_width=True):
                preset = SCHNELLZUGRIFFE[name]
                # Filter-Werte in Session-State schreiben
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
    st.markdown("---")
    mp_col1, mp_col2 = st.columns([2, 1])
    with mp_col1:
        # Musterportfolios aus Daten_PF laden
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

    with mp_col2:
        if st.button("📥 Musterportfolio laden", key="load_mp") and mp_sel != "-- Kein Musterportfolio --":
            csv_name = mp_to_csv.get(mp_sel)
            if csv_name and csv_name in pf_data:
                mp_df = pf_data[csv_name]
                new_portfolio = {}
                for _, row in mp_df.iterrows():
                    if "WKN" in mp_df.columns and "WKN" in universe.columns:
                        wkn = str(row.get("WKN", "")).strip()
                        match = universe[universe["WKN"] == wkn]
                        if not match.empty:
                            isin = match.iloc[0]["ISIN"]
                            new_portfolio[isin] = float(row["Gewicht"]) if pd.notna(row.get("Gewicht")) else 0.0
                st.session_state.builder_portfolio = new_portfolio
                st.success(f"✅ {len(new_portfolio)} Titel aus {mp_sel} geladen")
                st.rerun()

    # ── Filter ──
    st.markdown("### 🔍 Titel filtern & auswählen")

    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        all_asset = sorted(universe["Assetklasse"].dropna().unique().tolist())
        f_asset = st.multiselect("Assetklasse", all_asset, key="f_asset")

    with f_col2:
        all_region = sorted(universe["Region"].dropna().unique().tolist())
        f_region = st.multiselect("Region", all_region, key="f_region")

    with f_col3:
        all_segment = sorted(universe["Segment"].dropna().unique().tolist())
        f_segment = st.multiselect("Segment", all_segment, key="f_segment")

    # Erweiterte Filter
    with st.expander("📐 Erweiterte Filter"):
        ef_col1, ef_col2, ef_col3, ef_col4 = st.columns(4)
        with ef_col1:
            f_kupon_min = st.number_input("Kupon min (%)", 0.0, 20.0, step=0.5, key="f_kmin")
        with ef_col2:
            f_dur_min = st.number_input("Duration min (Jahre)", 0.0, 30.0, step=0.5, key="f_dmin")
        with ef_col3:
            f_dur_max = st.number_input("Duration max (Jahre)", 0.0, 30.0, step=0.5, key="f_dmax")
        with ef_col4:
            f_mrw_max = st.number_input("Marktrisikowert max", 1, 7, step=1, key="f_mrw")
            all_ml = sorted(universe["Masterlistenzuordnung"].dropna().unique().tolist())
            f_ml = st.multiselect("Masterlistenzuordnung", all_ml, key="f_ml")

    # Filter zusammenbauen
    filters = {}
    if f_asset: filters["Assetklasse"] = f_asset
    if f_region: filters["Region"] = f_region
    if f_segment: filters["Segment"] = f_segment
    if f_ml: filters["Masterlistenzuordnung"] = f_ml
    if f_kupon_min > 0: filters["kupon_min"] = f_kupon_min / 100.0
    if f_dur_min > 0: filters["duration_min"] = f_dur_min
    if f_dur_max < 30: filters["duration_max"] = f_dur_max
    if f_mrw_max < 7: filters["mrw_max"] = f_mrw_max

    filtered = apply_filters(universe, filters)
    st.caption(f"📋 {len(filtered)} Titel nach Filterung")

    # ── Titel hinzufügen via Multiselect (schnell) ──
    # Optionen für Multiselect: "Name (WKN | ISIN)" → ISIN als Wert
    filtered_sorted = filtered.sort_values("Name")
    option_labels = (
        filtered_sorted["Name"] + "  (" + filtered_sorted["WKN"].fillna("") + " | " + filtered_sorted["ISIN"].fillna("") + ")"
    ).tolist()
    option_isins = filtered_sorted["ISIN"].tolist()
    label_to_isin = dict(zip(option_labels, option_isins))

    # Bereits ausgewählte als Default
    current_isins = set(st.session_state.builder_portfolio.keys())
    current_labels = [lbl for lbl, isin in label_to_isin.items() if isin in current_isins]

    selected_labels = st.multiselect(
        "🔎 Titel suchen & hinzufügen (Name, WKN oder ISIN tippen)",
        options=option_labels,
        default=current_labels,
        key="builder_multiselect",
        help=f"Maximal {MAX_TITEL} Titel. Tippen Sie um zu suchen."
    )

    # Auswahl verarbeiten
    selected_isins_new = {label_to_isin[lbl] for lbl in selected_labels if lbl in label_to_isin}

    # Entfernte Titel
    for isin in current_isins - selected_isins_new:
        st.session_state.builder_portfolio.pop(isin, None)
    # Neue Titel
    for isin in selected_isins_new - current_isins:
        if len(st.session_state.builder_portfolio) >= MAX_TITEL:
            st.error(f"⛔ Maximum von {MAX_TITEL} Titeln erreicht!")
            break
        st.session_state.builder_portfolio[isin] = 0.0

    # ── Gefilterte Tabelle (read-only, zur Übersicht) ──
    with st.expander(f"📋 Gefilterte Titel anzeigen ({len(filtered)})"):
        display_cols = ["Name", "WKN", "ISIN", "Assetklasse", "Segment", "Region",
                        "Kupon", "Duration", "Marktrisikowert"]
        avail_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(filtered[avail_cols].head(200), use_container_width=True, hide_index=True)

    # ── Mein Portfolio ──
    st.markdown("---")
    st.markdown("### 📊 Mein Portfolio")

    portfolio = st.session_state.builder_portfolio
    n_titel = len(portfolio)

    if n_titel == 0:
        st.info("Noch keine Titel ausgewählt. Nutze die Filter oben oder lade ein Musterportfolio.")
        return

    st.caption(f"**{n_titel} Titel** ausgewählt (max. {MAX_TITEL})")

    # Buttons
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        if st.button("⚖️ Gleichgewichten", key="equalize", use_container_width=True):
            weight_per_title = (1.0 - CASH_PCT) / n_titel
            for isin in portfolio:
                portfolio[isin] = weight_per_title
            st.session_state.builder_portfolio = portfolio
            st.rerun()
    with btn_col2:
        if st.button("🔄 Portfolio zurücksetzen", key="reset_pf", use_container_width=True):
            _reset_portfolio()
            st.rerun()
    with btn_col3:
        pass  # CSV-Export kommt unten

    # Gewicht-Editor
    pf_rows = []
    for isin, weight in portfolio.items():
        match = universe[universe["ISIN"] == isin]
        if match.empty:
            continue
        row = match.iloc[0]
        pf_rows.append({
            "Name": row.get("Name", ""),
            "WKN": row.get("WKN", ""),
            "ISIN": isin,
            "Assetklasse": row.get("Assetklasse", ""),
            "Gewicht (%)": round(weight * 100, 2),
        })

    if not pf_rows:
        st.info("Keine gültigen Titel im Portfolio.")
        return

    pf_df = pd.DataFrame(pf_rows)

    edited_pf = st.data_editor(
        pf_df,
        column_config={
            "Gewicht (%)": st.column_config.NumberColumn(
                "Gewicht (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f"
            ),
        },
        disabled=["Name", "WKN", "ISIN", "Assetklasse"],
        hide_index=True,
        use_container_width=True,
        key="builder_pf_editor"
    )

    # Gewichte zurückschreiben
    if edited_pf is not None:
        for _, row in edited_pf.iterrows():
            isin = row["ISIN"]
            new_weight = row["Gewicht (%)"] / 100.0
            if isin in st.session_state.builder_portfolio:
                st.session_state.builder_portfolio[isin] = new_weight

    # Summen
    total_weight = sum(st.session_state.builder_portfolio.values())
    cash_weight = max(0.0, 1.0 - total_weight)

    sum_col1, sum_col2, sum_col3 = st.columns(3)
    with sum_col1:
        st.metric("Investiert", fmt_pct_de(total_weight))
    with sum_col2:
        st.metric("💰 Liquidität", fmt_pct_de(cash_weight))
    with sum_col3:
        color = "🟢" if abs(total_weight + cash_weight - 1.0) < 0.001 else "🔴"
        st.metric("Summe", f"{color} {fmt_pct_de(total_weight + cash_weight)}")

    if total_weight > (1.0 - CASH_PCT + 0.001):
        st.warning(f"⚠️ Investitionsgrad übersteigt {fmt_pct_de(1.0 - CASH_PCT)}. Bitte Gewichte anpassen (Cash-Minimum: {fmt_pct_de(CASH_PCT)}).")

    # ── CSV Export ──
    st.markdown("---")
    csv_col1, csv_col2 = st.columns(2)
    with csv_col1:
        if st.button("⬇️ Portfolio als CSV exportieren", key="csv_export", use_container_width=True):
            export_df = edited_pf.copy() if edited_pf is not None else pf_df.copy()
            # Cash-Zeile hinzufügen
            cash_row = pd.DataFrame([{
                "Name": "Liquidität", "WKN": "", "ISIN": "",
                "Assetklasse": "Cash", "Gewicht (%)": round(cash_weight * 100, 2)
            }])
            export_df = pd.concat([export_df, cash_row], ignore_index=True)
            csv_data = export_df.to_csv(index=False, sep=";", decimal=",")
            st.download_button(
                "⬇️ Download CSV", csv_data,
                f"Portfolio_Builder_{dt.date.today().strftime('%Y%m%d')}.csv",
                "text/csv", key="csv_dl"
            )

    # ── Strukturanalyse ──
    st.markdown("---")
    st.markdown("### 📊 Strukturanalyse")

    analysis_df = build_builder_analysis_df(st.session_state.builder_portfolio, universe)
    if analysis_df.empty:
        st.info("Keine Daten für Analyse vorhanden.")
        return

    # Kennzahlen
    liq = cash_weight
    w_duration = calc_weighted_duration(analysis_df)
    w_kupon = calc_weighted_kupon(analysis_df)

    kc = st.columns(5 if use_volume else 4)
    with kc[0]:
        st.metric("Anzahl Titel", n_titel)
    with kc[1]:
        st.metric("Investitionsgrad", fmt_pct_de(total_weight),
                  help="Anteil in Wertpapiere investiert.")
    with kc[2]:
        st.metric("Liquidität", fmt_pct_de(liq),
                  help="Nicht investierter Anteil.")
    with kc[3]:
        if w_duration is not None:
            st.metric("⌀ Duration (gew.)", f"{w_duration:.2f}".replace(".", ","),
                      help="Gewichtete durchschnittliche Duration aller Anleihen im Portfolio.")
        elif w_kupon is not None:
            st.metric("⌀ Kupon (gew.)", fmt_pct_de(w_kupon),
                      help="Gewichteter Durchschnittskupon aller Anleihen.")
        else:
            st.metric("Ø Risiko", f"{analysis_df['Marktrisikowert'].mean():.1f}".replace(".", ",") if analysis_df['Marktrisikowert'].notna().any() else "–",
                      help="Durchschnittlicher Marktrisikowert.")
    if use_volume:
        with kc[4]:
            st.metric("Investiert (€)", fmt_eur_de(total_weight * anlagevolumen))

    # Zusätzliche Kennzahlen für Anleihen
    has_bonds = analysis_df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False).any()
    if has_bonds:
        st.markdown("---")
        st.markdown("**🏦 Anleihen-Detail**")
        bond_rows = analysis_df[analysis_df["Gattung"].str.lower().str.contains("rente|anleihe|bond", na=False)]
        bond_weight = bond_rows["Gewicht"].sum()
        bond_count = len(bond_rows)

        n_bcols = 2 + (1 if w_duration is not None else 0) + (1 if w_kupon is not None else 0)
        bc = st.columns(max(n_bcols, 2))
        col_idx = 0
        with bc[col_idx]:
            st.metric("Anzahl Anleihen", bond_count)
            col_idx += 1
        with bc[col_idx]:
            st.metric("Gewicht Anleihen", fmt_pct_de(bond_weight),
                      help="Gesamtgewicht aller Anleihen im Portfolio.")
            col_idx += 1
        if w_duration is not None:
            with bc[min(col_idx, len(bc)-1)]:
                st.metric("⌀ Duration (gew.)", f"{w_duration:.2f}".replace(".", ","),
                          help="Gewichtete Duration der Anleihen. Gibt Zinssensitivität an.")
                col_idx += 1
        if w_kupon is not None:
            with bc[min(col_idx, len(bc)-1)]:
                st.metric("⌀ Kupon (gew.)", fmt_pct_de(w_kupon),
                          help="Gewichteter Durchschnittskupon aller Anleihen.")

    # Ring-Diagramme
    st.markdown("---")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        alloc_g = build_allocation(analysis_df, "Gattung")
        if not alloc_g.empty:
            st.plotly_chart(build_ring_chart(alloc_g, "Gattung", "Allokation nach Gattung"), use_container_width=True)
    with rc2:
        alloc_r = build_allocation(analysis_df, "Region")
        if not alloc_r.empty:
            st.plotly_chart(build_ring_chart(alloc_r, "Region", "Allokation nach Region"), use_container_width=True)
    with rc3:
        alloc_s = build_allocation(analysis_df, "Segment")
        if not alloc_s.empty:
            st.plotly_chart(build_ring_chart(alloc_s, "Segment", "Allokation nach Segment"), use_container_width=True)

    # Top 5 Holdings
    st.markdown("---")
    top5 = get_top_holdings(analysis_df, n=5)
    if not top5.empty:
        fig_t5 = build_top5_bar_chart(top5, "Top 5 Holdings (nach Gewicht)")
        st.plotly_chart(fig_t5, use_container_width=True)

    # Gruppierte Tabelle
    st.markdown("**Einzeltitel-Übersicht**")
    grouped = build_grouped_title_table(analysis_df, anlagevolumen if use_volume else 0.0, show_ytd=False)
    for gattung_name, gattung_weight, disp_df in grouped:
        if gattung_name.startswith("💰"):
            st.markdown(f"**{gattung_name}** ({fmt_pct_de(gattung_weight)})")
        else:
            st.markdown(f"**📋 {gattung_name}** – {fmt_pct_de(gattung_weight)}")
        st.dataframe(disp_df, use_container_width=True, hide_index=True)

    # ── Vergleich mit Musterportfolio ──
    st.markdown("---")
    st.markdown("### 🔄 Vergleich mit Musterportfolio")
    if pf_data:
        vgl_names = ["-- Kein Vergleich --"] + filtered_mp[col_display].tolist()
        vgl_sel = st.selectbox("Musterportfolio zum Vergleich", vgl_names, key="builder_vgl")

        if vgl_sel != "-- Kein Vergleich --":
            vgl_csv = mp_to_csv.get(vgl_sel)
            if vgl_csv and vgl_csv in pf_data:
                vgl_df = pf_data[vgl_csv]
                st.markdown(f"---")
                st.subheader(f"📊 Vergleich: Mein Portfolio vs. {vgl_sel}")

                # Mein Portfolio
                st.markdown(f"**Mein Portfolio** ({n_titel} Titel)")
                # Bereits oben angezeigt – hier nur Kurzinfo

                # Musterportfolio
                st.markdown(f"**{vgl_sel}**")
                vgl_liq = 1.0 - vgl_df["Gewicht"].sum()
                vc = st.columns(3)
                with vc[0]:
                    st.metric("Anzahl Titel", len(vgl_df))
                with vc[1]:
                    st.metric("Investitionsgrad", fmt_pct_de(vgl_df["Gewicht"].sum()))
                with vc[2]:
                    st.metric("Liquidität", fmt_pct_de(max(0, vgl_liq)))

                # Ring-Vergleich
                vrc1, vrc2, vrc3 = st.columns(3)
                with vrc1:
                    va_g = build_allocation(vgl_df, "Gattung")
                    if not va_g.empty:
                        st.plotly_chart(build_ring_chart(va_g, "Gattung", f"Gattung – {vgl_sel}"), use_container_width=True)
                with vrc2:
                    va_r = build_allocation(vgl_df, "Region")
                    if not va_r.empty:
                        st.plotly_chart(build_ring_chart(va_r, "Region", f"Region – {vgl_sel}"), use_container_width=True)
                with vrc3:
                    va_s = build_allocation(vgl_df, "Segment")
                    if not va_s.empty:
                        st.plotly_chart(build_ring_chart(va_s, "Segment", f"Segment – {vgl_sel}"), use_container_width=True)
    else:
        st.info("Keine Musterportfolios verfügbar für Vergleich.")
