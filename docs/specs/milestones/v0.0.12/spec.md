# v0.0.12 — Bundle apply and remove

The owner authorized on 2026-10-26 writing the hook, the MCP registrations and the worker agent into their Claude and Codex configuration, with preview, ownership hashes and reversal (see [v0.0.11 decisions](../v0.0.11/decisions.md), D2). This milestone turns the v0.0.10 plan and the v0.0.11 status into a single install and uninstall.

## Requirements

- R1 Commands: `python -m inonu_harness bundle apply [--host codex|claude|both] [--home PATH] [--with-stop-hook] [--apply]` and `bundle remove [same flags]`. Without `--apply` the command is a preview and writes nothing. Output is one JSON object with `mode` (`preview` or `apply`), `action` (`apply` or `remove`), `version` and `items`. Each item has `kind`, `host`, `id` where relevant, a logical `~/` target and a `result`. No file contents, settings values, environment values or absolute personal paths are printed.
- R2 Preflight everything first. If any selected item is a `conflict`, print the report, write nothing and exit 2. Otherwise exit 0. Running the same `apply --apply` twice gives `unchanged` for every item the second time (idempotent).
- R3 Items and apply rules:
  - `skill` (both hosts): reuse `host_profiles` preflight and apply. Results: `would_install`/`installed`, `would_update`/`updated`, `unchanged`, `conflict`.
  - `worker-agent` (Claude): write `agents/inonu-worker.md` to `~/.claude/agents/inonu-worker.md`. If the target is missing, install. If it is byte-identical, `unchanged`. If it is managed (its hash is in the ledger) but outdated, update. Otherwise `conflict`.
  - `mcp` (both hosts, ids `codegraph`, `headroom`, `sequential-thinking`): register only when the id is absent. An existing entry with that id that is not ours is `unchanged` (never overwritten). The launcher must be on `PATH` (an absolute-`PATH`-only lookup, `_find_executable`, of `codegraph`, `headroom`, `npx`), otherwise the result is `tool_missing` and the item is skipped, which is not a conflict. Launch commands: `codegraph mcp serve --root . --stdio --no-warmup`, `headroom mcp serve`, `npx -y @modelcontextprotocol/server-sequential-thinking`. Resolve launchers only through absolute `PATH` entries (never the current directory or a relative entry). When the resolved launcher is a `.cmd` or `.bat` file, use `command: "cmd"` with `args: ["/c", <absolute path>, ...]`; otherwise use the resolved absolute executable path.
    - Claude: add the entry `{"type": "stdio", "command": ..., "args": [...], "env": {}}` under the top-level `mcpServers` of `~/.claude.json`, preserving every other key.
    - Codex: append to `~/.codex/config.toml` a block delimited by `# >>> inonu-harness mcp <id>` and `# <<< inonu-harness mcp <id>`, containing `[mcp_servers.<id>]` with `command` and `args`. Strings are encoded as TOML basic strings. Parse the whole new text with `tomllib` before writing, and treat a parse failure as a `conflict`.
  - `stop-hook` (Claude, only with `--with-stop-hook`; otherwise `result: "not_selected"`): append `{"hooks": [{"type": "command", "command": <runner check command>}]}` to `hooks.Stop` in `~/.claude/settings.json`, creating keys as needed. The runner command uses `host_profiles.render_runner_command` for the Claude host. The runner path in the local file is acceptable; it is never printed.
- R4 Ownership ledger at `~/.inonu-harness/bundle-ledger.json` (schema_version 1). It records, per item key, the SHA-256 of the canonical JSON (`sort_keys`, compact) of each inserted JSON entry, or of the exact bytes of each written file or TOML block. Merge edits are made on parsed JSON. Writes are atomic (temp file plus `os.replace`). Immediately before replacing a shared config file, re-read it; if its hash changed since preflight, abort that item as a `conflict`.
- R5 Backup: before the first modification of an existing config file in a run, copy it to `~/.inonu-harness/backups/<file-name>.<sha256[:12]>` unless that file already exists.
- R6 Remove reverses only what the ledger proves is ours and unchanged:
  - Delete the worker agent file only if its hash matches the ledger.
  - Delete the skill files only if they match the skill ownership metadata, and remove the profile directory if it is then empty.
  - Delete a JSON entry only if its canonical hash matches the ledger; Claude's `mcpServers` entries and `hooks.Stop` entries are deleted that way.
  - Delete a Codex marker block only if its bytes match the ledger.
  - A changed item gets `result: "conflict"` and stays in place.
  - Remove the ledger entries for removed items.
  - Results: `would_remove`/`removed`, `absent`, `conflict`.
- R7 Tests use only an isolated temp `--home` and a fake `PATH`, built from stub executables in a temp dir and patched via `unittest.mock.patch.dict(os.environ)` or by patching `_find_executable`. They must cover:
  - preview writes nothing;
  - apply then apply again gives `unchanged`;
  - apply then remove restores a pre-existing `~/.claude.json` and `config.toml` to exactly the original parsed content, and the original bytes for a file that did not exist (absent again);
  - a user-modified entry makes remove report `conflict` and keep it;
  - an existing user entry with the same MCP id is never overwritten;
  - `tool_missing` when no launcher is found;
  - the stop hook is absent unless `--with-stop-hook` is given;
  - malformed `settings.json` gives `conflict` and nothing is written;
  - concurrent modification between preflight and write gives `conflict`;
  - stdout contains neither the temp home path nor a planted secret value from an existing config.
- R8 `bundle status` (v0.0.11) keeps working and reflects applied items. Docs (CHANGELOG 0.0.12, README, `docs/hosts.md`, skill) describe the commands, the preview-first flow, the ledger, the backups, the race limit (a host writing its config concurrently can still lose an edit inside the tiny window between re-read and replace), and that `configured` does not mean reachable. Version 0.0.12.

## Out of scope

Installing the tools themselves (codegraph, headroom, node); credentials or env values in MCP entries; project-scope `.mcp.json`; Codex agent files.

## Revision after the first independent reviews

Two independent reviews of the first implementation found defects, and these were added as requirements:

- R9 A failed or interrupted write is rolled back. Before writing, snapshot each path; if a file changes mid-run or a write raises `OSError`, restore the files already written (unlink those that did not exist). The report marks write results `failed` (error) or `conflict` (outside change), adds `rollback: complete|incomplete`, and exits 2.
- R10 The ledger also records `created` markers (`file:`, `dir:`, `key:`). Remove deletes only files, directories and JSON containers that apply created; pre-existing empty files, containers and directories are preserved.
- R11 A conflict found in preflight reports `would_*` results even with `--apply`, because nothing was written.
- R12 A Codex marker block is matched with CR LF or LF line endings. If the server is still configured but its block cannot be matched or its hash differs, remove reports `conflict` and keeps it.
- R13 JSON that contains non-finite numbers is a conflict and is not rewritten.
- R14 `bundle status` recognizes the Stop hook command that apply writes (`is_check_command`).
