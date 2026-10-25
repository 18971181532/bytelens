"""Byte-frequency histogram and composition statistics."""

import string
from typing import Dict, List

PRINTABLE = set(bytes(string.printable, "ascii"))
WHITESPACE = {9, 10, 13, 32, 11, 12}


def byte_counts(data: bytes) -> List[int]:
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    return counts


def composition(data: bytes) -> Dict[str, object]:
    """Categorize bytes into human-readable classes."""
    n = len(data)
    if n == 0:
        return {"total": 0, "printable_ratio": 0.0, "null_ratio": 0.0}
    counts = byte_counts(data)
    nulls = counts[0]
    whitespace = sum(counts[b] for b in WHITESPACE)
    ascii_printable = sum(1 for b in data
                          if 32 <= b < 127)
    control = sum(1 for b in data if b < 32 and b not in WHITESPACE)
    high = sum(1 for b in data if b >= 128)
    # printable excludes whitespace but includes visible ASCII only
    return {
        "total": n,
        "nulls": nulls,
        "null_ratio": round(nulls / n, 4),
        "ascii_printable": ascii_printable,
        "printable_ratio": round(ascii_printable / n, 4),
        "whitespace": whitespace,
        "control": control,
        "high_bytes": high,
        "high_ratio": round(high / n, 4),
    }


def histogram(data: bytes, top: int = 16) -> Dict[str, object]:
    n = len(data)
    counts = byte_counts(data)
    present = [{"byte": b, "count": counts[b],
                "char": _glyph(b)} for b in range(256)]
    top_bytes = sorted(
        (p for p in present if p["count"] > 0),
        key=lambda p: -p["count"])[:top]
    return {
        "total": n,
        "counts": counts,
        "present": present,
        "top": top_bytes,
        "distinct": sum(1 for c in counts if c > 0),
        "composition": composition(data),
    }


def _glyph(b: int) -> str:
    if 32 <= b < 127:
        return chr(b)
    names = {0: "NUL", 9: "TAB", 10: "LF", 13: "CR", 32: "SP"}
    return names.get(b, "")


def byte_heatmap(data: bytes, columns: int = 256,
                 buckets: int = 16) -> Dict[str, object]:
    """Downsample the file into ``columns`` x ``buckets`` normalized counts.

    Columns are address slices; rows are byte-value buckets (high nibble by
    default), giving a quick visual fingerprint of where high/low bytes
    cluster.
    """
    n = len(data)
    cols = max(1, min(columns, n or 1))
    grid = []
    for col in range(cols):
        lo = col * n // cols
        hi = (col + 1) * n // cols
        chunk = data[lo:hi]
        counts = [0] * buckets
        for b in chunk:
            counts[b >> 4] += 1
        size = len(chunk) or 1
        grid.append([round(counts[k] / size, 4) for k in range(buckets)])
    return {"columns": cols, "buckets": buckets,
            "bucket_labels": [f"0x{k:X}x" for k in range(buckets)],
            "grid": grid}

