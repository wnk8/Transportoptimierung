"""Wiederverwendbare Bausteine der Oberfläche: Kennzahlenkachel und Zustände."""

from __future__ import annotations

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
) -> None:
    """Kennzahlenkachel: Label, Wert Plan (28 px), darunter Ist und Delta mit Vorzeichen.

    Reduktion in Akzentfarbe, Zunahme in der Farbe der Vergleichsbasis. Das Delta steht
    immer als Text mit Vorzeichen, Farbe ist nie die einzige Information.
    """
    with ui.element("div").classes("tk-card flex flex-col gap-1 min-w-0"):
        ui.label(label).classes("tk-label")
        ui.label(fmt.with_unit(plan, unit, decimals) if unit != "%" else fmt.percent(plan, 1, False)).classes(
            "tk-kpi"
        )
        with ui.row().classes("items-baseline gap-2 flex-wrap"):
            if ist is not None:
                ist_text = fmt.with_unit(ist, unit, decimals) if unit != "%" else fmt.percent(ist, 1, False)
                ui.label(f"Ist: {ist_text}").classes("tk-label")
            if delta is not None:
                css = "tk-delta-down" if delta < 0 else "tk-delta-up" if delta > 0 else "tk-label"
                text = fmt.percent(delta) if not delta_is_level else fmt.percent(delta, 1, False)
                ui.label(text).classes(css + " tk-num").style("font-size:12px")
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
