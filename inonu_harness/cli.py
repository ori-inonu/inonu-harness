"""Local JSON CLI for the Inonu Harness."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .baseline import compare_runs, run_fixture
from .decision_graph import (
    Alternative,
    CriterionResult,
    DecisionError,
    DecisionGraph,
    EvidenceReference,
)
from .doctor import collect_environment
from .sdd_adapter import SddDecisionContextAdapter
from .sqlite_store import SQLiteDecisionStore


def _json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("expected a JSON object")
    return parsed


def _json_array(value: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise argparse.ArgumentTypeError("expected a JSON array")
    return parsed


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"cannot encode {type(value).__name__} as JSON")


def _write_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default))


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _read_json(path: str, *, reject_duplicate_keys: bool = False) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object if reject_duplicate_keys else None,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("cannot read a valid UTF-8 JSON file") from exc


def _task_packet(path: str) -> dict[str, str]:
    task = _read_json(path, reject_duplicate_keys=True)
    fields = ("task_id", "config_id", "prompt")
    if not isinstance(task, dict) or set(task) != set(fields):
        raise ValueError("task JSON must contain exactly task_id, config_id, and prompt")
    if any(not isinstance(task[name], str) or not task[name].strip() for name in fields):
        raise ValueError("task_id, config_id, and prompt must be non-empty strings")
    return {name: task[name] for name in fields}


def _db_path(value: str) -> Path:
    return Path(value).expanduser()


def _open_graph(path: Path, *, read_only: bool = False) -> tuple[SQLiteDecisionStore, DecisionGraph]:
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteDecisionStore(path, read_only=read_only)
    return store, DecisionGraph(store)


def _evidence(value: list[Any]) -> tuple[EvidenceReference, ...]:
    return tuple(EvidenceReference(**item) for item in value)


def _authorization_criteria(value: dict[str, Any]) -> dict[str, CriterionResult]:
    if any(not isinstance(key, str) or not isinstance(row, dict) for key, row in value.items()):
        raise ValueError("criteria must map criterion IDs to JSON objects")
    results: dict[str, CriterionResult] = {}
    for criterion_id, row in value.items():
        passed = row.get("passed")
        evidence = row.get("evidence")
        if not isinstance(passed, bool) or not isinstance(evidence, list):
            raise ValueError("each criterion needs a boolean passed value and evidence array")
        references = []
        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError("criterion evidence entries must be JSON objects")
            references.append(EvidenceReference(criterion_id=criterion_id, **item))
        results[criterion_id] = CriterionResult(passed, tuple(references))
    return results


def _decision_parser(commands: Any) -> None:
    decisions = commands.add_parser("decisions", help="create and inspect local persistent decisions")
    decisions.add_argument(
        "--db",
        type=_db_path,
        default=Path.home() / ".inonu-harness" / "decisions.sqlite",
        help="SQLite file (default: ~/.inonu-harness/decisions.sqlite)",
    )
    operations = decisions.add_subparsers(dest="operation", required=True)

    create = operations.add_parser("create", help="create a pending decision")
    create.add_argument("decision_id")
    create.add_argument("--question", required=True)
    create.add_argument("--alternatives", required=True, type=_json_array, help='JSON array of {"id", "label"}')
    create.add_argument("--criteria", required=True, type=_json_array, help="JSON array of required criterion IDs")
    create.add_argument("--constraints", type=_json_array, default=[])
    create.add_argument("--evidence", type=_json_array, default=[])
    create.add_argument("--dependencies", type=_json_array, default=[])
    create.add_argument("--idempotency-key", required=True)

    listing = operations.add_parser("list", help="list decisions")
    listing.add_argument("--status", choices=("pending", "blocked", "invalidated", "authorized"))

    show = operations.add_parser("show", help="show a decision and its revision history")
    show.add_argument("decision_id")

    review = operations.add_parser("review", help="revise a decision and preserve its history")
    review.add_argument("decision_id")
    review.add_argument("--question")
    review.add_argument("--alternatives", type=_json_array)
    review.add_argument("--criteria", type=_json_array)
    review.add_argument("--constraints", type=_json_array)
    review.add_argument("--evidence", type=_json_array)
    review.add_argument("--dependencies", type=_json_array)
    review.add_argument("--premise-changed", action="store_true")
    review.add_argument("--idempotency-key", required=True)

    recommend = operations.add_parser("recommend", help="record a recommendation without authorization")
    recommend.add_argument("decision_id")
    recommend.add_argument("--alternative-id", required=True)
    recommend.add_argument("--source", required=True)
    recommend.add_argument("--version", required=True)
    recommend.add_argument("--provenance", required=True)
    recommend.add_argument("--idempotency-key", required=True)

    authorize = operations.add_parser("authorize", help="record explicit, evidence-backed authorization")
    authorize.add_argument("decision_id")
    authorize.add_argument("--alternative-id", required=True)
    authorize.add_argument("--actor", required=True)
    authorize.add_argument(
        "--criteria",
        required=True,
        type=_json_object,
        help='JSON object such as {"safe":{"passed":true,"evidence":[{"source":"test","reference":"checks/safe","provenance":"local test"}]}}',
    )
    authorize.add_argument("--idempotency-key", required=True)

    block = operations.add_parser("block", help="mark a decision blocked with a reason")
    block.add_argument("decision_id")
    block.add_argument("--reason", required=True)
    block.add_argument("--idempotency-key", required=True)

    for name in ("history", "affected"):
        command = operations.add_parser(name, help=f"list {name} for a decision")
        command.add_argument("decision_id")

    context = operations.add_parser("context", help="print selected SDD decision context as JSON")
    context.add_argument("--ids", required=True, nargs="+", help="explicit decision IDs to include")

    packet = operations.add_parser("packet", help="print a task with selected SDD decision context as JSON")
    packet.add_argument("--task-file", required=True, help="UTF-8 JSON task file with task_id, config_id, and prompt")
    packet.add_argument("--ids", required=True, nargs="+", help="explicit decision IDs to include")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m inonu_harness")
    parser.add_argument("--version", action="version", version=f"inonu-harness {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="print a sanitized environment report as JSON")

    baseline = commands.add_parser("baseline", help="run offline baseline fixtures or compare saved runs")
    baseline_commands = baseline.add_subparsers(dest="operation", required=True)
    run = baseline_commands.add_parser("run", help="record a local fixture execution")
    run.add_argument("fixture", nargs="?")
    run.add_argument("--fixture", dest="fixture_option")
    run.add_argument("--execution-id")
    compare = baseline_commands.add_parser("compare", help="compare saved result JSON files")
    compare.add_argument("before")
    compare.add_argument("after")

    _decision_parser(commands)
    return parser


def _run_decision_command(args: argparse.Namespace) -> Any:
    task = _task_packet(args.task_file) if args.operation == "packet" else None
    store, graph = _open_graph(args.db, read_only=args.operation in ("context", "packet"))
    try:
        if args.operation in ("context", "packet"):
            adapter = SddDecisionContextAdapter(enabled=True, graph=graph)
            decision_context = adapter.load_context(args.ids)
            if args.operation == "packet":
                return {"schema_version": 1, "task": task, "decision_context": decision_context}
            return decision_context
        if args.operation == "create":
            return graph.create_decision(
                decision_id=args.decision_id,
                question=args.question,
                alternatives=tuple(Alternative(**item) for item in args.alternatives),
                constraints=args.constraints,
                required_criteria=args.criteria,
                evidence=_evidence(args.evidence),
                dependencies=args.dependencies,
                idempotency_key=args.idempotency_key,
            )
        if args.operation == "list":
            return graph.list_decisions(status=args.status)
        if args.operation == "show":
            return {"decision": graph.get(args.decision_id), "history": graph.history(args.decision_id)}
        if args.operation == "history":
            return graph.history(args.decision_id)
        if args.operation == "affected":
            return graph.affected_by(args.decision_id)
        if args.operation == "review":
            alternatives = (
                tuple(Alternative(**item) for item in args.alternatives)
                if args.alternatives is not None
                else None
            )
            evidence = _evidence(args.evidence) if args.evidence is not None else None
            return graph.revise(
                args.decision_id,
                question=args.question,
                alternatives=alternatives,
                constraints=args.constraints,
                required_criteria=args.criteria,
                evidence=evidence,
                dependencies=args.dependencies,
                relevant_premise_changed=args.premise_changed,
                idempotency_key=args.idempotency_key,
            )
        if args.operation == "recommend":
            return graph.recommend(
                args.decision_id,
                alternative_id=args.alternative_id,
                source=args.source,
                version=args.version,
                provenance=args.provenance,
                idempotency_key=args.idempotency_key,
            )
        if args.operation == "authorize":
            return graph.authorize(
                args.decision_id,
                alternative_id=args.alternative_id,
                actor=args.actor,
                criteria=_authorization_criteria(args.criteria),
                idempotency_key=args.idempotency_key,
            )
        if args.operation == "block":
            return graph.block_decision(
                args.decision_id,
                reason=args.reason,
                idempotency_key=args.idempotency_key,
            )
        raise AssertionError(f"unknown decision operation: {args.operation}")
    finally:
        store.close()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "doctor":
            _write_json(collect_environment())
        elif args.command == "baseline" and args.operation == "run":
            if args.fixture and args.fixture_option:
                raise ValueError("provide fixture as either a positional argument or --fixture")
            fixture = args.fixture_option or args.fixture
            if not fixture:
                raise ValueError("baseline run requires a fixture path")
            _write_json(run_fixture(fixture, execution_id=args.execution_id))
        elif args.command == "baseline" and args.operation == "compare":
            _write_json(compare_runs(_read_json(args.before), _read_json(args.after)))
        elif args.command == "decisions":
            _write_json(_run_decision_command(args))
        return 0
    except OSError:
        print("inonu-harness: local file operation failed; check the selected file and permissions", file=sys.stderr)
        return 2
    except sqlite3.Error:
        print("inonu-harness: decision store could not be opened or updated", file=sys.stderr)
        return 2
    except (DecisionError, TypeError, ValueError) as exc:
        print(f"inonu-harness: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
