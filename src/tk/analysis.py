"""Auswertungen der Eingabedaten (Overview & Results Abschnitte 3, 4 und 7).

Die Tabellen dienen der Anzeige und den Prüfungen 6 bis 12 (Summenabgleich).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable
from dataclasses import dataclass

from tk.excelfn import fold, to_number
from tk.models import Assumptions, Result, ShipmentRow

UTILIZATION_CLASSES: tuple[tuple[str, float, float], ...] = (
    ("unter 20 %", 0.0, 0.2),
    ("20 % bis unter 40 %", 0.2, 0.4),
    ("40 % bis unter 60 %", 0.4, 0.6),
    ("60 % bis unter 80 %", 0.6, 0.8),
    ("80 % und mehr", 0.8, math.inf),
)
"""Auslastungsklassen (Definition, Assumptions K3.7)."""

MONTHS = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)
START_ROWS = 10
"""Startorte einzeln in Overview Abschnitt 4 (B64:B73), weitere in einer Sammelzeile."""
ZIEL_ROWS = 15
"""Zielorte einzeln in Overview Abschnitt 4 (B123:B137), weitere in einer Sammelzeile."""


@dataclass(slots=True)
class Line:
    """Zeile einer Analysetabelle (Fahrten, Sendungen, Lkw-km, Auslastung, CO2e, Kosten)."""

    kategorie: str
    fahrten: float
    sendungen: int
    lkw_km: float
    auslastung: float | None
    co2: float
    anteil: float
    kosten: float
    g_je_tkm: float | None


def _line(name: str, rows: list[ShipmentRow], total_co2: float, plan: bool = False) -> Line:
    tkm = math.fsum(r.tkm or 0.0 for r in rows)
    co2 = math.fsum((r.co2_plan_fzgkm if plan else r.co2_ist_fzgkm) or 0.0 for r in rows)
    return Line(
        kategorie=name,
        fahrten=math.fsum((r.fahrzeuge_plan if plan else r.fahrzeuge_n) or 0 for r in rows),
        sendungen=len(rows),
        lkw_km=math.fsum((r.lkw_km_plan if plan else r.lkw_km_ist) or 0.0 for r in rows),
        auslastung=statistics.fmean(r.auslastung or 0.0 for r in rows) if rows else None,
        co2=co2,
        anteil=0.0 if total_co2 == 0 else co2 / total_co2,
        kosten=math.fsum((r.kosten_plan if plan else r.kosten_ist) or 0.0 for r in rows),
        g_je_tkm=None if tkm == 0 else co2 * 1000 / tkm,
    )


def _by_rank(
    ok: list[ShipmentRow],
    label: Callable[[ShipmentRow], str | None],
    rank: Callable[[ShipmentRow], int | None],
    limit: int,
) -> tuple[list[tuple[str, list[ShipmentRow]]], list[ShipmentRow]]:
    ordered = sorted((rank(r), label(r) or "") for r in ok if rank(r) is not None)
    shown = [name for _, name in ordered[:limit]]
    keys = {fold(n) for n in shown}
    groups = [(n, [r for r in ok if fold(label(r) or "") == fold(n)]) for n in shown]
    rest = [r for r in ok if label(r) and fold(label(r) or "") not in keys]
    return groups, rest


def by_start(result: Result) -> list[Line]:
    ok = result.valid_rows
    total = math.fsum(r.co2_ist_fzgkm or 0.0 for r in ok)
    groups, rest = _by_rank(ok, lambda r: r.start_label, lambda r: r.start_rang, START_ROWS)
    lines = [_line(n, rows, total) for n, rows in groups]
    if rest:
        lines.append(_line("Weitere Startorte", rest, total))
    return lines


def by_vehicle(result: Result, params: Assumptions) -> list[Line]:
    ok = result.valid_rows
    total = math.fsum(r.co2_ist_fzgkm or 0.0 for r in ok)
    return [
        _line(v.name, [r for r in ok if fold(r.fahrzeug or "") == fold(v.name)], total)
        for v in params.vehicles
    ]


def by_mode(result: Result) -> list[Line]:
    """Nach Verkehrsträger im Plan (Methode 3), Overview Zeilen 86 und 87."""
    ok = result.valid_rows
    total = math.fsum(r.co2_plan_fzgkm or 0.0 for r in ok)
    lkw = [r for r in ok if r.bahn == "Nein"]
    bahn = [r for r in ok if r.bahn == "Ja"]
    return [_line("Lkw", lkw, total, plan=True), _line("Bahn", bahn, total, plan=True)]


def by_utilization(result: Result) -> list[Line]:
    ok = result.valid_rows
    total = math.fsum(r.co2_ist_fzgkm or 0.0 for r in ok)
    return [
        _line(name, [r for r in ok if lo <= (r.auslastung or 0.0) < hi], total)
        for name, lo, hi in UTILIZATION_CLASSES
    ]


def by_bottleneck(result: Result) -> list[Line]:
    ok = result.valid_rows
    total = math.fsum(r.co2_ist_fzgkm or 0.0 for r in ok)
    return [_line(n, [r for r in ok if r.engpass == n], total) for n in ("Gewicht", "Paletten")]


def by_month(result: Result) -> list[Line]:
    ok = result.valid_rows
    total = math.fsum(r.co2_ist_fzgkm or 0.0 for r in ok)
    return [
        _line(f"{i:02d} {name}", [r for r in ok if r.monat == i], total)
        for i, name in enumerate(MONTHS, start=1)
    ]


@dataclass(slots=True)
class DestLine:
    zielort: str
    sendungen: int
    gewicht_t: float
    tkm: float
    entfernung_km: float | None
    kosten: float
    anteil_tkm: float
    kosten_je_tkm: float


def by_destination(result: Result) -> list[DestLine]:
    ok = result.valid_rows
    total_tkm = math.fsum(r.tkm or 0.0 for r in ok)
    groups, rest = _by_rank(ok, lambda r: r.ziel_label, lambda r: r.ziel_rang, ZIEL_ROWS)
    if rest:
        groups.append(("Weitere Zielorte", rest))
    out = []
    for name, rows in groups:
        tkm = math.fsum(r.tkm or 0.0 for r in rows)
        kosten = math.fsum(r.kosten_ist or 0.0 for r in rows)
        out.append(
            DestLine(
                zielort=name,
                sendungen=len(rows),
                gewicht_t=math.fsum(to_number(r.shipment.gewicht_kg) for r in rows) / 1000,
                tkm=tkm,
                entfernung_km=statistics.fmean(r.distanz_km or 0.0 for r in rows) if rows else None,
                kosten=kosten,
                anteil_tkm=0.0 if total_tkm == 0 else tkm / total_tkm,
                kosten_je_tkm=0.0 if tkm == 0 else kosten / tkm,
            )
        )
    return out


def input_figures(result: Result, params: Assumptions) -> dict[str, float | int | None]:
    """Kennzahlen der Eingabedaten (Overview Abschnitt 3) und Eingabequalität (Abschnitt 7)."""
    ok = result.valid_rows
    n = len(ok)
    kg = math.fsum(to_number(r.shipment.gewicht_kg) for r in ok)
    tkm = math.fsum(r.tkm or 0.0 for r in ok)
    util = [r.auslastung or 0.0 for r in ok]
    bundled = [t for t in result.tours if t.gebuendelt == 1]
    return {
        "sendungen_gueltig": n,
        "zeilen_mit_hinweis": sum(1 for r in result.rows if r.pruefung and r.pruefung != "OK"),
        "einzelfahrten": sum(r.fahrzeuge_n or 0 for r in ok),
        "gewicht_t": kg / 1000,
        "tkm": tkm,
        "mittlere_distanz_km": None if n == 0 or kg == 0 else tkm / (kg / 1000),
        "mittlere_auslastung": statistics.fmean(util) if util else None,
        "median_auslastung": statistics.median(util) if util else None,
        "anteil_unter_schwelle": 0.0 if n == 0 else sum(1 for u in util if u < params.a09_schwelle) / n,
        "touren": len(result.tours),
        "touren_gebuendelt": len(bundled),
        "sendungen_in_gebuendelten_touren": sum(t.sendungen for t in bundled),
        "fahrzeuge_aggregiert": sum(t.fahrzeuge_aggregiert or 0 for t in result.tour_lines),
        "c04": result.c04,
        "relationen": len({fold(r.relation or "") for r in ok}),
    }
