"""Routing-Cache und ORS-Client ohne Netz (httpx.MockTransport mit ORS-Antwortformat)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tk.routing import (
    ORSClient,
    RouteCache,
    RouteNotFound,
    RoutingUnavailable,
    nearest_neighbor_order,
    parse_ors_geojson,
    route_key,
    simplify,
)

# Aufbau wie eine Antwort von /v2/directions/driving-hgv/geojson (gekürzt).
ORS_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"summary": {"distance": 190512.3, "duration": 8123.4}},
            "geometry": {
                "type": "LineString",
                "coordinates": [[9.18, 48.77], [8.9, 49.3], [8.6, 49.6], [8.27, 50.0]],
            },
        }
    ],
}
WAYPOINTS = [(48.77265, 9.18), (50.001, 8.2688)]


def client_with(responses: list[httpx.Response], sleeps: list[float]) -> ORSClient:
    it = iter(responses)
    transport = httpx.MockTransport(lambda request: next(it))
    return ORSClient(api_key="test", http=httpx.Client(transport=transport), sleep=sleeps.append)


def test_parse_ors_response() -> None:
    route = parse_ors_geojson(ORS_RESPONSE, WAYPOINTS)
    assert route.distance_km == pytest.approx(190.5123)
    assert route.duration_h == pytest.approx(8123.4 / 3600)
    assert route.geometry[0] == [48.77, 9.18] and route.geometry[-1] == [50.0, 8.27]


def test_client_retries_on_429_and_sends_lonlat() -> None:
    sent: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        assert request.headers["Authorization"] == "test"
        assert request.url.path.endswith("/driving-hgv/geojson")
        return httpx.Response(429) if len(sent) == 1 else httpx.Response(200, json=ORS_RESPONSE)

    sleeps: list[float] = []
    client = ORSClient(
        api_key="test", http=httpx.Client(transport=httpx.MockTransport(handler)), sleep=sleeps.append
    )
    route = client.route(WAYPOINTS)
    assert route.distance_km == pytest.approx(190.5123)
    assert sent[0]["coordinates"] == [[9.18, 48.77265], [8.2688, 50.001]]
    assert sent[0]["radiuses"] == [5000, 5000]
    assert 10 in sleeps


def test_client_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORS_API_KEY", raising=False)
    with pytest.raises(RoutingUnavailable):
        ORSClient()


def test_route_not_found_is_skippable() -> None:
    body = '{"error":{"code":2009,"message":"Route could not be found"}}'
    client = client_with([httpx.Response(404, text=body)], [])
    with pytest.raises(RouteNotFound):
        client.route(WAYPOINTS)


def test_fallback_to_car_profile(tmp_path: Path) -> None:
    body = '{"error":{"code":2009,"message":"Route could not be found"}}'
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return (
            httpx.Response(404, text=body)
            if "hgv" in request.url.path
            else httpx.Response(200, json=ORS_RESPONSE)
        )

    client = ORSClient(
        api_key="test", http=httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _s: None
    )
    cache = RouteCache(tmp_path / "r.json")
    route = cache.get_or_fetch(WAYPOINTS, client)
    assert route is not None and route.profile == "driving-car"
    assert cache.get(WAYPOINTS) is route  # unter dem Lkw-Schlüssel abgelegt, Profil sichtbar
    assert paths[0].endswith("driving-hgv/geojson") and paths[1].endswith("driving-car/geojson")


def test_error_status_is_reported() -> None:
    client = client_with([httpx.Response(403, text="key invalid")], [])
    with pytest.raises(RoutingUnavailable, match="403"):
        client.route(WAYPOINTS)


def test_cache_round_trip_and_offline_hit(tmp_path: Path) -> None:
    path = tmp_path / "routes.json"
    cache = RouteCache(path)
    client = client_with([httpx.Response(200, json=ORS_RESPONSE)], [])
    first = cache.get_or_fetch(WAYPOINTS, client, ["Stuttgart > Mainz"])
    assert first is not None and path.exists()
    again = RouteCache(path)
    hit = again.get_or_fetch(WAYPOINTS, None)
    assert hit is not None and hit.distance_km == first.distance_km and hit.labels == ["Stuttgart > Mainz"]
    assert again.get([(1.0, 1.0), (2.0, 2.0)]) is None
    assert route_key(WAYPOINTS).startswith("driving-hgv:48.77265,9.18000")


def test_simplify_keeps_ends() -> None:
    line = [[0.0, float(i) / 100] for i in range(101)]
    out = simplify(line)
    assert out[0] == line[0] and out[-1] == line[-1] and len(out) == 2


def test_nearest_neighbor_order() -> None:
    order = nearest_neighbor_order((48.0, 9.0), [("weit", (52.0, 13.0)), ("nah", (48.5, 9.1))])
    assert [n for n, _ in order] == ["nah", "weit"]
