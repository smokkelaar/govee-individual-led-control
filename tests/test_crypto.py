"""Round-trip tests for the per-GATT-write H70B3 protection envelope."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "govee_led_control"
spec = importlib.util.spec_from_file_location("h70b3_crypto_test", COMPONENT / "crypto.py")
assert spec is not None and spec.loader is not None
crypto = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crypto)


class CryptoTests(unittest.TestCase):
    def test_round_trip_at_aes_and_rc4_boundaries(self) -> None:
        for length in (0, 1, 4, 15, 16, 17, 20, 32, 137, 509):
            with self.subTest(length=length):
                plain = bytes((index * 37 + 11) % 256 for index in range(length))
                cipher = crypto.protect(plain, crypto.PAIRING_KEY)
                self.assertEqual(len(cipher), length)
                self.assertEqual(crypto.unprotect(cipher, crypto.PAIRING_KEY), plain)

    def test_each_short_write_resets_rc4(self) -> None:
        plain = bytes.fromhex("A4 FF FF A4")
        first = crypto.protect(plain, crypto.PAIRING_KEY)
        second = crypto.protect(plain, crypto.PAIRING_KEY)
        self.assertEqual(first, second)
        self.assertNotEqual(first, plain)

    def test_key_must_be_16_bytes(self) -> None:
        with self.assertRaises(ValueError):
            crypto.protect(b"test", b"short")


if __name__ == "__main__":
    unittest.main()
