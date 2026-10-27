# v0.0.21 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Source: gap G4 of the [source-level research](../v0.0.20/research-reverse-engineering.md): Beads computes what to work on next as a deterministic query, while the Decision Graph could only list by status.
- Scope: Jev returned `sem_consenso` ([decisions.md](decisions.md) D1). The most reversible option was adopted: a read-only `decisions ready`. The combination with a `tools` allowlist for the worker agent (rail probability 0.40) was not adopted; that allowlist is deferred because it changes what the owner's installed agent may do on the next `bundle apply`.
- A Haiku worker built the command, tests and docs (T01); an independent Haiku reviewer then tried to make a wrong decision look ready (T02). There were no P1 findings.
- Review findings and the coordinator's resolution:
  - P2, the store did not validate records when it read them. A dependency list stored as an empty string or object was read as "no dependencies", so a decision waiting on a pending dependency was listed as ready. The same gap hid decisions behind a status typo, listed a decision twice when a record id was duplicated, and let a string become a list of characters.
  - P2, deeply nested or non-JSON stored text raised a `RecursionError` traceback naming absolute paths (exit 1) or printed the JSON library's own message, for `list`, `show`, `as-of` and `ready` alike.
  - Fix (shared by every command that reads decisions): each stored record is validated on read for list and object shapes, a known status, and an id that matches its row, and history entries are checked against their row and their snapshot. Any failure, and any JSON that is invalid or nested too deeply, becomes `decision store contains an unreadable record` with exit 2.
  - P3: test gaps (mixed-case ids in the sort test, a missing database next to existing files, corrupt records of each shape) added; the docs claimed "nothing is written" while a WAL-mode database converted by an outside tool gets helper files (the 0.0.18 qualifier is now stated); and "ready" could read like a gate when the graph does not require a decision's dependencies to be authorized first (the docs now say it looks only at direct dependencies).
  - P3, not fixed: two writers that revise dependencies at the same instant can store a dependency cycle, because the cycle check runs outside the write transaction. This predates `ready`; both decisions then show as waiting on each other. It is recorded in the changelog limits.
- A mutation check broke the store validation in 6 ways; one mutant first survived because the history test changed only the entry id, which the snapshot comparison already refused, so the comparison with the row was never exercised. The test now changes both ids consistently and the mutant is caught.

## Verification

- `python -m unittest discover -s tests`: exit 0, 4 skipped (three POSIX-only, one file-symlink case that needs a privilege this host lacks).
- `python -m inonu_harness check`: exit 0. `python -m inonu_harness docs lint`: pass. `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: both skills updated.

## Limits

- `ready` reports only direct declared dependencies and authorizes, claims or schedules nothing. Its output includes the owner's decision text and is not scanned for credentials.
- The dependency-cycle race above is not fixed. The worker agent `tools` allowlist and ledger digests remain open.

## Next

The commit and push (the owner's go-ahead is needed), then `python -m inonu_harness check --ref HEAD`. Candidate work: re-check dependency cycles inside the write transaction, the worker agent `tools` allowlist, and ledger post-write digests.
