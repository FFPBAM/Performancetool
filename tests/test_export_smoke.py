"""End-to-End-Test: erzeugt fuer jede Familie eine echte Broschuere.

Bildet nach, was render_portfolioanalyse beim Klick auf "PowerPoint
erstellen" tut — ohne Oberflaeche. Geprueft wird je Datei:
  - der Export laeuft ohne Exception durch
  - die Folienzahl stimmt (bei Thema inkl. Duplikation fuer N Strategien)
  - LAST_BUILD_ERRORS ist leer
  - die erzeugte Datei laesst sich wieder oeffnen

Braucht python-pptx, streamlit und die echten Daten. Fehlt etwas davon,
wird sauber uebersprungen statt zu scheitern.

    python tests/test_export_smoke.py [ausgabeordner]

Die erzeugten PPTX bitte STICHPROBENARTIG IN ECHTEM PowerPoint oeffnen —
LibreOffice reicht nicht (Transferwissen #16/#28).
"""

import io
import os
import sys
import tempfile
import traceback

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

# Vorlage/ und Daten/ werden im Code relativ zum Arbeitsverzeichnis geladen
os.chdir(WURZEL)

try:
    from pptx import Presentation
except ImportError:
    print("UEBERSPRUNGEN — python-pptx nicht installiert")
    sys.exit(0)

try:
    from modules.shared import (
        DATA_FOLDER, DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS,
        detect_newest_date_tag, load_all_csvs, load_mapping,
        load_name_mapping, build_portfolio_timeseries,
    )
    from modules.portfolioanalyse import (
        load_pf_csvs, build_pf_data, duration_info_aus_bestand,
        VORLAGEN_FAMILIEN, FAMILIE_ALLE_STRATEGIEN, _familien_portfolios,
        _vorlage_fuer_strategie, _familie_fuer_strategie,
        historie_beschneiden,
    )
    from modules import pptx_export
    from modules.pptx_export import generate_portfolioanalyse_pptx
    from modules import pdf_export
except ImportError as ex:
    print(f"UEBERSPRUNGEN — Abhaengigkeit fehlt: {ex}")
    sys.exit(0)

# Familie "Thema" laeuft als einzige im Dupliziermodus: pro zusaetzlicher
# Strategie waechst die Broschuere um den Block F10-13 (vier Folien).
THEMA_STRATEGIEN = ["Offensiv", "Pro", "Pro Dividende"]
THEMA_BLOCK = 4
# Die Grundzahl haengt seit 21.09.2026 an der LEITSTRATEGIE (Offensiv 20,
# Pro/Pro Dividende 22 Folien) und wird deshalb aus deren Config gelesen.


def _daten():
    tag = detect_newest_date_tag(DATA_FOLDER_PF, EXCLUDE_SUBSTRINGS)
    pf_data = build_pf_data(load_pf_csvs(DATA_FOLDER_PF, tag))
    nm = load_name_mapping()
    sp = nm.columns
    gefiltert = nm[nm[sp[1]].isin(set(pf_data.keys()))]
    mapping = load_mapping()
    ts = build_portfolio_timeseries(
        load_all_csvs(DATA_FOLDER,
                      detect_newest_date_tag(DATA_FOLDER, EXCLUDE_SUBSTRINGS),
                      EXCLUDE_SUBSTRINGS),
        mapping)
    return {
        "tag": tag,
        "pf_data": pf_data,
        "nm": nm,
        "namen": gefiltert[sp[0]].tolist(),
        "d2c": dict(zip(gefiltert[sp[0]], gefiltert[sp[1]])),
        "d2b": dict(zip(gefiltert[sp[0]], gefiltert[sp[3]])),
        "mapping": mapping,
        "ts": ts,
    }


def _portfolio(name, d):
    csv_n = d["d2c"][name]
    df = d["pf_data"][csv_n]
    ad = (df["Auswertungsdatum"].iloc[0]
          if "Auswertungsdatum" in df.columns else None)
    return (name, df, ad, duration_info_aus_bestand(df))


def _perf_inputs(portfolios, d, familie=""):
    """Wie render_portfolioanalyse die performance_inputs baut — inklusive
    Beschneiden auf den Historien-Beginn der Datenreihe (HISTORIE_AB)."""
    raus = []
    for name, _df, _ad, dur in portfolios:
        csv_n = d["d2c"].get(name)
        treffer = d["mapping"].loc[d["mapping"]["Inhaber"] == csv_n,
                                   "Honorarsatz Standard"]
        bm = d["d2b"].get(name)
        if bm is None or str(bm).strip().lower() in (
                "", "nan", "none", "haben keine benchmark"):
            bm = None
        else:
            bm = str(bm).strip()
        ts = d["ts"].get(csv_n) if csv_n else None
        raus.append({
            "timeseries_df": historie_beschneiden(ts, csv_n),
            "fee_dec": float(treffer.values[0]) if len(treffer) else 0.0,
            "duration": dur.get("duration") if isinstance(dur, dict) else None,
            "benchmark_text": bm,
        })
    return raus


def _bauen(portfolios, familie, d, ausgabe, dateiname):
    # Strategie-basierte Vorlagenauflösung wie im Produktionsweg (NEU
    # 17.09.2026): Die Leitstrategie (portfolios[0][0]) wählt die Vorlage —
    # für Thema-Strategien mit eigenen Anfangsfolien und für SCHWEIZ (F2/F3
    # entfernt). Für alle anderen fällt _vorlage_fuer_strategie auf die Familie
    # zurück, das Ergebnis ist identisch zu vorher.
    tpl, cfg = _vorlage_fuer_strategie(d["nm"], portfolios[0][0])
    daten = generate_portfolioanalyse_pptx(
        portfolios, 0.0, performance_inputs=_perf_inputs(portfolios, d, familie),
        template_path=tpl, template_config=cfg)
    ziel = os.path.join(ausgabe, dateiname)
    with open(ziel, "wb") as f:
        f.write(daten)
    return ziel, len(daten), list(pptx_export.LAST_BUILD_ERRORS)


def main():
    ausgabe = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="ffpb_export_")
    os.makedirs(ausgabe, exist_ok=True)

    d = _daten()
    print(f"Datenstand {d['tag']} — {len(d['pf_data'])} Portfolios, "
          f"{len(d['ts'])} Zeitreihen")
    print(f"Ausgabe: {ausgabe}\n")
    print(f"{'Fall':28s} {'Folien':>6s} {'soll':>5s} {'MB':>6s}  Status")
    print("-" * 68)

    fehler = 0

    # ── Teil 1: je Familie eine Broschuere ──────────────────────────────
    for familie in sorted(VORLAGEN_FAMILIEN):
        strategie = next((n for n in d["namen"]
                          if _familie_fuer_strategie(d["nm"], n) == familie), None)
        if strategie is None:
            print(f"{familie:28s} {'-':>6s} {'-':>5s} {'-':>6s}  "
                  f"UEBERSPRUNGEN (keine Strategie in den Daten)")
            continue
        try:
            alle = FAMILIE_ALLE_STRATEGIEN.get(familie)
            if alle:
                portfolios, fehlend = _familien_portfolios(
                    alle, d["namen"], d["d2c"], d["pf_data"],
                    duration_info_aus_bestand)
                if fehlend:
                    print(f"{familie:28s} {'-':>6s} {'-':>5s} {'-':>6s}  "
                          f"UEBERSPRUNGEN (fehlende Daten: {', '.join(fehlend)})")
                    continue
            else:
                portfolios = [_portfolio(strategie, d)]

            ziel, groesse, meldungen = _bauen(portfolios, familie, d, ausgabe,
                                              f"{familie}.pptx")
            n = len(Presentation(ziel).slides)
            # Soll aus der STRATEGIE-Config der Leitstrategie (berücksichtigt
            # z.B. SCHWEIZ mit entfernten Anfangsfolien), nicht stur aus der
            # Familie — sonst schlägt Teil 1 falsch an, wenn die erste
            # Thema-Strategie eine SCHWEIZ-Strategie ist.
            _, _cfg = _vorlage_fuer_strategie(d["nm"], portfolios[0][0])
            soll = _cfg.get("erwartete_folien") - len(_cfg.get("entfernen") or [])
            # Im Dupliziermodus waechst die Folienzahl mit den Strategien
            if _cfg.get("block_positionen"):
                soll += THEMA_BLOCK * (len(portfolios) - 1)
            ok = n == soll and not meldungen
            fehler += 0 if ok else 1
            print(f"{familie:28s} {n:6d} {soll:5d} {groesse/1048576:6.2f}  "
                  f"{'OK' if ok else 'ABWEICHUNG'}")
            for m in meldungen:
                print(f"    ! {m[:96]}")
        except Exception as ex:
            fehler += 1
            print(f"{familie:28s} {'-':>6s} {'-':>5s} {'-':>6s}  "
                  f"FEHLER: {type(ex).__name__}: {ex}")
            traceback.print_exc()

    # ── Teil 2: Thema mit mehreren Strategien (Dupliziermodus) ──────────
    # Der einzige Pfad, auf dem _vervielfaeltige_block laeuft. Waere
    # _THEMA_CONFIG faelschlich auf modus="fest" gestellt, blieben es
    # immer die Grundzahl und die Zusatzstrategien haetten stillschweigend keine.
    for anzahl in (2, 3):
        namen = [n for n in THEMA_STRATEGIEN if n in d["d2c"]][:anzahl]
        if len(namen) < anzahl:
            print(f"{'Thema x' + str(anzahl):28s} {'-':>6s} {'-':>5s} {'-':>6s}  "
                  f"UEBERSPRUNGEN (nur {len(namen)} Themen-Strategien in den Daten)")
            continue
        try:
            portfolios = [_portfolio(n, d) for n in namen]
            ziel, groesse, meldungen = _bauen(portfolios, "Thema", d, ausgabe,
                                              f"Thema_{anzahl}.pptx")
            n = len(Presentation(ziel).slides)
            _tpl, _cfg = _vorlage_fuer_strategie(d["nm"], namen[0])
            soll = (_cfg["erwartete_folien"] - len(_cfg.get("entfernen") or [])
                    + THEMA_BLOCK * (anzahl - 1))
            ok = n == soll and not meldungen
            fehler += 0 if ok else 1
            print(f"{'Thema x' + str(anzahl) + ' (Duplikation)':28s} {n:6d} {soll:5d} "
                  f"{groesse/1048576:6.2f}  {'OK' if ok else 'ABWEICHUNG'}")
            for m in meldungen:
                print(f"    ! {m[:96]}")
        except Exception as ex:
            fehler += 1
            print(f"{'Thema x' + str(anzahl):28s} {'-':>6s} {'-':>5s} {'-':>6s}  "
                  f"FEHLER: {type(ex).__name__}: {ex}")
            traceback.print_exc()

    # ── Teil 3: Thema-Strategien mit eigenen Anfangsfolien (NEU 17.09.2026) ──
    # Offensiv/Pro Dividende bekommen eigene F2/F3, beide SCHWEIZ keine
    # (Folie 2 wird dann "Aktien – die guten Jahre überwiegen"). Geprueft:
    # Folienzahl (mit entfernen), F2-Titel, KEINE externen Verknuepfungen.
    print("\nTeil 3: strategie-spezifische Anfangsfolien (Thema)")
    THEMA_F2 = {
        "Offensiv": ("Offensiv", "PRO"),
        "Pro": ("PRO", None),
        "Pro Dividende": ("Pro Dividende", "PRO"),
        "Schweiz_aktienorientiert": ("Aktien – die guten Jahre", "PRO"),
        "Schweiz_substanzorientiert": ("Aktien – die guten Jahre", "PRO"),
    }
    for strat, (muss, darf_nicht) in THEMA_F2.items():
        if strat not in d["d2c"]:
            print(f"   {strat:28s} UEBERSPRUNGEN (nicht in den Daten)")
            continue
        try:
            tpl, cfg = _vorlage_fuer_strategie(d["nm"], strat)
            port = [_portfolio(strat, d)]
            daten = generate_portfolioanalyse_pptx(
                port, 0.0, performance_inputs=_perf_inputs(port, d, "Thema"),
                template_path=tpl, template_config=cfg)
            meldungen = list(pptx_export.LAST_BUILD_ERRORS)
            prs = Presentation(io.BytesIO(daten))
            n = len(prs.slides)
            soll = cfg["erwartete_folien"] - len(cfg.get("entfernen") or [])
            t2 = prs.slides[1].shapes.title
            f2 = t2.text_frame.text.replace("\n", " ").strip() if t2 is not None else ""
            extern = pdf_export.externe_verknuepfungen(daten)
            probleme = []
            if n != soll:
                probleme.append(f"{n} Folien statt {soll}")
            if muss not in f2:
                probleme.append(f"F2 «{f2}» enthaelt nicht {muss!r}")
            if darf_nicht and darf_nicht in f2:
                probleme.append(f"F2 «{f2}» enthaelt faelschlich {darf_nicht!r}")
            if extern:
                probleme.append(f"externe Verknuepfungen: {extern[:2]}")
            if meldungen:
                probleme.append(f"Build-Meldungen: {meldungen}")
            fehler += 1 if probleme else 0
            print(f"   {'FEHLER' if probleme else 'OK':6s} {strat:28s} {n:2d} Folien, F2 «{f2[:34]}»"
                  + ("  " + "; ".join(probleme) if probleme else ""))
        except Exception as ex:
            fehler += 1
            print(f"   FEHLER {strat:28s} {type(ex).__name__}: {ex}")
            traceback.print_exc()

    # Gegenprobe, dass der Detektor misst: ein Original unter H: TRAEGT
    # externe Verknuepfungen (skip-if-not-present, kein Fehler wenn H: fehlt).
    import glob as _glob
    _orig = _glob.glob(r"H:\Entwicklung\Forschung_Claude\Performancetool"
                       r"\Themenvorlageneu\*.pptx")
    if _orig:
        with open(_orig[0], "rb") as fh:
            roh = fh.read()
        if pdf_export.externe_verknuepfungen(roh):
            print("   OK — Gegenprobe: Original-Broschuere traegt externe "
                  "Verknuepfungen (Detektor misst wirklich)")
        else:
            print("   FEHLER — Gegenprobe: Original ohne externe Verknuepfungen?")
            fehler += 1

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Fall/Faelle")
        return 1
    print("BESTANDEN — alle Broschueren erzeugt und wieder lesbar")
    print("Hinweis: stichprobenartig in ECHTEM PowerPoint oeffnen (#16/#28).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
