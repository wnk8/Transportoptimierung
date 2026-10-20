"""S4 to S10: every result column of sheet Input for all 2.266 shipments, relative deviation <= 1e-9."""

from __future__ import annotations

import pytest

from tests.conftest import needs_excel, needs_reference_csv
from tests.refdata import compare_rows, model_and_result

pytestmark = [needs_excel, needs_reference_csv]

GROUPS = {
    "S3 Eingabeprüfung und Datum (I, J)": ["I", "J"],
    "S4 Ortsauflösung (K bis V)": ["K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V"],
    "S4 Distanz (W bis AA)": ["W", "X", "Y", "Z", "AA"],
    "S7 Fahrzeugwahl (AB bis AH)": ["AB", "AC", "AD", "AE", "AF", "AG", "AH"],
    "S5 Emissionen (AI, AJ, AO)": ["AI", "AJ", "AO"],
    "S6 Kosten (AK, AL, AM)": ["AK", "AL", "AM"],
    "S9 Bahnprüfung (AM bis AO)": ["AM", "AN", "AO"],
    "S8 Tourbildung (AP bis AW)": ["AP", "AQ", "AR", "AS", "AT", "AU", "AV", "AW"],
    "S8 Plan (AX bis BD)": ["AX", "AY", "AZ", "BA", "BB", "BC", "BD"],
    "S10 Auswertungshilfen (BE bis BK)": ["BE", "BF", "BG", "BH", "BI", "BJ", "BK"],
}


@pytest.mark.parametrize("group", list(GROUPS))
def test_columns_match_excel(group: str) -> None:
    _, result = model_and_result()
    diffs = list(compare_rows(result, GROUPS[group]))
    assert not diffs, "\n".join(diffs[:20])


def test_row_count() -> None:
    _, result = model_and_result()
    assert result.n_valid == 2266
