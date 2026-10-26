# Inonu Harness

Inonu is a local, reproducible toolkit for observing an agent environment, evaluating deterministic fixtures, and keeping a persistent history of engineering decisions. It complements the current Codex runtime and SDD workflow; it does not replace either.

## Local capabilities

- A read-only environment doctor that emits sanitized JSON and labels facts it cannot verify as `unknown`.
- An offline baseline runner and comparison command. Every metric carries provenance; unavailable values stay `null`. An opt-in `--max-regression R` gate on `baseline compare` exits 0, 1 or 2 over two saved local measurements; it does not measure agent quality.
- An M0 SQLite Decision Graph with revisions, evidence, dependencies, idempotency, and separate recommendation and authorization records.
- An M0 typed JEV adapter that uses an injected MCP transport, plus a deterministic mock. Jev MCP calls were observed in the coordinator chat on 2026-10-24; that host/session observation does not establish access from other clients or a portable CLI. No portable live JEV transport is implemented or configured.
- M1–M2 read-only decision context for explicit IDs, exposed through an opt-in adapter and the manual `decisions context` command. M4 adds `decisions packet`, which combines a caller-provided task file with explicitly selected decisions; it rejects duplicate JSON object keys.
- An optional `sdd audit` command checks explicit requirement, task, verification, and local evidence links from a v1 manifest. It is read-only and does not add a step to the SDD sequence.
- M3 documents an exploratory evaluation protocol only; the pilot has not been run. The optional SDD gate is disabled by default, and the existing eight SDD steps remain the normal workflow.
- A standard-library loop runner, `loop run`, that repeats a caller-chosen `step` command and stops on verifier exit codes under four mandatory limits. It writes a JSONL log, calls no model, and proves nothing about agent quality.
- An opt-in Stop hook, `hook stop`, that runs a project's trusted `.inonu/verify.json` checks on each Stop and blocks the stop on a failing check (exit 2). The owner grants trust per config with `hook trust --yes`, which records its SHA-256; nothing installs the hook unless `bundle apply --with-stop-hook --apply` is run. See [the hook reference](docs/hook.md).

JEV recommendations are advisory and never grant authorization. Local authorization requires evidence for each required criterion, and recording it does not execute an external operation.

See [native host profiles](docs/hosts.md) for preview/apply instructions, portable runner use, and host discovery limits. [CHANGELOG.md](CHANGELOG.md) records implemented milestones and proposals.

The code uses Python 3.11+ and the standard library. No global installation or runtime package dependency is needed to run it from this checkout.

## Install as a Claude Code plugin

The repository is also a Claude Code plugin and its own marketplace. Install it with `/plugin marketplace add ori-inonu/inonu-harness`, then `/plugin install inonu-harness@inonu-harness`. It provides the Inonu skill, a Haiku worker agent and the Python runner. It needs Python 3.11+ reachable as `python`, and it starts no MCP server and no hook; `bundle apply` remains the previewed path for those. The package has not been run through `claude plugin validate` and no live installation was tested, so validate it before relying on it. Details and unverified points are in [the plugin reference](docs/plugin.md).

## Run locally

From the repository root:

```powershell
python --version
python -m inonu_harness doctor
python -m unittest discover -s tests -v
```

Run a deterministic fixture and compare two saved results:

```powershell
python -m inonu_harness baseline run fixtures/baseline/offline-smoke.json --execution-id before > before.json
python -m inonu_harness baseline run fixtures/baseline/offline-smoke.json --execution-id after > after.json
python -m inonu_harness baseline compare before.json after.json
```

The fixture path may be positional or supplied with `--fixture PATH`.

Add `--max-regression R` to gate a comparison. `R` is a finite number of at least 0, so `0.10` allows a 10% increase. The output gains a `gate` object. Exit codes: 0 for `pass`, 1 for `fail` (a judged metric regressed), 2 for `incomparable` (task, config or schema differ, or `R` is invalid). The gate compares two saved local measurements and does not establish agent quality or productivity:

```powershell
python -m inonu_harness baseline compare before.json after.json --max-regression 0.10
```

Run the deterministic gate for this checkout. It compiles `inonu_harness`, `scripts` and `tests`, then runs the unit tests. It prints one JSON summary and exits 0 only when every step passes; child output goes to stderr. Use `--root PATH` to check another checkout with the same layout:

```powershell
python -m inonu_harness check
```

To verify a commit instead of the working tree, commit first and run `check --ref HEAD`. The command writes that commit's own blobs (read with `git ls-tree` and `git cat-file`, so `.gitattributes` rules such as `export-ignore` and `export-subst`, and line-ending settings, do not change them) to a temporary directory, runs the same compile and test steps there, then runs `scripts/inonu.py --version` as a `runner` step, and removes the export. The JSON adds `ref`. Exit codes: 0 for a pass, 1 for a failed step, 2 for invalid input such as a root outside a git repository or a ref that is not a commit. A pass shows that the commit is self-contained for its tests and its runner. It does not show that the plugin installs. The check covers the operating system where it runs only, and the CI workflow is unchanged. See [the plugin reference](docs/plugin.md#before-you-push).

```powershell
python -m inonu_harness check --ref HEAD
```

Preview the read-only bundle plan for Claude Code. It prints one JSON object and writes nothing. Worker agent, hook and MCP items report `"applied": false`:

```powershell
python -m inonu_harness bundle plan --host claude
```

Install or remove the bundle. Each command previews by default and writes nothing until `--apply` is given. Add `--with-stop-hook` only if you accept that the Stop hook runs each trusted project's verifier on every Stop; the hook runs only a config that `hook trust --yes` has recorded for that project, and [the hook reference](docs/hook.md) explains the trust workflow and exit codes. Preflight conflicts exit 2 and write nothing. Host configuration writes are authorized by the owner (see the v0.11.0 decisions):

```powershell
python -m inonu_harness bundle apply --host claude
python -m inonu_harness bundle apply --host claude --apply
python -m inonu_harness bundle remove --host claude --apply
```

Check how far each host already matches that plan. `bundle status` is read-only and reports per-item states such as `current`, `absent` or `configured`; configuration is not proof of reachability:

```powershell
python -m inonu_harness bundle status --host claude
```

Each item also gets an `ownership` value from the ledger that `bundle apply` writes: `ours`, `modified` (recorded, then edited or deleted), `foreign` (present but not recorded), `none` or `unknown`. The top-level `ledger` reports `absent`, `present` or `unreadable`. Ownership is advisory and read-only; it changes nothing that `apply` or `remove` does.

Audit one frozen synthetic SDD case. The evidence root defaults to the manifest's directory; these shared fixtures use `--root fixtures/sdd_audit`:

```powershell
python -m inonu_harness sdd audit fixtures/sdd_audit/clear-change/manifest.json --root fixtures/sdd_audit
```

The command prints a JSON report and returns 0 for a pass, 1 when the manifest has findings, or 2 for invalid input. Evidence hashes detect byte drift, but do not establish semantic correctness or authenticate that a check actually ran. See [the SDD guide](docs/sdd-workflow.md) for scope and limitations.

Create a decision and inspect it. The database defaults to `~/.inonu-harness/decisions.sqlite`, outside the checkout; pass `--db PATH` after `decisions` to choose another file. The directory is created only when a decision command runs.

```powershell
python -m inonu_harness decisions create storage-choice `
  --question 'Which local persistence mechanism should M0 use?' `
  --alternatives '[{"id":"sqlite","label":"SQLite"},{"id":"json","label":"JSON file"}]' `
  --criteria '["durable"]' `
  --constraints '["standard library only"]' `
  --idempotency-key create-storage-choice
python -m inonu_harness decisions list
python -m inonu_harness decisions show storage-choice
```

`decisions recommend` records an existing recommendation; it does not call JEV. `decisions authorize` records an explicit local authorization only when every required criterion has evidence. Recording authorization does not execute an external operation.

`decisions as-of TIMESTAMP [--ids ID...]` shows what each decision looked like at an instant, read from its revision history. The timestamp needs an explicit offset or `Z`, the database must already exist, and nothing is written. Each item reports `state` (`existed` or `not_yet_created`), its revision, `recorded_at`, `later_revision` and a snapshot shaped like `decisions show`. The times come from the clock of the machine that recorded each revision and are not authenticated, so this is a local audit aid and not a tamper-proof ledger. It cannot show a state before the first revision, and it changes no schema.

`decisions ready` lists the pending decisions whose declared `dependencies` are all authorized; a decision with no dependencies is ready. Pending decisions that still wait appear under `waiting` with `waiting_on`, the dependencies that are not authorized, in declared order, each with its `status` (`missing` when the database has no such decision). Blocked, invalidated and authorized decisions are not listed. The database must already exist and is opened read-only. The output includes each decision's question text, as `show` does, and does not scan for credentials. `ready` only reports the dependency state: it does not authorize, claim, schedule or record approval for a decision.

`decisions context` and `decisions packet` accept `--refuse-secret-patterns`, an opt-in guard for output that will be attached to an agent. With the flag, the command scans exactly the object it would print, including a packet's task prompt, for a short list of credential formats. On a match it prints nothing to stdout, writes one stderr line with rule names and paths only, and exits 2. Without the flag the output is unchanged. The guard catches only the listed formats: it does not catch passwords in prose, custom tokens or most other credential formats, it can raise false positives, and it never prints a matched value. It does not redact and does not scan the database.

`jev spec` builds a Jev decision spec whose facts are the text of the documents that describe the problem, so the judge decides from the project's context and not from a summary. Pass the decision as a JSON file with `id`, `goal`, `rails` and `options`, and at least one `--doc`:

```powershell
python -m inonu_harness jev spec --decision decision.json --root . --doc docs/sdd-workflow.md > spec.json
```

Each document gives a source fact (its path relative to `--root` and a 16-digit SHA-256 prefix), then its text in chunks of at most 300 characters, in the order given. The command calls no Jev, writes no file and decides nothing. It exits 2, with nothing on stdout, when no document is given, when a document is not a regular UTF-8 file inside `--root`, when a value is over a Jev limit, or when the facts exceed `--max-facts` (default 80). It never truncates. The document should describe the problem and the constraints, not the answer; the command cannot check that. See [the SDD guide](docs/sdd-workflow.md).

## Run a verification loop

`loop run` repeats one `step` command and checks the result with verifier commands. Success comes only from check exit codes, and the four limits are mandatory. The runner never calls a model; the `step` command is yours and may cost money. Save this spec as `loop.json` in any directory; `answer.txt` and `loop.jsonl` are created next to it:

```json
{
  "step": ["python", "-c", "import pathlib; pathlib.Path('answer.txt').write_text('42')"],
  "checks": [
    {"id": "answer-file", "argv": ["python", "-c", "import pathlib, sys; p = pathlib.Path('answer.txt'); sys.exit(0 if p.is_file() and p.read_text() == '42' else 1)"]}
  ],
  "limits": {
    "max_iterations": 3,
    "iteration_timeout_seconds": 60,
    "total_timeout_seconds": 300,
    "stagnation_iterations": 2
  },
  "log": "loop.jsonl"
}
```

From the repository root, pass the spec's path:

```powershell
python -m inonu_harness loop run path/to/loop.json
```

The check fails on the baseline run, the step writes `answer.txt`, and the next check passes, so the run stops with `verified_done` after one iteration. Delete `answer.txt` before a rerun; otherwise the baseline check passes and the step never runs. Exit codes: 0 for `verified_done`, 1 for any other stop, 2 for invalid input. See [the loop reference](docs/loop.md).

## Lint instruction and documentation files

`docs lint` checks the instruction files (`AGENTS.md`, `AGENTS.override.md` and `CLAUDE.md`) for size, `@path` imports and UTF-8, and checks links in `README.md` and the Markdown files under `docs/`. It prints one JSON object, writes no file, and exits 0 for `pass`, 1 for `fail` (each finding has a `remediation` sentence) and 2 for invalid input. It checks links and size only: a pass does not show that a document is true or current, and heading anchors are not verified.

```powershell
python -m inonu_harness docs lint
python -m inonu_harness docs lint --root PATH --max-bytes 32768 --max-lines 200
```

The 200-line default is a configurable starting point, not a documented limit.

## Layout

- `inonu_harness/` — doctor, baseline, Decision Graph, JEV contract/mock and the document-based spec builder, loop runner, and CLI.
- `fixtures/` and `tests/` — deterministic, offline examples and checks.
- `docs/specs/milestones/v0.1.0/` — M0 requirements, decisions, plan, tasks, and checkpoint.
- `docs/integrations.md` — observed states, contracts, overlaps, licenses, and validation ideas.
- `docs/sdd-workflow.md` — the current SDD sequence and optional graph boundary.

See [the SDD guide](docs/sdd-workflow.md), [integration inventory](docs/integrations.md), and [benchmark plan](docs/benchmark-plan.md) before changing the workflow or claiming performance gains.

## Scope and license

The project does not install or reimplement RTK, Headroom, Ponytail, CodeGraph, or Sequential Thinking. No external tool source is copied. The public repository has not declared a project license; public visibility alone does not grant reuse rights.
