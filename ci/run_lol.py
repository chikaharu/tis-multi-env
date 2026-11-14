#!/usr/bin/env python3
"""LOL multi-environment check.

Converts lol/sample.edges with lol/edge2lol.py and requires the
produced image to be byte-identical to expected/sample.lol, then
rebuilds every row through one-bit loads only, then flips one
record in memory and requires exactly one bit of one row to move.
Prints the image sha256 so the four legs can be compared by eye.
"""
import hashlib
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lol"))
import edge2lol as e  # noqa: E402

EDGES = os.path.join(ROOT, "lol", "sample.edges")
GOLDEN = os.path.join(ROOT, "expected", "sample.lol")
EXPECT_ROWS = {
    0x1: 0x000000000000002A,
    0x2: 0xFFFFFFFFFFFFFFFF,
    0x1000: 0x8000000000000001,
}


def main():
    golden = open(GOLDEN, "rb").read()
    print("golden: %d bytes sha256=%s"
          % (len(golden), hashlib.sha256(golden).hexdigest()))
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.lol")
        e.convert(EDGES, out)
        produced = open(out, "rb").read()
    assert produced == golden, "converted image differs from golden"
    print("convert: byte-identical to golden")
    img = e.LolImage(GOLDEN)
    for addr, want in sorted(EXPECT_ROWS.items()):
        got = img.load_row(addr)
        assert got == want, "row %#x: want %#018x got %#018x" % (
            addr, want, got)
        print("load %#x -> %#018x ok" % (addr, got))
    img.answers[(0x1, 0)] ^= 1
    diff = img.load_row(0x1) ^ EXPECT_ROWS[0x1]
    assert diff == 1, "negative control: %d bits moved" % (
        bin(diff).count("1"))
    print("negative control: exactly 1 bit moved")
    print("LOL CHECK PASS")


if __name__ == "__main__":
    main()
