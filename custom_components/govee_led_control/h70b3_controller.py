"""Framebuffer, entity state and debounced transport for the H70B3."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    H70B3_HEIGHT as HEIGHT,
    H70B3_PIXEL_COUNT as PIXEL_COUNT,
    H70B3_WIDTH as WIDTH,
)
from .h70b3_ble import H70B3BleClient
from .h70b3_protocol import (
    RGB,
    make_orientation_demo,
    make_x_demo,
    transform_frame,
    validate_rgb,
)
from .visualization import h70b3_level_frame

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PixelState:
    """Optimistic state for one physical LED."""

    is_on: bool = False
    rgb: RGB = (255, 255, 255)
    brightness: int = 255

    @property
    def output_rgb(self) -> RGB:
        """Return the actual RGB value encoded into the image."""
        if not self.is_on:
            return (0, 0, 0)
        return tuple(
            max(0, min(255, round(channel * self.brightness / 255)))
            for channel in self.rgb
        )  # type: ignore[return-value]


class H70B3Controller:
    """Own the complete 520-pixel snapshot and serialize outgoing images."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        name: str,
        debounce_ms: int,
        idle_disconnect_seconds: int,
    ) -> None:
        self.hass = hass
        self.address = address
        self.name = name
        self.device_id = f"h70b3_{address.replace(':', '').lower()}"
        self.debounce_seconds = debounce_ms / 1000
        self.transport = H70B3BleClient(
            hass, address, name, idle_disconnect_seconds
        )

        self.pixels = [PixelState() for _ in range(PIXEL_COUNT)]
        self.global_brightness = 100
        self.matrix_rgb: RGB = (255, 255, 255)
        self.flip_horizontal = False
        self.flip_vertical = False
        self.last_error: str | None = None

        self._pixel_listeners: dict[int, set[Callable[[], None]]] = {}
        self._matrix_listeners: set[Callable[[], None]] = set()
        self._send_timer: asyncio.TimerHandle | None = None
        self._send_lock = asyncio.Lock()
        self._dirty = False
        self._closed = False

    @staticmethod
    def index(x: int, y: int) -> int:
        """Map zero-based x/y coordinates to the row-major protocol index."""
        if not 0 <= x < WIDTH or not 0 <= y < HEIGHT:
            raise ValueError(f"coordinate ({x}, {y}) is outside 20x26")
        return y * WIDTH + x

    def add_pixel_listener(
        self, pixel_index: int, listener: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback for one LED only."""
        listeners = self._pixel_listeners.setdefault(pixel_index, set())
        listeners.add(listener)

        def remove_listener() -> None:
            listeners.discard(listener)

        return remove_listener

    def add_matrix_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for aggregate state and diagnostics."""
        self._matrix_listeners.add(listener)

        def remove_listener() -> None:
            self._matrix_listeners.discard(listener)

        return remove_listener

    @staticmethod
    def _notify(callbacks: Iterable[Callable[[], None]]) -> None:
        for listener in tuple(callbacks):
            listener()

    def _notify_pixels(self, indices: Iterable[int]) -> None:
        for index in indices:
            self._notify(self._pixel_listeners.get(index, ()))

    def _notify_matrix(self) -> None:
        self._notify(self._matrix_listeners)

    def restore_pixel(
        self,
        pixel_index: int,
        *,
        is_on: bool,
        rgb: RGB,
        brightness: int,
    ) -> None:
        """Restore HA state without modifying the physical curtain."""
        self.pixels[pixel_index] = PixelState(
            is_on=is_on,
            rgb=validate_rgb(rgb),
            brightness=max(1, min(255, int(brightness))),
        )
        self._notify_matrix()

    def restore_matrix(self, *, rgb: RGB, brightness_percent: int) -> None:
        """Restore aggregate color and brightness without transmitting."""
        self.matrix_rgb = validate_rgb(rgb)
        self.global_brightness = max(1, min(100, int(brightness_percent)))

    def restore_flip(self, axis: str, enabled: bool) -> None:
        """Restore a mirror switch without transmitting during startup."""
        if axis == "horizontal":
            self.flip_horizontal = enabled
        elif axis == "vertical":
            self.flip_vertical = enabled
        else:
            raise ValueError(f"unknown mirror axis {axis!r}")
        self._notify_matrix()

    def set_flip(self, axis: str, enabled: bool) -> None:
        """Change one physical output transform and resend the current frame."""
        self.restore_flip(axis, enabled)
        self._mark_dirty()
        self._notify_matrix()

    def update_pixel(
        self,
        pixel_index: int,
        *,
        is_on: bool | None = None,
        rgb: RGB | None = None,
        brightness: int | None = None,
    ) -> None:
        """Change one LED and schedule one coalesced frame upload."""
        pixel = self.pixels[pixel_index]
        if is_on is not None:
            pixel.is_on = is_on
        if rgb is not None:
            pixel.rgb = validate_rgb(rgb)
        if brightness is not None:
            pixel.brightness = max(1, min(255, int(brightness)))
        self._mark_dirty()
        self._notify_pixels((pixel_index,))
        self._notify_matrix()

    def update_matrix(
        self,
        *,
        is_on: bool,
        rgb: RGB | None = None,
        brightness: int | None = None,
    ) -> None:
        """Turn/recolor every LED as one logical matrix light."""
        if rgb is not None:
            self.matrix_rgb = validate_rgb(rgb)
        if brightness is not None:
            self.global_brightness = max(
                1, min(100, round(int(brightness) * 100 / 255))
            )
        for pixel in self.pixels:
            pixel.is_on = is_on
            if rgb is not None:
                pixel.rgb = self.matrix_rgb
                pixel.brightness = 255
        self._mark_dirty()
        self._notify_pixels(range(PIXEL_COUNT))
        self._notify_matrix()

    def set_pixels(
        self,
        updates: Mapping[int, RGB],
        *,
        replace: bool,
        brightness_percent: int | None = None,
    ) -> None:
        """Apply several pixel changes atomically to the in-memory frame."""
        changed: set[int] = set()
        if replace:
            for index, pixel in enumerate(self.pixels):
                if pixel.is_on:
                    changed.add(index)
                pixel.is_on = False
        for index, rgb in updates.items():
            if not 0 <= index < PIXEL_COUNT:
                raise ValueError(f"pixel index {index} is outside 0..{PIXEL_COUNT - 1}")
            normalized = validate_rgb(rgb)
            pixel = self.pixels[index]
            pixel.rgb = normalized
            pixel.brightness = 255
            pixel.is_on = normalized != (0, 0, 0)
            changed.add(index)
        if brightness_percent is not None:
            self.global_brightness = max(1, min(100, int(brightness_percent)))
        self._mark_dirty()
        self._notify_pixels(changed)
        self._notify_matrix()

    def set_frame(
        self, colors: tuple[RGB, ...], *, brightness_percent: int | None = None
    ) -> None:
        """Replace all 520 pixels in row-major order."""
        if len(colors) != PIXEL_COUNT:
            raise ValueError(f"a frame requires exactly {PIXEL_COUNT} colors")
        for index, raw_rgb in enumerate(colors):
            rgb = validate_rgb(raw_rgb)
            self.pixels[index] = PixelState(
                is_on=rgb != (0, 0, 0), rgb=rgb, brightness=255
            )
        if brightness_percent is not None:
            self.global_brightness = max(1, min(100, int(brightness_percent)))
        self._mark_dirty()
        self._notify_pixels(range(PIXEL_COUNT))
        self._notify_matrix()

    def clear(self) -> None:
        """Turn every LED black while retaining each last chosen color."""
        for pixel in self.pixels:
            pixel.is_on = False
        self._mark_dirty()
        self._notify_pixels(range(PIXEL_COUNT))
        self._notify_matrix()

    def show_demo(self) -> None:
        """Load the physically verified red/blue X pattern."""
        self.set_frame(make_x_demo(), brightness_percent=100)

    def show_orientation(self) -> None:
        """Load the four-corner physical orientation pattern."""
        self.set_frame(make_orientation_demo(), brightness_percent=100)

    def apply_level(self, level: int, style: str) -> None:
        """Map a normalized HA sensor value to a deterministic 20x26 image."""
        self.set_frame(
            h70b3_level_frame(level, style, WIDTH, HEIGHT),
            brightness_percent=100,
        )

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._schedule_send()

    def _schedule_send(self) -> None:
        if self._closed:
            return
        if self._send_timer is not None:
            self._send_timer.cancel()
        loop = asyncio.get_running_loop()
        self._send_timer = loop.call_later(
            self.debounce_seconds,
            lambda: self.hass.async_create_task(
                self._async_send_pending(), f"send {self.name} pixel frame"
            ),
        )

    async def async_commit(self) -> None:
        """Bypass the remaining debounce delay and flush the latest frame."""
        if self._send_timer is not None:
            self._send_timer.cancel()
            self._send_timer = None
        await self._async_send_pending()

    async def _async_send_pending(self) -> None:
        self._send_timer = None
        async with self._send_lock:
            while self._dirty and not self._closed:
                self._dirty = False
                colors = self._output_colors()
                try:
                    await self.transport.async_send_frame(
                        colors, self.global_brightness
                    )
                except Exception as err:
                    self.last_error = str(err)
                    _LOGGER.exception("Could not send H70B3 frame to %s", self.address)
                else:
                    self.last_error = None
                self._notify_matrix()

    def _output_colors(self) -> tuple[RGB, ...]:
        """Transform logical coordinates to the currently selected mounting."""
        return transform_frame(
            tuple(pixel.output_rgb for pixel in self.pixels),
            flip_horizontal=self.flip_horizontal,
            flip_vertical=self.flip_vertical,
        )

    async def async_shutdown(self) -> None:
        """Cancel pending work and disconnect during config-entry unload."""
        self._closed = True
        if self._send_timer is not None:
            self._send_timer.cancel()
            self._send_timer = None
        async with self._send_lock:
            await self.transport.async_shutdown()

    @property
    def matrix_is_on(self) -> bool:
        """Return whether one or more pixels are lit."""
        return any(pixel.is_on for pixel in self.pixels)

    @property
    def pending(self) -> bool:
        """Return whether state is waiting to be sent."""
        return self._dirty or self._send_timer is not None

    @property
    def diagnostics(self) -> dict[str, Any]:
        """Return non-sensitive state useful for troubleshooting."""
        return {
            "address": self.address,
            "dimensions": f"{WIDTH}x{HEIGHT}",
            "pixel_count": PIXEL_COUNT,
            "global_brightness_percent": self.global_brightness,
            "flip_horizontal": self.flip_horizontal,
            "flip_vertical": self.flip_vertical,
            "lit_pixels": sum(pixel.is_on for pixel in self.pixels),
            "pending": self.pending,
            "connected": self.transport.connected,
            "connection_source": self.transport.last_connection_source,
            "reachability": self.transport.last_reachability,
            "last_error": self.last_error or self.transport.last_error,
            "last_send_duration_seconds": self.transport.last_send_duration,
            "last_packet_count": self.transport.last_packet_count,
            "last_packet_size": self.transport.last_packet_size,
            "successful_uploads": self.transport.successful_uploads,
        }
