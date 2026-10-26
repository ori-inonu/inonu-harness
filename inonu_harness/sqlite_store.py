"""SQLite implementation of the decision graph storage boundary."""

from __future__ import annotations

from dataclasses import asdict
import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

from .decision_graph import (
    Alternative,
    ConcurrentModification,
    Decision,
    DecisionAlreadyExists,
    DecisionError,
    EvidenceReference,
    HistoryEntry,
    IdempotencyConflict,
    Recommendation,
    UnsupportedSchemaVersion,
)


def _decision_data(decision: Decision) -> dict:
    return asdict(decision)


_STATUSES = ("pending", "blocked", "invalidated", "authorized")
_UNREADABLE = "decision store contains an unreadable record"


def _load(text: str) -> Any:
    """Decode one stored JSON value; text that is not JSON, or is nested too deeply, is an unreadable record."""
    try:
        return json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise DecisionError(_UNREADABLE) from exc


def _strings(value: Any, *, nonempty: bool = False) -> tuple[str, ...]:
    """A stored list of strings. A bare string or an object must not pass as an empty or exploded list."""
    if not isinstance(value, list) or not all(isinstance(item, str) and (item or not nonempty) for item in value):
        raise ValueError("expected a list of strings")
    return tuple(value)


def _objects(value: Any) -> list[dict]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("expected a list of objects")
    return value


def _decision_from_data(data: dict, expected_id: str | None = None) -> Decision:
    try:
        return _build_decision(data, expected_id)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise DecisionError(_UNREADABLE) from exc


def _build_decision(data: dict, expected_id: str | None) -> Decision:
    if not isinstance(data, dict) or data["status"] not in _STATUSES:
        raise ValueError("unknown record shape or status")
    if not isinstance(data["id"], str) or not data["id"] or (expected_id is not None and data["id"] != expected_id):
        raise ValueError("record id does not match its row")
    if type(data["revision"]) is not int or not isinstance(data["question"], str):
        raise ValueError("bad revision or question")
    return Decision(
        id=data["id"],
        revision=data["revision"],
        question=data["question"],
        alternatives=tuple(Alternative(**item) for item in _objects(data["alternatives"])),
        constraints=_strings(data["constraints"]),
        required_criteria=_strings(data["required_criteria"]),
        evidence=tuple(EvidenceReference(**item) for item in _objects(data["evidence"])),
        dependencies=_strings(data["dependencies"], nonempty=True),
        status=data["status"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        block_reason=data["block_reason"],
        recommendation=Recommendation(**data["recommendation"]) if data["recommendation"] else None,
        authorized_alternative_id=data["authorized_alternative_id"],
        authorized_by=data["authorized_by"],
        invalidated_by=_strings(data["invalidated_by"], nonempty=True),
        validated_criteria=_strings(data.get("validated_criteria", []), nonempty=True),
    )


def _history_data(entry: HistoryEntry) -> dict:
    return {
        "decision_id": entry.decision_id,
        "revision": entry.revision,
        "event": entry.event,
        "changed_fields": list(entry.changed_fields),
        "at": entry.at,
        "snapshot": _decision_data(entry.snapshot),
    }


def _history_from_data(data: dict, expected_id: str | None = None) -> HistoryEntry:
    try:
        return _build_history(data, expected_id)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise DecisionError(_UNREADABLE) from exc


def _build_history(data: dict, expected_id: str | None) -> HistoryEntry:
    if not isinstance(data, dict) or not all(isinstance(data[name], str) for name in ("decision_id", "event", "at")):
        raise ValueError("unknown history shape")
    if (expected_id is not None and data["decision_id"] != expected_id) or type(data["revision"]) is not int:
        raise ValueError("history entry does not match its row")
    return HistoryEntry(
        decision_id=data["decision_id"],
        revision=data["revision"],
        event=data["event"],
        changed_fields=_strings(data["changed_fields"]),
        at=data["at"],
        snapshot=_decision_from_data(data["snapshot"], data["decision_id"]),
    )



class SQLiteDecisionStore:
    def __init__(self, path: str | Path, *, read_only: bool = False):
        self.path = str(path)
        if read_only:
            uri = f"{Path(path).resolve().as_uri()}?mode=ro"
            self._connection = sqlite3.connect(uri, timeout=5.0, isolation_level=None, uri=True)
        else:
            self._connection = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        try:
            version = self._connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1) or (read_only and version != 1):
                raise UnsupportedSchemaVersion(f"unsupported decision store schema version: {version}")
            if read_only:
                self._connection.execute("PRAGMA query_only = ON")
                return
            self._connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    state_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decision_history (
                    decision_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    entry_json TEXT NOT NULL,
                    PRIMARY KEY (decision_id, revision)
                );
                CREATE TABLE IF NOT EXISTS idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL
                );
                """
            )
            if version == 0:
                self._connection.execute("PRAGMA user_version = 1")
        except Exception:
            self._connection.close()
            raise

    def get(self, decision_id: str) -> Decision | None:
        row = self._connection.execute(
            "SELECT state_json FROM decisions WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        return _decision_from_data(_load(row["state_json"]), decision_id) if row else None

    def list(self) -> tuple[Decision, ...]:
        rows = self._connection.execute(
            "SELECT decision_id, state_json FROM decisions ORDER BY decision_id"
        ).fetchall()
        return tuple(_decision_from_data(_load(row["state_json"]), row["decision_id"]) for row in rows)

    def history(self, decision_id: str) -> tuple[HistoryEntry, ...]:
        rows = self._connection.execute(
            "SELECT entry_json FROM decision_history WHERE decision_id = ? ORDER BY revision",
            (decision_id,),
        ).fetchall()
        return tuple(_history_from_data(_load(row["entry_json"]), decision_id) for row in rows)

    def replay(self, idempotency_key: str, request_hash: str) -> Decision | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT request_hash, result_json FROM idempotency WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        if row["request_hash"] != request_hash:
            raise IdempotencyConflict(idempotency_key)
        return _decision_from_data(_load(row["result_json"]))

    def commit(
        self,
        *,
        idempotency_key: str,
        request_hash: str,
        expected_revisions: dict[str, int],
        updates: tuple[Decision, ...],
        events: tuple[HistoryEntry, ...],
        result_id: str,
    ) -> Decision:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                previous = self._connection.execute(
                    "SELECT request_hash, result_json FROM idempotency WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if previous:
                    if previous["request_hash"] != request_hash:
                        raise IdempotencyConflict(idempotency_key)
                    self._connection.execute("COMMIT")
                    return _decision_from_data(_load(previous["result_json"]))

                for decision_id, expected in expected_revisions.items():
                    row = self._connection.execute(
                        "SELECT revision FROM decisions WHERE decision_id = ?", (decision_id,)
                    ).fetchone()
                    actual = row["revision"] if row else 0
                    if actual != expected:
                        if expected == 0 and actual:
                            raise DecisionAlreadyExists(decision_id)
                        raise ConcurrentModification(decision_id)

                for decision in updates:
                    data = json.dumps(_decision_data(decision), sort_keys=True, separators=(",", ":"))
                    self._connection.execute(
                        "INSERT INTO decisions(decision_id, revision, state_json) VALUES(?, ?, ?) "
                        "ON CONFLICT(decision_id) DO UPDATE SET revision=excluded.revision, state_json=excluded.state_json",
                        (decision.id, decision.revision, data),
                    )
                for event in events:
                    self._connection.execute(
                        "INSERT INTO decision_history(decision_id, revision, entry_json) VALUES(?, ?, ?)",
                        (
                            event.decision_id,
                            event.revision,
                            json.dumps(_history_data(event), sort_keys=True, separators=(",", ":")),
                        ),
                    )
                result = next((decision for decision in updates if decision.id == result_id), None)
                if result is None:
                    raise ValueError("result_id must identify one updated decision")
                result_json = json.dumps(_decision_data(result), sort_keys=True, separators=(",", ":"))
                self._connection.execute(
                    "INSERT INTO idempotency(idempotency_key, request_hash, result_json) VALUES(?, ?, ?)",
                    (idempotency_key, request_hash, result_json),
                )
                self._connection.execute("COMMIT")
                return result
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SQLiteDecisionStore:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
