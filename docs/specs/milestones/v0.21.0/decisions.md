# v0.21.0 decisions

## D1 — Scope (Jev, no consensus; most reversible option adopted)

- Spec id `inonu-v021-small-gaps`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) a ready queue plus a `tools` allowlist for the worker agent; (b) the ready queue only; (c) the allowlist only; (d) ledger post-write digests with a drift status.
- Result: `sem_consenso`. The leader was (a), mean 0.73 over three rounds with agreement 1.0, but with a rail probability of 0.40 against a 0.2 limit. Rail probabilities of the alternatives: b 0.10, c 0.16, d 0.92 (the ledger change touches the host-configuration bookkeeping).
- Resolution, per the rule for a missing consensus: the most reversible, lowest-risk option. That is (b), a new read-only command. The `tools` allowlist is deferred, not rejected: it would change what the owner's installed worker agent may do the next time `bundle apply` runs, and the combination was what raised the rail probability. Recorded as `sem-consenso`.
- The receipt is a recommendation and grants no authorization.

## D2 — Why a query and not a stored flag

Beads keeps a materialized readiness flag that is recomputed incrementally. Inonu's decision graph already stores the dependency list and a status per decision, so the answer is a pure function of the current state. Computing it on read needs no schema change and cannot drift.

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
