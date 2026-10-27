# v0.0.23 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 `jev spec`, tests, docs | none | new `inonu_harness/jev_context.py`, `inonu_harness/cli.py` (the `jev` subcommand only), `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json`, version strings in `tests/`, new `tests/test_jev_context.py`, `CHANGELOG.md`, `README.md`, `docs/sdd-workflow.md`, `docs/integrations.md`, `skills/inonu-harness/SKILL.md` | A1: R1–R8; A2: R9 tests pass; A3: R10 docs accurate. |
| T02 Independent review | T01 | read-only | A4: a reviewer that did not implement tries to drop or alter document text, leak a secret or a path, escape the root, exceed a Jev limit without an error, or make the output differ between runs. |
| T03 Convergence | T02 | `checkpoint.md` (coordinator) | A5: full suite, `check` and `docs lint` exit 0; every P1/P2 resolved. |
