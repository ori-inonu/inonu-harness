"""Opt-in scan of JSON-like values for a short list of credential formats.

A match is not proof that text is free of secrets, and no match does not prove it either. Findings carry rule
names and paths only; matched text is never returned.
"""

from __future__ import annotations

import re
from typing import Any

MAX_DEPTH = 200  # JSON from the CLI is shallow; deeper or cyclic input is refused instead of walked

_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]{0,39}")
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key_block", re.compile(r"-----BEGIN (?:[A-Z0-9]{1,16} )?PRIVATE KEY-----")),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,}")),
    ("slack_token", re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google_api_key", re.compile(r"AIza[A-Za-z0-9_-]{35}")),
    ("stripe_live_key", re.compile(r"(?:sk|rk)_live_[A-Za-z0-9]{16,}")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai_style_key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{32,}")),
    # the lookbehind starts a match only at a token boundary, so a run of "eyJ" cannot make the scan quadratic
    ("jwt", re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{7,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("bearer_token", re.compile(r"\bBearer [A-Za-z0-9._~+/=-]{20,}")),
    # shortcut: the name after the keyword is capped at 40 characters, raise the cap if real names are longer
    (
        "credential_assignment",
        re.compile(
            r"(?:api[_-]?key|secret|token|password|passwd|private[_-]?key)[A-Za-z0-9_-]{0,40}"
            r"[\"']?[ \t]*[:=][ \t]*[\"']?[A-Za-z0-9_\-/+=.]{16,}",
            re.IGNORECASE,
        ),
    ),
)


_CREDENTIAL = dict(_RULES)["credential_assignment"]
_WINDOW = 8  # a path never shows a key that shares this many consecutive characters with a matched text


def _matching_rules(text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in _RULES if pattern.search(text))


def _shares_window(key: str, text: str) -> bool:
    return len(key) >= _WINDOW and any(key[i:i + _WINDOW] in text for i in range(len(key) - _WINDOW + 1))


def _render(segments: tuple[str, ...], matched: str) -> str:
    """A finding path from list indices and dict keys; a key that overlaps the matched text is shown as `*`."""
    path = ""
    for segment in segments:
        if segment.startswith("["):
            path += segment
            continue
        name = "*" if segment != "*" and _shares_window(segment, matched) else segment
        path = f"{path}.{name}" if path else name
    return path


def scan(value: Any) -> list[dict[str, str]]:
    """Findings as {"rule", "path"} dicts, sorted by path then rule and without duplicates.

    Walks dicts and lists iteratively and scans dict keys as well as string values; a string value under a key is also
    checked as `key: value`, so {"password": ...} is found like the text "password: ...". Other types are ignored.
    Raises ValueError for input nested deeper than MAX_DEPTH, which includes a list that contains itself.
    """
    found: set[tuple[str, str]] = set()
    stack: list[tuple[tuple[str, ...], Any, int]] = [((), value, 0)]
    while stack:
        segments, node, depth = stack.pop()
        if isinstance(node, str):
            found.update((_render(segments, node), rule) for rule in _matching_rules(node))
        elif isinstance(node, (dict, list)):
            if depth >= MAX_DEPTH:
                raise ValueError("value is nested too deeply to scan")
            if isinstance(node, dict):
                for key, child in node.items():
                    segment = "*"
                    if isinstance(key, str):
                        rules = _matching_rules(key)
                        if rules:  # a key holding credential text is masked, so the text cannot reach a path
                            found.update((_render((*segments, "*"), key), rule) for rule in rules)
                        elif _IDENTIFIER.fullmatch(key):
                            segment = key
                        if isinstance(child, str) and _CREDENTIAL.search(f"{key}: {child}"):
                            found.add((_render((*segments, segment), child), "credential_assignment"))
                    stack.append(((*segments, segment), child, depth + 1))
            else:
                stack.extend(((*segments, f"[{index}]"), child, depth + 1) for index, child in enumerate(node))
    return [{"rule": rule, "path": path} for path, rule in sorted(found)]
