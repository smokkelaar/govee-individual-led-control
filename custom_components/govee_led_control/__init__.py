"""Govee Individual LED Control: verified model adapters behind one HA integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_BRIGHTNESS_PERCENT,
    ATTR_COLOR,
    ATTR_COLORS,
    ATTR_COMMIT,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_ELEMENTS,
    ATTR_INDEX,
    ATTR_LEVEL,
    ATTR_PIXELS,
    ATTR_REPLACE,
    ATTR_STYLE,
    ATTR_X,
    ATTR_Y,
    CONF_DEBOUNCE_MS,
    CONF_IDLE_DISCONNECT_SECONDS,
    CONF_MODEL,
    CONF_PANEL_COUNT,
    DATA_RUNTIMES,
    DATA_SERVICES_REGISTERED,
    DEFAULT_H6069_DEBOUNCE_MS,
    DEFAULT_H6069_PANEL_COUNT,
    DEFAULT_H70B3_DEBOUNCE_MS,
    DEFAULT_IDLE_DISCONNECT_SECONDS,
    DOMAIN,
    H70B3_HEIGHT,
    H70B3_WIDTH,
    LEVEL_STYLES,
    MODEL_H6069,
    MODEL_H70B3,
    SERVICE_APPLY_LEVEL,
    SERVICE_CLEAR,
    SERVICE_COMMIT,
    SERVICE_SET_ELEMENTS,
    SERVICE_SET_FRAME,
    SERVICE_SET_PIXELS,
    SERVICE_SHOW_DEMO,
    SERVICE_SHOW_ORIENTATION,
    STYLE_BAR,
)
from .h6069_controller import H6069PanelController
from .h70b3_controller import H70B3Controller
from .h70b3_protocol import RGB, parse_color
from .model_registry import get_model_spec
from .runtime import GoveeRuntime

_TARGET_FIELD = {vol.Optional(ATTR_CONFIG_ENTRY_ID): str}
_COMMIT_FIELD = {vol.Optional(ATTR_COMMIT, default=True): cv.boolean}
_BRIGHTNESS_FIELD = {
    vol.Optional(ATTR_BRIGHTNESS_PERCENT): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=100)
    )
}
_ELEMENT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_INDEX): vol.All(vol.Coerce(int), vol.Range(min=0, max=519)),
        vol.Required(ATTR_COLOR): object,
    }
)
_PIXEL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_X): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=H70B3_WIDTH - 1)
        ),
        vol.Required(ATTR_Y): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=H70B3_HEIGHT - 1)
        ),
        vol.Required(ATTR_COLOR): object,
    }
)

SET_ELEMENTS_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELD,
        **_BRIGHTNESS_FIELD,
        vol.Required(ATTR_ELEMENTS): vol.All(cv.ensure_list, [_ELEMENT_SCHEMA]),
        vol.Optional(ATTR_REPLACE, default=False): cv.boolean,
        **_COMMIT_FIELD,
    }
)
SET_PIXELS_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELD,
        **_BRIGHTNESS_FIELD,
        vol.Required(ATTR_PIXELS): vol.All(cv.ensure_list, [_PIXEL_SCHEMA]),
        vol.Optional(ATTR_REPLACE, default=False): cv.boolean,
        **_COMMIT_FIELD,
    }
)
SET_FRAME_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELD,
        **_BRIGHTNESS_FIELD,
        vol.Required(ATTR_COLORS): vol.All(cv.ensure_list, [object]),
        **_COMMIT_FIELD,
    }
)
APPLY_LEVEL_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELD,
        vol.Required(ATTR_LEVEL): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional(ATTR_STYLE, default=STYLE_BAR): vol.In(LEVEL_STYLES),
        **_COMMIT_FIELD,
    }
)
SIMPLE_SCHEMA = vol.Schema({**_TARGET_FIELD, **_COMMIT_FIELD})
COMMIT_SCHEMA = vol.Schema(_TARGET_FIELD)


def _runtime_for_call(hass: HomeAssistant, call: ServiceCall) -> GoveeRuntime:
    domain_data = hass.data.get(DOMAIN, {})
    runtimes: Mapping[str, GoveeRuntime] = domain_data.get(DATA_RUNTIMES, {})
    requested = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if requested is not None:
        runtime = runtimes.get(requested)
        if runtime is None:
            raise HomeAssistantError(
                f"No loaded Govee Advanced entry has id {requested!r}"
            )
        return runtime
    if len(runtimes) == 1:
        return next(iter(runtimes.values()))
    if not runtimes:
        raise HomeAssistantError("No Govee Advanced device is loaded")
    raise HomeAssistantError(
        "More than one Govee Advanced device is loaded; supply config_entry_id"
    )


def _parse_service_color(raw: object) -> RGB:
    try:
        return parse_color(raw)
    except ValueError as err:
        raise HomeAssistantError(str(err)) from err


def _brightness(call: ServiceCall) -> int | None:
    raw = call.data.get(ATTR_BRIGHTNESS_PERCENT)
    return int(raw) if raw is not None else None


def _scale_colors(colors: tuple[RGB, ...], brightness: int | None) -> tuple[RGB, ...]:
    if brightness is None or brightness == 100:
        return colors
    return tuple(
        tuple(round(channel * brightness / 100) for channel in color)
        for color in colors
    )  # type: ignore[return-value]


def _require_h70b3(runtime: GoveeRuntime, action: str) -> H70B3Controller:
    if runtime.spec.key != MODEL_H70B3:
        raise HomeAssistantError(f"{action} is only available for H70B3")
    return runtime.controller


async def _commit_if_requested(controller: Any, call: ServiceCall) -> None:
    if call.data.get(ATTR_COMMIT, True):
        await controller.async_commit()


async def _handle_set_elements(hass: HomeAssistant, call: ServiceCall) -> None:
    runtime = _runtime_for_call(hass, call)
    updates = {
        int(item[ATTR_INDEX]): _parse_service_color(item[ATTR_COLOR])
        for item in call.data[ATTR_ELEMENTS]
    }
    try:
        if runtime.spec.key == MODEL_H70B3:
            runtime.controller.set_pixels(
                updates,
                replace=bool(call.data[ATTR_REPLACE]),
                brightness_percent=_brightness(call),
            )
        else:
            brightness = _brightness(call)
            scaled = {
                index: _scale_colors((color,), brightness)[0]
                for index, color in updates.items()
            }
            runtime.controller.set_elements(
                scaled, replace=bool(call.data[ATTR_REPLACE])
            )
    except ValueError as err:
        raise HomeAssistantError(str(err)) from err
    await _commit_if_requested(runtime.controller, call)


async def _handle_set_pixels(hass: HomeAssistant, call: ServiceCall) -> None:
    runtime = _runtime_for_call(hass, call)
    controller = _require_h70b3(runtime, SERVICE_SET_PIXELS)
    updates = {
        controller.index(int(item[ATTR_X]), int(item[ATTR_Y])): _parse_service_color(
            item[ATTR_COLOR]
        )
        for item in call.data[ATTR_PIXELS]
    }
    controller.set_pixels(
        updates,
        replace=bool(call.data[ATTR_REPLACE]),
        brightness_percent=_brightness(call),
    )
    await _commit_if_requested(controller, call)


async def _handle_set_frame(hass: HomeAssistant, call: ServiceCall) -> None:
    runtime = _runtime_for_call(hass, call)
    colors = tuple(_parse_service_color(raw) for raw in call.data[ATTR_COLORS])
    try:
        if runtime.spec.key == MODEL_H70B3:
            runtime.controller.set_frame(
                colors, brightness_percent=_brightness(call)
            )
        else:
            runtime.controller.set_frame(_scale_colors(colors, _brightness(call)))
    except ValueError as err:
        raise HomeAssistantError(str(err)) from err
    await _commit_if_requested(runtime.controller, call)


async def _handle_apply_level(hass: HomeAssistant, call: ServiceCall) -> None:
    runtime = _runtime_for_call(hass, call)
    runtime.controller.apply_level(
        int(call.data[ATTR_LEVEL]), str(call.data[ATTR_STYLE])
    )
    await _commit_if_requested(runtime.controller, call)


async def _handle_clear(hass: HomeAssistant, call: ServiceCall) -> None:
    runtime = _runtime_for_call(hass, call)
    runtime.controller.clear()
    await _commit_if_requested(runtime.controller, call)


async def _handle_commit(hass: HomeAssistant, call: ServiceCall) -> None:
    await _runtime_for_call(hass, call).controller.async_commit()


async def _handle_demo(hass: HomeAssistant, call: ServiceCall) -> None:
    runtime = _runtime_for_call(hass, call)
    runtime.controller.show_demo()
    await _commit_if_requested(runtime.controller, call)


async def _handle_orientation(hass: HomeAssistant, call: ServiceCall) -> None:
    runtime = _runtime_for_call(hass, call)
    controller = _require_h70b3(runtime, SERVICE_SHOW_ORIENTATION)
    controller.show_orientation()
    await _commit_if_requested(controller, call)


def _register_services(hass: HomeAssistant) -> None:
    data = hass.data[DOMAIN]
    if data.get(DATA_SERVICES_REGISTERED):
        return
    handlers = (
        (SERVICE_SET_ELEMENTS, _handle_set_elements, SET_ELEMENTS_SCHEMA),
        (SERVICE_SET_PIXELS, _handle_set_pixels, SET_PIXELS_SCHEMA),
        (SERVICE_SET_FRAME, _handle_set_frame, SET_FRAME_SCHEMA),
        (SERVICE_APPLY_LEVEL, _handle_apply_level, APPLY_LEVEL_SCHEMA),
        (SERVICE_CLEAR, _handle_clear, SIMPLE_SCHEMA),
        (SERVICE_COMMIT, _handle_commit, COMMIT_SCHEMA),
        (SERVICE_SHOW_DEMO, _handle_demo, SIMPLE_SCHEMA),
        (SERVICE_SHOW_ORIENTATION, _handle_orientation, SIMPLE_SCHEMA),
    )
    for service, function, schema in handlers:
        async def handle(call: ServiceCall, fn=function) -> None:
            await fn(hass, call)

        hass.services.async_register(DOMAIN, service, handle, schema=schema)
    data[DATA_SERVICES_REGISTERED] = True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register model-independent actions without contacting any device."""
    hass.data.setdefault(
        DOMAIN, {DATA_RUNTIMES: {}, DATA_SERVICES_REGISTERED: False}
    )
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create one model adapter; setup never sends a physical command."""
    model = entry.data[CONF_MODEL]
    spec = get_model_spec(model)
    if model == MODEL_H6069:
        controller = H6069PanelController(
            hass=hass,
            host=entry.data[CONF_HOST],
            panel_count=entry.options.get(
                CONF_PANEL_COUNT,
                entry.data.get(CONF_PANEL_COUNT, DEFAULT_H6069_PANEL_COUNT),
            ),
            name=entry.data.get(CONF_NAME, entry.title),
            debounce_ms=entry.options.get(
                CONF_DEBOUNCE_MS, DEFAULT_H6069_DEBOUNCE_MS
            ),
        )
        platforms = (
            Platform.BUTTON,
            Platform.LIGHT,
            Platform.NUMBER,
            Platform.SELECT,
            Platform.SENSOR,
        )
    else:
        controller = H70B3Controller(
            hass=hass,
            address=entry.data[CONF_ADDRESS],
            name=entry.data.get(CONF_NAME, entry.title),
            debounce_ms=entry.options.get(
                CONF_DEBOUNCE_MS, DEFAULT_H70B3_DEBOUNCE_MS
            ),
            idle_disconnect_seconds=entry.options.get(
                CONF_IDLE_DISCONNECT_SECONDS, DEFAULT_IDLE_DISCONNECT_SECONDS
            ),
        )
        platforms = (
            Platform.BUTTON,
            Platform.LIGHT,
            Platform.NUMBER,
            Platform.SELECT,
            Platform.SENSOR,
            Platform.SWITCH,
        )

    runtime = GoveeRuntime(
        spec=spec,
        controller=controller,
        platforms=platforms,
        config_entry_id=entry.entry_id,
    )
    entry.runtime_data = runtime
    hass.data.setdefault(
        DOMAIN, {DATA_RUNTIMES: {}, DATA_SERVICES_REGISTERED: False}
    )[DATA_RUNTIMES][entry.entry_id] = runtime
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entities and close only the model transport owned by this entry."""
    runtime: GoveeRuntime = entry.runtime_data
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, runtime.platforms
    )
    if not unloaded:
        return False
    await runtime.controller.async_shutdown()
    hass.data[DOMAIN][DATA_RUNTIMES].pop(entry.entry_id, None)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
