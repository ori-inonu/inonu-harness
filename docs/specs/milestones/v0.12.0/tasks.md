# v0.12.0 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Apply/remove code and tests | none | `inonu_harness/bundle_apply.py`, `inonu_harness/cli.py`, `inonu_harness/bundle.py`, version strings, `tests/test_bundle_apply.py` | A1: R1–R8 at the CLI seam; A2: R7 tests pass; A3: R9–R14 (added after review) pass. |
| T02 Docs | none | `CHANGELOG.md`, `README.md`, `docs/hosts.md`, `skills/inonu-harness/SKILL.md` | A4: commands, ledger, backups, rollback and limits stated accurately. |
| T03 Independent reviews | T01, T02 | read-only | A5: safety/data-loss review and spec-fidelity review, both by reviewers that did not implement; every P1/P2 resolved. |
| T04 Re-reviews | T03 fixes | read-only | A6: fresh adversarial reviewers confirm the fixes and find nothing P1/P2 open. |
| T05 Apply on the owner's host | T04 | the owner's Claude and Codex configuration (authorized 2026-10-26) | A7: preview first, then `--apply`; `bundle status` reflects it; `remove` reverses it. |

Workers ran on Haiku (owner instruction); the coordinator made the review fixes.
