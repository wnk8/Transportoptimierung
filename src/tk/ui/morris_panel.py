"""Info, Tab Sensitivität: globales Morris-Screening als Tornado-Diagramm und Tabelle.

Gespeichertes Ergebnis für die Beispieldaten (``scripts/make_sensitivity.py``); mit geänderten
Parametern oder Sendungen rechnet "Neu rechnen" für den aktuellen Stand. Zahlen aus ``tk.sensitivity``.
"""

from __future__ import annotations

from typing import Any

from nicegui import run, ui

from tk.sensitivity import TARGETS, Screening, load, load_bounds, morris
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.state import Session
from tk.ui.theme import TOKENS

FONT = "Geist, Inter, system-ui, sans-serif"


def tornado_chart(screening: Screening, target: str) -> dict[str, Any]:
    """Balken :math:`\\mu^*` (Wirkung) und :math:`\\sigma` (Wechselwirkung) je Parameter, größte oben."""
    rows = screening.effekte[target]
    labels = [f"{e.kennung} {e.name}" for e in rows]
    return {
        "animation": False,
        "textStyle": {"fontFamily": FONT, "color": TOKENS["text"]},
        "legend": {"top": 0, "right": 0, "textStyle": {"color": TOKENS["muted"]}},
        "grid": {"left": 260, "right": 24, "top": 32, "bottom": 28},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            ":valueFormatter": "v => v.toLocaleString('de-DE', {maximumFractionDigits: 4})",
        },
        "xAxis": {
            "type": "value",
            "axisLabel": {"color": TOKENS["muted"]},
            "splitLine": {"lineStyle": {"color": TOKENS["line"]}},
        },
        "yAxis": {
            "type": "category",
            "inverse": True,
            "data": labels,
            "axisLabel": {"color": TOKENS["text"], "width": 250, "overflow": "truncate"},
            "axisTick": {"show": False},
        },
        "series": [
            {
                "name": "μ* Wirkung",
                "type": "bar",
                "data": [round(e.mu_star, 6) for e in rows],
                "itemStyle": {"color": TOKENS["accent"], "borderRadius": [0, 3, 3, 0]},
                "barMaxWidth": 14,
            },
            {
                "name": "σ Wechselwirkung",
                "type": "bar",
                "data": [round(e.sigma, 6) for e in rows],
                "itemStyle": {"color": TOKENS["line-strong"], "borderRadius": [0, 3, 3, 0]},
                "barMaxWidth": 14,
            },
        ],
    }


class MorrisPanel:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.target = "delta_co2_m3"
        self.screening: Screening | None = None
        base = session.shipments == session.base.shipments and not session.changes
        self.screening = load() if base else None
        self.stand = "Beispieldaten der Excel (gespeichertes Ergebnis)" if base else ""
        ui.label("Globales Screening (Morris)").classes("tk-section")
        ui.label(
            "Alle Parameter mit Bandbreite gleichzeitig variiert. μ* misst, wie stark ein Parameter die "
            "Zielgröße über seine Bandbreite im Mittel bewegt; σ zeigt Wechselwirkung mit anderen Parametern "
            "oder Nichtlinearität. Ergänzt die Tabelle oben, die je Zeile nur einen Parameter ändert. "
            "Vergleichsrechnung, nicht Teil der Excel."
        ).classes("tk-label")
        with ui.row().classes("w-full items-center gap-4 flex-wrap"):
            ui.toggle(TARGETS, value=self.target, on_change=lambda e: self._set_target(e.value)).props(
                "dense no-caps unelevated toggle-color=primary"
            )
            self.button = ui.button("Für den aktuellen Stand neu rechnen", on_click=self.recompute).props(
                "outline no-caps color=primary"
            )
        self.box = ui.column().classes("w-full gap-2")
        self.render()

    def _set_target(self, target: str) -> None:
        self.target = target
        self.render()

    async def recompute(self) -> None:
        self.button.disable()
        ui.notify("Morris-Screening läuft (240 Rechnungen, etwa 30 s)")
        try:
            self.screening = await run.io_bound(morris, self.s.model, list(self.s.shipments))
            self.stand = "aktueller Stand der Sitzung"
        finally:
            self.button.enable()
        self.render()

    def render(self) -> None:
        self.box.clear()
        with self.box:
            sc = self.screening
            if sc is None:
                components.empty_state(
                    "Für diesen Stand liegt kein Screening vor. Neu rechnen oder für die Beispieldaten "
                    "scripts/make_sensitivity.py ausführen."
                )
                return
            rows = sc.effekte[self.target]
            ui.echart(tornado_chart(sc, self.target)).classes("w-full").style(
                f"height:{60 + 30 * len(rows)}px"
            )
            top = rows[0]
            ui.label(
                f"Stärkster Treiber für {TARGETS[self.target]}: {top.kennung} {top.name} "
                f"(μ* {fmt.number(top.mu_star, 4)}). Stand: {self.stand}; {sc.trajektorien} Trajektorien, "
                f"{sc.stufen} Stufen, {sc.laeufe} Rechnungen, Startwert {sc.seed}."
            )
            bounds = load_bounds()
            data = [
                {
                    "p": f"{e.kennung} {e.name}",
                    "b": f"{fmt.number(e.min, 2)} bis {fmt.number(e.max, 2)}",
                    "m": fmt.number(e.mu_star, 4),
                    "c": f"± {fmt.number(e.mu_star_conf, 4)}",
                    "s": fmt.number(e.sigma, 4),
                    "g": bounds.get(e.parameter, {}).get("begruendung", ""),
                }
                for e in rows
            ]
            cols = [("p", "Parameter", "left"), ("b", "Bandbreite", "right"), ("m", "μ*", "right"),
                    ("c", "95 %-Intervall", "right"), ("s", "σ", "right"), ("g", "Begründung der Bandbreite", "left")]  # fmt: skip
            ui.table(
                columns=[{"name": c, "label": lab, "field": c, "align": a} for c, lab, a in cols],
                rows=data,
                row_key="p",
            ).props("dense flat hide-bottom wrap-cells").classes("w-full")
            ui.label(
                "Methode: Morris (1991), Elementareffekte mit normierter Schrittweite; Umsetzung SALib. "
                "Zielgrößen sind relative Änderungen gegen Ist bzw. ein Anteil und damit dimensionslos. "
                "Bandbreiten: data/sensitivity_bounds.json."
            ).classes("tk-label")
