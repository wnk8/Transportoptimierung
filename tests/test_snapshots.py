"""Snapshots (syrupy) der neuen Kartenbausteine und Vergleichsrechnungen.

Zahlen auf 6 Nachkommastellen gerundet. Eine gewollte Änderung wird mit
``uv run pytest tests/test_snapshots.py --snapshot-update`` übernommen und im Review geprüft.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from syrupy.assertion import SnapshotAssertion

from tests.conftest import needs_excel
from tests.refdata import model_and_result
from tk.compare import custom_bundle, route_options
from tk.ui.map_view import diff_specs, line_specs, svg_network


def _round(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_round(v) for v in value]
    return value


def _stuttgart(result: Any) -> str:
    return next(r.start for r in result.routes if "Stuttgart" in r.start)


@needs_excel
def test_line_specs_snapshot(snapshot: SnapshotAssertion) -> None:
    _, result = model_and_result()
    start = _stuttgart(result)
    specs = {
        side: [(key, _round(opts)) for _, opts, _, key in line_specs(result, "M3", side, start=start)]
        for side in ("vorher", "nachher")
    }
    specs["diff"] = [(key, _round(opts)) for _, opts, _, key in diff_specs(result, "M3", start)]
    assert specs == snapshot


@needs_excel
def test_svg_network_snapshot(snapshot: SnapshotAssertion) -> None:
    _, result = model_and_result()
    assert svg_network(result, "M3", "nachher", start=_stuttgart(result)) == snapshot


@needs_excel
def test_route_options_snapshot(snapshot: SnapshotAssertion) -> None:
    model, result = model_and_result()
    opts = route_options(result, result.routes[0].key, model.params)
    assert _round([asdict(o) for o in opts.optionen]) == snapshot


@needs_excel
def test_custom_bundle_snapshot(snapshot: SnapshotAssertion) -> None:
    model, result = model_and_result()
    keys = [r.key for r in result.routes[:3]]
    out = {}
    for days in (0, 2):
        b = custom_bundle(result, keys, model.params, "M3", days)
        out[days] = _round(
            {
                "ist": asdict(b.ist),
                "automatisch": asdict(b.automatisch),
                "eigen": asdict(b.eigen),
                "gebuendelt": b.gebuendelt,
                "verschiebung_max": b.verschiebung_max,
                "verschiebung_mittel": b.verschiebung_mittel,
            }
        )
    assert out == snapshot
