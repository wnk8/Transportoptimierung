"""Tests T01 bis T10 aus Assumptions K4 (Testprotokoll), nachgebaut nach der Beschreibung.

Die Datensätze der Excel-Tests liegen nicht vor (nur ``testprotokoll_v11.json`` mit
Ergebnissen). Die Tests bauen Datensätze nach der Beschreibung in Assumptions D299:D313
und prüfen das dort dokumentierte Verhalten: gültige Zeilen, Fehlermeldungen,
Prüfungen und Gesamtstatus. Die Nummerierung folgt der Excel.
"""

from __future__ import annotations

import datetime as dt
import math

import pytest

from tests.conftest import needs_excel
from tests.refdata import model_and_result
from tk.models import Result, Shipment
from tk.scenarios import Model, calculate, with_changes

pytestmark = needs_excel

STARTS = [
    "70173 Stuttgart", "68159 Mannheim", "76131 Karlsruhe", "55116 Mainz", "60311 Frankfurt am Main",
    "80331 München", "20095 Hamburg", "50667 Köln", "30159 Hannover", "01067 Dresden",
    "79098 Freiburg im Breisgau", "90402 Nürnberg", "04109 Leipzig", "28195 Bremen",
]  # fmt: skip
ZIELE = [
    *STARTS,
    "10115 Berlin", "44135 Dortmund", "45127 Essen", "40213 Düsseldorf", "53111 Bonn",
    "24103 Kiel", "18055 Rostock", "66111 Saarbrücken",
]  # fmt: skip


def model() -> Model:
    return model_and_result()[0]


def dataset(
    n: int, starts: int, ziele: int, days: int = 30, seed: int = 1, **extra: object
) -> list[Shipment]:
    out = []
    for i in range(n):
        k = (i * 7919 + seed) % 10007
        start = STARTS[k % starts]
        ziel = ZIELE[(k // 3) % ziele]
        if ziel == start:
            ziel = ZIELE[(k // 3 + 1) % ziele]
        day = dt.date(2025, 1, 2) + dt.timedelta(days=k % days)
        out.append(
            Shipment(
                datum=day.isoformat(),
                start=start,
                ziel=ziel,
                gewicht_kg=float(20 + (k * 37) % 2800),
                sendungs_id=f"T{i:05d}",
                **extra,  # type: ignore[arg-type]
            )
        )
    return out


def assert_passed(result: Result) -> None:
    assert result.gesamtstatus == "Alle Prüfungen bestanden", [c for c in result.checks if c.status != "OK"]


def test_t01_many_places_two_years_mixed_formats() -> None:
    ships = dataset(500, 14, 22)
    mixed = []
    for i, s in enumerate(ships):
        day = dt.date(2025 + i % 2, 1 + i % 12, 1 + i % 28)
        datum: object = [day.isoformat(), day.strftime("%d.%m.%Y"), day][i % 3]
        extra = {"paletten": None if i % 2 else 1 + i % 5, "fracht_eur": None if i % 3 else 100.0 + i}
        mixed.append(s.model_copy(update={"datum": datum, **extra}))
    result = calculate(mixed, model())
    assert result.n_valid == 500
    assert {r.distanz_quelle for r in result.valid_rows} == {"Näherung (Luftlinie x I01)"}
    assert_passed(result)


def test_t02_single_shipment() -> None:
    ship = Shipment(datum="2025-05-05", start="70173 Stuttgart", ziel="20095 Hamburg", gewicht_kg=800)
    result = calculate([ship], model())
    assert result.n_valid == 1
    assert result.rows[0].bahn == "Ja"  # 545 km Luftlinie x 1,22 > A01
    assert result.kpis["M3"].servicegrad == 0
    assert_passed(result)


def test_t03_optional_fields_missing() -> None:
    ships = [
        Shipment(datum=dt.date(2025, 2, 3), start=70173, ziel=None, km=120.0 + i, gewicht_kg=300.0 + i)
        for i in range(20)
    ] + [
        Shipment(datum=dt.date(2025, 2, 4), start=68159, ziel=55116, gewicht_kg=200.0 + i) for i in range(20)
    ]
    result = calculate(ships, model())
    assert result.n_valid == 40
    assert result.rows[0].distanz_quelle == "Eingabe"
    assert result.rows[0].start_label == "70173 Stuttgart"
    assert result.rows[25].distanz_quelle == "Näherung (Luftlinie x I01)"
    first_tour = [line for line in result.tour_lines if line.tour_nr == 1]
    assert all(line.neuer_stopp == 1 for line in first_tour)  # ohne Ziel: jede Sendung ein Stopp
    assert_passed(result)


def test_t04_new_places_and_place_logic() -> None:
    db = model().db
    unsure = next(str(k) for k, q in zip(db.keys, db.qual, strict=False) if q == "unsicher")
    base = {"datum": "2025-04-01", "gewicht_kg": 500}
    ok_rows = [
        Shipment(start="Köln", ziel="55116 Mainz", **base),  # Ortsname
        Shipment(start="50667 Köln", ziel="Mainz", **base),  # Label
        Shipment(start=50667, ziel=55116, **base),  # PLZ als Zahl
        Shipment(start="  50667   Köln ", ziel=" 55116 ", **base),  # Leerzeichen
        Shipment(start="KÖLN", ziel="mainz", **base),  # Groß-/Kleinschreibung
        Shipment(start="Atlantis", ziel="Mainz", km=300, **base),  # unbekannt, aber km
        Shipment(start="Aach", ziel="Mainz", km=250, **base),  # mehrdeutig, aber km
        Shipment(start=unsure, ziel="Mainz", km=200, **base),  # unsicher, aber km
        Shipment(start="70173", ziel="70173", km=15, **base),  # gleich, aber km
    ]
    bad_rows = [
        (Shipment(start="Atlantis", ziel="Mainz", **base), "Start nicht gefunden"),
        (Shipment(start="Mainz", ziel="Atlantis", **base), "Ziel nicht gefunden"),
        (Shipment(start="Aach", ziel="Mainz", **base), "Start mehrdeutig: PLZ nötig"),
        (Shipment(start=unsure, ziel="Mainz", **base), "PLZ unsicher: km eingeben"),
        (Shipment(start="70173", ziel="70173 Stuttgart", **base), "Start gleich Ziel: km nötig"),
    ]
    result = calculate(ok_rows + [s for s, _ in bad_rows], model())
    assert result.n_valid == 9
    assert [r.pruefung for r in result.rows[9:]] == [m for _, m in bad_rows]
    assert result.rows[0].start_label == "Köln (Ort)"
    assert result.checks[0].status == "Fehler"
    assert result.gesamtstatus == "1 Prüfung(en) fehlerhaft"


def test_t05_several_vehicles_per_shipment() -> None:
    ships = [
        s.model_copy(update={"gewicht_kg": float(500 + (i * 977) % 60000), "paletten": 1 + i % 50})
        for i, s in enumerate(dataset(253, 3, 6))
    ]
    result = calculate(ships, model())
    multi = [r for r in result.valid_rows if (r.fahrzeuge_n or 0) > 1]
    assert multi and all(r.fahrzeug == "Sattelzug 40t" and r.buendelbar == 0 for r in multi)
    assert_passed(result)


@pytest.mark.parametrize(
    ("name", "changes"),
    [
        ("T06a", {"A04": "Diesel", "A11": 0.7}),
        ("T06b", {"A05": 0}),
        ("T06c", {"A05": 3}),
        ("T06d", {"A01": 300, "A10": 0.35, "A09": 0.9, "A08": 0.3}),
        ("T06e", {"I01": 1.10, "A07": 0.2}),
        ("T06f", {"A03": "Sattelzug 40t", "A14": 150}),
    ],
)
def test_t06_parameter_variants(name: str, changes: dict[str, object]) -> None:
    m = with_changes(model(), changes)
    result = calculate(dataset(400, 5, 12), m)
    assert result.n_valid == 400
    assert_passed(result)
    kpis = result.kpis
    if name == "T06a":
        assert m.params.c01_bahn_faktor == m.params.bahn_diesel_g_tkm
    if name == "T06b":
        assert kpis["M3"].servicegrad == 1
    if name in ("T06c", "T06e"):
        assert kpis["M3"].bahn_sendungen == 0
        assert kpis["M3"].co2_fzgkm_kg == pytest.approx(kpis["M2"].co2_fzgkm_kg, rel=1e-12)
    if name == "T06f":
        assert m.params.c02_vnl_faktor == m.params.vehicles[-1].g_tkm


def test_t07_full_capacity() -> None:
    result = calculate(dataset(2500, 8, 20, days=200), model())
    assert result.n_valid == 2500
    assert result.overflow_cells == 0
    assert_passed(result)


def test_t08_overflow_row_2501() -> None:
    result = calculate(dataset(2501, 8, 20, days=200), model())
    assert result.n_valid == 2500
    assert result.overflow_cells > 0
    assert result.checks[16].status == "Fehler"
    assert result.gesamtstatus == "1 Prüfung(en) fehlerhaft"


def test_t09_invalid_inputs() -> None:
    base = {"datum": "2025-06-02", "start": "70173", "ziel": "55116", "gewicht_kg": 100}
    rows = [
        (Shipment(**base, sendungs_id="X1"), "OK"),
        (Shipment(**base, sendungs_id="X1"), "OK"),  # doppelte ID ist kein Fehler
        (Shipment(**{**base, "gewicht_kg": -5}), "Gewicht ≤ 0"),
        (Shipment(**{**base, "gewicht_kg": "viel"}), "Gewicht ist keine Zahl"),
        (Shipment(**{**base, "datum": "31.02.2025"}), "Datum ungültig"),
        (Shipment(**{**base, "datum": None}), "Datum fehlt"),
        (Shipment(**{**base, "start": None}), "Start fehlt"),
        (Shipment(**{**base, "ziel": None}), "Ziel oder Entfernung fehlt"),
        (Shipment(**{**base, "gewicht_kg": None}), "Gewicht fehlt"),
        (Shipment(**base, km="weit"), "Entfernung ist keine Zahl"),
        (Shipment(**base, km=0), "Entfernung ≤ 0"),
        (Shipment(**base, paletten="zwei"), "Paletten keine Zahl"),
        (Shipment(**base, paletten=-1), "Paletten ≤ 0"),
        (Shipment(**base, fracht_eur="teuer"), "Fracht keine Zahl"),
        (Shipment(**base, fracht_eur=12.5), "OK"),
    ]
    result = calculate([s for s, _ in rows] + [Shipment(**base, sendungs_id="X9")], model())
    assert [r.pruefung for r in result.rows[: len(rows)]] == [m for _, m in rows]
    assert result.n_valid == 4
    assert result.gesamtstatus == "1 Prüfung(en) fehlerhaft"


def test_t10_next_fit_many_small_same_day() -> None:
    ships = [
        Shipment(
            datum="2025-07-01",
            start="68159 Mannheim",
            ziel=ZIELE[8 + i % 6],
            gewicht_kg=50.0 + (i * 13) % 400,
        )
        for i in range(300)
    ]
    result = calculate(ships, model())
    p = model().params
    total_kg = math.fsum(float(s.gewicht_kg) for s in ships)  # type: ignore[arg-type]
    assert len(result.tours) >= math.ceil(total_kg / p.max_kg)
    assert all(t.gewicht_kg <= p.max_kg and t.paletten <= p.max_paletten for t in result.tours)
    groups = {line.gruppe for line in result.tour_lines}
    assert len(groups) == 1
    distances = [line.distanz_km for line in result.tour_lines]
    assert distances == sorted(distances, reverse=True)  # Rang: Entfernung absteigend
    assert_passed(result)
