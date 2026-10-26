# Native host profiles

Inonu provides a local skill profile for Codex and Claude Code. The installer is a standard-library Python script; Python 3.11 or later is required. It targets `~/.agents/skills/inonu-harness` for Codex and `~/.claude/skills/inonu-harness` for Claude Code. It does not change global agent instructions, host settings, authentication, permissions, providers, hooks, or other skills.

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

The target is a local session in Claude Desktop's **Code** tab. After previewing, apply the Claude profile from the repository checkout. In Claude Desktop, open the Code tab, choose **Local** as the environment, and select the repository folder for the session. Local Code sessions load personal skills from `~/.claude/skills` and share Claude Code's `~/.claude/settings.json` and `~/.claude.json`; this installer writes none of those settings files. Chat and Cowork do not load this local skill directory; enable account skills through **Customize** if you need them there.

In a local Code session, confirm `inonu-harness` appears in the Skills menu opened from the prompt's **+** menu, then invoke `/inonu-harness` and ask it to run the doctor for the selected repository. The profile file or a successful installer result alone does not prove that the active Desktop session loaded or invoked it. See the official [Claude Desktop shared configuration](https://code.claude.com/docs/en/desktop#shared-configuration), [Claude Desktop use skills](https://code.claude.com/docs/en/desktop#use-skills), and [Claude Code skill locations](https://code.claude.com/docs/en/skills).

Codex detects skill changes automatically; restart Codex if the skill does not appear. In Claude Code, local skill files are watched during a session; if the top-level skills directory did not exist when the session started, run `/reload-skills` or restart. See the official [Codex skill guide](https://learn.chatgpt.com/docs/build-skills) and the Claude Code skill lifecycle documentation linked above.

## Moving the checkout and checking limits

The profile embeds paths to the runner and its documentation. After moving the checkout, run `python scripts/configure_hosts.py --apply` from the new checkout for each selected host. The helper can update a profile it manages; if it finds a conflict, inspect the local profile before changing it.

The script applies a local user skill profile only. It does not register tools or plugins, configure authentication, or prove that a host session can reach an MCP server. Verify each state separately: the profile files exist, the host lists the skill, and a local session successfully invokes it. A loaded skill does not establish tool reachability or performance.

Inonu complements other tools: it does not provide CodeGraph symbol navigation, RTK terminal output filtering, Headroom context compression, or Ponytail coding guidance. No real-task benchmark establishes that Inonu alone replaces those capabilities.
