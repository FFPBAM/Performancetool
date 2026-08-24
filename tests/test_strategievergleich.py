"""Pruefstein fuer die Risiko-Rendite-Punktwolke (NEU 18.08.2026).

Die dritte Ansicht zeigt jede Strategie als EINEN Punkt: Rendite p.a. gegen
Volatilitaet oder Max Drawdown. Sie hat genau zwei Zusagen, und beide sind
keine Mathematik, sondern Ehrlichkeit:

  A) DIESELBE ZAHL WIE DIE KENNZAHLEN-KACHEL. Was in der Punktwolke steht,
     muss fuer denselben Zeitraum mit dem uebereinstimmen, was die
     Performance-Ansicht in ihrer Kachel zeigt. Zwei verschiedene Renditen
     fuer dieselbe Strategie auf zwei Bildschirmen waeren schlimmer als jede
     Lehrbuch-Ungenauigkeit (die Lehre aus #52).

  B) WER DEN ZEITRAUM NICHT ABDECKT, WIRD NICHT GEZEICHNET. Die 19
     Strategien haben zwischen 1,7 und 17,6 Jahren Historie. Ein Punkt, der
     stillschweigend ueber einen kuerzeren Zeitraum rechnet als seine
     Nachbarn, ist derselbe Fehler wie ein Rumpfjahr als Jahresbalken (#51).

  1. `rendite` in risiko_perioden — Anker, geschlossene Form, Grenzfaelle
  2. Zusage A: Punktwolke == Kennzahlen-Kachel, an allen 19 echten Reihen
  3. Zusage B: Abdeckung, mit NAMENTLICHER Festlegung der bekannten Faelle
     UND der Gegenprobe gegen eine naive Fassung
  4. Die FIGUR statt der Daten (#54)
  5. Die Oberflaeche faehrt hoch (AppTest)
  6. Der X-Achsen-Umschalter ist ein segmented_control (per AST)
  7. Die Figuren von Ueberschneidung und Exposure (#54)
  8. Die Oberflaeche der beiden neuen Abschnitte (AppTest)
  9. Der Drilldown: Auswahl-Aufloesung, Beitragsbalken, deutsche Zahlen
 10. Die Auswahlfelder koennen nicht ungueltig werden (Kennungs-Keys)

SCHRITT 10 GIBT ES WEGEN EINES GEMELDETEN FEHLERS: Nach dem Reduzieren der
Strategieauswahl auf zwei stand im Feld "Bezugsstrategie" weiter eine
Strategie, die es nicht mehr gab - und der Abschnitt zeigte keine Daten. Der
Schutz davor raeumte den session_state-Schluessel auf und verliess sich
darauf, dass er geloescht bleibt. AppTest kann das nicht nachstellen (drei
Bedienwege probiert), die echte App hat es widerlegt.

Geprueft wird deshalb nicht das Verhalten, sondern die REGEL - und die liegt
in zwei streamlit-freien Funktionen, seit der Schluessel eine Kennung der
Optionsmenge traegt.

SCHRITT 6 SIEHT AUS WIE KOSMETIK UND IST KEINE. Der Umschalter war zuerst ein
`st.radio`; die Heatmap benutzt fuer dieselbe Aufgabe `st.segmented_control`.
Zwei Bauformen fuer dasselbe sehen ungleichmaessig aus (Philip, 18.08.2026) —
und `required=True` ist der Grund, warum der Baustein hier ueberhaupt traegt:
Ohne ihn laesst sich das aktive Segment abwaehlen, und es gaebe den Zustand
"keine X-Achse gewaehlt". Der Schritt liest deshalb den SYNTAXBAUM und nicht
den Text, damit ein Kommentar ihn nicht beruhigen kann.

WARUM SCHRITT 1 MIT NULLTAGEN ANFAENGT: Eine Reihe ohne Marktbewegung muss
EXAKT den Honorarsatz p.a. kosten — und zwar unabhaengig davon, wie lang sie
ist, weil die Annualisierung die Tageszahl wieder aufhebt. Das ist derselbe
Anker, an dem Audit-Befund B3 haengt (test_kosten_mathematik, Schritt 3), nur
fuer die Groesse, die neu dazugekommen ist. Eine Rendite, die diesen Fall
verfehlt, rechnet den Honorarabzug falsch, und man saehe es der Punktwolke
nicht an. Dass die TAGESZAHL stimmt, faellt dabei nicht auf — dafuer ist
Schritt 1b da, der eine wachsende Reihe gegen die geschlossene Form prueft.

WARUM SCHRITT 3 EINE GEGENPROBE HAT: Fuer eine neue Ansicht gibt es keinen
"alten Stand", auf dem der Test rot waere. Ersatzweise wird die NAIVE Fassung
nachgestellt — rechnen, was da ist, ohne die Abdeckung zu pruefen — und
verlangt, dass sie fuer die bekannten Faelle etwas anderes liefert. Ein Test,
der nur gruen ist, beweist nichts (CLAUDE.md, Regel 2). Dasselbe Vorgehen wie
bei `_ist_voller_monat` am 14.08.2026.

Schritte 1 und 4 brauchen nur numpy/pandas (4 zusaetzlich plotly, das mit
streamlit ohnehin kommt). Schritte 2 und 3 lesen die echten CSVs, Schritt 5
braucht die AppTest-Umgebung. Fehlt etwas, wird uebersprungen statt zu
scheitern.

    python tests/test_strategievergleich.py
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

from modules.analytics import (  # noqa: E402
    compute_performance_data, risiko_perioden,
)

TOLERANZ = 1e-12

# Die fuenf Strategien, deren Historie am 24.08.2026 kuerzer als drei Jahre
# war — mit ihrer gemessenen Laenge. NAMENTLICH und nicht als Zahl: Wer eine
# Strategie ergaenzt oder eine Historie nachliefert, soll hier anschlagen und
# bewusst entscheiden, statt dass sich eine Zahl still verschiebt.
#
# NACHGEZOGEN am 24.08.2026 auf den Datenstand 260824. Vorher (Stand 260721,
# gemessen 18.08.2026): Pro 2.9, Pro Dividende 1.7, Comdirect_* je 2.4.
# Die Historien werden mit jeder Datenlieferung laenger — dass diese Zahlen
# wandern, ist kein Fehler, sondern der Zweck des Ankers.
#
# ACHTUNG, DIESER ANKER LAEUFT AB: `Pro` beginnt am 01.09.2023 und erreicht
# damit am 01.09.2026 die vollen drei Jahre. Ab der ersten Datenlieferung
# danach faellt es aus dieser Liste, und Pruefung (a) meldet zu Recht eine
# Abweichung — dann ist der Eintrag zu ENTFERNEN, nicht die Zahl zu erhoehen.
# Die uebrigen vier halten laenger: Comdirect_* bis 12.03.2027,
# Pro Dividende bis 22.10.2027.
KURZ_UNTER_3J = {
    "Pro":            2.98,
    "Pro Dividende":  1.84,
    "Comdirect_30":   2.45,
    "Comdirect_70":   2.45,
    "Comdirect_100":  2.45,
}


def _symbole(modulname, namen, pakete=("streamlit",)):
    """Holt Namen aus einem EIGENEN Modul. Returns dict, None oder False.

        dict   alles da
        None   ein PAKET fehlt -> der Schritt wird uebersprungen
        False  ein SYMBOL fehlt -> der Schritt ist FEHLGESCHLAGEN

    WARUM DIE UNTERSCHEIDUNG (18.08.2026, teuer gelernt): Die Schritte hier
    fingen bisher jede Ausnahme beim Import ab und meldeten UEBERSPRUNGEN.
    Fuer ein fehlendes Paket ist das richtig und Hausregel — die Suiten
    sollen in der eingeschraenkten Firmenumgebung laufen. Fuer ein fehlendes
    SYMBOL ist es falsch: Das ist ein gebrochener Vertrag.

    Aufgefallen ist es an der Gegenprobe zum Legenden-Fehler. Der neue
    Schritt 7 wurde gegen den alten Modulstand gehalten und meldete
    BESTANDEN — weil die geprueften Funktionen dort noch nicht existierten
    und der Schritt sich deshalb selbst uebersprang. Ein Test, der sich beim
    Fehlen seines Pruefgegenstands still zurueckzieht, ist schlimmer als
    keiner: Er sieht aus wie ein Beweis. Dieselbe Familie wie #64.
    """
    import importlib
    import importlib.util
    for paket in pakete:
        if importlib.util.find_spec(paket) is None:
            print(f"    UEBERSPRUNGEN — {paket} nicht installiert")
            return None
    try:
        modul = importlib.import_module(modulname)
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — {modulname} nicht ladbar: {ex}")
        return None
    fehlend = [n for n in namen if not hasattr(modul, n)]
    if fehlend:
        print(f"    FEHLER — {modulname} kennt diese Namen nicht: {fehlend}. "
              "Der Schritt kann nicht pruefen, was er pruefen soll.")
        return False
    return {n: getattr(modul, n) for n in namen}


def _nah(bezeichnung, ist, soll, toleranz=TOLERANZ):
    if ist is None or (isinstance(ist, float) and np.isnan(ist)):
        print(f"    FEHLER — {bezeichnung}: Fehlwert statt {soll}")
        return 1
    if abs(float(ist) - float(soll)) <= toleranz:
        print(f"    OK — {bezeichnung} = {float(ist):.10g}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {float(ist):.10g} statt {float(soll):.10g}")
    return 1


def _reihe(renditen, start="2023-01-01"):
    """Zeitreihe im Format, das risiko_perioden erwartet — kalendertaeglich."""
    n = len(renditen)
    idx = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({"ret_port": np.asarray(renditen, dtype=float)}, index=idx)


def _echte_reihen():
    """Die 19 echten Strategien als (Anzeigename, Zeitreihe, Honorar, Familie).

    None, wenn streamlit fehlt — `shared` und `portfolioanalyse` ziehen es
    herein, und die Suite soll dann ueberspringen statt zu scheitern.
    """
    try:
        from modules.shared import (DATA_FOLDER, EXCLUDE_SUBSTRINGS,
                                    build_name_lookups,
                                    build_portfolio_timeseries,
                                    detect_newest_date_tag, load_all_csvs,
                                    load_mapping, load_name_mapping)
        from modules.portfolioanalyse import familie_fuer_strategie
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return None
    mapping, name_mapping = load_mapping(), load_name_mapping()
    tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
    dateien = load_all_csvs(DATA_FOLDER, tag, EXCLUDE_SUBSTRINGS)
    if not dateien:
        print("    UEBERSPRUNGEN — keine Daten gefunden")
        return None
    data = build_portfolio_timeseries(dateien, mapping)
    namen, d2c, _ = build_name_lookups(name_mapping, set(data.keys()))
    return [(n, data[d2c[n]], float(data[d2c[n]]["fee_default"].iloc[0]),
             familie_fuer_strategie(name_mapping, n)) for n in namen]


# ─────────────────────────────────────────────────────────────────────────────

def schritt1_rendite():
    print("Schritt 1 — die neue Spalte `rendite` in risiko_perioden")
    f = 0

    # (a) DER ANKER: eine Zeitreihe ohne Marktbewegung kostet EXAKT den Satz
    # p.a. Derselbe Sollwert wie in test_kosten_mathematik Schritt 3 — und er
    # kommt aus der ZUSAGE ("ein Jahr ohne Bewegung kostet das Honorar"), nicht
    # aus einer Messung. Eine Toleranz, die an den Messwert angepasst ist,
    # prueft nichts mehr (#58).
    #
    # DAS GILT FUER JEDE LAENGE, und das ist die eigentliche Aussage: Der
    # Index traegt nach n Tagen den Faktor (1-d)^n, die Annualisierung hebt
    # das n wieder auf — ((1-d)^n)^(365/n) = (1-d)^365 = 1-f. Deshalb laeuft
    # die Schleife ueber drei Laengen und nicht nur ueber 365. Ein Fehler in
    # der Tageszahl faellt trotzdem auf, naemlich in (b).
    for satz in (0.0, 0.0055, 0.0155, 0.0255):
        for tage in (200, 365, 900):
            r = risiko_perioden(_reihe(np.zeros(tage)), satz).loc["Seit Auflage"]
            f += _nah(f"{tage} Nulltage bei {satz:.2%} kosten genau den Satz",
                      r["rendite"], -satz, 1e-11)

    # (b) GESCHLOSSENE FORM: konstante Tagesrendite r ueber n Tage, ohne
    # Honorar. Der Index waechst auf (1+r)^n, die CAGR ist damit
    # (1+r)^365 - 1 — unabhaengig von n. Das prueft zugleich, dass n_days die
    # ZEILENZAHL ist und nicht der Tagesabstand (der waere n-1).
    for n in (200, 365, 800):
        r_tag = 0.0002
        r = risiko_perioden(_reihe(np.full(n, r_tag)), 0.0).loc["Seit Auflage"]
        f += _nah(f"konstante {r_tag} ueber {n} Tage",
                  r["rendite"], (1.0 + r_tag) ** 365 - 1.0, 1e-12)

    # (c) DIE ZWEI GROESSEN KOMMEN AUS DERSELBEN INDEXREIHE. Bei einer nur
    # fallenden Reihe ist der Max Drawdown der Gesamtverlust — dieselbe Zahl
    # wie die kumulierte Rendite. Faellt das auseinander, rechnen Rendite und
    # Risiko auf verschiedenen Reihen.
    r = risiko_perioden(_reihe(np.full(365, -0.0001)), 0.0).loc["Seit Auflage"]
    f += _nah("nur fallend: max_dd == kumulierter Verlust",
              r["max_dd"], (1.0 - 0.0001) ** 365 - 1.0, 1e-12)

    # (d) GRENZFAELLE — leer, ein Element, konstant, NaN (CLAUDE.md).
    # Verlangt wird kein Wert, sondern KEIN ABSTURZ und ein Fehlwert.
    faelle = {
        "leere Reihe":      _reihe([]),
        "ein Element":      _reihe([0.001]),
        "nur NaN":          _reihe([np.nan] * 400),
    }
    for bez, df in faelle.items():
        try:
            wert = risiko_perioden(df, 0.0155).loc["Seit Auflage", "rendite"]
        except Exception as ex:
            print(f"    FEHLER — {bez}: {type(ex).__name__}: {ex}")
            f += 1
            continue
        if bez == "nur NaN":
            # NaN wird zu 0.0 gefuellt (wie ueberall in risiko_perioden), also
            # eine flache Reihe — und die kostet nach (a) exakt den Satz,
            # unabhaengig davon, wie lang sie ist.
            f += _nah("nur NaN -> reiner Honorarabzug", wert, -0.0155, 1e-11)
        elif pd.isna(wert):
            print(f"    OK — {bez}: Fehlwert statt Absturz")
        else:
            print(f"    FEHLER — {bez}: {wert!r} statt Fehlwert")
            f += 1
    return f


def schritt2_zusage_kachel():
    print("Schritt 2 — ZUSAGE A: Punktwolke zeigt die Zahl der Kennzahlen-Kachel")
    reihen = _echte_reihen()
    if reihen is None:
        return 0
    sym = _symbole("modules.strategievergleich",
                   ["GEMEINSAM", "kennzahlen_je_strategie"])
    if sym is None:
        return 0
    if sym is False:
        return 1
    GEMEINSAM = sym["GEMEINSAM"]
    kennzahlen_je_strategie = sym["kennzahlen_je_strategie"]

    f = 0
    # (a) Ueber die GANZE Reihe: die Kachel der Performance-Ansicht rechnet
    # mit compute_performance_data, die Punktwolke mit risiko_perioden. Zwei
    # Wege, eine Zahl — sonst widerspricht sich die Oberflaeche selbst.
    schlimmste = 0.0
    for name, df, fee, _ in reihen:
        kachel = compute_performance_data(df, fee)["kennzahlen"]
        zeile = risiko_perioden(df, fee).loc["Seit Auflage"]
        for feld, spalte in (("performance_pa_ref", "rendite"),
                             ("volatilitaet_ref", "vola"),
                             ("max_drawdown_ref", "max_dd")):
            a, b = kachel[feld], zeile[spalte]
            if a is None or pd.isna(b):
                print(f"    FEHLER — {name}/{spalte}: Fehlwert auf einer Seite")
                f += 1
                continue
            abweichung = abs(float(a) - float(b))
            schlimmste = max(schlimmste, abweichung)
            if abweichung > TOLERANZ:
                print(f"    FEHLER — {name}/{spalte}: {a!r} vs {b!r}")
                f += 1
    if not f:
        print(f"    OK — {len(reihen)} Strategien x 3 Kennzahlen, "
              f"groesste Abweichung {schlimmste:.3e}")

    # (b) Ueber ein FENSTER: derselbe Vergleich fuer den gemeinsamen Zeitraum.
    # Hier laeuft die Punktwolke ueber `kennzahlen_je_strategie`, also ueber
    # den Weg, den die Ansicht wirklich nimmt.
    tabelle = kennzahlen_je_strategie(reihen, GEMEINSAM)
    von = max(df.index.min() for _, df, _, _ in reihen)
    schlimmste_f = 0.0
    for name, df, fee, _ in reihen:
        teil = df.loc[df.index >= von]
        kachel = compute_performance_data(teil, fee)["kennzahlen"]
        for feld, spalte in (("performance_pa_ref", "rendite"),
                             ("volatilitaet_ref", "vola"),
                             ("max_drawdown_ref", "max_dd")):
            a, b = kachel[feld], tabelle.loc[name, spalte]
            if a is None or pd.isna(b):
                print(f"    FEHLER — {name}/{spalte} im Fenster: Fehlwert")
                f += 1
                continue
            abweichung = abs(float(a) - float(b))
            schlimmste_f = max(schlimmste_f, abweichung)
            if abweichung > TOLERANZ:
                print(f"    FEHLER — {name}/{spalte} im Fenster: {a!r} vs {b!r}")
                f += 1
    if not f:
        print(f"    OK — gemeinsames Fenster ab {von:%d.%m.%Y}, "
              f"groesste Abweichung {schlimmste_f:.3e}")
    return f


def schritt3_abdeckung():
    print("Schritt 3 — ZUSAGE B: wer den Zeitraum nicht abdeckt, wird nicht gezeigt")
    reihen = _echte_reihen()
    if reihen is None:
        return 0
    sym = _symbole("modules.strategievergleich",
                   ["GEMEINSAM", "kennzahlen_je_strategie",
                    "nicht_gezeigt_text"])
    if sym is None:
        return 0
    if sym is False:
        return 1
    GEMEINSAM = sym["GEMEINSAM"]
    kennzahlen_je_strategie = sym["kennzahlen_je_strategie"]
    nicht_gezeigt_text = sym["nicht_gezeigt_text"]

    f = 0
    tabelle = kennzahlen_je_strategie(reihen, "3 Jahre")
    fehlend = set(tabelle.index[~tabelle["abgedeckt"].astype(bool)])

    # (a) NAMENTLICH. Nicht "fuenf Stueck", sondern welche fuenf.
    if fehlend == set(KURZ_UNTER_3J):
        print(f"    OK — bei '3 Jahre' fehlen genau {sorted(fehlend)}")
    else:
        print(f"    FEHLER — bei '3 Jahre' fehlen {sorted(fehlend)}, "
              f"erwartet {sorted(KURZ_UNTER_3J)}")
        f += 1

    # (b) Die Historienlaenge, die im Hinweis steht, muss stimmen.
    for name, jahre_soll in KURZ_UNTER_3J.items():
        if name not in tabelle.index:
            continue
        jahre_ist = float(tabelle.loc[name, "jahre"])
        if abs(jahre_ist - jahre_soll) > 0.05:
            print(f"    FEHLER — {name}: {jahre_ist:.2f} J statt {jahre_soll} J")
            f += 1
    if not f:
        print("    OK — die genannten Historienlaengen stimmen")

    # (c) DER HINWEIS NENNT SIE AUCH WIRKLICH (#59).
    text = nicht_gezeigt_text(tabelle)
    fehlt_im_text = [n for n in KURZ_UNTER_3J if n not in text]
    if fehlt_im_text:
        print(f"    FEHLER — nicht im Hinweis genannt: {fehlt_im_text}")
        f += 1
    else:
        print("    OK — der Hinweis nennt alle ausgelassenen Strategien")

    # (d) DIE GEGENPROBE. So haette es eine naive Fassung gemacht: rechnen,
    # was im Fenster liegt, ohne zu fragen, ob die Historie es abdeckt. Wenn
    # sie fuer die bekannten Faelle DIESELBEN Fehlwerte liefert, prueft (a)
    # nichts — dann waere der Schutz gar nicht wirksam.
    ende = max(df.index.max() for _, df, _, _ in reihen)
    start = ende - pd.DateOffset(years=3)
    naiv_zahlen = 0
    for name, df, fee, _ in reihen:
        if name not in KURZ_UNTER_3J:
            continue
        teil = df.loc[df.index > start]          # <- der fehlende Schutz
        if len(teil) < 2:
            continue
        wert = risiko_perioden(teil, fee).loc["Seit Auflage", "rendite"]
        if pd.notna(wert):
            naiv_zahlen += 1
    if naiv_zahlen == len(KURZ_UNTER_3J):
        print(f"    OK — die naive Fassung liefert fuer alle {naiv_zahlen} "
              "Faelle eine Zahl; der Schutz ist also wirksam")
    else:
        print(f"    FEHLER — die Gegenprobe greift nicht: naiv nur "
              f"{naiv_zahlen} von {len(KURZ_UNTER_3J)} Zahlen")
        f += 1

    # (e) IM GEMEINSAMEN ZEITRAUM DARF NIEMAND FEHLEN — er ist ja gerade so
    # gewaehlt, dass alle ihn abdecken. Faellt hier jemand raus, stimmt die
    # Ableitung des Fensters nicht.
    gemein = kennzahlen_je_strategie(reihen, GEMEINSAM)
    raus = sorted(gemein.index[~gemein["abgedeckt"].astype(bool)])
    if raus:
        print(f"    FEHLER — im gemeinsamen Zeitraum fehlen {raus}")
        f += 1
    else:
        print(f"    OK — im gemeinsamen Zeitraum sind alle {len(gemein)} dabei")
    return f


def schritt4_figur():
    print("Schritt 4 — die FIGUR, nicht die Daten (#54)")
    sym = _symbole("modules.strategievergleich",
                   ["X_ACHSEN", "X_DRAWDOWN", "X_VOLA", "punktwolke_figur"])
    if sym is None:
        return 0
    if sym is False:
        return 1
    X_ACHSEN, X_DRAWDOWN = sym["X_ACHSEN"], sym["X_DRAWDOWN"]
    X_VOLA, punktwolke_figur = sym["X_VOLA"], sym["punktwolke_figur"]

    f = 0
    tabelle = pd.DataFrame(
        {"rendite":   [0.05, 0.08, 0.02, np.nan],
         "vola":      [0.06, 0.11, 0.03, np.nan],
         "max_dd":    [-0.12, -0.25, -0.04, np.nan],
         "familie":   ["CVV", "CVV", "ESG", "Thema"],
         "jahre":     [17.6, 7.8, 5.8, 1.7],
         "abgedeckt": [True, True, True, False]},
        index=["A", "B", "C", "D_ohne"])

    for achse in X_ACHSEN:
        fig = punktwolke_figur(tabelle, achse)
        if fig is None:
            print(f"    FEHLER — {achse}: keine Figur")
            f += 1
            continue
        layout = fig.layout

        # (a) ACHSENTYPEN GESETZT statt geraten. Genau dieses Feld stand am
        # 14.08.2026 auf None und liess die Bandbreite zusammenfallen.
        for name, achse_obj in (("xaxis", layout.xaxis), ("yaxis", layout.yaxis)):
            if achse_obj.type != "linear":
                print(f"    FEHLER — {achse}/{name}.type = {achse_obj.type!r}")
                f += 1

        # (b) Kein nicht abgedeckter Punkt darf im Chart landen.
        punkte = sum(len(sp.x) for sp in fig.data)
        if punkte != 3:
            print(f"    FEHLER — {achse}: {punkte} Punkte statt 3")
            f += 1

        # (c) Je Familie eine Spur, in stabiler Reihenfolge.
        namen = [sp.name for sp in fig.data]
        if namen != ["CVV", "ESG"]:
            print(f"    FEHLER — {achse}: Spuren {namen} statt ['CVV', 'ESG']")
            f += 1

        # (d) DIE X-WERTE SIND BETRAEGE. Beim Drawdown ist das der Punkt: Eine
        # Achse von -25 nach 0 wuerde die Leserichtung gegenueber der
        # Volatilitaets-Ansicht umdrehen.
        x_alle = [w for sp in fig.data for w in sp.x]
        if any(w < 0 for w in x_alle):
            print(f"    FEHLER — {achse}: negative X-Werte {x_alle}")
            f += 1

        # (e) Namen am Punkt.
        if not all("text" in (sp.mode or "") for sp in fig.data):
            print(f"    FEHLER — {achse}: keine Namen am Punkt")
            f += 1

    if not f:
        print("    OK — beide Achsen: Typ gesetzt, 3 Punkte, 2 Spuren, "
              "X-Werte nicht negativ, Namen am Punkt")

    # (f) Der Drawdown-Betrag ist wirklich der Betrag des Werts.
    fig = punktwolke_figur(tabelle, X_DRAWDOWN)
    x_cvv = list(fig.data[0].x)
    f += _nah("Drawdown-Betrag A", x_cvv[0], 12.0, 1e-9)
    f += _nah("Drawdown-Betrag B", x_cvv[1], 25.0, 1e-9)

    # (g) Volatilitaet unveraendert in Prozent.
    fig = punktwolke_figur(tabelle, X_VOLA)
    f += _nah("Volatilitaet A", list(fig.data[0].x)[0], 6.0, 1e-9)

    # (h) NAMEN IMMER AM PUNKT, auch bei vielen (Philip, 18.08.2026).
    # Eine erste Fassung liess sie ab 13 Punkten in den Hover wandern; im
    # Kundengespraech wird auf den Bildschirm gezeigt und nicht mit der Maus
    # darueber gefahren. Dieser Schritt haelt die Entscheidung fest — sonst
    # baut sie jemand aus Ruecksicht auf die Lesbarkeit wieder zurueck.
    viele = pd.concat([tabelle.iloc[:3]] * 9)          # 27 Punkte
    viele.index = [f"S{i}" for i in range(len(viele))]
    fig = punktwolke_figur(viele, X_VOLA)
    fehlt = [sp.name for sp in fig.data if "text" not in (sp.mode or "")]
    if fehlt:
        print(f"    FEHLER — bei {len(viele)} Punkten fehlen die Namen: {fehlt}")
        f += 1
    elif any(len(sp.text) != len(sp.x) for sp in fig.data):
        print("    FEHLER — nicht jeder Punkt traegt einen Namen")
        f += 1
    else:
        print(f"    OK — auch bei {len(viele)} Punkten traegt JEDER seinen Namen")

    # (h2) Und die Namen duerfen am Rand nicht abgeschnitten werden — sonst
    # verliert ausgerechnet der aeusserste Punkt seine Beschriftung.
    if any(sp.cliponaxis is not False for sp in fig.data):
        print("    FEHLER — cliponaxis nicht abgeschaltet, Randnamen werden beschnitten")
        f += 1
    else:
        print("    OK — Namen am Rand werden nicht abgeschnitten")

    # (i) Keine abgedeckte Zeile -> KEINE Figur, damit die Ansicht einen Satz
    # zeigen kann statt einer leeren Flaeche.
    leer = tabelle[tabelle["abgedeckt"] == False]  # noqa: E712
    if punktwolke_figur(leer, X_VOLA) is not None:
        print("    FEHLER — leere Auswahl liefert trotzdem eine Figur")
        f += 1
    else:
        print("    OK — ohne abgedeckte Strategie gibt es keine Figur")
    return f


def schritt5_apptest():
    print("Schritt 5 — die Oberflaeche faehrt hoch (AppTest)")
    import importlib.util
    if importlib.util.find_spec("streamlit.testing.v1") is None:
        print("    UEBERSPRUNGEN — streamlit.testing nicht verfuegbar")
        return 0
    from streamlit.testing.v1 import AppTest
    from modules.strategievergleich import GEMEINSAM, X_DRAWDOWN

    f = 0

    def _lauf(bez, **zustand):
        nonlocal f
        at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                               default_timeout=400)
        at.secrets["passwords"] = {"t": "t"}
        at.session_state["logged_in"] = True
        at.session_state["username"] = "t"
        at.session_state["nav_view"] = "Strategievergleich"
        for k, v in zustand.items():
            at.session_state[k] = v
        at.run()
        if at.exception:
            for e in at.exception:
                print(f"    FEHLER — {bez}: {str(e.value)[:200]}")
            f += 1
            return None
        print(f"    OK — {bez}")
        return at

    at = _lauf("Vorbelegung")
    if at is not None:
        # Der Tab muss auch wirklich DIESE Ansicht zeigen und nicht still auf
        # die Portfolioanalyse zurueckfallen.
        if not any("Risiko-Rendite" in s.value for s in at.subheader):
            print("    FEHLER — die Ueberschrift der Ansicht fehlt")
            f += 1
        # Und der Hinweis auf die ausgelassenen Strategien muss dastehen:
        # bei der Vorbelegung "3 Jahre" sind es fuenf.
        elif not any("Nicht gezeigt" in c.value for c in at.caption):
            print("    FEHLER — der Hinweis auf ausgelassene Strategien fehlt")
            f += 1
        else:
            print("    OK — Ueberschrift und Auslassungs-Hinweis stehen da")

    _lauf("Max Drawdown auf der X-Achse", sv_xachse=X_DRAWDOWN)
    _lauf("gemeinsamer Zeitraum", sv_periode=GEMEINSAM)
    _lauf("kurzer Zeitraum", sv_periode="YTD")
    _lauf("langer Zeitraum (nur 7 von 19 decken ihn ab)", sv_periode="10 Jahre")
    _lauf("nur eine Familie", sv_familien=["CVV"])
    _lauf("keine Familie gewaehlt", sv_familien=[])
    _lauf("Tabelle eingeblendet", sv_tabelle=True)
    # Der eigene Zeitraum blendet zwei Kalenderfelder und einen Knopf ein
    # (24.08.2026). Geprueft wird hier nur, dass die Ansicht dabei steht;
    # was die Felder BEWIRKEN, misst Schritt 11 streamlit-frei.
    _lauf("eigener Zeitraum eingeblendet", sv_zeit_frei=True)
    return f


def schritt6_umschalter():
    print("Schritt 6 — der X-Achsen-Umschalter ist ein segmented_control")
    import ast
    quelle = os.path.join(WURZEL, "modules", "strategievergleich.py")
    with open(quelle, encoding="utf-8") as fh:
        baum = ast.parse(fh.read())

    f = 0
    gefunden = []
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Call):
            continue
        ziel = getattr(knoten.func, "attr", None)
        if ziel not in ("radio", "segmented_control"):
            continue
        schluessel = None
        required = False
        for kw in knoten.keywords:
            if kw.arg == "key" and isinstance(kw.value, ast.Constant):
                schluessel = kw.value.value
            if kw.arg == "required" and isinstance(kw.value, ast.Constant):
                required = bool(kw.value.value)
        gefunden.append((ziel, schluessel, required))

    if any(z == "radio" for z, _, _ in gefunden):
        print(f"    FEHLER — es gibt wieder ein st.radio: {gefunden}")
        f += 1
    else:
        print("    OK — kein st.radio mehr im Modul")

    treffer = [g for g in gefunden if g[1] == "sv_xachse"]
    if not treffer:
        print("    FEHLER — kein Umschalter mit key='sv_xachse' gefunden")
        f += 1
    elif treffer[0][0] != "segmented_control":
        print(f"    FEHLER — sv_xachse ist ein {treffer[0][0]}")
        f += 1
    elif not treffer[0][2]:
        print("    FEHLER — sv_xachse ohne required=True: das aktive Segment "
              "liesse sich abwaehlen")
        f += 1
    else:
        print("    OK — sv_xachse ist ein segmented_control mit required=True")

    # ── DIE REIHENFOLGE (NEU 24.08.2026) ────────────────────────────────
    #
    # Der Schalter steht seit heute UNTER dem Zeitraum-Feld und direkt ueber
    # der Grafik. Das ist nicht nur Optik: Sein Rueckgabewert `x_groesse`
    # geht in `punktwolke_figur` und in `_tabelle_zum_anzeigen`. Stuende das
    # Widget im Quelltext HINTER seinen Verbrauchern, waere das entweder ein
    # NameError oder — schlimmer — ein Chart, das die VORHERIGE Auswahl
    # zeichnet, weil eine alte Variable noch im Namensraum liegt. Ein
    # stiller Fehler also, genau die Sorte, die keine Sichtpruefung findet.
    #
    # Geprueft wird deshalb die Zeilennummer, nicht der Augenschein.
    #
    # EHRLICH GESAGT: Vor dem Umzug war dieser Block bereits GRUEN — der
    # Schalter stand in der rechten Spalte, also ohnehin oberhalb. Er faengt
    # also nicht den Umbau vom 24.08.2026, sondern den Rueckfall danach.
    # Ein direkter `NameError` waere harmlos, weil er sofort auffiele; die
    # gefaehrliche Fassung ist die REPARIERTE — Widget nach unten, Wert aus
    # `st.session_state` geholt. Die laeuft durch und zeichnet die vorherige
    # Auswahl. Gegen diese Form ist der Block gebaut.
    ziel_funktion = None
    for knoten in ast.walk(baum):
        if (isinstance(knoten, ast.FunctionDef)
                and knoten.name == "zeige_strategievergleich"):
            ziel_funktion = knoten
    if ziel_funktion is None:
        print("    FEHLER — `zeige_strategievergleich` nicht gefunden")
        return f + 1

    def _zeile(pruefer):
        for k in ast.walk(ziel_funktion):
            if isinstance(k, ast.Call) and pruefer(k):
                return k.lineno
        return None

    def _mit_key(name):
        def _p(k):
            return any(kw.arg == "key" and isinstance(kw.value, ast.Constant)
                       and kw.value.value == name for kw in k.keywords)
        return _p

    schalter = _zeile(lambda k: getattr(k.func, "attr", None)
                      == "segmented_control" and _mit_key("sv_xachse")(k))
    verbraucher = {
        "punktwolke_figur": _zeile(
            lambda k: getattr(k.func, "id", getattr(k.func, "attr", None))
            == "punktwolke_figur"),
        "plotly_chart(sv_wolke)": _zeile(
            lambda k: getattr(k.func, "attr", None) == "plotly_chart"
            and _mit_key("sv_wolke")(k)),
        "_tabelle_zum_anzeigen": _zeile(
            lambda k: getattr(k.func, "id", getattr(k.func, "attr", None))
            == "_tabelle_zum_anzeigen"),
    }
    if schalter is None:
        print("    FEHLER — der Schalter steht nicht in "
              "`zeige_strategievergleich`")
        f += 1
    else:
        spaet = {n: z for n, z in verbraucher.items()
                 if z is not None and z < schalter}
        if spaet:
            print(f"    FEHLER — diese lesen `x_groesse`, bevor der Schalter "
                  f"in Zeile {schalter} steht: "
                  + ", ".join(f"{n} (Zeile {z})" for n, z in spaet.items()))
            f += 1
        elif any(z is None for z in verbraucher.values()):
            fehlt = [n for n, z in verbraucher.items() if z is None]
            print(f"    FEHLER — nicht gefunden: {fehlt}. Der Test prueft "
                  "sonst nichts (#65).")
            f += 1
        else:
            print(f"    OK — der Schalter (Zeile {schalter}) steht vor allen "
                  "drei Verbrauchern")

    # Der Schalter traegt die Ueberschrift nicht selbst — daher collapsed.
    beschriftung = None
    for k in ast.walk(ziel_funktion):
        if (isinstance(k, ast.Call)
                and getattr(k.func, "attr", None) == "segmented_control"
                and _mit_key("sv_xachse")(k)):
            for kw in k.keywords:
                if kw.arg == "label_visibility" and isinstance(kw.value,
                                                              ast.Constant):
                    beschriftung = kw.value.value
    if beschriftung != "collapsed":
        print(f"    FEHLER — sv_xachse ohne label_visibility='collapsed' "
              f"({beschriftung!r}); die eigene Zeile braucht die doppelte "
              "Beschriftung nicht")
        f += 1
    else:
        print("    OK — die Beschriftung ist eingeklappt")

    return f


def _bestaende_fuer_test():
    """Die echten Bestaende, oder None wenn etwas fehlt."""
    try:
        from modules.shared import (DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS,
                                    build_name_lookups, detect_newest_date_tag,
                                    load_name_mapping)
        from modules.portfolioanalyse import build_pf_data, load_pf_csvs
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return None
    dateien = load_pf_csvs(
        DATA_FOLDER_PF, detect_newest_date_tag(DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS))
    if not dateien:
        print("    UEBERSPRUNGEN — keine Bestandsdateien")
        return None
    roh = build_pf_data(dateien)
    namen, d2c, _ = build_name_lookups(load_name_mapping(), set(roh.keys()))
    return {n: roh[d2c[n]] for n in namen}


def schritt7_figuren():
    print("Schritt 7 — die Figuren von Ueberschneidung und Exposure (#54)")
    _namen = ["ACHSE_SEGMENT", "ACHSE_UNTEN_PX", "BALKEN_HOEHE_PX",
              "EBENEN", "EBENE_TITEL", "EXPOSURE_ACHSEN",
              "LEGENDE_ABSTAND_PX", "LEGENDE_JE_ZEILE", "LEGENDE_ZEILE_PX",
              "RAND_OBEN_PX", "REST_FARBEN", "balken_geometrie",
              "balkenhoehe_je_zeile", "exposure_figur", "exposure_tabelle",
              "legendenzeilen", "ueberschneidung_figur",
              "ueberschneidung_tabelle"]
    sym = _symbole("modules.strategievergleich", _namen)
    if sym is None:
        return 0
    if sym is False:
        return 1
    ACHSE_SEGMENT = sym["ACHSE_SEGMENT"]
    ACHSE_UNTEN_PX, BALKEN_HOEHE_PX = sym["ACHSE_UNTEN_PX"], sym["BALKEN_HOEHE_PX"]
    EBENEN, EXPOSURE_ACHSEN = sym["EBENEN"], sym["EXPOSURE_ACHSEN"]
    LEGENDE_ABSTAND_PX = sym["LEGENDE_ABSTAND_PX"]
    LEGENDE_JE_ZEILE, LEGENDE_ZEILE_PX = sym["LEGENDE_JE_ZEILE"], sym["LEGENDE_ZEILE_PX"]
    RAND_OBEN_PX, REST_FARBEN = sym["RAND_OBEN_PX"], sym["REST_FARBEN"]
    balken_geometrie = sym["balken_geometrie"]
    balkenhoehe_je_zeile = sym["balkenhoehe_je_zeile"]
    exposure_figur, exposure_tabelle = sym["exposure_figur"], sym["exposure_tabelle"]
    legendenzeilen = sym["legendenzeilen"]
    ueberschneidung_figur = sym["ueberschneidung_figur"]
    ueberschneidung_tabelle = sym["ueberschneidung_tabelle"]
    EBENE_TITEL_LOKAL = sym["EBENE_TITEL"]
    bestaende = _bestaende_fuer_test()
    if bestaende is None:
        return 0

    f = 0
    bezug = list(bestaende)[0]

    # --- Ueberschneidung ---
    for ebene, spalte in EBENEN.items():
        tab = ueberschneidung_tabelle(bestaende, bezug, spalte)
        fig = ueberschneidung_figur(tab, bezug, ebene)
        if fig is None:
            print(f"    FEHLER — {ebene}: keine Figur")
            f += 1
            continue
        if len(tab) != len(bestaende) - 1:
            print(f"    FEHLER — {ebene}: {len(tab)} Zeilen statt "
                  f"{len(bestaende) - 1}")
            f += 1
        if len(fig.data[0].x) != len(tab):
            print(f"    FEHLER — {ebene}: Balkenzahl != Zeilenzahl")
            f += 1
        # ACHSENTYPEN GESETZT statt geraten
        if fig.layout.xaxis.type != "linear" or fig.layout.yaxis.type != "category":
            print(f"    FEHLER — {ebene}: Achsentypen "
                  f"{fig.layout.xaxis.type!r}/{fig.layout.yaxis.type!r}")
            f += 1
        # GROESSTE OBEN. Plotly zeichnet den ersten Eintrag unten, deshalb
        # muss categoryarray umgedreht sein — sonst steht die Liste auf dem
        # Kopf, ohne dass es jemandem auffaellt (der Heatmap-Fehler vom 14.08.).
        if list(fig.layout.yaxis.categoryarray) != list(reversed(list(tab.index))):
            print(f"    FEHLER — {ebene}: Reihenfolge der y-Achse")
            f += 1
        # DIE NAMEN MUESSEN PLATZ BEKOMMEN. Ein festes `margin.l` schneidet
        # die laengsten Strategienamen ab; am Figur-Objekt sieht man das
        # nicht, nur am gerenderten Bild (#54, gemeldet 18.08.2026).
        if not fig.layout.yaxis.automargin or fig.layout.margin.l is not None:
            print(f"    FEHLER — {ebene}: y-Achse ohne automargin oder mit "
                  f"festem linken Rand ({fig.layout.margin.l})")
            f += 1
        if list(tab["anteil"]) != sorted(tab["anteil"], reverse=True):
            print(f"    FEHLER — {ebene}: nicht absteigend sortiert")
            f += 1
    print("    OK — Ueberschneidung: 5 Ebenen, Achsentypen, Reihenfolge, Sortierung")

    # Die Bezugsstrategie darf NICHT gegen sich selbst auftauchen.
    tab = ueberschneidung_tabelle(bestaende, bezug, "WKN")
    if bezug in tab.index:
        print("    FEHLER — die Bezugsstrategie steht in ihrer eigenen Liste")
        f += 1
    else:
        print("    OK — die Bezugsstrategie steht nicht in ihrer eigenen Liste")

    # --- Exposure ---
    for achse in EXPOSURE_ACHSEN:
        gattung = "Aktien" if achse == ACHSE_SEGMENT else None
        tab = exposure_tabelle(bestaende, achse, gattung)
        fig = exposure_figur(tab, achse)
        if fig is None:
            print(f"    FEHLER — Exposure {achse}: keine Figur")
            f += 1
            continue
        # JEDE ZEILE SUMMIERT AUF 100 % — inklusive Liquiditaet. Das ist die
        # Zusage des Abschnitts; ohne sie behauptet der Balken eine
        # Vollinvestition, die es nicht gibt (#59).
        summen = tab.sum(axis=1)
        if float((summen - 1.0).abs().max()) > 1e-9:
            print(f"    FEHLER — Exposure {achse}: Zeilensumme != 1")
            f += 1
        if fig.layout.barmode != "stack":
            print(f"    FEHLER — Exposure {achse}: barmode {fig.layout.barmode!r}")
            f += 1
        if fig.layout.xaxis.type != "linear" or fig.layout.yaxis.type != "category":
            print(f"    FEHLER — Exposure {achse}: Achsentypen falsch")
            f += 1
        if len(fig.data) != len(tab.columns):
            print(f"    FEHLER — Exposure {achse}: {len(fig.data)} Spuren, "
                  f"{len(tab.columns)} Spalten")
            f += 1
        if not fig.layout.yaxis.automargin or fig.layout.margin.l is not None:
            print(f"    FEHLER — Exposure {achse}: y-Achse ohne automargin "
                  f"oder mit festem linken Rand ({fig.layout.margin.l})")
            f += 1
        for spur in fig.data:
            if len(spur.x) != len(tab):
                print(f"    FEHLER — Exposure {achse}: Spur {spur.name} zu kurz")
                f += 1
                break
    print(f"    OK — Exposure: {len(EXPOSURE_ACHSEN)} Achsen, jede Zeile 100 %, "
          "gestapelt, Achsentypen gesetzt")

    # DIE SAMMELPOSTEN, und hier hat sich die Regel am 18.08.2026 geaendert:
    #
    # Auf den ANDEREN Achsen tragen sie weiter ihre gedaempften eigenen
    # Farben - sonst saehe die Liquiditaet dort aus wie eine Anlagekategorie
    # neben Regionen oder Waehrungen, zu denen sie nicht gehoert.
    #
    # Auf der GATTUNGS-Achse ist die Liquiditaet dagegen SELBST eine
    # Assetklasse und bekommt ihre feste Farbe aus dem Corporate Design.
    # Die Farbe folgt der Bedeutung, nicht der Rolle im Chart.
    tab = exposure_tabelle(bestaende, "Region")
    fig = exposure_figur(tab, "Region")
    for spur in fig.data:
        if spur.name in REST_FARBEN and spur.marker.color != REST_FARBEN[spur.name]:
            print(f"    FEHLER — Region/{spur.name} traegt nicht seine "
                  "Sammelfarbe")
            f += 1
    print("    OK — auf anderen Achsen tragen die Sammelposten gedaempfte Farben")

    from modules.farben import gattung_farbe as _gf
    tab = exposure_tabelle(bestaende, "Gattung")
    fig = exposure_figur(tab, "Gattung")
    for spur in fig.data:
        soll = _gf(spur.name)
        if spur.marker.color != soll:
            print(f"    FEHLER — Gattung/{spur.name}: {spur.marker.color} "
                  f"statt {soll}")
            f += 1
    print("    OK — auf der Gattungs-Achse gilt die feste Farbe, auch fuer "
          "die Liquiditaet")

    # DER MARKTRISIKOWERT DARF NICHT ZURUECKKOMMEN (Philip, 18.08.2026). Er
    # war gebaut und ist wieder ausgebaut worden: Das Haus legt ihn im Asset
    # Management selbst fest, im Beratungswerkzeug saehe er neben gemessenen
    # Groessen aus wie eine Beobachtung. Der Schritt haelt die Entscheidung
    # fest, damit sie niemand aus Versehen rueckgaengig macht - die Spalte
    # liegt schliesslich weiter in den Daten.
    if any("risiko" in a.lower() for a in EXPOSURE_ACHSEN):
        print(f"    FEHLER — Marktrisikowert wieder in EXPOSURE_ACHSEN: "
              f"{EXPOSURE_ACHSEN}")
        f += 1
    else:
        print("    OK — der Marktrisikowert ist nicht unter den Achsen")

    # --- GEOMETRIE (18.08.2026, nach einem gemeldeten Fehler) ---
    #
    # Gemeldet: Bei zwei Strategien und "Segment innerhalb Aktien" ueberdeckte
    # die Legende die Achsenbeschriftung "Anteil am Depot". Ursachen waren ein
    # Legenden-y RELATIV ZUR ZEICHENFLAECHE (das schrumpfte bei kurzen Charts)
    # und ein unterer Rand, der nie fuer die Legende reserviert wurde.
    #
    # Geprueft wird deshalb die RECHNUNG, nicht das Bild (#54): Wie viel Platz
    # reserviert die Figur, und haengt die Legende am Rand der FIGUR?

    # (j) Die Zeilenzahl der Legende ist exakt, nicht geschaetzt.
    for eintraege, soll in ((0, 0), (1, 1), (3, 1), (4, 2), (11, 4), (15, 5)):
        if legendenzeilen(eintraege) != soll:
            print(f"    FEHLER — {eintraege} Eintraege ergeben "
                  f"{legendenzeilen(eintraege)} Zeilen statt {soll}")
            f += 1
    print(f"    OK — Legendenzeilen = aufgerundet durch {LEGENDE_JE_ZEILE}")

    # (k) Der untere Rand waechst mit der Zahl der Segmente. DAS ist der
    # behobene Fehler: Vorher war er gar nicht gesetzt.
    ohne = balken_geometrie(2, 0)[1]
    mit_wenig = balken_geometrie(2, 3)[1]
    mit_viel = balken_geometrie(2, 11)[1]
    if not (ohne < mit_wenig < mit_viel):
        print(f"    FEHLER — unterer Rand waechst nicht mit der Segmentzahl: "
              f"{ohne} / {mit_wenig} / {mit_viel}")
        f += 1
    elif ohne != ACHSE_UNTEN_PX:
        print(f"    FEHLER — ohne Legende sollte der Rand {ACHSE_UNTEN_PX} "
              f"sein, ist {ohne}")
        f += 1
    else:
        soll = ACHSE_UNTEN_PX + LEGENDE_ABSTAND_PX + 4 * LEGENDE_ZEILE_PX
        if mit_viel != soll:
            print(f"    FEHLER — 11 Segmente ergeben {mit_viel} statt {soll}")
            f += 1
        else:
            print(f"    OK — unterer Rand {ohne} ohne Legende, {mit_viel} bei "
                  "elf Segmenten (vier Zeilen)")

    # (l) Feste Hoehe je Balken, bis der Deckel greift.
    for anzahl in (1, 2, 5, 15):
        if abs(balkenhoehe_je_zeile(anzahl) - BALKEN_HOEHE_PX) > 1e-9:
            print(f"    FEHLER — bei {anzahl} Balken ist die Hoehe je Balken "
                  f"{balkenhoehe_je_zeile(anzahl)} statt {BALKEN_HOEHE_PX}")
            f += 1
    if balkenhoehe_je_zeile(19) >= BALKEN_HOEHE_PX:
        print("    FEHLER — bei 19 Balken greift der Deckel nicht")
        f += 1
    if balkenhoehe_je_zeile(200) < 20:
        print("    FEHLER — der Boden haelt nicht, Balken werden unlesbar")
        f += 1
    print(f"    OK — {BALKEN_HOEHE_PX} px je Balken, Deckel greift ab 16")

    # (m) Die Hoehe geht auf: oben + Zeichenflaeche + unten.
    for balken, eintraege in ((2, 11), (5, 4), (19, 15), (1, 0)):
        hoehe, unten = balken_geometrie(balken, eintraege)
        soll = round(RAND_OBEN_PX + balken * balkenhoehe_je_zeile(balken)
                     + unten)
        if hoehe != soll:
            print(f"    FEHLER — {balken}/{eintraege}: Hoehe {hoehe} statt {soll}")
            f += 1
    print("    OK — Hoehe = oben + Balken + unten")

    # (n) AN DER ECHTEN FIGUR, ueber alle Achsen und Auswahlgroessen: Der
    # reservierte Rand muss zur Zahl der gezeichneten Spuren passen, und die
    # Legende muss am Rand der FIGUR haengen.
    namen_alle = list(bestaende)
    for achse in EXPOSURE_ACHSEN:
        gattung = "Aktien" if achse == ACHSE_SEGMENT else None
        for k in (2, 5, len(namen_alle)):
            aus = {n: bestaende[n] for n in namen_alle[:k]}
            tab = exposure_tabelle(aus, achse, gattung)
            fig = exposure_figur(tab, achse)
            if fig is None:
                continue
            soll_h, soll_u = balken_geometrie(len(tab), len(tab.columns))
            if fig.layout.margin.b != soll_u:
                print(f"    FEHLER — {achse}/{k}: margin.b {fig.layout.margin.b} "
                      f"statt {soll_u}")
                f += 1
            if fig.layout.height != soll_h:
                print(f"    FEHLER — {achse}/{k}: Hoehe {fig.layout.height} "
                      f"statt {soll_h}")
                f += 1
            if fig.layout.margin.t != RAND_OBEN_PX:
                print(f"    FEHLER — {achse}/{k}: margin.t falsch")
                f += 1
            # DIE LEGENDE HAENGT AN DER FIGUR, NICHT AN DER ZEICHENFLAECHE.
            # Mit Paper-Bezug schrumpfte der Abstand genau dann, wenn er
            # gebraucht wurde — bei wenigen Strategien.
            if fig.layout.legend.yref != "container" or fig.layout.legend.y != 0:
                print(f"    FEHLER — {achse}/{k}: Legende haengt an "
                      f"{fig.layout.legend.yref!r} bei y={fig.layout.legend.y}")
                f += 1
            # OHNE feste Eintragsbreite waere die Zeilenzahl wieder geraten.
            if (fig.layout.legend.entrywidthmode != "fraction"
                    or abs(fig.layout.legend.entrywidth
                           - 1.0 / LEGENDE_JE_ZEILE) > 1e-9):
                print(f"    FEHLER — {achse}/{k}: Eintragsbreite nicht fest")
                f += 1
    print(f"    OK — {len(EXPOSURE_ACHSEN)} Achsen x 3 Auswahlgroessen: Rand, "
          "Hoehe und Legendenverankerung stimmen")

    # (o) Der GEMELDETE FALL namentlich, damit er nicht still zurueckkommt.
    zwei = {n: bestaende[n] for n in ("Pro", "Pro Dividende")
            if n in bestaende}
    if len(zwei) == 2:
        tab = exposure_tabelle(zwei, ACHSE_SEGMENT, "Aktien")
        fig = exposure_figur(tab, ACHSE_SEGMENT)
        zeilen = legendenzeilen(len(tab.columns))
        if zeilen < 2:
            print(f"    FEHLER — der gemeldete Fall hat nur {zeilen} "
                  "Legendenzeile(n); pruefte er je den Fehler?")
            f += 1
        elif fig.layout.margin.b <= ACHSE_UNTEN_PX:
            print(f"    FEHLER — Pro/Pro Dividende, Segment/Aktien: unterer "
                  f"Rand {fig.layout.margin.b} laesst der Legende keinen Platz")
            f += 1
        else:
            print(f"    OK — der gemeldete Fall: {len(tab.columns)} Segmente, "
                  f"{zeilen} Legendenzeilen, unterer Rand {fig.layout.margin.b} px")
    else:
        print("    UEBERSPRUNGEN — Pro / Pro Dividende nicht im Bestand")

    # (p) Auch die Ueberschneidung rechnet mit derselben Formel — dort ohne
    # Legende, also nur der Achsentitel-Platz.
    tab_ue = ueberschneidung_tabelle(bestaende, bezug, "WKN")
    fig_ue = ueberschneidung_figur(tab_ue, bezug, EBENE_TITEL_LOKAL)
    soll_h, soll_u = balken_geometrie(len(tab_ue), 0)
    if fig_ue.layout.margin.b != soll_u or fig_ue.layout.height != soll_h:
        print(f"    FEHLER — Ueberschneidung: {fig_ue.layout.height}/"
              f"{fig_ue.layout.margin.b} statt {soll_h}/{soll_u}")
        f += 1
    else:
        print(f"    OK — Ueberschneidung nutzt dieselbe Rechnung "
              f"({soll_h} px, unten {soll_u})")

    # Leere Eingaben -> keine Figur, damit die Ansicht einen Satz zeigen kann.
    if (ueberschneidung_figur(ueberschneidung_tabelle({}, "x", "WKN"), "x", "WKN")
            is not None):
        print("    FEHLER — leere Ueberschneidung liefert eine Figur")
        f += 1
    elif exposure_figur(exposure_tabelle({}, "Gattung"), "Gattung") is not None:
        print("    FEHLER — leeres Exposure liefert eine Figur")
        f += 1
    else:
        print("    OK — ohne Bestaende gibt es keine Figur")
    return f


def schritt8_apptest_bestand():
    print("Schritt 8 — die Oberflaeche der beiden neuen Abschnitte (AppTest)")
    import importlib.util
    if importlib.util.find_spec("streamlit.testing.v1") is None:
        print("    UEBERSPRUNGEN — streamlit.testing nicht verfuegbar")
        return 0
    from streamlit.testing.v1 import AppTest
    from modules.strategievergleich import (EBENEN, EXPOSURE_ACHSEN,
                                            UE_EXKLUSIV)

    f = 0

    def _lauf(bez, **zustand):
        nonlocal f
        at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                               default_timeout=400)
        at.secrets["passwords"] = {"t": "t"}
        at.session_state["logged_in"] = True
        at.session_state["username"] = "t"
        at.session_state["nav_view"] = "Strategievergleich"
        for k, v in zustand.items():
            at.session_state[k] = v
        at.run()
        if at.exception:
            for e in at.exception:
                print(f"    FEHLER — {bez}: {str(e.value)[:200]}")
            f += 1
            return None
        return at

    at = _lauf("Vorbelegung")
    if at is not None:
        ueberschriften = [s.value for s in at.subheader]
        for erwartet in ("Überschneidung der Strategien", "Exposure im Vergleich"):
            if erwartet not in ueberschriften:
                print(f"    FEHLER — Überschrift fehlt: {erwartet}")
                f += 1
        if f == 0:
            print("    OK — beide Abschnitte erscheinen")

    for ebene in EBENEN:
        if _lauf(f"Ebene {ebene}", sv_ue_ebene=ebene) is not None:
            print(f"    OK — Ebene {ebene}")

    for achse in EXPOSURE_ACHSEN:
        if _lauf(f"Exposure {achse}", sv_ex_achse=achse) is not None:
            print(f"    OK — Exposure {achse}")

    if _lauf("Segment innerhalb Renten", sv_ex_achse="Segment",
             sv_ex_gattung="Renten") is not None:
        print("    OK — Segment innerhalb Renten")

    # EINE Strategie: die Ueberschneidung braucht zwei und muss das sagen,
    # statt eine leere Flaeche zu zeigen.
    # Die zweite Ansicht der Ueberschneidung (24.08.2026). `sv_ue_ansicht`
    # ist ein LITERALER Key und wirkt deshalb ueber session_state — anders
    # als `sv_ue_ebene`, das in Wahrheit `sv_ue_ebene_<kennung>` heisst.
    if _lauf("Nicht-Ueberschneidung", sv_ue_ansicht=UE_EXKLUSIV) is not None:
        print("    OK — Nicht-Ueberschneidung")

    at = _lauf("nur eine Strategie", sv_familien=[])
    if at is not None:
        print("    OK — leere Familienauswahl")

    if _lauf("beide Tabellen eingeblendet", sv_ue_tabelle=True,
             sv_ex_tabelle=True) is not None:
        print("    OK — beide Tabellen eingeblendet")
    return f


def schritt9_drilldown():
    print("Schritt 9 — der Drilldown: Auswahl, Balken, deutsche Zahlen")
    sym = _symbole("modules.strategievergleich",
                   ["EBENEN", "EBENE_TITEL", "gewaehlte_gegenpartei",
                    "ueberschneidung_tabelle", "_drilldown_tabelle"])
    if sym is None:
        return 0
    if sym is False:
        return 1
    EBENEN, EBENE_TITEL = sym["EBENEN"], sym["EBENE_TITEL"]
    gewaehlte_gegenpartei = sym["gewaehlte_gegenpartei"]
    ueberschneidung_tabelle = sym["ueberschneidung_tabelle"]
    _drilldown_tabelle = sym["_drilldown_tabelle"]
    bestaende = _bestaende_fuer_test()
    if bestaende is None:
        return 0

    f = 0
    bezug = list(bestaende)[0]
    tabelle = ueberschneidung_tabelle(bestaende, bezug, "WKN")

    # (a) DIE AUFLOESUNG DER AUSWAHL. Ohne Klick die staerkste Zeile, also nie
    # ein leerer Zustand.
    if gewaehlte_gegenpartei(None, tabelle) != tabelle.index[0]:
        print("    FEHLER — ohne Auswahl nicht die staerkste Zeile")
        f += 1
    else:
        print(f"    OK — ohne Auswahl: {tabelle.index[0]}")

    # Ein echter Treffer wird uebernommen ...
    ziel = tabelle.index[3]
    treffer = {"selection": {"points": [{"y": ziel}]}}
    f += 0 if gewaehlte_gegenpartei(treffer, tabelle) == ziel else 1

    # ... der Ersatzweg ueber customdata ebenso ...
    ueber_custom = {"selection": {"points": [{"y": None,
                                              "customdata": [ziel, 5]}]}}
    f += 0 if gewaehlte_gegenpartei(ueber_custom, tabelle) == ziel else 1

    # ... und ein Name, den es NICHT MEHR GIBT, faellt zurueck statt zu
    # werfen. Das ist der Fall nach einem Wechsel der Ebene oder der
    # Strategieauswahl (#53).
    veraltet = {"selection": {"points": [{"y": "Gibt es nicht mehr"}]}}
    if gewaehlte_gegenpartei(veraltet, tabelle) != tabelle.index[0]:
        print("    FEHLER — veralteter Name faellt nicht auf die staerkste zurueck")
        f += 1
    for kaputt in ({}, {"selection": {}}, {"selection": {"points": []}}, None):
        try:
            gewaehlte_gegenpartei(kaputt, tabelle)
        except Exception as ex:
            print(f"    FEHLER — {kaputt!r}: {type(ex).__name__}")
            f += 1
    if not f:
        print("    OK — Treffer, Ersatzweg, veralteter Name und Schrott")

    # (b) KEIN BEITRAGSBALKEN MEHR (Philip, 18.08.2026). Die Tabelle trug
    # rechts eine Spalte aus Blockzeichen; am Bildschirm las sie sich als
    # schwarzer Klotz statt als Groessenverhaeltnis. Der Schritt haelt die
    # Entscheidung fest — die Sortierung und das Chart darueber zeigen die
    # Verhaeltnisse, eine Textur braucht es dafuer nicht.
    gegen_pruef = tabelle.index[0]
    probe = _drilldown_tabelle(bestaende, bezug, gegen_pruef, EBENE_TITEL)
    if probe is None:
        print("    FEHLER — keine Drilldown-Tabelle")
        return f + 1
    if "" in probe.columns:
        print("    FEHLER — es gibt wieder eine namenlose Balkenspalte")
        f += 1
    bloecke = [c for c in probe.columns
               if any("\u2588" in str(v) for v in probe[c])]
    if bloecke:
        print(f"    FEHLER — Blockzeichen in den Spalten {bloecke}")
        f += 1
    if not bloecke and "" not in probe.columns:
        print("    OK — keine Balkenspalte, keine Blockzeichen")

    # (c) DIE TABELLE traegt deutsche Zahlen — keine zweite Formatierungs-
    # quelle neben `modules/formats.py`.
    gegen = tabelle.index[0]
    anzeige = _drilldown_tabelle(bestaende, bezug, gegen, EBENE_TITEL)
    if anzeige is None:
        print("    FEHLER — keine Drilldown-Tabelle")
        return f + 1
    prozentspalten = [bezug, gegen, "gemeinsam"]
    for spalte in prozentspalten:
        werte = [w for w in anzeige[spalte] if w != "–"]
        if any("." in w for w in werte):
            print(f"    FEHLER — Spalte {spalte!r} enthaelt Dezimalpunkte: "
                  f"{[w for w in werte if '.' in w][:3]}")
            f += 1
        if not all(w.endswith("%") for w in werte):
            print(f"    FEHLER — Spalte {spalte!r} ohne Prozentzeichen")
            f += 1
    if not f:
        print(f"    OK — {len(anzeige)} Zeilen, deutsche Notation in "
              f"{len(prozentspalten)} Spalten")

    # (d) Auf jeder Ebene eine brauchbare Tabelle, ohne Absturz.
    for ebene in EBENEN:
        t = _drilldown_tabelle(bestaende, bezug, gegen, ebene)
        if t is None or t.empty:
            print(f"    FEHLER — Ebene {ebene}: keine Tabelle")
            f += 1
    print(f"    OK — alle {len(EBENEN)} Ebenen liefern eine Tabelle")
    return f


def schritt10_auswahlfelder():
    print("Schritt 10 — die Auswahlfelder koennen nicht ungueltig werden")
    sym = _symbole("modules.strategievergleich",
                   ["auswahl_kennung", "auswahl_uebernehmen"],
                   pakete=())
    if sym is None:
        return 0
    if sym is False:
        return 1
    auswahl_kennung = sym["auswahl_kennung"]
    auswahl_uebernehmen = sym["auswahl_uebernehmen"]

    f = 0

    # (a) DIE KENNUNG haengt an der MENGE, nicht an der Reihenfolge. Die
    # Reihenfolge folgt der Auswahl des Beraters und kann sich aendern, ohne
    # dass sich die Menge aendert — dann soll das Feld stehen bleiben.
    a = ["cVV konservativ", "cVV defensiv", "Pro"]
    if auswahl_kennung(a) != auswahl_kennung(list(reversed(a))):
        print("    FEHLER — Umsortieren ergibt eine andere Kennung")
        f += 1
    if auswahl_kennung(a) == auswahl_kennung(a[:2]):
        print("    FEHLER — verschiedene Mengen ergeben dieselbe Kennung")
        f += 1
    if auswahl_kennung(a) == auswahl_kennung(a + ["Offensiv"]):
        print("    FEHLER — eine zusaetzliche Option aendert die Kennung nicht")
        f += 1
    if not auswahl_kennung([]):
        print("    FEHLER — leere Menge ohne Kennung")
        f += 1
    if not f:
        print("    OK — Kennung folgt der Menge, nicht der Reihenfolge")

    # (b) DIE UEBERNAHME: der bisherige Wert bleibt, wenn es ihn noch gibt.
    faelle = [
        ("noch dabei",        "cVV defensiv", a,                    "cVV defensiv"),
        ("weggefallen",       "cVV defensiv", ["Pro", "Pro Div."],  "Pro"),
        ("kein Vorwert",      None,           a,                    a[0]),
        ("Vorwert unbekannt", "Gibt es nicht", a,                   a[0]),
        ("keine Optionen",    "Pro",          [],                   None),
    ]
    for bez, vorher, optionen, soll in faelle:
        ist = auswahl_uebernehmen(vorher, optionen)
        if ist != soll:
            print(f"    FEHLER — {bez}: {ist!r} statt {soll!r}")
            f += 1
    print("    OK — bisherige Wahl bleibt, sonst rueckt die erste nach")

    # (c) DIE ZUSAGE, und sie ist der eigentliche Punkt: Was auch immer im
    # Feld stand — der uebernommene Wert liegt IMMER in den Optionen. Genau
    # das war beim gemeldeten Fehler verletzt.
    reihen = _echte_reihen()
    if reihen is None:
        return f
    namen = [r[0] for r in reihen]
    import itertools
    import random
    wuerfel = random.Random(20260818)     # fester Keim: reproduzierbar
    verletzt = 0
    geprueft = 0
    # Jede Zweierkombination plus 200 zufaellige Teilmengen — der gemeldete
    # Fall (19 -> 2) ist darunter, und die zufaelligen decken die Wege ab,
    # die niemand von Hand durchspielt.
    mengen = [list(paar) for paar in itertools.combinations(namen, 2)]
    for _ in range(200):
        k = wuerfel.randint(1, len(namen))
        mengen.append(wuerfel.sample(namen, k))
    for optionen in mengen:
        for vorher in (None, namen[0], namen[-1], "Gibt es nicht mehr"):
            wert = auswahl_uebernehmen(vorher, optionen)
            geprueft += 1
            if wert not in optionen:
                verletzt += 1
                if verletzt == 1:
                    print(f"    FEHLER — {vorher!r} bei {len(optionen)} "
                          f"Optionen ergibt {wert!r}, das nicht dabei ist")
    if verletzt:
        print(f"    FEHLER — {verletzt} von {geprueft} Faellen liefern einen "
              "ungueltigen Wert")
        f += 1
    else:
        print(f"    OK — {geprueft} Faelle ueber {len(mengen)} Teilmengen: "
              "der Wert liegt immer in den Optionen")

    # (d) UND DIE UEBERNAHME GREIFT AUCH WIRKLICH: Bei einer Verkleinerung,
    # die den bisherigen Wert enthaelt, darf er NICHT wechseln. Ohne diese
    # Pruefung waere (c) auch mit "nimm immer den ersten" erfuellt.
    behalten = 0
    for optionen in mengen:
        if len(optionen) < 2:
            continue
        vorher = optionen[-1]
        if auswahl_uebernehmen(vorher, optionen) != vorher:
            print(f"    FEHLER — {vorher!r} ist dabei, wird aber nicht behalten")
            f += 1
            break
        behalten += 1
    else:
        print(f"    OK — in {behalten} Faellen bleibt ein noch gueltiger Wert "
              "stehen (kein blindes Zuruecksetzen)")
    return f



# ─────────────────────────────────────────────────────────────────────────────

def schritt11_eigener_zeitraum():
    """Der frei gewaehlte Zeitraum — und der stille Datenverlust darin.

    Der Kern ist nicht, dass ein Fenster gerechnet werden kann, sondern dass
    eine Strategie, die es nicht abdeckt, HERAUSFAELLT statt still ueber
    einen kuerzeren Zeitraum gerechnet zu werden.
    """
    print("Schritt 11 — der eigene Zeitraum")
    sym = _symbole("modules.strategievergleich",
                   ("EIGEN", "GEMEINSAM", "PERIODEN",
                    "kennzahlen_je_strategie", "gemeinsamer_beginn",
                    "nicht_gezeigt_text", "zeitraum_text", "leer_hinweis",
                    "eigener_zeitraum_vorschlag"))
    if sym is None:
        return 0
    if sym is False:
        return 1
    ana = _symbole("modules.analytics",
                   ("deckt_zeitraum_ab", "ZEITRAUM_RAND_TOLERANZ_TAGE",
                    "_perioden_start", "RISIKO_PERIODEN"))
    if ana is None:
        return 0
    if ana is False:
        return 1

    EIGEN = sym["EIGEN"]
    GEM = sym["GEMEINSAM"]
    kjs = sym["kennzahlen_je_strategie"]
    f = 0

    # ── (e) DER ZAUN um `_perioden_start` ────────────────────────────────
    # `_perioden_start` liest die Zahl aus dem Label (`int(bez.split()[0])`).
    # Kaeme "Eigener Zeitraum" dort an, gaebe es einen ValueError mitten in
    # der Rechnung. Der Schutz ist strukturell: die Kennung steht gar nicht
    # erst in der Auswahlliste.
    if EIGEN in sym["PERIODEN"]:
        print(f"    FEHLER — {EIGEN!r} steht in PERIODEN und waere im "
              "Dropdown waehlbar")
        f += 1
    elif not (set(sym["PERIODEN"]) - {GEM}) <= set(ana["RISIKO_PERIODEN"]):
        print("    FEHLER — PERIODEN enthaelt ein Label, das "
              "`_perioden_start` nicht kennt")
        f += 1
    else:
        print("    OK — die Kennung steht nicht in der Auswahlliste")

    reihen = _echte_reihen()
    if reihen is None:
        return f

    try:
        kjs(reihen[:2], "Voelliger Unfug")
    except ValueError:
        print("    OK — ein unbekannter Zeitraum wirft ValueError")
    except Exception as ex:
        print(f"    FEHLER — unbekannter Zeitraum wirft {type(ex).__name__} "
              "statt ValueError")
        f += 1
    else:
        print("    FEHLER — ein unbekannter Zeitraum laeuft stillschweigend "
              "durch")
        f += 1

    # ── (a) KEIN NEUER RECHENWEG ─────────────────────────────────────────
    # Derselbe Zuschnitt muss dieselben Zahlen liefern wie der vorhandene
    # gemeinsame Zeitraum. Waere das nicht so, gaebe es die Mathematik nun
    # zweimal — die Krankheit aus Backlog B/E/F.
    gem_tab = kjs(reihen, GEM)
    eig_tab = kjs(reihen, EIGEN, von=sym["gemeinsamer_beginn"](reihen),
                  bis=None)
    unterschied = []
    for name in gem_tab.index:
        for spalte in ("rendite", "vola", "max_dd"):
            a, b = gem_tab.loc[name, spalte], eig_tab.loc[name, spalte]
            if pd.isna(a) and pd.isna(b):
                continue
            if pd.isna(a) or pd.isna(b) or abs(float(a) - float(b)) > 0:
                unterschied.append(f"{name}/{spalte}: {a} gegen {b}")
    if unterschied:
        print(f"    FEHLER — eigener Zeitraum rechnet anders als "
              f"{GEM!r}: {unterschied[:3]}")
        f += 1
    else:
        print(f"    OK — {len(gem_tab)} Strategien x 3 Groessen: "
              f"zeichengleich mit {GEM!r}")

    # ── (b) DECKUNGSGLEICH MIT EINER FESTEN PERIODE ──────────────────────
    # Die Reihen sind kalendertaeglich und lueckenlos (test_risiko Schritt 6),
    # deshalb ist `index >= start + 1 Tag` dasselbe wie `index > start` — und
    # genau so schneidet `risiko_perioden` die festen Perioden zu.
    ende = max(pd.Timestamp(ts.index.max()) for _, ts, _, _ in reihen)
    start3 = ana["_perioden_start"](ende, "3 Jahre") + pd.Timedelta(days=1)
    fest = kjs(reihen, "3 Jahre")
    frei = kjs(reihen, EIGEN, von=start3, bis=ende)
    abweichung = []
    for name in fest.index:
        if not bool(fest.loc[name, "abgedeckt"]):
            continue
        for spalte in ("rendite", "vola", "max_dd"):
            a, b = fest.loc[name, spalte], frei.loc[name, spalte]
            if pd.isna(a) or pd.isna(b) or abs(float(a) - float(b)) > 0:
                abweichung.append(f"{name}/{spalte}: {a} gegen {b}")
    if abweichung:
        print(f"    FEHLER — der eigene Zeitraum trifft '3 Jahre' nicht "
              f"exakt: {abweichung[:3]}")
        f += 1
    else:
        n = int(fest["abgedeckt"].astype(bool).sum())
        print(f"    OK — {n} abgedeckte Strategien treffen '3 Jahre' exakt")

    # ── (c) DIE FALLE, NAMENTLICH (#64) ──────────────────────────────────
    # Wer 2020 als Beginn waehlt, verlangt einen Zeitraum, den fuenf
    # Strategien nicht haben. Sie muessen HERAUSFALLEN und genannt werden.
    von2020 = pd.Timestamp("2020-01-01")
    tab2020 = kjs(reihen, EIGEN, von=von2020, bis=ende)
    soll_raus = {n for n, ts, _, _ in reihen
                 if pd.Timestamp(ts.index.min()) > von2020 + pd.Timedelta(days=1)}
    ist_raus = set(tab2020.index[~tab2020["abgedeckt"].astype(bool)])
    if not soll_raus:
        print("    FEHLER — Testfall taugt nicht: 2020 deckt alle ab")
        f += 1
    elif ist_raus != soll_raus:
        print(f"    FEHLER — herausgefallen {sorted(ist_raus)}, erwartet "
              f"{sorted(soll_raus)}")
        f += 1
    else:
        print(f"    OK — {len(soll_raus)} Strategien fallen heraus: "
              f"{sorted(soll_raus)}")

    text = sym["nicht_gezeigt_text"](tab2020)
    ungenannt = [n for n in soll_raus if n not in text]
    if ungenannt:
        print(f"    FEHLER — nicht im Hinweis genannt: {ungenannt}")
        f += 1
    else:
        print("    OK — der Hinweis nennt jede davon beim Namen")

    # DIE GEGENPROBE: So haette es eine Fassung OHNE `deckt_zeitraum_ab`
    # gemacht — zuschneiden und rechnen, was im Fenster liegt. Liefert sie
    # fuer dieselben Faelle ebenfalls Fehlwerte, prueft (c) gar nichts.
    naiv_mit_zahl = 0
    for name, ts, fee, _fam in reihen:
        if name not in soll_raus:
            continue
        teil = ts.loc[(ts.index >= von2020) & (ts.index <= ende)]
        if len(teil) >= 2:
            from modules.analytics import risiko_perioden as _rp
            if pd.notna(_rp(teil, fee).loc["Seit Auflage", "rendite"]):
                naiv_mit_zahl += 1
    if naiv_mit_zahl != len(soll_raus):
        print(f"    FEHLER — die Gegenprobe greift nicht: die naive Fassung "
              f"liefert nur fuer {naiv_mit_zahl} von {len(soll_raus)} eine Zahl")
        f += 1
    else:
        print(f"    OK — die naive Fassung haette fuer alle {len(soll_raus)} "
              "eine Zahl geliefert")

    # ── (d) BEIDE RAENDER, GLEICHE TOLERANZ ──────────────────────────────
    deckt = ana["deckt_zeitraum_ab"]
    tol = ana["ZEITRAUM_RAND_TOLERANZ_TAGE"]
    _, ts0, _, _ = reihen[0]
    mn, mx = pd.Timestamp(ts0.index.min()), pd.Timestamp(ts0.index.max())
    tag = pd.Timedelta(days=1)
    raender = [
        ("von = erster Tag", mn, None, True),
        ("von = erster Tag - Toleranz", mn - tol * tag, None, True),
        ("von = erster Tag - Toleranz - 1", mn - (tol + 1) * tag, None, False),
        ("bis = letzter Tag", None, mx, True),
        ("bis = letzter Tag + Toleranz", None, mx + tol * tag, True),
        ("bis = letzter Tag + Toleranz + 1", None, mx + (tol + 1) * tag, False),
    ]
    schief = [b for b, v, bi, soll in raender if deckt(ts0, v, bi) is not soll]
    if schief:
        print(f"    FEHLER — die Raender verhalten sich ungleich: {schief}")
        f += 1
    else:
        print(f"    OK — beide Raender mit derselben Toleranz ({tol} Tag)")

    # ── (f) Grenzfaelle ──────────────────────────────────────────────────
    leer = kjs([], EIGEN, von=von2020, bis=ende)
    if not leer.empty:
        print("    FEHLER — leere Reihenliste liefert Zeilen")
        f += 1
    gleich = kjs(reihen[:3], EIGEN, von=ende, bis=ende)
    if bool(gleich["abgedeckt"].any()):
        print("    FEHLER — von == bis liefert eine abgedeckte Strategie")
        f += 1
    verdreht = kjs(reihen[:3], EIGEN, von=ende, bis=von2020)
    if bool(verdreht["abgedeckt"].any()):
        print("    FEHLER — von > bis liefert eine abgedeckte Strategie")
        f += 1
    ohne = kjs(reihen[:3], EIGEN, von=None, bis=None)
    if not bool(ohne["abgedeckt"].all()):
        print("    FEHLER — ohne Grenzen ist nicht alles abgedeckt")
        f += 1
    print("    OK — leer, von==bis, von>bis und ohne Grenzen verhalten sich")

    # ── Die Textbausteine ────────────────────────────────────────────────
    t_eigen = sym["zeitraum_text"](reihen, EIGEN, von=von2020, bis=ende)
    if not t_eigen or "2020" not in t_eigen:
        print(f"    FEHLER — der Zeitraum-Satz nennt den Beginn nicht: "
              f"{t_eigen!r}")
        f += 1
    else:
        print("    OK — der Zeitraum-Satz nennt Beginn und Ende")

    h_fest, h_eigen = sym["leer_hinweis"]("3 Jahre"), sym["leer_hinweis"](EIGEN)
    if not h_fest or not h_eigen or h_fest == h_eigen:
        print("    FEHLER — `leer_hinweis` unterscheidet die beiden Faelle "
              "nicht")
        f += 1
    elif "kürzer" in h_eigen or "kuerzer" in h_eigen:
        # Beim eigenen Zeitraum ist "waehle einen kuerzeren" die genau
        # falsche Anweisung — das Fenster kann zu kurz sein, nicht zu lang.
        print(f"    FEHLER — der eigene Zeitraum raet zu einem kuerzeren "
              f"Zeitraum: {h_eigen!r}")
        f += 1
    else:
        print("    OK — `leer_hinweis` sagt beim eigenen Zeitraum etwas "
              "anderes als bei einer festen Periode")

    v_von, v_bis = sym["eigener_zeitraum_vorschlag"](reihen, "3 Jahre")
    if v_bis != ende.date() or abs((v_bis - v_von).days - 365 * 3) > 4:
        print(f"    FEHLER — die Vorbelegung fuer '3 Jahre' ist "
              f"{v_von} bis {v_bis}")
        f += 1
    else:
        print(f"    OK — die Vorbelegung folgt der Schnellwahl: "
              f"{v_von} bis {v_bis}")

    return f



# ─────────────────────────────────────────────────────────────────────────────

def schritt12_nicht_ueberschneidung():
    """Die zweite Ansicht der Ueberschneidung: Figur, Drilldown, Schalter."""
    print("Schritt 12 — die Nicht-Ueberschneidung in der Anzeige")
    sym = _symbole("modules.strategievergleich",
                   ("UE_GEMEINSAM", "UE_EXKLUSIV", "UE_ANSICHTEN", "EBENEN",
                    "EBENE_TITEL", "ueberschneidung_tabelle",
                    "ueberschneidung_figur", "_drilldown_tabelle",
                    "ue_kernsatz", "ue_gegenrichtung_satz",
                    "ue_ansicht_hinweis", "ue_summen_caption", "ue_vorbehalt"))
    if sym is None:
        return 0
    if sym is False:
        return 1

    GEM, EXK = sym["UE_GEMEINSAM"], sym["UE_EXKLUSIV"]
    EBENEN = sym["EBENEN"]
    tab_fn, fig_fn = sym["ueberschneidung_tabelle"], sym["ueberschneidung_figur"]
    f = 0

    bestaende = _bestaende_fuer_test()
    if bestaende is None:
        return f

    bezug = "cVV ausgewogen"
    if bezug not in bestaende:
        print(f"    FEHLER — {bezug} fehlt im Bestand")
        return f + 1

    # ── Die FIGUR (#54) ──────────────────────────────────────────────────
    tab = tab_fn(bestaende, bezug, "WKN", EXK)
    fig = fig_fn(tab, bezug, EBENE_TITEL_NAME(sym), EXK)
    if fig is None:
        print("    FEHLER — keine Figur fuer die exklusive Ansicht")
        return f + 1
    namen = list(tab.index)
    pruefungen = [
        ("x-Achse linear", fig.layout.xaxis.type, "linear"),
        ("y-Achse category", fig.layout.yaxis.type, "category"),
        ("Reihenfolge umgekehrt",
         list(fig.layout.yaxis.categoryarray), list(reversed(namen))),
        ("cliponaxis False", fig.data[0].cliponaxis, False),
        ("automargin an", fig.layout.yaxis.automargin, True),
        ("kein fester linker Rand", fig.layout.margin.l, None),
        ("ein Balken je Strategie", len(fig.data[0].x), len(namen)),
    ]
    for bez, ist, soll in pruefungen:
        if ist != soll:
            print(f"    FEHLER — {bez}: {ist!r} statt {soll!r}")
            f += 1
    if not f:
        print(f"    OK — {len(pruefungen)} Eigenschaften der Figur stimmen")

    if list(tab["anteil"]) != sorted(tab["anteil"], reverse=True):
        print("    FEHLER — die Tabelle ist nicht absteigend sortiert")
        f += 1
    else:
        print("    OK — absteigend sortiert")

    # Kein Balken darf ueber 100 % gehen — das war der Grund, die L1-Distanz
    # zu verwerfen. Waere sie doch eingebaut, faellt es hier auf.
    if max(fig.data[0].x) > 100.0:
        print(f"    FEHLER — ein Balken geht ueber 100 %: "
              f"{max(fig.data[0].x)}")
        f += 1
    else:
        print(f"    OK — groesster Balken {max(fig.data[0].x):.1f} %, "
              "kein Wert ueber 100")

    # Die beiden Ansichten muessen sich unterscheiden — sonst waere der
    # Schalter eine Attrappe.
    fig_gem = fig_fn(tab_fn(bestaende, bezug, "WKN", GEM), bezug,
                     EBENE_TITEL_NAME(sym), GEM)
    if fig.layout.xaxis.title.text == fig_gem.layout.xaxis.title.text:
        print("    FEHLER — beide Ansichten tragen denselben Achsentitel")
        f += 1
    elif fig.data[0].marker.color == fig_gem.data[0].marker.color:
        print("    FEHLER — beide Ansichten haben dieselbe Balkenfarbe")
        f += 1
    else:
        print(f"    OK — Achsentitel und Farbe unterscheiden sich "
              f"({fig.layout.xaxis.title.text!r})")

    # ── Der Drilldown ────────────────────────────────────────────────────
    gegen = "cVV defensiv plus"
    dd = sym["_drilldown_tabelle"]
    for ebene in EBENEN:
        anzeige = dd(bestaende, bezug, gegen, ebene, EXK)
        if anzeige is None or anzeige.empty:
            print(f"    FEHLER — Ebene {ebene}: keine Aufstellung")
            f += 1
            continue
        text = " ".join(str(v) for v in anzeige.to_numpy().ravel())
        if "\u2588" in text or "%" not in text:
            print(f"    FEHLER — Ebene {ebene}: Blockzeichen oder keine "
                  "Prozentangabe")
            f += 1
        if "." in text.replace("Inc.", "").replace("plc.", "").replace(
                "Corp.", "").replace("AG.", ""):
            pass  # Punkte in Wertpapiernamen sind erlaubt
    print(f"    OK — alle {len(EBENEN)} Ebenen liefern eine Aufstellung")

    anzeige = dd(bestaende, bezug, gegen, EBENE_TITEL_NAME(sym), EXK)
    if "Art" not in anzeige.columns:
        print("    FEHLER — die Spalte 'Art' fehlt")
        f += 1
    elif set(anzeige["Art"]) - {"nur hier", "Übergewicht"}:
        print(f"    FEHLER — unerwartete Art-Werte: {set(anzeige['Art'])}")
        f += 1
    else:
        print(f"    OK — Art-Spalte mit {sorted(set(anzeige['Art']))}")

    # DIE ZUSAGE AN DER ANZEIGE: Die letzte Spalte summiert sich auf die Zahl
    # im Kernsatz. Geprueft wird die ANGEZEIGTE Zeichenkette, nicht der
    # Rohwert — genau dort koennte eine Formatierung etwas verlieren.
    zeile = tab.loc[gegen]
    def _zahl_aus(text):
        return float(str(text).replace("%", "").replace(".", "")
                     .replace(",", ".").strip())
    summe = sum(_zahl_aus(v) for v in anzeige["nur hier"]) / 100.0
    if abs(summe - float(zeile["anteil"])) > 5e-4:
        print(f"    FEHLER — die Spalte summiert {summe} statt "
              f"{float(zeile['anteil'])}")
        f += 1
    else:
        print(f"    OK — die angezeigten Beitraege summieren sich auf "
              f"{summe * 100:.2f} %, die Zahl im Kernsatz")

    if len(anzeige) != int(zeile["schluessel"]):
        print(f"    FEHLER — {len(anzeige)} Zeilen, der Kernsatz nennt "
              f"{int(zeile['schluessel'])}")
        f += 1
    else:
        print(f"    OK — {len(anzeige)} Zeilen, so viele nennt auch der "
              "Kernsatz")

    # ── Die Textbausteine unterscheiden die Ansichten ────────────────────
    paare = [
        ("ue_ansicht_hinweis",
         sym["ue_ansicht_hinweis"](GEM), sym["ue_ansicht_hinweis"](EXK)),
        ("ue_summen_caption",
         sym["ue_summen_caption"](5, 0.25, GEM),
         sym["ue_summen_caption"](5, 0.25, EXK)),
        ("ue_vorbehalt",
         sym["ue_vorbehalt"]("Bestand zum 23.08.2026.", GEM),
         sym["ue_vorbehalt"]("Bestand zum 23.08.2026.", EXK)),
    ]
    for name, a, b in paare:
        if not a or not b or a == b:
            print(f"    FEHLER — {name} unterscheidet die Ansichten nicht")
            f += 1
    kern_g = sym["ue_kernsatz"](bezug, gegen, 0.7, 22, EBENE_TITEL_NAME(sym), GEM)
    kern_e = sym["ue_kernsatz"](bezug, gegen, 0.25, 22, EBENE_TITEL_NAME(sym), EXK)
    if kern_g == kern_e or bezug not in kern_e or gegen not in kern_e:
        print("    FEHLER — der Kernsatz nennt nicht beide Strategien oder "
              "unterscheidet die Ansichten nicht")
        f += 1
    gegen_satz = sym["ue_gegenrichtung_satz"](bezug, gegen, 0.24343)
    if gegen not in gegen_satz or "24,34" not in gegen_satz:
        print(f"    FEHLER — der Gegenrichtungs-Satz nennt die Zahl nicht: "
              f"{gegen_satz!r}")
        f += 1
    else:
        print("    OK — alle Textbausteine unterscheiden die beiden Ansichten")

    # ── Der Schalter per AST ─────────────────────────────────────────────
    import ast
    quelle = os.path.join(WURZEL, "modules", "strategievergleich.py")
    with open(quelle, encoding="utf-8") as fh:
        baum = ast.parse(fh.read())
    treffer = []
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Call):
            continue
        if getattr(knoten.func, "attr", None) not in ("radio",
                                                      "segmented_control"):
            continue
        schluessel, required = None, False
        for kw in knoten.keywords:
            if kw.arg == "key" and isinstance(kw.value, ast.Constant):
                schluessel = kw.value.value
            if kw.arg == "required" and isinstance(kw.value, ast.Constant):
                required = bool(kw.value.value)
        if schluessel == "sv_ue_ansicht":
            treffer.append((getattr(knoten.func, "attr", None), required))
    if not treffer:
        print("    FEHLER — kein Schalter mit literalem key='sv_ue_ansicht'")
        f += 1
    elif treffer[0][0] != "segmented_control":
        print(f"    FEHLER — sv_ue_ansicht ist ein {treffer[0][0]}")
        f += 1
    elif not treffer[0][1]:
        print("    FEHLER — sv_ue_ansicht ohne required=True")
        f += 1
    else:
        print("    OK — sv_ue_ansicht ist ein segmented_control mit "
              "required=True")

    return f


def EBENE_TITEL_NAME(sym):
    """Der Anzeigename der Einzeltitel-Ebene."""
    return sym["EBENE_TITEL"]


def main():
    print("Pruefstein: Strategievergleich\n")
    fehler = 0
    for schritt in (schritt1_rendite, schritt2_zusage_kachel,
                    schritt3_abdeckung, schritt4_figur, schritt5_apptest,
                    schritt6_umschalter, schritt7_figuren,
                    schritt8_apptest_bestand, schritt9_drilldown,
                    schritt10_auswahlfelder,
                    schritt11_eigener_zeitraum,
                    schritt12_nicht_ueberschneidung):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — die Punktwolke zeigt die Zahlen der Kennzahlen-Kachel, "
          "und wer den Zeitraum nicht abdeckt, wird genannt statt gezeichnet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
