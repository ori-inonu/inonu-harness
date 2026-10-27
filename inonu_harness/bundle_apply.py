"""Preview, apply and remove the Inonu host bundle, tracked by an ownership ledger."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tomllib
from typing import Any

from . import __version__, host_profiles
from .bundle import (
    MCP_SERVER_IDS, REPOSITORY, STOP_HOOK_NOTE, STOP_HOOK_TIMEOUT_SECONDS, WORKER_SOURCE, is_stop_hook_command,
    status_bundle,
)

WORKER_ID = "inonu-worker"
STOP_EVENT = "Stop"
_HASH = re.compile(r"[0-9a-f]{64}")
_VERBS = {
    "install": ("installed", "would_install"),
    "update": ("updated", "would_update"),
    "remove": ("removed", "would_remove"),
}
_WRITE_RESULTS = {"installed", "updated", "removed"}
_AS_PREVIEW = {"installed": "would_install", "updated": "would_update", "removed": "would_remove"}
_WINDOWS_SUFFIXES = (".exe", ".cmd", ".bat", ".com")
_LAUNCHERS = {
    "codegraph": ("codegraph", ["mcp", "serve", "--root", ".", "--stdio", "--no-warmup"]),
    "headroom": ("headroom", ["mcp", "serve"]),
    "sequential-thinking": ("npx", ["-y", "@modelcontextprotocol/server-sequential-thinking"]),
}


_UNKNOWN = object()  # a path whose post-write digest is unknown: rollback restores it unconditionally


class _Malformed(Exception):
    """A file that cannot be interpreted safely; the item using it becomes a conflict."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(value: Any) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _key(kind: str, host: str, ident: str) -> str:
    return f"{kind}:{host}:{ident}"


def _fingerprint(path: Path) -> str | None:
    """Digest of a file, None when absent, or a marker that never equals a digest."""
    if path.is_symlink():
        return "symlink"
    try:
        return _sha(path.read_bytes())
    except FileNotFoundError:
        return None
    except OSError:
        return "unreadable"


def _read_shared(path: Path) -> bytes | None:
    if path.is_symlink():
        raise _Malformed
    for ancestor in path.parents:
        if ancestor.exists():
            if not ancestor.is_dir():
                raise _Malformed
            break
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        raise _Malformed from None


def _reject_constant(_: str) -> Any:
    raise _Malformed


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise _Malformed
    return value


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({key for key, _ in pairs}) != len(pairs):
        raise _Malformed  # rewriting would silently drop the earlier value
    return dict(pairs)


def _json_doc(raw: bytes | None) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        value = json.loads(
            raw.decode("utf-8"), parse_constant=_reject_constant, parse_float=_finite_float,
            object_pairs_hook=_unique_pairs,
        )
    except (ValueError, RecursionError):
        raise _Malformed from None
    if not isinstance(value, dict):
        raise _Malformed
    try:
        json.dumps(value, ensure_ascii=False).encode("utf-8")  # a lone surrogate parses but cannot be written back
    except (ValueError, RecursionError):
        raise _Malformed from None
    return value


def _toml_servers(text: str) -> dict[str, Any]:
    try:
        servers = tomllib.loads(text).get("mcp_servers", {})
    except (ValueError, RecursionError):
        raise _Malformed from None
    if not isinstance(servers, dict):
        raise _Malformed
    return servers


def _valid_marker(marker: Any) -> bool:
    """Creation markers name home-relative paths: file:<rel>, dir:<rel> or key:<rel>:<dotted.key>."""
    if not isinstance(marker, str):
        return False
    kind, _, rest = marker.partition(":")
    if kind == "key":
        rest, _, dotted = rest.rpartition(":")
        if not dotted:
            return False
    if kind not in ("file", "dir", "key") or not rest or ":" in rest or chr(92) in rest:
        return False
    return all(part not in ("", ".", "..") for part in rest.split("/"))


def _parse_ledger(raw: bytes | None) -> tuple[dict[str, Any], set[str]]:
    if raw is None:
        return {}, set()
    doc = _json_doc(raw)
    items, created = doc.get("items"), doc.get("created", [])
    if doc.get("schema_version") != 1 or type(doc["schema_version"]) is not int or not isinstance(items, dict) or not isinstance(created, list):
        raise _Malformed
    for entry in items.values():
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str) or not _HASH.fullmatch(entry["sha256"]):
            raise _Malformed
    if not all(_valid_marker(marker) for marker in created):
        raise _Malformed
    return items, set(created)


def _find_executable(name: str) -> str | None:
    """Locate a launcher on PATH. Only absolute entries count: shutil.which would also try the current directory."""
    suffixes = _WINDOWS_SUFFIXES if os.name == "nt" else ("",)
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        directory = Path(entry) if entry else None
        if directory is None or not directory.is_absolute():
            continue
        for suffix in suffixes:
            candidate = directory / f"{name}{suffix}"
            if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
                return str(candidate)
    return None


def _cmd_executable() -> str:
    """An absolute cmd.exe, because the host would resolve a bare "cmd" from its current directory first."""
    comspec = os.environ.get("COMSPEC", "")
    if comspec and Path(comspec).is_absolute() and Path(comspec).is_file():
        return comspec
    return str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32" / "cmd.exe")


def _launcher(server: str) -> dict[str, Any] | None:
    name, args = _LAUNCHERS[server]
    resolved = _find_executable(name)
    if resolved is None:
        return None
    if Path(resolved).suffix.lower() in {".cmd", ".bat"}:
        # An absolute path: cmd.exe resolves a bare name from the current directory first.
        return {"command": _cmd_executable(), "args": ["/c", resolved, *args]}
    return {"command": resolved, "args": list(args)}


def _toml_block(server: str, launch: dict[str, Any]) -> str:
    args = ", ".join(json.dumps(arg) for arg in launch["args"])
    return (
        f"# >>> inonu-harness mcp {server}\n[mcp_servers.{server}]\n"
        f"command = {json.dumps(launch['command'])}\nargs = [{args}]\n"
        f"# <<< inonu-harness mcp {server}\n"
    )


def _find_block(text: str, server: str) -> tuple[int, int] | None:
    name = re.escape(server)
    opening = re.search(rf"# >>> inonu-harness mcp {name}\r?\n", text)
    if opening is None:
        return None
    closing = re.compile(rf"# <<< inonu-harness mcp {name}(?:\r?\n|\Z)").search(text, opening.end())
    if closing is None:
        raise _Malformed
    return opening.start(), closing.end()


def _hook_command(repository: Path) -> str:
    runner = (repository / "scripts" / "inonu.py").resolve()
    return host_profiles.render_runner_command(runner, "claude", "hook stop")


def _is_stop_hook_group(group: Any) -> bool:
    hooks = group.get("hooks") if isinstance(group, dict) else None
    return isinstance(hooks, list) and any(
        isinstance(hook, dict) and is_stop_hook_command(hook.get("command")) for hook in hooks
    )


def _mentions_runner(group: Any) -> bool:
    hooks = group.get("hooks") if isinstance(group, dict) else None
    return isinstance(hooks, list) and any(
        isinstance(hook, dict) and isinstance(hook.get("command"), str) and "inonu.py" in hook["command"]
        for hook in hooks
    )


def _backup_target(home: Path, path: Path, original: bytes) -> Path:
    return home / ".inonu-harness" / "backups" / f"{path.name}.{_sha(original)[:12]}"


def _backup(target: Path, original: bytes) -> bool:
    """Write the backup unless it exists. True when this call created it."""
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    host_profiles._atomic_write(target, original)
    return True


def _remove_skill(run: "_Run", directory: Path, *paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)
    run.prune(directory)


class _Run:
    """One preflight. Nothing reaches disk until write(), which re-checks every fingerprint first."""

    def __init__(self, home: Path, repository: Path, removing: bool, apply: bool) -> None:
        self.home, self.repository, self.removing, self.apply = home, repository, removing, apply
        self.ledger_path = home / ".inonu-harness" / "bundle-ledger.json"
        self.fingerprints: dict[Path, str | None] = {}
        self.originals: dict[Path, bytes | None] = {}
        self.dirty: dict[Path, bytes | None] = {}
        self.actions: list[tuple[list[Path], Callable[[], None]]] = []
        self.created: set[str] = set()
        self.rollback_complete = True
        self._ledger: dict[str, Any] | None = None

    def done(self, verb: str) -> str:
        return _VERBS[verb][0 if self.apply else 1]

    def track(self, path: Path) -> None:
        if path not in self.fingerprints:
            self.fingerprints[path] = _fingerprint(path)

    def before(self, path: Path) -> bytes | None:
        if path not in self.originals:
            data = _read_shared(path)
            self.originals[path] = data
            self.fingerprints.setdefault(path, None if data is None else _sha(data))
        return self.originals[path]

    def current(self, path: Path) -> bytes | None:
        return self.dirty[path] if path in self.dirty else self.before(path)

    def ledger(self) -> dict[str, Any]:
        if self._ledger is None:
            raw = self.before(self.ledger_path)
            self._ledger, self.created = _parse_ledger(raw)
            if raw is None:
                self.mark_dirs(self.ledger_path)
        return self._ledger

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.home).as_posix()

    def mark_dirs(self, path: Path) -> None:
        """Record the missing directories that installing `path` will create, so a removal can take them back."""
        self.ledger()
        parent = path.parent
        while parent != self.home and not parent.exists():
            self.created.add(f"dir:{self._rel(parent)}")
            parent = parent.parent

    def mark_file(self, path: Path) -> None:
        self.mark_dirs(path)
        if self.current(path) is None:
            self.created.add(f"file:{self._rel(path)}")

    def mark_key(self, path: Path, dotted: str) -> None:
        self.ledger()
        self.created.add(f"key:{self._rel(path)}:{dotted}")

    def owns_file(self, path: Path) -> bool:
        return f"file:{self._rel(path)}" in self.created

    def owns_key(self, path: Path, dotted: str) -> bool:
        return f"key:{self._rel(path)}:{dotted}" in self.created

    def prune(self, directory: Path) -> None:
        """Remove empty directories upward, but only those this bundle created."""
        while directory != self.home and f"dir:{self._rel(directory)}" in self.created:
            try:
                directory.rmdir()
            except OSError:
                return
            self.created.discard(f"dir:{self._rel(directory)}")
            directory = directory.parent

    def release_key(self, path: Path, dotted: str) -> None:
        self.created.discard(f"key:{self._rel(path)}:{dotted}")

    def seal_ledger(self) -> None:
        items = self.ledger()
        content = None
        if items:
            doc: dict[str, Any] = {"items": items, "schema_version": 1}
            if self.created:
                doc["created"] = sorted(self.created)
            content = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if content != self.before(self.ledger_path):
            self.dirty[self.ledger_path] = content

    def changed(self) -> bool:
        return any(_fingerprint(path) != digest for path, digest in self.fingerprints.items())

    def write(self) -> str:
        """Write every change, the ledger last. Returns "ok", "changed" (a file differs from its preflight
        fingerprint) or "error". Any other outcome rolls back the files this run already wrote.
        """
        if self.changed():
            return "changed"
        self.ledger()
        snapshots: dict[Path, bytes | None] = {self.ledger_path: self.before(self.ledger_path)}
        written: dict[Path, Any] = {}
        try:
            for paths, _ in self.actions:
                for path in paths:
                    snapshots.setdefault(path, _read_optional(path))
            for path in self.dirty:
                snapshots.setdefault(path, self.originals.get(path))
            for paths, action in self.actions:
                if any(_fingerprint(path) != self.fingerprints[path] for path in paths):
                    return self._abort("changed", written, snapshots)
                for path in paths:
                    written[path] = _UNKNOWN
                action()
                for path in paths:
                    written[path] = _fingerprint(path)
            for path, content in list(self.dirty.items()):
                if not self._put(path, content, written, snapshots):
                    return self._abort("changed", written, snapshots)
            self.seal_ledger()  # after pruning, so the markers describe what is still there
            if self.ledger_path in self.dirty and not self._put(self.ledger_path, self.dirty[self.ledger_path], written, snapshots):
                return self._abort("changed", written, snapshots)
        except OSError:
            return self._abort("error", written, snapshots)
        except BaseException:
            self._abort("error", written, snapshots)  # e.g. KeyboardInterrupt: leave no half state, then re-raise
            raise
        return "ok"

    def _put(self, path: Path, content: bytes | None, written: dict[Path, Any], snapshots: dict[Path, bytes | None]) -> bool:
        if _fingerprint(path) != self.fingerprints[path]:
            return False
        original = self.originals.get(path)
        if content == original:
            return True
        if original is not None and path != self.ledger_path and not self.removing:
            target = _backup_target(self.home, path, original)
            self.mark_dirs(target)
            if _backup(target, original):  # part of the transaction: a rollback takes it back
                snapshots[target] = None
                written[target] = _UNKNOWN
        written[path] = _UNKNOWN
        if content is None:
            path.unlink(missing_ok=True)
            self.created.discard(f"file:{self._rel(path)}")
            self.prune(path.parent)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            host_profiles._atomic_write(path, content)
        written[path] = _fingerprint(path)
        return True

    def _abort(self, status: str, written: dict[Path, Any], snapshots: dict[Path, bytes | None]) -> str:
        """Put back every file this run wrote, unless someone else changed it after the write."""
        for path, expected in reversed(list(written.items())):
            if expected is not _UNKNOWN and _fingerprint(path) != expected:
                self.rollback_complete = False  # an outside edit made since: leave it in place
                continue
            original = snapshots.get(path)
            try:
                if original is None:
                    path.unlink(missing_ok=True)
                    self.prune(path.parent)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    host_profiles._atomic_write(path, original)
            except OSError:
                self.rollback_complete = False
        return status


def _read_optional(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _store_json(run: _Run, path: Path, doc: dict[str, Any]) -> None:
    if not doc and run.owns_file(path):
        run.dirty[path] = None
    else:
        run.dirty[path] = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _store_text(run: _Run, path: Path, text: str) -> None:
    run.dirty[path] = None if text == "" and run.owns_file(path) else text.encode("utf-8")


def _skill(run: _Run, host: str) -> str:
    directory = host_profiles._target(run.home, host)
    skill_path = directory / host_profiles._SKILL
    metadata_path = directory / host_profiles._METADATA
    key = _key("skill", host, host_profiles._PROFILE)
    run.track(skill_path)
    run.track(metadata_path)
    if run.removing:
        return _skill_remove(run, key, directory, skill_path, metadata_path)
    plan = host_profiles._preflight(run.home, host, host_profiles._source_skill(run.repository, host))
    if plan["state"] == "conflict":
        return "conflict"
    if plan["state"] == "ready":
        run.mark_dirs(skill_path)
        run.actions.append(([skill_path, metadata_path], lambda: host_profiles._apply(plan)))
    run.ledger()[key] = {"sha256": plan["desired_hash"]}
    return host_profiles._status(plan, run.apply)["skill"]


def _skill_remove(run: _Run, key: str, directory: Path, skill_path: Path, metadata_path: Path) -> str:
    states = [_fingerprint(skill_path), _fingerprint(metadata_path)]
    if states == [None, None]:
        run.ledger().pop(key, None)
        return "absent"
    if any(state in (None, "symlink", "unreadable") for state in states):
        return "conflict"
    metadata = host_profiles._read_metadata(metadata_path)
    if metadata is None or states[0] != metadata["skill_sha256"]:
        return "conflict"
    run.ledger().pop(key, None)
    run.actions.append(([skill_path, metadata_path], lambda: _remove_skill(run, directory, skill_path, metadata_path)))
    return run.done("remove")


def _worker(run: _Run) -> str:
    path = run.home / ".claude" / "agents" / "inonu-worker.md"
    key = _key("worker-agent", "claude", WORKER_ID)
    source = (run.repository / WORKER_SOURCE).read_bytes()
    current = run.current(path)
    recorded = run.ledger().get(key)
    owned = recorded is not None and current is not None and recorded["sha256"] == _sha(current)
    if run.removing:
        if current is None:
            run.ledger().pop(key, None)
            return "absent"
        if not owned:
            if current == source:  # the user's own copy of our file: leave it
                run.ledger().pop(key, None)
                return "absent"
            return "conflict"
        run.ledger().pop(key)
        run.dirty[path] = None
        return run.done("remove")
    if current == source:
        return "unchanged"
    if current is not None and not owned:
        return "conflict"
    run.mark_dirs(path)
    run.dirty[path] = source
    run.ledger()[key] = {"sha256": _sha(source)}
    return run.done("update" if current is not None else "install")


def _claude_mcp(run: _Run, server: str) -> str:
    key = _key("mcp", "claude", server)
    path = run.home / ".claude.json"
    doc = _json_doc(run.current(path))
    servers = doc.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise _Malformed
    recorded = run.ledger().get(key)
    if run.removing:
        if server not in servers:
            run.ledger().pop(key, None)
            return "absent"
        if recorded is None:
            return "absent"
        if recorded["sha256"] != _canon(servers[server]):
            return "conflict"
        del servers[server]
        if servers or not run.owns_key(path, "mcpServers"):
            doc["mcpServers"] = servers
        else:
            doc.pop("mcpServers", None)
            run.release_key(path, "mcpServers")
        run.ledger().pop(key)
        _store_json(run, path, doc)
        return run.done("remove")
    if server in servers:
        return "unchanged"
    launch = _launcher(server)
    if launch is None:
        return "tool_missing"
    entry = {"type": "stdio", "command": launch["command"], "args": launch["args"], "env": {}}
    if "mcpServers" not in doc:
        run.mark_key(path, "mcpServers")
    run.mark_file(path)
    doc["mcpServers"] = {**servers, server: entry}
    run.ledger()[key] = {"sha256": _canon(entry)}
    _store_json(run, path, doc)
    return run.done("install")


def _codex_mcp(run: _Run, server: str) -> str:
    key = _key("mcp", "codex", server)
    path = run.home / ".codex" / "config.toml"
    raw = run.current(path)
    try:
        text = "" if raw is None else raw.decode("utf-8")
    except UnicodeError:
        raise _Malformed from None
    servers = _toml_servers(text)
    recorded = run.ledger().get(key)
    found = _find_block(text, server)
    if run.removing:
        if found is None:
            if recorded is not None and server in servers:
                return "conflict"
            run.ledger().pop(key, None)
            return "absent"
        if recorded is None:
            return "absent"
        start, end = found
        if recorded["sha256"] != _sha(text[start:end].encode("utf-8")):
            return "conflict"
        remaining = text[:start] + text[end:]
        _toml_servers(remaining)
        run.ledger().pop(key)
        _store_text(run, path, remaining)
        return run.done("remove")
    if server in servers:
        return "unchanged"
    if found is not None:
        return "conflict"
    launch = _launcher(server)
    if launch is None:
        return "tool_missing"
    block = _toml_block(server, launch)
    separator = "" if not text or text.endswith("\n") else "\n"
    updated = text + separator + block
    if _toml_servers(updated).get(server) is None:
        raise _Malformed
    run.ledger()[key] = {"sha256": _sha(block.encode("utf-8"))}
    run.mark_file(path)
    _store_text(run, path, updated)
    return run.done("install")


def _stop_hook(run: _Run, selected: bool) -> str:
    key = _key("stop-hook", "claude", STOP_EVENT)
    if not selected and not (run.removing and key in run.ledger()):
        return "not_selected"
    path = run.home / ".claude" / "settings.json"
    doc = _json_doc(run.current(path))
    hooks = doc.get("hooks", {})
    if not isinstance(hooks, dict):
        raise _Malformed
    stop = hooks.get(STOP_EVENT, [])
    if not isinstance(stop, list):
        raise _Malformed
    recorded = run.ledger().get(key)
    if run.removing:
        matches = [i for i, group in enumerate(stop) if recorded is not None and _canon(group) == recorded["sha256"]]
        if not matches:
            if any(_mentions_runner(group) for group in stop):
                return "conflict"  # recorded but edited, or an Inonu hook this ledger never wrote: delete it by hand
            run.ledger().pop(key, None)
            return "absent"
        del stop[matches[0]]
        if stop or not run.owns_key(path, f"hooks.{STOP_EVENT}"):
            hooks[STOP_EVENT] = stop
        else:
            hooks.pop(STOP_EVENT, None)
            run.release_key(path, f"hooks.{STOP_EVENT}")
        if hooks or not run.owns_key(path, "hooks"):
            doc["hooks"] = hooks
        else:
            doc.pop("hooks", None)
            run.release_key(path, "hooks")
        run.ledger().pop(key)
        _store_json(run, path, doc)
        return run.done("remove")
    group = {"hooks": [{"type": "command", "command": _hook_command(run.repository), "timeout": STOP_HOOK_TIMEOUT_SECONDS}]}
    if group in stop:
        return "unchanged"
    if any(_is_stop_hook_group(existing) for existing in stop):
        return "conflict"  # a hook from another checkout, or an earlier `check` registration: remove it first
    if "hooks" not in doc:
        run.mark_key(path, "hooks")
    if STOP_EVENT not in hooks:
        run.mark_key(path, f"hooks.{STOP_EVENT}")
    run.mark_file(path)
    stop.append(group)
    hooks[STOP_EVENT] = stop
    doc["hooks"] = hooks
    run.ledger()[key] = {"sha256": _canon(group)}
    _store_json(run, path, doc)
    return run.done("install")


def _item(kind: str, host: str, ident: str, target: str, call: Callable[[], str]) -> dict[str, str]:
    try:
        result = call()
    except _Malformed:
        result = "conflict"
    return {"kind": kind, "host": host, "id": ident, "target": target, "result": result}


def _plan(run: _Run, hosts: tuple[str, ...], with_stop_hook: bool) -> list[dict[str, str]]:
    items = []
    for host in hosts:
        parent = ".agents" if host == "codex" else ".claude"
        items.append(_item("skill", host, host_profiles._PROFILE,
                           f"~/{parent}/skills/{host_profiles._PROFILE}", lambda: _skill(run, host)))
        if host == "claude":
            items.append(_item("worker-agent", host, WORKER_ID, "~/.claude/agents/inonu-worker.md",
                               lambda: _worker(run)))
            hook = _item("stop-hook", host, STOP_EVENT, "~/.claude/settings.json", lambda: _stop_hook(run, with_stop_hook))
            hook["note"] = STOP_HOOK_NOTE
            items.append(hook)
        for server in MCP_SERVER_IDS:
            if host == "claude":
                items.append(_item("mcp", host, server, "~/.claude.json", lambda: _claude_mcp(run, server)))
            else:
                items.append(_item("mcp", host, server, "~/.codex/config.toml", lambda: _codex_mcp(run, server)))
    return items


def run_bundle(
    action: str,
    host: str,
    home: Path | None,
    *,
    with_stop_hook: bool = False,
    apply: bool = False,
    repository: Path = REPOSITORY,
) -> tuple[int, dict[str, Any]]:
    """Return (exit status, report). Status 2 means a conflict; nothing was written."""
    hosts = ("codex", "claude") if host == "both" else (host,)
    run = _Run((home or Path.home()).expanduser().resolve(), repository, action == "remove", apply)
    items = _plan(run, hosts, with_stop_hook)
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "apply" if apply else "preview",
        "action": action,
        "version": __version__,
        "items": items,
    }
    if any(item["result"] == "conflict" for item in items):
        for item in items:  # nothing was written, so no item may claim it was
            item["result"] = _AS_PREVIEW.get(item["result"], item["result"])
        return 2, report
    if apply:
        outcome = run.write()
        if outcome != "ok":
            failure = "conflict" if outcome == "changed" else "failed"
            for item in items:
                if item["result"] in _WRITE_RESULTS:
                    item["result"] = failure
            report["rollback"] = "complete" if run.rollback_complete else "incomplete"
            return 2, report
    return 0, report


_OTHER = "other"  # installed content that is not the recorded digest; no digest ever equals it
_FIXED_IDS = {"skill": host_profiles._PROFILE, "worker-agent": WORKER_ID, "stop-hook": STOP_EVENT}  # MCP items use their id


def _ledger_state(home: Path) -> tuple[str, dict[str, Any]]:
    """The ownership ledger read without writing: its state, and its items when it is readable."""
    try:
        raw = _read_shared(home / ".inonu-harness" / "bundle-ledger.json")
        items, _ = _parse_ledger(raw)
    except (_Malformed, OSError):
        return "unreadable", {}
    return ("absent" if raw is None else "present"), items


def _installed_digest(path: Path) -> str | None:
    raw = _read_shared(path)
    return None if raw is None else _sha(raw)


def _claude_mcp_digest(home: Path, server: str) -> str | None:
    servers = _json_doc(_read_shared(home / ".claude.json")).get("mcpServers", {})
    if not isinstance(servers, dict):
        raise _Malformed
    return _canon(servers[server]) if server in servers else None


def _codex_mcp_digest(home: Path, server: str) -> str | None:
    raw = _read_shared(home / ".codex" / "config.toml")
    if raw is None:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise _Malformed from None
    servers = _toml_servers(text)
    found = _find_block(text, server)
    if found is not None:
        start, end = found
        block = text[start:end]
        if servers.get(server) != _toml_servers(block).get(server):
            return _OTHER  # a table or sub-table outside the markers changes the server
        return _sha(block.encode("utf-8"))
    return _OTHER if server in servers else None  # a server table without the markers this bundle writes


def _stop_groups(home: Path) -> list[Any]:
    hooks = _json_doc(_read_shared(home / ".claude" / "settings.json")).get("hooks", {})
    stop = hooks.get(STOP_EVENT, []) if isinstance(hooks, dict) else None
    if not isinstance(stop, list):
        raise _Malformed
    return stop


def _installed(item: dict[str, Any], home: Path, recorded: str | None) -> str | None:
    """Digest of what the item is now, _OTHER for other content, None when absent. Raises _Malformed when unreadable."""
    kind, host = item["kind"], item["host"]
    if kind == "skill":
        return _installed_digest(host_profiles._target(home, host) / host_profiles._SKILL)
    if kind == "worker-agent":
        return _installed_digest(home / ".claude" / "agents" / "inonu-worker.md")
    if kind == "stop-hook":
        groups = _stop_groups(home)
        if recorded is not None and any(_canon(group) == recorded for group in groups):
            return recorded
        return _OTHER if any(_mentions_runner(group) for group in groups) else None
    if host == "claude":
        return _claude_mcp_digest(home, item["id"])
    return _codex_mcp_digest(home, item["id"])


def _ownership(item: dict[str, Any], home: Path, ledger: dict[str, Any]) -> str:
    recorded = ledger.get(_key(item["kind"], item["host"], _FIXED_IDS.get(item["kind"], item.get("id"))))
    recorded_digest = None if recorded is None else recorded["sha256"]
    installed = _installed(item, home, recorded_digest)
    if recorded_digest is None:
        return "none" if installed is None else "foreign"
    return "ours" if installed == recorded_digest else "modified"


def status_with_ownership(host: str = "both", home: Path | None = None, repository: Path = REPOSITORY) -> dict[str, Any]:
    """bundle status plus each item's ownership relative to the ledger. Read-only; an unreadable file reads as unknown."""
    report = status_bundle(host, home, repository)
    root = (home or Path.home()).expanduser().resolve()
    ledger_state, ledger = _ledger_state(root)
    for item in report["items"]:
        try:
            item["ownership"] = "unknown" if ledger_state == "unreadable" else _ownership(item, root, ledger)
        except (_Malformed, OSError):
            item["ownership"] = "unknown"
    counts = Counter(item["ownership"] for item in report["items"])
    return {**report, "ledger": ledger_state, "ownership_summary": dict(sorted(counts.items()))}
