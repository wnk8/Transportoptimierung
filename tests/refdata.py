"""Load the reference CSV files written by scripts/make_reference.py and compare values."""

from __future__ import annotations

import csv
import datetime as dt
import math
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any

from tk.excelfn import date_to_serial
from tk.models import ROW_COLUMNS, Result, ShipmentRow
from tk.scenarios import Model, calculate, load_model, workbook_shipments
from tk.workbook import load_workbook_data

REFERENCE = Path(__file__).resolve().parents[1] / "data" / "reference"
ALL_COLUMNS = list(ROW_COLUMNS)


def read_block(name: str) -> list[dict[str, str]]:
    """Rows of a reference CSV as raw text, keyed by Excel column letter."""
    with (REFERENCE / name).open(encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter=";")
        header = next(reader)
        letters = ["excel_row"] + [h.split(" ", 1)[0] for h in header[1:]]
        return [dict(zip(letters, row, strict=True)) for row in reader]


@cache
def model_and_result() -> tuple[Model, Result]:
    data = load_workbook_data()
    model = load_model(data)
    return model, calculate(workbook_shipments(data), model)


def same(want: str, got: Any, rel: float = 1e-9) -> bool:
    """Compare a raw reference text with a Python value (relative tolerance for numbers)."""
    if got is None:
        return want == ""
    if isinstance(got, str):
        return want == got
    if want == "":
        return False
    try:
        number = float(want)
    except ValueError:
        return date_to_serial(dt.date.fromisoformat(want)) == got
    return number == got or math.isclose(number, float(got), rel_tol=rel, abs_tol=1e-9)


def compare_rows(result: Result, columns: list[str], rel: float = 1e-9) -> Iterator[str]:
    """Yield one message per differing cell of sheet Input."""
    by_row: dict[int, ShipmentRow] = {r.excel_row: r for r in result.rows}
    for want in read_block("sendungen_ref.csv"):
        excel_row = int(want["excel_row"])
        row = by_row[excel_row]
        for col in columns:
            got = getattr(row, ROW_COLUMNS[col])
            if not same(want[col], got, rel):
                yield f"Input!{col}{excel_row}: Excel {want[col]!r}, Python {got!r}"
