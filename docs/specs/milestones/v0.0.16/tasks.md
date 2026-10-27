# v0.0.16 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Lint, architecture test | none | new `inonu_harness/docs_lint.py`, `inonu_harness/cli.py`, `inonu_harness/__init__.py`, `pyproject.toml`, new `tests/test_docs_lint.py`, new `tests/test_architecture.py`, version strings in `tests/` | A1: R1–R7 at the CLI seam; A2: this repository passes its own lint and the architecture test. |
| T02 Docs | none | `CHANGELOG.md`, `README.md`, `docs/architecture.md`, `skills/inonu-harness/SKILL.md` | A3: R8 accurate, limits and non-claims stated. |
| T03 Independent review | T01, T02 | read-only | A4: a reviewer that did not implement tries to break the lint and the architecture test. |
| T04 Convergence | T03 | `checkpoint.md` (coordinator) | A5: full suite and `check` exit 0; every P1/P2 resolved. |
