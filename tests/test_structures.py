import unittest

from bytelens.structures import parse
from tests.helpers import make_elf64, make_pe, make_png, make_zip


class TestStructures(unittest.TestCase):
    def test_png_regions(self):
        png = make_png(7, 5)
        meta, regions = parse(png, "png")
        kinds = [r["name"] for r in regions]
        self.assertIn("signature", kinds)
        self.assertIn("IHDR", kinds)
        self.assertIn("IDAT", kinds)
        self.assertIn("IEND", kinds)
        self.assertEqual(meta["width"], 7)
        self.assertEqual(meta["height"], 5)
        self.assertEqual(meta["chunk_count"], 3)

    def test_png_region_offsets_contiguous(self):
        png = make_png()
        _, regions = parse(png, "png")
        iend = [r for r in regions if r["name"] == "IEND"][0]
        self.assertEqual(iend["end"], len(png))

    def test_zip_entries(self):
        z = make_zip()
        meta, regions = parse(z, "zip")
        self.assertEqual(meta["entry_count"], 2)
        names = [e["name"] for e in meta["entries"]]
        self.assertIn("hello.txt", names)
        self.assertIn("data/num.bin", names)
        # deflate compression for the incompressible 256-byte table
        methods = {e["name"]: e["method"] for e in meta["entries"]}
        self.assertEqual(methods["hello.txt"], 8)

    def test_zip_missing_eocd(self):
        meta, regions = parse(b"PK\x03\x04junk", "zip")
        self.assertEqual(regions, [])

    def test_elf64(self):
        elf = make_elf64()
        meta, regions = parse(elf, "elf")
        self.assertEqual(meta["class"], "ELF64")
        self.assertEqual(meta["machine"], 62)
        self.assertTrue(any(r["name"] == "ELF header" for r in regions))

    def test_pe(self):
        pe = make_pe()
        meta, regions = parse(pe, "exe")
        self.assertEqual(meta["section_count"], 1)
        self.assertEqual(meta["format"], "PE32+")
        secs = [r for r in regions if r["name"] == "section .text"]
        self.assertEqual(len(secs), 1)

    def test_pe_truncated_is_safe(self):
        # short MZ with bad e_lfanew must not raise
        meta, _ = parse(b"MZ" + b"\x00" * 20, "exe")
        self.assertEqual(meta, {})

    def test_pdf(self):
        data = b"%PDF-1.4\n1 0 obj\nstream\nendstream\nendobj\n"
        meta, regions = parse(data, "pdf")
        self.assertGreaterEqual(meta["objects"], 1)
        self.assertEqual(regions[0]["name"], "header")

    def test_unknown_extension(self):
        meta, regions = parse(b"whatever", "bin")
        self.assertEqual(meta, {})
        self.assertEqual(regions, [])

    def test_jpeg_soi(self):
        # minimal SOI + EOI
        data = b"\xFF\xD8\xFF\xD9"
        meta, regions = parse(data, "jpg")
        names = [r["name"] for r in regions]
        self.assertIn("SOI", names)
        self.assertIn("EOI", names)


if __name__ == "__main__":
    unittest.main()
