"""Seite Info: Erklärung der Kennzahlen, Annahmen und Quellen, Prüfungen, Sensitivität, Agent-Spur.

Zeigt denselben Stand wie Rechnen und Ergebnis (Sitzung je Browser). Tab per
``?tab=erklaerung|annahmen|pruefungen|sensitivitaet|agent``, Kennzahl per ``?k=``.
"""

from __future__ import annotations

from typing import Any

from nicegui import run, ui

from tk.excelfn import general_text
from tk.explain import SPEC, explain
from tk.models import Result
from tk.scenarios import calculate, parse_change, sensitivity_row, with_changes
from tk.ui import components
from tk.ui import format as fmt
from tk.ui.agent_panel import render_trace
from tk.ui.layout import end, hero, nav
from tk.ui.state import Session, reference, snapshot
from tk.ui.theme import apply_theme

TABS = {
    "erklaerung": "Erklärung",
    "annahmen": "Annahmen und Quellen",
    "pruefungen": "Prüfungen",
    "sensitivitaet": "Sensitivität",
    "agent": "Agent-Spur",
}
"""Tabs der Info-Seite; der Schlüssel ist der Wert für ``?tab=``."""


class InfoPage:
    """Eine Sitzung der Seite Info."""

    def __init__(self, session: Session) -> None:
        self.s = session
        self.explain_key = "co2_fzgkm"

    def build(self, tab: str | None, key: str | None) -> None:
        apply_theme()
        nav("/info")
        if key in SPEC:
            self.explain_key = key
        with ui.column().classes("tk-page w-full"):
            title, _, _, sub, _ = hero("Info", "gerechnet")
            title.set_text("So wird ")
            sub.set_text(
                "Formeln, Annahmen mit Quelle, Prüfungen gegen die Excel v11 und die Werkzeugaufrufe des "
                "Assistenten zum aktuellen Stand."
            )
            with ui.element("div").classes("w-full tk-reveal").style("--delay:100ms"):
                with ui.tabs().props("dense no-caps align=left").classes("tk-pilltabs") as tabs:
                    handles = {k: ui.tab(k, label) for k, label in TABS.items()}
                start = handles.get(tab or "", handles["erklaerung"])
                with (
                    ui.tab_panels(tabs, value=start).classes("w-full bg-transparent").props("animated=false")
                ):
                    with ui.tab_panel(handles["erklaerung"]):
                        self.explain_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(handles["annahmen"]):
                        self.assumption_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(handles["pruefungen"]):
                        self.check_box = ui.column().classes("w-full gap-2")
                    with ui.tab_panel(handles["sensitivitaet"]):
                        self.sens_box = ui.column().classes("w-full gap-3")
                    with ui.tab_panel(handles["agent"]):
                        self.trace_box = ui.column().classes("w-full gap-2")
            end(self.s)
        self.refresh_all()

    def refresh_all(self) -> None:
        r = self.s.result
        if r is None:
            return
        self._explanation(r)
        self._assumptions()
        self._checks(r)
        self.sens_box.clear()
        with self.sens_box:
            self._sensitivity()
        render_trace(self.s, self.trace_box)

    def _assumptions(self) -> None:
        """Alle Parameter aus Assumptions mit aktuellem Wert, Einheit, Typ, Quelle und Zelle."""
        p = self.s.params
        rows: list[dict[str, Any]] = []
        for field, meta in p.meta.items():
            if "[" in field:
                name, idx = field[:-1].split("[")
                vehicle = p.vehicles[int(idx)]
                wert: Any = getattr(vehicle, name)
                label = f"{meta.name} ({vehicle.name})"
            else:
                wert, label = getattr(p, field), meta.name
            rows.append({
                "id": meta.id, "name": label,
                "wert": wert if isinstance(wert, str) else general_text(wert).replace(".", ","),
                "einheit": meta.unit, "typ": meta.typ, "quelle": meta.quelle, "zelle": meta.zelle,
                "key": field,
            })  # fmt: skip
        self.assumption_box.clear()
        with self.assumption_box:
            changed = len(self.s.changes)
            ui.label(
                "Werte der aktuellen Rechnung. Abweichend von Assumptions: "
                + (f"{changed} Wert(e), geändert auf der Seite Rechnen." if changed else "keine.")
            ).classes("tk-label")
            ui.table(
                columns=[{"name": c, "label": lab, "field": c, "align": "left"} for c, lab in
                         [("id", "ID"), ("name", "Parameter"), ("wert", "Wert"), ("einheit", "Einheit"),
                          ("typ", "Typ"), ("quelle", "Quelle"), ("zelle", "Zelle")]],
                rows=rows, row_key="key", pagination={"rowsPerPage": 25},
            ).props("dense flat wrap-cells").classes("w-full")  # fmt: skip

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

    def _sensitivity(self) -> None:
        snap = snapshot()
        ui.label("Sensitivität").classes("tk-section")
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
