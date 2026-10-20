"""Bahnprüfung M3.

Entspricht Input AM bis AO und der Schnittstelle J2.4 ``rail_check``.
"""

from __future__ import annotations

from tk.models import Assumptions


def rail_check(distanz_km: float, kosten_einzel: float, kosten_bahn: float, params: Assumptions) -> bool:
    r"""J2.4 ``rail_check`` (Register K2.11, Input AN).

    .. math:: \text{Bahn} \Leftrightarrow d > A_{01} \wedge A_{05} \le A_{06}
              \wedge K^{B} \le K\,(1 + A_{08})

    Annahmen: A01 Mindestdistanz, Laufzeitregel C03, Kostenregel A08 (Setzungen der Gruppe).
    Die Schwelle A09 gehört zur Bündelung (Touren AI), nicht zur Bahnprüfung.
    """
    return (
        distanz_km > params.a01_bahn_grenze_km
        and params.c03_laufzeit_ok == 1
        and kosten_bahn <= kosten_einzel * (1 + params.a08_kosten_tol)
    )
