# tis-multi-env

Does TIS (Texectum Instruction Set v1) really run anywhere?
This repo tests the claim on GitHub Actions across operating systems
and CPU architectures, with two independent executors:

- `executors/tisrun.pl` — the reference VM (Perl)
- `executors/tis_atom.py` — an atom-trace port (Python, needs `link_atom.py`)

Cases (in `programs/`, inputs in `inputs/`, golden outputs in `expected/`):

- `demo2` — arithmetic, no input
- `demo` — wider instruction mix incl. float formatting
- `streamsum` — read_int / read_eof loop over 1,000 tokens

The runner (`ci/run_tis.py`) compares both executors byte-for-byte
against the golden output and against each other. A mismatch that is
only CRLF translation is reported as PASS-CRLF, not hidden.

A native Linux x86_64 ELF of demo2 (`native/demo2.elf`, built by the
tisbin route) is included as a boundary check: it is expected to run
only on the Linux x86_64 leg.

Run locally:

    python3 ci/run_tis.py
