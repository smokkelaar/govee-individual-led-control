"""Checks for the separately tested H6069 streaming reference encoder."""

import base64
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "h6069_razer_frames_test", Path(__file__).parents[1] / "scripts" / "h6069_razer_frames.py"
)
assert spec is not None and spec.loader is not None
protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protocol)


class RazerFrameTests(unittest.TestCase):
    def test_enable_and_disable_reference_vectors(self):
        self.assertEqual(bytes.fromhex("bb0001b1010a"), protocol.build_enable_frame(True))
        self.assertEqual(bytes.fromhex("bb0001b1000b"), protocol.build_enable_frame(False))

    def test_forty_zone_identification_preserves_header_and_selected_color(self):
        colors = [(0, 0, 100)] * 40
        colors[5] = (100, 0, 0)
        frame = protocol.build_color_frame(colors)
        self.assertEqual(bytes.fromhex("bb007ab00028"), frame[:6])
        self.assertEqual(127, len(frame))
        self.assertEqual(bytes((100, 0, 0)), frame[21:24])
        self.assertEqual(bytes((0, 0, 100)), frame[24:27])
        message = json.loads(protocol.wrap_datagram(frame))
        self.assertEqual("razer", message["msg"]["cmd"])
        self.assertEqual(frame, base64.b64decode(message["msg"]["data"]["pt"]))

    def test_unproven_counts_and_invalid_rgb_are_rejected(self):
        for colors in ([], [(0, 0, 0)] * 41, [(0, 0)], [(0, -1, 0)], [(256, 0, 0)], [(0.5, 0, 0)]):
            with self.subTest(colors=colors), self.assertRaises(ValueError):
                protocol.build_color_frame(colors)

    def test_corrupted_frames_cannot_be_wrapped(self):
        good = protocol.build_color_frame([(100, 0, 0)])
        for bad in (b"", bytes((0,)) + good[1:], good[:2] + b"\x00" + good[3:], good[:-1] + bytes((good[-1] ^ 1,))):
            with self.subTest(frame=bad), self.assertRaises(ValueError):
                protocol.wrap_datagram(bad)


if __name__ == "__main__":
    unittest.main()
