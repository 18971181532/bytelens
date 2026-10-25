"""Assemble a full inspection report from a BinaryFile."""

import hashlib
import zlib
from typing import Dict, Optional

from . import magic, structures
from .carve import carve
from .entropy import entropy_summary
from .histogram import histogram
from .reader import BinaryFile, DEFAULT_MAX_BYTES
from .strings import extract_strings

BLOCK_SIZE = 4096


def hashes(data: bytes) -> Dict[str, str]:
    return {
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "crc32": format(zlib.crc32(data) & 0xFFFFFFFF, "08x"),
    }


def identify_file(data: bytes) -> Dict[str, object]:
    m = magic.identify(data)
    if m:
        return m
    t = magic.identify_text(data)
    if t:
        return t
    return {"extension": "bin", "kind": "unknown",
            "description": "unknown binary", "offset": 0,
            "confidence": 0.0}


def analyze(bf: BinaryFile, max_bytes: int = DEFAULT_MAX_BYTES,
            include_strings: bool = True,
            include_structure: bool = True,
            include_carve: bool = True) -> Dict[str, object]:
    """Build a report. Small files are analyzed fully; large files use the
    head for everything but size/hashes (caller streams when needed)."""
    head = bf.read_head()
    full = None
    if bf.size <= max_bytes:
        full = bf.read_all(max_bytes)
    data = full if full is not None else head

    report: Dict[str, object] = {
        "file": bf.meta(),
        "truncated": full is None,
        "analyzed_bytes": len(data),
        "magic": identify_file(data),
    }
    report["entropy"] = entropy_summary(data, BLOCK_SIZE)
    report["histogram"] = histogram(data)
    report["hashes"] = hashes(data) if full is not None else {
        "note": "file too large; hashes computed on head only",
        **hashes(head),
    }

    if include_strings:
        strings = extract_strings(data)
        report["string_count"] = len(strings)
        report["strings"] = strings
    else:
        report["string_count"] = 0
        report["strings"] = []

    if include_structure:
        meta, regions = structures.parse(data, report["magic"]["extension"])
        report["structure"] = {"meta": meta, "regions": regions}
    else:
        report["structure"] = {"meta": {}, "regions": []}

    if include_carve:
        report["carved"] = carve(data)
    else:
        report["carved"] = []

    return report
