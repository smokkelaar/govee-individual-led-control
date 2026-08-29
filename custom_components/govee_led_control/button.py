"""Explicit, one-shot controls used by dashboards and commissioning."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL_H6069, MODEL_H70B3
from .runtime import GoveeRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add safe, explicit buttons; creating them never sends a command."""
    runtime: GoveeRuntime = entry.runtime_data
    buttons = [
        GoveeCommandButton(
            runtime,
            "clear",
            "Alles zwart",
            "mdi:lightbulb-off-outline",
            runtime.controller.clear,
        ),
        GoveeCommandButton(
            runtime,
            "demo",
            "Bewezen demo tonen",
            "mdi:test-tube",
            runtime.controller.show_demo,
        ),
    ]
    if runtime.spec.key == MODEL_H70B3:
        buttons.append(
            GoveeCommandButton(
                runtime,
                "orientation",
                "Oriëntatie tonen",
                "mdi:axis-arrow",
                runtime.controller.show_orientation,
            )
        )
    if runtime.spec.key == MODEL_H6069:
        buttons.append(H6069TopologyRefreshButton(runtime))
    async_add_entities(buttons)


class GoveeCommandButton(ButtonEntity):
    """Apply one local framebuffer operation and explicitly commit it."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        runtime: GoveeRuntime,
        key: str,
        name: str,
        icon: str,
        command: Callable[[], None],
    ) -> None:
        self._runtime = runtime
        self._controller = runtime.controller
        self._command = command
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{self._controller.device_id}_{key}"
        self._attr_suggested_object_id = f"{runtime.spec.key}_{key}"

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

    async def async_press(self) -> None:
        self._command()
        await self._controller.async_commit()


class H6069TopologyRefreshButton(ButtonEntity):
    """Explicitly probe whether firmware exposes topology through LAN status."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Paneelindeling via LAN proberen"
    _attr_icon = "mdi:map-search-outline"

    def __init__(self, runtime: GoveeRuntime) -> None:
        self._runtime = runtime
        self._controller = runtime.controller
        self._attr_unique_id = f"{self._controller.device_id}_refresh_topology"
        self._attr_suggested_object_id = "h6069_paneelindeling_uitlezen"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._controller.device_id)},
            name=self._controller.name,
            manufacturer=MANUFACTURER,
            model=f"{self._runtime.spec.sku} {self._runtime.spec.name}",
        )

    async def async_press(self) -> None:
        await self._controller.async_refresh_topology()
