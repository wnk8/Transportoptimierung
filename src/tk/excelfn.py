"""Excel semantics needed for an exact port of the workbook formulas.

The workbook relies on behaviour that differs from plain Python: text comparison in
MATCH and COUNTIFS ignores case and understands wildcards, TRIM also collapses inner
spaces, ROUND rounds half away from zero, numeric criteria built with ``"<"&x`` are
converted to text with 15 significant digits, and dates are serial numbers.
"""

from __future__ import annotations

import datetime as dt
import math
import re
from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_UP, Decimal

Cell = str | int | float | dt.date | dt.datetime | None
"""A raw input cell as it can appear in sheet Input, columns A to H."""

EXCEL_EPOCH = dt.date(1899, 12, 30)
_NUMBER_TEXT = re.compile(r"^\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?\s*$")
_WILDCARD = re.compile(r"[*?~]")


def is_blank(value: object) -> bool:
    """Excel ``cell=""``: empty cell or empty text."""
    return value is None or value == ""


def is_number(value: object) -> bool:
    """Excel ``ISNUMBER``: numbers and date values, not text and not booleans."""
    if isinstance(value, bool):
        return False
    return isinstance(value, int | float | dt.date)


def to_number(value: object) -> float:
    """Numeric value of a cell that passed :func:`is_number`."""
    if isinstance(value, dt.datetime):
        return date_to_serial(value.date()) + (value.hour * 3600 + value.minute * 60 + value.second) / 86400
    if isinstance(value, dt.date):
        return float(date_to_serial(value))
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    raise TypeError(f"not a number: {value!r}")


def n_value(value: object) -> float:
    """Excel ``N()``: number for numbers, 0 for everything else."""
    return to_number(value) if is_number(value) else 0.0


def trim(text: str) -> str:
    """Excel ``TRIM``: strip spaces at both ends and collapse inner runs of spaces."""
    return re.sub(" +", " ", text.strip(" "))


def general_text(value: object) -> str:
    """Excel ``value&""`` for numbers and text (number format General)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float):
        number = float(value)
        if number == int(number) and abs(number) < 1e15:
            return str(int(number))
        return f"{number:.15g}"
    return str(value)


def german_number_text(value: float) -> str:
    """Number to text as in the German locale (decimal comma, no grouping)."""
    return general_text(value).replace(".", ",")


def criterion_number(value: float) -> float:
    """Number after the text conversion in criteria like ``"<"&x`` (15 significant digits)."""
    return float(f"{value:.15g}")


def round_half_away(value: float, digits: int) -> float:
    """Excel ``ROUND``: decimal rounding, ties away from zero.

    Python ``round`` rounds ties to even and works on the binary value, so it is not used.
    The decimal representation (shortest repr) is rounded with ``ROUND_HALF_UP``,
    which rounds ties away from zero for both signs.
    """
    if not math.isfinite(value):
        return value
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(repr(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def roundup0(value: float) -> int:
    """Excel ``ROUNDUP(x;0)`` for non-negative values, on 15 significant digits."""
    approx = criterion_number(value)
    return math.ceil(approx) if approx >= 0 else -math.ceil(-approx)


def fold(text: str) -> str:
    """Case folding used for Excel text comparison."""
    return text.lower()


def _wildcard_regex(pattern: str) -> re.Pattern[str]:
    out = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "~" and i + 1 < len(pattern) and pattern[i + 1] in "*?~":
            out.append(re.escape(pattern[i + 1]))
            i += 2
            continue
        out.append(".*" if ch == "*" else "." if ch == "?" else re.escape(ch))
        i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE | re.DOTALL)


class TextIndex:
    """Excel ``MATCH(text; range; 0)`` on a fixed list (first hit, case-insensitive, wildcards)."""

    def __init__(self, values: Sequence[object]) -> None:
        self._values = list(values)
        self._first: dict[str, int] = {}
        for pos, value in enumerate(self._values):
            if isinstance(value, str) and value != "":
                self._first.setdefault(fold(value), pos)

    def match(self, text: str) -> int | None:
        """0-based position of the first match or ``None`` (Excel: #N/A)."""
        if text == "":
            return None
        if _WILDCARD.search(text):
            rx = _wildcard_regex(text)
            for pos, value in enumerate(self._values):
                if isinstance(value, str) and rx.match(value):
                    return pos
            return None
        return self._first.get(fold(text))


def first_positions(values: Iterable[str | None]) -> list[int | None]:
    """For each value the 0-based position of its first occurrence in the same list."""
    seen: dict[str, int] = {}
    out: list[int | None] = []
    for pos, value in enumerate(values):
        if value is None or value == "":
            out.append(None)
            continue
        out.append(seen.setdefault(fold(value), pos))
    return out


def date_to_serial(day: dt.date) -> int:
    """Excel date serial number (1900 date system)."""
    return (day - EXCEL_EPOCH).days


def serial_to_date(serial: float) -> dt.date:
    return EXCEL_EPOCH + dt.timedelta(days=int(serial))


def excel_value(text: str) -> float | None:
    """Excel ``VALUE`` for plain decimal text; ``None`` where Excel returns an error."""
    if not _NUMBER_TEXT.match(text):
        return None
    return float(text)


def _valid_date(year: float, month: float, day: float) -> int | None:
    if not (2000 <= year <= 2099):
        return None
    if month != int(month) or day != int(day):
        return None
    try:
        return date_to_serial(dt.date(int(year), int(month), int(day)))
    except ValueError:
        return None


def parse_date(value: Cell) -> int | None:
    """Input column J: normalised date as serial number, ``None`` for invalid.

    Accepts a date value (serial 36526 to 73050, years 2000 to 2099), text
    ``JJJJ-MM-TT`` or ``TT.MM.JJJJ`` with exactly 10 characters after TRIM.
    """
    if is_blank(value):
        return None
    if is_number(value):
        number = to_number(value)
        return math.floor(number) if 36526 <= number < 73051 else None
    text = trim(str(value))
    if len(text) != 10:
        return None
    german = text[2] == "."
    parts = (text[6:10], text[3:5], text[0:2]) if german else (text[0:4], text[5:7], text[8:10])
    numbers = [excel_value(p) for p in parts]
    if any(n is None for n in numbers):
        return None
    year, month, day = (float(n) for n in numbers if n is not None)
    return _valid_date(year, month, day)
