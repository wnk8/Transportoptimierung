"""Erklärung je Kennzahl: Formel, Parameter, Quelle, Systemgrenze, Verifikationsstatus.

Grundlage ist das Formelregister K2 im Blatt Assumptions. Der Verifikationsstatus nennt,
ob der Wert gegen die gespeicherten Werte der Excel v11 geprüft ist (``expected.json``)
und wie belegt die verwendeten Faktoren sind (Spalte Typ in Assumptions).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from tk.models import Assumptions, Result

KpiKey = Literal["co2_fzgkm", "co2_tkm", "kosten", "lkw_km", "servicegrad", "bahn"]


class ParamUse(BaseModel):
    id: str
    name: str
    wert: Any
    einheit: str
    typ: str
    quelle: str


class Explanation(BaseModel):
    kennzahl: str
    einheit: str
    formel: str  # LaTeX
    beschreibung: str
    formelregister: str
    parameter: list[ParamUse]
    datenquelle: str
    systemgrenze: str
    werte: dict[str, float | int | None]
    verifikation: str


SPEC: dict[str, dict[str, Any]] = {
    "co2_fzgkm": {
        "titel": "CO₂e Hauptrechnung (Fahrzeug-km)",
        "einheit": "kg CO₂e",
        "attr": "co2_fzgkm_kg",
        "formel": r"E = km \cdot e_r \cdot \left(\alpha + (1-\alpha)\,\frac{kg/(n\,kg_r)}{u_{\mathrm{ref},r}}\right),"
        r"\quad e_r = A_{12}\cdot A_{13}\cdot l_r",
        "text": "Fahrzeug-km je Sendung oder Tour mal Emissionsfaktor je km der Fahrzeugklasse. "
        "Bahn-Sendungen: Vor-/Nachlauf mit C02, Hauptlauf mit C01.",
        "register": "K2.8, K2.12, K2.14, K2.16",
        "params": ["a11_alpha", "a12_diesel_kg_co2_je_kg", "a13_dichte_kg_l", "a02_vnl_km", "a10_umweg"],
        "vectors": ["verbrauch_l_km"],
        "grenze": "Well-to-Wheel, Hauptlauf; Vor-/Nachlauf der Bahn pauschal A02.",
    },
    "co2_tkm": {
        "titel": "CO₂e Kontrollrechnung (tkm, GLEC)",
        "einheit": "kg CO₂e",
        "attr": "co2_tkm_kg",
        "formel": r"E_{tkm} = tkm \cdot g_r / 1000",
        "text": "Transportleistung mal GLEC-Intensität der Fahrzeugklasse. Dient der Plausibilität.",
        "register": "K2.9",
        "params": [],
        "vectors": ["g_tkm"],
        "grenze": "Well-to-Wheel, Hauptlauf (GLEC Framework v3.2).",
    },
    "kosten": {
        "titel": "Kosten",
        "einheit": "EUR",
        "attr": "kosten_eur",
        "formel": r"K = \text{Fracht, sonst } km \cdot k_r \cdot C_{04},\quad "
        r"C_{04} = \frac{\sum Fr_i}{\sum K_i^{\mathrm{Modell}}}",
        "text": "Eingegebene Fracht, sonst Modellkosten mal Kalibrierfaktor. Bahn: Einzelkosten mal (1 + A07).",
        "register": "K2.10",
        "params": ["a07_bahn_aufschlag", "a08_kosten_tol"],
        "vectors": ["kostensatz_eur_km"],
        "grenze": "Frachtkosten der Sendung, keine Umschlag- oder Lagerkosten.",
    },
    "lkw_km": {
        "titel": "Lkw-Kilometer",
        "einheit": "km",
        "attr": "lkw_km",
        "formel": r"km = d \cdot n;\quad km_T = d_{\max}\,(1 + A_{10}\,(\mathrm{Stopps}-1))",
        "text": "Einzelfahrt: Distanz mal Fahrzeuganzahl. Tour: längste Distanz mit Umwegzuschlag je Stopp.",
        "register": "K2.2, K2.7, K2.14",
        "params": ["i01_strassenfaktor", "a10_umweg"],
        "vectors": [],
        "grenze": "Luftlinie mal Straßenfaktor I01, keine Routenoptimierung.",
    },
    "servicegrad": {
        "titel": "Servicegrad",
        "einheit": "Anteil",
        "attr": "servicegrad",
        "formel": r"S = 1 - \frac{N_{\mathrm{Bahn}}}{N}\quad(\text{nur wenn } A_{05} > 0)",
        "text": "Jede Bahn-Sendung gilt als verspätet, solange die Bahn eine Zusatzlaufzeit hat.",
        "register": "K2.17",
        "params": ["a05_zusatz_tage", "a06_max_tage"],
        "vectors": [],
        "grenze": "Laufzeit pauschal; keine Fahrplandaten.",
    },
    "bahn": {
        "titel": "Bahn-Sendungen",
        "einheit": "Stück",
        "attr": "bahn_sendungen",
        "formel": r"\mathrm{Bahn} \Leftrightarrow d > A_{01} \wedge A_{05} \le A_{06} \wedge K(1+A_{07}) \le K(1+A_{08})",
        "text": "Verlagerung bei ausreichender Distanz, zulässiger Laufzeit und Einhaltung der Kostenregel.",
        "register": "K2.11",
        "params": [
            "a01_bahn_grenze_km",
            "a05_zusatz_tage",
            "a06_max_tage",
            "a07_bahn_aufschlag",
            "a08_kosten_tol",
        ],
        "vectors": [],
        "grenze": "Prüfung je Sendung, keine Terminal- oder Kapazitätsdaten.",
    },
}

DATA_SOURCE = (
    "Sendungen: Eingabe im Schema Input!A:H. Orte: PLZ_Orte (GeoNames, CC BY 4.0). "
    "Parameter: Blatt Assumptions der Excel v11."
)


def _param_use(params: Assumptions, field: str) -> ParamUse:
    meta = params.meta[field]
    return ParamUse(
        id=meta.id,
        name=meta.name,
        wert=getattr(params, field),
        einheit=meta.unit,
        typ=meta.typ,
        quelle=meta.quelle,
    )


def explain(
    key: KpiKey, params: Assumptions, result: Result, reference: dict[str, Any] | None = None
) -> Explanation:
    """Erklärung einer Kennzahl für Ist, M2 und M3 mit Verifikationsstatus."""
    spec = SPEC[key]
    uses = [_param_use(params, f) for f in spec["params"]]
    for field in spec["vectors"]:
        for i, vehicle in enumerate(params.vehicles):
            meta = params.meta[f"{field}[{i}]"]
            uses.append(
                ParamUse(
                    id=meta.id,
                    name=vehicle.name,
                    wert=getattr(vehicle, field),
                    einheit=meta.unit,
                    typ=meta.typ,
                    quelle=meta.quelle,
                )
            )
    if key in ("co2_fzgkm", "bahn"):
        uses.append(
            ParamUse(
                id="C01",
                name=f"Bahnfaktor aktiv ({params.a04_traktion})",
                wert=params.c01_bahn_faktor,
                einheit="g CO₂e/tkm",
                typ="Abgeleitet (Formel)",
                quelle=params.meta["bahn_elektrisch_g_tkm"].quelle,
            )
        )
    if key == "kosten":
        uses.append(
            ParamUse(
                id="C04",
                name="Kalibrierungsfaktor",
                wert=result.c04,
                einheit="Faktor",
                typ="Abgeleitet (Formel)",
                quelle="Input H und AK",
            )
        )
    werte = {name: getattr(k, spec["attr"]) for name, k in result.kpis.items()}
    return Explanation(
        kennzahl=spec["titel"],
        einheit=spec["einheit"],
        formel=spec["formel"],
        beschreibung=spec["text"],
        formelregister=spec["register"],
        parameter=uses,
        datenquelle=DATA_SOURCE,
        systemgrenze=spec["grenze"],
        werte=werte,
        verifikation=verification(key, result, reference, uses),
    )


def verification(key: KpiKey, result: Result, reference: dict[str, Any] | None, uses: list[ParamUse]) -> str:
    """Verifikationsstatus: Abgleich mit Excel (falls Referenz passt) und Belegstand der Faktoren."""
    parts = []
    attr = SPEC[key]["attr"]
    if reference and reference.get("anzahl_sendungen") == result.n_valid:
        worst = 0.0
        for name, kpi in result.kpis.items():
            want = reference["kennzahlen"][name][attr]
            got = getattr(kpi, attr)
            if want:
                worst = max(worst, abs(got / want - 1))
        parts.append(f"Gegen Excel v11 geprüft, größte relative Abweichung {worst:.1e}.")
    else:
        parts.append("Kein Excel-Referenzwert für diese Eingabe; Rechenweg identisch zur Excel v11.")
    open_items = sorted({u.id for u in uses if "Annahme" in u.typ or "fehlt" in u.quelle})
    if open_items:
        parts.append("Annahmen ohne Primärbeleg: " + ", ".join(open_items) + ".")
    secondary = sorted({u.id for u in uses if "Sekundärquelle" in u.typ})
    if secondary:
        parts.append("Sekundärquelle, Primärverifikation ausstehend: " + ", ".join(secondary) + ".")
    return " ".join(parts)
