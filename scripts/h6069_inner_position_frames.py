"""Encode the verified steady H6069 internal-position effect, without I/O.

Masks select positions on every panel: 1 TL, 2 TR, 4 BR, 8 BL, 16 center.
There is no panel ID in this program. At most three disjoint color groups.
Activation must be supplied separately for the chosen effect slot.
"""

from __future__ import annotations

from typing import Sequence


def _checked(body: bytes) -> bytes:
    checksum = 0
    for value in body:
        checksum ^= value
    return body + bytes((checksum,))


def build_upload_frames(groups: Sequence[tuple[int, Sequence[int]]]) -> tuple[bytes, ...]:
    """Build A3/58 upload frames; no activation, Bluetooth or LAN writes.

    Three groups (1, red), (2, green), (4, blue) were physically verified
    steady for a minute. Other masks/colors are encodable, not all tested.
    Unselected internal positions are dark in that verified program.
    """
    if not 1 <= len(groups) <= 3:
        raise ValueError("The app supports one to three effect layers")
    layers = bytearray()
    used = 0
    for mask, rgb in groups:
        if type(mask) is not int or not 1 <= mask <= 31 or mask & used:
            raise ValueError("Masks must be disjoint selections of the five positions")
        if len(rgb) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in rgb):
            raise ValueError("RGB must contain three integers in 0..255")
        used |= mask
        # Movement: no entrance/exit or fade, one color, width50, no black
        # gap, fixed brightness100. Layer direction1 is the app default.
        action = bytes((0, 0, 0, 0, 0, 0, 1)) + bytes(rgb) + bytes((50, 0, 0, 100, 100))
        body = mask.to_bytes(2, "big") + bytes((0, 1, 0)) + bytes(4)
        body += bytes((0,)) + len(action).to_bytes(2, "little") + action
        layers += bytes((0, 50)) + len(body).to_bytes(2, "little") + body
    payload = bytes((100, 0, len(groups))) + layers
    chunks = [payload[:14]] + [payload[i:i + 17] for i in range(14, len(payload), 17)]
    frames = [_checked(bytes((0xA3, 0, 1, len(chunks), 0x58)) + chunks[0].ljust(14, b"\x00"))]
    for index, chunk in enumerate(chunks[1:], 1):
        frame_index = 0xFF if index == len(chunks) - 1 else index
        frames.append(_checked(bytes((0xA3, frame_index)) + chunk.ljust(17, b"\x00")))
    return tuple(frames)
