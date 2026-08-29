"""H70B3 BLE transport protection primitives."""

from __future__ import annotations

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PAIRING_KEY = b"MakingLifeSmarte"


def rc4(data: bytes, key: bytes) -> bytes:
    """Apply RC4 with a fresh state for this one GATT write."""
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) % 256
        state[i], state[j] = state[j], state[i]
    result = bytearray(len(data))
    i = j = 0
    for index, value in enumerate(data):
        i = (i + 1) % 256
        j = (j + state[i]) % 256
        state[i], state[j] = state[j], state[i]
        result[index] = value ^ state[(state[i] + state[j]) % 256]
    return bytes(result)


def crypt_blob(data: bytes, key: bytes, *, encrypt: bool) -> bytes:
    """Apply AES-ECB to full blocks and RC4 to the remaining tail."""
    if len(key) != 16:
        raise ValueError("a Govee transport key must contain 16 bytes")
    full_length = len(data) - (len(data) % 16)
    result = bytearray(len(data))
    if full_length:
        cipher = Cipher(algorithms.AES(key), modes.ECB())
        transform = cipher.encryptor() if encrypt else cipher.decryptor()
        result[:full_length] = transform.update(data[:full_length]) + transform.finalize()
    if full_length < len(data):
        result[full_length:] = rc4(data[full_length:], key)
    return bytes(result)


def protect(data: bytes, key: bytes) -> bytes:
    """Protect one complete GATT write."""
    return crypt_blob(data, key, encrypt=True)


def unprotect(data: bytes, key: bytes) -> bytes:
    """Unprotect one complete GATT notification."""
    return crypt_blob(data, key, encrypt=False)
