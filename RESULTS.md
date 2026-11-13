# Multi-environment TIS run: predictions and results

Claim under test (2026-11-14): "TIS runs surprisingly anywhere" —
the listing knows no registers and no syscalls, so porting cost is
re-implementing 25 instruction forms plus a thin driver per land.

## Calibration (local, before push)

- Known answer: tisrun.pl on this machine reproduces demo2 = 56877,
  demo and streamsum goldens; TisAtom agrees byte-for-byte on all 3.
- Golden outputs were frozen from tisrun only after that agreement.

## Predictions (fixed before the GitHub run)

- P1: TisAtom (Python) matches golden on all 4 legs
  (ubuntu-latest x86_64, ubuntu-24.04-arm ARM64, macos-latest, windows-latest)
- P2: tisrun (Perl) is present and matches golden on all 4 legs.
  Sole allowed exception: the Windows Perl leg may differ only by CRLF
  translation of newlines (reported as PASS-CRLF)
- P3: Cross-check tisrun vs TisAtom passes on every leg (modulo CRLF)
- P4: The native ELF boundary step runs demo2.elf successfully only on
  the Linux x86_64 leg; on ARM and non-Linux legs it does not run
  (informational step, does not fail the job)

## Results

Actions run 43530747178 (push of the workflow commit itself):
all 4 jobs success.

| Leg | Platform | Python executor | Perl executor | Cross-check |
|---|---|---|---|---|
| ubuntu-latest | Linux x86_64 | PASS 3/3 | PASS 3/3 (/usr/bin/perl) | PASS |
| ubuntu-24.04-arm | Linux aarch64 | PASS 3/3 | PASS 3/3 (/usr/bin/perl) | PASS |
| macos-latest | Darwin arm64 | PASS 3/3 | PASS 3/3 (Homebrew perl) | PASS |
| windows-latest | Windows AMD64 | PASS 3/3 | PASS-CRLF 3/3 (Strawberry Perl) | PASS |

- P1 PASS, P2 PASS (with exactly the predicted CRLF exception):
  on Windows, tisrun output differs from golden only by CRLF
  translation of newlines (demo2 7B vs 6B, demo 165B vs 154B,
  streamsum 35B vs 34B — the deltas are exactly the newline counts).
  Semantics identical; the difference is the platform text layer.
- P3 PASS: cross-executor check passed on every leg.
- P4 PASS: native/demo2.elf (1,724B, Linux x86_64 ELF) printed 56877
  on the Linux x86_64 leg only; on the ARM64 Linux leg it did not run;
  the step is skipped on macOS/Windows legs.

## Reading

TIS itself crossed OS and CPU boundaries untouched: the same three
listings produced byte-identical output on Linux x86_64, Linux ARM64,
macOS ARM64 and Windows x64, under two independent executors.
The only crack appeared exactly where predicted — not in TIS
semantics but in the Windows text layer's CRLF translation, i.e. in
the host's stdout plumbing, which the Perl executor inherits and the
Python executor (writing to a pipe it controls) does not.
The native ELF, by contrast, stayed home: one leg out of four.
Portability lives in the paper (the listing), not in the binary.
