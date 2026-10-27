# Inonu Harness M2 — CLI consumer for SDD decision context

## Problem

M1 provides a typed, read-only adapter, but a human or workflow must write Python code to consume it. The CLI already exposes the local Decision Graph, so a caller-facing JSON command is the smallest explicit path to copy selected decision context into an SDD task.

## Confirmed scope

Add `python -m inonu_harness decisions --db <path> context --ids <id> [<id> ...]`. The command is opt-in by invocation, accepts only caller-selected IDs, and emits the existing typed projection as JSON. It does not inject prompts, discover decisions, authorize actions, call JEV, or change the eight-stage SDD sequence.

Open the selected SQLite database in read-only mode for this command. Do not create a missing database, initialize its schema, or change its bytes. Existing write commands keep their current behavior. A valid but absent decision retains the existing CLI error behavior; malformed or repeated IDs return the adapter's `invalid_request` result.

## Controlled local comparison

Use one task fixture describing the real local task of adding this CLI consumer. Run its unchanged task packet in two conditions: without selected decision context, and with the JSON returned by the explicit command. Derive acceptance only from whether the selected context and task rails appear in the returned projection. Compare the two local baseline records with the existing `compare_runs` API using the same task/config IDs.

This contrast tests whether the consumer delivers the durable fields selected for this task. It does not execute an AI agent, assess answer quality, or claim productivity, token, cost, or agent-speed benefits. Measure only the local CLI read duration; retain `null` for unobserved agent runtime, model, token and cost fields. Tool/failure/block/recovery lists are fixture declarations, not agent observations.

## Requirements

### M2-R01 — Explicit CLI consumption

- The command requires a database path option already supported by the `decisions` CLI and one or more explicit decision IDs.
- Output is the existing `SddDecisionContextResult` JSON schema, with only the adapter's allowlisted projection.
- No automatic SDD/runtime consumer, hook, prompt injection or discovery is introduced.

### M2-R02 — Read-only storage access

- Context retrieval opens the database without creating it or initializing/updating the schema.
- Decision state and history are unchanged by retrieval.
- Existing create, review, recommend, authorize and block commands retain write behavior.

### M2-R03 — Controlled task contrast

- A fixture and test exercise the CLI against a temporary SQLite database and one unchanged task packet in context-free and context-attached conditions.
- Acceptance booleans are derived from the CLI result; the existing baseline comparison reports the observed difference.
- The evaluation makes no claim about AI-agent quality, productivity, model use, token/cost savings or end-to-end task speed.

### M2-R04 — Preserve SDD and M0

- Documentation explains the explicit manual command and its limits.
- The eight SDD stages and existing CLI operations remain unchanged.
- No new dependency, live JEV transport, credential access, user database mutation, commit or push is introduced.

## Test seam

Exercise `decisions context` through `inonu_harness.cli.main` with a temporary database. Compare database bytes and decision history around the read. For the task contrast, feed the CLI's serialized projection into the existing `run_fixture` and `compare_runs` functions.

## Out of scope

- Automatic Codex runtime integration or prompt construction.
- Agent-vs-agent experiments, hosted CI execution, or performance claims.
- Changes to the eight-stage SDD flow, decision schema, authentication, integrations or global configuration.
