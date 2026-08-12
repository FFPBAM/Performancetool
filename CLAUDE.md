# Arbeitsanweisung für Claude — FFPB Performancetool

**Zuerst lesen:** `STATUS.md` (wo stehen wir), dann `PROJEKT_DOKUMENTATION.md`
(47 Transferwissen-Einträge, Architektur, Compliance).

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
vergleichen, Zeitstempel ignorieren.

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
| `modules/shared.py` | Konstanten, Login, CSV-Loader, `APP_TITLE` (Name des Tools) |
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
python tests/test_formats.py                 # ohne jedes Paket
python tests/test_analytics.py               # nur numpy + pandas
python tests/test_benchmark_erkennung.py     # nur pandas
python tests/test_benchmark_charts.py        # Schritt 1 pandas, 2+3 + pptx/streamlit
python tests/test_honorarsatz.py             # pandas + streamlit
python tests/test_historie_ab.py             # pandas + streamlit
python tests/test_folien_config.py           # pandas + streamlit
python tests/test_export_smoke.py <ordner>   # + python-pptx, streamlit
python tests/test_trennstriche.py <ordner>   # + python-pptx
```

Tests bewusst **ohne pytest** — sie sollen in der eingeschränkten
Firmenumgebung laufen. Neue Tests genauso schreiben.

`pip` funktioniert (entgegen älterer Doku-Aussagen). Für den vollen Export:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Statische Prüfung nicht vergessen:** `py_compile` findet keine
undefinierten Namen. Nach dem Entfernen von Importen oder Funktionen immer
`pyflakes` laufen lassen.

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
