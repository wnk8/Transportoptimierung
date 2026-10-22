"""Straßenrouten über OpenRouteService (Profil driving-hgv) mit lokalem Cache.

Nicht Teil des Rechenkerns: Die Standardrechnung nutzt Luftlinie mal I01 wie die Excel.
Straßenrouten dienen der Darstellung und der optionalen Variante "Straßen-km" über die
Relationstabelle (Input X, PLZ_Orte R:T).

Dienst: https://api.openrouteservice.org/v2/directions/driving-hgv/geojson
Schlüssel nur aus ``ORS_API_KEY`` (lokal ``.env``). Limits des kostenlosen Standard-Plans laut
openrouteservice.org (geprüft 20.10.2026): Directions 2.000 je Tag, 40 je Minute. Der Client
wartet deshalb mindestens 1,6 s zwischen zwei Anfragen und wiederholt bei HTTP 429.
Routendaten: © openrouteservice.org by HeiGIT, Kartendaten © OpenStreetMap contributors (ODbL).
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import httpx

from tk.excelfn import fold
from tk.models import Result
from tk.scenarios import Model
from tk.workbook import DATA

ORS_URL = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"
PROFILE = "driving-hgv"
FALLBACK_PROFILE = "driving-car"
"""Rückfall, wenn das Lkw-Netz von ORS keine Route kennt (Fehler 2009, etwa Freiburg, 22.10.2026)."""
MIN_INTERVAL_S = 1.6
CACHE_FILE = DATA / "routes" / "routes.json"
ATTRIBUTION = "Routen: © openrouteservice.org by HeiGIT, Daten © OpenStreetMap contributors (ODbL)"
SNAP_RADIUS_M = 5000
"""Fangradius je Wegpunkt: PLZ-Schwerpunkte liegen oft abseits Lkw-tauglicher Straßen (ORS-Standard 350 m)."""
SIMPLIFY_DEG = 0.0005
"""Toleranz der Linienvereinfachung (etwa 50 m); nur Darstellung."""

LatLon = tuple[float, float]


class RoutingUnavailable(RuntimeError):
    """Kein Schlüssel, kein Netz oder Dienstfehler."""


class RouteNotFound(RoutingUnavailable):
    """ORS findet zwischen den Wegpunkten keine Route (Fehler 2009 bzw. 2010); andere Routen gehen weiter."""


@dataclass(slots=True)
class RoadRoute:
    """Eine Straßenroute über zwei oder mehr Wegpunkte."""

    waypoints: list[list[float]]  # [[lat, lon], ...]
    distance_km: float
    duration_h: float
    geometry: list[list[float]]  # [[lat, lon], ...], vereinfacht
    service: str = "openrouteservice"
    profile: str = PROFILE
    abgerufen: str = ""
    lizenz: str = ATTRIBUTION
    labels: list[str] = field(default_factory=list)


def route_key(waypoints: Sequence[LatLon], profile: str = PROFILE) -> str:
    """Cache-Schlüssel aus Profil und Wegpunkten (5 Nachkommastellen, etwa 1 m)."""
    return profile + ":" + ";".join(f"{lat:.5f},{lon:.5f}" for lat, lon in waypoints)


def simplify(points: list[list[float]], tolerance: float = SIMPLIFY_DEG) -> list[list[float]]:
    """Douglas-Peucker in Grad; erhält Anfangs- und Endpunkt."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (y1, x1), (y2, x2) = points[a], points[b]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-12
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            y, x = points[i]
            dist = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
            if dist > best:
                best, idx = dist, i
        if best > tolerance and idx > 0:
            keep[idx] = True
            stack.extend([(a, idx), (idx, b)])
    return [p for p, k in zip(points, keep, strict=True) if k]


def parse_ors_geojson(data: dict[str, Any], waypoints: Sequence[LatLon]) -> RoadRoute:
    """Antwort von ORS (GeoJSON) in eine :class:`RoadRoute`."""
    feature = data["features"][0]
    summary = feature["properties"]["summary"]
    coords = feature["geometry"]["coordinates"]  # [lon, lat]
    geometry = [[float(lat), float(lon)] for lon, lat, *_ in coords]
    return RoadRoute(
        waypoints=[[lat, lon] for lat, lon in waypoints],
        distance_km=float(summary.get("distance", 0.0)) / 1000,
        duration_h=float(summary.get("duration", 0.0)) / 3600,
        geometry=simplify(geometry),
        abgerufen=dt.date.today().isoformat(),
    )


class ORSClient:
    """Minimaler Client für ORS Directions mit Drosselung und Wiederholung bei 429."""

    def __init__(
        self,
        api_key: str | None = None,
        profile: str = PROFILE,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        retries: int = 3,
    ) -> None:
        key = api_key or os.environ.get("ORS_API_KEY", "")
        if not key:
            raise RoutingUnavailable("ORS_API_KEY ist nicht gesetzt (.env)")
        self._key = key
        self.profile = profile
        self._http = http or httpx.Client(timeout=30)
        self._sleep = sleep
        self._retries = retries
        self._last = 0.0

    def route_with_fallback(self, waypoints: Sequence[LatLon]) -> RoadRoute:
        """Lkw-Route; findet ORS keine, die Pkw-Route (``profile`` der Route zeigt das an)."""
        try:
            return self.route(waypoints)
        except RouteNotFound:
            car = ORSClient(api_key=self._key, profile=FALLBACK_PROFILE, http=self._http, sleep=self._sleep)
            car._last = self._last
            route = car.route(waypoints)
            self._last = car._last
            return route

    def route(self, waypoints: Sequence[LatLon]) -> RoadRoute:
        wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
        if wait > 0:
            self._sleep(wait)
        body = {
            "coordinates": [[lon, lat] for lat, lon in waypoints],
            "radiuses": [SNAP_RADIUS_M] * len(waypoints),
            "instructions": False,
        }
        headers = {"Authorization": self._key, "Content-Type": "application/json"}
        url = ORS_URL.format(profile=self.profile)
        for attempt in range(self._retries + 1):
            try:
                resp = self._http.post(url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                raise RoutingUnavailable(f"Netzfehler: {exc}") from exc
            finally:
                self._last = time.monotonic()
            if resp.status_code == 429 and attempt < self._retries:
                self._sleep(10 * 2**attempt)
                continue
            if resp.status_code == 404 and any(code in resp.text for code in ('"code":2009', '"code":2010')):
                raise RouteNotFound(f"keine Route: {resp.text[:160]}")
            if resp.status_code != 200:
                raise RoutingUnavailable(f"ORS antwortet {resp.status_code}: {resp.text[:200]}")
            route = parse_ors_geojson(resp.json(), waypoints)
            route.profile = self.profile
            return route
        raise RoutingUnavailable("ORS: Ratenlimit")


class RouteCache:
    """Routen als JSON-Datei (``data/routes/routes.json``), lesbar ohne Netz."""

    def __init__(self, path: Path = CACHE_FILE) -> None:
        self.path = path
        self._routes: dict[str, RoadRoute] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            self._routes = {k: RoadRoute(**v) for k, v in raw.get("routes", {}).items()}

    def __len__(self) -> int:
        return len(self._routes)

    def get(self, waypoints: Sequence[LatLon], profile: str = PROFILE) -> RoadRoute | None:
        return self._routes.get(route_key(waypoints, profile))

    def put(self, route: RoadRoute, profile: str = PROFILE) -> None:
        """Speichert unter dem angefragten Profil; ``route.profile`` nennt das tatsächlich genutzte."""
        self._routes[route_key([(p[0], p[1]) for p in route.waypoints], profile)] = route

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"hinweis": ATTRIBUTION, "routes": {k: asdict(v) for k, v in self._routes.items()}}
        self.path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def get_or_fetch(
        self, waypoints: Sequence[LatLon], client: ORSClient | None, labels: Sequence[str] = ()
    ) -> RoadRoute | None:
        """Route aus dem Cache; fehlt sie und ist ein Client da, wird sie abgerufen und gespeichert."""
        hit = self.get(waypoints)
        if hit is not None or client is None:
            return hit
        route = client.route_with_fallback(waypoints)
        route.labels = list(labels)
        self.put(route)
        self.save()
        return route


def nearest_neighbor_order(start: LatLon, stops: Sequence[tuple[str, LatLon]]) -> list[tuple[str, LatLon]]:
    """Reihenfolge der Stopps für die Darstellung einer Tour: jeweils der nächste Stopp.

    Das Rechenmodell legt keine Reihenfolge fest (Tour-km = längste Distanz mal Umwegzuschlag);
    diese Reihenfolge ist nur Darstellung.
    """
    rest = list(stops)
    order: list[tuple[str, LatLon]] = []
    here = start
    while rest:
        nxt = min(
            rest,
            key=lambda s: math.hypot(
                s[1][0] - here[0], (s[1][1] - here[1]) * math.cos(math.radians(here[0]))
            ),
        )
        order.append(nxt)
        rest.remove(nxt)
        here = nxt[1]
    return order


@dataclass(slots=True)
class RelationStop:
    """Eine Relation mit Schlüsseln (Input K, Q) und Koordinaten (O, P, U, V)."""

    key: str
    start_key: str
    ziel_key: str
    waypoints: list[LatLon]


def relation_stops(result: Result) -> list[RelationStop]:
    """Alle Relationen der gültigen Sendungen mit Koordinaten, in der Reihenfolge des Auftretens."""
    seen: dict[str, RelationStop] = {}
    for r in result.valid_rows:
        if None in (r.start_lat, r.start_lon, r.ziel_lat, r.ziel_lon) or not r.relation:
            continue
        k = fold(r.relation)
        if k not in seen:
            seen[k] = RelationStop(
                key=r.relation,
                start_key=r.start_key or "",
                ziel_key=r.ziel_key or "",
                waypoints=[(r.start_lat or 0.0, r.start_lon or 0.0), (r.ziel_lat or 0.0, r.ziel_lon or 0.0)],
            )
    return list(seen.values())


def tour_waypoints(result: Result, tour_nr: int) -> tuple[list[LatLon], list[str]]:
    """Wegpunkte einer Tour: Start, dann die Ziele nach "nächster Nachbar" (nur Darstellung)."""
    lines = [line for line in result.tour_lines if line.tour_nr == tour_nr]
    rows = [result.rows[line.input_pos - 1] for line in lines]
    if not rows or rows[0].start_lat is None or rows[0].start_lon is None:
        return [], []
    start = (rows[0].start_lat, rows[0].start_lon)
    stops: dict[str, LatLon] = {}
    for r in rows:
        if r.ziel_lat is not None and r.ziel_lon is not None and r.ziel_label:
            stops.setdefault(fold(r.ziel_label), (r.ziel_lat, r.ziel_lon))
    labels = {fold(r.ziel_label or ""): r.ziel_label or "" for r in rows}
    order = nearest_neighbor_order(start, [(labels[k], p) for k, p in stops.items()])
    return [start, *[p for _, p in order]], [rows[0].start_label or "", *[n for n, _ in order]]


def road_distances(result: Result, cache: RouteCache) -> dict[str, float]:
    """Straßen-km je Relation (Schlüssel in Kleinschreibung) aus dem Cache."""
    out = {}
    for stop in relation_stops(result):
        route = cache.get(stop.waypoints)
        if route is not None:
            out[fold(stop.key)] = route.distance_km
    return out


def with_road_km(model: Model, result: Result, cache: RouteCache) -> tuple[Model, int]:
    """Variante "Straßen-km": Straßenrouten als Einträge der Relationstabelle (PLZ_Orte R:T).

    Die Excel kennt diesen Weg (Input X, Quelle "Relationstabelle"); eingetragene eigene
    Entfernungen der Nutzer haben Vorrang, weil die Suche den ersten Treffer nimmt.
    Rückgabe: neues Modell und Anzahl der ergänzten Relationen.
    """
    keys = list(model.db.rel_keys)
    kms = list(model.db.rel_km)
    added = 0
    for stop in relation_stops(result):
        route = cache.get(stop.waypoints)
        if route is None or not stop.start_key or not stop.ziel_key:
            continue
        keys.append(f"{stop.start_key}|{stop.ziel_key}")
        kms.append(round(route.distance_km, 3))
        added += 1
    db = replace(model.db, rel_keys=keys, rel_km=kms)
    return Model(params=model.params, db=db, capacity=model.capacity), added


def relation_table_csv(result: Result, cache: RouteCache) -> str:
    """Relationstabelle zum Einfügen in PLZ_Orte R:T (Start;Ziel;Straßenentfernung km)."""
    lines = ["Start;Ziel;Straßenentfernung km"]
    for stop in relation_stops(result):
        route = cache.get(stop.waypoints)
        if route is not None:
            lines.append(f"{stop.start_key};{stop.ziel_key};{route.distance_km:.3f}".replace(".", ","))
    return "\r\n".join(lines) + "\r\n"
