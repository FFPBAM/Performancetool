# Arbeitsanweisung für Claude — FFPB Performancetool

**Zuerst lesen:** `STATUS.md` (wo stehen wir), dann `PROJEKT_DOKUMENTATION.md`
(58 Transferwissen-Einträge, Architektur, Compliance).

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
- **Jedes Trigger-Widget mit `key=` → Key in `_KEEPALIVE_SPERRE`** (oben in
  `streamlit_app.py`). Sonst stürzt die Seite ab: Das Keep-Alive schreibt
  alle session_state-Keys zurück, und für diese Widgets ist das verboten. Die
  Zuweisung selbst wirft nichts — erst das spätere Anlegen des Widgets,
  weshalb der Traceback dorthin zeigt statt auf die Ursache und das
  `try/except` im Keep-Alive **nicht** hilft (#19, korrigiert 11.08.2026).
  **Nicht nur Buttons** (18.08.2026, nach einem Ausfall): Auch ein
  `st.plotly_chart(key=…, on_select="rerun")` ist ein Widget — genau das hat
  die laufende App angehalten. Prüfstein `tests/test_keepalive.py` hält die
  Regel am Syntaxbaum; er läuft ohne jedes Paket.
- **Die Farben der Assetklassen hängen an der KATEGORIE, nicht an der
  Größe** (#67, 18.08.2026). Aktien dunkelblau, Renten hellblau, Edelmetalle
  gold — festgelegt im Corporate Design, abgelesen aus den Vorlagen, nicht
  erfunden. Die eine Quelle ist `modules/farben.py`; Broschüre und Tool
  greifen darauf zu. **Die Regel gilt nur auf der DIMENSION Gattung**: Die
  Klassifizierung arbeitet mit Teilzeichenketten und liest `Rentenfonds` (ein
  *Segment*) als RENTEN, `Immobilien-Aktien/Fonds` als AKTIEN — eine
  kategoriebasierte Regel färbte damit Segment-Ringe mit. Und: **OOXML will
  die Farbe ohne `#`, Plotly mit** — ein `#` im XML fällt nicht auf.
- **Ein Auswahlfeld, dessen Optionen von einer anderen Auswahl abhängen,
  bekommt einen Schlüssel mit Kennung der Optionsmenge** (#66, 18.08.2026).
  Sonst zeigt es einen Wert, den es nicht mehr gibt. Den Wert nachträglich
  aus dem `session_state` zu löschen ist eine **Annahme** über Streamlits
  Widget-Zustand — sie hat nicht gehalten, und AppTest kann die Verletzung
  nicht nachstellen. Muster: `_waehle_gueltig` in `strategievergleich.py` —
  Kennung über die **sortierte** Menge (Umsortieren soll kein neues Widget
  erzwingen), Startwert über **`index`** statt über eine Zuweisung (wirkt nur
  bei der ersten Instanziierung und umgeht #4).
- **Ein Test, der seinen Prüfgegenstand nicht findet, muss scheitern**
  (#65, 18.08.2026). Die Suiten überspringen bei fehlendem **Paket** — das
  ist richtig und Hausregel. Sie dürfen aber nicht überspringen, wenn ein
  **Symbol** fehlt: Das ist ein gebrochener Vertrag, kein Umgebungsproblem.
  Ein `except Exception` um den Import behandelt beides gleich und macht aus
  dem einen Schutz eine Tarnkappe für das andere. Muster:
  `_symbole(modul, namen, pakete)` in `tests/test_strategievergleich.py` —
  erst die Pakete prüfen (ggf. überspringen), dann die Namen holen (fehlt
  einer: FEHLER mit Namensnennung).
- **Wer ein Risiko prüft und nichts findet, hat zwei mögliche Ergebnisse**
  (#64, 18.08.2026): Das Risiko besteht nicht — oder **der Test erreicht es
  nicht**. Beim Chart oben wurde A gewählt, ohne B auszuschließen, und das
  grüne AppTest-Ergebnis wanderte als Beleg in die Doku. Ein Test, der ein
  Risiko ausschließen soll, braucht deshalb eine **Gegenprobe**: den Fehler
  absichtlich einbauen und verlangen, dass es anschlägt. Und wo ein
  Verhaltenstest nicht hinkommt, prüft man die **Regel** statt das Verhalten
  (Syntaxbaum statt AppTest).
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
- **„Es gibt Daten" ist nicht „der Zeitraum ist abgedeckt"** (#51,
  12.08.2026). Der Säulen-Chart der Wertentwicklungs-Folie zeigte das
  angebrochene **Auflagejahr** als vollen Jahresbalken — bei „Pro" 122 Tage
  als „2023", unter einer Überschrift, die „p.a." sagt. Geprüft wurde nur
  `sub.empty`. Wo ein Aggregat für einen Zeitraum steht, gehört die
  **Abdeckung** geprüft, und zwar an **beiden** Rändern mit **gleicher**
  Toleranz (`_ist_volles_jahr`, `JAHR_RAND_TOLERANZ_TAGE` in `analytics.py`;
  Prüfstein `tests/test_kalenderjahre.py`). Zwei Folgeregeln: Wer einen
  Filter verschärft, prüft, **was der leere Rest auslöst** — hier blieben
  sonst die Beispieldaten der Vorlage im Chart stehen. Und: das **Tool zeigt
  bewusst weiter Teiljahre** (Philip, 12.08.2026); die Konsistenz-Doktrin
  gilt für die Mathematik, nicht zwingend für den Ausschnitt.
- **Warnlisten sind nur dann Warnungen, wenn jemand sie liest.**
  `pptx_slides.EINZELTITEL_WARNUNGEN` behauptete im Kommentar, ausgelesen zu
  werden — im ganzen Repo gibt es keine Leseposition. Der einzige Kanal, der
  beim Berater ankommt, ist `pptx_export.LAST_BUILD_ERRORS`
  (`portfolioanalyse.py` zeigt ihn nach dem Export an). Dort anhängen, nicht
  woanders.
- **Eine Umrechnung muss zu der Rechenart passen, in der sie benutzt wird**
  (#56/#58, 14.08.2026, Audit-Befund B3). Der Honorar-Tagessatz kam aus
  `annual_to_daily_rate`, also aus der Aufzins-Formel für eine **Gutschrift**
  — abgezogen wurde er trotzdem. Aufzinsen und Abziehen sind nicht
  symmetrisch:

  ```
  Gutschrift (rf)       (1 + d)^365 = 1 + r    d = (1+r)^(1/365) - 1
  Belastung (Honorar)   (1 - d)^365 = 1 - f    d = 1 - (1-f)^(1/365)
  ```

  Bei 1,55 % wurden dadurch 1,5264 % abgezogen — 2,36 bp pro Jahr zu wenig,
  immer zugunsten des Hauses. **Der Honorarsatz betritt das System an genau
  einer Stelle** (`annual_fee_to_daily_drag`), deshalb war die Korrektur eine
  Zeile; die drei Verbraucher blieben unberührt. Prüfstein:
  `tests/test_kosten_mathematik.py`, Schritt 3.
- **Der Sollwert einer Prüfung kommt aus der Zusage, nicht aus dem Ergebnis**
  (#58). Genau dieser Fehler hielt B3 jahrelang verborgen: Der Kommentar
  sagte „muss **exakt** das Honorar kosten", geprüft wurde ein Band von 1,50
  bis 1,56, und die Fehlermeldung nannte als Soll „~1,53" — abgeschrieben vom
  gemessenen Wert. Die Toleranz umschloss den Fehler, den sie finden sollte.
  Wer eine Toleranz setzt, muss sagen können, **welchen Fehler sie noch
  fangen soll**; „so kam es halt heraus" ist keine Begründung.
- **Ein stiller Rückfall ist dort am gefährlichsten, wo er plausibel
  aussieht** (#57, Audit-Befund B6). `except Exception: fd = 0.0` beim
  Honorarsatz ließ eine Strategie brutto rechnen — auf dem Bildschirm nicht
  von einer Angabe zu unterscheiden, weil der Satz in einem **Eingabefeld**
  steht. Wirkung gemessen: 6,90 % statt 5,27 % p.a., **1,63 Prozentpunkte**
  zu hoch. Ein Vorgabewert nach einem Fehlschlag muss sich vom selben Wert
  als echte Angabe unterscheiden lassen — sonst ist der Schutz vor dem
  Absturz zugleich die Tarnung des Fehlers (`attrs["honorar_gefunden"]`).
- **Prüfe die Voraussetzung getrennt vom Ergebnis** (#56). Die Begründung für
  √365 war sachlich falsch (die Wochenenden tragen **Kuponabgrenzung** des
  Anleihenteils, keine Nullen — bei 18 von 19 Reihen), die Konvention aber
  richtig: Die Reihen sind echte Kalendertagreihen. Ein richtiges Ergebnis
  beweist die Begründung nicht, und eine falsche Begründung widerlegt das
  Ergebnis nicht. **Für `ret_bm` gilt die Nullen-Aussage weiter und zu Recht**
  (`has_benchmark`) — ein pauschales Ersetzen hätte drei korrekte Stellen
  zerstört.
- **Der Kalender bleibt englisch — nicht erneut versuchen** (#60, entschieden
  17.08.2026). `st.date_input` ist der richtige Baustein; `format="DD.MM.YYYY"`
  macht den Text **im Feld** deutsch, das aufklappende Popover kann Streamlit
  nicht übersetzen (1.61 liefert im Frontend nur die englische Sprachdatei
  aus, aus der Browsersprache kommt nur der erste Wochentag, einen
  Sprachparameter gibt es nicht). Der Ersatz durch eigene Tag/Monat/Jahr-Felder
  **wurde gebaut und wieder verworfen**: technisch einwandfrei, am Bildschirm
  schlechter — aus zwei Bedienelementen wurden sechs (Philip: „Es darf auf
  Englisch sein"). Prüfstein: `tests/test_bedienung.py`, Schritt 1b hält
  `format="DD.MM.YYYY"` an allen vier Feldern fest.
- **Ein gelöstes Problem ist noch keine Verbesserung** (#60). Wo eine Änderung
  nur das Aussehen betrifft, entscheidet die **Sichtprüfung** — und die gehört
  **vor** den Ausbau der Tests. Am 17.08.2026 waren 22 Suiten grün, bevor
  jemand das Ergebnis am Bildschirm gesehen hat; danach musste alles zurück.
- **Der Arbeitsbranch `verbesserungen` IST die laufende App.** Streamlit Cloud
  deployt ihn, nicht `main` — die Doku behauptete bis 17.08.2026 das Gegenteil
  und ein Push in dem Glauben hat die App für die Kollegen angehalten. Vor dem
  Push alle Tests grün, **nach** dem Push die App ansehen. Stürzt sie mit
  `ImportError` ab: erst prüfen, ob das Symbol wirklich auf dem Server fehlt
  (`git show origin/verbesserungen:<datei>`), dann **Reboot app** (die Cloud
  kann ein altes Modul im Speicher behalten), erst dann in die Logs (#11).
- **`st.dataframe` zeigt von sich aus höchstens zehn Zeilen** (17.08.2026).
  Die Vorgabe `height="auto"` bedeutet genau das; danach entsteht ein
  Scrollbalken **innerhalb** der Tabelle. Wo eine Tabelle vollständig gelesen
  werden soll, gehört `height="content"` dazu. Bewusst **kein** gerechneter
  Pixelwert — eine Annahme über die Zeilenhöhe kippt beim nächsten
  Streamlit-Update still. (`width` steht ohnehin schon auf `"stretch"`.)
- **Ein Aggregat muss sagen, was es NICHT enthält** (#59, 17.08.2026). Der
  Fälligkeits-Balkenchart der Portfolioanalyse zeigte nur Anleihen **mit**
  Fälligkeit, während die Kachel darüber alle zählte: bei *Muster SCHWEIZ
  Substanz* 30,89 % über Balken, die sich auf 15,35 % summieren, bei den
  ETF-Strategien gar kein Chart. Renten-ETFs und -fonds haben keine feste
  Fälligkeit — sie fielen still heraus. Wo ein Teilaggregat neben seiner
  Gesamtgröße steht, gehört die **Differenz benannt** (§10.9, dieselbe Klasse
  wie #46/B6). Prüfstein: `tests/test_portfolioanalyse.py`, Schritt 3.
- **Ein nicht gelesener Standard sieht aus wie eine Festlegung** (#63,
  18.08.2026). `.streamlit/config.toml` ist die einzige Datei hier, deren
  Fehler sich **nicht bemerkbar machen** — wird sie ignoriert, sieht die App
  aus wie eine App ohne Konfiguration. Zweimal passiert: der fehlende Punkt im
  Ordnernamen (#23) und ein **komplett fehlendes `[theme]`**, wodurch die App
  seit Projektbeginn mit Streamlits Akzentfarbe `#FF4B4B` lief. Ein Test auf
  den DATEIINHALT findet das nicht — geprüft wird die **Wirkung**:
  `config.get_where_defined("theme.primaryColor")` muss auf die Datei zeigen
  und nicht auf `<default>` (`tests/test_theme.py`, Schritt 2). Die Farben
  stehen als `THEME_AKZENT_HELL`/`-DUNKEL` in `shared.py`, damit es keine
  zwei Fassungen gibt.
- **Zahlenformate kommen aus `formats.py` — auch in Tabellen** (18.08.2026).
  `st.column_config` (NumberColumn, ProgressColumn) formatiert selbst,
  englisch oder nach der Locale des **Browsers**. Das wäre eine zweite,
  unkontrollierte Quelle. Werte deshalb als fertige Zeichenketten übergeben;
  wo ein Balken gebraucht wird, ist er aus Text gebaut
  (`strategievergleich.beitragsbalken`) — auf jedem Rechner derselbe, ohne
  CSS und auf Proportionalität prüfbar.
- **Ein Vergleichsmaß ist nur so aussagekräftig wie seine Ebene** (#62,
  18.08.2026). Überschneidung, Ähnlichkeit, Abweichung — jedes solche Maß
  hängt an der gewählten Ebene, und gröbere Kategorien liefern zwangsläufig
  höhere Werte. Dasselbe Depotpaar liest sich auf Einzeltitel-Ebene als
  **20,5 %** und auf Gattungs-Ebene als **73,8 %**. Die Ebene gehört deshalb
  an die Zahl. Zweitens: **Die Obergrenze ist selten 100 %** — die
  Titelgewichte machen nur 88,8 bis 98,2 % aus, der Rest ist Liquidität; der
  Vorbehalt wird benannt und nicht wegnormiert. Drittens: **Was verglichen
  wird, muss fest sein** — `build_allocation` bildet „Sonstige" je Strategie
  einzeln und ist deshalb für einen Vergleich nebeneinander unbrauchbar
  (dieselbe Lehre wie bei der Heatmap-Farbskala).
- **Der Marktrisikowert gehört nicht ins Beratungswerkzeug** (18.08.2026,
  Philip). Er liegt je Titel in `Daten_PF` und war als Exposure-Achse gebaut
  — das Haus legt ihn aber im Asset Management **selbst fest**, und eine
  vergebene Kennzahl sieht neben gemessenen Größen aus wie eine Beobachtung.
  Wieder ausgebaut; `tests/test_strategievergleich.py` Schritt 7 hält das
  fest, weil die Spalte in den Daten bleibt. **Ob eine Zahl in das Werkzeug
  gehört, entscheidet nicht ihre Verfügbarkeit.**
- **Ein Vergleich ist nur so ehrlich wie sein gemeinsamer Zeitraum** (#61,
  18.08.2026). Sobald mehrere Strategien NEBENEINANDER stehen, verspricht die
  Achsenbeschriftung eine gemeinsame Grundlage — und die Historien halten das
  nicht: Sie reichen von 1,7 bis 17,6 Jahren. Gemessen verschiebt das die
  Rangfolge um bis zu zehn Plätze (cVV dynamic: Rang 4 seit Auflage, Rang 14
  über drei gemeinsame Jahre). Beim **Max Drawdown** ist es schärfer, weil er
  ein Einzelereignis ist und mit der Länge der Historie wächst — ein langer
  Track Record wird dort bestraft. Deshalb: gemeinsames Fenster, und wer es
  nicht abdeckt, wird **genannt statt gezeichnet** (`strategievergleich.py`,
  Prüfstein `tests/test_strategievergleich.py` Schritt 3). Die Regel dafür
  musste nicht gebaut werden — `analytics.risiko_perioden` hatte sie schon.
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
| `modules/farben.py` | die **festen Assetklassen-Farben** und ihre Klassifizierung — **streamlit- und lxml-frei**, weil Broschüre *und* Oberfläche sie brauchen |
| `modules/risiko_ansicht.py` | Heatmap und Risiko-Block **innerhalb** der Performance-Ansicht |
| `modules/strategievergleich.py` | die dritte Ansicht: alle Strategien nebeneinander — Punktwolke, Überschneidung, Exposure |
| `modules/bestandsanalytik.py` | Mathematik auf dem **Bestand** (Gewicht je Kategorie, Überschneidung, Liquidität) — **streamlit-frei**, Gegenstück zu `analytics.py` |

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
python tests/test_kalenderjahre.py           # Schritte 1+2 nur pandas, 3 + pptx
python tests/test_monatsrenditen.py          # Schritte 1-4 nur numpy + pandas
python tests/test_risiko.py                  # Schritte 1-2+4 nur numpy + pandas
python tests/test_portfolioanalyse.py        # Schritte 1-5 pandas, 6 + streamlit
python tests/test_strategievergleich.py      # Schritte 1+4 numpy/pandas, 5 + streamlit
python tests/test_bestandsanalytik.py        # Schritt 1 ohne jedes Paket
python tests/test_theme.py                   # Schritt 1 ohne jedes Paket
python tests/test_keepalive.py               # ohne jedes Paket
python tests/test_farben.py                  # Schritt 2 ohne jedes Paket
python tests/test_quelle_position.py [<ordner>]  # + python-pptx
python tests/test_export_smoke.py <ordner>   # + python-pptx, streamlit
python tests/test_trennstriche.py <ordner>   # + python-pptx
```

Dazu ein Werkzeug, kein Test — für den Beweis nach einem UI-Umbau:

```
python tests/ui_dump.py vorher.json     # umbauen, dann nachher.json, vergleichen
python tests/ui_dump.py vorher_pf.json portfolio   # zweite Ansicht (17.08.2026)
python tests/ui_dump.py vorher_sv.json vergleich   # dritte Ansicht (18.08.2026)
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
- **Zeilenenden: LF ist Repo-Konvention — aber nur in der Ablage.** Git
  speichert überall LF (`git ls-files --eol` zeigt für jede Datei `i/lf`),
  `core.autocrlf` steht auf `true`. Der **Arbeitsbaum ist dagegen gemischt**:
  am 18.08.2026 gemessen **25 Dateien CRLF und 16 LF**, je nachdem, ob eine
  Datei zuletzt ausgecheckt oder direkt geschrieben wurde.

  Wer eine Datei bearbeitet, **behält deren vorhandene Zeilenenden bei** —
  sonst zeigt `git diff` die ganze Datei als geändert statt der drei Zeilen,
  die man wirklich angefasst hat, und die Änderung wird unprüfbar. Vorgehen:
  die Datei mit `newline=""` lesen, am gelesenen Text erkennen, ob sie
  Windows-Zeilenenden trägt, und die Suchtexte vor dem Ersetzen darauf
  umstellen. Am Commit ändert das nichts — Git normalisiert ohnehin auf LF;
  es geht allein um einen lesbaren Diff.

  Kostete am 18.08.2026 zwei fehlgeschlagene Bearbeitungen: Die Suchtexte
  trugen reine Zeilenumbrüche und trafen in einer CRLF-Datei nicht.

---

## Sprache

Code-Kommentare, Commit-Nachrichten und Dokumentation auf **Deutsch**.
Kommentare erklären das **Warum**, nicht das Was — die Doku dieses Projekts
lebt davon, dass jemand in sechs Monaten die Begründung noch findet.
