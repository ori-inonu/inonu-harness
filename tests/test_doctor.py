import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inonu_harness.doctor import LocalProbe, collect_environment, load_manifest


FIXTURES = Path(__file__).parent / "fixtures" / "doctor"


class FixtureProbe:
    def __init__(self, filename):
        self.data = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))

    def snapshot(self):
        return self.data


class DoctorTests(unittest.TestCase):
    def _codegraph_report(
        self, *, manifest_updates=None, npm_timeout=False, executable_matches=True,
        manifest_text=None, npm_output=None,
    ):
        with tempfile.TemporaryDirectory() as temporary_dir:
            temporary_root = Path(temporary_dir)
            project_root = temporary_root / "project"
            user_root = temporary_root / "user"
            project_root.mkdir()
            user_root.mkdir()

            prefix = temporary_root / "npm-global"
            if os.name == "nt":
                npm_root = prefix / "node_modules"
                npm_bin = prefix
                extension = ".cmd"
            else:
                npm_root = prefix / "lib" / "node_modules"
                npm_bin = prefix / "bin"
                extension = ""
            package_dir = npm_root / "@lzehrung" / "codegraph"
            package_dir.mkdir(parents=True)
            manifest = {
                "name": "@lzehrung/codegraph",
                "version": "3.0.1",
                "license": "MIT",
                "repository": {"type": "git", "url": "git+https://github.com/lzehrung/codegraph.git"},
            }
            manifest.update(manifest_updates or {})
            (package_dir / "package.json").write_text(
                manifest_text if manifest_text is not None else json.dumps(manifest), encoding="utf-8"
            )

            codegraph_path = npm_bin / f"codegraph{extension}"
            if not executable_matches:
                codegraph_path = temporary_root / "other-bin" / f"codegraph{extension}"
            npm_path = temporary_root / f"npm{extension}"
            paths = {"codegraph": str(codegraph_path), "npm": str(npm_path)}
            calls = {"popen": [], "wait_timeouts": [], "kills": []}

            def fake_run(command, **kwargs):
                if command == [paths["codegraph"], "--version"]:
                    return subprocess.CompletedProcess(command, 0, stdout="codegraph 3.0.1\n", stderr="")
                raise AssertionError(f"unexpected subprocess: {command!r}")

            class FakeProcess:
                def __init__(self, command):
                    self.args = command
                    self.stdout = io.StringIO(npm_output if npm_output is not None else f"{npm_root}\n")
                    self.returncode = None

                def wait(self, timeout=None):
                    calls["wait_timeouts"].append(timeout)
                    if npm_timeout and self.returncode is None:
                        raise subprocess.TimeoutExpired(self.args, timeout)
                    if self.returncode is None:
                        self.returncode = 0
                    return self.returncode

                def kill(self):
                    calls["kills"].append(self.args)
                    self.returncode = -9

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_value, traceback):
                    self.stdout.close()

            def fake_popen(command, **kwargs):
                if command != [paths["npm"], "root", "-g"]:
                    raise AssertionError(f"unexpected process: {command!r}")
                calls["popen"].append((command, kwargs))
                return FakeProcess(command)

            def fake_which(name):
                return paths.get(name)

            with (
                patch("inonu_harness.doctor.platform_module.system", return_value="Windows" if os.name == "nt" else "Linux"),
                patch("inonu_harness.doctor.platform_module.release", return_value="test"),
                patch("inonu_harness.doctor.platform_module.machine", return_value="test"),
                patch("inonu_harness.doctor.shutil.which", side_effect=fake_which),
                patch("inonu_harness.doctor.subprocess.Popen", side_effect=fake_popen),
                patch("inonu_harness.doctor.subprocess.run", side_effect=fake_run),
            ):
                report = collect_environment(LocalProbe(project_root, user_root))

            return report, str(temporary_root), calls

    def test_codegraph_package_manifest_is_reported_only_when_it_matches_the_cli(self):
        report, temporary_path, calls = self._codegraph_report()
        encoded = json.dumps(report, sort_keys=True)

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(
            set(report["integrations"]["codegraph"]),
            {"installed", "configured", "operational", "documented", "license"},
        )
        self.assertEqual(report["integrations"]["codegraph"]["license"], {
            "value": "MIT",
            "source": "local_package_manifest",
            "upstream_value": "MIT",
            "upstream_source": "official_repository",
        })
        self.assertEqual(len(calls["popen"]), 1)
        command, kwargs = calls["popen"][0]
        self.assertEqual(command[1:], ["root", "-g"])
        self.assertFalse(kwargs.get("shell", False))
        self.assertIn(4, calls["wait_timeouts"])
        self.assertFalse(temporary_path in encoded)
        for raw_manifest_value in ("@lzehrung", "https://github.com/lzehrung", "package.json", '"repository":', '"url":'):
            self.assertFalse(raw_manifest_value in encoded)

    def test_codegraph_package_mismatches_and_unavailable_npm_stay_unknown(self):
        cases = (
            {"manifest_updates": {"name": "@example/codegraph"}},
            {"manifest_updates": {"version": "9.9.9"}},
            {"manifest_updates": {"repository": "https://github.com/example/codegraph"}},
            {"manifest_updates": {"license": "Apache-2.0"}},
            {"executable_matches": False},
            {"npm_timeout": True},
            {"npm_output": "x" * (4 * 1024 + 1)},
            {"manifest_text": "{not valid json"},
        )
        for case in cases:
            with self.subTest(case=case):
                report, temporary_path, _ = self._codegraph_report(**case)
                encoded = json.dumps(report, sort_keys=True)
                license_status = report["integrations"]["codegraph"]["license"]

                self.assertIsNone(license_status["value"])
                self.assertEqual(license_status["source"], "local_distribution_unverified")
                self.assertEqual(license_status["upstream_value"], "MIT")
                self.assertEqual(report["schema_version"], 1)
                self.assertEqual(
                    set(report["integrations"]["codegraph"]),
                    {"installed", "configured", "operational", "documented", "license"},
                )
                self.assertFalse(temporary_path in encoded)
                for raw_manifest_value in ("@lzehrung", "@example", "https://github.com", "package.json", '"repository":', '"url":'):
                    self.assertFalse(raw_manifest_value in encoded)

    def test_oversized_npm_root_output_is_terminated(self):
        _, _, calls = self._codegraph_report(npm_output="x" * (4 * 1024 + 1))

        self.assertEqual(len(calls["kills"]), 1)

    def test_report_is_allowlisted_json_with_provenance_and_unknowns(self):
        report = collect_environment(FixtureProbe("host_snapshot.json"))
        encoded = json.dumps(report, sort_keys=True)

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["runtime"]["platform"]["name"], "Windows")
        self.assertEqual(report["runtime"]["python"]["version"], "3.14.7")
        self.assertEqual(report["runtime"]["codex_cli"]["version"], "0.164.0-alpha.11.1")
        self.assertEqual(report["runtime"]["codex_cli"]["source"], "codex_cli_version")
        self.assertEqual(report["runtime"]["codex_desktop"]["state"], "unknown")
        self.assertIn("unknowns", report)
        for skill in report["skills"]:
            self.assertEqual(skill["state"], "installed")
            self.assertIn(skill["origin"], {"user_agents", "user_codex", "project_agents", "project_codex", "plugin_cache"})
            self.assertIn("version", skill)
            self.assertEqual(skill["session_availability"], {
                "state": "unknown",
                "source": "active_host_skill_catalog",
                "reason": "local_probe_cannot_prove_skill_loaded_in_session",
            })
            self.assertIn({
                "subject": f"skill:{skill['name']}:{skill['origin']}:session_availability",
                "reason": "local_probe_cannot_prove_skill_loaded_in_session",
            }, report["unknowns"])
        for forbidden in (
            "PRIVATE_JEV_COMMAND", "PRIVATE_JEV_SECRET", "PRIVATE_CODEGRAPH_COMMAND",
            "PRIVATE_ARGUMENT", "PRIVATE_BASH_HOOK", "PRIVATE_PS_HOOK",
            "PRIVATE_SESSION_HOOK", "PRIVATE_PROMPT_TEXT", "PRIVATE_DIRECT_SECRET",
            "PRIVATE_MCP_TOKEN", "PRIVATE_OTHER_HOOK.ps1", "PRIVATE_DUPLICATE_HOOK",
            "PRIVATE_USER", "private-workspace", "C:\\Users",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_required_integration_states_do_not_infer_mcp_accessibility(self):
        report = collect_environment(FixtureProbe("host_snapshot.json"))
        integrations = report["integrations"]

        for key in ("jev", "rtk", "headroom", "codegraph", "ponytail", "sequential_thinking"):
            self.assertEqual(set(integrations[key]), {"installed", "configured", "operational", "documented", "license"})
            for status_key in ("installed", "configured", "operational", "documented"):
                self.assertIn(integrations[key][status_key]["state"], {"installed", "configured", "operational", "documented", "not_found", "unknown"})
        self.assertEqual(integrations["jev"]["configured"]["state"], "configured")
        self.assertEqual(integrations["jev"]["operational"]["state"], "unknown")
        self.assertEqual(integrations["rtk"]["installed"]["state"], "installed")
        self.assertEqual(integrations["rtk"]["configured"]["state"], "configured")
        self.assertEqual(integrations["headroom"]["installed"]["state"], "installed")
        self.assertEqual(integrations["codegraph"]["configured"]["state"], "configured")
        self.assertIsNone(integrations["codegraph"]["license"]["value"])
        self.assertEqual(integrations["codegraph"]["license"]["source"], "local_distribution_unverified")
        self.assertEqual(integrations["codegraph"]["license"]["upstream_value"], "MIT")
        self.assertEqual(integrations["ponytail"]["installed"]["state"], "installed")
        self.assertEqual(integrations["ponytail"]["configured"]["state"], "unknown")
        self.assertEqual(integrations["sequential_thinking"]["configured"]["state"], "not_found")
        self.assertEqual(integrations["sequential_thinking"]["installed"]["state"], "unknown")
        self.assertEqual(integrations["sequential_thinking"]["operational"]["state"], "unknown")
        self.assertTrue(all(mcp["accessibility"]["state"] == "unknown" for mcp in report["mcps"]))
        self.assertTrue(all(mcp["accessibility"]["source"] == "local_cli_cannot_prove_session_access" for mcp in report["mcps"]))

    def test_conflicts_and_hook_shell_compatibility_are_structural_only(self):
        report = collect_environment(FixtureProbe("host_snapshot.json"))

        self.assertTrue(any(item["type"] == "mcp_name_in_multiple_scopes" and item["name"] == "codegraph" for item in report["findings"]))
        self.assertTrue(any(item["type"] == "repeated_hook_event_matcher" and item["severity"] == "possible_redundancy" for item in report["findings"]))
        hooks = report["hooks"]["entries"]
        bash_hook = next(hook for hook in hooks if hook["matcher"] == "bash")
        powershell_hook = next(hook for hook in hooks if hook["matcher"] == "powershell")
        generic_hook = next(hook for hook in hooks if hook["event"] == "SessionStart")
        self.assertEqual(bash_hook["compatibility"]["bash"]["state"], "compatible")
        self.assertEqual(bash_hook["compatibility"]["powershell"]["state"], "incompatible")
        self.assertEqual(powershell_hook["compatibility"]["powershell"]["state"], "compatible")
        self.assertEqual(powershell_hook["compatibility"]["bash"]["state"], "incompatible")
        self.assertEqual(generic_hook["compatibility"]["powershell"]["state"], "unknown")
        self.assertTrue(all("command" not in json.dumps(hook).lower() for hook in hooks))

    def test_unavailable_probes_are_unknown_and_have_no_exception_text(self):
        report = collect_environment(FixtureProbe("unavailable_snapshot.json"))

        self.assertEqual(report["runtime"]["codex_cli"]["state"], "unknown")
        self.assertEqual(report["configurations"]["global"]["state"], "unknown")
        self.assertEqual(report["configurations"]["project"]["state"], "not_found")
        self.assertEqual(report["mcp_registry"]["state"], "unknown")
        self.assertEqual(report["hooks"]["state"], "unknown")
        self.assertEqual(report["integrations"]["jev"]["configured"]["state"], "unknown")
        self.assertEqual(report["integrations"]["rtk"]["configured"]["state"], "unknown")
        self.assertEqual(report["integrations"]["ponytail"]["installed"]["state"], "unknown")
        self.assertNotIn("Traceback", json.dumps(report))

    def test_manifest_separates_intent_from_environment_observations(self):
        manifest = load_manifest()
        self.assertEqual(manifest["schema_version"], 1)
        self.assertIn("observations", manifest)
        self.assertIn("populated_by", manifest["observations"])
        for integration in manifest["integrations"]:
            intent = integration["intent"]
            for field in ("purpose", "input_contract", "output_contract", "candidate_function", "dependencies", "overlap", "license", "test", "implementation_trigger"):
                self.assertIn(field, intent)
            self.assertNotIn("operational_state", intent)
            self.assertIn(integration["id"], ("jev", "rtk", "headroom", "codegraph", "ponytail", "sequential_thinking"))


if __name__ == "__main__":
    unittest.main()
