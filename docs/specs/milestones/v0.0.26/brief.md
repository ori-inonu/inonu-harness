# v0.0.26 decision brief

Context for the scope decision, written before the spec so that it does not state the answer. The Jev judge sees only the decision object, so this brief is sent as its `facts`.

## Problem

- v0.0.25 added `milestone new` and `milestone check`. A milestone is still closed by hand: nothing records that it shipped, nothing ties the manifests to the closed version, and no file lists the milestones that shipped.
- The research ([v0.0.25 synthesis](../v0.0.25/research-synthesis.md)) ranks the close of a milestone next, and also lists append-only gap tasks, a pause and resume file, and waves for parallel workers.
- Verified in GSD: its complete-milestone workflow writes a newest-first MILESTONES.md entry, archives, lets open items be acknowledged, and creates the git tag before the commit that removes REQUIREMENTS.md, so tag and archive disagree.

## What the code does today

- Each of the 25 milestone folders has a `checkpoint.md` written by hand. Measured with a script: from v0.0.12 on, every checkpoint has the folder's version in its first line, a `Status:` line, a `## Verification` section and a `## Limits` section. v0.0.9 to v0.0.11 lack `## Limits`; v0.0.1 to v0.0.8 use other layouts.
- The manifests carry the version of the last shipped milestone and are edited by hand. `version --scheme` checks that they agree and are in the scheme.
- `milestone check` ignores files in the milestones directory and never reads `checkpoint.md`.
- Tasks have no machine-readable status column, so a script cannot tell which tasks are open.

## Constraints

- No commit or push without the owner's authorization. No new dependency. No schema or data migration. Nothing may change what `bundle apply` writes into the owner's configuration.
- The tools must work for any project root, not only this repository, and read or write only files below the project root.
- Every change is proven by deterministic tests and an independent review. Existing output keeps its meaning.
