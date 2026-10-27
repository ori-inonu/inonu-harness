"""Structural rules for the package and its runner scripts: stdlib-only imports and one cli entry boundary."""

import ast
from contextlib import contextmanager
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "inonu_harness"
CLI_MODULE = f"{PACKAGE}.cli"
# cli.py and __main__.py are the package entry points; scripts/inonu.py is the documented runner that wraps cli.main.
CLI_IMPORTERS = frozenset({"inonu_harness/cli.py", "inonu_harness/__main__.py", "scripts/inonu.py"})


def _absolute_modules(node):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    return [node.module] if node.level == 0 else []


DYNAMIC_IMPORT_CALLS = frozenset({"__import__", "import_module", "exec", "eval"})


def _dynamic_import(node):
    """True for a call that imports by name or runs code from a string, which the static check cannot see."""
    if not isinstance(node, ast.Call):
        return False
    function = node.func
    name = function.id if isinstance(function, ast.Name) else function.attr if isinstance(function, ast.Attribute) else None
    return name in DYNAMIC_IMPORT_CALLS


def _reaches_cli(node, in_package):
    if isinstance(node, ast.Import):
        targets = [alias.name for alias in node.names]
    elif node.level == 0:
        targets = [node.module, *(f"{node.module}.{alias.name}" for alias in node.names)]
    elif in_package and node.level == 1:
        base = f"{PACKAGE}.{node.module}" if node.module else PACKAGE
        targets = [base, *(f"{base}.{alias.name}" for alias in node.names)]
    else:
        return False
    entry_points = (CLI_MODULE, f"{PACKAGE}.__main__")  # importing __main__ runs the CLI
    return any(target == entry or target.startswith(entry + ".") for target in targets for entry in entry_points)


def architecture_violations(root: Path) -> list[str]:
    """Return one message per structural violation in root's inonu_harness/ and scripts/ modules."""
    stdlib = set(sys.stdlib_module_names)
    problems: list[str] = []
    modules = [path for folder in (PACKAGE, "scripts") for path in sorted((root / folder).rglob("*.py"))]
    for path in modules:
        rel = path.relative_to(root).as_posix()
        in_package = rel.startswith(f"{PACKAGE}/")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if _dynamic_import(node):
                problems.append(
                    f"{rel}:{node.lineno} imports or executes code by name at run time, which this check cannot see; "
                    "use a static import statement."
                )
                continue
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for module in _absolute_modules(node):
                top = module.split(".")[0]
                if top not in stdlib and top != PACKAGE:
                    problems.append(
                        f"{rel}:{node.lineno} imports {module!r}, which is neither standard library nor {PACKAGE}; "
                        "remove the dependency or rewrite the code with the standard library."
                    )
            if rel not in CLI_IMPORTERS and _reaches_cli(node, in_package):
                problems.append(
                    f"{rel}:{node.lineno} imports {CLI_MODULE}; only {', '.join(sorted(CLI_IMPORTERS))} may. "
                    "Move the shared code into a lower module and have cli.py call it."
                )
    return problems


@contextmanager
def _copied_sources():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for folder in (PACKAGE, "scripts"):
            shutil.copytree(REPO_ROOT / folder, root / folder, ignore=shutil.ignore_patterns("__pycache__"))
        yield root


def _append(path: Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


class ArchitectureTests(unittest.TestCase):
    def test_repository_follows_structural_rules(self):
        problems = architecture_violations(REPO_ROOT)
        self.assertEqual([], problems, "structural violations:\n" + "\n".join(problems))

    def test_injected_third_party_import_is_reported_with_file(self):
        with _copied_sources() as copy:
            _append(copy / PACKAGE / "loop.py", "\nimport requests\n")
            problems = architecture_violations(copy)
        self.assertEqual(1, len(problems), problems)
        self.assertTrue(problems[0].startswith(f"{PACKAGE}/loop.py:"), problems[0])
        self.assertIn("'requests'", problems[0])

    def test_injected_third_party_from_import_in_scripts_is_reported(self):
        with _copied_sources() as copy:
            _append(copy / "scripts" / "inonu.py", "\nfrom yaml import safe_load\n")
            problems = architecture_violations(copy)
        self.assertTrue(any(problem.startswith("scripts/inonu.py:") and "'yaml'" in problem for problem in problems), problems)

    def test_cli_import_from_a_lower_module_is_reported_in_every_form(self):
        forms = ("from .cli import main\n", "from . import cli\n", "import inonu_harness.cli\n", "from inonu_harness import cli\n")
        for form in forms:
            with self.subTest(form=form), _copied_sources() as copy:
                _append(copy / PACKAGE / "docs_lint.py", "\n" + form)
                problems = architecture_violations(copy)
                self.assertTrue(
                    any(problem.startswith(f"{PACKAGE}/docs_lint.py:") and CLI_MODULE in problem for problem in problems),
                    problems,
                )

    def test_modules_in_subpackages_are_scanned(self):
        with _copied_sources() as copy:
            (copy / PACKAGE / "sub").mkdir()
            (copy / PACKAGE / "sub" / "x.py").write_text("import requests\nfrom inonu_harness.cli import main\n", encoding="utf-8")
            problems = architecture_violations(copy)
        self.assertTrue(any("sub/x.py:1" in problem and "'requests'" in problem for problem in problems), problems)
        self.assertTrue(any("sub/x.py:2" in problem and CLI_MODULE in problem for problem in problems), problems)

    def test_violations_inside_functions_and_try_blocks_are_found(self):
        snippets = (
            "\n\ndef late():\n    import requests\n",
            "\n\ntry:\n    import yaml\nexcept ImportError:\n    yaml = None\n",
            "\n\ndef late():\n    from .cli import main\n",
        )
        for snippet in snippets:
            with self.subTest(snippet=snippet), _copied_sources() as copy:
                _append(copy / PACKAGE / "loop.py", snippet)
                self.assertTrue(architecture_violations(copy), snippet)

    def test_dynamic_imports_and_code_execution_are_reported(self):
        snippets = ("\nimport importlib\nimportlib.import_module('requests')\n", "\n__import__('requests')\n", "\nexec('import requests')\n", "\neval('1')\n")
        for snippet in snippets:
            with self.subTest(snippet=snippet), _copied_sources() as copy:
                _append(copy / PACKAGE / "loop.py", snippet)
                problems = architecture_violations(copy)
                self.assertTrue(any("run time" in problem for problem in problems), problems)

    def test_importing_the_main_module_from_a_lower_module_is_reported(self):
        with _copied_sources() as copy:
            _append(copy / PACKAGE / "loop.py", "\nfrom inonu_harness import __main__\n")
            problems = architecture_violations(copy)
        self.assertTrue(any(problem.startswith(f"{PACKAGE}/loop.py:") for problem in problems), problems)

    def test_importing_the_main_module_does_not_run_the_cli(self):
        import importlib

        importlib.import_module("inonu_harness.__main__")  # would raise SystemExit if the CLI ran at import

    def test_entry_points_may_import_cli(self):
        with _copied_sources() as copy:
            _append(copy / PACKAGE / "__main__.py", "\nfrom .cli import main as _again\n")
            _append(copy / "scripts" / "inonu.py", "\nimport inonu_harness.cli\n")
            self.assertEqual([], architecture_violations(copy))


if __name__ == "__main__":
    unittest.main()
