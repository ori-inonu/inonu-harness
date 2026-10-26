# v0.15.0 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed, **and the plugin cannot be installed from GitHub until it is**: a git-hosted marketplace copies committed files only, and the manifests plus several modules and documents added since v0.10.0 are untracked. This milestone does not complete the broader single-install objective.

## Flow

- Format research: three Haiku workers read the official plugin, marketplace and trust documentation ([research-verify.md](research-verify.md)). No `claude` CLI exists on this host, so `claude plugin validate` was **not** run.
- Scope: Jev returned `sem_consenso` ([decisions.md](decisions.md) D1). The most reversible option was adopted: manifests, a dual-use skill and the worker agent, with no MCP servers and no hooks (their rail probabilities were 1.00 and 0.89: the docs describe no approval step before a plugin's MCP servers start).
- A Haiku worker built the package and tests (T01) and another the docs (T02); an independent Haiku reviewer then checked them (T03). There were no P1 findings.
- Review findings and the coordinator's resolution:
  - P2, the skill lacked the pointer to `docs/plugin.md` that R7 requires. Added, with a test.
  - P2, the skill's documentation links and the installer rewrite need `docs/` present in the cached copy. A test now requires every linked document to exist inside the repository, and the docs state the cache layout was not observed.
  - P2, a release precondition: the new files are untracked, and the tracked `cli.py` imports untracked modules. Recorded above and in the docs.
  - P3: a missing top-level marketplace `description` (added and tested), partial reserved-name coverage (the "official beside claude" rule is now implemented and tested), an overstated coexistence claim (reworded around component namespacing), and the root `CLAUDE.md` that `claude plugin validate` warns about (documented).
- A mutation check broke the package in 12 ways in temporary copies, from a changed version to an added `.mcp.json` and an installer that leaves the placeholder in; the suite failed each time.

## Verification

- `python -m unittest discover -s tests`: exit 0, 231 tests, 3 POSIX-only skipped.
- `python -m inonu_harness check`: exit 0.
- `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: the skill (rewritten from the placeholder) and the worker agent were updated; the installed copies contain no `${CLAUDE_PLUGIN_ROOT}`.

## Limits

- Not run: `claude plugin validate .`, a live plugin install, variable expansion in a real session, the Windows launcher name, coexistence with a `bundle apply` profile.
- The plugin starts no MCP server and no hook; those stay in `bundle apply`.
- A passing structural test establishes neither installation, reachability nor agent quality.

## Next

Commit the work so the plugin and the CI become testable (needs the owner's go-ahead), then run `claude plugin validate .` on a machine that has the Claude CLI.
