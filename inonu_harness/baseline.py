"""Offline, fixture-backed baseline recording and comparison.

The result schema intentionally records provenance next to each measured value.
It does not infer model usage, token counts, costs, or tool activity.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
import uuid
from collections.abc import Callable, Mapping
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


RESULT_SCHEMA_VERSION = 1
_FIXTURE_REQUIRED = (
    "fixture_schema_version",
    "fixture_id",
    "task_id",
    "config_id",
    "acceptance",
    "runtime",
    "model",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "tool_calls",
    "failures",
    "blocks",
    "recoveries",
)
_METRIC_UNITS = {
    "acceptance": "criteria",
    "elapsed_seconds": "seconds",
    "runtime": "runtime",
    "model": "model",
    "input_tokens": "tokens",
    "output_tokens": "tokens",
    "cost_usd": "USD",
    "tool_calls": "calls",
    "failures": "events",
    "blocks": "events",
    "recoveries": "events",
    "component_versions": "versions",
}
_LIST_FIELDS = ("acceptance", "tool_calls", "failures", "blocks", "recoveries")
_OPTIONAL_STRING_FIELDS = ("runtime", "model")
_OPTIONAL_NUMBER_FIELDS = ("input_tokens", "output_tokens", "cost_usd")
_FIXTURE_MEASUREMENT_FIELDS = {
    "acceptance",
    "runtime",
    "model",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "tool_calls",
    "failures",
    "blocks",
    "recoveries",
}


GATE_EXIT_CODES = {"pass": 0, "fail": 1, "incomparable": 2}
_GATED_COUNTS = ("tool_calls", "failures", "blocks")
_GATED_AMOUNTS = ("input_tokens", "output_tokens", "cost_usd")
_GATED_METRICS = ("acceptance", *_GATED_COUNTS, *_GATED_AMOUNTS)


def run_fixture(
    fixture: str | Path | Mapping[str, Any],
    *,
    execution_id: str | None = None,
    clock: Callable[[], float] | None = None,
    version_source: Callable[[], Mapping[str, str]] | Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Turn a local fixture into one schema-versioned baseline result.

    ``clock`` and ``version_source`` are injectable so callers can produce
    deterministic tests. The default clock measures only this local call; the
    default version source observes the Python runtime. Fixture paths are never
    copied into the result.
    """

    data = _load_fixture(fixture)
    _validate_fixture(data)
    if execution_id is not None and (not isinstance(execution_id, str) or not execution_id.strip()):
        raise ValueError("execution_id must be a non-empty string when provided")
    clock_fn = clock or time.perf_counter
    start = _finite_number(clock_fn(), "clock start")
    versions = _read_versions(version_source)
    end = _finite_number(clock_fn(), "clock end")
    elapsed = end - start
    if elapsed < 0:
        raise ValueError("clock moved backwards")

    fixture_id = data["fixture_id"]
    fixture_source = {"kind": "fixture", "reference": fixture_id}
    unavailable_sources = {
        name: {"kind": "unavailable", "reason": "not_observed"}
        for name in ("runtime", "model", *_OPTIONAL_NUMBER_FIELDS)
        if data[name] is None
    }
    measurement_sources = data.get("measurement_sources", {})
    metrics = {
        "acceptance": _measurement(data["acceptance"], _source_for(measurement_sources, "acceptance", fixture_source, "criteria")),
        "elapsed_seconds": _measurement(
            elapsed,
            {
                "kind": "clock",
                "reference": "time.perf_counter" if clock is None else "injected",
                "unit": "seconds",
            },
        ),
        "runtime": _measurement(
            data["runtime"],
            _source_for(measurement_sources, "runtime", unavailable_sources.get("runtime", fixture_source), "runtime"),
        ),
        "model": _measurement(
            data["model"],
            _source_for(measurement_sources, "model", unavailable_sources.get("model", fixture_source), "model"),
        ),
        "input_tokens": _measurement(
            data["input_tokens"],
            _source_for(measurement_sources, "input_tokens", unavailable_sources.get("input_tokens", fixture_source), "tokens"),
        ),
        "output_tokens": _measurement(
            data["output_tokens"],
            _source_for(measurement_sources, "output_tokens", unavailable_sources.get("output_tokens", fixture_source), "tokens"),
        ),
        "cost_usd": _measurement(
            data["cost_usd"],
            _source_for(measurement_sources, "cost_usd", unavailable_sources.get("cost_usd", fixture_source), "USD"),
        ),
        "tool_calls": _measurement(data["tool_calls"], _source_for(measurement_sources, "tool_calls", fixture_source, "calls")),
        "failures": _measurement(data["failures"], _source_for(measurement_sources, "failures", fixture_source, "events")),
        "blocks": _measurement(data["blocks"], _source_for(measurement_sources, "blocks", fixture_source, "events")),
        "recoveries": _measurement(data["recoveries"], _source_for(measurement_sources, "recoveries", fixture_source, "events")),
        "component_versions": _measurement(
            versions if versions else None,
            {
                "kind": "unavailable" if not versions else "version_source",
                "reference": "not_observed" if not versions else ("python-runtime" if version_source is None else "injected"),
                "unit": "versions",
            },
        ),
    }

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "execution_id": execution_id or str(uuid.uuid4()),
        "task_id": data["task_id"],
        "config_id": data["config_id"],
        "metrics": metrics,
    }


def compare_runs(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Compare matching task/config runs without filling unobserved metrics."""

    _validate_result(before, "before")
    _validate_result(after, "after")
    base = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "before_execution_id": before["execution_id"],
        "after_execution_id": after["execution_id"],
        "task_id": before["task_id"],
        "config_id": before["config_id"],
        "compatible": False,
        "comparisons": {},
    }
    if before["schema_version"] != after["schema_version"]:
        base["reason"] = "schema_version_mismatch"
        return base
    if before["task_id"] != after["task_id"] or before["config_id"] != after["config_id"]:
        base["reason"] = "task_or_config_mismatch"
        return base

    base["compatible"] = True
    for name in _METRIC_UNITS:
        base["comparisons"][name] = _compare_measurements(
            before["metrics"].get(name), after["metrics"].get(name), _METRIC_UNITS[name]
        )
    return base


def gate_comparison(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    comparison: Mapping[str, Any],
    max_regression: float,
) -> dict[str, Any]:
    """Judge a ``compare_runs`` result for regressions; pure and deterministic.

    ``before`` and ``after`` must be the results that produced ``comparison``.
    Only ``compared`` metrics the gate judges can fail it; every other metric
    is listed under ``skipped`` with its reason.
    """

    limit = _max_regression(max_regression)
    if comparison.get("compatible") is not True:
        return {
            "max_regression": limit,
            "status": "incomparable",
            "regressions": [],
            "skipped": [{"metric": name, "reason": comparison.get("reason")} for name in _METRIC_UNITS],
        }

    regressions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    unjudgeable = False
    for name in _METRIC_UNITS:
        result = comparison["comparisons"].get(name, {})
        if result.get("status") != "compared":
            skipped.append({"metric": name, "reason": result.get("reason")})
            # A changed measurement basis hides a possible regression; an unavailable value is just absent.
            unjudgeable = unjudgeable or (name in _GATED_METRICS and result.get("reason") == "source_incompatible")
        elif name not in _GATED_METRICS:
            skipped.append({"metric": name, "reason": "not_judged"})
        elif name == "acceptance":
            regressions.extend(_acceptance_regressions(before, after))
        else:
            old, new = _gated_amount(before, name), _gated_amount(after, name)
            if _exceeds(old, new, limit):
                regressions.append(
                    {
                        "metric": name,
                        "before": old,
                        "after": new,
                        "reason": "increase_from_zero" if old == 0 else "exceeds_max_regression",
                    }
                )
    return {
        "max_regression": limit,
        "status": "fail" if regressions else ("incomparable" if unjudgeable else "pass"),
        "regressions": regressions,
        "skipped": skipped,
    }


def _acceptance_regressions(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[dict[str, Any]]:
    after_passed: dict[str, bool] = {}
    for item in after["metrics"]["acceptance"]["value"]:
        after_passed[item["id"]] = after_passed.get(item["id"], True) and item["passed"]
    passed_before = {item["id"] for item in before["metrics"]["acceptance"]["value"] if item["passed"]}
    return [
        {
            "metric": f"acceptance:{criterion}",
            "before": True,
            "after": after_passed.get(criterion),
            "reason": "criterion_failed" if criterion in after_passed else "criterion_missing",
        }
        for criterion in sorted(passed_before)
        if after_passed.get(criterion) is not True
    ]


def _gated_amount(run: Mapping[str, Any], name: str) -> Any:
    value = run["metrics"][name]["value"]
    return len(value) if name in _GATED_COUNTS else value


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(value)
    except OverflowError:  # an int beyond float range is not a usable measurement
        return False


def _exceeds(old: Any, new: Any, limit: float) -> bool:
    """new > old * (1 + limit) in exact decimal arithmetic, so a rise of exactly `limit` is not a regression."""
    with localcontext() as context:
        context.prec = 400
        return Decimal(str(new)) > Decimal(str(old)) * (1 + Decimal(repr(limit)))


def _max_regression(value: Any) -> float:
    if not _is_number(value) or not _finite(value) or value < 0:
        raise ValueError("max_regression must be a finite number greater than or equal to 0")
    return float(value)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate JSON object key")  # a later duplicate could hide a regressed value
    return dict(pairs)


def _load_fixture(fixture: str | Path | Mapping[str, Any], *, strict: bool = False) -> dict[str, Any]:
    if isinstance(fixture, Mapping):
        return dict(fixture)
    try:
        path = Path(fixture)
        parsed = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs if strict else None)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("fixture must be a readable UTF-8 JSON file or mapping") from exc
    if not isinstance(parsed, dict):
        raise ValueError("fixture root must be a JSON object")
    return parsed


def _validate_fixture(data: Mapping[str, Any]) -> None:
    missing = [name for name in _FIXTURE_REQUIRED if name not in data]
    if missing:
        raise ValueError(f"fixture missing required fields: {', '.join(missing)}")
    if isinstance(data["fixture_schema_version"], bool) or data["fixture_schema_version"] != 1:
        raise ValueError("unsupported fixture_schema_version")
    for name in ("fixture_id", "task_id", "config_id"):
        if not isinstance(data[name], str) or not data[name].strip():
            raise ValueError(f"{name} must be a non-empty string")
    for name in _LIST_FIELDS:
        if not isinstance(data[name], list):
            raise ValueError(f"{name} must be a list")
    for item in data["acceptance"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not item["id"].strip()
            or not isinstance(item.get("passed"), bool)
        ):
            raise ValueError("acceptance entries require a non-empty id and boolean passed value")
    for name in _OPTIONAL_STRING_FIELDS:
        if data[name] is not None and not isinstance(data[name], str):
            raise ValueError(f"{name} must be a string or null")
    for name in _OPTIONAL_NUMBER_FIELDS:
        value = data[name]
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not _finite(value) or value < 0):
            raise ValueError(f"{name} must be a non-negative finite number or null")
    sources = data.get("measurement_sources", {})
    if not isinstance(sources, dict):
        raise ValueError("measurement_sources must be an object")
    for name, source in sources.items():
        if name not in _FIXTURE_MEASUREMENT_FIELDS or not _valid_source(source):
            raise ValueError(f"invalid measurement source for {name}")


def _read_versions(
    source: Callable[[], Mapping[str, str]] | Mapping[str, str] | None,
) -> dict[str, str]:
    if source is None:
        values: Mapping[str, str] = {"python": platform.python_version()}
    elif callable(source):
        values = source()
    else:
        values = source
    if not isinstance(values, Mapping):
        raise ValueError("version_source must return a mapping")
    versions = dict(values)
    if any(not isinstance(name, str) or not name.strip() or not isinstance(version, str) or not version.strip() for name, version in versions.items()):
        raise ValueError("component version names and versions must be non-empty strings")
    return versions


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not _finite(value):
        raise ValueError(f"{label} must return a finite number")
    return float(value)


def _measurement(value: Any, source: Mapping[str, Any]) -> dict[str, Any]:
    if not _valid_source(source):
        raise ValueError("measurement source must include a non-empty kind")
    if (value is None) != (source["kind"] == "unavailable"):
        raise ValueError("unavailable measurements must be null and observed measurements must not be null")
    return {"value": value, "source": dict(source)}


def _source_for(
    sources: Mapping[str, Any], name: str, default: Mapping[str, Any], unit: str
) -> dict[str, Any]:
    source = sources.get(name, default)
    if not _valid_source(source):
        raise ValueError(f"invalid measurement source for {name}")
    result = dict(source)
    result.setdefault("unit", unit)
    return result


def _valid_source(source: Any) -> bool:
    return isinstance(source, Mapping) and isinstance(source.get("kind"), str) and bool(source["kind"].strip())


def _validate_result(result: Mapping[str, Any], label: str) -> None:
    required = ("schema_version", "execution_id", "task_id", "config_id", "metrics")
    if not isinstance(result, Mapping) or any(name not in result for name in required):
        raise ValueError(f"{label} run is missing required fields")
    if (
        isinstance(result["schema_version"], bool)
        or not isinstance(result["schema_version"], int)
        or result["schema_version"] != RESULT_SCHEMA_VERSION
        or not isinstance(result["execution_id"], str)
        or not result["execution_id"].strip()
    ):
        raise ValueError(f"{label} run has unsupported schema or invalid execution id")
    if (
        not isinstance(result["task_id"], str)
        or not result["task_id"].strip()
        or not isinstance(result["config_id"], str)
        or not result["config_id"].strip()
    ):
        raise ValueError(f"{label} run has invalid task or config id")
    if not isinstance(result["metrics"], Mapping):
        raise ValueError(f"{label} run metrics must be an object")
    for name in _METRIC_UNITS:
        measurement = result["metrics"].get(name)
        if not isinstance(measurement, Mapping) or "value" not in measurement or not _valid_source(measurement.get("source")):
            raise ValueError(f"{label} run has an invalid {name} measurement")
        value = measurement["value"]
        source = measurement["source"]
        if (value is None) != (source["kind"] == "unavailable"):
            raise ValueError(f"{label} run has inconsistent availability for {name}")
        if name in ("elapsed_seconds", "input_tokens", "output_tokens", "cost_usd") and value is not None:
            if not _is_number(value) or not _finite(value) or value < 0:
                raise ValueError(f"{label} run has an invalid numeric value for {name}")
        if name in _LIST_FIELDS and (not isinstance(value, list) or not _valid_list_metric(name, value)):
            raise ValueError(f"{label} run has an invalid list value for {name}")
        if name in _OPTIONAL_STRING_FIELDS and value is not None and not isinstance(value, str):
            raise ValueError(f"{label} run has an invalid string value for {name}")
        if name == "component_versions" and value is not None:
            if not isinstance(value, Mapping) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
                raise ValueError(f"{label} run has invalid component versions")


def _valid_list_metric(name: str, value: list[Any]) -> bool:
    if name == "acceptance":
        return all(
            isinstance(item, Mapping)
            and isinstance(item.get("id"), str)
            and bool(item["id"].strip())
            and isinstance(item.get("passed"), bool)
            for item in value
        )
    return all(isinstance(item, (str, Mapping)) for item in value)


def _compare_measurements(
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    unit: str,
) -> dict[str, Any]:
    output = {
        "status": "incomparable",
        "reason": None,
        "before": before.get("value") if isinstance(before, Mapping) else None,
        "after": after.get("value") if isinstance(after, Mapping) else None,
        "delta": None,
    }
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        output["reason"] = "measurement_missing"
        return output
    before_source, after_source = before.get("source"), after.get("source")
    if not _valid_source(before_source) or not _valid_source(after_source):
        output["reason"] = "source_missing_or_invalid"
        return output
    before_value, after_value = before.get("value"), after.get("value")
    if before_value is None or after_value is None or before_source["kind"] == "unavailable" or after_source["kind"] == "unavailable":
        output["reason"] = "value_unavailable"
        return output
    if (
        before_source["kind"] != after_source["kind"]
        or before_source.get("unit", unit) != after_source.get("unit", unit)
        or before_source.get("reference") != after_source.get("reference")
    ):
        output["reason"] = "source_incompatible"
        return output

    output["status"] = "compared"
    output["reason"] = None
    output["unit"] = before_source.get("unit", unit)
    output["changed"] = before_value != after_value
    if _is_number(before_value) and _is_number(after_value):
        output["delta"] = after_value - before_value
    return output


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``run`` emits a result and ``compare`` emits a diff."""

    parser = argparse.ArgumentParser(description="Run an offline Inonu baseline fixture or compare saved results.")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="record one local fixture execution")
    run_parser.add_argument("fixture", help="path to a baseline fixture JSON file")
    run_parser.add_argument("--execution-id", help="caller-provided execution identifier")
    compare_parser = commands.add_parser("compare", help="compare two saved result JSON files")
    compare_parser.add_argument("before", help="earlier result JSON file")
    compare_parser.add_argument("after", help="later result JSON file")
    compare_parser.add_argument(
        "--max-regression",
        type=float,
        help="fail when a gated metric rises beyond this ratio (0.10 allows a 10 percent increase)",
    )
    args = parser.parse_args(argv)

    code = 0
    try:
        if args.command == "run":
            result = run_fixture(args.fixture, execution_id=args.execution_id)
        else:
            strict = args.max_regression is not None
            before = _load_fixture(args.before, strict=strict)
            after = _load_fixture(args.after, strict=strict)
            result = compare_runs(before, after)
            if args.max_regression is not None:
                gate = gate_comparison(before, after, result, args.max_regression)
                result["gate"] = gate
                code = GATE_EXIT_CODES[gate["status"]]
    except (OSError, ValueError) as exc:
        print(f"baseline: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":  # pragma: no cover - exercised as a command by users
    raise SystemExit(main())
