"""Morris-Screening: Struktur, Plausibilität, Speichern und Laden."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import needs_excel
from tk.scenarios import load_model, workbook_shipments
from tk.sensitivity import TARGETS, load, load_bounds, morris, save
from tk.workbook import load_workbook_data


@pytest.fixture(scope="module")
def screening():  # type: ignore[no-untyped-def]
    data = load_workbook_data()
    return morris(load_model(data), workbook_shipments(data), trajectories=2)


@needs_excel
def test_bounds_contain_the_excel_value() -> None:
    data = load_workbook_data()
    params = load_model(data).params
    for name, b in load_bounds().items():
        assert b["min"] <= getattr(params, name) <= b["max"], name
        assert b["begruendung"]


@needs_excel
def test_screening_covers_all_parameters_and_targets(screening) -> None:  # type: ignore[no-untyped-def]
    names = set(load_bounds())
    assert set(screening.effekte) == set(TARGETS)
    for rows in screening.effekte.values():
        assert {e.parameter for e in rows} == names
        assert all(e.mu_star >= 0 for e in rows)
        assert [e.mu_star for e in rows] == sorted((e.mu_star for e in rows), reverse=True)
    assert screening.laeufe == 2 * (len(names) + 1)


@needs_excel
def test_diesel_factor_cannot_move_rail_share(screening) -> None:  # type: ignore[no-untyped-def]
    service = {e.parameter: e for e in screening.effekte["servicegrad_m3"]}
    assert service["a12_diesel_kg_co2_je_kg"].mu_star == 0.0
    assert service["a01_bahn_grenze_km"].mu_star > 0.0


@needs_excel
def test_save_and_load_roundtrip(screening, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "morris.json"
    save(screening, path)
    again = load(path)
    assert again is not None and again.effekte["delta_co2_m3"][0] == screening.effekte["delta_co2_m3"][0]
    assert load(tmp_path / "fehlt.json") is None
