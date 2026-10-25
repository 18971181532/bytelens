import unittest

from bytelens.histogram import byte_counts, byte_heatmap, composition, histogram


class TestHistogram(unittest.TestCase):
    def test_counts(self):
        c = byte_counts(b"AAB")
        self.assertEqual(c[ord("A")], 2)
        self.assertEqual(c[ord("B")], 1)
        self.assertEqual(sum(c), 3)

    def test_composition_printable(self):
        comp = composition(b"hello world")
        self.assertGreater(comp["printable_ratio"], 0.9)
        self.assertEqual(comp["nulls"], 0)

    def test_composition_nulls(self):
        comp = composition(b"\x00\x00\x00\x00")
        self.assertEqual(comp["null_ratio"], 1.0)

    def test_high_bytes(self):
        comp = composition(bytes([0xFF, 0x80, 0x90, 0xAB]))
        self.assertEqual(comp["high_ratio"], 1.0)

    def test_empty(self):
        self.assertEqual(histogram(b"")["total"], 0)

    def test_distinct(self):
        self.assertEqual(histogram(b"AABB")["distinct"], 2)

    def test_top_bytes(self):
        top = histogram(b"AAAB")["top"][0]
        self.assertEqual(top["byte"], ord("A"))

    def test_glyph(self):
        self.assertEqual(histogram(b"A")["top"][0]["char"], "A")

    def test_heatmap_shape(self):
        hm = byte_heatmap(b"x" * 1000, columns=32, buckets=16)
        self.assertEqual(hm["columns"], 32)
        self.assertEqual(len(hm["grid"]), 32)
        self.assertEqual(len(hm["grid"][0]), 16)

    def test_heatmap_high_bucket(self):
        # 0xFF belongs to high-nibble bucket 15
        hm = byte_heatmap(b"\xff" * 100, columns=1, buckets=16)
        self.assertEqual(hm["grid"][0][15], 1.0)


if __name__ == "__main__":
    unittest.main()
