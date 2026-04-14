# FFPB Streamlit Tool – Komplette Projektdokumentation
## Für Übergabe an Kollegen / neuen Chat
## Stand: April 2026

---

## ⚠️ KRITISCHE LESSONS LEARNED (ZUERST LESEN!)

### 1. CSS Font-Override zerstört Streamlit Icons
**Problem:** Wenn CSS global `font-family` auf `span`, `button` oder `div` setzt, überschreibt das die Material Icons Font. Streamlit zeigt dann statt Icons den Ligatur-Namen als Klartext (`keyboard_double_arrow_right`, `arrow_right`).

**Lösung:** Font-Override NUR auf `[data-testid="stMainBlockContainer"]` und NUR auf h1-h6, p, label, input, textarea. KEINE span, button, div. Sidebar komplett in Ruhe lassen.

```css
/* RICHTIG */
[data-testid="stMainBlockContainer"] h1, [data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] label { font-family: 'Segoe UI' !important; }

/* FALSCH – zerstört Material Icons */
span, button, div { font-family: 'Segoe UI' !important; }
```

### 2. Kein st.expander in der Sidebar
Streamlit Cloud rendert den Expander-Pfeil als `_arrow_right` Text. **Immer `st.checkbox` verwenden.**

### 3. Widget-Key direkt setzen ist verboten
`st.session_state["key"] = value` bei aktiven Widgets → Error. Stattdessen:
- **Counter-Keys:** `key=f"widget_{counter}"` → Counter++ → rerun (für Datum-Reset)
- **Key löschen:** `del st.session_state["key"]` → rerun (für Musterportfolio laden)

### 4. Filter-Defaults NICHT auf Minimum setzen
`st.number_input("Duration max", 0.0, 30.0)` OHNE `value=30.0` → Default ist 0.0 → filtert alles weg!
**Immer explizite value setzen:** `value=30.0` für Duration max, `value=7` für Risiko max.

---

## 1. Projektübersicht

Streamlit-App für Fürst Fugger Privatbank mit 3 Tabs zur Analyse von Vermögensverwaltungs-Portfolios.

| Tab | Datei | Zeilen | Zweck |
|---|---|---|---|
| 📈 Performance | `streamlit_app.py` | 838 | Historische Performance, Kennzahlen, Drawdown, Charts, PDF+Glossar |
| 📊 Portfolioanalyse | `modules/portfolioanalyse.py` | 781 | Strukturanalyse: Ring-Diagramme, Tabellen, Anleihen-Detail, PDF |
| 📋 Portfolio zusammenstellen | `modules/portfolio_builder.py` | 694 | Berater baut individuelles Portfolio aus Anlageuniversum |
| (gemeinsam) | `modules/shared.py` | 190 | Konstanten, Login, Formatierung, Font-Registrierung |

**Gesamt: 2.503 Zeilen | Deployment: Streamlit Cloud via GitHub | Python 3.10+ (3.14 auf Cloud)**

---

## 2. Dateistruktur

```
Repository Root/
├── streamlit_app.py                 ← Hauptdatei: CSS, Login, Tabs, Performance (Tab 1)
├── modules/
│   ├── __init__.py                  ← Leer
│   ├── shared.py                    ← Konstanten, Login, Formatierung, PDF-Fonts
│   ├── portfolioanalyse.py          ← Tab 2 + Ring-Charts + PDF-Export
│   └── portfolio_builder.py         ← Tab 3 (nutzt Funktionen aus portfolioanalyse.py)
├── fonts/
│   ├── segoeui.ttf                  ← Segoe UI Regular (für PDF, von Windows kopiert)
│   └── segoeuib.ttf                 ← Segoe UI Bold
├── .streamlit/
│   └── config.toml                  ← toolbarMode = "minimal"
├── Mapping_Honorarsatz.xlsx         ← Inhaber → Honorarsatz (Dezimal, z.B. 0.0085)
├── Mapping_Namen.xlsx               ← 4 Spalten: A=Anzeige, B=CSV-Key, C=Duration, D=Benchmark
├── Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg
├── Daten/                           ← Performance-CSVs (Tagesrenditen)
├── Daten_PF/                        ← Portfolioanalyse-CSVs (Bestandsdaten)
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

## 3. Abhängigkeiten zwischen Dateien

```
shared.py ─────────────────────────────────────────────────────
  │ Exportiert: FFPB_DARK, FFPB_GOLD, FFPB_LIGHT, FFPB_BLUE2
  │             PDF_FONT, PDF_FONT_BOLD, FONT_DIR
  │             DATA_FOLDER, DATA_FOLDER_PF, DURATION_FOLDER, ZIELDATEN_FOLDER
  │             EXCLUDE_SUBSTRINGS, LOGO_FILENAME
  │             check_login(), fmt_date_de(), fmt_pct_de(), fmt_eur_de()
  │             detect_newest_date_tag(), load_mapping(), load_name_mapping()
  │             build_name_lookups(), csv_name_to_display()
  │             get_logo_path(), get_logo_aspect()
  │
  ├──→ streamlit_app.py
  │      Importiert: alles oben + PDF_FONT/PDF_FONT_BOLD
  │      Tab 1 Code inline
  │      Importiert: portfolioanalyse.render_portfolioanalyse
  │      Importiert: portfolio_builder.render_portfolio_builder
  │
  ├──→ portfolioanalyse.py
  │      Importiert: Farben, Pfade, PDF_FONT, Formatierung, detect_newest_date_tag
  │      Exportiert (für Builder): build_allocation, build_ring_chart,
  │        get_top_holdings, build_top5_bar_chart, build_grouped_title_table,
  │        get_bond_summary, load_pf_csvs, build_pf_data, RING_COLORS, TOP5_COLORS
  │
  └──→ portfolio_builder.py
         Importiert: shared + portfolioanalyse-Funktionen (wiederverwendet Ring, Top5, Tabelle)
```

---

## 4. Datenquellen im Detail

### 4.1 Mapping_Namen.xlsx
| Spalte A (Index 0) | Spalte B (Index 1) | Spalte C (Index 2) | Spalte D (Index 3) |
|---|---|---|---|
| Anzeigename | CSV-Key (Portfolio Name) | Duration-Name | Benchmark-Zusammensetzungstext |
| cVV konservativ | Muster konservativ cVV | konservativ | 50% iBoxx EUR Corp... |

**Reihenfolge in Excel = Reihenfolge in allen Dropdowns.**

### 4.2 Mapping_Honorarsatz.xlsx
| Inhaber | Honorarsatz Standard |
|---|---|
| Muster konservativ cVV | 0.0085 |

Honorarsatz als Dezimal → wird als Default in Sidebar vorbelegt → User kann anpassen.

### 4.3 Performance-CSVs (Daten/)
- **Dateiname:** `{Portfolio Name}_{yyMMdd}_{HHmm}.CSV`
- **Encoding:** ISO-8859-1, Semikolon-getrennt, deutsches Zahlenformat
- **Spalten:** Datum, Portfolio Name, Performance [%] (Intervall), Benchmark Performance [%] (Intervall), Benchmark Name
- **Besonderheit:** `to_decimal_interval()` prüft ob Werte >1 (dann /100) um Prozent vs. Dezimal zu unterscheiden

### 4.4 Portfolioanalyse-CSVs (Daten_PF/)
- **Dateiname:** `{Portfolio Name}_Portfolioanalyse_{yyMMdd}_{HHmm}.CSV`
- **Spalten:** Auswertungsdatum, Wertpapier, WKN, Gewicht, Performancebeitrag, WP-Performance, Fälligkeit, Kupon, Segment, Region, Gattung, Portfolio Name
- **String-Bereinigung:** `parse_pf_data()` → `.str.strip()` + "nan" → NaN
- **Gewichte:** Prozent in CSV (z.B. "3,13%") → `/100` → Dezimal

### 4.5 Duration-Datei (Duration/)
- **Spalten:** Wertpapier, Duration, Rendite
- **Zuordnung:** Spalte C im Mapping → CSV-Key (Spalte B)
- **Neueste Datei** nach `_yyMMdd_HHmm` im Namen

### 4.6 Zieldaten (Zieldaten/)
- **Dateiname:** `Gesamt_Zielmärkte erweitert_{yyMMdd}_{HHmm}.CSV`
- **Spalten:** Name, WKN, ISIN, Fälligkeit, Kupon, Duration, Segment, Region, Assetklasse, Marktrisikowert, Masterlistenzuordnung
- **Bereinigung:** `-`, `–`, `""`, `"nan"` → NaN
- **Fälligkeits-Parsing:** 4 Formate (dd.mm.yyyy, yyyy-mm-dd, dd/mm/yyyy, frei mit dayfirst)
- **Numerische Spalten:** Kupon_num, Duration_num, MRW_num, Fälligkeit_parsed

### 4.7 Date-Tag Erkennung
`detect_newest_date_tag(folder)`: Regex `_(\d{6})_` auf Dateinamen → höchster Tag. Dateien mit "Stiftung" ignoriert. In Sidebar als Checkbox "Erweiterte Einstellungen" versteckt.

---

## 5. Corporate Design & Farben

### Primärfarben
| Name | Hex | RGB | Verwendung |
|---|---|---|---|
| Fuggerblau | #003460 | 0, 52, 96 | Hauptfarbe, Überschriften, größtes Ring-Segment |
| Fuggergold | #C3A069 | 195, 160, 105 | Akzentfarbe, zweites Segment |

### Sekundärfarben (abgeleitet)
| Hex | Verwendung |
|---|---|
| #4A7FAA | Drittes Ring-Segment, Mittelblau |
| #D4BD8A | Viertes Segment, helles Gold |
| #7FABC8 | Fünftes Segment, Hellblau |
| #8B7340 | Sechstes Segment |

### Ring-Chart Farbpalette (Reihenfolge)
```python
RING_COLORS = ["#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8",
               "#8B7340", "#A8CBE8", "#5C6B3C", "#E8D5B0", "#2C5F8A", ...]
TOP5_COLORS = ["#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8"]
```

### Alte Farben (noch in shared.py, Performance-Charts)
```python
FFPB_DARK  = "#1B3A5C"  # Dunkelblau (Performance-Chart Hintergrund)
FFPB_GOLD  = "#B8973A"  # Altes Gold (Performance-Balken)
FFPB_LIGHT = "#A8CBE8"  # Hellblau
FFPB_BLUE2 = "#2C5F8A"  # Mittelblau
```
**TODO:** Performance-Charts auf neue Corporate Colors umstellen.

---

## 6. Schriftarten

### Web (Streamlit)
CSS in `streamlit_app.py` – NUR auf `stMainBlockContainer` (siehe Lesson Learned #1):
```css
[data-testid="stMainBlockContainer"] h1, h2, h3, h4, h5, h6, p,
div.stMarkdown, .stMetricLabel, .stMetricValue, .stCaption, label, input, textarea {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
}
```

### PDF
- `shared.py` registriert Segoe UI aus `fonts/segoeui.ttf` + `fonts/segoeuib.ttf`
- `PDF_FONT` = "SegoeUI" (oder "Helvetica" als Fallback)
- `PDF_FONT_BOLD` = "SegoeUI-Bold" (oder "Helvetica-Bold")
- Importiert in `streamlit_app.py` und `portfolioanalyse.py`

---

## 7. Tab 1: Performance (streamlit_app.py)

### 7.1 Aufbau oben → unten
```
⚠️ Hinweise: Siehe Disclaimer unten!
📊 Quelle: Infront & eigene Berechnungen, Stand: {maxd}
── Zeitraum auswählen ──
   [Start] [Ende]
   [↩️ Startdatum zurücksetzen (Auflagedatum)] [↩️ Enddatum zurücksetzen]
── Kennzahlen ──
   **{Strategie-Name}**
   Auflagedatum | ⌀ Rendite | Volatilität | Calmar | (Endwert €)
── Chart ──
   Linien mit Endwert-Labels (verschwinden mit Legende)
── Drawdown (optional) ──
   Max DD % + "entspricht €" darunter | Recovery | Längste Phase | Tief-Datum
── Tabelle rollierend (optional) ──
── Balken-Chart (optional) ──
   Benchmark-Beschreibung IMMER sichtbar
── Disclaimer ──
── PDF Button ──
```

### 7.2 Sidebar
- Portfolio + Vergleichsportfolio (Dropdowns)
- Checkboxen: Vor Kosten (default: an), Benchmark (an), Drawdown (aus), Tabelle (an), Balken (an)
- Kosten % (dynamischer Key: `p_fee1_{portfolio_name}`)
- MwSt-Checkbox → ×1.19, alle Labels dynamisch
- Erweiterte Einstellungen (Checkbox!): Date-Tag

### 7.3 Zeitraum-Reset
Counter-basierte Keys: `key=f"p_sd_{st.session_state.p_sd_reset}"` → Counter++ + rerun → neuer Key → Widget rendert mit Default `mind`.

### 7.4 Chart (Plotly)
- Endwerte: `go.Scatter(mode="text")` mit `legendgroup` → verschwinden wenn Linie ausgeblendet
  - Ohne Volumen: Index-Stand
  - Mit Volumen: Prozentuale Veränderung
- Legende: "Strategie", `x=1.02`, immer sichtbar
- Y-Achse: `separators=",."` bei Volumen
- Margin: `r=120` für Labels
- `config={"displayModeBar": False}` auf ALLEN plotly_chart Aufrufen

### 7.5 PDF (reportlab)
- Seite 1: Meta + Quelle + Kennzahlen + Linien-Chart (mit Endwerten) + Benchmark
- Seite 2: Rollierende Tabelle
- Seite 3: Balken-Charts
- **Vorletzte Seite: Disclaimer** (3 Absätze + Quelle + PBAM)
- **Letzte Seite: Glossar** (9 Begriffe: Auflagedatum, CAGR, Vola, Calmar, Max DD, Recovery, Längste DD, Benchmark, Vor/Nach Kosten)

### 7.6 Berechnungsformeln
```
daily_drag      = (1 + fee_pa)^(1/365) - 1
idx_nach_kosten = idx[i-1] * (1 + ret - daily_drag)
cagr            = (endwert/startwert)^(365/tage) - 1
vola            = std(tagesrenditen) * sqrt(365)
calmar          = cagr / |max_drawdown|
```

---

## 8. Tab 2: Portfolioanalyse (modules/portfolioanalyse.py)

### 8.1 Aufbau
```
⚠️ Hinweise + 📊 Quelle
📅 Momentaufnahme per {Datum}
── Kennzahlen ──
── Top 5 Holdings Säulendiagramm ──
── Ring-Diagramme (3 nebeneinander: Gattung, Region, Segment) ──
── Einzeltitel-Tabelle (gruppiert nach Gattung) ──
── Top/Flop 5 Performancebeitrag (nur wenn YTD aktiv) ──
   Caption: Erklärt Performancebeitrag + Wertpapier-Performance
── Anleihen-Detail (Duration, Kupon, Rendite, Fälligkeitsstruktur) ──
── Disclaimer ──
── PDF Button ──
```

### 8.2 YTD Performance
- Checkbox in Sidebar
- Spalten voll ausgeschrieben: **Wertpapier-Performance (YTD)**, **Performancebeitrag (YTD)**
- Caption unter Top/Flop erklärt:
  - Performancebeitrag = gewichteter Beitrag zur Portfolio-Gesamtperformance seit Jahresbeginn
  - Wertpapier-Performance = individuelle Wertentwicklung, unabhängig von Gewichtung
  - Beide = Momentaufnahme, kein Indikator

### 8.3 Ring-Diagramme (Plotly)
- Absteigend sortiert (größter Block bei 12 Uhr, im Uhrzeigersinn)
- Labels **außerhalb** des Rings (13px), unter 3% ausgeblendet
- Kleine Segmente herausgezogen (`pull`)
- Legende **horizontal unter** dem Chart
- `uniformtext=dict(minsize=11, mode="hide")` gegen Überlappung
- Corporate Colors: Fuggerblau → Fuggergold → Mittelblau → ...

### 8.4 Ring-Diagramme PDF (matplotlib)
- Gleiche Sortierung + Farben
- Labels außerhalb (`pctdistance=1.15`), unter 3% ausgeblendet
- Legende horizontal unten (`ncol=3`)
- Titel enthält Portfolio-Name
- Kleiner (100×85mm) für bessere Platznutzung

### 8.5 Tabelle PDF
- **Intelligente Spaltenbreiten:** Wertpapier 3×, Segment/Region 2×, Fälligkeit 1,5×, Rest 1×
- Font: PDF_FONT_BOLD für Header

### 8.6 PDF aktuell (reportlab) – GEPLANTER UMBAU AUF PPTX
Aktueller Stand:
- Seite 1: Deckblatt + Gattung-Ring (viel Leerraum)
- Seite 2: Region + Segment Ringe
- Seite 3: Einzeltitel-Tabelle
- Seite 4: Disclaimer

**Geplant:** Umstellung auf PowerPoint (python-pptx) für besseres Layout:
- Slide 1: Deckblatt
- Slide 2: Kennzahlen + 3 Ringe nebeneinander
- Slide 3+: Einzeltitel-Tabelle
- Letzter Slide: Disclaimer
- Format: 16:9 Breitbild
- Farben: Fuggerblau + Fuggergold

---

## 9. Tab 3: Portfolio zusammenstellen (modules/portfolio_builder.py)

### 9.1 Layout
```
⚠️ Session-Warnung
📂 Anlageuniversum geladen (Stand)
⚠️ Hinweise + 📊 Quelle
── ⚡ Schnellzugriffe (9 Buttons) ──
── 📦 Musterportfolio laden ──
── 🔍 Filter (Hauptfilter sichtbar, erweiterte als Checkbox) ──
── 🔎 Suche (Multiselect, default=[]) ──
── 📊 Ihr Portfolio (data_editor mit 🗑️) ──
── Cash (Input + Residual) ──
── Excel-Export (.xlsx) ──
── 📊 Portfoliostruktur ──
── 🔄 Vergleich mit Musterportfolio ──
── Disclaimer (via _show_builder_disclaimer, bei JEDEM return) ──
```

### 9.2 Schnellzugriffe
Setzen Filter-Keys direkt in `st.session_state` → `st.rerun()`:
| Button | Filter |
|---|---|
| Rein Aktien | Assetklasse: [Aktien] |
| Rein Renten | Assetklasse: [Renten] |
| Multi-Asset | Assetklasse: [Aktien, Renten] |
| High Yield (Kupon >3%) | Renten + kupon_min: 3% |
| Kurze Duration (<3J) | Renten + duration_max: 3 |
| Lange Duration (>5J) | Renten + duration_min: 5 |
| Europa-Fokus | Region: [Deutschland, Europa ohne Deutschland] |
| Nordamerika-Fokus | Region: [Nordamerika] |
| Niedriges Risiko (Marktrisikowert ≤3) | mrw_max: 3 |

### 9.3 Musterportfolio laden
- WKN-Matching: `_normalize_wkn()` (strip + upper) → Lookup
- Fallback: Name-Match (case-insensitive)
- `del st.session_state["builder_multiselect"]` vor rerun

### 9.4 Titel-Suche
- `st.multiselect` mit `default=[]` – **NUR zum Hinzufügen**, nie Sync mit Portfolio
- Optionen: `Name (WKN | ISIN)`, Placeholder: "z.B. Microsoft, A14Y6F..."
- Max 50 Titel (Hardblock)
- Bestehende Gewichte werden NICHT überschrieben

### 9.5 Cash-Handling
- Input über der Tabelle: 0-50%, Default 5%
- Gleichgewichten: `(100% - Cash%) / Anzahl Titel`
- Residual: `Cash = max(0, 100% - Summe)`
- Error wenn >100%

### 9.6 Export
- Excel (.xlsx, nicht CSV) via openpyxl
- 🗑️-Spalte entfernt, "–" → leere Zellen, Cash-Zeile angehängt

### 9.7 Disclaimer
`_show_builder_disclaimer(zm_hint)` wird aufgerufen:
- Bei `return` wenn kein Portfolio (Zeile 430)
- Bei `return` wenn keine gültigen Titel (Zeile 491)
- Bei `return` wenn keine Gewichte (Zeile 580)
- Am Ende des normalen Durchlaufs (Zeile 694)

---

## 10. Disclaimers (alle 3 Tabs)

Jeder Tab hat: Hinweis + Quelle oben, Disclaimer unten, in PDFs als eigene Seite.

### Performance
```
1) Historische Wertentwicklung, keine Garantie, in Euro gemessen
2) Tägliche Berechnung, Zinseszinseffekt, keine halbjährliche Berücksichtigung
3) Unverbindlich, nur zur Veranschaulichung
Quelle: Infront & eigene Berechnungen, Stand: {letztes Datum}
Ansprechpartner: PBAM
```

### Portfolioanalyse
```
1) Momentaufnahme, Abweichungen durch Käufe/Verkäufe, Klassifizierung kann sich ändern
2) Unverbindlich, nur zur Veranschaulichung
Quelle: Infront & eigene Berechnungen, Stand: {Auswertungsdatum}
Ansprechpartner: PBAM
```

### Portfolio Builder
```
1) Simulierte Zusammensetzung, basiert auf Stammdaten zum Stichtag
2) Zuordnungen können sich ändern, Produktgovernance einhalten, Kunden informieren
3) Keine Anlageberatung, unverbindlich
Quelle: Infront & eigene Berechnungen, Stand: {Zielmarkt-Datum}
Ansprechpartner: PBAM
```

---

## 11. Alle Streamlit-Workarounds

| # | Problem | Lösung | Wo |
|---|---|---|---|
| 1 | CSS Font überschreibt Material Icons | NUR `stMainBlockContainer` targeten | streamlit_app.py CSS |
| 2 | Expander in Sidebar → `_arrow_right` | `st.checkbox` statt `st.expander` | Überall in Sidebar |
| 3 | Widget-Key direkt setzen → Error | Counter-Keys + rerun | Datum-Reset |
| 4 | Widget-Key direkt setzen → Error | `del` + rerun | Musterportfolio laden |
| 5 | Multiselect überschreibt Portfolio | `default=[]`, nur hinzufügen | Builder-Suche |
| 6 | Fee bleibt bei Portfolio-Wechsel | Dynamischer Key `p_fee1_{name}` | Sidebar Kosten |
| 7 | Duration max Default=0 filtert alles weg | Explizit `value=30.0` | Builder Filter |
| 8 | Risiko max Default=1 filtert alles weg | Explizit `value=7` | Builder Filter |
| 9 | `float\|None` Type Hints → Error auf 3.9 | Keine Union-Types | Überall |
| 10 | Plotly Toolbar Hover stört | `config={"displayModeBar": False}` | Alle 16 plotly_chart |

---

## 12. Geplante nächste Schritte

### Sofort (nächste Session)
1. **Portfolioanalyse PDF → PowerPoint umstellen** (python-pptx)
   - Slide 1: Deckblatt (Logo, Titel, Portfolio-Name, Datum)
   - Slide 2: Kennzahlen + 3 Ringe nebeneinander
   - Slide 3+: Einzeltitel-Tabelle
   - Letzter Slide: Disclaimer
   - Format: 16:9, Fuggerblau/Fuggergold
   - `python-pptx` zu requirements.txt hinzufügen

2. **Performance-Charts Corporate Colors** – alte FFPB_DARK/#1B3A5C auf Fuggerblau #003460 umstellen

### Nach Compliance-Feedback
- Disclaimer-Texte ggf. anpassen
- Weitere Features nach Bedarf

---

## 13. Secrets & Deployment

- **Secrets:** Über Streamlit Cloud Settings (NICHT im Repo)
- **config.toml:** Im Repo unter `.streamlit/config.toml` mit `toolbarMode = "minimal"`
- **Fonts:** `fonts/segoeui.ttf` + `fonts/segoeuib.ttf` im Repo (von Windows kopiert)

### Deployment-Checkliste
- [ ] 4 Python-Dateien + requirements.txt + .streamlit/config.toml
- [ ] Ordner: Daten/, Daten_PF/, Duration/, Zieldaten/, fonts/
- [ ] Mapping-Dateien + Logo im Root
- [ ] Font-Dateien in fonts/
- [ ] Secrets über Streamlit Cloud Settings

---

## 14. Für den nächsten Chat / Kollegen

**Hochladen:**
1. Diese PROJEKT_DOKUMENTATION.md
2. streamlit_app.py
3. modules/shared.py
4. modules/portfolioanalyse.py
5. modules/portfolio_builder.py

**Sagen:** "Lies zuerst die PROJEKT_DOKUMENTATION.md komplett durch. Dann [konkreter Änderungswunsch]."

**Bei Problemen:** Screenshot + was erwartet wurde + was stattdessen passiert.

**Bei neuen Datenquellen:** Beispielzeile der CSV zeigen.

---

*Dokumentation: April 2026 | 2.503 Zeilen über 4 Module*
