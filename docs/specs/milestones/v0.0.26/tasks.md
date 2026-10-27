# v0.0.26 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 `milestone close`, the index and the new check rules, with tests | none | `inonu_harness/milestones.py`, `inonu_harness/cli.py` only if the subcommand needs a line, `tests/test_milestones.py` or a new `tests/test_milestone_close.py` | A1: R1, R2, R3, R4, R5, R6, R7, R8; A2: R9 tests pass. |
| T02 Docs, skill, versions | T01 | `docs/milestones.md`, `docs/versioning.md`, `README.md`, `docs/sdd-workflow.md`, `CHANGELOG.md`, `skills/inonu-harness/SKILL.md`, the three manifests | A3: R10. |
| T03 Independent review | T01, T02 | read-only | A4: a reviewer that did not implement tries to close what should be refused, refuse what should close, corrupt or lose an index entry, write outside the root, and checks the docs against the code. |
| T04 Convergence and the repository's own close | T03 | `checkpoint.md` (coordinator), `docs/specs/milestones/MILESTONES.md` through the command | A5: full suite, `check` and `docs lint` exit 0; every P1/P2 resolved; v0.0.25 is closed with the command (R11). |
