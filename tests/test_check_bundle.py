import importlib
import json
import shutil
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from inonu_harness import __version__
from inonu_harness.cli import main as cli_main


REPO_ROOT = Path(__file__).resolve().parents[1]
PASSING_TEST = "import unittest\n\n\nclass SampleTests(unittest.TestCase):\n    def test_passes(self):\n        self.assertTrue(True)\n"
FAILING_TEST = PASSING_TEST.replace("assertTrue(True)", "assertTrue(False)")


def make_root(directory: Path, test_source: str = PASSING_TEST) -> Path:
    (directory / "tests").mkdir(parents=True)
    (directory / "tests" / "test_sample.py").write_text(test_source, encoding="utf-8")
    # The versions step runs `python -m inonu_harness.versions` here; the module alone is enough, with no version statement.
    (directory / "inonu_harness").mkdir()
    shutil.copy(REPO_ROOT / "inonu_harness" / "versions.py", directory / "inonu_harness" / "versions.py")
    return directory


def run_cli(*arguments: str) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = cli_main(list(arguments))
    return status, stdout.getvalue(), stderr.getvalue()


def snapshot(home: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(home).as_posix(): None if path.is_dir() else path.read_bytes()
        for path in home.rglob("*")
    }


def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    return {key.strip(): value.strip() for key, _, value in (line.partition(":") for line in lines[1:end])}


class CheckTests(unittest.TestCase):
    def test_passing_root_reports_passed_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            status, output, _ = run_cli("check", "--root", str(root))
        self.assertEqual(0, status)
        report = json.loads(output)
        self.assertTrue(report["passed"])
        self.assertEqual(1, report["schema_version"])
        self.assertEqual(
            [("compile", 0), ("versions", 0), ("tests", 0)], [(s["name"], s["exit_code"]) for s in report["steps"]],
        )

    def test_failing_test_exits_one(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), FAILING_TEST)
            status, output, _ = run_cli("check", "--root", str(root))
        self.assertEqual(1, status)
        report = json.loads(output)
        self.assertFalse(report["passed"])
        self.assertNotEqual(0, dict((s["name"], s["exit_code"]) for s in report["steps"])["tests"])

    def test_syntax_error_fails_compile_but_still_runs_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            (root / "inonu_harness" / "broken.py").write_text("def broken(:\n", encoding="utf-8")
            status, output, _ = run_cli("check", "--root", str(root))
        self.assertEqual(1, status)
        steps = {s["name"]: s["exit_code"] for s in json.loads(output)["steps"]}
        self.assertNotEqual(0, steps["compile"])
        self.assertEqual(0, steps["tests"])

    def test_root_without_tests_directory_is_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inonu_harness").mkdir()
            status, output, error = run_cli("check", "--root", str(root))
        self.assertEqual(2, status)
        self.assertEqual("", output)
        self.assertIn("tests directory", error)


class BundlePlanTests(unittest.TestCase):
    def test_plan_writes_nothing_and_applies_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            (home / ".claude").mkdir(parents=True)
            (home / ".claude" / "settings.json").write_text('{"theme": "dark"}', encoding="utf-8")
            before = snapshot(home)
            status, output, error = run_cli("bundle", "plan", "--home", str(home))
            after = snapshot(home)
        self.assertEqual(0, status, error)
        self.assertEqual(before, after)
        plan = json.loads(output)
        self.assertEqual(__version__, plan["version"])
        self.assertEqual({"skill", "worker-agent", "stop-hook", "mcp"}, {item["kind"] for item in plan["items"]})
        for item in plan["items"]:
            if item["kind"] != "skill":
                self.assertFalse(item["applied"], item)
        self.assertNotIn(str(home), output)
        self.assertNotIn(str(Path.home()), output)
        self.assertNotIn(str(REPO_ROOT), output)

    def test_codex_only_plan_has_no_claude_only_items(self):
        with tempfile.TemporaryDirectory() as directory:
            status, output, error = run_cli("bundle", "plan", "--host", "codex", "--home", directory)
        self.assertEqual(0, status, error)
        kinds = {item["kind"] for item in json.loads(output)["items"]}
        self.assertNotIn("worker-agent", kinds)
        self.assertNotIn("stop-hook", kinds)
        self.assertIn("skill", kinds)

    def test_stop_hook_snippet_runs_hook_stop_through_runner_with_host_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            status, output, _ = run_cli("bundle", "plan", "--host", "claude", "--home", directory)
        self.assertEqual(0, status)
        hook = next(item for item in json.loads(output)["items"] if item["kind"] == "stop-hook")
        entry = hook["snippet"]["hooks"]["Stop"][0]["hooks"][0]
        self.assertEqual("python <checkout>/scripts/inonu.py hook stop", entry["command"])
        self.assertEqual(630, entry["timeout"])
        self.assertIn("trusts", hook["note"])
        self.assertTrue(hook["requires_owner_authorization"])


class PackagingTests(unittest.TestCase):
    def test_worker_agent_frontmatter_uses_haiku(self):
        values = frontmatter((REPO_ROOT / "agents" / "inonu-worker.md").read_text(encoding="utf-8"))
        self.assertEqual("inonu-worker", values["name"])
        self.assertTrue(values["description"])
        self.assertEqual("haiku", values["model"])

    def test_console_script_target_is_callable(self):
        project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        module_name, _, attribute = project["scripts"]["inonu"].partition(":")
        function = getattr(importlib.import_module(module_name), attribute)
        self.assertTrue(callable(function))
        self.assertIs(cli_main, function)
        self.assertEqual(__version__, project["version"])


if __name__ == "__main__":
    unittest.main()
