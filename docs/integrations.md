# Integration inventory

This page records the evidence gathered for the M0 implementation host on 2026-10-24. It is not a claim that another agent or machine has the same tools. `python -m inonu_harness doctor` rechecks the local host without printing configuration values or private paths. A registered MCP server is not evidence that it is reachable in every Codex client; the standalone doctor reports accessibility as `unknown` because it has no official API for inspecting the active tool set.

## Observed state

| Component | Evidence from this host | Limit |
| --- | --- | --- |
| Codex | CLI `0.164.0-alpha.11.1`; Python `3.14.7`; Windows PowerShell | `codex --version` does not report the desktop app version. |
| Jev | `jev-sdd` MCP calls worked in the coordinator chat; no standalone `jev-sdd` command was found | Local CLI doctor can see registration, not whether another session loaded it. Transport portability is unverified. |
| RTK | CLI `1.0.1` present; a global hook reference targets Bash | This session used PowerShell; the hook did not run here. Installed does not mean operational. |
| Headroom | `0.41.0` and MCP tools were available in the coordinator chat | The local proxy was unreachable. CLI doctor cannot assert active MCP reachability. |
| CodeGraph | CLI `3.0.1` present; MCP `orient` worked in the coordinator chat; a local index exists | MCP availability is specific to that session. The doctor reports it as `unknown`. |
| Ponytail | Plugin package `5.3.2` and its skill are present; the skill was active in the implementation conversation | This is agent guidance, not a separate service or decision authority. |
| Matt Pocock SDD skills | Local adapters and an upstream copy were present | No release or Git revision metadata was available, so no version is asserted. |
| Sequential Thinking | Not present in the Codex MCP registry | Installation and operational state remain unknown. It is not a core dependency. |

The inventory intentionally omits local configuration values, hook commands, credentials, and paths. MCP names in a local report mean only “registered in the visible configuration,” unless a host API proves more.

## Tool contracts and candidates

### Jev

- **Problem:** choose among a bounded set of engineering alternatives with advisory consensus.
- **Input/output contract:** the observed MCP contract accepts `consensus_plan({spec})`, followed by `consensus_run({spec})` with the same sanitized decision object and no `max_calls` unless explicitly required. A usable consensus can include a leader and spec hash. No result grants authorization.
- **Inonu candidate:** obtain an allowed alternative for a pending decision, then store only the bounded recommendation, available provenance, and version in the Decision Graph.
- **Dependencies and overlap:** host MCP transport and the existing Jev service; overlaps human review and graph recommendation records. The Python adapter exposes an injected transport and deterministic mock only; no portable live transport is configured in this CLI.
- **License:** unknown for the configured JEV service.
- **Test:** use the mock for allowed/forbidden options, malformed results, timeout, unavailability, and proof that no authorization is written.
- **Implement it ourselves when:** the confirmed host transport is unavailable and repeated local tasks need a bounded, auditable substitute. Do not recreate the model judge.

### RTK

- **Problem:** reduce noise in supported shell command output.
- **Input/output contract:** a supported local command goes through the RTK CLI or a compatible hook; the output is compacted. Exact coverage depends on the installed RTK component.
- **Inonu candidate:** keep routine terminal results concise while preserving a route to the original output for debugging and verification.
- **Dependencies and overlap:** RTK CLI plus a supported shell/hook route; overlaps agent summarization and other output filters. The host hook was Bash-oriented while this session used PowerShell, so the automatic path was not validated.
- **License:** RTK CLI is Apache-2.0; `rtk-engine` and the separate `rtk-proxy` use BUSL-1.1 terms. These components have different licenses.
- **Test:** compare compacted and original success/error output on fixed commands, including retrieval of the original.
- **Implement it ourselves when:** a measured fixture shows that runtime filtering does not preserve the needed information. Do not duplicate RTK's supported command filters.

### Headroom

- **Problem:** selectively compress unusually long context sources and retrieve original content when needed.
- **Input/output contract:** a caller supplies a document, log, or JSON payload to an available compression/retrieval tool; the result is a compressed representation or retrieved source content. The MCP tools also expose statistics.
- **Inonu candidate:** use it on unusually long non-terminal material while preserving access to the original for checks and debugging.
- **Dependencies and overlap:** Headroom package or MCP tool and a caller choosing the source; overlaps RTK output filtering, file search, and model context handling. The local proxy was unreachable in the observed host.
- **License:** Apache-2.0.
- **Test:** use a local long fixture and verify recovered facts against the source; do not infer token or cost savings without measurement.
- **Implement it ourselves when:** repeated tests show a retrieval or compression gap that the supported Headroom API does not cover.

### CodeGraph

- **Problem:** navigate symbols, dependency relationships, duplicates, and change impact beyond text search.
- **Input/output contract:** a local repository/index is queried through its CLI or MCP; supported results include repository orientation, symbol or dependency information, and impact evidence.
- **Inonu candidate:** target navigation and impact questions, then link the relevant source evidence to a decision or review.
- **Dependencies and overlap:** CodeGraph CLI/MCP and a local repository index; overlaps `rg`, language-server navigation, and test/compiler dependency graphs. The local CLI version was `3.0.1`; MCP access was observed only in the coordinator chat. The exact local package-to-upstream mapping was not proven by the doctor.
- **License:** MIT for the [CodeGraph repository](https://github.com/codegraph-ai/CodeGraph); confirm the installed distribution's source before relying on that license for the local binary.
- **Test:** run one bounded symbol/dependency query on a deterministic local fixture and compare it to known references.
- **Implement it ourselves when:** a measured navigation need persists and the installed CodeGraph interface does not provide the required evidence.

### Ponytail

- **Problem:** keep coding changes small while retaining correctness and necessary checks.
- **Input/output contract:** a coding task and repository context are read by the agent skill system; output is guidance to the coding agent, not a runtime service.
- **Inonu candidate:** apply the existing skill when choosing implementation scope and reviewing a change; do not build a second policy engine.
- **Dependencies and overlap:** Codex skill discovery/loading; overlaps repository instructions and implementation/review skills.
- **License:** the upstream skill frontmatter declares MIT.
- **Test:** review a fixed change and verify that simplifying it did not remove acceptance checks, validation, security, or accessibility.
- **Implement it ourselves when:** repeated examples show a concrete gap in the guidance; no replacement is needed now.

### Sequential Thinking

- **Problem:** structure branching or revision for a bounded multi-step question.
- **Input/output contract:** the specific server receives a question and returns intermediate or final structured content; this installation was not found, so its contract was not exercised here.
- **Inonu candidate:** none in the core. The Decision Graph already models durable dependencies and revisions.
- **Dependencies and overlap:** a Sequential Thinking MCP server and host transport; overlaps agent planning, successive Jev decisions, and graph dependencies.
- **License:** the upstream MCP server documentation identifies MIT.
- **Test:** compare a deterministic branching task with and without the tool, and confirm that no hidden model reasoning is persisted.
- **Implement it ourselves when:** a measured use case needs durable branching that the existing planning and Decision Graph cannot represent.

## Source references

- [RTK license overview](https://github.com/rtk-ai/rtk#license), [RTK engine license](https://github.com/rtk-ai/rtk/blob/develop/engine/LICENSE)
- [Headroom repository and license](https://github.com/headroomlabs-ai/headroom)
- [CodeGraph repository and license](https://github.com/codegraph-ai/CodeGraph)
- [Sequential Thinking server documentation and license](https://github.com/modelcontextprotocol/servers/blob/main/src/sequentialthinking/README.md)
- [Ponytail upstream repository](https://github.com/DietrichGebert/ponytail)
- [GitHub Actions checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python)

No source code or implementation from these tools is copied into Inonu.
