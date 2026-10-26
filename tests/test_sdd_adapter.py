import tempfile
import unittest
from pathlib import Path

from inonu_harness.decision_graph import (
    Alternative,
    AuthorizationRequired,
    DecisionGraph,
)
from inonu_harness.jev import JevAdapter, MockJevTransport
from inonu_harness.sdd_adapter import SddDecisionGate
from inonu_harness.sqlite_store import SQLiteDecisionStore


SPEC = {
    "id": "store-choice",
    "goal": "Choose local persistence",
    "facts": {"runtime": "python-stdlib"},
    "rails": ["No remote service"],
    "options": [
        {"id": "sqlite", "label": "SQLite", "what": "Persist locally"},
        {"id": "json", "label": "JSON", "what": "Use a local file"},
    ],
}
PLAN = {"specId": "store-choice", "plannedCalls": 12, "estimatedInputTokens": 500}
CONSENSUS = {
    "receipt": {
        "specId": "store-choice",
        "specHash": "b" * 64,
        "status": "consenso",
        "leader": "sqlite",
        "implement": True,
    }
}
NO_CONSENSUS = {
    "receipt": {
        "specId": "store-choice",
        "specHash": "b" * 64,
        "status": "sem_consenso",
        "leader": None,
        "implement": False,
    }
}


def create_decision(graph):
    return graph.create_decision(
        decision_id="store-choice",
        question="Which local persistence?",
        alternatives=(Alternative("sqlite", "SQLite"), Alternative("json", "JSON")),
        constraints=("No remote service",),
        required_criteria=("durable",),
        idempotency_key="create-store-choice",
    )


class SddDecisionGateTests(unittest.TestCase):
    def test_gate_is_disabled_by_default_and_touches_neither_dependency(self):
        class Untouchable:
            def __getattribute__(self, name):
                raise AssertionError(f"dependency accessed while gate is disabled: {name}")

        gate = SddDecisionGate(graph=Untouchable(), adapter=Untouchable())
        result = gate.request_recommendation("store-choice", SPEC, idempotency_key="once")
        self.assertEqual("disabled", result.status)
        self.assertIsNone(result.decision)

    def test_enabled_gate_persists_recommendation_without_authorizing(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            create_decision(graph)
            transport = MockJevTransport({"consensus_plan": PLAN, "consensus_run": CONSENSUS})
            gate = SddDecisionGate(enabled=True, graph=graph, adapter=JevAdapter(transport, server_version="0.1.0"))
            try:
                result = gate.request_recommendation("store-choice", SPEC, idempotency_key="recommend-once")
                self.assertEqual("recommended", result.status)
                self.assertEqual("sqlite", result.decision.recommendation.alternative_id)
                self.assertEqual("pending", result.decision.status)
                self.assertIsNone(result.decision.authorized_alternative_id)
                with self.assertRaises(AuthorizationRequired):
                    graph.require_authorized("store-choice", "sqlite")
            finally:
                store.close()

    def test_no_consensus_leaves_decision_and_history_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            created = create_decision(graph)
            transport = MockJevTransport({"consensus_plan": PLAN, "consensus_run": NO_CONSENSUS})
            gate = SddDecisionGate(enabled=True, graph=graph, adapter=JevAdapter(transport))
            try:
                result = gate.request_recommendation("store-choice", SPEC, idempotency_key="recommend-none")
                self.assertEqual("no_consensus", result.status)
                self.assertIsNone(result.decision)
                self.assertEqual(created, graph.get("store-choice"))
                self.assertEqual(1, len(graph.history("store-choice")))
            finally:
                store.close()

    def test_mismatched_decision_and_spec_ids_are_rejected_before_calls(self):
        transport = MockJevTransport()
        gate = SddDecisionGate(enabled=True, graph=object(), adapter=JevAdapter(transport))
        result = gate.request_recommendation("other-decision", SPEC, idempotency_key="mismatch")
        self.assertEqual("invalid_request", result.status)
        self.assertEqual([], transport.calls)

    def test_enabled_gate_requires_graph_and_adapter(self):
        with self.assertRaises(ValueError):
            SddDecisionGate(enabled=True)


if __name__ == "__main__":
    unittest.main()
