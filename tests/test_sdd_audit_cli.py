from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from inonu_harness.baseline import run_fixture
from inonu_harness.cli import main
from inonu_harness.sdd_audit import audit_manifest, load_audit_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_FIXTURE_ROOT = REPO_ROOT / "fixtures" / "sdd_audit"
AUDIT_CASES = {
    "clear-change": "pass",
    "ambiguous-change": "fail",
    "reproducible-bug": "pass",
    "specification-delta": "pass",
    "protected-action": "fail",
}


class RecordedSelfAuditTests(unittest.TestCase):
    def test_the_self_audit_recorded_for_milestone_8_still_passes(self):
        """audit.json pins the bytes of three files; an edit to any of them (a renumbering, a typo fix) must refresh the pins."""
        root = REPO_ROOT / "docs" / "specs" / "milestones" / "v0.0.8"
        report = audit_manifest(load_audit_manifest(root / "audit.json"), root)
        self.assertEqual("pass", report["status"], report)


class SddAuditCliTests(unittest.TestCase):
    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_audit_defaults_evidence_root_to_manifest_parent(self):
        source_manifest = load_audit_manifest(
            AUDIT_FIXTURE_ROOT / "clear-change" / "manifest.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence").mkdir()
            for name in ("specification.txt", "task-artifact.txt", "verification.txt"):
                shutil.copyfile(AUDIT_FIXTURE_ROOT / "evidence" / name, root / "evidence" / name)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(source_manifest), encoding="utf-8")

            code, output, error = self.run_cli(["sdd", "audit", str(manifest)])

        self.assertEqual((0, ""), (code, error))
        self.assertEqual("pass", json.loads(output)["status"])

    def test_audit_accepts_root_override_and_reports_findings(self):
        passing_manifest = AUDIT_FIXTURE_ROOT / "clear-change" / "manifest.json"
        code, output, error = self.run_cli([
            "sdd", "audit", str(passing_manifest), "--root", str(AUDIT_FIXTURE_ROOT)
        ])
        self.assertEqual((0, ""), (code, error))
        self.assertEqual("pass", json.loads(output)["status"])

        failing_manifest = AUDIT_FIXTURE_ROOT / "ambiguous-change" / "manifest.json"
        code, output, error = self.run_cli([
            "sdd", "audit", str(failing_manifest), "--root", str(AUDIT_FIXTURE_ROOT)
        ])
        report = json.loads(output)
        self.assertEqual((1, ""), (code, error))
        self.assertEqual("fail", report["status"])
        self.assertTrue(report["findings"])
        self.assertNotIn(str(AUDIT_FIXTURE_ROOT), output)

    def test_audit_invalid_file_inputs_return_sanitized_code_two(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate-secret-path.json"
            duplicate.write_text('{"private":"private-token","private":"other"}', encoding="utf-8")
            malformed = root / "malformed.json"
            malformed.write_text('{"private":"private-token",', encoding="utf-8")
            missing = root / "missing-private.json"

            for path in (duplicate, malformed, missing):
                with self.subTest(path=path.name):
                    code, output, error = self.run_cli(["sdd", "audit", str(path)])
                    self.assertEqual(2, code)
                    self.assertEqual("", output)
                    self.assertIn("invalid audit manifest", error)
                    self.assertNotIn(str(path), error)
                    self.assertNotIn("private-token", error)

    def test_baseline_records_computed_audit_report_outcomes_v1(self):
        for case, expected in AUDIT_CASES.items():
            with self.subTest(case=case):
                manifest_path = AUDIT_FIXTURE_ROOT / case / "manifest.json"
                report = audit_manifest(load_audit_manifest(manifest_path), AUDIT_FIXTURE_ROOT)
                fixture = {
                    "fixture_schema_version": 1,
                    "fixture_id": f"sdd-audit-{case}-v1",
                    "task_id": f"sdd.audit.{case}",
                    "config_id": "sdd.audit.cli.v1",
                    "runtime": None,
                    "model": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "cost_usd": None,
                    "tool_calls": [],
                    "failures": [],
                    "blocks": [],
                    "recoveries": [],
                    "acceptance": [
                        {"id": "audit-status-pass", "passed": report["status"] == "pass"},
                        {
                            "id": "all-requirements-covered",
                            "passed": all(row["status"] == "covered" for row in report["coverage"]),
                        },
                    ],
                    "measurement_sources": {
                        "acceptance": {"kind": "local-audit", "reference": f"audit-report:{case}"}
                    },
                }
                self.assertEqual(expected, report["status"])

                direct = run_fixture(fixture, execution_id=f"direct-{case}")
                with tempfile.TemporaryDirectory() as directory:
                    fixture_path = Path(directory) / "baseline.json"
                    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
                    code, output, error = self.run_cli([
                        "baseline", "run", str(fixture_path), "--execution-id", f"cli-{case}"
                    ])

                cli_result = json.loads(output)
                self.assertEqual((0, ""), (code, error))
                self.assertEqual(1, direct["schema_version"])
                self.assertEqual(1, cli_result["schema_version"])
                self.assertEqual(direct["metrics"]["acceptance"]["value"], cli_result["metrics"]["acceptance"]["value"])
                self.assertEqual("local-audit", cli_result["metrics"]["acceptance"]["source"]["kind"])
                self.assertEqual(f"audit-report:{case}", cli_result["metrics"]["acceptance"]["source"]["reference"])
                for name in ("runtime", "model", "input_tokens", "output_tokens", "cost_usd"):
                    self.assertIsNone(cli_result["metrics"][name]["value"])


if __name__ == "__main__":
    unittest.main()
