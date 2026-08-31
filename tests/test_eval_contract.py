import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals"
MANIFEST_PATH = EVAL_ROOT / "manifest.json"
RUBRIC_NAMES = {
    "context-and-locality.md",
    "behavior-and-validation.md",
    "decision-and-escalation.md",
}
ARM_IDS = {"control", "generic-clean-code", "skill-v0.2.0"}
SCENARIO_IDS = {
    "context-locality",
    "behavior-validation",
    "dependency-boundary",
    "concurrency-side-effects",
}
RESULT_REQUIRED_FIELDS = {
    "schema_version",
    "benchmark_version",
    "run_id",
    "date",
    "executor",
    "skill_version",
    "arm_id",
    "scenario_id",
    "repository_url",
    "commit",
    "working_tree_status",
    "model",
    "reasoning_effort",
    "client",
    "tool_permissions",
    "prompt",
    "loaded_skill_references",
    "raw_output",
    "files_inspected",
    "files_modified",
    "files_validated",
    "diff",
    "commands",
    "environment",
    "exit_codes",
    "artifacts",
    "oracle_results",
    "rubric_results",
    "blind_spots",
    "human_decisions_required",
    "token_telemetry",
    "tool_calls",
    "elapsed_time",
    "generated_lines",
}


class EvalContractTests(unittest.TestCase):
    def load_manifest(self) -> dict:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_defines_fixed_arms_and_scenarios(self) -> None:
        manifest = self.load_manifest()
        self.assertEqual(ARM_IDS, {item["id"] for item in manifest["arms"]})
        self.assertEqual(
            SCENARIO_IDS,
            {item["id"] for item in manifest["scenarios"]},
        )
        self.assertEqual(5, manifest["repetitions"]["micro"])
        self.assertEqual(3, manifest["repetitions"]["repository"])

    def test_every_scenario_is_reproducible(self) -> None:
        for scenario in self.load_manifest()["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                self.assertRegex(scenario["commit"], r"^[0-9a-f]{40}$")
                self.assertTrue(scenario["task"].strip())
                self.assertTrue(scenario["gold_files"])
                self.assertTrue(scenario["allowed_diff"])
                self.assertIn(
                    "dotnet test AiCleanCode.sln --no-restore",
                    scenario["oracle_commands"],
                )
                self.assertEqual(RUBRIC_NAMES, set(scenario["rubrics"]))

    def test_result_contract_requires_fresh_context_evidence(self) -> None:
        manifest = self.load_manifest()
        benchmark = (EVAL_ROOT / "benchmark.md").read_text(encoding="utf-8")

        self.assertEqual(RESULT_REQUIRED_FIELDS, set(manifest["result_required_fields"]))
        self.assertIn("`result_required_fields`", benchmark)

    def test_scenario_paths_match_fixture_snapshots(self) -> None:
        allowed_prefixes = (
            "src/WorkItems.Api/",
            "tests/WorkItems.Api.Tests/",
        )
        retired_prefixes = ("src/AiCleanCode.", "tests/AiCleanCode.")

        for scenario in self.load_manifest()["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                fixture_files = set(scenario["fixture_files"])
                self.assertTrue(set(scenario["gold_files"]).issubset(fixture_files))
                for path in [
                    *fixture_files,
                    *scenario["gold_files"],
                    *scenario["allowed_diff"],
                ]:
                    self.assertTrue(path.startswith(allowed_prefixes))
                    self.assertFalse(path.startswith(retired_prefixes))

    def test_rubric_files_exist_and_define_scoring(self) -> None:
        actual = {path.name for path in (EVAL_ROOT / "rubrics").glob("*.md")}
        self.assertEqual(RUBRIC_NAMES, actual)
        for path in (EVAL_ROOT / "rubrics").glob("*.md"):
            content = path.read_text(encoding="utf-8")
            self.assertIn("## Scoring", content)
            self.assertIn("## Evidence Required", content)
            self.assertIn("## Automatic Failure", content)


if __name__ == "__main__":
    unittest.main()
