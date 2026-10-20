"""Vergleichsrechnungen für die Karte: Fahrzeugalternativen, Tourentscheidung, Relation Ist gegen Plan.

Alle Werte entstehen mit den Funktionen des Rechenkerns. Die Alternativen (andere
Fahrzeugklassen, mehrere kleine Fahrzeuge) sind Vergleichsrechnungen und nicht Teil der
Excel; die gewählte Variante ist immer die der Excel (Rangregel K2.5, Bündelung K2.15).
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field

from tk import costs, emissions
from tk.excelfn import fold, roundup0, to_number
from tk.models import Assumptions, Result, ShipmentRow, Tour, TourLine
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
