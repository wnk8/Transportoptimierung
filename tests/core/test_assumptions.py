"""S3: parameters are read from sheet Assumptions, with unit and source, without defaults."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.conftest import needs_excel
from tk.models import Assumptions

pytestmark = needs_excel


@pytest.fixture(scope="module")
def params() -> Assumptions:
    from tests.refdata import model_and_result

    return model_and_result()[0].params


def test_no_defaults_in_code() -> None:
    with pytest.raises(ValidationError):
        Assumptions()  # type: ignore[call-arg]


def test_all_parameter_ids_present(params: Assumptions) -> None:
    ids = {m.id for m in params.meta.values()}
    for pid in [f"A{i:02d}" for i in range(1, 15)] + ["I01", "I02", "I03", "B3.5", "B3.6"]:
        assert pid in ids, pid
    for field, meta in params.meta.items():
        assert meta.zelle.startswith("Assumptions!"), field
        assert meta.unit or meta.id.startswith("B1"), field


def test_vehicle_table(params: Assumptions) -> None:
    assert [v.name for v in params.vehicles] == ["Sprinter (3,5t)", "Lkw 7,5t", "Lkw 12t", "Sattelzug 40t"]
    assert all(a.paletten < b.paletten for a, b in zip(params.vehicles, params.vehicles[1:], strict=False))


def test_derived_parameters_match_excel(params: Assumptions, expected: dict[str, Any]) -> None:
    derived = expected["abgeleitet"]
    assert params.c01_bahn_faktor == derived["C01"]
    assert params.c02_vnl_faktor == derived["C02"]
    assert params.c03_laufzeit_ok == derived["C03"]


def test_cockpit_parameters_match_excel(params: Assumptions, expected: dict[str, Any]) -> None:
    cockpit = expected["cockpit_parameter"]
    assert params.a01_bahn_grenze_km == cockpit["A01"]
    assert params.a02_vnl_km == cockpit["A02"]
    assert params.a05_zusatz_tage == cockpit["A05"]
    assert params.a08_kosten_tol == cockpit["A08"]
    assert params.a10_umweg == cockpit["A10"]
    assert params.c01_bahn_faktor == cockpit["C01"]
    assert params.c02_vnl_faktor == cockpit["C02"]
