"""Pure-Python encoder for H70B3 20x26 DIY images and BLE MTU packets."""

from __future__ import annotations

import binascii
import struct
import zlib
from collections.abc import Sequence

from .const import H70B3_HEIGHT as HEIGHT, H70B3_PIXEL_COUNT as PIXEL_COUNT, H70B3_WIDTH as WIDTH

DEFAULT_MTU_PACKET_SIZE = 137
RGB = tuple[int, int, int]

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_A4 = 0xA4
_DIY_IMAGE_COMMAND = 0x58
_PROTOCOL_CODE = 0x5F
_PAINTING_LAYER_TYPE = 0x00
_PAINTING_LAYER_TRAILER = bytes.fromhex("00 00 64 01 F4 01 00 00")


def validate_rgb(raw: Sequence[int]) -> RGB:
    """Validate and normalize one RGB color."""
    if len(raw) != 3:
        raise ValueError("each color must contain exactly three RGB values")
    rgb = tuple(int(value) for value in raw)
    if any(value < 0 or value > 255 for value in rgb):
        raise ValueError("RGB values must be between 0 and 255")
    return rgb  # type: ignore[return-value]


def parse_color(raw: object) -> RGB:
    """Parse either #RRGGBB or a three-item RGB sequence."""
    if isinstance(raw, str):
        value = raw.strip()
        if value.startswith("#"):
            value = value[1:]
        if len(value) != 6:
            raise ValueError(f"invalid hex color: {raw!r}")
        try:
            return tuple(bytes.fromhex(value))  # type: ignore[return-value]
        except ValueError as err:
            raise ValueError(f"invalid hex color: {raw!r}") from err
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        return validate_rgb(raw)
    raise ValueError(f"color must be #RRGGBB or [red, green, blue], got {raw!r}")


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(kind)
    checksum = binascii.crc32(data, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def encode_png(colors: Sequence[Sequence[int]]) -> bytes:
    """Encode 520 row-major RGB values as a minimal standards-compliant PNG."""
    if len(colors) != PIXEL_COUNT:
        raise ValueError(f"an H70B3 frame must contain exactly {PIXEL_COUNT} pixels")

    rows = bytearray()
    for y in range(HEIGHT):
        rows.append(0)
        for x in range(WIDTH):
            rows.extend(validate_rgb(colors[y * WIDTH + x]))

    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return b"".join(
        (
            _PNG_SIGNATURE,
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", zlib.compress(bytes(rows), level=9)),
            _png_chunk(b"IEND", b""),
        )
    )


def build_effect_bytes(
    colors: Sequence[Sequence[int]], *, brightness: int = 100
) -> bytes:
    """Build the protocol-0x5F static painting consumed by command A4/58."""
    if not 1 <= brightness <= 100:
        raise ValueError("brightness must be between 1 and 100")
    png = encode_png(colors)
    if len(png) > 0xFFFF:
        raise ValueError("PNG is too large for the two-byte layer length")

    painting_inner = b"".join(
        (
            bytes((_PAINTING_LAYER_TYPE,)),
            struct.pack("<H", len(png)),
            png,
            _PAINTING_LAYER_TRAILER,
        )
    )
    painting_layer = struct.pack("<H", len(painting_inner)) + painting_inner
    graffiti = b"".join(
        (
            bytes((1, 1, 1, brightness, 0, 0, 1)),
            painting_layer,
            bytes((0,)),
        )
    )
    return bytes((_PROTOCOL_CODE,)) + graffiti


def add_xor_checksum(body: bytes) -> bytes:
    """Append the XOR of all body bytes."""
    checksum = 0
    for value in body:
        checksum ^= value
    return body + bytes((checksum,))


def checksum_valid(frame: bytes) -> bool:
    """Return whether the final byte equals the XOR of all preceding bytes."""
    if not frame:
        return False
    checksum = 0
    for value in frame[:-1]:
        checksum ^= value
    return checksum == frame[-1]


def checked_frame(body: bytes) -> bytes:
    """Pad a short command to 19 bytes and append its XOR checksum."""
    if len(body) > 19:
        raise ValueError("a checksum frame body cannot exceed 19 bytes")
    return add_xor_checksum(body.ljust(19, b"\x00"))


def build_upload_packets(
    colors: Sequence[Sequence[int]],
    *,
    brightness: int = 100,
    packet_size: int = DEFAULT_MTU_PACKET_SIZE,
) -> tuple[bytes, ...]:
    """Wrap a generated image like Govee makeSendBytesMtu(A4, 58, ...)."""
    if packet_size < 20:
        raise ValueError("packet_size must be at least 20 bytes")
    effect = build_effect_bytes(colors, brightness=brightness)
    first_capacity = packet_size - 8
    continuation_capacity = packet_size - 4

    if len(effect) <= first_capacity:
        first = add_xor_checksum(
            bytes((_A4, 0, 0, 1, 2, 0, _DIY_IMAGE_COMMAND)) + effect
        )
        return (first, add_xor_checksum(bytes((_A4, 0xFF, 0xFF))))

    remaining = len(effect) - first_capacity
    remainder = remaining % continuation_capacity
    packet_count = remaining // continuation_capacity + 1 + (1 if remainder else 0)
    packets: list[bytes] = []

    first_body = bytearray(packet_size - 1)
    first_body[:7] = bytes(
        (_A4, 0, 0, 1, packet_count & 0xFF, packet_count >> 8, _DIY_IMAGE_COMMAND)
    )
    first_body[7:] = effect[:first_capacity]
    packets.append(add_xor_checksum(bytes(first_body)))

    for index in range(1, packet_count):
        source_offset = first_capacity + (index - 1) * continuation_capacity
        is_last = index == packet_count - 1
        if is_last:
            payload_length = remainder if remainder else continuation_capacity
            body = bytes((_A4, 0xFF, 0xFF)) + effect[
                source_offset : source_offset + payload_length
            ]
        else:
            body = bytes((_A4, index & 0xFF, index >> 8)) + effect[
                source_offset : source_offset + continuation_capacity
            ]
        packets.append(add_xor_checksum(body))

    return tuple(packets)


def transform_frame(
    colors: Sequence[Sequence[int]],
    *,
    flip_horizontal: bool,
    flip_vertical: bool,
) -> tuple[RGB, ...]:
    """Mirror a logical 20x26 row-major frame for the physical mounting."""
    if len(colors) != PIXEL_COUNT:
        raise ValueError(f"a frame requires exactly {PIXEL_COUNT} colors")
    normalized = tuple(validate_rgb(color) for color in colors)
    if not flip_horizontal and not flip_vertical:
        return normalized
    output: list[RGB] = [(0, 0, 0)] * PIXEL_COUNT
    for logical_y in range(HEIGHT):
        physical_y = HEIGHT - 1 - logical_y if flip_vertical else logical_y
        for logical_x in range(WIDTH):
            physical_x = WIDTH - 1 - logical_x if flip_horizontal else logical_x
            output[physical_y * WIDTH + physical_x] = normalized[
                logical_y * WIDTH + logical_x
            ]
    return tuple(output)


def make_x_demo() -> tuple[RGB, ...]:
    """Return the physical-test pattern: red and blue diagonals on black."""
    colors: list[RGB] = [(0, 0, 0)] * PIXEL_COUNT
    for y in range(HEIGHT):
        x_down = round(y * (WIDTH - 1) / (HEIGHT - 1))
        x_up = WIDTH - 1 - x_down
        colors[y * WIDTH + x_down] = (255, 0, 0)
        colors[y * WIDTH + x_up] = (
            (255, 255, 255) if x_up == x_down else (0, 0, 255)
        )
    return tuple(colors)


def make_orientation_demo() -> tuple[RGB, ...]:
    """Return four unique 3x3 corner markers for physical orientation mapping."""
    colors: list[RGB] = [(0, 0, 0)] * PIXEL_COUNT
    corners = (
        (0, 0, (255, 0, 0)),
        (WIDTH - 3, 0, (0, 255, 0)),
        (0, HEIGHT - 3, (0, 0, 255)),
        (WIDTH - 3, HEIGHT - 3, (255, 255, 255)),
    )
    for start_x, start_y, color in corners:
        for y in range(start_y, start_y + 3):
            for x in range(start_x, start_x + 3):
                colors[y * WIDTH + x] = color
    return tuple(colors)
