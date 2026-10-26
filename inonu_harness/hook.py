"""Stop hook: run the project's verifier config, and only the exact bytes the owner trusted.

A repository can ship .inonu/verify.json, so nothing in it runs until `hook trust --yes` records its SHA-256 for the
resolved path. Checks run as argv lists with no shell, and a failing check blocks the stop with exit 2. Nothing here
installs the hook.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

from .loop import Check, _ProcessTree, _argv, _text
from .secret_scan import scan

CONFIG_PATH = Path(".inonu") / "verify.json"
TRUST_PATH = Path(".inonu-harness") / "hook-trust.json"
STATE_DIRECTORY = "inonu-hook-state"
CONFIG_LIMIT_BYTES = 64 * 1024
TAIL_BYTES = 1500
SCAN_BYTES = 64 * 1024  # the credential scan sees this much of the end of the output, not only the shown tail
OUTPUT_LIMIT_BYTES = 16 * 1024 * 1024  # a check that writes more than this is stopped
_CONTROL = {code: chr(92) + "x" + format(code, "02x") for code in (*range(0, 9), 11, 12, *range(14, 32), 127)}
MESSAGE_LIMIT = 4000
MAX_CHECKS = 20
MAX_TIMEOUT_SECONDS = 600
MAX_CONSECUTIVE_BLOCKS = 20
_CONFIG_KEYS = frozenset({"checks", "timeout_seconds", "max_consecutive_blocks"})
_REVIEW = "python -m inonu_harness hook trust --root PROJECT"
_TRUST_BROKEN = "the trust file cannot be read or parsed; fix it or move it aside"
_TRUNCATED = "\n[message truncated]\n"
_UNEXPECTED = "inonu hook: unexpected error\n"


@dataclass(frozen=True)
class VerifierConfig:
    checks: tuple[Check, ...]
    timeout_seconds: int
    max_consecutive_blocks: int


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _config_key(project: Path, config_path: Path) -> str:
    """The trust key for a project's config, refusing a config that is a link to somewhere else."""
    expected = project.resolve() / CONFIG_PATH
    if os.path.normcase(str(config_path.resolve())) != os.path.normcase(str(expected)):
        raise ValueError("the verifier config must be a file inside the project, not a link to another place")
    return str(expected)


def _read_config(path: Path) -> bytes | None:
    """The config bytes, read at most one byte past the limit; None when the file does not exist."""
    try:
        with path.open("rb") as handle:
            raw = handle.read(CONFIG_LIMIT_BYTES + 1)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError("the verifier config cannot be read") from exc
    if len(raw) > CONFIG_LIMIT_BYTES:
        raise ValueError("the verifier config is larger than 64 KiB")
    return raw


def _config_from(data: Any) -> VerifierConfig:
    if not isinstance(data, dict) or set(data) != _CONFIG_KEYS:
        raise ValueError("it needs exactly checks, timeout_seconds and max_consecutive_blocks")
    checks = data["checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= MAX_CHECKS:
        raise ValueError(f"checks must hold 1 to {MAX_CHECKS} entries")
    parsed: list[Check] = []
    for item in checks:
        if not isinstance(item, dict) or set(item) != {"id", "argv"}:
            raise ValueError("each check must be an object with exactly id and argv")
        parsed.append(Check(_text(item["id"], "check id"), _argv(item["argv"], "check argv")))
    if len({check.id for check in parsed}) != len(parsed):
        raise ValueError("check ids must be unique")
    timeout = data["timeout_seconds"]
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT_SECONDS:  # a bool is not a count
        raise ValueError(f"timeout_seconds must be an integer from 1 to {MAX_TIMEOUT_SECONDS}")
    blocks = data["max_consecutive_blocks"]
    if type(blocks) is not int or not 1 <= blocks <= MAX_CONSECUTIVE_BLOCKS:
        raise ValueError(f"max_consecutive_blocks must be an integer from 1 to {MAX_CONSECUTIVE_BLOCKS}")
    return VerifierConfig(tuple(parsed), timeout, blocks)


def parse_config(raw: bytes) -> VerifierConfig:
    """Strict parse of the config bytes; each problem is a ValueError that says what is wrong, never the content."""
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (ValueError, RecursionError) as exc:  # UnicodeDecodeError is a ValueError too
        raise ValueError("the verifier config is invalid: not strict UTF-8 JSON") from exc
    try:
        return _config_from(data)
    except ValueError as exc:
        raise ValueError(f"the verifier config is invalid: {exc}") from None


def _read_trust(path: Path) -> dict[str, str]:
    """Trusted digests keyed by resolved config path. A missing file trusts nothing; a broken one is a ValueError."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError) as exc:
        raise ValueError(_TRUST_BROKEN) from exc
    try:
        data = json.loads(text, object_pairs_hook=_unique_json_object)
    except (ValueError, RecursionError) as exc:
        raise ValueError(_TRUST_BROKEN) from exc
    if not isinstance(data, dict) or set(data) != {"schema_version", "trusted"}:
        raise ValueError(_TRUST_BROKEN)
    version, trusted = data["schema_version"], data["trusted"]
    if (type(version) is not int or version != 1 or not isinstance(trusted, dict)
            or not all(isinstance(key, str) and isinstance(value, str) for key, value in trusted.items())):
        raise ValueError(_TRUST_BROKEN)
    return trusted


def _write_json_atomic(path: Path, value: Any) -> None:
    """Replace path with value as JSON through a temporary file in the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(temporary)
        raise


def _store_trust(path: Path, trusted: dict[str, str]) -> None:
    try:
        _write_json_atomic(path, {"schema_version": 1, "trusted": trusted})
    except OSError as exc:
        raise ValueError("the trust file could not be written") from exc


def _trust_file(home: Path | None) -> Path:
    return (Path.home() if home is None else home) / TRUST_PATH


def _command_project(root: Path | None) -> Path:
    return Path.cwd() if root is None else root


def _stop_project(data: dict[str, Any], environ: Mapping[str, str], process_cwd: Path) -> Path:
    """$CLAUDE_PROJECT_DIR, else the hook's cwd when it names a directory, else the process directory."""
    named = environ.get("CLAUDE_PROJECT_DIR")
    if named:
        return Path(named)
    cwd = data.get("cwd")
    if isinstance(cwd, str) and Path(cwd).is_dir():
        return Path(cwd)
    return process_cwd


def _hook_input(text: str) -> dict[str, Any]:
    """The hook's JSON object; an empty, invalid or non-object body reads as {} so the hook still runs."""
    try:
        data = json.loads(text, object_pairs_hook=_unique_json_object)
    except (ValueError, RecursionError):
        return {}
    return data if isinstance(data, dict) else {}


def _require_trust(key: str, digest: str, trust_path: Path) -> None:
    trusted = _read_trust(trust_path)
    if key not in trusted:
        raise ValueError(
            f"the verifier config is not trusted, so no check ran; review it with `{_REVIEW}`, then add --yes to trust it"
        )
    if trusted[key] != digest:
        raise ValueError(
            "the verifier config changed since it was trusted, so no check ran; "
            f"review it with `{_REVIEW}`, then add --yes to trust the new version"
        )


def _state_path(session_id: str, config_key: str) -> Path:
    digest = hashlib.sha256((session_id + config_key).encode("utf-8", "backslashreplace")).hexdigest()
    return Path(tempfile.gettempdir()) / STATE_DIRECTORY / f"{digest[:16]}.json"


def _read_blocks(path: Path) -> int:
    """Consecutive blocks so far; a missing, unreadable or malformed counter counts as zero."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))["consecutive_blocks"]
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        return 0
    return value if type(value) is int and value >= 0 else 0


def _write_blocks(path: Path, count: int) -> None:
    try:
        _write_json_atomic(path, {"consecutive_blocks": count})
    except OSError as exc:  # without a stored count the limit cannot be enforced, so never block
        raise ValueError(
            "the block counter cannot be stored, so the block limit cannot be enforced; this stop is allowed"
        ) from exc


def _clear_blocks(path: Path) -> None:
    with suppress(OSError):
        path.unlink()


def _run_check(check: Check, cwd: Path, timeout: float) -> tuple[str | None, str]:
    """Run one check with no shell, stdin closed and output captured.

    Returns (reason, text to show). The reason is None when the check exited 0, `exit N`, `timed out` or
    `output limit`. The text is the last TAIL_BYTES of output, or a note when the credential scan matched anywhere in
    the last SCAN_BYTES, with control characters escaped.
    """
    group: dict[str, Any] = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    )
    with tempfile.TemporaryFile() as output:
        try:
            process = subprocess.Popen(
                list(check.argv), cwd=cwd, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, **group,
            )
        except OSError as exc:
            raise ValueError(f"check {json.dumps(check.id)} could not be started") from exc
        tree = _ProcessTree(process)
        reason: str | None = None
        ended = time.monotonic() + timeout
        try:
            while True:
                left = ended - time.monotonic()
                if left <= 0:
                    reason = "timed out"
                    break
                try:
                    exit_code = process.wait(timeout=min(0.25, left))
                except subprocess.TimeoutExpired:
                    if os.fstat(output.fileno()).st_size > OUTPUT_LIMIT_BYTES:
                        reason = "output limit"
                        break
                    continue
                reason = None if exit_code == 0 else f"exit {exit_code}"
                break
        except BaseException:  # Ctrl+C reaches the hook only: the check's tree must not outlive it
            tree.kill()
            raise
        tree.kill()  # ends whatever the check left running, on a timeout as well as on a normal exit
        output.seek(0, os.SEEK_END)
        size = output.tell()
        output.seek(max(0, size - SCAN_BYTES))
        window = output.read().decode("utf-8", errors="replace")
        return reason, _shown(window)


def _shown(window: str) -> str:
    """What the message may show of the output: the tail, or a note naming only the rules that matched anywhere in the
    scanned window, so matched text (or a visible piece of it) never reaches the message."""
    rules = sorted({finding["rule"] for finding in scan({"output": window})})
    if rules:
        return f"[output withheld: credential-like text matched {', '.join(rules)}]"
    return window[-TAIL_BYTES:].translate(_CONTROL).rstrip()


def _block_message(attempt: int, limit: int, failures: list[tuple[Check, str, str]]) -> str:
    listed = "; ".join(f"{json.dumps(check.id)} {reason}" for check, reason, _ in failures)
    lines = [
        f"inonu hook: attempt {attempt} of {limit} blocked the stop; failing checks: {listed}.",
        "Fix the failing checks and try again.",
    ]
    for check, _, tail in failures:
        lines.append(f"--- {json.dumps(check.id)} output, last {TAIL_BYTES} bytes ---")
        lines.append(tail or "(no output)")
    message = "\n".join(lines) + "\n"
    if len(message) > MESSAGE_LIMIT:
        message = message[: MESSAGE_LIMIT - len(_TRUNCATED)] + _TRUNCATED
    return message


def _stop(
    stdin_text: str, environ: Mapping[str, str], home: Path | None, process_cwd: Path | None,
    clock: Callable[[], float],
) -> tuple[int, str]:
    data = _hook_input(stdin_text)
    project = _stop_project(data, environ, Path.cwd() if process_cwd is None else process_cwd)
    config_path = project / CONFIG_PATH
    raw = _read_config(config_path)
    if raw is None:
        return 0, ""
    key = _config_key(project, config_path)
    _require_trust(key, _digest(raw), _trust_file(home))
    config = parse_config(raw)
    session = data.get("session_id")
    state = _state_path(session if isinstance(session, str) else "", key)
    deadline = clock() + config.timeout_seconds  # one budget shared by every check
    failures: list[tuple[Check, str, str]] = []
    for check in config.checks:
        remaining = deadline - clock()
        if remaining <= 0:  # the budget is spent, so this check never got to finish
            failures.append((check, "timed out", ""))
            continue
        reason, tail = _run_check(check, project, remaining)
        if reason is not None:
            failures.append((check, reason, tail))
    if not failures:
        _clear_blocks(state)
        return 0, ""
    blocks = _read_blocks(state)
    limit = config.max_consecutive_blocks
    if blocks >= limit:
        _clear_blocks(state)
        return 0, (
            f"inonu hook: block limit of {limit} consecutive blocks reached; "
            "allowing this stop and resetting the block counter\n"
        )
    blocks += 1
    _write_blocks(state, blocks)
    return 2, _block_message(blocks, limit, failures)


def run_stop(
    stdin_text: str,
    environ: Mapping[str, str],
    home: Path | None = None,
    *,
    process_cwd: Path | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[int, str]:
    """Exit code and stderr text of one Stop hook run. Nothing is printed here, and no exception escapes."""
    try:
        return _stop(stdin_text, environ, home, process_cwd, clock)
    except ValueError as exc:  # invalid, untrusted or unreadable config: exit 1 is non-blocking
        return 1, f"inonu hook: {exc}\n"
    except (Exception, KeyboardInterrupt):
        return 1, _UNEXPECTED


def _trust(root: Path | None, home: Path | None, yes: bool) -> str:
    config_path = _command_project(root) / CONFIG_PATH
    raw = _read_config(config_path)
    if raw is None:
        raise ValueError("no verifier config at .inonu/verify.json in that project, so there is nothing to trust")
    config = parse_config(raw)
    key = _config_key(_command_project(root), config_path)
    digest = _digest(raw)
    lines = [f"verifier config: {json.dumps(key)}", f"sha256: {digest}", "checks, run in this order with no shell:"]
    lines += [f"  {json.dumps(check.id)}: {json.dumps(list(check.argv))}" for check in config.checks]
    lines.append(f"timeout_seconds: {config.timeout_seconds}; max_consecutive_blocks: {config.max_consecutive_blocks}")
    if not yes:
        return "\n".join([*lines, "not recorded: this preview wrote nothing; add --yes to trust exactly this config"]) + "\n"
    trust_path = _trust_file(home)
    trusted = _read_trust(trust_path)
    trusted[key] = digest
    _store_trust(trust_path, trusted)
    return "\n".join([*lines, "trusted: the digest above is recorded in the trust file"]) + "\n"


def run_trust(root: Path | None, home: Path | None = None, *, yes: bool = False) -> tuple[int, str, str]:
    """(exit code, stdout text, stderr text) for `hook trust`: a preview unless yes records the trust."""
    try:
        return 0, _trust(root, home, yes), ""
    except ValueError as exc:
        return 2, "", f"inonu hook: {exc}\n"
    except (Exception, KeyboardInterrupt):
        return 1, "", _UNEXPECTED


def _untrust(root: Path | None, home: Path | None) -> str:
    key = str(_command_project(root).resolve() / CONFIG_PATH)  # the config may already be deleted
    trust_path = _trust_file(home)
    trusted = _read_trust(trust_path)
    if key not in trusted:
        return "no trust record for this config; nothing was removed\n"
    del trusted[key]
    _store_trust(trust_path, trusted)
    return "untrusted: the trust record for this config was removed\n"


def run_untrust(root: Path | None, home: Path | None = None) -> tuple[int, str, str]:
    """(exit code, stdout text, stderr text) for `hook untrust`."""
    try:
        return 0, _untrust(root, home), ""
    except ValueError as exc:
        return 2, "", f"inonu hook: {exc}\n"
    except (Exception, KeyboardInterrupt):
        return 1, "", _UNEXPECTED
