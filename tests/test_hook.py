import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from inonu_harness import hook
from inonu_harness.cli import main
from inonu_harness.hook import parse_config, run_stop, run_trust, run_untrust

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
PASS = [PY, "-c", "pass"]
FAIL = [PY, "-c", "raise SystemExit(1)"]
CONFIG_LIMIT = 64 * 1024
UNEXPECTED = "inonu hook: unexpected error\n"
# Assembled at run time from fragments, so the repository holds no credential-looking literal.
CREDENTIAL = "AK" + "IA" + "Q7W8E9R2T3Y4U5I6"
TREE_PARENT = """import pathlib, subprocess, sys, time
d = pathlib.Path(sys.argv[1])
subprocess.Popen([sys.executable, str(d / 'grand.py'), str(d)])
time.sleep(60)
"""
TICKER = """import pathlib, sys, time
d = pathlib.Path(sys.argv[1])
while True:
    with open(d / 'ticks', 'a') as ticks:
        ticks.write('x')
    time.sleep(0.05)
"""


def verifier(checks, timeout=30, blocks=3):
    return {
        "checks": [{"id": check_id, "argv": list(argv)} for check_id, argv in checks],
        "timeout_seconds": timeout,
        "max_consecutive_blocks": blocks,
    }


def touch_check(name):
    return [PY, "-c", f"import pathlib; pathlib.Path({name!r}).touch()"]


class ConfigParsingTests(unittest.TestCase):
    BASE = verifier([("lint", PASS)])

    def test_valid_config_keeps_every_field(self):
        parsed = parse_config(json.dumps(self.BASE).encode("utf-8"))
        self.assertEqual([("lint", tuple(PASS))], [(check.id, check.argv) for check in parsed.checks])
        self.assertEqual((30, 3), (parsed.timeout_seconds, parsed.max_consecutive_blocks))

    def test_edge_values_are_accepted(self):
        twenty = verifier([(f"c{i}", PASS) for i in range(20)], timeout=600, blocks=20)
        for data in (verifier([("a", PASS)], timeout=1, blocks=1), twenty):
            with self.subTest(checks=len(data["checks"])):
                parse_config(json.dumps(data).encode("utf-8"))

    def test_every_invalid_config_is_a_value_error(self):
        def edit(change):
            data = copy.deepcopy(self.BASE)
            change(data)
            return json.dumps(data)

        cases = {
            "not JSON": "{",
            "top-level list": "[]",
            "invalid UTF-8": b"\xff",
            "duplicate top-level key": '{"checks": [], ' + json.dumps(self.BASE)[1:],
            "duplicate check id": json.dumps(verifier([("a", PASS), ("a", PASS)])),
            "missing timeout": edit(lambda d: d.pop("timeout_seconds")),
            "missing block limit": edit(lambda d: d.pop("max_consecutive_blocks")),
            "unknown key": edit(lambda d: d.update(extra=1)),
            "checks not a list": edit(lambda d: d.update(checks="lint")),
            "no checks": edit(lambda d: d.update(checks=[])),
            "21 checks": json.dumps(verifier([(f"c{i}", PASS) for i in range(21)])),
            "check not an object": edit(lambda d: d.update(checks=["lint"])),
            "check with an extra key": edit(lambda d: d["checks"][0].update(extra=1)),
            "check without argv": edit(lambda d: d["checks"][0].pop("argv")),
            "empty id": edit(lambda d: d["checks"][0].update(id="")),
            "lone surrogate id": json.dumps(verifier([("\ud800", PASS)])),
            "empty argv": edit(lambda d: d["checks"][0].update(argv=[])),
            "argv item not a string": edit(lambda d: d["checks"][0].update(argv=[1])),
            "argv with a NUL": edit(lambda d: d["checks"][0].update(argv=[PY, "a\u0000b"])),
            "timeout zero": edit(lambda d: d.update(timeout_seconds=0)),
            "timeout above the cap": edit(lambda d: d.update(timeout_seconds=601)),
            "timeout is a boolean": edit(lambda d: d.update(timeout_seconds=True)),
            "timeout is a float": edit(lambda d: d.update(timeout_seconds=1.5)),
            "timeout is a string": edit(lambda d: d.update(timeout_seconds="5")),
            "block limit zero": edit(lambda d: d.update(max_consecutive_blocks=0)),
            "block limit above the cap": edit(lambda d: d.update(max_consecutive_blocks=21)),
            "block limit is a boolean": edit(lambda d: d.update(max_consecutive_blocks=True)),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                raw = text if isinstance(text, bytes) else text.encode("utf-8")
                with self.assertRaises(ValueError):
                    parse_config(raw)


class HookCase(unittest.TestCase):
    """Each test gets a temp project, a temp home, a temp directory for the block counter and a neutral cwd."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.project = self.dir / "project"
        self.home = self.dir / "home"
        self.tmp = self.dir / "tmp"
        self.elsewhere = self.dir / "elsewhere"
        for folder in (self.project, self.home, self.tmp, self.elsewhere):
            folder.mkdir()
        patcher = patch.object(tempfile, "tempdir", str(self.tmp))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.env = {"CLAUDE_PROJECT_DIR": str(self.project)}

    def write_config(self, data, root=None):
        """Write the verifier config (a dict is dumped as JSON, a str is written as is) and return its bytes."""
        text = data if isinstance(data, str) else json.dumps(data)
        path = (root or self.project) / ".inonu" / "verify.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = text.encode("utf-8")
        path.write_bytes(raw)
        return raw

    def trust(self, root=None):
        code, out, err = run_trust(root or self.project, self.home, yes=True)
        self.assertEqual((0, ""), (code, err))
        return out

    def stop(self, body="{}", environ=None, process_cwd=None):
        environ = self.env if environ is None else environ
        return run_stop(body, environ, self.home, process_cwd=process_cwd or self.elsewhere)

    def trust_file(self):
        return self.home / ".inonu-harness" / "hook-trust.json"

    def trust_record(self):
        return json.loads(self.trust_file().read_text(encoding="utf-8"))

    def config_key(self, root=None):
        return str(((root or self.project) / ".inonu" / "verify.json").resolve())

    def assert_untouched(self, name):
        self.assertFalse((self.project / name).exists(), f"{name} was created, so a check ran")


class ProjectDiscoveryTests(HookCase):
    def test_claude_project_dir_wins_over_the_cwd_field(self):
        self.write_config(verifier([("lint", FAIL)]))
        self.trust()
        code, err = self.stop(json.dumps({"cwd": str(self.elsewhere)}))
        self.assertEqual(2, code, err)

    def test_cwd_field_is_used_when_the_env_var_is_unset(self):
        self.write_config(verifier([("lint", FAIL)]))
        self.trust()
        code, err = self.stop(json.dumps({"cwd": str(self.project)}), environ={})
        self.assertEqual(2, code, err)

    def test_process_directory_is_the_last_resort(self):
        self.write_config(verifier([("lint", FAIL)]), root=self.elsewhere)
        self.trust(self.elsewhere)
        for body in ('{"cwd": "no-such-directory-for-hook-test"}', json.dumps({"cwd": str(self.dir / "file.txt")})):
            with self.subTest(body=body):
                (self.dir / "file.txt").write_text("not a directory", encoding="utf-8")
                code, _ = self.stop(body, environ={"CLAUDE_PROJECT_DIR": ""})
                self.assertEqual(2, code)

    def test_ancestors_are_not_searched(self):
        self.write_config(verifier([("lint", FAIL)]), root=self.dir)
        self.assertEqual((0, ""), self.stop())


class NoConfigTests(HookCase):
    def test_no_config_is_a_silent_exit_zero_that_writes_nothing(self):
        self.assertEqual((0, ""), self.stop())
        self.assertFalse(self.trust_file().exists())
        self.assertFalse((self.tmp / hook.STATE_DIRECTORY).exists())


class TrustGateTests(HookCase):
    def test_untrusted_config_exits_one_and_runs_nothing(self):
        self.write_config(verifier([("touch", touch_check("ran"))]))
        code, err = self.stop()
        self.assertEqual(1, code)
        self.assertIn("not trusted", err)
        self.assertIn("hook trust", err)
        self.assert_untouched("ran")

    def test_changed_config_exits_one_and_runs_nothing(self):
        self.write_config(verifier([("ok", PASS)]))
        self.trust()
        self.write_config(verifier([("touch", touch_check("ran"))]))
        code, err = self.stop()
        self.assertEqual(1, code)
        self.assertIn("changed since it was trusted", err)
        self.assert_untouched("ran")

    def test_copy_of_a_trusted_config_in_another_directory_is_not_trusted(self):
        raw = self.write_config(verifier([("touch", touch_check("ran"))]))
        self.trust()
        (self.elsewhere / ".inonu").mkdir()
        (self.elsewhere / ".inonu" / "verify.json").write_bytes(raw)
        code, _ = self.stop(environ={"CLAUDE_PROJECT_DIR": str(self.elsewhere)})
        self.assertEqual(1, code)
        self.assert_untouched("ran")

    def test_unreadable_trust_file_exits_one_and_runs_nothing(self):
        self.write_config(verifier([("touch", touch_check("ran"))]))
        self.trust_file().parent.mkdir(parents=True)
        duplicated = '{"schema_version": 1, "trusted": {}, "trusted": {}}'
        broken = (
            "{", duplicated, "[]", '{"schema_version": 2, "trusted": {}}',
            '{"schema_version": true, "trusted": {}}', '{"schema_version": 1, "trusted": {"key": 5}}',
        )
        for text in broken:
            with self.subTest(trust=text):
                self.trust_file().write_text(text, encoding="utf-8")
                code, err = self.stop()
                self.assertEqual(1, code)
                self.assertIn("trust file cannot be read or parsed", err)
                self.assert_untouched("ran")
        self.trust_file().unlink()
        self.trust_file().mkdir()
        code, err = self.stop()
        self.assertEqual(1, code)
        self.assert_untouched("ran")

    def test_trusted_passing_config_exits_zero_and_the_hook_never_writes_the_trust_file(self):
        self.write_config(verifier([("ok", PASS)]))
        self.trust()
        before = self.trust_file().read_bytes()
        self.assertEqual((0, ""), self.stop())
        self.assertEqual(before, self.trust_file().read_bytes())


class TrustCommandTests(HookCase):
    def test_preview_lists_every_check_and_writes_nothing(self):
        self.write_config(verifier([("lint", [PY, "-c", "print(1)"]), ("tests", PASS)]))
        code, out, err = run_trust(self.project, self.home, yes=False)
        self.assertEqual((0, ""), (code, err))
        self.assertIn('"lint"', out)
        self.assertIn(json.dumps([PY, "-c", "print(1)"]), out)
        self.assertIn('"tests"', out)
        self.assertIn("not recorded", out)
        self.assertFalse(self.trust_file().exists())
        self.assertFalse((self.home / ".inonu-harness").exists())

    def test_yes_records_the_digest_of_the_exact_bytes_atomically(self):
        raw = self.write_config(verifier([("lint", PASS)]))
        code, out, err = run_trust(self.project, self.home, yes=True)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("trusted", out)
        self.assertNotIn("not recorded", out)
        self.assertEqual(
            {"schema_version": 1, "trusted": {self.config_key(): hashlib.sha256(raw).hexdigest()}},
            self.trust_record(),
        )
        self.assertEqual([self.trust_file().name], [path.name for path in self.trust_file().parent.iterdir()])

    def test_recording_a_second_config_keeps_the_first_record(self):
        other = self.dir / "other"
        other.mkdir()
        self.write_config(verifier([("a", PASS)]))
        self.trust()
        self.write_config(verifier([("b", PASS)]), root=other)
        self.trust(other)
        self.assertEqual({self.config_key(), self.config_key(other)}, set(self.trust_record()["trusted"]))

    def test_untrust_removes_the_record_and_the_hook_stops_running_the_config(self):
        self.write_config(verifier([("ok", PASS)]))
        self.trust()
        self.assertEqual((0, ""), self.stop())
        code, out, err = run_untrust(self.project, self.home)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("removed", out)
        self.assertEqual({}, self.trust_record()["trusted"])
        self.assertEqual(1, self.stop()[0])

    def test_untrust_without_a_record_changes_nothing(self):
        code, out, err = run_untrust(self.project, self.home)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("nothing was removed", out)
        self.assertFalse(self.trust_file().exists())

    def test_untrust_still_removes_the_record_after_the_config_is_deleted(self):
        self.write_config(verifier([("ok", PASS)]))
        self.trust()
        (self.project / ".inonu" / "verify.json").unlink()
        code, _, err = run_untrust(self.project, self.home)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual({}, self.trust_record()["trusted"])

    def test_missing_or_invalid_config_is_refused_with_exit_two(self):
        code, out, err = run_trust(self.project, self.home, yes=True)
        self.assertEqual((2, ""), (code, out))
        self.assertIn("nothing to trust", err)
        self.write_config("{")
        code, out, err = run_trust(self.project, self.home, yes=True)
        self.assertEqual((2, ""), (code, out))
        self.assertIn("invalid", err)
        self.assertFalse(self.trust_file().exists())

    def test_broken_trust_file_is_refused_and_not_overwritten(self):
        self.write_config(verifier([("ok", PASS)]))
        self.trust_file().parent.mkdir(parents=True)
        self.trust_file().write_text("{", encoding="utf-8")
        code, out, _ = run_trust(self.project, self.home, yes=True)
        self.assertEqual((2, ""), (code, out))
        self.assertEqual("{", self.trust_file().read_text(encoding="utf-8"))

    def test_trust_directory_that_cannot_be_created_exits_two(self):
        self.write_config(verifier([("ok", PASS)]))
        (self.home / ".inonu-harness").write_text("a file where the directory belongs", encoding="utf-8")
        code, out, err = run_trust(self.project, self.home, yes=True)
        self.assertEqual((2, ""), (code, out))
        self.assertIn("could not be written", err)


class ExecutionTests(HookCase):
    def test_failing_check_blocks_with_attempt_id_exit_code_and_tail(self):
        self.write_config(verifier([
            ("lint", [PY, "-c", "print('needle-7'); raise SystemExit(3)"]),
            ("ok", PASS),
        ]))
        self.trust()
        code, err = self.stop()
        self.assertEqual(2, code)
        self.assertIn("attempt 1 of 3", err)
        self.assertIn('"lint" exit 3', err)
        self.assertIn("needle-7", err)
        self.assertNotIn('"ok"', err, "a passing check must not be listed")
        self.assertTrue(err.endswith("\n"))

    def test_every_check_passing_exits_zero_silently(self):
        self.write_config(verifier([("a", PASS), ("b", PASS)]))
        self.trust()
        self.assertEqual((0, ""), self.stop())

    def test_checks_run_in_the_project_directory_with_stdin_closed(self):
        (self.project / "marker").write_text("1", encoding="utf-8")
        probe = [
            PY, "-c",
            "import pathlib, sys; sys.exit(0 if pathlib.Path('marker').exists() and sys.stdin.read() == '' else 1)",
        ]
        self.write_config(verifier([("probe", probe)]))
        self.trust()
        self.assertEqual((0, ""), self.stop())

    def test_argv_is_passed_without_a_shell(self):
        arg = "a; exit 9 && echo $HOME"
        probe = [PY, "-c", "import sys; sys.exit(0 if sys.argv[1] == " + repr(arg) + " else 1)", arg]
        self.write_config(verifier([("probe", probe)]))
        self.trust()
        self.assertEqual((0, ""), self.stop())

    def test_check_that_cannot_start_is_an_infrastructure_error(self):
        self.write_config(verifier([("ghost", ["no-such-command-for-hook-test"])]))
        self.trust()
        code, err = self.stop()
        self.assertEqual(1, code)
        self.assertIn('"ghost" could not be started', err)

    def test_timeout_kills_the_whole_process_tree_and_reports_timed_out(self):
        (self.project / "parent.py").write_text(TREE_PARENT, encoding="utf-8")
        (self.project / "grand.py").write_text(TICKER, encoding="utf-8")
        self.write_config(verifier([("tree", [PY, str(self.project / "parent.py"), str(self.project)])], timeout=2))
        self.trust()
        code, err = self.stop()
        self.assertEqual(2, code)
        self.assertIn('"tree" timed out', err)
        ticks = self.project / "ticks"
        self.assertTrue(ticks.exists(), "the grandchild must be running before the kill")
        size = ticks.stat().st_size
        time.sleep(0.6)  # a surviving grandchild appends every 50 ms
        self.assertEqual(size, ticks.stat().st_size, "a process outlived the timed-out check")

    def test_a_spent_budget_stops_later_checks_from_running(self):
        self.write_config(verifier([
            ("slow", [PY, "-c", "import time; time.sleep(30)"]),
            ("later", touch_check("ran")),
        ], timeout=2))
        self.trust()
        code, err = self.stop()
        self.assertEqual(2, code)
        self.assertIn('"slow" timed out', err)
        self.assertIn('"later" timed out', err)
        self.assert_untouched("ran")

    def test_credential_looking_tail_is_replaced_and_never_printed(self):
        leak = [PY, "-c", f"print({CREDENTIAL!r}); raise SystemExit(1)"]
        self.write_config(verifier([("leak", leak)]))
        self.trust()
        code, err = self.stop()
        self.assertEqual(2, code)
        self.assertNotIn(CREDENTIAL, err)
        self.assertIn("aws_access_key_id", err)
        self.assertIn("withheld", err)

    def test_message_is_capped_at_4000_characters(self):
        loud = [PY, "-c", "import sys; sys.stdout.write('x' * 3000); raise SystemExit(1)"]
        self.write_config(verifier([("one", loud), ("two", loud), ("three", loud)]))
        self.trust()
        code, err = self.stop()
        self.assertEqual(2, code)
        self.assertLessEqual(len(err), 4000)
        self.assertIn("[message truncated]", err)

    def test_non_ascii_tail_is_escaped_for_a_narrow_stream_not_a_traceback(self):
        emit = [PY, "-c", "import sys; sys.stdout.buffer.write('café'.encode('utf-8')); raise SystemExit(1)"]
        self.write_config(verifier([("accent", emit)]))
        self.trust()
        raw = io.BytesIO()
        narrow = io.TextIOWrapper(raw, encoding="ascii")
        stdin = io.TextIOWrapper(io.BytesIO(b"{}"), encoding="utf-8")
        with patch("sys.stdin", stdin), patch("sys.stderr", narrow), patch.dict(os.environ, self.env):
            code = main(["hook", "stop", "--home", str(self.home)])
            narrow.flush()
        self.assertEqual(2, code)
        self.assertIn("caf\\xe9", raw.getvalue().decode("ascii"))


class BlockCounterTests(HookCase):
    def test_limit_allows_the_stop_then_resets_the_counter(self):
        self.write_config(verifier([("lint", FAIL)], blocks=2))
        self.trust()
        first, second = self.stop(), self.stop()
        self.assertEqual(2, first[0])
        self.assertIn("attempt 1 of 2", first[1])
        self.assertEqual(2, second[0])
        self.assertIn("attempt 2 of 2", second[1])
        code, err = self.stop()
        self.assertEqual(0, code)
        self.assertIn("2 consecutive blocks reached", err)
        self.assertEqual(1, err.count("\n"), "the limit note is one line")
        code, err = self.stop()
        self.assertEqual(2, code)
        self.assertIn("attempt 1 of 2", err)

    def test_a_passing_run_resets_the_counter(self):
        flag = [PY, "-c", "import pathlib, sys; sys.exit(0 if pathlib.Path('ok').exists() else 1)"]
        self.write_config(verifier([("flag", flag)], blocks=3))
        self.trust()
        self.assertIn("attempt 1 of 3", self.stop()[1])
        (self.project / "ok").write_text("1", encoding="utf-8")
        self.assertEqual((0, ""), self.stop())
        (self.project / "ok").unlink()
        self.assertIn("attempt 1 of 3", self.stop()[1])

    def test_counter_is_one_small_file_per_session_and_config_in_the_temp_directory(self):
        self.write_config(verifier([("lint", FAIL)], blocks=5))
        self.trust()
        self.stop(json.dumps({"session_id": "one"}))
        self.assertIn("attempt 1 of 5", self.stop(json.dumps({"session_id": "two"}))[1])
        self.assertIn("attempt 2 of 5", self.stop(json.dumps({"session_id": "one"}))[1])
        files = sorted((self.tmp / hook.STATE_DIRECTORY).glob("*.json"))
        self.assertEqual(2, len(files))
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{16}", path.stem) for path in files))

    def test_a_counter_that_cannot_be_stored_never_blocks_so_an_agent_is_not_trapped(self):
        self.write_config(verifier([("lint", FAIL)], blocks=3))
        self.trust()
        (self.tmp / hook.STATE_DIRECTORY).write_text("a file where the directory belongs", encoding="utf-8")
        for _ in range(4):
            code, err = self.stop()
            self.assertEqual(1, code)  # non-blocking: the host lets the agent stop
            self.assertIn("the block limit cannot be enforced; this stop is allowed", err)
            self.assertNotIn(str(self.dir), err)

    def test_malformed_counter_reads_as_zero(self):
        self.write_config(verifier([("lint", FAIL)], blocks=3))
        self.trust()
        self.stop()
        (counter,) = (self.tmp / hook.STATE_DIRECTORY).glob("*.json")
        for text in ("{", '{"consecutive_blocks": -1}', '{"consecutive_blocks": true}', "[]"):
            with self.subTest(counter=text):
                counter.write_text(text, encoding="utf-8")
                self.assertIn("attempt 1 of 3", self.stop()[1])


class StopInputAndErrorTests(HookCase):
    def test_bad_stdin_is_tolerated_as_an_empty_object(self):
        self.write_config(verifier([("ok", PASS)]))
        self.trust()
        for body in ("", "{", "[1]", "null", '"text"', '{"session_id": 5}', '{"a": 1, "a": 2}'):
            with self.subTest(body=body):
                self.assertEqual((0, ""), self.stop(body))

    def test_config_size_limit_is_exactly_64_kib(self):
        body = json.dumps(verifier([("ok", PASS)]))
        self.write_config(body + " " * (CONFIG_LIMIT - len(body)))
        self.trust()
        self.assertEqual((0, ""), self.stop())
        self.write_config(body + " " * (CONFIG_LIMIT - len(body) + 1))
        code, err = self.stop()
        self.assertEqual(1, code)
        self.assertIn("larger than 64 KiB", err)

    def test_unexpected_exception_exits_one_without_a_traceback(self):
        self.write_config(verifier([("ok", PASS)]))
        self.trust()
        with patch.object(hook, "parse_config", side_effect=RuntimeError("internal-detail")):
            self.assertEqual((1, UNEXPECTED), self.stop())


class CliHookTests(HookCase):
    def run_main(self, argv, stdin_bytes=b"{}"):
        out, err = io.StringIO(), io.StringIO()
        stdin = io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding="utf-8")
        with patch("sys.stdin", stdin), patch("sys.stdout", out), patch("sys.stderr", err), \
                patch.dict(os.environ, self.env):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_hook_stop_keeps_stdout_empty_and_maps_the_exit_code(self):
        self.write_config(verifier([("lint", FAIL)]))
        self.trust()
        body = json.dumps({"session_id": "cli"}).encode("utf-8")
        code, out, err = self.run_main(["hook", "stop", "--home", str(self.home)], body)
        self.assertEqual((2, ""), (code, out))
        self.assertIn("attempt 1 of 3", err)

    def test_hook_stop_tolerates_invalid_utf8_on_stdin(self):
        self.assertEqual((0, "", ""), self.run_main(["hook", "stop", "--home", str(self.home)], b"\xff\xfe{"))

    def test_hook_stop_unexpected_error_is_exit_one_with_the_generic_message(self):
        self.write_config(verifier([("ok", PASS)]))
        self.trust()
        with patch.object(hook, "parse_config", side_effect=RuntimeError("internal-detail")):
            code, out, err = self.run_main(["hook", "stop", "--home", str(self.home)])
        self.assertEqual((1, "", UNEXPECTED), (code, out, err))

    def test_hook_trust_and_untrust_through_the_cli(self):
        self.write_config(verifier([("lint", PASS)]))
        code, out, _ = self.run_main(["hook", "trust", "--root", str(self.project), "--home", str(self.home)])
        self.assertEqual(0, code)
        self.assertIn("not recorded", out)
        self.assertFalse(self.trust_file().exists())
        code, out, _ = self.run_main(
            ["hook", "trust", "--root", str(self.project), "--home", str(self.home), "--yes"],
        )
        self.assertEqual(0, code)
        self.assertIn("trusted", out)
        code, out, _ = self.run_main(["hook", "untrust", "--root", str(self.project), "--home", str(self.home)])
        self.assertEqual(0, code)
        self.assertIn("removed", out)

    def test_hook_trust_refusal_is_exit_two_without_a_traceback(self):
        self.write_config("{")
        code, out, err = self.run_main(["hook", "trust", "--root", str(self.project), "--home", str(self.home), "--yes"])
        self.assertEqual(2, code)
        self.assertEqual("", out)
        self.assertNotIn("Traceback", err)


class ReviewRegressionTests(HookCase):
    def test_a_config_reached_through_a_link_to_another_project_never_runs(self):
        other = self.dir / "other"
        other.mkdir()
        self.write_config(verifier([("mark", touch_check("ran"))]), root=other)
        self.trust(root=other)
        link = self.project / ".inonu"
        try:
            os.symlink(other / ".inonu", link, target_is_directory=True)
        except (OSError, NotImplementedError):
            made = os.name == "nt" and subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(other / ".inonu")], capture_output=True, check=False,
            ).returncode == 0
            if not made:
                self.skipTest("directory links are not available on this host")
        code, err = self.stop()
        self.assertEqual(1, code)
        self.assertIn("must be a file inside the project", err)
        self.assert_untouched("ran")
        self.assertFalse((other / "ran").exists())

    def test_a_credential_that_starts_before_the_shown_tail_is_still_withheld(self):
        token = "gh" + "p_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        code_text = f"import sys; sys.stdout.write('x' * 100 + {token!r} + 'y' * 1470); raise SystemExit(1)"
        self.write_config(verifier([("leaky", [PY, "-c", code_text])]))
        self.trust()
        status, err = self.stop()
        self.assertEqual(2, status)
        self.assertIn("output withheld: credential-like text matched github_token", err)
        for start in range(len(token) - 7):
            self.assertNotIn(token[start:start + 8], err)

    def test_control_characters_in_check_output_are_escaped(self):
        code_text = "import sys; sys.stdout.write(chr(27) + ']0;SPOOF' + chr(7) + chr(27) + '[31mRED'); raise SystemExit(1)"
        self.write_config(verifier([("noisy", [PY, "-c", code_text])]))
        self.trust()
        status, err = self.stop()
        self.assertEqual(2, status)
        self.assertNotIn(chr(27), err)
        self.assertNotIn(chr(7), err)
        self.assertIn(chr(92) + "x1b", err)
        self.assertIn("RED", err)

    def test_a_check_that_floods_its_output_is_stopped_at_the_size_limit(self):
        flood = "import sys, time; sys.stdout.write('z' * 3000000); sys.stdout.flush(); time.sleep(60)"
        self.write_config(verifier([("flood", [PY, "-c", flood])], timeout=120))
        self.trust()
        began = time.monotonic()
        with patch.object(hook, "OUTPUT_LIMIT_BYTES", 1024 * 1024):
            status, err = self.stop()
        self.assertEqual(2, status)
        self.assertLess(time.monotonic() - began, 30)
        self.assertIn("output limit", err)

    def test_the_hook_reads_at_most_one_mebibyte_of_stdin(self):
        from inonu_harness import cli

        class Stdin:
            buffer = io.BytesIO(b"{" + b" " * (3 * 1024 * 1024) + b"}")

        with patch.object(sys, "stdin", Stdin):
            self.assertLessEqual(len(cli._read_stdin()), 1024 * 1024)


class EndToEndTests(unittest.TestCase):
    def test_trust_then_stop_through_the_module_runner(self):
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        project, home, tmp, work = base / "project", base / "home", base / "tmp", base / "work"
        for folder in (project, home, tmp, work):
            folder.mkdir()
        (project / ".inonu").mkdir()
        (project / ".inonu" / "verify.json").write_text(
            json.dumps(verifier([("lint", [PY, "-c", "print('e2e-tail'); raise SystemExit(1)"])])), encoding="utf-8",
        )
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(project),
            "PYTHONPATH": str(ROOT),
            "TMPDIR": str(tmp), "TEMP": str(tmp), "TMP": str(tmp),  # keep the block counter out of the real temp
        }
        trusted = subprocess.run(
            [PY, "-m", "inonu_harness", "hook", "trust", "--root", str(project), "--home", str(home), "--yes"],
            cwd=work, env=env, capture_output=True, timeout=60, check=False,
        )
        self.assertEqual(0, trusted.returncode, trusted.stderr)
        self.assertIn(b"trusted", trusted.stdout)
        stopped = subprocess.run(
            [PY, "-m", "inonu_harness", "hook", "stop", "--home", str(home)],
            input=json.dumps({"session_id": "e2e", "cwd": str(work)}).encode("utf-8"),
            cwd=work, env=env, capture_output=True, timeout=60, check=False,
        )
        err = stopped.stderr.decode("utf-8", errors="replace")
        self.assertEqual(2, stopped.returncode, err)
        self.assertEqual(b"", stopped.stdout)
        self.assertIn("attempt 1 of 3", err)
        self.assertIn('"lint" exit 1', err)
        self.assertIn("e2e-tail", err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
