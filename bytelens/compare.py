"""Compare two binaries: block-level similarity, aligned byte differences
and entropy/string deltas."""

import hashlib
from typing import Dict, List

from .entropy import shannon
from .strings import extract_strings

BLOCK = 4096


def _block_hashes(data: bytes) -> List[str]:
    return [hashlib.sha1(data[i:i + BLOCK]).hexdigest()
            for i in range(0, len(data), BLOCK)]


def _diff_map(a: bytes, b: bytes, common: int) -> List[Dict[str, int]]:
    """Per-aligned-block count of differing bytes (uses shorter length)."""
    out: List[Dict[str, int]] = []
    for off in range(0, common, BLOCK):
        ca = a[off:off + BLOCK]
        cb = b[off:off + BLOCK]
        diffs = sum(1 for x, y in zip(ca, cb) if x != y)
        if diffs:
            out.append({"offset": off, "differing_bytes": diffs,
                        "size": len(ca)})
    return out


def compare(a: bytes, b: bytes,
            block: int = BLOCK) -> Dict[str, object]:
    ha, hb = set(_block_hashes(a)), set(_block_hashes(b))
    union = ha | hb
    jaccard = round(len(ha & hb) / len(union), 4) if union else 1.0

    common = min(len(a), len(b))
    diff_map = _diff_map(a, b, common) if len(a) == len(b) else []
    aligned = None
    if len(a) == len(b):
        differing = sum(d["differing_bytes"] for d in diff_map)
        aligned = {
            "equal": len(a) == 0 or differing == 0,
            "differing_bytes": differing,
            "percent": round(100.0 * differing / len(a), 4) if a else 0.0,
            "map": diff_map,
        }

    sa = {s["value"] for s in extract_strings(a)}
    sb = {s["value"] for s in extract_strings(b)}

    return {
        "size_a": len(a),
        "size_b": len(b),
        "size_delta": len(b) - len(a),
        "entropy_a": round(shannon(a), 4),
        "entropy_b": round(shannon(b), 4),
        "entropy_delta": round(shannon(b) - shannon(a), 4),
        "blocks_a": len(_block_hashes(a)),
        "blocks_b": len(_block_hashes(b)),
        "shared_blocks": len(ha & hb),
        "jaccard_similarity": jaccard,
        "aligned": aligned,
        "strings_added": sorted(sb - sa)[:200],
        "strings_removed": sorted(sa - sb)[:200],
    }
