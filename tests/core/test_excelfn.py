"""Excel semantics: rounding, text functions, lookups, dates."""

from __future__ import annotations

import datetime as dt

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tk.excelfn import (
    TextIndex,
    criterion_number,
    date_to_serial,
    general_text,
    parse_date,
    round_half_away,
    roundup0,
    trim,
)


@pytest.mark.parametrize(
    ("value", "digits", "expected"),
    [
        (2.5, 0, 3.0),
        (-2.5, 0, -3.0),
        (0.5, 0, 1.0),
        (1.0000005, 6, 1.000001),
        (-1.0000005, 6, -1.000001),
        (2.675, 2, 2.68),
        (185.04225504187022, 6, 185.042255),
        (0.0000004999, 6, 0.0),
    ],
)
def test_round_half_away(value: float, digits: int, expected: float) -> None:
    assert round_half_away(value, digits) == expected


def test_round_ties_differ_from_python_round() -> None:
    """Python rounds ties to even; Excel away from zero."""
    assert round(2.5) == 2
    assert round_half_away(2.5, 0) == 3


@given(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False))
def test_round_is_idempotent(x: float) -> None:
    once = round_half_away(x, 6)
    assert round_half_away(once, 6) == once
    assert abs(once - x) <= 0.5e-6 + 1e-9


def test_roundup_and_criterion() -> None:
    assert roundup0(2.0) == 2
    assert roundup0(2.0000000000000004) == 2
    assert roundup0(2.01) == 3
    assert criterion_number(0.1 + 0.2) == 0.3


def test_trim_and_general_text() -> None:
    assert trim("  70173   Stuttgart ") == "70173 Stuttgart"
    assert general_text(1.0) == "1"
    assert general_text(1.5) == "1.5"


def test_text_index_is_case_insensitive_with_wildcards() -> None:
    idx = TextIndex(["Köln", "Mainz", "Bad Kreuznach"])
    assert idx.match("köln") == 0
    assert idx.match("MAINZ") == 1
    assert idx.match("Bad*") == 2
    assert idx.match("Bonn") is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2025-01-01", dt.date(2025, 1, 1)),
        ("01.01.2025", dt.date(2025, 1, 1)),
        (" 2025-03-31 ", dt.date(2025, 3, 31)),
        (dt.date(2025, 6, 2), dt.date(2025, 6, 2)),
        (45658, dt.date(2025, 1, 1)),
        ("31.02.2025", None),
        ("2025-13-01", None),
        ("1999-12-31", None),
        ("2025-1-1", None),
        ("heute", None),
        (None, None),
    ],
)
def test_parse_date(value: object, expected: dt.date | None) -> None:
    got = parse_date(value)  # type: ignore[arg-type]
    assert got == (date_to_serial(expected) if expected else None)
