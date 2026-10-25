import unittest

from bytelens.carve import carve
from tests.helpers import make_png, make_zip


class TestCarve(unittest.TestCase):
    def test_embedded_png_bounded(self):
        wrapper = b"prefix-data" * 4 + make_png() + b"tail"
        found = carve(wrapper)
        png = [f for f in found if f["extension"] == "png"]
        self.assertTrue(png)
        hit = png[0]
        self.assertTrue(hit["bounded"])
        self.assertIsNotNone(hit["size"])
        self.assertGreater(hit["size"], 0)

    def test_embedded_jpeg_bounded(self):
        jpeg = b"\xFF\xD8\xFF\xE0" + b"\x00" * 20 + b"\xFF\xD9"
        wrapper = b"x" * 30 + jpeg
        found = carve(wrapper)
        j = [f for f in found if f["extension"] == "jpg"]
        self.assertTrue(j)
        self.assertTrue(j[0]["bounded"])

    def test_embedded_zip_bounded(self):
        wrapper = b"AAAA" + make_zip()
        found = carve(wrapper)
        z = [f for f in found if f["extension"] == "zip"]
        self.assertTrue(z)
        self.assertTrue(z[0]["bounded"])

    def test_no_embedded(self):
        self.assertEqual(carve(b"plain text only, nothing here"), [])

    def test_container_offset_zero_not_reported(self):
        # PNG at offset 0 is the container, not an "embedded" hit
        found = carve(make_png())
        self.assertFalse(any(f["offset"] == 0 for f in found))

    def test_multiple_embedded_sorted(self):
        wrapper = b"x" * 20 + make_png() + b"y" * 20 + make_png()
        found = carve(wrapper)
        pngs = [f for f in found if f["extension"] == "png"]
        self.assertGreaterEqual(len(pngs), 2)
        offsets = [f["offset"] for f in pngs]
        self.assertEqual(offsets, sorted(offsets))


if __name__ == "__main__":
    unittest.main()
