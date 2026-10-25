import json
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from inonu_harness.cli import main
from inonu_harness.decision_graph import Alternative, DecisionGraph, EvidenceReference
from inonu_harness.sqlite_store import SQLiteDecisionStore


REPO_ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_convergence_baseline_fixture_option_runs_offline(self):
        output = StringIO()
        with patch("sys.stdout", output):
            self.assertEqual(
                0,
                main([
                    "baseline", "run", "--fixture",
                    str(REPO_ROOT / "fixtures" / "baseline" / "acceptance.json"),
                    "--execution-id", "cli-acceptance",
                ]),
            )

        result = json.loads(output.getvalue())
        self.assertEqual("baseline.acceptance", result["task_id"])
        self.assertEqual("cli-acceptance", result["execution_id"])

    def test_decisions_context_emits_selected_allowlisted_json_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.sqlite"
            store = SQLiteDecisionStore(path)
            graph = DecisionGraph(store)
            for decision_id in ("first-choice", "second-choice"):
                graph.create_decision(
                    decision_id=decision_id,
                    question=f"Question for {decision_id}?",
                    alternatives=(Alternative("option-a", "Option A"), Alternative("option-b", "Option B")),
                    constraints=("keep-local",),
                    required_criteria=("reviewed",),
                    evidence=(EvidenceReference("fixture", "source.md#1", "private detail", "reviewed", "v1"),),
                    idempotency_key=f"create-{decision_id}",
                )
            graph.recommend(
                "second-choice",
                alternative_id="option-b",
                source="fixture",
                version="1",
                provenance="private recommendation detail",
                idempotency_key="recommend-second-choice",
            )
            history_before = {decision_id: graph.history(decision_id) for decision_id in ("first-choice", "second-choice")}
            bytes_before = path.read_bytes()
            output = StringIO()
            try:
                with patch("sys.stdout", output):
                    self.assertEqual(
                        0,
                        main([
                            "decisions", "--db", str(path), "context", "--ids", "second-choice", "first-choice"
                        ]),
                    )
                result = json.loads(output.getvalue())
                self.assertEqual({"status", "decisions"}, set(result))
                self.assertEqual("ready", result["status"])
                self.assertEqual(["second-choice", "first-choice"], [item["id"] for item in result["decisions"]])
                self.assertEqual(
                    {
                        "id", "revision", "question", "alternatives", "constraints", "required_criteria",
                        "dependencies", "status", "evidence", "recommendation", "authorized_alternative_id",
                        "invalidated_by", "validated_criteria",
                    },
                    set(result["decisions"][0]),
                )
                self.assertEqual(
                    {"source", "reference", "criterion_id", "version"},
                    set(result["decisions"][0]["evidence"][0]),
                )
                self.assertNotIn("private detail", output.getvalue())
                self.assertEqual("option-b", result["decisions"][0]["recommendation"]["alternative_id"])
                self.assertEqual(
                    {"alternative_id", "source", "version"},
                    set(result["decisions"][0]["recommendation"]),
                )
                self.assertIsNone(result["decisions"][0]["authorized_alternative_id"])
                self.assertEqual(bytes_before, path.read_bytes())
                self.assertEqual(
                    history_before,
                    {decision_id: graph.history(decision_id) for decision_id in ("first-choice", "second-choice")},
                )
            finally:
                store.close()

    def test_decisions_context_rejects_bad_ids_and_missing_database_without_creating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.sqlite"
            store = SQLiteDecisionStore(path)
            store.close()
            for ids in (["bad id"], ["valid-id", "valid-id"]):
                output = StringIO()
                with patch("sys.stdout", output):
                    self.assertEqual(0, main(["decisions", "--db", str(path), "context", "--ids", *ids]))
                self.assertEqual("invalid_request", json.loads(output.getvalue())["status"])

            missing = Path(directory) / "missing" / "decisions.sqlite"
            error = StringIO()
            with patch("sys.stderr", error):
                self.assertEqual(2, main(["decisions", "--db", str(missing), "context", "--ids", "valid-id"]))
            self.assertFalse(missing.exists())

    def test_decisions_context_keeps_cli_error_for_valid_but_missing_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.sqlite"
            SQLiteDecisionStore(path).close()
            error = StringIO()
            with patch("sys.stderr", error):
                self.assertEqual(
                    2,
                    main(["decisions", "--db", str(path), "context", "--ids", "well-formed-missing"]),
                )
            self.assertIn("well-formed-missing", error.getvalue())

    def test_decisions_packet_combines_task_with_selected_context_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "decisions.sqlite"
            store = SQLiteDecisionStore(path)
            graph = DecisionGraph(store)
            graph.create_decision(
                decision_id="first-choice",
                question="Which option first?",
                alternatives=(Alternative("option-a", "Option A"), Alternative("option-b", "Option B")),
                constraints=("keep-local",),
                required_criteria=("reviewed",),
                evidence=(EvidenceReference("fixture", "source.md#1", "private detail", "reviewed", "v1"),),
                idempotency_key="create-first-choice",
            )
            graph.create_decision(
                decision_id="second-choice",
                question="Which option second?",
                alternatives=(Alternative("option-a", "Option A"), Alternative("option-b", "Option B")),
                constraints=("keep-manual",),
                required_criteria=("tested",),
                idempotency_key="create-second-choice",
            )
            graph.recommend(
                "second-choice",
                alternative_id="option-b",
                source="fixture",
                version="1",
                provenance="private recommendation detail",
                idempotency_key="recommend-second-choice",
            )
            history_before = {item: graph.history(item) for item in ("first-choice", "second-choice")}
            bytes_before = path.read_bytes()
            task = {
                "task_id": "planning.storage",
                "config_id": "sdd.manual.v1",
                "prompt": "Prepare a manual planning note.",
            }
            task_path = root / "task.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            output = StringIO()
            error = StringIO()
            try:
                with patch("sys.stdout", output), patch("sys.stderr", error):
                    self.assertEqual(
                        0,
                        main([
                            "decisions", "--db", str(path), "packet", "--task-file", str(task_path),
                            "--ids", "second-choice", "first-choice",
                        ]),
                    )

                result = json.loads(output.getvalue())
                self.assertEqual({"schema_version", "task", "decision_context"}, set(result))
                self.assertEqual(1, result["schema_version"])
                self.assertEqual(task, result["task"])
                self.assertEqual({"status", "decisions"}, set(result["decision_context"]))
                self.assertEqual("ready", result["decision_context"]["status"])
                decisions = result["decision_context"]["decisions"]
                self.assertEqual(["second-choice", "first-choice"], [item["id"] for item in decisions])
                self.assertEqual("option-b", decisions[0]["recommendation"]["alternative_id"])
                self.assertIsNone(decisions[0]["authorized_alternative_id"])
                self.assertNotIn("private detail", output.getvalue())
                self.assertNotIn(str(task_path), output.getvalue() + error.getvalue())
                self.assertEqual(bytes_before, path.read_bytes())
                self.assertEqual(history_before, {item: graph.history(item) for item in history_before})
            finally:
                store.close()

    def test_decisions_packet_rejects_invalid_task_json_without_exposing_its_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "decisions.sqlite"
            SQLiteDecisionStore(database).close()
            task_path = root / "private-task.json"
            invalid_tasks = (
                "{",
                "[]",
                json.dumps({"task_id": "task", "config_id": "config"}),
                json.dumps({"task_id": "task", "config_id": "config", "prompt": 1}),
                json.dumps({"task_id": "task", "config_id": "config", "prompt": "  "}),
                json.dumps({"task_id": "task", "config_id": "config", "prompt": "ok", "secret": "extra"}),
                '{"task_id":"task","config_id":"config","prompt":"first","prompt":"second"}',
            )
            for contents in invalid_tasks:
                task_path.write_text(contents, encoding="utf-8")
                output = StringIO()
                error = StringIO()
                with patch("sys.stdout", output), patch("sys.stderr", error):
                    self.assertEqual(
                        2,
                        main([
                            "decisions", "--db", str(database), "packet", "--task-file", str(task_path),
                            "--ids", "selected-decision",
                        ]),
                    )
                self.assertEqual("", output.getvalue())
                self.assertNotIn(str(task_path), error.getvalue())

            task_path.write_bytes(b'{"task_id":"task","config_id":"config","prompt":"\xff"}')
            output = StringIO()
            error = StringIO()
            with patch("sys.stdout", output), patch("sys.stderr", error):
                self.assertEqual(
                    2,
                    main([
                        "decisions", "--db", str(database), "packet", "--task-file", str(task_path),
                        "--ids", "selected-decision",
                    ]),
                )
            self.assertEqual("", output.getvalue())
            self.assertNotIn(str(task_path), error.getvalue())

    def test_decisions_packet_does_not_create_missing_database_or_reveal_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "missing" / "decisions.sqlite"
            task_path = root / "task.json"
            task_path.write_text(
                json.dumps({"task_id": "task", "config_id": "config", "prompt": "Do the task."}),
                encoding="utf-8",
            )
            output = StringIO()
            error = StringIO()
            with patch("sys.stdout", output), patch("sys.stderr", error):
                self.assertEqual(
                    2,
                    main([
                        "decisions", "--db", str(database), "packet", "--task-file", str(task_path),
                        "--ids", "selected-decision",
                    ]),
                )
            self.assertEqual("", output.getvalue())
            self.assertFalse(database.exists())
            self.assertNotIn(str(database), error.getvalue())

    def test_decisions_packet_keeps_cli_error_for_valid_but_missing_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "decisions.sqlite"
            SQLiteDecisionStore(database).close()
            task_path = root / "task.json"
            task_path.write_text(
                json.dumps({"task_id": "task", "config_id": "config", "prompt": "Do the task."}),
                encoding="utf-8",
            )
            error = StringIO()
            with patch("sys.stderr", error):
                self.assertEqual(
                    2,
                    main([
                        "decisions", "--db", str(database), "packet", "--task-file", str(task_path),
                        "--ids", "well-formed-missing",
                    ]),
                )
            self.assertIn("well-formed-missing", error.getvalue())
            self.assertNotIn(str(task_path), error.getvalue())


if __name__ == "__main__":
    unittest.main()
