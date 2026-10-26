# v0.13.0 checkpoint — 2026-10-26

Status: implemented, reviewed by an independent reviewer, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Scope: Jev returned `sem_consenso` for the gate design ([decisions.md](decisions.md) D1). The most reversible option was adopted: an opt-in gate, with no change to the command without the flag.
- A Haiku worker implemented the gate and its tests (T01); an independent Haiku reviewer tried to break it (T02).
- Review findings and the coordinator's resolution:
  - P2, floating-point boundary: a rise of exactly `R` failed (`100 -> 115` at `0.15`). Fixed with exact decimal arithmetic; the same change fixes identical integers above 2^53.
  - P2, a changed measurement source on a judged metric let the gate return `pass`. Fixed: with no certain regression the status is `incomparable` (exit 2); a certain regression still wins.
  - P3: duplicate JSON keys could shadow a regressed value (now rejected when the flag is given); the standalone entry point printed a traceback and exited 1 on bad input (now exit 2 like the CLI); an integer beyond float range crashed (now invalid input); the spec described a schema-mismatch branch that cannot be reached (spec corrected); test gaps (added).
- A mutation check broke the gate in 9 ways in a temporary copy; the suite failed each time after two tests were strengthened (the duplicate-key tests first covered only one file and one entry point).

## Verification

- `python -m unittest discover -s tests`: exit 0, 188 tests, 3 POSIX-only skipped.
- `python -m inonu_harness check`: exit 0.
- `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: both skills `updated`; `bundle status` unchanged otherwise.

## Limits

- The gate compares two saved local measurements. It says nothing about agent quality, productivity or the benefit of the Harness.
- Labeled-result fixtures and judge precision/recall were left out: the repository has no automated judge to measure.

## Next

v0.14.0: a loop with termination by verified state and mandatory limits, per [research.md](../v0.10.0/research.md). Running a real agent in the loop would involve cost, so its first slice should stay a deterministic runner that drives a caller-supplied command.
