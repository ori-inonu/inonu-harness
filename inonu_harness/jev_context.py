"""Jev decision specs whose facts are the text of the documents that give the judge its context."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from .hook import _unique_json_object
from .jev import _length, _safe_text, _validate_spec

MAX_FACTS = 80  # the default fact budget for the documents; over it the command refuses, it never truncates
MAX_FILE_BYTES = 64 * 1024
FACT_LIMIT = 300  # the per-fact limit that jev._validate_spec enforces; a test fails if the two drift
_SENTENCE_FROM = 60  # a sentence end earlier than this is not worth a cut
_GENERATED_KEY = re.compile(r"doc[0-9]+_")
_DECISION_KEYS = frozenset(("id", "goal", "facts", "rails", "options", "forbidden", "unknowns"))
# Common token formats on top of the judge's own patterns: a document is plain text from the project, so a key pasted into
# it must not travel to the judge. The list is short on purpose; it cannot recognize every secret.
_TOKENS = tuple(re.compile(pattern) for pattern in (
    r"\bgh[pousr]_[A-Za-z0-9]{30,}",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    r"\bAIza[0-9A-Za-z_-]{35}",
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}",
))


def load_decision(path: Path) -> dict[str, Any]:
    """The decision object in a UTF-8 JSON file of at most MAX_FILE_BYTES; fixed ValueError messages otherwise."""
    with path.open("rb") as handle:
        data = handle.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"decision file is larger than {MAX_FILE_BYTES} bytes")
    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=_unique_json_object)
    except (ValueError, RecursionError) as exc:  # UnicodeDecodeError is a ValueError too
        raise ValueError("decision file must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("decision file must hold a JSON object")
    return value


def build_spec(
    decision: Mapping[str, Any], documents: Sequence[str], root: Path, max_facts: int = MAX_FACTS
) -> dict[str, Any]:
    """The validated Jev spec: the decision plus, for each document in order, a source fact and its text as facts.

    Raises ValueError with a fixed message that never includes document or decision text.
    """
    if not isinstance(decision, Mapping):
        raise ValueError("decision spec must be an object")
    if set(decision) - _DECISION_KEYS:
        raise ValueError("decision has an unknown top-level key")  # a misspelled 'forbidden' would otherwise vanish
    if not documents:
        raise ValueError("at least one --doc is required")
    if not root.is_dir():
        raise ValueError("--root must be an existing directory")
    own = decision.get("facts", {})
    if not isinstance(own, Mapping):
        raise ValueError("decision spec facts must be an object")
    if any(isinstance(key, str) and _GENERATED_KEY.match(key) for key in own):
        raise ValueError("decision facts must not use doc<N>_ keys; the documents own them")
    base = root.resolve()
    seen: list[Path] = []
    documents_facts: list[list[str]] = []
    for index, name in enumerate(documents, 1):
        path = _document_path(base, name, index)
        if any(os.path.samefile(path, earlier) for earlier in seen):  # also catches a hard link to a given file
            raise ValueError(f"document {index} is given twice")
        seen.append(path)
        documents_facts.append(_document_facts(path, base, index))
    needed = sum(len(facts) for facts in documents_facts)
    if needed > max_facts:
        raise ValueError(f"documents need {needed} facts, more than the limit of {max_facts}")
    generated: dict[str, str] = {}
    for index, facts in enumerate(documents_facts, 1):
        generated[f"doc{index}_source"] = facts[0]
        for number, fact in enumerate(facts[1:], 1):
            generated[f"doc{index}_{number:03d}"] = fact
    return _validate_spec({**decision, "facts": {**own, **generated}})


def _document_path(base: Path, name: str, index: int) -> Path:
    candidate = base / name
    if ":" in Path(name).name:  # an NTFS alternate data stream is not a regular file's visible text
        raise ValueError(f"document {index} is not a regular file inside --root")
    if candidate.is_symlink():
        raise ValueError(f"document {index} is a symbolic link")
    if not candidate.is_file():
        raise ValueError(f"document {index} is not a regular file inside --root")
    path = candidate.resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"document {index} resolves outside --root")
    return path


def _document_facts(path: Path, base: Path, index: int) -> list[str]:
    """The source fact, then the text chunks, of one document; ValueError when it is not usable text."""
    with path.open("rb") as handle:
        data = handle.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"document {index} is larger than {MAX_FILE_BYTES} bytes")
    if b"\x00" in data:
        raise ValueError(f"document {index} contains a NUL character")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"document {index} is not valid UTF-8") from exc
    lines = [line for line in (" ".join(raw.split()) for raw in text.splitlines()) if line]
    if not lines:
        raise ValueError(f"document {index} contains no text")
    whole = "\n".join(lines)  # scanned whole, so a secret that a fact boundary would split is still seen
    if not _safe_text(whole) or any(pattern.search(whole) for pattern in _TOKENS):
        raise ValueError(f"document {index} contains a sensitive value")
    digest = hashlib.sha256(data).hexdigest()[:16]
    return [f"{path.relative_to(base).as_posix()} sha256:{digest}", *_chunks(lines)]


def _chunks(lines: Sequence[str]) -> list[str]:
    """Facts for collapsed non-blank lines: lines packed, nothing reordered or lost."""
    facts: list[str] = []
    for line in lines:
        pieces = _pieces(line)
        if facts and _length(facts[-1]) + 1 + _length(pieces[0]) <= FACT_LIMIT:
            facts[-1] = f"{facts[-1]}\n{pieces[0]}"
        else:
            facts.append(pieces[0])
        facts.extend(pieces[1:])  # the rest of a split line continues in its own fact
    return facts


def _window(line: str) -> int:
    """How many leading characters of `line` fit in FACT_LIMIT, counted as the judge counts (UTF-16 code units)."""
    units = 0
    for index, char in enumerate(line):
        units += 2 if ord(char) > 0xFFFF else 1
        if units > FACT_LIMIT:
            return index
    return len(line)


def _pieces(line: str) -> list[str]:
    """Cut a collapsed line into pieces that fit: after a sentence end at or past _SENTENCE_FROM, else at a space, else at the limit."""
    pieces: list[str] = []
    while _length(line) > FACT_LIMIT:
        window = _window(line)
        dot = line.rfind(". ", 0, window)
        cut = dot + 1 if dot >= _SENTENCE_FROM else line.rfind(" ", 0, window)
        if cut <= 0:
            cut = window
            while cut > 1 and unicodedata.combining(line[cut]):  # keep a letter with its combining mark
                cut -= 1
        pieces.append(line[:cut].rstrip())
        line = line[cut:].lstrip()
    pieces.append(line)
    return pieces
