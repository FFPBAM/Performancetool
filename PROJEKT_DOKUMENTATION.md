# FFPB Streamlit Tool – Projektdokumentation & Transferwissen
## Stand: Mai 2026

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

### 7. Cache muss nach Daten-Struktur-Änderungen geleert werden

**Situation:** Du änderst die Struktur einer CSV (neue Spalte, andere Reihenfolge, Spalte ersetzt) UND die Funktion die die CSV einliest ist mit `@st.cache_data` dekoriert.

**Falle:** Streamlit Cloud cached den DataFrame im alten Format. Auch nach Code-Deploy zeigt die App alte Daten / wirft KeyError auf die neue Spalte. Lokal sieht alles gut aus, in der Cloud crasht es.

**Lösung:** Nach JEDEM Daten-Struktur-Change einmal Cache leeren:
- Streamlit Cloud: "Manage app" → "Reboot app" (löscht ALL cached data)
- Alternativ: User klickt im 3-Punkte-Menü oben rechts "Clear cache"
- Im Code beim Testen: `st.cache_data.clear()` einmalig ausführen

**Betroffen in diesem Projekt:** `build_portfolio_timeseries`, `load_all_csvs`, `load_mapping`, `load_name_mapping` — alles `@st.cache_data`.

---

### 8. Dezimal-/Prozent-Auto-Erkennung bei numerischen CSV-Spalten

**Situation:** Eine CSV-Spalte könnte Werte als Dezimal (0,03928) oder Prozent (3,928) enthalten — verschiedene Datenquellen, verschiedene Konventionen.

**Falle:** Wenn du hartcodierst "ist immer Dezimal" und jemand liefert mal Prozent, ist deine ganze Berechnung um Faktor 100 falsch. Stille Fehler, schwer zu finden.

**Lösung:** Median-basierte Auto-Erkennung. Wenn der Median der Beträge > 1 ist → war Prozent, durch 100 teilen.

```python
rf_raw = vv.loc[1:, "Risiko freier Zins"].to_numpy(dtype=float)
if np.nanmedian(np.abs(rf_raw[~np.isnan(rf_raw)])) > 1.0:
    rf_raw = rf_raw / 100.0
```

Diese Logik wird in diesem Projekt schon länger bei `to_decimal_interval()` für Performance-Werte verwendet — wird jetzt analog auf rf angewendet.

---

### 9. Negative Werte in Finanzzeitreihen einplanen

**Situation:** Eine Finanzkennzahl die "normalerweise positiv" ist kann unter bestimmten Marktbedingungen negativ werden — z.B. der risikofreie Zins während der EZB-Negativzinsphase (ca. 2015-2022 für EUR-Geldmarktsätze, bis -0,5% EONIA).

**Falle:** Helper-Funktionen die mathematische Operationen auf positiven Werten testen aber nicht auf negativen, brechen oder liefern falsche Ergebnisse. Typische Stolpersteine:
- `growth ** (1/n)` mit negativem `growth` → komplexe Zahl oder NaN
- `log(rf)` für negative rf → ungültig
- Schutzbedingung `if value > 0` schließt versehentlich negative aus

**Lösung:** Bei jeder Helper-Funktion explizit prüfen ob sie mit negativen Werten umgehen muss, und Tests dafür schreiben. In diesem Projekt:
- `aggregate_rf_geometric()`: arbeitet mit `(1 + rf)` statt `rf` direkt → für rf > -100% mathematisch wohldefiniert (rf-Werte um -0,5% kein Problem)
- `make_index_from_rf()`: Index sinkt bei negativem rf — visuell korrekt
- Schutzbedingung `if growth <= 0: return None` fängt nur unrealistische Edge Cases

**Validiert in diesem Projekt:** Mit echter 17-Jahres-Zeitreihe (2008-2026) inkl. Negativzinsphase. Konstantes rf = -0,5% wird exakt als -0,5% zurückaggregiert.

**Wichtig für UI/Beratung:** Bei Zeitraum-Auswahl die VOLLSTÄNDIG in der Negativzinsphase liegt (z.B. nur 2018-2020), zeigt die Caption `Ø Risikofreier Zins p.a. (Zeitraum): -0,25%` an. Das ist KEIN Bug, sondern die wirtschaftliche Realität jener Jahre.

---

## 1. Projektübersicht

Streamlit-App für Fürst Fugger Privatbank mit 3 Tabs.

| Tab | Datei | Zeilen | Zweck |
|---|---|---|---|
| 📈 Performance | `streamlit_app.py` | ~960 | Historische Performance, Kennzahlen (inkl. Sharpe), Charts, PDF+Glossar |
| 📊 Portfolioanalyse | `modules/portfolioanalyse.py` | ~780 | Strukturanalyse: Ringe, Tabellen, Anleihen-Detail, PDF |
| 📋 Portfolio zusammenstellen | `modules/portfolio_builder.py` | ~695 | Individueller Portfolio-Aufbau durch Berater |
| (gemeinsam) | `modules/shared.py` | ~190 | Konstanten, Login, Formatierung, Font-Setup |

**Gesamt: ~2.625 Zeilen | Deployment: Streamlit Cloud via GitHub | Python 3.10+**

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

## 6. CSV-Datenstrukturen

### 6.1 Performance-CSVs (`Daten/`)

**Encoding:** ISO-8859-1, Separator `;`, Decimal `,`, Thousands `.`
**Dateinamen-Pattern:** `*_<yyMMdd>_*.CSV` (Date-Tag wird per Regex extrahiert)
**Erste Zeile** enthält Metadaten (Portfolio-Name, Benchmark-Name), **ab Zeile 2** beginnen die Tageswerte. Die erste Zeile wird beim Einlesen weggeworfen (`vv.loc[1:]`).

**Spalten (Stand Mai 2026, nach Umstellung Währung → rf):**

| # | Spalte | Inhalt | Format |
|---|---|---|---|
| 1 | `Portfolio Name` | CSV-Key, mappt auf Anzeigenamen | String |
| 2 | `Datum` | Tageswert-Datum | `DD.MM.YYYY` |
| 3 | `Performance [%] (Intervall)` | Tagesperformance Portfolio | Prozent (z.B. `0,12`) |
| 4 | `Performance (Intervall)` | (ungenutzt im Code) | – |
| 5 | `Performance [%] (kumuliert)` | (ungenutzt im Code) | – |
| 6 | `Performance (kumuliert)` | (ungenutzt im Code) | – |
| 7 | `Benchmark Performance [%] (Intervall)` | Tagesperformance Benchmark | Prozent |
| 8 | `Risiko freier Zins` | Annualisierter risikofreier Zins | Dezimal (z.B. `0,03928`) |

**Historische Anmerkung:** Spalte 8 enthielt früher `Währung` (String, z.B. "EUR") und wurde **nicht im Code verwendet**. Im Mai 2026 wurde die Spalte ersetzt durch `Risiko freier Zins`. Die alten CSVs ohne rf-Spalte werden vom Code abgefangen (Fallback `NaN`).

**Auto-Format-Erkennung:** Für `Performance [%]` und `Risiko freier Zins` ist Median-basierte Auto-Erkennung implementiert (siehe Transferwissen #8). Werte können also auch als Prozent (3,928) statt Dezimal (0,03928) geliefert werden — werden automatisch konvertiert.

### 6.2 Mapping-Dateien

**`Mapping_Honorarsatz.xlsx`:**
- Spalte `Inhaber` (= Portfolio Name aus CSV)
- Spalte `Honorarsatz Standard` (Dezimal, z.B. 0.015 für 1,5%)

**`Mapping_Namen.xlsx`:**
- Spalte A: Anzeigename (was der User sieht)
- Spalte B: CSV-Key (= Portfolio Name in CSVs)
- Spalte C: Duration
- Spalte D: Benchmark-Zusammensetzung (Text, wird unter Charts angezeigt)

---

## 7. Tab 1: Performance

### Layout & Aufbau
- Hinweis + Quelle oben, Disclaimer unten
- Sidebar: Portfolio, Vergleich, Checkboxen (Vor Kosten, Benchmark, **Risikofreier Zins**, Drawdown, Tabelle, Balken), Kosten (dynamischer Key), MwSt (×1.19)
- Zeitraum: Datumspicker + Reset-Buttons (Counter-Keys, siehe Transferwissen #4)

### Kennzahlen (zwei Reihen)
**Reihe 1:** Auflagedatum im PM | ⌀ Rendite p.a. (CAGR) | Volatilität p.a.
**Reihe 2:** Calmar Ratio | **Sharpe Ratio** | Endwert (nur wenn Anlagevolumen > 0)
**Darunter als Caption:** `Ø Risikofreier Zins p.a. (Zeitraum): X,XX%`

**Sharpe-Berechnung:** Wissenschaftlich saubere Variante nach Sharpe (1994) auf Basis täglicher Excess Returns — NICHT die p.a.-Approximation. Details siehe Abschnitt 11.

### Charts
- Linien-Chart: Endwerte als legendgroup-gebundene Text-Traces, Legende "Strategie" rechts
- **rf-Linie:** Optional per Sidebar-Checkbox `Risikofreier Zins` (Default aus). Wird aus täglich variablem rf zinstaggenau aufkompoundiert via `make_index_from_rf()`. Bei fehlenden Daten → freundliche Info-Caption statt Crash.
- Balken-Chart: `_rb()` Funktion mit `suffix="p1"/"p2"` (siehe Transferwissen #3)

### PDF
- Meta-Block: Portfolio, Zeitraum, Kosten, Anlagevolumen, **Ø Risikofreier Zins p.a. (Zeitraum)**, Quelle
- Kennzahlen: in `" | "`-Pipe-Liste, jetzt inkl. Sharpe direkt nach Calmar
- Chart: rf-Linie wird mitgenommen wenn aktiv
- Disclaimer-Seite
- Glossar (11 Begriffe): Auflagedatum, CAGR, Vola, Calmar, **Sharpe Ratio**, **Ø Risikofreier Zins p.a. (Zeitraum)**, Max DD, Recovery, Längste DD-Phase, Benchmark, Vor/Nach Kosten

### Disclaimer-Wording
*"Alle Berechnungen sind unverbindlich und **erfolgen** ohne Gewähr."*

---

## 8. Tab 2: Portfolioanalyse

- `_render_single_portfolio()` mit `suffix="pf1"/"pf2"` (siehe Transferwissen #3)
- Ring-Diagramme: Absteigend sortiert, Labels außen (13px), <3% ausgeblendet, Legende horizontal unten
- YTD: Spalten ausgeschrieben (Wertpapier-Performance/Performancebeitrag), Caption erklärt beide
- PDF (aktuell reportlab): Ring-Charts kompakter (100×85mm), intelligente Spaltenbreiten
- **Geplant: Umstellung auf PowerPoint (python-pptx)**
- Disclaimer: "Alle Angaben **erfolgen** ohne Gewähr."

---

## 9. Tab 3: Portfolio zusammenstellen

- Schnellzugriffe (9 Buttons) → setzen Filter via session_state
- Filter: Hauptfilter sichtbar, erweiterte als Checkbox (NICHT Expander!)
- Suche: Multiselect mit `default=[]` (NUR hinzufügen, nie syncen)
- Cash: Input + Residual + Hinweis
- Export: Excel (.xlsx, nicht CSV wegen Encoding)
- `_show_builder_disclaimer(zm_hint)` bei JEDEM return + am Ende
- Filter-Defaults: Duration max=30.0, Risiko max=7 (siehe Transferwissen #5)

---

## 10. Disclaimers

Alle 3 Tabs: Hinweis + Quelle oben, Disclaimer unten, in PDFs als eigene Seite.

| Tab | Schlüsselsatz |
|---|---|
| Performance | "Alle Berechnungen sind unverbindlich und erfolgen ohne Gewähr." |
| Portfolioanalyse | "Alle Angaben erfolgen ohne Gewähr." |
| Builder | "Alle Angaben sind ohne Gewähr." + Produktgovernance |

Quelle: Infront & eigene Berechnungen | Ansprechpartner: PBAM

---

## 11. Berechnungsformeln

```
daily_drag      = (1 + fee_pa)^(1/365) - 1
idx_nach_kosten = idx[i-1] * (1 + ret - daily_drag)
cagr            = (endwert/startwert)^(365/tage) - 1
vola            = std(tagesrenditen) * sqrt(365)
calmar          = cagr / |max_drawdown|
gew_duration    = Σ(gewicht × duration) / Σ(gewichte_anleihen)
```

### Sharpe Ratio – wissenschaftlich saubere Variante nach Sharpe (1994)

Wir nutzen NICHT die häufige Approximation `(CAGR − rf_pa) / Vola_pa`, sondern die mathematisch korrekte Variante auf Basis täglicher Excess Returns:

```
# 1. Annualisierten rf pro Tag in Tagessatz wandeln
daily_rf[t]   = (1 + rf_annual[t])^(1/365) - 1

# 2. Tägliche Überrendite des Portfolios
excess[t]     = ret_port_nachKosten[t] - daily_rf[t]

# 3. Sharpe auf Tagesbasis
sharpe_daily  = mean(excess) / std(excess, ddof=1)

# 4. Annualisierung
sharpe_p.a.   = sharpe_daily × √365
```

**Warum diese Variante:** Zähler (Mittelwert) und Nenner (Standardabweichung) basieren auf **derselben** Excess-Return-Zeitreihe. Das entspricht Sharpe's eigener Definition (1994, "The Sharpe Ratio", JPM) und ist robust bei stark schwankenden rf-Zeitreihen (z.B. Zinswende-Phasen).

**Unterschied zur p.a.-Approximation:** Bei konstantem rf liegen beide Varianten dicht beieinander (Differenz < 0,02), bei stark variablem rf wird der Unterschied spürbar. Beispiel-Validierung (3-Jahres-Zeitreihe, rf von 0 → 4%): klassisch 1,04 vs. Excess-Variante 1,02.

**Validierung mit echten Daten (Mai 2026):** Mit einer 17-Jahres-rf-Zeitreihe (2008-2026, ~6300 Tageswerte) getestet. Die Zeitreihe enthält Niedrigzinsphase, Negativzinsphase (rf bis -0,33%) und Zinswende (rf bis +3,99%). Alle Helper-Funktionen liefern plausible Werte. Negative rf-Werte werden mathematisch korrekt verarbeitet (siehe Transferwissen #9).

Implementiert in `calc_sharpe_excess(draf, df["rf"])` in `streamlit_app.py`.

### Risikofreier Zins – Aggregation (geometrisch, nur für Anzeige)

Wird **nur** für die Caption-Anzeige `Ø Risikofreier Zins p.a. (Zeitraum)` und die PDF-Meta-Zeile verwendet — NICHT für die Sharpe-Berechnung. Die Sharpe nutzt die tägliche rf-Zeitreihe direkt (siehe oben).

Eingabe: Zeitreihe annualisierter rf-Werte (z.B. 0,03928 = 3,928% p.a.) pro Handelstag.

```
# 1. Tagessatz aus annualisiertem rf
daily_rf = (1 + rf_annual)^(1/365) - 1

# 2. Alle Tagessätze über den Zeitraum kompoundieren
growth = Π (1 + daily_rf)

# 3. Zurück auf p.a. annualisieren
rf_pa = growth^(365 / n_days) - 1
```

**Validierung:** Konstanter rf von 3,928% kommt nach Aggregation exakt als 3,928% zurück (0 ppm Differenz). Implementiert in `aggregate_rf_geometric()` in `streamlit_app.py`.

### rf-Index für Chart

Jeder Tag verzinst sich mit seinem eigenen Tagessatz:
```
daily_rf[i] = (1 + rf_annual[i])^(1/365) - 1
idx[i]      = idx[i-1] * (1 + daily_rf[i])
```
Startwert = Anlagevolumen (wenn gesetzt) oder 100. Implementiert in `make_index_from_rf()`.

---

## 12. Geplante nächste Schritte

1. **Portfolioanalyse PDF → PowerPoint** (python-pptx, 16:9, Fuggerblau/Fuggergold)
2. Performance-Charts auf neue Corporate Colors umstellen
3. Compliance-Feedback abwarten → Disclaimer ggf. anpassen
4. Ggf. Sharpe + rf-Linie auch in Portfolioanalyse-Tab (aktuell nur Tab 1)

---

## 13. Changelog

### Mai 2026 (Validierung) – Echtdaten-Test mit 17-Jahres-Zeitreihe
- Sharpe-Berechnung und rf-Verarbeitung mit echter Zeitreihe (31.12.2008 – 12.05.2026, ~6300 Tageswerte) validiert
- Zeitreihe enthält alle drei relevanten Zins-Regime: Niedrigzins (2008-2014), Negativzins (2015-2022, bis -0,33%), Zinswende (2022-2024, bis +3,99%)
- Bestätigt: Auto-Format-Erkennung greift korrekt (Median ≈ 0,014 → als Dezimal erkannt, keine Fehl-Division)
- Bestätigt: Negative rf-Werte mathematisch korrekt verarbeitet — rf-Index sinkt bei negativem rf, was visuell der wirtschaftlichen Realität entspricht
- Bestätigt: Sharpe Ratio mit Excess-Return-Variante über kompletten Zeitraum plausibel
- Transferwissen #9 (Negative Werte in Finanzzeitreihen) ergänzt

### Mai 2026 (Update) – Sharpe Ratio auf Excess-Return-Variante
- `calc_sharpe(cagr, rf_pa, vola)` ersetzt durch `calc_sharpe_excess(draf, rf_series)`
- Sharpe nun nach Sharpe (1994): Mittelwert und Standardabweichung auf täglicher Excess-Return-Zeitreihe, anschließend × √365
- Vorher: p.a.-Approximation `(CAGR − rf_pa) / Vola_pa`
- Tooltips, PDF-Glossar und Doku-Formeln entsprechend aktualisiert
- `aggregate_rf_geometric()` bleibt erhalten — wird nur noch für die Caption- und PDF-Meta-Anzeige des Ø rf verwendet, nicht mehr für die Sharpe-Berechnung
- Defensive Bedingung: Sharpe nur berechnet wenn `df["rf"]` existiert UND mindestens einen Nicht-NaN-Wert enthält

### Mai 2026 – Risikofreier Zins & Sharpe Ratio (Erstimplementierung)
- CSV-Spalte 8 `Währung` (ungenutzt) ersetzt durch `Risiko freier Zins` (annualisiert, dezimal)
- `build_portfolio_timeseries` liest neue Spalte ein, mit Fallback `NaN` für alte CSVs
- Auto-Format-Erkennung (Dezimal vs. Prozent) via Median > 1
- Neue Helper: `aggregate_rf_geometric()`, `calc_sharpe()`, `make_index_from_rf()`
- Kennzahlen-Layout auf 2 Reihen umgestellt (Reihe 2: Calmar / Sharpe / Endwert)
- Caption mit `Ø Risikofreier Zins p.a. (Zeitraum)` unter den Kacheln
- Neue Sidebar-Checkbox `Risikofreier Zins` (Default aus) für Chart-Linie
- Join-Logik bei Vergleichsportfolio: rf-Spalte wird mitgezogen
- PDF erweitert: rf in Meta, Sharpe in Kennzahlen, rf-Linie im Chart, 2 neue Glossar-Einträge
- Transferwissen #7 (Cache leeren bei Daten-Struktur-Änderungen) ergänzt
- Transferwissen #8 (Dezimal-/Prozent-Auto-Erkennung) ergänzt

### April 2026 – Initiale Doku-Version
- 6 Transferwissen-Einträge
- 3 Tabs strukturiert dokumentiert
- Corporate Design + Schriftarten festgehalten

---

## 14. Für den nächsten Chat / Kollegen

**Hochladen:** Diese MD + alle 4 Code-Dateien (`streamlit_app.py`, `modules/shared.py`, `modules/portfolioanalyse.py`, `modules/portfolio_builder.py`)
**Sagen:** "Lies die PROJEKT_DOKUMENTATION.md zuerst komplett. Dann [Aufgabe]."
**Bei Problemen:** Screenshot + erwartetes Verhalten

**Wichtig bei CSV-Änderungen:** Nach Deploy IMMER Cache leeren (Transferwissen #7).

*Stand: Mai 2026*
