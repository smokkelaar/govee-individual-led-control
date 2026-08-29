"""Config and options flows for the multi-model Govee integration."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ADDRESS, CONF_HOST, CONF_NAME
from homeassistant.core import callback

from .const import (
    CONF_CREATE_PIXEL_ENTITIES,
    CONF_DEBOUNCE_MS,
    CONF_IDLE_DISCONNECT_SECONDS,
    CONF_MODEL,
    CONF_PANEL_COUNT,
    CONF_TRANSPORT,
    DEFAULT_CREATE_PIXEL_ENTITIES,
    DEFAULT_H6069_DEBOUNCE_MS,
    DEFAULT_H6069_HOST,
    DEFAULT_H6069_NAME,
    DEFAULT_H6069_PANEL_COUNT,
    DEFAULT_H70B3_ADDRESS,
    DEFAULT_H70B3_DEBOUNCE_MS,
    DEFAULT_H70B3_NAME,
    DEFAULT_IDLE_DISCONNECT_SECONDS,
    DOMAIN,
    MAX_PANEL_COUNT,
    MIN_PANEL_COUNT,
    MODEL_H6069,
    MODEL_H70B3,
    TRANSPORT_BLUETOOTH,
    TRANSPORT_LAN,
)

_MAC_PATTERN = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


class GoveeAdvancedConfigFlow(ConfigFlow, domain=DOMAIN):
    """Select a model first, then collect only its verified transport data."""

    VERSION = 1

    def __init__(self) -> None:
        self._address: str | None = None
        self._name = DEFAULT_H70B3_NAME

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GoveeAdvancedOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show model choices with their full-control transport at the start."""
        return self.async_show_menu(
            step_id="user", menu_options=[MODEL_H6069, MODEL_H70B3]
        )

    async def async_step_h6069(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the physically verified H6069 LAN adapter."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                ipaddress.ip_address(host)
            except ValueError:
                errors[CONF_HOST] = "invalid_ip"
            else:
                await self.async_set_unique_id(f"{MODEL_H6069}_{host}")
                self._abort_if_unique_id_configured()
                name = user_input[CONF_NAME].strip() or DEFAULT_H6069_NAME
                panel_count = int(user_input[CONF_PANEL_COUNT])
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_MODEL: MODEL_H6069,
                        CONF_TRANSPORT: TRANSPORT_LAN,
                        CONF_HOST: host,
                        CONF_NAME: name,
                        CONF_PANEL_COUNT: panel_count,
                    },
                    options={
                        CONF_PANEL_COUNT: panel_count,
                        CONF_DEBOUNCE_MS: DEFAULT_H6069_DEBOUNCE_MS,
                    },
                )

        return self.async_show_form(
            step_id="h6069",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_H6069_HOST): str,
                    vol.Required(CONF_NAME, default=DEFAULT_H6069_NAME): str,
                    vol.Required(
                        CONF_PANEL_COUNT, default=DEFAULT_H6069_PANEL_COUNT
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_PANEL_COUNT, max=MAX_PANEL_COUNT),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_h70b3(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the H70B3 through a local or proxied BLE adapter."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            if not _MAC_PATTERN.fullmatch(address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(f"{MODEL_H70B3}_{address}")
                self._abort_if_unique_id_configured()
                name = user_input[CONF_NAME].strip() or DEFAULT_H70B3_NAME
                return self._create_h70b3_entry(address, name)

        return self.async_show_form(
            step_id="h70b3",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS, default=DEFAULT_H70B3_ADDRESS): str,
                    vol.Required(CONF_NAME, default=DEFAULT_H70B3_NAME): str,
                }
            ),
            errors=errors,
        )

    def _create_h70b3_entry(self, address: str, name: str) -> ConfigFlowResult:
        return self.async_create_entry(
            title=name,
            data={
                CONF_MODEL: MODEL_H70B3,
                CONF_TRANSPORT: TRANSPORT_BLUETOOTH,
                CONF_ADDRESS: address,
                CONF_NAME: name,
            },
            options={
                CONF_CREATE_PIXEL_ENTITIES: DEFAULT_CREATE_PIXEL_ENTITIES,
                CONF_DEBOUNCE_MS: DEFAULT_H70B3_DEBOUNCE_MS,
                CONF_IDLE_DISCONNECT_SECONDS: DEFAULT_IDLE_DISCONNECT_SECONDS,
            },
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Offer a discovered H70B3 without contacting or changing it."""
        self._address = discovery_info.address.upper()
        self._name = discovery_info.name or DEFAULT_H70B3_NAME
        await self.async_set_unique_id(f"{MODEL_H70B3}_{self._address}")
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered Bluetooth; setup itself never transmits a frame."""
        if user_input is not None:
            assert self._address is not None
            return self._create_h70b3_entry(self._address, self._name)
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._name,
                "address": self._address or "",
            },
        )


class GoveeAdvancedOptionsFlow(OptionsFlow):
    """Expose only options that are meaningful for the configured model."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._entry.options
        model = self._entry.data[CONF_MODEL]
        if model == MODEL_H6069:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_PANEL_COUNT,
                        default=options.get(
                            CONF_PANEL_COUNT,
                            self._entry.data.get(
                                CONF_PANEL_COUNT, DEFAULT_H6069_PANEL_COUNT
                            ),
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_PANEL_COUNT, max=MAX_PANEL_COUNT),
                    ),
                    vol.Required(
                        CONF_DEBOUNCE_MS,
                        default=options.get(
                            CONF_DEBOUNCE_MS, DEFAULT_H6069_DEBOUNCE_MS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=50, max=2000)),
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_CREATE_PIXEL_ENTITIES,
                        default=options.get(
                            CONF_CREATE_PIXEL_ENTITIES,
                            DEFAULT_CREATE_PIXEL_ENTITIES,
                        ),
                    ): bool,
                    vol.Required(
                        CONF_DEBOUNCE_MS,
                        default=options.get(
                            CONF_DEBOUNCE_MS, DEFAULT_H70B3_DEBOUNCE_MS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=50, max=2000)),
                    vol.Required(
                        CONF_IDLE_DISCONNECT_SECONDS,
                        default=options.get(
                            CONF_IDLE_DISCONNECT_SECONDS,
                            DEFAULT_IDLE_DISCONNECT_SECONDS,
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=3, max=120)),
                }
            )
        return self.async_show_form(step_id="init", data_schema=schema)
