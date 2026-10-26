# v0.10.0 — Verification gate and read-only bundle plan

The owner's goal is a single Inonu install that gives the whole harness instead of many separate tools. [research.md](research.md) maps the gap; Jev recommended this slice (see [decisions.md](decisions.md)). This milestone adds a deterministic gate and a read-only plan of the full bundle. It writes nothing outside the checkout.

## Requirements

- R1 `check`: `python -m inonu_harness check [--root PATH]` runs, with `cwd` = root (default: this checkout), `python -m compileall -q` over the root's existing `inonu_harness`, `scripts` and `tests` directories, then `python -m unittest discover -s tests` (the same command CI runs). Child output goes to stderr. Stdout is one JSON object `{"schema_version": 1, "passed": bool, "steps": [{"name": "compile"|"tests", "exit_code": int}]}`. Exit 0 only when every step exits 0, otherwise 1; a root without a `tests` directory is invalid input (exit 2). A failing compile still runs the tests step so both results are reported.
- R2 `bundle plan`: `python -m inonu_harness bundle plan [--host codex|claude|both] [--home PATH]` (default `both`) prints one JSON object and writes nothing. `items` lists, per selected host:
  - `skill` — the existing native skill, with the status the v0.9 installer preview reports (`would_install`, `would_update`, `unchanged` or `conflict`), reusing `host_profiles` rather than duplicating it.
  - `worker-agent` (Claude only) — source `agents/inonu-worker.md`, logical target `~/.claude/agents/inonu-worker.md`, `"applied": false`.
  - `stop-hook` (Claude only) — a settings snippet whose command runs the installed runner's `check`, `"applied": false`, `"requires_owner_authorization": true`.
  - `mcp` — one entry per complementary server id (`codegraph`, `headroom`, `sequential-thinking`), `"applied": false`, `"requires_owner_authorization": true`, `"accessibility": "unknown"`. No credentials, env values or tokens.
  Output contains no absolute personal paths (targets use `~/`); the hook snippet may reference the runner as `<checkout>/scripts/inonu.py`. A preflight error exits 2 like the installer.
- R3 Worker agent source: `agents/inonu-worker.md` is a Claude Code subagent definition with frontmatter `name: inonu-worker`, a `description`, and `model: haiku`. Its body instructs one bounded ticket, no nested delegation, no Jev calls, return evidence and run `check` before claiming done. A test parses the frontmatter and fails if `model` is not `haiku`.
- R4 Console entry: `pyproject.toml` declares `[project.scripts] inonu = "inonu_harness.cli:main"`; a test reads it with `tomllib` and asserts the target is callable. No dependency added.
- R5 Docs and version: version 0.10.0 in `__init__.py`, `pyproject.toml` and tests; CHANGELOG entry; README, `docs/hosts.md`, `docs/sdd-workflow.md` and the source skill describe `check` and `bundle plan` with their limits (plan applies nothing; hook/MCP/agent installation is a later, owner-authorized milestone).
- R6 Verification: full suite passes; `check` on this checkout exits 0; isolated-home test proves `bundle plan` leaves the home tree byte-identical; a temp-root test proves `check` exits 1 for a failing test and for a syntax error.

## Out of scope

Writing any host setting, hook, MCP registration or agent file; loop runner; Decision Graph schema change; license choice. These touch fenced global configuration or later roadmap items.
