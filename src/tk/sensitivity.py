r"""Globale Sensitivität (Morris-Screening) über die stetigen Parameter der Assumptions.

Ergänzt die Einzelparameter-Tabelle der Excel (Overview Abschnitt 6): Morris variiert alle
Parameter gleichzeitig entlang von Trajektorien und misst je Parameter den mittleren Betrag des
Elementareffekts

.. math:: \mu^*_i = \frac{1}{r}\sum_{j=1}^{r}
          \left| \frac{y(x^{(j)} + \Delta e_i) - y(x^{(j)})}{\Delta} \right|

sowie dessen Streuung :math:`\sigma_i` (Wechselwirkung oder Nichtlinearität). :math:`\Delta` ist
auf die Bandbreite normiert, deshalb sind :math:`\mu^*` verschiedener Parameter vergleichbar.
Bandbreiten und Begründungen: ``data/sensitivity_bounds.json``. Jeder Lauf ist eine vollständige
Rechnung des Kerns (:func:`tk.scenarios.calculate`). Vergleichsrechnung, nicht Teil der Excel.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tk.models import Shipment
from tk.scenarios import Model, calculate, with_changes

ROOT = Path(__file__).resolve().parents[2]
BOUNDS_FILE = ROOT / "data" / "sensitivity_bounds.json"
RESULT_FILE = ROOT / "data" / "reference" / "sensitivity_morris.json"

TARGETS: dict[str, str] = {
    "delta_co2_m3": "Δ CO₂e M3 (Fzg-km)",
    "delta_kosten_m3": "Δ Kosten M3",
    "servicegrad_m3": "Servicegrad M3",
}
"""Zielgrößen: relative Änderungen gegen Ist bzw. Anteil, damit alle dimensionslos sind."""


@dataclass(slots=True)
class Effect:
    parameter: str
    kennung: str
    name: str
    min: float
    max: float
    mu_star: float
    sigma: float
    mu_star_conf: float


@dataclass(slots=True)
class Screening:
    trajektorien: int
    stufen: int
    laeufe: int
    seed: int
    basis: dict[str, float]
    effekte: dict[str, list[Effect]]
    """Je Zielgröße die Parameter, absteigend nach :math:`\\mu^*`."""


def load_bounds(path: Path = BOUNDS_FILE) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["parameter"]
    return data


def targets(model: Model, shipments: Sequence[Shipment]) -> dict[str, float]:
    k = calculate(shipments, model).kpis["M3"]
    return {
        "delta_co2_m3": k.delta_co2_fzgkm or 0.0,
        "delta_kosten_m3": k.delta_kosten or 0.0,
        "servicegrad_m3": k.servicegrad,
    }


def morris(
    model: Model,
    shipments: Sequence[Shipment],
    trajectories: int = 20,
    levels: int = 4,
    seed: int = 1,
    bounds: dict[str, dict[str, Any]] | None = None,
) -> Screening:
    """Morris-Screening mit SALib (Stichprobe und Auswertung); jede Zeile eine Rechnung des Kerns."""
    import numpy as np
    from SALib.analyze import morris as analyze
    from SALib.sample import morris as sample

    bounds = bounds or load_bounds()
    names = list(bounds)
    problem = {
        "num_vars": len(names),
        "names": names,
        "bounds": [[float(bounds[n]["min"]), float(bounds[n]["max"])] for n in names],
    }
    x = sample.sample(problem, N=trajectories, num_levels=levels, seed=seed)
    ys: dict[str, list[float]] = {t: [] for t in TARGETS}
    for row in x:
        values = targets(
            with_changes(model, dict(zip(names, (float(v) for v in row), strict=True))), shipments
        )
        for t in TARGETS:
            ys[t].append(values[t])
    effects: dict[str, list[Effect]] = {}
    for t in TARGETS:
        res = analyze.analyze(problem, x, np.array(ys[t]), num_levels=levels, seed=seed)
        rows = [
            Effect(
                parameter=n,
                kennung=model.params.meta[n].id if n in model.params.meta else n,
                name=model.params.meta[n].name if n in model.params.meta else n,
                min=float(bounds[n]["min"]),
                max=float(bounds[n]["max"]),
                mu_star=float(res["mu_star"][i]),
                sigma=float(res["sigma"][i]),
                mu_star_conf=float(res["mu_star_conf"][i]),
            )
            for i, n in enumerate(names)
        ]
        effects[t] = sorted(rows, key=lambda e: -e.mu_star)
    return Screening(
        trajektorien=trajectories,
        stufen=levels,
        laeufe=len(x),
        seed=seed,
        basis=targets(model, shipments),
        effekte=effects,
    )


def save(screening: Screening, path: Path = RESULT_FILE) -> None:
    path.write_text(json.dumps(asdict(screening), ensure_ascii=False, indent=1), encoding="utf-8")


def load(path: Path = RESULT_FILE) -> Screening | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["effekte"] = {t: [Effect(**e) for e in rows] for t, rows in data["effekte"].items()}
    return Screening(**data)
