# Milestones

This page describes the milestone folders that any project managed by the Inonu Harness can keep, and the three commands that create, check and close them. The numbering rules are in [versioning.md](versioning.md).

## The folder

A milestone lives in `docs/specs/milestones/vX.Y.Z`, named after its version. Files directly under the milestones directory are ignored by the folder rules, and only folders count. The one file there that is read is the index, `MILESTONES.md` ([The index](#the-index)).

- `spec.md` holds the requirements. Each requirement is a top-level list item that starts with its id, `- R1 <text>` or `- **R1** <text>`, under a `## Requirements` heading. Items are read under `## Requirements` and under any later heading that starts with `Revision`, until a section for deferred work (`Out of scope`, `Non-goals`, `Not in scope` or `Deferred`) begins. Fenced code blocks and HTML comments are skipped. Ids run R1, R2, ... with no gap. Items inside fenced code blocks are not requirements.
- `tasks.md` holds a table of tasks. A row is a line that starts with `|`. Any `R<n>` in a row cites that requirement, in any column. A range cites every id in it: `R1-R5`, `R1–R5` or `R1..R5`; the end may omit its `R`.
- `decisions.md` holds the decisions and their evidence. The check recommends it but does not require it.
- `checkpoint.md` is written by hand when the milestone closes. `check` reads its first non-empty line, and `close` reads what [The checkpoint](#the-checkpoint) requires. No command writes it.

## Commands

Run them from the repository root. `python scripts/inonu.py milestone ...` runs the same code with the same arguments:

    python -m inonu_harness milestone new [--title TEXT] [--root DIR] [--dir RELDIR]
    python -m inonu_harness milestone check [VERSION ...] [--from VERSION] [--root DIR] [--dir RELDIR]
    python -m inonu_harness milestone close [VERSION] [--date YYYY-MM-DD] [--root DIR] [--dir RELDIR]

`--root DIR` defaults to the current directory and must be an existing directory. `--dir RELDIR` defaults to `docs/specs/milestones` and must be a relative path that resolves inside the root. A link on the way out is refused.

### `milestone new`

Creates the folder of the next milestone with `spec.md`, `decisions.md` and `tasks.md` from fixed templates, then prints one JSON object with sorted keys, indented by two spaces (the example below is shown on one line). Its fields are `schema_version`, `version`, `directory` (relative to the root) and `files`:

    {"directory": "docs/specs/milestones/v0.0.26", "files": ["spec.md", "decisions.md", "tasks.md"], "schema_version": 1, "version": "0.0.26"}

- The version is computed, never typed. It is the next version after the one the manifests state. Without a stated version, it is the next after the highest milestone folder, and with neither it is `0.0.1`.
- `--title` is one line of 1 to 120 characters without control characters. It goes only into the heading of `spec.md`.
- Files are created exclusively and never overwritten. If a write fails, the files and folders this run made are removed.
- Exit 0: created. Exit 1: refused, nothing kept. The manifests disagree or leave the scheme, the folder already exists, the scheme is at `0.99.99`, or a write failed. Exit 2: invalid input, such as a bad `--title`, a `--dir` outside the root, a missing root, or a failed local file operation. Problems go to stderr.

### `milestone check`

Reads the milestone folders below `--dir`, in version order. Without arguments it reads all of them. `VERSION ...` limits it to the named versions, and `--from VERSION` to that version and every later one; with both, both apply. Folders whose names are not versions are always listed. A missing milestones directory passes with nothing to check. A `MILESTONES.md` in the milestones directory is linted too, whatever `--from` and the named versions say, and is reported as the entry `index`.

Prints one JSON report, with sorted keys:

    {"milestones": [{"findings": [...], "version": "0.0.1"}], "schema_version": 1, "status": "pass"}

Each finding has `rule`, `severity`, `file`, `line` (or `null`) and `detail`. Findings within a milestone are sorted by severity, rule, file and line.

- Exit 0: `status` is `pass`, with no error finding. Warnings do not fail.
- Exit 1: `status` is `fail`, with at least one error.
- Exit 2: invalid input, printed on stderr with no report. Examples: a missing root, a `--dir` outside the root, a version that is not in the `0.MINOR.PATCH` scheme, a named version with no folder when the milestones directory exists (a missing directory passes with nothing to check).

### `milestone close`

Writes the entry of one milestone into `MILESTONES.md`, the index of closed milestones, when every check below passes. `VERSION` names the milestone; without it, the highest in-scheme folder is closed. Only that folder is checked, so `check` still reports the others. `--date` is the shipping date, a real calendar date in the form `YYYY-MM-DD`; without it, today's date is used.

It writes that index and nothing else. It creates no git tag, does not touch git, and moves, renames or deletes no file.

On success it prints one JSON object with sorted keys, indented by two spaces. The example is shown on one line. The output is ASCII-escaped like the other JSON reports, so the em dash in `entry` is written as `\u2014`; the example shows it unescaped:

```text
{"entry": "## v0.0.9 — Sample (Shipped: 2026-01-15)\n- Requirements: 2\n- Deferred: 0\n- Folder: [v0.0.9](v0.0.9/)", "index": "docs/specs/milestones/MILESTONES.md", "schema_version": 1, "version": "0.0.9"}
```

Exit 0 when the entry is written. Exit 1 when the close is refused, with nothing written. Exit 2 for invalid input, also with nothing written.

The checks run in this order. A refusal says why on stderr, one line for each reason, each prefixed `inonu-harness: `. Exit 2 comes first, for invalid input:

1. The root is not an existing directory, or `--dir` is not a relative path that resolves to a folder inside the root.
2. `--date` is not a real calendar date in the form `YYYY-MM-DD` (`2026-02-30`, `26-1-1` and an empty value are refused), or it is later than today.
3. `VERSION` is not in the `0.MINOR.PATCH` scheme. `v0.0.9` is refused; the version is `0.0.9`.
4. The milestones directory exists but is not a directory.
5. `VERSION` has no folder, and the milestones directory exists.

Exit 1 comes next. With no folder to close, the close stops at once: `there is no milestone folder to close` when `VERSION` is omitted, or `the milestone folder for VERSION does not exist` when `VERSION` is named and the milestones directory is missing. Otherwise every reason below that applies is printed, not only the first:

6. The error findings of the folder check of the milestone, printed in the order of the rule names, so `checkpoint_version_mismatch` comes before `file_unreadable`. The folder or a file resolves outside the root (`link_escapes_root`). `spec.md` or `tasks.md` is missing (`required_file_missing`). A file that is present cannot be read (`file_unreadable`). Then `checkpoint_version_mismatch` and the coverage errors (`requirement_duplicate`, `requirement_unclaimed`, `task_cites_unknown_requirement`, `reference_range_invalid`, `reference_limit_exceeded`, `findings_truncated`). Warnings do not refuse: `requirement_gap`, `requirements_not_found`, `tasks_not_found` and `decisions_missing` leave the close open.
7. `checkpoint_missing` when `checkpoint.md` does not exist. Otherwise `checkpoint_status_missing` and `checkpoint_section_missing`, the latter for `## Verification` and then for `## Limits`. See [The checkpoint](#the-checkpoint).
8. `deferred_without_reason`, once for each deferred item that has no reason.
9. When `MILESTONES.md` exists: `link_escapes_root` or `file_unreadable` if it cannot be read, and then each `index_*` rule of [The index](#the-index).
10. The manifests: a manifest that cannot be read or parsed, has no version, states a version outside the scheme, or disagrees with another manifest. Each is a line of its own, such as `.claude-plugin/plugin.json has version 0.0.10 but inonu_harness/__init__.py has version 0.0.9`. A manifest that does not exist is skipped, so a project with no manifest is not held to them.
11. `manifests_not_bumped` when the manifests do not all state `VERSION`: `bump them first`.
12. `version_closed` when the index already has `VERSION`. Otherwise `version_not_higher` when `VERSION` is not above the highest version in the index.
13. `index_date_order` when the date is earlier than a date already in the index.

When every check passes, the entry goes above the newest entry of the index. With no index yet, the file is created with its heading and its description line. The title is the text after the em dash in the first heading of `spec.md`, and the heading has no title part when there is none. `- Requirements:` counts the requirement ids of `spec.md`, and `- Deferred:` counts the items of the checkpoint's deferred sections.

The file is written to a temporary file in the same folder and put in place with `os.replace`. If that fails, the close is refused with `could not write the index; nothing was changed`, the old index stays as it was, and no temporary file remains.

## The index

`MILESTONES.md` is the file of that name in the milestones directory: `docs/specs/milestones/MILESTONES.md` in this repository. `close` is the only command that writes it, and `check` lints it. Its format is:

1. The first non-empty line is `# Milestones`.
2. The next line is a one-line description. Any line that does not start with `#` or `-` will do. `close` writes a description that names the command and says the entries are newest first.
3. Then the entries, newest first. Each is a heading and exactly three list items, in this order: `- Requirements: <n>`, `- Deferred: <n>` and `- Folder: [v<version>](v<version>/)`. The heading is `## v<version> — <title> (Shipped: <date>)`. The part `— <title>` is left out when the title is empty.

The date is a real `YYYY-MM-DD` date. Blank lines are ignored. This index has two entries. The values are an illustration, not this repository's index:

```markdown
# Milestones

Milestones closed with `milestone close`, newest first.

## v0.0.10 — Sample title (Shipped: 2026-02-01)
- Requirements: 4
- Deferred: 1
- Folder: [v0.0.10](v0.0.10/)

## v0.0.9 (Shipped: 2026-01-15)
- Requirements: 2
- Deferred: 0
- Folder: [v0.0.9](v0.0.9/)
```

`check` reads the index whatever `--from` says, and reports it as the entry `index`. Every index rule is an error, so a damaged index fails `check` and makes `close` refuse.

## The checkpoint

`checkpoint.md` is written by hand when the milestone closes, after its verification commands have run. `close` reads these parts and refuses without them:

- The first non-empty visible line (outside HTML comments and code fences) names the milestone's own version as a whole token. `v0.0.1` is not named by `v0.0.10`. `check` reports the same mismatch, as `checkpoint_version_mismatch`, for any milestone that has a checkpoint.
- A line that starts with `Status:`, at the start of the line, outside a code fence and an HTML comment.
- A `## Verification` heading and a `## Limits` heading, at level 2 with exactly that text.
- Each list item under a `## Deferred` or `## Deferred items` heading, at level 2 in any letter case and with optional closing `#` marks, gives a reason after an em dash or a colon (a hyphen does not count, and a colon inside a URL does). A bullet or a number makes an item, with any indentation, so a nested line needs its own reason. A heading of level 3 or deeper keeps the section open, and any other heading of level 1 or 2 ends it.

The deferred section is optional. Its item count is the `- Deferred:` of the index entry. This is the skeleton a checkpoint follows:

```markdown
# v0.0.26 checkpoint — 2026-01-15

Status: implemented and verified locally; nothing is committed.

## Flow

What was done, step by step, and the reviews.

## Verification

The commands that were run, their exit codes, and what each showed.

## Limits

What the work does not prove and what was not checked.

## Next

The next step, or none.

## Deferred items

- R4 Later — waits for the next release.
```

`close` does not read `## Flow` or `## Next`, and it does not check what `## Verification` says. Those sections are for the reader.

## Finding rules

| Rule | Severity | Meaning |
| --- | --- | --- |
| `milestone_name_invalid` | error | A folder is not named `v<digits>.<digits>.<digits>`. |
| `milestone_not_in_scheme` | error | A folder named as a version is outside the scheme, such as `v0.0.0`, `v0.0.100` or `v1.0.0`. |
| `link_escapes_root` | error | A milestone folder or file resolves outside the root, or cannot be resolved. It is not read. |
| `required_file_missing` | error | `spec.md` or `tasks.md` is missing. |
| `file_unreadable` | error | A file cannot be read, is not a regular file, is not UTF-8, or is larger than 1 MiB. |
| `requirement_duplicate` | error | `spec.md` defines the same requirement id twice. |
| `requirement_unclaimed` | error | A requirement defined in `spec.md` is cited by no table row of `tasks.md`. The detail names the id. |
| `task_cites_unknown_requirement` | error | A table row of `tasks.md` cites an id that `spec.md` does not define. |
| `reference_range_invalid` | error | A cited range ends before it starts, or covers more than 1000 ids, or an id has more than 9 digits. An invalid range cites nothing, so the requirements it would have covered can also be reported as unclaimed. |
| `reference_limit_exceeded` | error | `tasks.md` has more than 10,000 requirement references. Coverage is not computed. |
| `findings_truncated` | error | More than 50 findings of one coverage rule (`requirement_unclaimed` or `task_cites_unknown_requirement`); the first 50 are listed. |
| `checkpoint_version_mismatch` | error | `checkpoint.md` does not name its own `v<version>` in its first non-empty line, so a checkpoint copied from another milestone is caught. |
| `index_malformed` | error | A line of `MILESTONES.md` is not part of its format: a first non-empty line other than `# Milestones`, a missing description line, a heading that is not `## v<version> — <title> (Shipped: <date>)` with a version of the scheme, a missing or out-of-order list item, or a folder link that does not name its own version. |
| `index_order` | error | The entries of `MILESTONES.md` are not in strictly descending version order. |
| `index_duplicate` | error | A version is listed more than once in `MILESTONES.md`. |
| `index_link_broken` | error | The `Folder:` link of an entry names a folder that does not exist or is not a directory. |
| `index_date_invalid` | error | The date of an entry is not a real `YYYY-MM-DD` date. |
| `index_date_order` | error | An entry is dated earlier than an older entry below it. |
| `requirement_gap` | warning | The requirement ids do not run from R1 to the highest one without a gap. |
| `requirements_not_found` | warning | `spec.md` has no requirement item under `## Requirements`. No coverage rule runs. |
| `tasks_not_found` | warning | `tasks.md` has no table row. No coverage rule runs. |
| `decisions_missing` | warning | `decisions.md` is missing. |

## Lifecycle

**Start.** Run `milestone new --title "..."`. The folder takes the version after the one the manifests state, so the manifests must state the last version that shipped. Replace the placeholder requirement in `spec.md`, add one task row per requirement in `tasks.md`, and write `decisions.md`. Run `milestone check` until it passes.

**Run.** Keep `milestone check` passing. In this repository the `check` command runs it as a step (see below). A passing check shows that every requirement is cited and the structure is right. It does not show that a requirement is met.

**Bump.** Before the close, set the three manifests to this milestone's version in one change: `__version__` in `inonu_harness/__init__.py`, `version` in `pyproject.toml` and `version` in `.claude-plugin/plugin.json`. Also bump `.claude-plugin/marketplace.json` if it states a version. Run `python -m inonu_harness version --scheme`.

**Checkpoint.** Run the project's verification commands; their exit codes are the evidence that a task is done. Then write `checkpoint.md` by hand, with the state, the verification and its results, the limits, the next step and any deferred items with their reasons.

**Close.** Run `python -m inonu_harness milestone close VERSION --date YYYY-MM-DD`. It writes the milestone's entry into the index and changes nothing else.

**New again.** The next `milestone new` takes the version after the one just closed, because the manifests now state it.

The index starts at the first milestone closed with the command. Milestones closed before it have no entry, and none is backfilled. `close` tags nothing, moves nothing and deletes nothing: the folder and its files stay where they are, and the index is the only file it changes.

What `close` does not prove:

- That the verification commands were run or passed. `## Verification` must exist; what it says is not read.
- That the work is done or that the requirements are met. The count in the entry is the number of requirement ids, and the coverage rules show only that tasks cite them.
- Anything about the `Status:` line, `## Flow`, `## Next` or the wording of `## Limits`.
- That the date is the real shipping date. `--date` is the caller's claim, checked only against the order of the index.
- Anything about git. It reads the working tree, not a commit, and it does not check for a tag or a clean tree.
- That the index is untampered. `MILESTONES.md` is an ordinary file; `check` lints its format and cannot tell who wrote a line.
- That the deferred reasons are good. Each item needs one, and nothing reads it further.
- That the other milestones are sound. Only the closed one is checked, and warnings do not refuse, so a folder whose spec has no requirement item closes with `- Requirements: 0`.

## Older milestones: `--from`

The milestones before v0.0.9 of this repository predate the `R<n>` format. `check --from 0.0.9` skips the folders before that version: they are not read, so their problems are not reported. The `check` command runs `milestone check --from 0.0.9` as its `milestones` step, and only when `docs/specs/milestones` exists in the checked directory. A project whose first milestone uses the format from the start needs no `--from`.

## The `check` step

The `check` command runs the `milestones` step between `versions` and `tests`, in the checked directory and, with `--ref`, in the temporary export. Its exit code decides that step, as it does for the other steps.

## Compared with GSD

GSD (Get Shit Done) was the reference for this part. Kept: a scaffold that numbers a milestone in code, requirement ids that tasks must cover, a check that runs inside `check`, and a newest-first index of closed milestones. Left behind: GSD writes requirement status from model prose and marks a requirement Complete when it is executed, before verification. Here the check reads text and reports. It never edits a requirement, and "done" stays with the verification commands. GSD also creates a tag when it closes a milestone; `close` writes only the index entry.

## Limits

- The commands read only the formats above: the three files, the first line and the sections of `checkpoint.md` named in [The checkpoint](#the-checkpoint), `MILESTONES.md`, requirement items under `## Requirements`, and table rows. Other text is not read and is not checked.
- A reference written as `R1 - R3` (spaces) or `R1—R3` (em dash) is not a range, and `R2D2` or `R1_final` is not a citation. Ranges use `R1–R3` (en dash), `R1-R3` or `R1..R3`.
- They read and report, except that `close` writes one entry into `MILESTONES.md`. They never edit a requirement, a manifest or `checkpoint.md`. `new` writes only its three templates and the folders that hold them, and `close` writes only the index, through a temporary file beside it.
- They do not decide that a requirement is done. A citation means a task claims the requirement, not that the work passed.
- They do not check the wording of tasks or headings, whether a cited task is finished, or the content of `checkpoint.md` beyond the rules of [The checkpoint](#the-checkpoint).
- The version comes from the three manifests and from `marketplace.json` when it states one. Git tags and other files that state a version are not read.
- Files are read and written only below the root.
