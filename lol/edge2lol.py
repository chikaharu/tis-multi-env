#!/usr/bin/env python3
"""edge2lol -- convert an edge list into a LOL binary, and read it back.

A LOL binary (Load OnLy binary) stores no 64-bit row anywhere.
Each row exists only as the bundle of its 64 one-bit load answers:
a record (addr, k, bit) says "loading bit k of the row at addr
returns bit".  A row is defined iff all 64 answers for its addr
exist, and no (addr, k) is answered twice with different bits
(extensionality: the same question must give the same answer).

Subcommands:
  convert IN.edges OUT.lol   edge list -> LOL binary
  load OUT.lol ADDR          print the row at ADDR, assembled from
                             64 one-bit loads and nothing else
  verify IN.edges OUT.lol    rebuild every row via one-bit loads
                             and compare; also runs the negative
                             control (flip one record, expect
                             exactly one bit of one row to change)
"""
import struct
import sys

MAGIC = b"LOL1"
REC = struct.Struct("<QB")        # addr u64, packed: k bits 0..5, val bit 7
HEADER = struct.Struct("<4sII")   # magic, record_count, row_count


def parse_edges(path):
    rows = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            a, v = line.split()
            addr, val = int(a, 16), int(v, 16)
            if not (0 <= addr < 2 ** 64 and 0 <= val < 2 ** 64):
                raise ValueError("out of u64 range: " + line)
            if addr in rows and rows[addr] != val:
                raise ValueError("conflicting rows for addr %#x" % addr)
            rows[addr] = val
    return rows


def convert(in_path, out_path):
    rows = parse_edges(in_path)
    recs = []
    for addr in sorted(rows):
        val = rows[addr]
        for k in range(64):
            bit = (val >> k) & 1
            recs.append((addr, k | (bit << 7)))
    with open(out_path, "wb") as f:
        f.write(HEADER.pack(MAGIC, len(recs), len(rows)))
        for addr, packed in recs:
            f.write(REC.pack(addr, packed))
    print("rows=%d records=%d bytes=%d"
          % (len(rows), len(recs), HEADER.size + REC.size * len(recs)))


class LolImage:
    """The only read primitive is load_bit(addr, k)."""

    def __init__(self, path):
        data = open(path, "rb").read()
        magic, nrec, nrows = HEADER.unpack_from(data, 0)
        if magic != MAGIC:
            raise ValueError("not a LOL1 image")
        self.answers = {}
        off = HEADER.size
        for _ in range(nrec):
            addr, packed = REC.unpack_from(data, off)
            off += REC.size
            k, bit = packed & 0x3F, (packed >> 7) & 1
            key = (addr, k)
            if key in self.answers and self.answers[key] != bit:
                raise ValueError(
                    "conflicting answers for (%#x, %d)" % key)
            self.answers[key] = bit
        self.nrows = nrows

    def load_bit(self, addr, k):
        return self.answers[(addr, k)]

    def load_row(self, addr):
        val = 0
        for k in range(64):
            val |= self.load_bit(addr, k) << k
        return val


def cmd_load(path, addr_s):
    img = LolImage(path)
    addr = int(addr_s, 16)
    print("%#018x" % img.load_row(addr))


def verify(in_path, lol_path):
    rows = parse_edges(in_path)
    img = LolImage(lol_path)
    bad = 0
    for addr, val in sorted(rows.items()):
        got = img.load_row(addr)
        if got != val:
            bad += 1
            print("MISMATCH addr=%#x want=%#018x got=%#018x"
                  % (addr, val, got))
    print("verify: %d/%d rows exact" % (len(rows) - bad, len(rows)))
    # Negative control: flip one record's answer in memory; exactly
    # one bit of exactly one row may change.
    addr0 = sorted(rows)[0]
    img.answers[(addr0, 0)] ^= 1
    diff = img.load_row(addr0) ^ rows[addr0]
    print("negative control: flipped bits = %d (expect 1)"
          % bin(diff).count("1"))
    return 0 if bad == 0 and diff == 1 else 1


def main(argv):
    if len(argv) >= 4 and argv[1] == "convert":
        convert(argv[2], argv[3])
        return 0
    if len(argv) >= 4 and argv[1] == "load":
        cmd_load(argv[2], argv[3])
        return 0
    if len(argv) >= 4 and argv[1] == "verify":
        return verify(argv[2], argv[3])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
