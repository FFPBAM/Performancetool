# FFPB Streamlit Tool – Projektdokumentation
## Stand: April 2026

---

## KRITISCHE LESSONS LEARNED

### CSS Font-Override: NIEMALS global auf span/button/div setzen!

**Problem:** Streamlit verwendet Material Icons als Icon-Font in `<span>` Elementen. Wenn CSS global `font-family` auf `span`, `button` oder `div` setzt, überschreibt das die Material Icons Font. Der Browser zeigt dann statt Icons den Ligatur-Namen als Klartext (z.B. `keyboard_double_arrow_right`, `arrow_right`).

**Lösung:** Font-Override NUR auf den Hauptbereich (`stMainBlockContainer`) und NUR auf spezifische Text-Elemente (h1-h6, p, label, input). KEINE `span`, `button`, `div` global. Sidebar und System-Elemente komplett in Ruhe lassen.

```css
/* RICHTIG – nur Hauptbereich, keine System-Elemente */
[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] label { font-family: 'Segoe UI' !important; }

/* FALSCH – zerstört Material Icons */
span, button, div { font-family: 'Segoe UI' !important; }
```

### Kein st.expander in der Sidebar
Streamlit Cloud rendert den Expander-Pfeil als `_arrow_right` Text. Stattdessen `st.checkbox` verwenden.

---

## 1. Übersicht

Streamlit-App mit 3 Tabs:

| Tab | Datei | Zeilen | Zweck |
|---|---|---|---|
| Performance | `streamlit_app.py` | ~840 | Historische Performance, Kennzahlen, Charts, PDF |
| Portfolioanalyse | `modules/portfolioanalyse.py` | ~715 | Strukturanalyse bestehender Musterportfolios |
| Portfolio zusammenstellen | `modules/portfolio_builder.py` | ~695 | Individueller Portfolio-Aufbau durch Berater |
| (gemeinsam) | `modules/shared.py` | ~190 | Konstanten, Login, Formatierung, Font-Setup |

**Deployment:** Streamlit Cloud via GitHub | Python 3.10+

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
│   ├── segoeui.ttf
│   └── segoeuib.ttf
├── .streamlit/
│   └── config.toml              (toolbarMode = "minimal")
├── Mapping_Honorarsatz.xlsx
├── Mapping_Namen.xlsx
├── Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg
├── Daten/
├── Daten_PF/
├── Duration/
├── Zieldaten/
└── requirements.txt
```

---

## 3. Abhängigkeiten

```
shared.py
  ├──→ streamlit_app.py (importiert alles + PDF_FONT)
  │       Tab 1 inline, importiert portfolioanalyse + portfolio_builder
  ├──→ portfolioanalyse.py (importiert Konstanten + PDF_FONT)
  │       Exportiert: Ring-Charts, Top 5, Tabellen → für Builder
  └──→ portfolio_builder.py (importiert shared + portfolioanalyse-Funktionen)
```

---

## 4. Datenquellen

- **Mapping_Namen.xlsx:** Spalte A=Anzeige, B=CSV-Key, C=Duration, D=Benchmark
- **Mapping_Honorarsatz.xlsx:** Inhaber → Honorarsatz (Dezimal)
- **Daten/*.CSV:** Performance-Zeitreihen (Semikolon, ISO-8859-1, deutsch)
- **Daten_PF/*.CSV:** Portfolioanalyse-Bestand (Gewicht, YTD, Gattung, Region...)
- **Duration/*.CSV:** Duration/Rendite pro Portfolio
- **Zieldaten/*.CSV:** Anlageuniversum für Builder
- **Date-Tag:** `detect_newest_date_tag()` Regex `_(\d{6})_` → höchster Tag

---

## 5. Schriftarten

| Kontext | Schriftart | Methode |
|---|---|---|
| Web Hauptbereich | Segoe UI | CSS auf `stMainBlockContainer` (NICHT global!) |
| Web Sidebar | Standard (unberührt) | Keine Überschreibung |
| PDF | Segoe UI / Helvetica | `PDF_FONT` aus shared.py, TTFont Registrierung |

**Font-Registrierung:** `shared.py._register_pdf_fonts()` → automatisch beim Import. Ohne `fonts/` → Helvetica Fallback.

---

## 6. Tab 1: Performance

- **Oben:** Hinweis + Quelle (Stand aus CSVs)
- **Sidebar:** Portfolio, Vergleich, Checkboxen, Kosten (dynamischer Key), MwSt, Erweiterte Einstellungen (Checkbox!)
- **Zeitraum:** Datumspicker + Reset-Buttons (Counter-Keys)
- **Kennzahlen:** Strategie-Name als Überschrift, CAGR/Vola/Calmar/Endwert, DD-Euro als caption darunter
- **Chart:** Endwerte als legendgroup-gebundene Text-Traces, Legende "Strategie" rechts, deutsches Y-Format
- **Balken:** Benchmark-Beschreibung IMMER sichtbar
- **PDF:** Meta+Quelle, Kennzahlen, Chart mit Endwerten, Tabelle, Balken, Disclaimer (vorletzte Seite), Glossar (letzte Seite)
- **Disclaimer unten:** 3 Absätze + Quelle + PBAM

---

## 7. Tab 2: Portfolioanalyse

- **Oben:** Hinweis + Quelle + Momentaufnahme
- **YTD:** Checkbox, Spalten ausgeschrieben (Wertpapier-Performance/Performancebeitrag), Caption erklärt beide Begriffe unter Top/Flop
- **Darstellung:** Kennzahlen → Ring-Diagramme → Top 5 → Gruppierte Tabelle → Top/Flop → Anleihen-Detail
- **PDF:** Quelle auf Seite 1, Disclaimer als letzte Seite
- **Disclaimer unten:** 2 Absätze (Momentaufnahme + Unverbindlichkeit) + Quelle + PBAM

---

## 8. Tab 3: Portfolio zusammenstellen

- **Layout:** Schnellzugriffe → Musterportfolio → Filter (Hauptfilter sichtbar, erweiterte als Checkbox) → Suche (Multiselect default=[]) → Tabelle (data_editor) → Cash (Input + Residual) → Excel-Export → Strukturanalyse → Vergleich → Disclaimer
- **Kritische Defaults:** Duration max=30.0, Risiko max=7
- **Disclaimer:** Via `_show_builder_disclaimer()` bei JEDEM return + am Ende
- **3 Absätze:** Simuliert + Produktgovernance + Unverbindlichkeit + Quelle + PBAM

---

## 9. Streamlit-Workarounds

| Problem | Lösung |
|---|---|
| CSS Font überschreibt Material Icons | NUR `stMainBlockContainer` targeten, keine span/button/div |
| Expander in Sidebar zeigt `_arrow_right` | `st.checkbox` statt `st.expander` |
| Widget-Key direkt setzen → Error | Counter-Keys oder del + rerun |
| Multiselect überschreibt Portfolio | `default=[]`, nur hinzufügen |
| Fee bleibt bei Portfolio-Wechsel | Dynamischer Key `p_fee1_{name}` |
| `float | None` Type Hints → Error | Keine Union-Types (Python 3.9) |

---

## 10. Farbschema

| Farbe | Hex | Verwendung |
|---|---|---|
| Dunkelblau | #1B3A5C | Chart-BG, Header |
| Gold | #B8973A | Primärfarbe, Balken |
| Hellblau | #A8CBE8 | Benchmark |
| Mittelblau | #2C5F8A | Zweites Portfolio |

Top 5: #1B3A5C, #6A9BC3, #B8973A, #C4B78C, #A8CBE8

---

## 11. Berechnungsformeln

```
daily_drag      = (1 + fee_pa)^(1/365) - 1
idx_nach_kosten = idx[i-1] * (1 + ret - daily_drag)
cagr            = (endwert/startwert)^(365/tage) - 1
vola            = std(tagesrenditen) * sqrt(365)
calmar          = cagr / |max_drawdown|
gew_duration    = Σ(gewicht × duration) / Σ(gewichte_anleihen)
gew_kupon       = Σ(gewicht × kupon) / Σ(gewichte_anleihen)
```

---

## 12. Disclaimers

Alle 3 Tabs: Hinweis + Quelle oben, Disclaimer unten, in PDFs als eigene Seite.

- **Performance:** Historische Wertentwicklung, tägliche Berechnung, unverbindlich
- **Portfolioanalyse:** Momentaufnahme, Klassifizierung kann sich ändern, unverbindlich
- **Builder:** Simuliert, Produktgovernance einhalten, keine Anlageberatung

Quelle: Infront & eigene Berechnungen | Ansprechpartner: PBAM

---

## 13. Deployment

- [ ] 4 Python-Dateien + requirements.txt auf GitHub
- [ ] Ordner: Daten/, Daten_PF/, Duration/, Zieldaten/, fonts/, .streamlit/
- [ ] .streamlit/config.toml mit `toolbarMode = "minimal"`
- [ ] Mapping-Dateien + Logo im Root
- [ ] Font-Dateien in fonts/
- [ ] Secrets über Streamlit Cloud Settings

---

## 14. Für den nächsten Chat

1. Diese Dokumentation + alle 4 Code-Dateien hochladen
2. Konkreten Änderungswunsch beschreiben
3. Bei UI-Problemen: Screenshot mitgeben
4. Bei neuen Datenquellen: Beispielzeile zeigen

*Stand: April 2026*
