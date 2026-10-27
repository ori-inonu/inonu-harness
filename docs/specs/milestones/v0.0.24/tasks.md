# v0.0.24 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 version audit, skill size rules, tests, docs | none | new `inonu_harness/versions.py`, `inonu_harness/docs_lint.py`, `inonu_harness/cli.py` (the `_run_steps` function only), the three manifests, `tests/test_check_bundle.py`, `tests/test_host_profiles.py`, new `tests/test_versions.py`, `tests/test_docs_lint.py`, `CHANGELOG.md`, `README.md`, `docs/plugin.md`, `skills/inonu-harness/SKILL.md` | A1: R1–R5; A2: R6 tests pass; A3: R7 docs accurate. |
| T04 version scheme, test gaps from the first review, docs | T01 | `inonu_harness/versions.py`, `inonu_harness/cli.py` (the `version` subcommand and the `--scheme` flag of the `versions` step), `tests/test_versions.py`, `tests/test_docs_lint.py`, new `docs/versioning.md`, `AGENTS.md`, `docs/sdd-workflow.md`, `CHANGELOG.md`, `README.md`, `skills/inonu-harness/SKILL.md` | A6: R8–R13; tests pass. |
| T02 Independent review | T01, T04 | read-only | A4: a reviewer that did not implement tries to make the audit pass on a mismatch or fail on a match, make `check` skip the step, make the lint miss an oversized skill or read outside the root. |
| T03 Convergence | T02 | `checkpoint.md` (coordinator) | A5: full suite, `check` and `docs lint` exit 0; every P1/P2 resolved. |
