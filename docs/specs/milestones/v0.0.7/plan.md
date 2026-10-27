# v0.0.7 plan — CodeGraph package provenance

The local decision is deliberately narrow: check the installed global npm package only when its package metadata, CLI version, and executable directory all agree. Unsupported or incomplete layouts remain unknown. No runtime dependency or installer is added.

1. Add red standard-library tests using a temporary global npm package and mocked subprocess/PATH boundaries.
2. Extend the local doctor probe and license normalization with a bounded, exact package identity check. Keep all raw paths and package data inside the probe snapshot.
3. Update the integration inventory to explain the local metadata source and its limits.
4. Run independent standards and specification reviews, resolve findings, then run the focused doctor tests, full unit suite, and `git diff --check`.

The existing user and project changes in the worktree are preserved. No commit or push is in scope.
