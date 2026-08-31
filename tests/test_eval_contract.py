import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote


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
PRIMARY_ARM_IDS = {"control", "generic-clean-code"}
BASELINE_ARM_IDS = {*PRIMARY_ARM_IDS, "skill-v0.1.0"}
EXPECTED_BASELINE_COMMIT_BY_SCENARIO = {
    "context-locality": "1583af33b5e517530871ff3ee724cdcad4e4c5c0",
    "behavior-validation": "9b8c94c79a18eea24645aaee268e81783d94886f",
    "dependency-boundary": "ccbc136daa59cfcd430d44ebd4cb62b57b4ab72d",
    "concurrency-side-effects": "be987152555b651532e4ba68ba1029aa777fb40e",
}
EXPECTED_ORACLE_COMMANDS = {
    "dotnet test AiCleanCode.sln --no-restore",
    "dotnet format AiCleanCode.sln --verify-no-changes --no-restore",
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
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
IGNORED_MARKDOWN_PARTS = {".git", ".superpowers"}


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

    def test_baseline_results_are_complete(self) -> None:
        result_path = EVAL_ROOT / "results" / "v0.1.0-baseline.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual("complete", result["status"])
        self.assertEqual("1.0", result["schema_version"])
        self.assertEqual("0.2.0", result["benchmark_version"])
        self.assertEqual("0.1.0", result["skill_version"])
        self.assertEqual("Codex collaboration subject", result["environment"]["client"])
        self.assertEqual("gpt-5.6-sol", result["environment"]["model"])
        self.assertEqual("high", result["environment"]["reasoning_effort"])
        self.assertEqual(
            "platform unrestricted; prompt-scoped to isolated one-commit fixture",
            result["environment"]["tool_permissions"],
        )

        runs = result["runs"]
        run_ids = [run["run_id"] for run in runs]
        self.assertEqual(28, len(runs))
        self.assertEqual(28, len(set(run_ids)))

        expected_matrix = {
            (scenario_id, arm_id, repetition)
            for scenario_id in SCENARIO_IDS
            for arm_id in PRIMARY_ARM_IDS
            for repetition in range(1, 4)
        }
        expected_matrix.update(
            (scenario_id, "skill-v0.1.0", 1)
            for scenario_id in SCENARIO_IDS
        )
        actual_matrix = {
            (run["scenario_id"], run["arm_id"], run["repetition"])
            for run in runs
        }
        self.assertEqual(expected_matrix, actual_matrix)

        primary = [run for run in runs if run["arm_id"] in PRIMARY_ARM_IDS]
        regression = [run for run in runs if run["arm_id"] == "skill-v0.1.0"]
        self.assertEqual(24, len(primary))
        self.assertEqual(4, len(regression))

        required_fields = set(self.load_manifest()["result_required_fields"])
        for run in runs:
            with self.subTest(run=run["run_id"]):
                self.assertIn(run["arm_id"], BASELINE_ARM_IDS)
                self.assertTrue(required_fields.issubset(run))
                self.assertEqual(
                    EXPECTED_BASELINE_COMMIT_BY_SCENARIO[run["scenario_id"]],
                    run["commit"],
                )
                self.assertIsInstance(run["raw_output"], str)
                self.assertTrue(run["raw_output"].strip())
                self.assertIsInstance(run["diff"], str)
                self.assertEqual("not available", run["token_telemetry"])
                self.assertEqual("not available", run["tool_calls"])
                self.assertEqual("gpt-5.6-sol", run["model"])
                self.assertEqual("high", run["reasoning_effort"])
                self.assertEqual("Codex collaboration subject", run["client"])
                self.assertEqual(
                    "platform unrestricted; prompt-scoped to isolated one-commit fixture",
                    run["tool_permissions"],
                )
                self.assertEqual(run["oracle"], run["oracle_results"])
                self.assertEqual(
                    run["human_decision"],
                    run["human_decisions_required"],
                )

                oracle_by_command = {
                    oracle["command"]: oracle for oracle in run["oracle_results"]
                }
                self.assertEqual(EXPECTED_ORACLE_COMMANDS, set(oracle_by_command))
                for oracle in oracle_by_command.values():
                    self.assertEqual(0, oracle["exit_code"])
                    self.assertTrue(oracle["summary"].strip())

                rubric_results = run["rubric_results"]
                self.assertEqual(RUBRIC_NAMES, {
                    rubric["rubric_file"] for rubric in rubric_results
                })
                for rubric in rubric_results:
                    self.assertIn(rubric["score"], {0, 1, 2})
                    self.assertTrue(rubric["evidence"])
                    self.assertTrue(rubric["reason"].strip())
                    self.assertNotIn("total_score", rubric)
                self.assertNotIn("total_score", run)
                self.assertNotIn("rubric_total", run)

                loaded_references = run["loaded_skill_references"]
                if run["arm_id"] == "skill-v0.1.0":
                    self.assertTrue(loaded_references)
                    self.assertEqual("0.1.0", run["skill_version"])
                else:
                    self.assertEqual([], loaded_references)
                    self.assertEqual("not loaded", run["skill_version"])

        exclusions = result["excluded_runs"]
        self.assertEqual(1, len(exclusions))
        exclusion = exclusions[0]
        self.assertEqual(
            "concurrency-side-effects-control-r02-original-protocol-deviation",
            exclusion["exclusion_id"],
        )
        self.assertFalse(exclusion["included_in_runs"])
        self.assertNotIn(exclusion["exclusion_id"], run_ids)
        self.assertNotIn(
            "skill-eval-v020-baseline-concurrency-side-effects-control-r02",
            {run["environment"]["source_worktree"] for run in runs},
        )
        self.assertIn(
            "skill-eval-v020-baseline-concurrency-side-effects-control-r02-replacement",
            {run["environment"]["source_worktree"] for run in runs},
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn('"not-run"', serialized)
        self.assertNotIn("\ufffd", serialized)

    def test_repository_markdown_is_utf8_and_local_links_exist(self) -> None:
        failures: list[str] = []

        for markdown_path in ROOT.rglob("*.md"):
            relative_path = markdown_path.relative_to(ROOT)
            if any(part in IGNORED_MARKDOWN_PARTS for part in relative_path.parts):
                continue
            if relative_path.parts[:2] == ("evals", "results"):
                continue

            try:
                content = markdown_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as error:
                failures.append(f"{relative_path}: invalid UTF-8 ({error})")
                continue

            if "\ufffd" in content:
                failures.append(f"{relative_path}: contains Unicode replacement character")

            for raw_target in MARKDOWN_LINK_PATTERN.findall(content):
                target = raw_target.strip()
                if target.startswith("<") and ">" in target:
                    target = target[1 : target.index(">")]
                else:
                    target = target.split(maxsplit=1)[0]

                lower_target = target.lower()
                if lower_target.startswith(("http://", "https://", "mailto:")):
                    continue
                if target.startswith("#"):
                    continue

                path_only = unquote(target.split("#", maxsplit=1)[0])
                candidate = (
                    ROOT / path_only.lstrip("/")
                    if path_only.startswith("/")
                    else markdown_path.parent / path_only
                ).resolve()

                try:
                    candidate.relative_to(ROOT)
                except ValueError:
                    failures.append(
                        f"{relative_path}: local link escapes repository ({target})"
                    )
                    continue

                if not candidate.exists():
                    failures.append(
                        f"{relative_path}: missing local link target ({target})"
                    )

        self.assertEqual([], failures, "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
