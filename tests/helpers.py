"""Shared test helpers: in-memory fixture builders and temp files."""

import io
import os
import struct
import tempfile
import zlib
import zipfile

PNG_SIG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def _chunk(ctype: bytes, data: bytes) -> bytes:
    body = ctype + data
    return struct.pack(">I", len(data)) + body + struct.pack(
        ">I", zlib.crc32(body) & 0xFFFFFFFF)


def make_png(width: int = 4, height: int = 3) -> bytes:
    """Build a valid RGB PNG entirely in memory."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(height):
        raw += b"\x00" + bytes([255, 0, 0]) * width
    idat = zlib.compress(raw)
    return (PNG_SIG + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", idat) + _chunk(b"IEND", b""))


def make_zip(entries=None) -> bytes:
    """Build a valid (stored) ZIP archive in memory."""
    entries = entries or {"hello.txt": b"hello world",
                          "data/num.bin": bytes(range(256))}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def make_elf64() -> bytes:
    """Minimal valid ELF64 header (little-endian) followed by zeros."""
    e_ident = b"\x7fELF" + bytes([2, 1, 1, 0]) + bytes(8)
    ehdr = struct.pack(
        "<HHIQQQIHHHHHH",
        2,        # e_type ET_EXEC
        62,       # e_machine x86_64
        1,        # e_version
        0x400000,  # e_entry
        0,        # e_phoff
        0,        # e_shoff
        0,        # e_flags
        64,       # e_ehsize
        0, 0,     # phentsize, phnum
        0, 0, 0)  # shentsize, shnum, shstrndx
    return e_ident + ehdr


def make_pe() -> bytes:
    """Minimal PE file: DOS header + PE signature + COFF + one section."""
    pe_off = 0x80
    buf = bytearray(pe_off + 24 + 224 + 40)
    buf[0:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, pe_off)
    buf[pe_off:pe_off + 4] = b"PE\x00\x00"
    struct.pack_into("<HHI", buf, pe_off + 4, 0x8664, 1, 0)
    struct.pack_into("<H", buf, pe_off + 20, 224)  # size of optional header
    buf[pe_off + 24:pe_off + 26] = b"\x0b\x02"      # PE32+ magic
    name = b".text\x00\x00\x00"
    so = pe_off + 24 + 224
    buf[so:so + 8] = name
    struct.pack_into("<IIII", buf, so + 8, 0x200, 0x1000, 0x200, 0x400)
    return bytes(buf)


def write_temp(data: bytes, suffix: str = ".bin", directory=None) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix, dir=directory)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return path
