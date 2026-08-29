"""Regression tests for the physically read H6069 shape topology."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import sys
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "govee_led_control"
spec = importlib.util.spec_from_file_location(
    "govee_led_control_h6069_topology_test", COMPONENT / "h6069_topology.py"
)
assert spec is not None and spec.loader is not None
topology_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = topology_module
spec.loader.exec_module(topology_module)

CAPTURED_PT = (
    "uwB8sgAoALQgBAogAgggCAMgCAQgAgQgBAkgCAIgCAIgAQYgCAEgAgAgAQIgCAIg"
    "BAkgAQwgBAEgCAAgAgEgAQAgCAIgCAAgAgAgAQAgAQQgBAEgBAIgAQYgAgAgBAgg"
    "CAQgCAYgAQQgAQwgAgggBAIgAgggCAAgBAAgBAggAgDr"
)

EXPECTED_COORDINATES = (
    (4, 7), (5, 7), (6, 7), (6, 6), (7, 6), (7, 5), (7, 4), (7, 3),
    (7, 2), (6, 2), (6, 3), (7, 1), (6, 1), (5, 1), (4, 1), (3, 1),
    (2, 1), (4, 0), (5, 0), (5, 2), (5, 3), (6, 5), (7, 7), (3, 7),
    (2, 7), (1, 7), (1, 6), (0, 6), (1, 5), (0, 5), (0, 4), (0, 3),
    (0, 2), (0, 1), (0, 0), (1, 0), (2, 0), (1, 2), (1, 4), (1, 3),
)


class H6069TopologyTests(unittest.TestCase):
    def test_captured_shape_decodes_to_all_40_proven_coordinates(self) -> None:
        topology = topology_module.decode_topology_pt(CAPTURED_PT)
        self.assertEqual(40, topology.panel_count)
        self.assertEqual((8, 8), (topology.width, topology.height))
        self.assertEqual(
            EXPECTED_COORDINATES,
            tuple((panel.x, panel.y) for panel in topology.placements),
        )
        self.assertEqual(40, len(set(EXPECTED_COORDINATES)))
        self.assertEqual(39, len(topology.links))

    def test_number_grid_matches_the_govee_shape_recognition_screen(self) -> None:
        topology = topology_module.decode_topology_pt(CAPTURED_PT)
        self.assertEqual(
            (
                (34, 35, 36, None, 17, 18, None, None),
                (33, None, 16, 15, 14, 13, 12, 11),
                (32, 37, None, None, None, 19, 9, 8),
                (31, 39, None, None, None, 20, 10, 7),
                (30, 38, None, None, None, None, None, 6),
                (29, 28, None, None, None, None, 21, 5),
                (27, 26, None, None, None, None, 3, 4),
                (None, 25, 24, 23, 0, 1, 2, 22),
            ),
            topology.number_grid,
        )
        self.assertIn("34 35 36    17 18", topology.grid_text)
        self.assertIn("   25 24 23 00 01 02 22", topology.grid_text)

    def test_status_json_is_read_only_and_round_trips(self) -> None:
        response = json.dumps(
            {"msg": {"cmd": "status", "data": {"pt": CAPTURED_PT}}}
        ).encode()
        self.assertEqual(40, topology_module.parse_status_datagram(response).panel_count)
        self.assertEqual(
            b'{"msg":{"cmd":"status","data":{}}}',
            topology_module.build_status_datagram(),
        )

    def test_corrupt_or_unknown_shapes_are_rejected(self) -> None:
        blob = bytearray(base64.b64decode(CAPTURED_PT))
        blob[-1] ^= 0x01
        with self.assertRaisesRegex(
            topology_module.H6069TopologyError, "checksum"
        ):
            topology_module.decode_topology_blob(bytes(blob))

        with self.assertRaises(topology_module.H6069TopologyError):
            topology_module.parse_status_datagram(
                b'{"msg":{"cmd":"devStatus","data":{}}}'
            )


if __name__ == "__main__":
    unittest.main()
