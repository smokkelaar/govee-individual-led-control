"""Encode the verified steady H6069 internal-position effect, without I/O.

Masks select positions on every panel: 1 TL, 2 TR, 4 BR, 8 BL, 16 center.
There is no panel ID in this program. Disjoint groups or a Whole/Point overlay.
Activation must be supplied separately for the chosen effect slot.
"""

from __future__ import annotations

from typing import Sequence


def _checked(body: bytes) -> bytes:
    checksum = 0
    for value in body:
        checksum ^= value
    return body + bytes((checksum,))


def _validate_rgb(rgb: Sequence[int]) -> None:
    if len(rgb) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in rgb):
        raise ValueError("RGB must contain three integers in 0..255")


def _steady_layer(mask: int, rgb: Sequence[int], *, whole: bool = False, priority: int = 0) -> bytes:
    # Movement: no entrance/exit or fade, one color, width50, no black gap,
    # fixed brightness100. Layer direction1 is the app default.
    action = bytes((0, 0, 0, 0, 0, 0, 1)) + bytes(rgb) + bytes((50, 0, 0, 100, 100))
    body = mask.to_bytes(2, "big") + bytes((int(whole), 1, 0)) + bytes(4)
    body += bytes((0,)) + len(action).to_bytes(2, "little") + action
    return bytes((priority, 50)) + len(body).to_bytes(2, "little") + body


def _encode_layers(layers: Sequence[bytes]) -> tuple[bytes, ...]:
    payload = bytes((100, 0, len(layers))) + b"".join(layers)
    chunks = [payload[:14]] + [payload[i:i + 17] for i in range(14, len(payload), 17)]
    frames = [_checked(bytes((0xA3, 0, 1, len(chunks), 0x58)) + chunks[0].ljust(14, b"\x00"))]
    for index, chunk in enumerate(chunks[1:], 1):
        frame_index = 0xFF if index == len(chunks) - 1 else index
        frames.append(_checked(bytes((0xA3, frame_index)) + chunk.ljust(17, b"\x00")))
    return tuple(frames)


def build_upload_frames(groups: Sequence[tuple[int, Sequence[int]]]) -> tuple[bytes, ...]:
    """Build A3/58 upload frames; no activation, Bluetooth or LAN writes.

    Three groups (1, red), (2, green), (4, blue) were physically verified
    steady for a minute. Other masks/colors are encodable, not all tested.
    Unselected internal positions are dark in that verified program.
    """
    if not 1 <= len(groups) <= 3:
        raise ValueError("The app supports one to three effect layers")
    layers = []
    used = 0
    for mask, rgb in groups:
        if type(mask) is not int or not 1 <= mask <= 31 or mask & used:
            raise ValueError("Masks must be disjoint selections of the five positions")
        _validate_rgb(rgb)
        used |= mask
        layers.append(_steady_layer(mask, rgb))
    return _encode_layers(layers)


def build_whole_point_upload_frames(
    background_rgb: Sequence[int], point_mask: int, point_rgb: Sequence[int]
) -> tuple[bytes, ...]:
    """Compose a steady Whole background and a higher-priority Point layer.

    Physically verified: blue background, mask1 red, all other positions blue.
    Every panel gets the same composition; this cannot preserve a per-panel
    color map from another mode. Other valid masks/colors are not all tested.
    Activation is separate and there is no I/O or HA transport registration.
    """
    if type(point_mask) is not int or not 1 <= point_mask <= 31:
        raise ValueError("point_mask must select one or more of the five positions")
    _validate_rgb(background_rgb)
    _validate_rgb(point_rgb)
    return _encode_layers([
        _steady_layer(31, background_rgb, whole=True, priority=1),
        _steady_layer(point_mask, point_rgb, whole=False, priority=0),
    ])
