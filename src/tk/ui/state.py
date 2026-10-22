"""Zustand der Oberfläche: Basismodell aus der Excel-Mappe und Sitzung je Browser-Tab."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from tk.agent.trace import Trace
from tk.models import Assumptions, Result, Shipment
from tk.scenarios import Model, calculate, load_model, with_changes, workbook_shipments
from tk.workbook import DATA, DEFAULT_WORKBOOK, load_workbook_data

REFERENCE_FILE = DATA / "reference" / "expected.json"
SNAPSHOT_FILE = DATA / "reference" / "snapshot.json"


@dataclass(slots=True)
class BaseData:
    """Unveränderliche Grundlage: Modell mit Parametern aus Assumptions und Beispieldaten."""

    model: Model
    shipments: list[Shipment]
    result: Result
    source: str


@cache
def base_data(path: Path | None = None) -> BaseData | None:
    """Lädt die Excel-Mappe einmal je Prozess. ``None``, wenn die Mappe fehlt."""
    workbook = path or DEFAULT_WORKBOOK
    if not workbook.exists():
        return None
    data = load_workbook_data(workbook)
    model = load_model(data)
    shipments = workbook_shipments(data)
    return BaseData(model, shipments, calculate(shipments, model), data.source)


@cache
def reference() -> dict[str, Any] | None:
    if not REFERENCE_FILE.exists():
        return None
    data: dict[str, Any] = json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))
    return data


@cache
def snapshot() -> dict[str, Any] | None:
    if not SNAPSHOT_FILE.exists():
        return None
    data: dict[str, Any] = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    return data


@dataclass
class Session:
    """Zustand eines Browser-Tabs."""

    base: BaseData
    shipments: list[Shipment]
    changes: dict[str, object] = field(default_factory=dict)
    scenario: str = "M3"
    result: Result | None = None
    road_km: bool = False
    agent_trace: Trace | None = None

    @property
    def model(self) -> Model:
        return with_changes(self.base.model, self.changes) if self.changes else self.base.model

    @property
    def params(self) -> Assumptions:
        return self.model.params

    def recalculate(self) -> Result:
        """Rechnet neu; mit ``road_km`` gehen Straßen-km als Relationstabelle ein (Variante)."""
        model = self.model
        result = calculate(self.shipments, model)
        if self.road_km:
            from tk.routing import with_road_km
            from tk.ui.map_area import route_cache

            road_model, _ = with_road_km(model, result, route_cache())
            result = calculate(self.shipments, road_model)
        self.result = result
        return self.result


SESSIONS: dict[str, Session] = {}
"""Sitzungen je Browser (Cookie-ID), damit Eingabe und Analyse denselben Stand zeigen. Nur im Speicher."""


def session_for(browser_id: str, base: BaseData) -> Session:
    """Sitzung des Browsers; beim ersten Aufruf mit den Beispieldaten der Excel-Mappe."""
    session = SESSIONS.get(browser_id)
    if session is None:
        session = Session(base=base, shipments=list(base.shipments), result=base.result)
        SESSIONS[browser_id] = session
    return session
