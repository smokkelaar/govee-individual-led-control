"""Persistent physical mounting controls for the H70B3 curtain."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, MANUFACTURER
from .h70b3_controller import H70B3Controller
from .runtime import GoveeRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add horizontal and vertical mirror switches."""
    runtime: GoveeRuntime = entry.runtime_data
    controller: H70B3Controller = runtime.controller
    async_add_entities(
        (
            H70B3MirrorSwitch(
                controller, "horizontal", "Horizontaal spiegelen", "mdi:flip-horizontal"
            ),
            H70B3MirrorSwitch(
                controller, "vertical", "Verticaal spiegelen", "mdi:flip-vertical"
            ),
        )
    )


class H70B3MirrorSwitch(RestoreEntity, SwitchEntity):
    """Mirror logical output while preserving all automation coordinates."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, controller: H70B3Controller, axis: str, name: str, icon: str
    ) -> None:
        self._controller = controller
        self._axis = axis
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{controller.device_id}_flip_{axis}"
        self._attr_suggested_object_id = f"h70b3_spiegel_{axis}"
        self._remove_listener = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._controller.device_id)},
            connections={("bluetooth", self._controller.address)},
            name=self._controller.name,
            manufacturer=MANUFACTURER,
            model="H70B3 Curtain Lights 2",
        )

    @property
    def is_on(self) -> bool:
        if self._axis == "horizontal":
            return self._controller.flip_horizontal
        return self._controller.flip_vertical

    async def async_added_to_hass(self) -> None:
        """Restore the mounting choice without writing during startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._controller.restore_flip(self._axis, last_state.state == STATE_ON)
        self._remove_listener = self._controller.add_matrix_listener(
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

    async def async_turn_on(self, **kwargs: object) -> None:
        self._controller.set_flip(self._axis, True)

    async def async_turn_off(self, **kwargs: object) -> None:
        self._controller.set_flip(self._axis, False)
