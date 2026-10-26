# v0.6.0 tasks — offline evaluation design

The current D01/D02 deliverable is a documentation proposal in [spec.md](spec.md), [plan.md](plan.md), and [decisions.md](decisions.md). D03 selects artifact-handoff contract validation only. The follow-on fixture/test tasks below are not authorized by the Jev receipts, D03, or this design. Do not start them until a later task explicitly authorizes fixture/test work.

The proposed fixtures and traces are synthetic test data. T02/T03 can validate deterministic contract handling and evidence linkage only; they do not execute agents, compare control and treatment sessions, or establish that a practice improves real-agent behavior, quality, productivity, safety, cost, tokens, or tool use.

The existing T01 research history remains in [decisions.md](decisions.md) and [research.md](research.md); it is not reopened here.

## T02 — Author the frozen synthetic five-case fixture records

**Blocked by:** a later explicit authorization to create fixtures. D03 is decided; it does not grant that authorization.
**Files:** `fixtures/sdd_evaluation/clear-change.json`, `ambiguous-change.json`, `reproducible-bug.json`, `specification-delta.json`, `blocked-action.json`.

**Acceptance criteria:**

- [ ] The five records contain only sanitized synthetic intent, the specified eight-entry expected trace with stage `claim_ids`, expected outcome, a case-level claim ledger, gate IDs, and evidence references. The claim ledger enumerates every material claim in `input_intent`, all eight expected trace entries, `expected_outcome`, and gate evidence. The separate gate ledger carries `N/A` reasons; the baseline v1 `acceptance` array contains only applicable `{id, passed}` entries.
- [ ] Each trace names Constitution, Research, Specification, Planning, Tasks, Implementation, Review, and Convergence exactly once and in order.
- [ ] `G-STAGES`, `G-LINKAGE`, `G-OUTCOME`, and `G-AUTHORITY` are mandatory for every case; `G-PROTECTED` is mandatory for the blocked-action case and otherwise carries the specified reason for `N/A` outside the baseline acceptance array.
- [ ] `G-FACT-INFERENCE` is mandatory for every case and covers every material claim in input, all eight expected/observed stages, outcomes, and gate evidence, not only claims supporting another gate. Each claim has a unique ledger ID, stage/scope, statement, kind (`fixture_input`, `observed_output`, `source_fact`, or `inference`), references, and support claim IDs where applicable; required references resolve, and inference is never source-fact evidence.
- [ ] Preserve baseline result schema v1 and its existing `acceptance` item shape; do not add runtime parsing or output fields.
- [ ] No fixture records a live model/service call, vendor tool, token/cost claim, or authorization inferred from a recommendation.

## T03 — Verify synthetic deterministic gates at the public baseline seams

**Blocked by:** T02.
**Files:** `tests/test_sdd_evaluation.py`.

**Acceptance criteria:**

- [ ] Standard-library tests compare each observed trace against the expected stage order, case outcome, gate conditions, and evidence references before recording gate results.
- [ ] Tests compare exact claim coverage for `input_intent`, each of the eight expected/observed trace entries, `expected_outcome`/`observed_outcome`, and every gate-evidence reference. Negative cases prove that omitting an input claim or a gate-evidence claim fails `G-FACT-INFERENCE`; missing, duplicate, orphaned, or unclassified claim IDs also fail.
- [ ] Tests exercise `inonu_harness.baseline.run_fixture(...)` and `inonu_harness.cli.main(argv)` for the existing public seams. After validating a case trace, tests build a complete baseline v1 mapping with every required field (`fixture_schema_version`, `fixture_id`, `task_id`, `config_id`, `acceptance`, `runtime`, `model`, `input_tokens`, `output_tokens`, `cost_usd`, `tool_calls`, `failures`, `blocks`, `recoveries`); the CLI test writes this mapping to a temporary fixture file. Case records are never passed directly to the baseline parser.
- [ ] Assertions cover computed gate entries and provenance only, not measured duration or Python/component versions.
- [ ] Tests verify evidence kinds and required resolvable references for `G-FACT-INFERENCE`; unresolved fixture, observation, or source references fail, and inference labels do not satisfy source-fact evidence. Coverage checks include material assertions in gate evidence, not only the gate status.
- [ ] The baseline result records computed acceptance IDs and pass booleans with fixture provenance; tests do not treat runner output alone as proof that a trace is valid.
- [ ] Unobserved model, token, and cost values remain `null`; no live model/service, added dependency, or router is used.

## T04 — Record per-case outcomes and reviewer notes

**Blocked by:** T03 and D04 result-interpretation decision.
**Files:** a later-authorized `results.md` in this milestone.

**Acceptance criteria:**

- [ ] Each of the five fixtures has a per-fixture pass/fail result, individual gate statuses, and evidence references; any `N/A` has its required reason and input reference.
- [ ] Qualitative reviewer notes appear separately from deterministic gate results and cite their evidence.
- [ ] The report makes no weighted or composite score and makes no claim beyond the traces and cases actually evaluated.
- [ ] The current eight SDD stages and the recommendation/authorization boundary remain intact.
