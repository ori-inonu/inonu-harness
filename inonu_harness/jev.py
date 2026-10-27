"""Typed, opt-in boundary for the observed Jev consensus MCP tools."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import re
from collections.abc import Mapping
from typing import Any, Literal, Protocol


class McpToolTransport(Protocol):
    def call_tool(self, name: str, arguments: Mapping[str, Any], *, timeout: float) -> Any: ...


class TransportUnavailable(ConnectionError):
    """The configured MCP transport cannot reach its server."""


JevStatus = Literal[
    "recommended",
    "no_consensus",
    "timeout",
    "unavailable",
    "refused",
    "invalid_response",
]


@dataclass(frozen=True, slots=True)
class JevRecommendation:
    alternative_id: str
    spec_hash: str
    source: str
    version: str
    provenance: str


@dataclass(frozen=True, slots=True)
class JevResult:
    status: JevStatus
    recommendation: JevRecommendation | None = None
    source_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return only bounded result fields; raw Jev receipts are never retained."""
        return asdict(self)


_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_SENSITIVE = (
    re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b"),
    re.compile(r"\b0x[0-9a-fA-F]{40}\b"),
    re.compile(r"\b(api[_ -]?key|secret|password|private[_ -]?key|seed phrase|mnemonic)\b\s*[:=]", re.I),
    re.compile(r"\bTYPESAFE[A-Z_]*\s*=", re.I),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
)


def _length(value: str) -> int:
    """Length as the Jev server counts it: a JavaScript string length, in UTF-16 code units (an emoji counts 2)."""
    return len(value) + sum(1 for char in value if ord(char) > 0xFFFF)


def _text(value: Any, limit: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and _length(value) <= limit


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _safe_text(value: str) -> bool:
    return not any(pattern.search(value) for pattern in _SENSITIVE)


def _validate_spec(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("decision spec must be an object")
    if not all(key in raw for key in ("id", "goal", "facts", "rails", "options")):
        raise ValueError("decision spec is missing required fields")
    if not _text(raw["id"], 40) or not _ID.fullmatch(raw["id"]):
        raise ValueError("decision spec has an invalid id")
    if not _text(raw["goal"], 600):
        raise ValueError("decision spec has an invalid goal")
    facts = raw["facts"]
    if not isinstance(facts, Mapping):
        raise ValueError("decision spec facts must be an object")
    clean_facts: dict[str, str | int | float | bool | None] = {}
    for key, value in facts.items():
        if not isinstance(key, str) or not key:
            raise ValueError("decision spec has an invalid fact key")
        valid = (isinstance(value, str) and _length(value) <= 300) or value is None or isinstance(value, bool) or _finite_number(value)
        if not valid:
            raise ValueError("decision spec has an invalid fact value")
        clean_facts[key] = value
    rails = raw["rails"]
    if not isinstance(rails, (list, tuple)) or len(rails) > 12 or any(not _text(item, 300) for item in rails):
        raise ValueError("decision spec rails must contain at most 12 non-empty strings")
    options = raw["options"]
    if not isinstance(options, (list, tuple)) or not 2 <= len(options) <= 8:
        raise ValueError("decision spec must contain 2 to 8 options")
    clean_options: list[dict[str, str]] = []
    for option in options:
        if not isinstance(option, Mapping):
            raise ValueError("decision spec contains an invalid option")
        option_id = option.get("id")
        if (
            not _text(option_id, 40)
            or not _ID.fullmatch(option_id)
            or option_id in {"none", "none_fits"}
            or not _text(option.get("label"), 120)
            or not _text(option.get("what"), 400)
        ):
            raise ValueError("decision spec contains an invalid option")
        clean_options.append({"id": option_id, "label": option["label"], "what": option["what"]})
    option_ids = [option["id"] for option in clean_options]
    if len(set(option_ids)) != len(option_ids):
        raise ValueError("decision spec option ids must be unique")
    clean: dict[str, Any] = {
        "id": raw["id"],
        "goal": raw["goal"],
        "facts": clean_facts,
        "rails": list(rails),
        "options": clean_options,
    }
    forbidden = raw.get("forbidden")
    if forbidden is not None:
        if (
            not isinstance(forbidden, (list, tuple))
            or any(not isinstance(item, str) or item not in option_ids for item in forbidden)
            or len(set(forbidden)) != len(forbidden)
        ):
            raise ValueError("decision spec forbidden options must identify unique allowed options")
        clean["forbidden"] = list(forbidden)
    unknowns = raw.get("unknowns")
    if unknowns is not None:
        if not isinstance(unknowns, (list, tuple)):
            raise ValueError("decision spec unknowns must be a list")
        clean_unknowns = []
        for item in unknowns:
            if (
                not isinstance(item, Mapping)
                or not _text(item.get("id"), 40)
                or not _ID.fullmatch(item["id"])
                or not _text(item.get("ask"), 300)
            ):
                raise ValueError("decision spec contains an invalid unknown")
            clean_unknowns.append({"id": item["id"], "ask": item["ask"]})
        clean["unknowns"] = clean_unknowns
    strings = [clean["id"], clean["goal"], *clean["rails"]]
    strings.extend(clean_facts.keys())
    strings.extend(value for value in clean_facts.values() if isinstance(value, str))
    strings.extend(text for option in clean_options for text in option.values())
    strings.extend(
        text for item in clean.get("unknowns", ()) for text in (item["id"], item["ask"])
    )
    if any(not _safe_text(value) for value in strings):
        raise ValueError("decision spec contains a sensitive value")
    return clean


def _decode_response(response: Any) -> tuple[str, Mapping[str, Any] | None]:
    if not isinstance(response, Mapping):
        return "invalid_response", None
    if response.get("isError") is True:
        return "refused", None
    payload: Any = response.get("structuredContent")
    if payload is None:
        contents = response.get("content")
        if contents is None:
            payload = response
        elif isinstance(contents, list):
            texts = [item.get("text") for item in contents if isinstance(item, Mapping) and item.get("type") == "text"]
            if len(texts) != 1 or not isinstance(texts[0], str):
                return "invalid_response", None
            try:
                payload = json.loads(texts[0])
            except (TypeError, json.JSONDecodeError):
                return "invalid_response", None
        else:
            return "invalid_response", None
    if not isinstance(payload, Mapping):
        return "invalid_response", None
    if "refused" in payload or "error" in payload:
        return "refused", payload
    return "ok", payload


class JevAdapter:
    def __init__(
        self,
        transport: McpToolTransport,
        *,
        timeout_seconds: float = 20.0,
        server_name: str = "jev-sdd",
        server_version: str = "unknown",
    ):
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not _text(server_name, 120) or not _text(server_version, 120):
            raise ValueError("server identity must be non-empty")
        self._transport = transport
        self.timeout_seconds = float(timeout_seconds)
        self.server_name = server_name
        self.server_version = server_version

    def recommend(self, raw_spec: Mapping[str, Any]) -> JevResult:
        spec = _validate_spec(raw_spec)
        for tool in ("consensus_plan", "consensus_run"):
            try:
                response = self._transport.call_tool(tool, {"spec": spec}, timeout=self.timeout_seconds)
            except TimeoutError:
                return JevResult("timeout")
            except (ConnectionError, OSError):
                return JevResult("unavailable")
            except Exception:
                return JevResult("unavailable")
            state, payload = _decode_response(response)
            if state != "ok" or payload is None:
                return JevResult(state)  # type: ignore[arg-type]
            if tool == "consensus_plan":
                if (
                    payload.get("specId") != spec["id"]
                    or isinstance(payload.get("plannedCalls"), bool)
                    or not isinstance(payload.get("plannedCalls"), int)
                    or payload["plannedCalls"] < 0
                    or not _finite_number(payload.get("estimatedInputTokens"))
                    or payload["estimatedInputTokens"] < 0
                ):
                    return JevResult("invalid_response")
                if payload["plannedCalls"] == 0:
                    return JevResult("no_consensus", source_status="sem_opcoes")
                continue
            return self._parse_run(payload, spec)
        return JevResult("invalid_response")

    def _parse_run(self, payload: Mapping[str, Any], spec: Mapping[str, Any]) -> JevResult:
        receipt = payload.get("receipt", payload)
        if not isinstance(receipt, Mapping):
            return JevResult("invalid_response")
        spec_id = receipt.get("specId")
        spec_hash = receipt.get("specHash")
        status = receipt.get("status")
        leader = receipt.get("leader")
        implement = receipt.get("implement")
        if (
            spec_id != spec["id"]
            or not isinstance(spec_hash, str)
            or not re.fullmatch(r"[0-9a-fA-F]{64}", spec_hash)
            or not isinstance(status, str)
            or status not in {"consenso", "sem_consenso", "sem_opcoes", "juiz_falhou"}
            or not isinstance(implement, bool)
        ):
            return JevResult("invalid_response")
        if status != "consenso":
            return JevResult("no_consensus", source_status=status)
        allowed_ids = {item["id"] for item in spec["options"]} - set(spec.get("forbidden", ()))
        if not implement or not isinstance(leader, str) or leader not in allowed_ids:
            return JevResult("invalid_response", source_status=status)
        provenance = f"{self.server_name}.consensus_run; specHash={spec_hash}"
        return JevResult(
            "recommended",
            JevRecommendation(
                alternative_id=leader,
                spec_hash=spec_hash,
                source=self.server_name,
                version=self.server_version,
                provenance=provenance,
            ),
            source_status=status,
        )


class MockJevTransport:
    """Deterministic transport for local tests; it has no network behavior."""

    def __init__(
        self,
        responses: Mapping[str, Any] | None = None,
        *,
        errors: Mapping[str, BaseException] | None = None,
    ):
        self.responses = dict(responses or {})
        self.errors = dict(errors or {})
        self.calls: list[tuple[str, Mapping[str, Any], float]] = []

    def call_tool(self, name: str, arguments: Mapping[str, Any], *, timeout: float) -> Any:
        self.calls.append((name, arguments, timeout))
        if name in self.errors:
            raise self.errors[name]
        if name not in self.responses:
            raise TransportUnavailable(f"mock has no response for {name}")
        return self.responses[name]
