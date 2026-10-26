# v0.23.0 checkpoint — 2026-10-26

Status: implemented, independently reviewed, fixed and verified locally. Nothing is committed or pushed. The installed skill profile was refreshed with `bundle apply` under the existing authorization. This milestone does not complete the broader single-install objective.

## Flow

- Scope: set by the owner, who said the Jev judge must decide from the project's context and needs a specification document ([decisions.md](decisions.md) D1). The prototype that built the facts for the second v0.22.0 Jev run became the command `jev spec`.
- A Haiku worker built the command, tests and docs (T01); an independent Haiku reviewer then attacked it (T02) and found 1 P1, 11 P2 and 3 P3 items.
- Review findings and the coordinator's resolution:
  - P1, the secret scan ran on each fact, so a key word and its value that a fact boundary split were both accepted. Fixed: the whole collapsed text of each document is scanned before it is chunked.
  - P2, the scan covered only key=value words, `0x` addresses, base58 runs, `TYPESAFE=` and `sk-` tokens. Added a short list of common formats (GitHub, AWS, Slack and Google keys, bearer tokens, JWTs, PEM private-key headers). The docs now say the scan cannot recognize every secret.
  - P2, a misspelled optional key such as `forbiden` was dropped without an error. Fixed: any top-level key outside the seven allowed ones is refused.
  - P2, an NTFS alternate data stream passed the regular-file check, and a hard link passed the duplicate check. Fixed: a colon in the last path component is refused, and duplicates are found with `os.path.samefile`.
  - P2, length was counted in code points while the judge's server uses a JavaScript string length, so UTF-16 units. The reviewer could not confirm this; the judge's source (`consensus/spec.ts`, `v.length`) does. Fixed in the chunker and in `_validate_spec`, so an emoji counts 2.
  - P2, the rule "joining the chunks gives back the text" was false for a split line. The spec now states the invariant that holds and is tested: removing all whitespace from the facts and joining them gives the document's characters without whitespace. A generated-text test checks it with 60 random texts.
  - P2, test gaps: the decision-file size check, duplicate keys in a complete decision, six limits (id, option id, rail length, unknown ask, option count, NaN), the packing boundary, the default budget of 80 and the sentence-cut threshold. All covered now.
  - P2, the docs said refusals name the field; they name the kind of field. Reworded.
  - P3, a byte order mark, a lone carriage return and a combining mark at a cut. Fixed: a BOM is dropped, `splitlines` ends lines, and a hard cut never separates a letter from its mark. A false positive of the inherited base58 pattern on a 40-character hex id with no zero is documented.
- A mutation check broke the implementation in 23 ways; all 23 were caught.
- On the real v0.22.0 documents the command's output is identical to the prototype's: 20 of 20 facts, the same remaining fields, longest fact 286 characters.

## Verification

- `python -m unittest discover -s tests`: exit 0, 493 tests, 5 skipped (three POSIX-only cases and two symbolic-link cases, one in the bundle tests and one in `tests/test_jev_context.py`, that need a privilege this host lacks).
- `python -m inonu_harness check`: exit 0. `python -m inonu_harness docs lint`: pass, 124 files. `git diff --check`: exit 0.
- `bundle apply --host both --apply`: both skills updated to this version; `bundle status` reads them as `ours`.

## Limits

- The command does not check that a brief leaves out the answer, or that a document is true or current. Those checks stay human.
- The secret scan is short on purpose. It cannot recognize every secret, so credentials do not belong in documents.
- Nothing in the facts marks where a long line was split.
- The 64 KiB document cap and the budget of 80 facts are local limits. The judge itself does not limit the number of facts in practice (30 were accepted in a free `consensus_plan`), but each fact adds input tokens to every call.
- Not verified: a real symbolic link (the host cannot create one; the test patches `Path.is_symlink`), POSIX behaviour, and a Jev run on a spec that the command built (the earlier `consensus_plan` accepted its prototype's output).
- Scopes decided in 0.10.0 to 0.21.0 were not re-run with documents.

## Next

The commit and push of the v0.10.0 to v0.23.0 work and `CLAUDE.md` need the owner's go-ahead. Open research gaps: G5 (a bounded context renderer, which `jev spec` partly covers for documents), G6 (the worker agent `tools` allowlist, fenced) and G7 (check steps).
