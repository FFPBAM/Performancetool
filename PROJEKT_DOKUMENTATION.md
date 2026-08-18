# FFPB Streamlit Tool – Projektdokumentation & Transferwissen
## Stand: 11.08.2026 (Phase 4: Code-Review — Benchmark-Bugfix, Deploy-Konfiguration repariert, ~2.200 Zeilen toter Code entfernt)

> **Neu am 12.08.2026:** Transferwissen **#47**–**#51**. Der letzte kam aus
> Philips Sichtprüfung an der Pro-Broschüre: „Es gibt Daten" ist nicht „der
> Zeitraum ist abgedeckt" — der Säulen-Chart zeigte ein 122-Tage-Rumpfjahr
> als Jahresbalken, auf 7 der 19 Strategien. Prüfstein
> `tests/test_kalenderjahre.py`.

> **Neu am 11.08.2026:** Transferwissen **#46** (ein Platzhalterwert pflanzt
> sich fort — bis in den Fließtext) sowie ein vierter Punkt in **#20**
> (Obergrenzen statt `==`-Pins). Backlog **A**, **C** und **1** sind damit
> erledigt — der Backlog §15 enthält nur noch Nachrangiges.

> **Neu am 07.08.2026:** Transferwissen **#41** (Null-Spalten sind keine Daten —
> der Benchmark-Bug), `.streamlit`-Ordner repariert, `lxml` in den requirements
> ergänzt, doppelte CSV-Loader aufgelöst, erster Regressionstest unter `tests/`.
> Die Abschnitte 2, 3, 13 und 15 wurden entsprechend korrigiert — insbesondere
> stand dort bisher, `erstelle_broschueren.py` und `modules/dataload.py` lägen im
> Repo; das war nie der Fall.

> Vorgänger-Stand: Juni 2026 (Phase 2: Performance-PPTX-Export). Alle
> Transferwissen-Einträge #1–#17 aus Phase 2 bleiben gültig und stehen
> weiter unten; NEU sind #18–#28 sowie die Abschnitte zu Themen-Broschüren,
> Vier-Modul-PPTX-Architektur, Konsistenz-Doktrin, lokalem Batch, dem
> Navigations-Umbau (st.tabs → segmented_control), dem gelösten
> Gateway-Download (#25, clientseitiger Blob-Download) sowie der
> datenbasierten Chart-Nachbearbeitung (#26, `chart_dynamik.py`), dem
> dynamischen Tabellen-Layout (#27) und dem Workflow zur optischen
> Fehlersuche (#28).

---

## 0. Was ist seit Juni 2026 passiert? (Executive Summary)

| Datum | Änderung |
|---|---|
| Ende Juni/02.07. | **PPTX-Codebase in 4 Module aufgeteilt** (`pptx_helpers` / `pptx_charts` / `pptx_slides` / `pptx_export`); Donut-Rückbau auf native PP-Charts (matplotlib-PNG-Ansatz verworfen, `png_charts.py` raus); **Kapazitäts-Fix** Anlagevorschlag-Tabelle (>34 Zeilen wurden vorher STILL abgeschnitten) |
| 02.07. | **Wertentwicklungs-Folie (F8)** aus altem VBA-Tool per ZIP-Slide-Copy in die Standard-Vorlage integriert → Vorlage jetzt **26 Slides**; Berechnungs-Logik nach `modules/analytics.py` (Single Source of Truth) |
| 03.07. | **YTD-Fix** rollierende Tabelle (asof 31.12. statt 01.01.); **Konsistenz-Doktrin** Tool ↔ PP festgelegt + Info-Caption; **Duration/Rendite aus den Titeln** berechnet (Duration-Ordner gelöscht); **Arrow-String-Falle** gefixt; `replace_data` **Bug 4** (Achsen-numFmt) entdeckt + gefixt; F9-Anpassungen (YTD-Balken, Achsen-Untergrenze, statische Quelle) |
| 04.–06.07. | **Lokaler Batch** `erstelle_broschueren.py` (streamlit-frei, bewiesen; aktuell pausiert wg. IT-Paketinstallation); **Themen-Broschüren** (Familie „Thema" via Mapping-Spalte „Powerpoint Familie", `Vorlage_Thema.pptx` 21 Folien, 24 MB → 3,95 MB); PDF-Export im Portfolioanalyse-Bereich entfernt |
| 06.07. | **Streamlit-Cloud-Versionsfalle**: `>=`-requirements zog Streamlit 1.59.0 + pandas 3.0; Downgrade-Versuch hing unter Python 3.14 → zurück auf `>=` (Pinnen offen, siehe Backlog) |
| 07.07. | **Navigations-Umbau**: `st.tabs` → `st.segmented_control` (Tab-Rücksprung-Bug strukturell gelöst); Keep-Alive für Widget-States; zentrale Datenbereitstellung vor der Navigation. Per AppTest unter 1.59.0 verifiziert, im Deploy bestätigt |
| 20.07. | **Ring-Optik final**: Cluster-Engine verworfen, (7)-Positionierung + schwarze Leader bleiben; `ring_labels_stub_fix` (Leader-Richtung); Punkte am Label-Ende (Assetklassen+Branchen der Thema-Familie); Familien-/Ringtyp-Erkennung. **Datenlogik-Bugs**: Themen-Einzeltitel-Ring wurde nie befüllt (EDELMETALLE fehlte) → GROUP_ORDER-Feed ergänzt; Legendenbox zu klein → `ensure_ring_legend_fits`. Transferwissen #29–#34 |

---

## ⚠️ TRANSFERWISSEN: Streamlit- und Office-Fallen (gilt für JEDES Streamlit/PPTX-Projekt)

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

Diese Logik wird in diesem Projekt schon länger bei `to_decimal_interval()` für Performance-Werte verwendet — wird analog auf rf angewendet.

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

**ZWEITER FALL — derselbe Fehler, gegenteilige Abhilfe (NEU 17.08.2026).**

Ein `ImportError` nach einem Push heißt **nicht** zwangsläufig, dass die
Datei im Repo falsch ist. Er kann auch bedeuten, dass die Cloud
`streamlit_app.py` neu ausgeführt, das importierte Modul aber aus dem
`sys.modules` des alten Prozesses genommen hat — dort existiert der neue Name
noch nicht.

| | Fall A (Juni 2026) | Fall B (17.08.2026) |
|---|---|---|
| Symbol im Repo vorhanden? | **nein** | **ja** |
| Reboot hilft? | **nein** | **ja** |
| Abhilfe | Datei richtig pushen | „Manage app" → „Reboot app" |

Am 17.08.2026 wurde `datum_waehler_de` gemeinsam mit seinem Import in **einem**
Commit gepusht. Trotzdem stürzte die App beim Start ab. Nachgemessen auf
`origin/verbesserungen`: Die Funktion stand auf Modulebene, **alle 23** aus
`modules.shared` importierten Namen waren vorhanden, keine Schattendatei,
lokal 22 von 22 Suiten grün. Ein Reboot hat es behoben.

**Die Prüfreihenfolge lautet deshalb ab jetzt:**

1. **Steht das Symbol wirklich auf dem Server?**
   `git show origin/<branch>:<datei> | grep "def <name>"` — zehn Sekunden, und
   sie trennen Fall A von Fall B.
2. **Fall B (Symbol ist da): Reboot app.** Der oben stehende Satz „Mehrfaches
   ‚Reboot app' ändert nichts" gilt **nur für Fall A** und hat die Suche am
   17.08. zunächst in die falsche Richtung geschickt.
3. **Erst danach in die Logs** (`Manage app` → Logs) — sie nennen den genauen
   Namen und die Datei.

**Nebenbei ein Diagnose-Werkzeug, das gut funktioniert hat:** Ab Python 3.13
kürzt der Traceback mehrzeilige Anweisungen zu `...<N lines>...`. **N
identifiziert die Revision.** Am 17.08. war so ohne jeden Zugriff auf den
Server belegbar, welcher Commit tatsächlich lief: Der Import-Block umfasste im
neuen Stand 18 Zeilen (`...<16 lines>...`), im Vorgängerstand 15
(`...<13 lines>...`) — gemeldet war 16. Genau das hat auch aufgedeckt, dass die
Cloud den Branch `verbesserungen` bedient und nicht `main`.

---

### 12. python-pptx `chart.replace_data()` ist VERSEUCHT — Bug-QUARTETT bei Charts mit embedded Excel

> **Update Juli 2026:** Zu den drei bekannten Bugs kam ein VIERTER dazu
> (Achsen-numFmt-Reset). Der Workaround lebt seit der Modul-Aufteilung in
> `modules/pptx_charts.py` → `replace_chart_data_safe()` und deckt alle
> vier ab. Ring-/Donut-Charts werden dagegen über `replace_chart_data`
> (XML-in-place) befüllt — dieser Pfad ist bugfrei.

**Situation:** Du willst Chart-Daten in einer PPTX programmatisch ändern (Balken-Werte, Linien-Werte, Kategorien). Die Standard-Methode in python-pptx ist `chart.replace_data(CategoryChartData)`.

**Falle (vier zusammenhängende Bugs):** Wenn der Chart ein **embedded Excel-Workbook** hat (das ist bei aus PowerPoint exportierten Vorlagen-Charts der Standard), passiert beim `replace_data()`:

1. **Embedded Excel wird NICHT aktualisiert.** Die XML-Daten werden geändert, das eingebettete `Microsoft_Excel_Worksheet1.xlsx` behält aber die alten Vorlagen-Werte. PowerPoint erkennt die Diskrepanz → "**Datei muss repariert werden**"-Dialog → die Folie wird beschädigt oder verschwindet.

2. **`style*.xml` wird mit Binärmüll überschrieben.** Konkret: die Chart-Style-Datei (z.B. `ppt/charts/style7.xml`) wird VOR `replace_data()` ein gültiges `<cs:chartStyle ...>` XML — und NACH `replace_data()` ein **ZIP-Header** (`PK\x03\x04...`). python-pptx schreibt aus Versehen ZIP-Inhalt in den falschen Pfad. Auch das löst den Reparieren-Dialog aus.

3. **Format-Codes der Daten-Labels werden auf `"General"` zurückgesetzt.** Das Daten-Label das vorher `0.05` als `5,00%` angezeigt hat, zeigt jetzt `0.05` als Text — die Prozent-Formatierung ist weg. Visueller Schaden, aber nicht datei-zerstörend.

4. **Format-Codes der ACHSEN werden ebenfalls zurückgesetzt** (NEU Juli 2026). Betrifft `valAx`, `catAx` UND `dateAx`. Fix: `<c:numFmt>` nach dem replace wieder einfügen — Position ist kritisch: **direkt nach `<c:axPos>`**, sonst ignoriert PowerPoint das Element.

**Diagnose:** Datei nach `replace_data()` öffnen mit:
```python
import zipfile
with zipfile.ZipFile("output.pptx") as z:
    for name in ["ppt/charts/style7.xml", "ppt/charts/style8.xml"]:
        c = z.read(name)
        if c[:2] == b"PK":
            print(f"⚠️ KORRUPT: {name} hat ZIP-Header statt XML")
```

**Lösung — Backup-Restore Pattern:**

```python
def _replace_chart_data_safe(chart_shape, categories, series_data, data_label_format=None):
    """
    Workaround für 4 python-pptx-Bugs bei chart.replace_data() mit embedded Excel.
    """
    from pptx.chart.data import CategoryChartData
    
    chart = chart_shape.chart
    chart_part = chart.part
    
    # ─── 1. Style/Color-Parts SICHERN ───
    backup_parts = {}  # partname -> (part_obj, blob_bytes)
    for rel_id, rel in chart_part.rels.items():
        try:
            reltype = rel.reltype
        except Exception:
            continue
        if 'chartStyle' in reltype or 'chartColorStyle' in reltype:
            try:
                target = rel.target_part
                backup_parts[str(target.partname)] = (target, bytes(target.blob))
            except Exception:
                pass
    
    # ─── 2. replace_data ausführen ───
    cd = CategoryChartData()
    cd.categories = categories
    for name, vals in series_data:
        cd.add_series(name, vals)
    chart.replace_data(cd)
    
    # ─── 3. Style/Color-Parts WIEDERHERSTELLEN (Bug 2 Fix) ───
    for partname, (part_obj, blob) in backup_parts.items():
        try:
            part_obj._blob = blob
        except Exception:
            pass
    
    # ─── 4. <c:externalData> entfernen (Bug 1 Fix) ───
    # PowerPoint ignoriert dann das embedded Excel und nutzt nur die XML-Daten
    ns = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
    chart_xml = chart._chartSpace
    ext_data = chart_xml.find(".//c:externalData", ns)
    if ext_data is not None:
        ext_data.getparent().remove(ext_data)
    
    # ─── 5. Format-Code Daten-Labels wiederherstellen (Bug 3 Fix) ───
    if data_label_format:
        _restore_data_label_format(chart_shape, data_label_format)

    # ─── 6. Format-Codes der ACHSEN wiederherstellen (Bug 4 Fix) ───
    # valAx/catAx/dateAx: <c:numFmt> DIREKT NACH <c:axPos> einfügen,
    # sonst wird es von PowerPoint ignoriert. Siehe pptx_charts.py.


def _restore_data_label_format(chart_shape, format_code: str):
    """Setzt den Format-Code (z.B. '0.00%') in <c:dLbls><c:numFmt> jeder Series."""
    from lxml import etree
    ns_uri = "http://schemas.openxmlformats.org/drawingml/2006/chart"
    ns = {"c": ns_uri}
    chart_xml = chart_shape.chart._chartSpace
    
    for ser in chart_xml.findall(".//c:ser", ns):
        dlbls = ser.find("c:dLbls", ns)
        if dlbls is None:
            continue
        num_fmt = dlbls.find("c:numFmt", ns)
        if num_fmt is None:
            num_fmt = etree.SubElement(dlbls, f"{{{ns_uri}}}numFmt")
            dlbls.insert(0, num_fmt)
        num_fmt.set("formatCode", format_code)
        num_fmt.set("sourceLinked", "0")
```

**Validierung:** Vor/Nach dem Fix:

```python
# Vorher (KAPUTT):
style7.xml: 5569 bytes, beginnt mit b'PK\x03\x04...'  ← ZIP-Müll!

# Nachher (RESTORED):
style7.xml: 9674 bytes, beginnt mit b'<cs:chartStyle xmlns:cs=...'  ← Korrektes XML
```

**Verwendet in diesem Projekt:** `modules/pptx_charts.py` → `replace_chart_data_safe()`. ALLE Kategorien-Charts (Säulen + Linien, F8/F9 und Themen-Blöcke) gehen durch diese Funktion. Ringe/Donuts: `replace_chart_data` (XML-in-place).

**Generelle Lesson:** Wenn eine populäre Bibliothek einen Bug hat den du nicht umgehen kannst → **Backup-Restore-Pattern** ist oft die schnellste Lösung. Statt den Bug zu fixen (kann Wochen dauern bis upstream merged ist), sicherst du den State vorher und stellst ihn hinterher wieder her. Funktioniert für `_blob`-Manipulation in python-pptx, könnte ähnlich für openpyxl oder python-docx funktionieren.

---

### 13. PPTX-Dateigröße optimieren: PNG → JPEG mit Alpha-Check

**Situation:** Eine PPTX-Vorlage ist 22 MB groß und der Streamlit-Cloud-Download bricht mit `progress.html` ab. Ursache: 19 PNGs in der Vorlage à 1-2 MB.

**Falle:** Naiv "alle PNGs zu JPEG konvertieren" zerstört Bilder die echte Transparenz haben (z.B. Logo-Freisteller, Icons). JPEG hat keinen Alpha-Channel — alles wird auf weißem Hintergrund "geflattet".

**Lösung:** PNG-Bilder unterscheiden in:
- **Fake-Alpha (min=255):** RGBA aber jedes Pixel ist voll opak → JPEG ohne Verlust möglich (~85% kleiner)
- **Fast-opak (min≥192):** Sehr leichte Transparenz, optisch kaum wahrnehmbar → JPEG mit weißem Hintergrund OK
- **Echtes Alpha (min<192, oft 0):** Echte Transparenz → MUSS PNG bleiben

```python
from PIL import Image
import io

def png_alpha_status(png_bytes):
    """Returns: 'fake' / 'nearly_opak' / 'real' / 'no_alpha'"""
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode != "RGBA":
        return "no_alpha"
    alpha = img.split()[-1]
    min_alpha = alpha.getextrema()[0]
    if min_alpha == 255:
        return "fake"
    if min_alpha >= 192:
        return "nearly_opak"
    return "real"

def png_to_jpeg(png_bytes, quality=85):
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode == "RGBA":
        white_bg = Image.new("RGB", img.size, (255, 255, 255))
        white_bg.paste(img, mask=img.split()[-1])
        img = white_bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()
```

**Beim PPTX modifizieren musst du dran denken:**

1. Bild-Datei umbenennen: `ppt/media/imageN.png` → `ppt/media/imageN.jpeg`
2. **`[Content_Types].xml`** updaten — Override-Pfad anpassen oder bei Default-Extensions sicherstellen dass `jpeg` registriert ist
3. **Alle `.rels`-Dateien** durchsuchen die das Bild referenzieren → Pfad aktualisieren

```python
# ContentTypes: PNG-Override → JPEG-Pfad
content = z.read("[Content_Types].xml").decode("utf-8")
for img in TO_JPEG:
    jpeg_img = img.replace(".png", ".jpeg")
    content = content.replace(f"/ppt/media/{img}", f"/ppt/media/{jpeg_img}")

# Alle .rels mit Bild-Referenz
for name in z.namelist():
    if name.endswith(".rels"):
        rels = z.read(name).decode("utf-8")
        for img in TO_JPEG:
            jpeg_img = img.replace(".png", ".jpeg")
            rels = rels.replace(f"media/{img}", f"media/{jpeg_img}")
```

**Validiert in diesem Projekt (2×):**
- Standard-Vorlage: 22.7 MB → 4.14 MB (−82%, 19 Bilder, alle fake-Alpha)
- `Vorlage_Thema.pptx` (Juli 2026): 24 MB → **3,95 MB** (24 unkomprimierte RGBA-PNGs; opake → JPG Q82, `.jpeg`-Endung nutzt den vorhandenen Content-Type-Default, 1 echt-transparentes Bild blieb PNG; Charts/Tabellen unangetastet)

**Generelle Lesson:** Vor jeder PPTX-Optimierung — Inhalts-Inventur. Welche Bilder sind drin, wie groß, welche Alpha-Properties? Dann gezielt komprimieren. Erspart blindes Trial-and-Error.

---

### 14. Slide-Copy zwischen PPTX-Dateien (python-pptx kann das NICHT eingebaut)

**Situation:** Du hast eine Master-PPTX mit einer ausgefeilten Folie (Charts, Tabellen, Layout) und möchtest **diese eine Folie** in eine andere PPTX einbauen — z.B. eine Corporate-Hauptvorlage um eine zusätzliche Folie ergänzen.

**Falle:** python-pptx hat KEINE eingebaute "copy slide from another presentation"-Funktion. Naive Versuche (Slide-Objekt direkt zwischen Presentation-Instanzen kopieren) brechen die internen ID-Konsistenzen — Charts verlinken auf falsche Embeddings, Layout-References sind kaputt, ContentTypes inkonsistent.

**Lösung — Recipe für sauberen Slide-Copy via ZIP-Manipulation:**

**Phase 1: Inventur der Abhängigkeiten der Quell-Folie**

Lies `master/slides/_rels/slideN.xml.rels` und folge ALLEN Targets:
- `../charts/chartX.xml` (Charts)
- `../slideLayouts/slideLayoutY.xml` (Layout)
- `../media/imageZ.png/jpeg` (Bilder)

Dann pro Chart `master/charts/_rels/chartX.xml.rels`:
- `../embeddings/Microsoft_Excel_WorksheetA.xlsx` (eingebettetes Excel)
- `colorsX.xml` (Chart-Farbschema)
- `styleX.xml` (Chart-Style)

Pro Layout `master/slideLayouts/_rels/slideLayoutY.xml.rels`:
- `../slideMasters/slideMasterN.xml` (meist nur slideMaster1)

**Phase 2: Ziel-Indizes finden (in der Ziel-PPTX)**

```python
import zipfile, re
with zipfile.ZipFile(target_pptx) as z:
    def next_free_idx(pattern, suffix=".xml"):
        idxs = [int(m.group(1)) for n in z.namelist()
                for m in [re.fullmatch(pattern + r"(\d+)" + re.escape(suffix), n)] if m]
        return max(idxs, default=0) + 1
    
    next_slide = next_free_idx("ppt/slides/slide")        # z.B. 26
    next_chart = next_free_idx("ppt/charts/chart")        # z.B. 7
    next_layout = next_free_idx("ppt/slideLayouts/slideLayout")  # z.B. 29
```

**Phase 3: Mapping erstellen — Master-Pfad → Ziel-Pfad**

```python
RENAME = {
    "ppt/slides/slide8.xml": f"ppt/slides/slide{next_slide}.xml",
    "ppt/slides/_rels/slide8.xml.rels": f"ppt/slides/_rels/slide{next_slide}.xml.rels",
    "ppt/charts/chart4.xml": f"ppt/charts/chart{next_chart}.xml",      # bar
    "ppt/charts/chart3.xml": f"ppt/charts/chart{next_chart+1}.xml",    # line
    "ppt/charts/_rels/chart4.xml.rels": f"ppt/charts/_rels/chart{next_chart}.xml.rels",
    # ... style, colors, embeddings, layout
}
```

**Phase 4: Files kopieren + Pfade in Rels aktualisieren**

```python
# Dateien rüber kopieren
for old_path, new_path in RENAME.items():
    files_target[new_path] = master_zip.read(old_path)

# Innere Pfade in .rels aktualisieren
def update_rels(content_str, mappings):
    for old, new in mappings.items():
        content_str = content_str.replace(f'Target="{old}"', f'Target="{new}"')
    return content_str

# Beispiel: slide26.xml.rels referenziert chart7, chart8, slideLayout29
slide_rels = files_target[new_slide_rels_path].decode("utf-8")
slide_rels = update_rels(slide_rels, {
    "../charts/chart3.xml": "../charts/chart8.xml",
    "../charts/chart4.xml": "../charts/chart7.xml",
    "../slideLayouts/slideLayout17.xml": "../slideLayouts/slideLayout29.xml",
})
files_target[new_slide_rels_path] = slide_rels.encode("utf-8")
```

**Phase 5: `presentation.xml` + `presentation.xml.rels` erweitern**

```python
from lxml import etree

NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"

# Lese presentation.xml und .rels
pres = etree.fromstring(files_target["ppt/presentation.xml"])
pres_rels = etree.fromstring(files_target["ppt/_rels/presentation.xml.rels"])

# Nächste freie rId und sldId bestimmen
existing_rids = [r.get("Id") for r in pres_rels.findall(f"{{{NS_PKG}}}Relationship")]
new_rid = f"rId{max(int(r[3:]) for r in existing_rids if r.startswith('rId')) + 1}"

sld_ids = pres.findall(f".//{{{NS_P}}}sldIdLst/{{{NS_P}}}sldId")
new_sld_id = max(int(s.get("id")) for s in sld_ids) + 1

# Relationship hinzufügen
new_rel = etree.SubElement(pres_rels, f"{{{NS_PKG}}}Relationship")
new_rel.set("Id", new_rid)
new_rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide")
new_rel.set("Target", f"slides/slide{next_slide}.xml")

# Slide in sldIdLst an gewünschter Position einfügen (z.B. Index 9 = Slide 10)
new_sld = etree.Element(f"{{{NS_P}}}sldId")
new_sld.set("id", str(new_sld_id))
new_sld.set(f"{{{NS_R}}}id", new_rid)
sld_id_lst = pres.find(f"{{{NS_P}}}sldIdLst")
sld_id_lst.insert(9, new_sld)
```

**Phase 6: `slideMaster1.xml` + `slideMaster1.xml.rels` erweitern (für neues Layout)**

```python
# slideMaster1.xml.rels: neue Layout-Relationship
sm_rels = etree.fromstring(files_target["ppt/slideMasters/_rels/slideMaster1.xml.rels"])
sm_rids = [r.get("Id") for r in sm_rels.findall(f"{{{NS_PKG}}}Relationship")]
new_layout_rid = f"rId{max(int(r[3:]) for r in sm_rids if r.startswith('rId')) + 1}"

new_layout_rel = etree.SubElement(sm_rels, f"{{{NS_PKG}}}Relationship")
new_layout_rel.set("Id", new_layout_rid)
new_layout_rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout")
new_layout_rel.set("Target", f"../slideLayouts/slideLayout{next_layout}.xml")

# slideMaster1.xml: sldLayoutIdLst erweitern
sm = etree.fromstring(files_target["ppt/slideMasters/slideMaster1.xml"])
layout_lst = sm.find(f"{{{NS_P}}}sldLayoutIdLst")
existing_layout_ids = [int(e.get("id")) for e in layout_lst.findall(f"{{{NS_P}}}sldLayoutId")]
new_layout_entry = etree.SubElement(layout_lst, f"{{{NS_P}}}sldLayoutId")
new_layout_entry.set("id", str(max(existing_layout_ids) + 1))
new_layout_entry.set(f"{{{NS_R}}}id", new_layout_rid)
```

**Phase 7: `[Content_Types].xml` erweitern (8 neue Overrides für die importierten Files)**

```python
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
ct = etree.fromstring(files_target["[Content_Types].xml"])

NEW_OVERRIDES = [
    (f"/ppt/slides/slide{next_slide}.xml", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"),
    (f"/ppt/charts/chart{next_chart}.xml", "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"),
    (f"/ppt/charts/chart{next_chart+1}.xml", "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"),
    (f"/ppt/charts/style{next_chart}.xml", "application/vnd.ms-office.chartstyle+xml"),
    (f"/ppt/charts/style{next_chart+1}.xml", "application/vnd.ms-office.chartstyle+xml"),
    (f"/ppt/charts/colors{next_chart}.xml", "application/vnd.ms-office.chartcolorstyle+xml"),
    (f"/ppt/charts/colors{next_chart+1}.xml", "application/vnd.ms-office.chartcolorstyle+xml"),
    (f"/ppt/slideLayouts/slideLayout{next_layout}.xml", "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"),
]
for partname, ct_type in NEW_OVERRIDES:
    ov = etree.SubElement(ct, f"{{{NS_CT}}}Override")
    ov.set("PartName", partname)
    ov.set("ContentType", ct_type)
```

**Phase 8: ZIP zusammenstellen**

```python
with zipfile.ZipFile(target_pptx_path, "w", zipfile.ZIP_DEFLATED) as zout:
    for path, content in files_target.items():
        zout.writestr(path, content)
```

**Validiert in diesem Projekt (2×):** v7-Vorlage komplett aus zwei Quellen gebaut (Juni 2026, 25 Slides, 0 XML-Fehler); Wertentwicklungs-Folie aus dem alten VBA-Tool in die Standard-Vorlage integriert (Juli 2026 → 26 Slides).

**Generelle Lesson:** Office-Dokumente sind ZIP-Archive mit strenger Hierarchie. Was ein einzelner Slide-Copy in PowerPoint mit zwei Mausklicks tut, sind im Code ~8 Phasen synchroner Updates. Das ist OK, weil reproduzierbar und versionierbar.

---

### 15. Streamlit Cross-View Daten-Sharing — robuste Fallback-Strategie

> **Update 07.07.2026:** Seit dem Navigations-Umbau (segmented_control statt
> st.tabs) läuft nur noch die AKTIVE Ansicht. Die Datenbereitstellung
> (`perf_timeseries`/`perf_d2c`/`perf_d2b`) wurde deshalb ZENTRAL vor die
> Navigation gezogen (läuft bei jedem Run) — der hier beschriebene
> Fallback-Loader in `portfolioanalyse.py` bleibt als zweites Netz bestehen.

**Situation:** Daten aus Ansicht A werden in Ansicht B benötigt (z.B. Performance-Zeitreihe wird für den PPTX-Export verwendet).

**Falle:** Naive Lösung `st.session_state["data"] = data` in Ansicht A, dann `data = st.session_state["data"]` in Ansicht B — funktioniert NICHT zuverlässig:
- Wenn Ansicht A einen `st.stop()` aufruft (z.B. fehlende CSV-Datei), wird `session_state` nie gesetzt
- User könnte direkt Ansicht B nutzen bevor Ansicht A "warm" ist
- Bei Reload geht session_state verloren

**Symptom in diesem Projekt:** User klickte Portfolioanalyse → PowerPoint, ohne den Performance-Bereich vorher geöffnet zu haben → Slide 8 zeigte Vorlagen-Defaults (0,0%) statt echte Daten.

**Lösung — Fallback-Pattern:**

```python
# Ansicht B: erst session_state versuchen, dann selbst laden
perf_timeseries = st.session_state.get("perf_timeseries", {})

# Wenn leer → direkt laden statt aufgeben
fallback_loaded = False
if not perf_timeseries:
    try:
        date_tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
        files = load_all_csvs(DATA_FOLDER, date_tag, EXCLUDE_SUBSTRINGS)
        if files and mapping is not None:
            perf_timeseries = build_portfolio_timeseries(files, mapping)
            fallback_loaded = True
    except Exception as ex:
        st.warning(f"Performance-Daten konnten nicht geladen werden: {ex}")

# Diagnose-Warnung wenn das Portfolio trotz Fallback fehlt
missing = []
for pf_name in selected_portfolios:
    csv_n = perf_d2c.get(pf_name) or display_to_csv.get(pf_name)
    if not csv_n or csv_n not in perf_timeseries:
        missing.append((pf_name, csv_n))

if missing:
    st.warning(
        f"⚠️ Performance-Daten fehlen für: {missing}. "
        f"Verfügbar: {list(perf_timeseries.keys())[:5]}. "
        f"Fallback aktiv: {fallback_loaded}."
    )
```

**Wichtige Voraussetzung:** Die Lade-Funktionen müssen aus einem GEMEINSAMEN Modul kommen, nicht aus dem Top-Level eines View-Files. In diesem Projekt: `build_portfolio_timeseries`, `load_all_csvs` etc. leben in `modules/shared.py`.

**Wichtig (NEU Juli 2026):** Diagnose-Meldungen, die direkt vor `st.rerun()` per `st.warning` ausgegeben werden, werden vom Rerun WEGGEWISCHT. Lösung: Meldungen in `session_state` sammeln (`pf_pptx_build_errors`) und NACH dem Rerun anzeigen.

**Generelle Lesson:** Cross-View Coupling ist ein Streamlit-Antipattern. session_state ist eine Optimierung (Cache), keine Datenquelle. Plan also: **session_state ist nie garantiert da, immer Fallback einbauen, immer Diagnose bei Datenlücken zeigen — und Diagnosen rerun-fest machen.**

---

### 16. PPTX-Validierung Multi-Layer-Toolchain

**Situation:** Du hast eine PPTX generiert/modifiziert und musst herausfinden warum PowerPoint sie nicht öffnen kann (oder reparieren möchte).

**Falle:** PowerPoint zeigt nur "Datei muss repariert werden" — keine Diagnose welcher Part kaputt ist. LibreOffice öffnet die Datei vielleicht fehlerfrei (LO ist toleranter), also `soffice --convert-to pdf` ist kein zuverlässiger Validitäts-Test.

> **Update Juli 2026 — LibreOffice ≠ PowerPoint gilt in BEIDE Richtungen:**
> LO zeigt Fehler, die PP nicht hat (Achsen-rot, Dezimalpunkt-, Datums-
> Formate) UND verschluckt Fehler, die PP hat (z.B. `baseTimeUnit`!).
> LO-Renders sind nur Näherung; echte Verifikation = PowerPoint-Screenshot
> vom Nutzer. Zusatz-Falle `dateAx`: `baseTimeUnit` muss zur Daten-
> Granularität passen — Tagesdaten mit `baseTimeUnit="months"` → PP bündelt
> monatsweise, Linie zerhackt, in LO unsichtbar. Fix:
> `set_date_axis_base_unit(chart, "days")` (pptx_charts). Ebenso: Achsen-
> Untergrenzen DATENBASIERT setzen, nie fix/Auto (PP wählt bei Index >>100%
> gern 0%), und Live-Datumsfelder in "Stand"-Boxen statisch setzen (zeigen
> sonst das Öffnungsdatum).

**Lösung — Multi-Layer-Validierung** (in der Reihenfolge ausführen, jeder Layer baut auf vorherigem auf):

```python
import zipfile
from lxml import etree
from pptx import Presentation

def validate_pptx(path):
    """Mehrstufige PPTX-Validierung."""
    errors = []
    
    # Layer 1: ZIP-Integrität
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad is not None:
            errors.append(f"L1 ZIP: {bad} korrupt")
            return errors
    
    # Layer 2: Alle XML-Files parsen
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not (name.endswith(".xml") or name.endswith(".rels")):
                continue
            content = z.read(name)
            # Sanity: kein ZIP-Header in XML-Files (Bug 2 aus #12)
            if content[:2] == b"PK":
                errors.append(f"L2 KORRUPT: {name} hat ZIP-Header (python-pptx style-bug?)")
                continue
            try:
                etree.fromstring(content)
            except Exception as e:
                errors.append(f"L2 PARSE: {name}: {str(e)[:60]}")
    
    # Layer 3: ContentTypes ↔ ZIP-Inhalt
    NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
    with zipfile.ZipFile(path) as z:
        ct = etree.fromstring(z.read("[Content_Types].xml"))
        defaults = {d.get("Extension") for d in ct.findall(f"{{{NS_CT}}}Default")}
        overrides = {ov.get("PartName") for ov in ct.findall(f"{{{NS_CT}}}Override")}
        actual_files = {f"/{n}" for n in z.namelist() if not n.endswith("/")}
        
        # Overrides ohne entsprechende ZIP-Datei?
        missing = overrides - actual_files
        if missing:
            errors.append(f"L3 CT: Overrides ohne Datei: {sorted(missing)[:3]}")
        
        # Files im ZIP ohne ContentType?
        for f in actual_files:
            if f.startswith("/_rels"): continue
            ext = f.rsplit(".", 1)[-1] if "." in f else ""
            if ext not in defaults and f not in overrides:
                errors.append(f"L3 CT: {f} hat keinen ContentType")
    
    # Layer 4: Relationships valide (Targets existieren)
    NS_RP = "http://schemas.openxmlformats.org/package/2006/relationships"
    import posixpath
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".rels"): continue
            tree = etree.fromstring(z.read(name))
            base = name.rsplit("_rels/", 1)[0]
            for rel in tree.findall(f"{{{NS_RP}}}Relationship"):
                if rel.get("TargetMode") == "External": continue
                target = rel.get("Target")
                target_path = posixpath.normpath(
                    target[1:] if target.startswith("/") else base + target
                )
                if target_path not in z.namelist():
                    errors.append(f"L4 REL: {name} → {target} (fehlt)")
    
    # Layer 5: python-pptx kann es öffnen (semantisch)
    try:
        prs = Presentation(path)
        _ = len(prs.slides)
    except Exception as e:
        errors.append(f"L5 SEMANTIK: python-pptx failure: {str(e)[:80]}")
    
    return errors
```

**Tabelle: Validation-Layer**

| Layer | Tool | Findet |
|---|---|---|
| L1 | `zipfile.testzip()` | Korrupte ZIP-Bytes |
| L2 | `lxml.etree.fromstring()` | XML-Syntax-Fehler, ZIP-Header in XML-Files (#12 Bug 2!) |
| L3 | ContentTypes-Vergleich | Inkonsistente Overrides/Defaults |
| L4 | Relationship-Target-Check | Tote Links zwischen Parts |
| L5 | `pptx.Presentation()` | Semantische OOXML-Fehler |
| (L6) | PowerPoint öffnen | Microsoft-spezifische Strenge (kann nicht in CI getestet werden) |

**Wichtig:** Manche Bugs werden NUR von einem bestimmten Layer gefunden. Der python-pptx style-corruption Bug (#12) wird z.B. von L2 erkannt (ZIP-Header in XML), aber L5 (python-pptx) findet ihn NICHT — er ist tolerant gegen seine eigene Korruption.

**Generelle Lesson:** Office-Dokument-Validierung braucht mehrere Layer. Auch dann gibt es PowerPoint-spezifische Strenge die nur in der echten Office-App auffällt. Best practice: nach jeder Code-Änderung an einem PPTX-Builder einmal manuell PowerPoint öffnen.

---

### 17. Office-Dokumente sind ZIP-Archive — Manipulation-Recipe

**Situation:** Du willst etwas an einem `.docx`, `.pptx` oder `.xlsx` modifizieren wozu die offizielle Library (python-docx, python-pptx, openpyxl) keine API hat — z.B. Footer-Texte in allen Slides ersetzen, Chart-Styles patchen, Custom-XML-Parts einfügen.

**Falle:** Du suchst stundenlang nach einer API-Methode die nicht existiert, statt direkt das ZIP zu manipulieren.

**Lösung — Allgemeines Manipulation-Recipe:**

```python
import zipfile, shutil

def modify_office_file(source_path, target_path, modifications):
    """
    Generisches Pattern: Office-Datei modifizieren.
    
    modifications: dict {file_in_zip: bytes | callable(bytes) -> bytes}
    """
    with zipfile.ZipFile(source_path, "r") as zin:
        with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                content = zin.read(info.filename)
                
                # Modification anwenden falls definiert
                if info.filename in modifications:
                    mod = modifications[info.filename]
                    if callable(mod):
                        content = mod(content)
                    else:
                        content = mod
                
                zout.writestr(info, content)

# Beispiel: "Stand 12.02.2026" durch aktuelles Datum ersetzen in allen Slides
import datetime
new_date = datetime.date.today().strftime("%d.%m.%Y")
def replace_date(content):
    return content.decode("utf-8").replace("12.02.2026", new_date).encode("utf-8")

mods = {
    "ppt/slides/slide24.xml": replace_date,
    "ppt/slides/slide25.xml": replace_date,
}
modify_office_file("Vorlage.pptx", "Vorlage_neu.pptx", mods)
```

**Faustregeln für sichere ZIP-Manipulation:**

| Regel | Warum |
|---|---|
| **Lese-Modus zuerst** | Niemals direkt überschreiben — könnte korrupt schreiben |
| **`ZIP_DEFLATED`** | Office-Dateien sind immer deflated, sonst wird's deutlich größer |
| **UTF-8 ohne BOM** | Office-XML ist immer UTF-8, BOM verwirrt Parser |
| **`<?xml ... standalone="yes"?>`** | Office erwartet diese Deklaration, sonst manchmal Reparieren-Dialog |
| **Relative Pfade in .rels** | `../charts/chart1.xml` NICHT `/ppt/charts/chart1.xml` (mit Slash am Anfang) |
| **PartNames in ContentTypes** | MIT führendem Slash (`/ppt/charts/chart1.xml`) — anders als in .rels |
| **Endung-Casing** | `.xml` und `.rels` immer kleingeschrieben |

**Generelle Lesson:** Vor jedem ZIP-Manipulation-Projekt einmal eine fertige Office-Datei entpacken und die Struktur durchschauen. Office-Dokumente sind erstaunlich gut lesbar als ZIP-Inhalt — manche Bugs erkennt man sofort wenn man die Files in der Hand hat.

---

### 18. st.tabs "vergisst" den aktiven Tab bei jedem Rerun — Navigation über keyed Widgets bauen (NEU 07.07.2026)

**Situation:** Eine App mit `st.tabs(["A", "B"])`. In Tab B löst eine Selectbox-Auswahl (oder jedes andere Widget) einen Rerun aus.

**Falle:** `st.tabs` rendert nach dem Rerun wieder den ERSTEN Tab — die Ansicht "springt zurück". Das ist ein bekanntes, vom Streamlit-Team bestätigtes Verhalten (GitHub #6257, #11160, #4996, #12554), KEIN Fehler im eigenen Code. **Auch die neuen Parameter helfen nicht:** `key="active_tab"` + `on_change="rerun"` trackt den Zustand, stellt den Tab aber nicht wieder her. Und `default=` ist bei gesetztem `key` per Doku wirkungslos nach der ersten Instanziierung (bei Key-basierter Widget-Identität wird `default` nur beim ersten Run ausgewertet) — kann also strukturell nichts "wiederherstellen".

**Lösung:** Navigation NICHT über `st.tabs` bauen, sondern über ein keyed Auswahl-Widget (`st.segmented_control` oder `st.radio`) + `if/else` um die View-Bodies. Der Zustand lebt dann nativ im `session_state` und kann bei Reruns nicht "vergessen" werden.

```python
_VIEW_A = "📈 Performance"
_VIEW_B = "📊 Portfolioanalyse"
if "nav_view" not in st.session_state:
    st.session_state["nav_view"] = _VIEW_A
ansicht = st.segmented_control("Ansicht", [_VIEW_A, _VIEW_B],
                               key="nav_view", required=True,
                               label_visibility="collapsed")
if ansicht == _VIEW_A:
    ...  # ehemals `with tab_a:` — gleiche Einrückung, minimaler Diff
else:
    ...
```

**Wichtige Details:**
- **`required=True`** (single mode, ab Streamlit ~1.59): verhindert das Abwählen — Klick aufs aktive Segment ist ein No-op, es gibt nie den Zustand "keine Ansicht gewählt" (sonst gibt das Widget `None` zurück!).
- **Nebenwirkung 1 — nur die aktive Ansicht läuft:** Bei `st.tabs` liefen ALLE Tab-Bodies bei jedem Run; nach dem Umbau nur noch der aktive. Alles, was "immer laufen muss" (z.B. session_state-Datenbereitstellung für den PPTX-Export), VOR die Navigation ziehen.
- **Nebenwirkung 2 — Widget-States der inaktiven Ansicht werden gelöscht:** siehe #19 (Keep-Alive).
- **Positiv-Nebenwirkung:** `st.stop()` in Ansicht A stoppt nicht mehr Ansicht B mit.

**Verifiziert in diesem Projekt:** Per Streamlit `AppTest` unter exakt 1.59.0 (Selectbox-Rerun → Navigation bleibt stehen), anschließend im Cloud-Deploy bestätigt.

**Generelle Lesson:** `st.tabs` ist ein reines LAYOUT-Element ohne verlässlichen Zustand — für NAVIGATION (Zustand, der Reruns überleben muss) immer ein keyed Input-Widget nehmen.

> 📖 **Ausführlich:** Kausalmodell, Vorher/Nachher-Rezept, Nebenwirkungen und Umbau-Checkliste stehen im **Deep-Dive Abschnitt 8**.

---

### 19. Keep-Alive-Pattern: Widget-Zustände überleben bedingtes Rendern nicht (NEU 07.07.2026)

**Situation:** Widgets werden nur bedingt gerendert (z.B. nur die aktive Ansicht einer Radio/segmented_control-Navigation, siehe #18).

**Falle:** Streamlit LÖSCHT den session_state-Eintrag eines Widgets, sobald das Widget in einem Run nicht gerendert wird. Wechselt der User Ansicht A → B → zurück zu A, stehen alle Häkchen/Selectboxen/Eingaben von A wieder auf Default.

**Lösung — Keep-Alive am Skriptanfang:** Alle Keys einmal re-assignen. Damit gelten sie als "per API gesetzt" und überleben das Nicht-Rendern.

```python
# JEDER Button/Download-Button mit key= MUSS in diese Liste.
_KEEPALIVE_SPERRE = {"pf_pptx_btn", "pf_pptx_dl", "p_zeit_reset"}
for _k in list(st.session_state.keys()):
    if _k in _KEEPALIVE_SPERRE:
        continue
    try:
        st.session_state[_k] = st.session_state[_k]
    except Exception:
        pass
```

⚠️ **KORREKTUR 11.08.2026 — das try/except rettet dich NICHT.** Hier stand
bis dahin, es fange künftige, nicht gelistete Trigger-Keys „defensiv" ab.
Das ist falsch, und es kostet sofort einen Absturz:

1. `st.session_state["mein_knopf"] = ...` **geht durch** — die Zuweisung
   wirft nichts, sie markiert den Key nur als „per API gesetzt".
2. Erst das spätere `st.button(key="mein_knopf")` prüft das in
   `check_session_state_rules` und wirft
   **`StreamlitValueAssignmentNotAllowedError`** — an einer ganz anderen
   Stelle, weit außerhalb dieses `try`.

Symptom: Die Seite bricht mit „Uncaught app execution" ab, und der
Traceback zeigt auf die Button-Zeile — nicht auf das Keep-Alive, das die
Ursache ist. Beim Einbau des Zurücksetzen-Knopfes (11.08.2026) genau so
passiert.

**Regel:** Neuer Button mit `key=` → Key in `_KEEPALIVE_SPERRE` eintragen.
Das `try/except` bleibt für andere nicht setzbare Keys, ersetzt die Liste
aber nicht.

**Alternative (offiziell, ab ~1.59):** Widgets haben einen `persist_state`-Parameter (`"page"` / `"session"`, braucht `key`). Für EINZELNE Widgets sauberer; das Keep-Alive-Loop-Pattern deckt dagegen ALLE Widgets zentral mit einer Stelle ab — in diesem Projekt bewusst so gewählt (minimaler Diff, keine Änderung an Dutzenden Widget-Aufrufen).

**Verifiziert in diesem Projekt:** Per AppTest unter 1.59.0 (Checkbox + Selectbox verstellen → Ansicht wechseln + dort interagieren → zurück → Werte erhalten).

> 📖 **Ausführlich:** Warum die Sperrliste + try/except nötig sind und wie das Keep-Alive in die feste Skript-Reihenfolge passt, steht im **Deep-Dive Abschnitt 8** (8.5–8.6).

---

### 20. Streamlit-Cloud-Versionsfalle: `>=` in requirements.txt + automatische Paket-Updates (NEU 06.07.2026)

**Situation:** `requirements.txt` nutzt `>=`-Mindestversionen. Streamlit Community Cloud zieht bei jedem Reboot die NEUESTEN Pakete.

**Falle (real passiert, teuer):** Am 6.7. erschien Streamlit 1.59.0 (+ pandas 3.0, numpy 2.5). Der Reboot zog sie automatisch — die App verhielt sich plötzlich anders ("lief gestern noch"), obwohl KEIN eigener Code geändert wurde. Der Verdacht fällt dann reflexhaft auf den letzten eigenen Commit.

**Zweite Falle beim Gegensteuern:** Naives Pinnen auf die ALTEN Versionen (streamlit==1.58, pandas==2.2.3, numpy==1.26.4) ließ die App im Reboot HÄNGEN — die alten Versionen bauen unter **Python 3.14** (das die Cloud nutzt) nicht sauber. Zurück auf `>=` brachte die App wieder hoch.

**Learnings:**
1. Bei "lief gestern noch, heute kaputt" auf Streamlit Cloud IMMER ZUERST ins **Deploy-Log** schauen (Manage app → schwarze Konsole) — dort stehen die installierten Paketversionen. Hätte hier Stunden gespart.
2. Versionen pinnen ist richtig, aber NUR auf Versionen, die mit der Cloud-Python-Version (aktuell 3.14) kompatibel sind. Erst prüfen, welche streamlit/pandas/numpy-Kombination unter 3.14 baut, DANN pinnen.
4. **Umgesetzt am 11.08.2026 — und zwar mit OBERGRENZEN, nicht mit `==`.** Ein exakter Pin löst Falle 1 und läuft direkt in Falle 2: er friert auch die Python-Kompatibilität ein, und beim nächsten Python-Sprung der Cloud baut das Paket nicht mehr. `paket>=geprüfte.version,<nächste_hauptversion` sperrt den Bruch aus (Hauptversionen sind es, die brechen) und lässt Fehlerkorrekturen sowie neue Python-Builds weiterhin durch. Untergrenze ist immer eine Version, die man selbst hat laufen sehen — nicht eine, die gut klingt.
3. Python-3.14/pandas-3-Nebenwirkung im Code: Arrow-String-dtypes → siehe #21.

---

### 21. Arrow-String-Falle unter Python 3.14 / pandas ≥ 3 (NEU 03.07.2026)

**Situation:** CSV-Spalten werden mit `dtype=str` gelesen und später verrechnet.

**Falle:** Unter Python 3.14 / pandas-Arrow-Backend sind Spalten teils **Arrow-Strings**. Dann macht z.B. `spalte.sum()` eine String-VERKETTUNG statt einer Summe, und Multiplikationen werfen `"Can only string multiply by an integer"` bzw. `"could not convert string to float"`. Betroffen war `get_bond_summary` (total_weight, Fälligkeits-Gewichte, gewichtete Mittel).

**Lösung/Regel:** Rechen-relevante Spalten IMMER erst **deterministisch in float** wandeln (elementweise; deutsches Komma, `%`, `-`, leere Werte abfangen), BEVOR summiert/multipliziert wird. `pd.to_numeric` allein reicht nur, wenn die Strings bereits Punkt-Dezimale sind — der robuste Weg ist die explizite Konvertierung wie in `get_bond_summary._to_float_series` bzw. `.astype(str)` → Komma→Punkt → `to_numeric` im Parser.

---

### 22. Perioden-Grenzen: `asof(Periodenstart)` schneidet den ersten Tag ab (NEU 03.07.2026)

**Situation:** Eine rollierende Renditetabelle rechnet "YTD" als `idx.asof(01.01.) → idx.asof(heute)`.

**Falle:** Bei kalendertäglichen Daten EXISTIERT am 01.01. eine Datenzeile — `asof(01.01.)` nimmt also den Indexstand NACH dem 01.01. Die Rechnung verliert damit den ersten Tag des Jahres (dessen Rendite + 1 Tag Honorar-Drag, hier ~0,003–0,004 %-Punkte) und weicht von jeder Rechnung ab, die ab Vorjahres-Schlussstand rechnet (PP-Folie 8, eigener Balken-Chart).

**Lösung/Regel:** Perioden-Konvention immer als **"ab Schlussstand des Vortags/Vorjahres"** definieren: YTD-Start = `asof(31.12. Vorjahr)`. Danach waren Tool-Tabelle, Balken-Chart und PP **bit-identisch** (numerisch bewiesen). Fachlich ist das auch die marktübliche Lesart von "Wertentwicklung seit 01.01.". Rollierende Punkt-zu-Punkt-Zeiträume (1/3/5/10 Jahre) behalten bewusst ihre Konvention — nur an Jahres-/Periodengrenzen schlägt die Falle zu.

---

### 23. GitHub Web-UI: Große Binärdateien NIE umbenennen, Git-LFS-Zeiger erkennen (NEU Juli 2026)

**Situation:** Eine große `.pptx` liegt im GitHub-Repo und soll umbenannt/ersetzt werden.

**Falle 1 (real passiert):** Der Web-Rename in GitHub **zerstörte den Datei-Inhalt** — übrig blieb eine 2-Byte-Datei; die App meldete beim Laden "Package not found". Große Binärdateien immer FRISCH hochladen, nie über die Web-UI umbenennen.

**Falle 2:** Wenn eine Datei über Git LFS ins Repo kam, liegt am Pfad nur ein ~130-Byte-**LFS-Zeiger** statt der echten Datei. Diagnose im Code (in `portfolioanalyse.py` eingebaut): existiert die Datei? Wie groß? `< 5000 Bytes` → sehr wahrscheinlich LFS-Zeiger oder Rename-Leiche.

```python
if os.path.getsize(pfad) < 5000:
    # ⚠️ vermutlich Git-LFS-Zeiger oder zerstörte Datei statt echter PPTX
```

**Regel:** Vorlagen als normale Binärdateien (nicht über LFS) im Repo halten; nach jedem Vorlagen-Upload einmal Dateigröße im Repo prüfen.

---

### 24. Streamlit AppTest als Beweis-Werkzeug für Rerun-/State-Verhalten (NEU 07.07.2026)

**Situation:** Du willst VOR dem Deploy beweisen, dass sich Widgets/Navigation über Reruns korrekt verhalten (z.B. Tab-Bug-Fix aus #18, Keep-Alive aus #19).

**Lösung:** `streamlit.testing.v1.AppTest` simuliert die App headless — Widgets lassen sich programmatisch bedienen (`at.selectbox(key=...).select(...).run()`), session_state ist inspizier- und setzbar. Damit lassen sich Rerun-Szenarien exakt nachstellen ("Selectbox-Auswahl → bleibt Navigation stehen?") und als assert-Tests festhalten.

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_function(app)   # oder .from_file("streamlit_app.py")
at.run()
at.session_state["nav_view"] = "B"; at.run()
at.selectbox(key="pf_sel_1").select("Strat Y").run()
assert at.session_state["nav_view"] == "B"
```

**Grenze:** AppTest simuliert das Streamlit-PROTOKOLL, nicht den Browser — Frontend-Rendering-Bugs (Material-Icons #1, LO/PP-Unterschiede) sieht es nicht. Für State-/Rerun-Logik ist es aber der schnellste harte Beweis; der echte Deploy bleibt der finale Prüfstein.

> 📖 **Ausführlich:** Die konkreten zwei AppTests für den Navigations-Umbau (Bug-Fall + Keep-Alive) stehen ausformuliert im **Deep-Dive Abschnitt 8** (8.7).

---

### 25. Download hinter einem scannenden Firmen-Gateway: clientseitiger Blob-Download statt Server-Abruf (NEU 07.07.2026)

**Situation:** Der Broschüren-Download aus der Streamlit-App landet hinter einem Download-scannenden Web-Gateway (hier: Atruvia Secure Web Gateway / Skyhigh, Regel „Block If Virus Was Found"). Der klassische `st.download_button` liefert dem Nutzer statt der PPTX eine `progress.htm` (die Scan-Zwischenseite des Gateways).

**Die Kernerkenntnis (teuer erkauft):** **JEDER Download, der die Datei vom Server holt, läuft durch den Scanner** — egal über welchen Streamlit-Pfad. Der Scanner hält die Verbindung, liefert seine `progress.htm` aus, und je nach Download-Mechanik hängt der Tab endlos oder speichert die Zwischenseite. Das ist NICHT durch Wahl eines anderen Server-Pfades lösbar. Drei Sackgassen wurden nacheinander durchgespielt und verworfen:

| Versuch | Was passierte | Warum Sackgasse |
|---|---|---|
| `st.download_button` (Standard) | progress.htm statt PPTX | Fetch vom `/media/`-Endpoint → Gateway scannt → In-Page-Mechanik speichert die Zwischenseite |
| Neuer Tab auf die interne Media-URL `/media/<id>.pptx` (via `media_file_mgr.add`) | Tab „lädt ewig" | Auf Community Cloud trifft `/media/…` NICHT den Media-Handler, sondern **bootet die App neu** im neuen Tab (im Deploy-Log bewiesen: Aufruf von `/media/…` löste „Starting up repository" aus). Zusätzlich: interne API, die ein Update zerlegen kann |
| Neuer Tab auf Static Serving `/app/static/<datei>.pptx` | Tab „lädt ewig" | Pfad + Content-Type sind korrekt (in 1.59.0 verifiziert: `guess_content_type` → `…presentation`, `enableStaticServing=true` nötig), ABER es ist immer noch ein **Server-Abruf** → der Gateway-Scan hängt genauso |

**Die Lösung — clientseitiger Blob-Download (KEIN Netzwerk-Request):** Die Datei-Bytes werden als **Base64 direkt in die Seite eingebettet**. Ein Button baut die Datei **im Browser lokal** aus diesen Bytes zusammen (`atob` → `Uint8Array` → `Blob` → `URL.createObjectURL` → `<a download>.click()`) und speichert sie. Dabei geht **kein HTTP-Request** raus → der Gateway hat **nichts zu scannen** → der Download startet sofort, im selben Fenster, ganz normal. Die Bytes reisen nur als Teil der ohnehin erlaubten App-Antwort mit; der eigentliche Speichervorgang ist rein lokal und fällt damit nicht unter die Download-Scan-Regel.

```python
# In st.components.v1.html einbetten (NICHT st.markdown — das entfernt <script>!):
import base64, json
b64 = base64.b64encode(daten).decode("ascii")
html = f'''
<button id="dl">📥 Herunterladen</button>
<script>
document.getElementById("dl").addEventListener("click", function() {{
  const bin = atob("{b64}"); const bytes = new Uint8Array(bin.length);
  for (let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
  const blob = new Blob([bytes], {{type: {json.dumps(mimetype)}}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = {json.dumps(dateiname)};
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(url), 2000);
}});
</script>'''
import streamlit.components.v1 as components
components.html(html, height=90)
```

**Zwei kritische Details, ohne die es nicht läuft:**
1. **`st.components.v1.html`, NICHT `st.markdown`.** `st.markdown(unsafe_allow_html=True)` entfernt `<script>`-Tags → das JS läuft nie. Die HTML-Komponente führt Skripte in ihrem iframe aus.
2. **Der Komponenten-iframe muss Downloads erlauben.** Streamlit setzt `sandbox="… allow-downloads"` (im Frontend-Code `IFrameUtil.ts` verifiziert) → der Blob-Download aus dem iframe ist erlaubt. Der Klick liefert die nötige User-Geste.

**Grenzen / Trade-offs:**
- **Größe:** ~4 MB PPTX → ~5,5 MB Base64 in der Seite, das bei jedem Rerun der Komponente mitgeht (Streamlit `maxMessageSize` default 200 MB → unkritisch für gelegentliche Downloads, aber kein Muster für sehr große oder häufige Dateien).
- **Content-DLP:** Die Bytes reisen im App-Verkehr mit. Ein Gateway, das zusätzlich **tiefe Inhaltsprüfung (DLP) auf den App-/Websocket-Verkehr** macht, könnte theoretisch anschlagen — das ist aber eine ANDERE Regel als die Download-Scan-Regel, die hier blockierte. In der Praxis (Atruvia „Block If Virus Was Found") lief es sauber durch.
- Der klassische `st.download_button` bleibt als Fallback unter einem Expander stehen (Server-Weg), falls die Komponente in einer Umgebung mal nicht greift.

**Implementiert in diesem Projekt:** `modules/download_helfer.py` → `download_bereich(daten, dateiname)`; aufgerufen aus `portfolioanalyse.py` im Export-Bereich. Frühere Versuche (`medien_download_url`, Static Serving, `enableStaticServing` in config.toml) sind toter Code bzw. ungenutzt — die config-Zeile darf raus.

**Generelle Lesson:** Kämpft ein Download gegen ein scannendes Gateway, hilft kein anderer Server-Pfad. Wenn die Datei-Bytes im Browser bereits vorliegen (oder sich clientseitig erzeugen lassen), ist der **Blob-Download aus in-Page-Daten** der Ausweg — er erzeugt gar keinen Netzwerk-Request, den ein Gateway scannen könnte. Gilt für jedes gateway-geplagte Web-Tool, nicht nur Streamlit.

---

### 26. Native PowerPoint-Charts datenbasiert nachbearbeiten — Achsen, Ring-Dicke, Außen-Labels (NEU 09.07.2026)

**Modul:** `modules/chart_dynamik.py` · **Aufruf:** `nachbearbeiten(prs)` in `pptx_export.py`, unmittelbar VOR `prs.save()`.

Die Ringe und Linien der Broschüren sind **native PowerPoint-Charts** (python-pptx + lxml auf `chart._chartSpace`, Namespace `c:`), **kein matplotlib, kein Bild**. Alle Layout-Eingriffe passieren im Chart-XML. Eine einzige Funktion läuft am Ende über alle Charts und zieht sie datenbasiert nach:

- **Doughnut-Ringe:** `holeSize=79` (dünner Original-Look), Prozent-Labels außerhalb des Rings mit Führungsstrich, überlappungsfrei, Ring in den freien Raum zwischen Überschrift und Legende eingepasst.
- **Linie mit Datums-Achse:** X- **und** Y-Achse auf die echte Datenspanne; `majorTimeUnit=years` bei Spannen > 5 Jahre.
- **Balken (catAx):** unberührt.

Selbstkalibrierend pro Chart → automatisch korrekt für Pro / Pro Dividende / Offensiv und jede Segmentzahl (2–12). Rührt die Download-Logik nicht an. Datenlogik bleibt unverändert.

**Native Äquivalente zu matplotlib-Begriffen** (eine fremde KI schlug uns `ax.annotate` / `radius=0.8` vor — das läuft hier ins Leere):

| matplotlib | nativ (Chart-XML) |
|---|---|
| `radius` kleiner | `<c:plotArea><c:layout><c:manualLayout>` x/y/w/h skalieren |
| Label-Position | `<c:dLbl><c:idx><c:layout><c:manualLayout><c:x/><c:y/>` (Offsets als Bruchteile von Rahmen**breite** bzw. -**höhe**) |
| Führungslinie | `<c:dLbls><c:showLeaderLines val="1"/>` — PP zeichnet nur bei seitlichem Versatz |
| `holeSize` | `<c:holeSize val="79"/>` (Lochanteil %, groß = dünn) |
| `startangle` | `<c:firstSliceAng val="…"/>` |

**Die zehn Fallen (teuer erkauft — nicht wieder aufmachen):**

1. **LibreOffice rendert `holeSize` FALSCH** (ignoriert es, zeigt immer ~50 %). Kontrolltest: `holeSize` 30 vs. 90 → identisches LO-Bild. **Ring-Dicke ist nur in echtem PowerPoint prüfbar.** Verifikation daher immer numerisch aus dem XML.
2. **PP-Default-Label-Position:** OHNE `manualLayout` sitzt das Label in der **Loch-Mitte**. MIT `manualLayout` rechnet PP den Offset von der **Ring-Band-Mitte** des Segments (`band_center = R_out*(1+holeSize)/2`, Richtung = Segment-Mittelwinkel). Offsets IMMER von dort berechnen — von der Chart-Mitte aus schießen die Labels doppelt weit raus (Striche bis in die Legende).
3. **`manualLayout` x = Bruchteil der BREITE, y = der HÖHE.** Der Rahmen ist breiter als hoch (5,24 × 4,55") → x muss gestaucht werden. (Im geometrischen Ansatz fällt das automatisch heraus, weil Offsets als `(Ziel − Default)/Rahmenmaß` gerechnet werden.)
4. **Die Vorlage kann WENIGER `<c:dLbl>` haben als das Portfolio Segmente.** Fehlende dLbl → Segment landet auf Default (im Loch). Beispiel: Offensiv-Regionen 7 Segmente, Vorlage nur 5 dLbl → 2 Zahlen im Loch. **Fix:** für jedes fehlende Segment ein dLbl aus einem vorhandenen KLONEN (`copy.deepcopy`, `idx` setzen, einfügen).
5. **Führungsstrich nur bei Seitenversatz.** PP zeichnet den Strich erst, wenn das Label SEITLICH (senkrecht zur Radiallinie seines Segments) ≥ ~0,16–0,20" versetzt ist. Rein radiale Labels bleiben strichlos. `showLeaderLines=1` allein reicht **nicht**. **Fix:** Leader-Garantie-Pass mit Mindest-Seitenabstand 0,20".
6. **Abstand winkelabhängig.** Zahlen sind waagerechter Text: seitliche Labels ragen mit der BREITE zum Ring, oben/unten nur mit der HÖHE. Fester radialer Abstand → seitliche Zahl klebt am Ring. **Fix:** `R_target = R_out + gap + (0,33·|sinθ| + 0,10·|cosθ|)`.
7. **Ringe haben unterschiedlich große Plot-Flächen** (Außenradius ~1,09 / 1,41 / 1,68" im selben Rahmen). Ein fester Radius-Bruchteil passt nie für alle. **Fix:** Geometrie pro Chart aus dem `plotArea`-Layout lesen (Zentrum, `R_out`).
8. **Zu große Ringe → kein Platz für Außen-Labels.** **Fix:** Plot-Fläche verkleinern (natives Äquivalent zu `radius=0.8`).
9. **Vertikale Einpassung / Legende.** Die Legende sitzt via `manualLayout` unten im Rahmen und schiebt den Ring hoch → obere Labels an der Überschrift. **Fix:** Legenden-Oberkante aus deren `manualLayout y` lesen, Ring verkleinern + im freien Bereich zentrieren.
10. **De-overlap kann Labels zum Ring drücken.** **Fix:** abschließende Mindest-Ring-Abstand-Passe (Innenkante ≥ `R_out + 0,12"`).

**Der Y-Achsen-Bug (Linien-Chart):** Die Vorlage hatte `valAx` fest auf 0,8–1,4. Offensiv steigt auf Index 2,84 → die Kurve schoss ~2011 über die Decke, die rechten ¾ des Charts blieben leer. Symptom war „links zu viel frei" — Ursache war die **Y**-Achse, nicht die X-Achse. Beide skalieren jetzt datenbasiert.

**Verifikations-Checkliste (numerisch, NICHT per LibreOffice):** `dLbl`-Anzahl == Segmentzahl · jedes Label-Radius > `R_out` · Innenkanten-Freiheit ≥ 0,10" (winkelabhängig) · Seitenabstand ≥ 0,16–0,20" · keine zwei Labels überlappen (|Δx|<0,55 und |Δy|<0,19) · oberstes Label über Kopf-Rand, unterstes über Legenden-Oberkante · kein Label am Rahmenrand.

**Parameter:** `hole_size=79` · `label_gap_in=0.14` · `min_gap_deg=24` · `min_tang=0.20` · `label_pad=0.52` · `min_clear=0.12`

---

### 27. PPTX-Tabellen dynamisch layouten — Zeilenhöhe, Schrift, Summenzeile, Zellrahmen (NEU 09.07.2026)

**Modul:** `modules/pptx_slides.py` · **Betrifft:** Einzeltitel-Folie der Themen-Broschüren (Rolle `einzeltitel_themen`).

**Ausgangslage:** `fill_einzeltitel_themen_slide()` hat die Tabelle nur **befüllt** — im Gegensatz zur Standard-Anlagevorschlag-Folie, die `remove_empty_table_rows` → `fit_shape_to_table` aufruft. Ergebnis: leere Zeilen mit Linien, gedrängte Zeilen, Tabelle bis an die Abschlusslinie, überdimensionierte „Gesamt"-Zeile.

**Warum die alten Helfer NICHT wiederverwendbar waren.** Die Anlagevorschlag-Tabelle hat **11 Spalten** (Daten auf 0/2/4/6/8/10), die Einzeltitel-Tabelle nur **7** (Daten auf 0/2/4/6):

- `remove_empty_table_rows` greift hart auf `COL_ANTEIL=8`, `COL_RATING=10` zu → **IndexError**
- `maybe_narrow_bond_columns` verschmälert Spalten 2/4 → das wären hier **Währung und WKN**
- `MAX_TABLE_BOTTOM_INCH = 6.60` gilt für die Anlagevorschlag-Folie; die Einzeltitel-Folie hat ihre blaue Abschlusslinie schon bei **6,38"**

**Konsequenz:** neue, **generische** Helfer (Daten-Spalten als Parameter), wiederverwendbar für jede Vorlage der PowerPoint-Familie (ESG/CVV/ETF/…). Die alten Funktionen und `MAX_TABLE_BOTTOM_INCH` bleiben bitweise unverändert → **Blast-Radius null.**

| Neue Funktion | Zweck |
|---|---|
| `tabelle_leere_zeilen_entfernen(table, daten_spalten, …)` | leere Datenzeilen raus; Spalten als Parameter |
| `tabelle_abschlusslinie_sichern(table)` | Unterkante der letzten Datenzeile auf die normale dünne Linie vereinheitlichen |
| `tabelle_abstandszeile_einfuegen(table)` | leere, seitlich rahmenlose Zeile vor die Summe |
| `tabelle_dynamisch_skalieren(table_shape, max_bottom_inch, …)` | Zeilenhöhe + Schrift an den Platz anpassen |
| `_zelle_rahmen_entfernen`, `_zelle_rahmen_uebernehmen`, `_zelle_leeren_kompakt`, `_zeile_schrift_setzen` | Bausteine |

**Aufrufreihenfolge (Indizes!):** leere Zeilen entfernen → Abschlusslinie vereinheitlichen → Abstandszeile einfügen → skalieren → Gesamt-Zeile Schrift explizit setzen.

**Die sechs Fallen:**

1. **Fehlendes `sz`-Attribut erbt ~18 pt.** Die Zelle „Gesamt" hatte `<a:rPr b="1"/>` **ohne** `sz`. In einer 0,142"-Zeile (≈10 pt) quoll der Text über und durchkreuzte die Rahmenlinie („Gesamt zu groß, blaue Linie darüber"). → Schriftgröße nach dem Befüllen **explizit** setzen, nie auf die Vorlage verlassen.
2. **`text_frame.clear()` hinterlässt einen 18-pt-Absatz.** Der leere Absatz hat keine Schriftgröße → die Zeile wird aufgebläht, egal welche Höhe im XML steht. → `defRPr` **und** `endParaRPr` klein setzen (Renderer nutzen unterschiedliche der beiden).
3. **Schema-Reihenfolge in `<a:tcPr>`.** `lnL, lnR, lnT, lnB` müssen **VOR** den Füll-Elementen (`noFill`/`solidFill`) stehen. Hängt man sie mit `SubElement` hinten an, ignorieren die Renderer sie und zeichnen die **Standard-Rahmen des Tabellen-Styles** → sichtbarer leerer Kasten. → `tcPr.insert(0, …)`.
4. **Renderer führen angrenzende Zellrahmen zusammen.** Setzt man die Abstandszeile rundum auf `noFill`, verschwinden auch die Linien der **Nachbarzeilen** (die Tabelle wirkt unten offen). → An jeder Zeilengrenze **beidseitig dasselbe** setzen: oben dünne Trennlinie, unten dicke Summenlinie; seitlich (`lnL`/`lnR`) `noFill`, sonst Kasten.
5. **Linien-Stärke hängt an der physischen Zeilenposition.** Die dicke 0,75-pt-Linie sitzt in der Vorlage an der *physisch letzten* Datenzeile. Nach dem Entfernen leerer Zeilen rutscht je nach Strategie mal eine dicke, mal eine dünne ans Ende → inkonsistent. → aktiv vereinheitlichen. Rahmen **kopieren** (`deepcopy` + Tag umbenennen), nicht Attribute nachbauen → Corporate-Design (0,75 pt, `14355C`, solid) bleibt exakt.
6. **Zeilenhöhe ist ein Minimum, kein Fixwert.** Renderer legen Zeilen höher aus als berechnet — gemessen **~0,1" Drift über 37 Zeilen**. → Unterkante konservativ wählen.

**Parameter (`pptx_slides.py`):**

```python
EINZELTITEL_MAX_BOTTOM_INCH = 6.20   # blaue Abschlusslinie liegt bei 6.38"
EINZELTITEL_MIN_ROW_H_INCH  = 0.125
EINZELTITEL_MAX_ROW_H_INCH  = 0.19   # wenige Titel → nicht aufblasen, Rest bleibt leer
EINZELTITEL_MIN_FONT_PT     = 6.0
EINZELTITEL_MAX_FONT_PT     = 7.0
EINZELTITEL_GAP_H_INCH      = 0.10   # Abstandszeile
EINZELTITEL_SUMMARY_H_INCH  = 0.17   # Gesamt-Zeile
_ROW_H_PER_PT_INCH          = 0.0237 # kalibriert: 0.142"-Zeile trägt 6 pt
```

**Ergebnis (gemessen):** Pro 34 Zeilen → 0,134"/6,0 pt · Offensiv & Pro Dividende 27 Zeilen (7 leere entfernt) → 0,169"/7,0 pt. Unterkante überall 6,20". Fußstruktur: dünne Linie 5,92" → 0,10" Abstand → dicke Linie 6,02" → „Gesamt" 6,07–6,14" → 0,21" Luft → blaue Linie 6,35".

**Bewusst nicht gemacht:** Spacer-Spalten weicher (0,06" harte Zwischenräume, rein kosmetisch) · **Fortsetzungsfolie** bei > 34 Zeilen. Achtung falls doch: `generate_portfolioanalyse_pptx` adressiert Folien über `base = block_start + B*k` — ein eingefügter Slide **verschiebt alle nachfolgenden Indizes**. Ferner: `EINZELTITEL_WARNUNGEN` wird befüllt, aber nirgends ausgelesen (könnte an `LAST_BUILD_ERRORS` gehängt werden).

---

### 28. Optische Fehlersuche bei PPTX-Layouts: Screenshots, numerische Verifikation, zweite KI (NEU 09.07.2026)

Die teuerste Zeit ging bei Charts **und** Tabellen dafür drauf, dass niemand zuverlässig sah, wie PowerPoint tatsächlich rendert. Diese Regeln haben sich bewährt.

**1. Screenshots sind das schnellste Diagnosemittel — aber nur aus echtem PowerPoint.**
Ein Bild von Folie 10/11 klärt in Sekunden, was zehn Runden verbaler Beschreibung nicht schaffen. Die LibreOffice-Vorschau ist **nicht** PowerPoint. Bekannte Abweichungen:

- `holeSize` (Ring-Dicke) wird **komplett ignoriert** (immer ~50 %) → #26
- angrenzende **Zellrahmen werden zusammengeführt** (PowerPoint zeichnet ggf. beide) → #27
- **Zeilenhöhen** werden minimal höher ausgelegt (~0,1" Drift über 37 Zeilen)

→ Ring-Dicke und Rahmen-Details **nur** in echtem PowerPoint bewerten.

**2. Immer zusätzlich numerisch verifizieren.**
Ein Screenshot zeigt, *dass* etwas falsch ist; das XML zeigt, *warum*. Beides kombinieren. Nie „sieht gut aus" als Abnahme akzeptieren, wenn man es messen kann (Label-Radius, `sz`-Attribut vorhanden, Rahmen an beiden Zeilengrenzen identisch).

**3. Renderer-unabhängige Messung am Bild.**
Liegt ein Render vor, lässt sich vieles objektiv messen statt „hinschauen":

- **Ring-Geometrie:** farbige Pixel → Mittelpunkt, Innen-/Außenradius über einen **radialen Scan pro Winkel-Bin**. (Perzentile über *alle* Pixel verzerren — erste Messung ergab so fälschlich 53 % statt 77 % Lochanteil.)
- **Tabellenlinien:** Bildzeilen mit Deckung > 45 % der Tabellenbreite = Linie; 2–40 % = Text. Sonst zählt man die **blaue Abschlusslinie als Text**.
- **Textgröße:** Höhe des Textbands relativ zu einer normalen Datenzeile („Gesamt" sollte ≈ 1,0–1,1× sein, nicht 3×).

**4. Eine zweite KI optisch bewerten lassen.**

- **Geschlossene, prüfbare Fragen** stellen — nicht „sieht das gut aus?", sondern *„Ragen Zahlen in die Legende? Gibt es leere Kästen? Ist die Gesamt-Zeile größer als die Datenzeilen?"*
- **Kontext mitgeben**, sonst schlägt sie matplotlib-Lösungen für native PP-Charts vor (genau so passiert). Dafür existiert der Übergabe-Block `docs/RING_CHART_KI_BRIEFING.md`; für Tabellen analog anlegbar.
- **Antworten gegen das XML prüfen**, nicht ungeprüft übernehmen. Die zweite KI sieht das Bild, kennt aber die Vorlage nicht.

**5. Vorher/Nachher rendern und dieselbe Messung anwenden.**
Nur so fällt auf, wenn ein Fix ein neues Problem erzeugt hat (Beispiel: „Rahmen der Abstandszeile weg" → *auch* die Nachbarlinien verschwanden).

**6. Validieren gegen das Original.**
`validate.py` auf **beide** Dateien anwenden und die Meldungszahl vergleichen (Transferwissen #16). Gleiche Zahl = kein neuer Fehler; die verbleibenden Meldungen sind Vorlagen-Altstand.

**7. Vor dem ersten Codeschreiben den Blast-Radius bestimmen.**
Aufrufgraph prüfen: Wer ruft die Funktion sonst noch auf? Geteilte Helfer nie „mal eben" erweitern — lieber **additiv daneben bauen** und den alten Pfad bitweise unverändert lassen (mit Diff belegen).

---

### 29. Ring-Führungslinien & Außen-Labels — der Endstand (NEU 20.07.2026)

**Modul:** `modules/chart_dynamik.py` · **Einstieg:** `nachbearbeiten(prs)` (in `pptx_export.py`, direkt vor `prs.save()`).

**WICHTIGSTE ENTSCHEIDUNG (nicht rückgängig machen):** Es gab zwei konkurrierende Positionierungs-Engines. Die **(7)-basierte ALT-Positionierung** (`ring_labels_aussen_dynamisch`) ist die **gültige, abgenommene Lösung**. Eine spätere **Cluster-Engine** (`ring_labels_cluster` / intern „V2": luftigere Anordnung, graue Leader, Punkte am Segment) wurde gebaut, getestet — und von Philip als **„sieht noch schlimmer aus"** verworfen. `ring_labels_cluster` und `ring_labels_kompakt` stehen nur noch als **UNGENUTZT** markierter Referenzcode in der Datei. **Nicht wiederbeleben.** Wer die Anordnung ändern will, arbeitet an `ring_labels_aussen_dynamisch`.

**Aufbau der Datei (für gezielte Änderungen):** Ganz oben steht ein **WEGWEISER** (Problem → Funktion), ein **CONFIG-Block** (alle Stellschrauben) und eine **FALLSTRICKE**-Liste. So findet man ohne Suchen die richtige Stelle: „Führungslinie anpassen" → `ring_leader_zeichnen` + CONFIG; „Labels stehen falsch" → `ring_labels_aussen_dynamisch`; „Punkt/Farbe" → CONFIG.

**Pipeline in `nachbearbeiten` pro Doughnut (Reihenfolge ist wichtig):**
1. `ring_holesize(79)` — dünner Ring.
2. `ring_segmentfarben` — Assetklassen-Farben namensbasiert (nur Assetklassen-Ringe; Rückgabe leer → Sektoren/Regionen bleiben unangetastet).
3. `kopf_sperre_aus_usershapes` — misst die Unterkante des Überschriftenbalkens.
4. `_enge_labelwinkel` → schaltet bei engen Assetklassen-Ringen stärkere Spreizung zu.
5. **`ring_labels_aussen_dynamisch`** — Label-Positionen (8 Pässe, s. #26).
6. `ring_leaderlines_aus` — PowerPoints Auto-Leader ABSCHALTEN.
7. **`ring_labels_stub_fix`** — Führungslinien-Richtung reparieren (s. #30).
8. **`ring_leader_zeichnen`** — eigene Leader als Connector + optional Punkt (s. #31).
9. `ring_label_schriftfarbe` — Prozentzahlen schwarz.

**Leader-Optik:** Die Führungslinien sind **eigene Connector-Shapes** (`add_connector`), **schwarz** (`LEADER_FARBE = "000000"` — Philip bevorzugt Schwarz gegenüber dem früheren Grau `A6A6A6`). Geknickte Führung: radialer Austritt am Segment → horizontaler Stub zur Zahl. Der Knick liegt auf dem **Radialstrahl** des Segments auf Label-Höhe; die dem Ring **zugewandte** Kante der Zahl-Box ist der Stub-Ansatz.

**FALLSTRICK (teuer, mehrfach):** **LibreOffice ist KEIN Beweis für die Leader-Optik.** LibreOffice ignoriert `showLeaderLines=0` und zeichnet ZUSÄTZLICH eigene Auto-Leader → im Render erscheinen **Doppel-Linien**. Die Leader-Optik ist nur an **echten PowerPoint-Screenshots** prüfbar. Die **Geometrie** (Koordinaten, Längen, Kreuzungen, Knick-Richtung) ist dagegen zuverlässig **aus dem XML** verifizierbar — genau so wurde jede Änderung dieser Session abgenommen (numerisch, nicht per LO-Bild).

**FALLSTRICK Koordinaten:** Ein Punkt `(xi, yi)` in Rahmen-Zoll liegt auf der Folie bei `(shape.left + xi*914400, shape.top + yi*914400)` EMU. Label-Positionen werden als **absolute** `manualLayout` mit `xMode/yMode="edge"` geschrieben: `stored_x = (mx − 0.33)/frame_w`, `stored_y = (my − 0.10)/frame_h` (0,33/0,10 = halbe Text-Box). NICHT als Offset (der Offset-Nullpunkt ist unbekannt, s. #26 Falle 2).

---

### 30. Führungslinien-Richtung reparieren: `ring_labels_stub_fix` (NEU 20.07.2026)

**Symptom (echter PowerPoint-Screenshot):** Bei manchen Ringen fehlt einzelnen Labels die „Richtung" — statt eines sauberen Knicks (radialer Austritt + horizontaler Stub zur Zahl) bekommen sie nur eine **gerade, fast senkrechte Diagonale**. Betroffen sind **obere Segmente** (nahe 12 Uhr), deren Zahl fast senkrecht ÜBER dem Segment sitzt.

**Ursache (am XML nachgewiesen):** In `ring_leader_zeichnen` scheitert für solche Labels die Knick-Bedingung `side·(e_x − k_x) > _LEADER_MIN_STUB` — der berechnete Stub ist **negativ** (Knie läge auf der falschen Seite der Zahl-Innenkante), weil die Zahl-Innenkante fast auf dem Segment-x liegt. Der Code fällt dann korrekt auf eine gerade Linie zurück — die aber richtungslos wirkt.

**Lösung:** Eigene Funktion `ring_labels_stub_fix`, aufgerufen ZWISCHEN Positionierung und Leader-Zeichnen. Sie schiebt betroffene Labels **minimal weiter nach außen** (horizontal vom Segment weg), bis ein sauberer Radial-Knick möglich ist — der Leader-Pfad wird dann x-monoton (kein Haken). Zielposition: `mx_neu = k_x + side·(HW + _LEADER_MIN_STUB + 0.05)`.

**Sicherungen (damit der (7)-Look erhalten bleibt):**
- Wirkt NUR, wenn `|cos(mid)| > 0.30` (seitliche Labels bekommen ohnehin eine korrekte, fast waagerechte Gerade) UND der saubere Stub sonst fehlschlägt.
- Nur nach AUSSEN schieben (`|mx−cx|` darf nicht kleiner werden — sonst zöge man Labels in den Ring).
- Verschiebung gedeckelt: `max_nudge_in = 0.50` (Ø real ~0,24"). Größere Sprünge würden den Look zu stark ändern → dann bleibt die gerade Linie.
- Nicht in ein anderes Label und nicht über Rand/Header schieben.

**Verifikation (numerisch):** 96 richtungslose Leader über alle Broschüren repariert, 0 neue Überlappungen. Verbleibende gerade obere Linien sind legitim (`r < R_out` → Label auf Segment-Höhe → horizontale Linie hat Richtung).

---

### 31. Punkte/Marker am Label-Ende — Ringtyp- + Familien-Regel (NEU 20.07.2026)

**Zielbild:** Kleiner **schwarzer, gefüllter Kreis** am **äußeren Ende** der Führungslinie, direkt VOR der Prozentzahl (nicht am Ring). Markiert den Abschluss des Leaders beim Label. Genau ein Punkt je Leader, klein und einheitlich.

**FALLSTRICK Position:** Zuerst wurde der Punkt am **Segment-Ansatz** `(sx, sy)` gezeichnet — dann wirkt er wie eine Markierung AUF dem Ring (unruhig). Richtig ist das **Label-Ende** = `punkte[-1]` (die dem Ring zugewandte Kante der Zahl-Box). Verifiziert: Abstand zur Zahl 0,00", Abstand zum Ring ~0,29".

**Regel (konfigurierbar im CONFIG-Block):** Punkte erscheinen nur
- auf Ringtypen in `PUNKT_RINGTYPEN = ("ANLAGEKLASSEN", "BRANCHEN")` — Regionen-Ring bewusst OHNE, UND
- nur in der **Thema-Familie** (`PUNKT_NUR_THEMA = True`).

Also: Assetklassen-Ring (Einzeltitel) + Branchen-Ring (Zusammenstellung) der Thema-Broschüren bekommen Punkte; Regionen-Ring und ALLE ESG/CVV/Standard-Ringe nicht. Erweitern = Ringtyp in `PUNKT_RINGTYPEN` ergänzen (z.B. `"REGIONEN"`). Weitere CONFIG: `PUNKT_AN`, `PUNKT_FARBE = "000000"`, `PUNKT_DURCHMESSER = 0.055"`.

**Umsetzung:** `ring_leader_zeichnen` bekam Parameter `punkt_zeichnen` (Entscheidung trifft `nachbearbeiten` anhand `_ring_typ` + `ist_thema`), zeichnet ein gefülltes OVAL ohne Kontur, benannt `RingLeaderDot_<chart>_<idx>` (idempotent: alte Punkte werden vor Neuzeichnen entfernt).

---

### 32. Familien- & Ringtyp-Erkennung (datengetrieben, NEU 20.07.2026)

**Ringtyp** — `_ring_typ(chart, shape)` → `ANLAGEKLASSEN` | `BRANCHEN` | `REGIONEN`:
- ANLAGEKLASSEN: Kategorien sind Assetklassen (`_ist_assetklassen_ring`: alle in der Palette + mind. eine Kernklasse AKTIEN/RENTEN/EDELMETALLE/LIQUIDITÄT).
- BRANCHEN/REGIONEN: über den Shape-Namen (`C_Kennzahlen2` endet auf „2" = Branchen, `C_Kennzahlen1` auf „1" = Regionen) als Rückfall. FALLSTRICK: nicht allein auf den Namen verlassen — Assetklassen immer über die Kategorien erkennen.

**Familie** — `_familie_aus_prs(prs)` → `Thema` | `CVV` | `ESG` | `ETF` | None, aus dem Mapping (`_STRATEGIE_FAMILIE`, gespiegelt aus `Mapping_Namen.xlsx` Spalte „Powerpoint Familie"), gematcht gegen den **Folientitel**:
- **FALLSTRICK Überlappung:** Strategienamen überlappen zwischen Familien — „Offensiv" = Thema, aber „ESG Offensiv" = ESG. Deshalb **längster Treffer zuerst** (`sorted(..., key=-len)`) → „esg offensiv" schlägt „offensiv".
- **FALLSTRICK cVV-Prefix:** cVV-Broschüren lassen im Titel den Prefix WEG („Anlagestrategie Ausgewogen", nicht „cVV Ausgewogen"). Deshalb sind die nackten Formen (konservativ/defensiv/ausgewogen/…) als CVV im Mapping hinterlegt, ESG mit Prefix.
- Es werden NUR echte Titelzeilen durchsucht (Text mit „Anlagestrategie"/„Portfoliozusammenstellung"), damit Fließtext wie „Die Strategie Pro stellt…" kein False Positive erzeugt.
- `_ist_thema_familie` = `_familie_aus_prs == "Thema"`, mit **strukturellem Rückfall** (nur Thema hat Regionen-/Branchen-Ringe), falls das Titel-Matching mal leer ausgeht.

Verifiziert über alle 18 Broschüren: ESG→ESG, Offensiv/Pro/Pro Dividende→Thema, cVV→CVV.

---

### 33. Themen-Einzeltitel: Assetklassen-Ring wurde nie mit Daten befüllt (BUG, NEU 20.07.2026)

**Modul:** `modules/pptx_slides.py` — **Datenlogik**, NICHT chart_dynamik.

**Symptom:** Auf der Einzeltitel-Folie der Offensiv-Broschüre zeigte der Assetklassen-Ring nur **AKTIEN 98,09 % + LIQUIDITÄT 1,91 %** — EDELMETALLE (XETRA Gold 5,93 %) fehlte, obwohl es in der Tabelle rechts korrekt stand. Zusätzlich stimmte die Ring-Liquidität (1,91 %) nicht mit der Tabelle (4,76 %) überein.

**Diagnose (Kette Quelldaten → Klassifizierung → Aggregation → Befüllung):**
- `classify_gattung` (gold/edelmetall/silber → EDELMETALLE) und `group_portfolio_positions` (Gruppierung + implizite Liquidität = 1 − Σ Gewicht) sind **korrekt** — die Tabelle nutzt sie und stimmt.
- Ring-Befüllung liegt in `pptx_slides.py` per `replace_chart_data(C_Kennzahlen, categories, values)`. `fill_anlagevorschlag_slides` (Standard-Pfad) füllt den Ring **korrekt** über die `GROUP_ORDER`-Aggregation.
- **ROOT CAUSE:** `fill_einzeltitel_themen_slide` (der Thema-Pfad) füllte **NUR die Tabelle** — es gab **keinen einzigen `replace_chart_data`-Aufruf für den Ring**. Die Orchestrierung ruft für die Block-Rolle `einzeltitel_themen` auch keinen separaten Ring-Feed auf. Ergebnis: Der Ring behielt die **Platzhalter-Daten der Vorlage** (AKTIEN 98,09 % / LIQUIDITÄT 1,91 %).

**Fix:** In `fill_einzeltitel_themen_slide` direkt nach `group_portfolio_positions(df)` denselben `GROUP_ORDER`-Aggregations-Feed wie im Standard ergänzt (`alloc_labels`/`alloc_values` → `replace_chart_data`, `if ring and has_chart and sum>0`). Datengetrieben, generisch für alle Thema-Strategien, `if`-Guard macht ihn risikofrei. Verifiziert mit den echten Funktionen: Ring → AKTIEN 89,32 % / EDELMETALLE 5,93 % / LIQUIDITÄT 4,75 %, Summe 100 %, deckungsgleich mit der Tabelle.

**Merksatz:** Der Assetklassen-Ring ist ein **eigener Datenpfad** neben der Tabelle — beide können auseinanderlaufen. `chart_dynamik.py` ändert nie Werte; Datenfehler sitzen immer in `pptx_slides.py`.

---

### 34. Legenden-Box eines Ringes datenbasiert dimensionieren (BUG, NEU 20.07.2026)

**Modul:** `modules/pptx_slides.py` → Helfer `ensure_ring_legend_fits`, aufgerufen nur im Thema-Einzeltitel-Pfad nach `replace_chart_data`.

**Symptom (nach dem Ring-Fix #33):** Der Ring zeigte korrekt 3 Segmente, die **Legende** unten links aber nur AKTIEN — EDELMETALLE/LIQUIDITÄT fehlten. Später (nach Höhen-Fix) brach „EDELMETALLE" auf zwei Zeilen um und LIQUIDITÄT fiel weiter raus.

**Diagnose:** Bei einem nativen Donut leitet PowerPoint die Legende **automatisch aus den Kategorien** ab; `replace_chart_data` fasst die Legende NICHT an (nur cat/val-Caches), es gibt keine `legendEntry`-Löschungen und keine Filterung. Ursache war die **feste `manualLayout`-Box** der Legende:
- Thema-Einzeltitel-Vorlage: **0,99" breit × 0,49" hoch** — dimensioniert für die 2 Platzhalter-Kategorien.
- Funktionierende ESG/CVV-Ringe: 0,83–0,84" hoch → zeigen alle 4.
- Bei 9pt-Schrift braucht jeder Eintrag **~0,21" Höhe**; „EDELMETALLE" **~1,07" Breite**. → Höhe zu klein schneidet Einträge ab, Breite zu klein bricht lange Labels um (Umbruch frisst die Höhe).

**Fix `ensure_ring_legend_fits(chart_shape, categories)`:** vergrößert die Legenden-Box bei Bedarf
- **Höhe** nach OBEN (Unterkante bleibt am Rahmenboden → Legende bleibt im Bild): `n·per_entry_in(0,22) + pad`,
- **Breite** nach RECHTS (linke Kante bleibt): `swatch + max_label_chars·char_w(0,078) + pad`.

Vergrößert **nur**, verkleinert nie → adäquate Legenden (ESG/CVV) bleiben unangetastet; wird **nur im Thema-Pfad** aufgerufen. Generisch: skaliert mit Kategorienzahl UND längstem Label (keine hartcodierten Kategorien). Ergebnis Offensiv: 0,99×0,49" → **1,22×0,72"**, alle 3 Einträge einzeilig, rechte Kante 1,22" (klar vor Ring ~2,6" und Quelle-Notiz ~2,8").

**Nebeneffekt (gewollt):** Weil die Legende höher wird, verkleinert `chart_dynamik` (Pass 2b von `ring_labels_aussen_dynamisch`) den Ring auf dieser Folie minimal — konsistent mit den ESG/CVV-Folien.

---

### 35. Neue PowerPoint-Familie hinzufügen — das Playbook (NEU 21.07.2026, erprobt an ETF)

Diese Sequenz hat die ETF-Familie sauber und ohne Regression eingebaut. Für jede weitere Familie (es kommen noch welche) genau so vorgehen.

**Grundarchitektur (Wiederholung):** Familien-Configs stehen in `portfolioanalyse.py` → `VORLAGEN_FAMILIEN = {Familie: (Vorlage_<X>.pptx, config)}` und `FAMILIE_ALLE_STRATEGIEN`. Der Export `generate_portfolioanalyse_pptx(portfolios, performance_inputs, template_path, template_config)` befüllt N Strategien in zwei Modi:
- **Normal** (Standard/Themen): Block wird dupliziert (`_normalisiere_vorlage` + `_vervielfaeltige_block`).
- **`feste_bloecke`** (Infoboards CVV/ESG/ETF): Vorlage hat alle Strategie-Folien vorgebaut → wird an FESTEN 1-indexierten Positionen befüllt, keine Duplikation.
- **`einmal_folien`** = `{uebersicht: N, vergleich: M}` läuft einmal für alle Strategien (Vergleichstabelle / Linien-Chart „Diagramm").
- Rollen: `anlagevorschlag` (Ring `C_Kennzahlen` + Tabelle `T_Kennzahlen`), `wertentwicklung` (Diagramm links/rechts + Kennzahlen — die Folie heißt in der Vorlage „Performance", die Code-Rolle ist aber `wertentwicklung`!), `performance`, `zusammenstellung`, `rollierend`, `einzeltitel_themen`. `rollen_optionen[rolle]` reicht kwargs durch.

**Schritt 1 — Vorlage analysieren.** Folienzahl; je Folie Charts/Tabellen + Shape-Namen + Titel. Entscheidend: Welche Folien unterscheiden sich zwischen Infoboard und Einzel-Broschüre (bzw. je Auswertungsdatum) → **dynamisch**; identischer Inhalt → **statisch**. Mit der nächstähnlichen Familie (ESG/CVV) vergleichen, um das Muster zu finden.

**Schritt 2 — Folien→Rollen mappen.** Welche Folie ist `anlagevorschlag`, welche `wertentwicklung`, welche die Vergleichsfolie (`uebersicht`-Tabelle bzw. `vergleich`-Chart).

**Schritt 3 — Config additiv schreiben** (`portfolioanalyse.py`): `_<FAM>_STRATEGIEN` (exakte Mapping-Namen aus „Strategie auswählen", in Folienreihenfolge), `_<FAM>_CONFIG` (`erwartete_folien`, `feste_bloecke` = [{Rolle: 1-indexierte Position} je Strategie], `einmal_folien`, `rollen_optionen`), dann Einträge in `VORLAGEN_FAMILIEN` und `FAMILIE_ALLE_STRATEGIEN`. **Ziel: 0 gelöschte Zeilen.** Der Loader `_familien_portfolios` ist generisch — greift automatisch, sobald die Familie registriert ist und die CSVs existieren.

**Schritt 4 — Layout-Abweichungen NIE durch Forken lösen.** Weicht die Vorlage ab (ETF: `T_Kennzahlen` hat 7 statt 11 Spalten, ohne Kupon/Fälligkeit), dann der geteilten Funktion einen **optionalen Parameter mit Default = altem Verhalten** geben (bei ETF: `spalten_map`, Default `DEFAULT_SPALTEN_MAP`), über `rollen_optionen` durchreichen und **byte-identisch belegen**: altes Modul vs. neues Modul (mit Default) dieselbe Tabelle/df füllen, Zellen vergleichen. Zusätzlich beide Dateien diffen — die bestehenden Familien-Configs müssen **0 geänderte/entfernte Zeilen** zeigen.

**Schritt 5 — Vorlage verkleinern + benennen.** Bilder-Komprimierung (siehe Transferwissen zur PNG/JPEG-Optimierung; ETF 55 MB → 12 MB). Datei zeichengenau `Vorlage_<FAM>.pptx` benennen (passend zu `VORLAGEN_FAMILIEN`), **nicht per GitHub-Web-UI umbenennen** (#23). Nutzer liefert: Vorlage im Ordner `Vorlage/` + Positions-CSVs der Strategien (mit Marktrisikowert). Tuning-Werte (`max_bottom_inch`, `original_row_h_inch`) an der Vorlage messen und nach echtem Deploy kalibrieren.

**Blast-Radius-Disziplin (der Grund, warum es reibungslos lief):** Erst analysieren, was existiert; additiv NEBEN dem laufenden Pfad bauen; Defaults byte-identisch halten; per Diff + Byte-Vergleich beweisen; jede Datei mit einem konkreten Verifikationssignal ausliefern.

**ETF-Konkret (Referenz):** 2 Strategien `ETF_ausgewogen`/`ETF_Wachstum`, `Vorlage_ETF.pptx` (35 Folien), spiegelt ESG ohne Vergleichs-Chart. `feste_bloecke=[{anlagevorschlag:16,wertentwicklung:17},{anlagevorschlag:18,wertentwicklung:19}]`, `einmal_folien={uebersicht:20}` mit `spalten=[4,6]`. Der 7-Spalten-Spalten-Map: `{wertpapier:0, kupon:None, faelligkeit:None, wkn:2, anteil:4, rating:6, spacers:[1,3,5]}`.

---

### 36. comdirect-Familie — reine Config, wenn keine Layout-Abweichung (NEU 21.07.2026)

comdirect („Klassische Portfolioverwaltung", 27 Folien, 3 Strategien Comdirect_30/70/100) war die einfachste Familie: **reine Config-Ergänzung, kein Eingriff in geteilte Funktionen**. Grund: `T_Kennzahlen` ist das Standard-11-Spalten-Layout (kein `spalten_map` nötig) UND es gibt keine dynamische Vergleichsfolie (F5 = statische Strategie-Beschreibung, F21 = Firmen-AuM-Wachstum → beide statisch, also kein `einmal_folien`). Dynamisch sind nur F6/8/10 (`anlagevorschlag`) + F7/9/11 (`wertentwicklung`).

**Mapping-Falle:** Die drei Strategien standen im Mapping (Comdirect_30/70/100), aber die Spalte „Powerpoint Familie" war leer → der Nutzer trug „comdirect" ein (Familien-Auflösung ist case-insensitiv). **Komprimierungs-Falle:** 20 MB → 7 MB, dabei fehlte in `[Content_Types].xml` der `jpg`-Default (anders als bei ETF) → nach PNG→JPG-Umbenennung ließ sich die Datei nicht öffnen, bis `<Default Extension="jpg" ContentType="image/jpeg"/>` vor `</Types>` ergänzt wurde.

---

### 37. Konfigurierbare Export-Dateinamen je Familie/Strategie (NEU 21.07.2026)

Der Broschüren-Dateiname wird an EINER Stelle aus einer editierbaren Konfig-Sektion in `portfolioanalyse.py` gebaut (`_export_dateiname`). Auflösung in dieser Reihenfolge: `EXPORT_NAME_STRATEGIE[Strategie]` (Vorrang) → `EXPORT_NAME_FAMILIE[Familie]` → `EXPORT_NAME_DEFAULT`. Platzhalter `{datum}`, `{strategie}`, `{familie}`; Datumsformat global (`EXPORT_DATUM_FORMAT`) oder je Eintrag als Tupel `("Muster", "%Y%m%d")` — comdirect nutzt `yyyymmdd`, die übrigen `dd.mm.yyyy`. Die Endung `.pptx` wird automatisch angehängt; ein Sanitizer entfernt nur dateisystem-illegale Zeichen (`\ / : * ? " < > |`), behält Punkte/Leerzeichen.

**Abhängigkeit (wichtig):** `download_helfer.py` reicht den Namen 1:1 durch (`a.download = json.dumps(dateiname)`), säubert NICHT — d. h. Punkte und Leerzeichen im Wunschnamen kommen exakt so an. Die tricky clientseitige Blob-Download-Mechanik blieb unangetastet (nur der übergebene String änderte sich).

---

### 38. Download-Button nach oben + kontextbezogener Familien-Hinweis (NEU 21.07.2026)

Der komplette Export-Block (Cache-Invalidierung + „PowerPoint erstellen" + Download) wurde direkt UNTER den „📅 Momentaufnahme per …"-Hinweis verschoben, noch vor die Tabellen/Charts. Voraussetzung war ein **Abhängigkeits-Check**: alle genutzten Variablen (`pf_sel_1`, `df_pf_1`, `ad1`, `dur_1`, `pf_sel_2`, `show_compare_pf`, `pf_brutto_mwst` …) sind schon vor dem Hinweis verfügbar; `portfolios`/`perf_timeseries`/`performance_inputs` baut der Block selbst. Die **Cache-Invalidierung MUSS mitwandern** (sie entscheidet, ob der Download-Button erscheint) — sonst zeigt der Button veraltete Daten.

Darunter ein **kontextbezogener Hinweis** (`_render_familien_hinweis`): nur bei Familien-Strategien, nennt Familie + alle Strategien (z. B. „Die CVV-Broschüre enthält immer alle 5 Strategien …, auch wenn oben nur ‚Konservativ' gewählt ist"). Der Text wird automatisch aus `FAMILIE_ALLE_STRATEGIEN` gezogen — neue Familie? Hinweis stimmt von allein. Bei Einzel-Strategien erscheint nichts. `download_bereich` byte-identisch, nur an anderer Stelle aufgerufen.

---

### 39. `_folien_config` — statische/dynamische Folien als geordnete Liste (NEU 21.07.2026, löst die Positions-Handarbeit aus #35 ab)

Statt Positionen von Hand in `feste_bloecke`/`einmal_folien` zu pflegen (fehleranfällig, sobald eine Folie eingefügt wird), beschreibt man die Broschüre jetzt **Folie für Folie als geordnete Liste**; die Position ergibt sich aus dem Listenindex. Helfer `_folien_config(folien, rollen_optionen, entfernen)` in `portfolioanalyse.py`. Einträge (Label immer am Ende, REINE Doku — fließt nie in die Logik):

- `("S", "Label")` — statische Folie (Generator fasst sie nie an)
- `("<rolle>", n, "Label")` — dynamische Folie der Strategie n (0-basiert)
- `("<rolle>", "*", "Label")` — Einmal-Folie (uebersicht / vergleich)

**Neue statische Folie = EIN Eintrag einfügen** → alle folgenden Positionen verschieben sich automatisch, `erwartete_folien` stimmt von allein. Kein Umnummerieren mehr; die Config liest sich wie eine Landkarte der Broschüre (mit echten Folientiteln als Labels).

comdirect, CVV, ESG, ETF sind umgestellt — je Familie per dict-Vergleich bewiesen, dass `_folien_config(...)` **exakt** die alte Hand-Config erzeugt (null Verhaltensänderung), und die Blöcke wurden aus den bewiesenen Listen generiert (kein Abtippfehler). `pptx_export.py` bleibt unangetastet. **Thema** läuft weiter im normalen Dupliziermodus (`block_reihenfolge`/`block_positionen`) und ist NICHT umgestellt (passt nicht 1:1 in die Liste).

---

### 40. Familienspezifische Ring-Optik — `FAMILIE_RING_FORMAT` (NEU 27.–28.07.2026) ⭐ die Grafik-Insights

Die Ring-Optik (Grafik) ist jetzt **je Familie überschreibbar**, über einen CONFIG-Block in `chart_dynamik.py`. Nur gelistete Familien weichen ab; alle anderen nutzen `_RING_FORMAT_DEFAULT` → deren Ringe bleiben **byte-identisch** (per ALT-vs-NEU-XML-Vergleich bewiesen). CVV, ESG, ETF, Thema und comdirect teilen ein gemeinsames Dict `_RING_KRAEFTIG`; nur „Standard" (Strategien ohne Familie) bleibt auf dem Default-Look.

**Die kräftige Optik (`_RING_KRAEFTIG`):**
- `hole: 68` — dickerer, markanterer Ring (Default 79; kleiner = dicker)
- `leader_breite_emu: 15875` — Führungslinien 1,25 pt (kräftig, aber nicht dominant)
- `label_fett: True` — Prozentzahlen fett, bleiben schwarz (keine Größenänderung)
- `punkte: True`, `punkt_durchmesser: 0.05` — kleine dezente Punkte am Label-Ende
- `leader_start_tiefe: 0.5` — Ansatz auf die MITTE der Ringdicke
- `leader_gerade: True` — ruhige gerade Linien statt harter Haken
- `label_gap_in: 0.18` — Labels etwas luftiger außerhalb

**Die zentralen Insights (teils per Screenshot-Iteration teuer erkauft):**

1. **Leader starten BEWUSST im Ringband, nicht am Außenrand.** Der Ansatz liegt (per `leader_start_tiefe`, R_start = R_out − tiefe·(R_out−R_in)) in der Bandmitte; die Linie kommt sichtbar aus dem farbigen Segment. Ein Versuch, den Ansatz nach außen auf den „echten" Rand zu schieben (`leader_aussen_faktor`), wurde **ausdrücklich verworfen** — genau der Start IM Band ist gewollt. **Merke: das ist kein Bug, nicht „reparieren".**

2. **PowerPoint zeichnet den Ring-Außenrand weiter außen als das aus `plotArea` berechnete `R_out`.** Beim dünnen Ring unauffällig, beim dicken Ring sichtbar. Das war die Quelle der Verwirrung „Linien starten im Ring" — es ist aber der gewünschte Effekt. (Diagnose: Bildvermessung + Render; LibreOffice taugt nicht, s. #28.)

3. **Gerade, gleichartige Linien.** Der frühere Knick (radialer Teil + horizontaler Stub) wirkte als „harte technische Haken" und war uneinheitlich (mal Knick, mal gerade). `leader_gerade=True` macht ALLE Linien gerade → ruhig, gleichmäßig, bewusst gesetzt.

4. **Punkte gehören ans Label-Ende** (`punkte[-1]`), nie an den Ring; klein/dezent (0,05").

5. **Familien-Erkennungs-Falle (comdirect):** Die Ring-Optik greift über `_familie_aus_prs`, das die Familie am **Folientitel** erkennt (`_STRATEGIE_FAMILIE`, GETRENNT von `portfolioanalyse.py`s `_familie_fuer_strategie`). Der comdirect-Config-Eintrag allein bewirkte NICHTS, bis die comdirect-Titelformen ergänzt wurden — Struktur-Folien heißen „Anlagestrategie **Portfolioverwaltung** 30/70/100", Performance-Folien „**Comdirect** 30 | Wertentwicklung". Beide Formen sind jetzt im Mapping.

6. **Thema behält, WELCHE Ringe Punkte bekommen:** nur Assetklassen-/Branchen-Ringe (`PUNKT_RINGTYPEN`), der Regionen-Ring NICHT — auch mit `punkte=True` (die Ringtyp-Regel bleibt).

**Mechanik:** `nachbearbeiten` ermittelt die Familie einmal (`_fam = _familie_aus_prs(prs)`), holt `_fmt = _ring_format(_fam, hole_size, label_gap_in)` (löst `hole`/`label_gap_in` bei `None` auf die globalen Defaults auf) und reicht die Werte an `ring_holesize`, `ring_leader_zeichnen` (neu: `start_tiefe`, `gerade`, `breite_emu`, `punkt_durchmesser`) und `ring_label_schriftfarbe` (neu: `fett` → setzt `b="1"`) durch. Segmentfarben (`ring_segmentfarben`) und Datenlogik unverändert.

**Zum Justieren** (alles Zahlen in `_RING_KRAEFTIG`, eine Stelle für alle fünf Familien; für eine abweichende Familie einen eigenen Block geben): Start tiefer ins Band → `leader_start_tiefe` 0,6–0,7. Linien kräftiger → `leader_breite_emu` z. B. 17462 (1,375 pt). Punkte kleiner → `punkt_durchmesser` z. B. 0,04. Labels luftiger → `label_gap_in` z. B. 0,20.

---

### 41. „Kein Wert" kommt in Finanzdaten oft als NULL, nicht als NaN (BUG, NEU 07.08.2026) ⭐

**Situation:** Du prüfst, ob eine optionale Spalte einer Datenlieferung überhaupt Inhalt hat — z.B. eine Benchmark-Zeitreihe.

**Falle:** Der naheliegende Test `df["spalte"].notna().any()` prüft auf *fehlende* Werte. Datenlieferanten liefern „nicht vorhanden" aber häufig als **0**, nicht als leeres Feld. `0.0` ist nicht `NaN` → der Test sagt True → die Nullreihe wird als echte Daten durchgerechnet.

**Konkret in diesem Projekt:** Infront liefert für Strategien ohne Vergleichsmaßstab eine Benchmark-Spalte aus lauter Nullen. Betroffen sind „Muster SCHWEIZ Aktien" (1409 von 1409 Zeilen null) und „Muster SCHWEIZ Substanz" (1399/1399); im `Mapping_Namen.xlsx` steht bei beiden ausdrücklich „Haben keine Benchmark". Ergebnis in der **Kundenbroschüre**:

```
performance_pa_bench      0,00 %
volatilitaet_bench        0,00 %
sharpe_bench            -67,48      ← der Wert, der es verraten hat
max_drawdown_bench        0,00 %
Linien-Chart: flache Benchmark bei 100 %
```

Die Sharpe Ratio entlarvt es: Bei konstanter Nullrendite ist die Überrendite exakt `−rf` mit Standardabweichung nahe null → der Quotient explodiert. Die anderen drei Kennzahlen sehen dagegen plausibel aus und wären wohl nie aufgefallen.

**Lösung:** `analytics.has_benchmark()` — vorhanden UND mindestens ein Wert ungleich null:

```python
def has_benchmark(ret_bm) -> bool:
    werte = pd.Series(ret_bm).dropna()
    if werte.empty:
        return False
    return bool((werte != 0).any())
```

**Wichtig bei der Abgrenzung:** *Einzelne* Nulltage sind normal und müssen gültig bleiben — rund 29 % aller Zeilen sind Wochenenden, an denen der Index steht. Nur die **komplett** leere Reihe darf durchfallen. Deshalb `.any()` auf „ungleich null", nicht etwa eine Quotenschwelle.

**Übertragbar:** Dieselbe Frage stellt sich bei jeder optionalen Spalte aus Fremdsystemen — Duration, Kupon, Rendite, Währung. Wenn „kein Wert" als 0 geliefert wird, ist `notna()` der falsche Test. Prüfe bei neuen Spalten einmal, wie der Lieferant „leer" kodiert.

**Prüfstein:** `tests/test_benchmark_erkennung.py` — läuft gegen die echten CSVs, ohne pytest und ohne Streamlit (`python tests/test_benchmark_erkennung.py`). Erwartung: 2 Strategien ohne Benchmark, 17 unverändert.

---

### 42. Vorlagen-Rahmen wandern NICHT mit den Daten (BUG, NEU 07.08.2026) ⭐

**Situation:** Eine PPTX-Vorlagentabelle ist optisch vorstrukturiert — dicke Trennstriche unter den Kategorie-Überschriften, dünne zwischen den Positionen. Der Code füllt die Zeilen dann mit echten Daten.

**Falle:** `set_cell_text` schreibt Text und Fettung, **fasst Rahmenlinien aber nie an**. Die Striche bleiben an ihren Vorlagen-Positionen kleben, während die Kategorien je nach Portfolio ganz woanders beginnen. Das Ergebnis sieht auf den ersten Blick sauber aus — es ist ja *eine* Linie da —, sitzt aber falsch.

**Konkret:** In der CVV-Broschüre „Defensiv" lief der dicke Strich mitten durch die Rentenliste zwischen *Fraport* und *Fresenius*, während der Übergang *Würth Finance* → **AKTIEN** gar keinen bekam. Über alle fünf Familien: **80 falsch platzierte Trennstriche**. Aufgefallen ist es einem Menschen beim Draufschauen, keinem Test.

**Regel (fachlich festgelegt, Philip 07.08.2026):** Dicker Strich **nur unter der Kategorie-Überschrift**; zwischen Positionen und vor der nächsten Überschrift die dünne Linie.

```
Würth Finance IHS 3 %     ← dünn darunter
AKTIEN                    ← DICK darunter
Future of Defence ETF     ← dünn darunter
```

**Lösung:** `pptx_slides.tabelle_kategorie_trennlinien(table)` — läuft NACH dem Befüllen und nach `remove_empty_table_rows` (sonst stimmen die Zeilenindizes nicht mehr).

Zwei Umsetzungsdetails, die den Unterschied machen:

1. **Linienarten aus der Tabelle ERNTEN statt nachbauen.** Pro Spalte werden die dickste und die dünnste vorhandene Unterkante gesucht und per `_zelle_rahmen_uebernehmen` kopiert. So bleiben Stärke, Farbe und Strichart der Vorlage exakt erhalten — ein nachgebauter Rahmen träfe das Corporate Design nie.
2. **An jeder Zeilengrenze BEIDSEITIG setzen** (`lnB` oben, `lnT` unten). Renderer führen angrenzende Zellrahmen zusammen; setzt man nur eine Seite, gewinnt mal die eine, mal die andere. (Dasselbe Prinzip steht schon in `tabelle_abstandszeile_einfuegen`.)

**Kategorie-Erkennung** über die Fettung der ersten Spalte — `fill_table_with_positions` schreibt Gruppennamen mit `is_bold=True`, Positionen mit `is_bold=False`. Das Merkmal sitzt damit am Ergebnis, nicht an einer parallel gepflegten Liste.

**Übertragbar:** Bei JEDER vorstrukturierten Vorlagentabelle gilt — was der Code nicht aktiv setzt, bleibt auf dem Stand der Vorlage. Das betrifft Rahmen, Hintergrundfarben, Zeilenhöhen und Zellverbünde gleichermaßen. Wenn Daten die Struktur verschieben können, muss die Optik mitgezogen werden.

**Prüfstein:** `tests/test_trennstriche.py <ordner>` — prüft erzeugte Broschüren gegen die Regel. Verifiziert: rot auf dem alten Stand, grün nach dem Fix.

---

### 43. Die ersten Datenpunkte sind oft nur Indexbasis, kein Track Record (NEU 07.08.2026)

**Situation:** Eine Broschüre schreibt „Wertentwicklung seit *Auflagejahr*" und leitet das Jahr aus dem ersten Datenpunkt der Zeitreihe ab.

**Falle:** Datenlieferanten setzen als erste Zeilen gern den **Schlussstand des Vorjahres**, damit die Indexierung einen Startwert hat. Diese Zeilen sind keine Wertentwicklung — sie sind der Nullpunkt. Wer das Jahr daraus ableitet, weist ein Jahr aus, in dem faktisch nichts passiert ist.

**Konkret:** Die klassischen cVV-Reihen beginnen am **30.12.2008** — zwei Zeilen. Die Broschüre schrieb „Wertentwicklung seit 2008 kumuliert" und suggerierte damit einen Track Record über das Krisenjahr 2008, den es nicht gibt. Fachlich beginnt er am 01.01.2009.

**Lösung:** `HISTORIE_AB` in `modules/vorlagen_config.py` + `portfolioanalyse.historie_beschneiden()`. Die Zeitreihe wird **einmal** beschnitten, bevor irgendetwas gerechnet wird:

```python
HISTORIE_AB = {
    "Muster konservativ cVV":   "2009-01-01",
    ...
    "Muster offensiv cVV":      "2009-01-01",   # Familie Thema
}
```

**Der wichtigste Entwurfsentscheid — Schlüssel ist die DATENREIHE, nicht die Familie.** Die Eigenschaft steckt in den Daten, nicht in der Broschüre: „Offensiv" gehört zur Familie *Thema*, nutzt aber die Reihe `Muster offensiv cVV` (früher eine cVV-Strategie) und hat denselben Stummel — während *Pro* und *Pro Dividende* derselben Familie nicht betroffen sind. Über einen Familien-Schlüssel wäre das nicht sauber abbildbar gewesen.

**Warum EINE Stelle vor allen Berechnungen:** Beschriftung, kumulierte Wertentwicklung, Rendite p.a. und Linien-Chart leiten sich alle aus derselben Zeitreihe ab. Wer stattdessen nur das Label korrigiert, erzeugt genau die Inkonsistenz, gegen die die Konsistenz-Doktrin (§10.8) geschrieben wurde.

**Bewusst keine Automatik** („erstes Jahr mit weniger als N Tagen abschneiden"): Eine Schwelle träfe irgendwann eine Reihe, bei der das Abschneiden falsch wäre. Geprüft: nur die cVV-Reihen sind betroffen — ESG startet mit 93 Tagen im ersten Jahr, ETF mit 32, comdirect mit 296.

**Übertragbar:** Bei jeder neuen Datenreihe einmal nachsehen, wie viele Tage das erste Jahr trägt. Ein- oder zweistellige Werte sind ein Warnsignal.

**Prüfstein:** `tests/test_historie_ab.py` — prüft zusätzlich, dass jeder Konfigurationseintrag wirklich in den Daten existiert. Das fängt Tippfehler und spätere Umbenennungen durch Infront ab, die sonst still wirkungslos blieben.

---

### 44. Ring-Labels: vermessen, verstanden — und bewusst nicht geändert (NEU 10.08.2026) ⭐

**Anlass:** Kleine und dicht benachbarte Segmente wirken gedrängt; die Zuordnung Segment ↔ Prozentwert ist nicht sofort klar. Gewünscht war eine allgemein bessere Label-Positionierung, nicht ein Einzelfall-Fix.

**Entscheidung von Philip nach der Diagnose: Der Stand bleibt.** „Wir sind am Zenit angekommen." Am Code wurde **nichts** geändert. Dieser Eintrag hält fest, was gemessen wurde — damit die Diagnose nicht noch einmal erarbeitet werden muss.

#### Der Ist-Zustand, gemessen an 143 Labels in 32 Ringen (alle sieben Broschüren)

| Kennzahl | Wert |
|---|---|
| Abweichung Segment ↔ Label, Mittel | 20,0° |
| Median / Maximum | 12,8° / **92,0°** (ESG F22, EDELMETALLE) |
| Labels > 12° / > 30° / > 45° daneben | 77 / 25 / **21** |
| Eng stehende Label-Paare | 18 |
| Überkreuzende Leader · zu kurze Leader | **0 · 0** ✓ |

Die Fixes aus #29–#31 halten also. Das Restproblem ist ein anderes: **54 % der Labels stehen mehr als 12° neben ihrem Segment.**

#### Die Ursachenkette (am Beispiel ESG F16, LIQUIDITÄT 6,52 %, Segment bei 348,3° = 11:37 Uhr)

| Schritt | x-Position des Labels |
|---|---|
| radiale Zielposition (Pass 5) | `cx − 0,21"` → **links** der Mitte ✓ |
| tangentialer Versatz `tangential_klein = 0,24"` | `cx + 0,03"` → **rechts** der Mitte |
| Pass 6d: `seite = 1.0 if dx0 >= 0 else -1.0` | dreht das Label die **rechte** Seite hinunter |
| Ergebnis | Label bei 53,3° = 1:46 Uhr — **65° daneben** |

**Ein Schubs von 0,24" kippt eine 65°-Entscheidung.** Die Führungslinie läuft dann quer über den Ringkopf und liegt dabei fast tangential auf der Ringkante — genau das wirkt unruhig.

**Warum überhaupt gedreht wird:** Oben ist zu. `kopf_sperre_aus_usershapes` addiert **0,30" Luft** auf die Balken-Unterkante. Das Label bräuchte seine Mitte bei y = 0,41", die Sperre erlaubt erst 0,65". Wegen **0,14" Platzmangel** wird ein Label 65° um den Ring gedreht.

Betroffen ist systematisch **LIQUIDITÄT in jeder Familie** — als letztes Segment der `GROUP_ORDER` endet es immer kurz vor 12 Uhr, also genau unter dem Überschriftenbalken.

#### Zwei Experimente (beide zurückgerollt)

| Kennzahl | heute | Spreizung 60°→24° | **Kopfluft 0,30"→0,12"** |
|---|---|---|---|
| Abweichung Mittel | 20,0° | 19,0° | **14,9°** |
| Abweichung Maximum | 92,0° | 65,2° | **52,7°** |
| Labels > 45° | 21 | 20 | **5** |
| Enge Paare | 18 | **22** ✗ | **9** |
| Leader-Länge Mittel | 0,68" | 0,66" | 0,60" |

**Erst-These war falsch:** Die 60°-Winkelspreizung (`min_gap_deg_klein`) ist *nicht* der Treiber — sie ließ die großen Fälle unverändert und verschlechterte die engen Paare. Sie half nur beim Extremfall ESG F22 (92° → 23°).

**Der wirksame Hebel ist die Kopfluft:** eine Zahl halbiert die engen Paare und drückt die schlimmste Kategorie um 76 %.

#### Ansatzpunkte, falls das Thema wieder aufgemacht wird

1. **Kopfluft datenbasiert** statt fix 0,30" — größter gemessener Hebel, kleinster Eingriff. Offene Frage: wie nah dürfen Zahlen optisch an den Balken?
2. **Seitentreue** — `seite` in Pass 6d aus dem *Segmentwinkel* ableiten statt aus der aktuellen x-Position. Kippt die Ursachenkette oben (~10 Zeilen).
3. **Entzerrung in 2D** — Pass 6 schiebt nur senkrecht, deshalb stehen alle engen Paare bei exakt `dy = 0,21"` (Text ist 0,20" hoch). Seitlich sind 1,4–1,6" frei. **Höchstes Risiko**, das ist der am stärksten austarierte Pass.
4. **Anti-Kreuzung nur zwischen winkelbenachbarten Paaren** — der Tausch in Pass 6e darf heute beliebige Paare vertauschen; genau daraus entsteht der 92°-Ausreißer.

#### Wovon ausdrücklich abgeraten wird

**Keine neue Layout-Engine** (Kräftemodell, Solver, Annealing). Drei Gründe:
- Genau das ist schon einmal gescheitert (Cluster-Engine, #29) — sie ersetzte das Layout, statt Ausreißer zu reparieren.
- Die 8 Pässe sind kein Chaos, sondern verdichtetes Erfahrungswissen über PowerPoint-Eigenheiten (wann PP einen Leader zeichnet, Bogengrenzen-Regel, absolute Positionierung). Ein Neubau riskiert alle gleichzeitig.
- Die Abnahme ist menschlich: LibreOffice ist als Beweis unbrauchbar (#29), jede Iteration braucht einen Blick in echtes PowerPoint. Ein Verfahren mit vielen Stellschrauben ist so nicht durchzutunen.

**Ein Rest ist nicht algorithmisch lösbar:** „zwei kleine Segmente dicht nebeneinander direkt unter dem Überschriftenbalken". Oben ist zu, beide wollen dieselbe Seite. Es gibt keine geometrisch gute Antwort, nur eine bewusst gewählte, konsistente Regel — das ist eine Design-, keine Rechenfrage.

**Übertragbar:** Bei Layout-Problemen dieser Art zuerst den *verfügbaren Platz* messen, nicht den Algorithmus verdächtigen. Hier steckte die Ursache in einer Randbedingung (0,30" Sicherheitsabstand), nicht in der Positionierungslogik — und die Kette aus drei je für sich vernünftigen Pässen machte sie unsichtbar.

**Messmethode:** Geometrie direkt aus dem Chart-XML der fertigen Broschüren (plotArea-Layout → Mittelpunkt/Radius, `val`+`firstSliceAng` → Segmentwinkel, `dLbl`/`manualLayout` mit `xMode=edge` → Label-Mitte). Damit sind Abweichung, Leader-Länge und Paar-Abstände ohne Rendern reproduzierbar.

---

### 45. Statische Vorlagen-Inhalte finden: ein Shape ist selten ein Textfeld (NEU 10.08.2026) ⭐

**Anlass:** Der Anlagekriterien-Kasten der Struktur-Folien sollte ins Streamlit-Tool übernommen werden. Der naheliegende erste Griff — alle Shapes der Folie durchgehen und `shape.text_frame.text` lesen — fand **nichts** außer Titel und Foliennummer. Der Kasten war „unsichtbar".

**Ursache:** Sichtbarer Text steckt in PowerPoint an **vier** verschiedenen Orten, und nur einer davon ist ein Textfeld:

| Ort | Zugriff | Beispiel in diesem Projekt |
|---|---|---|
| Textfeld / Platzhalter | `shape.text_frame.text` | Titel, Fußnote, Quelle |
| **Tabelle** | `shape.table.cell(r,c).text` | **Anlagekriterien-Kasten**, T_Kennzahlen |
| Gruppe | rekursiv über `shape.shapes` | — (hier keine, aber jederzeit möglich) |
| `chartUserShapes` | über `chart.part.rels`, Namespace `chartDrawing` | Balken „AKTUELLE STRUKTUR", Quelle-Zeile |

`has_text_frame` ist bei Tabellen **False**. Ein Scan, der nur darauf prüft, übersieht sie lautlos — kein Fehler, kein Hinweis, nur ein leeres Ergebnis.

**Regel:** Beim Suchen nach statischem Vorlagentext immer alle vier Orte abklopfen — `has_table` und Gruppen-Rekursion gehören dazu. Der Balken über dem Ring ist der zweite Klassiker: er liegt nicht auf der Folie, sondern im Chart-Part (siehe `kopf_sperre_aus_usershapes`).

**Der Anlagekriterien-Kasten konkret:**
- Tabelle **5 Zeilen × 3 Spalten**, Shape-Name `Tabelle`, Position **(0,38 / 1,14)", Größe 4,34 × 1,42"**
- Spalte 0 = Bezeichnung, Spalte 1 = leer (Abstandsspalte), Spalte 2 = Wert
- Zeile 0 ist die Kopfzeile: `Anlagekriterien` | | `<Strategiename>`
- Zeilen 1–4: Anlageregion · Aktienanteil · Anleihenanteil / Liquidität · Fremdwährungen

**Fundstellen je Familie** (Struktur-Folien, Rolle `anlagevorschlag`):

| Familie | Folien | Strategien |
|---|---|---|
| CVV | 7, 9, 11, 13, 15 | Konservativ, Defensiv, Defensiv Plus, Ausgewogen, Dynamic |
| ESG | 16, 18, 20, 22 | ESG Defensiv, Defensiv Plus, Ausgewogen, Offensiv |
| ETF | 16, 18 | ESG-ETF Ausgewogen, Wachstum |
| comdirect | 6, 8, 10 | FFPB Strategie 30 / 70 / 100 |
| **Thema** | — | **kein Kasten** (Rolle `einzeltitel_themen`) |

Zusammen **14 Strategien**.

**Robust suchen — inhaltsbasiert, nicht über den Namen:** Der Shape-Name `Tabelle` ist auf der Wertentwicklungs-Folie die Kennzahlen-Tabelle. Wer über den Namen sucht, erwischt die falsche. Zuverlässig ist: *die Tabelle, deren Zelle (0,0) „Anlagekriterien" enthält.*

```python
def kriterien_tabelle(slide):
    for sh in slide.shapes:
        if getattr(sh, "has_table", False) and len(sh.table.rows) >= 2:
            if "anlagekriterien" in sh.table.cell(0, 0).text.strip().lower():
                return sh
    return None
```

**Übertragbar:** Wenn ein Vorlagen-Element „nicht auffindbar" ist, liegt es fast nie daran, dass es fehlt — sondern daran, dass der Scan den falschen Shape-Typ prüft. Erst einen vollständigen Dump aller Shapes einer Folie ziehen (Typ, Name, Position, Inhalt), dann gezielt suchen.

---

### 46. Ein Platzhalterwert pflanzt sich fort — bis in den Fließtext (BUG, NEU 11.08.2026) ⭐

**Situation:** Am 07.08.2026 wurde der Null-Benchmark-Bug behoben (#41): Eine
Spalte aus lauter Nullen ist keine Benchmark, `has_benchmark` erkennt das, die
Kennzahlen zeigen „–". Fall abgeschlossen — dachten wir.

**Falle:** Die Erkennung war richtig, aber sie wurde nur an EINER Stelle
ausgewertet. `compute_performance_data` füllte die Chart-Serien weiterhin auf:

```python
if has_bm:
    pa_bench.append(calc_period_return(rb_y))
else:
    pa_bench.append(0.0)          # ← „keine Benchmark" wird zu „Benchmark = 0"
...
wert_bench = [1.0] * len(dates)   # ← und zu einer Index-Linie bei 100 %
```

Damit war die Information „es gibt keine Benchmark" **hinter der Datenstruktur
verschwunden**. Jede nachgelagerte Stelle sah eine gültige, vollständige Serie
und tat pflichtschuldig das Ihre.

**Was am echten Artefakt herauskam** (*Muster SCHWEIZ Substanz*, Themen-Broschüre):

| Stelle | Was stand da |
|---|---|
| Säulen-Chart | Serie „Benchmark" mit vier Nullen → vier Null-Balken |
| Linien-Chart | nichts — diese Folie übergibt ohnehin nur eine Serie |
| Legenden-Textbox | „Musterdepot     Benchmark***" |
| Fußnote | „*** 50% EuroStoxx 50; 50% MSCI World Euro" |

Die letzte Zeile ist der eigentliche Fund. Der Code schrieb die ***-Zeile nur
dann um, wenn ein Benchmark-Text vorlag — sonst blieb der **Vorlagentext**
stehen. Die Vorlage stammt von „Pro". Die Kundenbroschüre für SCHWEIZ nannte
also die Benchmark-Zusammensetzung einer fremden Strategie: keine Optik,
sondern eine **falsche Sachaussage in einem Kundendokument**.

**Zwei übertragbare Lehren:**

**1. Ein Fehlwert darf nicht wie ein Messwert aussehen.** `0.0` und `1.0` sind
gültige Zahlen; „nicht vorhanden" ist keine. Wer auffüllt, um die Struktur
gleich lang zu halten, verschiebt das Problem nur nach hinten — dorthin, wo
niemand mehr nachfragen kann. Richtig ist eine leere Liste plus ein
ausdrückliches Kennzeichen:

```python
return {
    "has_benchmark": has_bm,          # explizit, nicht aus Daten erratbar
    "performance_pa": {"jahre": jahre, "referenz": pa_ref,
                       "benchmark": pa_bench},   # leer, wenn has_bm False
}
```

**2. „Nicht vorhanden" muss ÜBERALL ankommen, auch im statischen Text.**
Eine Vorlage besteht nicht nur aus Charts. Beim Weglassen einer Größe ist
jeder Ort zu prüfen, an dem sie vorkommt:

- die **Chart-Serie** (python-pptx entfernt überzählige `<c:ser>` von selbst,
  wenn man schlicht eine Serie weniger übergibt — inklusive Legendeneintrag
  des Charts; siehe `_adjust_ser_count` in `pptx/chart/xmlwriter.py`)
- die **statische Legenden-Textbox** daneben (kein Chart-Element!)
- die **Fußnote** und jeder Verweis darauf (`*`, `**`, `***`)
- der **Folientitel** („… (mit Benchmark)")

Am schwersten zu finden ist der statische Text: ein Chart mit falschen Zahlen
fällt beim Durchblättern auf, eine Fußnote mit *plausiblen, aber fremden*
Angaben nicht.

**3. Beim Wegnehmen ist der Standardwert die wichtigste Entscheidung.** Der
Schalter heißt `has_benchmark` und wird mit **`.get("has_benchmark", True)`**
gelesen, nicht mit `.get("has_benchmark")`. Nur ein ausdrückliches `False`
lässt Inhalte verschwinden. Der umgekehrte Standard hätte bei jedem Aufrufer,
der ein unvollständiges Dict baut, still Legendeneinträge und Fußnotenzeilen
aus Broschüren gelöscht — auch bei Strategien MIT Benchmark. Genau das fiel
beim ersten Entwurf auf, weil `test_legende_musterdepot.py` rot wurde: dessen
Fixture kennt den neuen Schlüssel nicht. Ein Test, der eine Design-
Entscheidung kippt, hat seinen Zweck erfüllt.

**Diagnose-Rezept (das, was hier funktioniert hat):** Broschüre bauen, dann
Serien-Namen und -Werte direkt aus der Chart-XML lesen sowie jeden Text-Frame
der Folie ausgeben — und **immer einen Kontrollfall mitbauen**, der das
Merkmal HAT (hier „Pro"). Ohne den weiß man nach der Korrektur nicht, ob man
nur den Fehler oder auch die Funktion entfernt hat.

Prüfstein: `tests/test_benchmark_charts.py` (Datenschicht + echtes Artefakt).

### 47. Ein Guard auf `== 0` greift bei Fließkomma nicht (BUG, NEU 12.08.2026) ⭐

`calc_sharpe_excess` endete mit dem üblichen Schutz gegen Division durch
null:

```python
sd = float(np.std(excess, ddof=1))
if sd == 0:
    return None
```

Der Schutz wirkt bei **lauter Nullen** — da liefert numpy sauber `0.0`. Bei
**konstanten Renditen ungleich null** aber nicht: `np.std([0.001]*10, ddof=1)`
ergibt `2.28e-19`, nicht `0.0`. Die Prüfung greift nicht, und aus
`mu / sd × √365` wird:

```
Sharpe Ratio = 83.584.821.264.662.160
```

Das ist dieselbe Fehlerfamilie wie die **−67,48** aus Transferwissen #41 und
wie #46: **Ein Fehlwert sieht aus wie ein Messwert.** Nur hätte man diesen
hier nicht einmal für plausibel halten können — was ihn paradoxerweise
ungefährlicher macht als die −67,48, die jemand für eine schlechte Kennzahl
hielt statt für einen Fehler.

**Regel:** Degenerierte Fließkomma-Zustände nie auf Gleichheit prüfen,
sondern gegen eine fachlich begründete Schwelle:

```python
if not np.isfinite(sd) or sd < 1e-12:
    return None
```

Die Schwelle braucht eine **fachliche** Begründung, keine mathematische:
1e-12 Tagesstreuung wären 0,0000000001 % Schwankung am Tag — das ist keine
Streuung mehr, sondern Rechenrauschen. Ein `np.isclose(sd, 0)` wäre hier
falsch, weil dessen Standardtoleranz (`atol=1e-8`) für Tagesrenditen viel zu
grob ist.

**Wie es gefunden wurde:** nicht durch Lesen, sondern weil ein neuer Test
(`tests/test_analytics.py`) grundsätzlich jede Funktion auch mit
degenerierter Eingabe aufruft und `None` erwartet. Dieselbe Runde brachte
zwei weitere Funde derselben Art: `fmt_date_de(float('nan'))` lieferte
wörtlich `"nan"` (eine leere Excel-Zelle kommt als NaN an, nicht als None),
und der Doctest von `calc_period_return` behauptete seit jeher einen falsch
gerechneten Wert (`-0.000198` statt `-0.000302`; der Code war richtig).

**Übertragbar:** Wer eine rechnende Funktion testet, ruft sie mit leerer
Liste, einem Element, konstanten Werten, NaN und Null auf — nicht nur mit
plausiblen Daten. Die drei Funde dieser Runde kamen ausnahmslos aus dieser
Kategorie, keiner aus den fachlich interessanten Fällen.

Prüfsteine: `tests/test_analytics.py`, `tests/test_formats.py`.

### 48. Eine abgeleitete Konfiguration erbt die blinden Flecken ihrer Quelle (NEU 12.08.2026) ⭐

Am 10.08.2026 wurden die Anlagekriterien aus den PPTX-Vorlagen in
`Mapping_Anlagekriterien.xlsx` überführt — sauber gemacht, mit Test. Die
Datei erfasste **14 von 19 Strategien**, und niemandem fiel das auf: Die
fünf fehlenden gehören zur Familie *Thema*, und deren Vorlage hat als einzige
keinen Kriterien-Kasten. Der Test schrieb das sogar ausdrücklich fest
(„Thema hat bewusst keinen").

**Der Denkfehler:** Die Excel hatte die Sicht ihrer Quelle übernommen. Sie
kannte 14 Strategien, weil **14 Vorlagen einen Kasten hatten** — nicht, weil
es nur 14 Strategien mit Anlagekriterien gäbe. Tatsächlich hat *jede*
Strategie welche; dass eine Vorlage sie nicht abdruckt, ist eine Eigenschaft
der **Darstellung**, keine der Sache. Drei der fünf standen die ganze Zeit
öffentlich auf der Bank-Webseite.

**Regel:** Wer eine Konfigurationsdatei aus einem Artefakt ableitet, fragt
sich: *Beschreibt die Quelle die Sache oder nur ihre Darstellung?* Und danach:
*Welche Fälle kennt die Quelle systematisch nicht?* Ein Vollständigkeits-Test
gegen die **fachliche** Grundgesamtheit (hier: `Mapping_Namen.xlsx` mit 19
Strategien) hätte die Lücke am ersten Tag gezeigt — der vorhandene Test prüfte
stattdessen gegen die eigene, abgeleitete Liste und war deshalb immer grün.

**Der zweite Teil ist PPTX-spezifisch und gefährlicher.** Ob ein Excel-Eintrag
in einer **Kundenbroschüre** landet, entscheidet nicht die Excel, sondern die
Vorlage: `pptx_export` ruft `fill_anlagekriterien_slide` für *jede* Familie
auf, und die Funktion steigt nur deshalb aus, weil
`finde_anlagekriterien_tabelle` in `Vorlage_Thema.pptx` nichts findet. Wer
dieser Vorlage eines Tages eine Tabelle gibt, **druckt die Werte damit
automatisch** — ohne eine Zeile Code zu ändern. Solche stillen Kopplungen
gehören getestet, nicht kommentiert: `tests/test_anlagekriterien.py` tastet
seit dem 12.08.2026 alle sechs Vorlagen ab und schlägt an, sobald sich das
ändert.

**Übertragbar:** Wenn Daten und Darstellung an verschiedenen Orten liegen,
ist die Frage „wird das gedruckt?" eine Eigenschaft der *Verbindung* — und
die hat niemand im Blick, solange sie zufällig das Richtige tut.

Prüfstein: `tests/test_anlagekriterien.py` (Schritte 4, 4b, 9b).

---

### 49. Die Ticks einer Achse hängen am Achsen-Minimum, nicht am Kalender (BUG, NEU 12.08.2026) ⭐

Gemeldet aus der Praxis: In der ETF-Broschüre laufen die Daten bis Juli 2026,
die Datumsachse zeigt aber **kein 2026**.

**Der Mechanismus.** PowerPoint setzt die Ticks einer `<c:dateAx>` beim
**Achsen-Minimum** an und zählt von dort in Schritten von
`majorUnit × majorTimeUnit` weiter. Kalendergrenzen spielen **keine Rolle** —
ein Jahresschritt heißt „alle zwölf Monate ab dem Minimum", nicht „jeden
1. Januar".

`chart_dynamik.datumsachse_an_daten` legte das Minimum auf den Monatsanfang des
ersten Datenpunkts — bewusst, gegen den Leerraum vor der Kurve. Damit war
aber das ganze Raster auf den **Anfangsmonat** der Reihe verankert:

| Reihe | Daten ab | Ticks | letzte Beschriftung |
|---|---|---|---|
| ETF | 30.11.2015 | Nov/15, Nov/16, … | **Nov/25** |
| ESG | 30.09.2020 | Sep/20, Sep/21, … | **Sep/25** |
| cVV klassisch | 31.12.2008 | Dez/08, Dez/09, … | **Dez/25** |

Nachgemessen an sieben gebauten Broschüren: **21 Datumsachsen, keine einzige
in Ordnung.** Der Fehler stand seit dem 07.07.2026 in jeder Broschüre und ist
niemandem aufgefallen — bis ein Kollege die Achse mit den Daten verglich.

**Die Lösung: den Anker hinten setzen, nicht vorn.** Zwei Kandidaten, es
gewinnt der mit dem kleineren Vorlauf (der leeren Achsenstrecke vor der Kurve):

1. der Monat des **letzten** Datenpunkts — dann trägt genau er die letzte
   Beschriftung;
2. die nächste **Kalendergrenze** davor (Januar beim Jahres-, Jan/Jul beim
   Halbjahres-, Jan/Apr/Jul/Okt beim Quartalsschritt).

Für die ETF-Reihe gewinnt (1) mit vier statt elf leeren Monaten, für die
cVV-Vergleichsreihe (Beginn 31.01.2009) gewinnt (2) mit glatten Januar-Ticks
bei null Vorlauf. Ein Kandidat, dessen letzter Tick **hinter** dem letzten
Datenpunkt läge, wird verworfen — ein Achsendatum in der Zukunft hat in einer
Kundenbroschüre nichts zu suchen. Kandidat (1) erfüllt das immer, es bleibt
also stets einer übrig.

**Zwei Nebenfunde, beide teurer als der gemeldete:**

**(a) Wer `majorTimeUnit` ändert, muss `majorUnit` mitziehen.** Der Code
stellte nur die Zeiteinheit um („bei langen Historien Jahres- statt
Monatsticks"). Die cVV-Vergleichsfolie trägt in der Vorlage aber
`majorUnit=12` mit `majorTimeUnit="months"` — gemeint waren zwölf **Monate**.
Nach dem Umstellen auf `years` las PowerPoint daraus zwölf **Jahre**: zwei
Beschriftungen auf siebzehneinhalb Jahren Historie. Die beiden Werte sind ein
Paar; einen davon allein zu setzen ist immer falsch.

**(b) `if el is not None` ist ein stiller Aussetzer, wenn eine von sechs
Vorlagen das Element nicht hat.** In `Vorlage_comdirect.pptx` fehlt
`<c:majorTimeUnit>` — dort lief die Anpassung schlicht **nie**. Kein Fehler,
keine Meldung, kein Unterschied im Log. Wer ein Vorlagen-Element ändert, muss
es **anlegen können**; und zwar an der vom Schema verlangten Stelle
(`CT_DateAx`: … `lblOffset`, `baseTimeUnit`, `majorUnit`, `majorTimeUnit`,
`minorUnit`, `minorTimeUnit`). Ein `SubElement()` hängt hinten an und landet
damit hinter `minorTimeUnit` — die Datei ist dann für PowerPoint unlesbar.

**(c) Dieselbe Falle steht senkrecht daneben.** Am selben Tag, nach dem Fix
der Datumsachse, kam der zweite Hinweis: Auf den cVV-Folien fehlt die
**100-%-Linie**. Ursache identisch — das Minimum wurde datenbasiert gesetzt
(0,9), die Schrittweite kam unverändert aus der Vorlage (0,2), also lagen die
Ticks bei 90/110/130 %. Die Bezugslinie, auf die sich *jede* Aussage der
Folie stützt, kam auf der Achse **nicht vor**. Bei ESG/ETF/comdirect stand
sie da — durch Zufall, weil deren Vorlagen 0,05 tragen.

Regel für Achsen mit einem fachlichen Bezugswert: **Die Schrittweite muss ein
Teiler des Bezugswerts sein, und das Minimum ein Vielfaches der Schrittweite.**
Dann liegt der Bezugswert zwangsläufig auf dem Raster. Gewählt wird die
feinste Stufe, die die Beschriftungsgrenze noch einhält — feiner heißt
zugleich: weniger Leerraum unter der Kurve.

Was dabei **nicht** geht: die Achse bei 100 % beginnen zu lassen. Jede
Strategie war zeitweise darunter (cVV dynamic 85,3 %, cVV ausgewogen 91,4 %);
ein Minimum von 100 % würde diese Drawdowns abschneiden — ein stiller
Datenverlust in einem Kundendokument (§10.9). Der Wunsch „soll dort starten"
wird stattdessen so weit erfüllt, wie es das Raster zulässt: bei cVV
konservativ rückt die Achse von 90 % auf **95 %**.

Nebenbei aufgefallen: Die alte Luft-Regel („klebt die Kurve oben, eine Stufe
drauflegen") wird mit grobem Raster teuer — eine Stufe sind dann **zwanzig**
leere Prozentpunkte. Luft ist deshalb ein fester kleiner Betrag (fünf
Prozentpunkte), nicht eine Rastereinheit.

**Übertragbar:** Wenn ein Renderer ein Raster aus einem Startwert ableitet,
entscheidet der Startwert über **alle** Positionen. Die Frage ist nie „ist der
Anfang richtig?", sondern „liegt das Raster dort, wo es gelesen werden soll?" —
und das Ende ist meist wichtiger als der Anfang. Und: **Eine Prüfregel, die
nur an den Rändern misst (min/max), sieht so ein Raster nie.** Der Prüfstein
rechnet deshalb die Tickfolge nach, statt Achsengrenzen zu vergleichen. Genau
daran hingen alle vier Funde dieses Tages.

Prüfstein: `tests/test_chartachsen.py`. Konfiguration der Schrittweiten:
`DATUMSACHSE_STUFEN` und `WERTACHSE_STUFEN` im CONFIG-Block von
`modules/chart_dynamik.py`.

---

### 50. Ein Versprechen im Kommentar ist kein Prüfstein (BUG, NEU 12.08.2026) ⭐

Gemeldet wurde eine Folie: In der **Offensiv**-Broschüre wird
„Quelle: Eigene Berechnung, Stand 20.07.2026" vom Disclaimer überdruckt.
Nachgemessen waren es **16** — jede Wertentwicklungs-Folie in allen sechs
Vorlagen, auf den Emu identisch positioniert:

```
Quelle    23,30–28,10 × 13,89–14,19 cm
Fußnote   12,50–28,10 × 11,16–16,20 cm     ← die Quelle liegt DARIN
```

Die Quelle lag also seit jeher im Disclaimer-Feld. Sichtbar wurde das erst,
als der Text lang genug wurde — und dafür sorgte der Code.

**Der Mechanismus.** Der Disclaimer ist in der Vorlage **hart umbrochen**:
Die Sätze sind von Hand auf Absätze verteilt, die bei 6 pt genau die
Boxbreite füllen (längste Vorlagenzeile: 149 Zeichen). Diese Breite steht
**nirgends in der Datei** — sie entsteht erst beim Rendern.
`WE_DISCLAIMER_REPLACEMENTS` ersetzte einen dieser Absätze durch **189
Zeichen**. Der bricht um, und alles darunter rutscht eine Zeile tiefer:
Unterkante 14,21 → 14,47 cm, mitten durch die Quellenzeile.

Das Bittere daran steht direkt über der Konstanten, seit Juli 2026:

> „Die Ersetzung arbeitet daher absatzweise über eindeutige Präfixe; die
> neuen Zeilen sind **auf ähnliche Länge kalibriert, damit das Layout
> hält**."

Der Kommentar hatte recht — er beschrieb genau die Bedingung, auf die es
ankam. Nur hat sie nie jemand **gemessen**. Ein Wert von 189 gegen ein
Limit von 149 ist in einer Sekunde geprüft; er stand über einen Monat da.

**Übertragbar — drei Sätze:**

1. **Wer Text in eine Box mit fester Geometrie schreibt, muss die Geometrie
   mitdenken.** Hart umbrochener Vorlagentext hat eine Zeilenbreite, die
   nirgends deklariert ist. Sie gehört als Konstante in den Code
   (`WE_FUSSNOTE_ZEILE_MAX`) — sonst kann niemand dagegen prüfen.
2. **Eine Bedingung, die ein Kommentar nennt, ist ein Testfall.** Wenn ein
   Kommentar sagt „das muss kurz genug bleiben", „das muss vor X laufen",
   „das darf nicht null sein" — dann ist das die Zusage, und eine Zusage
   ohne Messung ist eine Hoffnung. Verwandt mit #47: dort war der Guard da,
   aber falsch; hier war die Regel da, aber ungeprüft.
3. **Ein Fehler, der erst durch Zusammenwirken sichtbar wird, hat mehr als
   eine Ursache — und man behebt beide.** Die Vorlagenposition war schon
   immer riskant, der Ersatztext machte sie zum Fehler. Nur den Text zu
   kürzen hätte 0,28 cm Luft gelassen; nur die Box zu verschieben hätte das
   stille Umbrechen stehen gelassen. Behoben sind beide, und die Position
   ist bewusst so gewählt, dass sie **auch mit dem alten Text** hält.

**Und die Methodenlehre aus #49 gilt weiter:** Gemeldet war eine Instanz,
gemessen wurden alle. Dass die Zahl wieder bei „alle" landete (16 von 16,
wie vorher 21 von 21 Achsen), ist kein Zufall: Was in einer Vorlage steht,
steht meist in allen sechs — Vorlagen werden kopiert, nicht neu gebaut.

**Gemessen wurde am Rendering, nicht im XML.** python-pptx kennt keine
Zeilenumbrüche; die Kollision ist im XML unsichtbar (beide Shapes haben
gültige, sich überlappende Rechtecke — das allein wäre noch kein Fehler).
PowerPoint hat die Folien per COM als PNG ausgegeben, gemessen wurde
zeilenweise über die dunklen Pixelreihen. Daraus stammen die Kennwerte im
Prüfstein: erste Zeile 0,06 cm unter der Boxkante, Zeilenabstand 0,2533 cm
bei 6 pt. Das ist die Fortsetzung von #16/#28 mit anderen Mitteln —
LibreOffice reicht nicht, aber ein PNG aus echtem PowerPoint schon, und das
kann ein Test selbst erzeugen.

Prüfstein: `tests/test_quelle_position.py`. Stellschrauben:
`WE_QUELLE_TOP_CM` und `WE_FUSSNOTE_ZEILE_MAX` in `modules/pptx_slides.py`.

### 51. „Es gibt Daten" ist nicht „der Zeitraum ist abgedeckt" (BUG, NEU 12.08.2026) ⭐

Gemeldet hat Philip einen Balken: Im Säulen-Chart der **Pro**-Broschüre
(„PERFORMANCE P.A. (NACH KOSTEN) IM BENCHMARKVERGLEICH") steht ein Jahr
**2023**. Die Strategie läuft seit dem **01.09.2023**. Der Balken zeigte
122 Tage — **+3,23 %** gegen **+5,11 %** Benchmark — und stand als
Jahreswert neben 2024 (+27,65 %) und 2025 (+7,58 %).

Der Code sah so aus:

```python
for year in target_years:
    sub = df[df.index.year == year]
    if sub.empty:            # ← die einzige Prüfung
        continue
```

Das Fenster war richtig gewählt (die letzten fünf **abgeschlossenen**
Kalenderjahre, 2021–2025); geprüft wurde danach nur noch, ob im Jahr
**irgendwelche** Daten liegen. Ob sie das Jahr **abdecken**, hat niemand
gefragt. Vier Monate genügten für einen vollwertigen Jahresbalken.

**Übertragbar — drei Sätze:**

1. **Ein Filter auf „leer" ist kein Filter auf „vollständig".** `empty`,
   `len() > 0`, `notna().any()` beantworten die Frage „habe ich etwas?" —
   nicht „habe ich genug?". Wo ein Aggregat für einen Zeitraum steht
   (Jahresrendite, Monatsmittel, Quartalsumsatz), gehört die Abdeckung des
   Zeitraums geprüft, nicht seine Nichtleere. Verwandt mit #43: dort waren
   die ersten Datenpunkte nur Indexbasis, hier ist das erste Jahr nur ein
   Rumpf — beide Male trägt der **Rand** der Zeitreihe die Falle.
2. **Prüfe beide Ränder, und prüfe sie am Ausschnitt.** Am Jahresende gab es
   die Regel längst („mindestens bis 28.12."), am Jahresanfang fehlte sie.
   Wer sie ergänzt, misst sie an den Zeilen **dieses Jahres**
   (`sub.index.min()`), nicht am Beginn der Gesamtreihe — dann greift
   dieselbe Prüfung auch bei einem Loch mitten in der Historie. Und sie
   braucht an beiden Rändern **dieselbe Toleranz**: Feiertage verschieben
   den ersten Kurs genauso wie den letzten (hier 3 Tage, `JAHR_RAND_TOLERANZ_TAGE`).
3. **Eine Regel, die eine Beschriftung verspricht, ist eine Sachaussage.**
   Über dem Chart steht „p.a.". Damit ist jeder Balken darunter eine
   Jahresangabe — auch der, der keine ist. Das ist kein Schönheitsfehler,
   sondern §10.9.

**Und wieder: gemeldet war einer, betroffen waren alle, die es sein
konnten.** Nachgemessen an den 19 Strategien waren es **7** — jede, deren
Auflage in das rollierende Fenster fällt (Pro, Pro Dividende, Comdirect ×3,
SCHWEIZ ×2). Die zwölf älteren waren sauber, nicht weil der Code sie
richtig behandelte, sondern weil ihr Rumpfjahr längst aus dem Fenster
gerutscht ist. Ein Fehler, der von selbst verschwindet, ist trotzdem einer —
er kommt mit jeder neuen Strategie zurück.

**Was der Fix aufdeckt: den Fall, den es vorher nicht geben konnte.** Fällt
das Rumpfjahr weg, kann die Jahresliste **leer** sein — bei einer Strategie,
die noch kein Kalenderjahr hinter sich hat. Die Folie ließ das Chart dann
unangetastet, und darin stehen die **Beispieldaten der Vorlage** (2024/2025
mit Fantasiewerten). Das wäre schlimmer als der Rumpfbalken. Deshalb gilt:
**Wer einen Filter verschärft, prüft, was der leere Rest auslöst.** Hier
eine Meldung über `LAST_BUILD_ERRORS` — den einzigen Warnkanal, der beim
Berater ankommt. (Nebenbefund derselben Runde: `EINZELTITEL_WARNUNGEN` in
`pptx_slides` behauptete im Kommentar, ausgelesen zu werden — im ganzen Repo
gibt es keine Leseposition. Wieder #50: eine Zusage im Kommentar.)

**Bewusst NICHT angeglichen: das Tool.** Im Streamlit-Tool bleiben
angebrochene Jahre im Balken-Chart stehen — Auflagejahr wie laufendes Jahr.
Das ist keine Inkonsistenz aus Versehen, sondern eine Entscheidung (Philip,
12.08.2026): Dort wählt der Berater den Zeitraum selbst und sieht ihn neben
dem Chart; in der Broschüre steht der Balken allein und ohne Kontext. Die
Konsistenz-Doktrin gilt für die **Mathematik** (eine Formel, ein Ort), nicht
zwingend für den **Ausschnitt**. Wo sie bewusst gebrochen wird, gehört ein
Kommentar an die Stelle — sonst gleicht sie jemand in sechs Monaten an.

Prüfstein: `tests/test_kalenderjahre.py`. Stellschrauben:
`_ist_volles_jahr` und `JAHR_RAND_TOLERANZ_TAGE` in `modules/analytics.py`.

---

### 52. Eine Differenz stellt strengere Fragen als ein Einzelwert (NEU 14.08.2026) ⭐

Die Monatsrenditen-Heatmap ist #51 eine Ebene feiner: Wo dort ein
Rumpf**jahr** als Jahresbalken stand, stünde hier ein Rumpf**monat** als
Monatsrendite. Gemessen am 14.08.2026 über alle 19 Strategien sind das **26
angebrochene Monate** — jeder Auflagemonat und, bei **jeder** Strategie, der
laufende. Die Antwort ist dieselbe: `_ist_voller_monat` als Zwilling zu
`_ist_volles_jahr`, beide Ränder geprüft.

Neu und übertragbar ist etwas anderes — **derselbe Fehlwert wiegt in einer
Differenz schwerer als in einem Einzelwert.**

Ein angebrochener Monat ist für sich eine **wahre** Aussage: „In den zwanzig
Tagen seit Auflage waren es +1,6 %." Er darf mit Kennzeichen stehenbleiben.
Dieselbe Zahl in einer Differenz ist eine **falsche** Aussage: Zwanzig Tage
der einen Strategie gegen einunddreißig der anderen ergeben keine
Monatsdifferenz, sondern gar nichts. Deshalb behandelt derselbe Code
denselben Monat unterschiedlich, je nachdem, was mit ihm geschieht:

| | absolute Matrix | Differenz-Matrix |
|---|---|---|
| angebrochener Monat | steht mit `*` | **entfällt** |
| Regel | „ist wahr für seine Tage" | „beide Seiten müssen voll sein" |

Der angenehme Nebeneffekt: Beim Vergleich zweier Strategien fällt der
Zeitraum, in dem die jüngere noch nicht lief, **von selbst** weg — es
braucht keinen eigenen Sonderfall für ungleich lange Historien.

**Die zweite Lehre betrifft die Verkettung.** Eine Differenz kann
arithmetisch (`r_a − r_b`) oder geometrisch (`(1+r_a)/(1+r_b) − 1` )
gerechnet werden. Steht neben den Monaten eine **Jahresspalte**, ist nur die
geometrische Variante in sich stimmig:

```
Strategie  +10 %  +10 %   ->  +21,00 %
Benchmark   +5 %   +5 %   ->  +10,25 %      Jahr: 1,21/1,1025 - 1 = +9,75 %

geometrisch   1,10/1,05 - 1 = +4,76 % je Monat, 1,0476² - 1 = +9,75 %   stimmt
arithmetisch  10 - 5        = +5,00 PP je Monat, Summe      = +10,00 PP  passt nicht
```

Verallgemeinert: **Wer eine Zeile und ihre Summenspalte nebeneinanderstellt,
schuldet dem Leser, dass die Zeile die Summe ergibt.** Sonst steht auf einem
Bildschirm eine Zahl, die der Zahl daneben widerspricht — und der Leser hat
recht, wenn er beiden misstraut. Bei der absoluten Matrix geht das nur auf,
**weil** angebrochene Monate gezeigt werden; bei der Differenz nur, weil die
Jahresspalte aus den gültigen Monaten verkettet und nicht direkt gerechnet
wird.

**Dritter Punkt, unabhängig von der Fachlichkeit: eine Farbskala hat genau
eine Textfarbe.** `go.Heatmap` kann die Schriftfarbe nicht je Zelle setzen.
Wer Zahlen in die Zellen schreibt — und das muss man, weil Farbe die Aussage
nie allein tragen darf —, muss die Skala so wählen, dass **eine** Textfarbe
über die ganze Spannweite liest. Nachgerechnet statt geschätzt: elf
Stützstellen, schlechtester Kontrast 5,37:1, WCAG AA verlangt 4,5:1. Eine
Skala mit kräftigen dunklen Enden hätte das nicht geschafft.

**Vierter Satz, nachgetragen am 14.08.2026 nach der Sichtprüfung: Eine
Farbskala ist erst fertig, wenn man weiß, wo die Daten LIEGEN — nicht, wo
sie enden.**

Die Grenzen kamen aus dem 95. Perzentil der Beträge (5,28 % absolut). Das
ist eine saubere Zahl und beantwortet eine sinnvolle Frage: *Was schneide
ich ab?* Nur war es die falsche Frage. Philips Rückmeldung lautete „wirkt zu
blass", und die Ursache saß in der Mitte der Verteilung: Der typische Monat
bringt rund **1,2 %**. Bei einer Grenze von 5 % sitzt er damit bei 24 %
Sättigung — die ganze Matrix ist blass, obwohl kein einziger Wert
abgeschnitten wird.

| | Grenze aus P95 (±5 %) | Grenze aus dem Median (±3 %) |
|---|---:|---:|
| typischer Monat (1,2 %) | 24 % Sättigung | 40 % |
| guter Monat (2,0 %) | 40 % | 67 % |
| starker Monat (3,0 %) | 60 % | 100 % |

**Ein Perzentil am Rand sagt, was nicht verloren geht; über die Wirkung
entscheidet die Mitte.** Wer eine Skala kalibriert, braucht beide Enden der
Frage: Wo liegt die Masse (bestimmt die Grenze), und was darf aussättigen
(bestimmt, ob man damit leben kann). Aussättigen ist erlaubt, solange der
Betrachter es SIEHT — deshalb tragen die Enden der Farblegende „≤" und „≥".
Ohne diese beiden Zeichen sähe der dunkelste Ton wie der Höchstwert aus.

Und die Gegenrechnung gehört dazu: Kräftigere Farben allein hätten das
Problem nicht gelöst (die vielen kleinen Monate blieben blass) und hätten
den Kontrast gekostet — Signalfarben liegen bei 3,20:1 statt der
geforderten 4,5:1.

Prüfsteine: `tests/test_monatsrenditen.py`, `tests/test_risiko.py`.
Stellschrauben: `_ist_voller_monat`, `MONAT_RAND_TOLERANZ_TAGE`,
`ROLL_FENSTER_TAGE` in `modules/analytics.py`; `HEATMAP_*` in
`modules/shared.py`.

---

### 53. Ein Vergleichsfenster darf den Vergleichswert nicht enthalten (NEU 14.08.2026) ⭐

Die Bandbreiten-Ansicht (Bloomberg-Vorbild „SEAG") stellt dem laufenden Jahr
das Hoch, das Mittel und das Tief der Vorjahre gegenüber — je Kalendermonat.
Der Fehler, der dabei fast entstanden wäre, ist keiner der Mathematik, sondern
der Mengendefinition: **Das laufende Jahr gehört nicht in sein eigenes Band.**

Nimmt man bei Datenstand 07/2026 die „letzten fünf Jahre" als 2022–2026 statt
2021–2025, dann zieht der laufende Wert sein eigenes Extrem mit. Ein
Rekordmonat läge dann **per Definition nie über dem Hoch** — er *wäre* das
Hoch. Die Ansicht könnte genau die Aussage nicht mehr treffen, für die sie
gebaut wurde.

**Übertragbar:** Wo ein Wert gegen eine Referenzmenge gelesen wird, muss er
außerhalb dieser Menge liegen. Das klingt selbstverständlich und ist es
solange, bis „die letzten fünf Jahre" als naheliegender Ausdruck in den Code
wandert. Verwandte Fälle: ein gleitender Durchschnitt, der den aktuellen Punkt
enthält; eine Perzentil-Einordnung gegen eine Verteilung, in der der
einzuordnende Wert selbst steckt; ein Ausreißertest gegen eine
Standardabweichung, die der Ausreißer mitgeprägt hat.

**Zweiter Satz, aus derselben Runde: Eine zweite Ansicht ist billig, wenn die
erste ihre Zeilen von ihrer Zeichenmaschine trennt.**

Die Jahr-für-Jahr-Matrix hatte in Runde 2 einen generischen Zeilen-Helfer
bekommen — nicht aus Weitsicht, sondern weil die Ø-Zeile sonst dieselbe
Schleife ein zweites Mal gebraucht hätte. Genau diese Trennung machte die
Bloomberg-Ansicht zu **anderen Zeilen an derselben Maschine**: dieselbe
Colorbar, dieselbe Jahresspalte, dieselbe Tabelle, dieselbe Kachelgröße. Ein
zweites Chart-Gerüst hätte all das dupliziert — und wäre beim nächsten Umbau
auseinandergelaufen, wie die Honorar-Mathematik in Backlog B.

**Dritter Satz, teuer bezahlt: Ein Auswahlfeld ignoriert einen ungültigen Wert
stillschweigend.**

Die AppTest-Fälle setzten `p_sel1="Comdirect 100"` — das ist der
**CSV-Portfolioname**. Das Auswahlfeld führt aber **Anzeigenamen**
(`Comdirect_100`). Streamlit wirft dabei nichts: Es bleibt einfach beim
Standard. Sechs Testfälle aus zwei Runden liefen deshalb gegen
*cVV konservativ* und bewiesen nichts über SCHWEIZ, comdirect oder Pro
Dividende — grün, aber blind.

Der Fund ist dieselbe Klasse wie das fehlende `majorTimeUnit` (#49) und der
nicht greifende Disclaimer-Anker (§15 H): **eine Zuweisung, die ins Leere
läuft, ohne Fehler und ohne Meldung.** Die Lehre ist nicht „Namen sorgfältiger
abschreiben", sondern: *Wer einen Zustand setzt, prüft, dass er angekommen
ist.* Der AppTest-Helfer vergleicht seitdem nach jedem Lauf den Wert des
Auswahlfelds mit dem, was er setzen wollte.

Prüfstein: `tests/test_monatsrenditen.py`, Schritte 7–9. Stellschrauben:
`BAND_MIN_JAHRE` in `modules/analytics.py`, `ZEILE_HOEHE_MIN`/`MAX` in
`modules/risiko_ansicht.py`.

---

### 54. Ein Test auf das Diagramm-Objekt ist kein Test auf das Diagramm (BUG, NEU 14.08.2026) ⭐

Die Bandbreiten-Ansicht war am Bildschirm unbrauchbar: Vier Zeilen zu einem
Strich am unteren Rand zusammengefallen, die Zahlen übereinander gedruckt
(`+0,5+0,7`), darüber eine Bildschirmhöhe Leerraum. **Alle Prüfsteine waren
grün.**

Sie lasen `z`, `text` und `y` aus dem Plotly-Figur-Objekt — also die **Daten**
und behaupteten damit, die Grafik sei in Ordnung. Die **Geometrie** entsteht
aber erst beim Rendern, und zwar aus Voreinstellungen, die niemand gesetzt
hatte.

**Zwei Ursachen, beide dieselbe Art Fahrlässigkeit:**

1. **Der Achsentyp war nicht gesetzt.** `fig.layout.yaxis.type` war `None`,
   Plotly entscheidet dann anhand der Werte. Die y-Beschriftungen waren
   `["17J-Hoch", "17J-Mittel", "17J-Tief", "2026"]` — drei echte Strings und
   ein **zahlartiger**. Sobald `"2026"` als Zahl gelesen wird, spannt die
   Achse bis 2026, und vier Kategorien schrumpfen auf einen Streifen.

2. **Annotationen wurden über Beschriftungstexte platziert** (`y="2026"`)
   statt über Koordinaten (`y=3`). Das verlangt vom Renderer eine **zweite
   Namensauflösung** gegen die Kategorienliste — und die kann scheitern, ohne
   dass jemand es merkt. Dieselbe Klasse wie das nicht greifende
   `majorTimeUnit` (#49), der ins Leere laufende Disclaimer-Anker (§15 H) und
   der stillschweigend ignorierte Auswahlfeld-Wert (#53).

**Nebenbefund, den erst die Reparatur zutage brachte:** Bei `go.Heatmap`
gehört `z[0]` zu `y[0]` und wird **unten** gezeichnet. Die Zeilenlisten waren
in Leserichtung gebaut (jüngstes Jahr zuerst) und wurden ungedreht übergeben —
die Jahr-für-Jahr-Matrix zeigte also **2026 unten und die Ø-Zeile oben**,
genau verkehrt herum. Das lief seit dem ersten Tag mit und ist niemandem
aufgefallen, weil 2009–2026 gleichmäßig gestaffelt sind und eine umgedrehte
Leiter aus der Ferne wie eine richtige aussieht.

**Übertragbar — drei Sätze:**

1. **Wer eine Achse nicht typisiert, überlässt die Darstellung einer
   Heuristik.** Die rät meistens richtig — und genau deshalb fällt der Fall,
   in dem sie falsch rät, erst spät auf. `type="category"` kostet eine Zeile.
2. **Wer ein Element über einen Beschriftungstext positioniert, hat eine
   Namensauflösung eingebaut, die scheitern kann.** Koordinaten können das
   nicht.
3. **Ein Test, der die Eingabe einer Bibliothek prüft, prüft nicht ihr
   Ergebnis.** Für Diagramme heißt das: Nicht nur `data` lesen, sondern
   `layout` — Achsentyp, Kategorienreihenfolge, Koordinatentypen der
   Annotationen. Und wo möglich das Ergebnis **ansehen**: `fig.write_html()`
   braucht kein Kaleido und liefert in einer Sekunde eine Datei, die man im
   Browser öffnen kann, bevor die Anwendung überhaupt startet.

Prüfstein: `tests/test_monatsrenditen.py`, **Schritt 8** — er prüft
ausschließlich das Layout. Nachgestellt gegen den alten Stand meldet er
sofort vier Abweichungen.

---

### 55. Was inline in der Oberfläche steht, ist für keinen Prüfstein erreichbar (BUG, NEU 14.08.2026) ⭐

Philip meldet: In der Monatsrenditen-Heatmap fehlen bei der Schnellwahl
„3 Jahre" die Kacheln Januar bis Juni 2023.

Die Ursache war eine einzige Zeile. Der Zuschnitt rechnete
`Datenstand − 3 Jahre`; bei einem Datenstand vom **21.07.2026** schnitt er am
**21.07.2023**. Jan–Jun 2023 fielen aus der Matrix, Juli 2023 blieb als
Elf-Tage-Rumpfmonat stehen. **Sechs leere Kacheln, und zwar bei jeder
Schnellwahl** — weil der Schnitt immer in demselben Monat landet wie der
Datenstand.

**Warum das ein Fehler war und nicht nur unschön:** Eine leere Kachel bedeutet
in dieser Matrix bereits etwas — *„die Strategie lief da noch nicht"*, so wie
bei comdirect vor März 2024. Hier bedeutete dieselbe Kachel *„es gibt Daten,
der Zeitraum blendet sie aus"*. Zwei Bedeutungen, ein Aussehen; dieselbe
Klasse wie ein Fehlwert, der aussieht wie ein Messwert (#46).

Die Reparatur ist trivial: auf den Jahresanfang runden. Gleiche Zeilenzahl
(nachgemessen für 1/3/5/10 Jahre), null Lücken, und das älteste Jahr zählt
danach als vollständig in die Ø-Zeile.

**Der eigentliche Befund ist ein anderer.** Auf dieser Heatmap lagen zu dem
Zeitpunkt **zehn Testschritte** — Grenzfälle, Verkettungszusagen, die
Invariante der Bandbreite, sogar die Figur-Geometrie nach #54. Und **keiner
davon konnte diese Zeile anfassen**, weil sie inline mitten im Renderpfad von
`streamlit_app.py` stand:

```python
_heat_von = (pd.Timestamp(maxd) - pd.DateOffset(years=jahre)).date()
```

Es gab nichts zu importieren, nichts aufzurufen, nichts zu vergleichen. Der
AppTest hätte es theoretisch über die gerenderte Caption sehen können — aber
nur, wenn jemand vorher auf die Idee gekommen wäre, genau danach zu suchen.

**Übertragbar:** *Wer eine Entscheidung trifft, die man prüfen können muss,
gibt ihr einen Namen.* Eine Berechnung im Renderpfad hat keine
Angriffsfläche; dieselbe Berechnung als Funktion mit Rückgabewert hat eine.
Nach dem Herausziehen prüft ein Testschritt sie gegen sieben von Hand
gerechnete Fälle und misst zusätzlich die Wirkung an allen 19 Strategien —
gegen die alte Formel meldet er neun Abweichungen und die sechs Lücken je
Strategie.

Das ist die Schwester von **#54**: Dort war die Lücke die fehlende
**Layout**-Prüfung, hier die fehlende **Erreichbarkeit**. Beide Male war die
Ursache nicht mangelnde Sorgfalt beim Testen, sondern dass es nichts gab,
woran ein Test hätte ansetzen können.

**Nebenbei mitgenommen:** Weil „3 Jahre" in der Heatmap jetzt 01/2023–07/2026
umfasst und damit ein halbes Jahr mehr als der Kennzahlen-Block darüber, sagt
die Caption es dazu. Zwei verschiedene Spannen unkommentiert untereinander
wären wieder eine Zahl, die der Zahl daneben widerspricht (vgl. #52).

---

### #56 — Die Begründung kann falsch sein, während das Ergebnis stimmt

**Gefunden im Audit vom 14.08.2026.** Bei `ROLL_FENSTER_TAGE` stand als
Begründung für √365: *„Wochenenden und Feiertage stehen mit Rendite 0 darin
(rund 29 % aller Zeilen)."* Nachgemessen an den echten Daten trifft das auf
**eine von 19** Strategien zu. Der Anteil exakter Nullen in `ret_port` hat
den Median **0,00 %**.

Was an den Wochenenden wirklich steht, ließ sich messen:

| Prüfung | Ergebnis |
|---|---|
| Comdirect 30 / 70 / 100, gleiche Historie | 1,925 % / 0,543 % / 0,000 % p.a. |
| Anleihenquote ihrer Benchmark | 85 % / 50 % / 15 % |
| Korrelation Wochenendanteil gegen Volatilität | **−0,66** |
| Wochenendsatz jemals negativ? | **nie** — auch 2015–2022 nicht, als `rf` < 0 war |

Es ist die **Kuponabgrenzung des Anleihenteils**. Deshalb bleibt sie positiv,
wenn der Leitzins es nicht ist, und deshalb ordnet sie sich nach der
Anleihenquote.

**Und jetzt der Punkt:** Die Reihe ist damit eine *echte* Kalendertagreihe —
also ist √365 **richtig**, nicht bloß eine hingenommene Ungenauigkeit, als
die der Text sie auswies. Die Konvention war die ganze Zeit korrekt. Nur der
Grund war es nicht. Von den fünf Fundstellen der „29 %"-Behauptung im Repo
waren drei **richtig**: Sie reden von `ret_bm`, und der Index steht am
Wochenende tatsächlich still (28,6–30,6 % Nullen, an 100 % der Wochenenden).
Ein pauschales „Suchen und Ersetzen" hätte drei korrekte Aussagen kaputt
gemacht.

**Übertragbar:** *Prüfe die Voraussetzung getrennt vom Ergebnis.* Ein
richtiges Ergebnis beweist die Begründung nicht — und eine falsche Begründung
widerlegt das Ergebnis nicht. Beim Audit heißt das: erst messen, was
tatsächlich in den Daten steht, dann entscheiden, ob die Rechnung dazu passt.

**Daraus folgt der Prüfstein.** Ein Test auf den *Text* eines Docstrings wäre
sinnlos. Schritt 6 in `test_risiko.py` prüft stattdessen die **Eigenschaft**,
von der die Konvention abhängt: kalendertäglich und lückenlos. Käme eine
Lieferung mit nur noch Handelstagen, wären 365 Zeilen rund **1,40 Jahre**
und √365 deutlich zu hoch — dann schlägt er an. Nachgewiesen an einer
simulierten Handelstag-Lieferung (Werktaganteil 1,000 statt 0,714).

---

### #58 — Eine Toleranz, die an den Messwert angepasst ist, prüft nichts mehr

**Gefunden im Audit vom 14.08.2026, Befund B3.** In
`test_kosten_mathematik.py` stand:

```python
# Ein Jahr ohne Marktbewegung muss exakt das Honorar kosten.
verlust = 100.0 - float(idx[-1])
if not (1.50 < verlust < 1.56):
    print(f"    FEHLER — 365 Nulltage kosten {verlust:.4f} statt ~1,53")
```

Der Kommentar sagt **„exakt"**. Die Prüfung lässt **drei Basispunkte** Spiel.
Und die Fehlermeldung nennt als Sollwert **„~1,53"** — nicht 1,55.

Damit ist die Geschichte vollständig erzählt: Jemand hat den Wert gemessen,
der herauskam, das Band darum gelegt und den erwarteten Wert aus der Messung
abgeschrieben. Genau in diesem Spielraum saß der Fehler — die Formel zog
1,5264 % statt 1,5500 % ab. Der Test konnte ihn nie finden, weil er ihn
umschloss.

**Übertragbar:** *Der Sollwert einer Prüfung kommt aus der Zusage, nicht aus
dem Ergebnis.* Wo eine Zusage „exakt" lautet, gehört dort auch eine exakte
Prüfung hin (`abs(ist - soll) > 1e-12`). Eine Toleranz braucht eine
Begründung aus der Sache — Fließkomma-Rundung, Datenungenauigkeit — und
niemals „so kam es halt heraus". Wer eine Toleranz setzt, muss sagen können,
welchen Fehler sie noch fangen soll.

**Konkret geändert:** Der Schritt verlangt jetzt für **alle sechs** im
Bestand vorkommenden Sätze, dass 365 Nulltage exakt den Satz kosten
(0,85 / 1,20 / 1,25 / 1,40 / 1,55 / 1,60 %), auf 1e−12 genau.

Verwandt mit **#56**: Dort war die *Begründung* falsch und das Ergebnis
richtig, hier war die *Prüfung* zu weich und das Ergebnis falsch. Beide Male
hätte der Blick auf die Zusage statt auf die Zahl es gezeigt.

---

### #57 — Ein stiller Rückfall ist dort am gefährlichsten, wo er plausibel aussieht

**Gefunden im Audit vom 14.08.2026, Befund B6.** In `shared.py` stand:

```python
try:
    fd = float(mapping.loc[mapping["Inhaber"] == pn,
                           "Honorarsatz Standard"].values[0])
except Exception:
    fd = 0.0
```

Fehlt die Mapping-Zeile, rechnet die Strategie mit **0 % Honorar**. Die
Zahlen sind dann brutto — und überall als „nach Kosten" beschriftet.

**Warum das niemandem auffiel:** Der Satz steht in einem *Eingabefeld* der
Seitenleiste. Dort sieht „0,00" aus wie eine Angabe, nicht wie ein Ausfall.
Ein Fehlwert, der sich als Messwert tarnt — dieselbe Klasse wie #46, nur eine
Ebene tiefer: Hier tarnt sich der Ausfall nicht als Null, sondern als
*Eingabe*.

**Die Größenordnung war der eigentliche Schreck.** Gemessen an „Muster
ausgewogen cVV":

| | ausgewiesene Rendite p.a. |
|---|---|
| ohne Honorar (der stille Ausfall) | **6,90 %** |
| mit 1,55 % Honorar (richtig) | **5,27 %** |
| zu hoch um | **1,63 Prozentpunkte** |

Nicht Basispunkte — Prozentpunkte, und in der schmeichelnden Richtung.

**Behoben, ohne die Schutzwirkung aufzugeben:** Der Rückfall auf 0,0 bleibt,
damit die App weiterläuft und der Berater den Satz überschreiben kann. Aber
die Zeitreihe merkt sich in `attrs["honorar_gefunden"]`, dass er geraten ist,
und die Oberfläche macht daraus eine Fehlermeldung mit Strategienamen. Ein
**gefundener** Satz von 0,0 löst bewusst keine Meldung aus — das ist etwas
anderes als ein fehlender.

**Übertragbar:** *Ein Vorgabewert nach einem Fehlschlag muss sich vom selben
Wert als echte Angabe unterscheiden lassen.* Sonst ist der Schutz vor dem
Absturz zugleich die Tarnung des Fehlers. Wo ein Rückfall unvermeidlich ist,
gehört neben den Wert ein Vermerk, dass er geraten wurde.

**Und die Ironie:** `test_honorarsatz.py` kannte das Problem seit dem
11.08.2026 — der Docstring zitierte das `except` wörtlich. Der Test prüfte
aber nur, dass *heute* nichts fehlt, nicht dass ein Fehlen *auffällt*.
Schritt 4 ist jetzt die Gegenprobe dazu. Verwandt mit **#55**: Die Prüfung
lag auch hier nicht am Ort der Entscheidung, deshalb liegt
`strategien_ohne_honorarsatz` ausdrücklich **nicht** inline im Renderpfad.

### #59 — Ein Aggregat muss sagen, was es nicht enthält

**Gefunden am 17.08.2026**, beim Umsetzen eines Beraterwunsches (Fälligkeiten
der einzelnen Anleihen). Der Wunsch war klein, der Nebenbefund nicht.

Der Anleihen-Block der Portfolioanalyse zeigt oben eine Kachel „Gewicht
Anleihen" und darunter ein Balkenchart „Fälligkeitsstruktur". Beide sprachen
von **verschiedenen Mengen**: Die Kachel zählte alle Renten-Positionen, der
Chart nur die mit einem Fälligkeitsdatum. Renten-ETFs und Rentenfonds haben
keines — sie fielen wortlos heraus.

Gemessen über alle 19 Strategien:

| Strategie | Kachel | Summe der Balken | Differenz |
|---|---:|---:|---:|
| ETF Muster 40/60 ausgew. | 46,54 % | 0,00 % | **46,54 %** (gar kein Chart) |
| Muster SCHWEIZ Substanz | 30,89 % | 15,35 % | **15,54 %** |
| Muster SCHWEIZ Aktien | 11,56 % | 0,00 % | 11,56 % (gar kein Chart) |
| ETF Muster 100/100 offensiv | 11,38 % | 0,00 % | 11,38 % (gar kein Chart) |
| ESG Muster defensiv | 61,14 % | 57,83 % | 3,31 % |
| übrige 9 mit Anleihen | | | 0,00 % |

Bei drei Strategien erschien **überhaupt kein Chart** — an dieser Stelle stand
eine Leerstelle, und eine Leerstelle sagt nichts. Wer sie sah, konnte „diese
Strategie hat keine Anleihen" verstehen, obwohl 46,54 % des Portfolios in
Renten steckten.

**Die Klasse ist bekannt, der Ort war neu.** #46 und #57 handeln davon, dass
ein *Fehlwert* wie ein *Messwert* aussieht. Hier sieht ein **unvollständiges
Aggregat** wie ein vollständiges aus: Der Chart lügt nicht über die Balken,
die er zeigt — er verschweigt, dass es weitere gibt.

**Übertragbar:** *Wo ein Teilaggregat neben seiner Gesamtgröße steht, gehört
die Differenz benannt.* Und: Ein Filter, der Zeilen ohne einen bestimmten Wert
verwirft (`notna()`), erzeugt fast immer so ein Teilaggregat — die Frage
„wie viel habe ich gerade weggelassen?" ist dann Pflicht, nicht Kür.
Verwandt mit #51 (*ein Filter auf „leer" ist kein Filter auf „vollständig"*),
nur umgekehrt: dort war der Filter zu schwach, hier ist er richtig, aber
sein Rest bleibt unerwähnt.

**Behoben:** `get_bond_summary` liefert `gewicht_ohne_faelligkeit` und
`anzahl_ohne_faelligkeit` (additiv, die bestehenden Schlüssel bleiben), die
Anzeige benennt die Differenz, und wo es keinen Chart gibt, steht jetzt ein
Satz. Prüfstein `tests/test_portfolioanalyse.py`, Schritt 3, rechnet über
alle Strategien nach, dass Balkensumme + Rest wieder die Kachel ergibt
(Toleranz 1e-12).

---

### #60 — Machbar ist nicht dasselbe wie besser (BITTE NICHT ERNEUT VERSUCHEN)

> **Ergebnis vorweg, damit niemand denselben Weg ein zweites Mal geht:** Der
> Streamlit-Datepicker lässt sich **nicht** auf Deutsch umstellen. Der Ersatz
> durch eigene Auswahlfelder wurde am 17.08.2026 gebaut, getestet und am
> Bildschirm gesichtet — und **verworfen**, weil er schlechter aussieht als
> der englische Kalender. *„Es darf auf Englisch sein. Weil jetzt sieht es
> nicht schön aus."* (Philip, 17.08.2026). Der Code ist zurückgebaut;
> `st.date_input` mit `format="DD.MM.YYYY"` ist der richtige Baustein.
>
> **Was bleibt, ist die Analyse darunter** — sie erspart dem Nächsten die
> Suche nach einer Einstellung, die es nicht gibt.

**Gemeldet von Kollegen am 17.08.2026:** Der Kalender im „Eigenen Zeitraum"
zeigt englische Monatsnamen.

Der erste Reflex — „da fehlt eine Einstellung" — führt hier ins Leere, und
das kostet Zeit, wenn man es nicht weiß:

| Vermutung | Befund |
|---|---|
| `format="DD.MM.YYYY"` reicht nicht? | Richtig. Der Parameter wirkt nur auf den Text **im Feld**, nicht auf das Popover. |
| Browsersprache umstellen? | Wirkungslos. Daraus leitet Streamlit **nur** ab, ob die Woche am Montag oder Sonntag beginnt. |
| Es gibt einen `locale`-Parameter? | Nein — weder an `st.date_input` noch in `config.toml`. |
| Vielleicht liefert Streamlit die Sprachdatei nach? | Nein. Im Frontend-Bündel von 1.61 steckt **nur** en-US (date-fns). |

**Nachgesehen statt vermutet:** `.venv/.../streamlit/static/static/js/` —
`useIntlLocale…js` enthält `January`, `Wednesday` und keinen einzigen
deutschen Monatsnamen; die Datei leitet aus dem Browser ausschließlich
`weekStartsOn` ab. Das war die Fünf-Minuten-Messung, die alle weiteren
Versuche erspart hat.

**Drei Wege, zwei verworfen** (Entscheidung Philip):

| Weg | Warum nicht |
|---|---|
| Popover per JavaScript übersetzen | Eingriff in fremdes DOM. Nach einem Streamlit-Update wirkt er still nicht mehr — und ein Prüfstein dafür lässt sich nicht bauen, weil die Wirkung erst im Browser entsteht (#54 in anderer Gestalt). |
| Fremdkomponente | Neue Abhängigkeit im öffentlichen Repo, die in der Cloud unter Python 3.14 laufen müsste — die Auto-Update-Falle #20, gegen die die requirements gerade erst gedeckelt wurden. |
| **Eigene Felder** | Gebaut — und nach der Sichtprüfung **wieder entfernt.** Tag / Monat / Jahr als `st.selectbox`, Namen aus `formats.MONATSNAMEN_LANG`. Technisch einwandfrei, 22 Suiten grün. Am Bildschirm trotzdem schlechter: Aus zwei Bedienelementen wurden sechs, der anklickbare Kalender war weg, und der Gewinn war ein Monatsname. |

**Die eigentliche Lehre ist nicht technisch.** Die Machbarkeit war nach einer
halben Stunde geklärt, der Bau lief glatt, die Prüfsteine waren grün — und das
Ergebnis war trotzdem eine Verschlechterung. *Ein gelöstes Problem ist noch
keine Verbesserung.* Bei einer Änderung, deren einziger Zweck das Aussehen
ist, entscheidet **allein die Sichtprüfung**, und die gehört **vor** den
Ausbau der Tests, nicht danach. Verwandt mit dem Muster, das dieses Projekt
schon zweimal getroffen hat (#44 Ring-Labels, Dichte der beiden Ansichten):
vermessen, verstanden — und bewusst nicht geändert.

Der Rückbau lief über `git revert`, nicht über `reset --hard`: Sollte
Streamlit die Sprache eines Tages unterstützen, ist der gebaute Weg in der
Historie nachlesbar (Commit `d99c61a`).

**Was beim Nachbau die Arbeit macht** — nicht die Darstellung, sondern der
Zustand:

1. **Rechenreihenfolge ≠ Anzeigereihenfolge.** Welche Tage zulässig sind,
   hängt an Monat und Jahr. Also erst Jahr, dann Monat, dann Tag beschreiben —
   und trotzdem Tag | Monat | Jahr anzeigen. `st.columns` erlaubt beides.
2. **`min_value`/`max_value` haben kein Gegenstück.** Statt eine freie Eingabe
   hinterher zurechtzubiegen, werden die **Optionen beschnitten**: im
   Anfangsjahr 2008 nur Dezember ab dem 30., im Endjahr 2026 nur Januar bis
   Juli. Ein unmögliches Datum ist damit nicht wählbar — und die Oberfläche
   zeigt nie eine Auswahl, die etwas anderes bedeutet als sie sagt.
3. **Optionen können verschwinden.** Steht im Zustand der 31. und jemand
   wechselt auf Februar, wirft `st.selectbox`, weil der gespeicherte Wert
   nicht mehr in `options` steht. Der Wert muss **vor** dem Anlegen des
   Widgets geklemmt werden. Das ist erlaubt, solange das Widget in diesem Lauf
   noch nicht existiert — die Ausnahme zu #4, wo das Setzen eines *aktiven*
   Widget-Keys wirft.
4. **Vorbelegung über `session_state`, nicht über `index=`.** Sonst hängt das
   Verhalten davon ab, ob der Key schon existiert — und der Zurücksetzen-Knopf
   mit seinen Zähler-Keys (#4, Lösung A) verliert seine Wirkung.

**Gemeldet war eine Stelle, betroffen waren vier.** Start/Ende im eigenen
Zeitraum **und** Von/Bis am Balken-Chart. Der zweite Bedienpfad war bis dahin
**von keinem Test berührt** — das ist der einzige bleibende Ertrag dieser
Runde: Schritt 1b in `tests/test_bedienung.py` fährt ihn jetzt hoch und prüft
zugleich, dass **alle vier** Felder `format="DD.MM.YYYY"` tragen. Das ist der
Teil der deutschen Darstellung, den Streamlit kann; fällt der Parameter weg,
steht dort `2026/07/21`, und ohne Prüfung sieht das niemand.

**Ein Prüf-Detail für den Fall, dass es doch jemand nochmal baut:** Die
Auswahlfelder tragen intern die Monats**nummer** und zeigen den Namen über
`format_func`. In Streamlits AppTest liefert `.value` den Rohwert (`7`),
`.options` die **Beschriftung** (`"Juli"`). Ein Test auf `.value` wäre grün,
während am Bildschirm „July" steht — geprüft gehört die Anzeige. Dasselbe
Muster wie #54: nicht das Objekt prüfen, sondern das, was ankommt. Und beim
Vergleichen aufpassen: `'2008' != 2008`, die beiden Seiten haben verschiedene
Typen.

---

### #63 — Ein nicht gelesener Standard sieht aus wie eine Festlegung (NEU 18.08.2026) ⭐

`.streamlit/config.toml` ist die einzige Datei dieses Projekts, deren Fehler
sich **nicht bemerkbar machen**. Wird sie nicht gelesen oder fehlt ein
Abschnitt, sieht die Anwendung aus wie eine Anwendung ohne Konfiguration —
also **normal**. Dasselbe ist hier zweimal passiert:

| Wann | Was | Wie lange unbemerkt |
|---|---|---|
| bis 07.08.2026 | Ordner hieß `streamlit/` statt `.streamlit/`, `toolbarMode` wirkte nie (#23) | Monate |
| bis 18.08.2026 | **gar kein `[theme]`** — die App lief mit Streamlits Akzentfarbe `#FF4B4B` | seit Projektbeginn |

Das zweite fiel nur auf, weil jemand **hingesehen** hat: Philip bemerkte, dass
die Auswahl-Chips im Strategievergleich rot leuchten. Ein grelles Korallenrot
auf Chips, Kontrollkästchen, Fokusrahmen und Umschaltern — in einem Werkzeug
für eine Privatbank, dessen Palette Fuggerblau und Fuggergold ist.

**Die Lehre für den Test ist die eigentliche.** Ein Prüfstein auf den INHALT
der Konfigurationsdatei hätte beide Fälle **nicht** gefunden: Die Datei war ja
richtig, sie wurde nur nicht gelesen. Zu prüfen ist deshalb die WIRKUNG:

```python
config.get_where_defined("theme.primaryColor")   # -> .streamlit/config.toml
                                                 #    und nicht "<default>"
```

Dieselbe Klasse wie #50 (*ein Versprechen im Kommentar ist kein Prüfstein*)
und #55 (*was inline steht, ist für keinen Prüfstein erreichbar*): Es genügt
nicht, dass etwas dasteht — es muss ankommen.

**Zwei Folgeregeln:**

1. **Wo eine Vorgabe wie eine Entscheidung aussieht, gehört die Entscheidung
   aufgeschrieben.** Der Akzent steht jetzt als `THEME_AKZENT_HELL` /
   `THEME_AKZENT_DUNKEL` in `shared.py`, und der Prüfstein hält die
   Konfiguration dagegen — sonst entstehen zwei Fassungen derselben Farbe.
2. **Streamlits Standardrot namentlich ausschließen.** Wer das Theme entfernt,
   bekommt `#FF4B4B` zurück, ohne dass es nach einem Fehler aussieht. Der
   Prüfstein nennt die Farbe deshalb beim Namen.

**Nebenbefund zur Formatierung:** `st.column_config` formatiert seine Zahlen
selbst — englisch oder nach der Locale des **Browsers**. In einem Werkzeug mit
genau einer Formatierungsquelle (`modules/formats.py`) ist das eine zweite,
unkontrollierte. Der Beitragsbalken des Drilldowns ist deshalb aus Text
gebaut: auf jedem Rechner derselbe, ohne CSS, und auf Proportionalität
prüfbar.

### #62 — Ein Vergleichsmaß ist nur so aussagekräftig wie seine Ebene (NEU 18.08.2026) ⭐

Wer zwei Portfolios vergleicht, wählt dabei immer eine **Ebene** — Einzeltitel,
Branche, Region, Währung. Dieselbe Rechnung auf gröberen Kategorien liefert
zwangsläufig höhere Werte, weil sich zwei Depots bei vier Gattungen kaum
verfehlen können. Am Paar *cVV ausgewogen* gegen *Comdirect 100* gemessen
(Überlappung = Σ min der Gewichte):

| Ebene | Ausprägungen | Überschneidung |
|---|---:|---:|
| Einzeltitel (WKN) | 166 | **20,5 %** |
| Segment | 18 | 52,0 % |
| Währung | 6 | 60,6 % |
| Region | 10 | 64,2 % |
| Gattung | 4 | **73,8 %** |

**Die Zahlen sind nicht untereinander vergleichbar**, und das ist keine
Feinheit: Wer „73,8 %" ohne die Ebene liest, hält zwei Depots für fast
identisch, die auf Titelebene zu einem Fünftel übereinstimmen. Die Ebene
gehört deshalb an die Zahl — im Titel, in der Achse und in der Caption.

**Zweiter Teil derselben Lehre: die Obergrenze ist selten 100 %.** Die
Titelgewichte der 19 Strategien summieren sich auf 88,8 bis 98,2 %, der Rest
ist Liquidität. Die maximal mögliche Überschneidung eines Paares ist damit
`min(Σw_A, Σw_B)`. **Bewusst nicht wegnormiert:** Eine Normierung auf
„100 % = maximal möglich" ließe zwei Depots mit viel Kasse ähnlicher
aussehen, als sie sind. Ein Vorbehalt, den man benennt, ist besser als eine
Zahl, die ihn versteckt (dieselbe Familie wie #59).

**Und was verglichen wird, muss FEST sein.** `build_allocation` fasst
Kategorien unter 3 % zu „Sonstige" zusammen — je Strategie einzeln. Für einen
Ring ist das richtig; für einen Vergleich nebeneinander wäre es fatal:
Dieselbe Region stünde bei der einen Strategie als eigener Balken und wäre
bei der nächsten in „Sonstige" verschwunden, ohne dass man es sieht. Genau
diese Lehre gab es schon einmal, bei der Farbskala der Heatmap (14.08.2026):
Eine datenabhängige Skala färbt zwei Strategien unterschiedlich ein.

**Nebenbefund zur Datenhygiene, den erst der Prüfstein brachte:** Der Filter
gegen Fehlwerte hing nur zufällig. `parse_pf_data` räumt sieben Spalten auf,
„Währung" und „Marktrisikowert" gehören **nicht** dazu; dort fiel die leere
CSV-Schlusszeile allein deshalb heraus, weil sie auch kein Gewicht trägt.
Dazu: **pandas 3.0 wirft NA-Schlüssel beim `groupby` von sich aus weg** — die
Gegenprobe eines Prüfsteins muss deshalb `dropna=False` setzen, sonst prüft
sie das Werkzeug statt den Code. Ein Schutz, den die Bibliothek stellt, kann
beim nächsten Versionswechsel verschwinden (#20).

**Und eine, die nicht technisch ist:** Der Marktrisikowert war gebaut und ist
wieder ausgebaut worden (Philip, 18.08.2026). Er liegt je Titel in den Daten
— aber das Haus **legt ihn selbst fest**. Eine vergebene Kennzahl neben
gemessenen Größen sieht aus wie eine Beobachtung. Ob eine Zahl in ein
Beratungswerkzeug gehört, entscheidet nicht ihre Verfügbarkeit.

### #61 — Ein Vergleich ist nur so ehrlich wie sein gemeinsamer Zeitraum (NEU 18.08.2026) ⭐

Eine Einzelansicht darf „seit Auflage" rechnen — dort steht die Zahl allein,
und das Auflagedatum steht daneben. Sobald aber **mehrere Reihen
nebeneinander** stehen, verspricht die gemeinsame Achse eine gemeinsame
Grundlage. Halten die Historien das nicht, misst die Grafik etwas anderes,
als ihre Beschriftung sagt.

Gemessen an den 19 Strategien (Historien von **1,7 bis 17,6 Jahren**):

| Strategie | Historie | Rang „seit Auflage" | Rang „3 gemeinsame Jahre" |
|---|---:|---:|---:|
| cVV dynamic | 7,8 J | 4 | **14** |
| cVV ausgewogen | 17,6 J | 11 | **5** |
| ETF_Wachstum | 10,6 J | 15 | **6** |
| Offensiv | 17,6 J | 7 | **12** |

Die Punktwolke hätte also nicht gezeigt, welche Strategie besser ist, sondern
**wann sie aufgelegt wurde**: Die alten Reihen tragen Finanzkrise, Corona und
2022 mit, die jungen nur den Aufschwung seit 2023.

**Beim Max Drawdown ist es schärfer als bei der Volatilität**, und das ist der
Teil, der leicht übersehen wird: Volatilität ist ein annualisiertes Streumaß
und über verschieden lange Fenster wenigstens grob vergleichbar. Der Max
Drawdown ist ein **Einzelereignis** — er kann mit der Länge der Historie nur
wachsen. Wer länger dabei ist, sieht schlechter aus:

| | seit Auflage | über 3 Jahre |
|---|---:|---:|
| cVV konservativ, Max Drawdown | −14,02 % | −3,67 % |

**Die Konsequenz:** gemeinsames Fenster, und wer es nicht vollständig abdeckt,
wird **nicht gezeichnet, sondern genannt** — mit seiner tatsächlichen
Historienlänge. Dieselbe Klasse wie #51 (ein Rumpfjahr ist kein Jahresbalken)
und #59 (ein Aggregat muss sagen, was es nicht enthält), nur in einem
Streudiagramm statt in einem Säulen-Chart oder einer Kachel.

**Und die Vorbelegung gehört dazu.** „Längster gemeinsamer Zeitraum" klingt
nach der besten Vorgabe und ist es nicht: Über alle 19 Strategien sind das
**1,7 Jahre**, weil die jüngste Reihe das Fenster bestimmt. Über 1,7 Jahre
lässt sich über Risiko nichts sagen — und es wäre das Erste, was der Berater
sieht. Die Ansicht startet deshalb mit „3 Jahre" (14 von 19 Strategien).
Aufgefallen ist das nicht beim Nachdenken, sondern **beim ersten AppTest**.

**Was NICHT gebaut werden musste:** Die Abdeckungsregel gab es schon —
`analytics.risiko_perioden` lässt eine nicht gedeckte Periode seit dem
14.08.2026 leer, statt gekürzt zu rechnen. Es lohnt sich, vor dem Bauen zu
suchen, ob die eigene Zusage anderswo schon eine Funktion hat: Hier fehlte am
Ende **eine einzige Größe** (die Rendite p.a.), und die kam in dieselbe
Funktion und dieselbe Schleife — aus **derselben Indexreihe** wie der
Drawdown, damit die beiden Achsen eines Punktes nicht auf zwei verschiedenen
Reihen rechnen können.

**Nebenbefund zur Mathematik, den erst der Prüfstein gebracht hat:** Eine
Reihe ohne Marktbewegung kostet **exakt** den Honorarsatz p.a. — und zwar
unabhängig davon, wie lang sie ist. Die Annualisierung hebt die Tageszahl
wieder auf: `((1−d)^n)^(365/n) = (1−d)^365 = 1−f`. Der Anker aus B3 ist also
allgemeiner, als er in `test_kosten_mathematik` formuliert war. Dass die
Tageszahl selbst stimmt, muss ein **eigener** Fall prüfen (eine wachsende
Reihe gegen die geschlossene Form) — der Nulltag-Anker kann es nicht.

## 1. Projektübersicht

Streamlit-App für Fürst Fugger Privatbank mit **3 Ansichten** (seit
07.07.2026 per `st.segmented_control` oben auf der Seite navigiert, davor
`st.tabs`; die dritte kam am 18.08.2026 dazu und war dadurch ein
Listeneintrag — der alte Tab-Bug von #18 kann nicht zurückkehren).

| Ansicht | Datei | Zeilen (ca.) | Zweck |
|---|---|---|---|
| 📈 Performance | `streamlit_app.py` | ~1.090 | Historische Performance, Kennzahlen (inkl. Sharpe), Charts, PDF+Glossar, Konsistenz-Caption |
| 📊 Portfolioanalyse | `modules/portfolioanalyse.py` | ~900 | Strukturanalyse: Ringe, Tabellen, Anleihen-Detail (Duration/Rendite aus Titeln), **PPTX-Export** (familiengesteuerte Vorlagenwahl) |
| 📐 Strategievergleich | `modules/strategievergleich.py` | ~800 | *(NEU 18.08.2026)* Alle Strategien nebeneinander: Risiko-Rendite-Punktwolke (#61), Überschneidung und Exposure (#62). Rechnet nichts selbst — liest `analytics.risiko_perioden` und `bestandsanalytik` |
| (Bestands-Mathematik) | `modules/bestandsanalytik.py` | ~200 | *(NEU 18.08.2026)* **streamlit-frei**: Gewicht je Kategorie, Überschneidung zweier Depots, Liquidität. Gegenstück zu `analytics.py`, das die Zeitreihen trägt |
| (Berechnungen) | `modules/analytics.py` | — | **Single Source of Truth** für Performance-Mathematik (CAGR, Vola, Sharpe, Drawdown, Perioden-Renditen); genutzt von App UND PPTX-Export |
| (gemeinsam) | `modules/shared.py` | ~300 | Konstanten, Login, Formatierung, Font-Setup, Corporate-Palette, CSV-Loading-Helpers |
| (PPTX generisch) | `modules/pptx_helpers.py` | — | Shape/Text/Table/Slide-Manipulation (inkl. `ensure_table_capacity`, `fit_shape_to_table`, `_reorder_slides`) |
| (PPTX Charts) | `modules/pptx_charts.py` | — | Chart-XML mit Bug-Workarounds (`replace_chart_data_safe` = 4-Bug-Fix, `replace_chart_data` XML-in-place für Ringe, `set_date_axis_base_unit`) |
| (PPTX Folien) | `modules/pptx_slides.py` | — | Domain-Logik pro Folie (`fill_*_slide`-Funktionen, Themen-Blöcke, `EINZELTITEL_WARNUNGEN`) |
| (PPTX Orchestrierung) | `modules/pptx_export.py` | — | Broschüren-Aufbau: N Strategien, `template_config`/`block_reihenfolge`, `compute_performance_data`, `compute_rollierend_data`, Block-Dispatcher, `LAST_BUILD_ERRORS` |
| (Tests) | `tests/test_benchmark_erkennung.py` | ~130 | Regressionstest gegen die echten CSVs; läuft ohne pytest und ohne Streamlit |

**Deployment:** Streamlit Community Cloud via GitHub (Repo `FFPBAM/Performancetool`), Branch **`verbesserungen`**. Cloud-Python: **3.14**. Alle Abhängigkeiten sind seit 11.08.2026 nach oben gedeckelt (Transferwissen #20).

> ⚠️ **Der Arbeitsbranch IST die produktive App.** Bis zum 17.08.2026 stand
> hier „Branch `main`", und `Start.txt` schrieb dazu „Solange main steht, sieht
> der Streamlit-Deploy nichts davon". **Beides war falsch.** Belegt am
> 17.08.2026 an einem Traceback aus der laufenden Cloud-App: Python fasst
> mehrzeilige Anweisungen als `...<N lines>...` zusammen, und N identifizierte
> den Import-Block eindeutig als den des **neuen** Commits auf
> `verbesserungen` (18 Zeilen → `...<16 lines>...`; der Vorgängerstand hätte
> `...<13 lines>...` gezeigt).
>
> Die Folge war ein echter Ausfall: Ein Push, der in dem Glauben erfolgte, er
> sei folgenlos, hat die App für die Kollegen angehalten. **Wer auf
> `verbesserungen` pusht, ändert das laufende Werkzeug** — Testlauf vorher,
> App ansehen nachher.

⚠️ **Repo-Sichtbarkeit:** Frühere Fassungen dieser Doku forderten „Repo MUSS privat sein (Honorarsätze im Mapping!)". Das Repo ist tatsächlich **öffentlich** (am 07.08.2026 über die GitHub-API verifiziert: `"visibility": "public"`, angelegt am 19.02.2026) — und bleibt es nach Entscheidung von Philip, damit der Cloud-Deploy unverändert läuft. Damit sind Honorarsätze, Benchmark-Zusammensetzungen und die Musterdepot-CSVs öffentlich einsehbar. **Kundendaten sind nicht betroffen** (nur „Muster"-Portfolios; der `EXCLUDE_SUBSTRINGS`-Filter hält Stiftungsdepots draußen), und `secrets.toml` wurde nie committet. Wer hier Daten ergänzt, sollte das im Bewusstsein tun, dass sie öffentlich werden — und dass die Git-Historie sie auch nach dem Löschen behält.

*Hinweis am Rande:* Streamlit Community Cloud kann grundsätzlich auch aus privaten Repos deployen (erweiterter OAuth-Scope beim Verbinden des GitHub-Kontos); auf dem freien Tarif ist die Zahl privater Apps allerdings begrenzt.

**Nicht aktiv im Repo:** `modules/portfolio_builder.py` (~606 Zeilen) – seit Juni 2026 nicht mehr importiert (Compliance-Entscheidung), bleibt aber bewusst liegen für eine mögliche Reaktivierung. `Zieldaten/` gehört dazu.

**Vorlagen:**
- `Vorlage/Vorlage_FFPB.pptx` – Standard-Broschüre, **26 Slides** (seit 02.07.2026 inkl. Wertentwicklungs-Folie), benannte Shapes, JPEG-optimiert (~4 MB)
- `Vorlage/Vorlage_Thema.pptx` – Themen-Broschüre (Pro / Pro Dividende / Offensiv), **21 Slides**, 3,95 MB (von 24 MB optimiert), dynamischer Block F10–F13

---

## 2. Dateistruktur

```
Repository Root/
├── streamlit_app.py                 ← Navigation (segmented_control), Keep-Alive,
│                                      zentrale Datenbereitstellung, Performance-Ansicht inline
├── modules/
│   ├── __init__.py
│   ├── shared.py                    ← Konstanten, Login, Formatierung, CSV-Loader
│   ├── analytics.py                 ← Berechnungs-Single-Source-of-Truth (inkl. has_benchmark)
│   ├── portfolioanalyse.py          ← Portfolioanalyse-Ansicht + PPTX-Export-Integration
│   ├── pptx_helpers.py              ← generische Shape/Table/Slide-Manipulation
│   ├── pptx_charts.py               ← Chart-XML inkl. replace_chart_data_safe (4 Bugs)
│   ├── chart_dynamik.py             ← Chart-Nachbearbeitung (Achsen, holeSize,
│   │                                   Ring-Labels außen) — nachbearbeiten(prs), TW #26
│   ├── pptx_slides.py               ← Folien-Befüllung (Domain-Logik) + generische
│   │                                   Tabellen-Helfer (TW #27)
│   ├── pptx_export.py               ← Broschüren-Orchestrierung
│   ├── download_helfer.py           ← clientseitiger Blob-Download (TW #25)
│   ├── formats.py                   ← Format-Helfer + Textkonstanten der Broschüre
│   └── portfolio_builder.py         ← deaktiviert seit Juni 2026 (bewusst aufgehoben)
├── tests/
│   └── test_benchmark_erkennung.py  ← NEU 07.08.2026, läuft ohne pytest/Streamlit
├── Vorlage/                         ← 6 Familien-Vorlagen (FFPB, Thema, ESG, ETF,
│                                      comdirect, cVV_Infoboard)
├── fonts/                           ← Segoe-UI-Dateien für den PDF-Export
├── .streamlit/config.toml           ← toolbarMode = "minimal"  (Punkt im Ordnernamen ist
│                                      zwingend, siehe unten!)
├── .gitignore                       ← NEU 07.08.2026 — schließt secrets.toml aus
├── Mapping_Honorarsatz.xlsx         ← Inhaber + Honorarsatz Standard (Dezimal)
├── Mapping_Namen.xlsx               ← A=Anzeigename, B=CSV-Key, C=Duration(alt), D=Benchmark,
│                                      + Spalte "Powerpoint Familie" (NEU Juli 2026)
├── FFPB_Architektur_Ueberblick.pdf  ← Architektur-Grafik (Stand 28.07.2026)
├── Fuerst_Fugger_Bank_Logo_2-ZL-RGB.jpg
├── Daten/                           ← Performance-CSVs
├── Daten_PF/                        ← Portfolioanalyse-CSVs (Spalten inkl. Duration, Rendite;
│                                      Spalte "Währung" angekündigt, siehe Backlog)
├── Zieldaten/                       ← Anlageuniversum für Builder (deaktiviert)
└── requirements.txt                 ← streamlit gepinnt, Rest Mindestversionen
```

⚠️ **`.streamlit` MUSS den Punkt haben.** Bis 07.08.2026 hieß der Ordner im Repo
`streamlit/` (ohne Punkt) — Streamlit liest ausschließlich `.streamlit/config.toml`
und hat die Datei deshalb stillschweigend ignoriert; `toolbarMode = "minimal"` war
nie aktiv. Ursache war vermutlich das Anlegen über die GitHub-Weboberfläche
(vgl. Transferwissen #23). Nach Änderungen an diesem Ordner immer prüfen, ob der
Punkt noch da ist.

⚠️ **NICHT im Repo, obwohl frühere Fassungen dieser Doku es behaupteten:**
`erstelle_broschueren.py` und `modules/dataload.py` (lokaler Batch, Abschnitt 13)
wurden **nie committet**. Sie existierten nur lokal bzw. in Chatverläufen. Wer den
Batch braucht, muss ihn neu bauen — die Beschreibung in Abschnitt 13 bleibt als
Bauplan stehen.

**ENTFERNT am 07.08.2026 (toter Code, rund 1.900 Zeilen):** `performance.py`
(Altkopie von `streamlit_app.py`, trug im Header noch `# streamlit_app.py`),
`macrobond_upload.py` (nirgends referenziert), `ll` (Tippfehler-Artefakt), die
leeren Platzhalter-`.md` in `Daten/`, `Daten_PF/`, `Vorlage/`, `fonts/`,
`Zieldaten/`, sowie `generate_pf_pdf` + `_mpl_ring_chart` aus
`portfolioanalyse.py` (damit dort auch reportlab und matplotlib).

**GELÖSCHT (03.07.2026):** Der Ordner `Duration/` — Duration/Rendite werden seit dem 03.07. **anleihe-gewichtet aus den Titeldaten** berechnet (`duration_info_aus_bestand` → `get_bond_summary`; verifiziert gegen Tool-Werte "Muster defensiv cVV": Duration 3,96 / Rendite 3,28 %). ⚠️ Der lokale Batch liest noch den alten Ordner — siehe Backlog Punkt 2.

**Es gibt ZWEI Mappings — nicht verwechseln:** `build_portfolio_timeseries` erwartet das HONORARSATZ-Mapping (`Mapping_Honorarsatz.xlsx`, Spalten "Inhaber" + "Honorarsatz Standard"); Familien/Benchmark/Duration nutzen das NAMEN-Mapping (`Mapping_Namen.xlsx`, Spalten A–D + "Powerpoint Familie").

### requirements.txt (Stand 11.08.2026 — jede Zeile mit Obergrenze)
```
streamlit==1.61.0                    ← exakt (Transferwissen #20)
starlette<1.4.0
pandas>=3.0.5,<4                     ← die beiden aus dem Ausfall vom 06.07.
numpy>=2.5.2,<3
plotly>=6.9,<7
openpyxl>=3.1.5,<4
Pillow>=12.3,<13
python-pptx>=1.0.2,<2
lxml>=6.1,<7                         ← KRITISCH für Chart-XML-Manipulation
```
**Am 11.08.2026 umgestellt** (Backlog 1 erledigt): Untergrenze = der Stand,
mit dem alle zwölf Testsuiten und sieben Broschüren durchliefen; Obergrenze =
nächste Hauptversion. Die Datei selbst trägt die vollständige Begründung als
Kommentar — sie ist die Stelle, an der jemand nachschaut, wenn die App wieder
„gestern noch lief". `matplotlib` und `reportlab` sind mit dem PDF-Weg am
11.08. entfallen.

Ein `pip install --dry-run --ignore-installed -r requirements.txt` landet
exakt auf dem getesteten Satz (pandas 3.0.5, numpy 2.5.2, streamlit 1.61.0,
…) — die Grenzen widersprechen sich also nicht. **Grenze dieser Prüfung:**
lokal unter Python 3.12 gelaufen, die Cloud nutzt 3.14.
⚠️ **`lxml` fehlte bis 07.08.2026 in dieser Datei**, obwohl `pptx_charts.py`,
`pptx_export.py` und `chart_dynamik.py` es DIREKT importieren
(`from lxml import etree`). Es kam nur zufällig als transitive Abhängigkeit von
python-pptx mit — ein Wechsel der python-pptx-Version hätte die Chart-XML-
Manipulation jederzeit lahmlegen können. Ebenfalls am 07.08. korrigiert:
`python-pptx>=0.6.21` (Untergrenze von 2021) → `>=1.0`.

⚠️ Siehe Transferwissen #20: Die Cloud zieht bei jedem Reboot die NEUESTEN
Versionen der nach oben offenen Pakete. Seit 11.08.2026 ist keine Zeile mehr
nach oben offen — der Reboot kann damit keine neue Hauptversion mehr
einschleppen.

**Merksatz:** Was der Code direkt importiert, gehört in die requirements —
transitive Abhängigkeiten sind kein Vertrag.

---

## 3. Abhängigkeiten

```
shared.py ──→ streamlit_app.py (Performance inline + importiert Portfolioanalyse)
          ──→ portfolioanalyse.py ──→ pptx_export.py
analytics.py ──→ streamlit_app.py (Wrapper) + pptx_export.py

PPTX-Schichten:
    pptx_helpers (Shape/Text/Table/Slide-Manipulation)
    pptx_charts  (Chart-XML mit Bug-Workarounds)
        ↑
    pptx_slides  (Domain-Logik pro Folie)
        ↑
    pptx_export  (Orchestrierung der Broschüre)
```

**Seit 07.08.2026 gibt es die CSV-Loader nur noch EINMAL**, in `shared.py`.
Vorher hatte `streamlit_app.py` eigene, zeilengleiche Kopien — mit zwei
getrennten `@st.cache_data`-Caches und dem Risiko, dass Tool und Broschüre bei
Drift verschiedene Zahlen zeigen. Dieselbe Falle lauert bei jeder neuen
„streamlit-freien Kopie": Wer Loader ohne Streamlit braucht, sollte sie in ein
gemeinsames UI-freies Modul ziehen, statt sie zu duplizieren.

`portfolio_builder.py` liegt im Repo, wird aber nicht importiert.

---

## 4. Corporate Design

**Beide Ansichten nutzen durchgängig die offiziellen Fürst Fugger Privatbank Corporate Colors.**
Single source of truth ist `modules/shared.py`.

### Hauptfarben

| Konstante | Hex | Name | Hauptverwendung |
|---|---|---|---|
| `FFPB_DARK` | #003460 | Fuggerblau | PDF-Headlines, Tabellen-Kopfzeile, Balken-Chart Hintergrund, Ring-Chart größtes Segment |
| `FFPB_GOLD` | #C3A069 | Fuggergold | Akzent, Portfolio-Balken, Fälligkeits-Balken, Ring-Chart zweites Segment |
| `FFPB_BLUE2` | #4A7FAA | Mittelblau | Portfolio 2 (Vergleich), Ring-Chart drittes Segment |
| `FFPB_SAND` | #D4BD8A | Sand | Benchmark 2 (Vergleich), Ring-Chart viertes Segment |
| `FFPB_LIGHT` | #7FABC8 | Hellblau | Benchmark, Ring-Chart fünftes Segment |

### Erweiterte 15er-Sequenz (`FFPB_PALETTE`)

```python
FFPB_PALETTE = [
    "#003460", "#C3A069", "#4A7FAA", "#D4BD8A", "#7FABC8",
    "#8B7340", "#A8CBE8", "#5C6B3C", "#E8D5B0", "#2C5F8A",
    "#C4C4C4", "#3A7CA5", "#F0C070", "#6A9BC3", "#2A4A6C",
]
```

### Spines & Gridlines (PDF/Plotly auf dunklem Hintergrund)

- **Spines:** `#1A4880`  
- **Gridlines:** `#0A4576`

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
**Dateinamen-Pattern:** `*_<yyMMdd>_*.CSV`  
**Erste Zeile** enthält Metadaten, **ab Zeile 2** beginnen die Tageswerte.

| # | Spalte | Inhalt | Format |
|---|---|---|---|
| 1 | `Portfolio Name` | CSV-Key | String |
| 2 | `Datum` | Tageswert-Datum | `DD.MM.YYYY` |
| 3 | `Performance [%] (Intervall)` | Tagesperformance Portfolio | Prozent |
| 7 | `Benchmark Performance [%] (Intervall)` | Tagesperformance Benchmark | Prozent |
| 8 | `Risiko freier Zins` | Annualisierter rf | Dezimal |

### 6.2 Portfolioanalyse-CSVs (`Daten_PF/`)

Positions-CSVs mit u.a. Wertpapier, WKN, ISIN, Gewicht, Gattung, Region,
Segment, Kupon, Fälligkeit, **Duration**, **Rendite**, Auswertungsdatum.
Duration ist eine JAHRES-Zahl (z.B. 3,96), KEIN Prozentwert. Seit 03.07.
werden Portfolio-Duration und -Rendite anleihe-gewichtet direkt aus diesen
Spalten berechnet (Variante B: normiert auf die Gewichtssumme der Anleihen).
**Geplant:** Spalte "Währung" (für die Themen-Einzeltitel-Folie; Philip
liefert per Push nach — der Code füllt sie dann automatisch).

### 6.3 Mapping-Dateien

**`Mapping_Honorarsatz.xlsx`:** Inhaber + Honorarsatz Standard (Dezimal)  
**`Mapping_Namen.xlsx`:** A=Anzeigename, B=CSV-Key, C=Duration (Altbestand, unbenutzt), D=Benchmark-Zusammensetzung, **Spalte "Powerpoint Familie"** (NEU Juli 2026): steuert die PPTX-Vorlage. Werte: `Thema` / `CVV` / `ETF` / `ESG` / leer (= Standard). Erkennung ist tolerant gegen Schreibweise/Whitespace (`_finde_familie_spalte`, case-insensitive Wert-Mapping auf kanonische Schlüssel).

---

## 7. App-Grundgerüst: Navigation, Keep-Alive, Datenbereitstellung (NEU 07.07.2026)

`streamlit_app.py` hat seit dem 07.07. folgende feste Reihenfolge — sie ist
BEWUSST so und darf beim Erweitern nicht durcheinandergebracht werden:

1. **Login** (`check_login`)
2. **Keep-Alive-Block** (Transferwissen #19): re-assignt alle session_state-Keys, Trigger-Widgets per `_KEEPALIVE_SPERRE` ausgenommen
3. **Gemeinsame Sidebar** (Anlagevolumen)
4. **Zentrale Datenbereitstellung** (läuft bei JEDEM Run): lädt die Performance-Zeitreihen (respektiert `adv_perf`+`perf_tag` aus dem session_state) und setzt `perf_timeseries` / `perf_d2c` / `perf_d2b`. Lade-Fehler stoppen NICHT die App — nur die Performance-Ansicht zeigt den Fehler, die Portfolioanalyse läuft weiter (Fallback-Loader, Transferwissen #15)
5. **Navigation**: `st.segmented_control(key="nav_view", required=True)` (Transferwissen #18)
6. `if ansicht == _VIEW_PERF:` → Performance-Ansicht (inline) / `else:` → `render_portfolioanalyse(...)`

**Warum 4 vor 5:** Der PPTX-Export im Portfolioanalyse-Bereich braucht die
Performance-Daten — seit dem Umbau läuft aber nur noch die aktive Ansicht,
die Bereitstellung darf also nicht mehr am Besuch der Performance-Ansicht
hängen.

### Performance-Ansicht (Inhalt unverändert zu Phase 2, plus:)

- **Konsistenz-Caption (03.07.2026):** Info-Box über den Kennzahlen benennt
  live jede aktive Abweichung von der PowerPoint-Basis (Zeitraum-Filter,
  Vergleichs-Schnittmenge, manuell geänderter Kostensatz). Siehe
  Konsistenz-Doktrin, Abschnitt 11.8.
- **YTD der rollierenden Tabelle** rechnet seit 03.07. ab
  Vorjahres-Schlussstand (`asof(31.12.)`) — bit-identisch zu Balken-Chart
  und PP-Folie (Transferwissen #22).
- Kennzahlen-Wrapper delegieren an `modules/analytics.py`; UI-spezifische
  Kennzahlen (Euro-Drawdown, Calmar, DD-Dauer, rf-Index) bleiben lokal.

### Portfolioanalyse-Ansicht

- `_render_single_portfolio()` mit `suffix="pf1"/"pf2"` (Transferwissen #3)
- Ring-Diagramme: Absteigend sortiert, Labels außen (13px), <3% ausgeblendet
- **Duration/Rendite aus den Titeln** (seit 03.07.): `duration_info_aus_bestand` → `get_bond_summary` (anleihe-gewichtet, Arrow-robust, Transferwissen #21)
- **Export: NUR noch PowerPoint** (PDF-Button im Juli entfernt; `generate_pf_pdf` = toter Code). Export-Bytes werden in `session_state` gecacht (Key aus Auswahl+Familie), Diagnosen rerun-fest über `pf_pptx_build_errors`
- **Familiengesteuerte Vorlagenwahl** (Variante A): Der Berater wählt NUR die Strategie; die Mapping-Spalte "Powerpoint Familie" bestimmt die Vorlage. Leere/unbekannte Familie ODER fehlende Vorlagen-Datei → Standard-Export (rückwärtskompatibel, kein Crash). Bei "Package not found" gibt es eine Diagnose (Dateigröße, LFS-Zeiger-Warnung, Ordnerinhalt — Transferwissen #23)

Sidebar-Optionen: ☐ YTD Performance anzeigen · ☐ Bruttohonorar (inkl. 19% MwSt., wirkt auf PPTX-Kennzahlen) · ☐ Erweiterte Einstellungen (Date-Tag-Override)

---

## 8. DEEP-DIVE: Navigation ohne st.tabs — das vollständige Muster

> **Warum ein eigener Abschnitt?** Der Umbau von `st.tabs` auf
> `st.segmented_control` am 07.07.2026 hat einen hartnäckigen Bug strukturell
> beseitigt, der über Wochen immer wieder auftauchte. Das zugrunde liegende
> Muster — "Layout-Container taugt nicht als Navigations-Zustand" — ist nicht
> FFPB-spezifisch, sondern trifft JEDE mehrseitige Streamlit-App. Dieser
> Abschnitt erklärt das Kausalmodell, liefert das komplette Vorher/Nachher-
> Rezept, einen Entscheidungsbaum und die Fallstricke, damit niemand die
> Fehlersuche wiederholen muss. Die Kurzeinträge Transferwissen #18 (Bug),
> #19 (Keep-Alive) und #24 (AppTest-Beweis) verweisen hierher.

### 8.1 Das Symptom (was der Nutzer sah)

Im Portfolioanalyse-Tab: Strategie in der Selectbox auswählen → die Ansicht
sprang zurück auf den Performance-Tab. Der Portfolioanalyse-Tab startete
sauber (per Marker-Test bewiesen: die farbige Box "HIER BEGINNT
PORTFOLIOANALYSE" stand ganz oben, kein Performance-Inhalt davor) — erst die
Strategie-**Auswahl** warf die Ansicht auf Tab 1. Für den Berater wirkte das
wie ein zufälliger, nicht reproduzierbarer Aussetzer; tatsächlich war es
deterministisch und trat bei JEDER Widget-Interaktion im zweiten Tab auf.

### 8.2 Das Kausalmodell (warum es passiert — der eigentliche Kern)

Drei Streamlit-Grundwahrheiten greifen hier ineinander. Wer sie einzeln
kennt, dem ist der Bug sofort klar:

**(1) Jede Widget-Interaktion löst einen kompletten Skript-Rerun aus.**
Streamlit hat kein Event-System, das nur ein Fragment aktualisiert — das
GESAMTE `streamlit_app.py` läuft bei jeder Selectbox-Auswahl von oben neu
durch. Das ist das Grundmodell, kein Bug.

**(2) `st.tabs` ist ein reines LAYOUT-Element, kein Zustands-Element.**
`st.tabs` erzeugt Container nebeneinander und rendert bei jedem Run ALLE
Tab-Bodies (der Browser blendet nur den nicht-aktiven visuell aus). Welcher
Tab "vorne" liegt, ist reiner Frontend-Zustand im Browser — er wird NICHT
serverseitig im `session_state` gehalten. Beim Rerun baut Streamlit die
Tab-Gruppe neu auf und der Frontend-Zustand fällt auf den Default zurück:
den ERSTEN Tab.

**(3) Der Rerun serialisiert Server → Frontend, nicht umgekehrt.** Zum
Zeitpunkt, an dem der Server die neue Tab-Gruppe rendert, weiß er nicht,
welcher Tab im Browser aktiv war — diese Information war nie beim Server.

**Zusammengesetzt:** Interaktion in Tab 2 → Rerun (1) → Server baut
Tab-Gruppe neu, ohne den aktiven Tab zu kennen (2)+(3) → Frontend zeigt
wieder Tab 1. Der Bug ist damit KEINE Fehlfunktion, sondern die logische
Folge davon, ein Layout-Element für Navigation zu missbrauchen.

> **Verallgemeinerung (das eigentliche Transferwissen):** In Streamlit muss
> jeder Zustand, der einen Rerun überleben soll, im `session_state` leben.
> Ein Container/Layout-Element (`st.tabs`, `st.columns`, `st.expander` in
> seiner Auf/Zu-Stellung ohne key) hält KEINEN rerun-festen Zustand. Für
> NAVIGATION braucht es ein keyed Input-Widget.

### 8.3 Was NICHT funktioniert hat (und warum — Zeit gespart für den Nächsten)

Diese Versuche wurden gemacht und scheiterten; sie erneut zu probieren ist
verlorene Zeit:

| Versuch | Warum es nicht reicht |
|---|---|
| `st.tabs(..., key="active_tab")` | Der key macht den Tab-Zustand im `session_state` LESBAR (für Callbacks), stellt ihn aber beim Rendern nicht wieder her. Bug bleibt. |
| zusätzlich `on_change="rerun"` | Ändert nur, WANN ein Rerun ausgelöst wird (beim Tab-Wechsel) — nicht, welcher Tab nach dem Rerun aktiv ist. Bug bleibt. |
| zusätzlich `default=_aktiver_tab` (aus `session_state` zurückgelesen) | Laut Streamlit-Doku zur Widget-Identität gilt: **bei gesetztem `key` bestimmt der key die Identität, und `default` wird nur bei der ERSTEN Instanziierung ausgewertet.** Ab dem zweiten Run ignoriert Streamlit `default` — es kann strukturell nichts "wiederherstellen". Bug bleibt. |

Der rote Faden: Alle drei Versuche kämpfen GEGEN das Layout-Element, statt
den Zustand woanders hinzulegen. Das kann nicht gewinnen.

### 8.4 Die Lösung (segmented_control + if/else)

Navigation über ein keyed Input-Widget, dessen Wert von Natur aus im
`session_state` lebt und Reruns übersteht. Die Tab-Bodies werden zu
`if/else`-Zweigen — bei gleicher Einrückung ist der Diff minimal.

```python
# ── NAVIGATION: segmented_control statt st.tabs ──
_VIEW_PERF = "📈 Performance"
_VIEW_PF = "📊 Portfolioanalyse"
if "nav_view" not in st.session_state:
    st.session_state["nav_view"] = _VIEW_PERF
ansicht = st.segmented_control(
    "Ansicht", [_VIEW_PERF, _VIEW_PF],
    key="nav_view",            # Zustand lebt im session_state
    required=True,             # Klick aufs aktive Segment = No-op (kein None!)
    label_visibility="collapsed",
)

if ansicht == _VIEW_PERF:
    ...   # ehemals `with tab_perf:` — Einrückung bleibt, Diff minimal
else:
    ...   # ehemals `with tab_pf:`
```

**Warum `required=True` nicht optional ist:** Im Single-Mode kann der Nutzer
ein `segmented_control` sonst ABWÄHLEN (nochmal aufs aktive Segment klicken)
→ das Widget gibt dann `None` zurück → `ansicht == _VIEW_PERF` ist False,
`else` greift, und plötzlich landet man ungewollt in der Portfolioanalyse
ODER (je nach Logik) im Nichts. `required=True` macht den Klick aufs aktive
Segment zum No-op — es gibt nie den `None`-Zustand.

**Alternativen (gleiches Prinzip, andere Optik):**
- `st.radio(..., horizontal=True, key="nav_view")` — funktioniert identisch
  (keyed → rerun-fest), sieht klassischer aus.
- Radio/segmented in der Sidebar statt oben — spart vertikalen Platz, aber
  bei FFPB ist die Sidebar schon voll mit Einstellungen, daher oben.
- `st.navigation`/`st.Page` (echte Multipage) — der "richtige" Weg für viele
  Seiten, aber ein größerer Umbau (eigene Dateien pro Seite, kein geteilter
  Inline-State) — für zwei Ansichten Overkill.

### 8.5 Die zwei Nebenwirkungen — und wie man sie behandelt

Der Wechsel von "alle Tab-Bodies laufen" zu "nur die aktive Ansicht läuft"
hat zwei Konsequenzen, die man AKTIV behandeln muss, sonst tauscht man einen
Bug gegen zwei neue.

#### Nebenwirkung A — Daten, die "immer da sein müssen", laufen nicht mehr

Bei `st.tabs` lief der Performance-Body bei jedem Run mit und füllte dabei
`st.session_state["perf_timeseries"]` (die der PPTX-Export im
Portfolioanalyse-Bereich braucht). Nach dem Umbau läuft der Performance-Code
nur noch, wenn seine Ansicht aktiv ist — öffnet der Nutzer direkt die
Portfolioanalyse und klickt "PowerPoint erstellen", fehlen die Daten.

**Lösung: alles "immer Nötige" VOR die Navigation ziehen.** Die
Datenbereitstellung läuft jetzt zentral, unabhängig von der aktiven Ansicht
(siehe Abschnitt 7, Schritt 4). Der Fallback-Loader in `portfolioanalyse.py`
(Transferwissen #15) bleibt als zweites Netz — er ist jetzt aber selten der
aktive Pfad, weil die zentrale Bereitstellung schon greift.

> **Merksatz:** Nach dem Umbau jede Zeile prüfen, die per Seiteneffekt in
> `session_state` schreibt und von der ANDEREN Ansicht gelesen wird. Solche
> Zeilen gehören vor die Navigation.

#### Nebenwirkung B — Widget-Zustände der inaktiven Ansicht werden gelöscht

Streamlit LÖSCHT den `session_state`-Eintrag eines Widgets, sobald das
Widget in einem Run nicht gerendert wird. Wechsel Performance →
Portfolioanalyse → zurück ⇒ alle Häkchen/Selectboxen/Eingaben der
Performance-Ansicht stehen wieder auf Default.

**Lösung: Keep-Alive am Skriptanfang** — alle Keys einmal re-assignen, damit
sie als "per API gesetzt" gelten und das Nicht-Rendern überleben:

```python
# JEDER Button/Download-Button mit key= MUSS hier eingetragen werden.
_KEEPALIVE_SPERRE = {"pf_pptx_btn", "pf_pptx_dl", "p_zeit_reset"}
for _k in list(st.session_state.keys()):
    if _k in _KEEPALIVE_SPERRE:
        continue
    try:
        st.session_state[_k] = st.session_state[_k]
    except Exception:
        pass   # nicht setzbarer Key → bewusst überspringen
```

**Warum die Sperrliste zwingend ist — und das try/except NICHT reicht**
(korrigiert 11.08.2026): Hier stand bisher, das `try/except` fange künftige,
nicht gelistete Trigger-Keys defensiv ab. Das stimmt nicht. Die Zuweisung
`st.session_state["mein_knopf"] = …` läuft ohne Fehler durch — sie markiert
den Key lediglich als „per API gesetzt". Die Exception kommt erst später,
beim `st.button(key="mein_knopf")`, aus `check_session_state_rules`:
`StreamlitValueAssignmentNotAllowedError`. Die liegt außerhalb dieses `try`
und reißt die ganze Seite ab („Uncaught app execution"), wobei der Traceback
auf die Button-Zeile zeigt statt auf das Keep-Alive, das die Ursache ist.

Beim Einbau des Zurücksetzen-Knopfes am 11.08.2026 genau so eingetreten.
Die Liste ist also der Mechanismus, nicht die Dokumentation bekannter Fälle;
das `try/except` bleibt nur als Netz für andere nicht setzbare Keys.

**Offizielle Alternative (ab Streamlit ~1.59):** Einzelne Widgets haben einen
`persist_state`-Parameter (`"page"` / `"session"`, braucht `key`). Sauberer
für EINZELNE Widgets — das zentrale Keep-Alive-Loop deckt dagegen ALLE
Widgets mit einer Stelle ab. In diesem Projekt bewusst das Loop-Pattern
gewählt: minimaler Diff, keine Änderung an Dutzenden Widget-Aufrufen.

### 8.6 Die feste Reihenfolge in streamlit_app.py (und warum sie fest ist)

Aus den beiden Nebenwirkungen ergibt sich eine ZWINGENDE Reihenfolge (siehe
auch Abschnitt 7):

```
1. Login
2. Keep-Alive        ← muss VOR allen Widgets laufen (re-assignt deren Keys)
3. Sidebar (global)
4. Datenbereitstellung  ← muss VOR der Navigation laufen (Nebenwirkung A)
5. Navigation (segmented_control)
6. if aktive Ansicht == A: ... else: ...
```

**Wenn man das durcheinanderbringt:** Keep-Alive nach den Widgets → wirkungslos
(die Keys existieren beim Re-Assign noch nicht bzw. wurden schon gelöscht).
Datenbereitstellung nach der Navigation → PPTX-Export bricht bei Direkt-Einstieg
in die Portfolioanalyse. Beide Fehler sind subtil (kein Crash, nur falsches
Verhalten in bestimmten Klick-Pfaden) — deshalb ist die Reihenfolge hier
explizit dokumentiert.

### 8.7 Verifikation OHNE Deploy: AppTest (Transferwissen #24)

Der Bug lebt im Rerun-/State-Verhalten — genau das lässt sich mit Streamlits
`AppTest` headless und deterministisch beweisen, BEVOR man deployed. Zwei
Tests haben den Umbau abgesichert:

**Test 1 — der Bug-Fall selbst:**
```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_function(app); at.run()
at.session_state["nav_view"] = "Portfolioanalyse"; at.run()   # auf Ansicht B
at.selectbox(key="pf_sel_1").select("Strat Y").run()          # Selectbox-Rerun
assert at.session_state["nav_view"] == "Portfolioanalyse"     # bleibt B? ✓
```

**Test 2 — Keep-Alive:**
```python
at.checkbox(key="p_vk").uncheck().run()          # Widget in A verstellen
at.selectbox(key="p_sel1").select("P3").run()
at.session_state["nav_view"] = "Portfolioanalyse"; at.run()   # weg von A
at.selectbox(key="pf_sel_1").select("Strat Y").run()          # in B interagieren
at.session_state["nav_view"] = "Performance"; at.run()        # zurück zu A
assert at.checkbox(key="p_vk").value == False    # Wert erhalten? ✓
assert at.selectbox(key="p_sel1").value == "P3"  # Wert erhalten? ✓
```

Beide liefen unter EXAKT der Cloud-Version (Streamlit 1.59.0, per
`pip install streamlit` im Container installiert und `__version__` geprüft) —
nicht gegen eine ältere lokale Version, in der sich das Verhalten
unterscheiden könnte.

**Grenze (ehrlich benannt):** AppTest simuliert das Streamlit-PROTOKOLL, nicht
den Browser. Reine Frontend-Effekte (Material-Icons-Rendering #1,
LibreOffice-≠-PowerPoint #16) sieht es NICHT. Für State-/Rerun-Logik ist es
der schnellste harte Beweis; der echte Deploy bleibt der finale Prüfstein
(hier bestätigt).

### 8.8 Checkliste: st.tabs → keyed Navigation umbauen (Rezept zum Nachkochen)

Für den nächsten, der eine `st.tabs`-App gegen den Rücksprung-Bug härtet:

1. **Bug bestätigen, nicht raten.** Marker-Box (`st.success`) als erste Zeile
   jedes Tab-Bodies → beweist, welcher Body nach der Interaktion läuft. Wenn
   nach einer Selectbox-Auswahl in Tab 2 die Tab-1-Marker-Box erscheint, ist
   es dieser Bug.
2. **`st.tabs([...])` ersetzen** durch `st.segmented_control(..., key=...,
   required=True)` (oder `st.radio(..., horizontal=True, key=...)`).
3. **`with tab_x:` → `if ansicht == _VIEW_X:` / `else:`.** Einrückung
   beibehalten (Diff minimal, kein versehentliches De-Indent von 500 Zeilen).
4. **Nebenwirkung A prüfen:** Jede `session_state`-Schreibzeile suchen, die
   von der anderen Ansicht gelesen wird → VOR die Navigation ziehen.
5. **Nebenwirkung B behandeln:** Keep-Alive-Loop am Skriptanfang einfügen,
   Trigger-Widgets (Buttons/Downloads) per Sperrliste ausnehmen.
6. **`st.stop()`-Aufrufe prüfen:** Ein `st.stop()` in der einen Ansicht reißt
   jetzt nicht mehr die andere mit (positiver Nebeneffekt) — aber ein `stop`,
   der VOR der Navigation steht (z.B. in der zentralen Datenbereitstellung),
   legt weiterhin ALLES lahm. Fehlerbehandlung so bauen, dass ein Daten-Fehler
   nur die betroffene Ansicht stoppt, nicht die App.
7. **AppTest schreiben:** mindestens Test 1 (Bug-Fall) + Test 2 (Keep-Alive),
   gegen die reale Cloud-Version.
8. **Deploy + Marker-/TEST-Titel-Trick:** im echten Streamlit gegenprüfen.

### 8.9 Wiederverwendbare Kernaussagen (das, was in 6 Monaten zählt)

- **Layout ≠ Navigation.** `st.tabs`/`st.columns`/`st.expander` sind Layout;
  ihr "aktiver" Zustand ist Frontend und überlebt keinen Rerun. Navigation =
  keyed Input-Widget (`segmented_control`/`radio`) + `if/else`.
- **Jeder rerun-feste Zustand lebt im `session_state`.** Wenn ein Zustand
  nach einer Interaktion "vergessen" wird, ist die erste Frage: liegt er
  überhaupt im `session_state` oder nur im Frontend?
- **Bedingt gerenderte Widgets verlieren ihren State** — Keep-Alive oder
  `persist_state` einplanen, sobald nicht mehr alles bei jedem Run rendert.
- **"Immer nötige" Seiteneffekte gehören vor die Verzweigung**, sobald nur
  noch ein Zweig läuft.
- **AppTest beweist State-/Rerun-Verhalten vor dem Deploy** — gegen die reale
  Ziel-Version, nicht die lokale.

---

## 9. Disclaimers

| Ansicht | Schlüsselsatz |
|---|---|
| Performance | "Dieses Performancetool dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. Alle Berechnungen sind unverbindlich und erfolgen ohne Gewähr." |
| Portfolioanalyse | "Diese Portfolioanalyse dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. Alle Angaben sind ohne Gewähr." |

Quelle: Infront & eigene Berechnungen | Ansprechpartner: PBAM

---

## 10. Berechnungsformeln

```
daily_drag      = (1 + fee_pa)^(1/365) - 1
idx_nach_kosten = idx[i-1] * (1 + ret - daily_drag)
cagr            = (endwert/startwert)^(365/tage) - 1
vola            = std(tagesrenditen) * sqrt(365)
calmar          = cagr / |max_drawdown|
gew_duration    = Σ(gewicht × duration) / Σ(gewichte_anleihen)   ← aus Titeln, seit 03.07.
```

### Sharpe Ratio – nach Sharpe (1994), tägliche Excess Returns

```
daily_rf[t]   = (1 + rf_annual[t])^(1/365) - 1
excess[t]     = ret_port_nachKosten[t] - daily_rf[t]
sharpe_daily  = mean(excess) / std(excess, ddof=1)
sharpe_p.a.   = sharpe_daily × √365
```

Implementiert in `modules/analytics.py` (`calc_sharpe_excess`) — genutzt von App UND `compute_performance_data()` im Export.

### Risikofreier Zins – Aggregation (geometrisch) / rf-Index

```
daily_rf = (1 + rf_annual)^(1/365) - 1
growth   = Π (1 + daily_rf)
rf_pa    = growth^(365 / n_days) - 1
idx[i]   = idx[i-1] * (1 + daily_rf[i])
```

### Kostenmodell-Fußnote (dokumentiert, KEIN Bug)

Der additive Tages-Drag `(1+f)^(1/365)−1` ergibt bei Nullperformance eine
effektive Jahresbelastung von `f/(1+f)` (Beispiel: 1,19% → ~1,176%,
Δ ~0,014 %-Pkt/Jahr). Das ist marktüblich und entspricht dem freigegebenen
Disclaimer. Nur ändern als bewusste fachliche Entscheidung — es verschiebt
ALLE Nach-Kosten-Zahlen minimal.

---

## 11. PowerPoint-Export-System (Stand Juli 2026)

### 10.1 Vier-Modul-Architektur

```
pptx_helpers  (generisch: Shapes, Text, Tabellen, Slide remove/move/duplicate/reorder)
pptx_charts   (generisch: Chart-XML; replace_chart_data_safe = 4-Bug-Workaround,
               replace_chart_data XML-in-place für Ringe, set_date_axis_base_unit)
chart_dynamik (NEU 09.07.2026 — Nachbearbeitung fertiger Charts: Achsen datenbasiert,
               holeSize, Ring-Labels außen mit Strich; nachbearbeiten(prs), TW #26)
    ↑
pptx_slides   (Domain: fill_*_slide je Folie, Asset-Klassen-Logik, Tabellen-Layouts,
               generische Tabellen-Helfer (TW #27), EINZELTITEL_WARNUNGEN;
               kennt KEIN Streamlit)
    ↑
pptx_export   (Orchestrierung: N Strategien, template_config, Block-Dispatcher,
               compute_performance_data, compute_rollierend_data, LAST_BUILD_ERRORS;
               ruft nachbearbeiten(prs) VOR prs.save())
```

**Wichtig zur Einordnung:** `chart_dynamik` läuft **nach** allen `fill_*_slide`-Aufrufen
und arbeitet ausschließlich am Chart-XML der bereits befüllten Präsentation. Es ist
bewusst kein Teil von `pptx_charts` (das die Daten schreibt), sondern eine
Nachbearbeitungs-Schicht. Die Download-Logik (`download_helfer.py`) wird davon nicht
berührt.

Fehler bei der Befüllung einzelner Folien werden NICHT mehr still
verschluckt: `pptx_export.LAST_BUILD_ERRORS` sammelt sie, die App zeigt
sie nach dem Rerun an (rerun-feste Diagnose, Transferwissen #15).

### 10.2 Standard-Broschüre (`Vorlage_FFPB.pptx`, 26 Slides)

Dynamischer Block der Standard-Broschüre (Export-Reihenfolge):

| Folie (Export) | Rolle | Inhalt |
|---|---|---|
| 7 | Anlagevorschlag | Tabelle (Kapazitäts-Fix! s.u.) + Allokations-Ring |
| 8 | **Wertentwicklung/Kurzübersicht** (NEU 02.07.2026) | Titel, 4 Kennzahlen (kumulierte WE, Rendite p.a., WE seit 01.01., Duration), Balken (Perf p.a.), Linie (Wertentwicklung). Aus dem alten VBA-Tool per ZIP-Slide-Copy integriert; `fill_wertentwicklung_slide`, `we_data=None` → Platzhalter-Modus (nur Titel) |
| 9 | Performance (mit Benchmark) | Kennzahlen-Tabelle + Säulen- + Linien-Chart |
| 10 | Aktuelle Portfoliozusammenstellung | 2 Ring-Charts |

**F9-Änderungen (07/2026):** Balken zeigt zusätzlich das LAUFENDE Jahr
(YTD nK vs. BM; Schalter `F9_BAR_INCLUDE_CURRENT_YEAR` in pptx_export,
Default True) → F8/F9 sind nicht mehr datenidentisch; der 2026-Balken trägt
KEINE Sternchen-Markierung (Tool-UI-analog). Linien-Chart: datenbasierte
Achsen-Untergrenze über BEIDE Serien (statt Template-Fixwert 70%).
Quelle-Datumsfeld statisch (wie F8). Fußnote: Tool-Wortlaut via
`WE_DISCLAIMER_REPLACEMENTS` (läuft daten-UNABHÄNGIG, auch im
Platzhalter-Modus).

**Kapazitäts-Fix Anlagevorschlag-Tabelle (F7, Juni/Juli 2026):** Vorher
wurden bei >34 Datenzeilen überschüssige Zeilen STILL abgeschnitten —
Positionen verschwanden kommentarlos aus einem Compliance-Dokument. Jetzt:
`ensure_table_capacity()` klont bei Bedarf `<a:tr>`-Zeilen,
`fit_shape_to_table()` staucht alle Zeilen proportional (Untergrenze
`MIN_ROW_H_EMU`; reicht das nicht, schrumpft die Schrift bis `MIN_FONT_PT`).
Geometrie-Konstanten aus ECHTEN Exporten kalibriert
(ORIGINAL_DATA_ROW_H_EMU = 0.1424" × 914400, ORIGINAL_FONT_PT = 6.0,
MIN_ROW_H_INCH = 0.115, MIN_FONT_PT = 5.5, MAX_TABLE_BOTTOM_INCH = 6.60).
Realer Extremfall (35 Titel/39 Zeilen) braucht keine Schriftverkleinerung.
Nur im pathologischen Fall gibt es eine WARNUNG — NIE mehr stilles Verwerfen.

**Ring-Charts:** Nach einem matplotlib-PNG-Zwischenspiel (verworfen, weil
die PNGs sich im Deploy nie zuverlässig aktualisieren ließen und das
Template-Styling verloren ging) laufen die Donuts wieder NATIV über
`replace_chart_data` (XML-in-place, bugfrei) — Banner, Legende, Quelle,
Datenlabels der Vorlage bleiben unangetastet. `png_charts.py` ist gelöscht.

### 10.3 Themen-Broschüren (`Vorlage_Thema.pptx`, 21 Slides) — NEU 06.07.2026

Pro / Pro Dividende / Offensiv teilen sich EINE Vorlage + Struktur.
Dynamischer Block F10–F13 mit Rollen (verifiziert an der echten Vorlage_Pro):

| Folie (Vorlage) | Rolle | Inhalt |
|---|---|---|
| 10 | `einzeltitel_themen` | 7-Spalten-Tabelle (Wertpapier / Währung / WKN / Anteil), Gruppen AKTIEN/RENTEN/LIQUIDITÄT, `fill_einzeltitel_themen_slide`; Währung aus Daten_PF-Spalte "Währung"; Summenzeile "Gesamt" links, Prozentwert rechts |
| 11 | `zusammenstellung` | Ring-Charts (holeSize 79→55 für Lesbarkeit; ECHTE Außenbeschriftung ist bei PP-Doughnuts technisch NICHT möglich) |
| 12 | `wertentwicklung` | wie Standard-F8 |
| 13 | `rollierend` | Renditetabelle YTD/1/3/5/10 Jahre, nach Kosten, bit-identisch zur Streamlit-Rolltabelle (`compute_rollierend_data` + `fill_rollierend_slide`; <3 Jahre → "–") |

BEWUSST: keine Performance-Folie mit Benchmark in der Themen-Struktur.
Block-Reihenfolge pro Vorlage konfigurierbar via
`template_config["block_reihenfolge"]` (Default-Fallback = Standard).

**Steuerung (Variante A, familiengesteuert):** `VORLAGEN_FAMILIEN` in
`portfolioanalyse.py` mappt Familie → (Vorlagen-Datei, template_config).
Aktuell nur `"Thema"` eingetragen; CVV/ETF/ESG fallen sicher auf Standard
zurück, bis ihre Vorlagen existieren. Der Vorlagen-Pfad wird vom
funktionierenden Standard-`TEMPLATE_PATH` abgeleitet (gleicher Ordner wie
Vorlage_FFPB.pptx) — funktioniert damit in jeder Ausführungsumgebung.

### 10.4 Shape-Namen-Konvention

Die Vorlagen nutzen **benannte Shapes** — Namen müssen EXAKT stimmen:

| Folie | Shapes |
|---|---|
| Anlagevorschlag | `Titel`, `C_Kennzahlen` (Ring), `T_Kennzahlen` (Tabelle, "Marktrisikowert"-Header), `Fußnote`, `Quelle` |
| Performance | `Titel`, `Tabelle` (7×5: KENNZAHLEN/REFERENZ/BENCHMARK; Rows: Perf p.a., Vola, Sharpe, Max DD), `Diagramm links` (Säulen), `Diagramm rechts` (Linie), `Fußnote`, `Quelle` |
| Wertentwicklung / Themen-Folien | analoge benannte Shapes je `fill_*_slide` (siehe pptx_slides.py Docstrings) |

### 10.5 Strategienamen-Normalisierung

`clean_strategy_name()` entfernt: `cVV`, `Muster`, `Stiftung`.

### 10.6 Slide-Umbau

`_remove_slide` / `_move_slide` / `_duplicate_slide` in pptx_helpers. Regeln:
nach Duplikaten `_save_and_reload(prs)`; Reorder als EIN atomarer Schritt
(`_reorder_slides`) statt Move-Ketten. Quelle-Datums-Diskrepanz F7 vs. F8
ist KEIN Bug: strukturell verschiedene Datumsquellen (Auswertungsdatum der
Positions-CSV vs. Enddatum der Performance-Zeitreihe).

### 10.7 Performance-Daten-Befüllung

`compute_performance_data(timeseries_df, fee_dec)` in `pptx_export.py`
liefert Kennzahlen (CAGR, Vola, Sharpe, Max DD je für Referenz + Benchmark),
Säulen-Chart-Daten (Kalenderjahre + laufendes Jahr) und Linien-Chart-Daten
(gesamte Historie, Index Start=1.0). Die `performance_inputs` aus der App
enthalten zusätzlich je Strategie `duration` (aus den Titeln) und
`benchmark_text` (Mapping Spalte D, für die ***-Fußnote der F8; Platzhalter-
Werte wie "haben keine Benchmark" werden gefiltert).

**Korrektheits-Verifikation (03.07., Technik merken):** Kennzahlen
unabhängig aus der Chart-eigenen Index-Serie im Export nachgerechnet
(Stichtags-Verhältnisse) — YTD 2,7439% ≈ 2,74% ✓, kumuliert 184,01% ✓.

### 10.8 KONSISTENZ-DOKTRIN Tool ↔ PowerPoint (fachlich festgelegt, Philip 03.07.2026)

**Die PowerPoint ist kanonisch:** Sie rechnet IMMER volle Historie +
Standardsatz aus dem Mapping (× pf_mwst). Die Tool-Anzeige DARF davon
abweichen (Datumsfilter, Vergleichs-INNER-JOIN auf gemeinsamen Zeitraum,
editierbarer Kostensatz, eigenes MwSt-Häkchen je Ansicht) — das ist GEWOLLT
und wird seit 03.07. per Info-Caption über den Kennzahlen sichtbar gemacht
(benennt jede aktive Abweichung, erinnert ans MwSt-Häkchen-Gleichstellen).
Beide Pfade nutzen identische `analytics`-Funktionen: bei gleichen Eingaben
bit-identisch (bewiesen). YTD überall ab Vorjahres-Schlussstand.

### 10.9 Compliance-Anforderungen (nicht verhandelbar — PPTX geht an Kunden)

| Anforderung | Umsetzung |
|---|---|
| **Anti-Cherry-Picking** | Performance-Folien zeigen **die gesamte verfügbare Historie** |
| **Benchmark wenn gemappt** | BM **immer** angezeigt (UI-Schalter ignoriert) |
| **Nur Nach Kosten** | "Vor Kosten"-Linien werden im Export **nie** gezeigt |
| **Strategieentwurf-Hinweis** | Folie 7: "Strategieentwurf im Rahmen einer Vermögensverwaltung" |
| **Disclaimer auf jeder Folie** | Standard-Wertentwicklungs-Disclaimer + Quelle + Stand |
| **Mindestens 5 Jahre Historie** | Durch "gesamte Historie zeigen" implizit erfüllt |
| **Strategienamen-Bereinigung** | `cVV`, `Muster`, `Stiftung` werden entfernt |
| **Keine stillen Datenverluste** | Kapazitäts-Fix F7 + `LAST_BUILD_ERRORS`-Diagnosen |

---

## 12. PowerPoint-Vorlage Recipe — Neuaufbau/Slide-Import aus Quell-PPTX

Das vollständige 8-Phasen-Recipe (Basis kopieren → Slide-Import mit
Pfad-Mapping → .rels aktualisieren → presentation.xml → slideMaster →
ContentTypes → PNG→JPEG → ZIP) steht in **Transferwissen #14** und wurde
in diesem Projekt ZWEIMAL erfolgreich angewendet:

1. **Juni 2026 (v7):** Standard-Vorlage sauber neu gebaut aus Original +
   `Anlagevorschlag_Master_Dynamische_Folien.pptx` (Performance-Folie);
   19 PNGs → JPEG; 22,7 MB → 4,14 MB; 25 Slides, 0 XML-Fehler,
   Generierung 0,6s. Post-Build-Mods: "AKTUELLE STRUKTUR",
   "Marktrisikowert"-Header, Linien-Y-Alignment (EMU; 914400 EMU = 1 Zoll).
2. **Juli 2026:** Wertentwicklungs-Folie (aus dem alten VBA-Tool) in die
   Standard-Vorlage integriert → **26 Slides**; außerdem
   `Vorlage_Thema.pptx` bild-optimiert (24 MB → 3,95 MB, Transferwissen #13).

**Regeln bei Vorlage-Updates:**
- Original-Vorlagen immer als Master archivieren
- Bei "Vorlage scheint kaputt": lieber neu aufbauen statt reparieren
- Shape-Namen müssen exakt stimmen
- Große .pptx im GitHub NIE per Web-UI umbenennen (Transferwissen #23) —
  immer frisch hochladen, danach Dateigröße im Repo prüfen

---

## 13. Lokaler Batch `erstelle_broschueren.py` (Stand: NICHT IM REPO — Bauplan)

**Zweck:** Massen-Erzeugung der Broschüren OHNE Streamlit/Cloud — z.B. alle
Strategien einer Familie in einem Lauf, lokal, reproduzierbar.

**Architektur:**
- `modules/dataload.py`: streamlit-freie KOPIEN der Loader
  (`detect_newest_date_tag`, `load_all_csvs`, `build_portfolio_timeseries`).
  Bewusst KEIN Import aus `modules.shared` (das importiert Streamlit).
  Abhängigkeiten nur: pandas, numpy, python-pptx, openpyxl, lxml.
- `VORLAGEN`-Konfiguration je Familie: Pfad, erwartete_folien,
  block_positionen, entfernen, Modus (`zusammen` = eine Datei mit allen
  Strategien / `einzeln` = eine Datei je Strategie), Dateiname.
- Nutzt dieselbe `pptx_export`-Logik wie die App (Konsistenz), inkl.
  Multi-Layer-Validierung (`validiere_pptx`) je erzeugter Datei.

**Bewiesen (Juli 2026):** Kompletter Batch-Lauf mit HART blockiertem
Streamlit-Import → identische Ergebnisse (CVV 28 Folien, Kennzahlen
befüllt, 0 Build-Errors).

**Status (korrigiert 07.08.2026): NICHT IM REPO.** Weder
`erstelle_broschueren.py` noch `modules/dataload.py` wurden je committet — ein
`git log` über beide Pfade ist leer. Frühere Fassungen dieser Doku führten sie
in den Abschnitten 1, 2, 3 und 17 als vorhanden auf; das stimmte nie. Die
Dateien existierten nur lokal bzw. in Chatverläufen und sind damit praktisch
verloren.

Die Beschreibung oben bleibt bewusst als **Bauplan** stehen, falls der Batch
neu gebaut werden soll. Zwei Dinge wären dann anders zu machen:
- `dataload.py` als Kopien anzulegen war der Umgehung von `import streamlit`
  in `shared.py` geschuldet. Besser: die Loader in ein streamlit-freies Modul
  ziehen, das BEIDE nutzen — sonst entsteht dieselbe Doppel-Wahrheit, die am
  07.08.2026 in `streamlit_app.py` beseitigt wurde.
- Duration aus den Titeln rechnen (`duration_info_aus_bestand`), nicht aus dem
  gelöschten Duration-Ordner (Backlog Punkt 2).

Der ursprüngliche Grund für die Pause gilt weiter: Die Firmen-IT lässt lokale
Paket-Installationen kaum zu (Stand 07.08.2026 fehlen lokal `streamlit`,
`plotly`, `python-pptx` und `reportlab`; vorhanden sind pandas, numpy,
matplotlib, lxml, openpyxl, Pillow). **Folge für die Arbeitsweise:** Nur
streamlit-freie Module lassen sich lokal testen — Änderungen am PPTX-Export
müssen im Deploy geprüft werden.

---

## 14. Download-Problem Firmen-Gateway (GELÖST 07.07.2026 — clientseitiger Blob-Download)

Der PowerPoint-Download aus der Streamlit-Cloud scheiterte firmenseitig am
**Atruvia Secure Web Gateway / Skyhigh** (Regel "Block If Virus was Found") —
statt der Datei kam eine `progress.htm`. Ursache: JEDER Download, der die
Datei vom Server holt, läuft durch den Scanner, der die Verbindung hält.

**Gelöst per clientseitigem Blob-Download** (Transferwissen #25, ausführlich
dort): Die PPTX-Bytes werden als Base64 in die Seite eingebettet, ein Button
baut die Datei im Browser lokal zusammen (`Blob` + `<a download>`) und
speichert sie — **ohne Netzwerk-Request**, den das Gateway scannen könnte.
Umgesetzt in `modules/download_helfer.py` → `download_bereich()` über
`st.components.v1.html` (dessen iframe erlaubt Downloads). Im Deploy bestätigt
funktionsfähig.

Verworfene Sackgassen (alle waren Server-Abrufe → Scan hängt): klassischer
`st.download_button`, neuer Tab auf die interne Media-URL `/media/…` (bootet
auf Community Cloud die App neu), neuer Tab auf Static Serving `/app/static/…`.
Details + Code-Muster in Transferwissen #25.

Langfristig bleibt **internes Hosting** sinnvoll (löst auch das
Cloud-Update-Problem, siehe Backlog) — für den Download ist es aber nicht
mehr nötig.

---

## 15. Backlog (Stand 12.08.2026, nach Priorität)

**Stand 12.08.2026 (abends) — was wirklich noch offen ist:** **G**
(Anlagekriterien SCHWEIZ) und **H** (comdirect-Disclaimer), beide von Philip
am 12.08.2026 ausdrücklich **zurückgestellt** — sie warten auf eine
fachliche Entscheidung, nicht auf Arbeit; die technische Analyse steht
jeweils unten und muss nicht wiederholt werden. Dazu **8–10** (internes
Hosting, Alt-Aufgaben aus Phase 2, Varianten). Alles andere ist
abgeschlossen; die Punkte bleiben durchgestrichen stehen, weil die
Begründungen mehr wert sind als die Aufgaben.

Sämtliche **Sichtprüfungen in echtem PowerPoint sind erledigt** (Philip,
12.08.2026): SCHWEIZ, Datumsachse, Wertachse und Quellenangabe — jede
Korrektur am Endprodukt bestätigt.

- **H. Der comdirect-Disclaimer beschreibt noch die alte Kostenregel**
  *(neu 12.08.2026, FACHLICH — Entscheidung Philip)*. Aufgefallen beim
  Vorher/Nachher-Vergleich zur Quelle-Korrektur: Von 15 Folien änderten
  sich die Disclaimer-Absätze nur auf 12. Die drei comdirect-Folien
  blieben unberührt — und tragen deshalb weiterhin den **Vorlagentext**:

  > „Der unterjährige Performance-Ausweis erfolgt vor Kosten (ab 30.06.
  > abzüglich des halbjährigen Honorarsatzes)."

  Das ist seit Juli 2026 **nicht mehr richtig**: Gerechnet wird nach
  Kosten mit taggenauem Honorarabzug. Genau diesen Satz ersetzt
  `WE_DISCLAIMER_REPLACEMENTS` in allen anderen Vorlagen.

  **Ursache — ein Bindestrich.** Der Präfix-Anker lautet
  `"Der unterjährige Performance Ausweis"`; `Vorlage_comdirect.pptx`
  schreibt „Performance**-**Ausweis". Der Präfix matcht nicht, die
  Ersetzung läuft ins Leere — **ohne Fehler, ohne Meldung**, genau wie
  das fehlende `majorTimeUnit` bei #49. Der zweite Anker
  (`"Kosten berechnet."`) greift ebenfalls nicht: comdirect führt den
  ganzen Disclaimer als **einen** Absatz, der Anker sitzt dort mitten im
  Satz statt am Absatzanfang.

  Damit steht in einem Kundendokument eine **falsche Aussage über die
  Kostenberechnung** — dieselbe Klasse wie die SCHWEIZ-Fußnote (#46),
  und deshalb nicht nur kosmetisch (§10.9). Verschärfend: Die `*`- und
  `**`-Zeilen **wurden** ersetzt (ihre Anker passen). Dieselbe Fußnote
  sagt oben „nach Kosten (taggenauer Honorarabzug)" und unten „vor Kosten
  (ab 30.06. abzüglich des halbjährigen Honorarsatzes)" — sie widerspricht
  sich also selbst.

  **Warum nicht sofort behoben:** Die Korrektur ändert einen
  Compliance-Text und ist keine reine Technikfrage. Zwei Wege:
  (a) die Anker toleranter machen (z. B. auf „Der unterjährige
  Performance" kürzen) — greift dann aber nur für den ersten Satz, weil
  comdirect einen einzigen Absatz hat; (b) den Vorlagentext in
  `Vorlage_comdirect.pptx` angleichen, dann greifen die vorhandenen Anker
  wie überall. **(b) ist der saubere Weg** und entspricht der Regel
  „statischer Vorlagentext gehört in die Vorlage" (CLAUDE.md).

  Prüfstein, der so etwas künftig findet: fehlt noch. Ein Test „nach dem
  Befüllen enthält keine Fußnote mehr den Wortlaut der alten Kostenregel"
  wäre für alle sechs Vorlagen in wenigen Zeilen zu haben.

- **G. Anlagekriterien für die beiden SCHWEIZ-Strategien** *(neu 12.08.2026)*.
  Seit heute sind 17 der 19 Strategien in `Mapping_Anlagekriterien.xlsx`
  erfasst; `Schweiz_substanzorientiert` und `Schweiz_aktienorientiert` fehlen.
  **Sie stehen bewusst nicht auf der Webseite** (Philip) — die Werte müssen
  aus dem Haus kommen (Vermögensverwaltungsvertrag, Factsheet o. ä.). Bis
  dahin zeigt das Tool dort korrekt keinen Banner; `anlagekriterien_fuer`
  liefert `[]`. Zum Eintragen: die vier Felder in die Excel, dann in
  `tests/test_anlagekriterien.py` die Liste `NOCH_OFFEN` leeren — der Test
  weist mit einem HINWEIS darauf hin, sobald Werte auftauchen.

E, F und der Wrapper-Block in `streamlit_app.py` waren **dieselbe
Krankheit** — eine Funktion, die zweimal existiert und deren Kopien
auseinanderlaufen — und wurden deshalb in einem Zug erledigt. Der Befund
daraus: Von den vier Fällen dieser Woche (B, E, F, Wrapper) war **keiner**
durch unterschiedliche Formeln aufgefallen, sondern immer erst dadurch, dass
jemand die Kopien nebeneinandergelegt hat. Zwei davon liefen bereits
auseinander, ohne dass es jemand bemerkt hatte: die Honorarsätze der
SCHWEIZ-Strategien (11.08.) und `fmt_date_de` (12.08.).

**Am 07.08.2026 erledigt:** Punkt 5 (`generate_pf_pdf` entfernt), Punkt 6
(`enableStaticServing` + `medien_download_url` entfernt), Teile von Punkt 1
(`lxml` ergänzt, `python-pptx` angehoben; streamlit war bereits gepinnt).

**Neu aufgenommen (aus dem Code-Review vom 07.08.2026):**

- ~~**A. Benchmark-Serie auch aus den PPTX-Charts nehmen.**~~ — **erledigt
  11.08.2026**, siehe Transferwissen **#46**. Der Befund war größer als hier
  beschrieben: Die flache Linie gab es auf der Themen-Folie gar nicht, dafür
  standen Legendeneintrag und ***-Fußnote noch da — letztere mit dem
  unveränderten Vorlagentext, also der Benchmark einer FREMDEN Strategie.
- ~~**B. Die zwei verbliebenen Mathe-Helfer in `pptx_export.py`**~~ —
  **erledigt 12.08.2026.** `_annual_fee_to_daily_drag` und
  `_make_index_after_fee` sind entfallen, beide kommen jetzt aus `analytics`.
  Die Sorge „das berührt `compute_wertentwicklung_data`" war unbegründet: die
  analytics-Fassungen sind formelgleich und durch `np.asarray` sogar
  toleranter bei der Eingabe. Beweis der Wirkungsgleichheit: alle sieben
  Broschüren vorher/nachher rekursiv verglichen — 2056 ZIP-Einträge, 34
  Abweichungen, ausnahmslos `docProps/core.xml`. Prüfstein
  `tests/test_kosten_mathematik.py`.
- ~~**C. Der Wrapper-Block in `pptx_export.py`**~~ — **erledigt 11.08.2026**
  (−292 Zeilen, 1303 → 1010). Die Warnung „viele Aufrufstellen" war falsch:
  27 der 40 Wrapper wurden NIRGENDS aufgerufen, die übrigen 13 an je einer
  bis drei Stellen, alle in derselben Datei. Vor dem Umbau erst zählen, dann
  schätzen. Beweis der Wirkungsgleichheit: alle sieben Broschüren vorher/
  nachher rekursiv verglichen — von 2056 ZIP-Einträgen unterschieden sich 34,
  ausnahmslos `docProps/core.xml` (Erzeugungs-Zeitstempel).
  ~~**Gleichartiger Block in `streamlit_app.py` bleibt**~~ — **auch erledigt,
  12.08.2026.** Es waren **zehn** Durchreicher, nicht sieben: Drei standen
  nicht im Block oben, sondern verstreut weiter unten (`calc_sharpe_excess`,
  `calc_period_return`, `calc_period_return_after_fee`). Einer war tot
  (`annual_fee_to_daily_drag`), die übrigen neun hingen an 25 Aufrufstellen.
  Ertrag deshalb nur **−4 Zeilen netto** — an die Stelle der Attrappen ist
  eine Erklärung getreten, warum dort jetzt nur noch UI-spezifische Helfer
  stehen. Gemacht wurde es trotzdem, aus demselben Grund wie bei den 40:
  Eine Attrappe mit dem Namen einer echten Funktion führt die Suche in die
  Irre. Beweis siehe Changelog (AppTest-Dump, zeichengleich).
- ~~**E. Die rf-Tagessatz-Umrechnung steht dreifach**~~ — **erledigt
  12.08.2026.** Es waren sogar vier Stellen (`annual_fee_to_daily_drag`,
  `calc_sharpe_excess`, `aggregate_rf_geometric`, `make_index_from_rf`).
  Neu: `analytics.annual_to_daily_rate(annual_rate)`, nimmt Einzelwert oder
  Reihe. **`annual_fee_to_daily_drag` behält seinen eigenen Namen** und ruft
  die neue Funktion nur auf: Die Mathematik ist identisch, die Größen sind es
  nicht — ein Honorar wird abgezogen, ein Zins gutgeschrieben, und wer
  `annual_to_daily_rate(fee)` liest, sieht dem Aufruf das Vorzeichen nicht
  mehr an. Vorab nachgemessen, dass der Weg über `np.asarray`
  **bit-identisch** ist; Broschüren unverändert. Prüfstein:
  `tests/test_analytics.py`, Schritt 6.
- ~~**D. Testabdeckung ausbauen.**~~ — **erledigt 12.08.2026.**
  `tests/test_analytics.py` (Bausteine gegen von Hand nachrechenbare Werte,
  degenerierte Eingaben, `has_benchmark`, der Vertrag von
  `compute_performance_data`) und `tests/test_formats.py` (deutsche Notation,
  Fehlwerte, Datum, Disclaimer-Anker). Beide brauchen kein Streamlit,
  `test_formats` gar keine Installation. Die Runde hat **drei Fehler
  gefunden** — siehe Transferwissen **#47**; alle drei kamen aus
  degenerierten Eingaben, keiner aus den fachlich interessanten Fällen.
- ~~**F. `fmt_date_de` existiert zweimal — und die beiden verhalten sich
  unterschiedlich**~~ — **erledigt 12.08.2026.** `shared.py` reicht
  `fmt_date_de` und `fmt_pct_de` jetzt aus `formats.py` durch (als Zuweisung,
  damit das Weiterreichen sichtbar ist und pyflakes die Namen nicht für
  unbenutzt hält — es kennt kein `noqa`). `fmt_eur_de` bleibt lokal, weil die
  Broschüre keine Beträge ausweist, verhält sich bei Fehlwerten aber jetzt
  genauso. Prüfstein: `tests/test_formats.py`, Schritt 7. Der Befund, der
  dazu führte:

  | Eingabe | `formats` | `shared` |
  |---|---|---|
  | `None` | `–` | `'None'` |
  | `pd.NaT` | `–` | **ValueError** |
  | `float('nan')` | `–` | `'nan'` |

  Dieselbe Bauart wie Backlog B, nur bei der Formatierung statt der
  Mathematik: Die eine Fassung wurde gehärtet, die andere nicht. `shared`
  wird von `streamlit_app.py` an rund 15 Stellen benutzt (Auflagedatum,
  Drawdown-Daten, Quelle-Zeile) — ein `NaT` dort **stürzt die Ansicht ab**.
  Auch `shared.fmt_pct_de(None)` wirft, wo `formats.fmt_pct` ein `–` liefert.
  Vorgehen: `shared` auf die `formats`-Fassung umstellen (nicht umgekehrt),
  vorher prüfen, wo heute bewusst `str(d)` durchgereicht wird.

1. ~~**requirements.txt Python-3.14-kompatibel pinnen**~~ — **erledigt
   11.08.2026.** Jede Zeile hat jetzt eine Obergrenze auf die nächste
   Hauptversion, Untergrenze ist der nachweislich laufende Stand. Bewusst
   keine `==`-Pins: die waren am 06.07. der zweite Fehlschlag (Details in
   Transferwissen #20, Punkt 4). Verifiziert per `pip install --dry-run
   --ignore-installed` — die Auflösung landet exakt auf dem getesteten Satz.
   **Offen bleibt nur die Bestätigung im Deploy-Log** (Cloud = Python 3.14,
   lokal geprüft wurde unter 3.12).
2. ~~**Duration-Inkonsistenz Batch vs. App**~~ — **gegenstandslos (07.08.2026):**
   Der Batch existiert nicht im Repo (siehe Abschnitt 13), es gibt also keine
   zweite Implementierung, die abweichen könnte. Die App rechnet Duration und
   Rendite seit 03.07. anleihe-gewichtet aus den Titeln
   (`duration_info_aus_bestand` → `get_bond_summary`). **Falls der Batch neu
   gebaut wird:** diese Berechnung vorher in ein streamlit-freies Modul ziehen,
   damit beide dieselbe nutzen — nicht wieder kopieren.
3. ~~**Spalte "Währung" in Daten_PF**~~ — **erledigt, bestätigt 12.08.2026.**
   Philip hat sie nachgeliefert; **alle 38 CSVs** in `Daten_PF` führen die
   Spalte, `pptx_slides.py:739` liest sie aus, und die Einzeltitel-Tabelle ist
   gesichtet. Der Punkt stand nur noch aus Trägheit hier.
4. ~~**Vorlagen-Familien ESG/CVV/ETF anlegen + kalibrieren**~~ — **erledigt,
   bestätigt 12.08.2026.** Alle sechs Vorlagen liegen in `Vorlage/`, alle vier
   Familien mit eigener Vorlage haben ihre Konfiguration in
   `VORLAGEN_FAMILIEN`, und `Mapping_Namen.xlsx` ordnet **alle 19 Strategien**
   einer Familie zu — keine Lücke (CVV 5, Thema 5, ESG 4, comdirect 3, ETF 2).
   Die Sichtprüfung je Familie hat stattgefunden. `tests/test_export_smoke.py`
   baut für jede Familie eine echte Broschüre und hält den Stand.
5. ~~**`generate_pf_pdf` toter Code**~~ — erledigt 07.08.2026.
6. ~~**Download-Toten-Code aufräumen**~~ — erledigt 07.08.2026, **nachgeprüft
   12.08.2026:** weder `enableStaticServing` in `.streamlit/config.toml` noch
   `medien_download_url` in den Modulen sind noch vorhanden. Der Punkt stand
   fälschlich weiter unter den offenen.
7. **`use_container_width` → `width` migrieren:** Streamlit 1.59 warnt bei
   JEDEM Aufruf (flutet das Deploy-Log) und entfernt den Parameter in einem
   künftigen Update → dann bricht die App (dieselbe Auto-Update-Falle wie
   #20). Sweep über alle Dateien: `use_container_width=True` → `width="stretch"`,
   `False` → `width="content"`.
7a. ~~**`pyflakes` über das ganze Repo ist nicht sauber**~~ — **erledigt
   12.08.2026, 16 Meldungen auf 0.** Keine war ein Laufzeitfehler, aber zwei
   verwiesen auf echte Geschichte (siehe Changelog): die tote
   `holeSize`-Kette in beiden Ring-Funktionen und ein `is_bond`, das einmal
   zwei Abfragen steuerte. Broschüren byte-identisch, `ui_dump` zeichengleich,
   alle 16 Suiten grün. **Der Wert liegt nicht im Aufgeräumten, sondern
   darin, dass `pyflakes` ab jetzt wieder gelesen wird** — eine Prüfung mit
   16 bekannten Meldungen sieht sich niemand an.
8. **Internes Hosting evaluieren** (löst Cloud-Update-Fallen dauerhaft; für
   den Download seit #25 NICHT mehr nötig).
9. **Alt-Aufgaben aus Phase 2 — Status prüfen:** PDF-Seitenzahlen
   (Position-Spec stand aus) und dynamische PPTX-Seitenzahlen. Ob sie noch
   gewünscht sind, ist offen — vor Umsetzung mit Philip klären.
10. Ggf. F2/F3-Varianten der Performance-Folie (ohne BM / Berater-Zeitraum);
    Sharpe + rf-Linie auch in der Portfolioanalyse; Portfolio-Builder-
    Reaktivierung bei Bedarf.

---

## 16. Changelog

### 18.08.2026 (Stufe 3) – Theme fürs ganze Werkzeug, Drilldown, Designsprache

Aus Philips Sichtprüfung: „das Rot leuchtet" an den Auswahl-Chips, und der
Wunsch nach einem Drilldown auf die gemeinsamen Einzeltitel.

**DAS ROT WAR NIE EINE ENTSCHEIDUNG.** `.streamlit/config.toml` hatte keinen
`[theme]`-Abschnitt; die App lief seit jeher mit Streamlits Standardakzent
`#FF4B4B` — auf Chips, Kontrollkästchen, Fokusrahmen, aktiven Segmenten und
Links, in allen drei Ansichten. Jetzt Fuggerblau `#003460` (hell) und
Hellblau `#7FABC8` (dunkel), `baseRadius = "small"`, und die Schrift kommt
über `theme.font` statt über einen CSS-Block mit `!important`. `theme.base`
bleibt ungesetzt, damit hell und dunkel beide brauchbar bleiben.
Transferwissen **#63**.

**Neuer Prüfstein `tests/test_theme.py`**, und er prüft nicht den Inhalt der
Datei, sondern ob **Streamlit sie liest**: `config.get_where_defined` muss auf
`.streamlit/config.toml` zeigen und nicht auf `<default>`. Ein Inhaltstest
hätte den Fehler von #23 nicht gefunden — die Datei war richtig, sie wurde
nur ignoriert.

**DRILLDOWN.** Ein Klick auf einen Balken der Überschneidung öffnet die
Aufstellung: welche Titel, mit welchem Gewicht in beiden Depots, und der
gemeinsame Anteil als Balken. Ohne Klick steht die stärkste Überschneidung da
— es gibt keinen leeren Zustand. Die Zusage: Die Summe der Einzelbeiträge ist
exakt die Überschneidung der Übersicht, über **855 Paar-Ebenen-Kombinationen**
gemessen, größte Abweichung **1,1e−16**.

Der Beitragsbalken ist **Text und keine `ProgressColumn`**: Streamlits
Spaltenformate formatieren ihre Zahlen selbst, englisch oder nach der
Browser-Locale — das wäre eine zweite Formatierungsquelle neben
`modules/formats.py`.

**Zwei eingeplante Fallen, beide gemessen:** Das Keep-Alive stürzt am Chart
mit `on_select` **nicht** ab (vier Läufe samt Ansichtswechsel geprüft),
`sv_ue_chart` muss also *nicht* in `_KEEPALIVE_SPERRE`. Und die Auswahl wird
über den **Namen** aufgelöst, nicht über den Index — nach einem Ebenenwechsel
zeigte derselbe Balkenindex sonst auf eine andere Strategie (#53).

**DESIGNSPRACHE:** drei einzelne Captions zu einem Hinweisblock, kurzer
Achsentitel, nur der Prozentwert am Balken, Honorar-Hinweis in den `help` des
Zeitraum-Feldes, das Kontrollkästchen „Tabelle anzeigen" der Überschneidung
entfällt (der Drilldown ist die Tabelle). Der **Wortlaut der Vorbehalte ist
unverändert** — er wurde ausdrücklich als verständlich abgenommen.

**Beweise:** 25 von 25 Suiten grün, `pyflakes` über 44 Dateien null,
`ui_dump` für Performance und Portfolioanalyse mit **genau einer** geänderten
Zeile — dem entfernten `<style>`-Block. Der Export-Pfad ist unberührt.

**Was hier nicht bewiesen werden kann:** `ui_dump` sieht keine Farben und
keine Schriften. Ob die Streamlit-Icons den Wechsel auf `theme.font`
überstehen und ob die Bedienelemente noch bedienbar wirken, kann allein die
Sichtprüfung sagen — in hell und dunkel.

### 18.08.2026 (Stufe 2) – Überschneidung und Exposure im Strategievergleich

Der dritte Tab hat zwei Abschnitte dazubekommen, untereinander gestapelt; die
Strategieauswahl oben gilt für alle drei. Dazu ist der Umschalter der
Punktwolke von `st.radio` auf `st.segmented_control` umgestellt — die Heatmap
schaltet ihre zwei Ansichten genauso um, und zwei Bauformen für dieselbe
Aufgabe sehen ungleichmäßig aus (Philip). `required=True` ist dabei nicht
Kosmetik: Ohne ihn ließe sich das aktive Segment abwählen.

**Überschneidung** = Σ min(w_A, w_B), die Gegengröße zur Active Share. Fokus
auf eine Bezugsstrategie, dagegen alle anderen als sortierte Balken, fünf
Ebenen. Zwei Vorbehalte stehen als Caption dabei: Die Ebenen sind nicht
vergleichbar (dasselbe Paar 20,5 % auf Titel-, 73,8 % auf Gattungsebene), und
100 % sind unerreichbar, weil die Titelgewichte nur 88,8 bis 98,2 % ausmachen.
Transferwissen **#62**.

**Exposure** als gestapelte 100-%-Balken über Gattung, Region, Währung und
Segment innerhalb einer Gattung. Liquidität als eigenes Segment ausgewiesen.
Segment nur innerhalb einer Gattung, weil die Spalte zwei Bedeutungen trägt
(„Financials" = 23 Renten-, „Banken, Versicherer, Finanzdienstl." = 42
Aktienpositionen). Region mit Look-through-Vorbehalt.

**Der Marktrisikowert war gebaut und ist wieder ausgebaut** (Philip): Das
Haus legt ihn im Asset Management selbst fest; im Beratungswerkzeug sähe er
neben gemessenen Größen aus wie eine Beobachtung. Ein Testschritt hält die
Entscheidung fest, weil die Spalte in den Daten bleibt.

**Neues Modul `modules/bestandsanalytik.py`, streamlit-frei.** `analytics.py`
trägt die Mathematik der Zeitreihen; was auf den Einzeltiteln eines Stichtags
rechnet, hat jetzt einen eigenen oberflächenfreien Ort. `calc_liquidity` ist
aus `portfolioanalyse.py` dorthin umgezogen (drei Verbraucher) und wird dort
per Zuweisung weitergereicht.

**Beweise:** 24 von 24 Suiten grün ohne übersprungenen Schritt, `pyflakes`
über 43 Dateien bei null, `ui_dump` für Performance und Portfolioanalyse
**zeichengleich**, und — weil `calc_liquidity` im Export-Pfad läuft — sieben
Broschüren vorher/nachher rekursiv verglichen: **2056 ZIP-Einträge, 0
inhaltliche Abweichungen**.

**Drei eigene Fehler, alle durch Messen gefunden:** eine erfundene Zahl in der
Planung (9 statt der gemessenen 5 gemeinsamen Titel), ein Fehlwert-Filter, der
nur zufällig griff, und eine Gegenprobe, die nicht naiv genug war, weil
pandas 3.0 NA-Schlüssel selbst verwirft.

### 18.08.2026 – Dritter Tab: der Strategievergleich (Risiko-Rendite-Punktwolke)

**Neu:** ein drittes Segment in der Navigation. Jede Strategie ist ein Punkt —
Y = Rendite p.a. nach Kosten, X = **Volatilität oder Max Drawdown**
(Umschalter wie bei der Heatmap), Farbe = Familie, Auswahl über
Familien-Mehrfachfeld oder einzeln. **Ausdrücklich keine Effizienzlinie nach
Markowitz** (Philip): Die Ansicht positioniert, sie optimiert nicht — ein
Kunde bekommt eine Vermögensverwaltung, keinen Mix aus dreien (§10.9).

**Der Aufwand lag im Zeitraum, nicht in der Darstellung.** Historien von 1,7
bis 17,6 Jahren verschieben die Rangfolge um bis zu zehn Plätze (cVV dynamic
4 → 14, cVV ausgewogen 11 → 5). Festgelegt: gemeinsames Fenster, und wer es
nicht abdeckt, wird namentlich genannt statt gezeichnet. „Seit Auflage" gibt
es hier deshalb nicht — an seiner Stelle steht der **längste gemeinsame
Zeitraum der Auswahl**. Transferwissen **#61**.

**Gebaut werden musste eine einzige Größe:** die Spalte `rendite` in
`analytics.risiko_perioden`. Volatilität, Max Drawdown **und die
Abdeckungsregel** standen dort seit dem 14.08.2026 schon. Rendite und
Drawdown kommen aus **derselben Indexreihe**, damit die beiden Achsen eines
Punktes nicht auseinanderlaufen können.

**Dateien:** `modules/strategievergleich.py` (neu),
`tests/test_strategievergleich.py` (neu), `modules/analytics.py` (+18/−4),
`streamlit_app.py` (drittes Segment, `elif`-Zweig, Honorarsatz-Warnung),
`modules/portfolioanalyse.py` (**nur** eine Namenszuweisung
`familie_fuer_strategie` — acht Kommentarzeilen und eine Zeile Code, kein
Verhalten), `tests/ui_dump.py` (dritte Ansicht).

**Beweise:** 23 von 23 Suiten grün ohne übersprungenen Schritt, `pyflakes`
über 41 Dateien bei null, `ui_dump` für Performance und Portfolioanalyse
vorher/nachher **zeichengleich**, Punktwolke gegen Kennzahlen-Kachel über 19
Strategien × 3 Kennzahlen mit größter Abweichung **0,000e+00** (ebenso über
das gemeinsame Fenster). Der Broschüren-Pfad ist unberührt: `risiko_perioden`
hat genau zwei Verbraucher, `risiko_ansicht` und `strategievergleich`, keiner
davon im Export.

**Zwei eigene Fehler, beide durch Messen gefunden.** Die Vorbelegung stand auf
dem gemeinsamen Zeitraum — der erste AppTest zeigte, dass das über alle 19
Strategien **1,7 Jahre** sind; sie steht jetzt auf „3 Jahre". Und die
Erwartung eines Grenzfalls im Prüfstein war von Hand falsch gerechnet;
richtig ist die allgemeinere Invariante aus #61.

**Nachgezogen am selben Tag (Philip):** Die Strategienamen stehen **immer**
am Punkt. Die erste Fassung ließ sie ab 13 Punkten in den Hover wandern; im
Kundengespräch wird auf den Bildschirm gezeigt, nicht mit der Maus darüber
gefahren. Die Konstante `NAMEN_BIS` ist entfallen, ein Testschritt hält die
Entscheidung fest, und `cliponaxis=False` verhindert, dass der äußerste Punkt
seine Beschriftung an der Zeichenfläche verliert. Die Überdeckung wurde
nachgemessen: bei der Vorbelegung 2 kollidierende Namenspaare von 14 Punkten,
im schlimmsten Fall (alle 19 über 1 Jahr) sechs.

**Offen: die Sichtprüfung**, ausdrücklich vor dem Push (#60).

### 17.08.2026 (abends) – Datumsauswahl zurückgebaut, zwei falsche Doku-Sätze korrigiert

**Die deutsche Datumsauswahl ist wieder draußen.** Nicht weil sie nicht
funktioniert hätte — 22 Suiten waren grün —, sondern weil sie am Bildschirm
schlechter aussieht als der englische Kalender. Aus zwei Bedienelementen waren
sechs geworden, der anklickbare Kalender war weg, und der Gewinn war ein
Monatsname. Entscheidung Philip: *„Es darf auf Englisch sein."* `git revert`
statt `reset --hard`, damit der gebaute Weg nachlesbar bleibt; die drei
Dateien sind danach zeichengleich mit dem Stand davor. Transferwissen **#60**
ist auf dieses Ergebnis umgeschrieben und trägt jetzt oben ein „bitte nicht
erneut versuchen".

**Ein Prüfstein bleibt** — der einzige bleibende Ertrag der Runde: Der
Bedienpfad „Performance blockweise" → „Benutzerdefiniert" war von **keinem**
Test je berührt. Schritt 1b in `tests/test_bedienung.py` fährt ihn jetzt hoch
und prüft zugleich, dass alle vier Datumsfelder `format="DD.MM.YYYY"` tragen.

**Der eigentliche Befund des Abends war ein Doku-Fehler.** Nach dem Push am
Nachmittag stürzte die Cloud-App mit `ImportError` ab. Ursache war ein
veraltetes Modul im Speicher der Cloud — ein Reboot hat es behoben, der Code
war in Ordnung (nachgemessen: alle 23 aus `modules.shared` importierten Namen
lagen korrekt auf dem Server). Dabei kam heraus:

- **Die Cloud deployt `verbesserungen`, nicht `main`.** Die Doku behauptete an
  zwei Stellen das Gegenteil (§2 „Branch `main`", `Start.txt` „Solange main
  steht, sieht der Streamlit-Deploy nichts davon"). Deshalb wurde in dem
  Glauben gepusht, das sei folgenlos — und die App stand für die Kollegen.
  Beide Stellen sind korrigiert und tragen jetzt eine Warnung.
- **Transferwissen #11 war unvollständig** und hat die Suche in die falsche
  Richtung geschickt: Es sagt für `ImportError` pauschal „Reboot ändert
  nichts". Das gilt nur, wenn die Datei im Repo falsch ist. Der zweite Fall
  (Datei richtig, Modul im Speicher alt) steht jetzt daneben, samt
  Prüfreihenfolge.
- **Diagnose-Werkzeug fürs nächste Mal:** Ab Python 3.13 kürzt der Traceback
  mehrzeilige Anweisungen zu `...<N lines>...`, und **N identifiziert die
  Revision** — so war ohne Serverzugriff belegbar, welcher Commit lief.

### 17.08.2026 – Kollegen-Feedback: deutsche Datumsauswahl, Einzeltitel, Fälligkeiten

Erste Rückmeldung aus dem Gegentest durch Kollegen. Drei gemeldete Punkte,
zwei Befunde beim Nachmessen dazu. Vier Commits, alle mit Prüfstein.

**1. Der Kalender im „Eigenen Zeitraum" war englisch** (gemeldet).
> ⚠️ **Noch am selben Abend zurückgebaut** — siehe den Eintrag darüber. Der
> Kalender bleibt englisch. Was hier steht, beschreibt einen Stand, den es
> nicht mehr gibt; die Analyse dazu ist als #60 weiterhin gültig.

Keine Fehlkonfiguration: Streamlit 1.61 liefert im Frontend nur die englische
Sprachdatei aus, `format="DD.MM.YYYY"` wirkt lediglich auf den Text im Feld,
einen Sprachparameter gibt es nicht. Ersetzt wurde es damals durch
`shared.datum_waehler_de` (Tag | Monat | Jahr, Namen aus
`formats.MONATSNAMEN_LANG`). **Betroffen waren alle vier Datumsfelder**, nicht
die zwei gemeldeten — Von/Bis am Balken-Chart gehören dazu und waren bis dahin
von keinem Test berührt. Ausführlich als Transferwissen **#60**.

**2. Die Einzeltitel-Übersicht zwang zum Scrollen** (gemeldet). `st.dataframe`
lief mit der Vorgabe `height="auto"`, und die bedeutet laut Streamlit-
Quelltext „zeigt höchstens zehn Zeilen". Bei *Muster FFPB Pro* (32 Aktien in
einer Gattung) waren zwei Drittel des Bestands unsichtbar. Jetzt
`height="content"`. Die Breite war nie das Problem — `width` steht ohnehin auf
`"stretch"`. Bewusst kein gerechneter Pixelwert.

**3. Die Fälligkeiten der einzelnen Anleihen fehlten** (gemeldet, Wunsch von
Beratern). Der Balkenchart zeigt Gewicht je Fälligkeits*jahr*; welche Anleihe
dahintersteckt, sagte er nicht. Neu darunter eine Tabelle Wertpapier /
Fälligkeit / Restlaufzeit / Kupon / Rendite / Duration / Gewicht, aufsteigend
sortiert. `build_faelligkeiten_tabelle` steht bewusst als eigene Funktion und
nicht inline im Renderpfad (#55). Die Restlaufzeit rechnet gegen das
**Auswertungsdatum** der Bestandsdatei — bewusst nicht „Datenstand" genannt,
weil auf derselben Seite zwei verschiedene Daten stehen (21.07.2026 aus dem
Dateinamen, 20.07.2026 aus der Spalte).

**4. Anleihen ohne feste Fälligkeit fielen still aus dem Chart** (nicht
gemeldet, beim Nachmessen gefunden). Bis zu 46,54 Prozentpunkte
Rentengewicht ohne ein Wort dazu; bei drei Strategien erschien gar kein
Chart. Transferwissen **#59**, Zahlen dort.

**5. „Anzahl Titel" stand überall um 1 zu hoch** (nicht gemeldet).
`n_titel = len(df)` zählte die leere CSV-Abschlusszeile mit — **38 von 38**
Dateien, Abweichung immer genau +1. Die Gattungs-Tabellen darunter waren
korrekt, weil `groupby` das NaN verwirft; deshalb fiel der Widerspruch nie
auf. Korrigiert über `anzahl_titel()`, bewusst nicht zentral in
`parse_pf_data` — das hätte den Broschüren-Pfad berührt für einen Fehler mit
genau einem Verbraucher.

**Nebenbei aufgeräumt:** Die Anleihen-Erkennung stand dreimal wortgleich im
Modul; jetzt `ANLEIHEN_KENNWORTE` / `ist_anleihe` / `nur_anleihen` an einer
Stelle. Und `tests/ui_dump.py` erfasst seit heute auch die
**Portfolioanalyse** (`python tests/ui_dump.py datei.json portfolio`) — für
diese Ansicht gab es bis dahin gar keinen Vorher/Nachher-Beweis, obwohl genau
sie hier umgebaut wurde.

**Neuer Prüfstein `tests/test_portfolioanalyse.py`** (sechs Schritte) — die
Ansicht hatte bis dahin keinen eigenen. Damit **22 Suiten**.

**Beweise.** 22 von 22 Suiten grün, kein Schritt übersprungen, `pyflakes` bei
null. `ui_dump` vorher/nachher: Performance-Ansicht **zeichengleich** (der
eigene Zeitraum ist in der Standardansicht aus); Portfolioanalyse ändert
genau vier Zeilen — neue Überschrift, neue Tabelle, neue Caption und „Anzahl
Titel" 23 → 22. Sieben Broschüren aus einem Arbeitsbaum auf dem alten Stand
gebaut und rekursiv verglichen: **2105 ZIP-Einträge, 0 inhaltliche
Abweichungen** — der Export-Pfad ist unberührt, obwohl `portfolioanalyse.py`
darin liegt. Jeder Schritt des neuen Prüfsteins schlägt gegen den alten Stand
an (1 Tabelle ohne `height`, 38 von 38 Titelzahlen, 4 × `st.date_input`,
beide neuen Funktionen fehlen).

*(Drei eigene Fehler fielen beim Bauen auf, alle in Tests bzw. beim
Formatieren, alle im Code vermerkt: ein `.replace(".", ",")` über den fertigen
String machte aus „0,6 J." ein „0,6 J,"; der AppTest-Schritt setzte die
Strategie auf CSV-Namen statt Anzeigenamen und lief grün, ohne etwas zu
prüfen — derselbe Fehler wie am 14.08.2026; und `.options` liefert
Beschriftungen (Strings), `.value` den Rohwert (int), weshalb ein Vergleich
`'2008' != 2008` das Verstellen ins Leere laufen ließ.)*

### 14.08.2026 (nachts) – Zeitraum-Zuschnitt der Heatmap auf Kalenderjahre

Philip: In „Jahr für Jahr" fehlen bei der Schnellwahl „3 Jahre" die Kacheln
Januar bis Juni 2023.

**Gemessen:** Der Zuschnitt rechnete `Datenstand − 3 Jahre` = 21.07.2023.
Jan–Jun 2023 lagen außerhalb, Juli 2023 blieb als Elf-Tage-Rumpfmonat stehen.
Sechs leere Kacheln — bei **jeder** Schnellwahl, weil der Schnitt immer im
Monat des Datenstands landet.

**Warum das ein Fehler war:** Eine leere Kachel bedeutet in dieser Matrix
schon etwas („die Strategie lief da noch nicht", bei comdirect vor 03/2024).
Hier bedeutete dieselbe Kachel „es gibt Daten, der Zeitraum blendet sie aus".
Zwei Bedeutungen, ein Aussehen (#46).

**Behoben** durch Ausrichtung auf ganze Kalenderjahre: „N Jahre" bedeutet in
der Heatmap die letzten N vollen Kalenderjahre plus das laufende. Kostet
nichts — gleiche Zeilenzahl bei 1/3/5/10 Jahren, null Lücken, und das älteste
Jahr zählt danach als vollständig in die Ø-Zeile. Ein **eigener Zeitraum wird
weiterhin wörtlich** genommen; wer Daten eintippt, meint genau diese.

In Kauf genommen: „3 Jahre" zeigt jetzt 01/2023–07/2026, also ein halbes Jahr
mehr als der Kennzahlen-Block darüber, der taggenau rechnet. Die Caption sagt
das dazu — zwei verschiedene Spannen unkommentiert untereinander wären wieder
eine Zahl, die der Zahl daneben widerspricht.

**Der eigentliche Befund** steht als Transferwissen **#55**: Auf dieser
Heatmap lagen zehn Testschritte, und **keiner konnte diese Zeile anfassen**,
weil sie inline im Renderpfad von `streamlit_app.py` stand. Sie heißt jetzt
`zeitraum_fuer_heatmap` und ist eine reine Funktion; der neue **Schritt 9**
prüft sie gegen sieben von Hand gerechnete Fälle (inklusive Jahreswechsel und
eigenem Zeitraum) und misst zusätzlich die Wirkung an allen 19 Strategien:
Die älteste Jahreszeile darf keine leere Kachel haben, solange die Strategie
in diesem Jahr durchgehend lief.

**Rot vor Grün nachgestellt:** Gegen die alte Formel meldet Schritt 9 neun
Abweichungen an der Ableitung plus die sechs Lücken je Strategie.

Die **Bandbreiten-Ansicht ist unberührt** — sie ignoriert den Zeitraum
ohnehin und nimmt fest fünf Kalenderjahre. `ui_dump` vorher/nachher
zeichengleich, alle 21 Suiten grün, `pyflakes` bei null.

### 14.08.2026 (spät) – Renderfehler behoben, Bandbreite nach Spezifikation

Philip hat die Bandbreiten-Ansicht am Bildschirm gesehen. Zwei Befunde: Sie
**rendert kaputt**, und sie **entspricht nicht der Bloomberg-Vorlage**, die er
kennt.

**DER RENDERFEHLER.** Vier Zeilen zu einem Strich zusammengefallen, Zahlen
übereinander, die Jahresspalten-Annotation allein am oberen Rand. Ursache:
`fig.layout.yaxis.type` war `None` — Plotly riet den Achsentyp, und die
Mischung aus echten Strings (`17J-Hoch`) und einem zahlartigen (`2026`)
sprengte den Achsenbereich. Dazu wurden Annotationen über
Beschriftungs**texte** platziert statt über Koordinaten.

**Alle Prüfsteine waren dabei grün** — sie lasen `z`, `text` und `y` aus dem
Figur-Objekt, also die Daten. Die Geometrie entsteht erst beim Rendern. Das
ist Transferwissen **#54**, und der neue **Schritt 8** prüft jetzt
ausschließlich das `layout`: Achsentyp, Kategorienreihenfolge, Spaltenzahl,
Koordinatentypen der Annotationen. Gegen den alten Stand nachgestellt meldet
er sofort vier Abweichungen.

**Nebenbefund aus der Reparatur:** Bei `go.Heatmap` wird `z[0]` **unten**
gezeichnet. Die Zeilenlisten kamen in Leserichtung und wurden ungedreht
übergeben — die Jahr-für-Jahr-Matrix zeigte also **2026 unten und Ø oben**,
verkehrt herum, seit dem ersten Tag. Jetzt wird an genau einer Stelle bewusst
umgedreht.

**DIE SPEZIFIKATION.** Philips Vorgabe wich an acht Stellen ab. Entscheidend
war eine: Meine Fassung war um die **Jahresspalte** herum gebaut — geometrisches
Mittel und „nur vollständige Jahre" waren die Bedingung dafür, dass sich die
Zeile zu dieser Spalte verkettet. Seine Vorlage hat zwölf Spalten und keine
Jahresspalte. Fällt sie weg, fällt der Grund weg, und sein Paket ist zugleich
das konventionelle (Bloomberg, TradingView):

| | neu | vorher |
|---|---|---|
| Mittelwert | **arithmetisch** (Summe / Anzahl) | geometrisch |
| Spalten | **12** | 13 (mit „Jahr") |
| fehlende Werte | **je Monat tolerant** | nur vollständige Kalenderjahre |
| Fenster | **fest 5 Jahre** | folgte der Zeitraum-Schnellwahl |
| Farbskala | **datengetrieben**, symmetrisch | fest ±3 % |
| Format | **2 Nachkommastellen, kein Plus** | 1 Stelle, mit Plus |

Die Ø-Zeile der Ansicht „Jahr für Jahr" rechnet **weiterhin geometrisch** —
dort gibt es die Jahresspalte, und die Verkettungs-Zusage aus Runde 2 gilt
unverändert. Damit stehen zwei verschiedene Mittelwerte im selben Werkzeug;
der Hover der Mittel-Zeile nennt deshalb **beide** (arithmetisch 0,85 %,
geometrisch 0,82 %). Ein unerklärter Unterschied wäre schlimmer als eine Zahl
mehr im Hover.

**Untergrenze weg, Vorbehalt hin.** Statt bei zu wenig Historie zu
verweigern, wird gerechnet und ehrlich beschriftet: `2J Hoch` statt `5J Hoch`.
Unter drei Vergleichsjahren erscheint ein Hinweis. Betroffen: die drei
comdirect-Strategien und *Pro Dividende*.

**Hover nach Vorlage:** „März — Hoch von 2021–2025 · Rendite: 2,83 % · Jahr:
2021 · Zeitraum: 28.02.2021 – 31.03.2021". Der Zeitraum beginnt am **Schluss
des Vormonats** — so misst eine Monatsrendite, und so steht es auch in
Philips Vorlage.

**Plumbing vereinfacht:** Weil das Fenster fest ist, fallen `band_von`,
`band_bis` und `band_jahre` aus der Vorrunde **ersatzlos** weg. Und
`_zeilen_tabelle` baut die Tabelle jetzt aus **denselben Zeilen** wie die
Figur — vorher gab es zwei Wege zu denselben Zahlen.

**Beweise:** `ui_dump` vorher/nachher zeichengleich; alle 21 Suiten grün;
`pyflakes` bei null; der Broschüren-Pfad unberührt. Die Figur wurde
zusätzlich als HTML ausgegeben und **angesehen** — der Schritt, der in der
Vorrunde gefehlt hat.

### 14.08.2026 (abends) – Bandbreiten-Ansicht nach Bloomberg-Vorbild

Philip bringt aus Bloomberg eine zweite Darstellung derselben Daten mit (dort
„SEAG"): Statt jedes Jahr als eigene Zeile zeigt sie **vier** Zeilen — Hoch,
Mittel und Tief je Kalendermonat über die Vorjahre, darunter das laufende
Jahr. Umschaltbar über ein `segmented_control` unter der Überschrift, Werte
**„Jahr für Jahr"** und **„Bandbreite"**.

**Recherche vorab** (Bloomberg SEAG, TradingView, StockCharts, Barchart):
TradingView steuert die Farbe über einen *Color Intensity Cutoff* — Werte
jenseits der Grenze bekommen volle Sättigung. Das ist exakt der Mechanismus,
den Runde 2 eingebaut hat; die ±3 % sind also konventionskonform. Mehrere
Werkzeuge nennen beim Hoch/Tief zusätzlich **das Jahr des Extrems** — das ist
in den Hover gewandert.

**Der Fund, der die Runde geprägt hat:** Das laufende Jahr darf **nicht** in
seinem eigenen Band stehen. Bei Datenstand 07/2026 ist das Band 2021–2025 und
die untere Zeile 2026. Nähme man 2022–2026, zöge der laufende Wert sein eigenes
Extrem mit — ein Rekordmonat läge per Definition nie „über dem Hoch", er wäre
das Hoch. Steht als Transferwissen **#53**.

**Das Band braucht ein eigenes Fenster.** Es denkt in ganzen Kalenderjahren,
der Zuschnitt aus Runde 2 in Tagen: Bei „5 Jahre" schnitte der tagbasierte Weg
am 21.07.2021, 2021 wäre unvollständig und das Band hätte **vier** Jahre,
obwohl „5J" darüber stünde. Die Beschriftung nennt darum immer die tatsächliche
Zahl — bei *Muster FFPB Pro* steht `2J-Hoch`, nicht `5J-Hoch`.

**Unter zwei vollständigen Jahren gibt es keine Bandbreite** (`BAND_MIN_JAHRE`):
Bei einem einzigen Jahr wären Hoch, Mittel und Tief dieselbe Zahl — eine
Bandbreite ohne Breite. Betroffen sind die drei comdirect-Strategien und
*Pro Dividende*; dort erscheint eine Erklärung statt einer Matrix, und die
Ansicht „Jahr für Jahr" zeigt die Daten unverändert.

**Nur die Mittel-Zeile verkettet sich** zu ihrer Jahresspalte (sie kommt aus
`monats_durchschnitt` mit Jahresfenster — dieselbe Funktion, keine zweite
Fassung). Bei Hoch und Tief steht je Monat das Extrem *dieses Monats*, in der
Jahresspalte das Extrem *des Jahres*; beide stammen nicht zwangsläufig aus
demselben Jahr. Das steht ausdrücklich in der Caption, sonst rechnet jemand
nach und hält es für einen Fehler.

**Kachelgröße** (zweiter Wunsch): Die Zeilenhöhe wächst umgekehrt zur
Zeilenzahl, gedeckelt bei 80 px — bei dreizehn Spalten auf voller Breite ist
eine Spalte rund 75 px breit, die Kachel wird also annähernd quadratisch statt
zum liegenden Balken. Bei zwei Zeilen (Zeitraum „1 Jahr") war die Matrix
vorher ein flacher Streifen. Die Schrift wächst mit (11 bis 16 pt).

**Umbau statt Anbau:** `_heatmap_figur` bekam in Runde 2 einen generischen
Zeilen-Helfer. Die neue Ansicht ist deshalb **andere Zeilen an derselben
Maschine** — `_zeilen_jahr_fuer_jahr` und `_zeilen_bandbreite` liefern, die
Figur zeichnet nur noch. Colorbar, Jahresspalte, Tabelle und Kachelgröße
gelten für beide.

**Ein eigener Fehler, der zwei Runden alt war.** Die AppTest-Fälle setzten
`p_sel1="Comdirect 100"` — den CSV-Portfolionamen. Das Auswahlfeld führt
aber **Anzeigenamen** (`Comdirect_100`), und Streamlit ignoriert einen
ungültigen Wert stillschweigend. **Sechs Testfälle aus zwei Runden liefen
gegen *cVV konservativ*** und bewiesen nichts über SCHWEIZ, comdirect oder
Pro Dividende — grün, aber blind. Dieselbe Klasse wie das fehlende
`majorTimeUnit` (#49): eine Zuweisung, die ins Leere läuft, ohne Fehler und
ohne Meldung. Korrigiert, und der AppTest-Helfer prüft seitdem nach jedem
Lauf, ob der gesetzte Wert **angekommen** ist. Die Prüfsteine testen damit
zum ersten Mal wirklich, was sie behaupten — und sind weiter grün.

**Beweise:** `ui_dump` vorher/nachher **zeichengleich**; alle 21 Suiten grün;
`pyflakes` bei null; der Broschüren-Pfad belegbar unberührt (die neuen
Symbole `bandbreite`, `BAND_*`, `ZEILE_HOEHE_*`, `ANSICHT_*` erreichen
ausschließlich `risiko_ansicht.py`). Die Invariante `Tief ≤ Mittel ≤ Hoch`
wurde über alle 19 Strategien und drei Fenster geprüft: null Verletzungen.

### 14.08.2026 (nachmittags) – Heatmap-Feinschliff aus der Sichtprüfung

Philip hat die Heatmap am Bildschirm gesichtet. Fünf Befunde, **keiner davon
durch einen Test auffindbar** — genau dafür ist die Sichtprüfung da.

**1. „Die Skala wirkt zu blass."** Grenzen von ±5 % auf **±3 %** (absolut)
und von ±2,5 % auf **±1,5 %** (Differenz), dazu etwas sattere Endfarben
(`#C06B58` / `#6B9153` statt `#C77B6B` / `#7A9B68`). Der Hebel lag bei den
Grenzen, nicht bei den Farben — die Herleitung steht als vierter Satz bei
Transferwissen **#52**. Der Kontrast wurde erneut über 21 Stützstellen
nachgerechnet: **4,55:1**, knapp über den 4,5:1 der WCAG AA. Weiter geht es
nicht; Signalfarben lägen bei 3,20:1.

**2. Der Zeitraum greift jetzt.** Die Heatmap folgt der Schnellwahl oben —
eine Umkehr der Entscheidung vom Vormittag, und sie ist erst jetzt
gefahrlos: Die Sternchen-Kennzeichnung, die es damals noch nicht gab, macht
die entstehenden Rumpfmonate am Zeitraum-Rand sichtbar.

Die Umsetzung darf **nicht** über `sd`/`sd_vor` laufen. Die sind auf `mind`
geklemmt, und `mind` ist bei aktivem Vergleichsportfolio die **Schnittmenge**
beider Historien — *Muster ausgewogen cVV* verlöre bei „Seit Auflage"
fünfzehn Jahre, sobald jemand eine junge Strategie danebenstellt. Der
Zeitraum wird deshalb eigens abgeleitet, und `None` heißt „Rand der
jeweiligen Reihe". Der Zuschnitt selbst passiert in `zeige_monatsheatmap`,
damit beide Reihen ihn unabhängig bekommen. Ein AppTest-Schritt nagelt genau
diesen Fall fest.

**Bewusst nicht gekoppelt:** Risiko-Block und Vola-Chart. Die Zeilen der
Risiko-Tabelle **sind** die Zeiträume — eine „10 Jahre"-Zeile in einer
Drei-Jahres-Auswahl wäre in sich widersprüchlich, und der Vola-Chart bräuchte
ein Jahr Vorlauf, das es bei „1 Jahr" nicht gäbe. Steht als Kommentar und als
Caption dort.

**3. Farblegende.** Waagerecht unter der Matrix, die Enden mit **„≤" und
„≥"** beschriftet. Rund 15 % der Monate sättigen bei ±3 % aus; ohne diese
beiden Zeichen sähe der dunkelste Ton wie der Höchstwert aus.

**4. Texte.** `„Mrz"` → `„März"`, dazu `MONATSNAMEN_LANG`/`monat_lang` für
Fließtexte („bester: April 2020" statt „bester Monat Apr 2020"). Captions
gestrafft, Quote mit einer statt zwei Nachkommastellen. Die
Sternchen-Fußnote **musste** ohnehin neu, weil ein angebrochener Monat jetzt
auch vom Zeitraum-Rand kommen kann.

**5. Der Vergleichs-Haken ist immer sichtbar**, ausgegraut statt versteckt,
wenn oben kein Vergleichsportfolio läuft. Vorher konnte man nicht wissen,
dass es die Möglichkeit gibt.

**Dazu zwei Ergänzungen:**

- **Ø-Zeile je Kalendermonat** (geometrisches Mittel, ausschließlich über
  **vollständige** Kalenderjahre). Die Beschränkung ist keine Vorsicht,
  sondern die Bedingung dafür, dass sich die Ø-Zeile exakt zu ihrem eigenen
  Ø-Jahr verkettet — dieselbe Zusage wie bei jeder anderen Zeile. Der Beweis
  hängt daran, dass für alle zwölf Monate dieselbe Jahresmenge zugrunde
  liegt. An *Muster ausgewogen cVV* gemessen: 17 volle Jahre, Verkettung
  5,16079 %, Ø-Jahr 5,16079 %, Abweichung 4,4e-16.
- **Haken „Tabelle anzeigen"** unter jeder Matrix, nach dem Muster des
  Balken-Charts — aus einem Plotly-Chart bekommt man keine Zahlen heraus.

**Beweise:**

- **`ui_dump` vorher/nachher zeichengleich.** Die Standardansicht hat sich
  nicht um ein Zeichen geändert; die Heatmap ist standardmäßig aus.
- **Der Broschüren-Pfad ist unberührt** — belegt statt behauptet: Alle
  geänderten Symbole (`MONATSNAMEN_*`, `monat_*`, `monats_durchschnitt`,
  `HEATMAP_*`) erreichen ausschließlich `risiko_ansicht.py`. `analytics.py`,
  `formats.py` und `shared.py` sind zwar Export-Module, aber es wurde dort
  nur ergänzt, nichts geändert.
- Alle **21 Suiten grün**, `pyflakes` bei null.

**Zwei eigene Fehler, die dabei auffielen** — beide in Tests, nicht im Code:
Die Kennzeilen-Prüfung verglich `"bester Monat"` gegen einen
kleingeschriebenen String und konnte nie zutreffen; und die Prüfung „kommen
die Monatsnamen aus `strftime`?" fand per Textsuche die **Warnung im
Docstring**, die genau davor warnt. Sie läuft jetzt über den Syntaxbaum.

### 14.08.2026 – Monatsrenditen-Heatmap und Risiko-Überblick

**Neu im Tool, nicht in der Broschüre** (Festlegung Philip): zwei
Auswertungen, die es bisher nicht gab. Die Ansicht zeigte Wertentwicklung,
Kennzahlen und Drawdown-Verlauf — aber nichts, woran sich die **Struktur**
einer Strategie über die Zeit ablesen ließ, und Volatilität wie Max Drawdown
gab es nur als **einen** Wert über den Gesamtzeitraum.

**Sidebar-Gruppe „Analysen"** mit vier Haken: Monatsrenditen (Heatmap),
darunter eingerückt Differenz zur eigenen Benchmark und Differenz zum
Vergleichsportfolio, sowie Risiko im Überblick. Die Vergleichsstrategie ist
bewusst das **bestehende** Vergleichsportfolio — ein zweites Auswahlfeld mit
demselben Inhalt daneben hätte die Sidebar unruhig gemacht.

**Der eigentliche Aufwand steckte nicht in der Darstellung, sondern in den
ungleichen Historien.** Die Reihen laufen von 2009 (cVV, nach `HISTORIE_AB`)
bis 03/2024 (comdirect). Drei Dinge waren zu lösen:

1. **Angebrochene Monate.** #51 eine Ebene feiner — gemessen 26 Stück über
   alle 19 Strategien. Sie stehen in der absoluten Matrix mit `*` und
   entfallen in jeder Differenz. Begründung als Transferwissen **#52**.
2. **Der Zuschnitt.** Die Blöcke rechnen auf `data[ps1]` und **nicht** auf
   `df1`/`df2`. Letztere sind zweifach beschnitten — auf die
   Zeitraum-Schnellwahl und, sobald das Vergleichsportfolio läuft, per
   Inner-Join auf die gemeinsamen Handelstage. *Muster ausgewogen cVV* gegen
   *Comdirect 100* hätte dabei **fünfzehn Jahre** verloren.
3. **`historie_beschneiden` lag am falschen Ort.** Die Funktion stand in
   `portfolioanalyse.py` und griff deshalb nur im Broschüren-Export. Ohne
   sie stünde in der Heatmap bei den fünf cVV-Strategien eine Zelle
   **Dez 2008 mit genau einem Tag** (+0,13 / +0,16 / +0,27 / +0,30 /
   −0,01 %) — die beiden 2008er-Zeilen sind reine Indexbasis (#43). Sie ist
   nach `analytics.py` gewandert; dieselbe Krankheit wie Backlog B/E/F, nur
   bei einer Regel statt bei einer Formel.

**Die Differenz ist geometrisch** (Festlegung Philip). Nur so verketten sich
die zwölf Monate einer Zeile exakt zur Jahresspalte — nachgerechnet an allen
19 Strategien und allen Jahren, Abweichung durchweg unter 1e-10.

**Risiko im Überblick:** rollierende Volatilität über 365 Tage als Chart,
darunter je Strategie eine Tabelle mit Volatilität, Sharpe Ratio, Tracking
Error und Information Ratio je Zeitraum (YTD/1/3/5/10 Jahre/seit Auflage).
Die beiden Benchmark-Spalten **entfallen ganz**, wenn keine Benchmark
hinterlegt ist, statt eine Spalte aus lauter „–" zu zeigen. Die
Drawdown-Perioden-Tabelle hängt am bestehenden Drawdown-Haken; beide speisen
sich aus **einer** Funktion `risiko_perioden`.

Die rollierende Volatilität nutzt bewusst dieselbe Formel wie `calc_vola`
(std ddof=1 × √365, nicht √252). Der letzte Punkt der Kurve trifft damit die
Kennzahlen-Kachel darüber — zwei verschiedene Volatilitäten auf einem
Bildschirm wären schlimmer als jede Lehrbuch-Ungenauigkeit. Ein eigener
Testschritt nagelt es fest.

**Farbskala.** Rot–neutral–grün, gedämpft, feste Grenzen bei ±5 % (absolut)
und ±2,5 % (Differenz). Fest und nicht datenabhängig: Eine Skala, die sich je
Strategie neu kalibriert, färbt zwei Strategien unterschiedlich ein. Die
Grenzen kommen aus einer Messung über alle 19 Strategien (|Wert| P95 = 5,28 %
bzw. 2,41 %) und liegen knapp darunter — 95 % der Monate nutzen die Skala
aus, die Extreme sättigen aus.

**Vorgehen und Beweise:**

- **Rot vor Grün nachgestellt.** `_ist_voller_monat` wurde vorübergehend auf
  die naive Fassung (`return not sub.empty`) gesetzt: Der Prüfstein meldete
  daraufhin bei **allen 19 Strategien** angebrochene Monate als vollständig,
  inklusive der 20-Tage-Monate von comdirect und der 1-Tages-Zelle der
  cVV-Indexbasis. Erst danach kam die Prüfung hinein.
- **Sieben Broschüren vorher/nachher rekursiv verglichen** (wegen des
  `historie_beschneiden`-Umzugs): 2056 ZIP-Einträge, **34 Abweichungen,
  ausnahmslos `docProps/core.xml`** der eingebetteten Arbeitsmappen. An einem
  Beispiel nachgewiesen, dass darin nur `dcterms:created`/`modified` steht —
  nach Entfernen der Zeitstempel zeichengleich.
- **`ui_dump` vorher/nachher: genau EINE geänderte Zeile**, die neue
  Sidebar-Überschrift „Analysen". Die Standardansicht ist unverändert.
- **Alle 21 Suiten grün**, `pyflakes` über 34 Dateien bei null Meldungen.

**Nebenbefund:** `HISTORIE_AB` wurde aus dem Re-Export-Block in
`portfolioanalyse.py` entfernt — nach dem Umzug meldete `pyflakes` es als
ungenutzt, und kein Modul und kein Test holt es von dort (nachgeprüft).
`pyflakes` kennt kein `noqa`, ein stehengelassener Re-Export hätte die
Prüfung dauerhaft rot gehalten.

**Offen und bewusst nicht angefasst:** `historie_beschneiden` wird im
Performance-Tab weiterhin **nur** von der Heatmap und dem Risiko-Block
angewandt. Kennzahlen, Linien-Chart und rollierende Tabelle rechnen bei den
fünf cVV-Strategien unverändert ab dem 31.12.2008, die Broschüre ab dem
01.01.2009. Die Wirkung auf CAGR und Volatilität ist klein, aber es ist
dieselbe Klasse Fund wie Backlog B/E/F. Eine Angleichung ändert ausgewiesene
Zahlen und gehört deshalb entschieden, nicht nebenbei gemacht.

### 12.08.2026 (abends, 6) – Der Säulen-Chart zeigte ein Rumpfjahr als Jahresbalken

**Auslöser:** Philip an der Pro-Broschüre — im Chart „PERFORMANCE P.A. (NACH
KOSTEN) IM BENCHMARKVERGLEICH" steht ein Balken **2023**, obwohl die
Strategie erst seit dem 01.09.2023 läuft.

**Befund:** Bestätigt und wieder breiter als gemeldet. Das Fenster („letzte
fünf abgeschlossene Kalenderjahre", 2021–2025) war richtig; die Schleife in
`compute_performance_data` übersprang ein Jahr aber nur bei `sub.empty`.
Betroffen ist damit jede Strategie, deren Auflage in das Fenster fällt —
**7 von 19**:

| Strategie | Auflage | Rumpfbalken | Länge | zeigte |
|---|---|---|---|---|
| Muster FFPB Pro | 01.09.2023 | 2023 | 122 Tage | +3,23 % / +5,11 % |
| Muster FFPB Pro Dividende | 22.10.2024 | 2024 | 71 Tage | −0,97 % / −1,30 % |
| Comdirect 30 / 70 / 100 | 12.03.2024 | 2024 | 295 Tage | z. B. +6,05 % / +4,47 % |
| Muster SCHWEIZ Substanz | 22.09.2022 | 2022 | 101 Tage | −2,19 % (ohne BM) |
| Muster SCHWEIZ Aktien | 12.09.2022 | 2022 | 111 Tage | −4,68 % (ohne BM) |

Die übrigen zwölf zeigen 2021–2025 und bleiben unverändert.

**Entscheidungen (Philip):** Der Rumpfbalken fällt **ganz weg** (nicht:
umbenennen in „2023 ab 01.09."), auch wenn Comdirect und Pro Dividende damit
auf **einen** Balken fallen — ein ehrlicher Balken ist besser als zwei, von
denen einer eine Jahresrendite behauptet, die es nicht gibt. Das **Tool
bleibt unverändert**. Bleibt kein volles Jahr übrig, gibt es eine **sichtbare
Warnung**; das Chart behält die Vorlagendaten.

**Korrektur:** `_ist_volles_jahr` in `modules/analytics.py` — beide Ränder
aus dem Jahresausschnitt, Toleranz `JAHR_RAND_TOLERANZ_TAGE = 3`
(spiegelbildlich zur schon vorhandenen 28.12.-Regel; Feiertagsstarts sollen
kein Jahr entwerten). Dazu die Leerfall-Meldung in
`pptx_export._build_we_data`.

**Nachher:** Pro `2024 · 2025`; SCHWEIZ `2023 · 2024 · 2025`; Comdirect und
Pro Dividende `2025`; cVV/ESG/ETF unverändert `2021 … 2025`.

**Beweis:** Sieben Broschüren vorher/nachher rekursiv verglichen — **2056
ZIP-Einträge, 17 inhaltliche Abweichungen**, ausschließlich in den
Säulen-Chart-XML und ihren eingebetteten Arbeitsmappen. CVV, ESG, ETF und
Thema (nur Offensiv) sind **byte-identisch**; in `Thema_x3` sind es genau
die Charts von Pro und Pro Dividende, der Offensiv-Chart daneben ist
unverändert. Der XML-Diff enthält nur je eine Kategorie und einen Datenpunkt
weniger pro Serie — keine Achse, kein Format, keine Legende, keine Fußnote.
Alle 19 Suiten grün, `pyflakes` 0.

**Zwei Nebenbefunde:**

- `pptx_slides.EINZELTITEL_WARNUNGEN` behauptete im Kommentar, von
  `pptx_export` ausgelesen zu werden. Im ganzen Repo gibt es keine
  Leseposition — die Liste wächst, und niemand sieht sie. Kommentar
  richtiggestellt, die Liste selbst unangetastet.
- `F9_BAR_INCLUDE_CURRENT_YEAR` hängt das **laufende, unvollständige** Jahr
  an und widerspricht damit der neuen Regel. Bewusst nicht geändert: Der
  Schalter hängt an der Folienrolle `performance`, die in **keiner**
  Familien-Konfiguration vorkommt — er läuft in keiner echten Broschüre. Als
  Hinweis an der Konstanten vermerkt.

Transferwissen **#51**. Prüfstein `tests/test_kalenderjahre.py`.

### 12.08.2026 (abends, 5) – Die Quellenangabe lag im Disclaimer (16 von 16 Folien)

**Auslöser:** Philip an der Offensiv-Broschüre — „Quelle: Eigene Berechnung,
Stand 20.07.2026" wird vom Disclaimer überdruckt.

**Befund:** Wieder alle. In allen sechs Vorlagen liegt die Box `Quelle`
(23,30–28,10 × 13,89–14,19 cm) **innerhalb** der Box `Fußnote`
(12,50–28,10 × 11,16–16,20 cm) — 16 Wertentwicklungs-Folien, auf den Emu
identisch. Zwei Ursachen, die sich addieren: die Vorlagenposition, und ein
Ersatztext mit **189 Zeichen** bei 149 Zeichen Zeilenbreite, der still
umbrach und alles darunter eine Zeile tiefer schob (14,21 → 14,47 cm).

**Gemessen am Rendering, nicht im XML.** python-pptx kennt keine
Zeilenumbrüche; die Kollision ist dort unsichtbar. PowerPoint 16.0 hat die
Folien per COM als PNG ausgegeben (1920 × 1225 px), gemessen wurde
zeilenweise über die dunklen Pixelreihen — daher auch die Kennwerte im
Prüfstein (erste Zeile 0,06 cm unter der Boxkante, Zeilenabstand 0,2533 cm).

| | Disclaimer bis | Quelle ab | |
|---|---|---|---|
| vorher | 14,47 cm | 13,89 cm | überdruckt |
| nachher | 14,21 cm | 14,80 cm | 0,59 cm Luft |

**Korrektur:** `WE_QUELLE_TOP_CM = 14,75` (in
`fill_wertentwicklung_slide` gesetzt, deckt alle 16 Folien ab) und
`WE_DISCLAIMER_REPLACEMENTS` von 146/189 auf 145/149 Zeichen gekürzt —
Aussagen unverändert, nur die Satzführung gestrafft. Die Position hält
**auch mit dem alten Text** (dann 0,28 cm Luft), die Kürzung ist also
einzeln rücknehmbar.

**Beweis:** fünf Broschüren vorher/nachher rekursiv verglichen — 1510
ZIP-Einträge, 15 Abweichungen, ausschließlich die 15 Folien-XML; darin
genau drei Änderungsarten (15× `<a:off>` der Quelle-Box, 12× die beiden
Disclaimer-Absätze). 18 Suiten grün, `pyflakes` 0.

**Zwei Nebenbefunde:**

- `tests/test_analytics.py` brach mit **UnicodeEncodeError** ab statt zu
  melden — ein „→" (U+2192) in der letzten Zeile des letzten Schrittes, das
  cp1252 nicht kennt. Alle Prüfungen hatten bestanden, der Rückgabewert war
  trotzdem 1. Behoben; repo-weit geprüft, es war die einzige Stelle, an der
  so ein Zeichen zur Laufzeit gedruckt wird.
- Der **comdirect-Disclaimer** wird gar nicht ersetzt — der Anker heißt
  „Performance Ausweis", die Vorlage schreibt „Performance-Ausweis". Dort
  steht deshalb weiter die alte Kostenregel, im Widerspruch zur `**`-Zeile
  derselben Fußnote. Als **Backlog H** aufgenommen (§15), nicht behoben:
  Wortlaut-Entscheidung.

Transferwissen **#50**. Prüfstein `tests/test_quelle_position.py`.

### 12.08.2026 (abends, 4) – Wertachse: die 100-%-Linie fehlte auf den cVV-Folien

**Auslöser:** Philips Sichtprüfung des vorigen Fixes. „Die 100 % sollen bei
der cVV in der Y-Achse dranstehen, und es soll dort starten, nicht mit dem
kleinen Abstand."

**Befund:** Dieselbe Mechanik wie waagerecht — das Minimum wurde datenbasiert
gesetzt (0,9), die Schrittweite kam unverändert aus der Vorlage (0,2). Ticks
also bei 90/110/130 %; die Linie, auf die sich jede Aussage der Folie bezieht,
kam auf der Achse **nicht vor**. Bei ESG/ETF/comdirect stand sie da, weil
deren Vorlagen zufällig 0,05 tragen.

**Der Teil des Wunsches, der nicht geht — und warum.** „Bei 100 % starten"
würde Kurve abschneiden: **Jede** Strategie war zeitweise darunter.

| Strategie | tiefster Punkt |
|---|---:|
| cVV konservativ | 99,10 % |
| cVV defensiv | 96,76 % |
| cVV defensiv plus | 92,25 % |
| cVV ausgewogen | 91,43 % |
| cVV dynamic | 85,33 % |

Ein Minimum von 100 % hätte diese Drawdowns unsichtbar gemacht — stiller
Datenverlust in einem Kundendokument, §10.9. **Entschieden (Philip):** 100 %
ist immer eine beschriftete Linie, die Achse beginnt auf der Rasterlinie
direkt unter dem tiefsten Kurvenpunkt. Damit rückt sie so nah heran, wie es
geht (cVV konservativ: von 90 % auf **95 %**), ohne etwas abzuschneiden.

**Umsetzung:** `wert_raster` in `modules/chart_dynamik.py` — Schrittweite aus
`WERTACHSE_STUFEN` (5/10/20/25/50/100 Prozentpunkte; **jede ein Teiler von
100 %**, damit die Bezugslinie zwangsläufig auf dem Raster liegt), Minimum als
Vielfaches davon, gewählt wird die feinste Stufe unter 13 Gitterlinien.
`majorUnit` der `valAx` wird jetzt mitgesetzt statt aus der Vorlage übernommen.

Dabei fiel die alte Luft-Regel auf („klebt die Kurve oben, eine Stufe
drauflegen"): Bei grobem Raster sind das **zwanzig** leere Prozentpunkte über
der Kurve. Luft ist jetzt ein fester kleiner Betrag von fünf Prozentpunkten.
Zwei Charts profitieren sichtbar: ETF ausgewogen (140 % → 135 %) und
comdirect 30 (125 % → 120 %).

**Wirkung, Beispiele:** cVV konservativ 90–160 % Schritt 20 → **95–155 %
Schritt 5** (Ticks 95/100/105/…); cVV ausgewogen 90–230 % Schritt 20 →
**80–225 % Schritt 20** (Ticks 80/100/120/…).

**Beweis:** Broschüren vorher/nachher verglichen — Abweichungen ausschließlich
in den Chart-XML, dort je `c:min`, `c:max` und `c:majorUnit` der Wertachse.
`test_chartachsen`, `test_export_smoke`, `test_trennstriche`,
`test_benchmark_charts` grün, `pyflakes` über 33 Dateien bei 0. Der Prüfstein
heißt seit dieser Runde `test_chartachsen.py` (vorher `test_datumsachse.py`) —
er deckt beide Achsen ab, und ein Name, der nur die halbe Zusage nennt, führt
in sechs Monaten in die Irre.

### 12.08.2026 (abends, 3) – Datumsachse: das aktuelle Jahr fehlte auf jeder Achse

**Auslöser:** Hinweis eines Kollegen — in der ETF-Broschüre laufen die Daten
bis Juli 2026, die Datumsachse zeigt aber kein 2026.

**Befund am Artefakt** (sieben gebaute Broschüren, Datenstand 260721):
**21 Datumsachsen, keine einzige in Ordnung.** Ursache und Lösung stehen als
Transferwissen **#49**; kurz: PowerPoint verankert die Ticks am
Achsen-**Minimum**, und das lag auf dem Anfangsmonat der Reihe.

| Broschüre | vorher | nachher |
|---|---|---|
| ETF (2 Achsen) | Ticks Nov/15 … **Nov/25** | Jul/15 … **Jul/26** |
| ESG (4) | Sep/20 … **Sep/25** | Halbjahresticks Jul/20 … Jul/26 |
| cVV klassisch (4) | Dez/08 … **Dez/25** | Jul/08 … Jul/26 |
| cVV Dynamic | Okt/18 … **Okt/25** | Jul/18 … Jul/26 |
| cVV Vergleich (F19) | **2 Beschriftungen** (Tick alle 12 Jahre) | 18, Jan/09 … Jan/26 |
| Thema, dupliziert | **37 bzw. 23** Monatsticks | 13 bzw. 8 (Quartal) |
| SCHWEIZ | **47** Monatsticks | 9 (Halbjahr) |
| comdirect (3) | `majorTimeUnit` fehlt in der Vorlage → gar keine Anpassung | 11 (Quartal) |

Die beiden fettesten Zeilen standen in **keinem** Backlog und hat auch niemand
gemeldet — sie fielen erst auf, weil für den Prüfstein die Tickfolge
nachgerechnet wurde statt der Achsengrenzen. Details zu beiden (`majorUnit`
wird nicht mitgezogen; `if el is not None` bei einem Element, das eine von
sechs Vorlagen gar nicht hat) in #49.

**Entschieden (Philip):** Das Beschriftungsformat bleibt überall `mmm/yy` —
die Vorlagen werden nicht angefasst, es ändert sich nur, *wo* die Ticks
sitzen. Und: Ein kleiner Vorlauf vor dem Kurvenstart ist in Ordnung, ein
Achsendatum in der Zukunft nicht.

**Geändert:** `modules/chart_dynamik.py` — neuer Rechenkern `achsen_raster`
(reine Datumsarithmetik, ohne XML und damit ohne PowerPoint testbar),
`datumsachse_an_daten` setzt jetzt Grenzen, Schrittweite und Anker;
`_ax_wert_setzen` legt fehlende Achsen-Elemente in Schema-Reihenfolge an.
Schrittweite konfigurierbar über `DATUMSACHSE_STUFEN` (≤ 3 Jahre Quartal,
≤ 7 Jahre Halbjahr, darüber Jahr) — Ziel sind 8–19 Beschriftungen. Der
Parameter `auf_monat_runden` ist entfallen; der einzige Aufrufer hat ihn nie
abgewählt.

**Beweis, dass nichts anderes kippt:** alle sieben Broschüren vorher/nachher
rekursiv verglichen — **2056 ZIP-Einträge, 55 Abweichungen**: 34 ×
`docProps/core.xml` (Erzeugungs-Zeitstempel) und 21 × `ppt/charts/chartN.xml`,
also exakt die 21 Datumsachsen. Innerhalb der Chart-XML sind es je ein bis
drei Elemente (`c:min`, `c:majorUnit`, `c:majorTimeUnit`) — sonst nichts.
`test_export_smoke`, `test_trennstriche`, `test_benchmark_charts` und
`test_folien_config` grün, `pyflakes` über alle 33 Dateien bei 0.

**Prüfstein:** `tests/test_chartachsen.py`. Schritt 1 rechnet den Kern gegen
dreizehn von Hand nachgerechnete Fälle (die acht echten Reihen plus
Grenzfälle: ein einziger Datenpunkt, Spanne unter einem Monat, Beginn im
Januar, genau auf der Stufengrenze) und braucht **keine Installation**;
Schritt 2 baut je Familie eine Broschüre plus die Themen-Duplikation und
SCHWEIZ und rechnet **jede** Tickfolge nach. Auf dem Stand vom Vormittag ist
er rot — alle 21 Achsen.

**Offen:** Sichtprüfung in echtem PowerPoint (#16/#28) an drei Stichproben —
ETF (Jahresschritt), SCHWEIZ (Halbjahr statt 47 Monatsticks) und cVV Folie 19
(der `majorUnit=12`-Fund).

### 12.08.2026 (abends, 2) – Anlagekriterien auch für die Thema-Strategien

`Mapping_Anlagekriterien.xlsx` deckte 14 der 19 Strategien ab. Der Grund war
historisch, nicht fachlich: Die Datei entstand am 10.08.2026 **aus den
PPTX-Vorlagen** und hat damit deren Sicht übernommen — die Thema-Vorlage hat
als einzige keinen Kriterien-Kasten, also stand Thema auch nicht in der Excel.

**Das ist falsch herum gedacht.** Jede Strategie hat Anlagekriterien; dass
eine Vorlage sie nicht abdruckt, ist eine Eigenschaft der **Vorlage**, keine
der Strategie. Im Tool gehören sie überall hin (Philip).

Drei der fünf fehlenden stehen öffentlich auf
`fuggerbank.de/private-banking/pro/` — in genau derselben Vier-Felder-Tabelle
wie die klassischen Strategien:

| Strategie | Anlageregion | Aktienanteil | Anleihenanteil / Liquidität | Fremdwährungen |
|---|---|---|---|---|
| Offensiv | Weltweit | mind. 50 %, max. 100 % | max. 50 % | Unbegrenzt |
| Pro | Weltweit | max. 100 % | **max. 15 %** | Unbegrenzt |
| Pro Dividende | Weltweit | max. 100 % | **max. 15 %** | Unbegrenzt |

**Die Spalte „Anleihenanteil / Liquidität" trägt zwei Bedeutungen — das ist
Absicht und kein Fehler.** Die Webseite nennt bei Pro „Anleihenanteil 0 %"
und im Fließtext eine vertragliche Liquiditätsgrenze von 15 %. Bei
`cVV dynamic` steht in der Excel aus demselben Grund „max. 10 %" — das ist
**die Liquidität**, nicht ein Anleihenanteil (Klarstellung Philip,
12.08.2026). Wer die Zeile mit der Webseite vergleicht und dort „0 %" liest,
möge sie **nicht „korrigieren"**.

**Abgleich der 14 bestehenden Zeilen gegen die Webseite:** 11 der 12
prüfbaren stimmen wörtlich (ESG alle vier, ETF beide, cVV vier von fünf), die
zwölfte ist der eben erklärte Dynamic-Fall. Die drei comdirect-Zeilen sind
nicht prüfbar — **comdirect tritt auf der Homepage nur als Depotbank auf**,
nicht mit eigenen Strategieseiten.

**Warum die Broschüren dabei nicht kippen konnten** (die eigentliche Gefahr):
`pptx_export.py` ruft `fill_anlagekriterien_slide` für **jede** Familie auf —
gesteuert wird der Kasten also von der **Excel**, nicht von der Vorlage. Der
Kommentar dort sagte „Strategien ohne Eintrag (Familie Thema) lassen die
Vorlage unberührt"; mit den neuen Zeilen greift diese Bedingung nicht mehr.
Vorher am Artefakt geprüft: `fill_anlagekriterien_slide` steigt aus, sobald
`finde_anlagekriterien_tabelle` nichts findet, und `Vorlage_Thema.pptx`
enthält keine solche Tabelle. Danach bewiesen: alle sieben Broschüren neu
gebaut, 2056 ZIP-Einträge, 34 Abweichungen, ausnahmslos `docProps/core.xml`
— auch bei Thema, Thema_2 und Thema_3.

**Der Prüfstein trennt jetzt, was vorher vermischt war:** `MIT_KASTEN` (14,
Broschüre) · `THEMA_MIT_EINTRAG` (3, nur Tool) · `NOCH_OFFEN` (2× SCHWEIZ,
bekannte Lücke statt Fehler). Neuer Schritt **4b** tastet alle sechs Vorlagen
ab und schlägt an, wenn `Vorlage_Thema.pptx` eines Tages doch eine
Kriterien-Tabelle bekommt — dann stünden die neuen Werte **plötzlich in
Kundenbroschüren**, ohne dass jemand Code angefasst hat. Neuer Schritt **9b**
wählt in der laufenden App eine Thema-Strategie aus und liest die vier Werte
am Markup nach; Schritt 9 prüft nur die vorausgewählte Strategie und hätte
die Neuerung nicht abgedeckt.

**Übertragbar:** Wenn eine Konfigurationsdatei aus einem Artefakt *abgeleitet*
wird, erbt sie dessen blinde Flecken. Die Excel kannte 14 Strategien, weil 14
Vorlagen einen Kasten hatten — nicht, weil es nur 14 Strategien mit Kriterien
gäbe. Beim Extrahieren lohnt die Frage: Beschreibt die Quelle die Sache oder
nur ihre Darstellung?

### 12.08.2026 (spät) – pyflakes über das ganze Repo sauber

**Backlog 7a erledigt: 16 Meldungen auf 0.** Der Anlass war nicht der
Aufräumzustand, sondern die Prüfung selbst: `CLAUDE.md` schreibt `pyflakes`
nach jedem Umbau vor, und eine Prüfung mit 16 bekannten Meldungen liest
niemand — die nächste echte fällt darin nicht auf.

Keine der 16 war ein Laufzeitfehler. Zwei verwiesen aber auf echte
Geschichte, und die ist der eigentliche Ertrag:

**Die tote `holeSize`-Kette in `chart_dynamik.py`.** In **beiden**
Ring-Funktionen wurde die `holeSize` aus dem Chart-XML gelesen und daraus die
Band-Mitte berechnet — `R_out * (1 + holeSize) / 2`, der Radius, auf den
PowerPoint ein Datenlabel **ohne** `manualLayout` von sich aus setzt.
Gebraucht wurde der Wert nie: `manualLayout`-x/y sind **absolute** Bruchteile
des Rahmens, keine Abstände vom Default. Die Kette (`holeSize` →
`band_mitte` → `dfx`/`dfy` bzw. `band_center`) ist entfernt, die Erkenntnis
steht als Kommentar an beiden Stellen. Wer künftig Label-Positionen anfasst,
muss nicht noch einmal herleiten, warum der PP-Default hier keine Rolle
spielt.

**Das `is_bond` in `portfolio_builder.py` war kein unfertiger Gedanke.**
`git log -S` zeigt: Es steuerte einmal `if is_bond and has_kupon` und
`if is_bond and has_faelligkeit`. Beide Abfragen sind bei einem späteren
Umbau entfallen, die Berechnung blieb liegen. Statt sie wortlos zu löschen,
steht dort jetzt der Hinweis, beim Reaktivieren des Moduls zu prüfen, ob
Kupon und Fälligkeit heute richtigerweise für **alle** Titel gefüllt werden.

**Übertragbar:** Eine unbenutzte Variable ist zweierlei — Schlamperei oder
die Spur einer entfernten Funktion. `git log -S <name>` unterscheidet das in
zehn Sekunden. Wer nur löscht, wirft im zweiten Fall den Hinweis weg.

Der Rest war Formalie: unbenutzte Importe (`clear_table`,
`set_value_axis_min_auto`, `lxml.etree`, drei Farben), eine No-Op-Zuweisung
vor einem `return`, zwei f-Strings ohne Platzhalter. Dazu zwei Kleinigkeiten
mit Substanz: `portfolioanalyse.py` reicht den **privaten** `_folien_config`
nicht mehr durch (der Test holt ihn jetzt aus `vorlagen_config.py`, seiner
Heimat), und die Verfügbarkeitsprobe in `test_bedienung.py` läuft über
`importlib.util.find_spec` statt über `import … # noqa` — **pyflakes kennt
kein `noqa`**, ein Kommentar beruhigt es also nie.

Beweis, nötig vor allem wegen `chart_dynamik.py`: Broschüren gegen den
Ausgangsstand des Tages **byte-identisch** (2056 Einträge, 34× nur
`docProps/core.xml`), `tests/ui_dump.py` vorher/nachher **zeichengleich**,
alle 16 Suiten grün.

### 12.08.2026 (abends) – Dieselbe Funktion an zwei Orten: E, F und der Wrapper-Block

Drei Backlog-Punkte, eine Krankheit. In einem Zug erledigt, weil sie
zusammengehören — und weil beim Nebeneinanderlegen erst sichtbar wird, was
eine einzelne Betrachtung verdeckt.

**F — `fmt_date_de` gab es zweimal, und die Oberfläche stürzte ab.**
`shared.py` (Oberfläche) und `formats.py` (Broschüre) formatierten gültige
Werte gleich, Fehlwerte aber nicht:

| Eingabe | `formats` | `shared` (vorher) |
|---|---|---|
| `None` | `–` | `'None'` |
| `pd.NaT` | `–` | **ValueError** |
| `float('nan')` | `–` | `'nan'` |

`fmt_date_de` wird an 23 Stellen aufgerufen (Auflagedatum, Drawdown-Tiefpunkt,
Erholungsdatum, Quelle-Zeile, Zeitraum-Beschriftungen), `fmt_pct_de` an 29.
Ein `NaT` aus einer unvollständigen Zeitreihe hat dort also nicht „–"
angezeigt, sondern **die Seite abgeräumt**. `shared` reicht beide Namen jetzt
aus `formats` durch — bewusst als Zuweisung statt als `from`-Import, damit
das Weiterreichen sichtbar bleibt und pyflakes die Namen nicht für unbenutzt
hält (es kennt kein `noqa`). `fmt_eur_de` bleibt lokal, weil die Broschüre
keine Beträge ausweist, wurde aber genauso gehärtet.

**E — die 365-Umrechnung stand an vier Stellen**, nicht an drei:
`annual_fee_to_daily_drag`, `calc_sharpe_excess`, `aggregate_rf_geometric`,
`make_index_from_rf`. Neu ist `analytics.annual_to_daily_rate(annual_rate)`,
die Einzelwert *und* Reihe nimmt. **Der Honorarsatz behält seinen eigenen
Namen** und ruft die neue Funktion nur auf: Die Mathematik ist identisch, die
Größen sind es nicht — ein Honorar wird abgezogen, ein Zins gutgeschrieben.
Wer `annual_to_daily_rate(fee)` liest, sieht dem Aufruf das Vorzeichen nicht
mehr an; der sprechende Name ist die Verständlichkeit wert.

Weil es um Kundenzahlen geht, wurde **vor** dem Umbau nachgemessen, dass der
Weg über `np.asarray` bit-identisch ist — an allen vorkommenden Sätzen (0 %,
1,023 %, 1,2 %, 1,55 %, 3 %) und für Arrays. Wäre er es nicht gewesen, hätte
sich die letzte Nachkommastelle jeder Broschüre verschoben.

**Wrapper-Block — es waren zehn, nicht sieben.** Drei standen nicht im Block
oben, sondern verstreut weiter unten (`calc_sharpe_excess`,
`calc_period_return`, `calc_period_return_after_fee`). Einer war tot, die
übrigen neun hingen an 25 Aufrufstellen. Ertrag: **−4 Zeilen netto** — an die
Stelle der Attrappen ist eine Erklärung getreten. Gemacht wurde es trotzdem,
aus demselben Grund wie bei den 40 in `pptx_export.py`: Eine Attrappe mit dem
Namen einer echten Funktion führt die Suche in die Irre. Was blieb, sind die
acht Funktionen, die es in `analytics` nicht gibt, weil die Broschüre sie
nicht braucht (Euro-Drawdown, Calmar, DD-Dauer und -Erholung, Datums-
Varianten des MDD, rf-Index).

**Beweismittel für einen UI-Umbau — neu und nachnutzbar:** Für Broschüren gab
es den rekursiven ZIP-Vergleich; für die Oberfläche gab es bisher nichts
Vergleichbares. Jetzt schon: Die App per AppTest hochfahren und **alle**
Kennzahlen, Captions, Markdown-Blöcke und Tabellen als JSON abziehen — vor
und nach dem Umbau. Beide Dumps waren zeichengleich (3806 Zeichen), erfasst
sind unter anderem Rendite p.a., Volatilität, Calmar, Sharpe und das
Auflagedatum. Das deckt die Standard-Ansicht ab, nicht jeden
Interaktionspfad — dafür stehen die drei AppTest-Suiten daneben. Das Skript
ist keine zehn Zeilen und gehört beim nächsten UI-Umbau wieder eingesetzt.

Alle 16 Suiten grün, `pyflakes` sauber, Broschüren unverändert.

### 12.08.2026 – Prüfsteine für analytics und formats; drei Fehler dabei gefunden

**Backlog D erledigt.** Die beiden streamlit-freien Module hatten keine
eigenen Tests: `analytics.py` wurde nur indirekt über zwei Suiten mitgezogen,
`formats.py` gar nicht — obwohl **jede Kennzahl jeder Kundenfolie** durch
dessen vier Funktionen läuft.

Neu: `tests/test_analytics.py` (braucht nur numpy/pandas) und
`tests/test_formats.py` (braucht **gar nichts**, Schritt 5 nutzt pandas, wenn
vorhanden). Zusammen 90 Einzelprüfungen.

**Die Runde hat drei Fehler gefunden** — alle drei bei degenerierten
Eingaben, keiner bei den fachlich interessanten Fällen (Transferwissen #47):

| Fund | Wirkung | Status |
|---|---|---|
| `calc_sharpe_excess` prüfte `sd == 0` | Bei konstanten Renditen bleibt eine Reststreuung von 2,3e-19; die Sharpe Ratio wurde zu **8,36e16** | korrigiert: `sd < 1e-12` |
| `fmt_date_de(float('nan'))` | lieferte wörtlich **`"nan"`** — eine leere Excel-Zelle kommt als NaN an, nicht als None | korrigiert: `–` |
| Doctest von `calc_period_return` | behauptete `-0.000198`, richtig ist `-0.000302` (1,01 × 1,01 × 0,98) | Doku korrigiert, **Code war richtig** |

Nur die ersten beiden ändern Verhalten, und beide nur dort, wo bisher Unsinn
herauskam. **Beweis, dass sonst nichts kippt:** alle sieben Broschüren erneut
gegen den Ausgangsstand von heute früh verglichen — 2056 ZIP-Einträge, 34
Abweichungen, ausnahmslos `docProps/core.xml`. Alle 16 Testsuiten grün,
`pyflakes` sauber.

**Was die Tests inhaltlich festnageln** — über die Grenzfälle hinaus:
die 10-%-hoch-10-%-runter-Falle (100 → 110 → **99**, nicht 100), Drawdown von
120 auf 90 als **−25 %** und nicht −10 %, die Gleichheit von
Periodenrendite-nach-Kosten und Index-Endstand (zwei Wege durch dieselbe
Mathematik — laufen sie auseinander, widersprechen sich Kennzahlen-Tabelle
und Chart), und die Längengleichheit von `dates` und `referenz` im
Linien-Chart. Dazu der Vertrag aus #46: ohne Benchmark sind die Listen
**leer**, nicht mit Nullen gefüllt.

**Neu aufgenommen: Backlog F.** Beim Testen fiel auf, dass `fmt_date_de`
zweimal existiert — in `formats.py` (gehärtet) und in `shared.py` (nicht).
`shared.fmt_date_de(pd.NaT)` wirft eine **ValueError**, und die Oberfläche
ruft die Funktion an rund 15 Stellen auf. Nicht in dieser Runde angefasst:
eigenes Thema, eigener Beweis.

### 12.08.2026 – Die Honorar-Mathematik steht nur noch an einer Stelle

**Backlog B erledigt.** `modules/pptx_export.py` hatte eigene Kopien der
Kosten-Rechnung: `_annual_fee_to_daily_drag` (drei Aufrufstellen) und
`_make_index_after_fee` (zwei). Beide sind entfernt; die Funktionen kommen
jetzt per Import aus `modules/analytics.py`.

**Warum das kein Schönheitsumbau war.** Die Formeln waren identisch — genau
deshalb sah niemand ein Problem. Das Problem war die Zukunft: Wer den
Honorarabzug in `analytics` korrigiert hätte, hätte die **Broschüre nicht
mitkorrigiert**, denn die rechnete mit ihrer eigenen Kopie. Und die Broschüre
geht zum Kunden. Es ist derselbe Mechanismus wie beim SCHWEIZ-Honorarfehler
vom 11.08.: eine Kostengröße, die an einer Stelle stimmte und an der anderen
nicht, ohne dass es jemandem auffiel.

**Warum es gefahrlos ging.** Die alte Begründung für das Vertagen lautete, der
Umbau berühre `compute_wertentwicklung_data`. Das stimmt, ist aber
unproblematisch: die analytics-Fassung ist formelgleich und durch das
vorgeschaltete `np.asarray` sogar toleranter bei der Eingabe. `analytics.py`
importiert nur numpy und pandas — der Export bleibt streamlit-frei und damit
batchfähig (Abschnitt 13). Der Import steht deshalb auf Modulebene, nicht
lazy.

**Beweis.** Alle sieben Broschüren vor und nach dem Umbau erzeugt und
rekursiv verglichen (PPTX sind ZIPs mit eingebetteten ZIPs): **2056
ZIP-Einträge, 34 Abweichungen, ausnahmslos `docProps/core.xml`** — der
Erzeugungs-Zeitstempel. Dieselbe Signatur wie beim Wrapper-Umbau am 11.08.
`pyflakes` sauber, alle 15 Testsuiten grün.

**Prüfstein: `tests/test_kosten_mathematik.py`** (neu). Drei Schritte —
(1) Quelltextscan: keine Zeile außerhalb von `analytics.py` darf die
365-Tage-Basis mit einem Honorar-Begriff verbinden; (2) Identität: die Namen
in `pptx_export` sind *dasselbe Funktionsobjekt* wie in `analytics`, und die
alten `_`-Kopien sind weg; (3) Zahlen: 1,55 % p.a. ergeben 0,4214 Basispunkte
pro Tag, 365 Nulltage kosten 1,5264 von 100, Startwert 1.0 und 100.0
skalieren identisch. Auf dem alten Stand ist der Test **rot** (Schritte 1+2),
danach grün — nachgewiesen, nicht behauptet.

Schritt 1 unterscheidet bewusst nach Honorar-Begriffen (`fee|honorar|drag`):
Der risikofreie Zins nutzt dieselbe 365-Tage-Basis, ist aber eine andere
Größe und darf weiterhin an mehreren Stellen stehen.

**Nebenbefund, nicht angefasst:** Die *rf*-Tagessatz-Umrechnung
`(1+rf)^(1/365)-1` steht dreifach — `analytics.py:231` sowie
`streamlit_app.py:144` und `:158`. Andere Größe, dieselbe Bauart. Eigenes
Thema, siehe Backlog.

### 11.08.2026 – Zurücksetzen im eigenen Zeitraum; Korrektur an Transferwissen #19

**Zurücksetzen-Knopf** neben den Kalenderfeldern, sichtbar nur bei
eingeschaltetem „Eigener Zeitraum" (Philip). Vorher klebten die Felder an
ihren Werten, sobald sie einmal angefasst waren — die Schnellwahl darüber
änderte dann nichts mehr, und es gab keinen Weg zurück außer Neuladen.
Zurückgesetzt wird auf den Zeitraum, den die Schnellwahl gerade vorgibt.

Umgesetzt mit **Counter-Keys** (`p_sd_0`, `p_sd_1`, …) nach Transferwissen
#4, Lösung A: `st.session_state["p_sd"] = …` wirft bei einem aktiven Widget.
Der Test `test_bedienung.py` prüft deshalb jetzt auf Key-PRÄFIX statt auf
exakte Namen — und prüft die Wirkung, nicht die Existenz: Datum verstellen,
klicken, Vorgabe muss zurück sein.

**Dabei ein Doku-Fehler aufgeflogen (#19).** Der Knopf ließ die App sofort
abstürzen. Ursache: Das Keep-Alive re-assigniert alle session_state-Keys,
und für Button-Keys ist das verboten — nur wirft die Zuweisung selbst nichts,
sondern erst das spätere `st.button()`. Das dokumentierte `try/except` fängt
das folglich nicht. #19 und Abschnitt 8.5 sind entsprechend korrigiert; die
Regel lautet jetzt unmissverständlich: **jeder neue Button mit `key=` gehört
in `_KEEPALIVE_SPERRE`.**

### 11.08.2026 – Honorarsatz SCHWEIZ ergänzt; Hinweis „keine Benchmark" im Tool

**Die beiden SCHWEIZ-Strategien fehlten in `Mapping_Honorarsatz.xlsx`** — 17
Zeilen bei 19 Strategien. Aufgefallen ist das nie, weil `shared.py` den
Fehlschlag abfängt und still auf `fd = 0.0` zurückfällt. Die App zeigte für
beide „nach Kosten"-Zahlen, in denen keine Kosten steckten. Auf Philips
Anweisung jetzt mit **1,55 % netto** ergänzt (Brutto 1,8445 % = ×1,19, wie in
allen übrigen Zeilen außer Comdirect).

Das verschiebt die ausgewiesenen Werte deutlich:

| Strategie | Performance p.a. | kumuliert gesamt |
|---|---|---|
| SCHWEIZ Substanz | 6,96 % → **5,33 %** | 29,43 % → **22,02 %** |
| SCHWEIZ Aktien | 9,01 % → **7,35 %** | 39,52 % → **31,47 %** |

Die neuen Werte sind die richtigen. Neuer Prüfstein
`tests/test_honorarsatz.py`: jede Strategie in den Daten braucht eine Zeile im
Mapping und einen Satz zwischen 0,5 % und 3 % p.a. Der Rückfall auf `0.0`
bleibt als Schutz im Code — er taugt nur nicht als Anzeige, und genau das
fängt der Test jetzt ab.

**Hinweis im Tool.** Über den Kennzahlen steht jetzt eine Caption, wenn eine
Strategie keinen Vergleichsmaßstab hat. Sie ersetzt den bisherigen Hinweis
unter dem Linien-Chart, der nur erschien, wenn der Benchmark-Schalter an war —
war er aus, blieb das „–" in den Kacheln unkommentiert. Die Erkennung läuft
über `has_benchmark`, nicht über eine Namensliste: der Hinweis gilt damit
automatisch für jede weitere Strategie ohne Benchmark. Geprüft an der
gerenderten Oberfläche (`test_benchmark_charts.py`, Schritt 3): genau einmal
bei SCHWEIZ, nie bei „Pro", in beiden Schalterstellungen.

### 11.08.2026 – SCHWEIZ ohne Benchmark; Wrapper raus; Versionen gedeckelt

**Backlog A — der Vergleichsmaßstab war noch an drei Stellen da.** Nachdem
`has_benchmark` am 07.08. die Kennzahlen korrigiert hatte, zeigte die
SCHWEIZ-Broschüre die Benchmark weiterhin im Säulen-Chart (vier Null-Balken),
in der Legenden-Textbox und in der Fußnote. Die Fußnote trug den
**unveränderten Vorlagentext** — die Benchmark der Strategie „Pro". Ursache:
`analytics` füllte die Chart-Serien mit `0.0`/`1.0` auf, statt sie leer zu
lassen; „es gibt keine" war damit von „sie ist null" nicht mehr zu
unterscheiden. Jetzt liefert `compute_performance_data` ein
`has_benchmark`-Kennzeichen und leere Listen, `pptx_slides` legt die Serie
gar nicht erst an (python-pptx entfernt das überzählige `<c:ser>` selbst) und
räumt Legendeneintrag und ***-Zeile ab. Standardwert des Schalters ist
bewusst `True`. Vollständige Herleitung: **Transferwissen #46**.
Prüfstein: `tests/test_benchmark_charts.py`.

**Backlog C — Wrapper raus.** 40 Durchreich-Funktionen aus `pptx_export.py`
entfernt (1303 → 1010 Zeilen). 27 davon wurden nirgends aufgerufen, die
übrigen 13 an je einer bis drei Stellen; die Backlog-Warnung „viele
Aufrufstellen" war schlicht falsch. `_load_template` blieb — sie ist kein
Durchreicher, sondern ergänzt einen Folienzahl-Guard. Der Import-Block
schrumpfte von 115 auf 58 Zeilen, pyflakes meldet die Datei jetzt ohne
Beanstandung (vorher 44 ungenutzte Importe). Beweis der Wirkungsgleichheit:
alle sieben Broschüren vorher/nachher rekursiv verglichen, von 2056
ZIP-Einträgen unterschieden sich 34 — ausnahmslos `docProps/core.xml`, also
der Erzeugungs-Zeitstempel.

**Nicht angefasst:** der gleichartige Wrapper-Block in `streamlit_app.py`
(Zeilen 62–88). Der ist nicht tot, und zwischen den Durchreichern stehen
echte UI-Helfer.

**Backlog 1 — requirements nach oben gedeckelt.** Bis dahin standen
`pandas>=2.0` und `numpy>=1.24` nach oben offen; genau diese beiden hatten am
06.07. den Ausfall verursacht. Jetzt hat **jede** Zeile eine Obergrenze auf
die nächste Hauptversion, Untergrenze ist der Stand, mit dem an diesem Tag
alle zwölf Testsuiten und sieben Broschüren durchgelaufen sind. Bewusst keine
`==`-Pins: die waren am 06.07. der zweite Fehlschlag, weil sie auch die
Python-Kompatibilität einfrieren (Transferwissen #20, Punkt 4). Die Datei
trägt die Begründung als Kommentar — dort schaut jemand nach, wenn die App
wieder „gestern noch lief". Verifiziert per `pip install --dry-run
--ignore-installed`: die Auflösung landet exakt auf dem getesteten Satz.
Offen bleibt die Bestätigung im Deploy-Log, weil lokal unter Python 3.12
geprüft wurde und die Cloud 3.14 nutzt.

### 11.08.2026 – Bedienbarkeit, Runden 2–4: Beschriftungen, Bedienfluss, Auftritt

**Beschriftungen.** Der Kostenhinweis stand in *jeder* Kennzahlen-Kachel und
erzeugte Klammern in Klammern („⌀ Rendite p.a. (nach Kosten (exkl.
MwSt.))"). Er steht jetzt **einmal** über der Kachelreihe; die Kacheln heißen
schlicht „⌀ Rendite p.a.", „Volatilität p.a.", „Calmar Ratio", „Sharpe
Ratio". „Auflagedatum im PM" → „Auflage der Strategie", „Recovery" →
„Erholungsdauer". Das Honorarfeld heißt jetzt **„Honorar % p.a. (netto)"** —
vorher verriet erst der Schalter darunter, dass die Eingabe ohne MwSt.
gemeint ist. Acht Schalter haben Hilfetexte bekommen; „Vor Kosten" erklärt
ausdrücklich, dass es nur eine zusätzliche Linie einblendet und die
Kennzahlen unberührt lässt.

**Zeitraum-Schnellwahl.** Statt zweier Kalenderfelder plus zweier
Zurücksetzen-Schaltflächen: **1 Jahr · 3 Jahre · 5 Jahre · 10 Jahre · Seit
Auflage**. Die Kalenderfelder erscheinen nur, wenn „Eigener Zeitraum"
angehakt ist (Wunsch Philip). „Seit Auflage" ersetzt beide
Zurücksetzen-Schaltflächen. Gemessen: 3 Jahre = 1096 Tage, 1 Jahr = 365,
10 Jahre = 3652. Liegt der berechnete Start vor dem ersten Datenpunkt,
gewinnt der erste Datenpunkt — sonst zeigte „10 Jahre" bei einer jungen
Strategie einen leeren Anfang.

**Seitenleiste gruppiert** in *Auswahl · Darstellung · Honorar*. Keine
Funktion ändert sich, nur die Ordnung. Die Fehlermeldung bei verdrehtem
Zeitraum sagt jetzt, was zu tun ist.

**Auftritt.** Das Logo lag im Repo und wurde ausschließlich in die frühere
PDF-Ausgabe eingebettet — es steht jetzt über dem Anmeldetitel. Der
Datenstand steht neben der Ansichtsumschaltung statt als Fußzeile.

⚠️ **Eine Falle beim Expander.** „Erweiterte Einstellungen" war ein
Kontrollkästchen und sollte laut Durchsicht ein `st.expander` werden. Beim
Umbau fiel auf: **Ein Expander rendert seinen Inhalt immer, auch
zugeklappt.** Hätte man den Datenstand-Wechsel allein daran gekoppelt, wäre
ein einmal eingetippter Date-Tag für immer wirksam geblieben — auch wenn
längst neuere Daten vorliegen, und ohne dass man es sieht. Deshalb: Expander
für die *Gruppierung*, ein ausdrückliches Häkchen „Anderen Datenstand
verwenden" als *Auslöser*.

**Prüfstein** `tests/test_bedienung.py` — prüft alles am **laufenden
Programm** per AppTest: die Zeitraum-Rechnung für drei Stufen, dass keine
PDF-Schaltfläche und keine reportlab/matplotlib-Reste existieren, dass die
Benchmark-Zusammensetzung in beiden Schalterstellungen **genau einmal**
erscheint, und dass Logo und Datenstand da sind.

Beim Schreiben des Tests selbst gelernt: `at.get("imgs")` liefert eine
**leere Liste statt eines Fehlers** — der Elementname heißt in Streamlit 1.61
`"image"`. Wer auf das Gelingen des Aufrufs prüft statt auf den Inhalt,
bekommt einen falschen Fehlschlag. Und `at.session_state` kennt kein `.get()`.

### 11.08.2026 – Bedienbarkeit, Runde 1: die drei echten Fehler

Aus der Durchsicht der Anwendung (14 Befunde, erhoben per `AppTest` am
laufenden Programm). Runde 1 sind die Punkte, die Nutzer direkt treffen.

**PDF-Ausgabe komplett entfernt.** Entscheidung von Philip: Kundendokumente
entstehen ausschließlich als PowerPoint. Der PDF-Weg hatte ohnehin einen
Konstruktionsfehler — Erzeugen und Herunterladen waren zwei Schaltflächen,
die Bytes lagen nur in einer lokalen Variablen; nach der nächsten Interaktion
war der Download weg. Entfernt: `generate_perf_pdf` (179 Zeilen), die drei
matplotlib-Bildbauer (`_mpl_line_chart`, `_mpl_drawdown_chart`,
`_mpl_bar_chart`, 65 Zeilen — sie rendern **nur** fürs PDF), der UI-Block,
die reportlab-Importe und die PDF-Schriftregistrierung in `shared.py`.
**−296 Zeilen**, und `reportlab` + `matplotlib` fallen aus
`requirements.txt` — zwei schwere Bibliotheken weniger im Deploy.

Vorgehen dabei: Für **jede** Hilfsvariable wurde einzeln geprüft, ob sie nur
dem PDF dient. `dfr` (rollierende Tabelle) wird auch auf dem Bildschirm
gezeigt und blieb; `md`, `bdl`, `plt_`, `pdd`, `lp` waren PDF-only und sind
weg. Das Entfernungs-Skript arbeitete mit **Ankern im Text statt
Zeilennummern** und brach beim ersten mehrdeutigen Anker ab — es lief zweimal
ins Leere, bevor es schrieb (einmal wegen CRLF im Arbeitsverzeichnis). Genau
so soll es sein.

**Benchmark-Zusammensetzung stand doppelt.** Sie wurde am Performance-Chart
*und* am Balken-Chart ausgegeben; beide auslösenden Schalter sind
standardmäßig an, der Doppel-Eintrag war also der Normalfall. Jetzt genau
einmal: am Chart, wenn „Benchmark" aktiv ist — sonst am Balken-Chart, dessen
Balken die Benchmark ja trotzdem zeigen.

**33 × `use_container_width` migriert.** Der Parameter ist abgekündigt,
Streamlit warnt bei jedem Aufruf. Die Regel wurde aus den **echten
Signaturen** von Streamlit 1.61 abgeleitet, nicht geraten:

| Element | Default | `use_container_width=True` wird zu |
|---|---|---|
| `dataframe`, `plotly_chart`, `data_editor` | bereits `"stretch"` | **ersatzlos gestrichen** |
| `button`, `download_button` | `"content"` | `width="stretch"` |

**Prüfstein** `tests/test_streamlit_api.py` — läuft ohne jedes Paket und
sperrt den abgekündigten Parameter. Auf dem alten Stand rot mit exakt 33
Befunden. Der Grund für einen Test statt eines Changelog-Eintrags: Der
Parameter steht in jeder älteren Anleitung im Netz und schleicht sich beim
nächsten Copy-Paste zurück.

### 10.08.2026 (spät) – Piktogramme aus der Oberfläche entfernt

Philip: Emoji vor Überschriften und Disclaimern wirken unprofessionell. Für
eine Privatbank mit gehobener Kundschaft — die Ergebnisse gehen ins
Kundengespräch — ist das nachvollziehbar.

**67 Zeilen** in fünf Dateien bereinigt: Navigations-Beschriftungen, alle
`st.subheader`, Hinweis- und Quellenzeilen, Schaltflächen, Download-Texte.
Kommentare und Docstrings bleiben unangetastet — die sieht kein Nutzer.

⚠️ **Zwei Piktogramme waren keine Dekoration, sondern Logik:**

1. `build_grouped_title_table` markierte die Liquiditäts-Gruppe mit einem
   vorangestellten Geldsack-Symbol; die Anzeige entschied per
   `startswith(...)`, ob eine Gruppe die Liquidität ist. Ein blindes
   Entfernen hätte die Prüfung **still** auf immer-False gesetzt — ohne
   Fehler, ohne Absturz, nur mit falscher Darstellung. Jetzt trägt die
   Konstante `GRUPPE_LIQUIDITAET` die Bedeutung. Auch `portfolio_builder.py`
   hing daran und ist mit umgestellt.
2. Im Builder war `"🗑️"` ein **Spaltenschlüssel** eines DataFrames, an
   sechs Stellen verwendet (`insert`, `column_config`, `row[...]`, `drop`).
   Umbenannt auf `"Entfernen"` — alle Stellen zugleich.

Dazu eine Ampel aus 🟢/🔴 in `st.metric`: ersetzt durch einen `delta`-Text
(„weicht von 100 % ab"). Eine Aussage, die nur in einer Farbe steckt, ist
ohnehin nicht barrierefrei.

**Prüfstein** `tests/test_keine_piktogramme.py` — läuft **ohne jedes Paket**
(reine Textprüfung). Erkennt Piktogramme (U+1F300–U+1FAFF) und Zeichen mit
Emoji-Variantenselektor (U+FE0F), überspringt Kommentarzeilen. Auf dem alten
Stand rot mit 67 Befunden.

**Merke für künftige Sweeps:** Ein Skript, das Zeichen aus Quelltext
entfernt, erwischt auch **Docstrings, die diese Zeichen erklären** — genau
das passierte hier mit der Begründung zum Geldsack-Marker. Nach solchen
Aktionen den Diff lesen, nicht nur die Tests laufen lassen.

`modules/portfolio_builder.py` ist nicht importiert (mögliche
Reaktivierung) und daher **nicht zur Laufzeit prüfbar**; dort wurde
`py_compile` als Mindestabsicherung gefahren.

### 10.08.2026 (spät) – Anlagekriterien: eine Quelle für Tool und Broschüre

Der Anlagekriterien-Kasten der Struktur-Folien wandert ins Streamlit-Tool.
In drei Schritten umgesetzt.

**Schritt 1 — `Mapping_Anlagekriterien.xlsx`.** Eine Zeile je Strategie,
Schlüssel ist die Spalte „Strategie auswählen" wie in `Mapping_Namen.xlsx`.
Die Spaltenüberschriften **sind** die gedruckten Beschriftungen — keine
zweite Liste, die auseinanderlaufen kann. 14 Strategien (CVV 5, ESG 4,
ETF 2, comdirect 3); die Thema-Familie hat keinen Kasten und bleibt außen vor.

**19 Bereinigungen**, mit Philip abgestimmt — diese Texte standen so in
Kundenbroschüren: Tippfehler `FPFB Strategie 30` → `FFPB`, `AUsgewogen` →
`Ausgewogen`; Groß-/Kleinschreibung der Anzeigenamen (`defensiv`,
`ausgewogen`, `dynamic`); `min.` → `mind.`; Aktienanteil `-` → `keine`
(Wortlaut der Webseite); bei CVV Dynamic hieß die Zeile nur `Liquidität`
statt `Anleihenanteil / Liquidität`; zehnmal Prozent einheitlich mit
Leerzeichen (DIN 5008).

**Schritt 2 — Banner im Tool**, in beiden Ansichten: Performance zwischen
Kennzahlen und Wertentwicklung, Portfolioanalyse direkt unter den
Bestandszahlen. Dort ist der fachliche Gewinn: Investitionsgrad und
erlaubter Aktienanteil stehen erstmals nebeneinander.

⚠️ **Einmal überarbeitet — die Lehre:** Die erste Fassung war ein
HTML-Block mit eigener heller Fläche und Fuggerblau als Textfarbe. Im
**Dark Mode** stand ein greller weißer Kasten in der dunklen App. Der
naheliegende Fix `var(--background-color)` wurde geprüft und verworfen:
**Streamlit 1.61 stellt keine Theme-CSS-Variablen bereit** (weder in
`static/css` noch im JS-Bundle nachweisbar) — die Variable wäre still ins
Leere gelaufen. Jetzt ohne eine Zeile eigenes CSS:
`st.container(border=True)` + `st.columns` + `st.caption` + fettes
`st.markdown`. **Regel: eigene HTML-Bausteine in Streamlit nur, wenn sie
ohne Farbannahmen auskommen.**

**Schritt 3 — Rückweg in die PowerPoint.** `fill_anlagekriterien_slide`
schreibt die Konfiguration beim Export in den Kasten. Die Tabelle wird
**inhaltsbasiert** gefunden (Kopfzelle „Anlagekriterien"), nicht über den
Shape-Namen — der ist „Tabelle", und so heißt auf der Wertentwicklungs-Folie
die Kennzahlen-Tabelle. Die leere Abstandsspalte 1 bleibt unberührt.

**Beweis, dass nichts kaputtgeht** (Vorher/Nachher über alle sieben
Broschüren): **genau 19 Zellen geändert — 0 Änderungen außerhalb der
Kästen**, ZIP-Struktur identisch, Thema unberührt. Formatvergleich über 210
Zellen: Schriftgröße, Fettung, Schriftart und Farbe unverändert.

Ein Zwischenbefund dabei: In der Vorlage bestand die Zelle
„Anleihenanteil / Liquidität" aus **zwei Runs** (`'Anleihenanteil'` +
`' / Liquidität '`). `set_cell_text_preserve_format` führt sie zu einem
zusammen. Geprüft statt angenommen: beide Runs trugen identisches Format
(9 pt, nicht fett, keine Farbe) — der Split war ein Bearbeitungsartefakt,
das Zusammenführen ist folgenlos.

**Architektur:** Die Kriterien-Logik steht in `modules/anlagekriterien.py`
und ist **streamlit-frei**, weil `pptx_export.py` sie ebenfalls braucht und
bewusst ohne Streamlit läuft (Batch-Fähigkeit, Abschnitt 13). `shared.py`
legt für die App nur `@st.cache_data` darum. Zwei Loader wären genau die
Duplizierung, an der die Codebasis früher krankte.

**Prüfstein** `tests/test_anlagekriterien.py`, zehn Schritte — vom Aufbau der
Excel über die Bauweise des Banners und einen **AppTest in beiden Ansichten**
bis zum Kasten in der erzeugten Broschüre (Schritt 10, nur mit
Ordner-Argument). Gegenproben gefahren: gegen den unbereinigten
Vorlagenstand 14 Abweichungen, gegen die alten Broschüren rot.

### 10.08.2026 (abends) – Ring-Label-Positionierung vermessen, bewusst NICHT geändert

Philips Anliegen: kleine und dicht benachbarte Segmente wirken gedrängt, die
Zuordnung Segment ↔ Prozentwert ist nicht sofort klar. Es wurde **gemessen,
diagnostiziert, zwei Experimente gefahren — und dann entschieden, den Stand
zu belassen** („wir sind am Zenit angekommen"). Details in Transferwissen #44.

**Am Code wurde nichts geändert.** `chart_dynamik.py` ist bitweise identisch;
beide Experimente wurden zurückgerollt. Dieser Eintrag existiert, damit die
Diagnose nicht verlorengeht.

### 10.08.2026 (nachmittags) – Das Tool trägt überall denselben Namen

Philip beim Anmelden aufgefallen: Der Login-Bildschirm hieß „Performance VV
Rechner | Fürst Fugger Privatbank" — das Tool kann aber auch die
Portfolioanalyse, die im Namen gar nicht vorkam.

Beim Nachsehen: es gab **drei** Namen.

| Wo | vorher |
|---|---|
| Login (`modules/shared.py`) | Performance VV Rechner \| Fürst Fugger Privatbank |
| Browser-Tab (`streamlit_app.py`) | FFPB – Performance & Portfolioanalyse |
| Kopfzeile nach dem Login | Fürst Fugger Privatbank – Vermögensverwaltung |

Neu an allen drei Stellen: **„Performance & Portfolioanalyse | Fürst Fugger
Privatbank"**, aus der neuen Konstante `shared.APP_TITLE`
(`APP_NAME` + `BANK_NAME`). Der Name benennt genau die beiden Bereiche der
Navigation (📈 Performance / 📊 Portfolioanalyse). „Rechner" ist bewusst
raus — das Tool erzeugt die fertigen Kundenbroschüren, es rechnet nicht nur;
„VV" als Haus-Jargon ebenfalls, das gehört nicht auf einen
Anmeldebildschirm.

Konstante statt Literal, weil genau die Duplizierung zu den drei Namen
geführt hat — dieselbe Lehre wie bei den Loadern und der Mathematik.

Prüfstein `tests/test_app_titel.py`: Wortlaut der Konstante, keine alten
Namen mehr als Literal (14 Dateien), und Schritt 3 fährt die App per
**AppTest** hoch und liest den Titel aus dem gerenderten Login-Bildschirm
(Transferwissen #24) — nicht aus dem Quelltext. Auf dem alten Stand rot
(4 Abweichungen).

⚠️ **Falle beim AppTest:** `check_login` liest `st.secrets["passwords"]`.
Ohne Secrets wirft die App eine Exception, *bevor* der Titel gerendert wird
— der Test wäre dann aus dem falschen Grund rot. `secrets.toml` ist bewusst
nie committet, deshalb setzt der Test ein Wegwerf-Passwort über
`at.secrets[...]` im Speicher. Wer weitere AppTests schreibt: daran denken.

### 10.08.2026 – Legende der Wertentwicklungs-Folie: zurück auf „Musterdepot"

Von Philip an der ETF-Broschüre bemerkt (F19, „ETF Wachstum"): Die Legende
zeigte `Referenzportfolio    Benchmark***`, die Vorlage sagt aber
`Musterdepot    Benchmark***`.

**Befund.** Der Begriff stand nie in der Vorlage — `fill_wertentwicklung_slide`
schrieb ihn beim Befüllen um (Ersetzung `'Musterdepot '` →
`'Referenzportfolio '` plus Kürzung des 5-Leerzeichen-Lücken-Runs auf 3,
damit `…Benchmark***` weiter in die 2,24"-Box passt). Eingeführt am
02.07.2026 als „Punkt 3, Wording-Vereinheitlichung".

Verifiziert an der Slide-XML aller sechs Vorlagen (PPTX als ZIP gelesen) —
**„Musterdepot" steht überall im Original**:

| Vorlage | Folien | Begriff |
|---|---|---|
| `Vorlage_ETF.pptx` | 17, 19 | Musterdepot |
| `Vorlage_cVV_Infoboard.pptx` | 8, 10, 12, 14, 16 | Musterdepot |
| `Vorlage_ESG.pptx` | 17, 19, 21, 23 | Musterdepot |
| `Vorlage_comdirect.pptx` | 7, 9, 11 | Musterdepot |
| `Vorlage_Thema.pptx` | 12 | Musterdepot |
| `Vorlage_FFPB.pptx` | 11 | Musterdepot |
| `Vorlage_FFPB.pptx` | **10** | **Referenzportfolio** ← performance-Folie |

**Warum die Begründung von damals nicht trug.** Der Angleich zielte auf die
performance-Folie, die „Referenzportfolio" tatsächlich statisch führt
(FFPB slide10, auch im Folientitel). Diese Rolle kommt aber in **keiner**
Familien-Konfiguration vor (`VORLAGEN_FAMILIEN` kennt nur
`wertentwicklung`) — sie existiert nur in
`pptx_export.DEFAULT_TEMPLATE_CONFIG`, Position 10. In den fünf
Familien-Broschüren gab es also gar keine Folie, zu der angeglichen werden
konnte; die Umschreibung entfernte sich dort nur von der Vorlage.

**Änderung.** Die Legenden-Umschreibung ist ersatzlos entfallen (die Vorlage
wird nicht mehr angefasst), `WE_SERIES_PORTFOLIO` steht auf `"Musterdepot"`.
Die performance-Folie behält „Referenzportfolio" — **bewusste Abweichung**,
als Kommentar an beiden Stellen vermerkt: jede Folie folgt ihrer eigenen
Vorlage. Betroffen sind alle 15 Wertentwicklungs-Folien über alle Familien.

Prüfstein `tests/test_legende_musterdepot.py`: prüft die Vorlagen-Invariante
(stdlib, ohne python-pptx — PPTX ist ein ZIP), den Serienamen und die Wirkung
am echten Artefakt. Auf dem Stand vom 07.08.2026 rot.

Nebenbefund: `replace_substring_in_runs` (pptx_slides.py) hat damit keinen
Aufrufer mehr. Als generischer Helfer stehen gelassen und im Docstring
markiert — Kandidat für die nächste Aufräumrunde.

⚠️ Merkposten für die Vorlagenpflege: Wer den Begriff künftig ändern will,
ändert die **Vorlage**, nicht den Code. Die Legenden-Box enthält
Wingdings-2-Farbquadrate und hochgestellte Runs (`baseline="14000"`); eine
Code-Ersetzung gefährdet die Formatierung ohne Not.

### 07.08.2026 (nachmittags) – Broschüren-Korrekturen aus der Sichtprüfung

Beides von Philip beim Durchsehen echter Broschüren gefunden — Fehlerklassen,
die kein Test von allein entdeckt, weil das Ergebnis plausibel aussieht.

**Trennstriche saßen an den Vorlagen-Positionen** (Transferwissen #42).
`fill_table_with_positions` schrieb Text und Fettung, fasste Rahmenlinien
aber nie an. Bei CVV „Defensiv" lief der dicke Strich mitten durch die
Rentenliste (Fraport ↔ Fresenius), während der Übergang Würth → AKTIEN
keinen bekam. Über alle Familien: 80 falsch platzierte Striche.
Neu: `tabelle_kategorie_trennlinien()` — dicker Strich genau unter der
Kategorie-Überschrift, Linienarten spaltenweise aus der Vorlage geerntet
statt nachgebaut. Prüfstein `tests/test_trennstriche.py`.

**Historie begann im falschen Jahr** (Transferwissen #43).
Die cVV-Reihen starten am 30.12.2008 (zwei Zeilen = Indexbasis). Die
Broschüre schrieb „Wertentwicklung seit 2008 kumuliert". Neu: `HISTORIE_AB`
je Datenreihe + `historie_beschneiden()`, angewandt an EINER Stelle vor
allen Berechnungen — Beschriftung, Kennzahlen und Chart ziehen automatisch
mit. Betroffen sind die fünf CVV-Strategien **und „Offensiv"** (Familie
Thema, nutzt `Muster offensiv cVV`).

| Strategie | vorher | nachher |
|---|---|---|
| Konservativ | seit 2008 · 46,38 % | seit 2009 · 46,40 % |
| Defensiv | seit 2008 · 80,68 % | seit 2009 · 80,39 % |
| Defensiv Plus | seit 2008 · 114,57 % | seit 2009 · 114,29 % |
| Ausgewogen | seit 2008 · 146,52 % | seit 2009 · 145,85 % |
| Offensiv (Thema) | seit 2008 · 185,77 % | seit 2009 · 184,92 % |
| Dynamic | seit 2018 · 76,82 % | unverändert (2018 aufgelegt) |

Linien-Chart: startet jetzt bei 100 % am 31.12.2008, erste Bewegung am
01.01.2009.

⚠️ **Die kumulierten Werte ändern sich leicht** (der 31.12.2008 fällt als
Renditetag heraus). Falls diese Zahlen außerhalb des Tools zitiert werden,
dort angleichen.

**Testumgebung:** `pip` funktioniert entgegen der bisherigen Annahme
(Abschnitt 13). In einem venv laufen streamlit 1.61, python-pptx 1.0.2,
pandas 3.0.5 und numpy 2.5.1 — also genau die Kombination, vor der
Transferwissen #20/#21 warnt. Der komplette Export läuft damit sauber durch;
`tests/test_export_smoke.py` erzeugt für jede Familie eine echte Broschüre.

### 07.08.2026 (vormittags) – Code-Review: Benchmark-Bugfix, Deploy-Konfiguration, Aufräumen

**Fachlicher Fehler behoben (ging in die Kundenbroschüre):**
- Eine Benchmark-Spalte aus lauter Nullen galt als echte Benchmark, weil
  `notna().any()` bei `0.0` True liefert. „Muster SCHWEIZ Aktien" und
  „Muster SCHWEIZ Substanz" (beide laut Mapping ohne Benchmark) bekamen
  dadurch BM-Performance 0,00 %, Vola 0,00 %, Max Drawdown 0,00 % und eine
  **Sharpe Ratio von −67,48** ausgewiesen. Neu: `analytics.has_benchmark()`,
  angewandt in `compute_performance_data`, im Balken- und Performance-Chart
  sowie im PDF-Export. Transferwissen #41.
- Erster Regressionstest: `tests/test_benchmark_erkennung.py`, 19/19 grün.
  Die 17 Strategien mit Benchmark liefern nachweislich unveränderte Werte.

**Deploy-Konfiguration repariert:**
- Ordner `streamlit/` → `.streamlit/`. Ohne Punkt hat Streamlit die Datei nie
  gelesen; `toolbarMode = "minimal"` war seit jeher wirkungslos.
- `lxml>=4.9` in die requirements aufgenommen — wird direkt importiert, kam
  bis dahin nur zufällig über python-pptx mit. `python-pptx>=0.6.21` → `>=1.0`.
- `enableStaticServing` entfernt (seit dem Blob-Download unnötig, Backlog 6).

**Doppelte Wahrheiten aufgelöst:**
- `streamlit_app.py` enthielt eigene, zeilengleiche Kopien von `load_all_csvs`,
  `read_one_csv`, `parse_dates_col`, `extract_benchmark_name` und
  `build_portfolio_timeseries`. Zwei `@st.cache_data`-Caches für dieselbe
  Arbeit → CSVs doppelt geparst und doppelt im Speicher; bei Drift hätten
  Tool und Broschüre verschiedene Zahlen gezeigt. Jetzt nur noch `shared.py`.
- Acht nie aufgerufene Kopien der analytics-Mathematik aus `pptx_export.py`.

**Robustheit:**
- `shared.load_all_csvs` findet jetzt `.CSV` UND `.csv`. Auf der Cloud (Linux,
  case-sensitiv) wäre eine klein geschriebene Datei stillschweigend
  verschwunden, während `detect_newest_date_tag` ihren Tag gefunden hätte.
- `check_login` nutzt `hmac.compare_digest` statt `==`.
- `.gitignore` angelegt — schließt `.streamlit/secrets.toml` aus.

**Toter Code entfernt (~1.900 Zeilen):** `performance.py`,
`macrobond_upload.py`, `ll`, fünf leere Platzhalter-`.md`, `generate_pf_pdf`,
`_mpl_ring_chart` (damit reportlab und matplotlib aus `portfolioanalyse.py`),
`medien_download_url`, `if True:`.

**Doku korrigiert:** `erstelle_broschueren.py` und `modules/dataload.py` waren
nie im Repo, wurden aber in vier Abschnitten als vorhanden geführt.

### 21.–28.07.2026 – Familien-Ausbau, Export-Namen, Folienlisten-Config & kräftigere Ring-Optik
- **comdirect-Familie** (Klassische Portfolioverwaltung, 27 Folien, 3 Strategien) — reine Config-Ergänzung. Transferwissen #36
- **Konfigurierbare Export-Dateinamen** je Familie/Strategie (`EXPORT_NAME_*`), Namen kommen 1:1 durch den clientseitigen Download. #37
- **Download-Button** direkt unter den „Momentaufnahme"-Hinweis verschoben + kontextbezogener Familien-Hinweis (`_render_familien_hinweis`). #38
- **`_folien_config`** — statische/dynamische Folien als geordnete Liste (Position = Listenindex); comdirect/CVV/ESG/ETF umgestellt, jeweils byte-identisch zur alten Hand-Config belegt. #39
- **`FAMILIE_RING_FORMAT`** — familienspezifische Ring-Optik. CVV/ESG/ETF/Thema/comdirect „kräftiger": dicker Ring (Loch 68), gerade Leader mittig im Band, kleine dezente Punkte (0,05"), fette schwarze Prozente, luftigere Labels; Nicht-gelistete (Standard) byte-identisch. Insight: Leader-Start IM Band ist gewollt (kein Bug); `leader_aussen_faktor` verworfen. #40
- **Geänderte Dateien:** `portfolioanalyse.py`, `modules/pptx_slides.py`, `modules/chart_dynamik.py`

### 21.07.2026 – ETF-Familie eingebaut (additiv, byte-identisch belegt)
- **ETF-Familie** (2 Strategien ETF_ausgewogen/ETF_Wachstum, Infoboard `Vorlage_ETF.pptx`, 35 Folien) in `portfolioanalyse.py` registriert — reine Config-Ergänzung (0 Zeilen entfernt), spiegelt ESG ohne Vergleichs-Chart. Transferwissen #35
- **7-Spalten-`T_Kennzahlen`**: ETF-Tabelle hat kein Kupon/Fälligkeit → optionaler `spalten_map`-Parameter an `fill_anlagevorschlag_slides`/`fill_table_with_positions`/`maybe_narrow_bond_columns`/`remove_empty_table_rows`, Default = bisherige 11-Spalten-Konstanten. **Byte-identisch für ESG/CVV/Standard belegt** (Alt-Modul vs. Neu-Modul mit Default). ETF übergibt sein Map via `rollen_optionen`.
- **Vorlagen-Komprimierung**: 55 MB → 12 MB (Bilder auf max 1920px, opake PNGs → JPEG q82, transparente PNGs/Vektoren unberührt).
- **Playbook** für weitere Familien als Transferwissen #35 dokumentiert.
- **Geänderte Dateien:** `portfolioanalyse.py`, `modules/pptx_slides.py`

### 20.07.2026 – Ring-Optik (Leader/Punkte) + Themen-Einzeltitel-Datenlogik + Legende
- **Führungslinien-Endstand:** Die Cluster-Engine („V2", luftig/grau/Punkte-am-Segment) wurde als „schlimmer" **verworfen**; gültig bleibt die **(7)-basierte** `ring_labels_aussen_dynamisch`. Leader jetzt **schwarz** (war grau), als eigene Connector-Shapes. `chart_dynamik.py` neu strukturiert (WEGWEISER + CONFIG + FALLSTRICKE-Kopf) für gezielte Änderungen. Transferwissen #29
- **Stub-Fix:** `ring_labels_stub_fix` repariert die richtungslosen Leader oberer Labels (Zahl fast senkrecht überm Segment) durch minimales Nach-außen-Schieben bis zum sauberen Knick; gedeckelt auf 0,50". 96 Leader repariert, 0 neue Überlappungen. Transferwissen #30
- **Punkte am Label-Ende:** kleiner schwarzer Kreis am äußeren Leader-Ende (vor der Zahl, nicht am Ring). Regel per CONFIG: `PUNKT_RINGTYPEN=("ANLAGEKLASSEN","BRANCHEN")` + nur Thema-Familie → Assetklassen- + Branchen-Ring der Thema-Broschüren, Regionen + ESG/CVV ohne. Transferwissen #31
- **Familien-/Ringtyp-Erkennung:** `_familie_aus_prs` (aus `Mapping_Namen.xlsx`, längster Titel-Treffer, cVV ohne Prefix) + `_ring_typ`. Über 18 Broschüren verifiziert. Transferwissen #32
- **BUG Themen-Einzeltitel-Ring:** `fill_einzeltitel_themen_slide` füllte nur die Tabelle, NIE den Assetklassen-Ring → Ring behielt Vorlagen-Platzhalter (EDELMETALLE fehlte, Werte ≠ Tabelle). Fix: `GROUP_ORDER`-Aggregations-Feed ergänzt (wie Standard). Ring nun deckungsgleich mit Tabelle (AKTIEN 89,32/EDELMETALLE 5,93/LIQUIDITÄT 4,75). Transferwissen #33
- **BUG Legende:** die kleine Vorlagen-Legendenbox (0,99×0,49") schnitt Einträge ab / brach „EDELMETALLE" um. `ensure_ring_legend_fits` vergrößert Höhe (alle Einträge) + Breite (längstes Label ohne Umbruch), nur bei Bedarf, nur im Thema-Pfad. Transferwissen #34
- **Verifikationsmethode dieser Session:** durchgängig **numerisch am Chart-XML** (LibreOffice-Render zeigt Doppel-Leader und ist kein Beweis); echte PowerPoint-Screenshots von Philip als finale Abnahme.
- **Geänderte Dateien:** `modules/chart_dynamik.py`, `modules/pptx_slides.py`

### 07.07.2026 – Gateway-Download gelöst (clientseitiger Blob-Download)
- **Problem:** PPTX-Download hinter dem Atruvia/Skyhigh-Gateway lieferte
  `progress.htm` statt der Datei; Kern: JEDER Server-Abruf läuft durch den
  Scanner
- **Verworfene Sackgassen (alle Server-Abrufe):** klassischer
  `st.download_button`; neuer Tab auf interne Media-URL `/media/…` (bootet auf
  Community Cloud die App neu — im Deploy-Log bewiesen); neuer Tab auf Static
  Serving `/app/static/…` (Pfad/Content-Type korrekt, Scan hängt trotzdem)
- **Lösung:** `modules/download_helfer.py` → `download_bereich()` bettet die
  Bytes als Base64 ein und lädt clientseitig per `Blob` + `<a download>` über
  `st.components.v1.html` (iframe erlaubt Downloads) → KEIN Netzwerk-Request →
  Gateway sieht nichts → Download startet sofort, kein neuer Tab. Im Deploy
  bestätigt
- **Verifikation:** py_compile; Base64-Roundtrip bit-identisch inkl. aller
  Byte-Werte; iframe-`allow-downloads` im Frontend-Code (IFrameUtil.ts) belegt;
  `guess_content_type`/`enableStaticServing`/`MEDIA_ENDPOINT` gegen 1.59.0 geprüft
- **Aufräum-Reste (Backlog):** `enableStaticServing` in config.toml + Legacy-
  Stub `medien_download_url` ungenutzt
- Transferwissen #25

### 07.07.2026 – Navigations-Umbau: st.tabs → segmented_control
- **Bug:** Strategie-Auswahl im Portfolioanalyse-Tab warf die Ansicht auf
  Tab 1 zurück (bekanntes st.tabs-Verhalten, GitHub #6257/#11160/#4996/#12554;
  `key`+`on_change`+`default` halfen nicht — `default` ist bei gesetztem key
  nach dem ersten Run wirkungslos)
- **Fix:** `st.segmented_control(key="nav_view", required=True)` oben auf der
  Seite; Tab-Bodies → `if/else`. Keep-Alive-Block für Widget-States
  (Trigger-Widgets ausgenommen). Zentrale Datenbereitstellung
  (`perf_timeseries`/`perf_d2c`/`perf_d2b`) VOR die Navigation gezogen;
  `st.stop()` der Performance-Ansicht reißt die Portfolioanalyse nicht mehr mit
- **Verifikation:** AppTest unter exakt Streamlit 1.59.0 (Selectbox-Rerun →
  Navigation bleibt; View-Wechsel → Widget-Werte erhalten); py_compile;
  AST-Check (alle 35 Funktionen, Bereitstellung vor Navigation); Deploy
  bestätigt. `portfolioanalyse.py` unverändert
- Transferwissen #18, #19, #24

### 06.07.2026 – Streamlit-Cloud-Versionsfalle
- Reboot zog Streamlit 1.59.0 + pandas 3.0 + numpy 2.5 (wegen `>=`);
  Downgrade-Pinnen hing unter Python 3.14 → zurück auf `>=`, App läuft
- LEARNING: bei "lief gestern noch" ZUERST Deploy-Log (Paketversionen) prüfen
- Transferwissen #20

### 04.–06.07.2026 – Themen-Broschüren + lokaler Batch
- **Themen-Broschüren** (Pro/Pro Dividende/Offensiv): familiengesteuerte
  Vorlagenwahl über Mapping-Spalte "Powerpoint Familie" (Variante A);
  `VORLAGEN_FAMILIEN`, `_familie_fuer_strategie`, `_vorlage_fuer_familie`
  (robuste, case-/whitespace-tolerante Erkennung, sicherer Fallback auf
  Standard); Blöcke `einzeltitel_themen` (7-Spalten-Tabelle mit Währung) und
  `rollierend` (YTD/1/3/5/10 J., bit-identisch zur Tool-Tabelle);
  `template_config["block_reihenfolge"]`
- `Vorlage_Thema.pptx` 24 MB → 3,95 MB (24 RGBA-PNGs, opake → JPG Q82);
  F10-Summenzeile bereinigt; F11-Ringe holeSize 79→55
- GitHub-Web-Rename zerstörte eine große PPTX (2-Byte-Datei) →
  Transferwissen #23; LFS-Zeiger-Diagnose in den Export eingebaut
- **PDF-Export im Portfolioanalyse-Bereich entfernt** (nur noch PowerPoint)
- **Lokaler Batch** `erstelle_broschueren.py` + `modules/dataload.py`:
  streamlit-frei (mit blockiertem Streamlit-Import bewiesen); pausiert
  wegen IT-Paketinstallation

### 03.07.2026 – Konsistenz-Tag
- **YTD-Fix** rollierende Tabelle: Start `asof(31.12. Vorjahr)` statt
  `asof(01.01.)` → Tabelle == Balken-Chart == PP bit-identisch
  (Transferwissen #22)
- **Konsistenz-Doktrin** Tool ↔ PP festgelegt (PP kanonisch: volle Historie
  + Standardsatz) + Info-Caption benennt live jede aktive Abweichung
- **Duration/Rendite aus den Titeln** (`duration_info_aus_bestand` →
  `get_bond_summary`, anleihe-gewichtet Variante B; verifiziert 3,96 /
  3,28 %); Duration-Ordner aus dem Repo gelöscht
- **Arrow-String-Fix** in `get_bond_summary` (Python 3.14 / pandas-Arrow;
  Transferwissen #21)
- **replace_data Bug 4** entdeckt + gefixt: Achsen-numFmt-Reset
  (valAx/catAx/dateAx; numFmt direkt nach c:axPos) — Transferwissen #12
- `perf_d2b` (Benchmark-Texte) für die ***-Fußnote der Wertentwicklungs-Folie
- **F9-Anpassungen:** YTD-Balken (Schalter `F9_BAR_INCLUDE_CURRENT_YEAR`),
  datenbasierte Achsen-Untergrenze, statische Quelle, Tool-Fußnote
- Korrektheits-Verifikation der Exportzahlen gegen unabhängige Nachrechnung

### Ende Juni/02.07.2026 – Modul-Architektur + F8
- **PPTX-Code in 4 Module aufgeteilt**: pptx_helpers / pptx_charts /
  pptx_slides / pptx_export (Schichten-Architektur, pptx_slides kennt kein
  Streamlit)
- **Berechnungs-Logik nach `modules/analytics.py`** (Single Source of Truth
  für App UND Export; streamlit_app.py behält dünne Wrapper)
- **Wertentwicklungs-Folie (F8)** aus dem alten VBA-Tool per ZIP-Slide-Copy
  integriert → Standard-Vorlage 26 Slides; `fill_wertentwicklung_slide`
  mit Platzhalter-Modus
- **Donut-Rückbau**: matplotlib-PNG-Ansatz (`png_charts.py`) verworfen,
  native PP-Donuts via `replace_chart_data` (Template-Styling bleibt)
- **Kapazitäts-Fix F7-Tabelle**: `ensure_table_capacity` +
  `fit_shape_to_table`; Geometrie aus echten Exporten kalibriert; nie mehr
  stilles Abschneiden von Positionen
- LibreOffice-≠-PowerPoint-Erkenntnisse + `dateAx baseTimeUnit`
  (Transferwissen #16-Update)

### Juni 2026 (Phase 2) – Performance-PPTX-Export + Vorlage v7
- `compute_performance_data`, `_fill_performance_slide`,
  `_replace_chart_data_safe` (damals 3 Bugs), Streamlit-Integration mit
  Fallback-Loader, MwSt-Checkbox, Vorlage v7 sauber neu gebaut
  (22,7 → 4,14 MB, 25 Slides). Details siehe Phase-2-Stand dieser Doku.

### Früher (Kurzform)
- Juni 2026: Corporate Colors (FFPB_PALETTE), Disclaimer-Wording,
  Tab "Portfolio zusammenstellen" deaktiviert (Compliance)
- Mai 2026: Sharpe (Excess-Variante) + risikofreier Zins, validiert an
  17-Jahres-Echtzeitreihe inkl. Negativzinsphase
- April 2026: Initiale Doku-Version

---

## 17. Für den nächsten Chat / Kollegen

**Hochladen:** Diese MD + die aktiven Code-Dateien (`streamlit_app.py`,
`modules/shared.py`, `modules/analytics.py`, `modules/portfolioanalyse.py`,
`modules/pptx_helpers.py`, `modules/pptx_charts.py`, `modules/pptx_slides.py`,
`modules/pptx_export.py`, `modules/chart_dynamik.py`).
Seit 07.08.2026 arbeiten wir stattdessen **direkt im geklonten Repo** — dann
entfällt das Hochladen ganz und die Dateistände können nicht auseinanderlaufen.
**Sagen:** "Lies die PROJEKT_DOKUMENTATION.md zuerst komplett. Dann [Aufgabe]."
**Bei Problemen:** Screenshot + erwartetes Verhalten + welche Dateien aktuell
deployed sind.

**Arbeitsstil (etabliert, bitte beibehalten):** Diagnose vor Lösung (am
Artefakt/XML/Log beweisen, NICHT raten) · gegen echte Dateien und den echten
Deploy testen · komplette Dateien liefern · deutsche Kommentare · Annahmen
markieren · ein konkreter Prüfstein je Lieferung.

**Bewährte Beweismittel:**
- TEST-Titel-Trick (st.title kurz ändern) → beweist, dass der Deploy ankommt
- Farbige Marker-Boxen (st.success/st.error) → beweist, welcher Code-Block läuft
- Deploy-Log (Manage app → Konsole) → zeigt installierte Paketversionen
- AppTest (Transferwissen #24) → beweist Rerun-/State-Verhalten vor dem Deploy
- Generierte-PNG-Dateigröße → verlässliches Signal, ob eine Datei sich wirklich geändert hat

**Wichtig bei CSV-Änderungen:** Nach Deploy IMMER Cache leeren (Transferwissen #7).

**Wichtig bei PPTX-Änderungen:**
- Nach jedem Code-Update lokal mit echten Daten testen, in ECHTEM PowerPoint öffnen (LO reicht nicht — #16)
- `chart.replace_data()` NIE direkt — immer `replace_chart_data_safe()` (#12, jetzt 4 Bugs); Ringe über `replace_chart_data` (XML-in-place)
- Bei Datei-Größe > 9 MB: PNG-Optimierung prüfen (#13)
- Bei "Reparieren"-Dialog: Multi-Layer-Validierung (#16)
- Große .pptx im Repo NIE per Web-UI umbenennen; Dateigröße nach Upload prüfen (#23)

**Wichtig bei Ring-Optik (Leader/Labels/Punkte) — chart_dynamik.py:**
- Endstand ist die **(7)-basierte** `ring_labels_aussen_dynamisch`; die Cluster-Engine ist VERWORFEN — nicht wiederbeleben (#29)
- Anordnung ändern → `ring_labels_aussen_dynamisch`; Leader/Punkt/Farbe → `ring_leader_zeichnen` + CONFIG-Block oben in der Datei; Knick-Richtung → `ring_labels_stub_fix` (#30)
- Punkte-Regel steht im CONFIG (`PUNKT_RINGTYPEN`, `PUNKT_NUR_THEMA`) — eine Stelle (#31)
- **Leader-Optik NUR an echten PowerPoint-Screenshots prüfen** (LibreOffice zeichnet Doppel-Leader); Geometrie numerisch aus dem XML verifizieren (#29)

**Wichtig bei Ring-DATEN (nicht Optik!) — pptx_slides.py:**
- Der Assetklassen-Ring ist ein EIGENER Datenpfad neben der Tabelle; Datenfehler sitzen in `pptx_slides.py`, nie in chart_dynamik (#33)
- Standard-Ring: `fill_anlagevorschlag_slides`; Themen-Einzeltitel-Ring: `fill_einzeltitel_themen_slide`; Regionen/Branchen: `fill_zusammenstellung_slide` via `build_ring_series`
- Legende zu klein/abgeschnitten → `ensure_ring_legend_fits` (#34)

**Wichtig bei Streamlit-Änderungen:**
- Navigation/State: #18 + #19 lesen, BEVOR an nav_view/Keep-Alive geschraubt wird
- Reihenfolge in streamlit_app.py (Abschnitt 7) nicht durcheinanderbringen —
  insbesondere Datenbereitstellung VOR der Navigation lassen
- Bei "lief gestern noch": Deploy-Log zuerst (#20)
- Chat-Praktisches: `.py`-Uploads kommen in sehr langen Chats teils leer an →
  als `.txt` hochladen oder Code einfügen; bei wiederholt leeren Uploads neue Session

*Stand: 20.07.2026 (Phase 3)*
