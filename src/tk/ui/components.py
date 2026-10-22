"""Wiederverwendbare Bausteine der Oberfläche: Kennzahlenkachel und Zustände."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from nicegui import ui

from tk.ui import format as fmt


def kpi_tile(
    label: str,
    plan: float | None,
    ist: float | None,
    delta: float | None,
    unit: str,
    decimals: int = 0,
    on_explain: Callable[[], Any] | None = None,
    extra: str | None = None,
    delta_is_level: bool = False,
    delta_label: str = "gegen Ist",
    tone: str | None = None,
) -> None:
    """Kennzahlenkachel: Label, Wert Plan (28 px), darunter Delta als Chip und Ist-Wert.

    Reduktion in Akzentfarbe, Zunahme in der Farbe der Vergleichsbasis. Das Delta steht
    immer als Text mit Vorzeichen, Farbe ist nie die einzige Information.
    """
    surface = f"tk-kpi-tile tk-tone-{tone}" if tone else "tk-card"
    with ui.element("div").classes(f"{surface} flex flex-col gap-1 min-w-0"):
        ui.label(label).classes("tk-kpi-label" if tone else "tk-label")
        ui.label(fmt.with_unit(plan, unit, decimals) if unit != "%" else fmt.percent(plan, 1, False)).classes(
            "tk-kpi"
        )
        with ui.row().classes("items-center gap-2 flex-wrap"):
            if delta is not None:
                css = "down" if delta < 0 else "up" if delta > 0 else "flat"
                text = fmt.percent(delta) if not delta_is_level else fmt.percent(delta, 1, False)
                ui.label(f"{text} {delta_label}").classes(f"tk-delta-chip {css}")
            if ist is not None:
                ist_text = fmt.with_unit(ist, unit, decimals) if unit != "%" else fmt.percent(ist, 1, False)
                ui.label(f"Ist: {ist_text}").classes("tk-label")
        if extra:
            ui.label(extra).classes("tk-label")
        if on_explain:
            ui.button("Wie berechnet?", on_click=on_explain).props("flat dense no-caps").classes(
                "tk-link self-start"
            )


def empty_state(
    text: str, action_label: str | None = None, on_action: Callable[[], Any] | None = None
) -> None:
    """Leerer Zustand: eine klare Aktion."""
    with ui.element("div").classes("tk-card flex flex-col items-start gap-2"):
        ui.label(text)
        if action_label and on_action:
            ui.button(action_label, on_click=on_action).props("unelevated no-caps color=primary")


def loading_state(text: str) -> None:
    """Lädt: dezenter Fortschritt ohne Spinner."""
    with ui.element("div").classes("tk-card flex flex-col gap-2"):
        ui.label(text).classes("tk-label")
        with ui.element("div").classes("tk-progress"):
            ui.element("div")


def error_state(cause: str, next_step: str) -> None:
    """Fehler: Ursache und nächster Schritt."""
    with ui.element("div").classes("tk-error flex flex-col").props('role="alert"'):
        ui.label(cause).style("font-weight:600")
        ui.label(next_step)


def success_state(text: str) -> None:
    """Erfolg: knappe Bestätigung."""
    ui.label(text).classes("tk-success").props('role="status"')


def note(text: str) -> None:
    """Hinweis zu Annahmen."""
    ui.label(text).classes("tk-note")


def step_header(n: int, title: str, tone: str = "mint") -> ui.label:
    """Schrittkopf mit Nummer im Pastellton und Titel; gibt das Statuslabel rechts zurück."""
    with ui.element("div").classes(f"tk-step tk-tone-{tone} w-full"):
        ui.label(str(n)).classes("tk-step-num").props('aria-hidden="true"')
        ui.label(title).classes("tk-step-title")
        return ui.label("").classes("tk-step-status")


def page_nav(active: str) -> None:
    """Seitennavigation Eingabe und Analyse; aktive Seite mit aria-current, Strich und Gewicht."""
    with ui.element("nav").classes("tk-pagenav").props('aria-label="Seiten"'):
        for href, text in (("/", "Eingabe"), ("/analyse", "Analyse")):
            link = ui.link(text, href)
            if href == active:
                link.props('aria-current="page"')


def number_field(
    label: str,
    unit: str,
    help_text: str,
    tooltip: str | None = None,
    value: float | None = None,
    step: float = 1.0,
    minimum: float | None = None,
    maximum: float | None = None,
    on_change: Callable[..., Any] | None = None,
    field_id: str | None = None,
) -> tuple[ui.element, ui.number, ui.label]:
    """Zahlenfeld: Beschriftung oben, Einheit im Feld, Hilfetext darunter.

    Gibt Container, Feld und Hilfelabel zurück, damit der Aufrufer Zustand und Text setzen kann.
    """
    with ui.element("div").classes("tk-field") as box:
        with ui.row().classes("tk-field-label gap-0 no-wrap items-baseline"):
            if field_id:
                ui.label(field_id).classes("tk-id")
            ui.label(label)
            if tooltip:
                ui.tooltip(tooltip).style("max-width:360px;font-size:12px;white-space:pre-line")
        num = ui.number(
            value=value,
            step=step,
            min=minimum,
            max=maximum,
            format="%.6g",
            on_change=on_change,
            validation={bounds_text(minimum, maximum, unit): lambda v: in_bounds(v, minimum, maximum)},
        ).props(f'dense outlined hide-bottom-space suffix="{html.escape(unit)}" aria-label="{html.escape(label)}"')
        num.classes("w-full")
        hint = ui.label(help_text).classes("tk-help")
    return box, num, hint


def in_bounds(value: float | None, minimum: float | None, maximum: float | None) -> bool:
    """Leeres Feld gilt als gültig; sonst innerhalb der Grenzen."""
    if value is None:
        return True
    return (minimum is None or value >= minimum) and (maximum is None or value <= maximum)


def bounds_text(minimum: float | None, maximum: float | None, unit: str) -> str:
    """Fehlertext zur Feldgrenze, mit Ursache und erlaubtem Bereich."""

    def show(v: float) -> str:
        return fmt.with_unit(v, unit, 0 if float(v).is_integer() else 2)

    if minimum is not None and maximum is not None:
        return f"Wert zwischen {show(minimum)} und {show(maximum)} eingeben"
    if minimum is not None:
        return f"Wert ab {show(minimum)} eingeben"
    if maximum is not None:
        return f"Wert bis {show(maximum)} eingeben"
    return "Zahl eingeben"
