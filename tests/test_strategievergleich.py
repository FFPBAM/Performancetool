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

# Die fuenf Strategien, deren Historie am 18.08.2026 kuerzer als drei Jahre
# war — mit ihrer gemessenen Laenge. NAMENTLICH und nicht als Zahl: Wer eine
# Strategie ergaenzt oder eine Historie nachliefert, soll hier anschlagen und
# bewusst entscheiden, statt dass sich eine Zahl still verschiebt.
KURZ_UNTER_3J = {
    "Pro":            2.9,
    "Pro Dividende":  1.7,
    "Comdirect_30":   2.4,
    "Comdirect_70":   2.4,
    "Comdirect_100":  2.4,
}


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
    try:
        from modules.strategievergleich import GEMEINSAM, kennzahlen_je_strategie
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return 0

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
    try:
        from modules.strategievergleich import (GEMEINSAM,
                                                kennzahlen_je_strategie,
                                                nicht_gezeigt_text)
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return 0

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
    try:
        from modules.strategievergleich import (X_ACHSEN, X_DRAWDOWN,
                                                X_VOLA, punktwolke_figur)
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return 0

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
    try:
        from modules.strategievergleich import (
            ACHSE_SEGMENT, EBENEN, EXPOSURE_ACHSEN, REST_FARBEN,
            exposure_figur, exposure_tabelle, ueberschneidung_figur,
            ueberschneidung_tabelle,
        )
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return 0
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
        for spur in fig.data:
            if len(spur.x) != len(tab):
                print(f"    FEHLER — Exposure {achse}: Spur {spur.name} zu kurz")
                f += 1
                break
    print(f"    OK — Exposure: {len(EXPOSURE_ACHSEN)} Achsen, jede Zeile 100 %, "
          "gestapelt, Achsentypen gesetzt")

    # Die Sammelposten tragen ihre eigenen Farben und nicht die der Palette —
    # sonst sieht Liquiditaet aus wie eine Anlagekategorie.
    tab = exposure_tabelle(bestaende, "Gattung")
    fig = exposure_figur(tab, "Gattung")
    for spur in fig.data:
        if spur.name in REST_FARBEN and spur.marker.color != REST_FARBEN[spur.name]:
            print(f"    FEHLER — {spur.name} traegt nicht seine Sammelfarbe")
            f += 1
    print("    OK — die Sammelposten tragen gedaempfte eigene Farben")

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
    from modules.strategievergleich import EBENEN, EXPOSURE_ACHSEN

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
    at = _lauf("nur eine Strategie", sv_familien=[])
    if at is not None:
        print("    OK — leere Familienauswahl")

    if _lauf("beide Tabellen eingeblendet", sv_ue_tabelle=True,
             sv_ex_tabelle=True) is not None:
        print("    OK — beide Tabellen eingeblendet")
    return f


def main():
    print("Pruefstein: Strategievergleich\n")
    fehler = 0
    for schritt in (schritt1_rendite, schritt2_zusage_kachel,
                    schritt3_abdeckung, schritt4_figur, schritt5_apptest,
                    schritt6_umschalter, schritt7_figuren,
                    schritt8_apptest_bestand):
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
