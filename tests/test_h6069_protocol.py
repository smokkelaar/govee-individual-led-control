"""Regression tests for the physically verified H6069 LAN encoder."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "govee_led_control"
spec = importlib.util.spec_from_file_location(
    "govee_led_control_h6069_protocol_test", COMPONENT / "h6069_protocol.py"
)
assert spec is not None and spec.loader is not None
protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protocol)


class H6069ProtocolTests(unittest.TestCase):
    def test_round_trip_all_40_panel_ids(self) -> None:
        colors = tuple(
            ((index * 17) % 256, (index * 29) % 256, (index * 43) % 256)
            for index in range(40)
        )
        payload = protocol.encode_grouped_payload(colors)
        self.assertEqual(colors, protocol.decode_grouped_payload(payload, 40))

    def test_ptreal_wrapper_contains_checksum_valid_frames(self) -> None:
        datagram = protocol.build_ptreal_datagram([(255, 255, 255)] * 40)
        decoded = json.loads(datagram)
        commands = decoded["msg"]["data"]["command"]
        frames = tuple(base64.b64decode(command) for command in commands)
        self.assertEqual("ptReal", decoded["msg"]["cmd"])
        self.assertTrue(protocol.verify_frame_checksums(frames))

    def test_exact_physically_proven_panel_five_vector(self) -> None:
        colors = [(0, 0, 255)] * 40
        colors[5] = (255, 0, 0)
        decoded = json.loads(protocol.build_ptreal_datagram(colors))
        self.assertEqual(
            [
                "owABBAMAAAAAAAACJwAA/wABAnw=",
                "owEDBAYHCAkKCwwNDg8QERITFLA=",
                "owIVFhcYGRobHB0eHyAhIiMkJbQ=",
                "o/8mJwH/AAAFAAAAAAAAAAAAAKY=",
                "MwUKIAMAAAAAAAAAAAAAAAAAAB8=",
            ],
            decoded["msg"]["data"]["command"],
        )

    def test_invalid_frames_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            protocol.encode_grouped_payload([])
        with self.assertRaises(ValueError):
            protocol.encode_grouped_payload([(0, 0, 999)])

    def test_upload_count_matches_solid_demo_and_rainbow(self) -> None:
        patterns = (
            ([(255, 255, 255)] * 40, 4),
            ([(255, 0, 0)] + [(0, 0, 255)] * 39, 4),
            ([(i, 255 - i, i * 3) for i in range(40)], 13),
        )
        for colors, expected_count in patterns:
            with self.subTest(count=expected_count):
                frames = protocol.build_pattern_frames(colors)
                self.assertEqual(expected_count, len(frames) - 1)
                self.assertEqual(expected_count, frames[0][3])
                self.assertEqual(0, frames[0][1])
                self.assertEqual(255, frames[-2][1])
                self.assertTrue(protocol.verify_frame_checksums(frames))

    def test_small_transfer_keeps_start_and_closing_frames(self) -> None:
        frames = protocol.build_pattern_frames([(255, 0, 0)])
        self.assertEqual(3, len(frames))
        self.assertEqual(2, frames[0][3])
        self.assertEqual(0, frames[0][1])
        self.assertEqual(255, frames[1][1])
        self.assertTrue(protocol.verify_frame_checksums(frames))


if __name__ == "__main__":
    unittest.main()
