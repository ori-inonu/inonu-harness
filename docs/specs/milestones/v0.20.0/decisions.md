# v0.20.0 decisions

## D1 — Scope (Jev, consensus)

- Spec id `inonu-v020-hook`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted. Two earlier, longer specs for this decision returned `internal error` from `consensus_plan` (nothing was sent); the shorter spec below worked. The failure is recorded here and the decision was not made without the judge.
- Options: (a) a real `hook stop` command registered by the bundle; (b) a flag that makes `check` exit 2 and registering that; (c) leave it and document that the hook cannot block.
- Result: `consenso`, leader `a_hook_entry_point`, mean 0.76, agreement 1.0, margin ≥ 0.56 over two rounds. Rail probabilities: a 0.18, b 0.52, c 0.86.
- Adopted as engineering scope. It grants no authorization to install the hook.

## D2 — Trust by hash

A verifier config comes from the repository being worked on, and the hook is global. Running it unconditionally would let any cloned repository run commands on every Stop. The design therefore requires an explicit, reviewable grant bound to the config's SHA-256, refuses on any change, and keeps the grant in a file only the owner's command writes. The pattern (a user grant keyed on a content digest, refusal on drift) comes from the source-level reading of spec-kit; the implementation is Inonu's own.

## D3 — Fail-open on infrastructure, fail-closed on findings

A broken or untrusted config exits 1 (a non-blocking error the user sees) so it can never trap an agent; a failing check exits 2. The block counter ends blocking after a configured maximum even when a check can never pass. Telemetry-style behavior (logging) is out of scope.

## D4 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
