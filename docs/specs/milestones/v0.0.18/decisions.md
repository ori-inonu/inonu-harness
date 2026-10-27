# v0.0.18 decisions

## D1 — Scope (Jev, consensus)

- Spec id `inonu-v018-graph-asof`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) a read-only `decisions as-of TIMESTAMP`; (b) a revision diff command; (c) both; (d) validity columns with a backfill.
- Result: `consenso`, leader `a_as_of_query`, mean 0.85, agreement 1.0, margin ≥ 0.69 over two rounds. Rail probabilities: a 0.01, b 0.01, c 0.03, d 1.00 (a schema change is a data migration, which stays fenced).
- Adopted as engineering scope. It grants no authorization.

## D2 — Why history is enough

Every `decision_history` row stores the complete decision snapshot, the event and a timestamp, so the state at an instant is the latest snapshot at or before it. The query adds no data and no schema; it cannot answer for instants before the first revision, and the timestamps are the recording machine's clock.

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
