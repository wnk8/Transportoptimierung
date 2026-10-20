"""Properties of the core (hypothesis): capacity, assignment, allocation, monotonicity."""

from __future__ import annotations

import math

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.conftest import needs_excel
from tests.refdata import model_and_result
from tk.models import Shipment
from tk.scenarios import calculate
from tk.vehicle import pick_vehicle, rank_for_load

pytestmark = needs_excel

STARTS = ["70173 Stuttgart", "68159 Mannheim", "76131 Karlsruhe"]
ZIELE = ["55116 Mainz", "30159 Hannover", "50667 Köln", "01067 Dresden", "80331 München", "20095 Hamburg"]

shipment = st.builds(
    Shipment,
    datum=st.sampled_from(["2025-03-03", "2025-03-04"]),
    start=st.sampled_from(STARTS),
    ziel=st.sampled_from(ZIELE),
    gewicht_kg=st.floats(min_value=1, max_value=30000).map(lambda x: round(x, 1)),
    paletten=st.one_of(st.none(), st.integers(min_value=1, max_value=40)),
    fracht_eur=st.one_of(st.none(), st.floats(min_value=20, max_value=3000).map(lambda x: round(x, 2))),
)


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(shipment, min_size=1, max_size=60))
def test_tours_respect_capacity_and_assignment(ships: list[Shipment]) -> None:
    model, _ = model_and_result()
    result = calculate(ships, model)
    p = model.params
    for tour in result.tours:
        assert tour.gewicht_kg <= p.max_kg
        assert tour.paletten <= p.max_paletten
    in_tours = {line.input_pos for line in result.tour_lines}
    for pos, row in enumerate(result.rows, start=1):
        if not row.ok:
            continue
        on_rail = row.bahn == "Ja"
        in_tour = pos in in_tours
        single = not on_rail and row.fahrzeuge_n != 1
        assert on_rail + in_tour + single == 1, pos
    for tour in result.tours:
        if tour.gebuendelt:
            members = [line for line in result.tour_lines if line.tour_nr == tour.tour_nr]
            assert math.isclose(math.fsum(m.co2_plan for m in members), tour.co2, rel_tol=1e-12)
            assert math.isclose(math.fsum(m.lkw_km_plan for m in members), tour.lkw_km, rel_tol=1e-12)
            assert math.isclose(math.fsum(m.kosten_plan for m in members), tour.kosten, rel_tol=1e-12)
    ok = result.valid_rows
    assert sum(r.fahrzeuge_plan or 0 for r in ok) <= sum(r.fahrzeuge_n or 0 for r in ok)
    assert result.checks[1].status == "OK" and result.checks[2].status == "OK"


@given(
    st.floats(min_value=1, max_value=24000),
    st.floats(min_value=1, max_value=24000),
    st.floats(min_value=1, max_value=34),
)
def test_vehicle_rank_is_monotone_in_weight(kg_a: float, kg_b: float, pal: float) -> None:
    model, _ = model_and_result()
    lo, hi = sorted((kg_a, kg_b))
    vehicles = model.params.vehicles
    assert rank_for_load(pal, lo, vehicles) <= rank_for_load(pal, hi, vehicles)


@given(st.floats(min_value=0.1, max_value=200000), st.floats(min_value=1, max_value=1000))
def test_vehicle_count_covers_load(kg: float, km: float) -> None:
    model, _ = model_and_result()
    pick = pick_vehicle(kg, None, km, model.params)
    assert pick.fahrzeuge_n * pick.fahrzeug.nutzlast_kg >= kg - 1e-6
    assert pick.auslastung <= 1 + 1e-9
