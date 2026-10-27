import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from inonu_harness import __version__
from inonu_harness.bundle import REPOSITORY, WORKER_SOURCE
from inonu_harness.cli import main as cli_main
from inonu_harness.host_profiles import main as profiles_main


SECRET = "sk-test-" + "SECRET-VALUE-12345"  # assembled, so no credential-looking literal is committed


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


def states(report: dict) -> dict[tuple[str, str, str], str]:
    return {
        (item["kind"], item["host"], item.get("id", "")): item["state"]
        for item in report["items"]
    }


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def install_profile(home: Path) -> None:
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        assert profiles_main(["--home", str(home), "--apply"]) == 0
    worker = home / ".claude" / "agents" / "inonu-worker.md"
    worker.parent.mkdir(parents=True, exist_ok=True)
    worker.write_bytes((REPOSITORY / WORKER_SOURCE).read_bytes())
    write(
        home / ".claude" / "settings.json",
        json.dumps({"env": {"TOKEN": SECRET}, "hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "python '/x/scripts/inonu.py' hook stop", "timeout": 630},
        ]}]}}),
    )
    write(
        home / ".claude.json",
        json.dumps({"mcpServers": {"codegraph": {"env": {"KEY": SECRET}}, "headroom": {}}}),
    )
    write(
        home / ".codex" / "config.toml",
        f'[mcp_servers.codegraph]\ncommand = "x"\nenv = {{ KEY = "{SECRET}" }}\n',
    )


class BundleStatusTests(unittest.TestCase):
    def assert_no_home(self, home: Path, text: str) -> None:
        for form in (str(home), json.dumps(str(home))[1:-1], home.as_posix()):
            self.assertNotIn(form, text)

    def test_deeply_nested_or_mistyped_configuration_reports_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            write(home / ".claude" / "settings.json", "[" * 100000)
            write(home / ".claude.json", json.dumps({"mcpServers": ["codegraph"]}))
            write(home / ".codex" / "config.toml", "mcp_servers = 1" + chr(10))
            status, output, _ = run_cli("bundle", "status", "--home", str(home))
        self.assertEqual(0, status)
        found = states(json.loads(output))
        self.assertEqual("unknown", found[("stop-hook", "claude", "")])
        self.assertEqual("unknown", found[("mcp", "claude", "codegraph")])
        self.assertEqual("unknown", found[("mcp", "codex", "codegraph")])

    def test_outdated_skill_and_unrelated_stop_hook(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_profile(home)
            write(home / ".claude" / "settings.json",
                  json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo done"}]}]}}))
            skill = home / ".claude" / "skills" / "inonu-harness" / "SKILL.md"
            metadata = skill.parent / ".inonu-harness.json"
            value = json.loads(metadata.read_text(encoding="utf-8"))
            value["version"] = "0.0.1"
            metadata.write_text(json.dumps(value), encoding="utf-8")
            status, output, _ = run_cli("bundle", "status", "--host", "claude", "--home", str(home))
        self.assertEqual(0, status)
        found = states(json.loads(output))
        self.assertEqual("outdated", found[("skill", "claude", "")])
        self.assertEqual("absent", found[("stop-hook", "claude", "")])

    def test_stop_hook_is_present_for_the_current_and_the_legacy_command(self):
        for ending in ("hook stop", "check"):
            with self.subTest(ending=ending), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                write(home / ".claude" / "settings.json", json.dumps({"hooks": {"Stop": [{"hooks": [
                    {"type": "command", "command": f"python '/x/scripts/inonu.py' {ending}"},
                ]}]}}))
                status, output, _ = run_cli("bundle", "status", "--host", "claude", "--home", str(home))
                self.assertEqual(0, status)
                self.assertEqual("present", states(json.loads(output))[("stop-hook", "claude", "")])

    def test_empty_home_reports_everything_absent_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            before = snapshot(home)
            status, output, error = run_cli("bundle", "status", "--home", str(home))
            after = snapshot(home)
        self.assertEqual(0, status)
        self.assertEqual(before, after)
        self.assertEqual("", error)
        report = json.loads(output)
        self.assertEqual("status", report["mode"])
        self.assertEqual(__version__, report["version"])
        self.assertEqual(["codex", "claude"], report["hosts"])
        self.assertTrue(all(item["applied"] is False for item in report["items"]))
        self.assertNotIn("status", report["items"][0])
        self.assertEqual({"absent": len(report["items"])}, report["summary"])
        self.assertTrue(all(state == "absent" for state in states(report).values()))
        self.assert_no_home(home, output)

    def test_applied_profile_and_configuration_report_current_present_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_profile(home)
            before = snapshot(home)
            status, output, error = run_cli("bundle", "status", "--home", str(home))
            after = snapshot(home)
        self.assertEqual(0, status)
        self.assertEqual(before, after)
        self.assertEqual("", error)
        state = states(json.loads(output))
        self.assertEqual("current", state[("skill", "codex", "")])
        self.assertEqual("current", state[("skill", "claude", "")])
        self.assertEqual("current", state[("worker-agent", "claude", "")])
        self.assertEqual("present", state[("stop-hook", "claude", "")])
        self.assertEqual("configured", state[("mcp", "claude", "codegraph")])
        self.assertEqual("configured", state[("mcp", "claude", "headroom")])
        self.assertEqual("absent", state[("mcp", "claude", "sequential-thinking")])
        self.assertEqual("configured", state[("mcp", "codex", "codegraph")])
        self.assertEqual("absent", state[("mcp", "codex", "headroom")])

    def test_summary_counts_items_per_state_and_accessibility_stays_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_profile(home)
            status, output, _ = run_cli("bundle", "status", "--host", "claude", "--home", str(home))
        self.assertEqual(0, status)
        report = json.loads(output)
        self.assertEqual(sum(report["summary"].values()), len(report["items"]))
        self.assertEqual({"absent": 1, "configured": 2, "current": 2, "present": 1}, report["summary"])
        for item in report["items"]:
            if item["kind"] == "mcp":
                self.assertEqual("unknown", item["accessibility"])

    def test_malformed_configuration_reports_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            write(home / ".claude" / "settings.json", "{not json")
            write(home / ".claude.json", "{not json")
            write(home / ".codex" / "config.toml", "[mcp_servers\n")
            status, output, _ = run_cli("bundle", "status", "--home", str(home))
        self.assertEqual(0, status)
        state = states(json.loads(output))
        self.assertEqual("unknown", state[("stop-hook", "claude", "")])
        self.assertEqual("unknown", state[("mcp", "claude", "codegraph")])
        self.assertEqual("unknown", state[("mcp", "codex", "codegraph")])

    def test_modified_worker_agent_and_skill_are_reported_without_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_profile(home)
            write(home / ".claude" / "agents" / "inonu-worker.md", f"custom {SECRET}\n")
            (home / ".claude" / "skills" / "inonu-harness" / "SKILL.md").write_text(f"edited {SECRET}\n", encoding="utf-8")
            status, output, _ = run_cli("bundle", "status", "--host", "claude", "--home", str(home))
        self.assertEqual(0, status)
        state = states(json.loads(output))
        self.assertEqual("different", state[("worker-agent", "claude", "")])
        self.assertEqual("conflict", state[("skill", "claude", "")])
        self.assertNotIn(SECRET, output)
        self.assert_no_home(home, output)

    def test_status_output_never_contains_planted_secret_or_home_path(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_profile(home)
            _, output, error = run_cli("bundle", "status", "--home", str(home))
        self.assertNotIn(SECRET, output + error)
        self.assert_no_home(home, output + error)


if __name__ == "__main__":
    unittest.main()
