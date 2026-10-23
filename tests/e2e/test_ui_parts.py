"""UI-Bausteine ohne Browser: Zahlenformat, Kartenlinien, Knoten-Kanten-Ansicht, App-Start."""

from __future__ import annotations

import math
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

from tests.conftest import ROOT, needs_excel
from tests.refdata import model_and_result
from tk.ui import format as fmt
from tk.ui.map_view import (
    DIMMED_OPACITY,
    arc,
    change_class,
    diff_specs,
    line_specs,
    nodes,
    relations,
    svg_network,
    view_for,
)
from tk.ui.theme import START_COLORS


def test_german_number_format() -> None:
    assert fmt.with_unit(306924.11, "kg") == "306.924 kg"
    assert fmt.number(841804.2, 2) == "841.804,20"
    assert fmt.percent(-0.5331202) == "−53,3 %"
    assert fmt.percent(0.1) == "+10,0 %"
    assert fmt.number(None) == "nicht berechenbar"


@needs_excel
def test_map_lines_encode_scenarios() -> None:
    _, result = model_and_result()
    ist = line_specs(result, "M3", "vorher")
    plan = line_specs(result, "M3", "nachher")
    assert len(ist) == 45
    dashed = [o for _, o, _, _ in plan if o.get("dashArray")]
    assert dashed, "Bahn muss gestrichelt sein"
    rels = relations(result, "M3")
    assert sum(r.n_bahn for r in rels) == 551
    assert sum(r.sendungen for r in rels) == 2266
    m2 = line_specs(result, "M2", "nachher")
    assert not [o for _, o, _, _ in m2 if o.get("dashArray")]


@needs_excel
def test_no_after_map_for_ist() -> None:
    _, result = model_and_result()
    assert line_specs(result, "Ist", "nachher") == []
    assert len(line_specs(result, "Ist", "vorher")) == 45


@needs_excel
@pytest.mark.parametrize("scenario", ["Ist", "M2", "M3"])
def test_relation_truck_km_add_up_to_kpi(scenario: str) -> None:
    _, result = model_and_result()
    rels = relations(result, scenario)
    assert math.fsum(r.lkw_km_plan for r in rels) == pytest.approx(result.kpis[scenario].lkw_km, abs=1e-6)
    assert math.fsum(r.lkw_km_ist for r in rels) == pytest.approx(result.kpis["Ist"].lkw_km, abs=1e-6)


@needs_excel
def test_before_and_after_share_one_width_scale() -> None:
    _, result = model_and_result()
    before = {key: o["weight"] for _, o, _, key in line_specs(result, "M2", "vorher")}
    plan = line_specs(result, "M2", "nachher")
    after = {key: o["weight"] for _, o, _, key in plan if not o.get("dashArray")}
    rels = {r.key: r for r in relations(result, "M2")}
    for key, weight in after.items():
        rel = rels[key]
        assert (weight <= before[key]) == (rel.lkw_km_plan <= rel.lkw_km_ist)


def test_arc_starts_and_ends_at_the_nodes() -> None:
    points = arc(48.8, 9.2, 50.0, 8.3, 0.12)
    assert points[0] == [48.8, 9.2]
    assert points[-1] == pytest.approx([50.0, 8.3])
    assert points[len(points) // 2] != pytest.approx([49.4, 8.75])


@needs_excel
def test_start_filter_colors_and_highlight() -> None:
    _, result = model_and_result()
    stuttgart = next(r.start for r in relations(result, "Ist") if "Stuttgart" in r.start)
    only = line_specs(result, "Ist", "vorher", start=stuttgart)
    assert len(only) == 15
    assert {o["color"] for _, o, _, _ in only} <= set(START_COLORS)
    assert len(nodes(result, stuttgart)) == 16
    key = only[0][3]
    marked = line_specs(result, "M3", "vorher", highlight={key: "#0072B2"})
    chosen = [o for _, o, _, k in marked if k == key]
    others = [o for _, o, _, k in marked if k != key]
    assert chosen[0]["color"] == "#0072B2" and chosen[0]["opacity"] == 0.9
    assert all(o["opacity"] == DIMMED_OPACITY for o in others)


def test_change_class() -> None:
    assert change_class(100.0, 80.0) == "weniger"
    assert change_class(100.0, 100.2) == "gleich"
    assert change_class(100.0, 120.0) == "mehr"
    assert change_class(0.0, 0.0) == "gleich"


@needs_excel
def test_diff_view_has_ghost_plan_and_rail() -> None:
    _, result = model_and_result()
    assert diff_specs(result, "Ist") == []
    specs = diff_specs(result, "M3")
    ghosts = [o for _, o, _, _ in specs if o["opacity"] == 0.22]
    assert len(ghosts) == 45
    rail = [o for _, o, _, _ in specs if o.get("dashArray") == "8 6"]
    assert len(rail) == sum(1 for r in relations(result, "M3") if r.n_bahn > 0)


@needs_excel
def test_svg_fallback_contains_nodes_and_edges() -> None:
    _, result = model_and_result()
    svg = svg_network(result, "M3", "nachher")
    assert svg.startswith("<svg") and svg.count("<polyline") >= 45 and "Hamburg" in svg


def test_view_for_germany() -> None:
    center, zoom = view_for([[47.9, 6.7], [53.6, 14.3]])
    assert 49 < center[0] < 52 and 5 <= zoom <= 7


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@needs_excel
@pytest.mark.skipif(os.environ.get("CI") == "true", reason="startet einen Server")
def test_app_starts_and_serves_pages() -> None:
    port = _free_port()
    # NiceGUI switches to its test mode when it sees pytest variables; start it as a normal server.
    base = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST")}
    env = {**base, "PYTHONPATH": "src", "TK_PORT": str(port), "TK_DEMO_MODE": "1"}
    proc = subprocess.Popen([sys.executable, "-m", "tk.ui.app"], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # fmt: skip
    try:
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as r:
                    body = r.read().decode()
                    break
            except OSError:
                time.sleep(0.5)
        else:
            pytest.fail("App startet nicht")
        assert "Transportkonzept" in body
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/vorschau", timeout=5) as r:
            assert r.status == 200
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/tk-fonts/Inter-Regular.woff2", timeout=5) as r:
            assert r.status == 200
    finally:
        proc.terminate()
        proc.wait(timeout=10)
