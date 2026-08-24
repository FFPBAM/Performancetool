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

# Drei Paare, am 24.08.2026 an den echten Bestaenden gemessen und HIER
# NAMENTLICH festgelegt. Wer die Bestandsdaten austauscht, sieht hier eine
# Abweichung und entscheidet bewusst — statt dass sich eine Zahl still
# verschiebt, die in der Doku als Beispiel steht.
#
# NACHGEZOGEN am 24.08.2026 auf den Bestandsstand 260824. Vorher standen hier
# die Werte vom Stand 260708 (gemessen 18.08.2026):
#   cVV ausgewogen/cVV defensiv plus  0.69564, 22 Titel
#   cVV dynamic/Comdirect_100         0.44982, 13 Titel
#   cVV ausgewogen/Comdirect_100      0.20530,  5 Titel
# Genau dafuer stehen diese Anker: Der Test hat den Datenwechsel gemeldet,
# statt ihn durchgehen zu lassen. Die Titelzahl des zweiten Paares ist dabei
# von 13 auf 12 gefallen — eine echte Bestandsaenderung, keine Rundung.
BEKANNTE_PAARE = [
    # (Strategie A, Strategie B, Anteil, gemeinsame Titel)
    ("cVV ausgewogen", "cVV defensiv plus", 0.70552, 22),
    ("cVV dynamic",    "Comdirect_100",     0.41607, 12),
    ("cVV ausgewogen", "Comdirect_100",     0.21385,  5),
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
        # Nachgezogen 24.08.2026 (Stand 260824); vorher 0.07544 (Stand 260708).
        f += _nah("XETRA Gold als groesster Beitrag", oben["gemeinsam"],
                  0.08236, 5e-6)

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



# ─────────────────────────────────────────────────────────────────────────────

# Am 24.08.2026 am Bestandsstand 260824 gemessen, Strategie *cVV ausgewogen*.
# DIE GEGENPROBE ZU #64 STECKT IN DIESEN ZAHLEN: "Eisen,Stahl,Rohstoffe" ist
# das einzige Segment, das in ZWEI Gattungen vorkommt. Flach ueber alle
# Gattungen aggregiert kippt dabei sogar das VORZEICHEN — die naive Fassung
# meldet einen Gewinn, wo die Aktienseite einen Verlust hatte.
BEITRAG_CVV_AUSGEWOGEN = {
    "Aktien":      (+0.089020, 9),   # (Summe, Zahl der Segmente)
    "Edelmetalle": (+0.005740, 1),
    "Renten":      (+0.001590, 2),
}
BEITRAG_GESAMT = +0.096350
# Dasselbe Segment, dreimal gelesen:
DOPPELSEGMENT = "Eisen,Stahl,Rohstoffe"
DOPPEL_AKTIEN = -0.001590
DOPPEL_EDELMETALLE = +0.005740
DOPPEL_FLACH = +0.004150   # was eine Fassung OHNE Gattungsfilter liefern wuerde


def schritt5_beitrag_je_kategorie():
    """Der Performancebeitrag je Segment — additiv, gattungsrein, sortiert.

    WARUM DIESER SCHRITT NICHT UEBERSPRINGT, WENN DER NAME FEHLT (#65): Ein
    fehlendes PAKET ist ein Umgebungsproblem, ein fehlendes SYMBOL ist ein
    Fehler in der Sache. Der Unterschied gehoert in die Ausgabe, sonst meldet
    ein Test "bestanden", der nichts geprueft hat.
    """
    print("Schritt 5 — `performancebeitrag_je_kategorie`")
    f = 0
    try:
        from modules.bestandsanalytik import performancebeitrag_je_kategorie as pjk
    except ImportError as ex:
        print(f"    FEHLER — das Symbol fehlt: {ex}")
        return 1

    # ── (a) Grenzfaelle: ein Fehlwert ist kein Messwert (#46) ────────────
    leer_faelle = [
        ("fehlende Kategoriespalte",
         pd.DataFrame({"Performancebeitrag": [0.01], "Gattung": ["Aktien"]}),
         "Segment", None),
        ("fehlende Beitragsspalte",
         pd.DataFrame({"Segment": ["X"], "Gattung": ["Aktien"]}),
         "Segment", None),
        ("leerer Bestand", pd.DataFrame(), "Segment", None),
        ("Gattung ohne Zeilen",
         pd.DataFrame({"Segment": ["X"], "Gattung": ["Aktien"],
                       "Performancebeitrag": [0.01]}),
         "Segment", "Renten"),
    ]
    for bez, df, spalte, gattung in leer_faelle:
        reihe, ohne, n = pjk(df, spalte, gattung)
        if len(reihe) or ohne != 0.0 or n != 0:
            print(f"    FEHLER — {bez}: {len(reihe)} Eintraege, "
                  f"ohne_zuordnung={ohne}, n={n} statt leer/0.0/0")
            f += 1
    if not f:
        print(f"    OK — {len(leer_faelle)} Grenzfaelle liefern leer, 0.0, 0")

    bestaende = _echte_bestaende()
    if bestaende is None:
        return f + 1   # UEBERSPRUNGEN waere hier eine Luege: die Daten sind da

    # ── (b) Additiv je Gattung, vollstaendig ueber alle Gattungen ────────
    schlimmste = 0.0
    geprueft = 0
    for name, df in sorted(bestaende.items()):
        gesamt_ist = 0.0
        for gattung in df["Gattung"].dropna().astype(str).str.strip().unique():
            teil = df[df["Gattung"].astype(str).str.strip() == gattung]
            soll = float(teil["Performancebeitrag"].sum())
            reihe, ohne, _n = pjk(df, "Segment", gattung)
            ist = float(reihe.sum()) + float(ohne)
            schlimmste = max(schlimmste, abs(ist - soll))
            if abs(ist - soll) > TOLERANZ:
                print(f"    FEHLER — {name}/{gattung}: {ist} statt {soll}")
                f += 1
            gesamt_ist += ist
            geprueft += 1
        gesamt_soll = float(df["Performancebeitrag"].sum())
        if abs(gesamt_ist - gesamt_soll) > TOLERANZ:
            print(f"    FEHLER — {name}: Summe ueber alle Gattungen "
                  f"{gesamt_ist} statt {gesamt_soll}")
            f += 1
    print(f"    OK — {geprueft} Strategie-Gattung-Paare additiv, groesste "
          f"Abweichung {schlimmste:.3e}")

    # ── (c) Absteigend sortiert — das ist eine fachliche Zusage ──────────
    unsortiert = 0
    for name, df in bestaende.items():
        for gattung in df["Gattung"].dropna().astype(str).str.strip().unique():
            reihe, _o, _n = pjk(df, "Segment", gattung)
            if list(reihe) != sorted(reihe, reverse=True):
                unsortiert += 1
    if unsortiert:
        print(f"    FEHLER — {unsortiert} Reihen sind nicht absteigend")
        f += 1
    else:
        print("    OK — jede Reihe ist absteigend sortiert")

    # ── (d) Keine leere und keine "nan"-Kategorie ────────────────────────
    schrott = set()
    for name, df in bestaende.items():
        for gattung in df["Gattung"].dropna().astype(str).str.strip().unique():
            reihe, _o, _n = pjk(df, "Segment", gattung)
            for k in reihe.index:
                if str(k).strip().lower() in ("", "nan", "none", "-"):
                    schrott.add((name, gattung, k))
    if schrott:
        print(f"    FEHLER — Schrottkategorien: {sorted(schrott)[:3]}")
        f += 1
    else:
        print("    OK — keine leere und keine \"nan\"-Kategorie")

    # ── (e) NAMENTLICH: cVV ausgewogen ───────────────────────────────────
    d = bestaende.get("cVV ausgewogen")
    if d is None:
        print("    FEHLER — cVV ausgewogen fehlt im Bestand")
        return f + 1
    for gattung, (soll, n_soll) in BEITRAG_CVV_AUSGEWOGEN.items():
        reihe, ohne, _n = pjk(d, "Segment", gattung)
        f += _nah(f"cVV ausgewogen/{gattung}", float(reihe.sum()) + float(ohne),
                  soll, 5e-6)
        if len(reihe) != n_soll:
            print(f"    FEHLER — cVV ausgewogen/{gattung}: {len(reihe)} "
                  f"Segmente statt {n_soll}")
            f += 1
    reihe_alle, ohne_alle, _n = pjk(d, "Segment", None)
    f += _nah("cVV ausgewogen, alle Gattungen",
              float(reihe_alle.sum()) + float(ohne_alle), BEITRAG_GESAMT, 5e-6)

    # ── (f) DIE GEGENPROBE (#64): der Gattungsfilter wirkt wirklich ──────
    # Ohne ihn stuende hier eine Zahl, die es in keiner Gattung gibt — und
    # zwar mit dem falschen VORZEICHEN. Waeren die drei Werte gleich, pruefte
    # (e) nichts.
    aktien, _o, _n = pjk(d, "Segment", "Aktien")
    edel, _o2, _n2 = pjk(d, "Segment", "Edelmetalle")
    naiv = float(d.groupby("Segment")["Performancebeitrag"].sum()[DOPPELSEGMENT])
    f += _nah(f"{DOPPELSEGMENT} unter Aktien", float(aktien[DOPPELSEGMENT]),
              DOPPEL_AKTIEN, 5e-6)
    f += _nah(f"{DOPPELSEGMENT} unter Edelmetallen", float(edel[DOPPELSEGMENT]),
              DOPPEL_EDELMETALLE, 5e-6)
    f += _nah(f"{DOPPELSEGMENT} flach (die verworfene Fassung)", naiv,
              DOPPEL_FLACH, 5e-6)
    if not (float(aktien[DOPPELSEGMENT]) < 0.0 < naiv):
        print("    FEHLER — die Gegenprobe greift nicht: das Vorzeichen "
              "kippt nicht mehr zwischen flach und gattungsrein")
        f += 1
    else:
        print("    OK — flach kippt das Vorzeichen gegenueber der Aktienseite")

    return f



# ─────────────────────────────────────────────────────────────────────────────

# Am 24.08.2026 am Bestandsstand 260824 gemessen. Die drei Zahlen je Paar
# haengen ueber eine IDENTITAET zusammen, nicht ueber drei Messungen:
#
#     Ueberschneidung + Nicht-Ueberschneidung == investiertes Gewicht von A
#
# Wer eine davon aendert, bricht die Zusage — und genau deshalb stehen sie
# hier nebeneinander und nicht einzeln.
BEKANNTE_EXKLUSIV = [
    # (A, B, Ueberschneidung, exklusiv A, exklusiv B, investiert A)
    ("cVV ausgewogen", "cVV defensiv plus", 0.70552, 0.25303, 0.24343, 0.95855),
    ("cVV ausgewogen", "Comdirect_100",     0.21385, 0.74470, 0.74246, 0.95855),
    ("cVV dynamic",    "Comdirect_100",     0.41607, 0.56309, 0.54024, 0.97916),
]
# Die VERWORFENE Definition, zum Vergleich: Summe |w_A - w_B|. Sie ist
# symmetrisch, kann aber ueber 100 % gehen — bei diesem Paar 148,7 %. Neben
# einem Mass mit Deckel 100 waere das ein Missverstaendnis mit Ansage.
L1_CVV_COMDIRECT = 1.48716


def schritt6_nicht_ueberlappung():
    """Die Nicht-Ueberschneidung: was A haelt und B nicht.

    NICHT SYMMETRISCH, und das ist der Punkt: Die Ueberschneidung ist eine
    Eigenschaft des PAARES, die Nicht-Ueberschneidung eine Eigenschaft der
    RICHTUNG. Waeren beide Richtungen gleich, waere die Bezugsstrategie eine
    Fiktion — deshalb wird die Ungleichheit hier namentlich festgehalten.
    """
    print("Schritt 6 — `nicht_ueberlappung` und `exklusive_titel`")
    try:
        from modules.bestandsanalytik import (exklusive_titel,
                                              nicht_ueberlappung)
    except ImportError as ex:
        print(f"    FEHLER — ein Symbol fehlt: {ex}")
        return 1

    f = 0

    # ── Grenzfaelle ──────────────────────────────────────────────────────
    leer = pd.Series(dtype=float)
    eins = pd.Series({"A": 0.5})
    zwei = pd.Series({"B": 0.5})
    faelle = [
        ("leer gegen leer", leer, leer, 0.0),
        ("leer gegen etwas", leer, eins, 0.0),
        ("etwas gegen leer", eins, leer, 0.5),
        ("voellig disjunkt", eins, zwei, 0.5),
        ("identisch", eins, eins, 0.0),
    ]
    for bez, a, b, soll in faelle:
        f += _nah(bez, nicht_ueberlappung(a, b), soll)

    # ── Die drei Zusagen an den echten Bestaenden ────────────────────────
    bestaende = _echte_bestaende()
    if bestaende is None:
        return f + 1

    ebenen = ["WKN", "Gattung", "Region", "Segment", "Währung"]
    namen = sorted(bestaende)
    schlimmste_z1 = schlimmste_z2 = 0.0
    paare = 0
    for spalte in ebenen:
        gew = {n: gewichte_je_kategorie(bestaende[n], spalte) for n in namen}
        for a in namen:
            # Z3: gegen sich selbst gibt es nichts Exklusives.
            if abs(nicht_ueberlappung(gew[a], gew[a])) > TOLERANZ:
                print(f"    FEHLER — {a}/{spalte}: n(a,a) = "
                      f"{nicht_ueberlappung(gew[a], gew[a])} statt 0")
                f += 1
            for b in namen:
                if a == b:
                    continue
                paare += 1
                # Z1: die Identitaet, die alles zusammenhaelt.
                summe = (nicht_ueberlappung(gew[a], gew[b])
                         + ueberlappung(gew[a], gew[b]))
                schlimmste_z1 = max(schlimmste_z1,
                                    abs(summe - float(gew[a].sum())))
                if abs(summe - float(gew[a].sum())) > TOLERANZ:
                    print(f"    FEHLER — {a}->{b}/{spalte}: "
                          f"{summe} statt {float(gew[a].sum())}")
                    f += 1
    print(f"    OK — Z1 ueber {paare} gerichtete Paar-Ebenen-Kombinationen, "
          f"groesste Abweichung {schlimmste_z1:.3e}")
    print("    OK — Z3: n(a,a) ist ueberall 0")

    # Z2: die Aufstellung summiert sich auf die Zahl.
    for spalte in ebenen:
        gew = {n: gewichte_je_kategorie(bestaende[n], spalte) for n in namen}
        for a in namen:
            for b in namen:
                if a == b:
                    continue
                tab = exklusive_titel(bestaende[a], bestaende[b], spalte)
                ist = float(tab["exklusiv"].sum())
                soll = nicht_ueberlappung(gew[a], gew[b])
                schlimmste_z2 = max(schlimmste_z2, abs(ist - soll))
                if abs(ist - soll) > TOLERANZ:
                    print(f"    FEHLER — Z2 {a}->{b}/{spalte}: "
                          f"{ist} statt {soll}")
                    f += 1
    print(f"    OK — Z2: die Aufstellung trifft die Zahl, groesste "
          f"Abweichung {schlimmste_z2:.3e}")

    # ── NAMENTLICH, und die Asymmetrie als Gegenprobe (#64) ──────────────
    for a, b, ue_soll, exa_soll, exb_soll, summe_soll in BEKANNTE_EXKLUSIV:
        if a not in bestaende or b not in bestaende:
            print(f"    FEHLER — {a} oder {b} fehlt im Bestand")
            f += 1
            continue
        ga = gewichte_je_kategorie(bestaende[a], "WKN")
        gb = gewichte_je_kategorie(bestaende[b], "WKN")
        f += _nah(f"{a} <-> {b} gemeinsam", ueberlappung(ga, gb), ue_soll, 5e-5)
        exa = nicht_ueberlappung(ga, gb)
        exb = nicht_ueberlappung(gb, ga)
        f += _nah(f"nur bei {a}", exa, exa_soll, 5e-5)
        f += _nah(f"nur bei {b}", exb, exb_soll, 5e-5)
        f += _nah(f"investiert {a}", float(ga.sum()), summe_soll, 5e-5)
        # DIE RICHTUNG IST ECHT: Waeren beide Seiten gleich, koennte man sich
        # die Bezugsstrategie sparen — und der Schalter waere eine Attrappe.
        if abs(exa - exb) < 1e-4:
            print(f"    FEHLER — {a}/{b}: beide Richtungen sind gleich "
                  f"({exa} gegen {exb}), die Asymmetrie ist eine Fiktion")
            f += 1

    # ── Die verworfene Definition liefert etwas ANDERES ──────────────────
    # Ohne diese Gegenprobe koennte jemand die Formel still gegen die
    # L1-Distanz tauschen, ohne dass ein Test es merkte.
    ga = gewichte_je_kategorie(bestaende["cVV ausgewogen"], "WKN")
    gb = gewichte_je_kategorie(bestaende["Comdirect_100"], "WKN")
    idx = ga.index.union(gb.index)
    l1 = float((ga.reindex(idx).fillna(0.0)
                - gb.reindex(idx).fillna(0.0)).abs().sum())
    f += _nah("L1-Distanz (die verworfene Fassung)", l1, L1_CVV_COMDIRECT, 5e-5)
    if l1 <= 1.0:
        print("    FEHLER — die Gegenprobe traegt nicht mehr: die L1-Distanz "
              "geht nicht mehr ueber 100 %")
        f += 1
    elif abs(l1 - nicht_ueberlappung(ga, gb)) < 1e-4:
        print("    FEHLER — L1 und Nicht-Ueberschneidung sind dasselbe "
              "geworden")
        f += 1
    else:
        print(f"    OK — L1 liegt bei {l1 * 100:.1f} % und damit ueber 100, "
              "die Nicht-Ueberschneidung nicht")

    # ── Die Aufstellung: Spalten, Sortierung, Art ────────────────────────
    tab = exklusive_titel(bestaende["cVV ausgewogen"],
                          bestaende["cVV defensiv plus"])
    soll_spalten = ["schluessel", "bezeichnung", "gattung", "gewicht_a",
                    "gewicht_b", "exklusiv", "art"]
    if list(tab.columns) != soll_spalten:
        print(f"    FEHLER — Spalten {list(tab.columns)} statt {soll_spalten}")
        f += 1
    elif list(tab["exklusiv"]) != sorted(tab["exklusiv"], reverse=True):
        print("    FEHLER — nicht absteigend sortiert")
        f += 1
    elif (tab["exklusiv"] <= 0).any():
        print("    FEHLER — eine Zeile traegt nichts bei und steht trotzdem da")
        f += 1
    else:
        nur_a = int((tab["art"] == "nur in A").sum())
        print(f"    OK — {len(tab)} Zeilen, absteigend, davon {nur_a} "
              f"ausschliesslich bei der Bezugsstrategie")

    # Jede Zeile ist wirklich die Differenz, nicht irgendeine Zahl.
    falsch = [z["schluessel"] for _, z in tab.iterrows()
              if abs(z["exklusiv"] - max(0.0, z["gewicht_a"] - z["gewicht_b"]))
              > TOLERANZ]
    if falsch:
        print(f"    FEHLER — {len(falsch)} Zeilen sind nicht max(0, a-b)")
        f += 1
    else:
        print("    OK — jede Zeile ist das Uebergewicht der Bezugsstrategie")

    # Auf groeberer Ebene gibt es keinen Klartextnamen (wie `gemeinsame_titel`).
    grob = exklusive_titel(bestaende["cVV ausgewogen"],
                           bestaende["cVV defensiv plus"], "Gattung")
    if len(grob) and list(grob["bezeichnung"]) != list(grob["schluessel"]):
        print("    FEHLER — auf Gattungsebene weicht die Bezeichnung ab")
        f += 1
    else:
        print("    OK — auf groeberer Ebene ist der Schluessel der Klartext")

    return f


def main():
    print("Pruefstein: Bestands-Mathematik\n")
    fehler = 0
    for schritt in (schritt1_ueberlappung, schritt2_echte_dateien,
                    schritt3_bekannte_paare, schritt4_gemeinsame_titel,
                    schritt5_beitrag_je_kategorie,
                    schritt6_nicht_ueberlappung):
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
