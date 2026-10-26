import unittest

from inonu_harness.jev import (
    JevAdapter,
    MockJevTransport,
    TransportUnavailable,
)


def spec(**changes):
    value = {
        "id": "store-choice",
        "goal": "Choose local persistence",
        "facts": {"runtime": "python-stdlib"},
        "rails": ["No remote service"],
        "options": [
            {"id": "sqlite", "label": "SQLite", "what": "Persist locally"},
            {"id": "json", "label": "JSON", "what": "Use a local file"},
        ],
    }
    value.update(changes)
    return value


def plan(spec_id="store-choice"):
    return {"specId": spec_id, "plannedCalls": 12, "estimatedInputTokens": 500}


def run_receipt(*, status="consenso", leader="sqlite", implement=True):
    return {
        "receipt": {
            "v": 1,
            "specId": "store-choice",
            "specHash": "a" * 64,
            "status": status,
            "leader": leader,
            "implement": implement,
            "rounds": [{"private_detail": "must not be retained"}],
        },
        "meter": {"calls": 12},
        "disclaimer": "Recommendation only.",
    }


class JevAdapterTests(unittest.TestCase):
    def test_calls_plan_then_run_with_same_validated_spec_and_omits_max_calls(self):
        transport = MockJevTransport({"consensus_plan": plan(), "consensus_run": run_receipt()})
        adapter = JevAdapter(transport, server_version="0.1.0")

        result = adapter.recommend(spec())

        self.assertEqual(["consensus_plan", "consensus_run"], [name for name, _, _ in transport.calls])
        planned_spec = transport.calls[0][1]["spec"]
        run_spec = transport.calls[1][1]["spec"]
        self.assertIs(planned_spec, run_spec)
        self.assertEqual(spec(), planned_spec)
        self.assertEqual({"spec"}, set(transport.calls[0][1]))
        self.assertEqual({"spec"}, set(transport.calls[1][1]))
        self.assertEqual([20.0, 20.0], [timeout for _, _, timeout in transport.calls])
        self.assertEqual("recommended", result.status)
        self.assertEqual("sqlite", result.recommendation.alternative_id)
        self.assertEqual("a" * 64, result.recommendation.spec_hash)
        self.assertEqual("0.1.0", result.recommendation.version)
        self.assertIn("specHash=" + "a" * 64, result.recommendation.provenance)
        self.assertNotIn("rounds", result.to_dict())

    def test_sends_only_schema_fields_and_rejects_secrets(self):
        supplied = spec(extra="must not reach JEV")
        transport = MockJevTransport({"consensus_plan": plan(), "consensus_run": run_receipt()})

        result = JevAdapter(transport).recommend(supplied)

        self.assertEqual("recommended", result.status)
        self.assertNotIn("extra", transport.calls[0][1]["spec"])
        for dirty in (
            spec(facts={"credential": "api_key=abc"}),
            spec(goal="Use sk-abcdefghijklmnopqrstuvwxyz123456"),
        ):
            with self.subTest(dirty=dirty):
                with self.assertRaises(ValueError):
                    JevAdapter(transport).recommend(dirty)

    def test_rejects_bad_spec_without_calling_transport(self):
        transport = MockJevTransport()
        with self.assertRaises(ValueError):
            JevAdapter(transport).recommend(spec(options=[{"id": "one"}]))
        self.assertEqual([], transport.calls)

    def test_forbidden_or_unknown_leaders_never_become_recommendations(self):
        for leader, forbidden in (("sqlite", ["sqlite"]), ("other", [])):
            with self.subTest(leader=leader):
                transport = MockJevTransport(
                    {"consensus_plan": plan(), "consensus_run": run_receipt(leader=leader)}
                )
                result = JevAdapter(transport).recommend(spec(forbidden=forbidden))
                self.assertEqual("invalid_response", result.status)
                self.assertIsNone(result.recommendation)

    def test_valid_non_consensus_is_explicit_and_does_not_recommend(self):
        for status in ("sem_consenso", "sem_opcoes", "juiz_falhou"):
            with self.subTest(status=status):
                transport = MockJevTransport(
                    {"consensus_plan": plan(), "consensus_run": run_receipt(status=status, leader=None, implement=False)}
                )
                result = JevAdapter(transport).recommend(spec())
                self.assertEqual("no_consensus", result.status)
                self.assertEqual(status, result.source_status)
                self.assertIsNone(result.recommendation)

    def test_bad_plan_receipt_and_bad_run_schema_are_invalid(self):
        transport = MockJevTransport({"consensus_plan": {"specId": "other", "plannedCalls": 0}})
        bad_plan = JevAdapter(transport).recommend(spec())
        self.assertEqual("invalid_response", bad_plan.status)
        self.assertEqual(["consensus_plan"], [name for name, _, _ in transport.calls])

        for response in ({"receipt": {"status": "consenso"}}, {"receipt": run_receipt()["receipt"] | {"implement": False}}):
            with self.subTest(response=response):
                transport = MockJevTransport({"consensus_plan": plan(), "consensus_run": response})
                result = JevAdapter(transport).recommend(spec())
                self.assertEqual("invalid_response", result.status)
                self.assertIsNone(result.recommendation)

    def test_timeout_unavailable_refusal_and_malformed_json_are_distinct(self):
        timeout_transport = MockJevTransport(errors={"consensus_plan": TimeoutError()})
        self.assertEqual("timeout", JevAdapter(timeout_transport).recommend(spec()).status)

        unavailable_transport = MockJevTransport(errors={"consensus_run": TransportUnavailable()})
        self.assertEqual("unavailable", JevAdapter(unavailable_transport).recommend(spec()).status)

        refusal_transport = MockJevTransport(
            {"consensus_plan": plan(), "consensus_run": {"isError": True, "content": []}}
        )
        self.assertEqual("refused", JevAdapter(refusal_transport).recommend(spec()).status)

        malformed_transport = MockJevTransport(
            {"consensus_plan": plan(), "consensus_run": {"content": [{"type": "text", "text": "not-json"}]}}
        )
        self.assertEqual("invalid_response", JevAdapter(malformed_transport).recommend(spec()).status)

    def test_plan_prevents_run_when_no_option_is_allowed(self):
        transport = MockJevTransport(
            {"consensus_plan": {"specId": "store-choice", "plannedCalls": 0, "estimatedInputTokens": 0}}
        )
        result = JevAdapter(transport).recommend(spec(forbidden=["sqlite", "json"]))
        self.assertEqual("no_consensus", result.status)
        self.assertEqual(["consensus_plan"], [name for name, _, _ in transport.calls])
if __name__ == "__main__":
    unittest.main()
