"""Shared state and debounced UDP transport for H6069 panel entities."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import socket
import time
from typing import Any

from homeassistant.core import HomeAssistant

from .h6069_protocol import RGB, build_ptreal_datagram
from .h6069_topology import H6069Topology, query_topology
from .visualization import h6069_level_frame

_LOGGER = logging.getLogger(__name__)

UDP_PORT = 4003

# Captured baseline after the successful physical single-panel proof. It is
# used only as optimistic restored state and is never transmitted at startup.
CAPTURED_40_PANEL_RGB: tuple[RGB, ...] = (
    (0x1D, 0xFF, 0xFF), (0x1D, 0xFF, 0xFF), (0x75, 0xFF, 0x3B),
    (0x75, 0xFF, 0x3B), (0x75, 0xFF, 0x3B), (0x00, 0x00, 0xFF),
    (0x75, 0xFF, 0x3B), (0x33, 0x38, 0xFF), (0x37, 0xFF, 0x38),
    (0x37, 0xFF, 0x38), (0x37, 0xFF, 0x38), (0xFF, 0x3C, 0xFF),
    (0xFF, 0x3C, 0xFF), (0x40, 0xFF, 0x40), (0x33, 0x38, 0xFF),
    (0x33, 0x38, 0xFF), (0xFB, 0x57, 0xFF), (0x33, 0x38, 0xFF),
    (0x33, 0x38, 0xFF), (0xFF, 0x3C, 0xFF), (0x37, 0xFF, 0x38),
    (0x33, 0x38, 0xFF), (0x75, 0xFF, 0x3B), (0x1D, 0xFF, 0xFF),
    (0x1D, 0xFF, 0xFF), (0x58, 0xFF, 0x56), (0x58, 0xFF, 0x56),
    (0x58, 0xFF, 0x56), (0xFF, 0xE7, 0x9A), (0x58, 0xFF, 0x56),
    (0xFF, 0xE7, 0x9A), (0xFF, 0xE7, 0x9A), (0xFF, 0x2A, 0x6A),
    (0xFF, 0x2A, 0x6A), (0xFF, 0x3C, 0xFF), (0xFF, 0x3C, 0xFF),
    (0xFF, 0x3C, 0xFF), (0x40, 0xFF, 0x40), (0xFF, 0xE7, 0x9A),
    (0x40, 0xFF, 0x40),
)


@dataclass(slots=True)
class PanelState:
    """Optimistic state retained for one physical panel."""

    is_on: bool
    rgb: RGB
    brightness: int

    @property
    def output_rgb(self) -> RGB:
        """Return the RGB values that must be written to the physical panel."""
        if not self.is_on:
            return (0, 0, 0)
        return tuple(
            max(0, min(255, round(channel * self.brightness / 255)))
            for channel in self.rgb
        )  # type: ignore[return-value]


def _initial_panel_states(panel_count: int) -> list[PanelState]:
    """Build a safe initial state without transmitting it during setup."""
    if panel_count == len(CAPTURED_40_PANEL_RGB):
        colors = CAPTURED_40_PANEL_RGB
    else:
        colors = tuple((255, 255, 255) for _ in range(panel_count))
    return [PanelState(True, rgb, 255) for rgb in colors]


class H6069PanelController:
    """Own the complete 40-panel snapshot and serialize outgoing updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        panel_count: int,
        name: str,
        debounce_ms: int,
    ) -> None:
        self.hass = hass
        self.host = host
        self.panel_count = panel_count
        self.name = name
        self.debounce_seconds = debounce_ms / 1000
        self.device_id = f"h6069_{host}"
        self.panels = _initial_panel_states(panel_count)
        self._listeners: set[Callable[[], None]] = set()
        self._send_timer: asyncio.TimerHandle | None = None
        self._send_lock = asyncio.Lock()
        self._topology_lock = asyncio.Lock()
        self._dirty = False
        self._closed = False
        self.last_error: str | None = None
        self.last_send_duration: float | None = None
        self.successful_uploads = 0
        self.topology: H6069Topology | None = None
        self.topology_last_updated: str | None = None
        self.topology_error: str | None = None
        self.topology_queries = 0

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity-state listener."""
        self._listeners.add(listener)

        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def restore_panel(
        self,
        panel_id: int,
        *,
        is_on: bool,
        rgb: RGB,
        brightness: int,
    ) -> None:
        """Restore state from Home Assistant without sending to the device."""
        self.panels[panel_id] = PanelState(is_on, rgb, brightness)

    def update_panel(
        self,
        panel_id: int,
        *,
        is_on: bool | None = None,
        rgb: RGB | None = None,
        brightness: int | None = None,
    ) -> None:
        """Update one panel and schedule a complete pattern write."""
        panel = self.panels[panel_id]
        if is_on is not None:
            panel.is_on = is_on
        if rgb is not None:
            panel.rgb = tuple(  # type: ignore[assignment]
                max(0, min(255, int(value))) for value in rgb
            )
        if brightness is not None:
            panel.brightness = max(1, min(255, int(brightness)))
        self._dirty = True
        self._schedule_send()
        self._notify_listeners()

    def set_elements(
        self, updates: dict[int, RGB], *, replace: bool = False
    ) -> None:
        """Apply several protocol-indexed panels as one shadow-state change."""
        if replace:
            for panel in self.panels:
                panel.is_on = False
        for panel_id, raw_rgb in updates.items():
            if not 0 <= panel_id < self.panel_count:
                raise ValueError(
                    f"panel index {panel_id} is outside 0..{self.panel_count - 1}"
                )
            rgb: RGB = tuple(
                max(0, min(255, int(value))) for value in raw_rgb
            )  # type: ignore[assignment]
            self.panels[panel_id] = PanelState(rgb != (0, 0, 0), rgb, 255)
        self._dirty = True
        self._schedule_send()
        self._notify_listeners()

    def set_frame(self, colors: tuple[RGB, ...]) -> None:
        """Replace the complete protocol-indexed panel frame."""
        if len(colors) != self.panel_count:
            raise ValueError(f"a frame requires exactly {self.panel_count} colors")
        normalized: list[PanelState] = []
        for raw_rgb in colors:
            rgb: RGB = tuple(
                max(0, min(255, int(value))) for value in raw_rgb
            )  # type: ignore[assignment]
            normalized.append(PanelState(rgb != (0, 0, 0), rgb, 255))
        self.panels = normalized
        self._dirty = True
        self._schedule_send()
        self._notify_listeners()

    def clear(self) -> None:
        """Turn all panels off in the shadow frame."""
        for panel in self.panels:
            panel.is_on = False
        self._dirty = True
        self._schedule_send()
        self._notify_listeners()

    def show_demo(self) -> None:
        """Load the physically proven panel-5 identification pattern."""
        colors: list[RGB] = [(0, 0, 255)] * self.panel_count
        if self.panel_count > 5:
            colors[5] = (255, 0, 0)
        self.set_frame(tuple(colors))

    def apply_level(self, level: int, style: str) -> None:
        """Map a normalized HA sensor value to a deterministic panel image."""
        self.set_frame(h6069_level_frame(level, style, self.panel_count))

    def _schedule_send(self) -> None:
        if self._closed:
            return
        if self._send_timer is not None:
            self._send_timer.cancel()
        loop = asyncio.get_running_loop()
        self._send_timer = loop.call_later(
            self.debounce_seconds,
            lambda: self.hass.async_create_task(
                self._async_send_pending(),
                f"send {self.name} panel pattern",
            ),
        )

    async def _async_send_pending(self) -> None:
        self._send_timer = None
        async with self._send_lock:
            while self._dirty and not self._closed:
                self._dirty = False
                colors = tuple(panel.output_rgb for panel in self.panels)
                datagram = build_ptreal_datagram(colors)
                started = time.monotonic()
                try:
                    await self.hass.async_add_executor_job(self._send_udp, datagram)
                except OSError as err:
                    self.last_error = str(err)
                    _LOGGER.exception("Could not send H6069 panel pattern to %s", self.host)
                else:
                    self.last_error = None
                    self.successful_uploads += 1
                self.last_send_duration = time.monotonic() - started
                self._notify_listeners()

    async def async_commit(self) -> None:
        """Bypass debounce and send the latest complete frame now."""
        if self._send_timer is not None:
            self._send_timer.cancel()
            self._send_timer = None
        await self._async_send_pending()

    async def async_refresh_topology(self) -> None:
        """Read the learned panel shape without changing any visible output."""
        async with self._topology_lock:
            try:
                topology = await self.hass.async_add_executor_job(
                    query_topology, self.host
                )
            except Exception as err:
                self.topology_error = str(err)
                _LOGGER.warning(
                    "Could not read H6069 topology from %s: %s", self.host, err
                )
                self._notify_listeners()
                raise
            self.topology = topology
            self.topology_last_updated = datetime.now(timezone.utc).isoformat()
            self.topology_error = None
            self.topology_queries += 1
            self._notify_listeners()

    def _send_udp(self, datagram: bytes) -> None:
        """Send one complete ptReal datagram from an executor thread."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.sendto(datagram, (self.host, UDP_PORT))

    async def async_shutdown(self) -> None:
        """Cancel pending work when the config entry unloads."""
        self._closed = True
        if self._send_timer is not None:
            self._send_timer.cancel()
            self._send_timer = None

    @property
    def pending(self) -> bool:
        """Return whether a complete frame is waiting to be sent."""
        return self._dirty or self._send_timer is not None

    @property
    def diagnostics(self) -> dict[str, Any]:
        """Return non-sensitive runtime diagnostics."""
        return {
            "host": self.host,
            "panel_count": self.panel_count,
            "last_error": self.last_error,
            "pending": self.pending,
            "last_send_duration_seconds": self.last_send_duration,
            "successful_uploads": self.successful_uploads,
            "acknowledgement": "UDP send only; physical state is optimistic",
            "topology": {
                "available": self.topology is not None,
                "last_updated": self.topology_last_updated,
                "last_error": self.topology_error,
                "successful_queries": self.topology_queries,
                "fingerprint": (
                    self.topology.fingerprint if self.topology is not None else None
                ),
            },
        }
