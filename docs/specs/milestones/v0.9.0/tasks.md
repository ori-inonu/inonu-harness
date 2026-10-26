# v0.9.0 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Native profile vertical slice | none | `scripts/inonu.py`, `scripts/configure_hosts.py`, `inonu_harness/host_profiles.py` if useful, `inonu_harness/cli.py`, `inonu_harness/__init__.py`, `skills/inonu-harness/**`, `tests/test_host_profiles.py` | A1: R1-R4 work at public seams with meaningful tests; A2: isolated preview/idempotence/conflict preservation and version0.9.0 verified, no actual user files touched. |
| T02 Changelog and setup guide | T01 | `CHANGELOG.md`, `docs/hosts.md`, `README.md` | A3: R5 accurately distinguishes shipped features/proposals; A4: portable setup/limits and no private paths or unsupported superiority claims. |
| T03 Standards review | T02 | read-only | A5: independently inspect public changes, safety/quoting/idempotence and privacy; actionable findings or explicit no-findings. |
| T04 Spec review | T02 | read-only | A6: independently review R1-R6 fidelity; R7/R8 remain coordinator delivery. |
| T05 Preparation convergence | T03,T04 | this milestone's `checkpoint.md` | A7: required full/focused checks and native skill validation pass with actual skip counts; A8: no unresolved P1/P2, truthful release-ready state and delivery next steps. |

Workers own one bounded task and may not delegate or invoke Jev. They do not touch real host configuration, credentials or Git mutations. Coordinator owns R7 host application and R8 public commit/push after preparation.
