"""Freitext-Eingabe über den Agenten und Agent-Spur."""

from __future__ import annotations

import html
import json
import os
from typing import TYPE_CHECKING, Any

from nicegui import run, ui

from tk.agent.demo import CASES, demo_provider
from tk.agent.orchestrator import AgentAnswer, Orchestrator
from tk.agent.provider import GeminiProvider, LLMProvider, ProviderUnavailable
from tk.agent.tools import AgentContext
from tk.agent.trace import Trace
from tk.ui import components

if TYPE_CHECKING:
    from tk.ui.app import Page
    from tk.ui.state import Session


def _provider(request: str) -> tuple[LLMProvider, str]:
    if os.environ.get("TK_DEMO_MODE") == "1":
        return demo_provider(request), "Demo-Modus (aufgezeichnet)"
    try:
        return GeminiProvider(), "Gemini"
    except ProviderUnavailable:
        return demo_provider(request), "Demo-Modus (kein GEMINI_API_KEY)"


def build_agent_input(page: Page, box: ui.column) -> None:
    if page.s.agent_trace is None:
        page.s.agent_trace = Trace()
    page.agent_ctx = AgentContext(model=page.s.model)  # type: ignore[attr-defined]
    with box:
        ui.label(
            "Sendungen in Worten beschreiben. Der Agent übernimmt nur genannte Werte, rechnet nie selbst "
            "und nennt nur Zahlen aus dem Rechenkern."
        ).classes("tk-label")
        _, mode = _provider("")
        mode_label = ui.label(f"Modus: {mode}").classes("tk-label")
        text = ui.textarea("Anfrage").props("outlined dense rows=3").classes("w-full")
        with ui.row().classes("gap-1 flex-wrap"):
            for case in CASES.values():
                ui.button(
                    str(case["titel"]), on_click=lambda c=case: text.set_value(str(c["anfrage"]))
                ).props("flat dense no-caps color=primary")
        answer_box = ui.column().classes("w-full gap-2")

        async def send() -> None:
            request = (text.value or "").strip()
            if not request:
                return
            provider, mode = _provider(request)
            mode_label.set_text(f"Modus: {mode}")
            ctx = AgentContext(model=page.s.model, bestand=list(page.s.shipments))
            orch = Orchestrator(provider, ctx, fallback=demo_provider)
            answer_box.clear()
            with answer_box:
                components.loading_state("Agent arbeitet")
            try:
                result = await run.io_bound(orch.run, request)
            except ProviderUnavailable as exc:
                answer_box.clear()
                with answer_box:
                    components.error_state(
                        f"Agent nicht erreichbar: {exc}", "Demo-Fall wählen oder Eingabe über das Formular."
                    )
                return
            if result is None:
                return
            answer: AgentAnswer = result
            used = (
                "Gemini"
                if answer.provider == "gemini"
                else "Demo-Modus (Gemini nicht verfügbar, aufgezeichneter Ablauf)"
            )
            mode_label.set_text(f"Modus: {used}")
            page.s.agent_trace = answer.trace
            page.agent_ctx = ctx  # type: ignore[attr-defined]
            answer_box.clear()
            with answer_box:
                if answer.accepted:
                    # Model text as Markdown; HTML in the model output is escaped first.
                    ui.markdown(html.escape(answer.text, quote=False)).classes("tk-card w-full")
                else:
                    components.error_state(answer.text, "Spur prüfen; Zahlen stehen in den Werkzeugausgaben.")
                if ctx.arbeitsliste:
                    ui.button(
                        f"{len(ctx.arbeitsliste)} Sendung(en) in die Eingabe übernehmen",
                        on_click=lambda: page.set_shipments(ctx.arbeitsliste, replace=False, origin="Agent"),
                    ).props("unelevated no-caps color=primary")
                ui.link("Werkzeugaufrufe ansehen (Info, Agent-Spur)", "/info?tab=agent").classes("tk-link")

        ui.button("Senden", on_click=send).props("unelevated no-caps color=primary")


def _short(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str, indent=1)
    return text if len(text) < 4000 else text[:4000] + "\n(gekürzt)"


def render_trace(session: Session, box: ui.column) -> None:
    box.clear()
    trace = session.agent_trace
    with box:
        if trace is None or not trace.entries:
            components.empty_state(
                "Noch keine Agent-Anfrage. Seite Rechnen, Abschnitt Sendungen, Tab Freitext."
            )
            return
        ui.label("Chronologische Werkzeugaufrufe mit Ein- und Ausgabe.").classes("tk-label")
        for e in trace.entries:
            title = f"{e.zeit}  {e.art}: {e.name}" + (f" ({e.dauer_ms:.0f} ms)" if e.dauer_ms else "")
            with ui.expansion(title).props("dense").classes("w-full"):
                if e.eingabe not in ("", None, {}):
                    ui.label("Eingabe").classes("tk-label")
                    ui.code(_short(e.eingabe), language="json").classes("w-full")
                if e.ausgabe not in ("", None, {}):
                    ui.label("Ausgabe").classes("tk-label")
                    ui.code(_short(e.ausgabe), language="json").classes("w-full")
