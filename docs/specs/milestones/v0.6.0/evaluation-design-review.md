# v0.6.0 independent evaluation design review

**Scope:** Reviewed `spec.md`, `plan.md`, `tasks.md`, and `decisions.md` against `research.md`, repository `AGENTS.md`, `inonu_harness/baseline.py`, and `tests/test_baseline.py` / `tests/test_cli.py`. This review did not implement T01, edit reviewed files, run project tests, or call Jev.

## Receipt and authority check

The `decisions.md` receipt table matches the metadata supplied for this review:

| Input | specId | Hash | Leader | Calls / failures | Input tokens |
| --- | --- | --- | --- | --- | ---: |
| Corpus | `inonu-v06-fixture-rubric-v1` | `8bd7872ee6d2ab6b749ce7eb735f9ad50ff37c20e11d3c8592ad45afc872f8e2` | `five-cases` | 12 / 0 | 9,881 |
| Rubric | `inonu-v06-evaluation-rubric-v1` | `156ac4e863374aae8f4c37fb930a54c667865e8b2982301f3af4205fd72efd06` | `gates-plus-notes` | 9 / 0 | 7,226 |

`decisions.md` identifies these as coordinator-supplied metadata, says the detailed response payloads are unavailable, and labels both results advisory only. It attributes no unprovided rationale to Jev and says they authorize neither implementation nor evaluation. This confirms consistency with the ticket-provided receipt values; it does not independently authenticate underlying receipt payloads or hashes.

## Findings

### [P2] The rubric omits a deterministic research fact/inference check

`research.md`'s offline-evaluation recommendation explicitly lists “source facts remain distinguishable from inference” among the deterministic properties to score. The D02 gate table in `spec.md` covers stage order, requirement linkage, outcomes, recommendation/authorization separation, and protected actions, but none checks whether research-stage claims are labeled and supported as source facts versus Inonu inferences. The case traces mention cited contracts, facts, or local evidence, but do not make this distinction a pass condition. As written, a trace could pass all gates while presenting an inference as a sourced fact. Add a bounded gate and expected evidence for this property, or narrow the research recommendation before freezing fixtures.

Evidence: [`research.md` — Offline evaluation recommendation](research.md#offline-evaluation-recommendation); [`spec.md` — D02 deterministic acceptance rubric](spec.md#d02--deterministic-acceptance-rubric).

### [P2] T02 does not define how its case records satisfy the baseline fixture contract

`spec.md` describes each case record as `case_id`, `input_intent`, `expected_trace`, `expected_outcome`, and a gate ledger. T02 similarly describes five records around expected traces and gate evidence, while T03 requires exercising `baseline.run_fixture(...)` and the CLI. The existing runner validates the input fixture before recording it: `_FIXTURE_REQUIRED` in `baseline.py` also requires `fixture_schema_version`, `fixture_id`, `task_id`, `config_id`, `runtime`, `model`, token/cost fields, and the tool/failure/block/recovery lists. The ordinary fixture examples provide these fields, but T02 does not say whether the evaluation records include that v1 envelope or whether tests construct a separate runner mapping. This leaves the future fixture-to-runner interface underspecified and risks records that cannot be passed to the named seam. Specify the required v1 envelope (including null/unobserved measurements and empty lists where appropriate), or explicitly define a test-only mapping from case metadata to a valid v1 runner fixture; keep `{id, passed}` unchanged and do not add runtime output fields.

Evidence: [`spec.md` — D01 case record](spec.md#d01--sanitized-fixture-corpus); [`tasks.md` — T02/T03](tasks.md#t02--author-the-frozen-five-case-fixture-records); [`baseline.py` — fixture validation](../../../../inonu_harness/baseline.py#L22-L35) and [`_validate_fixture`](../../../../inonu_harness/baseline.py#L197-L220); [`offline-smoke.json`](../../../../fixtures/baseline/offline-smoke.json).

## Verified design coverage

- The five cases are clear change, ambiguous change, reproducible bug, specification delta, and blocked action. Each expected trace narrates the preserved eight stages in order.
- The rubric keeps the four common gates mandatory, limits `G-PROTECTED` to the blocked-action case, gives the other four cases the stated `N/A` reason outside `acceptance`, and keeps reviewer notes separate with evidence references. It prohibits weighted/composite scores and claims beyond evaluated cases.
- The runner is accurately described as recording caller-supplied `{id, passed}` entries rather than validating traces. The code validates `passed` as a Python `bool` and records fixture provenance by default. `run_fixture(...)` and `inonu_harness.cli.main(argv)` are present public seams used by existing tests.
- The design explicitly excludes elapsed duration and Python/component versions from evaluation assertions and comparisons. Follow-on tasks are ordered T02 → T03 → T04, with D03 and separate fixture/test authorization before T02 and D04 before T04. The eight-stage flow and recommendation/authorization boundary remain intact.
- The spec, plan, and decision record state that the current increment is documentation-only and that fixtures, tests, live calls, integrations, adoption, and routing are not authorized or claimed complete.

## Convergence status

Structural documentation checks and `git diff --check` are pending for coordinator convergence. No project tests were run, as directed. This review does not claim milestone convergence.

## Independent re-review — 2026-10-25

**Scope:** Rechecked the updated `spec.md`, `plan.md`, `tasks.md`, `decisions.md`, and `research.md` against `inonu_harness/baseline.py`, `tests/test_baseline.py`, and `tests/test_cli.py`. No project tests were run. This section preserves the first review above and records the disposition of its findings.

### Finding dispositions

#### [P2] The research fact/inference gate still covers only claims used by gates — unresolved

The new `G-FACT-INFERENCE` row at `spec.md:90` requires every claim *used to support a gate* to be labeled and referenced. The research property at `research.md:115` is broader: source facts must remain distinguishable from inference. The case traces at `spec.md:44`, `52`, `60`, and `68` require Research to cite a contract, list local facts, or cite evidence, but none requires the claim/evidence ledger to cover every material Research-stage claim. A false or unsupported research claim that does not support a later gate can therefore remain unclassified while the gate passes. The original finding is only partially addressed; the future rubric must cover all material Research-stage claims as well as claims used by gates, or narrow the research property before fixtures are frozen.

#### [P2] Case records were not mapped to the baseline fixture contract — resolved

`spec.md:19` now explicitly separates case records from baseline fixtures and maps validated cases to an in-memory v1 fixture containing all 14 fields in `baseline.py:21-36`; it specifies applicable `{id, passed}` acceptance entries, `null` unobserved measurements, event lists, and the mapping to `run_fixture(...)`. `plan.md:8` and `tasks.md:29` repeat the contract and require the CLI test to write a valid mapping rather than pass a case record directly. The source validator at `baseline.py:198-224` checks schema version 1, required IDs, list fields, acceptance item shape, and nullable values. `tests/test_cli.py:17-31` confirms the existing `main(argv)` seam accepts `baseline run --fixture`.

No additional P1/P2 finding was identified in the reviewed scope. The eight ordered stages remain explicit in `spec.md:25-32`. Scope and authority remain constrained: `spec.md:11` keeps the current increment documentation-only, `spec.md:34` keeps recommendations advisory, `plan.md:7-8` and `tasks.md:9,19` gate later fixture work on D03 and separate explicit authorization, and `decisions.md:14-19,42-43` preserves the eight-stage flow and says no implementation, integration, router, or evaluation is authorized or claimed complete.

**Review disposition:** blocked pending resolution of the remaining P2 fact/inference coverage gap. Structural documentation checks and coordinator convergence are still pending; this review does not claim milestone convergence.

## Independent re-review — 2026-10-25 (full-trace claim coverage)

**Scope:** Rechecked the updated `spec.md`, `plan.md`, `tasks.md`, and `decisions.md` against `research.md`, `inonu_harness/baseline.py`, `tests/test_baseline.py`, and `tests/test_cli.py`. No project tests were run. Earlier reports above are preserved as historical findings.

### Finding dispositions

#### [P2] The fact/inference coverage requirement is broader than T03 test acceptance — unresolved

The design now closes the original Research-stage escape: `spec.md:38-40` requires `claim_ids` for each expected and observed stage entry and a case ledger covering all eight stages, while `spec.md:92` makes missing, unclassified, duplicate, orphaned, or unresolved required references fail `G-FACT-INFERENCE`. It excludes hidden model reasoning at `spec.md:40`.

However, the gate also requires coverage of material claims in the input and gate evidence (`spec.md:40,92`), while T03 only requires exact stage-to-claim coverage across eight trace entries and outcomes (`tasks.md:29`). Its reference checks at `tasks.md:32` do not require exact claim coverage for `input_intent` or material assertions in gate evidence. The future implementation could therefore satisfy T03 while omitting one of those claims from the ledger. Extend T03 to verify exact claim coverage for input and gate evidence, including missing/orphaned IDs. Until then, the earlier fact/inference finding is only partly resolved.

#### [P2] Case records were not mapped to the baseline fixture contract — resolved

The prior disposition remains valid: `spec.md:19` maps validated cases to all 14 required baseline v1 fields; `baseline.py:21-36` defines the required field list, and `baseline.py:198-224` validates schema version, IDs, list fields, `{id, passed}` entries, and nullable measurements. `plan.md:8` and `tasks.md:30` require construction of this complete mapping and a CLI test through the existing seam (`tests/test_cli.py:17-31`).

No additional P1/P2 finding was identified. The eight stages remain in `spec.md:23-32`; recommendation and authorization remain separate at `spec.md:34,91`; the current change is documented as docs-only at `spec.md:11`, with later fixture/test work still gated by D03 and explicit authorization in `plan.md:7-11` and `tasks.md:3,9`.

**Review disposition:** blocked pending the T03 coverage gap for input and gate evidence. No project tests were run, and this review does not claim deterministic convergence.

## Independent re-review — 2026-10-25 (input and gate-evidence test coverage)

**Scope:** Rechecked the corrected `plan.md` and `tasks.md` against the claim-ledger contract in `spec.md` and the earlier reports above. No project tests were run; this review verifies the future test requirements, not their implementation.

### Finding dispositions

#### [P2] Fact/inference coverage did not require T03 checks for input and gate evidence — resolved

The case record now requires the claim ledger to enumerate every material claim from `input_intent`, all eight expected trace entries, `expected_outcome`, and gate evidence (`tasks.md:14,17`). T03 now requires exact coverage checks for `input_intent`, each expected and observed stage, expected and observed outcomes, and every gate-evidence reference; it includes negative cases for omitting an input claim or a gate-evidence claim (`tasks.md:29`). It also requires coverage of material assertions in gate evidence, not only the gate status, and failure on unresolved fixture, observation, or source references (`tasks.md:32`). The plan repeats this scope and the negative cases (`plan.md:6,8`). These test requirements now match the full-trace gate in `spec.md:38-40,92`.

#### [P2] Case records were not mapped to the baseline fixture contract — remains resolved

`spec.md:19` maps validated case records to all 14 required baseline v1 fields. `baseline.py:21-36` lists those fields, and `baseline.py:198-224` validates schema version, required IDs, list fields, `{id, passed}` acceptance entries, and nullable measurements. `tasks.md:30` preserves construction of that mapping and exercises `run_fixture(...)` and the `main(argv)` CLI seam without passing a case record directly to the parser.

No new P1/P2 finding was identified. The eight stages remain explicit and ordered (`spec.md:23-32`); the claim contract excludes hidden model reasoning (`spec.md:40`); recommendation and authorization remain distinct (`spec.md:34,91`). The current increment remains documentation-only, with later fixture/test work gated on D03 and explicit authorization (`plan.md:3,7-11`; `tasks.md:3,9`).

**Review disposition:** no material findings remain in this design-document scope. No project tests were run, and this review does not claim implementation or milestone convergence.

Remaining findings: none.

## Independent re-review — 2026-10-25 (final coverage summary)

**Scope:** Rechecked the final `spec.md` summary against D01/D02, `plan.md`, `tasks.md`, `decisions.md`, and the earlier reports above. Confirmed the baseline contract against `inonu_harness/baseline.py` and the existing baseline/CLI test seams. No project tests were run; this remains a documentation design review.

### Finding dispositions

- **Research fact/inference gate — resolved.** `spec.md:38-40,92` defines material claims, excludes hidden model reasoning, requires the per-case ledger to cover input, all eight expected/observed stages, outcomes, and gate evidence, and makes missing, unclassified, duplicate, orphaned, or unresolved required references fail `G-FACT-INFERENCE`. `research.md:115` identifies this source-fact/inference distinction as a deterministic property.
- **Case-record to baseline v1 mapping — remains resolved.** `spec.md:19` lists all 14 required fields and keeps case records separate from runner fixtures; `tasks.md:30` requires the in-memory v1 mapping and CLI fixture file. `baseline.py:21-36,198-224` confirms the required fields, `{id, passed}` acceptance shape, and nullable optional values; `tests/test_cli.py:17-31` confirms the existing `main(argv)` baseline seam.
- **Full-trace and T03 claim-coverage scope — resolved.** `spec.md:97` now summarizes the same exact coverage as `spec.md:38-40,92`: `input_intent`, every expected/observed entry in the eight stages, expected/observed outcomes, and each gate-evidence reference. `tasks.md:14,17,29,32` requires the case ledger and tests to cover those scopes and includes negative omissions for input and gate-evidence claims, as well as malformed IDs and unresolved references. `plan.md:6,8` matches that contract.

No new P1/P2 finding was identified. The eight stages remain ordered at `spec.md:23-34`; recommendations remain separate from authorization at `spec.md:34,91`; the current increment remains documentation-only and later fixtures/tests remain gated by D03 and separate authorization in `plan.md:3,7-11` and `tasks.md:3,9`. `decisions.md:31,37,39` keeps the Jev result advisory and explicitly says it does not authorize fixture creation or implementation.

**Review disposition:** all prior material findings are resolved in the design documents. No project tests were run; fixtures and the offline evaluation remain unimplemented and unexecuted. This review does not claim implementation or coordinator convergence.

Remaining findings: none.
