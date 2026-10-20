"""Zustand der Oberfläche: Basismodell aus der Excel-Mappe und Sitzung je Browser-Tab."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

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

    @property
    def model(self) -> Model:
        return with_changes(self.base.model, self.changes) if self.changes else self.base.model

    @property
    def params(self) -> Assumptions:
        return self.model.params

    def recalculate(self) -> Result:
        self.result = calculate(self.shipments, self.model)
        return self.result
