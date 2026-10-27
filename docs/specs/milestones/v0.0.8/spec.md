# v0.0.8 — Executable SDD artifact audit

## Problem and authorized scope

The toolkit records baseline booleans and persistent decisions but has no executable check that a declared requirement reaches a task and a verification backed by unchanged local artifacts. The user's continuing implementation objective authorizes this reversible local feature and its tests. The historical v0.6 research-only protocol remains a proposal, not an evaluated agent workflow; this milestone supplies a separate usable contract selected in [decisions.md](decisions.md).

## Requirements

| ID | Observable behavior |
| --- | --- |
| R1 | A public `audit_manifest(document, root)` library seam audits explicit v1 requirement/specification/task/verification/evidence links and returns deterministic JSON-compatible findings and coverage. |
| R2 | Missing or dangling links, unresolved requirements, incomplete tasks, non-passing or unlinked checks, missing check evidence, and uncovered task requirements fail the audit. No empty manifest passes. |
| R3 | Evidence must be regular local files below the selected root, with exact SHA-256 byte matches. Unsafe paths, inaccessible/missing/oversized files, and changed evidence fail without reading outside the root or exposing paths/content. |
| R4 | Strict input validation rejects unsupported versions (including booleans), wrong types, unknown fields, invalid IDs/digests, duplicate IDs/list references and duplicate JSON object keys. File input is bounded. |
| R5 | `python -m inonu_harness sdd audit MANIFEST [--root ROOT]` emits the report; exit 0 means the declared artifact contract passes, 1 means findings, 2 means invalid input. The default evidence root is the manifest's parent directory. Existing commands stay compatible. |
| R6 | Five frozen synthetic cases plus adversarial mutations exercise the public library/CLI. Tests record computed audit outcomes through the existing baseline v1 seam; model/token/cost metrics stay null. |
| R7 | Documentation and a self-audit manifest show usage, primary-source inspiration, evidence provenance and limitations. The feature remains an explicit optional check in the existing eight-stage SDD flow and never executes commands, calls a service, writes state or grants authorization. |

## Frozen v1 input contract

The root is exactly `schema_version` (integer 1), `milestone_id`, `requirements`, `tasks`, `verifications`, and `evidence`. Each collection is a nonempty JSON array. Record fields are exact:

| Collection | Record fields |
| --- | --- |
| requirements | `id`, `status` (`defined` or `unresolved`), `specification_evidence_id` |
| tasks | `id`, `artifact_evidence_id`, `requirement_ids`, `status` (`pending`, `blocked`, `complete`), `verification_ids` |
| verifications | `id`, `requirement_ids`, `status` (`pass`, `fail`, `not_run`), `evidence_ids` |
| evidence | `id`, `path`, `sha256` |

IDs match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`; IDs are unique within each collection. Reference arrays contain unique IDs; requirement ID arrays are nonempty; task verification and check evidence arrays may be empty, producing findings. Digests are 64 lowercase hex characters. Paths are nonempty strings; unsafe path syntax is an audit finding, not proof of a local file.

An evidence path uses forward slashes and is relative to root. Reject absolute, drive/scheme, backslash, empty-component, dot or traversal components. A resolved path must remain below the resolved root and be a regular file. Stream at most 8 MiB + 1 byte per artifact; reject larger artifacts. A file loader `load_audit_manifest(path)` reads at most 1 MiB + 1 byte, rejects duplicate keys, and reports invalid UTF-8/JSON/read errors with a fixed sanitized message. Mapping validation raises a fixed sanitized ValueError; no raw key, value or path is echoed.

Every requirement needs verified specification evidence, a defined status and at least one complete task with verified task artifact and a linked passing verification for that same requirement with nonempty verified evidence. Every task's declared requirement needs such a linked verification. All listed tasks must be complete and all listed verifications must pass with verified evidence; checks must be linked from a task. Unknown references fail. Extra unreferenced evidence records are permitted but must still verify.

## Frozen v1 report contract

Top-level fields: `schema_version: 1`, `milestone_id`, `scope: "declared_artifact_links"`, `status: "pass" | "fail"`, `findings`, `coverage`. Each finding contains exactly `code` and `subject` (a sanitized `kind:id`). Each coverage row contains `requirement_id`, `status: "covered" | "uncovered"`, `task_ids` (all tasks declaring that requirement), `verification_ids` (passing verified checks linked through complete tasks with verified artifacts for that requirement). Preserve requirement/task/check input order and deduplicate findings by code/subject.

Stable finding codes: `evidence_unavailable` (unsafe/outside/unreadable/non-file/oversized), `evidence_changed`, `unknown_evidence`, `unknown_requirement`, `unknown_verification`, `requirement_unresolved`, `requirement_uncovered`, `task_incomplete`, `task_requirement_unverified`, `verification_not_passed`, `verification_evidence_missing`, `verification_unlinked`. Any finding yields fail.

## Validation and limits

Use five synthetic inputs: clear change (pass), ambiguous change (unresolved, fail), reproducible bug (pass), specification delta with preserved behavior (pass), and protected action with blocked task (fail). These records describe contract cases, not real agent executions. Negative mutations must catch a requirement dropped from task/check coverage, a check not linked from its task, false pass with no evidence, a changed artifact, path escape (including symlink escape when supported), duplicate keys/IDs, malformed input and oversize files. Exercise CLI exit codes and sanitized errors, as well as computed baseline v1 acceptance and null unobserved measurements. Keep fixture evidence byte-stable across Git checkouts.

This audit verifies declared links and bytes. It does not parse Markdown semantics, authenticate check results, infer missing requirements, execute checks or establish agent quality/productivity. A hash of an invented result is still an invented result. The caller and independent review remain responsible for authentic evidence and meaning. Recommendation/authorization fields are outside the strict input schema; an audit result never grants authority. No new dependencies, database changes, tool installation, runtime replacement, automatic context injection or adaptive routing.
