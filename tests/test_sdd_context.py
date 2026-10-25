from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import platform
import tempfile
import time
import unittest

from inonu_harness.baseline import run_fixture
from inonu_harness.decision_graph import (
    Alternative,
    DecisionGraph,
    DecisionNotFound,
    EvidenceReference,
)
from inonu_harness.sdd_adapter import SddDecisionContextAdapter
from inonu_harness.sqlite_store import SQLiteDecisionStore


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "sdd_context" / "context-projection.json"


class FixedClock:
    def __init__(self, *ticks: float):
        self._ticks = iter(ticks)

    def __call__(self) -> float:
        return next(self._ticks)


class SddDecisionContextAdapterTests(unittest.TestCase):
    def test_disabled_by_default_returns_without_accessing_graph(self):
        class NoTouchGraph:
            def __getattr__(self, name):
                raise AssertionError(f"disabled adapter touched graph attribute {name}")

        adapter = SddDecisionContextAdapter(graph=NoTouchGraph())

        result = adapter.load_context(["anything"])

        self.assertEqual("disabled", result.status)
        self.assertEqual((), result.decisions)

    def test_rejects_invalid_id_lists(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            adapter = SddDecisionContextAdapter(enabled=True, graph=graph)
            try:
                for ids in (
                    [],
                    "decision-a",
                    [""],
                    [" decision-a"],
                    ["decision-a "],
                    ["bad id"],
                    ["-invalid-first-character"],
                    ["a" * 129],
                    ["a", "a"],
                    None,
                ):
                    with self.subTest(ids=ids):
                        self.assertEqual("invalid_request", adapter.load_context(ids).status)
            finally:
                store.close()

    def test_enabled_context_projects_explicit_order_and_records_baseline_from_output(self):
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        scenario = fixture.pop("scenario")
        acceptance_ids = fixture.pop("acceptance_ids")

        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            adapter = SddDecisionContextAdapter(enabled=True, graph=graph)
            try:
                for spec in scenario["decisions"]:
                    graph.create_decision(
                        decision_id=spec["id"],
                        question=spec["question"],
                        alternatives=tuple(Alternative(**item) for item in spec["alternatives"]),
                        constraints=tuple(spec["constraints"]),
                        required_criteria=tuple(spec["required_criteria"]),
                        dependencies=tuple(spec["dependencies"]),
                        evidence=tuple(EvidenceReference(**item) for item in spec["evidence"]),
                        idempotency_key=f"create-{spec['id']}",
                    )
                recommendation = scenario["recommendation"]
                graph.recommend(
                    recommendation["decision_id"],
                    alternative_id=recommendation["alternative_id"],
                    source=recommendation["source"],
                    version=recommendation["version"],
                    provenance=recommendation["provenance"],
                    idempotency_key="recommend-fixture-choice",
                )
                revision = scenario["revision"]
                graph.revise(
                    revision["decision_id"],
                    question=revision["question"],
                    relevant_premise_changed=revision["relevant_premise_changed"],
                    idempotency_key="revise-fixture-premise",
                )

                history_before = {item: graph.history(item) for item in scenario["request_ids"]}
                started = time.perf_counter()
                result = adapter.load_context(scenario["request_ids"])
                stopped = time.perf_counter()
                history_after = {item: graph.history(item) for item in scenario["request_ids"]}
                disabled = SddDecisionContextAdapter().load_context(scenario["request_ids"])

                records = tuple(asdict(item) for item in result.decisions)
                by_id = {record["id"]: record for record in records}
                acceptance = {
                    "explicit-order-preserved": tuple(record["id"] for record in records)
                    == tuple(scenario["request_ids"]),
                    "pending-and-invalidated-states-projected": (
                        by_id["root-premise"]["status"] == "pending"
                        and by_id["dependent-choice"]["status"] == "invalidated"
                        and by_id["dependent-choice"]["invalidated_by"] == ("root-premise",)
                    ),
                    "recommendation-remains-unauthorized": (
                        by_id["recommended-choice"]["recommendation"]["alternative_id"] == "option-b"
                        and by_id["recommended-choice"]["authorized_alternative_id"] is None
                    ),
                    "only-allowlisted-fields-projected": self._contains_only_projected_fields(records),
                    "read-does-not-change-history": history_before == history_after,
                    "disabled-default-returns-no-context": (
                        disabled.status == "disabled" and disabled.decisions == ()
                    ),
                }
                self.assertEqual("ready", result.status)
                self.assertTrue(all(acceptance.values()), acceptance)

                fixture["acceptance"] = [
                    {"id": criterion, "passed": acceptance[criterion]}
                    for criterion in acceptance_ids
                ]
                baseline = run_fixture(
                    fixture,
                    execution_id="sdd-context-projection-test",
                    clock=FixedClock(started, stopped),
                    version_source={"python": platform.python_version()},
                )
                metrics = baseline["metrics"]
                self.assertEqual(
                    fixture["acceptance"],
                    metrics["acceptance"]["value"],
                )
                self.assertGreaterEqual(metrics["elapsed_seconds"]["value"], 0)
                self.assertEqual("injected", metrics["elapsed_seconds"]["source"]["reference"])
                for name in ("runtime", "model", "input_tokens", "output_tokens", "cost_usd"):
                    self.assertIsNone(metrics[name]["value"])
            finally:
                store.close()

    def test_missing_requested_id_propagates_decision_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            adapter = SddDecisionContextAdapter(enabled=True, graph=graph)
            try:
                with self.assertRaises(DecisionNotFound):
                    adapter.load_context(["does-not-exist"])
            finally:
                store.close()

    def test_enabling_requires_a_graph(self):
        with self.assertRaisesRegex(ValueError, "requires a decision graph"):
            SddDecisionContextAdapter(enabled=True)

    @staticmethod
    def _contains_only_projected_fields(records):
        decision_fields = {
            "id",
            "revision",
            "question",
            "alternatives",
            "constraints",
            "required_criteria",
            "dependencies",
            "status",
            "evidence",
            "recommendation",
            "authorized_alternative_id",
            "invalidated_by",
            "validated_criteria",
        }
        evidence_fields = {"source", "reference", "criterion_id", "version"}
        recommendation_fields = {"alternative_id", "source", "version"}
        for record in records:
            if set(record) != decision_fields:
                return False
            if any(set(alternative) != {"id", "label"} for alternative in record["alternatives"]):
                return False
            if any(set(evidence) != evidence_fields for evidence in record["evidence"]):
                return False
            if record["recommendation"] is not None and set(record["recommendation"]) != recommendation_fields:
                return False
        return True


if __name__ == "__main__":
    unittest.main()
