import unittest
from evals.harness.protocol_canary import validate_protocol_canary


ARMS = {
    "csharp-overdue-rule": ["core-only", "core-plus-csharp"],
    "fastapi-provider-boundary": ["core-only", "core-plus-python"],
    "typescript-runtime-validation": ["control", "generic-clean-code", "core-only", "core-plus-typescript"],
    "react-state-error-retention": ["core-only", "core-plus-typescript", "core-plus-typescript-plus-react"],
}


def documents():
    return [{"run_id": f"{scenario}--{arm}--r01", "scenario_id": scenario,
             "arm_id": arm, "repetition": 1, "terminal_state": "automatic_failure",
             "automatic_failure_reasons": ["acceptance_failed"],
             "inspection_diagnostics": [], "oracle_skipped_reason": "not_applicable",
             "oracle_results": [{"exit_code": 1}]}
            for scenario, arms in ARMS.items() for arm in arms]


class ProtocolCanaryTests(unittest.TestCase):
    def test_canary_runs_must_belong_to_the_expected_freeze(self):
        data = documents()
        for document in data:
            document["contract_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "contract"):
            validate_protocol_canary(data, expected_contract_sha256="a" * 64)
        self.assertEqual("passed", validate_protocol_canary(data, expected_contract_sha256="b" * 64)["status"])

    def test_behavior_failure_does_not_change_protocol_success(self):
        self.assertEqual("passed", validate_protocol_canary(documents())["status"])

    def test_missing_duplicate_or_formal_slots_cannot_be_canary(self):
        for invalid in (documents()[:-1], [*documents()[:-1], documents()[0]], documents() * 3):
            with self.assertRaises(ValueError):
                validate_protocol_canary(invalid)

    def test_evidence_failure_and_timeout_block_formal_pilot(self):
        for changes in (
            {"inspection_diagnostics": [{"code": "profile_contamination"}]},
            {"automatic_failure_reasons": ["invalid_claim"]},
            {"oracle_results": []}, {"terminal_state": "timeout"},
            {"oracle_skipped_reason": "not_run_due_to_evidence_gate"},
        ):
            data = documents()
            data[0].update(changes)
            result = validate_protocol_canary(data)
            self.assertEqual("failed", result["status"])
            self.assertEqual([data[0]["run_id"]], result["failed_run_ids"])
