# STATUS — FFPB Performancetool

**Letzte Sitzung:** 14.08.2026 · **Branch:** `verbesserungen` · **Nicht gemergt**
· 81 Commits vor `main`

Diese Datei ist der Einstiegspunkt für die nächste Sitzung. Sie beschreibt,
wo wir stehen, was offen ist und wie es weitergeht. Fachliche Tiefe steht in
`PROJEKT_DOKUMENTATION.md` (Transferwissen #1–#50) — hier nur der Zustand.

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

### Audit vom 14.08.2026 — Ergebnis

Philip hat einen Vollaudit über Mathematik, Fachlichkeit und Technik
angefordert; ausdrücklich mit dem Auftrag, die bestehende Umsetzung zu
**widerlegen**, und ohne Codeänderung während der Prüfung.

**Kein Rechenfehler gefunden.** Von sechzehn Widerlegungsversuchen sind
dreizehn an den echten Daten gescheitert:

| Geprüft | Größte Abweichung |
|---|---|
| Monatswert gegen direkte Rechnung (**alle** Monate, **alle** 19 Strategien) | **0,000e+00** |
| Jahresspalte der Differenz gegen ihre Zeile | **0,000e+00** |
| Risikotabelle „Seit Auflage" gegen Kennzahlen-Kachel | **0,000e+00** |
| Ø-Zeile verkettet sich zur Jahresspalte | 1,6e−15 |
| Monatszeile verkettet sich zur Jahresspalte | 4,2e−15 |
| Rollierende Vola gegen Punktschätzung | 3,3e−16 |

Ebenfalls sauber: Bandbreiten-Invarianten und Fenster, Plausibilität aller
19 Strategien (die cVV-Familie ordnet sich monoton in Vola **und** Drawdown),
keine Lücken oder NaN in den Reihen, `secrets.toml` nie committet,
zeitkonstanter Passwortvergleich, 21 von 21 Suiten grün.

**Behoben (2 von 6 Befunden):**

| Befund | Kern | Größenordnung |
|---|---|---|
| **B6** | Fehlender Honorarsatz fiel still auf 0 % — Bruttozahlen als „nach Kosten" beschriftet. Jetzt Vermerk + Fehlermeldung mit Strategienamen. | **1,63 Prozentpunkte** zu hoch |
| **B1** | Begründung für √365 war sachlich falsch (Wochenenden tragen Kuponabgrenzung, keine Nullen). Konvention bleibt — sie ist richtig, nur anders begründet. | reine Doku |

**Von Philip entschieden (14.08.2026):** **B2** — dass Broschüre (ab 2009)
und Oberfläche (ab 31.12.2008) bei den fünf cVV-Reihen um bis zu 1,7 bp
auseinanderliegen, ist **beabsichtigt**. Hintergrund: Die Strategien liefen
schon vor 2008, 2009 ist der Wechsel des Portfoliomanagement-Systems. Das
Tooltip der Kachel sagt es bereits („Erster verfügbarer Datenpunkt der
Strategie im Portfoliomanagement-System"), die Broschüre trägt die Fußnote
zur vollständigen Historie auf Anfrage.

**Ebenfalls behoben (14.08.2026, zweite Runde):**

**B3 — der Honorarabzug traf den eigenen Satz nicht.** Die Tagesbelastung
kam aus `annual_to_daily_rate`, also aus der Aufzins-Formel für eine
**Gutschrift** — abgezogen wurde sie trotzdem. Aufzinsen und Abziehen sind
nicht symmetrisch:

| | Frage | Formel |
|---|---|---|
| Gutschrift (rf) | welcher Tagessatz *wächst* auf 1+r? | `d = (1+r)^(1/365) − 1` |
| Belastung (Honorar) | welcher Tagessatz *zehrt* auf 1−f? | `d = 1 − (1−f)^(1/365)` |

Bei 1,55 % wurden effektiv **1,5264 %** abgezogen statt 1,5500 %. Die
ausgewiesene CAGR sinkt nun um **0,74 bis 2,80 bp** (Median 2,52 bp),
kumuliert bis **120 bp** bei der 17-Jahres-Reihe (Muster offensiv cVV:
184,92 % → 183,72 %). **Die Broschürenzahlen ändern sich dadurch.**

Der eigentliche Fund war der Prüfstein: Sein Kommentar sagte „muss exakt das
Honorar kosten", geprüft wurde ein Band von 1,50 bis 1,56, und die
Fehlermeldung nannte als Soll „~1,53". Die Toleranz war an den gemessenen
Wert angepasst und umschloss genau den Fehler, den sie finden sollte
(Transferwissen #58). Jetzt wird für alle sechs Sätze im Bestand auf 1e−12
genau geprüft.

**B4 — „3 Jahre" ist jetzt an jeder Stelle verortet.** Die Risikotabelle
sagte bereits, dass die Auswahl oben nicht wirkt, nannte aber nicht ihren
eigenen Bezug; die Drawdown-Tabelle sagte gar nichts. Beide tragen jetzt
`zeitraum_hinweis()`: „Gezählt wird taggenau ab dem Datenstand 21.07.2026 —
‚3 Jahre' meint hier 22.07.2023 bis 21.07.2026."

**B5 — die Kostenbasis von TE und IR steht jetzt dabei.** Beide vergleichen
die Strategie nach Kosten mit der Benchmark ohne Kosten (IR −0,464 statt
−0,118). Die Festlegung bleibt — sie ist konsistent mit dem übrigen Werkzeug
und entspricht dem, was der Kunde erlebt —, sie wird nur nicht mehr
verschwiegen. TE und IR erreichen die Broschüre nicht, sie stehen nur im
Werkzeug.

**Nicht verifiziert:** Verhalten unter Python 3.14 in der Cloud, die
erzeugte Broschüre selbst (nur Smoke-Test), das optische Erscheinungsbild im
Browser, die Richtigkeit der Quelldaten aus dem Vorsystem.

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
| **Tests** | **21 Suiten** unter `tests/` plus das Werkzeug `ui_dump.py` — vorher gab es keine einzige. |
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
| **Eine Funktion, ein Ort** | *(12.08.)* Backlog E, F und der Wrapper-Block in einem Zug. Wichtigster Fund: `shared.fmt_date_de` warf bei `pd.NaT` eine **ValueError** — die Oberfläche wäre abgestürzt, wo sie „–" hätte zeigen sollen. Dazu die rf-Umrechnung (vier Stellen) und zehn Durchreicher. |
| **`pyflakes` sauber** | *(12.08.)* Backlog 7a: 16 Meldungen auf 0. Kein Laufzeitfehler darunter — aber die Prüfung wird jetzt wieder gelesen. Zwei Funde mit Substanz: die tote `holeSize`-Kette in beiden Ring-Funktionen und ein `is_bond`, das laut Historie einmal zwei Abfragen steuerte. |
| **Chart-Achsen** | *(12.08.)* Hinweis eines Kollegen: Die ETF-Broschüre zeigt kein 2026, obwohl die Daten bis Juli 2026 laufen. Am Artefakt nachgemessen: **21 Datumsachsen, keine einzige in Ordnung.** Bei der Sichtprüfung kam die Wertachse dazu — auf den cVV-Folien fehlte die **100-%-Linie**. Gleicher Mechanismus, Details unten. |
| **Quelle im Disclaimer** | *(12.08.)* Hinweis von Philip an der Offensiv-Broschüre: Die Quellenangabe wird vom Disclaimer überdruckt. Am PowerPoint-Rendering nachgemessen: **16 von 16** Wertentwicklungs-Folien, alle sechs Vorlagen. Zwei Ursachen, beide behoben. Details unten. |
| **Rumpfjahr im Säulen-Chart** | *(12.08.)* Hinweis von Philip an der Pro-Broschüre: Der Benchmarkvergleich zeigt ein Jahr **2023**, obwohl die Strategie erst seit 01.09.2023 läuft. Nachgemessen: **7 von 19** Strategien zeigten ihr angebrochenes Auflagejahr als vollen Jahresbalken. Details unten. |
| **Anlagekriterien für Thema** | *(12.08.)* Die Excel kannte nur 14 Strategien — weil sie aus den PPTX-Vorlagen abgeleitet wurde und die Thema-Vorlage keinen Kriterien-Kasten hat. Offensiv, Pro und Pro Dividende sind jetzt drin (Werte von der Bank-Webseite) und erscheinen **im Tool**; die Broschüren bleiben byte-identisch. **17 von 19** — SCHWEIZ fehlt noch. |
| **Monatsrenditen-Heatmap** | *(14.08.)* Neu im Tool: jeder Monat der Historie als eingefärbtes Feld, wahlweise als Differenz zur eigenen Benchmark oder zum Vergleichsportfolio. Geometrisch gerechnet, damit die Zeile sich zur Jahresspalte verkettet. Details unten. |
| **Risiko im Überblick** | *(14.08.)* Rollierende Volatilität als Chart plus Volatilität, Sharpe, Tracking Error und Information Ratio je Zeitraum; dazu eine Max-Drawdown-Tabelle am bestehenden Drawdown-Block. Details unten. |

### Heatmap und Risiko-Block: der Aufwand steckte in den ungleichen Historien

Zwei neue Auswertungen im Tool (**nicht** in der Broschüre). In der Sidebar
gibt es dafür eine eigene Gruppe **„Analysen"** mit vier Haken; die
Vergleichsstrategie ist bewusst das **bestehende** Vergleichsportfolio, kein
zweites Auswahlfeld.

Die Darstellung war der kleinere Teil. Drei Dinge waren zu klären:

**1. Angebrochene Monate — #51 eine Ebene feiner.** Jeder Auflagemonat ist
angebrochen, und der laufende ist es bei *jeder* Strategie. Gemessen:
**26 Stück** über alle 19 Reihen. Ohne Prüfung stünde in der Matrix ein
20-Tage-Wert von comdirect als vollwertiger März 2024 — und bei *Muster FFPB
Pro* ein 21-Tage-Wert von **−7,54 %** als Juli 2026.

Behandelt werden sie **unterschiedlich, je nachdem was mit ihnen geschieht**:

| | absolute Matrix | Differenz-Matrix |
|---|---|---|
| angebrochener Monat | steht mit `*` | **entfällt** |
| warum | ist wahr für seine Tage | 20 Tage gegen 31 ist keine Differenz |

Der angenehme Nebeneffekt: Beim Vergleich zweier Strategien fällt der
Zeitraum, in dem die jüngere noch nicht lief, **von selbst** weg.

**2. Der Zuschnitt hätte fünfzehn Jahre gekostet.** Die Blöcke rechnen auf
den **ungeschnittenen** Reihen und schneiden selbst. `df1`/`df2` sind
zweifach beschnitten — auf die Zeitraum-Schnellwahl und, sobald das
Vergleichsportfolio läuft, per Inner-Join auf die gemeinsamen Handelstage.
*Muster ausgewogen cVV* (ab 2009) gegen *Comdirect 100* (ab 2024) hätte so
die gesamte Historie bis 2024 verloren.

*(Am 14.08. nachmittags geändert: Die Heatmap **folgt** jetzt dem gewählten
Zeitraum — siehe „Nachgeschärft" weiter unten. Der Schutz vor der
Schnittmenge bleibt aber genau derselbe.)*

**3. `historie_beschneiden` lag am falschen Ort.** Die Funktion stand in
`portfolioanalyse.py` und griff deshalb **nur im Broschüren-Export**. Ohne
sie stünde in der Heatmap bei den fünf cVV-Strategien eine Zelle **Dez 2008
mit genau einem Tag** — die beiden 2008er-Zeilen sind reine Indexbasis (#43).
Sie ist nach `analytics.py` gewandert. Dieselbe Krankheit wie Backlog B/E/F,
nur bei einer Regel statt bei einer Formel.

**Die Differenz ist geometrisch** (Festlegung Philip). Nur so verkettet sich
die Zeile exakt zur Jahresspalte:

```
Strategie  +10 %  +10 %   ->  +21,00 %
Benchmark   +5 %   +5 %   ->  +10,25 %     Jahr: 1,21/1,1025 - 1 = +9,75 %

geometrisch   1,10/1,05 - 1 = +4,76 % je Monat -> 1,0476² - 1 = +9,75 %  stimmt
arithmetisch  10 - 5        = +5,00 PP je Monat -> Summe = +10,00 PP     passt nicht
```

Nachgemessen an allen 19 Strategien und allen Jahren: Abweichung durchweg
unter 1e-10.

**Der Risiko-Block** bringt die rollierende Volatilität über 365 Tage als
Chart und je Strategie eine Tabelle (YTD/1/3/5/10 Jahre/seit Auflage) mit
Volatilität, Sharpe Ratio, Tracking Error und Information Ratio. Die beiden
Benchmark-Spalten **entfallen ganz** ohne hinterlegte Benchmark, statt eine
Spalte aus lauter „–" zu zeigen. Eine Periode, die weiter zurückreicht als
die Historie, bleibt leer — dort steht bewusst kein gekürzter Wert.

Die rollierende Vola nutzt **dieselbe Formel wie `calc_vola`** (√365, nicht
√252). Der letzte Punkt der Kurve trifft damit die Kennzahlen-Kachel darüber;
ein eigener Testschritt nagelt das fest. Zwei verschiedene Volatilitäten auf
einem Bildschirm wären schlimmer als jede Lehrbuch-Ungenauigkeit.

**Farben.** Rot–neutral–grün, gedämpft, mit festen Grenzen bei ±5 % (absolut)
und ±2,5 % (Differenz) — aus einer Messung über alle 19 Strategien (|Wert|
P95 = 5,28 % bzw. 2,41 %). Fest und nicht datenabhängig, sonst färbte die
Skala zwei Strategien unterschiedlich ein. In jeder Zelle steht die **Zahl**;
`go.Heatmap` kann die Schriftfarbe nicht je Zelle setzen, deshalb wurde der
Kontrast über elf Stützstellen nachgerechnet: schlechtester Wert **5,37:1**,
WCAG AA verlangt 4,5:1.

**Beweise.** Das Rot wurde nachgestellt: Mit der naiven Fassung
(`return not sub.empty`) meldete der Prüfstein bei **allen 19 Strategien**
angebrochene Monate als vollständig. Sieben Broschüren vorher/nachher
verglichen (wegen des Funktions-Umzugs): 2056 ZIP-Einträge, **34
Abweichungen, ausnahmslos Zeitstempel** in `docProps/core.xml` der
eingebetteten Arbeitsmappen — an einem Beispiel nachgewiesen, dass nach
Entfernen von `dcterms:created`/`modified` Zeichengleichheit besteht.
`ui_dump` vorher/nachher: **genau eine** geänderte Zeile, die neue
Sidebar-Überschrift. Alle 21 Suiten grün, `pyflakes` bei null.

### Nachgeschärft nach der Sichtprüfung (14.08. nachmittags)

Philip hat die Heatmap am Bildschirm gesichtet. **Fünf Befunde, keiner davon
durch einen Test auffindbar** — genau dafür ist die Sichtprüfung da.

| Befund | Was daraus wurde |
|---|---|
| „Skala wirkt zu blass" | Grenzen von ±5 % auf **±3 %** (Differenz ±2,5 % → **±1,5 %**), Endfarben etwas satter. Der Hebel lag bei den **Grenzen**, nicht bei den Farben — Details unten. |
| Zeitraum soll greifen | Die Heatmap **folgt jetzt der Schnellwahl** oben. Risiko-Block und Vola-Chart bewusst nicht. |
| „Mrz" → „März" | Dazu ausgeschriebene Monatsnamen in Fließtexten und gestraffte Captions. |
| Farblegende fehlt | Waagerecht unter der Matrix, Enden mit **„≤" und „≥"**. |
| Vergleichs-Option unsichtbar | Der Haken steht jetzt **immer** da, ausgegraut statt versteckt. |

Dazu zwei Ergänzungen: eine **Ø-Zeile je Kalendermonat** und ein Haken
**„Tabelle anzeigen"** unter jeder Matrix.

**Warum die Skala blass wirkte — die Lehre ist methodisch.** Die Grenzen kamen
aus dem 95. Perzentil der Beträge (5,28 %). Saubere Zahl, falsche Frage: Ein
Perzentil am Rand beantwortet „was schneide ich ab?". Über die Wirkung
entscheidet die **Mitte**, und der typische Monat bringt nur **1,2 %**:

| | Grenze aus P95 (±5 %) | Grenze aus dem Median (±3 %) |
|---|---:|---:|
| typischer Monat (1,2 %) | 24 % Sättigung | 40 % |
| guter Monat (2,0 %) | 40 % | 67 % |
| starker Monat (3,0 %) | 60 % | 100 % |

Kräftigere Farben allein hätten es nicht gelöst — die vielen kleinen Monate
wären blass geblieben — und sie kosten Kontrast. Nachgerechnet über 21
Stützstellen: **4,55:1**, knapp über den 4,5:1 der WCAG AA. Signalfarben
lägen bei 3,20:1, und die Zahl in der Zelle ist die eigentliche Aussage.
Rund 15 % der Monate sättigen jetzt aus; deshalb tragen die Enden der
Legende „≤" und „≥".

**Beim Zeitraum lauerte dieselbe Falle wie am Vormittag.** Die Kopplung darf
**nicht** über `sd`/`sd_vor` laufen: Die sind auf `mind` geklemmt, und `mind`
ist bei aktivem Vergleichsportfolio die **Schnittmenge** beider Historien.
Ein naives „folgt dem Zeitraum" hätte *Muster ausgewogen cVV* bei
„Seit Auflage" wieder auf 2024 gestutzt, sobald jemand *Comdirect 100*
danebenstellt. Der Zeitraum wird deshalb eigens abgeleitet; `None` heißt
„Rand der jeweiligen Reihe". Ein AppTest-Schritt nagelt genau diesen Fall
fest.

**Nicht gekoppelt sind Risiko-Block und Vola-Chart**, und das ist keine
Nachlässigkeit: Die Zeilen der Risiko-Tabelle **sind** die Zeiträume — eine
„10 Jahre"-Zeile in einer Drei-Jahres-Auswahl widerspräche sich selbst. Und
der Vola-Chart bräuchte ein Jahr Vorlauf, das es bei „1 Jahr" nicht gäbe.

**Die Ø-Zeile hat eine hübsche Eigenschaft.** Geometrisch gemittelt und
ausschließlich über **vollständige** Kalenderjahre, verkettet sie sich exakt
zu ihrem eigenen Ø-Jahr — dieselbe Zusage wie bei jeder anderen Zeile. Der
Beweis hängt daran, dass für alle zwölf Monate dieselbe Jahresmenge zugrunde
liegt; deshalb die Beschränkung. An *Muster ausgewogen cVV* gemessen: 17
volle Jahre, Verkettung 5,16079 %, Ø-Jahr 5,16079 %, Abweichung 4,4e-16.

**Beweise.** `ui_dump` vorher/nachher **zeichengleich** — die Standardansicht
hat sich nicht um ein Zeichen geändert. Der Broschüren-Pfad ist belegbar
unberührt: Alle geänderten Symbole erreichen ausschließlich
`risiko_ansicht.py`. Alle 21 Suiten grün, `pyflakes` bei null.

*(Zwei eigene Fehler fielen dabei auf, beide in Tests statt im Code: Die
Kennzeilen-Prüfung verglich „bester Monat" gegen einen kleingeschriebenen
String und konnte nie zutreffen; und die Prüfung „kommen die Monatsnamen aus
`strftime`?" fand per Textsuche die **Warnung im Docstring**, die genau davor
warnt. Sie läuft jetzt über den Syntaxbaum.)*

### Zweite Ansicht: die Bandbreite (14.08. abends, spät korrigiert)

Aus Bloomberg mitgebracht (dort „SEAG"). Dieselben Daten, andere Frage:

- **Jahr für Jahr** — *wie lief jeder einzelne Monat der Historie?*
- **Bandbreite** — *ist der laufende März ungewöhnlich, gemessen an allen
  bisherigen Märzen?*

Vier Zeilen statt neunzehn, **zwölf Spalten ohne Jahresspalte**:

```
             Jan   Feb  März   Apr   Mai   Jun    Jul  Aug ... Dez
 5J Hoch    3,41  0,75  2,83  2,19  2,04  4,29   6,72 2,52    2,24
 5J Mittel  0,07 -0,85  0,85 -0,65  0,99  0,94   2,37 -0,08  -0,30
 5J Tief   -5,90 -2,32 -4,01 -4,49 -0,67 -3,14   0,06 -2,74  -3,68
 2026       1,86  0,70 -4,98  5,95  2,71 -0,66  -0,80*

 2026 gegen 5 Jahre · über dem Hoch: April, Mai · unter dem
 Tief: März · 4 von 6 Monaten über dem Mittel
```

**Der erste Anlauf renderte kaputt** — vier Zeilen zu einem Strich
zusammengefallen, Zahlen übereinander. Ursache und Lehre stehen unten unter
„Ein Renderfehler, den kein Test finden konnte".

**Nach Philips Spezifikation gebaut**, und die weicht bewusst von der ersten
Fassung ab:

| | jetzt | erster Anlauf |
|---|---|---|
| Mittelwert | **arithmetisch** (Summe / Anzahl) | geometrisch |
| Spalten | **12** | 13 (mit „Jahr") |
| fehlende Werte | **je Monat tolerant** | nur vollständige Kalenderjahre |
| Fenster | **fest 5 Jahre** | folgte der Zeitraum-Schnellwahl |
| Farbskala | **datengetrieben**, symmetrisch | fest ±3 % |
| Format | **2 Stellen, kein Plus** | 1 Stelle, mit Plus |

Der Zusammenhang ist wichtig: Die erste Fassung war um die **Jahresspalte**
herum gebaut — geometrisch und „nur vollständige Jahre" waren die Bedingung
dafür, dass sich die Zeile zu dieser Spalte verkettet. Die Vorlage hat die
Spalte nicht, also fällt der Grund weg, und die Konvention (Bloomberg,
TradingView) ist ohnehin arithmetisch.

**Zwei Mittelwerte im Werkzeug, und das ist Absicht.** Die Ø-Zeile in „Jahr
für Jahr" rechnet weiter geometrisch — dort gibt es die Jahresspalte, und die
Verkettungs-Zusage gilt unverändert. Der Hover der Mittel-Zeile nennt deshalb
**beide** (arithmetisch 0,85 %, geometrisch 0,82 %). Ein unerklärter
Unterschied wäre schlimmer als eine Zahl mehr im Hover.

**Das laufende Jahr steht nicht in seinem eigenen Band.** Band 2021–2025,
untere Zeile 2026. Nähme man 2022–2026, zöge der laufende Wert sein eigenes
Extrem mit — ein Rekordmonat läge **per Definition nie über dem Hoch**, er
wäre das Hoch (Transferwissen **#53**).

**Wenig Historie wird gerechnet, nicht verweigert.** Bei *Comdirect_100*
stehen nur 2024 und 2025 zur Verfügung; die Zeilen heißen dann ehrlich
`2J Hoch`, und ein Hinweis nennt den Vorbehalt. Jeder Monat rechnet für sich
— fehlt ein einzelner März, fällt nur er weg.

**Die Farbskala richtet sich hier nach den Daten** (symmetrisch bis zum
größten Betrag, aufgerundet, mindestens ±1 %). Bei festen ±3 % wären Hoch-
und Tief-Zeile durchgehend gesättigt gewesen. Preis: Zwischen zwei Strategien
ist die Färbung nicht mehr vergleichbar — eine Caption sagt das.

**Kacheln wachsen bei wenigen Zeilen**, gedeckelt bei 80 px: Bei dreizehn
Spalten auf voller Breite ist eine Spalte rund 75 px breit, die Kachel wird
also annähernd quadratisch statt zum liegenden Balken.

| Zeilen | px/Zeile | gesamt | Fall |
|---:|---:|---:|---|
| 2 | 80 | 310 | Zeitraum „1 Jahr" |
| 4 | 80 | 470 | Bandbreite |
| 11 | 55 | 750 | Zeitraum „10 Jahre" |
| 19 | 32 | 750 | „Seit Auflage" |

### Der Zeitraum schnitt mitten ins Jahr (14.08. nachts)

Philip an der Ansicht „Jahr für Jahr" mit der Schnellwahl **„3 Jahre"**:
Januar bis Juni 2023 fehlen als Kacheln.

Der Zuschnitt rechnete `Datenstand − 3 Jahre` = **21.07.2023**. Jan–Jun 2023
lagen damit außerhalb, Juli 2023 blieb als Elf-Tage-Rumpfmonat stehen —
**sechs leere Kacheln, bei jeder Schnellwahl**, weil der Schnitt immer im
Monat des Datenstands landet.

**Das war ein Fehler, nicht nur unschön.** Eine leere Kachel bedeutet in
dieser Matrix schon etwas: *„die Strategie lief da noch nicht"* (bei
comdirect vor 03/2024). Hier bedeutete dieselbe Kachel *„es gibt Daten, der
Zeitraum blendet sie aus"*. Zwei Bedeutungen, ein Aussehen.

**Behoben** durch Ausrichtung auf ganze Kalenderjahre. Das kostet nichts:

| Auswahl | Zeilen vorher | Zeilen jetzt | leere Kacheln |
|---|---:|---:|---|
| 1 Jahr | 2 | 2 | 6 → 0 |
| 3 Jahre | 4 | 4 | 6 → 0 |
| 5 Jahre | 6 | 6 | 6 → 0 |
| 10 Jahre | 11 | 11 | 6 → 0 |

Ein **eigener Zeitraum wird weiterhin wörtlich** genommen — wer Daten
eintippt, meint genau diese. In Kauf genommen: „3 Jahre" zeigt jetzt
01/2023–07/2026, ein halbes Jahr mehr als die Kennzahlen darüber. Die Caption
sagt es dazu.

**Der eigentliche Befund:** Auf dieser Heatmap lagen zehn Testschritte — und
**keiner konnte diese Zeile anfassen**, weil sie inline im Renderpfad von
`streamlit_app.py` stand. Es gab nichts zu importieren, nichts aufzurufen.
Sie heißt jetzt `zeitraum_fuer_heatmap`, und Schritt 9 prüft sie gegen sieben
gerechnete Fälle plus die Wirkung an allen 19 Strategien. Steht als
Transferwissen **#55** — *wer eine Entscheidung trifft, die man prüfen können
muss, gibt ihr einen Namen.* Die Schwester von #54: dort fehlte die
Layout-Prüfung, hier die Erreichbarkeit.

### Ein Renderfehler, den kein Test finden konnte

Die Bandbreite war am Bildschirm unbrauchbar — **und alle Prüfsteine waren
grün.** Sie lasen `z`, `text` und `y` aus dem Plotly-Figur-Objekt, also die
**Daten**. Die Geometrie entsteht aber erst beim Rendern, aus Voreinstellungen,
die niemand gesetzt hatte:

1. **`yaxis.type` war `None`** — Plotly riet den Achsentyp. Bei
   `["17J-Hoch", "17J-Mittel", "17J-Tief", "2026"]` reicht ein zahlartiges
   Label, um den Achsenbereich bis 2026 zu spannen; vier Kategorien schrumpfen
   dann auf einen Streifen.
2. **Annotationen saßen auf Beschriftungstexten** (`y="2026"`) statt auf
   Koordinaten — eine zweite Namensauflösung, die scheitern kann. Dieselbe
   Klasse wie das fehlende `majorTimeUnit` (#49) und der ins Leere laufende
   Auswahlfeld-Wert (#53).

**Nebenbefund, den erst die Reparatur zutage brachte:** Bei `go.Heatmap` wird
`z[0]` **unten** gezeichnet. Die Zeilenlisten kamen in Leserichtung und wurden
ungedreht übergeben — „Jahr für Jahr" zeigte also **2026 unten und Ø oben**,
verkehrt herum, seit dem ersten Tag. Niemandem aufgefallen, weil 2009–2026
gleichmäßig gestaffelt sind und eine umgedrehte Leiter aus der Ferne wie eine
richtige aussieht.

Der neue **Schritt 8** des Prüfsteins liest ausschließlich das `layout`:
Achsentyp, Kategorienreihenfolge, Spaltenzahl, Koordinatentypen der
Annotationen. Gegen den alten Stand nachgestellt meldet er sofort vier
Abweichungen. Steht als Transferwissen **#54** — *ein Test auf das
Diagramm-Objekt ist kein Test auf das Diagramm.*

Dazu ein Werkzeug, das gefehlt hat: `fig.write_html()` braucht kein Kaleido
und liefert in einer Sekunde eine Datei, die sich im Browser öffnen lässt —
**bevor** die Anwendung startet.

**Beweise.** `ui_dump` vorher/nachher zeichengleich, alle 21 Suiten grün,
`pyflakes` bei null, Broschüren-Pfad unberührt. Die Invariante
`Tief ≤ Mittel ≤ Hoch` über alle 19 Strategien: **null Verletzungen**.

*(Ein weiterer eigener Fehler, am Abend zuvor gefunden: Sechs AppTest-Fälle
setzten `p_sel1` auf **CSV-Namen** statt Anzeigenamen und liefen deshalb zwei
Runden lang gegen `cVV konservativ` — grün, aber blind. Korrigiert; der
AppTest-Helfer prüft seitdem, ob ein gesetzter Wert angekommen ist.)*

### Der Säulen-Chart zeigte vier Monate als Jahresbalken

Philip hat an der **Pro**-Broschüre gesehen, dass im Chart „PERFORMANCE P.A.
(NACH KOSTEN) IM BENCHMARKVERGLEICH" ein Balken **2023** steht. *Muster FFPB
Pro* läuft aber erst seit dem **01.09.2023**: Der Balken zeigte 122 Tage
(+3,23 % gegen +5,11 % Benchmark) und stand als Jahreswert neben 2024
(+27,65 %) und 2025 (+7,58 %).

Das Fenster war richtig — die letzten fünf **abgeschlossenen** Kalenderjahre,
also 2021–2025. Der Fehler saß eine Ebene tiefer: Die Schleife übersprang ein
Jahr nur, wenn es **gar keine** Daten hatte. Ob die Daten das Jahr
**abdecken**, hat niemand geprüft. Betroffen ist damit jede Strategie, deren
Auflage in das Fenster fällt — **7 von 19**:

| Strategie | Auflage | Rumpfbalken | Länge | zeigte |
|---|---|---|---|---|
| Muster FFPB Pro | 01.09.2023 | **2023** | 122 Tage | +3,23 % / +5,11 % |
| Muster FFPB Pro Dividende | 22.10.2024 | 2024 | 71 Tage | −0,97 % / −1,30 % |
| Comdirect 30 / 70 / 100 | 12.03.2024 | 2024 | 295 Tage | z. B. +6,05 % / +4,47 % |
| Muster SCHWEIZ Substanz | 22.09.2022 | 2022 | 101 Tage | −2,19 % (ohne BM) |
| Muster SCHWEIZ Aktien | 12.09.2022 | 2022 | 111 Tage | −4,68 % (ohne BM) |

Die anderen zwölf waren sauber — nicht weil der Code sie richtig behandelte,
sondern weil ihr Rumpfjahr längst aus dem Fenster gerutscht ist. Der Fehler
wäre also von selbst verschwunden und mit jeder neuen Strategie
wiedergekommen.

**Festgelegt (Philip, 12.08.2026), drei Entscheidungen:**

1. Der Rumpfbalken fällt **ganz weg** — nicht umbenannt in „2023 (ab 01.09.)".
   Dass Comdirect und Pro Dividende damit auf **einen** Balken fallen, ist in
   Kauf genommen: ein ehrlicher Balken ist besser als zwei, von denen einer
   eine Jahresrendite behauptet, die es nicht gibt.
2. Das **Tool bleibt unverändert.** Dort wählt der Berater den Zeitraum selbst
   und sieht ihn neben dem Chart; ein Teiljahr trägt Information. In der
   Broschüre steht der Balken allein unter der Überschrift „p.a.". Ein
   Kommentar in `compute_bar_data` hält fest, dass das entschieden ist.
3. Bleibt **kein** volles Jahr übrig (Strategie jünger als ein Kalenderjahr),
   gibt es eine sichtbare Warnung. Bisher wäre dort stillschweigend das
   **Beispiel-Chart der Vorlage** stehengeblieben (2024/2025 mit
   Fantasiewerten). Mit den heutigen 19 Strategien tritt der Fall nicht ein.

**Nachher:**

```
Pro             2024  2025
SCHWEIZ ×2      2023  2024  2025
Comdirect ×3    2025
Pro Dividende   2025
cVV/ESG/ETF     2021 2022 2023 2024 2025   (unverändert)
```

Die Toleranz ist **spiegelbildlich**: Am Jahresende galt „mindestens bis
28.12." schon immer, am Jahresanfang gilt jetzt „spätestens ab 04.01." —
Feiertage verschieben den ersten Kurs genauso wie den letzten.

**Beweis.** Sieben Broschüren vorher/nachher rekursiv verglichen: **2056
ZIP-Einträge, 17 inhaltliche Abweichungen**, ausschließlich Säulen-Chart-XML
und deren eingebettete Arbeitsmappen. cVV, ESG, ETF und Thema (nur Offensiv)
sind **byte-identisch**; in `Thema_x3` sind es genau die Charts von Pro und
Pro Dividende — der Offensiv-Chart daneben ist unverändert, also ein
Kontrollfall in derselben Datei. Der XML-Diff zeigt je Serie **eine Kategorie
und einen Datenpunkt weniger**, sonst nichts: keine Achse, kein Format, keine
Legende, keine Fußnote.

Die Lehre steht als Transferwissen **#51**: *Ein Filter auf „leer" ist kein
Filter auf „vollständig".* Prüfstein `tests/test_kalenderjahre.py` — auf dem
alten Stand rot (9 Abweichungen), danach grün.

**Zwei Nebenbefunde:**

- `pptx_slides.EINZELTITEL_WARNUNGEN` behauptete im Kommentar, von
  `pptx_export` ausgelesen zu werden. Im ganzen Repo gibt es **keine
  Leseposition** — die Liste wächst, und niemand sieht sie. Kommentar
  richtiggestellt; der Kanal, der beim Berater ankommt, ist
  `LAST_BUILD_ERRORS`, und dort steht jetzt auch die neue Meldung.
- `F9_BAR_INCLUDE_CURRENT_YEAR` hängt das **laufende** Jahr an und
  widerspricht der neuen Regel — läuft aber in **keiner** echten Broschüre
  (die Folienrolle `performance` kommt in keiner Familie vor). Bewusst nicht
  geändert, nur an der Konstanten vermerkt.

### Die Datumsachse: gemeldet war eine Achse, betroffen waren alle

Ein Kollege hat gesehen, dass in der **ETF**-Broschüre die Datumsachse kein
2026 zeigt, obwohl die Kurve bis Juli 2026 läuft. Am Artefakt nachgesehen war
es nicht eine Achse, sondern **jede**: sieben gebaute Broschüren, 21
Datumsachsen, **keine in Ordnung**.

Der Grund ist eine Eigenheit von PowerPoint: Die Ticks einer Datumsachse
hängen am **Achsen-Minimum** und laufen von dort in festen Schritten weiter —
Kalendergrenzen spielen keine Rolle. Der Code legte das Minimum auf den
Anfangsmonat der Reihe (gegen den Leerraum vor der Kurve) und verankerte damit
das ganze Raster dort. Die ETF-Reihe beginnt am 30.11.2015, also lagen die
Jahresticks auf November — der letzte auf **Nov/25**.

| Broschüre | vorher | jetzt |
|---|---|---|
| ETF | Nov/15 … **Nov/25** | Jul/15 … **Jul/26** |
| ESG | Sep/20 … **Sep/25** | Jul/20 … Jul/26 (Halbjahr) |
| cVV klassisch | Dez/08 … **Dez/25** | Jul/08 … Jul/26 |
| cVV Dynamic | Okt/18 … **Okt/25** | Jul/18 … Jul/26 |
| cVV Vergleich (F19) | **2 Beschriftungen** | 18, Jan/09 … Jan/26 |
| Thema, dupliziert | **37 bzw. 23** Monatsticks | 13 bzw. 8 |
| SCHWEIZ | **47** Monatsticks | 9 |
| comdirect | keine Anpassung (Element fehlt in der Vorlage) | 11 |

**Zwei Funde, die niemand gemeldet hatte** und die schwerer wogen als der
gemeldete — beide fielen nur auf, weil für den Prüfstein die **Tickfolge**
nachgerechnet wurde statt der Achsengrenzen:

- Der Code zog `majorUnit` nie mit, nur `majorTimeUnit`. Die
  cVV-Vergleichsfolie trägt in der Vorlage `majorUnit=12` mit
  `majorTimeUnit="months"` — nach dem Umstellen auf „years" las PowerPoint
  daraus **zwölf Jahre pro Tick**: zwei Beschriftungen auf siebzehneinhalb
  Jahren Historie.
- In `Vorlage_comdirect.pptx` fehlt `majorTimeUnit` ganz. Wegen
  `if el is not None` lief die Anpassung dort **nie** — ohne Fehler, ohne
  Meldung.

Festgelegt (Philip): Das Format bleibt überall `mmm/yy`, die Vorlagen werden
nicht angefasst — es ändert sich nur, *wo* die Ticks sitzen. Ein kleiner
Vorlauf vor dem Kurvenstart ist in Ordnung (0 bis 5 Monate), ein Achsendatum
in der **Zukunft** nicht.

Die Lehre steht als Transferwissen **#49**: Wenn ein Renderer ein Raster aus
einem Startwert ableitet, entscheidet der Startwert über *alle* Positionen —
und das Ende ist wichtiger als der Anfang. Prüfstein
`tests/test_chartachsen.py`; alle sieben Broschüren vorher/nachher verglichen:
2056 ZIP-Einträge, 55 Abweichungen, ausschließlich die 21 Chart-XML und die
Zeitstempel.

### Die Quellenangabe lag im Disclaimer — und zwar überall

Philip hat an der **Offensiv**-Broschüre gesehen, dass „Quelle: Eigene
Berechnung, Stand 20.07.2026" vom Disclaimer-Fließtext überdruckt wird.
Nachgemessen war es wieder **jede**: In allen sechs Vorlagen liegt die
Textbox `Quelle` auf den Emu identisch **innerhalb** der Disclaimer-Box.

| Shape | Rechteck |
|---|---|
| `Fußnote` (Disclaimer) | 12,50–28,10 × 11,16–16,20 cm |
| `Quelle` | 23,30–28,10 × **13,89–14,19 cm** |

Betroffen: cVV 5 Folien, ESG 4, comdirect 3, ETF 2, Thema 1, FFPB 1 —
zusammen **16**. Alle tragen dieselbe Rolle und laufen durch **eine**
Funktion, deshalb genügte dort eine Korrektur.

**Zwei Ursachen, die sich addieren.** Die Vorlagenposition war immer schon
riskant — sichtbar wurde sie erst, als der Text lang genug wurde, und dafür
sorgte der Code: Der Disclaimer ist in der Vorlage hart umbrochen (längste
Zeile 149 Zeichen bei 6 pt), und eine Ersetzung schrieb dort **189 Zeichen**
hinein. Der Absatz bricht um, alles darunter rutscht eine Zeile tiefer.

Das Ärgerliche: Genau diese Bedingung stand seit Juli 2026 als Kommentar
über der Konstanten — „auf ähnliche Länge kalibriert, damit das Layout
hält". Gemessen hat sie nie jemand. Das ist Transferwissen **#50**: *Eine
Bedingung, die ein Kommentar nennt, ist ein Testfall.*

**Gemessen, nicht geschätzt.** Im XML ist die Kollision unsichtbar —
python-pptx kennt keine Zeilenumbrüche. PowerPoint hat die Folien deshalb
per COM als PNG ausgegeben, vermessen wurde das Rendering:

| | Disclaimer bis | Quelle ab | Ergebnis |
|---|---|---|---|
| vorher | 14,47 cm | 13,89 cm | **überdruckt** |
| nachher | 14,21 cm | 14,80 cm | 0,59 cm Luft |

Behoben sind **beide** Ursachen: Die Quelle-Box rückt beim Befüllen auf
14,75 cm (`WE_QUELLE_TOP_CM`), und der Ersatztext ist auf 145/149 Zeichen
gekürzt. Die Position ist bewusst so gewählt, dass sie **auch mit dem alten
Text** hielte — wer den gekürzten Wortlaut nicht will, nimmt allein diese
eine Konstante zurück.

Prüfstein `tests/test_quelle_position.py`; fünf Broschüren vorher/nachher
verglichen: 1510 ZIP-Einträge, 15 Abweichungen, ausschließlich die 15
Folien-XML — darin genau drei Änderungsarten (15× die Position der
Quelle-Box, 12× die zwei Disclaimer-Absätze). Kein Chart, keine Tabelle,
keine Legende.

### Dieselbe Falle stand senkrecht daneben: die fehlende 100-%-Linie

Bei der Sichtprüfung des Datumsachsen-Fixes fiel Philip auf, dass die
cVV-Folien **keine 100-%-Linie** haben. Ursache identisch: Das Minimum war
datenbasiert (90 %), die Schrittweite kam unverändert aus der Vorlage (20) —
Ticks also bei 90/110/130 %. Die Bezugslinie, auf die sich jede Aussage der
Folie stützt, kam auf der Achse nicht vor. Bei ESG/ETF/comdirect stand sie da,
weil deren Vorlagen zufällig 5 tragen.

Der zweite Teil des Wunsches — „soll auch dort starten" — geht **nicht**:
Jede Strategie war zeitweise unter 100 % (cVV dynamic 85,3 %, ausgewogen
91,4 %, selbst konservativ 99,1 %). Eine Achse ab 100 % hätte diese Drawdowns
abgeschnitten; das wäre ein stiller Datenverlust in einem Kundendokument
(§10.9). Stattdessen liegt 100 % jetzt **immer** auf dem Raster, und die
Achse beginnt auf der Rasterlinie direkt unter dem tiefsten Kurvenpunkt —
also so dicht, wie es ohne Abschneiden geht:

| Chart | vorher | jetzt |
|---|---|---|
| cVV konservativ | 90–160 %, Ticks 90/110/130/150 | **95–155 %, Ticks 95/100/105/…** |
| cVV ausgewogen | 90–230 %, Ticks 90/110/130/… | **80–225 %, Ticks 80/100/120/…** |
| ETF ausgewogen | 90–140 % | 90–135 % |
| comdirect 30 | 95–125 % | 95–120 % |

Die letzten beiden Zeilen sind ein Nebenfund: Die alte Luft-Regel legte, wenn
die Kurve oben an einer Linie klebt, **eine ganze Rasterstufe** drauf — bei
grobem Raster zwanzig leere Prozentpunkte. Jetzt sind es feste fünf.

Der Prüfstein heißt seit dieser Runde `test_chartachsen.py`: Er deckt beide
Achsen ab, und ein Name, der nur die halbe Zusage nennt, führt in sechs
Monaten in die Irre.

### Die drei Funde der Testrunde (Backlog D) — alle aus Grenzfällen

Die neuen Prüfsteine für `analytics` und `formats` haben drei Fehler
aufgedeckt. Bemerkenswert ist, **wo** sie saßen: ausnahmslos in degenerierten
Eingaben, kein einziger in den fachlich interessanten Fällen. (Der 12.08.
brachte noch zwei weitere aus anderen Runden: den `NaT`-Absturz in
`shared.fmt_date_de` und die tote `holeSize`-Kette — siehe Tabelle oben.)

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

### Die Bilanz des Branches (gemessen 14.08.2026 nachts, gegen `main`)

| | Zeilen |
|---|---:|
| Produktivcode (15 Dateien inkl. `risiko_ansicht.py`) | +4.516 / −3.640 → **netto +876** |
| Tests (22 Dateien inkl. `ui_dump.py`, vorher gab es keine) | **+6.490** |
| Dokumentation (8 Dateien) | +3.949 / −87 |

*(Verlauf: 12.08. netto −974, 14.08. vormittags −10, nachmittags +264, abends
+651, spät +814, jetzt +876. Heatmap, Risiko-Block und Bandbreite haben
zusammen rund 1.850 Zeilen gebracht — dem stehen die rund 2.600 gegenüber,
die in den Runden davor weggefallen sind. Jedes Mal gemessen, nicht
geschätzt.)*

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

### Sichtprüfung in echtem PowerPoint — bis auf die Wertachse erledigt

Zweimal geschehen, beide Male von Philip am Endprodukt und nicht nur im XML:

- **07.08.2026** — CVV „Defensiv" und Thema „Offensiv": Trennstriche und
  „seit 2009" sitzen korrekt.
- **12.08.2026** — SCHWEIZ: Säulen-Chart, Legende und Fußnote sitzen. Damit
  ist auch der Benchmark-Fix vom 11.08. am Endprodukt bestätigt — er war der
  heikelste, weil dort eine **falsche Sachaussage** in einem Kundendokument
  stand (die Fußnote nannte die Benchmark einer fremden Strategie).

- **12.08.2026 (abends)** — Datumsachse: Philip hat den Fix am Endprodukt
  gesichtet, die Achsen sitzen. **Dabei kam die Wertachse als neuer Befund
  heraus** (fehlende 100-%-Linie).
- **12.08.2026 (abends, 2)** — **Wertachse und Quellenangabe: beide
  gesichtet, beide in Ordnung** (Philip, an der Offensiv-Broschüre). Damit
  ist die Kette dieses Abends geschlossen: Datumsachse → Wertachse →
  Quelle, jede Korrektur am Endprodukt bestätigt.

- **12.08.2026 (abends, 3)** — **Rumpfjahr im Säulen-Chart: gesichtet und in
  Ordnung.** Philip hat die Broschüren **selbst aus Streamlit exportiert**
  und angesehen: **Pro** zwei Jahresbalken (2024, 2025), **Pro Dividende**
  und die **comdirect-Familie** je ein Jahresbalken (2025). Damit ist nicht
  nur die Korrektur bestätigt, sondern der ganze Weg — Tool → Export →
  Folie, nicht nur die im Test gebauten Dateien.

  **Der Ein-Balken-Fall ist damit entschieden.** Er war die einzige offene
  Frage dieser Runde, weil sie sich nur am Bildschirm beantworten ließ:
  Trägt das Chart ein einziges Balkenpaar? Es trägt. Es braucht also
  **keine** Vorlagenänderung an der Balkenlücke und **keine** beschriftete
  Variante („2024 ab 12.03.") — beide Wege sind hiermit vom Tisch, nicht
  vergessen. Wer den Chart später doch voller haben will, ändert die
  **Vorlage**, nicht die Regel: Ein Balken, der ein Rumpfjahr als
  Jahresrendite ausgibt, bleibt eine falsche Sachaussage (§10.9).

Alle Funde dieses Abends kamen aus dem **Auge**, nicht aus einem Test: erst
ein Kollege, der die Datumsachse mit den Daten verglich, dann Philip an der
frisch korrigierten Broschüre — zweimal hintereinander, denn die Wertachse
und die überdruckte Quellenangabe fielen erst an der jeweils *korrigierten*
Folie auf. Die Methode hat die Fälle danach jedes Mal vervielfacht (21 von
21 Achsen, 16 von 16 Quellenangaben) — aber **gesehen** hat sie niemand am
Bildschirm des Testlaufs. Beides wird gebraucht, und zwar in dieser
Reihenfolge.

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
| `test_anlagekriterien.py` | pandas **+ streamlit** | 17 Strategien, Schreibweise, Banner-Bauweise, AppTest in beiden Ansichten **und für eine Thema-Strategie** (9b); Schritt 4b tastet die Vorlagen ab, damit ein Excel-Eintrag nicht unbemerkt in einer Broschüre landet; **mit Ordner-Argument** zusätzlich der Kasten in den erzeugten Broschüren |
| `test_app_titel.py` | **nichts** (Schritt 1+2) | Tool heißt überall gleich; Schritt 3 fährt die App per AppTest hoch und braucht streamlit |
| `test_legende_musterdepot.py` | **nichts** (Schritt 1) | Legende sagt „Musterdepot"; Schritt 2+3 brauchen python-pptx und überspringen sonst |
| `test_kosten_mathematik.py` | **nichts** (Schritt 1) | Die Honorar-Formel steht nur in `analytics.py`; Schritt 2 prüft die Objekt-Identität in `pptx_export` (braucht pandas + python-pptx), Schritt 3 nagelt die Zahlen fest |
| `test_formats.py` | **nichts** (Schritt 5 nutzt pandas, Schritt 7 streamlit — beide überspringen sauber) | Deutsche Notation, Datum, Disclaimer-Anker — vor allem: ein Fehlwert wird „–" und niemals „nan"/„None"/„NaT"; Schritt 7 hält fest, dass `shared` dieselben Funktionen nutzt |
| `test_analytics.py` | numpy + pandas | Bausteine gegen von Hand nachrechenbare Werte, degenerierte Eingaben liefern `None` statt Absturz, `has_benchmark`, der Vertrag von `compute_performance_data` (Längen, leere Listen) |
| `test_benchmark_erkennung.py` | pandas | 19 Strategien: 2 ohne Benchmark, 17 unverändert (**Kennzahlen**) |
| `test_benchmark_charts.py` | pandas; Schritte 2+3 **+ python-pptx, streamlit** | dasselbe für **Chart, Legende, Fußnote und den Hinweis im Tool** — Schritt 2 baut zwei echte Broschüren und liest nach, Schritt 3 prüft den Hinweis an der gerenderten Oberfläche; „Pro" ist jeweils Kontrollfall |
| `test_honorarsatz.py` | pandas **+ streamlit** | jede Strategie hat einen Satz zwischen 0,5 % und 3 % — fängt das stille Zurückfallen auf 0 % ab; SCHWEIZ auf 1,55 % festgenagelt |
| `test_historie_ab.py` | pandas **+ streamlit** | 5 Reihen ab 2009, 14 unberührt, Konfiguration zeigt auf existierende Reihen |
| `test_folien_config.py` | pandas **+ streamlit** | Thema-Config identisch zur handgeschriebenen Fassung, alle 5 Familien passen zu ihrer PPTX |
| `test_chartachsen.py` | **nichts** (Schritte 1+2); Schritt 3 **+ python-pptx, streamlit** | Beide Achsen der Linien-Charts. Schritt 1 rechnet `achsen_raster` gegen 13 Fälle nach (Datumsachse), Schritt 2 `wert_raster` gegen 15 (Wertachse) — alle von Hand nachgerechnet, inkl. Grenzfälle. Schritt 3 baut je Familie eine Broschüre plus Themen-Duplikation und SCHWEIZ und **rechnet jede Tickfolge nach**: letzter Datums-Tick im Jahr des letzten Datenpunkts, 100 % auf dem Wertachsen-Raster, keine Achse schneidet etwas ab, beide bleiben lesbar |
| `test_quelle_position.py` | pandas **+ python-pptx**; Schritt 3 **+ streamlit** | Die Quellenangabe steht unter dem Disclaimer, nicht darin. Schritt 1 rechnet den Fußnoten-Textblock aller sechs Vorlagen gegen `WE_QUELLE_TOP_CM`, Schritt 2 misst die Länge **jedes** Ersatztextes gegen die Zeilenbreite (der Test, der den Fehler verhindert hätte), Schritt 3 misst 19 Folien in sieben gebauten Broschüren |
| `test_kalenderjahre.py` | **nichts** (Schritte 1+2); Schritt 3 **+ python-pptx, streamlit** | Der Säulen-Chart zeigt nur Kalenderjahre, die die Zeitreihe vollständig abdeckt. Schritt 1 rechnet 15 Grenzfälle nach (beide Toleranzränder, Loch in der Historie, Strategie ohne ein einziges volles Jahr), Schritt 2 misst **jeden** Balken der 19 echten Reihen gegen die Daten, die ihn tragen, und nagelt die 7 bekannten Fälle namentlich fest, Schritt 3 liest die Kategorien aus gebauten Broschüren (Pro, SCHWEIZ, comdirect ×3, Offensiv als Kontrolle) |
| `test_monatsrenditen.py` | **nichts** (Schritte 1–4 nur numpy + pandas); Schritte 5–11 **+ streamlit** | Die Heatmap, elf Schritte. Schritt 1 rechnet `_ist_voller_monat` gegen 13 Grenzfälle nach, Schritt 2 die Verkettung Zeile → Jahresspalte, Schritt 3 die geometrische Differenz gegen das von Hand gerechnete Beispiel (+9,7506 % statt +10,00 PP), Schritt 5 die Ø-Zeile, Schritt 6 misst **jeden** angebrochenen Monat der 19 echten Reihen gegen die Rohdaten und prüft den Zeitraum-Zuschnitt an beiden Rändern, **Schritt 7 die Bandbreite** (arithmetisches Mittel gegen von Hand gerechnete Werte, Je-Monat-Toleranz, festes Fenster, Invariante `Tief ≤ Mittel ≤ Hoch` über alle Strategien), **Schritt 8 die FIGUR statt der Daten** — Achsentyp, Kategorienreihenfolge, Spaltenzahl, Koordinatentypen der Annotationen; das ist die Prüfung, durch deren Fehlen der Renderfehler schlüpfte —, **Schritt 9 die Zeitraum-Ableitung** (sieben gerechnete Fälle plus die Zusage, dass die älteste Jahreszeile keine Lücke hat), Schritt 10 die Kachelhöhe, Schritt 11 fährt die Oberfläche hoch (beide Ansichten, alle Zeiträume, „Seit Auflage mit jungem Vergleichsportfolio") |
| `test_risiko.py` | **nichts** (Schritte 1–2+4); Schritt 3 nutzt zusätzlich die echten CSVs, Schritt 5 **+ streamlit** | Schritt 1 ist der Konsistenz-Beweis: letzter Punkt der rollierenden Vola == `calc_vola` derselben 365 Tage. Schritt 3 prüft, dass nicht abgedeckte Perioden **leer** bleiben statt gekürzt zu rechnen, Schritt 4 Tracking Error und Information Ratio — inklusive des 1e-12-Guards (#47): identische Reihen ergeben TE 0 und IR „–", nicht 1e16 |
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
python tests/test_chartachsen.py [C:\pfad\zur\ausgabe]
python tests/test_quelle_position.py [C:\pfad\zur\ausgabe]
python tests/test_kalenderjahre.py
python tests/test_monatsrenditen.py
python tests/test_risiko.py
python tests/test_export_smoke.py C:\pfad\zur\ausgabe
python tests/test_trennstriche.py C:\pfad\zur\ausgabe
```

**Nachgemessen am 12.08.2026** — nicht geschätzt: Alle **19** Suiten wurden mit
dem System-Python gestartet (hat pandas und numpy, aber **kein** streamlit und
**kein** python-pptx). Ergebnis:

| Verhalten ohne streamlit/pptx | Suiten |
|---|---|
| laufen vollständig durch | `test_analytics`, `test_formats`, `test_kosten_mathematik`, `test_benchmark_erkennung`, `test_streamlit_api`, `test_keine_piktogramme` |
| laufen, überspringen ihre AppTest-/PPTX-Schritte | `test_anlagekriterien`, `test_app_titel`, `test_legende_musterdepot`, `test_benchmark_charts`, `test_chartachsen`, `test_kalenderjahre`, `test_monatsrenditen`, `test_risiko` *(beide neu am 14.08.)* |
| überspringen sich ganz (Rückgabewert 0) | `test_bedienung`, `test_historie_ab`, `test_honorarsatz`, `test_export_smoke`, `test_trennstriche`, `test_folien_config`, `test_quelle_position` |
| **brechen ab** | keine |

Die „Braucht"-Spalte oben nennt also, was ein Test für seinen **vollen**
Umfang braucht — nicht, woran er scheitert. Keine Suite meldet ohne Pakete
einen Fehlschlag.

*(Vorgeschichte: Die Tabelle führte `test_historie_ab` und
`test_folien_config` bis 10.08.2026 als „nur pandas" — falsch, beide ziehen
über `modules.portfolioanalyse` streamlit herein. `test_folien_config` war
bis zum 12.08.2026 zudem der einzige Test, der dann mit
`ModuleNotFoundError` **abbrach** statt zu überspringen; das ist behoben.)*

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

**Es sind drei — alle liegen bei Philip.** Zwei weitere Punkte sind
**bewusst zurückgestellt** und stehen darunter.

1. **Beide Ansichten am Bildschirm gegensehen.** Der Renderfehler ist behoben
   und per Layout-Prüfstein festgenagelt, die Zahlen sind belegt.
   - **„Jahr für Jahr" bitte auf die Reihenfolge ansehen:** 2026 muss jetzt
     **oben** stehen, die Ø-Zeile unten. Vorher war es umgekehrt, ohne dass
     es aufgefallen wäre.
   - Wirkt die datengetriebene Skala der Bandbreite richtig? Sie läuft bis
     zum größten gezeigten Betrag (bei *cVV ausgewogen* ±7 %) und ist
     zwischen Strategien deshalb **nicht** vergleichbar.
   - Sind die Kacheln bei vier Zeilen richtig proportioniert oder zu hoch?
     `ZEILE_HOEHE_MAX` in `risiko_ansicht.py` ist **eine** Konstante.
   - Reichen zwei Nachkommastellen ohne Pluszeichen, oder wirkt die Matrix
     dadurch unruhig?
   - **Light- und Dark-Mode.**
   - Umschalten, mit und ohne Differenz-Matrizen, alle Zeiträume. Die
     Bandbreite darf sich vom Zeitraum **nicht** verändern — das ist Absicht
     und steht als Caption dort.
   - **Schnellwahl durchklicken:** Bei 1 / 3 / 5 / 10 Jahren muss die
     älteste Jahreszeile jetzt **vollständig** sein. Bei „Eigener Zeitraum"
     dagegen bleiben angebrochene Randmonate stehen (mit `*`) — auch das ist
     Absicht.
   - *Comdirect_100* in der Bandbreite: `2J`-Zeilen plus Vorbehalt-Hinweis.
   - „Tabelle anzeigen" bei allen drei Matrizen gleichzeitig.

   ```
   .venv\Scripts\python.exe -m streamlit run streamlit_app.py
   ```

   Vorab ohne App ansehen geht auch — die Figuren lassen sich als HTML
   ausgeben (`fig.write_html`, kein Kaleido nötig).

2. **PR mergen** — alles andere hängt daran.
2. **Deploy-Log nach dem Merge ansehen** (Manage app → schwarze Konsole). Die
   requirements sind jetzt nach oben gedeckelt, geprüft wurde das aber lokal
   unter **Python 3.12** — die Cloud läuft unter **3.14**. Das Log ist die
   einzige Stelle, an der die tatsächlich installierte Kombination sichtbar
   wird. Fünf Minuten, die im Zweifel Stunden sparen (#20).

### Zurückgestellt — nicht vergessen, sondern entschieden (Philip, 12.08.2026)

Beides ist **fachlich offen und technisch beschrieben**; die Umsetzung wartet
auf eine Entscheidung, nicht auf Arbeit. Wer hier weitermacht, fängt bei den
genannten Stellen an und nicht bei null.

- **Anlagekriterien SCHWEIZ** (Backlog G). 17 der 19 Strategien sind in
  `Mapping_Anlagekriterien.xlsx` erfasst; `Schweiz_substanzorientiert` und
  `Schweiz_aktienorientiert` fehlen, weil sie **bewusst nicht auf der
  Webseite stehen** — die Werte müssen aus dem Haus kommen. Gebraucht werden
  vier je Strategie: Anlageregion, Aktienanteil, Anleihenanteil/Liquidität,
  Fremdwährungen. Bis dahin zeigt das Tool dort korrekt keinen Banner; das
  ist **kein Fehlzustand**. Zum Eintragen: Werte in die Excel, dann in
  `tests/test_anlagekriterien.py` die Liste `NOCH_OFFEN` leeren.
- **comdirect-Disclaimer** (Backlog H). Dort steht weiter die alte
  Kostenregel („erfolgt vor Kosten (ab 30.06. …)"), weil der Ersetzungs-Anker
  „Performance Ausweis" heißt und `Vorlage_comdirect.pptx`
  „Performance**-**Ausweis" schreibt — ein Bindestrich. Dieselbe Fußnote sagt
  oben „nach Kosten (taggenauer Honorarabzug)": Sie widerspricht sich selbst,
  und die untere Aussage ist seit Juli 2026 falsch. **Das ist eine
  Sachaussage in einem Kundendokument** (§10.9), keine Kosmetik — deshalb
  steht es hier und nicht unter „nachrangig". Sauberster Weg: den Satz in der
  Vorlage angleichen, dann greifen die vorhandenen Anker. Details in
  `PROJEKT_DOKUMENTATION.md` §15 H.

Im Code ist darüber hinaus nichts offen außer Nachrangigem: internes Hosting
(§15 Punkt 8) und die Alt-Aufgaben aus Phase 2, die vor einer Umsetzung
ohnehin erst mit Philip zu klären sind.

**Neu am 14.08.2026 und ausdrücklich nicht nebenbei erledigt:**
`historie_beschneiden` wird im Performance-Tab **nur** von der Heatmap und
dem Risiko-Block angewandt. Kennzahlen, Linien-Chart und rollierende Tabelle
rechnen bei den fünf cVV-Strategien weiterhin ab dem **31.12.2008**, die
Broschüre ab dem **01.01.2009**. Die Wirkung auf CAGR und Volatilität ist
klein (zwei Tage auf siebzehn Jahre), aber es ist dieselbe Klasse Fund wie
Backlog B/E/F: eine Regel, die nur an einem von zwei Orten greift. Eine
Angleichung **ändert ausgewiesene Zahlen** und gehört deshalb entschieden.

*(Die Sichtprüfungen SCHWEIZ, Datumsachse, Wertachse und Quellenangabe
standen hier bis zum 12.08.2026 als offene Punkte — alle vier sind erledigt,
siehe „Sichtprüfung in echtem PowerPoint".)*

### `pyflakes` ist ab jetzt ein echtes Signal

Über alle **36 Dateien null Meldungen** (Stand 14.08.2026; am 12.08. waren es
33). Wer eine neue erzeugt, sieht sie sofort — vorher ging sie in 16
bekannten unter. Am 14.08. hat die Prüfung prompt geliefert: Nach dem Umzug
von `historie_beschneiden` war `HISTORIE_AB` in `portfolioanalyse.py`
ungenutzt und wurde gemeldet. Aufruf:

```
.venv\Scripts\python.exe -m pyflakes streamlit_app.py modules\*.py tests\*.py
```

In PowerShell expandiert `modules\*.py` **nicht** von selbst; entweder die
Dateiliste vorher aufbauen (`Get-ChildItem`) oder den Aufruf über die Bash
absetzen.

**Erledigt am 14.08.2026:** **Monatsrenditen-Heatmap** (absolut, gegen die
eigene Benchmark, gegen das Vergleichsportfolio) und **Risiko im Überblick**
(rollierende Vola als Chart, Kennzahlen je Zeitraum, Max-Drawdown-Tabelle).
Kam aus keinem Backlog, sondern aus Philips Wunsch. Zwei neue Prüfsteine
`tests/test_monatsrenditen.py` und `tests/test_risiko.py`, Transferwissen
**#52**. Dabei ist `historie_beschneiden` von `portfolioanalyse.py` nach
`analytics.py` gewandert — sie griff bis dahin nur im Broschüren-Export.

**Nachmittags nachgeschärft** nach Philips Sichtprüfung: Skalengrenzen von
±5 % auf ±3 %, Zeitraum-Kopplung, Farblegende, „März" statt „Mrz",
Ø-Zeile je Kalendermonat, Haken „Tabelle anzeigen", Vergleichs-Haken immer
sichtbar. Der vierte Satz von Transferwissen #52 kam daraus.

**Abends die Bandbreiten-Ansicht** nach Bloomberg-Vorbild (Hoch/Mittel/Tief
je Kalendermonat gegen das laufende Jahr), Umschalter zwischen beiden
Ansichten und mitwachsende Kacheln. Transferwissen **#53** — und dabei fiel
auf, dass sechs AppTest-Fälle aus zwei Runden mit CSV-Namen statt
Anzeigenamen liefen und deshalb nichts bewiesen.

**Erledigt am 12.08.2026 (abends, 3):** Der **Rumpfjahr-Balken** im
Säulen-Chart — gemeldet an Pro, gefunden bei 7 von 19 Strategien. Kam aus
keinem Backlog, sondern aus Philips Auge. Neuer Prüfstein
`tests/test_kalenderjahre.py`, Transferwissen **#51**.

**Erledigt am 12.08.2026:** Backlog **B** (Honorar-Mathematik nur noch in
`analytics`), **D** (Prüfsteine für `analytics` und `formats` — die Runde hat
dabei **drei Fehler gefunden**, siehe oben), **E** (rf-Umrechnung stand an
vier statt drei Stellen → `annual_to_daily_rate`), **F** (`fmt_date_de`
zweifach — die UI-Fassung **stürzte bei `NaT` ab**), der **Wrapper-Block
in `streamlit_app.py`** (zehn Durchreicher statt der vermuteten sieben, einer
davon tot, 25 Aufrufstellen) und **7a** (`pyflakes` von 16 Meldungen auf 0).
Dazu die **Anlagekriterien für die Thema-Strategien** (Offensiv, Pro, Pro
Dividende — 17 von 19; die Lehre daraus steht als Transferwissen **#48**).
Außerdem **abgehakt statt abgearbeitet**:
Backlog 3 (Spalte „Währung" — alle 38 CSVs führen sie, gesichtet), Backlog 4
(Familien ESG/CVV/ETF — alle Vorlagen da, alle 19 Strategien zugeordnet,
gesichtet) und Backlog 6 (Download-Toter-Code — war schon am 07.08. entfernt,
stand nur noch fälschlich in der Liste).

**Erledigt am 11.08.2026, war vorher hier gelistet:** Backlog A (SCHWEIZ),
Backlog C (Wrapper in `pptx_export.py`), Backlog 1 (requirements gedeckelt),
Backlog 7 (`use_container_width` → `width` — stand hier noch als offen, war
aber schon migriert; der Parameter kommt nur noch in dem Test vor, der ihn
verbietet).

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
- **Für die Oberfläche gibt es das jetzt auch** *(12.08.2026)*:
  `python tests/ui_dump.py vorher.json` → umbauen →
  `python tests/ui_dump.py nachher.json` → vergleichen. Zieht alle
  Kennzahlen, Captions, Markdown-Blöcke und Tabellen ab. Erfasst die
  Standard-Ansicht, nicht die Bedienpfade — dafür stehen die AppTest-Suiten
  daneben.
- **Ein Commit je Thema**, deutsche Commit-Nachricht mit Begründung.
- **Was das Auge findet, findet kein Test.** Beide Fehler der Sitzung vom
  07.08.2026 kamen aus Philips Sichtprüfung. Broschüren stichprobenartig in
  *echtem* PowerPoint öffnen — LibreOffice reicht nicht (#16/#28).
- **Für Layout-Fragen kann der Test das Auge nachbauen** *(12.08.2026)*:
  PowerPoint gibt eine Folie per COM als PNG aus
  (`$pres.Slides.Item(N).Export(<pfad>.png, "PNG", 1920, 1225)`), und über
  die dunklen Pixelreihen lässt sich zeilenweise messen. So wurde die
  Quelle-Kollision belegt (Disclaimer bis 14,47 cm, Quelle ab 13,89) — im
  XML war sie unsichtbar, weil python-pptx keine Zeilenumbrüche kennt.
- **Umgekehrt gilt es aber auch** *(12.08.2026)*: Die fünf Fehler dieses Tages
  hat **kein Auge** gefunden, sondern durchweg die Methode — Grenzfälle
  durchtesten, Kopien nebeneinanderlegen, `pyflakes` lesen. Beides wird
  gebraucht.
