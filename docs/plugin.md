# Claude Code plugin

This repository is a Claude Code plugin and its own marketplace. This page states what the plugin provides, what it leaves out and why, how to install and update it, and what has not been verified. It does not claim that the installation has been validated, that Inonu works better than other tools, or that the plugin is listed in any directory.

## What the plugin provides

- **Skill** `inonu-harness` (`skills/inonu-harness/SKILL.md`). It documents the runner commands: `check`, `bundle plan` and `bundle status`, `hook trust`, `doctor`, `baseline`, `decisions` and `sdd audit`. The skill calls the runner as `python "${CLAUDE_PLUGIN_ROOT}/scripts/inonu.py"`. The plugin docs say Claude Code expands that variable in skill bodies; this has not been observed in a session.
- **Worker agent** `inonu-worker` (`agents/inonu-worker.md`, `model: haiku`). It completes one bounded ticket, runs the verification command that the ticket names, and reports that command's exit code. It is not a planner and does not coordinate other agents.
- **Python runner**: `scripts/inonu.py` and the `inonu_harness/` package, both at the plugin root. The runner adds the root to `sys.path` and calls the CLI, so it works from any working directory. It uses only the Python standard library; `pyproject.toml` declares no dependencies.
- **Manifests**: `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

Git-based marketplace plugins are copied into a local cache when installed. The plugin therefore carries its own runner and package instead of pointing at this checkout.

`bundle apply` and `scripts/configure_hosts.py` copy the same skill file into user directories. In those copies they replace the `${CLAUDE_PLUGIN_ROOT}` token with the absolute runner command, so the copies contain no placeholder.

## What it deliberately omits

- **MCP servers (`.mcp.json`).** The plugin docs read on 2026-10-26 do not describe an approval prompt before the MCP servers of an enabled marketplace plugin start. The servers Inonu would register run third-party code, such as `npx` packages.
- **Hooks (`hooks/`).** The docs describe no approval step for a user-scope plugin hook, so the plugin ships no hook. The Stop hook (`hook stop`) that the bundle can register runs on every Stop, and it runs checks only in a project whose `.inonu/verify.json` the owner trusted with `hook trust --yes`; it stays opt-in. See [the hook reference](hook.md).
- **Commands, monitors and `bin/`.** Out of scope for this version.

These components stay an explicit, previewed action. `bundle apply --host claude` previews by default and writes nothing. With `--apply` it writes the skill profile, the worker agent and the MCP entries. `--with-stop-hook` adds the Stop hook, which runs the project's trusted verifier config and nothing else; see [the hook reference](hook.md). Each run keeps an ownership ledger and backups and rolls back a failed run. `bundle remove` reverses what apply created. See [native host profiles](hosts.md#install-the-full-bundle).

## Requirements

- Python 3.11 or later, reachable as `python` from the shell that Claude Code uses.
- The plugin docs do not name the Python launcher for Windows (`python`, `py` or `python3`). This page does not verify which one works there. If `python` is missing or older than 3.11, the runner command fails.
- A Claude Code version with plugin support. The minimum version that accepts every manifest and agent field is not verified.
- No Python packages to install.

## Install

In Claude Code:

```text
/plugin marketplace add ori-inonu/inonu-harness
/plugin install inonu-harness@inonu-harness
```

The repository is the marketplace. Its single plugin entry uses `source: ./` and has no `version`; the plugin manifest owns the version.

A git-hosted marketplace is copied from **committed** files. Every file the package needs (the manifests, `skills/`, `agents/`, `scripts/`, `inonu_harness/` and `docs/`) must be committed and pushed before `/plugin marketplace add` from GitHub can install it. Adding the repository from a local path instead loads the working tree in place, which is how to try changes before committing (`/plugin marketplace add ./` from the checkout).

Before you rely on the package, run the validator from a checkout of this repository:

```text
claude plugin validate .
```

This validation has not been run for this package. See [Not verified](#not-verified).

## Before you push

The plugin installs from committed files, and a working-tree check cannot see a module that was never committed. Commit first, then verify that commit in an isolated export, from the checkout:

```text
python -m inonu_harness check --ref HEAD
```

The command writes the commit's own blobs, read with `git ls-tree` and `git cat-file`, to a temporary directory (so `export-ignore`, `export-subst` and line-ending settings cannot hide or alter a committed file), runs the compile step, the version comparison, the unit tests and `scripts/inonu.py --version` there, and removes the export. Exit 0 means every step passed for that commit. Uncommitted edits do not affect the result. The check covers the operating system where it runs only, and the CI workflow is unchanged in this release.

A pass shows that the commit is self-contained for its tests and its runner. It does not show that the plugin installs or that a host loads it; see [What passing checks do not establish](#what-passing-checks-do-not-establish).

## Update and version pinning

`version` in `.claude-plugin/plugin.json` equals the package version (a structural test enforces it). Per the plugin docs as read on 2026-10-26, when `version` is set, an installed user stays on the cached copy until that string changes. Without `version`, the plugin would follow new commits instead.

A release edits the version in these three manifests: `.claude-plugin/plugin.json`, `pyproject.toml` and `inonu_harness/__init__.py`. The structural tests require all three to match. The `versions` step of `check` compares them too, requires the version to be in the milestone scheme (see [versioning](versioning.md)), and also compares `.claude-plugin/marketplace.json` when that file states a version. Update an installed copy with your Claude Code plugin manager. This page does not verify a specific update command.

## Not verified

- `claude plugin validate .` has not been run. No `claude` CLI was available when the plugin format was checked on 2026-10-26.
- No live installation test. The install commands, the skill, the worker agent and the runner have not been exercised through an installed plugin.
- The Windows launcher. Whether `python` is the right command on Windows is not established.
- Variable expansion. That Claude Code expands `${CLAUDE_PLUGIN_ROOT}` in the skill body comes from the docs text, not from an observed session.
- Version pinning and the update command come from the docs text and have not been tested.
- Coexistence. The plugin docs namespace every plugin component under the plugin name, so the plugin's skill and agent should not collide with a user-level `inonu-harness` skill or `inonu-worker` agent installed by `bundle apply`. This has not been tested in a live session.
- Cache contents. The installed plugin is a cached copy of the repository. The skill's documentation links and the installer rewrite need `docs/` (and the Python package and `scripts/`) to be present in that copy, which holds when the whole repository is the plugin root. The exact cache layout was not observed.
- Root `CLAUDE.md`. The plugin docs say a `CLAUDE.md` at a plugin root is not loaded as context and that `claude plugin validate` warns about it. This repository keeps a short `CLAUDE.md` for its own development sessions, so expect that warning; it does not affect the skill or the agent.
- Field support. Whether the user's Claude Code version accepts every manifest and agent field used here.
- Source quality. The format facts were read from official pages through model-based extraction, not raw HTML. See [research-verify.md](specs/milestones/v0.0.15/research-verify.md).

## What passing checks do not establish

The structural tests in `tests/test_plugin.py` check the files against the documented rules without the Claude CLI. They do not establish that the plugin installs, that a host discovers the skill or agent, that the runner is reachable from a session, or that the worker's output is good. Nothing here shows that Inonu is better than CodeGraph, RTK, Headroom or Ponytail. The plugin is not listed in any official or community directory.
