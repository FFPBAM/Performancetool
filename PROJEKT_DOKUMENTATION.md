# FFPB Streamlit Tool – Projektdokumentation & Transferwissen
## Stand: Juni 2026

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

### 10. Plotly Default-Farben überschreiben: `colorway` im Layout

**Situation:** Ein Plotly-Chart mit mehreren Traces (Linien, Balken, Bereiche) soll Corporate-Farben statt der Plotly-Standard-Palette (Blau/Rot/Grün/Lila) nutzen.

**Falle (umständlicher Weg):** Jedem `go.Scatter(...)` oder `go.Bar(...)` einzeln `marker_color=...` oder `line=dict(color=...)` setzen. Bei 5-10 Traces ist das fehleranfällig (Index-Fehler, vergessene Trace) und unübersichtlich.

**Lösung:** Einmal `colorway` im Layout setzen — Plotly weist Traces dann automatisch in der gegebenen Reihenfolge zu:

```python
fig = go.Figure()
fig.add_trace(go.Scatter(x=x, y=y1, name="Portfolio 1"))
fig.add_trace(go.Scatter(x=x, y=y2, name="Portfolio 2"))
fig.add_trace(go.Scatter(x=x, y=y3, name="Benchmark"))

fig.update_layout(colorway=FFPB_PALETTE)  # ← eine Zeile, fertig
```

`y1` bekommt `FFPB_PALETTE[0]` (Fuggerblau), `y2` `FFPB_PALETTE[1]` (Fuggergold), `y3` `FFPB_PALETTE[2]` (Mittelblau) etc. Bei mehr als 15 Traces (extrem unwahrscheinlich) wird zyklisch von vorne durchlaufen.

**Achtung bei dunklen Hintergründen:** Wenn der Plot-Hintergrund Fuggerblau ist (z.B. der Balken-Chart `paper_bgcolor=FFPB_DARK`), wäre die erste Palette-Farbe unsichtbar. Lösung: `colorway=FFPB_PALETTE[1:]` oder explizite `marker_color`-Zuweisung pro Trace.

**Implementiert in diesem Projekt:** `streamlit_app.py` Hauptlinien-Chart (Z. 874), Drawdown-Chart Euro/% (Z. 898, 902). PDF-matplotlib-Charts nutzen `FFPB_PALETTE[1:]` aus dem gleichen Grund (Hintergrund-Skip).

---

### 11. Import-Änderungen brauchen IMMER gleichzeitiges Deployment der referenzierten Datei

**Situation:** Du erweiterst den Import in Datei A:
```python
# A.py
from B import KONSTANTE_ALT, KONSTANTE_NEU  # KONSTANTE_NEU neu hinzugefügt
```
Und definierst `KONSTANTE_NEU` in `B.py`.

**Falle:** Wenn du nur `A.py` ins Repo pushst aber `B.py` vergisst (oder die alte Version von B oben drüber lädst), crasht die App beim Start mit `ImportError: cannot import name 'KONSTANTE_NEU' from 'B'`.

**Klingt trivial.** Ist in der Praxis aber **DER häufigste Deployment-Fehler**, weil:
- Die ältere Datei lokal im Editor-Cache "richtig aussieht"
- Der Push-Workflow (z.B. Drag-and-Drop in GitHub Desktop) übersieht stille Dateien
- Streamlit Cloud zeigt nur den Crash, nicht welche Datei nicht-aktuell ist
- Mehrfaches "Reboot app" ändert nichts (die Datei IST falsch im Repo)

**Lösungen:**

1. **Vor jedem Commit ein Pärchen-Check:** Wenn ein Import-Block einer Datei geändert wurde, kontrollieren ob alle referenzierten Module wirklich gleichzeitig aktualisiert wurden.

2. **GitHub Web-Editor als Notfall-Workflow:** Falls lokaler Datei-Sync hängt, direkt im Browser unter `github.com/<user>/<repo>/blob/main/<datei>` über das Bleistift-Icon editieren. Umgeht jeden lokalen Upload-Stolperstein.

3. **Bei ImportError zuerst in den App-Logs nachschauen:** Streamlit Cloud-Logs (`Manage app` → Logs) zeigen den genauen Namen, der nicht importiert werden kann. Daraus ist sofort klar welche Datei fehlt/falsch ist.

**Real passiert in diesem Projekt (Juni 2026, Corporate Colors Migration):** `streamlit_app.py` wurde mit neuem Import auf `FFPB_SAND, FFPB_PALETTE` gepusht, `shared.py` lag aber noch in der alten Version im Repo. Vier "Reboot app" später war klar dass die `shared.py`-Datei lokal nicht ersetzt worden war. Fix: über GitHub Web-Editor direkt online editiert.

---

## 1. Projektübersicht

Streamlit-App für Fürst Fugger Privatbank mit 2 aktiven Tabs.

| Tab | Datei | Zeilen | Zweck |
|---|---|---|---|
| 📈 Performance | `streamlit_app.py` | ~990 | Historische Performance, Kennzahlen (inkl. Sharpe), Charts, PDF+Glossar |
| 📊 Portfolioanalyse | `modules/portfolioanalyse.py` | ~780 | Strukturanalyse: Ringe, Tabellen, Anleihen-Detail, PDF |
| (gemeinsam) | `modules/shared.py` | ~200 | Konstanten, Login, Formatierung, Font-Setup, Corporate-Palette |
| (PowerPoint-Export) | `modules/pptx_export.py` | ~850 | PPTX-Export aus Portfolioanalyse-Tab (geplant: auch Performance-Tab) |

**Gesamt aktiv: ~2.820 Zeilen | Deployment: Streamlit Cloud via GitHub | Python 3.10+**

**Nicht aktiv im Repo:** `modules/portfolio_builder.py` (~695 Zeilen) – seit Juni 2026 nicht mehr importiert (Compliance-Entscheidung: Berater dürfen keinen freien Portfolio-Builder nutzen). Datei bleibt für mögliche spätere Reaktivierung im Repo.

**Vorlage-Datei:** `Vorlage/Vorlage_FFPB.pptx` – PowerPoint-Master mit Corporate-Design, benannten Shapes und 24 Slides. Wird von `pptx_export.py` als Template genutzt.

---

## 2. Dateistruktur

```
Repository Root/
├── streamlit_app.py
├── modules/
│   ├── __init__.py
│   ├── shared.py
│   ├── portfolioanalyse.py
│   ├── pptx_export.py               ← PowerPoint-Export (Portfolioanalyse + geplant Performance)
│   └── portfolio_builder.py         ← deaktiviert seit Juni 2026
├── Vorlage/
│   └── Vorlage_FFPB.pptx            ← Corporate-Master, 24 Slides, benannte Shapes
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
├── Zieldaten/                       ← Anlageuniversum für Builder (deaktiviert)
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
python-pptx>=1.0                     ← für pptx_export.py
lxml>=4.9                            ← für pptx_export.py (XML-Manipulation der Charts)
```

---

## 3. Abhängigkeiten

```
shared.py ──→ streamlit_app.py (Tab 1 inline + importiert Tab 2)
          ──→ portfolioanalyse.py ──→ pptx_export.py (für PowerPoint-Export)
          ──→ pptx_export.py (geplant: auch von streamlit_app.py)
```

`portfolio_builder.py` liegt im Repo, wird aber nicht importiert (siehe Abschnitt 1).
`pptx_export.py` nutzt `Vorlage/Vorlage_FFPB.pptx` als Master-Template.

---

## 4. Corporate Design

**Seit Juni 2026 nutzen beide Tabs durchgängig die offiziellen Fürst Fugger Privatbank Corporate Colors.**
Single source of truth ist `modules/shared.py` — dort sind alle 5 Hauptfarben + erweiterte 15er-Sequenz als Konstanten definiert. Alle anderen Module importieren von dort.

### Hauptfarben (Konstanten in `shared.py`)

| Konstante | Hex | Name | Hauptverwendung |
|---|---|---|---|
| `FFPB_DARK` | #003460 | Fuggerblau | PDF-Headlines, Tabellen-Kopfzeile, Balken-Chart Hintergrund, Ring-Chart größtes Segment |
| `FFPB_GOLD` | #C3A069 | Fuggergold | Akzent, Portfolio-Balken, Fälligkeits-Balken, Ring-Chart zweites Segment |
| `FFPB_BLUE2` | #4A7FAA | Mittelblau | Portfolio 2 (Vergleich), Ring-Chart drittes Segment |
| `FFPB_SAND` | #D4BD8A | Sand | Benchmark 2 (Vergleich), Ring-Chart viertes Segment |
| `FFPB_LIGHT` | #7FABC8 | Hellblau | Benchmark, Ring-Chart fünftes Segment |

### Erweiterte 15er-Sequenz für Linien-Charts (`FFPB_PALETTE`)

```python
FFPB_PALETTE = [
    "#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8",   # Hauptfarben
    "#8B7340", "#A8CBE8", "#5C6B3C", "#E8D5B0", "#2C5F8A",   # Erweiterung 1
    "#C4C4C4", "#3A7CA5", "#F0C070", "#6A9BC3", "#2A4A6C",   # Erweiterung 2
]
```

**Verwendung:**
- **Plotly Linien-Charts (Tab 1):** `fig.update_layout(colorway=FFPB_PALETTE)` — Plotly weist Traces automatisch in dieser Reihenfolge zu (siehe Transferwissen #10).
- **PDF Linien-Chart matplotlib:** `FFPB_PALETTE[1:]` (Index 0 = Fuggerblau = Hintergrund → würde unsichtbar; deshalb ab Index 1 starten).
- **Portfolioanalyse `RING_COLORS`:** Identische 15-Werte-Sequenz, in `modules/portfolioanalyse.py` separat definiert (historisch gewachsen, könnte langfristig auf `FFPB_PALETTE` zusammengeführt werden).

### Spines & Gridlines (PDF/Plotly auf dunklem Hintergrund)

Bei Balken-/Linien-Charts mit Fuggerblau-Hintergrund:
- **Spines (Achsen-Linien):** `#1A4880` (heller als BG, dezent sichtbar)
- **Gridlines:** `#0A4576` (sehr subtil, deutet nur an)

Diese Werte sind hartcodiert in `streamlit_app.py` (vier Stellen: Plotly-Balken-Chart, PDF-Linien-, PDF-Drawdown-, PDF-Bar-Chart) und konsistent mit der Hintergrundfarbe `FFPB_DARK` abgestimmt.

### Historischer Kontext

Vor Juni 2026 nutzte das Performance-Tool ein eigenes, ähnliches aber nicht identisches Farb-Set (`#1B3A5C` als FFPB_DARK, `#B8973A` als FFPB_GOLD, etc.). Die Portfolioanalyse hatte schon vorher die Corporate Colors als hartcodierte Werte in `RING_COLORS`. Im Juni 2026 wurde **shared.py auf Corporate umgestellt** (Strategie A: Konstanten umdefinieren statt neue anlegen), damit beide Tabs durchgängig dasselbe Design haben. Dies betraf zusätzlich die PDF-Header/Tabellenkopfzeilen der Portfolioanalyse (Fuggerblau statt Dunkelblau-Annäherung).

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
*"Dieses Performancetool dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. Alle Berechnungen sind unverbindlich und erfolgen ohne Gewähr."*

---

## 8. Tab 2: Portfolioanalyse

- `_render_single_portfolio()` mit `suffix="pf1"/"pf2"` (siehe Transferwissen #3)
- Ring-Diagramme: Absteigend sortiert, Labels außen (13px), <3% ausgeblendet, Legende horizontal unten
- YTD: Spalten ausgeschrieben (Wertpapier-Performance/Performancebeitrag), Caption erklärt beide
- PDF (reportlab): Ring-Charts kompakter (100×85mm), intelligente Spaltenbreiten
- **PowerPoint-Export aktiv** (`modules/pptx_export.py` + `Vorlage/Vorlage_FFPB.pptx`):
  - Slides 7-8: Anlagevorschlag (Tabelle pro Gattung + Allokations-Ring)
  - Slide 9: Aktuelle Portfoliozusammenstellung (Regionen + Branchen-Ringe)
  - Slide 10 (Währungen) wird entfernt — keine Währungs-Daten verfügbar
  - Bei Vergleichsportfolio: Slides 7-9 werden dupliziert (3 weitere Slides für Portfolio 2)
  - Details siehe Abschnitt 10 "PowerPoint-Export-System"
- Disclaimer: *"Diese Portfolioanalyse dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. Alle Angaben sind ohne Gewähr."*

---

## 9. Disclaimers

Beide Tabs: Hinweis + Quelle oben, Disclaimer unten, in PDFs als eigene Seite.

| Tab | Schlüsselsatz |
|---|---|
| Performance | "Dieses Performancetool dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. Alle Berechnungen sind unverbindlich und erfolgen ohne Gewähr." |
| Portfolioanalyse | "Diese Portfolioanalyse dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. Alle Angaben sind ohne Gewähr." |

**Wording-Historie:** Bis Mai 2026 hieß es "im Beratungsgespräch". Im Juni 2026 wurde dies — in Abstimmung mit Compliance — auf das aktuelle Wording umgestellt, um klarzustellen, dass die Tools nur im Rahmen der Vermögensverwaltung zur Veranschaulichung dienen (nicht zur Anlageberatung).

Quelle: Infront & eigene Berechnungen | Ansprechpartner: PBAM

---

## 10. PowerPoint-Export-System

Das PowerPoint-Export-System ist ein zentraler Baustein für die Kunden-Kommunikation. Beide Tabs (Performance + Portfolioanalyse) erzeugen aus denselben Daten eine fertig formatierte PPTX-Datei, die der Berater an Kunden weiterleiten kann.

### 10.1 Architektur-Prinzip "B2" — jeder Tab füllt nur eigene Folien

Beim PPTX-Export gibt es **keine** zentrale "alles in einem"-Funktion. Jeder Tab hat seinen eigenen Export-Button und befüllt **nur seine eigenen Folien**:

| Tab | Befüllt Slides | Entfernt Slides |
|---|---|---|
| 📊 Portfolioanalyse | 7-9 (Anlagevorschlag, Zusammenstellung) | 10-12 (Performance) — wenn vorhanden |
| 📈 Performance (geplant) | 10-12 (Wertentwicklung) | 7-9 (Anlagevorschlag) |

**Begründung:** Saubere Trennung. Der Berater entscheidet welcher Tab den Export erzeugt, und bekommt eine schlanke Datei mit nur den für ihn relevanten Folien.

### 10.2 Vorlage `Vorlage/Vorlage_FFPB.pptx`

24 Slides mit Corporate-Design der Fürst Fugger Privatbank. Wichtige Eigenschaften:

| # | Slide | Verwendung |
|---|---|---|
| 1 | Cover "Unsere Vermögensverwaltung" | statisch |
| 2 | Inhaltsverzeichnis | wird ggf. dynamisch angepasst (Performance-Eintrag nur wenn Performance-Folien drin) |
| 3-6 | Intro (Begrüßung, Die Fugger, VV-Konzept) | statisch |
| 7-8 | **Anlagevorschlag** (Aktien/Renten Tabelle + Allokations-Ring) | dynamisch befüllt von `pptx_export.py` |
| 9 | **Zusammenstellung** (Regionen + Branchen-Ringe) | dynamisch befüllt |
| ~~10~~ | ~~Währungen-Ring~~ | wird beim Export ENTFERNT (keine Daten) |
| 11+ | Honorar, Bank, Standorte, Tradition, Impressum | statisch |

**Geplante Erweiterung (Juni 2026):** Folien 10-12 sollen Performance-Folien werden (siehe Abschnitt 11 "Geplante Implementierungen").

### 10.3 Shape-Namen-Konvention

Die Vorlage nutzt **benannte Shapes**, damit `pptx_export.py` sie per Name finden und befüllen kann (statt per Index). Diese Konvention muss bei jeder Vorlagen-Änderung in PowerPoint eingehalten werden:

| Shape-Name | Typ | Verwendung |
|---|---|---|
| `Titel` / `Titel 2` | Placeholder | Folien-Headline (z.B. "Anlagevorschlag – Konservativ") |
| `C_Kennzahlen` | Chart | Großer Allokations-Ring (Slides 7, 8) |
| `T_Kennzahlen` | Tabelle | Positionen-Tabelle (Slides 7, 8) |
| `C_Kennzahlen1` | Chart | Linker Ring (Slide 9: Regionen) |
| `C_Kennzahlen2` | Chart | Rechter Ring (Slide 9: Segmente/Branchen) |
| `Fußnote` | Placeholder | Disclaimer-Text |
| `Quelle` | Textbox | "Quelle: Eigene Berechnung, Stand DD.MM.YYYY" |
| `Foliennummer` | Placeholder | Seitenzahl |

**Geplante Performance-Folien-Shapes** (für Slides 10-12):
- `Titel` — Wertentwicklung-Headline
- `Tabelle` — 4×2 Kennzahlen-Tabelle (Performance p.a., Vola, Sharpe, Max DD × Referenz/Benchmark)
- `Diagramm links` — Balken-Chart Performance p.a. (Kalenderjahre)
- `Diagramm rechts` — Linien-Chart Wertentwicklung
- `Header Diagramm links` / `Header Diagramm rechts` — Header-Textboxen
- `Legende Diagramm links` — Legende Balken-Chart
- `Fußnote` — Disclaimer
- `Quelle` — Quelle/Stand

### 10.4 Strategienamen-Normalisierung

`clean_strategy_name()` in `pptx_export.py` entfernt unerwünschte Präfixe vor der Anzeige:
- `"cVV Konservativ"` → `"Konservativ"`
- `"Stiftung Konservativ"` → `"Konservativ"`
- `"Muster Konservativ cVV"` → `"Konservativ"`

Präfixe-Liste: `STRATEGY_PREFIXES = ["cVV", "Muster", "Stiftung"]`. Wird sowohl am Anfang als auch am Ende entfernt. Erster Buchstabe wird groß geschrieben.

### 10.5 Slide-Duplikation für Vergleichsportfolio

`_duplicate_slide(prs, source_idx)` dupliziert eine komplette Slide inklusive:
- Aller Shape-Inhalte (per `deepcopy`)
- Chart-Parts (eigene XML-Datei pro Chart, damit Änderungen unabhängig sind — kritisch!)
- Image-Referenzen (geteilt, weil unveränderlich)
- Sub-Relationships (z.B. eingebettete XLSX-Files in Charts)

Nach Duplikation: **immer** `_save_and_reload(prs)` aufrufen, um interne Slide-IDs zu konsolidieren. Sonst "Duplicate name"-Warnungen beim späteren Speichern.

Bei 2 Portfolios: Slides 7-9 werden 3× dupliziert, dann umsortiert zu `[P1.S7, P1.S8, P1.S9, P2.S7, P2.S8, P2.S9]`, dann P2-Slides befüllt.

### 10.6 Chart-Befüllung — XML-basiert, NICHT über python-pptx CategoryChartData

**Wichtig:** Charts in Vorlagen können auf externe Excel-Dateien referenzieren (`xl/embeddings/`). Die python-pptx Standard-API `CategoryChartData` würde diese Referenzen brechen.

**Lösung:** `_replace_chart_data(chart_shape, categories, values)` manipuliert direkt das Chart-XML:
- Findet `<c:cat>` und `<c:val>` Elemente
- Tauscht `<c:pt>`-Punkte aus
- Updated `<c:ptCount>`
- Lässt externe Referenzen intakt

Diese Mechanik wurde experimentell entwickelt und ist robust gegen Vorlagen-Eigenheiten.

### 10.7 Positionen-Verteilung auf Slides 7+8

Slide 7 (asymmetrisch groß): max 34 Datenzeilen
Slide 8 (kleiner): max 12 Datenzeilen

Eine Gruppe (z.B. AKTIEN) darf über die Slide-Grenze fließen. Bei Aufteilung wird der Gruppen-Header auf Slide 8 wiederholt.

**Wichtige Regel — Tabellen-Struktur unverändert lassen:** Frühere Versuche, leere Tabellenzeilen zu entfernen, haben dazu geführt dass LibreOffice die Zeilenhöhen automatisch vergrößert und die Tabelle den Footer überlappt. Daher: leere Zeilen bleiben sichtbar leer (mit NBSP gefüllt), die Vorlagen-Höhen sind exakt auf die Slide-Höhe kalibriert.

### 10.8 Kritische Compliance-Anforderungen für PowerPoint-Export

Die PPTX wird an Kunden weitergegeben — alle nachfolgenden Regeln sind **nicht verhandelbar**:

| Anforderung | Umsetzung |
|---|---|
| **Anti-Cherry-Picking** | Performance-Folien zeigen **die gesamte verfügbare Historie**, nicht den Berater-Custom-Zeitraum |
| **Benchmark wenn gemappt** | Bei Portfolios mit gemappter Benchmark wird die BM **immer** angezeigt (UI-Schalter wird im Export ignoriert) |
| **Nur Nach Kosten** | "Vor Kosten"-Linien werden im Export **nie** gezeigt, auch wenn UI-Checkbox aktiv |
| **Strategieentwurf-Hinweis** | Folie 7 hat Überschrift "Strategieentwurf im Rahmen einer Vermögensverwaltung" statt "Anlagevorschlag" (Email-Anforderung Juni 2026) |
| **Disclaimer auf jeder Folie** | Standard-Wertentwicklungs-Disclaimer + Quelle + Stand |
| **Mindestens 5 Jahre Historie** | Durch "gesamte Historie zeigen" implizit erfüllt |
| **Custom-Zeitraum als separate Folie** | F3 "Berater-Auswahl" — transparent macht welcher Zeitraum tatsächlich vom Berater betrachtet wurde |
| **Strategienamen-Bereinigung** | `cVV`, `Muster`, `Stiftung` werden vor Anzeige entfernt |

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

## 12. Roadmap — Geplante Implementierungen

### 12.1 Aktuelle Aufgaben (Juni 2026 — Email-Anforderung Compliance)

Stand: alle Brainstorming-Punkte sind geklärt, Implementierung steht noch aus.

#### Aufgabe A: Strategieentwurf-Überschrift auf PPTX Folie 7
- **Was:** Überschrift "Anlagevorschlag" → "Strategieentwurf im Rahmen einer Vermögensverwaltung"
- **Wo:** Nur Folie 7 (nicht 8, 9)
- **Code:** In `pptx_export.py` → `_fill_anlagevorschlag_slides()` → bei Slide 7 den Titel-Shape mit dem festen neuen Text ersetzen, statt mit dem dynamischen "Anlagevorschlag – <Strategie>"
- **Zusatztext:** Kein Footer-Hinweis (nur Überschrift wird geändert)
- **Aufwand:** Trivial (~10 Min)

#### Aufgabe B: Seitenzahlen in PDF-Druckversionen
- **Was:** Seitenzahlen einfügen, wie in der PPTX-Vorlage
- **Wo:** `streamlit_app.py` (Performance-PDF) + `portfolioanalyse.py` (Portfolioanalyse-PDF)
- **Format:** Nur die Zahl (z.B. "7") — kein "Seite X von Y"
- **Position:** **NOCH ZU KLÄREN — Anforderer hatte gesagt "ich gebe dir sie", Spec ausstehend**
  - Default-Annahme falls keine andere Spec: rechts unten (wie in der PPTX-Vorlage)
- **Technik:** reportlab `onFirstPage` + `onLaterPages` Callback im `SimpleDocTemplate` — zeichnet auf canvas via `canvas.drawRightString()` o.ä.
- **Aufwand:** Klein (~30 Min)

#### Aufgabe C: Seitenzahlen in PPTX-Export — dynamisch korrekt
- **Problem:** Die Vorlage hat statische Seitenzahlen (Slides 7-9 zeigen "13"-"15"), Lücke 7-12 für dynamische Slides reserviert
- **Was:** Bei Export Seitenzahlen dynamisch auf die finale Slide-Position setzen
- **Logik:** Nach allen Add/Remove-Operationen über alle Slides iterieren, Shape `Foliennummer` finden und mit der korrekten Slide-Position (1-indexed, Cover ausgenommen) befüllen
- **Aufwand:** Mittel (~1h, weil Edge-Cases beachten: Slides ohne `Foliennummer`-Shape, Cover/Endseiten)

#### Aufgabe D: Performance-PPTX-Export (großes Feature)
Komplette neue Funktionalität — alle Spezifikationen aus Brainstorming Juni 2026 (siehe 12.2).
- **Aufwand:** Groß (~6-8h)

### 12.2 Spezifikation Performance-PPTX-Export (vollständig geklärt)

Alle Punkte sind durch Brainstorming geklärt — kann ohne weitere Klärung implementiert werden.

#### Architektur
- **B2-Prinzip:** Jeder Tab füllt nur eigene Folien
- **Position:** Performance-Folien NACH Anlagevorschlag — Slides 10-12 in der Vorlage (nach Entfernung Slide 10 alt = Währungen)
- **TOC** (Slide 2): "3. Wertentwicklung" neu, "3. Honorar" wird zu "4. Honorar" etc.
- **Button:** In `streamlit_app.py` neben "PDF erstellen" — analog zum Portfolioanalyse-Tab
- **Dateiname:** `<Strategie>_Performance_<Datum>.pptx`

#### Folien
Aus EINER Master-Vorlagen-Folie (in `Anlagevorschlag_Master_Dynamische_Folien.pptx` als Slide 8 angelegt) werden bis zu 3 Folien generiert:

| Folie | Überschrift | Zeitraum | Benchmark |
|---|---|---|---|
| F1 | `<Strategie>\| Wertentwicklung (ohne Benchmark)` | Gesamte verfügbare Historie | — |
| F2 | `<Strategie>\| Wertentwicklung (mit Benchmark)` | Gesamte verfügbare Historie | nur wenn gemappt |
| F3 | `<Strategie>\| Wertentwicklung (Berater-Auswahl)` | Berater-Custom-Zeitraum aus UI | wie F2 (mit BM wenn gemappt) |

**Skip-Regeln:**
- F2: übersprungen wenn keine Benchmark im Mapping
- F3: übersprungen wenn UI-Zeitraum = volle Historie (±5 Tage Toleranz)

**Bei Vergleich** (2 Portfolios im UI): V1 = je 3 Folien sequentiell (analog Portfolioanalyse-Vergleich), 6 Folien total.

#### Folien-Inhalt pro Folie
- **Überschrift** oben links: `<Strategie>\| Wertentwicklung (...)`
- **Kennzahlen-Tabelle** links oben: 4 Zeilen × 2 Spalten (Referenz / Benchmark)
  - Performance p.a.
  - Volatilität
  - Sharpe Ratio
  - Max Drawdown
- **Linien-Chart** rechts oben: Wertentwicklung (Index, Start=100), immer normalisiert (egal ob Anlagevolumen im UI gesetzt)
- **Balken-Chart** links unten: Performance p.a. nach Kalenderjahren (nach Kosten)
- **Disclaimer** rechts unten: *"Die angegebenen Werte beziehen sich auf die historische Wertentwicklung. Der Wert sowie die Erträge einer Kapitalanlage können sowohl steigen als auch fallen. Eine positive Wertentwicklung in der Vergangenheit stellt keine Garantie für zukünftige Entwicklungen dar. Die Wertentwicklung wird in Euro (€) gemessen. Die ausgewiesene Performance wird auf täglicher Basis berechnet. Der jährliche Honorarsatz wird dabei in eine äquivalente tägliche Belastung umgerechnet und unter Berücksichtigung des Zinseszinseffekts taggenau von der Performance abgezogen; eine halbjährliche Berücksichtigung erfolgt nicht."*
- **Footer:** Logo links, "Quelle: Eigene Berechnung, Stand <heutiges Datum>" rechts neben Seitenzahl

#### Compliance-Regeln (siehe auch Abschnitt 10.8)
- **Nur Nach Kosten** im Export (UI-Schalter "Vor Kosten" ignoriert)
- **Strategiename gereinigt** (via `clean_strategy_name`)
- **Heutiges Datum** im Footer (Erstellungsdatum)
- **Benchmark immer wenn gemappt** — UI-Checkbox ignoriert

#### Shape-Namen in der neuen Vorlagen-Folie
Bereits angelegt in `Anlagevorschlag_Master_Dynamische_Folien.pptx` Slide 8:

| Name | Typ | Zweck |
|---|---|---|
| `Titel` | Placeholder | Folien-Headline |
| `Tabelle` | Tabelle (4×2) | Kennzahlen (Referenz/Benchmark) |
| `Diagramm links` | Chart | Balken Performance p.a. |
| `Diagramm rechts` | Chart | Linien Wertentwicklung |
| `Header Diagramm links` | Textbox | "PERFORMANCE P.A. (NACH KOSTEN)" |
| `Header Diagramm rechts` | Textbox | "WERTENTWICKLUNG" |
| `Legende Diagramm links` | Textbox | Balken-Legende (Referenz/Benchmark) |
| `Fußnote` | Placeholder | Disclaimer-Text |
| `Quelle` | Textbox | "Quelle: Eigene Berechnung, Stand DD.MM.YYYY" |
| `Foliennummer` | Placeholder | Seitenzahl |

### 12.3 Implementierungs-Reihenfolge (Vorschlag)

1. **Aufgabe A** (Strategieentwurf-Überschrift) — trivial, schneller Win
2. **Aufgabe B** (PDF-Seitenzahlen) — wartet auf Position-Spec vom Anforderer
3. **Aufgabe C** (PPTX-Seitenzahlen dynamisch)
4. **Aufgabe D** (Performance-PPTX-Export) — größtes Feature, in Teilschritten:
   - 4.1 Vorlage Performance-Folie in `Vorlage_FFPB.pptx` integrieren (Slides 10-12)
   - 4.2 `generate_performance_pptx()` in `pptx_export.py` neu anlegen
   - 4.3 Streamlit-Button in `streamlit_app.py` einbauen
   - 4.4 End-to-End-Test mit echten Daten

### 12.4 Sonstige Pflege-Punkte (langfristig)

- Ggf. Sharpe + rf-Linie auch in Portfolioanalyse-Tab (aktuell nur Tab 1)
- Compliance-Feedback weiter beobachten → Disclaimer ggf. anpassen
- Bei Bedarf: Portfolio-Builder-Reaktivierung (siehe Abschnitt 1, deaktiviert seit Juni 2026)

---

## 13. Changelog

### Juni 2026 – Brainstorming PowerPoint-Export-Erweiterung (Spezifikation komplett, Implementierung steht aus)
- **Email-Anforderung mit 3 Compliance-Punkten:** Seitenzahlen in Druckversionen, Mindest-Historie 5 Jahre, Strategieentwurf-Hinweis auf PPTX
- **Bestehender PPTX-Export** (`pptx_export.py`) erstmals in Doku dokumentiert (Abschnitt 10 "PowerPoint-Export-System")
- **Performance-PPTX-Export** als neues großes Feature spezifiziert:
  - Architektur **B2:** jeder Tab füllt nur seine eigenen Folien
  - Position: Performance nach Anlagevorschlag in der Vorlage (Slides 10-12)
  - Inhalts-VZ-Eintrag "3. Wertentwicklung" wird neu in TOC eingefügt
  - 3 Folien-Varianten F1 (ohne BM), F2 (mit BM), F3 (Berater-Auswahl)
  - F2 wird übersprungen wenn keine BM gemappt; F3 wenn Custom-Zeitraum = volle Historie
  - Vergleichsportfolio: V1 = je 3 Folien sequentiell (analog Portfolioanalyse-Vergleich)
  - Nur "Nach Kosten" im Export, UI-Schalter ignoriert
  - Heutiges Datum im Footer (nicht Auswertungsdatum)
  - Linien-Chart immer normalisiert (Start=100), Anlagevolumen ignoriert
  - Kennzahlen: Performance p.a., Volatilität, Sharpe, Max Drawdown (4 Zeilen)
  - Charts: Linien + Balken; KEIN Drawdown, KEINE rollierende Tabelle
- **Master-Vorlage** mit Performance-Folie wurde vom Anforderer geliefert (`Anlagevorschlag_Master_Dynamische_Folien.pptx` Slide 8, Shape-Namen extrahiert und dokumentiert)
- **Disclaimer-Text für Performance-Folien** finalisiert (siehe Abschnitt 12.2)
- **"Strategieentwurf im Rahmen einer Vermögensverwaltung"** ersetzt die Überschrift "Anlagevorschlag" auf PPTX-Folie 7 (nur Überschrift, kein zusätzlicher Footer-Text, nur Slide 7 nicht 8/9)
- Detailfragen zu Folien-Layout, Strategienamen-Bereinigung, Compliance-Anforderungen alle geklärt — siehe Abschnitt 10 und 12

### Juni 2026 – Performance-Tab auf Corporate Colors umgestellt
- **Strategie A:** Konstanten in `shared.py` direkt umdefiniert (single source of truth)
- `FFPB_DARK`: `#1B3A5C` → `#003460` (Fuggerblau)
- `FFPB_GOLD`: `#B8973A` → `#C3A069` (Fuggergold)
- `FFPB_LIGHT`: `#A8CBE8` → `#7FABC8` (Hellblau)
- `FFPB_BLUE2`: `#2C5F8A` → `#4A7FAA` (Mittelblau)
- Neue Konstanten: `FFPB_SAND = "#D4BD8A"` und `FFPB_PALETTE` (15-Farben-Sequenz analog zu Portfolioanalyse `RING_COLORS`)
- `streamlit_app.py`: Plotly-Balken-Chart (BG + 4 Balkenfarben + Achsen-Linien) auf Konstanten; PDF-Linien/Drawdown/Bar-Charts auf neue Konstanten + neue Spines/Grid-Werte (`#1A4880`/`#0A4576`)
- **Plotly-Linien-Charts** (Hauptchart Performance, Drawdown Euro/%): nutzen jetzt `fig.update_layout(colorway=FFPB_PALETTE)` — siehe Transferwissen #10
- **PDF-Linien-Chart** matplotlib: `colors=FFPB_PALETTE[1:]` (Skip Index 0 weil = Hintergrund-Farbe Fuggerblau)
- Portfolioanalyse-PDF-Header/Tabellenkopfzeilen profitieren automatisch (nutzen `FFPB_DARK` aus shared.py)
- Doku: Abschnitt 4 (Corporate Design) komplett neu — Hauptfarben-Tabelle + Palette + Spines/Grid + historischer Kontext
- Transferwissen #10 (Plotly `colorway`) und #11 (Import-Pärchen-Deployment) ergänzt

### Juni 2026 – Disclaimer-Wording auf Vermögensverwaltung
- **Compliance-Abstimmung:** "im Beratungsgespräch" → "der Vermögensverwaltungsstrategien im Kundengespräch"
- 4 Stellen geändert: `streamlit_app.py` Performance UI + PDF, `portfolioanalyse.py` UI + PDF
- Doku: Abschnitt 7 (Performance), 8 (Portfolioanalyse), 9 (Disclaimers-Tabelle) auf neues Wording

### Juni 2026 – Tab "Portfolio zusammenstellen" deaktiviert
- **Compliance-Entscheidung:** Berater dürfen den freien Portfolio-Builder nicht nutzen
- `streamlit_app.py`: Import von `render_portfolio_builder` entfernt, Tab-Tuple von 3 auf 2 Tabs reduziert, Tab-3-Block komplett raus
- Docstring angepasst mit Hinweis warum
- `modules/portfolio_builder.py` bleibt im Repo (nicht gelöscht, nicht verschoben) — kann bei späterer Compliance-Klärung wieder aktiviert werden indem Import + Tab wieder hinzugefügt werden
- `modules/portfolioanalyse.py` unverändert (importierte nie aus dem Builder)
- Doku: Abschnitt "Tab 3" komplett entfernt, Nummerierung von 14 auf 13 Abschnitte reduziert, Abhängigkeits-Diagramm und Disclaimers-Tabelle aktualisiert

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

**Hochladen:** Diese MD + 3 aktive Code-Dateien (`streamlit_app.py`, `modules/shared.py`, `modules/portfolioanalyse.py`).
`modules/portfolio_builder.py` ist deaktiviert und muss nicht mitgegeben werden — nur falls es um eine Reaktivierung geht.
**Sagen:** "Lies die PROJEKT_DOKUMENTATION.md zuerst komplett. Dann [Aufgabe]."
**Bei Problemen:** Screenshot + erwartetes Verhalten

**Wichtig bei CSV-Änderungen:** Nach Deploy IMMER Cache leeren (Transferwissen #7).

*Stand: Juni 2026*
