"""Browsertests der Ergebnisseite (pytest-playwright). Laufen nur mit ``pytest -m e2e``.

Startet die App als Server im Demo-Modus und prüft die Karte, den Routenvergleich und die
eigene Bündelung so, wie eine Person sie bedient.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator

import pytest

from tests.conftest import ROOT, needs_excel

pytestmark = [pytest.mark.e2e, needs_excel]

ROUTES = "70173-55116,70173-60311,70173-50667"
RIGHT_MAP = 2
"""Leaflet-Elemente in DOM-Reihenfolge: Differenz (verborgen), Vorher, Nachher."""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def app_url() -> Iterator[str]:
    port = _free_port()
    # NiceGUI switches to its test mode when it sees pytest variables; start it as a normal server.
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST")}
    env.update({"PYTHONPATH": "src", "TK_PORT": str(port), "TK_DEMO_MODE": "1"})
    proc = subprocess.Popen([sys.executable, "-m", "tk.ui.app"], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # fmt: skip
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(url, timeout=2).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            pytest.fail("App startet nicht")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _scenario(page, label: str) -> None:  # type: ignore[no-untyped-def]
    page.get_by_text(label, exact=True).first.click()
    page.wait_for_timeout(800)


def test_ist_shows_hint_instead_of_after_map(page, app_url: str) -> None:  # type: ignore[no-untyped-def]
    page.goto(f"{app_url}/ergebnis?tab=karte")
    page.wait_for_selector("path.leaflet-interactive")
    _scenario(page, "Ist")
    assert page.get_by_text("um Vorher und Nachher zu vergleichen").first.is_visible()
    _scenario(page, "M3 Bahn + Bündelung")
    page.wait_for_timeout(600)
    maps = page.locator(".nicegui-leaflet")
    # Both side-by-side maps keep Leaflet's own classes after being hidden and shown again.
    assert "leaflet-container" in (maps.nth(RIGHT_MAP).get_attribute("class") or "")
    assert maps.nth(RIGHT_MAP).locator("img.leaflet-tile").count() > 0


def test_m3_draws_rail_as_dashed_lines(page, app_url: str) -> None:  # type: ignore[no-untyped-def]
    page.goto(f"{app_url}/ergebnis?tab=karte")
    page.wait_for_selector("path.leaflet-interactive")
    _scenario(page, "M3 Bahn + Bündelung")
    page.wait_for_timeout(800)
    dashed = page.locator(".nicegui-leaflet").nth(RIGHT_MAP).locator("path[stroke-dasharray='8 6']")
    assert dashed.count() > 0


def test_route_selection_from_url_and_click(page, app_url: str) -> None:  # type: ignore[no-untyped-def]
    page.goto(f"{app_url}/ergebnis?tab=karte&routen={ROUTES}")
    page.wait_for_selector(".q-chip")
    assert page.locator(".q-chip").count() == 3
    assert page.get_by_text("Alle per Bahn").first.is_visible()
    page.evaluate("emitEvent('tk-relation', '76131 Karlsruhe > 10115 Berlin')")
    page.wait_for_timeout(800)
    assert page.locator(".q-chip").count() == 4
    assert "76131-10115" in page.url
    page.locator(".q-chip").first.locator(".q-chip__icon--remove").click()
    page.wait_for_timeout(800)
    assert page.locator(".q-chip").count() == 3
    assert "70173-55116" not in page.url


def test_custom_bundle_same_day_and_window(page, app_url: str) -> None:  # type: ignore[no-untyped-def]
    page.goto(f"{app_url}/ergebnis?tab=karte&routen={ROUTES}")
    page.wait_for_selector(".q-chip")
    page.get_by_role("button", name="Eigene Gruppe").click()
    page.wait_for_timeout(800)
    assert page.get_by_text("keine Verschiebung").first.is_visible()
    page.get_by_role("button", name="Zeitfenster").click()
    page.wait_for_timeout(1200)
    assert page.get_by_text("Block von 3 Tagen").first.is_visible()
    assert page.get_by_text("Verschiebung bis").first.is_visible()
