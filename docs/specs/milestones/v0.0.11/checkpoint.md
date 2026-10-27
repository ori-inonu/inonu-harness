# v0.0.11 checkpoint — 2026-10-26

Status: converged locally; nothing is committed. A Haiku worker implemented T01 and an independent Haiku reviewer did T02. The coordinator resolved the findings.

## Review disposition

- P2 RecursionError on deeply nested JSON crashed `bundle status`. Fixed: the parsers catch `ValueError` and `RecursionError` and report `unknown`. A test uses a 100,000-deep `[` payload.
- P2 Home-path leak assertions missed the JSON-escaped and POSIX forms on Windows. Fixed with `assert_no_home`, which checks all three forms.
- P3 A mistyped `mcpServers`/`mcp_servers` or a non-object top level reported `absent`. It now reports `unknown`, with a test.
- P3 The `outdated` skill state and an unrelated Stop hook (`absent`) were untested. Tests were added.

## Verification

- `python -m unittest discover -s tests`: exit 0 (116 tests, 3 POSIX-only skipped).
- `python -m inonu_harness check`: exit 0, `passed: true`.
- `git diff --check`: exit 0.

## Next

The owner authorized host configuration writes on 2026-10-26 ([decisions.md](decisions.md) D2). v0.0.12 implements `bundle apply`/`remove` under that authorization.
