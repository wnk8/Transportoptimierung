"""Gemeinsame Teile beider Seiten: feste Leiste, Szenario-Umschalter, Abschluss mit Attribution."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from tk.models import Result
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.state import Session
from tk.ui.theme import ScenarioToggle, apply_theme

SCENARIO_LABEL = {"Ist": "Ist (Einzelversand)", "M2": "M2 Bündelung", "M3": "M3 Bahn + Bündelung"}

FOOTER = (
    "© OpenStreetMap contributors (Kartendaten, ODbL) | Postleitzahl- und Ortsdaten: GeoNames, geonames.org, "
    "CC BY 4.0 | Rechenmodell: Excel v11, Python-Port"
)


def nav(active: str) -> ui.element:
    """Feste Leiste: Wortmarke, Seiten-Pillen, Platz für kompakte Kennzahlen, CTA zur jeweils anderen Seite.

    Gibt den Container der kompakten Kennzahlen zurück (befüllt mit ``nav_kpis``).
    """
    other, other_text = ("/analyse", "Analyse öffnen") if active == "/" else ("/", "Zur Eingabe")
    with ui.element("header").classes("tk-nav"):
        with ui.link(target="/").classes("tk-wordmark").props('aria-label="Transportkonzept, Startseite"'):
            ui.label("TK").classes("inline")
            ui.label(".").classes("inline tk-dot")
        components.page_nav(active)
        kpis = ui.element("div").classes("tk-nav-kpis").props('aria-label="Kennzahlen"')
        ui.button(other_text, on_click=lambda: ui.navigate.to(other)).props(
            "unelevated no-caps color=primary"
        ).classes("tk-cta tk-cta-link")
    return kpis


def nav_kpis(box: ui.element, result: Result | None, scenario: str) -> None:
    """Kompakte Kennzahlen in der festen Leiste: Bezeichnung, Wert, Delta gegen Ist."""
    box.clear()
    if result is None or result.n_valid == 0:
        return
    k = result.kpis[scenario]
    items = [
        ("CO₂e", fmt.with_unit(k.co2_fzgkm_kg, "kg"), k.delta_co2_fzgkm, "mint"),
        ("Kosten", fmt.with_unit(k.kosten_eur, "€"), k.delta_kosten, "sky"),
        ("Fzg-km", fmt.with_unit(k.lkw_km, "km"), k.delta_lkw_km, "peach"),
    ]
    with box:
        for label, value, delta, tone in items:
            with ui.element("div").classes(f"tk-nav-kpi tk-tone-{tone}"):
                ui.label(label).classes("tk-nav-kpi-label")
                ui.label(value).classes("tk-nav-kpi-value")
                if delta is not None and scenario != "Ist":
                    css = "down" if delta < 0 else "up" if delta > 0 else "flat"
                    ui.label(fmt.percent(delta)).classes(f"tk-delta-chip {css}")
        with ui.element("div").classes("tk-nav-kpi"):
            ui.label("Servicegrad").classes("tk-nav-kpi-label")
            ui.label(fmt.percent(k.servicegrad, 1, False)).classes("tk-nav-kpi-value")


def scenario_controls(session: Session, on_scenario: Callable[[str], object]) -> ui.element:
    """Szenario-Umschalter und Status. Gibt den Container des Status-Chips zurück."""
    with ui.element("div").classes("tk-hero-side"):
        ScenarioToggle(session.scenario, on_scenario)
        status_box = ui.row().classes("items-center")
    return status_box


def end(session: Session, href: str, text: str) -> ui.element:
    """Abschluss: optionale Zusammenfassung, großer Link zur nächsten Seite, Attribution."""
    with ui.element("footer").classes("tk-end"):
        summary = ui.element("div").classes("tk-label")
        ui.link(text, href).classes("tk-end-link")
        ui.label(f"{FOOTER} | Datenstand: {session.base.source}").classes("tk-footer")
    return summary


def missing_workbook() -> None:
    apply_theme()
    with ui.column().classes("tk-page"):
        ui.label("Transportkonzept").classes("tk-title")
        components.error_state(
            "Excel-Mappe nicht gefunden: data/excel/Thema1_Transportkonzept_v11_Beispieldaten.xlsx",
            "Mappe in den Ordner data/excel kopieren und die Seite neu laden (siehe README).",
        )
