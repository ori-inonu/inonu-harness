# v0.0.14 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Runner and tests | none | new `inonu_harness/loop.py`, `inonu_harness/cli.py`, `inonu_harness/__init__.py`, `pyproject.toml`, new `tests/test_loop.py`, version strings in `tests/` | A1: R1–R8 at the CLI seam; A2: R9 tests pass on Windows and POSIX semantics (process-tree kill). |
| T02 Docs | none | `CHANGELOG.md`, `README.md`, new `docs/loop.md`, `skills/inonu-harness/SKILL.md` | A3: R10 accurate, limits and non-claims stated. |
| T03 Independent review | T01, T02 | read-only | A4: a reviewer that did not implement tries to break the runner (hangs, leaked processes, limit bypass, log leaks). |
| T04 Convergence | T03 | `checkpoint.md` (coordinator) | A5: full suite and `check` exit 0; every P1/P2 resolved. |
