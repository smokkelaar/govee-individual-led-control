"""Tests for smart sensor visualizations without Home Assistant or hardware."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "govee_led_control"
PACKAGE = "govee_led_control_visualization_test"


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
const = _load("const", "const.py")
visualization = _load("visualization", "visualization.py")


class VisualizationTests(unittest.TestCase):
    def test_h6069_bar_endpoints(self) -> None:
        self.assertEqual(
            set(visualization.h6069_level_frame(0, const.STYLE_BAR, 40)),
            {(0, 0, 0)},
        )
        full = visualization.h6069_level_frame(100, const.STYLE_BAR, 40)
        self.assertNotIn((0, 0, 0), full)
        self.assertEqual(full[-1], (255, 0, 0))

    def test_h6069_position_has_exactly_one_light(self) -> None:
        frame = visualization.h6069_level_frame(50, const.STYLE_POSITION, 40)
        self.assertEqual(sum(color != (0, 0, 0) for color in frame), 1)

    def test_h70b3_bar_fills_from_bottom(self) -> None:
        frame = visualization.h70b3_level_frame(50, const.STYLE_BAR, 20, 26)
        self.assertEqual(sum(color != (0, 0, 0) for color in frame), 13 * 20)
        self.assertEqual(set(frame[: 13 * 20]), {(0, 0, 0)})

    def test_h70b3_position_is_one_complete_column(self) -> None:
        frame = visualization.h70b3_level_frame(100, const.STYLE_POSITION, 20, 26)
        lit = [index for index, color in enumerate(frame) if color != (0, 0, 0)]
        self.assertEqual(len(lit), 26)
        self.assertTrue(all(index % 20 == 19 for index in lit))

    def test_out_of_range_level_is_clamped(self) -> None:
        self.assertEqual(
            visualization.h6069_level_frame(-50, const.STYLE_BAR, 2),
            ((0, 0, 0), (0, 0, 0)),
        )
        self.assertNotIn(
            (0, 0, 0),
            visualization.h6069_level_frame(500, const.STYLE_BAR, 2),
        )

    def test_unknown_style_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            visualization.h70b3_level_frame(50, "unknown", 20, 26)


if __name__ == "__main__":
    unittest.main()
