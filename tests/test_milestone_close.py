import datetime
import json
import shutil
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from inonu_harness import milestones
from inonu_harness.cli import main as cli_main
from inonu_harness.milestones import MAX_BYTES, Refused, check_milestones, close_milestone, main
from inonu_harness.versions import INIT, PLUGIN, PYPROJECT


REPO_ROOT = Path(__file__).resolve().parents[1]
MILESTONES = "docs/specs/milestones"
INDEX = f"{MILESTONES}/MILESTONES.md"
DAY = "2026-01-15"
SPEC = "# v0.0.9 — Sample\n\n## Requirements\n\n- R1 First.\n- R2 Second.\n\n## Out of scope\n\nNothing.\n"
TASKS = "| Task | Depends on | Ownership | Acceptance |\n| --- | --- | --- | --- |\n| T01 one | none | x | A1: R1, R2 |\n"
DECISIONS = "## D1 — Scope\n\nText.\n"
ENTRY = "## v0.0.9 — Sample (Shipped: 2026-01-15)\n- Requirements: 2\n- Deferred: 0\n- Folder: [v0.0.9](v0.0.9/)"


def write(root, rel, content):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))


def checkpoint(version, extra=""):
    """A checkpoint with the sections that close requires, named for version; extra goes after them."""
    return f"# v{version} — checkpoint\n\nStatus: shipped.\n\n## Verification\n\nThe commands exit 0.\n\n## Limits\n\nNone known.\n{extra}"


def index_entry(version, day=DAY, requirements=2, deferred=0):
    return f"## v{version} — Sample (Shipped: {day})\n- Requirements: {requirements}\n- Deferred: {deferred}\n- Folder: [v{version}](v{version}/)\n"


def index_text(*entries):
    return "# Milestones\n\nNote.\n\n" + "\n".join(entries)


def add_milestone(root, version, spec=SPEC, tasks=TASKS):
    write(root, f"{MILESTONES}/v{version}/spec.md", spec)
    write(root, f"{MILESTONES}/v{version}/tasks.md", tasks)
    write(root, f"{MILESTONES}/v{version}/decisions.md", DECISIONS)


def write_manifests(root, version):
    write(root, INIT, f'__version__ = "{version}"\n')
    write(root, PYPROJECT, f'[project]\nname = "x"\nversion = "{version}"\n')
    write(root, PLUGIN, json.dumps({"name": "x", "version": version}))


def snapshot(root):
    return {path.relative_to(root).as_posix(): None if path.is_dir() else path.read_bytes() for path in root.rglob("*")}


def run_main(*arguments):
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main(list(arguments))
    return status, stdout.getvalue(), stderr.getvalue()


def findings_of(report):
    """(version, rule, severity) for each finding, in the report's order."""
    return [(entry["version"], finding["rule"], finding["severity"]) for entry in report["milestones"] for finding in entry["findings"]]


class TempCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.parent = Path(directory.name)
        self.root = self.parent / "repo"
        self.root.mkdir()

    def check(self, *versions, start=None):
        return check_milestones(self.root, MILESTONES, versions, start)


class CloseCase(TempCase):
    """A project with milestone 0.0.9 and manifests that state it; the close tests start from here."""

    def setUp(self):
        super().setUp()
        write_manifests(self.root, "0.0.9")
        add_milestone(self.root, "0.0.9")
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9"))

    def add_closable(self, version):
        """A folder of version with its checkpoint, and manifests that state it."""
        add_milestone(self.root, version)
        write(self.root, f"{MILESTONES}/v{version}/checkpoint.md", checkpoint(version))
        write_manifests(self.root, version)

    def close(self, version="0.0.9", date=DAY):
        return close_milestone(self.root, MILESTONES, version, date)

    def index(self):
        return (self.root / INDEX).read_text(encoding="utf-8")

    def refused(self, version="0.0.9", date=DAY):
        """Refuse the close with exit 1 and one stderr line per reason, write nothing, and return the stderr text."""
        before = snapshot(self.root)
        status, output, error = run_main("close", version, "--root", str(self.root), "--date", date)
        self.assertEqual((1, ""), (status, output))
        self.assertEqual(before, snapshot(self.root))
        self.assertTrue(error and all(line.startswith("inonu-harness: ") for line in error.splitlines()))
        self.assertNotIn(str(self.parent), error)
        return error


class CloseTests(CloseCase):
    def test_the_first_entry_creates_the_index_with_its_header(self):
        report = self.close()
        self.assertEqual({"schema_version": 1, "version": "0.0.9", "index": INDEX, "entry": ENTRY}, report)
        self.assertTrue(self.index().startswith("# Milestones\n\n"))
        self.assertTrue(self.index().endswith(ENTRY + "\n"))

    def test_the_command_prints_the_report_as_sorted_json_and_closes(self):
        status, output, error = run_main("close", "0.0.9", "--root", str(self.root), "--date", DAY)
        self.assertEqual((0, ""), (status, error))
        self.assertEqual(json.dumps(json.loads(output), indent=2, sort_keys=True) + "\n", output)
        self.assertEqual(["entry", "index", "schema_version", "version"], list(json.loads(output)))

    def test_the_milestone_close_command_of_the_cli_runs_the_same_code(self):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli_main(["milestone", "close", "0.0.9", "--root", str(self.root), "--date", DAY])
        self.assertEqual((0, ""), (status, stderr.getvalue()))
        self.assertEqual("0.0.9", json.loads(stdout.getvalue())["version"])

    def test_a_later_entry_goes_before_the_first(self):
        self.close()
        self.add_closable("0.0.10")
        self.close("0.0.10", "2026-02-01")
        headings = [line for line in self.index().splitlines() if line.startswith("## ")]
        self.assertEqual(["## v0.0.10 — Sample (Shipped: 2026-02-01)", "## v0.0.9 — Sample (Shipped: 2026-01-15)"], headings)
        self.assertEqual("pass", self.check()["status"])

    def test_without_a_version_the_highest_folder_is_closed(self):
        self.add_closable("0.0.10")
        self.assertEqual("0.0.10", close_milestone(self.root, MILESTONES, date="2026-02-01")["version"])

    def test_the_title_is_the_text_after_the_dash_of_the_first_heading(self):
        write(self.root, f"{MILESTONES}/v0.0.9/spec.md", SPEC.replace("# v0.0.9 — Sample", "# v0.0.9 — Closing: the `close` gate (1)"))
        self.assertEqual("## v0.0.9 — Closing: the `close` gate (1) (Shipped: 2026-01-15)", self.close()["entry"].splitlines()[0])

    def test_a_heading_without_a_dash_has_no_title(self):
        write(self.root, f"{MILESTONES}/v0.0.9/spec.md", SPEC.replace("# v0.0.9 — Sample", "# v0.0.9"))
        self.assertEqual("## v0.0.9 (Shipped: 2026-01-15)", self.close()["entry"].splitlines()[0])

    def test_the_requirement_and_the_deferred_counts_are_in_the_entry(self):
        write(self.root, f"{MILESTONES}/v0.0.9/spec.md", SPEC.replace("- R2 Second.\n", "- R2 Second.\n- R3 Third.\n"))
        write(self.root, f"{MILESTONES}/v0.0.9/tasks.md", TASKS.replace("A1: R1, R2", "A1: R1-R3"))
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", "\n## Deferred\n\n- R4 later — waits for the release\n- Second: needs a decision\n"))
        self.assertEqual(["- Requirements: 3", "- Deferred: 2"], self.close()["entry"].splitlines()[1:3])

    def test_a_deferred_item_without_a_reason_refuses_the_close(self):
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", "\n## Deferred items\n\n- Bare item\n"))
        self.assertIn("deferred_without_reason: checkpoint.md line 15 has no reason", self.refused())

    def test_a_deferred_heading_of_another_level_is_not_the_section(self):
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", "\n### Deferred\n\n- Bare item\n"))
        self.assertIn("- Deferred: 0", self.close()["entry"])

    def test_a_deferred_section_in_a_fence_or_a_comment_is_not_read(self):
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", "\n```\n## Deferred\n\n- Bare item\n```\n<!--\n## Deferred\n\n- Bare item\n-->\n"))
        self.assertIn("- Deferred: 0", self.close()["entry"])

    def test_a_missing_checkpoint_refuses(self):
        (self.root / MILESTONES / "v0.0.9" / "checkpoint.md").unlink()
        self.assertIn("checkpoint_missing: checkpoint.md is missing", self.refused())

    def test_a_checkpoint_that_is_not_a_regular_file_refuses(self):
        path = self.root / MILESTONES / "v0.0.9" / "checkpoint.md"
        path.unlink()
        path.mkdir()
        self.assertIn("file_unreadable: checkpoint.md is not a regular file", self.refused())

    def test_a_checkpoint_that_names_another_version_refuses(self):
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.8"))
        self.assertIn("checkpoint_version_mismatch: checkpoint.md does not name v0.0.9 in its first non-empty line", self.refused())

    def test_a_checkpoint_without_a_status_line_refuses(self):
        for text in (checkpoint("0.0.9").replace("Status: shipped.", "The state is shipped."), checkpoint("0.0.9").replace("Status: shipped.", "```\nStatus: shipped.\n```")):
            with self.subTest(text=text[:24]):
                write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", text)
                self.assertIn("checkpoint_status_missing: checkpoint.md has no line that starts with Status:", self.refused())

    def test_a_checkpoint_without_a_verification_or_a_limits_heading_refuses(self):
        for heading, text in (("Verification", checkpoint("0.0.9").replace("## Verification", "### Verification")), ("Limits", checkpoint("0.0.9").replace("## Limits", "## Bounds"))):
            with self.subTest(heading=heading):
                write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", text)
                self.assertIn(f"checkpoint_section_missing: checkpoint.md has no ## {heading} heading", self.refused())

    def test_a_check_error_of_the_folder_refuses(self):
        write(self.root, f"{MILESTONES}/v0.0.9/tasks.md", TASKS.replace("A1: R1, R2", "A1: R1"))
        self.assertIn("requirement_unclaimed: R2 is cited by no table row of tasks.md", self.refused())

    def test_manifests_that_state_another_version_refuse(self):
        write_manifests(self.root, "0.0.8")
        self.assertIn("manifests_not_bumped: the manifests do not all state 0.0.9; bump them first", self.refused())

    def test_manifests_that_disagree_refuse(self):
        write(self.root, PLUGIN, json.dumps({"name": "x", "version": "0.0.10"}))
        self.assertIn(f"{PLUGIN} has version 0.0.10 but {INIT} has version 0.0.9", self.refused())

    def test_manifests_outside_the_scheme_refuse(self):
        write_manifests(self.root, "1.0.0")
        self.assertIn(f"{INIT} has version 1.0.0, which is not in the 0.MINOR.PATCH scheme", self.refused())

    def test_a_project_without_manifests_is_not_held_to_them(self):
        for rel in (INIT, PYPROJECT, PLUGIN):
            (self.root / rel).unlink()
        self.assertEqual(ENTRY, self.close()["entry"])

    def test_a_version_not_above_the_index_refuses(self):
        self.close()
        self.add_closable("0.0.8")
        self.assertIn("version_not_higher: v0.0.8 is not higher than v0.0.9", self.refused("0.0.8"))

    def test_a_version_already_in_the_index_refuses(self):
        self.close()
        self.assertIn("version_closed: the index already has v0.0.9", self.refused())

    def test_a_date_earlier_than_an_entry_in_the_index_refuses(self):
        self.close()
        self.add_closable("0.0.10")
        self.assertIn("index_date_order: 2025-12-01 is earlier than 2026-01-15", self.refused("0.0.10", "2025-12-01"))

    def test_a_malformed_index_refuses_with_its_line(self):
        write(self.root, INDEX, "# Milestones\n\nNote.\n\nstray text\n")
        self.assertIn("index_malformed: a line before the first entry is not part of the format (line 5)", self.refused())

    def test_an_index_path_that_resolves_outside_the_root_refuses_and_is_not_read(self):
        outside = self.parent / "outside.md"
        outside.write_text("# Milestones\n", encoding="utf-8")
        real = Path.resolve

        def resolve(path, *arguments, **keywords):
            return outside if path.name == "MILESTONES.md" else real(path, *arguments, **keywords)

        with mock.patch.object(Path, "resolve", resolve):
            error = self.refused()
        self.assertIn("link_escapes_root: MILESTONES.md resolves outside the root", error)
        self.assertEqual("# Milestones\n", outside.read_text(encoding="utf-8"))

    def test_an_oversized_or_non_utf8_index_refuses(self):
        write(self.root, INDEX, b"x" * (MAX_BYTES + 1))
        self.assertIn("file_unreadable: MILESTONES.md is larger than", self.refused())
        write(self.root, INDEX, b"# Milestones\n\xff\n")
        self.assertIn("file_unreadable: MILESTONES.md is not UTF-8", self.refused())

    def test_a_failed_replace_leaves_the_old_index_and_no_temporary_file(self):
        self.close()
        self.add_closable("0.0.10")
        before = self.index()
        with mock.patch.object(milestones.os, "replace", side_effect=OSError(28, "no space left")), self.assertRaises(Refused):
            self.close("0.0.10", "2026-02-01")
        self.assertEqual(before, self.index())
        self.assertEqual(["MILESTONES.md", "v0.0.10", "v0.0.9"], sorted(path.name for path in (self.root / MILESTONES).iterdir()))

    def test_a_version_without_a_folder_or_outside_the_scheme_is_invalid_input(self):
        before = snapshot(self.root)
        for version in ("0.0.7", "v0.0.9", "1.0.0"):
            with self.subTest(version=version):
                self.assertEqual(2, run_main("close", version, "--root", str(self.root), "--date", DAY)[0])
        self.assertEqual(before, snapshot(self.root))

    def test_a_malformed_or_impossible_date_is_invalid_input(self):
        before = snapshot(self.root)
        for date in ("2026-02-30", "26-1-1", "", "2026-01-15 "):
            with self.subTest(date=date):
                status, output, error = run_main("close", "0.0.9", "--root", str(self.root), "--date", date)
                self.assertEqual((2, ""), (status, output))
                self.assertIn("--date must be a real calendar date in the form YYYY-MM-DD", error)
        self.assertEqual(before, snapshot(self.root))

    def test_without_a_date_the_entry_takes_today(self):
        before = datetime.date.today()
        self.close(date=None)
        after = datetime.date.today()
        self.assertTrue(any(f"(Shipped: {day.isoformat()})" in self.index() for day in (before, after)))

    def test_a_root_without_milestones_refuses_the_close(self):
        empty = self.parent / "empty"
        empty.mkdir()
        status, _, error = run_main("close", "--root", str(empty))
        self.assertEqual((1, "there is no milestone folder to close"), (status, error.replace("inonu-harness: ", "").strip()))
        status, _, error = run_main("close", "0.0.9", "--root", str(empty))
        self.assertEqual(1, status)
        self.assertIn("the milestone folder for 0.0.9 does not exist", error)


class CheckTests(TempCase):
    def setUp(self):
        super().setUp()
        add_milestone(self.root, "0.0.9")
        add_milestone(self.root, "0.0.10")

    def index_rules(self, text, start=None):
        """The (rule, severity) of the index findings once the index holds text."""
        write(self.root, INDEX, text)
        return [(rule, severity) for version, rule, severity in findings_of(self.check(start=start)) if version == "index"]

    def test_the_checkpoint_names_its_whole_version_in_the_first_non_empty_line(self):
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.10"))
        write(self.root, f"{MILESTONES}/v0.0.10/checkpoint.md", checkpoint("0.0.1"))
        self.assertEqual([("0.0.9", "checkpoint_version_mismatch", "error"), ("0.0.10", "checkpoint_version_mismatch", "error")], findings_of(self.check()))
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", "\n\n" + checkpoint("0.0.9"))
        write(self.root, f"{MILESTONES}/v0.0.10/checkpoint.md", "# Notes\n\n" + checkpoint("0.0.10"))
        self.assertEqual([("0.0.10", "checkpoint_version_mismatch", "error")], findings_of(self.check()))

    def test_a_milestone_without_a_checkpoint_passes_and_the_exit_code_follows_a_mismatch(self):
        self.assertEqual([], findings_of(self.check()))
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.8"))
        self.assertEqual(1, run_main("check", "--root", str(self.root))[0])

    def test_every_index_rule_is_an_error_of_the_index(self):
        cases = {
            "index_malformed": index_text(index_entry("0.0.10")) + "stray\n",
            "index_order": index_text(index_entry("0.0.9"), index_entry("0.0.10")),
            "index_duplicate": index_text(index_entry("0.0.10"), index_entry("0.0.10")),
            "index_link_broken": index_text(index_entry("0.0.11")),
            "index_date_invalid": index_text(index_entry("0.0.10", day="2026-02-30")),
            "index_date_order": index_text(index_entry("0.0.10", day="2026-01-01"), index_entry("0.0.9")),
        }
        for rule, text in cases.items():
            with self.subTest(rule=rule):
                self.assertIn((rule, "error"), self.index_rules(text))

    def test_an_index_without_its_heading_or_its_description_is_malformed(self):
        self.assertIn(("index_malformed", "error"), self.index_rules(index_entry("0.0.10")))
        self.assertIn(("index_malformed", "error"), self.index_rules("# Milestones\n\n" + index_entry("0.0.10")))

    def test_a_clean_index_is_reported_as_an_entry_with_no_findings(self):
        write(self.root, INDEX, index_text(index_entry("0.0.10"), index_entry("0.0.9")))
        report = self.check()
        self.assertEqual({"findings": [], "version": "index"}, report["milestones"][-1])
        self.assertEqual("pass", report["status"])

    def test_a_missing_index_adds_no_entry(self):
        self.assertNotIn("index", [entry["version"] for entry in self.check()["milestones"]])

    def test_the_index_is_linted_whatever_the_from_or_the_named_versions(self):
        write(self.root, INDEX, "# Milestones\n\nNote.\n\nstray text\n")
        self.assertIn(("index", "index_malformed", "error"), findings_of(self.check(start="0.0.10")))
        self.assertIn(("index", "index_malformed", "error"), findings_of(self.check("0.0.9")))
        self.assertEqual(1, run_main("check", "--root", str(self.root), "--from", "0.0.10")[0])
        write(self.root, INDEX, index_text(index_entry("0.0.10")))
        self.assertEqual(0, run_main("check", "--root", str(self.root), "--from", "0.0.10")[0])


class RepositoryTests(unittest.TestCase):
    def test_this_repository_has_no_milestone_error_from_v0_0_9(self):
        report = check_milestones(REPO_ROOT, MILESTONES, start="0.0.9")
        self.assertEqual("pass", report["status"], findings_of(report))

    def test_a_closed_copy_of_the_v0_0_25_folder_in_a_temporary_project_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(REPO_ROOT / MILESTONES / "v0.0.25", root / MILESTONES / "v0.0.25")
            write_manifests(root, "0.0.25")
            close_milestone(root, MILESTONES, "0.0.25", "2026-10-26")
            report = check_milestones(root, MILESTONES)
            self.assertEqual("pass", report["status"], findings_of(report))
            self.assertEqual(["0.0.25", "index"], [entry["version"] for entry in report["milestones"]])


class ReviewFixTests(CloseCase):
    def test_a_version_named_only_inside_a_comment_is_not_the_first_line(self):
        for first in ("<!-- v0.0.9 -->\n# v0.0.1 — copied", "# v0.0.1 <!-- v0.0.9 -->"):
            with self.subTest(first=first):
                write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", first + "\n\nStatus: shipped.\n\n## Verification\n\nx\n\n## Limits\n\ny\n")
                self.assertIn("checkpoint_version_mismatch", self.refused())

    def test_a_checkpoint_of_a_longer_version_does_not_close_a_shorter_one(self):
        self.add_closable("0.0.1")
        write(self.root, f"{MILESTONES}/v0.0.1/checkpoint.md", checkpoint("0.0.10"))
        self.assertIn("checkpoint_version_mismatch", self.refused("0.0.1"))

    def test_status_must_start_the_line(self):
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9").replace("Status: shipped.", "   Status: shipped."))
        self.assertIn("checkpoint_status_missing", self.refused())

    def test_headings_inside_a_fence_or_a_comment_are_not_headings(self):
        fenced = "# v0.0.9 — checkpoint\n\nStatus: shipped.\n\n```\n## Verification\n```\n\n<!--\n## Limits\n-->\n"
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", fenced)
        error = self.refused()
        self.assertIn("checkpoint_section_missing: checkpoint.md has no ## Verification heading", error)
        self.assertIn("checkpoint_section_missing: checkpoint.md has no ## Limits heading", error)

    def test_a_heading_after_the_end_of_a_comment_on_the_same_line_is_not_a_heading(self):
        text = checkpoint("0.0.9").replace("## Limits", "<!--x-->## Limits")
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", text)
        self.assertIn("checkpoint_section_missing", self.refused())

    def test_warnings_do_not_refuse_a_close(self):
        (self.root / MILESTONES / "v0.0.9" / "decisions.md").unlink()
        self.assertIn(("0.0.9", "decisions_missing", "warning"), findings_of(self.check()))
        self.assertEqual("0.0.9", self.close()["version"])

    def test_two_milestones_may_close_on_the_same_day(self):
        self.close()
        self.add_closable("0.0.10")
        self.assertEqual("0.0.10", self.close("0.0.10")["version"])

    def test_the_index_stays_newest_first_over_several_closes(self):
        self.close()
        for version in ("0.0.10", "0.0.11", "0.0.12"):
            self.add_closable(version)
            self.close(version, "2026-02-01")
        headings = [line for line in self.index().splitlines() if line.startswith("## ")]
        self.assertEqual(["0.0.12", "0.0.11", "0.0.10", "0.0.9"], [line.split()[1][1:] for line in headings])
        self.assertEqual("pass", self.check()["status"])

    def test_deferred_headings_in_any_case_and_indented_items_are_counted(self):
        extra = "\n## DEFERRED ITEMS ##\n\n 1. one without a reason\n* two — has a reason\n   - three: has one too\n"
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", extra))
        error = self.refused()
        self.assertEqual(1, error.count("deferred_without_reason"))
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", extra.replace("one without a reason", "one: with a reason")))
        self.assertIn("- Deferred: 3", self.close()["entry"])

    def test_a_hyphen_does_not_separate_a_reason(self):
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", "\n## Deferred\n\n- item - because\n"))
        self.assertIn("deferred_without_reason", self.refused())

    def test_a_shipping_date_later_than_today_is_invalid_input(self):
        status, output, error = run_main("close", "0.0.9", "--root", str(self.root), "--date", "2999-01-01")
        self.assertEqual((2, ""), (status, output))
        self.assertIn("later than today", error)
        self.assertEqual("0.0.9", close_milestone(self.root, MILESTONES, "0.0.9", "2999-01-01", today=datetime.date(2999, 1, 1))["version"])

    def test_a_title_with_a_control_character_is_left_out_of_the_entry(self):
        spec = SPEC.replace("# v0.0.9 — Sample", "# v0.0.9 — Sample\u2028line two")
        write(self.root, f"{MILESTONES}/v0.0.9/spec.md", spec)
        self.assertEqual("## v0.0.9 (Shipped: 2026-01-15)", self.close()["entry"].splitlines()[0])

    def test_a_comment_opener_inside_a_code_span_is_text_and_hides_nothing(self):
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9").replace("## Verification", "The marker `<!--` is text.\n\n## Verification"))
        self.assertEqual("0.0.9", self.close()["version"])
        write(self.root, f"{MILESTONES}/v0.0.9/spec.md", SPEC.replace("- R1 First.", "- R1 First, with a `<!--` in code."))
        self.assertEqual([], [finding for finding in self.check()["milestones"][0]["findings"] if finding["severity"] == "error"])

    def test_a_double_backtick_span_and_an_unclosed_run_are_read_as_commonmark_does(self):
        from inonu_harness.milestones import _mask_code_spans
        self.assertEqual("a " + " " * 9 + " b", _mask_code_spans("a ``x ` y`` b"))
        self.assertEqual("a ` b <!--", _mask_code_spans("a ` b <!--"))
        self.assertEqual("no code", _mask_code_spans("no code"))

    def test_a_line_of_many_backticks_costs_linear_time(self):
        line = "`" * 400000 + "<!--"
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", "\n" + line + "\n"))
        started = time.monotonic()
        self.check()
        self.assertLess(time.monotonic() - started, 5)

    def test_a_long_run_of_comment_openers_costs_linear_time(self):
        line = "text " + "<!--" * 200000
        write(self.root, f"{MILESTONES}/v0.0.9/checkpoint.md", checkpoint("0.0.9", "\n" + line + "\n"))
        started = time.monotonic()
        self.check()
        self.assertLess(time.monotonic() - started, 5)


if __name__ == "__main__":
    unittest.main()
