from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from inonu_harness.cli import main
from inonu_harness.decision_graph import Alternative, DecisionGraph
from inonu_harness.secret_scan import scan
from inonu_harness.sqlite_store import SQLiteDecisionStore


# Every credential-looking value is assembled here at run time from short fragments, so the repository holds none.
def fill(alphabet: str, length: int) -> str:
    return (alphabet * length)[:length]


def github_token() -> str:
    return "gh" + "p_" + fill("Qw8Z", 36)


RULE_NAMES = (
    "private_key_block",
    "aws_access_key_id",
    "github_token",
    "slack_token",
    "google_api_key",
    "stripe_live_key",
    "anthropic_key",
    "openai_style_key",
    "jwt",
    "bearer_token",
    "credential_assignment",
)

SAMPLES = (
    ("private_key_block", "-----" + "BEGIN " + "RSA " + "PRIVATE " + "KEY-----"),
    ("aws_access_key_id", "AK" + "IA" + "Q7W8E9R2T3Y4U5I6"),
    ("github_token", github_token()),
    ("github_token", "github" + "_pat_" + fill("Qw8_", 22)),
    ("slack_token", "xox" + "b-" + fill("Qw8-", 10)),
    ("google_api_key", "AI" + "za" + fill("Qw8_-", 35)),
    ("stripe_live_key", "sk" + "_live_" + fill("Qw8Z", 16)),
    ("anthropic_key", "sk-" + "ant-" + fill("Qw8_-", 20)),
    ("openai_style_key", "sk-" + fill("Qw8Z", 32)),
    ("openai_style_key", "sk-" + "proj-" + fill("Qw8Z", 32)),
    ("jwt", "eyJ" + fill("Qw8_-", 10) + "." + fill("Qw8_-", 10) + "." + fill("Qw8_-", 10)),
    ("bearer_token", "Bearer " + fill("Qw8._~", 20)),
    ("credential_assignment", "api" + "_key" + "=" + fill("Qw8_-/+=.", 16)),
    ("credential_assignment", '"password": "' + fill("Qw8_-/+=.", 16) + '"'),
)

NEAR_MISSES = (
    ("aws one short", "AK" + "IA" + fill("Q7W8E9R2T3Y4U5I", 15)),
    ("github one short", "gh" + "p_" + fill("Qw8Z", 35)),
    ("slack one short", "xox" + "b-" + fill("Qw8-", 9)),
    ("google one short", "AI" + "za" + fill("Qw8_-", 34)),
    ("stripe one short", "sk" + "_live_" + fill("Qw8Z", 15)),
    ("anthropic one short", "sk-" + "ant-" + fill("Qw8_-", 19)),
    ("sk prefix too short", "sk-" + fill("Qw8Z", 31)),
    ("base64 without eyJ", fill("Qw8_-", 10) + "." + fill("Qw8_-", 10) + "." + fill("Qw8_-", 10)),
    ("bearer short", "Bearer " + fill("Qw8._~", 19)),
    ("short assignment value", "token: " + fill("Qw8_-", 15)),
    ("password in prose", "Remember to rotate the password before Friday."),
    ("bare keyword", "password"),
)


def _database(directory: str, question: str) -> Path:
    path = Path(directory) / "decisions.sqlite"
    store = SQLiteDecisionStore(path)
    try:
        DecisionGraph(store).create_decision(
            decision_id="choice-a",
            question=question,
            alternatives=(Alternative("option-a", "Option A"), Alternative("option-b", "Option B")),
            constraints=("keep-local",),
            required_criteria=("reviewed",),
            idempotency_key="create-choice-a",
        )
    finally:
        store.close()
    return path


def _run(argv: list[str]) -> tuple[int, str, str]:
    output, error = StringIO(), StringIO()
    with patch("sys.stdout", output), patch("sys.stderr", error):
        code = main(argv)
    return code, output.getvalue(), error.getvalue()


class SecretScanTests(unittest.TestCase):
    def assertNoWindow(self, text: str, secret: str, width: int = 8) -> None:
        for start in range(len(secret) - width + 1):
            self.assertNotIn(secret[start:start + width], text)

    def test_each_rule_matches_its_synthetic_value(self):
        for rule, value in SAMPLES:
            with self.subTest(rule=rule):
                self.assertIn({"rule": rule, "path": "field"}, scan({"field": value}))
        self.assertEqual(set(RULE_NAMES), {rule for rule, _ in SAMPLES})

    def test_near_misses_do_not_match(self):
        for label, value in NEAR_MISSES:
            with self.subTest(label=label):
                self.assertEqual([], scan({"field": value}))

    def test_paths_show_indices_and_mask_keys_that_are_not_identifiers(self):
        secret = github_token()
        value = {"task": {"prompt": "plain"}, "items": [{"ok": "plain"}, {"text": secret}], "Odd Key": {"nested": secret}}

        self.assertEqual(
            [
                {"rule": "github_token", "path": "*.nested"},
                {"rule": "github_token", "path": "items[1].text"},
            ],
            scan(value),
        )

    def test_keys_are_scanned_and_a_key_holding_credential_text_is_masked(self):
        identifier_shaped = "gh" + "p_" + fill("abc", 36)  # 40 lowercase characters: a plain identifier by shape

        self.assertEqual([{"rule": "github_token", "path": "*"}], scan({identifier_shaped: "plain"}))
        self.assertEqual([{"rule": "github_token", "path": "ok_key"}], scan({"ok_key": github_token()}))

    def test_other_types_and_root_strings_are_ignored_or_reported_at_the_root(self):
        self.assertEqual([], scan({1: "plain", "number": 3, "flag": True, "none": None}))
        self.assertEqual([{"rule": "github_token", "path": ""}], scan(github_token()))

    def test_findings_are_sorted_without_duplicates_and_deterministic(self):
        value = {"b": [github_token(), github_token()], "a": github_token()}

        first = scan(value)

        self.assertEqual([{"rule": "github_token", "path": "a"}, {"rule": "github_token", "path": "b[0]"}, {"rule": "github_token", "path": "b[1]"}], first)
        self.assertEqual(first, scan(value))

    def test_cyclic_or_deeply_nested_values_are_refused(self):
        cyclic: list = []
        cyclic.append(cyclic)
        deep: object = "plain"
        for _ in range(300):
            deep = [deep]

        with self.assertRaises(ValueError):
            scan(cyclic)
        with self.assertRaises(ValueError):
            scan(deep)

    def test_megabyte_near_misses_scan_within_two_seconds(self):
        size = 1_000_000
        texts = (
            "eyJ" * (size // 3),
            "sk-" * (size // 3),
            "a" * size,
            ("token=" + "a" * 15 + " ") * (size // 23),
            ("secret" + "x" * 40 + "=" + "y" * 15 + " ") * (size // 62),
            "Bearer " * (size // 7),
            ("AKIA" + "Q" * 15 + "a") * (size // 21),
        )
        for text in texts:
            with self.subTest(prefix=text[:12]):
                started = time.perf_counter()
                self.assertEqual([], scan({"value": text}))
                self.assertLess(time.perf_counter() - started, 2.0)

    def test_packet_refuses_credential_in_task_prompt_with_empty_stdout(self):
        secret = github_token()
        with tempfile.TemporaryDirectory() as directory:
            database = _database(directory, "Which option?")
            task_path = Path(directory) / "task.json"
            task_path.write_text(
                json.dumps({"task_id": "planning.storage", "config_id": "sdd.manual.v1", "prompt": f"Call with {secret}"}),
                encoding="utf-8",
            )
            argv = ["decisions", "--db", str(database), "packet", "--task-file", str(task_path), "--ids", "choice-a"]

            code, output, error = _run([*argv, "--refuse-secret-patterns"])
            repeat = _run([*argv, "--refuse-secret-patterns"])

        self.assertEqual(2, code)
        self.assertEqual("", output)
        self.assertEqual("inonu-harness: refused to print credential-like text: github_token at task.prompt\n", error)
        self.assertEqual(repeat, (code, output, error))
        self.assertNoWindow(output + error, secret)
        self.assertNotIn(str(task_path), error)

    def test_context_refuses_credential_in_decision_field_with_empty_stdout(self):
        secret = github_token()
        with tempfile.TemporaryDirectory() as directory:
            database = _database(directory, f"Use {secret} for the release?")
            code, output, error = _run(
                ["decisions", "--db", str(database), "context", "--ids", "choice-a", "--refuse-secret-patterns"]
            )

        self.assertEqual(2, code)
        self.assertEqual("", output)
        self.assertEqual(
            "inonu-harness: refused to print credential-like text: github_token at decisions[0].question\n",
            error,
        )
        self.assertNoWindow(output + error, secret)

    def test_clean_output_is_byte_identical_with_and_without_the_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            database = _database(directory, "Which storage option?")
            task_path = Path(directory) / "task.json"
            task_path.write_text(
                json.dumps({"task_id": "planning.storage", "config_id": "sdd.manual.v1", "prompt": "Plan the note."}),
                encoding="utf-8",
            )
            for argv in (
                ["context", "--ids", "choice-a"],
                ["packet", "--task-file", str(task_path), "--ids", "choice-a"],
            ):
                with self.subTest(command=argv[0]):
                    plain = _run(["decisions", "--db", str(database), *argv])
                    flagged = _run(["decisions", "--db", str(database), *argv, "--refuse-secret-patterns"])

                    self.assertEqual((0, plain[1], ""), plain)
                    self.assertEqual(plain, flagged)

    def test_secret_bearing_output_is_unchanged_without_the_flag(self):
        secret = github_token()
        with tempfile.TemporaryDirectory() as directory:
            database = _database(directory, f"Use {secret} for the release?")
            task_path = Path(directory) / "task.json"
            task_path.write_text(
                json.dumps({"task_id": "planning.storage", "config_id": "sdd.manual.v1", "prompt": f"Call with {secret}"}),
                encoding="utf-8",
            )

            context_code, context_output, context_error = _run(
                ["decisions", "--db", str(database), "context", "--ids", "choice-a"]
            )
            packet_code, packet_output, packet_error = _run(
                ["decisions", "--db", str(database), "packet", "--task-file", str(task_path), "--ids", "choice-a"]
            )

        self.assertEqual((0, ""), (context_code, context_error))
        self.assertEqual((0, ""), (packet_code, packet_error))
        self.assertIn(secret, context_output)
        self.assertEqual(f"Call with {secret}", json.loads(packet_output)["task"]["prompt"])


class SecretScanGapTests(unittest.TestCase):
    def test_a_key_that_is_part_of_the_matched_value_never_reaches_a_path(self):
        key = "sk" + "_live_" + "qwertyui"
        value = key + fill("Qw8Z", 12)
        paths = [item["path"] for item in scan({key: value})]
        self.assertEqual(["*"], paths)
        nested = scan({"outer": {key: value}})
        self.assertEqual(["outer.*"], [item["path"] for item in nested])
        for finding in nested:
            for start in range(len(key) - 7):
                self.assertNotIn(key[start:start + 8], finding["path"])

    def test_a_credential_named_key_with_a_bare_value_is_found_and_the_key_stays_visible(self):
        value = fill("Qw8_-/+=.", 16)
        for name in ("password", "api_key", "secret_token"):
            with self.subTest(name=name):
                self.assertEqual([{"rule": "credential_assignment", "path": name}], scan({name: value}))
        self.assertEqual([], scan({"password": "too short"}))
        self.assertEqual([], scan({"password": "correct horse battery staple"}))
        self.assertEqual([], scan({"title": fill("Qw8_-/+=.", 40)}))

    def test_aws_ids_need_word_boundaries(self):
        body = "Q7W8E9R2T3Y4U5I6"
        self.assertEqual(["aws_access_key_id"], [item["rule"] for item in scan("key " + "AK" + "IA" + body + " end")])
        self.assertEqual([], scan("1" + "AK" + "IA" + body))
        self.assertEqual([], scan("AK" + "IA" + body + "X"))
        self.assertEqual(["aws_access_key_id"], [item["rule"] for item in scan("AS" + "IA" + body)])

    def test_keywords_are_case_insensitive_and_both_live_key_prefixes_match(self):
        self.assertEqual(
            ["credential_assignment"], [item["rule"] for item in scan("PASS" + "WORD" + "=" + fill("Qw8_-/+=.", 16))]
        )
        self.assertEqual(["stripe_live_key"], [item["rule"] for item in scan("rk" + "_live_" + fill("Qw8Z", 16))])

    def test_identifier_keys_are_shown_up_to_forty_characters(self):
        token = github_token()
        forty, forty_one = "k" * 40, "k" * 41
        self.assertEqual([forty], [item["path"] for item in scan({forty: token})])
        self.assertEqual(["*"], [item["path"] for item in scan({forty_one: token})])

    def test_findings_are_ordered_by_path_then_rule_and_masked_duplicates_collapse(self):
        token = github_token()
        found = scan({"b": token + " Bearer " + fill("Qw8._~", 20), "a": token})
        self.assertEqual(
            [("a", "github_token"), ("b", "bearer_token"), ("b", "github_token")],
            [(item["path"], item["rule"]) for item in found],
        )
        collapsed = scan({"A B": token, "C D": token})
        self.assertEqual([{"rule": "github_token", "path": "*"}], collapsed)

    def test_near_miss_inputs_finish_in_linear_time_even_if_a_pattern_regresses(self):
        # A quadratic pattern would run for minutes here, so each input runs in a child process with a hard limit.
        code = (
            "import sys; from inonu_harness.secret_scan import scan; "
            "kind = sys.argv[1]; unit = {'jwt': 'eyJ', 'github': 'gh' + 'p_', 'bearer': 'Bearer ', "
            "'assignment': 'password=', 'slack': 'xox' + 'b-', 'pem': '-----' + 'BEGIN '}[kind]; "
            "scan(unit * 100000)"
        )
        for kind in ("jwt", "github", "bearer", "assignment", "slack", "pem"):
            with self.subTest(kind=kind):
                completed = subprocess.run(
                    [sys.executable, "-c", code, kind], cwd=str(Path(__file__).resolve().parents[1]),
                    capture_output=True, text=True, timeout=30, check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)

    def test_an_unknown_token_shaped_id_is_not_echoed_when_the_guard_is_on(self):
        unknown = github_token()
        with tempfile.TemporaryDirectory() as directory:
            database = _database(directory, "Which option?")
            code, output, error = _run(
                ["decisions", "--db", str(database), "context", "--ids", unknown, "--refuse-secret-patterns"]
            )
        self.assertEqual((2, ""), (code, output))
        self.assertIn("github_token at ids[0]", error)
        for start in range(len(unknown) - 7):
            self.assertNotIn(unknown[start:start + 8], error)


if __name__ == "__main__":
    unittest.main()
