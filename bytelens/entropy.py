"""Shannon entropy over byte streams, with sliding-window block entropy."""

import math
from typing import Dict, List, Optional, Sequence


def shannon(data: bytes) -> float:
    """Shannon entropy in bits per byte (range 0..8)."""
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    ent = 0.0
    for c in counts:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent


def shannon_from_counts(counts: Sequence[int], n: int) -> float:
    if n <= 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent


def block_entropy(data: bytes, block_size: int = 4096,
                  step: Optional[int] = None) -> List[Dict[str, int]]:
    """Entropy of fixed-size (optionally overlapping) windows.

    Returns a list of ``{offset, size, entropy}``.
    """
    if step is None:
        step = block_size
    n = len(data)
    out: List[Dict[str, int]] = []
    if n == 0 or block_size <= 0:
        return out
    offset = 0
    while offset < n:
        chunk = data[offset:offset + block_size]
        out.append({
            "offset": offset,
            "size": len(chunk),
            "entropy": round(shannon(chunk), 4),
        })
        offset += step
    return out


def classify(ent: float) -> str:
    """Rough interpretation of a Shannon entropy value."""
    if ent < 1.0:
        return "trivial/constant"
    if ent < 5.0:
        return "text or structured code"
    if ent < 6.5:
        return "mixed / sparse binary"
    if ent < 7.3:
        return "compressed or serialized data"
    return "encrypted/compressed (high entropy)"


def entropy_summary(data: bytes, block_size: int = 4096) -> Dict[str, object]:
    blocks = block_entropy(data, block_size)
    vals = [b["entropy"] for b in blocks]
    return {
        "entropy": round(shannon(data), 4),
        "classification": classify(shannon(data)),
        "block_size": block_size,
        "blocks": blocks,
        "min_block": round(min(vals), 4) if vals else 0.0,
        "max_block": round(max(vals), 4) if vals else 0.0,
        "mean_block": round(sum(vals) / len(vals), 4) if vals else 0.0,
    }
