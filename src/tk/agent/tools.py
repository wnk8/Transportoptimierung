"""Werkzeuge des Agenten, alle Zahlen aus src/tk.

Der Agent arbeitet auf einer Arbeitsliste von Sendungen (aus Freitext übernommen). Jede
Ausgabe ist ein JSON-fähiges Dictionary; fehlende Daten erscheinen als
"nicht berechenbar, weil [Grund]".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tk.excelfn import fold, serial_to_date
from tk.explain import SPEC, explain
from tk.models import Result, Shipment
from tk.scenarios import Model, calculate

FIELDS = ("datum", "start", "ziel", "gewicht_kg", "sendungs_id", "km", "paletten", "fracht_eur")
REQUIRED = ("datum", "start", "gewicht_kg")


@dataclass
class AgentContext:
    """Arbeitsliste des Agenten und Bestand der Oberfläche."""

    model: Model
    bestand: list[Shipment] = field(default_factory=list)
    arbeitsliste: list[Shipment] = field(default_factory=list)
    result: Result | None = None

    def shipments(self, mit_bestand: bool) -> list[Shipment]:
        return [*self.bestand, *self.arbeitsliste] if mit_bestand else list(self.arbeitsliste)


SHIPMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "datum": {"type": "string", "description": "JJJJ-MM-TT oder TT.MM.JJJJ, nur wenn genannt"},
        "start": {"type": "string", "description": "PLZ oder Ort wie genannt"},
        "ziel": {"type": "string", "description": "PLZ oder Ort wie genannt"},
        "gewicht_kg": {"type": "number", "description": "Gewicht in kg, nur wenn genannt (t mal 1000)"},
        "sendungs_id": {"type": "string"},
        "km": {"type": "number", "description": "Entfernung in km, nur wenn ausdrücklich genannt"},
        "paletten": {"type": "number"},
        "fracht_eur": {"type": "number"},
    },
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "parse_shipments",
        "description": "Übernimmt Sendungen aus dem Text in die Arbeitsliste (Schema Input A bis H). "
        "Nur genannte Werte übergeben, nichts ergänzen oder schätzen. Meldet fehlende Pflichtfelder.",
        "parameters": {
            "type": "object",
            "properties": {
                "sendungen": {"type": "array", "items": SHIPMENT_SCHEMA},
                "ersetzen": {"type": "boolean", "description": "Arbeitsliste vorher leeren"},
            },
            "required": ["sendungen"],
        },
    },
    {
        "name": "validate_shipments",
        "description": "Prüft die Arbeitsliste wie Spalte I der Excel (Pflichtfelder, Orte, Zahlen).",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "plan_scenarios",
        "description": "Rechnet Ist, M2 und M3 mit dem Rechenkern und liefert das Ergebnis je Sendung.",
        "parameters": {
            "type": "object",
            "properties": {
                "mit_bestand": {"type": "boolean", "description": "Sendungen der Oberfläche einbeziehen"}
            },
        },
    },
    {
        "name": "get_route_summary",
        "description": "Kennzahlen einer Relation (Start > Ziel) aus dem letzten Rechenlauf.",
        "parameters": {
            "type": "object",
            "properties": {"start": {"type": "string"}, "ziel": {"type": "string"}},
            "required": ["start"],
        },
    },
    {
        "name": "compare_scenarios",
        "description": "Kennzahlen und Deltas von Ist, M2 und M3 aus dem letzten Rechenlauf.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "explain_result",
        "description": "Formel, Parameter, Quelle und Verifikation einer Kennzahl.",
        "parameters": {
            "type": "object",
            "properties": {"kennzahl": {"type": "string", "enum": list(SPEC)}},
            "required": ["kennzahl"],
        },
    },
]


def _row_report(result: Result) -> list[dict[str, Any]]:
    out = []
    for row in result.rows:
        s = row.shipment
        item: dict[str, Any] = {
            "zeile": row.excel_row,
            "sendungs_id": s.sendungs_id,
            "pruefung": row.pruefung,
        }
        if row.ok:
            item.update(
                {
                    "start": row.start_label,
                    "ziel": row.ziel_label,
                    "datum": serial_to_date(row.datum_serial).isoformat() if row.datum_serial else None,
                    "distanz_km": row.distanz_km,
                    "distanzquelle": row.distanz_quelle,
                    "fahrzeug_ist": row.fahrzeug,
                    "bahn": row.bahn,
                    "ergebnis": row.ergebnis,
                    "co2_ist_kg": row.co2_ist_fzgkm,
                    "co2_plan_kg": row.co2_plan_fzgkm,
                    "kosten_ist_eur": row.kosten_ist,
                    "kosten_plan_eur": row.kosten_plan,
                }
            )
        else:
            item["hinweis"] = f"nicht berechenbar, weil {row.pruefung}"
        out.append(item)
    return out


def _kpis(result: Result) -> dict[str, Any]:
    return {name: k.model_dump() for name, k in result.kpis.items()}


def parse_shipments(
    ctx: AgentContext, sendungen: list[dict[str, Any]], ersetzen: bool = False
) -> dict[str, Any]:
    if ersetzen:
        ctx.arbeitsliste = []
    added = []
    for raw in sendungen:
        values = {k: raw.get(k) for k in FIELDS}
        values = {k: (None if v in ("", None) else v) for k, v in values.items()}
        missing = [k for k in REQUIRED if values.get(k) is None]
        if values.get("ziel") is None and values.get("km") is None:
            missing.append("ziel oder km")
        ctx.arbeitsliste.append(Shipment(**values))
        added.append({"felder": {k: v for k, v in values.items() if v is not None}, "fehlend": missing})
    return {"arbeitsliste": len(ctx.arbeitsliste), "uebernommen": added}


def validate_shipments(ctx: AgentContext) -> dict[str, Any]:
    if not ctx.arbeitsliste:
        return {"hinweis": "nicht berechenbar, weil die Arbeitsliste leer ist"}
    result = calculate(ctx.arbeitsliste, ctx.model)
    rows = [
        {"zeile": i + 1, "pruefung": r.pruefung, "start": r.start_label, "ziel": r.ziel_label}
        for i, r in enumerate(result.rows)
    ]
    return {"gueltig": result.n_valid, "zeilen": rows}


def plan_scenarios(ctx: AgentContext, mit_bestand: bool = False) -> dict[str, Any]:
    ships = ctx.shipments(mit_bestand)
    if not ships:
        return {"hinweis": "nicht berechenbar, weil keine Sendungen vorliegen"}
    result = calculate(ships, ctx.model)
    ctx.result = result
    report = _row_report(result)
    return {
        "gueltig": result.n_valid,
        "status": result.status,
        "gesamtstatus": result.gesamtstatus,
        "kennzahlen": _kpis(result),
        "touren_gebuendelt": sum(t.gebuendelt for t in result.tours),
        "sendungen": report[-len(ctx.arbeitsliste) :] if mit_bestand and ctx.arbeitsliste else report[:50],
    }


def get_route_summary(ctx: AgentContext, start: str, ziel: str | None = None) -> dict[str, Any]:
    if ctx.result is None:
        return {"hinweis": "nicht berechenbar, weil noch kein Rechenlauf vorliegt (plan_scenarios)"}
    for route in ctx.result.routes:
        if fold(start) in fold(route.start) and (ziel is None or fold(ziel) in fold(route.ziel)):
            return route.model_dump()
    return {"hinweis": f"nicht berechenbar, weil keine Relation {start} > {ziel or ''} im Rechenlauf ist"}


def compare_scenarios(ctx: AgentContext) -> dict[str, Any]:
    if ctx.result is None:
        return {"hinweis": "nicht berechenbar, weil noch kein Rechenlauf vorliegt (plan_scenarios)"}
    return {"kennzahlen": _kpis(ctx.result), "status": ctx.result.status}


def explain_result(ctx: AgentContext, kennzahl: str) -> dict[str, Any]:
    if ctx.result is None:
        return {"hinweis": "nicht berechenbar, weil noch kein Rechenlauf vorliegt (plan_scenarios)"}
    if kennzahl not in SPEC:
        return {"hinweis": f"unbekannte Kennzahl {kennzahl}"}
    return explain(kennzahl, ctx.model.params, ctx.result).model_dump()  # type: ignore[arg-type]


REGISTRY = {
    "parse_shipments": parse_shipments,
    "validate_shipments": validate_shipments,
    "plan_scenarios": plan_scenarios,
    "get_route_summary": get_route_summary,
    "compare_scenarios": compare_scenarios,
    "explain_result": explain_result,
}


def call_tool(ctx: AgentContext, name: str, args: dict[str, Any]) -> dict[str, Any]:
    func = REGISTRY.get(name)
    if func is None:
        return {"fehler": f"unbekanntes Werkzeug {name}"}
    try:
        out: dict[str, Any] = func(ctx, **args)  # type: ignore[operator]
        return out
    except TypeError as exc:
        return {"fehler": f"ungültige Argumente: {exc}"}
