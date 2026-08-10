# STATUS — FFPB Performancetool

**Letzte Sitzung:** 10.08.2026 · **Branch:** `verbesserungen` · **Nicht gemergt**

Diese Datei ist der Einstiegspunkt für die nächste Sitzung. Sie beschreibt,
wo wir stehen, was offen ist und wie es weitergeht. Fachliche Tiefe steht in
`PROJEKT_DOKUMENTATION.md` (Transferwissen #1–#44) — hier nur der Zustand.

---

## So starten wir nächste Woche

Diese drei Zeilen im Chat genügen:

> Arbeite im Repo `C:\Entwicklung\Performancetool`.
> Lies zuerst `STATUS.md`, dann `PROJEKT_DOKUMENTATION.md`.
> Hol den aktuellen Stand von GitHub und sag mir, wo wir stehen.

**Was dann automatisch passiert / passieren sollte:**

1. **GitHub-Verbindung steht bereits.** Das Token liegt im Windows-
   Anmeldeinformationsspeicher, `git push`/`pull` laufen ohne Nachfrage.
   Es ist **nichts einzurichten** — kein `gh auth login` nötig (die `gh` CLI
   ist gar nicht installiert und wird für push/pull auch nicht gebraucht).
   Angemeldet als `FFPBAM`, Schreibrechte auf `FFPBAM/Performancetool`.
2. **Stand holen:** `git fetch origin && git status -sb`
3. **Testumgebung:** `.venv` liegt im Projekt und übersteht den Neustart.

### Gearbeitet wird auf C:, nicht auf DRACOON (NEU 10.08.2026)

**Arbeitskopie:** `C:\Entwicklung\Performancetool` (Klon von GitHub, Branch
`verbesserungen`). **Wahrheit ist GitHub.** Das DRACOON-Laufwerk
`H:\Entwicklung\Forschung_Claude\Performancetool` ist nur noch Ablage und
wird **am Sessionende** nachgezogen.

Warum — am 10.08.2026 gemessen:

| | DRACOON (H:) | lokal (C:) |
|---|---|---|
| `pip install -r requirements.txt` | > 20 Min, abgebrochen | ~1 Min |
| Fremddateien im Arbeitsverzeichnis | `__init__.py`, `py.typed` tauchen auf und verschwinden wieder | keine |

Die Geisterdateien sind keine Einbildung: `git status` zeigte sie, Sekunden
später waren sie weg. Genau davor warnt `CLAUDE.md` („DRACOON legt
kurzlebige Dateien an") — deshalb beim Commit **Dateien explizit nennen**,
nie `git add -A`.

**Sessionende — H: nachziehen** (Reihenfolge wichtig, erst pushen):

```
cd C:\Entwicklung\Performancetool
git push origin verbesserungen
cd H:\Entwicklung\Forschung_Claude\Performancetool
git fetch origin && git reset --hard origin/verbesserungen
```

`git reset --hard` auf H: ist unkritisch, **solange dort nicht gearbeitet
wird** — die Kopie soll ja nur spiegeln. Wer doch etwas auf H: geändert hat:
vorher `git status` dort ansehen.

**Falls Git auf H: „dubious ownership" meldet:** einmalig

```
git config --global --add safe.directory '%(prefix)///RCO-MASCHINE/DRACOON/Entwicklung/Forschung_Claude/Performancetool'
```

---

## Wo wir stehen

`main` ist **unverändert** — auf GitHub liegt dort weiterhin `3c3b920`.
Alle Arbeit liegt im Branch `verbesserungen` und wartet auf Philips Review:

**https://github.com/FFPBAM/Performancetool/pull/new/verbesserungen**

### Was im Branch steckt

| Thema | Kern |
|---|---|
| **Benchmark-Bugfix** | Null-Spalte galt als Benchmark → Sharpe −67,48 in der Broschüre. Betraf beide SCHWEIZ-Strategien. |
| **Trennstriche** | Standen an den Vorlagen-Positionen statt an den echten Kategoriegrenzen. 80 Stück über alle Familien. |
| **Historie ab 2009** | cVV-Reihen starten am 30.12.2008 (2 Zeilen Indexbasis) → „seit 2008" war irreführend. Inkl. „Offensiv". |
| **Deploy-Konfiguration** | `streamlit/` → `.streamlit/` (Config wurde nie gelesen), `lxml` in requirements ergänzt. |
| **Doppelte Loader** | `streamlit_app.py` hatte eigene Kopien der `shared.py`-Loader → zwei Caches, Drift-Risiko. |
| **Toter Code** | ~1.900 Zeilen: `performance.py`, `macrobond_upload.py`, `generate_pf_pdf`, Platzhalter-Dateien. |
| **Konfiguration getrennt** | Broschüren-Bauplan in `modules/vorlagen_config.py` (550 Zeilen, importfrei). |
| **Thema-Familie** | Als letzte auf `_folien_config` umgestellt, mit neuem `modus="dupliziert"`. |
| **Tests** | Vier Suiten unter `tests/` — vorher gab es keine. |
| **Legende „Musterdepot"** | *(10.08.)* Der Code schrieb die Vorlagen-Legende auf „Referenzportfolio" um. Zurückgenommen — die Vorlage sagt überall „Musterdepot". Alle 15 Wertentwicklungs-Folien. |
| **Ein Name fürs Tool** | *(10.08.)* Login, Browser-Tab und Kopfzeile trugen drei verschiedene Namen. Jetzt überall „Performance & Portfolioanalyse \| Fürst Fugger Privatbank" aus `shared.APP_TITLE`. |

Netto etwa −1.500 Zeilen bei mehr Funktion.

### Sichtprüfung in echtem PowerPoint — ERLEDIGT

Philip hat am 07.08.2026 **CVV „Defensiv"** und **Thema „Offensiv"** in
echtem PowerPoint geöffnet: Trennstriche und „seit 2009" sitzen korrekt.
Damit sind die beiden Broschüren-Korrekturen dieser Sitzung am Endprodukt
bestätigt, nicht nur im XML.

### Nach dem Merge noch testen (in der App)

1. **Muster SCHWEIZ Aktien** wählen → Kennzahlen zeigen „–" statt 0,00 %
2. **Eine andere Strategie** → muss exakt dieselben Zahlen liefern wie vorher
3. **Toolbar oben rechts** → erstmals schlank (Config wird jetzt gelesen)

---

## Tests

Alle laufen ohne pytest, mit reinem `python`:

| Test | Braucht | Prüft |
|---|---|---|
| `test_app_titel.py` | **nichts** (Schritt 1+2) | Tool heißt überall gleich; Schritt 3 fährt die App per AppTest hoch und braucht streamlit |
| `test_legende_musterdepot.py` | **nichts** (Schritt 1) | Legende sagt „Musterdepot"; Schritt 2+3 brauchen python-pptx und überspringen sonst |
| `test_benchmark_erkennung.py` | pandas | 19 Strategien: 2 ohne Benchmark, 17 unverändert |
| `test_historie_ab.py` | pandas **+ streamlit** | 5 Reihen ab 2009, 14 unberührt, Konfiguration zeigt auf existierende Reihen |
| `test_folien_config.py` | pandas **+ streamlit** | Thema-Config identisch zur handgeschriebenen Fassung, alle 5 Familien passen zu ihrer PPTX |
| `test_export_smoke.py` | **+ python-pptx, streamlit** | erzeugt je Familie eine echte Broschüre |
| `test_trennstriche.py` | **+ python-pptx** | Trennstriche an den Kategoriegrenzen (braucht einen Export-Ordner) |

```
python tests/test_app_titel.py
python tests/test_legende_musterdepot.py
python tests/test_benchmark_erkennung.py
python tests/test_historie_ab.py
python tests/test_folien_config.py
python tests/test_export_smoke.py C:\pfad\zur\ausgabe
python tests/test_trennstriche.py C:\pfad\zur\ausgabe
```

**Korrektur 10.08.2026:** Die Tabelle führte `test_historie_ab` und
`test_folien_config` als „nur pandas". Das stimmt nicht — beide ziehen über
`modules.portfolioanalyse` streamlit herein. `test_historie_ab` überspringt
dann sauber, `test_folien_config` bricht mit `ModuleNotFoundError` ab. Ohne
venv laufen tatsächlich nur `test_benchmark_erkennung` und Schritt 1 von
`test_legende_musterdepot`.

### Testumgebung — steht (10.08.2026)

Die Doku behauptete lange, die Firmen-IT lasse keine Paketinstallationen zu.
**Das stimmt nicht** — `pip` funktioniert.

`C:\Entwicklung\Performancetool\.venv` ist **angelegt und bleibt liegen**
(nicht mehr im Temp-Ordner, übersteht also den Neustart). Installiert:

```
pandas 3.0.5 · numpy 2.5.2 · python-pptx 1.0.2 · streamlit 1.61.0 · pyflakes
```

Genau die pandas/numpy-Kombination aus Transferwissen #20/#21 — der Export
läuft damit sauber durch (7 Broschüren am 10.08. erzeugt).

Neu anlegen, falls doch nötig:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt pyflakes
```

**Auf C: dauert das rund eine Minute, auf H: über zwanzig** (dort am 10.08.
abgebrochen). Ein Grund mehr für die Arbeitskopie auf C:.

`.venv/` steht in `.gitignore`.

---

## Offene Punkte

Vollständige Liste in `PROJEKT_DOKUMENTATION.md` §15. Das Wichtigste:

1. **PR mergen** — alles andere hängt daran.
2. **Flache Benchmark-Linie bei SCHWEIZ** (Backlog A). Die *Kennzahlen* sind
   korrigiert, die *Charts* zeigen weiter eine 0-%-Linie und Null-Balken.
   Sauber wäre, die Serie im Vorlagen-Chart zu entfernen (`pptx_slides`).
   Philip: „lassen wir erstmal" — vor dem nächsten SCHWEIZ-Versand klären.
3. **`pandas`/`numpy` pinnen** (Backlog 1). Genau die beiden verursachten den
   Ausfall am 06.07. Jetzt testbar, weil die venv läuft.
4. **~300 Zeilen Durchreich-Wrapper in `pptx_export.py`** (Backlog C) —
   mechanisch entfernbar, viele Aufrufstellen.
5. **`use_container_width` → `width`** (Backlog 7) — Streamlit warnt und
   entfernt den Parameter künftig.

**Nicht offen, sondern entschieden:** Die Ring-Label-Positionierung bei
kleinen/dicht benachbarten Segmenten wurde am 10.08.2026 vollständig
vermessen und diagnostiziert — Philip: „wir sind am Zenit angekommen",
**keine Änderung**. Die Messung, die Ursachenkette und vier konkrete
Ansatzpunkte für später stehen in `PROJEKT_DOKUMENTATION.md` §44. Wer das
Thema wieder aufmacht, fängt dort an und nicht bei null.

---

## Rahmenbedingungen

- **Repo ist öffentlich.** Bewusste Entscheidung von Philip, damit der
  Cloud-Deploy läuft. Honorarsätze, Benchmark-Zusammensetzungen und die
  Musterdepot-CSVs sind damit einsehbar; Kundendaten sind nicht betroffen,
  `secrets.toml` wurde nie committet. Wer Daten ergänzt, sollte das wissen.
  *(Nebenbei: Streamlit Cloud kann auch private Repos — erweiterter
  OAuth-Scope, freier Tarif erlaubt ~1 private App.)*
- **Daten liegen im Repo und werden von Philip selbst ausgetauscht.**
  `Daten/`, `Daten_PF/`, `Mapping_*.xlsx` nicht anfassen.
- **Nicht im Repo, obwohl die Doku es lange behauptete:**
  `erstelle_broschueren.py` und `modules/dataload.py`. Nie committet.
  §13 bleibt als Bauplan stehen.
- **`modules/portfolio_builder.py` + `Zieldaten/`** bleiben liegen
  (mögliche Reaktivierung), werden nicht importiert.
- **Git-Identität** ist repo-lokal gesetzt: `FFPBAM` /
  `asset-management@fuggerbank.de`.

---

## Arbeitsweise

Bewährt in der letzten Sitzung und bitte beibehalten:

- **Diagnose vor Lösung.** Beide Broschüren-Fehler wurden erst am echten
  Artefakt reproduziert (Chart-XML, Tabellen-Rahmen ausgelesen), dann
  behoben. Nicht raten.
- **Ein Prüfstein je Lieferung.** Jede Korrektur bekam einen Test, der auf
  dem alten Stand rot und danach grün ist — sonst weiß niemand, ob er greift.
- **Beweisen, dass nichts kaputtgeht.** Bei der Konfigurations-Extraktion
  wurden alle sieben Broschüren vorher/nachher rekursiv verglichen (PPTX und
  eingebettete XLSX sind ZIPs); übrig blieb nur der Zeitstempel.
- **Ein Commit je Thema**, deutsche Commit-Nachricht mit Begründung.
- **Was das Auge findet, findet kein Test.** Beide Fehler dieser Sitzung
  kamen aus Philips Sichtprüfung. Broschüren stichprobenartig in *echtem*
  PowerPoint öffnen — LibreOffice reicht nicht (#16/#28).
