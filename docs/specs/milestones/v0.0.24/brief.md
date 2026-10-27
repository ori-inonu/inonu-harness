# v0.0.24 decision brief

Context for the scope decision, written before the spec so that it does not state the answer. The Jev judge sees only the decision object, so this brief is sent as its `facts`.

## Problem

- A research round read 12 primary sources and 6 star-ranked repositories and found gaps in Inonu Harness that its own code does not cover. Three are deterministic and need no new authorization. Only one milestone can be built at a time.
- Gap A, release version drift: the version is written in 3 manifests (`inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json`) and in 6 hard-coded test assertions. A release needs 9 edits. The 0.0.15 review found `plugin.json` not bumped. No `check` step compares the manifests.
- Gap B, skill size: `docs lint` covers `AGENTS.md`, `AGENTS.override.md` and `CLAUDE.md` only. A `SKILL.md` can grow without a failing check. superpowers (305k stars) enforces a 20,000-byte budget with a test. The Inonu skill is 7,601 bytes.
- Gap C, verifier integrity in the loop runner: the loop runs a step, then every check, and reports `verified_done` when all pass. Nothing stops the step from editing the files the checks read. No source read names this failure; the mechanism is an inference from the principle that the evaluator must be independent of the generator (Anthropic).
- Gap D, Jev adapter token formats: `jev spec` scans documents for common token formats, but a hand-written spec passed to the adapter is checked only against the narrower patterns in `jev.py`.

## What the code does today

- `check` compiles the package and runs the test suite; `check --ref` does the same on an exported commit.
- `LoopSpec` accepts `step`, `checks`, `limits`, `log` and `cwd`. The loop already has an iteration cap, a stagnation streak over the failing-check signature and the working-tree hash, and a per-iteration JSONL record.
- Each gap is small: A and B touch checks and lint only; C adds a spec field, a digest before and after the step and a new stop status; D moves a pattern list.

## Constraints

- No commit or push without the owner's authorization. No new dependency. No schema or data migration. No change to what `bundle apply` writes into the owner's configuration.
- Every change must be proven by deterministic tests and an independent review. Existing output keeps its meaning.
