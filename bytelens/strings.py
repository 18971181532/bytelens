"""Extract printable strings (ASCII and UTF-16LE) with their offsets."""

from typing import Dict, List

DEFAULT_MIN = 4
MAX_STRING_LEN = 4096


def _is_ascii_printable(b: int) -> bool:
    return 32 <= b < 127 or b in (9, 10, 13)


def extract_ascii(data: bytes, min_len: int = DEFAULT_MIN) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    start = -1
    n = len(data)
    for i in range(n + 1):
        ok = i < n and _is_ascii_printable(data[i])
        if ok and start < 0:
            start = i
        elif not ok and start >= 0:
            length = i - start
            if length >= min_len and length <= MAX_STRING_LEN:
                raw = data[start:i]
                out.append({
                    "offset": start,
                    "length": length,
                    "encoding": "ascii",
                    "value": _clean(raw.decode("ascii", "replace")),
                })
            start = -1
    return out


def extract_utf16le(data: bytes, min_len: int = DEFAULT_MIN) -> List[Dict[str, object]]:
    """Detect runs of ASCII characters encoded as L,0,L,0 (UTF-16LE)."""
    out: List[Dict[str, object]] = []
    start = -1
    n = len(data) - 1
    i = 0
    while i < n:
        ch, hi = data[i], data[i + 1]
        ok = _is_ascii_printable(ch) and hi == 0
        if ok and start < 0:
            start = i
        elif not ok and start >= 0:
            _flush_utf16(data, start, i, out, min_len)
            start = -1
        i += 2 if ok else 1
    if start >= 0:
        _flush_utf16(data, start, i, out, min_len)
    return out


def _flush_utf16(data: bytes, start: int, end: int,
                 out: list, min_len: int) -> None:
    length = (end - start) // 2
    if length < min_len:
        return
    raw = data[start:end]
    try:
        value = raw.decode("utf-16-le", "replace").rstrip("\x00")
    except Exception:
        value = ""
    if len(value) >= min_len:
        out.append({
            "offset": start,
            "length": len(value),
            "encoding": "utf-16le",
            "value": _clean(value),
        })


def _clean(value: str) -> str:
    return value.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


def extract_strings(data: bytes, min_len: int = DEFAULT_MIN,
                    encodings=("ascii", "utf-16le")) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    if "ascii" in encodings:
        out.extend(extract_ascii(data, min_len))
    if "utf-16le" in encodings:
        out.extend(extract_utf16le(data, min_len))
    out.sort(key=lambda s: s["offset"])
    return out
