"""Embedded-file carving: locate and estimate the bounds of nested payloads."""

import zlib
from typing import Dict, List

from .magic import scan


def _estimate_end(data: bytes, start: int, ext: str) -> int:
    """Best-effort end offset for an embedded payload."""
    tail = data[start:]
    if ext == "png":
        iend = tail.find(b"IEND")
        if iend >= 0:
            return start + iend + 4 + 4  # type + CRC
    elif ext == "jpg":
        eoi = tail.find(b"\xFF\xD9")
        if eoi >= 0:
            return start + eoi + 2
    elif ext == "gif":
        term = tail.find(b"\x3B")
        if term >= 0:
            return start + term + 1
    elif ext == "zip":
        eocd = tail.rfind(b"PK\x05\x06")
        if eocd >= 0:
            return start + eocd + 22
    elif ext == "gz":
        # inflate as much as possible to find the logical end
        try:
            dobj = zlib.decompressobj(-zlib.MAX_WBITS)
            dobj.decompress(tail)
            consumed = len(tail) - len(dobj.unused_data)
            return start + consumed
        except Exception:
            pass
    return start


def carve(data: bytes, max_hits: int = 100) -> List[Dict[str, object]]:
    """Find embedded files, estimating end offsets and sizes."""
    out: List[Dict[str, object]] = []
    for hit in scan(data, max_hits=max_hits):
        start = hit["offset"]
        ext = hit["extension"]
        end = _estimate_end(data, start, ext)
        size = end - start if end > start else None
        out.append({
            "offset": start,
            "end": end if end > start else None,
            "size": size,
            "extension": ext,
            "description": hit["description"],
            "bounded": size is not None,
        })
    return out
