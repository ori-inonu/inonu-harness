# v0.0.14 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Research gaps first: four Haiku workers verified loop-engineering claims from primary sources ([research-verify.md](research-verify.md)). The OpenAI primary page stayed unreadable (HTTP 403) and is recorded as an open gap.
- Scope: Jev consensus for the runner with a baseline check and runner-owned `passes` ([decisions.md](decisions.md) D1).
- A Haiku worker built the runner and tests (T01) and another the docs (T02) in parallel; an independent Haiku reviewer then tried to break it (T03).
- Review findings and the coordinator's resolution:
  - P2, a verified run exited 2 when stdout could not encode the summary. The summary is now ASCII-escaped.
  - P2, the tree hash ignored the content of untracked files, so a loop that rewrote a new file every iteration stopped as stagnant. It now hashes untracked content, excluding the loop's own log (tracked or not).
  - P2, processes a finished step left running survived the verdict. The whole process tree is now killed when each command ends.
  - P2, on Windows `taskkill /T` could not reach orphaned grandchildren. A kill-on-close Job Object now covers them, with `taskkill` as the fallback.
  - P3: a repository without a commit, an unreadable repository (now "unknown", never stagnation), a budget-starved check reported as a regression (now `not_run`), docs that contradicted the streak rule, a missing precedence test, lone Unicode surrogates in the spec.
- A mutation check broke the runner in 12 ways in temporary copies; the suite failed each time. Two of the mutants deliberately disable the process-tree kill, and the three infinite ticker processes they left behind were stopped by PID. A rerun of the leak tests on the real code left no process behind.

## Verification

- `python -m unittest discover -s tests`: exit 0, 213 tests, 3 POSIX-only skipped.
- `python -m inonu_harness check`: exit 0.
- `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: both skills updated.

## Limits

- Not verified: the POSIX path (process group kill, git behaviors) was reviewed and tested only for logic on this Windows host; CI on Linux has not run it.
- A process that deliberately escapes its session or job, or a descendant spawned in the instant before the Windows job is assigned, can survive.
- The log is not tamper-proof: a step runs with the caller's permissions.
- No resume, no token or spend accounting, no generated host hook. Limit values and the stagnation window are unvalidated starting points.
- `verified_done` means only that every check exited 0 in the same iteration.

## Next

The remaining research gaps (the OpenAI page, the SubagentStop section) need another source or a different fetch route. A candidate next milestone is a CI run on Linux for the loop runner's POSIX path, which does not need host configuration.
