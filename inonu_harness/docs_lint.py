"""Deterministic checks for instruction-file and SKILL.md size and imports and for Markdown link targets. Reads files only."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote

SCHEMA_VERSION = 1
DEFAULT_MAX_BYTES = 32768  # the documented Codex project-doc default
DEFAULT_MAX_LINES = 200  # a configurable starting point, not a documented limit
INSTRUCTION_FILES = ("AGENTS.md", "AGENTS.override.md", "CLAUDE.md")
SKILL_FILE = "SKILL.md"
SKILL_MAX_BYTES = 20000  # superpowers fails a skill of this size or more
SKILL_MAX_LINES = 500  # the Claude Code skills documentation advises fewer lines than this

# A fence may sit inside a list item or a block quote, so indentation and `>` prefixes are allowed. A backtick fence
# cannot carry another backtick on its opening line (that line is inline code, not a fence).
_FENCE = re.compile(r"^[ \t>]*(`{3,}(?=[^`]*$)|~{3,})")
_CODE_SPAN = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)")
_INLINE_OPEN = re.compile(r"!?\[[^\[\]]*\]\(")
_REFERENCE_OPEN = re.compile(r"^ {0,3}\[(?!\^)[^\]]+\]:[ \t]*")  # a [^note]: footnote is not a link target
_IMPORT = re.compile(r"^@(\S+)$")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")  # also matches a Windows drive letter
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_MAX_TARGET = 1024  # no real path is longer; the cap keeps a pathological line from being rescanned quadratically


def lint(root: Path, max_bytes: int = DEFAULT_MAX_BYTES, max_lines: int = DEFAULT_MAX_LINES) -> dict[str, Any]:
    """Return the R2 report for root. Raises ValueError for a bad root or limit; never writes."""
    if not root.is_dir():
        raise ValueError("docs lint root must be an existing directory")
    if max_bytes < 1 or max_lines < 1:
        raise ValueError("docs lint limits must be positive integers")
    base = root.resolve()
    findings: list[dict[str, Any]] = []
    files, skills = _candidate_files(base, findings)
    tree = _Tree(base)
    for path in files:
        _lint_file(path, tree, max_bytes, max_lines, findings, path in skills)
    findings.sort(key=lambda item: (item["file"], item["line"] or 0, item["rule"], item["detail"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "fail" if findings else "pass",
        "files_checked": len(files),
        "findings": findings,
    }


def _candidate_files(base: Path, findings: list[dict[str, Any]]) -> tuple[list[Path], set[Path]]:
    """The files to lint, and which of them are skills (a SKILL.md below skills/; one under docs/ is only a document)."""
    paths = [base / name for name in (*INSTRUCTION_FILES, "README.md")]
    paths.extend(_walk(base, base / "docs", findings, lambda name: name.lower().endswith(".md")))
    skills = _walk(base, base / "skills", findings, lambda name: name.lower() == SKILL_FILE.lower())
    paths.extend(skills)
    return [path for path in paths if path.is_file()], set(skills)


def _walk(base: Path, folder: Path, findings: list[dict[str, Any]], wanted: Callable[[str], bool]) -> list[Path]:
    """Files under folder whose names pass wanted, listed under the folder's own path. A link that leaves the root is
    reported and not followed; a link to a folder inside the root but outside this one is followed; a link to a folder
    below this one is skipped, because that folder is read at its real place. A directory that cannot be listed is
    reported, so an unreadable folder never passes as an empty one.
    """
    if not folder.is_dir():
        return []
    top = folder.resolve()
    visited = {top}
    found: list[Path] = []

    def shown(path: Path) -> str:
        try:
            return path.relative_to(base).as_posix()
        except ValueError:  # a folder that is itself a link out of the root: name the folder
            return folder.relative_to(base).as_posix()

    def unreadable(error: OSError) -> None:
        rel = shown(Path(error.filename) if error.filename else folder)
        findings.append(_finding(
            "directory_unreadable", rel, None, "directory could not be listed and was not read",
            f"Allow the listing of {rel}, or remove it.",
        ))

    for directory, subdirectories, names in os.walk(folder, followlinks=True, onerror=unreadable):
        here = Path(directory).resolve()
        subdirectories.sort()
        kept = []
        for name in subdirectories:
            full = Path(directory, name)
            real = full.resolve()
            if real == here / name:  # an ordinary subdirectory, also when the folder it sits in is reached through a link
                kept.append(name)
            elif not real.is_relative_to(base):
                rel = full.relative_to(base).as_posix()
                findings.append(_finding(
                    "link_escapes_root", rel, None, "directory link resolves outside the root and was not read",
                    f"Replace {rel} with a real directory inside the root, or remove it.",
                ))
            elif not real.is_relative_to(top) and real not in visited:
                visited.add(real)
                kept.append(name)
        subdirectories[:] = kept
        found.extend(Path(directory, name) for name in sorted(names) if wanted(name))
    return found


class _Tree:
    """Case-exact existence checks with cached directory listings, so results do not depend on the host OS."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self._listings: dict[Path, frozenset[str]] = {}
        self._located: dict[str, tuple[bool, bool]] = {}  # keyed by text: Path equality ignores case on Windows

    def _names(self, directory: Path) -> frozenset[str]:
        if directory not in self._listings:
            try:
                self._listings[directory] = frozenset(os.listdir(directory))
            except OSError:
                self._listings[directory] = frozenset()
        return self._listings[directory]

    def locate(self, text: str, source_dir: Path) -> tuple[bool, bool]:
        """Return (inside the root, exists) for a relative reference; names that cannot be resolved count as missing."""
        try:
            candidate = Path(os.path.normpath(source_dir / text))
            key = str(candidate)
            if key in self._located:
                return self._located[key]
            result = self._locate(candidate)
        except (OSError, RuntimeError, ValueError):
            return True, False
        self._located[key] = result
        return result

    def _locate(self, candidate: Path) -> tuple[bool, bool]:
        if not candidate.is_relative_to(self.base):
            return False, candidate.exists()
        current = self.base
        for part in candidate.relative_to(self.base).parts:
            if not current.is_dir() or part not in self._names(current):
                return True, False
            current = current / part
        return current.resolve().is_relative_to(self.base), True


def _lint_file(path: Path, tree: _Tree, max_bytes: int, max_lines: int, findings: list[dict[str, Any]], skill: bool = False) -> None:
    base = tree.base
    rel = path.relative_to(base).as_posix()
    if not path.resolve().is_relative_to(base):  # a symlink out of the root is reported, never read
        findings.append(_finding(
            "link_escapes_root", rel, None, "file resolves outside the root and was not read",
            f"Replace {rel} with a regular file inside the root, or remove it.",
        ))
        return
    instruction = path.parent == base and path.name in INSTRUCTION_FILES
    size = path.stat().st_size
    if instruction and size > max_bytes:
        findings.append(_finding(
            "instruction_file_too_large", rel, None, f"{size} bytes is more than the {max_bytes}-byte limit",
            f"Shorten {rel} to at most {max_bytes} bytes by moving detail into a linked file under docs/.",
        ))
    if skill and size >= SKILL_MAX_BYTES:
        findings.append(_finding(
            "skill_file_too_large", rel, None, f"{size} bytes is at least the {SKILL_MAX_BYTES}-byte skill limit",
            f"Shorten {rel} below {SKILL_MAX_BYTES} bytes by moving detail into a file it links to.",
        ))
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        findings.append(_finding("file_unreadable", rel, None, "file is not valid UTF-8", f"Re-save {rel} as UTF-8 text."))
        return
    except OSError:
        findings.append(_finding("file_unreadable", rel, None, "file could not be read", f"Allow reading {rel}, or remove it."))
        return
    lines = _lines(text)
    if instruction and len(lines) > max_lines:
        findings.append(_finding(
            "instruction_file_too_long", rel, None, f"{len(lines)} lines is more than the {max_lines}-line limit",
            f"Move detailed sections of {rel} into docs/ and keep it to at most {max_lines} lines.",
        ))
    if skill and len(lines) >= SKILL_MAX_LINES:
        findings.append(_finding(
            "skill_file_too_long", rel, None, f"{len(lines)} lines is at least the {SKILL_MAX_LINES}-line skill limit",
            f"Move detailed sections of {rel} into a linked file and keep it under {SKILL_MAX_LINES} lines.",
        ))
    fence: tuple[str, int] | None = None
    for number, line in enumerate(lines, start=1):
        if fence is not None:
            if _closes(line, fence):
                fence = None
            continue
        opening = _FENCE.match(line)
        if opening:
            fence = (opening.group(1)[0], len(opening.group(1)))
            continue
        if instruction:
            imported = _IMPORT.match(line.strip())
            if imported:
                _append(findings, _import_finding(imported.group(1), path.parent, tree, rel, number))
                continue
        for raw in _link_targets(_CODE_SPAN.sub(" ", line)):
            _append(findings, _link_finding(raw, path.parent, tree, rel, number))


def _lines(text: str) -> list[str]:
    if text.startswith("﻿"):  # a byte-order mark must not hide an @import on line 1
        text = text[1:]
    lines = _LINE_BREAK.split(text)
    if lines[-1] == "":
        lines.pop()
    return lines


def _closes(line: str, fence: tuple[str, int]) -> bool:
    match = _FENCE.match(line)
    return (
        bool(match) and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1]
        and not line[match.end():].strip()
    )


def _destination(text: str, start: int) -> str | None:
    """Read a link destination: `<...>` (spaces allowed) or a run up to whitespace with balanced parentheses."""
    index = start
    while index < len(text) and text[index] in " \t":
        index += 1
    if index < len(text) and text[index] == "<":
        end = text.find(">", index + 1)
        return text[index + 1:end] if end > index else None
    depth = 0
    end = index
    while end < len(text) and end - index < _MAX_TARGET and text[end] not in " \t":
        if text[end] == "(":
            depth += 1
        elif text[end] == ")":
            if depth == 0:
                break
            depth -= 1
        end += 1
    return None if end - index >= _MAX_TARGET else (text[index:end] or None)


def _link_targets(line: str) -> list[str]:
    found = [_destination(line, match.end()) for match in _INLINE_OPEN.finditer(line)]
    reference = _REFERENCE_OPEN.match(line)
    if reference:
        found.append(_destination(line, reference.end()))
    return [target for target in found if target]


def _link_finding(raw: str, source_dir: Path, tree: _Tree, rel: str, number: int) -> dict[str, Any] | None:
    if raw.startswith(("/", "\\")) or _SCHEME.match(raw):  # absolute and scheme targets are not checked
        return None
    target = re.split(r"[#?]", raw, maxsplit=1)[0]
    if not target:  # a bare #fragment or ?query names the linking file itself
        return None
    text = unquote(target)
    if "\\" in text:  # a backslash path only resolves on Windows, and Markdown links need forward slashes
        return _finding(
            "link_broken", rel, number, f"link target '{raw}' uses a backslash",
            f"Change the link in {rel} to use forward slashes.",
        )
    inside, exists = tree.locate(text, source_dir)
    if not inside:
        return _finding(
            "link_escapes_root", rel, number, f"link target '{raw}' resolves outside the root",
            f"Point the link in {rel} at a file inside the root, or remove it.",
        )
    if not exists:
        return _finding(
            "link_broken", rel, number, f"link target '{raw}' does not exist",
            f"Change the link in {rel} to an existing file, or remove it.",
        )
    return None


def _import_finding(raw: str, source_dir: Path, tree: _Tree, rel: str, number: int) -> dict[str, Any] | None:
    if raw.startswith(("~", "/", "\\")) or _SCHEME.match(raw):  # user-global and absolute imports are not checked
        return None
    inside, exists = tree.locate(raw, source_dir)
    if not inside:
        return _finding(
            "import_missing", rel, number, f"@import target '{raw}' resolves outside the root",
            f"Change the @import in {rel} to a file inside the root, or delete the line.",
        )
    if not exists:
        return _finding(
            "import_missing", rel, number, f"@import target '{raw}' does not exist relative to the file",
            f"Fix the @import in {rel} to an existing file, or delete the line.",
        )
    return None


def _finding(rule: str, file: str, line: int | None, detail: str, remediation: str) -> dict[str, Any]:
    return {"rule": rule, "file": file, "line": line, "detail": detail, "remediation": remediation}


def _append(findings: list[dict[str, Any]], finding: dict[str, Any] | None) -> None:
    if finding is not None:
        findings.append(finding)
