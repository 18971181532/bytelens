import unittest

from bytelens import magic
from tests.helpers import make_png, make_zip


class TestMagic(unittest.TestCase):
    def test_png(self):
        m = magic.identify(make_png())
        self.assertEqual(m["extension"], "png")
        self.assertEqual(m["kind"], "image")

    def test_zip(self):
        m = magic.identify(make_zip())
        self.assertEqual(m["extension"], "zip")

    def test_jpeg(self):
        m = magic.identify(b"\xFF\xD8\xFF\xE0")
        self.assertEqual(m["extension"], "jpg")

    def test_elf(self):
        m = magic.identify(b"\x7fELF\x02\x01")
        self.assertEqual(m["extension"], "elf")

    def test_pe(self):
        m = magic.identify(b"MZ\x90\x00")
        self.assertEqual(m["extension"], "exe")

    def test_pdf(self):
        m = magic.identify(b"%PDF-1.7")
        self.assertEqual(m["extension"], "pdf")

    def test_unknown(self):
        self.assertIsNone(magic.identify(bytes([0x01, 0x02, 0x03])))

    def test_text(self):
        m = magic.identify_text(b"<?xml version='1.0'?>\n<a/>")
        self.assertEqual(m["extension"], "xml")
        self.assertIsNone(magic.identify_text(b"\x00\x01\x02\x03"))

    def test_scan_finds_embedded(self):
        wrapper = b"X" * 50 + make_png() + b"Y" * 10
        hits = magic.scan(wrapper)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["offset"], 50)
        self.assertEqual(hits[0]["extension"], "png")

    def test_scan_excludes_offset_zero(self):
        hits = magic.scan(make_png())
        self.assertFalse(any(h["offset"] == 0 for h in hits))

    def test_wildcard_zip(self):
        # ZIP signature exact
        self.assertIsNotNone(magic.identify(b"PK\x03\x04rest"))


if __name__ == "__main__":
    unittest.main()
