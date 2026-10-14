"""Geometry checks for the independently probed H6069 focus points."""

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "h6069_effect_coordinates_test",
    Path(__file__).parents[1] / "scripts" / "h6069_effect_coordinates.py",
)
assert spec is not None and spec.loader is not None
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


class EffectCoordinateTests(unittest.TestCase):
    def test_two_physically_checked_points_on_sparse_grid(self):
        grid = [[None] * 8 for _ in range(8)]
        grid[0][0] = 35
        grid[6][6] = 5
        grid[7][7] = 3
        points = geometry.panel_effect_centers(grid)
        self.assertEqual((1516, 1516), points[35])
        self.assertEqual((1660, 1660), points[5])

    def test_empty_padding_does_not_change_coordinates(self):
        compact = [[0, None, 1], [None, 2, None]]
        padded = [[None] * 5] + [[None] + row + [None] for row in compact]
        padded.append([None] * 5)
        self.assertEqual(
            geometry.panel_effect_centers(compact),
            geometry.panel_effect_centers(padded),
        )

    def test_neighbour_pitch_and_single_panel_origin(self):
        self.assertEqual({7: (1600, 1600)}, geometry.panel_effect_centers([[7]]))
        points = geometry.panel_effect_centers([[0, 1], [2, 3]])
        self.assertEqual(24, points[1][0] - points[0][0])
        self.assertEqual(24, points[2][1] - points[0][1])

    def test_invalid_or_ambiguous_grids_are_rejected(self):
        for grid in ([], [[]], [[None]], [[0], []], [[0, 0]], [[True]], [[-1]]):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                geometry.panel_effect_centers(grid)


if __name__ == "__main__":
    unittest.main()
