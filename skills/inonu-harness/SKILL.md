---
name: inonu-harness
description: Use Inonu Harness for local environment diagnosis, offline baseline runs, persistent SDD decisions, explicit decision context packets, or SDD artifact audits.
---

# Inonu Harness

Use the local runner for opt-in, read-only diagnosis and explicit SDD support. Keep the normal eight-stage workflow: Constitution, Research, Specification, Planning, Tasks, Implementation, Review, and Convergence. Inonu supplements those stages; it does not replace the host, authorize actions, or run paid services automatically.

## Commands

From the repository root, use `python scripts/inonu.py`:

- `doctor [--project-root PATH]` prints a sanitized JSON inventory. Use `--project-root` when diagnosing a selected project from an installed global skill; omit it to inspect this checkout.
- `baseline run FIXTURE` runs a local offline fixture; `baseline compare BEFORE AFTER` compares saved JSON results.
- `decisions --db PATH create ID --question TEXT --alternatives JSON --criteria JSON --idempotency-key KEY` records a pending decision in a local SQLite store. The decision remains pending until explicit evidence-backed authorization is recorded.
- `decisions --db PATH context --ids ID...` reads only explicitly selected decisions. `decisions --db PATH packet --task-file PATH --ids ID...` validates a task file and combines it with those decisions. Review outputs before attaching them to a task; neither command injects prompts.
- `sdd audit MANIFEST [--root ROOT]` checks declared local artifact links and hashes. It does not run checks or prove their meaning.

Keep real money, credentials, authentication, risk limits, migrations, billing, and other protected actions behind their required human approval. Recommendations and stored decisions never grant permission.

See the [SDD workflow](../../docs/sdd-workflow.md) and [benchmark plan](../../docs/benchmark-plan.md) for the existing process and evidence limits.
