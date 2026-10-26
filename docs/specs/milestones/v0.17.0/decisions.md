# v0.17.0 decisions

## D1 — Scope (Jev, no consensus; most reversible option adopted)

- Spec id `inonu-v017-release-gate`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) `check --ref` plus a three-OS CI that runs it; (b) `check --ref` only; (c) the CI matrix only; (d) a separate `release` command that tags and builds.
- Result: `sem_consenso`. The leader was (a), but with a mean that fell from 0.78 to 0.43 across rounds and a rail probability of 0.66 against a 0.2 limit; (b) was a close second (mean 0.41, rail 0.04). The CI matrix alone scored a rail of 0.64 and the release command 1.00. The judge's concern is consistent with changing the workflow that the first push would run on three operating systems with code that has so far run on one.
- Resolution, per the rule for a missing consensus: the most reversible, lowest-risk option, (b). Recorded as `sem-consenso`. The CI change is deferred rather than rejected: the workflow is a public, outward-facing file that runs on every push.
- The receipt is a recommendation and grants no authorization.

## D2 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
