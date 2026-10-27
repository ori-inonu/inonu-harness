"""Local JSON CLI for the Inonu Harness."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import __version__, milestones, versions
from .baseline import GATE_EXIT_CODES, compare_runs, gate_comparison, run_fixture
from .bundle import plan_bundle
from .bundle_apply import run_bundle, status_with_ownership
from .decision_graph import (
    Alternative,
    CriterionResult,
    Decision,
    DecisionError,
    DecisionGraph,
    EvidenceReference,
)
from .doctor import collect_environment
from .docs_lint import DEFAULT_MAX_BYTES, DEFAULT_MAX_LINES, lint
from .hook import _unique_json_object, run_stop, run_trust, run_untrust
from .jev_context import MAX_FACTS, build_spec, load_decision
from .loop import parse_spec, run_loop
from .sdd_adapter import SddDecisionContextAdapter
from .sdd_audit import audit_manifest, load_audit_manifest
from .secret_scan import scan
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


def _refuse_secret_patterns(value: Any) -> None:
    """Raise ValueError naming rules and paths when the printed object holds credential-like text."""
    printed = json.loads(json.dumps(value, default=_json_default))  # scan what the printer emits, not raw dataclasses
    findings = scan(printed)
    if findings:
        listed = ", ".join(f"{item['rule']} at {item['path']}" for item in findings)
        raise ValueError(f"refused to print credential-like text: {listed}")


def _read_json(path: str, *, reject_duplicate_keys: bool = False) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object if reject_duplicate_keys else None,
        )
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
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


_INSTANT_MESSAGE = "as-of TIMESTAMP must be ISO 8601 with an explicit offset or Z"


def _instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(_INSTANT_MESSAGE) from exc
    if parsed.tzinfo is None:
        raise ValueError(_INSTANT_MESSAGE)
    try:
        return parsed.astimezone(timezone.utc)
    except OverflowError as exc:  # an offset can push the instant past year 1 or 9999
        raise ValueError(_INSTANT_MESSAGE) from exc


def _as_of(graph: DecisionGraph, instant: datetime, ids: list[str] | None) -> list[dict[str, Any]]:
    """Each decision's latest history entry recorded at or before instant."""
    decision_ids = sorted(set(ids)) if ids is not None else sorted(item.id for item in graph.list_decisions())
    items: list[dict[str, Any]] = []
    for decision_id in decision_ids:
        history = graph.history(decision_id)  # DecisionNotFound for an unknown explicit id
        visible = [entry for entry in history if _instant(entry.at) <= instant]
        if not visible:
            if ids is not None:
                items.append(
                    {
                        "id": decision_id,
                        "state": "not_yet_created",
                        "revision": None,
                        "recorded_at": None,
                        "later_revision": True,
                        "snapshot": None,
                    }
                )
            continue
        entry = max(visible, key=lambda item: item.revision)
        items.append(
            {
                "id": decision_id,
                "state": "existed",
                "revision": entry.revision,
                "recorded_at": entry.at,
                "later_revision": any(item.revision > entry.revision for item in history),
                "snapshot": entry.snapshot,
            }
        )
    return items


def _ready_queue(decisions: tuple[Decision, ...]) -> dict[str, Any]:
    """Pending decisions whose declared dependencies are all authorized, and the pending ones still waiting."""
    status = {item.id: item.status for item in decisions}
    ready: list[dict[str, Any]] = []
    waiting: list[dict[str, Any]] = []
    for item in sorted(decisions, key=lambda decision: decision.id):
        if item.status != "pending":
            continue
        waiting_on = [
            {"id": dependency_id, "status": status.get(dependency_id, "missing")}
            for dependency_id in item.dependencies
            if status.get(dependency_id) != "authorized"
        ]
        if waiting_on:
            waiting.append({"id": item.id, "question": item.question, "waiting_on": waiting_on})
        else:
            ready.append({"id": item.id, "question": item.question, "dependencies": item.dependencies})
    return {"schema_version": 1, "ready": ready, "waiting": waiting}


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
    context.add_argument("--refuse-secret-patterns", action="store_true", help="exit 2 with no stdout if the output holds credential-like text")

    packet = operations.add_parser("packet", help="print a task with selected SDD decision context as JSON")
    packet.add_argument("--task-file", required=True, help="UTF-8 JSON task file with task_id, config_id, and prompt")
    packet.add_argument("--ids", required=True, nargs="+", help="explicit decision IDs to include")
    packet.add_argument("--refuse-secret-patterns", action="store_true", help="exit 2 with no stdout if the output holds credential-like text")

    as_of = operations.add_parser("as-of", help="print decisions as they were at TIMESTAMP, read from history")
    as_of.add_argument("timestamp", help="ISO 8601 time with an explicit offset or Z")
    as_of.add_argument("--ids", nargs="+", help="decision IDs to include (default: every decision that existed then)")

    operations.add_parser("ready", help="list pending decisions whose declared dependencies are all authorized")


CHECK_GIT_TIMEOUT_SECONDS = 60


def _git(root: Path, *arguments: str) -> str | None:
    """Stdout of one git command run in root, or None when git exits non-zero."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments], stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=CHECK_GIT_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("git is unavailable or did not finish in time") from exc
    return result.stdout.strip() if result.returncode == 0 else None


def _git_bytes(root: Path, *arguments: str, data: bytes | None = None) -> bytes | None:
    """Raw stdout of one git command run in root, or None when git exits non-zero."""
    feed: dict[str, Any] = {"input": data} if data is not None else {"stdin": subprocess.DEVNULL}
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments], capture_output=True, timeout=CHECK_GIT_TIMEOUT_SECONDS,
            check=False, **feed,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("git is unavailable or did not finish in time") from exc
    return result.stdout if result.returncode == 0 else None


def _exportable_path(path: str) -> str:
    """A committed path that is safe to write under the export directory on every host, else ValueError."""
    parts = path.split("/")
    unsafe = (
        not path or path.startswith("/")
        or any(part in ("", ".", "..") or part.lower() == ".git" or ":" in part or "\\" in part for part in parts)
    )
    if unsafe:
        raise ValueError("commit contains a path that cannot be exported safely")
    return path


def _export_tree(top: Path, commit: str, tree: Path) -> list[str]:
    """Write the commit's blobs exactly as stored.

    Unlike git archive, this applies no export-ignore, export-subst or line-ending conversion, so a committed file
    cannot silently go missing or change. Gitlinks (submodules) are not exported; a symlink becomes a plain file
    holding its target text, never a link, and its path is returned so that a step can refuse what it cannot read as a link.

    shortcut: every blob is held in memory once, upgrade to streaming cat-file for repositories of hundreds of megabytes.
    """
    listing = _git_bytes(top, "ls-tree", "-r", "-z", "--full-tree", commit)
    if listing is None:
        raise ValueError("git could not export the ref")
    entries: list[tuple[str, str]] = []
    symlinks: list[str] = []
    for record in listing.split(b"\0"):
        header, _, raw_path = record.partition(b"\t")
        fields = header.split(b" ")
        if len(fields) == 3 and fields[1] == b"blob":
            entries.append((fields[2].decode("ascii"), _exportable_path(os.fsdecode(raw_path))))
            if fields[0] == b"120000":
                symlinks.append(entries[-1][1])
    tree.mkdir(parents=True)
    if not entries:
        return symlinks
    blobs = _git_bytes(top, "cat-file", "--batch", data="".join(f"{sha}\n" for sha, _ in entries).encode("ascii"))
    if blobs is None:
        raise ValueError("git could not export the ref")
    position, root = 0, tree
    for sha, rel in entries:
        end = blobs.find(b"\n", position)
        fields = blobs[position:end].split(b" ") if end >= 0 else []
        if len(fields) != 3 or fields[0].decode("ascii", "replace") != sha or fields[1] != b"blob":
            raise ValueError("git could not export the ref")
        size = int(fields[2])
        content, position = blobs[end + 1:end + 1 + size], end + 1 + size + 1
        destination = root / rel  # rel passed _exportable_path, and only plain files are written
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return symlinks


def _export_ref(checkout: Path, ref: str, scratch: Path) -> tuple[Path, list[str]]:
    """Extract the commit REF under scratch; return the part of it that corresponds to checkout, and the committed symlinks."""
    top, prefix = _git(checkout, "rev-parse", "--show-toplevel"), _git(checkout, "rev-parse", "--show-prefix")
    if top is None or prefix is None:
        raise ValueError("check root must be inside a git repository")
    commit = None if ref.startswith("-") else _git(checkout, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if not commit:
        raise ValueError("ref does not resolve to a commit")
    tree = scratch / "tree"
    symlinks = _export_tree(Path(top), commit, tree)  # from the repository top: a subdirectory root still sees the whole commit
    return tree / prefix, symlinks


def _under_milestones(path: str) -> bool:
    return "/docs/specs/milestones/" in f"/{path}/"


def _run_steps(checkout: Path, *, runner: bool, symlinks: Sequence[str] = ()) -> list[dict[str, Any]]:
    if not (checkout / "tests").is_dir():
        raise ValueError("check root must contain a tests directory")
    sources = [name for name in ("inonu_harness", "scripts", "tests") if (checkout / name).is_dir()]
    steps = [
        ("compile", [sys.executable, "-m", "compileall", "-q", *sources]),
        ("versions", [sys.executable, "-m", "inonu_harness.versions", "--scheme"]),
    ]
    # v0.0.9 is the first milestone written in the R<n> format; the earlier ones predate it and are not checked.
    if (checkout / "docs" / "specs" / "milestones").is_dir() or any(_under_milestones(path) for path in symlinks):
        steps.append(("milestones", [sys.executable, "-m", "inonu_harness", "milestone", "check", "--from", "0.0.9"]))
    steps.append(("tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"]))
    if runner:
        steps.append(("runner", [sys.executable, "scripts/inonu.py", "--version"]))
    results = []
    for name, command in steps:
        if name == "milestones" and any(_under_milestones(path) for path in symlinks):
            # the export writes a committed link as a plain file, which the check would read as an empty milestone
            sys.stderr.write("a symbolic link is committed under docs/specs/milestones; the milestone check cannot read it\n")
            results.append({"name": name, "exit_code": 1})
            continue
        result = subprocess.run(
            command, cwd=checkout, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
        sys.stderr.write(result.stdout + result.stderr)
        results.append({"name": name, "exit_code": result.returncode})
    return results


def _run_check(root: Path | None, ref: str | None = None) -> dict[str, Any]:
    checkout = (root or Path(__file__).resolve().parents[1]).resolve()
    if ref is None:
        steps = _run_steps(checkout, runner=False)
    else:
        with tempfile.TemporaryDirectory() as scratch:
            tree, symlinks = _export_ref(checkout, ref, Path(scratch))
            steps = _run_steps(tree, runner=True, symlinks=symlinks)
    report: dict[str, Any] = {"schema_version": 1, "passed": all(step["exit_code"] == 0 for step in steps), "steps": steps}
    if ref is not None:
        report["ref"] = ref
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m inonu_harness")
    parser.add_argument("--version", action="version", version=f"inonu-harness {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="print a sanitized environment report as JSON")
    doctor.add_argument("--project-root", type=Path, help="project to inspect (default: this checkout)")

    check = commands.add_parser("check", help="compile and run the test suite; print a JSON verdict")
    check.add_argument("--root", type=Path, help="checkout to verify (default: this checkout)")
    check.add_argument("--ref", help="verify this commit in a temporary export instead of the working tree")

    version = commands.add_parser("version", help="check the milestone version scheme, or print the next milestone's version")
    version.add_argument("--root", type=Path, default=Path("."), help="checkout whose manifests are compared (default: current directory)")
    version.add_argument("--scheme", action="store_true", help="also require every stated version to be in the 0.MINOR.PATCH scheme")
    version.add_argument("--next", action="store_true", help="print the next milestone's version computed from the stated version")

    milestone = commands.add_parser("milestone", help="create the next milestone folder, or check the milestone folders")
    milestones.add_commands(milestone)

    bundle = commands.add_parser("bundle", help="inspect the host bundle without writing")
    bundle_commands = bundle.add_subparsers(dest="operation", required=True)
    bundle_plan = bundle_commands.add_parser("plan", help="print the read-only bundle plan as JSON")
    bundle_plan.add_argument("--host", choices=("codex", "claude", "both"), default="both")
    bundle_plan.add_argument("--home", type=Path, help="home directory (default: the user's home)")
    bundle_status = bundle_commands.add_parser("status", help="report read-only how far each host matches the bundle plan")
    bundle_status.add_argument("--host", choices=("codex", "claude", "both"), default="both")
    bundle_status.add_argument("--home", type=Path, help="home directory (default: the user's home)")
    for name, text in (("apply", "preview or write the host bundle"), ("remove", "preview or remove what the bundle ledger proves is ours")):
        bundle_change = bundle_commands.add_parser(name, help=text)
        bundle_change.add_argument("--host", choices=("codex", "claude", "both"), default="both")
        bundle_change.add_argument("--home", type=Path, help="home directory (default: the user's home)")
        bundle_change.add_argument("--with-stop-hook", action="store_true", help="also register the Claude Stop hook")
        bundle_change.add_argument("--apply", action="store_true", help="write changes (default: preview only)")

    baseline = commands.add_parser("baseline", help="run offline baseline fixtures or compare saved runs")
    baseline_commands = baseline.add_subparsers(dest="operation", required=True)
    run = baseline_commands.add_parser("run", help="record a local fixture execution")
    run.add_argument("fixture", nargs="?")
    run.add_argument("--fixture", dest="fixture_option")
    run.add_argument("--execution-id")
    compare = baseline_commands.add_parser("compare", help="compare saved result JSON files")
    compare.add_argument("before")
    compare.add_argument("after")
    compare.add_argument(
        "--max-regression",
        type=float,
        help="fail when a gated metric rises beyond this ratio (0.10 allows a 10 percent increase)",
    )

    sdd = commands.add_parser("sdd", help="inspect optional SDD artifact contracts")
    sdd_commands = sdd.add_subparsers(dest="operation", required=True)
    audit = sdd_commands.add_parser("audit", help="audit a local artifact manifest")
    audit.add_argument("manifest")
    audit.add_argument("--root", type=Path, help="root directory for evidence paths (default: manifest directory)")

    loop = commands.add_parser("loop", help="run a verifier-gated loop from a JSON spec and print a JSON summary")
    loop_commands = loop.add_subparsers(dest="operation", required=True)
    loop_run = loop_commands.add_parser("run", help="run the loop described by SPEC")
    loop_run.add_argument("spec", help="strict JSON loop spec; relative log and cwd resolve against its directory")

    hook = commands.add_parser("hook", help="opt-in Stop hook and the trust record for its project verifier config")
    hook_commands = hook.add_subparsers(dest="operation", required=True)
    hook_stop = hook_commands.add_parser("stop", help="Stop hook entry: reads the hook JSON from stdin; exit 2 blocks the stop")
    hook_stop.add_argument("--home", type=Path, help="home directory holding the trust file (default: the user's home)")
    hook_trust = hook_commands.add_parser("trust", help="preview the project's verifier config; --yes records trust of it")
    hook_trust.add_argument("--root", type=Path, help="project holding .inonu/verify.json (default: current directory)")
    hook_trust.add_argument("--home", type=Path, help="home directory holding the trust file (default: the user's home)")
    hook_trust.add_argument("--yes", action="store_true", help="record trust (default: preview only)")
    hook_untrust = hook_commands.add_parser("untrust", help="remove the trust record for the project's verifier config")
    hook_untrust.add_argument("--root", type=Path, help="project holding .inonu/verify.json (default: current directory)")
    hook_untrust.add_argument("--home", type=Path, help="home directory holding the trust file (default: the user's home)")

    docs = commands.add_parser("docs", help="check instruction files and Markdown links without writing")
    docs_commands = docs.add_subparsers(dest="operation", required=True)
    docs_lint = docs_commands.add_parser("lint", help="print a JSON lint report; exit 1 when findings exist")
    docs_lint.add_argument("--root", type=Path, default=Path("."), help="repository root (default: current directory)")
    docs_lint.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="instruction file byte limit")
    docs_lint.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="instruction file line limit")

    jev = commands.add_parser("jev", help="build a Jev decision spec whose facts come from documents; calls no Jev")
    jev_commands = jev.add_subparsers(dest="operation", required=True)
    jev_spec = jev_commands.add_parser("spec", help="print the spec as one JSON line; writes no file")
    jev_spec.add_argument("--decision", required=True, type=Path, metavar="PATH", help="JSON decision object: id, goal, rails, options and optional facts, forbidden, unknowns")
    jev_spec.add_argument("--doc", dest="documents", required=True, action="append", metavar="PATH", help="document whose text becomes facts; repeat in the order wanted")
    jev_spec.add_argument("--root", type=Path, default=Path("."), help="directory that --doc paths resolve against (default: current directory)")
    jev_spec.add_argument("--max-facts", type=int, default=MAX_FACTS, help=f"fact budget for the documents (default: {MAX_FACTS})")

    _decision_parser(commands)
    return parser


def _run_decision_command(args: argparse.Namespace) -> Any:
    task = _task_packet(args.task_file) if args.operation == "packet" else None
    instant = _instant(args.timestamp) if args.operation == "as-of" else None
    store, graph = _open_graph(args.db, read_only=args.operation in ("context", "packet", "as-of", "ready"))
    try:
        if args.operation in ("context", "packet"):
            if args.refuse_secret_patterns:  # the lookup error below would echo an unknown id back
                _refuse_secret_patterns({"ids": args.ids})
            adapter = SddDecisionContextAdapter(enabled=True, graph=graph)
            decision_context = adapter.load_context(args.ids)
            if args.operation == "packet":
                printed = {"schema_version": 1, "task": task, "decision_context": decision_context}
            else:
                printed = decision_context
            if args.refuse_secret_patterns:
                _refuse_secret_patterns(printed)
            return printed
        if args.operation == "as-of":
            return {"schema_version": 1, "as_of": instant.isoformat(), "decisions": _as_of(graph, instant, args.ids)}
        if args.operation == "ready":
            return _ready_queue(graph.list_decisions())
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


def _read_stdin() -> str:
    """The hook's JSON body; missing or unreadable stdin reads as empty, which the hook treats as {}."""
    try:
        return sys.stdin.buffer.read(1 << 20).decode("utf-8", errors="replace")  # the hook body is small; read no more
    except (AttributeError, OSError, ValueError):
        return ""


def _emit(stream: Any, text: str) -> None:
    """Write text; a narrow console encoding gets escapes instead of turning a finished hook into a traceback."""
    if not text or stream is None:
        return
    try:
        stream.write(text)
    except UnicodeEncodeError:
        stream.write(text.encode("ascii", "backslashreplace").decode("ascii"))


def _run_hook(args: argparse.Namespace) -> int:
    if args.operation == "stop":  # the Stop hook prints only to stderr; stdout stays empty
        code, stderr_text = run_stop(_read_stdin(), os.environ, args.home)
        _emit(sys.stderr, stderr_text)
        return code
    if args.operation == "trust":
        code, stdout_text, stderr_text = run_trust(args.root, args.home, yes=args.yes)
    else:
        code, stdout_text, stderr_text = run_untrust(args.root, args.home)
    _emit(sys.stdout, stdout_text)
    _emit(sys.stderr, stderr_text)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "doctor":
            _write_json(collect_environment(project_root=args.project_root))
        elif args.command == "check":
            report = _run_check(args.root, args.ref)
            # ASCII-escaped: a ref name outside the stdout code page must not turn a finished check into exit 2
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["passed"] else 1
        elif args.command == "version":
            flags = [flag for flag, chosen in (("--scheme", args.scheme), ("--next", args.next)) if chosen]
            return versions.main([*flags, "--root", str(args.root)])
        elif args.command == "milestone":
            return milestones.run(args)
        elif args.command == "bundle" and args.operation == "status":
            _write_json(status_with_ownership(args.host, args.home))
        elif args.command == "bundle" and args.operation in ("apply", "remove"):
            status, report = run_bundle(
                args.operation, args.host, args.home,
                with_stop_hook=args.with_stop_hook, apply=args.apply,
            )
            _write_json(report)
            if status:
                print("inonu-harness: bundle conflict detected; inspect the reported items", file=sys.stderr)
            return status
        elif args.command == "bundle":
            plan = plan_bundle(args.host, args.home)
            _write_json(plan)
            if any(item["kind"] == "skill" and item["status"]["skill"] == "conflict" for item in plan["items"]):
                print("inonu-harness: selected profile has unmanaged or modified files; nothing written", file=sys.stderr)
                return 2
        elif args.command == "baseline" and args.operation == "run":
            if args.fixture and args.fixture_option:
                raise ValueError("provide fixture as either a positional argument or --fixture")
            fixture = args.fixture_option or args.fixture
            if not fixture:
                raise ValueError("baseline run requires a fixture path")
            _write_json(run_fixture(fixture, execution_id=args.execution_id))
        elif args.command == "baseline" and args.operation == "compare":
            strict = args.max_regression is not None  # the gate must not read a value a duplicate key could shadow
            before = _read_json(args.before, reject_duplicate_keys=strict)
            after = _read_json(args.after, reject_duplicate_keys=strict)
            comparison = compare_runs(before, after)
            if args.max_regression is None:
                _write_json(comparison)
            else:
                gate = gate_comparison(before, after, comparison, args.max_regression)
                _write_json({**comparison, "gate": gate})
                return GATE_EXIT_CODES[gate["status"]]
        elif args.command == "sdd" and args.operation == "audit":
            manifest = load_audit_manifest(args.manifest)
            root = args.root if args.root is not None else Path(args.manifest).parent
            report = audit_manifest(manifest, root)
            _write_json(report)
            return 0 if report["status"] == "pass" else 1
        elif args.command == "decisions":
            result = _run_decision_command(args)
            if args.operation in ("as-of", "ready"):
                # ASCII-escaped: decision text outside the stdout code page must not turn a finished query into exit 2
                print(json.dumps(result, indent=2, sort_keys=True, default=_json_default))
            else:
                _write_json(result)
        elif args.command == "loop":
            spec = parse_spec(_read_json(args.spec, reject_duplicate_keys=True), Path(args.spec).absolute().parent)
            summary = run_loop(spec)
            # ASCII-escaped: a narrow stdout encoding must not turn a finished run into exit 2
            print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["status"] == "verified_done" else 1
        elif args.command == "hook":
            return _run_hook(args)
        elif args.command == "docs" and args.operation == "lint":
            report = lint(args.root, max_bytes=args.max_bytes, max_lines=args.max_lines)
            print(json.dumps(report, indent=2, sort_keys=True))  # ASCII-escaped, like the loop summary
            return 0 if report["status"] == "pass" else 1
        elif args.command == "jev" and args.operation == "spec":
            spec = build_spec(load_decision(args.decision), args.documents, args.root, args.max_facts)
            # compact and ASCII-escaped: the spec goes to consensus_plan and consensus_run unchanged
            print(json.dumps(spec, ensure_ascii=True, separators=(",", ":")))
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
