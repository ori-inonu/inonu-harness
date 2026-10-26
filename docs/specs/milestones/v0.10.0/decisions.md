# v0.10.0 decisions

## D1 — Milestone scope (Jev, consensus)

- Spec id `inonu-v010-scope`, planned with `consensus_plan` then run with `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) `check` + read-only `bundle plan`; (b) `check` + install a Haiku worker agent; (c) both; (d) `check` only.
- Result: `consenso`, leader `a_check_plan`, mean 0.73–0.76, agreement 1.0, margin ≥ 0.52 over two rounds. Rail probability: a 0.02, b 0.32, c 0.64 (writing into user host directories was judged closer to the fence).
- Status: recommendation adopted by the coordinator as engineering scope. It grants no authorization for host configuration.

## D2 — Worker model routing (owner instruction)

The owner instructed on 2026-10-26 that dynamic-workflow workers run on Haiku 5.5 and Opus 5.5 only orchestrates. Claude Code subagent frontmatter supports `model: haiku` ([docs](https://code.claude.com/docs/en/sub-agents)). R3 ships that definition as a source file; installing it is deferred.

## Open

- Applying hooks, MCP registrations and agent files (v0.11.0) needs the owner's specific authorization for global host configuration.
- Whether Haiku is adequate for every SDD worker role is not evaluated.
