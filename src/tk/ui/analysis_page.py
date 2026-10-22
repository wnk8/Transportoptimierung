"""Seite Analyse: Detailtabellen, Szenarienvergleich, Erklärung, Prüfungen und Agent-Spur.

Zeigt denselben Stand wie die Seite Eingabe (Sitzung je Browser). Alle Zahlen aus ``tk``.
"""

from __future__ import annotations

from nicegui import run, ui

from tk.analysis import input_figures
from tk.excelfn import general_text, serial_to_date
from tk.explain import SPEC, explain
from tk.models import Result
from tk.scenarios import calculate, parse_change, sensitivity_row, with_changes
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.agent_panel import render_trace
from tk.ui.layout import SCENARIO_LABEL, footer, header
from tk.ui.state import Session, reference, snapshot
from tk.ui.theme import TOKENS, apply_theme, status_chip

PCT_JS = "(v => v.toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 2}).replace('-', '\u2212') + '\u202f%')"
"""Prozent im deutschen Format für ECharts (Dezimalkomma, Minuszeichen, schmales Leerzeichen)."""

M2_BAR = "#8A99AD"
"""Balkenfarbe M2: gedämpftes Schiefergrau neben dem Akzent für M3 (Beschriftung trägt die Bedeutung)."""

TABS = {
    "sendungen": "Sendungen",
    "touren": "Touren",
    "szenarien": "Szenarien",
    "erklaerung": "Erklärung",
    "pruefungen": "Prüfungen",
    "agent": "Agent-Spur",
}
"""Tabs der Analyse; der Schlüssel ist der Wert für ``?tab=``."""


class AnalysisPage:
    """Eine Sitzung der Seite Analyse."""

    def __init__(self, session: Session) -> None:
        self.s = session
        self.explain_key = "co2_fzgkm"

    def build(self, tab: str | None) -> None:
        apply_theme()
        with ui.column().classes("tk-page w-full"):
            self.status_box = header(self.s, "/analyse", self.set_scenario)
            with ui.element("div").classes("tk-card w-full"):
                with ui.tabs().props("dense no-caps align=left") as tabs:
                    handles = {key: ui.tab(key, label) for key, label in TABS.items()}
                start = handles.get(tab or "", handles["sendungen"])
                with ui.tab_panels(tabs, value=start).classes("w-full").props("animated=false"):
                    with ui.tab_panel(handles["sendungen"]):
                        self.ship_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(handles["touren"]):
                        self.tour_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(handles["szenarien"]):
                        self.scen_box = ui.column().classes("w-full gap-3")
                    with ui.tab_panel(handles["erklaerung"]):
                        self.explain_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(handles["pruefungen"]):
                        self.check_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(handles["agent"]):
                        self.trace_box = ui.column().classes("w-full gap-2")
            footer(self.s)
        self.refresh_all()

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
        self._shipments_table(r)
        self._tours_table(r)
        self._scenarios(r)
        self._explanation(r)
        self._checks(r)
        render_trace(self.s, self.trace_box)

    def _shipments_table(self, r: Result) -> None:
        self.ship_box.clear()
        with self.ship_box:
            if not r.rows:
                components.empty_state("Noch keine Sendungen.", "Zur Eingabe", lambda: ui.navigate.to("/"))
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
            table.on("rowClick", lambda e: ui.navigate.to(f"/?tour={int(e.args[1]['nr'])}"))
            ui.label(
                "Zeile anklicken: Tour auf der Seite Eingabe in der Karte (Tab Touren) mit Begründung."
            ).classes("tk-label")

    def _scenarios(self, r: Result) -> None:
        self.scen_box.clear()
        with self.scen_box:
            ui.label("Methodenvergleich (Overview & Results, Abschnitt 1)").classes("tk-section")
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
                    "textStyle": {"fontFamily": "Inter, system-ui, sans-serif", "color": TOKENS["text"]},
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
            self._sensitivity()

    def _sensitivity(self) -> None:
        snap = snapshot()
        ui.label("Sensitivität (Overview & Results, Abschnitt 6)").classes("tk-section")
        if snap is None:
            components.empty_state("Snapshot fehlt: make reference ausführen.")
            return
        ui.label(
            "Momentaufnahme der Excel für die Beispieldaten, je Zeile ein Parameter. "
            "Python rechnet jede Zeile mit dem Kern nach."
        ).classes("tk-label")
        box = ui.column().classes("w-full")

        def render(py: dict[int, dict[str, float | int]] | None) -> None:
            box.clear()
            rows = []
            for scen in snap["szenarien"]:
                row = {
                    "s": scen["szenario"], "p": scen["parameter"],
                    "m2": fmt.percent(scen["delta_co2_m2"], 1), "m3": fmt.percent(scen["delta_co2_m3_fzgkm"], 1),
                    "k": fmt.percent(scen["delta_kosten_m3"], 1), "b": scen["bahn_sendungen"],
                    "t": scen["touren_gebuendelt"], "km": fmt.percent(scen["delta_lkw_km_m3"], 1), "py": "",
                }  # fmt: skip
                if py is not None:
                    got = py[scen["zeile"]]
                    worst = max(abs(float(got[k]) - float(scen[k])) for k in got)
                    row["py"] = f"{worst:.1e}"
                rows.append(row)
            cols = [("s", "Szenario"), ("p", "Parameter"), ("m2", "Δ CO₂e M2"), ("m3", "Δ CO₂e M3"),
                    ("k", "Δ Kosten M3"), ("b", "Bahn"), ("t", "gebündelte Touren"), ("km", "Δ Lkw-km M3"),
                    ("py", "max. Abweichung Python")]  # fmt: skip
            with box:
                ui.table(
                    columns=[{"name": c, "label": lab, "field": c, "align": "left" if c in ("s", "p") else "right"}
                             for c, lab in cols],
                    rows=rows, row_key="s",
                ).props("dense flat hide-bottom").classes("w-full")  # fmt: skip

        async def recompute() -> None:
            if self.s.shipments != self.s.base.shipments:
                ui.notify("Nachrechnung nur mit den Beispieldaten der Excel möglich.", type="warning")
                return

            def work() -> dict[int, dict[str, float | int]]:
                base = self.s.base.model
                return {
                    scen["zeile"]: sensitivity_row(calculate(self.s.base.shipments, with_changes(base, parse_change(scen["parameter"]))))
                    for scen in snap["szenarien"]
                }  # fmt: skip

            render(await run.io_bound(work))

        ui.button("Mit Python nachrechnen", on_click=recompute).props("outline no-caps color=primary")
        render(None)

    def _explanation(self, r: Result) -> None:
        self.explain_box.clear()
        with self.explain_box:
            options = {k: v["titel"] for k, v in SPEC.items()}
            content = ui.column().classes("w-full gap-2")

            def show(key: str) -> None:
                self.explain_key = key
                content.clear()
                with content:
                    explain_content(key, self.s, r)

            ui.select(
                options, value=self.explain_key, label="Kennzahl", on_change=lambda e: show(e.value)
            ).props("dense outlined").style("width:320px")
            show(self.explain_key)

    def _checks(self, r: Result) -> None:
        self.check_box.clear()
        with self.check_box:
            ok = r.gesamtstatus == "Alle Prüfungen bestanden"
            ui.label(f"Gesamtstatus: {r.gesamtstatus}").classes("tk-success" if ok else "tk-error")
            rows = [{"nr": c.nr, "name": c.name, "soll": fmt.number(c.soll, 2), "ist": fmt.number(c.ist, 2),
                     "diff": fmt.number(c.differenz, 6), "status": c.status, "text": c.beschreibung} for c in r.checks]  # fmt: skip
            ui.table(
                columns=[{"name": c, "label": lab, "field": c, "align": "right" if c in ("nr", "soll", "ist", "diff") else "left"}
                         for c, lab in [("nr", "Nr"), ("name", "Prüfung"), ("soll", "Soll"), ("ist", "Ist"),
                                        ("diff", "Differenz"), ("status", "Status"), ("text", "Was geprüft wird")]],
                rows=rows, row_key="nr", pagination={"rowsPerPage": 20},
            ).props("dense flat wrap-cells hide-bottom").classes("w-full")  # fmt: skip
            self._reference_compare(r)

    def _reference_compare(self, r: Result) -> None:
        ref = reference()
        ui.label("Referenzabgleich Python gegen Excel v11").classes("tk-section")
        if ref is None:
            components.empty_state("Referenz fehlt: make reference ausführen.")
            return
        if self.s.shipments != self.s.base.shipments or self.s.changes or self.s.road_km:
            components.note(
                "Abgleich nur für die Beispieldaten mit Parametern aus Assumptions. Beispieldaten laden und Parameter zurücksetzen."
            )
            return
        rows = []
        for name in ("Ist", "M2", "M3"):
            got = r.kpis[name].model_dump()
            for key, want in ref["kennzahlen"][name].items():
                if want is None:
                    continue
                dev = 0.0 if want == got[key] else abs(got[key] / want - 1) if want else abs(got[key])
                rows.append({"k": f"{name} {key}", "excel": general_text(want), "py": general_text(got[key]),
                             "dev": f"{dev:.1e}", "ok": "bestanden" if dev <= 1e-9 else "Abweichung"})  # fmt: skip
        ui.table(
            columns=[{"name": c, "label": lab, "field": c, "align": "left" if c in ("k", "ok") else "right"}
                     for c, lab in [("k", "Kennzahl"), ("excel", "Excel"), ("py", "Python"), ("dev", "rel. Abweichung"), ("ok", "Ergebnis (≤ 1e-9)")]],
            rows=rows, row_key="k", pagination={"rowsPerPage": 30},
        ).props("dense flat hide-bottom").classes("w-full")  # fmt: skip


def explain_content(key: str, s: Session, r: Result) -> None:
    """Erklärung einer Kennzahl: Formel, Werte, Parameter, Quelle, Systemgrenze, Verifikation."""
    ref = reference() if s.shipments == s.base.shipments and not s.changes and not s.road_km else None
    e = explain(key, s.params, r, ref)  # type: ignore[arg-type]
    ui.label(f"{e.kennzahl} ({e.einheit})").classes("tk-section")
    ui.markdown(f"$$ {e.formel} $$", extras=["latex"])
    ui.label(e.beschreibung)
    ui.label(
        "Werte: "
        + ", ".join(f"{n}: {fmt.number(v, 2) if isinstance(v, float) else v}" for n, v in e.werte.items())
    ).classes("tk-num")
    ui.label(f"Formelregister: {e.formelregister} (Assumptions K2)").classes("tk-label")
    ui.label(f"Datenquelle: {e.datenquelle}").classes("tk-label")
    ui.label(f"Systemgrenze: {e.systemgrenze}").classes("tk-label")
    ui.label(f"Verifikation: {e.verifikation}").classes("tk-note")
    if e.parameter:
        ui.table(
            columns=[{"name": c, "label": lab, "field": c, "align": "left"} for c, lab in
                     [("id", "ID"), ("name", "Parameter"), ("wert", "Wert"), ("einheit", "Einheit"), ("typ", "Typ"), ("quelle", "Quelle")]],
            rows=[{**p.model_dump(), "wert": p.wert if isinstance(p.wert, str) else general_text(p.wert).replace(".", ",")} for p in e.parameter], row_key="name",
        ).props("dense flat hide-bottom wrap-cells").classes("w-full")  # fmt: skip
