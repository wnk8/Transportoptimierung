"""Shared fixtures and paths for the test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXCEL = ROOT / "data" / "excel" / "Thema1_Transportkonzept_v11_Beispieldaten.xlsx"
REFERENCE = ROOT / "data" / "reference"

needs_excel = pytest.mark.skipif(not EXCEL.exists(), reason="Excel-Referenz nur lokal vorhanden")
needs_reference_csv = pytest.mark.skipif(
    not (REFERENCE / "sendungen_ref.csv").exists(), reason="Referenz-CSV nur lokal (make reference)"
)


@pytest.fixture(scope="session")
def expected() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((REFERENCE / "expected.json").read_text(encoding="utf-8"))
    return data
