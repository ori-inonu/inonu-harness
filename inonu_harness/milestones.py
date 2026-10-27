"""Create the next milestone folder, check the milestone folders and close one into MILESTONES.md: their structure, the coverage of their requirements and the checkpoint and index rules, read from Markdown. Files are read and written only below the root."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections.abc import Iterable, Iterator
from contextlib import suppress
import datetime
import json
import os
from pathlib import Path, PurePath
import re
import sys
import tempfile
import unicodedata
from typing import Any

from .versions import in_scheme, next_version, stated_versions

SCHEMA_VERSION = 1
DEFAULT_DIR = "docs/specs/milestones"
MAX_BYTES = 1 << 20
MAX_RANGE = 1000
MAX_REFERENCES = 10000  # per tasks.md: a larger file is reported and its coverage is not computed
MAX_FINDINGS_PER_RULE = 50
MAX_DIGITS = 9
TITLE_LIMIT = 120
INDEX_FILE = "MILESTONES.md"
CHECKPOINT_FILE = "checkpoint.md"

# A fence may sit in a list item or a block quote, as in docs_lint; a backtick fence cannot carry a backtick on its opening line.
_FENCE = re.compile(r"^[ \t>]*(`{3,}(?=[^`]*$)|~{3,})")
_FOLDER = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+")
_HEADING = re.compile(r"^(#{1,6})[ \t]")
# Top-level items only: an indented bullet such as v0.0.15's "  - R5 holds" is a test case under R6, not a requirement.
_REQUIREMENT = re.compile(r"^[-*][ \t]+(?:\*\*)?R([0-9]{1,9})(?![0-9A-Za-z_])")
# R<a>, or a range R<a> to R<b> joined by an en dash, a hyphen or two dots; the end may omit its R.
_REFERENCE = re.compile(r"(?<![0-9A-Za-z_])R([0-9]+)(?:(?:–|-|\.\.)(?:R)?([0-9]+))?(?![0-9A-Za-z_])")
_HTML_BLOCK = re.compile(r" {0,3}<!--")  # a line that starts with a comment opens a CommonMark HTML block
# A requirement list item is read in every section except these: R<n> items under them are deferred or excluded work.
_EXCLUDED_SECTIONS = ("out of scope", "out-of-scope", "non-goals", "not in scope", "deferred")
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
# A list item of a deferred section: up to three spaces, a bullet or a number, then a space or the end of the line. An item that is
# indented further counts too, so a nested line needs its own reason; that is the safer way to be wrong.
_DEFERRED_ITEM = re.compile(r" {0,3}(?:[-*+]|[0-9]{1,9}[.)])(?=[ \t]|$)")
# A reason follows an em dash or a colon, with some text after it.
_REASON = re.compile(r"[—:]\s*\S")
_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_ENTRY = re.compile(r"## v([0-9]+\.[0-9]+\.[0-9]+)(?: — (.+?))? \(Shipped: ([^()]*)\)")
_INDEX_ITEMS = (
    re.compile(r"- Requirements: ([0-9]+)"),
    re.compile(r"- Deferred: ([0-9]+)"),
    re.compile(r"- Folder: \[(v[0-9.]+)\]\((v[0-9.]+)/\)"),
)

SEVERITY = {
    "checkpoint_version_mismatch": "error",
    "decisions_missing": "warning",
    "file_unreadable": "error",
    "findings_truncated": "error",
    "index_date_invalid": "error",
    "index_date_order": "error",
    "index_duplicate": "error",
    "index_link_broken": "error",
    "index_malformed": "error",
    "index_order": "error",
    "link_escapes_root": "error",
    "milestone_name_invalid": "error",
    "milestone_not_in_scheme": "error",
    "reference_limit_exceeded": "error",
    "reference_range_invalid": "error",
    "requirement_duplicate": "error",
    "requirement_gap": "warning",
    "requirement_unclaimed": "error",
    "required_file_missing": "error",
    "requirements_not_found": "warning",
    "task_cites_unknown_requirement": "error",
    "tasks_not_found": "warning",
}

_SPEC = """# v{version} — {title}

## Requirements

- R1 <...>

## Out of scope

<...>
"""
_DECISIONS = """## D1 — Scope

<...>
"""
_TASKS = """| Task | Depends on | Ownership | Acceptance |
| --- | --- | --- | --- |
| T01 <...> | none | <...> | A1: R1 <...> |
"""


_INDEX_TEXT = "# Milestones\n\nMilestones closed with `milestone close`, newest first.\n"


class Refused(Exception):
    """A milestone that was not written (exit 1): a conflict, a version the scheme cannot give, a failed write, or a close
    with one reason per line."""


def new_milestone(root: Path, directory: str = DEFAULT_DIR, title: str | None = None) -> dict[str, Any]:
    """Create the next milestone folder with its three templates and return the report. ValueError for invalid input;
    Refused when the manifests or the folders forbid it, or when a file cannot be written (then nothing is kept)."""
    base, milestones = _locate(root, directory)
    if title is not None:
        _check_title(title)
    if milestones.exists() and not milestones.is_dir():
        raise ValueError("milestones directory is not a directory")
    problems, stated = stated_versions(base, scheme=True)
    if problems:
        raise Refused("; ".join(problems))
    try:
        if stated:
            version = next_version(stated[0][1])
        else:
            found = _scheme_folders(milestones)
            version = next_version(max(found, key=_order)) if found else "0.0.1"
    except ValueError as exc:
        raise Refused(str(exc)) from exc
    folder = milestones / f"v{version}"
    if os.path.lexists(folder):
        raise Refused(f"the milestone folder for {version} already exists")
    texts = _templates(version, title)
    created: list[Path] = []
    written: list[Path] = []
    try:
        _make_dirs(milestones, created)
        os.mkdir(folder)
        created.append(folder)
        for name, text in texts.items():
            with open(folder / name, "x", encoding="utf-8", newline="\n") as handle:  # "x" never overwrites
                written.append(folder / name)
                handle.write(text)
    except OSError as exc:
        for path in reversed(written):
            with suppress(OSError):
                path.unlink()
        for path in reversed(created):
            with suppress(OSError):  # a folder that still holds someone else's file stays
                path.rmdir()
        raise Refused(f"could not create the milestone folder for {version} (it may exist, or another run may have made it); nothing was kept") from exc
    return {
        "schema_version": SCHEMA_VERSION,
        "version": version,
        "directory": folder.relative_to(base).as_posix(),
        "files": list(texts),
    }


def check_milestones(root: Path, directory: str = DEFAULT_DIR, versions: Iterable[str] = (), start: str | None = None) -> dict[str, Any]:
    """The check report for the milestone folders below directory: all of them, the named versions, or those from start on,
    in version order. Folders whose name is not a version are always reported. ValueError for invalid input."""
    base, milestones = _locate(root, directory)
    named = set(versions)
    for version in [*named, *([] if start is None else [start])]:
        if not in_scheme(version):
            raise ValueError("a milestone version must be in the 0.MINOR.PATCH scheme")
    if not milestones.exists():
        return _report([])  # no milestones directory means no milestones to check
    if not milestones.is_dir():
        raise ValueError("milestones directory is not a directory")
    names = _folder_names(milestones)
    scheme = {name[1:]: name for name in names if _FOLDER.fullmatch(name) and in_scheme(name[1:])}
    if named - set(scheme):
        raise ValueError("a named milestone version has no folder in the milestones directory")
    entries: list[dict[str, Any]] = []
    for version in sorted(scheme, key=_order):
        if (named and version not in named) or (start is not None and _order(version) < _order(start)):
            continue
        entries.append({"version": version, "findings": _check_folder(base, milestones / scheme[version], version)})
    unknown: list[dict[str, Any]] = []
    for name in names:
        if name in scheme.values():
            continue
        if _FOLDER.fullmatch(name):
            finding = _finding("milestone_not_in_scheme", ".", None, "the version is not in the 0.MINOR.PATCH scheme")
            unknown.append({"version": name[1:], "findings": [finding]})
        else:
            finding = _finding("milestone_name_invalid", ".", None, "the folder name is not v<digits>.<digits>.<digits>")
            unknown.append({"version": name, "findings": [finding]})
    entries.extend(sorted(unknown, key=lambda entry: entry["version"]))
    index = _index_findings(base, milestones)
    if index is not None:
        entries.append({"version": "index", "findings": index})
    return _report(entries)


def close_milestone(
    root: Path, directory: str = DEFAULT_DIR, version: str | None = None, date: str | None = None, today: datetime.date | None = None,
) -> dict[str, Any]:
    """Write the index entry of a milestone whose folder, checkpoint, manifests and index allow it, and nothing else: nothing is
    moved, deleted or tagged. ValueError for invalid input; Refused, with one line per reason, when the close is not allowed.
    Without version the highest milestone folder is closed."""
    base, milestones = _locate(root, directory)
    closed_on = _closing_date(date)
    if closed_on > (today or datetime.date.today()):
        raise ValueError("the shipping date is later than today")
    if version is not None and not in_scheme(version):
        raise ValueError("a milestone version must be in the 0.MINOR.PATCH scheme")
    if milestones.exists() and not milestones.is_dir():
        raise ValueError("milestones directory is not a directory")
    folders = _scheme_folders(milestones)
    if version is None:
        if not folders:
            raise Refused("there is no milestone folder to close")
        version = max(folders, key=_order)
    elif version not in folders:
        if milestones.exists():
            raise ValueError(f"no milestone folder for {version}")
        raise Refused(f"the milestone folder for {version} does not exist")
    folder = milestones / folders[version]
    reasons = [_reason(finding) for finding in _check_folder(base, folder, version) if finding["severity"] == "error"]
    # The folder check already reports a checkpoint that cannot be read, so a failed read adds no second reason.
    unreadable: list[dict[str, Any]] = []
    checkpoint = _read(base, folder / CHECKPOINT_FILE, None, unreadable)
    deferred: list[tuple[int, bool]] = []
    if checkpoint is None:
        if not unreadable:
            reasons.append("checkpoint_missing: checkpoint.md is missing")
    else:
        reasons += _checkpoint_reasons(checkpoint)
        deferred = _deferred_items(checkpoint)
        reasons += [f"deferred_without_reason: checkpoint.md line {number} has no reason after an em dash or a colon" for number, reasoned in deferred if not reasoned]
    index_findings: list[dict[str, Any]] = []
    index_text = _read(base, milestones / INDEX_FILE, None, index_findings)
    entries = _index_entries(index_text, milestones, index_findings) if index_text is not None else []
    reasons += [_reason(finding) for finding in index_findings]
    problems, stated = stated_versions(base, scheme=True)
    reasons += problems
    if any(value != version for _, value in stated):
        reasons.append(f"manifests_not_bumped: the manifests do not all state {version}; bump them first")
    listed = [entry["version"] for entry in entries]
    if version in listed:
        reasons.append(f"version_closed: the index already has v{version}")
    elif listed and _order(max(listed, key=_order)) > _order(version):
        reasons.append(f"version_not_higher: v{version} is not higher than v{max(listed, key=_order)}")
    dated = [entry["date"] for entry in entries if entry["date"] is not None]
    if dated and closed_on < max(dated):
        reasons.append(f"index_date_order: {closed_on.isoformat()} is earlier than {max(dated).isoformat()}, a date in the index")
    if reasons:
        raise Refused("\n".join(reasons))
    spec = _read(base, folder / "spec.md", None, []) or ""
    title = _title(spec)
    if title is not None and (len(title) > TITLE_LIMIT or any(_is_control(char) for char in title)):
        title = None  # the index keeps to one clean line, as milestone new --title does
    heading = f"## v{version}" + (f" — {title}" if title else "") + f" (Shipped: {closed_on.isoformat()})"
    entry = [heading, f"- Requirements: {len(_requirements(spec, []))}", f"- Deferred: {len(deferred)}", f"- Folder: [v{version}](v{version}/)"]
    lines = _LINE_BREAK.split(index_text if index_text is not None else _INDEX_TEXT)
    if entries:
        at = entries[0]["line"] - 1
        lines[at:at] = [*entry, ""]
    else:
        while lines and not lines[-1]:
            lines.pop()
        lines += ["", *entry]
    index = milestones / INDEX_FILE
    try:
        _write_index(index, "\n".join(lines).rstrip("\n") + "\n")
    except OSError as exc:
        raise Refused("could not write the index; nothing was changed") from exc
    return {"schema_version": SCHEMA_VERSION, "version": version, "index": index.relative_to(base).as_posix(), "entry": "\n".join(entry)}


def add_commands(parser: argparse.ArgumentParser) -> None:
    """The new, check and close subcommands. cli.py mounts them under its milestone command; main parses them on a parser of its own."""
    commands = parser.add_subparsers(dest="operation", required=True)
    new = commands.add_parser("new", help="create the next milestone folder with spec.md, decisions.md and tasks.md")
    new.add_argument("--root", type=Path, default=Path("."), help="repository root (default: current directory)")
    new.add_argument("--dir", default=DEFAULT_DIR, help=f"milestones directory below the root (default: {DEFAULT_DIR})")
    new.add_argument("--title", help=f"one line of 1 to {TITLE_LIMIT} characters for the spec heading")
    check = commands.add_parser("check", help="check the milestone folders and print a JSON report")
    check.add_argument("versions", nargs="*", metavar="VERSION", help="check only these versions")
    check.add_argument("--from", dest="start", metavar="VERSION", help="check this version and every later one")
    check.add_argument("--root", type=Path, default=Path("."), help="repository root (default: current directory)")
    check.add_argument("--dir", default=DEFAULT_DIR, help=f"milestones directory below the root (default: {DEFAULT_DIR})")
    close = commands.add_parser("close", help="close a milestone: write its entry into MILESTONES.md when the checks pass")
    close.add_argument("version", nargs="?", metavar="VERSION", help="milestone to close (default: the highest folder)")
    close.add_argument("--date", metavar="YYYY-MM-DD", help="shipping date (default: today)")
    close.add_argument("--root", type=Path, default=Path("."), help="repository root (default: current directory)")
    close.add_argument("--dir", default=DEFAULT_DIR, help=f"milestones directory below the root (default: {DEFAULT_DIR})")


def run(args: argparse.Namespace) -> int:
    """Run a parsed new, close or check command: the JSON report on stdout, a problem line on stderr for each reason, and the exit code."""
    try:
        if args.operation == "new":
            report = new_milestone(args.root, args.dir, args.title)
        elif args.operation == "close":
            report = close_milestone(args.root, args.dir, args.version, args.date)
        else:
            report = check_milestones(args.root, args.dir, args.versions, args.start)
    except Refused as exc:
        for line in str(exc).split("\n"):  # close gives one line per reason
            print(f"inonu-harness: {line}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"inonu-harness: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("inonu-harness: local file operation failed; check the milestones directory and permissions", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))  # ASCII-escaped, like the other JSON reports
    return 1 if report.get("status") == "fail" else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m inonu_harness.milestones", description="Create the next milestone folder or check the milestone folders.")
    add_commands(parser)
    return run(parser.parse_args(argv))


def _locate(root: Path, directory: str) -> tuple[Path, Path]:
    """The resolved root and the resolved milestones directory. ValueError unless directory is a relative path below the root
    that resolves inside it, so that a link on the way out is refused as well."""
    try:
        if not root.is_dir():
            raise ValueError("milestones root must be an existing directory")
        base = root.resolve()
        relative = PurePath(directory)
        if relative.anchor or not relative.parts:
            raise ValueError("milestones directory must be a relative path below the root")
        milestones = (base / relative).resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError("milestones directory cannot be resolved") from exc
    if milestones == base or not milestones.is_relative_to(base):
        raise ValueError("milestones directory must resolve to a folder inside the root")
    return base, milestones


def _folder_names(milestones: Path) -> list[str]:
    with os.scandir(milestones) as entries:
        return sorted(entry.name for entry in entries if entry.is_dir())


def _scheme_folders(milestones: Path) -> dict[str, str]:
    """Version to folder name for each in-scheme milestone folder; empty when the directory does not exist."""
    if not milestones.is_dir():
        return {}
    return {name[1:]: name for name in _folder_names(milestones) if _FOLDER.fullmatch(name) and in_scheme(name[1:])}


def _order(version: str) -> tuple[int, ...]:
    """Sort key of an in-scheme version: the same order as the milestone numbers."""
    return tuple(int(part) for part in version.split("."))


def _check_title(title: str) -> None:
    if not 1 <= len(title) <= TITLE_LIMIT or any(_is_control(char) for char in title):
        raise ValueError(f"--title must be one line of 1 to {TITLE_LIMIT} characters with no control characters")


def _is_control(char: str) -> bool:
    return unicodedata.category(char)[0] == "C" or char in "\u2028\u2029"


def _templates(version: str, title: str | None) -> dict[str, str]:
    """The three files of a new milestone, in the order they are written; without a title the heading keeps a placeholder."""
    return {
        "spec.md": _SPEC.format(version=version, title="<title>" if title is None else title),
        "decisions.md": _DECISIONS,
        "tasks.md": _TASKS,
    }


def _make_dirs(path: Path, created: list[Path]) -> None:
    """Create path and each missing parent below the root, recording the folders this call made, parents first."""
    if path.is_dir():
        return
    _make_dirs(path.parent, created)
    os.mkdir(path)
    created.append(path)


def _report(entries: list[dict[str, Any]]) -> dict[str, Any]:
    failed = any(finding["severity"] == "error" for entry in entries for finding in entry["findings"])
    return {"schema_version": SCHEMA_VERSION, "status": "fail" if failed else "pass", "milestones": entries}


def _finding(rule: str, file: str, line: int | None, detail: str) -> dict[str, Any]:
    return {"rule": rule, "severity": SEVERITY[rule], "file": file, "line": line, "detail": detail}


def _sort_key(finding: dict[str, Any]) -> tuple[str, str, str, int, str]:
    return finding["severity"], finding["rule"], finding["file"], finding["line"] or 0, finding["detail"]


def _check_folder(base: Path, folder: Path, version: str) -> list[dict[str, Any]]:
    """The findings of one milestone folder, sorted by severity, rule, file and line."""
    try:
        inside = folder.resolve().is_relative_to(base)
    except (OSError, RuntimeError):
        inside = False  # a folder that cannot be resolved is refused like one that leaves the root
    if not inside:
        return [_finding("link_escapes_root", ".", None, "the milestone folder resolves outside the root or cannot be resolved, and was not read")]
    findings: list[dict[str, Any]] = []
    spec = _read(base, folder / "spec.md", "required_file_missing", findings)
    tasks = _read(base, folder / "tasks.md", "required_file_missing", findings)
    _read(base, folder / "decisions.md", "decisions_missing", findings)
    checkpoint = _read(base, folder / CHECKPOINT_FILE, None, findings)
    if checkpoint is not None:
        number, first = _first_line(checkpoint)
        if not _names(first, version):
            findings.append(_finding("checkpoint_version_mismatch", CHECKPOINT_FILE, number, f"checkpoint.md does not name v{version} in its first non-empty line"))
    defined = _requirements(spec, findings) if spec is not None else {}
    if tasks is not None:
        _coverage(tasks, defined, findings)
    return sorted(findings, key=_sort_key)


def _read(base: Path, path: Path, missing: str | None, findings: list[dict[str, Any]]) -> str | None:
    """The text of one milestone file, or None after a finding says why it was not read; a missing file gets the rule that
    missing names, and none when missing is None. Only a file inside the root is read."""
    name = path.name
    try:
        if not path.resolve().is_relative_to(base):
            findings.append(_finding("link_escapes_root", name, None, f"{name} resolves outside the root and was not read"))
            return None
        if path.exists() and not path.is_file():  # a FIFO or a device would block the read
            findings.append(_finding("file_unreadable", name, None, f"{name} is not a regular file"))
            return None
        with path.open("rb") as handle:
            data = handle.read(MAX_BYTES + 1)
    except FileNotFoundError:
        if missing is not None:
            findings.append(_finding(missing, name, None, f"{name} is missing"))
        return None
    except (OSError, RuntimeError):
        findings.append(_finding("file_unreadable", name, None, f"{name} cannot be read"))
        return None
    if len(data) > MAX_BYTES:
        findings.append(_finding("file_unreadable", name, None, f"{name} is larger than {MAX_BYTES} bytes"))
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        findings.append(_finding("file_unreadable", name, None, f"{name} is not UTF-8"))
        return None


def _prose(text: str) -> Iterator[tuple[int, str]]:
    """The (line number, line) pairs of text outside fenced code blocks and HTML comments."""
    fence: tuple[str, int] | None = None
    in_comment = False
    for number, line in enumerate(_LINE_BREAK.split(text), start=1):
        match = _FENCE.match(line)
        if fence is not None:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1] and not line[match.end():].strip():
                fence = None
            continue
        if in_comment:  # a comment runs to the line that holds its end, and nothing on that line is Markdown
            in_comment = "-->" not in line
            continue
        if match:
            fence = (match.group(1)[0], len(match.group(1)))
            continue
        block = _HTML_BLOCK.match(line)
        if block:
            in_comment = "-->" not in line[block.end():]
            continue
        line, in_comment = _strip_comments(line)
        yield number, line


def _mask_code_spans(line: str) -> str:
    """The line with each inline code span blanked out, same length, so that '<!--' written inside backticks is not a comment.
    A run of backticks closes at the next run of exactly its length, as in CommonMark; the scan is linear in the line."""
    if "`" not in line:
        return line
    runs = [(match.start(), match.end() - match.start()) for match in re.finditer("`+", line)]
    by_length: dict[int, list[int]] = {}
    for index, (_, length) in enumerate(runs):
        by_length.setdefault(length, []).append(index)
    masked = list(line)
    index = 0
    while index < len(runs):
        start, length = runs[index]
        later = by_length[length]
        position = bisect_right(later, index)
        if position < len(later):
            close = later[position]
            masked[start:runs[close][0] + length] = " " * (runs[close][0] + length - start)
            index = close + 1
        else:
            index += 1
    return "".join(masked)


def _strip_comments(line: str) -> tuple[str, bool]:
    """The line without its closed comments, and whether an open one follows. One pass, so a long run of '<!--' costs linear time;
    a '<!--' inside an inline code span is text."""
    masked = _mask_code_spans(line)
    parts: list[str] = []
    position = 0
    while True:
        start = masked.find("<!--", position)
        if start < 0:
            parts.append(line[position:])
            return "".join(parts), False
        parts.append(line[position:start])
        end = masked.find("-->", start + 4)
        if end < 0:
            return "".join(parts), True
        position = end + 3


def _requirements(text: str, findings: list[dict[str, Any]]) -> dict[int, int]:
    """The requirement ids that spec.md defines, each with its first line."""
    defined: dict[int, int] = {}
    inside = False
    for number, line in _prose(text):
        heading = _HEADING.match(line)
        if heading:
            title = line[heading.end() - 1:].strip().lower()
            # Requirements may continue under a later heading (v0.0.12 keeps R9 to R14 under "## Revision ..."); a section
            # for deferred work ends them.
            if title.startswith(("requirements", "revision")):
                inside = True
            elif title in _EXCLUDED_SECTIONS:
                inside = False
            continue
        item = _REQUIREMENT.match(line) if inside else None
        if item is None:
            continue
        identifier = int(item.group(1))
        if identifier in defined:
            findings.append(_finding("requirement_duplicate", "spec.md", number, f"R{identifier} is defined more than once"))
        else:
            defined[identifier] = number
    if not defined:
        findings.append(_finding("requirements_not_found", "spec.md", None, "no requirement list item under ## Requirements"))
    elif sorted(defined) != list(range(1, len(defined) + 1)):
        findings.append(_finding("requirement_gap", "spec.md", None, f"requirement ids do not run from R1 to R{max(defined)} without a gap"))
    return defined


def _coverage(text: str, defined: dict[int, int], findings: list[dict[str, Any]]) -> None:
    """Each defined requirement must be cited by a table row of tasks.md, and each citation must be defined. Nothing is
    compared when the spec defines no requirement. Ranges are kept as intervals, so a hostile file costs little."""
    rows = [(number, line) for number, line in _prose(text) if line.startswith("|")]
    if not rows:
        findings.append(_finding("tasks_not_found", "tasks.md", None, "tasks.md has no table row"))
        return
    if not defined:
        return
    spans: list[tuple[int, int, int]] = []  # (first id, last id, row line)
    references = 0
    for number, line in rows:
        for match in _REFERENCE.finditer(line):
            references += 1
            if references > MAX_REFERENCES:
                findings.append(_finding("reference_limit_exceeded", "tasks.md", number, f"more than {MAX_REFERENCES} requirement references; coverage was not computed"))
                return
            if len(match.group(1)) > MAX_DIGITS or (match.group(2) is not None and len(match.group(2)) > MAX_DIGITS):
                findings.append(_finding("reference_range_invalid", "tasks.md", number, f"a requirement id has more than {MAX_DIGITS} digits"))
                continue
            first = int(match.group(1))
            last = first if match.group(2) is None else int(match.group(2))
            if last < first or last - first >= MAX_RANGE:
                findings.append(_finding("reference_range_invalid", "tasks.md", number, f"R{first} to R{last} is not an ascending range of at most {MAX_RANGE} ids"))
                continue
            spans.append((first, last, number))
    merged: list[list[int]] = []
    for first, last, _ in sorted(spans):
        if merged and first <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], last)
        else:
            merged.append([first, last])
    starts = [interval[0] for interval in merged]

    def cited(identifier: int) -> bool:
        index = bisect_right(starts, identifier) - 1
        return index >= 0 and merged[index][1] >= identifier

    unclaimed = [identifier for identifier in sorted(defined) if not cited(identifier)]
    for identifier in unclaimed[:MAX_FINDINGS_PER_RULE]:
        findings.append(_finding("requirement_unclaimed", "spec.md", defined[identifier], f"R{identifier} is cited by no table row of tasks.md"))
    unknown: list[int] = []
    for first, last in merged:
        for identifier in range(first, last + 1):
            if identifier not in defined:
                unknown.append(identifier)
                if len(unknown) > MAX_FINDINGS_PER_RULE:
                    break
        if len(unknown) > MAX_FINDINGS_PER_RULE:
            break
    for identifier in unknown[:MAX_FINDINGS_PER_RULE]:
        row = min(number for first, last, number in spans if first <= identifier <= last)
        findings.append(_finding("task_cites_unknown_requirement", "tasks.md", row, f"R{identifier} is not defined in spec.md"))
    if len(unclaimed) > MAX_FINDINGS_PER_RULE or len(unknown) > MAX_FINDINGS_PER_RULE:
        findings.append(_finding("findings_truncated", ".", None, f"more than {MAX_FINDINGS_PER_RULE} findings of one rule; the rest were left out"))


def _reason(finding: dict[str, Any]) -> str:
    """One stderr line of a close refusal: the rule, the detail and the line when the finding has one."""
    line = f" (line {finding['line']})" if finding["line"] else ""
    return f"{finding['rule']}: {finding['detail']}{line}"


def _first_line(text: str) -> tuple[int | None, str]:
    """The number and text of the first non-empty visible line (outside comments and fences), or (None, "") when there is none."""
    for number, line in _prose(text):
        if line.strip():
            return number, line
    return None, ""


def _names(line: str, version: str) -> bool:
    """Whether line names v<version> as a whole token: v0.0.1 is not named by v0.0.10 or v0.0.1.5."""
    return re.search(rf"(?<![0-9A-Za-z])v{re.escape(version)}(?![0-9A-Za-z]|\.[0-9])", line) is not None


def _headings(text: str) -> list[tuple[int, str, int]]:
    """The (level, text, line) of each heading outside fenced blocks and HTML comments."""
    found = []
    for number, line in _prose(text):
        heading = _HEADING.match(line)
        if heading:
            found.append((len(heading.group(1)), line[heading.end():].strip(), number))
    return found


def _checkpoint_reasons(text: str) -> list[str]:
    """Why a checkpoint cannot close a milestone: no line starts with Status:, or a ## Verification or ## Limits heading is missing."""
    reasons = []
    if not any(line.startswith("Status:") for _, line in _prose(text)):
        reasons.append("checkpoint_status_missing: checkpoint.md has no line that starts with Status:")
    headings = {(level, title) for level, title, _ in _headings(text)}
    for title in ("Verification", "Limits"):
        if (2, title) not in headings:
            reasons.append(f"checkpoint_section_missing: checkpoint.md has no ## {title} heading")
    return reasons


def _deferred_items(text: str) -> list[tuple[int, bool]]:
    """The line and the reason flag of each list item under ## Deferred or ## Deferred items, in any letter case. A heading of
    another level does not open the section, and a deeper heading inside it keeps it open."""
    items: list[tuple[int, bool]] = []
    inside = False
    for number, line in _prose(text):
        heading = _HEADING.match(line)
        if heading:
            if len(heading.group(1)) <= 2:
                title = re.sub(r"[ \t]+#+[ \t]*$", "", line[heading.end():]).strip().lower()
                inside = len(heading.group(1)) == 2 and title in ("deferred", "deferred items")
            continue
        item = _DEFERRED_ITEM.match(line) if inside else None
        if item:
            items.append((number, _REASON.search(line[item.end():]) is not None))
    return items


def _title(spec: str) -> str | None:
    """The text after the em dash of the first heading of spec.md, or None when that heading has no dash or no text after it."""
    headings = _headings(spec)
    if not headings:
        return None
    _, dash, title = headings[0][1].partition("—")
    return (title.strip() or None) if dash else None


def _day(text: str) -> datetime.date | None:
    """The calendar date that text spells as YYYY-MM-DD, or None."""
    if not _DAY.fullmatch(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def _closing_date(value: str | None) -> datetime.date:
    """The date of --date, or today's date when it is not given. ValueError for a value that is not a real date."""
    if value is None:
        return datetime.date.today()
    day = _day(value)
    if day is None:
        raise ValueError("--date must be a real calendar date in the form YYYY-MM-DD")
    return day


def _index_entries(text: str, milestones: Path, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The entries of an index text in file order, each with its heading line, version and date (None when the date is not a
    real one). Each line that breaks the format and each rule that fails is appended to findings."""
    rows = [(number, line.strip()) for number, line in enumerate(_LINE_BREAK.split(text), start=1) if line.strip()]
    if rows and rows[0][1] == "# Milestones":
        rows = rows[1:]
    else:
        findings.append(_finding("index_malformed", INDEX_FILE, rows[0][0] if rows else 1, "the first line is not the heading # Milestones"))
    if rows and not rows[0][1].startswith(("#", "-")):
        rows = rows[1:]  # the one-line description
    else:
        findings.append(_finding("index_malformed", INDEX_FILE, rows[0][0] if rows else 1, "the one-line description is missing"))
    blocks: list[tuple[int, str, list[tuple[int, str]]]] = []
    for number, line in rows:
        if line.startswith("#"):
            blocks.append((number, line, []))
        elif blocks:
            blocks[-1][2].append((number, line))
        else:
            findings.append(_finding("index_malformed", INDEX_FILE, number, "a line before the first entry is not part of the format"))
    entries: list[dict[str, Any]] = []
    for number, line, items in blocks:
        heading = _ENTRY.fullmatch(line)
        if heading is None or not in_scheme(heading.group(1)):
            findings.append(_finding("index_malformed", INDEX_FILE, number, "a heading is not ## v<version> — <title> (Shipped: <date>) with a version of the scheme"))
            continue
        version = heading.group(1)
        if len(items) < len(_INDEX_ITEMS):
            findings.append(_finding("index_malformed", INDEX_FILE, number, f"v{version} has fewer list items than the format"))
        matches = []
        for offset, (item_number, item) in enumerate(items):
            found = _INDEX_ITEMS[offset].fullmatch(item) if offset < len(_INDEX_ITEMS) else None
            if found is None:
                findings.append(_finding("index_malformed", INDEX_FILE, item_number, f"a line under v{version} is not its next list item"))
            else:
                matches.append(found)
        if len(matches) == len(_INDEX_ITEMS):
            link = matches[2]
            if link.group(1) != f"v{version}" or link.group(2) != f"v{version}":
                findings.append(_finding("index_malformed", INDEX_FILE, items[2][0], f"the folder link does not name v{version}"))
            elif not (milestones / f"v{version}").is_dir():
                findings.append(_finding("index_link_broken", INDEX_FILE, items[2][0], f"the folder v{version} does not exist"))
        day = _day(heading.group(3))
        if day is None:
            findings.append(_finding("index_date_invalid", INDEX_FILE, number, f"the date of v{version} is not a real YYYY-MM-DD date"))
        entries.append({"line": number, "version": version, "date": day})
    seen: set[str] = set()
    above: dict[str, Any] | None = None
    for entry in entries:
        if entry["version"] in seen:
            findings.append(_finding("index_duplicate", INDEX_FILE, entry["line"], f"v{entry['version']} is listed more than once"))
        if above is not None and _order(entry["version"]) >= _order(above["version"]):
            findings.append(_finding("index_order", INDEX_FILE, entry["line"], f"v{entry['version']} is not below the entry above it"))
        seen.add(entry["version"])
        above = entry
    newest_below: datetime.date | None = None
    for entry in reversed(entries):
        if entry["date"] is None:
            continue
        if newest_below is not None and entry["date"] < newest_below:
            findings.append(_finding("index_date_order", INDEX_FILE, entry["line"], f"v{entry['version']} is dated earlier than an entry below it"))
        newest_below = entry["date"] if newest_below is None else max(newest_below, entry["date"])
    return entries


def _index_findings(base: Path, milestones: Path) -> list[dict[str, Any]] | None:
    """The sorted findings of the index, or None when there is no index to report."""
    findings: list[dict[str, Any]] = []
    text = _read(base, milestones / INDEX_FILE, None, findings)
    if text is not None:
        _index_entries(text, milestones, findings)
    elif not findings:
        return None
    return sorted(findings, key=_sort_key)


def _write_index(path: Path, text: str) -> None:
    """Put text in place of the index through a temporary file in the same folder, so that a failure leaves the old index
    untouched and no temporary file behind."""
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(temporary)
        raise


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
