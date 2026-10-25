"""Paginated hexadecimal / ASCII dump rendering."""

from typing import Dict, List

ROW_WIDTH = 16


def hexdump(data: bytes, base: int = 0, width: int = ROW_WIDTH) -> List[Dict[str, object]]:
    """Produce structured rows for ``data`` with an absolute ``base``."""
    rows: List[Dict[str, object]] = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_pairs = [f"{b:02x}" for b in chunk]
        ascii_col = "".join(
            chr(b) if 32 <= b < 127 else "." for b in chunk)
        rows.append({
            "offset": base + i,
            "hex": hex_pairs,
            "ascii": ascii_col,
            "size": len(chunk),
        })
    return rows


def dump_window(data: bytes, offset: int = 0, length: int = 256,
                base: int = 0) -> Dict[str, object]:
    """Slice a window for the web UI and return rows + navigation info."""
    total = len(data)
    offset = max(0, min(offset, total))
    chunk = data[offset:offset + length]
    return {
        "offset": offset,
        "length": len(chunk),
        "file_size": total,
        "rows": hexdump(chunk, base=base + offset),
        "next_offset": offset + length if offset + length < total else None,
        "prev_offset": max(0, offset - length) if offset > 0 else None,
    }
