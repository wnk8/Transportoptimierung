"""Gemeinsame Teile aller Seiten: Marke, Kopfzeile, Schrittleiste, Headline, Footer mit Attribution."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from tk.ui import components
from tk.ui import format as fmt
from tk.ui.state import Session
from tk.ui.theme import ScenarioToggle, apply_theme

BRAND = "TourKlima"
"""Markenname neben der Wortmarke TK.: Touren bündeln, Klimawirkung senken."""

CLAIM = "Die Transportoptimierung für weniger CO₂e."

SCENARIO_LABEL = {"Ist": "Ist (Einzelversand)", "M2": "M2 Bündelung", "M3": "M3 Bahn + Bündelung"}

ATTRIBUTION = (
    "© OpenStreetMap contributors (Kartendaten, ODbL)",
    "Postleitzahl- und Ortsdaten: GeoNames, geonames.org, CC BY 4.0",
    "Rechenmodell: Excel v11, Python-Port",
)

PAGES = (("/", "Produkt"), ("/rechnen", "Rechnen"), ("/ergebnis", "Ergebnis"), ("/info", "Info"))
"""Seiten in der Navigation: Pfad und Beschriftung."""


def nav(active: str) -> None:
    """Kopfzeile: Wortmarke und Marke links, Seitenlinks mittig, Hauptaktion rechts; aktive Seite per aria-current."""
    with ui.element("header").classes("tk-nav"):
        with ui.link(target="/").classes("tk-brand").props(f'aria-label="TK. {BRAND}, Startseite"'):
            with ui.element("span").classes("tk-wordmark"):
                ui.label("TK").classes("inline")
                ui.label(".").classes("inline tk-dot")
            ui.label(BRAND).classes("tk-brand-name")
        with ui.element("nav").classes("tk-pagenav").props('aria-label="Seiten"'):
            for href, text in PAGES:
                link = ui.link(text, href)
                if href == active:
                    link.props('aria-current="page"')
        with ui.element("div").classes("tk-nav-cta"):
            if active == "/rechnen":
                ui.button("Zum Ergebnis", on_click=lambda: ui.navigate.to("/ergebnis?tab=karte")).props(
                    "outline no-caps color=primary"
                ).classes("tk-cta")
            else:
                ui.button("Jetzt optimieren", on_click=lambda: ui.navigate.to("/rechnen")).props(
                    "unelevated no-caps color=primary"
                ).classes("tk-cta")


def steps(active: int, session: Session) -> None:
    """Schrittleiste der App: Sendungen, Parameter, Ergebnis. Status als Text, nie nur über Farbe."""
    r = session.result
    n_valid = r.n_valid if r is not None else 0
    n_changed = len(session.changes)
    items = (
        (1, "Sendungen", "/rechnen#schritt-1", f"{fmt.number(n_valid)} gültig" if n_valid else "keine",
         n_valid > 0),
        (2, "Parameter", "/rechnen#schritt-2",
         "Standard" if n_changed == 0 else f"{n_changed} geändert", n_valid > 0),
        (3, "Ergebnis", "/ergebnis?tab=karte", r.status if r is not None and n_valid else "offen", False),
    )  # fmt: skip
    with ui.element("nav").classes("tk-steps").props('aria-label="Ablauf"'):
        for i, (no, label, href, meta, done) in enumerate(items):
            if i:
                ui.element("span").classes("tk-step-sep").props('aria-hidden="true"')
            link = ui.link(target=href).classes("tk-step" + (" is-done" if done and no != active else ""))
            if no == active:
                link.props('aria-current="step"')
            with link:
                ui.label("✓" if done and no != active else str(no)).classes("tk-step-no")
                ui.label(label)
                ui.label(meta).classes("tk-step-meta")


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
    """Footer: Marke, Produkt, Methodik, Daten mit Attribution und Datenstand."""
    with ui.element("footer").classes("tk-foot"):
        with ui.element("div").classes("tk-foot-col"):
            with ui.element("span").classes("tk-wordmark").style("color:var(--text);font-size:20px"):
                ui.label("TK").classes("inline")
                ui.label(".").classes("inline tk-dot")
                ui.label(f" {BRAND}").classes("inline")
            ui.label(CLAIM).classes("tk-foot-claim")
        with ui.element("div").classes("tk-foot-col"):
            ui.label("Produkt").classes("tk-foot-head")
            for href, text in PAGES:
                ui.link(text, href)
        with ui.element("div").classes("tk-foot-col"):
            ui.label("Methodik").classes("tk-foot-head")
            ui.link("Formeln und Erklärung", "/info?tab=erklaerung")
            ui.link("Annahmen und Quellen", "/info?tab=annahmen")
            ui.link("Prüfungen gegen Excel v11", "/info?tab=pruefungen")
            ui.label("GLEC Framework, ISO 14083, DIN EN 16258").classes("tk-foot-item")
        with ui.element("div").classes("tk-foot-col"):
            ui.label("Daten").classes("tk-foot-head")
            for line in ATTRIBUTION:
                ui.label(line).classes("tk-foot-item")
        ui.label(f"Datenstand: {session.base.source} | Seminar BLO513/WPML733").classes("tk-foot-base")


def missing_workbook() -> None:
    apply_theme()
    with ui.column().classes("tk-page"):
        ui.label(f"TK. {BRAND}").classes("tk-title")
        components.error_state(
            "Excel-Mappe nicht gefunden: data/excel/Thema1_Transportkonzept_v11_Beispieldaten.xlsx",
            "Mappe in den Ordner data/excel kopieren und die Seite neu laden (siehe README).",
        )
