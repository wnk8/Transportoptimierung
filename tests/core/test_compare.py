"""Vergleichsrechnungen der Karte gegen die Ergebnisse des Kerns (und damit gegen die Excel)."""

from __future__ import annotations

import math

import pytest

from tests.conftest import needs_excel
from tests.refdata import model_and_result
from tk.compare import relation_detail, road_vs_air, tour_comparison, vehicle_options
from tk.excelfn import to_number
from tk.routing import RoadRoute, RouteCache, relation_stops, road_distances, with_road_km
from tk.scenarios import calculate, workbook_shipments
from tk.workbook import load_workbook_data

pytestmark = needs_excel


def test_vehicle_options_choose_like_excel() -> None:
    model, result = model_and_result()
    for row in result.valid_rows:
        assert row.paletten is not None and row.distanz_km is not None
        opts = vehicle_options(
            to_number(row.shipment.gewicht_kg), row.paletten, row.distanz_km, model.params, result.c04
        )
        chosen = [o for o in opts if o.gewaehlt]
        assert len(chosen) == 1 and chosen[0].fahrzeug == row.fahrzeug
        assert chosen[0].anzahl == row.fahrzeuge_n
        assert chosen[0].co2_kg == pytest.approx(row.co2_ist_fzgkm, rel=1e-12)
        if row.shipment.fracht_eur is None:
            assert chosen[0].kosten_eur == pytest.approx(row.kosten_ist, rel=1e-12)


def test_tour_conditions_match_decision() -> None:
    model, result = model_and_result()
    for tour in result.tours:
        comp = tour_comparison(result, tour, model.params)
        assert all(c.erfuellt for c in comp.bedingungen) == bool(tour.gebuendelt)
        chosen = [o for o in comp.optionen if o.gewaehlt]
        assert len(chosen) == 1 and chosen[0].fahrzeug == tour.fahrzeug
        assert chosen[0].co2_kg == pytest.approx(tour.co2, rel=1e-12)
        assert chosen[0].kosten_eur == pytest.approx(tour.kosten, rel=1e-12)
        assert len(comp.sendungen) == tour.sendungen


@pytest.mark.parametrize("scenario", ["Ist", "M2", "M3"])
def test_relation_detail_sums_match_routes(scenario: str) -> None:
    _, result = model_and_result()
    totals = [0.0, 0.0, 0.0, 0.0]
    for route in result.routes:
        d = relation_detail(result, route.key, scenario)
        assert d.sendungen == route.sendungen
        assert d.ist.co2_kg == pytest.approx(route.co2_ist, rel=1e-12)
        assert d.ist.kosten_eur == pytest.approx(route.kosten_ist, rel=1e-12)
        if scenario == "M3":
            assert d.plan.co2_kg == pytest.approx(route.co2_plan, rel=1e-12)
            assert d.plan.kosten_eur == pytest.approx(route.kosten_plan, rel=1e-12)
        totals = [
            totals[0] + d.plan.co2_kg,
            totals[1] + d.plan.kosten_eur,
            totals[2] + d.plan.lkw_km,
            totals[3] + d.plan.fahrten,
        ]
    k = result.kpis[scenario]
    assert totals[0] == pytest.approx(k.co2_fzgkm_kg, rel=1e-9)
    assert totals[1] == pytest.approx(k.kosten_eur, rel=1e-9)
    assert totals[2] == pytest.approx(k.lkw_km, rel=1e-9)
    if scenario == "M3":
        assert totals[3] == pytest.approx(sum(r.fahrzeuge_plan or 0 for r in result.valid_rows), rel=1e-9)


def test_road_variant_uses_relation_table(tmp_path: object) -> None:
    model, result = model_and_result()
    cache = RouteCache(tmp_path / "r.json")  # type: ignore[operator]
    for stop in relation_stops(result):
        cache.put(
            RoadRoute(
                waypoints=[list(p) for p in stop.waypoints], distance_km=400.0, duration_h=5.0, geometry=[]
            )
        )
    assert len(road_distances(result, cache)) == 45
    road_model, added = with_road_km(model, result, cache)
    assert added == 45
    road = calculate(workbook_shipments(load_workbook_data()), road_model)
    assert {r.distanz_quelle for r in road.valid_rows} == {"Relationstabelle"}
    assert {r.distanz_km for r in road.valid_rows} == {400.0}
    # Standardrechnung bleibt unverändert (Excel-Abnahme)
    assert result.kpis["M3"].co2_fzgkm_kg == pytest.approx(143296.666562641, rel=1e-9)
    rows, total, median = road_vs_air(result, road_distances(result, cache), model.params)
    assert len(rows) == 45 and total is not None and median is not None
    assert all(math.isclose(r.naeherung_km, r.luftlinie_km * 1.22) for r in rows)
