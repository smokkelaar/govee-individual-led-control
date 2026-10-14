"""Explicit H6069 Bluetooth recognition read, with cleanup and import output."""
import argparse
import asyncio
import base64
import contextlib
import importlib.util
import json
from pathlib import Path
import sys

WRITE = "00010203-0405-0607-0809-0a0b0c0d2b11"
NOTIFY = "00010203-0405-0607-0809-0a0b0c0d2b10"
HANDSHAKES = tuple(bytes.fromhex(value) for value in (
    "e701a0754961244e6a3219a7fff4a610e0caffff",
    "e702ef85bbae5d1e945c37138bedab9fb04432a1",
))


def checked_frame(prefix):
    if not 1 <= len(prefix) <= 19:
        raise ValueError("request needs 1..19 bytes before checksum")
    body = bytes(prefix).ljust(19, b"\0")
    checksum = 0
    for value in body:
        checksum ^= value
    return body + bytes((checksum,))


def checksum_valid(frame):
    checksum = 0
    for value in frame:
        checksum ^= value
    return len(frame) == 20 and checksum == 0


def import_pt_from_reply(frames):
    """Convert verified AC frames to a synthesized import, not a LAN capture."""
    if len(frames) < 2 or any(not checksum_valid(f) or f[0] != 0xAC for f in frames):
        raise ValueError("incomplete or checksum-invalid Bluetooth response")
    if [f[1] for f in frames] != list(range(len(frames) - 1)) + [0xFF]:
        raise ValueError("missing, duplicate or reordered Bluetooth frames")
    payload = b"".join(f[2:19] for f in frames)
    if payload[0] != len(frames) or payload[3:5] != b"\x02\x00":
        raise ValueError("unexpected topology response header")
    # The meaning of transport-header bytes 1..2 has not been established.
    count = payload[5]
    end = 6 + count * 3
    if not 1 <= count <= 70 or end > len(payload) or any(payload[end:]):
        raise ValueError("invalid count, truncated records or nonzero trailing data")
    records = payload[6:end]
    body = b"\xbb" + (4 + len(records)).to_bytes(2, "big") + bytes((0xB2, 0, count, 0, 0xB4)) + records
    checksum = 0
    for value in body:
        checksum ^= value
    return base64.b64encode(body + bytes((checksum,))).decode("ascii")


def load_module(name, filename):
    folder = Path(__file__).resolve().parents[1] / "custom_components/govee_led_control"
    spec = importlib.util.spec_from_file_location(name, folder / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


async def read_topology(address):
    from bleak import BleakClient, BleakScanner
    crypto = load_module("h6069_probe_crypto", "crypto.py")
    device = await BleakScanner.find_device_by_address(address, timeout=12)
    if device is None or "H6069" not in (device.name or "").upper():
        raise RuntimeError("H6069 not visible; close Govee Home and check range")
    async with BleakClient(device, timeout=20) as client:
        queue = asyncio.Queue()
        await client.start_notify(NOTIFY, lambda _, data: queue.put_nowait(bytes(data)))

        async def write(plain, key):
            await client.write_gatt_char(WRITE, crypto.protect(plain, key), response=False)

        async def receive(key, prefix, timeout=6):
            async with asyncio.timeout(timeout):
                while True:
                    plain = crypto.unprotect(await queue.get(), key)
                    if plain.startswith(prefix):
                        if not checksum_valid(plain):
                            raise ValueError("invalid Bluetooth response checksum")
                        return plain

        key = None
        for request in HANDSHAKES:
            await write(request, crypto.PAIRING_KEY)
            reply = await receive(crypto.PAIRING_KEY, request[:2])
            if request[1] == 1:
                key = reply[2:18]
        if key is None or len(key) != 16:
            raise RuntimeError("invalid Bluetooth session key")
        await write(checked_frame(b"\xaa\x60\x01"), key)
        await receive(key, b"\xaa\x60\x01")

        async def keepalive():
            while True:
                await asyncio.sleep(1)
                await write(checked_frame(b"\xaa"), key)

        heartbeat = None
        entered = False
        try:
            # Recognition mode can temporarily change the visible display.
            entered = True
            await write(checked_frame(b"\x33\x45\x00"), key)
            await receive(key, b"\x33\x45")
            await asyncio.sleep(0.3)
            heartbeat = asyncio.create_task(keepalive())
            await write(checked_frame(b"\xac\x02\x00"), key)
            frames = []
            async with asyncio.timeout(12):
                while True:
                    frame = await receive(key, b"\xac", 12)
                    frames.append(frame)
                    if frame[1] == 0xFF:
                        break
            import_pt_from_reply(frames)
            return frames
        finally:
            if heartbeat is not None:
                heartbeat.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat
            if entered and client.is_connected:
                await write(checked_frame(b"\x33\x45\xff"), key)
                await receive(key, b"\x33\x45")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True, help="H6069 Bluetooth MAC, not wifi MAC")
    parser.add_argument("--output", type=Path, help="optional local JSON destination")
    args = parser.parse_args()
    frames = asyncio.run(read_topology(args.address))
    pt = import_pt_from_reply(frames)
    decoder = load_module("h6069_probe_decoder", "h6069_topology.py")
    topology = decoder.decode_topology_pt(pt, source="authenticated Bluetooth recognition refresh")
    result = {"import_pt": pt, "import_envelope_is_synthesized": True,
              "bluetooth_frames": [f.hex() for f in frames], **topology.state_attributes}
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(topology.grid_text)
    print(f"\nValidated {topology.panel_count} panels; fingerprint {topology.fingerprint}")
    print(f"Shape Recognition import:\n{pt}")


if __name__ == "__main__":
    main()
