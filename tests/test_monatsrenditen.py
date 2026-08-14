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
  7. Die Bandbreite: arithmetisch, je Monat tolerant, festes Fenster
  8. Die FIGUR statt der Daten: Achsentyp, Reihenfolge, Annotationen
  9. Der Zeitraum-Zuschnitt laesst keine Luecken in der aeltesten Zeile
 10. Die Kachelhoehe waechst, wenn es wenige Zeilen gibt
 11. Die Oberflaeche rendert beide Ansichten ohne Fehler (AppTest)

SCHRITT 8 GIBT ES WEGEN EINES FEHLERS, DEN DIE UEBRIGEN NICHT FANDEN
(14.08.2026): Die Bandbreiten-Ansicht war unbrauchbar - vier Zeilen zu einem
Strich zusammengefallen, Werte uebereinander - und alle Pruefsteine waren
gruen. Sie lasen z, text und y aus dem Figur-Objekt, also die DATEN. Die
Geometrie entsteht aber erst beim Rendern, aus Voreinstellungen, die niemand
gesetzt hatte. Schritt 8 prueft deshalb das LAYOUT.

Schritte 1-4 brauchen nur numpy und pandas. Schritt 5 und 7 nutzen die
echten CSVs fuer die Gegenprobe, Schritt 6 braucht sie ganz (streamlit fuer
die Loader), Schritt 8 und 9 brauchen streamlit fuer das Darstellungsmodul,
Schritt 10 die AppTest-Umgebung; alle ueberspringen sich sauber.

    python tests/test_monatsrenditen.py
"""

import datetime
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
    BAND_JAHRE, MONAT_RAND_TOLERANZ_TAGE, _ist_voller_monat, bandbreite,
    heatmap_kennzahlen, historie_beschneiden, monats_durchschnitt,
    monatsrenditen, monatsrenditen_differenz,
)

# Kachelhoehe, Figur-Geometrie und die Zeitraum-Ableitung liegen in der
# Darstellung, nicht in der Mathematik. Sie brauchen streamlit — deshalb erst
# hier und mit sauberem Ueberspringen.
try:
    from modules.risiko_ansicht import (  # noqa: E402
        BAND_GRENZE_MIN, ZEILE_HOEHE_MAX, ZEILE_HOEHE_MIN, _grenze_aus_daten,
        _heatmap_figur, _zeilen_bandbreite, _zeilen_jahr_fuer_jahr,
        _zeilenhoehe, _zellentext_band, zeitraum_fuer_heatmap,
    )
    HAT_ANSICHT = True
except ImportError:
    HAT_ANSICHT = False

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


def schritt7_bandbreite():
    print("Schritt 7 — die Bandbreite: arithmetisch, je Monat tolerant, "
          "festes Fenster")
    f = 0
    f += _ist("BAND_JAHRE steht auf 5", BAND_JAHRE, 5)

    # Sieben Jahre plus ein angebrochenes. Januar bekommt in jedem Jahr einen
    # eigenen Wert, damit Hoch, Tief und Mittel von Hand nachrechenbar sind.
    idx = pd.date_range("2019-01-01", "2026-07-21", freq="D")
    rp = np.zeros(len(idx))
    januar = {2019: 0.20, 2020: 0.05, 2021: -0.03, 2022: 0.01,
              2023: 0.09, 2024: -0.07, 2025: 0.02, 2026: 0.04}
    for jahr, wert in januar.items():
        rp[idx.get_loc(pd.Timestamp(jahr, 1, 15))] = wert
    for jahr in range(2019, 2026):
        for monat in range(2, 13):
            rp[idx.get_loc(pd.Timestamp(jahr, monat, 15))] = 0.002
    for monat in range(2, 8):
        rp[idx.get_loc(pd.Timestamp(2026, monat, 15))] = 0.002
    df = pd.DataFrame({"ret_port": rp}, index=idx)
    m = monatsrenditen(df, 0.0)

    b = bandbreite(m)
    f += _ist("laufendes Jahr ist das juengste", b["aktuelles_jahr"], 2026)
    f += _ist("Fenster sind genau die 5 Jahre DAVOR",
              b["jahre"], [2021, 2022, 2023, 2024, 2025])
    f += _ist("laufendes Jahr NICHT im Band", 2026 in b["jahre"], False)
    f += _ist("2019 und 2020 fallen aus dem Fenster",
              [j for j in (2019, 2020) if j in b["jahre"]], [])

    # Januar 2021..2025: -0,03 / 0,01 / 0,09 / -0,07 / 0,02
    f += _nah("Januar-Hoch", b["hoch"].loc[1], 0.09)
    f += _nah("Januar-Tief", b["tief"].loc[1], -0.07)
    f += _ist("Januar-Hoch stammt aus 2023", b["hoch_wann"].loc[1], 2023)
    f += _ist("Januar-Tief stammt aus 2024", b["tief_wann"].loc[1], 2024)
    f += _ist("Januar: 5 Beobachtungen", int(b["anzahl"].loc[1]), 5)
    # ARITHMETISCH: (-0.03 + 0.01 + 0.09 - 0.07 + 0.02) / 5 = 0.004
    f += _nah("Januar-Mittel ist ARITHMETISCH", b["mittel"].loc[1], 0.004)
    # Zur Gegenprobe das geometrische, das frueher hier stand
    geo = (0.97 * 1.01 * 1.09 * 0.93 * 1.02) ** (1 / 5) - 1.0
    f += _nah("mittel_geo ist das geometrische", b["mittel_geo"].loc[1], geo)
    if abs(b["mittel"].loc[1] - geo) < 1e-6:
        print("    FEHLER — arithmetisch und geometrisch sind gleich; "
              "die Testdaten taugen nicht als Unterscheidung")
        f += 1
    else:
        print(f"    OK — arithmetisch {b['mittel'].loc[1]:.6f} gegen "
              f"geometrisch {geo:.6f}")
    f += _nah("Januar-Trefferquote: 3 von 5", b["trefferquote"].loc[1], 0.6)

    # ── Je Monat tolerant ────────────────────────────────────────────────
    # Ein Loch in EINEM Maerz darf nur den Maerz betreffen.
    mit_loch = df.drop(df.loc["2023-03-01":"2023-03-31"].index)
    bl = bandbreite(monatsrenditen(mit_loch, 0.0))
    f += _ist("Maerz rechnet mit 4 statt 5 Werten",
              int(bl["anzahl"].loc[3]), 4)
    f += _ist("Januar bleibt bei 5", int(bl["anzahl"].loc[1]), 5)
    f += _ist("Maerz hat trotzdem einen Wert",
              bool(pd.notna(bl["mittel"].loc[3])), True)
    f += _nah("Januar-Mittel unveraendert", bl["mittel"].loc[1], 0.004)

    # ── Weniger als BAND_JAHRE Jahre: rechnen statt verweigern ───────────
    kurz = df.loc["2024-01-01":]
    bk = bandbreite(monatsrenditen(kurz, 0.0))
    f += _ist("nur zwei Vergleichsjahre", bk["jahre"], [2024, 2025])
    f += _nah("Januar-Mittel aus zwei Werten", bk["mittel"].loc[1],
              (-0.07 + 0.02) / 2)

    einjahr = df.loc["2025-01-01":]
    b1 = bandbreite(monatsrenditen(einjahr, 0.0))
    f += _ist("ein Vergleichsjahr wird gerechnet", b1["jahre"], [2025])
    f += _nah("Hoch = Mittel bei einem Jahr",
              b1["hoch"].loc[1], b1["mittel"].loc[1])
    f += _nah("Mittel = Tief bei einem Jahr",
              b1["mittel"].loc[1], b1["tief"].loc[1])

    # Kein abgeschlossenes Vergleichsjahr -> leer
    nur_lauf = df.loc["2026-01-01":]
    f += _ist("ohne Vorjahr: leere Bandbreite",
              bandbreite(monatsrenditen(nur_lauf, 0.0))["jahre"], [])
    f += _ist("leere Matrix -> leere Bandbreite",
              bandbreite(monatsrenditen(None))["jahre"], [])

    # ── Angebrochene Monate gehen NICHT ein ──────────────────────────────
    # Der Maerz 2023 wird auf zehn Tage gestutzt: Er darf dann weder Hoch
    # noch Tief stellen, auch wenn sein Wert extrem waere.
    ohne_anfang = df.drop(df.loc["2023-03-01":"2023-03-20"].index)
    ba = bandbreite(monatsrenditen(ohne_anfang, 0.0))
    f += _ist("angebrochener Maerz zaehlt nicht mit",
              int(ba["anzahl"].loc[3]), 4)

    # ── Die Invariante, an allen echten Strategien ───────────────────────
    def _invariante(bez, band):
        fehler = 0
        for monat in range(1, 13):
            h, mi, t = (band["hoch"].loc[monat], band["mittel"].loc[monat],
                        band["tief"].loc[monat])
            if pd.isna(h) or pd.isna(mi) or pd.isna(t):
                continue
            if not (t <= mi + 1e-12 and mi <= h + 1e-12):
                print(f"    FEHLER — {bez} Monat {monat}: Tief {t:.8f} / "
                      f"Mittel {mi:.8f} / Hoch {h:.8f}")
                fehler += 1
        return fehler

    f += _invariante("synthetisch", b)

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
        mm = monatsrenditen(d, float(d["fee_default"].iloc[0]) if len(d) else 0.0)
        band = bandbreite(mm)
        if not band["jahre"]:
            continue
        geprueft += 1
        f += _invariante(name, band)

        if band["aktuelles_jahr"] in band["jahre"]:
            print(f"    FEHLER — {name}: {band['aktuelles_jahr']} steht im "
                  f"eigenen Band")
            f += 1
        if band["jahre"][-1] >= band["aktuelles_jahr"]:
            print(f"    FEHLER — {name}: Band reicht bis {band['jahre'][-1]}")
            f += 1
        if len(band["jahre"]) > BAND_JAHRE:
            print(f"    FEHLER — {name}: {len(band['jahre'])} Jahre bei "
                  f"Fenster {BAND_JAHRE}")
            f += 1

        for monat in range(1, 13):
            h = band["hoch"].loc[monat]
            if pd.isna(h):
                continue
            # Das Extrem muss ein tatsaechlich vorkommender Wert sein, und
            # hoch_wann muss auf genau diese Zelle zeigen.
            jahr = band["hoch_wann"].loc[monat]
            if not bool(np.isclose(mm["renditen"].loc[jahr, monat], h)):
                print(f"    FEHLER — {name} Monat {monat}: hoch_wann zeigt "
                      f"auf {jahr}, dort steht ein anderer Wert")
                f += 1
            # Und das Mittel muss der Schnitt der gueltigen Werte sein
            gueltig = [j for j in band["jahre"]
                       if bool(mm["vollstaendig"].loc[j, monat])
                       and pd.notna(mm["renditen"].loc[j, monat])]
            soll = float(mm["renditen"].loc[gueltig, monat].mean())
            if abs(float(band["mittel"].loc[monat]) - soll) > 1e-12:
                print(f"    FEHLER — {name} Monat {monat}: Mittel "
                      f"{band['mittel'].loc[monat]} statt {soll}")
                f += 1

    print(f"    OK — {geprueft} echte Strategien: Tief <= Mittel <= Hoch, "
          f"laufendes Jahr ausserhalb, Mittel ist der arithmetische Schnitt")
    return f


def schritt8_geometrie():
    print("Schritt 8 — die FIGUR, nicht die Daten: Achsen, Reihenfolge, "
          "Annotationen")
    if not HAT_ANSICHT:
        print("    UEBERSPRUNGEN — modules.risiko_ansicht braucht streamlit")
        return 0

    # WARUM ES DIESEN SCHRITT GIBT (14.08.2026): Die Bandbreiten-Ansicht war
    # unbrauchbar - vier Zeilen zu einem Strich zusammengefallen, Werte
    # uebereinander - und ALLE Pruefsteine waren gruen. Sie lasen z, text und
    # y aus dem Figur-Objekt, also die DATEN. Die Geometrie entsteht aber
    # erst beim Rendern, aus Voreinstellungen, die niemand gesetzt hatte:
    # `yaxis.type` war None, Plotly riet, und ein zahlartiges Zeilenlabel
    # ("2026") sprengte den Achsenbereich.
    #
    # Dieser Schritt prueft deshalb das LAYOUT.
    f = 0
    idx = pd.date_range("2020-01-01", "2026-07-21", freq="D")
    rp = np.zeros(len(idx))
    for jahr in range(2020, 2027):
        for monat in range(1, 13):
            try:
                rp[idx.get_loc(pd.Timestamp(jahr, monat, 15))] = 0.003 * monat
            except KeyError:
                pass
    m = monatsrenditen(pd.DataFrame({"ret_port": rp}, index=idx), 0.0)

    band = bandbreite(m)
    zeilen_b = _zeilen_bandbreite(m, band, "Test")
    fig_b = _heatmap_figur(zeilen_b, _grenze_aus_daten(zeilen_b),
                           mit_jahresspalte=False,
                           zellentext=_zellentext_band, gesaettigt=False)
    zeilen_j = _zeilen_jahr_fuer_jahr(m, "Test")
    fig_j = _heatmap_figur(zeilen_j, 0.03)

    for bez, fig, zeilen, spalten_soll in (
            ("Bandbreite", fig_b, zeilen_b, 12),
            ("Jahr fuer Jahr", fig_j, zeilen_j, 13)):
        lay = fig.layout
        f += _ist(f"{bez}: xaxis.type ist gesetzt", lay.xaxis.type, "category")
        f += _ist(f"{bez}: yaxis.type ist gesetzt", lay.yaxis.type, "category")
        f += _ist(f"{bez}: categoryorder x", lay.xaxis.categoryorder, "array")
        f += _ist(f"{bez}: categoryorder y", lay.yaxis.categoryorder, "array")
        f += _ist(f"{bez}: Spaltenzahl", len(lay.xaxis.categoryarray),
                  spalten_soll)
        f += _ist(f"{bez}: Zeilenzahl", len(lay.yaxis.categoryarray),
                  len(zeilen))
        f += _ist(f"{bez}: z hat so viele Zeilen", len(fig.data[0].z),
                  len(zeilen))
        f += _ist(f"{bez}: z hat so viele Spalten", len(fig.data[0].z[0]),
                  spalten_soll)

        # Plotly zeichnet y[0] UNTEN. Die erste Zeile in Leserichtung muss
        # deshalb die LETZTE Kategorie sein.
        f += _ist(f"{bez}: oberste Zeile", lay.yaxis.categoryarray[-1],
                  zeilen[0]["label"])
        f += _ist(f"{bez}: unterste Zeile", lay.yaxis.categoryarray[0],
                  zeilen[-1]["label"])

        # Annotationen ueber Koordinaten, nicht ueber Beschriftungen: Ein
        # y="2026" verlangt eine zweite Namensaufloesung, die scheitern kann.
        nicht_zahl = [a.y for a in lay.annotations
                      if not isinstance(a.y, (int, float))]
        f += _ist(f"{bez}: keine Annotation mit Text-y", nicht_zahl, [])
        ausserhalb = [a.y for a in lay.annotations
                      if not (0 <= float(a.y) <= len(zeilen) - 1)]
        f += _ist(f"{bez}: alle Annotationen im Zeilenbereich", ausserhalb, [])

    # Die Bandbreite hat KEINE Jahresspalte und damit keine Annotationen
    f += _ist("Bandbreite ohne Jahresspalte: keine Annotation",
              len(fig_b.layout.annotations), 0)
    f += _ist("Jahr fuer Jahr hat Annotationen",
              bool(len(fig_j.layout.annotations) > 0), True)
    f += _ist("Bandbreite: Spaltenkopf 'Jahr' fehlt",
              "Jahr" in list(fig_b.layout.xaxis.categoryarray), False)
    f += _ist("Jahr fuer Jahr: Spaltenkopf 'Jahr' da",
              list(fig_j.layout.xaxis.categoryarray)[-1], "Jahr")

    # Die datengetriebene Grenze
    grenze = _grenze_aus_daten(zeilen_b)
    groesster = max(abs(float(zl["werte"].loc[k]))
                    for zl in zeilen_b for k in range(1, 13)
                    if pd.notna(zl["werte"].loc[k]))
    f += _ist("Grenze deckt den groessten Betrag", bool(grenze >= groesster),
              True)
    f += _ist("Grenze nicht unter der Untergrenze",
              bool(grenze >= BAND_GRENZE_MIN), True)
    f += _ist("leere Zeilen -> Untergrenze", _grenze_aus_daten([]),
              BAND_GRENZE_MIN)

    # Zellformat der Bandbreite: zwei Stellen, kein Plus
    f += _ist("Zellformat positiv", _zellentext_band(0.0341, True), "3,41")
    f += _ist("Zellformat negativ", _zellentext_band(-0.059, True), "-5,90")
    f += _ist("Zellformat angebrochen", _zellentext_band(0.008, False), "0,80*")
    f += _ist("Zellformat Fehlwert", _zellentext_band(None, True), "")
    return f


def schritt9_zeitraum():
    print("Schritt 9 — der Zeitraum-Zuschnitt laesst keine Luecken")
    if not HAT_ANSICHT:
        print("    UEBERSPRUNGEN — modules.risiko_ansicht braucht streamlit")
        return 0

    # WARUM ES DIESEN SCHRITT GIBT (14.08.2026): Die Ableitung des Zeitraums
    # stand INLINE in streamlit_app.py und war fuer keinen Pruefstein
    # erreichbar - obwohl zehn Schritte auf dieser Heatmap liegen. Sie
    # rechnete `maxd - N Jahre`; bei Datenstand 21.07.2026 schnitt
    # "3 Jahre" damit am 21.07.2023, und Januar bis Juni 2023 fehlten als
    # Kacheln. Sechs Luecken, bei JEDER Schnellwahl.
    #
    # Eine leere Kachel bedeutet in dieser Matrix aber schon etwas: "die
    # Strategie lief da noch nicht". Zwei Bedeutungen, ein Aussehen (#46).
    f = 0
    maxd = datetime.date(2026, 7, 21)

    faelle = [
        # (jahre, erwartetes von, warum)
        (1,  datetime.date(2025, 1, 1),  "1 Jahr"),
        (3,  datetime.date(2023, 1, 1),  "3 Jahre - der gemeldete Fall"),
        (5,  datetime.date(2021, 1, 1),  "5 Jahre"),
        (10, datetime.date(2016, 1, 1),  "10 Jahre"),
    ]
    for jahre, soll, warum in faelle:
        von, bis, gerundet = zeitraum_fuer_heatmap(jahre, False, None, None, maxd)
        f += _ist(f"{warum}: von", von, soll)
        f += _ist(f"{warum}: bis bleibt offen", bis, None)
        f += _ist(f"{warum}: als gerundet gemeldet", gerundet, True)
        # Die Zusage, die die alte Formel verletzte
        if not (von.month == 1 and von.day == 1):
            print(f"    FEHLER — {warum}: {von} ist kein Jahresanfang")
            f += 1

    von, bis, gerundet = zeitraum_fuer_heatmap(None, False, None, None, maxd)
    f += _ist("Seit Auflage: von", von, None)
    f += _ist("Seit Auflage: bis", bis, None)
    f += _ist("Seit Auflage: nicht gerundet", gerundet, False)

    # Ein eigener Zeitraum wird WOERTLICH genommen
    sd, ed = datetime.date(2023, 5, 15), datetime.date(2026, 6, 20)
    von, bis, gerundet = zeitraum_fuer_heatmap(None, True, sd, ed, maxd)
    f += _ist("eigener Zeitraum: von unveraendert", von, sd)
    f += _ist("eigener Zeitraum: bis unveraendert", bis, ed)
    f += _ist("eigener Zeitraum: nicht gerundet", gerundet, False)
    # Auch wenn zusaetzlich eine Jahreszahl gesetzt ist, gewinnt die Eingabe
    f += _ist("eigener Zeitraum schlaegt die Schnellwahl",
              zeitraum_fuer_heatmap(3, True, sd, ed, maxd)[0], sd)

    # Jahreswechsel: Der Zuschnitt haengt nur am JAHR des Datenstands
    for stand in (datetime.date(2026, 12, 31), datetime.date(2026, 1, 1)):
        f += _ist(f"Datenstand {stand}: '3 Jahre'",
                  zeitraum_fuer_heatmap(3, False, None, None, stand)[0],
                  datetime.date(2023, 1, 1))

    # ── Die Wirkung: keine Luecke in der aeltesten Zeile ─────────────────
    try:
        from modules.shared import (
            DATA_FOLDER, EXCLUDE_SUBSTRINGS, detect_newest_date_tag,
            load_all_csvs, load_mapping, build_portfolio_timeseries,
        )
        from modules.risiko_ansicht import _zuschnitt
    except ImportError as ex:
        print(f"    HINWEIS — echte Daten uebersprungen: {ex}")
        return f

    tag = detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS)
    if tag is None:
        print("    HINWEIS — keine CSVs gefunden")
        return f
    ts = build_portfolio_timeseries(
        load_all_csvs(DATA_FOLDER, tag, EXCLUDE_SUBSTRINGS), load_mapping())

    luecken = 0
    geprueft = 0
    for name in sorted(ts):
        voll = historie_beschneiden(ts[name], name)
        fee = float(voll["fee_default"].iloc[0]) if len(voll) else 0.0
        echt_maxd = voll.index.max().date()
        for jahre in (1, 3, 5, 10, None):
            von, bis, _ = zeitraum_fuer_heatmap(jahre, False, None, None,
                                                echt_maxd)
            aus = _zuschnitt(voll, von, bis)
            if aus is None or len(aus) == 0:
                continue
            m = monatsrenditen(aus, fee)
            aelteste = min(m["renditen"].index)
            # Nur pruefen, wenn die Strategie in diesem Jahr durchgehend
            # lief - sonst sind die Luecken echt (Auflage mitten im Jahr).
            if voll.index.min().date() > datetime.date(int(aelteste), 1, 4):
                continue
            geprueft += 1
            leer = int(m["renditen"].loc[aelteste].isna().sum())
            if leer:
                print(f"    FEHLER — {name} / {jahre} Jahre: {leer} leere "
                      f"Kacheln in der aeltesten Zeile ({aelteste})")
                luecken += 1
    f += luecken
    if not luecken:
        print(f"    OK — {geprueft} Faelle: keine leere Kachel in der "
              f"aeltesten Jahreszeile")
    return f


def schritt10_kachelgroesse():
    print("Schritt 10 — die Kachelhoehe waechst, wenn es wenige Zeilen gibt")
    if not HAT_ANSICHT:
        print("    UEBERSPRUNGEN — modules.risiko_ansicht braucht streamlit")
        return 0
    f = 0
    f += _ist("Untergrenze", ZEILE_HOEHE_MIN, 30.0)
    f += _ist("Obergrenze", ZEILE_HOEHE_MAX, 80.0)

    for zeilen, soll in ((1, 80.0), (2, 80.0), (4, 80.0), (6, 80.0),
                         (8, 75.0), (11, 600 / 11), (19, 600 / 19),
                         (25, 30.0), (40, 30.0)):
        f += _nah(f"{zeilen} Zeilen", _zeilenhoehe(zeilen), soll, 1e-9)

    # Monoton fallend und immer innerhalb der Grenzen
    vorher = None
    for zeilen in range(1, 60):
        h = _zeilenhoehe(zeilen)
        if not (ZEILE_HOEHE_MIN <= h <= ZEILE_HOEHE_MAX):
            print(f"    FEHLER — {zeilen} Zeilen: {h} ausserhalb der Grenzen")
            f += 1
        if vorher is not None and h > vorher + 1e-9:
            print(f"    FEHLER — {zeilen} Zeilen hoeher als {zeilen - 1}")
            f += 1
        vorher = h
    print("    OK — monoton fallend, nie ausserhalb der Grenzen")

    # Null und negativ duerfen nicht durch null teilen
    f += _nah("0 Zeilen", _zeilenhoehe(0), ZEILE_HOEHE_MAX, 1e-9)
    f += _nah("-1 Zeilen", _zeilenhoehe(-1), ZEILE_HOEHE_MAX, 1e-9)
    return f


def schritt11_apptest():
    print("Schritt 11 — die Oberflaeche rendert die Heatmap ohne Fehler")
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
        # Ein nicht existierender Wert fuer ein Auswahlfeld wird von
        # Streamlit STILLSCHWEIGEND ignoriert - der Test liefe dann gegen die
        # Standardstrategie und bewiese nichts. Genau das ist am 14.08.2026
        # passiert: Die Auswahlfelder fuehren ANZEIGEnamen ("Comdirect_100"),
        # eingesetzt waren aber die CSV-Namen ("Comdirect 100").
        for schluessel in ("p_sel1", "p_sel2"):
            if schluessel not in zustand:
                continue
            ist = next((s.value for s in at.selectbox
                        if s.key == schluessel), None)
            if ist != zustand[schluessel]:
                print(f"    FEHLER — {bez}: {schluessel} steht auf {ist!r} "
                      f"statt {zustand[schluessel]!r} (kein gueltiger "
                      f"Anzeigename?)")
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
          p_sel1="Schweiz_aktienorientiert", p_heat=True, p_heat_bm=True)

    # ── Zeitraum-Kopplung (NEU 14.08.2026) ─────────────────────────────────
    for zeitraum in ("1 Jahr", "3 Jahre", "10 Jahre", "Seit Auflage"):
        _lauf(f"Zeitraum '{zeitraum}'", p_heat=True, p_zeitraum=zeitraum)

    # Der Fall, der die Kopplung heikel macht: „Seit Auflage" MIT
    # Vergleichsportfolio. Die alte Strategie darf ihre Historie NICHT an die
    # Schnittmenge mit der jungen verlieren.
    at = _lauf("Seit Auflage + junges Vergleichsportfolio",
               p_heat=True, p_zeitraum="Seit Auflage", p_cmp=True,
               p_sel1="cVV ausgewogen", p_sel2="Comdirect_100")
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

    # ── Die zweite Ansicht (NEU 14.08.2026) ────────────────────────────────
    # Das Fenster ist FEST fuenf Kalenderjahre — die Zeitraum-Auswahl darf
    # daran nichts aendern. Deshalb wird hier ausdruecklich ein anderer
    # Zeitraum gesetzt und trotzdem 2021-2025 erwartet.
    at = _lauf("Bandbreiten-Ansicht (Zeitraum '3 Jahre' gesetzt)",
               p_heat=True, p_heat_ansicht="Bandbreite", p_zeitraum="3 Jahre")
    if at is not None:
        captions = " ".join(c.value for c in at.caption)
        for stueck, bez in (("die letzten 5 Kalenderjahre",
                             "Erklaerung des festen Fensters"),
                            ("2021–2025",
                             "das Fenster trotz Zeitraum '3 Jahre'"),
                            ("gegen 5 Jahre", "Kennzeile"),
                            ("nicht enthalten", "Hinweis laufendes Jahr"),
                            ("arithmetischer Durchschnitt",
                             "Hinweis auf das arithmetische Mittel"),
                            ("wirkt in dieser Ansicht nicht",
                             "Hinweis zur Zeitraum-Auswahl")):
            if stueck not in captions:
                print(f"    FEHLER — {bez} fehlt (suchte '{stueck}')")
                f += 1
            else:
                print(f"    OK — {bez} steht")

    # Umschalten muss die Zeilenzahl aendern. Plotly-Charts erfasst AppTest
    # nicht, wohl aber die Captions — die Ø-Erklaerung gibt es NUR in
    # "Jahr fuer Jahr", die Bandbreiten-Erklaerung NUR in "Bandbreite".
    at_jahre = _lauf("Ansicht 'Jahr fuer Jahr'", p_heat=True,
                     p_heat_ansicht="Jahr für Jahr")
    if at_jahre is not None:
        captions = " ".join(c.value for c in at_jahre.caption)
        if "Vergleichsfenster" in captions:
            print("    FEHLER — Bandbreiten-Erklaerung in 'Jahr fuer Jahr'")
            f += 1
        elif "geometrisches Mittel über die" not in captions:
            print("    FEHLER — Ø-Erklaerung fehlt in 'Jahr fuer Jahr'")
            f += 1
        else:
            print("    OK — die beiden Ansichten zeigen verschiedene Texte")

    # Wenig Historie: Es wird trotzdem gerechnet, ehrlich beschriftet und
    # mit einem Vorbehalt versehen. Comdirect_100 (Auflage 03/2024) hat 2024
    # und 2025 als Vergleichsjahre - unter BAND_DUENN_UNTER.
    at = _lauf("Bandbreite mit kurzer Historie",
               p_sel1="Comdirect_100", p_heat=True,
               p_heat_ansicht="Bandbreite")
    if at is not None:
        captions = " ".join(c.value for c in at.caption)
        if "Vergleichsjahr" not in captions:
            print("    FEHLER — Vorbehalt bei duenner Bandbreite fehlt")
            f += 1
        else:
            print("    OK — Vorbehalt steht")
        if "Vergleichsfenster" not in captions:
            print("    FEHLER — es wird gar keine Bandbreite gezeigt")
            f += 1
        else:
            print("    OK — es wird trotzdem gerechnet")
    at = _lauf("dieselbe Strategie in 'Jahr fuer Jahr'",
               p_sel1="Comdirect_100", p_heat=True,
               p_heat_ansicht="Jahr für Jahr")
    if at is not None:
        captions = " ".join(c.value for c in at.caption)
        if "Vergleichsfenster" in captions:
            print("    FEHLER — 'Jahr fuer Jahr' zeigt Bandbreiten-Texte")
            f += 1
        else:
            print("    OK — 'Jahr fuer Jahr' bleibt unberuehrt")

    # Der Umschalter wirkt auch auf die Differenz-Matrizen
    _lauf("Bandbreite mit beiden Differenzen",
          p_heat=True, p_heat_ansicht="Bandbreite",
          p_heat_bm=True, p_heat_cmp=True, p_cmp=True)
    # Und mit jedem Zeitraum
    for zeitraum in ("3 Jahre", "5 Jahre", "Seit Auflage"):
        _lauf(f"Bandbreite mit Zeitraum '{zeitraum}'", p_heat=True,
              p_heat_ansicht="Bandbreite", p_zeitraum=zeitraum)
    _lauf("Bandbreite mit eigenem Zeitraum", p_heat=True,
          p_heat_ansicht="Bandbreite", p_zeit_frei=True)
    return f


def main():
    print("Pruefstein: Monatsrenditen-Heatmap\n")
    fehler = 0
    for schritt in (schritt1_voller_monat, schritt2_verkettung,
                    schritt3_differenz, schritt4_degeneriert,
                    schritt5_durchschnitt, schritt6_echte_daten,
                    schritt7_bandbreite, schritt8_geometrie,
                    schritt9_zeitraum, schritt10_kachelgroesse,
                    schritt11_apptest):
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
