# v0.0.20 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Hook command, trust, tests | none | new `inonu_harness/hook.py`, `inonu_harness/cli.py`, `inonu_harness/loop.py` only to expose a reusable process-tree helper if needed, `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json`, version strings in `tests/`, new `tests/test_hook.py` | A1: R1–R7; A2: the R9 hook, trust and end-to-end tests pass. |
| T02 Bundle registration and docs | T01 | `inonu_harness/bundle.py`, `inonu_harness/bundle_apply.py`, `tests/test_bundle_apply.py`, `tests/test_bundle_status.py`, `tests/test_check_bundle.py`, new `docs/hook.md`, `CHANGELOG.md`, `README.md`, `docs/plugin.md`, `docs/hosts.md`, `skills/inonu-harness/SKILL.md` | A3: R8 and the R9 bundle tests pass; A4: R10 docs accurate. |
| T03 Independent review | T02 | read-only | A5: a reviewer that did not implement tries to make the hook run an untrusted config, trap an agent, leak output, or break the bundle. |
| T04 Convergence | T03 | `checkpoint.md` (coordinator) | A6: full suite, `check` and `docs lint` exit 0; every P1/P2 resolved. |
