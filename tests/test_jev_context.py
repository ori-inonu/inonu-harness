import hashlib
import io
import json
import os
import random
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from inonu_harness.cli import main
from inonu_harness.jev import JevAdapter, MockJevTransport, _length, _validate_spec
from inonu_harness.jev_context import FACT_LIMIT, build_spec


def decision(**changes):
    value = {
        "id": "store-choice",
        "goal": "Choose local persistence",
        "facts": {"runtime": "python-stdlib"},
        "rails": ["No remote service"],
        "options": [
            {"id": "sqlite", "label": "SQLite", "what": "Persist locally"},
            {"id": "json", "label": "JSON", "what": "Use a local file"},
        ],
    }
    value.update(changes)
    return value


def plan(spec_id):
    return {"specId": spec_id, "plannedCalls": 12, "estimatedInputTokens": 500}


def run_receipt(spec_id):
    return {
        "receipt": {
            "v": 1,
            "specId": spec_id,
            "specHash": "a" * 64,
            "status": "consenso",
            "leader": "sqlite",
            "implement": True,
        }
    }


class JevSpecTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.write_text("decision.json", json.dumps(decision()))

    def write_bytes(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def write_text(self, name, text):
        return self.write_bytes(name, text.encode("utf-8"))

    def chunks_for(self, text):
        self.write_text("doc.md", text)
        spec = build_spec(decision(), ["doc.md"], self.root, max_facts=10_000)
        return [value for key, value in spec["facts"].items() if key != "doc1_source" and key.startswith("doc1_")]

    def run_cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                status = main(["jev", "spec", *arguments])
            except SystemExit as exc:  # argparse exits 2 for a missing required flag
                status = exc.code
        return status, stdout.getvalue(), stderr.getvalue()

    def spec_arguments(self, *documents, root=None, extra=()):
        arguments = ["--decision", str(self.root / "decision.json"), "--root", str(root or self.root)]
        for document in documents:
            arguments += ["--doc", document]
        return [*arguments, *extra]

    def refused(self, *documents, root=None, extra=()):
        status, stdout, stderr = self.run_cli(*self.spec_arguments(*documents, root=root, extra=extra))
        self.assertEqual(2, status, stderr)
        self.assertEqual("", stdout)
        return stderr

    def snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes() if path.is_file() else None
            for path in self.root.rglob("*")
        }


class ChunkingTests(JevSpecTestCase):
    def test_lines_of_299_300_and_301_characters_keep_their_text(self):
        self.assertEqual(["x" * 299], self.chunks_for("x" * 299))
        self.assertEqual(["x" * 300], self.chunks_for("x" * 300))
        self.assertEqual(["x" * 299, "y"], self.chunks_for("x" * 299 + " y"))
        self.assertEqual(["x" * 300, "x"], self.chunks_for("x" * 301))

    def test_chunks_join_back_to_the_collapsed_text(self):
        text = "\r\n".join(
            f"Line {number:02d}\tfirst  part " + "word  " * (number % 9 + 2) for number in range(40)
        ) + "\n\n   \n"
        collapsed = "\n".join(" ".join(line.split()) for line in text.split("\n") if line.split())
        chunks = self.chunks_for(text)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= FACT_LIMIT for chunk in chunks))
        self.assertEqual(collapsed, "\n".join(chunks))

    def test_long_line_splits_after_a_sentence_end(self):
        line = "A" * 70 + ". " + "B" * 200 + ". " + "C" * 100
        self.assertEqual(["A" * 70 + ". " + "B" * 200 + ".", "C" * 100], self.chunks_for(line))

    def test_sentence_end_before_the_sixtieth_character_is_not_a_cut(self):
        line = "A. " + " ".join(["word"] * 80)
        chunks = self.chunks_for(line)
        self.assertGreater(len(chunks[0]), 60)
        self.assertTrue(chunks[0].startswith("A. word"))
        self.assertEqual(line.split(), " ".join(chunks).split())

    def test_long_line_without_sentence_ends_splits_at_a_space(self):
        line = " ".join(["ab"] * 200)
        chunks = self.chunks_for(line)
        self.assertTrue(all(len(chunk) <= FACT_LIMIT for chunk in chunks))
        self.assertEqual(line, " ".join(chunks))

    def test_long_line_with_no_space_splits_at_the_limit(self):
        chunks = self.chunks_for("x" * 700)
        self.assertEqual([300, 300, 100], [len(chunk) for chunk in chunks])
        self.assertEqual("x" * 700, "".join(chunks))

    def test_last_piece_of_a_long_line_packs_with_the_next_line(self):
        self.assertEqual(["x" * 300, "x" * 100 + "\nshort line"], self.chunks_for("x" * 400 + "\nshort line"))

    def test_chunks_lose_nothing_and_fit_the_limit_as_the_judge_counts_it(self):
        rng = random.Random(7)
        words = ["alpha", "b", "gamma.", "delta", "x" * 25, "é", "\U0001F600", "end.", "z" * 310, "é"]
        for case in range(60):
            lines = [" ".join(rng.choice(words) for _ in range(rng.randint(1, 120))) for _ in range(rng.randint(1, 6))]
            text = "\n".join(lines)
            chunks = self.chunks_for(text)
            with self.subTest(case=case):
                self.assertTrue(all(_length(chunk) <= FACT_LIMIT for chunk in chunks))
                self.assertEqual("".join(text.split()), "".join("".join(chunk.split()) for chunk in chunks))

    def test_two_lines_that_fill_a_fact_exactly_pack_and_one_more_character_does_not(self):
        self.assertEqual(["a" * 149 + "\n" + "b" * 150], self.chunks_for("a" * 149 + "\n" + "b" * 150))
        self.assertEqual(["a" * 149, "b" * 151], self.chunks_for("a" * 149 + "\n" + "b" * 151))

    def test_the_sentence_cut_starts_at_the_sixtieth_character(self):
        words = " ".join(["word"] * 80)
        self.assertGreater(len(self.chunks_for("A" * 59 + ". " + words)[0]), 200)
        self.assertEqual("A" * 60 + ".", self.chunks_for("A" * 60 + ". " + words)[0])

    def test_emoji_count_two_units_so_no_fact_exceeds_the_limit_as_the_judge_counts_it(self):
        chunks = self.chunks_for("\U0001F600" * 200)
        self.assertEqual([150, 50], [len(chunk) for chunk in chunks])
        _validate_spec(decision(facts={"edge": "\U0001F600" * 150}))
        _validate_spec(decision(goal="\U0001F600" * 300))
        for refused in (decision(facts={"edge": "\U0001F600" * 151}), decision(goal="\U0001F600" * 301)):
            with self.assertRaises(ValueError):
                _validate_spec(refused)

    def test_a_cut_never_separates_a_letter_from_its_combining_mark(self):
        chunks = self.chunks_for("x" * 299 + "é" + "tail")
        self.assertEqual("x" * 299, chunks[0])
        self.assertTrue(chunks[1].startswith("é"))

    def test_a_byte_order_mark_is_dropped_and_a_lone_cr_ends_a_line(self):
        self.assertEqual(["First line\nsecond line\nthird"], self.chunks_for("﻿First line\rsecond line\r\nthird\n"))

    def test_a_decision_file_with_a_byte_order_mark_is_read(self):
        self.write_text("a.md", "Text.\n")
        self.write_bytes("decision.json", b"\xef\xbb\xbf" + json.dumps(decision()).encode("utf-8"))
        status, stdout, stderr = self.run_cli(*self.spec_arguments("a.md"))
        self.assertEqual(0, status, stderr)
        self.assertEqual("store-choice", json.loads(stdout)["id"])

    def test_non_ascii_text_is_kept_and_printed_as_ascii(self):
        self.write_text("doc.md", "Café — naïve 日本語 😀\n")
        stream = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
        with redirect_stdout(stream):
            status = main(["jev", "spec", *self.spec_arguments("doc.md")])
        stream.flush()
        printed = stream.buffer.getvalue().decode("ascii")
        self.assertEqual(0, status)
        self.assertEqual("Café — naïve 日本語 😀", json.loads(printed)["facts"]["doc1_001"])


class SourceAndOrderTests(JevSpecTestCase):
    def test_source_fact_holds_the_relative_path_and_digest(self):
        data = "Stored text.\n".encode("utf-8")
        self.write_bytes("specs/storage.md", data)
        spec = build_spec(decision(), ["specs/storage.md"], self.root)
        digest = hashlib.sha256(data).hexdigest()[:16]
        self.assertEqual(f"specs/storage.md sha256:{digest}", spec["facts"]["doc1_source"])

    def test_documents_keep_the_order_given(self):
        self.write_text("a.md", "First.\n")
        self.write_text("b.md", "Second.\n")
        spec = build_spec(decision(), ["b.md", "a.md"], self.root)
        self.assertEqual(
            ["doc1_source", "doc1_001", "doc2_source", "doc2_001"],
            [key for key in spec["facts"] if key.startswith("doc")],
        )
        self.assertTrue(spec["facts"]["doc1_source"].startswith("b.md "))
        self.assertEqual("Second.", spec["facts"]["doc1_001"])
        self.assertEqual("First.", spec["facts"]["doc2_001"])

    def test_decision_facts_keep_their_keys_beside_the_generated_ones(self):
        self.write_text("a.md", "Text.\n")
        spec = build_spec(decision(facts={"runtime": "python-stdlib", "limit": 3}), ["a.md"], self.root)
        self.assertEqual("python-stdlib", spec["facts"]["runtime"])
        self.assertEqual(3, spec["facts"]["limit"])
        self.assertIn("doc1_source", spec["facts"])

    def test_decision_fact_with_a_generated_key_is_refused(self):
        self.write_text("a.md", "Text.\n")
        for key in ("doc1_001", "doc1_source", "doc12_source"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    build_spec(decision(facts={key: "x"}), ["a.md"], self.root)
                self.write_text("decision.json", json.dumps(decision(facts={key: "x"})))
                self.refused("a.md")


def option(ident="a", label="A", what="A"):
    return {"id": ident, "label": label, "what": what}


class RefusalTests(JevSpecTestCase):
    def test_without_a_document_exits_2_with_nothing_on_stdout(self):
        status, stdout, stderr = self.run_cli("--decision", str(self.root / "decision.json"), "--root", str(self.root))
        self.assertEqual(2, status)
        self.assertEqual("", stdout)
        self.assertIn("--doc", stderr)

    def test_missing_document_is_refused(self):
        self.assertIn("document 1", self.refused("missing.md"))

    def test_directory_is_refused(self):
        (self.root / "folder").mkdir()
        self.assertIn("document 1", self.refused("folder"))

    def test_symbolic_link_is_refused(self):
        self.write_text("real.md", "Text.\n")
        try:
            os.symlink(self.root / "real.md", self.root / "link.md")
        except OSError as exc:
            self.skipTest(f"this host cannot create symbolic links: {exc}")
        self.assertIn("document 1 is a symbolic link", self.refused("link.md"))

    def test_path_reported_as_a_link_is_refused(self):
        self.write_text("a.md", "Text.\n")
        with patch.object(Path, "is_symlink", return_value=True):
            self.assertIn("document 1 is a symbolic link", self.refused("a.md"))

    def test_document_outside_the_root_is_refused(self):
        self.write_text("outside.md", "Text.\n")
        inner = self.root / "inner"
        inner.mkdir()
        self.assertIn("document 1 resolves outside --root", self.refused("../outside.md", root=inner))
        self.assertIn("document 1 resolves outside --root", self.refused(str(self.root / "outside.md"), root=inner))

    def test_duplicate_document_is_refused_even_under_another_spelling(self):
        self.write_text("a.md", "Text.\n")
        self.assertIn("document 2 is given twice", self.refused("a.md", "a.md"))
        self.assertIn("document 2 is given twice", self.refused("a.md", "./a.md"))

    def test_a_hard_link_to_a_document_given_before_is_a_duplicate(self):
        self.write_text("a.md", "Text.\n")
        try:
            os.link(self.root / "a.md", self.root / "b.md")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"this host cannot create hard links: {exc}")
        self.assertIn("document 2 is given twice", self.refused("a.md", "b.md"))

    def test_a_name_with_a_colon_in_its_last_part_is_refused_even_when_it_reads(self):
        self.write_text("a.md", "Visible text.\n")
        self.write_text("a.md:stream", "Hidden text.\n")  # an alternate data stream on NTFS, a plain name elsewhere
        self.assertIn("document 1 is not a regular file", self.refused("a.md:stream"))

    def test_a_misspelled_top_level_key_is_refused_instead_of_dropped(self):
        self.write_text("a.md", "Text.\n")
        with self.assertRaises(ValueError):
            build_spec({**decision(), "forbiden": ["sqlite"]}, ["a.md"], self.root)
        self.write_text("decision.json", json.dumps({**decision(), "forbiden": ["sqlite"]}))
        self.refused("a.md")

    def test_a_secret_split_by_a_fact_boundary_is_still_refused(self):
        key, value = "pass" + "word", "=" + "planted-" + "value-123"
        token = "s" + "k-" + "a" * 20
        for text in ("x" * 280 + f" {key}\n{value}\n", "A" * 291 + f"-{key}{value}\n", "A" * 291 + f"-{token}\n"):
            with self.subTest(text=text[-30:]):
                self.write_text("a.md", text)
                self.assertIn("contains a sensitive value", self.refused("a.md"))

    def test_common_token_formats_are_refused(self):
        samples = {
            "github": "gh" + "p_" + "A" * 36,
            "aws": "AK" + "IA" + "B" * 16,
            "bearer": "Authorization: Bear" + "er " + "c" * 30,
            "pem": "-----BEGIN " + "PRIVATE KEY-----",
            "slack": "xo" + "xb-" + "1234567890-abc",
            "google": "AI" + "za" + "d" * 35,
            "jwt": "ey" + "JhbGciOiJIUzI1NiJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkwIn0" + "." + "abcdefghij",
        }
        for name, sample in samples.items():
            with self.subTest(format=name):
                self.write_text("a.md", f"Note before.\n{sample}\nNote after.\n")
                stderr = self.refused("a.md")
                self.assertIn("document 1 contains a sensitive value", stderr)
                self.assertNotIn(sample, stderr)

    def test_document_that_is_not_utf8_is_refused(self):
        self.write_bytes("a.md", b"Caf\xe9 text\n")
        self.assertIn("document 1 is not valid UTF-8", self.refused("a.md"))

    def test_nul_character_is_refused(self):
        self.write_bytes("a.md", b"abc\x00def\n")
        self.assertIn("document 1 contains a NUL character", self.refused("a.md"))

    def test_document_over_64_KiB_is_refused_and_exactly_64_KiB_is_read(self):
        self.write_bytes("big.md", b"a" * (64 * 1024 + 1))
        self.assertIn("document 1 is larger than", self.refused("big.md"))
        self.write_bytes("edge.md", b"a" * (64 * 1024))
        status, stdout, stderr = self.run_cli(*self.spec_arguments("edge.md", extra=("--max-facts", "1000")))
        self.assertEqual(0, status, stderr)
        chunks = [value for key, value in json.loads(stdout)["facts"].items() if key.startswith("doc1_") and key != "doc1_source"]
        self.assertEqual("a" * (64 * 1024), "".join(chunks))

    def test_document_without_text_is_refused(self):
        self.write_text("blank.md", "  \n\t\n")
        self.assertIn("document 1 contains no text", self.refused("blank.md"))

    def test_planted_credential_is_refused_without_being_echoed(self):
        planted = "pass" + "word" + "=" + "planted-" + "value"
        self.write_text("a.md", f"Setup note.\n{planted}\n")
        stderr = self.refused("a.md")
        self.assertIn("document 1 contains a sensitive value", stderr)
        self.assertNotIn("planted-value", stderr)
        self.assertNotIn("password", stderr)

    def test_planted_token_is_refused_without_being_echoed(self):
        token = "s" + "k-" + "a" * 20
        self.write_text("a.md", f"Key {token} is here.\n")
        stderr = self.refused("a.md")
        self.assertIn("document 1 contains a sensitive value", stderr)
        self.assertNotIn(token, stderr)

    def test_sensitive_decision_text_is_refused_without_being_echoed(self):
        self.write_text("a.md", "Text.\n")
        self.write_text("decision.json", json.dumps(decision(goal="api" + "_key=placeholder")))
        stderr = self.refused("a.md")
        self.assertIn("sensitive value", stderr)
        self.assertNotIn("placeholder", stderr)

    def test_invalid_decision_files_are_refused(self):
        self.write_text("a.md", "Text.\n")
        without_options = {key: value for key, value in decision().items() if key != "options"}
        duplicate = json.dumps(decision()).replace('"goal"', '"goal": "first", "goal"', 1)
        for raw in ("[1, 2]", '{"id": ', '{"id": "a", "id": "b"}', duplicate, json.dumps(without_options)):
            with self.subTest(raw=raw[:24]):
                self.write_text("decision.json", raw)
                self.refused("a.md")

    def test_oversized_decision_file_is_refused(self):
        self.write_text("a.md", "Text.\n")
        padding = lambda size: json.dumps(decision()).encode("utf-8") + b" " * (size - len(json.dumps(decision())))
        self.write_bytes("decision.json", padding(64 * 1024 + 1))
        self.assertIn("larger than", self.refused("a.md"))
        self.write_bytes("decision.json", padding(64 * 1024))
        status, _, stderr = self.run_cli(*self.spec_arguments("a.md"))
        self.assertEqual(0, status, stderr)

    def test_missing_decision_file_is_refused(self):
        self.write_text("a.md", "Text.\n")
        status, stdout, _ = self.run_cli("--decision", str(self.root / "absent.json"), "--root", str(self.root), "--doc", "a.md")
        self.assertEqual(2, status)
        self.assertEqual("", stdout)

    def test_fact_option_and_goal_over_the_jev_limits_are_refused(self):
        self.write_text("a.md", "Text.\n")
        cases = {
            "fact": decision(facts={"long": "x" * (FACT_LIMIT + 1)}),
            "goal": decision(goal="x" * 601),
            "option what": decision(options=[{"id": "a", "label": "A", "what": "x" * 401}, {"id": "b", "label": "B", "what": "B"}]),
            "option label": decision(options=[{"id": "a", "label": "x" * 121, "what": "A"}, {"id": "b", "label": "B", "what": "B"}]),
            "rails": decision(rails=["x"] * 13),
            "options": decision(options=[{"id": "a", "label": "A", "what": "A"}]),
        }
        for name, raw in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    build_spec(raw, ["a.md"], self.root)

    def test_every_jev_limit_is_enforced_at_its_edge(self):
        self.write_text("a.md", "Text.\n")
        eight = [option(f"o{number}") for number in range(8)]
        edges = {
            "id": (decision(id="x0" * 20), decision(id="x0" * 20 + "x")),
            "goal": (decision(goal="g" * 600), decision(goal="g" * 601)),
            "fact": (decision(facts={"k": "f" * 300}), decision(facts={"k": "f" * 301})),
            "rail": (decision(rails=["r" * 300]), decision(rails=["r" * 301])),
            "rails": (decision(rails=["r"] * 12), decision(rails=["r"] * 13)),
            "option id": (decision(options=[option("x0" * 20), option("b")]), decision(options=[option("x0" * 20 + "x"), option("b")])),
            "option label": (decision(options=[option(label="l" * 120), option("b")]), decision(options=[option(label="l" * 121), option("b")])),
            "option what": (decision(options=[option(what="w" * 400), option("b")]), decision(options=[option(what="w" * 401), option("b")])),
            "options": (decision(options=eight), decision(options=[*eight, option("o8")])),
            "unknown ask": (
                decision(unknowns=[{"id": "u", "ask": "q" * 300}]), decision(unknowns=[{"id": "u", "ask": "q" * 301}]),
            ),
        }
        for name, (accepted, refused) in edges.items():
            with self.subTest(limit=name):
                build_spec(accepted, ["a.md"], self.root)
                with self.assertRaises(ValueError):
                    build_spec(refused, ["a.md"], self.root)
        with self.assertRaises(ValueError):
            build_spec(decision(facts={"k": float("nan")}), ["a.md"], self.root)

    def test_the_default_fact_budget_is_80_including_the_source_fact(self):
        self.write_text("a.md", "\n".join(f"{number:03d} " + "y" * 250 for number in range(79)))
        status, stdout, stderr = self.run_cli(*self.spec_arguments("a.md"))
        self.assertEqual(0, status, stderr)
        self.assertEqual(80, len([key for key in json.loads(stdout)["facts"] if key.startswith("doc1_")]))
        self.write_text("a.md", "\n".join(f"{number:03d} " + "y" * 250 for number in range(80)))
        self.assertIn("need 81 facts", self.refused("a.md"))

    def test_max_facts_refuses_without_truncating(self):
        self.write_text("a.md", "\n".join(f"Line {number} " + "y" * 250 for number in range(3)))
        stderr = self.refused("a.md", extra=("--max-facts", "3"))
        self.assertIn("need 4 facts", stderr)
        self.assertIn("limit of 3", stderr)
        status, stdout, stderr = self.run_cli(*self.spec_arguments("a.md", extra=("--max-facts", "4")))
        self.assertEqual(0, status, stderr)
        self.assertEqual(4, len([key for key in json.loads(stdout)["facts"] if key.startswith("doc1_")]))


class OutputTests(JevSpecTestCase):
    def test_output_is_identical_across_runs_and_compact(self):
        self.write_text("a.md", "Alpha text here.\n")
        self.write_text("b.md", "Beta text here.\n")
        first = self.run_cli(*self.spec_arguments("a.md", "b.md"))
        second = self.run_cli(*self.spec_arguments("a.md", "b.md"))
        self.assertEqual(0, first[0], first[2])
        self.assertEqual(first, second)
        self.assertTrue(first[1].endswith("\n"))
        self.assertIn('"id":"store-choice"', first[1])

    def test_nothing_is_written(self):
        self.write_text("a.md", "Text.\n")
        before = self.snapshot()
        status, _, stderr = self.run_cli(*self.spec_arguments("a.md"))
        self.assertEqual(0, status, stderr)
        self.assertEqual(before, self.snapshot())

    def test_output_passes_validation_and_the_mock_transport_accepts_it(self):
        self.write_text("a.md", "Stored text for the judge.\n")
        status, stdout, stderr = self.run_cli(*self.spec_arguments("a.md"))
        self.assertEqual(0, status, stderr)
        spec = json.loads(stdout)
        self.assertEqual(spec, _validate_spec(spec))
        transport = MockJevTransport({"consensus_plan": plan(spec["id"]), "consensus_run": run_receipt(spec["id"])})
        result = JevAdapter(transport).recommend(spec)
        self.assertEqual("recommended", result.status)
        self.assertEqual([spec, spec], [arguments["spec"] for _, arguments, _ in transport.calls])

    def test_fact_limit_matches_the_validator(self):
        _validate_spec(decision(facts={"edge": "x" * FACT_LIMIT}))
        with self.assertRaises(ValueError):
            _validate_spec(decision(facts={"edge": "x" * (FACT_LIMIT + 1)}))


if __name__ == "__main__":
    unittest.main()
