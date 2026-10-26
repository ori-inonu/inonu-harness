"""Domain contracts and rules for a local, persistent decision graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Mapping, Protocol, Sequence
import hashlib
import json
import re


@dataclass(frozen=True, slots=True)
class Alternative:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    source: str
    reference: str
    provenance: str
    criterion_id: str | None = None
    version: str | None = None


@dataclass(frozen=True, slots=True)
class CriterionResult:
    passed: bool
    evidence: tuple[EvidenceReference, ...]


@dataclass(frozen=True, slots=True)
class Recommendation:
    alternative_id: str
    source: str
    version: str
    provenance: str


@dataclass(frozen=True, slots=True)
class Decision:
    id: str
    revision: int
    question: str
    alternatives: tuple[Alternative, ...]
    constraints: tuple[str, ...]
    required_criteria: tuple[str, ...]
    evidence: tuple[EvidenceReference, ...]
    dependencies: tuple[str, ...]
    status: str
    created_at: str
    updated_at: str
    block_reason: str | None = None
    recommendation: Recommendation | None = None
    authorized_alternative_id: str | None = None
    authorized_by: str | None = None
    invalidated_by: tuple[str, ...] = ()
    validated_criteria: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    decision_id: str
    revision: int
    event: str
    changed_fields: tuple[str, ...]
    at: str
    snapshot: Decision


class DecisionError(Exception):
    """Base class for expected decision graph errors."""


class DecisionValidationError(DecisionError, ValueError):
    pass


class DecisionNotFound(DecisionError, LookupError):
    pass


class DecisionAlreadyExists(DecisionError):
    pass


class IdempotencyConflict(DecisionError):
    pass


class DependencyCycle(DecisionError):
    pass


class AuthorizationRequired(DecisionError):
    pass


class ConcurrentModification(DecisionError):
    pass


class UnsupportedSchemaVersion(DecisionError):
    pass


class DecisionStore(Protocol):
    """Persistence boundary; business validation stays in DecisionGraph."""

    def get(self, decision_id: str) -> Decision | None: ...

    def list(self) -> tuple[Decision, ...]: ...

    def history(self, decision_id: str) -> tuple[HistoryEntry, ...]: ...

    def replay(self, idempotency_key: str, request_hash: str) -> Decision | None: ...

    def commit(
        self,
        *,
        idempotency_key: str,
        request_hash: str,
        expected_revisions: dict[str, int],
        updates: tuple[Decision, ...],
        events: tuple[HistoryEntry, ...],
        result_id: str,
    ) -> Decision: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionGraph:
    def __init__(self, store: DecisionStore):
        self._store = store

    def create_decision(
        self,
        *,
        decision_id: str,
        question: str,
        alternatives: Sequence[Alternative],
        constraints: Sequence[str],
        required_criteria: Sequence[str],
        evidence: Sequence[EvidenceReference] = (),
        dependencies: Sequence[str] = (),
        idempotency_key: str,
    ) -> Decision:
        self._ensure_idempotency_key(idempotency_key)
        request = {
            "decision_id": decision_id,
            "question": question,
            "alternatives": alternatives,
            "constraints": constraints,
            "required_criteria": required_criteria,
            "evidence": evidence,
            "dependencies": dependencies,
        }
        request_hash = self._request_hash("create", request)
        previous = self._store.replay(idempotency_key, request_hash)
        if previous is not None:
            return previous
        alternatives = self._as_tuple(alternatives, "alternatives")
        constraints = self._as_tuple(constraints, "constraints")
        required_criteria = self._as_tuple(required_criteria, "required_criteria")
        evidence = self._as_tuple(evidence, "evidence")
        dependencies = self._as_tuple(dependencies, "dependencies")
        created = _now()
        decision = Decision(
            id=decision_id,
            revision=1,
            question=question,
            alternatives=tuple(alternatives),
            constraints=tuple(constraints),
            required_criteria=tuple(required_criteria),
            evidence=tuple(evidence),
            dependencies=tuple(dependencies),
            status="pending",
            created_at=created,
            updated_at=created,
        )
        self._validate_decision(decision)
        self._validate_dependencies(decision)
        event = HistoryEntry(decision_id, 1, "created", tuple(), created, decision)
        return self._store.commit(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            expected_revisions={decision_id: 0},
            updates=(decision,),
            events=(event,),
            result_id=decision_id,
        )

    def get(self, decision_id: str) -> Decision:
        decision = self._store.get(decision_id)
        if decision is None:
            raise DecisionNotFound(decision_id)
        return decision

    def list_decisions(self, *, status: str | None = None) -> tuple[Decision, ...]:
        decisions = self._store.list()
        if status is None:
            return decisions
        if status not in {"pending", "blocked", "invalidated", "authorized"}:
            raise DecisionValidationError(f"unknown decision status: {status}")
        return tuple(decision for decision in decisions if decision.status == status)

    def history(self, decision_id: str) -> tuple[HistoryEntry, ...]:
        if self._store.get(decision_id) is None:
            raise DecisionNotFound(decision_id)
        return self._store.history(decision_id)

    def revise(
        self,
        decision_id: str,
        *,
        question: str | None = None,
        alternatives: Sequence[Alternative] | None = None,
        constraints: Sequence[str] | None = None,
        required_criteria: Sequence[str] | None = None,
        evidence: Sequence[EvidenceReference] | None = None,
        dependencies: Sequence[str] | None = None,
        relevant_premise_changed: bool = False,
        idempotency_key: str,
    ) -> Decision:
        self._ensure_idempotency_key(idempotency_key)
        request = {
            "decision_id": decision_id,
            "question": question,
            "alternatives": alternatives,
            "constraints": constraints,
            "required_criteria": required_criteria,
            "evidence": evidence,
            "dependencies": dependencies,
            "relevant_premise_changed": relevant_premise_changed,
        }
        request_hash = self._request_hash("revise", request)
        previous = self._store.replay(idempotency_key, request_hash)
        if previous is not None:
            return previous
        if not isinstance(relevant_premise_changed, bool):
            raise DecisionValidationError("relevant_premise_changed must be a boolean")
        alternatives = self._as_tuple(alternatives, "alternatives") if alternatives is not None else None
        constraints = self._as_tuple(constraints, "constraints") if constraints is not None else None
        required_criteria = self._as_tuple(required_criteria, "required_criteria") if required_criteria is not None else None
        evidence = self._as_tuple(evidence, "evidence") if evidence is not None else None
        dependencies = self._as_tuple(dependencies, "dependencies") if dependencies is not None else None
        old = self.get(decision_id)
        changed = {
            "question": question if question is not None else old.question,
            "alternatives": tuple(alternatives) if alternatives is not None else old.alternatives,
            "constraints": tuple(constraints) if constraints is not None else old.constraints,
            "required_criteria": tuple(required_criteria) if required_criteria is not None else old.required_criteria,
            "evidence": tuple(evidence) if evidence is not None else old.evidence,
            "dependencies": tuple(dependencies) if dependencies is not None else old.dependencies,
        }
        if all(changed[name] == getattr(old, name) for name in changed):
            raise DecisionValidationError("revision must change at least one decision field")

        revised = replace(
            old,
            revision=old.revision + 1,
            **changed,
            status="pending",
            updated_at=_now(),
            block_reason=None,
            recommendation=None,
            authorized_alternative_id=None,
            authorized_by=None,
            invalidated_by=(),
            validated_criteria=(),
        )
        self._validate_decision(revised)
        self._validate_dependencies(revised)
        updates = [revised]
        events = [
            HistoryEntry(
                decision_id,
                revised.revision,
                "revised",
                tuple(name for name in changed if changed[name] != getattr(old, name)),
                revised.updated_at,
                revised,
            )
        ]
        expected = {decision_id: old.revision}
        if relevant_premise_changed:
            for dependent in self._dependent_decisions(decision_id):
                invalidated = replace(
                    dependent,
                    revision=dependent.revision + 1,
                    status="invalidated",
                    updated_at=revised.updated_at,
                    block_reason=None,
                    recommendation=None,
                    authorized_alternative_id=None,
                    authorized_by=None,
                    validated_criteria=(),
                    invalidated_by=tuple(dict.fromkeys((*dependent.invalidated_by, decision_id))),
                )
                updates.append(invalidated)
                expected[dependent.id] = dependent.revision
                events.append(
                    HistoryEntry(
                        dependent.id,
                        invalidated.revision,
                        "invalidated",
                        ("status", "invalidated_by"),
                        invalidated.updated_at,
                        invalidated,
                    )
                )
        return self._store.commit(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            expected_revisions=expected,
            updates=tuple(updates),
            events=tuple(events),
            result_id=decision_id,
        )

    def recommend(
        self,
        decision_id: str,
        *,
        alternative_id: str,
        source: str,
        version: str,
        provenance: str,
        idempotency_key: str,
    ) -> Decision:
        self._ensure_idempotency_key(idempotency_key)
        request = {
            "decision_id": decision_id,
            "alternative_id": alternative_id,
            "source": source,
            "version": version,
            "provenance": provenance,
        }
        request_hash = self._request_hash("recommended", request)
        previous = self._store.replay(idempotency_key, request_hash)
        if previous is not None:
            return previous
        old = self.get(decision_id)
        if old.status != "pending":
            raise DecisionValidationError("only a pending decision can receive a recommendation")
        self._validate_alternative(old, alternative_id)
        if not all(isinstance(value, str) and value.strip() for value in (source, version, provenance)):
            raise DecisionValidationError("recommendation source, version, and provenance are required")
        at = _now()
        updated = replace(
            old,
            revision=old.revision + 1,
            updated_at=at,
            recommendation=Recommendation(alternative_id, source, version, provenance),
        )
        return self._commit_one(
            old,
            updated,
            event="recommended",
            changed_fields=("recommendation",),
            idempotency_key=idempotency_key,
            request=request,
            request_hash=request_hash,
        )

    def authorize(
        self,
        decision_id: str,
        *,
        alternative_id: str,
        actor: str,
        criteria: Mapping[str, CriterionResult],
        idempotency_key: str,
    ) -> Decision:
        self._ensure_idempotency_key(idempotency_key)
        request = {
            "decision_id": decision_id,
            "alternative_id": alternative_id,
            "actor": actor,
            "criteria": dict(criteria) if isinstance(criteria, Mapping) else criteria,
        }
        request_hash = self._request_hash("authorized", request)
        previous = self._store.replay(idempotency_key, request_hash)
        if previous is not None:
            return previous
        if not isinstance(criteria, Mapping):
            raise DecisionValidationError("criteria must map each criterion id to a result")
        old = self.get(decision_id)
        if old.status != "pending":
            raise AuthorizationRequired("only a pending decision can be authorized")
        self._validate_alternative(old, alternative_id)
        if not isinstance(actor, str) or not actor.strip():
            raise DecisionValidationError("authorization actor is required")
        if set(criteria) != set(old.required_criteria):
            raise DecisionValidationError("every required criterion must have exactly one result")
        attached_evidence: list[EvidenceReference] = []
        for criterion_id in old.required_criteria:
            result = criteria[criterion_id]
            if not isinstance(result, CriterionResult) or result.passed is not True:
                raise DecisionValidationError(f"criterion {criterion_id} has not passed")
            if not result.evidence:
                raise DecisionValidationError(f"criterion {criterion_id} requires evidence")
            for reference in result.evidence:
                if (
                    not isinstance(reference, EvidenceReference)
                    or reference.criterion_id != criterion_id
                    or not all(
                        isinstance(value, str) and value.strip()
                        for value in (reference.source, reference.reference, reference.provenance)
                    )
                ):
                    raise DecisionValidationError(f"criterion {criterion_id} has invalid evidence provenance")
                attached_evidence.append(reference)
        at = _now()
        updated = replace(
            old,
            revision=old.revision + 1,
            evidence=old.evidence + tuple(attached_evidence),
            status="authorized",
            updated_at=at,
            authorized_alternative_id=alternative_id,
            authorized_by=actor.strip(),
            validated_criteria=old.required_criteria,
        )
        return self._commit_one(
            old,
            updated,
            event="authorized",
            changed_fields=("status", "authorized_alternative_id", "authorized_by", "validated_criteria", "evidence"),
            idempotency_key=idempotency_key,
            request=request,
            request_hash=request_hash,
        )

    def block_decision(self, decision_id: str, *, reason: str, idempotency_key: str) -> Decision:
        self._ensure_idempotency_key(idempotency_key)
        request = {"decision_id": decision_id, "reason": reason}
        request_hash = self._request_hash("blocked", request)
        previous = self._store.replay(idempotency_key, request_hash)
        if previous is not None:
            return previous
        old = self.get(decision_id)
        if not isinstance(reason, str) or not reason.strip():
            raise DecisionValidationError("block reason is required")
        at = _now()
        updated = replace(
            old,
            revision=old.revision + 1,
            status="blocked",
            updated_at=at,
            block_reason=reason.strip(),
            recommendation=None,
            authorized_alternative_id=None,
            authorized_by=None,
            validated_criteria=(),
        )
        return self._commit_one(
            old,
            updated,
            event="blocked",
            changed_fields=("status", "block_reason"),
            idempotency_key=idempotency_key,
            request=request,
            request_hash=request_hash,
        )

    def require_authorized(self, decision_id: str, alternative_id: str | None = None) -> Decision:
        decision = self.get(decision_id)
        if (
            decision.status != "authorized"
            or decision.authorized_alternative_id is None
            or (alternative_id is not None and decision.authorized_alternative_id != alternative_id)
            or not set(decision.required_criteria).issubset(decision.validated_criteria)
            or any(
                not any(reference.criterion_id == criterion for reference in decision.evidence)
                for criterion in decision.required_criteria
            )
        ):
            raise AuthorizationRequired(decision_id)
        return decision

    @staticmethod
    def _validate_alternative(decision: Decision, alternative_id: str) -> None:
        if not any(item.id == alternative_id for item in decision.alternatives):
            raise DecisionValidationError(f"unknown alternative: {alternative_id}")

    def _commit_one(
        self,
        old: Decision,
        updated: Decision,
        *,
        event: str,
        changed_fields: tuple[str, ...],
        idempotency_key: str,
        request: object,
        request_hash: str,
    ) -> Decision:
        entry = HistoryEntry(updated.id, updated.revision, event, changed_fields, updated.updated_at, updated)
        return self._store.commit(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            expected_revisions={old.id: old.revision},
            updates=(updated,),
            events=(entry,),
            result_id=updated.id,
        )

    def affected_by(self, decision_id: str) -> tuple[Decision, ...]:
        self.get(decision_id)
        return tuple(sorted(self._dependent_decisions(decision_id), key=lambda item: item.id))

    def pending(self) -> tuple[Decision, ...]:
        return self.list_decisions(status="pending")

    def blocked(self) -> tuple[Decision, ...]:
        return self.list_decisions(status="blocked")

    def invalidated(self) -> tuple[Decision, ...]:
        return self.list_decisions(status="invalidated")

    def _validate_dependencies(self, decision: Decision) -> None:
        all_decisions = {item.id: item for item in self._store.list()}
        for dependency_id in decision.dependencies:
            if dependency_id != decision.id and dependency_id not in all_decisions:
                raise DecisionValidationError(f"unknown dependency: {dependency_id}")
            to_visit = [dependency_id]
            visited: set[str] = set()
            while to_visit:
                current = to_visit.pop()
                if current == decision.id:
                    raise DependencyCycle(f"dependency cycle includes {decision.id}")
                if current in visited:
                    continue
                visited.add(current)
                if current in all_decisions:
                    to_visit.extend(all_decisions[current].dependencies)

    def _dependent_decisions(self, decision_id: str) -> tuple[Decision, ...]:
        all_decisions = {item.id: item for item in self._store.list()}
        reverse: dict[str, list[str]] = {}
        for decision in all_decisions.values():
            for dependency in decision.dependencies:
                reverse.setdefault(dependency, []).append(decision.id)
        found: list[Decision] = []
        visited = {decision_id}
        queue = [decision_id]
        while queue:
            current = queue.pop(0)
            for dependent_id in sorted(reverse.get(current, ())):
                if dependent_id in visited:
                    continue
                visited.add(dependent_id)
                dependent = all_decisions[dependent_id]
                found.append(dependent)
                queue.append(dependent_id)
        return tuple(found)

    @staticmethod
    def _ensure_idempotency_key(key: str) -> None:
        if not isinstance(key, str) or not key.strip():
            raise DecisionValidationError("idempotency_key is required")

    @staticmethod
    def _as_tuple(values: Sequence, field: str) -> tuple:
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise DecisionValidationError(f"{field} must be a sequence")
        return tuple(values)

    @staticmethod
    def _request_hash(operation: str, payload: object) -> str:
        serialized = json.dumps(
            [operation, payload],
            sort_keys=True,
            separators=(",", ":"),
            default=lambda value: asdict(value),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_decision(decision: Decision) -> None:
        if not isinstance(decision.id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", decision.id):
            raise DecisionValidationError("decision id must be a stable identifier (1-128 safe characters)")
        if not isinstance(decision.question, str) or not decision.question.strip():
            raise DecisionValidationError("question is required")
        if not 2 <= len(decision.alternatives) <= 12:
            raise DecisionValidationError("a decision must have 2 to 12 alternatives")
        ids = []
        for alternative in decision.alternatives:
            if (
                not isinstance(alternative, Alternative)
                or not isinstance(alternative.id, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", alternative.id)
                or not isinstance(alternative.label, str)
                or not alternative.label.strip()
            ):
                raise DecisionValidationError("each alternative requires an id and label")
            ids.append(alternative.id)
        if len(ids) != len(set(ids)):
            raise DecisionValidationError("alternative ids must be unique")
        if not decision.required_criteria or any(
            not isinstance(criterion, str) or not criterion.strip()
            for criterion in decision.required_criteria
        ):
            raise DecisionValidationError("at least one required criterion is required")
        if len(set(decision.required_criteria)) != len(decision.required_criteria):
            raise DecisionValidationError("required criteria must be unique")
        if any(not isinstance(item, str) or not item.strip() for item in decision.constraints):
            raise DecisionValidationError("constraints must be non-empty text")
        if any(not isinstance(item, str) or not item.strip() for item in decision.dependencies):
            raise DecisionValidationError("dependencies must be non-empty decision ids")
        if decision.id in decision.dependencies or len(set(decision.dependencies)) != len(decision.dependencies):
            raise DecisionValidationError("dependencies must be unique and cannot include the decision itself")
        for evidence in decision.evidence:
            if not isinstance(evidence, EvidenceReference):
                raise DecisionValidationError("evidence entries must be EvidenceReference values")
            if not all(isinstance(value, str) and value.strip() for value in (evidence.source, evidence.reference, evidence.provenance)):
                raise DecisionValidationError("evidence requires source, reference, and provenance")
            if evidence.criterion_id is not None and evidence.criterion_id not in decision.required_criteria:
                raise DecisionValidationError("evidence references an unknown criterion")
            if evidence.version is not None and (
                not isinstance(evidence.version, str) or not evidence.version.strip()
            ):
                raise DecisionValidationError("evidence version must be non-empty text when supplied")
