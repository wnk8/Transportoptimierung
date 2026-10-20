"""Die 20 Prüfungen aus Overview & Results (Abschnitt 5, Zeilen 142 bis 161) und der Gesamtstatus (C162).

Jede Prüfung vergleicht Sollwert und Istwert. Status "OK", "Fehler" oder bei den
Plausibilitätsprüfungen 14 und 18 "Hinweis". Toleranz der Summenabgleiche 0,005 wie in Excel.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import fields

from tk import analysis
from tk.excelfn import fold, to_number
from tk.models import Assumptions, CheckResult, Result, ShipmentRow, TourLine

TOLERANCE = 0.005
"""Toleranz der Summenabgleiche (Overview F142:F161)."""

DESCRIPTIONS: dict[int, tuple[str, str]] = {
    1: (
        "Eingabezeilen fehlerfrei",
        "Anzahl der Zeilen mit Hinweis in Spalte I. Diese Zeilen rechnen nicht mit.",
    ),
    2: (
        "Gewicht vollständig in Touren",
        "Σ Gewicht der Touren plus nicht bündelbare Sendungen = Σ Gewicht aller gültigen Sendungen.",
    ),
    3: (
        "Sendungen vollständig in Touren",
        "Anzahl der bündelbaren Sendungen = Anzahl der Zeilen der Tourbildung.",
    ),
    4: (
        "Plan nicht mehr Fahrzeuge als Einzelversand",
        "Der Plan setzt höchstens so viele Fahrzeuge ein wie der Einzelversand.",
    ),
    5: (
        "Fahrzeugtabelle aufsteigend",
        "Voraussetzung der Rangregel: Paletten und Nutzlast steigen von klein nach groß.",
    ),
    6: (
        "Ist-CO₂e nach Startort = Abschnitt 1",
        "Σ CO₂e der Startorttabelle = Ist-CO₂e im Methodenvergleich.",
    ),
    7: (
        "Ist-CO₂e nach Fahrzeug = Abschnitt 1",
        "Σ CO₂e der Fahrzeugtabelle = Ist-CO₂e im Methodenvergleich.",
    ),
    8: ("Ist-CO₂e nach Auslastungsklasse = Abschnitt 1", "Die fünf Klassen umfassen alle Sendungen."),
    9: ("Ist-CO₂e nach Engpass = Abschnitt 1", "Σ CO₂e der Engpasstabelle = Ist-CO₂e im Methodenvergleich."),
    10: ("Ist-CO₂e nach Monat = Abschnitt 1", "Σ CO₂e der Monatstabelle = Ist-CO₂e im Methodenvergleich."),
    11: ("Plan-CO₂e nach Verkehrsträger = Abschnitt 1", "Σ CO₂e Lkw und Bahn im Plan = CO₂e der Methode 3."),
    12: (
        "Transportleistung nach Zielort = Eingabe",
        "Σ tkm der Zielorttabelle = Σ tkm der Sendungen mit Zielort.",
    ),
    13: (
        "Kostenmodell trifft eingegebene Fracht",
        "Modellkosten x C04 treffen die Σ der eingegebenen Fracht.",
    ),
    14: (
        "Plausibilität: CO₂e Plan nicht höher als Ist",
        "Hinweis, kein Rechenfehler: Liegt der Plan über dem Ist, sind Parameter zu prüfen.",
    ),
    15: (
        "Kein Fahrzeug einer Tour überladen",
        "Touren über der Kapazität des größten Fahrzeugs. Muss 0 sein.",
    ),
    16: ("Parameter gültig", "Anzahl ungültiger Parameter in Assumptions. Muss 0 sein."),
    17: (
        "Alle Eingabezeilen im Rechenbereich",
        "Gefüllte Zellen unterhalb des Rechenbereichs. Muss 0 sein, sonst Eingabe teilen.",
    ),
    18: (
        "Eingegebene Entfernung nicht kürzer als Luftlinie",
        "Hinweis: Sendungen mit eingegebener Entfernung unter der Luftlinie.",
    ),
    19: (
        "Keine Fehlerwerte in Input, Touren und Routen",
        "Anzahl der Fehlerwerte in den Rechenergebnissen. Muss 0 sein.",
    ),
    20: (
        "Dashboard vollständig mit dem Modell verbunden",
        "Kernwerte der Kennzahlenleiste gegenüber einer unabhängigen Rechnung. Muss 0 sein.",
    ),
}


def _check(nr: int, soll: float, ist: float, kind: str = "abs") -> CheckResult:
    diff = ist - soll
    if kind == "abs":
        status = "OK" if abs(diff) < TOLERANCE else "Fehler"
    elif kind == "le":
        status = "OK" if diff <= TOLERANCE else "Fehler"
    else:  # "hint": Hinweis statt Fehler
        status = "OK" if diff <= abs(soll) * 0.000001 else "Hinweis"
    name, text = DESCRIPTIONS[nr]
    return CheckResult(nr=nr, name=name, soll=soll, ist=ist, differenz=diff, status=status, beschreibung=text)


def invalid_parameters(p: Assumptions) -> int:
    """Prüfung 16 (Overview D157): Anzahl ungültiger Parameter."""
    numbers = [
        p.a01_bahn_grenze_km,
        p.a02_vnl_km,
        p.a05_zusatz_tage,
        p.a06_max_tage,
        p.a07_bahn_aufschlag,
        p.a08_kosten_tol,
        p.a09_schwelle,
        p.a10_umweg,
        p.a11_alpha,
        p.a14_kg_je_palette,
        p.i01_strassenfaktor,
        p.i02_ort_streuung_km,
        p.i03_erdradius_km,
    ]
    count = sum(1 for x in numbers if not math.isfinite(x))
    count += int(p.a01_bahn_grenze_km <= 0) + int(p.a14_kg_je_palette <= 0) + int(p.a02_vnl_km < 0)
    count += int(p.a05_zusatz_tage < 0) + int(p.a06_max_tage < 0) + int(p.a07_bahn_aufschlag < 0)
    count += int(p.a08_kosten_tol < 0) + int(p.a10_umweg < 0)
    count += int(p.a09_schwelle <= 0 or p.a09_schwelle > 1) + int(p.a11_alpha < 0 or p.a11_alpha > 1)
    for v in p.vehicles:
        count += int(v.paletten <= 0) + int(v.nutzlast_kg <= 0)
        count += int(v.kostensatz_eur_km <= 0) + int(v.referenz_auslastung <= 0)
    count += int(p.c02_vnl_faktor is None)
    count += int(fold(p.a04_traktion) not in ("diesel", "elektrisch"))
    count += int(p.i01_strassenfaktor < 1) + int(p.i02_ort_streuung_km <= 0) + int(p.i03_erdradius_km <= 0)
    return count


def _error_values(rows: list[ShipmentRow], lines: list[TourLine], result: Result) -> int:
    count = 0
    objs: list[ShipmentRow | TourLine] = [*rows, *lines]
    for obj in objs:
        for f in fields(obj):
            value = getattr(obj, f.name)
            if isinstance(value, float) and not math.isfinite(value):
                count += 1
    for route in result.routes:
        for value in route.model_dump().values():
            if isinstance(value, float) and not math.isfinite(value):
                count += 1
    return count


def _dashboard_mismatch(result: Result, p: Assumptions) -> int:
    ok = result.valid_rows

    def ratio(plan: str, ist: str) -> float:
        base = math.fsum(getattr(r, ist) or 0.0 for r in ok)
        return 0.0 if base == 0 else math.fsum(getattr(r, plan) or 0.0 for r in ok) / base - 1

    m3 = result.kpis["M3"]
    n = result.n_valid
    rail = sum(1 for r in ok if r.bahn == "Ja")
    service = 1.0 if n == 0 else (1 - rail / n if p.a05_zusatz_tage > 0 else 1.0)
    in_bundles = sum(t.sendungen for t in result.tours if t.gebuendelt == 1)
    modes = rail + in_bundles + (n - rail - in_bundles)
    count = int(abs((m3.delta_co2_fzgkm or 0.0) - ratio("co2_plan_fzgkm", "co2_ist_fzgkm")) > 1e-6)
    count += int(abs((m3.delta_kosten or 0.0) - ratio("kosten_plan", "kosten_ist")) > 1e-6)
    count += int(abs((m3.delta_lkw_km or 0.0) - ratio("lkw_km_plan", "lkw_km_ist")) > 1e-6)
    count += int(abs(m3.servicegrad - service) > 1e-6)
    count += int(abs(modes - n) > 1e-6)
    return count


def run_checks(result: Result, p: Assumptions) -> list[CheckResult]:
    """Alle 20 Prüfungen in der Reihenfolge von Overview & Results Abschnitt 5."""
    ok = result.valid_rows
    ist = result.kpis["Ist"]
    m3 = result.kpis["M3"]
    co2_ist = ist.co2_fzgkm_kg
    non_ok = sum(1 for r in result.rows if r.pruefung and r.pruefung != "OK")
    kg_ok = math.fsum(to_number(r.shipment.gewicht_kg) for r in ok)
    kg_tours = math.fsum(line.gewicht_kg for line in result.tour_lines)
    kg_not_eligible = math.fsum(to_number(r.shipment.gewicht_kg) for r in ok if r.buendelbar == 0)
    vehicles = p.vehicles
    ascending = all(
        a.paletten < b.paletten and a.nutzlast_kg < b.nutzlast_kg for a, b in itertools.pairwise(vehicles)
    )
    with_fracht = [r for r in ok if (r.shipment.fracht_eur or 0) and to_number(r.shipment.fracht_eur) > 0]
    tkm_with_ziel = math.fsum(r.tkm or 0.0 for r in ok if r.ziel_label)
    overloaded = sum(1 for t in result.tours if t.gewicht_kg > p.max_kg) + sum(
        1 for t in result.tours if t.paletten > p.max_paletten
    )
    return [
        _check(1, 0, non_ok),
        _check(2, kg_ok, kg_tours + kg_not_eligible),
        _check(3, sum(1 for r in ok if r.buendelbar == 1), len(result.tour_lines)),
        _check(4, sum(r.fahrzeuge_n or 0 for r in ok), sum(r.fahrzeuge_plan or 0 for r in ok), "le"),
        _check(5, 1, 1 if ascending else 0),
        _check(6, co2_ist, math.fsum(line.co2 for line in analysis.by_start(result))),
        _check(7, co2_ist, math.fsum(line.co2 for line in analysis.by_vehicle(result, p))),
        _check(8, co2_ist, math.fsum(line.co2 for line in analysis.by_utilization(result))),
        _check(9, co2_ist, math.fsum(line.co2 for line in analysis.by_bottleneck(result))),
        _check(10, co2_ist, math.fsum(line.co2 for line in analysis.by_month(result))),
        _check(11, m3.co2_fzgkm_kg, math.fsum(line.co2 for line in analysis.by_mode(result))),
        _check(12, tkm_with_ziel, math.fsum(d.tkm for d in analysis.by_destination(result))),
        _check(
            13,
            math.fsum(to_number(r.shipment.fracht_eur) for r in with_fracht),
            math.fsum(r.kosten_modell or 0.0 for r in with_fracht) * result.c04,
        ),
        _check(14, co2_ist, m3.co2_fzgkm_kg, "hint"),
        _check(15, 0, overloaded),
        _check(16, 0, invalid_parameters(p)),
        _check(17, 0, result.overflow_cells),
        _check(18, 0, sum(r.plausibel or 0 for r in ok), "hint"),
        _check(19, 0, _error_values(result.rows, result.tour_lines, result)),
        _check(20, 0, _dashboard_mismatch(result, p)),
    ]


def overall_status(checks: list[CheckResult], n_valid: int) -> str:
    """Gesamtstatus (Overview C162)."""
    if checks[15].status == "Fehler":
        return "Parameter ungültig, siehe Prüfung 16"
    errors = sum(1 for c in checks if c.status == "Fehler")
    if errors:
        return f"{errors} Prüfung(en) fehlerhaft"
    if n_valid == 0:
        return "Keine Eingabe"
    return "Alle Prüfungen bestanden"
