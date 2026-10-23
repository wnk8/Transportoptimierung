"""Kontrast nach WCAG 2.x für alle Farbpaare aus Gesamtpaket 7.2 (Abnahmekriterium)."""

from __future__ import annotations

import pytest

from tk.ui.theme import (
    MAP_BACKGROUND,
    MAP_LINES,
    SELECTION_COLORS,
    START_COLORS,
    STATUS_STYLES,
    TEXT_PAIRS,
    TOKENS,
)


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_formula_reference_values() -> None:
    assert contrast("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert contrast("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)


@pytest.mark.parametrize(("fg", "bg"), TEXT_PAIRS)
def test_text_pairs_at_least_4_5(fg: str, bg: str) -> None:
    assert contrast(TOKENS[fg], TOKENS[bg]) >= 4.5, (fg, bg)


@pytest.mark.parametrize("status", list(STATUS_STYLES))
def test_status_chips(status: str) -> None:
    bg, fg = STATUS_STYLES[status]
    assert contrast(TOKENS[fg], TOKENS[bg]) >= 4.5


@pytest.mark.parametrize("layer", list(MAP_LINES))
def test_map_lines_at_least_3(layer: str) -> None:
    color, _ = MAP_LINES[layer]
    assert contrast(color, MAP_BACKGROUND) >= 3.0
    assert contrast(color, TOKENS["surface"]) >= 3.0  # SVG-Rückfall auf weißer Fläche


@pytest.mark.parametrize("color", START_COLORS + SELECTION_COLORS)
def test_route_colors_at_least_3(color: str) -> None:
    assert contrast(color, MAP_BACKGROUND) >= 3.0
    assert contrast(color, TOKENS["surface"]) >= 3.0


def test_documented_values() -> None:
    """Die in 7.2 genannten Werte sind gerundet korrekt."""
    assert round(contrast(TOKENS["text"], TOKENS["surface"]), 1) == 14.8
    assert round(contrast(TOKENS["text-soft"], TOKENS["surface"]), 1) == 9.6
    assert round(contrast(TOKENS["muted"], TOKENS["surface"]), 1) == 6.3
    assert round(contrast(TOKENS["accent"], TOKENS["surface"]), 1) == 6.0
    assert round(contrast(TOKENS["base"], TOKENS["surface"]), 1) == 5.9
    assert round(contrast(TOKENS["info"], TOKENS["surface"]), 1) == 5.3
    assert round(contrast(TOKENS["danger"], TOKENS["surface"]), 1) == 6.6
