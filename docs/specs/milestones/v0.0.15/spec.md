# v0.0.15 — Installable Claude Code plugin

The owner's goal is one install instead of many tools. `bundle apply` does that for the owner's own host; this milestone makes the repository installable by anyone as a Claude Code plugin and marketplace. It adds files to the repository only: it writes no host configuration and installs nothing. The format facts are in [research-verify.md](research-verify.md). The scope was decided by Jev without consensus ([decisions.md](decisions.md)).

## Requirements

- R1 `.claude-plugin/plugin.json`: `name` `inonu-harness`, `version` equal to the package version, `description`, `author` `{"name": "Inonu Harness"}`, `homepage` and `repository` set to the public repository URL, and `keywords`. No `license` (the project declares none), no component keys (default discovery), no unknown top-level keys.
- R2 `.claude-plugin/marketplace.json`: `name` `inonu-harness`, `owner` `{"name": "Inonu Harness"}`, one plugin entry `{"name": "inonu-harness", "source": "./", "description": ...}` with no `version` in the entry (the manifest owns it).
- R3 Dual-use skill: `skills/inonu-harness/SKILL.md` calls the runner as `python "${CLAUDE_PLUGIN_ROOT}/scripts/inonu.py"`. In a plugin Claude Code expands the variable. `scripts/configure_hosts.py` and `bundle apply` replace that exact token with the rendered absolute runner command, so an installed copy contains no placeholder. Frontmatter stays `name` and `description` only; existing installer behavior and tests are preserved.
- R4 Worker agent: `agents/inonu-worker.md` keeps only frontmatter fields a plugin accepts (`name`, `description`, `model`) and `model: haiku`. Its body no longer names a runner path (the same bytes are copied to a user's agents directory by `bundle apply`, where no plugin variable expands): it tells the worker to run the verification command named by the ticket and report its exit code.
- R5 No `.mcp.json`, no `hooks/` directory, no `commands/` directory and no `bin/` at the repository root: the plugin starts no third-party server or hook. A test enforces this. MCP registration and the Stop hook stay in `bundle apply`, with preview, ledger and rollback.
- R6 Structural tests (`tests/test_plugin.py`) enforce the documented rules without the Claude CLI:
  - JSON parses with no duplicate keys;
  - `name` is kebab-case, free of reserved prefixes and words, and the marketplace name is not reserved;
  - `version` equals `inonu_harness.__version__` and the `pyproject.toml` version;
  - `homepage` parses as an https URL;
  - the marketplace entry name equals the manifest name, the source is `./` and resolves to the repository root;
  - only documented top-level manifest keys appear;
  - the agent and skill frontmatter use allowed fields only;
  - the plugin root carries `scripts/inonu.py` and `inonu_harness/__init__.py`;
  - R5 holds;
  - the skill body uses the placeholder prefix and no bare `python scripts/inonu.py`;
  - the rendered installer output has no `${CLAUDE_PLUGIN_ROOT}` left, for both hosts.
- R7 Docs: a `docs/plugin.md` reference (what it provides, what it deliberately omits, install and update commands, the unverified points) and short pointers in README, CHANGELOG 0.0.15 and the skill. They say the package was not run through `claude plugin validate` and should be before relying on it, that it needs Python 3.11+ reachable as `python` (the docs do not name the Windows launcher), and that it proves nothing about reachability or quality. Version 0.0.15.

## Out of scope

MCP servers, hooks, commands and monitors in the plugin; publishing to any directory or marketplace; running the Claude CLI; any host configuration.
