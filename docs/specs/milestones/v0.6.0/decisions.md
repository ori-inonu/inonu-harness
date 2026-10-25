# v0.6.0 Wayfinder map: evaluate workflow practices

**Updated:** 2026-10-25

**Map status:** research T01 is recorded; the D01/D02 evaluation proposal is now documented; candidate choice and any evaluation run remain open.
**Research record:** [research.md](research.md)

## Destination

Produce enough first-party evidence and offline evaluation evidence to decide whether a narrowly scoped Inonu practice deserves a future specification. Preserve the current eight-stage SDD flow and its authorization boundaries. This destination does not adopt an external tool, authorize source reuse or implementation, or imply a working integration.

## Notes and guardrails

- The current sequence remains Constitution → Research → Specification → Planning → Tasks → Implementation → Review → Convergence, as recorded in [the SDD guide](../../../sdd-workflow.md).
- Keep sourced facts separate from Inonu inferences. Use the six project snapshots and practice proposals in [research.md](research.md).
- GitHub star counts are dated attention signals only; do not use them as a quality, safety, or fit score.
- Start with a no-paid-call, fixture-backed evaluation. Do not add an adaptive router until its need is supported by that evaluation and a later decision.
- No source copying, installation, production dependency, live model call, tool adoption, or workflow integration is authorized by this research task.
- The D01/D02 proposal is documentation only. No fixture creation or execution, code/test change, live model/service call, tool installation/adoption, or router implementation is authorized by the recorded receipts.

## Decisions so far

- **T01 — Evidence boundary and candidate set:** completed against official GitHub sources for Spec Kit, Superpowers, OpenSpec, BMAD-METHOD, OpenHands, and Cline. Their problem, input/output, candidate practice, dependencies/overlap, license, validation test, and in-house trigger are recorded in [research.md](research.md), with facts separated from inference.
- **Evaluation direction (recommendation only):** test candidate practices offline with frozen fixtures before considering an adaptive router or adoption. This is an evaluation proposal, not an authorization or decision to implement a practice.
- **Flow constraint:** retain the existing eight stages. No external workflow is asserted to integrate with Inonu.
- **D01 — Fixture corpus proposal:** five sanitized categories and their expected traces/outcomes are specified in [spec.md](spec.md). This records the design, not created or executed fixture data.
- **D02 — Acceptance rubric proposal:** deterministic gates, evidence references, the justified `N/A` rule, and separate reviewer notes are specified in [spec.md](spec.md). No aggregate score is proposed.

## Advisory Jev receipt summaries

The following metadata was supplied by the coordinator. Receipt fields are reproduced as supplied; detailed response payloads are not reproduced here. All results are advisory recommendations and none authorizes implementation or evaluation.

| Decision input | specId | Spec hash | Leader | Calls | Failed | Input tokens | Authority |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| D01 corpus | `inonu-v06-fixture-rubric-v1` | `8bd7872ee6d2ab6b749ce7eb735f9ad50ff37c20e11d3c8592ad45afc872f8e2` | `five-cases` | 12 | 0 | 9,881 | Advisory only |
| D02 rubric | `inonu-v06-evaluation-rubric-v1` | `156ac4e863374aae8f4c37fb930a54c667865e8b2982301f3af4205fd72efd06` | `gates-plus-notes` | 9 | 0 | 7,226 | Advisory only |
| D02 evidence scope | `inonu-v06-evidence-gate-scope-2026-10-25` | `9338447d42b147327d86ccebf7ab07bf43c8c1dd4f90331aa6811224715d49c4` | `all_material_trace` | 9 | 0 | 7,611 | Advisory only |

The local D02 proposal now applies claim classification to every material claim in the complete trace and case evidence. This resolves the review's identified coverage gap in the design; it does not authorize fixture creation or implementation.

## Inference and limits

- The `five-cases` and `gates-plus-notes` labels are consistent with the five-case corpus and gate-plus-notes rubric specified here. That is a local interpretation of the supplied leader labels, not a claim about unprovided Jev rationale.
- The current baseline runner records acceptance IDs/pass booleans and fixture provenance; it does not inspect SDD trace events. Future tests must verify traces and evidence references before recording gate results. Existing local fixtures are format examples, not proof that all five categories are covered.
- The evaluation direction and this design do not choose which of the six candidate practices to test, establish that any candidate improves outcomes, or justify a router, tool adoption, source reuse, or integration.
- No evaluation was run, and this record does not claim milestone convergence.

## Not yet specified — fog

These are future decision nodes, not completed choices:

- **D03 — Candidate scope:** which, if any, candidate practices merit an offline evaluation, or does the current flow meet the observed need?
- **D04 — Result interpretation:** after any authorized evaluation, what evidence would justify a follow-on spec for a minimal in-house practice, and what evidence would close this route with no change?
- **D05 — Adaptive routing:** is there a demonstrated problem that requires adaptive selection after a non-routing evaluation? No router is proposed for the current work.

## Out of scope

- Replacing or adding stages to the existing SDD flow.
- Installing or adopting any of the six external projects.
- Copying third-party source, prompts, or skills into Inonu.
- Building a live runtime integration, model router, or evaluation service.
- Treating GitHub stars as anything beyond point-in-time repository attention.

## Next frontier

The next bounded decision is **D03: select whether any candidate practice deserves the later offline evaluation**. If D03 supports proceeding, obtain separate authorization for fixture/test implementation before T02/T03 in [tasks.md](tasks.md). Only then may the five cases be created and exercised through the existing standard-library baseline seam. Keep D04 and D05 open until case-level evidence exists; do not proceed to a router, adoption, or source integration from this map without new evidence and an explicit later decision.
