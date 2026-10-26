# v0.14.0 decisions

## D1 — Loop runner scope (Jev, consensus)

- Spec id `inonu-v014-loop-scope`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) runner with a baseline check, runner-owned `passes` and a JSONL log; (b) single verifier and an iteration cap only; (c) runner plus resume state and a generated Stop hook; (d) Stop-hook generator only.
- Result: `consenso`, leader `a_runner_with_ledger`, mean 0.98, agreement 1.0, margin ≥ 0.97 over two rounds. Rail probability: a 0.10, b 0.53, c 0.71, d 0.59 (resume and hook generation sit closest to the fenced host-configuration writes).
- Adopted as engineering scope. It grants no authorization.

## D2 — Research gaps stay visible

The OpenAI primary page remained unreadable (HTTP 403). The design rests on the Anthropic and Claude Code documentation and on the code of two Ralph variants; stagnation thresholds are explicitly unvalidated starting points ([research-verify.md](research-verify.md)).

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
