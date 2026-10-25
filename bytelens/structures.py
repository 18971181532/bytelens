"""Parse the internal structure of common container formats.

Each parser returns ``(metadata, regions)`` where a region is
``{name, start, end, kind, detail}``. Parsers are defensive: malformed
input yields whatever could be read rather than raising.
"""

import struct
from typing import Dict, List, Optional, Tuple

Region = Dict[str, object]
Result = Tuple[Dict[str, object], List[Region]]


def _region(name: str, start: int, end: int, kind: str,
            detail: str = "") -> Region:
    return {"name": name, "start": start, "end": end,
            "kind": kind, "detail": detail}


def parse(data: bytes, magic_ext: Optional[str] = None) -> Result:
    """Dispatch to the best structural parser."""
    ext = magic_ext
    if ext is None:
        return {}, []
    table = {
        "png": _png, "jpg": _jpeg, "jpeg": _jpeg, "gif": _gif,
        "zip": _zip, "gz": _gzip, "elf": _elf, "exe": _pe,
        "pdf": _pdf, "wav": _wav,
    }
    fn = table.get(ext)
    if fn is None:
        return {}, []
    try:
        return fn(data)
    except Exception as exc:  # malformed / truncated
        return {"error": f"{ext} parse failed: {exc}"}, []


# ---------------------------------------------------------------- PNG ----
def _png(data: bytes) -> Result:
    regions: List[Region] = [_region("signature", 0, 8, "header", "PNG")]
    meta: Dict[str, object] = {"chunks": []}
    pos = 8
    end = len(data)
    while pos + 8 <= end:
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8].decode("latin-1", "replace")
        body_start = pos + 8
        body_end = body_start + length
        crc_end = body_end + 4
        if crc_end > end:
            break
        detail = f"{length} bytes"
        if ctype == "IHDR":
            w, h = struct.unpack(">II", data[body_start:body_start + 8])
            bit = data[body_start + 8]
            cmap = data[body_start + 9]
            meta["width"] = w
            meta["height"] = h
            meta["bit_depth"] = bit
            meta["color_type"] = cmap
            detail = f"{w}x{h} {bit}-bit"
        regions.append(_region(ctype, pos, crc_end, "chunk", detail))
        meta["chunks"].append({"type": ctype, "length": length,
                               "offset": pos})
        if ctype == "IEND":
            break
        pos = crc_end
    if meta.get("chunks"):
        meta["chunk_count"] = len(meta["chunks"])
    return meta, regions


# ---------------------------------------------------------------- JPEG ---
_JPEG_MARKERS = {
    0xD8: "SOI", 0xD9: "EOI", 0xDA: "SOS", 0xDB: "DQT",
    0xC0: "SOF0", 0xC2: "SOF2", 0xC4: "DHT", 0xDD: "DRI",
    0xE0: "APP0", 0xE1: "EXIF", 0xE2: "APP2", 0xED: "Photoshop",
    0xEE: "Adobe", 0xFE: "COM",
}


def _jpeg(data: bytes) -> Result:
    regions: List[Region] = [_region("SOI", 0, 2, "marker", "start of image")]
    meta: Dict[str, object] = {"markers": []}
    pos = 2
    end = len(data)
    while pos + 1 < end:
        if data[pos] != 0xFF:
            pos += 1
            continue
        # skip fill bytes
        while pos < end and data[pos] == 0xFF:
            pos += 1
        if pos >= end:
            break
        marker = data[pos]
        name = _JPEG_MARKERS.get(marker, f"0x{marker:02X}")
        pos += 1
        if marker in (0xD8, 0xD9):
            regions.append(_region(name, pos - 2, pos, "marker"))
            if marker == 0xD9:
                break
            continue
        if pos + 2 > end:
            break
        seg_len = struct.unpack(">H", data[pos:pos + 2])[0]
        seg_start = pos - 2
        seg_end = seg_start + 2 + seg_len
        if name in ("SOF0", "SOF2") and seg_end <= end:
            if pos + 6 < end:
                h = struct.unpack(">H", data[pos + 3:pos + 5])[0]
                w = struct.unpack(">H", data[pos + 5:pos + 7])[0]
                meta["width"] = w
                meta["height"] = h
        regions.append(_region(name, seg_start, min(seg_end, end),
                               "segment", f"{seg_len} bytes"))
        meta["markers"].append(name)
        if name == "SOS":
            # entropy-coded data follows until EOI
            eoi = data.find(b"\xFF\xD9", seg_end)
            if eoi >= 0:
                regions.append(_region("scan data", seg_end, eoi,
                                       "data", "entropy coded"))
                regions.append(_region("EOI", eoi, eoi + 2, "marker",
                                       "end of image"))
                break
            break
        pos = seg_end
    return meta, regions


# ---------------------------------------------------------------- GIF ---
def _gif(data: bytes) -> Result:
    regions: List[Region] = [_region("header", 0, 6, "header",
                                    data[:6].decode("latin-1", "replace"))]
    meta: Dict[str, object] = {}
    if len(data) >= 13:
        w = struct.unpack("<H", data[6:8])[0]
        h = struct.unpack("<H", data[8:10])[0]
        packed = data[10]
        gct = bool(packed & 0x80)
        gct_size = 2 ** ((packed & 0x07) + 1) if gct else 0
        meta["width"] = w
        meta["height"] = h
        meta["global_color_table"] = gct_size
        pos = 13
        if gct:
            end = pos + gct_size * 3
            regions.append(_region("global color table", pos, end,
                                   "table", f"{gct_size} colors"))
            pos = end
        frames = data.count(b"\x2C")
        meta["frames"] = frames
    return meta, regions


# ---------------------------------------------------------------- ZIP ---
def _zip(data: bytes) -> Result:
    meta: Dict[str, object] = {"entries": []}
    regions: List[Region] = []
    eocd = data.rfind(b"PK\x05\x06")
    if eocd < 0 or eocd + 22 > len(data):
        return meta, regions
    (disk_no, cd_disk, cd_entries_disk, cd_entries,
     cd_size, cd_offset, comment_len) = struct.unpack(
        "<HHHHIIH", data[eocd + 4:eocd + 22])
    regions.append(_region("end of central directory", eocd,
                           eocd + 22 + comment_len, "directory"))
    meta["central_dir_offset"] = cd_offset
    meta["entry_count"] = cd_entries
    pos = cd_offset
    count = 0
    while count < cd_entries and data[pos:pos + 4] == b"PK\x01\x02":
        fixed = data[pos:pos + 46]
        if len(fixed) < 46:
            break
        (sig, ver_made, ver_needed, flag, method, mtime, mdate, crc,
         csize, usize, nlen, elen, clen, disk, iattr, xattr,
         lho) = struct.unpack("<IHHHHHHIIIHHHHHII", fixed)
        name = data[pos + 46:pos + 46 + nlen].decode("utf-8", "replace")
        regions.append(_region(f"central: {name}", pos,
                               pos + 46 + nlen + elen + clen,
                               "directory", f"{usize} -> {csize}"))
        meta["entries"].append({
            "name": name, "method": method,
            "uncompressed": usize, "compressed": csize,
            "local_header": lho,
        })
        # local header region
        if lho + 30 <= len(data):
            ln = struct.unpack(
                "<H", data[lho + 26:lho + 28])[0]
            le = struct.unpack(
                "<H", data[lho + 28:lho + 30])[0]
            regions.append(_region(f"local: {name}", lho,
                                   lho + 30 + ln + le + csize,
                                   "file",
                                   "deflate" if method == 8 else "stored"))
        pos += 46 + nlen + elen + clen
        count += 1
    return meta, regions


# ---------------------------------------------------------------- gzip ---
def _gzip(data: bytes) -> Result:
    regions: List[Region] = [_region("gzip header", 0, 10, "header")]
    meta: Dict[str, object] = {}
    if len(data) >= 10:
        flg = data[3]
        meta["compression"] = "deflate"
        meta["mtime"] = struct.unpack("<I", data[4:8])[0]
        meta["flags"] = flg
    return meta, regions


# ---------------------------------------------------------------- WAV ---
def _wav(data: bytes) -> Result:
    regions: List[Region] = [_region("RIFF", 0, 12, "header")]
    meta: Dict[str, object] = {}
    pos = 12
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        name = cid.decode("latin-1", "replace")
        if name == "fmt " and pos + 24 <= len(data):
            audio_fmt, channels, rate, _br, _ba, bps = struct.unpack(
                "<HHIIHH", data[pos + 8:pos + 24])
            meta["channels"] = channels
            meta["sample_rate"] = rate
            meta["bits_per_sample"] = bps
        regions.append(_region(name, pos, pos + 8 + size, "chunk",
                               f"{size} bytes"))
        if size == 0:
            break
        pos += 8 + size + (size % 2)
    return meta, regions


# ---------------------------------------------------------------- ELF ---
def _elf(data: bytes) -> Result:
    meta: Dict[str, object] = {}
    regions: List[Region] = [_region("ELF header", 0, 64, "header")]
    is64 = data[4] == 2
    little = data[5] == 1
    endian = "<" if little else ">"
    meta["class"] = "ELF64" if is64 else "ELF32"
    meta["endianness"] = "little" if little else "big"
    try:
        if is64:
            (etype, machine, version, entry, phoff, shoff, flags,
             ehsize, phentsize, phnum, shentsize, shnum, shstr) = \
                struct.unpack(endian + "HHIQQQIHHHHHH", data[16:64])
        else:
            (etype, machine, version, entry, phoff, shoff, flags,
             ehsize, phentsize, phnum, shentsize, shnum, shstr) = \
                struct.unpack(endian + "HHIIIIIHHHHHH", data[16:52])
            regions[0]["end"] = 52
        meta["type"] = etype
        meta["machine"] = machine
        meta["entry"] = entry
        meta["section_count"] = shnum
        meta["program_header_count"] = phnum
        regions.append(_region("section headers", shoff,
                               shoff + shnum * shentsize, "table",
                               f"{shnum} sections"))
        regions.append(_region("program headers", phoff,
                               phoff + phnum * phentsize, "table",
                               f"{phnum} segments"))
    except Exception:
        pass
    return meta, regions


# ---------------------------------------------------------------- PE ----
def _pe(data: bytes) -> Result:
    meta: Dict[str, object] = {}
    regions: List[Region] = [_region("DOS header", 0, 64, "header",
                                    "MZ stub")]
    if len(data) < 0x40:
        return meta, regions
    e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]
    if e_lfanew + 24 > len(data) or data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return meta, regions
    regions.append(_region("PE header", e_lfanew, e_lfanew + 24, "header"))
    machine, num_sections, timestamp = struct.unpack(
        "<HHI", data[e_lfanew + 4:e_lfanew + 12])
    size_opt = struct.unpack("<H", data[e_lfanew + 20:e_lfanew + 22])[0]
    meta["machine"] = hex(machine)
    meta["section_count"] = num_sections
    meta["timestamp"] = timestamp
    opt_start = e_lfanew + 24
    sec_start = opt_start + size_opt
    if data[opt_start:opt_start + 2] == b"\x0b\x02":
        meta["format"] = "PE32+"
    elif data[opt_start:opt_start + 2] == b"\x0b\x01":
        meta["format"] = "PE32"
    regions.append(_region("optional header", opt_start, sec_start, "header"))
    for i in range(num_sections):
        off = sec_start + i * 40
        if off + 40 > len(data):
            break
        raw_name = data[off:off + 8].rstrip(b"\x00").decode(
            "latin-1", "replace")
        v_size, v_addr, raw_size, raw_ptr = struct.unpack(
            "<IIII", data[off + 8:off + 24])
        regions.append(_region(f"section {raw_name}", raw_ptr,
                               raw_ptr + raw_size, "section",
                               f"virtual {v_size:#x} raw {raw_size}"))
    return meta, regions


# ---------------------------------------------------------------- PDF ---
def _pdf(data: bytes) -> Result:
    meta: Dict[str, object] = {
        "objects": data.count(b" obj") - data.count(b"endobj") * 0,
        "streams": data.count(b"stream"),
        "pages": data.count(b"/Type/Page") + data.count(b"/Type /Page"),
    }
    meta["objects"] = data.count(b" obj")
    meta["pages"] = (data.count(b"/Type/Page") +
                     data.count(b"/Type /Page") +
                     data.count(b"/Type/Page ") +
                     data.count(b"/Type /Page "))
    regions: List[Region] = [
        _region("header", 0, min(8, len(data)), "header",
                data[:8].decode("latin-1", "replace"))]
    startxref = data.rfind(b"startxref")
    if startxref >= 0:
        regions.append(_region("startxref", startxref, len(data),
                               "trailer", "cross reference"))
    return meta, regions
