"""Routenvergleich: Varianten je Relation und eigene Bündelung (Vergleichsrechnungen)."""

from __future__ import annotations

import math
from typing import Any

import pytest

from tests.conftest import needs_excel
from tests.refdata import model_and_result
from tk.compare import custom_bundle, relation_detail, relation_rows, route_options, vehicle_options
from tk.excelfn import to_number


@needs_excel
def test_route_options_ist_row_matches_relation_detail() -> None:
    model, result = model_and_result()
    key = result.routes[0].key
    opts = route_options(result, key, model.params)
    ist = relation_detail(result, key, "Ist").ist
    first = opts.optionen[0]
    assert first.art == "ist"
    assert (first.fahrten, first.lkw_km, first.co2_kg, first.kosten_eur) == (
        ist.fahrten,
        ist.lkw_km,
        ist.co2_kg,
        ist.kosten_eur,
    )
    assert [o.art for o in opts.optionen].count("lkw") == len(model.params.vehicles)


@needs_excel
def test_chosen_class_per_shipment_reproduces_ist() -> None:
    model, result = model_and_result()
    key = result.routes[0].key
    km = co2 = 0.0
    for row in relation_rows(result, key):
        assert row.paletten is not None and row.distanz_km is not None
        kg = to_number(row.shipment.gewicht_kg)
        chosen = next(
            o
            for o in vehicle_options(kg, row.paletten, row.distanz_km, model.params, result.c04)
            if o.gewaehlt
        )
        km += chosen.lkw_km
        co2 += chosen.co2_kg
    ist = relation_detail(result, key, "Ist").ist
    assert km == pytest.approx(ist.lkw_km, abs=1e-9)
    assert co2 == pytest.approx(ist.co2_kg, abs=1e-9)


@needs_excel
def test_rail_option_always_computed_with_reason() -> None:
    model, result = model_and_result()
    short = min(result.routes, key=lambda r: r.distanz_km)
    rail = next(o for o in route_options(result, short.key, model.params).optionen if o.art == "bahn")
    assert rail.co2_kg > 0 and rail.servicegrad == 0.0
    assert "Distanz bis A01" in rail.hinweis
    long = max(result.routes, key=lambda r: r.distanz_km)
    m3 = next(o for o in route_options(result, long.key, model.params).optionen if o.name == "Plan M3")
    assert m3.servicegrad < 1.0 and m3.zusatz_tage == model.params.a05_zusatz_tage


@needs_excel
def test_plan_rows_add_up_to_kpis() -> None:
    model, result = model_and_result()
    for scenario in ("M2", "M3"):
        total = math.fsum(
            next(
                o for o in route_options(result, r.key, model.params).optionen if o.name == f"Plan {scenario}"
            ).co2_kg
            for r in result.routes
        )
        assert total == pytest.approx(result.kpis[scenario].co2_fzgkm_kg, abs=1e-6)


@needs_excel
def test_route_param_roundtrip() -> None:
    from tk.ui.route_compare import keys_from_param, route_param

    _, result = model_and_result()
    keys = [result.routes[0].key, result.routes[5].key]
    value = route_param(keys, result)
    assert value.count(",") == 1 and "-" in value
    assert keys_from_param(value, result) == keys
    assert keys_from_param("00000-11111", result) == []


@needs_excel
def test_option_chart_is_percent_of_ist() -> None:
    from tk.ui.route_compare import options_chart

    model, result = model_and_result()
    opts = route_options(result, result.routes[0].key, model.params)
    chart = options_chart([("A", "#0072B2", opts)], "co2_kg")
    values = chart["series"][0]["data"]
    assert values[0] == 100.0
    assert len(values) == len(opts.optionen) == len(chart["yAxis"]["data"])


@needs_excel
def test_sankey_counts_every_shipment_once() -> None:
    from tk.ui.route_compare import sankey_chart

    _, result = model_and_result()
    keys = [r.key for r in result.routes]
    for scenario in ("Ist", "M2", "M3"):
        chart = sankey_chart(result, scenario, [("Alle", "#1F6F8B", keys)])
        links = chart["series"][0]["links"]
        assert sum(link["value"] for link in links) == result.n_valid
        if scenario == "M3":
            assert next(link["value"] for link in links if link["target"] == "Bahn") == 551


def test_route_colors_stay_when_others_are_removed() -> None:
    from tk.ui.route_compare import RouteCompare

    rc = object.__new__(RouteCompare)
    rc.keys, rc._colors = ["a", "b", "c"], {}
    before = rc.colors()
    rc.keys = ["b", "c"]
    after = rc.colors()
    assert after == {"b": before["b"], "c": before["c"]}
    rc.keys = ["b", "c", "d"]
    assert rc.colors()["d"] == before["a"]


def _start_keys(result: Any, index: int = 0) -> list[str]:
    start = result.routes[index].start
    return [r.key for r in result.routes if r.start == start]


@needs_excel
@pytest.mark.parametrize("scenario", ["M2", "M3"])
def test_custom_bundle_same_day_reproduces_excel(scenario: str) -> None:
    model, result = model_and_result()
    keys = _start_keys(result)
    bundle = custom_bundle(result, keys, model.params, scenario, 0)
    start = result.routes[0].start
    assert bundle.gebuendelt == sum(t.gebuendelt for t in result.tours if t.start == start)
    assert bundle.eigen.co2_kg == pytest.approx(bundle.automatisch.co2_kg, abs=1e-9)
    assert bundle.eigen.lkw_km == pytest.approx(bundle.automatisch.lkw_km, abs=1e-9)
    assert bundle.eigen.kosten_eur == pytest.approx(bundle.automatisch.kosten_eur, abs=1e-9)
    assert bundle.verschiebung_max == 0


@needs_excel
def test_custom_bundle_does_not_touch_result() -> None:
    model, result = model_and_result()
    before = [(r.gruppe, r.tour_nr, r.lkw_km_plan) for r in result.valid_rows]
    tours_before = len(result.tours)
    custom_bundle(result, _start_keys(result), model.params, "M2", 3)
    assert [(r.gruppe, r.tour_nr, r.lkw_km_plan) for r in result.valid_rows] == before
    assert len(result.tours) == tours_before


@needs_excel
def test_time_window_trades_km_for_days() -> None:
    model, result = model_and_result()
    keys = _start_keys(result)
    same_day = custom_bundle(result, keys, model.params, "M2", 0)
    window = custom_bundle(result, keys, model.params, "M2", 2)
    assert window.eigen.lkw_km <= same_day.eigen.lkw_km
    assert 0 < window.verschiebung_max <= 2
    assert window.sendungen == same_day.sendungen == sum(r.sendungen for r in result.routes if r.key in keys)


@needs_excel
def test_custom_bundle_subset_lists_starts() -> None:
    model, result = model_and_result()
    keys = [
        _start_keys(result, 0)[0],
        next(r.key for r in result.routes if r.start != result.routes[0].start),
    ]
    bundle = custom_bundle(result, keys, model.params, "M2", 0)
    assert len(bundle.startorte) == 2
    assert all(t.tour.start in bundle.startorte for t in bundle.touren)
