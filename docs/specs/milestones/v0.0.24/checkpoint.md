# v0.0.24 checkpoint — 2026-10-26

Status: implemented, reviewed twice, fixed and verified locally. Nothing from this milestone is committed. The installed skill profiles for Claude and Codex were refreshed with `bundle apply` under the existing authorization, so the versioning rule reaches every project that loads them.

## Flow

- Scope of the release-hygiene part: chosen by the Jev judge from [brief.md](brief.md) ([decisions.md](decisions.md) D1, consensus, rail probability 0.02). The version scheme (R8 to R13) and the renumbering were set by the owner (D4).
- Renumbering: milestones 1 to 24 went from `v0.N.0` to `v0.0.N`, as 24 directory names (23 of them tracked, moved with `git mv`) and as references in docs, tests, manifests and fixtures. The coordinator's script changed 109 files and skipped two test values that are not Inonu versions. Nothing in the git history changed.
- First implementation (T01, a Haiku worker) and its review (T02): 4 P1 and several P2 findings; the coordinator fixed the main ones (a regular expression read `__version__` from docstrings, an `exists()` that behaves differently between Python 3.11 and 3.14, a silent skip of unlistable folders, a case-sensitive skill name).
- Second worker (T04) built the scheme, the `version` subcommand, `docs/versioning.md`, the tests and the docs. A second independent review found 4 P1, 4 P2 and 7 P3 items:
  - P1, the renumbering edited three files that `docs/specs/milestones/v0.0.8/audit.json` pins by SHA-256, so the recorded self-audit failed while the suite stayed green. Fixed: the three hashes were refreshed once and `tests/test_sdd_audit_cli.py` now runs that audit.
  - P1, the audit read only simple top-level assignments, so a rebinding of `__version__` in a block, tuple, loop, import, function or `del` gave a false pass. Fixed: any such form makes the version unusable.
  - P1, a link below `skills/` to a folder elsewhere in the root was dropped silently, so an oversized skill passed. Fixed in the shared walk: such a link is followed, a link to a folder already below the walked one is read once at its real place, a cycle ends, and a link out of the root is reported.
  - P1, the audit followed a manifest through a link out of the root. Fixed: it is refused, without echoing the file.
  - P2, a stray `version0.9.0` the renumbering missed in `v0.0.9/tasks.md`, and four surviving boundary mutants (the 40-character version cap, the 1 MiB read, an augmented assignment, the read bound). Fixed or covered; the read bound stays untested and is documented.
  - P3, non-text input raised `TypeError` (now `ValueError`), an unreadable `SKILL.md` aborted the lint (now `file_unreadable`), the skill's `docs lint` bullet and `docs/plugin.md` omitted the new rules, and the module docstring was wrong for `-m` (all fixed). An f-string or tuple version is reported unusable by design.
- A mutation check broke the fixes in 11 ways; 10 were caught. The survivor turns link following off, and it is an equivalent mutant on this Windows host, where a junction is descended into even without `followlinks`; on POSIX the same test uses a real symbolic link.

## Verification

- `python -m unittest discover -s tests`: exit 0, 567 tests, 6 skipped (symbolic-link and POSIX-only cases that this host cannot run).
- `python -m inonu_harness check`: exit 0, with the `versions` step between `compile` and `tests`. `docs lint`: pass, 134 files. `version --scheme`: exit 0. `version --next`: `0.0.25`. `git diff --check`: exit 0.
- `bundle apply --host both --apply`: both skills updated; both installed `SKILL.md` files carry the `version --scheme` command.

## Limits

- The reading that the two-digit limit also applies to the minor is the coordinator's, recorded in D4 for the owner to change.
- `--next` exits 1 when the version is `0.99.99` or when no manifest states one; the spec names no code for either. Reversible.
- Not verified: POSIX and macOS paths, a real symbolic link on this host, and the `version` subcommand from a runner started in another directory beyond one check.
- The audit reads source text: a version set at run time is invisible to it.

## Next

The commit of this milestone needs the owner's go-ahead, as the earlier one did. Research for the next milestone is in `docs/specs/milestones/v0.0.25/`.
