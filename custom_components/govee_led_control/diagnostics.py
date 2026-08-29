"""Redacted diagnostics for every Govee Advanced model adapter."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .runtime import GoveeRuntime


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, object]:
    """Return capabilities and runtime state without keys or frame contents."""
    runtime: GoveeRuntime = entry.runtime_data
    return {
        "entry": {
            "title": entry.title,
            "model": runtime.spec.sku,
            "full_control_transport": runtime.spec.full_control_transport,
            "options": dict(entry.options),
        },
        "capabilities": {
            "transports": runtime.spec.transport_support,
            "smart_functions": runtime.spec.smart_functions,
            "evidence": runtime.spec.evidence,
        },
        "runtime": runtime.controller.diagnostics,
    }
