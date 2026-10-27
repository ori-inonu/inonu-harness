# v0.0.17 — Check a commit, not just the working tree

The v0.0.15 review found that the plugin installs from committed files only, while 38 files added since v0.0.10 are still untracked and the tracked `cli.py` imports some of them. `check` reads the working tree, so it cannot see that gap. This milestone lets `check` verify a commit in isolation, so the moment of committing is provable instead of hoped for. It never commits, tags or pushes. The scope was decided by Jev without consensus ([decisions.md](decisions.md)).

## Requirements

- R1 `python -m inonu_harness check [--root PATH] [--ref REF]`. Without `--ref` nothing changes: same steps, same output keys, same exit codes.
- R2 With `--ref`, `--root` (default: this checkout) must be inside a git repository. The command resolves `REF` to a commit (`git rev-parse --verify REF^{commit}`), exports that commit's blobs, read with `git ls-tree -r -z` and `git cat-file --batch` (so no attribute or line-ending conversion applies, and submodule entries are skipped), into a temporary directory, refusing any path that is absolute or contains `..`, `.git`, a colon or a backslash, and runs there, in this order: `compile` and `tests` exactly as without the flag, then `runner`, which is `python scripts/inonu.py --version`. The output is the usual JSON plus `"ref"` (the string as given) and the extra `runner` step. Exit 0 only when every step exits 0, 1 otherwise.
- R3 Invalid input exits 2 with a generic message that holds no absolute path: a root that is not a git repository, a ref that does not resolve, a git failure or timeout (60 s), and an exported tree without a `tests` directory.
- R4 The temporary directory is removed on every outcome. Nothing in the repository is read or written beyond what read-only `git` commands do; no network is used.
- R4b The export is faithful: a committed file marked `export-ignore` is still present, `export-subst` placeholders are not expanded, and `core.autocrlf` does not change bytes. The reason is that `git archive` applies those rules, which let a committed failing test disappear from the check (found by the independent review).
- R5 Tests, using temporary git repositories with a minimal project (a passing test, a runner script):
  - a complete commit passes with the three steps and the `ref` key;
  - a module the tests import but that was never added makes the committed tree fail while the working tree still passes;
  - a tracked file modified but not committed does not change the result for `HEAD`;
  - a broken test that is committed fails even when the working tree has been fixed;
  - a ref that does not resolve, a root that is not a repository, and a commit without `tests/` all exit 2;
  - the temporary export is gone afterwards;
  - without the flag the output has neither `ref` nor `runner`.
- R6 Docs: CHANGELOG 0.0.17, README, `docs/plugin.md` (the pre-push procedure: commit, then `python -m inonu_harness check --ref HEAD`), and the skill bullet for `check`. They state that the check covers this operating system only, that the CI workflow is unchanged (D1), and that a passing result proves the commit is self-contained for the tests and the runner, not that the plugin installs. Version 0.0.17 in `__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and the tests.

## Out of scope

Changing the CI workflow, a commit or tag command, building artifacts, `claude plugin validate`, and any network access.
