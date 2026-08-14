"""Pruefstein fuer die Monatsrenditen-Heatmap (NEU 14.08.2026).

Eine Zelle der Heatmap behauptet eine MONATSrendite. Damit gilt hier
dieselbe Regel, die am 12.08.2026 den Saeulen-Chart in Ordnung gebracht hat
(Transferwissen #51): "Es gibt Daten" ist nicht "der Zeitraum ist
abgedeckt". Ohne die Vollstaendigkeitspruefung stuende der Auflagemonat als
vollwertiger Monat in der Matrix — bei "Muster FFPB Pro Dividende" waeren
das zehn Tage fuer 10/2024, bei der comdirect-Familie zwanzig fuer 03/2024.
Und der LAUFENDE Monat ist immer angebrochen: Am Datenstand 21.07.2026
stand bei "Muster FFPB Pro" ein 21-Tage-Wert von -7,54 %.

Zweite Zusage dieses Pruefsteins: Die zwoelf Monate einer Zeile verketten
sich EXAKT zur Jahresspalte. Bei der Differenz gilt das nur, weil sie
geometrisch gerechnet wird — arithmetisch waere die Zeile mit ihrer eigenen
Summe im Widerspruch.

  1. _ist_voller_monat gegen von Hand gerechnete Grenzfaelle
  2. monatsrenditen — Zeile verkettet sich zur Jahresspalte
  3. Geometrische Differenz — das nachgerechnete Zwei-Monats-Beispiel
  4. Degenerierte Eingaben liefern Fehlwerte statt Nullen oder Abstuerze
  5. Die Durchschnittszeile verkettet sich zum Durchschnittsjahr
  6. Die 19 echten Strategien — jeder angebrochene Monat nachgemessen,
     dazu der Zeitraum-Zuschnitt an beiden Raendern
  7. Die Oberflaeche rendert die Heatmap ohne Fehler (AppTest)

Schritte 1-4 brauchen nur numpy und pandas. Schritt 5 nutzt die echten CSVs
nur fuer die Gegenprobe, Schritt 6 braucht sie ganz (streamlit fuer die
Loader), Schritt 7 die AppTest-Umgebung; alle ueberspringen sich sauber.

    python tests/test_monatsrenditen.py
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
    MONAT_RAND_TOLERANZ_TAGE, _ist_voller_monat, heatmap_kennzahlen,
    historie_beschneiden, monats_durchschnitt, monatsrenditen,
    monatsrenditen_differenz,
)

TOLERANZ = 1e-12

# Die angebrochenen Monate der echten Daten, gemessen am 14.08.2026 gegen den
# Datenstand 260721. Namentlich festgenagelt, damit eine neue Datenlieferung
# nicht unbemerkt einen Monat mehr oder weniger als vollstaendig fuehrt.
# Der laufende Monat (07/2026) ist bei JEDER Strategie angebrochen und steht
# deshalb nicht einzeln in dieser Tabelle, sondern wird separat geprueft.
AUFLAGEMONATE = {
    "Comdirect 30":              (2024, 3),
    "Comdirect 70":              (2024, 3),
    "Comdirect 100":             (2024, 3),
    "Muster Dynamic cVV":        (2018, 10),
    "Muster FFPB Pro Dividende": (2024, 10),
    "Muster SCHWEIZ Aktien":     (2022, 9),
    "Muster SCHWEIZ Substanz":   (2022, 9),
}

# Strategien, deren ERSTER Monat vollstaendig ist — die Kontrollfaelle.
# "Muster FFPB Pro" ist der interessanteste: Die Strategie hat ein
# Rumpf-JAHR 2023 (122 Tage, siehe test_kalenderjahre.py), aber keinen
# Rumpf-MONAT, weil die Auflage am 01.09.2023 auf einen Monatsanfang faellt.
OHNE_AUFLAGEMONAT = ("Muster FFPB Pro", "ESG Muster ausgewogen",
                     "ETF Muster 40/60 ausgew.", "Muster ausgewogen cVV")


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


def _reihe(von, bis, wert=0.0):
    """Kalendertaegliche Zeitreihe wie die echten CSVs (lueckenlos)."""
    idx = pd.date_range(von, bis, freq="D")
    return pd.DataFrame({"ret_port": np.full(len(idx), wert, dtype=float),
                         "ret_bm": np.full(len(idx), wert, dtype=float)},
                        index=idx)


# ─────────────────────────────────────────────────────────────────────────────

def schritt1_voller_monat():
    print("Schritt 1 — _ist_voller_monat gegen von Hand gerechnete Grenzfaelle")
    f = 0
    f += _ist("Toleranz steht auf 3 Tagen", MONAT_RAND_TOLERANZ_TAGE, 3)

    faelle = [
        # (von, bis, jahr, monat, erwartet, warum)
        ("2024-03-01", "2024-03-31", 2024, 3, True,  "voller Maerz"),
        ("2024-03-04", "2024-03-28", 2024, 3, True,  "beide Toleranzraender gerade noch"),
        ("2024-03-05", "2024-03-31", 2024, 3, False, "Anfang einen Tag zu spaet"),
        ("2024-03-01", "2024-03-27", 2024, 3, False, "Ende einen Tag zu frueh"),
        ("2024-03-12", "2024-03-31", 2024, 3, False, "Auflagemonat comdirect (20 Tage)"),
        ("2024-03-31", "2024-03-31", 2024, 3, False, "ein einziger Tag"),
        ("2024-02-01", "2024-02-29", 2024, 2, True,  "Februar im Schaltjahr"),
        ("2023-02-01", "2023-02-28", 2023, 2, True,  "Februar ohne Schalttag"),
        ("2024-02-01", "2024-02-28", 2024, 2, True,  "Schaltjahr, 29. fehlt (Toleranz)"),
        ("2024-04-01", "2024-04-30", 2024, 4, True,  "30-Tage-Monat"),
        ("2008-12-31", "2008-12-31", 2008, 12, False, "die cVV-Indexbasis"),
    ]
    for von, bis, jahr, monat, soll, warum in faelle:
        sub = _reihe(von, bis)
        f += _ist(f"{warum} ({von}..{bis})",
                  _ist_voller_monat(sub, jahr, monat), soll)

    # Ein Loch mitten im Monat: die Raender stimmen, die Mitte fehlt. Die
    # Pruefung sieht nur die Raender — das ist bewusst so (wie beim Jahr) und
    # wird hier festgehalten, damit niemand es fuer einen Fehler haelt.
    loch = pd.concat([_reihe("2024-05-01", "2024-05-05"),
                      _reihe("2024-05-25", "2024-05-31")])
    f += _ist("Loch in der Monatsmitte gilt als voll (Raender-Regel)",
              _ist_voller_monat(loch, 2024, 5), True)

    f += _ist("leerer Ausschnitt", _ist_voller_monat(pd.DataFrame(), 2024, 3), False)
    return f


def schritt2_verkettung():
    print("Schritt 2 — monatsrenditen: die Zeile verkettet sich zur Jahresspalte")
    f = 0

    # Ein Jahr, in jedem Monat genau ein Renditetag von +1 %.
    idx = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    rp = np.zeros(len(idx))
    for monat in range(1, 13):
        rp[idx.get_loc(pd.Timestamp(2024, monat, 15))] = 0.01
    df = pd.DataFrame({"ret_port": rp}, index=idx)

    m = monatsrenditen(df, 0.0)
    f += _ist("12 Monatswerte vorhanden", int(m["renditen"].loc[2024].notna().sum()), 12)
    f += _ist("alle 12 vollstaendig", int(m["vollstaendig"].loc[2024].sum()), 12)
    f += _nah("Januar", m["renditen"].loc[2024, 1], 0.01)
    # 1,01^12 - 1 = 0,126825030...
    f += _nah("Jahresspalte = 1,01^12 - 1", m["jahr"].loc[2024], 1.01 ** 12 - 1)
    verkettet = float(np.prod(1.0 + m["renditen"].loc[2024].dropna().to_numpy()) - 1.0)
    f += _nah("Verkettung der Monate trifft die Jahresspalte",
              verkettet, float(m["jahr"].loc[2024]), 1e-14)

    # Mit Honorar: der Abzug wirkt taggenau, die Verkettung muss trotzdem
    # aufgehen. Das ist der Fall, der bei einer nachtraeglichen
    # Jahres-Korrektur auseinanderliefe.
    mf = monatsrenditen(df, 0.01)
    verkettet_f = float(np.prod(1.0 + mf["renditen"].loc[2024].dropna().to_numpy()) - 1.0)
    f += _nah("mit 1 % Honorar: Verkettung trifft Jahresspalte",
              verkettet_f, float(mf["jahr"].loc[2024]), 1e-14)
    if float(mf["jahr"].loc[2024]) >= float(m["jahr"].loc[2024]):
        print("    FEHLER — Honorar senkt die Jahresrendite nicht")
        f += 1
    else:
        print("    OK — Honorar senkt die Jahresrendite")

    # Angebrochenes Jahr: nur zwei Monate, Verkettung muss weiter aufgehen.
    teil = df.loc["2024-01-01":"2024-02-29"]
    mt = monatsrenditen(teil, 0.0)
    f += _ist("Rumpfjahr: 2 Monate", int(mt["renditen"].loc[2024].notna().sum()), 2)
    f += _ist("Rumpfjahr ist nicht vollstaendig",
              bool(mt["jahr_vollstaendig"].loc[2024]), False)
    f += _nah("Rumpfjahr: Verkettung trifft Jahresspalte",
              float(np.prod(1.0 + mt["renditen"].loc[2024].dropna().to_numpy()) - 1.0),
              float(mt["jahr"].loc[2024]), 1e-14)
    return f


def schritt3_differenz():
    print("Schritt 3 — geometrische Differenz, das nachgerechnete Beispiel")
    f = 0

    # Zwei volle Monate. Strategie je +10 %, Benchmark je +5 %.
    #   geometrisch  1,10/1,05 - 1 = +4,761904...% je Monat
    #                1,0476...^2 - 1 = +9,750566...%  = 1,21/1,1025 - 1
    #   arithmetisch 10 - 5 = 5 PP je Monat, Summe 10 PP — passt NICHT
    idx = pd.date_range("2024-01-01", "2024-02-29", freq="D")
    rp = np.zeros(len(idx))
    rb = np.zeros(len(idx))
    for monat in (1, 2):
        pos = idx.get_loc(pd.Timestamp(2024, monat, 15))
        rp[pos] = 0.10
        rb[pos] = 0.05
    df = pd.DataFrame({"ret_port": rp, "ret_bm": rb}, index=idx)

    a = monatsrenditen(df, 0.0)
    b = monatsrenditen(df, 0.0, spalte="ret_bm", nach_kosten=False)
    d = monatsrenditen_differenz(a, b)

    soll_monat = 1.10 / 1.05 - 1.0
    soll_jahr = 1.21 / 1.1025 - 1.0
    f += _nah("Januar-Differenz", d["renditen"].loc[2024, 1], soll_monat)
    f += _nah("Februar-Differenz", d["renditen"].loc[2024, 2], soll_monat)
    f += _nah("Jahresdifferenz", d["jahr"].loc[2024], soll_jahr)
    f += _nah("Verkettung der Monatsdifferenzen trifft die Jahresdifferenz",
              (1.0 + soll_monat) ** 2 - 1.0, float(d["jahr"].loc[2024]), 1e-14)

    # Der Gegenbeweis: arithmetisch waere es 0,10 und damit falsch.
    if abs(float(d["jahr"].loc[2024]) - 0.10) < 1e-6:
        print("    FEHLER — Jahresdifferenz ist arithmetisch gerechnet")
        f += 1
    else:
        print(f"    OK — arithmetisch waere +10,0000 %, geometrisch sind es "
              f"{float(d['jahr'].loc[2024])*100:.4f} %")

    # Ungleich lange Reihen: Die Differenz darf nur dort stehen, wo BEIDE
    # Monate voll sind. Reihe B beginnt mitten im Februar.
    kurz = df.loc["2024-02-12":]
    bk = monatsrenditen(kurz, 0.0, spalte="ret_bm", nach_kosten=False)
    dk = monatsrenditen_differenz(a, bk)
    f += _ist("Januar entfaellt (B hat ihn nicht)",
              bool(pd.notna(dk["renditen"].loc[2024, 1])), False)
    f += _ist("Februar entfaellt (B nur angebrochen)",
              bool(pd.notna(dk["renditen"].loc[2024, 2])), False)
    f += _ist("kein gueltiger Monat -> Jahr leer",
              bool(pd.isna(dk["jahr"].loc[2024])), True)

    # Ein angebrochener Monat auf der A-Seite muss ebenso entfallen.
    a_kurz = monatsrenditen(df.loc["2024-01-12":], 0.0)
    da = monatsrenditen_differenz(a_kurz, b)
    f += _ist("angebrochener Monat auf der A-Seite entfaellt",
              bool(pd.notna(da["renditen"].loc[2024, 1])), False)
    f += _ist("voller Februar bleibt",
              bool(pd.notna(da["renditen"].loc[2024, 2])), True)
    f += _nah("Jahr = nur der Februar", da["jahr"].loc[2024], soll_monat)
    return f


def schritt4_degeneriert():
    print("Schritt 4 — degenerierte Eingaben")
    f = 0

    for bez, eingabe in (("None", None),
                         ("leerer DataFrame",
                          pd.DataFrame({"ret_port": []}, index=pd.DatetimeIndex([])))):
        m = monatsrenditen(eingabe)
        f += _ist(f"{bez}: renditen leer", bool(m["renditen"].empty), True)
        f += _ist(f"{bez}: jahr leer", bool(m["jahr"].empty), True)
        k = heatmap_kennzahlen(m)
        f += _ist(f"{bez}: kennzahlen anzahl", k["anzahl"], 0)
        f += _ist(f"{bez}: kennzahlen bester", k["bester"], None)

    # Fehlende Spalte
    ohne = pd.DataFrame({"irgendwas": [1.0]}, index=pd.DatetimeIndex(["2026-01-05"]))
    f += _ist("Spalte fehlt: renditen leer",
              bool(monatsrenditen(ohne)["renditen"].empty), True)

    # Ein einziger Tag
    eintag = pd.DataFrame({"ret_port": [0.01], "ret_bm": [np.nan]},
                          index=pd.DatetimeIndex(["2026-03-05"]))
    m1 = monatsrenditen(eintag)
    f += _nah("ein Tag: Wert steht da", m1["renditen"].loc[2026, 3], 0.01)
    f += _ist("ein Tag: NICHT vollstaendig",
              bool(m1["vollstaendig"].loc[2026, 3]), False)
    f += _ist("ein Tag: keine vollen Monate in den Kennzahlen",
              heatmap_kennzahlen(m1)["anzahl"], 0)

    # Eine Spalte aus lauter NaN (Benchmark ohne Benchmark) darf NICHT zu 0,0
    # werden — sonst saehe ein Fehlwert wie ein Nullmonat aus (#46).
    mb = monatsrenditen(eintag, spalte="ret_bm", nach_kosten=False)
    f += _ist("nur NaN: Fehlwert, nicht 0,0",
              bool(pd.isna(mb["renditen"].loc[2026, 3])), True)

    # Konstante Renditen ungleich null — der Fall, an dem der Sharpe-Guard
    # gescheitert ist (#47). Hier muss schlicht ein Wert herauskommen.
    konst = _reihe("2024-01-01", "2024-12-31", wert=0.0001)
    mk = monatsrenditen(konst, 0.0)
    f += _ist("konstante Renditen: 12 volle Monate",
              int(mk["vollstaendig"].loc[2024].sum()), 12)

    # Lauter Nullen: 0,0 ist hier ein echter Messwert, kein Fehlwert.
    null = _reihe("2024-01-01", "2024-12-31", wert=0.0)
    mn = monatsrenditen(null, 0.0)
    f += _nah("lauter Nullen: Januar ist 0,0", mn["renditen"].loc[2024, 1], 0.0)
    kn = heatmap_kennzahlen(mn)
    f += _ist("lauter Nullen: 12 Monate gezaehlt", kn["anzahl"], 12)
    f += _ist("lauter Nullen: kein Monat positiv", kn["positiv"], 0)

    # Differenz mit leeren Matrizen
    leer_m = monatsrenditen(None)
    f += _ist("Differenz zweier leerer Matrizen",
              bool(monatsrenditen_differenz(leer_m, leer_m)["renditen"].empty), True)
    voll_m = monatsrenditen(_reihe("2024-01-01", "2024-12-31", 0.001), 0.0)
    f += _ist("Differenz voll gegen leer",
              bool(monatsrenditen_differenz(voll_m, leer_m)["renditen"].empty), True)

    # Ohne zeitliche Ueberschneidung
    frueh = monatsrenditen(_reihe("2020-01-01", "2020-12-31", 0.001), 0.0)
    spaet = monatsrenditen(_reihe("2024-01-01", "2024-12-31", 0.001), 0.0)
    f += _ist("keine gemeinsamen Jahre",
              bool(monatsrenditen_differenz(frueh, spaet)["renditen"].empty), True)
    return f


def schritt5_durchschnitt():
    print("Schritt 5 — die Durchschnittszeile verkettet sich zum Durchschnittsjahr")
    f = 0

    # Zwei volle Jahre. 2024 jeden Monat +1 %, 2025 jeden Monat -1 %.
    # Das geometrische Mittel je Monat ist damit sqrt(1,01 * 0,99) - 1
    # = -0,00005001..., fuer jeden der zwoelf Monate gleich.
    idx = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    rp = np.zeros(len(idx))
    for jahr, wert in ((2024, 0.01), (2025, -0.01)):
        for monat in range(1, 13):
            rp[idx.get_loc(pd.Timestamp(jahr, monat, 15))] = wert
    df = pd.DataFrame({"ret_port": rp}, index=idx)

    m = monatsrenditen(df, 0.0)
    s = monats_durchschnitt(m)
    f += _ist("beide Jahre einbezogen", s["jahre"], [2024, 2025])
    f += _nah("Januar-Mittel = sqrt(1,01 x 0,99) - 1",
              s["monate"].loc[1], (1.01 * 0.99) ** 0.5 - 1.0)
    f += _ist("alle 12 Monate gefuellt", int(s["monate"].notna().sum()), 12)

    # DIE Zusage: Die Zeile verkettet sich exakt zum Durchschnittsjahr.
    verkettet = float(np.prod(1.0 + s["monate"].to_numpy(dtype=float)) - 1.0)
    f += _nah("Verkettung der Ø-Monate trifft das Ø-Jahr",
              verkettet, s["jahr"], 1e-14)
    # Und das Ø-Jahr ist das geometrische Mittel der beiden Jahreswerte.
    f += _nah("Ø-Jahr = geometrisches Mittel der Jahre",
              s["jahr"],
              ((1 + m["jahr"].loc[2024]) * (1 + m["jahr"].loc[2025])) ** 0.5 - 1.0,
              1e-14)

    # Angebrochene Jahre duerfen NICHT eingehen — sonst haette der Januar
    # mehr Beobachtungen als der Dezember und die Verkettung braeche.
    mit_rumpf = pd.DataFrame(
        {"ret_port": np.concatenate([rp, np.zeros(60)])},
        index=idx.append(pd.date_range("2026-01-01", "2026-03-01", freq="D")))
    s2 = monats_durchschnitt(monatsrenditen(mit_rumpf, 0.0))
    f += _ist("Rumpfjahr 2026 bleibt aussen vor", s2["jahre"], [2024, 2025])
    f += _nah("Ø-Monate unveraendert", s2["monate"].loc[1],
              s["monate"].loc[1], 1e-15)

    # Kein volles Jahr -> keine Zeile
    kurz = monatsrenditen(df.loc["2024-03-01":"2024-08-31"], 0.0)
    s3 = monats_durchschnitt(kurz)
    f += _ist("ohne volles Kalenderjahr: keine Ø-Zeile",
              bool(s3["monate"].empty), True)
    f += _ist("ohne volles Kalenderjahr: kein Ø-Jahr", s3["jahr"], None)

    # Degeneriert
    f += _ist("leere Matrix: keine Ø-Zeile",
              bool(monats_durchschnitt(monatsrenditen(None))["monate"].empty),
              True)

    # An echten Daten: ueber ALLE Strategien muss die Verkettung aufgehen.
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
        print("    HINWEIS — keine CSVs gefunden")
        return f
    ts = build_portfolio_timeseries(
        load_all_csvs(DATA_FOLDER, tag, EXCLUDE_SUBSTRINGS), load_mapping())

    geprueft = 0
    for name in sorted(ts):
        d = historie_beschneiden(ts[name], name)
        m = monatsrenditen(d, float(d["fee_default"].iloc[0]) if len(d) else 0.0)
        s = monats_durchschnitt(m)
        if s["monate"].empty:
            continue
        geprueft += 1
        verkettet = float(np.prod(1.0 + s["monate"].to_numpy(dtype=float)) - 1.0)
        if abs(verkettet - float(s["jahr"])) > 1e-10:
            print(f"    FEHLER — {name}: Ø-Verkettung {verkettet:.10f} gegen "
                  f"Ø-Jahr {float(s['jahr']):.10f}")
            f += 1
        # Jedes einbezogene Jahr muss wirklich vollstaendig sein
        for jahr in s["jahre"]:
            if not bool(m["jahr_vollstaendig"].loc[jahr]):
                print(f"    FEHLER — {name}: {jahr} ist nicht vollstaendig, "
                      f"geht aber in den Durchschnitt ein")
                f += 1
    print(f"    OK — {geprueft} echte Strategien: Ø-Zeile verkettet sich zum "
          f"Ø-Jahr, nur volle Jahre einbezogen")
    return f


def schritt6_echte_daten():
    print("Schritt 6 — die 19 echten Strategien: jeder angebrochene Monat nachgemessen")
    try:
        from modules.shared import (
            DATA_FOLDER, EXCLUDE_SUBSTRINGS, detect_newest_date_tag,
            load_all_csvs, load_mapping, build_portfolio_timeseries,
        )
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — {ex}")
        return 0

    tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
    if tag is None:
        print(f"    UEBERSPRUNGEN — keine CSVs in {DATA_FOLDER}")
        return 0
    ts = build_portfolio_timeseries(
        load_all_csvs(DATA_FOLDER, tag, EXCLUDE_SUBSTRINGS), load_mapping())
    print(f"    Datenstand {tag} — {len(ts)} Strategien")

    f = 0
    gefunden = {}
    letzter_monat_offen = []

    for name in sorted(ts):
        df = historie_beschneiden(ts[name], name)
        m = monatsrenditen(df, float(df["fee_default"].iloc[0]) if len(df) else 0.0)
        offen = [(int(j), int(k))
                 for j in m["renditen"].index for k in m["renditen"].columns
                 if pd.notna(m["renditen"].loc[j, k])
                 and not bool(m["vollstaendig"].loc[j, k])]

        # Jeden gemeldeten Monat gegen die Rohdaten nachrechnen: Deckt er
        # wirklich nicht den ganzen Kalendermonat ab?
        for jahr, monat in offen:
            sub = df[(df.index.year == jahr) & (df.index.month == monat)]
            anfang = pd.Timestamp(jahr, monat, 1)
            ende = anfang + pd.offsets.MonthEnd(0)
            wirklich_offen = (sub.index.min() > anfang + pd.Timedelta(days=3)
                              or sub.index.max() < ende - pd.Timedelta(days=3))
            if not wirklich_offen:
                print(f"    FEHLER — {name} {monat:02d}/{jahr} als angebrochen "
                      f"gemeldet, deckt den Monat aber ab "
                      f"({sub.index.min():%d.%m.} bis {sub.index.max():%d.%m.})")
                f += 1

        # Umgekehrt: Kein VOLLER Monat darf in Wahrheit angebrochen sein.
        for jahr in m["renditen"].index:
            for monat in m["renditen"].columns:
                if not bool(m["vollstaendig"].loc[jahr, monat]):
                    continue
                sub = df[(df.index.year == jahr) & (df.index.month == monat)]
                anfang = pd.Timestamp(int(jahr), int(monat), 1)
                ende = anfang + pd.offsets.MonthEnd(0)
                if (sub.index.min() > anfang + pd.Timedelta(days=3)
                        or sub.index.max() < ende - pd.Timedelta(days=3)):
                    print(f"    FEHLER — {name} {int(monat):02d}/{int(jahr)} gilt als "
                          f"voll, deckt den Monat aber nicht ab")
                    f += 1

        # Der letzte Monat der Reihe ist der laufende und immer angebrochen.
        letzter = (int(df.index.max().year), int(df.index.max().month))
        if letzter in offen:
            letzter_monat_offen.append(name)
        else:
            print(f"    FEHLER — {name}: der laufende Monat "
                  f"{letzter[1]:02d}/{letzter[0]} gilt als vollstaendig")
            f += 1

        uebrig = [p for p in offen if p != letzter]
        if uebrig:
            gefunden[name] = uebrig[0] if len(uebrig) == 1 else tuple(uebrig)

    print(f"    OK — bei allen {len(letzter_monat_offen)} Strategien ist der "
          f"laufende Monat als angebrochen gekennzeichnet")

    # Die bekannten Auflagemonate namentlich
    for name, soll in sorted(AUFLAGEMONATE.items()):
        if name not in ts:
            print(f"    HINWEIS — {name} nicht in den Daten, uebersprungen")
            continue
        f += _ist(f"Auflagemonat {name}", gefunden.get(name), soll)

    for name in OHNE_AUFLAGEMONAT:
        if name not in ts:
            print(f"    HINWEIS — {name} nicht in den Daten, uebersprungen")
            continue
        f += _ist(f"{name} hat KEINEN angebrochenen Auflagemonat",
                  gefunden.get(name), None)

    # Kein cVV-Dezember 2008 mehr: historie_beschneiden hat ihn entfernt.
    for name in ("Muster ausgewogen cVV", "Muster offensiv cVV",
                 "Muster konservativ cVV", "Muster defensiv cVV",
                 "Muster Defensiv Plus cVV"):
        if name not in ts:
            continue
        df = historie_beschneiden(ts[name], name)
        m = monatsrenditen(df, 0.0)
        hat_2008 = 2008 in list(m["renditen"].index)
        f += _ist(f"{name}: kein Dezember 2008 in der Matrix", hat_2008, False)

    # Unerwartete Zusatzfunde melden
    unerwartet = {n: v for n, v in gefunden.items() if n not in AUFLAGEMONATE}
    if unerwartet:
        print("    FEHLER — angebrochene Monate ausser dem laufenden, "
              "die nicht in AUFLAGEMONATE stehen:")
        for n, v in sorted(unerwartet.items()):
            print(f"      ! {n}: {v}")
        f += len(unerwartet)

    # Und die Verkettungs-Zusage an echten Daten, ueber ALLE Strategien.
    abweichungen = 0
    for name in sorted(ts):
        df = historie_beschneiden(ts[name], name)
        fee = float(df["fee_default"].iloc[0]) if len(df) else 0.0
        m = monatsrenditen(df, fee)
        for jahr in m["renditen"].index:
            zeile = m["renditen"].loc[jahr].dropna()
            if zeile.empty:
                continue
            verkettet = float(np.prod(1.0 + zeile.to_numpy(dtype=float)) - 1.0)
            direkt = float(m["jahr"].loc[jahr])
            if abs(verkettet - direkt) > 1e-10:
                print(f"    FEHLER — {name} {jahr}: Verkettung {verkettet:.10f} "
                      f"gegen Jahresspalte {direkt:.10f}")
                abweichungen += 1
    f += abweichungen
    if not abweichungen:
        print("    OK — bei allen Strategien und Jahren verkettet sich die "
              "Zeile zur Jahresspalte")

    # ── Zeitraum-Zuschnitt (NEU 14.08.2026) ────────────────────────────────
    # Seit die Heatmap dem gewaehlten Zeitraum folgt, entstehen an BEIDEN
    # Raendern angebrochene Monate — auch mitten in der Historie, wo die
    # Strategie laengst laeuft. Sie muessen genauso gekennzeichnet werden wie
    # der Auflagemonat, sonst behauptet ein Zuschnitt-Artefakt eine
    # Monatsrendite.
    name = "Muster ausgewogen cVV"
    if name in ts:
        voll = historie_beschneiden(ts[name], name)
        # Ausschnitt mitten in der Historie, an beiden Seiten angebrochen
        aus = voll.loc[pd.Timestamp("2015-05-12"):pd.Timestamp("2018-09-20")]
        ma = monatsrenditen(aus, 0.0)
        f += _ist("Zuschnitt: erster Monat 05/2015 angebrochen",
                  bool(ma["vollstaendig"].loc[2015, 5]), False)
        f += _ist("Zuschnitt: letzter Monat 09/2018 angebrochen",
                  bool(ma["vollstaendig"].loc[2018, 9]), False)
        f += _ist("Zuschnitt: Juni 2015 dazwischen ist voll",
                  bool(ma["vollstaendig"].loc[2015, 6]), True)
        f += _ist("Zuschnitt: 2016 und 2017 sind volle Jahre",
                  [bool(ma["jahr_vollstaendig"].loc[j]) for j in (2016, 2017)],
                  [True, True])
        f += _ist("Zuschnitt: 2015 und 2018 sind KEINE vollen Jahre",
                  [bool(ma["jahr_vollstaendig"].loc[j]) for j in (2015, 2018)],
                  [False, False])
        # Der Durchschnitt darf nur die beiden vollen Jahre nehmen
        f += _ist("Zuschnitt: Ø nur ueber 2016 und 2017",
                  monats_durchschnitt(ma)["jahre"], [2016, 2017])
        # Ein Ausschnitt auf exakte Jahresgrenzen hat KEINE Randmonate
        genau = voll.loc[pd.Timestamp("2016-01-01"):pd.Timestamp("2017-12-31")]
        mg = monatsrenditen(genau, 0.0)
        f += _ist("exakte Jahresgrenzen: kein angebrochener Monat",
                  int((~mg["vollstaendig"].to_numpy()).sum()), 0)
    return f


def schritt7_apptest():
    print("Schritt 7 — die Oberflaeche rendert die Heatmap ohne Fehler")
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

    # Ohne Haken darf keine Heatmap-Ueberschrift erscheinen
    at = _lauf("Heatmap aus", p_heat=False)
    if at is not None:
        texte = [s.value for s in at.subheader]
        if any("Monatsrenditen" in t for t in texte):
            print("    FEHLER — Heatmap erscheint, obwohl der Haken aus ist")
            f += 1
        else:
            print("    OK — ohne Haken keine Heatmap")

    at = _lauf("Heatmap absolut", p_heat=True)
    if at is not None:
        texte = [s.value for s in at.subheader]
        if not any("Monatsrenditen" in t for t in texte):
            print(f"    FEHLER — Ueberschrift 'Monatsrenditen' fehlt "
                  f"(gefunden: {texte})")
            f += 1
        else:
            print("    OK — Ueberschrift steht")
        captions = " ".join(c.value for c in at.caption).lower()
        for stueck, bez in (("bester:", "Kennzeile"),
                            ("angebrochener monat", "Sternchen-Fussnote"),
                            ("geometrisches mittel", "Ø-Fussnote")):
            if stueck not in captions:
                print(f"    FEHLER — {bez} fehlt (suchte '{stueck}')")
                f += 1
            else:
                print(f"    OK — {bez} steht")

    _lauf("Heatmap gegen die Benchmark", p_heat=True, p_heat_bm=True)
    _lauf("Heatmap gegen das Vergleichsportfolio",
          p_heat=True, p_heat_cmp=True, p_cmp=True)

    # Eine Strategie ohne Benchmark darf nicht in eine leere Matrix laufen.
    _lauf("SCHWEIZ ohne Benchmark, Differenz angehakt",
          p_sel1="Muster SCHWEIZ Aktien", p_heat=True, p_heat_bm=True)

    # ── Zeitraum-Kopplung (NEU 14.08.2026) ─────────────────────────────────
    for zeitraum in ("1 Jahr", "3 Jahre", "10 Jahre", "Seit Auflage"):
        _lauf(f"Zeitraum '{zeitraum}'", p_heat=True, p_zeitraum=zeitraum)

    # Der Fall, der die Kopplung heikel macht: „Seit Auflage" MIT
    # Vergleichsportfolio. Die alte Strategie darf ihre Historie NICHT an die
    # Schnittmenge mit der jungen verlieren.
    at = _lauf("Seit Auflage + junges Vergleichsportfolio",
               p_heat=True, p_zeitraum="Seit Auflage", p_cmp=True,
               p_sel1="Muster ausgewogen cVV", p_sel2="Comdirect 100")
    if at is not None:
        captions = " ".join(c.value for c in at.caption)
        if "01/2009" not in captions:
            print("    FEHLER — die Heatmap beginnt nicht bei 01/2009; "
                  "die Schnittmenge hat die Historie beschnitten")
            f += 1
        else:
            print("    OK — volle cVV-Historie trotz jungem Vergleich")

    _lauf("Eigener Zeitraum", p_heat=True, p_zeit_frei=True)

    # Tabelle unter der Heatmap
    at = _lauf("Tabelle anzeigen", p_heat=True, tbl_heat_abs_p1=True)
    if at is not None:
        if not at.dataframe:
            print("    FEHLER — die Tabelle unter der Heatmap fehlt")
            f += 1
        else:
            print(f"    OK — Tabelle steht ({len(at.dataframe)} Stueck)")

    # Alle drei Matrizen mit Tabelle gleichzeitig — Key-Kollisionen faenden
    # sich genau hier.
    _lauf("drei Matrizen, alle mit Tabelle",
          p_heat=True, p_heat_bm=True, p_heat_cmp=True, p_cmp=True,
          tbl_heat_abs_p1=True, tbl_heat_bm_p1=True, tbl_heat_cmp_p1=True)

    # Der Vergleichs-Haken muss auch OHNE Vergleichsportfolio da sein
    # (ausgegraut) und darf dann nichts ausloesen.
    at = _lauf("Vergleichs-Haken ohne Vergleichsportfolio",
               p_heat=True, p_cmp=False, p_heat_cmp=True)
    if at is not None:
        markdown = " ".join(m.value for m in at.markdown)
        if "Differenz zu " in markdown:
            print("    FEHLER — Vergleichs-Matrix erscheint ohne "
                  "Vergleichsportfolio")
            f += 1
        else:
            print("    OK — ohne Vergleichsportfolio keine Vergleichs-Matrix")
    return f


def main():
    print("Pruefstein: Monatsrenditen-Heatmap\n")
    fehler = 0
    for schritt in (schritt1_voller_monat, schritt2_verkettung,
                    schritt3_differenz, schritt4_degeneriert,
                    schritt5_durchschnitt, schritt6_echte_daten,
                    schritt7_apptest):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — angebrochene Monate sind gekennzeichnet, die Zeile "
          "verkettet sich zur Jahresspalte, die Differenz ist geometrisch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
