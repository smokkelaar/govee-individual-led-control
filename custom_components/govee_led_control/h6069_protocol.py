"""Pure-Python encoder for the reverse-engineered H6069 LAN protocol."""

from __future__ import annotations

import base64
from collections import OrderedDict
import json
from typing import Iterable, Sequence

RGB = tuple[int, int, int]

_A3_HEADER = bytes((0x01, 0x06, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00))
_A3_DATA_BYTES_PER_FRAME = 17
_ACTIVATE_BODY = bytes(
    (0x33, 0x05, 0x0A, 0x20, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00,
     0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
)


def _validate_rgb(rgb: Sequence[int]) -> RGB:
    """Validate and normalize one RGB tuple."""
    if len(rgb) != 3:
        raise ValueError("RGB colors must contain exactly three values")
    values = tuple(int(value) for value in rgb)
    if any(value < 0 or value > 255 for value in values):
        raise ValueError("RGB values must be between 0 and 255")
    return values  # type: ignore[return-value]


def add_xor_checksum(body: bytes) -> bytes:
    """Append the Govee XOR checksum to a 19-byte frame body."""
    if len(body) != 19:
        raise ValueError("A Govee frame body must be exactly 19 bytes")
    checksum = 0
    for value in body:
        checksum ^= value
    return body + bytes((checksum,))


def encode_grouped_payload(colors: Sequence[Sequence[int]]) -> bytes:
    """Encode every panel exactly once, grouped by identical RGB color."""
    if not colors:
        raise ValueError("At least one panel is required")
    if len(colors) > 255:
        raise ValueError("The one-byte panel identifiers support at most 255 panels")

    groups: OrderedDict[RGB, list[int]] = OrderedDict()
    for panel_id, raw_rgb in enumerate(colors):
        rgb = _validate_rgb(raw_rgb)
        groups.setdefault(rgb, []).append(panel_id)

    if len(groups) > 255:
        raise ValueError("The one-byte group count supports at most 255 groups")

    payload = bytearray(_A3_HEADER)
    payload.append(len(groups))
    for rgb, panel_ids in groups.items():
        payload.append(len(panel_ids))
        payload.extend(rgb)
        payload.extend(panel_ids)
    return bytes(payload)


def decode_grouped_payload(payload: bytes, panel_count: int) -> tuple[RGB, ...]:
    """Decode a grouped payload for validation and diagnostics."""
    if len(payload) < 10 or payload[:9] != _A3_HEADER:
        raise ValueError("Invalid H6069 grouped-payload header")

    result: list[RGB | None] = [None] * panel_count
    group_count = payload[9]
    offset = 10
    for _ in range(group_count):
        if offset + 4 > len(payload):
            raise ValueError("Truncated color group")
        member_count = payload[offset]
        rgb: RGB = (payload[offset + 1], payload[offset + 2], payload[offset + 3])
        offset += 4
        if offset + member_count > len(payload):
            raise ValueError("Truncated panel-id list")
        for panel_id in payload[offset : offset + member_count]:
            if panel_id >= panel_count:
                raise ValueError(f"Panel id {panel_id} exceeds panel count")
            if result[panel_id] is not None:
                raise ValueError(f"Panel id {panel_id} occurs more than once")
            result[panel_id] = rgb
        offset += member_count

    if offset != len(payload):
        raise ValueError("Unexpected trailing bytes in grouped payload")
    missing = [index for index, rgb in enumerate(result) if rgb is None]
    if missing:
        raise ValueError(f"Missing panel ids: {missing}")
    return tuple(rgb for rgb in result if rgb is not None)


def encode_a3_frames(payload: bytes) -> tuple[bytes, ...]:
    """Split grouped data over indexed A3 frames."""
    if not payload:
        raise ValueError("The grouped payload cannot be empty")

    chunks = [
        payload[offset : offset + _A3_DATA_BYTES_PER_FRAME]
        for offset in range(0, len(payload), _A3_DATA_BYTES_PER_FRAME)
    ]
    frames: list[bytes] = []
    for index, chunk in enumerate(chunks):
        frame_index = 0xFF if index == len(chunks) - 1 else index
        if frame_index != 0xFF and frame_index > 0xFE:
            raise ValueError("The pattern requires too many A3 frames")
        body = bytearray(19)
        body[0] = 0xA3
        body[1] = frame_index
        body[2 : 2 + len(chunk)] = chunk
        frames.append(add_xor_checksum(bytes(body)))
    return tuple(frames)


def build_pattern_frames(colors: Sequence[Sequence[int]]) -> tuple[bytes, ...]:
    """Build the A3 upload followed by the captured static-pattern activation."""
    payload = encode_grouped_payload(colors)
    return encode_a3_frames(payload) + (add_xor_checksum(_ACTIVATE_BODY),)


def build_ptreal_datagram(colors: Sequence[Sequence[int]]) -> bytes:
    """Wrap a complete pattern in the Govee LAN ptReal JSON envelope."""
    commands = [base64.b64encode(frame).decode("ascii") for frame in build_pattern_frames(colors)]
    message = {"msg": {"cmd": "ptReal", "data": {"command": commands}}}
    return json.dumps(message, separators=(",", ":")).encode("utf-8")


def verify_frame_checksums(frames: Iterable[bytes]) -> bool:
    """Return True when every supplied 20-byte frame has a valid XOR checksum."""
    for frame in frames:
        if len(frame) != 20:
            return False
        checksum = 0
        for value in frame[:19]:
            checksum ^= value
        if checksum != frame[19]:
            return False
    return True

