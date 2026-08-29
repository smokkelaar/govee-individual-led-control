"""Capability and transport visibility for configured Govee devices."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL_H70B3
from .runtime import GoveeRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one decision-useful capability entity per physical device."""
    async_add_entities((GoveeTransportSensor(entry.runtime_data),))


class GoveeTransportSensor(SensorEntity):
    """Show which path provides full element control and what remains limited."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:connection"
    _attr_name = "Volledige controle via"
    _attr_should_poll = False

    def __init__(self, runtime: GoveeRuntime) -> None:
        self._runtime = runtime
        self._controller = runtime.controller
        self._attr_unique_id = f"{self._controller.device_id}_transport"
        self._attr_suggested_object_id = f"{runtime.spec.key}_transport"
        self._remove_listener: Callable[[], None] | None = None

    @property
    def native_value(self) -> str:
        return self._runtime.spec.full_control_transport.upper()

    @property
    def device_info(self) -> DeviceInfo:
        connections = set()
        if self._runtime.spec.key == MODEL_H70B3:
            connections.add(("bluetooth", self._controller.address))
        return DeviceInfo(
            identifiers={(DOMAIN, self._controller.device_id)},
            connections=connections,
            name=self._controller.name,
            manufacturer=MANUFACTURER,
            model=f"{self._runtime.spec.sku} {self._runtime.spec.name}",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "config_entry_id": self._runtime.config_entry_id,
            "model": self._runtime.spec.sku,
            "element_type": self._runtime.spec.element_label,
            "element_count": (
                self._controller.panel_count
                if hasattr(self._controller, "panel_count")
                else self._runtime.spec.element_count
            ),
            "lan": self._runtime.spec.transport_support["lan"],
            "bluetooth": self._runtime.spec.transport_support["bluetooth"],
            "matter": self._runtime.spec.transport_support["matter"],
            "smart_functions": self._runtime.spec.smart_functions,
            "evidence": self._runtime.spec.evidence,
            "runtime": self._controller.diagnostics,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._runtime.spec.key == MODEL_H70B3:
            self._remove_listener = self._controller.add_matrix_listener(
                self._handle_update
            )
        else:
            self._remove_listener = self._controller.add_listener(
                self._handle_update
            )

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
