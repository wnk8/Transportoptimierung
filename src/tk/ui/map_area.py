"""Kartenbereich mit drei Ansichten und Detailpanel.

1. Vorher/Nachher: Luftlinien je Relation (``MapView``), Klick öffnet das Relationsdetail.
2. Straße gegen Luftlinie: Straßenrouten (OpenRouteService, Cache) neben der Luftlinie, mit km-Tabelle.
3. Touren: Ist als Stern vom Start zu jedem Ziel, Plan als eine Tour mit nummerierten Stopps.

Alle Zahlen kommen aus ``tk`` (``compare``, ``routing``); Vergleichsrechnungen sind beschriftet.
"""

from __future__ import annotations

import html
import os
from collections.abc import Callable
from typing import Any

from nicegui import run, ui

from tk.compare import (
    COMPARISON_NOTE,
    RelationDetail,
    VehicleOption,
    relation_detail,
    road_vs_air,
    tour_comparison,
    vehicle_options,
)
from tk.excelfn import fold, to_number
from tk.models import Assumptions, Result
from tk.routing import (
    ATTRIBUTION,
    ORSClient,
    RouteCache,
    RoutingUnavailable,
    relation_stops,
    road_distances,
    tour_waypoints,
)
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.map_view import MapView, bind_layer, relations, view_for
from tk.ui.theme import MAP_LINES, TOKENS

_cache: RouteCache | None = None


def route_cache() -> RouteCache:
    """Gemeinsamer Routen-Cache des Prozesses (``data/routes/routes.json``)."""
    global _cache
    if _cache is None:
        _cache = RouteCache()
    return _cache


def ors_client() -> ORSClient | None:
    if not os.environ.get("ORS_API_KEY"):
        return None
    try:
        return ORSClient()
    except RoutingUnavailable:
        return None


def _legend(items: list[tuple[str, str]]) -> None:
    with ui.row().classes("items-center gap-4 flex-wrap"):
        for key, text in items:
            color, dash = MAP_LINES[key]
            with ui.row().classes("items-center gap-1"):
                ui.html(
                    f'<svg width="36" height="10" aria-hidden="true"><line x1="0" y1="5" x2="36" y2="5" '
                    f'stroke="{color}" stroke-width="4" stroke-dasharray="{dash}"/></svg>'
                )
                ui.label(text).classes("tk-label")


def _new_map(result: Result | None, height: int = 460) -> tuple[ui.leaflet, tuple[tuple[float, float], int]]:
    center, zoom = (51.1, 10.2), 6
    if result is not None:
        rels = relations(result, "Ist")
        if rels:
            lats = [v for r in rels for v in (r.lat1, r.lat2)]
            lons = [v for r in rels for v in (r.lon1, r.lon2)]
            center, zoom = view_for([[min(lats), min(lons)], [max(lats), max(lons)]])
    m = ui.leaflet(center=center, zoom=zoom).classes("w-full").style(f"height:{height}px")
    return m, (center, zoom)


async def _settle(m: ui.leaflet, view: tuple[tuple[float, float], int] | None = None) -> None:
    """Leaflet nach dem Einblenden neu vermessen (Karte in verborgenem Tab hat Größe 0)."""
    await m.initialized()
    m.run_map_method("invalidateSize")
    if view is not None:
        m.run_map_method("setView", list(view[0]), view[1])


def options_table(options: list[VehicleOption]) -> None:
    rows = [
        {
            "f": ("gewählt: " if o.gewaehlt else "") + o.fahrzeug,
            "n": o.anzahl,
            "u": fmt.percent(o.auslastung, 0, False),
            "km": fmt.number(o.lkw_km, 1),
            "co2": fmt.number(o.co2_kg, 1),
            "k": fmt.number(o.kosten_eur, 2),
            "b": o.begruendung,
        }
        for o in options
    ]
    cols = [
        ("f", "Fahrzeug"), ("n", "Anzahl"), ("u", "Auslastung"), ("km", "Lkw-km"),
        ("co2", "CO₂e kg"), ("k", "Kosten €"), ("b", "Begründung"),
    ]  # fmt: skip
    table = (
        ui.table(
            columns=[
                {"name": c, "label": lab, "field": c, "align": "left" if c in ("f", "b") else "right"}
                for c, lab in cols
            ],
            rows=rows,
            row_key="f",
        )
        .props("dense flat hide-bottom wrap-cells")
        .classes("w-full")
    )
    table.add_slot(
        "body-cell-f",
        "<q-td :props=\"props\" :style=\"props.value.startsWith('gewählt') ? 'font-weight:600;color:var(--accent)' : ''\">"
        "{{ props.value }}</q-td>",
    )


def compare_table(rows: list[tuple[str, float, float, int, str]], plan_label: str) -> None:
    """Tabelle Kennzahl, Ist, Plan, Delta (Reduktion in Akzentfarbe, immer mit Vorzeichen)."""
    data = []
    for name, ist, plan, decimals, unit in rows:
        delta = None if ist == 0 else plan / ist - 1
        data.append(
            {
                "k": name,
                "ist": fmt.with_unit(ist, unit, decimals) if unit else fmt.number(ist, decimals),
                "plan": fmt.with_unit(plan, unit, decimals) if unit else fmt.number(plan, decimals),
                "d": fmt.percent(delta) if delta is not None else "",
            }
        )
    ui.table(
        columns=[
            {"name": "k", "label": "Kennzahl", "field": "k", "align": "left"},
            {"name": "ist", "label": "Ist", "field": "ist", "align": "right"},
            {"name": "plan", "label": plan_label, "field": "plan", "align": "right"},
            {"name": "d", "label": "Δ", "field": "d", "align": "right"},
        ],
        rows=data,
        row_key="k",
    ).props("dense flat hide-bottom").classes("w-full")


class DetailPanel:
    """Relationsdetail: Ist gegen Plan, beteiligte Touren, Begründung der Fahrzeugwahl."""

    def __init__(self, on_tour: Callable[[int], None]) -> None:
        self.on_tour = on_tour
        self.box = ui.column().classes("w-full gap-2")
        with self.box:
            components.empty_state(
                "Linie in einer Karte anklicken: Vergleich Ist gegen Plan für diese Relation."
            )

    def show(self, result: Result, key: str, scenario: str, params: Assumptions) -> None:
        d: RelationDetail = relation_detail(result, key, scenario)
        self.box.clear()
        with self.box:
            with ui.row().classes("w-full items-baseline justify-between"):
                ui.label(f"{d.start} > {d.ziel}").classes("tk-section")
                ui.label(
                    f"{d.sendungen} Sendungen, {fmt.with_unit(d.gewicht_t, 't', 1)}, Ø {fmt.with_unit(d.distanz_km, 'km', 1)} "
                    f"({d.distanzquelle})"
                ).classes("tk-label")
            ui.label(d.zusammenfassung)
            compare_table(
                [
                    ("Fahrten (Sammeltouren anteilig nach tkm)", d.ist.fahrten, d.plan.fahrten, 1, ""),
                    ("Lkw-km", d.ist.lkw_km, d.plan.lkw_km, 0, "km"),
                    ("CO₂e (Fzg-km)", d.ist.co2_kg, d.plan.co2_kg, 1, "kg"),
                    ("Kosten", d.ist.kosten_eur, d.plan.kosten_eur, 2, "€"),
                ],
                f"Plan {scenario}",
            )
            if scenario == "M3" and d.bahn:
                ui.label(
                    f"Bahn: {d.bahn} Sendungen über A01 = {fmt.number(params.a01_bahn_grenze_km)} km, "
                    f"Lkw nur im Vor- und Nachlauf ({fmt.number(params.a02_vnl_km)} km), Zusatzlaufzeit "
                    f"{fmt.number(params.a05_zusatz_tage)} Tag(e)."
                ).classes("tk-label")
            if d.touren:
                ui.label("Beteiligte Sammeltouren").classes("tk-section")
                shown, rest = d.touren[:8], d.touren[8:]

                def buttons(tours: list[Any]) -> None:
                    with ui.row().classes("gap-1 flex-wrap"):
                        for t in tours:
                            ui.button(
                                f"Tour {t.tour_nr}: {t.sendungen} Sendungen, {t.fahrzeug}",
                                on_click=lambda _e, n=t.tour_nr: self.on_tour(n),
                            ).props("outline dense no-caps color=primary")

                buttons(shown)
                if rest:
                    with ui.expansion(f"{len(rest)} weitere Touren").props("dense").classes("w-full"):
                        buttons(rest)
            ex = d.beispiel_sendung
            if ex is not None and ex.paletten is not None and ex.distanz_km is not None:
                kg = to_number(ex.shipment.gewicht_kg)
                ui.label("Warum dieses Fahrzeug?").classes("tk-section")
                ui.label(
                    f"Schwerste Sendung der Relation ({ex.shipment.sendungs_id or 'Zeile ' + str(ex.excel_row)}: "
                    f"{fmt.with_unit(kg, 'kg', 1)}, {fmt.number(ex.paletten)} Paletten) im Einzelversand. "
                    "Die Rangregel wählt das kleinste Fahrzeug, in das Gewicht und Paletten passen; mehrere kleine "
                    "Fahrzeuge fahren dieselbe Strecke mehrfach. Einen Pkw enthält die Flotte (Assumptions B1) nicht."
                ).classes("tk-label")
                options_table(vehicle_options(kg, ex.paletten, ex.distanz_km, params, result.c04))
                ui.label(COMPARISON_NOTE + "; gewählt ist die Variante der Excel.").classes("tk-label")


class RoadView:
    """Straße gegen Luftlinie: eine Karte, beide Linienarten, km-Tabelle und empirischer Faktor."""

    def __init__(self, result: Result, page: Any) -> None:
        self.page = page
        self.result = result
        self._layers: list[object] = []
        with ui.row().classes("w-full gap-4 no-wrap tk-two-col items-start"):
            with ui.column().classes("flex-1 min-w-0 gap-1"):
                self.map, self.view = _new_map(result)
                _legend(
                    [
                        ("luft", "Luftlinie (Rechnung: × I01)"),
                        ("strasse", "Straßenroute Lkw (ORS driving-hgv)"),
                    ]
                )
                ui.label(ATTRIBUTION).classes("tk-footer")
            with ui.column().classes("gap-2").style("width:420px;flex-shrink:0"):
                self.summary = ui.column().classes("w-full gap-1")
                self.table_box = ui.column().classes("w-full")

    async def settle(self) -> None:
        await _settle(self.map, self.view)

    def update(self, result: Result) -> None:
        self.result = result
        cache = route_cache()
        params = self.page.s.params
        for layer in self._layers:
            self.map.remove_layer(layer)  # type: ignore[arg-type]
        self._layers = []
        air_color, air_dash = MAP_LINES["luft"]
        road_color, _ = MAP_LINES["strasse"]
        pending: list[tuple[object, str, str]] = []
        for stop in relation_stops(result):
            a, b = stop.waypoints
            air = self.map.generic_layer(
                name="polyline",
                args=[[list(a), list(b)], {"color": air_color, "weight": 2, "dashArray": air_dash}],
            )
            self._layers.append(air)
            route = cache.get(stop.waypoints)
            tip = f"<b>{html.escape(stop.key)}</b>"
            if route is not None:
                road = self.map.generic_layer(
                    name="polyline",
                    args=[route.geometry, {"color": road_color, "weight": 3, "opacity": 0.85}],
                )
                self._layers.append(road)
                tip += f"<br>Straße {fmt.with_unit(route.distance_km, 'km', 1)}"
                if route.profile != "driving-hgv":
                    tip += " (Pkw-Profil: ORS kennt hier keine Lkw-Route)"
                pending.append((road, tip, stop.key))
            pending.append((air, tip, stop.key))

        async def bind() -> None:
            await self.map.initialized()
            for layer, tip, key in pending:
                bind_layer(layer, tip, key)

        ui.timer(0.1, bind, once=True)
        rows, total, median = road_vs_air(result, road_distances(result, cache), params)
        self.summary.clear()
        with self.summary:
            routed = sum(1 for r in rows if r.strasse_km is not None)
            if routed == 0:
                components.note(
                    "Noch keine Straßenrouten im Cache. ORS_API_KEY in .env eintragen und `make routes` ausführen "
                    "oder hier abrufen."
                )
            else:
                ui.label(
                    f"{routed} von {len(rows)} Relationen mit Straßenroute. Empirischer Straßenfaktor "
                    f"Σ Straße / Σ Luftlinie = {fmt.number(total, 3)} (Median {fmt.number(median, 3)}), "
                    f"Rechenannahme I01 = {fmt.number(params.i01_strassenfaktor, 2)}."
                )
            if routed < len(rows):
                ui.button("Fehlende Routen abrufen", on_click=self.fetch_missing).props(
                    "outline no-caps color=primary"
                ).set_enabled(ors_client() is not None)
        self.table_box.clear()
        with self.table_box:
            data = [
                {
                    "r": r.key,
                    "l": fmt.number(r.luftlinie_km, 1),
                    "n": fmt.number(r.naeherung_km, 1),
                    "s": fmt.number(r.strasse_km, 1) if r.strasse_km is not None else "",
                    "f": fmt.number(r.faktor, 2) if r.faktor is not None else "",
                }
                for r in rows
            ]
            ui.table(
                columns=[
                    {"name": "r", "label": "Relation", "field": "r", "align": "left", "sortable": True},
                    {"name": "l", "label": "Luftlinie km", "field": "l", "align": "right"},
                    {"name": "n", "label": "× I01 km", "field": "n", "align": "right"},
                    {"name": "s", "label": "Straße km", "field": "s", "align": "right"},
                    {"name": "f", "label": "Faktor", "field": "f", "align": "right"},
                ],
                rows=data,
                row_key="r",
                pagination={"rowsPerPage": 12},
            ).props("dense flat wrap-cells").classes("w-full")

    async def fetch_missing(self) -> None:
        client = ors_client()
        if client is None:
            ui.notify("ORS_API_KEY fehlt in .env", type="warning")
            return
        cache = route_cache()
        todo = [s for s in relation_stops(self.result) if cache.get(s.waypoints) is None]
        ui.notify(f"Rufe {len(todo)} Routen ab (etwa {len(todo) * 2} s)")

        def work() -> str:
            for s in todo:
                cache.get_or_fetch(s.waypoints, client, [s.key])
            return f"{len(todo)} Routen gespeichert"

        try:
            ui.notify(await run.io_bound(work), type="positive")
        except RoutingUnavailable as exc:
            ui.notify(f"Abruf abgebrochen: {exc}", type="negative")
        self.update(self.result)
        self.page.refresh_road_toggle()


class TourView:
    """Tourvergleich: Ist als Einzelfahrten (Stern), Plan als Sammeltour mit Stopps."""

    def __init__(self, result: Result, page: Any) -> None:
        self.page = page
        self.result = result
        self._layers: list[object] = []
        with ui.row().classes("w-full items-center gap-2"):
            self.select = (
                ui.select({}, label="Tour", on_change=lambda e: self.show(e.value))
                .props("dense outlined")
                .style("min-width:360px")
            )
            ui.label(
                "Gebündelte Touren zuerst; Reihenfolge der Stopps nur zur Darstellung (nächster Nachbar)."
            ).classes("tk-label")
        with ui.row().classes("w-full gap-4 no-wrap tk-two-col items-start"):
            with ui.column().classes("flex-1 min-w-0 gap-1"):
                self.map, self.view = _new_map(result)
                _legend(
                    [
                        ("ist", "Ist: je Ziel eine Einzelfahrt"),
                        ("lkw", "Plan: Sammeltour"),
                        ("luft", "Plan schematisch (keine Straßenroute im Cache)"),
                    ]
                )
            with ui.column().classes("gap-2").style("width:460px;flex-shrink:0"):
                self.side = ui.column().classes("w-full gap-2")
        self.below = ui.column().classes("w-full gap-2")

    async def settle(self) -> None:
        await _settle(self.map)

    def update(self, result: Result) -> None:
        self.result = result
        tours = sorted(result.tours, key=lambda t: (-t.gebuendelt, t.tour_nr))
        options = {
            t.tour_nr: f"Tour {t.tour_nr}: {t.start}, {t.sendungen} Sendungen, "
            f"{t.fahrzeug if t.gebuendelt else 'nicht gebündelt'}"
            for t in tours
        }
        self.select.set_options(options)
        current = self.select.value if self.select.value in options else (tours[0].tour_nr if tours else None)
        self.select.set_value(current)
        if current is not None:
            self.show(current)
        else:
            self.side.clear()
            with self.side:
                components.empty_state("Keine Touren: keine bündelbaren Sendungen.")

    def show(self, tour_nr: int | None) -> None:
        if tour_nr is None:
            return
        result = self.result
        tour = next((t for t in result.tours if t.tour_nr == tour_nr), None)
        if tour is None:
            return
        params = self.page.s.params
        comp = tour_comparison(result, tour, params)
        points, labels = tour_waypoints(result, tour_nr)
        for layer in self._layers:
            self.map.remove_layer(layer)  # type: ignore[arg-type]
        self._layers = []
        route = route_cache().get(points) if len(points) >= 2 else None
        if points:
            start = points[0]
            per_stop: dict[str, int] = {}
            for row in comp.sendungen:
                per_stop[fold(row.ziel_label or "")] = per_stop.get(fold(row.ziel_label or ""), 0) + 1
            ist_color, _ = MAP_LINES["ist"]
            for name, p in zip(labels[1:], points[1:], strict=True):
                n = per_stop.get(fold(name), 1)
                self._layers.append(
                    self.map.generic_layer(
                        name="polyline",
                        args=[
                            [list(start), list(p)],
                            {"color": ist_color, "weight": 1.5 + 2 * n, "opacity": 0.6},
                        ],
                    )
                )
            if route is not None:
                color, _ = MAP_LINES["lkw"]
                plan_layer = self.map.generic_layer(
                    name="polyline", args=[route.geometry, {"color": color, "weight": 4}]
                )
            else:
                color, dash = MAP_LINES["luft"]
                plan_layer = self.map.generic_layer(
                    name="polyline",
                    args=[[list(p) for p in points], {"color": color, "weight": 3, "dashArray": dash}],
                )
            self._layers.append(plan_layer)
            markers = []
            for i, (name, p) in enumerate(zip(labels, points, strict=True)):
                marker = self.map.generic_layer(
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
                self._layers.append(marker)

            async def bind() -> None:
                await self.map.initialized()
                for marker, text in markers:
                    marker.run_method("bindTooltip", text, {"permanent": True, "direction": "right"})
                lats = [p[0] for p in points]
                lons = [p[1] for p in points]
                self.map.run_map_method(
                    "fitBounds", [[min(lats), min(lons)], [max(lats), max(lons)]], {"padding": [40, 40]}
                )

            ui.timer(0.2, bind, once=True)
        self.side.clear()
        with self.side:
            ui.label(f"Tour {tour.tour_nr}, Start {tour.start}").classes("tk-section")
            ui.label(comp.ergebnis)
            plan_km_label = "Plan (Tour)" if tour.gebuendelt else "Plan (bleibt einzeln)"
            plan = (
                (tour.lkw_km, tour.co2, tour.kosten, 1.0)
                if tour.gebuendelt
                else (comp.einzel_km, comp.einzel_co2, comp.einzel_kosten, float(comp.einzel_fahrzeuge))
            )
            compare_table(
                [
                    ("Fahrten", float(comp.einzel_fahrzeuge), plan[3], 0, ""),
                    ("Lkw-km (Modell)", comp.einzel_km, plan[0], 1, "km"),
                    ("CO₂e (Fzg-km)", comp.einzel_co2, plan[1], 1, "kg"),
                    ("Kosten", comp.einzel_kosten, plan[2], 2, "€"),
                ],
                plan_km_label,
            )
            model_km = (
                f"Modell-Tourstrecke: längste Distanz {fmt.with_unit(tour.max_distanz_km, 'km', 1)} × (1 + A10 × "
                f"({tour.stopps} Stopps − 1)) = {fmt.with_unit(tour.lkw_km, 'km', 1)}."
            )
            ui.label(model_km).classes("tk-label")
            if route is not None:
                ui.label(
                    f"Straßenroute über alle Stopps: {fmt.with_unit(route.distance_km, 'km', 1)} "
                    f"({fmt.percent(route.distance_km / tour.lkw_km - 1)} gegen Modell; Darstellung, nicht Rechengrundlage)."
                ).classes("tk-label")
            elif ors_client() is not None:
                ui.button("Straßenroute dieser Tour abrufen", on_click=lambda: self.fetch(tour_nr)).props(
                    "outline dense no-caps color=primary"
                )
            ui.label("Bündelungsbedingungen (Touren AI)").classes("tk-section")
            for c in comp.bedingungen:
                ui.label(f"{'erfüllt' if c.erfuellt else 'nicht erfüllt'}: {c.name} ({c.wert})").classes(
                    "tk-success" if c.erfuellt else "tk-error"
                )
        self.below.clear()
        with self.below:
            ui.label("Warum dieses Fahrzeug für die Tour?").classes("tk-section")
            ui.label(
                f"Tourladung {fmt.with_unit(tour.gewicht_kg, 'kg', 1)} und {fmt.number(tour.paletten)} Paletten. "
                "Kleinere Fahrzeuge müssten die Tour mehrfach fahren."
            ).classes("tk-label")
            options_table(comp.optionen)
            ui.label(COMPARISON_NOTE + "; gewählt ist die Variante der Excel.").classes("tk-label")

    async def fetch(self, tour_nr: int) -> None:
        client = ors_client()
        points, labels = tour_waypoints(self.result, tour_nr)
        if client is None or len(points) < 2:
            return
        try:
            await run.io_bound(route_cache().get_or_fetch, points, client, labels)
        except RoutingUnavailable as exc:
            ui.notify(f"Abruf nicht möglich: {exc}", type="negative")
        self.show(tour_nr)


class MapArea:
    """Tabs Vorher/Nachher, Straße gegen Luftlinie, Touren; darunter das Relationsdetail."""

    def __init__(self, page: Any, result: Result) -> None:
        self.page = page
        self.result = result
        self.scenario = page.s.scenario
        with ui.tabs().props("dense no-caps align=left").classes("w-full") as tabs:
            self.t_map = ui.tab("Vorher / Nachher")
            self.t_road = ui.tab("Straße gegen Luftlinie")
            self.t_tour = ui.tab("Touren")
        self.panels = (
            ui.tab_panels(tabs, value=self.t_map, on_change=self._tab_changed)
            .classes("w-full")
            .props("animated=false keep-alive")
        )
        with self.panels:
            with ui.tab_panel(self.t_map).classes("p-0 pt-2"):
                self.compare = MapView(result)
            with ui.tab_panel(self.t_road).classes("p-0 pt-2"):
                self.road = RoadView(result, page)
            with ui.tab_panel(self.t_tour).classes("p-0 pt-2"):
                self.tours = TourView(result, page)
        ui.separator().classes("my-2")
        self.detail = DetailPanel(self.open_tour)
        self._selected: str | None = None

    async def _tab_changed(self, _e: Any) -> None:
        if self.panels.value == self.t_road or self.panels.value == "Straße gegen Luftlinie":
            await self.road.settle()
        elif self.panels.value == self.t_tour or self.panels.value == "Touren":
            await self.tours.settle()

    async def probe_tiles(self) -> None:
        await self.compare.probe_tiles()

    async def settle(self) -> None:
        """Nach dem Einblenden des umgebenden Tabs alle sichtbaren Karten neu vermessen."""
        if self.compare.mode.value != "netz":
            for m in (self.compare.map_left, self.compare.map_right):
                await _settle(m)
        await self._tab_changed(None)

    def update(self, result: Result, scenario: str) -> None:
        self.result, self.scenario = result, scenario
        self.compare.update(result, scenario)
        self.road.update(result)
        self.tours.update(result)
        if self._selected:
            self.select_relation(self._selected)

    def select_relation(self, key: str) -> None:
        self._selected = key
        if any(fold(r.relation or "") == fold(key) for r in self.result.valid_rows):
            self.detail.show(self.result, key, self.scenario, self.page.s.params)

    def open_tour(self, tour_nr: int) -> None:
        self.panels.set_value(self.t_tour)
        self.tours.select.set_value(tour_nr)
        self.tours.show(tour_nr)
