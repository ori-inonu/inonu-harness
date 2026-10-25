from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import platform
import tempfile
import time
import unittest
from unittest.mock import patch

from inonu_harness.baseline import compare_runs, run_fixture
from inonu_harness.cli import main
from inonu_harness.decision_graph import Alternative, DecisionGraph, EvidenceReference
from inonu_harness.sqlite_store import SQLiteDecisionStore


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "sdd_context" / "consumer-task.json"


class FixedClock:
    def __init__(self, *ticks: float):
        self._ticks = iter(ticks)

    def __call__(self) -> float:
        return next(self._ticks)


class SddContextEvaluationTests(unittest.TestCase):
    def test_same_local_task_compares_without_context_and_with_cli_projection(self):
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        task = fixture["task"]
        decision = task["decision"]

        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "decisions.sqlite"
            store = SQLiteDecisionStore(db_path)
            graph = DecisionGraph(store)
            try:
                graph.create_decision(
                    decision_id=decision["id"],
                    question=decision["question"],
                    alternatives=tuple(Alternative(**item) for item in decision["alternatives"]),
                    constraints=tuple(decision["constraints"]),
                    required_criteria=tuple(decision["required_criteria"]),
                    dependencies=tuple(decision["dependencies"]),
                    evidence=tuple(EvidenceReference(**item) for item in decision["evidence"]),
                    idempotency_key="create-m2-cli-consumer",
                )
                recommendation = decision["recommendation"]
                graph.recommend(
                    decision["id"],
                    alternative_id=recommendation["alternative_id"],
                    source=recommendation["source"],
                    version=recommendation["version"],
                    provenance=recommendation["provenance"],
                    idempotency_key="recommend-m2-cli-consumer",
                )
                history_before = graph.history(decision["id"])
            finally:
                store.close()

            db_before = db_path.read_bytes()
            output = StringIO()
            started = time.perf_counter()
            with patch("sys.stdout", output):
                exit_code = main([
                    "decisions", "--db", str(db_path), "context", "--ids", decision["id"]
                ])
            stopped = time.perf_counter()
            projected = json.loads(output.getvalue())
            self.assertEqual(0, exit_code)
            self.assertEqual("ready", projected["status"])
            self.assertEqual([decision["id"]], [item["id"] for item in projected["decisions"]])
            self.assertEqual(db_before, db_path.read_bytes())

            readonly_store = SQLiteDecisionStore(db_path, read_only=True)
            try:
                self.assertEqual(history_before, DecisionGraph(readonly_store).history(decision["id"]))
            finally:
                readonly_store.close()

        control_packet = {"task": task["prompt"], "decision_context": None}
        treatment_packet = {"task": task["prompt"], "decision_context": projected["decisions"]}
        self.assertEqual(control_packet["task"], treatment_packet["task"])

        acceptance_ids = fixture["acceptance_ids"]

        def evaluate(packet):
            records = packet["decision_context"] or []
            record = records[0] if len(records) == 1 else None
            return {
                "selected-context-present": record is not None,
                "task-rails-delivered": record is not None and (
                    set(decision["constraints"]).issubset(record["constraints"])
                    and set(decision["required_criteria"]).issubset(record["required_criteria"])
                ),
                "recommendation-remains-unauthorized": record is not None and (
                    record["recommendation"]["alternative_id"] == "cli-json"
                    and record["authorized_alternative_id"] is None
                ),
            }

        def acceptance_rows(packet):
            measured = evaluate(packet)
            return [{"id": item, "passed": measured[item]} for item in acceptance_ids]

        control_fixture = dict(fixture)
        control_fixture["acceptance"] = acceptance_rows(control_packet)
        control = run_fixture(
            control_fixture,
            execution_id="sdd-context-without-context",
            version_source={"python": platform.python_version()},
        )
        control["metrics"]["elapsed_seconds"] = {
            "value": None,
            "source": {"kind": "unavailable", "reason": "no_cli_context_read"},
        }

        treatment_fixture = dict(fixture)
        treatment_fixture["acceptance"] = acceptance_rows(treatment_packet)
        treatment = run_fixture(
            treatment_fixture,
            execution_id="sdd-context-with-cli-context",
            clock=FixedClock(started, stopped),
            version_source={"python": platform.python_version()},
        )

        self.assertEqual([False] * len(acceptance_ids), [item["passed"] for item in control_fixture["acceptance"]])
        self.assertEqual([True] * len(acceptance_ids), [item["passed"] for item in treatment_fixture["acceptance"]])
        comparison = compare_runs(control, treatment)
        self.assertTrue(comparison["compatible"])
        self.assertTrue(comparison["comparisons"]["acceptance"]["changed"])
        self.assertEqual("incomparable", comparison["comparisons"]["elapsed_seconds"]["status"])
        self.assertEqual(
            "value_unavailable",
            comparison["comparisons"]["elapsed_seconds"]["reason"],
        )
        self.assertGreaterEqual(treatment["metrics"]["elapsed_seconds"]["value"], 0)
        self.assertEqual("injected", treatment["metrics"]["elapsed_seconds"]["source"]["reference"])

        for run in (control, treatment):
            for name in ("runtime", "model", "input_tokens", "output_tokens", "cost_usd"):
                self.assertIsNone(run["metrics"][name]["value"])
            self.assertEqual([], run["metrics"]["tool_calls"]["value"])
            self.assertEqual("fixture", run["metrics"]["tool_calls"]["source"]["kind"])


if __name__ == "__main__":
    unittest.main()
