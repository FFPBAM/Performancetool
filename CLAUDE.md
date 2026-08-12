# Arbeitsanweisung für Claude — FFPB Performancetool

**Zuerst lesen:** `STATUS.md` (wo stehen wir), dann `PROJEKT_DOKUMENTATION.md`
(50 Transferwissen-Einträge, Architektur, Compliance).

Streamlit-App der Fürst Fugger Privatbank, die aus Corporate-Vorlagen
PowerPoint-Broschüren erzeugt. **Die Ergebnisse gehen an Kunden.**

---

## Die drei Regeln, die hier am meisten zählen

**1. Diagnose vor Lösung.** Am echten Artefakt beweisen — Chart-XML auslesen,
Tabellen-Rahmen dumpen, die Broschüre erzeugen und hineinschauen. Nicht aus
dem Code schließen, was passieren müsste. Zwei Fehler dieser Codebasis
(Trennstriche, Historien-Beginn) sahen im Code völlig unauffällig aus.

**2. Ein Prüfstein je Lieferung.** Jede Korrektur braucht einen Test, der auf
dem alten Stand **rot** und danach **grün** ist. Ein Test, der nur grün ist,
beweist nichts.

**3. Beweisen, dass nichts kaputtgeht.** Bei Umbauten die Ergebnisse
vorher/nachher vergleichen. PPTX sind ZIPs mit eingebetteten ZIPs — rekursiv
vergleichen, Zeitstempel ignorieren. Für die **Oberfläche** gibt es dasselbe
seit 12.08.2026: `python tests/ui_dump.py vorher.json`, umbauen,
`nachher.json`, vergleichen.

**Und beim Testen rechnender Funktionen:** immer auch leere Liste, ein
Element, konstante Werte, NaN und Null durchschicken. Alle drei Fehler der
Testrunde vom 12.08.2026 saßen dort und keiner in den fachlich interessanten
Fällen — darunter eine Sharpe Ratio von 8,4·10¹⁶, weil ein Guard auf `== 0`
prüfte statt gegen eine Schwelle (#47).

---

## Was hier anders ist als in normalen Projekten

- **Compliance ist nicht verhandelbar** (Doku §10.9): gesamte Historie
  zeigen (Anti-Cherry-Picking), Benchmark immer wenn gemappt, nur „nach
  Kosten", Disclaimer auf jeder Folie. Keine stillen Datenverluste.
- **Konsistenz-Doktrin** (§10.8): Die PowerPoint ist kanonisch. Tool-Anzeige
  darf abweichen, aber sichtbar. Beide Pfade nutzen `modules/analytics.py` —
  Mathematik gehört dorthin und **nirgendwo sonst hin kopiert**.
- **Das Repo ist öffentlich.** Keine Zugangsdaten, keine Kundendaten
  einchecken. `.gitignore` schützt `secrets.toml` — nicht aufweichen.
- **Keine Piktogramme in der Oberfläche** (10.08.2026). Überschriften,
  Hinweise, Schaltflächen und Disclaimer tragen keine Emoji — die Ergebnisse
  gehen ins Kundengespräch einer Privatbank. In Kommentaren und Doku sind sie
  erlaubt. Prüfstein: `tests/test_keine_piktogramme.py`.
- **`chart.replace_data()` ist verseucht** (#12, vier Bugs). Immer
  `replace_chart_data_safe()`, Ringe über `replace_chart_data`.
- **Neuer `st.button(key=…)` → Key in `_KEEPALIVE_SPERRE`** (oben in
  `streamlit_app.py`). Sonst stürzt die Seite ab: Das Keep-Alive schreibt
  alle session_state-Keys zurück, und für Button-Keys ist das verboten. Die
  Zuweisung selbst wirft nichts — erst das spätere `st.button()`, weshalb der
  Traceback auf den Button zeigt statt auf die Ursache und das `try/except`
  im Keep-Alive **nicht** hilft (#19, korrigiert 11.08.2026).
- **Datumsfelder zurücksetzen nur über Counter-Keys** (#4, Lösung A):
  `st.session_state["p_sd"] = …` wirft bei aktivem Widget. Ein neuer Key
  (`p_sd_0` → `p_sd_1`) erzeugt ein frisches Widget mit seinem Default.
- **Ein Fehlwert darf nicht wie ein Messwert aussehen** (#46, 11.08.2026).
  Fehlt eine Größe, wird die Liste **leer** gelassen und ein ausdrückliches
  Kennzeichen mitgegeben — nicht mit `0.0`/`1.0` aufgefüllt. Sonst kann keine
  nachgelagerte Stelle „gibt es nicht" von „ist null" unterscheiden. Und beim
  Weglassen einer Größe ist **jeder** Ort zu prüfen, an dem sie vorkommt:
  Chart-Serie, statische Legenden-Textbox, Fußnote, Folientitel.
- **Statischer Vorlagentext wird in der VORLAGE geändert, nicht im Code.**
  Bis 10.08.2026 schrieb der Export die Legende der Wertentwicklungs-Folie
  von „Musterdepot" auf „Referenzportfolio" um — niemand sah der Vorlage noch
  an, was gedruckt wird. Zurückgenommen. Code fasst statischen Text nur an,
  wenn er *dynamisch* werden muss (Datenstand, Benchmark-Zusammensetzung,
  Kennzahlen-Labels). Reine Wording-Wünsche gehören in die `.pptx`.
  **Die eine Ausnahme:** Text, der an ZWEI Stellen erscheinen muss (Tool
  *und* Broschüre), braucht EINE Quelle — sonst läuft er auseinander. Dann
  gewinnt eine gepflegte Konfigurationsdatei, und die Vorlage wird zum
  Ausgabeziel. So bei den Anlagekriterien (`Mapping_Anlagekriterien.xlsx`,
  10.08.2026). Der Unterschied zum Musterdepot-Fall: Dort widersprach der
  Code der Vorlage *heimlich*; hier ersetzt eine sichtbare Datei sie als
  Quelle. Wer eine weitere solche Ausnahme anlegt, dokumentiert sie hier.
  **Die zweite Ausnahme** *(12.08.2026)*: die **Position** der Quelle-Box
  auf der Wertentwicklungs-Folie (`WE_QUELLE_TOP_CM`). Es geht nicht um
  Text, sondern um Geometrie — und um eine Box, deren Inhalt der Code
  ohnehin schreibt (das Stand-Datum). Ein Eingriff deckt 16 Folien in
  sechs Vorlagen ab, die sonst einzeln in PowerPoint nachzuziehen wären.
- **Wer Text in eine Box mit fester Geometrie schreibt, muss die Geometrie
  mitdenken** (#50, 12.08.2026). Der Disclaimer der Wertentwicklungs-Folie
  ist in der Vorlage **hart umbrochen**; die Zeilenbreite (149 Zeichen bei
  6 pt) steht nirgends in der Datei. Ein Ersatztext darüber bricht **still**
  um, und alles darunter rutscht eine Zeile tiefer — so landete die
  Quellenangabe unter dem Fließtext. Die Breite steht jetzt als
  `WE_FUSSNOTE_ZEILE_MAX` im Code, Prüfstein
  `tests/test_quelle_position.py`. Und die allgemeine Lehre: **Eine
  Bedingung, die ein Kommentar nennt, ist ein Testfall.** Genau diese Regel
  stand seit Juli 2026 als Kommentar da („auf ähnliche Länge kalibriert,
  damit das Layout hält") — gemessen hat sie nie jemand.
- **Kollisionen sieht man nicht im XML.** python-pptx kennt keine
  Zeilenumbrüche; zwei überlappende Rechtecke sind für sich noch kein
  Fehler. Wo es um Layout geht, gibt PowerPoint per COM die Folie als PNG
  aus, und gemessen wird das Bild:
  `$ppt = New-Object -ComObject PowerPoint.Application` →
  `$pres.Slides.Item(N).Export(<pfad>.png, "PNG", 1920, 1225)`. Das ist
  #16/#28 mit anderen Mitteln — und ein Test kann es selbst erzeugen.
- **Ein Eintrag in `Mapping_Anlagekriterien.xlsx` kann in einer Kundenbroschüre
  landen** (12.08.2026). `pptx_export` ruft `fill_anlagekriterien_slide` für
  **jede** Familie auf — ob gedruckt wird, entscheidet allein, ob die Vorlage
  eine Kriterien-Tabelle hat. `Vorlage_Thema.pptx` hat keine, deshalb stehen
  Offensiv/Pro/Pro Dividende seit dem 12.08.2026 nur im **Tool**. Wer dieser
  Vorlage eine Tabelle gibt, druckt sie damit **automatisch** — Schritt 4b in
  `tests/test_anlagekriterien.py` schlägt in dem Fall an.
- **Chart-Achsen: das Ende zählt mehr als der Anfang** (#49, 12.08.2026).
  PowerPoint verankert die Ticks einer Datumsachse am **Achsen-Minimum**, nicht
  am Kalender. Wer das Minimum auf den ersten Datenpunkt legt, verankert das
  ganze Raster auf dessen Monat — und die letzte Beschriftung fällt vor das
  aktuelle Jahr. `majorUnit` und `majorTimeUnit` sind ein **Paar**: eines
  allein zu setzen verstellt den Abstand um den Faktor der Vorlage. Und ein
  Achsen-Element, das eine von sechs Vorlagen nicht hat, macht aus
  `if el is not None` einen stillen Aussetzer — Elemente müssen **angelegt**
  werden können, in Schema-Reihenfolge. Prüfstein:
  `tests/test_chartachsen.py`, Stellschrauben: `DATUMSACHSE_STUFEN` und
  `WERTACHSE_STUFEN`.
- **Die Spalte „Anleihenanteil / Liquidität" trägt zwei Bedeutungen.** Wo eine
  Strategie keine Anleihen hält, steht dort die **Liquiditätsgrenze**: `cVV
  dynamic` „max. 10 %", Pro und Pro Dividende „max. 15 %". Die Bank-Webseite
  nennt an dieser Stelle „0 %" — das ist **kein Widerspruch** und nicht zu
  „korrigieren" (Philip, 12.08.2026).

---

## Wo was hingehört

| Datei | Zuständig für |
|---|---|
| `modules/analytics.py` | **alle** Berechnungen (CAGR, Vola, Sharpe, Drawdown) |
| `modules/vorlagen_config.py` | Broschüren-Bauplan: Folienlisten, Familien, Dateinamen, `HISTORIE_AB` |
| `modules/pptx_slides.py` | **was** auf einer Folie steht (Werte) |
| `modules/chart_dynamik.py` | **wie** es aussieht (Optik, nie Werte) |
| `modules/pptx_helpers.py` | generische PPTX-Mechanik |
| `modules/pptx_charts.py` | Chart-XML + Bug-Workarounds |
| `modules/shared.py` | Konstanten, Login, CSV-Loader, `APP_TITLE` (Name des Tools) — **Formatierung nur noch durchgereicht** |
| `modules/formats.py` | **alle** Zahlen-, Prozent- und Datumsformate + Fehlwert `–`; streamlit-frei, gilt für Tool *und* Broschüre |
| `modules/anlagekriterien.py` | Anlagekriterien je Strategie — **streamlit-frei**, weil Tool *und* Export sie brauchen |

**Eine neue Folie oder Familie?** Nur `vorlagen_config.py` anfassen.
`vorlagen_config.py` hat bewusst **keine Importe** — das bitte so lassen.

**Loader oder Mathematik nie duplizieren.** Genau daran krankte die Codebasis
(zwei Kopien der CSV-Loader, elf Kopien der analytics-Funktionen). Wer etwas
ohne Streamlit braucht, zieht es in ein UI-freies Modul — er kopiert es nicht.
`analytics.py` importiert bewusst nur numpy und pandas; von dort darf jedes
Modul importieren, ohne Streamlit hereinzuziehen. Die **Kosten-Mathematik**
ist seit 12.08.2026 per Test darauf festgenagelt, dass sie nur dort steht
(`tests/test_kosten_mathematik.py`) — eine zweite Kopie fällt nicht auf,
solange die Formeln gleich sind, und genau das ist die Gefahr.

---

## Testen

```
python tests/test_bedienung.py               # + streamlit (AppTest)
python tests/test_streamlit_api.py           # ohne jedes Paket
python tests/test_keine_piktogramme.py       # ohne jedes Paket
python tests/test_anlagekriterien.py         # pandas + streamlit
python tests/test_app_titel.py               # Schritt 1+2 ohne jedes Paket
python tests/test_legende_musterdepot.py     # Schritt 1 ohne jedes Paket
python tests/test_kosten_mathematik.py       # Schritt 1 ohne jedes Paket
python tests/test_formats.py                 # Schritte 1-4+6 ohne jedes Paket
python tests/test_analytics.py               # nur numpy + pandas
python tests/test_benchmark_erkennung.py     # nur pandas
python tests/test_benchmark_charts.py        # Schritt 1 pandas, 2+3 + pptx/streamlit
python tests/test_honorarsatz.py             # pandas + streamlit
python tests/test_historie_ab.py             # pandas + streamlit
python tests/test_folien_config.py           # pandas + streamlit
python tests/test_chartachsen.py [<ordner>]  # Schritte 1+2 ohne jedes Paket
python tests/test_quelle_position.py [<ordner>]  # + python-pptx
python tests/test_export_smoke.py <ordner>   # + python-pptx, streamlit
python tests/test_trennstriche.py <ordner>   # + python-pptx
```

Dazu ein Werkzeug, kein Test — für den Beweis nach einem UI-Umbau:

```
python tests/ui_dump.py vorher.json     # umbauen, dann nachher.json, vergleichen
```

Tests bewusst **ohne pytest** — sie sollen in der eingeschränkten
Firmenumgebung laufen. Neue Tests genauso schreiben: Schritte einzeln
ausgeben, fehlende Pakete **überspringen statt scheitern**, Rückgabewert 0/1.

`pip` funktioniert (entgegen älterer Doku-Aussagen). Für den vollen Export:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Statische Prüfung nicht vergessen:** `py_compile` findet keine
undefinierten Namen. Nach dem Entfernen von Importen oder Funktionen immer
`pyflakes` laufen lassen. **Der Lauf über das ganze Repo ist seit 12.08.2026
bei null Meldungen — bitte so lassen.** Jede neue Meldung ist damit ein
echtes Signal. Zwei Fallstricke: `pyflakes` kennt **kein `noqa`** (ein
Kommentar beruhigt es nie — Namen stattdessen per Zuweisung weiterreichen,
siehe `shared.py`), und eine unbenutzte Variable kann die **Spur einer
entfernten Funktion** sein: `git log -S <name>` klärt das in zehn Sekunden,
bevor man sie löscht (#47).

---

## Git

- **Gearbeitet wird in `C:\Entwicklung\Performancetool`** (seit 10.08.2026).
  DRACOON (`H:\…`) ist nur Ablage und wird am Sessionende nachgezogen —
  Ablauf in `STATUS.md`. Wahrheit ist GitHub, Branch `verbesserungen`.
- Auf einem Branch arbeiten, `main` nie direkt anfassen.
- Ein Commit je Thema, **deutsche** Nachricht mit Begründung und Messwerten.
- Vor dem Push: alle Tests grün.
- Netzlaufwerk-Eigenheit: DRACOON legt kurzlebige Dateien an (`__init__.py`,
  `py.typed` erscheinen und verschwinden von selbst) — `git add -A` kann
  daran scheitern. **Dateien immer explizit nennen**, auch auf C:.
- Commit-Nachrichten über `git commit -F <datei>`, nicht `-m` mit
  PowerShell-Here-String: eingebettete Anführungszeichen zerlegen sonst die
  Argumentgrenzen und git liest die Nachricht als Pathspecs (10.08.2026).
- Zeilenenden: LF ist Repo-Konvention.

---

## Sprache

Code-Kommentare, Commit-Nachrichten und Dokumentation auf **Deutsch**.
Kommentare erklären das **Warum**, nicht das Was — die Doku dieses Projekts
lebt davon, dass jemand in sechs Monaten die Begründung noch findet.
