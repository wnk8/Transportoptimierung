"""Datenmodelle (pydantic v2) für Sendungen, Parameter, Touren und Ergebnisse.

``Shipment`` bildet eine Eingabezeile des Blatts Input (Spalten A bis H) ab. Die Felder
nehmen Rohwerte auf (Text, Zahl, Datum oder leer), weil die Eingabeprüfung (Spalte I)
genau diese Rohwerte bewertet. ``ShipmentRow`` hält die Rechenspalten I bis BK einer
Zeile, ``Tour`` eine Tour des Blatts Touren, ``ScenarioKpis`` und ``Result`` die
Kennzahlen aus Overview & Results Abschnitt 1.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict

CellValue = str | int | float | dt.datetime | dt.date | None

INPUT_COLUMNS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")
INPUT_FIELDS: tuple[str, ...] = (
    "datum",
    "start",
    "ziel",
    "gewicht_kg",
    "sendungs_id",
    "km",
    "paletten",
    "fracht_eur",
)
INPUT_HEADERS: tuple[str, ...] = (
    "Datum",
    "Start (PLZ oder Ort)",
    "Ziel (PLZ oder Ort)",
    "Gewicht kg",
    "Sendungs-ID",
    "Entfernung km",
    "Paletten",
    "Frachtkosten EUR",
)


class Shipment(BaseModel):
    """Eingabezeile im Schema von Input!A:H (Pflicht A bis D, optional E bis H)."""

    model_config = ConfigDict(frozen=True)

    datum: CellValue = None
    start: CellValue = None
    ziel: CellValue = None
    gewicht_kg: CellValue = None
    sendungs_id: CellValue = None
    km: CellValue = None
    paletten: CellValue = None
    fracht_eur: CellValue = None

    def cells(self) -> tuple[CellValue, ...]:
        return tuple(getattr(self, name) for name in INPUT_FIELDS)

    def is_empty(self) -> bool:
        return all(v is None or v == "" for v in self.cells())


@dataclass(slots=True)
class ShipmentRow:
    """Rechenspalten einer Input-Zeile (Spalten I bis BK). ``None`` entspricht ``""`` in Excel."""

    excel_row: int
    shipment: Shipment
    pruefung: str | None = None  # I
    datum_serial: int | None = None  # J
    start_key: str | None = None  # K
    start_art: str | None = None  # L
    start_row: int | None = None  # M (1-based position in PLZ_Orte)
    start_label: str | None = None  # N
    start_lat: float | None = None  # O
    start_lon: float | None = None  # P
    ziel_key: str | None = None  # Q
    ziel_art: str | None = None  # R
    ziel_row: int | None = None  # S
    ziel_label: str | None = None  # T
    ziel_lat: float | None = None  # U
    ziel_lon: float | None = None  # V
    luftlinie_km: float | None = None  # W
    relation_km: float | None = None  # X
    naeherung_km: float | None = None  # Y
    distanz_km: float | None = None  # Z
    distanz_quelle: str | None = None  # AA
    paletten: float | None = None  # AB
    tkm: float | None = None  # AC
    fahrzeuge_n: int | None = None  # AD
    fahrzeug_rang: int | None = None  # AE (1-based)
    fahrzeug: str | None = None  # AF
    auslastung: float | None = None  # AG
    lkw_km_ist: float | None = None  # AH
    co2_ist_fzgkm: float | None = None  # AI
    co2_ist_tkm: float | None = None  # AJ
    kosten_modell: float | None = None  # AK
    kosten_ist: float | None = None  # AL
    kosten_bahn: float | None = None  # AM
    bahn: str | None = None  # AN ("Ja" / "Nein")
    co2_bahn: float | None = None  # AO
    gruppe: int | None = None  # AP
    buendelbar: int | None = None  # AQ
    rang_gruppe: int | None = None  # AR
    sortkey: int | None = None  # AS
    touren_zeile: int | None = None  # AT (1-based)
    tour_nr: int | None = None  # AU
    sendungen_tour: int | None = None  # AV
    tour_gebuendelt: int | None = None  # AW
    fahrzeuge_plan: int | None = None  # AX
    fahrzeug_plan: str | None = None  # AY
    lkw_km_plan: float | None = None  # AZ
    co2_plan_fzgkm: float | None = None  # BA
    co2_plan_tkm: float | None = None  # BB
    kosten_plan: float | None = None  # BC
    ergebnis: str | None = None  # BD
    monat: int | None = None  # BE
    start_rang: int | None = None  # BF
    ziel_rang: int | None = None  # BG
    engpass: str | None = None  # BH
    relation: str | None = None  # BI
    relation_rang: int | None = None  # BJ
    plausibel: int | None = None  # BK

    @property
    def ok(self) -> bool:
        return self.pruefung == "OK"


ROW_COLUMNS: dict[str, str] = {
    "I": "pruefung",
    "J": "datum_serial",
    "K": "start_key",
    "L": "start_art",
    "M": "start_row",
    "N": "start_label",
    "O": "start_lat",
    "P": "start_lon",
    "Q": "ziel_key",
    "R": "ziel_art",
    "S": "ziel_row",
    "T": "ziel_label",
    "U": "ziel_lat",
    "V": "ziel_lon",
    "W": "luftlinie_km",
    "X": "relation_km",
    "Y": "naeherung_km",
    "Z": "distanz_km",
    "AA": "distanz_quelle",
    "AB": "paletten",
    "AC": "tkm",
    "AD": "fahrzeuge_n",
    "AE": "fahrzeug_rang",
    "AF": "fahrzeug",
    "AG": "auslastung",
    "AH": "lkw_km_ist",
    "AI": "co2_ist_fzgkm",
    "AJ": "co2_ist_tkm",
    "AK": "kosten_modell",
    "AL": "kosten_ist",
    "AM": "kosten_bahn",
    "AN": "bahn",
    "AO": "co2_bahn",
    "AP": "gruppe",
    "AQ": "buendelbar",
    "AR": "rang_gruppe",
    "AS": "sortkey",
    "AT": "touren_zeile",
    "AU": "tour_nr",
    "AV": "sendungen_tour",
    "AW": "tour_gebuendelt",
    "AX": "fahrzeuge_plan",
    "AY": "fahrzeug_plan",
    "AZ": "lkw_km_plan",
    "BA": "co2_plan_fzgkm",
    "BB": "co2_plan_tkm",
    "BC": "kosten_plan",
    "BD": "ergebnis",
    "BE": "monat",
    "BF": "start_rang",
    "BG": "ziel_rang",
    "BH": "engpass",
    "BI": "relation",
    "BJ": "relation_rang",
    "BK": "plausibel",
}
"""Zuordnung Excel-Spalte zu Attribut von :class:`ShipmentRow`."""


@dataclass(slots=True)
class TourLine:
    """Eine Zeile des Blatts Touren (eine bündelbare Sendung in sortierter Reihenfolge)."""

    nr: int  # A
    sortkey: int  # B
    input_pos: int  # C (1-based position in Input)
    sendung: str  # D
    gruppe: int  # E
    start: str  # F
    ziel: str  # G
    distanz_km: float  # H
    gewicht_kg: float  # I
    paletten: float  # J
    tkm: float  # K
    auslastung: float  # L
    co2_ist: float  # M
    kosten_ist: float  # N
    neue_gruppe: int  # O
    neue_tour: int  # P
    ladung_kg: float  # Q
    ladung_pal: float  # R
    tour_nr: int  # S
    neuer_stopp: int  # T
    anteil: float = 0.0  # AM
    fahrzeuge_plan: int = 0  # AN
    fahrzeug_plan: str = ""  # AO
    lkw_km_plan: float = 0.0  # AP
    co2_plan: float = 0.0  # AQ
    co2_plan_tkm: float = 0.0  # AR
    kosten_plan: float = 0.0  # AS
    fahrzeuge_aggregiert: int | None = None  # AT (first line of a group only)


class Tour(BaseModel):
    """Tourdaten aus der ersten Zeile einer Tour im Blatt Touren (Spalten U bis AI)."""

    tour_nr: int
    gruppe: int
    start: str
    erste_zeile: int  # AJ (1-based line in Touren)
    sendungen: int  # U
    stopps: int  # V
    gewicht_kg: float  # W
    paletten: float  # X
    max_distanz_km: float  # Y
    min_auslastung: float  # Z
    co2_einzel: float  # AA
    kosten_einzel: float  # AB
    tkm: float  # AC
    fahrzeug_rang: int  # AD
    fahrzeug: str
    lkw_km: float  # AE
    co2: float  # AF
    co2_tkm: float  # AG
    kosten: float  # AH
    gebuendelt: int  # AI
    sendungen_ids: tuple[str, ...] = ()


ScenarioName = Literal["Ist", "M2", "M3"]


class ScenarioKpis(BaseModel):
    """Eine Zeile des Methodenvergleichs (Overview & Results, Zeilen 10 bis 12)."""

    name: ScenarioName
    co2_fzgkm_kg: float
    delta_co2_fzgkm: float | None
    co2_tkm_kg: float
    delta_co2_tkm: float | None
    kosten_eur: float
    delta_kosten: float | None
    lkw_km: float
    delta_lkw_km: float | None
    bahn_sendungen: int
    servicegrad: float


class Route(BaseModel):
    """Eine Relation des Blatts Routen."""

    nr: int
    input_pos: int
    start: str
    ziel: str
    start_lat: float | None
    start_lon: float | None
    ziel_lat: float | None
    ziel_lon: float | None
    sendungen: int
    gewicht_t: float
    distanz_km: float
    distanz_quelle: str
    tkm: float
    co2_ist: float
    co2_plan: float
    delta_co2: float
    kosten_ist: float
    kosten_plan: float
    key: str
    einsparung: float
    rang: int


class CheckResult(BaseModel):
    """Eine der 20 Prüfungen aus Overview & Results Abschnitt 5."""

    nr: int
    name: str
    soll: float
    ist: float
    differenz: float
    status: Literal["OK", "Fehler", "Hinweis"]
    beschreibung: str


@dataclass(slots=True)
class Result:
    """Vollständiges Ergebnis eines Rechenlaufs."""

    rows: list[ShipmentRow]
    tour_lines: list[TourLine]
    tours: list[Tour]
    kpis: dict[str, ScenarioKpis]
    routes: list[Route]
    c04: float
    n_valid: int
    status: str
    overflow_cells: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    gesamtstatus: str = ""

    @property
    def valid_rows(self) -> list[ShipmentRow]:
        return [r for r in self.rows if r.ok]


class ParamMeta(BaseModel):
    """Beschreibung eines Parameters aus dem Blatt Assumptions."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    unit: str
    typ: str
    quelle: str
    zelle: str


class Vehicle(BaseModel):
    """Eine Fahrzeugklasse (Assumptions B1, B2, B3 und C2; Reihenfolge klein nach groß)."""

    model_config = ConfigDict(frozen=True)

    name: str
    paletten: float  # B1, v_Pal
    nutzlast_kg: float  # B1, v_Kg
    verbrauch_l_km: float  # B2, v_Verbrauch
    g_tkm: float  # B3, v_gTkm
    kostensatz_eur_km: float  # C2, v_Kostensatz
    referenz_auslastung: float  # C2, v_LFref


class Assumptions(BaseModel):
    """Alle Parameter des Blatts Assumptions (A01 bis A14, B, C2, I01 bis I03).

    Keine Standardwerte im Code: Instanzen entstehen nur über
    :func:`tk.assumptions.load_assumptions` aus der Excel-Mappe.
    """

    model_config = ConfigDict(frozen=True)

    a01_bahn_grenze_km: float
    a02_vnl_km: float
    a03_vnl_fahrzeug: str
    a04_traktion: str
    a05_zusatz_tage: float
    a06_max_tage: float
    a07_bahn_aufschlag: float
    a08_kosten_tol: float
    a09_schwelle: float
    a10_umweg: float
    a11_alpha: float
    a12_diesel_kg_co2_je_kg: float
    a13_dichte_kg_l: float
    a14_kg_je_palette: float
    vehicles: tuple[Vehicle, ...]
    bahn_elektrisch_g_tkm: float  # B3.5
    bahn_diesel_g_tkm: float  # B3.6
    i01_strassenfaktor: float
    i02_ort_streuung_km: float
    i03_erdradius_km: float
    meta: dict[str, ParamMeta]

    def kg_co2_je_km(self, vehicle: Vehicle) -> float:
        """C2: kg CO2e/km = A12 x A13 x Verbrauch (B2), Reihenfolge wie Assumptions!D59."""
        return self.a12_diesel_kg_co2_je_kg * self.a13_dichte_kg_l * vehicle.verbrauch_l_km

    @property
    def c01_bahn_faktor(self) -> float:
        """C01 (Assumptions!D49): aktiver Bahnfaktor nach Traktion A04."""
        if self.a04_traktion.lower() == "diesel":
            return self.bahn_diesel_g_tkm
        return self.bahn_elektrisch_g_tkm

    @property
    def c02_vnl_faktor(self) -> float | None:
        """C02 (Assumptions!D50): GLEC-Intensität des Vor-/Nachlauffahrzeugs A03."""
        for vehicle in self.vehicles:
            if vehicle.name.lower() == self.a03_vnl_fahrzeug.lower():
                return vehicle.g_tkm
        return None

    @property
    def c03_laufzeit_ok(self) -> int:
        """C03 (Assumptions!D51): 1, wenn A05 <= A06."""
        return 1 if self.a05_zusatz_tage <= self.a06_max_tage else 0

    @property
    def max_paletten(self) -> float:
        return max(v.paletten for v in self.vehicles)

    @property
    def max_kg(self) -> float:
        return max(v.nutzlast_kg for v in self.vehicles)
