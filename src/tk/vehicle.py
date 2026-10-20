"""Fahrzeugwahl nach Rangregel, Fahrzeuganzahl, Auslastung, Rundung.

Entspricht Input AB bis AH und BH sowie der Schnittstelle J2.3 ``pick_vehicle``.
Voraussetzung der Rangregel: Fahrzeugtabelle aufsteigend nach Paletten und Nutzlast
(Prüfung 5).
"""

from __future__ import annotations

from dataclasses import dataclass

from tk.excelfn import criterion_number, roundup0
from tk.excelfn import round_half_away as round_half_away
from tk.models import Assumptions, Vehicle

__all__ = ["VehiclePick", "palettes", "pick_vehicle", "rank_for_load", "round_half_away"]


def palettes(gewicht_kg: float, paletten_eingabe: float | None, params: Assumptions) -> float:
    r"""Register K2.3 (Input AB): :math:`p = \text{Eingabe, sonst } \max(1, \lceil kg / A_{14} \rceil)`.

    Annahme: Standardwert A14 kg je Palette, nur wenn keine Palettenzahl eingegeben ist.
    """
    if paletten_eingabe is not None:
        return paletten_eingabe
    return float(max(1, roundup0(gewicht_kg / params.a14_kg_je_palette)))


def rank_for_load(paletten: float, gewicht_kg: float, vehicles: tuple[Vehicle, ...]) -> int:
    r"""Rangregel (Register K2.5, Input AE bei n = 1, Touren AD).

    .. math:: r = \min\left(R, \max\left(\#\{v: p_v < p\}, \#\{v: kg_v < kg\}\right) + 1\right)

    Die Kriterien ``"<"&x`` vergleichen mit der Zahl nach Textumwandlung (15 Stellen).
    """
    p = criterion_number(paletten)
    kg = criterion_number(gewicht_kg)
    below_pal = sum(1 for v in vehicles if v.paletten < p)
    below_kg = sum(1 for v in vehicles if v.nutzlast_kg < kg)
    return min(len(vehicles), max(below_pal, below_kg) + 1)


@dataclass(slots=True)
class VehiclePick:
    paletten: float  # AB
    fahrzeuge_n: int  # AD
    rang: int  # AE (1-based)
    fahrzeug: Vehicle  # AF
    auslastung: float  # AG
    lkw_km: float  # AH
    engpass: str  # BH


def pick_vehicle(
    gewicht_kg: float, paletten_eingabe: float | None, distanz_km: float, params: Assumptions
) -> VehiclePick:
    r"""J2.3 ``pick_vehicle`` (Register K2.3 bis K2.7).

    .. math::
        n = \max(1, \lceil p/p_{\max}\rceil, \lceil kg/kg_{\max}\rceil),\quad
        u = \max\left(\frac{kg}{n\,kg_r}, \frac{p}{n\,p_r}\right),\quad km = d\cdot n

    Bei ``n > 1`` wird das größte Fahrzeug gewählt, sonst das kleinste passende.
    Quelle: Fahrzeugtabelle Assumptions B1.
    """
    vehicles = params.vehicles
    p = palettes(gewicht_kg, paletten_eingabe, params)
    n = max(1, roundup0(p / params.max_paletten), roundup0(gewicht_kg / params.max_kg))
    rang = len(vehicles) if n > 1 else rank_for_load(p, gewicht_kg, vehicles)
    v = vehicles[rang - 1]
    kg_share = gewicht_kg / n / v.nutzlast_kg
    pal_share = p / n / v.paletten
    return VehiclePick(
        paletten=p,
        fahrzeuge_n=n,
        rang=rang,
        fahrzeug=v,
        auslastung=max(kg_share, pal_share),
        lkw_km=distanz_km * n,
        engpass="Gewicht" if kg_share >= pal_share else "Paletten",
    )
