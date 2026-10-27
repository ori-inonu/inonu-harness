# v0.0.19 decisions

## D1 — Policy (Jev, no consensus; most reversible option adopted)

- Spec id `inonu-v019-secret-scan`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) refuse by default with an explicit override; (b) warn on stderr and never block; (c) an opt-in refusal flag; (d) redact matches in the output.
- Result: `sem_consenso`. The leader was (c), mean 0.46 in the last round with a margin of 0.13 and a rail probability of 0.25 against a 0.2 limit. The alternatives scored rail probabilities of 0.63 (a), 0.62 (b) and 0.80 (d): changing the default exit behavior of existing commands, or silently altering printed text, was seen as riskier than an opt-in check.
- Resolution, per the rule for a missing consensus: the most reversible, lowest-risk option, (c). Recorded as `sem-consenso`. Because the guard is off by default, existing callers are unaffected; making it the default is a later, separately decided change.
- The receipt is a recommendation and grants no authorization.

## D2 — Why not scan arbitrary files

The packet and context commands are the points where free text is handed to an agent. A general scanner would need decisions about file types, binary content and entropy heuristics, and would suggest more coverage than a short list of formats provides.

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
