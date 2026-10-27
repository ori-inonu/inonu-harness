# v0.0.21 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 `decisions ready`, tests, docs | none | `inonu_harness/cli.py`, `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json`, version strings in `tests/`, new `tests/test_decisions_ready.py`, `CHANGELOG.md`, `README.md`, `docs/sdd-workflow.md`, `skills/inonu-harness/SKILL.md` | A1: R1–R5; A2: R6 tests pass; A3: R7 docs accurate. |
| T02 Independent review | T01 | read-only | A4: a reviewer that did not implement tries to make a wrong decision appear ready, break the read-only guarantee or leak a path. |
| T03 Convergence | T02 | `checkpoint.md` (coordinator) | A5: full suite, `check` and `docs lint` exit 0; every P1/P2 resolved. |
