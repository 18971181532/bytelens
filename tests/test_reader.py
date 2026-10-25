import os
import unittest

from bytelens.reader import BinaryFile
from tests.helpers import write_temp


class TestReader(unittest.TestCase):
    def test_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            BinaryFile(os.path.join(os.path.dirname(__file__), "nope.bin"))

    def test_meta(self):
        path = write_temp(b"abcdef")
        bf = BinaryFile(path)
        self.assertEqual(bf.size, 6)
        self.assertEqual(bf.name, os.path.basename(path))

    def test_extension(self):
        path = write_temp(b"x", suffix=".png")
        self.assertEqual(BinaryFile(path).meta()["extension"], "png")

    def test_head(self):
        path = write_temp(b"ABCDEF")
        self.assertEqual(BinaryFile(path).read_head(3), b"ABC")

    def test_range(self):
        path = write_temp(b"0123456789")
        bf = BinaryFile(path)
        self.assertEqual(bf.read_range(2, 3), b"234")

    def test_read_all(self):
        path = write_temp(b"xyz")
        self.assertEqual(BinaryFile(path).read_all(1024), b"xyz")

    def test_over_ceiling(self):
        path = write_temp(b"x" * 20)
        with self.assertRaises(ValueError):
            BinaryFile(path).read_all(10)


if __name__ == "__main__":
    unittest.main()
