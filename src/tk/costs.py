"""Kostenmodell, Kalibrierfaktor C04, Einzel- und Bahnkosten.

Entspricht Input AK bis AM, Assumptions D52 (C04) und Touren AH.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from tk.models import Assumptions, Vehicle


def model_cost(lkw_km: float, vehicle: Vehicle) -> float:
    r"""Kosten Modell roh (Register K2.10, Input AK): :math:`K^{\text{Modell}} = km \cdot k_r`.

    Quelle: Kostensatz C2 (Standardwerte aus Original_Data, Eingabe änderbar).
    """
    return lkw_km * vehicle.kostensatz_eur_km


def calibration_factor(pairs: Iterable[tuple[float | None, float]]) -> float:
    r"""C04 (Assumptions!D52, Register K2.10).

    .. math:: C_{04} = \frac{\sum_{\text{OK},\,Fr_i>0} Fr_i}{\sum_{\text{OK},\,Fr_i>0} K_i^{\text{Modell}}}

    ``pairs`` sind (eingegebene Fracht, Modellkosten) der gültigen Zeilen. Ohne eingegebene
    Fracht gilt 1.
    """
    fracht = []
    modell = []
    for fr, km in pairs:
        if fr is not None and fr > 0:
            fracht.append(fr)
            modell.append(km)
    total = math.fsum(fracht)
    if total == 0:
        return 1.0
    return total / math.fsum(modell)


def single_cost(fracht: float | None, model: float, c04: float) -> float:
    """Kosten Einzel (Input AL): eingegebene Fracht, sonst Modell x C04."""
    return fracht if fracht is not None else model * c04


def rail_cost(kosten_einzel: float, params: Assumptions) -> float:
    r"""Bahnkosten (Input AM): :math:`K^{B} = K \cdot (1 + A_{07})`.

    Annahme: A07 = 0, ein Bahntarif liegt nicht vor (vorsichtige Setzung der Gruppe).
    """
    return kosten_einzel * (1 + params.a07_bahn_aufschlag)


def tour_cost(lkw_km: float, vehicle: Vehicle, c04: float) -> float:
    """Kosten Tour (Touren AH): km x Kostensatz x C04."""
    return lkw_km * vehicle.kostensatz_eur_km * c04
