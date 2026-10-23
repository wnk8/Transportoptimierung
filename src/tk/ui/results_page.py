"""Seite Ergebnis: Headline, Kennzahlen, Karte und Tabellen zum Stand der Seite Rechnen.

Alle Zahlen aus ``tk``. Tab per ``?tab=karte|sendungen|touren|szenarien``, Tour per ``?tour=N``.
"""

from __future__ import annotations

import functools

from nicegui import ui

from tk.analysis import input_figures
from tk.excelfn import general_text, serial_to_date
from tk.models import Result
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.layout import SCENARIO_LABEL, end, hero, nav, scenario_controls, steps
from tk.ui.map_area import MapArea
from tk.ui.map_view import RELATION_EVENT
from tk.ui.route_compare import keys_from_param
from tk.ui.state import Session
from tk.ui.theme import TOKENS, apply_theme, status_chip

PCT_JS = "(v => v.toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 2}).replace('-', '\u2212') + '\u202f%')"
"""Prozent im deutschen Format für ECharts (Dezimalkomma, Minuszeichen, schmales Leerzeichen)."""

M2_BAR = "#A79BD6"
"""Balkenfarbe M2: gedämpftes Lavendel neben dem Akzent für M3 (Beschriftung trägt die Bedeutung)."""

TABS = {"karte": "Karte", "sendungen": "Sendungen", "touren": "Touren", "szenarien": "Szenarien"}
"""Tabs der Ergebnisseite; der Schlüssel ist der Wert für ``?tab=``."""


class ResultsPage:
    """Eine Sitzung der Seite Ergebnis."""

    def __init__(self, session: Session) -> None:
        self.s = session

    def build(self, tab: str | None, tour: int | None, routen: str | None = None) -> None:
        apply_theme()
        nav("/ergebnis")
        r = self.s.result
        assert r is not None
        with ui.column().classes("tk-page w-full"):
            steps(3, self.s)
            self.hero_title, self.hero_serif, self.hero_tail, self.hero_sub, _ = hero("Ergebnis", "weniger")
            with (
                ui.element("div")
                .classes("tk-toolbar")
                .props('role="toolbar" aria-label="Szenario und Aktionen"')
            ):
                self.status_box = scenario_controls(self.s, self.set_scenario)
                with ui.element("div").classes("tk-toolbar-end"):
                    ui.link("Wie wird gerechnet?", "/info?tab=erklaerung").classes("tk-link")
                    ui.button(
                        "Parameter ändern", on_click=lambda: ui.navigate.to("/rechnen#schritt-2")
                    ).props("outline no-caps color=primary")
            self.kpi_box = (
                ui.element("div").classes("tk-stats tk-reveal").style("--delay:80ms; margin-top:32px")
            )
            with ui.element("div").classes("w-full tk-reveal").style("--delay:160ms; padding-top: 40px"):
                with ui.tabs().props("dense no-caps align=left").classes("tk-pilltabs") as tabs:
                    self.handles = {key: ui.tab(key, label) for key, label in TABS.items()}
                start = self.handles.get(tab or "", self.handles["karte"])
                self.panels = (
                    ui.tab_panels(tabs, value=start, on_change=self._tab_changed)
                    .classes("w-full bg-transparent")
                    .props("animated=false keep-alive")
                )
                with self.panels:
                    with ui.tab_panel(self.handles["karte"]):
                        self.map = MapArea(self, r)
                    with ui.tab_panel(self.handles["sendungen"]):
                        self.ship_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(self.handles["touren"]):
                        self.tour_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(self.handles["szenarien"]):
                        self.scen_box = ui.column().classes("w-full gap-3")
            end(self.s)
        ui.on(RELATION_EVENT, lambda e: self.map.select_relation(str(e.args)))
        self.map.routes.keys = keys_from_param(routen, r)
        self.refresh_all()
        ui.timer(0.5, self.map.probe_tiles, once=True)
        if tour is not None and any(t.tour_nr == tour for t in r.tours):
            ui.timer(0.6, lambda: self.open_tour(tour), once=True)

    async def _tab_changed(self, _e: object) -> None:
        if self.panels.value in (self.handles["karte"], "karte"):
            await self.map.settle()

    def open_tour(self, tour_nr: int) -> None:
        """Tour in der Karte zeigen (Tab Karte, darin Touren)."""
        self.panels.set_value(self.handles["karte"])
        self.map.open_tour(tour_nr)

    def set_route_param(self, value: str) -> None:
        """Routenauswahl in der Adresse halten (teilen, neu laden), ohne die Seite neu zu laden."""
        query = "tab=karte" + (f"&routen={value}" if value else "")
        ui.navigate.history.replace(f"/ergebnis?{query}")

    def refresh_road_toggle(self) -> None:
        """Von der Straßenansicht nach dem Abruf neuer Routen aufgerufen; der Schalter liegt auf Rechnen."""
        if self.s.result is not None:
            self.map.update(self.s.result, self.s.scenario)

    def set_scenario(self, key: str) -> None:
        self.s.scenario = key
        self.refresh_all()

    def refresh_all(self) -> None:
        r = self.s.result
        if r is None:
            return
        self.status_box.clear()
        with self.status_box:
            status_chip(r.status)
        self._kpis(r)
        self.map.update(r, self.s.scenario)
        self._shipments_table(r)
        self._tours_table(r)
        self._scenarios(r)

    def _kpis(self, r: Result) -> None:
        plan = self.s.scenario != "Ist"
        k, ist = r.kpis[self.s.scenario], r.kpis["Ist"]
        self.hero_serif.set_visibility(r.n_valid > 0)
        delta = k.delta_co2_fzgkm
        self.hero_serif.set_text(
            ("mehr" if delta is not None and delta > 0 else "weniger") if plan else "im Ist"
        )
        self.hero_tail.set_text(" CO₂e" if plan and r.n_valid else "")
        if r.n_valid == 0:
            self.hero_title.set_text("Keine Sendungen")
            self.hero_sub.set_text("Auf der Seite Rechnen Sendungen erfassen oder Beispieldaten laden.")
        elif plan:
            self.hero_title.set_text(f"{fmt.percent(abs(delta) if delta is not None else None, 1, False)} ")
            self.hero_sub.set_text(
                f"{SCENARIO_LABEL[self.s.scenario]} gegen Einzelversand: {fmt.with_unit(k.co2_fzgkm_kg, 'kg')} statt "
                f"{fmt.with_unit(ist.co2_fzgkm_kg, 'kg')}."
            )
        else:
            self.hero_title.set_text(f"{fmt.with_unit(ist.co2_fzgkm_kg, 'kg')} CO₂e ")
            self.hero_sub.set_text(f"{fmt.number(r.n_valid)} Sendungen einzeln gefahren. M2 oder M3 wählen.")
        self.kpi_box.clear()
        with self.kpi_box:
            if r.n_valid == 0:
                return
            tiles = [
                (
                    "CO₂e (Fzg-km)",
                    k.co2_fzgkm_kg,
                    k.delta_co2_fzgkm,
                    "kg",
                    "co2_fzgkm",
                    ist.co2_fzgkm_kg,
                    "mint",
                ),
                ("Kosten", k.kosten_eur, k.delta_kosten, "€", "kosten", ist.kosten_eur, "sky"),
                ("Fahrzeug-km (Lkw)", k.lkw_km, k.delta_lkw_km, "km", "lkw_km", ist.lkw_km, "peach"),
            ]
            for label, value, delta, unit, key, base, tone in tiles:
                components.kpi_stat(
                    label, fmt.with_unit(value, unit), delta if plan else None,
                    f"Ist: {fmt.with_unit(base, unit)}" if plan else None, tone,
                    on_explain=functools.partial(ui.navigate.to, f"/info?tab=erklaerung&k={key}"),
                )  # fmt: skip
            components.kpi_stat(
                "Servicegrad", fmt.percent(k.servicegrad, 1, False), None,
                f"Bahn {fmt.percent(k.bahn_sendungen / r.n_valid, 1, False)}, {fmt.number(k.bahn_sendungen)} Sendungen",
                "lavender", on_explain=lambda: ui.navigate.to("/info?tab=erklaerung&k=servicegrad"),
            )  # fmt: skip

    def _shipments_table(self, r: Result) -> None:
        self.ship_box.clear()
        with self.ship_box:
            if not r.rows:
                components.empty_state(
                    "Noch keine Sendungen.", "Zur Seite Rechnen", lambda: ui.navigate.to("/rechnen")
                )
                return
            rows = []
            for row in r.rows:
                s = row.shipment
                mode = (
                    "Bahn"
                    if row.bahn == "Ja"
                    else "Sammeltour"
                    if row.tour_gebuendelt == 1 and row.buendelbar == 1
                    else "Lkw einzeln"
                )
                rows.append({
                    "zeile": row.excel_row,
                    "datum": serial_to_date(row.datum_serial).isoformat() if row.datum_serial else general_text(s.datum),
                    "start": row.start_label or general_text(s.start),
                    "ziel": row.ziel_label or general_text(s.ziel),
                    "kg": fmt.number(s.gewicht_kg if isinstance(s.gewicht_kg, int | float) else None, 1),
                    "km": fmt.number(row.distanz_km, 1) if row.distanz_km is not None else "",
                    "quelle": row.distanz_quelle or "",
                    "pruefung": row.pruefung or "",
                    "modus": mode if row.ok else "",
                    "tour": row.tour_nr or "",
                    "ergebnis": row.ergebnis or "",
                    "co2_ist": fmt.number(row.co2_ist_fzgkm, 1) if row.ok else "",
                    "co2_plan": fmt.number(row.co2_plan_fzgkm, 1) if row.ok else "",
                    "kosten_plan": fmt.number(row.kosten_plan, 2) if row.ok else "",
                })  # fmt: skip
            cols = [
                ("zeile", "Zeile", "right"), ("datum", "Datum", "left"), ("start", "Start", "left"),
                ("ziel", "Ziel", "left"), ("kg", "Gewicht kg", "right"), ("km", "Distanz km", "right"),
                ("quelle", "Quelle", "left"), ("pruefung", "Prüfung", "left"), ("modus", "Verkehrsträger", "left"),
                ("tour", "Tour", "right"), ("ergebnis", "Ergebnis", "left"), ("co2_ist", "CO₂e Ist kg", "right"),
                ("co2_plan", "CO₂e M3 kg", "right"), ("kosten_plan", "Kosten M3 €", "right"),
            ]  # fmt: skip
            with ui.row().classes("items-center gap-2"):
                mode_filter = (
                    ui.select(
                        ["Alle", "Bahn", "Sammeltour", "Lkw einzeln", "mit Hinweis"],
                        value="Alle",
                        label="Verkehrsträger",
                    )
                    .props("dense outlined")
                    .style("width:180px")
                )
                tour_filter = ui.number("Tour-Nr").props("dense outlined clearable").style("width:120px")
            table = ui.table(
                columns=[{"name": c, "label": lab, "field": c, "align": al, "sortable": True} for c, lab, al in cols],
                rows=rows, row_key="zeile", pagination={"rowsPerPage": 15},
            ).props("dense flat sticky-header").classes("w-full")  # fmt: skip

            def apply() -> None:
                sel = mode_filter.value
                tour = tour_filter.value
                table.rows = [
                    x for x in rows
                    if (sel == "Alle" or (sel == "mit Hinweis" and x["pruefung"] not in ("", "OK")) or x["modus"] == sel)
                    and (tour in (None, "") or x["tour"] == int(tour))
                ]  # fmt: skip
                table.update()

            mode_filter.on_value_change(lambda _: apply())
            tour_filter.on_value_change(lambda _: apply())

    def _tours_table(self, r: Result) -> None:
        self.tour_box.clear()
        with self.tour_box:
            if not r.tours:
                components.empty_state("Keine bündelbaren Sendungen.")
                return
            fig = input_figures(r, self.s.params)
            ui.label(
                f"{fmt.number(len(r.tours))} Touren (Next-Fit je Tag und Startort), davon "
                f"{fmt.number(fig['touren_gebuendelt'])} gebündelt mit {fmt.number(fig['sendungen_in_gebuendelten_touren'])} Sendungen."
            ).classes("tk-label")
            rows = [{
                "nr": t.tour_nr, "start": t.start, "datum": serial_to_date(t.gruppe // 10000).isoformat(),
                "n": t.sendungen, "stopps": t.stopps, "kg": fmt.number(t.gewicht_kg, 1),
                "pal": fmt.number(t.paletten, 0), "fzg": t.fahrzeug, "km": fmt.number(t.lkw_km, 1),
                "co2": fmt.number(t.co2, 1), "co2e": fmt.number(t.co2_einzel, 1),
                "kosten": fmt.number(t.kosten, 2), "kostene": fmt.number(t.kosten_einzel, 2),
                "umin": fmt.percent(t.min_auslastung, 0, False), "b": "gebündelt" if t.gebuendelt else "einzeln",
            } for t in r.tours]  # fmt: skip
            cols = [
                ("nr", "Tour"), ("datum", "Datum"), ("start", "Start"), ("n", "Sendungen"), ("stopps", "Stopps"),
                ("kg", "Gewicht kg"), ("pal", "Paletten"), ("fzg", "Fahrzeug"), ("km", "Tour-km"),
                ("umin", "min. Auslastung"), ("co2", "CO₂e Tour kg"), ("co2e", "Σ CO₂e einzeln kg"),
                ("kosten", "Kosten Tour €"), ("kostene", "Σ Kosten einzeln €"), ("b", "Entscheidung"),
            ]  # fmt: skip
            table = ui.table(
                columns=[{"name": c, "label": lab, "field": c, "sortable": True,
                          "align": "left" if c in ("start", "fzg", "b", "datum") else "right"} for c, lab in cols],
                rows=rows, row_key="nr", pagination={"rowsPerPage": 15},
            ).props("dense flat sticky-header").classes("w-full cursor-pointer")  # fmt: skip
            table.on("rowClick", lambda e: self.open_tour(int(e.args[1]["nr"])))
            ui.label("Zeile anklicken: Tour in der Karte mit Begründung.").classes("tk-label")

    def _scenarios(self, r: Result) -> None:
        self.scen_box.clear()
        with self.scen_box:
            ui.label("Methodenvergleich").classes("tk-section")
            rows = []
            for name in ("Ist", "M2", "M3"):
                k = r.kpis[name]
                rows.append({
                    "s": SCENARIO_LABEL[name],
                    "co2": fmt.number(k.co2_fzgkm_kg, 2), "dco2": fmt.percent(k.delta_co2_fzgkm, 2) if k.delta_co2_fzgkm is not None else "",
                    "tkm": fmt.number(k.co2_tkm_kg, 2), "kosten": fmt.number(k.kosten_eur, 2),
                    "dk": fmt.percent(k.delta_kosten, 2) if k.delta_kosten is not None else "",
                    "km": fmt.number(k.lkw_km, 2), "dkm": fmt.percent(k.delta_lkw_km, 2) if k.delta_lkw_km is not None else "",
                    "bahn": k.bahn_sendungen, "sg": fmt.percent(k.servicegrad, 2, False),
                })  # fmt: skip
            cols = [("s", "Szenario"), ("co2", "CO₂e Fzg-km kg"), ("dco2", "Δ"), ("tkm", "CO₂e tkm kg (Kontrolle)"),
                    ("kosten", "Kosten €"), ("dk", "Δ"), ("km", "Lkw-km"), ("dkm", "Δ"), ("bahn", "Bahn-Sendungen"),
                    ("sg", "Servicegrad")]  # fmt: skip
            ui.table(
                columns=[{"name": c, "label": lab, "field": c, "align": "left" if c == "s" else "right"} for c, lab in cols],
                rows=rows, row_key="s",
            ).props("dense flat hide-bottom").classes("w-full")  # fmt: skip
            if r.n_valid:
                m2, m3 = r.kpis["M2"], r.kpis["M3"]
                cats = ["Δ CO₂e (Fzg-km)", "Δ Kosten", "Δ Fahrzeug-km"]

                def pct(v: float | None) -> float:
                    return round((v or 0.0) * 100, 2)

                ui.echart({
                    "animation": False,
                    "textStyle": {"fontFamily": "Geist, Inter, system-ui, sans-serif", "color": TOKENS["text"]},
                    "legend": {"top": 0, "left": 0, "itemGap": 16},
                    "grid": {"left": 56, "right": 16, "top": 36, "bottom": 32},
                    "tooltip": {"trigger": "axis", ":valueFormatter": PCT_JS},
                    "xAxis": {"type": "category", "data": cats, "axisTick": {"show": False}},
                    "yAxis": {"type": "value", "axisLabel": {":formatter": PCT_JS},
                              "splitLine": {"lineStyle": {"color": TOKENS["line"]}}},
                    "series": [
                        {"name": "M2 Bündelung", "type": "bar", "barGap": "10%", "itemStyle": {"color": M2_BAR, "borderRadius": [0, 0, 6, 6]},
                         "label": {"show": True, "position": "bottom", ":formatter": "p => (" + PCT_JS + ")(p.value)"},
                         "data": [pct(m2.delta_co2_fzgkm), pct(m2.delta_kosten), pct(m2.delta_lkw_km)]},
                        {"name": "M3 Bahn + Bündelung", "type": "bar", "itemStyle": {"color": TOKENS["accent"], "borderRadius": [0, 0, 6, 6]},
                         "label": {"show": True, "position": "bottom", ":formatter": "p => (" + PCT_JS + ")(p.value)"},
                         "data": [pct(m3.delta_co2_fzgkm), pct(m3.delta_kosten), pct(m3.delta_lkw_km)]},
                    ],
                }).classes("w-full").style("height:300px")  # fmt: skip
                if m2.kosten_eur == m3.kosten_eur:
                    components.note(
                        "Die Kosten von M2 und M3 sind gleich, weil die Bahn mit A07 = 0 so viel kostet wie der "
                        "Lkw-Einzelversand der Sendung und M2 die Bahn-Sendungen mit genau diesen Einzelkosten führt."
                    )
