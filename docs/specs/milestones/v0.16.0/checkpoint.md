# v0.16.0 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Research gap closed: the OpenAI "harness engineering" page, which returned HTTP 403 to every fetch route, was read in full through the app's built-in browser in read-only mode ([research-verify.md](research-verify.md)). Its findings that bear on this project: a short instruction file as an index, mechanical verification of documentation, lint messages that carry remediation text, and architecture enforced by structural tests.
- Scope: Jev consensus, unanimous, for a documentation lint plus a structural test ([decisions.md](decisions.md) D1). A documentation-gardening agent scored a rail probability of 0.99 because it would make Inonu run agents.
- A Haiku worker built the lint and the architecture test (T01) and another the docs (T02); an independent Haiku reviewer then tried to break them (T03).
- Review findings and the coordinator's resolution:
  - P1, a miss of mine: `.claude-plugin/plugin.json` stayed at 0.15.0 while the package moved to 0.16.0, which turned the unit suite and `check` red. The plugin version test written in v0.15.0 caught it. Fixed; the prose no longer repeats the version number, since a test already forces the three version strings to agree.
  - P2, fences nested in list items or block quotes were linted as prose, and a line like "```x``` text" opened a fence that hid every later link. Both fixed in a rewritten lint module.
  - P2, the architecture test skipped subpackages, let `scripts/inonu.py` import the CLI without saying so, and could not see `__import__`, `importlib.import_module`, `exec` or `eval`. Fixed; the runner exemption is now stated in the spec, the architecture notes and the changelog.
  - P3: `inonu_harness.__main__` ran the CLI on import (now guarded and forbidden as an import target for lower modules), links with balanced parentheses or `<...>` targets, CR-only line endings, a quadratic rescan on long lines, case and backslash targets that only resolve on some hosts, directory links and junctions, and test gaps for sorting and nested imports.
- Two of my own new tests found real defects during the fixes: an unbounded scan of a link target was quadratic (7.7 s on a pathological line, now capped at 1024 characters), and the resolution cache keyed by `Path` ignored case on Windows, which hid wrong-case links.
- A mutation check broke the lint and the architecture test in 16 ways in temporary copies; the suite failed each time. One mutant first survived because the directory-link test was skipped for lack of a symlink privilege; it now uses a Windows junction as a fallback and the mutant is caught.

## Verification

- `python -m unittest discover -s tests`: exit 0, 282 tests, 4 skipped (three POSIX-only, one file-symlink case that needs a privilege this host lacks).
- `python -m inonu_harness check`: exit 0.
- `python -m inonu_harness docs lint` on this repository: pass, 93 files, no findings.
- `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: both skills updated.

## Limits

- The lint checks links, size and imports only. It does not check whether a document is true or current, heading anchors, links that span lines, escaped brackets, indented (non-fenced) code, nested instruction files or absolute local paths.
- The 200-line limit is a configurable starting point; the 32768-byte limit is the documented Codex default. The research source is a vendor's own account without independent evaluation.
- Not run: the POSIX path (no Linux here), a file symlink escaping the root.

## Next

Commit the work so the plugin and CI become testable (the owner's go-ahead is needed), then run `claude plugin validate .` and the Linux CI. Candidate unblocked work: a secret-pattern scan for decision packets, and the entropy idea from the OpenAI source as a deterministic drift report rather than an agent.
