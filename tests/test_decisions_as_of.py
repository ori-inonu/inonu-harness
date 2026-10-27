import io
import json
from io import StringIO
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from inonu_harness import decision_graph
from inonu_harness.cli import main
from inonu_harness.decision_graph import Alternative, CriterionResult, DecisionGraph, EvidenceReference
from inonu_harness.sqlite_store import SQLiteDecisionStore


CREATED_ALPHA = "2026-10-26T10:00:00+00:00"
CREATED_BETA = "2026-10-26T11:00:00+00:00"
REVISED_ALPHA = "2026-10-26T12:00:00+00:00"
RECOMMENDED_ALPHA = "2026-10-26T13:00:00+00:00"
AUTHORIZED_ALPHA = "2026-10-26T14:00:00+00:00"
ALTERNATIVES = (Alternative("a", "A"), Alternative("b", "B"))


class DecisionsAsOfTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "decisions.sqlite"
        clock = [CREATED_ALPHA, CREATED_BETA, REVISED_ALPHA, RECOMMENDED_ALPHA, AUTHORIZED_ALPHA]
        store = SQLiteDecisionStore(self.path)
        try:
            graph = DecisionGraph(store)
            with patch.object(decision_graph, "_now", side_effect=clock):
                graph.create_decision(
                    decision_id="alpha",
                    question="Question for alpha?",
                    alternatives=ALTERNATIVES,
                    constraints=(),
                    required_criteria=("safe",),
                    idempotency_key="create-alpha",
                )
                graph.create_decision(
                    decision_id="beta",
                    question="Question for beta?",
                    alternatives=ALTERNATIVES,
                    constraints=(),
                    required_criteria=("safe",),
                    dependencies=("alpha",),
                    idempotency_key="create-beta",
                )
                graph.revise(
                    "alpha",
                    question="Revised question for alpha?",
                    relevant_premise_changed=True,
                    idempotency_key="revise-alpha",
                )
                graph.recommend(
                    "alpha",
                    alternative_id="a",
                    source="test",
                    version="1",
                    provenance="local recommendation",
                    idempotency_key="recommend-alpha",
                )
                graph.authorize(
                    "alpha",
                    alternative_id="a",
                    actor="owner",
                    criteria={
                        "safe": CriterionResult(
                            True,
                            (EvidenceReference("test", "checks/safe", "local test", criterion_id="safe"),),
                        )
                    },
                    idempotency_key="authorize-alpha",
                )
        finally:
            store.close()
        self.before = self.path.read_bytes()

    def run_cli(self, *arguments):
        output, error = StringIO(), StringIO()
        with patch("sys.stdout", output), patch("sys.stderr", error):
            code = main(["decisions", "--db", str(self.path), *arguments])
        return code, output.getvalue(), error.getvalue()

    def answer(self, *arguments):
        code, output, error = self.run_cli("as-of", *arguments)
        self.assertEqual((0, ""), (code, error))
        return json.loads(output)

    @staticmethod
    def item(result, decision_id):
        return next(entry for entry in result["decisions"] if entry["id"] == decision_id)

    @staticmethod
    def summary(entry):
        snapshot = entry["snapshot"] or {}
        return entry["state"], entry["revision"], entry["recorded_at"], entry["later_revision"], snapshot.get("status")

    def test_instant_before_first_revision_lists_nothing_and_marks_requested_ids_not_yet_created(self):
        self.assertEqual(
            {"schema_version": 1, "as_of": "2026-10-26T09:00:00+00:00", "decisions": []},
            self.answer("2026-10-26T09:00:00Z"),
        )

        result = self.answer("2026-10-26T09:00:00Z", "--ids", "beta", "alpha")
        self.assertEqual(["alpha", "beta"], [entry["id"] for entry in result["decisions"]])
        for entry in result["decisions"]:
            self.assertEqual(
                {
                    "id": entry["id"],
                    "state": "not_yet_created",
                    "revision": None,
                    "recorded_at": None,
                    "later_revision": True,
                    "snapshot": None,
                },
                entry,
            )

    def test_without_ids_only_decisions_that_existed_at_the_instant_are_listed(self):
        result = self.answer("2026-10-26T10:30:00Z")
        self.assertEqual(["alpha"], [entry["id"] for entry in result["decisions"]])
        self.assertEqual(("existed", 1, CREATED_ALPHA, True, "pending"), self.summary(self.item(result, "alpha")))

    def test_between_two_revisions_shows_the_earlier_snapshot_without_later_recommendation(self):
        alpha = self.item(self.answer("2026-10-26T12:30:00Z", "--ids", "alpha"), "alpha")
        self.assertEqual(("existed", 2, REVISED_ALPHA, True, "pending"), self.summary(alpha))
        self.assertEqual("Revised question for alpha?", alpha["snapshot"]["question"])
        self.assertIsNone(alpha["snapshot"]["recommendation"])
        self.assertIsNone(alpha["snapshot"]["authorized_by"])

        alpha = self.item(self.answer("2026-10-26T13:30:00Z", "--ids", "alpha"), "alpha")
        self.assertEqual(("existed", 3, RECOMMENDED_ALPHA, True, "pending"), self.summary(alpha))
        self.assertEqual("a", alpha["snapshot"]["recommendation"]["alternative_id"])
        self.assertIsNone(alpha["snapshot"]["authorized_by"])

    def test_invalidated_decision_is_shown_with_its_earlier_status(self):
        result = self.answer("2026-10-26T11:30:00Z", "--ids", "beta")
        self.assertEqual(("existed", 1, CREATED_BETA, True, "pending"), self.summary(self.item(result, "beta")))

        beta = self.item(self.answer("2026-10-26T12:00:00Z", "--ids", "beta"), "beta")
        self.assertEqual(("existed", 2, REVISED_ALPHA, False, "invalidated"), self.summary(beta))
        self.assertEqual(["alpha"], beta["snapshot"]["invalidated_by"])

    def test_instant_equal_to_a_revision_time_is_included_and_one_second_before_is_not(self):
        self.assertEqual(
            ("existed", 1, CREATED_ALPHA, True, "pending"),
            self.summary(self.item(self.answer("2026-10-26T11:59:59Z", "--ids", "alpha"), "alpha")),
        )
        self.assertEqual(
            ("existed", 2, REVISED_ALPHA, True, "pending"),
            self.summary(self.item(self.answer("2026-10-26T12:00:00Z", "--ids", "alpha"), "alpha")),
        )

    def test_same_instant_written_with_z_and_with_an_offset_gives_the_same_answer(self):
        with_z = self.answer("2026-10-26T12:00:00Z")
        with_offset = self.answer("2026-10-26T09:00:00-03:00")
        self.assertEqual(with_z, with_offset)
        self.assertEqual("2026-10-26T12:00:00+00:00", with_offset["as_of"])

    def test_after_the_last_revision_there_is_no_later_revision(self):
        result = self.answer("2026-10-26T15:00:00Z")
        self.assertEqual(("existed", 4, AUTHORIZED_ALPHA, False, "authorized"), self.summary(self.item(result, "alpha")))
        self.assertEqual(("existed", 2, REVISED_ALPHA, False, "invalidated"), self.summary(self.item(result, "beta")))

    def test_authorization_recorded_later_does_not_appear_in_earlier_snapshot(self):
        alpha = self.item(self.answer("2026-10-26T13:30:00Z", "--ids", "alpha"), "alpha")
        self.assertIsNone(alpha["snapshot"]["authorized_alternative_id"])
        self.assertEqual([], alpha["snapshot"]["validated_criteria"])

        alpha = self.item(self.answer("2026-10-26T14:30:00Z", "--ids", "alpha"), "alpha")
        self.assertEqual(("existed", 4, AUTHORIZED_ALPHA, False, "authorized"), self.summary(alpha))
        self.assertEqual("owner", alpha["snapshot"]["authorized_by"])

    def test_latest_snapshot_matches_the_decisions_show_serialization(self):
        shown = json.loads(self.run_cli("show", "alpha")[1])["decision"]
        self.assertEqual(shown, self.item(self.answer("2026-10-26T15:00:00Z"), "alpha")["snapshot"])

    def test_ids_are_filtered_and_sorted_by_id(self):
        self.assertEqual(["alpha", "beta"], [entry["id"] for entry in self.answer("2026-10-26T15:00:00Z")["decisions"]])
        self.assertEqual(["alpha", "beta"], [entry["id"] for entry in self.answer("2026-10-26T15:00:00Z", "--ids", "beta", "alpha")["decisions"]])
        self.assertEqual(["alpha"], [entry["id"] for entry in self.answer("2026-10-26T15:00:00Z", "--ids", "alpha")["decisions"]])

    def test_output_is_one_json_object_with_the_documented_keys(self):
        code, output, error = self.run_cli("as-of", "2026-10-26T12:30:00Z", "--ids", "alpha")
        self.assertEqual((0, ""), (code, error))
        result = json.loads(output)
        self.assertEqual({"schema_version", "as_of", "decisions"}, set(result))
        self.assertEqual({"id", "state", "revision", "recorded_at", "later_revision", "snapshot"}, set(result["decisions"][0]))

    def test_invalid_input_exits_2_with_empty_stdout_and_no_absolute_path(self):
        bad_database = self.root / "not-a-database.sqlite"
        bad_database.write_bytes(b"x" * 200)
        unsupported = self.root / "unsupported.sqlite"
        connection = sqlite3.connect(unsupported)
        connection.execute("PRAGMA user_version = 2")
        connection.close()
        for arguments in (
            ("as-of", "2026-10-26T12:00:00"),
            ("as-of", "not-a-time"),
            ("as-of", "2026-10-26T12:00:00Z", "--ids", "missing-id"),
            ("as-of", "0001-01-01T00:00:00+01:00"),
            ("as-of", "9999-12-31T23:00:00-05:00"),
        ):
            code, output, error = self.run_cli(*arguments)
            self.assertEqual(2, code, arguments)
            self.assertEqual("", output, arguments)
            self.assertNotIn(str(self.root), error, arguments)

        for database in (bad_database, unsupported, self.root / "missing" / "decisions.sqlite"):
            output, error = StringIO(), StringIO()
            with patch("sys.stdout", output), patch("sys.stderr", error):
                code = main(["decisions", "--db", str(database), "as-of", "2026-10-26T12:00:00Z"])
            self.assertEqual(2, code, database)
            self.assertEqual("", output.getvalue(), database)
            self.assertNotIn(str(self.root), error.getvalue(), database)
        self.assertFalse((self.root / "missing").exists())

    def test_queries_leave_the_database_bytes_and_directory_unchanged(self):
        files_before = sorted(entry.name for entry in self.root.iterdir())
        self.answer("2026-10-26T09:00:00Z", "--ids", "alpha", "beta")
        self.answer("2026-10-26T12:30:00Z")
        self.answer("2026-10-26T15:00:00Z", "--ids", "beta", "alpha")
        self.assertEqual(self.before, self.path.read_bytes())
        self.assertEqual(files_before, sorted(entry.name for entry in self.root.iterdir()))


class DecisionsAsOfClockTests(unittest.TestCase):
    """Histories whose recorded times are written in different formats or out of order."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "decisions.sqlite"

    def build(self, clock):
        store = SQLiteDecisionStore(self.path)
        try:
            graph = DecisionGraph(store)
            with patch.object(decision_graph, "_now", side_effect=clock):
                graph.create_decision(
                    decision_id="alpha", question="Q1?", alternatives=ALTERNATIVES, constraints=(),
                    required_criteria=("safe",), idempotency_key="create-alpha",
                )
                for number in range(2, len(clock) + 1):
                    graph.revise("alpha", question=f"Q{number}?", idempotency_key=f"revise-{number}")
        finally:
            store.close()

    def query(self, instant):
        output, error = StringIO(), StringIO()
        with patch("sys.stdout", output), patch("sys.stderr", error):
            code = main(["decisions", "--db", str(self.path), "as-of", instant, "--ids", "alpha"])
        self.assertEqual((0, ""), (code, error.getvalue()))
        return json.loads(output.getvalue())["decisions"][0]

    def test_mixed_offsets_and_precisions_are_compared_as_instants_not_as_text(self):
        self.build(["2026-10-26T09:30:00-03:00", "2026-10-26T14:00:00.250000+00:00", "2026-10-26T15:00:00+00:00"])
        entry = self.query("2026-10-26T12:00:00Z")  # 09:30-03:00 is 12:30Z, so alpha did not exist yet
        self.assertEqual("not_yet_created", entry["state"])
        self.assertEqual("existed", self.query("2026-10-26T12:30:00Z")["state"])

    def test_the_highest_revision_wins_even_when_an_earlier_revision_has_a_later_clock_time(self):
        self.build(["2026-10-26T10:00:00+00:00", "2026-10-26T12:00:00+00:00", "2026-10-26T11:00:00+00:00"])
        entry = self.query("2026-10-26T12:30:00Z")
        self.assertEqual(3, entry["revision"])
        self.assertEqual("Q3?", entry["snapshot"]["question"])
        self.assertFalse(entry["later_revision"])

    def test_a_corrupt_history_record_is_a_clean_error_not_a_traceback(self):
        self.build(["2026-10-26T10:00:00+00:00", "2026-10-26T11:00:00+00:00"])
        connection = sqlite3.connect(self.path)
        connection.execute("UPDATE decision_history SET entry_json = '{}' WHERE revision = 2")
        connection.commit()
        connection.close()
        for arguments in (("as-of", "2026-10-26T12:00:00Z"), ("show", "alpha")):
            output, error = StringIO(), StringIO()
            with patch("sys.stdout", output), patch("sys.stderr", error):
                code = main(["decisions", "--db", str(self.path), *arguments])
            self.assertEqual(2, code, arguments)
            self.assertEqual("", output.getvalue(), arguments)
            self.assertIn("unreadable record", error.getvalue())
            self.assertNotIn(str(self.root), error.getvalue())

    def test_decision_text_outside_the_stdout_code_page_is_ascii_escaped(self):
        store = SQLiteDecisionStore(self.path)
        try:
            with patch.object(decision_graph, "_now", side_effect=["2026-10-26T10:00:00+00:00"]):
                DecisionGraph(store).create_decision(
                    decision_id="alpha", question="Choose A → B?", alternatives=ALTERNATIVES, constraints=(),
                    required_criteria=("safe",), idempotency_key="create-alpha",
                )
        finally:
            store.close()
        raw = io.BytesIO()
        narrow = io.TextIOWrapper(raw, encoding="ascii")  # strict, like a redirected cp1252 or ASCII stdout
        with patch("sys.stdout", narrow), patch("sys.stderr", StringIO()):
            code = main(["decisions", "--db", str(self.path), "as-of", "2026-10-26T12:00:00Z", "--ids", "alpha"])
            narrow.flush()
        self.assertEqual(0, code)
        entry = json.loads(raw.getvalue().decode("ascii"))["decisions"][0]
        self.assertEqual("Choose A → B?", entry["snapshot"]["question"])


if __name__ == "__main__":
    unittest.main()
