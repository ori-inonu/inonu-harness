# Native host profiles

Inonu provides a local skill profile for Codex and Claude Code. The installer is a standard-library Python script; Python 3.11 or later is required. It targets `~/.agents/skills/inonu-harness` for Codex and `~/.claude/skills/inonu-harness` for Claude Code. `scripts/configure_hosts.py` still changes no settings: it does not change global agent instructions, host settings, authentication, permissions, providers, hooks, or other skills. The separate `bundle apply --apply` command does write hook, MCP registration and worker agent entries into host configuration, but only after the owner's explicit authorization; see [Install the full bundle](#install-the-full-bundle).

## Preview and apply

From the repository root, preview both profiles (the default). Preview does not write files:

```powershell
python scripts/configure_hosts.py
```

Choose a host and apply only after reviewing the preview:

```powershell
python scripts/configure_hosts.py --host codex --apply
python scripts/configure_hosts.py --host claude --apply
```

`--host` accepts `codex`, `claude`, or `both`; `both` is the default. `--home PATH` roots the profile directories under a selected home and is useful for isolated preview or installation checks. Replace the placeholder with a temporary home path:

```powershell
python scripts/configure_hosts.py --host both --home "<temporary-home>"
```

The installer reports the version, selected host, and logical skill/ownership status without printing the home path or file content. A preflight conflict, such as an unmanaged profile or a file changed outside the installer, returns an error and writes nothing for the selected hosts. Reapplying an unchanged managed profile is idempotent. Profile ownership metadata stays beside the local skill files.

## Plan the full bundle

`python -m inonu_harness bundle plan [--host codex|claude|both] [--home PATH]` prints a read-only JSON plan. It lists the skill status using the same preview logic as this installer, plus, for Claude, a worker agent source, a stop-hook snippet that runs `hook stop` with a 630-second timeout, and complementary MCP server entries. The stop-hook item also carries a `note` that says what the hook does. The command writes nothing and applies nothing: every non-skill item reports `"applied": false`, and hook and MCP items also require owner authorization. Use `--home PATH` to inspect an isolated home tree. The snippet runs on every Stop event, but the hook checks a project only when that project's trusted verifier config exists; see [the hook reference](hook.md).

## Check what is installed

`python -m inonu_harness bundle status [--host codex|claude|both] [--home PATH]` reads the same items as `bundle plan` and adds a `state` to each: the skill is `current`, `absent`, `outdated` or `conflict`; the worker agent is `current`, `different` or `absent`; the Stop hook is `present` or `absent` (an earlier registration ending in ` check` also counts as `present`); MCP entries are `configured` or `absent`. Any file that cannot be read or parsed reports `unknown`. The command writes nothing, prints no file contents or setting values, and exits 0 for a report; a `SKILL.md` that cannot be read is reported as `unknown` here and in `bundle plan`. A `configured` MCP entry only means the key exists in the host configuration; reachability is not probed.

Each item also gets an `ownership` value, compared with the ownership ledger that `apply` writes: `ours` (recorded and unchanged), `modified` (recorded, but edited or deleted since), `foreign` (installed, not recorded), `none` (neither) or `unknown` (the ledger, or that item's host file, cannot be read or parsed). `modified` also covers an item the user deleted. The report adds a top-level `ledger` (`absent`, `present` or `unreadable`) and an `ownership_summary` with a count per value. An unreadable ledger (including an empty file or a `schema_version` that is not the integer 1) makes every item `unknown`; a malformed or unreadable host file makes only its own items `unknown`. The Claude MCP entry and the Stop hook group are compared as canonical JSON, so key order and spacing do not matter; the skill, the worker agent and the Codex block are compared as exact bytes, so changed line endings count as `modified`. A Codex server is `ours` only if no table outside its markers changes it. The skill's `ownership` looks at `SKILL.md` alone, while its `state` also checks the metadata file. Ownership is advisory and read-only: it does not change what `apply` or `remove` do.

## Install the full bundle

`python -m inonu_harness bundle apply [--host codex|claude|both] [--home PATH] [--with-stop-hook] [--apply]` previews the bundle by default and writes nothing. With `--apply` it writes the skill profile, the Claude worker agent (`~/.claude/agents/inonu-worker.md`), the complementary MCP entries, and, only when `--with-stop-hook` is given, the Stop hook. The stop hook is opt-in: on every Stop it runs the trusted verifier config of the current project, if there is one, and it can block the stop when a check fails. See [the hook reference](hook.md) for trust and exit codes. An earlier registration ending in ` check` conflicts with apply; `bundle remove` reverses it when the ledger recorded it, and apply then adds the current one. `bundle remove` uses the same flags and reverses the items.

Each apply writes an ownership ledger (hashes, plus what the run created) and backs up the original file before a change. The write is all-or-nothing: if a file changes mid-run, a write fails or the process is interrupted, the files already written are restored and the report shows `failed` or `conflict` with `rollback`. Backups of files that existed before are kept in `~/.inonu-harness/backups` and remove does not delete them; remove restores the parsed content of JSON files, not their original formatting. Re-running an unchanged apply reports `unchanged`. Remove reverses only items whose hash still matches the ledger and deletes only what apply created; a user-modified item, or a Codex block with changed line endings, is reported as `conflict` and kept. An existing user MCP entry with the same id is never overwritten. A missing launcher is reported as `tool_missing`; launchers are resolved only from absolute `PATH` entries, never from the current directory. A preflight conflict exits 2 and writes nothing. The output is JSON without file contents, settings values or personal paths.

Limits: a host that writes its own configuration at the same moment can lose an edit in the short window between re-reading and replacing a file. `configured` only means the key exists, not that the server is reachable. The command does not install CodeGraph, Headroom or Node. Owner authorization for these writes is recorded in `docs/specs/milestones/v0.0.11/decisions.md` (D2).

## Run the CLI from another directory

The installed skill contains the absolute runner path from the checkout used during installation. It quotes that path for PowerShell on Windows Codex and for Bash/POSIX shells on Claude Code. To invoke it manually from another working directory, substitute the checkout and project locations below; keep the path quoted if it contains spaces.

PowerShell:

```powershell
& python '<checkout>\scripts\inonu.py' doctor --project-root '<selected-project>'
```

Bash or another POSIX shell:

```sh
python '<checkout>/scripts/inonu.py' doctor --project-root '<selected-project>'
```

Omit `--project-root` to inspect the checkout associated with the runner. The same runner exposes the existing `baseline`, `decisions`, and `sdd audit` commands. Their inputs and effects remain explicit; see the [README](../README.md) and [SDD workflow](sdd-workflow.md).

## Use the profile in Claude Desktop

The target is a local session in Claude Desktop's **Code** tab. After previewing, apply the Claude profile from the repository checkout. In Claude Desktop, open the Code tab, choose **Local** as the environment, and select the repository folder for the session. Local Code sessions load personal skills from `~/.claude/skills` and share Claude Code's `~/.claude/settings.json` and `~/.claude.json`; `configure_hosts.py` writes none of those settings files (`bundle apply --apply` may, see [Install the full bundle](#install-the-full-bundle)). Chat and Cowork do not load this local skill directory; enable account skills through **Customize** if you need them there.

In a local Code session, confirm `inonu-harness` appears in the Skills menu opened from the prompt's **+** menu, then invoke `/inonu-harness` and ask it to run the doctor for the selected repository. The profile file or a successful installer result alone does not prove that the active Desktop session loaded or invoked it. See the official [Claude Desktop shared configuration](https://code.claude.com/docs/en/desktop#shared-configuration), [Claude Desktop use skills](https://code.claude.com/docs/en/desktop#use-skills), and [Claude Code skill locations](https://code.claude.com/docs/en/skills).

Codex detects skill changes automatically; restart Codex if the skill does not appear. In Claude Code, local skill files are watched during a session; if the top-level skills directory did not exist when the session started, run `/reload-skills` or restart. See the official [Codex skill guide](https://learn.chatgpt.com/docs/build-skills) and the Claude Code skill lifecycle documentation linked above.

## Moving the checkout and checking limits

The profile embeds paths to the runner and its documentation. After moving the checkout, run `python scripts/configure_hosts.py --apply` from the new checkout for each selected host. The helper can update a profile it manages; if it finds a conflict, inspect the local profile before changing it.

The script applies a local user skill profile only. It does not register tools or plugins, configure authentication, or prove that a host session can reach an MCP server. Verify each state separately: the profile files exist, the host lists the skill, and a local session successfully invokes it. A loaded skill does not establish tool reachability or performance.

Inonu complements other tools: it does not provide CodeGraph symbol navigation, RTK terminal output filtering, Headroom context compression, or Ponytail coding guidance. No real-task benchmark establishes that Inonu alone replaces those capabilities.
