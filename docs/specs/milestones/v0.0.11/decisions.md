# v0.0.11 decisions

## D1 — Unfenced slice (Jev, consensus)

- Spec id `inonu-v011-unfenced`: `consensus_plan` then `consensus_run` on the same spec, `max_calls` omitted.
- Options: (a) read-only `bundle status`; (b) baseline regression threshold; (c) secret scan in packets; (d) a + b.
- Result: `consenso`, leader `a_bundle_status`, mean 0.88–0.89, agreement 1.0, margin ≥ 0.81 over two rounds.
- Adopted as engineering scope. It grants no authorization for host configuration writes.

## D2 — Blocked: host configuration writes

`bundle apply/remove` (now v0.0.12) writes hooks, MCP registrations and agent files into global host configuration. It was blocked until the owner's specific authorization. On 2026-10-26 the owner wrote: "Autorizo a v0.0.11: bundle apply/remove/status pode gravar hook, registro MCP e agente worker na minha configuração do Claude e do Codex, com prévia, hashes de posse e reversão." This read-only status slice is implemented first; apply/remove become v0.0.12 under that authorization. The options not chosen (b, c) remain roadmap candidates.

## D3 — Workers on Haiku

Same owner instruction as v0.0.10 D2: workers run on Haiku 5.5, and Opus only coordinates.
