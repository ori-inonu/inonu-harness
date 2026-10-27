# v0.0.14 — Deterministic loop runner

Research in [research-verify.md](research-verify.md) shows the reviewed loop designs end on an agent-written sentinel and none reads a verifier result, while the vendor docs prescribe an external exit-code gate. This milestone adds a runner whose success comes only from verifier exit codes and whose limits are mandatory. It never invokes a model or any paid service itself; what the `step` command runs is the caller's choice and cost. It touches no host configuration. The scope was chosen by Jev consensus ([decisions.md](decisions.md)).

## Requirements

- R1 `python -m inonu_harness loop run SPEC.json`. Output is one JSON summary on stdout. Exit codes: 0 `verified_done`, 1 any other stop, 2 invalid input (bad spec, unreadable file). Spec paths are resolved against the spec file's directory unless absolute.
- R2 Spec (strict JSON; duplicate keys, unknown keys and wrong types are invalid input):
  - `step`: argv list, non-empty strings — the command run once per iteration.
  - `checks`: non-empty list of `{"id": str, "argv": [str, ...]}` with unique non-empty ids.
  - `limits`: all four required positive integers, with no defaults: `max_iterations` (≤ 1000), `iteration_timeout_seconds` (≤ 86400), `total_timeout_seconds` (≤ 604800), `stagnation_iterations` (≤ 100).
  - `log`: path of the JSONL file.
  - `cwd`: optional working directory (default the spec's directory).
  Commands run as argv lists without a shell, with stdin closed, in fresh subprocesses, with the caller's environment.
- R3 Loop:
  - Iteration 0 runs every check once, before any step. If all pass, the status is `verified_done` after 0 iterations and the step never runs.
  - Each iteration then runs `step`, then every check, whether or not the step succeeded.
  - `passes` per check id is owned by the runner and set only from that check's exit code (0 → true). A check that passed earlier and fails later is a `regression`, logged and counted as failing.
  - Success is every check passing in the same iteration.
- R4 Stop reasons, in this precedence per iteration: `verified_done`; `verifier_error` (a check cannot start, so it can never verify); `wall_clock` (total budget spent, including mid-run); `max_iterations`; `stagnation`. The summary has `status` (the reason), `iterations`, `passes` (id → bool), `regressions`, `log`.
- R5 Timeouts and process trees: every subprocess is limited to `min(iteration_timeout_seconds, remaining total)`. The command's whole process tree is killed when it ends (normally, on timeout or on an interrupt): POSIX uses its own session and process group with SIGKILL; Windows uses a kill-on-close Job Object, with `taskkill /T /F` as the fallback. A timed-out step or check is recorded with `timed_out: true`; a timed-out check counts as failing. A command the spent total budget never let start is recorded with `not_run: true` and is not counted as a regression.
- R6 Stagnation: the failing signature is the sha256 of the sorted failing check ids with their exit codes and timeout flags. The tree hash is the sha256 of `HEAD`, the binary diff against it (staged plus unstaged diff in a repository without a commit) and the name and content of each untracked, non-ignored file under `cwd` (files over 16 MiB by size and mtime), excluding the loop's own log. It is the constant `"no-git"` when no `.git` entry exists at or above `cwd`, and unknown (`null`, which resets the streak) when git fails or stalls. If both are unchanged for `stagnation_iterations` consecutive iterations (counting from the first iteration with a step), the status is `stagnation`. Command output is never part of the signature.
- R7 Log: append-only JSONL, one object per iteration (including iteration 0), flushed after each write. Fields: `iteration`, `started_at`, `ended_at` (UTC ISO 8601), `step` (`null` for iteration 0, else `{"exit_code", "timed_out", "not_run", "duration_seconds"}`), `checks` (list of `{"id", "exit_code", "timed_out", "not_run", "passes"}`), `newly_passing`, `regressed`, `failing_signature`, `tree_hash`, `decision` (`continue` or `stop`), `stop_reason`. The log contains no argv, output, environment or absolute paths.
- R8 The runner module has no network access and no dependencies. Its core is a pure-ish function `run_loop(spec, ...)` that takes injectable `clock`/`runner` seams for tests.
- R9 Tests (deterministic, using `sys.executable -c ...` commands in temp directories):
  - success after N iterations;
  - already-passing baseline runs zero steps;
  - `max_iterations`;
  - `wall_clock`;
  - a step timeout kills its grandchild;
  - `stagnation` after exactly K iterations;
  - a tree change resets stagnation;
  - regression recorded;
  - `verifier_error`;
  - every invalid-spec case exits 2;
  - the log is valid JSONL and contains none of a planted secret argv or output;
  - the CLI exit codes.
- R10 Docs: CHANGELOG 0.0.14, README, a new `docs/loop.md` (spec format, stop reasons, what the runner does not do), source skill bullet. Version 0.0.14. The docs state that the runner proves nothing about agent quality, that thresholds are unvalidated starting points, and that it neither resumes an interrupted loop nor writes any host hook.

## Out of scope

Resume after interruption, token or spend accounting, a generated Claude Code Stop hook, any call to a model, and host configuration.
