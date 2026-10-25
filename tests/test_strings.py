import unittest

from bytelens.strings import (extract_ascii, extract_strings,
                              extract_utf16le)


class TestStrings(unittest.TestCase):
    def test_ascii_run(self):
        data = b"\x00\x00hello world\x00\x00"
        s = extract_ascii(data, 4)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["value"], "hello world")
        self.assertEqual(s[0]["offset"], 2)

    def test_min_len(self):
        self.assertEqual(extract_ascii(b"ab\x00", 4), [])

    def test_offsets(self):
        data = b"\x00" * 10 + b"first" + b"\x00" + b"second"
        s = extract_ascii(data, 4)
        self.assertEqual([x["value"] for x in s], ["first", "second"])
        self.assertEqual(s[1]["offset"], 16)

    def test_utf16le(self):
        data = b"h\x00i\x00!\x00!\x00"
        s = extract_utf16le(data, 4)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["value"], "hi!!")
        self.assertEqual(s[0]["encoding"], "utf-16le")

    def test_no_utf16_below_min(self):
        self.assertEqual(extract_utf16le(b"h\x00i\x00", 4), [])

    def test_combined_sorted(self):
        data = b"ascii_word\x00" + b"w\x00i\x00d\x00e\x00"
        s = extract_strings(data)
        encs = {x["encoding"] for x in s}
        self.assertIn("ascii", encs)
        self.assertIn("utf-16le", encs)

    def test_cleaned_whitespace(self):
        s = extract_ascii(b"a\tb\nc")
        self.assertIn("\\t", s[0]["value"])
        self.assertIn("\\n", s[0]["value"])


if __name__ == "__main__":
    unittest.main()
