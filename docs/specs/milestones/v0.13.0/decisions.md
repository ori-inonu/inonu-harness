# v0.13.0 decisions

## D1 — Gate design (Jev, no consensus; most reversible option adopted)

- Spec id `inonu-v013-gate-design`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) strict acceptance plus a ratio on counts, tokens and cost, wall-clock excluded; (b) a plus `elapsed_seconds`; (c) acceptance only; (d) one ratio on everything with no strict acceptance rule.
- Result: `sem_consenso`. The leader was (a), mean 0.84, agreement 1.0, margin 0.71 over three rounds. It was held back only by its rail probability (0.33 against a 0.2 limit); (d) scored 0.98 on rail probability and ~0 on preference.
- Resolution, per the rule for a missing consensus: the most reversible, lowest-risk option. That is (a) as an opt-in gate: without `--max-regression` the command is unchanged, so adopting it changes nothing for existing callers. Recorded as `sem-consenso`; adoption of the exact thresholds stays revisable.
- The receipt is a recommendation and grants no authorization.

## D2 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
