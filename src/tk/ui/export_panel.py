"""Export-Schaltflächen (CSV, XLSX im Input-Schema)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from tk.export import to_csv, to_xlsx_bytes

if TYPE_CHECKING:
    from tk.ui.app import Page


def build_export(page: Page, box: ui.row) -> None:
    with box:
        ui.button(
            "Export CSV",
            on_click=lambda: ui.download.content(
                to_csv(page.s.shipments).encode("utf-8-sig"), "sendungen_input.csv"
            ),
        ).props("flat no-caps color=primary")
        ui.button(
            "Export XLSX",
            on_click=lambda: ui.download.content(to_xlsx_bytes(page.s.shipments), "sendungen_input.xlsx"),
        ).props("flat no-caps color=primary")
