import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from inonu_harness.cli import main as cli_main
from inonu_harness.versions import INIT, MARKETPLACE, PLUGIN, PYPROJECT, audit, in_scheme, main, next_version


REPO_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_SOURCE = (REPO_ROOT / "inonu_harness" / "versions.py").read_bytes()
IDENTITY = ("-c", "user.email=t@example.test", "-c", "user.name=t")
PASSING_TEST = "import unittest\n\n\nclass SampleTests(unittest.TestCase):\n    def test_passes(self):\n        self.assertTrue(True)\n"
RUNNER = 'print("inonu-harness test")\n'
MAX_MANIFEST_BYTES = 1 << 20


def write(root, rel, content):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))


def write_manifests(root, init="1.2.3", pyproject="1.2.3", plugin="1.2.3"):
    """Write the three manifests; a None value writes the file without a version statement."""
    init_text = '"""Package."""\n' + (f'\n__version__ = "{init}"\n' if init is not None else "")
    write(root, INIT, init_text)
    write(root, PYPROJECT, '[project]\nname = "x"\n' + (f'version = "{pyproject}"\n' if pyproject is not None else ""))
    write(root, PLUGIN, json.dumps({"name": "x", **({"version": plugin} if plugin is not None else {})}))


def snapshot(root):
    return {path.relative_to(root).as_posix(): None if path.is_dir() else path.read_bytes() for path in root.rglob("*")}


def run_cli(*arguments):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = cli_main(list(arguments))
    return status, stdout.getvalue(), stderr.getvalue()


def steps_of(output):
    return [(step["name"], step["exit_code"]) for step in json.loads(output)["steps"]]


def git(repo, *arguments):
    subprocess.run(["git", "-C", str(repo), *IDENTITY, *arguments], check=True, stdin=subprocess.DEVNULL, capture_output=True)


def make_checkout(root, manifests=True, version="0.0.1"):
    """The smallest checkout that `check` accepts; without manifests it holds only the audit module (a namespace package)."""
    write(root, "tests/test_ok.py", PASSING_TEST)
    write(root, "scripts/inonu.py", RUNNER)
    write(root, "inonu_harness/versions.py", VERSIONS_SOURCE)
    if manifests:
        write_manifests(root, init=version, pyproject=version, plugin=version)
    return root


class TempCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / "checkout"
        self.root.mkdir()


class AuditTests(TempCase):
    def test_manifests_that_agree_have_no_problem(self):
        write_manifests(self.root)
        self.assertEqual([], audit(self.root))

    def test_each_manifest_that_differs_is_named_with_both_versions(self):
        cases = (
            ("init", [f"{PYPROJECT} has version 1.2.3 but {INIT} has version 9.9.9", f"{PLUGIN} has version 1.2.3 but {INIT} has version 9.9.9"]),
            ("pyproject", [f"{PYPROJECT} has version 9.9.9 but {INIT} has version 1.2.3"]),
            ("plugin", [f"{PLUGIN} has version 9.9.9 but {INIT} has version 1.2.3"]),
        )
        for keyword, expected in cases:
            with self.subTest(differs=keyword):
                write_manifests(self.root, **{keyword: "9.9.9"})
                self.assertEqual(expected, audit(self.root))

    def test_a_missing_manifest_is_skipped_and_the_rest_are_still_compared(self):
        write_manifests(self.root)
        (self.root / PYPROJECT).unlink()
        self.assertEqual([], audit(self.root))
        write_manifests(self.root, plugin="9.9.9")
        (self.root / PYPROJECT).unlink()
        self.assertEqual([f"{PLUGIN} has version 9.9.9 but {INIT} has version 1.2.3"], audit(self.root))

    def test_a_root_without_manifests_passes(self):
        self.assertEqual([], audit(self.root))

    def test_a_manifest_without_a_version_is_a_problem(self):
        for keyword, rel in (("init", INIT), ("pyproject", PYPROJECT), ("plugin", PLUGIN)):
            with self.subTest(manifest=rel):
                write_manifests(self.root, **{keyword: None})
                self.assertEqual([f"{rel} has no version"], audit(self.root))

    def test_an_unparseable_manifest_is_a_problem_that_echoes_no_file_text(self):
        write_manifests(self.root)
        write(self.root, PYPROJECT, "[project\nversion = 'SECRET'\n")
        self.assertEqual([f"{PYPROJECT} cannot be parsed as TOML"], audit(self.root))
        write_manifests(self.root)
        write(self.root, PLUGIN, '{"version": "1.2.3", "token": ')
        self.assertEqual([f"{PLUGIN} cannot be parsed as JSON"], audit(self.root))
        write_manifests(self.root)
        write(self.root, INIT, b'\xff__version__ = "1.2.3"\n')
        self.assertEqual([f"{INIT} is not valid UTF-8"], audit(self.root))

    def test_the_last_version_assignment_in_init_is_compared_and_crlf_is_read(self):
        write_manifests(self.root)
        write(self.root, INIT, '__version__ = "9.9.9"\n__version__ = "1.2.3"\n')
        self.assertEqual([], audit(self.root))
        write(self.root, INIT, b'__version__ = "1.2.3"\r\n')
        self.assertEqual([], audit(self.root))

    def test_a_version_that_is_not_plain_text_is_reported_without_its_text(self):
        write_manifests(self.root, plugin="1.2.3\x1b[2J SECRET")
        self.assertEqual([f"{PLUGIN} has no usable version"], audit(self.root))

    def test_a_version_that_is_not_a_string_or_is_longer_than_forty_characters_has_no_usable_version(self):
        write_manifests(self.root)
        write(self.root, PLUGIN, '{"version": 1}')
        self.assertEqual([f"{PLUGIN} has no usable version"], audit(self.root))
        write(self.root, PLUGIN, json.dumps({"version": "1." + "0" * 40}))
        self.assertEqual([f"{PLUGIN} has no usable version"], audit(self.root))

    def test_only_a_top_level_assignment_is_a_version_statement(self):
        write_manifests(self.root)
        write(self.root, INIT, '"""Package.\n\n__version__ = "9.9.9"\n"""\n# __version__ = "8.8.8"\n__version__ = "1.2.3"  # release\n')
        self.assertEqual([], audit(self.root))
        write(self.root, INIT, '"""Package.\n\n__version__ = "9.9.9"\n"""\n')
        self.assertEqual([f"{INIT} has no version"], audit(self.root))
        write(self.root, INIT, 'if True:\n    __version__ = "9.9.9"\n')
        self.assertEqual([f"{INIT} has no usable version"], audit(self.root))  # a rebinding in a block cannot be trusted

    def test_any_other_binding_of_the_version_is_an_unusable_version(self):
        write_manifests(self.root, init="0.0.24", pyproject="0.0.24", plugin="0.0.24")
        base = '__version__ = "0.0.24"\n'
        cases = {
            "augmented": base + '__version__ += "x"\n',
            "try": base + 'try:\n    __version__ = "9.9.9"\nexcept ImportError:\n    pass\n',
            "if": base + 'if True:\n    __version__ = "9.9.9"\n',
            "tuple": base + '__version__, other = "9.9.9", 0\n',
            "for": base + 'for __version__ in ["9.9.9"]:\n    pass\n',
            "del": base + 'del __version__\n',
            "walrus": base + '(__version__ := "9.9.9")\n',
            "import": base + 'from elsewhere import __version__\n',
            "def": base + 'def __version__():\n    pass\n',
            "class": base + 'class __version__:\n    pass\n',
            "global": base + 'def change():\n    global __version__\n    __version__ = "9.9.9"\n',
        }
        for name, source in cases.items():
            with self.subTest(case=name):
                write(self.root, INIT, source)
                self.assertEqual([f"{INIT} has no usable version"], audit(self.root, scheme=True))

    def test_the_last_top_level_assignment_wins(self):
        write_manifests(self.root)
        write(self.root, INIT, '__version__ = "9.9.9"\n__version__ = "1.2.3"\n')
        self.assertEqual([], audit(self.root))

    def test_a_forty_character_version_is_usable_and_forty_one_is_not(self):
        edge, over = "1." + "0" * 38, "1." + "0" * 39
        write_manifests(self.root, init=edge, pyproject=edge, plugin=edge)
        self.assertEqual([], audit(self.root))
        write_manifests(self.root, init=over, pyproject=over, plugin=over)
        self.assertEqual([f"{label} has no usable version" for label in (INIT, PYPROJECT, PLUGIN)], audit(self.root))

    def test_a_manifest_of_exactly_one_mebibyte_is_read_and_one_byte_more_is_refused(self):
        write_manifests(self.root)
        body = json.dumps({"name": "x", "version": "1.2.3"}).encode("utf-8")
        write(self.root, PLUGIN, body + b" " * (MAX_MANIFEST_BYTES - len(body)))
        self.assertEqual([], audit(self.root))
        write(self.root, PLUGIN, body + b" " * (MAX_MANIFEST_BYTES + 1 - len(body)))
        self.assertEqual([f"{PLUGIN} is larger than {MAX_MANIFEST_BYTES} bytes"], audit(self.root))

    def test_a_manifest_reached_through_a_link_that_leaves_the_root_is_refused_without_echoing_it(self):
        write_manifests(self.root, init="0.0.24", pyproject="0.0.24", plugin=None)
        outside = self.root.parent / (self.root.name + "-outside")
        outside.mkdir()
        self.addCleanup(lambda: [path.unlink() for path in outside.iterdir()] or outside.rmdir())
        (outside / "plugin.json").write_text(json.dumps({"version": "9.9.9"}), encoding="utf-8")
        shutil.rmtree(self.root / ".claude-plugin")
        link = self.root / ".claude-plugin"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            made = os.name == "nt" and subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True, check=False).returncode == 0
            if not made:
                self.skipTest("directory links are not available on this host")
        problems = audit(self.root)
        self.assertEqual([f"{PLUGIN} resolves outside the root", f"{MARKETPLACE} resolves outside the root"], problems)
        self.assertNotIn("9.9.9", "".join(problems))

    def test_scheme_functions_take_only_text(self):
        self.assertFalse(in_scheme(None))
        self.assertFalse(in_scheme(b"0.0.1"))
        for value in (None, 1, b"0.0.1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                next_version(value)

    def test_single_quotes_an_annotation_and_a_trailing_comment_are_read(self):
        write_manifests(self.root)
        for line in ("__version__ = '1.2.3'\n", '__version__: str = "1.2.3"  # release\n', "__version__: 'str' = '1.2.3'\n"):
            with self.subTest(line=line):
                write(self.root, INIT, line)
                self.assertEqual([], audit(self.root))
                write(self.root, INIT, line.replace("1.2.3", "9.9.9"))
                self.assertEqual(
                    [f"{PYPROJECT} has version 1.2.3 but {INIT} has version 9.9.9", f"{PLUGIN} has version 1.2.3 but {INIT} has version 9.9.9"],
                    audit(self.root),
                )

    def test_a_byte_order_mark_is_ignored_in_every_manifest(self):
        bom = b"\xef\xbb\xbf"
        write(self.root, INIT, bom + b'__version__ = "1.2.3"\n')
        write(self.root, PYPROJECT, bom + b'[project]\nversion = "1.2.3"\n')
        write(self.root, PLUGIN, bom + b'{"version": "1.2.3"}')
        self.assertEqual([], audit(self.root))
        write(self.root, PLUGIN, bom + b'{"version": "9.9.9"}')
        self.assertEqual([f"{PLUGIN} has version 9.9.9 but {INIT} has version 1.2.3"], audit(self.root))

    def test_deeply_nested_json_is_a_problem_line_not_a_crash(self):
        write_manifests(self.root)
        write(self.root, PLUGIN, '{"version": "1.2.3", "deep": ' + "[" * 100000 + "]" * 100000 + "}")
        self.assertEqual([f"{PLUGIN} cannot be parsed as JSON"], audit(self.root))

    def test_duplicate_json_keys_are_a_problem_line(self):
        write_manifests(self.root)
        write(self.root, PLUGIN, '{"version": "1.2.3", "version": "9.9.9"}')
        self.assertEqual([f"{PLUGIN} cannot be parsed as JSON"], audit(self.root))
        write_manifests(self.root)
        write(self.root, MARKETPLACE, '{"version": "1.2.3", "version": "9.9.9"}')
        self.assertEqual([f"{MARKETPLACE} cannot be parsed as JSON"], audit(self.root))

    def test_an_oversized_manifest_is_a_problem_line(self):
        write_manifests(self.root)
        write(self.root, PLUGIN, b'{"version": "1.2.3", "pad": "' + b"x" * MAX_MANIFEST_BYTES + b'"}')
        self.assertEqual([f"{PLUGIN} is larger than {MAX_MANIFEST_BYTES} bytes"], audit(self.root))

    def test_an_unreadable_manifest_is_a_problem_line_not_a_crash(self):
        write_manifests(self.root)
        real_open = Path.open

        def denied(path, *args, **kwargs):
            if path.name == PYPROJECT:
                raise PermissionError(13, "permission denied")
            return real_open(path, *args, **kwargs)

        with mock.patch.object(Path, "open", denied):
            self.assertEqual([f"{PYPROJECT} cannot be read"], audit(self.root))

    def test_a_directory_where_a_manifest_belongs_is_a_problem_line_not_a_crash(self):
        write_manifests(self.root)
        (self.root / PLUGIN).unlink()
        (self.root / PLUGIN).mkdir()
        self.assertEqual([f"{PLUGIN} cannot be read"], audit(self.root))

    def test_marketplace_version_is_compared_when_it_is_stated(self):
        write_manifests(self.root)
        write(self.root, MARKETPLACE, json.dumps({"name": "x", "plugins": [{"name": "x"}]}))
        self.assertEqual([], audit(self.root))
        write(self.root, MARKETPLACE, json.dumps({"version": "9.9.9", "plugins": []}))
        self.assertEqual([f"{MARKETPLACE} has version 9.9.9 but {INIT} has version 1.2.3"], audit(self.root))
        write(self.root, MARKETPLACE, json.dumps({"plugins": [{"name": "x", "version": "9.9.9"}]}))
        self.assertEqual([f"{MARKETPLACE} plugins[0] has version 9.9.9 but {INIT} has version 1.2.3"], audit(self.root))
        write(self.root, MARKETPLACE, json.dumps({"plugins": [{"name": "x", "version": "1.2.3"}]}))
        self.assertEqual([], audit(self.root))

    def test_a_marketplace_that_cannot_be_parsed_or_is_not_an_object_is_a_problem(self):
        write_manifests(self.root)
        write(self.root, MARKETPLACE, "{")
        self.assertEqual([f"{MARKETPLACE} cannot be parsed as JSON"], audit(self.root))
        write(self.root, MARKETPLACE, "[]")
        self.assertEqual([f"{MARKETPLACE} is not a JSON object"], audit(self.root))

    def test_a_root_that_is_not_a_directory_is_invalid_input(self):
        with self.assertRaises(ValueError):
            audit(self.root / "absent")


class SchemeTests(unittest.TestCase):
    def test_versions_of_the_scheme_are_accepted(self):
        for version in ("0.0.1", "0.0.9", "0.0.10", "0.0.24", "0.0.99", "0.1.0", "0.10.10", "0.99.0", "0.99.99"):
            with self.subTest(version=version):
                self.assertTrue(in_scheme(version))

    def test_texts_outside_the_scheme_are_refused(self):
        for text in (
            "0.0.0", "0.01.1", "0.0.01", "0.0.100", "0.100.0", "1.0.0", "1.2.3", "v0.0.1", "0.0.1-rc1", "0.0.1+build",
            " 0.0.1", "0.0.1 ", "0.0.1\n", "0.0", "0.0.1.0", "0.0.", "0.-1.1", "0.0.+1", "00.0.1", "", "0.0.١", "０.0.1",
        ):
            with self.subTest(text=text):
                self.assertFalse(in_scheme(text))

    def test_next_version_at_every_boundary(self):
        cases = {
            "0.0.1": "0.0.2", "0.0.23": "0.0.24", "0.0.98": "0.0.99", "0.0.99": "0.1.0", "0.1.0": "0.1.1",
            "0.1.98": "0.1.99", "0.1.99": "0.2.0", "0.9.99": "0.10.0", "0.98.99": "0.99.0", "0.99.98": "0.99.99",
        }
        for version, expected in cases.items():
            with self.subTest(version=version):
                self.assertEqual(expected, next_version(version))

    def test_next_version_refuses_the_last_version_and_every_text_outside_the_scheme_with_one_fixed_message(self):
        messages = set()
        for version in ("0.99.99", "0.0.0", "1.0.0", "v0.0.1", "0.0.100", "SECRET-0.0.1"):
            with self.subTest(version=version):
                with self.assertRaises(ValueError) as raised:
                    next_version(version)
                messages.add(str(raised.exception))
        self.assertEqual(1, len(messages))
        self.assertNotIn("SECRET", messages.pop())


class SchemeAuditTests(TempCase):
    def test_each_manifest_that_states_a_version_outside_the_scheme_is_named(self):
        write_manifests(self.root, init="1.0.0", pyproject="1.0.0", plugin="1.0.0")
        self.assertEqual([], audit(self.root))
        self.assertEqual(
            [
                f"{INIT} has version 1.0.0, which is not in the 0.MINOR.PATCH scheme",
                f"{PYPROJECT} has version 1.0.0, which is not in the 0.MINOR.PATCH scheme",
                f"{PLUGIN} has version 1.0.0, which is not in the 0.MINOR.PATCH scheme",
            ],
            audit(self.root, scheme=True),
        )

    def test_scheme_adds_to_the_mismatch_lines_and_passes_when_every_version_is_in_the_scheme(self):
        write_manifests(self.root, init="0.0.2", pyproject="0.0.2", plugin="0.0.2")
        self.assertEqual([], audit(self.root, scheme=True))
        write_manifests(self.root, init="0.0.2", pyproject="0.0.2", plugin="1.0.0")
        self.assertEqual(
            [
                f"{PLUGIN} has version 1.0.0 but {INIT} has version 0.0.2",
                f"{PLUGIN} has version 1.0.0, which is not in the 0.MINOR.PATCH scheme",
            ],
            audit(self.root, scheme=True),
        )

    def test_a_root_without_manifests_passes_the_scheme(self):
        self.assertEqual([], audit(self.root, scheme=True))


class MainTests(TempCase):
    def run_main(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(list(arguments))
        return status, stdout.getvalue(), stderr.getvalue()

    def test_agreeing_manifests_exit_zero_with_no_output(self):
        write_manifests(self.root)
        self.assertEqual((0, "", ""), self.run_main("--root", str(self.root)))

    def test_differing_manifests_exit_one_and_print_each_problem_on_stderr(self):
        write_manifests(self.root, plugin="9.9.9")
        status, stdout, stderr = self.run_main("--root", str(self.root))
        self.assertEqual(1, status)
        self.assertEqual("", stdout)
        self.assertEqual(f"{PLUGIN} has version 9.9.9 but {INIT} has version 1.2.3\n", stderr)

    def test_default_root_is_the_current_directory(self):
        write_manifests(self.root, pyproject="9.9.9")
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            status, _, stderr = self.run_main()
        finally:
            os.chdir(cwd)
        self.assertEqual(1, status)
        self.assertIn(f"{PYPROJECT} has version 9.9.9", stderr)

    def test_a_root_that_is_not_a_directory_exits_two_with_a_fixed_message(self):
        status, stdout, stderr = self.run_main("--root", str(self.root / "absent"))
        self.assertEqual((2, ""), (status, stdout))
        self.assertEqual("inonu-harness: version root must be an existing directory\n", stderr)

    def test_scheme_flag_exits_one_for_a_version_outside_the_scheme(self):
        write_manifests(self.root, init="1.0.0", pyproject="1.0.0", plugin="1.0.0")
        status, stdout, stderr = self.run_main("--root", str(self.root), "--scheme")
        self.assertEqual((1, ""), (status, stdout))
        self.assertEqual(3, len(stderr.splitlines()))
        self.assertIn(f"{PLUGIN} has version 1.0.0, which is not in the 0.MINOR.PATCH scheme", stderr)

    def test_next_prints_only_the_next_version_on_stdout(self):
        for version, expected in (("0.0.24", "0.0.25\n"), ("0.0.99", "0.1.0\n")):
            with self.subTest(version=version):
                write_manifests(self.root, init=version, pyproject=version, plugin=version)
                self.assertEqual((0, expected, ""), self.run_main("--root", str(self.root), "--next"))

    def test_next_exits_one_with_the_problem_lines_when_the_manifests_disagree_or_leave_the_scheme(self):
        write_manifests(self.root, init="0.0.24", pyproject="0.0.24", plugin="9.9.9")
        status, stdout, stderr = self.run_main("--root", str(self.root), "--next")
        self.assertEqual((1, ""), (status, stdout))
        self.assertEqual(
            f"{PLUGIN} has version 9.9.9 but {INIT} has version 0.0.24\n"
            f"{PLUGIN} has version 9.9.9, which is not in the 0.MINOR.PATCH scheme\n",
            stderr,
        )

    def test_next_refuses_the_last_version_and_a_root_that_states_none(self):
        write_manifests(self.root, init="0.99.99", pyproject="0.99.99", plugin="0.99.99")
        status, stdout, stderr = self.run_main("--root", str(self.root), "--next")
        self.assertEqual((1, ""), (status, stdout))
        self.assertTrue(stderr.startswith("inonu-harness: no next version"), stderr)
        empty = self.root / "empty"
        empty.mkdir()
        status, stdout, stderr = self.run_main("--root", str(empty), "--next")
        self.assertEqual((1, ""), (status, stdout))
        self.assertIn("no manifest states a version", stderr)

    def test_next_on_a_root_that_is_not_a_directory_exits_two(self):
        self.assertEqual((2, ""), self.run_main("--root", str(self.root / "absent"), "--next")[:2])

    def test_nothing_is_written(self):
        write_manifests(self.root, plugin="9.9.9")
        before = snapshot(self.root)
        self.run_main("--root", str(self.root))
        self.run_main("--root", str(self.root), "--scheme")
        audit(self.root)
        self.assertEqual(before, snapshot(self.root))
        write_manifests(self.root, init="0.0.24", pyproject="0.0.24", plugin="0.0.24")
        before = snapshot(self.root)
        self.run_main("--root", str(self.root), "--next")
        self.assertEqual(before, snapshot(self.root))


class VersionCommandTests(TempCase):
    def test_version_subcommand_prints_the_next_version_and_checks_the_scheme(self):
        write_manifests(self.root, init="0.0.24", pyproject="0.0.24", plugin="0.0.24")
        self.assertEqual((0, "0.0.25\n", ""), run_cli("version", "--root", str(self.root), "--next"))
        self.assertEqual((0, "", ""), run_cli("version", "--root", str(self.root), "--scheme"))

    def test_version_subcommand_exit_codes_match_the_module(self):
        write_manifests(self.root, init="1.0.0", pyproject="1.0.0", plugin="1.0.0")
        self.assertEqual(0, run_cli("version", "--root", str(self.root))[0])
        status, output, error = run_cli("version", "--root", str(self.root), "--scheme")
        self.assertEqual((1, ""), (status, output))
        self.assertIn("not in the 0.MINOR.PATCH scheme", error)
        self.assertEqual(1, run_cli("version", "--root", str(self.root), "--next")[0])
        self.assertEqual((2, ""), run_cli("version", "--root", str(self.root / "absent"))[:2])

    def test_version_subcommand_defaults_to_the_current_directory(self):
        write_manifests(self.root, init="0.0.24", pyproject="0.0.24", plugin="0.0.24")
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            status, output, _ = run_cli("version", "--next")
        finally:
            os.chdir(cwd)
        self.assertEqual((0, "0.0.25\n"), (status, output))


class CheckStepTests(TempCase):
    def test_versions_step_runs_between_compile_and_tests(self):
        make_checkout(self.root)
        status, output, error = run_cli("check", "--root", str(self.root))
        self.assertEqual(0, status, error)
        self.assertEqual([("compile", 0), ("versions", 0), ("tests", 0)], steps_of(output))

    def test_mismatched_manifests_fail_the_check_and_name_both_files_on_stderr(self):
        make_checkout(self.root)
        write_manifests(self.root, init="0.0.1", pyproject="0.0.1", plugin="0.0.2")
        status, output, error = run_cli("check", "--root", str(self.root))
        self.assertEqual(1, status)
        self.assertEqual([("compile", 0), ("versions", 1), ("tests", 0)], steps_of(output))
        self.assertIn(f"{PLUGIN} has version 0.0.2 but {INIT} has version 0.0.1", error)

    def test_the_versions_step_requires_the_scheme(self):
        make_checkout(self.root, version="1.0.0")
        status, output, error = run_cli("check", "--root", str(self.root))
        self.assertEqual(1, status)
        self.assertEqual([("compile", 0), ("versions", 1), ("tests", 0)], steps_of(output))
        self.assertIn(f"{INIT} has version 1.0.0, which is not in the 0.MINOR.PATCH scheme", error)

    def test_a_root_without_manifests_still_passes(self):
        make_checkout(self.root, manifests=False)
        status, output, error = run_cli("check", "--root", str(self.root))
        self.assertEqual(0, status, error)
        self.assertEqual([("compile", 0), ("versions", 0), ("tests", 0)], steps_of(output))

    def test_ref_check_runs_the_versions_step_in_order(self):
        make_checkout(self.root)
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "checkout")
        status, output, error = run_cli("check", "--root", str(self.root), "--ref", "HEAD")
        self.assertEqual(0, status, error)
        self.assertEqual([("compile", 0), ("versions", 0), ("tests", 0), ("runner", 0)], steps_of(output))

    def test_ref_check_fails_a_committed_mismatch(self):
        make_checkout(self.root)
        write_manifests(self.root, init="0.0.1", pyproject="0.0.1", plugin="0.0.2")
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "mismatched versions")
        status, output, _ = run_cli("check", "--root", str(self.root), "--ref", "HEAD")
        self.assertEqual(1, status)
        self.assertNotEqual(0, dict(steps_of(output))["versions"])


class RepositoryTests(unittest.TestCase):
    def test_this_repository_states_one_version(self):
        self.assertEqual([], audit(REPO_ROOT))

    def test_this_repository_is_in_the_scheme(self):
        self.assertEqual([], audit(REPO_ROOT, scheme=True))


if __name__ == "__main__":
    unittest.main()
