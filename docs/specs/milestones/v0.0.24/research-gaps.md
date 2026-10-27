# v0.0.24 research: gaps that survive verification

Date: 2026-10-26. Inputs: [research-official-docs.md](research-official-docs.md) (six groups, 84 practices from official documentation and leading engineers) and [research-repositories.md](research-repositories.md) (six star-ranked repositories, 84 mechanisms pinned to commits). Every reader and verifier was a Haiku-class model; no human has read the sources.

The readers compared each practice with a short description of Inonu, so some of the gaps they proposed were already built. The coordinator checked every gap below against Inonu's own code before listing it. Where the check could not be made, the row says so.

## Readers' gaps that Inonu already covers

- An iteration cap in the loop runner: `max_iterations` is required, capped at 1000 and reported as a stop status; there are also `iteration_timeout_seconds`, `total_timeout_seconds` and `stagnation_iterations` (`inonu_harness/loop.py`). Proposed by five groups.
- Repeat and no-progress detection: the loop hashes the failing-check signature together with the working tree and counts a streak of unchanged states. Proposed by two sources.
- Re-approval of the Stop hook config when it changes: `hook trust` records a SHA-256 of the config per resolved path, and a changed config runs no check (`inonu_harness/hook.py`).
- A reason returned to the agent on a block: the failing check's output goes to stderr with exit 2. A JSON decision schema and input rewriting are not built, and are not needed by anything here.
- A consecutive-block cap on the Stop path: `max_consecutive_blocks`, 1 to 20.
- A per-iteration record of the loop: one JSONL record per iteration with the step and check exit codes.

## Gaps confirmed against Inonu's code

- **G8, P1: protect the verifier from the step.** The loop runs `step`, then every check, and reports `verified_done` when all checks pass. Nothing stops the step from editing the files the checks read, which is how an agent makes a failing check pass. Support in the verified sources is for the principle, not for the mechanism: Anthropic (AN-02, AN-03) says completion must rest on external checks and that the evaluator must be separate from the generator, and Huntley (`huntley-backpressure`, `huntley-no-placeholders`) says deterministic checks reject bad output and that agents must be told not to cheat with stubs. No source read says "hash the check files"; that mechanism is the coordinator's inference from the independence principle, and no page was found that names editing the tests as a failure mode. In `LoopSpec` there is no protected-path field (`_SPEC_KEYS` is `step`, `checks`, `limits`, `log`, `cwd`).
- **G9, P2: version drift across manifests.** superpowers lists twelve manifest version fields in one file and audits them in its bump script. Inonu keeps the version in `inonu_harness/__init__.py`, `pyproject.toml` and `.claude-plugin/plugin.json`, and six hard-coded assertions in two test files (`tests/test_check_bundle.py`, `tests/test_host_profiles.py`); a release needs nine edits, and the 0.0.15 review found `plugin.json` not bumped. No `check` step compares the three manifests; only the tests, through their hard-coded strings, notice a mismatch.
- **G10, P2: size budget for `SKILL.md`.** superpowers enforces a 20,000-byte budget with a deterministic test. `inonu_harness/docs_lint.py` covers only `AGENTS.md`, `AGENTS.override.md` and `CLAUDE.md` (the word `SKILL` does not occur in it), so a skill can grow without a failing check. The Inonu skill is 7,601 bytes in 33 very long lines.
- **G13, P3: token formats in the Jev adapter.** hermes-agent scrubs text before it leaves for a remote provider. `jev spec` now scans documents for common token formats, but a hand-written spec passed to `JevAdapter` is checked only against the narrower `_SENSITIVE` list in `jev.py`.

## Gaps that need an owner decision or more design

- **G6, P2, fenced: a `tools` allowlist and turn limit for `inonu-worker`.** Confirmed again against the Claude Code subagent documentation (`agents/inonu-worker.md` sets only the model). It changes the agent file in the owner's configuration on the next `bundle apply`.
- **G14, P2: a deterministic gate before a tool runs (allow, ask, deny).** Anthropic hooks, OpenAI guardrails and the Strands before-tool-call event all describe it, and Inonu has none (`PreToolUse` appears only as an event name in `doctor.py`). Building the evaluator is possible; installing it is a new kind of hook in the owner's settings and needs its own authorization.
- **G15, P2, fenced: link loop iterations to Decision Graph revisions** (Horthy on unified state, rea on stable ids for unknowns). `loop.py` does not use the graph, and linking needs a schema change.
- **G16, P3: a paired with-and-without-harness evaluation.** `docs/benchmark-plan.md` has the unassisted baseline row, and no paired run has been executed. Running it means real model calls, which is a paid service.
- **G12, P3: a real-client lane for the Stop hook and the plugin** (rea). Inonu has never been run by a real Claude session blocking on the hook, and `claude plugin validate` has not been run: the `claude` command is not on this machine's path. The owner can run it.
- **G11, P3: a verification record keyed to the tree digest** that the Stop hook could consult (claw-code, hermes-agent). The loop already computes a tree digest; whether its summary carries it was not checked.

## Order

G8, G9 and G10 are deterministic, need no new authorization and have independent support, so they come first: G9 and G10 as a small release-hygiene milestone, G8 as its own milestone with a brief for the Jev judge. G13 follows. G6, G14, G15, G16 and G12 wait for the owner.
