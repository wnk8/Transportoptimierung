"""Deutsches Zahlenformat (Gesamtpaket 7.3): Tausenderpunkt, Dezimalkomma, schmales Leerzeichen vor der Einheit."""

from __future__ import annotations

import math

NARROW = " "
MINUS = "−"


def number(value: float | int | None, decimals: int = 0) -> str:
    """``306924.11`` wird ``306.924`` (0 Stellen) bzw. ``306.924,11`` (2 Stellen)."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "nicht berechenbar"
    text = f"{abs(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return (MINUS if value < 0 and float(text.replace(".", "").replace(",", ".")) != 0 else "") + text


def with_unit(value: float | int | None, unit: str, decimals: int = 0) -> str:
    text = number(value, decimals)
    return text if text == "nicht berechenbar" else f"{text}{NARROW}{unit}"


def percent(value: float | None, decimals: int = 1, signed: bool = True) -> str:
    """Anteil als Prozent mit Vorzeichen, ``-0.5331`` wird ``−53,3 %``."""
    if value is None:
        return "nicht berechenbar"
    text = number(value * 100, decimals)
    if signed and value > 0 and not text.startswith(MINUS):
        text = "+" + text
    return f"{text}{NARROW}%"


def display_unit(unit: str) -> str:
    """Einheit im Eingabefeld: Anteile erscheinen als Prozent."""
    return "%" if unit == "Anteil" else unit


def to_display(value: float, unit: str) -> float:
    """Modellwert in Feldwert, ``0.1`` Anteil wird ``10`` %. Gerundet gegen Gleitkommareste."""
    return round(value * 100, 6) if unit == "Anteil" else value


def from_display(value: float, unit: str) -> float:
    """Feldwert in Modellwert, ``10`` % wird ``0.1``."""
    return round(value / 100, 10) if unit == "Anteil" else value
