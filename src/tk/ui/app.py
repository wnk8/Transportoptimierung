"""Seite Rechnen: 01 Sendungen, 02 Parameter, schwebende Leiste mit "Berechnen".

Ergebnisse und Karte stehen auf ``/ergebnis``, Erklärungen und Prüfungen auf ``/info``. Alle Zahlen
kommen aus ``tk`` (Rechenkern). Beim Start sind die Beispieldaten der Excel-Mappe geladen.
Start: ``make run`` (http://127.0.0.1:8080).
"""

from __future__ import annotations

import datetime as dt
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
from tk.ui.info_page import InfoPage
from tk.ui.layout import SCENARIO_LABEL, end, hero, missing_workbook, nav
from tk.ui.map_area import route_cache
from tk.ui.preview import preview_page
from tk.ui.results_page import ResultsPage
from tk.ui.state import Session, base_data, session_for
from tk.ui.theme import apply_theme

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
    """Eine Sitzung der Seite Rechnen."""

    def __init__(self, session: Session) -> None:
        self.s = session
        self.busy = False
        self.param_fields: dict[str, tuple[ui.element, ui.number, ui.label]] = {}

    # ---------- Aufbau ----------
    def build(self) -> None:
        apply_theme()
        nav("/")
        with ui.column().classes("tk-page tk-page-dock w-full"):
            title, _, _, sub, _ = hero("Rechnen", "rechnen")
            title.set_text("Transport ")
            sub.set_text("Sendungen erfassen, Parameter prüfen, berechnen.")
            self._input_section()
            self._param_section()
            end(self.s)
        self._dock()
        self.refresh_all()

    def _dock(self) -> None:
        with ui.element("div").classes("tk-dock").props('role="region" aria-label="Berechnen"'):
            self.dock_info = ui.element("div").classes("tk-dock-info").props('aria-live="polite"')
            self.progress = ui.element("div").classes("tk-progress").style("width:64px")
            with self.progress:
                ui.element("div")
            self.progress.set_visibility(False)
            ui.button("Berechnen", on_click=self.go_results).props(
                "unelevated no-caps color=primary"
            ).classes("tk-cta")

    async def go_results(self) -> None:
        """Offene Neuberechnung abwarten, dann zum Ergebnis mit der Karte."""
        if self.busy:
            await self.recalculate()
        ui.navigate.to("/ergebnis?tab=karte")

    def _input_section(self) -> None:
        self.count_label, body = components.section(1, "Sendungen", anchor="schritt-1", delay=120)
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
        self.param_status, body = components.section(2, "Parameter", anchor="schritt-2", delay=180)
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
                            meta.name, unit, "", self._tooltip(field, help_text.format(a06=_num(base.a06_max_tage))),
                            value=fmt.to_display(getattr(current, field), meta.unit), step=step,
                            minimum=MIN_VALUE.get(field, 0.0), maximum=100.0 if unit == "%" else None,
                            on_change=lambda e, f=field: self.set_param(f, e.value), field_id=meta.id,
                        )  # fmt: skip
                        num.props("debounce=400")
                        self.param_fields[field] = (box, num, hint)
                    if group.startswith("Bahn"):
                        self._traction()
                if group == "Distanz":
                    self._road()
            self.param_note = ui.label("").classes("tk-note")
            self.param_note.set_visibility(False)

    def _tooltip(self, field: str, effect: str = "") -> str:
        meta = self.s.base.model.params.meta[field]
        lead = f"{meta.id}: {meta.name}" + (f"\n{effect}" if effect else "")
        return f"{lead}\nTyp: {meta.typ}\nQuelle: {meta.quelle}\nZelle: {meta.zelle}"

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
        for field, (_, num, _) in self.param_fields.items():
            num.set_value(fmt.to_display(getattr(p, field), p.meta[field].unit))
        self.traction.set_value(p.a04_traktion)
        ui.timer(0, self.recalculate, once=True)

    async def recalculate(self) -> None:
        self.busy = True
        self.progress.set_visibility(True)
        try:
            await run.io_bound(self.s.recalculate)
        except Exception as exc:
            self._message(
                "error", f"Rechnung nicht möglich: {exc}", "Parameter zurücksetzen oder Eingabe prüfen."
            )
        finally:
            self.busy = False
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
        self.count_label.set_text(
            f"{fmt.number(len(self.s.shipments))} Zeilen, davon {fmt.number(r.n_valid)} gültig"
        )
        self._param_state()
        self.refresh_road_toggle()
        self._dock_state(r)

    def _param_state(self) -> None:
        p, base = self.s.params, self.s.base.model.params
        self.c01_label.set_text(f"Bahn-Emissionsfaktor C01: {fmt.number(p.c01_bahn_faktor, 1)} g/tkm")
        for field, (box, _, hint) in self.param_fields.items():
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
            hint.set_text(f"Geändert, Standard: {default}" if changed else f"Standard: {default}")

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

    def _dock_state(self, r: Result) -> None:
        """Schwebende Leiste: Sendungen, Szenario und CO₂e-Wirkung der aktuellen Eingabe."""
        k = r.kpis[self.s.scenario]
        parts = [f"{fmt.number(r.n_valid)} Sendungen", SCENARIO_LABEL[self.s.scenario]]
        if r.n_valid and self.s.scenario != "Ist":
            parts.append(f"CO₂e {fmt.percent(k.delta_co2_fzgkm)}")
        elif r.n_valid:
            parts.append(f"CO₂e {fmt.with_unit(k.co2_fzgkm_kg, 'kg')}")
        self.dock_info.clear()
        with self.dock_info:
            for n, text in enumerate(parts):
                if n:
                    ui.label("/").classes("tk-sep").props('aria-hidden="true"')
                ui.label(text).classes("tk-num" if n == len(parts) - 1 else "")


@ui.page("/")
async def index() -> None:
    base = base_data()
    if base is None:
        missing_workbook()
        return
    session = session_for(app.storage.browser["id"], base)
    page = Page(session)
    app.storage.client["page"] = page
    page.build()


@ui.page("/ergebnis")
async def ergebnis(tab: str | None = None, tour: int | None = None) -> None:
    base = base_data()
    if base is None:
        missing_workbook()
        return
    ResultsPage(session_for(app.storage.browser["id"], base)).build(tab, tour)


@ui.page("/info")
async def info(tab: str | None = None, k: str | None = None) -> None:
    base = base_data()
    if base is None:
        missing_workbook()
        return
    InfoPage(session_for(app.storage.browser["id"], base)).build(tab, k)


@ui.page("/analyse")
def analyse() -> None:
    """Frühere Seite Analyse: leitet auf Ergebnis weiter (Links in README und Präsentation)."""
    ui.navigate.to("/ergebnis")


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
