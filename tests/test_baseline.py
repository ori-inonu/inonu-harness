import json
import unittest
from pathlib import Path

from inonu_harness.baseline import compare_runs, run_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "fixtures" / "baseline" / "offline-smoke.json"


class FixedClock:
    def __init__(self, *ticks):
        self._ticks = iter(ticks)

    def __call__(self):
        return next(self._ticks)


class BaselineRunnerTests(unittest.TestCase):
    def test_runs_checked_in_fixture_offline_with_injected_observations(self):
        result = run_fixture(
            FIXTURE,
            execution_id="run-offline-001",
            clock=FixedClock(100.0, 100.125),
            version_source=lambda: {"python": "3.test", "inonu-harness": "0.1.0"},
        )

        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["execution_id"], "run-offline-001")
        self.assertEqual(result["task_id"], "baseline.offline-smoke")
        self.assertEqual(result["config_id"], "fixture.offline.v1")
        self.assertEqual(result["metrics"]["elapsed_seconds"]["value"], 0.125)
        self.assertEqual(
            result["metrics"]["component_versions"]["value"],
            {"python": "3.test", "inonu-harness": "0.1.0"},
        )

    def test_every_measurement_has_a_source_and_unobserved_values_are_null(self):
        result = run_fixture(
            FIXTURE,
            execution_id="run-offline-002",
            clock=FixedClock(1.0, 1.5),
            version_source=lambda: {"python": "3.test"},
        )
        metrics = result["metrics"]
        self.assertEqual(
            set(metrics),
            {
                "acceptance",
                "elapsed_seconds",
                "runtime",
                "model",
                "input_tokens",
                "output_tokens",
                "cost_usd",
                "tool_calls",
                "failures",
                "blocks",
                "recoveries",
                "component_versions",
            },
        )

        for name, measurement in metrics.items():
            with self.subTest(metric=name):
                self.assertIn("value", measurement)
                self.assertIsInstance(measurement["source"], dict)
                self.assertTrue(measurement["source"])

        for name in ("runtime", "model", "input_tokens", "output_tokens", "cost_usd"):
            with self.subTest(metric=name):
                self.assertIsNone(metrics[name]["value"])
                self.assertEqual(metrics[name]["source"]["kind"], "unavailable")

    def test_rejects_fixture_with_missing_required_ids(self):
        with self.assertRaises(ValueError):
            run_fixture({"fixture_id": "broken"}, clock=FixedClock(1.0, 1.1))

    def test_does_not_invent_acceptance_when_fixture_has_no_evidence(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        fixture["acceptance"] = []

        result = run_fixture(
            fixture,
            execution_id="empty-acceptance",
            clock=FixedClock(1.0, 1.1),
            version_source={},
        )

        self.assertEqual(result["metrics"]["acceptance"]["value"], [])
        self.assertIsNone(result["metrics"]["component_versions"]["value"])
        self.assertEqual(result["metrics"]["component_versions"]["source"]["kind"], "unavailable")


class BaselineComparisonTests(unittest.TestCase):
    def run_fixture_with(self, *, execution_id, duration, input_tokens=None, source_kind="fixture"):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        fixture["input_tokens"] = input_tokens
        if input_tokens is not None:
            fixture["measurement_sources"] = {"input_tokens": {"kind": source_kind, "reference": "test-counter"}}
        return run_fixture(
            fixture,
            execution_id=execution_id,
            clock=FixedClock(10.0, 10.0 + duration),
            version_source=lambda: {"python": "3.test"},
        )

    def test_compares_only_compatible_observed_metrics_for_same_task_and_config(self):
        before = self.run_fixture_with(execution_id="before", duration=0.2, input_tokens=100)
        after = self.run_fixture_with(execution_id="after", duration=0.3, input_tokens=140)

        comparison = compare_runs(before, after)

        self.assertTrue(comparison["compatible"])
        self.assertAlmostEqual(comparison["comparisons"]["elapsed_seconds"]["delta"], 0.1)
        self.assertEqual(comparison["comparisons"]["input_tokens"]["delta"], 40)
        self.assertEqual(comparison["comparisons"]["cost_usd"]["status"], "incomparable")

    def test_marks_different_measurement_sources_incomparable(self):
        before = self.run_fixture_with(execution_id="before", duration=0.2, input_tokens=100)
        after = self.run_fixture_with(execution_id="after", duration=0.3, input_tokens=140, source_kind="runtime-api")

        comparison = compare_runs(before, after)

        self.assertEqual(comparison["comparisons"]["input_tokens"]["status"], "incomparable")
        self.assertIsNone(comparison["comparisons"]["input_tokens"]["delta"])

    def test_marks_different_measurement_references_incomparable(self):
        before_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        after_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        before_fixture["input_tokens"] = 100
        after_fixture["input_tokens"] = 140
        before_fixture["measurement_sources"] = {"input_tokens": {"kind": "fixture", "reference": "case-a"}}
        after_fixture["measurement_sources"] = {"input_tokens": {"kind": "fixture", "reference": "case-b"}}
        before = run_fixture(before_fixture, execution_id="before", clock=FixedClock(1.0, 1.2), version_source={"python": "3.test"})
        after = run_fixture(after_fixture, execution_id="after", clock=FixedClock(1.0, 1.2), version_source={"python": "3.test"})

        comparison = compare_runs(before, after)

        self.assertEqual(comparison["comparisons"]["input_tokens"]["status"], "incomparable")
        self.assertEqual(comparison["comparisons"]["input_tokens"]["reason"], "source_incompatible")

    def test_rejects_result_with_missing_measurement_provenance(self):
        result = self.run_fixture_with(execution_id="before", duration=0.2)
        result["metrics"]["cost_usd"]["source"] = {}

        with self.assertRaises(ValueError):
            compare_runs(result, result)

    def test_rejects_unsupported_result_schema_even_when_both_runs_match(self):
        result = self.run_fixture_with(execution_id="before", duration=0.2)
        result["schema_version"] = 2

        with self.assertRaisesRegex(ValueError, "unsupported schema"):
            compare_runs(result, result)

    def test_rejects_comparison_across_task_or_config(self):
        before = self.run_fixture_with(execution_id="before", duration=0.2)
        after = self.run_fixture_with(execution_id="after", duration=0.3)
        after["config_id"] = "another-config"

        comparison = compare_runs(before, after)

        self.assertFalse(comparison["compatible"])
        self.assertEqual(comparison["reason"], "task_or_config_mismatch")
        self.assertEqual(comparison["comparisons"], {})


if __name__ == "__main__":
    unittest.main()
