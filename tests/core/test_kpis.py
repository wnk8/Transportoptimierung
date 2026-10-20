"""S10, S11: key figures, sensitivity snapshot, checks and status (Gate G5)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import REFERENCE, needs_excel
from tests.refdata import model_and_result
from tk.explain import SPEC, explain
from tk.scenarios import calculate, parse_change, sensitivity_row, with_changes, workbook_shipments
from tk.workbook import load_workbook_data

pytestmark = needs_excel


def test_kpis_within_1e9(expected: dict[str, Any]) -> None:
    _, result = model_and_result()
    for name, want in expected["kennzahlen"].items():
        got = result.kpis[name].model_dump()
        for key, value in want.items():
            if value is None:
                assert got[key] is None, (name, key)
            else:
                assert got[key] == pytest.approx(value, rel=1e-9, abs=1e-12), (name, key)


def test_c04_and_status(expected: dict[str, Any]) -> None:
    _, result = model_and_result()
    assert result.c04 == pytest.approx(expected["abgeleitet"]["C04"], rel=1e-9)
    assert round(result.c04, 4) == 0.6465
    assert result.status == expected["cockpit"]["Status"] == "Plan zulässig"
    assert result.gesamtstatus == expected["gesamtstatus"] == "Alle Prüfungen bestanden"


def test_cockpit_counts(expected: dict[str, Any]) -> None:
    _, result = model_and_result()
    ok = result.valid_rows
    assert sum(r.fahrzeuge_n or 0 for r in ok) == expected["cockpit"]["Lkw-Fahrzeuge ungeplant"]
    assert sum(r.fahrzeuge_plan or 0 for r in ok) == expected["cockpit"]["Lkw-Fahrzeuge geplant"]


def test_checks_match_excel(expected: dict[str, Any]) -> None:
    _, result = model_and_result()
    assert len(result.checks) == 20
    for got, want in zip(result.checks, expected["pruefungen"], strict=True):
        assert got.status == want["status"], got.nr
        assert got.soll == pytest.approx(want["soll"], rel=1e-9, abs=1e-6), got.nr
        assert got.ist == pytest.approx(want["ist"], rel=1e-9, abs=1e-6), got.nr


def test_sensitivity_snapshot_within_1e8() -> None:
    model, _ = model_and_result()
    shipments = workbook_shipments(load_workbook_data())
    snapshot = json.loads((REFERENCE / "snapshot.json").read_text(encoding="utf-8"))
    assert len(snapshot["szenarien"]) == 14
    for scen in snapshot["szenarien"]:
        row = sensitivity_row(calculate(shipments, with_changes(model, parse_change(scen["parameter"]))))
        for key, value in row.items():
            assert value == pytest.approx(scen[key], abs=1e-8), (scen["szenario"], key)


@pytest.mark.parametrize("key", list(SPEC))
def test_explanations_complete(key: str, expected: dict[str, Any]) -> None:
    model, result = model_and_result()
    e = explain(key, model.params, result, expected)  # type: ignore[arg-type]
    assert e.formel and e.parameter is not None and e.datenquelle and e.systemgrenze
    assert "Gegen Excel v11 geprüft" in e.verifikation
    assert set(e.werte) == {"Ist", "M2", "M3"}
