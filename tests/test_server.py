import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from bytelens import server
from tests.helpers import make_png, make_zip, write_temp


class ServerHarness:
    def __init__(self, path):
        server._load_state(path)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever,
                                       daemon=True)
        self.thread.start()

    def get(self, route):
        url = f"http://127.0.0.1:{self.port}{route}"
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = write_temp(make_png(), suffix=".png")
        cls.other = write_temp(make_zip(), suffix=".zip")
        cls.h = ServerHarness(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.h.stop()

    def test_health(self):
        status, body = self.h.get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_overview(self):
        status, body = self.h.get("/api/overview")
        self.assertEqual(status, 200)
        r = json.loads(body)
        self.assertEqual(r["magic"]["extension"], "png")
        self.assertIn("entropy", r)

    def test_hex(self):
        status, body = self.h.get("/api/hex?offset=0&length=16")
        r = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(len(r["rows"][0]["hex"]), 16)

    def test_hex_clamps_length(self):
        status, body = self.h.get("/api/hex?offset=0&length=99999")
        r = json.loads(body)
        self.assertLessEqual(len(r["rows"][0]["hex"]), 4096)

    def test_strings(self):
        status, _ = self.h.get("/api/strings?offset=0&limit=10")
        self.assertEqual(status, 200)

    def test_structure(self):
        status, body = self.h.get("/api/structure")
        r = json.loads(body)
        names = [x["name"] for x in r["regions"]]
        self.assertIn("IHDR", names)

    def test_map(self):
        status, body = self.h.get("/api/map")
        r = json.loads(body)
        self.assertEqual(len(r["histogram"]), 256)
        self.assertEqual(r["heatmap"]["buckets"], 16)

    def test_static_index(self):
        status, body = self.h.get("/")
        self.assertEqual(status, 200)
        self.assertIn("BYTELENS", body)

    def test_static_404(self):
        status, _ = self.h.get("/nope.html")
        self.assertEqual(status, 404)

    def test_compare(self):
        from urllib.parse import quote
        status, body = self.h.get("/api/compare?other=" + quote(self.other))
        self.assertEqual(status, 200)
        r = json.loads(body)
        self.assertIn("jaccard_similarity", r)

    def test_compare_missing_param(self):
        status, body = self.h.get("/api/compare")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_compare_missing_file(self):
        status, _ = self.h.get("/api/compare?other=C:/no/such/file.bin")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
