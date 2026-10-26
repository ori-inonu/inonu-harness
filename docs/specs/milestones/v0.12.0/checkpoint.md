# v0.12.0 checkpoint — 2026-10-26

Status: implemented, reviewed three times by independent reviewers, and applied to the owner's host under the authorization recorded in [v0.11.0 decisions](../v0.11.0/decisions.md) D2. Nothing is committed or pushed. This milestone does not complete the broader single-install objective.

## Flow

- Haiku workers implemented T01 (code and tests) and T02 (docs). The coordinator made every review fix.
- Review 1 (safety and spec fidelity): 1 P1, 4 P2 and several P3. Fixed: launcher lookup from the current directory, non-transactional apply, CRLF block, untruthful conflict report, status/hook mismatch, pre-existing empty files and directories, non-finite JSON, directory pruning.
- Review 2 (two fresh adversarial reviewers): bare `cmd` launcher (P1), rollback overwriting a later outside edit, stale created markers, a second Stop hook from another checkout, ledger directory ownership, edited hook classified as absent, plus test gaps. All fixed.
- Review 3 (one fresh reviewer, narrow): rollback on `KeyboardInterrupt`, an unrecorded identical worker file blocking remove, backups outside the transaction, a foreign Stop hook without a ledger, duplicate JSON keys, and an overclaim about byte-exact restore. All fixed or reworded.
- A mutation check broke `bundle_apply.py` in 10 ways in a temporary copy; the suite failed each time (no survivors).

## Verification

- `python -m unittest discover -s tests`: exit 0, 156 tests, 3 POSIX-only skipped.
- `python -m inonu_harness check`: exit 0.
- Fault injection: an `OSError` and a `KeyboardInterrupt` at every write point leave only the original files.

## Applied on the owner's host

- Preview first, then `bundle apply --host both --apply` without `--with-stop-hook`.
- Updated the skill in both hosts, installed the Claude worker agent (`model: haiku`), registered `sequential-thinking` in the Codex configuration (an existing config was backed up to `~/.inonu-harness/backups`).
- `codegraph`, `headroom` and Claude's `sequential-thinking` already existed and were left untouched (`unchanged`).
- A second apply reports `unchanged`; `bundle status` reports every item `current`/`configured` except the hook.
- The Stop hook was not installed on purpose: it runs the Inonu checkout's own suite on every Stop of every project, which neither verifies the project at hand nor is cheap. It stays opt-in (`--with-stop-hook`).

## Limits

- `configured` is not reachability; a session must be restarted to load a new MCP entry or agent.
- Restoring a JSON file restores its content, not its formatting; backups are kept.
- The race window between re-reading and replacing a file that a host writes concurrently remains.
- Claude's `sequential-thinking` entry (added by hand earlier, not by the bundle) still launches `cmd` by bare name.

## Next

v0.13.0: an evaluation threshold (`baseline compare --max-regression`) and labeled-result fixtures, then the state-terminated loop with mandatory limits (v0.14.0), per [research.md](../v0.10.0/research.md). Neither touches host configuration.
