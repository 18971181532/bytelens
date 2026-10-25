"""Generate small fixture files for exploring Bytelens.

Run:  python examples/make_examples.py
Produces PNG/ZIP fixtures plus a high-entropy "packed" sample and a
polyglot container that hides an embedded PNG and JPEG.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.helpers import make_png, make_zip  # noqa: E402


def build_packed(size=64 * 1024):
    """A low-entropy header followed by a high-entropy payload."""
    import random
    random.seed(42)
    header = b"MYFORMAT-v1" + b"\x00" * 22 + b"HELLO_FROM_BYTELENS"
    payload = bytes(random.getrandbits(8) for _ in range(size - len(header)))
    return header + payload


def build_polyglot():
    """A plain wrapper with PNG and JPEG embedded at nonzero offsets."""
    jpeg = b"\xFF\xD8\xFF\xE0" + b"\x00" * 64 + b"\xFF\xD9"
    wrapper = (b"FAKE-CONTAINER-HEADER\n" + b"X" * 200 + make_png()
               + b"---SEPARATOR---" + b"Y" * 128 + jpeg
               + b"TRAILER-END")
    return wrapper


def build_text():
    return (b"#!/bin/bash\n"
            b"# A readable script to demonstrate text/string detection.\n"
            b"echo hello\n"
            b"for i in 1 2 3; do\n"
            b"  printf 'iteration %s\\n' \"$i\"\n"
            b"done\n"
            b"# padding: " + b"z" * 120 + b"\n")


def main():
    out = os.path.dirname(os.path.abspath(__file__))
    fixtures = {
        "sample.png": make_png(8, 6),
        "sample.zip": make_zip(),
        "packed.bin": build_packed(),
        "polyglot.bin": build_polyglot(),
        "script.sh": build_text(),
    }
    for name, data in fixtures.items():
        path = os.path.join(out, name)
        with open(path, "wb") as fh:
            fh.write(data)
        print(f"wrote {name:14} {len(data):>8} bytes")


if __name__ == "__main__":
    main()
