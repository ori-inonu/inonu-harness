# v0.0.25 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 `milestones.py` with `new` and `check`, the CLI subcommand, the `check` step, tests | none | new `inonu_harness/milestones.py`, `inonu_harness/cli.py` (the `milestone` subcommand and `_run_steps` only), new `tests/test_milestones.py`, `tests/test_check_ref.py` if its fixtures need it | A1: R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11; A2: R12 tests pass. |
| T02 Docs, skill, versions | T01 | `docs/milestones.md`, `README.md`, `AGENTS.md`, `docs/sdd-workflow.md`, `docs/versioning.md`, `CHANGELOG.md`, `skills/inonu-harness/SKILL.md`, the three manifests | A3: R13. |
| T03 Independent review | T01, T02 | read-only | A4: a reviewer that did not implement tries to make the check pass on an unclaimed requirement or fail on a covered one, make `new` overwrite, escape the root or leave a partial folder, and checks the docs against the code. |
| T04 Convergence | T03 | `checkpoint.md` (coordinator) | A5: full suite, `check` and `docs lint` exit 0; every P1/P2 resolved. |
