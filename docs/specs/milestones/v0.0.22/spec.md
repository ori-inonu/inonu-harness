# v0.0.22 — Ownership in `bundle status`

The source-level research ([v0.0.20 research](../v0.0.20/research-reverse-engineering.md), gap G2) found that ECC and spec-kit tell apart "ours and unchanged", "changed by the user" and "not ours" before they touch a host file. `bundle status` cannot: it never reads the ownership ledger, so an MCP entry the user edited and the entry the bundle wrote both show as `configured`. This milestone adds that distinction as extra, read-only information. It changes no schema and no write path. The scope was decided by Jev without consensus ([decisions.md](decisions.md)).

## Requirements

- R1 `python -m inonu_harness bundle status` keeps every existing key and value. It adds:
  - `ownership` on every item;
  - a top-level `ledger`: `"absent"` (no ledger file), `"present"` or `"unreadable"` (see R4);
  - a top-level `ownership_summary`: a count per ownership value, like `summary` does for `state`.
- R2 `ownership` is one of:
  - `ours`: the item is recorded in the ledger and what is installed now has the recorded digest;
  - `modified`: the item is recorded in the ledger but what is installed now differs from the recorded digest, or the item is gone;
  - `foreign`: the item is installed but not recorded in the ledger;
  - `none`: the item is not installed and not recorded;
  - `unknown`: see R4.
- R3 What is compared, mirroring what `bundle apply` records (ledger key `<kind>:<host>:<id>`, the same keys as today):
  - skill: the digest of the installed `SKILL.md` for that host. An outdated skill the bundle wrote is still `ours`; a skill edited by the user is `modified`;
  - worker agent: the digest of `~/.claude/agents/inonu-worker.md`;
  - Claude MCP server: the digest of the canonical JSON of that server's entry in `~/.claude.json`;
  - Codex MCP server: the digest of the marked `# >>> inonu-harness mcp <id>` block of `~/.codex/config.toml`. A server table with no marked block is `modified` if the ledger records the server and `foreign` otherwise. The server is `ours` only if the table that the whole file defines for it equals the one its marked block defines alone, so a table or sub-table added outside the markers makes it `modified`;
  - Stop hook: the digest of the canonical JSON of any group under `hooks.Stop` of `~/.claude/settings.json`; if none matches, the hook is `modified` when recorded, `foreign` when a group that runs `inonu.py` exists, and `none` otherwise.
  Any digest function already used by `bundle apply` is reused, not copied.
- R4 `unknown`: the ledger is malformed (wrong schema, including a `schema_version` that is `true` or `1.0`; bad hash; an empty file; a symbolic link; a directory in the way; unreadable) — then `ledger` is `"unreadable"` and every item is `unknown` — or the host file for that item is malformed or unreadable (a skill file too, so `bundle plan` and `bundle status` report it as `unknown` instead of exiting 2). Status still exits 0 and never raises.
- R5 `bundle status` stays read-only: the home directory is byte-identical afterwards (no ledger, no backup, no directory created). The output never contains file contents, the home path, or a secret planted in a host file.
- R6 Tests build the installed state with the real `bundle apply --apply` into a temporary home (fake launchers on `PATH` the way `tests/test_bundle_apply.py` does), not by hand-writing ledger digests. They cover, for the skill (both hosts), the worker agent, a Claude MCP entry, a Codex MCP entry and the Stop hook:
  - `ours` right after apply;
  - `modified` after the user edits the item, and after the user deletes it;
  - `foreign` when the item exists with no ledger, and a different server the user added next to ours stays out of the report (only the bundle's own ids are reported);
  - `none` on an empty home;
  and also: an outdated skill the bundle wrote is `ours`; a malformed, symbolic-link and wrong-schema ledger give `ledger: "unreadable"` and `unknown` everywhere; a malformed host file gives `unknown` for its items only; the summaries add up; the home is unchanged; no secret or home path in the output; existing `state` values and `summary` unchanged. The existing status tests keep passing without edits except version strings.
- R7 Docs: CHANGELOG 0.0.22, README, `docs/hosts.md` (the bundle status section), a skill bullet. They state the five values, that `ownership` is advisory and read-only, that it does not change what `apply` or `remove` do, and that `modified` also covers an item the user deleted. Version 0.0.22 in `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and the version assertions in the tests.

## Out of scope

A new ledger schema, verbatim entry copies and post-write digests (they would migrate the owner's ledger; recorded as deferred in [decisions.md](decisions.md)), changing the `state` values, making `apply` or `remove` act on ownership, the worker agent `tools` allowlist, and repairing a drifted item.
