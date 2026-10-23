"""Vergleichsrechnungen für die Karte: Fahrzeugalternativen, Tourentscheidung, Relation Ist gegen Plan.

Alle Werte entstehen mit den Funktionen des Rechenkerns. Die Alternativen (andere
Fahrzeugklassen, mehrere kleine Fahrzeuge) sind Vergleichsrechnungen und nicht Teil der
Excel; die gewählte Variante ist immer die der Excel (Rangregel K2.5, Bündelung K2.15).
"""

from __future__ import annotations

import copy
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field

from tk import costs, emissions
from tk.bundling import assign_groups, build_tours
from tk.excelfn import fold, roundup0, to_number
from tk.models import Assumptions, Result, ShipmentRow, Tour, TourLine
from tk.routing import nearest_neighbor_order
from tk.vehicle import pick_vehicle

COMPARISON_NOTE = "Vergleichsrechnung, nicht Teil der Excel"


@dataclass(slots=True)
class VehicleOption:
    """Eine Fahrzeugklasse für eine Ladung."""

    fahrzeug: str
    anzahl: int
    auslastung: float
    lkw_km: float
    co2_kg: float
    kosten_eur: float
    gewaehlt: bool
    begruendung: str


def vehicle_options(
    gewicht_kg: float,
    paletten: float,
    distanz_km: float,
    params: Assumptions,
    c04: float,
) -> list[VehicleOption]:
    r"""Alle Fahrzeugklassen für eine Ladung über eine Strecke.

    Je Klasse: :math:`n_v = \max(1, \lceil p/p_v\rceil, \lceil kg/kg_v\rceil)`, Lkw-km
    :math:`d\,n_v`, CO₂e nach K2.8, Kosten Modell mal C04. Die gewählte Klasse folgt der
    Rangregel der Excel (kleinste passende Klasse, bei mehreren Fahrzeugen die größte).
    """
    chosen = pick_vehicle(gewicht_kg, paletten, distanz_km, params)
    out = []
    for rank, v in enumerate(params.vehicles, start=1):
        n = max(1, roundup0(paletten / v.paletten), roundup0(gewicht_kg / v.nutzlast_kg))
        km = distanz_km * n
        util = max(gewicht_kg / n / v.nutzlast_kg, paletten / n / v.paletten)
        selected = rank == chosen.rang
        if selected and chosen.fahrzeuge_n > 1:
            reason = (
                f"gewählt: Ladung braucht {chosen.fahrzeuge_n} Fahrzeuge, dann gilt das größte (K2.4, K2.5)"
            )
        elif selected:
            reason = "gewählt: kleinstes Fahrzeug, in das Gewicht und Paletten passen (Rangregel K2.5)"
        elif rank < chosen.rang:
            limits = []
            if paletten > v.paletten:
                limits.append(f"Paletten {_n(paletten)} > {_n(v.paletten)}")
            if gewicht_kg > v.nutzlast_kg:
                limits.append(f"Gewicht {_n(gewicht_kg)} kg > {_n(v.nutzlast_kg)} kg")
            reason = "passt nicht in ein Fahrzeug (" + ", ".join(limits) + f"), bräuchte {n}"
        else:
            reason = "passt, aber größer als nötig: höherer Verbrauch und Kostensatz je km"
        out.append(
            VehicleOption(
                fahrzeug=v.name,
                anzahl=n,
                auslastung=util,
                lkw_km=km,
                co2_kg=emissions.co2_fzgkm(km, gewicht_kg, n, v, params),
                kosten_eur=costs.model_cost(km, v) * c04,
                gewaehlt=selected,
                begruendung=reason,
            )
        )
    return out


def _n(x: float) -> str:
    return (
        f"{x:,.0f}".replace(",", ".")
        if x == int(x)
        else f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )


@dataclass(slots=True)
class Condition:
    name: str
    wert: str
    erfuellt: bool


@dataclass(slots=True)
class TourComparison:
    tour: Tour
    sendungen: list[ShipmentRow]
    einzel_fahrzeuge: int
    einzel_km: float
    einzel_co2: float
    einzel_kosten: float
    bedingungen: list[Condition]
    optionen: list[VehicleOption]
    ergebnis: str


def tour_members(result: Result, tour_nr: int) -> list[tuple[TourLine, ShipmentRow]]:
    return [(line, result.rows[line.input_pos - 1]) for line in result.tour_lines if line.tour_nr == tour_nr]


def tour_comparison(result: Result, tour: Tour, params: Assumptions) -> TourComparison:
    """Einzelversand der Tour-Sendungen gegen Sammeltour (Touren U bis AI) mit Begründung.

    Die vier Bedingungen sind die der Excel (K2.15). Die Fahrzeugalternativen rechnen die
    Tourladung mit jeder Klasse über die Tourstrecke (Vergleichsrechnung).
    """
    members = tour_members(result, tour.tour_nr)
    rows = [row for _, row in members]
    tol = params.a08_kosten_tol
    cond = [
        Condition("mindestens 2 Sendungen", f"{tour.sendungen} Sendungen", tour.sendungen >= 2),
        Condition(
            f"eine Sendung schlechter ausgelastet als A09 = {params.a09_schwelle:.0%}".replace(".", ","),
            f"kleinste Auslastung {tour.min_auslastung:.1%}".replace(".", ","),
            tour.min_auslastung < params.a09_schwelle,
        ),
        Condition(
            "CO₂e der Tour kleiner als Σ Einzelfahrten",
            f"{tour.co2:,.1f} kg gegen {tour.co2_einzel:,.1f} kg".replace(",", "X")
            .replace(".", ",")
            .replace("X", "."),
            tour.co2 < tour.co2_einzel,
        ),
        Condition(
            f"Kosten höchstens Σ Einzelkosten × (1 + A08 = {tol:.0%})".replace(".", ","),
            f"{tour.kosten:,.2f} € gegen {tour.kosten_einzel * (1 + tol):,.2f} €".replace(",", "X")
            .replace(".", ",")
            .replace("X", "."),
            tour.kosten <= tour.kosten_einzel * (1 + tol),
        ),
    ]
    options = []
    for rank, v in enumerate(params.vehicles, start=1):
        n = max(1, roundup0(tour.paletten / v.paletten), roundup0(tour.gewicht_kg / v.nutzlast_kg))
        km = tour.lkw_km * n
        selected = rank == tour.fahrzeug_rang
        if selected:
            reason = "gewählt: kleinstes Fahrzeug für die Tourladung (Touren AD)"
        elif rank < tour.fahrzeug_rang:
            reason = f"Tourladung passt nicht in ein Fahrzeug, bräuchte {n}, jedes fährt die Tour"
        else:
            reason = "passt, aber größer als nötig"
        options.append(
            VehicleOption(
                fahrzeug=v.name,
                anzahl=n,
                auslastung=max(tour.gewicht_kg / n / v.nutzlast_kg, tour.paletten / n / v.paletten),
                lkw_km=km,
                co2_kg=emissions.co2_fzgkm(km, tour.gewicht_kg, n, v, params),
                kosten_eur=costs.tour_cost(km, v, result.c04),
                gewaehlt=selected,
                begruendung=reason,
            )
        )
    bundled = all(c.erfuellt for c in cond)
    ergebnis = (
        f"Gebündelt: {tour.sendungen} Einzelfahrten werden eine Tour mit {tour.fahrzeug}."
        if bundled
        else "Nicht gebündelt: " + ", ".join(c.name for c in cond if not c.erfuellt) + " nicht erfüllt."
    )
    return TourComparison(
        tour=tour,
        sendungen=rows,
        einzel_fahrzeuge=sum(r.fahrzeuge_n or 0 for r in rows),
        einzel_km=math.fsum(r.lkw_km_ist or 0.0 for r in rows),
        einzel_co2=tour.co2_einzel,
        einzel_kosten=tour.kosten_einzel,
        bedingungen=cond,
        optionen=options,
        ergebnis=ergebnis,
    )


@dataclass(slots=True)
class SideValues:
    fahrten: float
    lkw_km: float
    co2_kg: float
    kosten_eur: float


@dataclass(slots=True)
class RelationDetail:
    key: str
    start: str
    ziel: str
    szenario: str
    sendungen: int
    gewicht_t: float
    distanz_km: float
    distanzquelle: str
    ist: SideValues
    plan: SideValues
    bahn: int
    in_touren: int
    einzeln: int
    touren: list[Tour] = field(default_factory=list)
    zusammenfassung: str = ""
    beispiel_sendung: ShipmentRow | None = None


def relation_rows(result: Result, key: str) -> list[ShipmentRow]:
    k = fold(key)
    return [r for r in result.valid_rows if fold(r.relation or "") == k]


def relation_detail(result: Result, key: str, scenario: str) -> RelationDetail:
    """Ist gegen Plan für eine Relation (Start > Ziel) im gewählten Szenario.

    Plan M3: Bahn-Sendungen mit Bahnwerten, gebündelte Sendungen anteilig nach tkm, übrige
    Einzelfahrten (Input AX bis BC). Plan M2: wie M3, Bahn-Sendungen aber im Ist.
    Fahrten im Plan: Bahn 0, Sammeltour anteilig nach tkm, Einzelfahrt wie Ist.
    """
    rows = relation_rows(result, key)
    tours_by_nr = {t.tour_nr: t for t in result.tours}
    rail = [r for r in rows if r.bahn == "Ja"] if scenario == "M3" else []
    bundled = [r for r in rows if r.bahn == "Nein" and r.buendelbar == 1 and r.tour_gebuendelt == 1]
    if scenario == "Ist":
        bundled = []
    single = [r for r in rows if r not in rail and r not in bundled]
    line_share = {line.input_pos: line.anteil for line in result.tour_lines}
    pos = {id(r): i + 1 for i, r in enumerate(result.rows)}

    def plan_side() -> SideValues:
        trips = float(sum(r.fahrzeuge_n or 0 for r in single)) + math.fsum(
            line_share.get(pos[id(r)], 0.0) for r in bundled
        )
        km = math.fsum(r.lkw_km_ist or 0.0 for r in single) + math.fsum(r.lkw_km_plan or 0.0 for r in bundled)
        co2 = (
            math.fsum(r.co2_ist_fzgkm or 0.0 for r in single)
            + math.fsum(r.co2_plan_fzgkm or 0.0 for r in bundled)
            + math.fsum(r.co2_bahn or 0.0 for r in rail)
        )
        cost = (
            math.fsum(r.kosten_ist or 0.0 for r in single)
            + math.fsum(r.kosten_plan or 0.0 for r in bundled)
            + math.fsum(r.kosten_bahn or 0.0 for r in rail)
        )
        return SideValues(trips, km, co2, cost)

    ist = SideValues(
        float(sum(r.fahrzeuge_n or 0 for r in rows)),
        math.fsum(r.lkw_km_ist or 0.0 for r in rows),
        math.fsum(r.co2_ist_fzgkm or 0.0 for r in rows),
        math.fsum(r.kosten_ist or 0.0 for r in rows),
    )
    plan = ist if scenario == "Ist" else plan_side()
    tour_nrs = sorted({r.tour_nr for r in bundled if r.tour_nr})
    tours = [tours_by_nr[n] for n in tour_nrs]
    head = rows[0] if rows else None
    parts = [f"{len(rows)} Sendungen, im Ist {int(ist.fahrten)} Einzelfahrten"]
    if scenario != "Ist":
        if rail:
            parts.append(f"{len(rail)} auf die Bahn (Lkw nur im Vor- und Nachlauf)")
        if bundled:
            parts.append(f"{len(bundled)} in {len(tours)} Sammeltour(en)")
        if single:
            parts.append(f"{len(single)} bleiben Einzelfahrt")
    return RelationDetail(
        key=key,
        start=head.start_label or "" if head else "",
        ziel=head.ziel_label or "(ohne Ziel)" if head else "",
        szenario=scenario,
        sendungen=len(rows),
        gewicht_t=math.fsum(to_number(r.shipment.gewicht_kg) for r in rows) / 1000,
        distanz_km=statistics.fmean(r.distanz_km or 0.0 for r in rows) if rows else 0.0,
        distanzquelle=(head.distanz_quelle or "") if head else "",
        ist=ist,
        plan=plan,
        bahn=len(rail),
        in_touren=len(bundled),
        einzeln=len(single),
        touren=tours,
        zusammenfassung="; ".join(parts) + ".",
        beispiel_sendung=max(rows, key=lambda r: to_number(r.shipment.gewicht_kg)) if rows else None,
    )


@dataclass(slots=True)
class RoadAirRow:
    key: str
    start_key: str
    ziel_key: str
    luftlinie_km: float
    naeherung_km: float
    strasse_km: float | None
    faktor: float | None


def road_vs_air(
    result: Result, road_km: dict[str, float], params: Assumptions
) -> tuple[list[RoadAirRow], float | None, float | None]:
    """Luftlinie, Näherung (× I01) und Straßen-km je Relation; empirischer Straßenfaktor.

    ``road_km`` ordnet einem Relationsschlüssel (Start > Ziel) die Straßen-km zu.
    Rückgabe: Zeilen, Faktor Σ Straße / Σ Luftlinie und Median der Faktoren.
    """
    first: dict[str, ShipmentRow] = {}
    for r in result.valid_rows:
        if r.relation and r.luftlinie_km:
            first.setdefault(fold(r.relation), r)
    rows = []
    for k, r in first.items():
        assert r.luftlinie_km is not None
        road = road_km.get(k)
        rows.append(
            RoadAirRow(
                key=r.relation or k,
                start_key=r.start_key or "",
                ziel_key=r.ziel_key or "",
                luftlinie_km=r.luftlinie_km,
                naeherung_km=r.luftlinie_km * params.i01_strassenfaktor,
                strasse_km=road,
                faktor=None if road is None else road / r.luftlinie_km,
            )
        )
    routed = [x for x in rows if x.strasse_km is not None]
    if not routed:
        return rows, None, None
    total = math.fsum(x.strasse_km or 0.0 for x in routed) / math.fsum(x.luftlinie_km for x in routed)
    median = statistics.median(x.faktor or 0.0 for x in routed)
    return rows, total, median


def relation_index(result: Result) -> dict[str, list[ShipmentRow]]:
    out: dict[str, list[ShipmentRow]] = defaultdict(list)
    for r in result.valid_rows:
        out[fold(r.relation or "")].append(r)
    return out


@dataclass(slots=True)
class RouteOption:
    """Eine Transportvariante für alle Sendungen einer Relation."""

    name: str
    art: str
    """``ist``, ``lkw`` (eine Fahrzeugklasse für alle Sendungen), ``bahn``, ``plan``."""
    fahrten: float
    lkw_km: float
    co2_kg: float
    kosten_eur: float
    servicegrad: float
    zusatz_tage: float
    hinweis: str
    gewaehlt: bool = False


@dataclass(slots=True)
class RouteOptions:
    key: str
    sendungen: int
    distanz_km: float
    optionen: list[RouteOption]
    erklaerung: str


def _rail_reason(row: ShipmentRow, params: Assumptions) -> str:
    assert row.distanz_km is not None and row.kosten_ist is not None and row.kosten_bahn is not None
    if row.distanz_km <= params.a01_bahn_grenze_km:
        return "Distanz bis A01"
    if params.c03_laufzeit_ok != 1:
        return "Laufzeitregel C03"
    if row.kosten_bahn > row.kosten_ist * (1 + params.a08_kosten_tol):
        return "Kosten über A08"
    return ""


def route_options(result: Result, key: str, params: Assumptions) -> RouteOptions:
    r"""Alle Varianten einer Relation: Ist, jede Lkw-Klasse, Bahn, Plan M2 und M3.

    Lkw-Klasse :math:`v`: je Sendung :math:`n_v = \max(1, \lceil p/p_v\rceil, \lceil kg/kg_v\rceil)`
    Fahrzeuge über die Sendungsdistanz (wie :func:`vehicle_options`), summiert über alle
    Sendungen; Kosten als Modellkosten :math:`km \cdot k_v \cdot C_{04}`. Bahn: jede Sendung
    über die Bahn mit Vor- und Nachlauf (K2.12, Kosten :math:`K(1 + A_{07})`), auch wenn die
    Bahnprüfung (J2.4) sie ablehnt; der Grund steht im Hinweis. Plan M2 und M3 aus
    :func:`relation_detail`. Systemgrenze: Sendungen der Relation, Luftlinie mal I01 oder
    eingegebene Distanz, keine Rückfahrten.
    """
    rows = relation_rows(result, key)
    n = len(rows)
    ist = relation_detail(result, key, "Ist").ist
    note = "Excel, Rangregel K2.5 je Sendung"
    out = [
        RouteOption(
            "Ist (Einzelversand)", "ist", ist.fahrten, ist.lkw_km, ist.co2_kg, ist.kosten_eur, 1.0, 0.0, note
        )
    ]
    classes = [
        [0.0, 0.0, 0.0, 0.0, 0, 0] for _ in params.vehicles
    ]  # Fahrten, km, CO2e, Kosten, gewählt, mehrfach
    for row in rows:
        assert row.paletten is not None and row.distanz_km is not None
        kg = to_number(row.shipment.gewicht_kg)
        for acc, opt in zip(
            classes, vehicle_options(kg, row.paletten, row.distanz_km, params, result.c04), strict=True
        ):
            acc[0] += opt.anzahl
            acc[1] += opt.lkw_km
            acc[2] += opt.co2_kg
            acc[3] += opt.kosten_eur
            acc[4] += int(opt.gewaehlt)
            acc[5] += int(opt.anzahl > 1)
    for v, (trips, km, co2, cost, chosen, multi) in zip(params.vehicles, classes, strict=True):
        parts = [f"im Ist für {int(chosen)} von {n} Sendungen gewählt"]
        if multi:
            parts.append(f"{int(multi)} Sendungen brauchen mehrere Fahrzeuge")
        out.append(RouteOption(f"Alle mit {v.name}", "lkw", trips, km, co2, cost, 1.0, 0.0, "; ".join(parts)))
    rejected: dict[str, int] = defaultdict(int)
    for row in rows:
        reason = _rail_reason(row, params)
        if reason:
            rejected[reason] += 1
    rail_note = (
        "Bahnprüfung abgelehnt: " + ", ".join(f"{k} ({v} Sendungen)" for k, v in rejected.items())
        if rejected
        else "Bahnprüfung für alle Sendungen erfüllt"
    )
    out.append(
        RouteOption(
            "Alle per Bahn",
            "bahn",
            0.0,
            0.0,
            math.fsum(
                emissions.co2_rail(to_number(r.shipment.gewicht_kg), r.distanz_km or 0.0, params)
                for r in rows
            ),
            math.fsum(r.kosten_bahn or 0.0 for r in rows),
            0.0,
            params.a05_zusatz_tage,
            rail_note + "; Lkw nur im Vor- und Nachlauf (A02, im CO₂e enthalten)",
        )
    )
    for scenario in ("M2", "M3"):
        d = relation_detail(result, key, scenario)
        out.append(
            RouteOption(
                f"Plan {scenario}",
                "plan",
                d.plan.fahrten,
                d.plan.lkw_km,
                d.plan.co2_kg,
                d.plan.kosten_eur,
                1 - d.bahn / n if n else 1.0,
                params.a05_zusatz_tage if d.bahn else 0.0,
                d.zusammenfassung,
                gewaehlt=True,
            )
        )
    return RouteOptions(
        key=key,
        sendungen=n,
        distanz_km=statistics.fmean(r.distanz_km or 0.0 for r in rows) if rows else 0.0,
        optionen=out,
        erklaerung=(
            "Lkw-Klassen: je Sendung n = max(1, ⌈Paletten/Kapazität⌉, ⌈kg/Nutzlast⌉) Fahrzeuge, Kosten "
            "Modell × C04. Bahn: CO₂e nach K2.8 (Vor- und Nachlauf A02 mit Lkw, Hauptlauf Bahnfaktor C01), "
            "Kosten Ist × (1 + A07), Zusatzlaufzeit A05. Plan M2 und M3 aus der Excel-Logik. "
            + COMPARISON_NOTE
            + "."
        ),
    )


@dataclass(slots=True)
class BundleTotals:
    fahrten: float
    lkw_km: float
    co2_kg: float
    kosten_eur: float


@dataclass(slots=True)
class CustomTour:
    tour: Tour
    stopps: list[tuple[str, float, float]]
    """Start, dann Ziele (Name, Breite, Länge) in der Reihenfolge "nächster Nachbar" (Darstellung)."""
    sendungen_je_ziel: dict[str, int]
    tage: list[int]
    """Versanddaten (Excel-Serienzahl) der Sendungen der Tour."""


@dataclass(slots=True)
class CustomBundle:
    keys: list[str]
    szenario: str
    fenster_tage: int
    sendungen: int
    ist: BundleTotals
    automatisch: BundleTotals
    eigen: BundleTotals
    touren: list[CustomTour]
    gebuendelt: int
    verschiebung_max: int
    verschiebung_mittel: float
    startorte: list[str]
    erklaerung: str


def custom_bundle(
    result: Result, keys: list[str], params: Assumptions, scenario: str = "M2", fenster_tage: int = 0
) -> CustomBundle:
    r"""Eigene Bündelung nur der gewählten Relationen, wahlweise über ein Zeitfenster.

    Kopien der Sendungen der gewählten Relationen durchlaufen dieselbe Tourbildung wie M2
    (:func:`assign_groups`, :func:`build_tours`: Next-Fit je Gruppe, Tour-km
    :math:`d_{\max}(1 + A_{10}(s-1))`, Entscheidung K2.15). Gruppe = Tag (``fenster_tage = 0``)
    oder Block von :math:`w+1` Tagen, je Startort. Sendungen, die die Bahnprüfung bestehen, fahren
    in M3 Bahn und sind nie bündelbar (wie Excel). Verschiebung je Sendung einer gebündelten Tour:
    letzter Versandtag der Tour minus eigener Versandtag. Das Ergebnis der Excel bleibt unverändert.
    """
    plan_scenario = "M3" if scenario == "M3" else "M2"
    wanted = {fold(k) for k in keys}
    originals = [r for r in result.valid_rows if fold(r.relation or "") in wanted]
    rows = copy.deepcopy(originals)
    assign_groups(rows, fenster_tage)
    lines, tours = build_tours(rows, params, result.c04)
    by_pos = {line.input_pos: line for line in lines}
    trips = km = co2 = cost = 0.0
    for i, row in enumerate(rows, start=1):
        line = by_pos.get(i)
        if plan_scenario == "M3" and row.bahn == "Ja":
            co2 += row.co2_bahn or 0.0
            cost += row.kosten_bahn or 0.0
        elif line is not None:
            trips += line.fahrzeuge_plan or 0
            km += line.lkw_km_plan or 0.0
            co2 += line.co2_plan or 0.0
            cost += line.kosten_plan or 0.0
        else:
            trips += row.fahrzeuge_n or 0
            km += row.lkw_km_ist or 0.0
            co2 += row.co2_ist_fzgkm or 0.0
            cost += row.kosten_ist or 0.0
    ist = BundleTotals(
        float(sum(r.fahrzeuge_n or 0 for r in originals)),
        math.fsum(r.lkw_km_ist or 0.0 for r in originals),
        math.fsum(r.co2_ist_fzgkm or 0.0 for r in originals),
        math.fsum(r.kosten_ist or 0.0 for r in originals),
    )
    autos = [relation_detail(result, k, plan_scenario).plan for k in keys]
    auto = BundleTotals(
        math.fsum(a.fahrten for a in autos),
        math.fsum(a.lkw_km for a in autos),
        math.fsum(a.co2_kg for a in autos),
        math.fsum(a.kosten_eur for a in autos),
    )
    members: dict[int, list[ShipmentRow]] = defaultdict(list)
    for line in lines:
        members[line.tour_nr].append(rows[line.input_pos - 1])
    shifts: list[int] = []
    custom: list[CustomTour] = []
    for tour in sorted(tours, key=lambda t: (-t.gebuendelt, -t.sendungen, t.tour_nr)):
        ms = members[tour.tour_nr]
        days = [m.datum_serial or 0 for m in ms]
        if tour.gebuendelt:
            shifts += [max(days) - d for d in days]
        head = ms[0]
        per_stop: dict[str, int] = defaultdict(int)
        coords: dict[str, tuple[float, float]] = {}
        for m in ms:
            label = m.ziel_label or ""
            per_stop[label] += 1
            if m.ziel_lat is not None and m.ziel_lon is not None:
                coords.setdefault(label, (m.ziel_lat, m.ziel_lon))
        start = (head.start_lat or 0.0, head.start_lon or 0.0)
        order = nearest_neighbor_order(start, list(coords.items()))
        custom.append(
            CustomTour(
                tour=tour,
                stopps=[(head.start_label or "", *start), *[(n, p[0], p[1]) for n, p in order]],
                sendungen_je_ziel=dict(per_stop),
                tage=days,
            )
        )
    rule = "je Tag" if fenster_tage == 0 else f"je Block von {fenster_tage + 1} Tagen"
    return CustomBundle(
        keys=list(keys),
        szenario=plan_scenario,
        fenster_tage=fenster_tage,
        sendungen=len(rows),
        ist=ist,
        automatisch=auto,
        eigen=BundleTotals(trips, km, co2, cost),
        touren=custom,
        gebuendelt=sum(1 for t in tours if t.gebuendelt),
        verschiebung_max=max(shifts, default=0),
        verschiebung_mittel=statistics.fmean(shifts) if shifts else 0.0,
        startorte=sorted({r.start_label or "" for r in rows}),
        erklaerung=(
            f"Eigene Gruppe: nur die gewählten Relationen, Gruppe {rule} und Startort, "
            "Next-Fit in das größte Fahrzeug, Tour-km = längste Distanz × (1 + A10 × (Stopps − 1)), "
            "Bündelung nur wenn K2.15 erfüllt. Automatisch: Ergebnis der Excel für dieselben Sendungen "
            "(Sammeltouren anteilig nach tkm, auch mit Sendungen anderer Relationen). "
            f"{COMPARISON_NOTE}."
        ),
    )
