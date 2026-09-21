"""Tests for persistent LED Studio gallery payloads."""

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "govee_led_control"
    / "gallery_data.py"
)
SPEC = importlib.util.spec_from_file_location("govee_gallery_data", MODULE_PATH)
gallery_data = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gallery_data)


def test_static_curtain_art_is_normalized() -> None:
    item = gallery_data.validate_gallery_item(
        {
            "name": "  Spookje  ",
            "target": "h70b3",
            "kind": "art",
            "brightness": 70,
            "colors": ["#AABBCC"] * 520,
        }
    )
    assert item["name"] == "Spookje"
    assert item["colors"] == ["#aabbcc"] * 520


def test_animation_frames_are_validated() -> None:
    item = gallery_data.validate_gallery_item(
        {
            "name": "Dansend spookje",
            "target": "h70b3",
            "kind": "animation",
            "frames": [{"colors": ["#000000"] * 520, "duration": 125}],
        }
    )
    assert item["brightness"] == 100
    assert item["frames"][0]["duration"] == 125


@pytest.mark.parametrize(
    "changes",
    [
        {"name": ""},
        {"target": "unknown"},
        {"brightness": 0},
        {"colors": ["not-a-color"] * 520},
        {"colors": ["#000000"] * 519},
    ],
)
def test_invalid_static_art_is_rejected(changes: dict) -> None:
    payload = {
        "name": "Art",
        "target": "h70b3",
        "kind": "art",
        "brightness": 50,
        "colors": ["#000000"] * 520,
    }
    payload.update(changes)
    with pytest.raises(ValueError):
        gallery_data.validate_gallery_item(payload)


def test_animation_is_not_supported_for_panels() -> None:
    with pytest.raises(ValueError):
        gallery_data.validate_gallery_item(
            {
                "name": "Panel animation",
                "target": "h6069",
                "kind": "animation",
                "frames": [{"colors": ["#000000"] * 520, "duration": 100}],
            }
        )
