import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from inonu_harness.cli import _export_tree, _exportable_path, _git_bytes, main as cli_main


IDENTITY = ("-c", "user.email=t@example.test", "-c", "user.name=t")
PASSING_TEST = "import unittest\n\n\nclass SampleTests(unittest.TestCase):\n    def test_passes(self):\n        self.assertTrue(True)\n"
FAILING_TEST = PASSING_TEST.replace("assertTrue(True)", "assertTrue(False)")
NEEDS_EXTRA = PASSING_TEST.replace("import unittest\n", "import unittest\n\nfrom inonu_harness import extra\n").replace(
    "assertTrue(True)", "assertTrue(extra.VALUE)"
)
RUNNER = 'print("inonu-harness test")\n'


def run_cli(*arguments: str) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = cli_main(list(arguments))
    return status, stdout.getvalue(), stderr.getvalue()


def git(repo: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(repo), *IDENTITY, *arguments], check=True, stdin=subprocess.DEVNULL, capture_output=True)


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def write_files(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def project(test_source: str = PASSING_TEST) -> dict[str, str]:
    """The smallest layout that `check` accepts: one test, the runner script and the package."""
    return {"tests/test_ok.py": test_source, "scripts/inonu.py": RUNNER, "inonu_harness/__init__.py": ""}


def steps_of(output: str) -> dict[str, int]:
    return {step["name"]: step["exit_code"] for step in json.loads(output)["steps"]}


class RepoCase(unittest.TestCase):
    """A temporary git repository holding one complete commit; it defines no tests of its own."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        write_files(self.repo, project())
        commit_all(self.repo, "complete project")

    def check_ref(self, ref="HEAD", root=None):
        return run_cli("check", "--root", str(root or self.repo), "--ref", ref)


class CheckRefTests(RepoCase):
    def test_complete_commit_passes_all_three_steps(self):
        status, output, error = self.check_ref()
        self.assertEqual(0, status, error)
        report = json.loads(output)
        self.assertTrue(report["passed"])
        self.assertEqual("HEAD", report["ref"])
        self.assertEqual(
            [("compile", 0), ("tests", 0), ("runner", 0)],
            [(step["name"], step["exit_code"]) for step in report["steps"]],
        )

    def test_module_that_was_never_added_fails_the_commit_while_the_working_tree_passes(self):
        write_files(self.repo, {"tests/test_ok.py": NEEDS_EXTRA})
        commit_all(self.repo, "test imports a module that is not committed")
        write_files(self.repo, {"inonu_harness/extra.py": "VALUE = True\n"})
        working_status, _, working_error = run_cli("check", "--root", str(self.repo))
        ref_status, ref_output, _ = self.check_ref()
        self.assertEqual(0, working_status, working_error)
        self.assertEqual(1, ref_status)
        self.assertNotEqual(0, steps_of(ref_output)["tests"])

    def test_uncommitted_edit_does_not_change_the_result_for_head(self):
        write_files(self.repo, {"tests/test_ok.py": FAILING_TEST})
        working_status, _, _ = run_cli("check", "--root", str(self.repo))
        ref_status, _, error = self.check_ref()
        self.assertEqual(1, working_status)
        self.assertEqual(0, ref_status, error)

    def test_committed_broken_test_fails_even_after_the_working_tree_is_fixed(self):
        write_files(self.repo, {"tests/test_ok.py": FAILING_TEST})
        commit_all(self.repo, "broken test")
        write_files(self.repo, {"tests/test_ok.py": PASSING_TEST})
        ref_status, ref_output, _ = self.check_ref()
        working_status, _, working_error = run_cli("check", "--root", str(self.repo))
        self.assertEqual(1, ref_status)
        self.assertNotEqual(0, steps_of(ref_output)["tests"])
        self.assertEqual(0, working_status, working_error)

    def test_invalid_input_exits_two_with_a_generic_message(self):
        plain = self.base / "plain"
        write_files(plain, project())
        no_tests = self.base / "no_tests"
        no_tests.mkdir()
        git(no_tests, "init", "-q")
        write_files(no_tests, {"inonu_harness/__init__.py": ""})
        commit_all(no_tests, "no tests directory")
        cases = (
            ("ref that does not resolve", self.repo, "refs/heads/missing", "ref"),
            ("root that is not a repository", plain, "HEAD", "git repository"),
            ("commit without tests", no_tests, "HEAD", "tests directory"),
        )
        for label, root, ref, expected in cases:
            with self.subTest(label):
                status, output, error = self.check_ref(ref, root)
                self.assertEqual(2, status)
                self.assertEqual("", output)
                self.assertIn(expected, error)
                self.assertNotIn(str(self.base), error)

    def test_temporary_export_is_removed_after_every_outcome(self):
        scratch = self.base / "scratch"
        scratch.mkdir()
        saved, tempfile.tempdir = tempfile.tempdir, str(scratch)
        try:
            passed = self.check_ref()[0]
            write_files(self.repo, {"tests/test_ok.py": FAILING_TEST})
            commit_all(self.repo, "broken test")
            failed = self.check_ref()[0]
        finally:
            tempfile.tempdir = saved
        self.assertEqual((0, 1), (passed, failed))
        self.assertEqual([], list(scratch.iterdir()))

    def test_output_without_the_flag_has_neither_ref_nor_runner(self):
        status, output, error = run_cli("check", "--root", str(self.repo))
        self.assertEqual(0, status, error)
        report = json.loads(output)
        self.assertNotIn("ref", report)
        self.assertEqual(["compile", "tests"], [step["name"] for step in report["steps"]])

    def test_subdirectory_root_checks_its_own_tree_at_the_commit(self):
        write_files(self.repo / "sub", project(FAILING_TEST))
        commit_all(self.repo, "failing project below the top")
        status, output, error = run_cli("check", "--root", str(self.repo / "sub"), "--ref", "HEAD")
        top_status, _, _ = self.check_ref()
        self.assertEqual(1, status, error)
        self.assertEqual("HEAD", json.loads(output)["ref"])
        self.assertEqual(0, top_status)


class ExportFidelityTests(RepoCase):
    """The export must be the commit's own bytes: attributes and line-ending settings must not change it."""

    def test_a_committed_failing_test_marked_export_ignore_is_still_checked(self):
        write_files(self.repo, {"tests/test_broken.py": FAILING_TEST, ".gitattributes": "tests/test_broken.py export-ignore\n"})
        commit_all(self.repo, "broken test hidden from git archive")
        working_status, _, _ = run_cli("check", "--root", str(self.repo))
        ref_status, ref_output, _ = self.check_ref()
        self.assertEqual(1, working_status)
        self.assertEqual(1, ref_status, "export-ignore must not hide a committed file")
        self.assertNotEqual(0, steps_of(ref_output)["tests"])

    def test_export_subst_placeholders_are_not_expanded(self):
        probe = PASSING_TEST.replace(
            "assertTrue(True)", 'assertEqual("$Format:%H$", "$" + "Format:%H$")'
        )
        write_files(self.repo, {"tests/test_subst.py": probe, ".gitattributes": "tests/test_subst.py export-subst\n"})
        commit_all(self.repo, "export-subst probe")
        status, _, error = self.check_ref()
        self.assertEqual(0, status, error)

    def test_line_endings_are_the_committed_ones_even_with_autocrlf(self):
        git(self.repo, "config", "core.autocrlf", "true")
        (self.repo / "scripts" / "eol_probe.txt").write_bytes(b"one\ntwo\n")
        commit_all(self.repo, "eol probe")
        committed = subprocess.run(
            ["git", "-C", str(self.repo), "show", "HEAD:scripts/eol_probe.txt"], capture_output=True, check=True
        ).stdout
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch) / "tree"
            _export_tree(self.repo, "HEAD", target)
            exported = (target / "scripts" / "eol_probe.txt").read_bytes()
        self.assertEqual(committed, exported)

    def test_names_with_spaces_and_non_ascii_characters_are_exported(self):
        source = PASSING_TEST.replace("SampleTests", "Spaced")
        write_files(self.repo, {"tests/test spaced ção.py": source})
        commit_all(self.repo, "awkward file name")
        status, output, error = self.check_ref()
        self.assertEqual(0, status, error)
        self.assertEqual(0, steps_of(output)["tests"])

    def test_unsafe_committed_paths_are_refused(self):
        for bad in ("../escape.py", "/absolute.py", "a/../b.py", "a//b.py", "./x.py", ".git/config", "C:evil.py", "a\\b.py", ""):
            with self.subTest(path=bad), self.assertRaises(ValueError):
                _exportable_path(bad)
        for good in ("tests/test_ok.py", "docs/a b.md", "módulo.py"):
            self.assertEqual(good, _exportable_path(good))

    def test_a_ref_name_outside_the_stdout_code_page_still_exits_zero(self):
        git(self.repo, "branch", "日本")
        status, output, error = self.check_ref("日本")
        self.assertEqual(0, status, error)
        output.encode("ascii")  # the report is ASCII-escaped
        self.assertEqual("日本", json.loads(output)["ref"])


class ExportRobustnessTests(RepoCase):
    def test_a_submodule_gitlink_is_skipped_not_exported(self):
        git(self.repo, "update-index", "--add", "--cacheinfo", "160000,1111111111111111111111111111111111111111,vendor/sub")
        git(self.repo, "commit", "-q", "-m", "gitlink")
        status, output, error = self.check_ref()
        self.assertEqual(0, status, error)
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch) / "tree"
            _export_tree(self.repo, "HEAD", target)
            self.assertFalse((target / "vendor").exists())

    def test_corrupt_cat_file_output_is_refused(self):
        nul, tab, newline = bytes([0]), bytes([9]), bytes([10])
        sha = b"a" * 40
        one_entry = b"100644 blob " + sha + tab + b"a.txt" + nul  # a single file, so only the header check can fail
        for name, reply in (
            ("wrong sha", b"0" * 40 + b" blob 3" + newline + b"abc" + newline),
            ("wrong type", sha + b" tree 3" + newline + b"abc" + newline),
            ("truncated", b""),
            ("missing object", sha + b" missing" + newline),
        ):
            def fake(root, *arguments, data=None, _reply=reply):
                return one_entry if arguments[0] == "ls-tree" else _reply

            with self.subTest(reply=name), patch("inonu_harness.cli._git_bytes", fake), tempfile.TemporaryDirectory() as scratch:
                with self.assertRaises(ValueError):
                    _export_tree(self.repo, "HEAD", Path(scratch) / "tree")


class ExportCleanupAndGitFailureTests(RepoCase):
    def scratch_listing(self):
        return sorted(path.name for path in self.scratch.iterdir())

    def setUp(self):
        super().setUp()
        self.scratch = self.base / "scratch"
        self.scratch.mkdir()
        patcher = patch("tempfile.tempdir", str(self.scratch))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_export_is_removed_after_every_outcome(self):
        before_entries = sorted(path.name for path in self.repo.iterdir())
        no_tests = self.base / "no-tests"
        no_tests.mkdir()
        git(no_tests, "init", "-q")
        write_files(no_tests, {"scripts/inonu.py": RUNNER})
        commit_all(no_tests, "no tests directory")
        outcomes = (
            (0, self.check_ref()),
            (2, self.check_ref("does-not-exist")),
            (2, self.check_ref(root=no_tests)),
        )
        for expected, (status, _, _) in outcomes:
            self.assertEqual(expected, status)
        self.assertEqual([], self.scratch_listing())
        self.assertEqual(before_entries, sorted(path.name for path in self.repo.iterdir()))

    def test_a_git_timeout_is_reported_without_a_path(self):
        real_run = subprocess.run

        def timing_out(command, *args, **kwargs):
            if command[:1] == ["git"]:
                raise subprocess.TimeoutExpired(command, 1)
            return real_run(command, *args, **kwargs)

        with patch("inonu_harness.cli.subprocess.run", timing_out):
            status, output, error = self.check_ref()
        self.assertEqual((2, ""), (status, output))
        self.assertIn("git is unavailable or did not finish in time", error)
        self.assertNotIn(str(self.base), error)

    def test_a_missing_git_executable_is_reported_as_invalid_input(self):
        with patch.dict(os.environ, {"PATH": str(self.base / "empty")}):
            status, output, error = self.check_ref()
        self.assertEqual((2, ""), (status, output))
        self.assertIn("git is unavailable", error)

    def test_a_ref_that_looks_like_an_option_is_refused_before_any_export(self):
        for ref in ("-h", "--output=leak.zip", "--all"):
            with self.subTest(ref=ref):
                status, output, _ = run_cli("check", "--root", str(self.repo), f"--ref={ref}")
                self.assertEqual((2, ""), (status, output))
        self.assertEqual([], self.scratch_listing())
        self.assertFalse((self.repo / "leak.zip").exists())


if __name__ == "__main__":
    unittest.main()
