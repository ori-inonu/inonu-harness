# v0.0.7 checkpoint — 2026-10-25

## Status

The CodeGraph license provenance improvement is implemented, documented, independently reviewed, and verified. The workflow completed T01–T06 on graph `doctor-codegraph-provenance-2026-10-25`, run `c3ab3704-784e-4b3b-8266-6ee9b246fff5` (reviewed hash `81fdb1ef2b862ed37b87d7e49835680138463eaef39f91efa1ff67450d139182`). No commit or push was made.

## Implementation

- The Environment Doctor reports the declared MIT license from the local npm manifest only when the installed CLI version, package name, package version, repository, license, and expected global executable location match.
- `npm root -g` is invoked without a shell, with a four-second wait and a 4 KiB stdout limit. The process is killed on overflow; incomplete, oversized, or inconsistent metadata stays `unknown`.
- The report schema remains v1 and omits local paths and raw package metadata. Standalone installations, forks, and unverified distributions remain unknown. The local CLI does not prove active MCP access.
- Documentation records the local provenance rule and its limits. No dependency or installation behavior was added.

## Verification and review

- Focused Doctor suite: `python -m unittest discover -s tests -p test_doctor.py -v` — **8/8 passed**.
- Full suite: `python -m unittest discover -s tests -v` — **59/59 passed**.
- `git diff --check` — **passed**.
- Real `python -m inonu_harness doctor` execution returned exit code 0, schema v1, and CodeGraph license `MIT` from `local_package_manifest`; the filtered report check found no personal path.
- The independent standards review initially found a P2: unbounded `npm root -g` stdout. The implementation now caps the read and kills on overflow; the regression test verifies `kill()` for 4 KiB + 1 byte. Follow-up review confirmed it resolved and found no remaining actionable standards or security issues.
- Independent specification review and follow-up found no remaining findings.

## Files in this increment

- `inonu_harness/doctor.py`
- `tests/test_doctor.py`
- `docs/integrations.md` (CodeGraph provenance subsection)
- `docs/specs/milestones/v0.0.7/decisions.md`
- `docs/specs/milestones/v0.0.7/plan.md`
- `docs/specs/milestones/v0.0.7/spec.md`
- `docs/specs/milestones/v0.0.7/tasks.md`
- `docs/specs/milestones/v0.0.7/checkpoint.md`

Existing unrelated worktree edits in `docs/sdd-workflow.md` and `docs/specs/milestones/v0.0.6/` were preserved.

## Residual limits and follow-up

- The over-limit test uses a fake process; it verifies the kill call but does not exercise real child-process termination on every supported operating system.
- The probe intentionally recognizes only the verified npm global layout. Other package managers or layouts remain unknown until separately verified.
- A useful follow-up is a small OS matrix check of the real npm layout and timeout/overflow termination, without changing the conservative unknown fallback.
