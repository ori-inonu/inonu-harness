import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from inonu_harness import milestones
from inonu_harness.cli import main as cli_main
from inonu_harness.milestones import MAX_BYTES, Refused, check_milestones, main, new_milestone
from inonu_harness.versions import INIT, PLUGIN, PYPROJECT, next_version, stated_versions


REPO_ROOT = Path(__file__).resolve().parents[1]
MILESTONES = "docs/specs/milestones"
IDENTITY = ("-c", "user.email=t@example.test", "-c", "user.name=t")
PASSING_TEST = "import unittest\n\n\nclass SampleTests(unittest.TestCase):\n    def test_passes(self):\n        self.assertTrue(True)\n"
RUNNER = 'print("inonu-harness test")\n'
SPEC = "# v0.0.9 — Sample\n\n## Requirements\n\n- R1 First.\n- R2 Second.\n\n## Out of scope\n\nNothing.\n"
TASKS = "| Task | Depends on | Ownership | Acceptance |\n| --- | --- | --- | --- |\n| T01 one | none | x | A1: R1, R2 |\n"
DECISIONS = "## D1 — Scope\n\nText.\n"


def write(root, rel, content):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))


def add_milestone(root, version, spec=SPEC, tasks=TASKS, decisions=DECISIONS):
    """A milestone folder named for version; a None text leaves that file out."""
    for name, text in (("spec.md", spec), ("tasks.md", tasks), ("decisions.md", decisions)):
        if text is not None:
            write(root, f"{MILESTONES}/v{version}/{name}", text)


def write_manifests(root, version):
    write(root, INIT, f'__version__ = "{version}"\n')
    write(root, PYPROJECT, f'[project]\nname = "x"\nversion = "{version}"\n')
    write(root, PLUGIN, json.dumps({"name": "x", "version": version}))


def snapshot(root):
    return {path.relative_to(root).as_posix(): None if path.is_dir() else path.read_bytes() for path in root.rglob("*")}


def run_main(*arguments):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main(list(arguments))
    return status, stdout.getvalue(), stderr.getvalue()


def run_cli(*arguments):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = cli_main(list(arguments))
    return status, stdout.getvalue(), stderr.getvalue()


def findings_of(report):
    """(version, rule, severity) for each finding, in the report's order."""
    return [(entry["version"], finding["rule"], finding["severity"]) for entry in report["milestones"] for finding in entry["findings"]]


def git(repo, *arguments):
    subprocess.run(["git", "-C", str(repo), *IDENTITY, *arguments], check=True, stdin=subprocess.DEVNULL, capture_output=True)


def make_checkout(root):
    """A checkout that `check` accepts: the whole package, so that `python -m inonu_harness` runs there, and one passing test."""
    shutil.copytree(REPO_ROOT / "inonu_harness", root / "inonu_harness", ignore=shutil.ignore_patterns("__pycache__"))
    write(root, "tests/test_ok.py", PASSING_TEST)
    write(root, "scripts/inonu.py", RUNNER)


def steps_of(output):
    return [(step["name"], step["exit_code"]) for step in json.loads(output)["steps"]]


class TempCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.parent = Path(directory.name)
        self.root = self.parent / "repo"
        self.root.mkdir()

    def check(self, *versions, start=None):
        return check_milestones(self.root, MILESTONES, versions, start)

    def link_directory(self, target, link):
        """Point link at target as a symlink or, on Windows, a junction; skip the test when neither can be made."""
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            # Windows needs a privilege for symlinks but not for a directory junction, which resolves the same way.
            made = os.name == "nt" and subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=False,
            ).returncode == 0
            if not made:
                self.skipTest("directory links are not available on this host")


class ScaffoldTests(TempCase):
    def test_the_first_milestone_in_an_empty_root_is_0_0_1(self):
        report = new_milestone(self.root, MILESTONES, "Sample")
        self.assertEqual(
            {"schema_version": 1, "version": "0.0.1", "directory": f"{MILESTONES}/v0.0.1", "files": ["spec.md", "decisions.md", "tasks.md"]},
            report,
        )
        folder = self.root / MILESTONES / "v0.0.1"
        self.assertEqual(["decisions.md", "spec.md", "tasks.md"], sorted(path.name for path in folder.iterdir()))

    def test_the_templates_are_the_fixed_text_and_the_title_is_only_the_spec_heading(self):
        new_milestone(self.root, MILESTONES, "Sample title")
        folder = self.root / MILESTONES / "v0.0.1"
        spec = (folder / "spec.md").read_text(encoding="utf-8")
        self.assertEqual("# v0.0.1 — Sample title\n\n## Requirements\n\n- R1 <...>\n\n## Out of scope\n\n<...>\n", spec)
        self.assertEqual(
            "| Task | Depends on | Ownership | Acceptance |\n| --- | --- | --- | --- |\n| T01 <...> | none | <...> | A1: R1 <...> |\n",
            (folder / "tasks.md").read_text(encoding="utf-8"),
        )
        self.assertEqual("## D1 — Scope\n\n<...>\n", (folder / "decisions.md").read_text(encoding="utf-8"))

    def test_without_a_title_the_spec_heading_keeps_its_placeholder(self):
        new_milestone(self.root)
        self.assertEqual("# v0.0.1 — <title>", (self.root / MILESTONES / "v0.0.1" / "spec.md").read_text(encoding="utf-8").splitlines()[0])

    def test_the_next_version_comes_from_the_manifests_before_the_folders(self):
        write_manifests(self.root, "0.0.5")
        add_milestone(self.root, "0.0.9")
        self.assertEqual("0.0.6", new_milestone(self.root)["version"])

    def test_the_next_version_comes_from_the_manifests_alone_or_the_highest_folder_alone(self):
        write_manifests(self.root, "0.0.24")
        self.assertEqual("0.0.25", new_milestone(self.root)["version"])
        empty = self.parent / "folders"
        empty.mkdir()
        for version in ("0.0.3", "0.0.20", "0.0.9"):
            add_milestone(empty, version)
        add_milestone(empty, "0.0.100")  # outside the scheme: never the highest
        write(empty, f"{MILESTONES}/notes/spec.md", SPEC)  # not a version: ignored
        self.assertEqual("0.0.21", new_milestone(empty)["version"])
        highest = self.parent / "last"
        add_milestone(highest, "0.0.99")
        self.assertEqual("0.1.0", new_milestone(highest)["version"])

    def test_manifests_outside_the_scheme_or_in_disagreement_refuse_and_create_nothing(self):
        write_manifests(self.root, "1.0.0")
        before = snapshot(self.root)
        with self.assertRaises(Refused):
            new_milestone(self.root)
        self.assertEqual(before, snapshot(self.root))
        write_manifests(self.root, "0.0.5")
        write(self.root, PLUGIN, json.dumps({"name": "x", "version": "0.0.6"}))
        before = snapshot(self.root)
        with self.assertRaises(Refused) as raised:
            new_milestone(self.root)
        self.assertIn(f"{PLUGIN} has version 0.0.6 but {INIT} has version 0.0.5", str(raised.exception))
        self.assertEqual(before, snapshot(self.root))
        write(self.root, INIT, '"""Package."""\n')  # a manifest with no version is a problem too
        with self.assertRaises(Refused):
            new_milestone(self.root)

    def test_an_existing_folder_or_file_in_the_way_refuses_and_changes_nothing(self):
        write_manifests(self.root, "0.0.24")
        (self.root / MILESTONES / "v0.0.25").mkdir(parents=True)
        before = snapshot(self.root)
        with self.assertRaises(Refused):
            new_milestone(self.root)
        self.assertEqual(before, snapshot(self.root))
        (self.root / MILESTONES / "v0.0.25").rmdir()
        write(self.root, f"{MILESTONES}/v0.0.25", "a file, not a folder")
        before = snapshot(self.root)
        with self.assertRaises(Refused):
            new_milestone(self.root)
        self.assertEqual(before, snapshot(self.root))

    def test_the_last_version_refuses_with_the_message_of_version_next(self):
        with self.assertRaises(ValueError) as expected:
            next_version("0.99.99")
        write_manifests(self.root, "0.99.99")
        with self.assertRaises(Refused) as raised:
            new_milestone(self.root)
        self.assertEqual(str(expected.exception), str(raised.exception))
        status, _, error = run_main("new", "--root", str(self.root))
        self.assertEqual((1, str(expected.exception)), (status, error.replace("inonu-harness: ", "").strip()))
        highest = self.parent / "last"
        add_milestone(highest, "0.99.99")
        with self.assertRaises(Refused):
            new_milestone(highest)

    def test_the_title_is_one_line_of_one_to_one_hundred_and_twenty_characters_without_control_characters(self):
        new_milestone(self.root, title="x" * 120)
        before = snapshot(self.root)
        for bad in ("", "x" * 121, "a\nb", "a\rb", "a\tb", "a\u2028b", "a\x00b"):
            with self.subTest(title=bad), self.assertRaises(ValueError):
                new_milestone(self.root, title=bad)
        self.assertEqual(before, snapshot(self.root))
        new_milestone(self.root, title="Café — {braces} ok")
        self.assertIn("# v0.0.2 — Café — {braces} ok", (self.root / MILESTONES / "v0.0.2" / "spec.md").read_text(encoding="utf-8"))

    def test_a_failed_write_removes_the_files_and_the_folders_this_run_made(self):
        before = snapshot(self.root)
        real_open = open

        def failing(path, *args, **kwargs):
            if Path(path).name == "tasks.md":
                raise OSError(28, "no space left")
            return real_open(path, *args, **kwargs)

        with mock.patch.object(milestones, "open", failing, create=True), self.assertRaises(Refused):
            new_milestone(self.root)
        self.assertEqual(before, snapshot(self.root))

    def test_the_folder_is_created_exclusively_and_a_file_that_appears_meanwhile_is_never_overwritten(self):
        prior = "prior text\n"
        real_mkdir = os.mkdir

        def racing(path, *args, **kwargs):
            real_mkdir(path, *args, **kwargs)
            if Path(path).name == "v0.0.1":  # another party writes spec.md right after the folder appears
                Path(path, "spec.md").write_text(prior, encoding="utf-8")

        with mock.patch.object(milestones.os, "mkdir", racing), self.assertRaises(Refused):
            new_milestone(self.root)
        folder = self.root / MILESTONES / "v0.0.1"
        self.assertEqual(prior, (folder / "spec.md").read_text(encoding="utf-8"))
        self.assertEqual(["spec.md"], [path.name for path in folder.iterdir()])

    def test_the_output_names_no_absolute_path(self):
        status, output, error = run_main("new", "--root", str(self.root), "--title", "Sample")
        self.assertEqual((0, ""), (status, error))
        self.assertNotIn(str(self.parent), output)
        write(self.root, f"{MILESTONES}/notes/spec.md", SPEC)
        status, output, error = run_main("check", "--root", str(self.root))
        self.assertEqual(1, status)
        self.assertNotIn(str(self.parent), output + error)

    def test_a_scaffolded_folder_passes_the_check(self):
        new_milestone(self.root, title="Sample")
        report = self.check()
        self.assertEqual("pass", report["status"])
        self.assertEqual([], findings_of(report))

    def test_a_custom_directory_is_created_with_its_missing_parents(self):
        report = new_milestone(self.root, "plans/milestones")
        self.assertEqual("plans/milestones/v0.0.1", report["directory"])
        self.assertTrue((self.root / "plans" / "milestones" / "v0.0.1" / "tasks.md").is_file())


class ContainmentTests(TempCase):
    def test_a_milestones_directory_that_is_a_link_outside_the_root_is_refused(self):
        outside = self.parent / "outside"
        outside.mkdir()
        (self.root / "docs" / "specs").mkdir(parents=True)
        self.link_directory(outside, self.root / MILESTONES)
        with self.assertRaises(ValueError):
            new_milestone(self.root)
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual([], list(outside.iterdir()))
        self.assertEqual((2, ""), run_main("check", "--root", str(self.root))[:2])

    def test_a_parent_of_the_milestones_directory_that_is_a_link_outside_the_root_is_refused(self):
        outside = self.parent / "outside"
        (outside / "specs" / "milestones").mkdir(parents=True)
        self.link_directory(outside, self.root / "docs")
        with self.assertRaises(ValueError):
            new_milestone(self.root)
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual([], list((outside / "specs" / "milestones").iterdir()))

    def test_a_milestone_folder_that_is_a_link_outside_the_root_is_reported_and_not_read(self):
        outside = self.parent / "outside"
        write(outside, "spec.md", SPEC)
        write(outside, "tasks.md", TASKS)
        write(outside, "decisions.md", DECISIONS)
        (self.root / MILESTONES).mkdir(parents=True)
        self.link_directory(outside, self.root / MILESTONES / "v0.0.9")
        report = self.check()
        self.assertEqual([("0.0.9", "link_escapes_root", "error")], findings_of(report))
        self.assertEqual("fail", report["status"])

    def test_a_spec_file_that_is_a_link_outside_the_root_is_reported_and_not_read(self):
        outside = self.parent / "outside.md"
        outside.write_text(SPEC, encoding="utf-8")
        add_milestone(self.root, "0.0.9", spec=None)
        try:
            os.symlink(outside, self.root / MILESTONES / "v0.0.9" / "spec.md")
        except (OSError, NotImplementedError):
            self.skipTest("file symbolic links are not available on this host")
        self.assertEqual([("0.0.9", "link_escapes_root", "error")], findings_of(self.check()))

    def test_a_directory_that_escapes_the_root_is_absolute_or_is_the_root_itself_is_refused(self):
        for directory in ("../elsewhere", "docs/../../elsewhere", str(self.parent / "elsewhere"), "", "."):
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    new_milestone(self.root, directory)
                with self.assertRaises(ValueError):
                    check_milestones(self.root, directory)
                self.assertEqual(2, run_main("check", "--root", str(self.root), "--dir", directory)[0])
        self.assertFalse((self.parent / "elsewhere").exists())

    def test_a_root_that_does_not_exist_is_invalid_input(self):
        absent = self.parent / "absent"
        with self.assertRaises(ValueError):
            check_milestones(absent, MILESTONES)
        self.assertEqual((2, ""), run_main("new", "--root", str(absent))[:2])
        self.assertEqual((2, ""), run_main("check", "--root", str(absent))[:2])

    def test_a_missing_milestones_directory_has_nothing_to_check_and_new_creates_it(self):
        self.assertEqual({"schema_version": 1, "status": "pass", "milestones": []}, self.check())
        self.assertEqual("pass", check_milestones(self.root, MILESTONES, ["0.0.1"])["status"])
        self.assertFalse((self.root / "docs").exists())
        new_milestone(self.root)
        self.assertTrue((self.root / MILESTONES / "v0.0.1").is_dir())

    def test_a_milestones_directory_that_is_a_file_is_invalid_input(self):
        write(self.root, MILESTONES, "not a folder")
        with self.assertRaises(ValueError):
            self.check()
        with self.assertRaises(ValueError):
            new_milestone(self.root)


class CheckRuleTests(TempCase):
    def test_a_folder_name_that_is_not_a_version_or_is_outside_the_scheme_is_an_error(self):
        for name in ("notes", "v0.0.0", "v0.01.1", "v0.0.100", "v1.0.0", "v00.0.1"):
            (self.root / MILESTONES / name).mkdir(parents=True)
        report = self.check()
        self.assertEqual(
            [
                ("0.0.0", "milestone_not_in_scheme", "error"),
                ("0.0.100", "milestone_not_in_scheme", "error"),
                ("0.01.1", "milestone_not_in_scheme", "error"),
                ("00.0.1", "milestone_not_in_scheme", "error"),
                ("1.0.0", "milestone_not_in_scheme", "error"),
                ("notes", "milestone_name_invalid", "error"),
            ],
            findings_of(report),
        )
        self.assertEqual("fail", report["status"])

    def test_files_in_the_milestones_directory_are_ignored(self):
        write(self.root, f"{MILESTONES}/v0.0.9", "a file named like a folder")
        write(self.root, f"{MILESTONES}/README.md", "notes")
        self.assertEqual([], self.check()["milestones"])

    def test_a_missing_spec_or_tasks_is_an_error_and_a_missing_decisions_file_a_warning(self):
        add_milestone(self.root, "0.0.1", spec=None)
        add_milestone(self.root, "0.0.2", tasks=None)
        add_milestone(self.root, "0.0.3", decisions=None)
        self.assertEqual(
            [
                ("0.0.1", "required_file_missing", "error"),
                ("0.0.2", "required_file_missing", "error"),
                ("0.0.3", "decisions_missing", "warning"),
            ],
            findings_of(self.check()),
        )
        self.assertEqual("pass", self.check("0.0.3")["status"])
        self.assertEqual(0, run_main("check", "--root", str(self.root), "0.0.3")[0])

    def test_a_file_that_cannot_be_read_is_an_error(self):
        add_milestone(self.root, "0.0.1", spec=b"# v0.0.1\n\xff\n- R1 bad utf-8\n")
        add_milestone(self.root, "0.0.2", tasks=b"x" * (MAX_BYTES + 1))
        add_milestone(self.root, "0.0.3", tasks=b"x" * MAX_BYTES)  # exactly one mebibyte is read
        self.assertEqual(
            [("0.0.1", "file_unreadable", "error"), ("0.0.2", "file_unreadable", "error"), ("0.0.3", "tasks_not_found", "warning")],
            findings_of(self.check()),
        )

    def test_a_file_the_process_cannot_open_is_an_error_and_names_no_path(self):
        add_milestone(self.root, "0.0.1")
        real_open = Path.open

        def denied(path, *args, **kwargs):
            if path.name == "spec.md":
                raise PermissionError(13, "permission denied", str(path))
            return real_open(path, *args, **kwargs)

        with mock.patch.object(Path, "open", denied):
            report = self.check()
        self.assertEqual([("0.0.1", "file_unreadable", "error")], findings_of(report))
        self.assertNotIn(str(self.parent), json.dumps(report))

    def test_a_requirement_defined_twice_is_an_error_at_its_second_line(self):
        add_milestone(self.root, "0.0.1", spec="# v0.0.1 — x\n\n## Requirements\n\n- R1 a\n- R2 b\n- R1 again\n", tasks="| T01 | none | x | A1: R1, R2 |\n")
        report = self.check()
        self.assertEqual([("0.0.1", "requirement_duplicate", "error")], findings_of(report))
        self.assertEqual(7, report["milestones"][0]["findings"][0]["line"])

    def test_ids_with_a_gap_are_a_warning_and_the_check_still_passes(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n- R3 c\n", tasks="| T01 | none | x | A1: R1, R3 |\n")
        report = self.check()
        self.assertEqual([("0.0.1", "requirement_gap", "warning")], findings_of(report))
        self.assertEqual("pass", report["status"])

    def test_a_requirement_inside_a_fenced_block_does_not_count(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n```md\n- R1 example\n```\n", tasks="| T01 | none | x | A1: R1 |\n")
        self.assertEqual([("0.0.1", "requirements_not_found", "warning")], findings_of(self.check()))

    def test_bold_and_star_items_count_as_requirements(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- **R1** first\n* R2 second\n", tasks="| T01 | none | x | A1: R1 |\n")
        self.assertEqual([("0.0.1", "requirement_unclaimed", "error")], findings_of(self.check()))

    def test_requirements_continue_under_a_revision_heading_and_stop_at_a_section_for_deferred_work(self):
        spec = "# v0.0.1 — x\n\n## Requirements\n\n- R1 a\n\n## Revision after review\n\n- R2 b\n\n## Out of scope\n\n- R3 deferred\n- R1 deferred too\n"
        add_milestone(self.root, "0.0.1", spec=spec, tasks="| T01 | none | x | A1: R1, R2 |\n")
        self.assertEqual([], findings_of(self.check()))
        add_milestone(self.root, "0.0.2", spec=spec, tasks="| T01 | none | x | A1: R1, R2, R3 |\n")
        self.assertEqual([("0.0.2", "task_cites_unknown_requirement", "error")], findings_of(self.check("0.0.2")))

    def test_a_byte_order_mark_on_the_first_line_is_accepted(self):
        spec = b"\xef\xbb\xbf## Requirements\n\n- R1 a\n- R2 b\n"
        add_milestone(self.root, "0.0.1", spec=spec, tasks="| T01 | none | x | A1: R1 |\n")
        self.assertEqual([("0.0.1", "requirement_unclaimed", "error")], findings_of(self.check()))

    def test_tilde_fences_html_comments_and_prose_with_a_pipe_are_not_read(self):
        spec = "## Requirements\n\n- R1 a\n~~~\n- R2 inside a tilde fence\n~~~\n<!--\n- R3 retired\n-->\n<!-- - R4 retired --> \n"
        tasks = "<!--\n| T09 | none | x | A1: R9 |\n-->\nT01 covers R1 | R2 in prose\n| T01 | none | x | A1: R1 |\n"
        add_milestone(self.root, "0.0.1", spec=spec, tasks=tasks)
        self.assertEqual([], findings_of(self.check()))
        add_milestone(self.root, "0.0.2", spec="## Requirements\n\n- R1 a\n- R2 b\n", tasks="T01 covers R1 | R2 in prose\n| T01 | none | x | A1: R1 |\n")
        self.assertEqual([("0.0.2", "requirement_unclaimed", "error")], findings_of(self.check("0.0.2")))

    def test_a_comment_closed_on_its_own_line_does_not_swallow_what_follows(self):
        spec = "## Requirements\n\n- R1 a\n<!-- - R9 retired -->\n- R2 b\ntext <!-- inline --> more\n- R3 c\n"
        add_milestone(self.root, "0.0.1", spec=spec, tasks="| T01 | none | x | A1: R1, R2, R3 |\n")
        self.assertEqual([], findings_of(self.check()))

    def test_a_citation_glued_to_letters_or_digits_is_not_a_citation(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n- R2 b\n", tasks="| T01 | none | x | A1: R1, R2D2, R2_final |\n")
        self.assertEqual([("0.0.1", "requirement_unclaimed", "error")], findings_of(self.check()))

    def test_ids_with_more_than_nine_digits_are_invalid_references_and_never_a_crash(self):
        for cell in ("R1, R1234567890", "R1-R1000000000", "R1..R9999999999999", "R1, R" + "9" * 5000):
            with self.subTest(cell=cell[:30]):
                add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n", tasks=f"| T01 | none | x | A1: {cell} |\n")
                rules = [rule for _, rule, _ in findings_of(self.check())]
                self.assertEqual(1, rules.count("reference_range_invalid"))
                self.assertNotIn("task_cites_unknown_requirement", rules)  # an invalid range cites nothing, so R1 may be unclaimed

    def test_ranges_are_not_expanded_and_the_findings_per_rule_are_capped(self):
        ranges = ", ".join(f"R{1000 + 1000 * number}..R{1999 + 1000 * number}" for number in range(60))
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n", tasks=f"| T01 | none | x | A1: R1, {ranges} |\n")
        rules = [rule for _, rule, _ in findings_of(self.check())]
        self.assertEqual(50, rules.count("task_cites_unknown_requirement"))
        self.assertEqual(1, rules.count("findings_truncated"))

    def test_more_than_ten_thousand_references_are_reported_and_coverage_is_not_computed(self):
        cells = ", ".join(["R1"] * 10001)
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n- R2 b\n", tasks=f"| T01 | none | x | A1: {cells} |\n")
        self.assertEqual([("0.0.1", "reference_limit_exceeded", "error")], findings_of(self.check()))

    def test_a_special_file_where_a_milestone_file_belongs_is_not_opened(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("named pipes are not available on this host")
        add_milestone(self.root, "0.0.1", spec=None)
        os.mkfifo(self.root / MILESTONES / "v0.0.1" / "spec.md")
        self.assertIn(("0.0.1", "file_unreadable", "error"), findings_of(self.check()))

    def test_a_path_that_is_not_a_regular_file_is_not_opened(self):
        add_milestone(self.root, "0.0.1")
        real = Path.is_file

        def is_file(path):
            return False if path.name == "spec.md" else real(path)

        with mock.patch.object(Path, "is_file", is_file):
            self.assertIn(("0.0.1", "file_unreadable", "error"), findings_of(self.check()))

    def test_a_milestone_file_that_resolves_outside_the_root_is_not_read(self):
        add_milestone(self.root, "0.0.1")
        outside = self.parent / "outside.md"
        outside.write_text(SPEC, encoding="utf-8")
        real = Path.resolve

        def resolve(path, *arguments, **keywords):
            return outside if path.name == "spec.md" else real(path, *arguments, **keywords)

        with mock.patch.object(Path, "resolve", resolve):
            report = self.check()
        self.assertIn(("0.0.1", "link_escapes_root", "error"), findings_of(report))

    def test_an_indented_bullet_is_not_a_requirement(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n  - R1 test case under it\n", tasks="| T01 | none | x | A1: R1 |\n")
        self.assertEqual([], findings_of(self.check()))

    def test_a_legacy_spec_without_requirement_items_is_a_warning_and_no_coverage_rules_apply(self):
        add_milestone(self.root, "0.0.1", spec="# v0.0.1 — legacy\n\n| R1 | table |\n", tasks="| T01 | none | x | A1: R9 |\n")
        report = self.check()
        self.assertEqual([("0.0.1", "requirements_not_found", "warning")], findings_of(report))
        self.assertEqual("pass", report["status"])

    def test_a_requirement_that_no_row_cites_is_unclaimed_and_named(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n- R2 b\n", tasks="| T01 | none | x | A1: R1 |\n")
        report = self.check()
        self.assertEqual([("0.0.1", "requirement_unclaimed", "error")], findings_of(report))
        self.assertIn("R2", report["milestones"][0]["findings"][0]["detail"])
        self.assertEqual(1, run_main("check", "--root", str(self.root))[0])

    def test_a_row_that_cites_an_undefined_requirement_is_an_error_at_its_line(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n", tasks="| T01 | none | x | A1: R1, R9 |\n")
        report = self.check()
        self.assertEqual([("0.0.1", "task_cites_unknown_requirement", "error")], findings_of(report))
        self.assertEqual(1, report["milestones"][0]["findings"][0]["line"])

    def test_the_range_forms_are_expanded_and_an_inverted_range_is_refused(self):
        spec = "## Requirements\n\n- R1 a\n- R2 b\n- R3 c\n- R4 d\n- R5 e\n"
        for row in ("| T01 | none | x | A1: R1–R5 |\n", "| T01 | none | x | A1: R1-R5 |\n", "| T01 | none | x | A1: R1..R5 |\n", "| T01 | none | x | A1: R1–5 |\n"):
            with self.subTest(row=row):
                add_milestone(self.root, "0.0.1", spec=spec, tasks=row)
                self.assertEqual([], findings_of(self.check()))
        add_milestone(self.root, "0.0.1", spec=spec, tasks="| T01 | none | x | A1: R3–R1 |\n")
        self.assertIn(("0.0.1", "reference_range_invalid", "error"), findings_of(self.check()))

    def test_a_range_of_one_thousand_ids_passes_and_one_of_one_thousand_and_one_is_refused(self):
        spec = "## Requirements\n\n" + "".join(f"- R{number} item\n" for number in range(1, 1001))
        add_milestone(self.root, "0.0.1", spec=spec, tasks="| T01 | none | x | A1: R1–R1000 |\n")
        self.assertEqual([], findings_of(self.check()))
        add_milestone(self.root, "0.0.1", spec=spec, tasks="| T01 | none | x | A1: R1–R1001 |\n")
        self.assertIn(("0.0.1", "reference_range_invalid", "error"), findings_of(self.check()))

    def test_references_outside_table_rows_and_fenced_blocks_do_not_count(self):
        tasks = "R2 is discussed here.\n\n```\n| T01 | none | x | A1: R2 |\n```\n\n| T01 | none | x | A1: R1 |\n"
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n- R2 b\n", tasks=tasks)
        self.assertEqual([("0.0.1", "requirement_unclaimed", "error")], findings_of(self.check()))

    def test_a_cell_that_cites_the_same_id_twice_is_fine(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n", tasks="| T01 | none | x | A1: R1 and R1 again |\n")
        self.assertEqual([], findings_of(self.check()))

    def test_a_tasks_file_without_table_rows_is_a_warning_and_no_coverage_rules_apply(self):
        add_milestone(self.root, "0.0.1", spec="## Requirements\n\n- R1 a\n", tasks="No table here, R9 only.\n")
        self.assertEqual([("0.0.1", "tasks_not_found", "warning")], findings_of(self.check()))

    def test_findings_are_sorted_by_version_then_severity_rule_and_line(self):
        add_milestone(self.root, "0.0.10", decisions=None)
        add_milestone(self.root, "0.0.9", spec="## Requirements\n\n- R1 a\n- R2 b\n", tasks="| T01 | none | x | A1: R1, R9 |\n", decisions=None)
        report = self.check()
        self.assertEqual(["0.0.9", "0.0.10"], [entry["version"] for entry in report["milestones"]])
        self.assertEqual(
            ["requirement_unclaimed", "task_cites_unknown_requirement", "decisions_missing"],
            [finding["rule"] for finding in report["milestones"][0]["findings"]],
        )


class SelectionTests(TempCase):
    def setUp(self):
        super().setUp()
        for version in ("0.0.1", "0.0.9", "0.0.10", "0.0.24"):
            add_milestone(self.root, version)

    def test_from_and_named_versions_select_milestones_in_version_order(self):
        self.assertEqual(["0.0.9", "0.0.10", "0.0.24"], [entry["version"] for entry in self.check(start="0.0.9")["milestones"]])
        self.assertEqual(["0.0.1", "0.0.10"], [entry["version"] for entry in self.check("0.0.10", "0.0.1")["milestones"]])

    def test_a_version_argument_outside_the_scheme_is_invalid_input(self):
        with self.assertRaises(ValueError):
            self.check("v0.0.1")
        with self.assertRaises(ValueError):
            self.check(start="1.0.0")
        self.assertEqual(2, run_main("check", "--root", str(self.root), "--from", "v0.0.1")[0])

    def test_a_named_version_without_a_folder_is_invalid_input_when_the_directory_exists(self):
        with self.assertRaises(ValueError):
            self.check("0.0.2")
        self.assertEqual(2, run_main("check", "--root", str(self.root), "0.0.2")[0])

    def test_exit_codes_follow_the_severity_and_the_check_prints_json(self):
        status, output, error = run_main("check", "--root", str(self.root), "--from", "0.0.9")
        self.assertEqual((0, ""), (status, error))
        report = json.loads(output)
        self.assertEqual({"milestones", "schema_version", "status"}, set(report))
        self.assertEqual(("pass", 1), (report["status"], report["schema_version"]))
        add_milestone(self.root, "0.0.30", spec="## Requirements\n\n- R1 a\n- R2 b\n", tasks="| T01 | none | x | A1: R1 |\n")
        self.assertEqual(1, run_main("check", "--root", str(self.root), "--from", "0.0.9")[0])

    def test_folders_with_names_that_are_not_versions_are_reported_even_with_a_filter(self):
        (self.root / MILESTONES / "notes").mkdir()
        self.assertIn("notes", [entry["version"] for entry in self.check(start="0.0.9")["milestones"]])


class CliTests(TempCase):
    def test_the_milestone_command_runs_the_same_code_and_exit_codes(self):
        status, output, error = run_cli("milestone", "new", "--root", str(self.root), "--title", "Sample")
        self.assertEqual((0, ""), (status, error))
        self.assertEqual("0.0.1", json.loads(output)["version"])
        status, output, _ = run_cli("milestone", "check", "--root", str(self.root), "--from", "0.0.1")
        self.assertEqual((0, "pass"), (status, json.loads(output)["status"]))
        self.assertEqual(2, run_cli("milestone", "check", "--root", str(self.parent / "absent"))[0])
        write_manifests(self.root, "1.0.0")
        self.assertEqual(1, run_cli("milestone", "new", "--root", str(self.root))[0])


class ExitCodeTests(TempCase):
    def test_a_file_operation_error_is_invalid_input(self):
        with mock.patch.object(milestones, "check_milestones", side_effect=OSError):
            self.assertEqual(2, run_main("check", "--root", str(self.root))[0])
        with mock.patch.object(milestones, "new_milestone", side_effect=OSError):
            self.assertEqual(2, run_main("new", "--root", str(self.root))[0])

    def test_a_second_new_for_the_same_manifest_version_names_the_existing_folder(self):
        write_manifests(self.root, "0.0.4")
        self.assertEqual(0, run_main("new", "--root", str(self.root))[0])
        status, output, error = run_main("new", "--root", str(self.root))
        self.assertEqual((1, ""), (status, output))
        self.assertIn("0.0.5 already exists", error)


class StepTests(TempCase):
    def test_the_milestones_step_checks_from_v0_0_9(self):
        make_checkout(self.root)
        add_milestone(self.root, "0.0.9")
        commands = []
        real = subprocess.run

        def spy(command, **keywords):
            commands.append(command)
            return real(command, **keywords)

        with mock.patch("inonu_harness.cli.subprocess.run", spy):
            run_cli("check", "--root", str(self.root))
        milestone = [command for command in commands if "milestone" in command]
        self.assertEqual(["milestone", "check", "--from", "0.0.9"], milestone[0][-4:])

    def test_a_symlink_committed_under_the_milestones_folder_fails_the_step_for_ref(self):
        make_checkout(self.root)
        add_milestone(self.root, "0.0.9", tasks=None)
        write(self.root, f"{MILESTONES}/v0.0.9/tasks-real.md", TASKS)
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        blob = subprocess.run(
            ["git", "-C", str(self.root), "hash-object", "-w", "--stdin"], input=b"tasks-real.md", capture_output=True, check=True,
        ).stdout.decode("ascii").strip()
        git(self.root, "update-index", "--add", "--cacheinfo", f"120000,{blob},{MILESTONES}/v0.0.9/tasks.md")
        git(self.root, "commit", "-q", "-m", "a milestone file that is a link")
        status, output, error = run_cli("check", "--root", str(self.root), "--ref", "HEAD")
        self.assertEqual(1, status, error)
        self.assertIn(("milestones", 1), steps_of(output))
        self.assertIn("symbolic link", error)

    def test_the_milestones_step_is_present_only_with_the_milestones_directory(self):
        make_checkout(self.root)
        status, output, error = run_cli("check", "--root", str(self.root))
        self.assertEqual(0, status, error)
        self.assertEqual([("compile", 0), ("versions", 0), ("tests", 0)], steps_of(output))
        add_milestone(self.root, "0.0.9")
        status, output, error = run_cli("check", "--root", str(self.root))
        self.assertEqual(0, status, error)
        self.assertEqual([("compile", 0), ("versions", 0), ("milestones", 0), ("tests", 0)], steps_of(output))

    def test_the_milestones_step_fails_on_a_milestone_with_an_unclaimed_requirement(self):
        make_checkout(self.root)
        add_milestone(self.root, "0.0.9", tasks="| T01 | none | x | A1: R1 |\n")
        status, output, _ = run_cli("check", "--root", str(self.root))
        self.assertEqual(1, status)
        self.assertEqual([("compile", 0), ("versions", 0), ("milestones", 1), ("tests", 0)], steps_of(output))

    def test_the_ref_check_runs_the_milestones_step_and_fails_a_committed_unclaimed_requirement(self):
        make_checkout(self.root)
        add_milestone(self.root, "0.0.9", tasks="| T01 | none | x | A1: R1 |\n")
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "unclaimed requirement")
        status, output, error = run_cli("check", "--root", str(self.root), "--ref", "HEAD")
        self.assertEqual(1, status, error)
        self.assertEqual(
            [("compile", 0), ("versions", 0), ("milestones", 1), ("tests", 0), ("runner", 0)],
            steps_of(output),
        )


class RepositoryTests(unittest.TestCase):
    def test_this_repository_passes_its_milestone_check_from_v0_0_9(self):
        report = check_milestones(REPO_ROOT, MILESTONES, start="0.0.9")
        self.assertEqual("pass", report["status"], findings_of(report))
        self.assertEqual("0.0.9", report["milestones"][0]["version"])
        self.assertGreaterEqual(len(report["milestones"]), 16)

    def test_stated_versions_returns_the_problems_and_the_statements_in_source_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifests(root, "0.0.24")
            self.assertEqual(([], [(INIT, "0.0.24"), (PYPROJECT, "0.0.24"), (PLUGIN, "0.0.24")]), stated_versions(root))
            write(root, PLUGIN, json.dumps({"name": "x", "version": "0.0.25"}))
            problems, stated = stated_versions(root)
            self.assertEqual([f"{PLUGIN} has version 0.0.25 but {INIT} has version 0.0.24"], problems)
            self.assertEqual(3, len(stated))
            with self.assertRaises(ValueError):
                stated_versions(root / "absent")


if __name__ == "__main__":
    unittest.main()
