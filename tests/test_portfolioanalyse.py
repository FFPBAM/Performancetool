"""Pruefstein fuer die Portfolioanalyse-Ansicht (NEU 17.08.2026).

Die Ansicht hatte bis heute keinen eigenen Test. Beruehrt wurde sie nur am
Rand — ueber den Broschueren-Export (test_export_smoke), den Emoji-Sweep und
die Familien-Helfer. Die Anzeige selbst, also das was der Berater sieht, war
ungeprueft: Einzeltitel-Tabelle, Kennzahlen-Kacheln, Anleihen-Block.

Anlass ist das Kollegen-Feedback vom 17.08.2026 (Einzeltitel ohne Scrollbalken,
Faelligkeiten der einzelnen Anleihen) und zwei Befunde, die beim Nachmessen
dazukamen.

  1. Anzahl Titel — die Kachel zaehlte die leere CSV-Abschlusszeile mit
  2. build_faelligkeiten_tabelle gegen von Hand nachgerechnete Werte
  3. Die Zusage: Balkensumme + "ohne feste Faelligkeit" == Gewicht Anleihen
  4. Sortierung, Restlaufzeit und Grenzfaelle
  5. Statisch: die langen Tabellen tragen height="content"
  6. AppTest: die Ansicht faehrt hoch, mit und ohne Anleihen

Schritte 1-5 brauchen nur pandas (Schritt 5 gar nichts), Schritt 6 zusaetzlich
streamlit. Fehlt etwas, wird uebersprungen statt zu scheitern.

    python tests/test_portfolioanalyse.py
"""

import ast
import glob
import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

try:
    import pandas as pd
except ImportError as ex:
    print(f"UEBERSPRUNGEN — {ex}")
    sys.exit(0)

TOLERANZ = 1e-12

# Stichtag der aktuellen Lieferung. Bewusst als Konstante und nicht aus dem
# Dateinamen geraten: Wer die Daten austauscht, sieht hier, was zu pflegen ist.
STICHTAG_MUSTER = "260721"


def _pf_dateien(muster="*"):
    return sorted(glob.glob(os.path.join("Daten_PF", f"*_{muster}_*.CSV")))


def _lade(pfad):
    """Wie die App: read_pf_csv + parse_pf_data, damit derselbe Weg geprueft wird."""
    from modules.portfolioanalyse import parse_pf_data, read_pf_csv
    return parse_pf_data(read_pf_csv(pfad))


def _name(pfad):
    return os.path.basename(pfad).split("_Portfolioanalyse")[0]


# ---------------------------------------------------------------------------


def schritt1_anzahl_titel():
    """Die Kachel 'Anzahl Titel' gegen die tatsaechlichen Positionen.

    Jede der 38 CSVs endet mit einer leeren Zeile (';;;;...'). parse_pf_data
    verwirft sie nicht, und `len(df)` zaehlte sie mit — die Kachel stand
    dadurch bei JEDER Strategie um genau 1 zu hoch. Aufgefallen ist es nicht,
    weil eine Zahl wie "23" statt "22" fuer sich plausibel aussieht; erst der
    Vergleich mit den Gattungs-Tabellen darunter (die per groupby das NaN von
    selbst verwerfen) zeigt den Widerspruch.
    """
    print("Schritt 1 — Anzahl Titel zaehlt nur echte Positionen")
    from modules.portfolioanalyse import anzahl_titel

    dateien = _pf_dateien()
    if not dateien:
        print("    UEBERSPRUNGEN — keine Dateien in Daten_PF/")
        return 0

    fehler = 0
    for pfad in dateien:
        df = _lade(pfad)
        ist = anzahl_titel(df)
        soll = int(df["Wertpapier"].notna().sum())
        if ist != soll:
            print(f"    FEHLER — {_name(pfad)}: {ist} statt {soll}")
            fehler += 1
        if ist == len(df):
            # Gegenprobe: Wenn die Funktion einfach len(df) waere, faellt sie
            # hier auf — genau das war der alte Zustand.
            if df["Wertpapier"].isna().any():
                print(f"    FEHLER — {_name(pfad)}: zaehlt Leerzeilen mit "
                      f"({ist} == len(df))")
                fehler += 1

    if fehler:
        return 1
    print(f"    OK — {len(dateien)} Dateien, Titelzahl gleich der Zahl der "
          "Positionen")

    # Und die Zahl muss zu den Gattungs-Tabellen passen, die darunter stehen.
    from modules.portfolioanalyse import build_grouped_title_table
    for pfad in dateien[:5]:
        df = _lade(pfad)
        gruppen = build_grouped_title_table(df)
        zeilen = sum(len(g[2]) for g in gruppen if g[0] != "Liquidität")
        if zeilen != anzahl_titel(df):
            print(f"    FEHLER — {_name(pfad)}: Kachel {anzahl_titel(df)}, "
                  f"Tabellen zeigen {zeilen} Zeilen")
            return 1
    print("    OK — Kachel und Gattungs-Tabellen nennen dieselbe Zahl")
    return 0


def schritt2_faelligkeiten_werte():
    """build_faelligkeiten_tabelle gegen von Hand nachgerechnete Werte."""
    print("Schritt 2 — Faelligkeiten-Tabelle gegen die Rohdaten")
    from modules.portfolioanalyse import build_faelligkeiten_tabelle

    treffer = [p for p in _pf_dateien(STICHTAG_MUSTER)
               if _name(p) == "Muster defensiv cVV"]
    if not treffer:
        print("    UEBERSPRUNGEN — 'Muster defensiv cVV' nicht gefunden")
        return 0
    df = _lade(treffer[0])
    stichtag = df["Auswertungsdatum"].dropna().max()

    tab, gew_mit, gew_ohne, n_ohne = build_faelligkeiten_tabelle(df, stichtag)

    # Aus den Rohdaten unabhaengig nachgerechnet, nicht aus der Funktion.
    g = df["Gattung"].astype("object").astype(str).str.lower()
    bonds = df[g.str.contains("rente|anleihe|bond", na=False)]
    soll_n = len(bonds)
    soll_mit = float(bonds.loc[bonds["Fälligkeit_parsed"].notna(),
                               "Gewicht"].sum())
    soll_ohne = float(bonds.loc[bonds["Fälligkeit_parsed"].isna(),
                                "Gewicht"].sum())

    fehler = 0
    if len(tab) != soll_n:
        print(f"    FEHLER — {len(tab)} Zeilen statt {soll_n}")
        fehler += 1
    if abs(gew_mit - soll_mit) > TOLERANZ:
        print(f"    FEHLER — Gewicht mit Faelligkeit {gew_mit} statt {soll_mit}")
        fehler += 1
    if abs(gew_ohne - soll_ohne) > TOLERANZ:
        print(f"    FEHLER — Gewicht ohne Faelligkeit {gew_ohne} statt {soll_ohne}")
        fehler += 1
    if n_ohne != int(bonds["Fälligkeit_parsed"].isna().sum()):
        print(f"    FEHLER — Anzahl ohne Faelligkeit {n_ohne}")
        fehler += 1

    # Die erste Zeile muss die frueheste Faelligkeit tragen.
    frueheste = bonds["Fälligkeit_parsed"].min()
    from modules.formats import fmt_date_de
    if tab.iloc[0]["Fälligkeit"] != fmt_date_de(frueheste):
        print(f"    FEHLER — erste Zeile {tab.iloc[0]['Fälligkeit']!r}, "
              f"frueheste ist {fmt_date_de(frueheste)}")
        fehler += 1

    if fehler:
        return 1
    print(f"    OK — {soll_n} Anleihen, {soll_mit:.4%} mit Faelligkeit, "
          f"{soll_ohne:.4%} ohne")
    return 0


def schritt3_zusage_gewichte():
    """Die eigentliche Zusage, ueber ALLE Strategien.

    Vor dem 17.08.2026 zeigte der Balkenchart nur die Anleihen MIT Faelligkeit,
    waehrend die Kachel darueber alle zaehlte. Bei 'Muster SCHWEIZ Substanz'
    standen so 30,89 % ueber Balken, die sich auf 15,35 % summieren — ohne ein
    Wort dazu. Diese Pruefung nagelt fest, dass beide Groessen zusammen wieder
    das Gesamtgewicht ergeben; die Anzeige kann die Luecke damit benennen.
    """
    print("Schritt 3 — Balkensumme + ohne Faelligkeit == Gewicht Anleihen")
    from modules.portfolioanalyse import build_faelligkeiten_tabelle, get_bond_summary

    dateien = _pf_dateien(STICHTAG_MUSTER)
    if not dateien:
        print("    UEBERSPRUNGEN — keine Dateien zum Stichtag")
        return 0

    fehler = 0
    mit_luecke = 0
    geprueft = 0
    for pfad in dateien:
        df = _lade(pfad)
        summary = get_bond_summary(df)
        if summary is None:
            continue
        geprueft += 1
        stichtag = df["Auswertungsdatum"].dropna().max()
        _, gew_mit, gew_ohne, _ = build_faelligkeiten_tabelle(df, stichtag)

        if abs((gew_mit + gew_ohne) - summary["total_weight"]) > TOLERANZ:
            print(f"    FEHLER — {_name(pfad)}: {gew_mit} + {gew_ohne} != "
                  f"{summary['total_weight']}")
            fehler += 1
        if abs(summary["gewicht_ohne_faelligkeit"] - gew_ohne) > TOLERANZ:
            print(f"    FEHLER — {_name(pfad)}: get_bond_summary meldet "
                  f"{summary['gewicht_ohne_faelligkeit']}, Tabelle {gew_ohne}")
            fehler += 1

        # Und die Balken selbst muessen sich auf gew_mit summieren.
        if summary["faelligkeit"] is not None:
            balken = float(summary["faelligkeit"]["Gewicht"].sum())
            if abs(balken - gew_mit) > TOLERANZ:
                print(f"    FEHLER — {_name(pfad)}: Balken {balken} != "
                      f"Tabelle {gew_mit}")
                fehler += 1
        elif gew_mit > TOLERANZ:
            print(f"    FEHLER — {_name(pfad)}: kein Chart, aber {gew_mit} "
                  "mit Faelligkeit")
            fehler += 1

        if gew_ohne > TOLERANZ:
            mit_luecke += 1
            print(f"    {_name(pfad):32s} {summary['total_weight']:7.2%} "
                  f"Anleihen, davon {gew_ohne:7.2%} ohne feste Faelligkeit")

    if fehler:
        return 1
    print(f"    OK — {geprueft} Strategien mit Anleihen, {mit_luecke} davon "
          "mit Titeln ohne feste Faelligkeit")
    return 0


def schritt4_sortierung_und_grenzfaelle():
    print("Schritt 4 — Sortierung, Restlaufzeit, Grenzfaelle")
    from modules.portfolioanalyse import build_faelligkeiten_tabelle
    fehler = 0

    def _mach_df(zeilen):
        return pd.DataFrame(zeilen)

    stichtag = pd.Timestamp("2026-07-21")

    # Sortierung: aufsteigend, ohne Faelligkeit ans Ende — unabhaengig davon,
    # in welcher Reihenfolge die Zeilen ankommen.
    df = _mach_df([
        {"Wertpapier": "C", "Gattung": "Renten", "Gewicht": 0.03,
         "Fälligkeit_parsed": pd.Timestamp("2031-01-01"), "Kupon": 0.02,
         "Duration": 4.0, "Rendite": 0.03},
        {"Wertpapier": "OHNE", "Gattung": "Renten", "Gewicht": 0.05,
         "Fälligkeit_parsed": pd.NaT, "Kupon": 0.0,
         "Duration": float("nan"), "Rendite": float("nan")},
        {"Wertpapier": "A", "Gattung": "Renten", "Gewicht": 0.01,
         "Fälligkeit_parsed": pd.Timestamp("2027-03-15"), "Kupon": 0.01,
         "Duration": 0.6, "Rendite": 0.025},
        {"Wertpapier": "Aktie", "Gattung": "Aktien", "Gewicht": 0.40,
         "Fälligkeit_parsed": pd.NaT, "Kupon": 0.0,
         "Duration": float("nan"), "Rendite": float("nan")},
    ])
    tab, gew_mit, gew_ohne, n_ohne = build_faelligkeiten_tabelle(df, stichtag)
    namen = list(tab["Wertpapier"])
    if namen != ["A", "C", "OHNE"]:
        print(f"    FEHLER — Reihenfolge {namen}, erwartet ['A','C','OHNE']")
        fehler += 1
    else:
        print("    OK — aufsteigend, ohne Faelligkeit am Ende, Aktie nicht dabei")
    if abs(gew_mit - 0.04) > 1e-9 or abs(gew_ohne - 0.05) > 1e-9 or n_ohne != 1:
        print(f"    FEHLER — Gewichte {gew_mit}/{gew_ohne}, n_ohne {n_ohne}")
        fehler += 1

    # Restlaufzeit gegen den Stichtag nachgerechnet: 15.03.2027 - 21.07.2026
    # sind 237 Tage = 0,6489... Jahre -> "0,6"
    if tab.iloc[0]["Restlaufzeit"] != "0,6 J.":
        print(f"    FEHLER — Restlaufzeit {tab.iloc[0]['Restlaufzeit']!r}, "
              "erwartet '0,6 J.'")
        fehler += 1
    else:
        print("    OK — Restlaufzeit gegen den Stichtag gerechnet")

    # Fehlwerte werden zum Gedankenstrich, niemals zu 'nan'/'None'/'NaT'.
    letzte = tab.iloc[-1]
    for spalte in ("Fälligkeit", "Restlaufzeit", "Duration", "Rendite"):
        if str(letzte[spalte]) in ("nan", "None", "NaT", "0,00"):
            print(f"    FEHLER — {spalte} zeigt {letzte[spalte]!r} statt '–'")
            fehler += 1

    # Grenzfaelle: keine Anleihen, alles ohne Faelligkeit, leeres DataFrame
    nur_aktien = _mach_df([{"Wertpapier": "X", "Gattung": "Aktien",
                            "Gewicht": 1.0, "Fälligkeit_parsed": pd.NaT,
                            "Kupon": 0.0, "Duration": float("nan"),
                            "Rendite": float("nan")}])
    tab2, m2, o2, n2 = build_faelligkeiten_tabelle(nur_aktien, stichtag)
    if len(tab2) or m2 or o2 or n2:
        print(f"    FEHLER — ohne Anleihen: {len(tab2)} Zeilen, {m2}/{o2}/{n2}")
        fehler += 1
    else:
        print("    OK — ohne Anleihen leer statt Absturz")

    leer = pd.DataFrame(columns=["Wertpapier", "Gattung", "Gewicht",
                                 "Fälligkeit_parsed", "Kupon", "Duration",
                                 "Rendite"])
    try:
        tab3, *_ = build_faelligkeiten_tabelle(leer, stichtag)
        if len(tab3):
            print(f"    FEHLER — leeres DataFrame ergab {len(tab3)} Zeilen")
            fehler += 1
        else:
            print("    OK — leeres DataFrame liefert leere Tabelle")
    except Exception as ex:
        print(f"    FEHLER — leeres DataFrame wirft {type(ex).__name__}: {ex}")
        fehler += 1

    # Ohne Stichtag darf die Restlaufzeit fehlen, aber nichts abstuerzen.
    try:
        tab4, *_ = build_faelligkeiten_tabelle(df, None)
        if "Restlaufzeit" in tab4.columns and tab4.iloc[0]["Restlaufzeit"] != "–":
            print("    FEHLER — ohne Stichtag steht eine Restlaufzeit da")
            fehler += 1
        else:
            print("    OK — ohne Stichtag keine Restlaufzeit, kein Absturz")
    except Exception as ex:
        print(f"    FEHLER — ohne Stichtag wirft {type(ex).__name__}: {ex}")
        fehler += 1

    return 1 if fehler else 0


def schritt5_tabellenhoehe():
    """Statisch: die langen Tabellen tragen height="content".

    Streamlits Vorgabe ist height="auto" und bedeutet laut Quelltext "zeigt
    hoechstens zehn Zeilen" — danach entsteht ein Scrollbalken INNERHALB der
    Tabelle. Genau das haben die Kollegen gemeldet. Der Parameter ist
    unscheinbar; ohne diese Pruefung faellt es beim naechsten Umbau niemandem
    auf, wenn er wieder verschwindet.

    Geprueft wird der Quelltext (AST) und nicht die gerenderte Seite: Die
    Elementhoehe ist ueber AppTest nicht zuverlaessig auslesbar.
    """
    print("Schritt 5 — lange Tabellen tragen height=\"content\"")
    quelle = os.path.join("modules", "portfolioanalyse.py")
    baum = ast.parse(open(quelle, encoding="utf-8").read())

    ohne = []
    gefunden = 0
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Call):
            continue
        ziel = knoten.func
        if not (isinstance(ziel, ast.Attribute) and ziel.attr == "dataframe"):
            continue
        schluessel = {kw.arg: kw.value for kw in knoten.keywords}
        key = schluessel.get("key")
        # Nur die Tabellen, die lang werden koennen: Einzeltitel je Gattung
        # und die Faelligkeiten. Top/Flop 5 haben immer fuenf Zeilen.
        if not isinstance(key, ast.JoinedStr):
            continue
        text = ast.unparse(key)
        if not ("tbl_" in text or "faell_tab" in text):
            continue
        gefunden += 1
        hoehe = schluessel.get("height")
        if not (isinstance(hoehe, ast.Constant) and hoehe.value == "content"):
            ohne.append(f"{text} (Zeile {knoten.lineno})")

    if not gefunden:
        print(f"    FEHLER — keine lange Tabelle in {quelle} gefunden")
        return 1
    if ohne:
        print(f"    FEHLER — {len(ohne)} Tabelle(n) ohne height=\"content\":")
        for o in ohne:
            print(f"      ! {o}")
        print("    Ohne den Parameter zeigt Streamlit hoechstens zehn Zeilen.")
        return 1
    print(f"    OK — {gefunden} lange Tabelle(n), alle mit height=\"content\"")
    return 0


def schritt6_apptest():
    """Die Ansicht an der gerenderten Oberflaeche, drei Faelle.

    ACHTUNG bei der Strategie-Auswahl: `pf_sel_1` traegt ANZEIGENAMEN
    ("cVV defensiv"), nicht die CSV-Namen ("Muster defensiv cVV"). Genau diese
    Verwechslung liess am 14.08.2026 sechs AppTest-Faelle zwei Runden lang
    gegen die Standardstrategie laufen — gruen, aber blind. Beim Bau dieses
    Schrittes ist sie prompt wieder passiert. Deshalb wird hier erzwungen,
    dass die Auswahl WIRKT: Ist der Name nicht waehlbar oder kommt er nicht
    an, ist das ein Fehler und kein Hinweis.
    """
    print("Schritt 6 — Portfolioanalyse an der gerenderten Oberflaeche")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — {ex}")
        return 0

    # (Anzeigename, Beschreibung, erwartet Anleihen?, erwartet Faelligkeiten?)
    faelle = [
        ("cVV defensiv", "alle Anleihen mit Faelligkeit", True, True),
        ("Pro", "ohne Anleihen", False, False),
        ("ETF_ausgewogen", "Anleihen, aber keine feste Faelligkeit", True, False),
    ]
    fehler = 0
    for name, was, hat_anleihen, hat_faelligkeit in faelle:
        at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                               default_timeout=400)
        at.secrets["passwords"] = {"t": "t"}
        at.session_state["logged_in"] = True
        at.session_state["username"] = "t"
        at.session_state["nav_view"] = "Portfolioanalyse"
        at.run()
        if at.exception:
            print(f"    FEHLER — {name}: {str(at.exception[0].value)[:200]}")
            fehler += 1
            continue

        auswahl = next((s for s in at.selectbox if s.key == "pf_sel_1"), None)
        if auswahl is None:
            print("    FEHLER — kein Auswahlfeld 'pf_sel_1'")
            return 1
        if name not in list(auswahl.options):
            print(f"    FEHLER — {name!r} steht nicht zur Auswahl "
                  f"(vorhanden: {list(auswahl.options)})")
            fehler += 1
            continue
        auswahl.set_value(name).run()
        if at.exception:
            print(f"    FEHLER — {name}: {str(at.exception[0].value)[:200]}")
            fehler += 1
            continue
        if at.session_state["pf_sel_1"] != name:
            print(f"    FEHLER — Auswahl kam nicht an: "
                  f"{at.session_state['pf_sel_1']!r} statt {name!r}")
            fehler += 1
            continue

        kacheln = {m.label: m.value for m in at.metric}
        markdown = [m.value.strip() for m in at.markdown]
        captions = [c.value for c in at.caption]
        anleihen_da = "Anzahl Anleihen" in kacheln
        # EXAKT die Ueberschrift, nicht "enthaelt das Wort": Der erklaerende
        # Satz unter dem fehlenden Chart lautet "... keine Fälligkeitsstruktur"
        # und enthaelt damit denselben Begriff. Eine Teilstring-Suche meldete
        # deshalb einen Chart, wo gerade dessen Fehlen erklaert wird (beim Bau
        # passiert, 17.08.2026).
        chart_da = "**Fälligkeitsstruktur**" in markdown
        liste_da = "**Einzelne Fälligkeiten**" in markdown

        if "Anzahl Titel" not in kacheln:
            print(f"    FEHLER — {name}: keine Kachel 'Anzahl Titel'")
            fehler += 1
            continue
        if anleihen_da != hat_anleihen:
            print(f"    FEHLER — {name}: Anleihen-Block {anleihen_da}, "
                  f"erwartet {hat_anleihen}")
            fehler += 1
            continue
        if chart_da != hat_faelligkeit:
            print(f"    FEHLER — {name}: Fälligkeitsstruktur {chart_da}, "
                  f"erwartet {hat_faelligkeit}")
            fehler += 1
            continue
        # Wo Anleihen sind, muss die Liste stehen — auch dann, wenn KEINE
        # von ihnen eine feste Faelligkeit hat. Genau dort war bisher eine
        # unerklaerte Leerstelle.
        if anleihen_da and not liste_da:
            print(f"    FEHLER — {name}: Anleihen, aber keine Liste "
                  "'Einzelne Fälligkeiten'")
            fehler += 1
            continue
        if anleihen_da and not hat_faelligkeit:
            erklaert = any("feste Fälligkeit" in c for c in captions)
            if not erklaert:
                print(f"    FEHLER — {name}: kein Chart und kein erklaerender "
                      "Satz dazu")
                fehler += 1
                continue

        print(f"    OK — {name} ({was}): Anzahl Titel "
              f"{kacheln['Anzahl Titel']}, Anleihen-Block {anleihen_da}, "
              f"Chart {chart_da}, Liste {liste_da}")

    return 1 if fehler else 0



# ──────────────────────────────────────────────────────────────────────────────

def schritt7_beitrag_figur():
    """Die FIGUR des Beitrags-Charts (#54).

    Nicht "sieht gut aus", sondern die Eigenschaften, deren Fehlen schon
    einmal etwas kaputt gemacht hat: geratene Achsentypen, die verkehrte
    Balkenreihenfolge und ein fest genagelter linker Rand, der lange Namen
    abschneidet.
    """
    print("Schritt 7 — die Figur des Beitrags-Charts")
    try:
        from modules.portfolioanalyse import (
            build_beitrag_bar_chart, beitrag_chart_hoehe,
            BEITRAG_BALKEN_HOEHE_PX,
        )
        from modules.bestandsanalytik import performancebeitrag_je_kategorie
        from modules.shared import HEATMAP_GRUEN, HEATMAP_ROT
    except ImportError as ex:
        # Ein fehlendes SYMBOL ist ein Fehler in der Sache, kein
        # Umgebungsproblem — deshalb FEHLER und nicht UEBERSPRUNGEN (#65).
        print(f"    FEHLER — ein Symbol fehlt: {ex}")
        return 1

    f = 0
    if build_beitrag_bar_chart(pd.Series(dtype=float), "leer") is not None:
        print("    FEHLER — die leere Reihe liefert eine Figur statt None")
        f += 1
    else:
        print("    OK — die leere Reihe liefert None")

    # *cVV ausgewogen* traegt unter Aktien BEIDE Vorzeichen — der Fall, den
    # eine einfarbige Fassung nicht unterscheiden koennte.
    pfade = [x for x in _pf_dateien() if _name(x) == "Muster ausgewogen cVV"]
    if not pfade:
        print("    FEHLER — Muster ausgewogen cVV nicht gefunden")
        return f + 1
    df = _lade(sorted(pfade)[-1])
    reihe, _ohne, _n = performancebeitrag_je_kategorie(df, "Segment", "Aktien")
    if len(reihe) < 2 or not (min(reihe) < 0 < max(reihe)):
        print(f"    FEHLER — Testfall taugt nicht: {len(reihe)} Segmente")
        return f + 1

    fig = build_beitrag_bar_chart(reihe, "Test")
    namen = [str(k) for k in reihe.index]

    pruefungen = [
        ("x-Achse ist linear", fig.layout.xaxis.type, "linear"),
        ("y-Achse ist category", fig.layout.yaxis.type, "category"),
        ("Reihenfolge umgekehrt gesetzt",
         list(fig.layout.yaxis.categoryarray), list(reversed(namen))),
        ("cliponaxis ist False", fig.data[0].cliponaxis, False),
        ("automargin ist an", fig.layout.yaxis.automargin, True),
        # Der linke Rand DARF NICHT fest sein, sonst kann Plotly ihn nicht
        # fuer "Banken,Versicherer,Finanzdienstl." (33 Zeichen) aufweiten.
        ("kein fester linker Rand", fig.layout.margin.l, None),
        ("keine Legende", fig.layout.showlegend, False),
        ("deutsche Trennzeichen", fig.layout.separators, ",."),
        ("ein Balken je Segment", len(fig.data[0].x), len(namen)),
    ]
    for bez, ist, soll in pruefungen:
        if ist != soll:
            print(f"    FEHLER — {bez}: {ist!r} statt {soll!r}")
            f += 1
    if not f:
        print(f"    OK — {len(pruefungen)} Eigenschaften der Figur stimmen")

    # Farbe folgt dem VORZEICHEN, nicht dem Rang.
    farben = list(fig.data[0].marker.color)
    soll_farben = [HEATMAP_GRUEN if float(v) >= 0 else HEATMAP_ROT
                   for v in reihe.values]
    if farben != soll_farben:
        print(f"    FEHLER — Farben folgen nicht dem Vorzeichen: {farben}")
        f += 1
    else:
        print(f"    OK — {soll_farben.count(HEATMAP_ROT)} negative Balken in "
              "Terrakotta, der Rest in Salbeigruen")

    # Der Platz fuer die aussen liegenden Beschriftungen muss auf BEIDEN
    # Seiten da sein. Ohne das wird die Zahl des negativsten Balkens am
    # linken Rand abgeschnitten — am Figur-Objekt unsichtbar, am Bild nicht.
    von, bis = fig.layout.xaxis.range
    werte = [float(v) * 100.0 for v in reihe.values]
    if not (von < min(werte) and bis > max(werte)):
        print(f"    FEHLER — die Achse laesst keinen Platz aussen: "
              f"[{von}, {bis}] gegen {min(werte)}..{max(werte)}")
        f += 1
    else:
        print("    OK — die Achse laesst auf beiden Seiten Platz")

    # Die Hoehe waechst mit der Zahl der Balken, und zwar um genau einen
    # Balken je Balken. Eine feste Hoehe hat im Strategievergleich schon
    # einmal zwei fette Kloetze erzeugt.
    if (beitrag_chart_hoehe(9) - beitrag_chart_hoehe(8)
            != BEITRAG_BALKEN_HOEHE_PX):
        print("    FEHLER — die Hoehe waechst nicht um einen Balken je Balken")
        f += 1
    elif fig.layout.height != beitrag_chart_hoehe(len(namen)):
        print(f"    FEHLER — Hoehe {fig.layout.height} statt "
              f"{beitrag_chart_hoehe(len(namen))}")
        f += 1
    else:
        print(f"    OK — Hoehe {fig.layout.height} px fuer {len(namen)} Balken")

    return f


def schritt8_beitrag_apptest():
    """Der Segment-Block an der gerenderten Oberflaeche.

    Der interessante Fall ist NICHT, dass der Block erscheint, sondern der
    Wechsel zu einer Strategie OHNE Aktien: `cVV konservativ` fuehrt nur
    Renten und Edelmetalle. Bliebe dort "Aktien" stehen, waere das genau der
    Fehler, gegen den der Kennungs-Key gebaut ist (#66).
    """
    print("Schritt 8 — der Segment-Block in der Oberflaeche")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — {ex}")
        return 0

    UEBERSCHRIFT = "Performancebeitrag je Segment (YTD)"

    def _lauf(strategie, ytd):
        at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                               default_timeout=400)
        at.secrets["passwords"] = {"t": "t"}
        at.session_state["logged_in"] = True
        at.session_state["username"] = "t"
        at.session_state["nav_view"] = "Portfolioanalyse"
        at.session_state["pf_show_ytd"] = ytd
        at.run()
        if at.exception:
            return at, str(at.exception[0].value)[:200]
        auswahl = next((x for x in at.selectbox if x.key == "pf_sel_1"), None)
        if auswahl is None or strategie not in list(auswahl.options):
            return at, f"{strategie!r} steht nicht zur Auswahl"
        auswahl.set_value(strategie).run()
        if at.exception:
            return at, str(at.exception[0].value)[:200]
        return at, None

    f = 0

    # (a) Ohne den Haken darf der Block NICHT da sein.
    at, fehler = _lauf("cVV ausgewogen", False)
    if fehler:
        print(f"    FEHLER — ohne Haken: {fehler}")
        f += 1
    elif any(UEBERSCHRIFT in m.value for m in at.markdown):
        print("    FEHLER — der Block erscheint, obwohl der Haken aus ist")
        f += 1
    else:
        print("    OK — ohne den YTD-Haken bleibt der Block weg")

    # (b) Mit Haken erscheint er, und die Gattungen stehen zur Wahl.
    at, fehler = _lauf("cVV ausgewogen", True)
    if fehler:
        print(f"    FEHLER — mit Haken: {fehler}")
        return f + 1
    if not any(UEBERSCHRIFT in m.value for m in at.markdown):
        print("    FEHLER — der Block fehlt, obwohl der Haken gesetzt ist")
        return f + 1
    feld = next((x for x in at.selectbox
                 if x.key.startswith("pf_beitrag_gattung_pf1_")), None)
    if feld is None:
        print("    FEHLER — kein Gattungsfeld")
        return f + 1
    if set(feld.options) != {"Aktien", "Renten", "Edelmetalle"}:
        print(f"    FEHLER — Gattungen {list(feld.options)} statt "
              "Aktien/Renten/Edelmetalle")
        f += 1
    else:
        print(f"    OK — der Block ist da, Gattungen {sorted(feld.options)}")

    # (c) Edelmetalle hat GENAU EIN Segment -> ein Satz statt eines Balkens.
    feld.set_value("Edelmetalle").run()
    if at.exception:
        print(f"    FEHLER — Edelmetalle: {str(at.exception[0].value)[:200]}")
        f += 1
    else:
        satz = [c.value for c in at.caption if "nur ein Segment" in c.value]
        if not satz:
            print("    FEHLER — bei einem Segment fehlt der Ersatzsatz")
            f += 1
        else:
            print("    OK — bei einem Segment steht ein Satz statt eines Balkens")

    # (d) DER EIGENTLICHE FALL: eine Strategie ohne Aktien.
    at, fehler = _lauf("cVV konservativ", True)
    if fehler:
        print(f"    FEHLER — cVV konservativ: {fehler}")
        return f + 1
    feld = next((x for x in at.selectbox
                 if x.key.startswith("pf_beitrag_gattung_pf1_")), None)
    if feld is None:
        print("    FEHLER — kein Gattungsfeld bei cVV konservativ")
        return f + 1
    if "Aktien" in list(feld.options):
        print(f"    FEHLER — cVV konservativ bietet Aktien an: "
              f"{list(feld.options)}")
        f += 1
    elif feld.value not in list(feld.options):
        print(f"    FEHLER — gewaehlt ist {feld.value!r}, waehlbar sind "
              f"{list(feld.options)}")
        f += 1
    else:
        print(f"    OK — cVV konservativ zeigt {sorted(feld.options)}, "
              f"gewaehlt {feld.value!r}")

    return f


def main():
    print("Pruefstein: Portfolioanalyse-Ansicht\n")
    fehler = 0
    for schritt in (schritt1_anzahl_titel, schritt2_faelligkeiten_werte,
                    schritt3_zusage_gewichte, schritt4_sortierung_und_grenzfaelle,
                    schritt5_tabellenhoehe, schritt6_apptest,
                    schritt7_beitrag_figur, schritt8_beitrag_apptest):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — Titelzahl, Faelligkeiten und Tabellenhoehe stimmen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
