# v0.0.6 workflow-tool research

- **Research date:** 2026-10-25 (UTC date)
- **Question:** Which practices described by six official AI workflow projects merit an offline, fixture-backed evaluation for Inonu while preserving its current SDD flow?
- **Boundary:** First-party GitHub repository material only: README and relevant project documentation, LICENSE files, and GitHub REST repository metadata. Repository content is pinned below to the `main` commit observed on the research date. Star counts are the `stargazers_count` values read from the linked GitHub API endpoints on that date.
**Stop condition:** Record sourced facts, separate Inonu inferences, and recommend a bounded evaluation design. This is not tool adoption, source reuse, implementation authorization, or evidence that any integration works.

## Source and attention snapshot

Stars are a **point-in-time attention signal only**. They do not establish quality, safety, maintenance, compatibility, license fitness, or suitability for Inonu. The API endpoint is live and may show a later count when opened; the count in this table is the value observed on 2026-10-25.

| Project | Official source snapshot | License file | Stars observed 2026-10-25 |
| --- | --- | --- | ---: |
| Spec Kit | [github/spec-kit README at `67e0f72`](https://github.com/github/spec-kit/blob/67e0f7294e6e728ab60bf7b4590deb470448bc2d/README.md) | [MIT LICENSE](https://github.com/github/spec-kit/blob/67e0f7294e6e728ab60bf7b4590deb470448bc2d/LICENSE) | 142,803 ([GitHub API](https://api.github.com/repos/github/spec-kit)) |
| Superpowers | [obra/superpowers README at `2ce8aa1`](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/README.md) | [MIT LICENSE](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/LICENSE) | 304,841 ([GitHub API](https://api.github.com/repos/obra/superpowers)) |
| OpenSpec | [Fission-AI/OpenSpec README at `6d04a1b`](https://github.com/Fission-AI/OpenSpec/blob/6d04a1b58dedc95729d34e4f223d9d483aae210a/README.md) | [MIT LICENSE](https://github.com/Fission-AI/OpenSpec/blob/6d04a1b58dedc95729d34e4f223d9d483aae210a/LICENSE) | 72,939 ([GitHub API](https://api.github.com/repos/Fission-AI/OpenSpec)) |
| BMAD-METHOD | [bmad-code-org/BMAD-METHOD README at `61e01f8`](https://github.com/bmad-code-org/BMAD-METHOD/blob/61e01f82644c4bb533750cfa0d6d61ab61d2cc9b/README.md) | [MIT LICENSE](https://github.com/bmad-code-org/BMAD-METHOD/blob/61e01f82644c4bb533750cfa0d6d61ab61d2cc9b/LICENSE) | 54,530 ([GitHub API](https://api.github.com/repos/bmad-code-org/BMAD-METHOD)) |
| OpenHands | [OpenHands/OpenHands README at `b7fdc6c`](https://github.com/OpenHands/OpenHands/blob/b7fdc6c312039a0b840fdcd34a5c23ca7e65c218/README.md) | [MIT LICENSE](https://github.com/OpenHands/OpenHands/blob/b7fdc6c312039a0b840fdcd34a5c23ca7e65c218/LICENSE) | 91,790 ([GitHub API](https://api.github.com/repos/OpenHands/OpenHands)) |
| Cline | [cline/cline README at `40c5d99`](https://github.com/cline/cline/blob/40c5d99031fe1128189c5b52e40638d2b7787754/README.md) | [Apache-2.0 LICENSE](https://github.com/cline/cline/blob/40c5d99031fe1128189c5b52e40638d2b7787754/LICENSE) | 70,846 ([GitHub API](https://api.github.com/repos/cline/cline)) |

## Comparisons

Each candidate has the same seven fields. Statements marked **Source fact** describe the linked project material; statements marked **Inonu inference/proposal** are evaluation ideas, not claims about project behavior or adoption.

### Spec Kit

Sources: [official README](https://github.com/github/spec-kit/blob/67e0f7294e6e728ab60bf7b4590deb470448bc2d/README.md), [workflow reference](https://github.com/github/spec-kit/blob/67e0f7294e6e728ab60bf7b4590deb470448bc2d/docs/reference/workflows.md), [LICENSE](https://github.com/github/spec-kit/blob/67e0f7294e6e728ab60bf7b4590deb470448bc2d/LICENSE).

| Field | Evidence or proposal |
| --- | --- |
| Problem | **Source fact:** offers structured processes and reusable templates for taking an agent-assisted change from a specification through planning, tasks, implementation, and convergence. |
| Input/output contract | **Source fact:** setup takes a project and agent integration; its SDD commands take project principles, a change description, and plan constraints, then produce specification, plan, task, implementation, and convergence artifacts. Commands are invoked in the agent chat, one at a time, with result review. |
| Candidate practice for Inonu | **Inonu inference/proposal:** test explicit artifact handoffs and a recorded convergence result, while leaving Inonu's stage names and ownership intact. |
| Dependencies/overlap | **Source fact:** the README lists Python 3.11+, `uv`, and a supported coding agent. **Inonu inference:** artifacts overlap directly with the current SDD stages and could duplicate the existing milestone documents if installed wholesale. |
| License | **Source fact:** MIT, as stated by the linked LICENSE. |
| Validation test | **Proposed, not run:** give a fixture a requirement, one explicit constraint, and one missing decision; check that the expected requirement links to plan and task records and that convergence cites a deterministic check without silently resolving the missing decision. |
| Condition for an in-house implementation | **Inonu inference/proposal:** only consider a small artifact-linkage improvement if repeated fixtures show the current documents cannot preserve requirement-to-task-to-verification traceability. |

### Superpowers

Sources: [official README](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/README.md), [LICENSE](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/LICENSE).

| Field | Evidence or proposal |
| --- | --- |
| Problem | **Source fact:** provides coding-agent methodology through composable skills and instructions, including brainstorming, test-driven development, systematic debugging, verification, planning, and review. |
| Input/output contract | **Source fact:** the README describes a workflow-level interface rather than one machine-readable artifact schema: an agent task and repository context activate composable skills, whose documented outputs include plans, code changes, and verification results. Installation is described separately for each supported agent harness. |
| Candidate practice for Inonu | **Inonu inference/proposal:** evaluate one narrow behavior contract at a time (for example, a bug fix must show a failing check before its fix and a passing check after), rather than importing a whole skills catalog. |
| Dependencies/overlap | **Source fact:** installation is harness-specific and the project describes skills/tests for behavior and plugin infrastructure. **Inonu inference:** test-first work and verification overlap the existing implementation and review stages; Superpowers' overall methodology is broader than a new Inonu service. |
| License | **Source fact:** MIT, as stated by the linked LICENSE. |
| Validation test | **Proposed, not run:** use a fixed bug-report fixture with an expected failing-test → root-cause → fix → passing-verification trace; reject an answer that skips the initial failure or claims success without evidence. |
| Condition for an in-house implementation | **Inonu inference/proposal:** consider only a small, local behavior check if repeated fixtures reveal a gap in current stage instructions after the existing skills and repository rules are applied. |

### OpenSpec

Sources: [official README](https://github.com/Fission-AI/OpenSpec/blob/6d04a1b58dedc95729d34e4f223d9d483aae210a/README.md), [CLI reference](https://github.com/Fission-AI/OpenSpec/blob/6d04a1b58dedc95729d34e4f223d9d483aae210a/docs/cli.md), [LICENSE](https://github.com/Fission-AI/OpenSpec/blob/6d04a1b58dedc95729d34e4f223d9d483aae210a/LICENSE).

| Field | Evidence or proposal |
| --- | --- |
| Problem | **Source fact:** helps an agent and developer agree on a change before code, using a proposal, task list, implementation, and archive lifecycle. |
| Input/output contract | **Source fact:** accepts a project initialized with OpenSpec and a named change; chat commands propose and apply the change, while archive merges its delta specifications into the main specifications and moves the completed change into the archive. The CLI reference also exposes JSON instructions for agent workflows. |
| Candidate practice for Inonu | **Inonu inference/proposal:** evaluate change-scoped delta requirements and a final archive/checkpoint that preserves the original evidence trail. |
| Dependencies/overlap | **Source fact:** the quick start installs the npm package and initializes a project; proposal/apply/archive actions occur in an AI assistant. **Inonu inference:** proposal and tasks overlap specification/planning/task records; archived deltas may overlap milestone decisions and checkpoints. |
| License | **Source fact:** MIT, as stated by the linked LICENSE. |
| Validation test | **Proposed, not run:** start from a fixture baseline specification, add one delta requirement, mark tasks complete, and check that the archived result updates the baseline once while retaining the change record and refusing incomplete tasks. |
| Condition for an in-house implementation | **Inonu inference/proposal:** consider a small delta/archival helper only if fixtures repeatedly show that the current milestone documents cannot preserve change-specific requirements and their final disposition. |

### BMAD-METHOD

Sources: [official README](https://github.com/bmad-code-org/BMAD-METHOD/blob/61e01f82644c4bb533750cfa0d6d61ab61d2cc9b/README.md), [LICENSE](https://github.com/bmad-code-org/BMAD-METHOD/blob/61e01f82644c4bb533750cfa0d6d61ab61d2cc9b/LICENSE), [trademark notice](https://github.com/bmad-code-org/BMAD-METHOD/blob/61e01f82644c4bb533750cfa0d6d61ab61d2cc9b/TRADEMARK.md).

| Field | Evidence or proposal |
| --- | --- |
| Problem | **Source fact:** supplies an AI-driven development method with named skills, specialist perspectives, and workflows intended to carry product and technical context into delivery. |
| Input/output contract | **Source fact:** setup installs selected skills/modules for a coding tool; a user invokes named workflows with a project or change context. The README describes outputs including briefs, specifications, architecture, and implementation/review artifacts, and says small changes can use less planning. |
| Candidate practice for Inonu | **Inonu inference/proposal:** compare the amount of planning on one clear small-change fixture and one ambiguous multi-step fixture; keep the required eight Inonu stages present in both traces. |
| Dependencies/overlap | **Source fact:** the README lists a skills-capable coding tool, Node.js/npm/Git for the Skills CLI install route, and `uv` for setup/Python scripts. **Inonu inference:** specialist prompts and planning workflows overlap research, specification, planning, implementation, and review; installing a module is not evidence that it fits Inonu. |
| License | **Source fact:** the repository LICENSE says MIT; its README also identifies BMad and BMAD-METHOD as trademarks and links a notice. GitHub API metadata reported `NOASSERTION` for the license field on the snapshot date, so any later source/package use needs a fresh license review. |
| Validation test | **Proposed, not run:** run two frozen task-description fixtures through a rubric: the clear task should not acquire unneeded artifacts, and the ambiguous task should retain its unresolved decision; both must keep the eight-stage sequence and explicit verification. |
| Condition for an in-house implementation | **Inonu inference/proposal:** consider a small planning-depth rubric only if repeated offline cases expose an actual planning-fit gap; do not recreate the agent catalog or workflows. |

### OpenHands

Sources: [official OpenHands README](https://github.com/OpenHands/OpenHands/blob/b7fdc6c312039a0b840fdcd34a5c23ca7e65c218/README.md), [Software Agent SDK repository](https://github.com/OpenHands/software-agent-sdk), [SDK README](https://github.com/OpenHands/software-agent-sdk/blob/d2ee0cdea60825608c2f8906eb54e1d4d264fb42/README.md), [OpenHands LICENSE](https://github.com/OpenHands/OpenHands/blob/b7fdc6c312039a0b840fdcd34a5c23ca7e65c218/LICENSE), [SDK LICENSE](https://github.com/OpenHands/software-agent-sdk/blob/d2ee0cdea60825608c2f8906eb54e1d4d264fb42/LICENSE).

| Field | Evidence or proposal |
| --- | --- |
| Problem | **Source fact:** provides an AI software development agent platform. The top-level repository describes Agent Canvas and local-stack orchestration; the separate Software Agent SDK owns agents, tools, conversations, workspaces, events, and the Agent Server API. |
| Input/output contract | **Source fact:** the SDK provides Python, TypeScript, and REST interfaces for coding agents; a task is run against a local or ephemeral workspace and yields an agent conversation with tool/activity events and workspace effects. The API/runtime is in the SDK repository, not the Canvas repository. |
| Candidate practice for Inonu | **Inonu inference/proposal:** evaluate a portable execution/evidence boundary: record which fixture workspace was used, what deterministic commands ran, and what outputs support the result. This does not imply an OpenHands integration. |
| Dependencies/overlap | **Source fact:** the described platform is multi-repository; SDK/Agent Server, TypeScript client, Canvas, and automation have distinct responsibilities, and Agent Server can run locally or in an ephemeral workspace. **Inonu inference:** it overlaps runtime execution and event capture more than the eight-stage planning flow and has a larger operational surface than an offline evaluation needs. |
| License | **Source fact:** both the OpenHands/OpenHands and Software Agent SDK LICENSE files say MIT. The SDK is a separate repository, so any specific package dependency still needs its own review before evaluation. |
| Validation test | **Proposed, not run:** replay a synthetic agent-event fixture against an empty temporary repository; verify that the recorded workspace identity and command results are reproducible and that an event outside the declared workspace is rejected. No model or SDK call is needed for this boundary test. |
| Condition for an in-house implementation | **Inonu inference/proposal:** consider only a minimal event/provenance record if fixtures show that current baseline and decision records cannot identify which workspace and verification output support an execution claim. |

### Cline

Sources: [official README](https://github.com/cline/cline/blob/40c5d99031fe1128189c5b52e40638d2b7787754/README.md), [tools reference](https://github.com/cline/cline/blob/40c5d99031fe1128189c5b52e40638d2b7787754/docs/tools-reference/all-cline-tools.mdx), [LICENSE](https://github.com/cline/cline/blob/40c5d99031fe1128189c5b52e40638d2b7787754/LICENSE).

| Field | Evidence or proposal |
| --- | --- |
| Problem | **Source fact:** offers an agent across IDE, terminal, desktop, and SDK surfaces; the README describes code exploration, editing, command execution, and human review of changes. |
| Input/output contract | **Source fact:** takes a user task, workspace, and configured agent/model environment; Plan mode is for exploration and a strategy, while Act mode performs tool-backed work. The CLI can emit NDJSON; the tools reference lists file reading, code search, commands, patches/editor, skills, questions, and completion. |
| Candidate practice for Inonu | **Inonu inference/proposal:** test a clear plan/execute boundary with recorded tool permission/approval outcomes, without changing the current runtime or adding Cline as a dependency. |
| Dependencies/overlap | **Source fact:** Cline spans CLI, IDE extensions, desktop, and SDK; its docs describe native MCP and tool approval/policy controls. **Inonu inference:** this overlaps runtime/tool permission and execution evidence, not milestone-level SDD stages; the CLI can execute arbitrary commands, which is outside an offline contract test. |
| License | **Source fact:** Apache-2.0, as stated in the repository LICENSE. |
| Validation test | **Proposed, not run:** replay a synthetic Plan/Act event fixture; assert that Plan contains no write/command event and that an Act edit appears only after its expected approval event. |
| Condition for an in-house implementation | **Inonu inference/proposal:** consider a small deterministic permission/event validator only if current runtime evidence cannot prove the expected approval boundary on repeated fixtures. |

## Offline evaluation recommendation

Before any adaptive router or tool adoption, evaluate only the **candidate practices** above with a frozen, no-paid-call fixture set. Keep the baseline as the eight stages documented in [the current SDD guide](../../../sdd-workflow.md): Constitution, Research, Specification, Planning, Tasks, Implementation, Review, and Convergence.

1. Freeze a small set of sanitized task fixtures covering a clear change, an ambiguous change, a bug with a reproducible failure, a change with a specification delta, and an attempted action that should remain blocked. Store expected observations as fixture data; use no live model, paid API, external service, or newly installed tool.
2. For each candidate practice, specify one expected trace and one local validation rule. In the first pass, replay fixed, sanitized traces through local deterministic checks against the unchanged baseline; do not invoke an agent, install a vendor tool, or call an external service. Do not compare stars, project popularity, or self-reported marketing claims as quality measures.
3. Score deterministic properties first: all eight stages remain represented and ordered; each requirement maps to a task and verification; source facts remain distinguishable from inference; blocked actions stay blocked; fixture outputs are reproducible. Keep any qualitative rubric separate and label it as reviewer judgment.
4. Report per-fixture pass/fail, failures, and evidence references. Do not aggregate into an unsupported productivity, quality, token, or cost claim. A passing fixture establishes only that the proposed contract behaves on those cases.

This is a test-design recommendation, not an approved evaluation run, implementation, integration, router, or tool selection. The first useful result should be a reviewable fixture-and-rubric proposal; any later implementation or live evaluation needs its own authorization and decision record.
