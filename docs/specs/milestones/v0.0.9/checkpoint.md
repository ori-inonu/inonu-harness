# v0.0.9 checkpoint — 2026-10-26

Status: public preparation converged, the coordinator published the implementation, and both local native profiles were applied and verified. Active host-session loading remains unverified. This milestone does not complete the broader Harness objective.

## Preparation graph

- Native graph: `inonu-v09-host-release-20261026`
- Graph hash: `e98998c6fa85874379da2361c27d7dad9243eee0fbfe695e2557e47416f89c38`
- Run: `ef13f13a-9dc3-4896-9a19-2f5ab5bddc68`
- T03 standards review and T04 spec review completed with no findings. The reviewed source includes the coordinator's minor alignment fixes for package version `0.0.9` and portable test expectations.

## Public preparation changes

The reviewed public scope covers `README.md`, `CHANGELOG.md`, `docs/hosts.md`, the architecture, benchmark, integrations and SDD workflow documentation, milestone records for v0.0.6 through v0.0.9, the `inonu_harness` package, scripts, the native source skill, tests, `pyproject.toml`, `.gitattributes` and the synthetic SDD audit fixtures. This task changed only this checkpoint.

## A7 — verification evidence

- Focused host-profile suite: `python -m unittest discover -s tests -p test_host_profiles.py -v` — exit 0; 9 tests passed.
- Full suite: `python -m unittest discover -s tests -v` — exit 0; 99 tests considered, 96 passed and 3 POSIX-only regressions skipped on this Windows host.
- Runner version: `python scripts/inonu.py --version` — exit 0; `inonu-harness 0.0.9`.
- Installer preview: ran `scripts/configure_hosts.py --home <isolated temporary directory>` without `--apply` — exit 0; JSON reported preview for Codex and Claude at version 0.0.9, and the temporary home remained empty.
- Native skill validation: the source frontmatter contains exactly the supported `name` and `description` plain-scalar fields; both relative documentation pointers resolve inside the repository. The focused tests also verify native frontmatter/workflow expectations, generated ownership metadata and SHA-256, shell quoting, and resolved documentation URIs.
- `git diff --check` — exit 0 with no diagnostics. The untracked checkpoint was also checked for a final newline and trailing whitespace.
- The optional `quick_validate.py` could not complete because its PyYAML import fails in the existing Python environments. No dependency was installed; the source's restricted frontmatter subset and pointers were checked directly with the standard library.

## A8 — review disposition and delivery boundary

No unresolved P1/P2 findings remain from T03 or T04. At the preparation boundary, R7 host application and R8 publication were still coordinator work. The engine subsequently reported `terminal: true` and `engineStatus: complete`, with no outstanding native tickets. The coordinator's later delivery evidence is recorded below; preparation alone did not establish it.

## Coordinator delivery and CI follow-up

- Published implementation commit `f16f360` to the existing `codex/m0-inonu-harness` branch and verified that the remote revision matched. No merge, force-push or default-branch change was performed.
- Created a separate desktop checkout with the same remote and upstream branch. Applied both Inonu 0.0.9 user profiles from that checkout; repeat apply returned `unchanged`. Both ownership hashes matched, and the installed PowerShell and Bash runner commands succeeded from unrelated working directories. A real doctor invocation returned schema v1 without a personal home path. Private host configuration and detailed tool observations remain outside Git.
- The first Linux CI run found two test-instrumentation failures: wrapping `os.open` removed its membership in `os.supports_dir_fd`, so the reader correctly returned before the simulated substitution. Follow-up commit `7ee66c8` preserves the wrapper's supported capability in the test context, keeps the safety assertions, and leaves production reader code unchanged. An independent read-only follow-up review found no issues.
- [CI run 40305606958](https://github.com/ori-inonu/inonu-harness/actions/runs/40305606958) passed on Ubuntu with Python 3.11 and 3.14 at `7ee66c87684ed130d46956573f2553615463d226`: each considered 99 tests, passed 94 and skipped 5 Win32-only tests. All three POSIX regressions executed and passed in both jobs. This adds native POSIX evidence to the Windows results above.
- Publication checks also normalized trailing blank lines in previously untracked milestone documents, refreshed the affected v0.8 manifest hashes, and reran its actual self-audit successfully. Staged whitespace validation passed.

Keep complementary tools because replacement equivalence is unproven. Installing profiles, checking MCP connections and exercising local commands do not prove that an existing model session loaded them. The Claude Desktop native UI automation channel was unavailable; activation in a local Code-tab session remains an explicit limit. The changed Codex MCP launcher likewise requires a fresh client session for client-level confirmation. Portable activation guidance is in [hosts.md](../../../hosts.md).
