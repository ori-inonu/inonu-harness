"""Read-only audit of explicit SDD artifact links and local evidence bytes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_EVIDENCE_BYTES = 8 * 1024 * 1024
_INVALID_MANIFEST = "invalid audit manifest"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z", re.ASCII)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_ROOT_FIELDS = {"schema_version", "milestone_id", "requirements", "tasks", "verifications", "evidence"}
_RECORD_FIELDS = {
    "requirements": {"id", "status", "specification_evidence_id"},
    "tasks": {"id", "artifact_evidence_id", "requirement_ids", "status", "verification_ids"},
    "verifications": {"id", "requirement_ids", "status", "evidence_ids"},
    "evidence": {"id", "path", "sha256"},
}


def audit_manifest(document: Mapping[str, Any], root: str | Path) -> dict[str, Any]:
    """Return deterministic findings and requirement coverage for a v1 manifest."""

    _validate_manifest(document)
    requirement_by_id = {item["id"]: item for item in document["requirements"]}
    verification_by_id = {item["id"]: item for item in document["verifications"]}
    evidence_by_id = {item["id"]: item for item in document["evidence"]}
    verified_evidence: set[str] = set()
    findings: list[dict[str, str]] = []
    seen_findings: set[tuple[str, str]] = set()

    def add_finding(code: str, kind: str, identifier: str) -> None:
        subject = f"{kind}:{identifier}"
        key = (code, subject)
        if key not in seen_findings:
            seen_findings.add(key)
            findings.append({"code": code, "subject": subject})

    resolved_root = _resolve_root(root)
    for evidence in document["evidence"]:
        candidate = _resolve_evidence_path(evidence["path"], resolved_root)
        if candidate is None:
            add_finding("evidence_unavailable", "evidence", evidence["id"])
            continue
        content = _read_evidence(candidate, resolved_root)
        if content is None:
            add_finding("evidence_unavailable", "evidence", evidence["id"])
            continue
        if len(content) > MAX_EVIDENCE_BYTES:
            add_finding("evidence_unavailable", "evidence", evidence["id"])
        elif hashlib.sha256(content).hexdigest() != evidence["sha256"]:
            add_finding("evidence_changed", "evidence", evidence["id"])
        else:
            verified_evidence.add(evidence["id"])

    for requirement in document["requirements"]:
        evidence_id = requirement["specification_evidence_id"]
        if evidence_id not in evidence_by_id:
            add_finding("unknown_evidence", "evidence", evidence_id)
    for task in document["tasks"]:
        evidence_id = task["artifact_evidence_id"]
        if evidence_id not in evidence_by_id:
            add_finding("unknown_evidence", "evidence", evidence_id)
        for requirement_id in task["requirement_ids"]:
            if requirement_id not in requirement_by_id:
                add_finding("unknown_requirement", "requirement", requirement_id)
        for verification_id in task["verification_ids"]:
            if verification_id not in verification_by_id:
                add_finding("unknown_verification", "verification", verification_id)
    for verification in document["verifications"]:
        for requirement_id in verification["requirement_ids"]:
            if requirement_id not in requirement_by_id:
                add_finding("unknown_requirement", "requirement", requirement_id)
        for evidence_id in verification["evidence_ids"]:
            if evidence_id not in evidence_by_id:
                add_finding("unknown_evidence", "evidence", evidence_id)

    def verification_evidence_verified(verification: Mapping[str, Any]) -> bool:
        return bool(verification["evidence_ids"]) and all(
            evidence_id in verified_evidence for evidence_id in verification["evidence_ids"]
        )

    def task_artifact_verified(task: Mapping[str, Any]) -> bool:
        return task["artifact_evidence_id"] in verified_evidence

    def has_verified_check(task: Mapping[str, Any], requirement_id: str) -> bool:
        return any(
            verification_id in verification_by_id
            and requirement_id in verification_by_id[verification_id]["requirement_ids"]
            and verification_by_id[verification_id]["status"] == "pass"
            and verification_evidence_verified(verification_by_id[verification_id])
            for verification_id in task["verification_ids"]
        )

    coverage: list[dict[str, Any]] = []
    for requirement in document["requirements"]:
        requirement_id = requirement["id"]
        task_ids = [
            task["id"]
            for task in document["tasks"]
            if requirement_id in task["requirement_ids"]
        ]
        verification_ids = [
            verification["id"]
            for verification in document["verifications"]
            if verification["status"] == "pass"
            and requirement_id in verification["requirement_ids"]
            and any(
                task["status"] == "complete"
                and task_artifact_verified(task)
                and verification["id"] in task["verification_ids"]
                and requirement_id in task["requirement_ids"]
                for task in document["tasks"]
            )
            and verification_evidence_verified(verification)
        ]
        covered = (
            requirement["status"] == "defined"
            and requirement["specification_evidence_id"] in verified_evidence
            and bool(verification_ids)
        )
        if requirement["status"] == "unresolved":
            add_finding("requirement_unresolved", "requirement", requirement_id)
        if not covered:
            add_finding("requirement_uncovered", "requirement", requirement_id)
        coverage.append(
            {
                "requirement_id": requirement_id,
                "status": "covered" if covered else "uncovered",
                "task_ids": task_ids,
                "verification_ids": verification_ids,
            }
        )

    for task in document["tasks"]:
        if task["status"] != "complete":
            add_finding("task_incomplete", "task", task["id"])
        for requirement_id in task["requirement_ids"]:
            if (
                task["status"] != "complete"
                or not task_artifact_verified(task)
                or requirement_id not in requirement_by_id
                or not has_verified_check(task, requirement_id)
            ):
                add_finding("task_requirement_unverified", "task", task["id"])

    linked_verification_ids = {
        verification_id
        for task in document["tasks"]
        for verification_id in task["verification_ids"]
    }
    for verification in document["verifications"]:
        if verification["status"] != "pass":
            add_finding("verification_not_passed", "verification", verification["id"])
        if not verification_evidence_verified(verification):
            add_finding("verification_evidence_missing", "verification", verification["id"])
        if verification["id"] not in linked_verification_ids:
            add_finding("verification_unlinked", "verification", verification["id"])

    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": document["milestone_id"],
        "scope": "declared_artifact_links",
        "status": "fail" if findings else "pass",
        "findings": findings,
        "coverage": coverage,
    }


def load_audit_manifest(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate one bounded UTF-8 JSON manifest."""

    try:
        with Path(path).open("rb") as stream:
            content = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(content) > MAX_MANIFEST_BYTES:
            raise ValueError
        document = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
        _validate_manifest(document)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError):
        raise ValueError(_INVALID_MANIFEST) from None
    return document


class _DuplicateJsonKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey
        result[key] = value
    return result


def _validate_manifest(document: Any) -> None:
    if not isinstance(document, Mapping) or set(document) != _ROOT_FIELDS:
        raise ValueError(_INVALID_MANIFEST)
    version = document["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise ValueError(_INVALID_MANIFEST)
    if not _valid_id(document["milestone_id"]):
        raise ValueError(_INVALID_MANIFEST)

    for collection, fields in _RECORD_FIELDS.items():
        records = document[collection]
        if not isinstance(records, list) or not records:
            raise ValueError(_INVALID_MANIFEST)
        seen_ids: set[str] = set()
        for record in records:
            if not isinstance(record, Mapping) or set(record) != fields or not _valid_id(record.get("id")):
                raise ValueError(_INVALID_MANIFEST)
            if record["id"] in seen_ids:
                raise ValueError(_INVALID_MANIFEST)
            seen_ids.add(record["id"])

            if collection == "requirements":
                if record["status"] not in ("defined", "unresolved") or not _valid_id(record["specification_evidence_id"]):
                    raise ValueError(_INVALID_MANIFEST)
            elif collection == "tasks":
                if (
                    not _valid_id(record["artifact_evidence_id"])
                    or record["status"] not in ("pending", "blocked", "complete")
                    or not _valid_reference_list(record["requirement_ids"], nonempty=True)
                    or not _valid_reference_list(record["verification_ids"], nonempty=False)
                ):
                    raise ValueError(_INVALID_MANIFEST)
            elif collection == "verifications":
                if (
                    record["status"] not in ("pass", "fail", "not_run")
                    or not _valid_reference_list(record["requirement_ids"], nonempty=True)
                    or not _valid_reference_list(record["evidence_ids"], nonempty=False)
                ):
                    raise ValueError(_INVALID_MANIFEST)
            else:
                if not isinstance(record["path"], str) or not record["path"] or not isinstance(record["sha256"], str) or not _SHA256.fullmatch(record["sha256"]):
                    raise ValueError(_INVALID_MANIFEST)


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _valid_reference_list(value: Any, *, nonempty: bool) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(_valid_id(item) for item in value)
        and len(value) == len(set(value))
    )


def _resolve_root(root: Any) -> Path | None:
    try:
        path = Path(root).resolve(strict=True)
        return path if path.is_dir() else None
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _resolve_evidence_path(relative_path: str, root: Path | None) -> Path | None:
    if root is None or "\\" in relative_path:
        return None
    components = relative_path.split("/")
    if (
        any(component in ("", ".", "..") for component in components)
        or ":" in relative_path
        or relative_path.startswith("/")
    ):
        return None
    try:
        resolved = root.joinpath(*components).resolve(strict=True)
        resolved.relative_to(root)
        return resolved
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _read_evidence(candidate: Path, root: Path) -> bytes | None:
    try:
        if os.name == "posix":
            return _read_posix_evidence(candidate, root)
        if os.name == "nt":
            return _read_windows_evidence(candidate, root)
    except Exception:
        return None
    return None


def _read_posix_evidence(candidate: Path, root: Path) -> bytes | None:
    if os.open not in os.supports_dir_fd:
        return None
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    nonblock = getattr(os, "O_NONBLOCK", None)
    if nofollow is None or directory is None or nonblock is None:
        return None

    parts = candidate.relative_to(root).parts
    if not parts:
        return None
    close_on_exec = getattr(os, "O_CLOEXEC", 0)
    directory_flags = os.O_RDONLY | directory | nofollow | close_on_exec
    file_flags = os.O_RDONLY | nofollow | nonblock | close_on_exec
    file_fd: int | None = None
    directory_fds: list[int] = []
    root_directory_fds: list[int] = []
    try:
        root_parts = root.parts
        if not root.is_absolute() or not root_parts or root_parts[0] != os.sep:
            return None
        root_directory_fds.append(os.open(os.sep, directory_flags))
        for part in root_parts[1:]:
            root_directory_fds.append(os.open(part, directory_flags, dir_fd=root_directory_fds[-1]))
        parent_fd = root_directory_fds[-1]
        if not stat.S_ISDIR(os.fstat(parent_fd).st_mode):
            return None
        for part in parts[:-1]:
            parent_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            directory_fds.append(parent_fd)
        file_fd = os.open(parts[-1], file_flags, dir_fd=parent_fd)
        opened = os.fstat(file_fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_EVIDENCE_BYTES:
            return None
        return _read_bounded(file_fd)
    finally:
        if file_fd is not None:
            _close_fd(file_fd)
        for directory_fd in reversed(directory_fds):
            _close_fd(directory_fd)
        for directory_fd in reversed(root_directory_fds):
            _close_fd(directory_fd)


def _windows_kernel32() -> Any:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.GetFileType.argtypes = (wintypes.HANDLE,)
    kernel32.GetFileType.restype = wintypes.DWORD
    kernel32.GetFileInformationByHandle.argtypes = (wintypes.HANDLE, ctypes.c_void_p)
    kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
    kernel32.GetFinalPathNameByHandleW.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def _read_windows_evidence(candidate: Path, root: Path) -> bytes | None:
    import ctypes
    import msvcrt
    import ntpath
    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = (("low", wintypes.DWORD), ("high", wintypes.DWORD))

    class FileInformation(ctypes.Structure):
        _fields_ = (
            ("attributes", wintypes.DWORD),
            ("creation", FileTime),
            ("last_access", FileTime),
            ("last_write", FileTime),
            ("volume_serial", wintypes.DWORD),
            ("size_high", wintypes.DWORD),
            ("size_low", wintypes.DWORD),
            ("links", wintypes.DWORD),
            ("index_high", wintypes.DWORD),
            ("index_low", wintypes.DWORD),
        )

    api = _windows_kernel32()
    invalid_handle = ctypes.c_void_p(-1).value
    root_handle: Any = None
    file_handle: Any = None
    file_fd: int | None = None

    def handle_value(handle: Any) -> int | None:
        return handle if isinstance(handle, int) else getattr(handle, "value", None)

    def valid_handle(handle: Any) -> bool:
        return handle_value(handle) not in (None, invalid_handle)

    def final_path(handle: Any) -> str | None:
        size = 512
        while size <= 32768:
            buffer = ctypes.create_unicode_buffer(size)
            length = api.GetFinalPathNameByHandleW(handle, buffer, size, 0)
            if not length:
                return None
            if length < size:
                return buffer.value
            size = length + 1
        return None

    def file_info(handle: Any) -> FileInformation | None:
        info = FileInformation()
        return info if api.GetFileInformationByHandle(handle, ctypes.byref(info)) else None

    def normalized_windows_path(path: str) -> str:
        if path[:8].casefold() == "\\\\?\\UNC\\".casefold():
            return ntpath.normpath("\\\\" + path[8:])
        if path.startswith("\\\\?\\"):
            return ntpath.normpath(path[4:])
        return ntpath.normpath(path)

    def contained(path: str, parent: str) -> bool:
        normalized_path = normalized_windows_path(path)
        normalized_parent = normalized_windows_path(parent).rstrip("\\")
        return normalized_path.startswith(normalized_parent + "\\")

    try:
        root_handle = api.CreateFileW(
            str(root), 0x0080, 0x00000001 | 0x00000002, None, 3, 0x02000000 | 0x00200000, None
        )
        if not valid_handle(root_handle) or api.GetFileType(root_handle) != 1:
            return None
        root_info = file_info(root_handle)
        root_path = final_path(root_handle)
        if (
            root_info is None
            or not root_info.attributes & 0x00000010
            or root_info.attributes & 0x00000400
            or root_path is None
        ):
            return None
        if normalized_windows_path(root_path) != normalized_windows_path(str(root)):
            return None

        file_handle = api.CreateFileW(
            str(candidate), 0x80000000, 0x00000001, None, 3, 0x00200000 | 0x08000000, None
        )
        if not valid_handle(file_handle) or api.GetFileType(file_handle) != 1:
            return None
        info = file_info(file_handle)
        path = final_path(file_handle)
        if (
            info is None
            or info.attributes & (0x00000010 | 0x00000400)
            or path is None
            or not contained(path, root_path)
        ):
            return None
        size = (info.size_high << 32) | info.size_low
        if size > MAX_EVIDENCE_BYTES:
            return None

        file_fd = msvcrt.open_osfhandle(handle_value(file_handle), os.O_RDONLY | os.O_BINARY)
        file_handle = None
        return _read_bounded(file_fd)
    finally:
        if file_fd is not None:
            _close_fd(file_fd)
        if valid_handle(file_handle):
            api.CloseHandle(file_handle)
        if valid_handle(root_handle):
            api.CloseHandle(root_handle)


def _close_fd(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass


def _read_bounded(fd: int) -> bytes | None:
    content = bytearray()
    while len(content) <= MAX_EVIDENCE_BYTES:
        chunk = os.read(fd, MAX_EVIDENCE_BYTES + 1 - len(content))
        if not chunk:
            return bytes(content)
        content.extend(chunk)
        if len(content) > MAX_EVIDENCE_BYTES:
            return None
    return None
