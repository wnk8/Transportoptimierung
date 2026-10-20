"""Emissionsrechnung: Fahrzeugkilometer (Hauptrechnung), tkm (Kontrolle), Bahn.

Systemgrenze aller Faktoren: Well-to-Wheel (WTW), Hauptlauf. Die Formeln sind die
Zellformeln Input AI, AJ, AO und Touren AF, AG in derselben Rechenreihenfolge.
"""

from __future__ import annotations

from tk.models import Assumptions, Vehicle


def load_factor(gewicht_kg: float, n: int, vehicle: Vehicle, params: Assumptions) -> float:
    r"""Lastfaktor :math:`\alpha + (1-\alpha)\,\frac{kg/(n\,kg_r)}{u_{\text{ref},r}}` (Register K2.8).

    Annahme: A11 = 1 setzt den Verbrauch lastunabhängig (kein belegter Wert, E09).
    """
    a = params.a11_alpha
    return a + (1 - a) * (gewicht_kg / n / vehicle.nutzlast_kg) / vehicle.referenz_auslastung


def co2_fzgkm(lkw_km: float, gewicht_kg: float, n: int, vehicle: Vehicle, params: Assumptions) -> float:
    r"""Hauptrechnung Einzelfahrt (Register K2.8, Input AI).

    .. math:: E = km \cdot e_r \cdot \left(\alpha + (1-\alpha)\frac{kg/(n\,kg_r)}{u_{\text{ref},r}}\right),
              \quad e_r = A_{12}\cdot A_{13}\cdot l_r

    Einheit kg CO2e. Quelle: Verbrauch B2 und Dieselfaktor A12 sind Annahmen der Gruppe
    (Projektpunkt P4, Primärbeleg offen). Systemgrenze WTW.
    """
    return lkw_km * params.kg_co2_je_km(vehicle) * load_factor(gewicht_kg, n, vehicle, params)


def co2_tour_fzgkm(lkw_km: float, gewicht_kg: float, vehicle: Vehicle, params: Assumptions) -> float:
    r"""Hauptrechnung Tour (Touren AF): :math:`E_T = km_T \cdot e_r \cdot \lambda_T` mit Tourgewicht."""
    a = params.a11_alpha
    lf = a + (1 - a) * (gewicht_kg / vehicle.nutzlast_kg) / vehicle.referenz_auslastung
    return lkw_km * params.kg_co2_je_km(vehicle) * lf


def co2_tkm(tkm: float, vehicle: Vehicle) -> float:
    r"""Kontrollrechnung (Register K2.9, Input AJ, Touren AG): :math:`E_{tkm} = tkm \cdot g_r / 1000`.

    Quelle: GLEC Framework v3.2, Intensitäten je Fahrzeugklasse (Assumptions B3),
    Sekundärquelle, Primärverifikation ausstehend. Dient der Plausibilität, nicht dem Ergebnis.
    """
    return tkm * vehicle.g_tkm / 1000


def co2_rail(gewicht_kg: float, distanz_km: float, params: Assumptions) -> float:
    r"""Bahn-CO2e je Sendung (Register K2.12, Input AO).

    .. math:: E_B = \frac{\frac{kg}{1000}\min(d, A_{02})\,C_{02}
              + \frac{kg}{1000}\,(d - \min(d, A_{02}))\,C_{01}}{1000}

    Vor- und Nachlauf mit dem Lkw-Faktor des Fahrzeugs A03 (C02), Hauptlauf mit dem
    aktiven Bahnfaktor C01 (Traktion A04). Quelle: GLEC v3.2 (B3.5, B3.6), WTW.
    """
    vnl = min(distanz_km, params.a02_vnl_km)
    c02 = params.c02_vnl_faktor
    if c02 is None:
        raise ValueError("A03 ist nicht in der Fahrzeugtabelle (Prüfung 16)")
    return (
        gewicht_kg / 1000 * vnl * c02 + gewicht_kg / 1000 * (distanz_km - vnl) * params.c01_bahn_faktor
    ) / 1000
