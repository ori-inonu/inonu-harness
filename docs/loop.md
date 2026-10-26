# Loop runner reference

`python -m inonu_harness loop run SPEC.json` repeats one caller-chosen `step` command and checks the result with verifier commands. Success comes only from check exit codes, and every limit is mandatory. The runner never calls a model or a paid service itself. The `step` command is the caller's choice, and it may cost money.

From a checkout, `python scripts/inonu.py loop run SPEC.json` runs the same command.

## Spec format

The spec is strict JSON. Duplicate keys, unknown keys and wrong types are invalid input (exit 2).

| Key | Required | Type | Rules |
| --- | --- | --- | --- |
| `step` | yes | array of strings | Non-empty argv. Run once per iteration. |
| `checks` | yes | array of objects | Non-empty. Each object is `{"id": string, "argv": [string, ...]}`. Ids are unique and non-empty. |
| `limits` | yes | object | Exactly the four keys below, each a positive integer. No defaults. |
| `log` | yes | string | Path of the JSONL log file. |
| `cwd` | no | string | Working directory for every command. Default: the spec file's directory. |

Relative `log` and `cwd` paths are resolved against the spec file's directory. Absolute paths are used as given.

### Limits

| Limit | Maximum | Meaning |
| --- | --- | --- |
| `max_iterations` | 1000 | Step iterations allowed. Iteration 0 runs no step and is not counted. |
| `iteration_timeout_seconds` | 86400 | Time limit for each step or check process. |
| `total_timeout_seconds` | 604800 | Budget for the whole run, including iteration 0. |
| `stagnation_iterations` | 100 | Length of the unchanged streak that ends the run (see Stagnation). |

Every process is limited to `min(iteration_timeout_seconds, remaining total budget)`.

## Iteration flow

1. Validate the spec. Invalid input exits 2 before any command runs.
2. Iteration 0: run every check once, before any step. Each `passes` value is set from that check's exit code. If every check passes, the run stops with `verified_done` after 0 iterations, and the step never runs.
3. Iteration `k` (1, 2, ...): run `step` once, then every check, whether or not the step succeeded.
4. After the checks, update `passes`, list the ids that newly pass and the ids that regressed, and compute the failing signature and tree hash.
5. Apply the stop reasons in precedence order (below). Write the iteration's log line with `decision` and, when stopping, `stop_reason`. Continue if no reason applies.

Success is every check passing in the same iteration. A check that passed in an earlier iteration and fails later is a regression. It is logged in `regressed` and counted as failing.

A timed-out step or check is recorded with `timed_out: true`. A timed-out check counts as failing. A command that the spent total budget never let start is recorded with `not_run: true` (and `timed_out: false`); it fails the iteration but is not counted as a regression, because it did not run.

## Stop reasons

Each iteration, including iteration 0, is tested against these reasons in this order. The first one that applies is the status.

| Precedence | Status | Meaning | Exit |
| --- | --- | --- | --- |
| 1 | `verified_done` | Every check passed in this iteration. | 0 |
| 2 | `verifier_error` | A check could not start (for example, its executable is missing). It can never pass, so the run stops. | 1 |
| 3 | `wall_clock` | The total budget is spent. If the budget runs out during a step or check, that process is killed and recorded with `timed_out: true`; commands after it are recorded with `not_run: true`. | 1 |
| 4 | `max_iterations` | The iteration limit was reached without success. | 1 |
| 5 | `stagnation` | The unchanged streak reached `stagnation_iterations`. | 1 |

The summary printed on stdout has `status` (the stop reason), `iterations` (step iterations run), `passes` (check id to boolean), `regressions` (regressions recorded in the log) and `log` (the log path).

## Stagnation

- Failing signature: SHA-256 of the sorted failing check ids, each with its exit code and timeout flag. Command output is never part of it.
- Tree hash: SHA-256 over `HEAD`, the binary diff against it (staged diff plus unstaged diff in a repository without a commit yet) and the name and content of every untracked, non-ignored file under `cwd`. Files larger than 16 MiB are fingerprinted by size and modification time. The loop's own log is excluded, tracked or not, because it changes on every iteration. Ignored files are not part of the hash. The scope is `cwd` and below. When no `.git` entry exists at or above `cwd` the hash is the constant `"no-git"`; when git fails or stalls it is unknown (`null` in the log).
- Streak: an iteration with a step is *unchanged* when its failing signature and tree hash both equal the previous iteration's (iteration 0 is the first reference). The streak counts consecutive unchanged iterations; a changed iteration, or an unknown tree hash, resets it to 0. When the streak reaches `stagnation_iterations`, the status is `stagnation`. With `stagnation_iterations` of 2 and a step that changes nothing, the run therefore stops at iteration 2.

## Log

The log is append-only JSONL. It gets one object per line for iteration 0 and for each step iteration, and each write is flushed. Runs that share a log path append to the same file, and each run starts again at iteration 0.

| Field | Content |
| --- | --- |
| `iteration` | 0 for the baseline, then 1, 2, ... |
| `started_at`, `ended_at` | UTC ISO 8601 timestamps. |
| `step` | `null` for iteration 0. Otherwise `{"exit_code", "timed_out", "not_run", "duration_seconds"}`. |
| `checks` | List of `{"id", "exit_code", "timed_out", "not_run", "passes"}`. |
| `newly_passing` | Ids that pass in this iteration after failing before. |
| `regressed` | Ids that passed earlier and fail now. |
| `failing_signature` | Failing signature, as described under Stagnation. |
| `tree_hash` | Tree hash, as described under Stagnation. |
| `decision` | `continue` or `stop`. |
| `stop_reason` | The stop reason when `decision` is `stop`. |

The runner never writes argv, command output, environment variables or absolute paths to the log. The runner appends to it; it is not tamper-proof, because a step runs with the caller's permissions and can edit any file the caller can, including the log. The summary printed on stdout is ASCII-escaped, so a narrow stdout encoding cannot turn a finished run into exit 2.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | `verified_done`. |
| 1 | Any other stop reason. |
| 2 | Invalid input: a bad spec or an unreadable spec file. No iteration runs. |

## Safety notes

- Commands are argv lists run without a shell. There is no shell expansion, pipe, redirect or `&&`. Put such logic in a script file and call the script as one argv item.
- Stdin is closed for every command.
- Commands inherit the caller's environment, which can contain credentials. The runner does not filter it and does not write it to the log.
- Command output is not stored in the log or the summary.
- Commands run with the caller's operating-system permissions. The runner adds no sandbox, so a step can change any file the caller can change, and checks have the same access.
- The whole process tree of each command is killed when the command ends, not only on timeout. Anything a step leaves running (a server, a watcher) dies with it. POSIX: the command's own session and process group, SIGKILL. Windows: a Job Object with kill-on-close, which also reaches descendants whose parent already exited; if Windows refuses the job, `taskkill /T /F` is the fallback and orphans may survive. A process that deliberately escapes its session or job may also survive, and a descendant spawned in the instant before the Windows job is assigned can escape.
- The runner module makes no network calls and has no third-party dependencies.

## What it does not do

- It does not prove agent quality, that a change is correct, or that the checks test the right thing. `verified_done` means only that every check exited 0 in the same iteration.
- It does not resume an interrupted loop.
- It does no token, spend or model-usage accounting.
- It does not call a model or a paid service, and it does not choose or validate the `step` command. The `step` command may do either.
- It does not generate, install or change any host configuration, including a Claude Code Stop hook.
- Its limit values are unvalidated starting points, not measured thresholds.
- It does not sandbox commands or isolate the filesystem.
- Stagnation sees only the failing signature and the git-visible tree under `cwd`. Any change there, even a cosmetic one, restarts the streak, and changes in ignored files or outside `cwd` are not seen. Outside git, the tree hash is constant, so only the failing signature can produce `stagnation`.
