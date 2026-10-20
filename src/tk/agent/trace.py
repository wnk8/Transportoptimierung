"""Protokoll aller Werkzeugaufrufe (Agent-Spur)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TraceEntry:
    zeit: str
    art: str  # "Anfrage", "Werkzeug", "Antwort", "Hinweis"
    name: str
    eingabe: Any
    ausgabe: Any
    dauer_ms: float = 0.0


@dataclass
class Trace:
    entries: list[TraceEntry] = field(default_factory=list)

    def add(self, art: str, name: str, eingabe: Any, ausgabe: Any, dauer_ms: float = 0.0) -> TraceEntry:
        entry = TraceEntry(dt.datetime.now().strftime("%H:%M:%S"), art, name, eingabe, ausgabe, dauer_ms)
        self.entries.append(entry)
        return entry

    def tool_outputs(self) -> list[Any]:
        return [e.ausgabe for e in self.entries if e.art == "Werkzeug"]
