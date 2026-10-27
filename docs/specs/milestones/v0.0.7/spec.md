# v0.0.7 — CodeGraph package provenance in Environment Doctor

## Problem

The Environment Doctor reports CodeGraph's installed license as unknown even when its local CLI and package metadata identify the installed distribution. This loses useful provenance while the same report already preserves an upstream license separately.

## Outcome

Report a local CodeGraph license only when the global npm package can be tied to the executable found on `PATH` and its metadata agrees with the observed CLI version and official package identity. Keep the current unknown result whenever any link in that chain cannot be checked.

## Confirmed facts

- On 2026-10-25, the host reported CodeGraph CLI version `3.0.1`.
- `npm root -g` located the package metadata for `@lzehrung/codegraph`; the declared version was `3.0.1`, license `MIT`, and repository `https://github.com/lzehrung/codegraph`.
- The executable's containing global npm bin directory matched the directory inferred from that global package root.
- The report currently uses schema version 1 and exposes only allowlisted fields.

These facts describe this host only. The [official CodeGraph installation guide](https://github.com/lzehrung/codegraph/blob/main/docs/installation.md) supports npm and standalone installation paths; the latter is outside this check.

## Requirements

- **R1 — Provenance:** recognize only the exact `@lzehrung/codegraph` package, its safe version matching `codegraph --version`, the declared MIT license, the official HTTPS repository, and the matching npm global executable directory.
- **R2 — Bounded read-only probe:** use `npm root -g` without a shell, with a short timeout; read only the package manifest under that root and enforce a small size limit.
- **R3 — Conservative fallback:** missing npm, timeout, malformed or ambiguous JSON, unsupported global layout, path mismatch, version mismatch, or metadata mismatch leaves the installed license `unknown`.
- **R4 — Privacy:** package roots, executable paths, manifest contents, stderr, and exception text never appear in the report.
- **R5 — Compatibility:** retain report schema version 1, existing integration keys, and the static intent manifest. MCP availability remains unknown unless independently observed by an official host interface.
- **R6 — Evidence:** tests cover a matching package and representative mismatches/unavailability through the Environment Doctor seams; documentation states the source and limits.

## Test seam

Use `LocalProbe.snapshot()` with a temporary npm package root and mocked process/PATH boundaries to verify discovery. Pass that snapshot through `collect_environment()` to verify the sanitized public report. This catches both false attribution and path leakage; it does not verify MCP reachability or standalone installers.

## Out of scope

Scanning standalone installers or forks, installing or updating tools, changing MCP configuration, determining active-session access, changing the report schema, or editing the integration intent manifest.
