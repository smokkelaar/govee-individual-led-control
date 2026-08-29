"""Authenticated direct-Bluetooth client for Govee H70B3 Curtain Lights 2."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import TYPE_CHECKING

from bleak import BleakClient
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    close_stale_connections_by_address,
    establish_connection,
)
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .crypto import PAIRING_KEY, protect, unprotect
from .h70b3_protocol import (
    DEFAULT_MTU_PACKET_SIZE,
    RGB,
    build_upload_packets,
    checked_frame,
    checksum_valid,
)

if TYPE_CHECKING:
    from asyncio import TimerHandle
    from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)

WRITE_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
NOTIFY_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

# These checksum-valid requests were captured from Govee Home and then proven
# reusable in multiple fresh PC-to-curtain sessions.
HANDSHAKE_1 = bytes.fromhex(
    "E7 01 A0 75 49 61 24 4E 6A 32 19 A7 FF F4 A6 10 E0 CA FF FF"
)
HANDSHAKE_2 = bytes.fromhex(
    "E7 02 EF 85 BB AE 5D 1E 94 5C 37 13 8B ED AB 9F B0 44 32 A1"
)
DEVICE_INFO_REQUEST = bytes.fromhex(
    "33 09 08 38 0A 06 01 02 00 1D 08 EA 07 8A 82 92 6A 00 00 0D"
)
CAPABILITY_REQUEST = bytes.fromhex(
    "AC 03 03 41 39 40 00 00 00 00 00 00 00 00 00 00 00 00 00 94"
)
KEEPALIVE = checked_frame(b"\xAA")
ACTIVATE = checked_frame(bytes((0x33, 0x05, 0x0A, 0xFE)))

_MAX_CONNECT_ATTEMPTS = 4
_PACKET_GAP_SECONDS = 0.017
_KEEPALIVE_SECONDS = 1.0


class H70B3TransportError(RuntimeError):
    """Raised when the curtain cannot complete an authenticated command."""


class H70B3BleClient:
    """Own one serialized BLE session and upload full 20x26 frames."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        name: str,
        idle_disconnect_seconds: int,
    ) -> None:
        self.hass = hass
        self.address = address
        self.name = name
        self.idle_disconnect_seconds = idle_disconnect_seconds

        self._client: BleakClient | None = None
        self._session_key: bytes | None = None
        self._notifications: asyncio.Queue[bytes] = asyncio.Queue()
        self._operation_lock = asyncio.Lock()
        self._keepalive_task: asyncio.Task[None] | None = None
        self._idle_handle: TimerHandle | None = None
        self._idle_generation = 0
        self._closed = False

        self.last_error: str | None = None
        self.last_send_duration: float | None = None
        self.last_packet_count: int | None = None
        self.last_packet_size: int | None = None
        self.successful_uploads = 0
        self.last_connection_source: str | None = None
        self.last_reachability: str | None = None

    def _fresh_ble_device(self) -> BLEDevice | None:
        return bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

    def _on_disconnected(self, client: BleakClient) -> None:
        if self._client is client:
            self._client = None
            self._session_key = None
        task = self._keepalive_task
        self._keepalive_task = None
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    def _on_notify(self, _sender: object, data: bytearray) -> None:
        self._notifications.put_nowait(bytes(data))

    async def _write_protected(self, plain: bytes, key: bytes) -> None:
        client = self._client
        if client is None or not client.is_connected:
            raise H70B3TransportError("Bluetooth connection was lost")
        await client.write_gatt_char(WRITE_UUID, protect(plain, key), response=False)

    async def _next_plain(
        self,
        key: bytes,
        prefix: bytes,
        *,
        timeout: float = 6.0,
    ) -> bytes:
        async with asyncio.timeout(timeout):
            while True:
                cipher = await self._notifications.get()
                plain = unprotect(cipher, key)
                _LOGGER.debug(
                    "H70B3 notification length=%d prefix=%s",
                    len(plain),
                    plain[:4].hex(),
                )
                if not plain.startswith(prefix):
                    continue
                if not checksum_valid(plain):
                    raise H70B3TransportError(
                        f"invalid checksum in response {plain.hex()}"
                    )
                return plain

    async def _negotiate_session(self) -> None:
        await self._write_protected(HANDSHAKE_1, PAIRING_KEY)
        response_1 = await self._next_plain(PAIRING_KEY, b"\xE7\x01")
        session_key = response_1[2:18]
        if len(session_key) != 16:
            raise H70B3TransportError("device supplied an invalid session key")

        await self._write_protected(HANDSHAKE_2, PAIRING_KEY)
        await self._next_plain(PAIRING_KEY, b"\xE7\x02")
        self._session_key = session_key

        await self._write_protected(checked_frame(b"\xAA\x60\x01"), session_key)
        await self._next_plain(session_key, b"\xAA\x60\x01")

        await self._write_protected(DEVICE_INFO_REQUEST, session_key)
        await self._next_plain(session_key, b"\x33\x09")

        await self._write_protected(CAPABILITY_REQUEST, session_key)
        while True:
            capability = await self._next_plain(session_key, b"\xAC", timeout=8.0)
            if capability.startswith(b"\xAC\xFF"):
                break

        await self._write_protected(KEEPALIVE, session_key)
        await self._next_plain(session_key, b"\xAA\x00")

    async def _ensure_ready(self) -> None:
        if (
            self._client is not None
            and self._client.is_connected
            and self._session_key is not None
        ):
            return
        if self._closed:
            raise H70B3TransportError("Bluetooth client has been shut down")

        device = self._fresh_ble_device()
        if device is None:
            diagnostics = getattr(
                bluetooth, "async_address_reachability_diagnostics", None
            )
            intent_type = getattr(bluetooth, "BluetoothReachabilityIntent", None)
            self.last_reachability = (
                diagnostics(self.hass, self.address, intent_type.CONNECTION)
                if diagnostics is not None and intent_type is not None
                else "no connectable Bluetooth adapter or active proxy currently sees it"
            )
            raise H70B3TransportError(
                f"{self.name} ({self.address}) is not currently connectable over "
                f"Bluetooth: {self.last_reachability}"
            )
        self.last_reachability = None
        details = device.details
        self.last_connection_source = (
            str(details.get("source", "unknown"))
            if isinstance(details, dict)
            else type(details).__name__
        )
        await close_stale_connections_by_address(self.address)

        def ble_device_callback() -> BLEDevice:
            fresh = self._fresh_ble_device()
            return fresh if fresh is not None else device

        self._notifications = asyncio.Queue()
        self._client = await establish_connection(
            BleakClientWithServiceCache,
            device=device,
            name=self.name,
            disconnected_callback=self._on_disconnected,
            ble_device_callback=ble_device_callback,
            max_attempts=_MAX_CONNECT_ATTEMPTS,
            use_services_cache=True,
        )
        try:
            await self._client.start_notify(NOTIFY_UUID, self._on_notify)
            await self._negotiate_session()
        except Exception:
            await self._disconnect_unlocked()
            raise

        self._keepalive_task = self.hass.async_create_task(
            self._keepalive_loop(), f"{self.name} BLE keepalive"
        )
        _LOGGER.debug("Authenticated BLE session established with %s", self.address)

    async def _send_frame_unlocked(
        self, colors: tuple[RGB, ...], brightness: int
    ) -> None:
        await self._ensure_ready()
        session_key = self._session_key
        if session_key is None:
            raise H70B3TransportError("encrypted session is not initialized")

        client = self._client
        if client is None:
            raise H70B3TransportError("Bluetooth connection was lost")
        characteristic = client.services.get_characteristic(WRITE_UUID)
        if characteristic is None:
            raise H70B3TransportError("H70B3 write characteristic is missing")
        max_write = characteristic.max_write_without_response_size
        packet_size = min(DEFAULT_MTU_PACKET_SIZE, int(max_write))
        if packet_size < 20:
            raise H70B3TransportError(
                f"Bluetooth path permits only {packet_size}-byte writes; at least 20 required"
            )
        packets = build_upload_packets(
            colors, brightness=brightness, packet_size=packet_size
        )
        self.last_packet_count = len(packets)
        self.last_packet_size = packet_size
        for packet in packets:
            # Encryption state is deliberately reset for every GATT write.
            await self._write_protected(packet, session_key)
            await asyncio.sleep(_PACKET_GAP_SECONDS)
        await self._next_plain(session_key, b"\xA4\x58", timeout=8.0)

        await self._write_protected(ACTIVATE, session_key)
        await self._next_plain(session_key, b"\x33\x05", timeout=8.0)

    async def async_send_frame(
        self, colors: tuple[RGB, ...], brightness: int
    ) -> None:
        """Upload and activate a complete frame, retrying one fresh session."""
        started = time.monotonic()
        last_exception: Exception | None = None
        for attempt in range(2):
            async with self._operation_lock:
                try:
                    await self._send_frame_unlocked(colors, brightness)
                except Exception as err:  # BLE backends expose several error types.
                    last_exception = err
                    await self._disconnect_unlocked()
                    if attempt == 0:
                        _LOGGER.warning(
                            "H70B3 upload failed; retrying a fresh BLE session: %s", err
                        )
                    continue
                self.last_error = None
                self.last_send_duration = time.monotonic() - started
                self.successful_uploads += 1
                self._schedule_idle_disconnect()
                return

        self.last_send_duration = time.monotonic() - started
        self.last_error = str(last_exception)
        raise H70B3TransportError(
            f"frame upload failed after reconnect: {last_exception}"
        ) from last_exception

    def _schedule_idle_disconnect(self) -> None:
        self._idle_generation += 1
        generation = self._idle_generation
        if self._idle_handle is not None:
            self._idle_handle.cancel()
        loop = asyncio.get_running_loop()
        self._idle_handle = loop.call_later(
            self.idle_disconnect_seconds,
            lambda: self.hass.async_create_task(
                self._async_idle_disconnect(generation),
                f"disconnect idle {self.name} BLE session",
            ),
        )

    async def _async_idle_disconnect(self, generation: int) -> None:
        async with self._operation_lock:
            if generation != self._idle_generation:
                return
            self._idle_handle = None
            await self._disconnect_unlocked()

    async def _keepalive_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(_KEEPALIVE_SECONDS)
                if self._operation_lock.locked():
                    continue
                async with self._operation_lock:
                    key = self._session_key
                    client = self._client
                    if key is None or client is None or not client.is_connected:
                        return
                    await self._write_protected(KEEPALIVE, key)
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.debug("H70B3 keepalive ended: %s", err)
            async with self._operation_lock:
                await self._disconnect_unlocked()

    async def _disconnect_unlocked(self) -> None:
        self._session_key = None
        task = self._keepalive_task
        self._keepalive_task = None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
        client, self._client = self._client, None
        if client is not None:
            with contextlib.suppress(Exception):
                if client.is_connected:
                    await client.stop_notify(NOTIFY_UUID)
            with contextlib.suppress(Exception):
                await client.disconnect()

    async def async_shutdown(self) -> None:
        """Stop timers and release the BLE connection."""
        self._closed = True
        self._idle_generation += 1
        if self._idle_handle is not None:
            self._idle_handle.cancel()
            self._idle_handle = None
        async with self._operation_lock:
            await self._disconnect_unlocked()

    @property
    def connected(self) -> bool:
        """Return whether an authenticated connection is alive."""
        return bool(
            self._client is not None
            and self._client.is_connected
            and self._session_key is not None
        )
