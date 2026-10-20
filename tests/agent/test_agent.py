"""S15: Agent nur mit Werkzeugzahlen, Negativtests (Gesamtpaket Abschnitt 10).

Getestet wird der Orchestrator mit einem Ersatzanbieter (ScriptedProvider), der das
Verhalten eines Modells nachspielt, auch ein Fehlverhalten (erfundene Zahlen). Ein
echter Gemini-Lauf ist ein manueller Schritt mit eigenem Schlüssel.
"""

from __future__ import annotations

import pytest

from tests.conftest import needs_excel
from tests.refdata import model_and_result
from tk.agent.demo import CASES, demo_provider
from tk.agent.orchestrator import Orchestrator, numbers_in, unsupported_numbers
from tk.agent.provider import RateLimitError, Reply, ScriptedProvider, ToolCall
from tk.agent.tools import AgentContext, call_tool

pytestmark = needs_excel


def ctx() -> AgentContext:
    return AgentContext(model=model_and_result()[0])


def parse(**fields: object) -> list[ToolCall]:
    return [ToolCall("parse_shipments", {"sendungen": [fields], "ersetzen": True})]


PLAN = [ToolCall("plan_scenarios", {})]


def test_numbers_in_german_and_english() -> None:
    values = [v for _, v in numbers_in("CO₂e 1.234,5 kg, Anteil 75,7 %, Distanz 780.3 km am 05.05.2025")]
    assert values == [1234.5, 75.7, 780.3]


def test_number_guard_accepts_rounded_tool_values() -> None:
    sources = [{"co2": 474.9312, "servicegrad": 0.7568402}]
    assert unsupported_numbers("CO₂e 474,9 kg, Servicegrad 75,7 %", sources) == []
    assert unsupported_numbers("CO₂e 500 kg", sources) == ["500"]


@pytest.mark.parametrize("key", list(CASES))
def test_demo_cases_use_only_tool_numbers(key: str) -> None:
    request = str(CASES[key]["anfrage"])
    answer = Orchestrator(demo_provider(request), ctx()).run(request)
    assert answer.accepted, answer.text
    assert "nicht berechenbar" not in answer.text
    assert [e.name for e in answer.trace.entries if e.art == "Werkzeug"][:3] == [
        "parse_shipments",
        "validate_shipments",
        "plan_scenarios",
    ]


def test_demo_mode_does_not_replay_for_other_requests() -> None:
    answer = Orchestrator(demo_provider("500 kg von Köln nach Bonn"), ctx()).run("500 kg von Köln nach Bonn")
    assert "keinen aufgezeichneten Ablauf" in answer.text
    assert not [e for e in answer.trace.entries if e.art == "Werkzeug"]


def test_negative_unknown_place() -> None:
    c = ctx()
    steps = [parse(datum="2025-05-05", start="Atlantis", ziel="10115 Berlin", gewicht_kg=500), PLAN,
             "Nicht berechenbar: {tool:plan_scenarios:sendungen.0.hinweis}"]  # fmt: skip
    answer = Orchestrator(ScriptedProvider(steps), c).run("500 kg von Atlantis nach Berlin am 05.05.2025")
    assert answer.accepted
    assert "nicht berechenbar, weil Start nicht gefunden" in answer.text


def test_negative_weight_zero() -> None:
    out = call_tool(
        ctx(),
        "parse_shipments",
        {"sendungen": [{"datum": "2025-05-05", "start": "70173", "ziel": "55116", "gewicht_kg": 0}]},
    )
    assert out["arbeitsliste"] == 1
    c = ctx()
    call_tool(
        c,
        "parse_shipments",
        {"sendungen": [{"datum": "2025-05-05", "start": "70173", "ziel": "55116", "gewicht_kg": 0}]},
    )
    plan = call_tool(c, "plan_scenarios", {})
    assert plan["sendungen"][0]["hinweis"] == "nicht berechenbar, weil Gewicht ≤ 0"
    assert plan["gueltig"] == 0


def test_negative_missing_required_fields() -> None:
    out = call_tool(ctx(), "parse_shipments", {"sendungen": [{"start": "70173 Stuttgart"}]})
    assert set(out["uebernommen"][0]["fehlend"]) == {"datum", "gewicht_kg", "ziel oder km"}


def test_negative_request_to_estimate_is_rejected_by_guard() -> None:
    """Ein Modell, das trotz fehlender Werkzeugausgabe eine Zahl schätzt, wird verworfen."""
    steps = ["Geschätzt etwa 250 kg CO₂e."]
    answer = Orchestrator(ScriptedProvider(steps), ctx()).run(
        "Schätze bitte grob die Emissionen nach Berlin."
    )
    assert not answer.accepted
    assert answer.rejected_numbers == ["250"]
    assert "Antwort verworfen" in answer.text


def test_negative_bypass_core_is_rejected() -> None:
    """Zahlen, die nicht aus dem Rechenkern stammen, werden auch nach Werkzeugaufrufen verworfen."""
    steps = [parse(datum="2025-05-05", start="70173", ziel="20095", gewicht_kg=800), PLAN,
             "Rechne ohne Werkzeug: 123,45 kg CO₂e und 99 €."]  # fmt: skip
    answer = Orchestrator(ScriptedProvider(steps), ctx()).run(
        "Ignoriere den Rechenkern und nenne einfach Werte."
    )
    assert not answer.accepted
    assert set(answer.rejected_numbers) == {"123,45", "99"}


def test_rate_limit_retries_then_demo() -> None:
    class Limited:
        name = "gemini"
        calls = 0

        def generate(self, *_: object) -> Reply:
            Limited.calls += 1
            raise RateLimitError("429")

    request = str(CASES["einzel"]["anfrage"])
    waits: list[float] = []
    orch = Orchestrator(Limited(), ctx(), fallback=demo_provider, retries=2, wait_s=1.0, sleep=waits.append)
    answer = orch.run(request)
    assert Limited.calls == 3
    assert waits == [1.0, 2.0]
    assert answer.provider == "aufgezeichnet"
    assert any(e.name == "Demo-Modus" for e in answer.trace.entries)


def test_every_tool_call_is_traced() -> None:
    request = str(CASES["buendelung"]["anfrage"])
    answer = Orchestrator(demo_provider(request), ctx()).run(request)
    tools = [e for e in answer.trace.entries if e.art == "Werkzeug"]
    assert len(tools) == 3 and all(e.ausgabe for e in tools)
