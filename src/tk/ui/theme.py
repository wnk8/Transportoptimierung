"""Design-System (Gesamtpaket Abschnitt 7): Tokens, Schrift, Komponentenklassen.

Heller Modus, eine Akzentfarbe, Farbe trägt Bedeutung. Hierarchie über Größe, Gewicht und
Abstand. Keine Animation außer 150 ms bei Hover und Fokus.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from nicegui import app, ui

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

TOKENS: dict[str, str] = {
    "bg": "#F6F7F8",
    "surface": "#FFFFFF",
    "line": "#E3E6EA",
    "text": "#1F2933",
    "muted": "#56616E",
    "accent": "#1F6F5F",
    "accent-tint": "#E8F3EE",
    "base": "#9A4F2F",
    "base-tint": "#F8EBE4",
    "info": "#2F6FA8",
    "info-tint": "#E6EFF8",
    "note-tint": "#FAF3DC",
    "note-text": "#8A5A00",
    "danger": "#B42318",
    "danger-tint": "#FDECEA",
}
"""Farbtokens (Gesamtpaket 7.2)."""

MAP_LINES: dict[str, tuple[str, str]] = {
    "ist": ("#B5694A", ""),
    "lkw": ("#2D8470", ""),
    "bahn": ("#2F6FA8", "8 6"),
}
"""Kartenlinien: Farbe und Strichmuster (Muster zusätzlich zur Farbe)."""

MAP_BACKGROUND = "#E5E5E5"
"""Bezugsfläche für den Linienkontrast: helle, entsättigte OSM-Kachel nach dem Filter in 7.3."""

TEXT_PAIRS: list[tuple[str, str]] = [
    ("text", "bg"),
    ("text", "surface"),
    ("muted", "surface"),
    ("muted", "bg"),
    ("accent", "surface"),
    ("surface", "accent"),
    ("text", "accent-tint"),
    ("accent", "accent-tint"),
    ("muted", "accent-tint"),
    ("base", "surface"),
    ("base", "base-tint"),
    ("text", "base-tint"),
    ("info", "surface"),
    ("info", "info-tint"),
    ("text", "info-tint"),
    ("text", "note-tint"),
    ("note-text", "note-tint"),
    ("danger", "surface"),
    ("danger", "danger-tint"),
    ("surface", "danger"),
    ("surface", "text"),
]
"""Alle Text-Hintergrund-Paare, die die Oberfläche verwendet (mindestens 4,5 : 1)."""

STATUS_STYLES: dict[str, tuple[str, str]] = {
    "Keine Eingabe": ("surface", "muted"),
    "Eingabe prüfen": ("note-tint", "note-text"),
    "Plan zulässig": ("accent-tint", "accent"),
    "Plan prüfen": ("danger-tint", "danger"),
}
"""Status-Chip: Fläche und Schrift je Cockpit-Status (Input!R8)."""

CSS = """
@font-face { font-family: 'Inter'; font-weight: 400; font-display: swap;
  src: url('/tk-fonts/Inter-Regular.woff2') format('woff2'); }
@font-face { font-family: 'Inter'; font-weight: 500; font-display: swap;
  src: url('/tk-fonts/Inter-Medium.woff2') format('woff2'); }
@font-face { font-family: 'Inter'; font-weight: 600; font-display: swap;
  src: url('/tk-fonts/Inter-SemiBold.woff2') format('woff2'); }
:root {
%(tokens)s
}
body { background: var(--bg); color: var(--text); font-family: Inter, system-ui, sans-serif; font-size: 14px; }
.q-field, .q-btn, .q-tab, .q-table, .q-item, .q-chip { font-family: Inter, system-ui, sans-serif; }
.tk-page { max-width: 1600px; margin: 0 auto; padding: 16px; gap: 16px; }
.tk-title { font-size: 20px; font-weight: 600; }
.tk-section { font-size: 14px; font-weight: 600; }
.tk-card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }
.tk-label { color: var(--muted); font-size: 12px; font-weight: 500; }
.tk-kpi { font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.2; }
.tk-num { font-variant-numeric: tabular-nums; }
.tk-delta-down { color: var(--accent); font-weight: 600; }
.tk-delta-up { color: var(--base); font-weight: 600; }
.tk-ist { color: var(--base); }
.tk-chip { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 12px;
  font-size: 12px; font-weight: 600; border: 1px solid var(--line); }
.tk-note { background: var(--note-tint); color: var(--text); border-radius: 8px; padding: 8px 12px; }
.tk-error { background: var(--danger-tint); color: var(--danger); border-radius: 8px; padding: 8px 12px; }
.tk-success { background: var(--accent-tint); color: var(--accent); border-radius: 8px; padding: 8px 12px; }
.tk-segment { display: inline-flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden;
  background: var(--surface); }
.tk-segment button { padding: 6px 14px; font-size: 14px; font-weight: 500; color: var(--text);
  background: transparent; border: 0; cursor: pointer; transition: background-color 150ms, color 150ms; }
.tk-segment button + button { border-left: 1px solid var(--line); }
.tk-segment button:hover { background: var(--bg); }
.tk-segment button[aria-pressed="true"] { background: var(--accent); color: var(--surface); }
.tk-link { color: var(--accent); text-decoration: underline; cursor: pointer; background: none; border: 0;
  padding: 0; font-size: 12px; font-weight: 500; }
.tk-footer { color: var(--muted); font-size: 12px; }
.tk-progress { height: 2px; background: var(--accent-tint); overflow: hidden; border-radius: 2px; }
.tk-progress > div { height: 100%%; width: 40%%; background: var(--accent); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
a, button { transition: background-color 150ms, color 150ms; }
.leaflet-tile-pane { filter: grayscale(0.85) contrast(0.95) brightness(1.04); }
.q-table th { font-weight: 600; color: var(--muted); font-size: 12px; }
.q-table td { font-variant-numeric: tabular-nums; }
.q-tab__label { font-weight: 500; }
@media (max-width: 1279px) {
  .tk-two-col { flex-direction: column; }
  .tk-two-col > * { width: 100%% !important; min-width: 0 !important; flex: none !important; }
}
"""


def css() -> str:
    tokens = "\n".join(f"  --{k}: {v};" for k, v in TOKENS.items())
    return CSS % {"tokens": tokens}


_fonts_registered = False


def apply_theme() -> None:
    """Schrift, CSS-Tokens und Quasar-Farben für die aktuelle Seite setzen."""
    global _fonts_registered
    if not _fonts_registered:
        app.add_static_files("/tk-fonts", FONT_DIR)
        _fonts_registered = True
    ui.add_css(css())
    ui.colors(
        primary=TOKENS["accent"],
        secondary=TOKENS["muted"],
        accent=TOKENS["accent"],
        positive=TOKENS["accent"],
        negative=TOKENS["danger"],
        info=TOKENS["info"],
        warning=TOKENS["note-text"],
        dark=TOKENS["text"],
    )
    ui.query("body").classes("tk-body")


def status_chip(status: str) -> ui.html:
    """Status-Chip als Abbild von Input!R8, immer mit Text."""
    bg, fg = STATUS_STYLES.get(status, ("surface", "muted"))
    return ui.html(
        f'<span class="tk-chip" role="status" style="background:var(--{bg});color:var(--{fg})">{status}</span>'
    )


class ScenarioToggle:
    """Segmentierte Auswahl Ist, M2, M3. Aktiv: Akzentfläche mit weißer Schrift."""

    OPTIONS = (("Ist", "Ist"), ("M2", "M2 Bündelung"), ("M3", "M3 Bahn + Bündelung"))

    def __init__(self, value: str, on_change: Callable[[str], object]) -> None:
        self.value = value
        self._on_change = on_change
        self._buttons: dict[str, ui.element] = {}
        with ui.element("div").classes("tk-segment").props('role="group" aria-label="Szenario"'):
            for key, label in self.OPTIONS:
                btn = ui.element("button").props(f'type="button" aria-pressed="{str(key == value).lower()}"')
                with btn:
                    ui.label(label)
                btn.on("click", lambda _e, k=key: self.set(k))
                self._buttons[key] = btn

    def set(self, key: str) -> None:
        self.value = key
        for k, btn in self._buttons.items():
            btn.props(f'aria-pressed="{str(k == key).lower()}"')
        self._on_change(key)
