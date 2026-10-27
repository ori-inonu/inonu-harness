# v0.0.20 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization; **the Stop hook was not installed**. This milestone does not complete the broader single-install objective.

## Flow

- Research first: five Haiku workers read the source of the reference projects (ECC, spec-kit, Graphiti and Beads, Anthropic's own plugin repositories) and verified the engineers' prescriptions against primary sources, with commits pinned ([research-reverse-engineering.md](research-reverse-engineering.md)). It also found wrong attributions in the v0.0.10 research, which are now corrected there.
- The reading exposed a functional defect (gap G1): a Stop hook blocks only on exit code 2, `check` exits 1 on failure, so the hook that `bundle apply --with-stop-hook` would register could never block; it also ran Inonu's own suite in every project, had no timeout and no block limit.
- Scope: Jev consensus for a real `hook stop` command ([decisions.md](decisions.md) D1). Two longer specs got `internal error` from `consensus_plan` and a shorter one worked; the failure is recorded. The exit-code-only fix and "leave it" scored rail probabilities of 0.52 and 0.86.
- Design decision (D2): a verifier config comes from the repository, so the hook runs it only after the owner records the SHA-256 of that exact config with `hook trust --yes`; any change makes it refuse. Findings exit 2, infrastructure problems exit 1 (non-blocking), and a block counter ends blocking after a configured maximum.
- Haiku workers built the hook and its tests (T01) and the bundle registration and docs (T02); an independent Haiku reviewer then tried to break it (T03). There were no P1 findings.
- Review findings and the coordinator's resolution:
  - P2, trust was bound to the config's resolved path, so a symlink or junction from one project's `.inonu` to another project's trusted config ran the trusted checks inside the wrong tree. The config must now be a plain file at `.inonu/verify.json` inside the project.
  - P2, a block counter that could not be stored made the hook block on every stop, so an agent could be trapped, and the unit test and docs codified it. The hook now exits 1 (non-blocking) when the counter cannot be stored.
  - P2, the credential scan covered only the 1500 shown bytes, so a token that began earlier leaked its visible suffix. The scan now covers the last 64 KiB and withholds the tail on any match.
  - P3: control characters from check output reached the terminal (now escaped); a check could write unbounded output (stopped at 16 MiB); stdin was read without a cap (1 MiB); an unledgered legacy Stop hook made `bundle remove` report success while status still showed it (now a conflict with a manual instruction).
- A mutation check broke the hook, the CLI and the bundle in 13 ways in temporary copies; the suite failed each time.

## Evidence

An end-to-end run in a temporary project, home and state directory: untrusted exits 1 without running anything; trusted and failing exits 2 with an empty stdout and the failing check's output tail; the second failure exits 2; at the limit it exits 0 and allows the stop. Nothing was written to the real home.

## Verification

- `python -m unittest discover -s tests`: exit 0, 396 tests, 4 skipped (three POSIX-only, one file-symlink case that needs a privilege this host lacks).
- `python -m inonu_harness check`: exit 0. `python -m inonu_harness docs lint`: pass, 111 files. `git diff --check`: exit 0.
- Repository audit with the credential scanner: only the three pre-existing placeholders in a doctor fixture remain.
- `bundle apply --host both` preview, then `--apply`: both skills updated; the hook item's preview carries a one-sentence note.

## Limits

- Nothing installs the hook unless the owner runs `bundle apply --with-stop-hook --apply` after `hook trust --yes`. A live Claude Code session has not been observed blocking a stop with it.
- A trusted config runs commands with the owner's permissions; trust records what was reviewed, it does not sandbox.
- The host applies its own cap on consecutive Stop blocks, which resets whenever a tool is called. The credential scan is a short list of formats and sees the last 64 KiB of output.
- Not run: the POSIX paths, `claude plugin validate`, a real plugin install. The research's source readings were not executed, and the engineers' blog posts were read through summaries.

## Next

The commit and push (the owner's go-ahead is needed), then `python -m inonu_harness check --ref HEAD`. Candidate work from the research gaps: ledger post-write digests and drift status (G2), a decision ready queue (G4), and an explicit `tools` allowlist for the worker agent (G6).
