# v0.0.10 checkpoint — 2026-10-26

Status: implementation converged locally. Nothing is committed or pushed. This milestone does not complete the broader single-install Harness objective.

## Flow

- Research: one dynamic workflow, 6 parallel Haiku sweeps (harness, loop and graph repos; vendor docs; engineers; internal audit) plus a Haiku synthesis, recorded in [research.md](research.md). The Opus coordinator only orchestrated (D2).
- Scope: Jev consensus `a_check_plan` ([decisions.md](decisions.md), D1).
- Implementation: T01 (code) and T02 (docs) ran in parallel on Haiku workers with disjoint ownership; T03 was an independent Haiku review that did not implement.

## Review disposition

- T03 P1: the spec required `unittest discover -s tests -t .`, which fails on this checkout because `tests/` is not a package. The fault was in the spec, not the worker. Fixed by using `discover -s tests`, the command CI already runs, and by updating R1 and removing the test helper's `__init__.py` workaround.
- Coordinator fixes: moved the `docs/hosts.md` bundle section out of the installer instructions it had split, and added a note that the stop-hook snippet would run the full suite on every Stop event; corrected a grammar slip in the CHANGELOG.
- No open P1/P2 findings.

## Verification evidence

- `python -m unittest discover -s tests`: exit 0, 108 tests, 3 skipped (POSIX-only, Windows host).
- `python -m inonu_harness check` on this checkout: exit 0, `passed: true`, compile 0, tests 0.
- `bundle plan --home <empty temp dir>`: exit 0; the temp home stayed empty; 10 items (codex: skill + 3 MCP; claude: skill, worker-agent, stop-hook + 3 MCP); no personal path in the output.
- `scripts/inonu.py --version`: `inonu-harness 0.0.10`. `git diff --check`: exit 0.
- Local profiles reapplied with `configure_hosts.py --apply` (both hosts `updated`); a repeat preview reports `unchanged`. That does not prove a running session reloaded the skill.

## Next

v0.0.11 (`bundle apply`/`remove`/`status` with ownership hashes) writes into host configuration: hooks, MCP registry and agent files. It needs the owner's specific authorization before implementation. Until then, independent research-only or read-only work can continue (for example the evaluation fixtures planned for v0.0.13).
