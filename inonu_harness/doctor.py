"""Read-only, allowlisted environment inventory for Inonu Harness."""

from __future__ import annotations

import json
import os
import platform as platform_module
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Mapping


_STATE_VALUES = {"installed", "configured", "operational", "documented", "not_found", "unknown"}
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_VERSION = re.compile(r"(?<![A-Za-z0-9])\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.-]+)?")
_SAFE_VERSION = re.compile(r"^\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.-]+)?$")
_KNOWN_EVENTS = {
    "SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PostToolUseFailure", "Notification", "Stop", "SubagentStart", "SubagentStop",
    "PreCompact", "AfterCompact", "ConfigChange", "WorktreeCreate", "WorktreeRemove",
}
_ORIGINS = {"user_agents", "user_codex", "project_agents", "project_codex", "plugin_cache"}
_INTEGRATION_IDS = ("jev", "rtk", "headroom", "codegraph", "ponytail", "sequential_thinking")


def _state(value: Any) -> str:
    return value if isinstance(value, str) and value in _STATE_VALUES else "unknown"


def _version(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _VERSION.search(value)
    candidate = match.group(0) if match else None
    return candidate if candidate and _SAFE_VERSION.fullmatch(candidate) else None


def _safe_name(value: Any) -> str | None:
    return value if isinstance(value, str) and _NAME.fullmatch(value) else None


def _status(state: str, source: str, reason: str | None = None, version: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"state": _state(state), "source": source}
    if version is not None:
        result["version"] = version
    if reason:
        result["reason"] = reason
    return result


class LocalProbe:
    """Collect raw local data for the normalizer; raw values never enter the report."""

    def __init__(self, project_root: str | Path | None = None, user_root: str | Path | None = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.user_root = Path(user_root) if user_root else Path.home()

    @staticmethod
    def _read_toml(path: Path, source: str) -> dict[str, Any]:
        if not path.is_file():
            return {"state": "not_found", "source": source, "document": None}
        try:
            with path.open("rb") as stream:
                document = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError):
            return {"state": "unknown", "source": source, "document": None}
        return {"state": "configured", "source": source, "document": document}

    @staticmethod
    def _read_json(path: Path) -> tuple[str, Any]:
        if not path.is_file():
            return "not_found", None
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return "unknown", None
        if not isinstance(document, (Mapping, list)):
            return "unknown", None
        return "configured", document

    @staticmethod
    def _cli_version(executable: str | None) -> dict[str, Any]:
        if executable is None:
            return {"available": False, "version_output": None}
        try:
            result = subprocess.run(
                [executable, "--version"], capture_output=True, text=True, timeout=4, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return {"available": None, "version_output": None}
        if result.returncode != 0:
            return {"available": True, "version_output": None}
        return {"available": True, "version_output": result.stdout[:4096]}

    @staticmethod
    def _mcp_registry(executable: str | None) -> dict[str, Any]:
        if executable is None:
            return {"available": False, "servers": None}
        try:
            result = subprocess.run(
                [executable, "mcp", "list", "--json"], capture_output=True, text=True,
                timeout=5, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return {"available": None, "servers": None}
        if result.returncode != 0:
            return {"available": None, "servers": None}
        try:
            return {"available": True, "servers": json.loads(result.stdout)}
        except (TypeError, json.JSONDecodeError):
            return {"available": True, "servers": None}

    @staticmethod
    def _read_skill(path: Path, origin: str) -> dict[str, Any] | None:
        try:
            content = path.read_text(encoding="utf-8")[:4096]
        except (OSError, UnicodeError):
            return None
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return None
        fields: dict[str, str] = {}
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, separator, value = line.partition(":")
            if separator and key.strip() in {"name", "version"}:
                fields[key.strip()] = value.strip().strip("\"'")
        name = _safe_name(fields.get("name"))
        if not name:
            return None
        version = fields.get("version")
        if not _SAFE_VERSION.fullmatch(version or ""):
            version = None
        if version is None and origin == "plugin_cache":
            parts = path.parts
            if "skills" in parts:
                index = parts.index("skills")
                candidate = parts[index - 1] if index else ""
                version = candidate if _SAFE_VERSION.fullmatch(candidate) else None
        return {"name": name, "origin": origin, "version": version}

    def _skills(self, codex_home: Path) -> list[dict[str, Any]] | None:
        roots = (
            (self.user_root / ".agents" / "skills", "user_agents"),
            (codex_home / "skills", "user_codex"),
            (self.project_root / ".agents" / "skills", "project_agents"),
            (self.project_root / ".codex" / "skills", "project_codex"),
            (codex_home / "plugins" / "cache", "plugin_cache"),
        )
        skills: list[dict[str, Any]] = []
        try:
            for root, origin in roots:
                if root.exists():
                    for skill_file in root.rglob("SKILL.md"):
                        row = self._read_skill(skill_file, origin)
                        if row:
                            skills.append(row)
        except OSError:
            return None
        unique: dict[tuple[str, str], dict[str, Any]] = {}
        for row in skills:
            key = (row["name"].casefold(), row["origin"])
            previous = unique.get(key)
            if previous is None or (previous["version"] is None and row["version"] is not None):
                unique[key] = row
        return sorted(unique.values(), key=lambda row: (row["name"].casefold(), row["origin"]))

    def _documented_integrations(self) -> list[str]:
        terms = {
        "jev": ("jev-sdd", "jev engineering"),
            "rtk": ("rtk",), "headroom": ("headroom",), "codegraph": ("codegraph",),
            "ponytail": ("ponytail",), "sequential_thinking": ("sequential thinking", "sequential-thinking"),
        }
        files = [self.project_root / "README.md"]
        docs = self.project_root / "docs"
        try:
            if docs.exists():
                files.extend(docs.rglob("*.md"))
        except OSError:
            return []
        found: set[str] = set()
        for path in files:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore").casefold()
            except OSError:
                continue
            for integration, candidates in terms.items():
                if any(candidate in content for candidate in candidates):
                    found.add(integration)
        return sorted(found)

    def snapshot(self) -> dict[str, Any]:
        raw_codex_home = os.environ.get("CODEX_HOME")
        codex_home = Path(raw_codex_home) if raw_codex_home else self.user_root / ".codex"
        global_config = self._read_toml(codex_home / "config.toml", "user_codex_config")
        project_config = self._read_toml(self.project_root / ".codex" / "config.toml", "project_codex_config")
        global_hooks_state, global_hooks = self._read_json(codex_home / "hooks.json")
        project_hooks_state, project_hooks = self._read_json(self.project_root / ".codex" / "hooks.json")
        global_config["hooks_file_state"] = global_hooks_state
        project_config["hooks_file_state"] = project_hooks_state
        if global_hooks is not None:
            global_config["hooks_document"] = global_hooks
        if project_hooks is not None:
            project_config["hooks_document"] = project_hooks

        cli = {name: self._cli_version(shutil.which(name)) for name in ("codex", "rtk", "headroom", "codegraph", "jev-sdd")}
        codex_path = shutil.which("codex")
        return {
            "platform": {
                "name": platform_module.system(), "release": platform_module.release(),
                "architecture": platform_module.machine(),
                "python_version": ".".join(str(part) for part in sys.version_info[:3]),
            },
            "configurations": {"global": global_config, "project": project_config},
            "skills": self._skills(codex_home),
            "cli": cli,
            "mcp_registry": self._mcp_registry(codex_path),
            "documentation": self._documented_integrations(),
        }


def _mcp_names_from_config(configurations: Mapping[str, Any]) -> dict[str, set[str]]:
    names: dict[str, set[str]] = {"global": set(), "project": set()}
    for scope in names:
        entry = configurations.get(scope)
        document = entry.get("document") if isinstance(entry, Mapping) else None
        servers = document.get("mcp_servers") if isinstance(document, Mapping) else None
        if isinstance(servers, Mapping):
            names[scope].update(name for key in servers if (name := _safe_name(key)))
    return names


def _mcp_names_from_registry(registry: Any) -> tuple[set[str], str]:
    if not isinstance(registry, Mapping) or registry.get("available") is not True:
        return set(), "unknown"
    raw = registry.get("servers")
    if raw is None:
        return set(), "unknown"
    if isinstance(raw, Mapping):
        raw = raw.get("servers", [])
    if not isinstance(raw, list):
        return set(), "unknown"
    result = set()
    for server in raw:
        if isinstance(server, Mapping) and (name := _safe_name(server.get("name"))):
            result.add(name)
    return result, "observed"


def _shell_kind(command: Any) -> str:
    if not isinstance(command, str) or not command.strip():
        return "unknown"
    value = command.strip().casefold()
    if re.match(r"^(?:pwsh|powershell)(?:\.exe)?(?:\s|$)", value) or "$env:" in value or "write-host" in value:
        return "powershell"
    if re.match(r"^(?:bash|sh)(?:\.exe)?(?:\s|$)", value) or value.startswith("#!/bin/bash") or "[[" in value or "set -e" in value:
        return "bash"
    return "unknown"


def _hook_rows(document: Any, scope: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def visit(node: Any, event_hint: str = "unknown", matcher_hint: Any = None) -> None:
        if isinstance(node, Mapping):
            event = node.get("event", event_hint)
            if not isinstance(event, str) or event not in _KNOWN_EVENTS:
                event = "other" if event != "unknown" else "unknown"
            matcher = node.get("matcher", matcher_hint)
            if isinstance(matcher, str):
                normalized = matcher.casefold()
                matcher_kind = "bash" if "bash" in normalized else "powershell" if "powershell" in normalized else "other"
            else:
                matcher_kind = "all" if matcher is None else "unknown"
            has_default = "command" in node
            has_windows = "commandWindows" in node or "command_windows" in node
            if has_default or has_windows:
                default_kind = _shell_kind(node.get("command"))
                windows_kind = _shell_kind(node.get("commandWindows", node.get("command_windows")))
                bash_state = "compatible" if default_kind == "bash" else "incompatible" if default_kind == "powershell" else "unknown"
                powershell_kind = windows_kind if windows_kind != "unknown" else default_kind
                powershell_state = "compatible" if powershell_kind == "powershell" else "incompatible" if powershell_kind == "bash" else "unknown"
                if has_windows and default_kind == "bash":
                    powershell_state = "compatible" if windows_kind == "powershell" else "unknown"
                if not has_default and has_windows and windows_kind == "powershell":
                    bash_state = "incompatible"
                found.append({
                    "event": event,
                    "matcher": matcher_kind,
                    "source": f"{scope}_codex_hooks",
                    "compatibility": {
                        "bash": {"state": bash_state, "reason": "shell_family_inferred_without_execution"},
                        "powershell": {"state": powershell_state, "reason": "shell_family_inferred_without_execution"},
                    },
                })
            for key, child in node.items():
                if key in {"command", "commandWindows", "command_windows"}:
                    continue
                child_event = key if key in _KNOWN_EVENTS else event_hint
                if key == "hooks" or key == "hook" or key in _KNOWN_EVENTS or isinstance(child, (Mapping, list)):
                    visit(child, child_event, node.get("matcher", matcher_hint))
        elif isinstance(node, list):
            for child in node:
                visit(child, event_hint, matcher_hint)

    visit(document)
    return found


def _status_for_cli(raw: Any, source: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _status("unknown", source, "probe_unavailable")
    available = raw.get("available")
    version = _version(raw.get("version_output"))
    if available is False:
        return _status("not_found", source, "cli_not_on_path")
    if available is not True:
        return _status("unknown", source, "probe_unavailable")
    if version:
        return _status("installed", source, version=version)
    return _status("unknown", source, "version_not_reported")


def _hook_references(document: Any, tool_name: str) -> bool:
    pattern = re.compile(rf"(?<![A-Za-z0-9_.-]){re.escape(tool_name)}(?![A-Za-z0-9_.-])", re.IGNORECASE)
    if isinstance(document, Mapping):
        for key, value in document.items():
            if key in {"command", "commandWindows", "command_windows"}:
                values = value if isinstance(value, list) else [value]
                if any(isinstance(item, str) and pattern.search(item) for item in values):
                    return True
            elif _hook_references(value, tool_name):
                return True
    elif isinstance(document, list):
        return any(_hook_references(item, tool_name) for item in document)
    return False


def _config_summary(raw: Any, scope: str) -> dict[str, Any]:
    source = "user_codex_config" if scope == "global" else "project_codex_config"
    if not isinstance(raw, Mapping):
        return {"state": "unknown", "source": source, "reason": "probe_unavailable"}
    state = _state(raw.get("state"))
    result: dict[str, Any] = {"state": state, "source": source}
    if state == "unknown":
        result["reason"] = "configuration_unavailable_or_invalid"
    return result


def _normalize_skills(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = _safe_name(item.get("name"))
        origin = item.get("origin")
        if not name or not isinstance(origin, str) or origin not in _ORIGINS:
            continue
        version = item.get("version")
        if not isinstance(version, str) or not _SAFE_VERSION.fullmatch(version):
            version = None
        result.append({
            "name": name, "origin": origin, "version": version,
            "state": "installed", "source": "skill_frontmatter_or_scanned_location",
            "session_availability": _status(
                "unknown", "active_host_skill_catalog", "local_probe_cannot_prove_skill_loaded_in_session",
            ),
        })
    unique = {(item["name"], item["origin"], item["version"]): item for item in result}
    return sorted(unique.values(), key=lambda item: (item["name"].casefold(), item["origin"]))


def _integration_statuses(
    skills: list[dict[str, Any]], cli: Mapping[str, Any], mcp_names: set[str], documented: set[str],
    rtk_configured: bool, registration_complete: bool, hook_probe_complete: bool, skill_probe_available: bool,
) -> dict[str, dict[str, Any]]:
    skill_names = {item["name"].casefold() for item in skills}
    cli_status = {name: _status_for_cli(cli.get(name), f"{name}_cli_version") for name in ("rtk", "headroom", "codegraph", "jev-sdd")}
    configured_ids = {
        "jev": "jev-sdd", "headroom": "headroom", "codegraph": "codegraph",
        "sequential_thinking": "sequential-thinking",
    }
    result: dict[str, dict[str, Any]] = {}
    licenses = {
        "jev": {"value": None, "source": "not_verified"},
        "rtk": {"value": "Apache-2.0 CLI; BUSL-1.1 engine/proxy", "source": "verified_package_metadata"},
        "headroom": {"value": "Apache-2.0", "source": "verified_package_metadata"},
        "codegraph": {
            "value": None,
            "source": "local_distribution_unverified",
            "upstream_value": "MIT",
            "upstream_source": "official_repository",
        },
        "ponytail": {"value": "MIT skill", "source": "skill_frontmatter"},
        "sequential_thinking": {"value": "MIT", "source": "verified_upstream_metadata"},
    }
    for key in _INTEGRATION_IDS:
        installed: dict[str, Any]
        if key == "jev":
            if "jev-engineering" in skill_names:
                installed = _status("installed", "jev_engineering_skill_inventory", "standalone_server_installation_not_probed")
            elif not skill_probe_available and cli_status["jev-sdd"]["state"] == "not_found":
                installed = _status("unknown", "skill_and_cli_inventory", "skill_probe_unavailable")
            else:
                installed = cli_status["jev-sdd"]
        elif key == "ponytail":
            installed = _status("installed", "skill_inventory") if "ponytail" in skill_names else _status("unknown", "skill_inventory", "skill_probe_unavailable") if not skill_probe_available else _status("not_found", "skill_inventory", "not_found_in_scanned_locations")
        elif key == "sequential_thinking":
            installed = _status("unknown", "known_skill_and_plugin_locations", "server_installation_not_probed")
        else:
            installed = cli_status[key]

        mcp_name = configured_ids.get(key)
        config_state = "configured" if mcp_name and mcp_name in mcp_names else "not_found" if registration_complete else "unknown"
        if key == "rtk":
            config_state = "configured" if rtk_configured else "not_found" if hook_probe_complete else "unknown"
            config_source = "hook_configuration"
            config_reason = None if rtk_configured else "no_hook_reference_observed" if config_state == "not_found" else "hook_probe_incomplete"
        elif key == "ponytail":
            config_state = "unknown"
            config_source = "skill_activation_state"
            config_reason = "skill_presence_does_not_prove_active_session_loading"
        else:
            config_source = "codex_mcp_registry_and_configuration"
            config_reason = None if config_state == "configured" else "not_registered_in_observed_configuration" if config_state == "not_found" else "registration_probe_incomplete"
        if key in {"jev", "headroom", "codegraph", "sequential_thinking"}:
            operational = _status("unknown", "active_host_mcp_catalog", "local_cli_cannot_prove_active_session_access")
        elif key == "ponytail":
            operational = _status("unknown", "active_host_skill_catalog", "local_probe_cannot_prove_skill_loaded_in_session")
        else:
            operational = _status("unknown", "cli_and_hook_observation", "version_and_reference_do_not_prove_hook_execution")
        result[key] = {
            "installed": installed,
            "configured": _status(config_state, config_source, config_reason),
            "operational": operational,
            "documented": _status("documented" if key in documented else "not_found", "project_documentation_scan", None if key in documented else "not_mentioned_in_scanned_docs"),
            "license": licenses[key],
        }
    return result


def _safe_platform(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {"name": "unknown", "release": None, "architecture": None, "source": "platform_probe", "state": "unknown"}
    name = raw.get("name")
    name = name if isinstance(name, str) and name in {"Windows", "Linux", "Darwin"} else "unknown"
    release = raw.get("release")
    architecture = raw.get("architecture")
    release = release[:40] if isinstance(release, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,40}", release) else None
    architecture = architecture[:24] if isinstance(architecture, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,24}", architecture) else None
    return {"name": name, "release": release, "architecture": architecture, "source": "platform_module", "state": "operational" if name != "unknown" else "unknown"}


def collect_environment(probe: Any = None, project_root: str | Path | None = None, user_root: str | Path | None = None) -> dict[str, Any]:
    """Return only allowlisted metadata; probe details and all raw values are discarded."""
    if probe is None:
        probe = LocalProbe(project_root, user_root)
    try:
        snapshot = probe.snapshot() if hasattr(probe, "snapshot") else probe
    except Exception:
        snapshot = {}
    if not isinstance(snapshot, Mapping):
        snapshot = {}

    configurations_raw = snapshot.get("configurations")
    configurations_raw = configurations_raw if isinstance(configurations_raw, Mapping) else {}
    configurations = {scope: _config_summary(configurations_raw.get(scope), scope) for scope in ("global", "project")}
    config_mcp_names = _mcp_names_from_config(configurations_raw)
    registry_names, registry_state = _mcp_names_from_registry(snapshot.get("mcp_registry"))
    all_names = registry_names | config_mcp_names["global"] | config_mcp_names["project"]
    mcps = [{
        "name": name,
        "registration": _status(
            "configured",
            "codex_mcp_list_and_configuration" if name in registry_names and (name in config_mcp_names["global"] or name in config_mcp_names["project"]) else "codex_mcp_list" if name in registry_names else "codex_configuration",
        ),
        "accessibility": _status("unknown", "local_cli_cannot_prove_session_access", "active_host_tool_catalog_not_available_to_standalone_cli"),
    } for name in sorted(all_names)]
    if registry_state == "unknown" and not all_names:
        mcp_registry = _status("unknown", "codex_mcp_list", "registry_probe_unavailable")
    else:
        mcp_registry = _status("configured" if all_names else "not_found", "codex_mcp_list_or_configuration", None if all_names else "no_registered_servers_observed")

    skills = _normalize_skills(snapshot.get("skills"))
    cli_raw = snapshot.get("cli") if isinstance(snapshot.get("cli"), Mapping) else {}
    cli_status = _status_for_cli(cli_raw.get("codex"), "codex_cli_version")
    python_version = _version(snapshot.get("platform", {}).get("python_version")) if isinstance(snapshot.get("platform"), Mapping) else None
    if not python_version:
        python_version = ".".join(str(part) for part in sys.version_info[:3])
        python_source = "python_runtime"
    else:
        python_source = "python_runtime"
    platform_info = _safe_platform(snapshot.get("platform"))

    hook_entries: list[dict[str, Any]] = []
    for scope in ("global", "project"):
        raw_config = configurations_raw.get(scope)
        if not isinstance(raw_config, Mapping):
            continue
        document = raw_config.get("document")
        hooks_document = raw_config.get("hooks_document")
        if isinstance(document, Mapping) and "hooks" in document:
            hook_entries.extend(_hook_rows(document.get("hooks"), scope))
        if hooks_document is not None:
            hook_entries.extend(_hook_rows(hooks_document, scope))
    rtk_configured = False
    for raw in configurations_raw.values():
        if not isinstance(raw, Mapping):
            continue
        document = raw.get("document")
        if isinstance(document, Mapping) and _hook_references(document.get("hooks"), "rtk"):
            rtk_configured = True
        if _hook_references(raw.get("hooks_document"), "rtk"):
            rtk_configured = True
    hook_entry_counts: dict[tuple[str, str, str], int] = {}
    for row in hook_entries:
        key = (row["event"], row["matcher"], row["source"])
        hook_entry_counts[key] = hook_entry_counts.get(key, 0) + 1
    hook_unique = {(row["event"], row["matcher"], row["source"], row["compatibility"]["bash"]["state"], row["compatibility"]["powershell"]["state"]): row for row in hook_entries}
    hook_entries = sorted(hook_unique.values(), key=lambda row: (row["source"], row["event"], row["matcher"]))
    hook_probe_complete = all(configurations[scope]["state"] != "unknown" for scope in configurations)
    hook_probe_complete = hook_probe_complete and all(
        not isinstance(configurations_raw.get(scope), Mapping) or configurations_raw[scope].get("hooks_file_state", "not_found") != "unknown"
        for scope in configurations
    )
    hooks_state = "configured" if hook_entries else "not_found" if hook_probe_complete else "unknown"

    findings: list[dict[str, Any]] = []
    for name in sorted(config_mcp_names["global"] & config_mcp_names["project"]):
        findings.append({"type": "mcp_name_in_multiple_scopes", "name": name, "scopes": ["global", "project"], "severity": "possible_conflict", "source": "global_and_project_codex_configuration"})
    for (event, matcher, source), count in sorted(hook_entry_counts.items()):
        if count > 1:
            findings.append({"type": "repeated_hook_event_matcher", "event": event, "matcher": matcher, "scope": source, "count": count, "severity": "possible_redundancy", "source": "hook_structure"})
    hook_keys: dict[tuple[str, str], set[str]] = {}
    for item in hook_entries:
        key = (item["event"], item["matcher"])
        hook_keys.setdefault(key, set()).add(item["source"])
    for (event, matcher), scopes in sorted(hook_keys.items()):
        if len(scopes) > 1:
            findings.append({"type": "hook_event_in_multiple_scopes", "event": event, "matcher": matcher, "scopes": sorted(scopes), "severity": "possible_overlap", "source": "global_and_project_codex_configuration"})

    documented_raw = snapshot.get("documentation")
    documented = {item.casefold().replace("-", "_").replace(" ", "_") for item in documented_raw if isinstance(item, str)} if isinstance(documented_raw, list) else set()
    alias = {"jev_sdd": "jev", "sequential_thinking": "sequential_thinking"}
    documented = {alias.get(item, item) for item in documented}
    registration_complete = registry_state == "observed" or all(configurations[scope]["state"] != "unknown" for scope in configurations)
    integrations = _integration_statuses(
        skills, cli_raw, all_names, documented, rtk_configured, registration_complete, hook_probe_complete,
        isinstance(snapshot.get("skills"), list),
    )
    for key, item in integrations.items():
        if item["operational"]["state"] == "unknown":
            pass

    unknowns: list[dict[str, str]] = []
    for mcp in mcps:
        unknowns.append({"subject": f"mcp:{mcp['name']}:accessibility", "reason": "local_cli_cannot_prove_active_session_access"})
    for item in hook_entries:
        for shell in ("bash", "powershell"):
            if item["compatibility"][shell]["state"] == "unknown":
                unknowns.append({"subject": f"hook:{item['event']}:{shell}", "reason": "shell_family_not_identifiable_without_execution"})
    for name, status in (("codex_cli", cli_status), ("mcp_registry", mcp_registry)):
        if status["state"] == "unknown":
            unknowns.append({"subject": name, "reason": status.get("reason", "probe_unavailable")})
    unknowns.append({"subject": "codex_desktop", "reason": "desktop_app_version_not_reported_by_codex_cli"})
    for skill in skills:
        unknowns.append({
            "subject": f"skill:{skill['name']}:{skill['origin']}:session_availability",
            "reason": skill["session_availability"]["reason"],
        })
    for key, integration in integrations.items():
        if integration["operational"]["state"] == "unknown":
            unknowns.append({"subject": f"integration:{key}:operational", "reason": integration["operational"].get("reason", "operation_not_verified")})
        if integration["installed"]["state"] == "unknown":
            unknowns.append({"subject": f"integration:{key}:installed", "reason": integration["installed"].get("reason", "installation_not_verified")})
    if not isinstance(snapshot.get("skills"), list):
        unknowns.append({"subject": "skill_inventory", "reason": "skill_probe_unavailable"})

    return {
        "schema_version": 1,
        "runtime": {
            "platform": platform_info,
            "python": {"version": python_version, "source": python_source, "state": "operational"},
            "codex_cli": cli_status,
            "codex_desktop": _status("unknown", "standalone_cli_limit", "desktop_app_version_not_reported_by_codex_cli"),
        },
        "configurations": configurations,
        "skills": skills,
        "mcps": mcps,
        "mcp_registry": mcp_registry,
        "integrations": integrations,
        "hooks": {"state": hooks_state, "source": "global_and_project_codex_configuration", "entries": hook_entries},
        "findings": findings,
        "unknowns": unknowns,
    }


def load_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path) if path else Path(__file__).with_name("integrations.json")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("integrations"), list):
        raise ValueError("invalid integrations manifest schema")
    return data


def render_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
