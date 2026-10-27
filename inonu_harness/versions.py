"""Check that the manifests state one package version, and with --scheme that it is a milestone version. The audit reads files and parses source text; it does not import the package, though running it with -m imports the package first."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Callable
import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Any

INIT = "inonu_harness/__init__.py"
PYPROJECT = "pyproject.toml"
PLUGIN = ".claude-plugin/plugin.json"
MARKETPLACE = ".claude-plugin/marketplace.json"
MAX_BYTES = 1 << 20

# A problem line echoes a version, so only plain version characters are echoed; anything else is reported without its text.
# Versions are compared as exact strings, so 0.0.24.0 and v0.0.24 do not match 0.0.24.
_USABLE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,39}")
# Milestone n is 0.(n // 100).(n % 100); the last version of the scheme is 0.99.99, and 1.0.0 is the owner's decision.
_SCHEME = re.compile(r"0\.(0|[1-9][0-9]?)\.(0|[1-9][0-9]?)")
_LAST_MILESTONE = 9999
_NEXT_PROBLEM = "no next version: the version is not in the 0.MINOR.PATCH scheme, or it is 0.99.99, the last one"


class _Broken(Exception):
    """A manifest that exists but yields no version statements; its message is the whole problem line."""


def _read(root: Path, rel: str) -> str | None:
    """The manifest's text, None when it does not exist. Reads directly: Path.exists() differs between Python versions on errors."""
    path = root.joinpath(*rel.split("/"))
    try:
        if not path.resolve().is_relative_to(root.resolve()):  # a link must not take the audit outside the checked root
            raise _Broken(f"{rel} resolves outside the root")
    except (OSError, RuntimeError) as exc:
        raise _Broken(f"{rel} cannot be read") from exc
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_BYTES + 1)
    except (FileNotFoundError, NotADirectoryError):
        return None  # an absent manifest is skipped
    except OSError as exc:
        raise _Broken(f"{rel} cannot be read") from exc
    if len(data) > MAX_BYTES:
        raise _Broken(f"{rel} is larger than {MAX_BYTES} bytes")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _Broken(f"{rel} is not valid UTF-8") from exc


def _parse(rel: str, text: str, fmt: str, loads: Callable[[str], Any]) -> Any:
    try:
        return loads(text)
    except (ValueError, RecursionError) as exc:  # json and tomllib raise ValueError subclasses
        raise _Broken(f"{rel} cannot be parsed as {fmt}") from exc


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate JSON object key")  # the last value would silently win
    return dict(pairs)


def _json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_unique)


def _field(data: Any, key: str) -> Any:
    return data.get(key) if isinstance(data, dict) else None


def _is_version_name(target: ast.expr) -> bool:
    return isinstance(target, ast.Name) and target.id == "__version__"


def _init_statements(root: Path) -> list[tuple[str, Any]]:
    """The value of the top-level assignment to __version__. Any other way of binding the name makes the value unusable:
    the audit reads source text, and a rebinding in a block, a tuple, a loop, an import or a function would make it wrong."""
    text = _read(root, INIT)
    if text is None:
        return []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        raise _Broken(f"{INIT} cannot be parsed as Python") from exc
    value: Any = None
    direct: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [target for target in node.targets if _is_version_name(target)]
            assigned: ast.expr | None = node.value
        elif isinstance(node, ast.AnnAssign) and _is_version_name(node.target) and node.value is not None:
            targets, assigned = [node.target], node.value
        else:
            continue
        if targets:
            direct.extend(targets)
            value = assigned.value if isinstance(assigned, ast.Constant) and isinstance(assigned.value, str) else 0
    for node in ast.walk(tree):
        rebound = (
            (isinstance(node, ast.Name) and node.id == "__version__" and isinstance(node.ctx, (ast.Store, ast.Del)) and node not in direct)
            or (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == "__version__")
            or (isinstance(node, (ast.Import, ast.ImportFrom)) and any((alias.asname or alias.name.split(".")[0]) == "__version__" for alias in node.names))
            or (isinstance(node, (ast.Global, ast.Nonlocal)) and "__version__" in node.names)
        )
        if rebound:
            value = 0  # not a plain string the audit can compare
            break
    return [(INIT, value)]


def _pyproject_statements(root: Path) -> list[tuple[str, Any]]:
    text = _read(root, PYPROJECT)
    if text is None:
        return []
    return [(PYPROJECT, _field(_field(_parse(PYPROJECT, text, "TOML", tomllib.loads), "project"), "version"))]


def _plugin_statements(root: Path) -> list[tuple[str, Any]]:
    text = _read(root, PLUGIN)
    if text is None:
        return []
    return [(PLUGIN, _field(_parse(PLUGIN, text, "JSON", _json), "version"))]


def _marketplace_statements(root: Path) -> list[tuple[str, Any]]:
    text = _read(root, MARKETPLACE)
    if text is None:
        return []
    data = _parse(MARKETPLACE, text, "JSON", _json)
    if not isinstance(data, dict):
        raise _Broken(f"{MARKETPLACE} is not a JSON object")
    found = [(MARKETPLACE, data["version"])] if "version" in data else []
    plugins = data.get("plugins")
    for index, entry in enumerate(plugins if isinstance(plugins, list) else []):
        if isinstance(entry, dict) and "version" in entry:
            found.append((f"{MARKETPLACE} plugins[{index}]", entry["version"]))
    return found


_SOURCES = (_init_statements, _pyproject_statements, _plugin_statements, _marketplace_statements)


def _milestone(version: str) -> int:
    """The milestone number a version names; 0 for any text outside the scheme, so 0.0.0 too."""
    match = _SCHEME.fullmatch(version) if isinstance(version, str) else None
    return int(match[1]) * 100 + int(match[2]) if match else 0


def in_scheme(version: str) -> bool:
    """Whether text is a version of the 0.MINOR.PATCH scheme."""
    return _milestone(version) > 0


def next_version(version: str) -> str:
    """The version of the next milestone; ValueError for text outside the scheme and for 0.99.99, the last one."""
    number = _milestone(version)
    if number == 0 or number == _LAST_MILESTONE:
        raise ValueError(_NEXT_PROBLEM)
    return f"0.{(number + 1) // 100}.{(number + 1) % 100}"


def _check(root: Path, scheme: bool) -> tuple[list[str], list[tuple[str, str]]]:
    """The problem lines under root, and the usable (label, version) statements in source order."""
    if not root.is_dir():
        raise ValueError("version root must be an existing directory")
    problems: list[str] = []
    stated: list[tuple[str, str]] = []
    for source in _SOURCES:
        try:
            statements = source(root)
        except _Broken as exc:
            problems.append(str(exc))
            continue
        for label, value in statements:
            if value is None:
                problems.append(f"{label} has no version")
            elif isinstance(value, str) and _USABLE.fullmatch(value):
                stated.append((label, value))
            else:
                problems.append(f"{label} has no usable version")
    if stated:
        first_label, first = stated[0]
        problems.extend(
            f"{label} has version {version} but {first_label} has version {first}"
            for label, version in stated[1:] if version != first
        )
    if scheme:
        problems.extend(
            f"{label} has version {version}, which is not in the 0.MINOR.PATCH scheme"
            for label, version in stated if not in_scheme(version)
        )
    return problems, stated


def audit(root: Path, scheme: bool = False) -> list[str]:
    """Return one problem line per inconsistency under root; an empty list when every stated version agrees.
    With scheme, each stated version must also be a version of the 0.MINOR.PATCH scheme."""
    return _check(root, scheme)[0]


def stated_versions(root: Path, scheme: bool = False) -> tuple[list[str], list[tuple[str, str]]]:
    """The problem lines and the usable (label, version) statements under root, in source order; audit returns only the problems."""
    return _check(root, scheme)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m inonu_harness.versions", description="Check that the stated package versions agree.")
    parser.add_argument("--root", type=Path, default=Path("."), help="checkout whose manifests are compared (default: current directory)")
    parser.add_argument("--scheme", action="store_true", help="also require every stated version to be in the 0.MINOR.PATCH scheme")
    parser.add_argument("--next", action="store_true", help="print the next milestone's version computed from the stated version")
    args = parser.parse_args(argv)
    try:
        problems, stated = _check(args.root, scheme=args.scheme or args.next)
    except ValueError as exc:
        print(f"inonu-harness: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    if not args.next:
        return 0
    if not stated:
        print("inonu-harness: no manifest states a version to advance from", file=sys.stderr)
        return 1
    try:
        print(next_version(stated[0][1]))
    except ValueError as exc:
        print(f"inonu-harness: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
