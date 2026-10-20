"""Gate G2: generated reference matches section 2.5 and the delivered reference file."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.conftest import REFERENCE

GIVEN = REFERENCE / "given" / "referenz_v11_kennzahlen.json"


def test_section_2_5(expected: dict[str, Any]) -> None:
    k = expected["kennzahlen"]
    assert k["Ist"]["co2_fzgkm_kg"] == pytest.approx(306924.11, abs=0.006)
    assert k["M2"]["delta_co2_fzgkm"] == pytest.approx(-0.1689, abs=5e-5)
    assert k["M3"]["delta_co2_fzgkm"] == pytest.approx(-0.5331, abs=5e-5)
    assert k["M3"]["delta_kosten"] == pytest.approx(-0.2495, abs=5e-5)
    assert k["M3"]["delta_lkw_km"] == pytest.approx(-0.6769, abs=5e-5)
    assert k["M3"]["bahn_sendungen"] == 551
    assert k["M3"]["servicegrad"] == pytest.approx(0.7568, abs=5e-5)
    assert expected["touren_gesamt"] == 428
    assert expected["touren_gebuendelt"] == 318
    assert expected["abgeleitet"]["C04"] == pytest.approx(0.6465, abs=5e-5)
    assert expected["gesamtstatus"] == "Alle Prüfungen bestanden"


@pytest.mark.skipif(not GIVEN.exists(), reason="mitgelieferte Referenz nur lokal")
def test_matches_delivered_reference(expected: dict[str, Any]) -> None:
    given = json.loads(GIVEN.read_text(encoding="utf-8"))
    for scen, values in given["kennzahlen"].items():
        for key, want in values.items():
            got = expected["kennzahlen"][scen][key]
            if want is None:
                assert got in (None, "")
            else:
                assert got == pytest.approx(want, rel=1e-9, abs=1e-12), (scen, key)
