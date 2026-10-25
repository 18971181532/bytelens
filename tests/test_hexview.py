import unittest

from bytelens.hexview import dump_window, hexdump


class TestHexview(unittest.TestCase):
    def test_row_width(self):
        rows = hexdump(b"A" * 16)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["hex"]), 16)
        self.assertEqual(rows[0]["ascii"], "A" * 16)

    def test_multi_rows(self):
        rows = hexdump(b"B" * 40)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1]["offset"], 16)

    def test_nonprintable_ascii(self):
        rows = hexdump(bytes([0x00, 0x01, 0x41]))
        self.assertTrue(rows[0]["ascii"].startswith("..A"))

    def test_base_offset(self):
        rows = hexdump(b"X", base=256)
        self.assertEqual(rows[0]["offset"], 256)

    def test_window_navigation(self):
        sample = bytes(range(256)) * 2  # 512 bytes
        win = dump_window(sample, 0, 256)
        self.assertEqual(win["next_offset"], 256)
        self.assertIsNone(win["prev_offset"])
        win2 = dump_window(sample, 256, 256)
        self.assertIsNone(win2["next_offset"])
        self.assertEqual(win2["prev_offset"], 0)

    def test_window_clamps_offset(self):
        win = dump_window(b"abcd", 9999, 16)
        self.assertEqual(win["rows"], [])

    def test_window_returns_hex(self):
        win = dump_window(b"AB", 0, 16)
        self.assertEqual(win["rows"][0]["hex"][:2], ["41", "42"])


if __name__ == "__main__":
    unittest.main()
