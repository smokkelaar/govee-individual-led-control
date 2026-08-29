"""Validate H6069 Shape Recognition data and probe read-only LAN status.

The long topology format was established against a real 40-panel installation.
The tested firmware's normal ``status.pt`` reply is only short runtime state,
so a live query is explicitly best-effort and a captured long value can be
imported. Both routes use the same strict decoder so unknown firmware data is
never presented as a correct map.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import socket
import time
from typing import Any

STATUS_LISTEN_PORT = 4002
DEVICE_PORT = 4003
MULTICAST_GROUP = "239.255.255.250"

_STATUS_HEADER_PREFIX = bytes((0xBB, 0x00, 0x7C, 0xB2, 0x00))
_RECORD_PREFIX = 0x20
_SIDE_ORDER = (0x01, 0x02, 0x04, 0x08)
_WORLD_VECTORS = ((0, -1), (1, 0), (0, 1), (-1, 0))


class H6069TopologyError(ValueError):
    """Raised when status data cannot be trusted as a panel topology."""


class H6069TopologyQueryError(RuntimeError):
    """Raised when a read-only topology query cannot be completed."""


@dataclass(frozen=True, slots=True)
class H6069PanelPlacement:
    """One protocol-indexed panel in normalized grid coordinates."""

    panel_id: int
    x: int
    y: int
    parent_id: int | None
    parent_side: int | None
    input_side: int
    child_sides: tuple[int, ...]
    rotation_degrees: int


@dataclass(frozen=True, slots=True)
class H6069Topology:
    """Validated physical panel tree and its derived rectangular grid."""

    placements: tuple[H6069PanelPlacement, ...]
    width: int
    height: int
    fingerprint: str
    source: str = "read-only local LAN status.pt"

    @property
    def panel_count(self) -> int:
        """Return the number of decoded panels."""
        return len(self.placements)

    @property
    def number_grid(self) -> tuple[tuple[int | None, ...], ...]:
        """Return row-major protocol IDs with ``None`` for empty cells."""
        grid: list[list[int | None]] = [
            [None for _ in range(self.width)] for _ in range(self.height)
        ]
        for panel in self.placements:
            grid[panel.y][panel.x] = panel.panel_id
        return tuple(tuple(row) for row in grid)

    @property
    def grid_text(self) -> str:
        """Return a dashboard-friendly monospace representation."""
        digits = max(2, len(str(max(0, self.panel_count - 1))))
        blank = " " * digits
        return "\n".join(
            " ".join(blank if value is None else f"{value:0{digits}d}" for value in row)
            for row in self.number_grid
        ).rstrip()

    @property
    def links(self) -> tuple[dict[str, int], ...]:
        """Return parent/child edges for diagnostics and richer frontends."""
        return tuple(
            {
                "parent": panel.parent_id,
                "child": panel.panel_id,
                "parent_side": panel.parent_side,
                "child_input_side": panel.input_side,
            }
            for panel in self.placements
            if panel.parent_id is not None and panel.parent_side is not None
        )

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return JSON-safe data suitable for a Home Assistant sensor."""
        return {
            "source": self.source,
            "protocol_indexing": "zero-based",
            "root_panel": 0,
            "power_input_side": self.placements[0].input_side,
            "width": self.width,
            "height": self.height,
            "fingerprint": self.fingerprint,
            "grid_text": self.grid_text,
            "number_grid": [list(row) for row in self.number_grid],
            "panels": [
                {
                    "id": panel.panel_id,
                    "x": panel.x,
                    "y": panel.y,
                    "parent": panel.parent_id,
                    "input_side": panel.input_side,
                    "rotation_degrees": panel.rotation_degrees,
                }
                for panel in self.placements
            ],
            "links": list(self.links),
        }


@dataclass(frozen=True, slots=True)
class _PanelRecord:
    input_side: int
    child_mask: int

    @property
    def child_sides(self) -> tuple[int, ...]:
        return tuple(side for side in _SIDE_ORDER if self.child_mask & side)


def build_status_datagram() -> bytes:
    """Build the standard read-only Govee LAN shape/status request."""
    return b'{"msg":{"cmd":"status","data":{}}}'


def _xor_valid(data: bytes) -> bool:
    checksum = 0
    for value in data:
        checksum ^= value
    return checksum == 0


def _side_index(side: int) -> int:
    try:
        return _SIDE_ORDER.index(side)
    except ValueError as err:
        raise H6069TopologyError(f"invalid local side 0x{side:02x}") from err


def _vector_index(vector: tuple[int, int]) -> int:
    try:
        return _WORLD_VECTORS.index(vector)
    except ValueError as err:
        raise H6069TopologyError(f"invalid world direction {vector!r}") from err


def _mapping_for_input(
    input_side: int, world_direction_to_parent: tuple[int, int]
) -> tuple[tuple[int, int], ...]:
    """Rotate the local clockwise side cycle onto one known world edge."""
    rotation = (
        _vector_index(world_direction_to_parent) - _side_index(input_side)
    ) % 4
    return tuple(_WORLD_VECTORS[(index + rotation) % 4] for index in range(4))


def decode_topology_blob(blob: bytes) -> H6069Topology:
    """Decode one checksum-valid ``status.pt`` binary topology."""
    if len(blob) < 12:
        raise H6069TopologyError("topology blob is too short")
    if blob[:5] != _STATUS_HEADER_PREFIX:
        raise H6069TopologyError("unknown H6069 topology header")
    if blob[6:8] != bytes((0x00, 0xB4)):
        raise H6069TopologyError("unknown H6069 topology header variant")
    if not _xor_valid(blob):
        raise H6069TopologyError("invalid topology XOR checksum")

    panel_count = blob[5]
    if not 1 <= panel_count <= 70:
        raise H6069TopologyError(f"invalid panel count {panel_count}")
    expected_length = 8 + panel_count * 3 + 1
    if len(blob) != expected_length:
        raise H6069TopologyError(
            f"topology has {len(blob)} bytes; expected {expected_length}"
        )

    records: list[_PanelRecord] = []
    for panel_id in range(panel_count):
        offset = 8 + panel_id * 3
        prefix, input_side, child_mask = blob[offset : offset + 3]
        if prefix != _RECORD_PREFIX:
            raise H6069TopologyError(
                f"panel {panel_id} has unknown record prefix 0x{prefix:02x}"
            )
        _side_index(input_side)
        if child_mask & ~0x0F:
            raise H6069TopologyError(
                f"panel {panel_id} has invalid child mask 0x{child_mask:02x}"
            )
        if child_mask & input_side:
            raise H6069TopologyError(
                f"panel {panel_id} uses its input side as an output"
            )
        records.append(_PanelRecord(input_side, child_mask))

    edge_count = sum(len(record.child_sides) for record in records)
    if edge_count != panel_count - 1:
        raise H6069TopologyError(
            f"topology has {edge_count} links for {panel_count} panels"
        )

    # Panel IDs are serialized as a depth-first preorder traversal.  A panel's
    # local sides form the clockwise cycle 1,2,4,8.  Once the input edge is
    # known, all four world directions and every child coordinate are fixed.
    raw: list[dict[str, Any] | None] = [None] * panel_count
    occupied: dict[tuple[int, int], int] = {}
    next_id = 1

    root = records[0]
    root_mapping = _mapping_for_input(root.input_side, (0, 1))

    def visit(
        panel_id: int,
        coordinate: tuple[int, int],
        mapping: tuple[tuple[int, int], ...],
        parent_id: int | None,
        parent_side: int | None,
    ) -> None:
        nonlocal next_id
        if coordinate in occupied:
            other = occupied[coordinate]
            raise H6069TopologyError(
                f"panels {other} and {panel_id} occupy the same grid cell"
            )
        occupied[coordinate] = panel_id
        record = records[panel_id]
        rotation = (
            _vector_index(mapping[0]) - _vector_index(_WORLD_VECTORS[0])
        ) % 4
        raw[panel_id] = {
            "panel_id": panel_id,
            "coordinate": coordinate,
            "parent_id": parent_id,
            "parent_side": parent_side,
            "input_side": record.input_side,
            "child_sides": record.child_sides,
            "rotation_degrees": rotation * 90,
        }

        for local_side in record.child_sides:
            if next_id >= panel_count:
                raise H6069TopologyError("tree contains more children than panels")
            child_id = next_id
            next_id += 1
            vector = mapping[_side_index(local_side)]
            child_coordinate = (
                coordinate[0] + vector[0],
                coordinate[1] + vector[1],
            )
            child_record = records[child_id]
            child_mapping = _mapping_for_input(
                child_record.input_side, (-vector[0], -vector[1])
            )
            visit(
                child_id,
                child_coordinate,
                child_mapping,
                panel_id,
                local_side,
            )

    visit(0, (0, 0), root_mapping, None, None)
    if next_id != panel_count or any(item is None for item in raw):
        raise H6069TopologyError("tree did not consume every panel record")

    coordinates = [item["coordinate"] for item in raw if item is not None]
    min_x = min(x for x, _ in coordinates)
    max_x = max(x for x, _ in coordinates)
    min_y = min(y for _, y in coordinates)
    max_y = max(y for _, y in coordinates)
    placements = tuple(
        H6069PanelPlacement(
            panel_id=item["panel_id"],
            x=item["coordinate"][0] - min_x,
            y=item["coordinate"][1] - min_y,
            parent_id=item["parent_id"],
            parent_side=item["parent_side"],
            input_side=item["input_side"],
            child_sides=item["child_sides"],
            rotation_degrees=item["rotation_degrees"],
        )
        for item in raw
        if item is not None
    )
    return H6069Topology(
        placements=placements,
        width=max_x - min_x + 1,
        height=max_y - min_y + 1,
        fingerprint=hashlib.sha256(blob).hexdigest()[:16],
    )


def decode_topology_pt(
    encoded: str, *, source: str = "read-only local LAN status.pt"
) -> H6069Topology:
    """Decode the Base64 ``pt`` value from a Govee status response."""
    try:
        blob = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as err:
        raise H6069TopologyError("status.pt is not valid Base64") from err
    topology = decode_topology_blob(blob)
    return H6069Topology(
        placements=topology.placements,
        width=topology.width,
        height=topology.height,
        fingerprint=topology.fingerprint,
        source=source,
    )


def parse_status_datagram(datagram: bytes | str) -> H6069Topology:
    """Validate a Govee ``status`` JSON response and decode its shape."""
    try:
        message = json.loads(datagram)
        inner = message["msg"]
        if inner["cmd"] != "status":
            raise H6069TopologyError("datagram is not a status response")
        encoded = inner["data"]["pt"]
        if not isinstance(encoded, str) or not encoded:
            raise H6069TopologyError("status response has no topology pt value")
    except H6069TopologyError:
        raise
    except (json.JSONDecodeError, KeyError, TypeError) as err:
        raise H6069TopologyError("invalid Govee status response") from err
    return decode_topology_pt(encoded)


def query_topology(host: str, timeout: float = 5.0) -> H6069Topology:
    """Request and receive one topology without changing visible light state."""
    deadline = time.monotonic() + timeout
    memberships: list[bytes] = []
    last_topology_error: H6069TopologyError | None = None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            reuse_port = getattr(socket, "SO_REUSEPORT", None)
            if reuse_port is not None:
                try:
                    udp_socket.setsockopt(socket.SOL_SOCKET, reuse_port, 1)
                except OSError:
                    pass
            udp_socket.bind(("0.0.0.0", STATUS_LISTEN_PORT))

            # H6069 sends ``status`` replies to the Govee multicast group on
            # port 4002. Binding the port alone is not sufficient on Linux:
            # the kernel drops multicast traffic until the socket joins the
            # group. Join both the route-selected interface and the default
            # interface so this also works on multi-homed Home Assistant hosts.
            route_interface = "0.0.0.0"
            try:
                with socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM
                ) as route_socket:
                    route_socket.connect((host, DEVICE_PORT))
                    route_interface = str(route_socket.getsockname()[0])
            except OSError:
                pass
            for interface in (route_interface, "0.0.0.0"):
                membership = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton(
                    interface
                )
                if membership in memberships:
                    continue
                try:
                    udp_socket.setsockopt(
                        socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership
                    )
                except OSError:
                    continue
                memberships.append(membership)
            if not memberships:
                raise OSError("could not join the Govee multicast group")

            udp_socket.sendto(build_status_datagram(), (host, DEVICE_PORT))

            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                udp_socket.settimeout(remaining)
                datagram, sender = udp_socket.recvfrom(65535)
                if sender[0] != host:
                    continue
                try:
                    return parse_status_datagram(datagram)
                except H6069TopologyError as err:
                    # A concurrent devStatus query can answer from the same IP.
                    # Keep waiting only until this request's fixed deadline.
                    last_topology_error = err
                    continue
    except (OSError, TimeoutError) as err:
        detail = str(err).strip() or "timeout"
        if last_topology_error is not None:
            detail = (
                "device answered, but status.pt did not contain a panel topology: "
                f"{last_topology_error}"
            )
        raise H6069TopologyQueryError(
            f"no valid H6069 topology response from {host}: {detail}"
        ) from err
