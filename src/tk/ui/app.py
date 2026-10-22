"""Seite Eingabe: Schritt 1 Sendungen, Schritt 2 Parameter, daneben Kennzahlen und Karte.

Detailtabellen stehen auf der Seite Analyse (``/analyse``). Alle Zahlen kommen aus ``tk``
(Rechenkern). Beim Start sind die Beispieldaten der Excel-Mappe geladen.
Start: ``make run`` (http://127.0.0.1:8080).
"""

from __future__ import annotations

import datetime as dt
import functools
import os
import secrets
from typing import Any

from nicegui import app, events, run, ui

from tk.geo import resolve_place
from tk.inputs import parse_csv_bytes, parse_text, parse_xlsx
from tk.models import Result, Shipment
from tk.routing import relation_table_csv
from tk.scenarios import calculate
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.analysis_page import AnalysisPage, explain_content
from tk.ui.layout import SCENARIO_LABEL, end, missing_workbook, nav, nav_kpis, scenario_controls
from tk.ui.map_area import MapArea, route_cache
from tk.ui.map_view import RELATION_EVENT
from tk.ui.preview import preview_page
from tk.ui.state import Session, base_data, session_for
from tk.ui.theme import apply_theme, status_chip

PARAM_GROUPS: list[tuple[str, list[tuple[str, float, str]]]] = [
    ("Bahnverlagerung (M3)", [
        ("a01_bahn_grenze_km", 1.0, "Ab dieser Sendungsdistanz prüft M3 die Bahn."),
        ("a02_vnl_km", 1.0, "Lkw-Strecke zum und vom Terminal je verlagerter Sendung."),
        ("a05_zusatz_tage", 1.0, "Längere Laufzeit der Bahn. Zulässig bis {a06} Tage (A06)."),
    ]),
    ("Bündelung (M2)", [
        ("a10_umweg", 1.0, "Mehrweg je zusätzlichem Stopp einer Sammeltour."),
        ("a09_schwelle", 1.0, "Touren unter dieser Auslastung gelten als schlecht ausgelastet."),
    ]),
    ("Kosten", [
        ("a08_kosten_tol", 1.0, "Höchste zulässige Mehrkosten einer Maßnahme gegenüber Ist."),
    ]),
    ("Distanz", [
        ("i01_strassenfaktor", 0.01, "Umrechnung Luftlinie in Straßenkilometer."),
    ]),
]  # fmt: skip
"""Parameter im Panel: Gruppe, dann Feld, Schrittweite (in Anzeigeeinheit) und Hilfetext.
Name, Einheit, Quelle und Standardwert kommen aus Assumptions."""

MIN_VALUE = {"i01_strassenfaktor": 1.0}
"""Untergrenzen der Eingabe außer 0: Straßenentfernung ist nie kürzer als die Luftlinie."""

SCHEMA = [("A", "Datum"), ("B", "Start"), ("C", "Ziel"), ("D", "Gewicht kg"), ("E", "Sendungs-ID"),
          ("F", "Entfernung km"), ("G", "Paletten"), ("H", "Fracht €")]  # fmt: skip
"""Spalten des Blatts Input."""


def _num(value: float) -> str:
    return fmt.number(value, 0 if float(value).is_integer() else 2)


class Page:
    """Eine Sitzung der Seite Eingabe."""

    def __init__(self, session: Session) -> None:
        self.s = session
        self.busy = False
        self.param_fields: dict[str, tuple[ui.element, ui.number, ui.label, str]] = {}

    # ---------- Aufbau ----------
    def build(self, tour: int | None = None) -> None:
        apply_theme()
        ui.query("body").classes(add="tk-hero-page")
        self.nav_kpi_box = nav("/")
        with ui.column().classes("tk-page w-full"):
            self._hero()
            self._input_section()
            self._param_section()
            _, map_body = components.section(
                3, "Karte", "Vorher und nachher", "Relationen als Luftlinie, schematisch. Linie anklicken "
                "für den Vergleich Ist gegen Plan.", tone="sky", anchor="karte", delay=240,
            )  # fmt: skip
            map_body.classes("tk-sec-wide")
            with map_body:
                assert self.s.result is not None
                self.map = MapArea(self, self.s.result)
            self.summary_box = end(self.s, "/analyse", "Weiter zur Analyse")
        ui.on(RELATION_EVENT, lambda e: self.map.select_relation(str(e.args)))
        self.refresh_all()
        ui.timer(0.5, self.map.probe_tiles, once=True)
        if (
            tour is not None
            and self.s.result is not None
            and any(t.tour_nr == tour for t in self.s.result.tours)
        ):
            ui.timer(0.6, lambda: self.map.open_tour(tour), once=True)

    def _hero(self) -> None:
        with ui.element("div").classes("tk-hero tk-reveal"):
            with ui.element("div"):
                with ui.element("h1").classes("tk-hero-title"):
                    self.hero_title = ui.label("").classes("inline")
                    ui.label(".").classes("inline tk-dot")
                self.hero_sub = ui.label("").classes("tk-hero-sub")
            self.status_box = scenario_controls(self.s, self.set_scenario)
        self.kpi_box = ui.element("div").classes("tk-stats tk-reveal").style("--delay:80ms")
        self.progress = ui.row().classes("w-full items-center gap-3 no-wrap pt-3").props('role="status"')
        with self.progress:
            ui.label("Rechnet neu").classes("tk-label")
            with ui.element("div").classes("tk-progress flex-1"):
                ui.element("div")
        self.progress.set_visibility(False)

    def _input_section(self) -> None:
        self.count_label, body = components.section(
            1, "Sendungen", "Sendungen erfassen", "Einzeln im Formular, als Tabelle aus Excel oder in Worten "
            "über den Assistenten.", tone="mint", anchor="schritt-1", delay=120,
        )  # fmt: skip
        with body:
            with ui.tabs().props("dense no-caps align=left").classes("w-full") as tabs:
                t_form = ui.tab("Formular")
                t_paste = ui.tab("Einfügen / CSV")
                self.t_agent = ui.tab("Freitext")
            with ui.tab_panels(tabs, value=t_form).classes("w-full bg-transparent").props("animated=false"):
                with ui.tab_panel(t_form):
                    self._form()
                with ui.tab_panel(t_paste):
                    self._paste()
                with ui.tab_panel(self.t_agent):
                    self.agent_box = ui.column().classes("w-full gap-2")
                    self.build_agent_input(self.agent_box)
            self.input_msg = ui.column().classes("w-full")
            ui.label("Datenbestand").classes("tk-group")
            with ui.row().classes("gap-4 flex-wrap items-center"):
                ui.button("Beispieldaten laden", on_click=self.load_sample).props(
                    "outline no-caps color=primary"
                )
                ui.button("Alle entfernen", on_click=self.clear_all).props("flat no-caps color=negative")
                self.export_box = ui.row().classes("gap-2 flex-wrap")
                self.build_export(self.export_box)

    def _form(self) -> None:
        p = self.s.params
        with ui.element("div").classes("tk-grid-2"):
            with ui.element("div").classes("tk-field"):
                ui.label("Datum (Pflicht)").classes("tk-field-label")
                self.f_datum = (
                    ui.input(value=dt.date.today().isoformat())
                    .props('dense outlined aria-label="Datum"')
                    .classes("w-full")
                )
                ui.label("JJJJ-MM-TT oder TT.MM.JJJJ").classes("tk-help")
            _, self.f_kg, _ = components.number_field(
                "Gewicht (Pflicht)", "kg", "Bruttogewicht der Sendung.", minimum=0
            )
            with ui.element("div").classes("tk-field"):
                ui.label("Start (Pflicht)").classes("tk-field-label")
                self.f_start = ui.input().props('dense outlined aria-label="Start"').classes("w-full")
                self.f_start_hint = ui.label("PLZ fünfstellig oder Ortsname").classes("tk-help")
            with ui.element("div").classes("tk-field"):
                ui.label("Ziel (Pflicht)").classes("tk-field-label")
                self.f_ziel = ui.input().props('dense outlined aria-label="Ziel"').classes("w-full")
                self.f_ziel_hint = ui.label("PLZ fünfstellig oder Ortsname").classes("tk-help")
        with (
            ui.expansion("Optionale Angaben").props("dense").classes("w-full pt-2"),
            ui.element("div").classes("tk-grid-2 pt-2"),
        ):
            with ui.element("div").classes("tk-field"):
                ui.label("Sendungs-ID").classes("tk-field-label")
                self.f_id = ui.input().props('dense outlined aria-label="Sendungs-ID"').classes("w-full")
            _, self.f_km, _ = components.number_field(
                "Entfernung",
                "km",
                "Leer: Luftlinie × I01. Ein Wert hier überschreibt die Distanz.",
                minimum=0,
            )
            _, self.f_pal, _ = components.number_field(
                "Paletten", "Pal.",
                f"Leer: Gewicht / {_num(p.a14_kg_je_palette)} kg je Palette (A14).", minimum=0,
            )  # fmt: skip
            _, self.f_fr, _ = components.number_field(
                "Frachtkosten", "€", "Leer: Modellkosten × C04.", minimum=0
            )
        self.f_start.on("blur", lambda: self._hint(self.f_start, self.f_start_hint))
        self.f_ziel.on("blur", lambda: self._hint(self.f_ziel, self.f_ziel_hint))
        ui.button("Sendung hinzufügen", on_click=self.add_from_form).props(
            "unelevated no-caps color=primary"
        ).classes("tk-cta self-start")

    def _hint(self, field: ui.input, hint: ui.label) -> None:
        text = (field.value or "").strip()
        if not text:
            hint.set_text("PLZ fünfstellig oder Ortsname")
            return
        place = resolve_place(text, self.s.model.db, self.s.params)
        if place.lat is not None:
            hint.set_text(f"Zuordnung: {place.label} ({place.art})")
        else:
            hint.set_text(f"Keine Koordinate: {place.art}. PLZ angeben oder Entfernung eintragen.")

    def _paste(self) -> None:
        with ui.column().classes("w-full gap-2 pt-2"):
            ui.label("Spalten wie im Blatt Input, Kopfzeile optional:").classes("tk-help")
            with ui.element("div").classes("tk-schema w-full"):
                for col, name in SCHEMA:
                    ui.html(f"<b>{col}</b>{name}")
            self.paste_area = (
                ui.textarea("Aus Excel einfügen").props("outlined dense rows=5").classes("w-full")
            )
            self.paste_mode = ui.toggle({"append": "Anhängen", "replace": "Ersetzen"}, value="append").props(
                "dense no-caps unelevated toggle-color=primary"
            )
            ui.button("Übernehmen", on_click=self.add_from_paste).props(
                "unelevated no-caps color=primary"
            ).classes("tk-cta self-start")
            ui.upload(label="CSV oder XLSX hochladen", auto_upload=True, on_upload=self.upload).props(
                'accept=".csv,.txt,.xlsx" flat bordered'
            ).classes("w-full")

    def _param_section(self) -> None:
        base = self.s.base.model.params
        current = self.s.params
        self.param_status, body = components.section(
            2, "Parameter", "Parameter anpassen", "Standardwerte aus Assumptions. Jede Änderung rechnet sofort "
            "neu; Quelle je Wert über den Mauszeiger auf der Beschriftung.", tone="lavender", anchor="schritt-2",
            delay=180,
        )  # fmt: skip
        with body:
            ui.button("Zurücksetzen", on_click=self.reset_params).props("flat dense no-caps").classes(
                "tk-link self-start"
            )
            for group, fields in PARAM_GROUPS:
                ui.label(group).classes("tk-group")
                with ui.element("div").classes("tk-grid-3"):
                    for field, step, help_text in fields:
                        meta = base.meta[field]
                        unit = fmt.display_unit(meta.unit)
                        box, num, hint = components.number_field(
                            meta.name, unit, "", self._tooltip(field),
                            value=fmt.to_display(getattr(current, field), meta.unit), step=step,
                            minimum=MIN_VALUE.get(field, 0.0), maximum=100.0 if unit == "%" else None,
                            on_change=lambda e, f=field: self.set_param(f, e.value), field_id=meta.id,
                        )  # fmt: skip
                        num.props("debounce=400")
                        self.param_fields[field] = (
                            box,
                            num,
                            hint,
                            help_text.format(a06=_num(base.a06_max_tage)),
                        )
                    if group.startswith("Bahn"):
                        self._traction()
                if group == "Distanz":
                    self._road()
            self.param_note = ui.label("").classes("tk-note")
            self.param_note.set_visibility(False)

    def _tooltip(self, field: str) -> str:
        meta = self.s.base.model.params.meta[field]
        return f"{meta.id}: {meta.name}\nTyp: {meta.typ}\nQuelle: {meta.quelle}\nZelle: {meta.zelle}"

    def _traction(self) -> None:
        meta = self.s.base.model.params.meta["a04_traktion"]
        with ui.element("div").classes("tk-field"):
            with ui.row().classes("tk-field-label gap-0 no-wrap items-baseline"):
                ui.label(meta.id).classes("tk-id")
                ui.label(f"{meta.name} (bestimmt C01)")
                ui.tooltip(self._tooltip("a04_traktion")).style(
                    "max-width:360px;font-size:12px;white-space:pre-line"
                )
            self.traction = (
                ui.select(
                    {"elektrisch": "elektrisch", "Diesel": "Diesel"},
                    value=self.s.params.a04_traktion,
                    on_change=lambda e: self.set_param("a04_traktion", e.value),
                )
                .props(f'dense outlined aria-label="{meta.name}"')
                .classes("w-full")
            )
            self.c01_label = ui.label("").classes("tk-help")

    def _road(self) -> None:
        with ui.column().classes("w-full gap-1"):
            self.road_switch = ui.switch(
                "Distanz aus Straßenrouten (ORS) statt Luftlinie × I01",
                value=self.s.road_km,
                on_change=lambda e: self.set_road_km(bool(e.value)),
            ).props("dense color=primary")
            self.road_hint = ui.label("").classes("tk-help")
            ui.button(
                "Relationstabelle herunterladen",
                on_click=lambda: (
                    ui.download.content(
                        relation_table_csv(self.s.result, route_cache()).encode("utf-8-sig"),
                        "relationstabelle_plz_orte.csv",
                    )
                    if self.s.result is not None
                    else None
                ),
            ).props("flat dense no-caps color=primary").classes("self-start").tooltip(
                "Straßen-km zum Einfügen in PLZ_Orte R:T der Excel"
            )

    # ---------- Erweiterungspunkte (Agent S15, Export S16) ----------
    def build_agent_input(self, box: ui.column) -> None:
        from tk.ui.agent_panel import build_agent_input

        build_agent_input(self, box)

    def build_export(self, box: ui.row) -> None:
        from tk.ui.export_panel import build_export

        build_export(self, box)

    # ---------- Aktionen ----------
    def set_scenario(self, key: str) -> None:
        self.s.scenario = key
        self.refresh_all()

    def set_param(self, field: str, value: Any) -> None:
        if value is None or value == "":
            return
        if field in self.param_fields:
            num = self.param_fields[field][1]
            if not num.min <= value <= num.max:
                return
            value = fmt.from_display(value, self.s.base.model.params.meta[field].unit)
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
        for field, (_, num, _, _) in self.param_fields.items():
            num.set_value(fmt.to_display(getattr(p, field), p.meta[field].unit))
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
        self._param_state()
        self.refresh_road_toggle()
        self._kpis(r)
        self.map.update(r, self.s.scenario)
        self._summary(r)

    def _param_state(self) -> None:
        p, base = self.s.params, self.s.base.model.params
        self.c01_label.set_text(f"Bahn-Emissionsfaktor C01: {fmt.number(p.c01_bahn_faktor, 1)} g/tkm")
        for field, (box, _, hint, help_text) in self.param_fields.items():
            meta = base.meta[field]
            default = fmt.with_unit(
                fmt.to_display(getattr(base, field), meta.unit), fmt.display_unit(meta.unit), 2
            )
            default = default.replace(",00", "")
            changed = field in self.s.changes
            if changed:
                box.classes(add="tk-field--changed")
            else:
                box.classes(remove="tk-field--changed")
            hint.set_text(f"Geändert, Standard: {default}" if changed else f"{help_text} Standard: {default}")

        def shown(field: str, value: Any) -> str:
            if isinstance(value, str):
                return value
            unit = base.meta[field].unit
            return f"{_num(fmt.to_display(value, unit))}{fmt.NARROW}{fmt.display_unit(unit)}"

        notes = [f"{base.meta[f].id} = {shown(f, v)}" for f, v in self.s.changes.items()]
        n = len(notes)
        self.param_status.set_text(
            "Standardwerte aus Assumptions"
            if n == 0
            else f"{n} Wert geändert"
            if n == 1
            else f"{n} Werte geändert"
        )
        self.param_note.set_text("Abweichend von Assumptions: " + ", ".join(notes))
        self.param_note.set_visibility(bool(notes))

    def _kpis(self, r: Result) -> None:
        plan = self.s.scenario != "Ist"
        k, ist = r.kpis[self.s.scenario], r.kpis["Ist"]
        if r.n_valid == 0:
            self.hero_title.set_text("Noch keine Sendungen")
            self.hero_sub.set_text(
                "Sendungen erfassen oder Beispieldaten laden, dann rechnet die Seite sofort."
            )
        elif plan:
            self.hero_title.set_text(f"{fmt.percent(k.delta_co2_fzgkm)} CO₂e")
            self.hero_sub.set_text(
                f"{SCENARIO_LABEL[self.s.scenario]} gegen Einzelversand: {fmt.with_unit(k.co2_fzgkm_kg, 'kg')} statt "
                f"{fmt.with_unit(ist.co2_fzgkm_kg, 'kg')}, Kosten {fmt.percent(k.delta_kosten)}, "
                f"Servicegrad {fmt.percent(k.servicegrad, 1, False)}."
            )
        else:
            self.hero_title.set_text(f"{fmt.with_unit(ist.co2_fzgkm_kg, 'kg')} CO₂e")
            self.hero_sub.set_text(
                f"Ist: {fmt.number(r.n_valid)} Sendungen einzeln gefahren. M2 oder M3 wählen für den Vergleich."
            )
        nav_kpis(self.nav_kpi_box, r, self.s.scenario)
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
                    on_explain=functools.partial(self.open_explain, key),
                )  # fmt: skip
            components.kpi_stat(
                "Servicegrad", fmt.percent(k.servicegrad, 1, False), None,
                f"Bahn {fmt.percent(k.bahn_sendungen / r.n_valid, 1, False)}, {fmt.number(k.bahn_sendungen)} Sendungen",
                "lavender", on_explain=lambda: self.open_explain("servicegrad"),
            )  # fmt: skip

    def _summary(self, r: Result) -> None:
        self.summary_box.clear()
        passed = sum(1 for c in r.checks if c.status == "OK")
        with self.summary_box, ui.row().classes("items-center gap-4"):
            ui.label(
                f"{fmt.number(len(r.rows))} Sendungen, {fmt.number(len(r.tours))} Touren, "
                f"{passed} von {len(r.checks)} Prüfungen bestanden. Tabellen, Szenarienvergleich, "
                "Erklärungen und Prüfungen auf der Seite Analyse."
            )
            if passed < len(r.checks):
                ui.link("Offene Prüfungen ansehen", "/analyse?tab=pruefungen").classes("tk-link")

    def open_explain(self, key: str) -> None:
        r = self.s.result
        if r is None:
            return
        with ui.dialog() as dialog, ui.card().classes("tk-card").style("max-width:760px"):
            explain_content(key, self.s, r)
            ui.button("Schließen", on_click=dialog.close).props("flat no-caps color=primary")
        dialog.open()


@ui.page("/")
async def index(tour: int | None = None) -> None:
    base = base_data()
    if base is None:
        missing_workbook()
        return
    session = session_for(app.storage.browser["id"], base)
    page = Page(session)
    app.storage.client["page"] = page
    page.build(tour)


@ui.page("/analyse")
async def analyse(tab: str | None = None) -> None:
    base = base_data()
    if base is None:
        missing_workbook()
        return
    AnalysisPage(session_for(app.storage.browser["id"], base)).build(tab)


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
        # Signs the browser id cookie only; sessions live in memory, so a fresh secret per start is enough.
        storage_secret=os.environ.get("TK_STORAGE_SECRET") or secrets.token_hex(16),
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
