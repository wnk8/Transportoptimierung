"""Vorschauseite des Design-Systems: alle Komponenten und Zustände.

Zahlen stammen aus dem Rechenkern mit den Beispieldaten der Excel-Mappe. Fehlt die Mappe,
zeigt die Seite den leeren Zustand statt erfundener Werte.
"""

from __future__ import annotations

from nicegui import ui

from tk.ui import components
from tk.ui import format as fmt
from tk.ui.layout import hero, nav
from tk.ui.state import base_data
from tk.ui.theme import MAP_LINES, STATUS_STYLES, TOKENS, ScenarioToggle, apply_theme, status_chip


def preview_page() -> None:
    apply_theme()
    with ui.column().classes("tk-page w-full"):
        ui.label("Design-System").classes("tk-title")
        ui.label("Farbtokens, Schrift, Komponenten und Zustände der Oberfläche.").classes("tk-label")

        ui.label("Farbtokens").classes("tk-section")
        with ui.row().classes("gap-2 flex-wrap"):
            for name, value in TOKENS.items():
                with (
                    ui.element("div").classes("tk-card flex flex-col gap-1").style("width:150px;padding:8px")
                ):
                    ui.element("div").style(
                        f"height:32px;border-radius:8px;background:{value};border:1px solid var(--line)"
                    )
                    ui.label(f"--{name}").classes("tk-label")
                    ui.label(value).classes("tk-num").style("font-size:12px")

        ui.label("Kartenlinien").classes("tk-section")
        with ui.row().classes("gap-4"):
            labels = {
                "ist": "Ist, Einzelversand",
                "lkw": "Plan, Lkw",
                "bahn": "Plan, Bahn",
                "luft": "Luftlinie",
                "strasse": "Straßenroute",
                "auswahl": "Auswahl",
            }
            for key, (color, dash) in MAP_LINES.items():
                with ui.row().classes("items-center gap-2"):
                    ui.html(
                        f'<svg width="48" height="10" aria-hidden="true"><line x1="0" y1="5" x2="48" y2="5" '
                        f'stroke="{color}" stroke-width="4" stroke-dasharray="{dash}"/></svg>'
                    )
                    ui.label(labels[key])

        ui.label("Schrift").classes("tk-section")
        with ui.element("div").classes("tk-card flex flex-col gap-2"):
            ui.label("Seitentitel 20 px / 600").classes("tk-title")
            ui.label("Abschnitt 14 px / 600").classes("tk-section")
            ui.label("Fließtext 14 px / 400")
            ui.label("Beschriftung 12 px / 500").classes("tk-label")
            ui.label("306.924 kg").classes("tk-kpi")

        ui.label("Szenario-Umschalter und Status").classes("tk-section")
        with ui.row().classes("items-center gap-4"):
            choice = ui.label("Auswahl: M3").classes("tk-label")
            ScenarioToggle("M3", lambda k: choice.set_text(f"Auswahl: {k}"))
            for status in STATUS_STYLES:
                status_chip(status)

        ui.label("Navigation, Headline und schwebende Leiste").classes("tk-section")
        nav("/")
        title, _, _, sub, _ = hero("Rechnen", "rechnen")
        title.set_text("Transport ")
        sub.set_text("Headline aus Geist mit kursivem Serif-Wort (Instrument Serif) und Akzentpunkt.")
        with (
            ui.element("div").classes("tk-dock").style("position:static;transform:none;align-self:flex-start")
        ):
            with ui.element("div").classes("tk-dock-info"):
                ui.label("Sendungen")
                ui.label("/").classes("tk-sep")
                ui.label("M3 Bahn + Bündelung")
            ui.button("Berechnen", on_click=lambda: None).props("unelevated no-caps color=primary").classes(
                "tk-cta"
            )

        ui.label("Zahlenfelder").classes("tk-section")
        with ui.element("div").classes("grid gap-4").style("grid-template-columns:repeat(3,minmax(0,1fr))"):
            with ui.element("div").classes("tk-card"):
                components.number_field(
                    "Bahn-Mindestdistanz", "km", "Standard: 500 km", "Tooltip mit Typ, Quelle und Zelle",
                    value=500, field_id="A01",
                )  # fmt: skip
            with ui.element("div").classes("tk-card"):
                box, _, _ = components.number_field(
                    "Umweg-Zuschlag", "%", "Geändert, Standard: 20 %", value=40, field_id="A10", maximum=100
                )
                box.classes("tk-field--changed")
            with ui.element("div").classes("tk-card"):
                _, num, _ = components.number_field("Gewicht (Pflicht)", "kg", "Bruttogewicht.", minimum=0)
                num.set_value(-5)
                num.validate()

        ui.label("Abschnitt und Kennzahlenreihe").classes("tk-section")
        sec_status, sec_body = components.section(1, "Sendungen")
        with sec_body:
            ui.button("Sendung hinzufügen", on_click=lambda: None).props(
                "unelevated no-caps color=primary"
            ).classes("tk-cta self-start")
        sample = base_data()
        if sample is not None:
            m3, ist = sample.result.kpis["M3"], sample.result.kpis["Ist"]
            sec_status.set_text(f"{fmt.number(sample.result.n_valid)} gültige Zeilen")
            with ui.element("div").classes("tk-stats"):
                components.kpi_stat(
                    "CO₂e (Fzg-km)", fmt.with_unit(m3.co2_fzgkm_kg, "kg"), m3.delta_co2_fzgkm,
                    f"Ist: {fmt.with_unit(ist.co2_fzgkm_kg, 'kg')}", "mint",
                )  # fmt: skip
                components.kpi_stat("Kosten", fmt.with_unit(m3.kosten_eur, "€"), m3.delta_kosten, None, "sky")
                components.kpi_stat(
                    "Fahrzeug-km (Lkw)", fmt.with_unit(m3.lkw_km, "km"), m3.delta_lkw_km, None, "peach"
                )
                components.kpi_stat(
                    "Servicegrad", fmt.percent(m3.servicegrad, 1, False), None, None, "lavender"
                )

        ui.label("Kennzahlenkacheln").classes("tk-section")
        data = base_data()
        if data is None:
            components.empty_state(
                "Keine Beispieldaten: Die Excel-Mappe liegt nicht in data/excel.",
            )
        else:
            k = data.result.kpis
            for tones in ((None, None, None, None), ("mint", "sky", "peach", "lavender")):
                with ui.element("div").classes("tk-kpi-grid w-full"):
                    components.kpi_tile(
                        "CO₂e (Fzg-km)", k["M3"].co2_fzgkm_kg, k["Ist"].co2_fzgkm_kg, k["M3"].delta_co2_fzgkm, "kg",
                        tone=tones[0],
                    )  # fmt: skip
                    components.kpi_tile(
                        "Kosten",
                        k["M3"].kosten_eur,
                        k["Ist"].kosten_eur,
                        k["M3"].delta_kosten,
                        "€",
                        tone=tones[1],
                    )
                    components.kpi_tile(
                        "Lkw-km", k["M3"].lkw_km, k["Ist"].lkw_km, k["M3"].delta_lkw_km, "km", tone=tones[2]
                    )
                    components.kpi_tile(
                        "Servicegrad", k["M3"].servicegrad, k["Ist"].servicegrad, None, "%",
                        extra=f"Bahn: {k['M3'].bahn_sendungen} Sendungen", tone=tones[3],
                    )  # fmt: skip

        ui.label("Zustände").classes("tk-section")
        with ui.element("div").classes("grid gap-4").style("grid-template-columns:repeat(2,minmax(0,1fr))"):
            components.empty_state("Noch keine Sendungen.", "Beispieldaten laden", lambda: None)
            components.loading_state("Rechnet Szenarien")
            components.error_state(
                "Zeile 3: Ziel nicht gefunden",
                "PLZ des Ziels eintragen oder Entfernung in km angeben.",
            )
            components.success_state("2.266 Sendungen gerechnet, alle Prüfungen bestanden.")
            components.note("A01 Bahn-Mindestdistanz ist eine Setzung der Gruppe ohne Quelle.")
