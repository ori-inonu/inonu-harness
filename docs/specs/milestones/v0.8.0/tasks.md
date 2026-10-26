# v0.8.0 finite tasks

Each worker owns one ticket, may not delegate or call Jev, and stops after its acceptance evidence is returned. Stop protected actions as blocked; report unexpected shared-file conflicts to the coordinator. No commit/push.

| Task | Dependencies | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Library vertical slice | none | `inonu_harness/sdd_audit.py`, `tests/test_sdd_audit.py`, `fixtures/sdd_audit/**`, fixture-only `.gitattributes` rule if needed | A1: red-to-green public audit behavior covers R1-R4, with five cases and meaningful negative mutations; A2: file safety, exact-byte hashes and deterministic sanitized output are proven by tests. |
| T02 CLI and baseline vertical slice | T01 | `inonu_harness/cli.py`, `tests/test_sdd_audit_cli.py`, `README.md`, `docs/sdd-workflow.md`, `docs/architecture.md`, `docs/benchmark-plan.md` | A3: R5 CLI codes/default root/override/invalid input pass through public main; A4: R6 computed baseline outcomes/null metrics and R7 usage/limits documented; existing commands pass. |
| T03 Standards review | T02 | read-only feature diff | A5: independent review of safety, validation, compatibility and necessity with actionable findings or explicit no-findings. |
| T04 Specification review | T02 | read-only feature diff/spec | A6: independent R1-R7 fidelity review with evidence and remaining gaps. |
| T05 Self-audit and convergence | T03,T04 | `checkpoint.md`, `validation.json`, `audit.json` in this milestone | A7: actual focused/full test counts and diff check, no unresolved P1/P2; A8: self-audit binds spec/tasks/validation artifacts and CLI passes while limits and preserved work are recorded. |

The coordinator verifies actual diffs and deterministic checks; child assertions alone cannot close a task. Repairs reuse the original owner and are re-reviewed where material.
