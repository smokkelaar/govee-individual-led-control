"""Pure, deterministic visual mappings for external Home Assistant sensors."""

from __future__ import annotations

from .const import STYLE_BAR, STYLE_POSITION, STYLE_PULSE

RGB = tuple[int, int, int]


def _normalized(level: int) -> int:
    return max(0, min(100, int(level)))


def _pulse_color(value: int) -> RGB:
    red = round(255 * value / 100)
    blue = 255 - red
    scale = max(10, value) / 100
    return (round(red * scale), 0, round(blue * scale))


def h6069_level_frame(level: int, style: str, panel_count: int) -> tuple[RGB, ...]:
    """Map 0..100 to protocol-indexed H6069 panel colors."""
    if panel_count < 1:
        raise ValueError("panel_count must be at least 1")
    value = _normalized(level)
    colors: list[RGB] = [(0, 0, 0)] * panel_count
    if style == STYLE_BAR:
        lit = round(value * panel_count / 100)
        for index in range(lit):
            fraction = (index + 1) / panel_count
            colors[index] = (
                (0, 255, 0)
                if fraction <= 0.60
                else (255, 190, 0)
                if fraction <= 0.85
                else (255, 0, 0)
            )
    elif style == STYLE_POSITION:
        index = round(value * (panel_count - 1) / 100)
        colors[index] = (255, 255, 255)
    elif style == STYLE_PULSE:
        colors = [_pulse_color(value)] * panel_count
    else:
        raise ValueError(f"unsupported level style {style!r}")
    return tuple(colors)


def h70b3_level_frame(
    level: int, style: str, width: int, height: int
) -> tuple[RGB, ...]:
    """Map 0..100 to a logical row-major curtain image."""
    if width < 1 or height < 1:
        raise ValueError("width and height must be at least 1")
    value = _normalized(level)
    colors: list[RGB] = [(0, 0, 0)] * (width * height)
    if style == STYLE_BAR:
        lit_rows = round(value * height / 100)
        for y in range(height - lit_rows, height):
            fraction = (height - y) / height
            color = (
                (255, 0, 0)
                if fraction > 0.85
                else (255, 190, 0)
                if fraction > 0.60
                else (0, 255, 0)
            )
            for x in range(width):
                colors[y * width + x] = color
    elif style == STYLE_POSITION:
        x_position = round(value * (width - 1) / 100)
        for y in range(height):
            colors[y * width + x_position] = (0, 255, 255)
    elif style == STYLE_PULSE:
        colors = [_pulse_color(value)] * (width * height)
    else:
        raise ValueError(f"unsupported level style {style!r}")
    return tuple(colors)
