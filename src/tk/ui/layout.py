"""Gemeinsame Teile beider Seiten: Kopfzeile mit Seitennavigation, Fußzeile, Szenario-Beschriftung."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from tk.ui import components
from tk.ui.state import Session
from tk.ui.theme import ScenarioToggle, apply_theme

SCENARIO_LABEL = {"Ist": "Ist (Einzelversand)", "M2": "M2 Bündelung", "M3": "M3 Bahn + Bündelung"}

FOOTER = (
    "© OpenStreetMap contributors (Kartendaten, ODbL) | Postleitzahl- und Ortsdaten: GeoNames, geonames.org, "
    "CC BY 4.0 | Rechenmodell: Excel v11, Python-Port"
)


def header(session: Session, active: str, on_scenario: Callable[[str], object]) -> ui.element:
    """App-Leiste: Marke, Seitennavigation, Szenario-Umschalter, Status. Gibt den Container des Status-Chips zurück."""
    with ui.element("header").classes("tk-appbar"):
        with ui.element("div").classes("tk-brand"):
            ui.label("TK").classes("tk-mark").props('aria-hidden="true"')
            with ui.column().classes("gap-0"):
                ui.label("Transportkonzept").classes("tk-title")
                ui.label("Nachhaltiges Transportkonzept, Excel v11").classes("tk-label")
        components.page_nav(active)
        with ui.element("div").classes("tk-appbar-end"):
            ScenarioToggle(session.scenario, on_scenario)
            status_box = ui.row().classes("items-center")
    return status_box


def footer(session: Session) -> None:
    ui.label(f"{FOOTER} | Datenstand: {session.base.source}").classes("tk-footer")


def missing_workbook() -> None:
    apply_theme()
    with ui.column().classes("tk-page"):
        ui.label("Transportkonzept").classes("tk-title")
        components.error_state(
            "Excel-Mappe nicht gefunden: data/excel/Thema1_Transportkonzept_v11_Beispieldaten.xlsx",
            "Mappe in den Ordner data/excel kopieren und die Seite neu laden (siehe README).",
        )
