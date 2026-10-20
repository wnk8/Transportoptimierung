"""Lädt alle Parameter aus dem Blatt Assumptions der Excel v11.

Die Zellen werden über die benannten Bereiche der Mappe gefunden (``p_*``, ``v_*``), nicht
über feste Zeilennummern. Einheit, Typ und Quelle stehen in derselben Zeile (Spalten E, F
und H, bei Abschnitt I Spalte G). Es gibt keine Standardwerte im Code.
"""

from __future__ import annotations

from typing import Any

from openpyxl.utils import get_column_letter

from tk.models import Assumptions, ParamMeta, Vehicle
from tk.workbook import WorkbookData

SCALARS: dict[str, str] = {
    "a01_bahn_grenze_km": "p_BahnGrenze",
    "a02_vnl_km": "p_VNL_km",
    "a03_vnl_fahrzeug": "p_VNL_Fzg",
    "a04_traktion": "p_Traktion",
    "a05_zusatz_tage": "p_ZusatzTage",
    "a06_max_tage": "p_MaxTage",
    "a07_bahn_aufschlag": "p_BahnAufschlag",
    "a08_kosten_tol": "p_KostenTol",
    "a09_schwelle": "p_Schwelle",
    "a10_umweg": "p_Umweg",
    "a11_alpha": "p_Alpha",
    "a12_diesel_kg_co2_je_kg": "p_Diesel",
    "a13_dichte_kg_l": "p_Dichte",
    "a14_kg_je_palette": "p_KgPal",
    "bahn_elektrisch_g_tkm": "p_Bahn_elektrisch",
    "bahn_diesel_g_tkm": "p_Bahn_Diesel",
    "i01_strassenfaktor": "p_Strassenfaktor",
    "i02_ort_streuung_km": "p_OrtStreuung",
    "i03_erdradius_km": "p_Erdradius",
}
"""Feld des Modells zu benanntem Bereich der Excel."""

VECTORS: dict[str, str] = {
    "name": "v_Name",
    "paletten": "v_Pal",
    "nutzlast_kg": "v_Kg",
    "verbrauch_l_km": "v_Verbrauch",
    "g_tkm": "v_gTkm",
    "kostensatz_eur_km": "v_Kostensatz",
    "referenz_auslastung": "v_LFref",
}

SHEET = "Assumptions"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _meta(data: WorkbookData, name: str, index: int = 0) -> ParamMeta:
    sheet, row, col = data.name_cells(name)[index]
    grid = data.sheets[sheet]
    pid = _text(grid.get((row, 2)))
    label = _text(grid.get((row, 3)))
    unit = _text(grid.get((row, 5)))
    typ = _text(grid.get((row, 6)))
    quelle = _text(grid.get((row, 8))) or _text(grid.get((row, 7)))
    ref = f"{sheet}!{get_column_letter(col)}{row}"
    return ParamMeta(id=pid, name=label, unit=unit, typ=typ, quelle=quelle, zelle=ref)


def load_assumptions(data: WorkbookData) -> Assumptions:
    """Alle Parameter mit Einheit und Quelle aus dem Blatt Assumptions."""
    values: dict[str, Any] = {field: data.name_value(name) for field, name in SCALARS.items()}
    meta = {f: _meta(data, n) for f, n in SCALARS.items()}
    columns = {field: data.name_values(name) for field, name in VECTORS.items()}
    count = len(columns["name"])
    vehicles = tuple(Vehicle(**{field: columns[field][i] for field in VECTORS}) for i in range(count))
    for i in range(count):
        for field, name in VECTORS.items():
            meta[f"{field}[{i}]"] = _meta(data, name, i)
    return Assumptions(**values, vehicles=vehicles, meta=meta)


def describe(assumptions: Assumptions) -> list[dict[str, Any]]:
    """Parameterliste für Anzeige und Dokumentation (ID, Name, Wert, Einheit, Typ, Quelle, Zelle)."""
    out = []
    for field in SCALARS:
        m = assumptions.meta[field]
        out.append(
            {
                "feld": field,
                "id": m.id,
                "name": m.name,
                "wert": getattr(assumptions, field),
                "einheit": m.unit,
                "typ": m.typ,
                "quelle": m.quelle,
                "zelle": m.zelle,
            }
        )
    return out
