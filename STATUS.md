# STATUS — FFPB Performancetool

**Letzte Sitzung:** 24.08.2026 (nachmittags) · **Branch:**
`verbesserungen` · **Nicht gemergt** · **30 von 30 Suiten grün**,
`pyflakes` bei null · **noch nicht gepusht, Sichtprüfung offen**.

> ### Für Philip: was diese Sitzung geändert hat (24.08.2026, nachmittags)
>
> **Drei Sachen. Die erste ist die wichtigste, und sie ist größer geworden
> als geplant.**
>
> **1. Die Broschüre baut nicht mehr still weiter.** Der zurückgestellte
> Punkt von heute Vormittag ist erledigt — mit einer Korrektur, die ich
> vorher nachgestellt habe. **Der Beweis, im Arbeitsspeicher gebaut:** drei
> comdirect-Strategien, bei der zweiten die Zeitreihe entfernt.
>
> | Lauf | Folie 7 | Folie 9 | Folie 11 | Meldung |
> |---|---|---|---|---|
> | ohne Eingriff | 0,0611 | 0,0861 | 0,0509 | keine ✔ |
> | Zeitreihe entfernt | 0,0611 | **0,0715 / 0,1025** ← Vorlage | 0,0509 | **keine** ✘ |
>
> Genau eine Folie fällt auf die Beispielzahlen der Vorlage zurück, und
> niemand erfährt es. Jetzt schon: Jede der drei Stellen meldet mit Namen,
> Folie und Handlungsanweisung.
>
> **Es waren nämlich drei, nicht eine.** Derselbe stille Zweig stand in
> `_build_we_data`, `_build_perf_data` **und** `_build_rollierend_data`.
> Der dritte trifft die Familie *Thema* — also eine echte Kundenbroschüre.
> Dazu eine vierte Lücke: Fehlte in der Übersichtstabelle **eine** von fünf
> Zeitreihen, behielt genau diese Zeile die Vorlagenwerte, gemeldet wurde
> aber nur, wenn **alle** fehlten.
>
> **Eine Meldung wäre fast eine Fehlmeldung geworden.** Nicht jede Vorlage
> kennt jede Folie: Nur `Vorlage_FFPB` führt die Performance-Folie, nur
> `Vorlage_Thema` die rollierende Tabelle; comdirect, CVV, ESG und ETF
> führen keine von beiden. Meine erste Fassung hätte bei comdirect vor einer
> Folie gewarnt, die es dort gar nicht gibt — und wer zwei Wochen lang eine
> unzutreffende Zeile überliest, überliest bald auch die zutreffende. Die
> Meldung hängt jetzt an der Rolle, die die Vorlage tatsächlich hat:
> comdirect **1**, Standard **2**, Thema **2**.
>
> **Der Prüfstein misst nachweislich etwas** (`tests/test_wertentwicklung_`
> `platzhalter.py`, die 30. Suite). Gegenprobe mit stillgelegter Meldung:
> Schritt 3 **3 Fehler**, Schritt 5 **9 Fehler** — mit der Korrektur beide
> null. Ein Test, der nur grün ist, beweist nichts.
>
> **2. Der Balken erscheint jetzt auch bei nur einem Segment.** Betroffen
> sind **20 Fälle** über die 19 Strategien, fast alle *Edelmetalle* — aber
> nicht nur: auch *ESG offensiv / Renten / Corporates*. Der erklärende Satz
> bleibt und steht jetzt **unter** dem Balken statt an seiner Stelle.
>
> *Nebenbefund:* Der Satz behauptete, der Beitrag des einen Segments sei
> zugleich der Beitrag der ganzen Gattung. Das gilt nur, solange keine
> Position ohne Segment-Angabe dasteht — heute trifft das auf alle 20 Fälle
> zu, zugesichert war es nie. Der Satz nennt den Fall jetzt.
>
> **3. Ein Klick auf ein Segment zeigt seine Einzeltitel** — mit Gewicht,
> Beitrag und Wertpapier-Performance, absteigend nach Beitrag.
> **Die Zahlen lassen sich nachrechnen:** Die Summe der angezeigten Beiträge
> ist exakt der Balken darüber. Über **709 Gattung/Segment-Kombinationen**
> gemessen, größte Abweichung **1,4e−17**. Die Summe wird dabei aus den
> **angezeigten Zeilen** gerechnet und nicht vom Balken abgeschrieben —
> sonst wäre die Zusage per Konstruktion wahr.
>
> *Ohne Klick steht das größte Segment offen* (dein Wunsch) — denselben
> Weg geht der Drilldown im Strategievergleich. *Keine Textbalken:* Die
> hattest du am 18.08. abgeschafft, das bleibt so.
>
> **Die Falle vom 18.08.2026 war eingeplant und ist entschärft.** Ein Chart
> mit `on_select` ist ein Widget; sein Key muss in `_KEEPALIVE_SPERRE`
> stehen, sonst hält die App beim zweiten Rendern an. Beide neuen Keys
> stehen drin, und `tests/test_keepalive.py` bestätigt es. Der Key musste
> dafür **ausgeschrieben** werden statt aus einer f-Zeichenkette zu kommen —
> Einzelheiten unten.
>
> **➜ Was für dich offen bleibt:** die **Sichtprüfung** (der Klick lässt
> sich in keinem Test auslösen — genau das ist die Klasse, die am
> 18.08.2026 die laufende App angehalten hat), danach Push und Merge.
>
> ---
>
> ### Aus der Sitzung davor (24.08.2026, vormittags)
>
> **Vier neue Sachen, einzeln gebaut und einzeln gesichtet.** Der Datenstand
> ist **260824**, 19 von 19 Strategien, alle Reihen bis 24.08.2026.
>
> **1. Portfolioanalyse: Performancebeitrag je Segment.** Hinter dem
> vorhandenen Sidebar-Haken „YTD Performance anzeigen" steht jetzt zusätzlich
> ein waagerechtes Balkendiagramm mit **allen** Segmenten einer Gattung,
> größter Beitrag oben, negative in Terrakotta.
>
> *Gewünscht war Top 5 / Flop 5. Es sind alle geworden* — bei rund elf
> Segmenten, von denen meist ein bis zwei negativ sind, hätte eine
> Flop-Spalte überwiegend **positive** Beiträge enthalten und verschwiegen,
> was sie weglässt (#59). Entschieden mit Philip.
>
> *Die Gattungs-Auswahl davor ist keine Bequemlichkeit:* „Segment" trägt bei
> Aktien Branchen, bei Renten Schuldnerklassen (Festlegung Philip,
> 18.08.2026). An *cVV ausgewogen* gemessen steht „Eisen,Stahl,Rohstoffe"
> unter Aktien bei **−0,159 %**, unter Edelmetallen bei **+0,574 %**; flach
> aggregiert käme **+0,415 %** heraus — eine Zahl, die es in keiner Gattung
> gibt, und mit dem **falschen Vorzeichen**. Genau das ist die Gegenprobe im
> Prüfstein.
>
> **2. Strategievergleich: der X-Achsen-Schalter steht jetzt über der
> Grafik** statt daneben — dieselbe Anordnung wie die Heatmap, die dieselbe
> Aufgabe löst. Dazu eine Caption, die die **Leserichtung** nennt („je weiter
> links, desto ruhiger"); ohne sie muss man raten, ob links besser ist.
>
> **3. Strategievergleich: eigener Zeitraum.** Ein Häkchen neben der
> Schnellwahl blendet Kalenderfelder ein. Die eigentliche Arbeit steckte
> nicht in den Feldern, sondern in einem **stillen Datenverlust**: Schneidet
> man die Reihe aufs Fenster und rechnet „Seit Auflage", liefert auch eine
> Strategie, die erst mitten im Fenster beginnt, brav eine Zahl — nur über
> einen kürzeren Zeitraum, und niemand sähe es. `deckt_zeitraum_ab` fragt das
> an **beiden** Rändern; wer durchfällt, wird namentlich genannt.
> **Die Gegenprobe belegt, dass das keine theoretische Sorge war:** Bei
> Beginn 01.01.2020 fallen 11 Strategien heraus, und die Fassung ohne diese
> Prüfung hätte für **alle 11** eine Zahl geliefert.
>
> **4. Strategievergleich: Nicht-Überschneidung.** Ein Schalter zeigt
> wahlweise „Gemeinsam" oder „Nur im Bezugsdepot" — er wirkt auf Chart *und*
> Aufstellung. **Die Zahl lässt sich am Bildschirm nachrechnen:**
> 70,55 % + 25,30 % = **95,86 %**, das investierte Gewicht von *cVV
> ausgewogen* aus der Portfolioanalyse. Verworfen wurde die Summe der
> Beträge aller Gewichtsunterschiede: Sie hätte für *cVV ausgewogen* gegen
> *Comdirect_100* **148,7 %** ergeben — über 100 neben einem Maß mit Deckel
> 100.
>
> *Achtung bei der Lesart:* Die Überschneidung ist **symmetrisch**, die
> Nicht-Überschneidung **nicht** (25,30 % hin, 24,34 % zurück). Ein Satz
> nennt die Gegenrichtung, damit die Asymmetrie sichtbar ist statt versteckt.
>
> **➜ Was für dich offen bleibt:** die Sichtprüfung an der laufenden
> Cloud-App (#11) und danach der Merge nach `main`.
>
> **Nachtrag am selben Tag:** Die Segment-Balken tragen jetzt die
> **Corporate Colors** — Fuggerblau für positive, Fuggergold für negative
> Beiträge (Entscheidung Philip). Vorher standen dort die Heatmap-Farben;
> die sind im Corporate Design gar nicht definiert. Ein Paar für
> positiv/negativ gibt es dort nicht, gewählt sind deshalb die beiden
> Hauptfarben.
>
> **Nebenbefund, zurückgestellt:** Die Broschüre baut bei fehlender
> Zeitreihe still mit den Zahlen der Vorlage weiter — Einzelheiten unter
> „Offene Punkte".
>
> ---
>
> ### Aus der Sitzung davor (21.08.2026)
>
> **Neu ist eine YTD-Kachel** in der Kennzahlen-Reihe des Performance-Reiters,
> direkt neben „Auflage der Strategie" (dein Feedback, 21.08.2026). Beide
> Reihen stehen jetzt auf **vier** Kacheln statt drei.
>
> **Die Zahl ist nicht neu gerechnet, sondern geliehen.** Die rollierende
> Tabelle im selben Reiter hat seit dem 03.07.2026 eine YTD-Zeile, die ab
> Vorjahres-Schlussstand rechnet und bit-identisch zu Balken-Chart und
> PP-Folie 8 ist (#22). Die Kachel ruft **dieselbe Funktion auf denselben
> Serien** auf — `period_return(sa1t, …)`. Damit können die beiden Anzeigen
> nicht auseinanderlaufen; an 19 von 19 Strategien nachgemessen und
> zeichengleich. Details unter „Die YTD-Kachel" weiter unten,
> Transferwissen **#70**. Neuer Prüfstein: `tests/test_ytd_kachel.py`
> (29. Suite).
>
> **Sichtprüfung bestanden und gepusht** (Philip, 21.08.2026, an der lokal
> laufenden App). Der Branch ist die laufende App — die Kachel ist damit
> live. **Nicht vergessen:** nach dem Push die Cloud-App ansehen (#11).
>
> **➜ Was für dich offen bleibt:** der Merge nach `main` (ändert am Betrieb
> nichts, räumt die Historie) und danach das Deploy-Log. Beides steht in
> `Start.txt` unter „Was offen ist".
>
> ---
>
> ### Aus der Sitzung davor (18.08.2026) — erledigt
>
> **Die Sichtprüfung der beiden Tooltips ist bestanden** (Philip,
> 21.08.2026): *„Sichtprüfung passt. Beide Tooltips passen."* Der offene
> Punkt aus der letzten Sitzung ist damit zu.
>
> **Geändert wurden zwei Sätze** hinter den Fragezeichen der Kennzahlen-Kacheln
> im Performance-Reiter (`display_metrics` in `streamlit_app.py`, zwei Zeilen):
> der Calmar-Hinweis ist ein vollständiger Satz geworden, und der
> Sharpe-Hinweis nennt jetzt den **3-Monats-Euribor** beim Namen. Details im
> Abschnitt „Zwei Hinweistexte im Performance-Reiter" weiter unten,
> Transferwissen **#69**. Neuer Prüfstein:
> `tests/test_kennzahlen_hinweise.py` (28. Suite).
>
> **Gepusht — der Branch ist die laufende App, die Änderung ist also live.**
>
> **Die Sichtprüfung dazu ist erledigt** (Philip, 21.08.2026): Der
> Sharpe-Text war von 232 auf 297 Zeichen gewachsen und die Prüfung bewusst
> übersprungen worden (Michael, 18.08.2026) — nachgeholt und **in Ordnung**.
> Der Fall bleibt trotzdem als Beleg für #60 stehen: übersprungen heißt
> übersprungen und nicht erledigt. Diesmal ging es gut aus.
>
> **DRACOON ist nachgezogen**, am Ende über den dokumentierten Weg
> (`git fetch origin` + `reset --hard origin/verbesserungen`). **Achtung, der
> Pfad ist rechnerabhängig:** Bei Philip ist DRACOON das Netzlaufwerk `H:`;
> auf diesem Rechner hängt der Client die Ablage ins Benutzerprofil
> (`%USERPROFILE%\DRACOON\<ID>\Entwicklung\Forschung_Claude\`
> `Performancetool`). In dieser Sitzung wurde daraus erst fälschlich „DRACOON
> ist nicht erreichbar" geschlossen, weil `H:` hier nicht existiert.
> **Gemessen war das richtig, geschlossen war es falsch** — dieselbe Klasse
> wie #64. Und `reset --hard` scheitert dort beim ersten Versuch **zur
> Hälfte**; der Ablauf weiter unten nennt den Schalter dagegen.
>
> **Die Arbeitskopie auf `C:` war zu Sitzungsbeginn kein Git-Checkout** —
> `.git`, `.gitignore`, `.streamlit/` und `.venv` fehlten. Inhaltlich war sie
> deckungsgleich mit `origin/verbesserungen` (202 Dateien verglichen, 0
> inhaltliche Abweichungen), es fehlte nur die Historie. Wiederhergestellt
> ohne Verlust; `.venv` und `.streamlit/secrets.toml` sind neu angelegt.

> **Der dritte Tab ist live und abgenommen** — Stufe 1 bis 3 plus die
> Nachbesserungen aus dem Gegentest (18.08.2026). Philip an der laufenden
> App: *„Tab läuft wieder, Icons und Dunkelmodus sind in Ordnung."*
>
> *Hier steht bewusst **kein** Commit-Hash mehr: Ein Commit kann seinen
> eigenen nicht enthalten, also wäre die Angabe nach jedem Push einen Stand
> alt — dieselbe Drift, vor der die Kopfzeile weiter oben warnt. Den
> aktuellen Stand liefert `git log --oneline -1 origin/verbesserungen`.*
>
> Damit ist die einzige Frage beantwortet, die kein Testlauf beantworten
> konnte: **Die Font-Falle #1 hat sich nicht verwirklicht.** `theme.font`
> trägt, die Streamlit-Icons bleiben heil, und der CSS-Hack in
> `streamlit_app.py` kann entfallen bleiben. Akzentfarbe und Dunkelmodus
> ebenfalls in Ordnung.
>
> **Aus jeder der drei Sichtprüfungen kam eine Korrektur, die kein Test
> gefunden hatte** — Namen am Punkt, abgeschnittener linker Rand, das rote
> Akzent —, dazu der schwarze Beitragsbalken und der Ausfall vom selben Tag.
> Fünf Funde aus dem Auge, alle bei grünem Testlauf. Das ist kein Zufall
> mehr, sondern die Arbeitsteilung: Die Vorschau vor dem Push bleibt.
>
> **Offen ist nur noch der Merge**, und der wartet auf die Rückmeldung der
> Kollegen (Philip, 18.08.2026).

> ### Achtung: möglicherweise arbeitet jemand parallel am selben Branch
>
> **Hinweis Philip, 18.08.2026:** Ein Kollege will das Streamlit-Thema
> eventuell noch am selben Nachmittag mit einem eigenen Claude-Terminal
> angehen.
>
> Das ist keine Kleinigkeit, weil `verbesserungen` **die laufende App ist**:
> Zwei Terminals, die dieselbe Datei anfassen und pushen, überschreiben sich
> gegenseitig direkt im Betrieb. Vor der Arbeit deshalb **immer**
>
> ```
> git fetch origin && git status -sb
> ```
>
> und bei `behind` erst ziehen. Wer nach einer Pause weiterarbeitet, macht
> das erneut — der eigene Stand kann in der Zwischenzeit alt geworden sein.
> Kommt es doch zu einem Konflikt: **nicht** mit `--force` drüber, sondern
> den fremden Stand ansehen und zusammenführen. Die Historie dieses Branches
> ist die einzige Aufzeichnung darüber, warum das Werkzeug so aussieht, wie
> es aussieht.
>
> Für die nächste Sitzung heißt das:
> `git fetch origin && git log --oneline HEAD..origin/verbesserungen`
> zeigt sofort, ob fremde Commits dazugekommen sind — **ohne dass hier ein
> Hash stehen muss**, der nach jedem Push ohnehin einen Stand alt wäre.

> ### ⚠️ Zuerst lesen: Dieser Branch IST die laufende App
>
> Streamlit Cloud deployt **`verbesserungen`**, nicht `main`. Jeder Push geht
> sofort in das Werkzeug, mit dem die Kollegen arbeiten. Die Doku behauptete
> bis zum 17.08.2026 das Gegenteil (§2 der Projektdokumentation und
> `Start.txt`) — deshalb wurde an dem Tag in dem Glauben gepusht, es sei
> folgenlos, und die App stand. Beide Stellen sind korrigiert.
>
> **Vor dem Push** alle Suiten grün. **Nach dem Push** die App ansehen.
> Stürzt sie mit `ImportError` ab: erst prüfen, ob das Symbol wirklich auf
> dem Server fehlt, dann **Manage app → Reboot app** (die Cloud kann ein
> altes Modul im Speicher behalten), erst dann in die Logs. Beide Fälle
> stehen als Transferwissen **#11**.

*Diese Zeile nennt bewusst den **getesteten** Stand und nicht den jeweils
letzten: Ein Commit kann seinen eigenen Hash nicht enthalten, deshalb war die
Kopfzeile bisher nach jeder Sitzung genau einen Commit alt. Die aktuelle Zahl
liefert `git log --oneline origin/main..origin/verbesserungen`. Wer hier
wieder einen Hash einträgt, handelt sich die Drift erneut ein.*

Diese Datei ist der Einstiegspunkt für die nächste Sitzung. Sie beschreibt,
wo wir stehen, was offen ist und wie es weitergeht. Fachliche Tiefe steht in
`PROJEKT_DOKUMENTATION.md` (Transferwissen #1–#58) — hier nur der Zustand.

> **Das Wichtigste in drei Sätzen.** Am 14.08.2026 lief ein Vollaudit über
> Mathematik, Fachlichkeit und Technik; **kein Rechenfehler** — 13 von 16
> Widerlegungsversuchen scheiterten an den echten Daten, drei Gegenproben
> exakt auf 0,000e+00. Sechs Befunde blieben übrig, **fünf davon sind
> behoben**, einer wurde von Philip als beabsichtigt entschieden.
> **Achtung:** Befund B3 (Honorarformel) verändert die Broschürenzahlen um
> bis zu 120 Basispunkte — alles Weitere unter „Audit vom 14.08.2026".

> **Stand 17.08.2026, vormittags.** Abnahmelauf, **keine Codeänderung**: 21 von
> 21 Suiten grün im vollen Umfang, `pyflakes` bei null, die Nachkosten-Zahlen
> gegen die dokumentierten Sollwerte nachgerechnet (auf zwei Nachkommastellen
> getroffen). Philip hat die beiden neuen Ansichten am Bildschirm gesichtet —
> **in Ordnung**. Sie gingen dann an Kollegen zum Gegentesten.

> **Stand 17.08.2026, nachmittags — die Rückmeldung ist da und eingearbeitet.**
> Drei gemeldete Punkte (englischer Kalender, Einzeltitel-Scrollbalken,
> Fälligkeiten je Anleihe), dazu **zwei Befunde beim Nachmessen**: Anleihen
> ohne feste Fälligkeit fielen still aus dem Chart (bis zu 46,54
> Prozentpunkte), und „Anzahl Titel" stand bei **38 von 38** Dateien um genau
> 1 zu hoch. Alles behoben, vier Commits, neuer Prüfstein — **22 Suiten**.

> **Stand 17.08.2026, abends — der Kalender ist zurückgebaut, alles gesichtet.**
> Die deutsche Datumsauswahl ist wieder draußen: Sie funktionierte, sah aber
> schlechter aus als vorher (aus zwei Bedienelementen wurden sechs, der
> anklickbare Kalender war weg). Philip: *„Es darf auf Englisch sein."*
> `st.date_input` ist zurück, die drei Dateien sind zeichengleich mit dem
> Stand davor. **Die drei anderen Verbesserungen bleiben** — Fälligkeiten,
> Einzeltitel, Titelzahl —, und Philip hat sie am selben Abend an der
> laufenden Cloud-App **abgenommen** („Neues Anleihendetail sieht auch super
> aus. Und man hat die Vollansicht."). Dabei kam der eigentliche Befund des
> Tages heraus: **die Doku nannte einen falschen Deploy-Branch** (siehe Kasten
> oben). **Offen ist damit nur noch der Merge** — er ändert am Betrieb nichts,
> weil die Cloud ohnehin auf `verbesserungen` läuft, räumt aber die Historie.

> **Stand 18.08.2026 — ein dritter Tab: der Strategievergleich.**
> Neu ist eine **Risiko-Rendite-Punktwolke** über alle 19 Strategien:
> Rendite p.a. gegen Volatilität oder Max Drawdown, Farbe nach Familie,
> Auswahl über Familien oder einzeln. Der eigentliche Aufwand lag **nicht**
> in der Darstellung, sondern in einer einzigen fachlichen Frage — dem
> **Zeitraum**. Details unten unter „Der dritte Tab".

---

### Der dritte Tab: der Strategievergleich (18.08.2026)

Die beiden bestehenden Ansichten zeigen **immer eine** Strategie (plus
optional ein Vergleichsportfolio). Die Frage, die im Kundengespräch als
nächstes kommt — *„und wo steht diese Strategie im Vergleich zu unseren
anderen?"* — konnte das Werkzeug nicht beantworten. Jetzt gibt es dafür ein
drittes Segment in der Navigation.

**Gezeigt wird eine Punktwolke:** je Strategie ein Punkt, Y = Rendite p.a.
nach Kosten, X = **Volatilität oder Max Drawdown** (Umschalter wie bei der
Heatmap), Farbe = Familie, Auswahl über Familien-Mehrfachfeld oder einzeln.

**Ausdrücklich keine Effizienzlinie nach Markowitz** (Philip, 18.08.2026).
Die Ansicht *positioniert*, sie *optimiert nicht*. Eine Effizienzlinie
bräuchte eine Kovarianzmatrix und die Annahme, dass man beliebig zwischen den
Strategien mischen kann — und sie suggeriert das dann auch. Ein Kunde bekommt
**eine** Vermögensverwaltung, keinen Mix aus dreien (§10.9).

#### Der ganze Aufwand steckte in einer Frage: dem Zeitraum

Die 19 Strategien haben zwischen **1,7 und 17,6 Jahren** Historie. Eine
Punktwolke „je Strategie seit Auflage" zeigt deshalb nicht, welche besser
ist, sondern **wann sie aufgelegt wurde**: Die alten Reihen tragen
Finanzkrise, Corona und 2022 mit, die jungen nur den Aufschwung seit 2023.
Am 18.08.2026 gemessen:

| Strategie | Historie | CAGR seit Auflage | CAGR letzte 3 J | Rang |
|---|---:|---:|---:|---|
| cVV dynamic | 7,8 J | 7,56 % | 7,42 % | **4 → 14** |
| cVV ausgewogen | 17,6 J | 5,25 % | 9,02 % | **11 → 5** |
| ETF_Wachstum | 10,6 J | 4,15 % | 8,93 % | 15 → 6 |
| Offensiv | 17,6 J | 6,13 % | 7,43 % | 7 → 12 |

Beim **Max Drawdown ist es schärfer**, weil er ein Einzelereignis ist und
nicht mit der Zeit skaliert — ein langer Track Record wird dort *bestraft*:
cVV konservativ zeigt −14,02 % seit Auflage und −3,67 % über drei Jahre.

**Festgelegt (Philip, 18.08.2026):** gemeinsamer Zeitraum. Wer ihn nicht
vollständig abdeckt, wird **nicht gezeichnet**, sondern unter dem Chart
namentlich mit seiner Historienlänge genannt:

> *Nicht gezeigt, weil die Historie den Zeitraum nicht abdeckt: Pro (2,9 J),
> Pro Dividende (1,7 J), Comdirect_30 (2,4 J), Comdirect_70 (2,4 J),
> Comdirect_100 (2,4 J).*

**„Seit Auflage" gibt es hier deshalb nicht.** An seiner Stelle steht der
**längste gemeinsame Zeitraum der Auswahl** — er folgt der jüngsten
gewählten Reihe:

| Auswahl | gemeinsamer Zeitraum |
|---|---:|
| nur die CVV-Familie | 7,8 Jahre *(cVV dynamic ab 10/2018)* |
| CVV + comdirect | 2,4 Jahre |
| alle 19 | **1,7 Jahre** *(Pro Dividende ab 10/2024)* |

Die letzte Zeile ist der Grund, warum die Ansicht mit **„3 Jahre"** startet
und nicht mit dem gemeinsamen Zeitraum: Über 1,7 Jahre lässt sich über Risiko
nichts sagen, und es wäre das Erste, was der Berater sieht. Bei „3 Jahre"
sind es 14 von 19 Strategien, bei „10 Jahre" nur noch 7.

#### Gebaut werden musste weniger, als es aussah

Die Abdeckungsregel **stand schon**: `analytics.risiko_perioden` setzt sie
seit dem 14.08.2026 um (`if start < indexbeginn: continue` — *„Historie deckt
die Periode nicht ab"*), und `test_risiko` Schritt 3 nagelt sie fest. Sie
rechnet auch Volatilität und Max Drawdown je Zeitraum bereits.

**Neu ist genau eine Größe: die Rendite p.a.** Sie kam als Spalte `rendite`
in dieselbe Funktion und in dieselbe Schleife — aus **derselben Indexreihe**
wie der Drawdown, damit die beiden Achsen nicht auf zwei Reihen rechnen
können. Auch der gemeinsame Zeitraum braucht keine zweite Rechnung: Die
Ansicht schneidet die Reihen zu und liest dann `risiko_perioden(...)` mit
„Seit Auflage" — *seit Auflage einer zugeschnittenen Reihe* **ist** der Wert
über das Fenster.

**Beweise.**

| Gemessen | Ergebnis |
|---|---|
| Testsuiten | **23 von 23 grün**, kein Schritt übersprungen |
| `pyflakes` über 41 Dateien | **null** |
| `ui_dump` Performance + Portfolioanalyse vorher/nachher | **zeichengleich** |
| Punktwolke gegen Kennzahlen-Kachel, 19 Strategien × 3 Kennzahlen | größte Abweichung **0,000e+00** |
| dasselbe über das gemeinsame Fenster | **0,000e+00** |
| Broschüren-Pfad | `risiko_perioden` hat **zwei** Verbraucher (`risiko_ansicht`, `strategievergleich`), keiner im Export |

Der Beweis, dass die bestehenden Tabellen die neue Spalte nicht sehen, ist
`ui_dump`: `_perioden_tabelle(reihen, spalten)` wählt ihre Spalten
ausdrücklich aus, und beide Dumps sind zeichengleich.

**Die Gegenprobe zum Prüfstein.** Für eine neue Ansicht gibt es keinen alten
Stand, auf dem ein Test rot wäre. Ersatzweise stellt Schritt 3 die **naive
Fassung** nach — rechnen, was im Fenster liegt, ohne die Abdeckung zu prüfen
— und verlangt, dass sie für alle fünf bekannten Fälle **eine Zahl** liefert.
Täte sie das nicht, prüfte der Schritt nichts.

**Der Anker von Schritt 1** ist derselbe, an dem Audit-Befund B3 hängt: Eine
Reihe ohne Marktbewegung muss **exakt** den Honorarsatz p.a. kosten. Beim
Schreiben ist dabei aufgefallen, dass das für **jede Länge** gilt und nicht
nur für 365 Tage — die Annualisierung hebt die Tageszahl wieder auf
(`((1−d)^n)^(365/n) = (1−d)^365 = 1−f`). Der Test prüft jetzt drei Längen;
dass die Tageszahl selbst stimmt, sichert ein eigener Teilschritt gegen die
geschlossene Form.

**Zwei eigene Fehler, beide durch Messen gefunden statt durch Nachdenken:**
Die Vorbelegung stand zuerst auf dem gemeinsamen Zeitraum — erst der erste
AppTest zeigte, dass das 1,7 Jahre sind. Und die Erwartung im NaN-Grenzfall
war von Hand falsch gerechnet; richtig ist die schönere Invariante oben.

**Die Namen stehen immer am Punkt** (Philip, 18.08.2026). Eine erste Fassung
ließ sie ab 13 Punkten in den Hover wandern, damit sie einander nicht
überdecken — im Kundengespräch wird aber auf den Bildschirm gezeigt und nicht
mit der Maus darüber gefahren. Zurückgebaut; ein Testschritt hält die
Entscheidung fest, damit sie niemand aus Rücksicht auf die Lesbarkeit wieder
einbaut. Zusätzlich `cliponaxis=False`, sonst verliert ausgerechnet der
äußerste Punkt seine Beschriftung.

**Die Überdeckung ist nachgemessen** und kleiner als befürchtet — gezählt
wurden Namenspaare, deren Rechtecke sich bei 760 × 430 px Zeichenfläche
überschneiden:

| Fall | Punkte | kollidierende Paare | betroffene Namen |
|---|---:|---:|---:|
| **3 Jahre** (Vorbelegung) | 14 | **2** | 4 |
| 5 Jahre | 12 | 3 | 5 |
| 1 Jahr (alle 19) | 19 | **6** | 6 |
| 10 Jahre | 7 | 1 | 2 |

Betroffen sind fast immer dieselben: die dicht beieinander liegenden
defensiven Reihen und `Schweiz_substanzorientiert` mit 26 Zeichen. Falls es
am Bildschirm stört, ist der Hebel **kürzere Anzeigenamen**, nicht das
Ausblenden.

**Offen ist die Sichtprüfung** — und zwar bevor gepusht wird (#60). Zu
beurteilen sind vor allem:

- Liest sich der Satz über die ausgelassenen Strategien für einen Berater
  verständlich?
- Ist „Längster gemeinsamer Zeitraum" als Bezeichnung klar?
- Light- und Dark-Mode, beide Achsen, alle Zeiträume.

**Ohne die App ansehen:** Es liegt eine gerenderte HTML-Vorschau mit sechs
Fällen (beide Achsen, mit und ohne Namen, drei Zeiträume) im Scratchpad der
Sitzung — `fig.write_html`, kein Kaleido nötig.

---

### Stufe 2 des Strategievergleichs: Überschneidung und Exposure (18.08.2026)

Der dritte Tab hat zwei Abschnitte dazubekommen — untereinander, die
Strategieauswahl oben gilt für alle drei. Dazu ist der Umschalter der
Punktwolke auf die Bauform der Heatmap umgestellt.

| Abschnitt | Was es beantwortet |
|---|---|
| **Überschneidung** | *„Der Kunde hat schon X — was bringt Y dazu?"* Fokus auf eine Bezugsstrategie, dagegen alle anderen als sortierte Balken |
| **Exposure** | Wie sind die Strategien aufgeteilt — alle nebeneinander statt je Strategie als Ring |

#### Das Maß: Überlappung = Σ min(w_A, w_B)

Die Gegengröße zur *Active Share*, im Gespräch in einem Satz erklärbar:
*„Diese beiden Depots halten zu 69,6 % des Gewichts dieselben Titel."* Eine
reine Titelzahl wäre irreführend — zwei Depots können neun Titel teilen, die
zusammen 3 % wiegen. Gemessen am Stichtag 21.07.2026:

| Paar | Überschneidung | gemeinsame Titel |
|---|---:|---:|
| cVV defensiv plus ↔ cVV ausgewogen | **69,56 %** | 22 |
| Comdirect 70 ↔ Comdirect 100 | 61,4 % | 13 |
| **cVV dynamic ↔ Comdirect 100** | **44,98 %** | 13 |
| cVV ausgewogen ↔ Comdirect 100 | 20,53 % | 5 |

Innerhalb der Familien hoch — erwartbar. Der Wert liegt im Blick **über die
Familien hinweg**; 30 von 171 Paaren haben keinen gemeinsamen Titel.

**Zwei Vorbehalte stehen als Caption in der Ansicht**, weil beide sonst
falsch gelesen würden:

1. **Die Ebenen sind nicht vergleichbar.** Dasselbe Paar (*cVV ausgewogen* ↔
   *Comdirect 100*) liest sich auf Einzeltitel-Ebene als **20,5 %** und auf
   Gattungs-Ebene als **73,8 %** — bei vier Gattungen können sich zwei Depots
   kaum verfehlen. Wer nur die Zahl sieht, hält zwei Depots für fast
   identisch, die auf Titelebene zu einem Fünftel übereinstimmen.
2. **100 % sind unerreichbar.** Die Titelgewichte machen je Strategie nur
   **88,8 bis 98,2 %** aus, der Rest ist Liquidität. Bewusst *nicht*
   wegnormiert: Eine Normierung ließe zwei Depots mit viel Kasse ähnlicher
   aussehen, als sie sind.

#### Exposure: jede Zeile summiert auf 100 %

Gestapelte Balken über **Gattung, Region, Währung** und **Segment innerhalb
einer Gattung**. Die Liquidität ist als eigenes Segment ausgewiesen — ein
Balken, der bei 94 % endet und trotzdem wie ein volles Depot aussieht,
behauptet eine Vollinvestition, die es nicht gibt (#59).

**Segment nur innerhalb einer Gattung** (Entscheidung Philip): Die Spalte
trägt zwei Bedeutungen. „Financials" sind **23 Rentenpositionen**, „Banken,
Versicherer, Finanzdienstl." **42 Aktienpositionen** — flach nebeneinander
sähen sie aus wie zwei Branchen, dabei ist es dasselbe Kreditrisiko in zwei
Formen.

**Region trägt einen Vorbehalt:** Es gibt **kein Look-through** in Fonds und
ETFs. „Europa" sind ausschließlich Fonds, ETFs und Zertifikate, „Europa ohne
Deutschland" ausschließlich Einzeltitel — sachlich richtig, aber der
ausgewiesene Deutschland-Anteil ist dadurch eher zu niedrig. Philip am
18.08.2026 dazu: *„Das haben ETFs an sich."*

**Der Marktrisikowert war gebaut und ist wieder ausgebaut** (Philip,
18.08.2026). Die Spalte liegt in den Daten und ließe sich je Strategie
aufteilen — aber das Haus **legt sie im Asset Management selbst fest**. Eine
vergebene Kennzahl sieht neben gemessenen Größen aus wie eine Beobachtung.
Ein Testschritt hält die Entscheidung fest, weil die Spalte in den Daten
bleibt und sich sonst leicht wieder einbauen ließe.

#### Neues Modul `bestandsanalytik.py` — streamlit-frei

`analytics.py` trägt die Mathematik der **Zeitreihen**, die Tool *und*
Broschüre teilen. Was auf den **Einzeltiteln eines Stichtags** rechnet, hat
jetzt einen eigenen, oberflächenfreien Ort: `ueberlappung`,
`gewichte_je_kategorie`, `kategorien_vereinigt` — und `calc_liquidity`, die
aus `portfolioanalyse.py` dorthin umgezogen ist und dort per Zuweisung
weitergereicht wird. Sie wird inzwischen an drei Stellen gebraucht.

Dort gehören auf Dauer auch `build_allocation`, `get_bond_summary` und
`duration_info_aus_bestand` hin — sie sind heute hinter dem Streamlit-Import
von `portfolioanalyse.py` eingesperrt. Der Umzug war bewusst nicht Teil
dieser Runde.

**`build_allocation` wird bewusst NICHT wiederverwendet.** Sie fasst
Kategorien unter 3 % zu „Sonstige" zusammen — je Strategie einzeln. Für einen
Ring ist das richtig, für einen Vergleich wäre es fatal: Dieselbe Region
stünde bei der einen Strategie als eigener Balken und wäre bei der nächsten
unsichtbar. Dieselbe Lehre wie bei der Farbskala der Heatmap — was verglichen
wird, muss fest sein.

#### Beweise

| Gemessen | Ergebnis |
|---|---|
| Testsuiten | **24 von 24 grün**, kein Schritt übersprungen |
| `pyflakes` über 43 Dateien | **null** |
| `ui_dump` Performance + Portfolioanalyse | **zeichengleich** |
| **Broschüren vorher/nachher, rekursiv** | **7 Stück, 2056 ZIP-Einträge, 0 inhaltliche Abweichungen** |
| Überschneidung gegen die Vormessung | 69,564 / 44,982 / 20,53 % — exakt getroffen |
| Exposure-Zeilensummen | 100 % auf 2,2e−16 |

Der Broschüren-Vergleich war hier **nicht optional**: `calc_liquidity` läuft
im Export-Pfad. Jetzt ist es bewiesen statt argumentiert.

#### Drei Funde beim Bauen, alle aus dem Messen

1. **Eine Zahl in der Planung war erfunden.** Dort stand „cVV ausgewogen ↔
   Comdirect 100: 9 gemeinsame Titel". Es sind **5** — am Rohdatensatz
   gegengerechnet. Der Prozentwert stimmte; die Titelzahl war beim Schreiben
   gefüllt worden, ohne sie zu messen.
2. **Der Fehlwert-Filter funktionierte nur zufällig.** `parse_pf_data` räumt
   „Währung" und „Marktrisikowert" **nicht** auf; bei diesen Spalten hing das
   Aussortieren der leeren Schlusszeile allein daran, dass sie auch kein
   *Gewicht* trägt. Jetzt wird der Fehlwert ausdrücklich zuerst entfernt.
3. **pandas 3.0 wirft NA-Schlüssel beim `groupby` von selbst weg.** Die erste
   Gegenprobe war deshalb gar nicht naiv genug und meldete „greift bei 0 von
   19". Sie braucht `dropna=False` — und das ist selbst ein Befund: Im
   Standardpfad schützt das Werkzeug, nicht der Code. Auf so etwas sollte man
   sich nicht verlassen (#20).

Dazu hat der Prüfstein zwei **gerundete Sollwerte** kassiert (0,696 statt
0,69564). Richtig so: Ein Sollwert, der aus der Anzeige abgeschrieben ist,
trägt eine Unschärfe, die niemand begründen kann (#58).

---

### Stufe 3: ein Theme fürs Haus und der Drilldown (18.08.2026)

Philip hat beim Ansehen zwei Dinge angemerkt, und die erste ging tiefer, als
sie klang.

#### Das Rot war nie eine Entscheidung

Gemeint waren die Auswahl-Chips im Strategievergleich. Die Ursache lag aber
nicht im Tab: **`.streamlit/config.toml` hatte gar keinen `[theme]`-Abschnitt.**
Die App lief damit seit jeher mit Streamlits Standard-Akzentfarbe
**`#FF4B4B`** — einem grellen Korallenrot auf Chips, Kontrollkästchen,
Fokusrahmen, aktiven Segmenten und Links, **in allen drei Ansichten**. In
einem Werkzeug, dessen Palette Fuggerblau und Fuggergold ist, war das nie
beabsichtigt. Es ist nur niemandem als *Entscheidung* aufgefallen — **ein
Standard sieht aus wie eine Festlegung**.

| | vorher | jetzt |
|---|---|---|
| Akzent hell | `#FF4B4B` (Streamlit) | **`#003460`** Fuggerblau |
| Akzent dunkel | `#FF4B4B` | **`#7FABC8`** Hellblau |
| Ecken | Streamlit-Vorgabe | `baseRadius = "small"` |
| Schrift | CSS-Block mit `!important`, nur Hauptbereich | `theme.font`, auch Sidebar |

**Hell und Dunkel bleiben beide.** Streamlit 1.61 kennt getrennte
`[theme.light]`- und `[theme.dark]`-Abschnitte; `base` wird bewusst **nicht**
gesetzt, sonst wäre eine der beiden Fassungen erzwungen.

**Der CSS-Hack ist weg.** Er schrieb Segoe UI per `!important` auf den
Hauptbereich — ausdrücklich nur dort, weil ein globaler Font-Override die
Streamlit-Icons zerstört (#1). `theme.font` ist der dafür vorgesehene Weg,
kennt das Problem nicht und erreicht auch die Sidebar. **Ob die Icons heil
bleiben, kann nur die Sichtprüfung sagen** — geht es schief, kommt der Hack
zurück und nur die Farbe bleibt aus dem Theme.

#### Ein Prüfstein, den es seit #23 hätte geben müssen

Diese Konfiguration ist die einzige Datei des Projekts, deren Fehler sich
**nicht bemerkbar machen**: Wird sie nicht gelesen, sieht die App aus wie eine
App ohne Konfiguration — also normal. Genau so war `toolbarMode` monatelang
wirkungslos, weil der Ordner den Punkt nicht hatte.

`tests/test_theme.py` prüft deshalb nicht den *Inhalt* der Datei, sondern ob
**Streamlit sie wirklich liest**: `config.get_where_defined("theme.primaryColor")`
muss auf `.streamlit/config.toml` zeigen und nicht auf `<default>`. Ein Test
auf den Dateiinhalt hätte den Fehler von 2026 nicht gefunden.

Dazu: die Farben stimmen mit `shared.py` überein (keine handgetippten
Zwillinge), `theme.base` ist nicht gesetzt, hell und dunkel tragen
verschiedene Akzente, es gibt keinen Ordner `streamlit` ohne Punkt, und im
Quelltext steht kein `font-family`-CSS mehr.

#### Der Drilldown: welche Titel sich überschneiden

Ein **Klick auf einen Balken** öffnet die Aufstellung darunter — der Chart ist
damit selbst die Navigation, ohne ein weiteres Auswahlfeld. Ohne Klick steht
die stärkste Überschneidung da; einen leeren Zustand gibt es nicht.

**Die Zusage:** Die Summe der Einzelbeiträge ist **exakt** die Überschneidung
aus der Übersicht. Über **855 Paar-Ebenen-Kombinationen** gemessen, größte
Abweichung **1,1e−16**.

| Wertpapier | Gattung | cVV ausgewogen | cVV defensiv plus | gemeinsam | |
|---|---|---:|---:|---:|---|
| XETRA Gold | Edelmetalle | 7,54 % | 7,64 % | **7,54 %** | ████████████ |
| Bayer IHS 4,625 % 26.05.33 | Renten | 4,08 % | 4,06 % | 4,06 % | ██████ |

**Kein „Top 5"** — die fünf größten tragen nur 33 % der Überschneidung.

**Der Balken ist Text, keine `ProgressColumn`.** Streamlits Spaltenformate
formatieren ihre Zahlen selbst, englisch oder nach der Locale des *Browsers* —
das wäre eine zweite Formatierungsquelle neben `modules/formats.py`, und genau
eine Quelle ist hier Hausregel. Ein Textbalken ist auf jedem Rechner derselbe,
braucht kein CSS und lässt sich auf **Proportionalität prüfen**. Bezugsgröße
ist der größte Beitrag der Tabelle, nicht 1,0 — bei Titelgewichten um vier
Prozent wären sonst alle Balken gleich unsichtbar.

#### Die Designsprache: weniger Elemente, gleiche Aussage

| Heute | Vorher |
|---|---|
| **ein** Hinweisblock unter der Überschneidung | drei einzelne Captions — sie lasen sich wie Kleingedrucktes |
| Achsentitel „gemeinsames Depotgewicht" | ein ganzer Satz an der Achse |
| Balken tragen nur den Prozentwert | zusätzlich die Titelzahl, bei 18 Balken unruhig |
| Honorar-Hinweis im `help` des Zeitraum-Feldes | vierte Caption unter der Punktwolke |
| Drilldown ersetzt „Tabelle anzeigen" | ein Kontrollkästchen für eine zweite Tabelle |

Der Wortlaut der Vorbehalte ist **unverändert** — Philip hat ihn ausdrücklich
als verständlich abgenommen; geändert hat sich nur, wie ruhig er dasteht.

#### Zwei Fallen, die eingeplant waren, und wie sie ausgingen

- **Das Keep-Alive** (#19): Ein Chart mit `key=` und `on_select` legt einen
  Widget-Zustand an, und für Trigger-artige Widgets ist ein Re-Assign
  verboten. **Hier stand, ein AppTest über vier Läufe habe „kein Absturz"
  ergeben, `sv_ue_chart` müsse also nicht in `_KEEPALIVE_SPERRE`.**
  ~~Das war falsch~~ — und der Satz hat die laufende App angehalten. Siehe
  „Der Ausfall vom 18.08.2026" weiter unten.
- **Die Auswahl über den Namen, nicht den Index** (#53): Wechselt die Ebene,
  zeigt derselbe Balkenindex auf eine andere Strategie. Ein Name, den es nicht
  mehr gibt, fällt auf die stärkste Überschneidung zurück. Festgenagelt gegen
  Treffer, Ersatzweg über `customdata`, veralteten Namen und Schrott-Eingaben.

#### Beweise

| Gemessen | Ergebnis |
|---|---|
| Testsuiten | **25 von 25 grün**, kein Schritt übersprungen |
| `pyflakes` über 44 Dateien | **null** |
| Drilldown-Zusage | 855 Kombinationen, größte Abweichung **1,1e−16** |
| `ui_dump` Performance / Portfolioanalyse | **genau eine** Zeile: der entfernte `<style>`-Block. Sonst nichts |
| Export-Pfad | weder `bestandsanalytik` noch `strategievergleich` noch die Theme-Konstanten erreichen ihn |

**Was `ui_dump` hier NICHT beweist:** Es sieht keine Farben und keine
Schriften. Bei einer Designänderung sagt es nur, dass der Text derselbe blieb
— das Aussehen kann allein die Sichtprüfung beurteilen, und zwar **in hell und
dunkel**.

**Die Sichtprüfung hat stattgefunden und ist in Ordnung** (Philip,
18.08.2026): *„Tab läuft wieder, Icons und Dunkelmodus sind in Ordnung."*
Damit ist die riskanteste Annahme dieser Runde bestätigt: **`theme.font`
zerstört die Streamlit-Icons nicht.** Der CSS-Hack aus `streamlit_app.py`
bleibt entfallen — er war seit 07.07.2026 nur deshalb auf den Hauptbereich
beschränkt, und die Einschränkung ist damit gegenstandslos. Auch die
Akzentfarbe wirkt am Bildschirm wie beabsichtigt.

**Was aus dem Auge kam und aus keinem Test:** der schwarze Beitragsbalken im
Drilldown (entfernt, siehe Changelog) — der fünfte solche Fund dieser
Sitzung.

---

### Der Ausfall vom 18.08.2026 — und warum ein grüner Test ihn deckte

Kurz nach dem Push von Stufe 3 stand der Tab Strategievergleich in der Cloud:

```
StreamlitValueAssignmentNotAllowedError
  streamlit_app.py:1129  -> zeige_strategievergleich(...)
  strategievergleich.py  -> st.plotly_chart(key="sv_ue_chart",
                                            on_select="rerun")
```

**Die Ursache war bekannt, benannt und geprüft.** Der Überschneidungs-Chart
wurde durch `on_select="rerun"` vom Bild zum **Widget**; das Keep-Alive
re-assigniert am Skriptanfang alle `session_state`-Keys, und für
Trigger-artige Widgets ist genau das verboten (#19). Der Key gehörte in
`_KEEPALIVE_SPERRE`. Er stand nicht drin.

**Warum nicht:** Die Falle war im Plan als Risiko notiert. Zur Prüfung lief
ein AppTest über vier Läufe samt Ansichtswechsel — er meldete **„kein
Absturz"**, und dieses Ergebnis wurde als Beleg in Commit-Nachricht, STATUS
und Projektdokumentation geschrieben, mitsamt dem Satz, der Key müsse *nicht*
gesperrt werden.

**Nachgestellt: AppTest reproduziert diese Klasse nicht.** Vier Varianten
probiert — Ansicht über `session_state` gesetzt, Navigation bedient, Ansicht
gewechselt und zurück, Bedienelement im Tab angefasst. **Keine** löst den
Fehler aus, der in der Cloud sofort kommt. Der Zustand, den das Keep-Alive
dafür braucht, entsteht in der Testumgebung nicht auf demselben Weg.

**Die Lehre ist nicht „mehr testen", sondern die richtige Art zu testen.**
Ein Verhaltenstest kann diese Regel nicht absichern. Die Regel selbst
dagegen ist statisch prüfbar, und genau das tut jetzt
`tests/test_keepalive.py`: Er liest den **Syntaxbaum** von `streamlit_app.py`
und aller Module, sammelt jedes Widget, dessen Zustand nicht geschrieben
werden darf — Buttons, Download-Buttons, Charts mit `on_select` —, und hält
deren Keys gegen die Sperrliste.

Gegen den Stand, der die App angehalten hat, ist er **rot** und nennt Datei,
Zeile, Widget und Grund:

```
FEHLER — 'sv_ue_chart' fehlt in _KEEPALIVE_SPERRE
         (plotly_chart, modules\strategievergleich.py:843).
         Die App stuerzt beim zweiten Rendern dieses Widgets ab (#19).
```

Er prüft außerdem, dass kein Eintrag der Liste **verwaist** ist (am
11.08.2026 standen dort zwei Keys längst ersetzter Schaltflächen) und dass
kein Trigger-Widget einen **berechneten** Key trägt — ein `key=f"knopf_{x}"`
ließe sich gegen keine Liste halten und wäre dieselbe Falle noch einmal.

**Der eigentliche Fehler war nicht der fehlende Listeneintrag, sondern der
Schluss daraus.** Ein grüner Testlauf belegt, was der Test prüft — nicht,
dass die Falle nicht existiert. Wer ein *Risiko* prüft und nichts findet, hat
zwei mögliche Ergebnisse: Das Risiko besteht nicht, oder der Test erreicht es
nicht. Diese beiden auseinanderzuhalten ist Arbeit, und sie wurde hier nicht
gemacht. Steht als Transferwissen **#64**.

---

### Die Legende überdeckte den Achsentitel (18.08.2026, aus dem Gegentest)

Gemeldet: Im Exposure-Vergleich mit nur zwei Strategien (*Pro*, *Pro
Dividende*) und der Aufteilung **Segment innerhalb Aktien** verschwand die
Achsenbeschriftung „Anteil am Depot" unter der Legende.

**Nachgemessen, vorher und nachher:**

| | Strat. | Segm. | Höhe | unterer Rand | Zeichenfläche | Legende hängt an |
|---|---:|---:|---:|---:|---:|---|
| vorher | 2 | 11 | 220 px | **nicht gesetzt** (80) | 110 px | 13 px unter der Fläche |
| jetzt | 2 | 11 | 292 px | **174 px** | 88 px | am Rand der **Figur** |

**Zwei Ursachen wirkten zusammen:**

1. **`y = −0,12` war relativ zur Zeichenfläche.** Bei 110 px sind das 13 px,
   bei 760 px wären es 91. Der Abstand schrumpfte also genau dann, wenn er am
   meisten gebraucht wurde — bei *wenigen* Strategien.
2. **Die Legende wuchs nach unten, ohne dass jemand Platz reservierte.** Elf
   lange Beschriftungen brauchen vier Zeilen; der Achsentitel saß im selben
   Band.

Dazu ein struktureller Mangel: **`_balkenhoehe` kannte nur die Zahl der
Balken.** Die Zahl der Segmente bestimmt den Platzbedarf mit, ging aber
nirgends ein. Dieselbe Klasse wie der abgeschnittene linke Rand vom Vormittag
(`margin=dict(l=10)`): ein fester Wert gegen eine Automatik.

#### Aus der Schätzung wurde eine Rechnung

Die naheliegende Lösung — „schätze, wie viele Legendeneinträge in eine Zeile
passen" — wäre eine Annahme über Zeichenbreiten und damit genau das, was
`CLAUDE.md` seit dem 17.08. verbietet. Zwei Plotly-Bausteine machen sie
überflüssig:

| Baustein | Wirkung |
|---|---|
| `entrywidthmode="fraction"`, `entrywidth=1/3` | **genau drei** Einträge je Zeile → Zeilenzahl `ceil(n/3)`, exakt |
| `legend.yref="container"`, `y=0` | Legende hängt am Rand der **Figur** → Ursache 1 entfällt |

```
zeilen = ceil(segmente / 3)
unten  = 58 (Achse) + 12 (Abstand) + zeilen × 26 (Legende)
höhe   = 30 (oben) + balken × balkenhöhe + unten
```

Die **12 px Abstand** sind ausdrücklich drin: Ohne sie ginge die Rechnung zwar
auf, aber bei vier Legendenzeilen blieben acht Pixel zwischen Achsentitel und
Legende — und ein Abstand, der sich gerade so ausgeht, ist keiner.

**Die eine verbleibende Pixelannahme wird benannt statt versteckt:** die Höhe
einer Legendenzeile. Sie ist beherrschbar, weil die Schriftgröße der Legende
ausdrücklich gesetzt wird — anders als bei `st.dataframe`, wo die Zeilenhöhe
Streamlit gehört (17.08.2026).

**Feste Höhe je Balken** (Philip): 44 px, mit Deckel nach dem Vorbild der
Heatmap (`_zeilenhoehe`). Zwei Strategien ergeben jetzt ein flaches Bild statt
zweier fetter Klötze; bei 19 greift der Deckel und die Balken schrumpfen auf
36,8 px. Beide Balken-Charts nutzen dieselbe Rechnung — die Überschneidung hat
keine Legende, also `zeilen = 0`.

#### Der Prüfstein hätte sich beinahe selbst übersprungen

**Die Gegenprobe war zuerst wertlos.** Gegen den gemeldeten Stand gehalten,
meldete der neue Schritt 7 **BESTANDEN** — weil die geprüften Funktionen dort
noch nicht existierten, der Import fehlschlug und `except Exception` daraus
ein „ÜBERSPRUNGEN" machte.

Das ist #64 von demselben Tag, eine Ebene tiefer: **Ein Test, der sich beim
Fehlen seines Prüfgegenstands still zurückzieht, ist schlimmer als keiner —
er sieht aus wie ein Beweis.**

Behoben für **alle acht** betroffenen Stellen in zwei Prüfsteinen. Der neue
Helfer `_symbole` unterscheidet sauber:

| Fall | Verhalten | Warum |
|---|---|---|
| ein **Paket** fehlt | überspringen | Hausregel — die Suiten sollen in der eingeschränkten Firmenumgebung laufen |
| ein **Symbol** fehlt | **FEHLER** | das ist ein gebrochener Vertrag, kein Umgebungsproblem |

Gegen den gemeldeten Stand meldet Schritt 7 jetzt namentlich, welche neun
Namen fehlen — und schlägt fehl.

#### Beweise

| Gemessen | Ergebnis |
|---|---|
| Testsuiten | **26 von 26 grün**, kein Schritt übersprungen |
| `pyflakes` über 44 Dateien | **null** |
| `ui_dump` **alle drei** Ansichten | **zeichengleich** — es ändert sich nur Geometrie, kein Text |
| Gegenprobe Schritt 7 | gegen den gemeldeten Stand **rot**, mit Namen der fehlenden Symbole |

---

### Die Bezugsstrategie blieb stehen (18.08.2026, aus dem Gegentest)

Gemeldet: Wer die Strategieauswahl oben stark reduziert — etwa auf *Pro* und
*Pro Dividende* —, sah im Feld **Bezugsstrategie** weiterhin *cVV
konservativ*. Da diese Strategie nicht mehr gewählt war, lieferte die
Überschneidung nichts und der Abschnitt zeigte statt Daten den Satz „Keine
Vergleichsstrategie vorhanden".

**Der Schutz dagegen existierte — und war eine Annahme.** `_waehle_gueltig`
las den Wert aus dem `session_state`, verglich ihn mit den Optionen und
löschte den Schlüssel, wenn er nicht mehr passte. Das setzt voraus, dass ein
gelöschter Schlüssel gelöscht bleibt. **Über Streamlits Widget-Zustand lässt
sich das von außen nicht zusichern.**

**Und AppTest kann es nicht nachstellen.** Drei Bedienwege probiert — über
das Strategien-Feld, über die Familien, mit vorher gesetztem Bezug —, in der
Testumgebung griff der alte Schutz jedes Mal. Dieselbe Feststellung wie beim
Keep-Alive am selben Vormittag (#64): Die Session-State-Semantik von AppTest
weicht von der echten Sitzung ab.

**Daraus folgte: nicht den Schutz nachbessern, sondern die Ursache
entfernen.**

#### Kennungs-Keys statt Aufräumen

Das Muster steht seit dem 07.07.2026 im Projekt (#4, Lösung A) und wird im
selben Modul bereits benutzt — das Strategien-Mehrfachfeld trägt
`key="sv_strategien_" + Familien`. **Ändert sich die Optionsmenge, ist es ein
anderes Widget, und ein Widget ohne Vorgeschichte kann keinen alten Wert
zeigen.**

Zwei streamlit-freie Funktionen tragen jetzt die Entscheidung:

| Funktion | Aufgabe |
|---|---|
| `auswahl_kennung(optionen)` | Kennung der Optionsmenge, **sortiert** — bloßes Umsortieren erzwingt kein neues Widget |
| `auswahl_uebernehmen(vorher, optionen)` | der bisherige Wert, wenn er noch dabei ist — sonst der erste |

**`index` statt einer Zuweisung an den `session_state`** ist dabei der Kern:
`index` wirkt nur bei der **ersten** Instanziierung eines Schlüssels, also
genau dann, wenn die Optionsmenge neu ist. Bei unveränderten Optionen bleibt
die Wahl des Beraters unangetastet — und es wird nie ein Widget-Schlüssel
zugewiesen, womit die Falle aus #4 gar nicht erst auftreten kann.

**Die bisherige Wahl wird übernommen, wenn sie noch gilt** (Philip): Wer von
19 auf die fünf cVV-Reihen reduziert und *cVV defensiv* behält, verliert
seinen Bezug nicht. Am AppTest nachgemessen:

| Schritt | Bezug |
|---|---|
| 19 Strategien, Bezug auf *cVV defensiv* gesetzt | cVV defensiv |
| auf die fünf cVV reduziert (*cVV defensiv* dabei) | **cVV defensiv** — übernommen |
| auf *Pro* + *Pro Dividende* reduziert | **Pro** — rückt nach, Daten sofort da |
| wieder auf sechs erweitert | Pro — bleibt |

#### Der Prüfstein prüft die Regel, nicht das Verhalten

Da AppTest den Fehler nicht erzeugen kann, wäre ein Verhaltenstest wieder ein
grüner Lauf ohne Aussage (#64/#65). Schritt 10 prüft stattdessen die beiden
reinen Funktionen — und **die Zusage** über 371 Teilmengen der 19 Strategien:
*Der übernommene Wert liegt immer in den Optionen.* **1484 Fälle, keine
Verletzung.**

Dazu eine Prüfung, die leicht vergessen wird: Ein noch gültiger Wert muss
auch wirklich **stehen bleiben**. Ohne sie wäre die Zusage auch mit „nimm
immer den ersten" erfüllt — und die Übernahme stillschweigend wirkungslos.

**Gegenprobe:** Gegen die vorherige Fassung ist Schritt 10 rot; die beiden
Funktionen fehlen dort, und `_symbole` meldet sie namentlich (#65).

#### Beweise

| Gemessen | Ergebnis |
|---|---|
| Testsuiten | **26 von 26 grün**, kein Schritt übersprungen |
| `pyflakes` über 44 Dateien | **null** |
| `ui_dump` **alle drei** Ansichten | **zeichengleich** |
| Zusage über 371 Teilmengen | 1484 Fälle, **keine Verletzung** |

---

### Die Gattungsfarben liegen fest — jetzt auch im Tool (18.08.2026)

Gemeldet: In der Allokation nach Gattung bekam die **größte** Gattung immer
Fuggerblau. Tatsächlich sind die Farben der Assetklassen im Corporate Design
fest vergeben — so auf der Webseite der Bank und so in der Broschüre.

**Der Fehler war schon einmal da, an anderer Stelle.** Der Kommentar in
`chart_dynamik.py` beschreibt ihn seit dem 10.07.2026 wörtlich:

> *Die `<c:dPt>`-Farben der Vorlage hängen am INDEX, nicht am Namen. […] nach
> dem Befüllen steht AKTIEN auf idx 0 und erbt Gold.*

Dort wurde er mit `ring_segmentfarben` und der Tabelle `ASSET_FARBEN` gelöst.
**Die Streamlit-Seite konnte sie nicht erreichen** — sie lag in einem Modul
des Export-Pfads.

#### Was gemessen wurde, bevor etwas geändert wurde

| Gemessen | Ergebnis |
|---|---|
| Ring-Segmente in **gebauten** Broschüren | **54 von 54 richtig** — die Broschüre war nie betroffen |
| Ring-Charts in den Vorlagen | **22**, Zuordnung positionsunabhängig belegt |
| Gegenprobe am alten Tool-Stand | *cVV defensiv*: **Aktien trug Gold** `#C3A069`, Renten Fuggerblau |

Die kanonische Tabelle, aus den Vorlagen abgelesen und nicht erfunden:

| Kategorie | Farbe | |
|---|---|---|
| AKTIEN | `#14355C` | dunkelblau |
| RENTEN | `#66A4CE` | hellblau |
| EDELMETALLE | `#BB9256` | gold |
| LIQUIDITÄT | `#9FD0EF` | helleres blau |
| SONSTIGE | `#808080` | grau |

*(FFPB und Thema führen für LIQUIDITÄT `#D1E9F8`. `ASSET_FARBEN` normalisiert
seit 10.07.2026 auf `#9FD0EF`; die Abweichung steht im Prüfstein namentlich
als anerkannte Ausnahme.)*

#### Warum die Regel an der DIMENSION hängt und nicht an der Kategorie

Die Klassifizierung arbeitet mit Teilzeichenketten und trifft deshalb auch
Werte, die gar keine Gattungen sind. An den echten Daten gemessen:

| Wert | Dimension | klassifiziert als |
|---|---|---|
| `Rentenfonds` | **Segment** | RENTEN |
| `Immobilien-Aktien/Fonds` | **Segment** | AKTIEN |

Eine Regel „färbe jede Kategorie, die wie eine Assetklasse aussieht" würde
Assetklassen-Farben in die Segment-Ringe bluten lassen. Im Export löst das
`_ist_assetklassen_ring` (alle Kategorien müssen Assetklassen sein), im Tool
der bekannte Spaltenname. **Beide Prüfsteine halten diese Begründung fest** —
fällt die Klassifizierung eines Tages anders aus, ist der Grund für die
Dimensionsregel weg und gehört neu geprüft.

#### Umfang: nur die Gattung (Philip)

Region, Segment und Währung behalten die Palette — wie in der Broschüre. Die
Vorlagen führen dort zwar ebenfalls eindeutige Farben (**26 Kategorien, keine
mit zwei Farben**), decken aber nur einen Teil der echten Daten ab:

| Dimension | in den Vorlagen | in den Daten |
|---|---:|---:|
| Gattung | 5 | 4 — vollständig |
| Region | 7 | 10 |
| Währung | 4 | 6 |
| Segment | 11 | 18 |

Dazu eine Kollision: `#D1E4C6` trägt *Emerging Markets* (FFPB) und *Asien*
(Thema) — beide kommen in den Daten vor. Für eine Ausweitung müssten zwölf
Farben erfunden werden, und der Kommentar zur Palette sagt ausdrücklich
*„stammt aus den Vorlagen selbst (nicht erfunden)"*.

#### Neues Modul `modules/farben.py` — streamlit-frei

Die Zuordnung wird von **beiden** Seiten gebraucht. Sie liegt jetzt an einem
Ort, den Export und Oberfläche erreichen, ohne dass der Export Streamlit
hereinzieht: `ASSET_FARBEN`, die Gruppen und `klassifiziere_gattung` sind
dorthin umgezogen, `chart_dynamik` und `pptx_slides` reichen die alten Namen
per Zuweisung weiter.

**Zwei Schreibweisen, und das ist kein Versehen:** OOXML will
`srgbClr val="14355C"` **ohne** Doppelkreuz, Plotly `#14355C` **mit**. Ein
`#` im XML fällt nicht auf — die Datei bleibt gültig, PowerPoint zeigt
irgendetwas. Der Prüfstein hält deshalb fest, dass in `ASSET_FARBEN` keine
Raute steht.

#### Der Prüfstein hängt die Konstante ans Artefakt

`tests/test_farben.py` öffnet **alle sechs Vorlagen**, liest die tatsächlichen
`<c:dPt>`-Farben und hält sie gegen die Tabelle: **62 Segmente, alle stimmen.**
Ein Test, der nur die Konstante gegen sich selbst prüft, würde jede
Verschiebung mitmachen.

**Gegenprobe:** Gegen den gemeldeten Stand ist Schritt 3 rot und nennt den
Fehler wörtlich — *„cVV defensiv: Aktien hat #C3A069, erwartet #14355C"*.

#### Beweise

| Gemessen | Ergebnis |
|---|---|
| Testsuiten | **27 von 27 grün**, kein Schritt übersprungen |
| `pyflakes` über 45 Dateien | **null** |
| **Broschüren vorher/nachher** | **2056 ZIP-Einträge, 0 Abweichungen** |
| `ui_dump` alle drei Ansichten | **zeichengleich** |
| `ASSET_FARBEN` gegen die Vorlagen | 62 Segmente, alle stimmen |

Der Broschüren-Vergleich war Pflicht: `ASSET_FARBEN` und `classify_gattung`
liegen **im Export-Pfad**.

#### Nachfrage zur Rentenfarbe: nicht verifizierbar — und das war die Antwort

Nach der Sichtprüfung kam der Verdacht, die Renten seien auf der Webseite der
Bank **dunkler** als im Werkzeug, mit der Bitte, das über die Seite zu
verifizieren. **Das ging nicht.** Die brauchbare Antwort war, genau das zu
sagen, statt eine plausible Zahl zu liefern.

Warum es nicht ging, als technischer Merksatz für das nächste Mal: Das
Abrufwerkzeug wandelt eine Seite in **Text** um und wirft dabei CSS, SVG und
Skripte weg. Die Ringe unter „Aktuelle Struktur" entstehen erst im Browser;
ein gezielter zweiter Versuch nach Diagrammdateien fand **nur Fotos und das
Logo**. Eine Farbe, die in keiner abrufbaren Datei steht, ist so nicht
messbar — und ein Werkzeug, das die Quelle nicht lesen kann, darf ihr
Ergebnis nicht behaupten.

Geliefert wurde stattdessen das, was die Frage trotzdem entscheidbar macht:
**alle** Farben der sechs Vorlagen ausgezählt, mit Helligkeit.

| Farbe | Vorkommen | Helligkeit | wofür |
|---|---:|---:|---|
| `#14355C` | 21x | 49 | Aktien |
| **`#66A4CE`** | **20x** | **154** | **Renten** |
| `#BB9256` | 19x | 150 | Edelmetalle |
| `#9FD0EF` | 15x | 200 | Liquidität |
| `#386FA7` | 2x | 103 | Corporates, USD |
| `#5F8CA1` | 2x | 132 | Prod. Gewerbe und Industrie |

Damit war der einzige ernsthafte Kandidat für „dunkler" benannt: `#386FA7`,
deutlich dunkler — aber in keiner Vorlage je für Renten benutzt. Dazu eine
Vergleichsseite mit vier Ringen, gleiche Anteile, Aktien, Edelmetalle und
Liquidität überall gleich, **nur die Renten wechselten**.

**Ergebnis:** Philip hat in der Broschüre nachgesehen und `#66A4CE`
bestätigt. **Am Code wurde nichts geändert.**

Der Grundsatz stand vorher schon im Modul und im Prüfstein — die Palette
*„stammt aus den Vorlagen selbst (nicht erfunden)"*. Eine Farbe auf Verdacht
zu ändern hätte den Prüfstein rot gemacht und Broschüre und Werkzeug
auseinandergezogen, für eine Vermutung, die sich als falsch erwies.

Als Transferwissen **#68** festgehalten, zusammen mit dem Umkehrschluss:
Wäre der Verdacht richtig gewesen, hätte dieselbe Gegenüberstellung ihn in
einem Schritt bewiesen.

---

### Zwei Hinweistexte im Performance-Reiter (18.08.2026)

Zwei Fragezeichen-Texte der Kennzahlen-Kacheln waren unpräzise. Der
Calmar-Hinweis endete auf einen halben Satz; der Sharpe-Hinweis nannte den
risikofreien Zins dreimal, ohne zu sagen, welcher gemeint ist — im
Kundengespräch ist genau das die Rückfrage.

| | vorher | jetzt |
|---|---|---|
| Calmar | „Je höher, desto besser die risikoadjustierte Rendite." | „Je höher der Wert, desto besser **ist** die risikoadjustierte Rendite." |
| Sharpe | „(Portfolio − **rf**) … Misst die Überrendite …" | „(Portfolio − **risikofreier Zins**) … als risikofreier Zins dient der **3-Monats-Euribor**." |

**Die Euribor-Angabe ist gemessen, nicht übernommen.** Die CSV-Spalte heißt
schlicht `Risiko freier Zins` und nennt keine Quelle. Belegt hat es die Reihe
selbst: Tief **−0,605 % am 14.12.2021**, Hoch **4,002 % am 19.10.2023** — die
Extremwerte des 3-Monats-Euribor. Die Laufzeit ist damit unterscheidbar (1M
rund 3,86 %, 6M rund 4,2 %). Steht als Transferwissen **#69**.

**Nicht geändert:** die sichtbare Zeile „Ø Risikofreier Zins p.a. (Zeitraum)"
unter den Kacheln und der Hinweis des Kontrollkästchens — so entschieden.

| Gemessen | Ergebnis |
|---|---|
| Neuer Prüfstein gegen den alten Stand | **rot**, vier benannte Abweichungen |
| Diff in `streamlit_app.py` | **2 Zeilen**, Zeilenenden unverändert (1150 CRLF) |
| Export-Pfad | nicht berührt — `display_metrics` ist reine Oberfläche |

---

### Die YTD-Kachel (21.08.2026)

Aus dem Feedback: In der Kennzahlen-Reihe fehlte die **YTD-Rendite**. Sie ist
im Kundengespräch die erste Rückfrage („und dieses Jahr?"), stand aber nur in
der rollierenden Tabelle — und die liegt hinter einem Schalter.

Jetzt steht sie als zweite Kachel, direkt neben „Auflage der Strategie"
(Position: Philip). Beide Reihen stehen dafür auf **vier** Spalten statt drei,
damit die Kacheln untereinander bleiben.

#### Die Rechnung ist geliehen, nicht neu

Das ist der eigentliche Punkt. Eine zweite eigene YTD-Rechnung wäre der
Rückschritt gewesen: Seit dem 03.07.2026 rechnen rollierende Tabelle,
Balken-Chart und PP-Folie 8 **bit-identisch** ab Vorjahres-Schlussstand
(`asof(31.12.)` statt `asof(01.01.)`, Transferwissen **#22**). Eine vierte
Rechnung daneben hätte diese Einigkeit wieder aufgelöst.

Die Kachel ruft deshalb `period_return(sa1t, Timestamp(jahr-1,12,31), ende)`
auf — **dieselbe Funktion auf denselben Serien**, die `build_rolling_table`
für ihre YTD-Zeile bekommt. Sie kann gar nicht abweichen.

| Gemessen | Ergebnis |
|---|---|
| Kachel gegen YTD-Zeile der Tabelle, 19 Strategien | **19 von 19 zeichengleich** |
| Gegenprobe: Start auf `01.01.` gedreht | **6 von 6 fallen auf** (1,136 % → 1,158 %) |
| `ui_dump` vorher/nachher | **4 Zeilen** eingefügt, sonst zeichengleich |
| `streamlit_app.py` | 1200 CRLF, keine gemischten Zeilenenden |

#### Drei Entscheidungen, die nicht im Code stehen

1. **Bezugspunkt ist das Ende des gewählten Zeitraums**, nicht „heute"
   (Philip). Bei Standardeinstellung ist das das laufende Jahr, bei einer
   historischen Auswertung das letzte darin enthaltene. Sonst widerspräche
   die Kachel ihren Nachbarn, die alle auf dem gefilterten Zeitraum rechnen.
2. **Die Jahreszahl steht nur im Label, wenn es nicht das laufende Jahr ist.**
   `YTD` bei Standardeinstellung, `YTD 2022` bei einer historischen
   Auswertung — sonst wäre „YTD 2026" eine Dopplung. Der Vergleich hängt am
   Ende der Reihe und **nicht** daran, ob jemand am Filter gedreht hat: Eine
   Strategie, deren Daten früher enden, braucht die Jahreszahl genauso.
3. **Deckt der Zeitraum den Jahresanfang nicht ab, steht „–"** und keine
   Zahl. Das kommt gratis aus `_asof_value` und ist wichtiger, als es
   aussieht: Ein stillschweigend abgeschnittenes Rumpf-YTD sähe wie ein
   volles aus — dieselbe Fehlerklasse wie das 122-Tage-Rumpfjahr aus #51
   („Es gibt Daten" ist nicht „der Zeitraum ist abgedeckt").

#### Der Prüfstein sagt die Gleichheit zu, nicht die Zahl

`tests/test_ytd_kachel.py` (29. Suite) rechnet die Kachel **nicht** nach —
das wäre eine zweite Meinung über dieselbe Formel. Er hält fest, dass es
**dieselbe** Zahl ist wie in der Tabelle, über alle 19 Strategien und
zeichengleich statt gerundet. Dazu ein statischer Schritt, der die Bauform
festnagelt (`period_return` auf `sa1t`): Wer die Kachel später auf die volle
Reihe `_voll1` oder eine eigene Formel umstellt, bricht ihn — und genau das
ist der Weg, auf dem die beiden Anzeigen auseinanderlaufen würden.

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
3. **Testumgebung:** `.venv` liegt im Projekt und übersteht den Neustart —
   **aber nur auf dem Rechner, auf dem sie angelegt wurde.** `.venv` und
   `.streamlit\secrets.toml` sind gitignored und kommen **nicht** mit dem
   Klon. Auf einer anderen Maschine fehlen beide:

   ```
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

**App lokal ansehen** (nicht nötig zum Arbeiten, aber praktisch):

```
.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.headless true
```

**`--server.headless true` ist kein Schmuck** (18.08.2026): Beim allerersten
Start fragt Streamlit auf stdin nach einer E-Mail (Onboarding). Wo kein
Eingabekanal hängt, bricht es mit **Exit 127** ab — das sieht aus wie ein
kaputtes Paket und ist keins. Der Schalter überspringt die Frage; die Seite
danach selbst unter http://localhost:8501 öffnen.

Braucht `.streamlit\secrets.toml` mit einem Testzugang — die Datei ist
gitignored und muss lokal angelegt werden (das Repo ist öffentlich):

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

**Sessionende — DRACOON nachziehen** (Reihenfolge wichtig, erst pushen):

```
cd C:\Entwicklung\Performancetool
git push origin verbesserungen
cd <DRACOON-Ablage>
git log --oneline origin/verbesserungen..HEAD    # muss LEER sein
git fetch origin && git reset --hard origin/verbesserungen
```

**`<DRACOON-Ablage>` ist rechnerabhängig — der Buchstabe `H:` gilt nicht
überall.** Der DRACOON-Client bindet dieselbe Ablage unterschiedlich ein:

| Rechner | Pfad |
|---|---|
| Philip | `H:\Entwicklung\Forschung_Claude\Performancetool` |
| Michael (18.08.2026) | `%USERPROFILE%\DRACOON\<Mandanten-ID>\Entwicklung\Forschung_Claude\Performancetool` |

Wer das nicht weiß, misst `Test-Path H:\` → `False` und schließt daraus, die
Ablage sei nicht erreichbar. Genau das ist am 18.08.2026 passiert. Der Pfad
gehört deshalb **gesucht statt angenommen**:

```
Get-ChildItem "$env:USERPROFILE\DRACOON" -Directory
```

`git reset --hard` in der Ablage ist unkritisch, **solange dort nicht
gearbeitet wird** — die Kopie soll ja nur spiegeln. Wer doch etwas geändert
hat: vorher `git status` dort ansehen.

> **Der erste `reset --hard` schlägt dort fehl — und zwar zur Hälfte**
> (18.08.2026). Git bricht ab mit
>
> ```
> warning: invalid write operation detected; you may try:
>         git config windows.appendAtomically false
> error: update_ref failed for ref 'HEAD': cannot update the ref 'HEAD':
>        unable to append to '.git/logs/HEAD': Invalid argument
> ```
>
> **Das Tückische ist der halbe Zustand:** Arbeitsbaum und Index tragen den
> neuen Stand bereits, nur `HEAD` bleibt stehen. `git status` zeigt danach
> jede Datei der Änderung als **vorgemerkt** an — es sieht aus wie ein großer,
> versehentlich angelegter Änderungssatz, und der Reflex, „aufzuräumen", geht
> in die falsche Richtung. Richtig ist der Weg, den git selbst nennt:
>
> ```
> git config windows.appendAtomically false     # einmalig, nur diese Ablage
> git reset --hard FETCH_HEAD                   # jetzt geht er durch
> ```
>
> Der Schalter steht in der Ablage jetzt. Die Ursache ist dieselbe wie bei den
> Geisterdateien: Der DRACOON-Client verträgt kein anhängendes Schreiben auf
> `.git/logs/HEAD`. **Ein Fehlschlag, der die Hälfte seiner Arbeit stehen
> lässt, ist gefährlicher als einer, der gar nichts tut** — nach einem Abbruch
> auf dieser Ablage also immer `git log` UND `git status` ansehen, nicht nur
> eines von beiden.

**Am 18.08.2026 durchgeführt.** Der Sprung ging über **10 Commits** — auf H:
lag noch der Stand vor der Legenden-Geometrie, nicht nur die Farbarbeit des
Tages fehlte. Auf Vorlauf geprüft wurde trotzdem
(`git log origin/verbesserungen..HEAD` muss leer sein), weil ein Kollege
parallel arbeiten könnte; er war leer, also reiner Fast-Forward.

**Die Geisterdateien sind dabei noch einmal beobachtet worden**, dreimal
hintereinander: `test_monatsrenditen.py` lag unversioniert im
Wurzelverzeichnis, war beim gezielten Nachsehen Sekunden später verschwunden
und stand nach dem Reset wieder da. Wer so etwas auf H: findet, muss es also
**nicht** retten — und die Regel „Dateien beim Commit explizit nennen"
bleibt begründet.

**Falls Git auf H: „dubious ownership" meldet:** einmalig

```
git config --global --add safe.directory '%(prefix)///RCO-MASCHINE/DRACOON/Entwicklung/Forschung_Claude/Performancetool'
```

---

## Wo wir stehen

`main` ist **unverändert** — auf GitHub liegt dort weiterhin `3c3b920`.
Alle Arbeit liegt im Branch `verbesserungen` und wartet auf Philips Review:

**https://github.com/FFPBAM/Performancetool/pull/new/verbesserungen**

### Kollegen-Feedback vom 17.08.2026 — eingearbeitet

Die erste Rückmeldung aus dem Gegentest. Drei Punkte kamen von Kollegen, zwei
kamen beim Nachmessen dazu. Fachliche Tiefe steht als Transferwissen **#59**
und **#60** sowie im Changelog; hier nur, was man wissen muss.

| # | Woher | Kern | Wirkung |
|---|---|---|---|
| 1 | Kollegen | Kalender im „Eigenen Zeitraum" zeigt **englische Monate** | **gebaut und wieder zurückgebaut** — bleibt englisch |
| 2 | Kollegen | Einzeltitel-Übersicht zwingt zum **Scrollen in der Tabelle** | bei *Pro* waren 22 von 32 Aktien unsichtbar |
| 3 | Berater | **Fälligkeiten der einzelnen Anleihen** fehlen | neue Tabelle unter dem Balkenchart |
| 4 | nachgemessen | Anleihen **ohne feste Fälligkeit** fielen still aus dem Chart | bis **46,54 Prozentpunkte** |
| 5 | nachgemessen | „Anzahl Titel" zählt die leere CSV-Zeile mit | **38 von 38** Dateien, immer +1 |

**Zu Punkt 1 — gebaut, angesehen, verworfen. Der Kalender bleibt englisch.**

Es war nichts falsch eingestellt: Streamlit 1.61 liefert im Frontend
**ausschließlich** die englische Sprachdatei aus; aus der Browsersprache wird
nur abgeleitet, ob die Woche am Montag beginnt, und einen Sprachparameter gibt
es nicht. `format="DD.MM.YYYY"` wirkt nur auf den Text *im Feld* — dieser Teil
der deutschen Darstellung bleibt und ist per Test festgenagelt.

Verworfen wurden zuerst ein JavaScript-Eingriff (nicht prüfbar, kippt still
beim Update) und eine Fremdkomponente (neue Abhängigkeit, Auto-Update-Falle
#20). Gebaut wurde dann `shared.datum_waehler_de` — **Tag | Monat | Jahr** als
Auswahlfelder. Technisch einwandfrei, 22 Suiten grün.

**Am Bildschirm war es trotzdem schlechter** (Philip, 17.08.2026: *„Es darf
auf Englisch sein. Weil jetzt sieht es nicht schön aus."*): Aus zwei
Bedienelementen wurden sechs, der anklickbare Kalender war weg, und der Gewinn
war ein Monatsname. **Zurückgebaut per `git revert`** — die drei Dateien sind
zeichengleich mit dem Stand davor, der gebaute Weg bleibt in der Historie
nachlesbar (`d99c61a`).

Die Lehre steht als Transferwissen **#60** und ist keine technische: *Ein
gelöstes Problem ist noch keine Verbesserung.* Wo eine Änderung nur das
Aussehen betrifft, gehört die Sichtprüfung **vor** den Ausbau der Tests — hier
waren 22 Suiten grün, bevor überhaupt jemand das Ergebnis gesehen hatte.

**Geblieben ist ein Prüfstein:** Der Bedienpfad „Performance blockweise" →
„Benutzerdefiniert" war von **keinem** Test je berührt. Er wird jetzt
hochgefahren, und alle vier Datumsfelder werden auf `format="DD.MM.YYYY"`
geprüft.

**Zu Punkt 2 — ein Parameter, kein Pixelrechnen.** `st.dataframe` lief mit der
Vorgabe `height="auto"`, und die bedeutet laut Streamlit-Quelltext wörtlich
„zeigt höchstens zehn Zeilen". Jetzt `height="content"`. Die **Breite war nie
das Problem** (`width` steht ohnehin auf `"stretch"`) — die Annahme, dass die
Tabellen zu schmal seien, hat sich beim Nachsehen nicht gehalten.

**Zu Punkt 4 — die Kachel und der Chart sprachen von verschiedenen Mengen.**
Renten-ETFs und Rentenfonds haben keine feste Fälligkeit. Sie zählten oben mit
und fehlten unten wortlos:

| Strategie | Kachel „Gewicht Anleihen" | Summe der Balken | fehlte |
|---|---:|---:|---:|
| ETF Muster 40/60 ausgew. | 46,54 % | 0,00 % | **46,54 %** (kein Chart) |
| Muster SCHWEIZ Substanz | 30,89 % | 15,35 % | **15,54 %** |
| Muster SCHWEIZ Aktien | 11,56 % | 0,00 % | 11,56 % (kein Chart) |
| ETF Muster 100/100 offensiv | 11,38 % | 0,00 % | 11,38 % (kein Chart) |
| ESG Muster defensiv | 61,14 % | 57,83 % | 3,31 % |

Dieselbe Klasse wie Audit-Befund B6: Ein Fehlwert darf nicht wie ein Messwert
aussehen — hier sah ein **unvollständiges Aggregat** wie ein vollständiges
aus. Die Differenz wird jetzt benannt, und wo gar kein Chart erscheint, steht
ein Satz statt einer Leerstelle.

**Beweise.** 22 von 22 Suiten grün, kein Schritt übersprungen, `pyflakes` bei
null. `ui_dump` vorher/nachher: Performance-Ansicht **zeichengleich**;
Portfolioanalyse ändert genau vier Zeilen (neue Überschrift, neue Tabelle,
neue Caption, „Anzahl Titel" 23 → 22). Sieben Broschüren aus einem
Arbeitsbaum auf dem alten Stand gebaut und rekursiv verglichen: **2105
ZIP-Einträge, 0 inhaltliche Abweichungen** — obwohl `portfolioanalyse.py` im
Export-Pfad liegt. Jeder Schritt des neuen Prüfsteins schlägt gegen den alten
Stand an.

*(Ein Werkzeug ist dabei besser geworden: `ui_dump` erfasste bis heute nur die
Performance-Ansicht. Für die Portfolioanalyse gab es also gar keinen
Vorher/Nachher-Beweis — ausgerechnet für die Ansicht, die hier umgebaut wurde.
Jetzt `python tests/ui_dump.py datei.json portfolio`.)*

### Abnahmelauf vom 17.08.2026 (vormittags) — grün, ohne Codeänderung

Kein neuer Commit. Geprüft wurde der Stand `5beecff`, so wie er auf GitHub
liegt.

| Gemessen | Ergebnis |
|---|---|
| Testsuiten | **21 von 21 grün**, rund 100 Sekunden |
| `pyflakes` über 38 Dateien | **null Meldungen** |
| Arbeitsverzeichnis | sauber, identisch mit `origin/verbesserungen` |

**Gelaufen ist der volle Umfang, nicht die Kurzfassung** — das ist bei dieser
Testlandschaft die eigentliche Frage. Die Suiten überspringen ihre schweren
Schritte stillschweigend, wenn Pakete fehlen (siehe „Tests"); gestartet wurde
deshalb gegen `.venv\Scripts\python.exe`, und die Protokolle wurden auf
übersprungene Schritte durchsucht: **keiner**. Die AppTest-Schritte sind
wirklich hochgefahren, die PPTX-Schritte haben neun echte Broschüren gebaut
(inkl. `Thema_x3`, `Thema_SCHWEIZ`, `comdirect`) und wieder eingelesen.

Damit sind auch die Prüfsteine des Audits am aktuellen Stand bestätigt:
`test_kosten_mathematik` Schritt 3 (die auf 1e−12 verschärfte Prüfung über
alle sechs Honorarsätze, an der B3 hängt), `test_monatsrenditen` Schritt 8
(Layout statt Daten, #54) und `test_risiko` Schritt 7.

**Die Nachkosten-Zahlen sind gegengerechnet.** Aus den Rohdaten neu verkettet,
einmal über die Monatsmatrix und einmal über die Tagesrenditen — beide Wege
treffen die Sollwerte aus dem Audit auf zwei Nachkommastellen:

| Strategie | gerechnet | Soll (nach B3) |
|---|---:|---:|
| Muster offensiv cVV, kumuliert seit 2009 | 183,72 % | 183,72 % |
| Muster ausgewogen cVV, kumuliert | 144,82 % | 144,82 % |

Das ist mehr als eine Wiederholung des Tests: Gerechnet wurde **von den
CSV-Rohdaten aus durch die ganze Kette** — Laden, `historie_beschneiden`,
Honorarabzug, Verkettung —, nicht an der einzelnen Funktion, die der
Prüfstein aufruft. Die korrigierte Formel kommt also in der ausgewiesenen
Kennzahl an. *(Nicht gemessen: eine gebaute Broschüre wieder aufgemacht und
die Zahl dort abgelesen — das bleibt der Sichtprüfung am Endprodukt.)*

**Sichtprüfung: Philip hat die neuen Ansichten am Bildschirm gegengesehen —
in Ordnung.** Sie gehen jetzt an Kollegen zum Gegentesten; bis deren
Rückmeldung da ist, wird an den Ansichten nichts geändert. Vorbereitend
wurden vier Strategien als HTML vorgerendert (*Muster ausgewogen cVV*,
*Comdirect 100*, *Muster FFPB Pro*, *Muster SCHWEIZ Aktien* — sie decken
lange Historie, dünne Historie, angebrochenen Monat und fehlende Benchmark
ab). Vier Zusagen ließen sich dabei an der **Geometrie** nachmessen statt am
Auge: 2026 steht oben und die Ø-Zeile unten, die Bandbreite trägt bei
*Comdirect 100* die Zeilen `2J Hoch/Mittel/Tief` ohne Jahresspalte, der Juli
2026 bei *Muster FFPB Pro* trägt sein Sternchen, und beide Achsentypen sind
gesetzt statt geraten.

*(Das Renderskript liegt bewusst im Scratchpad und nicht im Repo — es ist ein
Werkzeug für einen Tag, kein Prüfstein. Was dauerhaft gelten soll, steht in
`tests/test_monatsrenditen.py`.)*

**Eine Lehre aus dem Vorgehen, die nichts mit dem Code zu tun hat:** Der erste
Renderlauf rechnete mit **0,0155 % statt 1,55 %** Honorar, weil das
Wegwerfskript `fee_default` durch 100 teilte — der Wert steht aber bereits
dezimal in der Zeitreihe, die Oberfläche multipliziert ihn nur fürs
Eingabefeld mit 100 und teilt danach wieder (`streamlit_app.py`: `fd1*100`
→ `fdec1 = fp1/100`). Ergebnis wären Bruttozahlen unter der Beschriftung
„nach Kosten" gewesen — **genau Befund B6, nur selbst gebaut**. Aufgefallen
ist es an der ausgegebenen Kennzahl, nicht am Bild: 0,02 % passte nicht zu
den 1,55 %, die im Mapping stehen. Deshalb steht die Gegenprobe oben. Wer ein
Hilfsskript baut, das dieselben Zahlen zeigt wie das Werkzeug, muss es an
einer bekannten Zahl festmachen — sonst prüft er sein Skript und nicht die App.

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

### Was der Audit im Code hinterlassen hat — die Landkarte

| Datei | Stelle | Was |
|---|---|---|
| `modules/analytics.py` | `annual_fee_to_daily_drag` | **Die Formel.** `d = 1 − (1−f)^(1/365)`. Delegiert **nicht** mehr an `annual_to_daily_rate`. Wirft `ValueError` ab 100 % p.a. |
| | `calc_vola` | Trägt jetzt die Begründung für √365 (stand vorher nirgends). Einzige Stelle, an der √365 gerechnet wird |
| | `ROLL_FENSTER_TAGE` | Docstring korrigiert — die alte Begründung war für 18 von 19 Reihen falsch |
| `modules/shared.py` | `build_portfolio_timeseries` | Kein blankes `except` mehr beim Honorarsatz; setzt `attrs["honorar_gefunden"]` |
| | `strategien_ohne_honorarsatz` | **neu** — bewusst nicht inline im Renderpfad (#55) |
| `modules/risiko_ansicht.py` | `zeitraum_hinweis` | **neu** — verortet „3 Jahre" unter beiden Tabellen |
| | Caption Risikotabelle | Kostenbasis von TE/IR benannt |
| | Caption Drawdown-Tabelle | Sagte vorher **gar nichts** über ihre festen Zeiträume |
| `streamlit_app.py` | vor dem Kennzahlen-Block | `st.error`, wenn ein Honorarsatz fehlt — nennt die Strategie |

**Drei Verbraucher der Formel blieben unverändert** (`calc_daily_returns_after_fee`,
`calc_period_return_after_fee`, `make_index_after_fee`) — der Satz betritt das
System an genau einer Stelle, deshalb war B3 eine Ein-Zeilen-Korrektur.

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
| **Tests** | **23 Suiten** unter `tests/` plus das Werkzeug `ui_dump.py` — vorher gab es keine einzige. |
| **Dritter Tab** | *(18.08.)* **Strategievergleich**: Risiko-Rendite-Punktwolke über alle 19 Strategien, X-Achse umschaltbar zwischen Volatilität und Max Drawdown, Farbe nach Familie. Die eigentliche Arbeit war der **Zeitraum** — ungleiche Historien von 1,7 bis 17,6 Jahren verschieben die Rangfolge um bis zu zehn Plätze. Wer den gewählten Zeitraum nicht abdeckt, wird genannt statt gezeichnet. Details oben. |
| **Stufe 2 desselben Tabs** | *(18.08.)* **Überschneidung** (Σ min der Gewichte, fünf Ebenen, Fokus auf eine Bezugsstrategie) und **Exposure** (gestapelte 100-%-Balken über Gattung, Region, Währung, Segment-innerhalb-Gattung). Neues streamlit-freies Modul `bestandsanalytik.py`; `calc_liquidity` dorthin umgezogen. Broschüren bewiesen unverändert. |
| **Ein Theme fürs ganze Werkzeug** | *(18.08.)* Die App lief seit jeher mit Streamlits Standard-Akzent **#FF4B4B**, weil `.streamlit/config.toml` keinen `[theme]`-Abschnitt hatte. Jetzt Fuggerblau (hell) und Hellblau (dunkel), ruhigere Ecken, Schrift über das Theme statt über einen CSS-Hack. Neuer Prüfstein `test_theme.py`. |
| **Drilldown auf die Einzeltitel** | *(18.08.)* Klick auf einen Balken der Überschneidung öffnet die Aufstellung: welche Titel, mit welchem Gewicht in beiden Depots. Die Beiträge summieren sich exakt zur Übersicht (855 Kombinationen, 1,1e−16). |
| **Kollegen-Feedback** | *(17.08.)* Einzeltitel ohne Scrollbalken, Fälligkeiten je Anleihe. Dazu zwei Befunde beim Nachmessen: still fehlendes Rentengewicht im Fälligkeits-Chart (bis 46,54 PP) und „Anzahl Titel" bei 38 von 38 Dateien um 1 zu hoch. Der vierte Punkt — deutsche Monatsnamen im Kalender — wurde gebaut und wieder **zurückgebaut**; er ist nicht im Branch. Details oben. |
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

- **17.08.2026 (abends)** — **Kollegen-Feedback: alle drei Punkte an der
  laufenden Cloud-App abgenommen.** Philip: *„Der Datumspicker ist wieder der
  alte. Neues Anleihendetail sieht auch super aus. Und man hat die
  Vollansicht."* Damit ist bestätigt, was kein Test zeigen konnte: dass der
  Rückbau vollständig angekommen ist, dass die Fälligkeiten-Tabelle den
  Beraterwunsch trifft, und dass die Einzeltitel-Übersicht ohne Scrollbalken
  tatsächlich als Gewinn empfunden wird.

  **Bemerkenswert an dieser Runde ist die Richtung des Urteils.** Vier
  Änderungen gingen hinaus, alle mit denselben Belegen — 22 grüne Suiten,
  Broschüren byte-identisch, `ui_dump` zeichengleich. Drei kamen gut an, eine
  nicht, und das ließ sich an den Belegen **nicht ablesen**: Die deutsche
  Datumsauswahl war die am gründlichsten geprüfte Änderung des Tages und die
  einzige, die zurückmusste. Wo es ums Aussehen geht, entscheidet der
  Bildschirm, und zwar früh (#60).

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
| `test_bedienung.py` | **+ streamlit** | Zeitraum-Schnellwahl rechnet richtig, PDF-Weg entfernt, Benchmark-Zeile genau einmal, Logo + Datenstand — alles per AppTest am laufenden Programm. **Neu am 17.08.2026: Schritt 1b**, der eigene Zeitraum am **Balken-Chart** („Performance blockweise" → „Benutzerdefiniert"). Dieser Bedienpfad war bis dahin von keinem Test je berührt; er wird jetzt hochgefahren, und es wird geprüft, dass die Auswahl ankommt, beide Felder (`p_bv`, `p_bb`) erscheinen und nichts wirft. Dazu per AST: **alle vier** Datumsfelder tragen `format="DD.MM.YYYY"` — der Teil der deutschen Darstellung, den Streamlit kann; die Monatsnamen im Kalender kann es nicht (#60) |
| `test_portfolioanalyse.py` *(neu 17.08.2026)* | Schritte 1–5 pandas (5 gar nichts), Schritt 6 **+ streamlit** | Die Portfolioanalyse-Ansicht, die bis dahin **keinen eigenen Prüfstein** hatte. Schritt 1 rechnet „Anzahl Titel" gegen die echten Positionen **aller 38** Dateien (alter Stand: 38 Abweichungen), Schritt 2 die Fälligkeiten-Tabelle gegen die Rohdaten, **Schritt 3 die Zusage** Balkensumme + „ohne feste Fälligkeit" == Kachel „Gewicht Anleihen" über alle Strategien (1e−12), Schritt 4 Sortierung, Restlaufzeit und fünf Grenzfälle, Schritt 5 statisch, dass die langen Tabellen `height="content"` tragen, Schritt 6 die gerenderte Ansicht für drei Fälle (mit Anleihen / ohne Anleihen / Anleihen ohne Fälligkeit) |
| `test_streamlit_api.py` | **nichts** | keine abgekündigten Streamlit-Parameter (`use_container_width`) |
| `test_keine_piktogramme.py` | **nichts** | keine Emoji in Überschriften, Hinweisen, Schaltflächen (Kommentare/Doku ausgenommen) |
| `test_anlagekriterien.py` | pandas **+ streamlit** | 17 Strategien, Schreibweise, Banner-Bauweise, AppTest in beiden Ansichten **und für eine Thema-Strategie** (9b); Schritt 4b tastet die Vorlagen ab, damit ein Excel-Eintrag nicht unbemerkt in einer Broschüre landet; **mit Ordner-Argument** zusätzlich der Kasten in den erzeugten Broschüren |
| `test_app_titel.py` | **nichts** (Schritt 1+2) | Tool heißt überall gleich; Schritt 3 fährt die App per AppTest hoch und braucht streamlit |
| `test_legende_musterdepot.py` | **nichts** (Schritt 1) | Legende sagt „Musterdepot"; Schritt 2+3 brauchen python-pptx und überspringen sonst |
| `test_kosten_mathematik.py` | **nichts** (Schritt 1) | Die Honorar-Formel steht nur in `analytics.py`; Schritt 2 prüft die Objekt-Identität in `pptx_export` (braucht pandas + python-pptx), Schritt 3 nagelt die Zahlen fest. **Verschärft am 14.08.2026:** Schritt 3 verlangt jetzt für **alle sechs** Sätze im Bestand, dass 365 Nulltage **exakt** den Satz kosten (1e−12). Vorher stand dort ein Band von 1,50 bis 1,56 — breit genug, um Befund B3 zu verbergen (#58). Dazu: ein Satz ab 100 % p.a. muss `ValueError` werfen |
| `test_formats.py` | **nichts** (Schritt 5 nutzt pandas, Schritt 7 streamlit — beide überspringen sauber) | Deutsche Notation, Datum, Disclaimer-Anker — vor allem: ein Fehlwert wird „–" und niemals „nan"/„None"/„NaT"; Schritt 7 hält fest, dass `shared` dieselben Funktionen nutzt |
| `test_analytics.py` | numpy + pandas | Bausteine gegen von Hand nachrechenbare Werte, degenerierte Eingaben liefern `None` statt Absturz, `has_benchmark`, der Vertrag von `compute_performance_data` (Längen, leere Listen). **Umgestellt am 14.08.2026:** Der Schritt verlangte bis dahin ausdrücklich `annual_fee_to_daily_drag == annual_to_daily_rate` („die Mathematik ist identisch, **nur** die Größe ist eine andere") — in diesem „nur" saß Befund B3. Jetzt wird das Gegenteil verlangt und jede der beiden Zusagen einzeln geprüft; Schritt 6 lässt die 365-Umrechnung in `analytics.py` folglich **zweimal** zu (Gutschrift und Belastung), aber weiterhin nirgends sonst |
| `test_benchmark_erkennung.py` | pandas | 19 Strategien: 2 ohne Benchmark, 17 unverändert (**Kennzahlen**) |
| `test_benchmark_charts.py` | pandas; Schritte 2+3 **+ python-pptx, streamlit** | dasselbe für **Chart, Legende, Fußnote und den Hinweis im Tool** — Schritt 2 baut zwei echte Broschüren und liest nach, Schritt 3 prüft den Hinweis an der gerenderten Oberfläche; „Pro" ist jeweils Kontrollfall |
| `test_honorarsatz.py` | pandas **+ streamlit** | jede Strategie hat einen Satz zwischen 0,5 % und 3 %; SCHWEIZ auf 1,55 % festgenagelt. **Schritt 4 (14.08.2026)** ist die Gegenprobe dazu: Er entfernt eine Mapping-Zeile absichtlich und verlangt, dass die Zeitreihe den Ausfall in `attrs["honorar_gefunden"]` vermerkt — Schritt 1 prüft, dass heute nichts fehlt, Schritt 4, dass ein Fehlen *auffällt*. Dazu fünf Fälle von `strategien_ohne_honorarsatz` |
| `test_historie_ab.py` | pandas **+ streamlit** | 5 Reihen ab 2009, 14 unberührt, Konfiguration zeigt auf existierende Reihen |
| `test_folien_config.py` | pandas **+ streamlit** | Thema-Config identisch zur handgeschriebenen Fassung, alle 5 Familien passen zu ihrer PPTX |
| `test_chartachsen.py` | **nichts** (Schritte 1+2); Schritt 3 **+ python-pptx, streamlit** | Beide Achsen der Linien-Charts. Schritt 1 rechnet `achsen_raster` gegen 13 Fälle nach (Datumsachse), Schritt 2 `wert_raster` gegen 15 (Wertachse) — alle von Hand nachgerechnet, inkl. Grenzfälle. Schritt 3 baut je Familie eine Broschüre plus Themen-Duplikation und SCHWEIZ und **rechnet jede Tickfolge nach**: letzter Datums-Tick im Jahr des letzten Datenpunkts, 100 % auf dem Wertachsen-Raster, keine Achse schneidet etwas ab, beide bleiben lesbar |
| `test_quelle_position.py` | pandas **+ python-pptx**; Schritt 3 **+ streamlit** | Die Quellenangabe steht unter dem Disclaimer, nicht darin. Schritt 1 rechnet den Fußnoten-Textblock aller sechs Vorlagen gegen `WE_QUELLE_TOP_CM`, Schritt 2 misst die Länge **jedes** Ersatztextes gegen die Zeilenbreite (der Test, der den Fehler verhindert hätte), Schritt 3 misst 19 Folien in sieben gebauten Broschüren |
| `test_kalenderjahre.py` | **nichts** (Schritte 1+2); Schritt 3 **+ python-pptx, streamlit** | Der Säulen-Chart zeigt nur Kalenderjahre, die die Zeitreihe vollständig abdeckt. Schritt 1 rechnet 15 Grenzfälle nach (beide Toleranzränder, Loch in der Historie, Strategie ohne ein einziges volles Jahr), Schritt 2 misst **jeden** Balken der 19 echten Reihen gegen die Daten, die ihn tragen, und nagelt die 7 bekannten Fälle namentlich fest, Schritt 3 liest die Kategorien aus gebauten Broschüren (Pro, SCHWEIZ, comdirect ×3, Offensiv als Kontrolle) |
| `test_monatsrenditen.py` | **nichts** (Schritte 1–4 nur numpy + pandas); Schritte 5–11 **+ streamlit** | Die Heatmap, elf Schritte. Schritt 1 rechnet `_ist_voller_monat` gegen 13 Grenzfälle nach, Schritt 2 die Verkettung Zeile → Jahresspalte, Schritt 3 die geometrische Differenz gegen das von Hand gerechnete Beispiel (+9,7506 % statt +10,00 PP), Schritt 5 die Ø-Zeile, Schritt 6 misst **jeden** angebrochenen Monat der 19 echten Reihen gegen die Rohdaten und prüft den Zeitraum-Zuschnitt an beiden Rändern, **Schritt 7 die Bandbreite** (arithmetisches Mittel gegen von Hand gerechnete Werte, Je-Monat-Toleranz, festes Fenster, Invariante `Tief ≤ Mittel ≤ Hoch` über alle Strategien), **Schritt 8 die FIGUR statt der Daten** — Achsentyp, Kategorienreihenfolge, Spaltenzahl, Koordinatentypen der Annotationen; das ist die Prüfung, durch deren Fehlen der Renderfehler schlüpfte —, **Schritt 9 die Zeitraum-Ableitung** (sieben gerechnete Fälle plus die Zusage, dass die älteste Jahreszeile keine Lücke hat), Schritt 10 die Kachelhöhe, Schritt 11 fährt die Oberfläche hoch (beide Ansichten, alle Zeiträume, „Seit Auflage mit jungem Vergleichsportfolio") |
| `test_risiko.py` | **nichts** (Schritte 1–2+4); Schritt 3 nutzt zusätzlich die echten CSVs, Schritt 5 **+ streamlit** | Schritt 1 ist der Konsistenz-Beweis: letzter Punkt der rollierenden Vola == `calc_vola` derselben 365 Tage. Schritt 3 prüft, dass nicht abgedeckte Perioden **leer** bleiben statt gekürzt zu rechnen, Schritt 4 Tracking Error und Information Ratio — inklusive des 1e-12-Guards (#47): identische Reihen ergeben TE 0 und IR „–", nicht 1e16. **Neu am 14.08.2026: Schritt 6** prüft die *Voraussetzung* der 365-Konvention an den echten Daten (kalendertäglich, lückenlos, Werktaganteil rund 5/7) — eine Handelstag-Lieferung würde 365 Zeilen zu 1,40 Jahren machen und √365 falsch. **Schritt 7** prüft den Zeitraum-Hinweis der beiden Tabellen gegen beide Aufrufformen, drei leere Eingaben und einen Schaltjahr-Rand |
| `test_strategievergleich.py` *(neu 18.08.2026)* | Schritte 1+4 numpy/pandas, 2+3 zusätzlich die echten CSVs, 5 **+ streamlit** | Die Risiko-Rendite-Punktwolke des dritten Tabs. Schritt 1 die neue Spalte `rendite` gegen den Anker „eine Reihe ohne Marktbewegung kostet exakt den Satz" (derselbe wie bei B3), dazu die geschlossene Form und vier Grenzfälle; **Schritt 2 die Zusage**, dass die Punktwolke dieselbe Zahl zeigt wie die Kennzahlen-Kachel — 19 Strategien × 3 Kennzahlen, einmal über die ganze Reihe und einmal über das gemeinsame Fenster; **Schritt 3 die Abdeckung** mit namentlicher Festlegung der fünf bekannten Fälle **und der Gegenprobe gegen eine naive Fassung**; Schritt 4 die **Figur** statt der Daten (#54: Achsentypen, Punktzahl, Spuren je Familie, Drawdown als Betrag, **jeder Punkt trägt seinen Namen** — auch bei 27, und nicht abgeschnitten am Rand); Schritt 5 acht Bedienpfade per AppTest |
| `test_bestandsanalytik.py` *(neu 18.08.2026)* | Schritt 1 nur numpy/pandas, 2+3 lesen die echten CSVs | Die Bestands-Mathematik. Schritt 1 `ueberlappung` gegen von Hand gerechnete Fälle und Grenzfälle (leer, None, ein Titel, doppelter Schlüssel, NaN-Gewicht), **Schritt 2 die Zusage** „Kategoriegewichte + Liquidität == 1" über 19 Strategien × 4 Ebenen **plus die Gegenprobe** gegen eine naive Fassung mit `dropna=False`, Schritt 3 Symmetrie und Selbstüberschneidung über alle 171 Paare, drei namentlich festgelegte Paare und die Ungleichung „die feine Ebene liegt nie über einer gröberen" |
| `test_farben.py` *(neu 18.08.2026)* | Schritt 1 **+ lxml**, Schritt 2 **nichts**, 3+4 die echten Bestände | Die festen Assetklassen-Farben. **Schritt 1 hängt die Konstante ans Artefakt:** alle sechs Vorlagen öffnen, die `dPt`-Farben auslesen und gegen `ASSET_FARBEN` halten (62 Segmente); die bekannte Liquiditäts-Abweichung steht namentlich als Ausnahme. Schritt 2 hält fest, dass `Rentenfonds` als RENTEN und `Immobilien-Aktien/Fonds` als AKTIEN klassifizieren — die **Begründung** für die Dimensionsregel. **Schritt 3 die Zusage:** dieselbe Gattung, dieselbe Farbe, über 19 Strategien und bei umgedrehter Reihenfolge. Schritt 4: Region, Segment und Währung bleiben bei der Palette |
| `test_keepalive.py` *(neu 18.08.2026, nach dem Ausfall)* | **nichts** | Jedes Widget mit `key=`, dessen Zustand nicht geschrieben werden darf (Buttons, Download-Buttons, Charts mit `on_select`), muss in `_KEEPALIVE_SPERRE` stehen — geprüft am **Syntaxbaum**, weil AppTest diese Klasse nachweislich nicht reproduziert. Dazu: kein verwaister Eintrag in der Liste, kein berechneter Key an einem Trigger-Widget. Gegen den Stand, der am 18.08.2026 die App anhielt, ist er rot |
| `test_theme.py` *(neu 18.08.2026)* | Schritt 1 ohne jedes Paket, 2–4 **+ streamlit** | Die Oberflächen-Konfiguration — die einzige Datei, deren Fehler sich **nicht bemerkbar machen**. **Schritt 2 ist der eigentliche:** `config.get_where_defined` muss auf `.streamlit/config.toml` zeigen und nicht auf `<default>`; ein Test auf den Dateiinhalt hätte den Fehler von #23 nicht gefunden. Dazu: Punkt im Ordnernamen, kein Zwilling ohne Punkt, gültiges TOML, Farben identisch mit `shared.py`, kein Streamlit-Rot mehr, `theme.base` nicht gesetzt (hell und dunkel bleiben beide), kein `font-family`-CSS mehr im Quelltext |
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
python tests/test_portfolioanalyse.py
python tests/test_strategievergleich.py
python tests/test_bestandsanalytik.py
python tests/test_theme.py
python tests/test_keepalive.py
python tests/test_farben.py
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

**ERLEDIGT am 24.08.2026 (nachmittags) — der Prüfstein steht, und der
Fehler ist behoben.** `tests/test_wertentwicklung_platzhalter.py` (30.
Suite); alle drei stillen Zweige melden jetzt, rollengebunden an die Folien,
die die jeweilige Vorlage wirklich führt. Der ursprüngliche Befund bleibt
unten stehen, weil die Begründung mehr wert ist als die Aufgabe.

**NEU 24.08.2026 — ein Prüfstein fehlt: die Broschüre baut still weiter.**
Fehlt einer Strategie die Zeitreihe, während ihr Bestand vorhanden ist, baut
`pptx_export` die Broschüre trotzdem — und die Wertentwicklungs-Folie behält
die **Zahlen aus der Vorlage**. Ohne Build-Meldung, ohne Eintrag in
`LAST_BUILD_ERRORS`. Am 24.08.2026 am damaligen Datenstand 260821
nachgewiesen, bytegleich mit der unveränderten `.pptx`:

| Familie | Folie | Werte im gebauten Dokument |
|---|---|---|
| comdirect (Comdirect_30) | 7 | 2024: 5,36 %, 2025: 6,24 % |
| ESG (ESG defensiv) | 17 | −12,91 / 5,56 / 6,91 / 7,03 % |

Die Nachbarfolien waren korrekt ersetzt — es fällt also nicht auf. Damit
stünden Platzhalterzahlen als echte Wertentwicklung in einem
**Kundendokument**; dieselbe Klasse wie der comdirect-Disclaimer (Backlog H)
und das fehlende `majorTimeUnit` (#49): eine Ersetzung, die lautlos ins Leere
läuft.

Der Auslöser ist inzwischen weg (die Datenlieferung vom 24.08.2026 ist mit
19 von 19 vollständig), **der Fehler nicht**. Ein Test „nach dem Befüllen
trägt keine Wertentwicklungs-Folie mehr die Zahlen ihrer Vorlage" wäre für
alle sechs Vorlagen in wenigen Zeilen zu haben.

*Zurückgestellt von Philip am 24.08.2026 vormittags — und am selben
Nachmittag gebaut. Beim Bauen kamen zwei weitere Stellen derselben Klasse
heraus, die im Befund oben noch nicht standen: `_build_rollierend_data`
(Familie *Thema*, also eine echte Kundenbroschüre) und die
Übersichtstabelle, die einen TEILausfall verschwieg.*

**Es sind noch drei**, alle bei Philip. Punkt 1 (Sichtprüfung) ist am
17.08.2026 abends **erledigt** und bleibt nur als Beleg stehen. Zwei weitere
Punkte sind **bewusst zurückgestellt** und stehen darunter.

**NEU 18.08.2026 — Sichtprüfung der beiden Tooltips.** Im Performance-Reiter
die Fragezeichen von *Calmar Ratio* und *Sharpe Ratio* aufziehen: Bricht der
Sharpe-Text sauber um? Er ist von 232 auf 297 Zeichen gewachsen. Bewusst
übersprungen (Michael, 18.08.2026) — und deshalb hier genannt und nicht
stillschweigend weggelassen. Der Wortlaut selbst ist per
`tests/test_kennzahlen_hinweise.py` festgenagelt; zu beurteilen ist allein das
Schriftbild.

0. **NEU 14.08.2026 — die geänderten Zahlen freigeben.** Befund B3 hat die
   Honorarformel korrigiert; jede Nachkosten-Zahl im Werkzeug **und in der
   Broschüre** ist dadurch etwas niedriger. Das ist kein Anzeigefehler,
   sondern die Korrektur — bitte einmal bewusst zur Kenntnis nehmen:

   | | vorher | nachher |
   |---|---|---|
   | CAGR, je Strategie | | −0,74 bis −2,80 bp (Median −2,52) |
   | Muster offensiv cVV, kumuliert seit 2009 | 184,92 % | **183,72 %** |
   | Muster ausgewogen cVV, kumuliert | 145,85 % | **144,82 %** |
   | cVV konservativ, „nach Kosten" 10 Jahre | 10,349 % | **10,270 %** |

   Philip hat am 14.08.2026 entschieden: *„die neuen werden jetzt richtig
   gerechnet"* — ältere Broschüren werden **nicht** nachgezogen. Wer die
   Zahlen vergleicht, braucht also den Stichtag.

   Die Spalte **„vor Kosten" ändert sich nicht** — das ist die Gegenprobe,
   dass wirklich nur die Kostenseite betroffen ist (`ui_dump` zeigt genau
   eine geänderte Zeile).

1. ~~**Sichtprüfung der Änderungen aus dem Kollegen-Feedback.**~~ —
   **ERLEDIGT, Philip am 17.08.2026 abends an der laufenden Cloud-App:**

   > *„Der Datumspicker ist wieder der alte. Neues Anleihendetail sieht auch
   > super aus. Und man hat die Vollansicht."*

   Damit sind alle drei Punkte des Kollegen-Feedbacks am Endprodukt bestätigt
   — nicht nur im Testlauf, sondern dort, wo die Berater arbeiten:

   | Geprüft | Ergebnis |
   |---|---|
   | Rückbau der Datumsauswahl vollständig angekommen | in Ordnung |
   | Anleihen-Detail mit den einzelnen Fälligkeiten | in Ordnung |
   | Einzeltitel-Übersicht ohne Scrollbalken („Vollansicht") | in Ordnung |

   *(Nicht ausdrücklich zurückgemeldet und deshalb offen, falls es später
   stört: ob 32 Zeilen am Stück bei „Muster FFPB Pro" die gewünschte Länge
   sind, und ob der Satz zur Lücke bei „Muster SCHWEIZ Substanz" für einen
   Berater verständlich formuliert ist. Beides ist eine Konstante bzw. ein
   Satz — jederzeit änderbar, ohne dass etwas nachgerechnet werden müsste.)*

2. **Beide Ansichten am Bildschirm gegensehen** — *Philip erledigt am
   17.08.2026, Ergebnis in Ordnung. Der Gegentest durch Kollegen hat
   stattgefunden, die Rückmeldung ist eingearbeitet (siehe oben).*

   Die Liste bleibt als **Prüfliste** stehen. Der Renderfehler ist behoben und
   per Layout-Prüfstein festgenagelt, die Zahlen sind belegt.
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
   - **NEU aus dem Audit:** Unter der Risiko- **und** der Drawdown-Tabelle
     steht jetzt je ein Satz, der die festen Zeiträume verortet
     („Gezählt wird taggenau ab dem Datenstand 21.07.2026 — ‚3 Jahre' meint
     hier 22.07.2023 bis 21.07.2026"). Liest er sich neben der Schnellwahl
     oben verständlich, oder verwirrt er mehr, als er klärt?
   - **NEU aus dem Audit:** Unter der Risikotabelle steht der Hinweis, dass
     Tracking Error und Information Ratio die Strategie *nach* Kosten mit
     der Benchmark *ohne* Kosten vergleichen. Ist das so für einen Berater
     brauchbar formuliert?

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

**Nicht offen, sondern entschieden (Philip, 17.08.2026): der
Historien-Beginn bleibt unterschiedlich.** `historie_beschneiden` wirkt im
Performance-Tab **nur** auf Heatmap und Risiko-Block; Kennzahlen,
Linien-Chart und rollierende Tabelle rechnen bei den fünf alten
cVV-Strategien ab dem **31.12.2008**, die Broschüre ab dem **01.01.2009**.

Das stand hier bis zum 17.08.2026 als „gehört entschieden". Es ist
entschieden, und zwar so:

> Dass die Broschüre bei 2009 beginnt, ist **gewollt** und seinerzeit so
> festgelegt worden. Fachlich ist es nicht ganz sauber, betrifft aber nur die
> fünf alten cVV-Reihen. **Das Tool indexiert richtig** — dort bleibt es beim
> tatsächlich ersten Datenpunkt.

Eine Angleichung ist damit **vom Tisch**, nicht vergessen. Die Wirkung ist
ohnehin klein: zwei Tage auf siebzehn Jahre, bei *Muster ausgewogen cVV*
145,4853 % gegen 144,8158 % kumuliert.

Wer die Kennzahlen des Tools nachrechnet, nimmt also die **ungeschnittene**
Reihe. Nachgemessen am 17.08.2026 gegen die laufende Oberfläche: *Muster
konservativ cVV* zeigt 2,19 % p.a. und 2,97 % Volatilität — aus der
ungeschnittenen Reihe gerechnet 2,1854 % und 2,9694 %.

*(Die Heatmap schneidet weiterhin, und das aus einem eigenen Grund: Ohne
`historie_beschneiden` stünde dort eine Kachel **Dez 2008 mit genau einem
Tag**. In einer Matrix aus Monatsfeldern ist das eine Falschaussage; in einer
CAGR über siebzehn Jahre sind zwei Tage keine. Die beiden Konventionen folgen
also der Darstellung und nicht der Nachlässigkeit.)*

*(Die Sichtprüfungen SCHWEIZ, Datumsachse, Wertachse und Quellenangabe
standen hier bis zum 12.08.2026 als offene Punkte — alle vier sind erledigt,
siehe „Sichtprüfung in echtem PowerPoint".)*

### `pyflakes` ist ab jetzt ein echtes Signal

Über alle **39 Dateien null Meldungen** (nachgemessen 17.08.2026 nachmittags,
nach dem Kollegen-Feedback; vormittags waren es 38 Dateien; am 14.08.
waren es 36 gezählte, am 12.08. 33). Wer eine neue erzeugt, sieht sie sofort
— vorher ging sie in 16 bekannten unter. Am 14.08. hat die Prüfung prompt
geliefert: Nach dem Umzug
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
  daneben. **Alle drei Ansichten** sind erfasst: ohne Argument die
  Performance, sonst `portfolio` oder `vergleich` *(18.08.2026 — diesmal am
  Tag des Baus und nicht erst beim ersten Umbau; genau das war der Fehler bei
  der Portfolioanalyse)*.
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
