"""Hauptseite gemäß Layout 7.4: Kopfzeile, Eingabe und Parameter, Karte, Kennzahlen, Tabs.

Alle Zahlen kommen aus ``tk`` (Rechenkern). Beim Start sind die Beispieldaten der
Excel-Mappe geladen. Start: ``make run`` (http://127.0.0.1:8080).
"""

from __future__ import annotations

import datetime as dt
import functools
import os
from typing import Any

from nicegui import app, events, run, ui

from tk.analysis import input_figures
from tk.excelfn import general_text, serial_to_date
from tk.explain import SPEC, explain
from tk.geo import resolve_place
from tk.inputs import parse_csv_bytes, parse_text, parse_xlsx
from tk.models import Result, Shipment
from tk.routing import relation_table_csv
from tk.scenarios import calculate, parse_change, sensitivity_row, with_changes
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.map_area import MapArea, route_cache
from tk.ui.map_view import RELATION_EVENT
from tk.ui.preview import preview_page
from tk.ui.state import Session, base_data, reference, snapshot
from tk.ui.theme import ScenarioToggle, apply_theme, status_chip

SCENARIO_LABEL = {"Ist": "Ist (Einzelversand)", "M2": "M2 Bündelung", "M3": "M3 Bahn + Bündelung"}
PARAMS_PANEL = [
    ("A01", "a01_bahn_grenze_km", 1.0),
    ("A02", "a02_vnl_km", 1.0),
    ("A05", "a05_zusatz_tage", 1.0),
    ("A08", "a08_kosten_tol", 0.01),
    ("A10", "a10_umweg", 0.01),
    ("A09", "a09_schwelle", 0.01),
    ("I01", "i01_strassenfaktor", 0.01),
]
"""Parameter im Panel: Kennung, Feld, Schrittweite. Werte und Einheiten aus Assumptions."""

FOOTER = (
    "© OpenStreetMap contributors (Kartendaten, ODbL) | Postleitzahl- und Ortsdaten: GeoNames, geonames.org, "
    "CC BY 4.0 | Rechenmodell: Excel v11, Python-Port"
)


class Page:
    """Eine Sitzung der Hauptseite."""

    def __init__(self, session: Session) -> None:
        self.s = session
        self.busy = False
        self.explain_key = "co2_fzgkm"

    # ---------- Aufbau ----------
    def build(self) -> None:
        apply_theme()
        with ui.column().classes("tk-page w-full"):
            self._header()
            with ui.row().classes("w-full gap-4 no-wrap items-start tk-two-col"):
                with ui.column().classes("gap-4").style("width:380px;min-width:340px;flex-shrink:0"):
                    self._input_card()
                    self._param_card()
                with ui.column().classes("gap-4 flex-1 min-w-0"):
                    with ui.element("div").classes("tk-card w-full"):
                        assert self.s.result is not None
                        self.map = MapArea(self, self.s.result)
                    self.progress = ui.element("div").classes("tk-progress w-full")
                    with self.progress:
                        ui.element("div")
                    self.progress.set_visibility(False)
                    self.kpi_box = (
                        ui.element("div")
                        .classes("grid gap-4 w-full")
                        .style("grid-template-columns:repeat(4,minmax(0,1fr))")
                    )
            self._tabs()
            ui.label(f"{FOOTER} | Datenstand: {self.s.base.source}").classes("tk-footer")
        ui.on(RELATION_EVENT, lambda e: self.map.select_relation(str(e.args)))
        self.refresh_all()
        ui.timer(0.5, self.map.probe_tiles, once=True)

    def _header(self) -> None:
        with ui.row().classes("w-full items-center justify-between gap-4 flex-wrap"):
            with ui.row().classes("items-baseline gap-3"):
                ui.label("Transportkonzept").classes("tk-title")
                ui.label("Nachhaltiges Transportkonzept, Excel v11").classes("tk-label")
            with ui.row().classes("items-center gap-4"):
                self.toggle = ScenarioToggle(self.s.scenario, self.set_scenario)
                self.status_box = ui.row().classes("items-center")

    def _input_card(self) -> None:
        with ui.element("div").classes("tk-card w-full flex flex-col gap-3"):
            ui.label("Eingabe").classes("tk-section")
            self.count_label = ui.label("").classes("tk-label")
            with ui.tabs().props("dense no-caps align=left").classes("w-full") as tabs:
                t_form = ui.tab("Formular")
                t_paste = ui.tab("Einfügen / CSV")
                self.t_agent = ui.tab("Freitext")
            with ui.tab_panels(tabs, value=t_form).classes("w-full").props("animated=false"):
                with ui.tab_panel(t_form).classes("p-0"):
                    self._form()
                with ui.tab_panel(t_paste).classes("p-0"):
                    self._paste()
                with ui.tab_panel(self.t_agent).classes("p-0"):
                    self.agent_box = ui.column().classes("w-full gap-2")
                    self.build_agent_input(self.agent_box)
            with ui.row().classes("gap-2 flex-wrap"):
                ui.button("Beispieldaten laden", on_click=self.load_sample).props(
                    "outline no-caps color=primary"
                )
                ui.button("Alle entfernen", on_click=self.clear_all).props("flat no-caps color=negative")
            self.export_box = ui.row().classes("gap-2 flex-wrap")
            self.build_export(self.export_box)
            self.input_msg = ui.column().classes("w-full")

    def _form(self) -> None:
        with ui.column().classes("w-full gap-1"):
            today = dt.date.today().isoformat()
            self.f_datum = (
                ui.input("Datum (JJJJ-MM-TT)", value=today).props("dense outlined").classes("w-full")
            )
            self.f_start = ui.input("Start (PLZ oder Ort)").props("dense outlined").classes("w-full")
            self.f_start_hint = ui.label("").classes("tk-label")
            self.f_ziel = ui.input("Ziel (PLZ oder Ort)").props("dense outlined").classes("w-full")
            self.f_ziel_hint = ui.label("").classes("tk-label")
            self.f_kg = ui.number("Gewicht kg", min=0).props("dense outlined").classes("w-full")
            with ui.expansion("Optionale Angaben").props("dense").classes("w-full"):
                self.f_id = ui.input("Sendungs-ID").props("dense outlined").classes("w-full")
                self.f_km = (
                    ui.number("Entfernung km (überschreibt die Distanz)")
                    .props("dense outlined")
                    .classes("w-full")
                )
                self.f_pal = (
                    ui.number("Paletten (leer: Gewicht / A14)").props("dense outlined").classes("w-full")
                )
                self.f_fr = (
                    ui.number("Frachtkosten € (leer: Modell x C04)").props("dense outlined").classes("w-full")
                )
            self.f_start.on("blur", lambda: self._hint(self.f_start, self.f_start_hint))
            self.f_ziel.on("blur", lambda: self._hint(self.f_ziel, self.f_ziel_hint))
            ui.button("Sendung hinzufügen", on_click=self.add_from_form).props(
                "unelevated no-caps color=primary"
            )

    def _hint(self, field: ui.input, hint: ui.label) -> None:
        text = (field.value or "").strip()
        if not text:
            hint.set_text("")
            return
        place = resolve_place(text, self.s.model.db, self.s.params)
        if place.lat is not None:
            hint.set_text(f"Zuordnung: {place.label} ({place.art})")
        else:
            hint.set_text(f"Keine Koordinate: {place.art}. PLZ angeben oder Entfernung eintragen.")

    def _paste(self) -> None:
        with ui.column().classes("w-full gap-2"):
            ui.label(
                "Spalten A bis H wie im Blatt Input: Datum, Start, Ziel, Gewicht kg, Sendungs-ID, "
                "Entfernung km, Paletten, Fracht €. Kopfzeile optional."
            ).classes("tk-label")
            self.paste_area = (
                ui.textarea("Aus Excel einfügen").props("outlined dense rows=5").classes("w-full")
            )
            self.paste_mode = ui.toggle({"append": "Anhängen", "replace": "Ersetzen"}, value="append").props(
                "dense no-caps unelevated toggle-color=primary"
            )
            ui.button("Übernehmen", on_click=self.add_from_paste).props("unelevated no-caps color=primary")
            ui.upload(label="CSV oder XLSX hochladen", auto_upload=True, on_upload=self.upload).props(
                'accept=".csv,.txt,.xlsx" flat bordered'
            ).classes("w-full")

    def _param_card(self) -> None:
        with ui.element("div").classes("tk-card w-full flex flex-col gap-2"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Parameter").classes("tk-section")
                ui.button("Zurücksetzen", on_click=self.reset_params).props("flat dense no-caps").classes(
                    "tk-link"
                )
            ui.label("Standardwerte aus Assumptions. Änderung rechnet sofort neu.").classes("tk-label")
            self.param_inputs: dict[str, ui.number] = {}
            p = self.s.base.model.params
            for pid, field, step in PARAMS_PANEL:
                meta = p.meta[field]
                with ui.row().classes("w-full items-center no-wrap gap-2"):
                    ui.label(pid).classes("tk-label").style("width:30px")
                    num = (
                        ui.number(
                            label=meta.name,
                            value=getattr(p, field),
                            step=step,
                            format="%.4g",
                            on_change=lambda e, f=field: self.set_param(f, e.value),
                        )
                        .props("dense outlined debounce=400")
                        .classes("flex-1")
                    )
                    ui.label(meta.unit).classes("tk-label").style("width:56px")
                    self.param_inputs[field] = num
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                ui.label("A04").classes("tk-label").style("width:30px")
                self.traction = (
                    ui.select(
                        {"elektrisch": "elektrisch", "Diesel": "Diesel"},
                        value=p.a04_traktion,
                        label="Bahn-Traktion (bestimmt C01)",
                        on_change=lambda e: self.set_param("a04_traktion", e.value),
                    )
                    .props("dense outlined")
                    .classes("flex-1")
                )
                self.c01_label = ui.label("").classes("tk-label").style("width:56px")
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                self.road_switch = ui.switch(
                    "Variante: Distanz aus Straßenrouten (ORS)",
                    on_change=lambda e: self.set_road_km(bool(e.value)),
                ).props("dense color=primary")
                ui.button(
                    "Relationstabelle",
                    on_click=lambda: (
                        ui.download.content(
                            relation_table_csv(self.s.result, route_cache()).encode("utf-8-sig"),
                            "relationstabelle_plz_orte.csv",
                        )
                        if self.s.result is not None
                        else None
                    ),
                ).props("flat dense no-caps color=primary").tooltip(
                    "Straßen-km zum Einfügen in PLZ_Orte R:T der Excel"
                )
            self.road_hint = ui.label("").classes("tk-label")
            self.param_note = ui.label("").classes("tk-note")
            self.param_note.set_visibility(False)

    def _tabs(self) -> None:
        with ui.element("div").classes("tk-card w-full"):
            with ui.tabs().props("dense no-caps align=left") as tabs:
                t1 = ui.tab("Sendungen")
                t2 = ui.tab("Touren")
                t3 = ui.tab("Szenarien")
                t4 = ui.tab("Erklärung")
                t5 = ui.tab("Prüfungen")
                t6 = ui.tab("Agent-Spur")
            with ui.tab_panels(tabs, value=t1).classes("w-full").props("animated=false"):
                with ui.tab_panel(t1):
                    self.ship_box = ui.column().classes("w-full gap-2")
                with ui.tab_panel(t2):
                    self.tour_box = ui.column().classes("w-full gap-2")
                with ui.tab_panel(t3):
                    self.scen_box = ui.column().classes("w-full gap-3")
                with ui.tab_panel(t4):
                    self.explain_box = ui.column().classes("w-full gap-2")
                with ui.tab_panel(t5):
                    self.check_box = ui.column().classes("w-full gap-2")
                with ui.tab_panel(t6):
                    self.trace_box = ui.column().classes("w-full gap-2")

    # ---------- Erweiterungspunkte (Agent S15, Export S16) ----------
    def build_agent_input(self, box: ui.column) -> None:
        from tk.ui.agent_panel import build_agent_input

        build_agent_input(self, box)

    def build_export(self, box: ui.row) -> None:
        from tk.ui.export_panel import build_export

        build_export(self, box)

    def render_trace(self) -> None:
        from tk.ui.agent_panel import render_trace

        render_trace(self, self.trace_box)

    # ---------- Aktionen ----------
    def set_scenario(self, key: str) -> None:
        self.s.scenario = key
        self.refresh_all()

    def set_param(self, field: str, value: Any) -> None:
        if value is None or value == "":
            return
        base = getattr(self.s.base.model.params, field)
        if value == base:
            self.s.changes.pop(field, None)
        else:
            self.s.changes[field] = value
        ui.timer(0, self.recalculate, once=True)

    def set_road_km(self, on: bool) -> None:
        if on == self.s.road_km:
            return
        self.s.road_km = on
        ui.timer(0, self.recalculate, once=True)

    def refresh_road_toggle(self) -> None:
        n = len(route_cache())
        self.road_switch.set_enabled(n > 0)
        if n == 0:
            self.road_hint.set_text("Keine Straßenrouten im Cache: ORS_API_KEY in .env und make routes.")
        elif self.s.road_km and self.s.result is not None:
            used = sum(1 for r in self.s.result.valid_rows if r.distanz_quelle == "Relationstabelle")
            self.road_hint.set_text(
                f"{used} Sendungen rechnen mit Straßen-km (Quelle Relationstabelle). Die Referenzwerte der Excel gelten "
                "für diese Variante nicht."
            )
        else:
            self.road_hint.set_text(f"{n} Straßenrouten im Cache. Standard: Luftlinie × I01 wie die Excel.")

    def reset_params(self) -> None:
        self.s.changes.clear()
        p = self.s.base.model.params
        for field, num in self.param_inputs.items():
            num.set_value(getattr(p, field))
        self.traction.set_value(p.a04_traktion)
        ui.timer(0, self.recalculate, once=True)

    async def recalculate(self) -> None:
        self.progress.set_visibility(True)
        try:
            await run.io_bound(self.s.recalculate)
        except Exception as exc:
            self._message(
                "error", f"Rechnung nicht möglich: {exc}", "Parameter zurücksetzen oder Eingabe prüfen."
            )
        finally:
            self.progress.set_visibility(False)
        self.refresh_all()

    def _message(self, kind: str, text: str, next_step: str = "") -> None:
        self.input_msg.clear()
        with self.input_msg:
            if kind == "error":
                components.error_state(text, next_step)
            elif kind == "note":
                components.note(text)
            else:
                components.success_state(text)

    async def set_shipments(self, shipments: list[Shipment], replace: bool, origin: str) -> None:
        self.s.shipments = list(shipments) if replace else [*self.s.shipments, *shipments]
        await self.recalculate()
        result = self.s.result
        assert result is not None
        bad = (
            [r for r in result.rows[-len(shipments) :] if r.pruefung and r.pruefung != "OK"]
            if shipments
            else []
        )
        if bad:
            first = bad[0]
            self._message(
                "error",
                f"{origin}: {len(bad)} Zeile(n) mit Hinweis, zuerst Zeile {first.excel_row}: {first.pruefung}",
                "Hinweis in Spalte I beheben: Pflichtfeld ergänzen, PLZ angeben oder Entfernung eintragen.",
            )
        else:
            self._message("success", f"{origin}: {len(shipments)} Sendung(en) übernommen und gerechnet.")

    async def add_from_form(self) -> None:
        def val(x: Any) -> Any:
            return None if x in (None, "") else x

        ship = Shipment(
            datum=val(self.f_datum.value), start=val(self.f_start.value), ziel=val(self.f_ziel.value),
            gewicht_kg=val(self.f_kg.value), sendungs_id=val(self.f_id.value), km=val(self.f_km.value),
            paletten=val(self.f_pal.value), fracht_eur=val(self.f_fr.value),
        )  # fmt: skip
        check = calculate([ship], self.s.model).rows[0]
        if check.pruefung != "OK":
            self._message("error", f"Eingabe prüfen: {check.pruefung}", self._next_step(check.pruefung or ""))
            return
        await self.set_shipments([ship], replace=False, origin="Formular")

    @staticmethod
    def _next_step(message: str) -> str:
        if "fehlt" in message:
            return "Pflichtfeld ausfüllen (Datum, Start, Ziel oder Entfernung, Gewicht)."
        if "nicht gefunden" in message or "mehrdeutig" in message or "unsicher" in message:
            return "PLZ angeben (fünfstellig) oder Entfernung in km eintragen."
        if "Datum" in message:
            return "Datum als JJJJ-MM-TT oder TT.MM.JJJJ eingeben (Jahr 2000 bis 2099)."
        if "gleich" in message:
            return "Entfernung in km eintragen."
        return "Wert als Zahl größer 0 eingeben."

    async def add_from_paste(self) -> None:
        ships = parse_text(self.paste_area.value or "")
        if not ships:
            self._message(
                "error", "Keine Zeilen erkannt.", "Zeilen aus Excel kopieren (Spalten A bis H) und einfügen."
            )
            return
        await self.set_shipments(ships, replace=self.paste_mode.value == "replace", origin="Einfügen")

    async def upload(self, e: events.UploadEventArguments) -> None:
        data = await e.file.read()
        name = e.file.name.lower()
        try:
            ships = parse_xlsx(data) if name.endswith(".xlsx") else parse_csv_bytes(data)
        except Exception as exc:
            self._message(
                "error",
                f"Datei nicht lesbar: {exc}",
                "CSV (Semikolon) oder XLSX im Schema Input!A:H verwenden.",
            )
            return
        await self.set_shipments(ships, replace=self.paste_mode.value == "replace", origin=e.file.name)

    async def load_sample(self) -> None:
        await self.set_shipments(self.s.base.shipments, replace=True, origin="Beispieldaten")

    async def clear_all(self) -> None:
        self.s.shipments = []
        await self.recalculate()
        self._message("note", "Alle Sendungen entfernt. Die Excel-Mappe bleibt unverändert.")

    # ---------- Darstellung ----------
    def refresh_all(self) -> None:
        r = self.s.result
        if r is None:
            return
        self.status_box.clear()
        with self.status_box:
            status_chip(r.status)
        self.count_label.set_text(
            f"{fmt.number(len(self.s.shipments))} Zeilen, davon {fmt.number(r.n_valid)} gültig"
        )
        p = self.s.params
        self.c01_label.set_text(f"{fmt.number(p.c01_bahn_faktor, 1)} g/tkm")
        changed = [
            f"{p.meta[f].id} = {general_text(v) if not isinstance(v, str) else v}"
            for f, v in self.s.changes.items()
        ]
        self.param_note.set_text("Abweichend von Assumptions: " + ", ".join(changed))
        self.param_note.set_visibility(bool(changed))
        self.refresh_road_toggle()
        self._kpis(r)
        self.map.update(r, self.s.scenario)
        self._shipments_table(r)
        self._tours_table(r)
        self._scenarios(r)
        self._explanation(r)
        self._checks(r)
        self.render_trace()

    def _kpis(self, r: Result) -> None:
        self.kpi_box.clear()
        with self.kpi_box:
            if r.n_valid == 0:
                components.empty_state("Keine gültigen Sendungen.", "Beispieldaten laden", self.load_sample)
                return
            k, ist = r.kpis[self.s.scenario], r.kpis["Ist"]
            plan = self.s.scenario != "Ist"
            tiles = [
                ("CO₂e (Fzg-km)", k.co2_fzgkm_kg, k.delta_co2_fzgkm, "kg", "co2_fzgkm", ist.co2_fzgkm_kg),
                ("Kosten", k.kosten_eur, k.delta_kosten, "€", "kosten", ist.kosten_eur),
                ("Fahrzeug-km (Lkw)", k.lkw_km, k.delta_lkw_km, "km", "lkw_km", ist.lkw_km),
            ]
            for label, value, delta, unit, key, base in tiles:
                components.kpi_tile(
                    f"{label}, {self.s.scenario}", value, base if plan else None, delta if plan else None, unit,
                    on_explain=functools.partial(self.open_explain, key),
                )  # fmt: skip
            components.kpi_tile(
                f"Servicegrad, {self.s.scenario}", k.servicegrad, None, None, "%",
                on_explain=lambda: self.open_explain("servicegrad"),
                extra=f"Anteil Bahn: {fmt.percent(k.bahn_sendungen / r.n_valid, 1, False)} "
                f"({fmt.number(k.bahn_sendungen)} Sendungen)",
            )  # fmt: skip

    def _shipments_table(self, r: Result) -> None:
        self.ship_box.clear()
        with self.ship_box:
            if not r.rows:
                components.empty_state("Noch keine Sendungen.", "Beispieldaten laden", self.load_sample)
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
            table.on("rowClick", lambda e: self.map.open_tour(int(e.args[1]["nr"])))
            ui.label("Zeile anklicken: Tour in der Karte (Tab Touren) mit Begründung.").classes("tk-label")

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
                    "textStyle": {"fontFamily": "Inter, system-ui, sans-serif", "color": "#1F2933"},
                    "legend": {"top": 0, "left": 0, "itemGap": 16},
                    "grid": {"left": 56, "right": 16, "top": 36, "bottom": 32},
                    "tooltip": {"trigger": "axis", "valueFormatter": "value => value.toLocaleString('de-DE') + ' %'"},
                    "xAxis": {"type": "category", "data": cats, "axisTick": {"show": False}},
                    "yAxis": {"type": "value", "axisLabel": {"formatter": "{value} %"},
                              "splitLine": {"lineStyle": {"color": "#E3E6EA"}}},
                    "series": [
                        {"name": "M2 Bündelung", "type": "bar", "barGap": "10%", "itemStyle": {"color": "#56616E"},
                         "label": {"show": True, "position": "bottom", "formatter": "{c} %"},
                         "data": [pct(m2.delta_co2_fzgkm), pct(m2.delta_kosten), pct(m2.delta_lkw_km)]},
                        {"name": "M3 Bahn + Bündelung", "type": "bar", "itemStyle": {"color": "#1F6F5F"},
                         "label": {"show": True, "position": "bottom", "formatter": "{c} %"},
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

    def open_explain(self, key: str) -> None:
        self.explain_key = key
        r = self.s.result
        if r is None:
            return
        with ui.dialog() as dialog, ui.card().classes("tk-card").style("max-width:760px"):
            self._explain_content(key, r)
            ui.button("Schließen", on_click=dialog.close).props("flat no-caps color=primary")
        dialog.open()

    def _explain_content(self, key: str, r: Result) -> None:
        ref = (
            reference()
            if self.s.shipments == self.s.base.shipments and not self.s.changes and not self.s.road_km
            else None
        )
        e = explain(key, self.s.params, r, ref)  # type: ignore[arg-type]
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

    def _explanation(self, r: Result) -> None:
        self.explain_box.clear()
        with self.explain_box:
            options = {k: v["titel"] for k, v in SPEC.items()}
            content = ui.column().classes("w-full gap-2")

            def show(key: str) -> None:
                self.explain_key = key
                content.clear()
                with content:
                    self._explain_content(key, r)

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


@ui.page("/")
async def index() -> None:
    base = base_data()
    if base is None:
        apply_theme()
        with ui.column().classes("tk-page"):
            ui.label("Transportkonzept").classes("tk-title")
            components.error_state(
                "Excel-Mappe nicht gefunden: data/excel/Thema1_Transportkonzept_v11_Beispieldaten.xlsx",
                "Mappe in den Ordner data/excel kopieren und die Seite neu laden (siehe README).",
            )
        return
    session = Session(base=base, shipments=list(base.shipments), result=base.result)
    page = Page(session)
    app.storage.client["page"] = page
    page.build()


@ui.page("/vorschau")
def vorschau() -> None:
    preview_page()


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()  # GEMINI_API_KEY only from the local .env file
    ui.run(
        title="Transportkonzept",
        host=os.environ.get("TK_HOST", "127.0.0.1"),
        port=int(os.environ.get("TK_PORT", "8080")),
        reload=False,
        show=False,
        language="de",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
