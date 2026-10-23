"""Karte mit Luftlinien aus Routen (Gesamtpaket Abschnitt 9).

Zwei Karten nebeneinander (Vorher: Ist, Nachher: gewähltes Szenario) mit synchronem Zoom.
Jede Relation ist eine gerade Linie zwischen Ortsschwerpunkten (Luftlinie, schematisch).
Kodierung: Farbe plus Linienstärke plus Muster. Ohne Kachelserver zeigt die Ansicht
automatisch eine Knoten-Kanten-Darstellung (SVG) aus denselben Koordinaten.
"""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass
from typing import Any

from nicegui import ui

from tk.compare import relation_detail
from tk.excelfn import fold
from tk.models import Result
from tk.ui import format as fmt
from tk.ui.layout import SCENARIO_LABEL
from tk.ui.theme import MAP_LINES, START_COLORS, TOKENS

GERMANY_CENTER = (51.1, 10.2)
TILE_PROBE = "https://a.tile.osm.org/6/33/21.png"
"""Eine Kachel desselben Servers wie die Karte (NiceGUI-Standard: tile.osm.org, OpenStreetMap)."""
ROAD_BULGE = 0.12
"""Bogenhöhe der Lkw-Linie (Anteil der Linienlänge); Bögen trennen Linien aus demselben Startort."""
RAIL_BULGE = 0.24
"""Bogenhöhe der Bahnlinie: weiter außen als Lkw, damit beide Linien einer Relation sichtbar bleiben."""
ARC_POINTS = 16
DIMMED_OPACITY = 0.15
"""Deckkraft nicht ausgewählter Linien, solange Routen ausgewählt sind."""


@dataclass(slots=True)
class RelationView:
    key: str
    start: str
    ziel: str
    lat1: float
    lon1: float
    lat2: float
    lon2: float
    sendungen: int
    gewicht_t: float
    distanz_km: float
    quelle: str
    tkm_lkw: float
    tkm_bahn: float
    n_bahn: int
    co2_ist: float
    co2_plan: float
    kosten_ist: float
    kosten_plan: float
    lkw_km_ist: float
    lkw_km_plan: float
    lkw_km_bahn: float
    """Ist-Lkw-km der Sendungen, die im Plan auf die Bahn gehen (Breite der Bahnlinie)."""
    fahrten_ist: float
    fahrten_plan: float


def relations(result: Result, scenario: str) -> list[RelationView]:
    """Kennzahlen je Relation (Blatt Routen) für das gewählte Szenario."""
    out = []
    for route in result.routes:
        if None in (route.start_lat, route.start_lon, route.ziel_lat, route.ziel_lon):
            continue
        members = [r for r in result.valid_rows if fold(r.relation or "") == fold(route.key)]
        rail = [r for r in members if r.bahn == "Ja"] if scenario == "M3" else []
        road = [r for r in members if r not in rail]

        def plan(r: object) -> tuple[float, float]:
            if scenario == "Ist" or (scenario == "M2" and getattr(r, "bahn", "") == "Ja"):
                return getattr(r, "co2_ist_fzgkm", 0.0) or 0.0, getattr(r, "kosten_ist", 0.0) or 0.0
            return getattr(r, "co2_plan_fzgkm", 0.0) or 0.0, getattr(r, "kosten_plan", 0.0) or 0.0

        plans = [plan(r) for r in members]
        detail = relation_detail(result, route.key, scenario)
        out.append(
            RelationView(
                key=route.key,
                start=route.start,
                ziel=route.ziel,
                lat1=route.start_lat or 0.0,
                lon1=route.start_lon or 0.0,
                lat2=route.ziel_lat or 0.0,
                lon2=route.ziel_lon or 0.0,
                sendungen=route.sendungen,
                gewicht_t=route.gewicht_t,
                distanz_km=route.distanz_km,
                quelle=route.distanz_quelle,
                tkm_lkw=math.fsum(r.tkm or 0.0 for r in road),
                tkm_bahn=math.fsum(r.tkm or 0.0 for r in rail),
                n_bahn=len(rail),
                co2_ist=route.co2_ist,
                co2_plan=math.fsum(p[0] for p in plans),
                kosten_ist=route.kosten_ist,
                kosten_plan=math.fsum(p[1] for p in plans),
                lkw_km_ist=detail.ist.lkw_km,
                lkw_km_plan=detail.plan.lkw_km,
                lkw_km_bahn=math.fsum(r.lkw_km_ist or 0.0 for r in rail),
                fahrten_ist=detail.ist.fahrten,
                fahrten_plan=detail.plan.fahrten,
            )
        )
    return out


def _width(value: float, maximum: float) -> float:
    return 1.5 + 6 * math.sqrt(value / maximum) if maximum > 0 else 1.5


def _popup(rel: RelationView, scenario: str) -> str:
    delta = 0.0 if rel.co2_ist == 0 else rel.co2_plan / rel.co2_ist - 1
    rows = [
        ("Sendungen", fmt.number(rel.sendungen)),
        ("Gewicht", fmt.with_unit(rel.gewicht_t, "t", 1)),
        ("Distanz", f"{fmt.with_unit(rel.distanz_km, 'km', 1)} ({rel.quelle})"),
        ("Lkw-Fahrten Ist", fmt.number(rel.fahrten_ist, 1)),
        (f"Lkw-Fahrten {scenario}", fmt.number(rel.fahrten_plan, 1)),
        ("Lkw-km Ist", fmt.with_unit(rel.lkw_km_ist, "km")),
        (f"Lkw-km {scenario}", fmt.with_unit(rel.lkw_km_plan, "km")),
        ("CO₂e Ist", fmt.with_unit(rel.co2_ist, "kg")),
        (f"CO₂e {scenario}", fmt.with_unit(rel.co2_plan, "kg")),
        ("Δ CO₂e", fmt.percent(delta)),
        ("Kosten Ist", fmt.with_unit(rel.kosten_ist, "€")),
        (f"Kosten {scenario}", fmt.with_unit(rel.kosten_plan, "€")),
        ("davon Bahn", f"{rel.n_bahn} Sendungen"),
    ]
    body = "".join(
        f"<tr><td>{html.escape(k)}</td><td style='text-align:right'>{html.escape(v)}</td></tr>"
        for k, v in rows
    )
    title = html.escape(f"{rel.start} > {rel.ziel}")
    return f"<b>{title}</b><table style='font-size:12px;margin-top:4px'>{body}</table>"


def arc(lat1: float, lon1: float, lat2: float, lon2: float, bulge: float) -> list[list[float]]:
    r"""Quadratischer Bézier-Bogen von A nach B (schematisch, keine Route).

    .. math:: P(t) = (1-t)^2 A + 2t(1-t) C + t^2 B, \quad C = M + b\,(-\Delta\varphi, \Delta\lambda)

    mit Mittelpunkt :math:`M` und Bogenhöhe :math:`b`; die Ausbuchtung liegt immer links der Fahrtrichtung.
    """
    dlat, dlon = lat2 - lat1, lon2 - lon1
    c_lat = (lat1 + lat2) / 2 + bulge * dlon
    c_lon = (lon1 + lon2) / 2 - bulge * dlat
    points = []
    for i in range(ARC_POINTS + 1):
        t = i / ARC_POINTS
        a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t**2
        points.append([a * lat1 + b * c_lat + c * lat2, a * lon1 + b * c_lon + c * lon2])
    return points


Spec = tuple[list[list[float]], dict[str, object], str, str]
"""Linie: Koordinaten, Leaflet-Optionen, Tooltip-HTML, Relationsschlüssel."""

RELATION_EVENT = "tk-relation"
TOUR_EVENT = "tk-tour"


def bind_layer(layer: object, tooltip: str, key: str, event: str = RELATION_EVENT) -> None:
    """Tooltip beim Überfahren und Klickereignis an Python (Spike R1: run_method mit Präfix ':')."""
    layer.run_method("bindTooltip", tooltip, {"sticky": True})  # type: ignore[attr-defined]
    layer.run_method(":on", "'click'", f"() => emitEvent({json.dumps(event)}, {json.dumps(key)})")  # type: ignore[attr-defined]


def start_colors(rels: list[RelationView]) -> dict[str, str]:
    """Farbe je Startort; Startorte alphabetisch, damit eine Farbe bei jeder Rechnung gleich bleibt."""
    starts = sorted({r.start for r in rels})
    return {s: START_COLORS[i % len(START_COLORS)] for i, s in enumerate(starts)}


def short_name(label: str) -> str:
    """ "70173 Stuttgart" wird "Stuttgart"."""
    return label.split(" ", 1)[-1]


def line_specs(
    result: Result,
    scenario: str,
    side: str,
    color_by: str = "start",
    start: str | None = None,
    highlight: dict[str, str] | None = None,
) -> list[Spec]:
    """Linien einer Karte: (Koordinaten, Leaflet-Optionen, Tooltip-HTML, Relationsschlüssel).

    Breite links und rechts aus derselben Größe (Lkw-km je Relation) mit gemeinsamem
    Maximum, damit eine dünnere Linie rechts tatsächlich weniger Lkw-km bedeutet. Die
    Bahnlinie zeigt die Lkw-km, die von der Straße verlagert werden. Bei Szenario Ist
    gibt es kein Nachher.

    ``color_by``: ``"start"`` färbt nach Startort (Bahn gestrichelt), ``"szenario"`` nach
    Ist, Lkw und Bahn wie bisher. ``start`` beschränkt auf einen Startort. ``highlight``
    ordnet ausgewählten Relationen eine Farbe zu; alle anderen Linien treten zurück.
    """
    if side == "nachher" and scenario == "Ist":
        return []
    rels = relations(result, scenario)
    km_max = max((max(r.lkw_km_ist, r.lkw_km_plan) for r in rels), default=0.0)
    by_start = start_colors(rels)
    picked = {fold(k): c for k, c in (highlight or {}).items()}
    _, dash = MAP_LINES["bahn"]
    specs: list[Spec] = []
    for rel in rels:
        if start is not None and rel.start != start:
            continue
        chosen = picked.get(fold(rel.key))
        opacity = 0.9 if not picked or chosen else DIMMED_OPACITY

        def color(kind: str, rel: RelationView = rel, chosen: str | None = chosen) -> str:
            if chosen:
                return chosen
            return by_start[rel.start] if color_by == "start" else MAP_LINES[kind][0]

        popup = _popup(rel, scenario)
        extra = 1.5 if chosen else 0.0
        if side == "vorher":
            opts: dict[str, object] = {
                "color": color("ist"),
                "weight": _width(rel.lkw_km_ist, km_max) + extra,
                "opacity": opacity,
            }
            specs.append((arc(rel.lat1, rel.lon1, rel.lat2, rel.lon2, ROAD_BULGE), opts, popup, rel.key))
            continue
        if rel.lkw_km_plan > 0:
            opts = {
                "color": color("lkw"),
                "weight": _width(rel.lkw_km_plan, km_max) + extra,
                "opacity": opacity,
            }
            specs.append((arc(rel.lat1, rel.lon1, rel.lat2, rel.lon2, ROAD_BULGE), opts, popup, rel.key))
        if rel.n_bahn > 0:
            opts = {
                "color": color("bahn"),
                "weight": _width(rel.lkw_km_bahn, km_max) + extra,
                "dashArray": dash,
                "opacity": opacity,
            }
            specs.append((arc(rel.lat1, rel.lon1, rel.lat2, rel.lon2, RAIL_BULGE), opts, popup, rel.key))
    return specs


CHANGE_TOLERANCE = 0.005
"""Unter 0,5 % Änderung der Lkw-km gilt eine Relation als unverändert (nur Darstellung)."""

CHANGE_STYLES: dict[str, tuple[str, str, str]] = {
    "weniger": (MAP_LINES["lkw"][0], "", "Lkw, weniger km"),
    "gleich": (TOKENS["muted"], "2 6", "Lkw, unverändert, gepunktet"),
    "mehr": (MAP_LINES["auswahl"][0], "", "Lkw, mehr km"),
}
"""Differenzansicht: Farbe, Muster und Text je Veränderungsklasse der Lkw-km."""


def change_class(ist: float, plan: float) -> str:
    if ist <= 0 or abs(plan / ist - 1) < CHANGE_TOLERANCE:
        return "gleich"
    return "weniger" if plan < ist else "mehr"


def diff_specs(
    result: Result, scenario: str, start: str | None = None, highlight: dict[str, str] | None = None
) -> list[Spec]:
    """Differenzansicht: je Relation heller Ist-Bogen, darüber Plan-Bogen und Bahnbogen.

    Breiten wie in :func:`line_specs` (Lkw-km, gemeinsames Maximum); die Farbe zeigt die
    Veränderungsklasse, nicht den Startort. Ausgewählte Relationen bleiben kräftig.
    """
    if scenario == "Ist":
        return []
    rels = relations(result, scenario)
    km_max = max((max(r.lkw_km_ist, r.lkw_km_plan) for r in rels), default=0.0)
    picked = {fold(k) for k in (highlight or {})}
    bahn, dash = MAP_LINES["bahn"]
    specs: list[Spec] = []
    for rel in rels:
        if start is not None and rel.start != start:
            continue
        dim = bool(picked) and fold(rel.key) not in picked
        popup = _popup(rel, scenario)
        road = arc(rel.lat1, rel.lon1, rel.lat2, rel.lon2, ROAD_BULGE)
        ghost = {
            "color": TOKENS["muted"],
            "weight": _width(rel.lkw_km_ist, km_max),
            "opacity": DIMMED_OPACITY / 2 if dim else 0.22,
        }
        specs.append((road, ghost, popup, rel.key))
        opacity = DIMMED_OPACITY if dim else 0.95
        if rel.lkw_km_plan > 0:
            color, pattern, _ = CHANGE_STYLES[change_class(rel.lkw_km_ist, rel.lkw_km_plan)]
            opts: dict[str, object] = {
                "color": color,
                "weight": _width(rel.lkw_km_plan, km_max),
                "dashArray": pattern,
                "opacity": opacity,
            }
            specs.append((road, opts, popup, rel.key))
        if rel.n_bahn > 0:
            opts = {
                "color": bahn,
                "weight": _width(rel.lkw_km_bahn, km_max),
                "dashArray": dash,
                "opacity": opacity,
            }
            specs.append((arc(rel.lat1, rel.lon1, rel.lat2, rel.lon2, RAIL_BULGE), opts, popup, rel.key))
    return specs


def diff_legend(scenario: str) -> None:
    def swatch(color: str, dash: str, text: str, opacity: float = 1.0) -> None:
        with ui.row().classes("items-center gap-1"):
            ui.html(
                f'<svg width="36" height="10" aria-hidden="true"><line x1="0" y1="5" x2="36" y2="5" '
                f'stroke="{color}" stroke-opacity="{opacity}" stroke-width="6" stroke-dasharray="{dash}"/></svg>'
            )
            ui.label(text).classes("tk-label")

    with ui.row().classes("items-center gap-4 flex-wrap"):
        swatch(TOKENS["muted"], "", "Ist, hell (Breite: Ist-Lkw-km)", 0.3)
        for color, pattern, text in CHANGE_STYLES.values():
            swatch(color, pattern, text)
        if scenario == "M3":
            swatch(*MAP_LINES["bahn"], "Bahn, gestrichelt (Breite: verlagerte Lkw-km)")
        ui.label("Luftlinie, schematisch").classes("tk-label")


Node = tuple[str, float, float, str]
"""Knoten: Name, Breite, Länge, Farbe (Startort) oder leer (Ziel)."""


def nodes(result: Result, start: str | None = None) -> list[Node]:
    """Startorte (farbig) und Ziele der sichtbaren Relationen."""
    rels = [r for r in relations(result, "Ist") if start is None or r.start == start]
    colors = start_colors(relations(result, "Ist"))
    out: dict[str, Node] = {}
    for r in rels:
        out.setdefault(r.start, (r.start, r.lat1, r.lon1, colors[r.start]))
    for r in rels:
        out.setdefault(r.ziel, (r.ziel, r.lat2, r.lon2, ""))
    return list(out.values())


def legend(scenario: str, color_by: str = "start", starts: dict[str, str] | None = None) -> None:
    def swatch(color: str, dash: str, text: str) -> None:
        with ui.row().classes("items-center gap-1"):
            ui.html(
                f'<svg width="36" height="10" aria-hidden="true"><line x1="0" y1="5" x2="36" y2="5" '
                f'stroke="{color}" stroke-width="4" stroke-dasharray="{dash}"/></svg>'
            )
            ui.label(text).classes("tk-label")

    with ui.row().classes("items-center gap-4 flex-wrap"):
        if color_by == "start" and starts:
            for name, color in starts.items():
                swatch(color, "", f"Start {short_name(name)}")
            if scenario == "M3":
                swatch(TOKENS["muted"], MAP_LINES["bahn"][1], "Bahn, gestrichelt (Breite: verlagerte Lkw-km)")
        else:
            items = [("ist", "Ist, Einzelversand")]
            if scenario != "Ist":
                items.append(("lkw", f"{scenario}, Lkw"))
            if scenario == "M3":
                items.append(("bahn", "M3, Bahn, gestrichelt (Breite: verlagerte Lkw-km)"))
            for key, text in items:
                color, dash = MAP_LINES[key]
                swatch(color, dash, text)
        ui.label("Breite: Lkw-km je Relation, gleiche Skala links und rechts").classes("tk-label")
        ui.label("Luftlinie, schematisch").classes("tk-label")


def svg_network(
    result: Result,
    scenario: str,
    side: str,
    width: int = 520,
    height: int = 420,
    color_by: str = "start",
    start: str | None = None,
    highlight: dict[str, str] | None = None,
) -> str:
    """Knoten-Kanten-Ansicht ohne Kacheln (Rückfall bei fehlendem Netz), gleiche Linien wie die Karte."""
    rels = relations(result, scenario)
    if not rels:
        return ""
    lats = [v for r in rels for v in (r.lat1, r.lat2)]
    lons = [v for r in rels for v in (r.lon1, r.lon2)]
    pad = 40
    lat_min, lat_max, lon_min, lon_max = min(lats), max(lats), min(lons), max(lons)
    kx = math.cos(math.radians((lat_min + lat_max) / 2))
    span = max((lon_max - lon_min) * kx, lat_max - lat_min) or 1.0
    scale = min(width, height) - 2 * pad

    def xy(lat: float, lon: float) -> tuple[float, float]:
        return pad + (lon - lon_min) * kx / span * scale, pad + (lat_max - lat) / span * scale

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Knoten-Kanten-Ansicht">'
    ]
    parts.append(f'<rect width="{width}" height="{height}" fill="{TOKENS["surface"]}"/>')
    for coords, opts, popup, _key in line_specs(result, scenario, side, color_by, start, highlight):
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(lat, lon) for lat, lon in coords))
        dash = opts.get("dashArray", "")
        title = html.escape(popup.split("</b>")[0].replace("<b>", ""))
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{opts["color"]}" '
            f'stroke-opacity="{opts["opacity"]}" stroke-width="{float(str(opts["weight"])):.1f}" '
            f'stroke-dasharray="{dash}" stroke-linecap="round"><title>{title}</title></polyline>'
        )
    for name, lat, lon, color in nodes(result, start):
        x, y = xy(lat, lon)
        r = 6 if color else 4
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color or TOKENS["text"]}"/>')
        weight = "600" if color else "400"
        parts.append(
            f'<text x="{x + 7:.1f}" y="{y - 6:.1f}" font-size="11" font-weight="{weight}" '
            f'fill="{TOKENS["text"]}">{html.escape(short_name(name))}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def draw_tour(
    m: ui.leaflet,
    points: list[tuple[float, float]],
    labels: list[str],
    per_stop: dict[str, int],
    route: Any | None,
) -> list[object]:
    """Ist als Stern vom Start zu jedem Ziel (Breite: Sendungen je Ziel), Plan als Tour mit Stopps.

    ``per_stop`` zählt Sendungen je gefaltetem Zielnamen; ``route`` ist eine Straßenroute aus dem
    Cache oder ``None`` (dann schematisch). Gibt die Ebenen zurück, damit der Aufrufer sie entfernt.
    """
    layers: list[object] = []
    if not points:
        return layers
    start = points[0]
    ist_color, _ = MAP_LINES["ist"]
    for name, p in zip(labels[1:], points[1:], strict=True):
        n = per_stop.get(fold(name), 1)
        layers.append(
            m.generic_layer(
                name="polyline",
                args=[[list(start), list(p)], {"color": ist_color, "weight": 1.5 + 2 * n, "opacity": 0.6}],
            )
        )
    if route is not None:
        color, _ = MAP_LINES["lkw"]
        layers.append(m.generic_layer(name="polyline", args=[route.geometry, {"color": color, "weight": 4}]))
    else:
        color, dash = MAP_LINES["luft"]
        layers.append(
            m.generic_layer(
                name="polyline",
                args=[[list(p) for p in points], {"color": color, "weight": 3, "dashArray": dash}],
            )
        )
    markers = []
    for i, (name, p) in enumerate(zip(labels, points, strict=True)):
        marker = m.generic_layer(
            name="circleMarker",
            args=[
                list(p),
                {
                    "radius": 7,
                    "color": TOKENS["text"],
                    "fillColor": TOKENS["surface"],
                    "fillOpacity": 1,
                    "weight": 2,
                },
            ],
        )
        markers.append((marker, f"{'Start' if i == 0 else i}: {name}"))
        layers.append(marker)

    async def bind() -> None:
        await m.initialized()
        for marker, text in markers:
            marker.run_method("bindTooltip", text, {"permanent": True, "direction": "right"})
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        m.run_map_method("fitBounds", [[min(lats), min(lons)], [max(lats), max(lons)]], {"padding": [40, 40]})

    ui.timer(0.2, bind, once=True)
    return layers


def view_for(
    bounds: list[list[float]], width_px: int = 460, height_px: int = 420
) -> tuple[tuple[float, float], int]:
    """Mittelpunkt und ganzzahliger Zoom, bei dem alle Relationen in die Karte passen (Web-Mercator)."""
    (lat1, lon1), (lat2, lon2) = bounds
    center = ((lat1 + lat2) / 2, (lon1 + lon2) / 2)

    def merc(lat: float) -> float:
        return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

    span_x = max(abs(lon2 - lon1), 0.01) / 360
    span_y = max(abs(merc(lat2) - merc(lat1)), 0.0001) / (2 * math.pi)
    zoom = min(math.log2(width_px / 256 / span_x), math.log2(height_px / 256 / span_y))
    return center, max(3, min(12, math.floor(zoom)))


class MapView:
    """Zwei synchronisierte Karten (Vorher, Nachher) mit Rückfall auf SVG."""

    def __init__(self, initial: Result | None = None) -> None:
        center, zoom = GERMANY_CENTER, 6
        if initial is not None:
            rels = relations(initial, "Ist")
            if rels:
                lats = [v for r in rels for v in (r.lat1, r.lat2)]
                lons = [v for r in rels for v in (r.lon1, r.lon2)]
                center, zoom = view_for([[min(lats), min(lons)], [max(lats), max(lons)]])
        self._view = (center, zoom)
        self._ready = False
        self.result: Result | None = None
        self.scenario = "M3"
        self.offline = False
        self._layers: dict[str, list[object]] = {"vorher": [], "nachher": [], "diff": []}
        self._syncing = False
        self.highlight: dict[str, str] = {}
        """Ausgewählte Relationen und ihre Farbe (Routenvergleich)."""
        self.root = ui.column().classes("w-full gap-2")
        with self.root:
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Karte").classes("tk-section")
                self.mode = ui.toggle(
                    {"karte": "Nebeneinander", "diff": "Differenz", "netz": "Knoten-Kanten"},
                    value="karte",
                    on_change=lambda _: self._apply_mode(),
                ).props("dense no-caps unelevated toggle-color=primary")
            with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                self.start_filter = ui.toggle(
                    {"": "Alle Startorte"}, value="", on_change=lambda _: self.render()
                ).props("dense no-caps unelevated toggle-color=primary")
                with ui.row().classes("items-center gap-2") as self.color_row:
                    ui.label("Farbe nach").classes("tk-label")
                    self.color_by = ui.toggle(
                        {"start": "Startort", "szenario": "Szenario"},
                        value="start",
                        on_change=lambda _: self.render(),
                    ).props("dense no-caps unelevated toggle-color=primary")
            with ui.column().classes("w-full gap-1") as self.diff_col:
                self.title_diff = ui.label("Differenz").classes("tk-label")
                with ui.element("div").classes("w-full") as self.box_diff:
                    self.map_diff = (
                        ui.leaflet(center=center, zoom=zoom).classes("w-full").style("height:520px")
                    )
                self.hint_diff = ui.label(
                    "Ist gewählt. M2 oder M3 wählen, um die Differenz zu sehen."
                ).classes("tk-note")
            with ui.row().classes("w-full gap-2 no-wrap tk-two-col") as self.pair:
                with ui.column().classes("flex-1 gap-1 min-w-0"):
                    self.title_left = ui.label("Vorher: Ist").classes("tk-label")
                    # Toggle a wrapper, never the map: set_visibility rewrites the element's classes
                    # and drops the ones Leaflet added itself (leaflet-container), which hides tiles.
                    with ui.element("div").classes("w-full") as self.box_left:
                        self.map_left = (
                            ui.leaflet(center=center, zoom=zoom).classes("w-full").style("height:420px")
                        )
                    self.svg_left = ui.html("").classes("w-full")
                with ui.column().classes("flex-1 gap-1 min-w-0"):
                    self.title_right = ui.label("Nachher").classes("tk-label")
                    # Toggle a wrapper, never the map: set_visibility rewrites the element's classes
                    # and drops the ones Leaflet added itself (leaflet-container), which hides tiles.
                    with ui.element("div").classes("w-full") as self.box_right:
                        self.map_right = (
                            ui.leaflet(center=center, zoom=zoom).classes("w-full").style("height:420px")
                        )
                    self.svg_right = ui.html("").classes("w-full")
                    self.hint_right = ui.label(
                        "Ist gewählt. M2 oder M3 wählen, um Vorher und Nachher zu vergleichen."
                    ).classes("tk-note")
                    self.hint_right.set_visibility(False)
            self.legend_box = ui.row().classes("w-full")
            self.notice = ui.label("").classes("tk-note")
            self.notice.set_visibility(False)
        for src, dst in ((self.map_left, self.map_right), (self.map_right, self.map_left)):
            src.on("map-moveend", lambda e, d=dst: self._sync(e.args, d))
        self._apply_mode()

    def _sync(self, args: dict[str, object], dst: ui.leaflet) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            center = args.get("center")
            zoom = args.get("zoom")
            if isinstance(center, dict):
                target = (float(center["lat"]), float(center["lng"]))
            elif isinstance(center, list | tuple):
                target = (float(center[0]), float(center[1]))
            else:
                return
            # Only move when the other map differs, otherwise both maps echo each other.
            current = dst.center
            if abs(current[0] - target[0]) > 1e-4 or abs(current[1] - target[1]) > 1e-4:
                dst.set_center(target)
            if isinstance(zoom, int | float) and int(zoom) != dst.zoom:
                dst.set_zoom(int(zoom))
        finally:
            self._syncing = False

    async def probe_tiles(self) -> None:
        """Prüft einmal, ob der Kachelserver erreichbar ist; sonst Knoten-Kanten-Ansicht."""
        script = (
            "new Promise(r => { const i = new Image(); const t = setTimeout(() => r(false), 10000);"
            f" i.onload = () => {{ clearTimeout(t); r(true); }}; i.onerror = () => {{ clearTimeout(t); r(false); }};"
            f" i.src = '{TILE_PROBE}'; }})"
        )
        try:
            ok = await ui.run_javascript(script, timeout=12)
        except TimeoutError:
            ok = False
        if not ok:
            self.offline = True
            self.mode.set_value("netz")
            self.notice.set_text(
                "Kartenkacheln nicht erreichbar: Knoten-Kanten-Ansicht aus denselben Koordinaten."
            )
            self.notice.set_visibility(True)

    def _apply_mode(self) -> None:
        self._visibility()
        self.render()

    def _visibility(self) -> None:
        """Karte, Differenz oder SVG je Modus; bei Szenario Ist zeigt die Planseite einen Hinweis."""
        mode = self.mode.value
        net, diff = mode == "netz", mode == "diff"
        no_plan = self.scenario == "Ist"
        self.pair.set_visibility(not diff)
        self.diff_col.set_visibility(diff)
        self.hint_diff.set_visibility(no_plan)
        boxes = (
            (self.box_left, self.map_left, mode == "karte"),
            (self.box_right, self.map_right, mode == "karte" and not no_plan),
            (self.box_diff, self.map_diff, diff and not no_plan),
        )
        for box, m, show in boxes:
            was_hidden = not box.visible
            box.set_visibility(show)
            if show and self._ready and was_hidden:
                # Leaflet measures 0 x 0 while hidden; re-measure once the container is visible
                # and align it with the left map, which stayed visible.
                ui.timer(0.3, lambda m=m: self._remeasure(m), once=True)
        self.svg_left.set_visibility(net)
        self.svg_right.set_visibility(net and not no_plan)
        self.hint_right.set_visibility(no_plan)

    def _remeasure(self, m: ui.leaflet) -> None:
        ref = self.map_left if m is not self.map_left else self.map_right
        m.run_map_method("invalidateSize")
        m.run_map_method("setView", list(ref.center), ref.zoom)

    async def settle(self) -> None:
        """Nach dem Einblenden des umgebenden Tabs die sichtbaren Karten neu vermessen."""
        visible = {"karte": (self.map_left, self.map_right), "diff": (self.map_diff,)}
        for m in visible.get(str(self.mode.value), ()):
            await m.initialized()
            m.run_map_method("invalidateSize")

    def update(self, result: Result, scenario: str) -> None:
        self.result, self.scenario = result, scenario
        self._visibility()
        self.render()

    def set_highlight(self, highlight: dict[str, str]) -> None:
        self.highlight = dict(highlight)
        self.render()

    def _sync_start_options(self) -> None:
        assert self.result is not None
        starts = sorted({r.start for r in relations(self.result, "Ist")})
        options = {"": "Alle Startorte"} | {s: short_name(s) for s in starts}
        if options != self.start_filter.options:
            self.start_filter.set_options(
                options, value=self.start_filter.value if self.start_filter.value in options else ""
            )

    def render(self) -> None:
        if self.result is None:
            return
        self._sync_start_options()
        color_by = str(self.color_by.value)
        start = str(self.start_filter.value) or None
        self.title_left.set_text("Vorher: Ist (Einzelversand)")
        self.title_right.set_text(
            "Nachher" if self.scenario == "Ist" else f"Nachher: {SCENARIO_LABEL[self.scenario]}"
        )
        diff = self.mode.value == "diff"
        self.color_row.set_visibility(not diff)
        self.title_diff.set_text(
            f"Differenz: Ist gegen {SCENARIO_LABEL[self.scenario]}" if self.scenario != "Ist" else "Differenz"
        )
        self.legend_box.clear()
        with self.legend_box:
            if diff:
                diff_legend(self.scenario)
            else:
                legend(self.scenario, color_by, start_colors(relations(self.result, "Ist")))
        if self.mode.value == "netz":
            for side, box in (("vorher", self.svg_left), ("nachher", self.svg_right)):
                box.set_content(
                    svg_network(
                        self.result,
                        self.scenario,
                        side,
                        color_by=color_by,
                        start=start,
                        highlight=self.highlight,
                    )
                )
            return
        pending: list[tuple[ui.leaflet, object, str, str]] = []
        labels: list[tuple[object, str, bool]] = []
        drawn = (
            [("diff", self.map_diff, diff_specs(self.result, self.scenario, start, self.highlight))]
            if diff
            else [
                (side, m, line_specs(self.result, self.scenario, side, color_by, start, self.highlight))
                for side, m in (("vorher", self.map_left), ("nachher", self.map_right))
            ]
        )
        for side, m, specs in drawn:
            for layer in self._layers[side]:
                m.remove_layer(layer)  # type: ignore[arg-type]
            self._layers[side] = []
            for coords, opts, popup, key in specs:
                layer = m.generic_layer(name="polyline", args=[coords, opts])
                self._layers[side].append(layer)
                pending.append((m, layer, popup, key))
            if not specs:
                continue
            for name, lat, lon, color in nodes(self.result, start):
                is_start = bool(color)
                marker = m.generic_layer(
                    name="circleMarker",
                    args=[
                        [lat, lon],
                        {
                            "radius": 7 if is_start else 4,
                            "color": TOKENS["surface"],
                            "weight": 2 if is_start else 1,
                            "fillColor": color or TOKENS["text"],
                            "fillOpacity": 1,
                            "interactive": False,
                        },
                    ],
                )
                self._layers[side].append(marker)
                labels.append((marker, short_name(name), is_start))

        async def bind() -> None:
            # Tooltips and clicks can only be bound once the layers exist in the browser (spike S14).
            for m in (self.map_left, self.map_right, self.map_diff):
                await m.initialized()
            if not self._ready:
                # Leaflet measures its container at creation; re-measure once the layout is final.
                self._ready = True
                for m in (self.map_left, self.map_right, self.map_diff):
                    m.run_map_method("invalidateSize")
                    m.run_map_method("setView", list(self._view[0]), self._view[1])
            for _, layer, popup, key in pending:
                bind_layer(
                    layer, popup + "<div style='margin-top:4px'>Klick: Vergleich Ist gegen Plan</div>", key
                )
            for marker, text, is_start in labels:
                css = "tk-map-label tk-map-start" if is_start else "tk-map-label"
                marker.run_method(  # type: ignore[attr-defined]
                    "bindTooltip",
                    text,
                    {"permanent": True, "direction": "right", "offset": [6, 0], "className": css},
                )

        ui.timer(0.1, bind, once=True)
