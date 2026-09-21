"""Validation helpers for saved LED Studio artwork."""

from __future__ import annotations

import re
from typing import Any

MAX_ITEMS = 50
MAX_NAME_LENGTH = 64
MAX_ANIMATION_FRAMES = 120
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _colors(value: object, *, expected: int | None = None) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("Artwork must contain colors")
    if expected is not None and len(value) != expected:
        raise ValueError(f"Artwork must contain exactly {expected} colors")
    if len(value) > 520:
        raise ValueError("Artwork contains too many colors")
    if not all(isinstance(color, str) and _HEX_COLOR.fullmatch(color) for color in value):
        raise ValueError("Artwork contains an invalid color")
    return [color.lower() for color in value]


def validate_gallery_item(raw: object) -> dict[str, Any]:
    """Validate and normalize one browser-provided gallery item."""
    if not isinstance(raw, dict):
        raise ValueError("Artwork is not an object")

    name = str(raw.get("name", "")).strip()
    if not name:
        raise ValueError("Give the artwork a name")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Artwork names may contain at most {MAX_NAME_LENGTH} characters")

    target = raw.get("target")
    if target not in ("h70b3", "h6069"):
        raise ValueError("Unknown artwork target")
    kind = raw.get("kind")
    if kind not in ("art", "animation"):
        raise ValueError("Unknown artwork type")
    if kind == "animation" and target != "h70b3":
        raise ValueError("Animations are only supported for H70B3")

    brightness = int(raw.get("brightness", 100))
    if not 1 <= brightness <= 100:
        raise ValueError("Brightness must be between 1 and 100")

    item: dict[str, Any] = {
        "name": name,
        "target": target,
        "kind": kind,
        "brightness": brightness,
    }
    if kind == "art":
        item["colors"] = _colors(raw.get("colors"), expected=520 if target == "h70b3" else None)
    else:
        frames = raw.get("frames")
        if not isinstance(frames, list) or not frames:
            raise ValueError("Animation must contain frames")
        if len(frames) > MAX_ANIMATION_FRAMES:
            raise ValueError(f"Animation may contain at most {MAX_ANIMATION_FRAMES} frames")
        normalized_frames = []
        for frame in frames:
            if not isinstance(frame, dict):
                raise ValueError("Animation contains an invalid frame")
            duration = int(frame.get("duration", 100))
            if not 100 <= duration <= 2000:
                raise ValueError("Frame duration must be between 100 and 2000 ms")
            normalized_frames.append(
                {"colors": _colors(frame.get("colors"), expected=520), "duration": duration}
            )
        item["frames"] = normalized_frames

    return item
