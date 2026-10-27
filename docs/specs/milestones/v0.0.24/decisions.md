# v0.0.24 decisions

## D1 — Scope (Jev, consensus)

- Spec id `inonu-v024-scope`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted. The facts were built by `jev spec` from [brief.md](brief.md) and `AGENTS.md`: 21 facts, 4,088 characters, the first run of the command on a real decision. The brief was written before the spec and names the gaps and the constraints without stating the answer.
- Options: (a) release hygiene, gaps A and B together; (b) loop verifier integrity, gap C alone; (c) A, B and C in one milestone; (d) adapter token formats, gap D alone; (e) stop building.
- Result: `consenso`, leader (a), mean 0.64 in round 1 and 0.57 in round 2, agreement 1.0, margin 0.44 then 0.32, rail probability 0.02. Runner-up (b) 0.20 and 0.25, rail 0.07; (c) 0.01 with rail 0.16; (d) 0.11; (e) 0.03. 11 calls, 23,146 input tokens. The judge stopped after two rounds because the result was stable.
- The receipt is a recommendation and grants no authorization. Compare the two v0.0.22 runs ([v0.0.22 decisions](../v0.0.22/decisions.md) D1), which ended without consensus: there the rail probability of the leader was 0.24 and 0.67. Here the brief states what the code does and each rail can be checked against it, and the rail probability fell to 0.02. One run each does not prove the cause, but it is the pattern D4 of 0.0.22 predicted.
- Gaps C and D stay open. C (the runner-up) is the next candidate; it needs its own brief because it changes the loop spec.

## D4 — The version scheme (set by the owner)

The owner wrote, in two messages during this milestone: the project is at v0.24.0 and should be v0.0.24, with all other versions renumbered as references; the Harness works with a scheme that starts at v0.0.1, goes to v0.0.99 before v0.1.0, with at most two digits, so that 99 milestones of implementation and improvement pass before v0.1.0 and the project is already well evolved at v1.0.0; and this must work the same for all projects, globally, as a concept of the Harness for version and milestone management. No Jev call was made: the owner decided it.

- Reading of the scheme: milestone n is `0.(n // 100).(n % 100)`, so v0.1.0 is the 100th milestone. The owner named the first 99 patches; the same two-digit limit is applied to the minor so that the scheme is closed under the same rule, and v1.0.0 stays the owner's decision. That extension to the minor is the coordinator's reading and is recorded here so that the owner can change it.
- Renumbering: the 24 milestones v0.N.0 for N from 1 to 24 became v0.0.N, as directory names under `docs/specs/milestones` and as references in docs, tests, manifests and fixtures. Two test values that are not Inonu versions were left alone: the Jev server version `0.1.0` in the adapter tests, and external tool versions such as Headroom 0.41.0. Git commit messages, Jev spec ids such as `inonu-v021-small-gaps` and the receipts keep the numbers they were written with; the mapping table in `docs/versioning.md` decodes them. Nothing in the git history was rewritten.
- Enforcement: the scheme is a deterministic check (`versions --scheme`) in `check`, not only text, and the installed skill carries the rule so that other projects get it.

## D2 — Why limits come from two sources

`SKILL_MAX_BYTES` follows superpowers (a skill of 20,000 bytes or more fails its size test, read at a pinned commit and re-read by a second model). `SKILL_MAX_LINES` follows the Claude Code skills documentation (under 500 lines), also read twice. Both are starting points and not a measured optimum; the constants make them easy to change.

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
