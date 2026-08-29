"""Persistent style selector for normalized sensor visualization."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, LEVEL_STYLES, MANUFACTURER, MODEL_H70B3
from .runtime import GoveeRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities((GoveeVisualStyle(entry.runtime_data),))


class GoveeVisualStyle(RestoreEntity, SelectEntity):
    """Choose bar, position or pulse and preview it on explicit selection."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:animation-outline"
    _attr_name = "Sensorvisualisatie"
    _attr_options = list(LEVEL_STYLES)
    _attr_should_poll = False

    def __init__(self, runtime: GoveeRuntime) -> None:
        self._runtime = runtime
        self._controller = runtime.controller
        self._attr_unique_id = f"{self._controller.device_id}_visual_style"
        self._attr_suggested_object_id = f"{runtime.spec.key}_visual_style"

    @property
    def current_option(self) -> str:
        return self._runtime.visual_style

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
        if last_state is not None and last_state.state in self.options:
            self._runtime.visual_style = last_state.state

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError(f"unsupported visualization style {option!r}")
        self._runtime.visual_style = option
        self._controller.apply_level(self._runtime.visual_level, option)
        await self._controller.async_commit()
        self.async_write_ha_state()
