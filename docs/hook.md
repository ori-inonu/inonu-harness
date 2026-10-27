# Stop hook

The Stop hook runs a project's verifier checks when Claude Code is about to end a turn, and blocks the stop when a check fails. It is opt-in. Nothing installs it, and it runs a project's checks only after the owner has trusted that project's config. The entry point is `python -m inonu_harness hook stop`, which reads the hook's JSON from stdin. `bundle apply --with-stop-hook --apply` registers it through the runner (see [install and remove](#install-and-remove-through-the-bundle)).

The hook does not run this repository's own test suite. It runs only the checks listed in the project's `.inonu/verify.json`.

## Project config

The config is `.inonu/verify.json` directly inside the project directory (see [project directory](#project-directory)). Ancestor directories are not searched. A missing file is a silent no-op: exit 0, no output.

The file is strict JSON of at most 64 KiB with exactly three keys, all required:

```json
{
  "checks": [
    {"id": "readme-present", "argv": ["python", "-c", "import pathlib, sys; sys.exit(0 if pathlib.Path('README.md').is_file() else 1)"]}
  ],
  "timeout_seconds": 120,
  "max_consecutive_blocks": 3
}
```

- `checks` holds 1 to 20 objects. Each has exactly an `id` string and an `argv` list of strings. Ids are non-empty and unique; each `argv` is non-empty. A check runs as an argv list with no shell, sequentially, in the project directory, with stdin closed.
- `timeout_seconds` is an integer from 1 to 600. It is one budget shared by all checks.
- `max_consecutive_blocks` is an integer from 1 to 20. See [block limit](#block-limit).

A duplicate key, an unknown key, a wrong type (a boolean is not an integer), an out-of-range value or a file over 64 KiB makes the config invalid. Invalid config exits 1 and names the problem without echoing the file's content.

For a real project, put your own verifier in `argv`, for example `["python", "-m", "unittest", "discover", "-s", "tests"]`.

## Trust

A repository can ship `.inonu/verify.json`, so the hook runs it only after the owner records its SHA-256. From the project, or with `--root`:

```powershell
python -m inonu_harness hook trust --root PATH
python -m inonu_harness hook trust --root PATH --yes
python -m inonu_harness hook untrust --root PATH
```

- Without `--yes`, `hook trust` prints a preview: the resolved config path, the SHA-256, and every check id and argv in order. It writes nothing. Read the list before you trust it.
- With `--yes`, it records the digest against the resolved path in `<home>/.inonu-harness/hook-trust.json`. The file is replaced atomically. `--home PATH` chooses another home directory, which the tests use.
- `hook untrust` removes that record.
- The hook reads the trust file and never writes it. A config with no record, or whose bytes differ from the recorded digest, exits 1 before any check runs. Every edit to the config needs a new `hook trust --yes`, including whitespace.
- A trust file that cannot be read or parsed exits 1 as well, and the message says to fix it or move it aside.

Trust is the owner's decision. Recording it runs nothing by itself, but afterwards every Stop in that project runs the listed commands with the owner's permissions. An agent should not run `--yes` on the owner's behalf.

## Exit codes

| Exit | Meaning | Effect on the stop |
| --- | --- | --- |
| 0 | Every check passed, the project has no config, or the block limit was reached. | The stop proceeds. |
| 2 | A check failed or timed out. Stderr holds the message the model sees. | The stop is blocked. |
| 1 | An infrastructure problem: invalid or untrusted config, a drifted or unreadable trust file, or an unexpected error. | A non-blocking error that the owner sees. |

The codes follow how Claude Code reads a Stop hook: it blocks a stop only on exit 2, and any other non-zero code is a non-blocking error. A broken config or a crash therefore cannot trap an agent, and only a failing check blocks. The hook prints no traceback.

## Output

Stdout stays empty. On a failed run, stderr holds one message with:

- the attempt, as `attempt N of MAX`, where `MAX` is `max_consecutive_blocks`;
- each failing check id with its exit code, or `timed out`;
- one line asking the model to fix the failing checks and try again; and
- for each failing check, the last 1500 bytes of its output.

Each output tail first passes the credential-pattern scan in `inonu_harness/secret_scan.py`, the same rules as `--refuse-secret-patterns`. A tail that matches is replaced by a note that names only the rule names. The whole message is capped at 4000 characters and marked when it is truncated.

## Project directory

The hook uses `$CLAUDE_PROJECT_DIR` when it is set. Otherwise it uses the hook JSON's `cwd` when that names a directory. Otherwise it uses the process working directory. The hook reads its JSON from stdin, and an empty or invalid body counts as `{}`.

## Timeouts

Checks run one after another, each with the time left in the single `timeout_seconds` budget. A check that exceeds its share is killed, and so is every process it started. It is reported as `timed out`. The bundle registers the hook with a host timeout of 630 seconds, above the 600-second maximum for `timeout_seconds`. Process-tree handling is exercised by the repository's tests on the operating system where they run; other systems are not checked.

## Block limit

A failing run increments a counter of consecutive blocks, and a passing run resets it. The counter is a small JSON file in the system temporary directory, named `inonu-hook-state/<first 16 hex of sha256(session_id + config path)>.json`. A missing `session_id` counts as an empty string.

When the counter has already reached `max_consecutive_blocks`, the hook resets it, writes one line to stderr and exits 0. The stop is allowed, so a check that never passes ends its blocking after that many attempts. If the counter cannot be stored (for example the state directory is not writable), the hook cannot enforce the limit and so it never blocks: it exits 1, which the host treats as non-blocking, with a message saying so.

## Limits

- The checks are commands from the project. Trust records what was reviewed, but it does not sandbox them: a trusted config can run anything the owner's account can run.
- The host applies its own cap on consecutive Stop blocks, and that cap resets whenever a tool is called. The host's cap can therefore end a loop before this hook's block limit does.
- The output scan is a short list of credential formats. A tail that passes it still reaches the model, and so does any text the scan does not recognize. A match is replaced; nothing is redacted.
- While the counter cannot be written, a failing check does not block at all (exit 1 with a message), because the limit could not be enforced. The host's own cap is the only other limit.
- The config must be a plain file at `.inonu/verify.json` inside the project: a symlink or junction that leads to another place, even to another trusted config, is refused (exit 1), because trust is bound to the project path.
- A check is stopped when it writes more than 16 MiB to its output. The credential scan covers the last 64 KiB of the output, and the text shown is the last 1500 bytes of it with control characters escaped. A credential that begins more than 64 KiB before the end of the output is not seen by the scan.
- A legacy Stop hook from before this version (a command ending in ` check`) that the ledger did not record cannot be removed by `bundle remove`, which reports a conflict; delete that group from the `hooks.Stop` list of `~/.claude/settings.json` by hand. A recorded legacy group is removed normally.
- Not included: an ancestor config search, a special case for `stop_hook_active`, async hooks, and SubagentStop hooks.
- The repository's tests drive the hook with temporary directories and with one end-to-end run of `python -m inonu_harness hook stop` on stdin JSON. A live Claude Code session has not been observed blocking a stop.

## Install and remove through the bundle

```powershell
python -m inonu_harness bundle apply --host claude --with-stop-hook
python -m inonu_harness bundle apply --host claude --with-stop-hook --apply
python -m inonu_harness bundle remove --host claude --with-stop-hook --apply
```

The first command previews and writes nothing. Its stop-hook item carries a `note` that says what the hook does. With `--apply`, the bundle adds one Stop group to the Claude settings:

```json
{"hooks": [{"type": "command", "command": "python '<checkout>/scripts/inonu.py' hook stop", "timeout": 630}]}
```

The ownership ledger records the group's hash. `bundle remove` reverses the group only while that hash still matches, and keeps it when someone edited it. Nothing installs the hook unless the owner runs `bundle apply --with-stop-hook --apply`.

An earlier registration ending in ` check`, from before 0.0.20, is still recognized as an Inonu hook. `bundle status` reports it as `present`, and `bundle apply` reports a conflict rather than adding a second group. Run `bundle remove --host claude --with-stop-hook --apply` first; it reverses that registration only when the ledger recorded it. Then apply again.

See [native host profiles](hosts.md#install-the-full-bundle) for the ledger, backups and conflict rules, and [the plugin reference](plugin.md) for why the plugin itself ships no hook.
