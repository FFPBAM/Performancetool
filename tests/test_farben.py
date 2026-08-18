"""Pruefstein fuer die festen Assetklassen-Farben (NEU 18.08.2026).

Die Farben der Assetklassen liegen im Corporate Design fest und haengen an
der KATEGORIE, nicht an ihrer Groesse. Am 18.08.2026 gemeldet: Im Ring
"Allokation nach Gattung" bekam die GROESSTE Gattung immer Fuggerblau, weil
die Palette nach dem Sortieren der Reihe nach vergeben wurde.

  1. `ASSET_FARBEN` gegen die VORLAGEN - die Konstante haengt am Artefakt
  2. `klassifiziere_gattung` und `gattung_farbe` an den echten Werten
  3. DIE ZUSAGE: gleiche Kategorie, gleiche Farbe - egal in welcher Ordnung
  4. Region, Segment und Waehrung bleiben bei der Palette

SCHRITT 1 IST DER WICHTIGSTE. Die Palette ist nicht erfunden, sie steht in
den PowerPoint-Vorlagen. Ein Test, der nur die Konstante gegen sich selbst
prueft, wuerde jede Verschiebung mitmachen; dieser oeffnet alle sechs
Vorlagen, liest die tatsaechlichen `<c:dPt>`-Farben und haelt sie dagegen.
Aendert jemand eine Vorlage, schlaegt er an.

SCHRITT 2 HAELT EINE WARNUNG FEST, keine Zusage: Die Klassifizierung arbeitet
mit Teilzeichenketten und trifft deshalb auch Werte, die gar keine Gattungen
sind - "Rentenfonds" (ein SEGMENT) wird als RENTEN gelesen,
"Immobilien-Aktien/Fonds" als AKTIEN. Genau deswegen gelten die festen Farben
nur auf der DIMENSION Gattung und nicht je Kategorie. Faellt dieser Schritt
eines Tages anders aus, ist die Begruendung fuer die Dimensionsregel weg und
gehoert neu geprueft.

Schritt 1 braucht lxml (kommt mit python-pptx), Schritt 2 nichts, Schritte 3
und 4 brauchen pandas/plotly und die echten Bestandsdaten.

    python tests/test_farben.py
"""

import os
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
os.chdir(WURZEL)

from modules.farben import (  # noqa: E402
    ASSET_FARBEN, GROUP_AKTIEN, GROUP_EDELMETALLE, GROUP_LIQUIDITAET,
    GROUP_RENTEN, GROUP_SONSTIGE, gattung_farbe, klassifiziere_gattung,
)

VORLAGEN = "Vorlage"

# Die LIQUIDITAET weicht in zwei Vorlagen ab: ESG, ETF, cVV und comdirect
# fuehren 9FD0EF, FFPB und Thema dagegen D1E9F8. `ASSET_FARBEN` normalisiert
# seit dem 10.07.2026 auf 9FD0EF - eine bestehende Festlegung, die hier
# NAMENTLICH als Ausnahme steht und nicht stillschweigend durchrutscht.
BEKANNTE_ABWEICHUNG = {
    (GROUP_LIQUIDITAET, "D1E9F8"): ("Vorlage_FFPB.pptx", "Vorlage_Thema.pptx"),
}


def _ist(bezeichnung, ist, soll):
    if ist == soll:
        print(f"    OK — {bezeichnung}: {ist!r}")
        return 0
    print(f"    FEHLER — {bezeichnung}: {ist!r} statt {soll!r}")
    return 1


# ─────────────────────────────────────────────────────────────────────────────

def schritt1_vorlagen():
    print("Schritt 1 — ASSET_FARBEN gegen die Vorlagen")
    try:
        import glob
        import re
        import zipfile

        from lxml import etree
    except ImportError as ex:
        print(f"    UEBERSPRUNGEN — {ex}")
        return 0

    dateien = sorted(glob.glob(os.path.join(VORLAGEN, "*.pptx")))
    if not dateien:
        print(f"    UEBERSPRUNGEN — keine Vorlagen in {VORLAGEN}/")
        return 0

    NS_C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
    NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

    f = 0
    geprueft = 0
    abweichungen = []
    for pfad in dateien:
        datei = os.path.basename(pfad)
        with zipfile.ZipFile(pfad) as z:
            for name in sorted(z.namelist()):
                if not re.match(r"ppt/charts/chart\d+\.xml$", name):
                    continue
                baum = etree.fromstring(z.read(name))
                if baum.find(f".//{NS_C}doughnutChart") is None:
                    continue
                kategorien = [e.text for e in
                              baum.findall(f".//{NS_C}cat//{NS_C}pt/{NS_C}v")]
                farben = {}
                for dpt in baum.findall(f".//{NS_C}dPt"):
                    idx = dpt.find(f"{NS_C}idx")
                    clr = dpt.find(f".//{NS_A}solidFill/{NS_A}srgbClr")
                    if idx is not None and clr is not None:
                        farben[int(idx.get("val"))] = clr.get("val").upper()
                for i, roh in enumerate(kategorien):
                    schluessel = (roh or "").strip().upper()
                    if schluessel not in ASSET_FARBEN or i not in farben:
                        continue
                    geprueft += 1
                    ist = farben[i]
                    soll = ASSET_FARBEN[schluessel].upper()
                    if ist == soll:
                        continue
                    erlaubt = BEKANNTE_ABWEICHUNG.get((schluessel, ist))
                    if erlaubt and datei in erlaubt:
                        abweichungen.append(f"{datei}/{schluessel}={ist}")
                        continue
                    print(f"    FEHLER — {datei} {name}: {schluessel} hat "
                          f"{ist}, ASSET_FARBEN sagt {soll}")
                    f += 1

    if geprueft == 0:
        print("    FEHLER — kein einziges Assetklassen-Segment gefunden; "
              "prueft dieser Schritt ueberhaupt etwas?")
        return f + 1
    if not f:
        print(f"    OK — {geprueft} Segmente in {len(dateien)} Vorlagen "
              "stimmen mit ASSET_FARBEN ueberein")
    if abweichungen:
        print(f"    HINWEIS — {len(abweichungen)} bekannte Abweichung(en) bei "
              f"der Liquiditaet, siehe BEKANNTE_ABWEICHUNG: "
              f"{sorted(set(abweichungen))}")

    # Jede der fuenf Gruppen muss in der Tabelle stehen - sonst faerbt
    # `gattung_farbe` irgendwann ins Leere.
    for gruppe in (GROUP_AKTIEN, GROUP_RENTEN, GROUP_EDELMETALLE,
                   GROUP_LIQUIDITAET, GROUP_SONSTIGE):
        if gruppe not in ASSET_FARBEN:
            print(f"    FEHLER — {gruppe} fehlt in ASSET_FARBEN")
            f += 1
    # Und keine Farbe darf ein Doppelkreuz tragen: OOXML will sie ohne, und
    # ein "#" im XML faellt nicht auf - die Datei bleibt gueltig.
    mit_raute = [k for k, v in ASSET_FARBEN.items() if v.startswith("#")]
    if mit_raute:
        print(f"    FEHLER — {mit_raute} tragen ein '#'; OOXML will die Farbe "
              "ohne, und PowerPoint meldet den Fehler nicht")
        f += 1
    else:
        print("    OK — alle Werte ohne '#' (OOXML-Form)")
    return f


def schritt2_klassifizierung():
    print("Schritt 2 — Klassifizierung und Farbe an den echten Werten")
    f = 0

    # Die vier Gattungen, die in den Bestandsdaten wirklich vorkommen.
    for wert, gruppe in (("Aktien", GROUP_AKTIEN),
                         ("Renten", GROUP_RENTEN),
                         ("Edelmetalle", GROUP_EDELMETALLE),
                         ("Liquidität", GROUP_LIQUIDITAET),
                         ("Alternative Investments", GROUP_SONSTIGE),
                         ("Sonstige", GROUP_SONSTIGE)):
        f += _ist(f"{wert!r}", klassifiziere_gattung(wert), gruppe)

    # Fehlwerte werden grau, nicht bunt.
    for wert in (None, float("nan"), "", "   "):
        if klassifiziere_gattung(wert) != GROUP_SONSTIGE:
            print(f"    FEHLER — {wert!r} ist nicht SONSTIGE")
            f += 1
    print("    OK — Fehlwerte werden SONSTIGE")

    # DIE WARNUNG, festgehalten: Diese beiden sind SEGMENT-Werte und werden
    # von der Teilzeichenketten-Heuristik trotzdem als Assetklasse gelesen.
    # Sie sind der Grund, warum die festen Farben an der DIMENSION haengen
    # und nicht an der Kategorie. Faellt das hier eines Tages anders aus, ist
    # die Begruendung fuer die Dimensionsregel weg.
    f += _ist("Segment 'Rentenfonds' (Warnung!)",
              klassifiziere_gattung("Rentenfonds"), GROUP_RENTEN)
    f += _ist("Segment 'Immobilien-Aktien/Fonds' (Warnung!)",
              klassifiziere_gattung("Immobilien-Aktien/Fonds"), GROUP_AKTIEN)

    # `gattung_farbe` liefert die Plotly-Form MIT Doppelkreuz.
    farbe = gattung_farbe("Aktien")
    if not (farbe.startswith("#") and len(farbe) == 7):
        print(f"    FEHLER — gattung_farbe liefert {farbe!r}, erwartet '#RRGGBB'")
        f += 1
    else:
        print(f"    OK — gattung_farbe liefert die Plotly-Form ({farbe})")
    return f


def _bestaende():
    """{Anzeigename: Bestand}, oder None."""
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


def schritt3_zusage():
    print("Schritt 3 — ZUSAGE: gleiche Kategorie, gleiche Farbe")
    bestaende = _bestaende()
    if bestaende is None:
        return 0
    try:
        from modules.portfolioanalyse import build_allocation, build_ring_chart
        from modules.strategievergleich import exposure_figur, exposure_tabelle
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return 0

    f = 0

    # (a) DER RING ueber ALLE 19 Strategien: Dieselbe Gattung muss ueberall
    # dieselbe Farbe tragen - unabhaengig davon, ob sie dort die groesste
    # oder die kleinste Position ist. Genau das war der gemeldete Fehler.
    gesehen = {}
    for name, df in bestaende.items():
        alloc = build_allocation(df, "Gattung")
        if alloc.empty:
            continue
        fig = build_ring_chart(alloc, "Gattung", name)
        for kat, farbe in zip(fig.data[0].labels, fig.data[0].marker.colors):
            soll = gattung_farbe(kat)
            if farbe != soll:
                print(f"    FEHLER — {name}: {kat!r} hat {farbe}, erwartet {soll}")
                f += 1
            gesehen.setdefault(str(kat), set()).add(farbe)
    mehrdeutig = {k: v for k, v in gesehen.items() if len(v) > 1}
    if mehrdeutig:
        print(f"    FEHLER — dieselbe Gattung in mehreren Farben: {mehrdeutig}")
        f += 1
    elif not f:
        print(f"    OK — {len(gesehen)} Gattungen ueber {len(bestaende)} "
              "Strategien, je genau eine Farbe")

    # (b) UMGEDREHTE REIHENFOLGE. Ohne diese Pruefung waere (a) auch erfuellt,
    # wenn die Farbe zufaellig zur Sortierung passt.
    for name in list(bestaende)[:5]:
        alloc = build_allocation(bestaende[name], "Gattung")
        if len(alloc) < 2:
            continue
        normal = dict(zip(*[build_ring_chart(alloc, "Gattung", name).data[0].labels,
                            build_ring_chart(alloc, "Gattung", name).data[0].marker.colors]))
        gedreht_df = alloc.iloc[::-1].reset_index(drop=True)
        gedreht_fig = build_ring_chart(gedreht_df, "Gattung", name)
        gedreht = dict(zip(gedreht_fig.data[0].labels,
                           gedreht_fig.data[0].marker.colors))
        if normal != gedreht:
            print(f"    FEHLER — {name}: umgedrehte Reihenfolge ergibt andere "
                  f"Farben\n        {normal}\n        {gedreht}")
            f += 1
    print("    OK — umgedrehte Reihenfolge ergibt dieselben Farben")

    # (c) DER EXPOSURE-CHART, dieselbe Zusage.
    tab = exposure_tabelle(bestaende, "Gattung")
    fig = exposure_figur(tab, "Gattung")
    for spur in fig.data:
        soll = gattung_farbe(spur.name)
        if spur.marker.color != soll:
            print(f"    FEHLER — Exposure/{spur.name}: {spur.marker.color} "
                  f"statt {soll}")
            f += 1
    print(f"    OK — Exposure/Gattung: {len(fig.data)} Segmente fest gefaerbt")
    return f


def schritt4_andere_dimensionen():
    print("Schritt 4 — Region, Segment und Waehrung bleiben bei der Palette")
    bestaende = _bestaende()
    if bestaende is None:
        return 0
    try:
        from modules.portfolioanalyse import (RING_COLORS, build_allocation,
                                              build_ring_chart)
        from modules.strategievergleich import exposure_figur, exposure_tabelle
    except Exception as ex:
        print(f"    UEBERSPRUNGEN — {type(ex).__name__}: {ex}")
        return 0

    f = 0
    df = list(bestaende.values())[0]
    for dimension in ("Region", "Segment"):
        alloc = build_allocation(df, dimension)
        if alloc.empty:
            continue
        fig = build_ring_chart(alloc, dimension, "x")
        ist = list(fig.data[0].marker.colors)
        soll = RING_COLORS[:len(ist)]
        if ist != soll:
            print(f"    FEHLER — {dimension} folgt nicht mehr der Palette: "
                  f"{ist[:3]} statt {soll[:3]}")
            f += 1
    if not f:
        print("    OK — die Ringe fuer Region und Segment nutzen RING_COLORS")

    # Und im Exposure: Auf einer anderen Achse darf KEINE Gattungsfarbe
    # auftauchen, sonst waechst die Regel still.
    for achse in ("Region", "Währung"):
        tab = exposure_tabelle(bestaende, achse)
        fig = exposure_figur(tab, achse)
        for spur in fig.data:
            if spur.name in ("Liquidität", "ohne Angabe", "übrige Gattungen"):
                continue
            if spur.marker.color.upper().lstrip("#") in {
                    v.upper() for k, v in ASSET_FARBEN.items()
                    if k != GROUP_SONSTIGE}:
                print(f"    FEHLER — Exposure/{achse}: {spur.name!r} traegt "
                      f"die Assetklassen-Farbe {spur.marker.color}")
                f += 1
    print("    OK — auf den anderen Achsen taucht keine Assetklassen-Farbe auf")
    return f


def main():
    print("Pruefstein: feste Assetklassen-Farben\n")
    fehler = 0
    for schritt in (schritt1_vorlagen, schritt2_klassifizierung,
                    schritt3_zusage, schritt4_andere_dimensionen):
        fehler += schritt()
        print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — die Assetklassen tragen ihre feste Farbe, unabhaengig "
          "von ihrer Groesse, und die Tabelle stimmt mit den Vorlagen ueberein")
    return 0


if __name__ == "__main__":
    sys.exit(main())
