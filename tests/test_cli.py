import io
import json
import os
import unittest
from contextlib import redirect_stdout

from bytelens.cli import main
from tests.helpers import make_png, make_zip, write_temp


def run_cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class TestCli(unittest.TestCase):
    def test_analyze_json(self):
        path = write_temp(make_png(), suffix=".png")
        code, out = run_cli(["analyze", path, "--json"])
        self.assertEqual(code, 0)
        r = json.loads(out)
        self.assertEqual(r["magic"]["extension"], "png")
        self.assertIn("entropy", r)

    def test_analyze_human(self):
        path = write_temp(make_png(), suffix=".png")
        code, out = run_cli(["analyze", path])
        self.assertEqual(code, 0)
        self.assertIn("Magic:", out)

    def test_hex(self):
        path = write_temp(b"ABCDEFGH")
        code, out = run_cli(["hex", path, "--json", "--length", "8"])
        self.assertEqual(code, 0)
        r = json.loads(out)
        self.assertEqual(r["rows"][0]["hex"][0], "41")

    def test_strings(self):
        path = write_temp(b"\x00\x00findme_string\x00")
        code, out = run_cli(["strings", path, "--json", "--search", "find"])
        r = json.loads(out)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["value"], "findme_string")

    def test_entropy(self):
        path = write_temp(b"AAAA")
        code, out = run_cli(["entropy", path, "--json"])
        self.assertEqual(json.loads(out)["entropy"], 0.0)

    def test_structures(self):
        path = write_temp(make_zip(), suffix=".zip")
        code, out = run_cli(["structures", path, "--json"])
        r = json.loads(out)
        self.assertEqual(r["meta"]["entry_count"], 2)

    def test_compare(self):
        a = write_temp(b"aaaa")
        b = write_temp(b"bbbb")
        code, out = run_cli(["compare", a, b, "--json"])
        r = json.loads(out)
        self.assertEqual(r["aligned"]["differing_bytes"], 4)

    def test_missing_file(self):
        code, _ = run_cli(["analyze", "/nonexistent/path.bin"])
        self.assertEqual(code, 2)

    def test_version(self):
        with self.assertRaises(SystemExit):
            main(["--version"])


if __name__ == "__main__":
    unittest.main()
