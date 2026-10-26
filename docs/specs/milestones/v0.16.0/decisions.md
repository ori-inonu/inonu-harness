# v0.16.0 decisions

## D1 — Scope (Jev, consensus)

- Spec id `inonu-v016-legibility-scope`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) docs lint plus a structural import test; (b) the structural test only; (c) docs lint only; (d) a documentation-gardening agent with a quality score.
- Result: `consenso`, unanimous on (a): mean 1.0, agreement 1.0, margin 1.0 over two rounds. Rail probabilities: a 0.02, b 0.05, c 0.11, d 0.99 (the agent would have Inonu run agents and open changes).
- Adopted as engineering scope. It grants no authorization.

## D2 — Research gap closed

The OpenAI primary page that returned HTTP 403 to every fetch route was read through the app's built-in browser in read-only mode ([research-verify.md](research-verify.md)). The in-app browser is a real browser pane, not an automated fetch, and the page is public.

## D3 — Heuristic limits

The 32 KiB byte limit is the documented Codex project-doc default. The 200-line limit is a configurable starting point: the OpenAI team reports an index of about 100 lines, which is their practice and not a limit.

## D4 — Workers on Haiku

Same owner instruction as before: workers run on Haiku 5.5, and the coordinator only orchestrates and fixes review findings.
