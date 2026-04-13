# streamlit_app.py
"""
Hauptdatei: Login, Sidebar, Tabs (Performance + Portfolioanalyse).
Performance-Code bleibt inline (bewährt), Portfolioanalyse aus Modul.
"""
import os
import re
import glob
import io
import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, PageBreak, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from PIL import Image as PILImage

from modules.shared import (
    LOGO_FILENAME, FFPB_DARK, FFPB_GOLD, FFPB_LIGHT, FFPB_BLUE2,
    MAPPING_PATH, NAME_MAPPING_PATH, DATA_FOLDER, EXCLUDE_SUBSTRINGS,
    PDF_FONT, PDF_FONT_BOLD,
    check_login, fmt_date_de, fmt_pct_de, fmt_eur_de,
    detect_newest_date_tag, load_mapping, load_name_mapping,
    build_name_lookups, get_logo_aspect, get_logo_path,
)
from modules.portfolioanalyse import render_portfolioanalyse
from modules.portfolio_builder import render_portfolio_builder


# ==========================================================================
# PERFORMANCE HELPERS (bewährter Code, inline)
# ==========================================================================

def annual_fee_to_daily_drag(fee_pa_decimal): return (1.0 + fee_pa_decimal) ** (1 / 365) - 1

def make_index_from_returns(d_returns_decimal, startwert=100.0):
    idx = np.empty(len(d_returns_decimal) + 1, dtype=float); idx[0] = startwert
    for i, d in enumerate(d_returns_decimal, start=1): idx[i] = idx[i-1] * (1.0 + d)
    return idx

def make_index_after_fee(d_returns_decimal, fee_pa_decimal, startwert=100.0):
    e = annual_fee_to_daily_drag(fee_pa_decimal)
    idx = np.empty(len(d_returns_decimal) + 1, dtype=float); idx[0] = startwert
    for i, d in enumerate(d_returns_decimal, start=1): idx[i] = idx[i-1] * (1.0 + (d - e))
    return idx

def drawdown_from_index(idx):
    peak = np.maximum.accumulate(idx); return (idx / peak) - 1.0

def drawdown_euro_from_index(idx):
    peak = np.maximum.accumulate(idx); return idx - peak

def to_decimal_interval(series_float):
    x = series_float.to_numpy(dtype=float); ax = np.nan_to_num(np.abs(x), nan=0.0)
    if ax.max() > 1.0 or np.median(ax) > 0.2: x = x / 100.0
    return x

def calc_cagr(idx_after, n_days):
    if n_days <= 0 or idx_after[0] == 0: return None
    return (idx_after[-1] / idx_after[0]) ** (365.0 / n_days) - 1.0

def calc_vola(daily_returns_after_fee):
    if len(daily_returns_after_fee) < 2: return None
    return float(np.std(daily_returns_after_fee, ddof=1) * np.sqrt(365))

def calc_daily_returns_after_fee(d_returns_decimal, fee_pa_decimal):
    return d_returns_decimal - annual_fee_to_daily_drag(fee_pa_decimal)

def calc_max_drawdown(idx_after, dates_list):
    dd = drawdown_from_index(idx_after); mi = np.argmin(dd)
    return float(dd[mi]), dates_list[mi]

def calc_max_drawdown_euro(idx_after, dates_list):
    dd = drawdown_euro_from_index(idx_after); mi = np.argmin(dd)
    return float(dd[mi]), dates_list[mi]

def calc_calmar_ratio(cagr, max_dd):
    if cagr is None or max_dd is None or max_dd == 0: return None
    return cagr / abs(max_dd)

def calc_drawdown_recovery(idx_after, dates_list):
    dd = drawdown_from_index(idx_after); mi = np.argmin(dd)
    for i in range(mi+1, len(dd)):
        if dd[i] >= 0.0:
            rd = dates_list[i]; td = dates_list[mi]
            return (rd - td).days if isinstance(rd, pd.Timestamp) else i - mi, rd
    return None, None

def calc_max_drawdown_duration(idx_after, dates_list):
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
    periods = [("ytd", pd.Timestamp(end_ts.year,1,1)),("1 Jahre", end_ts-pd.DateOffset(years=1)),
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

def calc_period_return(returns): return float(np.prod(1.0 + returns) - 1.0)
def calc_period_return_after_fee(returns, fee_pa_decimal):
    e = annual_fee_to_daily_drag(fee_pa_decimal); return float(np.prod(1.0 + (returns - e)) - 1.0)

def compute_bar_data(df, fee_dec, mode, label, custom_start=None, custom_end=None):
    rows = []
    def _add(pl, sub):
        if sub.empty: return
        rp = sub["ret_port"].fillna(0.0).to_numpy(float); rb = sub["ret_bm"].fillna(0.0).to_numpy(float)
        has_bm = sub["ret_bm"].notna().any()
        rows.append({"label": pl, f"{label} (nach Kosten)": calc_period_return_after_fee(rp, fee_dec)*100,
            "ret_bm_raw": calc_period_return(rb)*100 if has_bm else None})
    if mode == "Kalenderjahre":
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
    BG="#1B3A5C"; fig=go.Figure(); cp1=f"{label_1} (nach Kosten)"
    if cp1 in bar_df1.columns:
        v=bar_df1[cp1].tolist()
        fig.add_trace(go.Bar(name=cp1,x=bar_df1["label"],y=v,marker_color="#B8973A",text=[f"{x:+.2f}%" for x in v],textposition="outside",textfont=dict(size=11,color="white"),cliponaxis=False))
    if "ret_bm_raw" in bar_df1.columns and bar_df1["ret_bm_raw"].notna().any():
        bv=bar_df1["ret_bm_raw"].tolist()
        fig.add_trace(go.Bar(name=bench_name_1,x=bar_df1["label"],y=bv,marker_color="#A8CBE8",text=[f"{x:+.2f}%" if pd.notna(x) else "" for x in bv],textposition="outside",textfont=dict(size=11,color="white"),cliponaxis=False))
    if bar_df2 is not None and label_2:
        cp2=f"{label_2} (nach Kosten)"
        if cp2 in bar_df2.columns:
            v2=bar_df2[cp2].tolist()
            fig.add_trace(go.Bar(name=cp2,x=bar_df2["label"],y=v2,marker_color="#2C5F8A",text=[f"{x:+.2f}%" for x in v2],textposition="outside",textfont=dict(size=11,color="white"),cliponaxis=False))
        if bench_name_2 and bench_name_2!=bench_name_1 and "ret_bm_raw" in bar_df2.columns and bar_df2["ret_bm_raw"].notna().any():
            bv2=bar_df2["ret_bm_raw"].tolist()
            fig.add_trace(go.Bar(name=bench_name_2,x=bar_df2["label"],y=bv2,marker_color="#7FB5D5",text=[f"{x:+.2f}%" if pd.notna(x) else "" for x in bv2],textposition="outside",textfont=dict(size=11,color="white"),cliponaxis=False))
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
        xaxis=dict(tickfont=dict(color="white",size=12),showgrid=False,zeroline=False,linecolor="#3A5A7C"),
        yaxis=dict(range=[ymi,yma],tickformat=".1f",ticksuffix="%",tickfont=dict(color="white",size=11),gridcolor="#2A4A6C",zeroline=False),
        legend=dict(font=dict(color="white",size=11),bgcolor="rgba(0,0,0,0)",orientation="h",y=-0.18),
        margin=dict(t=55,b=75,l=65,r=25))
    return fig

def show_benchmark_composition(dn, bt, dn2=None, bt2=None):
    if bt and str(bt).strip() and str(bt).strip().lower() not in ("","nan","haben keine benchmark"):
        st.caption(f"**Zusammensetzung Benchmark {dn}:** {bt}")
    if dn2 and bt2 and str(bt2).strip() and str(bt2).strip().lower() not in ("","nan","haben keine benchmark"):
        st.caption(f"**Zusammensetzung Benchmark {dn2}:** {bt2}")

def display_metrics(label, cagr, vola, endwert, use_volume, auflagedatum, calmar, mwst_suffix=""):
    nk = f"nach Kosten{mwst_suffix}"
    st.markdown(f"**{label}**")
    n=4+(1 if use_volume else 0); cols=st.columns(n)
    with cols[0]: st.metric("Auflagedatum im PM",fmt_date_de(auflagedatum),help="Erster verfügbarer Datenpunkt der Strategie im Portfoliomanagement.")
    with cols[1]: st.metric(f"⌀ Rendite p.a. ({nk})",fmt_pct_de(cagr) if cagr else "–",help="Annualisierte Rendite nach Kosten (CAGR): (Endwert/Startwert)^(365/Tage) − 1.")
    with cols[2]: st.metric(f"Volatilität p.a. ({nk})",fmt_pct_de(vola) if vola else "–",help="Annualisierte Schwankungsbreite: Standardabweichung der Tagesrenditen × √365.")
    with cols[3]: st.metric(f"Calmar Ratio ({nk})",f"{calmar:.2f}".replace(".",",") if calmar else "–",help="CAGR / |Max Drawdown|. Je höher, desto besser die risikoadjustierte Rendite.")
    if use_volume and endwert:
        with cols[4]: st.metric(f"Endwert ({nk})",fmt_eur_de(endwert),help="Aktueller Wert des Anlagevolumens nach Abzug aller Kosten.")

def display_drawdown_metrics(label, mddv, mddd, mdde, uv, rd, rdate, mddur, dds, dde, mwst_suffix=""):
    nk = f"nach Kosten{mwst_suffix}"
    st.markdown(f"**{label} ({nk})**")
    rv=f"{rd} Tage" if rd else "noch nicht erholt"; rh=f" Erholt am {fmt_date_de(rdate)}." if rd else ""
    cols=st.columns(4)
    with cols[0]:
        st.metric(f"Max. Drawdown ({nk})",fmt_pct_de(mddv),help=f"Größter Verlust vom Höchststand. Tiefpunkt am {fmt_date_de(mddd)}.")
        if uv and mdde is not None:
            st.caption(f"entspricht {fmt_eur_de(mdde)}")
    with cols[1]: st.metric("Recovery",rv,help=f"Tage vom Tief bis zur Erholung.{rh}")
    with cols[2]: st.metric("Längste Drawdown-Phase",f"{mddur} Tage" if mddur>0 else "–",help=f"Längster Zeitraum unter Peak: {fmt_date_de(dds)} – {fmt_date_de(dde)}." if mddur>0 else "Kein Drawdown.")
    with cols[3]: st.metric("Drawdown-Tief am",fmt_date_de(mddd),help="Datum des tiefsten Drawdown-Punkts.")

# PDF helpers for performance
def _mpl_line_chart(x_dates, traces, y_label, title, use_volume, startwert=100.0):
    fig,ax=plt.subplots(figsize=(10,4.5)); fig.patch.set_facecolor(FFPB_DARK); ax.set_facecolor(FFPB_DARK)
    colors=[FFPB_GOLD,FFPB_BLUE2,"#E8A838","#5BA0D0",FFPB_LIGHT,"#7FB5D5","#C4C4C4","#F0C070"]
    for i,(l,y) in enumerate(traces): ax.plot(x_dates,y,label=l,color=colors[i%len(colors)],linewidth=1.3)

    # Endwerte am rechten Rand jeder Linie
    for i,(l,y) in enumerate(traces):
        end_val = float(y[-1])
        if use_volume:
            pct = (end_val / startwert - 1.0) * 100
            label = f"{pct:+.2f}%".replace(".",",")
        else:
            label = f"{end_val:.2f}".replace(".",",")
        ax.annotate(label, xy=(x_dates[-1], end_val), xytext=(8, 0),
            textcoords="offset points", fontsize=7, color=colors[i%len(colors)],
            fontweight="bold", va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=FFPB_DARK, edgecolor=colors[i%len(colors)], alpha=0.8))

    ax.set_title(title,color="white",fontsize=11,fontweight="bold",loc="left")
    ax.set_ylabel(y_label,color="white",fontsize=9); ax.tick_params(colors="white",labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y")); ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=30)
    for s in ax.spines.values(): s.set_color("#3A5A7C")
    ax.grid(axis="y",color="#2A4A6C",linewidth=0.5)
    ax.legend(fontsize=7,facecolor=FFPB_DARK,edgecolor="#3A5A7C",labelcolor="white",loc="upper left")
    if use_volume: ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:,.0f} €"))
    buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=180,bbox_inches="tight",facecolor=fig.get_facecolor()); plt.close(fig); buf.seek(0); return buf

def _mpl_drawdown_chart(x_dates, traces, title, use_volume):
    fig,ax=plt.subplots(figsize=(10,3)); fig.patch.set_facecolor(FFPB_DARK); ax.set_facecolor(FFPB_DARK)
    colors=[FFPB_GOLD,FFPB_BLUE2]
    for i,(l,y) in enumerate(traces):
        ax.fill_between(x_dates,y,alpha=0.3,color=colors[i%2]); ax.plot(x_dates,y,label=l,color=colors[i%2],linewidth=1.2)
    ax.set_title(title,color="white",fontsize=11,fontweight="bold",loc="left")
    ax.set_ylabel("Drawdown",color="white",fontsize=9); ax.tick_params(colors="white",labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y")); fig.autofmt_xdate(rotation=30)
    if use_volume: ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:,.0f} €"))
    else: ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:.0%}"))
    for s in ax.spines.values(): s.set_color("#3A5A7C")
    ax.grid(axis="y",color="#2A4A6C",linewidth=0.5)
    ax.legend(fontsize=7,facecolor=FFPB_DARK,edgecolor="#3A5A7C",labelcolor="white")
    buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=180,bbox_inches="tight",facecolor=fig.get_facecolor()); plt.close(fig); buf.seek(0); return buf

def _mpl_bar_chart(bar_df, label, bench_name, title):
    fig,ax=plt.subplots(figsize=(10,4)); fig.patch.set_facecolor(FFPB_DARK); ax.set_facecolor(FFPB_DARK)
    labels=bar_df["label"].tolist(); cp=f"{label} (nach Kosten)"
    pv=bar_df[cp].tolist() if cp in bar_df.columns else []
    bv=bar_df["ret_bm_raw"].tolist() if "ret_bm_raw" in bar_df.columns else []; hb=any(pd.notna(v) for v in bv)
    x=np.arange(len(labels)); w=0.35
    if pv:
        o=-w/2 if hb else 0; b1=ax.bar(x+o,pv,w if hb else w*1.5,label=f"{label} (nach Kosten)",color=FFPB_GOLD)
        for b,v in zip(b1,pv): ax.text(b.get_x()+b.get_width()/2,b.get_height(),f"{v:+.2f}%",ha="center",va="bottom" if v>=0 else "top",fontsize=7,color="white")
    if hb:
        bc=[v if pd.notna(v) else 0 for v in bv]; b2=ax.bar(x+w/2,bc,w,label=bench_name,color=FFPB_LIGHT)
        for b,v,o2 in zip(b2,bc,bv):
            if pd.notna(o2): ax.text(b.get_x()+b.get_width()/2,b.get_height(),f"{v:+.2f}%",ha="center",va="bottom" if v>=0 else "top",fontsize=7,color="white")
    ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=8,color="white",rotation=30,ha="right")
    ax.set_title(title,color="white",fontsize=10,fontweight="bold",loc="left"); ax.axhline(y=0,color="white",linewidth=0.5)
    ax.tick_params(colors="white",labelsize=8); ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:.1f}%"))
    for s in ax.spines.values(): s.set_color("#3A5A7C")
    ax.grid(axis="y",color="#2A4A6C",linewidth=0.5); ax.legend(fontsize=7,facecolor=FFPB_DARK,edgecolor="#3A5A7C",labelcolor="white")
    buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=180,bbox_inches="tight",facecolor=fig.get_facecolor()); plt.close(fig); buf.seek(0); return buf

def generate_perf_pdf(logo_path, label_1, label_2, bench_name_1, bench_name_2, bench_text_1, bench_text_2,
    fee_pct_1, fee_pct_2, anlagevolumen, use_volume, start_date, end_date, x_dates, line_traces, y_label,
    show_drawdown, dd_traces, show_table, df_roll, show_bar, bar_data_list, metrics_data, mwst_suffix=""):
    nk = f"nach Kosten{mwst_suffix}"
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,topMargin=15*mm,bottomMargin=15*mm,leftMargin=15*mm,rightMargin=15*mm)
    styles=getSampleStyleSheet()
    st_t=ParagraphStyle("T",parent=styles["Title"],fontName=PDF_FONT_BOLD,textColor=HexColor(FFPB_DARK),fontSize=16,spaceAfter=6)
    st_s=ParagraphStyle("S",parent=styles["Heading2"],fontName=PDF_FONT_BOLD,textColor=HexColor(FFPB_DARK),fontSize=12,spaceAfter=4,spaceBefore=10)
    st_n=ParagraphStyle("N",parent=styles["Normal"],fontName=PDF_FONT,textColor=HexColor("#333333"),fontSize=9,leading=12)
    st_sm=ParagraphStyle("SM",parent=styles["Normal"],fontName=PDF_FONT,textColor=HexColor("#666666"),fontSize=7.5,leading=10)
    la=get_logo_aspect(logo_path); story=[]
    if logo_path and os.path.exists(logo_path):
        lw=50*mm; story.append(RLImage(logo_path,width=lw,height=lw*la)); story.append(Spacer(1,4*mm))
    story.append(Paragraph("Performancevergleich",st_t))
    story.append(HRFlowable(width="100%",thickness=1,color=HexColor(FFPB_DARK))); story.append(Spacer(1,3*mm))
    ml=[f"<b>Portfolio:</b> {label_1}"]
    if label_2: ml.append(f"<b>Vergleich:</b> {label_2}")
    ml.append(f"<b>Zeitraum:</b> {fmt_date_de(start_date)} – {fmt_date_de(end_date)}")
    ml.append(f"<b>Kosten {label_1}:</b> {fee_pct_1:.2f}% p.a.{mwst_suffix}")
    if label_2 and fee_pct_2 is not None: ml.append(f"<b>Kosten {label_2}:</b> {fee_pct_2:.2f}% p.a.{mwst_suffix}")
    if use_volume: ml.append(f"<b>Anlagevolumen:</b> {fmt_eur_de(anlagevolumen)}")
    ml.append(f"<b>Quelle:</b> Infront &amp; eigene Berechnungen, Stand: {fmt_date_de(end_date)}")
    for l in ml: story.append(Paragraph(l,st_n))
    story.append(Spacer(1,4*mm))
    story.append(Paragraph(f"Kennzahlen ({nk})",st_s))
    for m in metrics_data:
        p=[f"<b>{m['label']}:</b>"]
        if m.get("auflagedatum"): p.append(f"Auflage: {fmt_date_de(m['auflagedatum'])}")
        if m.get("cagr") is not None: p.append(f"CAGR: {fmt_pct_de(m['cagr'])}")
        if m.get("vola") is not None: p.append(f"Vola: {fmt_pct_de(m['vola'])}")
        if m.get("calmar") is not None: p.append(f"Calmar: {m['calmar']:.2f}".replace(".",","))
        if use_volume and m.get("endwert"): p.append(f"Endwert: {fmt_eur_de(m['endwert'])}")
        if m.get("max_dd_val") is not None:
            ds=f"Max DD: {fmt_pct_de(m['max_dd_val'])} am {fmt_date_de(m['max_dd_date'])}"
            if use_volume and m.get("max_dd_eur"): ds+=f" ({fmt_eur_de(m['max_dd_eur'])})"
            p.append(ds)
        if m.get("recovery_days"): p.append(f"Recovery: {m['recovery_days']} Tage")
        elif m.get("max_dd_val") is not None: p.append("Recovery: n.n. erholt")
        if m.get("max_dd_dur") and m["max_dd_dur"]>0: p.append(f"Längste DD: {m['max_dd_dur']} Tage")
        story.append(Paragraph(" | ".join(p),st_n))
    story.append(Spacer(1,5*mm))
    story.append(Paragraph("Performance-Index",st_s))
    lt=f"Wertentwicklung ({fmt_eur_de(anlagevolumen)})" if use_volume else "Performance-Index (Start = 100)"
    sw_pdf = anlagevolumen if use_volume else 100.0
    story.append(RLImage(_mpl_line_chart(x_dates,line_traces,y_label,lt,use_volume,sw_pdf),width=170*mm,height=80*mm))
    story.append(Spacer(1,2*mm))
    if bench_text_1 and str(bench_text_1).strip().lower() not in ("","nan","haben keine benchmark"):
        story.append(Paragraph(f"<b>BM {label_1}:</b> {bench_text_1}",st_sm))
    if label_2 and bench_text_2 and str(bench_text_2).strip().lower() not in ("","nan","haben keine benchmark"):
        story.append(Paragraph(f"<b>BM {label_2}:</b> {bench_text_2}",st_sm))
    if show_drawdown and dd_traces:
        story.append(Spacer(1,4*mm)); ddt="Drawdown in €" if use_volume else "Drawdown"
        story.append(Paragraph(ddt,st_s))
        story.append(RLImage(_mpl_drawdown_chart(x_dates,dd_traces,ddt,use_volume),width=170*mm,height=60*mm))
    if show_table and df_roll is not None and not df_roll.empty:
        story.append(PageBreak())
        if logo_path and os.path.exists(logo_path): lws=35*mm; story.append(RLImage(logo_path,width=lws,height=lws*la)); story.append(Spacer(1,3*mm))
        story.append(Paragraph("Wertentwicklung rollierend",st_s)); story.append(Spacer(1,2*mm))
        hdr=[str(c) if isinstance(c,str) else f"{c[0]}\n{c[1]}" for c in df_roll.columns]
        td=[hdr]+df_roll.values.tolist(); nc=len(hdr); fw=45*mm; ow=(170*mm-fw)/max(nc-1,1); cw=[fw]+[ow]*(nc-1)
        t=Table(td,colWidths=cw,repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),HexColor(FFPB_DARK)),("TEXTCOLOR",(0,0),(-1,0),white),
            ("FONTSIZE",(0,0),(-1,-1),7),("FONTNAME",(0,0),(-1,0),PDF_FONT_BOLD),("ALIGN",(1,0),(-1,-1),"RIGHT"),
            ("ALIGN",(0,0),(0,-1),"LEFT"),("GRID",(0,0),(-1,-1),0.5,HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[white,HexColor("#F5F5F5")]),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)])); story.append(t)
    if show_bar and bar_data_list:
        story.append(PageBreak())
        if logo_path and os.path.exists(logo_path): lws=35*mm; story.append(RLImage(logo_path,width=lws,height=lws*la)); story.append(Spacer(1,3*mm))
        story.append(Paragraph("Performance blockweise",st_s))
        for bd,bl,bb,bt2,bbt in bar_data_list:
            if bd.empty: continue
            story.append(Spacer(1,3*mm)); story.append(RLImage(_mpl_bar_chart(bd,bl,bb,bt2),width=170*mm,height=75*mm))
            story.append(Spacer(1,2*mm))
            if bbt and str(bbt).strip().lower() not in ("","nan","haben keine benchmark"):
                story.append(Paragraph(f"<b>BM {bl}:</b> {bbt}",st_sm))

    # ── Disclaimer ──
    story.append(PageBreak())
    if logo_path and os.path.exists(logo_path):
        lws=35*mm; story.append(RLImage(logo_path,width=lws,height=lws*la)); story.append(Spacer(1,3*mm))
    story.append(Paragraph("Disclaimer",st_s))
    story.append(Spacer(1,3*mm))

    disclaimer_texts = [
        "Die angegebenen Werte beziehen sich auf die historische Wertentwicklung. "
        "Der Wert sowie die Erträge einer Kapitalanlage können sowohl steigen als auch fallen. "
        "Eine positive Wertentwicklung in der Vergangenheit stellt keine Garantie für zukünftige "
        "Entwicklungen dar. Die Wertentwicklung wird in Euro (€) gemessen.",

        "Die ausgewiesene Performance wird auf täglicher Basis berechnet. "
        "Der jährliche Honorarsatz wird dabei in eine äquivalente tägliche Belastung umgerechnet "
        "und unter Berücksichtigung des Zinseszinseffekts taggenau von der Performance abgezogen; "
        "eine halbjährliche Berücksichtigung erfolgt nicht.",

        "Dieses Performancetool dient ausschließlich der unverbindlichen Veranschaulichung im "
        "Beratungsgespräch. Alle Berechnungen sind unverbindlich und ohne Gewähr.",
    ]
    for txt in disclaimer_texts:
        story.append(Paragraph(txt, st_n))
        story.append(Spacer(1, 2*mm))

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"<b>Quelle:</b> Infront &amp; eigene Berechnungen, Stand: {fmt_date_de(end_date)}", st_n))
    story.append(Paragraph("<b>Ansprechpartner:</b> PBAM", st_n))

    # ── Glossar ──
    story.append(PageBreak())
    if logo_path and os.path.exists(logo_path):
        lws=35*mm; story.append(RLImage(logo_path,width=lws,height=lws*la)); story.append(Spacer(1,3*mm))
    story.append(Paragraph("Glossar – Kennzahlen",st_s))
    story.append(Spacer(1,3*mm))

    glossar = [
        ("Auflagedatum im PM",
         "Erster verfügbarer Datenpunkt der Strategie im Portfoliomanagement. "
         "Ab diesem Datum liegen historische Performancedaten vor."),
        ("CAGR (⌀ Rendite p.a.)",
         "Compound Annual Growth Rate – die annualisierte Rendite nach Abzug aller Kosten. "
         "Berechnung: (Endwert / Startwert)^(365 / Anzahl Tage) − 1. "
         "Gibt die durchschnittliche jährliche Wertentwicklung über den gewählten Zeitraum an."),
        ("Volatilität p.a.",
         "Annualisierte Schwankungsbreite der täglichen Renditen nach Kosten. "
         "Berechnung: Standardabweichung der Tagesrenditen × √365. "
         "Je höher die Volatilität, desto stärker schwankt der Portfoliowert."),
        ("Calmar Ratio",
         "Verhältnis von annualisierter Rendite (CAGR) zum maximalen Drawdown. "
         "Berechnung: CAGR / |Max. Drawdown|. "
         "Je höher der Wert, desto besser die risikoadjustierte Rendite. "
         "Ein Wert > 1 bedeutet, dass die Rendite den größten Verlust übersteigt."),
        ("Maximaler Drawdown",
         "Größter Verlust vom Höchststand bis zum Tiefpunkt im gewählten Zeitraum. "
         "Angabe in Prozent (und Euro, wenn ein Anlagevolumen eingegeben wurde). "
         "Zeigt das Worst-Case-Verlustrisiko der Strategie."),
        ("Recovery (Erholungsdauer)",
         "Anzahl der Tage vom Drawdown-Tief bis zur vollständigen Erholung auf das vorherige Hoch. "
         "Gibt an, wie lange ein Anleger nach dem größten Verlust warten musste, bis der Wert wieder hergestellt war."),
        ("Längste Drawdown-Phase",
         "Längster zusammenhängender Zeitraum, in dem das Portfolio unterhalb eines vorherigen Höchststands lag. "
         "Zeigt die maximale Dauer einer Verlustphase – relevant für die Geduld des Anlegers."),
        ("Benchmark",
         "Vergleichsmaßstab für die Portfolioperformance, bestehend aus einem oder mehreren Marktindizes. "
         "Die Zusammensetzung wird unterhalb der Charts angegeben."),
        ("Vor Kosten / Nach Kosten",
         "Die Performance vor Kosten zeigt die Bruttorendite der Anlagestrategie. "
         "Nach Kosten werden die Verwaltungsgebühren (Honorarsatz p.a.) täglich anteilig abgezogen. "
         "Bei aktivierter MwSt.-Option wird zusätzlich 19% Mehrwertsteuer auf das Honorar berechnet."),
    ]
    for term, desc in glossar:
        story.append(Paragraph(f"<b>{term}</b>", st_n))
        story.append(Paragraph(desc, st_sm))
        story.append(Spacer(1, 2*mm))

    story.append(Spacer(1,10*mm)); story.append(HRFlowable(width="100%",thickness=0.5,color=HexColor("#CCCCCC")))
    story.append(Paragraph(f"Erstellt am {fmt_date_de(dt.date.today())} | Fürst Fugger Privatbank",st_sm))
    doc.build(story); buf.seek(0); return buf.getvalue()

# Data loading
@st.cache_data(show_spinner=True)
def load_all_csvs(data_folder, date_tag, exclude_substrings):
    pattern=os.path.join(data_folder,f"*_{date_tag}_*.CSV"); files=glob.glob(pattern)
    return [p for p in files if not any(sub in os.path.basename(p) for sub in exclude_substrings)]

def read_one_csv(path):
    return pd.read_csv(path,comment="#",encoding="ISO-8859-1",delimiter=";",decimal=",",thousands=".",dtype=str)

def parse_dates_col(vv): return pd.to_datetime(vv["Datum"],format="%d.%m.%Y",errors="raise")

def extract_benchmark_name(vv):
    for c in ["Benchmark Name","Benchmark","Benchmarkname","Benchmark Name ","Benchmark-Bezeichnung"]:
        if c in vv.columns:
            v=vv.loc[0,c]
            if pd.notna(v) and str(v).strip(): return str(v).strip()
    return "Benchmark"

@st.cache_data(show_spinner=True)
def build_portfolio_timeseries(files, mapping):
    out={}
    for path in files:
        vv=read_one_csv(path); pn=vv.loc[0,"Portfolio Name"]; bn=extract_benchmark_name(vv); dates=parse_dates_col(vv)
        vv["Performance [%] (Intervall)"]=vv["Performance [%] (Intervall)"].astype(str).str.replace(",",".").astype(float)
        rp=to_decimal_interval(vv.loc[1:,"Performance [%] (Intervall)"]); rb=None
        if "Benchmark Performance [%] (Intervall)" in vv.columns:
            vv["Benchmark Performance [%] (Intervall)"]=vv["Benchmark Performance [%] (Intervall)"].astype(str).str.replace(",",".").astype(float)
            rb=to_decimal_interval(vv.loc[1:,"Benchmark Performance [%] (Intervall)"])
        try: fd=float(mapping.loc[mapping["Inhaber"]==pn,"Honorarsatz Standard"].values[0])
        except: fd=0.0
        idx=dates.iloc[1:].reset_index(drop=True); df=pd.DataFrame(index=idx); df.index.name="Datum"
        df["ret_port"]=rp; df["ret_bm"]=rb if (rb is not None and len(rb)==len(df)) else np.nan
        df["fee_default"]=fd; df=df.sort_index(); df.attrs["benchmark_name"]=bn; out[pn]=df
    return out


# ==========================================================================
# STREAMLIT APP
# ==========================================================================
st.set_page_config(page_title="FFPB – Performance & Portfolioanalyse", layout="wide")

# Globale Schriftart + Toolbar-Icons ausblenden (Rendering-Bug auf Streamlit Cloud)
st.markdown("""
<style>
    html, body, [class*="css"], .stMarkdown, .stMetricLabel, .stMetricValue,
    .stSelectbox, .stMultiSelect, .stTextInput, .stNumberInput,
    .stDataFrame, .stTable, .stCaption, .stButton, .stTabs,
    h1, h2, h3, h4, h5, h6, p, span, div, label, input, button, textarea {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }

    /* Toolbar-Icons bei DataFrames, Charts und Expandern ausblenden */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }
    /* Fullscreen-Button bei Charts ausblenden */
    button[title="View fullscreen"],
    button[title="Exit fullscreen"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

if not check_login(): st.stop()
st.title("Fürst Fugger Privatbank – Vermögensverwaltung")

# ── Gemeinsame Sidebar ──
mapping = load_mapping()
name_mapping = load_name_mapping()

with st.sidebar:
    st.header("Einstellungen")
    st.markdown("---")
    st.subheader("Anlagevolumen")
    anlagevolumen = st.number_input("Anlagevolumen in € (optional)",
        min_value=0.0, max_value=1_000_000_000.0, value=0.0, step=10_000.0, format="%.2f",
        help="Gilt für beide Tabs. Wenn > 0: Werte in Euro.")
    use_volume = anlagevolumen > 0

# ── TABS ──
tab_perf, tab_pf, tab_builder = st.tabs(["📈 Performance", "📊 Portfolioanalyse", "📋 Portfolio zusammenstellen"])


# ===========================================================================
# TAB 1: PERFORMANCE
# ===========================================================================
with tab_perf:
    auto_tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
    date_tag = auto_tag

    with st.sidebar:
        st.markdown("---")
        st.subheader("📈 Performance")
        show_adv_perf = st.checkbox("Erweiterte Einstellungen", value=False, key="adv_perf")
        if show_adv_perf:
            date_tag = st.text_input("Date-Tag (yyMMdd)", value=auto_tag,
                help="Neuester Tag automatisch erkannt. Nur ändern um auf ältere Stände zuzugreifen.", key="perf_tag")

    files = load_all_csvs(DATA_FOLDER, date_tag, EXCLUDE_SUBSTRINGS)
    if not files: st.error(f"Keine Dateien für Tag {date_tag}."); st.stop()
    data = build_portfolio_timeseries(files, mapping)
    dn_ordered, d2c, d2b = build_name_lookups(name_mapping, set(data.keys()))
    if not dn_ordered: st.error("Keine Portfolios zugeordnet."); st.stop()

    with st.sidebar:
        ds1=st.selectbox("Portfolio",dn_ordered,key="p_sel1"); ps1=d2c[ds1]
        sc=st.checkbox("Vergleichsportfolio",value=False,key="p_cmp"); ps2=ds2=None
        if sc: ds2=st.selectbox("Vergleichsportfolio",dn_ordered,key="p_sel2"); ps2=d2c[ds2]
        sv=st.checkbox("Vor Kosten",value=True,key="p_vk"); sb=st.checkbox("Benchmark",value=True,key="p_bm")
        sdd=st.checkbox("Drawdown (nach Kosten)",value=False,key="p_dd")
        stbl=st.checkbox("Tabelle rollierend",value=True,key="p_tbl"); sbar=st.checkbox("Balken-Chart",value=True,key="p_bar")
        st.markdown("---")
        fd1=float(data[ps1]["fee_default"].iloc[0]) if len(data[ps1]) else 0.0
        # Dynamischer Key: wenn Portfolio wechselt, wird der Default neu geladen
        fee_key_1 = f"p_fee1_{ps1}"
        if fee_key_1 not in st.session_state:
            st.session_state[fee_key_1] = float(round(fd1*100, 4))
        fp1=st.number_input(f"Kosten % – {ds1}",0.0,20.0,step=0.05,key=fee_key_1)
        fdec2=fp2=None
        if sc and ps2:
            fd2=float(data[ps2]["fee_default"].iloc[0]) if len(data[ps2]) else 0.0
            fee_key_2 = f"p_fee2_{ps2}"
            if fee_key_2 not in st.session_state:
                st.session_state[fee_key_2] = float(round(fd2*100, 4))
            fp2=st.number_input(f"Kosten % – {ds2}",0.0,20.0,step=0.05,key=fee_key_2)

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
    st.caption("⚠️ **Hinweise:** Siehe Disclaimer unten!")
    st.caption(f"📊 **Quelle:** Infront & eigene Berechnungen, Stand: {fmt_date_de(maxd)}")

    st.markdown("#### Zeitraum auswählen")
    # Reset-Logik: Counter ändert den Widget-Key, sodass das Widget frisch mit Default rendert
    if "p_sd_reset" not in st.session_state: st.session_state.p_sd_reset = 0
    if "p_ed_reset" not in st.session_state: st.session_state.p_ed_reset = 0

    c1,c2=st.columns(2)
    with c1: sd=st.date_input("Start",value=mind,min_value=mind,max_value=maxd,format="DD.MM.YYYY",key=f"p_sd_{st.session_state.p_sd_reset}")
    with c2: ed=st.date_input("Ende",value=maxd,min_value=mind,max_value=maxd,format="DD.MM.YYYY",key=f"p_ed_{st.session_state.p_ed_reset}")

    rc1,rc2=st.columns(2)
    with rc1:
        if st.button(f"↩️ Startdatum zurücksetzen ({fmt_date_de(mind)})", key="reset_sd", use_container_width=True):
            st.session_state.p_sd_reset += 1
            st.rerun()
    with rc2:
        if st.button(f"↩️ Enddatum zurücksetzen ({fmt_date_de(maxd)})", key="reset_ed", use_container_width=True):
            st.session_state.p_ed_reset += 1
            st.rerun()

    if sd>ed: st.error("Start > Ende."); st.stop()

    df1=data[ps1].copy(); df1=df1.loc[(df1.index.date>=sd)&(df1.index.date<=ed)].copy(); df2=None
    if sc and ps2:
        d2r=data[ps2].copy(); d2r=d2r.loc[(d2r.index.date>=sd)&(d2r.index.date<=ed)].copy()
        j=df1[["ret_port","ret_bm"]].rename(columns={"ret_port":"rp1","ret_bm":"rb1"}).join(
            d2r[["ret_port","ret_bm"]].rename(columns={"ret_port":"rp2","ret_bm":"rb2"}),how="inner")
        if j.empty: st.error("Kein gemeinsamer Zeitraum."); st.stop()
        df1=j[["rp1","rb1"]].rename(columns={"rp1":"ret_port","rb1":"ret_bm"})
        df2=j[["rp2","rb2"]].rename(columns={"rp2":"ret_port","rb2":"ret_bm"})

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

    # Kennzahlen
    nd1=len(r1); draf1=calc_daily_returns_after_fee(r1,fdec1); cg1=calc_cagr(ia1,nd1); vo1=calc_vola(draf1)
    ew1=float(ia1[-1]) if use_volume else None
    ia1_100=make_index_after_fee(r1,fdec1,100.0); mddv1,mddd1=calc_max_drawdown(ia1_100,xd)
    mdde1=calc_max_drawdown_euro(ia1,xd)[0] if use_volume else None
    cm1=calc_calmar_ratio(cg1,mddv1); rd1,rdt1=calc_drawdown_recovery(ia1_100,xd); dur1,ds1_,de1_=calc_max_drawdown_duration(ia1_100,xd)
    cg2=vo2=ew2=mddv2=mddd2=mdde2=cm2=rd2=rdt2=dur2=ds2_=de2_=None
    if df2 is not None:
        nd2=len(r2); draf2=calc_daily_returns_after_fee(r2,float(fdec2)); cg2=calc_cagr(ia2,nd2); vo2=calc_vola(draf2)
        ew2=float(ia2[-1]) if use_volume else None
        ia2_100=make_index_after_fee(r2,float(fdec2),100.0); mddv2,mddd2=calc_max_drawdown(ia2_100,xd)
        mdde2=calc_max_drawdown_euro(ia2,xd)[0] if use_volume else None
        cm2=calc_calmar_ratio(cg2,mddv2); rd2,rdt2=calc_drawdown_recovery(ia2_100,xd); dur2,ds2_,de2_=calc_max_drawdown_duration(ia2_100,xd)

    md=[{"label":l1,"auflagedatum":ad1,"cagr":cg1,"vola":vo1,"endwert":ew1,"calmar":cm1,
        "max_dd_val":mddv1 if sdd else None,"max_dd_date":mddd1 if sdd else None,"max_dd_eur":mdde1 if sdd else None,
        "recovery_days":rd1 if sdd else None,"recovery_date":rdt1 if sdd else None,"max_dd_dur":dur1 if sdd else None}]
    if df2 is not None and l2:
        md.append({"label":l2,"auflagedatum":ad2,"cagr":cg2,"vola":vo2,"endwert":ew2,"calmar":cm2,
            "max_dd_val":mddv2 if sdd else None,"max_dd_date":mddd2 if sdd else None,"max_dd_eur":mdde2 if sdd else None,
            "recovery_days":rd2 if sdd else None,"recovery_date":rdt2 if sdd else None,"max_dd_dur":dur2 if sdd else None})

    nk_label = f"nach Kosten{mwst_suffix}"
    st.subheader(f"📊 Kennzahlen ({nk_label})")
    display_metrics(l1,cg1,vo1,ew1,use_volume,ad1,cm1,mwst_suffix)
    if df2 is not None and l2: display_metrics(l2,cg2,vo2,ew2,use_volume,ad2,cm2,mwst_suffix)

    eff_fee_1 = fp1 * mwst_faktor  # effektive Kosten in %
    eff_fee_2 = (fp2 * mwst_faktor) if fp2 is not None else 0.0
    if use_volume: st.subheader(f"📈 Wertentwicklung in Euro ({fmt_eur_de(anlagevolumen)})"); yl="Wert in €"
    else: st.subheader("📈 Performance-Index (Start = 100)"); yl="Index (Start 100)"
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
    if sb and df1["ret_bm"].notna().any():
        rbm1=df1["ret_bm"].fillna(0).to_numpy(float); ibm1=make_index_from_returns(rbm1,sw)
        _add_line(xd, ibm1, f"BM {l1}: {bn1}")
        if df2 is not None and df2["ret_bm"].notna().any():
            rbm2=df2["ret_bm"].fillna(0).to_numpy(float); ibm2=make_index_from_returns(rbm2,sw)
            _add_line(xd, ibm2, f"BM {l2}: {bn2}")

    fig.update_layout(height=550,xaxis_title="Datum",xaxis=dict(tickformat="%d.%m.%Y"),yaxis_title=yl,
        yaxis=dict(tickformat=",.0f" if use_volume else None, separatethousands=True),
        legend=dict(title_text="Strategie", x=1.02, y=1, xanchor="left"),
        showlegend=True, hovermode="x unified",
        margin=dict(r=120))

    # Deutsche Tausender-Formatierung auf Y-Achse bei Volumen
    if use_volume:
        fig.update_layout(yaxis=dict(tickformat=",.0f"))
        # Plotly nutzt Locale – wir überschreiben mit separatethousands
        fig.update_layout(separators=",.")

    st.plotly_chart(fig,use_container_width=True)
    if sb: show_benchmark_composition(l1,bt1,l2,bt2)

    if sdd:
        st.markdown("---")
        display_drawdown_metrics(l1,mddv1,mddd1,mdde1,use_volume,rd1,rdt1,dur1,ds1_,de1_,mwst_suffix)
        if df2 is not None and l2: display_drawdown_metrics(l2,mddv2,mddd2,mdde2,use_volume,rd2,rdt2,dur2,ds2_,de2_,mwst_suffix)
        fdd=go.Figure()
        if use_volume:
            fdd.add_trace(go.Scatter(x=xd,y=drawdown_euro_from_index(ia1),mode="lines",name=f"{l1} – DD € (nK)"))
            if df2 is not None: fdd.add_trace(go.Scatter(x=xd,y=drawdown_euro_from_index(ia2),mode="lines",name=f"{l2} – DD € (nK)"))
            fdd.update_layout(height=350,xaxis_title="Datum",xaxis=dict(tickformat="%d.%m.%Y"),yaxis_title="DD in €",yaxis=dict(tickformat=",.0f"),hovermode="x unified")
        else:
            fdd.add_trace(go.Scatter(x=xd,y=drawdown_from_index(ia1_100),mode="lines",name=f"{l1} – DD (nK)"))
            if df2 is not None: fdd.add_trace(go.Scatter(x=xd,y=drawdown_from_index(ia2_100),mode="lines",name=f"{l2} – DD (nK)"))
            fdd.update_layout(height=350,xaxis_title="Datum",xaxis=dict(tickformat="%d.%m.%Y"),yaxis_title="Drawdown",hovermode="x unified")
        st.plotly_chart(fdd,use_container_width=True)

    dfr=None
    if stbl:
        sl=f"Seit: {fmt_date_de(df1.index.min())}"
        dfr=build_rolling_table(sb1t,sa1t,l1,sb2t,sa2t,l2,sl)
        st.subheader("📋 Wertentwicklung rollierend"); st.dataframe(dfr,use_container_width=True)

    bdl=[]
    if sbar:
        st.markdown("---"); st.subheader("📊 Performance blockweise")
        bl,br=st.columns([1,3])
        with bl:
            bm=st.radio("Zeitraum",["Kalenderjahre","Quartale","Benutzerdefiniert"],key="p_bm_r")
            csb=ceb=None
            if bm=="Benutzerdefiniert":
                csb=st.date_input("Von",value=sd,min_value=mind,max_value=maxd,format="DD.MM.YYYY",key="p_bv")
                ceb=st.date_input("Bis",value=ed,min_value=mind,max_value=maxd,format="DD.MM.YYYY",key="p_bb")
        tm={"Kalenderjahre":"PERFORMANCE P.A. (NACH KOSTEN)","Quartale":"PERFORMANCE QUARTALE (NACH KOSTEN)","Benutzerdefiniert":"PERFORMANCE (NACH KOSTEN) – BENUTZERDEFINIERT"}
        def _rb(dfs,fee,lab,bname,btxt,cont):
            bd=compute_bar_data(dfs,fee,bm,lab,csb,ceb)
            if bd.empty: cont.info(f"Keine Daten für {lab}."); return
            btt=f"{tm[bm]} – {lab}"; bdl.append((bd,lab,bname,btt,btxt))
            cont.plotly_chart(build_bar_chart(bd,lab,bname,title=btt),use_container_width=True)
            show_tbl = cont.checkbox(f"🔢 Tabelle anzeigen – {lab}", value=False, key=f"bar_tbl_{lab}")
            if show_tbl:
                cp=f"{lab} (nach Kosten)"; dp=bd[["label",cp,"ret_bm_raw"]].copy()
                dp[cp]=dp[cp].map(lambda x:f"{x:+.2f}%"); dp["ret_bm_raw"]=dp["ret_bm_raw"].map(lambda x:f"{x:+.2f}%" if pd.notna(x) else "–")
                dp.columns=["Zeitraum",f"{lab} nK",bname]; cont.dataframe(dp,use_container_width=True,hide_index=True)
        with br:
            _rb(df1,fdec1,l1,bn1,bt1,st.container())
            show_benchmark_composition(l1,bt1)
            if df2 is not None and fdec2 is not None and ps2:
                st.markdown("---"); _rb(df2,fdec2,l2,bn2 or "BM",bt2 or "",st.container())
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
        "Dieses Performancetool dient ausschließlich der unverbindlichen Veranschaulichung im Beratungsgespräch. "
        "Alle Berechnungen sind unverbindlich und ohne Gewähr."
    )
    st.markdown(f"**Quelle:** Infront & eigene Berechnungen, Stand: {fmt_date_de(maxd)}")
    st.markdown("**Ansprechpartner:** PBAM")

    # PDF Performance
    st.markdown("---")
    plt_=[(f"{l1} – {nk_label} ({eff_fee_1:.2f}%)",ia1)]
    if ia2 is not None: plt_.append((f"{l2} – {nk_label} ({eff_fee_2:.2f}%)",ia2))
    if sv: plt_.append((f"{l1} – vK",ib1));
    if sv and ib2 is not None: plt_.append((f"{l2} – vK",ib2))
    if sb and df1["ret_bm"].notna().any():
        plt_.append((f"BM {l1}: {bn1}",make_index_from_returns(df1["ret_bm"].fillna(0).to_numpy(float),sw)))
        if df2 is not None and df2["ret_bm"].notna().any():
            plt_.append((f"BM {l2}: {bn2}",make_index_from_returns(df2["ret_bm"].fillna(0).to_numpy(float),sw)))
    pdd=[]
    if sdd:
        if use_volume: pdd.append((f"{l1} DD €",drawdown_euro_from_index(ia1)));
        else: pdd.append((f"{l1} DD",drawdown_from_index(ia1_100)))
        if df2 is not None:
            if use_volume: pdd.append((f"{l2} DD €",drawdown_euro_from_index(ia2)))
            else: pdd.append((f"{l2} DD",drawdown_from_index(ia2_100)))
    lp=get_logo_path()
    if st.button("📄 PDF Performance",key="perf_pdf"):
        with st.spinner("PDF..."): pb=generate_perf_pdf(lp,l1,l2,bn1,bn2,bt1,bt2,eff_fee_1,eff_fee_2 if fp2 is not None else None,anlagevolumen,use_volume,sd,ed,xd,plt_,yl,sdd,pdd,stbl,dfr,sbar,bdl,md,mwst_suffix)
        st.download_button("⬇️ PDF",pb,f"Performance_{l1}_{fmt_date_de(sd)}-{fmt_date_de(ed)}.pdf","application/pdf",key="perf_dl")


# ===========================================================================
# TAB 2: PORTFOLIOANALYSE
# ===========================================================================
with tab_pf:
    render_portfolioanalyse(name_mapping, anlagevolumen)

# ===========================================================================
# TAB 3: PORTFOLIO BUILDER
# ===========================================================================
with tab_builder:
    render_portfolio_builder(name_mapping, anlagevolumen)
