# v0.15.0 decisions

## D1 — Plugin scope (Jev, no consensus; most reversible option adopted)

- Spec id `inonu-v015-plugin-scope`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) plugin with skill, worker agent and marketplace, no MCP and no hooks; (b) a plus an automatic `.mcp.json` for three servers; (c) a plus a Stop hook; (d) documentation only.
- Result: `sem_consenso`. The leader was (a), mean 0.48 in the last round, agreement 1.0, margin 0.29. It was held back by its rail probability (0.41 against a 0.2 limit) and by "none fits" (0.33 against 0.3). Options (b) and (c) scored near zero with rail probabilities of 1.00 and 0.89, matching the finding that no approval prompt is documented before a plugin's MCP servers start.
- Resolution, per the rule for a missing consensus: the most reversible, lowest-risk option that still delivers. That is (a): it adds repository files only, installs nothing anywhere and is undone by deleting them. Recorded as `sem-consenso`. The unconfirmed points are stated in the docs.
- The receipt is a recommendation and grants no authorization.

## D2 — What the plugin deliberately omits

No automatic MCP servers and no hooks. They would run third-party code (`npx` packages) or a test suite for every user who enables the plugin without a documented approval step. Installing them stays an explicit, previewed action through `bundle apply`.

## D3 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
