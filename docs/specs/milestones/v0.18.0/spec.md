# v0.18.0 — Temporal queries on the Decision Graph

The research ([v0.10.0 research](../v0.10.0/research.md)) found that graph memories such as Graphiti keep a validity window per fact and invalidate a contradicted fact instead of deleting it, so "what held on that date" stays answerable. Adding validity columns to the SQLite schema would be a data migration and stays blocked. The Decision Graph already stores the full decision snapshot and a timestamp for every revision, so the same question can be answered by reading history. This milestone adds that query. It is read-only and changes no schema. The scope was chosen by Jev consensus ([decisions.md](decisions.md)).

## Requirements

- R1 `python -m inonu_harness decisions --db PATH as-of TIMESTAMP [--ids ID...]`. The database must already exist and is opened read-only, exactly as `decisions context` does; it is never created or written. `TIMESTAMP` is ISO 8601 with an explicit offset or `Z`; a timestamp without an offset is invalid input.
- R2 Output (stdout, one JSON object): `{"schema_version": 1, "as_of": <the instant in UTC, ISO 8601>, "decisions": [...]}`. Each item has `id`, `state`, `revision`, `recorded_at`, `later_revision` and `snapshot`:
  - the snapshot is the history entry of the highest revision whose recorded time is at or before the instant (the instant itself is included), serialized as `decisions show` serializes a decision;
  - `state` is `existed` for such a decision, with `revision`, `recorded_at` and `snapshot` set and `later_revision` true when a later revision exists;
  - for an id requested with `--ids` that was created after the instant, `state` is `not_yet_created`, `revision` and `recorded_at` and `snapshot` are `null` and `later_revision` is `true`.
  Without `--ids`, only decisions that existed at the instant are listed. Items are sorted by `id`, so the output is deterministic.
- R3 Invalid input exits 2 with a generic message that holds no absolute path: an unparseable or offset-less timestamp, an id that is not in the database, and an unreadable or unsupported database. Nothing is printed to stdout on error.
- R4 The query writes nothing: the database file is byte-identical afterwards. A database that an outside tool switched to WAL mode may get `-wal` and `-shm` helper files created by SQLite when it is opened, as `decisions context` already does; the store never enables WAL itself, and this is a documented limit rather than a refusal.
- R5 Tests use a temporary database built through the public API with a deterministic clock, and cover:
  - an instant before any decision (empty list, and `not_yet_created` with `--ids`);
  - between two revisions of one decision (the old revision, `later_revision` true);
  - after the last revision (`later_revision` false);
  - an instant equal to a revision's time (included);
  - the same instant written with `Z` and with an offset;
  - a decision that was invalidated by a premise change, shown with its earlier status;
  - recommendation and authorization recorded later than the instant do not appear in the earlier snapshot;
  - `--ids` filtering and ordering;
  - unknown id, naive timestamp and a missing database all exit 2;
  - the database bytes unchanged;
  - the CLI path.
- R6 Docs: CHANGELOG 0.18.0, README, a short Portuguese paragraph in `docs/sdd-workflow.md`, and a skill bullet. They state that times come from the clock of the machine that recorded them and are not authenticated, so the result is a local audit aid and not a tamper-proof ledger; that it reads history and cannot show a state older than the first revision; and that it does not change the schema. Version 0.18.0 in `__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and the tests.

## Out of scope

Validity columns or any schema change, a revision diff command, writing or repairing history, and the allowlisted `context` projection (this command is an owner-facing audit view like `show`).
