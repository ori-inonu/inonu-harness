# Versioning and milestones

This page describes the version scheme that the Inonu Harness uses for any project it manages. The last section gives this repository's own renumbering.

## The scheme

A version has the form `0.MINOR.PATCH`. Each part is an integer from 0 to 99 written without leading zeros, and `0.0.0` is not a version. The scheme runs from `0.0.1` to `0.99.99`.

Each milestone takes the next version. Milestone number `n` has the version

    0.(n // 100).(n % 100)

| Milestone | Version |
| --- | --- |
| 1 | `0.0.1` |
| 24 | `0.0.24` |
| 99 | `0.0.99` |
| 100 | `0.1.0` |
| 199 | `0.1.99` |
| 200 | `0.2.0` |
| 9999 | `0.99.99`, the last version of the scheme |

After `0.0.99` the next milestone is `0.1.0`, and the patch starts again at 0.

`1.0.0` is never computed. It is the owner's decision.

## Rules for every project

- Every file that states the project's version carries the version of the current milestone, and a release edits them together. In this repository these files are `inonu_harness/__init__.py`, `pyproject.toml`, `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` when it states a version.
- A project that keeps milestone artifacts names each milestone directory after its version, `docs/specs/milestones/vMAJOR.MINOR.PATCH`, for example `docs/specs/milestones/v0.0.24`.

## Commands

Both commands read files only. They write nothing and change no manifest.

    python -m inonu_harness version --root PATH              # the stated versions agree
    python -m inonu_harness version --root PATH --scheme     # ... and each one is in the scheme
    python -m inonu_harness version --root PATH --next       # print the next milestone's version

- Without flags, the command exits 0 when the stated versions agree and 1 when they differ, when a file has no version, or when a manifest cannot be read or parsed. Each problem is one line on stderr.
- `--scheme` also exits 1 for a version outside the scheme.
- `--next` prints the next version on stdout, computed from the version the manifests state, and exits 0. It exits 1, with the problems on stderr, when the manifests disagree or leave the scheme, when no manifest states a version, and when the version is `0.99.99`.
- A root that is not a directory exits 2.

`--root` defaults to the current directory. To check another project from any directory, run `python /path/to/inonu-harness/scripts/inonu.py version --root /path/to/project --scheme`.

## Adopting the scheme

A project that does not start at `0.0.1` adopts the scheme with its next milestone:

1. Find the last version the project has used.
2. The next milestone takes the next version of the scheme after it. It never takes a lower version, so a version that was published or recorded keeps its place. `version --next` prints that version once the manifests state the last one.
3. A project that has used no version of the scheme yet has its owner choose the starting version. `0.0.1` is the natural start.
4. If the last version is outside the scheme, such as `1.4.0`, the owner decides the next one. The scheme does not go past `0.99.99`.
5. Update every stated version in the same change, and name the new milestone directory after its version.

## This repository's renumbering

Earlier milestones of this repository were numbered `v0.N.0`. They now carry `v0.0.N`, for N from 1 to 24. The milestone directories, the references in the docs, the tests and the manifests use the new numbers. Git commit messages, Jev spec ids such as `inonu-v021-small-gaps`, and receipts keep the old numbers, and the history was not rewritten. This table decodes the old numbers.

| Old | New | Old | New |
| --- | --- | --- | --- |
| v0.1.0 | v0.0.1 | v0.13.0 | v0.0.13 |
| v0.2.0 | v0.0.2 | v0.14.0 | v0.0.14 |
| v0.3.0 | v0.0.3 | v0.15.0 | v0.0.15 |
| v0.4.0 | v0.0.4 | v0.16.0 | v0.0.16 |
| v0.5.0 | v0.0.5 | v0.17.0 | v0.0.17 |
| v0.6.0 | v0.0.6 | v0.18.0 | v0.0.18 |
| v0.7.0 | v0.0.7 | v0.19.0 | v0.0.19 |
| v0.8.0 | v0.0.8 | v0.20.0 | v0.0.20 |
| v0.9.0 | v0.0.9 | v0.21.0 | v0.0.21 |
| v0.10.0 | v0.0.10 | v0.22.0 | v0.0.22 |
| v0.11.0 | v0.0.11 | v0.23.0 | v0.0.23 |
| v0.12.0 | v0.0.12 | v0.24.0 | v0.0.24 |

## Limits

- Versions are compared as exact text. `0.0.24.0`, `v0.0.24` and `0.0.24 ` are not the same as `0.0.24`.
- A version is at most 40 characters.
- The commands read text and parsed data only. They do not check Git tags, installed copies of the plugin or other files that state a version.
