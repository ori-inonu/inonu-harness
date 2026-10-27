# v0.0.17 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Motivation: the v0.0.15 review found that the plugin installs from committed files only, while many files added since v0.0.10 are untracked and the tracked `cli.py` imports some of them. `check` reads the working tree, so it could not see that gap.
- Scope: Jev returned `sem_consenso` ([decisions.md](decisions.md) D1). The most reversible option was adopted: `check --ref` only. The multi-OS CI change was deferred, not rejected, because it would make the first push run unverified code on three operating systems.
- A Haiku worker built `check --ref`, its tests and docs (T01); an independent Haiku reviewer then tried to break it (T02).
- Review findings and the coordinator's resolution:
  - P2, `git archive` applies `.gitattributes` (`export-ignore`, `export-subst`) and `core.autocrlf`, so a committed failing test marked `export-ignore` was dropped from the export and `check --ref` passed falsely. Fixed by replacing `git archive` with a direct export of the commit's own blobs (`git ls-tree -r -z` plus `git cat-file --batch`). It also validates every committed path (absolute, `..`, `.git`, colon and backslash names are refused), skips submodule entries and checks each blob header.
  - P3, a ref name outside the stdout code page turned a passing check into exit 2; the report is now ASCII-escaped.
  - P3, tests did not cover cleanup on failing outcomes, the git timeout, a missing git executable or option-like refs. Added.
- A mutation check broke `check --ref` in 8 ways in temporary copies. Two mutants first survived because my own corrupt-output test failed for the wrong reason (a fake with one object failed by truncation before the header check ran); the test now uses a single-entry listing and the mutants are caught. A redundant path-escape check that no input can reach was removed instead of tested.

## Evidence

The new command was used on copies of the current tree to simulate the two commits the owner could make:

- Commit of only the 107 already-tracked files (`git add -u`): `check --ref HEAD` exits 1 (`tests` 1, `runner` 1) with `ModuleNotFoundError: No module named 'inonu_harness.bundle'`.
- Commit of everything (53 files are untracked and not ignored): exits 0 with `compile`, `tests` and `runner` all 0.

## Verification

- `python -m unittest discover -s tests`: exit 0, 302 tests, 4 skipped (three POSIX-only, one file-symlink case that needs a privilege this host lacks).
- `python -m inonu_harness check`: exit 0. `python -m inonu_harness docs lint`: pass, 97 files, no findings. `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: both skills updated.

## Limits

- The check covers the operating system where it runs, and a passing result shows the commit is self-contained for the tests and the runner, not that the plugin installs.
- All blobs are held in memory once during the export; a symlink is exported as a plain file holding its target text.
- Not run: `claude plugin validate`, a live plugin install, the Linux and macOS paths.

## Next

Committing (the owner's go-ahead is needed) and then `python -m inonu_harness check --ref HEAD` on the result; the CI matrix proposal is waiting for that first push.
