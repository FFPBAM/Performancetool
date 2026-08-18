# streamlit_app.py
"""
Hauptdatei: Login, Sidebar, Navigation (Performance + Portfolioanalyse).
Performance-Code bleibt inline (bewährt), Portfolioanalyse aus Modul.

NAVIGATION (NEU 07.07.2026): st.tabs wurde durch st.segmented_control
ersetzt. Grund: st.tabs "vergisst" bei jedem Rerun (z.B. Selectbox-Auswahl
im Portfolioanalyse-Bereich) den aktiven Tab und springt auf den ersten
zurück (bekanntes Streamlit-Verhalten, GitHub #6257/#11160/#4996/#12554;
auch key+default+on_change stellten den Tab nicht wieder her).
segmented_control hält seinen Zustand nativ im session_state → das Problem
ist strukturell weg (per AppTest unter Streamlit 1.59.0 verifiziert).

Hinweis: Tab 'Portfolio zusammenstellen' wurde deaktiviert (Modul
modules/portfolio_builder.py bleibt im Repo, wird aber nicht importiert).
"""
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from modules.shared import (
    APP_TITLE,
    FFPB_DARK, FFPB_GOLD, FFPB_LIGHT, FFPB_BLUE2, FFPB_SAND, FFPB_PALETTE,
    DATA_FOLDER, DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS,
    load_anlagekriterien, zeige_anlagekriterien,
    check_login, fmt_date_de, fmt_pct_de, fmt_eur_de,
    detect_newest_date_tag, load_mapping, load_name_mapping,
    build_name_lookups,
    # CSV-Loader (07.08.2026): kommen jetzt von hier statt als lokale
    # Kopien weiter unten — eine Implementierung, ein Cache.
    # (to_decimal_interval wird seitdem nur noch innerhalb von shared.py
    # gebraucht und ist deshalb hier nicht mehr importiert.)
    load_all_csvs, build_portfolio_timeseries,
    strategien_ohne_honorarsatz,
)
# Performance-Berechnungs-Funktionen (Single Source of Truth — siehe modules/analytics.py)
#
# AUFGERÄUMT 12.08.2026: Die Namen kamen bis dahin mit `as _ana_…` herein und
# wurden unten durch zehn Funktionen wieder durchgereicht, die nichts taten
# als weiterzurufen. Jetzt heißen sie hier so, wie sie in analytics heißen —
# die 25 Aufrufstellen im Programm sind unverändert geblieben.
from modules.analytics import (
    annual_to_daily_rate,
    make_index_from_returns,
    make_index_after_fee,
    drawdown_from_index,
    calc_cagr,
    calc_vola,
    calc_daily_returns_after_fee,
    calc_sharpe_excess,
    calc_period_return,
    calc_period_return_after_fee,
    has_benchmark,
    historie_beschneiden,
)
from modules.portfolioanalyse import (
    build_pf_data, familie_fuer_strategie, load_pf_csvs,
    render_portfolioanalyse,
)
from modules.risiko_ansicht import (
    zeige_drawdown_tabelle, zeige_monatsheatmap, zeige_risiko_ueberblick,
    zeitraum_fuer_heatmap,
)
from modules.strategievergleich import zeige_strategievergleich
from modules.vorlagen_config import VORLAGEN_FAMILIEN


# ==========================================================================
# PERFORMANCE HELPERS — die UI-spezifischen Ergänzungen zu analytics
# ==========================================================================
# Die Berechnungs-Logik lebt in modules/analytics.py und wird auch vom
# PPTX-Export genutzt. Hier stehen nur noch die Funktionen, die es dort NICHT
# gibt, weil sie die Broschüre nicht braucht: der Euro-Drawdown, die
# Calmar-Ratio, die Drawdown-Dauer und -Erholung, die Datums-Varianten des
# MDD und der rf-Index.
#
# AUFGERÄUMT 12.08.2026: Zwischen diesen Helfern standen zehn Funktionen, die
# nichts taten, als eine gleichnamige analytics-Funktion aufzurufen. Eine
# davon (annual_fee_to_daily_drag) rief niemand auf, die übrigen neun an 25
# Stellen. Die Aufrufstellen sind unverändert geblieben — die Namen kommen
# jetzt direkt aus dem Import oben. Wer eine Berechnung sucht, findet sie
# damit dort, wo sie hingehört, und nicht in einer Attrappe hier.
#
# Der Unterschied zu den 40 Wrappern, die am 11.08. aus pptx_export.py
# geflogen sind: Dort waren 27 von 40 tot. Hier war es einer von zehn —
# der Ertrag ist entsprechend klein (rund 25 Zeilen). Aufgeräumt wurde
# trotzdem, weil eine Attrappe mit dem Namen einer echten Funktion die
# Suche in die Irre führt.

def drawdown_euro_from_index(idx):
    """UI-spezifisch: Euro-Drawdown (idx - peak), bleibt lokal."""
    peak = np.maximum.accumulate(idx); return idx - peak

# to_decimal_interval kommt jetzt aus modules.shared (siehe Import oben)

def calc_max_drawdown(idx_after, dates_list):
    """UI-Variante: gibt (mdd_wert, datum) Tupel zurück — wird auf der UI angezeigt.
    Nutzt intern analytics.drawdown_from_index für die Mathematik."""
    dd = drawdown_from_index(idx_after); mi = np.argmin(dd)
    return float(dd[mi]), dates_list[mi]

def calc_max_drawdown_euro(idx_after, dates_list):
    """UI-spezifisch: Euro-Variante mit Datum. Bleibt lokal."""
    dd = drawdown_euro_from_index(idx_after); mi = np.argmin(dd)
    return float(dd[mi]), dates_list[mi]

def calc_calmar_ratio(cagr, max_dd):
    """UI-spezifisch: Calmar = CAGR / |MDD|. Bleibt lokal."""
    if cagr is None or max_dd is None or max_dd == 0: return None
    return cagr / abs(max_dd)

def calc_drawdown_recovery(idx_after, dates_list):
    """UI-spezifisch: Erholungs-Dauer nach maximalem DD. Bleibt lokal."""
    dd = drawdown_from_index(idx_after); mi = np.argmin(dd)
    for i in range(mi+1, len(dd)):
        if dd[i] >= 0.0:
            rd = dates_list[i]; td = dates_list[mi]
            return (rd - td).days if isinstance(rd, pd.Timestamp) else i - mi, rd
    return None, None

def calc_max_drawdown_duration(idx_after, dates_list):
    """UI-spezifisch: längste DD-Phase. Bleibt lokal."""
    dd = drawdown_from_index(idx_after)
    max_dur = 0; max_start = 0; max_end = 0; current_start = None
    for i in range(len(dd)):
        if dd[i] < 0:
            if current_start is None: current_start = i
        else:
            if current_start is not None:
                dur = (dates_list[i] - dates_list[current_start]).days if isinstance(dates_list[i], pd.Timestamp) else i - current_start
                if dur > max_dur: max_dur = dur; max_start = current_start; max_end = i
                current_start = None
    if current_start is not None:
        dur = (dates_list[-1] - dates_list[current_start]).days if isinstance(dates_list[-1], pd.Timestamp) else len(dd)-1-current_start
        if dur > max_dur: max_dur = dur; max_start = current_start; max_end = len(dd)-1
    return max_dur, dates_list[max_start], dates_list[max_end]

# --- NEU: Risikofreier Zins + Sharpe -------------------------------------

def aggregate_rf_geometric(rf_annual_series, n_days):
    """Aggregiert eine Zeitreihe annualisierter rf-Werte geometrisch zu einem
    einzelnen p.a.-Wert über den Zeitraum.

    Logik: Jeder Tageswert ist ein annualisierter Zinssatz. Wir wandeln ihn in
    den korrespondierenden Tagessatz um ((1+rf)^(1/365)-1), kompoundieren alle
    Tagessätze und rechnen das Ergebnis zurück auf p.a.
    """
    rf = pd.Series(rf_annual_series).dropna().to_numpy(dtype=float)
    if len(rf) == 0 or n_days <= 0:
        return None
    daily = annual_to_daily_rate(rf)
    growth = float(np.prod(1.0 + daily))
    if growth <= 0:
        return None
    return growth ** (365.0 / n_days) - 1.0

def make_index_from_rf(rf_annual_series, startwert=100.0):
    """UI-spezifisch: Baut einen Index aus täglich variablen rf-Werten.
    Jeder Tag verzinst sich mit seinem eigenen Tagessatz. Bleibt lokal."""
    rf = pd.Series(rf_annual_series).fillna(0).to_numpy(dtype=float)
    daily = annual_to_daily_rate(rf)
    return make_index_from_returns(daily, startwert)

# -------------------------------------------------------------------------

def _asof_value(series, target_ts):
    s = series.dropna()
    if s.empty or target_ts < s.index.min(): return None
    return float(s.asof(target_ts))

def period_return(series_idx, start_ts, end_ts):
    v_end = _asof_value(series_idx, end_ts); v_start = _asof_value(series_idx, start_ts)
    if v_end is None or v_start is None or v_start == 0: return None
    return (v_end / v_start) - 1.0

def build_rolling_table(idx_before_1, idx_after_1, label_1, idx_before_2=None, idx_after_2=None, label_2=None, since_label=None):
    end_ts = idx_after_1.dropna().index.max()
    if pd.isna(end_ts): return pd.DataFrame()
    first_ts = idx_after_1.dropna().index.min()
    # YTD ab VORJAHRES-SCHLUSSSTAND (03.07.2026): asof(01.01.) nahm bei
    # kalendertäglichen Daten den Indexstand NACH dem 01.01. — die Tabelle
    # verlor damit den ersten Tag des Jahres (Rendite + 1 Tag Honorar-Drag,
    # ~0,003%-Punkte) und wich von PP-Folie 8 und dem eigenen Balken-Chart
    # ab (beide rechnen ab 31.12.-Schluss, d.h. Renditen >= 01.01. inklusive).
    # asof(31.12. Vorjahr) = letzter Schlussstand des Vorjahres → Tabelle,
    # Balken-Chart und PP sind jetzt bit-identisch. Die rollierenden
    # Zeiträume (1/3/5/10 Jahre) behalten bewusst ihre Punkt-zu-Punkt-
    # Konvention (end − n Jahre), dort gibt es keine Jahresgrenzen-Semantik.
    periods = [("ytd", pd.Timestamp(end_ts.year-1,12,31)),("1 Jahre", end_ts-pd.DateOffset(years=1)),
        ("3 Jahre", end_ts-pd.DateOffset(years=3)),("5 Jahre", end_ts-pd.DateOffset(years=5)),
        ("10 Jahre", end_ts-pd.DateOffset(years=10)),(since_label or f"Seit: {fmt_date_de(first_ts)}", first_ts)]
    rows = []
    for pname, start_ts in periods:
        r = {"Wertentwicklung rollierend": pname}
        r[(label_1, "vor Kosten")] = period_return(idx_before_1, start_ts, end_ts)
        r[(label_1, "nach Kosten")] = period_return(idx_after_1, start_ts, end_ts)
        if idx_before_2 is not None and idx_after_2 is not None and label_2:
            r[(label_2, "vor Kosten")] = period_return(idx_before_2, start_ts, end_ts)
            r[(label_2, "nach Kosten")] = period_return(idx_after_2, start_ts, end_ts)
        rows.append(r)
    df = pd.DataFrame(rows)
    base = ["Wertentwicklung rollierend"]; multi = [c for c in df.columns if c not in base]
    df = df[base + multi]
    def fmt(x):
        if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))): return "-"
        return f"{x*100:.3f}%".replace(".",",")
    for c in multi: df[c] = df[c].apply(fmt)
    return df

def compute_bar_data(df, fee_dec, mode, label, custom_start=None, custom_end=None):
    rows = []
    def _add(pl, sub):
        if sub.empty: return
        rp = sub["ret_port"].fillna(0.0).to_numpy(float); rb = sub["ret_bm"].fillna(0.0).to_numpy(float)
        # has_benchmark statt notna().any(): eine Spalte aus lauter Nullen
        # ist keine Benchmark (Bugfix 07.08.2026, siehe analytics.py).
        has_bm = has_benchmark(sub["ret_bm"])
        rows.append({"label": pl, f"{label} (nach Kosten)": calc_period_return_after_fee(rp, fee_dec)*100,
            "ret_bm_raw": calc_period_return(rb)*100 if has_bm else None})
    if mode == "Kalenderjahre":
        # BEWUSST anders als die Broschuere (Entscheidung Philip, 12.08.2026):
        # Hier bleiben angebrochene Jahre stehen — das Auflagejahr genauso wie
        # das laufende. Die Broschuere laesst sie weg (analytics._ist_volles_jahr),
        # weil dort "PERFORMANCE P.A." darueber steht und der Kunde die Zahl
        # nicht einordnen kann. Im Tool waehlt der Berater den Zeitraum selbst
        # und sieht ihn neben dem Chart; ein Teiljahr ist dort erwartbar und
        # traegt Information. Wer das angleicht, nimmt sie ihm weg.
        for y in sorted(df.index.year.unique()): _add(str(y), df[df.index.year==y])
    elif mode == "Quartale":
        tmp=df.copy(); tmp["_y"]=tmp.index.year; tmp["_q"]=tmp.index.quarter
        for (y,q),sub in tmp.groupby(["_y","_q"]): _add(f"{y} Q{q}", sub)
    elif mode == "Benutzerdefiniert":
        if custom_start is None or custom_end is None: return pd.DataFrame()
        mask=(df.index.date>=custom_start)&(df.index.date<=custom_end)
        _add(f"{fmt_date_de(custom_start)} – {fmt_date_de(custom_end)}", df[mask])
    return pd.DataFrame(rows)

def build_bar_chart(bar_df1, label_1, bench_name_1, bar_df2=None, label_2=None, bench_name_2=None, title=""):
    BG=FFPB_DARK; fig=go.Figure(); cp1=f"{label_1} (nach Kosten)"
    if cp1 in bar_df1.columns:
        v=bar_df1[cp1].tolist()
        fig.add_trace(go.Bar(name=cp1,x=bar_df1["label"],y=v,marker_color=FFPB_GOLD,text=[f"{x:+.2f}%" for x in v],textposition="outside",textfont=dict(size=11,color="white"),cliponaxis=False))
    if "ret_bm_raw" in bar_df1.columns and bar_df1["ret_bm_raw"].notna().any():
        bv=bar_df1["ret_bm_raw"].tolist()
        fig.add_trace(go.Bar(name=bench_name_1,x=bar_df1["label"],y=bv,marker_color=FFPB_LIGHT,text=[f"{x:+.2f}%" if pd.notna(x) else "" for x in bv],textposition="outside",textfont=dict(size=11,color="white"),cliponaxis=False))
    if bar_df2 is not None and label_2:
        cp2=f"{label_2} (nach Kosten)"
        if cp2 in bar_df2.columns:
            v2=bar_df2[cp2].tolist()
            fig.add_trace(go.Bar(name=cp2,x=bar_df2["label"],y=v2,marker_color=FFPB_BLUE2,text=[f"{x:+.2f}%" for x in v2],textposition="outside",textfont=dict(size=11,color="white"),cliponaxis=False))
        if bench_name_2 and bench_name_2!=bench_name_1 and "ret_bm_raw" in bar_df2.columns and bar_df2["ret_bm_raw"].notna().any():
            bv2=bar_df2["ret_bm_raw"].tolist()
            fig.add_trace(go.Bar(name=bench_name_2,x=bar_df2["label"],y=bv2,marker_color=FFPB_SAND,text=[f"{x:+.2f}%" if pd.notna(x) else "" for x in bv2],textposition="outside",textfont=dict(size=11,color="white"),cliponaxis=False))
    fig.add_hline(y=0,line_color="white",line_width=1)
    av=[]
    for c in [cp1]+([f"{label_2} (nach Kosten)"] if label_2 else []):
        s=bar_df1 if c==cp1 else (bar_df2 if bar_df2 is not None else pd.DataFrame())
        if c in s.columns: av+=s[c].dropna().tolist()
    if "ret_bm_raw" in bar_df1.columns: av+=bar_df1["ret_bm_raw"].dropna().tolist()
    if bar_df2 is not None and "ret_bm_raw" in bar_df2.columns: av+=bar_df2["ret_bm_raw"].dropna().tolist()
    ymi=min(av)*1.45 if av and min(av)<0 else -2; yma=max(av)*1.45 if av and max(av)>0 else 2
    fig.update_layout(title=dict(text=f"<b>{title}</b>",font=dict(size=13,color="white"),x=0,xanchor="left"),
        paper_bgcolor=BG,plot_bgcolor=BG,barmode="group",bargap=0.28,bargroupgap=0.05,height=480,
        xaxis=dict(tickfont=dict(color="white",size=12),showgrid=False,zeroline=False,linecolor="#1A4880"),
        yaxis=dict(range=[ymi,yma],tickformat=".1f",ticksuffix="%",tickfont=dict(color="white",size=11),gridcolor="#0A4576",zeroline=False),
        legend=dict(font=dict(color="white",size=11),bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.18),
        margin=dict(t=55,b=75,l=65,r=25))
    return fig

def show_benchmark_composition(dn, bt, dn2=None, bt2=None):
    if bt and str(bt).strip() and str(bt).strip().lower() not in ("","nan","haben keine benchmark"):
        st.caption(f"**Zusammensetzung Benchmark {dn}:** {bt}")
    if dn2 and bt2 and str(bt2).strip() and str(bt2).strip().lower() not in ("","nan","haben keine benchmark"):
        st.caption(f"**Zusammensetzung Benchmark {dn2}:** {bt2}")

def display_metrics(label, cagr, vola, endwert, use_volume, auflagedatum, calmar, sharpe, rf_pa, mwst_suffix=""):
    """Kennzahlen in zwei Reihen:
       Reihe 1: Auflagedatum | CAGR | Vola
       Reihe 2: Calmar | Sharpe | (Endwert wenn Volumen)
       Ø Risikofreier Zins p.a. (Zeitraum) als Caption unter den Kacheln.
    """
    # Der Kostenhinweis steht EINMAL über der Kachelreihe (11.08.2026).
    # Vorher trug ihn jede einzelne Kachel — „⌀ Rendite p.a. (nach Kosten
    # (exkl. MwSt.))" — Klammern in Klammern, und die eigentliche Aussage
    # verschwand dahinter. Die Angabe gilt für alle Kacheln der Reihe.
    nk = f"nach Kosten{mwst_suffix}"
    st.markdown(f"**{label}** · {nk}")
    # Reihe 1
    r1 = st.columns(3)
    with r1[0]:
        st.metric("Auflage der Strategie", fmt_date_de(auflagedatum),
                  help="Erster verfügbarer Datenpunkt der Strategie im "
                       "Portfoliomanagement-System.")
    with r1[1]:
        st.metric("⌀ Rendite p.a.", fmt_pct_de(cagr) if cagr else "–",
                  help=f"Annualisierte Rendite {nk} (CAGR): "
                       f"(Endwert/Startwert)^(365/Tage) − 1.")
    with r1[2]:
        st.metric("Volatilität p.a.", fmt_pct_de(vola) if vola else "–",
                  help="Annualisierte Schwankungsbreite: Standardabweichung der Tagesrenditen × √365.")
    # Reihe 2
    r2 = st.columns(3)
    with r2[0]:
        st.metric("Calmar Ratio",
                  f"{calmar:.2f}".replace(".",",") if calmar else "–",
                  help="CAGR / |Max Drawdown|. Je höher, desto besser die risikoadjustierte Rendite.")
    with r2[1]:
        st.metric("Sharpe Ratio",
                  f"{sharpe:.2f}".replace(".",",") if sharpe is not None else "–",
                  help="Sharpe Ratio nach Sharpe (1994): Mittelwert der täglichen Überrenditen (Portfolio − rf) geteilt durch deren Standardabweichung, anschließend × √365 annualisiert. Misst die Überrendite über den risikofreien Zins pro Risikoeinheit.")
    if use_volume and endwert:
        with r2[2]:
            st.metric("Endwert", fmt_eur_de(endwert),
                      help=f"Wert des Anlagevolumens am Ende des Zeitraums, {nk}.")
    # Aggregierter rf als Caption
    if rf_pa is not None:
        st.caption(f"Ø Risikofreier Zins p.a. (Zeitraum): **{fmt_pct_de(rf_pa)}**")

def display_drawdown_metrics(label, mddv, mddd, mdde, uv, rd, rdate, mddur, dds, dde, mwst_suffix=""):
    nk = f"nach Kosten{mwst_suffix}"
    st.markdown(f"**{label} ({nk})**")
    rv=f"{rd} Tage" if rd else "noch nicht erholt"; rh=f" Erholt am {fmt_date_de(rdate)}." if rd else ""
    cols=st.columns(4)
    with cols[0]:
        st.metric("Max. Drawdown",fmt_pct_de(mddv),help=f"Größter Verlust vom Höchststand ({nk}). Tiefpunkt am {fmt_date_de(mddd)}.")
        if uv and mdde is not None:
            st.caption(f"entspricht {fmt_eur_de(mdde)}")
    with cols[1]: st.metric("Erholungsdauer",rv,help=f"Tage vom Tief bis zurück zum alten Höchststand.{rh}")
    with cols[2]: st.metric("Längste Drawdown-Phase",f"{mddur} Tage" if mddur>0 else "–",help=f"Längster Zeitraum unter Peak: {fmt_date_de(dds)} – {fmt_date_de(dde)}." if mddur>0 else "Kein Drawdown.")
    with cols[3]: st.metric("Drawdown-Tief am",fmt_date_de(mddd),help="Datum des tiefsten Drawdown-Punkts.")

# Data loading
# ENTFERNT 07.08.2026: Hier standen bis dahin EIGENE Kopien von
# load_all_csvs / read_one_csv / parse_dates_col / extract_benchmark_name /
# build_portfolio_timeseries — Zeile für Zeile identisch zu modules/shared.py.
#
# Warum das ein Problem war:
#   • Der Performance-Tab nutzte die lokalen Kopien, Portfolioanalyse und
#     PPTX-Export die aus shared.py. Zwei @st.cache_data-Funktionen mit
#     gleichem Inhalt = zwei getrennte Caches → alle CSVs wurden doppelt
#     geparst und doppelt im Speicher gehalten.
#   • Wären die Kopien je auseinandergelaufen, hätten Tool-Anzeige und
#     Broschüre verschiedene Zahlen gezeigt — genau das, was die
#     Konsistenz-Doktrin (Doku 10.8) verhindern soll.
#
# Die Funktionen kommen jetzt aus modules.shared (Import ganz oben).


# ==========================================================================
# STREAMLIT APP
# ==========================================================================
st.set_page_config(page_title=APP_TITLE, layout="wide")

# SCHRIFTART: kommt seit 18.08.2026 aus dem THEME, nicht mehr von hier.
#
# An dieser Stelle stand ein <style>-Block, der 'Segoe UI' per !important auf
# die Elemente des Hauptbereichs schrieb - ausdruecklich NUR dort, weil ein
# globaler Font-Override die Streamlit-Icons zerstoert (Transferwissen #1).
# Die Sidebar blieb deshalb bei der Standardschrift.
#
# `.streamlit/config.toml` setzt jetzt `theme.font`. Das ist der dafuer
# vorgesehene Weg, wirkt auf die ganze Anwendung einschliesslich Sidebar und
# ruehrt die Icons nicht an - der Hack und seine Einschraenkung entfallen
# beide. Wer ihn zurueckholen will, findet ihn in der Historie dieses
# Commits.

if not check_login(): st.stop()

# ── KEEP-ALIVE für Widget-Zustände (NEU 07.07.2026) ─────────────────────────
# Seit dem Umbau auf segmented_control läuft nur noch die AKTIVE Ansicht.
# Streamlit löscht Widget-States, deren Widget in einem Run nicht gerendert
# wird — d.h. beim Wechsel Performance → Portfolioanalyse → zurück wären
# Selectbox/Häkchen/Kostensatz auf Default. Das Re-Assignen aller Keys am
# Skriptanfang markiert sie als API-gesetzt → sie überleben den Wechsel
# (per AppTest unter Streamlit 1.59.0 verifiziert).
# Trigger-Widgets (Buttons/Downloads) sind ausgenommen: ihr Zustand darf
# nicht persistieren (sonst würde ein Klick "hängen bleiben").
#
# ACHTUNG — JEDER NEUE BUTTON MIT key= GEHÖRT IN DIESE LISTE (11.08.2026):
# Das try/except unten hilft dabei NICHT. Die Zuweisung selbst geht durch;
# sie markiert den Key nur als "per API gesetzt". Erst das spätere
# st.button(key=...) wirft dann StreamlitValueAssignmentNotAllowedError —
# außerhalb dieses try. Der Kommentar behauptete bis 11.08.2026 das
# Gegenteil ("fängt künftige Trigger-Keys defensiv ab"); beim Einbau des
# Zurücksetzen-Knopfes kam prompt der Absturz. Das try/except bleibt für
# andere nicht setzbare Keys, ersetzt die Liste aber nicht.
#
# 11.08.2026: "reset_sd"/"reset_ed" entfallen — die beiden alten
# Zurücksetzen-Schaltflächen sind durch die Zeitraum-Schnellwahl ersetzt.
# Neu: "p_zeit_reset" (Zurücksetzen im eigenen Zeitraum).
# 18.08.2026: "sv_ue_chart" dazu — der Ueberschneidungs-Chart im
# Strategievergleich laeuft mit `on_select="rerun"` und ist damit ein WIDGET,
# nicht nur eine Zeichnung. Sein Zustand darf nicht re-assigniert werden.
#
# DIESE ZEILE FEHLTE UND HAT DIE LAUFENDE APP ANGEHALTEN. Sie war eingeplant
# ("falls es wirft, gehoert der Key hierher"), und ein AppTest ueber vier
# Laeufe meldete "kein Absturz" — in der Cloud kam
# StreamlitValueAssignmentNotAllowedError. Warum der AppTest es nicht sah,
# steht in tests/test_bedienung.py bei Schritt 1c; die Kurzfassung: Er hat
# die Ansicht ueber session_state gesetzt statt sie zu bedienen, und der
# Chart wurde deshalb nie zweimal MIT vorhandenem Zustand gerendert.
_KEEPALIVE_SPERRE = {"pf_pptx_btn", "pf_pptx_dl", "p_zeit_reset",
                     "sv_ue_chart"}
for _k in list(st.session_state.keys()):
    if _k in _KEEPALIVE_SPERRE:
        continue
    try:
        st.session_state[_k] = st.session_state[_k]
    except Exception:
        pass  # nicht setzbarer Key → bewusst überspringen

st.title(APP_TITLE)

# ── Gemeinsame Sidebar ──
mapping = load_mapping()
name_mapping = load_name_mapping()

with st.sidebar:
    st.header("Einstellungen")
    st.markdown("---")
    st.subheader("Anlagevolumen")
    anlagevolumen = st.number_input("Anlagevolumen in € (optional)",
        min_value=0.0, max_value=1_000_000_000.0, value=0.0, step=10_000.0, format="%.2f",
        help="Gilt für beide Bereiche. Wenn > 0: Werte in Euro.")
    use_volume = anlagevolumen > 0
    # Der Hinweis stand bisher nur im Tooltip (11.08.2026). Das Feld sitzt
    # über den ansichtseigenen Einstellungen und wirkt auf BEIDE Bereiche —
    # das sollte man sehen, ohne den Mauszeiger darüber zu halten.
    st.caption("Wirkt in beiden Ansichten: 0 zeigt Prozente, ein Betrag "
               "rechnet alles zusätzlich in Euro."
               if not use_volume else
               "Wirkt in beiden Ansichten — Werte werden in Euro gezeigt.")

# ── ZENTRALE DATENBEREITSTELLUNG (läuft bei JEDEM Run, VOR der Navigation) ──
# Der PowerPoint-Export im Portfolioanalyse-Bereich braucht perf_timeseries /
# perf_d2c / perf_d2b. Da seit dem Navigations-Umbau nur noch die aktive
# Ansicht rendert, wird die Bereitstellung hier zentral gemacht — sie darf
# nicht mehr vom Besuch der Performance-Ansicht abhängen. (Der Fallback-
# Loader in portfolioanalyse.py bleibt als zweites Netz bestehen, nutzt aber
# immer den Standard-Date-Tag — hier gilt derselbe Tag wie in der Anzeige.)
auto_tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
date_tag = auto_tag
# Manuell gesetzter Date-Tag (Erweiterte Einstellungen im Performance-
# Bereich) gilt auch hier — aber wie bisher NUR solange das Häkchen aktiv
# ist. Die Widgets selbst werden weiter unten in der Performance-Ansicht
# gerendert; ihre Werte liegen zum Zeitpunkt dieses Runs bereits im
# session_state (Streamlit aktualisiert Widget-States VOR dem Rerun).
if st.session_state.get("adv_perf") and st.session_state.get("perf_tag"):
    date_tag = st.session_state["perf_tag"]

perf_daten_fehler = None
data = {}; dn_ordered = []; d2c = {}; d2b = {}
files = load_all_csvs(DATA_FOLDER, date_tag, EXCLUDE_SUBSTRINGS)
if not files:
    perf_daten_fehler = f"Keine Dateien für Tag {date_tag}."
else:
    data = build_portfolio_timeseries(files, mapping)
    dn_ordered, d2c, d2b = build_name_lookups(name_mapping, set(data.keys()))
    if not dn_ordered:
        perf_daten_fehler = "Keine Portfolios zugeordnet."

if perf_daten_fehler is None:
    # Daten an den Portfolioanalyse-Bereich weitergeben (PowerPoint-Export:
    # Wertentwicklungs-Folie braucht Zeitreihen, d2c-Auflösung und die
    # Benchmark-Texte für die ***-Fußnote).
    st.session_state["perf_timeseries"] = data
    st.session_state["perf_d2c"] = d2c
    st.session_state["perf_d2b"] = d2b

# ── NAVIGATION (NEU 07.07.2026): segmented_control statt st.tabs ──
# st.tabs sprang bei jedem Rerun (z.B. Strategie-Selectbox) auf den ersten
# Tab zurück — auch mit key/default/on_change (bei gesetztem key wirkt
# default nur bei der ERSTEN Instanziierung, kann also nichts wiederher-
# stellen). segmented_control hält seinen Zustand nativ im session_state.
# required=True verhindert das Abwählen (Klick auf aktives Segment = no-op),
# es gibt also nie den Zustand "keine Ansicht gewählt".
_VIEW_PERF = "Performance"
_VIEW_PF = "Portfolioanalyse"
# Dritte Ansicht (18.08.2026). Sie wird ANGEHAENGT und nicht dazwischen
# geschoben: Die Reihenfolge der ersten beiden Segmente sitzt bei den
# Kollegen in der Hand, und ein Umsortieren waere eine Aenderung ohne Gewinn.
_VIEW_VGL = "Strategievergleich"
if "nav_view" not in st.session_state:
    st.session_state["nav_view"] = _VIEW_PERF
# Datenstand neben die Ansichtsumschaltung (11.08.2026): Er stand bisher nur
# als kleine Fußzeile zwischen Kennzahlen und Zeitraum. Im Kundengespräch ist
# der Stichtag eine der ersten Fragen — er gehört nach oben.
_nav_l, _nav_r = st.columns([3, 2])
with _nav_l:
    ansicht = st.segmented_control("Ansicht",
                                   [_VIEW_PERF, _VIEW_PF, _VIEW_VGL],
                                   key="nav_view", required=True,
                                   label_visibility="collapsed")
with _nav_r:
    _stand = auto_tag if len(auto_tag) == 6 else None
    if _stand:
        st.caption(f"Datenstand **{_stand[4:6]}.{_stand[2:4]}.20{_stand[0:2]}**")


# ===========================================================================
# ANSICHT 1: PERFORMANCE
# ===========================================================================
if ansicht == _VIEW_PERF:
    with st.sidebar:
        st.markdown("---")
        st.subheader("Performance")
        # Aufklappbereich statt Kontrollkästchen für die GRUPPIERUNG
        # (11.08.2026) — der AUSLÖSER bleibt aber ein ausdrückliches Häkchen.
        # Grund: Ein Expander rendert seinen Inhalt immer, auch zugeklappt.
        # Würde man allein daran koppeln, griffe ein einmal eingetippter
        # Datenstand für immer weiter — auch wenn längst neuere Daten da sind.
        # Das Häkchen macht diese Abweichung sichtbar und rücknehmbar.
        with st.expander("Erweiterte Einstellungen"):
            st.checkbox("Anderen Datenstand verwenden", value=False,
                key="adv_perf",
                help="Normalerweise wird automatisch der neueste Datenstand "
                     "genommen. Nur für den Blick auf ältere Stände.")
            # Der Wert wird OBEN in der zentralen Datenbereitstellung gelesen
            # (session_state["perf_tag"]) — hier nur das Widget rendern.
            st.text_input("Date-Tag (yyMMdd)", value=auto_tag,
                help="Neuester Tag automatisch erkannt. Nur ändern um auf ältere Stände zuzugreifen.", key="perf_tag")

    # Fehler aus der zentralen Datenbereitstellung hier anzeigen (nur die
    # Performance-Ansicht braucht diese Daten zwingend; die Portfolioanalyse
    # hat einen eigenen Fallback und läuft weiter).
    if perf_daten_fehler:
        st.error(perf_daten_fehler); st.stop()

    with st.sidebar:
        # Gruppiert (11.08.2026): vorher standen 11 Schalter flach
        # untereinander — Auswahl, Darstellung und Honorar ohne Trennung.
        # Es ändert sich keine Funktion, nur die Ordnung.
        st.caption("**Auswahl**")
        ds1=st.selectbox("Portfolio",dn_ordered,key="p_sel1",
            help="Die Anlagestrategie, deren Wertentwicklung ausgewertet wird.")
        ps1=d2c[ds1]
        sc=st.checkbox("Vergleichsportfolio",value=False,key="p_cmp",
            help="Stellt eine zweite Strategie daneben — in Chart, Kennzahlen und Tabellen.")
        ps2=ds2=None
        if sc:
            ds2=st.selectbox("Vergleichsportfolio",dn_ordered,key="p_sel2")
            ps2=d2c[ds2]

        st.caption("**Darstellung**")
        sv=st.checkbox("Vor Kosten",value=True,key="p_vk",
            help="Zeigt zusätzlich eine Linie OHNE Honorarabzug. Die Kennzahlen "
                 "bleiben davon unberührt — die sind immer nach Kosten.")
        sb=st.checkbox("Benchmark",value=True,key="p_bm",
            help="Zeigt die hinterlegte Vergleichsgröße als eigene Linie. "
                 "Strategien ohne Benchmark im Mapping bleiben ohne.")
        sb_rf=st.checkbox("Risikofreier Zins",value=False,key="p_rf",
            help="Zeigt den risikofreien Zins als zusätzliche Linie im Performance-Chart (kompoundiert aus den täglichen Werten).")
        sdd=st.checkbox("Drawdown",value=False,key="p_dd",
            help="Blendet Verlustphasen ein: Chart des Rückgangs vom jeweiligen "
                 "Höchststand plus Kennzahlen zu Tiefe und Erholungsdauer.")
        stbl=st.checkbox("Tabelle rollierend",value=True,key="p_tbl",
            help="Tabelle der Wertentwicklung über rollierende Zeiträume "
                 "(z. B. jeweils 1, 3 und 5 Jahre).")
        sbar=st.checkbox("Balken-Chart",value=True,key="p_bar",
            help="Wertentwicklung je Kalenderjahr bzw. Zeitraum als Balken, "
                 "im Vergleich zur Benchmark.")

        # Eigene Gruppe (14.08.2026): Die Schalter unter "Darstellung"
        # blenden Sichten auf DIESELBEN Zahlen ein. Die beiden hier bringen
        # zusaetzliche Auswertungen mit eigener Rechnung — und die Heatmap
        # ignoriert bewusst den gewaehlten Zeitraum. Das gehoert getrennt.
        st.caption("**Analysen**")
        sheat=st.checkbox("Monatsrenditen (Heatmap)",value=False,key="p_heat",
            help="Zeigt jeden Monat als eingefärbtes Feld: rot negativ, grün "
                 "positiv, mit der Zahl darin. Folgt dem oben gewählten "
                 "Zeitraum.")
        sheat_bm=sheat_cmp=False
        if sheat:
            sheat_bm=st.checkbox("Differenz zur eigenen Benchmark",value=False,
                key="p_heat_bm",
                help="Zweite Matrix: um wieviel die Strategie im jeweiligen "
                     "Monat besser oder schlechter war als ihr "
                     "Vergleichsmaßstab. Geometrisch gerechnet.")
            # Der Haken steht IMMER da, auch ohne aktives Vergleichsportfolio
            # (Philip, 14.08.2026): Vorher tauchte er erst auf, wenn oben ein
            # Vergleichsportfolio gewählt war — man konnte also nicht wissen,
            # dass es die Möglichkeit gibt. Ausgegraut statt versteckt.
            sheat_cmp=st.checkbox("Differenz zum Vergleichsportfolio",
                value=False,key="p_heat_cmp",disabled=not sc,
                help=("Dasselbe gegen die oben gewählte zweite Strategie. "
                      "Gezeigt werden nur Monate, in denen beide liefen."
                      if sc else
                      "Dafür oben „Vergleichsportfolio“ einschalten und eine "
                      "zweite Strategie wählen."))
        srisk=st.checkbox("Risiko im Überblick",value=False,key="p_risk",
            help="Rollierende Volatilität über ein Jahr als Chart, dazu "
                 "Volatilität, Sharpe Ratio, Tracking Error und Information "
                 "Ratio je Zeitraum.")

        st.markdown("---")
        st.caption("**Honorar**")
        fd1=float(data[ps1]["fee_default"].iloc[0]) if len(data[ps1]) else 0.0
        # Dynamischer Key: wenn Portfolio wechselt, wird der Default neu geladen
        fee_key_1 = f"p_fee1_{ps1}"
        if fee_key_1 not in st.session_state:
            st.session_state[fee_key_1] = float(round(fd1*100, 4))
        # Beschriftung nennt „netto" ausdrücklich (11.08.2026): Erst der
        # Schalter darunter verriet bisher, dass die Eingabe ohne MwSt. gemeint
        # ist. Der Strategiename entfällt — er steht direkt darüber im Feld
        # „Portfolio" und machte die Beschriftung nur lang.
        fp1=st.number_input("Honorar % p.a. (netto)",0.0,20.0,step=0.05,key=fee_key_1,
            help="Jährlicher Honorarsatz ohne Mehrwertsteuer. Vorbelegt aus dem "
                 "Honorarsatz-Mapping; für Einzelfälle überschreibbar.")
        fdec2=fp2=None
        if sc and ps2:
            fd2=float(data[ps2]["fee_default"].iloc[0]) if len(data[ps2]) else 0.0
            fee_key_2 = f"p_fee2_{ps2}"
            if fee_key_2 not in st.session_state:
                st.session_state[fee_key_2] = float(round(fd2*100, 4))
            fp2=st.number_input(f"Honorar % p.a. (netto) – {ds2}",0.0,20.0,step=0.05,key=fee_key_2,
                help="Honorarsatz des Vergleichsportfolios, ohne Mehrwertsteuer.")

        # MwSt-Option
        st.markdown("---")
        brutto_mwst = st.checkbox("Bruttohonorar (inkl. 19% MwSt.)", value=False, key="p_mwst",
            help="Wenn aktiviert, wird auf das eingegebene Nettohonorar 19% MwSt. aufgeschlagen.")
        mwst_faktor = 1.19 if brutto_mwst else 1.0
        mwst_suffix = " (inkl. 19% MwSt.)" if brutto_mwst else " (exkl. MwSt.)"

        fdec1 = (fp1 * mwst_faktor) / 100.0
        if brutto_mwst:
            st.caption(f"Effektive Kosten {ds1}: {fp1 * mwst_faktor:.4f}% p.a. (inkl. MwSt.)")
        if fp2 is not None:
            fdec2 = (fp2 * mwst_faktor) / 100.0
            if brutto_mwst:
                st.caption(f"Effektive Kosten {ds2}: {fp2 * mwst_faktor:.4f}% p.a. (inkl. MwSt.)")

    l1=ds1; l2=ds2 if sc and ds2 else None
    ad1=data[ps1].index.min().date(); ad2=data[ps2].index.min().date() if sc and ps2 else None
    rm1=data[ps1].index.min().date(); rx1=data[ps1].index.max().date()
    if sc and ps2: rm2=data[ps2].index.min().date(); rx2=data[ps2].index.max().date(); mind=max(rm1,rm2); maxd=min(rx1,rx2)
    else: mind=rm1; maxd=rx1

    # Hinweis + Quelle oben
    st.caption("**Hinweise:** Siehe Disclaimer unten!")
    st.caption(f"**Quelle:** Infront & eigene Berechnungen, Stand: {fmt_date_de(maxd)}")

    # ── Zeitraum (überarbeitet 11.08.2026) ────────────────────────────────
    # Vorher: zwei Kalenderfelder plus zwei Zurücksetzen-Schaltflächen. Für
    # „die letzten drei Jahre" waren zwei Klickfolgen im Kalender nötig — im
    # Kundengespräch der häufigste Griff überhaupt.
    # Jetzt: Schnellwahl als Normalfall, die Kalenderfelder erscheinen nur auf
    # Wunsch (Philip, 11.08.2026). „Seit Auflage" ersetzt beide
    # Zurücksetzen-Schaltflächen.
    st.markdown("#### Zeitraum")

    ZEITRAEUME = [("1 Jahr", 1), ("3 Jahre", 3), ("5 Jahre", 5),
                  ("10 Jahre", 10), ("Seit Auflage", None)]
    if "p_zeitraum" not in st.session_state:
        st.session_state["p_zeitraum"] = "Seit Auflage"

    zc1, zc2 = st.columns([3, 1])
    with zc1:
        # required=True: ein Klick auf das aktive Segment darf nicht abwählen,
        # sonst gäbe es den Zustand „kein Zeitraum gewählt" (wie bei nav_view).
        wahl = st.segmented_control(
            "Zeitraum", [n for n, _ in ZEITRAEUME], key="p_zeitraum",
            required=True, label_visibility="collapsed",
            help="Der Zeitraum endet immer am aktuellen Datenstand.")
    with zc2:
        eigener = st.checkbox("Eigener Zeitraum", value=False, key="p_zeit_frei",
            help="Blendet Kalenderfelder für Start und Ende ein.")

    # Aus der Schnellwahl abgeleitete Vorgabe. Liegt der berechnete Start vor
    # dem ersten Datenpunkt, gewinnt der erste Datenpunkt — sonst zeigte die
    # Auswahl „10 Jahre" bei einer jüngeren Strategie einen leeren Anfang.
    jahre = dict(ZEITRAEUME).get(wahl)
    if jahre is None:
        sd_vor = mind
    else:
        # Über pd.Timestamp rechnen: mind/maxd sind datetime.date, und
        # date − DateOffset ist nicht definiert.
        rueck = (pd.Timestamp(maxd) - pd.DateOffset(years=jahre)).date()
        sd_vor = max(mind, rueck)
    ed_vor = maxd

    if eigener:
        # Zurücksetzen über COUNTER-KEYS (Transferwissen #4, Lösung A):
        # st.session_state["p_sd"] = ... wirft bei einem aktiven Widget eine
        # StreamlitAPIException. Ein neuer Key erzeugt stattdessen ein NEUES
        # Widget, das seinen Default (value=sd_vor) übernimmt.
        #
        # Warum es den Knopf überhaupt braucht (Philip, 11.08.2026): Sobald
        # jemand die Kalenderfelder einmal angefasst hat, kleben sie an ihren
        # Werten — die Schnellwahl darüber ändert dann nichts mehr, und es
        # gibt keinen Weg zurück außer die Seite neu zu laden. Zurückgesetzt
        # wird auf den Zeitraum, den die Schnellwahl gerade vorgibt.
        if "p_zeit_zaehler" not in st.session_state:
            st.session_state["p_zeit_zaehler"] = 0
        n = st.session_state["p_zeit_zaehler"]

        c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
        with c1:
            sd = st.date_input("Start", value=sd_vor, min_value=mind,
                               max_value=maxd, format="DD.MM.YYYY",
                               key=f"p_sd_{n}")
        with c2:
            ed = st.date_input("Ende", value=ed_vor, min_value=mind,
                               max_value=maxd, format="DD.MM.YYYY",
                               key=f"p_ed_{n}")
        with c3:
            if st.button("Zurücksetzen", key="p_zeit_reset",
                         width="stretch",
                         help=f"Setzt Start und Ende auf die Schnellwahl "
                              f"zurück ({fmt_date_de(sd_vor)} – "
                              f"{fmt_date_de(ed_vor)})."):
                st.session_state["p_zeit_zaehler"] += 1
                st.rerun()
    else:
        sd, ed = sd_vor, ed_vor
        st.caption(f"{fmt_date_de(sd)} – {fmt_date_de(ed)}")

    # Fehlermeldung sagt, was zu tun ist, und bricht die Seite NICHT ab
    # (vorher: st.error("Start > Ende."); st.stop() → leere Seite).
    if sd > ed:
        st.error("Das Startdatum liegt nach dem Enddatum. "
                 "Bitte den Zeitraum korrigieren.")
        st.stop()

    df1=data[ps1].copy(); df1=df1.loc[(df1.index.date>=sd)&(df1.index.date<=ed)].copy(); df2=None
    if sc and ps2:
        d2r=data[ps2].copy(); d2r=d2r.loc[(d2r.index.date>=sd)&(d2r.index.date<=ed)].copy()
        # rf mitziehen damit es nach dem Join verfügbar bleibt
        cols1 = ["ret_port","ret_bm","rf"] if "rf" in df1.columns else ["ret_port","ret_bm"]
        cols2 = ["ret_port","ret_bm","rf"] if "rf" in d2r.columns else ["ret_port","ret_bm"]
        ren1 = {"ret_port":"rp1","ret_bm":"rb1","rf":"rf1"}
        ren2 = {"ret_port":"rp2","ret_bm":"rb2","rf":"rf2"}
        j = df1[cols1].rename(columns=ren1).join(d2r[cols2].rename(columns=ren2), how="inner")
        if j.empty: st.error("Kein gemeinsamer Zeitraum."); st.stop()
        df1 = j[["rp1","rb1"] + (["rf1"] if "rf1" in j.columns else [])].rename(columns={"rp1":"ret_port","rb1":"ret_bm","rf1":"rf"})
        df2 = j[["rp2","rb2"] + (["rf2"] if "rf2" in j.columns else [])].rename(columns={"rp2":"ret_port","rb2":"ret_bm","rf2":"rf"})

    sw=anlagevolumen if use_volume else 100.0
    r1=df1["ret_port"].to_numpy(float); ia1=make_index_after_fee(r1,fdec1,sw); ib1=make_index_from_returns(r1,sw)
    ia2=ib2=None
    if df2 is not None: r2=df2["ret_port"].to_numpy(float); ia2=make_index_after_fee(r2,float(fdec2),sw); ib2=make_index_from_returns(r2,sw)
    xd=[df1.index.min()-pd.Timedelta(days=1)]+list(df1.index)
    r1t=df1["ret_port"].to_numpy(float)
    sb1t=pd.Series(make_index_from_returns(r1t,100.0),index=pd.to_datetime(xd))
    sa1t=pd.Series(make_index_after_fee(r1t,fdec1,100.0),index=pd.to_datetime(xd))
    sb2t=sa2t=None
    if df2 is not None:
        r2t=df2["ret_port"].to_numpy(float)
        sb2t=pd.Series(make_index_from_returns(r2t,100.0),index=pd.to_datetime(xd))
        sa2t=pd.Series(make_index_after_fee(r2t,float(fdec2),100.0),index=pd.to_datetime(xd))
    bn1=data[ps1].attrs.get("benchmark_name","Benchmark"); bn2=data[ps2].attrs.get("benchmark_name","Benchmark") if sc and ps2 else None
    bt1=d2b.get(ds1,""); bt2=d2b.get(ds2,"") if ds2 else ""

    # ── Reihen für Heatmap und Risiko-Block (14.08.2026) ────────────────────
    # Diese Blöcke rechnen bewusst auf der VOLLEN Reihe aus `data`, nicht auf
    # df1/df2. df1/df2 sind zweifach beschnitten: auf die Zeitraum-Schnellwahl
    # und — sobald das Vergleichsportfolio läuft — per Inner-Join oben auf die
    # gemeinsamen Handelstage beider Strategien. "Muster ausgewogen cVV" (ab
    # 2009) gegen "Comdirect 100" (ab 2024) verlöre dabei fünfzehn Jahre.
    #
    # historie_beschneiden wird hier angewandt, damit die Heatmap dieselbe
    # Basis nutzt wie die Broschüre: Ohne sie stünde bei den fünf
    # cVV-Strategien eine Zelle "Dez 2008" mit genau EINEM Tag — die beiden
    # 2008er-Zeilen sind reine Indexbasis und kein Track Record.
    _voll1 = historie_beschneiden(data[ps1], ps1)
    _voll2 = historie_beschneiden(data[ps2], ps2) if sc and ps2 else None

    # Zeitraum für die Heatmap (14.08.2026). Sie folgt der Auswahl oben, aber
    # BEWUSST NICHT über sd/sd_vor: Die sind auf `mind` geklemmt, und `mind`
    # ist bei aktivem Vergleichsportfolio die SCHNITTMENGE beider Historien
    # (siehe oben). "Muster ausgewogen cVV" verlöre bei „Seit Auflage"
    # fünfzehn Jahre, sobald jemand eine junge Strategie danebenstellt.
    #
    # None heißt „Rand der jeweiligen Reihe" — jede Strategie beginnt dann an
    # ihrem eigenen ersten Monat. Der Zuschnitt selbst passiert in
    # `zeige_monatsheatmap`, damit beide Reihen ihn unabhängig bekommen.
    #
    # Gilt nur für die Ansicht „Jahr für Jahr". Die Bandbreiten-Ansicht nimmt
    # immer die letzten fünf Kalenderjahre und ignoriert die Auswahl (siehe
    # `zeige_monatsheatmap`) — sie sagt das in einer Caption auch.
    #
    # Die Ableitung stand bis zum 14.08.2026 hier inline und war damit für
    # keinen Prüfstein erreichbar; genau deshalb blieb ein Fehler darin lange
    # unbemerkt (Transferwissen #55). Sie hat jetzt einen Namen.
    _heat_von, _heat_bis, _heat_gerundet = zeitraum_fuer_heatmap(
        jahre, eigener, sd, ed, maxd)

    def _analyse_reihen(kurz=False):
        """(label, reihe, honorar[, benchmark_name, hat_benchmark]) je Strategie.

        `kurz` lässt die beiden Benchmark-Felder weg — die Drawdown-Tabelle
        braucht sie nicht.
        """
        raus = []
        for lab, reihe, fee, bmn in ((l1, _voll1, fdec1, bn1),
                                     (l2, _voll2, fdec2, bn2)):
            if reihe is None or not lab:
                continue
            if kurz:
                raus.append((lab, reihe, fee))
            else:
                hat = "ret_bm" in reihe.columns and has_benchmark(reihe["ret_bm"])
                raus.append((lab, reihe, fee, bmn or "Benchmark", bool(sb and hat)))
        return raus

    # ── rf aggregieren und rf-Index für Chart bauen ──
    rf_series_1 = df1["rf"] if "rf" in df1.columns else pd.Series(dtype=float)
    rf_pa_1 = aggregate_rf_geometric(rf_series_1, len(r1)) if not rf_series_1.empty else None
    rf_pa_2 = None
    rf_series_2 = pd.Series(dtype=float)
    if df2 is not None and "rf" in df2.columns:
        rf_series_2 = df2["rf"]
        rf_pa_2 = aggregate_rf_geometric(rf_series_2, len(r2))

    # ── Konsistenz-Hinweis Tool vs. PowerPoint (03.07.2026) ─────────────────
    # Fachliche Festlegung (Philip): Die PowerPoint-Broschüre rechnet IMMER
    # über die volle Historie mit dem Standardsatz aus dem Mapping — sie ist
    # die kanonische, reproduzierbare Basis. Die Tool-Anzeige darf davon
    # abweichen (Zeitraum-Filter, Vergleichs-Schnittmenge, editierter Satz),
    # das ist GEWOLLT — muss aber sichtbar sein, sonst wirken die Zahlen
    # "inkonsistent". Diese Caption benennt live jede aktive Abweichung.
    # FEHLENDER HONORARSATZ (Audit 14.08.2026) — muss VOR allem anderen
    # stehen. Findet der Loader keine Mapping-Zeile, rechnet die Strategie
    # mit 0 % Honorar; die Zahlen darunter waeren dann brutto, sind aber
    # ueberall als "nach Kosten" beschriftet. Frueher fiel das lautlos aus.
    _ohne_satz = strategien_ohne_honorarsatz(
        [(ds1, data.get(ps1)),
         (ds2, data.get(ps2)) if (sc and ps2) else (None, None)])
    if _ohne_satz:
        st.error(
            "**Kein Honorarsatz hinterlegt für " + " und ".join(_ohne_satz)
            + ".** Im Honorarsatz-Mapping fehlt eine Zeile zu dieser "
            "Strategie. Das Feld in der Seitenleiste ist deshalb mit 0,00 % "
            "vorbelegt — alle Zahlen unten sind damit **brutto**, obwohl sie "
            "als „nach Kosten“ beschriftet sind. Bitte den Satz von Hand "
            "eintragen oder das Mapping ergänzen.")

    _pp_abweichungen = []
    if sd > mind or ed < maxd:
        _pp_abweichungen.append(f"Zeitraum gefiltert ({fmt_date_de(sd)} – {fmt_date_de(ed)})")
    if df2 is not None:
        _pp_abweichungen.append("Vergleich aktiv → Berechnung auf gemeinsamem Zeitraum beider Portfolios")
    _fee_std_1 = float(round(fd1 * 100, 4))
    if abs(fp1 - _fee_std_1) > 1e-9:
        _pp_abweichungen.append(f"Kostensatz {ds1} manuell geändert ({fp1:.4f}% statt Standard {_fee_std_1:.4f}%)")
    if sc and ps2 and fp2 is not None:
        _fee_std_2 = float(round(fd2 * 100, 4))
        if abs(fp2 - _fee_std_2) > 1e-9:
            _pp_abweichungen.append(f"Kostensatz {ds2} manuell geändert ({fp2:.4f}% statt Standard {_fee_std_2:.4f}%)")
    if _pp_abweichungen:
        st.info("**Anzeige weicht von der PowerPoint-Basis ab** (die Broschüre rechnet immer: "
                "volle Historie, Standardsatz aus dem Mapping): " + " · ".join(_pp_abweichungen)
                + ". MwSt-Häkchen ggf. in beiden Bereichen gleich stellen.")

    # Kennzahlen
    nd1=len(r1); draf1=calc_daily_returns_after_fee(r1,fdec1); cg1=calc_cagr(ia1,nd1); vo1=calc_vola(draf1)
    ew1=float(ia1[-1]) if use_volume else None
    ia1_100=make_index_after_fee(r1,fdec1,100.0); mddv1,mddd1=calc_max_drawdown(ia1_100,xd)
    mdde1=calc_max_drawdown_euro(ia1,xd)[0] if use_volume else None
    cm1=calc_calmar_ratio(cg1,mddv1)
    sh1=calc_sharpe_excess(draf1, df1["rf"]) if ("rf" in df1.columns and df1["rf"].notna().any()) else None
    rd1,rdt1=calc_drawdown_recovery(ia1_100,xd); dur1,ds1_,de1_=calc_max_drawdown_duration(ia1_100,xd)
    cg2=vo2=ew2=mddv2=mddd2=mdde2=cm2=sh2=rd2=rdt2=dur2=ds2_=de2_=None
    if df2 is not None:
        nd2=len(r2); draf2=calc_daily_returns_after_fee(r2,float(fdec2)); cg2=calc_cagr(ia2,nd2); vo2=calc_vola(draf2)
        ew2=float(ia2[-1]) if use_volume else None
        ia2_100=make_index_after_fee(r2,float(fdec2),100.0); mddv2,mddd2=calc_max_drawdown(ia2_100,xd)
        mdde2=calc_max_drawdown_euro(ia2,xd)[0] if use_volume else None
        cm2=calc_calmar_ratio(cg2,mddv2)
        sh2=calc_sharpe_excess(draf2, df2["rf"]) if ("rf" in df2.columns and df2["rf"].notna().any()) else None
        rd2,rdt2=calc_drawdown_recovery(ia2_100,xd); dur2,ds2_,de2_=calc_max_drawdown_duration(ia2_100,xd)


    nk_label = f"nach Kosten{mwst_suffix}"

    # ── Hinweis: Strategie ohne Vergleichsmaßstab (11.08.2026) ──────────────
    # Betrifft aktuell die beiden SCHWEIZ-Strategien ("Haben keine Benchmark"
    # laut Mapping_Namen.xlsx). Die Erkennung läuft aber über has_benchmark,
    # NICHT über eine Namensliste — der Hinweis gilt damit automatisch für
    # jede weitere Strategie ohne Benchmark, ohne dass ihn jemand nachpflegt.
    #
    # Steht bewusst HIER, oberhalb der Kennzahlen: Die Kacheln zeigen gleich
    # darunter "–" statt eines Benchmark-Vergleichs, und das soll erklärt
    # sein, bevor es auffällt. Der frühere Hinweis unter dem Linien-Chart
    # erschien nur, wenn der Benchmark-Schalter überhaupt an war — war der
    # aus, blieb das "–" unkommentiert.
    _ohne_bm = [name for name, d in ((l1, df1), (l2, df2))
                if d is not None and name and "ret_bm" in d.columns
                and not has_benchmark(d["ret_bm"])]
    if _ohne_bm:
        st.caption(f"Für {' und '.join(_ohne_bm)} ist kein Vergleichsmaßstab "
                   "(Benchmark) hinterlegt. Benchmark-Kennzahlen zeigen "
                   "deshalb „–\", und im Chart wird keine Benchmark-Linie "
                   "gezeichnet.")

    # Der Kostenhinweis steht jetzt in display_metrics über jeder Kachelreihe
    # (11.08.2026) — hier wäre er die zweite Klammer in der Klammer.
    st.subheader("Kennzahlen")
    display_metrics(l1,cg1,vo1,ew1,use_volume,ad1,cm1,sh1,rf_pa_1,mwst_suffix)
    if df2 is not None and l2: display_metrics(l2,cg2,vo2,ew2,use_volume,ad2,cm2,sh2,rf_pa_2,mwst_suffix)

    # ── Anlagekriterien (NEU 10.08.2026) ──────────────────────────────────
    # Eigener Block ZWISCHEN Kennzahlen und Wertentwicklung: erst was die
    # Strategie geleistet hat, dann in welchem Rahmen sie das darf.
    # Quelle ist Mapping_Anlagekriterien.xlsx — dieselbe Datei, die den
    # Kasten auf der Struktur-Folie der Broschuere fuellt.
    # Der Strategiename steht nur dann in der Ueberschrift, wenn ein
    # Vergleichsportfolio gewaehlt ist; sonst waere nicht erkennbar, welcher
    # Banner zu welcher Strategie gehoert.
    _krit = load_anlagekriterien()
    _vergleich_aktiv = df2 is not None and l2
    zeige_anlagekriterien(ds1, _krit, mit_strategiename=bool(_vergleich_aktiv))
    if _vergleich_aktiv and ds2 != ds1:
        zeige_anlagekriterien(ds2, _krit, mit_strategiename=True)

    eff_fee_1 = fp1 * mwst_faktor  # effektive Kosten in %
    eff_fee_2 = (fp2 * mwst_faktor) if fp2 is not None else 0.0
    if use_volume: st.subheader(f"Wertentwicklung in Euro ({fmt_eur_de(anlagevolumen)})"); yl="Wert in €"
    else: st.subheader("Performance-Index (Start = 100)"); yl="Index (Start 100)"
    fig=go.Figure()

    def _add_line(x, y, name):
        """Fügt Linie + Endwert-Label hinzu. Label verschwindet mit der Linie."""
        end_val = float(y[-1])
        if use_volume:
            pct_change = (end_val / sw - 1.0) * 100
            label = f"{pct_change:+.2f}%".replace(".",",")
        else:
            label = f"{end_val:.2f}".replace(".",",")
        # Hauptlinie
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name, legendgroup=name))
        # Endwert-Label (nur letzter Punkt, gleiche legendgroup → verschwindet zusammen)
        fig.add_trace(go.Scatter(
            x=[x[-1]], y=[end_val], mode="text", text=[f"<b>{label}</b>"],
            textposition="middle right", textfont=dict(size=10),
            legendgroup=name, showlegend=False, hoverinfo="skip"))

    _add_line(xd, ia1, f"{l1} – {nk_label} ({eff_fee_1:.2f}%)")
    if ia2 is not None: _add_line(xd, ia2, f"{l2} – {nk_label} ({eff_fee_2:.2f}%)")
    if sv:
        _add_line(xd, ib1, f"{l1} – vor Kosten")
        if ib2 is not None: _add_line(xd, ib2, f"{l2} – vor Kosten")
    if sb and has_benchmark(df1["ret_bm"]):
        rbm1=df1["ret_bm"].fillna(0).to_numpy(float); ibm1=make_index_from_returns(rbm1,sw)
        _add_line(xd, ibm1, f"BM {l1}: {bn1}")
        if df2 is not None and has_benchmark(df2["ret_bm"]):
            rbm2=df2["ret_bm"].fillna(0).to_numpy(float); ibm2=make_index_from_returns(rbm2,sw)
            _add_line(xd, ibm2, f"BM {l2}: {bn2}")
    # Kein zweiter Hinweis an dieser Stelle (11.08.2026): Der Fall wird jetzt
    # EINMAL oberhalb der Kennzahlen benannt, unabhängig vom Benchmark-Schalter.
    # Hier stand bis dahin dieselbe Aussage noch einmal — bei eingeschaltetem
    # Schalter also doppelt.
    # rf-Linie (nur eine, da für gleichen Zeitraum identisch)
    rf_idx = None
    if sb_rf and not rf_series_1.empty and rf_series_1.notna().any():
        irf = make_index_from_rf(rf_series_1.fillna(0).to_numpy(float), sw)
        _add_line(xd, irf, "Risikofreier Zins")
        rf_idx = irf
    elif sb_rf:
        st.caption("Keine Daten zum risikofreien Zins für den gewählten Zeitraum verfügbar.")

    fig.update_layout(height=550,xaxis_title="Datum",xaxis=dict(tickformat="%d.%m.%Y"),yaxis_title=yl,
        yaxis=dict(tickformat=",.0f" if use_volume else None, separatethousands=True),
        legend=dict(title_text="Strategie", x=1.02, y=1, xanchor="left"),
        showlegend=True, hovermode="x unified",
        colorway=FFPB_PALETTE,
        margin=dict(r=120))

    # Deutsche Tausender-Formatierung auf Y-Achse bei Volumen
    if use_volume:
        fig.update_layout(yaxis=dict(tickformat=",.0f"))
        # Plotly nutzt Locale – wir überschreiben mit separatethousands
        fig.update_layout(separators=",.")

    st.plotly_chart(fig,config={"displayModeBar": False})
    if sb: show_benchmark_composition(l1,bt1,l2,bt2)

    if sdd:
        st.markdown("---")
        display_drawdown_metrics(l1,mddv1,mddd1,mdde1,use_volume,rd1,rdt1,dur1,ds1_,de1_,mwst_suffix)
        if df2 is not None and l2: display_drawdown_metrics(l2,mddv2,mddd2,mdde2,use_volume,rd2,rdt2,dur2,ds2_,de2_,mwst_suffix)
        fdd=go.Figure()
        if use_volume:
            fdd.add_trace(go.Scatter(x=xd,y=drawdown_euro_from_index(ia1),mode="lines",name=f"{l1} – DD € (nK)"))
            if df2 is not None: fdd.add_trace(go.Scatter(x=xd,y=drawdown_euro_from_index(ia2),mode="lines",name=f"{l2} – DD € (nK)"))
            fdd.update_layout(height=350,xaxis_title="Datum",xaxis=dict(tickformat="%d.%m.%Y"),yaxis_title="DD in €",yaxis=dict(tickformat=",.0f"),hovermode="x unified",colorway=FFPB_PALETTE)
        else:
            fdd.add_trace(go.Scatter(x=xd,y=drawdown_from_index(ia1_100),mode="lines",name=f"{l1} – DD (nK)"))
            if df2 is not None: fdd.add_trace(go.Scatter(x=xd,y=drawdown_from_index(ia2_100),mode="lines",name=f"{l2} – DD (nK)"))
            fdd.update_layout(height=350,xaxis_title="Datum",xaxis=dict(tickformat="%d.%m.%Y"),yaxis_title="Drawdown",hovermode="x unified",colorway=FFPB_PALETTE)
        st.plotly_chart(fdd,config={"displayModeBar": False})
        zeige_drawdown_tabelle(_analyse_reihen(kurz=True))

    dfr=None
    if stbl:
        sl=f"Seit: {fmt_date_de(df1.index.min())}"
        dfr=build_rolling_table(sb1t,sa1t,l1,sb2t,sa2t,l2,sl)
        st.subheader("Wertentwicklung rollierend"); st.dataframe(dfr)

    if sheat:
        _vgl=None
        if sheat_cmp and sc and ps2:
            _vgl=(l2, _voll2, fdec2)
        zeige_monatsheatmap(l1,_voll1,fdec1,gegen_benchmark=sheat_bm,
                            benchmark_name=bn1,vergleich=_vgl,
                            mwst_suffix=mwst_suffix,
                            von=_heat_von,bis=_heat_bis,
                            gerundet=_heat_gerundet)

    if srisk:
        zeige_risiko_ueberblick(_analyse_reihen(),mwst_suffix=mwst_suffix)

    if sbar:
        st.markdown("---"); st.subheader("Performance blockweise")
        bl,br=st.columns([1,3])
        with bl:
            bm=st.radio("Zeitraum",["Kalenderjahre","Quartale","Benutzerdefiniert"],key="p_bm_r",
                help=("Wie die Balken gruppiert werden. Benutzerdefiniert "
                      "teilt den gewählten Zeitraum in gleich lange Blöcke."))
            csb=ceb=None
            if bm=="Benutzerdefiniert":
                csb=st.date_input("Von",value=sd,min_value=mind,max_value=maxd,format="DD.MM.YYYY",key="p_bv")
                ceb=st.date_input("Bis",value=ed,min_value=mind,max_value=maxd,format="DD.MM.YYYY",key="p_bb")
        tm={"Kalenderjahre":"PERFORMANCE P.A. (NACH KOSTEN)","Quartale":"PERFORMANCE QUARTALE (NACH KOSTEN)","Benutzerdefiniert":"PERFORMANCE (NACH KOSTEN) – BENUTZERDEFINIERT"}
        def _rb(dfs,fee,lab,bname,btxt,cont,suffix="1"):
            bd=compute_bar_data(dfs,fee,bm,lab,csb,ceb)
            if bd.empty: cont.info(f"Keine Daten für {lab}."); return
            btt=f"{tm[bm]} – {lab}"
            cont.plotly_chart(build_bar_chart(bd,lab,bname,title=btt),config={"displayModeBar": False},key=f"bar_chart_{suffix}")
            show_tbl = cont.checkbox(f"Tabelle anzeigen – {lab}", value=False, key=f"bar_tbl_{lab}_{suffix}")
            if show_tbl:
                cp=f"{lab} (nach Kosten)"; dp=bd[["label",cp,"ret_bm_raw"]].copy()
                dp[cp]=dp[cp].map(lambda x:f"{x:+.2f}%"); dp["ret_bm_raw"]=dp["ret_bm_raw"].map(lambda x:f"{x:+.2f}%" if pd.notna(x) else "–")
                dp.columns=["Zeitraum",f"{lab} nK",bname]; cont.dataframe(dp,hide_index=True)
        with br:
            _rb(df1,fdec1,l1,bn1,bt1,st.container(),suffix="p1")
            # Benchmark-Zusammensetzung nur, wenn sie NICHT schon oben am
            # Performance-Chart steht (11.08.2026). Bis dahin erschien sie
            # doppelt und wortgleich, sobald "Benchmark" und "Balken-Chart"
            # aktiv waren — beide sind standardmaessig an, der Doppel-Eintrag
            # war also der Normalfall. Ist der Benchmark-Schalter aus, gehoert
            # sie hierher: die Balken zeigen die Benchmark trotzdem.
            if not sb:
                show_benchmark_composition(l1,bt1)
            if df2 is not None and fdec2 is not None and ps2:
                st.markdown("---"); _rb(df2,fdec2,l2,bn2 or "BM",bt2 or "",st.container(),suffix="p2")
                if not sb:
                    show_benchmark_composition(l2,bt2)

    # Disclaimer
    st.markdown("---")
    st.markdown("##### Disclaimer")
    st.markdown(
        "Die angegebenen Werte beziehen sich auf die historische Wertentwicklung. "
        "Der Wert sowie die Erträge einer Kapitalanlage können sowohl steigen als auch fallen. "
        "Eine positive Wertentwicklung in der Vergangenheit stellt keine Garantie für zukünftige Entwicklungen dar. "
        "Die Wertentwicklung wird in Euro (€) gemessen."
    )
    st.markdown(
        "Die ausgewiesene Performance wird auf täglicher Basis berechnet. "
        "Der jährliche Honorarsatz wird dabei in eine äquivalente tägliche Belastung umgerechnet und unter "
        "Berücksichtigung des Zinseszinseffekts taggenau von der Performance abgezogen; "
        "eine halbjährliche Berücksichtigung erfolgt nicht."
    )
    st.markdown(
        "Dieses Performancetool dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. "
        "Alle Berechnungen sind unverbindlich und erfolgen ohne Gewähr."
    )
    st.markdown(f"**Quelle:** Infront & eigene Berechnungen, Stand: {fmt_date_de(maxd)}")
    st.markdown("**Ansprechpartner:** PBAM")


# ===========================================================================
# ANSICHT 3: STRATEGIEVERGLEICH  (NEU 18.08.2026)
# ===========================================================================
# Bewusst VOR der Portfolioanalyse im Quelltext, damit deren `else` der
# Auffangzweig bleibt: Ein unbekannter Wert in `nav_view` landet dann wie
# bisher auf der Portfolioanalyse und nicht auf einer leeren Seite.
#
# Die Ansicht braucht KEINE eigene Datenbereitstellung — die Zeitreihen aller
# Strategien liegen seit dem Navigations-Umbau zentral bereit (siehe oben).
elif ansicht == _VIEW_VGL:
    if perf_daten_fehler:
        st.error(perf_daten_fehler)
    else:
        _reihen_vgl = []
        for _name in dn_ordered:
            _df = data.get(d2c.get(_name))
            if _df is None or len(_df) < 2:
                continue
            _reihen_vgl.append((_name, _df,
                                float(_df["fee_default"].iloc[0]),
                                familie_fuer_strategie(name_mapping, _name)))

        # DERSELBE SCHUTZ WIE IN DER PERFORMANCE-ANSICHT (Audit-Befund B6).
        # Fehlt einer Strategie der Honorarsatz, faellt der Loader still auf
        # 0,0 zurueck — ihr Punkt laege dann zu HOCH, und zwar unter einer
        # Achse, die "nach Kosten" sagt. Hier waere das sogar heimtueckischer
        # als drueben: In der Punktwolke steht kein Eingabefeld daneben, in
        # dem man die 0,00 % sehen koennte.
        _ohne_satz = strategien_ohne_honorarsatz(
            [(_name, _df) for _name, _df, _, _ in _reihen_vgl])
        if _ohne_satz:
            st.error(
                "**Kein Honorarsatz hinterlegt für " + ", ".join(_ohne_satz)
                + ".** Im Honorarsatz-Mapping fehlt eine Zeile zu dieser "
                "Strategie. Ihr Punkt wird deshalb **brutto** gerechnet und "
                "liegt zu hoch, obwohl die Achse „nach Kosten“ sagt. Bitte "
                "das Mapping ergänzen.")

        # BESTANDSDATEN NUR HIER, nicht zentral (18.08.2026): Die beiden
        # anderen Ansichten brauchen sie nicht, und die Portfolioanalyse holt
        # sie ohnehin selbst. `build_pf_data` traegt `@st.cache_data`, ein
        # zweiter Aufruf mit derselben Dateiliste kostet also nichts.
        #
        # FAELLT DAS AUS, FAELLT NUR DER UNTERE TEIL DER ANSICHT AUS. Die
        # Punktwolke haengt an den Zeitreihen und ist davon unberuehrt --
        # deshalb hier ein weiches `None` statt einer Fehlermeldung, die die
        # ganze Ansicht abschaltet.
        _bestaende = None
        _pf_stichtag = None
        try:
            _tag_pf = detect_newest_date_tag(DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS)
            _pf_dateien = load_pf_csvs(DATA_FOLDER_PF, _tag_pf)
            if _pf_dateien:
                _pf_daten = build_pf_data(_pf_dateien)
                # Dieselben Anzeigenamen wie oben: Die Spalte "Portfolio Name"
                # ist in Daten/ und Daten_PF/ identisch, deshalb traegt
                # dasselbe Mapping beide Seiten.
                _pf_namen, _pf_d2c, _ = build_name_lookups(
                    name_mapping, set(_pf_daten.keys()))
                _bestaende = {n: _pf_daten[_pf_d2c[n]] for n in _pf_namen}
                for _df_pf in _bestaende.values():
                    if "Auswertungsdatum" in _df_pf.columns and len(_df_pf):
                        _pf_stichtag = _df_pf["Auswertungsdatum"].dropna().max()
                        break
        except Exception as _ex:
            st.caption(f"Bestandsdaten nicht lesbar: {type(_ex).__name__}")

        zeige_strategievergleich(_reihen_vgl, tuple(VORLAGEN_FAMILIEN),
                                 bestaende=_bestaende,
                                 auswertungsdatum=_pf_stichtag)


# ===========================================================================
# ANSICHT 2: PORTFOLIOANALYSE
# ===========================================================================
else:
    render_portfolioanalyse(name_mapping, anlagevolumen)
