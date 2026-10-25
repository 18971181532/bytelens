"""Local HTTP server for the Bytelens dashboard.

Serves a small JSON API plus the static web/ bundle. Bound to
127.0.0.1 by default; the compare endpoint only accepts real files that
resolve under the inspected file's directory (or an absolute path that
exists), preventing traversal outside the filesystem.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import __version__
from .compare import compare
from .hexview import dump_window
from .histogram import byte_heatmap
from .reader import BinaryFile, DEFAULT_MAX_BYTES
from .report import analyze

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}

_state = {
    "bf": None,
    "data": None,
    "report": None,
    "lock": threading.Lock(),
}


def _load_state(path: str, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    bf = BinaryFile(path)
    data = (bf.read_all(max_bytes) if bf.size <= max_bytes
            else bf.read_head())
    report = analyze(bf, max_bytes=max_bytes)
    _state.update({"bf": bf, "data": data, "report": report})


class Handler(BaseHTTPRequestHandler):
    server_version = f"Bytelens/{__version__}"

    def log_message(self, *args):  # quiet
        pass

    # ---- helpers -----------------------------------------------------
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg, status=400):
        self._json({"error": msg}, status)

    # ---- routing -----------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        qs = parse_qs(parsed.query)
        try:
            if route == "/api/health":
                return self._json({"status": "ok", "version": __version__})
            if route == "/api/overview":
                return self._api_overview()
            if route == "/api/hex":
                return self._api_hex(qs)
            if route == "/api/strings":
                return self._api_strings(qs)
            if route == "/api/structure":
                return self._api_structure()
            if route == "/api/map":
                return self._api_map()
            if route == "/api/compare":
                return self._api_compare(qs)
            return self._static(route)
        except FileNotFoundError as exc:
            return self._error(f"file not found: {exc}", 404)
        except Exception as exc:  # surface, do not crash the server
            return self._error(str(exc), 500)

    # ---- API ---------------------------------------------------------
    def _api_overview(self):
        r = dict(_state["report"])
        # strings are served separately; keep the payload light
        r["strings"] = r.get("strings", [])[:1]
        r["histogram"] = {
            "total": r["histogram"]["total"],
            "distinct": r["histogram"]["distinct"],
            "composition": r["histogram"]["composition"],
            "top": r["histogram"]["top"],
        }
        self._json(r)

    def _api_hex(self, qs):
        offset = int(qs.get("offset", ["0"])[0])
        length = int(qs.get("length", ["256"])[0])
        length = max(1, min(length, 4096))
        data = _state["data"]
        self._json(dump_window(data, offset, length))

    def _api_strings(self, qs):
        offset = int(qs.get("offset", ["0"])[0])
        limit = int(qs.get("limit", ["200"])[0])
        q = qs.get("q", [""])[0].lower()
        limit = max(1, min(limit, 2000))
        strings = _state["report"].get("strings", [])
        if q:
            strings = [s for s in strings if q in s["value"].lower()]
        page = strings[offset:offset + limit]
        self._json({"total": len(strings), "offset": offset,
                    "limit": limit, "strings": page})

    def _api_structure(self):
        r = _state["report"]
        self._json({"magic": r["magic"],
                    "meta": r["structure"]["meta"],
                    "regions": r["structure"]["regions"]})

    def _api_map(self):
        data = _state["data"]
        r = _state["report"]
        self._json({
            "file_size": len(data),
            "entropy": r["entropy"],
            "histogram": r["histogram"]["counts"],
            "heatmap": byte_heatmap(data),
        })

    def _api_compare(self, qs):
        other = qs.get("other", [""])[0]
        if not other:
            return self._error("missing 'other' query parameter")
        path = os.path.abspath(other)
        if not os.path.isfile(path):
            return self._error(f"other file not found: {other}", 404)
        bf = BinaryFile(path)
        other_data = (bf.read_all(DEFAULT_MAX_BYTES)
                      if bf.size <= DEFAULT_MAX_BYTES else bf.read_head())
        result = compare(_state["data"], other_data)
        result["other"] = bf.meta()
        self._json(result)

    # ---- static ------------------------------------------------------
    def _static(self, route):
        if route in ("", "/"):
            route = "/index.html"
        rel = route.lstrip("/")
        safe = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not safe.startswith(os.path.abspath(WEB_DIR)) or \
                not os.path.isfile(safe):
            return self._error("not found", 404)
        with open(safe, "rb") as fh:
            body = fh.read()
        ext = os.path.splitext(safe)[1].lower()
        self.send_response(200)
        self.send_header("Content-Type",
                         CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(path: str, host: str = "127.0.0.1", port: int = 8854,
          max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    _load_state(path, max_bytes)
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"Bytelens inspecting {os.path.basename(path)}")
    print(f"Dashboard: {url}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()
