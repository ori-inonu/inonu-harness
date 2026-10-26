from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

from inonu_harness import sdd_audit
from inonu_harness.sdd_audit import (
    MAX_EVIDENCE_BYTES,
    MAX_MANIFEST_BYTES,
    audit_manifest,
    load_audit_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "sdd_audit"
FROZEN_EVIDENCE_SHA256 = {
    "specification.txt": "c8901716603a5438b98294ad5937d46ec8f294be2afb801ba803329ba4734ef6",
    "task-artifact.txt": "862d96ffbf9973420ffe733825a5b9dcae091a776e67fc7de66beeef8478fc4b",
    "verification.txt": "65a6ed9f0cbef41e46689873584522030ce46a24c7eee7a0146a7312b70edfe2",
}


def _case(name: str) -> dict:
    return load_audit_manifest(FIXTURE_ROOT / name / "manifest.json")


def _findings(report: dict) -> set[tuple[str, str]]:
    return {(item["code"], item["subject"]) for item in report["findings"]}


def _copy_evidence(root: Path) -> None:
    (root / "evidence").mkdir()
    for name in FROZEN_EVIDENCE_SHA256:
        (root / "evidence" / name).write_bytes((FIXTURE_ROOT / "evidence" / name).read_bytes())


class SddAuditTests(unittest.TestCase):
    def test_clear_manifest_passes_with_declared_coverage(self):
        report = audit_manifest(_case("clear-change"), FIXTURE_ROOT)

        self.assertEqual(
            report,
            {
                "schema_version": 1,
                "milestone_id": "v08.clear-change",
                "scope": "declared_artifact_links",
                "status": "pass",
                "findings": [],
                "coverage": [
                    {
                        "requirement_id": "req.clear",
                        "status": "covered",
                        "task_ids": ["task.clear"],
                        "verification_ids": ["check.clear"],
                    }
                ],
            },
        )

    def test_five_frozen_synthetic_cases_have_recorded_outcomes(self):
        expected = {
            "clear-change": ("pass", set()),
            "ambiguous-change": (
                "fail",
                {("requirement_unresolved", "requirement:req.ambiguous"), ("requirement_uncovered", "requirement:req.ambiguous")},
            ),
            "reproducible-bug": ("pass", set()),
            "specification-delta": ("pass", set()),
            "protected-action": (
                "fail",
                {
                    ("requirement_uncovered", "requirement:req.protected"),
                    ("task_incomplete", "task:task.protected"),
                    ("task_requirement_unverified", "task:task.protected"),
                    ("verification_not_passed", "verification:check.protected"),
                },
            ),
        }
        for name, (status, expected_findings) in expected.items():
            with self.subTest(case=name):
                report = audit_manifest(_case(name), FIXTURE_ROOT)
                self.assertEqual(status, report["status"])
                self.assertEqual(expected_findings, _findings(report))

    def test_reports_are_deterministic_and_contain_no_local_paths(self):
        manifest = _case("specification-delta")

        first = audit_manifest(manifest, FIXTURE_ROOT)
        second = audit_manifest(manifest, FIXTURE_ROOT)
        encoded = json.dumps(first, ensure_ascii=False, sort_keys=True)

        self.assertEqual(first, second)
        self.assertNotIn(str(FIXTURE_ROOT), encoded)
        self.assertEqual(
            ["req.delta", "req.preserved"],
            [item["requirement_id"] for item in first["coverage"]],
        )
        self.assertEqual(["task.delta"], first["coverage"][0]["task_ids"])
        self.assertEqual(["check.delta"], first["coverage"][0]["verification_ids"])

    def test_fixture_evidence_bytes_match_frozen_hashes_and_are_not_text_normalized(self):
        for name, expected_digest in FROZEN_EVIDENCE_SHA256.items():
            with self.subTest(file=name):
                actual = hashlib.sha256((FIXTURE_ROOT / "evidence" / name).read_bytes()).hexdigest()
                self.assertEqual(expected_digest, actual)
        attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("fixtures/sdd_audit/evidence/** -text", attributes)

    def test_requirement_dropped_from_its_check_loses_coverage(self):
        manifest = _case("specification-delta")
        manifest["verifications"][0]["requirement_ids"] = ["req.preserved"]

        report = audit_manifest(manifest, FIXTURE_ROOT)

        self.assertEqual("fail", report["status"])
        self.assertIn(("task_requirement_unverified", "task:task.delta"), _findings(report))
        self.assertIn(("requirement_uncovered", "requirement:req.delta"), _findings(report))
        self.assertEqual("uncovered", report["coverage"][0]["status"])

    def test_check_not_linked_from_a_task_fails(self):
        manifest = _case("clear-change")
        manifest["tasks"][0]["verification_ids"] = []

        report = audit_manifest(manifest, FIXTURE_ROOT)

        self.assertIn(("verification_unlinked", "verification:check.clear"), _findings(report))
        self.assertIn(("task_requirement_unverified", "task:task.clear"), _findings(report))
        self.assertEqual("uncovered", report["coverage"][0]["status"])

    def test_passing_check_without_evidence_fails(self):
        manifest = _case("clear-change")
        manifest["verifications"][0]["evidence_ids"] = []

        report = audit_manifest(manifest, FIXTURE_ROOT)

        self.assertIn(("verification_evidence_missing", "verification:check.clear"), _findings(report))
        self.assertIn(("task_requirement_unverified", "task:task.clear"), _findings(report))
        self.assertEqual("uncovered", report["coverage"][0]["status"])

    def test_check_coverage_requires_every_declared_evidence_reference_to_verify(self):
        manifest = _case("specification-delta")
        manifest["evidence"].append(
            {"id": "ev.missing", "path": "evidence/missing.txt", "sha256": hashlib.sha256(b"missing").hexdigest()}
        )
        manifest["verifications"][0]["evidence_ids"] = ["ev.check", "ev.missing"]

        report = audit_manifest(manifest, FIXTURE_ROOT)

        self.assertIn(("evidence_unavailable", "evidence:ev.missing"), _findings(report))
        self.assertIn(("verification_evidence_missing", "verification:check.delta"), _findings(report))
        self.assertEqual("uncovered", report["coverage"][0]["status"])
        self.assertEqual("covered", report["coverage"][1]["status"])

    def test_unreferenced_evidence_must_still_verify(self):
        manifest = _case("clear-change")
        manifest["evidence"].append(
            {"id": "ev.unused", "path": "evidence/unused.txt", "sha256": hashlib.sha256(b"unused").hexdigest()}
        )

        report = audit_manifest(manifest, FIXTURE_ROOT)

        self.assertEqual("fail", report["status"])
        self.assertIn(("evidence_unavailable", "evidence:ev.unused"), _findings(report))
        self.assertEqual("covered", report["coverage"][0]["status"])

    def test_changed_artifact_bytes_fail_without_exposing_content(self):
        manifest = _case("clear-change")
        secret = b"synthetic changed bytes must not appear in report"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_evidence(root)
            (root / "evidence" / "task-artifact.txt").write_bytes(secret)

            report = audit_manifest(manifest, root)

        output = json.dumps(report)
        self.assertIn(("evidence_changed", "evidence:ev.task"), _findings(report))
        self.assertEqual("uncovered", report["coverage"][0]["status"])
        self.assertNotIn(str(root), output)
        self.assertNotIn(secret.decode(), output)

    def test_unsafe_paths_and_nul_are_sanitized_unavailable_findings(self):
        for unsafe_path in ("../outside-secret.txt", "C:/private", "file:///private", "a//b", "./file", "a\\b", "evidence\0bad"):
            with self.subTest(path=repr(unsafe_path)):
                manifest = _case("clear-change")
                manifest["evidence"][0]["path"] = unsafe_path
                report = audit_manifest(manifest, FIXTURE_ROOT)
                output = json.dumps(report)

                self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))
                self.assertNotIn(unsafe_path, output)
                self.assertNotIn(str(FIXTURE_ROOT), output)

    def test_traversal_does_not_open_an_outside_file(self):
        manifest = _case("clear-change")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            root.mkdir()
            _copy_evidence(root)
            outside = base / "outside.txt"
            outside.write_text("outside content", encoding="utf-8")
            manifest["evidence"][0]["path"] = "../outside.txt"
            opened: list[Path] = []
            original_open = Path.open

            def tracked_open(path: Path, *args: Any, **kwargs: Any):
                opened.append(path)
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", tracked_open):
                report = audit_manifest(manifest, root)

            self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))
            self.assertNotIn(outside.resolve(), [path.resolve() for path in opened])

    def test_safe_internal_symlink_passes_and_external_symlink_is_not_opened(self):
        manifest = _case("clear-change")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            root.mkdir()
            _copy_evidence(root)
            link = root / "evidence" / "spec-link.txt"
            outside = base / "outside.txt"
            safe_target = root / "evidence" / "specification.txt"
            try:
                os.symlink(safe_target, link)
                has_symlink_support = True
            except (OSError, NotImplementedError):
                has_symlink_support = False
            manifest["evidence"][0]["path"] = "evidence/spec-link.txt"
            if has_symlink_support:
                self.assertEqual("pass", audit_manifest(manifest, root)["status"])
            else:
                original_resolve = Path.resolve

                def resolve_safe(path: Path, *, strict: bool = False) -> Path:
                    return safe_target if path == link else original_resolve(path, strict=strict)

                with patch.object(Path, "resolve", resolve_safe):
                    self.assertEqual("pass", audit_manifest(manifest, root)["status"])

            outside.write_bytes(safe_target.read_bytes())
            if has_symlink_support:
                link.unlink()
                os.symlink(outside, link)
            outside_resolved = outside.resolve(strict=True)
            read_lengths: list[int] = []

            original_read = os.read
            original_resolve = Path.resolve

            def tracked_read(fd: int, size: int) -> bytes:
                content = original_read(fd, size)
                read_lengths.append(len(content))
                return content

            def resolve_external(path: Path, *, strict: bool = False) -> Path:
                return outside_resolved if path == link else original_resolve(path, strict=strict)

            with patch.object(os, "read", tracked_read), patch.object(Path, "resolve", resolve_external):
                report = audit_manifest(manifest, root)

            self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))
            self.assertEqual(2, read_lengths.count(0))
            self.assertNotIn(str(outside_resolved), json.dumps(report))

    @unittest.skipUnless(os.name == "nt", "Win32 handle-boundary regression")
    def test_opened_handle_outside_root_is_rejected_after_path_resolution(self):
        import ctypes

        manifest = _case("clear-change")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            root.mkdir()
            _copy_evidence(root)
            target = root / "evidence" / "specification.txt"
            outside = base / "outside.txt"
            outside.write_bytes(target.read_bytes())
            real_api = sdd_audit._windows_kernel32()
            outside_handle = real_api.CreateFileW(
                str(outside), 0x80000000, 0x00000001, None, 3, 0x80, None
            )
            invalid_handle = ctypes.c_void_p(-1).value
            outside_value = outside_handle if isinstance(outside_handle, int) else outside_handle.value
            self.assertNotIn(outside_value, (None, invalid_handle))

            class RedirectedKernel:
                def __getattr__(self, name: str):
                    return getattr(real_api, name)

                def CreateFileW(self, path: str, *args: Any):
                    if Path(path) == target:
                        return outside_handle
                    return real_api.CreateFileW(path, *args)

            read_lengths: list[int] = []
            original_read = os.read

            def tracked_read(fd: int, size: int) -> bytes:
                content = original_read(fd, size)
                read_lengths.append(len(content))
                return content

            with patch.object(sdd_audit, "_windows_kernel32", return_value=RedirectedKernel()), patch.object(
                os, "read", tracked_read
            ):
                report = audit_manifest(manifest, root)

        self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))
        self.assertEqual(2, read_lengths.count(0))

    @unittest.skipUnless(os.name == "nt", "Win32 special-file type regression")
    def test_opened_non_disk_handle_is_rejected_before_reading(self):
        manifest = _case("clear-change")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_evidence(root)
            target = root / "evidence" / "specification.txt"
            real_api = sdd_audit._windows_kernel32()
            target_handle = None

            class PipeTypeKernel:
                target_opened = False

                def __getattr__(self, name: str):
                    return getattr(real_api, name)

                def CreateFileW(self, path: str, *args: Any):
                    nonlocal target_handle
                    handle = real_api.CreateFileW(path, *args)
                    if Path(path) != root:
                        target_handle = handle if Path(path) == target else None
                        if Path(path) == target:
                            self.target_opened = True
                    return handle

                def GetFileType(self, handle: Any) -> int:
                    value = handle if isinstance(handle, int) else handle.value
                    target_value = target_handle if isinstance(target_handle, int) else getattr(target_handle, "value", None)
                    return 3 if target_value is not None and value == target_value else real_api.GetFileType(handle)

            read_lengths: list[int] = []
            original_read = os.read

            def tracked_read(fd: int, size: int) -> bytes:
                content = original_read(fd, size)
                read_lengths.append(len(content))
                return content

            api = PipeTypeKernel()
            with patch.object(sdd_audit, "_windows_kernel32", return_value=api), patch.object(
                os, "read", tracked_read
            ):
                report = audit_manifest(manifest, root)

            self.assertTrue(api.target_opened)

        self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))
        self.assertEqual(2, read_lengths.count(0))

    @unittest.skipUnless(os.name == "nt", "Win32 root-handle regression")
    def test_windows_root_reparse_handle_is_rejected_without_delete_sharing(self):
        import ctypes

        manifest = _case("clear-change")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_evidence(root)
            real_api = sdd_audit._windows_kernel32()

            class ReparseRootKernel:
                def __init__(self):
                    self.root_handle = None
                    self.root_flags = None
                    self.root_share = None

                def __getattr__(self, name: str):
                    return getattr(real_api, name)

                def CreateFileW(self, path: str, access: int, share: int, security: Any, disposition: int, flags: int, template: Any):
                    handle = real_api.CreateFileW(path, access, share, security, disposition, flags, template)
                    if Path(path) == root:
                        self.root_handle = handle
                        self.root_flags = flags
                        self.root_share = share
                    return handle

                def GetFileInformationByHandle(self, handle: Any, info: Any) -> bool:
                    result = real_api.GetFileInformationByHandle(handle, info)
                    if result and handle == self.root_handle:
                        attributes = ctypes.cast(info, ctypes.POINTER(ctypes.c_uint32))
                        attributes[0] |= 0x00000400
                    return result

            api = ReparseRootKernel()
            with patch.object(sdd_audit, "_windows_kernel32", return_value=api):
                report = audit_manifest(manifest, root)

        self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))
        self.assertTrue(api.root_flags & 0x00200000)
        self.assertFalse(api.root_share & 0x00000004)

    @unittest.skipUnless(os.name == "nt", "Win32 root-ancestor containment regression")
    def test_windows_root_handle_redirected_to_outside_directory_is_rejected_before_read(self):
        manifest = _case("clear-change")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            outside_root = base / "outside-root"
            root.mkdir()
            outside_root.mkdir()
            _copy_evidence(root)
            _copy_evidence(outside_root)
            real_api = sdd_audit._windows_kernel32()

            class RedirectedRootKernel:
                def __getattr__(self, name: str):
                    return getattr(real_api, name)

                def CreateFileW(self, path: str, *args: Any):
                    path_obj = Path(path)
                    if path_obj == root:
                        return real_api.CreateFileW(str(outside_root), *args)
                    if path_obj.is_relative_to(root):
                        return real_api.CreateFileW(str(outside_root / path_obj.relative_to(root)), *args)
                    return real_api.CreateFileW(path, *args)

            read_lengths: list[int] = []
            original_read = os.read

            def tracked_read(fd: int, size: int) -> bytes:
                content = original_read(fd, size)
                read_lengths.append(len(content))
                return content

            with patch.object(sdd_audit, "_windows_kernel32", return_value=RedirectedRootKernel()), patch.object(
                os, "read", tracked_read
            ):
                report = audit_manifest(manifest, root)

        self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))
        self.assertEqual([], read_lengths)

    @unittest.skipUnless(os.name == "nt", "Win32 case-sensitive path boundary regression")
    def test_windows_containment_does_not_fold_case_distinct_siblings(self):
        manifest = _case("clear-change")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_evidence(root)
            target = root / "evidence" / "specification.txt"
            real_api = sdd_audit._windows_kernel32()

            class CaseDistinctKernel:
                def __init__(self):
                    self.root_handle = None
                    self.file_handle = None

                def __getattr__(self, name: str):
                    return getattr(real_api, name)

                def CreateFileW(self, path: str, *args: Any):
                    handle = real_api.CreateFileW(path, *args)
                    if Path(path) == root:
                        self.root_handle = handle
                    elif Path(path) == target:
                        self.file_handle = handle
                    return handle

                def GetFinalPathNameByHandleW(self, handle: Any, buffer: Any, size: int, flags: int) -> int:
                    root_value = self.root_handle if isinstance(self.root_handle, int) else getattr(self.root_handle, "value", None)
                    handle_value = handle if isinstance(handle, int) else getattr(handle, "value", None)
                    path = "\\\\?\\" + str(root) if handle_value == root_value else (
                        "\\\\?\\" + str(root.parent / root.name.swapcase() / "evidence" / "specification.txt")
                    )
                    for index, character in enumerate(path):
                        buffer[index] = character
                    buffer[len(path)] = "\0"
                    return len(path)

            with patch.object(sdd_audit, "_windows_kernel32", return_value=CaseDistinctKernel()):
                report = audit_manifest(manifest, root)

        self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))

    @unittest.skipUnless(os.name == "posix", "POSIX descriptor-relative race regression")
    def test_posix_open_rejects_outside_symlink_substitution_before_read(self):
        manifest = _case("clear-change")
        self._assert_posix_substitution_rejected(manifest, replacement_kind="outside")

    @unittest.skipUnless(os.name == "posix", "POSIX special-file regression")
    def test_posix_open_rejects_special_file_substitution_before_read(self):
        manifest = _case("clear-change")
        manifest["evidence"][0]["sha256"] = hashlib.sha256(b"").hexdigest()
        self._assert_posix_substitution_rejected(manifest, replacement_kind="special")

    @unittest.skipUnless(os.name == "posix", "POSIX root-ancestor containment regression")
    def test_posix_root_ancestor_symlink_substitution_is_rejected(self):
        manifest = _case("clear-change")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            parent = base / "container"
            root = parent / "root"
            root.mkdir(parents=True)
            outside_parent = base / "outside"
            outside_root = outside_parent / "root"
            outside_root.mkdir(parents=True)
            _copy_evidence(root)
            _copy_evidence(outside_root)
            probe = base / "symlink-probe"
            try:
                os.symlink(outside_parent, probe, target_is_directory=True)
                probe.unlink()
            except (OSError, NotImplementedError):
                self.skipTest("temporary directory symlink creation is unavailable")

            target = root / "evidence" / "specification.txt"
            saved_parent = base / "container-original"
            original_resolve = Path.resolve
            original_open = Path.open
            path_opens: list[Path] = []
            swapped = False

            def swap_after_candidate_resolve(path: Path, *, strict: bool = False) -> Path:
                nonlocal swapped
                resolved = original_resolve(path, strict=strict)
                if path == target and not swapped:
                    parent.rename(saved_parent)
                    os.symlink(outside_parent, parent, target_is_directory=True)
                    swapped = True
                return resolved

            def tracked_open(path: Path, *args: Any, **kwargs: Any):
                path_opens.append(path)
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "resolve", swap_after_candidate_resolve), patch.object(Path, "open", tracked_open):
                report = audit_manifest(manifest, root)

        self.assertTrue(swapped)
        self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))
        self.assertEqual([], path_opens)

    def _assert_posix_substitution_rejected(self, manifest: dict, *, replacement_kind: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            root.mkdir()
            _copy_evidence(root)
            target = root / "evidence" / "specification.txt"
            if replacement_kind == "outside":
                replacement = base / "outside.txt"
                replacement.write_bytes(target.read_bytes())
            else:
                replacement = Path("/dev/null")
                if not replacement.exists():
                    self.skipTest("/dev/null is unavailable")
            probe = base / "symlink-probe"
            try:
                os.symlink(replacement, probe)
                probe.unlink()
            except (OSError, NotImplementedError):
                self.skipTest("temporary symlink creation is unavailable")

            original_path_open = Path.open
            original_os_open = os.open
            swapped = False

            def substitute() -> None:
                nonlocal swapped
                if not swapped:
                    target.unlink()
                    os.symlink(replacement, target)
                    swapped = True

            def intercepted_path_open(path: Path, *args: Any, **kwargs: Any):
                if path == target:
                    substitute()
                return original_path_open(path, *args, **kwargs)

            def intercepted_os_open(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None):
                if dir_fd is not None and path == target.name:
                    substitute()
                if dir_fd is None:
                    return original_os_open(path, flags, mode)
                return original_os_open(path, flags, mode, dir_fd=dir_fd)

            try:
                with patch.object(Path, "open", intercepted_path_open), patch.object(os, "open", intercepted_os_open):
                    report = audit_manifest(manifest, root)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"temporary symlink is unavailable: {type(exc).__name__}")

        self.assertTrue(swapped)
        self.assertIn(("evidence_unavailable", "evidence:ev.spec"), _findings(report))

    def test_mapping_validation_rejects_schema_errors_with_one_sanitized_message(self):
        base = _case("clear-change")
        mutations = []

        document = copy.deepcopy(base)
        document["schema_version"] = True
        mutations.append(("boolean version", document))
        document = copy.deepcopy(base)
        document["schema_version"] = 2
        mutations.append(("unsupported version", document))
        document = copy.deepcopy(base)
        document["extra"] = "not accepted"
        mutations.append(("unknown root field", document))
        document = copy.deepcopy(base)
        document["requirements"] = []
        mutations.append(("empty collection", document))
        document = copy.deepcopy(base)
        document["requirements"][0]["extra"] = 1
        mutations.append(("unknown record field", document))
        document = copy.deepcopy(base)
        document["requirements"][0]["id"] = "bad id"
        mutations.append(("invalid id", document))
        document = copy.deepcopy(base)
        document["requirements"].append(copy.deepcopy(document["requirements"][0]))
        mutations.append(("duplicate id", document))
        for collection in ("tasks", "verifications", "evidence"):
            document = copy.deepcopy(base)
            document[collection].append(copy.deepcopy(document[collection][0]))
            mutations.append((f"duplicate {collection} id", document))
        document = copy.deepcopy(base)
        document["tasks"][0]["requirement_ids"] = ["req.clear", "req.clear"]
        mutations.append(("duplicate reference", document))
        document = copy.deepcopy(base)
        document["tasks"][0]["verification_ids"] = ["check.clear", "check.clear"]
        mutations.append(("duplicate task verification reference", document))
        document = copy.deepcopy(base)
        document["verifications"][0]["requirement_ids"] = ["req.clear", "req.clear"]
        mutations.append(("duplicate check requirement reference", document))
        document = copy.deepcopy(base)
        document["verifications"][0]["evidence_ids"] = ["ev.check", "ev.check"]
        mutations.append(("duplicate check evidence reference", document))
        document = copy.deepcopy(base)
        document["tasks"][0]["status"] = "done"
        mutations.append(("invalid status", document))
        document = copy.deepcopy(base)
        document["evidence"][0]["sha256"] = "A" * 64
        mutations.append(("invalid digest", document))
        document = copy.deepcopy(base)
        document["tasks"] = {"id": "wrong type"}
        mutations.append(("wrong collection type", document))

        for label, document in mutations:
            with self.subTest(mutation=label), self.assertRaisesRegex(ValueError, "^invalid audit manifest$"):
                audit_manifest(document, FIXTURE_ROOT)

    def test_unknown_references_and_failure_statuses_are_findings(self):
        manifest = _case("clear-change")
        manifest["requirements"][0]["specification_evidence_id"] = "ev.missing"
        manifest["tasks"][0]["requirement_ids"] = ["req.missing"]
        manifest["tasks"][0]["verification_ids"] = ["check.missing"]
        manifest["verifications"][0]["requirement_ids"] = ["req.missing"]
        manifest["verifications"][0]["status"] = "fail"

        report = audit_manifest(manifest, FIXTURE_ROOT)
        findings = _findings(report)

        self.assertIn(("unknown_evidence", "evidence:ev.missing"), findings)
        self.assertIn(("unknown_requirement", "requirement:req.missing"), findings)
        self.assertIn(("unknown_verification", "verification:check.missing"), findings)
        self.assertIn(("verification_not_passed", "verification:check.clear"), findings)
        self.assertIn(("verification_unlinked", "verification:check.clear"), findings)

    def test_loader_rejects_duplicate_keys_malformed_deep_invalid_and_oversized_files(self):
        invalid_contents = (
            b'{"schema_version":1,"schema_version":1}',
            b'{"schema_version":1,"nested":{"same":1,"same":2}}',
            b"{not json",
            b"\xff",
            b"[" * 2000 + b"]" * 2000,
            b" " * (MAX_MANIFEST_BYTES + 1),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            with self.assertRaisesRegex(ValueError, "^invalid audit manifest$"):
                load_audit_manifest(path)
            for index, content in enumerate(invalid_contents):
                with self.subTest(index=index):
                    path.write_bytes(content)
                    with self.assertRaisesRegex(ValueError, "^invalid audit manifest$"):
                        load_audit_manifest(path)

    def test_manifest_loader_reads_at_most_one_mebibyte_plus_one_byte(self):
        read_sizes: list[int] = []

        class OversizedStream(io.BytesIO):
            def read(self, size: int = -1) -> bytes:
                read_sizes.append(size)
                return super().read(size)

        stream = OversizedStream(b" " * (MAX_MANIFEST_BYTES + 1))
        with patch.object(Path, "open", return_value=stream):
            with self.assertRaisesRegex(ValueError, "^invalid audit manifest$"):
                load_audit_manifest("manifest.json")

        self.assertEqual([MAX_MANIFEST_BYTES + 1], read_sizes)

    def test_evidence_reader_requests_at_most_eight_mebibytes_plus_one_byte(self):
        reads: list[tuple[int, int]] = []
        original_read = os.read

        def tracked_read(fd: int, size: int) -> bytes:
            content = original_read(fd, size)
            reads.append((size, len(content)))
            return content

        with patch.object(os, "read", tracked_read):
            report = audit_manifest(_case("clear-change"), FIXTURE_ROOT)

        self.assertEqual("pass", report["status"])
        groups: list[list[tuple[int, int]]] = []
        current: list[tuple[int, int]] = []
        for item in reads:
            current.append(item)
            if item[1] == 0:
                groups.append(current)
                current = []
        self.assertEqual(3, len(groups))
        self.assertTrue(all(size <= MAX_EVIDENCE_BYTES + 1 for group in groups for size, _ in group))
        self.assertTrue(all(sum(length for _, length in group) <= MAX_EVIDENCE_BYTES + 1 for group in groups))

    def test_short_reads_are_retried_until_the_evidence_is_complete(self):
        reads: list[tuple[int, int]] = []
        original_read = os.read

        def short_first_read(fd: int, size: int) -> bytes:
            limit = min(size, 5) if size == MAX_EVIDENCE_BYTES + 1 else size
            content = original_read(fd, limit)
            reads.append((limit, len(content)))
            return content

        with patch.object(os, "read", short_first_read):
            report = audit_manifest(_case("clear-change"), FIXTURE_ROOT)

        self.assertEqual("pass", report["status"])
        self.assertGreaterEqual(len(reads), 9)


if __name__ == "__main__":
    unittest.main()
