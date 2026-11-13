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

(to be filled from the Actions run)
