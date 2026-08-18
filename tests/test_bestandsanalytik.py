"""Pruefstein fuer die Bestands-Mathematik (NEU 18.08.2026).

`modules/bestandsanalytik.py` rechnet auf den EINZELTITELN eines Stichtags:
Gewicht je Kategorie, Ueberschneidung zweier Depots, Liquiditaet. Es ist
bewusst streamlit-frei, damit genau dieser Pruefstein ohne Oberflaeche laeuft.

DREI ZUSAGEN, und keine davon ist die Formel selbst:

  A) DIE SUMME STIMMT MIT DER LIQUIDITAET ZUSAMMEN. Fuer jede Strategie gilt
     `Summe der Kategoriegewichte + calc_liquidity == 1`. Bricht das, zeigt
     der Exposure-Balken eine Vollinvestition, die es nicht gibt (#59) — oder
     er zaehlt etwas doppelt.

  B) DIE LEERE SCHLUSSZEILE ZAEHLT NICHT MIT. Jede CSV in `Daten_PF` endet
     mit einer Zeile ohne Werte. Am 17.08.2026 stand "Anzahl Titel" deshalb
     bei 38 von 38 Dateien um genau 1 zu hoch. Derselbe Fehler in einer
     Kategorie-Aggregation waere eine eigene Kategorie namens "nan".

  C) `ueberlappung(a, a)` IST DIE SUMME VON `a` UND NICHT 1,0. Das ist die
     knappste Formulierung des Vorbehalts, der in der Oberflaeche als Satz
     steht: Die Titelgewichte machen nur 90 bis 98 % aus, der Rest ist
     Liquiditaet und gehoert keinem gemeinsamen Titel.

  1. `ueberlappung` gegen von Hand gerechnete Faelle und Grenzfaelle
  2. `gewichte_je_kategorie` an den echten Dateien — mit Gegenprobe
  3. Symmetrie, Selbstueberschneidung und drei namentlich festgelegte Paare
  4. `gemeinsame_titel`: die Aufstellung summiert sich zur Uebersicht

SCHRITT 4 HAELT DIE ZUSAGE DES DRILLDOWNS. Die Uebersicht sagt, DASS zwei
Depots zu 69,56 % dasselbe halten; die Aufstellung sagt, WORAUS. Beide Zahlen
muessen exakt zusammenpassen — sonst stehen in einer Ansicht zwei
verschiedene Wahrheiten uebereinander. Geprueft ueber alle Paare und alle
fuenf Ebenen.

WARUM SCHRITT 2 EINE GEGENPROBE HAT: Fuer ein neues Modul gibt es keinen
alten Stand, auf dem der Test rot waere. Ersatzweise wird die NAIVE Fassung
nachgestellt — roh nach der Spalte gruppieren, ohne aufzuraeumen — und
verlangt, dass sie bei JEDER Datei eine Kategorie mehr findet. Taete sie das
nicht, pruefte Schritt 2 nichts (CLAUDE.md, Regel 2).

Die naive Fassung braucht dafuer ausdruecklich `dropna=False`, und das ist
selbst ein Befund: pandas 3.0 wirft NA-Schluessel beim groupby von sich aus
weg. Die leere Schlusszeile faellt im Standardpfad also durch das WERKZEUG
und nicht, weil jemand sie behandelt haette — ein Schutz, auf den man sich
nicht verlassen sollte, weil er beim naechsten Versionswechsel wieder
verschwinden kann (#20).

Schritt 1 braucht nur pandas/numpy. Schritte 2 und 3 lesen die echten CSVs;
der Loader dafuer haengt an `portfolioanalyse` und damit an streamlit — fehlt
es, wird uebersprungen statt zu scheitern.

    python tests/test_bestandsanalytik.py
"""

import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

try:
    import numpy as np
    import pandas as pd
except ImportError as ex:
    print(f"UEBERSPRUNGEN — {ex}")
    sys.exit(0)

from modules.bestandsanalytik import (  # noqa: E402
    calc_liquidity, gemeinsame_schluessel, gemeinsame_titel,
    gewichte_je_kategorie, kategorien_vereinigt, ueberlappung,
)

TOLERANZ = 1e-12

# Drei Paare, am 18.08.2026 an den echten Bestaenden gemessen und HIER
# NAMENTLICH festgelegt. Wer die Bestandsdaten austauscht, sieht hier eine
# Abweichung und entscheidet bewusst — statt dass sich eine Zahl still
# verschiebt, die in der Doku als Beispiel steht.
BEKANNTE_PAARE = [
    # (Strategie A, Strategie B, Anteil, gemeinsame Titel)
    ("cVV ausgewogen", "cVV defensiv plus", 0.69564, 22),
    ("cVV dynamic",    "Comdirect_100",     0.44982, 13),
    ("cVV ausgewogen", "Comdirect_100",     0.20530,  5),
]
# Die Werte sind EXAKT und nicht gerundet. Beim ersten Lauf standen hier
# 0,696 und 0,450 aus einer gerundeten Ausgabe — der Test schlug an, und das
# war richtig so: Ein Sollwert, der aus der Anzeige abgeschrieben ist, traegt
# eine Unschaerfe, die niemand begruenden kann (#58).


def _nah(bezeichnung, ist, soll, toleranz=TOLERANZ):
    if ist is None or (isinstance(ist, float) and np.isnan(ist)):
        print(f"    FEHLER — {bezeichnung}: Fehlwert statt {soll}")
        return 1
    if abs(float(ist) - float(soll)) <= toleranz:
        print(f"    OK — {bezeichnung} = {float(ist):.10g}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {float(ist):.10g} statt {float(soll):.10g}")
    return 1


def _bestand(paare, spalte="WKN"):
    """Kleiner Bestand aus (Schluessel, Gewicht)-Paaren."""
    return pd.DataFrame({spalte: [p[0] for p in paare],
                         "Gewicht": [p[1] for p in paare]})


def _echte_bestaende():
    """{Anzeigename: Bestand} fuer den neuesten Stichtag, oder None."""
    try:
        from modules.shared import (DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS,
                                    build_name_lookups, detect_newest_date_tag,
                                    load_name_mapping)
        from modules.portfolioanalyse import build_pf_data, load_pf_csvs
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return None
    tag = detect_newest_date_tag(DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS)
    dateien = load_pf_csvs(DATA_FOLDER_PF, tag)
    if not dateien:
        print("    UEBERSPRUNGEN — keine Bestandsdateien gefunden")
        return None
    roh = build_pf_data(dateien)
    namen, d2c, _ = build_name_lookups(load_name_mapping(), set(roh.keys()))
    return {n: roh[d2c[n]] for n in namen}


# ─────────────────────────────────────────────────────────────────────────────

def schritt1_ueberlappung():
    print("Schritt 1 — `ueberlappung` gegen von Hand gerechnete Faelle")
    f = 0

    a = gewichte_je_kategorie(_bestand([("A", 0.30), ("B", 0.20), ("C", 0.10)]), "WKN")
    b = gewichte_je_kategorie(_bestand([("A", 0.10), ("B", 0.40), ("D", 0.25)]), "WKN")

    # min(0,30;0,10) + min(0,20;0,40) = 0,10 + 0,20 = 0,30
    f += _nah("Teilmenge mit unterschiedlichen Gewichten", ueberlappung(a, b), 0.30)
    f += _nah("symmetrisch", ueberlappung(b, a), 0.30)

    # C) Selbstueberschneidung ist die SUMME, nicht 1,0. Der Bestand oben
    # wiegt 0,60 — die uebrigen 0,40 waeren Liquiditaet.
    f += _nah("u(a,a) == Summe von a (NICHT 1,0)", ueberlappung(a, a), 0.60)

    disjunkt = gewichte_je_kategorie(_bestand([("X", 0.5), ("Y", 0.5)]), "WKN")
    f += _nah("disjunkte Depots", ueberlappung(a, disjunkt), 0.0)

    ein_titel = gewichte_je_kategorie(_bestand([("A", 0.99)]), "WKN")
    f += _nah("ein gemeinsamer Titel, kleineres Gewicht zaehlt",
              ueberlappung(a, ein_titel), 0.30)

    # DOPPELT GEFUEHRTER TITEL wird summiert, bevor verglichen wird. Ohne das
    # zaehlte ein zweimal auftauchender Titel nur mit einer seiner Zeilen.
    doppelt = gewichte_je_kategorie(
        _bestand([("A", 0.15), ("A", 0.15), ("B", 0.20)]), "WKN")
    f += _nah("doppelt gefuehrter Titel wird summiert", float(doppelt.loc["A"]), 0.30)
    f += _nah("und zaehlt dann voll", ueberlappung(a, doppelt), 0.50)

    # GRENZFAELLE — kein Absturz, sondern 0.0 (CLAUDE.md).
    leer = pd.Series(dtype=float)
    for bez, x, y in (("beide leer", leer, leer), ("eine leer", a, leer),
                      ("None", a, None)):
        try:
            wert = ueberlappung(x, y)
        except Exception as ex:
            print(f"    FEHLER — {bez}: {type(ex).__name__}: {ex}")
            f += 1
            continue
        f += _nah(bez, wert, 0.0)
    f += _nah("gemeinsame Schluessel bei leer", gemeinsame_schluessel(a, leer), 0)

    # NaN-GEWICHTE fallen heraus, statt die Summe zu vergiften.
    mit_nan = _bestand([("A", 0.30), ("B", float("nan"))])
    g = gewichte_je_kategorie(mit_nan, "WKN")
    f += _nah("NaN-Gewicht faellt heraus", g.sum(), 0.30)

    # FEHLENDE SPALTE -> leere Series statt Absturz.
    if len(gewichte_je_kategorie(_bestand([("A", 1.0)]), "GibtEsNicht")):
        print("    FEHLER — fehlende Spalte liefert Werte")
        f += 1
    else:
        print("    OK — fehlende Spalte liefert eine leere Reihe")
    return f


def schritt2_echte_dateien():
    print("Schritt 2 — `gewichte_je_kategorie` an den echten Bestaenden")
    bestaende = _echte_bestaende()
    if bestaende is None:
        return 0
    f = 0

    # A) Kategoriegewichte + Liquiditaet == 1, fuer JEDE Strategie und JEDE
    # Ebene. Das ist die Zusage, auf der der Exposure-Balken steht.
    schlimmste = 0.0
    for spalte in ("Gattung", "Region", "Segment", "Währung"):
        for name, df in bestaende.items():
            summe = float(gewichte_je_kategorie(df, spalte).sum())
            gesamt = summe + calc_liquidity(df)
            # "ohne Angabe" gibt es bei diesen vier Spalten nicht — sonst
            # waere `gesamt` kleiner als 1 und der Balken haette eine Luecke.
            schlimmste = max(schlimmste, abs(gesamt - 1.0))
            if abs(gesamt - 1.0) > 1e-9:
                print(f"    FEHLER — {name}/{spalte}: Summe + Liquiditaet "
                      f"= {gesamt:.6f}")
                f += 1
    if not f:
        print(f"    OK — {len(bestaende)} Strategien x 4 Ebenen: Summe plus "
              f"Liquiditaet trifft 1,0 (groesste Abweichung {schlimmste:.2e})")

    # B) KEINE "nan"-KATEGORIE, nirgends.
    schmutz = []
    for spalte in ("WKN", "Gattung", "Region", "Segment", "Währung"):
        for name, df in bestaende.items():
            for schluessel in gewichte_je_kategorie(df, spalte).index:
                if str(schluessel).strip().lower() in ("", "nan", "none", "-"):
                    schmutz.append(f"{name}/{spalte}: {schluessel!r}")
    if schmutz:
        print(f"    FEHLER — Fehlwerte als Kategorie: {schmutz[:5]}")
        f += 1
    else:
        print("    OK — keine leere und keine „nan\"-Kategorie")

    # B') DIE GEGENPROBE. So haette es eine naive Fassung gemacht: roh nach
    # der Spalte gruppieren, ohne aufzuraeumen. Sie MUSS bei jeder Datei eine
    # Kategorie mehr finden — die leere Schlusszeile. Faende sie dasselbe,
    # pruefte der Schritt oben nichts.
    naiv_mehr = 0
    for name, df in bestaende.items():
        sauber = gewichte_je_kategorie(df, "WKN")
        # dropna=False ist noetig, damit die Fassung wirklich naiv ist:
        # pandas 3.0 wirft NA-Schluessel beim groupby von sich aus weg. Die
        # leere Schlusszeile faellt dort also schon durch das Werkzeug — und
        # nicht, weil jemand sie behandelt haette. Genau das soll dieser
        # Schritt sichtbar machen.
        naiv = df.groupby(df["WKN"].astype(str).str.strip(),
                          dropna=False)["Gewicht"].sum()
        if len(naiv) > len(sauber):
            naiv_mehr += 1
    if naiv_mehr == len(bestaende):
        print(f"    OK — die naive Fassung faellt bei allen {naiv_mehr} "
              "Dateien auf die leere Schlusszeile herein")
    else:
        print(f"    FEHLER — Gegenprobe greift nur bei {naiv_mehr} von "
              f"{len(bestaende)} Dateien")
        f += 1

    # C) Die Titelgewichte erreichen nirgends 100 % — der Vorbehalt, den die
    # Oberflaeche als Satz nennt, ist hier gemessen.
    summen = {n: float(gewichte_je_kategorie(df, "WKN").sum())
              for n, df in bestaende.items()}
    if max(summen.values()) >= 1.0:
        zu_hoch = [n for n, v in summen.items() if v >= 1.0]
        print(f"    FEHLER — Titelgewicht erreicht 100 %: {zu_hoch}")
        f += 1
    else:
        print(f"    OK — Titelgewichte zwischen {min(summen.values()):.1%} und "
              f"{max(summen.values()):.1%}, nie 100 %")

    # D) Die Kategorien sind ueber alle Strategien gemeinsam bestimmt und
    # decken jede einzelne ab — sonst fehlte in einem Balken ein Stueck.
    for spalte in ("Gattung", "Region", "Segment", "Währung"):
        gemeinsam = set(kategorien_vereinigt(bestaende, spalte))
        for name, df in bestaende.items():
            fehlend = set(gewichte_je_kategorie(df, spalte).index) - gemeinsam
            if fehlend:
                print(f"    FEHLER — {name}/{spalte}: {fehlend} fehlt in der "
                      "gemeinsamen Kategorienliste")
                f += 1
    print("    OK — die gemeinsame Kategorienliste deckt jede Strategie ab")
    return f


def schritt3_bekannte_paare():
    print("Schritt 3 — Symmetrie und die namentlich festgelegten Paare")
    bestaende = _echte_bestaende()
    if bestaende is None:
        return 0
    f = 0

    gewichte = {n: gewichte_je_kategorie(df, "WKN")
                for n, df in bestaende.items()}

    # Symmetrie und Selbstueberschneidung an ALLEN echten Reihen.
    for name, g in gewichte.items():
        if abs(ueberlappung(g, g) - float(g.sum())) > TOLERANZ:
            print(f"    FEHLER — u({name},{name}) != Summe")
            f += 1
    namen = list(gewichte)
    for i, a in enumerate(namen):
        for b in namen[i + 1:]:
            hin = ueberlappung(gewichte[a], gewichte[b])
            her = ueberlappung(gewichte[b], gewichte[a])
            if abs(hin - her) > TOLERANZ:
                print(f"    FEHLER — unsymmetrisch: {a} / {b}")
                f += 1
    if not f:
        paare = len(namen) * (len(namen) - 1) // 2
        print(f"    OK — {len(namen)} Selbstueberschneidungen und {paare} "
              "Paare: symmetrisch und gleich der Summe")

    # Die drei bekannten Paare — namentlich, nicht als Spanne.
    for a, b, soll, titel in BEKANNTE_PAARE:
        if a not in gewichte or b not in gewichte:
            print(f"    FEHLER — {a} oder {b} fehlt im Bestand")
            f += 1
            continue
        ist = ueberlappung(gewichte[a], gewichte[b])
        k = gemeinsame_schluessel(gewichte[a], gewichte[b])
        f += _nah(f"{a} <-> {b}", ist, soll, 5e-5)
        if k != titel:
            print(f"    FEHLER — {a} <-> {b}: {k} gemeinsame Titel statt {titel}")
            f += 1

    # Eine Ebene ist zwangslaeufig groeber als die andere. Das ist der
    # Vorbehalt aus der Oberflaeche, hier als Ungleichung festgehalten:
    # Auf WKN-Ebene kann die Ueberschneidung nie GROESSER sein als auf einer
    # Ebene, die Titel zu Gruppen zusammenfasst.
    verletzt = 0
    for i, a in enumerate(namen):
        for b in namen[i + 1:]:
            fein = ueberlappung(gewichte[a], gewichte[b])
            for spalte in ("Gattung", "Region", "Segment", "Währung"):
                grob = ueberlappung(gewichte_je_kategorie(bestaende[a], spalte),
                                    gewichte_je_kategorie(bestaende[b], spalte))
                if fein > grob + 1e-9:
                    verletzt += 1
    if verletzt:
        print(f"    FEHLER — {verletzt}x ist die feine Ebene groesser als die grobe")
        f += 1
    else:
        print("    OK — die Einzeltitel-Ebene liegt nie ueber einer groeberen")
    return f


def schritt4_gemeinsame_titel():
    print("Schritt 4 — `gemeinsame_titel`: die Aufstellung stimmt mit der Summe")
    bestaende = _echte_bestaende()
    if bestaende is None:
        return 0
    f = 0

    # DIE ZUSAGE DES DRILLDOWNS, ueber ALLE Paare und ALLE Ebenen:
    # Die Summe der Einzelbeitraege IST die Ueberschneidung der Uebersicht.
    # Bricht das, zeigt die Ansicht zwei verschiedene Wahrheiten uebereinander
    # — die Zahl im Chart und die Zahl unter der Tabelle.
    namen = list(bestaende)
    schlimmste = 0.0
    paare = 0
    for spalte in ("WKN", "Gattung", "Region", "Segment", "Währung"):
        for i, a in enumerate(namen):
            for b in namen[i + 1:]:
                tab = gemeinsame_titel(bestaende[a], bestaende[b], spalte)
                soll = ueberlappung(gewichte_je_kategorie(bestaende[a], spalte),
                                    gewichte_je_kategorie(bestaende[b], spalte))
                ist = float(tab["gemeinsam"].sum()) if len(tab) else 0.0
                schlimmste = max(schlimmste, abs(ist - soll))
                paare += 1
                if abs(ist - soll) > TOLERANZ:
                    print(f"    FEHLER — {a}/{b}/{spalte}: Summe {ist} "
                          f"statt {soll}")
                    f += 1
    if not f:
        print(f"    OK — {paare} Paar-Ebenen-Kombinationen, groesste "
              f"Abweichung {schlimmste:.3e}")

    # Absteigend sortiert, und jeder Beitrag ist das KLEINERE der Gewichte.
    a, b = "cVV ausgewogen", "cVV defensiv plus"
    tab = gemeinsame_titel(bestaende[a], bestaende[b])
    if list(tab["gemeinsam"]) != sorted(tab["gemeinsam"], reverse=True):
        print("    FEHLER — nicht absteigend sortiert")
        f += 1
    falsch = [z for _, z in tab.iterrows()
              if abs(z["gemeinsam"] - min(z["gewicht_a"], z["gewicht_b"])) > TOLERANZ]
    if falsch:
        print(f"    FEHLER — {len(falsch)} Zeilen sind nicht das Minimum")
        f += 1
    if not falsch:
        print(f"    OK — {len(tab)} Zeilen, absteigend, je das kleinere Gewicht")

    # NAMENTLICH: der groesste Beitrag dieses Paares.
    oben = tab.iloc[0]
    if oben["bezeichnung"] != "XETRA Gold":
        print(f"    FEHLER — groesster Beitrag ist {oben['bezeichnung']!r} "
              "statt 'XETRA Gold'")
        f += 1
    else:
        f += _nah("XETRA Gold als groesster Beitrag", oben["gemeinsam"],
                  0.07544, 5e-6)

    # AUF GROEBEREN EBENEN GIBT ES KEINEN KLARTEXTNAMEN. Beim ersten Schreiben
    # bildete die Funktion dort "Aktien" auf einen beliebigen Wertpapiernamen
    # ab, weil je Gattung viele Zeilen in Frage kommen und die letzte gewann.
    grob = gemeinsame_titel(bestaende[a], bestaende[b], "Gattung")
    if list(grob["bezeichnung"]) != list(grob["schluessel"]):
        print(f"    FEHLER — auf Gattungsebene weicht die Bezeichnung vom "
              f"Schluessel ab: {list(grob['bezeichnung'])[:3]}")
        f += 1
    else:
        print("    OK — auf groeberer Ebene ist der Schluessel der Klartext")

    # Disjunkte Depots -> leere Tabelle statt Absturz.
    ohne = [(x, y) for x in namen for y in namen
            if x < y and gemeinsame_schluessel(
                gewichte_je_kategorie(bestaende[x], "WKN"),
                gewichte_je_kategorie(bestaende[y], "WKN")) == 0]
    if ohne:
        x, y = ohne[0]
        leer = gemeinsame_titel(bestaende[x], bestaende[y])
        if not leer.empty:
            print(f"    FEHLER — {x}/{y} haben keinen gemeinsamen Titel, "
                  "liefern aber Zeilen")
            f += 1
        else:
            print(f"    OK — {x} / {y}: kein gemeinsamer Titel, leere Tabelle")
    return f


def main():
    print("Pruefstein: Bestands-Mathematik\n")
    fehler = 0
    for schritt in (schritt1_ueberlappung, schritt2_echte_dateien,
                    schritt3_bekannte_paare, schritt4_gemeinsame_titel):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — Kategoriegewichte plus Liquiditaet ergeben 1, die leere "
          "Schlusszeile zaehlt nicht mit, und u(a,a) ist die Summe von a")
    return 0


if __name__ == "__main__":
    sys.exit(main())
