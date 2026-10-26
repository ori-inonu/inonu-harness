# v0.22.0 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 ownership in `bundle status`, tests, docs | none | `inonu_harness/bundle_apply.py`, `inonu_harness/cli.py` (the status call only), `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json`, version strings in `tests/`, new `tests/test_bundle_ownership.py`, `CHANGELOG.md`, `README.md`, `docs/hosts.md`, `skills/inonu-harness/SKILL.md` | A1: R1–R5; A2: R6 tests pass; A3: R7 docs accurate. |
| T02 Independent review | T01 | read-only | A4: a reviewer that did not implement tries to make a changed item look `ours`, make status write, leak a path or secret, or crash on a hostile ledger. |
| T03 Convergence | T02 | `checkpoint.md` (coordinator) | A5: full suite, `check` and `docs lint` exit 0; every P1/P2 resolved. |
