import json
import shutil
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from inonu_harness import bundle_apply
from inonu_harness.bundle import MCP_SERVER_IDS, REPOSITORY, status_bundle
from inonu_harness.cli import main as cli_main


SECRET = "sk-test-" + "SECRET-VALUE-67890"  # assembled, so no credential-looking literal is committed
STUBS = {"codegraph": "codegraph.exe", "headroom": "headroom.exe", "npx": "npx.exe"}
# (kind, host, id) as the report keys them; skills, the worker agent and the Stop hook have no id.
ITEMS = (
    ("skill", "codex", ""),
    ("skill", "claude", ""),
    ("worker-agent", "claude", ""),
    ("mcp", "claude", "codegraph"),
    ("mcp", "codex", "codegraph"),
    ("stop-hook", "claude", ""),
)
ITEM_COUNT = 10  # two skills, the worker agent, the Stop hook, and three MCP servers on each host
LEDGER = ".inonu-harness/bundle-ledger.json"


def snapshot(home: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(home).as_posix(): None if path.is_dir() else path.read_bytes()
        for path in home.rglob("*")
    }


def by_key(report: dict, field: str) -> dict[tuple[str, str, str], str]:
    return {(item["kind"], item["host"], item.get("id", "")): item[field] for item in report["items"]}


class BundleOwnershipTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.stubs = self.root / "stubs"
        self.stubs.mkdir()
        for filename in STUBS.values():
            (self.stubs / filename).write_bytes(b"")
        self.home = self.new_home("home")

    def new_home(self, name):
        home = self.root / name
        home.mkdir()
        return home

    def install(self):
        """The real `bundle apply --apply` with every item, into self.home, with fake launchers on PATH."""
        def fake_which(name):
            return str(self.stubs / STUBS[name])

        with patch("inonu_harness.bundle_apply._find_executable", side_effect=fake_which), \
                redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            status = cli_main(["bundle", "apply", "--with-stop-hook", "--apply", "--home", str(self.home)])
        self.assertEqual(0, status)

    def run_status(self):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli_main(["bundle", "status", "--home", str(self.home)])
        return status, stdout.getvalue(), stderr.getvalue()

    def status(self):
        status, text, error = self.run_status()
        self.assertEqual((0, ""), (status, error))
        return json.loads(text)

    def assert_status_is_clean(self):
        before = snapshot(self.home)
        status, text, error = self.run_status()
        self.assertEqual(before, snapshot(self.home))
        self.assertEqual((0, ""), (status, error))
        self.assertNotIn(SECRET, text)
        for form in (str(self.home), json.dumps(str(self.home))[1:-1], self.home.as_posix()):
            self.assertNotIn(form, text)

    def write(self, relative, text):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read_json(self, relative):
        return json.loads((self.home / relative).read_text(encoding="utf-8"))

    def write_json(self, relative, doc):
        self.write(relative, json.dumps(doc))

    def skill_path(self, host):
        return self.home / (".agents" if host == "codex" else ".claude") / "skills" / "inonu-harness" / "SKILL.md"

    def worker_path(self):
        return self.home / ".claude" / "agents" / "inonu-worker.md"

    def edit(self, kind, host, ident):
        if kind == "stop-hook":
            doc = self.read_json(".claude/settings.json")
            doc["hooks"]["Stop"][0]["hooks"][0]["timeout"] = 1
            self.write_json(".claude/settings.json", doc)
        elif kind == "mcp" and host == "claude":
            doc = self.read_json(".claude.json")
            doc["mcpServers"][ident]["command"] = "edited"
            self.write_json(".claude.json", doc)
        elif kind == "mcp":  # bytes, so the other blocks keep their line endings
            path = self.home / ".codex" / "config.toml"
            marker = f"# <<< inonu-harness mcp {ident}".encode("utf-8")
            path.write_bytes(path.read_bytes().replace(marker, b"# edited by hand\n" + marker))
        else:
            path = self.skill_path(host) if kind == "skill" else self.worker_path()
            path.write_text(path.read_text(encoding="utf-8") + "\nedited by hand\n", encoding="utf-8")

    def delete(self, kind, host, ident):
        if kind == "stop-hook":
            doc = self.read_json(".claude/settings.json")
            doc["hooks"]["Stop"] = []
            self.write_json(".claude/settings.json", doc)
        elif kind == "mcp" and host == "claude":
            doc = self.read_json(".claude.json")
            del doc["mcpServers"][ident]
            self.write_json(".claude.json", doc)
        elif kind == "mcp":  # only the marked block goes; the other servers stay
            path = self.home / ".codex" / "config.toml"
            raw = path.read_bytes()
            start = raw.index(f"# >>> inonu-harness mcp {ident}".encode("utf-8"))
            end = raw.index(b"\n", raw.index(f"# <<< inonu-harness mcp {ident}".encode("utf-8"))) + 1
            path.write_bytes(raw[:start] + raw[end:])
        else:
            (self.skill_path(host) if kind == "skill" else self.worker_path()).unlink()

    def damage_ledger(self, kind, stack):
        ledger = self.home / LEDGER
        if kind == "malformed":
            ledger.write_text("{", encoding="utf-8")
        elif kind == "wrong schema":
            ledger.write_text(json.dumps({"schema_version": 2, "items": {}}), encoding="utf-8")
        elif kind == "empty":
            ledger.write_bytes(b"")
        elif kind == "schema is true":
            ledger.write_text(json.dumps({"schema_version": True, "items": {}}), encoding="utf-8")
        elif kind == "schema is 1.0":
            ledger.write_text('{"schema_version": 1.0, "items": {}}', encoding="utf-8")
        elif kind == "bad hash":
            ledger.write_text(json.dumps({"schema_version": 1, "items": {"mcp:claude:codegraph": {"sha256": "not-a-digest"}}}),
                              encoding="utf-8")
        elif kind == "directory":
            ledger.unlink()
            ledger.mkdir()
        elif kind == "file in the way":
            shutil.rmtree(self.home / ".inonu-harness")
            (self.home / ".inonu-harness").write_text("a file, not a directory", encoding="utf-8")
        else:  # symbolic link
            target = self.root / f"{self.home.name}-ledger.json"
            target.write_bytes(ledger.read_bytes())
            ledger.unlink()
            try:
                ledger.symlink_to(target)
            except OSError:  # this host needs a privilege to make links: report the same bytes as a link instead
                ledger.write_bytes(target.read_bytes())
                real_is_symlink = Path.is_symlink
                stack.enter_context(patch.object(Path, "is_symlink", lambda path: path == ledger or real_is_symlink(path)))

    def test_empty_home_is_none_for_every_item_and_nothing_is_written(self):
        before = snapshot(self.home)
        report = self.status()
        self.assertEqual(before, snapshot(self.home))
        self.assertEqual(ITEM_COUNT, len(report["items"]))
        self.assertEqual("absent", report["ledger"])
        self.assertEqual({"none": ITEM_COUNT}, report["ownership_summary"])

    def test_right_after_apply_every_item_is_ours(self):
        self.install()
        report = self.status()
        self.assertEqual("present", report["ledger"])
        self.assertEqual({"ours": ITEM_COUNT}, report["ownership_summary"])

    def test_an_edited_or_deleted_item_is_modified_and_the_rest_stay_ours(self):
        for index, item in enumerate(ITEMS):
            for change in ("edit", "delete"):
                with self.subTest(item=item, change=change):
                    self.home = self.new_home(f"{change}-{index}")
                    self.install()
                    getattr(self, change)(*item)
                    report = self.status()
                    self.assertEqual("modified", by_key(report, "ownership")[item])
                    self.assertEqual({"modified": 1, "ours": ITEM_COUNT - 1}, report["ownership_summary"])

    def test_no_ledger_makes_installed_items_foreign_and_a_user_server_stays_out(self):
        self.install()
        (self.home / LEDGER).unlink()
        doc = self.read_json(".claude.json")
        doc["mcpServers"]["mine"] = {"command": "mine", "env": {"KEY": SECRET}}
        self.write_json(".claude.json", doc)
        path = self.home / ".codex" / "config.toml"
        path.write_bytes(path.read_bytes() + b'[mcp_servers.mine]\ncommand = "mine"\n')
        report = self.status()
        self.assertEqual("absent", report["ledger"])
        self.assertEqual({"foreign": ITEM_COUNT}, report["ownership_summary"])
        self.assertEqual(set(MCP_SERVER_IDS), {item["id"] for item in report["items"] if item["kind"] == "mcp"})

    def test_hand_written_items_without_a_ledger_are_foreign(self):
        self.write_json(".claude.json", {"mcpServers": {"codegraph": {"command": "mine"}}})
        self.write(".codex/config.toml", '[mcp_servers.codegraph]\ncommand = "mine"\n')
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "python '/other/scripts/inonu.py' hook stop"},
        ]}]}})
        report = self.status()
        found = by_key(report, "ownership")
        self.assertEqual("foreign", found[("mcp", "claude", "codegraph")])
        self.assertEqual("foreign", found[("mcp", "codex", "codegraph")])  # a bare table, no marked block
        self.assertEqual("foreign", found[("stop-hook", "claude", "")])
        self.assertEqual({"foreign": 3, "none": ITEM_COUNT - 3}, report["ownership_summary"])

    def test_a_codex_server_table_without_its_markers_is_modified_when_recorded(self):
        self.install()
        path = self.home / ".codex" / "config.toml"
        raw = path.read_bytes().replace(b"# >>> inonu-harness mcp codegraph\n", b"")
        path.write_bytes(raw.replace(b"# <<< inonu-harness mcp codegraph\n", b""))
        report = self.status()
        self.assertEqual("modified", by_key(report, "ownership")[("mcp", "codex", "codegraph")])

    def test_an_outdated_skill_the_bundle_wrote_is_still_ours(self):
        self.install()
        checkout = self.root / "newer-checkout"
        shutil.copytree(REPOSITORY, checkout, ignore=shutil.ignore_patterns(".git", "__pycache__", ".jevis", ".codegraph"))
        skill = checkout / "skills" / "inonu-harness" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nA newer skill text.\n", encoding="utf-8")
        report = bundle_apply.status_with_ownership("both", self.home, checkout)
        states, found = by_key(report, "state"), by_key(report, "ownership")
        for host in ("codex", "claude"):
            self.assertEqual("outdated", states[("skill", host, "")])
            self.assertEqual("ours", found[("skill", host, "")])
        self.assertEqual({"ours": ITEM_COUNT}, report["ownership_summary"])

    def test_an_unreadable_ledger_makes_every_item_unknown(self):
        for kind in ("malformed", "empty", "wrong schema", "schema is true", "schema is 1.0", "bad hash", "directory",
                     "file in the way", "symbolic link"):
            with self.subTest(ledger=kind), ExitStack() as stack:
                self.home = self.new_home(kind.replace(" ", "-"))
                self.install()
                self.damage_ledger(kind, stack)
                report = self.status()
                self.assertEqual("unreadable", report["ledger"])
                self.assertEqual({"unknown": ITEM_COUNT}, report["ownership_summary"])

    def test_a_malformed_host_file_makes_only_its_items_unknown(self):
        self.install()
        self.write(".claude/settings.json", "{")
        self.write(".codex/config.toml", "[mcp_servers\n")
        report = self.status()
        found = by_key(report, "ownership")
        self.assertEqual("unknown", found[("stop-hook", "claude", "")])
        for server in MCP_SERVER_IDS:
            self.assertEqual("unknown", found[("mcp", "codex", server)])
        self.assertEqual("ours", found[("mcp", "claude", "codegraph")])
        self.assertEqual({"ours": 6, "unknown": 4}, report["ownership_summary"])

    def test_a_directory_where_a_host_file_belongs_makes_its_items_unknown(self):
        self.install()
        (self.home / ".claude.json").unlink()
        (self.home / ".claude.json").mkdir()
        report = self.status()
        found = by_key(report, "ownership")
        for server in MCP_SERVER_IDS:
            self.assertEqual("unknown", found[("mcp", "claude", server)])
        self.assertEqual("ours", found[("skill", "claude", "")])
        self.assertEqual("ours", found[("mcp", "codex", "codegraph")])

    def test_canonical_json_digests_ignore_key_order_and_spacing_but_not_content(self):
        self.install()
        doc = self.read_json(".claude.json")
        entry = doc["mcpServers"]["codegraph"]
        doc["mcpServers"]["codegraph"] = dict(reversed(list(entry.items())))
        self.write(".claude.json", json.dumps(doc, indent=8))
        settings = self.read_json(".claude/settings.json")
        group = settings["hooks"]["Stop"][0]
        settings["hooks"]["Stop"][0] = {"hooks": [dict(reversed(list(hook.items()))) for hook in group["hooks"]]}
        self.write(".claude/settings.json", json.dumps(settings, indent=8))
        found = by_key(self.status(), "ownership")
        self.assertEqual("ours", found[("mcp", "claude", "codegraph")])
        self.assertEqual("ours", found[("stop-hook", "claude", "")])
        doc["mcpServers"]["codegraph"]["env"] = {"KEY": "changed"}
        self.write_json(".claude.json", doc)
        self.assertEqual("modified", by_key(self.status(), "ownership")[("mcp", "claude", "codegraph")])

    def test_a_stop_group_of_the_user_placed_before_ours_leaves_ours_ours(self):
        self.install()
        doc = self.read_json(".claude/settings.json")
        doc["hooks"]["Stop"].insert(0, {"hooks": [{"type": "command", "command": "echo mine"}]})
        self.write_json(".claude/settings.json", doc)
        self.assertEqual("ours", by_key(self.status(), "ownership")[("stop-hook", "claude", "")])

    def test_another_inonu_command_in_a_stop_group_is_foreign_not_ours(self):
        self.write_json(".claude/settings.json", {"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "python '/other/scripts/inonu.py' baseline run"},
        ]}]}})
        report = self.status()
        self.assertEqual("foreign", by_key(report, "ownership")[("stop-hook", "claude", "")])
        self.assertEqual("absent", by_key(report, "state")[("stop-hook", "claude", "")])

    def test_a_codex_table_added_outside_the_markers_makes_the_server_modified(self):
        self.install()
        path = self.home / ".codex" / "config.toml"
        path.write_bytes(path.read_bytes() + b'[mcp_servers.codegraph.env]\nKEY = "changed"\n[mcp_servers.mine]\ncommand = "mine"\n')
        found = by_key(self.status(), "ownership")
        self.assertEqual("modified", found[("mcp", "codex", "codegraph")])
        self.assertEqual("ours", found[("mcp", "codex", "headroom")])

    def test_a_codex_file_rewritten_with_crlf_makes_its_servers_modified(self):
        self.install()
        path = self.home / ".codex" / "config.toml"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        found = by_key(self.status(), "ownership")
        for server in MCP_SERVER_IDS:
            self.assertEqual("modified", found[("mcp", "codex", server)])

    def test_a_host_file_that_cannot_be_read_makes_only_its_item_unknown(self):
        self.install()
        real = bundle_apply._read_shared

        def denied(path):
            if path.name == "inonu-worker.md":
                raise PermissionError
            return real(path)

        with patch.object(bundle_apply, "_read_shared", denied):
            report = bundle_apply.status_with_ownership("both", self.home)
        self.assertEqual("unknown", by_key(report, "ownership")[("worker-agent", "claude", "")])
        self.assertEqual({"ours": ITEM_COUNT - 1, "unknown": 1}, report["ownership_summary"])

    def test_a_skill_file_that_cannot_be_read_is_unknown_and_status_and_plan_still_exit_0(self):
        self.install()
        with patch("inonu_harness.host_profiles._file_hash", side_effect=PermissionError):
            outputs = {}
            for operation in ("status", "plan"):
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = cli_main(["bundle", operation, "--home", str(self.home)])
                self.assertEqual((0, ""), (code, stderr.getvalue()), operation)
                outputs[operation] = json.loads(stdout.getvalue())
        for host in ("codex", "claude"):
            self.assertEqual("unknown", by_key(outputs["status"], "state")[("skill", host, "")])
        plan_skills = [item["status"]["skill"] for item in outputs["plan"]["items"] if item["kind"] == "skill"]
        self.assertEqual(["unknown", "unknown"], plan_skills)

    def test_a_skill_without_its_metadata_is_a_conflict_in_state_but_still_ours(self):
        self.install()
        (self.skill_path("claude").parent / ".inonu-harness.json").unlink()
        report = self.status()
        self.assertEqual("conflict", by_key(report, "state")[("skill", "claude", "")])
        self.assertEqual("ours", by_key(report, "ownership")[("skill", "claude", "")])

    def test_existing_keys_states_and_summary_are_unchanged_and_the_summary_adds_up(self):
        self.install()
        self.edit("mcp", "claude", "codegraph")
        report = self.status()
        plain = status_bundle("both", self.home)
        for key in plain:
            if key != "items":
                self.assertEqual(plain[key], report[key], key)
        self.assertEqual(plain["items"], [{k: v for k, v in item.items() if k != "ownership"} for item in report["items"]])
        self.assertEqual(len(report["items"]), sum(report["ownership_summary"].values()))

    def test_status_writes_nothing_and_prints_no_secret_or_home_path(self):
        self.write_json(".claude.json", {"mcpServers": {"mine": {"env": {"KEY": SECRET}}}})
        self.write_json(".claude/settings.json", {"env": {"TOKEN": SECRET}})
        self.write(".codex/config.toml", f'[mcp_servers.mine]\ncommand = "x"\nenv = {{ KEY = "{SECRET}" }}\n')
        self.assert_status_is_clean()
        self.install()
        self.assert_status_is_clean()
        with ExitStack() as stack:
            self.damage_ledger("malformed", stack)
            self.assert_status_is_clean()


if __name__ == "__main__":
    unittest.main()
