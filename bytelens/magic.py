"""File magic / signature identification.

A small, dependency-free signature table covering common binary and text
formats. Each signature is anchored at an explicit offset and may contain
wildcard bytes (``None``).  ``identify`` reads the head of a file and
returns the best match; ``scan`` finds signatures at arbitrary offsets
(embedded-file carving).
"""

from typing import Dict, List, Optional, Tuple

# (offset, signature, canonical extension, kind, description)
# A signature is a tuple of ints or None (wildcard).
SIGNATURES: List[Tuple[int, Tuple, str, str, str]] = [
    (0, (0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A),
     "png", "image", "PNG image"),
    (0, (0xFF, 0xD8, 0xFF), "jpg", "image", "JPEG image"),
    (0, (0x47, 0x49, 0x46, 0x38), "gif", "image", "GIF image"),
    (0, (0x42, 0x4D), "bmp", "image", "BMP image"),
    (0, (0x49, 0x49, 0x2A, 0x00), "tif", "image", "TIFF image (LE)"),
    (0, (0x4D, 0x4D, 0x00, 0x2A), "tif", "image", "TIFF image (BE)"),
    (0, (0x50, 0x4B, 0x03, 0x04), "zip", "archive", "ZIP archive"),
    (0, (0x50, 0x4B, 0x05, 0x06), "zip", "archive", "ZIP empty archive"),
    (0, (0x50, 0x4B, 0x07, 0x08), "zip", "archive", "ZIP spanned archive"),
    (0, (0x1F, 0x8B), "gz", "archive", "gzip stream"),
    (0, (0x42, 0x5A, 0x68), "bz2", "archive", "bzip2 stream"),
    (0, (0xFD, 0x37, 0x7A, 0x58, 0x5A, 0x00), "xz", "archive", "xz stream"),
    (0, (0x37, 0x7A, 0xBC, 0xAF, 0x27, 0x1C), "7z", "archive", "7-Zip archive"),
    (0, (0x52, 0x61, 0x72, 0x21, 0x1A, 0x07, 0x00), "rar", "archive",
     "RAR archive"),
    (0, (0x7F, 0x45, 0x4C, 0x46), "elf", "executable", "ELF binary"),
    (0, (0x4D, 0x5A), "exe", "executable", "PE/DOS executable"),
    (0, (0xFE, 0xED, 0xFA, 0xCE), "macho", "executable", "Mach-O 32-bit"),
    (0, (0xFE, 0xED, 0xFA, 0xCF), "macho", "executable", "Mach-O 64-bit"),
    (0, (0xCF, 0xFA, 0xED, 0xFE), "macho", "executable",
     "Mach-O 64-bit (LE)"),
    (0, (0xCE, 0xFA, 0xED, 0xFE), "macho", "executable",
     "Mach-O fat binary"),
    (0, (0xCA, 0xFE, 0xBA, 0xBE), "class", "executable", "Java class"),
    (0, (0x00, 0x61, 0x73, 0x6D), "wasm", "executable", "WebAssembly module"),
    (0, (0x25, 0x50, 0x44, 0x46), "pdf", "document", "PDF document"),
    (0, (0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1), "doc",
     "document", "OLE compound document (Office)"),
    (0, (0x53, 0x51, 0x4C, 0x69, 0x74, 0x65, 0x20, 0x66, 0x6F, 0x72,
         0x6D, 0x61, 0x74, 0x20, 0x33, 0x00), "sqlite", "database",
     "SQLite database"),
    (0, (0x52, 0x45, 0x44, 0x49, 0x53, 0x30, 0x30, 0x30), "rdb",
     "database", "Redis RDB dump"),
    (0, (0x00, 0x00, 0x01, 0xBA), "mpg", "media", "MPEG video"),
    (0, (0x00, 0x00, 0x00, 0x18, 0x66, 0x74, 0x79, 0x70), "mp4",
     "media", "MP4 video"),
    (0, (0x1A, 0x45, 0xDF, 0xA3), "webm", "media", "Matroska/WebM"),
    (0, (0x49, 0x44, 0x33), "mp3", "media", "MP3 (ID3)"),
    (0, (0xFF, 0xFB), "mp3", "media", "MP3 audio"),
    (0, (0x4F, 0x67, 0x67, 0x53), "ogg", "media", "OGG media"),
    (0, (0x66, 0x4C, 0x61, 0x43), "flac", "media", "FLAC audio"),
    (0, (0x52, 0x49, 0x46, 0x46, None, None, None, None, 0x57, 0x41,
         0x56, 0x45), "wav", "media", "WAV audio"),
    (0, (0x52, 0x49, 0x46, 0x46, None, None, None, None, 0x41, 0x56,
         0x49, 0x20), "avi", "media", "AVI video"),
    (0, (0xEF, 0xBB, 0xBF), "txt", "text", "UTF-8 text (BOM)"),
    (0, (0xFF, 0xFE), "txt", "text", "UTF-16 LE text (BOM)"),
    (0, (0xFE, 0xFF), "txt", "text", "UTF-16 BE text (BOM)"),
    # text-like anchors
    (0, (0x23, 0x21), "sh", "text", "shebang script"),
]

# Markers that frequently introduce embedded payloads (carving).
CARVE_MARKERS: List[Tuple[Tuple, str, str]] = [
    ((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A), "png", "PNG image"),
    ((0xFF, 0xD8, 0xFF, 0xE0), "jpg", "JPEG (JFIF)"),
    ((0xFF, 0xD8, 0xFF, 0xE1), "jpg", "JPEG (EXIF)"),
    ((0xFF, 0xD8, 0xFF), "jpg", "JPEG image"),
    ((0x47, 0x49, 0x46, 0x38), "gif", "GIF image"),
    ((0x50, 0x4B, 0x03, 0x04), "zip", "ZIP archive"),
    ((0x1F, 0x8B, 0x08), "gz", "gzip stream"),
    ((0x25, 0x50, 0x44, 0x46), "pdf", "PDF document"),
    ((0x7F, 0x45, 0x4C, 0x46), "elf", "ELF binary"),
    ((0x4D, 0x5A), "exe", "PE/DOS executable"),
]


def _matches_at(buf: bytes, offset: int, sig: Tuple) -> bool:
    if offset < 0 or offset + len(sig) > len(buf):
        return False
    for i, b in enumerate(sig):
        if b is not None and buf[offset + i] != b:
            return False
    return True


def identify(head: bytes) -> Optional[Dict[str, object]]:
    """Identify the file format from its leading bytes.

    Returns ``None`` when no signature matches.
    """
    if not head:
        return None
    for off, sig, ext, kind, desc in SIGNATURES:
        if _matches_at(head, off, sig):
            return {
                "extension": ext,
                "kind": kind,
                "description": desc,
                "offset": off,
                "confidence": 1.0,
            }
    return None


def identify_text(head: bytes) -> Optional[Dict[str, object]]:
    """Heuristic text detection (no binary signature matched)."""
    if not head:
        return None
    sample = head[:4096]
    if not sample:
        return None
    # Text if almost all bytes are printable / common whitespace.
    text_chars = sum(
        1 for b in sample
        if b in (9, 10, 13) or 32 <= b < 127 or b >= 0x80)
    ratio = text_chars / len(sample)
    if ratio >= 0.97:
        lower = head[:256].lstrip().lower()
        if lower.startswith(b"<?xml"):
            return _text("xml", "XML document", ratio)
        if lower.startswith(b"<!doctype html") or lower.startswith(b"<html"):
            return _text("html", "HTML document", ratio)
        if head[:1] in (b"{", b"["):
            return _text("json", "JSON data", ratio)
        return _text("txt", "plain text", ratio)
    return None


def _text(ext: str, desc: str, ratio: float) -> Dict[str, object]:
    return {
        "extension": ext, "kind": "text", "description": desc,
        "offset": 0, "confidence": round(ratio, 4),
    }


def scan(buf: bytes, max_hits: int = 100) -> List[Dict[str, object]]:
    """Find all embedded signatures (carving) at any offset.

    Offset 0 is excluded — that is the container's own magic.
    """
    hits: List[Dict[str, object]] = []
    found: Dict[int, str] = {}
    for sig, ext, desc in CARVE_MARKERS:
        start = 0
        while True:
            idx = buf.find(bytes(b for b in sig), start)
            if idx < 0:
                break
            if idx > 0 and idx not in found:
                found[idx] = ext
                hits.append({
                    "offset": idx,
                    "extension": ext,
                    "kind": "embedded",
                    "description": desc,
                })
            start = idx + 1
            if len(hits) >= max_hits:
                break
    hits.sort(key=lambda h: h["offset"])
    return hits
