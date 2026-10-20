"""Distanzermittlung: Eingabe, Relationstabelle, Näherung Luftlinie mal I01.

Entspricht Input W bis AA und der Schnittstelle J2.2 ``distance_km``.
"""

from __future__ import annotations

from dataclasses import dataclass

from tk.excelfn import Cell, is_blank, is_number, round_half_away, to_number
from tk.geo import Place, PlaceDB, haversine_km
from tk.models import Assumptions

SOURCE_INPUT = "Eingabe"
SOURCE_RELATION = "Relationstabelle"
SOURCE_APPROX = "Näherung (Luftlinie x I01)"


@dataclass(slots=True)
class Distance:
    luftlinie_km: float | None  # W
    relation_km: float | None  # X
    naeherung_km: float | None  # Y
    distanz_km: float | None  # Z
    quelle: str | None  # AA


def relation_km(start: Place, ziel: Place, db: PlaceDB) -> float | None:
    """Input X: eigene Straßenentfernung aus PLZ_Orte, Schlüssel ``Start|Ziel`` in beiden Richtungen."""
    if not start.key or not ziel.key:
        return None
    for key in (f"{start.key}|{ziel.key}", f"{ziel.key}|{start.key}"):
        pos = db.match_relation(key)
        if pos is not None:
            value = db.rel_km[pos]
            if is_blank(value):
                return 0.0  # INDEX on an empty cell yields 0 in Excel
            return to_number(value) if is_number(value) else None
    return None


def distance_km(start: Place, ziel: Place, km_eingabe: Cell, db: PlaceDB, params: Assumptions) -> Distance:
    r"""J2.2 ``distance_km`` (Register K2.1, K2.2; Assumptions I2.3).

    .. math:: d = \begin{cases} d^{\text{Eingabe}} & \text{falls angegeben}\\
              d^{\text{Relation}} & \text{falls vorhanden}\\
              I_{01}\cdot d_L & \text{sonst}\end{cases}

    Die verwendete Distanz wird auf 6 Nachkommastellen gerundet (Input Z, ROUND(...;6)).
    Annahme: Straße = Luftlinie mal Straßenfaktor I01 (Näherung, kein Routing).
    Quelle: PLZ_Orte (GeoNames, CC BY 4.0), Relationstabelle der Nutzer.
    """
    luft = None
    if None not in (start.lat, start.lon, ziel.lat, ziel.lon):
        assert start.lat is not None and start.lon is not None
        assert ziel.lat is not None and ziel.lon is not None
        luft = haversine_km(start.lat, start.lon, ziel.lat, ziel.lon, params.i03_erdradius_km)
    rel = relation_km(start, ziel, db)
    approx = luft * params.i01_strassenfaktor if luft is not None else None
    used: float | None
    if not is_blank(km_eingabe):
        used = round_half_away(to_number(km_eingabe), 6) if is_number(km_eingabe) else None
    elif rel is not None:
        used = round_half_away(rel, 6)
    elif approx is not None:
        used = round_half_away(approx, 6)
    else:
        used = None
    if used is None:
        source = None
    elif not is_blank(km_eingabe):
        source = SOURCE_INPUT
    elif rel is not None:
        source = SOURCE_RELATION
    else:
        source = SOURCE_APPROX
    return Distance(luft, rel, approx, used, source)
