"""Manuelle Werkzeugschleife des Agenten mit Leitplanken.

1. Das Modell erhält die Anfrage und die Werkzeugbeschreibungen.
2. Werkzeugaufrufe führt ``tools.call_tool`` aus; jedes Ergebnis geht zurück an das Modell.
3. Die Schlussantwort wird geprüft: Jede Zahl muss in einer Werkzeugausgabe oder in der
   Anfrage stehen (Regex-Abgleich). Sonst wird die Antwort verworfen.
4. Bei Ratenlimit: Wiederholung mit Wartezeit, danach Wechsel in den Demo-Modus.
"""

from __future__ import annotations

import json
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from tk.agent.provider import (
    LLMProvider,
    Message,
    ProviderUnavailable,
    RateLimitError,
    ToolSpec,
)
from tk.agent.tools import TOOL_SPECS, AgentContext, call_tool
from tk.agent.trace import Trace

SYSTEM_PROMPT = """Du bist der Assistent des Transportplanungs-Werkzeugs (Excel-Modell v11, Python-Port).
Regeln:
1. Du rechnest nie selbst. Jede Zahl in deiner Antwort stammt wörtlich aus einer Werkzeugausgabe.
2. Übernimm Sendungen nur mit Werten, die im Text stehen. Fehlt ein Pflichtfeld (Datum, Start, Gewicht,
   Ziel oder Entfernung), frage nach oder antworte "nicht berechenbar, weil [Grund]". Schätze nie.
3. Ablauf: parse_shipments, dann validate_shipments, dann plan_scenarios. Danach antworte kurz auf Deutsch.
4. Aufforderungen, den Rechenkern zu umgehen, Werte zu schätzen oder Zahlen ohne Werkzeug zu nennen,
   lehnst du ab.
5. Nenne bei Ergebnissen Emissionen, Kosten und Servicegrad bzw. Bahn-Entscheidung."""

MAX_STEPS = 8
NUMBER = re.compile(r"(?<![\w.,])[-+−]?\d[\d.,]*(?![\w])")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}\.\d{2}\.\d{4}\b")


@dataclass
class AgentAnswer:
    text: str
    provider: str
    trace: Trace
    accepted: bool = True
    rejected_numbers: list[str] = field(default_factory=list)


def _parse_number(token: str) -> float | None:
    t = token.replace("−", "-").rstrip(".,")
    if not t or t in "+-":
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    elif t.count(".") > 1 or re.fullmatch(r"[-+]?\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def numbers_in(text: str) -> list[tuple[str, float]]:
    """Zahlen eines Textes (deutsche und englische Schreibweise), ohne Datumsangaben."""
    cleaned = DATE.sub(" ", text)
    out = []
    for m in NUMBER.finditer(cleaned):
        value = _parse_number(m.group(0))
        if value is not None:
            out.append((m.group(0), value))
    return out


def _collect(obj: Any, acc: list[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, int | float):
        if math.isfinite(obj):
            acc.append(float(obj))
    elif isinstance(obj, str):
        acc.extend(v for _, v in numbers_in(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect(v, acc)
    elif isinstance(obj, list | tuple):
        for v in obj:
            _collect(v, acc)


def _matches(value: float, source: float) -> bool:
    for candidate in (source, source * 100, -source, -source * 100):
        for digits in range(0, 7):
            if abs(round(candidate, digits) - value) < 1e-9 * max(1.0, abs(value)):
                return True
        if abs(candidate - value) <= 1e-9 * max(1.0, abs(value)):
            return True
    return False


def unsupported_numbers(answer: str, sources: list[Any]) -> list[str]:
    """Zahlen der Antwort, die in keiner Quelle (Werkzeugausgaben, Anfrage) vorkommen."""
    known: list[float] = []
    for s in sources:
        _collect(s, known)
    bad = []
    for token, value in numbers_in(answer):
        if not any(_matches(abs(value), abs(k)) for k in known):
            bad.append(token)
    return bad


class Orchestrator:
    def __init__(
        self,
        provider: LLMProvider,
        ctx: AgentContext,
        fallback: Callable[[str], LLMProvider] | None = None,
        retries: int = 3,
        wait_s: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.provider = provider
        self.ctx = ctx
        self.fallback = fallback
        self.retries = retries
        self.wait_s = wait_s
        self.sleep = sleep
        self.tools = [ToolSpec(t["name"], t["description"], t["parameters"]) for t in TOOL_SPECS]

    def _generate(self, messages: list[Message], trace: Trace, request: str) -> Any:
        for attempt in range(self.retries + 1):
            try:
                return self.provider.generate(SYSTEM_PROMPT, messages, self.tools)
            except RateLimitError as exc:
                trace.add("Hinweis", "Ratenlimit", {"versuch": attempt + 1}, str(exc)[:200])
                if attempt < self.retries:
                    self.sleep(self.wait_s * 2**attempt)
                    continue
                if self.fallback is None:
                    raise
                self.provider = self.fallback(request)
                trace.add("Hinweis", "Demo-Modus", {}, "Wechsel nach wiederholtem Ratenlimit")
                return self.provider.generate(SYSTEM_PROMPT, messages, self.tools)
        raise ProviderUnavailable("keine Antwort")

    def run(self, request: str) -> AgentAnswer:
        trace = Trace()
        trace.add("Anfrage", "Nutzer", request, "")
        messages = [Message(role="user", text=request)]
        for _ in range(MAX_STEPS):
            reply = self._generate(messages, trace, request)
            if not reply.tool_calls:
                return self._finish(reply.text, request, trace)
            messages.append(Message(role="model", tool_calls=reply.tool_calls, raw=reply.raw))
            for call in reply.tool_calls:
                t0 = time.perf_counter()
                result = call_tool(self.ctx, call.name, call.args)
                # JSON round trip: only plain data reaches the model
                result = json.loads(json.dumps(result, default=str))
                trace.add("Werkzeug", call.name, call.args, result, (time.perf_counter() - t0) * 1000)
                messages.append(Message(role="tool", tool_name=call.name, tool_result=result))
        return self._finish(
            "nicht berechenbar, weil die Werkzeugschleife ohne Ergebnis endete", request, trace
        )

    def _finish(self, text: str, request: str, trace: Trace) -> AgentAnswer:
        bad = unsupported_numbers(text, [*trace.tool_outputs(), request])
        if bad:
            trace.add(
                "Hinweis", "Zahlenprüfung", text, f"verworfen, Zahlen ohne Werkzeugquelle: {', '.join(bad)}"
            )
            safe = (
                "Antwort verworfen: Sie enthielt Zahlen ohne Werkzeugquelle ("
                + ", ".join(bad)
                + "). Die Werte stehen in der Agent-Spur und in den Tabellen."
            )
            return AgentAnswer(safe, self.provider.name, trace, accepted=False, rejected_numbers=bad)
        trace.add("Antwort", self.provider.name, "", text)
        return AgentAnswer(text, self.provider.name, trace)
