# v0.0.25 decision brief

Context for the scope decision, written before the spec so that it does not state the answer. The Jev judge sees only the decision object, so this brief is sent as its `facts`.

## Problem

- The owner wants version and milestone management to be a global concept of the Inonu Harness, for every project it manages, and asked for a reverse engineering of GSD (Get Shit Done), whose milestones run as new-milestone, execute, audit, close gaps, complete, then the next one.
- The research is in [research-synthesis.md](research-synthesis.md). Verified in GSD: the milestone audit is model prose, requirements flip to Complete at execution before verification, and no code computes the next version or normalizes ids. Inonu has the scheme and `version --next` (v0.0.24).

## What the code does today

- A milestone is a folder `docs/specs/milestones/vX.Y.Z/` with `spec.md` (requirements R1..Rn), `decisions.md`, `tasks.md` and `checkpoint.md`. Today an agent or a person creates and numbers it by hand.
- `sdd audit` reads a hand-written JSON manifest (requirements, tasks, verifications, evidence with pinned hashes) and reports uncovered requirements. Only the v0.0.8 milestone has such a manifest.
- Measured with a script on the 24 existing milestones: the 16 newest (v0.0.9 to v0.0.24) name each requirement as `R<n>` in spec.md and cite all of them in the acceptance column of tasks.md, with no requirement unclaimed and no unknown one cited; v0.0.12 has no decisions.md. The 8 oldest (v0.0.1 to v0.0.8) use other formats and some have no `R<n>` at all.
- Nothing parses spec.md or tasks.md. Nothing creates a milestone folder, lists the milestones, or checks that a folder name is in the scheme.

## Constraints

- No commit or push without the owner's authorization. No new dependency. No schema or data migration. Nothing may change what `bundle apply` writes into the owner's configuration.
- The tools must work for any project root, not only this repository, and read or write only files below the project root.
- Every change is proven by deterministic tests and an independent review. Existing output keeps its meaning.
