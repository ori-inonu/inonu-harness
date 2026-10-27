# v0.0.22 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Source: gap G2 of the [source-level research](../v0.0.20/research-reverse-engineering.md).
- Scope: Jev returned `sem_consenso` twice ([decisions.md](decisions.md) D1). The second run, made after the owner pointed out that the judge needs the project's context, sent [brief.md](brief.md) and `AGENTS.md` as facts. The leader was (a) in both runs, so the most reversible option was adopted: a read-only `ownership` value in `bundle status`. The ledger migration, the `state` split and the `tools` allowlist stay deferred. D4 records what the judge sees and the rule that follows.
- A Haiku worker built the change, tests and docs (T01); an independent Haiku reviewer then attacked it (T02) and found 3 P1, 7 P2 and 5 P3 items.
- Review findings and the coordinator's resolution:
  - P1, a Codex server stayed `ours` after the user added a table or sub-table outside the markers (for example `[mcp_servers.codegraph.env]`). Fixed: `ours` now also requires that the table the whole file defines equals the one the marked block defines alone.
  - P1, `schema_version` of `true` or `1.0` was read as valid, so every item looked `ours`. Fixed in the shared ledger parser, so `status`, `apply` and `remove` refuse it alike. A ledger that `apply` wrote always holds the integer 1.
  - P1, an unreadable `SKILL.md` made `bundle status` exit 2 with no output, breaking R4. Fixed in `plan_bundle`: the skill is reported as `unknown`, for `status` and `plan`. `apply` is unchanged.
  - P2, the changelog said digests compare exact bytes, which is wrong for the Claude MCP entry and the Stop hook group (canonical JSON). Corrected here, in `docs/hosts.md` and in the spec.
  - P2, tests were missing for canonical JSON (reordered keys, changed `env`), a Stop group of the user placed first, an empty ledger, `schema_version` `true` and `1.0`, CRLF in the Codex file, an unreadable host file and another `inonu.py` command. All added; the apply test file also checks the `true` and `1.0` ledgers.
  - P3, the skill's `state` and `ownership` can disagree when its metadata file is deleted (`conflict` and `ours`). Documented, not changed. A Codex file fully rewritten with CRLF is `modified`, as `apply` reports a conflict; recorded as a decision, not a defect.
  - P3, no real symbolic link could be created on this host (no privilege): the test reports the same bytes as a link by patching `Path.is_symlink`. Not covered by a real link here.
- A mutation check broke the implementation in 10 ways (no sorted keys, `env` ignored, only the first Stop group, CRLF normalised, an empty ledger read as present, a boolean schema accepted, the `OSError` branch dropped, a narrower runner match, the Codex effective-table check dropped, the skill `OSError` not caught). All 10 were caught.
- The worker also reported that the real home's ledger and skill files had a recent modification time that it could not attribute. The only apply that ran before the worker started was this session's own, at the close of v0.0.21 (authorized), which is the likely cause; that was not checked against a timestamp. The worker ran every test against a temporary home.

## Verification

- `python -m unittest discover -s tests`: exit 0, 444 tests, 4 skipped (three POSIX-only, one file-symlink case that needs a privilege this host lacks).
- `python -m inonu_harness check`: exit 0. `python -m inonu_harness docs lint`: pass, 120 files. `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: both skills updated, nothing else changed.
- `bundle status` on the real home, read-only: ledger `present`; `ours` for both skills, the worker agent and the Codex `sequential-thinking` entry; `foreign` for the `codegraph` and `headroom` entries on both hosts and for the Claude `sequential-thinking` entry, which were registered before the bundle or by hand; `none` for the Stop hook, which is not installed. This matches what each file's history says.

## Limits

- `ownership` is advisory and read-only. `apply` and `remove` still decide from the ledger and the file contents at the moment of the write.
- `modified` covers a deleted item as well as an edited one.
- Not verified: POSIX paths, a real symbolic link or a read-denied file on this host (the reviewer exercised read-denied files with `icacls` in temporary homes; the committed tests patch the read).
- The ledger migration (verbatim entries, post-write digests) and the worker agent `tools` allowlist remain open and fenced.

## Next

Version 0.0.23 turns the prototype that built the Jev facts for D1's second run into a tested command (D4), so that no decision reaches the judge without a document. The commit and push still need the owner's go-ahead.
