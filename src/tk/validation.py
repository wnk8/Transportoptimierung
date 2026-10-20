"""Eingabeprüfung je Zeile (Input Spalte I) und Normierung der Zahlenfelder.

Die Reihenfolge der Prüfungen entspricht der verschachtelten WENN-Formel in Input!I14.
"""

from __future__ import annotations

from tk.excelfn import Cell, is_blank, is_number, n_value, to_number
from tk.geo import ART_AMBIGUOUS, ART_ENTRY_UNSURE, ART_NOT_FOUND, Place


def check_row(
    cells: tuple[Cell, ...],
    datum_serial: int | None,
    start: Place,
    ziel: Place,
    relation_km: float | None,
    distanz_km: float | None,
) -> str | None:
    """Input I: "OK", ein Hinweis oder ``None`` für eine leere Zeile."""
    datum, start_in, ziel_in, gewicht, _sid, km, pal, fracht = cells
    if all(is_blank(c) for c in cells):
        return None
    if is_blank(datum):
        return "Datum fehlt"
    if is_blank(start_in):
        return "Start fehlt"
    if is_blank(ziel_in) and is_blank(km):
        return "Ziel oder Entfernung fehlt"
    if is_blank(gewicht):
        return "Gewicht fehlt"
    if datum_serial is None:
        return "Datum ungültig"
    if not is_blank(km) and not is_number(km):
        return "Entfernung ist keine Zahl"
    if not is_number(gewicht):
        return "Gewicht ist keine Zahl"
    if not is_blank(km) and n_value(km) <= 0:
        return "Entfernung ≤ 0"
    if to_number(gewicht) <= 0:
        return "Gewicht ≤ 0"
    if not is_blank(pal) and not is_number(pal):
        return "Paletten keine Zahl"
    if not is_blank(pal) and n_value(pal) <= 0:
        return "Paletten ≤ 0"
    if not is_blank(fracht) and not is_number(fracht):
        return "Fracht keine Zahl"
    if not is_blank(fracht) and n_value(fracht) <= 0:
        return "Fracht ≤ 0"
    if not is_blank(km):
        return "OK"
    if start.art == ART_NOT_FOUND:
        return "Start nicht gefunden"
    if start.art == ART_AMBIGUOUS:
        return "Start mehrdeutig: PLZ nötig"
    if ziel.art == ART_NOT_FOUND:
        return "Ziel nicht gefunden"
    if ziel.art == ART_AMBIGUOUS:
        return "Ziel mehrdeutig: PLZ nötig"
    if relation_km is None and ART_ENTRY_UNSURE in (start.art, ziel.art):
        return "PLZ unsicher: km eingeben"
    if distanz_km is None:
        return "Entfernung nicht berechenbar"
    if distanz_km <= 0:
        return "Start gleich Ziel: km nötig"
    return "OK"
