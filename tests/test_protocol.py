"""Unit tests for the dependency-free H70B3 protocol encoder."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys
import types
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "govee_led_control"
PACKAGE = "govee_led_control_h70b3_test"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", COMPONENT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType(PACKAGE)
package.__path__ = [str(COMPONENT)]
sys.modules[PACKAGE] = package
_load("const", "const.py")
protocol = _load("h70b3_protocol", "h70b3_protocol.py")


class ProtocolTests(unittest.TestCase):
    def test_png_is_rgb_20_by_26(self) -> None:
        colors = [(0, 0, 0)] * protocol.PIXEL_COUNT
        png = protocol.encode_png(colors)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(png[12:16], b"IHDR")
        width, height = struct.unpack(">II", png[16:24])
        self.assertEqual((width, height), (20, 26))
        self.assertEqual(png[24:27], bytes((8, 2, 0)))

    def test_verified_x_contains_both_diagonals(self) -> None:
        colors = protocol.make_x_demo()
        self.assertEqual(len(colors), 520)
        self.assertEqual(colors[0], (255, 0, 0))
        self.assertEqual(colors[19], (0, 0, 255))
        self.assertEqual(colors[25 * 20], (0, 0, 255))
        self.assertEqual(colors[25 * 20 + 19], (255, 0, 0))

    def test_packets_are_bounded_and_checksum_valid(self) -> None:
        colors = tuple(
            ((index * 17) % 256, (index * 31) % 256, (index * 47) % 256)
            for index in range(520)
        )
        packets = protocol.build_upload_packets(colors)
        self.assertGreater(len(packets), 2)
        self.assertTrue(all(len(packet) <= 137 for packet in packets))
        self.assertTrue(all(protocol.checksum_valid(packet) for packet in packets))
        self.assertEqual(packets[0][:4], bytes((0xA4, 0, 0, 1)))
        self.assertEqual(packets[-1][:3], bytes((0xA4, 0xFF, 0xFF)))

    def test_packetizer_supports_minimum_ble_write_size(self) -> None:
        colors = tuple(
            ((index * 17) % 256, (index * 31) % 256, (index * 47) % 256)
            for index in range(520)
        )
        packets = protocol.build_upload_packets(colors, packet_size=20)
        self.assertGreater(len(packets), 20)
        self.assertTrue(all(len(packet) <= 20 for packet in packets))
        self.assertTrue(all(protocol.checksum_valid(packet) for packet in packets))

    def test_orientation_markers_have_unique_protocol_corners(self) -> None:
        colors = protocol.make_orientation_demo()
        self.assertEqual(colors[0], (255, 0, 0))
        self.assertEqual(colors[19], (0, 255, 0))
        self.assertEqual(colors[25 * 20], (0, 0, 255))
        self.assertEqual(colors[25 * 20 + 19], (255, 255, 255))

    def test_mirror_transforms_keep_logical_coordinates_stable(self) -> None:
        colors = [(0, 0, 0)] * 520
        colors[0] = (255, 0, 0)
        horizontal = protocol.transform_frame(
            colors, flip_horizontal=True, flip_vertical=False
        )
        vertical = protocol.transform_frame(
            colors, flip_horizontal=False, flip_vertical=True
        )
        both = protocol.transform_frame(
            colors, flip_horizontal=True, flip_vertical=True
        )
        self.assertEqual(horizontal[19], (255, 0, 0))
        self.assertEqual(vertical[25 * 20], (255, 0, 0))
        self.assertEqual(both[25 * 20 + 19], (255, 0, 0))

    def test_validation_rejects_wrong_frame_or_color(self) -> None:
        with self.assertRaises(ValueError):
            protocol.encode_png([(0, 0, 0)])
        with self.assertRaises(ValueError):
            protocol.parse_color("#xyzxyz")
        with self.assertRaises(ValueError):
            protocol.parse_color([0, 1, 999])

    def test_hex_and_rgb_color_inputs(self) -> None:
        self.assertEqual(protocol.parse_color("#12aBf0"), (0x12, 0xAB, 0xF0))
        self.assertEqual(protocol.parse_color([1, 2, 3]), (1, 2, 3))


if __name__ == "__main__":
    unittest.main()
