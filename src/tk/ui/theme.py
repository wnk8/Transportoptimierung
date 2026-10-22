"""Design-System (Gesamtpaket Abschnitt 7): Tokens, Schrift, Komponentenklassen, Bewegung.

Minimaler Website-Look: warmes Off-White, Geist, abgestimmte Pastelltöne, Haarlinien statt
Karten. Dezente Einblend- und Hover-Animationen; ``prefers-reduced-motion`` schaltet sie ab.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from nicegui import app, ui

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

TOKENS: dict[str, str] = {
    "bg": "#FAF8F5",
    "surface": "#FFFFFF",
    "canvas": "#F3F0EB",
    "line": "#E6E1D9",
    "line-strong": "#D8D2C8",
    "text": "#1F2933",
    "muted": "#56616E",
    "accent": "#1F6F5F",
    "accent-tint": "#E3EEE7",
    "base": "#9A4F2F",
    "base-tint": "#F6E6DB",
    "info": "#2F6FA8",
    "info-tint": "#E9F0F7",
    "violet": "#5B4BB0",
    "violet-tint": "#E9E5F4",
    "note-tint": "#F5EED8",
    "note-text": "#8A5A00",
    "danger": "#B42318",
    "danger-tint": "#F7E4E2",
}
"""Farbtokens (Gesamtpaket 7.2)."""

MAP_LINES: dict[str, tuple[str, str]] = {
    "ist": ("#B5694A", ""),
    "lkw": ("#2D8470", ""),
    "bahn": ("#2F6FA8", "8 6"),
    "luft": ("#56616E", "4 6"),
    "strasse": ("#1F2933", ""),
    "auswahl": ("#B42318", ""),
}
"""Kartenlinien: Farbe und Strichmuster (Muster zusätzlich zur Farbe)."""

MAP_BACKGROUND = "#E5E5E5"
"""Bezugsfläche für den Linienkontrast: helle, entsättigte OSM-Kachel nach dem Filter in 7.3."""

TEXT_PAIRS: list[tuple[str, str]] = [
    ("text", "bg"),
    ("text", "surface"),
    ("muted", "surface"),
    ("muted", "bg"),
    ("text", "canvas"),
    ("muted", "canvas"),
    ("accent", "canvas"),
    ("accent", "bg"),
    ("surface", "text"),
    ("muted", "note-tint"),
    ("muted", "danger-tint"),
    ("accent", "surface"),
    ("surface", "accent"),
    ("text", "accent-tint"),
    ("accent", "accent-tint"),
    ("muted", "accent-tint"),
    ("base", "surface"),
    ("base", "base-tint"),
    ("text", "base-tint"),
    ("muted", "base-tint"),
    ("info", "surface"),
    ("info", "info-tint"),
    ("text", "info-tint"),
    ("muted", "info-tint"),
    ("violet", "surface"),
    ("violet", "violet-tint"),
    ("text", "violet-tint"),
    ("muted", "violet-tint"),
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

TONES: dict[str, tuple[str, str]] = {
    "mint": ("accent-tint", "accent"),
    "sky": ("info-tint", "info"),
    "peach": ("base-tint", "base"),
    "lavender": ("violet-tint", "violet"),
}
"""Pastelltöne für Kennzahlenkacheln und Schrittnummern: Fläche und Schriftfarbe (Paare in TEXT_PAIRS)."""

CSS = """
@font-face { font-family: 'Geist'; font-weight: 100 900; font-display: swap;
  src: url('/tk-fonts/Geist-Variable.woff2') format('woff2'); }
@font-face { font-family: 'Inter'; font-weight: 400; font-display: swap;
  src: url('/tk-fonts/Inter-Regular.woff2') format('woff2'); }
:root {
%(tokens)s
  --font: Geist, Inter, system-ui, sans-serif;
  --shadow-sm: 0 1px 2px rgba(31, 41, 51, 0.06);
  --ease: cubic-bezier(0.22, 1, 0.36, 1);
}
%(tones)s
html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 15px; line-height: 1.5;
  -webkit-font-smoothing: antialiased; font-feature-settings: "ss01"; }
.q-field, .q-btn, .q-tab, .q-table, .q-item, .q-chip, .q-menu, .q-tooltip { font-family: var(--font); }
.nicegui-content { padding: 0; }
.tk-page { max-width: 1280px; margin: 0 auto; padding: 0 32px 48px; gap: 0; }

/* ---------- Typografie ---------- */
.tk-title { font-size: 18px; font-weight: 600; letter-spacing: -0.02em; }
.tk-section { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
.tk-label { color: var(--muted); font-size: 13px; font-weight: 500; }
.tk-kicker { color: var(--muted); font-size: 12px; font-weight: 500; text-transform: uppercase;
  letter-spacing: 0.08em; }
.tk-dot { color: var(--accent); }
.tk-kicker-line { display: flex; align-items: center; gap: 12px; }
.tk-kicker-line > :first-child::after { content: ""; display: inline-block; width: 28px; height: 1px;
  background: currentColor; vertical-align: middle; margin-left: 12px; }
.tk-num { font-variant-numeric: tabular-nums; }
.tk-kpi { font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }
.tk-delta-down { color: var(--accent); font-weight: 600; }
.tk-delta-up { color: var(--base); font-weight: 600; }
.tk-ist { color: var(--base); }

/* ---------- Navigation (fest) ---------- */
.tk-nav { position: sticky; top: 0; z-index: 1100; display: flex; align-items: center; gap: 24px; width: 100%%;
  height: 68px; box-sizing: border-box;
  padding: 0 max(32px, calc((100%% - 1280px) / 2 + 32px)); background: color-mix(in srgb, var(--bg) 88%%, transparent); backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px); border-bottom: 1px solid var(--line); }
.tk-wordmark { font-size: 20px; font-weight: 700; letter-spacing: -0.04em; text-decoration: none; color: var(--text); }
.tk-pagenav { display: flex; gap: 2px; padding: 3px; border-radius: 999px; background: var(--canvas); }
.tk-pagenav a { color: var(--muted); font-size: 14px; font-weight: 500; text-decoration: none; padding: 6px 14px;
  border-radius: 999px; transition: background-color 200ms var(--ease), color 200ms var(--ease); }
.tk-pagenav a:hover { color: var(--text); }
.tk-pagenav a[aria-current="page"] { color: var(--text); background: var(--surface); font-weight: 600;
  box-shadow: var(--shadow-sm); }
.tk-nav-kpis { display: flex; gap: 20px; margin-left: auto; align-items: center;
  transition: opacity 300ms var(--ease), transform 300ms var(--ease); }
.tk-nav-kpi { display: flex; align-items: center; gap: 8px; font-size: 13px; white-space: nowrap; }
.tk-nav-kpi .tk-nav-kpi-label { color: var(--muted); }
.tk-nav-kpi .tk-nav-kpi-value { font-weight: 600; font-variant-numeric: tabular-nums; }
body.tk-hero-page:not(.tk-scrolled) .tk-nav-kpis { opacity: 0; transform: translateY(-6px); pointer-events: none; }
.tk-nav .tk-cta-link { margin-left: 8px; flex-shrink: 0; }

/* ---------- Hero ---------- */
.tk-hero { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 32px; align-items: end;
  padding: 72px 0 40px; width: 100%%; }
.tk-hero-title { font-size: clamp(44px, 5.4vw, 72px); font-weight: 600; line-height: 1.02; letter-spacing: -0.045em;
  margin: 0; }
.tk-hero-sub { color: var(--muted); font-size: 18px; line-height: 1.5; max-width: 660px; margin-top: 18px; }
.tk-hero-side { display: flex; flex-direction: column; align-items: flex-end; gap: 12px; }

/* ---------- Kennzahlen ---------- */
.tk-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); width: 100%%;
  border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.tk-stat { display: flex; flex-direction: column; gap: 8px; padding: 24px 24px 24px 0; min-width: 0;
  transition: background-color 250ms var(--ease); }
.tk-stat + .tk-stat { border-left: 1px solid var(--line); padding-left: 24px; }
.tk-stat-label { display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px;
  font-weight: 500; }
.tk-stat-label::before { content: ""; width: 8px; height: 8px; border-radius: 999px; background: var(--tone-bg);
  box-shadow: inset 0 0 0 1.5px var(--tone-ink); }
.tk-stat-value { font-size: clamp(30px, 3vw, 40px); font-weight: 600; letter-spacing: -0.035em; line-height: 1.05;
  font-variant-numeric: tabular-nums; }
.tk-stat-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; color: var(--muted); font-size: 13px; }
.tk-delta-chip { display: inline-flex; border-radius: 999px; padding: 3px 10px; font-size: 12px; font-weight: 600;
  font-variant-numeric: tabular-nums; }
.tk-delta-chip.down { background: var(--accent-tint); color: var(--accent); }
.tk-delta-chip.up { background: var(--base-tint); color: var(--base); }
.tk-delta-chip.flat { background: var(--canvas); color: var(--muted); }

/* ---------- Abschnitte ---------- */
.tk-sec { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); column-gap: 32px; row-gap: 24px;
  width: 100%%; padding: 56px 0; border-top: 1px solid var(--line); scroll-margin-top: 72px; }
.tk-sec:first-of-type { border-top: 0; }
.tk-sec-head { grid-column: span 4; display: flex; flex-direction: column; gap: 14px; align-self: start;
  position: sticky; top: 92px; }
.tk-sec-body { grid-column: span 8; min-width: 0; display: flex; flex-direction: column; gap: 20px; }
.tk-sec-wide { grid-column: 1 / -1; }
.tk-sec-title { font-size: 34px; font-weight: 600; line-height: 1.08; letter-spacing: -0.035em; margin: 0; }
.tk-sec-intro { color: var(--muted); font-size: 15px; max-width: 340px; }
.tk-step-status { display: inline-flex; align-self: flex-start; color: var(--text); font-size: 13px; font-weight: 500;
  background: var(--tone-bg, var(--canvas)); border-radius: 999px; padding: 4px 12px; }
.tk-group { color: var(--muted); font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em;
  padding-bottom: 8px; border-bottom: 1px solid var(--line); width: 100%%; margin-top: 8px; }
.tk-grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px 24px; width: 100%%; }
.tk-grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px 24px; width: 100%%;
  align-items: start; }

/* Alte Kartenklassen bleiben für Dialoge, leere Zustände und die Vorschau. */
.tk-card { background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 20px; }
.tk-chip { display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 5px 12px;
  font-size: 13px; font-weight: 500; border: 1px solid transparent; }
.tk-chip::before { content: ""; width: 7px; height: 7px; border-radius: 999px; background: currentColor; }
.tk-note { background: var(--note-tint); color: var(--text); border-radius: 12px; padding: 12px 16px; }
.tk-error { background: var(--danger-tint); color: var(--danger); border-radius: 12px; padding: 12px 16px; }
.tk-success { background: var(--accent-tint); color: var(--accent); border-radius: 12px; padding: 12px 16px; }

/* ---------- Felder ---------- */
.tk-field { display: flex; flex-direction: column; gap: 6px; width: 100%%; }
.tk-field-label { color: var(--text); font-size: 13px; font-weight: 500; cursor: help; }
.tk-field-label .tk-id { color: var(--muted); font-weight: 500; margin-right: 6px; font-variant-numeric: tabular-nums; }
.tk-help { color: var(--muted); font-size: 12.5px; line-height: 1.45; }
.q-field--outlined .q-field__control { border-radius: 12px; background: var(--surface);
  transition: background-color 200ms var(--ease); }
.q-field--outlined .q-field__control:before { border-color: var(--line-strong); transition: border-color 200ms; }
.q-field--outlined:hover .q-field__control:before { border-color: var(--muted); }
.q-field--focused .q-field__control:after { border-width: 1.5px !important; }
.q-field__suffix { color: var(--muted); font-size: 13px; font-weight: 500; }
.q-field__native, .q-field__input { font-variant-numeric: tabular-nums; }
.tk-field--changed .q-field__control { background: var(--accent-tint); }
.tk-field--changed .tk-help { color: var(--accent); font-weight: 500; }

/* ---------- Schaltflächen ---------- */
.q-btn { border-radius: 999px; font-weight: 500; letter-spacing: 0; padding: 6px 18px;
  transition: transform 200ms var(--ease), background-color 200ms var(--ease); }
.q-btn--unelevated.bg-primary:hover { transform: translateY(-1px); }
.q-btn--outline:before { border-color: var(--line-strong) !important; }
.q-btn--flat { padding: 6px 10px; }
.tk-cta .q-btn__content::after { content: "\\2192"; margin-left: 10px; transition: transform 200ms var(--ease); }
.tk-cta:hover .q-btn__content::after { transform: translateX(3px); }
.tk-link { position: relative; color: var(--text); text-decoration: none; cursor: pointer; background: none; border: 0;
  padding: 0 0 2px; font-size: 13px; font-weight: 500;
  background-image: linear-gradient(currentColor, currentColor); background-size: 100%% 1px;
  background-position: 0 100%%; background-repeat: no-repeat; transition: background-size 250ms var(--ease); }
.tk-link:hover { background-size: 0%% 1px; background-position: 100%% 100%%; }
.tk-link.q-btn { padding: 0 0 2px; min-height: 0; border-radius: 0; }
.tk-link.q-btn .q-focus-helper { display: none; }

/* ---------- Umschalter ---------- */
.tk-segment { display: inline-flex; gap: 2px; padding: 3px; border-radius: 999px; background: var(--canvas); }
.tk-segment button { padding: 7px 16px; font-size: 13px; font-weight: 500; color: var(--muted); border-radius: 999px;
  background: transparent; border: 0; cursor: pointer; font-family: var(--font);
  transition: background-color 200ms var(--ease), color 200ms var(--ease); }
.tk-segment button:hover { color: var(--text); }
.tk-segment button[aria-pressed="true"] { background: var(--surface); color: var(--text); font-weight: 600;
  box-shadow: var(--shadow-sm); }

/* ---------- Tabs ---------- */
.q-tabs { border-bottom: 1px solid var(--line); }
.q-tab { color: var(--muted); padding: 0 12px; min-height: 40px; }
.q-tab--active { color: var(--text); }
.q-tab__label { font-weight: 500; font-size: 14px; }
.q-tab__indicator { height: 1.5px; background: var(--text); }
.tk-pilltabs.q-tabs { border-bottom: 0; }
.tk-pilltabs .q-tab { border-radius: 999px; margin-right: 4px; min-height: 36px; padding: 0 14px;
  transition: background-color 200ms var(--ease); }
.tk-pilltabs .q-tab:hover { background: var(--canvas); }
.tk-pilltabs .q-tab--active { background: var(--text); color: var(--surface); }
.tk-pilltabs .q-tab__indicator { display: none; }
.q-tab-panel { padding: 24px 0 0; }
.q-tab-panels { background: transparent; }
.tk-step-status:empty { display: none; }
.q-uploader { border-radius: 12px; box-shadow: none; border: 1px dashed var(--line-strong); }
.q-expansion-item .q-item { border-radius: 12px; padding-left: 4px; }

/* ---------- Tabellen ---------- */
.q-table__container, .q-table__card { background: transparent; box-shadow: none; }
.q-table th { font-weight: 500; color: var(--muted); font-size: 12.5px; }
.q-table td { font-variant-numeric: tabular-nums; }
.q-table thead tr, .q-table tbody td { border-color: var(--line); }
.q-table tbody tr { transition: background-color 150ms; }
.q-table tbody tr:hover > td { background: var(--canvas); }

/* ---------- Karte und Fortschritt ---------- */
.leaflet-tile-pane { filter: grayscale(0.85) sepia(0.08) contrast(0.95) brightness(1.04); }
.leaflet-container { border-radius: 16px; background: var(--canvas); }
.tk-progress { height: 2px; background: var(--line); overflow: hidden; border-radius: 2px; }
.tk-progress > div { height: 100%%; width: 40%%; background: var(--text); animation: tk-slide 900ms var(--ease) infinite; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

/* ---------- Abschluss ---------- */
.tk-end { width: 100%%; padding: 72px 0 24px; border-top: 1px solid var(--line); display: flex; flex-direction: column;
  gap: 16px; }
.tk-end-link { font-size: clamp(32px, 4vw, 52px); font-weight: 600; letter-spacing: -0.04em; color: var(--text);
  text-decoration: none; display: inline-flex; align-items: center; gap: 16px; align-self: flex-start; }
.tk-end-link::after { content: "\\2192"; transition: transform 250ms var(--ease); }
.tk-end-link:hover::after { transform: translateX(8px); }
.tk-footer { color: var(--muted); font-size: 12px; padding-top: 24px; }

/* ---------- Bewegung ---------- */
@keyframes tk-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes tk-pop { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes tk-slide { from { transform: translateX(-100%%); } to { transform: translateX(250%%); } }
.tk-reveal { animation: tk-rise 700ms var(--ease) both; animation-delay: var(--delay, 0ms); }
.tk-stat-value, .tk-hero-title, .tk-nav-kpi-value { animation: tk-pop 450ms var(--ease) both; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}

/* ---------- Breakpoints ---------- */
@media (max-width: 1279px) {
  .tk-nav-kpi-value { display: none; }
  .tk-nav-kpi:last-child .tk-nav-kpi-value { display: inline; }
  .tk-nav-kpis { gap: 14px; }
  .tk-nav { padding: 0 24px; gap: 16px; }
  .tk-page { padding: 0 24px 40px; }
}
@media (max-width: 1099px) {
  .tk-sec-head, .tk-sec-body { grid-column: 1 / -1; }
  .tk-sec-head { position: static; }
  .tk-sec-intro { max-width: 640px; }
  .tk-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tk-stat:nth-child(3) { border-left: 0; padding-left: 0; border-top: 1px solid var(--line); }
  .tk-stat:nth-child(4) { border-top: 1px solid var(--line); }
  .tk-hero { grid-template-columns: 1fr; }
  .tk-hero-side { align-items: flex-start; }
}
"""

MOTION_JS = """
<script>
(() => {
  // Fixed nav shows the compact figures once the hero figures have scrolled out of view.
  const update = () => {
    const stats = document.querySelector('.tk-stats');
    const scrolled = !stats || stats.getBoundingClientRect().bottom < 72;
    document.body.classList.toggle('tk-scrolled', scrolled);
  };
  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update);
  setInterval(update, 1000);
})();
</script>
"""
"""Kleines Skript für die feste Leiste: setzt ``tk-scrolled``, sobald die Kennzahlen des Hero oben verschwinden."""


def css() -> str:
    tokens = "\n".join(f"  --{k}: {v};" for k, v in TOKENS.items())
    tones = "\n".join(
        f".tk-tone-{name} {{ --tone-bg: var(--{bg}); --tone-ink: var(--{ink}); }}"
        for name, (bg, ink) in TONES.items()
    )
    return CSS % {"tokens": tokens, "tones": tones}


_fonts_registered = False


def apply_theme() -> None:
    """Schrift, CSS-Tokens und Quasar-Farben für die aktuelle Seite setzen."""
    global _fonts_registered
    if not _fonts_registered:
        app.add_static_files("/tk-fonts", FONT_DIR)
        _fonts_registered = True
    ui.add_css(css())
    ui.add_body_html(MOTION_JS)
    ui.colors(
        primary=TOKENS["text"],
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
    """Segmentierte Auswahl Ist, M2, M3 als Pillen. Aktiv: weiße Pille, fette Schrift, aria-pressed."""

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
