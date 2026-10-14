"""A real Bluetooth refresh and damaged transfers, without radio I/O."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = load("h6069_bt_probe_test", ROOT / "scripts/h6069_bluetooth_topology.py")
topology = load("h6069_bt_decoder_test", ROOT / "custom_components/govee_led_control/h6069_topology.py")
CAPTURED = tuple(bytes.fromhex(value) for value in (
    "ac0008000702002820020520080220020820018f",
    "ac010220010220010820040220040820010420aa",
    "ac02080120010420020120080420010420040884",
    "ac032004082002082008042002042008012004ae",
    "ac040020020820040120080420010220010820a1",
    "ac05040220010220080120020120080420010289",
    "ac062004082001082001042008042001042004a7",
    "acff022002042004000000000000000000000053",
))


class BluetoothTopologyTests(unittest.TestCase):
    def test_live_refresh_decodes_changed_wiring(self):
        decoded = topology.decode_topology_pt(probe.import_pt_from_reply(CAPTURED))
        self.assertEqual(decoded.panel_count, 40)
        self.assertEqual(decoded.fingerprint, "8b4ab68acdc14ae1")
        self.assertEqual(decoded.number_grid[0], (35, 36, 37, None, 19, 18, None, None))
        self.assertEqual(decoded.number_grid[-1], (None, 23, 22, 21, 0, 1, 2, 3))
        self.assertEqual(decoded.placements[0].input_side, 2)
        self.assertEqual([e["child"] for e in decoded.links if e["parent"] == 0], [1, 21])

    def test_rejects_missing_duplicate_and_reordered_frames(self):
        for frames in (CAPTURED[:-1], CAPTURED[:2] + CAPTURED[3:],
                       CAPTURED[:2] + CAPTURED[1:],
                       (CAPTURED[1], CAPTURED[0]) + CAPTURED[2:]):
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                probe.import_pt_from_reply(frames)

    def test_rejects_checksum_damage(self):
        damaged = bytearray(CAPTURED[2])
        damaged[7] ^= 1
        with self.assertRaises(ValueError):
            probe.import_pt_from_reply(CAPTURED[:2] + (bytes(damaged),) + CAPTURED[3:])

    def test_rejects_wrong_response_command(self):
        first = bytearray(CAPTURED[0][:-1])
        first[5] = 3
        with self.assertRaises(ValueError):
            probe.import_pt_from_reply((probe.checked_frame(first),) + CAPTURED[1:])

    def test_rejects_nonzero_trailing_data(self):
        last = bytearray(CAPTURED[-1][:-1])
        last[18] = 1
        with self.assertRaises(ValueError):
            probe.import_pt_from_reply(CAPTURED[:-1] + (probe.checked_frame(last),))

    def test_import_still_rejects_invalid_connection_tree(self):
        first = bytearray(CAPTURED[0][:-1])
        first[9] = 3
        pt = probe.import_pt_from_reply((probe.checked_frame(first),) + CAPTURED[1:])
        with self.assertRaises(topology.H6069TopologyError):
            topology.decode_topology_pt(pt)


if __name__ == "__main__":
    unittest.main()
