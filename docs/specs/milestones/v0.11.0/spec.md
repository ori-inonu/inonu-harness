# v0.11.0 — Read-only bundle status

Writing hooks, MCP registrations and agent files into host configuration (formerly planned as v0.11.0) awaits the owner's specific authorization and moves to v0.12.0. This slice stays read-only: it reports how far a host already matches the v0.10.0 `bundle plan`. Scope chosen by Jev consensus (see [decisions.md](decisions.md)).

## Requirements

- R1 `python -m inonu_harness bundle status [--host codex|claude|both] [--home PATH]` (default `both`) prints one JSON object with the same `items` (kind, host, id, target) as `bundle plan` and a `state` per item. It writes nothing, and it never prints file contents, settings values, environment values or absolute personal paths.
- R2 States:
  - `skill`: reuse `host_profiles._preflight`. Up to date → `current`; no skill file → `absent`; managed but a different hash → `outdated`; unmanaged or modified → `conflict`.
  - `worker-agent` (Claude): `~/.claude/agents/inonu-worker.md` missing → `absent`; bytes equal to `agents/inonu-worker.md` → `current`; different → `different`.
  - `stop-hook` (Claude): parse `~/.claude/settings.json` read-only. A `Stop` hook command containing `inonu.py check` → `present`; file missing or no match → `absent`; unreadable or invalid JSON → `unknown`.
  - `mcp`: Claude reads the top-level `mcpServers` keys of `~/.claude.json`; Codex reads the `mcp_servers` table keys of `~/.codex/config.toml` via `tomllib`. Id present → `configured`; missing → `absent`; unreadable or invalid → `unknown`. Only key names are inspected. `accessibility` stays `unknown`, because configuration does not prove reachability.
- R3 Summary: the top-level `summary` counts items per state. Exit 0 for any report; invalid input exits 2 through the existing CLI error path.
- R4 Tests with an isolated `--home`: an empty home yields all `absent`; a home with the profile applied, a matching agent file, a settings Stop hook and MCP keys yields `current`/`present`/`configured`; malformed JSON/TOML yields `unknown`; the home tree is byte-identical before and after; stdout contains neither the temp home path nor a planted secret value from the settings or MCP config.
- R5 Docs: CHANGELOG 0.11.0, README, `docs/hosts.md`, source skill bullet; version 0.11.0 in `__init__.py`, `pyproject.toml` and test expectations.

## Out of scope

Any write to host configuration, the install/remove commands (v0.12.0, owner authorization), reachability probes of MCP servers.
