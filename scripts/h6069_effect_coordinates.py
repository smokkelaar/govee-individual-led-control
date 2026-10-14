"""Calculate H6069 effect focus points from a confirmed panel grid.

This is a read-only geometry helper, not an encoder or an individual LED API.
The square panel pitch is 24 and the app centres the occupied bounds at 1600.
Panel 05 and panel 35 were physically checked on the documented installation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


def panel_effect_centers(
    number_grid: Sequence[Sequence[int | None]],
) -> dict[int, tuple[int, int]]:
    """Return panel IDs mapped to effect coordinates, ignoring empty padding."""
    if not number_grid or not number_grid[0]:
        raise ValueError("A non-empty rectangular grid is required")
    width = len(number_grid[0])
    cells: dict[int, tuple[int, int]] = {}
    for y, row in enumerate(number_grid):
        if len(row) != width:
            raise ValueError("Grid rows must have equal length")
        for x, panel_id in enumerate(row):
            if panel_id is None:
                continue
            if type(panel_id) is not int or panel_id < 0:
                raise ValueError("Panel IDs must be non-negative integers")
            if panel_id in cells:
                raise ValueError("Panel IDs must be unique")
            cells[panel_id] = (x, y)
    if not cells:
        raise ValueError("The grid has no panels")
    min_x = min(x for x, _ in cells.values())
    max_x = max(x for x, _ in cells.values())
    min_y = min(y for _, y in cells.values())
    max_y = max(y for _, y in cells.values())
    centers = {
        panel_id: (
            1600 + 12 * (2 * x - min_x - max_x),
            1600 + 12 * (2 * y - min_y - max_y),
        )
        for panel_id, (x, y) in sorted(cells.items())
    }
    if any(not 0 <= c <= 3200 for point in centers.values() for c in point):
        raise ValueError("The calculated layout exceeds the app canvas")
    return centers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topology", type=Path, help="JSON with number_grid")
    parser.add_argument("--output", type=Path, help="Write a new JSON file")
    args = parser.parse_args()
    topology = json.loads(args.topology.read_text(encoding="utf-8-sig"))
    centers = panel_effect_centers(topology["number_grid"])
    result = {
        "panel_pitch": 24,
        "occupied_bounds_center": [1600, 1600],
        "coordinate_kind": "effect_focus",
        "independent_internal_rgb_addressing_proven": False,
        "panels": [
            {"id": panel_id, "effect_x": x, "effect_y": y}
            for panel_id, (x, y) in centers.items()
        ],
    }
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
