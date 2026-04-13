# FFPB Streamlit Performance & Portfolioanalyse Tool
## Vollständige Projektdokumentation (Stand: April 2026)

---

## 1. Projektübersicht

Streamlit-App für **Fürst Fugger Privatbank** zur Analyse und Visualisierung von Vermögensverwaltungs-Portfolios. Die App bietet drei Hauptfunktionen:

1. **📈 Performance** – Historische Performance-Analyse mit Zeitreihen, Kennzahlen, Drawdown, rollierenden Tabellen, Balken-Charts und PDF-Export
2. **📊 Portfolioanalyse** – Strukturanalyse bestehender Musterportfolios (Allokation, Top Holdings, Anleihen-Detail)
3. **📋 Portfolio zusammenstellen** – Berater-Tool zum individuellen Aufbau von Portfolios aus dem Anlageuniversum

**Deployment:** Streamlit Cloud via GitHub  
**Python:** 3.10+ (3.14 auf Streamlit Cloud)  
**Codeumfang:** ~2.220 Zeilen über 4 Dateien

---

## 2. Dateistruktur

```
📁 Repository Root
├── streamlit_app.py                 ← Hauptdatei: Login, Tabs, Performance-Tool (Tab 1)
├── modules/
│   ├── __init__.py                  ← Leer (Python-Paket)
│   ├── shared.py                    ← Gemeinsame Konstanten, Login, Formatierung, Helpers
│   ├── portfolioanalyse.py          ← Tab 2: Portfolioanalyse
│   └── portfolio_builder.py         ← Tab 3: Portfolio zusammenstellen
├── Mapping_Honorarsatz.xlsx         ← Fee-Mapping
├── Mapping_Namen.xlsx               ← Name-Mapping (4 Spalten)
├── Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg
├── Daten/                           ← Performance-CSVs
├── Daten_PF/                        ← Portfolioanalyse-CSVs
├── Duration/                        ← Duration/Rendite-Datei (Portfolio-Ebene)
├── Zieldaten/                       ← Anlageuniversum-CSV für Portfolio Builder
├── requirements.txt
└── .streamlit/
    └── secrets.toml                 ← Login-Passwörter (nicht im Repo)
```

---

## 3. Dependencies (requirements.txt)

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

## 4. Konfiguration & Secrets

### 4.1 Streamlit Secrets (.streamlit/secrets.toml)
```toml
[passwords]
benutzername1 = "passwort1"
benutzername2 = "passwort2"
```

### 4.2 Konstanten (modules/shared.py)
```python
LOGO_FILENAME     = "Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg"  # 815×249px JPEG
FFPB_DARK         = "#1B3A5C"   # Dunkelblau
FFPB_GOLD         = "#B8973A"   # Gold
FFPB_LIGHT        = "#A8CBE8"   # Hellblau
FFPB_BLUE2        = "#2C5F8A"   # Mittelblau
MAPPING_PATH      = "Mapping_Honorarsatz.xlsx"
NAME_MAPPING_PATH = "Mapping_Namen.xlsx"
DATA_FOLDER       = "Daten"
DATA_FOLDER_PF    = "Daten_PF"
DURATION_FOLDER   = "Duration"
ZIELDATEN_FOLDER  = "Zieldaten"
EXCLUDE_SUBSTRINGS = ["Stiftung"]  # Portfolios mit diesem Substring werden ausgeblendet
```

---

## 5. Datenquellen & Formate

### 5.1 Mapping_Namen.xlsx (Name-Mapping)
| Spalte A (Index 0) | Spalte B (Index 1) | Spalte C (Index 2) | Spalte D (Index 3) |
|---|---|---|---|
| Anzeigename | CSV-Key (Portfolio Name) | Duration-Name | Benchmark-Text |
| cVV konservativ | Muster konservativ cVV | konservativ | 50% iBoxx EUR Corp... |

- **Reihenfolge aus Excel** bestimmt Dropdown-Reihenfolge
- Spalte A → wird dem User angezeigt
- Spalte B → matcht den "Portfolio Name" in den Performance-/PF-CSVs
- Spalte C → matcht den "Wertpapier"-Namen in der Duration-Datei
- Spalte D → Benchmark-Zusammensetzungstext (wird unter Charts angezeigt)

### 5.2 Mapping_Honorarsatz.xlsx (Fee-Mapping)
| Spalte "Inhaber" | Spalte "Honorarsatz Standard" |
|---|---|
| Muster konservativ cVV | 0.0085 |

- Honorarsatz als Dezimalzahl (0.0085 = 0,85%)
- Wird als Default in der Sidebar vorbelegt
- User kann den Wert manuell anpassen
- Optional: MwSt-Aufschlag (×1.19) über Checkbox

### 5.3 Performance-CSVs (Daten/)
**Dateiname-Schema:** `{Portfolio Name}_{yyMMdd}_{HHmm}.CSV`  
**Beispiel:** `Muster konservativ cVV_260316_0823.CSV`

**Format:**
- Semikolon-getrennt, ISO-8859-1 Encoding, deutsches Zahlenformat (Komma als Dezimal)
- Erste Zeile = Header, Daten ab Zeile 2
- Tägliche Intervall-Renditen

**Wichtige Spalten:**
- `Datum` → dd.mm.yyyy
- `Portfolio Name` → matcht Mapping Spalte B
- `Performance [%] (Intervall)` → Tagesrendite (deutsches Format, z.B. "0,12")
- `Benchmark Performance [%] (Intervall)` → Benchmark-Tagesrendite
- `Benchmark Name` → Name der Benchmark

**Verarbeitung:** `to_decimal_interval()` prüft ob Werte >1 sind (dann /100), um Prozent vs. Dezimal zu unterscheiden.

### 5.4 Portfolioanalyse-CSVs (Daten_PF/)
**Dateiname-Schema:** `{Portfolio Name}_Portfolioanalyse_{yyMMdd}_{HHmm}.CSV`

**Spalten:**
```
Auswertungsdatum;Wertpapier;WKN;Gewicht;Performancebeitrag;WP-Performance;
Fälligkeit;Kupon;Segment;Region;Gattung;Portfolio Name
```

- Gewichte als Prozent (z.B. "3,13%") → werden zu Dezimal geparst (/100)
- Liquidität = `max(0, 1.0 - Summe(Gewichte))` (automatisch berechnet)
- **String-Bereinigung:** Alle Text-Spalten (WKN, Wertpapier, Gattung, etc.) werden mit `.str.strip()` bereinigt und "nan" zu echtem NaN konvertiert

### 5.5 Duration-Datei (Duration/)
**Dateiname-Schema:** Enthält `_yyMMdd_HHmm` im Namen, neueste wird automatisch genommen

**Format (Tab- oder Semikolon-getrennt):**
```
Wertpapier	Duration	Rendite
ausgewogen	3,71	3,60%
konservativ	4,48	3,41%
```

- Zuordnung über **Spalte C** im Mapping_Namen.xlsx → CSV-Key (Spalte B)
- Duration und Rendite werden als Kennzahlen im Anleihen-Detail angezeigt
- Nur auf Portfolio-Ebene verfügbar (nicht pro Einzeltitel)

### 5.6 Zieldaten/Anlageuniversum (Zieldaten/)
**Dateiname-Schema:** `Gesamt_Zielmärkte erweitert_{yyMMdd}_{HHmm}.CSV`

**Spalten:**
```
Name;WKN;ISIN;Fälligkeit;Kupon;Duration;Segment;Region;Assetklasse;
Marktrisikowert;Masterlistenzuordnung;Zugelassen zum Vertrieb in der Beratung;Anlagehorizont
```

- Neueste Datei wird automatisch geladen (nach Zeitstempel im Namen sortiert)
- **String-Bereinigung:** Alle Text-Spalten getrimmt, "-", "–", "", "nan" → NaN
- Numerische Spalten: `Kupon_num` (Dezimal), `Duration_num`, `MRW_num`, `Fälligkeit_parsed`
- Fälligkeit wird in 4 Formaten probiert: dd.mm.yyyy, yyyy-mm-dd, dd/mm/yyyy, freies Parsen

### 5.7 Date-Tag Erkennung
Alle Ordner nutzen `detect_newest_date_tag()`:
- Regex `_(\d{6})_` auf allen Dateinamen
- Höchster 6-stelliger Tag = neuester Stand
- Dateien mit "Stiftung" im Namen werden ignoriert (`EXCLUDE_SUBSTRINGS`)
- Date-Tags sind als "Erweiterte Einstellungen" in der Sidebar zuklappbar (für Zugriff auf ältere Stände)

---

## 6. Tab 1: Performance (streamlit_app.py)

### 6.1 Architektur
- Code liegt direkt in `streamlit_app.py` (nicht in eigenem Modul)
- Sidebar-Einstellungen: Portfolio-Auswahl, Vergleichsportfolio, Checkboxen, Kosten, MwSt
- Hauptbereich: Kennzahlen, Chart, Drawdown, Tabelle, Balken-Chart, PDF

### 6.2 Sidebar-Optionen
- **Portfolio auswählen** (Dropdown, Reihenfolge aus Mapping_Namen.xlsx)
- **Vergleichsportfolio** (Checkbox + zweiter Dropdown)
- **Checkboxen:** Vor Kosten, Benchmark, Drawdown, Tabelle rollierend, Balken-Chart
- **Kosten % pro Portfolio** (Dynamischer Key: `p_fee1_{portfolio_name}` → bei Portfolio-Wechsel wird Default neu geladen)
- **Bruttohonorar (inkl. 19% MwSt.)** Checkbox → multipliziert Kosten ×1.19
- **Anlagevolumen in €** (gilt für alle Tabs)
- **⚙️ Erweiterte Einstellungen** (zugeklappter Expander): Date-Tag manuell ändern

### 6.3 MwSt-Logik
```python
mwst_faktor = 1.19 if brutto_mwst else 1.0
mwst_suffix = " (inkl. 19% MwSt.)" if brutto_mwst else " (exkl. MwSt.)"
fdec1 = (fp1 * mwst_faktor) / 100.0  # effektive Fee als Dezimal
```
- Alle Labels zeigen dynamisch "(inkl. 19% MwSt.)" oder "(exkl. MwSt.)"
- Effektive Kosten werden als Caption angezeigt wenn MwSt aktiv
- In der PDF: Kosten-Zeile und Kennzahlen-Header zeigen MwSt-Status

### 6.4 Zeitraum-Auswahl
- Start/Ende Datumspicker mit `format="DD.MM.YYYY"`
- Bei 2 Portfolios: Gemeinsamer Zeitraum (`max(start1, start2)` bis `min(ende1, ende2)`)
- **Reset-Buttons:** "↩️ Startdatum zurücksetzen (Auflagedatum)" und "↩️ Enddatum zurücksetzen"
- Reset nutzt **Counter-basierte Keys** (`p_sd_{counter}`) weil Streamlit keine direkte Zuweisung an Widget-Keys erlaubt

### 6.5 Index-Berechnung
```python
# Täglicher Fee-Drag
daily_drag = (1 + fee_pa)^(1/365) - 1

# Index nach Kosten
index[0] = startwert  # 100 oder Anlagevolumen
index[i] = index[i-1] * (1 + (tagesrendite - daily_drag))

# Index vor Kosten
index[i] = index[i-1] * (1 + tagesrendite)
```

### 6.6 Kennzahlen (alle nach Kosten)
Jede Strategie hat eine Überschrift: **`{Strategiename}`**

| Kennzahl | Berechnung | Tooltip |
|---|---|---|
| Auflagedatum im PM | Erster Datenpunkt (unabhängig vom Zeitraum-Filter) | ℹ️ |
| ⌀ Rendite p.a. (CAGR) | `(Endwert/Startwert)^(365/Tage) - 1` | ℹ️ |
| Volatilität p.a. | `Std(Tagesrenditen) × √365` | ℹ️ |
| Calmar Ratio | `CAGR / |Max Drawdown|` | ℹ️ |
| Endwert in € | Nur wenn Anlagevolumen > 0 | ℹ️ |

### 6.7 Drawdown-Kennzahlen
| Kennzahl | Details |
|---|---|
| Max. Drawdown (%) | Prozent vom Peak |
| Max. Drawdown (€) | Unter dem Prozent-Wert als `st.caption("entspricht ...")` |
| Recovery | Tage vom Tief bis Erholung, oder "noch nicht erholt" |
| Längste DD-Phase | Tage + Zeitraum |
| Drawdown-Tief am | Datum |

### 6.8 Performance-Chart (Plotly)
- Linien: nach Kosten, vor Kosten (optional), Benchmark (optional)
- **Endwerte:** Als `go.Scatter(mode="text")` mit `legendgroup` → verschwinden wenn Linie in Legende ausgeblendet wird
  - Ohne Volumen: Index-Stand (z.B. "108,34")
  - Mit Volumen: Prozentuale Veränderung (z.B. "+36,12%")
- **Legende:** Titel "Strategie", immer sichtbar, positioniert rechts außerhalb (`x=1.02`)
- **Y-Achse:** Bei Volumen deutsches Format (`separators=",."`)
- **Margin:** `r=120` für Platz für Endwert-Labels
- Benchmark-Zusammensetzungstext unter dem Chart (wenn Benchmark-Checkbox aktiv)

### 6.9 Rollierende Tabelle
Perioden: YTD, 1J, 3J, 5J, 10J, Seit-Inception  
Spalten: Vor Kosten, Nach Kosten (pro Portfolio)  
Format: `x,xxx%`

### 6.10 Balken-Chart
- Modi: Kalenderjahre, Quartale, Benutzerdefiniert
- Farben: Gold (P1), Dunkelblau (P2), Hellblau (BM1), Blaugrau (BM2)
- Dunkler Hintergrund (#1B3A5C)
- **Benchmark-Beschreibung wird IMMER angezeigt** (nicht abhängig von der Sidebar-Checkbox)

### 6.11 PDF-Export (reportlab + matplotlib)
- **Seite 1:** Logo, Meta-Infos (Portfolio, Zeitraum, Kosten inkl. MwSt-Status), Kennzahlen, Linien-Chart mit Endwerten, Benchmark-Text, optional Drawdown
- **Seite 2:** Rollierende Tabelle
- **Seite 3:** Balken-Charts mit Benchmark-Text
- **Letzte Seite: Glossar** – Erklärungen aller Kennzahlen (CAGR, Volatilität, Calmar, Max DD, Recovery, Längste DD-Phase, Benchmark, Vor/Nach Kosten)
- Footer: Erstellungsdatum + "Fürst Fugger Privatbank"

---

## 7. Tab 2: Portfolioanalyse (modules/portfolioanalyse.py)

### 7.1 Datenfluss
```
Daten_PF/*.CSV → load_pf_csvs() → build_pf_data() → {Portfolio Name: DataFrame}
Duration/*.CSV → load_duration_data() → {CSV-Key: {duration, rendite}}
```

### 7.2 String-Bereinigung (parse_pf_data)
Alle Text-Spalten (Wertpapier, WKN, ISIN, Segment, Region, Gattung, Portfolio Name) werden:
- `.astype(str).str.strip()`
- `.replace("nan", np.nan)`

### 7.3 Darstellung (pro Portfolio)
1. **Kennzahlen:** Anzahl Titel, Investitionsgrad, Liquidität (+ € wenn Volumen)
2. **Ring-Diagramme** (3 nebeneinander, volle Breite): Gattung, Region, Segment
   - Kleine Kategorien (<3%) → "Sonstige" zusammengefasst
   - Labels innerhalb des Rings (Prozent), Legende vertikal rechts
3. **Top 5 Holdings:** Säulendiagramm (nach Gewicht)
   - Farben: Dunkelblau, Mittelblau, Gold, Beige, Hellblau (Corporate Colors)
4. **Einzeltitel-Tabelle:** Gruppiert nach Gattung (nicht als Spalte)
   - Gattung als Überschrift mit Gesamtgewicht
   - Kupon/Fälligkeit nur bei Renten-Blöcken
   - Liquidität als eigener Block am Ende
5. **Top/Flop 5 Performancebeitrag** (nur wenn YTD aktiv, optional)
6. **Anleihen-Detail:** Anzahl, Gewicht, ⌀ Kupon (gewichtet), Duration (aus Duration-Datei), Rendite, Fälligkeitsstruktur als Balkendiagramm

### 7.4 Vergleich (2 Portfolios)
- **Untereinander** mit voller Breite (nicht nebeneinander)
- Trennlinie zwischen den Portfolios
- Jedes Portfolio: Name als Header, dann komplette Analyse

### 7.5 PDF-Export
- Ring-Diagramme via matplotlib (nicht Plotly)
- Gruppierte Einzeltitel-Tabelle als reportlab Table
- Logo auf jeder Seite, Footer mit Erstellungsdatum

---

## 8. Tab 3: Portfolio zusammenstellen (modules/portfolio_builder.py)

### 8.1 Konzept
Berater baut aus dem Anlageuniversum (Zieldaten/) ein individuelles Portfolio:
- **Strukturanalyse** (keine Performance-Analyse – dafür fehlen Zeitreihen)
- Portfolio wird in `st.session_state.builder_portfolio` gespeichert: `{WKN: gewicht_dezimal}`
- Bei Logout geht das Portfolio verloren → Hinweis permanent sichtbar

### 8.2 Layout-Reihenfolge
```
1. ⚡ Schnellzugriffe (9 Buttons)
2. 📦 Musterportfolio als Startportfolio laden
3. 🔍 Anlageuniversum filtern (Expander, standardmäßig offen)
4. 🔎 Titel suchen & zum Portfolio hinzufügen (Multiselect)
5. 📊 Ihr Portfolio (Gewicht-Editor, Cash, Export)
6. 📊 Portfoliostruktur (Ring-Diagramme, Top 5, Tabelle)
7. 🔄 Ihr Portfolio im Vergleich (mit Musterportfolio)
```

### 8.3 Schnellzugriffe
Setzen Filter-Werte direkt in `st.session_state` und lösen `st.rerun()` aus:

| Schnellzugriff | Filter |
|---|---|
| Rein Aktien | Assetklasse: [Aktien] |
| Rein Renten | Assetklasse: [Renten] |
| Multi-Asset | Assetklasse: [Aktien, Renten] |
| High Yield (Kupon >3%) | Assetklasse: [Renten], kupon_min: 3% |
| Kurze Duration (<3J) | Assetklasse: [Renten], duration_max: 3.0 |
| Lange Duration (>5J) | Assetklasse: [Renten], duration_min: 5.0 |
| Europa-Fokus | Region: [Deutschland, Europa ohne Deutschland] |
| Nordamerika-Fokus | Region: [Nordamerika] |
| Niedriges Risiko (Marktrisikowert ≤3) | mrw_max: 3 |

### 8.4 Musterportfolio laden
- Dropdown mit allen Musterportfolios aus `Daten_PF/`
- **WKN-Matching:** Normalisiert (strip + uppercase) via `_normalize_wkn()` und `_build_wkn_lookup()`
- Fallback: Match über Name (case-insensitive)
- Gewichte werden übernommen
- `builder_multiselect` Key wird gelöscht → Multiselect rendert frisch
- Hinweis: "📦 Basis: **cVV defensiv plus** (Stand: 260320)"

### 8.5 Filter
**Hauptfilter (4 Spalten):** Assetklasse, Region, Segment, Masterlistenzuordnung  
**Erweiterte Filter:** Kupon min (%), Duration min/max (Jahre), Marktrisikowert max

**WICHTIG – Default-Werte:**
- Duration max: `value=30.0` (NICHT 0.0, sonst filtert es alles weg!)
- Risiko max: `value=7` (NICHT 1!)
- Kupon min: `value=0.0` (korrekt)
- Duration min: `value=0.0` (korrekt)

**Placeholder-Texte:** "z.B. Aktien, Renten...", "z.B. Nordamerika, Europa...", etc.

**Filter wirken auf die Suche:** Wenn Filter aktiv → Multiselect zeigt nur gefilterte Titel. Ohne Filter → gesamtes Universum.

### 8.6 Titel-Suche (Multiselect)
- **NUR zum Hinzufügen** – `default=[]`, kein Sync mit Portfolio
- Optionen: `Name (WKN | ISIN)` – durchsuchbar nach allen drei Feldern
- Nach Auswahl: "✅ Ausgewählte Titel ins Portfolio übernehmen" Button
- **Max 50 Titel** (Hardblock mit Fehlermeldung)
- Bestehende Gewichte werden NIEMALS überschrieben

### 8.7 Portfolio-Tabelle (st.data_editor)
**Spalten:** 🗑️ (Checkbox), Name, WKN, Assetklasse, Gewicht (%), Kupon, Duration, Fälligkeit

- **Gewicht (%)** editierbar (0-100%, Schritt 0.1)
- **🗑️** Checkbox zum Entfernen → Titel wird sofort entfernt bei Anhaken
- Kupon, Duration, Fälligkeit: readonly, bei Aktien "–"
- Entfernen/Gewichte: Alles über Session-State, kein Multiselect-Sync

### 8.8 Cash-Handling
```python
CASH_PCT = 0.05  # Default 5%
```
- **Cash-Input** über der Tabelle: `st.number_input("💰 Cash-Anteil (%)", 0-50%)`
- **Gleichgewichten:** `(100% - Cash%) / Anzahl Titel`
- **Residual:** `Cash = max(0, 100% - Summe(Gewichte))`
- Hinweis: "ℹ️ Die Differenz zu 100% wird automatisch als Cash-Position (Liquidität) ausgewiesen."
- Fehlermeldung wenn Summe > 100%

### 8.9 Export
- **Excel (.xlsx)** via openpyxl
- 🗑️-Spalte wird entfernt, "–" durch leere Zellen ersetzt
- Cash-Zeile wird angehängt
- Dateiname: `Portfolio_20260323.xlsx`

### 8.10 Strukturanalyse
Nutzt Funktionen aus `portfolioanalyse.py` (wiederverwendet):
- `build_allocation()`, `build_ring_chart()`, `get_top_holdings()`, `build_top5_bar_chart()`, `build_grouped_title_table()`

**Kennzahlen:** Anzahl Titel, Investitionsgrad, Liquidität (+ € wenn Volumen)

**Anleihen-Detail (nur wenn Renten im Portfolio):**
- Anzahl Anleihen, Gewicht Anleihen
- **⌀ Duration (gewichtet):** `Σ(Gewicht × Duration) / Σ(Gewichte)` mit ausführlichem Tooltip
- **⌀ Kupon (gewichtet):** gleiche Berechnung
- **Fälligkeitsstruktur:** Balkendiagramm (Fälligkeitsjahr vs. aggregiertes Gewicht)

### 8.11 Vergleich mit Musterportfolio
- Dropdown: Musterportfolio zum Vergleich auswählen
- Untereinander: Kennzahlen + Ring-Diagramme des Musterportfolios

---

## 9. Gemeinsame Funktionen (modules/shared.py)

| Funktion | Beschreibung |
|---|---|
| `check_login()` | Streamlit Secrets `[passwords]`, Session-State basiert |
| `fmt_date_de(d)` | → `dd.mm.yyyy` |
| `fmt_pct_de(v, decimals=2)` | → `x,xx%` (Dezimal → Prozent mit Komma) |
| `fmt_eur_de(v)` | → `xxx.xxx,xx €` (deutsches Format) |
| `detect_newest_date_tag(folder, exclude)` | Regex `_(\d{6})_` auf Dateinamen → höchster Tag |
| `load_mapping()` | Liest Mapping_Honorarsatz.xlsx (cached) |
| `load_name_mapping()` | Liest Mapping_Namen.xlsx (cached) |
| `build_name_lookups(mapping, available)` | → `(display_names_ordered, display_to_csv, display_to_benchmark)` |
| `csv_name_to_display(csv_name, mapping)` | Rückwärts-Lookup CSV-Key → Anzeigename |
| `get_logo_path()` | Gibt Logo-Pfad zurück oder None |
| `get_logo_aspect(path)` | Seitenverhältnis des Logos (h/w) |

---

## 10. Wichtige Streamlit-Patterns & Workarounds

### 10.1 Widget-Key Reset
Streamlit erlaubt **keine direkte Zuweisung** an aktive Widget-Keys (`st.session_state["key"] = value` → Error). Workarounds:

- **Counter-basierte Keys:** `key=f"widget_{counter}"` → Counter hochzählen + rerun → neuer Key → frischer Default
  - Verwendet bei: Datum-Reset-Buttons
- **Key löschen + rerun:** `del st.session_state["key"]` → Widget rendert mit Default
  - Verwendet bei: Musterportfolio laden (Multiselect)
- **Separate Flags:** Wert in eigenem Key speichern, Widget liest beim nächsten Render

### 10.2 Dynamische Kosten-Keys
```python
fee_key_1 = f"p_fee1_{portfolio_name}"
if fee_key_1 not in st.session_state:
    st.session_state[fee_key_1] = default_value
```
Problem: `st.number_input(value=...)` wird nur beim ersten Render beachtet. Lösung: Key enthält Portfolio-Name → bei Portfolio-Wechsel neuer Key → neuer Default.

### 10.3 Multiselect nur zum Hinzufügen
```python
# NICHT: default=current_selection (→ Sync-Probleme)
# STATTDESSEN: default=[] + separate Add-Logik
new_titles = st.multiselect(..., default=[], key="builder_add_titles")
if new_titles:
    for lbl in new_titles:
        _add_to_portfolio(wkn, 0.0)  # Nur hinzufügen, nie überschreiben
```

### 10.4 Type Hints
Python 3.9 kompatibel: Keine `float | None` oder `list[str]` Type Hints verwenden. Stattdessen `float` oder `list` ohne Parameter.

---

## 11. Farbschema

| Name | Hex | Verwendung |
|---|---|---|
| FFPB Dark | #1B3A5C | Dunkelblau, Chart-Hintergrund, Header |
| FFPB Gold | #B8973A | Primärfarbe, Balken, Fälligkeitsstruktur |
| FFPB Light | #A8CBE8 | Hellblau, Benchmark-Balken |
| FFPB Blue2 | #2C5F8A | Mittelblau, zweites Portfolio |

### Top 5 Holdings Farben (Corporate Design)
```python
TOP5_COLORS = ["#1B3A5C", "#6A9BC3", "#B8973A", "#C4B78C", "#A8CBE8"]
# Dunkelblau → Mittelblau → Gold → Beige → Hellblau (absteigend nach Gewicht)
```

### Ring-Diagramm Farben
```python
RING_COLORS = ["#B8973A", "#2C5F8A", "#A8CBE8", "#7FB5D5", "#1B3A5C",
               "#E8A838", "#5BA0D0", "#C4C4C4", "#3A7CA5", "#D4A84B", ...]
```

---

## 12. Bekannte Einschränkungen & TODOs

### Einschränkungen
- **Portfolio Builder:** Nur Strukturanalyse, keine Performance-Analyse (keine Zeitreihen für Einzeltitel)
- **Duration im Portfolioanalyse-Tab:** Kommt aus separater Datei (Portfolio-Ebene), nicht aus Einzeltiteln
- **Duration im Builder-Tab:** Wird gewichtet aus Einzeltitel-Duration berechnet (Mehrwert gegenüber PF-Tab)
- **Builder-Portfolio:** Geht bei Logout verloren (Session-basiert)
- **Multiselect-Performance:** Bei sehr großem Universum (>1000 Titel) kann der Multiselect langsam werden

### Mögliche Erweiterungen
- PDF-Export für den Portfolio Builder
- Historische Performance-Simulation für Builder-Portfolios (wenn Einzeltitel-Zeitreihen verfügbar)
- Persistente Speicherung von Builder-Portfolios (Datenbank/File)
- Vergleich mehrerer Builder-Portfolios untereinander
- ESG-Kennzahlen Integration

---

## 13. Deployment-Checkliste

1. **Dateien auf GitHub pushen** (alle 4 Python-Dateien + requirements.txt)
2. **Ordner erstellen:** Daten/, Daten_PF/, Duration/, Zieldaten/
3. **CSVs hochladen** in die jeweiligen Ordner
4. **Mapping-Dateien** (Mapping_Honorarsatz.xlsx, Mapping_Namen.xlsx) im Root
5. **Logo** (Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg) im Root
6. **Secrets konfigurieren** auf Streamlit Cloud: Settings → Secrets → `[passwords]`
7. **Python-Version:** 3.10+ (3.14 auf Cloud bestätigt funktionierend)

---

*Dokumentation erstellt: April 2026*  
*Codestand: ~2.220 Zeilen über 4 Module*
