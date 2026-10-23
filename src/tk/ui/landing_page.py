"""Startseite: Marke, Nutzen, Kennzahlen der Beispieldaten, Ablauf, Funktionen, Methodik.

Alle Zahlen kommen aus der Rechnung der Excel-Beispieldaten (``BaseData.result``), nichts ist
hartkodiert. Die Netzansicht ist die Knoten-Kanten-Grafik der Ergebnisseite ohne Kartenkacheln.
"""

from __future__ import annotations

from nicegui import run, ui

from tk.ui import components
from tk.ui import format as fmt
from tk.ui.layout import BRAND, end, nav
from tk.ui.map_view import legend, svg_network
from tk.ui.state import Session
from tk.ui.theme import apply_theme

STEPS = (
    ("Sendungen erfassen", "Formular, Einfügen aus Excel, CSV oder XLSX hochladen oder in eigenen Worten "
     "beschreiben. Jede Zeile wird sofort geprüft.", "Sendungen erfassen", "/rechnen#schritt-1"),
    ("Parameter prüfen", "Bahn-Mindestdistanz, Umwegzuschlag, Kostentoleranz und Straßenfaktor. Jeder Wert "
     "mit Standard, Quelle und Zelle aus Assumptions.", "Parameter ansehen", "/rechnen#schritt-2"),
    ("Ergebnis vergleichen", "Ist, M2 und M3 nebeneinander: Karte, Touren und Kennzahlen gegen den "
     "Einzelversand, mit Begründung je Relation.", "Ergebnis öffnen", "/ergebnis?tab=karte"),
)  # fmt: skip
"""Ablauf: Titel, Text, Linktext, Ziel."""

FEATURES = (
    ("M2 Bündelung", "Next-Fit je Tag und Startort fasst Sendungen zu Sammeltouren. Es fährt das kleinste "
     "Fahrzeug, in das Gewicht und Paletten passen.", "Touren ansehen", "/ergebnis?tab=touren"),
    ("M3 Bahnverlagerung", "Ab der Mindestdistanz A01 prüft M3 die Bahn mit Vor- und Nachlauf. Verlagert wird "
     "nur, was Laufzeit und Kostengrenze einhält.", "Szenarien vergleichen", "/ergebnis?tab=szenarien"),
    ("Karte und Routenvergleich", "Vorher und Nachher auf einer Karte, je Relation mit Fahrzeugwahl. Eigene "
     "Bündel nach Tag oder Zeitfenster bilden.", "Karte öffnen", "/ergebnis?tab=karte"),
    ("Nachvollziehbar", "Jede Kennzahl mit Formel, Annahmen, Datenquelle und Systemgrenze. Prüfungen "
     "gleichen jede Zahl mit der Excel v11 ab.", "Prüfungen ansehen", "/info?tab=pruefungen"),
    ("Sensitivität", "Das Morris-Screening zeigt, welche Annahme CO₂e, Kosten und Servicegrad am "
     "stärksten bewegt.", "Sensitivität ansehen", "/info?tab=sensitivitaet"),
    ("Freitext-Assistent", "Sendungen in eigenen Worten beschreiben. Der Assistent legt sie an, gerechnet "
     "wird ausschließlich im Rechenkern.", "Assistent nutzen", "/rechnen#schritt-1"),
)  # fmt: skip
"""Funktionen: Titel, Text, Linktext, Ziel."""


class LandingPage:
    """Eine Sitzung der Startseite."""

    def __init__(self, session: Session) -> None:
        self.s = session
        self.side = "nachher"

    def build(self) -> None:
        apply_theme()
        nav("/")
        r = self.s.base.result
        with ui.column().classes("tk-page w-full"):
            self._hero()
            if r.n_valid:
                self._kpis()
            self._band_steps()
            self._band_features()
            self._band_method()
            self._final()
            end(self.s)

    # ---------- Abschnitte ----------
    def _hero(self) -> None:
        r = self.s.base.result
        with ui.element("section").classes("tk-land-hero"):
            with ui.element("div").classes("tk-reveal"):
                ui.label(f"TK. {BRAND} | Transportoptimierung").classes("tk-kicker")
                with ui.element("h1").classes("tk-land-title").style("margin-top:24px"):
                    ui.label("Weniger Fahrten,").classes("block")
                    ui.label("weniger ").classes("inline")
                    ui.label("Emissionen").classes("inline tk-serif")
                    ui.label(".").classes("inline tk-dot")
                ui.label(
                    f"{BRAND} bündelt Sendungen zu Sammeltouren, prüft die Verlagerung auf die Bahn und zeigt "
                    "für jedes Szenario CO₂e, Kosten und Servicegrad. Jede Zahl mit Formel, Annahme und Quelle."
                ).classes("tk-land-sub")
                with ui.element("div").classes("tk-land-actions"):
                    self.sample_btn = (
                        ui.button("Mit Beispieldaten starten", on_click=self.start_sample)
                        .props("unelevated no-caps color=primary")
                        .classes("tk-cta tk-btn-lg")
                    )
                    ui.button(
                        "Eigene Sendungen erfassen", on_click=lambda: ui.navigate.to("/rechnen#schritt-1")
                    ).props("outline no-caps color=primary").classes("tk-btn-lg")
                ui.label(
                    f"Beispieldaten: {fmt.number(r.n_valid)} Sendungen aus der Excel-Mappe v11, ohne Anmeldung."
                ).classes("tk-land-note")
            with ui.element("div").classes("tk-land-visual tk-reveal").style("--delay:160ms"):
                with ui.element("div").classes("tk-land-visual-head"):
                    ui.label("Netz der Beispieldaten").classes("tk-label")
                    with ui.element("div").classes("tk-segment").props('role="group" aria-label="Ansicht"'):
                        self.side_buttons = {}
                        for key, label in (("vorher", "Vorher: Ist"), ("nachher", "Nachher: M3")):
                            btn = ui.element("button").props(
                                f'type="button" aria-pressed="{str(key == self.side).lower()}"'
                            )
                            with btn:
                                ui.label(label)
                            btn.on("click", lambda _e, k=key: self.set_side(k))
                            self.side_buttons[key] = btn
                self.svg = ui.html("").classes("tk-land-svg w-full")
                self.legend_box = ui.element("div")
                self._render_network()

    def _kpis(self) -> None:
        r = self.s.base.result
        k, ist = r.kpis["M3"], r.kpis["Ist"]
        with ui.element("div").classes("tk-stats tk-inview"):
            components.kpi_stat(
                "CO₂e (Fzg-km)", fmt.with_unit(k.co2_fzgkm_kg, "kg"), k.delta_co2_fzgkm,
                f"Ist: {fmt.with_unit(ist.co2_fzgkm_kg, 'kg')}", "mint",
            )  # fmt: skip
            components.kpi_stat(
                "Kosten", fmt.with_unit(k.kosten_eur, "€"), k.delta_kosten,
                f"Ist: {fmt.with_unit(ist.kosten_eur, '€')}", "sky",
            )  # fmt: skip
            components.kpi_stat(
                "Fahrzeug-km (Lkw)", fmt.with_unit(k.lkw_km, "km"), k.delta_lkw_km,
                f"Ist: {fmt.with_unit(ist.lkw_km, 'km')}", "peach",
            )  # fmt: skip
            components.kpi_stat(
                "Servicegrad", fmt.percent(k.servicegrad, 1, False), None,
                f"{fmt.number(k.bahn_sendungen)} Sendungen per Bahn", "lavender",
            )  # fmt: skip
        ui.label("Szenario M3 Bahn + Bündelung gegen Einzelversand, Beispieldaten der Excel v11.").classes(
            "tk-land-note"
        )

    def _band_head(self, kicker: str, title: str, serif: str, lead: str) -> None:
        with ui.element("div").classes("tk-band-head"):
            with ui.element("div"):
                ui.label(kicker).classes("tk-kicker")
                with ui.element("h2").classes("tk-band-title").style("margin-top:16px"):
                    ui.label(title).classes("inline")
                    ui.label(serif).classes("inline tk-serif")
                    ui.label(".").classes("inline tk-dot")
            ui.label(lead).classes("tk-band-lead self-end")

    def _band_steps(self) -> None:
        with ui.element("section").classes("tk-band tk-inview").props('id="ablauf"'):
            self._band_head(
                "Ablauf", "In drei Schritten zum ", "Plan",
                "Ohne Vorwissen startklar: Daten erfassen, Annahmen prüfen, Szenarien vergleichen. "
                "Die Beispieldaten sind bereits geladen.",
            )  # fmt: skip
            with ui.element("div").classes("tk-cols"):
                for n, (title, text, link, href) in enumerate(STEPS, start=1):
                    with ui.element("div").classes("tk-col tk-inview").style(f"--delay:{n * 80}ms"):
                        ui.label(f"{n:02d}").classes("tk-col-no")
                        ui.label(title).classes("tk-col-title")
                        ui.label(text).classes("tk-col-text")
                        ui.link(link, href).classes("tk-link")

    def _band_features(self) -> None:
        with ui.element("section").classes("tk-band tk-inview").props('id="funktionen"'):
            self._band_head(
                "Funktionen", f"Was {BRAND} ", "rechnet",
                "Zwei Maßnahmen gegen den Einzelversand, gerechnet wie in der Excel v11. Abweichungen zur "
                "Excel gelten als Fehler und werden geprüft.",
            )  # fmt: skip
            with ui.element("div").classes("tk-cols"):
                for n, (title, text, link, href) in enumerate(FEATURES):
                    with ui.element("div").classes("tk-col tk-inview").style(f"--delay:{(n % 3) * 80}ms"):
                        ui.label(title).classes("tk-col-title")
                        ui.label(text).classes("tk-col-text")
                        ui.link(link, href).classes("tk-link")

    def _band_method(self) -> None:
        with ui.element("section").classes("tk-band tk-inview").props('id="methodik"'):
            self._band_head(
                "Methodik", "Normen statt ", "Schätzung",
                "Emissionen nach GLEC Framework, ISO 14083 und DIN EN 16258. Distanz aus Eingabe, "
                "Relationstabelle oder Luftlinie × Straßenfaktor I01. Fehlende Daten erscheinen als nicht "
                "berechenbar, nie als geschätzter Wert.",
            )  # fmt: skip
            ui.link("Annahmen und Quellen ansehen", "/info?tab=annahmen").classes("tk-link")

    def _final(self) -> None:
        with ui.element("section").classes("tk-final tk-inview"):
            with ui.element("h2").classes("tk-land-title").style("font-size:clamp(40px, 5vw, 80px)"):
                ui.label("Bereit für den ersten ").classes("inline")
                ui.label("Plan").classes("inline tk-serif")
                ui.label("?").classes("inline")
            ui.button("Jetzt optimieren", on_click=lambda: ui.navigate.to("/rechnen")).props(
                "unelevated no-caps color=primary"
            ).classes("tk-cta tk-btn-lg")

    # ---------- Aktionen ----------
    def set_side(self, side: str) -> None:
        self.side = side
        for key, btn in self.side_buttons.items():
            btn.props(f'aria-pressed="{str(key == side).lower()}"')
        self._render_network()

    def _render_network(self) -> None:
        r = self.s.base.result
        self.svg.set_content(svg_network(r, "M3", self.side, width=640, height=480, color_by="szenario"))
        self.legend_box.clear()
        with self.legend_box:
            legend("Ist" if self.side == "vorher" else "M3", "szenario")

    async def start_sample(self) -> None:
        """Beispieldaten in die Sitzung laden, rechnen und das Ergebnis mit der Karte öffnen."""
        self.sample_btn.classes(add="is-loading").props("aria-busy=true")
        self.s.shipments = list(self.s.base.shipments)
        await run.io_bound(self.s.recalculate)
        ui.navigate.to("/ergebnis?tab=karte")
