import copy
import io
import json
from io import StringIO
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from inonu_harness.cli import main
from inonu_harness.loop import parse_spec, run_loop

PY = sys.executable
PASS = [PY, "-c", "pass"]
FAIL = [PY, "-c", "raise SystemExit(1)"]
LOG_FIELDS = {
    "iteration", "started_at", "ended_at", "step", "checks", "newly_passing", "regressed",
    "failing_signature", "tree_hash", "decision", "stop_reason",
}
PARENT = """import pathlib, subprocess, sys, time
d = pathlib.Path(sys.argv[1])
subprocess.Popen([sys.executable, str(d / 'grand.py'), str(d)])
time.sleep(60)
"""
SPAWN = """import pathlib, subprocess, sys, time
d = pathlib.Path(sys.argv[1])
subprocess.Popen([sys.executable, str(d / 'grand.py'), str(d)])
deadline = time.monotonic() + 20
while not (d / 'ticks').exists() and time.monotonic() < deadline:
    time.sleep(0.02)
"""
MIDDLE = """import pathlib, subprocess, sys
d = pathlib.Path(sys.argv[1])
subprocess.Popen([sys.executable, str(d / 'grand.py'), str(d)])
"""
ORPHANING_PARENT = """import pathlib, subprocess, sys, time
d = pathlib.Path(sys.argv[1])
subprocess.Popen([sys.executable, str(d / 'middle.py'), str(d)])
time.sleep(60)
"""
GROW = "import pathlib; p = pathlib.Path('draft.md'); p.write_text(p.read_text() + 'x' if p.exists() else 'x')"
STAGE = (
    "import pathlib, subprocess; p = pathlib.Path('staged.txt'); "
    "p.write_text(p.read_text() + 'x' if p.exists() else 'x'); subprocess.run(['git', 'add', 'staged.txt'], check=True)"
)
GRAND = """import pathlib, sys, time
d = pathlib.Path(sys.argv[1])
while True:
    with open(d / 'ticks', 'a') as ticks:
        ticks.write('x')
    time.sleep(0.05)
"""


def spec_data(step, checks, log="run.jsonl", **limits):
    return {
        "step": list(step),
        "checks": [{"id": check_id, "argv": list(argv)} for check_id, argv in checks],
        "limits": {
            "max_iterations": limits.get("max_iterations", 5),
            "iteration_timeout_seconds": limits.get("iteration_timeout_seconds", 30),
            "total_timeout_seconds": limits.get("total_timeout_seconds", 120),
            "stagnation_iterations": limits.get("stagnation_iterations", 5),
        },
        "log": log,
    }


def spec_in(directory, step, checks, **kwargs):
    return parse_spec(spec_data(step, checks, **kwargs), Path(directory))


def read_log(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


class LoopRunnerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)

    def write_json(self, path, data):
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def run_cli(self, spec_path):
        output, error = StringIO(), StringIO()
        with patch("sys.stdout", output), patch("sys.stderr", error):
            code = main(["loop", "run", spec_path])
        return code, output.getvalue()

    def test_success_after_three_iterations(self):
        step = [PY, "-c", "import pathlib as p; f = p.Path('count'); f.write_text(str(int(f.read_text()) + 1 if f.exists() else 1))"]
        check = [PY, "-c", "import pathlib as p, sys; f = p.Path('count'); sys.exit(0 if f.exists() and int(f.read_text()) >= 3 else 1)"]
        spec = spec_in(self.dir, step, [("done", check)], max_iterations=10)
        summary = run_loop(spec)
        self.assertEqual(("verified_done", 3), (summary["status"], summary["iterations"]))
        self.assertEqual({"done": True}, summary["passes"])
        records = read_log(spec.log)
        self.assertEqual([0, 1, 2, 3], [record["iteration"] for record in records])
        self.assertIsNone(records[0]["step"])
        self.assertEqual(["done"], records[-1]["newly_passing"])
        self.assertEqual(("stop", "verified_done"), (records[-1]["decision"], records[-1]["stop_reason"]))

    def test_already_passing_baseline_runs_no_step(self):
        spec = spec_in(self.dir, [PY, "-c", "open('ran', 'w').close()"], [("done", PASS)])
        summary = run_loop(spec)
        self.assertEqual(("verified_done", 0), (summary["status"], summary["iterations"]))
        self.assertFalse((self.dir / "ran").exists())
        self.assertEqual(1, len(read_log(spec.log)))

    def test_max_iterations_stops_after_the_limit(self):
        spec = spec_in(self.dir, PASS, [("done", FAIL)], max_iterations=2, stagnation_iterations=5)
        summary = run_loop(spec)
        self.assertEqual(("max_iterations", 2), (summary["status"], summary["iterations"]))
        self.assertEqual([0, 1, 2], [record["iteration"] for record in read_log(spec.log)])

    def test_total_budget_kills_the_step_and_stops_wall_clock(self):
        spec = spec_in(
            self.dir, [PY, "-c", "import time; time.sleep(30)"], [("done", FAIL)],
            max_iterations=9, iteration_timeout_seconds=60, total_timeout_seconds=2,
        )
        summary = run_loop(spec)
        self.assertEqual(("wall_clock", 1), (summary["status"], summary["iterations"]))
        records = read_log(spec.log)
        self.assertTrue(records[1]["step"]["timed_out"])
        self.assertTrue(records[1]["checks"][0]["not_run"])
        self.assertFalse(records[1]["checks"][0]["timed_out"])

    def test_step_timeout_kills_its_grandchild(self):
        (self.dir / "parent.py").write_text(PARENT, encoding="utf-8")
        (self.dir / "grand.py").write_text(GRAND, encoding="utf-8")
        spec = spec_in(
            self.dir, [PY, str(self.dir / "parent.py"), str(self.dir)], [("done", FAIL)],
            max_iterations=1, iteration_timeout_seconds=2,
        )
        summary = run_loop(spec)
        self.assertEqual("max_iterations", summary["status"])
        self.assertTrue(read_log(spec.log)[1]["step"]["timed_out"])
        ticks = self.dir / "ticks"
        self.assertTrue(ticks.exists(), "the grandchild must be running before the kill")
        size = ticks.stat().st_size
        time.sleep(0.5)  # a surviving grandchild would keep appending every 50 ms
        self.assertEqual(size, ticks.stat().st_size)

    def test_stagnation_after_exactly_k_iterations(self):
        spec = spec_in(self.dir, PASS, [("done", FAIL)], max_iterations=10, stagnation_iterations=3)
        summary = run_loop(spec)
        self.assertEqual(("stagnation", 3), (summary["status"], summary["iterations"]))
        self.assertEqual([0, 1, 2, 3], [record["iteration"] for record in read_log(spec.log)])

    @unittest.skipUnless(shutil.which("git"), "git is required for the tree hash")
    def test_tree_change_resets_stagnation(self):
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        spec = spec_in(
            self.dir, [PY, "-c", "open('new.txt', 'w').close()"], [("done", FAIL)],
            max_iterations=10, stagnation_iterations=3,
        )
        summary = run_loop(spec)
        # The step creates new.txt in iteration 1, which resets the streak; stagnation then needs 3 more.
        self.assertEqual(("stagnation", 4), (summary["status"], summary["iterations"]))
        self.assertNotEqual(read_log(spec.log)[0]["tree_hash"], read_log(spec.log)[1]["tree_hash"])

    def test_regression_is_recorded_and_counts_as_failing(self):
        guard = [PY, "-c", "import os, sys; sys.exit(1 if os.path.exists('broken') else 0)"]
        # "never" keeps the loop running; a lone passing guard would stop as verified_done at iteration 0.
        spec = spec_in(
            self.dir, [PY, "-c", "open('broken', 'w').close()"], [("guard", guard), ("never", FAIL)], max_iterations=2,
        )
        summary = run_loop(spec)
        self.assertEqual("max_iterations", summary["status"])
        self.assertEqual({"guard": False, "never": False}, summary["passes"])
        self.assertEqual([{"iteration": 1, "id": "guard"}], summary["regressions"])
        records = read_log(spec.log)
        self.assertEqual(["guard"], records[0]["newly_passing"])
        self.assertEqual(["guard"], records[1]["regressed"])

    def test_check_that_cannot_start_is_verifier_error_before_any_step(self):
        spec = spec_in(self.dir, [PY, "-c", "open('ran', 'w').close()"], [("done", ["no-such-command-for-loop-test"])])
        summary = run_loop(spec)
        self.assertEqual(("verifier_error", 0), (summary["status"], summary["iterations"]))
        self.assertFalse((self.dir / "ran").exists())

    def test_step_that_cannot_start_is_a_failed_iteration_not_verifier_error(self):
        spec = spec_in(self.dir, ["no-such-command-for-loop-test"], [("done", FAIL)], max_iterations=1)
        summary = run_loop(spec)
        self.assertEqual(("max_iterations", 1), (summary["status"], summary["iterations"]))
        step = read_log(spec.log)[1]["step"]
        self.assertEqual((None, False), (step["exit_code"], step["timed_out"]))

    def test_log_is_jsonl_without_argv_or_output(self):
        check = [PY, "-c", "print('OUTPUT-SECRET-7'); raise SystemExit(1)"]
        spec = spec_in(self.dir, [PY, "-c", "pass", "ARGV-SECRET-7"], [("done", check)], log="logs/run.jsonl", max_iterations=1)
        run_loop(spec)
        text = spec.log.read_text(encoding="utf-8")
        records = [json.loads(line) for line in text.splitlines()]
        self.assertEqual(2, len(records))
        for record in records:
            self.assertEqual(LOG_FIELDS, set(record))
        self.assertNotIn("SECRET", text)
        self.assertNotIn(str(self.dir), text)

    def test_cli_exit_codes_and_spec_relative_paths(self):
        spec_dir = self.dir / "spec-dir"
        spec_dir.mkdir()
        (spec_dir / "marker").write_text("1", encoding="utf-8")
        marker_check = [PY, "-c", "import os, sys; sys.exit(0 if os.path.exists('marker') else 1)"]

        code, output = self.run_cli(self.write_json(
            spec_dir / "ok.json", spec_data(PASS, [("done", marker_check)], log="out/run.jsonl"),
        ))
        self.assertEqual((0, "verified_done"), (code, json.loads(output)["status"]))
        self.assertTrue((spec_dir / "out" / "run.jsonl").exists())

        code, output = self.run_cli(self.write_json(
            spec_dir / "stop.json", spec_data(PASS, [("done", FAIL)], max_iterations=1),
        ))
        self.assertEqual((1, "max_iterations"), (code, json.loads(output)["status"]))

        code, output = self.run_cli(self.write_json(
            spec_dir / "missing.json", spec_data(PASS, [("done", ["no-such-command-for-loop-test"])]),
        ))
        self.assertEqual((1, "verifier_error"), (code, json.loads(output)["status"]))

    def test_every_invalid_spec_exits_two(self):
        base = spec_data([PY, "-c", "pass"], [("done", PASS)], max_iterations=2, stagnation_iterations=2)

        def mutate(change):
            data = copy.deepcopy(base)
            change(data)
            return json.dumps(data)

        (self.dir / "logdir").mkdir()
        duplicate = '{"log": "other.jsonl", ' + json.dumps(base)[1:]
        cases = {
            "not JSON": "{",
            "top-level list": "[]",
            "duplicate key": duplicate,
            "NaN limit": json.dumps(base).replace('"max_iterations": 2', '"max_iterations": NaN'),
            "unknown top-level key": mutate(lambda d: d.update(extra=1)),
            "missing checks": mutate(lambda d: d.pop("checks")),
            "missing limits": mutate(lambda d: d.pop("limits")),
            "unknown limit key": mutate(lambda d: d["limits"].update(extra=1)),
            "missing limit": mutate(lambda d: d["limits"].pop("stagnation_iterations")),
            "boolean limit": mutate(lambda d: d["limits"].update(max_iterations=True)),
            "float limit": mutate(lambda d: d["limits"].update(max_iterations=2.0)),
            "zero limit": mutate(lambda d: d["limits"].update(max_iterations=0)),
            "negative limit": mutate(lambda d: d["limits"].update(max_iterations=-1)),
            "max_iterations above cap": mutate(lambda d: d["limits"].update(max_iterations=1001)),
            "iteration timeout above cap": mutate(lambda d: d["limits"].update(iteration_timeout_seconds=86401)),
            "total timeout above cap": mutate(lambda d: d["limits"].update(total_timeout_seconds=604801)),
            "stagnation above cap": mutate(lambda d: d["limits"].update(stagnation_iterations=101)),
            "empty step": mutate(lambda d: d.update(step=[])),
            "non-string step item": mutate(lambda d: d.update(step=[1])),
            "empty step string": mutate(lambda d: d.update(step=[PY, ""])),
            "NUL in step": mutate(lambda d: d.update(step=[PY, "a\u0000b"])),
            "empty checks": mutate(lambda d: d.update(checks=[])),
            "empty check id": mutate(lambda d: d["checks"][0].update(id="")),
            "duplicate check id": mutate(lambda d: d["checks"].append(copy.deepcopy(d["checks"][0]))),
            "unknown check key": mutate(lambda d: d["checks"][0].update(extra=1)),
            "empty log": mutate(lambda d: d.update(log="")),
            "cwd is not a directory": mutate(lambda d: d.update(cwd="no-such-dir")),
            "log is a directory": mutate(lambda d: d.update(log="logdir")),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                spec_path = self.dir / "bad.json"
                spec_path.write_text(text, encoding="utf-8")
                code, _ = self.run_cli(str(spec_path))
                self.assertEqual(2, code)
        code, _ = self.run_cli(str(self.dir / "absent.json"))
        self.assertEqual(2, code)

    def assert_ticker_stopped(self):
        ticks = self.dir / "ticks"
        self.assertTrue(ticks.exists(), "the grandchild must have been running")
        size = ticks.stat().st_size
        time.sleep(0.6)  # a surviving ticker appends every 50 ms
        self.assertEqual(size, ticks.stat().st_size, "a process outlived the command that started it")

    def test_process_left_running_by_a_finished_step_is_killed(self):
        (self.dir / "spawn.py").write_text(SPAWN, encoding="utf-8")
        (self.dir / "grand.py").write_text(GRAND, encoding="utf-8")
        spec = spec_in(self.dir, [PY, str(self.dir / "spawn.py"), str(self.dir)], [("done", FAIL)], max_iterations=1)
        summary = run_loop(spec)
        self.assertEqual("max_iterations", summary["status"])
        self.assert_ticker_stopped()

    def test_orphaned_grandchild_is_killed_when_the_step_times_out(self):
        for name, body in (("parent.py", ORPHANING_PARENT), ("middle.py", MIDDLE), ("grand.py", GRAND)):
            (self.dir / name).write_text(body, encoding="utf-8")
        spec = spec_in(
            self.dir, [PY, str(self.dir / "parent.py"), str(self.dir)], [("done", FAIL)],
            max_iterations=1, iteration_timeout_seconds=2,
        )
        run_loop(spec)
        self.assertTrue(read_log(spec.log)[1]["step"]["timed_out"])
        self.assert_ticker_stopped()

    def test_check_the_spent_budget_never_ran_is_not_a_regression(self):
        (self.dir / "ok").write_text("", encoding="utf-8")
        guard = [PY, "-c", "import pathlib, sys; sys.exit(0 if pathlib.Path('ok').exists() else 1)"]
        spec = spec_in(
            self.dir, [PY, "-c", "import time; time.sleep(30)"], [("guard", guard), ("other", FAIL)],
            max_iterations=9, iteration_timeout_seconds=60, total_timeout_seconds=2,
        )
        summary = run_loop(spec)
        self.assertEqual("wall_clock", summary["status"])
        self.assertEqual([], summary["regressions"])
        last = read_log(spec.log)[-1]
        self.assertEqual([True, True], [row["not_run"] for row in last["checks"]])
        self.assertEqual([], last["regressed"])

    def test_max_iterations_wins_when_stagnation_is_reached_in_the_same_iteration(self):
        spec = spec_in(self.dir, PASS, [("done", FAIL)], max_iterations=2, stagnation_iterations=2)
        summary = run_loop(spec)
        self.assertEqual(("max_iterations", 2), (summary["status"], summary["iterations"]))

    def test_stagnation_window_of_two_stops_at_iteration_two(self):
        spec = spec_in(self.dir, PASS, [("done", FAIL)], max_iterations=9, stagnation_iterations=2)
        summary = run_loop(spec)
        self.assertEqual(("stagnation", 2), (summary["status"], summary["iterations"]))

    def test_lone_surrogate_in_a_spec_string_is_invalid(self):
        data = spec_data(PASS, [(chr(0xD800), PASS)])
        with self.assertRaises(ValueError):
            parse_spec(data, self.dir)

    def test_cli_finishes_with_exit_0_under_a_narrow_stdout_encoding(self):
        spec_path = self.write_json(self.dir / "spec.json", spec_data(PASS, [("中文", PASS)]))
        raw = io.BytesIO()
        narrow = io.TextIOWrapper(raw, encoding="ascii")
        with patch("sys.stdout", narrow), patch("sys.stderr", StringIO()):
            code = main(["loop", "run", spec_path])
            narrow.flush()
        self.assertEqual(0, code)
        self.assertEqual("verified_done", json.loads(raw.getvalue().decode("ascii"))["status"])


@unittest.skipUnless(shutil.which("git"), "git is required")
class LoopTreeHashTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)

    def git(self, *args):
        subprocess.run(
            ["git", "-c", "user.email=t@example.test", "-c", "user.name=t", *args],
            cwd=self.dir, check=True, capture_output=True,
        )

    def repo_with_commit(self):
        self.git("init", "-q")
        (self.dir / "tracked.txt").write_text("t", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-q", "-m", "init")

    def test_content_change_of_an_untracked_file_is_progress(self):
        self.repo_with_commit()
        spec = spec_in(self.dir, [PY, "-c", GROW], [("done", FAIL)], max_iterations=6, stagnation_iterations=3)
        summary = run_loop(spec)
        self.assertEqual(("max_iterations", 6), (summary["status"], summary["iterations"]))

    def test_the_loop_log_inside_the_repository_does_not_defeat_stagnation(self):
        self.repo_with_commit()
        spec = spec_in(self.dir, PASS, [("done", FAIL)], max_iterations=9, stagnation_iterations=2)
        summary = run_loop(spec)
        self.assertEqual(("stagnation", 2), (summary["status"], summary["iterations"]))
        hashes = {record["tree_hash"] for record in read_log(spec.log)}
        self.assertEqual(1, len(hashes))

    def test_a_tracked_loop_log_does_not_defeat_stagnation(self):
        self.repo_with_commit()
        (self.dir / "run.jsonl").write_text("", encoding="utf-8")
        self.git("add", "run.jsonl")
        self.git("commit", "-q", "-m", "log")
        spec = spec_in(self.dir, PASS, [("done", FAIL)], max_iterations=9, stagnation_iterations=2)
        summary = run_loop(spec)
        self.assertEqual("stagnation", summary["status"])

    def test_staged_changes_in_a_repository_without_a_commit_are_progress(self):
        self.git("init", "-q")
        spec = spec_in(self.dir, [PY, "-c", STAGE], [("done", FAIL)], max_iterations=6, stagnation_iterations=3)
        summary = run_loop(spec)
        self.assertEqual(("max_iterations", 6), (summary["status"], summary["iterations"]))

    def test_unreadable_repository_is_unknown_and_never_stagnates(self):
        self.repo_with_commit()
        (self.dir / ".git" / "HEAD").write_text("garbage", encoding="utf-8")
        spec = spec_in(self.dir, PASS, [("done", FAIL)], max_iterations=4, stagnation_iterations=2)
        summary = run_loop(spec)
        self.assertEqual(("max_iterations", 4), (summary["status"], summary["iterations"]))
        self.assertEqual({None}, {record["tree_hash"] for record in read_log(spec.log)})


if __name__ == "__main__":
    unittest.main()
