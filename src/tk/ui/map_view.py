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

from nicegui import ui

from tk.compare import relation_detail
from tk.excelfn import fold
from tk.models import Result
from tk.ui import format as fmt
from tk.ui.layout import SCENARIO_LABEL
from tk.ui.theme import MAP_LINES, TOKENS

GERMANY_CENTER = (51.1, 10.2)
TILE_PROBE = "https://a.tile.osm.org/6/33/21.png"
"""Eine Kachel desselben Servers wie die Karte (NiceGUI-Standard: tile.osm.org, OpenStreetMap)."""
RAIL_OFFSET = 0.012
"""Seitlicher Versatz der Bahnlinie (Anteil der Linienlänge), damit Lkw und Bahn sichtbar bleiben."""


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


def _rail_path(rel: RelationView) -> list[list[float]]:
    dlat, dlon = rel.lat2 - rel.lat1, rel.lon2 - rel.lon1
    length = math.hypot(dlat, dlon) or 1.0
    off_lat, off_lon = -dlon / length * RAIL_OFFSET * length, dlat / length * RAIL_OFFSET * length
    return [[rel.lat1 + off_lat, rel.lon1 + off_lon], [rel.lat2 + off_lat, rel.lon2 + off_lon]]


Spec = tuple[list[list[float]], dict[str, object], str, str]
"""Linie: Koordinaten, Leaflet-Optionen, Tooltip-HTML, Relationsschlüssel."""

RELATION_EVENT = "tk-relation"
TOUR_EVENT = "tk-tour"


def bind_layer(layer: object, tooltip: str, key: str, event: str = RELATION_EVENT) -> None:
    """Tooltip beim Überfahren und Klickereignis an Python (Spike R1: run_method mit Präfix ':')."""
    layer.run_method("bindTooltip", tooltip, {"sticky": True})  # type: ignore[attr-defined]
    layer.run_method(":on", "'click'", f"() => emitEvent({json.dumps(event)}, {json.dumps(key)})")  # type: ignore[attr-defined]


def line_specs(result: Result, scenario: str, side: str) -> list[Spec]:
    """Linien einer Karte: (Koordinaten, Leaflet-Optionen, Tooltip-HTML, Relationsschlüssel).

    Breite links und rechts aus derselben Größe (Lkw-km je Relation) mit gemeinsamem
    Maximum, damit eine dünnere Linie rechts tatsächlich weniger Lkw-km bedeutet. Die
    Bahnlinie zeigt die Lkw-km, die von der Straße verlagert werden. Bei Szenario Ist
    gibt es kein Nachher.
    """
    if side == "nachher" and scenario == "Ist":
        return []
    rels = relations(result, scenario)
    km_max = max((max(r.lkw_km_ist, r.lkw_km_plan) for r in rels), default=0.0)
    specs: list[Spec] = []
    if side == "vorher":
        color, _ = MAP_LINES["ist"]
        for rel in rels:
            opts = {"color": color, "weight": _width(rel.lkw_km_ist, km_max), "opacity": 0.9}
            specs.append(([[rel.lat1, rel.lon1], [rel.lat2, rel.lon2]], opts, _popup(rel, scenario), rel.key))
        return specs
    lkw, _ = MAP_LINES["lkw"]
    bahn, dash = MAP_LINES["bahn"]
    for rel in rels:
        popup = _popup(rel, scenario)
        if rel.lkw_km_plan > 0:
            opts = {"color": lkw, "weight": _width(rel.lkw_km_plan, km_max), "opacity": 0.9}
            specs.append(([[rel.lat1, rel.lon1], [rel.lat2, rel.lon2]], opts, popup, rel.key))
        if rel.n_bahn > 0:
            opts = {
                "color": bahn,
                "weight": _width(rel.lkw_km_bahn, km_max),
                "dashArray": dash,
                "opacity": 0.95,
            }
            specs.append((_rail_path(rel), opts, popup, rel.key))
    return specs


def legend(scenario: str) -> None:
    items = [("ist", "Ist, Einzelversand")]
    if scenario != "Ist":
        items.append(("lkw", f"{scenario}, Lkw"))
    if scenario == "M3":
        items.append(("bahn", "M3, Bahn, gestrichelt (Breite: verlagerte Lkw-km)"))
    with ui.row().classes("items-center gap-4 flex-wrap"):
        for key, text in items:
            color, dash = MAP_LINES[key]
            with ui.row().classes("items-center gap-1"):
                ui.html(
                    f'<svg width="36" height="10" aria-hidden="true"><line x1="0" y1="5" x2="36" y2="5" '
                    f'stroke="{color}" stroke-width="4" stroke-dasharray="{dash}"/></svg>'
                )
                ui.label(text).classes("tk-label")
        ui.label("Breite: Lkw-km je Relation, gleiche Skala links und rechts").classes("tk-label")
        ui.label("Luftlinie, schematisch").classes("tk-label")


def svg_network(result: Result, scenario: str, side: str, width: int = 520, height: int = 420) -> str:
    """Knoten-Kanten-Ansicht ohne Kacheln (Rückfall bei fehlendem Netz)."""
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
    for coords, opts, popup, _key in line_specs(result, scenario, side):
        (a, b), (c, d) = xy(*coords[0]), xy(*coords[1])
        dash = opts.get("dashArray", "")
        title = html.escape(popup.split("</b>")[0].replace("<b>", ""))
        parts.append(
            f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" stroke="{opts["color"]}" '
            f'stroke-width="{float(str(opts["weight"])):.1f}" stroke-dasharray="{dash}" stroke-linecap="round">'
            f"<title>{title}</title></line>"
        )
    nodes: dict[str, tuple[float, float]] = {}
    for r in rels:
        nodes.setdefault(r.start, (r.lat1, r.lon1))
        nodes.setdefault(r.ziel, (r.lat2, r.lon2))
    for name, (lat, lon) in nodes.items():
        x, y = xy(lat, lon)
        label = html.escape(name.split(" ", 1)[-1])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{TOKENS["text"]}"/>')
        parts.append(
            f'<text x="{x + 6:.1f}" y="{y - 6:.1f}" font-size="11" fill="{TOKENS["text"]}">{label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


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
        self._layers: dict[str, list[object]] = {"vorher": [], "nachher": []}
        self._syncing = False
        self.root = ui.column().classes("w-full gap-2")
        with self.root:
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Karte").classes("tk-section")
                self.mode = ui.toggle(
                    {"karte": "Karte", "netz": "Knoten-Kanten"},
                    value="karte",
                    on_change=lambda _: self._apply_mode(),
                ).props("dense no-caps unelevated toggle-color=primary")
            with ui.row().classes("w-full gap-2 no-wrap tk-two-col"):
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
        """Karte oder SVG je Modus; bei Szenario Ist bleibt die rechte Seite ein Hinweis."""
        net = self.mode.value == "netz"
        no_plan = self.scenario == "Ist"
        boxes = (
            (self.box_left, self.map_left, not net),
            (self.box_right, self.map_right, not net and not no_plan),
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

    def update(self, result: Result, scenario: str) -> None:
        self.result, self.scenario = result, scenario
        self._visibility()
        self.render()

    def render(self) -> None:
        if self.result is None:
            return
        self.title_left.set_text("Vorher: Ist (Einzelversand)")
        self.title_right.set_text(
            "Nachher" if self.scenario == "Ist" else f"Nachher: {SCENARIO_LABEL[self.scenario]}"
        )
        self.legend_box.clear()
        with self.legend_box:
            legend(self.scenario)
        if self.mode.value == "netz":
            self.svg_left.set_content(svg_network(self.result, self.scenario, "vorher"))
            self.svg_right.set_content(svg_network(self.result, self.scenario, "nachher"))
            return
        pending: list[tuple[ui.leaflet, object, str, str]] = []
        for side, m in (("vorher", self.map_left), ("nachher", self.map_right)):
            for layer in self._layers[side]:
                m.remove_layer(layer)  # type: ignore[arg-type]
            self._layers[side] = []
            for coords, opts, popup, key in line_specs(self.result, self.scenario, side):
                layer = m.generic_layer(name="polyline", args=[coords, opts])
                self._layers[side].append(layer)
                pending.append((m, layer, popup, key))

        async def bind() -> None:
            # Tooltips and clicks can only be bound once the layers exist in the browser (spike S14).
            for m in (self.map_left, self.map_right):
                await m.initialized()
            if not self._ready:
                # Leaflet measures its container at creation; re-measure once the layout is final.
                self._ready = True
                for m in (self.map_left, self.map_right):
                    m.run_map_method("invalidateSize")
                    m.run_map_method("setView", list(self._view[0]), self._view[1])
            for _, layer, popup, key in pending:
                bind_layer(
                    layer, popup + "<div style='margin-top:4px'>Klick: Vergleich Ist gegen Plan</div>", key
                )

        ui.timer(0.1, bind, once=True)
