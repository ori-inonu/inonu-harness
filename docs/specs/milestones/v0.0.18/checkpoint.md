# v0.0.18 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Motivation: the graph-engineering research found that memory graphs such as Graphiti keep validity over time and invalidate rather than delete. A schema migration for validity columns stays fenced, but every `decision_history` row already stores the full snapshot and a timestamp, so the state at an instant can be derived from history alone.
- Scope: Jev consensus for a read-only `decisions as-of` ([decisions.md](decisions.md) D1); the migration option scored a rail probability of 1.00.
- A Haiku worker built the query, tests and docs (T01); an independent Haiku reviewer then tried to break it (T02). There were no P1 findings.
- Review findings and the coordinator's resolution:
  - P2, an offset that pushed the instant past year 1 or 9999 raised an uncaught `OverflowError` (exit 1, traceback). Now exit 2 with the generic message.
  - P2, the suite could not detect a string comparison of recorded times, which mis-orders mixed offsets, nor the highest-revision rule under clock skew. Tests added for both.
  - P2, a database an outside tool had switched to WAL mode gets `-wal` and `-shm` files when opened read-only, which `context` and `packet` already did. Documented as a limit instead of refusing such databases, which would have changed two existing commands.
  - P3: the output was not ASCII-escaped, so decision text outside the stdout code page turned a successful query into exit 2 (fixed for `as-of`); a corrupt history record raised a traceback (now exit 2 with a generic message for every decisions command, including `show`); the skill bullet lacked "changes no schema".
- A mutation check broke the query in 9 ways in temporary copies; the suite failed each time. One mutant first survived because the ASCII test used `StringIO`, which accepts any character; it now uses a strict ASCII stdout.

## Verification

- `python -m unittest discover -s tests`: exit 0, 319 tests, 4 skipped (three POSIX-only, one file-symlink case that needs a privilege this host lacks).
- `python -m inonu_harness check`: exit 0. `python -m inonu_harness docs lint`: pass. `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: both skills updated.

## Limits

- Times are the clock of the machine that recorded each revision and are not authenticated: this is a local audit aid, not a tamper-proof ledger. A state older than the first revision cannot be shown.
- The database file is never modified; a WAL-mode database converted by an outside tool may still get SQLite helper files.
- No validity columns, no revision diff, no repair of history.

## Next

The commit and push (the owner's go-ahead is needed), then `python -m inonu_harness check --ref HEAD`. Candidate unblocked work: a secret-pattern scan for decision packets, and a revision-diff command.
