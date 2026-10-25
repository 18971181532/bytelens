import math
import os
import unittest

from bytelens.entropy import (block_entropy, classify, shannon,
                              shannon_from_counts, entropy_summary)


class TestEntropy(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(shannon(b""), 0.0)

    def test_constant_is_zero(self):
        self.assertEqual(shannon(b"AAAA"), 0.0)

    def test_two_equal_symbols_is_one(self):
        self.assertAlmostEqual(shannon(b"AB"), 1.0, places=6)
        self.assertAlmostEqual(shannon(b"AABB"), 1.0, places=6)

    def test_known_formula(self):
        data = bytes([0, 0, 1, 1])
        self.assertAlmostEqual(shannon(data), 1.0, places=6)

    def test_random_high_entropy(self):
        data = os.urandom(8192)
        self.assertGreater(shannon(data), 7.5)

    def test_bounded_max(self):
        self.assertLessEqual(shannon(os.urandom(4096)), 8.0)

    def test_from_counts(self):
        self.assertAlmostEqual(shannon_from_counts([2, 2], 4), 1.0, 6)

    def test_block_entropy(self):
        blocks = block_entropy(b"A" * 4096 + os.urandom(4096), 4096)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["entropy"], 0.0)
        self.assertGreater(blocks[1]["entropy"], 7.5)

    def test_overlapping_step(self):
        blocks = block_entropy(b"A" * 400, 100, step=100)
        self.assertEqual(len(blocks), 4)

    def test_classify(self):
        self.assertEqual(classify(0.0), "trivial/constant")
        self.assertIn("text", classify(4.5))
        self.assertIn("encrypted", classify(7.9))

    def test_summary(self):
        s = entropy_summary(os.urandom(8192), 4096)
        self.assertEqual(len(s["blocks"]), 2)
        self.assertGreater(s["max_block"], 7.0)


if __name__ == "__main__":
    unittest.main()
