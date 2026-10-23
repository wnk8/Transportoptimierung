"""Routenvergleich unter der Karte: Routen auswählen, Varianten je Route, Verbleib der Sendungen.

Die Auswahl färbt die Linien in allen Karten (``MapView.set_highlight``) mit denselben Farben
wie Chips, Balken und Tabellen. Alle Zahlen kommen aus ``tk.compare``; die UI formatiert nur.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from nicegui import ui

from tk.compare import RouteOptions, relation_detail, route_options
from tk.excelfn import fold
from tk.models import Assumptions, Result
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.map_view import RelationView, relations, short_name, start_colors
from tk.ui.theme import MAP_LINES, SELECTION_COLORS, TOKENS

MAX_ROUTES = len(SELECTION_COLORS)
FONT = "Geist, Inter, system-ui, sans-serif"

OUTCOMES: tuple[tuple[str, str], ...] = (
    ("Lkw einzeln", TOKENS["muted"]),
    ("Sammeltour", MAP_LINES["lkw"][0]),
    ("Bahn", MAP_LINES["bahn"][0]),
)
"""Ziele im Sankey: Verbleib einer Sendung im Plan."""


def route_label(rel: RelationView) -> str:
    return f"{short_name(rel.start)} > {short_name(rel.ziel)}"


def route_param(keys: list[str], result: Result) -> str:
    """Auswahl als URL-Wert: Postleitzahlpaare ``70173-55116``, durch Komma getrennt."""
    by_key = {fold(r.key): r for r in relations(result, "Ist")}
    pairs = [f"{by_key[fold(k)].start.split(' ')[0]}-{by_key[fold(k)].ziel.split(' ')[0]}" for k in keys]
    return quote(",".join(pairs), safe=",-")


def keys_from_param(value: str | None, result: Result) -> list[str]:
    if not value:
        return []
    by_pair = {f"{r.start.split(' ')[0]}-{r.ziel.split(' ')[0]}": r.key for r in relations(result, "Ist")}
    keys = [by_pair[p] for p in value.split(",") if p in by_pair]
    return list(dict.fromkeys(keys))[:MAX_ROUTES]


def options_chart(series: list[tuple[str, str, RouteOptions]], metric: str) -> dict[str, Any]:
    """Balken je Variante in Prozent von Ist (Ist = 100), eine Reihe je ausgewählter Route.

    ``metric``: ``co2_kg`` oder ``kosten_eur``. Prozent statt absoluter Werte, damit kurze und
    lange Relationen auf einer Skala vergleichbar sind.
    """
    names = [o.name for o in series[0][2].optionen] if series else []
    data = []
    for label, color, opts in series:
        base = getattr(opts.optionen[0], metric) or 0.0
        values = [round(getattr(o, metric) / base * 100, 1) if base else None for o in opts.optionen]
        data.append(
            {
                "name": label,
                "type": "bar",
                "data": values,
                "itemStyle": {"color": color, "borderRadius": [0, 3, 3, 0]},
                "barMaxWidth": 14,
            }
        )
    if data:
        data[0]["markLine"] = {
            "symbol": "none",
            "silent": True,
            "data": [{"xAxis": 100}],
            "label": {"formatter": "Ist", "color": TOKENS["muted"], "position": "insideEndTop"},
            "lineStyle": {"color": TOKENS["muted"], "type": "dashed"},
        }
    unit = "CO₂e" if metric == "co2_kg" else "Kosten"
    return {
        "animation": False,
        "textStyle": {"fontFamily": FONT, "color": TOKENS["text"]},
        "title": {"text": f"{unit} in % von Ist", "textStyle": {"fontSize": 13, "fontWeight": 600}},
        "legend": {"top": 0, "right": 0, "textStyle": {"color": TOKENS["muted"]}},
        "grid": {"left": 170, "right": 24, "top": 48, "bottom": 28},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            ":valueFormatter": "v => v == null ? 'nicht berechenbar' : v.toLocaleString('de-DE') + ' %'",
        },
        "xAxis": {
            "type": "value",
            "axisLabel": {":formatter": "v => v.toLocaleString('de-DE') + ' %'", "color": TOKENS["muted"]},
            "splitLine": {"lineStyle": {"color": TOKENS["line"]}},
        },
        "yAxis": {
            "type": "category",
            "inverse": True,
            "data": names,
            "axisLabel": {"color": TOKENS["text"]},
            "axisLine": {"lineStyle": {"color": TOKENS["line-strong"]}},
            "axisTick": {"show": False},
        },
        "series": data,
    }


def sankey_chart(result: Result, scenario: str, sources: list[tuple[str, str, list[str]]]) -> dict[str, Any]:
    """Verbleib der Sendungen im Szenario: Quelle (Route oder Startort) nach Lkw einzeln, Sammeltour, Bahn.

    ``sources``: (Name, Farbe, Relationsschlüssel). Zählung aus :func:`relation_detail`.
    """
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    used: set[str] = set()
    for name, color, keys in sources:
        counts = [0, 0, 0]
        for key in keys:
            d = relation_detail(result, key, scenario)
            counts[0] += d.einzeln
            counts[1] += d.in_touren
            counts[2] += d.bahn
        nodes.append({"name": name, "itemStyle": {"color": color}})
        for (target, _), value in zip(OUTCOMES, counts, strict=True):
            if value:
                links.append({"source": name, "target": target, "value": value})
                used.add(target)
    nodes += [{"name": t, "itemStyle": {"color": c}} for t, c in OUTCOMES if t in used]
    return {
        "animation": False,
        "textStyle": {"fontFamily": FONT, "color": TOKENS["text"]},
        "title": {"text": "Verbleib der Sendungen", "textStyle": {"fontSize": 13, "fontWeight": 600}},
        "tooltip": {"trigger": "item", ":valueFormatter": "v => v.toLocaleString('de-DE') + ' Sendungen'"},
        "series": [
            {
                "type": "sankey",
                "top": 36,
                "bottom": 8,
                "left": 8,
                "right": 120,
                "nodeWidth": 12,
                "nodeGap": 10,
                "data": nodes,
                "links": links,
                "lineStyle": {"color": "gradient", "opacity": 0.35},
                "label": {"color": TOKENS["text"], "fontSize": 12},
                "emphasis": {"focus": "adjacency"},
            }
        ],
    }


class RouteCompare:
    """Auswahl von bis zu acht Routen und Vergleich ihrer Varianten."""

    def __init__(self, on_highlight: Callable[[dict[str, str]], None], on_url: Callable[[str], None]) -> None:
        self.on_highlight = on_highlight
        self.on_url = on_url
        self.result: Result | None = None
        self.scenario = "M3"
        self.params: Assumptions | None = None
        self.keys: list[str] = []
        self._colors: dict[str, str] = {}
        self._updating = False
        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full items-baseline justify-between"):
                ui.label("Routen vergleichen").classes("tk-section")
                ui.label(
                    "Bis zu acht Routen wählen oder eine Linie in der Karte anklicken. Die Farbe einer Route ist "
                    "in Karte, Diagramm und Tabelle gleich."
                ).classes("tk-label")
            with ui.row().classes("w-full items-center gap-2"):
                self.select = (
                    ui.select(
                        {}, multiple=True, with_input=True, label="Route hinzufügen", on_change=self._picked
                    )
                    .props("dense outlined clearable hide-selected")
                    .style("min-width:320px")
                )
                ui.button("Auswahl leeren", on_click=lambda: self.set_keys([])).props(
                    "flat dense no-caps color=primary"
                )
            self.chips = ui.row().classes("w-full gap-2 flex-wrap")
            self.body = ui.column().classes("w-full gap-4")

    def colors(self) -> dict[str, str]:
        """Farbe je Route, beim Hinzufügen vergeben; sie bleibt, wenn andere Routen entfernt werden."""
        self._colors = {k: c for k, c in self._colors.items() if k in self.keys}
        for key in self.keys:
            if key not in self._colors:
                free = [c for c in SELECTION_COLORS if c not in self._colors.values()]
                self._colors[key] = free[0]
        return dict(self._colors)

    def update(self, result: Result, scenario: str, params: Assumptions) -> None:
        self.result, self.scenario, self.params = result, scenario, params
        rels = sorted(relations(result, "Ist"), key=lambda r: (r.start, r.ziel))
        self._updating = True
        self.select.set_options({r.key: route_label(r) for r in rels})
        valid = {fold(r.key): r.key for r in rels}
        self.keys = [valid[fold(k)] for k in self.keys if fold(k) in valid]
        self.select.set_value(list(self.keys))
        self._updating = False
        self.render()

    def _picked(self, e: Any) -> None:
        if not self._updating:
            self.set_keys(list(e.value or []))

    def toggle(self, key: str) -> None:
        if key in self.keys:
            self.set_keys([k for k in self.keys if k != key])
        else:
            self.set_keys([*self.keys, key])

    def add(self, key: str) -> None:
        if key not in self.keys:
            self.set_keys([*self.keys, key])

    def set_keys(self, keys: list[str]) -> None:
        if len(keys) > MAX_ROUTES:
            ui.notify(f"Höchstens {MAX_ROUTES} Routen gleichzeitig", type="warning")
        self.keys = list(dict.fromkeys(keys))[:MAX_ROUTES]
        self._updating = True
        self.select.set_value(list(self.keys))
        self._updating = False
        self.render()

    def render(self) -> None:
        result, params = self.result, self.params
        if result is None or params is None:
            return
        colors = self.colors()
        self.on_highlight(colors)
        self.on_url(route_param(self.keys, result) if self.keys else "")
        by_key = {fold(r.key): r for r in relations(result, "Ist")}
        self.chips.clear()
        with self.chips:
            for key in self.keys:
                ui.chip(
                    route_label(by_key[fold(key)]),
                    removable=True,
                    color=colors[key],
                    text_color="white",
                    on_value_change=lambda e, k=key: None if e.value else self.toggle(k),
                ).props("dense")
        self.body.clear()
        with self.body:
            if not self.keys:
                starts = start_colors(relations(result, "Ist"))
                groups = [
                    (short_name(s), c, [r.key for r in by_key.values() if r.start == s])
                    for s, c in starts.items()
                ]
                components.empty_state(
                    "Noch keine Route gewählt. Der Überblick zeigt, wohin die Sendungen je Startort im "
                    "gewählten Szenario gehen."
                )
                ui.echart(sankey_chart(result, self.scenario, groups)).classes("w-full").style("height:260px")
                return
            series = [
                (route_label(by_key[fold(k)]), colors[k], route_options(result, k, params)) for k in self.keys
            ]
            height = 120 + 20 * len(series[0][2].optionen) * max(1, len(series)) ** 0.5
            with (
                ui.element("div")
                .classes("w-full tk-two-col")
                .style("display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:16px")
            ):
                for metric in ("co2_kg", "kosten_eur"):
                    ui.echart(options_chart(series, metric)).classes("w-full").style(f"height:{height:.0f}px")
            for label, color, opts in series:
                self._table(label, color, opts)
            groups = [(label, color, [opts.key]) for label, color, opts in series]
            ui.echart(sankey_chart(result, self.scenario, groups)).classes("w-full").style(
                f"height:{max(180, 60 * len(groups)):.0f}px"
            )
            ui.label(series[0][2].erklaerung).classes("tk-label")

    def _table(self, label: str, color: str, opts: RouteOptions) -> None:
        best_co2 = min(o.co2_kg for o in opts.optionen)
        best_cost = min(o.kosten_eur for o in opts.optionen)
        rows = [
            {
                "v": o.name,
                "f": fmt.number(o.fahrten, 1),
                "km": fmt.number(o.lkw_km, 0),
                "co2": fmt.number(o.co2_kg, 1),
                "k": fmt.number(o.kosten_eur, 2),
                "s": fmt.percent(o.servicegrad, 1, False),
                "t": f"+{fmt.number(o.zusatz_tage)} Tag(e)" if o.zusatz_tage else "",
                "h": o.hinweis,
                "best_co2": o.co2_kg == best_co2,
                "best_k": o.kosten_eur == best_cost,
            }
            for o in opts.optionen
        ]
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("items-center gap-2"):
                ui.html(
                    f'<span aria-hidden="true" style="display:inline-block;width:12px;height:12px;'
                    f'border-radius:6px;background:{color}"></span>'
                )
                ui.label(label).classes("tk-section")
                ui.label(f"{opts.sendungen} Sendungen, Ø {fmt.with_unit(opts.distanz_km, 'km', 1)}").classes(
                    "tk-label"
                )
            cols = [
                ("v", "Variante", "left"), ("f", "Lkw-Fahrten", "right"), ("km", "Lkw-km", "right"),
                ("co2", "CO₂e kg", "right"), ("k", "Kosten €", "right"), ("s", "Servicegrad", "right"),
                ("t", "Laufzeit", "right"), ("h", "Hinweis", "left"),
            ]  # fmt: skip
            table = (
                ui.table(
                    columns=[{"name": c, "label": lab, "field": c, "align": a} for c, lab, a in cols],
                    rows=rows,
                    row_key="v",
                )
                .props("dense flat hide-bottom wrap-cells")
                .classes("w-full")
            )
            table.add_slot(
                "body-cell-co2",
                "<q-td :props=\"props\" :style=\"props.row.best_co2 ? 'font-weight:600;color:var(--accent)' : ''\">"
                "{{ props.value }}{{ props.row.best_co2 ? ' (min.)' : '' }}</q-td>",
            )
            table.add_slot(
                "body-cell-k",
                "<q-td :props=\"props\" :style=\"props.row.best_k ? 'font-weight:600;color:var(--accent)' : ''\">"
                "{{ props.value }}{{ props.row.best_k ? ' (min.)' : '' }}</q-td>",
            )
