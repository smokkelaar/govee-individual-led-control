"""Manual normalized-level control for sensor and dashboard experiments."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, MANUFACTURER, MODEL_H70B3
from .runtime import GoveeRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities((GoveeVisualLevel(entry.runtime_data),))


class GoveeVisualLevel(RestoreEntity, NumberEntity):
    """Preview the generic 0..100 sensor mapping without an automation."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:gauge"
    _attr_mode = NumberMode.SLIDER
    _attr_name = "Demo/sensorniveau"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_should_poll = False

    def __init__(self, runtime: GoveeRuntime) -> None:
        self._runtime = runtime
        self._controller = runtime.controller
        self._attr_unique_id = f"{self._controller.device_id}_visual_level"
        self._attr_suggested_object_id = f"{runtime.spec.key}_visual_level"

    @property
    def native_value(self) -> float:
        return float(self._runtime.visual_level)

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

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            try:
                self._runtime.visual_level = max(
                    0, min(100, round(float(last_state.state)))
                )
            except ValueError:
                pass

    async def async_set_native_value(self, value: float) -> None:
        self._runtime.visual_level = max(0, min(100, round(value)))
        self._controller.apply_level(
            self._runtime.visual_level, self._runtime.visual_style
        )
        await self._controller.async_commit()
        self.async_write_ha_state()
