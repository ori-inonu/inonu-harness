# v0.0.8 decisions and research frontier

## Destination and scope

Ship an optional local artifact audit so explicit SDD requirement/task/check links can be inspected deterministically. The current user Goal and prior implementation request authorize routine reversible implementation, fixtures and tests. This scope comes from the user, not a Jev receipt. The v0.6 document-only scope and unexecuted agent-study protocol remain historical; they do not block this separately specified feature or establish a completed study.

## Primary-source evidence, observed 2026-10-25

- [Spec Kit Agentic SDD](https://github.github.com/spec-kit/reference/agentic-sdd.html) describes read-only cross-artifact consistency analysis across specification, plan and tasks, including missing coverage. **Inonu inference:** explicit structured links allow a smaller deterministic structural check; semantic review remains necessary.
- [OpenSpec CLI reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md) and [troubleshooting](https://github.com/Fission-AI/OpenSpec/blob/main/docs/troubleshooting.md) describe structural validation and artifact dependencies. **Inonu inference:** expose machine-readable findings and a useful exit status for a local explicit audit.
- [Superpowers verification-before-completion](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md) requires checking actual verification output before completion claims. **Inonu inference:** preserve evidence identity and document that a declared pass/hash alone cannot authenticate execution.
- [v0.6 research](../v0.0.6/research.md) contains pinned README/license snapshots, overlap and candidate validation designs for six projects. No code, prompts or skills are copied or installed by v0.8.

Fresh public GitHub REST `stargazers_count` observations: [Spec Kit](https://api.github.com/repos/github/spec-kit) 142,844; [Superpowers](https://api.github.com/repos/obra/superpowers) 304,984; [OpenSpec](https://api.github.com/repos/Fission-AI/OpenSpec) 72,952; [BMAD](https://api.github.com/repos/bmad-code-org/BMAD-METHOD) 54,539; [OpenHands](https://api.github.com/repos/OpenHands/OpenHands) 91,817; [Cline](https://api.github.com/repos/cline/cline) 70,833. This is a dated sample of attention, not an exhaustive ranking, usage count, quality comparison or adoption recommendation. License claims remain attached to the pinned files in v0.6; metadata classifiers alone are insufficient.

## Confirmed local decisions

- D01: implement the explicit local audit rather than keep this capability in test-only proposals or prioritize further CodeGraph package probing. Jev `inonu-v08-artifact-gate-20261025`, hash `81265423e4def5b93f1c95466e16dae0fb2a9fa25195a1afa1414a9fd5abe893`, recommended `structured_gate`: 9 calls, 0 failures, 10,291 input tokens. The coordinator adopts it within user scope.
- D02: use explicit v1 typed records and SHA-256-bound evidence. Jev `inonu-v08-audit-contract-20261025`, hash `53b03d1c796aca803d5497c5717b3bad296e06ea9cca55e580cef1b9e34ef0b5`, recommended `sha256_manifest`: 9 calls, 0 failures, 12,780 input tokens. An initial free plan was refused because scalar facts exceeded the local 300-character limit; splitting sanitized facts repaired validation before the successful matching plan/run.
- D02 fixes the public seams, strict manifest/report schema, 1 MiB manifest and 8 MiB evidence caps, safe relative paths, failure rules and five-case validation defined in [spec.md](spec.md). SHA-256 detects byte drift; it does not prove correctness or check execution.
- D03: deliver two vertical slices: library with behavioral tests/frozen corpus; then CLI with baseline integration tests/documentation. Independent standards and spec reviews precede a final milestone self-audit and deterministic convergence. The native graph keeps file ownership disjoint and serializes the two slices.
- D04 safety repair: T03 found a P2 in the resolve/stat-then-open sequence: a concurrent substitution could make the subsequent open follow an outside-root link or special file. The coordinator reproduced the trust-boundary gap by redirecting the selected open to a synthetic outside file; the old audit incorrectly passed. Jev `inonu-v08-opened-evidence-20261025`, hash `bf31001320cd6cf102acb5723ba23dbc88f8f773b76a2dd533a0056835281bda`, recommended `opened_handle` (9 calls, 0 failures, 10,247 input tokens). The coordinator selects same-handle validation/reading, descriptor-relative no-follow traversal on POSIX, and documented Win32 handle final-path/type checks on Windows through the standard library. This enforces R3 without a new dependency or a path-only fallback. Primary API references: [Python os](https://docs.python.org/3/library/os.html), [Windows final handle path](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew), [directory handles](https://learn.microsoft.com/en-us/windows/win32/fileio/obtaining-a-handle-to-a-directory), [file sharing](https://learn.microsoft.com/en-us/windows/desktop/FileIO/creating-and-opening-files). Repair tests and re-review are required before convergence.

## Open questions

- Whether this gate reduces missed requirements or rework in real agent tasks remains unmeasured.
- Semantic contradiction detection, automatic discovery, adaptive routing and portable live JEV transport remain future decisions.
- A future native integration must bind authentic verification receipts and preserve human authorization fences; this static audit does not create those privileges.
