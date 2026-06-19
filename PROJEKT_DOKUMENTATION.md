# FFPB Streamlit Tool – Projektdokumentation & Transferwissen
## Stand: Juni 2026 (Phase 2: Performance-PPTX-Export implementiert)

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

### 12. python-pptx `chart.replace_data()` ist VERSEUCHT — Bug-Trio bei Charts mit embedded Excel

**Situation:** Du willst Chart-Daten in einer PPTX programmatisch ändern (Balken-Werte, Linien-Werte, Kategorien). Die Standard-Methode in python-pptx ist `chart.replace_data(CategoryChartData)`.

**Falle (drei zusammenhängende Bugs):** Wenn der Chart ein **embedded Excel-Workbook** hat (das ist bei aus PowerPoint exportierten Vorlagen-Charts der Standard), passiert beim `replace_data()`:

1. **Embedded Excel wird NICHT aktualisiert.** Die XML-Daten werden geändert, das eingebettete `Microsoft_Excel_Worksheet1.xlsx` behält aber die alten Vorlagen-Werte. PowerPoint erkennt die Diskrepanz → "**Datei muss repariert werden**"-Dialog → die Folie wird beschädigt oder verschwindet.

2. **`style*.xml` wird mit Binärmüll überschrieben.** Konkret: die Chart-Style-Datei (z.B. `ppt/charts/style7.xml`) wird VOR `replace_data()` ein gültiges `<cs:chartStyle ...>` XML — und NACH `replace_data()` ein **ZIP-Header** (`PK\x03\x04...`). python-pptx schreibt aus Versehen ZIP-Inhalt in den falschen Pfad. Auch das löst den Reparieren-Dialog aus.

3. **Format-Codes der Daten-Labels werden auf `"General"` zurückgesetzt.** Das Daten-Label das vorher `0.05` als `5,00%` angezeigt hat, zeigt jetzt `0.05` als Text — die Prozent-Formatierung ist weg. Visueller Schaden, aber nicht datei-zerstörend.

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
    Workaround für 3 python-pptx-Bugs bei chart.replace_data() mit embedded Excel.
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
    
    # ─── 5. Format-Code wiederherstellen (Bug 3 Fix) ───
    if data_label_format:
        _restore_data_label_format(chart_shape, data_label_format)


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

**Verwendet in diesem Projekt:** `modules/pptx_export.py` → `_replace_chart_data_safe()`. Beide Performance-Charts (Säulen + Linien) gehen durch diese Funktion.

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

**Validiert in diesem Projekt:** Original-Vorlage 22.7 MB → optimierte Vorlage 4.14 MB. **−82% Größe** ohne sichtbaren Qualitätsverlust. Streamlit-Cloud progress.html Problem gelöst.

**Statistik der 19 konvertierten Bilder:** Alle hatten min-Alpha = 255 (fake), zusammen 17 MB → 1.8 MB als JPEG. Ohne erkennbaren visuellen Unterschied bei q=85.

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

**Validiert in diesem Projekt:** v7-Vorlage komplett aus zwei Quellen (Original + Master) gebaut, 25 Slides, 0 XML-Fehler. Siehe Abschnitt 11 "PowerPoint-Vorlage Recipe" für das vollständige `build_v7.py` Skript.

**Generelle Lesson:** Office-Dokumente sind ZIP-Archive mit strenger Hierarchie. Was ein einzelner Slide-Copy in PowerPoint mit zwei Mausklicks tut, sind im Code ~8 Phasen synchroner Updates. Das ist OK, weil reproduzierbar und versionierbar.

---

### 15. Streamlit Cross-Tab Daten-Sharing — robuste Fallback-Strategie

**Situation:** Daten aus Tab A werden in Tab B benötigt (z.B. Performance-Zeitreihe aus Tab A wird in Tab B für PPTX-Export verwendet).

**Falle:** Naive Lösung `st.session_state["data"] = data` in Tab A, dann `data = st.session_state["data"]` in Tab B — funktioniert NICHT zuverlässig:
- Streamlit-Tabs werden zwar alle gerendert, aber wenn Tab A einen `st.stop()` aufruft (z.B. fehlende CSV-Datei), wird `session_state` nie gesetzt
- User könnte direkt auf Tab B klicken bevor Tab A "warm" ist
- Bei Reload geht session_state verloren

**Symptom in diesem Projekt:** User klickte Portfolioanalyse → PowerPoint, ohne den Performance-Tab vorher geöffnet zu haben → Slide 8 zeigte Vorlagen-Defaults (0,0%) statt echte Daten.

**Lösung — Fallback-Pattern:**

```python
# Tab B: erst session_state versuchen, dann selbst laden
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

**Wichtige Voraussetzung:** Die Lade-Funktionen müssen aus einem GEMEINSAMEN Modul kommen, nicht aus dem Top-Level eines Tab-Files. In diesem Projekt: `build_portfolio_timeseries`, `load_all_csvs` etc. wurden in `modules/shared.py` verschoben, damit sowohl `streamlit_app.py` (Tab A) als auch `portfolioanalyse.py` (Tab B) sie nutzen können.

**Generelle Lesson:** Cross-Tab Coupling ist Streamlit-Antipattern. Wenn du die Daten in Tab B brauchst, lade sie in Tab B. session_state ist eine Optimierung (Cache), keine Datenquelle. Plan also: **session_state ist nie garantiert da, immer Fallback einbauen, immer Diagnose bei Datenlücken zeigen.**

---

### 16. PPTX-Validierung Multi-Layer-Toolchain

**Situation:** Du hast eine PPTX generiert/modifiziert und musst herausfinden warum PowerPoint sie nicht öffnen kann (oder reparieren möchte).

**Falle:** PowerPoint zeigt nur "Datei muss repariert werden" — keine Diagnose welcher Part kaputt ist. LibreOffice öffnet die Datei vielleicht fehlerfrei (LO ist toleranter), also `soffice --convert-to pdf` ist kein zuverlässiger Validitäts-Test.

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

## 1. Projektübersicht

Streamlit-App für Fürst Fugger Privatbank mit 2 aktiven Tabs.

| Tab | Datei | Zeilen | Zweck |
|---|---|---|---|
| 📈 Performance | `streamlit_app.py` | ~990 | Historische Performance, Kennzahlen (inkl. Sharpe), Charts, PDF+Glossar |
| 📊 Portfolioanalyse | `modules/portfolioanalyse.py` | ~870 | Strukturanalyse: Ringe, Tabellen, Anleihen-Detail, PDF, **PPTX-Export inkl. Performance-Folie** |
| (gemeinsam) | `modules/shared.py` | ~290 | Konstanten, Login, Formatierung, Font-Setup, Corporate-Palette, **CSV-Loading-Helpers** |
| (PowerPoint-Export) | `modules/pptx_export.py` | ~1920 | PPTX-Export aus Portfolioanalyse-Tab inkl. **Performance-Folie mit Daten-Befüllung** |

**Gesamt aktiv: ~4.070 Zeilen | Deployment: Streamlit Cloud via GitHub | Python 3.10+**

**Nicht aktiv im Repo:** `modules/portfolio_builder.py` (~695 Zeilen) – seit Juni 2026 nicht mehr importiert (Compliance-Entscheidung). Datei bleibt für mögliche spätere Reaktivierung im Repo.

**Vorlage-Datei:** `Vorlage/Vorlage_FFPB.pptx` – PowerPoint-Master mit Corporate-Design, benannten Shapes und 25 Slides (inkl. Performance-Folie an Position 10). Wird von `pptx_export.py` als Template genutzt. Größe: 4.14 MB (optimiert von ursprünglich 22.7 MB — siehe Transferwissen #13).

---

## 2. Dateistruktur

```
Repository Root/
├── streamlit_app.py
├── modules/
│   ├── __init__.py
│   ├── shared.py
│   ├── portfolioanalyse.py
│   ├── pptx_export.py               ← PowerPoint-Export (Portfolioanalyse + Performance-Folie aktiv)
│   └── portfolio_builder.py         ← deaktiviert seit Juni 2026
├── Vorlage/
│   └── Vorlage_FFPB.pptx            ← Corporate-Master, 25 Slides, benannte Shapes, JPEG-optimiert
├── fonts/
│   ├── segoeui.ttf
│   └── segoeuib.ttf
├── .streamlit/
│   └── config.toml                  ← toolbarMode = "minimal"
├── Mapping_Honorarsatz.xlsx
├── Mapping_Namen.xlsx
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
python-pptx>=1.0
lxml>=4.9                            ← KRITISCH für Chart-XML-Manipulation
```

---

## 3. Abhängigkeiten

```
shared.py ──→ streamlit_app.py (Tab 1 inline + importiert Tab 2)
          ──→ portfolioanalyse.py ──→ pptx_export.py
          ──→ pptx_export.py
```

Seit Juni 2026 (Phase 2):
- `shared.py` enthält die CSV-Loading-Helpers (`build_portfolio_timeseries`, `load_all_csvs`, `read_one_csv`, `parse_dates_col`, `extract_benchmark_name`, `to_decimal_interval`). Damit kann sowohl der Performance-Tab als auch der Portfolioanalyse-Tab die Performance-Zeitreihen laden — egal in welcher Reihenfolge der User die Tabs öffnet.
- `pptx_export.py` enthält die `compute_performance_data()` Funktion, die aus einer Zeitreihe alle Kennzahlen + Chart-Daten für die Performance-Folie berechnet.

`portfolio_builder.py` liegt im Repo, wird aber nicht importiert.

---

## 4. Corporate Design

**Seit Juni 2026 nutzen beide Tabs durchgängig die offiziellen Fürst Fugger Privatbank Corporate Colors.**
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

### 6.2 Mapping-Dateien

**`Mapping_Honorarsatz.xlsx`:** Inhaber + Honorarsatz Standard (Dezimal)  
**`Mapping_Namen.xlsx`:** A=Anzeigename, B=CSV-Key, C=Duration, D=Benchmark-Zusammensetzung

---

## 7. Tab 1: Performance

### Layout & Aufbau
- Hinweis + Quelle oben, Disclaimer unten
- Sidebar: Portfolio, Vergleich, Checkboxen (Vor Kosten, Benchmark, **Risikofreier Zins**, Drawdown, Tabelle, Balken), Kosten (dynamischer Key), MwSt (×1.19)
- Zeitraum: Datumspicker + Reset-Buttons (Counter-Keys, siehe Transferwissen #4)

### Kennzahlen (zwei Reihen)
**Reihe 1:** Auflagedatum | ⌀ Rendite p.a. (CAGR) | Volatilität p.a.  
**Reihe 2:** Calmar Ratio | **Sharpe Ratio** | Endwert  
**Caption:** `Ø Risikofreier Zins p.a. (Zeitraum): X,XX%`

**Sharpe-Berechnung:** Wissenschaftlich saubere Variante nach Sharpe (1994) auf Basis täglicher Excess Returns.

### Cross-Tab Daten-Sharing (NEU Juni 2026)
Tab 1 setzt nach erfolgreichem Daten-Loading:
```python
st.session_state["perf_timeseries"] = data
st.session_state["perf_d2c"] = d2c
```

Tab 2 (Portfolioanalyse) liest diese im PPTX-Export — mit Fallback-Loader falls leer (siehe Transferwissen #15).

---

## 8. Tab 2: Portfolioanalyse

- `_render_single_portfolio()` mit `suffix="pf1"/"pf2"` (siehe Transferwissen #3)
- Ring-Diagramme: Absteigend sortiert, Labels außen (13px), <3% ausgeblendet, Legende horizontal unten
- YTD: Spalten ausgeschrieben (Wertpapier-Performance/Performancebeitrag)
- PDF (reportlab): Ring-Charts kompakter (100×85mm), intelligente Spaltenbreiten
- **PowerPoint-Export aktiv** mit Performance-Folie (siehe Abschnitt 10)

### Sidebar-Optionen (Portfolioanalyse-Sektion)
- ☐ YTD Performance anzeigen
- ☐ **Bruttohonorar (inkl. 19% MwSt.)** — wirkt auf Performance-Folie-Kennzahlen im PPTX
- ☐ Erweiterte Einstellungen (Date-Tag-Override)

---

## 9. Disclaimers

| Tab | Schlüsselsatz |
|---|---|
| Performance | "Dieses Performancetool dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. Alle Berechnungen sind unverbindlich und erfolgen ohne Gewähr." |
| Portfolioanalyse | "Diese Portfolioanalyse dient ausschließlich der unverbindlichen Veranschaulichung der Vermögensverwaltungsstrategien im Kundengespräch. Alle Angaben sind ohne Gewähr." |

Quelle: Infront & eigene Berechnungen | Ansprechpartner: PBAM

---

## 10. PowerPoint-Export-System

Das PowerPoint-Export-System ist ein zentraler Baustein für die Kunden-Kommunikation.

### 10.1 Architektur-Prinzip "B2"

Jeder Tab füllt **nur seine eigenen Folien**:

| Tab | Befüllt Slides | Entfernt Slides |
|---|---|---|
| 📊 Portfolioanalyse | 7-9 (Anlagevorschlag, **Performance**, Zusammenstellung) | 11 (Währungen) |
| 📈 Performance (geplant) | (eigener Export) | analog |

### 10.2 Vorlage `Vorlage/Vorlage_FFPB.pptx`

25 Slides nach Phase-2-Integration:

| # | Slide | Verwendung |
|---|---|---|
| 1-6 | Cover, Intro | statisch |
| 7 | **Anlagevorschlag** (Tabelle + Allokations-Ring) | dynamisch befüllt |
| 8 | (alte Anlagevorschlag-Teil-2) | wird beim Export ENTFERNT |
| 9 | **Aktuelle Portfoliozusammenstellung** | dynamisch befüllt |
| 10 | **Performance/Wertentwicklung** (NEU Juni 2026) | dynamisch befüllt |
| 11 | Währungen-Ring | wird beim Export ENTFERNT |
| 12+ | Honorar, Bank, Ansprechpartner, etc. | statisch |

**Beim Export passiert** (in `pptx_export.py`):
1. `_remove_slide(prs, 7)` → alte Anlagevorschlag-Teil-2 raus (Index 7 = Slide 8)
2. `_remove_slide(prs, 9)` → Währungen raus (war Index 10, nach Op1 = 9)
3. `_move_slide(prs, 8, 7)` → Performance nach Position 8 (vor Portfolio)

**Resultierende Reihenfolge:**
- Slide 7 = Anlagevorschlag
- Slide 8 = **Performance** (war Slide 10 in der Vorlage)
- Slide 9 = Portfoliozusammenstellung

### 10.3 Shape-Namen-Konvention

Die Vorlage nutzt **benannte Shapes**:

#### Anlagevorschlag-Slide (Slide 7 in der Vorlage)
| Shape-Name | Typ | Verwendung |
|---|---|---|
| `Titel` | Placeholder | "Anlagevorschlag – {Strategie}" |
| `C_Kennzahlen` | Chart | Allokations-Ring |
| `T_Kennzahlen` | Tabelle | Positionen mit "Marktrisikowert" Header |
| `Fußnote` | Placeholder | Disclaimer |
| `Quelle` | Textbox | "Quelle: ... Stand DD.MM.YYYY" |

#### Performance-Slide (Slide 10 in der Vorlage)
| Shape-Name | Typ | Verwendung |
|---|---|---|
| `Titel` | Placeholder | "{Strategie} \| Wertentwicklung (mit Benchmark)" |
| `Tabelle` | Tabelle 7×5 | KENNZAHLEN / REFERENZ / BENCHMARK |
| `Diagramm links` | Chart (Säulen) | "PERFORMANCE P.A. (NACH KOSTEN)" |
| `Diagramm rechts` | Chart (Linien) | "WERTENTWICKLUNG" |
| `Fußnote` | Placeholder | Disclaimer |
| `Quelle` | Textbox | Dynamisch via Drawing-XML-Manipulation |

**Tabellen-Struktur** (7×5):
- Row 0: Header (KENNZAHLEN | _ | REFERENZ | _ | BENCHMARK)
- Row 1: Spacer
- Row 2: Performance p.a.
- Row 3: Volatilität
- Row 4: Sharpe Ratio
- Row 5: Max Drawdown
- Row 6: Spacer

### 10.4 Strategienamen-Normalisierung

`clean_strategy_name()` entfernt: `cVV`, `Muster`, `Stiftung`.

### 10.5 Slide-Duplikation für Vergleichsportfolio

`_duplicate_slide(prs, source_idx)` mit deepcopy aller Shapes, eigene Chart-Parts, geteilte Image-Referenzen. Nach Duplikation immer `_save_and_reload(prs)`.

### 10.6 Chart-Befüllung — XML-basiert, `_replace_chart_data_safe()`

Charts in Vorlagen haben oft embedded Excel-Workbooks. Python-pptx's `chart.replace_data()` hat dabei **drei bekannte Bugs** (siehe Transferwissen #12):

1. embedded Excel wird nicht aktualisiert
2. `style*.xml` wird mit ZIP-Header überschrieben  
3. Format-Codes der Daten-Labels gehen verloren

**Lösung:** `_replace_chart_data_safe()` Wrapper in `pptx_export.py`:

```python
# Pseudocode des Workflows:
def _replace_chart_data_safe(chart_shape, categories, series_data, data_label_format):
    # 1. Backup style/colors parts (Bytes)
    # 2. chart.replace_data(CategoryChartData(...))
    # 3. Restore style/colors parts from backup
    # 4. Remove <c:externalData> from chart XML
    # 5. Restore numFmt formatCode in <c:dLbls>
```

Vollständige Implementierung siehe `pptx_export.py` und Transferwissen #12.

### 10.7 Performance-Daten-Befüllung (Phase 2, Juni 2026)

`compute_performance_data(timeseries_df, fee_dec)` in `pptx_export.py`:

**Eingaben:**
- `timeseries_df`: DataFrame mit Spalten `ret_port`, `ret_bm`, `rf` (Tagessätze)
- `fee_dec`: Honorarsatz dezimal (z.B. 0,012 für 1,2% p.a.)

**Berechnete Ausgaben (Dict):**
```python
{
    "kennzahlen": {
        "performance_pa": (ref_dec, bench_dec),     # CAGR nach Kosten
        "volatilitaet":   (ref_dec, bench_dec),     # std×√365
        "sharpe":         (ref_val, bench_val),     # Sharpe nach Sharpe (1994)
        "max_drawdown":   (ref_dec, bench_dec),     # min(idx/cummax - 1)
    },
    "performance_pa": {
        "jahre":     [2021, 2022, 2023, 2024, 2025],
        "referenz":  [0.054, -0.018, 0.082, ...],   # dezimal pro Kalenderjahr
        "benchmark": [...],
    },
    "wertentwicklung": {
        "dates":     [date(2020,1,1), date(2020,1,2), ...],
        "referenz":  [1.0, 1.0023, 1.0011, ...],    # Index (Start=1.0)
        "benchmark": [...],
    },
}
```

**Architektur:**
- `_fill_performance_slide(prs, slide_idx, strategy_name, performance_data)` orchestriert
- `_fill_kennzahlen_table(table, kz)` füllt die 4 Metric-Rows
- `_replace_chart_data_safe()` (zwei mal) für Säulen + Linien-Chart

### 10.8 Compliance-Anforderungen

Die PPTX wird an Kunden weitergegeben — alle nachfolgenden Regeln sind **nicht verhandelbar**:

| Anforderung | Umsetzung |
|---|---|
| **Anti-Cherry-Picking** | Performance-Folien zeigen **die gesamte verfügbare Historie** |
| **Benchmark wenn gemappt** | BM **immer** angezeigt (UI-Schalter ignoriert) |
| **Nur Nach Kosten** | "Vor Kosten"-Linien werden im Export **nie** gezeigt |
| **Strategieentwurf-Hinweis** | Folie 7 hat Überschrift "Strategieentwurf im Rahmen einer Vermögensverwaltung" |
| **Disclaimer auf jeder Folie** | Standard-Wertentwicklungs-Disclaimer + Quelle + Stand |
| **Mindestens 5 Jahre Historie** | Durch "gesamte Historie zeigen" implizit erfüllt |
| **Strategienamen-Bereinigung** | `cVV`, `Muster`, `Stiftung` werden entfernt |

### 10.9 Streamlit-Integration für Performance-Daten

Im Portfolioanalyse-Tab beim PPTX-Erstellen (`portfolioanalyse.py`):

```python
# Priorität 1: aus session_state
perf_timeseries = st.session_state.get("perf_timeseries", {})
perf_d2c = st.session_state.get("perf_d2c", {})

# Priorität 2 (Fallback): direkt laden wenn leer
if not perf_timeseries:
    date_tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
    files = load_all_csvs(DATA_FOLDER, date_tag, EXCLUDE_SUBSTRINGS)
    if files and mapping_pf is not None:
        perf_timeseries = build_portfolio_timeseries(files, mapping_pf)

# Performance-Inputs zusammenbauen
performance_inputs = []
for pf_name, df_pf, _ad, _dur in portfolios:
    csv_n = perf_d2c.get(pf_name) or display_to_csv_pf.get(pf_name)
    ts_df = perf_timeseries.get(csv_n) if csv_n else None
    fee_dec = float(mapping_pf.loc[mapping_pf["Inhaber"] == csv_n,
                                   "Honorarsatz Standard"].values[0]) * mwst_faktor
    performance_inputs.append({"timeseries_df": ts_df, "fee_dec": fee_dec})

# An generate_portfolioanalyse_pptx übergeben
generate_portfolioanalyse_pptx(portfolios, anlagevolumen, 
                                performance_inputs=performance_inputs)
```

**MwSt-Faktor:** Sidebar-Checkbox `Bruttohonorar (inkl. 19% MwSt.)` × 1.19 wenn aktiviert.

---

## 11. PowerPoint-Vorlage Recipe — Neuaufbau aus Quell-PPTX

**Dieser Abschnitt dokumentiert wie die aktuelle Vorlage `Vorlage_FFPB.pptx` (v7) gebaut wurde — als Recipe für zukünftige Vorlagen-Updates oder ähnliche Projekte.**

### 11.1 Wann brauche ich das?

- Eine Master-PPTX enthält eine wichtige Folie (z.B. Performance-Folie), die in eine bestehende Corporate-Vorlage integriert werden soll
- python-pptx kann keine Slides zwischen Dateien kopieren
- Eine Vorlage ist über die Sessions "verbastelt" und soll von Grund auf sauber neu gebaut werden
- Bilder in einer PPTX sollen optimiert werden (PNG → JPEG)

### 11.2 Phase-Übersicht

| Phase | Schritt | Tool |
|---|---|---|
| 1 | Basis-PPTX kopieren (alle Files in dict) | `zipfile.ZipFile.read()` |
| 2 | Performance-Slide aus Master importieren mit Pfad-Mapping | dict + `RENAME` mapping |
| 3 | Innere Pfade in .rels aktualisieren | String-Replace |
| 4 | `presentation.xml` + .rels: neue Slide registrieren | `lxml.etree` |
| 5 | `slideMaster1.xml` + .rels: neues Layout registrieren | `lxml.etree` |
| 6 | `[Content_Types].xml` erweitern | `lxml.etree` |
| 7 | PNG → JPEG Konvertierung (optional) | PIL + ContentType/rels-Update |
| 8 | ZIP zusammenstellen | `zipfile.ZipFile.writestr()` |

### 11.3 Phase 1 — Basis kopieren

```python
import zipfile, io, re
from PIL import Image
from lxml import etree

ORIG   = "Vorlage_FFPB_original.pptx"           # Corporate-Master ohne Performance-Folie
MASTER = "Anlagevorschlag_Master_Dynamische_Folien.pptx"  # mit Performance-Folie
TARGET = "Vorlage_FFPB_v7.pptx"

files_v7 = {}
with zipfile.ZipFile(ORIG, "r") as z:
    for info in z.infolist():
        files_v7[info.filename] = z.read(info.filename)
```

### 11.4 Phase 2 — Slide-Import mit Pfad-Mapping

```python
# Dependencies der Master-Slide identifizieren (manuell, einmal):
#  master/slide8.xml          → enthält Performance-Folie mit Benchmark
#  master/charts/chart3.xml   → Linien-Chart (Wertentwicklung)
#  master/charts/chart4.xml   → Säulen-Chart (Performance p.a.)
#  master/charts/style3.xml, colors3.xml, style4.xml, colors4.xml
#  master/embeddings/Microsoft_Excel_Worksheet2.xlsx (chart3)
#  master/embeddings/Microsoft_Excel_Worksheet3.xlsx (chart4)
#  master/slideLayouts/slideLayout17.xml (Anlagestrategie Wertentwicklung)

# Pfad-Mapping master → v7 (neue freie Indizes)
RENAME = {
    "ppt/slides/slide8.xml": "ppt/slides/slide26.xml",
    "ppt/slides/_rels/slide8.xml.rels": "ppt/slides/_rels/slide26.xml.rels",
    "ppt/charts/chart3.xml": "ppt/charts/chart8.xml",   # Line → chart8
    "ppt/charts/_rels/chart3.xml.rels": "ppt/charts/_rels/chart8.xml.rels",
    "ppt/charts/style3.xml": "ppt/charts/style8.xml",
    "ppt/charts/colors3.xml": "ppt/charts/colors8.xml",
    "ppt/charts/chart4.xml": "ppt/charts/chart7.xml",   # Bar → chart7
    "ppt/charts/_rels/chart4.xml.rels": "ppt/charts/_rels/chart7.xml.rels",
    "ppt/charts/style4.xml": "ppt/charts/style7.xml",
    "ppt/charts/colors4.xml": "ppt/charts/colors7.xml",
    "ppt/embeddings/Microsoft_Excel_Worksheet2.xlsx": "ppt/embeddings/Microsoft_Excel_Worksheet2.xlsx",
    "ppt/embeddings/Microsoft_Excel_Worksheet3.xlsx": "ppt/embeddings/Microsoft_Excel_Worksheet1.xlsx",
    "ppt/slideLayouts/slideLayout17.xml": "ppt/slideLayouts/slideLayout29.xml",
    "ppt/slideLayouts/_rels/slideLayout17.xml.rels": "ppt/slideLayouts/_rels/slideLayout29.xml.rels",
}

with zipfile.ZipFile(MASTER, "r") as z:
    for old_path, new_path in RENAME.items():
        files_v7[new_path] = z.read(old_path)
```

### 11.5 Phase 3 — Innere Pfade in .rels aktualisieren

```python
def update_rels(rels_str, mappings):
    for old, new in mappings.items():
        rels_str = rels_str.replace(f'Target="{old}"', f'Target="{new}"')
    return rels_str

# slide26.xml.rels: enthielt master-Pfade
content_str = files_v7["ppt/slides/_rels/slide26.xml.rels"].decode("utf-8")
content_str = update_rels(content_str, {
    "../charts/chart3.xml": "../charts/chart8.xml",
    "../charts/chart4.xml": "../charts/chart7.xml",
    "../slideLayouts/slideLayout17.xml": "../slideLayouts/slideLayout29.xml",
})
files_v7["ppt/slides/_rels/slide26.xml.rels"] = content_str.encode("utf-8")

# chart8.xml.rels: war chart3.xml.rels
content_str = files_v7["ppt/charts/_rels/chart8.xml.rels"].decode("utf-8")
content_str = update_rels(content_str, {
    "colors3.xml": "colors8.xml",
    "style3.xml": "style8.xml",
})
files_v7["ppt/charts/_rels/chart8.xml.rels"] = content_str.encode("utf-8")

# chart7.xml.rels: war chart4.xml.rels (mit Worksheet-Umnummerierung!)
content_str = files_v7["ppt/charts/_rels/chart7.xml.rels"].decode("utf-8")
content_str = update_rels(content_str, {
    "../embeddings/Microsoft_Excel_Worksheet3.xlsx": "../embeddings/Microsoft_Excel_Worksheet1.xlsx",
    "colors4.xml": "colors7.xml",
    "style4.xml": "style7.xml",
})
files_v7["ppt/charts/_rels/chart7.xml.rels"] = content_str.encode("utf-8")
```

### 11.6 Phase 4 — Slide in presentation.xml registrieren

```python
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"

# presentation.xml.rels: neue Slide-Relationship
pres_rels = etree.fromstring(files_v7["ppt/_rels/presentation.xml.rels"])
existing_rids = [r.get("Id") for r in pres_rels.findall(f"{{{NS_PKG}}}Relationship")]
new_rid = f"rId{max(int(r[3:]) for r in existing_rids if r.startswith('rId')) + 1}"

new_rel = etree.SubElement(pres_rels, f"{{{NS_PKG}}}Relationship")
new_rel.set("Id", new_rid)
new_rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide")
new_rel.set("Target", "slides/slide26.xml")

# presentation.xml: sldIdLst erweitern an Position 9 (= Slide 10 in UI)
pres = etree.fromstring(files_v7["ppt/presentation.xml"])
sld_ids = pres.findall(f".//{{{NS_P}}}sldIdLst/{{{NS_P}}}sldId")
new_sld_id = max(int(s.get("id")) for s in sld_ids) + 1

new_sld = etree.Element(f"{{{NS_P}}}sldId")
new_sld.set("id", str(new_sld_id))
new_sld.set(f"{{{NS_R}}}id", new_rid)
pres.find(f"{{{NS_P}}}sldIdLst").insert(9, new_sld)  # Position 9 = Slide 10

files_v7["ppt/presentation.xml"] = etree.tostring(
    pres, xml_declaration=True, encoding="UTF-8", standalone=True
)
files_v7["ppt/_rels/presentation.xml.rels"] = etree.tostring(
    pres_rels, xml_declaration=True, encoding="UTF-8", standalone=True
)
```

### 11.7 Phase 5 — Layout im slideMaster registrieren

```python
# slideMaster1.xml.rels: slideLayout29 als neue Relationship
sm_rels = etree.fromstring(files_v7["ppt/slideMasters/_rels/slideMaster1.xml.rels"])
existing_sm_rids = [r.get("Id") for r in sm_rels.findall(f"{{{NS_PKG}}}Relationship")]
new_layout_rid = f"rId{max(int(r[3:]) for r in existing_sm_rids if r.startswith('rId')) + 1}"

new_layout_rel = etree.SubElement(sm_rels, f"{{{NS_PKG}}}Relationship")
new_layout_rel.set("Id", new_layout_rid)
new_layout_rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout")
new_layout_rel.set("Target", "../slideLayouts/slideLayout29.xml")

# slideMaster1.xml: sldLayoutIdLst erweitern
sm = etree.fromstring(files_v7["ppt/slideMasters/slideMaster1.xml"])
layout_lst = sm.find(f"{{{NS_P}}}sldLayoutIdLst")
existing_ids = [int(e.get("id")) for e in layout_lst.findall(f"{{{NS_P}}}sldLayoutId")]
new_layout_entry = etree.SubElement(layout_lst, f"{{{NS_P}}}sldLayoutId")
new_layout_entry.set("id", str(max(existing_ids) + 1))
new_layout_entry.set(f"{{{NS_R}}}id", new_layout_rid)

files_v7["ppt/slideMasters/slideMaster1.xml"] = etree.tostring(sm, ...)
files_v7["ppt/slideMasters/_rels/slideMaster1.xml.rels"] = etree.tostring(sm_rels, ...)
```

### 11.8 Phase 6 — ContentTypes erweitern

```python
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
ct = etree.fromstring(files_v7["[Content_Types].xml"])

NEW_OVERRIDES = [
    ("/ppt/slides/slide26.xml", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"),
    ("/ppt/charts/chart7.xml", "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"),
    ("/ppt/charts/chart8.xml", "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"),
    ("/ppt/charts/style7.xml", "application/vnd.ms-office.chartstyle+xml"),
    ("/ppt/charts/style8.xml", "application/vnd.ms-office.chartstyle+xml"),
    ("/ppt/charts/colors7.xml", "application/vnd.ms-office.chartcolorstyle+xml"),
    ("/ppt/charts/colors8.xml", "application/vnd.ms-office.chartcolorstyle+xml"),
    ("/ppt/slideLayouts/slideLayout29.xml", "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"),
]
for partname, ct_type in NEW_OVERRIDES:
    ov = etree.SubElement(ct, f"{{{NS_CT}}}Override")
    ov.set("PartName", partname)
    ov.set("ContentType", ct_type)

files_v7["[Content_Types].xml"] = etree.tostring(ct, ...)
```

### 11.9 Phase 7 — PNG → JPEG Optimierung (siehe Transferwissen #13)

```python
TO_JPEG = ["image4.png", "image7.png", "image8.png", "image11.png", "image12.png",
           "image13.png", "image14.png", "image15.png", "image16.png", "image18.png",
           "image20.png", "image25.png", "image26.png", "image27.png", "image28.png",
           "image29.png", "image30.png", "image31.png", "image32.png"]

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

# Files konvertieren
files_v7_new = {}
for path, content in files_v7.items():
    if path.startswith("ppt/media/"):
        bn = path.split("/")[-1]
        if bn in TO_JPEG:
            jpeg = png_to_jpeg(content)
            new_path = path.replace(".png", ".jpeg")
            files_v7_new[new_path] = jpeg
            continue
    files_v7_new[path] = content
files_v7 = files_v7_new

# Pfade in ContentTypes + rels aktualisieren
for path in list(files_v7.keys()):
    if path == "[Content_Types].xml" or path.endswith(".rels"):
        s = files_v7[path].decode("utf-8")
        for img in TO_JPEG:
            jpeg_img = img.replace(".png", ".jpeg")
            s = s.replace(f"media/{img}", f"media/{jpeg_img}")
            s = s.replace(f"/ppt/media/{img}", f"/ppt/media/{jpeg_img}")
        files_v7[path] = s.encode("utf-8")
```

### 11.10 Phase 8 — ZIP zusammenstellen + Validieren

```python
with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED) as zout:
    for path, content in files_v7.items():
        zout.writestr(path, content)

# Validierung (Transferwissen #16)
from pptx import Presentation
prs = Presentation(TARGET)
print(f"✓ {len(prs.slides)} Slides, {os.path.getsize(TARGET)/1024/1024:.2f} MB")
```

### 11.11 Layout-Anpassungen (Post-Build)

Nach dem Neuaufbau wurden noch drei Layout-Mods angewendet:

```python
# 1. "ASSETKLASSEN" → "AKTUELLE STRUKTUR" in drawing1.xml + slideLayout26.xml
# 2. Tabellen-Header "Rating" → "Marktrisikowert" in slide8.xml (UI Slide 7)
# 3. "Linie links" Y-Position: 5240797 EMU → 5848626 EMU (auf gleiche Höhe wie "Linie rechts")
```

EMU = English Metric Unit, 914400 EMU = 1 Zoll.

### 11.12 Resultat

- **Vorher:** Vorlage v5/v6 mit Altlasten, 8.4 MB, gelegentliche Reparieren-Dialoge
- **Nachher (v7):** Vorlage 4.14 MB, 25 Slides, 0 XML-Fehler, sauber neu gebaut, generierte PPTX 4.22 MB
- **Generierungs-Zeit:** 0.6s (vorher ~2s)
- **Streamlit-Cloud:** kein progress.html-Timeout mehr

---

## 12. Berechnungsformeln

```
daily_drag      = (1 + fee_pa)^(1/365) - 1
idx_nach_kosten = idx[i-1] * (1 + ret - daily_drag)
cagr            = (endwert/startwert)^(365/tage) - 1
vola            = std(tagesrenditen) * sqrt(365)
calmar          = cagr / |max_drawdown|
gew_duration    = Σ(gewicht × duration) / Σ(gewichte_anleihen)
```

### Sharpe Ratio – wissenschaftlich saubere Variante nach Sharpe (1994)

```
daily_rf[t]   = (1 + rf_annual[t])^(1/365) - 1
excess[t]     = ret_port_nachKosten[t] - daily_rf[t]
sharpe_daily  = mean(excess) / std(excess, ddof=1)
sharpe_p.a.   = sharpe_daily × √365
```

Implementiert in `calc_sharpe_excess(draf, df["rf"])` in `streamlit_app.py` und in `compute_performance_data()` in `pptx_export.py`.

### Risikofreier Zins – Aggregation (geometrisch)

```
daily_rf = (1 + rf_annual)^(1/365) - 1
growth   = Π (1 + daily_rf)
rf_pa    = growth^(365 / n_days) - 1
```

### rf-Index für Chart

```
daily_rf[i] = (1 + rf_annual[i])^(1/365) - 1
idx[i]      = idx[i-1] * (1 + daily_rf[i])
```

---

## 13. Roadmap — Geplante Implementierungen

### 13.1 Aktueller Stand (Juni 2026)

| Aufgabe | Status |
|---|---|
| **Aufgabe A:** Strategieentwurf-Überschrift auf PPTX Folie 7 | ⚠️ Offen |
| **Aufgabe B:** Seitenzahlen in PDF-Druckversionen | ⚠️ Offen (Position-Spec ausstehend) |
| **Aufgabe C:** Seitenzahlen in PPTX dynamisch | ⚠️ Offen |
| **Aufgabe D:** Performance-PPTX-Export | ✅ **ERLEDIGT (Juni 2026)** |

### 13.2 Aufgabe A: Strategieentwurf-Überschrift

- **Was:** Überschrift "Anlagevorschlag" → "Strategieentwurf im Rahmen einer Vermögensverwaltung"
- **Wo:** Nur Folie 7
- **Aufwand:** Trivial (~10 Min)

### 13.3 Aufgabe B: PDF-Seitenzahlen

- **Was:** Seitenzahlen analog zur PPTX
- **Wo:** `streamlit_app.py` (Performance-PDF) + `portfolioanalyse.py` (Portfolioanalyse-PDF)
- **Position:** NOCH ZU KLÄREN
- **Aufwand:** Klein (~30 Min)

### 13.4 Aufgabe C: PPTX-Seitenzahlen dynamisch

- **Problem:** Vorlage hat statische Seitenzahlen, aber dynamisches Slide-Reorder beim Export
- **Lösung:** Über alle Slides iterieren, `Foliennummer`-Shape mit korrekter Position befüllen
- **Aufwand:** Mittel (~1h)

### 13.5 Aufgabe D — ERLEDIGT (Juni 2026)

**Performance-PPTX-Export** wurde vollständig implementiert. Details:

- ✅ `_fill_performance_slide()` in `pptx_export.py`
- ✅ `compute_performance_data()` mit allen Kennzahlen + Chart-Daten
- ✅ `_replace_chart_data_safe()` mit Workaround für 3 python-pptx-Bugs
- ✅ Streamlit-Integration: session_state + Fallback-Loader
- ✅ MwSt-Checkbox in Portfolioanalyse-Sidebar
- ✅ Sauber neu aufgebaute Vorlage v7 mit Performance-Folie an Slide 10
- ✅ 4.14 MB Vorlage (statt 22.7 MB), löst Streamlit-Cloud progress.html

**Architektur abweichend von ursprünglicher Spec:**
- Performance-Folie wurde Teil des **Portfolioanalyse-Tabs** (nicht separater Performance-Tab-Button), weil sie strukturell mit Slide 7-9 zusammengehört
- Nur EINE Performance-Folie statt der ursprünglich geplanten F1/F2/F3-Variante (kann später erweitert werden)

### 13.6 Sonstige Pflege-Punkte

- Ggf. F2/F3-Varianten (ohne BM / Berater-Zeitraum) als zusätzliche Slides
- Sharpe + rf-Linie auch in Portfolioanalyse-Tab
- Bei Bedarf: Portfolio-Builder-Reaktivierung

---

## 14. Changelog

### Juni 2026 (Phase 2) – Performance-PPTX-Export implementiert + Vorlage-Neuaufbau

**Phase 2.1 — Performance-Daten-Berechnung (`pptx_export.py`)**
- `compute_performance_data(timeseries_df, fee_dec)` neu: berechnet alle Kennzahlen, Säulen-Chart-Daten (5 Kalenderjahre) und Linien-Chart-Daten (gesamte Historie) aus einer Zeitreihe
- `_fill_performance_slide(prs, slide_idx, strategy_name, performance_data=None)` befüllt Titel + Tabelle + 2 Charts; bei `performance_data=None` werden nur Titel gesetzt (Phase-1-Verhalten)
- Berechnungs-Funktionen aus `streamlit_app.py` dupliziert: `_calc_cagr`, `_calc_vola`, `_calc_sharpe_excess`, `_calc_max_drawdown`, `_make_index_after_fee`
- `_fmt_pct()`, `_fmt_ratio()` für deutsche Zahlenformatierung in der Tabelle

**Phase 2.2 — python-pptx Bug-Workaround (`_replace_chart_data_safe`)**
- 3 Bugs in `chart.replace_data()` identifiziert und gefixt (siehe Transferwissen #12):
  - Bug 1: embedded Excel nicht aktualisiert → `<c:externalData>` entfernen
  - Bug 2: `style*.xml` mit ZIP-Header überschrieben → Backup-Restore Pattern
  - Bug 3: Format-Codes auf "General" → `_restore_data_label_format()`
- Vollständige Diagnose dokumentiert (siehe `WISSENSBASIS.md` im Workspace)

**Phase 2.3 — Streamlit-Integration (`portfolioanalyse.py`)**
- Sidebar-Checkbox `pf_brutto_mwst` für Bruttohonorar (×1.19)
- PPTX-Button-Block baut `performance_inputs` aus session_state + load_mapping + mwst_faktor
- **Fallback-Loader** (Transferwissen #15): wenn session_state leer → direkt aus `Daten/`-Ordner laden
- Diagnose-Warnung wenn ein gewähltes Portfolio nicht in den Performance-Daten gefunden wird

**Phase 2.4 — shared.py erweitert**
- CSV-Loading-Helpers verschoben aus `streamlit_app.py`: `to_decimal_interval`, `read_one_csv`, `parse_dates_col`, `extract_benchmark_name`, `load_all_csvs`, `build_portfolio_timeseries`
- Damit können sowohl Performance-Tab als auch Portfolioanalyse-Tab die Daten laden

**Phase 2.5 — streamlit_app.py erweitert**
- Im Performance-Tab nach Daten-Load: `st.session_state["perf_timeseries"] = data` + `st.session_state["perf_d2c"] = d2c`
- Damit kann Portfolioanalyse-Tab die Daten direkt nutzen (mit Fallback wenn leer)

**Phase 2.6 — Vorlage komplett neu aufgebaut (v5/v6 → v7)**
- Problem: v5 hatte Altlasten aus mehreren Modifikations-Sessions, gelegentliche PowerPoint-Reparieren-Dialoge
- Lösung: Sauberer Neuaufbau aus Original (22.7 MB, ohne Performance-Folie) + Master (mit Performance-Folie)
- **`build_v7.py` Skript** (siehe Abschnitt 11 für Details):
  1. Original-Vorlage als Basis (alle 181 Files)
  2. Performance-Slide aus Master importiert mit Umnummerierung (slide8→26, chart3/4→7/8, etc.)
  3. presentation.xml + slideMaster.xml + ContentTypes synchron erweitert
  4. 19 PNGs zu JPEG q=85 konvertiert (alle hatten fake-Alpha min=255)
- **Layout-Mods auf v7**: "AKTUELLE STRUKTUR", "Marktrisikowert"-Header, Linien-Y-Alignment
- **Resultat:** Vorlage 4.14 MB (statt 22.7 MB), 25 Slides, 0 XML-Fehler, sauber

**Phase 2.7 — Transferwissen erweitert**
- Transferwissen #12: python-pptx `chart.replace_data()` Bug-Trio
- Transferwissen #13: PNG → JPEG mit Alpha-Check für PPTX-Optimierung
- Transferwissen #14: Slide-Copy zwischen PPTX-Dateien (ZIP-Workflow)
- Transferwissen #15: Streamlit Cross-Tab Daten-Sharing mit Fallback-Strategie
- Transferwissen #16: PPTX-Validierung Multi-Layer-Toolchain
- Transferwissen #17: Office-Dokumente sind ZIPs (Manipulation-Recipe)

**Performance-Test Phase 2 (Endzustand):**
- Generation: 0.60s (mit 5-Jahres-Zeitreihe)
- PPTX-Größe: 4.22 MB
- 0 XML-Fehler in Validation
- 0 PK-Header in XML-Files (kein style-corruption)
- `<c:externalData>` korrekt entfernt aus chart7 und chart8

### Juni 2026 – Brainstorming PowerPoint-Export-Erweiterung
- Email-Anforderung mit 3 Compliance-Punkten dokumentiert
- Bestehender PPTX-Export erstmals in Doku dokumentiert
- Performance-PPTX-Export als großes Feature spezifiziert (→ dann in Phase 2 implementiert)
- Master-Vorlage `Anlagevorschlag_Master_Dynamische_Folien.pptx` als Quelle für Performance-Folie identifiziert

### Juni 2026 – Performance-Tab auf Corporate Colors umgestellt
- Strategie A: Konstanten in `shared.py` direkt umdefiniert (single source of truth)
- `FFPB_DARK`, `FFPB_GOLD`, `FFPB_LIGHT`, `FFPB_BLUE2` auf Fürst-Fugger-Hex-Werte
- Neue Konstanten: `FFPB_SAND`, `FFPB_PALETTE` (15 Farben)
- Plotly-Linien-Charts nutzen `colorway=FFPB_PALETTE` (Transferwissen #10)

### Juni 2026 – Disclaimer-Wording auf Vermögensverwaltung
- Compliance-Abstimmung: "im Beratungsgespräch" → "der Vermögensverwaltungsstrategien im Kundengespräch"

### Juni 2026 – Tab "Portfolio zusammenstellen" deaktiviert
- Compliance-Entscheidung

### Mai 2026 (Validierung) – Echtdaten-Test mit 17-Jahres-Zeitreihe
- Sharpe-Berechnung und rf-Verarbeitung mit echter Zeitreihe (31.12.2008 – 12.05.2026, ~6300 Tageswerte) validiert

### Mai 2026 – Sharpe Ratio auf Excess-Return-Variante

### Mai 2026 – Risikofreier Zins & Sharpe Ratio (Erstimplementierung)

### April 2026 – Initiale Doku-Version

---

## 15. Für den nächsten Chat / Kollegen

**Hochladen:** Diese MD + 4 aktive Code-Dateien (`streamlit_app.py`, `modules/shared.py`, `modules/portfolioanalyse.py`, `modules/pptx_export.py`).  
**Sagen:** "Lies die PROJEKT_DOKUMENTATION.md zuerst komplett. Dann [Aufgabe]."  
**Bei Problemen:** Screenshot + erwartetes Verhalten + welche Dateien aktuell deployed sind.

**Wichtig bei CSV-Änderungen:** Nach Deploy IMMER Cache leeren (Transferwissen #7).

**Wichtig bei PPTX-Änderungen:** 
- Nach jedem Code-Update einmal lokal mit echten Daten testen, in PowerPoint öffnen
- python-pptx `chart.replace_data()` NIE direkt nutzen — immer durch `_replace_chart_data_safe()` (Transferwissen #12)
- Bei Datei-Größe > 9 MB: PNG-Optimierung prüfen (Transferwissen #13)
- Bei "Reparieren"-Dialog: Multi-Layer-Validierung laufen lassen (Transferwissen #16)

**Wichtig bei Vorlage-Updates:**
- Original-Vorlage immer als Master behalten (`/mnt/user-data/uploads/` oder eigenes Archiv)
- Bei "Vorlage scheint kaputt": lieber neu aufbauen (Recipe in Abschnitt 11) statt zu reparieren
- Shape-Namen müssen exakt übereinstimmen (`Titel`, `Tabelle`, `Diagramm links`, `Diagramm rechts`, ...)

*Stand: Juni 2026 (Phase 2 abgeschlossen)*
