"""Design-System (Gesamtpaket Abschnitt 7): Tokens, Schrift, Komponentenklassen, Bewegung.

Heller Website-Look über die volle Breite: reines Weiß, Geist, abgestimmte Pastelltöne, Haarlinien
statt Karten, feine Abstufung der Schrift (Überschrift, Fließtext, Beschriftung). Dezente Einblend-,
Hover- und Druckanimationen; ``prefers-reduced-motion`` schaltet sie ab.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from nicegui import app, ui

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

TOKENS: dict[str, str] = {
    "bg": "#FFFFFF",
    "surface": "#FFFFFF",
    "canvas": "#F5F5F4",
    "line": "#ECECEA",
    "line-strong": "#D9D9D6",
    "text": "#1F2933",
    "text-soft": "#3A4652",
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

START_COLORS: tuple[str, ...] = ("#1F6F8B", "#9A4F2F", "#5B4BB0", "#2D8470", "#8A5A00")
"""Linienfarbe je Startort (Reihenfolge der Startorte alphabetisch); Szenario über das Muster."""

SELECTION_COLORS: tuple[str, ...] = (
    "#0072B2", "#C24A00", "#00795A", "#A8327A", "#6E4BB0", "#8A6A00", "#B42318", "#1F6F8B",
)  # fmt: skip
"""Ausgewählte Routen: kategoriale Farben (Okabe-Ito, für Kontrast abgedunkelt), überall gleich."""

MAP_BACKGROUND = "#E5E5E5"
"""Bezugsfläche für den Linienkontrast: helle, entsättigte OSM-Kachel nach dem Filter in 7.3."""

TEXT_PAIRS: list[tuple[str, str]] = [
    ("text", "bg"),
    ("text", "surface"),
    ("text-soft", "bg"),
    ("text-soft", "canvas"),
    ("text-soft", "accent-tint"),
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
@font-face { font-family: 'Instrument Serif'; font-style: italic; font-weight: 400; font-display: swap;
  src: url('/tk-fonts/InstrumentSerif-Italic.woff2') format('woff2'); }
@font-face { font-family: 'Instrument Serif'; font-style: normal; font-weight: 400; font-display: swap;
  src: url('/tk-fonts/InstrumentSerif-Regular.woff2') format('woff2'); }
@font-face { font-family: 'Inter'; font-weight: 400; font-display: swap;
  src: url('/tk-fonts/Inter-Regular.woff2') format('woff2'); }
:root {
%(tokens)s
  --font: Geist, Inter, system-ui, sans-serif;
  --serif: "Instrument Serif", Georgia, serif;
  --shadow-sm: 0 1px 2px rgba(31, 41, 51, 0.06);
  --gutter: clamp(16px, 4vw, 72px);
  --ease: cubic-bezier(0.22, 1, 0.36, 1);
}
%(tones)s
html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 15px; line-height: 1.5;
  -webkit-font-smoothing: antialiased; font-feature-settings: "ss01"; }
.q-field, .q-btn, .q-tab, .q-table, .q-item, .q-chip, .q-menu, .q-tooltip { font-family: var(--font); }
.nicegui-content { padding: 0; }
.tk-page { width: 100%%; box-sizing: border-box; padding: 0 var(--gutter) 48px; gap: 0; }
.tk-prose { color: var(--text-soft); max-width: 68ch; }

/* ---------- Typografie ---------- */
.tk-title { font-size: 18px; font-weight: 600; letter-spacing: -0.02em; }
.tk-section { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
.tk-label { color: var(--muted); font-size: 13px; font-weight: 500; }
.tk-kicker { color: var(--muted); font-size: 12px; font-weight: 500; text-transform: uppercase;
  letter-spacing: 0.08em; }
.tk-dot { color: var(--accent); }
.tk-serif { font-family: var(--serif); font-style: italic; font-weight: 400; letter-spacing: -0.01em;
  font-size: 1.06em; }
.tk-kicker-line { display: flex; align-items: center; gap: 12px; }
.tk-kicker-line > :first-child::after { content: ""; display: inline-block; width: 28px; height: 1px;
  background: currentColor; vertical-align: middle; margin-left: 12px; }
.tk-num { font-variant-numeric: tabular-nums; }
.tk-kpi { font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }
.tk-delta-down { color: var(--accent); font-weight: 600; }
.tk-delta-up { color: var(--base); font-weight: 600; }
.tk-ist { color: var(--base); }

/* ---------- Navigation ---------- */
.tk-nav { position: sticky; top: 0; z-index: 1100; display: grid; grid-template-columns: 1fr auto 1fr;
  align-items: center; gap: 24px; width: 100%%; height: 72px; box-sizing: border-box; padding: 0 var(--gutter);
  background: rgba(255, 255, 255, 0.92); backdrop-filter: saturate(1.4) blur(12px);
  border-bottom: 1px solid transparent; transition: border-color 250ms var(--ease); }
.tk-nav.is-scrolled { border-bottom-color: var(--line); }
.tk-brand { display: inline-flex; align-items: baseline; gap: 10px; text-decoration: none; color: var(--text);
  justify-self: start; }
.tk-wordmark { font-size: 20px; font-weight: 700; letter-spacing: -0.04em; }
.tk-brand-name { font-size: 15px; font-weight: 500; letter-spacing: -0.01em; color: var(--text-soft); }
.tk-pagenav { display: flex; gap: 32px; justify-self: center; }
.tk-pagenav a { color: var(--muted); font-size: 14px; font-weight: 500; text-decoration: none; padding: 4px 0;
  background-image: linear-gradient(currentColor, currentColor); background-size: 0%% 1px;
  background-position: 0 100%%; background-repeat: no-repeat;
  transition: color 200ms var(--ease), background-size 250ms var(--ease); }
.tk-pagenav a:hover { color: var(--text); background-size: 100%% 1px; }
.tk-pagenav a[aria-current="page"] { color: var(--text); background-size: 100%% 1px; }
.tk-nav-cta { justify-self: end; }

/* ---------- Schrittleiste ---------- */
.tk-steps { display: flex; align-items: center; gap: 8px; width: 100%%; padding: 20px 0 0; flex-wrap: wrap; }
.tk-step { display: inline-flex; align-items: center; gap: 10px; padding: 6px 14px 6px 6px; border-radius: 999px;
  color: var(--muted); font-size: 13px; font-weight: 500; text-decoration: none;
  transition: background-color 200ms var(--ease), color 200ms var(--ease); }
.tk-step:hover { background: var(--canvas); color: var(--text); }
.tk-step-no { display: inline-grid; place-items: center; width: 24px; height: 24px; border-radius: 999px;
  border: 1px solid var(--line-strong); font-size: 12px; font-variant-numeric: tabular-nums; color: var(--muted); }
.tk-step-meta { color: var(--muted); font-weight: 400; }
.tk-step[aria-current="step"] { color: var(--text); }
.tk-step[aria-current="step"] .tk-step-no { background: var(--text); border-color: var(--text); color: var(--surface); }
.tk-step.is-done .tk-step-no { background: var(--accent-tint); border-color: var(--accent-tint); color: var(--accent); }
.tk-step-sep { width: 24px; height: 1px; background: var(--line-strong); }

/* ---------- Hero ---------- */
.tk-hero { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 32px; align-items: end;
  padding: 64px 0 48px; width: 100%%; }
.tk-hero-kicker { margin-bottom: 20px; }
.tk-hero-title { font-size: clamp(48px, 6.4vw, 88px); font-weight: 500; line-height: 1; letter-spacing: -0.045em;
  margin: 0; }
.tk-hero-sub { color: var(--text-soft); font-size: 17px; line-height: 1.55; max-width: 560px; margin-top: 24px; }
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
.tk-sec { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); column-gap: 32px; row-gap: 20px;
  width: 100%%; padding: 48px 0; border-top: 1px solid var(--line); scroll-margin-top: 80px; }
.tk-sec-head { grid-column: span 3; display: flex; flex-direction: column; gap: 10px; align-self: start;
  position: sticky; top: 96px; }
.tk-sec-body { grid-column: 4 / -1; min-width: 0; display: flex; flex-direction: column; gap: 20px; }
.tk-sec-wide { grid-column: 1 / -1; }
.tk-sec-title { display: flex; align-items: baseline; gap: 14px; font-size: 22px; font-weight: 500;
  letter-spacing: -0.02em; margin: 0; }
.tk-sec-num { color: var(--muted); font-size: 13px; font-weight: 500; font-variant-numeric: tabular-nums; }
.tk-step-status { color: var(--muted); font-size: 13px; }
.tk-step-status:empty { display: none; }
.tk-group { color: var(--muted); font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em;
  padding-bottom: 8px; border-bottom: 1px solid var(--line); width: 100%%; margin-top: 8px; }
.tk-grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px 24px; width: 100%%; }
.tk-grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px 24px; width: 100%%;
  align-items: start; }

/* ---------- Schwebende Leiste (Rechnen) ---------- */
@media (min-width: 1100px) {
  .tk-has-summary .tk-dock { display: none; }
  .tk-has-summary .tk-page-dock { padding-bottom: 48px; }
}
/* Centered via left/right/margin: the rise animation owns transform. */
.tk-dock { position: fixed; left: 0; right: 0; margin: 0 auto; bottom: 24px; z-index: 1200;
  display: flex; align-items: center; gap: 20px; padding: 8px 8px 8px 24px; border-radius: 999px;
  background: var(--surface); border: 1px solid var(--line);
  box-shadow: 0 1px 2px rgba(31, 41, 51, 0.06), 0 12px 32px rgba(31, 41, 51, 0.10);
  animation: tk-rise 600ms var(--ease) both; animation-delay: 300ms; width: max-content;
  max-width: calc(100%% - 32px); }
.tk-dock-info { display: flex; align-items: center; gap: 14px; font-size: 14px; white-space: nowrap; min-width: 0; }
.tk-dock .q-btn { flex-shrink: 0; white-space: nowrap; }
.tk-dock-info .tk-sep { color: var(--line-strong); }
.tk-page-dock { padding-bottom: 140px; }

/* ---------- Rechnen: Arbeitsbereich und Zusammenfassung ---------- */
.tk-work { display: grid; grid-template-columns: minmax(0, 1fr) 340px; column-gap: 48px; width: 100%%;
  align-items: start; }
.tk-work-main { min-width: 0; }
.tk-summary { position: sticky; top: 96px; margin-top: 48px; display: flex; flex-direction: column; gap: 16px;
  padding: 24px; border-radius: 12px; background: var(--canvas); }
.tk-summary-row { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; font-size: 14px;
  color: var(--text-soft); }
.tk-summary-row b { color: var(--text); font-weight: 600; font-variant-numeric: tabular-nums; }
.tk-summary-big { font-size: 34px; font-weight: 600; letter-spacing: -0.035em; line-height: 1.05;
  font-variant-numeric: tabular-nums; color: var(--text); }
.tk-summary .q-btn { width: 100%%; }
.tk-summary hr { border: 0; border-top: 1px solid var(--line-strong); margin: 0; width: 100%%; }
.tk-empty { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; padding: 24px;
  border: 1px dashed var(--line-strong); border-radius: 12px; }

/* ---------- Ergebnis: Werkzeugleiste ---------- */
.tk-toolbar { position: sticky; top: 72px; z-index: 1000; display: flex; align-items: center; gap: 16px;
  flex-wrap: wrap; width: 100%%; padding: 12px 0; background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(1.4) blur(12px); border-bottom: 1px solid var(--line); }
.tk-toolbar-end { margin-left: auto; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }

/* ---------- Info: Dokumentationslayout ---------- */
.tk-docs { display: grid; grid-template-columns: 240px minmax(0, 1fr); column-gap: 48px; width: 100%%;
  align-items: start; }
.tk-docs .q-tabs--vertical { position: sticky; top: 96px; border: 0; border-left: 1px solid var(--line); height: auto; }
.tk-docs .q-tabs--vertical .q-tab--active { color: var(--text); }
.tk-docs .q-tabs--vertical .q-tab--active .q-tab__label { font-weight: 600; }
.tk-docs .q-tabs--vertical .q-tab:hover { color: var(--text); }
.tk-docs .q-tabs--vertical .q-tab { justify-content: flex-start; padding: 0 16px; min-height: 40px; }
.tk-docs .q-tabs--vertical .q-tab__content { justify-content: flex-start; }
.tk-docs .q-tabs--vertical .q-tab__indicator { width: 1.5px; left: -1px; right: auto; background: var(--text); }
.tk-docs .q-tab-panel { padding-top: 0; }

/* ---------- Landing Page ---------- */
.tk-land-hero { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: 64px; align-items: center;
  width: 100%%; padding: 72px 0 64px; }
.tk-land-title { font-size: clamp(48px, 5.2vw, 104px); font-weight: 500; line-height: 0.98; letter-spacing: -0.05em;
  margin: 0; color: var(--text); }
.tk-land-sub { color: var(--text-soft); font-size: 19px; line-height: 1.55; max-width: 560px; margin-top: 28px; }
.tk-land-actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 36px; }
.tk-land-note { color: var(--muted); font-size: 13px; margin-top: 16px; }
.tk-land-visual { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.tk-land-visual-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.tk-land-svg { border: 1px solid var(--line); border-radius: 16px; overflow: hidden; background: var(--surface); }
.tk-land-svg svg { display: block; }
.tk-band { width: 100%%; padding: 72px 0; border-top: 1px solid var(--line); }
.tk-band-head { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); column-gap: 32px; margin-bottom: 40px; }
.tk-band-head > :first-child { grid-column: span 4; }
.tk-band-head > :last-child { grid-column: 6 / -1; }
.tk-band-title { font-size: clamp(30px, 3.2vw, 48px); font-weight: 500; letter-spacing: -0.04em; line-height: 1.05;
  margin: 0; color: var(--text); }
.tk-band-lead { color: var(--text-soft); font-size: 17px; line-height: 1.6; max-width: 68ch; }
.tk-cols { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 32px; row-gap: 48px; width: 100%%; }
.tk-col { display: flex; flex-direction: column; gap: 10px; padding-top: 20px; border-top: 1px solid var(--line-strong);
  min-width: 0; }
.tk-col-no { color: var(--muted); font-size: 13px; font-weight: 500; font-variant-numeric: tabular-nums; }
.tk-col-title { display: inline-flex; align-items: center; gap: 10px; font-size: 20px; font-weight: 500;
  letter-spacing: -0.02em; color: var(--text); margin: 0; }
.tk-col-title.tk-dotted::before { content: ""; width: 8px; height: 8px; border-radius: 999px; background: var(--tone-bg);
  box-shadow: inset 0 0 0 1.5px var(--tone-ink); flex-shrink: 0; }
.tk-col-text { color: var(--text-soft); font-size: 15px; line-height: 1.6; }
.tk-col .tk-link { align-self: flex-start; margin-top: 4px; }
.tk-stats-5 { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.tk-final { display: flex; justify-content: space-between; align-items: flex-end; gap: 32px; flex-wrap: wrap;
  width: 100%%; padding: 96px 0 72px; border-top: 1px solid var(--line); }

/* ---------- Footer ---------- */
.tk-foot { display: grid; grid-template-columns: minmax(0, 4fr) repeat(3, minmax(0, 2fr)); column-gap: 32px;
  row-gap: 32px; width: 100%%; padding: 48px 0 24px; border-top: 1px solid var(--line); margin-top: 48px; }
.tk-foot-col { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.tk-foot-head { color: var(--text); font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.tk-foot-col a, .tk-foot-item { color: var(--muted); font-size: 13px; text-decoration: none; line-height: 1.5; }
.tk-foot-col a:hover { color: var(--text); }
.tk-foot-claim { color: var(--text-soft); font-size: 14px; max-width: 36ch; }
.tk-foot-base { grid-column: 1 / -1; color: var(--muted); font-size: 12px; padding-top: 24px;
  border-top: 1px solid var(--line); }

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
  transition: transform 200ms var(--ease), background-color 200ms var(--ease), box-shadow 200ms var(--ease); }
.q-btn--unelevated.bg-primary:hover, .q-btn--outline:hover { transform: translateY(-1px); }
.q-btn--unelevated.bg-primary:hover { box-shadow: 0 6px 16px rgba(31, 41, 51, 0.16); }
.q-btn:active { transform: scale(0.97); }
.tk-btn-lg.q-btn { min-height: 48px; padding: 8px 24px; font-size: 15px; }
.tk-cta.is-loading { pointer-events: none; overflow: hidden; }
.tk-cta.is-loading .q-btn__content { opacity: 0.72; }
.tk-cta.is-loading::after { content: ""; position: absolute; left: 0; bottom: 0; width: 40%%; height: 2px;
  background: var(--surface); opacity: 0.8; animation: tk-slide 900ms var(--ease) infinite; }
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
.leaflet-tooltip.tk-map-label { background: rgba(255,255,255,0.85); border: 0; box-shadow: none; padding: 0 4px;
  font-size: 11px; font-weight: 500; color: var(--text); border-radius: 4px; }
.leaflet-tooltip.tk-map-label::before { display: none; }
.leaflet-tooltip.tk-map-start { font-size: 12px; font-weight: 600; }
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
.tk-js .tk-inview { transition: opacity 700ms var(--ease), transform 700ms var(--ease);
  transition-delay: var(--delay, 0ms); }
.tk-js .tk-inview:not(.is-in) { opacity: 0; transform: translateY(16px); }
.tk-stat-value, .tk-hero-title { animation: tk-pop 450ms var(--ease) both; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
  .tk-js .tk-inview:not(.is-in) { opacity: 1; transform: none; }
}

/* ---------- Breakpoints ---------- */
@media (max-width: 1279px) {
  .tk-cols { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tk-stats-5 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .tk-stats-5 .tk-stat:nth-child(4) { border-left: 0; padding-left: 0; }
  .tk-stats-5 .tk-stat:nth-child(n+4) { border-top: 1px solid var(--line); }
}
@media (max-width: 1099px) {
  .tk-nav { grid-template-columns: auto 1fr auto; }
  .tk-brand-name { display: none; }
  .tk-pagenav { gap: 20px; }
  .tk-work, .tk-docs, .tk-land-hero { grid-template-columns: 1fr; }
  .tk-summary { display: none; }
  .tk-docs .q-tabs--vertical { position: static; border-left: 0; margin-bottom: 24px; }
  .tk-band-head > :first-child, .tk-band-head > :last-child { grid-column: 1 / -1; }
  .tk-band-head { row-gap: 16px; }
  .tk-foot { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tk-foot > :first-child { grid-column: 1 / -1; }
  .tk-sec-head, .tk-sec-body { grid-column: 1 / -1; }
  .tk-sec-head { position: static; }
  .tk-sec-intro { max-width: 640px; }
  .tk-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tk-stat:nth-child(3) { border-left: 0; padding-left: 0; border-top: 1px solid var(--line); }
  .tk-stat:nth-child(4) { border-top: 1px solid var(--line); }
  .tk-hero { grid-template-columns: 1fr; }
  .tk-hero-side { align-items: flex-start; }
}
@media (max-width: 699px) {
  .tk-nav { grid-template-columns: auto 1fr; height: 60px; }
  .tk-nav-cta { display: none; }
  .tk-pagenav { gap: 14px; justify-self: end; }
  .tk-pagenav a { font-size: 13px; }
  .tk-toolbar { top: 60px; }
  .tk-steps { flex-wrap: nowrap; gap: 4px; }
  .tk-step { padding-right: 8px; gap: 6px; }
  .tk-step-meta { display: none; }
  .tk-step-sep { width: 12px; }
  .tk-segment button { padding: 7px 10px; }
  .tk-stats-5, .tk-cols { grid-template-columns: 1fr; }
  .tk-foot { grid-template-columns: 1fr; }
  .tk-dock { padding-left: 16px; gap: 12px; }
  .tk-dock-info > :not(:last-child) { display: none; }
  .q-btn-toggle { flex-wrap: wrap; }
}
"""


SCRIPT = """<script>
document.documentElement.classList.add('tk-js');
(() => {
  const nav = () => document.querySelector('.tk-nav')?.classList.toggle('is-scrolled', window.scrollY > 8);
  window.addEventListener('scroll', nav, {passive: true});
  const seen = new IntersectionObserver((items) => items.forEach((it) => {
    if (it.isIntersecting) { it.target.classList.add('is-in'); seen.unobserve(it.target); }
  }), {rootMargin: '0px 0px -8% 0px'});
  const watch = () => document.querySelectorAll('.tk-inview:not(.is-in)').forEach((el) => seen.observe(el));
  new MutationObserver(watch).observe(document.documentElement, {childList: true, subtree: true});
  watch();
  window.addEventListener('beforeprint', () => document.querySelectorAll('.tk-inview').forEach((el) => el.classList.add('is-in')));
})();
</script>"""
"""Kopfzeile mit Haarlinie nach dem Scrollen; Abschnitte mit ``tk-inview`` blenden beim Erreichen ein."""


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
    ui.add_head_html(SCRIPT)
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
