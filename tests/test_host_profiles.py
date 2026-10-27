import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from inonu_harness import __version__
from inonu_harness.cli import main as cli_main
from inonu_harness.host_profiles import main as profiles_main, render_runner_command


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "inonu.py"
INSTALLER = REPO_ROOT / "scripts" / "configure_hosts.py"


class HostProfileTests(unittest.TestCase):
    def run_installer(self, home: Path, *arguments: str) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = profiles_main(["--home", str(home), *arguments])
        return status, stdout.getvalue(), stderr.getvalue()

    def test_runner_exposes_cli_from_an_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(RUNNER), "--version"], cwd=directory,
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(f"inonu-harness {__version__}\n", result.stdout)

    def test_doctor_accepts_selected_project_root_and_preserves_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "selected project"
            project_config = project / ".codex" / "config.toml"
            project_config.parent.mkdir(parents=True)
            project_config.write_text('[mcp_servers]\nselected = {}\n', encoding="utf-8")
            stdout = StringIO()
            with (
                patch("inonu_harness.doctor.Path.home", return_value=home),
                patch("inonu_harness.doctor.shutil.which", return_value=None),
                redirect_stdout(stdout),
            ):
                self.assertEqual(0, cli_main(["doctor", "--project-root", str(project)]))
            report = json.loads(stdout.getvalue())
            self.assertEqual(1, report["schema_version"])
            self.assertEqual("configured", report["configurations"]["project"]["state"])
            self.assertEqual(["selected"], [item["name"] for item in report["mcps"]])
            self.assertNotIn(str(root), stdout.getvalue())

            stdout = StringIO()
            with (
                patch("inonu_harness.doctor.Path.home", return_value=home),
                patch("inonu_harness.doctor.shutil.which", return_value=None),
                redirect_stdout(stdout),
            ):
                self.assertEqual(0, cli_main(["doctor"]))
            default_report = json.loads(stdout.getvalue())
            self.assertEqual(set(report), set(default_report))
            self.assertEqual(1, default_report["schema_version"])

    def test_preview_is_default_and_does_not_write_any_target(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "private home"
            result = subprocess.run(
                [sys.executable, str(INSTALLER), "--home", str(home)],
                cwd=directory, capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            status = json.loads(result.stdout)
            self.assertEqual("preview", status["mode"])
            self.assertEqual(__version__, status["version"])
            self.assertEqual({"codex", "claude"}, set(status["hosts"]))
            self.assertFalse(home.exists())
            self.assertNotIn(str(home), result.stdout + result.stderr)

    def test_apply_and_repeat_are_idempotent_and_preserve_other_skills(self):
        with tempfile.TemporaryDirectory(prefix="host profiles ") as directory:
            home = Path(directory) / "home"
            unrelated = home / ".agents" / "skills" / "other-skill" / "SKILL.md"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("other skill", encoding="utf-8")
            status, output, error = self.run_installer(home, "--apply")
            self.assertEqual(0, status, error)
            self.assertNotIn(str(home), output + error)
            codex_skill = home / ".agents" / "skills" / "inonu-harness" / "SKILL.md"
            claude_skill = home / ".claude" / "skills" / "inonu-harness" / "SKILL.md"
            codex_before, claude_before = codex_skill.read_bytes(), claude_skill.read_bytes()
            codex_metadata = json.loads((codex_skill.parent / ".inonu-harness.json").read_text(encoding="utf-8"))
            self.assertEqual("inonu-harness.host-profile", codex_metadata["owner"])
            self.assertEqual(__version__, codex_metadata["version"])
            self.assertEqual(hashlib.sha256(codex_before).hexdigest(), codex_metadata["skill_sha256"])
            self.assertIn("& python " if os.name == "nt" else "python '", codex_before.decode("utf-8"))
            self.assertIn("python '", claude_before.decode("utf-8"))
            self.assertIn((REPO_ROOT / "docs" / "sdd-workflow.md").resolve().as_uri(), codex_before.decode("utf-8"))
            self.assertIn((REPO_ROOT / "docs" / "benchmark-plan.md").resolve().as_uri(), claude_before.decode("utf-8"))
            self.assertEqual("other skill", unrelated.read_text(encoding="utf-8"))

            status, output, error = self.run_installer(home, "--apply")
            self.assertEqual(0, status, error)
            result = json.loads(output)
            self.assertTrue(all(row["skill"] == "unchanged" for row in result["hosts"].values()))
            self.assertEqual(codex_before, codex_skill.read_bytes())
            self.assertEqual(claude_before, claude_skill.read_bytes())

    def test_custom_and_modified_skills_are_preserved_and_conflict_preflight_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex_skill = home / ".agents" / "skills" / "inonu-harness" / "SKILL.md"
            codex_skill.parent.mkdir(parents=True)
            codex_skill.write_text("custom skill", encoding="utf-8")
            status, output, error = self.run_installer(home, "--apply")
            self.assertEqual(2, status)
            self.assertIn('"codex"', output)
            self.assertIn("conflict", output)
            self.assertNotIn(str(home), output + error)
            self.assertEqual("custom skill", codex_skill.read_text(encoding="utf-8"))
            self.assertFalse((home / ".claude" / "skills" / "inonu-harness").exists())

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(0, self.run_installer(home, "--host", "codex", "--apply")[0])
            skill = home / ".agents" / "skills" / "inonu-harness" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\ncustom edit\n", encoding="utf-8")
            status, _, _ = self.run_installer(home, "--host", "codex", "--apply")
            self.assertEqual(2, status)
            self.assertTrue(skill.read_text(encoding="utf-8").endswith("custom edit\n"))

    def test_runner_commands_quote_spaces_and_apostrophes_for_each_shell(self):
        windows_runner = r"C:\Users\A B\O'Neil\scripts\inonu.py"
        posix_runner = "/home/A B/O'Neil/scripts/inonu.py"
        self.assertEqual(
            "& python 'C:\\Users\\A B\\O''Neil\\scripts\\inonu.py' doctor",
            render_runner_command(windows_runner, "codex", "doctor"),
        )
        self.assertEqual(
            "python 'C:/Users/A B/O'\\''Neil/scripts/inonu.py' doctor",
            render_runner_command(windows_runner, "claude", "doctor"),
        )
        self.assertEqual(
            "python '/home/A B/O'\\''Neil/scripts/inonu.py' doctor",
            render_runner_command(posix_runner, "claude", "doctor"),
        )
        self.assertEqual(
            "python '/home/A B/O'\\''Neil/scripts/inonu.py' doctor",
            render_runner_command(posix_runner, "codex", "doctor"),
        )

    def test_source_skill_has_native_frontmatter_and_required_workflows(self):
        source = (REPO_ROOT / "skills" / "inonu-harness" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(source.startswith("---\n"))
        self.assertIn("\nname: inonu-harness\n", source)
        self.assertIn("\ndescription:", source)
        for expected in (
            "doctor", "baseline", "decisions --db path create", "decisions --db path context", "decisions --db path packet",
            "sdd audit", "Constitution", "Convergence", "human",
        ):
            self.assertIn(expected.casefold(), source.casefold())
        self.assertIn("../../docs/sdd-workflow.md", source)
        self.assertIn("../../docs/benchmark-plan.md", source)

    def test_version_is_released_version(self):
        plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(__version__, plugin["version"])

    def test_host_selection_installs_only_the_requested_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            status, output, error = self.run_installer(home, "--host", "claude", "--apply")
            self.assertEqual(0, status, error)
            self.assertEqual({"claude"}, set(json.loads(output)["hosts"]))
            self.assertTrue((home / ".claude" / "skills" / "inonu-harness" / "SKILL.md").is_file())
            self.assertFalse((home / ".agents").exists())


if __name__ == "__main__":
    unittest.main()
