# v0.0.17 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 `check --ref`, tests, docs | none | `inonu_harness/cli.py`, `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json`, version strings in `tests/`, new `tests/test_check_ref.py`, `CHANGELOG.md`, `README.md`, `docs/plugin.md`, `skills/inonu-harness/SKILL.md` | A1: R1–R4 at the CLI seam; A2: R5 tests pass; A3: R6 docs accurate. |
| T02 Independent review | T01 | read-only | A4: a reviewer that did not implement tries to break the export, the isolation and the cleanup. |
| T03 Convergence | T02 | `checkpoint.md` (coordinator) | A5: full suite, `check` and `docs lint` exit 0; every P1/P2 resolved. |
