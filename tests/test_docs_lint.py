import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from inonu_harness.cli import main
from inonu_harness.docs_lint import lint


REPO_ROOT = Path(__file__).resolve().parents[1]


def snapshot(directory):
    return {
        str(path.relative_to(directory)): (path.is_dir(), path.read_bytes() if path.is_file() else None)
        for path in sorted(directory.rglob("*"))
    }


class LintCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.parent = Path(directory.name)
        self.root = self.parent / "repo"
        self.root.mkdir()

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def rules(self, **limits):
        return [(finding["rule"], finding["file"], finding["line"]) for finding in lint(self.root, **limits)["findings"]]

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main(["docs", "lint", *args])
        return status, out.getvalue(), err.getvalue()

    def messy_tree(self):
        self.write("CLAUDE.md", "@nope.md\n[b](nope.md)\n[a](gone.md)\n")
        self.write("AGENTS.md", "[x](docs/zz.md) [y](docs/aa.md)\n")
        self.write("docs/deep/page.md", "[u](../../missing.md)\n")
        self.write("docs/bad.md", b"\xff")
        self.write("README.md", "[r](docs/none.md)\n")

    def link_directory(self, target, link):
        """Point link at target as a symlink or, on Windows, a junction; skip the test when neither can be made."""
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            # Windows needs a privilege for symlinks but not for a directory junction, which resolves the same way.
            made = os.name == "nt" and subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=False,
            ).returncode == 0
            if not made:
                self.skipTest("directory links are not available on this host")


class RuleTests(LintCase):
    def test_broken_link_reports_file_and_line(self):
        self.write("AGENTS.md", "# Index\n\nSee [guide](docs/missing.md).\n")
        self.assertEqual([("link_broken", "AGENTS.md", 3)], self.rules())

    def test_instruction_file_byte_limit_applies_only_to_instruction_files(self):
        self.write("AGENTS.md", "x" * 21)
        self.assertEqual([("instruction_file_too_large", "AGENTS.md", None)], self.rules(max_bytes=20))
        self.assertEqual([], self.rules(max_bytes=21))
        self.write("README.md", "x" * 500)
        self.assertEqual([], self.rules(max_bytes=21))

    def test_instruction_file_line_limit(self):
        self.write("CLAUDE.md", "a\nb\n")
        self.assertEqual([], self.rules(max_lines=2))
        self.write("CLAUDE.md", "a\nb\nc\n")
        self.assertEqual([("instruction_file_too_long", "CLAUDE.md", None)], self.rules(max_lines=2))

    def test_default_limits_are_the_documented_values(self):
        self.write("AGENTS.md", "x" * 32768)
        self.assertEqual([], self.rules())
        self.write("AGENTS.md", "x" * 32769)
        self.assertEqual([("instruction_file_too_large", "AGENTS.md", None)], self.rules())
        self.write("AGENTS.md", "x\n" * 200)
        self.assertEqual([], self.rules())
        self.write("AGENTS.md", "x\n" * 201)
        self.assertEqual([("instruction_file_too_long", "AGENTS.md", None)], self.rules())

    def test_import_missing_reports_line_and_skips_global_and_absolute_imports(self):
        self.write("present.md", "ok\n")
        self.write("CLAUDE.md", "# Notes\n@missing.md\n@present.md\n@~/global.md\n@/abs/x.md\n@a b\n")
        self.assertEqual([("import_missing", "CLAUDE.md", 2)], self.rules())

    def test_import_outside_root_and_byte_order_mark_are_handled(self):
        (self.parent / "outside.md").write_text("x", encoding="utf-8")
        self.write("AGENTS.md", "@../outside.md\n")
        self.assertEqual([("import_missing", "AGENTS.md", 1)], self.rules())
        self.assertIn("outside the root", lint(self.root)["findings"][0]["detail"])
        self.write("AGENTS.md", b"\xef\xbb\xbf@missing.md\n")
        self.assertEqual([("import_missing", "AGENTS.md", 1)], self.rules())

    def test_imports_outside_instruction_files_and_inside_fences_are_not_checked(self):
        self.write("docs/guide.md", "@missing.md\n")
        self.write("AGENTS.md", "```\n@missing.md\n```\n")
        self.assertEqual([], self.rules())

    def test_non_utf8_file_is_unreadable(self):
        self.write("docs/bad.md", b"caf\xe9\n")
        self.assertEqual([("file_unreadable", "docs/bad.md", None)], self.rules())

    def test_link_escape_outside_root_is_reported(self):
        (self.parent / "outside.md").write_text("x", encoding="utf-8")
        self.write("AGENTS.md", "[up](../outside.md)\n[ghost](../nothing.md)\n")
        self.assertEqual([("link_escapes_root", "AGENTS.md", 1), ("link_escapes_root", "AGENTS.md", 2)], self.rules())

    def test_symlink_out_of_root_is_reported_and_not_followed(self):
        (self.parent / "outside.md").write_text("[x](missing.md)\n", encoding="utf-8")
        try:
            (self.root / "docs").mkdir()
            os.symlink(self.parent / "outside.md", self.root / "docs" / "linked.md")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available on this platform")
        self.assertEqual([("link_escapes_root", "docs/linked.md", None)], self.rules())


class ParsingTests(LintCase):
    def test_fences_inside_list_items_and_block_quotes_are_code(self):
        self.write("CLAUDE.md", "- Example:\n\n    ```\n    @missing.md\n    [a](gone.md)\n    ```\n\n> ```\n> [b](gone.md)\n> ```\n")
        self.assertEqual([], self.rules())

    def test_a_line_that_only_looks_like_a_fence_does_not_hide_the_rest(self):
        self.write("AGENTS.md", "```x``` see below\n[a](gone.md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 2)], self.rules())
        self.write("CLAUDE.md", "```a``` note\n@missing.md\n")
        self.assertIn(("import_missing", "CLAUDE.md", 2), self.rules())

    def test_a_closing_fence_may_have_trailing_spaces_but_not_text(self):
        self.write("AGENTS.md", "```\n[a](gone.md)\n```   \n[b](gone.md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 4)], self.rules())
        self.write("AGENTS.md", "```\n[a](gone.md)\n```x\n[b](gone.md)\n```\n[c](gone.md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 6)], self.rules())

    def test_balanced_parentheses_and_angle_bracket_targets(self):
        self.write("docs/a(1).md", "x\n")
        self.write("docs/my file.md", "x\n")
        self.write("AGENTS.md", "[x](docs/a(1).md)\n[y](<docs/my file.md>)\n[z]: <docs/my file.md> \"t\"\n[w](docs/a(2).md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 4)], self.rules())

    def test_titles_after_the_target_are_ignored(self):
        self.write("docs/ok.md", "x\n")
        self.write("AGENTS.md", "[x](docs/ok.md \"title\") [y](docs/ok.md 'title')\n")
        self.assertEqual([], self.rules())

    def test_carriage_return_line_endings_give_real_line_numbers(self):
        self.write("AGENTS.md", "a\rb\r[x](gone.md)\r")
        self.assertEqual([("link_broken", "AGENTS.md", 3)], self.rules())
        self.write("CLAUDE.md", "a\r\nb\r\n@missing.md\r\n")
        self.assertIn(("import_missing", "CLAUDE.md", 3), self.rules())

    def test_a_very_long_line_is_linted_in_linear_time(self):
        self.write("AGENTS.md", "[" * 100000 + "\n" + "[a](" * 5000 + "\n")
        import time

        began = time.monotonic()
        lint(self.root)
        self.assertLess(time.monotonic() - began, 5)

    def test_link_case_must_match_exactly_on_every_host(self):
        self.write("docs/Guide.md", "x\n")
        self.write("AGENTS.md", "[ok](docs/Guide.md)\n[bad](docs/guide.md)\n[dir](Docs/Guide.md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 2), ("link_broken", "AGENTS.md", 3)], self.rules())

    def test_backslash_targets_are_reported_on_every_host(self):
        self.write("docs/ok.md", "x\n")
        self.write("AGENTS.md", "[x](docs\\ok.md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 1)], self.rules())

    def test_markdown_suffix_is_matched_case_insensitively(self):
        self.write("docs/PAGE.MD", "[a](gone.md)\n")
        self.assertEqual([("link_broken", "docs/PAGE.MD", 1)], self.rules())

    def test_findings_are_sorted_by_file_then_line_then_rule(self):
        self.write("docs/b.md", "[x](gone.md)\n")
        self.write("docs/a/x.md", "[y](gone.md)\n[z](gone2.md)\n")
        self.write("AGENTS.md", "[w](gone.md)\n")
        self.assertEqual(
            [("link_broken", "AGENTS.md", 1), ("link_broken", "docs/a/x.md", 1), ("link_broken", "docs/a/x.md", 2),
             ("link_broken", "docs/b.md", 1)],
            self.rules(),
        )

    def test_a_directory_link_that_leaves_the_root_is_reported_and_not_read(self):
        outside = self.parent / "outside"
        outside.mkdir()
        (outside / "secret.md").write_text("[x](gone.md)\n", encoding="utf-8")
        (self.root / "docs").mkdir()
        self.link_directory(outside, self.root / "docs" / "linked")
        self.assertEqual([("link_escapes_root", "docs/linked", None)], self.rules())


class SkipTests(LintCase):
    def test_fenced_blocks_and_inline_code_are_skipped(self):
        self.write("AGENTS.md", "```md\n[a](missing.md)\n```\n~~~\n[b](missing.md)\n~~~\nUse `[c](missing.md)` here.\n")
        self.assertEqual([], self.rules())

    def test_fence_closes_only_with_same_character(self):
        self.write("AGENTS.md", "~~~\n[a](missing.md)\n```\n[b](missing.md)\n~~~\n[c](missing.md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 6)], self.rules())

    def test_fence_closes_only_with_at_least_the_opening_length(self):
        self.write("AGENTS.md", "````\n```\n[a](missing.md)\n````\n[b](missing.md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 5)], self.rules())

    def test_reference_definitions_and_images_are_checked(self):
        self.write("docs/ok.md", "x\n")
        self.write("AGENTS.md", "![logo](docs/logo.png)\n[guide]: docs/ok.md\n[gone]: docs/gone.md \"Title\"\n")
        self.assertEqual([("link_broken", "AGENTS.md", 1), ("link_broken", "AGENTS.md", 3)], self.rules())

    def test_fragment_and_query_are_removed_before_checking(self):
        self.write("docs/ok.md", "x\n")
        self.write("AGENTS.md", "[a](docs/ok.md#section)\n[b](docs/ok.md?plain=1)\n[c](docs/nope.md#s)\n[d](#top)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 3)], self.rules())
        self.assertIn("docs/nope.md#s", lint(self.root)["findings"][0]["detail"])

    def test_scheme_fragment_and_absolute_targets_are_skipped(self):
        self.write(
            "AGENTS.md",
            "[a](https://example.com/x)\n[b](mailto:a@example.com)\n[c](#top)\n"
            "[d](/abs/path.md)\n[e](C:/tools/x.md)\n[f](\\\\server\\share)\n",
        )
        self.assertEqual([], self.rules())

    def test_percent_escapes_are_decoded_before_checking(self):
        self.write("docs/my file.md", "x\n")
        self.write("AGENTS.md", "[ok](docs/my%20file.md)\n[bad](docs/my%20gone.md)\n")
        self.assertEqual([("link_broken", "AGENTS.md", 2)], self.rules())

    def test_targets_resolve_relative_to_the_linking_file(self):
        self.write("docs/guide/a.md", "[up](../b.md) [sibling](c.md)\n")
        self.write("docs/b.md", "x\n")
        self.write("docs/guide/c.md", "x\n")
        self.assertEqual([], self.rules())


class SkillTests(LintCase):
    def test_skill_at_the_byte_limit_is_reported_and_one_byte_less_is_not(self):
        self.write("skills/x/SKILL.md", "x" * 19999)
        self.assertEqual([], self.rules(max_bytes=1, max_lines=1))  # the instruction limits do not apply to skills
        self.write("skills/x/SKILL.md", "x" * 20000)
        self.assertEqual([("skill_file_too_large", "skills/x/SKILL.md", None)], self.rules())

    def test_skill_at_the_line_limit_is_reported_and_one_line_less_is_not(self):
        self.write("skills/x/SKILL.md", "x\n" * 499)
        self.assertEqual([], self.rules())
        self.write("skills/x/SKILL.md", "x\n" * 500)
        self.assertEqual([("skill_file_too_long", "skills/x/SKILL.md", None)], self.rules())

    def test_skill_nested_below_another_folder_is_read(self):
        self.write("skills/outer/inner/SKILL.md", "x" * 20000)
        self.assertEqual([("skill_file_too_large", "skills/outer/inner/SKILL.md", None)], self.rules())

    def test_links_in_a_skill_are_relative_to_its_own_directory(self):
        self.write("skills/x/refs/guide.md", "x\n")
        self.write("docs/guide.md", "x\n")
        self.write("skills/x/SKILL.md", "[own](refs/guide.md)\n[up](../../docs/guide.md)\n[root](docs/guide.md)\n[gone](refs/none.md)\n")
        self.assertEqual([("link_broken", "skills/x/SKILL.md", 3), ("link_broken", "skills/x/SKILL.md", 4)], self.rules())

    def test_skill_in_a_linked_directory_outside_the_root_is_not_read(self):
        outside = self.parent / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text("x" * 20000 + "\n[x](gone.md)\n", encoding="utf-8")
        (self.root / "skills").mkdir()
        self.link_directory(outside, self.root / "skills" / "linked")
        self.assertEqual([("link_escapes_root", "skills/linked", None)], self.rules())

    def test_only_skill_md_under_skills_is_read_and_a_skill_under_docs_is_an_ordinary_document(self):
        self.write("skills/x/notes.md", "x" * 20000)
        self.write("docs/x/SKILL.md", "x\n" * 500 + "x" * 20000)
        self.assertEqual([], self.rules())

    def test_skill_size_is_measured_in_bytes_not_characters(self):
        self.write("skills/x/SKILL.md", "é" * 10000)  # two bytes per character: 20,000 bytes
        self.assertEqual([("skill_file_too_large", "skills/x/SKILL.md", None)], self.rules())
        self.write("skills/x/SKILL.md", "é" * 9999)
        self.assertEqual([], self.rules())

    def test_skill_file_name_is_matched_in_any_case(self):
        self.write("skills/x/skill.md", "x" * 20000)
        self.write("skills/y/Skill.MD", "x\n" * 500)
        self.assertEqual(
            [("skill_file_too_large", "skills/x/skill.md", None), ("skill_file_too_long", "skills/y/Skill.MD", None)],
            self.rules(),
        )

    def test_a_skill_folder_that_cannot_be_listed_is_reported_and_never_read_as_empty(self):
        self.write("skills/open/SKILL.md", "x" * 20000)
        self.write("skills/locked/SKILL.md", "x" * 20000)
        real_scandir = os.scandir

        def denied(path="."):
            if os.path.basename(os.fspath(path)) == "locked":
                raise PermissionError(13, "permission denied", os.fspath(path))
            return real_scandir(path)

        with mock.patch("os.scandir", denied):
            self.assertEqual(
                [("directory_unreadable", "skills/locked", None), ("skill_file_too_large", "skills/open/SKILL.md", None)],
                self.rules(),
            )

    def test_a_skills_folder_that_is_a_link_inside_the_root_is_read_through_the_link(self):
        self.write("real/x/SKILL.md", "x" * 20000)
        self.link_directory(self.root / "real", self.root / "skills")
        self.assertEqual([("skill_file_too_large", "skills/x/SKILL.md", None)], self.rules())

    def test_a_link_below_skills_to_a_folder_outside_skills_but_inside_the_root_is_followed(self):
        self.write("agents/big/SKILL.md", "x" * 20000)
        (self.root / "skills").mkdir()
        self.link_directory(self.root / "agents" / "big", self.root / "skills" / "alias")
        self.assertEqual([("skill_file_too_large", "skills/alias/SKILL.md", None)], self.rules())

    def test_a_link_below_skills_to_a_folder_that_is_already_below_skills_is_read_once(self):
        self.write("skills/real/SKILL.md", "x" * 20000)
        self.link_directory(self.root / "skills" / "real", self.root / "skills" / "alias")
        self.assertEqual([("skill_file_too_large", "skills/real/SKILL.md", None)], self.rules())

    def test_two_links_to_the_same_folder_are_read_once_and_a_cycle_ends(self):
        self.write("agents/big/SKILL.md", "x" * 20000)
        (self.root / "skills").mkdir()
        self.link_directory(self.root / "agents" / "big", self.root / "skills" / "a")
        self.link_directory(self.root / "agents" / "big", self.root / "skills" / "b")
        self.link_directory(self.root / "skills", self.root / "agents" / "big" / "back")
        self.assertEqual(1, len(self.rules()))

    def test_a_docs_folder_that_is_a_link_inside_the_root_keeps_its_own_path_in_findings(self):
        self.write("real_docs/a.md", "[x](gone.md)\n")
        self.link_directory(self.root / "real_docs", self.root / "docs")
        self.assertEqual([("link_broken", "docs/a.md", 1)], self.rules())

    def test_a_skill_that_cannot_be_read_is_a_finding_and_not_an_exception(self):
        self.write("skills/x/SKILL.md", "fine\n")
        real = Path.read_bytes

        def denied(path):
            if path.name == "SKILL.md":
                raise PermissionError
            return real(path)

        with mock.patch.object(Path, "read_bytes", denied):
            self.assertEqual([("file_unreadable", "skills/x/SKILL.md", None)], self.rules())

    def test_skill_size_counts_bytes_and_not_characters(self):
        self.write("skills/x/SKILL.md", "é" * 10000)  # 10,000 characters, 20,000 bytes
        self.assertEqual([("skill_file_too_large", "skills/x/SKILL.md", None)], self.rules())
        self.write("skills/x/SKILL.md", "é" * 9999)
        self.assertEqual([], self.rules())

    def test_a_skills_folder_that_is_a_link_outside_the_root_is_reported_and_not_read(self):
        outside = self.parent / "outside"
        (outside / "x").mkdir(parents=True)
        (outside / "x" / "SKILL.md").write_text("x" * 20000, encoding="utf-8")
        self.link_directory(outside, self.root / "skills")
        self.assertEqual([("link_escapes_root", "skills/x/SKILL.md", None)], self.rules())

    def test_a_skill_file_that_is_a_link_outside_the_root_is_reported_and_not_read(self):
        outside = self.parent / "outside.md"
        outside.write_text("[x](gone.md)\n" + "x" * 20000, encoding="utf-8")
        (self.root / "skills" / "x").mkdir(parents=True)
        try:
            os.symlink(outside, self.root / "skills" / "x" / "SKILL.md")
        except (OSError, NotImplementedError):
            self.skipTest("file symbolic links are not available on this host")
        self.assertEqual([("link_escapes_root", "skills/x/SKILL.md", None)], self.rules())

    def test_a_skill_file_that_resolves_outside_the_root_is_reported_without_creating_a_link(self):
        self.write("skills/x/SKILL.md", "x" * 20000)
        outside = self.parent / "outside.md"
        real_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            if path.name == "SKILL.md" and path.parent.name == "x":
                return outside
            return real_resolve(path, *args, **kwargs)

        with mock.patch.object(Path, "resolve", resolve):
            self.assertEqual([("link_escapes_root", "skills/x/SKILL.md", None)], self.rules())


class ContractTests(LintCase):
    def test_findings_are_sorted_by_file_line_and_rule(self):
        self.messy_tree()
        keys = [(f["file"], f["line"] or 0, f["rule"]) for f in lint(self.root)["findings"]]
        self.assertGreater(len(keys), 4)
        self.assertEqual(sorted(keys), keys)

    def test_report_shape_and_files_checked(self):
        self.write("AGENTS.md", "x\n")
        self.write("docs/a.md", "x\n")
        self.write("docs/sub/b.md", "x\n")
        self.write("docs/c.txt", "x\n")
        self.assertEqual({"schema_version": 1, "status": "pass", "files_checked": 3, "findings": []}, lint(self.root))
        self.write("AGENTS.md", "[x](gone.md)\n")
        report = lint(self.root)
        self.assertEqual("fail", report["status"])
        self.assertEqual({"detail", "file", "line", "remediation", "rule"}, set(report["findings"][0]))

    def test_output_is_deterministic_and_has_no_absolute_path(self):
        self.messy_tree()
        first = self.cli("--root", str(self.root))
        self.assertEqual(first, self.cli("--root", str(self.root)))
        output = first[1]
        self.assertNotIn(self.parent.name, output)
        for finding in json.loads(output)["findings"]:
            self.assertFalse(finding["file"].startswith("/") or ":" in finding["file"] or "\\" in finding["file"])

    def test_lint_writes_nothing(self):
        self.messy_tree()
        before = snapshot(self.parent)
        lint(self.root)
        self.cli("--root", str(self.root))
        self.assertEqual(before, snapshot(self.parent))


class CliTests(LintCase):
    def test_exit_0_for_pass_and_1_for_fail(self):
        self.write("AGENTS.md", "x\n")
        status, output, _ = self.cli("--root", str(self.root))
        self.assertEqual((0, "pass"), (status, json.loads(output)["status"]))
        self.write("AGENTS.md", "[x](gone.md)\n")
        status, output, _ = self.cli("--root", str(self.root))
        self.assertEqual((1, "fail"), (status, json.loads(output)["status"]))

    def test_default_root_is_the_current_directory(self):
        self.write("AGENTS.md", "[x](gone.md)\n")
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            status, output, _ = self.cli()
        finally:
            os.chdir(cwd)
        self.assertEqual(1, status)
        self.assertEqual(["AGENTS.md"], [finding["file"] for finding in json.loads(output)["findings"]])

    def test_invalid_root_and_limits_exit_2_with_empty_stdout(self):
        self.write("AGENTS.md", "x\n")
        cases = {
            "missing root": ["--root", str(self.parent / "absent")],
            "root is a file": ["--root", str(self.root / "AGENTS.md")],
            "zero bytes": ["--root", str(self.root), "--max-bytes", "0"],
            "negative lines": ["--root", str(self.root), "--max-lines", "-1"],
        }
        for name, args in cases.items():
            with self.subTest(name):
                status, output, error = self.cli(*args)
                self.assertEqual(2, status)
                self.assertEqual("", output)
                self.assertTrue(error.startswith("inonu-harness: "))
                self.assertNotIn(self.parent.name, error)

    def test_non_integer_limit_is_an_argparse_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["docs", "lint", "--max-lines", "many"])
        self.assertEqual(2, raised.exception.code)

    def test_library_rejects_invalid_root_and_limits(self):
        with self.assertRaises(ValueError):
            lint(self.parent / "absent")
        with self.assertRaises(ValueError):
            lint(self.root, max_bytes=0)
        with self.assertRaises(ValueError):
            lint(self.root, max_lines=0)


class RepositoryTests(unittest.TestCase):
    def test_repository_passes_its_own_lint(self):
        report = lint(REPO_ROOT)
        self.assertGreater(report["files_checked"], 0)
        self.assertEqual(
            "pass", report["status"],
            "repository lint findings:\n" + json.dumps(report["findings"], indent=2, sort_keys=True),
        )

    def test_cli_lints_this_repository_with_exit_0(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main(["docs", "lint", "--root", str(REPO_ROOT)])
        self.assertEqual(0, status, out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main()
