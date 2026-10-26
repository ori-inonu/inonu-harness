"""Optional bridge from an existing SDD decision to the local Decision Graph."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
import re
from typing import Any, Literal

from .decision_graph import Decision, DecisionGraph
from .jev import JevAdapter, JevRecommendation, JevResult


GateStatus = Literal[
    "disabled",
    "invalid_request",
    "recommended",
    "no_consensus",
    "timeout",
    "unavailable",
    "refused",
    "invalid_response",
]


@dataclass(frozen=True, slots=True)
class SddGateResult:
    status: GateStatus
    jev_result: JevResult | None = None
    recommendation: JevRecommendation | None = None
    decision: Decision | None = None


ContextStatus = Literal["disabled", "invalid_request", "ready"]


@dataclass(frozen=True, slots=True)
class ContextAlternative:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class ContextEvidence:
    source: str
    reference: str
    criterion_id: str | None
    version: str | None


@dataclass(frozen=True, slots=True)
class ContextRecommendation:
    alternative_id: str
    source: str
    version: str


@dataclass(frozen=True, slots=True)
class SddDecisionContext:
    id: str
    revision: int
    question: str
    alternatives: tuple[ContextAlternative, ...]
    constraints: tuple[str, ...]
    required_criteria: tuple[str, ...]
    dependencies: tuple[str, ...]
    status: str
    evidence: tuple[ContextEvidence, ...]
    recommendation: ContextRecommendation | None
    authorized_alternative_id: str | None
    invalidated_by: tuple[str, ...]
    validated_criteria: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SddDecisionContextResult:
    status: ContextStatus
    decisions: tuple[SddDecisionContext, ...] = ()


class SddDecisionContextAdapter:
    """Read-only, explicit projection of selected local decisions for SDD."""

    def __init__(self, *, enabled: bool = False, graph: DecisionGraph | None = None):
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean")
        if enabled and graph is None:
            raise ValueError("enabled SDD context adapter requires a decision graph")
        self.enabled = enabled
        self._graph = graph

    def load_context(self, ids: Sequence[str]) -> SddDecisionContextResult:
        if not self.enabled:
            return SddDecisionContextResult("disabled")
        if not self._valid_ids(ids):
            return SddDecisionContextResult("invalid_request")

        assert self._graph is not None
        decisions = tuple(self._project(self._graph.get(decision_id)) for decision_id in ids)
        return SddDecisionContextResult("ready", decisions)

    @staticmethod
    def _valid_ids(ids: object) -> bool:
        if not isinstance(ids, Sequence) or isinstance(ids, (str, bytes)) or not ids:
            return False
        seen: set[str] = set()
        for decision_id in ids:
            if (
                not isinstance(decision_id, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", decision_id)
                or decision_id in seen
            ):
                return False
            seen.add(decision_id)
        return True

    @staticmethod
    def _project(decision: Decision) -> SddDecisionContext:
        recommendation = decision.recommendation
        return SddDecisionContext(
            id=decision.id,
            revision=decision.revision,
            question=decision.question,
            alternatives=tuple(ContextAlternative(option.id, option.label) for option in decision.alternatives),
            constraints=decision.constraints,
            required_criteria=decision.required_criteria,
            dependencies=decision.dependencies,
            status=decision.status,
            evidence=tuple(
                ContextEvidence(
                    source=reference.source,
                    reference=reference.reference,
                    criterion_id=reference.criterion_id,
                    version=reference.version,
                )
                for reference in decision.evidence
            ),
            recommendation=(
                ContextRecommendation(
                    alternative_id=recommendation.alternative_id,
                    source=recommendation.source,
                    version=recommendation.version,
                )
                if recommendation is not None
                else None
            ),
            authorized_alternative_id=decision.authorized_alternative_id,
            invalidated_by=decision.invalidated_by,
            validated_criteria=decision.validated_criteria,
        )


class SddDecisionGate:
    """An additive recommendation bridge; disabled instances do no work."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        graph: DecisionGraph | None = None,
        adapter: JevAdapter | None = None,
    ):
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean")
        if enabled and (graph is None or adapter is None):
            raise ValueError("enabled SDD gate requires a graph and JEV adapter")
        self.enabled = enabled
        self._graph = graph
        self._adapter = adapter

    def request_recommendation(
        self,
        decision_id: str,
        spec: Any,
        *,
        idempotency_key: str,
    ) -> SddGateResult:
        if not self.enabled:
            return SddGateResult("disabled")
        if (
            not isinstance(decision_id, str)
            or not decision_id.strip()
            or not isinstance(spec, Mapping)
            or spec.get("id") != decision_id
            or not isinstance(idempotency_key, str)
            or not idempotency_key.strip()
        ):
            return SddGateResult("invalid_request")
        assert self._adapter is not None and self._graph is not None
        try:
            result = self._adapter.recommend(spec)
        except ValueError:
            return SddGateResult("invalid_request")
        if result.status != "recommended" or result.recommendation is None:
            return SddGateResult(result.status, jev_result=result)
        recommendation = result.recommendation
        decision = self._graph.recommend(
            decision_id,
            alternative_id=recommendation.alternative_id,
            source=recommendation.source,
            version=recommendation.version,
            provenance=recommendation.provenance,
            idempotency_key=idempotency_key,
        )
        return SddGateResult(
            "recommended",
            jev_result=result,
            recommendation=recommendation,
            decision=decision,
        )
