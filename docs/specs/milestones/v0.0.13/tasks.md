# v0.0.13 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Gate and tests | none | `inonu_harness/baseline.py`, `inonu_harness/cli.py`, `inonu_harness/__init__.py`, `pyproject.toml`, new `tests/test_baseline_gate.py`, version strings in `tests/`, `CHANGELOG.md`, `README.md`, `docs/benchmark-plan.md`, `skills/inonu-harness/SKILL.md` | A1: R1–R5 at the CLI seam; A2: R6 tests pass; A3: R7 docs accurate. |
| T02 Independent review | T01 | read-only | A4: a reviewer that did not implement checks R1–R7 and tries to break the gate. |
| T03 Convergence | T02 | `checkpoint.md` (coordinator) | A5: full suite and `check` exit 0; every P1/P2 resolved. |
