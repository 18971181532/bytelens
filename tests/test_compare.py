import unittest

from bytelens.compare import compare


class TestCompare(unittest.TestCase):
    def test_identical(self):
        r = compare(b"hello world" * 500, b"hello world" * 500)
        self.assertEqual(r["jaccard_similarity"], 1.0)
        self.assertEqual(r["size_delta"], 0)
        self.assertEqual(r["entropy_delta"], 0.0)
        self.assertTrue(r["aligned"]["equal"])
        self.assertEqual(r["aligned"]["differing_bytes"], 0)

    def test_different(self):
        a = b"aaaaaaaaaaaaaaaa"
        b = b"bbbbbbbbbbbbbbbb"
        r = compare(a, b)
        self.assertEqual(r["aligned"]["differing_bytes"], 16)
        self.assertEqual(r["aligned"]["percent"], 100.0)
        # entirely different 4 KiB blocks => no shared blocks
        self.assertEqual(r["jaccard_similarity"], 0.0)

    def test_size_difference(self):
        r = compare(b"short", b"a much longer byte sequence here")
        self.assertEqual(r["size_delta"],
                         len(b"a much longer byte sequence here") - 5)
        self.assertIsNone(r["aligned"])

    def test_shared_blocks(self):
        block = b"X" * 4096
        a = block + b"0" * 4096
        b = block + b"1" * 4096
        r = compare(a, b)
        self.assertEqual(r["shared_blocks"], 1)

    def test_strings_added_removed(self):
        a = b"unique_alpha" + b"\x00" * 40
        b = b"unique_beta" + b"\x00" * 40
        r = compare(a, b)
        self.assertIn("unique_beta", r["strings_added"])
        self.assertIn("unique_alpha", r["strings_removed"])

    def test_empty_files(self):
        r = compare(b"", b"")
        self.assertEqual(r["jaccard_similarity"], 1.0)


if __name__ == "__main__":
    unittest.main()
