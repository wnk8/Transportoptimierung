"""Gemeinsame Teile der drei Seiten Rechnen, Ergebnis, Info: Navigation, Headline, Attribution."""

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

PAGES = (("/", "Rechnen"), ("/ergebnis", "Ergebnis"), ("/info", "Info"))
"""Seiten in der Navigation: Pfad und Beschriftung."""


def nav(active: str) -> None:
    """Kopfzeile: Wortmarke links, drei Textlinks rechts; die aktive Seite ist unterstrichen und per aria-current markiert."""
    with ui.element("header").classes("tk-nav"):
        with ui.link(target="/").classes("tk-wordmark").props('aria-label="Transportkonzept, Rechnen"'):
            ui.label("TK").classes("inline")
            ui.label(".").classes("inline tk-dot")
        with ui.element("nav").classes("tk-pagenav").props('aria-label="Seiten"'):
            for href, text in PAGES:
                link = ui.link(text, href)
                if href == active:
                    link.props('aria-current="page"')


def hero(kicker: str, serif: str = "") -> tuple[ui.label, ui.label, ui.label, ui.label, ui.element]:
    """Headline: Kicker, Titel mit kursivem Serif-Wort, Nachsatz und Punkt, Einleitung, rechte Spalte.

    Gibt Titel, Serif-Wort, Nachsatz, Einleitung und die rechte Spalte zurück. Das Serif-Wort ohne
    Sonderzeichen wählen: Instrument Serif enthält etwa kein tiefgestelltes ₂.
    """
    with ui.element("div").classes("tk-hero tk-reveal"):
        with ui.element("div"):
            ui.label(kicker).classes("tk-kicker tk-hero-kicker")
            with ui.element("h1").classes("tk-hero-title"):
                title = ui.label("").classes("inline")
                serif_label = ui.label(serif).classes("inline tk-serif")
                tail = ui.label("").classes("inline")
                ui.label(".").classes("inline tk-dot")
            sub = ui.label("").classes("tk-hero-sub")
        side = ui.element("div").classes("tk-hero-side")
    serif_label.set_visibility(bool(serif))
    return title, serif_label, tail, sub, side


def scenario_controls(session: Session, on_scenario: Callable[[str], object]) -> ui.element:
    """Szenario-Umschalter und Status. Gibt den Container des Status-Chips zurück."""
    ScenarioToggle(session.scenario, on_scenario)
    return ui.row().classes("items-center")


def end(session: Session) -> None:
    """Attribution und Datenstand am Seitenende."""
    with ui.element("footer").classes("tk-end"):
        ui.label(f"{FOOTER} | Datenstand: {session.base.source}").classes("tk-footer")


def missing_workbook() -> None:
    apply_theme()
    with ui.column().classes("tk-page"):
        ui.label("Transportkonzept").classes("tk-title")
        components.error_state(
            "Excel-Mappe nicht gefunden: data/excel/Thema1_Transportkonzept_v11_Beispieldaten.xlsx",
            "Mappe in den Ordner data/excel kopieren und die Seite neu laden (siehe README).",
        )
