"""Verifier-gated loop runner: check exit codes decide success, limits are mandatory, no model calls."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import time
from typing import Any

_GIT_TIMEOUT_SECONDS = 10
_TASKKILL_TIMEOUT_SECONDS = 10
_UNTRACKED_HASH_LIMIT = 16 * 1024 * 1024  # larger untracked files are fingerprinted by size and mtime
_LIMIT_CAPS = {
    "max_iterations": 1000,
    "iteration_timeout_seconds": 86400,
    "total_timeout_seconds": 604800,
    "stagnation_iterations": 100,
}
_REQUIRED_KEYS = {"step", "checks", "limits", "log"}
_SPEC_KEYS = _REQUIRED_KEYS | {"cwd"}


@dataclass(frozen=True)
class Check:
    id: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class LoopSpec:
    step: tuple[str, ...]
    checks: tuple[Check, ...]
    max_iterations: int
    iteration_timeout_seconds: int
    total_timeout_seconds: int
    stagnation_iterations: int
    log: Path
    cwd: Path


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValueError(f"{label} must be a non-empty string without NUL")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(f"{label} must be valid Unicode text") from None
    return value


def _argv(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty argv list")
    return tuple(_text(item, label) for item in value)


def _path(value: Any, base: Path, label: str) -> Path:
    path = Path(_text(value, label))
    return path if path.is_absolute() else base / path


def parse_spec(data: Any, base: Path) -> LoopSpec:
    """Validate spec JSON already read with duplicate keys rejected; relative log and cwd resolve against base."""
    if not isinstance(data, dict) or not _REQUIRED_KEYS <= set(data) <= _SPEC_KEYS:
        raise ValueError("spec needs step, checks, limits and log, with optional cwd and no other keys")
    checks = data["checks"]
    if not isinstance(checks, list) or not checks:
        raise ValueError("checks must be a non-empty list")
    parsed: list[Check] = []
    for item in checks:
        if not isinstance(item, dict) or set(item) != {"id", "argv"}:
            raise ValueError("each check must be an object with exactly id and argv")
        parsed.append(Check(_text(item["id"], "check id"), _argv(item["argv"], "check argv")))
    if len({check.id for check in parsed}) != len(parsed):
        raise ValueError("check ids must be unique")
    limits = data["limits"]
    if not isinstance(limits, dict) or set(limits) != set(_LIMIT_CAPS):
        raise ValueError("limits must contain exactly " + ", ".join(_LIMIT_CAPS))
    for name, cap in _LIMIT_CAPS.items():
        value = limits[name]
        if type(value) is not int or not 1 <= value <= cap:  # bool and float are not counts
            raise ValueError(f"limits.{name} must be an integer from 1 to {cap}")
    cwd = base
    if "cwd" in data:
        cwd = _path(data["cwd"], base, "cwd")
        if not cwd.is_dir():
            raise ValueError("cwd must be an existing directory")
    return LoopSpec(
        step=_argv(data["step"], "step"),
        checks=tuple(parsed),
        max_iterations=limits["max_iterations"],
        iteration_timeout_seconds=limits["iteration_timeout_seconds"],
        total_timeout_seconds=limits["total_timeout_seconds"],
        stagnation_iterations=limits["stagnation_iterations"],
        log=_path(data["log"], base, "log"),
        cwd=cwd,
    )


_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_PROCESS_SET_QUOTA_AND_TERMINATE = 0x0100 | 0x0001
_windows_api: Any = None


def _kernel32() -> Any:
    """kernel32 with the handle-sized signatures a Job Object needs (loaded only on Windows)."""
    global _windows_api
    if _windows_api is None:
        import ctypes
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters), ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.CreateJobObjectW.restype = wintypes.HANDLE
        api.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.ExtendedLimits, api.byref, api.sizeof = ExtendedLimits, ctypes.byref, ctypes.sizeof
        _windows_api = api
    return _windows_api


def _job_for(process: subprocess.Popen) -> Any:
    """A kill-on-close Job Object holding the process, or None when Windows refuses (taskkill is the fallback)."""
    try:
        api = _kernel32()
        job = api.CreateJobObjectW(None, None)
        if not job:
            return None
        info = api.ExtendedLimits()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        handle = api.OpenProcess(_PROCESS_SET_QUOTA_AND_TERMINATE, False, process.pid)
        ok = bool(handle) and api.SetInformationJobObject(
            job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, api.byref(info), api.sizeof(info)
        ) and api.AssignProcessToJobObject(job, handle)
        if handle:
            api.CloseHandle(handle)
        if not ok:
            api.CloseHandle(job)
            return None
        return job
    except (OSError, AttributeError, ValueError):
        return None


class _ProcessTree:
    """Everything a command starts: one Job Object on Windows, one session and process group on POSIX.

    shortcut: a descendant spawned in the instant before the Windows job is assigned can escape, upgrade to a suspended start.
    """

    def __init__(self, process: subprocess.Popen) -> None:
        self.process = process
        self.job = _job_for(process) if os.name == "nt" else None

    def kill(self) -> None:
        with suppress(OSError, subprocess.SubprocessError):
            if self.job is not None:
                _kernel32().TerminateJobObject(self.job, 1)
            elif os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    capture_output=True, check=False, timeout=_TASKKILL_TIMEOUT_SECONDS,
                )
            else:
                os.killpg(self.process.pid, signal.SIGKILL)  # the session leader's group holds the whole tree
        with suppress(OSError):
            self.process.kill()  # covers a failed tree kill so wait() cannot hang on a live child
        self.process.wait()
        if self.job is not None:
            with suppress(OSError):
                _kernel32().CloseHandle(self.job)
            self.job = None


def _run_process(argv: tuple[str, ...] | list[str], cwd: Path, timeout: float) -> tuple[int | None, bool, bool]:
    """Run argv without a shell and discard its output; returns (exit_code, timed_out, started).

    The whole process tree dies when the command ends, on timeout and on an interrupt: nothing it started outlives it.
    """
    group: dict[str, Any] = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    )
    try:
        process = subprocess.Popen(
            list(argv), cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **group,
        )
    except OSError:
        return None, False, False
    tree = _ProcessTree(process)
    try:
        exit_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        tree.kill()
        return None, True, True
    except BaseException:  # Ctrl+C reaches the runner only: the child tree must not outlive it
        tree.kill()
        raise
    tree.kill()
    return exit_code, False, True


def _execute(
    argv: tuple[str, ...], spec: LoopSpec, deadline: float, clock: Callable[[], float], runner: Callable[..., Any],
) -> tuple[int | None, bool, bool, bool, float]:
    """(exit_code, timed_out, started, ran, seconds); a spent budget means the command never ran."""
    remaining = deadline - clock()
    if remaining <= 0:
        return None, False, True, False, 0.0
    began = clock()
    exit_code, timed_out, started = runner(argv, spec.cwd, min(spec.iteration_timeout_seconds, remaining))
    return exit_code, timed_out, started, True, round(clock() - began, 3)


def _has_git_entry(cwd: Path) -> bool:
    return any((directory / ".git").exists() for directory in (cwd, *cwd.parents))


def _file_fingerprint(path: Path) -> bytes:
    try:
        info = path.lstat()
        if stat.S_ISREG(info.st_mode) and info.st_size <= _UNTRACKED_HASH_LIMIT:
            return hashlib.sha256(path.read_bytes()).digest()
        return f"{info.st_size}:{info.st_mtime_ns}".encode("ascii")
    except OSError:
        return b"unreadable"


def _tree_hash(spec: LoopSpec, deadline: float, clock: Callable[[], float]) -> str | None:
    """Digest of HEAD, the binary diff and the content of untracked files, minus the loop log.

    "no-git" when no .git entry exists at or above the working directory; None (unknown, which resets the stagnation
    streak) when git fails or stalls. Ignored files are not part of the digest.
    """
    if not _has_git_entry(spec.cwd):
        return "no-git"

    def git(*args: str) -> subprocess.CompletedProcess[bytes] | None:
        limit = min(_GIT_TIMEOUT_SECONDS, spec.iteration_timeout_seconds, deadline - clock())
        if limit <= 0:
            return None
        try:
            return subprocess.run(
                ["git", *args], cwd=spec.cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=limit, check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

    try:
        log_relative = spec.log.resolve().relative_to(spec.cwd.resolve()).as_posix()
    except ValueError:
        log_relative = None
    pathspec = ["--", ".", f":(exclude,literal){log_relative}"] if log_relative else []
    inside = git("rev-parse", "--is-inside-work-tree")
    head = git("rev-parse", "--verify", "-q", "HEAD")
    if inside is None or inside.returncode != 0 or inside.stdout.strip() != b"true":
        return None
    if head is None or head.returncode not in (0, 1):  # 1: a repository without a commit yet
        return None
    diffs = (
        [git("diff", "HEAD", "--binary", *pathspec)] if head.returncode == 0
        else [git("diff", "--cached", "--binary", *pathspec), git("diff", "--binary", *pathspec)]
    )
    untracked = git("ls-files", "--others", "--exclude-standard", "-z")
    if any(done is None or done.returncode != 0 for done in (*diffs, untracked)):
        return None
    digest = hashlib.sha256()
    for part in (head.stdout, *(done.stdout for done in diffs)):
        digest.update(f"{len(part)}:".encode("ascii") + part)  # length prefix keeps the parts unambiguous
    for name in sorted(item for item in untracked.stdout.split(b"\0") if item):
        text = os.fsdecode(name)
        if text != log_relative:
            digest.update(name + b"\0" + _file_fingerprint(spec.cwd / text) + b"\n")
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def run_loop(
    spec: LoopSpec,
    *,
    clock: Callable[[], float] = time.monotonic,
    runner: Callable[..., tuple[int | None, bool, bool]] = _run_process,
) -> dict[str, Any]:
    """Run the checks (iteration 0), then step and checks per iteration until a stop; one JSONL record each."""
    deadline = clock() + spec.total_timeout_seconds
    passes = {check.id: False for check in spec.checks}
    regressions: list[dict[str, Any]] = []
    previous: tuple[str, str] | None = None
    streak = 0
    iteration = 0
    spec.log.parent.mkdir(parents=True, exist_ok=True)
    with spec.log.open("a", encoding="utf-8", newline="\n") as log:
        while True:
            started_at = _utc_now()
            step = None
            if iteration:
                exit_code, timed_out, _, ran, duration = _execute(spec.step, spec, deadline, clock, runner)
                step = {"exit_code": exit_code, "timed_out": timed_out, "not_run": not ran, "duration_seconds": duration}
            checks: list[dict[str, Any]] = []
            newly: list[str] = []
            regressed: list[str] = []
            unstartable = False
            for check in spec.checks:
                exit_code, timed_out, started, ran, _ = _execute(check.argv, spec, deadline, clock, runner)
                unstartable = unstartable or not started
                now = ran and exit_code == 0
                if ran:  # a check the spent budget never ran says nothing about regressions
                    if now and not passes[check.id]:
                        newly.append(check.id)
                    elif passes[check.id] and not now:
                        regressed.append(check.id)
                        regressions.append({"iteration": iteration, "id": check.id})
                    passes[check.id] = now
                checks.append(
                    {"id": check.id, "exit_code": exit_code, "timed_out": timed_out, "not_run": not ran, "passes": now}
                )
            tree = _tree_hash(spec, deadline, clock)
            failing = sorted((row["id"], row["exit_code"], row["timed_out"]) for row in checks if not row["passes"])
            signature = hashlib.sha256(json.dumps(failing).encode("utf-8")).hexdigest()
            state = None if tree is None else (signature, tree)
            # Streak of step iterations whose state equals the previous one; iteration 0 is the first reference.
            streak = streak + 1 if iteration and state is not None and state == previous else 0
            previous = state
            if all(row["passes"] for row in checks):
                status: str | None = "verified_done"
            elif unstartable:
                status = "verifier_error"
            elif clock() >= deadline:
                status = "wall_clock"
            elif iteration >= spec.max_iterations:
                status = "max_iterations"
            elif streak >= spec.stagnation_iterations:
                status = "stagnation"
            else:
                status = None
            record = {
                "iteration": iteration,
                "started_at": started_at,
                "ended_at": _utc_now(),
                "step": step,
                "checks": checks,
                "newly_passing": newly,
                "regressed": regressed,
                "failing_signature": signature,
                "tree_hash": tree,
                "decision": "stop" if status else "continue",
                "stop_reason": status,
            }
            log.write(json.dumps(record, sort_keys=True) + "\n")
            log.flush()
            if status is not None:
                return {
                    "status": status,
                    "iterations": iteration,
                    "passes": passes,
                    "regressions": regressions,
                    "log": str(spec.log),
                }
            iteration += 1
