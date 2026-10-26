# v0.11.0 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Status slice | none | `inonu_harness/bundle.py`, `inonu_harness/cli.py`, `inonu_harness/__init__.py`, `pyproject.toml`, new `tests/test_bundle_status.py`, version strings in `tests/`, `CHANGELOG.md`, `README.md`, `docs/hosts.md`, `skills/inonu-harness/SKILL.md` | A1: R1–R3 behave at the CLI seam; A2: R4 tests pass; A3: R5 docs accurate. |
| T02 Review | T01 | read-only | A4: independent reviewer checks R1–R5, read-only guarantee and privacy; findings or explicit none. |
| T03 Convergence | T02 | `checkpoint.md` (coordinator) | A5: full suite and `check` exit 0; findings resolved. |
