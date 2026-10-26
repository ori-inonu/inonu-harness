import json
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from inonu_harness import baseline
from inonu_harness.baseline import compare_runs, gate_comparison, run_fixture
from inonu_harness.cli import main as cli_main


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "fixtures" / "baseline" / "offline-smoke.json"
ACCEPTANCE = [
    {"id": "offline-fixture-loaded", "passed": True},
    {"id": "unobserved-usage-remains-null", "passed": True},
]


class FixedClock:
    def __init__(self, *ticks):
        self._ticks = iter(ticks)

    def __call__(self):
        return next(self._ticks)


def make_result(execution_id, *, duration=0.2, **fixture_fields):
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fixture.update(fixture_fields)
    return run_fixture(
        fixture,
        execution_id=execution_id,
        clock=FixedClock(10.0, 10.0 + duration),
        version_source={"python": "3.test"},
    )


def gate_for(before, after, max_regression):
    return gate_comparison(before, after, compare_runs(before, after), max_regression)


class GateTests(unittest.TestCase):
    def test_identical_runs_pass(self):
        before = make_result("before", input_tokens=100, acceptance=ACCEPTANCE)
        after = make_result("after", input_tokens=100, acceptance=ACCEPTANCE)

        gate = gate_for(before, after, 0.1)

        self.assertEqual("pass", gate["status"])
        self.assertEqual([], gate["regressions"])
        self.assertEqual(0.1, gate["max_regression"])

    def test_acceptance_passed_before_and_failed_after_is_a_regression(self):
        after = make_result(
            "after",
            acceptance=[ACCEPTANCE[0], {"id": "unobserved-usage-remains-null", "passed": False}],
        )

        gate = gate_for(make_result("before", acceptance=ACCEPTANCE), after, 0.5)

        self.assertEqual("fail", gate["status"])
        self.assertEqual(
            [{
                "metric": "acceptance:unobserved-usage-remains-null",
                "before": True,
                "after": False,
                "reason": "criterion_failed",
            }],
            gate["regressions"],
        )

    def test_acceptance_that_disappears_is_a_regression(self):
        after = make_result("after", acceptance=ACCEPTANCE[:1])

        gate = gate_for(make_result("before", acceptance=ACCEPTANCE), after, 0.5)

        self.assertEqual("fail", gate["status"])
        self.assertEqual(
            [{
                "metric": "acceptance:unobserved-usage-remains-null",
                "before": True,
                "after": None,
                "reason": "criterion_missing",
            }],
            gate["regressions"],
        )

    def test_acceptance_that_never_passed_or_improved_is_not_a_regression(self):
        failing = [{"id": "offline-fixture-loaded", "passed": False}]
        passing = [{"id": "offline-fixture-loaded", "passed": True}]

        self.assertEqual("pass", gate_for(make_result("before", acceptance=failing), make_result("after", acceptance=failing), 0.0)["status"])
        self.assertEqual("pass", gate_for(make_result("before", acceptance=failing), make_result("after", acceptance=passing), 0.0)["status"])

    def test_token_increase_beyond_ratio_fails_and_within_ratio_passes(self):
        before = make_result("before", input_tokens=100)

        over = gate_for(before, make_result("after", input_tokens=126), 0.25)
        self.assertEqual("fail", over["status"])
        self.assertEqual(
            [{"metric": "input_tokens", "before": 100, "after": 126, "reason": "exceeds_max_regression"}],
            over["regressions"],
        )
        self.assertEqual("pass", gate_for(before, make_result("after", input_tokens=125), 0.25)["status"])
        self.assertEqual("fail", gate_for(before, make_result("after", input_tokens=101), 0.0)["status"])

    def test_cost_and_output_tokens_use_the_same_ratio(self):
        before = make_result("before", cost_usd=1.0, output_tokens=10)
        after = make_result("after", cost_usd=1.5, output_tokens=12)

        gate = gate_for(before, after, 0.25)

        self.assertEqual(["cost_usd"], [item["metric"] for item in gate["regressions"]])

    def test_zero_baseline_to_positive_fails(self):
        gate = gate_for(make_result("before", output_tokens=0), make_result("after", output_tokens=1), 5.0)

        self.assertEqual("fail", gate["status"])
        self.assertEqual("increase_from_zero", gate["regressions"][0]["reason"])

    def test_failure_and_block_counts_are_judged_by_list_length(self):
        before = make_result("before", failures=[], blocks=["bash"], tool_calls=["read", "edit"])
        after = make_result("after", failures=["timeout"], blocks=["bash", "bash"], tool_calls=["read", "edit"])

        gate = gate_for(before, after, 0.5)

        self.assertEqual(["failures", "blocks"], [item["metric"] for item in gate["regressions"]])

    def test_unavailable_tokens_and_cost_are_skipped_not_failed(self):
        before = make_result("before", input_tokens=None, cost_usd=None)
        after = make_result("after", input_tokens=999, cost_usd=99.0)

        gate = gate_for(before, after, 0.0)

        self.assertEqual("pass", gate["status"])
        self.assertEqual([], gate["regressions"])
        skipped = {item["metric"]: item["reason"] for item in gate["skipped"]}
        self.assertEqual("value_unavailable", skipped["input_tokens"])
        self.assertEqual("value_unavailable", skipped["cost_usd"])

    def test_elapsed_seconds_blow_up_alone_passes(self):
        gate = gate_for(make_result("before", duration=0.1), make_result("after", duration=500.0), 0.0)

        self.assertEqual("pass", gate["status"])
        self.assertIn({"metric": "elapsed_seconds", "reason": "not_judged"}, gate["skipped"])

    def test_skipped_names_every_metric_the_gate_did_not_judge(self):
        gate = gate_for(make_result("before"), make_result("after"), 0.1)

        self.assertEqual(
            {
                "elapsed_seconds",
                "runtime",
                "model",
                "input_tokens",
                "output_tokens",
                "cost_usd",
                "recoveries",
                "component_versions",
            },
            {item["metric"] for item in gate["skipped"]},
        )

    def test_task_or_config_mismatch_is_incomparable(self):
        after = make_result("after", config_id="another-config")

        gate = gate_for(make_result("before"), after, 0.1)

        self.assertEqual("incomparable", gate["status"])
        self.assertEqual([], gate["regressions"])
        self.assertEqual({"task_or_config_mismatch"}, {item["reason"] for item in gate["skipped"]})

    def test_invalid_max_regression_is_rejected(self):
        before = make_result("before")
        for value in (-0.1, float("nan"), float("inf"), True, "0.1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "max_regression"):
                    gate_comparison(before, before, compare_runs(before, before), value)

    def test_a_rise_of_exactly_the_ratio_passes_in_exact_arithmetic(self):
        for before_tokens, after_tokens, ratio in ((100, 115, 0.15), (100, 1150, 10.5), (7, 77, 10.0)):
            with self.subTest(before=before_tokens, after=after_tokens, ratio=ratio):
                gate = gate_for(
                    make_result("before", input_tokens=before_tokens),
                    make_result("after", input_tokens=after_tokens),
                    ratio,
                )
                self.assertEqual("pass", gate["status"])
        gate = gate_for(make_result("before", cost_usd=1.5), make_result("after", cost_usd=1.8), 0.2)
        self.assertEqual("pass", gate["status"])
        for before_tokens, after_tokens, ratio in ((100, 116, 0.15), (100, 1151, 10.5)):
            with self.subTest(before=before_tokens, after=after_tokens, ratio=ratio):
                gate = gate_for(
                    make_result("before", input_tokens=before_tokens),
                    make_result("after", input_tokens=after_tokens),
                    ratio,
                )
                self.assertEqual("fail", gate["status"])

    def test_a_doubled_subnormal_cost_is_caught(self):
        gate = gate_for(make_result("before", cost_usd=5e-324), make_result("after", cost_usd=1e-323), 0.5)
        self.assertEqual("fail", gate["status"])

    def test_identical_integers_above_2_pow_53_pass_at_zero_ratio(self):
        huge = 9007199254740993
        gate = gate_for(make_result("before", input_tokens=huge), make_result("after", input_tokens=huge), 0)
        self.assertEqual("pass", gate["status"])
        gate = gate_for(make_result("before", input_tokens=huge), make_result("after", input_tokens=huge + 1), 0)
        self.assertEqual("fail", gate["status"])

    def test_an_integer_beyond_float_range_is_invalid_input_not_a_crash(self):
        with self.assertRaises(ValueError):
            make_result("before", input_tokens=10**400)

    def test_changed_measurement_source_cannot_pass_silently(self):
        before = make_result("before", input_tokens=100, acceptance=ACCEPTANCE)
        estimated = {"input_tokens": {"kind": "estimate"}}
        after = make_result("after", input_tokens=10000, acceptance=ACCEPTANCE, measurement_sources=estimated)

        gate = gate_for(before, after, 0.1)

        self.assertEqual("incomparable", gate["status"])
        self.assertIn({"metric": "input_tokens", "reason": "source_incompatible"}, gate["skipped"])

    def test_a_certain_regression_wins_over_an_unjudgeable_metric(self):
        before = make_result("before", input_tokens=100, failures=[])
        after = make_result(
            "after", input_tokens=10000, failures=["boom"], measurement_sources={"input_tokens": {"kind": "estimate"}},
        )

        gate = gate_for(before, after, 0.1)

        self.assertEqual("fail", gate["status"])
        self.assertEqual(["failures"], [item["metric"] for item in gate["regressions"]])

    def test_unjudged_source_change_on_an_ungated_metric_does_not_block(self):
        before = make_result("before", runtime="a")
        after = make_result("after", runtime="b", measurement_sources={"runtime": {"kind": "estimate"}})
        self.assertEqual("pass", gate_for(before, after, 0.1)["status"])

    def test_duplicate_acceptance_ids_after_are_judged_together(self):
        before = make_result("before", acceptance=[{"id": "a", "passed": True}])
        after = make_result("after", acceptance=[{"id": "a", "passed": True}, {"id": "a", "passed": False}])
        gate = gate_for(before, after, 0.5)
        self.assertEqual(["acceptance:a"], [item["metric"] for item in gate["regressions"]])

    def test_duplicate_acceptance_ids_before_need_only_one_pass_to_count(self):
        before = make_result("before", acceptance=[{"id": "a", "passed": False}, {"id": "a", "passed": True}])
        after = make_result("after", acceptance=[{"id": "a", "passed": False}])
        gate = gate_for(before, after, 0.5)
        self.assertEqual(["acceptance:a"], [item["metric"] for item in gate["regressions"]])


class GateEntryPointTests(unittest.TestCase):
    def write_pair(self, directory, before, after):
        paths = []
        for name, result in (("before.json", before), ("after.json", after)):
            path = Path(directory) / name
            path.write_text(json.dumps(result), encoding="utf-8")
            paths.append(str(path))
        return paths

    def run_cli(self, argv):
        output, error = StringIO(), StringIO()
        with patch("sys.stdout", output), patch("sys.stderr", error):
            code = cli_main(argv)
        return code, output.getvalue(), error.getvalue()

    def test_regression_exits_1_and_prints_comparison_with_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(
                directory, make_result("before", input_tokens=100), make_result("after", input_tokens=200)
            )

            code, output, _ = self.run_cli(["baseline", "compare", before, after, "--max-regression", "0.1"])

        self.assertEqual(1, code)
        result = json.loads(output)
        self.assertEqual("fail", result["gate"]["status"])
        self.assertEqual(["input_tokens"], [item["metric"] for item in result["gate"]["regressions"]])
        self.assertIn("comparisons", result)

    def test_clean_run_exits_0_with_pass_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(directory, make_result("before"), make_result("after"))

            code, output, _ = self.run_cli(["baseline", "compare", before, after, "--max-regression", "0.1"])

        self.assertEqual(0, code)
        self.assertEqual("pass", json.loads(output)["gate"]["status"])

    def test_task_mismatch_exits_2_as_incomparable(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(
                directory, make_result("before"), make_result("after", config_id="another-config")
            )

            code, output, _ = self.run_cli(["baseline", "compare", before, after, "--max-regression", "0.1"])

        self.assertEqual(2, code)
        self.assertEqual("incomparable", json.loads(output)["gate"]["status"])

    def test_without_flag_regression_still_exits_0_with_unchanged_output(self):
        before_result = make_result("before", input_tokens=100)
        after_result = make_result("after", input_tokens=200)
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(directory, before_result, after_result)

            code, output, _ = self.run_cli(["baseline", "compare", before, after])

        self.assertEqual(0, code)
        self.assertNotIn("gate", json.loads(output))
        self.assertEqual(
            json.dumps(compare_runs(before_result, after_result), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            output,
        )

    def test_invalid_max_regression_exits_2_without_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(directory, make_result("before"), make_result("after"))
            for value in ("-0.1", "nan", "inf"):
                with self.subTest(value=value):
                    code, output, error = self.run_cli(["baseline", "compare", before, after, "--max-regression", value])

                    self.assertEqual(2, code)
                    self.assertEqual("", output)
                    self.assertIn("max_regression", error)

    def test_standalone_entry_point_agrees_with_cli_path(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(
                directory, make_result("before", input_tokens=100), make_result("after", input_tokens=200)
            )
            cli_code, cli_output, _ = self.run_cli(["baseline", "compare", before, after, "--max-regression", "0.1"])
            standalone_output = StringIO()
            with patch("sys.stdout", standalone_output):
                standalone_code = baseline.main(["compare", before, after, "--max-regression", "0.1"])

        self.assertEqual(cli_code, standalone_code)
        self.assertEqual(cli_output, standalone_output.getvalue())

    def test_standalone_entry_point_rejects_invalid_max_regression_with_exit_2(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(directory, make_result("before"), make_result("after"))
            output = StringIO()
            with patch("sys.stdout", output), patch("sys.stderr", StringIO()):
                code = baseline.main(["compare", before, after, "--max-regression", "-0.1"])

        self.assertEqual(2, code)
        self.assertEqual("", output.getvalue())

    def test_duplicate_json_keys_are_invalid_input_when_the_gate_is_on_only(self):
        for shadowed_file in ("before", "after"):
            for entry_point in ("cli", "standalone"):
                with self.subTest(file=shadowed_file, entry_point=entry_point):
                    with tempfile.TemporaryDirectory() as directory:
                        before, after = self.write_pair(
                            directory, make_result("before", input_tokens=100), make_result("after", input_tokens=100)
                        )
                        target = Path(before if shadowed_file == "before" else after)
                        target.write_text(
                            target.read_text(encoding="utf-8").replace('"metrics":', '"metrics": {}, "metrics":', 1),
                            encoding="utf-8",
                        )

                        def run(extra):
                            output, error = StringIO(), StringIO()
                            with patch("sys.stdout", output), patch("sys.stderr", error):
                                if entry_point == "cli":
                                    code = cli_main(["baseline", "compare", before, after, *extra])
                                else:
                                    code = baseline.main(["compare", before, after, *extra])
                            return code, output.getvalue(), error.getvalue()

                        code, output, error = run(["--max-regression", "0.1"])
                        self.assertEqual(2, code)
                        self.assertEqual("", output)
                        self.assertTrue(error)
                        self.assertEqual(0, run([])[0], "without the flag the input is read as before")

    def test_standalone_entry_point_maps_bad_input_to_exit_2_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(directory, make_result("before"), make_result("after"))
            for argv in (
                ["compare", str(Path(directory) / "missing.json"), after, "--max-regression", "0.1"],
                ["compare", str(Path(directory) / "missing.json"), after],
            ):
                with self.subTest(argv=argv):
                    output, error = StringIO(), StringIO()
                    with patch("sys.stdout", output), patch("sys.stderr", error):
                        code = baseline.main(argv)
                    self.assertEqual(2, code)
                    self.assertEqual("", output.getvalue())
                    self.assertTrue(error.getvalue())

    def test_python_module_entry_point_exits_with_gate_status(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = self.write_pair(
                directory, make_result("before", input_tokens=100), make_result("after", input_tokens=200)
            )

            completed = subprocess.run(
                [sys.executable, "-m", "inonu_harness", "baseline", "compare", before, after, "--max-regression", "0.1"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

        self.assertEqual(1, completed.returncode)
        self.assertEqual("fail", json.loads(completed.stdout)["gate"]["status"])


if __name__ == "__main__":
    unittest.main()
