# FFPB Streamlit Tool – Projektdokumentation & Transferwissen
## Stand: April 2026

---

## ⚠️ TRANSFERWISSEN: Streamlit-Fallen (gilt für JEDES Streamlit-Projekt)

### 1. CSS Font-Override zerstört Streamlit Icons

**Situation:** Du willst eine Custom-Schriftart (z.B. Segoe UI) in einer Streamlit-App verwenden.

**Falle:** Wenn du CSS global auf `span`, `button` oder `div` setzt, überschreibst du die Material Icons Font die Streamlit intern verwendet. Der Browser zeigt dann statt Icons den Ligatur-Namen als Klartext: `keyboard_double_arrow_right`, `arrow_right`, `expand_more` etc.

**Warum:** Streamlit rendert Icons als `<span class="material-symbols-rounded">keyboard_double_arrow_right</span>`. Die Material Icons Font wandelt diesen Text in ein Icon um (Ligatur-Rendering). Wenn du die Font überschreibst, wird der Text als Klartext angezeigt.

**Lösung:** Font-Override NUR auf den Hauptbereich und NUR auf Text-Elemente. Sidebar, System-Elemente, `span` und `button` komplett in Ruhe lassen.

```css
/* ✅ RICHTIG – nur Hauptbereich, nur Text-Elemente */
[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
[data-testid="stMainBlockContainer"] h4,
[data-testid="stMainBlockContainer"] h5,
[data-testid="stMainBlockContainer"] h6,
[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] div.stMarkdown,
[data-testid="stMainBlockContainer"] .stMetricLabel,
[data-testid="stMainBlockContainer"] .stMetricValue,
[data-testid="stMainBlockContainer"] .stCaption,
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] input,
[data-testid="stMainBlockContainer"] textarea {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
}

/* ❌ FALSCH – zerstört Material Icons UND Sidebar */
html, body, span, button, div, [class*="css"] {
    font-family: 'Segoe UI' !important;
}
```

**Konsequenz in diesem Projekt:** Sidebar behält Standard-Streamlit-Schriftart. Hauptbereich nutzt Segoe UI. Das ist ein bewusster Kompromiss.

---

### 2. Kein st.expander in der Sidebar

**Situation:** Du willst einen zuklappbaren Bereich in der Sidebar.

**Falle:** `st.expander` in der Sidebar rendert auf Streamlit Cloud den Pfeil als `_arrow_right` Text statt als Icon. Gleicher Grund wie #1 – Material Icons Problem auf Cloud-Infrastruktur.

**Lösung:** `st.checkbox` statt `st.expander` in der Sidebar. Im Hauptbereich sind Expander OK (aber wir haben sie trotzdem überall durch Checkboxes ersetzt um konsistent zu sein).

---

### 3. Duplicate Element IDs bei gleichen Daten

**Situation:** Eine Funktion rendert Plotly-Charts oder DataFrames und wird mehrfach aufgerufen (z.B. Portfolio 1 und Portfolio 2 vergleichen). Wenn beide Portfolios die gleiche Strategie sind, sind die Charts identisch.

**Falle:** Streamlit erzeugt Element-IDs basierend auf dem Inhalt. Identische Charts → identische IDs → `StreamlitDuplicateElementId` Error.

**Lösung:** Jeder wiederverwendeten Funktion einen `suffix`-Parameter geben und an alle `st.plotly_chart()`, `st.dataframe()`, `st.checkbox()` als `key=f"element_{suffix}"` übergeben.

```python
# ✅ RICHTIG
def _render_portfolio(data, suffix="p1"):
    st.plotly_chart(fig, key=f"chart_{suffix}")
    st.dataframe(df, key=f"table_{suffix}")

_render_portfolio(data1, suffix="p1")
_render_portfolio(data2, suffix="p2")

# ❌ FALSCH – crasht wenn data1 == data2
def _render_portfolio(data):
    st.plotly_chart(fig)  # Keine key → Duplicate ID bei gleichen Daten
```

---

### 4. Widget-Key direkt setzen ist verboten

**Situation:** Du willst einen Date-Picker oder Multiselect programmatisch zurücksetzen.

**Falle:** `st.session_state["widget_key"] = new_value` bei aktiven Widgets → `StreamlitAPIException`.

**Lösung A (Counter-Keys):** Für Datum-Reset:
```python
if "reset_count" not in st.session_state: st.session_state.reset_count = 0
sd = st.date_input("Start", value=default, key=f"sd_{st.session_state.reset_count}")
if st.button("Reset"):
    st.session_state.reset_count += 1  # Neuer Key → neues Widget → Default-Wert
    st.rerun()
```

**Lösung B (Key löschen):** Für Multiselect beim Laden eines Musterportfolios:
```python
if "multiselect_key" in st.session_state:
    del st.session_state["multiselect_key"]
st.rerun()
```

---

### 5. Filter-Defaults NICHT auf Minimum setzen

**Situation:** `st.number_input("Duration max", min_value=0.0, max_value=30.0)` OHNE expliziten `value`.

**Falle:** Streamlit setzt den Default auf `min_value` = 0.0. Ein Filter "Duration max = 0" filtert ALLES weg → leeres Universum → User sieht nichts und versteht nicht warum.

**Lösung:** Immer explizit `value=` setzen: `value=30.0` für Max-Filter, `value=0.0` für Min-Filter.

---

### 6. Plotly Toolbar ausblenden

**Situation:** Die Plotly-Toolbar (Zoom, Pan, Download) erscheint beim Hover über Charts.

**Lösung:** `config={"displayModeBar": False}` an JEDEN `st.plotly_chart()` Aufruf.

---

## 1. Projektübersicht

Streamlit-App für Fürst Fugger Privatbank mit 3 Tabs.

| Tab | Datei | Zeilen | Zweck |
|---|---|---|---|
| 📈 Performance | `streamlit_app.py` | ~840 | Historische Performance, Kennzahlen, Charts, PDF+Glossar |
| 📊 Portfolioanalyse | `modules/portfolioanalyse.py` | ~780 | Strukturanalyse: Ringe, Tabellen, Anleihen-Detail, PDF |
| 📋 Portfolio zusammenstellen | `modules/portfolio_builder.py` | ~695 | Individueller Portfolio-Aufbau durch Berater |
| (gemeinsam) | `modules/shared.py` | ~190 | Konstanten, Login, Formatierung, Font-Setup |

**Gesamt: ~2.500 Zeilen | Deployment: Streamlit Cloud via GitHub | Python 3.10+**

---

## 2. Dateistruktur

```
Repository Root/
├── streamlit_app.py
├── modules/
│   ├── __init__.py
│   ├── shared.py
│   ├── portfolioanalyse.py
│   └── portfolio_builder.py
├── fonts/
│   ├── segoeui.ttf                  ← Von C:\Windows\Fonts kopiert
│   └── segoeuib.ttf
├── .streamlit/
│   └── config.toml                  ← toolbarMode = "minimal"
├── Mapping_Honorarsatz.xlsx         ← Inhaber → Honorarsatz (Dezimal)
├── Mapping_Namen.xlsx               ← A=Anzeige, B=CSV-Key, C=Duration, D=Benchmark
├── Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg
├── Daten/                           ← Performance-CSVs
├── Daten_PF/                        ← Portfolioanalyse-CSVs
├── Duration/                        ← Duration/Rendite pro Portfolio
├── Zieldaten/                       ← Anlageuniversum für Builder
└── requirements.txt
```

### requirements.txt
```
streamlit>=1.30
pandas>=2.0
numpy>=1.24
plotly>=5.18
openpyxl>=3.1
matplotlib>=3.7
reportlab>=4.0
Pillow>=10.0
```

---

## 3. Abhängigkeiten

```
shared.py ──→ streamlit_app.py (Tab 1 inline + importiert Tab 2 + Tab 3)
          ──→ portfolioanalyse.py (exportiert Ring-Charts, Tabellen → für Builder)
          ──→ portfolio_builder.py (importiert shared + portfolioanalyse-Funktionen)
```

---

## 4. Corporate Design

| Farbe | Hex | Verwendung |
|---|---|---|
| Fuggerblau | #003460 | Ring-Charts, Überschriften, größtes Segment |
| Fuggergold | #C3A069 | Akzent, zweites Segment, Fälligkeit |
| Mittelblau | #4A7FAA | Drittes Segment |
| Sand | #D4BD8A | Viertes Segment |
| Hellblau | #7FABC8 | Fünftes Segment |

```python
RING_COLORS = ["#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8", ...]
TOP5_COLORS = ["#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8"]
```

Alte Performance-Chart Farben (noch in shared.py): `FFPB_DARK=#1B3A5C`, `FFPB_GOLD=#B8973A`

---

## 5. Schriftarten

| Kontext | Schriftart | Methode |
|---|---|---|
| Web Hauptbereich | Segoe UI | CSS auf stMainBlockContainer (NICHT global!) |
| Web Sidebar | Standard Streamlit | Bewusst NICHT überschrieben (siehe Transferwissen #1) |
| PDF | Segoe UI / Helvetica Fallback | shared.py._register_pdf_fonts() |

---

## 6. Tab 1: Performance

- Hinweis + Quelle oben, Disclaimer unten
- Sidebar: Portfolio, Vergleich, Checkboxen, Kosten (dynamischer Key), MwSt (×1.19)
- Zeitraum: Datumspicker + Reset-Buttons (Counter-Keys, siehe Transferwissen #4)
- Chart: Endwerte als legendgroup-gebundene Text-Traces, Legende "Strategie" rechts
- Balken-Chart: `_rb()` Funktion mit `suffix="p1"/"p2"` (siehe Transferwissen #3)
- PDF: Meta, Kennzahlen, Chart+Endwerte, Tabelle, Balken, Disclaimer, Glossar (9 Begriffe)
- Disclaimer: "Alle Berechnungen sind unverbindlich und **erfolgen** ohne Gewähr."

---

## 7. Tab 2: Portfolioanalyse

- `_render_single_portfolio()` mit `suffix="pf1"/"pf2"` (siehe Transferwissen #3)
- Ring-Diagramme: Absteigend sortiert, Labels außen (13px), <3% ausgeblendet, Legende horizontal unten
- YTD: Spalten ausgeschrieben (Wertpapier-Performance/Performancebeitrag), Caption erklärt beide
- PDF (aktuell reportlab): Ring-Charts kompakter (100×85mm), intelligente Spaltenbreiten
- **Geplant: Umstellung auf PowerPoint (python-pptx)**
- Disclaimer: "Alle Angaben **erfolgen** ohne Gewähr."

---

## 8. Tab 3: Portfolio zusammenstellen

- Schnellzugriffe (9 Buttons) → setzen Filter via session_state
- Filter: Hauptfilter sichtbar, erweiterte als Checkbox (NICHT Expander!)
- Suche: Multiselect mit `default=[]` (NUR hinzufügen, nie syncen)
- Cash: Input + Residual + Hinweis
- Export: Excel (.xlsx, nicht CSV wegen Encoding)
- `_show_builder_disclaimer(zm_hint)` bei JEDEM return + am Ende
- Filter-Defaults: Duration max=30.0, Risiko max=7 (siehe Transferwissen #5)

---

## 9. Disclaimers

Alle 3 Tabs: Hinweis + Quelle oben, Disclaimer unten, in PDFs als eigene Seite.

| Tab | Schlüsselsatz |
|---|---|
| Performance | "Alle Berechnungen sind unverbindlich und erfolgen ohne Gewähr." |
| Portfolioanalyse | "Alle Angaben erfolgen ohne Gewähr." |
| Builder | "Alle Angaben sind ohne Gewähr." + Produktgovernance |

Quelle: Infront & eigene Berechnungen | Ansprechpartner: PBAM

---

## 10. Berechnungsformeln

```
daily_drag      = (1 + fee_pa)^(1/365) - 1
idx_nach_kosten = idx[i-1] * (1 + ret - daily_drag)
cagr            = (endwert/startwert)^(365/tage) - 1
vola            = std(tagesrenditen) * sqrt(365)
calmar          = cagr / |max_drawdown|
gew_duration    = Σ(gewicht × duration) / Σ(gewichte_anleihen)
```

---

## 11. Geplante nächste Schritte

1. **Portfolioanalyse PDF → PowerPoint** (python-pptx, 16:9, Fuggerblau/Fuggergold)
2. Performance-Charts auf neue Corporate Colors umstellen
3. Compliance-Feedback abwarten → Disclaimer ggf. anpassen

---

## 12. Für den nächsten Chat / Kollegen

**Hochladen:** Diese MD + alle 4 Code-Dateien
**Sagen:** "Lies die PROJEKT_DOKUMENTATION.md zuerst komplett. Dann [Aufgabe]."
**Bei Problemen:** Screenshot + erwartetes Verhalten

*Stand: April 2026*
