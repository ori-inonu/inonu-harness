import json
import os
import shutil
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from inonu_harness import bundle_apply, host_profiles
from inonu_harness.bundle import REPOSITORY
from inonu_harness.cli import main as cli_main


SECRET = "sk-test-" + "SECRET-VALUE-54321"  # assembled, so no credential-looking literal is committed
ALL_STUBS = {"codegraph": "codegraph.exe", "headroom": "headroom.exe", "npx": "npx.exe"}
CMD_STUBS = {"codegraph": "codegraph.cmd", "headroom": "headroom.cmd", "npx": "npx.cmd"}
LEDGER_KEYS = {
    "skill:claude:inonu-harness", "skill:codex:inonu-harness", "worker-agent:claude:inonu-worker",
    "stop-hook:claude:Stop", "mcp:claude:codegraph", "mcp:claude:headroom", "mcp:claude:sequential-thinking",
    "mcp:codex:codegraph", "mcp:codex:headroom", "mcp:codex:sequential-thinking",
}


def snapshot(home: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(home).as_posix(): None if path.is_dir() else path.read_bytes()
        for path in home.rglob("*")
    }


def states(report: dict) -> dict[tuple[str, str, str], str]:
    return {(item["kind"], item["host"], item.get("id", "")): item["result"] for item in report["items"]}


class BundleApplyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.stubs = self.root / "stubs"
        self.stubs.mkdir()
        for filename in (*ALL_STUBS.values(), *CMD_STUBS.values()):
            (self.stubs / filename).write_bytes(b"")

    def run_cli(self, *arguments, stubs=ALL_STUBS):
        def fake_which(name):
            return str(self.stubs / stubs[name]) if name in stubs else None

        stdout, stderr = StringIO(), StringIO()
        with patch("inonu_harness.bundle_apply._find_executable", side_effect=fake_which), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli_main(["bundle", *arguments, "--home", str(self.home)])
        return status, json.loads(stdout.getvalue()), stdout.getvalue() + stderr.getvalue()

    def write(self, relative, text):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read_json(self, relative):
        return json.loads((self.home / relative).read_text(encoding="utf-8"))

    def test_preview_writes_nothing(self):
        before = snapshot(self.home)
        status, report, _ = self.run_cli("apply", "--with-stop-hook")
        self.assertEqual((0, "preview"), (status, report["mode"]))
        self.assertEqual(before, snapshot(self.home))

    def test_apply_records_stable_ledger_keys(self):
        status, _, _ = self.run_cli("apply", "--with-stop-hook", "--apply")
        self.assertEqual(0, status)
        ledger = self.read_json(".inonu-harness/bundle-ledger.json")
        self.assertEqual(1, ledger["schema_version"])
        self.assertEqual(LEDGER_KEYS, set(ledger["items"]))

    def test_second_apply_is_unchanged(self):
        self.run_cli("apply", "--with-stop-hook", "--apply")
        status, report, _ = self.run_cli("apply", "--with-stop-hook", "--apply")
        self.assertEqual(0, status)
        self.assertEqual({"unchanged"}, {item["result"] for item in report["items"]})

    def test_apply_then_remove_restores_preexisting_configs(self):
        claude_original = {"numStartups": 3, "mcpServers": {"mine": {"command": "x"}}}
        codex_original = 'model = "gpt"\n'
        self.write(".claude.json", json.dumps(claude_original))
        self.write(".codex/config.toml", codex_original)
        status, _, _ = self.run_cli("apply", "--with-stop-hook", "--apply")
        self.assertEqual(0, status)
        self.assertEqual(
            {"mine", "codegraph", "headroom", "sequential-thinking"},
            set(self.read_json(".claude.json")["mcpServers"]),
        )
        status, report, _ = self.run_cli("remove", "--with-stop-hook", "--apply")
        self.assertEqual(0, status, report)
        self.assertEqual(claude_original, self.read_json(".claude.json"))
        self.assertEqual(codex_original, (self.home / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertFalse((self.home / ".claude" / "agents" / "inonu-worker.md").exists())
        self.assertFalse((self.home / ".claude" / "skills" / "inonu-harness").exists())
        self.assertFalse((self.home / ".claude" / "settings.json").exists())
        self.assertFalse((self.home / ".inonu-harness" / "bundle-ledger.json").exists())

    def test_fresh_home_round_trip_leaves_no_config_files(self):
        self.run_cli("apply", "--with-stop-hook", "--apply")
        status, report, _ = self.run_cli("remove", "--with-stop-hook", "--apply")
        self.assertEqual(0, status)
        self.assertEqual({"removed"}, set(states(report).values()))
        for name in (".claude.json", ".codex/config.toml", ".claude/settings.json", ".inonu-harness"):
            self.assertFalse((self.home / name).exists(), name)

    def test_user_modified_entry_conflicts_and_is_kept(self):
        self.run_cli("apply", "--apply")
        doc = self.read_json(".claude.json")
        doc["mcpServers"]["codegraph"]["command"] = "edited"
        (self.home / ".claude.json").write_text(json.dumps(doc), encoding="utf-8")
        before = snapshot(self.home)
        status, report, _ = self.run_cli("remove", "--apply")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("mcp", "claude", "codegraph")])
        self.assertEqual(before, snapshot(self.home))

    def test_existing_user_entry_is_never_overwritten(self):
        self.write(".claude.json", json.dumps({"mcpServers": {"codegraph": {"command": "mine"}}}))
        status, report, _ = self.run_cli("apply", "--apply")
        self.assertEqual(0, status)
        self.assertEqual("unchanged", states(report)[("mcp", "claude", "codegraph")])
        self.assertEqual({"command": "mine"}, self.read_json(".claude.json")["mcpServers"]["codegraph"])

    def test_missing_launcher_is_tool_missing_not_conflict(self):
        status, report, _ = self.run_cli("apply", "--apply", stubs={})
        self.assertEqual(0, status)
        mcp = [item["result"] for item in report["items"] if item["kind"] == "mcp"]
        self.assertEqual(["tool_missing"] * 6, mcp)
        self.assertFalse((self.home / ".claude.json").exists())

    def test_stop_hook_only_with_flag(self):
        status, report, _ = self.run_cli("apply", "--apply")
        self.assertEqual(0, status)
        self.assertEqual("not_selected", states(report)[("stop-hook", "claude", "Stop")])
        self.assertFalse((self.home / ".claude" / "settings.json").exists())
        status, report, _ = self.run_cli("apply", "--apply", "--with-stop-hook")
        self.assertEqual(0, status)
        self.assertEqual([self.stop_group()], self.read_json(".claude/settings.json")["hooks"]["Stop"])

    def stop_group(self, command=None):
        if command is None:
            command = bundle_apply._hook_command(REPOSITORY)
        return {"hooks": [{"type": "command", "command": command, "timeout": 630}]}

    def test_stop_hook_registers_hook_stop_with_the_host_timeout(self):
        self.assertEqual(0, self.run_cli("apply", "--host", "claude", "--apply", "--with-stop-hook")[0])
        group = self.read_json(".claude/settings.json")["hooks"]["Stop"][0]
        self.assertEqual(630, group["hooks"][0]["timeout"])
        self.assertTrue(group["hooks"][0]["command"].endswith("inonu.py' hook stop"), group)

    def test_only_the_stop_hook_item_carries_a_one_sentence_note_without_paths(self):
        status, report, text = self.run_cli("apply", "--with-stop-hook")
        self.assertEqual(0, status)
        notes = [item for item in report["items"] if "note" in item]
        self.assertEqual(["stop-hook"], [item["kind"] for item in notes])
        note = notes[0]["note"]
        self.assertEqual(1, note.count("."), note)
        self.assertTrue(note.endswith("."), note)
        self.assertNotRegex(note, r"[/\\:]")
        self.assertNotIn(str(self.home), text)

    def test_malformed_settings_conflicts_and_writes_nothing(self):
        self.write(".claude/settings.json", "{")
        before = snapshot(self.home)
        status, report, _ = self.run_cli("apply", "--apply", "--with-stop-hook")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("stop-hook", "claude", "Stop")])
        self.assertEqual(before, snapshot(self.home))

    def test_malformed_ledger_conflicts_and_writes_nothing(self):
        self.write(".inonu-harness/bundle-ledger.json", "{")
        before = snapshot(self.home)
        status, _, _ = self.run_cli("apply", "--apply")
        self.assertEqual(2, status)
        self.assertEqual(before, snapshot(self.home))

    def test_a_ledger_whose_schema_version_is_true_or_a_float_conflicts_and_writes_nothing(self):
        for literal in ("true", "1.0"):
            with self.subTest(schema_version=literal):
                self.write(".inonu-harness/bundle-ledger.json", '{"schema_version": ' + literal + ', "items": {}}')
                before = snapshot(self.home)
                status, _, _ = self.run_cli("apply", "--apply")
                self.assertEqual(2, status)
                self.assertEqual(before, snapshot(self.home))

    def test_change_between_preflight_and_write_conflicts(self):
        self.write(".claude.json", json.dumps({}))
        original_write = bundle_apply._Run.write

        def racing(run):
            (self.home / ".claude.json").write_text(json.dumps({"changed": True}), encoding="utf-8")
            return original_write(run)

        with patch.object(bundle_apply._Run, "write", racing):
            status, report, _ = self.run_cli("apply", "--apply")
        self.assertEqual(2, status)
        self.assertNotIn("installed", {item["result"] for item in report["items"]})
        self.assertEqual({"changed": True}, self.read_json(".claude.json"))
        self.assertFalse((self.home / ".inonu-harness").exists())
        self.assertFalse((self.home / ".claude" / "agents" / "inonu-worker.md").exists())

    def test_output_hides_home_path_and_secret_values(self):
        self.write(".claude.json", json.dumps({"mcpServers": {"other": {"env": {"KEY": SECRET}}}}))
        self.write(".codex/config.toml", f'[mcp_servers.other]\ncommand = "x"\nenv = {{ KEY = "{SECRET}" }}\n')
        self.write(".claude/settings.json", json.dumps({"env": {"TOKEN": SECRET}}))
        for arguments in (("apply", "--with-stop-hook"), ("apply", "--with-stop-hook", "--apply"),
                          ("remove", "--with-stop-hook", "--apply")):
            _, _, text = self.run_cli(*arguments)
            self.assertNotIn(SECRET, text)
            self.assertNotIn(str(self.home), text)
            self.assertNotIn(self.home.as_posix(), text)

    def test_windows_cmd_launchers_are_wrapped_and_toml_is_valid(self):
        status, _, _ = self.run_cli("apply", "--apply", stubs=CMD_STUBS)
        self.assertEqual(0, status)
        servers = self.read_json(".claude.json")["mcpServers"]
        self.assertEqual(bundle_apply._cmd_executable(), servers["codegraph"]["command"])
        self.assertNotEqual("cmd", servers["codegraph"]["command"])
        self.assertEqual(["/c", str(self.stubs / "codegraph.cmd"), "mcp", "serve", "--root", ".", "--stdio", "--no-warmup"],
                         servers["codegraph"]["args"])
        self.assertEqual(["/c", str(self.stubs / "npx.cmd"), "-y", "@modelcontextprotocol/server-sequential-thinking"],
                         servers["sequential-thinking"]["args"])
        codex = tomllib.loads((self.home / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(bundle_apply._cmd_executable(), codex["mcp_servers"]["headroom"]["command"])

    def test_launcher_lookup_ignores_the_current_directory_and_relative_path_entries(self):
        name = "inonu-test-tool"
        suffix = ".exe" if os.name == "nt" else ""
        planted, real = self.root / "planted", self.root / "real"
        for directory in (planted, real):
            directory.mkdir()
            executable = directory / f"{name}{suffix}"
            executable.write_bytes(b"")
            executable.chmod(0o755)
        previous = os.getcwd()
        os.chdir(planted)
        try:
            with patch.dict(os.environ, {"PATH": os.pathsep.join(["", ".", str(real)])}):
                found = bundle_apply._find_executable(name)
            with patch.dict(os.environ, {"PATH": os.pathsep.join(["", "."])}):
                missing = bundle_apply._find_executable(name)
        finally:
            os.chdir(previous)
        self.assertEqual(str(real / f"{name}{suffix}"), found)
        self.assertIsNone(missing)

    def test_conflict_with_apply_never_reports_a_write(self):
        self.write(".claude/settings.json", "{")
        before = snapshot(self.home)
        status, report, _ = self.run_cli("apply", "--apply", "--with-stop-hook")
        self.assertEqual(2, status)
        results = {item["result"] for item in report["items"]}
        self.assertTrue({"installed", "updated", "removed"}.isdisjoint(results), results)
        self.assertIn("would_install", results)
        self.assertEqual(before, snapshot(self.home))

    def test_status_reports_the_hook_that_apply_wrote(self):
        self.run_cli("apply", "--apply", "--with-stop-hook")
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            cli_main(["bundle", "status", "--host", "claude", "--home", str(self.home)])
        found = {(item["kind"], item.get("id", "")): item["state"] for item in json.loads(stdout.getvalue())["items"]}
        self.assertEqual("present", found[("stop-hook", "")])
        self.assertEqual("current", found[("worker-agent", "")])

    def test_remove_restores_preexisting_empty_containers_files_and_directories(self):
        self.write(".claude.json", json.dumps({"mcpServers": {}, "numStartups": 2}))
        self.write(".claude/settings.json", json.dumps({"hooks": {"Stop": []}, "theme": "dark"}))
        self.write(".codex/config.toml", "")
        for directory in (".claude/skills", ".claude/agents", ".agents"):
            (self.home / directory).mkdir(parents=True, exist_ok=True)
        self.assertEqual(0, self.run_cli("apply", "--with-stop-hook", "--apply")[0])
        status, report, _ = self.run_cli("remove", "--with-stop-hook", "--apply")
        self.assertEqual(0, status, report)
        self.assertEqual({"mcpServers": {}, "numStartups": 2}, self.read_json(".claude.json"))
        self.assertEqual({"hooks": {"Stop": []}, "theme": "dark"}, self.read_json(".claude/settings.json"))
        self.assertEqual("", (self.home / ".codex" / "config.toml").read_text(encoding="utf-8"))
        for directory in (".claude/skills", ".claude/agents", ".agents"):
            self.assertTrue((self.home / directory).is_dir(), directory)
        self.assertFalse((self.home / ".claude" / "skills" / "inonu-harness").exists())

    def test_remove_restores_a_preexisting_empty_object_file(self):
        self.write(".claude.json", "{}")
        self.write(".claude/settings.json", "{}")
        self.run_cli("apply", "--with-stop-hook", "--apply")
        self.assertEqual(0, self.run_cli("remove", "--with-stop-hook", "--apply")[0])
        self.assertEqual({}, self.read_json(".claude.json"))
        self.assertEqual({}, self.read_json(".claude/settings.json"))

    def test_non_finite_json_numbers_conflict_instead_of_corrupting_the_file(self):
        self.write(".claude/settings.json", '{"limit": 1e400}')
        before = snapshot(self.home)
        status, report, _ = self.run_cli("apply", "--apply", "--with-stop-hook")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("stop-hook", "claude", "Stop")])
        self.assertEqual(before, snapshot(self.home))

    def test_codex_block_with_changed_line_endings_is_a_conflict_not_absent(self):
        self.run_cli("apply", "--host", "codex", "--apply")
        path = self.home / ".codex" / "config.toml"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        before = snapshot(self.home)
        status, report, _ = self.run_cli("remove", "--host", "codex", "--apply")
        self.assertEqual(2, status)
        self.assertEqual({"conflict"}, {item["result"] for item in report["items"] if item["kind"] == "mcp"})
        self.assertEqual(before, snapshot(self.home))

    def files_on_disk(self):
        return {path.relative_to(self.home).as_posix() for path in self.home.rglob("*") if path.is_file()}

    def test_failed_write_rolls_back_every_file(self):
        original_write = host_profiles._atomic_write
        for fail_at in range(1, 40):
            self.home = self.root / f"fault{fail_at}"
            self.home.mkdir()
            self.write(".claude.json", json.dumps({"numStartups": 1}))
            self.write(".codex/config.toml", 'model = "gpt"\n')
            originals = {name: (self.home / name).read_bytes() for name in (".claude.json", ".codex/config.toml")}
            calls = []

            def flaky(path, content):
                calls.append(path)
                if len(calls) == fail_at:
                    raise OSError("injected")
                return original_write(path, content)

            with patch("inonu_harness.host_profiles._atomic_write", flaky):
                status, report, _ = self.run_cli("apply", "--apply", "--with-stop-hook")
            if status == 0:
                self.assertGreater(fail_at, 5, "apply should perform several writes")
                break
            with self.subTest(fail_at=fail_at):
                self.assertEqual("complete", report["rollback"])
                self.assertIn("failed", {item["result"] for item in report["items"]})
                self.assertEqual({".claude.json", ".codex/config.toml"}, self.files_on_disk())
                for name, content in originals.items():
                    self.assertEqual(content, (self.home / name).read_bytes())
        else:
            self.fail("apply never completed within the injected-failure range")

    def test_change_between_writes_rolls_back_and_keeps_the_outside_edit(self):
        original_write = host_profiles._atomic_write
        self.write(".claude.json", json.dumps({"numStartups": 1}))
        self.write(".codex/config.toml", 'model = "gpt"\n')
        calls = []

        def racing(path, content):
            result = original_write(path, content)
            calls.append(path)
            if len(calls) == 1:
                self.write(".claude.json", json.dumps({"edited": "outside"}))
                self.write(".codex/config.toml", 'model = "edited"\n')
            return result

        with patch("inonu_harness.host_profiles._atomic_write", racing):
            status, report, _ = self.run_cli("apply", "--apply", "--with-stop-hook")
        self.assertEqual(2, status)
        self.assertEqual("complete", report["rollback"])
        self.assertIn("conflict", {item["result"] for item in report["items"]})
        self.assertEqual({"edited": "outside"}, self.read_json(".claude.json"))
        self.assertEqual('model = "edited"\n', (self.home / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual({".claude.json", ".codex/config.toml"}, self.files_on_disk())

    def test_cmd_executable_prefers_an_absolute_comspec(self):
        shell = self.root / "shell" / "cmd.exe"
        shell.parent.mkdir()
        shell.write_bytes(b"")
        with patch.dict(os.environ, {"COMSPEC": str(shell)}):
            self.assertEqual(str(shell), bundle_apply._cmd_executable())
        with patch.dict(os.environ, {"COMSPEC": "cmd.exe", "SystemRoot": str(self.root)}):
            self.assertEqual(str(self.root / "System32" / "cmd.exe"), bundle_apply._cmd_executable())

    def test_outside_edit_after_a_write_survives_rollback_and_is_reported(self):
        original_write = host_profiles._atomic_write

        def hostile(path, content):
            if path.name == "bundle-ledger.json":
                self.write(".claude.json", json.dumps({"edited": "outside"}))  # after .claude.json was written
                raise OSError("injected")
            original_write(path, content)

        with patch("inonu_harness.host_profiles._atomic_write", hostile):
            status, report, _ = self.run_cli("apply", "--host", "claude", "--apply", "--with-stop-hook")
        self.assertEqual(2, status)
        self.assertEqual("incomplete", report["rollback"])
        self.assertEqual({"edited": "outside"}, self.read_json(".claude.json"))
        self.assertFalse((self.home / ".claude" / "agents" / "inonu-worker.md").exists())
        self.assertFalse((self.home / ".claude" / "settings.json").exists())

    def test_created_markers_do_not_outlive_a_partial_removal(self):
        self.run_cli("apply", "--apply")
        self.assertEqual(0, self.run_cli("remove", "--host", "codex", "--apply")[0])
        self.assertFalse((self.home / ".codex" / "config.toml").exists())
        self.write(".codex/config.toml", "")
        self.assertEqual(0, self.run_cli("apply", "--host", "codex", "--apply")[0])
        self.assertEqual(0, self.run_cli("remove", "--host", "codex", "--apply")[0])
        self.assertTrue((self.home / ".codex" / "config.toml").is_file())
        self.assertEqual("", (self.home / ".codex" / "config.toml").read_text(encoding="utf-8"))

    def test_preexisting_ledger_directory_survives_remove(self):
        (self.home / ".inonu-harness").mkdir()
        self.assertEqual(0, self.run_cli("apply", "--host", "codex", "--apply", stubs={})[0])
        self.assertEqual(0, self.run_cli("remove", "--host", "codex", "--apply", stubs={})[0])
        self.assertTrue((self.home / ".inonu-harness").is_dir())

    def test_ledger_directory_created_by_apply_is_removed_with_it(self):
        self.assertEqual(0, self.run_cli("apply", "--host", "codex", "--apply", stubs={})[0])
        self.assertEqual(0, self.run_cli("remove", "--host", "codex", "--apply", stubs={})[0])
        self.assertFalse((self.home / ".inonu-harness").exists())

    def test_regular_file_where_a_directory_belongs_is_a_conflict_in_preview(self):
        self.write(".codex", "precious")
        before = snapshot(self.home)
        status, report, _ = self.run_cli("apply", "--host", "codex")
        self.assertEqual(2, status)
        self.assertIn("conflict", {item["result"] for item in report["items"] if item["kind"] == "mcp"})
        self.assertEqual(before, snapshot(self.home))

    def test_json_that_cannot_be_written_back_as_utf8_is_a_conflict(self):
        self.write(".claude.json", '{"x": "' + chr(92) + 'ud800"}')
        before = snapshot(self.home)
        status, report, _ = self.run_cli("apply", "--host", "claude", "--apply")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("mcp", "claude", "codegraph")])
        self.assertEqual("would_install", states(report)[("worker-agent", "claude", "inonu-worker")])
        self.assertEqual(before, snapshot(self.home))

    def test_nan_and_infinity_constants_are_conflicts(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                self.write(".claude/settings.json", '{"x": ' + constant + "}")
                before = snapshot(self.home)
                status, report, _ = self.run_cli("apply", "--apply", "--with-stop-hook")
                self.assertEqual(2, status)
                self.assertEqual("conflict", states(report)[("stop-hook", "claude", "Stop")])
                self.assertEqual(before, snapshot(self.home))

    def test_second_checkout_cannot_add_a_second_stop_hook(self):
        self.assertEqual(0, self.run_cli("apply", "--host", "claude", "--apply", "--with-stop-hook")[0])
        other = self.root / "other-checkout"
        shutil.copytree(REPOSITORY, other, ignore=shutil.ignore_patterns(".git", "__pycache__", ".jevis", ".codegraph"))
        before = snapshot(self.home)
        with patch("inonu_harness.bundle_apply._find_executable", side_effect=lambda name: str(self.stubs / ALL_STUBS[name])):
            status, report = bundle_apply.run_bundle(
                "apply", "claude", self.home, with_stop_hook=True, apply=True, repository=other,
            )
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("stop-hook", "claude", "Stop")])
        self.assertEqual(before, snapshot(self.home))

    def test_edited_stop_hook_command_is_a_conflict_on_remove(self):
        self.run_cli("apply", "--host", "claude", "--apply", "--with-stop-hook")
        doc = self.read_json(".claude/settings.json")
        doc["hooks"]["Stop"][0]["hooks"][0]["command"] += " --verbose"
        (self.home / ".claude" / "settings.json").write_text(json.dumps(doc), encoding="utf-8")
        before = snapshot(self.home)
        status, report, _ = self.run_cli("remove", "--host", "claude", "--apply", "--with-stop-hook")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("stop-hook", "claude", "Stop")])
        self.assertEqual(before, snapshot(self.home))

    def test_modified_worker_agent_and_skill_are_kept_on_remove(self):
        self.run_cli("apply", "--host", "claude", "--apply")
        worker = self.home / ".claude" / "agents" / "inonu-worker.md"
        skill = self.home / ".claude" / "skills" / "inonu-harness" / "SKILL.md"
        worker.write_text(worker.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
        skill.write_text(skill.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
        before = snapshot(self.home)
        status, report, _ = self.run_cli("remove", "--host", "claude", "--apply")
        self.assertEqual(2, status)
        found = states(report)
        self.assertEqual("conflict", found[("worker-agent", "claude", "inonu-worker")])
        self.assertEqual("conflict", found[("skill", "claude", "inonu-harness")])
        self.assertEqual(before, snapshot(self.home))

    def test_crlf_block_is_matched_even_when_the_server_table_is_gone(self):
        self.run_cli("apply", "--host", "codex", "--apply")
        path = self.home / ".codex" / "config.toml"
        text = path.read_text(encoding="utf-8").replace("[mcp_servers.codegraph]", "[mcp_servers.renamed]")
        path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        before = snapshot(self.home)
        status, report, _ = self.run_cli("remove", "--host", "codex", "--apply")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("mcp", "codex", "codegraph")])
        self.assertEqual(before, snapshot(self.home))

    def test_apply_backs_up_a_preexisting_config_before_changing_it(self):
        original = json.dumps({"numStartups": 7}).encode("utf-8")
        (self.home / ".claude.json").write_bytes(original)
        self.assertEqual(0, self.run_cli("apply", "--host", "claude", "--apply")[0])
        backups = list((self.home / ".inonu-harness" / "backups").glob(".claude.json.*"))
        self.assertEqual([original], [path.read_bytes() for path in backups])
        self.assertEqual(0, self.run_cli("remove", "--host", "claude", "--apply")[0])
        self.assertEqual([original], [path.read_bytes() for path in backups], "remove keeps the backup")
        self.assertEqual(1, len(list((self.home / ".inonu-harness" / "backups").iterdir())), "remove adds no backup")
    def test_interrupt_rolls_back_every_file_and_propagates(self):
        original_write = host_profiles._atomic_write
        for fail_at in range(1, 40):
            self.home = self.root / f"interrupt{fail_at}"
            self.home.mkdir()
            self.write(".claude.json", json.dumps({"numStartups": 1}))
            self.write(".codex/config.toml", 'model = "gpt"\n')
            calls = []

            def interrupting(path, content):
                calls.append(path)
                if len(calls) == fail_at:
                    raise KeyboardInterrupt
                return original_write(path, content)

            try:
                with patch("inonu_harness.host_profiles._atomic_write", interrupting):
                    status, _, _ = self.run_cli("apply", "--apply", "--with-stop-hook")
            except KeyboardInterrupt:
                with self.subTest(fail_at=fail_at):
                    self.assertEqual({".claude.json", ".codex/config.toml"}, self.files_on_disk())
                continue
            self.assertEqual(0, status)
            self.assertGreater(fail_at, 5)
            break
        else:
            self.fail("apply never completed within the injected-interrupt range")

    def test_identical_but_unrecorded_worker_file_is_left_alone_and_does_not_block_remove(self):
        worker = self.home / ".claude" / "agents" / "inonu-worker.md"
        worker.parent.mkdir(parents=True)
        worker.write_bytes((bundle_apply.REPOSITORY / bundle_apply.WORKER_SOURCE).read_bytes())
        status, report, _ = self.run_cli("apply", "--host", "claude", "--apply")
        self.assertEqual("unchanged", states(report)[("worker-agent", "claude", "inonu-worker")])
        status, report, _ = self.run_cli("remove", "--host", "claude", "--apply")
        self.assertEqual(0, status, report)
        self.assertEqual("absent", states(report)[("worker-agent", "claude", "inonu-worker")])
        self.assertTrue(worker.is_file())
        self.assertFalse((self.home / ".claude" / "skills" / "inonu-harness").exists())

    def test_foreign_stop_hook_without_a_ledger_is_a_conflict_for_both_endings(self):
        for ending in ("check", "hook stop"):
            with self.subTest(ending=ending):
                self.write(".claude/settings.json", json.dumps({"hooks": {"Stop": [{"hooks": [
                    {"type": "command", "command": f"python '/other/checkout/scripts/inonu.py' {ending}"},
                ]}]}}))
                before = snapshot(self.home)
                status, report, _ = self.run_cli("apply", "--host", "claude", "--apply", "--with-stop-hook")
                self.assertEqual(2, status)
                self.assertEqual("conflict", states(report)[("stop-hook", "claude", "Stop")])
                self.assertEqual(before, snapshot(self.home))

    def test_legacy_check_registration_of_this_checkout_conflicts_and_is_kept(self):
        legacy = self.stop_group(bundle_apply._hook_command(REPOSITORY).replace(" hook stop", " check"))
        self.write(".claude/settings.json", json.dumps({"hooks": {"Stop": [legacy]}}))
        before = snapshot(self.home)
        status, report, _ = self.run_cli("apply", "--host", "claude", "--apply", "--with-stop-hook")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("stop-hook", "claude", "Stop")])
        self.assertEqual(before, snapshot(self.home))

    def test_remove_reverses_a_legacy_check_registration_that_the_ledger_recorded(self):
        legacy = self.stop_group(bundle_apply._hook_command(REPOSITORY).replace(" hook stop", " check"))
        self.write(".claude/settings.json", json.dumps({"hooks": {"Stop": [legacy]}, "theme": "dark"}))
        self.write(".inonu-harness/bundle-ledger.json", json.dumps(
            {"schema_version": 1, "items": {"stop-hook:claude:Stop": {"sha256": bundle_apply._canon(legacy)}}}))
        status, report, _ = self.run_cli("remove", "--host", "claude", "--with-stop-hook", "--apply")
        self.assertEqual(0, status, report)
        self.assertEqual("removed", states(report)[("stop-hook", "claude", "Stop")])
        self.assertEqual({"hooks": {"Stop": []}, "theme": "dark"}, self.read_json(".claude/settings.json"))

    def test_duplicate_keys_in_a_user_json_file_are_a_conflict(self):
        self.write(".claude.json", '{"a": 1, "a": 2}')
        before = snapshot(self.home)
        status, report, _ = self.run_cli("apply", "--host", "claude", "--apply")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("mcp", "claude", "codegraph")])
        self.assertEqual(before, snapshot(self.home))

    def test_an_unledgered_legacy_stop_hook_is_a_conflict_on_remove_and_stays_in_place(self):
        legacy = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python '/old/scripts/inonu.py' check"}]}]}}
        self.write(".claude/settings.json", json.dumps(legacy))
        before = snapshot(self.home)
        status, report, _ = self.run_cli("remove", "--host", "claude", "--apply", "--with-stop-hook")
        self.assertEqual(2, status)
        self.assertEqual("conflict", states(report)[("stop-hook", "claude", "Stop")])
        self.assertEqual(before, snapshot(self.home))


if __name__ == "__main__":
    unittest.main()
