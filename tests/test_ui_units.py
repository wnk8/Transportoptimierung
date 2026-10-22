"""Anteile im Parameterpanel als Prozent: Hin- und Rückweg ohne Gleitkommareste."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from tk.ui.format import display_unit, from_display, to_display


def test_known_values() -> None:
    assert to_display(0.1, "Anteil") == 10
    assert to_display(0.2, "Anteil") == 20
    assert from_display(10, "Anteil") == 0.1
    assert display_unit("Anteil") == "%"
    assert to_display(500.0, "km") == 500.0
    assert display_unit("km") == "km"


@given(st.integers(min_value=0, max_value=10_000))
def test_round_trip_exact(n: int) -> None:
    value = n / 10_000
    assert from_display(to_display(value, "Anteil"), "Anteil") == value
