"""Tourbildung M2: Next-Fit je Tag und Startort, Tourentscheidung, Rückführung.

Entspricht Input AP bis AW, dem Blatt Touren (Spalten A bis AT) und den Schnittstellen
J2.5 ``group_and_tour``, J2.6 ``bundle_decision`` und J2.7 ``allocate``.
"""

from __future__ import annotations

import math
from collections import defaultdict

from tk.costs import tour_cost
from tk.emissions import co2_tkm, co2_tour_fzgkm
from tk.excelfn import criterion_number, first_positions, fold, round_half_away, roundup0, to_number
from tk.models import Assumptions, ShipmentRow, Tour, TourLine
from tk.vehicle import rank_for_load

GROUP_FACTOR = 10_000
"""Gruppe = Datum x 10.000 + Startort-Nr. (Definition, Assumptions K3.7)."""


def assign_groups(rows: list[ShipmentRow], window_days: int = 0) -> None:
    r"""Gruppe und Rang je bündelbarer Sendung (Register K2.13, Input AP bis AS).

    .. math:: \text{Gruppe} = \text{Datum}\cdot 10\,000 + \text{Position der Start-Zuordnung}

    Rang in der Gruppe: Entfernung absteigend, bei Gleichstand Eingabereihenfolge.

    ``window_days`` > 0 ist eine Vergleichsrechnung (nicht Excel): Das Datum wird auf Blöcke von
    ``window_days + 1`` Tagen gerastert, :math:`\lfloor \text{Datum}/(w+1)\rfloor (w+1)`, sodass
    Sendungen aus mehreren Tagen eine Gruppe bilden. Mit 0 gilt die Excel-Regel unverändert.
    """
    first = first_positions([r.start_label for r in rows])
    block = window_days + 1
    for row, pos in zip(rows, first, strict=True):
        if row.ok:
            assert row.datum_serial is not None and pos is not None
            day = row.datum_serial // block * block
            row.gruppe = day * GROUP_FACTOR + pos + 1
            row.buendelbar = 1 if row.bahn == "Nein" and row.fahrzeuge_n == 1 else 0
    by_group: dict[int, list[ShipmentRow]] = defaultdict(list)
    for row in rows:
        if row.ok and row.buendelbar == 1:
            assert row.gruppe is not None
            by_group[row.gruppe].append(row)
    for members in by_group.values():
        seen: dict[float, int] = defaultdict(int)
        for row in members:
            assert row.distanz_km is not None
            z = row.distanz_km
            crit = criterion_number(z)
            longer = sum(1 for m in members if m.distanz_km is not None and m.distanz_km > crit)
            seen[z] += 1
            row.rang_gruppe = longer + seen[z]
            assert row.gruppe is not None
            row.sortkey = row.gruppe * GROUP_FACTOR + row.rang_gruppe


def build_tours(
    rows: list[ShipmentRow], params: Assumptions, c04: float
) -> tuple[list[TourLine], list[Tour]]:
    """J2.5 ``group_and_tour`` und J2.6 ``bundle_decision`` (Blatt Touren).

    Next-Fit: Die Sendungen einer Gruppe kommen der Reihe nach in ein Fahrzeug der größten
    Klasse, bis Gewicht oder Paletten die Kapazität überschreiten; dann beginnt eine neue
    Tour. Sendungen werden nicht geteilt. Tourladungen werden auf 6 Stellen gerundet.
    """
    eligible = sorted((r for r in rows if r.ok and r.buendelbar == 1), key=lambda r: r.sortkey or 0)
    input_pos = {id(r): i + 1 for i, r in enumerate(rows)}
    max_kg, max_pal = params.max_kg, params.max_paletten
    lines: list[TourLine] = []
    stops_seen: set[tuple[int, str]] = set()
    for nr, row in enumerate(eligible, start=1):
        assert row.sortkey is not None and row.gruppe is not None and row.distanz_km is not None
        assert row.paletten is not None and row.tkm is not None and row.auslastung is not None
        assert row.co2_ist_fzgkm is not None and row.kosten_ist is not None
        kg = to_number(row.shipment.gewicht_kg)
        prev = lines[-1] if lines else None
        if prev is None:
            neue_gruppe, neue_tour, q, r, s = 1, 1, kg, row.paletten, 1
        else:
            neue_gruppe = 0 if row.gruppe == prev.gruppe else 1
            q_sum = round_half_away(prev.ladung_kg + kg, 6)
            r_sum = round_half_away(prev.ladung_pal + row.paletten, 6)
            fits = q_sum <= max_kg and r_sum <= max_pal
            neue_tour = 1 if neue_gruppe == 1 or not fits else 0
            q = kg if neue_tour else q_sum
            r = row.paletten if neue_tour else r_sum
            s = prev.tour_nr + neue_tour
        ziel = row.ziel_label or ""
        if ziel == "":
            stopp = 1
        else:
            stopp = 0 if (s, fold(ziel)) in stops_seen else 1
            stops_seen.add((s, fold(ziel)))
        sid = row.shipment.sendungs_id
        pos = input_pos[id(row)]
        lines.append(
            TourLine(
                nr=nr,
                sortkey=row.sortkey,
                input_pos=pos,
                sendung=f"Zeile {pos + 13}" if sid is None or sid == "" else str(sid),
                gruppe=row.gruppe,
                start=row.start_label or "",
                ziel=ziel,
                distanz_km=row.distanz_km,
                gewicht_kg=kg,
                paletten=row.paletten,
                tkm=row.tkm,
                auslastung=row.auslastung,
                co2_ist=row.co2_ist_fzgkm,
                kosten_ist=row.kosten_ist,
                neue_gruppe=neue_gruppe,
                neue_tour=neue_tour,
                ladung_kg=q,
                ladung_pal=r,
                tour_nr=s,
                neuer_stopp=stopp,
            )
        )
    tours = _tour_heads(lines, params, c04)
    _allocate(lines, tours, rows, params)
    _aggregate_lower_bound(lines, params)
    return lines, tours


def _tour_heads(lines: list[TourLine], params: Assumptions, c04: float) -> list[Tour]:
    members: dict[int, list[TourLine]] = defaultdict(list)
    for line in lines:
        members[line.tour_nr].append(line)
    tours = []
    for tour_nr, ms in members.items():
        head = ms[0]
        weight = round_half_away(math.fsum(m.gewicht_kg for m in ms), 6)
        pallets = round_half_away(math.fsum(m.paletten for m in ms), 6)
        stops = sum(m.neuer_stopp for m in ms)
        dmax = max(m.distanz_km for m in ms)
        rank = rank_for_load(pallets, weight, params.vehicles)
        vehicle = params.vehicles[rank - 1]
        km = dmax * (1 + params.a10_umweg * max(0, stops - 1))
        co2 = co2_tour_fzgkm(km, weight, vehicle, params)
        tkm = math.fsum(m.tkm for m in ms)
        cost = tour_cost(km, vehicle, c04)
        co2_single = math.fsum(m.co2_ist for m in ms)
        cost_single = math.fsum(m.kosten_ist for m in ms)
        u_min = min(m.auslastung for m in ms)
        tours.append(
            Tour(
                tour_nr=tour_nr,
                gruppe=head.gruppe,
                start=head.start,
                erste_zeile=head.nr,
                sendungen=len(ms),
                stopps=stops,
                gewicht_kg=weight,
                paletten=pallets,
                max_distanz_km=dmax,
                min_auslastung=u_min,
                co2_einzel=co2_single,
                kosten_einzel=cost_single,
                tkm=tkm,
                fahrzeug_rang=rank,
                fahrzeug=vehicle.name,
                lkw_km=km,
                co2=co2,
                co2_tkm=co2_tkm(tkm, vehicle),
                kosten=cost,
                gebuendelt=bundle_decision(len(ms), u_min, co2, co2_single, cost, cost_single, params),
                sendungen_ids=tuple(m.sendung for m in ms),
            )
        )
    return tours


def bundle_decision(
    n: int,
    u_min: float,
    co2_tour: float,
    co2_single: float,
    cost_tour: float,
    cost_single: float,
    params: Assumptions,
) -> int:
    r"""J2.6 ``bundle_decision`` (Register K2.15, Touren AI).

    .. math:: \text{bündeln} \Leftrightarrow n_T \ge 2 \wedge u_{\min} < A_{09}
              \wedge E_T < \sum E_i \wedge K_T \le \sum K_i\,(1 + A_{08})
    """
    if n == 1:
        return 0
    ok = (
        u_min < params.a09_schwelle
        and co2_tour < co2_single
        and cost_tour <= cost_single * (1 + params.a08_kosten_tol)
    )
    return 1 if ok else 0


def _allocate(lines: list[TourLine], tours: list[Tour], rows: list[ShipmentRow], params: Assumptions) -> None:
    r"""J2.7 ``allocate`` (Register K2.16, Touren AJ bis AS).

    .. math:: x_i = \frac{tkm_i}{\sum_{j\in T} tkm_j}\, X_T

    Nicht gebündelte Touren behalten die Werte der Einzelfahrt.
    """
    by_nr = {t.tour_nr: t for t in tours}
    for line in lines:
        tour = by_nr[line.tour_nr]
        row = rows[line.input_pos - 1]
        line.anteil = line.tkm / tour.tkm
        if tour.gebuendelt == 1:
            line.fahrzeuge_plan = line.neue_tour
            line.fahrzeug_plan = tour.fahrzeug if line.neue_tour == 1 else "in Sammeltour"
            line.lkw_km_plan = line.anteil * tour.lkw_km
            line.co2_plan = line.anteil * tour.co2
            line.co2_plan_tkm = line.anteil * tour.co2_tkm
            line.kosten_plan = line.anteil * tour.kosten
        else:
            assert row.fahrzeug is not None and row.lkw_km_ist is not None
            assert row.co2_ist_tkm is not None
            line.fahrzeuge_plan = 1
            line.fahrzeug_plan = row.fahrzeug
            line.lkw_km_plan = row.lkw_km_ist
            line.co2_plan = line.co2_ist
            line.co2_plan_tkm = row.co2_ist_tkm
            line.kosten_plan = line.kosten_ist
        row.touren_zeile = line.nr
        row.tour_nr = tour.tour_nr
        row.sendungen_tour = tour.sendungen
        row.tour_gebuendelt = tour.gebuendelt


def _aggregate_lower_bound(lines: list[TourLine], params: Assumptions) -> None:
    """Touren AT: Untergrenze der Fahrzeuge je Gruppe bei teilbaren Sendungen."""
    pal: dict[int, list[float]] = defaultdict(list)
    kg: dict[int, list[float]] = defaultdict(list)
    for line in lines:
        pal[line.gruppe].append(line.paletten)
        kg[line.gruppe].append(line.gewicht_kg)
    for line in lines:
        if line.neue_gruppe == 1:
            line.fahrzeuge_aggregiert = max(
                roundup0(math.fsum(pal[line.gruppe]) / params.max_paletten),
                roundup0(math.fsum(kg[line.gruppe]) / params.max_kg),
            )
