import tempfile
import sqlite3
import unittest
from pathlib import Path

from inonu_harness.decision_graph import (
    Alternative,
    AuthorizationRequired,
    CriterionResult,
    DependencyCycle,
    DecisionGraph,
    DecisionValidationError,
    EvidenceReference,
    IdempotencyConflict,
    UnsupportedSchemaVersion,
)
from inonu_harness.sqlite_store import SQLiteDecisionStore


class DecisionGraphTests(unittest.TestCase):
    @staticmethod
    def create(graph, decision_id, dependencies=(), idempotency_key=None):
        return graph.create_decision(
            decision_id=decision_id,
            question=f"Question for {decision_id}?",
            alternatives=(Alternative("a", "A"), Alternative("b", "B")),
            constraints=(),
            required_criteria=("safe",),
            dependencies=dependencies,
            idempotency_key=(
                f"create-{decision_id}" if idempotency_key is None else idempotency_key
            ),
        )

    def test_created_decision_is_retrievable_with_its_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            evidence = EvidenceReference(
                source="repository",
                reference="docs/spec.md#R04",
                provenance="accepted milestone spec",
            )
            try:
                created = graph.create_decision(
                    decision_id="storage-choice",
                    question="Which local persistence mechanism should be used?",
                    alternatives=(Alternative("sqlite", "SQLite"), Alternative("json", "JSON file")),
                    constraints=("standard library only",),
                    required_criteria=("durable",),
                    evidence=(evidence,),
                    idempotency_key="create-storage-choice",
                )

                self.assertEqual(created, graph.get("storage-choice"))
                self.assertEqual("pending", created.status)
                self.assertEqual("Which local persistence mechanism should be used?", created.question)
                self.assertEqual(("sqlite", "json"), tuple(option.id for option in created.alternatives))
                self.assertEqual("accepted milestone spec", created.evidence[0].provenance)
                self.assertEqual(1, created.revision)
                self.assertEqual(("storage-choice",), tuple(item.id for item in graph.list_decisions()))
            finally:
                store.close()

    def test_decision_cannot_depend_on_an_unknown_id(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)

            try:
                with self.assertRaises(DecisionValidationError):
                    graph.create_decision(
                        decision_id="dependent",
                        question="Which option?",
                        alternatives=(Alternative("a", "A"), Alternative("b", "B")),
                        constraints=(),
                        required_criteria=("safe",),
                        dependencies=("missing",),
                        idempotency_key="create-dependent",
                    )
            finally:
                store.close()

    def test_idempotent_create_returns_original_result_and_rejects_changed_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            args = {
                "decision_id": "same-id",
                "question": "Which option?",
                "alternatives": (Alternative("a", "A"), Alternative("b", "B")),
                "constraints": (),
                "required_criteria": ("safe",),
                "idempotency_key": "same-key",
            }
            try:
                original = graph.create_decision(**args)
                retry = graph.create_decision(**args)
                self.assertEqual(original, retry)
                self.assertEqual(1, len(graph.history("same-id")))

                with self.assertRaises(IdempotencyConflict):
                    graph.create_decision(**{**args, "question": "A changed question"})
            finally:
                store.close()

    def test_idempotent_revision_retry_returns_original_revision_without_duplication(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                self.create(graph, "revision-retry")
                args = {
                    "question": "Revised question?",
                    "idempotency_key": "same-revision-key",
                }
                original = graph.revise("revision-retry", **args)
                retry = graph.revise("revision-retry", **args)
                self.assertEqual(original, retry)
                self.assertEqual(2, len(graph.history("revision-retry")))
            finally:
                store.close()

    def test_relevant_premise_revision_invalidates_transitive_dependents_and_keeps_history(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                self.create(graph, "root")
                self.create(graph, "middle", ("root",))
                self.create(graph, "leaf", ("middle",))
                proof = EvidenceReference(
                    "test", "checks/middle", "operator validation", criterion_id="safe"
                )
                graph.authorize(
                    "middle",
                    alternative_id="a",
                    actor="operator",
                    criteria={"safe": CriterionResult(True, (proof,))},
                    idempotency_key="authorize-middle",
                )

                revised = graph.revise(
                    "root",
                    question="Revised premise?",
                    relevant_premise_changed=True,
                    idempotency_key="revise-root",
                )

                self.assertEqual(2, revised.revision)
                self.assertEqual("pending", revised.status)
                self.assertEqual("invalidated", graph.get("middle").status)
                self.assertEqual("invalidated", graph.get("leaf").status)
                self.assertEqual(("leaf", "middle"), tuple(sorted(item.id for item in graph.affected_by("root"))))
                self.assertEqual(3, len(graph.history("middle")))
                self.assertEqual("invalidated", graph.history("middle")[-1].event)
                with self.assertRaises(AuthorizationRequired):
                    graph.require_authorized("middle", "a")
            finally:
                store.close()

    def test_revision_that_would_create_a_dependency_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                self.create(graph, "first")
                self.create(graph, "second", ("first",))

                with self.assertRaises(DependencyCycle):
                    graph.revise(
                        "first",
                        dependencies=("second",),
                        idempotency_key="cycle-attempt",
                    )

                self.assertEqual(1, graph.get("first").revision)
                self.assertEqual(1, len(graph.history("first")))
            finally:
                store.close()

    def test_unmarked_revision_does_not_invalidate_dependents(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                self.create(graph, "ordinary-root")
                self.create(graph, "ordinary-child", ("ordinary-root",))
                graph.revise(
                    "ordinary-root",
                    question="Edited text without premise change?",
                    idempotency_key="ordinary-revision",
                )
                self.assertEqual("pending", graph.get("ordinary-child").status)
                self.assertEqual(1, len(graph.history("ordinary-child")))
            finally:
                store.close()

    def test_recommendation_never_authorizes_and_explicit_evidenced_criteria_do(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                self.create(graph, "choice")
                recommended = graph.recommend(
                    "choice",
                    alternative_id="a",
                    source="jev-mock",
                    version="fixture-1",
                    provenance="local mock result",
                    idempotency_key="recommend-choice",
                )
                self.assertEqual("a", recommended.recommendation.alternative_id)
                self.assertIsNone(recommended.authorized_alternative_id)
                with self.assertRaises(AuthorizationRequired):
                    graph.require_authorized("choice", "a")

                proof = EvidenceReference(
                    source="test",
                    reference="acceptance/safe",
                    provenance="operator validation",
                    criterion_id="safe",
                )
                authorization_args = {
                    "alternative_id": "a",
                    "actor": "operator",
                    "criteria": {"safe": CriterionResult(passed=True, evidence=(proof,))},
                    "idempotency_key": "authorize-choice",
                }
                authorized = graph.authorize("choice", **authorization_args)
                self.assertEqual("authorized", authorized.status)
                self.assertEqual("a", graph.require_authorized("choice", "a").authorized_alternative_id)
                self.assertEqual(("choice",), tuple(item.id for item in graph.list_decisions(status="authorized")))
                with self.assertRaises(AuthorizationRequired):
                    graph.require_authorized("choice", "b")
                self.assertEqual(authorized, graph.authorize("choice", **authorization_args))
                self.assertEqual(3, len(graph.history("choice")))
                with self.assertRaises(IdempotencyConflict):
                    graph.authorize("choice", **{**authorization_args, "actor": "different operator"})
            finally:
                store.close()

    def test_authorization_requires_a_true_evidence_backed_result_for_every_criterion(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                graph.create_decision(
                    decision_id="two-criteria",
                    question="Which option?",
                    alternatives=(Alternative("a", "A"), Alternative("b", "B")),
                    constraints=(),
                    required_criteria=("safe", "private"),
                    idempotency_key="create-two-criteria",
                )
                safe_evidence = EvidenceReference(
                    "test", "checks/safety", "local check", criterion_id="safe"
                )
                private_evidence = EvidenceReference(
                    "test", "checks/privacy", "local check", criterion_id="private"
                )

                with self.assertRaises(DecisionValidationError):
                    graph.authorize(
                        "two-criteria",
                        alternative_id="a",
                        actor="operator",
                        criteria={"safe": CriterionResult(True, (safe_evidence,))},
                        idempotency_key="missing-criterion",
                    )
                with self.assertRaises(DecisionValidationError):
                    graph.authorize(
                        "two-criteria",
                        alternative_id="a",
                        actor="operator",
                        criteria={
                            "safe": CriterionResult(True, (safe_evidence,)),
                            "private": CriterionResult(True, ()),
                        },
                        idempotency_key="missing-evidence",
                    )
                with self.assertRaises(DecisionValidationError):
                    graph.authorize(
                        "two-criteria",
                        alternative_id="a",
                        actor="operator",
                        criteria={
                            "safe": CriterionResult(True, (safe_evidence,)),
                            "private": CriterionResult(False, (private_evidence,)),
                        },
                        idempotency_key="failed-criterion",
                    )
            finally:
                store.close()

    def test_status_queries_and_revision_clear_state_without_erasing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                self.create(graph, "premise")
                self.create(graph, "dependent", ("premise",))
                self.create(graph, "blocked-decision")
                graph.block_decision(
                    "blocked-decision", reason="waiting on evidence", idempotency_key="block-one"
                )
                self.assertEqual(("blocked-decision",), tuple(item.id for item in graph.blocked()))

                graph.revise(
                    "premise",
                    question="New premise?",
                    relevant_premise_changed=True,
                    idempotency_key="change-premise",
                )
                self.assertEqual(("dependent",), tuple(item.id for item in graph.invalidated()))
                graph.revise("dependent", question="Reviewed again?", idempotency_key="review-dependent")
                self.assertEqual("pending", graph.get("dependent").status)
                self.assertEqual(
                    ("created", "invalidated", "revised"),
                    tuple(item.event for item in graph.history("dependent")),
                )
                self.assertIn("premise", graph.history("dependent")[1].snapshot.invalidated_by)
            finally:
                store.close()

    def test_state_and_revision_history_survive_closing_and_reopening_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.sqlite"
            first_store = SQLiteDecisionStore(path)
            first_graph = DecisionGraph(first_store)
            self.create(first_graph, "durable")
            first_graph.revise("durable", question="Persisted revision?", idempotency_key="revise-durable")
            expected_history = first_graph.history("durable")
            first_store.close()

            reopened_store = SQLiteDecisionStore(path)
            try:
                reopened = DecisionGraph(reopened_store)
                self.assertEqual("Persisted revision?", reopened.get("durable").question)
                self.assertEqual(expected_history, reopened.history("durable"))
                self.assertEqual(("durable",), tuple(item.id for item in reopened.pending()))
                original_result = reopened.revise(
                    "durable", question="Persisted revision?", idempotency_key="revise-durable"
                )
                self.assertEqual(2, original_result.revision)
                self.assertEqual(expected_history, reopened.history("durable"))
            finally:
                reopened_store.close()

    def test_invalid_decision_shapes_and_empty_idempotency_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                with self.assertRaises(DecisionValidationError):
                    graph.create_decision(
                        decision_id="empty-question",
                        question=" ",
                        alternatives=(Alternative("a", "A"), Alternative("b", "B")),
                        constraints=(),
                        required_criteria=("valid",),
                        idempotency_key="empty-question-key",
                    )
                with self.assertRaises(DecisionValidationError):
                    graph.create_decision(
                        decision_id="duplicate-alternatives",
                        question="Which option?",
                        alternatives=(Alternative("a", "A"), Alternative("a", "Again")),
                        constraints=(),
                        required_criteria=("valid",),
                        idempotency_key="duplicate-options-key",
                    )
                with self.assertRaises(DecisionValidationError):
                    self.create(graph, "empty-key", idempotency_key=" ")
            finally:
                store.close()

    def test_malformed_collection_and_scalar_types_are_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteDecisionStore(Path(directory) / "decisions.sqlite")
            graph = DecisionGraph(store)
            try:
                with self.assertRaises(DecisionValidationError):
                    graph.create_decision(
                        decision_id="bad-constraint-shape",
                        question="Which option?",
                        alternatives=(Alternative("a", "A"), Alternative("b", "B")),
                        constraints="abc",
                        required_criteria=("valid",),
                        idempotency_key="bad-constraints",
                    )
                with self.assertRaises(DecisionValidationError):
                    graph.create_decision(
                        decision_id="bad-alternative-shape",
                        question="Which option?",
                        alternatives=(Alternative(7, "A"), Alternative("b", "B")),
                        constraints=(),
                        required_criteria=("valid",),
                        idempotency_key="bad-alternative",
                    )
                self.create(graph, "valid-premise")
                self.create(graph, "valid-dependent", ("valid-premise",))
                with self.assertRaises(DecisionValidationError):
                    graph.revise(
                        "valid-premise",
                        question="Changed?",
                        relevant_premise_changed="false",
                        idempotency_key="bad-premise-flag",
                    )
                self.assertEqual("pending", graph.get("valid-dependent").status)
            finally:
                store.close()

    def test_unsupported_sqlite_schema_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "future.sqlite"
            connection = sqlite3.connect(path)
            try:
                connection.execute("PRAGMA user_version = 999")
            finally:
                connection.close()

            with self.assertRaises(UnsupportedSchemaVersion):
                SQLiteDecisionStore(path)


if __name__ == "__main__":
    unittest.main()
