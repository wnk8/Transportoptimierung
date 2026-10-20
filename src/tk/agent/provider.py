"""Schnittstelle LLMProvider und Gemini-Anbieter.

Der Anbieter liefert nur Text oder Werkzeugaufrufe. Er rechnet nie; alle Zahlen stammen
aus den Werkzeugen (``tk.agent.tools``). Der Schlüssel kommt ausschließlich aus der
Umgebungsvariable ``GEMINI_API_KEY`` (lokal aus ``.env``).

Geprüft am 20.10.2026 gegen google-genai 2.31 (Context7, Doku v2.30): manuelle
Funktionsaufrufe über ``FunctionDeclaration`` mit ``parameters_json_schema``,
``AutomaticFunctionCallingConfig(disable=True)`` und ``Part.from_function_response``.
Modellname über ``GEMINI_MODEL``; ohne Angabe der Alias ``gemini-flash-latest``.
Limits der kostenlosen Stufe stehen in Google AI Studio (Stand vor Nutzung prüfen).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

DEFAULT_MODEL = "gemini-flash-latest"


@dataclass(slots=True)
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass(slots=True)
class Message:
    """Nachricht im Verlauf: Nutzer, Modell (Text oder Werkzeugaufrufe) oder Werkzeugergebnis."""

    role: Literal["user", "model", "tool"]
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_name: str = ""
    tool_result: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(slots=True)
class Reply:
    text: str
    tool_calls: list[ToolCall]


class RateLimitError(RuntimeError):
    """Ratenlimit oder Kontingent des Anbieters erschöpft (HTTP 429)."""


class ProviderUnavailable(RuntimeError):
    """Kein Schlüssel, kein Netz oder Anbieterfehler."""


class LLMProvider(Protocol):
    name: str

    def generate(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> Reply: ...


class GeminiProvider:
    """Gemini über das SDK google-genai, manuelle Werkzeugschleife."""

    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise ProviderUnavailable("GEMINI_API_KEY ist nicht gesetzt (.env)")
        from google import genai

        self._client = genai.Client(api_key=key)
        self.model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL

    def _contents(self, messages: list[Message]) -> list[Any]:
        from google.genai import types

        contents: list[Any] = []
        for m in messages:
            if m.role == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m.text)]))
            elif m.role == "model":
                parts = [types.Part.from_text(text=m.text)] if m.text else []
                parts += [types.Part.from_function_call(name=c.name, args=c.args) for c in m.tool_calls]
                contents.append(types.Content(role="model", parts=parts))
            else:
                part = types.Part.from_function_response(name=m.tool_name, response=m.tool_result)
                contents.append(types.Content(role="user", parts=[part]))
        return contents

    def generate(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> Reply:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t.name, description=t.description, parameters_json_schema=t.parameters
                        )
                        for t in tools
                    ]
                )
            ],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=self._contents(messages), config=config
            )
        except errors.ClientError as exc:
            if exc.code == 429:
                raise RateLimitError(str(exc)) from exc
            raise ProviderUnavailable(str(exc)) from exc
        except (errors.ServerError, OSError) as exc:
            raise ProviderUnavailable(str(exc)) from exc
        calls = [ToolCall(c.name or "", dict(c.args or {})) for c in (response.function_calls or [])]
        text = "" if calls else (response.text or "")
        return Reply(text=text, tool_calls=calls)


class ScriptedProvider:
    """Ersatzanbieter für Tests und Demo: spielt vorbereitete Antworten der Reihe nach ab.

    Ein Schritt ist eine Liste von Werkzeugaufrufen oder ein Text. Ein Text darf den
    Platzhalter ``{tool:NAME:PFAD}`` enthalten, der aus dem letzten Ergebnis des Werkzeugs
    NAME gefüllt wird (Pfad mit Punkten, z. B. ``kennzahlen.M3.co2_fzgkm_kg``).
    """

    name = "aufgezeichnet"

    def __init__(self, steps: list[list[ToolCall] | str]) -> None:
        self.steps = list(steps)
        self.calls = 0

    def generate(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> Reply:
        if self.calls >= len(self.steps):
            return Reply(text="", tool_calls=[])
        step = self.steps[self.calls]
        self.calls += 1
        if isinstance(step, str):
            return Reply(text=_fill(step, messages), tool_calls=[])
        return Reply(text="", tool_calls=step)


def _fill(template: str, messages: list[Message]) -> str:
    import re

    from tk.ui import format as fmt

    def lookup(match: re.Match[str]) -> str:
        name, path, spec = match.group(1), match.group(2), match.group(3)
        for m in reversed(messages):
            if m.role == "tool" and m.tool_name == name:
                value: Any = m.tool_result
                try:
                    for key in path.split("."):
                        value = value[int(key)] if isinstance(value, list) else value[key]
                except (KeyError, IndexError, TypeError, ValueError):
                    return "nicht berechenbar"
                if isinstance(value, int | float) and not isinstance(value, bool) and spec:
                    return fmt.percent(value, 1, False) if spec == "%" else fmt.number(value, int(spec))
                return str(value)
        return "nicht berechenbar"

    return re.sub(r"\{tool:([a-z_]+):([^}:]+)(?::([0-9%]))?\}", lookup, template)
