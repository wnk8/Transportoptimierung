"""S8: sheet Touren line by line; sheet Routen relation by relation (<= 1e-9)."""

from __future__ import annotations

from typing import Any

from tests.conftest import needs_excel, needs_reference_csv
from tests.refdata import model_and_result, read_block, same

pytestmark = [needs_excel, needs_reference_csv]

LINE_COLUMNS = {
    "A": "nr", "B": "sortkey", "C": "input_pos", "D": "sendung", "E": "gruppe", "F": "start",
    "G": "ziel", "H": "distanz_km", "I": "gewicht_kg", "J": "paletten", "K": "tkm",
    "L": "auslastung", "M": "co2_ist", "N": "kosten_ist", "O": "neue_gruppe", "P": "neue_tour",
    "Q": "ladung_kg", "R": "ladung_pal", "S": "tour_nr", "T": "neuer_stopp", "AM": "anteil",
    "AN": "fahrzeuge_plan", "AO": "fahrzeug_plan", "AP": "lkw_km_plan", "AQ": "co2_plan",
    "AR": "co2_plan_tkm", "AS": "kosten_plan", "AT": "fahrzeuge_aggregiert",
}  # fmt: skip
HEAD_COLUMNS = {
    "U": "sendungen", "V": "stopps", "W": "gewicht_kg", "X": "paletten", "Y": "max_distanz_km",
    "Z": "min_auslastung", "AA": "co2_einzel", "AB": "kosten_einzel", "AC": "tkm",
    "AD": "fahrzeug_rang", "AE": "lkw_km", "AF": "co2", "AG": "co2_tkm", "AH": "kosten",
    "AI": "gebuendelt",
}  # fmt: skip
ROUTE_COLUMNS = {
    "A": "nr", "B": "input_pos", "C": "start", "D": "ziel", "E": "start_lat", "F": "start_lon",
    "G": "ziel_lat", "H": "ziel_lon", "I": "sendungen", "J": "gewicht_t", "K": "distanz_km",
    "L": "distanz_quelle", "M": "tkm", "N": "co2_ist", "O": "co2_plan", "P": "delta_co2",
    "Q": "kosten_ist", "R": "kosten_plan", "S": "key", "T": "einsparung", "U": "rang",
}  # fmt: skip


def _diffs(ref: list[dict[str, str]], objs: list[Any], columns: dict[str, str], sheet: str) -> list[str]:
    out = []
    for want, obj in zip(ref, objs, strict=True):
        for col, attr in columns.items():
            got = getattr(obj, attr)
            if not same(want[col], got):
                out.append(f"{sheet}!{col}{want['excel_row']}: Excel {want[col]!r}, Python {got!r}")
    return out


def test_tour_lines_match_excel() -> None:
    _, result = model_and_result()
    ref = read_block("touren_ref.csv")
    assert len(ref) == len(result.tour_lines) == 1715
    diffs = _diffs(ref, result.tour_lines, LINE_COLUMNS, "Touren")
    assert not diffs, "\n".join(diffs[:20])


def test_tour_heads_match_excel() -> None:
    _, result = model_and_result()
    ref = read_block("touren_ref.csv")
    heads = [ref[t.erste_zeile - 1] for t in result.tours]
    diffs = _diffs(heads, result.tours, HEAD_COLUMNS, "Touren")
    assert not diffs, "\n".join(diffs[:20])


def test_tour_counts() -> None:
    """Gate G4: 428 Touren, davon 318 gebündelt, 551 Bahnsendungen."""
    _, result = model_and_result()
    assert len(result.tours) == 428
    assert sum(t.gebuendelt for t in result.tours) == 318
    assert sum(t.sendungen for t in result.tours if t.gebuendelt) == 1488
    assert sum(1 for r in result.rows if r.bahn == "Ja") == 551


def test_routes_match_excel() -> None:
    _, result = model_and_result()
    ref = read_block("routen_ref.csv")
    assert len(ref) == len(result.routes) == 45
    diffs = _diffs(ref, result.routes, ROUTE_COLUMNS, "Routen")
    assert not diffs, "\n".join(diffs[:20])
