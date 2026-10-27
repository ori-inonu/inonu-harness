# v0.0.19 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Motivation: the gap matrix in the v0.0.10 research listed redaction of secrets in packets as the caller's job. `decisions context` and `decisions packet` print free text that the owner hands to an agent.
- Scope: Jev returned `sem_consenso` ([decisions.md](decisions.md) D1). The most reversible option was adopted: an opt-in `--refuse-secret-patterns` flag. Refusing by default, warning only and redacting scored rail probabilities of 0.63, 0.62 and 0.80.
- A Haiku worker built the scanner, the flag, tests and docs (T01), with the instruction never to commit a credential-looking literal; an independent Haiku reviewer then tried to evade, leak through and slow it (T02). There were no P1 findings.
- Review findings and the coordinator's resolution:
  - P2, an identifier-shaped dict key was printed in a finding path even when it was part of the matched value, so the public `scan()` could disclose a 16-character piece of a credential. A key that shares eight or more consecutive characters with the matched text is now shown as `*`.
  - P3, a credential-named key with a bare value (for example a `password` field) was not detected. A string under a key is now also checked as `key: value`.
  - P3, with the flag, an unknown token-shaped `--ids` value was echoed by the existing "decision not found" error. The ids are now scanned before the lookup.
  - P3, the docs claimed "bounded quantifiers" where the patterns use open-ended minimum counts, and omitted that a credential split across fields is printed. Both corrected.
  - P3, test gaps (AWS boundaries, case, `rk_live_`, the 40- versus 41-character key limit, ordering, masked duplicates) and a one-megabyte test that would run for minutes instead of failing fast if the JWT token boundary were removed. Added; the time bound now runs six near-miss shapes in child processes with a hard limit.
  - P3, credential-looking sentinels in this project's own tests. The ones this work owns are now assembled from fragments, including a sample in `tests/test_jev.py`.
- A mutation check broke the scanner and its wiring in 10 ways in temporary copies; the suite failed each time. The scanner was also run over every tracked and untracked text file (171): the only remaining hits are three obvious placeholders (`PRIVATE_..._SECRET`) in `tests/fixtures/doctor/host_snapshot.json`, which pre-date this milestone.

## Verification

- `python -m unittest discover -s tests`: exit 0, 339 tests, 4 skipped (three POSIX-only, one file-symlink case that needs a privilege this host lacks).
- `python -m inonu_harness check`: exit 0. `python -m inonu_harness docs lint`: pass. `git diff --check`: exit 0.
- `bundle apply --host both` preview, then `--apply`: both skills updated.

## Limits

- The guard is opt-in and off by default; callers who attach output to an agent should pass it. It catches only eleven formats, not passwords in prose, custom tokens or most credential formats, and it can raise false positives. A match means the text needs review; no match does not prove it is free of secrets.
- A credential split across fields, list items or the task id and prompt is not joined, so each half is printed. Matched values are never printed, and nothing is redacted.
- Linear time is a property of the patterns on tested inputs, not a proof.

## Next

The commit and push (the owner's go-ahead is needed), then `python -m inonu_harness check --ref HEAD`. Candidate unblocked work: a revision-diff command for the Decision Graph; making the guard the default would be a separate decision.
