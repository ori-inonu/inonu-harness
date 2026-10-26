# v0.9.0 checkpoint — 2026-10-26

Status: public source preparation is release-ready for coordinator delivery. T05 convergence covers A7 and A8. This checkpoint does not complete the broader release objective.

## Preparation graph

- Native graph: `inonu-v09-host-release-20261026`
- Graph hash: `e98998c6fa85874379da2361c27d7dad9243eee0fbfe695e2557e47416f89c38`
- Run: `ef13f13a-9dc3-4896-9a19-2f5ab5bddc68`
- T03 standards review and T04 spec review completed with no findings. The reviewed source includes the coordinator's minor alignment fixes for package version `0.9.0` and portable test expectations.

## Public preparation changes

The reviewed public scope covers `README.md`, `CHANGELOG.md`, `docs/hosts.md`, the architecture, benchmark, integrations and SDD workflow documentation, milestone records for v0.6.0 through v0.9.0, the `inonu_harness` package, scripts, the native source skill, tests, `pyproject.toml`, `.gitattributes` and the synthetic SDD audit fixtures. This task changed only this checkpoint.

## A7 — verification evidence

- Focused host-profile suite: `python -m unittest discover -s tests -p test_host_profiles.py -v` — exit 0; 9 tests passed.
- Full suite: `python -m unittest discover -s tests -v` — exit 0; 99 tests considered, 96 passed and 3 POSIX-only regressions skipped on this Windows host.
- Runner version: `python scripts/inonu.py --version` — exit 0; `inonu-harness 0.9.0`.
- Installer preview: ran `scripts/configure_hosts.py --home <isolated temporary directory>` without `--apply` — exit 0; JSON reported preview for Codex and Claude at version 0.9.0, and the temporary home remained empty.
- Native skill validation: the source frontmatter contains exactly the supported `name` and `description` plain-scalar fields; both relative documentation pointers resolve inside the repository. The focused tests also verify native frontmatter/workflow expectations, generated ownership metadata and SHA-256, shell quoting, and resolved documentation URIs.
- `git diff --check` — exit 0 with no diagnostics. The untracked checkpoint was also checked for a final newline and trailing whitespace.
- The optional `quick_validate.py` could not complete because its PyYAML import fails in the existing Python environments. No dependency was installed; the source's restricted frontmatter subset and pointers were checked directly with the standard library.

## A8 — review disposition and delivery boundary

No unresolved P1/P2 findings remain from T03 or T04. The public source preparation meets the v0.9.0 release-readiness criteria. Host application and actual host-registration verification under R7 remain coordinator work; the Inonu profiles are not claimed as applied or loaded in a host session. R8 commit, push and remote-revision verification also remain pending. Preserve existing complementary tools because replacement equivalence is not established, and keep private host configuration and reports outside the public source. Do not claim publication or completion of the broader release objective from this preparation checkpoint.

Next action: the coordinator completes R7 host application and records registration, handshake, tool-result and session-loaded evidence separately; then completes R8 publication and verifies the pushed revision.
