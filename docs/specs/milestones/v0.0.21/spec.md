# v0.0.21 — A deterministic ready queue for decisions

The source-level research ([v0.0.20 research](../v0.0.20/research-reverse-engineering.md), gap G4) found that Beads computes what to work on next as a deterministic query over a derived state, instead of leaving it to an agent's judgement. The Decision Graph can only list decisions by status (`pending()`), so "what can be decided now" is an agent judgement. This milestone adds that query. It is read-only, changes no schema and treats no recommendation as authorization. The scope was decided by Jev without consensus ([decisions.md](decisions.md)).

## Requirements

- R1 `python -m inonu_harness decisions --db PATH ready`. The database must already exist and is opened read-only exactly as `decisions context` and `decisions as-of` do; it is never created or written.
- R2 A decision is listed only if its status is `pending`. It is **ready** when every decision in its declared `dependencies` has status `authorized` (a decision with no dependencies is ready). It is **waiting** otherwise.
- R3 Output (stdout, one JSON object, ASCII-escaped like `as-of`): `{"schema_version": 1, "ready": [...], "waiting": [...]}`.
  - Each `ready` item has `id`, `question` and `dependencies` (the declared list).
  - Each `waiting` item has `id`, `question` and `waiting_on`, a list of `{"id", "status"}` for each dependency that is not authorized, in the declared order; a dependency that is not in the database has status `missing`.
  - Both lists are sorted by `id`. Decisions that are `blocked`, `invalidated` or `authorized` do not appear.
- R4 `ready` says only that the declared dependencies are authorized. It does not authorize the decision, claim a worker or schedule anything.
- R5 Invalid input and unreadable stores exit 2 with the generic messages the other read-only commands use, and nothing is printed to stdout. The database file is byte-identical afterwards.
- R6 Tests use a temporary database built through the public API, and cover:
  - an empty database;
  - a decision with no dependencies;
  - one that waits on a pending dependency, on a blocked one, on an invalidated one and on several at once (declared order kept);
  - becoming ready after its dependency is authorized;
  - authorized, blocked and invalidated decisions not listed;
  - sorting;
  - a dependency missing from the database;
  - determinism;
  - the database bytes unchanged;
  - non-ASCII question text under a strict ASCII stdout;
  - the CLI path and exit codes.
- R7 Docs: CHANGELOG 0.0.21, README, a short Portuguese paragraph in `docs/sdd-workflow.md`, and a skill bullet. They state what ready means (and does not), that the output includes the owner's decision text like `show`, and that it does not scan for credentials. Version 0.0.21 in `__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and the tests.

## Out of scope

Claiming or leasing decisions, a materialized readiness flag, non-blocking link types, hash-based identifiers (all need schema changes or concurrency design), the worker agent `tools` allowlist (deferred, see decisions), and ledger digests.
