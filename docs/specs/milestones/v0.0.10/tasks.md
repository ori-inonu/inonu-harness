# v0.0.10 plan and tasks

Phases: F01 implementation (T01 ∥ T02) → F02 independent review (T03) → F03 convergence (T04, coordinator).

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Code slice | none | `inonu_harness/cli.py`, new `inonu_harness/bundle.py`, `inonu_harness/__init__.py`, `pyproject.toml`, `agents/inonu-worker.md`, `tests/test_check_bundle.py`, version strings in `tests/test_host_profiles.py` | A1: R1–R4 behave at the CLI seam with tests; A2: R6 temp-root and isolated-home tests pass. |
| T02 Docs | none | `CHANGELOG.md`, `README.md`, `docs/hosts.md`, `docs/sdd-workflow.md`, `skills/inonu-harness/SKILL.md` | A3: R5 accurate, limits stated, no private paths or superiority claims. |
| T03 Review | T01, T02 | read-only | A4: independent reviewer (did not implement) checks R1–R6 fidelity, safety and privacy; findings or explicit none. |
| T04 Convergence | T03 | `checkpoint.md` | A5: full suite and `check` exit 0; findings resolved; checkpoint records evidence. |

Workers run on Haiku (D2), own one task, do not delegate, call Jev, touch host configuration or mutate Git.
