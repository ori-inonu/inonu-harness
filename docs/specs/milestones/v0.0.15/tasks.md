# v0.0.15 tasks

| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 Manifests, skill, agent, tests | none | new `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, `skills/inonu-harness/SKILL.md`, `agents/inonu-worker.md`, `inonu_harness/host_profiles.py`, `inonu_harness/__init__.py`, `pyproject.toml`, new `tests/test_plugin.py`, affected existing tests | A1: R1–R6 hold; A2: the existing installer and bundle behavior is unchanged except the placeholder rewrite. |
| T02 Docs | none | new `docs/plugin.md`, `README.md`, `CHANGELOG.md` | A3: R7 accurate, unverified points and non-claims stated. |
| T03 Independent review | T01, T02 | read-only | A4: a reviewer that did not implement checks the documented rules, the installer rewrite and the omitted components. |
| T04 Convergence | T03 | `checkpoint.md` (coordinator) | A5: full suite and `check` exit 0; every P1/P2 resolved. |
