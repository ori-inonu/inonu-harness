import io
import json
from io import StringIO
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from inonu_harness.cli import main
from inonu_harness.decision_graph import Alternative, CriterionResult, DecisionGraph, EvidenceReference
from inonu_harness.sqlite_store import SQLiteDecisionStore


ALTERNATIVES = (Alternative("a", "A"), Alternative("b", "B"))


def create(graph, decision_id, dependencies=(), question=None):
    graph.create_decision(
        decision_id=decision_id,
        question=question or f"Question for {decision_id}?",
        alternatives=ALTERNATIVES,
        constraints=(),
        required_criteria=("safe",),
        dependencies=dependencies,
        idempotency_key=f"create-{decision_id}",
    )


def authorize(graph, decision_id):
    graph.recommend(
        decision_id,
        alternative_id="a",
        source="test",
        version="1",
        provenance="local recommendation",
        idempotency_key=f"recommend-{decision_id}",
    )
    graph.authorize(
        decision_id,
        alternative_id="a",
        actor="owner",
        criteria={
            "safe": CriterionResult(True, (EvidenceReference("test", "checks/safe", "local test", criterion_id="safe"),))
        },
        idempotency_key=f"authorize-{decision_id}",
    )


class DecisionsReadyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "decisions.sqlite"
        store = SQLiteDecisionStore(self.path)
        try:
            graph = DecisionGraph(store)
            create(graph, "authorized-one")
            authorize(graph, "authorized-one")
            create(graph, "blocked-one")
            graph.block_decision("blocked-one", reason="waiting for the owner", idempotency_key="block-blocked-one")
            create(graph, "root")
            create(graph, "invalidated-one", dependencies=("root",))
            graph.revise(
                "root",
                question="Revised question for root?",
                relevant_premise_changed=True,
                idempotency_key="revise-root",
            )
            create(graph, "free")
            create(graph, "waits-on-root", dependencies=("root",))
            create(graph, "waits-on-blocked", dependencies=("blocked-one",))
            create(graph, "waits-on-invalidated", dependencies=("invalidated-one",))
            create(graph, "waits-on-several", dependencies=("root", "blocked-one", "invalidated-one"))
            create(graph, "waits-on-authorized", dependencies=("authorized-one",))
            create(graph, "vanished")
            create(graph, "orphan", dependencies=("vanished",))
        finally:
            store.close()
        # A dependency cannot be created or left dangling through the API, so the one row is removed directly.
        connection = sqlite3.connect(self.path)
        connection.execute("DELETE FROM decisions WHERE decision_id = ?", ("vanished",))
        connection.commit()
        connection.close()
        self.before = self.path.read_bytes()

    def run_cli(self, *arguments, db=None):
        output, error = StringIO(), StringIO()
        with patch("sys.stdout", output), patch("sys.stderr", error):
            code = main(["decisions", "--db", str(db or self.path), *arguments])
        return code, output.getvalue(), error.getvalue()

    def ready(self, db=None):
        code, output, error = self.run_cli("ready", db=db)
        self.assertEqual((0, ""), (code, error))
        return json.loads(output)

    @staticmethod
    def entry(result, section, decision_id):
        return next(item for item in result[section] if item["id"] == decision_id)

    def test_empty_database_lists_nothing(self):
        path = self.root / "empty.sqlite"
        SQLiteDecisionStore(path).close()
        self.assertEqual({"schema_version": 1, "ready": [], "waiting": []}, self.ready(db=path))

    def test_decisions_without_dependencies_are_ready(self):
        result = self.ready()
        self.assertEqual({"id": "free", "question": "Question for free?", "dependencies": []}, self.entry(result, "ready", "free"))
        self.assertEqual({"id": "root", "question": "Revised question for root?", "dependencies": []}, self.entry(result, "ready", "root"))

    def test_waiting_on_a_pending_dependency(self):
        self.assertEqual(
            {"id": "waits-on-root", "question": "Question for waits-on-root?", "waiting_on": [{"id": "root", "status": "pending"}]},
            self.entry(self.ready(), "waiting", "waits-on-root"),
        )

    def test_waiting_on_a_blocked_dependency(self):
        self.assertEqual(
            [{"id": "blocked-one", "status": "blocked"}],
            self.entry(self.ready(), "waiting", "waits-on-blocked")["waiting_on"],
        )

    def test_waiting_on_an_invalidated_dependency(self):
        self.assertEqual(
            [{"id": "invalidated-one", "status": "invalidated"}],
            self.entry(self.ready(), "waiting", "waits-on-invalidated")["waiting_on"],
        )

    def test_waiting_on_several_dependencies_keeps_the_declared_order(self):
        self.assertEqual(
            [
                {"id": "root", "status": "pending"},
                {"id": "blocked-one", "status": "blocked"},
                {"id": "invalidated-one", "status": "invalidated"},
            ],
            self.entry(self.ready(), "waiting", "waits-on-several")["waiting_on"],
        )

    def test_a_decision_whose_dependency_is_authorized_is_ready(self):
        self.assertEqual(
            {"id": "waits-on-authorized", "question": "Question for waits-on-authorized?", "dependencies": ["authorized-one"]},
            self.entry(self.ready(), "ready", "waits-on-authorized"),
        )

    def test_becomes_ready_once_its_dependency_is_authorized(self):
        store = SQLiteDecisionStore(self.path)
        try:
            authorize(DecisionGraph(store), "root")
        finally:
            store.close()
        result = self.ready()
        self.assertEqual(["free", "waits-on-authorized", "waits-on-root"], [item["id"] for item in result["ready"]])
        self.assertNotIn("root", [item["id"] for item in result["ready"] + result["waiting"]])
        self.assertEqual(
            [{"id": "blocked-one", "status": "blocked"}, {"id": "invalidated-one", "status": "invalidated"}],
            self.entry(result, "waiting", "waits-on-several")["waiting_on"],
        )

    def test_authorized_blocked_and_invalidated_decisions_are_not_listed(self):
        result = self.ready()
        listed = {item["id"] for item in result["ready"] + result["waiting"]}
        for decision_id in ("authorized-one", "blocked-one", "invalidated-one"):
            self.assertNotIn(decision_id, listed)

    def test_both_lists_are_sorted_by_id(self):
        result = self.ready()
        self.assertEqual(["free", "root", "waits-on-authorized"], [item["id"] for item in result["ready"]])
        self.assertEqual(
            ["orphan", "waits-on-blocked", "waits-on-invalidated", "waits-on-root", "waits-on-several"],
            [item["id"] for item in result["waiting"]],
        )

    def test_a_dependency_missing_from_the_database_has_status_missing(self):
        self.assertEqual(
            [{"id": "vanished", "status": "missing"}],
            self.entry(self.ready(), "waiting", "orphan")["waiting_on"],
        )

    def test_output_is_one_json_object_with_the_documented_keys(self):
        result = self.ready()
        self.assertEqual({"schema_version", "ready", "waiting"}, set(result))
        self.assertEqual(1, result["schema_version"])
        self.assertEqual({"id", "question", "dependencies"}, set(result["ready"][0]))
        self.assertEqual({"id", "question", "waiting_on"}, set(result["waiting"][0]))
        self.assertEqual({"id", "status"}, set(result["waiting"][0]["waiting_on"][0]))

    def test_output_is_deterministic(self):
        self.assertEqual(self.run_cli("ready"), self.run_cli("ready"))

    def test_queries_leave_the_database_bytes_and_directory_unchanged(self):
        files_before = sorted(entry.name for entry in self.root.iterdir())
        self.ready()
        self.ready()
        self.assertEqual(self.before, self.path.read_bytes())
        self.assertEqual(files_before, sorted(entry.name for entry in self.root.iterdir()))

    def test_non_ascii_question_text_survives_a_strict_ascii_stdout(self):
        question = "Choose A → B, então Ação?"
        store = SQLiteDecisionStore(self.path)
        try:
            create(DecisionGraph(store), "unicode-one", question=question)
        finally:
            store.close()
        raw = io.BytesIO()
        narrow = io.TextIOWrapper(raw, encoding="ascii")  # strict, like a redirected cp1252 or ASCII stdout
        with patch("sys.stdout", narrow), patch("sys.stderr", StringIO()):
            code = main(["decisions", "--db", str(self.path), "ready"])
            narrow.flush()
        self.assertEqual(0, code)
        self.assertEqual(question, self.entry(json.loads(raw.getvalue().decode("ascii")), "ready", "unicode-one")["question"])

    def test_invalid_or_unreadable_stores_exit_2_with_empty_stdout_and_no_path(self):
        bad_database = self.root / "not-a-database.sqlite"
        bad_database.write_bytes(b"x" * 200)
        unsupported = self.root / "unsupported.sqlite"
        connection = sqlite3.connect(unsupported)
        connection.execute("PRAGMA user_version = 2")
        connection.close()
        corrupt = self.root / "corrupt.sqlite"
        corrupt.write_bytes(self.before)
        connection = sqlite3.connect(corrupt)
        connection.execute("UPDATE decisions SET state_json = '{}' WHERE decision_id = 'free'")
        connection.commit()
        connection.close()
        missing = self.root / "missing" / "decisions.sqlite"
        for database in (bad_database, unsupported, corrupt, missing):
            code, output, error = self.run_cli("ready", db=database)
            self.assertEqual(2, code, database)
            self.assertEqual("", output, database)
            self.assertNotIn(str(self.root), error, database)
        self.assertFalse((self.root / "missing").exists())
        self.assertIn("unreadable record", self.run_cli("ready", db=corrupt)[2])

    def corrupt(self, sql, *parameters):
        database = self.root / "corrupt-case.sqlite"
        database.write_bytes(self.before)
        connection = sqlite3.connect(database)
        connection.execute(sql, parameters)
        connection.commit()
        connection.close()
        return database

    def assert_unreadable(self, database):
        code, output, error = self.run_cli("ready", db=database)
        self.assertEqual((2, ""), (code, output), error)
        self.assertIn("unreadable record", error)
        self.assertNotIn("Traceback", error)
        self.assertNotIn(str(self.root), error)

    def set_field(self, decision_id, field, value):
        """Rewrite one field of a stored decision record (the value is stored as given, bypassing the API)."""
        source = sqlite3.connect(self.path)
        state = json.loads(source.execute("SELECT state_json FROM decisions WHERE decision_id = ?", (decision_id,)).fetchone()[0])
        source.close()
        state[field] = value
        return self.corrupt("UPDATE decisions SET state_json = ? WHERE decision_id = ?", json.dumps(state), decision_id)

    def test_dependencies_stored_in_the_wrong_shape_are_refused_not_read_as_none(self):
        for bad in ("", {}, "root", None, 5, ["root", ""], ["root", 3]):
            with self.subTest(dependencies=bad):
                self.assert_unreadable(self.set_field("waits-on-root", "dependencies", bad))

    def test_other_list_fields_stored_in_the_wrong_shape_are_refused(self):
        for field in ("constraints", "required_criteria", "invalidated_by", "alternatives", "evidence"):
            for bad in ("text", {}, 7):
                with self.subTest(field=field, value=bad):
                    self.assert_unreadable(self.set_field("free", field, bad))

    def test_a_status_typo_or_an_unknown_status_is_refused_instead_of_hiding_a_decision(self):
        for bad in ("pendng", "", None, "PENDING"):
            with self.subTest(status=bad):
                self.assert_unreadable(self.set_field("free", "status", bad))

    def test_a_record_whose_id_does_not_match_its_row_is_refused(self):
        self.assert_unreadable(self.set_field("free", "id", "root"))

    def test_json_that_is_invalid_or_nested_too_deeply_is_refused_with_the_generic_message(self):
        for text in ("not json", "[" * 200000 + "]" * 200000, "", "null"):
            with self.subTest(text=text[:12]):
                self.assert_unreadable(self.corrupt("UPDATE decisions SET state_json = ? WHERE decision_id = 'free'", text))

    def test_every_reading_command_refuses_a_corrupt_record_the_same_way(self):
        database = self.set_field("free", "dependencies", "root")
        for arguments in (("list",), ("show", "free"), ("history", "free")):
            code, output, error = self.run_cli(*arguments, db=database)
            self.assertEqual((2, ""), (code, output), arguments)
            self.assertNotIn("Traceback", error)

    def test_a_history_entry_that_belongs_to_another_decision_is_refused(self):
        database = self.root / "history-case.sqlite"
        database.write_bytes(self.before)
        connection = sqlite3.connect(database)
        row = connection.execute(
            "SELECT revision, entry_json FROM decision_history WHERE decision_id = 'free' ORDER BY revision LIMIT 1"
        ).fetchone()
        entry = json.loads(row[1])
        entry["decision_id"] = "root"
        entry["snapshot"]["id"] = "root"  # consistent with itself, so only the comparison with the row can refuse it
        connection.execute(
            "UPDATE decision_history SET entry_json = ? WHERE decision_id = 'free' AND revision = ?",
            (json.dumps(entry), row[0]),
        )
        connection.commit()
        connection.close()
        for arguments in (("show", "free"), ("history", "free"), ("as-of", "2100-01-01T00:00:00Z")):
            code, output, error = self.run_cli(*arguments, db=database)
            self.assertEqual((2, ""), (code, output), arguments)
            self.assertIn("unreadable record", error)

    def test_ids_are_sorted_by_code_point_with_mixed_case_and_punctuation(self):
        store = SQLiteDecisionStore(self.root / "mixed.sqlite")
        try:
            graph = DecisionGraph(store)
            for name in ("Zeta", "alpha", "1st", "a-b", "a.b", "a_b", "a:b", "Alpha"):
                create(graph, name)
        finally:
            store.close()
        ids = [item["id"] for item in self.ready(db=self.root / "mixed.sqlite")["ready"]]
        self.assertEqual(sorted(ids), ids)
        self.assertEqual(["1st", "Alpha", "Zeta", "a-b", "a.b", "a:b", "a_b", "alpha"], ids)

    def test_a_missing_database_next_to_existing_files_is_never_created(self):
        absent = self.root / "absent.sqlite"
        code, output, _ = self.run_cli("ready", db=absent)
        self.assertEqual((2, ""), (code, output))
        self.assertFalse(absent.exists())

    def test_ready_only_looks_at_direct_dependencies_and_does_not_authorize_anything(self):
        store = SQLiteDecisionStore(self.root / "chain.sqlite")
        try:
            graph = DecisionGraph(store)
            create(graph, "c-upstream")
            create(graph, "b-middle", dependencies=("c-upstream",))
            create(graph, "a-downstream", dependencies=("b-middle",))
            authorize(graph, "b-middle")  # the graph does not require its dependencies to be authorized first
        finally:
            store.close()
        result = self.ready(db=self.root / "chain.sqlite")
        self.assertIn("a-downstream", [item["id"] for item in result["ready"]])
        self.assertIn("c-upstream", [item["id"] for item in result["ready"]])

    def test_ready_takes_no_extra_arguments(self):
        output, error = StringIO(), StringIO()
        with patch("sys.stdout", output), patch("sys.stderr", error), self.assertRaises(SystemExit) as raised:
            main(["decisions", "--db", str(self.path), "ready", "--ids", "free"])  # argparse usage error
        self.assertEqual(2, raised.exception.code)
        self.assertEqual("", output.getvalue())


if __name__ == "__main__":
    unittest.main()
