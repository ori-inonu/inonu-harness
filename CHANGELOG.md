# Changelog

Notable changes to the Inonu Harness, newest first. Each version below has a [GitHub release](https://github.com/ori-inonu/inonu-harness/releases) with the same notes.

Versions follow the milestone scheme of [docs/versioning.md](docs/versioning.md): a project starts at `0.0.1`, each milestone raises the patch number, minor and patch have at most two digits (so `0.1.0` follows `0.0.99`), and `1.0.0` is the owner's decision. This repository's first 24 milestones were numbered `v0.N.0` while they were built and were renumbered to `v0.0.N`; the Git history, Jev spec ids and receipts keep the old numbers, and the table in the versioning guide translates them.

A release tag marks the **first commit that contains the milestone's folder**. Several early milestones were committed together, so their tags share a commit; the notes of each release say so.

Sections: **Added** (new behaviour), **Changed** (existing behaviour or rules), **Fixed**, and **Limits** (what the change does not establish or does not cover).

## Releases at a glance

| Version | First committed | Summary | Release |
| --- | --- | --- | --- |
| [0.0.26](#0026--2026-10-26) | 2026-10-27 | `milestone close` and `MILESTONES.md`, the index of closed milestones. | [v0.0.26](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.26) |
| [0.0.25](#0025--2026-10-26) | 2026-10-27 | `milestone new` and `milestone check`, and a `milestones` step in `check`. | [v0.0.25](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.25) |
| [0.0.24](#0024--2026-10-26) | 2026-10-26 | The `v0.0.N` milestone scheme, a manifest version check and SKILL.md size limits. | [v0.0.24](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.24) |
| [0.0.23](#0023--2026-10-26) | 2026-10-26 | `jev spec` sends a document's text as the judge's facts. | [v0.0.23](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.23) |
| [0.0.22](#0022--2026-10-26) | 2026-10-26 | An `ownership` value per item: ours, modified, foreign, none or unknown. | [v0.0.22](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.22) |
| [0.0.21](#0021--2026-10-26) | 2026-10-26 | `decisions ready` lists pending decisions whose dependencies are authorized. | [v0.0.21](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.21) |
| [0.0.20](#0020--2026-10-26) | 2026-10-26 | An opt-in `hook stop` that runs a trusted verifier config and can block a stop. | [v0.0.20](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.20) |
| [0.0.19](#0019--2026-10-26) | 2026-10-26 | `--refuse-secret-patterns` for decision context and task packets. | [v0.0.19](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.19) |
| [0.0.18](#0018--2026-10-26) | 2026-10-26 | `decisions as-of` shows a decision as it was at a given time. | [v0.0.18](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.18) |
| [0.0.17](#0017--2026-10-26) | 2026-10-26 | `check --ref` verifies a commit's own blobs instead of the working tree. | [v0.0.17](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.17) |
| [0.0.16](#0016--2026-10-26) | 2026-10-26 | A read-only `docs lint` for instruction files, links and imports. | [v0.0.16](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.16) |
| [0.0.15](#0015--2026-10-26) | 2026-10-26 | A plugin package and marketplace at the repository root. | [v0.0.15](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.15) |
| [0.0.14](#0014--2026-10-26) | 2026-10-26 | `loop run`, which stops on verifier exit codes under four mandatory limits. | [v0.0.14](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.14) |
| [0.0.13](#0013--2026-10-26) | 2026-10-26 | An opt-in `--max-regression` gate on `baseline compare`. | [v0.0.13](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.13) |
| [0.0.12](#0012--2026-10-26) | 2026-10-26 | `bundle apply` and `bundle remove`, with an ownership ledger, backups and rollback. | [v0.0.12](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.12) |
| [0.0.11](#0011--2026-10-26) | 2026-10-26 | A read-only `bundle status` for the planned bundle items. | [v0.0.11](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.11) |
| [0.0.10](#0010--2026-10-26) | 2026-10-26 | `check` compiles and runs the unit tests, and prints one JSON summary. | [v0.0.10](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.10) |
| [0.0.9](#009--2026-10-26) | 2026-10-26 | `scripts/inonu.py` and native skill profiles for Codex and Claude Code. | [v0.0.9](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.9) |
| [0.0.8](#008--2026-10-26) | 2026-10-26 | `sdd audit` over a strict manifest, with hardened evidence reading. | [v0.0.8](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.8) |
| [0.0.7](#007--2026-10-26) | 2026-10-26 | The doctor reports a CodeGraph license only when the npm package identity agrees. | [v0.0.7](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.7) |
| [0.0.6](#006--2026-10-25) | 2026-10-25 | Research snapshots and an offline evaluation design; nothing was executed. | [v0.0.6](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.6) |
| [0.0.5](#005--2026-10-25) | 2026-10-25 | `decisions packet` with explicit ids, and duplicate-key rejection. | [v0.0.5](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.5) |
| [0.0.4](#004--2026-10-25) | 2026-10-25 | An exploratory evaluation protocol for persistent context; the pilot was not run. | [v0.0.4](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.4) |
| [0.0.3](#003--2026-10-25) | 2026-10-25 | The manual `decisions context` command over an existing database. | [v0.0.3](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.3) |
| [0.0.2](#002--2026-10-25) | 2026-10-25 | A read-only decision context adapter for explicitly chosen decision ids. | [v0.0.2](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.2) |
| [0.0.1](#001--2026-10-25) | 2026-10-25 | Environment doctor, offline baseline runner, SQLite Decision Graph and a typed Jev adapter. | [v0.0.1](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.1) |

## 0.0.26 — 2026-10-26

**Release:** [v0.0.26](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.26) · **Milestone folder:** [docs/specs/milestones/v0.0.26](docs/specs/milestones/v0.0.26/)

### Added

- `python -m inonu_harness milestone close [VERSION] [--date YYYY-MM-DD] [--root DIR] [--dir RELDIR]` closes a milestone. When its folder, its `checkpoint.md`, the manifests and the index pass the close's checks, it writes the milestone's entry into `MILESTONES.md`, the newest-first index of closed milestones, and prints one JSON object with the version, the index path and the entry. It exits 1, writing nothing and printing one line per reason, when a check refuses, and 2 for invalid input. It creates no tag and moves, renames and deletes no file. The index starts at the first milestone closed with the command.
- `tests/test_milestone_close.py` covers each refusal of the close, the index writes and their atomic replacement, the deferred items, the index and checkpoint rules of `check`, and this repository's own milestones.

### Changed

- `check` reports `checkpoint_version_mismatch` for a milestone whose `checkpoint.md` does not name its own version in its first non-empty line. It lints `MILESTONES.md` when that file exists, whatever `--from` says, with the rules `index_malformed`, `index_order`, `index_duplicate`, `index_link_broken`, `index_date_invalid` and `index_date_order`, all errors. The `milestones` step still runs in the same place.
- [docs/milestones.md](docs/milestones.md) describes the close, the index format, the checkpoint that the close requires and the new rules. [docs/versioning.md](docs/versioning.md) says that the manifests are bumped before the close. The README, [docs/sdd-workflow.md](docs/sdd-workflow.md) and the installed skill carry the command.
- The version is 0.0.26 in `inonu_harness/__init__.py`, `pyproject.toml` and `.claude-plugin/plugin.json`. `.claude-plugin/marketplace.json` still states no version, so it was not changed.

### Limits

- The close checks the first line of `checkpoint.md`, its `Status:` line, its `## Verification` and `## Limits` headings, and the reasons of its deferred items. It does not run the verification commands, read `## Flow` or `## Next`, or check that the work passed.
- A warning does not refuse a close, so a milestone whose spec has no requirement item closes with `- Requirements: 0`.
- Earlier milestones have no entry in the index, and none is backfilled. `MILESTONES.md` is an ordinary file, so a hand edit is detected only when it breaks the format.
- Nothing is tagged, moved or deleted, and git is not read. The date is the one given, or today's; it may not be later than today or earlier than the newest date in the index.
- The reason of a deferred item is any text after an em dash or a colon, so a colon inside a URL counts. The first line of a checkpoint only has to name the version, so a line that says it was copied from another milestone passes for the milestone it names.
- The close rewrites the whole index: line endings become LF and a byte order mark is dropped. On POSIX the temporary file makes the index mode 0600. Two closes of the same version at the same moment both succeed and the later write wins; two different versions cannot race, because each needs the manifests to state its own version.
- A spec title with a control character or more than 120 characters is left out of the entry.

## 0.0.25 — 2026-10-26

**Release:** [v0.0.25](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.25) · **Milestone folder:** [docs/specs/milestones/v0.0.25](docs/specs/milestones/v0.0.25/)

### Added

- `python -m inonu_harness milestone new [--title TEXT] [--root DIR] [--dir RELDIR]` creates the folder of the next milestone with `spec.md`, `decisions.md` and `tasks.md` from fixed templates, and prints one JSON object with its version, directory and files. The version is the next one after the version the manifests state, else after the highest milestone folder, else `0.0.1`. It never overwrites a file. It exits 1, creating nothing, when the folder exists, the manifests disagree or leave the scheme, or the scheme is at `0.99.99`; it removes what it made when a write fails. `--title` is one line of 1 to 120 characters without control characters.
- `python -m inonu_harness milestone check [VERSION ...] [--from VERSION] [--root DIR] [--dir RELDIR]` reads the milestone folders and prints a JSON report of findings: requirements that no task row cites, citations of undefined requirements, duplicate or gapped ids, invalid ranges and the folder and file rules. Exit 0 when there is no error finding, 1 otherwise, 2 for invalid input. Each rule and its severity is in [docs/milestones.md](docs/milestones.md).
- `inonu_harness/milestones.py` with `new_milestone` and `check_milestones`, runnable as `python -m inonu_harness.milestones` and reached through the `milestone` subcommand, and `tests/test_milestones.py`.
- [docs/milestones.md](docs/milestones.md) describes the milestone folder, both commands, the finding rules, how a milestone starts, runs, closes and bumps the manifests, the `--from` flag, a short comparison with GSD and the limits. The installed skill carries both commands, and README, AGENTS.md and [docs/sdd-workflow.md](docs/sdd-workflow.md) link to the guide.

### Changed

- `check` runs a `milestones` step between `versions` and `tests`: `python -m inonu_harness milestone check --from 0.0.9`. It runs only when `docs/specs/milestones` exists in the checked directory, and with `--ref` in the temporary export. The milestones before v0.0.9 predate the `R<n>` format and are skipped by name. The other steps are unchanged.
- The version is 0.0.25 in `inonu_harness/__init__.py`, `pyproject.toml` and `.claude-plugin/plugin.json`. `.claude-plugin/marketplace.json` still states no version, so it was not changed.

### Limits

- The commands read only the formats they describe: the three files of a milestone folder, requirement items under `## Requirements`, and table rows that start with `|`. They report and never edit a requirement, a manifest or `checkpoint.md`, and they do not decide that a requirement is done.
- `milestone new` does not close a milestone, write `checkpoint.md` or bump the manifests. How a milestone closes, with a deferred-items ledger and an index, is not decided here; 0.0.26 adds `milestone close`.
- The check does not read git tags or other files that state a version, and the milestones before v0.0.9 are not checked.
- A committed symbolic link under `docs/specs/milestones` fails the `milestones` step of `check --ref`, because the export writes a link as a plain file that the check would read as an empty milestone. A `--ref` export of a commit that has the milestones folder but not `inonu_harness/milestones.py` fails the step with an import error from that commit.
- Requirement items are read under `## Requirements` and under later `Revision` headings until a section for deferred work; a retired requirement kept in an HTML comment is skipped. A range written with spaces around a hyphen or with an em dash is not read as a range.
- A tasks table is read through intervals, so a hostile file costs little: more than 10,000 references stop the coverage rules, and at most 50 findings are listed per coverage rule.

## 0.0.24 — 2026-10-26

**Release:** [v0.0.24](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.24) · **Milestone folder:** [docs/specs/milestones/v0.0.24](docs/specs/milestones/v0.0.24/)

### Added

- `python -m inonu_harness.versions [--root DIR]` checks that the package version is the same in `inonu_harness/__init__.py`, `pyproject.toml` and `.claude-plugin/plugin.json`, and in `.claude-plugin/marketplace.json` when that file states a version. A manifest that does not exist is skipped. Each problem is one line on stderr that names the files and the versions; the command exits 0 when they agree and 1 otherwise. A manifest that cannot be read or parsed, or that has no version, is a problem. A root that is not a directory exits 2. It reads files only and never imports the package.
- `check` runs the same comparison as a `versions` step between `compile` and `tests`, in the checked directory and, with `--ref`, in the temporary export. The report format and the other steps are unchanged.
- `docs lint` also reads each `SKILL.md` below `skills/`. A skill of 20,000 bytes or more gets `skill_file_too_large`, and one of 500 lines or more gets `skill_file_too_long`; each has a remediation sentence. Its links are checked from its own folder. A directory link that leaves the root is reported and not read, as under `docs/`. The limits are the constants `SKILL_MAX_BYTES` and `SKILL_MAX_LINES`.
- `tests/test_versions.py` covers the comparison, the exit codes and output of `main`, the `versions` step with and without manifests and with `--ref`, and this repository. `tests/test_docs_lint.py` covers the skill rules.
- The milestone version scheme, as a global concept for any project, in [docs/versioning.md](docs/versioning.md). Each part of `0.MINOR.PATCH` is 0 to 99 without leading zeros, and `0.0.0` is not a version. Milestone `n` is `0.(n // 100).(n % 100)`, so milestone 24 is `0.0.24` and milestone 100 is `0.1.0`. `python -m inonu_harness version [--root DIR] [--scheme] [--next]` runs the same code as `python -m inonu_harness.versions`, with the same exit codes. `--scheme` also requires every stated version to be in the scheme. `--next` prints the next milestone's version on stdout (`0.0.25` after `0.0.24`, `0.1.0` after `0.0.99`) and exits 1, with the problem lines, when the manifests disagree, leave the scheme, state no version or state `0.99.99`, the last version of the scheme. The command never edits a manifest, and `1.0.0` is the owner's decision.
- The `versions` step of `check` runs with `--scheme`, so this repository cannot leave the scheme. A checkout without manifests still passes.
- The installed skill states the rule in its description and the two commands in a bullet. [docs/versioning.md](docs/versioning.md) covers the milestone directory `docs/specs/milestones/vMAJOR.MINOR.PATCH`, one version in every manifest, how an existing project adopts the scheme, and the table of old and new numbers for this repository.

### Changed

- The version assertions in `tests/test_check_bundle.py` and `tests/test_host_profiles.py` compare with `inonu_harness.__version__` or with the manifest under test, not with a literal. A release edits the three manifests and nothing else.
- Test checkouts that run `check` include `inonu_harness/versions.py`, because the new step runs that module.
- `--max-bytes` and `--max-lines` still apply only to the instruction files. The skill limits are fixed by the constants above.
- Earlier milestones of this repository are renumbered from `v0.N.0` to `v0.0.N`, for N from 1 to 24: the milestone directories under `docs/specs/milestones` (`v0.0.1` to `v0.0.24`), and the references in docs, tests, manifests and fixtures. Git commit messages, Jev spec ids such as `inonu-v021-small-gaps` and receipts keep the numbers they were written with, and the git history was not rewritten.
- The review of the first version audit and skill size rule found the cases below. Each now has a test. A `__version__` line inside a docstring or comment is not a statement, while a trailing comment, single quotes and an annotation are read. A byte order mark is accepted. Duplicate JSON keys and deeply nested JSON are problem lines. A manifest that is unreadable, larger than 1 MiB or a directory is a problem line, not a crash. A skill is measured in bytes, and its file name matches in any case. A `skills/` folder that cannot be listed is reported as `directory_unreadable`. A `skills/` folder or a `SKILL.md` that links outside the root is reported as `link_escapes_root`, and a folder link inside the root is read at its real place.

### Limits

- The comparison reads text and parsed data only. It does not check git tags, an installed plugin cache or any other file that states a version. A release that changes only one manifest is caught only while another manifest still states the old value.
- A checkout without `inonu_harness/versions.py`, such as an older commit checked with `--ref`, fails the `versions` step, because the step runs that module.
- The skill limits are starting points taken from the superpowers size test and the Claude Code skills documentation, not measured optima. Only `SKILL.md` files are read under `skills/`; other Markdown there is not linted.
- Versions are compared as exact text: `0.0.24.0`, `v0.0.24` and `0.0.24 ` do not match `0.0.24`, and the scheme accepts only the plain `0.MINOR.PATCH` form. A version is at most 40 characters; a longer one is reported as having no usable version.
- `python -m inonu_harness.versions` imports the package `inonu_harness` before it runs, because Python runs the package's `__init__` for `-m`. The audit itself reads files only and never imports the package.
- The audit reads `__version__` from source text. It accepts one form: a top-level assignment of a plain string, with a trailing comment, single quotes or an annotation allowed; the last one wins. Any other way of binding the name (in a block, a tuple, a loop, an import, a function, `del`, `+=`) makes the version unusable, and so does an f-string or a computed value. A value set at run time, for example through `globals()`, is invisible to it.
- A link to a folder below `docs/` or `skills/` is read at its real place and is not listed twice. A link below `skills/` or `docs/` to a folder elsewhere inside the root is followed and the findings name the path through the link. A link to a folder outside the root is reported as `link_escapes_root` and is not read. A folder that cannot be listed is reported as `directory_unreadable`, and a file that cannot be read as `file_unreadable`.
- A manifest reached through a link that leaves the checked root is refused, and the problem line does not echo what it holds.
- `audit.json` of milestone v0.0.8 pins the bytes of three files. The renumbering edited them, so the three hashes were refreshed once, and a test now runs that recorded audit so that the next edit to those files cannot silently break it.

## 0.0.23 — 2026-10-26

**Release:** [v0.0.23](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.23) · **Milestone folder:** [docs/specs/milestones/v0.0.23](docs/specs/milestones/v0.0.23/)

### Added

- `python -m inonu_harness jev spec --decision PATH --doc PATH [--doc PATH ...] [--root DIR] [--max-facts N]` prints one Jev decision spec as compact, ASCII-escaped JSON, ready to pass as `spec` to `consensus_plan` and then `consensus_run`. For each `--doc`, in the order given, it writes a source fact (the path relative to `--root`, and the first 16 hex digits of the file's SHA-256) and then the document's text as facts of at most 300 characters. Whitespace inside a line is collapsed and blank lines are dropped; nothing is summarized, reordered or left out. Length is counted in UTF-16 code units, as the judge's server counts it, so an emoji counts 2.
- The command calls no Jev, decides nothing and writes no file. It exits 2, with a fixed message and nothing on stdout, when no `--doc` is given, a document is not a regular UTF-8 file of at most 64 KiB inside `--root`, a document is a symbolic link, has a colon in its file name (an NTFS alternate data stream), is given twice (also through a hard link), holds a NUL character or no text, or matches the secret patterns. A decision file must be strict UTF-8 JSON of at most 64 KiB with no top-level key other than `id`, `goal`, `facts`, `rails`, `options`, `forbidden` and `unknowns`, and its facts may not use the `doc<N>_` keys the documents own.
- The spec is checked by the existing `_validate_spec` before it is printed, so the Jev limits apply: id 40 characters, goal 600, option label 120, option what 400, fact 300, at most 12 rails of 300, 2 to 8 options. `_validate_spec` now counts length in UTF-16 code units, as the server does (its source uses a JavaScript string length), so a spec with emoji that the server would refuse is refused here too. A document whose facts exceed `--max-facts` (default 80) is refused with the count and the limit; nothing is truncated.
- The code is in `inonu_harness/jev_context.py`. `tests/test_jev_context.py` covers the chunk boundaries (299, 300 and 301 characters, packing with the newline, the sentence cut at index 60, emoji, combining marks), a generated-text check that no text is lost, the source facts and their order, every refusal above, each Jev limit at its edge, the fact budget, a secret split by a fact boundary, common token formats, determinism, that nothing is written, and that `JevAdapter` with `MockJevTransport` accepts the output.
- [docs/sdd-workflow.md](docs/sdd-workflow.md) states the rule that no Jev call goes out without a document whose text is sent as facts, and that the document must not state the answer. [docs/integrations.md](docs/integrations.md) records what the judge sees, the limits and the generic `internal error`.

### Changed

- Version 0.0.23 in `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and the version assertions in the tests.

### Limits

- The command does not check whether a document states the answer, or whether it is true or current. Those checks remain human.
- The sensitive-text scan covers the judge's own patterns and a short list of common token formats, on the whole text of each document. It does not catch a password written in prose or a custom token. Keep credentials out of documents. A run of 32 to 44 letters and digits with no zero, such as some commit ids, can be refused as a possible address.
- A line with no space is cut every 300 units, so a word can be split between two facts, though never between a letter and its combining mark. The text is kept, but the judge sees the split, and nothing in the facts marks where a line was split.
- The 300-character chunk size is the validator's fact limit written as a constant in `jev_context.py`; `jev.py` was not changed. A test fails if the two drift apart.
- `--max-facts` is a local budget. Jev does not limit the number of facts in practice (see [docs/integrations.md](docs/integrations.md)).
- The symbolic-link refusal is tested with a patched `Path.is_symlink`, because the Windows host used for this release could not create a link. A real link was not exercised here.

## 0.0.22 — 2026-10-26

**Release:** [v0.0.22](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.22) · **Milestone folder:** [docs/specs/milestones/v0.0.22](docs/specs/milestones/v0.0.22/)

### Added

- `bundle status` gives each item an `ownership` value, read from the ownership ledger that `bundle apply` writes. `ours` means the ledger records the item and what is installed matches the recorded digest. `modified` means the item is recorded but differs, or is gone. `foreign` means it is installed but not recorded. `none` means it is neither. `unknown` means the ledger, or that item's host file, cannot be read or parsed.
- The report adds a top-level `ledger` (`absent`, `present` or `unreadable`) and `ownership_summary`, a count per ownership value sorted by name, as `summary` does for `state`.
- The digests are the ones `bundle apply` already records. The installed `SKILL.md` of each host, the worker agent file and the Codex server's marked block are compared as exact bytes. The Claude MCP entry and the Stop hook group are compared as canonical JSON, so key order and spacing do not matter; any group under `hooks.Stop` may match. A Codex server is `ours` only if no table or sub-table outside the markers changes its effective configuration. An outdated skill that the bundle wrote is `ours`. No ledger schema or write path changes.
- `tests/test_bundle_ownership.py` builds the installed state with the real `bundle apply --apply` into a temporary home, with fake launchers on `PATH`. It covers each ownership value for the skill on both hosts, the worker agent, a Claude and a Codex MCP entry and the Stop hook; an outdated skill; canonical-JSON digests; a user's Stop group placed first; a Codex table added outside the markers; a CRLF rewrite; unreadable ledgers (including an empty file and a `schema_version` of `true` or `1.0`); malformed and unreadable host files; the summaries; byte-identical homes; and output with no planted secret or home path.

### Changed

- `bundle status` keeps every existing key, every `state` value and `summary`. It now reads the ledger as well, and still writes nothing.
- A skill file that exists but cannot be read is now reported as `unknown` by `bundle status` and `bundle plan`, instead of making them exit 2 with no output. `bundle apply` is unchanged.
- A ledger whose `schema_version` is `true` or `1.0` is now refused as a wrong schema by `status`, `apply` and `remove` alike; it was read as valid. A ledger that `bundle apply` wrote always has the integer 1, so nothing a real ledger holds changes.
- Version 0.0.22 in `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and the version assertions in the tests.

### Limits

- `ownership` is advisory and read-only. It does not change what `bundle apply` or `bundle remove` do; both still decide from the ledger and the file contents at the moment of the write.
- `modified` also covers an item the user deleted. The report does not separate a deletion from an edit.
- A Codex block whose line endings changed is `modified`, as `apply` reports it as a conflict.
- The skill's `ownership` looks at `SKILL.md` alone, while its `state` also checks the metadata file: a skill whose metadata file was deleted shows `state` `conflict` and `ownership` `ours`.

## 0.0.21 — 2026-10-26

**Release:** [v0.0.21](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.21) · **Milestone folder:** [docs/specs/milestones/v0.0.21](docs/specs/milestones/v0.0.21/)

### Added

- `python -m inonu_harness decisions --db PATH ready` lists the pending decisions whose declared dependencies are all authorized. A decision with no dependencies is ready. Each `ready` item carries `id`, `question` and the declared `dependencies`. Each `waiting` item carries `id`, `question` and `waiting_on`: each dependency that is not authorized, in declared order, with its `status` (`pending`, `blocked`, `invalidated`, or `missing` when the database has no such decision). Both lists are sorted by id. Blocked, invalidated and authorized decisions are not listed.
- `ready` opens the existing database read-only, as `context` and `as-of` do. It changes no schema, and the database file's bytes are not modified. A database that an outside tool switched to WAL mode may still get SQLite `-wal` and `-shm` helper files when it is opened, as `context` and `as-of` already do. Its output is ASCII-escaped like `as-of`, and an invalid or unreadable store exits 2 with nothing on stdout.
- Stored decision records are now validated when they are read, for every command that reads decisions (`list`, `show`, `history`, `context`, `packet`, `as-of`, `ready`): a field of the wrong shape (a dependency list stored as a string or an object), an unknown status, a record id that does not match its row, and JSON that is invalid or nested too deeply are refused with `decision store contains an unreadable record` and exit 2, instead of being read as an empty list, hiding a decision or raising a traceback. A corrupt record can no longer make a decision look ready.
- `tests/test_decisions_ready.py` covers an empty database, decisions with and without dependencies, each waiting status, several dependencies in declared order, the move to ready after an authorization, sorting, a missing dependency, determinism, unchanged database bytes, non-ASCII text under a strict ASCII stdout and the exit codes.
- The README, [the SDD workflow](docs/sdd-workflow.md) and the skill describe the command.

### Changed

- Version 0.0.21 in `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and the version assertions in the tests.

### Limits

- `ready` says only that the decision's own declared, direct dependencies are authorized. The graph does not require a decision's dependencies to be authorized before the decision itself, so a decision can be ready while something further upstream is still pending. It does not authorize the decision, claim it for a worker, schedule it or record that anyone has started it.
- Two writers that revise dependencies at the same instant can still store a dependency cycle, because the cycle check runs outside the write transaction. This predates `ready`; both decisions then appear under `waiting` on each other. It is not fixed here.
- The output includes each decision's question text, as `show` does, and does not scan for credentials. It has no `--refuse-secret-patterns` option, so review the output before attaching it to an agent.
- The answer is computed on each read. No readiness flag is stored, so nothing can drift from the decisions it describes.

## 0.0.20 — 2026-10-26

**Release:** [v0.0.20](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.20) · **Milestone folder:** [docs/specs/milestones/v0.0.20](docs/specs/milestones/v0.0.20/)

### Added

- `python -m inonu_harness hook stop` is a Stop hook that can block a stop. It reads the hook's JSON from stdin, runs the project's `.inonu/verify.json` checks as argv lists with no shell, and exits 2 with a message when a check fails. It exits 0 when every check passes, when there is no config, or when the block limit is reached, and 1 for an invalid, untrusted or unreadable config or an unexpected error. See [docs/hook.md](docs/hook.md).
- `hook trust` previews a project's verifier config and, with `--yes`, records its SHA-256 against the resolved path in `<home>/.inonu-harness/hook-trust.json` through an atomic write. `hook untrust` removes the record. The hook reads that file and never writes it, and a config that is unrecorded or changed exits 1 before anything runs.
- The block limit counts consecutive blocks in a small state file under the system temporary directory and resets on a pass. When it is reached, the hook allows the stop, so a check that never passes stops blocking after that many attempts. If the counter cannot be stored, the hook exits 1 (non-blocking) instead of blocking, because the limit could not be enforced.
- A failing run reports the attempt, each failing check id with its exit code or `timed out`, and the last 1500 bytes of each check's output, capped at 4000 characters. Each tail passes the credential-pattern scan first and is replaced by a note naming only the matched rules.
- `bundle apply --with-stop-hook` registers `python <checkout>/scripts/inonu.py hook stop` with a 630-second timeout. The stop-hook item of the plan, the preview and the apply report carries a one-sentence `note` on what the hook does.
- `tests/test_hook.py` covers strict config parsing, project directory discovery, the trust and drift cases, check execution and timeouts, the block limit, output scanning and the message cap, unexpected input, the trust commands and one end-to-end run through `hook stop` with stdin JSON. The tests use temporary directories and never touch the real home or the real temporary state.
- The bundle tests cover the new registration and its timeout, status for the current and the legacy command, a conflict with a legacy registration, removal of a recorded legacy registration, and the note.
- Docs: [docs/hook.md](docs/hook.md), with the config format and an example, the trust workflow, exit codes and the reason for them, limits, and install and removal through the bundle. The README, [the plugin reference](docs/plugin.md), [native host profiles](docs/hosts.md) and the skill have matching updates.

### Changed

- The Stop hook that `bundle apply --with-stop-hook` registers now runs `hook stop` instead of `check`. A Stop hook blocks only on exit 2, and `check` exits 1 on failure, so the old hook could never block. It also ran Inonu's own test suite in every project, and it declared no timeout.
- `bundle status` and `bundle apply` recognize an earlier registration that ends in ` check` as an Inonu hook. Status reports it `present`, and apply reports a conflict rather than adding a second group. `bundle remove` reverses it when the ledger recorded it.
- `inonu_harness/bundle.py` renames `is_check_command` to `is_stop_hook_command`. Nothing else imported the old name.

### Limits

- Nothing installs the hook. Only `bundle apply --with-stop-hook --apply` does, and only after the owner has run `hook trust --yes` for the project.
- A trusted config runs its commands with the owner's permissions. Trust records what was reviewed; it does not sandbox the commands.
- The host caps consecutive Stop blocks on its own, and that cap resets whenever a tool is called, so it can end a loop before the hook's block limit does.
- The credential-pattern scan is narrow. A tail that passes it still reaches the model.
- While the state directory cannot be written, a failing check does not block at all (exit 1 with a message); the host's cap is then the only other limit.
- The config must be a plain file inside the project: a link to another place is refused, because trust is bound to the project path. A check is stopped at 16 MiB of output; the credential scan covers the last 64 KiB and the shown text is the last 1500 bytes with control characters escaped, so a credential that begins earlier than 64 KiB before the end is not seen.
- An unledgered legacy Stop hook (a command ending in ` check`) cannot be removed by `bundle remove`, which reports a conflict; delete it by hand.
- The end-to-end run uses the hook's own stdin contract. A live Claude Code session has not been observed blocking a stop.

## 0.0.19 — 2026-10-26

**Release:** [v0.0.19](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.19) · **Milestone folder:** [docs/specs/milestones/v0.0.19](docs/specs/milestones/v0.0.19/)

### Added

- `decisions context` and `decisions packet` accept `--refuse-secret-patterns`. With it, the command scans the object it would print, including a packet's task prompt. On a match it prints nothing to stdout, writes one stderr line naming only rule names and paths, and exits 2. Output without a match is byte-identical to the output without the flag, and without the flag behavior is unchanged.
- `inonu_harness/secret_scan.py` exposes `scan(value)`, which returns `{"rule", "path"}` findings for eleven narrow formats: `private_key_block`, `aws_access_key_id`, `github_token`, `slack_token`, `google_api_key`, `stripe_live_key`, `anthropic_key`, `openai_style_key`, `jwt`, `bearer_token` and `credential_assignment`. Dict keys and string values are scanned. Paths hold list indices and plain lowercase identifier keys; any other key, and any key that holds credential text, appears as `*`.
- `tests/test_secret_scan.py` assembles every synthetic credential at run time from fragments, so the repository holds none. It covers each rule, near misses, paths, key scanning, the rule that no matched value reaches stdout or stderr, a one-megabyte near-miss time bound, the flag on both commands and determinism.
- Docs: a README paragraph, a Portuguese paragraph in [docs/sdd-workflow.md](docs/sdd-workflow.md) and the skill's bullet.

### Limits

- The guard is opt-in and off by default. Callers who attach the output to an agent should pass the flag.
- It catches only the listed formats. It does not catch passwords in prose, custom tokens or most other credential formats, and it can raise false positives. A match means the text needs review; no match does not prove that it is free of secrets.
- Matched values are never printed. The guard does not redact, does not scan the decision database or arbitrary files, and makes no network lookup.
- Matching uses a literal prefix or keyword for every rule, open-ended minimum counts in single-pass matches, and a token boundary for the JWT rule. Linear time is a property of those patterns on the tested inputs, not a proof for every input; the suite runs one-megabyte near-miss inputs for six rule shapes in child processes with a hard time limit, so a quadratic regression fails fast instead of hanging.
- A string under a dict key is also checked as `key: value`, so a credential-named key with a bare value (for example a `password` field) is found like the text form. A key that overlaps the matched text by eight or more consecutive characters is shown as `*` in a path, so no part of a matched value reaches a finding.
- With the flag, the requested ids are scanned before the lookup, because the existing "decision not found" error would otherwise echo a token-shaped id.
- A credential split across fields, list items or the task id and prompt is not joined, so each half is printed.

## 0.0.18 — 2026-10-26

**Release:** [v0.0.18](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.18) · **Milestone folder:** [docs/specs/milestones/v0.0.18](docs/specs/milestones/v0.0.18/)

### Added

- `decisions as-of TIMESTAMP [--ids ID...]` prints each decision as it was at an instant, read from its revision history: `python -m inonu_harness decisions --db PATH as-of TIMESTAMP [--ids ID...]`. `TIMESTAMP` is ISO 8601 with an explicit offset or `Z`; a timestamp without one is refused. The JSON object holds `schema_version` 1, `as_of` (the instant in UTC) and `decisions`, sorted by `id`. Each item has `id`, `state`, `revision`, `recorded_at`, `later_revision` and `snapshot`. The snapshot is the history entry with the highest revision recorded at or before the instant, serialized as `decisions show` serializes a decision.
- An explicit `--ids` decision created after the instant is `not_yet_created`, with `revision`, `recorded_at` and `snapshot` null and `later_revision` true. Without `--ids`, only decisions that existed at the instant are listed.
- The database is opened read-only, as `decisions context` does. It is never created or written, and its bytes do not change. Invalid input exits 2 with a generic message and nothing on stdout: an unparseable or offset-less timestamp, an id not in the database, or an unreadable or unsupported database.
- `tests/test_decisions_as_of.py` builds a temporary database through the public API with a controlled clock. It covers an instant before any decision, a time between two revisions, a time equal to a revision, the time after the last revision, a dependent invalidated by a premise change, a later recommendation and authorization, `--ids` filtering and order, the error exits, unchanged bytes and the CLI output.
- Docs: a README paragraph, a Portuguese paragraph in [docs/sdd-workflow.md](docs/sdd-workflow.md) and the skill's `as-of` bullet.

### Limits

- Times are the clock of the machine that recorded each revision. They are not authenticated, so the result is a local audit aid and not a tamper-proof ledger.
- The query reads history and cannot show a state older than the first revision. It changes no schema; validity columns, a revision diff and writing or repairing history stay out of scope.
- The database file is never modified. A database that an outside tool switched to WAL mode may get `-wal` and `-shm` helper files created by SQLite when it is opened, as `decisions context` already does; the store never enables WAL itself.
- The output is ASCII-escaped, and an unreadable history record now gives exit 2 with a generic message for every decisions command instead of a traceback.

## 0.0.17 — 2026-10-26

**Release:** [v0.0.17](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.17) · **Milestone folder:** [docs/specs/milestones/v0.0.17](docs/specs/milestones/v0.0.17/)

### Added

- `check --ref REF` verifies a commit instead of the working tree: `python -m inonu_harness check [--root PATH] [--ref REF]`. `REF` must resolve to a commit (`git rev-parse --verify REF^{commit}`). Git's own blobs for that commit are read with `git ls-tree` and `git cat-file --batch` and written to a temporary directory, with no attribute or line-ending conversion, and unsafe paths (absolute, `..`, `.git`, drive or backslash names) are refused. There the command runs the `compile` and `tests` steps as without the flag, then `runner`, which is `python scripts/inonu.py --version`. The JSON gains `ref` (the string as given) and the `runner` step. Exit 0 only when every step exits 0, 1 otherwise.
- With `--ref`, a root below the top of its repository checks the matching directory of that commit.
- Invalid input exits 2 with a generic message that holds no path: a root outside a git repository, a ref that does not resolve to a commit, a git failure or a 60-second git timeout, and an exported tree without `tests/`. The temporary directory is removed on every outcome, and the command makes no network request.
- Without `--ref`, the steps, output keys and exit codes are unchanged.
- `tests/test_check_ref.py` builds temporary git repositories and covers a complete commit, a module that was never committed, an uncommitted edit, a committed broken test, the invalid inputs, the removed export, a subdirectory root and the output without the flag.
- Docs: a "Before you push" section in [docs/plugin.md](docs/plugin.md) (commit, then `python -m inonu_harness check --ref HEAD`), a README paragraph and the skill's `check` bullet.

### Limits

- The check covers the operating system where it runs only. It is not verified on other systems. The CI workflow is unchanged in this release (decision D1 in the v0.0.17 milestone), so a three-system CI run is deferred.
- A pass shows that the commit is self-contained for its compile step, its unit tests and its runner. It does not show that the plugin installs, that a host loads the skill or agent, or that the code is correct.
- The export holds the commit's blobs exactly as stored: `export-ignore`, `export-subst` and `core.autocrlf` do not apply, submodule entries are skipped and a symlink becomes a plain file holding its target text. All blobs are held in memory once. Uncommitted and ignored files are never read.
- The 60-second limit covers git calls only. The compile and test steps have no time limit, as before.

## 0.0.16 — 2026-10-26

**Release:** [v0.0.16](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.16) · **Milestone folder:** [docs/specs/milestones/v0.0.16](docs/specs/milestones/v0.0.16/)

### Added

- A read-only documentation lint: `python -m inonu_harness docs lint [--root PATH] [--max-bytes N] [--max-lines N]`. It prints one JSON object with `schema_version` 1, `status`, `files_checked` and `findings`, and writes no file. Exit codes: 0 for `pass`, 1 for `fail` (at least one finding), 2 for invalid input (a root that is not a directory, or a limit that is not positive).
- Instruction-file rules for `AGENTS.md`, `AGENTS.override.md` and `CLAUDE.md` in the root: `instruction_file_too_large` (default 32768 bytes, the documented Codex project-doc default), `instruction_file_too_long` (default 200 lines), `import_missing` for an `@path` line whose target does not exist, and `file_unreadable` for a file that is not valid UTF-8.
- Link rules for those instruction files, `README.md` and every `*.md` under `docs/`: `link_broken` and `link_escapes_root`. Fenced code blocks and inline code spans are skipped; scheme, fragment-only and absolute targets are not checked.
- Each finding carries `rule`, `file` (root-relative), `line`, `detail` and a `remediation` sentence that says what to change. Findings are sorted by file, line and rule, and the output holds no absolute path, so the same tree gives byte-identical output.
- An architecture test, `tests/test_architecture.py`, that runs in the unit suite and therefore in `check`. It fails when a module in `inonu_harness/` or `scripts/` imports anything that is neither standard library nor `inonu_harness`, when a module other than `cli.py`, `__main__.py` and the runner `scripts/inonu.py` imports `inonu_harness.cli` or `inonu_harness.__main__`, when any module (including subpackages) imports or runs code by name with `__import__`, `importlib.import_module`, `exec` or `eval`, or when `docs_lint.py` imports `cli`. The failure message names the file and what to change.

### Limits

- The lint checks links and size only. It does not check whether a document is true or current, and it does not detect absolute local paths.
- Heading anchors are not verified. A trailing `#fragment` or `?query` is removed before the target file is checked.
- The 200-line limit is a configurable starting point, not a documented limit. The 32768-byte limit is the documented Codex default.
- Nested instruction files are not checked, and the link rules do not cover `CHANGELOG.md` or `skills/`.
- Link matching is case-exact and reports backslash targets on every host, so a link that only works on Windows or macOS is a finding. Links that span lines, escaped brackets and indented (non-fenced) code are not modelled. Directory links are not followed; one that leaves the root is reported.
- There is no documentation-gardening agent and no quality-score document. A stale claim passes the lint unless it breaks a link or size rule, and nothing opens a correction.
- The architecture test checks imports only. It does not test behavior or any other structural rule.
- The research source is one vendor's article (OpenAI), read in a browser pane and not independently evaluated. It describes one team's experience and does not measure how much each practice contributes; see [research-verify.md](docs/specs/milestones/v0.0.16/research-verify.md).

## 0.0.15 — 2026-10-26

**Release:** [v0.0.15](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.15) · **Milestone folder:** [docs/specs/milestones/v0.0.15](docs/specs/milestones/v0.0.15/)

### Added

- An installable Claude Code plugin at the repository root: `.claude-plugin/plugin.json` (name `inonu-harness`, version `0.0.15`) and `.claude-plugin/marketplace.json`, with the repository as its own marketplace. Install with `/plugin marketplace add ori-inonu/inonu-harness` and `/plugin install inonu-harness@inonu-harness`.
- The plugin carries the `inonu-harness` skill, the `inonu-worker` agent (`model: haiku`) and the standard-library runner `scripts/inonu.py` with the `inonu_harness` package.
- The skill calls the runner as `python "${CLAUDE_PLUGIN_ROOT}/scripts/inonu.py"`. `scripts/configure_hosts.py` and `bundle apply` replace that token with the absolute runner command in the copies they write, so those copies contain no placeholder.
- Structural tests in `tests/test_plugin.py` check the manifests, frontmatter and layout without the Claude CLI.
- The reference is in [docs/plugin.md](docs/plugin.md).

### Limits

- The package was not run through `claude plugin validate`, and no live installation was tested. Run `claude plugin validate .` before relying on it.
- The plugin needs Python 3.11+ reachable as `python`. The Claude docs do not name the Windows launcher; that is not verified.
- The plugin starts no MCP server and no hook. MCP registration and the Stop hook stay in `bundle apply`, with preview, ledger and rollback.
- Installed users stay on the cached copy until `version` changes.
- The plugin docs namespace plugin components under the plugin name, so a plugin installed beside a `bundle apply` profile should not collide with it. This is not tested in a live session.
- The plugin installs from committed files only: the manifests and every module and document the package needs must be committed and pushed before it can be installed from GitHub.
- A `CLAUDE.md` at the plugin root is not loaded as context and `claude plugin validate` warns about it.
- Passing the structural tests does not establish installation, reachability or agent quality. The plugin is not listed in any directory.

## 0.0.14 — 2026-10-26

**Release:** [v0.0.14](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.14) · **Milestone folder:** [docs/specs/milestones/v0.0.14](docs/specs/milestones/v0.0.14/)

### Added

- A deterministic loop runner: `python -m inonu_harness loop run SPEC.json`. It runs the caller's `step` command once per iteration, then every check, and prints one JSON summary on stdout. Exit codes: 0 for `verified_done`, 1 for any other stop, 2 for invalid input (bad spec or unreadable file).
- A strict JSON spec with `step`, `checks`, `limits`, `log` and an optional `cwd`. Duplicate keys, unknown keys and wrong types are invalid input. Commands are argv lists, run without a shell and with stdin closed.
- Stop reasons `verified_done`, `verifier_error`, `wall_clock`, `max_iterations` and `stagnation`, applied in that precedence after each iteration. Iteration 0 runs every check before any step, so an already-passing project runs zero steps.
- Four mandatory limits with no defaults: `max_iterations`, `iteration_timeout_seconds`, `total_timeout_seconds` and `stagnation_iterations`.
- Runner-owned `passes`: each check's state comes only from its exit code. A check that passed earlier and fails later is recorded as a regression.
- An append-only JSONL log with one object per iteration, flushed after each write. It holds ids, exit codes, timeout flags, hashes and decisions, and no argv, command output, environment or absolute paths.
- Every command's whole process tree is killed when the command ends and on timeout, so nothing a step starts outlives it: on POSIX, the command's own session and process group with SIGKILL; on Windows, a kill-on-close Job Object (with `taskkill /T /F` as fallback).
- The stagnation tree hash covers untracked file contents, handles a repository without a commit, excludes the loop's own log and treats a git failure as unknown, which never counts as stagnation. A command the spent budget never let start is recorded as `not_run` and is not counted as a regression. The printed summary is ASCII-escaped.
- The reference is in [docs/loop.md](docs/loop.md).

### Limits

- The loop does not resume after an interruption. The log keeps the iterations written before it stopped.
- The runner does no token, spend or model-usage accounting.
- The limit values and the stagnation window are unvalidated starting points. No source gave a numeric threshold.
- A passing run means only that every check exited 0 in the same iteration. The runner proves nothing about agent quality or whether the checks test the right thing.
- The `step` command is the caller's choice and may call a model or a paid service, so it may cost money.
- The log is not tamper-proof: a step runs with the caller's permissions and can edit it.
- No host hook is generated or installed. The loop does not write a Claude Code Stop hook or any other host configuration.
- Research gaps for the hook and loop designs remain open (the OpenAI primary page, the SubagentStop and `onFailure` text, and whether `stop_hook_active` resets); see [research-verify.md](docs/specs/milestones/v0.0.14/research-verify.md).

## 0.0.13 — 2026-10-26

**Release:** [v0.0.13](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.13) · **Milestone folder:** [docs/specs/milestones/v0.0.13](docs/specs/milestones/v0.0.13/)

### Added

- `baseline compare` takes an opt-in regression gate: `python -m inonu_harness baseline compare BEFORE AFTER --max-regression R`. `R` is a finite number of at least 0 (`0.10` allows a 10% increase). A negative, NaN or infinite `R` exits 2 and prints nothing to stdout.
- With the flag, the output is the existing comparison plus a `gate` object with `max_regression`, `status`, `regressions` and `skipped`. Exit codes: 0 for `pass`, 1 for `fail`, 2 for `incomparable` (task or config differ, or a judged metric changed its measurement source and no regression is certain). A certain regression always wins and exits 1. Unreadable files, an unsupported schema, duplicate JSON keys and an invalid `R` are invalid input and exit 2 without a `gate` object. Without the flag, the output and exit code are unchanged.
- Judged metrics, only when both runs observed them: acceptance criteria that passed before and are missing or failed after (named `acceptance:<id>`, no tolerance); `failures`, `blocks` and `tool_calls` by list length; `input_tokens`, `output_tokens` and `cost_usd` by value. A value that grows from 0 to a positive number fails. The comparison uses exact decimal arithmetic, so a rise of exactly `R` passes and very large integers compare exactly.
- `elapsed_seconds`, `recoveries`, `runtime`, `model` and `component_versions` are not judged. Metrics whose values are unavailable (for example tokens or cost `null`) are listed under `skipped` with their reason and never filled in.
- The standalone entry point `python -m inonu_harness.baseline compare` takes the same flag. Both entry points call the pure function `gate_comparison()` in `inonu_harness/baseline.py`.

### Limits

- The gate compares two saved local measurements. It does not establish agent quality or productivity, and a lower token count does not offset a lower acceptance outcome.
- Skipped metrics never count as a pass or a regression, except that a judged metric whose measurement source changed makes the gate `incomparable` rather than `pass`.
- Duplicate JSON keys are rejected only when the flag is given, so reading without the gate is unchanged.

## 0.0.12 — 2026-10-26

**Release:** [v0.0.12](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.12) · **Milestone folder:** [docs/specs/milestones/v0.0.12](docs/specs/milestones/v0.0.12/)

### Added

- `bundle apply` and `bundle remove`: `python -m inonu_harness bundle apply [--host codex|claude|both] [--home PATH] [--with-stop-hook] [--apply]` and `bundle remove` with the same flags. Without `--apply` the command is a preview and writes nothing. Output is one JSON object with `mode`, `action`, `version` and `items`; it prints no file contents, settings values, environment values or absolute personal paths.
- Apply covers the user skill profile (both hosts), the Claude worker agent, complementary MCP server entries and, only with `--with-stop-hook`, the Stop hook. The stop hook is opt-in because it would run the Inonu suite on every Stop in every project.
- Preflight runs before any write. A conflict prints the report, writes nothing and exits 2. Applying twice reports `unchanged` the second time.
- An ownership ledger records the hash of each item Inonu wrote, plus what the run created (files, directories, JSON containers). Before a write, the original file is backed up.
- A write is all-or-nothing per run: if a file changes mid-run, a write fails or the process is interrupted, the files already written (backups included) are restored and the report says `failed` or `conflict` with `rollback: complete` (or `incomplete`). A file edited by someone else after the run wrote it is left alone and the rollback is reported incomplete.
- A conflict found during preflight is reported as `would_install`/`would_update`/`would_remove`; no item claims a write that did not happen.
- `bundle remove` reverses only items whose hash matches the ledger. A user-modified item, or a Codex block whose line endings were changed, is reported as `conflict` and kept. Remove deletes only the files, directories and empty containers that apply created, so files and containers that existed before (even empty ones) stay. JSON files are rewritten from their parsed content, so remove restores the content but not the original formatting; the pre-apply file is kept in `~/.inonu-harness/backups`, which remove does not delete.
- MCP launchers are found only through absolute `PATH` entries. A file in the current directory or a relative `PATH` entry is never recorded, and a Windows `.cmd` launcher is written with its absolute path.
- JSON files containing non-finite numbers (`NaN`, `Infinity`, `1e400`), duplicate keys or text that cannot be written back as UTF-8 are treated as a conflict instead of being rewritten. A regular file where a directory belongs is also a conflict.
- `tool_missing` is reported when a required launcher is not found; Inonu does not install it.
- Existing user MCP entries with the same id are never overwritten.
- `bundle status` keeps working and reflects applied items.

### Limits

- A host that writes its own configuration at the same moment can lose an edit inside the short window between re-reading a file and replacing it. Rollback restores what this run wrote and does not undo an outside edit made after that.
- Directories created by a run that fails midway are removed only if they are empty and listed as created by the bundle.
- `configured` means the host file contains the key. It does not prove that the server is reachable or that a hook runs.
- Apply and remove do not install the tools themselves (CodeGraph, Headroom, Node).
- The write of host configuration is authorized by the owner; the record is in `docs/specs/milestones/v0.0.11/decisions.md` (D2).

## 0.0.11 — 2026-10-26

**Release:** [v0.0.11](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.11) · **Milestone folder:** [docs/specs/milestones/v0.0.11](docs/specs/milestones/v0.0.11/)

### Added

- A read-only `bundle status`: `python -m inonu_harness bundle status [--host codex|claude|both] [--home PATH]` reports the state of each `bundle plan` item (`skill`, `worker-agent`, `stop-hook`, `mcp`) plus a `summary` count per state. It reuses the plan and the v0.9 skill preflight, reads host files without writing them, and never prints file contents, settings values, environment values or absolute personal paths.

### Limits

- `bundle status` is read-only. `configured` and `present` describe what a host file contains; they do not prove that an MCP server is reachable or that a hook runs. `accessibility` stays `unknown`.
- Install and remove commands for hooks, MCP registrations and agent files move to v0.0.12 and still require explicit owner authorization.

## 0.0.10 — 2026-10-26

**Release:** [v0.0.10](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.10) · **Milestone folder:** [docs/specs/milestones/v0.0.10](docs/specs/milestones/v0.0.10/)

### Added

- A deterministic `check` gate: `python -m inonu_harness check [--root PATH]` runs `compileall` and the unit tests for the selected checkout, prints one JSON summary to stdout, sends child output to stderr, and exits 0 only when every step passes.
- A read-only `bundle plan`: `python -m inonu_harness bundle plan [--host codex|claude|both] [--home PATH]` lists the skill status (reusing the v0.9 host profile logic), a Claude worker agent source, a stop-hook settings snippet that would run `check`, and complementary MCP server entries. Every non-skill item reports `"applied": false`.
- A worker agent source at `agents/inonu-worker.md` with `model: haiku`, bounded to one ticket, without nested delegation or Jev calls, and required to run `check` before reporting done.
- An `inonu` console script declared in `pyproject.toml` that points to `inonu_harness.cli:main`. No dependency was added.
- Research and decision records for this slice are in `docs/specs/milestones/v0.0.10/research.md` and `docs/specs/milestones/v0.0.10/decisions.md`.

### Limits

- `bundle plan` applies nothing and writes nothing. Installing the hook, MCP registrations or the worker agent requires a later milestone with explicit owner authorization.
- `check` verifies only this checkout layout (`inonu_harness`, `scripts` and `tests`). A passing result is deterministic evidence for those steps, not proof of semantic correctness or of host behavior.
- Haiku adequacy for the worker agent has not been evaluated; the `model: haiku` setting is a configuration choice, not a measured result.

## 0.0.9 — 2026-10-26

**Release:** [v0.0.9](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.9) · **Milestone folder:** [docs/specs/milestones/v0.0.9](docs/specs/milestones/v0.0.9/)

### Added

- A standard-library runner at `scripts/inonu.py` for invoking the CLI from any working directory. `doctor --project-root PATH` selects the project to inspect while preserving the default behavior when omitted.
- Native user skill profiles for Codex and Claude Code. `scripts/configure_hosts.py` previews by default and writes only when `--apply` is given. It targets the selected user skill directories, records local ownership metadata, and refuses unmanaged or modified profile files.
- Portable profile commands that quote the runner path for the host shell and point skill documentation links at the checkout that supplied the profile.
- No runtime dependency was added.

### Fixed

- POSIX substitution-test instrumentation now preserves the wrapped `os.open` descriptor-relative capability. This lets Linux CI exercise the intended file substitutions instead of returning early; production evidence-reading rules are unchanged.

### Limits

- Profile application proves only that files were installed or updated. It does not prove a host discovered the skill, loaded it in a session, or successfully used every command. A local Claude Desktop Code session uses local skills; Chat and Cowork use account skill settings instead.
- The profile helper does not configure MCP servers, plugins, credentials, hooks, permissions, providers, or global agent instructions. It is not evidence of universal host activation.
- Inonu complements existing tools. It does not provide CodeGraph symbol navigation, RTK terminal filtering, Headroom context compression, or Ponytail coding guidance. No real-task benchmark shows that Inonu alone is superior to those tools.

## 0.0.8 — 2026-10-26

**Release:** [v0.0.8](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.8) · **Milestone folder:** [docs/specs/milestones/v0.0.8](docs/specs/milestones/v0.0.8/)

### Added

- Added the optional, read-only `sdd audit` command for a strict v1 manifest. It checks declared requirement, task, verification, and evidence links and hashes files under the selected root.
- Synthetic fixtures exercise passing, failing, and adversarial inputs. The audit does not interpret document meaning, authenticate that a check ran, execute checks, or grant authorization.
- Hardened evidence access against unsafe paths and file substitution while keeping reports sanitized. Platform-specific tests remain skipped where their POSIX conditions are unavailable.

## 0.0.7 — 2026-10-26

**Release:** [v0.0.7](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.7) · **Milestone folder:** [docs/specs/milestones/v0.0.7](docs/specs/milestones/v0.0.7/)

### Added

- The doctor reports a local CodeGraph license only when the global npm package identity, version, repository, declared license, and executable location agree. Unverified layouts and mismatches remain `unknown`; local paths and raw package metadata stay out of the report.
- This probe does not establish MCP reachability or active-session use.

## 0.0.6 — 2026-10-25

**Release:** [v0.0.6](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.6) · **Milestone folder:** [docs/specs/milestones/v0.0.6](docs/specs/milestones/v0.0.6/)

### Added

- Recorded research snapshots and proposals for offline artifact-handoff evaluation, with synthetic case and rubric designs that preserve the eight SDD stages.
- This milestone is research and design only: the proposed corpus and agent evaluation were not executed, and no candidate tool or adaptive router was adopted from the research.

## 0.0.5 — 2026-10-25

**Release:** [v0.0.5](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.5) · **Milestone folder:** [docs/specs/milestones/v0.0.5](docs/specs/milestones/v0.0.5/)

### Added

- Added `decisions packet` to combine caller-provided task JSON with decisions selected by explicit IDs, using the existing read-only projection. The caller reviews and attaches the output; it is not injected automatically.
- The packet reader rejects duplicate JSON object keys, extra fields, and invalid task values. This hardening is specific to the task packet input.

## 0.0.4 — 2026-10-25

**Release:** [v0.0.4](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.4) · **Milestone folder:** [docs/specs/milestones/v0.0.4](docs/specs/milestones/v0.0.4/)

### Added

- Documented a proposed text-only pilot comparing the same task with and without explicit decision context. The protocol preserves the existing eight SDD stages and specifies observable criteria and missing-value handling.
- The pilot has not been run. The protocol provides no evidence of a general effect on agent outcomes.

## 0.0.3 — 2026-10-25

**Release:** [v0.0.3](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.3) · **Milestone folder:** [docs/specs/milestones/v0.0.3](docs/specs/milestones/v0.0.3/)

### Added

- Added the manual `decisions context` CLI command, which reads an existing schema-v1 database without creating or changing it. Fixture checks verify the output contract; they do not measure agent quality, productivity, or speed.

## 0.0.2 — 2026-10-25

**Release:** [v0.0.2](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.2) · **Milestone folder:** [docs/specs/milestones/v0.0.2](docs/specs/milestones/v0.0.2/)

### Added

- Added an opt-in, read-only decision context adapter that returns an allowlisted projection for caller-selected IDs.

## 0.0.1 — 2026-10-25

**Release:** [v0.0.1](https://github.com/ori-inonu/inonu-harness/releases/tag/v0.0.1) · **Milestone folder:** [docs/specs/milestones/v0.0.1](docs/specs/milestones/v0.0.1/)

### Added

- Added a sanitized, read-only environment doctor; an offline baseline runner and comparison; and a local SQLite Decision Graph with revisions, evidence, dependencies, idempotency, and distinct recommendation and authorization records.
- Added a typed JEV adapter over an injected MCP transport and a deterministic mock. This is not a portable live JEV transport or proof of JEV availability in another client or session.
