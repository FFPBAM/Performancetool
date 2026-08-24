"""Aufloesung von Chart-Klicks auf fachliche Schluessel — ohne jedes Paket.

WOFUER DIESES MODUL DA IST

Ein `st.plotly_chart(..., on_select="rerun")` gibt zurueck, WO geklickt wurde.
Diese Rueckgabe in einen Namen zu uebersetzen, den die Anwendung kennt, ist
eine eigene kleine Aufgabe mit ueberraschend vielen Fallstricken — und seit
dem 24.08.2026 haben zwei Ansichten sie: der Strategievergleich (Klick auf
eine Gegenpartei) und die Portfolioanalyse (Klick auf ein Segment).

WARUM EIN EIGENES MODUL UND NICHT `shared.py`

`shared.py` zieht streamlit, pandas, numpy und PIL herein. Der ganze Wert
dieser Funktion steckt aber in ihren Grenzfaellen — veralteter Name, kaputte
Eingabe, fehlende Auswahl —, und die gehoeren in einen Pruefstein, der OHNE
JEDES PAKET laeuft (Hausregel: fehlende Pakete ueberspringen statt
scheitern). In `shared.py` waere er nur mit halber Firmenumgebung lauffaehig.

Dasselbe Muster hat schon `farben.py` (streamlit- und lxml-frei) und
`bestandsanalytik.py` (streamlit-frei) hervorgebracht: Was zwei Verbraucher
brauchen und kein Paket noetig hat, bekommt ein eigenes Modul. Deshalb hat
diese Datei bewusst KEINE Importe — bitte so lassen.
"""


def gewaehlter_balkenname(auswahl, namen):
    """Welchen Balken hat der Klick getroffen? Rueckfall: der erste.

    Args:
        auswahl: Rueckgabe von `st.plotly_chart(..., on_select="rerun")`,
            oder None. Alles andere wird als "keine Auswahl" gelesen und
            nicht als Fehler — ein kaputtes Ereignis darf die Seite nicht
            anhalten.
        namen: Die Namen der Balken IN ZEICHENREIHENFOLGE des Charts.

    Returns:
        Einen Eintrag aus `namen`, nie etwas anderes. Bei leerer Folge None.

    ES WIRD UEBER DEN NAMEN AUFGELOEST, NICHT UEBER DEN INDEX. Wechselt die
    Ebene, die Gattung oder das Portfolio, zeigt derselbe Balkenindex auf
    einen ANDEREN Gegenstand — die Aufstellung darunter gehoerte dann zu
    etwas, das niemand angeklickt hat. Dieselbe Klasse wie ein
    Auswahlfeld-Wert, der ins Leere laeuft (#53).

    Ein Name, den es nicht mehr gibt, faellt deshalb auf `namen[0]` zurueck.
    DAMIT GIBT ES AUCH KEINEN LEEREN ZUSTAND: Wer nie klickt, sieht trotzdem
    etwas.

    DIE ZUSAGE DER AUFRUFER: `namen` kommt absteigend sortiert, weshalb der
    Rueckfall der groesste Balken ist. Wer die Sortierung aendert, aendert
    damit auch, was ohne Klick dasteht — das ist hier festgehalten, weil es
    sonst still kippt.
    """
    liste = list(namen or [])
    if not liste:
        return None

    punkte = []
    try:
        punkte = list((auswahl or {}).get("selection", {}).get("points", []))
    except Exception:
        # Kein Dict, kein `get`, irgendetwas anderes: als "kein Klick" lesen.
        punkte = []

    kandidat = None
    if punkte:
        try:
            punkt = punkte[0]
            # `y` traegt bei waagerechten Balken die Kategorie; `customdata`
            # ist der Ersatzweg, falls Plotly die Achse anders zurueckmeldet.
            kandidat = punkt.get("y")
            if kandidat not in liste:
                daten = punkt.get("customdata")
                if isinstance(daten, str):
                    # Bei eindimensionalem customdata liefert Plotly nicht
                    # zuverlaessig eine Liste.
                    kandidat = daten
                elif isinstance(daten, (list, tuple)) and daten:
                    kandidat = daten[0]
        except Exception:
            kandidat = None

    try:
        if kandidat in liste:
            return kandidat
    except Exception:
        # Ein nicht vergleichbarer Wert ist kein Treffer, kein Absturz.
        pass
    return liste[0]
