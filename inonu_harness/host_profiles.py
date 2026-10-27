"""Preview and install only Inonu's native host skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile
from typing import Any

from . import __version__


_PROFILE = "inonu-harness"
_OWNER = "inonu-harness.host-profile"
_METADATA = ".inonu-harness.json"
_SKILL = "SKILL.md"
_HASH = re.compile(r"^[0-9a-f]{64}$")


def _bash_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def render_runner_command(runner_path: str | Path, host: str, command: str = "") -> str:
    """Render one shell-safe command prefix for a host's native skill."""
    raw = str(runner_path)
    windows_path = PureWindowsPath(raw)
    if host == "codex" and windows_path.is_absolute():
        quoted = "'" + raw.replace("'", "''") + "'"
        prefix = f"& python {quoted}"
    else:
        normalized = windows_path.as_posix() if windows_path.is_absolute() else Path(raw).as_posix()
        prefix = f"python {_bash_quote(normalized)}"
    return f"{prefix} {command}" if command else prefix


def _source_skill(repository: Path, host: str) -> bytes:
    source_path = repository / "skills" / _PROFILE / _SKILL
    content = source_path.read_text(encoding="utf-8")
    runner = (repository / "scripts" / "inonu.py").resolve()
    content = content.replace('python "${CLAUDE_PLUGIN_ROOT}/scripts/inonu.py"', render_runner_command(runner, host))
    link_pattern = re.compile(r"\]\((\.\./\.\./docs/[^)]+)\)")

    def resolve_doc(match: re.Match[str]) -> str:
        document = (source_path.parent / match.group(1)).resolve()
        if not document.is_file() or not document.is_relative_to(repository.resolve()):
            raise ValueError("source skill contains an unavailable documentation link")
        return f"]({document.as_uri()})"

    content = link_pattern.sub(resolve_doc, content)
    return content.encode("utf-8")


def _metadata(skill: bytes, previous_hash: str | None = None) -> bytes:
    value: dict[str, Any] = {
        "owner": _OWNER,
        "schema_version": 1,
        "version": __version__,
        "skill_sha256": hashlib.sha256(skill).hexdigest(),
    }
    if previous_hash:
        value["previous_sha256"] = previous_hash
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read_metadata(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            return None
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(value, dict)
        or value.get("owner") != _OWNER
        or value.get("schema_version") != 1
        or not isinstance(value.get("version"), str)
        or not isinstance(value.get("skill_sha256"), str)
        or not _HASH.fullmatch(value["skill_sha256"])
    ):
        return None
    previous = value.get("previous_sha256")
    if previous is not None and (not isinstance(previous, str) or not _HASH.fullmatch(previous)):
        return None
    return value


def _target(home: Path, host: str) -> Path:
    parent = ".agents" if host == "codex" else ".claude"
    return home / parent / "skills" / _PROFILE


def _preflight(home: Path, host: str, skill: bytes) -> dict[str, Any]:
    directory = _target(home, host)
    current = home
    for part in directory.relative_to(home).parts:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            return {"host": host, "directory": directory, "state": "conflict"}

    skill_path = directory / _SKILL
    metadata_path = directory / _METADATA
    if skill_path.is_symlink() or metadata_path.is_symlink() or skill_path.is_dir() or metadata_path.is_dir():
        return {"host": host, "directory": directory, "state": "conflict"}
    if (skill_path.exists() and not skill_path.is_file()) or (metadata_path.exists() and not metadata_path.is_file()):
        return {"host": host, "directory": directory, "state": "conflict"}

    desired_hash = hashlib.sha256(skill).hexdigest()
    skill_exists, metadata_exists = skill_path.is_file(), metadata_path.is_file()
    metadata = _read_metadata(metadata_path) if metadata_exists else None
    if metadata_exists and metadata is None:
        return {"host": host, "directory": directory, "state": "conflict"}
    if skill_exists and not metadata_exists:
        return {"host": host, "directory": directory, "state": "conflict"}
    current_hash = _file_hash(skill_path) if skill_exists else None
    if current_hash and metadata and current_hash not in {metadata["skill_sha256"], metadata.get("previous_sha256")}:
        return {"host": host, "directory": directory, "state": "conflict"}

    unchanged = bool(
        skill_exists and metadata
        and current_hash == desired_hash
        and metadata["skill_sha256"] == desired_hash
        and metadata["version"] == __version__
        and not metadata.get("previous_sha256")
    )
    return {
        "host": host,
        "directory": directory,
        "skill": skill,
        "desired_hash": desired_hash,
        "current_hash": current_hash,
        "metadata": metadata,
        "state": "unchanged" if unchanged else "ready",
    }


def _atomic_write(path: Path, content: bytes) -> None:
    handle, temporary = tempfile.mkstemp(prefix=".inonu-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _apply(plan: dict[str, Any]) -> None:
    directory = plan["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    skill_path, metadata_path = directory / _SKILL, directory / _METADATA
    skill = plan["skill"]
    previous_hash = plan["current_hash"]
    transitioning = bool(previous_hash and previous_hash != plan["desired_hash"])
    _atomic_write(metadata_path, _metadata(skill, previous_hash if transitioning else None))
    _atomic_write(skill_path, skill)
    if transitioning:
        _atomic_write(metadata_path, _metadata(skill))


def _status(plan: dict[str, Any], applying: bool) -> dict[str, str]:
    if plan["state"] == "conflict":
        skill_status = ownership_status = "conflict"
    elif plan["state"] == "unchanged":
        skill_status = ownership_status = "unchanged"
    elif applying:
        old_hash = plan["current_hash"]
        skill_status = "installed" if old_hash is None else "updated"
        ownership_status = "installed" if plan["metadata"] is None else "updated"
    else:
        skill_status = "would_install" if plan["current_hash"] is None else "would_update"
        ownership_status = "would_install" if plan["metadata"] is None else "would_update"
    return {"skill": skill_status, "ownership": ownership_status}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview or install Inonu native host skills.")
    parser.add_argument("--host", choices=("codex", "claude", "both"), default="both")
    parser.add_argument("--home", type=Path, help="home directory (useful for isolated installations)")
    parser.add_argument("--apply", action="store_true", help="write the selected native skill profiles")
    args = parser.parse_args(argv)
    try:
        home = (args.home or Path.home()).expanduser().resolve()
        hosts = ("codex", "claude") if args.host == "both" else (args.host,)
        repository = Path(__file__).resolve().parents[1]
        plans = [_preflight(home, host, _source_skill(repository, host)) for host in hosts]
    except (OSError, RuntimeError, UnicodeError, ValueError):
        print("inonu-harness: selected profile could not be inspected", file=sys.stderr)
        return 2

    if any(plan["state"] == "conflict" for plan in plans):
        statuses = {plan["host"]: _status(plan, False) for plan in plans}
        print(json.dumps({"version": __version__, "mode": "apply" if args.apply else "preview", "hosts": statuses}, sort_keys=True))
        print("inonu-harness: selected profile has unmanaged or modified files; no files changed", file=sys.stderr)
        return 2
    result = {
        "version": __version__,
        "mode": "apply" if args.apply else "preview",
        "hosts": {plan["host"]: _status(plan, False) for plan in plans},
    }
    if args.apply:
        try:
            for plan in plans:
                if plan["state"] != "unchanged":
                    _apply(plan)
        except OSError:
            print("inonu-harness: profile installation failed; local files may need inspection", file=sys.stderr)
            return 2
        result["hosts"] = {plan["host"]: _status(plan, True) for plan in plans}
    print(json.dumps(result, sort_keys=True))
    return 0


__all__ = ["main", "render_runner_command"]
