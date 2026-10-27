# v0.0.7 decisions — CodeGraph package provenance

## D01 — How to attribute the installed CodeGraph package

**Evidence:** local package metadata reports `@lzehrung/codegraph` 3.0.1, MIT, and `git+https://github.com/lzehrung/codegraph.git`; the CLI reports 3.0.1 and its containing directory matches the inferred global npm bin. The official installation guide also documents a standalone path, which this npm-only check cannot identify.

**Jev:** `consensus_plan` and matching `consensus_run` were performed for `doctor-codegraph-provenance-2026-10-25` (spec hash `829a91005445c7abd99c4d729629ec34c4659b16ff78227390107318f379e1e1`). Result: `sem_consenso`, no leader, 13 calls, 0 failures, 12,934 input tokens. The rounds favored npm-root discovery but did not reach consensus. This receipt is advisory.

**Decision:** use `npm root -g` read-only and accept metadata only when the package identity, CLI version, license, official repository, and executable bin directory all match. Otherwise retain unknown. This is a reversible implementation choice based on the verified local layout; it does not authorize installation or configuration changes.

**Rejected alternatives:** keep every installation unknown (safe but discards directly verifiable local provenance); infer identity from CLI version alone (can misattribute forks or standalone binaries).

## D02 — Verification boundary

Test `LocalProbe.snapshot()` with temporary files and mocked external process/PATH boundaries, then pass its result through `collect_environment()` and assert the serialized report is allowlisted. This checks package discovery and sanitization without network access or a live MCP call.
