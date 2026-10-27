# v0.0.22 decisions

## D1 — Scope (Jev, no consensus; most reversible option adopted)

Options: (a) an additive, read-only `ownership` field in `bundle status`; (b) (a) plus a new ledger schema with verbatim entries and post-write digests; (c) split the existing `state` values; (d) (a) plus a `tools` allowlist for the worker agent; (e) do nothing (added in the second run).

- Run 1, spec `inonu-v022-ledger-drift`: five facts that the coordinator wrote as a summary. Result `sem_consenso`; leader (a), mean 0.95, agreement 1.0, rail probability 0.24 against a 0.2 limit. Rail probabilities of the others: b 1.00, c 0.94, d 0.95.
- Run 2, spec `inonu-v022-ledger-ctx`, made after the owner pointed out that the judge must decide from the project's context (see D4). The facts are [brief.md](brief.md) and `AGENTS.md`, chunked verbatim: 20 facts, 4,091 characters, each document identified by a digest fact. Neutral options, with (e) added. Result `sem_consenso`; leader (a) again, mean 0.95 in round 1 and 0.79 in round 3, agreement 1.0, but a rail probability of 0.67; (e) 0.00 with mean 0.03; b, c and d 0.99 to 1.00; none-fits rose to 0.19.
- What the two runs show: more context did not change the leader, and it raised the judge's doubt about the rails of (a). The receipt does not say which rail the doubt was about, and the judge cannot see the code.
- Resolution, per the rule for a missing consensus: the most reversible, lowest-risk option, which is (a) and was the judge's own leader in both runs. The rails it could not confirm are enforced by deterministic tests instead of by the judge: the home directory is byte-identical after `status` (R5), `apply` and `remove` are untouched, and the existing status tests pass unchanged (R1, R6). Recorded as `sem-consenso`.
- (b) is deferred, not rejected: it migrates the owner's ledger, a fenced topic, and (a) does not need it because the ledger already records a digest of what the bundle wrote (D2). (c) is rejected for now because it changes the meaning of existing output. (d) stays deferred as in 0.0.21.
- The receipts are recommendations and grant no authorization.

## D2 — Why the existing digests are enough

The ledger already stores, per installed item, the digest of what `apply` wrote. That is the post-write digest for the purpose of telling "unchanged" from "changed": comparing it with what is installed now answers the question without a new field. Verbatim copies would only add a way to show a diff, which `status` does not need and which would put host-file content into a second file.

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.

## D4 — What the Jev judge sees (verified), and the rule that follows

- Verified in the judge's source (`consensus/engine.ts` of the Jevis checkout): the judge receives only `{goal, facts, rails, options}`. The source says of `facts`: "Anything not here, the judge does not know." It reads no repository, no spec file and no conversation.
- Limits: `id` 40 characters, `goal` 600, option `label` 120, option `what` 400, each fact string 300, at most 12 rails of 300, `unknowns.ask` 300, 2 to 8 options. The number of facts is not limited in practice: `consensus_plan` (free, nothing sent) accepted 30 facts of 289 characters (11 planned calls, 38,445 estimated input tokens).
- A fact of 302 characters made `consensus_plan` return only `internal error`, so the server hides a limit violation behind that generic message. This is the likely cause of the two longer specs that failed in 0.0.20; that was not re-run.
- Rule from now on: no Jev call without a written document for the decision. Its text goes verbatim into `facts`, at most 300 characters each, with a fact naming the document path and a short digest. The document states the problem, what the code does today and the constraints, and not the answer. Options are neutral and include "do nothing" when that is real. Rails are written so that a fact in the document lets the judge check them.
- Scopes decided in 0.0.10 to 0.0.21 came from facts the coordinator summarized; no document went with them. They are not re-run: each was also covered by deterministic tests and an independent review. The prototype that built the facts for run 2 is turned into a tested command in 0.0.23.
