# v0.13.0 — Regression gate for `baseline compare`

Research ([v0.10.0 research](../v0.10.0/research.md), section 4–6) shows vendors and engineers converge on deterministic, exit-code gates and on alerting when a metric drifts from its baseline. `baseline compare` already emits a per-metric `delta` but never decides anything and always exits 0. This milestone adds an opt-in gate. It touches no host configuration. The design choice is recorded in [decisions.md](decisions.md).

## Requirements

- R1 `python -m inonu_harness baseline compare BEFORE AFTER [--max-regression R]` (and the same flag on the standalone `inonu_harness.baseline` entry point). `R` is a finite number ≥ 0 (`0.10` allows a 10% increase). An invalid `R` exits 2. Without the flag nothing changes: no `gate` key, and the exit code is as before.
- R2 With the flag, the output is the existing comparison JSON plus a `gate` object: `{"max_regression": R, "status": "pass"|"fail"|"incomparable", "regressions": [{"metric", "before", "after", "reason"}], "skipped": [{"metric", "reason"}]}`. Exit 0 for `pass`, 1 for `fail`, 2 for `incomparable`. Results with an unsupported schema, unreadable files, duplicate JSON keys (checked only when the flag is given) or an invalid `R` are invalid input and also exit 2, without a `gate` object.
- R3 What counts as a regression, evaluated only on metrics whose comparison status is `compared`:
  - `acceptance`: each criterion id with `passed: true` before that is missing or `passed: false` after is a regression named `acceptance:<id>`. No tolerance applies.
  - `failures`, `blocks`, `tool_calls` (list lengths) and `input_tokens`, `output_tokens`, `cost_usd` (numbers): a regression when `after > before * (1 + R)`, or when `before` is 0 and `after` is greater than 0. The comparison uses exact decimal arithmetic, so a rise of exactly `R` passes and integers above 2^53 compare exactly.
  - Any regression found makes the status `fail`. Otherwise, a gated metric whose measurement source changed between the runs (`source_incompatible`) makes the status `incomparable`, because the gate cannot tell whether it regressed.
- R4 Skipped, never counted as pass or regression: any metric that is not `compared` (the `skipped` entry carries its reason, for example `value_unavailable`), and metrics the gate does not judge: `elapsed_seconds` (wall-clock, nondeterministic), `recoveries`, `runtime`, `model`, `component_versions`. The `skipped` list names every metric that was not judged. Unavailable values are never filled in.
- R5 The gate is a pure function `gate_comparison(before, after, comparison, max_regression)` in `inonu_harness/baseline.py`, reused by both entry points. Deterministic output; no clock, network or randomness.
- R6 Tests cover:
  - identical runs pass;
  - an acceptance criterion that passed before and fails or disappears after fails;
  - a tokens increase beyond the ratio fails and one within it passes;
  - 0 → positive fails;
  - unavailable tokens or cost are skipped and do not fail;
  - a task/config mismatch exits 2 and the status is `incomparable`;
  - an `elapsed_seconds` blow-up alone passes;
  - without the flag a regression still exits 0 and no `gate` key appears;
  - a negative, NaN or infinite `R` exits 2;
  - the CLI path and the standalone path agree.
- R7 Docs: CHANGELOG 0.13.0, README, `docs/benchmark-plan.md` (short, Portuguese), source skill bullet. Version 0.13.0 in `__init__.py`, `pyproject.toml` and test expectations. The docs state that the gate compares two saved local measurements; it does not establish agent quality or productivity.

## Out of scope

Labeled-result fixtures and judge precision/recall (no automated judge exists in the repository yet), the loop runner (v0.14.0), any host configuration.
