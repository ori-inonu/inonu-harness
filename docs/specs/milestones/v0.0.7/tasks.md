# v0.0.7 tasks — CodeGraph package provenance

The milestone spec, plan, and decision record are prepared. The native workflow graph tracks implementation, review, and convergence.

## T01 — Test package provenance and report sanitization

**Blocked by:** none.
**Files:** `tests/test_doctor.py`.

- [ ] A temporary matching npm package, matching executable location, and matching CLI version produce the local `MIT` license with package-manifest provenance.
- [ ] Package identity/version/repository mismatch and unavailable npm metadata preserve the unknown license.
- [ ] The JSON report contains no temporary path or raw manifest data and keeps schema version 1 and existing integration keys.

## T02 — Probe and validate CodeGraph package metadata

**Blocked by:** T01.
**Files:** `inonu_harness/doctor.py`.

- [ ] The probe invokes `npm root -g` without a shell and with a bounded timeout, checks the matching global bin directory, and bounds the manifest read.
- [ ] Only exact package name, safe matching version, `MIT`, and official repository metadata are accepted.
- [ ] Every unsupported or invalid result remains unknown; no local path or package metadata is emitted.

## T03 — Document the observed license source

**Blocked by:** T02.
**Files:** `docs/integrations.md`.

- [ ] The doctor behavior, local provenance, and standalone/fork limitation are stated without changing the intent manifest or asserting MCP availability.

## T04 — Standards review

**Blocked by:** T03.
**Files:** read-only review of `inonu_harness/doctor.py`, `tests/test_doctor.py`, and the new documentation.

- [ ] Report any correctness, security, privacy, maintainability, or documented-standard findings with file and line evidence.

## T05 — Specification review

**Blocked by:** T03.
**Files:** read-only review against `spec.md`.

- [ ] Report missing/partial requirements, scope creep, and incorrect behavior with spec and code evidence.

## T06 — Deterministic convergence

**Blocked by:** T04 and T05.
**Files:** checkpoint evidence only.

- [ ] Focused doctor tests, the full unit suite, and `git diff --check` pass.
- [ ] The checkpoint records actual test results, review findings, preserved worktree state, and any residual limitation.
