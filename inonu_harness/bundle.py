"""Read-only plan and status of the Inonu host bundle. Writes nothing."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import tomllib
from typing import Any

from . import __version__, host_profiles

REPOSITORY = Path(__file__).resolve().parents[1]
WORKER_SOURCE = "agents/inonu-worker.md"
MCP_SERVER_IDS = ("codegraph", "headroom", "sequential-thinking")
STOP_HOOK_TIMEOUT_SECONDS = 630  # above the hook's own 600-second cap on timeout_seconds
STOP_HOOK_NOTE = (
    "Runs the project's trusted verifier config on every Stop and can block the stop when a check fails; "
    "no check runs until the owner trusts that config."
)
STOP_HOOK = {
    "hooks": {
        "Stop": [{"hooks": [{
            "type": "command", "command": "python <checkout>/scripts/inonu.py hook stop",
            "timeout": STOP_HOOK_TIMEOUT_SECONDS,
        }]}],
    },
}
_SKILL_STATES = {
    "conflict": "conflict", "unchanged": "current", "would_install": "absent", "would_update": "outdated",
    "unknown": "unknown",
}


def plan_bundle(host: str = "both", home: Path | None = None, repository: Path = REPOSITORY) -> dict[str, Any]:
    hosts = ("codex", "claude") if host == "both" else (host,)
    home = (home or Path.home()).expanduser().resolve()
    skill_source = f"skills/{host_profiles._PROFILE}/{host_profiles._SKILL}"
    items: list[dict[str, Any]] = []
    for name in hosts:
        try:
            skill_status = host_profiles._status(
                host_profiles._preflight(home, name, host_profiles._source_skill(repository, name)), False)
        except OSError:  # a skill file that cannot be read: report it, as for every other host file
            skill_status = {"skill": "unknown", "ownership": "unknown"}
        parent = ".agents" if name == "codex" else ".claude"
        items.append({
            "kind": "skill",
            "host": name,
            "source": skill_source,
            "target": f"~/{parent}/skills/{host_profiles._PROFILE}/{host_profiles._SKILL}",
            "status": skill_status,
            "applied": False,
        })
        if name == "claude":
            items.append({"kind": "worker-agent", "host": name, "source": WORKER_SOURCE,
                          "target": "~/.claude/agents/inonu-worker.md", "applied": False})
            items.append({"kind": "stop-hook", "host": name, "target": "~/.claude/settings.json",
                          "snippet": STOP_HOOK, "note": STOP_HOOK_NOTE, "applied": False,
                          "requires_owner_authorization": True})
        for server in MCP_SERVER_IDS:
            items.append({"kind": "mcp", "host": name, "id": server, "applied": False,
                          "requires_owner_authorization": True, "accessibility": "unknown"})
    return {"schema_version": 1, "mode": "plan", "version": __version__, "hosts": list(hosts), "items": items}


def is_stop_hook_command(command: Any) -> bool:
    """True for a Stop hook command this bundle wrote: the runner path followed by `hook stop`, or the legacy `check`."""
    return isinstance(command, str) and "inonu.py" in command and command.endswith((" hook stop", " check"))


def _worker_state(home: Path, repository: Path) -> str:
    try:
        installed = (home / ".claude" / "agents" / "inonu-worker.md").read_bytes()
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unknown"
    return "current" if installed == (repository / WORKER_SOURCE).read_bytes() else "different"


def _stop_hook_state(home: Path) -> str:
    try:
        settings = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "absent"
    except (OSError, UnicodeError, ValueError, RecursionError):
        return "unknown"
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    stop = hooks.get("Stop") if isinstance(hooks, dict) else None
    for group in stop if isinstance(stop, list) else []:
        commands = group.get("hooks") if isinstance(group, dict) else None
        for hook in commands if isinstance(commands, list) else []:
            command = hook.get("command") if isinstance(hook, dict) else None
            if is_stop_hook_command(command):
                return "present"
    return "absent"


def _mcp_server_ids(home: Path, host: str) -> set[str] | None:
    if host == "claude":
        path, parse, key = home / ".claude.json", json.loads, "mcpServers"
        errors: tuple[type[Exception], ...] = (OSError, UnicodeError, ValueError, RecursionError)
    else:
        path, parse, key = home / ".codex" / "config.toml", tomllib.loads, "mcp_servers"
        errors = (OSError, UnicodeError, ValueError, RecursionError)
    try:
        value = parse(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except errors:
        return None
    if not isinstance(value, dict) or not isinstance(value.get(key, {}), dict):
        return None
    return set(value.get(key, {}))


def status_bundle(host: str = "both", home: Path | None = None, repository: Path = REPOSITORY) -> dict[str, Any]:
    plan = plan_bundle(host, home, repository)
    root = (home or Path.home()).expanduser().resolve()
    items: list[dict[str, Any]] = []
    for item in plan["items"]:
        entry = {key: value for key, value in item.items() if key != "status"}
        if item["kind"] == "skill":
            entry["state"] = _SKILL_STATES[item["status"]["skill"]]
        elif item["kind"] == "worker-agent":
            entry["state"] = _worker_state(root, repository)
        elif item["kind"] == "stop-hook":
            entry["state"] = _stop_hook_state(root)
        else:
            servers = _mcp_server_ids(root, item["host"])
            entry["state"] = "unknown" if servers is None else ("configured" if item["id"] in servers else "absent")
        items.append(entry)
    counts = Counter(entry["state"] for entry in items)
    return {
        "schema_version": 1,
        "mode": "status",
        "version": plan["version"],
        "hosts": plan["hosts"],
        "items": items,
        "summary": dict(sorted(counts.items())),
    }
