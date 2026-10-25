"""Command-line interface for Bytelens."""

import argparse
import json
import sys
from typing import List, Optional

from . import __version__
from .entropy import block_entropy, classify, shannon
from .hexview import dump_window
from .reader import BinaryFile, DEFAULT_MAX_BYTES
from .report import analyze, identify_file
from .structures import parse
from .strings import extract_strings
from .compare import compare


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _load(path: str, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    bf = BinaryFile(path)
    if bf.size > max_bytes:
        return bf.read_head()
    return bf.read_all(max_bytes)


def cmd_analyze(args) -> int:
    bf = BinaryFile(args.path)
    report = analyze(bf, max_bytes=args.max_bytes,
                     include_strings=not args.no_strings,
                     include_structure=not args.no_structure,
                     include_carve=not args.no_carve)
    if args.json:
        _print(report)
    else:
        _print_human(report)
    return 0


def _print_human(r: dict) -> None:
    f = r["file"]
    m = r["magic"]
    e = r["entropy"]
    print(f"File:       {f['name']} ({f['size']} bytes)")
    print(f"Magic:      {m['description']}  .{m['extension']}")
    print(f"Entropy:    {e['entropy']:.4f}  ({e['classification']})")
    print(f"Hashes:     md5={r['hashes'].get('md5','?')}")
    print(f"            sha256={r['hashes'].get('sha256','?')}")
    comp = r["histogram"]["composition"]
    print(f"ASCII%:     {comp.get('printable_ratio', 0)}  "
          f"null%: {comp.get('null_ratio', 0)}  "
          f"high%: {comp.get('high_ratio', 0)}")
    print(f"Strings:    {r['string_count']}")
    meta = r["structure"]["meta"]
    if meta:
        print(f"Structure:  {json.dumps(meta, ensure_ascii=False)}")
    if r["carved"]:
        print(f"Embedded:   {len(r['carved'])} candidate(s)")
        for c in r["carved"][:10]:
            print(f"   @{c['offset']:>10} {c['extension']} "
                  f"size={c['size']} {c['description']}")


def cmd_hex(args) -> int:
    data = _load(args.path, args.max_bytes)
    result = dump_window(data, args.offset, args.length)
    if args.json:
        _print(result)
    else:
        for row in result["rows"]:
            hexpart = " ".join(row["hex"]).ljust(16 * 3 - 1)
            print(f"{row['offset']:08x}  {hexpart}  |{row['ascii']}|")
    return 0


def cmd_strings(args) -> int:
    data = _load(args.path, args.max_bytes)
    strings = extract_strings(data, args.min_len)
    if args.search:
        needle = args.search.lower()
        strings = [s for s in strings if needle in s["value"].lower()]
    if args.json:
        _print(strings)
    else:
        for s in strings:
            print(f"{s['offset']:08x}  [{s['encoding']:>8}] {s['value']}")
    return 0


def cmd_entropy(args) -> int:
    data = _load(args.path, args.max_bytes)
    if args.json:
        _print({"entropy": round(shannon(data), 4),
                "classification": classify(shannon(data)),
                "blocks": block_entropy(data, args.block)})
    else:
        print(f"overall entropy: {shannon(data):.4f} "
              f"({classify(shannon(data))})")
        for b in block_entropy(data, args.block):
            bar = "#" * int(b["entropy"] * 8)
            print(f"{b['offset']:08x}  {b['entropy']:5.2f} {bar}")
    return 0


def cmd_structures(args) -> int:
    bf = BinaryFile(args.path)
    data = _load(args.path, args.max_bytes)
    m = identify_file(data)
    meta, regions = parse(data, m["extension"])
    if args.json:
        _print({"magic": m, "meta": meta, "regions": regions})
    else:
        print(f"{m['description']}: {len(regions)} region(s)")
        for r in regions:
            print(f"  {r['start']:>10}..{r['end']:>10}  "
                  f"{r['name']:<18} {r['detail']}")
    return 0


def cmd_compare(args) -> int:
    a = _load(args.a, args.max_bytes)
    b = _load(args.b, args.max_bytes)
    result = compare(a, b)
    _print(result) if args.json else _print_compare(result)
    return 0


def _print_compare(r: dict) -> None:
    print(f"size:    {r['size_a']} -> {r['size_b']} "
          f"(delta {r['size_delta']:+d})")
    print(f"entropy: {r['entropy_a']} -> {r['entropy_b']} "
          f"(delta {r['entropy_delta']:+.4f})")
    print(f"shared blocks: {r['shared_blocks']}  "
          f"Jaccard similarity: {r['jaccard_similarity']}")
    if r["aligned"]:
        al = r["aligned"]
        print(f"aligned: {al['differing_bytes']} differing bytes "
              f"({al['percent']}%)")
    print(f"strings added: {len(r['strings_added'])}  "
          f"removed: {len(r['strings_removed'])}")


def cmd_serve(args) -> int:
    from .server import serve
    serve(args.path, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bytelens",
        description="Bytelens — zero-dependency local binary inspection "
                    "workbench.")
    p.add_argument("--version", action="version",
                   version=f"bytelens {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add_io(sp):
        sp.add_argument("path", help="file to inspect")
        sp.add_argument("--max-bytes", type=int,
                        default=DEFAULT_MAX_BYTES,
                        help="fully-loaded ceiling (default 64 MiB)")
        sp.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")

    sp = sub.add_parser("analyze", help="full inspection report")
    add_io(sp)
    sp.add_argument("--no-strings", action="store_true")
    sp.add_argument("--no-structure", action="store_true")
    sp.add_argument("--no-carve", action="store_true")
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("hex", help="paginated hex dump")
    add_io(sp)
    sp.add_argument("--offset", type=int, default=0)
    sp.add_argument("--length", type=int, default=256)
    sp.set_defaults(func=cmd_hex)

    sp = sub.add_parser("strings", help="extract printable strings")
    add_io(sp)
    sp.add_argument("--min-len", type=int, default=4)
    sp.add_argument("--search", help="filter by substring")
    sp.set_defaults(func=cmd_strings)

    sp = sub.add_parser("entropy", help="entropy and block entropy")
    add_io(sp)
    sp.add_argument("--block", type=int, default=4096)
    sp.set_defaults(func=cmd_entropy)

    sp = sub.add_parser("structures", help="container structure regions")
    add_io(sp)
    sp.set_defaults(func=cmd_structures)

    sp = sub.add_parser("compare", help="compare two binaries")
    sp.add_argument("a", help="first file")
    sp.add_argument("b", help="second file")
    sp.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("serve", help="interactive web dashboard")
    sp.add_argument("path", help="file to inspect")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8854)
    sp.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
