# v0.0.26 checkpoint — 2026-10-26

Status: implemented, reviewed, fixed and verified locally. Nothing from this milestone is committed or released. The installed skill profiles for Claude and Codex were refreshed with `bundle apply` under the existing authorization, so `milestone close` reaches every project that loads them.

## Flow

- Scope: chosen by the Jev judge from [brief.md](brief.md) ([decisions.md](decisions.md) D1): consensus, leader "close gate and index", mean 0.74, rail probability 0.10. It is the third consensus in a row with a written brief.
- Build: a Haiku worker wrote `milestone close`, the index reader, linter and atomic writer, the checkpoint rules and the new check rules, with 41 tests (T01); a second wrote the docs, the skill bullet and the version bump (T02).
- Review (T03, independent) found no P1, 13 P2 and 9 P3 items. The coordinator fixed them:
  - the identity of a checkpoint was read from the raw first line, so a version named only inside an HTML comment passed; it is now read from the first visible line;
  - an HTML comment is now handled as CommonMark does, in one linear pass: a line that starts with a comment is an HTML block and nothing on it is Markdown. The old per-line scan was quadratic, and one line of 200,000 `<!--` could hang `close` and `check`;
  - deferred items were missed when the heading was written in another case, with closing `#` marks, or when the item was indented by one to three spaces, so the entry could record `- Deferred: 0` for items without a reason. Headings are now matched in any case and indented items count;
  - `close` accepted a date later than today, which would have refused every later close; it is now invalid input;
  - a spec title with a control character is left out of the entry, as `milestone new --title` would refuse it;
  - the spec's R11 could not run as written, because `close` needs the manifests to state the version; the spec now says the manifests are set back for that one command and restored;
  - the docs said the JSON em dash is literal (it is ASCII-escaped), listed the refusal reasons in an order the code does not print, omitted the first-line rule from the Portuguese paragraph and used example dates in the future. Fixed.
  - closing v0.0.26 with its own command failed at first: its checkpoint quotes the marker `<!--` inside a code span, and the reader took it for the start of a comment, hid the headings after it and refused. Inline code spans are now blanked out before comments are looked for, in one linear pass (a run of backticks closes at the next run of the same length, as in CommonMark), with tests for the span, the CommonMark cases and a line of 400,000 backticks;
  - nine test gaps are closed: warnings do not refuse a close, a close on the same day, an indented `Status:`, headings inside a fence or a comment, the longer-version boundary, three or more entries, a hyphen as a reason separator, a future date and a long run of comment openers.
- A mutation check broke the fixes in 14 ways; 13 were caught at once (the code-span fix came after it and has its own tests). The survivor (an HTML block that starts a line) was not told apart from an inline comment by the test; the test now puts the heading right after the comment without a space, and the mutant is caught.
- The repository closed v0.0.25 with the command (R11): the three manifests were set to 0.0.25 for that command and restored to 0.0.26, and `docs/specs/milestones/MILESTONES.md` was created by it. v0.0.26 was then closed the same way, once the manifests stated 0.0.26.

## Verification

- `python -m unittest discover -s tests`: exit 0, 691 tests, 8 skipped (symbolic-link, FIFO and POSIX-only cases that this host cannot run).
- `python -m inonu_harness check`: exit 0, steps `compile`, `versions`, `milestones`, `tests`. `docs lint`: pass. `version --scheme`: exit 0. `milestone check --from 0.0.9`: pass.
- `bundle apply --host both --apply`: both skills updated.

## Limits

- The close writes the index and nothing else. It does not run the verification commands, read `## Flow` or `## Next`, tag, move or delete anything, or prove that the work passed.
- A colon inside a URL counts as a reason separator, and a first line that says a checkpoint was copied from another milestone passes for the milestone it names.
- The index is rewritten as a whole: line endings become LF, a byte order mark is dropped and, on POSIX, the file mode is 0600. Two closes of the same version at the same moment both succeed and the later write wins.
- Earlier milestones are not in the index and are not backfilled.
- Not verified here: POSIX behaviour of the new code (GitHub's Linux CI has not seen it yet), a real symbolic link on the index path, and two concurrent closes.

## Next

The commit, the pull request and the releases of v0.0.25 and v0.0.26 need the owner's go-ahead. The next candidates in the research are append-only gap tasks, a pause and resume file, and waves for parallel workers.
