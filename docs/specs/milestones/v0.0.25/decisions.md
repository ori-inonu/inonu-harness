# v0.0.25 decisions

## D1 — Scope (Jev, consensus)

- Spec id `inonu-v025-scope`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted. The facts were built by `jev spec` from [brief.md](brief.md) and `AGENTS.md`: 19 facts, 3,969 characters. The brief was written before the spec and does not state the answer; it records the measurement that the 16 newest milestones already cite every requirement in their task table.
- Options: (a) `milestone new` and `milestone check`; (b) the check only; (c) a close gate and a `MILESTONES.md` index; (d) append-only gap tasks; (e) a pause and resume file; (f) stop.
- Result: `consenso`, leader (a), mean 0.79 in both rounds, agreement 1.0, margin 0.60, rail probability 0.09. Runner-up (b) 0.19, rail 0.01; (c) 0.01, rail 0.08; (d) 0.003, rail 0.15; (e) 0.0, rail 0.09; (f) 0.007. 12 calls, 26,252 input tokens; the judge stopped after two rounds because the result was stable.
- The receipt is a recommendation and grants no authorization. Options (c), (d) and (e) stay open for later milestones; the research ranks them in [research-synthesis.md](research-synthesis.md).

## D2 — What GSD taught, and what was left behind

- Kept: a scaffold that numbers the milestone in code, requirement ids that must be covered by tasks, and a check that runs in `check`.
- Not copied: GSD derives status from model prose and flips a requirement to Complete at execution. Here the check reads only text and reports; it never edits a requirement, and "done" stays the business of the verification commands.
- Not decided here: how a milestone closes. That needs a deferred-items ledger and an index (option c) and is the next candidate.

## D3 — Design choices

- The next version comes from the manifests first (the last released version), then from the highest folder, then `0.0.1`. When the folder for that version already exists, `new` refuses; this repository's own `v0.0.25` folder was created by hand for research, so `new` would refuse here until the manifests are bumped, which is the intended order: the manifests are bumped when a milestone ships.
- Severity: errors fail the check, warnings do not. `decisions.md` is only recommended because v0.0.12 has none; backfilling a decision record for an old milestone would invent history.
- `--from` instead of weaker rules: the legacy milestones are skipped by name, explicitly, and the `check` step documents why. A project that starts at v0.0.1 gets no skip.
- The check reads only the formats this repository uses (`R<n>` list items, a task table). It reports a legacy spec as a warning instead of guessing.

## D4 — Amendments made while building and reviewing

The first implementation found that the spec, read literally, failed the milestones it said must pass, and the independent review found gaps. The spec (R8 to R11) now says what the code does:

- v0.0.12 keeps R9 to R14 under `## Revision after the first independent reviews`, so requirement items are read under `## Requirements` and later `Revision` headings, not only the first section, and stop at a section for deferred work. v0.0.15 has an indented sub-bullet `R5`, so only top-level items count.
- Ranges are kept as intervals. Without that, ten thousand ranges of a thousand ids each cost ten million set entries and a hostile `tasks.md` could produce millions of findings; now references and findings are capped and reported.
- A range whose end had ten digits was read as its bare first id and passed (`R1-R1000000000` cited only R1); ids are now read whole and refused above nine digits.
- A committed symbolic link under the milestones folder fails the step for `--ref`, because the export writes a link as a plain file and the check would read an empty milestone and pass.
- Folders that are not milestones are always reported, and a named version with no folder is exit 2 only when the directory exists.

## D5 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
