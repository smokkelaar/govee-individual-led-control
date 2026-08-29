"""Runtime wrapper shared by model-specific platforms and services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.const import Platform

from .model_registry import ModelSpec
from .const import STYLE_BAR


@dataclass(slots=True)
class GoveeRuntime:
    """One configured device and the model adapter that controls it."""

    spec: ModelSpec
    controller: Any
    platforms: tuple[Platform, ...]
    config_entry_id: str
    visual_level: int = 50
    visual_style: str = STYLE_BAR
