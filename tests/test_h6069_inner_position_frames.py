"""Check the exact physically verified upload and its selection boundaries."""

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "inner_position_reference", Path(__file__).parents[1] / "scripts/h6069_inner_position_frames.py"
)
assert spec and spec.loader
protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protocol)


class InnerPositionFrameTests(unittest.TestCase):
    def test_exact_physically_verified_moving_intersection(self):
        frames = protocol.build_spatial_intersection_upload_frames((0, 0, 255), (255, 0, 0))
        expected = (
            "a30001065864000302321b00001f0101000000af",
            "a3010000000f00000000000000010000ff320061",
            "a30200646401191b0000010001000000000000a2",
            "a3030f0000000000000001ff0000010800646458",
            "a30400191b00000100030000000000000f0000a8",
            "a3ff0000000000010000ff0801006464000000ab",
        )
        self.assertEqual(tuple(bytes.fromhex(f) for f in expected), frames)

    def test_intersection_retains_background_and_foreground_channels(self):
        frames = protocol.build_spatial_intersection_upload_frames((12, 34, 56), (78, 90, 123))
        payload = frames[0][5:19] + b"".join(f[2:19] for f in frames[1:])
        self.assertEqual(2, payload.count(bytes((12, 34, 56))))
        self.assertEqual(1, payload.count(bytes((78, 90, 123))))
        self.assertEqual(3, payload[2])
        for background, point in (((0, 0), (0, 0, 0)), ((0, 0, 0), (256, 0, 0))):
            with self.assertRaises(ValueError):
                protocol.build_spatial_intersection_upload_frames(background, point)

    def test_exact_physically_verified_whole_point_overlay(self):
        frames = protocol.build_whole_point_upload_frames((0, 0, 255), 1, (255, 0, 0))
        expected = (
            "a30001045864000201321b00001f0101000000af",
            "a3010000000f00000000000000010000ff320061",
            "a30200646400321b000001000100000000000088",
            "a3ff0f0000000000000001ff000032000064649f",
        )
        self.assertEqual(tuple(bytes.fromhex(f) for f in expected), frames)

    def test_overlay_rejects_invalid_selection_and_background(self):
        for mask in (0, 32, -1, True):
            with self.subTest(mask=mask), self.assertRaises(ValueError):
                protocol.build_whole_point_upload_frames((0, 0, 255), mask, (255, 0, 0))
        for background, point in (((0, 0), (0, 0, 0)), ((0, 0, 256), (0, 0, 0)),
                                  ((0, 0, 0), (0, -1, 0)), ((0, 0, 0), (0, 0, True))):
            with self.subTest(background=background, point=point), self.assertRaises(ValueError):
                protocol.build_whole_point_upload_frames(background, 1, point)

    def test_exact_physically_verified_three_color_program(self):
        frames = protocol.build_upload_frames([(1, (255, 0, 0)), (2, (0, 255, 0)), (4, (0, 0, 255))])
        expected = (
            "a30001065864000300321b0000010001000000b2",
            "a3010000000f0000000000000001ff0000320061",
            "a30200646400321b00000200010000000000008b",
            "a3030f000000000000000100ff00320000646463",
            "a30400321b00000400010000000000000f000084",
            "a3ff0000000000010000ff320000646400000090",
        )
        self.assertEqual(tuple(bytes.fromhex(f) for f in expected), frames)

    def test_short_program_has_closing_frame_and_valid_checksums(self):
        frames = protocol.build_upload_frames([(24, (12, 34, 56))])
        self.assertEqual(len(frames), frames[0][3])
        self.assertEqual(255, frames[-1][1])
        for frame in frames:
            self.assertEqual(20, len(frame))
            checksum = 0
            for value in frame:
                checksum ^= value
            self.assertEqual(0, checksum)
        payload = frames[0][5:19] + b"".join(f[2:19] for f in frames[1:])
        self.assertEqual(b"\x00\x18", payload[7:9])
        self.assertIn(bytes((12, 34, 56)), payload)

    def test_ambiguous_masks_invalid_colors_and_excess_layers_rejected(self):
        invalid = ([], [(1, (0, 0, 0))] * 4, [(0, (0, 0, 0))],
                   [(32, (0, 0, 0))], [(3, (0, 0, 0)), (2, (0, 0, 0))],
                   [(True, (0, 0, 0))], [(1, (0, 256, 0))], [(1, (0, 0))])
        for groups in invalid:
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                protocol.build_upload_frames(groups)
