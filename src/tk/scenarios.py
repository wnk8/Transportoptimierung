"""Szenarien Ist, M2, M3, Allokation, Servicegrad, Zulässigkeit.

``calculate`` rechnet eine Liste von Sendungen vollständig durch, in der Reihenfolge der
Excel-Spalten: Eingabeprüfung und Ortsauflösung (I bis AA), Einzelversand (AB bis AL),
Bahnprüfung (AM bis AO), Tourbildung (AP bis AW, Blatt Touren), Plan (AX bis BD),
Auswertungshilfen (BE bis BK), Kennzahlen (Overview Abschnitt 1) und Routen.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from tk import costs, emissions
from tk.assumptions import load_assumptions
from tk.bundling import assign_groups, build_tours
from tk.checks import overall_status, run_checks
from tk.distance import distance_km
from tk.excelfn import (
    fold,
    german_number_text,
    is_blank,
    is_number,
    parse_date,
    round_half_away,
    serial_to_date,
    to_number,
)
from tk.geo import PlaceDB, load_place_db, resolve_place
from tk.models import (
    INPUT_FIELDS,
    Assumptions,
    Result,
    Route,
    ScenarioKpis,
    Shipment,
    ShipmentRow,
    TourLine,
)
from tk.rail import rail_check
from tk.validation import check_row
from tk.vehicle import pick_vehicle
from tk.workbook import WorkbookData

ROUTES_CAPACITY = 300
"""Strukturelle Grenze des Blatts Routen (Zeilen 14 bis 313, Assumptions K6.2)."""


@dataclass(slots=True)
class Model:
    """Rechenkontext: Parameter, Ortsdatenbank und Rechenbereich (Zeilen der Mappe)."""

    params: Assumptions
    db: PlaceDB
    capacity: int


def calculate(shipments: Sequence[Shipment], model: Model) -> Result:
    """Rechnet alle Sendungen wie die Excel v11 (Blätter Input, Touren, Routen, Overview)."""
    params = model.params
    inside = list(shipments[: model.capacity])
    overflow = sum(1 for s in shipments[model.capacity :] for c in s.cells() if not (c is None or c == ""))
    rows = [ShipmentRow(excel_row=14 + i, shipment=s) for i, s in enumerate(inside)]
    for row in rows:
        _locate(row, model)
    for row in rows:
        if row.ok:
            _single(row, params)
    c04 = costs.calibration_factor(
        (_opt_number(r.shipment.fracht_eur), r.kosten_modell or 0.0) for r in rows if r.ok
    )
    for row in rows:
        if row.ok:
            _cost_and_rail(row, params, c04)
    assign_groups(rows)
    lines, tours = build_tours(rows, params, c04)
    for row in rows:
        if row.ok:
            _plan(row, lines, params)
    _helpers(rows)
    n_valid = sum(1 for r in rows if r.ok)
    kpis = scenario_kpis(rows, params, n_valid)
    routes = build_routes(rows)
    result = Result(
        rows=rows,
        tour_lines=lines,
        tours=tours,
        kpis=kpis,
        routes=routes,
        c04=c04,
        n_valid=n_valid,
        status="",
        overflow_cells=overflow,
    )
    result.status = cockpit_status(result, params)
    result.checks = run_checks(result, params)
    result.gesamtstatus = overall_status(result.checks, n_valid)
    return result


def _opt_number(value: object) -> float | None:
    return to_number(value) if not is_blank(value) and is_number(value) else None


def _locate(row: ShipmentRow, model: Model) -> None:
    s = row.shipment
    row.datum_serial = parse_date(s.datum)
    start = resolve_place(s.start, model.db, model.params)
    ziel = resolve_place(s.ziel, model.db, model.params)
    row.start_key, row.start_art, row.start_row = start.key, start.art, start.row
    row.start_label, row.start_lat, row.start_lon = start.label, start.lat, start.lon
    row.ziel_key, row.ziel_art, row.ziel_row = ziel.key, ziel.art, ziel.row
    row.ziel_label, row.ziel_lat, row.ziel_lon = ziel.label, ziel.lat, ziel.lon
    d = distance_km(start, ziel, s.km, model.db, model.params)
    row.luftlinie_km, row.relation_km, row.naeherung_km = d.luftlinie_km, d.relation_km, d.naeherung_km
    row.distanz_km, row.distanz_quelle = d.distanz_km, d.quelle
    row.pruefung = check_row(s.cells(), row.datum_serial, start, ziel, d.relation_km, d.distanz_km)


def _single(row: ShipmentRow, params: Assumptions) -> None:
    """Einzelversand (Ist), Input AB bis AK."""
    s = row.shipment
    kg = to_number(s.gewicht_kg)
    assert row.distanz_km is not None
    pick = pick_vehicle(kg, _opt_number(s.paletten), row.distanz_km, params)
    row.paletten = pick.paletten
    row.tkm = kg / 1000 * row.distanz_km
    row.fahrzeuge_n = pick.fahrzeuge_n
    row.fahrzeug_rang = pick.rang
    row.fahrzeug = pick.fahrzeug.name
    row.auslastung = pick.auslastung
    row.lkw_km_ist = pick.lkw_km
    row.co2_ist_fzgkm = emissions.co2_fzgkm(pick.lkw_km, kg, pick.fahrzeuge_n, pick.fahrzeug, params)
    row.co2_ist_tkm = emissions.co2_tkm(row.tkm, pick.fahrzeug)
    row.kosten_modell = costs.model_cost(pick.lkw_km, pick.fahrzeug)
    row.engpass = pick.engpass


def _cost_and_rail(row: ShipmentRow, params: Assumptions, c04: float) -> None:
    """Kosten Einzel und Bahnprüfung, Input AL bis AO."""
    assert row.kosten_modell is not None and row.distanz_km is not None
    row.kosten_ist = costs.single_cost(_opt_number(row.shipment.fracht_eur), row.kosten_modell, c04)
    row.kosten_bahn = costs.rail_cost(row.kosten_ist, params)
    on_rail = rail_check(row.distanz_km, row.kosten_ist, row.kosten_bahn, params)
    row.bahn = "Ja" if on_rail else "Nein"
    kg = to_number(row.shipment.gewicht_kg)
    row.co2_bahn = emissions.co2_rail(kg, row.distanz_km, params) if on_rail else 0.0


def _plan(row: ShipmentRow, lines: list[TourLine], params: Assumptions) -> None:
    """Plan je Sendung (Input AX bis BD)."""
    if row.bahn == "Ja":
        row.fahrzeuge_plan = 0
        row.fahrzeug_plan = "Bahn"
        row.lkw_km_plan = 0.0
        row.co2_plan_fzgkm = row.co2_bahn
        row.co2_plan_tkm = row.co2_bahn
        row.kosten_plan = row.kosten_bahn
        row.ergebnis = f"Bahn mit Lkw-Vor-/Nachlauf (+{german_number_text(params.a05_zusatz_tage)} Tag)"
        return
    if row.buendelbar == 1:
        assert row.touren_zeile is not None
        line = lines[row.touren_zeile - 1]
        row.fahrzeuge_plan = line.fahrzeuge_plan
        row.fahrzeug_plan = line.fahrzeug_plan
        row.lkw_km_plan = line.lkw_km_plan
        row.co2_plan_fzgkm = line.co2_plan
        row.co2_plan_tkm = line.co2_plan_tkm
        row.kosten_plan = line.kosten_plan
    else:
        row.fahrzeuge_plan = row.fahrzeuge_n
        row.fahrzeug_plan = row.fahrzeug
        row.lkw_km_plan = row.lkw_km_ist
        row.co2_plan_fzgkm = row.co2_ist_fzgkm
        row.co2_plan_tkm = row.co2_ist_tkm
        row.kosten_plan = row.kosten_ist
    if row.buendelbar == 1 and row.tour_gebuendelt == 1:
        row.ergebnis = (
            f"Sammeltour {row.tour_nr}: {row.sendungen_tour} Sendungen, {row.fahrzeug_plan} für die Tour"
        )
    else:
        row.ergebnis = f"Einzelfahrt: {row.fahrzeuge_n} x {row.fahrzeug}"


def _helpers(rows: list[ShipmentRow]) -> None:
    """Auswertungshilfen Input BE bis BK."""
    seen_start: set[str] = set()
    seen_ziel: set[str] = set()
    seen_rel: set[str] = set()
    n_start = n_ziel = n_rel = 0
    for row in rows:
        s = row.shipment
        if not row.ok:
            continue
        assert row.datum_serial is not None
        row.monat = serial_to_date(row.datum_serial).month
        key = fold(row.start_label or "")
        if key not in seen_start:
            seen_start.add(key)
            n_start += 1
            row.start_rang = n_start
        if row.ziel_label:
            zkey = fold(row.ziel_label)
            if zkey not in seen_ziel:
                seen_ziel.add(zkey)
                n_ziel += 1
                row.ziel_rang = n_ziel
        row.relation = f"{row.start_label} > {row.ziel_label or '(ohne Ziel)'}"
        rkey = fold(row.relation)
        if rkey not in seen_rel:
            seen_rel.add(rkey)
            n_rel += 1
            row.relation_rang = n_rel
        if not is_blank(s.km) and row.luftlinie_km is not None:
            row.plausibel = 1 if to_number(s.km) < row.luftlinie_km else 0


def _delta(value: float, base: float) -> float:
    return 0.0 if base == 0 else value / base - 1


def _service(n_valid: int, n_rail: int, params: Assumptions) -> float:
    r"""Servicegrad (Register K2.17): :math:`S = 1 - N_{\text{Bahn}}/N`, nur wenn A05 > 0."""
    if n_valid == 0:
        return 1.0
    return 1 - n_rail / n_valid if params.a05_zusatz_tage > 0 else 1.0


def scenario_kpis(rows: list[ShipmentRow], params: Assumptions, n_valid: int) -> dict[str, ScenarioKpis]:
    r"""Methodenvergleich (Overview & Results C10:L12, Register K2.17).

    Ist: Summen des Einzelversands. M2: Plan der Lkw-Sendungen plus Ist der Bahn-Sendungen.
    M3: Plan aller Sendungen. :math:`\Delta = \sum \text{Plan} / \sum \text{Ist} - 1`.
    """
    ok = [r for r in rows if r.ok]
    rail = [r for r in ok if r.bahn == "Ja"]
    road = [r for r in ok if r.bahn == "Nein"]

    def total(items: list[ShipmentRow], attr: str) -> float:
        return math.fsum(getattr(r, attr) or 0.0 for r in items)

    ist = {
        "co2_fzgkm_kg": total(ok, "co2_ist_fzgkm"),
        "co2_tkm_kg": total(ok, "co2_ist_tkm"),
        "kosten_eur": total(ok, "kosten_ist"),
        "lkw_km": total(ok, "lkw_km_ist"),
    }
    m2 = {
        "co2_fzgkm_kg": total(road, "co2_plan_fzgkm") + total(rail, "co2_ist_fzgkm"),
        "co2_tkm_kg": total(road, "co2_plan_tkm") + total(rail, "co2_ist_tkm"),
        "kosten_eur": total(road, "kosten_plan") + total(rail, "kosten_ist"),
        "lkw_km": total(road, "lkw_km_plan") + total(rail, "lkw_km_ist"),
    }
    m3 = {
        "co2_fzgkm_kg": total(ok, "co2_plan_fzgkm"),
        "co2_tkm_kg": total(ok, "co2_plan_tkm"),
        "kosten_eur": total(ok, "kosten_plan"),
        "lkw_km": total(ok, "lkw_km_plan"),
    }

    def build(name: str, values: dict[str, float], n_rail: int, base: bool) -> ScenarioKpis:
        deltas = {
            f"delta_{k.removesuffix('_kg').removesuffix('_eur')}": None if base else _delta(v, ist[k])
            for k, v in values.items()
        }
        return ScenarioKpis(
            name=name,
            co2_fzgkm_kg=values["co2_fzgkm_kg"],
            delta_co2_fzgkm=deltas["delta_co2_fzgkm"],
            co2_tkm_kg=values["co2_tkm_kg"],
            delta_co2_tkm=deltas["delta_co2_tkm"],
            kosten_eur=values["kosten_eur"],
            delta_kosten=deltas["delta_kosten"],
            lkw_km=values["lkw_km"],
            delta_lkw_km=deltas["delta_lkw_km"],
            bahn_sendungen=n_rail,
            servicegrad=_service(n_valid, n_rail, params),
        )

    return {
        "Ist": build("Ist", ist, 0, True),
        "M2": build("M2", m2, 0, False),
        "M3": build("M3", m3, len(rail), False),
    }


def cockpit_status(result: Result, params: Assumptions) -> str:
    """Cockpit Input!R8: Keine Eingabe, Eingabe prüfen, Plan zulässig, Plan prüfen."""
    n = result.n_valid
    if n == 0:
        return "Keine Eingabe"
    non_empty = sum(1 for r in result.rows if r.pruefung)
    if non_empty > n:
        return "Eingabe prüfen"
    delta_cost = result.kpis["M3"].delta_kosten or 0.0
    if delta_cost <= params.a08_kosten_tol and params.c03_laufzeit_ok == 1:
        return "Plan zulässig"
    return "Plan prüfen"


def build_routes(rows: list[ShipmentRow]) -> list[Route]:
    """Blatt Routen: eine Zeile je Relation in der Reihenfolge des ersten Auftretens."""
    groups: dict[str, list[ShipmentRow]] = defaultdict(list)
    first: list[tuple[int, ShipmentRow]] = []
    for pos, row in enumerate(rows, start=1):
        if row.relation is None:
            continue
        key = fold(row.relation)
        if row.relation_rang is not None:
            first.append((pos, row))
        groups[key].append(row)
    routes = []
    for nr, (pos, head) in enumerate(first[:ROUTES_CAPACITY], start=1):
        assert head.relation is not None
        members = [m for m in groups[fold(head.relation)] if m.ok]
        quelle = head.distanz_quelle or ""
        same = sum(1 for m in groups[fold(head.relation)] if fold(m.distanz_quelle or "") == fold(quelle))
        co2_ist = math.fsum(m.co2_ist_fzgkm or 0.0 for m in members)
        co2_plan = math.fsum(m.co2_plan_fzgkm or 0.0 for m in members)
        routes.append(
            Route(
                nr=nr,
                input_pos=pos,
                start=head.start_label or "",
                ziel=head.ziel_label or "(ohne Ziel)",
                start_lat=head.start_lat,
                start_lon=head.start_lon,
                ziel_lat=head.ziel_lat,
                ziel_lon=head.ziel_lon,
                sendungen=len(members),
                gewicht_t=math.fsum(to_number(m.shipment.gewicht_kg) for m in members) / 1000,
                distanz_km=math.fsum(m.distanz_km or 0.0 for m in members) / len(members),
                distanz_quelle=quelle if same == len(members) else "gemischt",
                tkm=math.fsum(m.tkm or 0.0 for m in members),
                co2_ist=co2_ist,
                co2_plan=co2_plan,
                delta_co2=0.0 if co2_ist == 0 else co2_plan / co2_ist - 1,
                kosten_ist=math.fsum(m.kosten_ist or 0.0 for m in members),
                kosten_plan=math.fsum(m.kosten_plan or 0.0 for m in members),
                key=head.relation,
                einsparung=round_half_away(co2_ist - co2_plan, 6),
                rang=0,
            )
        )
    values = [r.einsparung for r in routes]
    for i, route in enumerate(routes):
        higher = sum(1 for v in values if v > route.einsparung)
        ties_before = sum(1 for v in values[: i + 1] if v == route.einsparung)
        route.rang = higher + ties_before
    return routes


def load_model(data: WorkbookData) -> Model:
    """Parameter, Ortsdatenbank und Rechenbereich (Länge des Namens i_Kg) aus der Mappe."""
    return Model(
        params=load_assumptions(data),
        db=load_place_db(data),
        capacity=len(data.name_cells("i_Kg")),
    )


def workbook_shipments(data: WorkbookData) -> list[Shipment]:
    """Die Eingabezeilen Input!A14:H der Mappe (Beispieldaten), Leerzeilen eingeschlossen."""
    if not data.input_rows:
        return []
    last = data.input_rows[-1][0]
    by_row = dict(data.input_rows)
    out = []
    for excel_row in range(14, last + 1):
        values = by_row.get(excel_row, (None,) * len(INPUT_FIELDS))
        out.append(Shipment(**dict(zip(INPUT_FIELDS, values, strict=True))))
    return out


def param_field(params: Assumptions, param_id: str) -> str:
    """Feldname zu einer Parameterkennung (z. B. "A10") laut Blatt Assumptions."""
    for field, meta in params.meta.items():
        if meta.id == param_id and "[" not in field:
            return field
    raise KeyError(f"Parameter {param_id} nicht in Assumptions")


def with_changes(model: Model, changes: dict[str, object]) -> Model:
    """Kopie des Modells mit geänderten Parametern (Schlüssel: Kennung wie "A01" oder Feldname)."""
    update = {}
    for key, value in changes.items():
        field = key if key in Assumptions.model_fields else param_field(model.params, key)
        update[field] = value
    params = Assumptions.model_validate({**model.params.model_dump(), **update})
    return Model(params=params, db=model.db, capacity=model.capacity)


def parse_change(text: str) -> dict[str, object]:
    """Parameteränderung aus der Sensitivitätstabelle, z. B. "A10 = 0,10" oder "A04 = Diesel"."""
    if "=" not in text:
        return {}
    pid, raw = (part.strip() for part in text.split("=", 1))
    try:
        value: object = float(raw.replace(",", "."))
    except ValueError:
        value = raw
    return {pid: value}


def sensitivity_row(result: Result) -> dict[str, float | int]:
    """Kennzahlen einer Zeile der Sensitivitätstabelle (Overview D bis J)."""
    m2, m3 = result.kpis["M2"], result.kpis["M3"]
    return {
        "delta_co2_m2": m2.delta_co2_fzgkm or 0.0,
        "delta_co2_m3_fzgkm": m3.delta_co2_fzgkm or 0.0,
        "delta_co2_m3_tkm": m3.delta_co2_tkm or 0.0,
        "delta_kosten_m3": m3.delta_kosten or 0.0,
        "bahn_sendungen": m3.bahn_sendungen,
        "touren_gebuendelt": sum(t.gebuendelt for t in result.tours),
        "delta_lkw_km_m3": m3.delta_lkw_km or 0.0,
    }
