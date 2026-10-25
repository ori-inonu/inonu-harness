import json
import unittest
from pathlib import Path

from inonu_harness.doctor import collect_environment, load_manifest


FIXTURES = Path(__file__).parent / "fixtures" / "doctor"


class FixtureProbe:
    def __init__(self, filename):
        self.data = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))

    def snapshot(self):
        return self.data


class DoctorTests(unittest.TestCase):
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
