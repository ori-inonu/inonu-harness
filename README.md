# Inonu Harness

Inonu is a local, reproducible toolkit for observing an agent environment, evaluating deterministic fixtures, and keeping a persistent history of engineering decisions. It complements the current Codex runtime and SDD workflow; it does not replace either.

## Local capabilities

- A read-only environment doctor that emits sanitized JSON and labels facts it cannot verify as `unknown`.
- An offline baseline runner and comparison command. Every metric carries provenance; unavailable values stay `null`.
- An M0 SQLite Decision Graph with revisions, evidence, dependencies, idempotency, and separate recommendation and authorization records.
- An M0 typed JEV adapter that uses an injected MCP transport, plus a deterministic mock. Jev MCP calls were observed in the coordinator chat on 2026-10-24; that host/session observation does not establish access from other clients or a portable CLI. No portable live JEV transport is implemented or configured.
- M1–M2 read-only decision context for explicit IDs, exposed through an opt-in adapter and the manual `decisions context` command. M4 adds `decisions packet`, which combines a caller-provided task file with explicitly selected decisions; it rejects duplicate JSON object keys.
- An optional `sdd audit` command checks explicit requirement, task, verification, and local evidence links from a v1 manifest. It is read-only and does not add a step to the SDD sequence.
- M3 documents an exploratory evaluation protocol only; the pilot has not been run. The optional SDD gate is disabled by default, and the existing eight SDD steps remain the normal workflow.

JEV recommendations are advisory and never grant authorization. Local authorization requires evidence for each required criterion, and recording it does not execute an external operation.

See [native host profiles](docs/hosts.md) for preview/apply instructions, portable runner use, and host discovery limits. [CHANGELOG.md](CHANGELOG.md) records implemented milestones and proposals.

The code uses Python 3.11+ and the standard library. No global installation or runtime package dependency is needed to run it from this checkout.

## Run locally

From the repository root:

```powershell
python --version
python -m inonu_harness doctor
python -m unittest discover -s tests -v
```

Run a deterministic fixture and compare two saved results:

```powershell
python -m inonu_harness baseline run fixtures/baseline/offline-smoke.json --execution-id before > before.json
python -m inonu_harness baseline run fixtures/baseline/offline-smoke.json --execution-id after > after.json
python -m inonu_harness baseline compare before.json after.json
```

The fixture path may be positional or supplied with `--fixture PATH`.

Audit one frozen synthetic SDD case. The evidence root defaults to the manifest's directory; these shared fixtures use `--root fixtures/sdd_audit`:

```powershell
python -m inonu_harness sdd audit fixtures/sdd_audit/clear-change/manifest.json --root fixtures/sdd_audit
```

The command prints a JSON report and returns 0 for a pass, 1 when the manifest has findings, or 2 for invalid input. Evidence hashes detect byte drift, but do not establish semantic correctness or authenticate that a check actually ran. See [the SDD guide](docs/sdd-workflow.md) for scope and limitations.

Create a decision and inspect it. The database defaults to `~/.inonu-harness/decisions.sqlite`, outside the checkout; pass `--db PATH` after `decisions` to choose another file. The directory is created only when a decision command runs.

```powershell
python -m inonu_harness decisions create storage-choice `
  --question 'Which local persistence mechanism should M0 use?' `
  --alternatives '[{"id":"sqlite","label":"SQLite"},{"id":"json","label":"JSON file"}]' `
  --criteria '["durable"]' `
  --constraints '["standard library only"]' `
  --idempotency-key create-storage-choice
python -m inonu_harness decisions list
python -m inonu_harness decisions show storage-choice
```

`decisions recommend` records an existing recommendation; it does not call JEV. `decisions authorize` records an explicit local authorization only when every required criterion has evidence. Recording authorization does not execute an external operation.

## Layout

- `inonu_harness/` — doctor, baseline, Decision Graph, JEV contract/mock, and CLI.
- `fixtures/` and `tests/` — deterministic, offline examples and checks.
- `docs/specs/milestones/v0.1.0/` — M0 requirements, decisions, plan, tasks, and checkpoint.
- `docs/integrations.md` — observed states, contracts, overlaps, licenses, and validation ideas.
- `docs/sdd-workflow.md` — the current SDD sequence and optional graph boundary.

See [the SDD guide](docs/sdd-workflow.md), [integration inventory](docs/integrations.md), and [benchmark plan](docs/benchmark-plan.md) before changing the workflow or claiming performance gains.

## Scope and license

The project does not install or reimplement RTK, Headroom, Ponytail, CodeGraph, or Sequential Thinking. No external tool source is copied. The public repository has not declared a project license; public visibility alone does not grant reuse rights.
