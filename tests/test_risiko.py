"""Pruefstein fuer die Risiko-Kennzahlen (NEU 14.08.2026).

Die wichtigste Zusage steht in Schritt 1 und ist keine Mathematik, sondern
Konsistenz: Der letzte Punkt der rollierenden Volatilitaet MUSS dieselbe
Zahl sein, die calc_vola ueber dieselben Tage liefert — also die Zahl, die
in der Kennzahlen-Kachel darueber steht. Zwei verschiedene Volatilitaeten
auf einem Bildschirm waeren schlimmer als jede Lehrbuch-Ungenauigkeit.
Bricht dieser Schritt, widerspricht sich die Oberflaeche selbst.

Die zweite Zusage: Eine Periode, die weiter zurueckreicht als die Historie,
bleibt LEER. Ein "10 Jahre"-Feld, das in Wahrheit zwei Jahre zeigt, ist
derselbe Fehler wie ein Rumpfjahr als Jahresbalken (#51).

  1. rollierende_vola trifft calc_vola (Konsistenz zur Kennzahlen-Kachel)
  2. Degenerierte Eingaben: kein Absturz, Fehlwerte statt Rechenrauschen
  3. risiko_perioden: nicht abgedeckte Perioden bleiben leer
  4. Tracking Error und Information Ratio, inkl. des 1e-12-Guards (#47)
  5. Die Oberflaeche rendert den Risiko-Block ohne Fehler (AppTest)

Schritte 1-4 brauchen nur numpy und pandas. Schritt 3 nutzt zusaetzlich die
echten CSVs (streamlit) und ueberspringt diesen Teil sonst; Schritt 5
braucht die AppTest-Umgebung.

    python tests/test_risiko.py
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
    RISIKO_PERIODEN, ROLL_FENSTER_TAGE, calc_daily_returns_after_fee,
    calc_vola, historie_beschneiden, information_ratio, risiko_perioden,
    rollierende_vola, tracking_error,
)

TOLERANZ = 1e-12


def _nah(bezeichnung, ist, soll, toleranz=TOLERANZ):
    if ist is None or (isinstance(ist, float) and np.isnan(ist)):
        print(f"    FEHLER — {bezeichnung}: Fehlwert statt {soll}")
        return 1
    if abs(float(ist) - float(soll)) <= toleranz:
        print(f"    OK — {bezeichnung} = {float(ist):.10g}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {float(ist):.10g} statt {float(soll):.10g}")
    return 1


def _ist(bezeichnung, ist, soll):
    if ist == soll:
        print(f"    OK — {bezeichnung}: {ist!r}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {ist!r} statt {soll!r}")
    return 1


def _zufallsreihe(n, streuung=0.004, keim=20260814):
    """Reproduzierbare Tagesrenditen — fester Keim, damit der Test nicht wackelt."""
    return np.random.default_rng(keim).normal(0.0003, streuung, n)


# ─────────────────────────────────────────────────────────────────────────────

def schritt1_konsistenz():
    print("Schritt 1 — rollierende_vola trifft calc_vola (die Kennzahlen-Kachel)")
    f = 0
    f += _ist("Fenster steht auf 365 Tagen", ROLL_FENSTER_TAGE, 365)

    r = _zufallsreihe(1000)
    rv = rollierende_vola(r, 365)

    f += _ist("Laenge = Laenge der Eingabe", len(rv), len(r))
    f += _ist("erste 364 Werte sind NaN", int(np.isnan(rv[:364]).sum()), 364)
    f += _ist("ab Position 364 kein NaN mehr", int(np.isnan(rv[364:]).sum()), 0)

    # Der Kern: letzter Punkt == calc_vola der letzten 365 Tage
    f += _nah("letzter Punkt = calc_vola(letzte 365)",
              rv[-1], calc_vola(r[-365:]), 1e-14)
    # Und an einer beliebigen anderen Stelle
    f += _nah("Punkt 500 = calc_vola(r[136:501])",
              rv[500], calc_vola(r[136:501]), 1e-14)

    # Fenster ueber die ganze Reihe trifft die Gesamt-Vola
    rv_voll = rollierende_vola(r, len(r))
    f += _nah("Fenster = ganze Reihe trifft calc_vola(alles)",
              rv_voll[-1], calc_vola(r), 1e-14)

    # Konstante Renditen: keine Streuung, also Vola 0 — und zwar exakt,
    # nicht das Rechenrauschen, an dem der Sharpe-Guard gescheitert ist.
    konst = rollierende_vola(np.full(500, 0.0001), 365)
    f += _nah("konstante Renditen -> Vola 0", konst[-1], 0.0, 1e-9)
    return f


def schritt2_degeneriert():
    print("Schritt 2 — degenerierte Eingaben")
    f = 0

    f += _ist("leere Eingabe -> leeres Array", rollierende_vola([]).shape, (0,))
    f += _ist("ein Wert -> ein NaN",
              bool(np.isnan(rollierende_vola([0.01], 365)).all()), True)

    # Reihe kuerzer als das Fenster: alles NaN. Das ist der ehrliche Zustand
    # einer Strategie, die noch kein Jahr laeuft — kein Fehler.
    kurz = rollierende_vola(_zufallsreihe(100), 365)
    f += _ist("Reihe kuerzer als das Fenster -> alles NaN",
              bool(np.isnan(kurz).all()), True)
    f += _ist("Laenge bleibt erhalten", len(kurz), 100)

    # Genau ein Wert zuwenig, genau passend
    f += _ist("364 Werte, Fenster 365 -> alles NaN",
              bool(np.isnan(rollierende_vola(_zufallsreihe(364), 365)).all()), True)
    genau = rollierende_vola(_zufallsreihe(365), 365)
    f += _ist("365 Werte, Fenster 365 -> genau ein Wert",
              int((~np.isnan(genau)).sum()), 1)

    # NaN mitten in der Reihe darf nicht zum Absturz fuehren
    mit_nan = _zufallsreihe(500)
    mit_nan[100] = np.nan
    try:
        rv = rollierende_vola(mit_nan, 365)
        f += _ist("NaN in der Reihe: kein Absturz, Laenge stimmt", len(rv), 500)
    except Exception as ex:
        print(f"    FEHLER — NaN in der Reihe stuerzt ab: {ex}")
        f += 1

    # Lauter Nullen
    f += _nah("lauter Nullen -> Vola 0",
              rollierende_vola(np.zeros(500), 365)[-1], 0.0, 1e-15)
    return f


def schritt3_perioden():
    print("Schritt 3 — risiko_perioden: nicht abgedeckte Perioden bleiben leer")
    f = 0

    leer = pd.DataFrame({"ret_port": []}, index=pd.DatetimeIndex([]))
    tab = risiko_perioden(leer)
    f += _ist("leerer DataFrame: Zeilen stehen trotzdem",
              list(tab.index), list(RISIKO_PERIODEN))
    f += _ist("leerer DataFrame: alles leer", bool(tab.isna().all().all()), True)
    f += _ist("None: alles leer",
              bool(risiko_perioden(None).isna().all().all()), True)

    # Eine synthetische Reihe ueber genau zwei Jahre
    idx = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    df = pd.DataFrame({"ret_port": _zufallsreihe(len(idx)),
                       "rf": np.full(len(idx), 0.03)}, index=idx)
    tab = risiko_perioden(df, 0.01)

    for bez in ("YTD", "1 Jahr", "Seit Auflage"):
        f += _ist(f"{bez} ist gefuellt", bool(pd.notna(tab.loc[bez, "vola"])), True)
    for bez in ("3 Jahre", "5 Jahre", "10 Jahre"):
        f += _ist(f"{bez} bleibt leer (Historie reicht nicht)",
                  bool(tab.loc[bez].isna().all()), True)

    # "Seit Auflage" muss die Gesamt-Vola treffen
    netto = calc_daily_returns_after_fee(df["ret_port"].to_numpy(float), 0.01)
    f += _nah("Seit Auflage trifft calc_vola(alles)",
              tab.loc["Seit Auflage", "vola"], calc_vola(netto), 1e-12)

    # Max Drawdown ist negativ oder null, nie positiv
    for bez in RISIKO_PERIODEN:
        wert = tab.loc[bez, "max_dd"]
        if pd.notna(wert) and float(wert) > 0:
            print(f"    FEHLER — {bez}: Max Drawdown ist positiv ({wert})")
            f += 1
    print("    OK — kein Max Drawdown ist positiv")

    # Laengere Perioden koennen nur tiefer sein, nie flacher
    tief = {b: tab.loc[b, "max_dd"] for b in RISIKO_PERIODEN
            if pd.notna(tab.loc[b, "max_dd"])}
    if float(tief["Seit Auflage"]) > float(tief["1 Jahr"]) + 1e-12:
        print("    FEHLER — Max Drawdown seit Auflage ist flacher als ueber 1 Jahr")
        f += 1
    else:
        print("    OK — laengere Periode hat den tieferen Drawdown")

    # Ohne rf-Spalte darf keine Sharpe Ratio entstehen
    ohne_rf = df.drop(columns=["rf"])
    f += _ist("ohne rf-Spalte: keine Sharpe Ratio",
              bool(risiko_perioden(ohne_rf, 0.01)["sharpe"].isna().all()), True)
    nur_nan = df.copy()
    nur_nan["rf"] = np.nan
    f += _ist("rf nur NaN: keine Sharpe Ratio",
              bool(risiko_perioden(nur_nan, 0.01)["sharpe"].isna().all()), True)

    # Eine Reihe mit nur einem Tag
    eintag = pd.DataFrame({"ret_port": [0.01]}, index=pd.DatetimeIndex(["2026-05-05"]))
    f += _ist("ein einziger Tag: alles leer",
              bool(risiko_perioden(eintag).isna().all().all()), True)

    # An echten Daten
    try:
        from modules.shared import (
            DATA_FOLDER, EXCLUDE_SUBSTRINGS, detect_newest_date_tag,
            load_all_csvs, load_mapping, build_portfolio_timeseries,
        )
    except ImportError as ex:
        print(f"    HINWEIS — echte Daten uebersprungen: {ex}")
        return f

    tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
    if tag is None:
        print("    HINWEIS — keine CSVs gefunden, echte Daten uebersprungen")
        return f
    ts = build_portfolio_timeseries(
        load_all_csvs(DATA_FOLDER, tag, EXCLUDE_SUBSTRINGS), load_mapping())

    for name in sorted(ts):
        df = historie_beschneiden(ts[name], name)
        fee = float(df["fee_default"].iloc[0]) if len(df) else 0.0
        tab = risiko_perioden(df, fee)
        beginn = df.index.min() - pd.Timedelta(days=1)
        for bez in RISIKO_PERIODEN:
            gefuellt = bool(pd.notna(tab.loc[bez, "vola"]))
            if bez == "Seit Auflage":
                soll = True
            elif bez == "YTD":
                soll = pd.Timestamp(df.index.max().year - 1, 12, 31) >= beginn
            else:
                soll = (df.index.max()
                        - pd.DateOffset(years=int(bez.split()[0]))) >= beginn
            if gefuellt != soll:
                print(f"    FEHLER — {name} / {bez}: gefuellt={gefuellt}, "
                      f"abgedeckt={soll} (Historie ab {df.index.min():%d.%m.%Y})")
                f += 1

        # Die Gesamt-Vola muss die Kennzahlen-Kachel treffen
        netto = calc_daily_returns_after_fee(
            df["ret_port"].fillna(0.0).to_numpy(float), fee)
        if abs(float(tab.loc["Seit Auflage", "vola"]) - calc_vola(netto)) > 1e-12:
            print(f"    FEHLER — {name}: Seit Auflage weicht von calc_vola ab")
            f += 1

    print(f"    OK — {len(ts)} echte Strategien: Perioden korrekt abgedeckt, "
          f"Gesamt-Vola trifft calc_vola")
    return f


def schritt4_tracking_error():
    print("Schritt 4 — Tracking Error und Information Ratio")
    f = 0

    # Identische Reihen: keine Aktivrendite, also TE exakt 0 — und die
    # Information Ratio MUSS ein Fehlwert sein statt einer Zahl der
    # Groessenordnung 1e16. Genau dieser Guard fehlte bis 12.08.2026 in
    # calc_sharpe_excess und schrieb dort -67,48 in eine Kundenbroschuere.
    r = _zufallsreihe(800)
    f += _nah("identische Reihen -> TE = 0", tracking_error(r, r), 0.0, 1e-15)
    f += _ist("identische Reihen -> IR ist Fehlwert", information_ratio(r, r), None)

    # Praktisch identisch (Rechenrauschen): der 1e-12-Guard muss greifen
    fast = r + 1e-18
    ir_fast = information_ratio(fast, r)
    if ir_fast is not None and abs(ir_fast) > 100:
        print(f"    FEHLER — Rechenrauschen ergibt IR = {ir_fast:.3e}")
        f += 1
    else:
        print(f"    OK — Rechenrauschen ergibt IR = {ir_fast!r}, keine Riesenzahl")

    # Konstanter Abstand: Aktivrendite konstant, also TE = 0 und IR Fehlwert
    rb = np.zeros(500)
    rp_konst = np.full(500, 0.0002)
    f += _nah("konstante Aktivrendite -> TE = 0",
              tracking_error(rp_konst, rb), 0.0, 1e-12)
    f += _ist("konstante Aktivrendite -> IR ist Fehlwert",
              information_ratio(rp_konst, rb), None)

    # Von Hand nachgerechnet: Benchmark still, Strategie schwankt.
    # Aktivrendite = (1+rp)/1 - 1 = rp, also TE = calc_vola(rp).
    rp = _zufallsreihe(600)
    f += _nah("Benchmark bei null -> TE = calc_vola(Strategie)",
              tracking_error(rp, np.zeros(600)), calc_vola(rp), 1e-12)

    # Positive Ueberrendite -> positive IR, negative -> negative
    hoch = rb + 0.0005 + _zufallsreihe(500, 0.001, keim=1)
    f_ir = information_ratio(hoch, rb)
    f += _ist("dauerhafte Ueberrendite -> IR positiv", bool(f_ir > 0), True)
    tief = rb - 0.0005 + _zufallsreihe(500, 0.001, keim=2)
    f += _ist("dauerhafte Unterrendite -> IR negativ",
              bool(information_ratio(tief, rb) < 0), True)

    # Degeneriert
    f += _ist("leere Reihen -> TE Fehlwert", tracking_error([], []), None)
    f += _ist("ein Wert -> TE Fehlwert", tracking_error([0.01], [0.01]), None)
    f += _ist("leere Reihen -> IR Fehlwert", information_ratio([], []), None)

    # Ungleich lange Reihen werden auf die kuerzere gestutzt statt zu stuerzen
    kurz_te = tracking_error(_zufallsreihe(500), _zufallsreihe(300, keim=7))
    f += _ist("ungleiche Laengen: TE kommt heraus", bool(kurz_te is not None), True)

    # NaN in der Benchmark darf nicht durchschlagen
    rb_nan = np.zeros(500)
    rb_nan[10] = np.nan
    f += _ist("NaN in der Benchmark: TE kommt heraus",
              bool(tracking_error(_zufallsreihe(500), rb_nan) is not None), True)

    # Eine Benchmark-Rendite von exakt -100 % wuerde durch null teilen
    rb_null = np.zeros(500)
    rb_null[42] = -1.0
    te_null = tracking_error(_zufallsreihe(500), rb_null)
    f += _ist("Benchmark -100 % an einem Tag: kein Unendlich",
              bool(te_null is not None and np.isfinite(te_null)), True)
    return f


def schritt5_apptest():
    print("Schritt 5 — die Oberflaeche rendert den Risiko-Block ohne Fehler")
    import importlib.util
    if importlib.util.find_spec("streamlit.testing.v1") is None:
        print("    UEBERSPRUNGEN — streamlit.testing nicht verfuegbar")
        return 0
    from streamlit.testing.v1 import AppTest

    def _app(**zustand):
        at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                               default_timeout=400)
        at.secrets["passwords"] = {"t": "t"}
        at.session_state["logged_in"] = True
        at.session_state["username"] = "t"
        for k, v in zustand.items():
            at.session_state[k] = v
        return at.run()

    f = 0

    def _lauf(bez, **zustand):
        nonlocal f
        at = _app(**zustand)
        if at.exception:
            for e in at.exception:
                print(f"    FEHLER — {bez}: {str(e.value)[:200]}")
            f += 1
            return None
        print(f"    OK — {bez} rendert ohne Fehler")
        return at

    at = _lauf("Risiko-Block aus", p_risk=False)
    if at is not None:
        if any("Risiko" in s.value for s in at.subheader):
            print("    FEHLER — Risiko-Block erscheint, obwohl der Haken aus ist")
            f += 1
        else:
            print("    OK — ohne Haken kein Risiko-Block")

    at = _lauf("Risiko-Block an", p_risk=True)
    if at is not None:
        if not any("Risiko" in s.value for s in at.subheader):
            print(f"    FEHLER — Ueberschrift fehlt "
                  f"(gefunden: {[s.value for s in at.subheader]})")
            f += 1
        else:
            print("    OK — Ueberschrift steht")

    # Drawdown-Block mit der neuen Tabelle
    _lauf("Drawdown-Block mit Perioden-Tabelle", p_dd=True)
    # Beide zusammen und mit Vergleichsportfolio
    _lauf("Risiko + Drawdown + Vergleich", p_risk=True, p_dd=True, p_cmp=True)
    # Eine junge Strategie: kein volles Jahr rollierende Vola moeglich
    _lauf("junge Strategie ohne volles Vola-Fenster",
          p_sel1="Muster FFPB Pro Dividende", p_risk=True)
    # Ohne Benchmark duerfen TE/IR nicht in eine Ausnahme laufen
    _lauf("Strategie ohne Benchmark",
          p_sel1="Muster SCHWEIZ Aktien", p_risk=True)
    return f


def main():
    print("Pruefstein: Risiko-Kennzahlen\n")
    fehler = 0
    for schritt in (schritt1_konsistenz, schritt2_degeneriert,
                    schritt3_perioden, schritt4_tracking_error,
                    schritt5_apptest):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — rollierende Vola trifft die Kennzahlen-Kachel, nicht "
          "abgedeckte Perioden bleiben leer, IR faellt bei TE=0 nicht um")
    return 0


if __name__ == "__main__":
    sys.exit(main())
