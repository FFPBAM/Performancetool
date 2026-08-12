# STATUS — FFPB Performancetool

**Letzte Sitzung:** 11.08.2026 · **Branch:** `verbesserungen` · **Nicht gemergt**
· 36 Commits vor `main`

Diese Datei ist der Einstiegspunkt für die nächste Sitzung. Sie beschreibt,
wo wir stehen, was offen ist und wie es weitergeht. Fachliche Tiefe steht in
`PROJEKT_DOKUMENTATION.md` (Transferwissen #1–#45) — hier nur der Zustand.

---

## So starten wir beim nächsten Mal

Diese drei Zeilen im Chat genügen (stehen auch in `Start.txt` zum Kopieren):

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
   Falls sie doch fehlt, steht das Anlegen weiter unten.

**App lokal ansehen** (nicht nötig zum Arbeiten, aber praktisch):

```
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Braucht `.streamlit\secrets.toml` mit einem Testzugang — die Datei ist
gitignored und muss lokal angelegt werden:

```toml
[passwords]
test = "test"
```

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
| **Anlagekriterien** | *(10.08.)* Aus der Vorlage in `Mapping_Anlagekriterien.xlsx` überführt — **eine Quelle für Tool und Broschüre**. Banner in beiden Ansichten, Rückschreiben in die PPTX. 19 Textfehler in Kundenbroschüren bereinigt (u. a. „FPFB Strategie 30"). |
| **Piktogramme raus** | *(10.08.)* 67 Emoji aus Überschriften, Hinweisen und Schaltflächen entfernt — unpassend für eine Privatbank. Zwei davon steuerten Logik und wurden durch Konstanten ersetzt. |
| **Bedienbarkeit, Runde 1** | *(11.08.)* PDF-Ausgabe komplett entfernt (−296 Zeilen, reportlab + matplotlib raus), doppelte Benchmark-Zeile behoben, 33 abgekündigte `use_container_width` migriert. |
| **Bedienbarkeit, Runden 2–4** | *(11.08.)* Kennzahlen-Beschriftungen entklammert, 8 fehlende Hilfetexte ergänzt, Honorarfeld als „netto" benannt, Zeitraum-Schnellwahl (1/3/5/10 J · seit Auflage) mit optionalem eigenem Datum, Seitenleiste gruppiert, Logo auf dem Anmeldebildschirm, Datenstand nach oben. |
| **SCHWEIZ ohne Benchmark** | *(11.08.)* Backlog A erledigt — und dabei mehr gefunden als dort stand. Details unten. |
| **Wrapper raus** | *(11.08.)* Backlog C erledigt: 40 Durchreich-Funktionen aus `pptx_export.py`, −292 Zeilen. Broschüren vorher/nachher bewiesen identisch. |
| **Versionen gedeckelt** | *(11.08.)* Backlog 1 erledigt: **jede** Zeile der requirements hat jetzt eine Obergrenze auf die nächste Hauptversion — ein Cloud-Rebuild kann keine neue Hauptversion mehr einschleppen. Bewusst keine `==`-Pins. |
| **Honorar SCHWEIZ** | *(11.08.)* Beide SCHWEIZ-Strategien **fehlten** im Honorar-Mapping und liefen deshalb still mit 0 % Kosten. Jetzt 1,55 % netto. **Ändert die ausgewiesenen Zahlen** — siehe unten. |
| **Hinweis ohne Benchmark** | *(11.08.)* Kleiner Hinweis über den Kennzahlen, wenn eine Strategie keinen Vergleichsmaßstab hat. Ersetzt den alten Hinweis unter dem Chart, der nur bei eingeschaltetem Benchmark-Schalter erschien. |
| **Zurücksetzen im Zeitraum** | *(11.08.)* Knopf neben den Kalenderfeldern, nur bei „Eigener Zeitraum". Vorher klebten die Felder an ihren Werten, sobald man sie einmal angefasst hatte. Dabei ist ein Fehler in der Doku zu #19 aufgeflogen — siehe unten. |
| **Kosten-Mathematik zentral** | *(12.08.)* Backlog B erledigt: `pptx_export.py` rechnete den Honorarabzug mit eigenen Kopien. Formelgleich — und genau das war die Gefahr: Eine Korrektur in `analytics` hätte die **Broschüre nicht erreicht**. Broschüren vorher/nachher byte-identisch bewiesen. |
| **Prüfsteine für die Rechenmodule** | *(12.08.)* Backlog D erledigt: `analytics` und `formats` hatten keine eigenen Tests, obwohl jede Kennzahl jeder Kundenfolie durch sie läuft. **Drei Fehler dabei gefunden** — siehe unten. |

### Die drei Funde vom 12.08.2026 — alle aus Grenzfällen

Die neuen Prüfsteine für `analytics` und `formats` haben drei Fehler
aufgedeckt. Bemerkenswert ist, **wo** sie saßen: ausnahmslos in
degenerierten Eingaben, kein einziger in den fachlich interessanten Fällen.

| Fund | Wirkung | Status |
|---|---|---|
| `calc_sharpe_excess` prüfte `sd == 0` | Bei **konstanten** Renditen lässt numpy eine Reststreuung von 2,3e-19 stehen — der Guard griff nicht, die Sharpe Ratio wurde **8,36 × 10¹⁶** | korrigiert: Schwelle `sd < 1e-12` |
| `fmt_date_de(float('nan'))` | lieferte wörtlich **„nan"**. Eine leere Excel-Zelle kommt als NaN an, nicht als None | korrigiert: „–" |
| Doctest von `calc_period_return` | behauptete `-0.000198`; richtig ist `-0.000302` (1,01 × 1,01 × 0,98 = 0,999698) | Doku korrigiert, **der Code war richtig** |

Nur die ersten beiden ändern Verhalten, und beide nur dort, wo bisher Unsinn
herauskam. Alle sieben Broschüren wurden gegen den Ausgangsstand des Tages
geprüft: **inhaltlich Byte für Byte identisch**.

Die Lehre steht als Transferwissen **#47** in der Doku: Ein Guard auf `== 0`
greift bei Fließkomma nicht — es braucht eine fachlich begründete Schwelle.
Und: Wer eine rechnende Funktion testet, ruft sie mit leerer Liste, einem
Element, konstanten Werten, NaN und Null auf.

### Falle beim nächsten Button: `_KEEPALIVE_SPERRE`

Wer einen `st.button(..., key="…")` einbaut, muss den Key in
`_KEEPALIVE_SPERRE` (oben in `streamlit_app.py`) eintragen — sonst stürzt die
Seite ab. Das Keep-Alive re-assigniert alle session_state-Keys; für
Button-Keys ist das verboten. Tückisch: Die Zuweisung selbst wirft nichts,
erst das spätere `st.button()` — der Traceback zeigt also auf den Button,
nicht auf die Ursache. Das `try/except` im Keep-Alive hilft dagegen **nicht**,
auch wenn die Doku das bis 11.08.2026 behauptet hat (jetzt korrigiert, #19).

### Honorar SCHWEIZ: die Zahlen ändern sich

`Mapping_Honorarsatz.xlsx` hatte 17 Zeilen bei 19 Strategien — die beiden
SCHWEIZ-Strategien fehlten. Das fiel nicht auf, weil der Loader den Fehlschlag
abfängt und still auf `0.0` zurückfällt (`shared.py`, `except: fd = 0.0`). Die
App zeigte also „nach Kosten"-Zahlen, in denen keine Kosten steckten.

Mit 1,55 % netto (Festlegung Philip) verschieben sich die Werte spürbar:

| Strategie | Kennzahl | vorher (0 %) | jetzt (1,55 %) |
|---|---|---:|---:|
| SCHWEIZ Substanz | Performance p.a. | 6,96 % | **5,33 %** |
| SCHWEIZ Substanz | kumuliert gesamt | 29,43 % | **22,02 %** |
| SCHWEIZ Aktien | Performance p.a. | 9,01 % | **7,35 %** |
| SCHWEIZ Aktien | kumuliert gesamt | 39,52 % | **31,47 %** |

Die neuen Werte sind die richtigen; die alten waren zu hoch, weil das Honorar
fehlte. **Wer eine SCHWEIZ-Broschüre vor dem 11.08.2026 verschickt hat, hat zu
gute Zahlen verschickt.** Prüfstein `tests/test_honorarsatz.py` schlägt künftig
an, sobald eine Strategie ohne Satz dasteht.

Netto etwa −1.800 Zeilen bei mehr Funktion.

### SCHWEIZ: der Vergleichsmaßstab war an drei Stellen noch da

Der Backlog nannte „flache Benchmark-Linie und Null-Balken". Am echten
Artefakt (*Muster SCHWEIZ Substanz*) nachgesehen, stimmte davon die Hälfte —
und es kam etwas Schwereres dazu:

| Stelle | Befund |
|---|---|
| Säulen-Chart | Serie „Benchmark" aus vier Nullen → Null-Balken. **Bestätigt.** |
| Linien-Chart | Zeigte nur *eine* Serie. Die im Backlog vermutete flache 100-%-Linie gab es auf der Themen-Folie **nicht**. |
| Legenden-Box | „Musterdepot     Benchmark***" — benannte einen Balken, den es nicht gibt. |
| Fußnote | „*** 50% EuroStoxx 50; 50% MSCI World Euro" — der **unveränderte Vorlagentext**, also die Benchmark der Strategie *Pro*. |

Die Fußnote wog am schwersten und stand in keinem Backlog: kein optischer
Makel, sondern eine **falsche Sachaussage in einem Kundendokument**.

Ursache überall dieselbe: `analytics` füllte die Benchmark-Serien mit `0.0`
bzw. `1.0` auf, statt sie leer zu lassen — die nachgelagerten Stellen konnten
„es gibt keine" nicht von „sie ist null" unterscheiden. Jetzt liefert
`compute_performance_data` ein `has_benchmark`-Kennzeichen und leere Listen;
Chart-Serie, Legendeneintrag und ***-Zeile entfallen dann.

Der Schalter hat bewusst den Standardwert **True**: nur ein ausdrückliches
`has_benchmark=False` lässt Inhalte verschwinden. Ein fehlender Schlüssel darf
nicht still Text aus einer Broschüre löschen.

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
| `test_bedienung.py` | **+ streamlit** | Zeitraum-Schnellwahl rechnet richtig, PDF-Weg entfernt, Benchmark-Zeile genau einmal, Logo + Datenstand — alles per AppTest am laufenden Programm |
| `test_streamlit_api.py` | **nichts** | keine abgekündigten Streamlit-Parameter (`use_container_width`) |
| `test_keine_piktogramme.py` | **nichts** | keine Emoji in Überschriften, Hinweisen, Schaltflächen (Kommentare/Doku ausgenommen) |
| `test_anlagekriterien.py` | pandas **+ streamlit** | 14 Strategien, Schreibweise, Banner-Bauweise, AppTest in beiden Ansichten; **mit Ordner-Argument** zusätzlich der Kasten in den erzeugten Broschüren |
| `test_app_titel.py` | **nichts** (Schritt 1+2) | Tool heißt überall gleich; Schritt 3 fährt die App per AppTest hoch und braucht streamlit |
| `test_legende_musterdepot.py` | **nichts** (Schritt 1) | Legende sagt „Musterdepot"; Schritt 2+3 brauchen python-pptx und überspringen sonst |
| `test_kosten_mathematik.py` | **nichts** (Schritt 1) | Die Honorar-Formel steht nur in `analytics.py`; Schritt 2 prüft die Objekt-Identität in `pptx_export` (braucht pandas + python-pptx), Schritt 3 nagelt die Zahlen fest |
| `test_formats.py` | **nichts** (Schritt 5 nutzt pandas, wenn da) | Deutsche Notation, Datum, Disclaimer-Anker — vor allem: ein Fehlwert wird „–" und niemals „nan"/„None"/„NaT" |
| `test_analytics.py` | numpy + pandas | Bausteine gegen von Hand nachrechenbare Werte, degenerierte Eingaben liefern `None` statt Absturz, `has_benchmark`, der Vertrag von `compute_performance_data` (Längen, leere Listen) |
| `test_benchmark_erkennung.py` | pandas | 19 Strategien: 2 ohne Benchmark, 17 unverändert (**Kennzahlen**) |
| `test_benchmark_charts.py` | pandas; Schritte 2+3 **+ python-pptx, streamlit** | dasselbe für **Chart, Legende, Fußnote und den Hinweis im Tool** — Schritt 2 baut zwei echte Broschüren und liest nach, Schritt 3 prüft den Hinweis an der gerenderten Oberfläche; „Pro" ist jeweils Kontrollfall |
| `test_honorarsatz.py` | pandas **+ streamlit** | jede Strategie hat einen Satz zwischen 0,5 % und 3 % — fängt das stille Zurückfallen auf 0 % ab; SCHWEIZ auf 1,55 % festgenagelt |
| `test_historie_ab.py` | pandas **+ streamlit** | 5 Reihen ab 2009, 14 unberührt, Konfiguration zeigt auf existierende Reihen |
| `test_folien_config.py` | pandas **+ streamlit** | Thema-Config identisch zur handgeschriebenen Fassung, alle 5 Familien passen zu ihrer PPTX |
| `test_export_smoke.py` | **+ python-pptx, streamlit** | erzeugt je Familie eine echte Broschüre |
| `test_trennstriche.py` | **+ python-pptx** | Trennstriche an den Kategoriegrenzen (braucht einen Export-Ordner) |

```
python tests/test_bedienung.py
python tests/test_streamlit_api.py
python tests/test_keine_piktogramme.py
python tests/test_anlagekriterien.py [C:\pfad\zur\ausgabe]
python tests/test_app_titel.py
python tests/test_legende_musterdepot.py
python tests/test_kosten_mathematik.py
python tests/test_formats.py
python tests/test_analytics.py
python tests/test_benchmark_erkennung.py
python tests/test_benchmark_charts.py
python tests/test_honorarsatz.py
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
2. ~~**SCHWEIZ in echtem PowerPoint ansehen.**~~ — **erledigt 12.08.2026**,
   Philip hat die Broschüre geöffnet: Säulen-Chart, Legende und Fußnote
   sitzen. Damit ist auch der zweite Broschüren-Fix am Endprodukt bestätigt
   und nicht nur im XML.
3. **Deploy-Log nach dem Merge ansehen** (Manage app → schwarze Konsole). Die
   requirements sind jetzt nach oben gedeckelt, geprüft wurde das aber lokal
   unter **Python 3.12** — die Cloud läuft unter **3.14**. Das Log ist die
   einzige Stelle, an der die tatsächlich installierte Kombination sichtbar
   wird. Fünf Minuten, die im Zweifel Stunden sparen (#20).
4. **Wrapper-Block in `streamlit_app.py`** (Zeilen 62–113) — dasselbe Muster
   wie das entfernte in `pptx_export.py`, aber **nicht tot**: die UI ruft ihn
   überall auf, und zwischen den Durchreichern stehen echte UI-Helfer
   (Euro-Drawdown, Calmar, DD-Dauer). Am 12.08.2026 nachgezählt: von sieben
   reinen Durchreichern ist **einer** tot (`annual_fee_to_daily_drag`), die
   übrigen sechs hängen an **21 Aufrufstellen**. Ertrag also ~20 Zeilen gegen
   den Rendering-Pfad der Oberfläche — anders als bei `pptx_export.py`, wo 27
   von 40 Wrappern schlicht niemand aufrief. Wenn, dann die kleine Variante:
   den toten löschen, die sechs anderen durch direkte Importe ersetzen.
5. **`fmt_date_de` existiert zweimal — und stürzt in einer der beiden
   Fassungen ab** (Backlog F, neu 12.08.2026). `formats.py` (Broschüre)
   liefert bei `None`/`NaT`/`nan` sauber „–"; `shared.py:133` (Oberfläche)
   liefert „None" bzw. „nan" — und bei `pd.NaT` eine **ValueError**. Die UI
   ruft die Funktion an rund 15 Stellen auf. Von den offenen Punkten der
   einzige mit Absturzrisiko.
6. **rf-Tagessatz-Umrechnung steht dreifach** (Backlog E, neu 12.08.2026):
   `analytics.py:231`, `streamlit_app.py:144` und `:158`. Dieselbe Bauart wie
   die zusammengeführte Honorar-Mathematik, aber kleinere Wirkung — der rf
   beeinflusst nur die Sharpe Ratio, nicht die ausgewiesene Rendite.

Die Punkte 4–6 sind **dieselbe Krankheit**: eine Funktion, die zweimal
existiert und deren Kopien auseinanderlaufen. Am besten in einem Zug.

**Erledigt am 12.08.2026:** Backlog **B** (Honorar-Mathematik nur noch in
`analytics`, Broschüren byte-identisch bewiesen, neuer Prüfstein
`test_kosten_mathematik.py`) und Backlog **D** (Prüfsteine für `analytics`
und `formats` — die Runde hat dabei **drei Fehler gefunden**, siehe oben).
Außerdem **abgehakt statt abgearbeitet**:
Backlog 3 (Spalte „Währung" — alle 38 CSVs führen sie, gesichtet), Backlog 4
(Familien ESG/CVV/ETF — alle Vorlagen da, alle 19 Strategien zugeordnet,
gesichtet) und Backlog 6 (Download-Toter-Code — war schon am 07.08. entfernt,
stand nur noch fälschlich in der Liste).

**Erledigt am 11.08.2026, war vorher hier gelistet:** Backlog A (SCHWEIZ),
Backlog C (Wrapper in `pptx_export.py`), Backlog 1 (requirements gedeckelt),
Backlog 7 (`use_container_width` → `width` — stand hier noch als offen, war
aber schon migriert; der Parameter kommt nur noch in dem Test vor, der ihn
verbietet). **Damit ist der Backlog bis auf Nachrangiges leer.**

**Nicht offen, sondern entschieden:** Die beiden Ansichten sind
unterschiedlich dicht — 19 Bedienelemente in der Performance-Ansicht gegen 9
in der Portfolioanalyse. Das ist **kein Missstand und braucht keine
Angleichung** (Philip, 11.08.2026): In der Performance gibt es viel zum
Ausprobieren (Zeitraum, Vergleich, Benchmark, Honorar, Darstellung), die
Portfolioanalyse zeigt einen Bestand zum Stichtag. Die Dichte folgt der
Aufgabe.

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
  `Daten/`, `Daten_PF/`, `Mapping_*.xlsx` nicht anfassen — **außer auf
  ausdrückliche Ansage.** Am 11.08.2026 einmal geschehen:
  `Mapping_Honorarsatz.xlsx` um die beiden fehlenden SCHWEIZ-Zeilen ergänzt,
  auf Philips Anweisung. Die Regel gilt weiter; von selbst wird an diesen
  Dateien nichts geändert.
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
