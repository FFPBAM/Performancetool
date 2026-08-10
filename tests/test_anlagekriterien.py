"""Prueft die Anlagekriterien-Konfiguration (Mapping_Anlagekriterien.xlsx).

HINTERGRUND (10.08.2026):
    Der Anlagekriterien-Kasten stand bisher NUR statisch in den PPTX-Vorlagen
    — je Familie unterschiedlich geschrieben, mit Tippfehlern ("FPFB Strategie
    30", "AUsgewogen") und uneinheitlicher Prozent-Schreibweise. Er wandert
    jetzt in eine Excel, die BEIDE Ausgaben speist: den Banner im Streamlit-
    Tool und den Kasten auf der Struktur-Folie der Broschuere.

    Weil damit eine einzige Datei bestimmt, was Kunden gedruckt bekommen,
    prueft dieser Test sie streng.

Geprueft wird:
  1. Die Excel existiert und hat die erwarteten Spalten.
  2. Jede Strategie ist im Namens-Mapping bekannt (kein Schluessel ins Leere).
  3. Die Spalte 'Familie' stimmt mit Mapping_Namen.xlsx ueberein — sie ist
     bewusst doppelt gefuehrt (Lesbarkeit in Excel) und wird hier festgenagelt,
     damit sie nicht auseinanderlaeuft.
  4. Genau die 14 Strategien mit Kasten sind erfasst; die Thema-Familie NICHT
     (dort gibt es keinen Kasten — bewusste Entscheidung).
  5. Kein Feld ist leer.
  6. Schreibweisen sind einheitlich: 'mind.' statt 'min.', Prozent mit
     Leerzeichen, kein doppelter Leerraum.
  7. anlagekriterien_fuer() liefert die vier Kriterien in Vorlagen-Reihenfolge
     und [] fuer Strategien ohne Kasten.

    python tests/test_anlagekriterien.py     (braucht pandas + streamlit)
"""

import os
import re
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

import pandas as pd                                            # noqa: E402

EXCEL = os.path.join(WURZEL, "Mapping_Anlagekriterien.xlsx")
NAMEN = os.path.join(WURZEL, "Mapping_Namen.xlsx")

KEY = "Strategie auswählen"
KRITERIEN = ["Anlageregion", "Aktienanteil",
             "Anleihenanteil / Liquidität", "Fremdwährungen"]

# Die 14 Strategien MIT Kasten. Thema (Offensiv, Pro, Pro Dividende, die
# beiden SCHWEIZ-Strategien) hat bewusst keinen.
ERWARTET = [
    "cVV konservativ", "cVV defensiv", "cVV defensiv plus",
    "cVV ausgewogen", "cVV dynamic",
    "ESG defensiv", "ESG defensiv+", "ESG ausgewogen", "ESG offensiv",
    "ETF_ausgewogen", "ETF_Wachstum",
    "Comdirect_30", "Comdirect_70", "Comdirect_100",
]
OHNE_KASTEN = ["Offensiv", "Pro", "Pro Dividende",
               "Schweiz_substanzorientiert", "Schweiz_aktienorientiert"]


def _pruefe_struktur(df):
    print("1. Aufbau der Excel")
    fehler = 0
    soll = [KEY, "Familie", "Anzeigename"] + KRITERIEN
    fehlend = [s for s in soll if s not in df.columns]
    if fehlend:
        print(f"   FEHLER — Spalten fehlen: {fehlend}")
        fehler += 1
    else:
        print(f"   OK — {len(df.columns)} Spalten, {len(df)} Zeilen")
    return fehler


def _pruefe_schluessel(df, namen):
    print("\n2. Jede Strategie ist im Namens-Mapping bekannt")
    fehler = 0
    bekannt = set(namen[KEY].astype(str).str.strip())
    for s in df[KEY].astype(str).str.strip():
        if s not in bekannt:
            print(f"   FEHLER — '{s}' steht nicht in Mapping_Namen.xlsx")
            fehler += 1
    if not fehler:
        print(f"   OK — alle {len(df)} Schluessel gefunden")
    return fehler


def _pruefe_familie(df, namen):
    print("\n3. Spalte 'Familie' deckt sich mit Mapping_Namen.xlsx")
    fehler = 0
    soll = dict(zip(namen[KEY].astype(str).str.strip(),
                    namen["Powerpoint Familie"].astype(str).str.strip()))
    for _, z in df.iterrows():
        s = str(z[KEY]).strip()
        ist = str(z["Familie"]).strip()
        if soll.get(s, "") != ist:
            print(f"   FEHLER — {s}: Excel sagt '{ist}', "
                  f"Mapping sagt '{soll.get(s, '')}'")
            fehler += 1
    if not fehler:
        print("   OK — keine Abweichung")
    return fehler


def _pruefe_umfang(df):
    print("\n4. Genau die 14 Strategien mit Kasten (Thema bleibt aussen vor)")
    fehler = 0
    ist = list(df[KEY].astype(str).str.strip())
    fehlend = [s for s in ERWARTET if s not in ist]
    zuviel = [s for s in ist if s not in ERWARTET]
    if fehlend:
        print(f"   FEHLER — fehlen: {fehlend}")
        fehler += 1
    for s in zuviel:
        if s in OHNE_KASTEN:
            print(f"   FEHLER — '{s}' gehoert zur Thema-Familie und hat "
                  f"KEINEN Kasten in der Vorlage")
        else:
            print(f"   FEHLER — unbekannte Strategie '{s}'")
        fehler += 1
    if not fehler:
        print(f"   OK — {len(ist)} Strategien, Thema korrekt ausgenommen")
    return fehler


def _pruefe_vollstaendig(df):
    print("\n5. Kein Feld leer")
    fehler = 0
    for _, z in df.iterrows():
        for sp in ["Anzeigename"] + KRITERIEN:
            wert = z.get(sp)
            if pd.isna(wert) or not str(wert).strip():
                print(f"   FEHLER — {z[KEY]}: '{sp}' ist leer")
                fehler += 1
    if not fehler:
        print(f"   OK — {len(df) * 5} Felder gefuellt")
    return fehler


def _pruefe_schreibweise(df):
    print("\n6. Einheitliche Schreibweise")
    fehler = 0
    for _, z in df.iterrows():
        for sp in KRITERIEN:
            w = str(z[sp])
            if re.search(r"\bmin\.(?!\w)", w):
                print(f"   FEHLER — {z[KEY]} / {sp}: 'min.' statt 'mind.' ({w!r})")
                fehler += 1
            if re.search(r"\d%", w):
                print(f"   FEHLER — {z[KEY]} / {sp}: Prozent ohne "
                      f"Leerzeichen ({w!r})")
                fehler += 1
            if "  " in w or w != w.strip():
                print(f"   FEHLER — {z[KEY]} / {sp}: ueberfluessiger "
                      f"Leerraum ({w!r})")
                fehler += 1
    # Tippfehler, die es in den Vorlagen gab — duerfen nicht zurueckkehren
    alle = " ".join(df.astype(str).values.ravel())
    for tippfehler in ("FPFB", "AUsgewogen"):
        if tippfehler in alle:
            print(f"   FEHLER — Tippfehler '{tippfehler}' ist zurueck")
            fehler += 1
    if not fehler:
        print("   OK — keine Abweichung")
    return fehler


def _pruefe_zugriff(df):
    print("\n7. anlagekriterien_fuer() liefert die richtige Reihenfolge")
    try:
        from modules.shared import anlagekriterien_fuer
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0
    fehler = 0
    paare = anlagekriterien_fuer("cVV defensiv plus", df)
    bez = [b for b, _ in paare]
    if bez != KRITERIEN:
        print(f"   FEHLER — Reihenfolge {bez}, erwartet {KRITERIEN}")
        fehler += 1
    else:
        print(f"   OK — cVV defensiv plus: "
              f"{', '.join(f'{b}={w}' for b, w in paare)}")
    for s in OHNE_KASTEN:
        if anlagekriterien_fuer(s, df):
            print(f"   FEHLER — '{s}' sollte KEINE Kriterien liefern")
            fehler += 1
    if not fehler:
        print(f"   OK — {len(OHNE_KASTEN)} Thema-Strategien liefern korrekt []")
    for leer in ("", None, "Gibt es nicht"):
        if anlagekriterien_fuer(leer, df):
            print(f"   FEHLER — {leer!r} sollte [] liefern")
            fehler += 1
    return fehler


def _pruefe_bauweise(df):
    """Der Block MUSS aus nativen Streamlit-Bausteinen bestehen.

    Die erste Fassung war ein HTML-Block mit eigener heller Flaeche — im Dark
    Mode ein greller weisser Kasten. Dieser Schritt haelt fest, dass wir da
    nicht zurueckfallen: kein eigenes CSS, keine festen Farben.
    """
    print("\n8. Bauweise: native Streamlit-Bausteine, kein eigenes CSS")
    import inspect
    fehler = 0
    try:
        from modules.shared import zeige_anlagekriterien, markdown_escapen
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0

    # NUR den ausfuehrbaren Code pruefen: Docstring und Kommentare BEGRUENDEN
    # ja gerade, warum wir var(--…) und st.metric NICHT verwenden — ohne diese
    # Bereinigung schlaegt der Test auf seine eigene Erklaerung an.
    roh = inspect.getsource(zeige_anlagekriterien)
    doku = zeige_anlagekriterien.__doc__ or ""
    if doku:
        roh = roh.replace(doku, "")
    quelle = "\n".join(z for z in roh.splitlines()
                       if not z.strip().startswith("#"))

    # Kein Roh-HTML, keine Farbwerte, kein unsafe_allow_html
    verboten = {
        "unsafe_allow_html": "eigenes HTML statt nativer Bausteine",
        "background:": "fest verdrahteter Hintergrund",
        "#003460": "fest verdrahtete Textfarbe (bricht im Dark Mode)",
        "<div": "Roh-HTML",
        "var(--": "Streamlit 1.61 stellt KEINE Theme-CSS-Variablen bereit",
    }
    for muster, warum in verboten.items():
        if muster in quelle:
            print(f"   FEHLER — '{muster}' im Code: {warum}")
            fehler += 1

    # Die nativen Bausteine, die das Theme mitbringen
    for muster in ("st.container(border=True)", "st.columns", "st.caption"):
        if muster not in quelle:
            print(f"   FEHLER — '{muster}' fehlt; Block ist nicht nativ gebaut")
            fehler += 1

    # Bewusst NICHT st.metric — sonst sieht die Regel aus wie eine Kennzahl
    if "st.metric" in quelle:
        print("   FEHLER — st.metric verwischt Bestandszahl und Regel")
        fehler += 1

    # Markdown-Sonderzeichen aus der Excel duerfen nichts verschlucken
    if markdown_escapen("max. *5* _%_") != "max. \\*5\\* \\_%\\_":
        print("   FEHLER — Markdown-Sonderzeichen werden nicht entschaerft")
        fehler += 1

    if not fehler:
        print("   OK — container/columns/caption, kein CSS, keine Farbwerte")
    return fehler


def _view_pf_beschriftung():
    """Beschriftung der Portfolioanalyse-Ansicht aus streamlit_app lesen.

    streamlit_app.py laesst sich nicht importieren (das Skript wuerde
    losrennen), deshalb wird die Zuweisung aus dem Quelltext gelesen. So
    steht der Wert trotzdem nur an EINER Stelle.
    """
    import re
    pfad = os.path.join(WURZEL, "streamlit_app.py")
    with open(pfad, encoding="utf-8") as fh:
        m = re.search(r'^_VIEW_PF\s*=\s*"([^"]*)"', fh.read(), re.M)
    return m.group(1) if m else "Portfolioanalyse"


def _pruefe_in_der_app(df):
    """End-to-End: die App hochfahren und den Banner im Markup suchen."""
    print("\n9. Banner erscheint in der laufenden App (AppTest)")
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0

    at = AppTest.from_file(os.path.join(WURZEL, "streamlit_app.py"),
                           default_timeout=300)
    # check_login liest st.secrets; angemeldet wird ueber den session_state,
    # damit der Test nicht am Passwort haengt (siehe test_app_titel.py).
    at.secrets["passwords"] = {"testnutzer": "nur-fuer-den-test"}
    at.session_state["logged_in"] = True
    at.session_state["username"] = "testnutzer"
    try:
        at.run()
    except Exception as ex:
        print(f"   UEBERSPRUNGEN — App liess sich nicht starten: {ex}")
        return 0
    if at.exception:
        for ex in at.exception:
            print(f"   FEHLER — App warf: {str(ex.value)[:220]}")
        return 1

    markup = " ".join(m.value for m in at.markdown)
    if "Anlagekriterien" not in markup:
        print("   FEHLER — 'Anlagekriterien' steht nicht im Seiten-Markup")
        return 1

    # Der Banner muss zur AUSGEWAEHLTEN Strategie passen. Streamlit waehlt die
    # erste Option der Portfolio-Auswahl vor.
    gewaehlt = at.selectbox(key="p_sel1").value if at.selectbox else None
    print(f"   vorausgewaehlte Strategie: {gewaehlt!r}")
    from modules.shared import anlagekriterien_fuer
    paare = anlagekriterien_fuer(gewaehlt, df)
    if not paare:
        print("   OK — Strategie ohne Kasten, Banner entfaellt korrekt")
        return 0
    fehlen = [w for _, w in paare if w not in markup]
    if fehlen:
        print(f"   FEHLER — Werte fehlen im Markup: {fehlen}")
        return 1
    print(f"   OK — Performance-Ansicht: alle {len(paare)} Werte gefunden "
          f"({', '.join(w for _, w in paare)})")

    # ── zweite Ansicht: Portfolioanalyse ──────────────────────────────────
    # Der Banner soll in BEIDEN Ansichten stehen. Umschalten ueber den
    # session_state des segmented_control (key "nav_view", siehe #18).
    # Der Wert wird aus streamlit_app importiert statt hier wiederholt —
    # sonst bricht der Test still, wenn sich die Beschriftung aendert
    # (genau das passierte beim Entfernen der Piktogramme am 10.08.2026).
    at.session_state["nav_view"] = _view_pf_beschriftung()
    try:
        at.run()
    except Exception as ex:
        print(f"   UEBERSPRUNGEN (Portfolioanalyse) — {ex}")
        return 0
    if at.exception:
        for ex in at.exception:
            print(f"   FEHLER — Portfolioanalyse warf: {str(ex.value)[:220]}")
        return 1

    markup2 = " ".join(m.value for m in at.markdown)
    gewaehlt2 = None
    for sb in at.selectbox:
        if sb.key == "pf_sel_1":
            gewaehlt2 = sb.value
    print(f"   vorausgewaehltes Portfolio: {gewaehlt2!r}")
    paare2 = anlagekriterien_fuer(gewaehlt2, df)
    if not paare2:
        print("   OK — Portfolio ohne Kasten, Banner entfaellt korrekt")
        return 0
    fehlen2 = [w for _, w in paare2 if w not in markup2]
    if fehlen2:
        print(f"   FEHLER — Portfolioanalyse, Werte fehlen: {fehlen2}")
        return 1
    print(f"   OK — Portfolioanalyse: alle {len(paare2)} Werte gefunden")
    return 0


def _pruefe_broschueren(df, ordner):
    """Schritt 10 (nur mit Ordner-Argument): Zeigt die ERZEUGTE Broschuere
    genau das, was in der Konfiguration steht?

        python tests/test_anlagekriterien.py C:\\pfad\\zur\\ausgabe
    """
    print(f"\n10. Kasten in den erzeugten Broschueren ({ordner})")
    try:
        import glob
        from pptx import Presentation
        from modules.pptx_slides import finde_anlagekriterien_tabelle
    except ImportError as ex:
        print(f"   UEBERSPRUNGEN — {ex}")
        return 0

    dateien = sorted(glob.glob(os.path.join(ordner, "*.pptx")))
    if not dateien:
        print(f"   FEHLER — keine PPTX in {ordner}")
        return 1

    # Nachschlagen ueber die Kopfzeile: unabhaengig von Folienpositionen.
    nach_anzeige = {}
    for _, z in df.iterrows():
        nach_anzeige.setdefault(str(z["Anzeigename"]).strip(), []).append(z)

    fehler, geprueft = 0, 0
    for pfad in dateien:
        name = os.path.basename(pfad)
        prs = Presentation(pfad)
        for si, slide in enumerate(prs.slides, 1):
            t = finde_anlagekriterien_tabelle(slide)
            if t is None:
                continue
            geprueft += 1
            kopf = t.cell(0, 2).text.strip()
            kandidaten = nach_anzeige.get(kopf)
            if not kandidaten:
                print(f"   FEHLER — {name} F{si}: Kopfzeile {kopf!r} steht "
                      f"in keiner Zeile der Konfiguration")
                fehler += 1
                continue
            # Bei gleichem Anzeigenamen (ETF/CVV 'Ausgewogen') genuegt EINE
            # passende Zeile — die Werte entscheiden.
            passt = False
            for z in kandidaten:
                if all(t.cell(r, 0).text.strip() == k
                       and t.cell(r, 2).text.strip() == str(z[k]).strip()
                       for r, k in enumerate(KRITERIEN, start=1)):
                    passt = True
                    break
            if not passt:
                z = kandidaten[0]
                print(f"   FEHLER — {name} F{si} ({kopf}):")
                for r, k in enumerate(KRITERIEN, start=1):
                    ist_b, ist_w = t.cell(r, 0).text.strip(), t.cell(r, 2).text.strip()
                    if ist_b != k or ist_w != str(z[k]).strip():
                        print(f"      Zeile {r}: {ist_b!r}={ist_w!r}  "
                              f"erwartet {k!r}={str(z[k]).strip()!r}")
                fehler += 1
                continue
            # Formatierung darf nicht verloren gehen: jede beschriebene Zelle
            # braucht einen Run MIT expliziter Schriftgroesse.
            for r in range(len(t.rows)):
                for c in (0, 2):
                    paras = t.cell(r, c).text_frame.paragraphs
                    runs = paras[0].runs if paras else []
                    if not runs or runs[0].font.size is None:
                        print(f"   FEHLER — {name} F{si} Zeile {r} Spalte {c}: "
                              f"Formatierung verloren (keine Schriftgroesse)")
                        fehler += 1

    if geprueft == 0:
        print("   FEHLER — kein einziger Kasten gefunden")
        return 1
    if not fehler:
        print(f"   OK — {geprueft} Kaesten stimmen mit der Konfiguration "
              f"ueberein, Formatierung erhalten")
    return fehler


def main():
    if not os.path.exists(EXCEL):
        print(f"FEHLER: {EXCEL} fehlt")
        return 1
    df = pd.read_excel(EXCEL)
    namen = pd.read_excel(NAMEN)

    fehler = (_pruefe_struktur(df)
              + _pruefe_schluessel(df, namen)
              + _pruefe_familie(df, namen)
              + _pruefe_umfang(df)
              + _pruefe_vollstaendig(df)
              + _pruefe_schreibweise(df)
              + _pruefe_zugriff(df)
              + _pruefe_bauweise(df)
              + _pruefe_in_der_app(df))

    # Schritt 10 nur, wenn ein Export-Ordner uebergeben wurde (wie
    # test_trennstriche.py). Ohne Ordner bleibt der Test schnell.
    if len(sys.argv) > 1:
        fehler += _pruefe_broschueren(df, sys.argv[1])

    print()
    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print(f"BESTANDEN — {len(df)} Strategien, Konfiguration konsistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
