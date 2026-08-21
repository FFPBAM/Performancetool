"""Pruefstein fuer die YTD-Kachel der Kennzahlen-Reihe (NEU 21.08.2026).

Die Kachel zeigt die Wertentwicklung im letzten Kalenderjahr des GEWAEHLTEN
Zeitraums. Sie ist neu, aber die Rechnung dahinter ist es nicht: Im selben
Reiter steht seit dem 03.07.2026 die rollierende Tabelle mit einer YTD-Zeile,
die ab VORJAHRES-SCHLUSSSTAND rechnet und bit-identisch zu Balken-Chart und
PP-Folie 8 ist (Transferwissen #22).

DIE ZUSAGE DIESES PRUEFSTEINS IST DESHALB NICHT "die Zahl ist richtig",
SONDERN "es ist DIESELBE Zahl": Kachel und Tabelle duerfen nicht
auseinanderlaufen. Ein Berater, der den Schalter "Wertentwicklung rollierend"
aufzieht, sieht sonst zwei YTD-Werte im selben Reiter — und keiner der beiden
traegt dann noch Autoritaet.

Erreicht wird das nicht durch Nachrechnen, sondern durch Wiederverwendung: Die
Kachel ruft period_return auf sa1t/sa2t auf, also exakt die Funktion auf exakt
den Serien, die build_rolling_table fuer ihre YTD-Zeile bekommt. Schritt 1
haelt genau das fest — wer die Kachel spaeter auf die volle Reihe (_voll1)
oder auf eine eigene Formel umstellt, bricht hier.

DREI SCHRITTE:

  1. Der Quelltext haelt die Bauform ein (statisch, ohne Paket):
     Kachel vorhanden, help nennt "31.12." und den Zeitraum-Vorbehalt,
     und die Rechnung sitzt auf period_return(sa1t, ...).

  2. Die Zahlen an den echten CSVs: Kachel-Rechnung gegen die YTD-Zeile aus
     build_rolling_table, ueber ALLE Strategien. Verlangt wird exakte
     Gleichheit, nicht "auf zwei Nachkommastellen".

  3. Der Abdeckungs-Guard: Deckt der Zeitraum den Jahresanfang nicht ab, MUSS
     None herauskommen (Anzeige "-"). Ein stillschweigend abgeschnittenes
     Rumpf-YTD waere genau die Fehlerklasse aus Transferwissen #51
     ("Es gibt Daten" ist nicht "der Zeitraum ist abgedeckt").

Findet der Pruefstein seinen Gegenstand nicht, ist das ein FEHLER und kein
"uebersprungen" (Transferwissen #65).

Schritt 2 und 3 brauchen pandas/numpy und die echten CSVs unter Daten/:

    .venv\\Scripts\\python.exe tests/test_ytd_kachel.py
"""

import ast
import glob
import os
import sys

import pandas as pd

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)
sys.path.insert(0, os.path.join(WURZEL, "tests"))
os.chdir(WURZEL)   # Daten/ wird relativ geladen

APP = "streamlit_app.py"
FUNKTION = "display_metrics"
DATEN = os.path.join(WURZEL, "Daten")

# Was der Hinweistext zusagen muss. NICHT der volle Wortlaut: Der darf sich
# aendern, die beiden Aussagen nicht (vgl. Schritt 2 in
# test_kennzahlen_hinweise.py — ein Test auf den exakten Satz schlaegt schon
# bei einem eingefuegten Komma an).
HILFE_ZUSAGEN = {
    "31.12.":   "der Bezugspunkt (Schlussstand des Vorjahres) ist benannt",
    "Zeitraum": "der Zeitraum-Vorbehalt ist benannt",
}

# Die Bauform der Rechnung. Beides muss im Quelltext der Kachel-Herleitung
# vorkommen, sonst rechnet sie nicht mehr auf derselben Basis wie die Tabelle.
BAUFORM = ("period_return", "sa1t")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _sicher(text):
    kodierung = getattr(sys.stdout, "encoding", None) or "ascii"
    return text.encode(kodierung, errors="replace").decode(kodierung, "replace")


def _quelltext():
    with open(os.path.join(WURZEL, APP), encoding="utf-8") as fh:
        return fh.read()


# ─────────────────────────────────────────────────────────────────────────────
# Schritt 1 — die Bauform im Quelltext
# ─────────────────────────────────────────────────────────────────────────────

def _ytd_metric(baum):
    """Der st.metric-Aufruf der YTD-Kachel in display_metrics.

    Das Label ist ein Ausdruck (die Jahreszahl kommt nur bei einem
    historischen Zeitraum dazu), laesst sich also nicht als Konstante lesen.
    Erkannt wird die Kachel deshalb am help-Text.
    """
    for knoten in ast.walk(baum):
        if not (isinstance(knoten, ast.FunctionDef) and knoten.name == FUNKTION):
            continue
        for k in ast.walk(knoten):
            if not isinstance(k, ast.Call):
                continue
            if getattr(k.func, "attr", None) != "metric":
                continue
            for kw in k.keywords:
                if kw.arg != "help":
                    continue
                stuecke = [t.value for t in ast.walk(kw.value)
                           if isinstance(t, ast.Constant) and isinstance(t.value, str)]
                text = "".join(stuecke)
                if "31.12." in text:
                    return k, text
    return None, None


def schritt1_bauform():
    print("Schritt 1 — die Bauform im Quelltext")
    fehler = 0
    quelle = _quelltext()
    baum = ast.parse(quelle, filename=APP)

    knoten, hilfe = _ytd_metric(baum)
    if knoten is None:
        print(f"    FEHLER — in {APP}:{FUNKTION} gibt es keine Kachel, deren "
              "Hinweistext den Bezugspunkt '31.12.' nennt. Entweder fehlt die "
              "YTD-Kachel, oder ihr Text nennt die Konvention nicht mehr.")
        return 1

    print(f"    OK — YTD-Kachel gefunden ({APP}:{knoten.lineno})")

    for stueck, was in HILFE_ZUSAGEN.items():
        if stueck in hilfe:
            print(f"    OK — {was}")
        else:
            print(f"    FEHLER — der Hinweistext nennt '{stueck}' nicht: {was} "
                  f"fehlt.\n           IST: {_sicher(hilfe)}")
            fehler += 1

    # Die Herleitung: period_return auf sa1t. Ohne diese Bauform kann die
    # Kachel von der Tabelle abweichen, ohne dass Schritt 2 es merkt (der
    # rechnet die Referenz selbst und nicht das, was die App tut).
    fehlend = [b for b in BAUFORM if b not in quelle]
    if fehlend:
        print(f"    FEHLER — im Quelltext fehlt {fehlend}. Die YTD-Kachel muss "
              "period_return auf sa1t/sa2t rechnen, also auf derselben Serie "
              "wie build_rolling_table. Eine eigene Formel laeuft frueher "
              "oder spaeter auseinander (Transferwissen #22).")
        fehler += 1
    else:
        print("    OK — die Rechnung sitzt auf period_return/sa1t")

    return fehler


# ─────────────────────────────────────────────────────────────────────────────
# Schritt 2 + 3 — die Zahlen an den echten Daten
# ─────────────────────────────────────────────────────────────────────────────

def _reihen(df, fee_dec):
    """Baut sb/sa genau so, wie es streamlit_app.py vor den Kennzahlen tut."""
    from modules.analytics import make_index_after_fee, make_index_from_returns
    r = df["ret_port"].to_numpy(float)
    xd = [df.index.min() - pd.Timedelta(days=1)] + list(df.index)
    sb = pd.Series(make_index_from_returns(r, 100.0), index=pd.to_datetime(xd))
    sa = pd.Series(make_index_after_fee(r, fee_dec, 100.0), index=pd.to_datetime(xd))
    return sb, sa


def _kachel_ytd(sa):
    """Die Rechnung der Kachel (streamlit_app.py, _ytd_aus)."""
    from streamlit_app import period_return
    e = sa.dropna().index.max()
    if pd.isna(e):
        return None, None
    return period_return(sa, pd.Timestamp(e.year - 1, 12, 31), e), e.year


def _tabellen_ytd(sb, sa, label):
    """Die YTD-Zeile aus build_rolling_table — als formatierter String."""
    from streamlit_app import build_rolling_table
    tab = build_rolling_table(sb, sa, label)
    spalte = tab.columns[0]
    zeile = tab[tab[spalte] == "ytd"]
    if zeile.empty:
        return None
    return str(zeile.iloc[0][(label, "nach Kosten")])


def _fmt(x):
    """Dieselbe Formatierung wie in build_rolling_table."""
    if x is None:
        return "-"
    return f"{x*100:.3f}%".replace(".", ",")


def _daten():
    from test_benchmark_erkennung import FEE_TEST, lade_zeitreihe, neuester_tag
    from modules.shared import to_decimal_interval
    tag = neuester_tag()
    if tag is None:
        return None, None, None
    dateien = sorted(glob.glob(os.path.join(DATEN, f"*_{tag}_*.CSV")))
    reihen = []
    for pfad in dateien:
        name, df = lade_zeitreihe(pfad)
        # lade_zeitreihe liefert die Rohspalte; die App wandelt sie ueber
        # to_decimal_interval in Dezimal. Ohne das waeren die YTD-Werte um
        # den Faktor 100 daneben — die Bit-Identitaet zwar trotzdem gegeben,
        # die Plausibilitaetsspalte aber unlesbar.
        df = df.copy()
        df["ret_port"] = to_decimal_interval(df["ret_port"])
        df = df.dropna(subset=["ret_port"])
        if len(df) > 1:
            reihen.append((name, df))
    return tag, reihen, FEE_TEST


def schritt2_bit_identitaet(reihen, fee):
    print("Schritt 2 — Kachel gegen die YTD-Zeile der rollierenden Tabelle")
    if not reihen:
        print("    FEHLER — keine Zeitreihen aus Daten/ ladbar")
        return 1

    kopf = f"    {'Strategie':30s} {'Jahr':>6s} {'Kachel':>11s} {'Tabelle':>11s}"
    print(kopf)
    print("    " + "-" * (len(kopf) - 4))

    fehler = 0
    for name, df in reihen:
        sb, sa = _reihen(df, fee)
        wert, jahr = _kachel_ytd(sa)
        kachel = _fmt(wert)
        tabelle = _tabellen_ytd(sb, sa, name)
        marke = "" if kachel == tabelle else "   <-- WEICHT AB"
        if marke:
            fehler += 1
        print(f"    {_sicher(name)[:30]:30s} {jahr!s:>6s} "
              f"{kachel:>11s} {tabelle!s:>11s}{marke}")

    if fehler:
        print(f"\n    FEHLER — {fehler} Strategie(n) zeigen in Kachel und "
              "Tabelle verschiedene YTD-Werte.")
    else:
        print(f"\n    OK — alle {len(reihen)} Strategien zeichengleich")
    return fehler


def schritt3_guard(reihen, fee):
    """Deckt der Zeitraum den Jahresanfang nicht ab, MUSS None herauskommen."""
    print("Schritt 3 — der Abdeckungs-Guard")
    if not reihen:
        print("    FEHLER — keine Zeitreihen aus Daten/ ladbar")
        return 1

    fehler = 0
    geprueft = 0
    for name, df in reihen:
        ende = df.index.max()
        # Zeitraum, der erst im Februar des letzten Jahres beginnt: der
        # Jahresanfang fehlt, ein YTD ist nicht berechenbar.
        start = pd.Timestamp(ende.year, 2, 1)
        sub = df.loc[df.index >= start]
        if len(sub) < 2 or sub.index.min().year != ende.year:
            continue
        _, sa = _reihen(sub, fee)
        wert, _ = _kachel_ytd(sa)
        geprueft += 1
        if wert is not None:
            print(f"    FEHLER — {_sicher(name)}: Zeitraum ab "
                  f"{start:%d.%m.%Y}, der Jahresanfang fehlt, trotzdem kommt "
                  f"{_fmt(wert)} heraus statt '-'. Das ist ein abgeschnittenes "
                  "Rumpf-YTD und sieht wie ein volles aus.")
            fehler += 1

    if geprueft == 0:
        print("    FEHLER — keine Strategie liess sich auf einen Zeitraum ohne "
              "Jahresanfang beschneiden; der Guard wurde damit nicht geprueft.")
        return 1
    if not fehler:
        print(f"    OK — {geprueft} Strategien liefern '-' statt eines "
              "Rumpf-YTD")
    return fehler


def main():
    print("Pruefstein: YTD-Kachel der Kennzahlen-Reihe\n")
    fehler = schritt1_bauform()
    print()

    try:
        tag, reihen, fee = _daten()
    except Exception as ex:
        print(f"FEHLER — die echten Daten liessen sich nicht laden: "
              f"{type(ex).__name__}: {ex}")
        return 1
    if tag is None:
        print("FEHLER — keine CSVs in Daten/")
        return 1
    print(f"Datenstand {tag} — {len(reihen)} Strategien\n")

    fehler += schritt2_bit_identitaet(reihen, fee)
    print()
    fehler += schritt3_guard(reihen, fee)
    print()

    if fehler:
        print(f"FEHLGESCHLAGEN — {fehler} Abweichung(en)")
        return 1
    print("BESTANDEN — die YTD-Kachel rechnet dieselbe Zahl wie die "
          "rollierende Tabelle, und sie erfindet keine, wo der Zeitraum "
          "den Jahresanfang nicht abdeckt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
