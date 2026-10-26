# Changelog

This changelog prepares release 0.9.0. Earlier entries record repository milestones and do not imply separate published releases or Git tags.

## 0.9.0 — 2026-10-26

### Added

- A standard-library runner at `scripts/inonu.py` for invoking the CLI from any working directory. `doctor --project-root PATH` selects the project to inspect while preserving the default behavior when omitted.
- Native user skill profiles for Codex and Claude Code. `scripts/configure_hosts.py` previews by default and writes only when `--apply` is given. It targets the selected user skill directories, records local ownership metadata, and refuses unmanaged or modified profile files.
- Portable profile commands that quote the runner path for the host shell and point skill documentation links at the checkout that supplied the profile.
- No runtime dependency was added.

### Fixed

- POSIX substitution-test instrumentation now preserves the wrapped `os.open` descriptor-relative capability. This lets Linux CI exercise the intended file substitutions instead of returning early; production evidence-reading rules are unchanged.

### Limits

- Profile application proves only that files were installed or updated. It does not prove a host discovered the skill, loaded it in a session, or successfully used every command. A local Claude Desktop Code session uses local skills; Chat and Cowork use account skill settings instead.
- The profile helper does not configure MCP servers, plugins, credentials, hooks, permissions, providers, or global agent instructions. It is not evidence of universal host activation.
- Inonu complements existing tools. It does not provide CodeGraph symbol navigation, RTK terminal filtering, Headroom context compression, or Ponytail coding guidance. No real-task benchmark shows that Inonu alone is superior to those tools.

## Earlier implementation milestones

### M0 — Local foundation

- Added a sanitized, read-only environment doctor; an offline baseline runner and comparison; and a local SQLite Decision Graph with revisions, evidence, dependencies, idempotency, and distinct recommendation and authorization records.
- Added a typed JEV adapter over an injected MCP transport and a deterministic mock. This is not a portable live JEV transport or proof of JEV availability in another client or session.

### M1–M2 — Explicit decision context and CLI

- Added an opt-in, read-only decision context adapter that returns an allowlisted projection for caller-selected IDs.
- Added the manual `decisions context` CLI command, which reads an existing schema-v1 database without creating or changing it. Fixture checks verify the output contract; they do not measure agent quality, productivity, or speed.

### M3 — Exploratory evaluation protocol

- Documented a proposed text-only pilot comparing the same task with and without explicit decision context. The protocol preserves the existing eight SDD stages and specifies observable criteria and missing-value handling.
- The pilot has not been run. The protocol provides no evidence of a general effect on agent outcomes.

### M4 — Manual task packets and duplicate-key rejection

- Added `decisions packet` to combine caller-provided task JSON with decisions selected by explicit IDs, using the existing read-only projection. The caller reviews and attaches the output; it is not injected automatically.
- The packet reader rejects duplicate JSON object keys, extra fields, and invalid task values. This hardening is specific to the task packet input.

### v0.6.0 — Research and proposals

- Recorded research snapshots and proposals for offline artifact-handoff evaluation, with synthetic case and rubric designs that preserve the eight SDD stages.
- This milestone is research and design only: the proposed corpus and agent evaluation were not executed, and no candidate tool or adaptive router was adopted from the research.

### v0.7.0 — CodeGraph package provenance

- The doctor reports a local CodeGraph license only when the global npm package identity, version, repository, declared license, and executable location agree. Unverified layouts and mismatches remain `unknown`; local paths and raw package metadata stay out of the report.
- This probe does not establish MCP reachability or active-session use.

### v0.8.0 — SDD artifact audit and safety repairs

- Added the optional, read-only `sdd audit` command for a strict v1 manifest. It checks declared requirement, task, verification, and evidence links and hashes files under the selected root.
- Synthetic fixtures exercise passing, failing, and adversarial inputs. The audit does not interpret document meaning, authenticate that a check ran, execute checks, or grant authorization.
- Hardened evidence access against unsafe paths and file substitution while keeping reports sanitized. Platform-specific tests remain skipped where their POSIX conditions are unavailable.
