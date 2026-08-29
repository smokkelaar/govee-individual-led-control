"""Light entities for every model adapter in Govee Individual LED Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_CREATE_PIXEL_ENTITIES,
    DEFAULT_CREATE_PIXEL_ENTITIES,
    DOMAIN,
    H70B3_HEIGHT as HEIGHT,
    H70B3_PIXEL_COUNT as PIXEL_COUNT,
    H70B3_WIDTH as WIDTH,
    MANUFACTURER,
    MODEL_H6069,
)
from .h6069_controller import H6069PanelController
from .h6069_protocol import RGB as H6069RGB
from .h70b3_controller import H70B3Controller
from .h70b3_protocol import RGB, validate_rgb
from .runtime import GoveeRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up only the entities implemented by the selected model adapter."""
    runtime: GoveeRuntime = entry.runtime_data
    if runtime.spec.key == MODEL_H6069:
        controller: H6069PanelController = runtime.controller
        async_add_entities(
            H6069PanelLight(controller, panel_id)
            for panel_id in range(controller.panel_count)
        )
        return

    controller: H70B3Controller = runtime.controller
    entities: list[LightEntity] = [H70B3MatrixLight(controller)]
    create_pixels = entry.options.get(
        CONF_CREATE_PIXEL_ENTITIES, DEFAULT_CREATE_PIXEL_ENTITIES
    )
    if create_pixels:
        entities.extend(
            H70B3PixelLight(controller, pixel_index)
            for pixel_index in range(PIXEL_COUNT)
        )
    async_add_entities(entities)


class H70B3Entity:
    """Common device registry metadata."""

    _controller: H70B3Controller

    @property
    def device_info(self) -> DeviceInfo:
        """Return the physical curtain device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._controller.device_id)},
            connections={("bluetooth", self._controller.address)},
            name=self._controller.name,
            manufacturer=MANUFACTURER,
            model="H70B3 Curtain Lights 2",
        )


class H70B3MatrixLight(H70B3Entity, RestoreEntity, LightEntity):
    """Aggregate light that controls the complete curtain."""

    _attr_assumed_state = True
    _attr_color_mode = ColorMode.RGB
    _attr_has_entity_name = True
    _attr_name = "Matrix"
    _attr_should_poll = False
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, controller: H70B3Controller) -> None:
        self._controller = controller
        self._attr_unique_id = f"{controller.device_id}_matrix"
        self._attr_suggested_object_id = "h70b3_matrix"
        self._remove_listener = None

    @property
    def is_on(self) -> bool:
        return self._controller.matrix_is_on

    @property
    def rgb_color(self) -> RGB:
        return self._controller.matrix_rgb

    @property
    def brightness(self) -> int:
        return round(self._controller.global_brightness * 255 / 100)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._controller.diagnostics

    async def async_added_to_hass(self) -> None:
        """Restore aggregate color/brightness without sending anything."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            rgb: RGB = self._controller.matrix_rgb
            raw_rgb = last_state.attributes.get(ATTR_RGB_COLOR)
            if isinstance(raw_rgb, (list, tuple)) and len(raw_rgb) == 3:
                rgb = validate_rgb(raw_rgb)
            brightness_percent = self._controller.global_brightness
            raw_brightness = last_state.attributes.get(ATTR_BRIGHTNESS)
            if isinstance(raw_brightness, int):
                brightness_percent = max(
                    1, min(100, round(raw_brightness * 100 / 255))
                )
            self._controller.restore_matrix(
                rgb=rgb, brightness_percent=brightness_percent
            )
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        rgb = kwargs.get(ATTR_RGB_COLOR)
        normalized_rgb: RGB | None = None
        if isinstance(rgb, (list, tuple)) and len(rgb) == 3:
            normalized_rgb = validate_rgb(rgb)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        self._controller.update_matrix(
            is_on=True,
            rgb=normalized_rgb,
            brightness=brightness if isinstance(brightness, int) else None,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._controller.update_matrix(is_on=False)


class H70B3PixelLight(H70B3Entity, RestoreEntity, LightEntity):
    """One physical LED at a zero-based x/y coordinate."""

    _attr_assumed_state = True
    _attr_color_mode = ColorMode.RGB
    _attr_entity_registry_enabled_default = True
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, controller: H70B3Controller, pixel_index: int) -> None:
        self._controller = controller
        self._pixel_index = pixel_index
        self._x = pixel_index % WIDTH
        self._y = pixel_index // WIDTH
        self._attr_name = f"Led R{self._y + 1:02d} K{self._x + 1:02d}"
        self._attr_unique_id = (
            f"{controller.device_id}_pixel_y{self._y:02d}_x{self._x:02d}"
        )
        self._attr_suggested_object_id = (
            f"h70b3_led_r{self._y + 1:02d}_k{self._x + 1:02d}"
        )
        self._remove_listener = None

    @property
    def is_on(self) -> bool:
        return self._controller.pixels[self._pixel_index].is_on

    @property
    def rgb_color(self) -> RGB:
        return self._controller.pixels[self._pixel_index].rgb

    @property
    def brightness(self) -> int:
        return self._controller.pixels[self._pixel_index].brightness

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        return {
            "pixel_index": self._pixel_index,
            "x": self._x,
            "y": self._y,
            "row": self._y + 1,
            "column": self._x + 1,
        }

    async def async_added_to_hass(self) -> None:
        """Restore the optimistic pixel state without transmitting it."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            current = self._controller.pixels[self._pixel_index]
            rgb = current.rgb
            raw_rgb = last_state.attributes.get(ATTR_RGB_COLOR)
            if isinstance(raw_rgb, (list, tuple)) and len(raw_rgb) == 3:
                rgb = validate_rgb(raw_rgb)
            brightness = current.brightness
            raw_brightness = last_state.attributes.get(ATTR_BRIGHTNESS)
            if isinstance(raw_brightness, int):
                brightness = max(1, min(255, raw_brightness))
            self._controller.restore_pixel(
                self._pixel_index,
                is_on=last_state.state == STATE_ON,
                rgb=rgb,
                brightness=brightness,
            )
        self._remove_listener = self._controller.add_pixel_listener(
            self._pixel_index, self._handle_update
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        rgb = kwargs.get(ATTR_RGB_COLOR)
        normalized_rgb: RGB | None = None
        if isinstance(rgb, (list, tuple)) and len(rgb) == 3:
            normalized_rgb = validate_rgb(rgb)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        self._controller.update_pixel(
            self._pixel_index,
            is_on=True,
            rgb=normalized_rgb,
            brightness=brightness if isinstance(brightness, int) else None,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._controller.update_pixel(self._pixel_index, is_on=False)


class H6069PanelLight(RestoreEntity, LightEntity):
    """One physical H6069 square addressed by its protocol panel id."""

    _attr_assumed_state = True
    _attr_color_mode = ColorMode.RGB
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, controller: H6069PanelController, panel_id: int) -> None:
        self._controller = controller
        self._panel_id = panel_id
        self._attr_name = f"Paneel {panel_id:02d}"
        self._attr_unique_id = f"{controller.device_id}_panel_{panel_id:02d}"
        self._attr_suggested_object_id = f"h6069_paneel_{panel_id:02d}"
        self._remove_listener = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._controller.device_id)},
            name=self._controller.name,
            manufacturer=MANUFACTURER,
            model="H6069 Mini Panel Lights",
        )

    @property
    def is_on(self) -> bool:
        return self._controller.panels[self._panel_id].is_on

    @property
    def rgb_color(self) -> H6069RGB:
        return self._controller.panels[self._panel_id].rgb

    @property
    def brightness(self) -> int:
        return self._controller.panels[self._panel_id].brightness

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "protocol_panel_id": self._panel_id,
            "transport": "LAN",
            "last_send_error": self._controller.last_error,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            raw_rgb = last_state.attributes.get(ATTR_RGB_COLOR)
            raw_brightness = last_state.attributes.get(ATTR_BRIGHTNESS)
            current = self._controller.panels[self._panel_id]
            rgb: H6069RGB = current.rgb
            if isinstance(raw_rgb, (list, tuple)) and len(raw_rgb) == 3:
                rgb = tuple(int(value) for value in raw_rgb)  # type: ignore[assignment]
            brightness = current.brightness
            if isinstance(raw_brightness, int):
                brightness = max(1, min(255, raw_brightness))
            self._controller.restore_panel(
                self._panel_id,
                is_on=last_state.state == STATE_ON,
                rgb=rgb,
                brightness=brightness,
            )
        self._remove_listener = self._controller.add_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        raw_rgb = kwargs.get(ATTR_RGB_COLOR)
        rgb: H6069RGB | None = None
        if isinstance(raw_rgb, (list, tuple)) and len(raw_rgb) == 3:
            rgb = tuple(int(value) for value in raw_rgb)  # type: ignore[assignment]
        raw_brightness = kwargs.get(ATTR_BRIGHTNESS)
        self._controller.update_panel(
            self._panel_id,
            is_on=True,
            rgb=rgb,
            brightness=raw_brightness if isinstance(raw_brightness, int) else None,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._controller.update_panel(self._panel_id, is_on=False)
