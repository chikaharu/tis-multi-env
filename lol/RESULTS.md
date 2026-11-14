# LOL multi-environment results (2026-11-14)

Run: https://github.com/chikaharu/tis-multi-env/actions/runs/43534358395
(commit 622a834, all four legs success)

- M1 PASS: the LOL check passed on all four legs (Linux x86_64,
  Linux ARM64, macOS ARM64, Windows x64), and the converted image
  was byte-identical to the golden on every leg: 1,740 bytes,
  sha256 34780c5b29491e77d8e73d7f7b62804aa4f697c0431726252da908633793dd46.
- M2 PASS: row reconstruction identical on all legs
  (0x2a / 0xffffffffffffffff / 0x8000000000000001), negative
  control moved exactly 1 bit on all legs.
- M3 PASS: no CRLF exception on the Windows leg this time
  (the TIS Perl executor in the same run still shows its
  PASS-CRLF exception). The .edges file is pinned to LF and
  parsed by whitespace, and the image itself is `*.lol binary`.

Boundary: this measures the format + the CPython reader with
Python 3.12 pinned by CI. Other Python versions and non-Python
readers are unmeasured.
