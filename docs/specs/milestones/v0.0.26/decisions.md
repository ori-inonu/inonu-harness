# v0.0.26 decisions

## D1 — Scope (Jev, consensus)

- Spec id `inonu-v026-scope`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted. The facts were built by `jev spec` from [brief.md](brief.md) and `AGENTS.md`: 19 facts, 3,903 characters. The brief records the measurement that every checkpoint from v0.0.12 on has the version in its first line, a `Status:` line and the `Verification` and `Limits` sections.
- Options: (a) close gate and index; (b) index lint only; (c) checkpoint identity only; (d) append-only gap tasks; (e) pause and resume file; (f) waves for parallel workers; (g) stop.
- Result: `consenso`, leader (a), mean 0.74 in round 1 and 0.74 in round 2, agreement 1.0, margin 0.57, rail probability 0.10. Runner-up (c) 0.17 with rail 0.01; (b) 0.04 to 0.06; (d) 0.02 with rail 0.15; (e) and (f) 0. 13 calls, 28,202 input tokens; the judge stopped after two rounds because the result was stable.
- The receipt is a recommendation and grants no authorization. Options (d), (e) and (f) stay open; the research ranks them in [research-synthesis.md](../v0.0.25/research-synthesis.md).

## D2 — Design choices

- The close is a gate that writes one file. GSD's close also archives, deletes the requirements file and tags; the tag comes before the commit that removes the file, so the two disagree about what shipped. Here nothing is moved, deleted or tagged, so there is nothing to disagree.
- The manifests must already state the version. The close does not bump them, because they are three formats of source (Python, TOML, JSON) and a bump script is a larger risk than the one-line edit it saves; the gate makes the order explicit instead: bump, write the checkpoint, close, then `milestone new`.
- The index starts at the first milestone closed with the command. Earlier milestones are not backfilled: a dated list of 24 entries written now would be reconstructed history. The Git log and the checkpoints remain their record.
- Checkpoint sections are required at close, not retroactively in `check`: only the identity (the version in the first line) is checked for every milestone from `--from` on, because every checkpoint from v0.0.9 has it.
- Deferred items are counted, and must carry a reason, because the research shows GSD lets open items be acknowledged with no record of why. The section is optional, since no existing checkpoint has one.
- The index lives inside the milestones directory, so `check` already ignores it as a non-directory and the same containment rules cover it.

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
