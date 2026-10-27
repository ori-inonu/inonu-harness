# v0.0.25 checkpoint — 2026-10-26

Status: implemented, reviewed, fixed and verified locally. Nothing from this milestone is committed. The installed skill profiles for Claude and Codex were refreshed with `bundle apply` under the existing authorization, so `milestone new` and `milestone check` reach every project that loads them.

## Flow

- Research: [research-synthesis.md](research-synthesis.md) and eleven area files read GSD (`gsd-build/get-shit-done`), GSD 2, gstack, OpenSpec, spec-kit and superpowers from primary sources, each area read by one Haiku-class model and re-fetched by another. The LeanRea skill was installed first, pinned and reviewed; only its evidence method was used.
- Scope: chosen by the Jev judge from [brief.md](brief.md) ([decisions.md](decisions.md) D1): consensus, leader `milestone new` and `milestone check`, mean 0.79, rail probability 0.09. It is the second consensus in a row with a written brief; the 0.0.22 run with a brief ended without consensus.
- Build: a Haiku worker wrote `inonu_harness/milestones.py`, the `milestone` subcommand, the conditional `milestones` step of `check` and the tests (T01); a second wrote `docs/milestones.md`, the README, AGENTS.md, sdd-workflow and skill text, the CHANGELOG and the version bump (T02). The spec's R9 and R11 conflicted when read literally; the worker's resolutions are recorded in decisions.md D4 and in the spec.
- Review (T03, independent) found 2 P1, 5 P2 and 10 P3 items; the coordinator fixed them:
  - P1, `check --ref` passed a commit whose milestone file is a committed symbolic link, because the export writes a link as a plain file that the check read as an empty milestone. Fixed: the export reports committed symlinks and a link under the milestones folder fails the `milestones` step.
  - P1, a range whose end had ten digits (`R1-R1000000000`) was read as the bare `R1` and passed. Fixed: ids are read whole and refused above nine digits, also for a 5,000-digit id that would have crashed `int()`.
  - P2, the section rule counted `R<n>` items under `## Out of scope`; the cost of a hostile `tasks.md` was linear in the cited ids (up to 120,000 findings from 1.7 KB). Fixed: deferred-work sections end the requirements; ranges are intervals; at most 10,000 references and 50 findings per rule, reported as `reference_limit_exceeded` and `findings_truncated`.
  - P2, the docs omitted the new step in `docs/plugin.md`, and four boundary mutants survived (tilde fences, a pipe in prose, a section heading, a byte order mark). Fixed.
  - P3, a FIFO named `spec.md` would block the read, `R2D2` counted as a citation, a requirement kept in an HTML comment counted, and several doc claims did not match the code (the indentation of the JSON example, the version a manifest carries, a named version when the directory is absent). Fixed. A race message, the case of a Windows folder `V0.0.26` and `R1—R3` with an em dash stay as documented limits.
- A mutation check broke the fixes in 15 ways; 14 were caught at once and the survivor (an HTML comment closed on its own line) got a test and is caught.

## Verification

- `python -m unittest discover -s tests`: exit 0, 634 tests, 8 skipped (symbolic-link, FIFO and POSIX-only cases that this host cannot run).
- `python -m inonu_harness check`: exit 0, steps `compile`, `versions`, `milestones`, `tests`. `docs lint`: pass, 153 files. `version --scheme`: exit 0; `version --next`: `0.0.26`. `milestone check --from 0.0.9`: pass over 17 milestones, one warning (`decisions_missing` for v0.0.12, which has no decision record and was not backfilled).
- `bundle apply --host both --apply`: both skills updated; both installed `SKILL.md` files carry `milestone new`.
- A scratch project run through `scripts/inonu.py`: `milestone new` created `v0.0.1`, a second `milestone new` created `v0.0.2`, and `milestone check` passed both.

## Limits

- The commands read the formats they describe (`R<n>` list items, a task table) and report. They never edit a requirement, bump a manifest, write `checkpoint.md` or decide that work is done; a citation means a task claims the requirement, not that it passed.
- The milestones before v0.0.9 predate the `R<n>` format and are not checked by this repository's `check`.
- Not verified: the FIFO and real-symlink cases (this host cannot create them; a patched variant covers the containment branch), POSIX behaviour, two concurrent `new` runs on POSIX, and the `--ref` export of a commit that lacks `milestones.py` (it fails with an import error from that commit).
- Closing a milestone (a deferred-items ledger and an index), append-only gap tasks and pause and resume remain open; the research ranks them.

## Next

The commit of v0.0.24, v0.0.25 and the research needs the owner's go-ahead. The next candidate is the close of a milestone: a deferred-items ledger, a newest-first `MILESTONES.md` index and a guard for `1.0.0` (research items C, D and G).
