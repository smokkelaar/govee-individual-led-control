"""Reference frames for the physically tested 40-panel H6069 Razer channel.

Pure encoding only: no socket, no light output and no Home Assistant registration.
On the tested installation 10 and 40 zones rendered; 41, 80 and 200 did not.
The 40-zone guard describes that installation, not all H6069 firmware versions.
"""

from __future__ import annotations

import base64
import json
from typing import Sequence


def _frame(opcode: int, payload: bytes) -> bytes:
    body = b"\xbb" + len(payload).to_bytes(2, "big") + bytes((opcode,)) + payload
    checksum = 0
    for value in body:
        checksum ^= value
    return body + bytes((checksum,))


def build_enable_frame(enabled: bool) -> bytes:
    """Arm or disarm the stream; an arm can temporarily make the lights dark."""
    if type(enabled) is not bool:
        raise ValueError("enabled must be a boolean")
    return _frame(0xB1, bytes((int(enabled),)))


def build_color_frame(colors: Sequence[Sequence[int]]) -> bytes:
    """Encode hard-edged zones, limited to the tested installation's 40 panels."""
    if not 1 <= len(colors) <= 40:
        raise ValueError("This reference encoder is limited to 1..40 zones")
    rgb = bytearray()
    for color in colors:
        if len(color) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in color):
            raise ValueError("Each color must contain three integers in 0..255")
        rgb.extend(color)
    return _frame(0xB0, bytes((0, len(colors))) + rgb)


def wrap_datagram(frame: bytes) -> bytes:
    """Wrap a valid Razer frame in the LAN JSON envelope."""
    if len(frame) < 5 or frame[0] != 0xBB:
        raise ValueError("Invalid Razer frame header")
    if int.from_bytes(frame[1:3], "big") != len(frame) - 5:
        raise ValueError("Invalid Razer payload length")
    checksum = 0
    for value in frame:
        checksum ^= value
    if checksum:
        raise ValueError("Invalid Razer checksum")
    return json.dumps(
        {"msg": {"cmd": "razer", "data": {"pt": base64.b64encode(frame).decode("ascii")}}}
    ).encode("utf-8")
