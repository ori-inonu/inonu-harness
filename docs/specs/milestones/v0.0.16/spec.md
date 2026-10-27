# v0.0.16 — Documentation lint and enforced architecture rules

The OpenAI harness-engineering post ([research-verify.md](research-verify.md)) found that a short instruction file acting as an index worked where one giant file failed, that freshness and cross-links were enforced by linters and CI, that custom lint messages should carry correction instructions into the agent's context, and that architecture rules were enforced by structural tests rather than prose. Inonu states "standard library only" in `AGENTS.md` but no test enforces it, and its documentation links are unchecked. This milestone closes both. It is read-only: it writes no file and calls no model. The scope was chosen by Jev consensus ([decisions.md](decisions.md)).

## Requirements

- R1 `python -m inonu_harness docs lint [--root PATH] [--max-bytes N] [--max-lines N]` (root default: the current directory). Prints one JSON object on stdout and exits 0 for `pass`, 1 for `fail` (at least one finding) and 2 for invalid input (a root that is not a directory, a non-positive limit). It never writes a file.
- R2 Output: `{"schema_version": 1, "status": "pass"|"fail", "files_checked": int, "findings": [...]}`. Each finding has `rule`, `file` (root-relative, forward slashes), `line` (1-based, or `null`), `detail` and `remediation` (one sentence telling the agent exactly what to change). Findings are sorted by file, then line, then rule. No absolute path appears anywhere in the output.
- R3 Instruction files are `AGENTS.md`, `AGENTS.override.md` and `CLAUDE.md` in the root. Rules:
  - `instruction_file_too_large` when the file is larger than `--max-bytes` (default 32768, the documented Codex project-doc default);
  - `instruction_file_too_long` when it has more than `--max-lines` lines (default 200; a configurable starting point, not a documented limit);
  - `import_missing` for a line that is an `@path` import (the whole stripped line is `@` followed by one path token) when the target does not exist relative to the file. `@~/...` and `@/...` imports are not checked and fenced code blocks are skipped;
  - `file_unreadable` when the file is not valid UTF-8.
- R4 Link rules apply to the instruction files, `README.md` and every `*.md` under `docs/`. A link is `[text](target)`, `![alt](target)` or a reference definition `[label]: target`; fenced code blocks and inline code spans are skipped. Targets with a scheme (`https:`, `mailto:` and so on), a `#fragment` alone or an absolute path are not checked; a trailing `#fragment` or `?query` is removed before checking. Rules:
  - `link_broken` when the target does not exist relative to the linking file;
  - `link_escapes_root` when it resolves outside the root.
  Heading anchors are not verified.
- R5 Findings are deterministic: the same tree gives byte-identical output.
- R6 Architecture test `tests/test_architecture.py`, enforced by the unit suite (and therefore by `check`):
  - every absolute import in `inonu_harness/` and `scripts/` resolves to the standard library (`sys.stdlib_module_names`) or `inonu_harness`;
  - no module other than `cli.py`, `__main__.py` and the runner `scripts/inonu.py` imports `inonu_harness.cli` or `inonu_harness.__main__`;
  - no module, in any subpackage, calls `__import__`, `importlib.import_module`, `exec` or `eval`;
  - the lint module imports nothing from `cli`.
  Its failure message states the offending file and what to change.
- R7 Tests cover:
  - each rule with a temp tree, including the line numbers;
  - fenced blocks and inline code skipped;
  - reference-style links and images;
  - fragment and query stripping;
  - scheme and absolute targets skipped;
  - root escape;
  - non-UTF-8 files;
  - invalid root and limits exit 2;
  - determinism;
  - no absolute path in the output;
  - the CLI exit codes;
  - this repository passes its own lint;
  - the architecture test fails when a third-party import or a `cli` import from a lower module is injected into a temp copy.
- R8 Docs: CHANGELOG 0.0.16, README, a short Portuguese paragraph in `docs/architecture.md` about the structural rules the test enforces, and a skill bullet. They state that the lint checks links and size only, not whether the documents are true or current. Version 0.0.16.

## Out of scope

A documentation-gardening agent, a quality-score document, anchor verification, absolute-local-path detection, nested instruction files, and any model call.
