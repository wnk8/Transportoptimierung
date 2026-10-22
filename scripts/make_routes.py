"""Straßenrouten (OpenRouteService, driving-hgv) für die Beispieldaten vorab abrufen.

Ruft je Relation und je gebündelter Tour eine Route ab und speichert sie in
``data/routes/routes.json``. Bereits gespeicherte Routen werden übersprungen. Der Schlüssel
kommt aus ``ORS_API_KEY`` (``.env``). Drosselung 1,6 s je Anfrage (Limit 40 je Minute).

Usage: ``uv run python scripts/make_routes.py [--nur-relationen]``
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from tk.routing import (
    ORSClient,
    RouteCache,
    RouteNotFound,
    RoutingUnavailable,
    relation_stops,
    tour_waypoints,
)
from tk.scenarios import calculate, load_model, workbook_shipments
from tk.workbook import load_workbook_data


def main() -> int:
    load_dotenv()
    try:
        client = ORSClient()
    except RoutingUnavailable as exc:
        print(f"Abbruch: {exc}")
        return 2
    data = load_workbook_data()
    model = load_model(data)
    result = calculate(workbook_shipments(data), model)
    cache = RouteCache()
    jobs: list[tuple[str, list[tuple[float, float]], list[str]]] = [
        (f"Relation {s.key}", s.waypoints, [s.key]) for s in relation_stops(result)
    ]
    if "--nur-relationen" not in sys.argv:
        for tour in result.tours:
            if tour.gebuendelt:
                points, labels = tour_waypoints(result, tour.tour_nr)
                if len(points) >= 2:
                    jobs.append((f"Tour {tour.tour_nr}", points, labels))
    todo = [j for j in jobs if cache.get(j[1]) is None]
    print(f"{len(jobs)} Routen, davon {len(todo)} neu abzurufen (etwa {len(todo) * 1.6 / 60:.0f} min).")
    skipped: list[str] = []
    for i, (name, points, labels) in enumerate(todo, start=1):
        try:
            route = cache.get_or_fetch(points, client, labels)
        except RouteNotFound as exc:
            print(f"[{i}/{len(todo)}] {name}: übersprungen ({exc})")
            skipped.append(name)
            continue
        except RoutingUnavailable as exc:
            print(f"{name}: {exc}")
            cache.save()
            return 1
        if route is not None:
            print(f"[{i}/{len(todo)}] {name}: {route.distance_km:.1f} km")
    cache.save()
    print(f"Gespeichert: {cache.path} ({len(cache)} Routen), übersprungen: {len(skipped)}")
    for name in skipped:
        print(f"  ohne Route: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
