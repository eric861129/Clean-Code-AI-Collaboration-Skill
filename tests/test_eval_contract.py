from copy import deepcopy
import hashlib
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
    "repetition",
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
    "diff_sha256",
    "diff_boundary",
    "commands",
    "environment",
    "exit_codes",
    "artifacts",
    "oracle_results",
    "rubric_results",
    "automatic_failure",
    "comparison_eligibility",
    "blind_spots",
    "human_decisions_required",
    "token_telemetry",
    "tool_calls",
    "elapsed_time",
    "generated_lines",
}
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
IGNORED_MARKDOWN_PARTS = {".git", ".superpowers"}
FORBIDDEN_DIFF_PATH_PARTS = {
    ".benchmark-subject-report.json",
    ".vs",
    "artifacts",
    "bin",
    "obj",
    "runtime",
    "testresults",
}
PORCELAIN_STATUS_PATTERN = re.compile(r"^[ MADRCUT?!]{2} .+$")
AGGREGATE_SCORE_KEYS = {"total_score", "rubric_total"}


class EvalContractTests(unittest.TestCase):
    def load_manifest(self) -> dict:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def assert_no_aggregate_scores(
        self, value: object, location: str = "result"
    ) -> None:
        if isinstance(value, dict):
            aggregate_score_keys = AGGREGATE_SCORE_KEYS.intersection(value)
            self.assertFalse(
                aggregate_score_keys,
                f"{location}: aggregate score aliases are forbidden: "
                f"{sorted(aggregate_score_keys)}",
            )
            for key, child in value.items():
                self.assert_no_aggregate_scores(child, f"{location}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.assert_no_aggregate_scores(child, f"{location}[{index}]")

    def assert_diff_boundary_contract(self, run: dict, scenario: dict) -> None:
        boundary = run["diff_boundary"]
        allowed_diff = boundary["allowed_diff"]
        actual_product_paths = boundary["actual_product_paths"]
        outside_allowed_diff = boundary["outside_allowed_diff"]

        self.assertEqual(scenario["allowed_diff"], allowed_diff)
        self.assertEqual(run["files_modified"], actual_product_paths)
        for paths in (allowed_diff, actual_product_paths, outside_allowed_diff):
            self.assertEqual(len(paths), len(set(paths)))

        allowed_diff_set = set(allowed_diff)
        expected_outside_allowed_diff = [
            path for path in actual_product_paths if path not in allowed_diff_set
        ]
        self.assertEqual(expected_outside_allowed_diff, outside_allowed_diff)
        self.assertTrue(set(outside_allowed_diff).issubset(actual_product_paths))

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

    def test_locality_boundary_rejects_manifest_and_outside_diff_drift(self) -> None:
        manifest = self.load_manifest()
        scenario = next(
            item for item in manifest["scenarios"] if item["id"] == "context-locality"
        )
        result = json.loads(
            (EVAL_ROOT / "results" / "v0.1.0-baseline.json").read_text(
                encoding="utf-8"
            )
        )
        run = next(
            item
            for item in result["runs"]
            if item["run_id"] == "context-locality-control-r01"
        )

        mutations = {
            "manifest allowed_diff drift": {
                "allowed_diff": ["src/WorkItems.Api/Unexpected.cs"]
            },
            "false outside_allowed_diff entry": {
                "outside_allowed_diff": run["diff_boundary"][
                    "actual_product_paths"
                ]
            },
        }
        for label, boundary_mutation in mutations.items():
            with self.subTest(mutation=label):
                mutated_run = deepcopy(run)
                mutated_run["diff_boundary"].update(boundary_mutation)
                with self.assertRaises(AssertionError):
                    self.assert_diff_boundary_contract(mutated_run, scenario)

    def test_locality_boundary_rejects_duplicate_path_lists(self) -> None:
        manifest = self.load_manifest()
        scenario = next(
            item for item in manifest["scenarios"] if item["id"] == "context-locality"
        )
        result = json.loads(
            (EVAL_ROOT / "results" / "v0.1.0-baseline.json").read_text(
                encoding="utf-8"
            )
        )
        run = next(
            item
            for item in result["runs"]
            if item["run_id"] == "context-locality-control-r01"
        )
        product_path = run["diff_boundary"]["actual_product_paths"][0]

        for path_list_name in (
            "allowed_diff",
            "actual_product_paths",
            "outside_allowed_diff",
        ):
            with self.subTest(path_list=path_list_name):
                mutated_run = deepcopy(run)
                mutated_scenario = deepcopy(scenario)
                if path_list_name == "allowed_diff":
                    duplicated_paths = [
                        *scenario["allowed_diff"],
                        scenario["allowed_diff"][0],
                    ]
                    mutated_scenario["allowed_diff"] = duplicated_paths
                else:
                    duplicated_paths = [product_path, product_path]

                mutated_run["diff_boundary"][path_list_name] = duplicated_paths
                if path_list_name == "actual_product_paths":
                    mutated_run["files_modified"] = duplicated_paths

                with self.assertRaises(AssertionError):
                    self.assert_diff_boundary_contract(
                        mutated_run,
                        mutated_scenario,
                    )

    def test_aggregate_score_aliases_are_forbidden_recursively(self) -> None:
        for aggregate_score_key in AGGREGATE_SCORE_KEYS:
            with self.subTest(key=aggregate_score_key):
                mutation = {"nested": [{aggregate_score_key: 6}]}
                with self.assertRaises(AssertionError):
                    self.assert_no_aggregate_scores(mutation)

    def test_baseline_results_are_complete(self) -> None:
        result_path = EVAL_ROOT / "results" / "v0.1.0-baseline.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        manifest = self.load_manifest()
        scenario_by_id = {
            scenario["id"]: scenario for scenario in manifest["scenarios"]
        }

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

        required_fields = set(manifest["result_required_fields"])
        for run in runs:
            with self.subTest(run=run["run_id"]):
                scenario = scenario_by_id[run["scenario_id"]]
                self.assertIn(run["arm_id"], BASELINE_ARM_IDS)
                self.assertTrue(required_fields.issubset(run))
                self.assertEqual(
                    EXPECTED_BASELINE_COMMIT_BY_SCENARIO[run["scenario_id"]],
                    run["commit"],
                )
                self.assertIsInstance(run["raw_output"], str)
                self.assertTrue(run["raw_output"].strip())
                self.assertIsInstance(run["diff"], str)
                for status_line in run["working_tree_status"].splitlines():
                    if status_line:
                        self.assertRegex(status_line, PORCELAIN_STATUS_PATTERN)
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

                actual_product_paths = run["diff_boundary"]["actual_product_paths"]
                self.assert_diff_boundary_contract(run, scenario)
                self.assertEqual(
                    hashlib.sha256(run["diff"].encode("utf-8")).hexdigest(),
                    run["diff_sha256"],
                )

                diff_header_paths: list[str] = []
                for line in run["diff"].splitlines():
                    if not line.startswith("diff --git a/"):
                        continue
                    header_paths = line.removeprefix("diff --git a/").split(" b/", 1)
                    self.assertEqual(2, len(header_paths), line)
                    old_path, new_path = header_paths
                    self.assertEqual(old_path, new_path, line)
                    diff_header_paths.append(new_path)

                self.assertEqual(len(diff_header_paths), len(set(diff_header_paths)))
                self.assertEqual(set(actual_product_paths), set(diff_header_paths))
                for product_path in actual_product_paths:
                    path_parts = {part.lower() for part in Path(product_path).parts}
                    self.assertTrue(
                        FORBIDDEN_DIFF_PATH_PARTS.isdisjoint(path_parts),
                        product_path,
                    )

                if actual_product_paths:
                    self.assertTrue(run["diff"].strip())
                else:
                    self.assertEqual("", run["diff"])
                    self.assertEqual(
                        "stopped_for_human_decision",
                        run["diff_boundary"].get("empty_diff_disposition"),
                    )
                    self.assertTrue(run["human_decisions_required"])

                oracle_results = run["oracle_results"]
                oracle_commands = [oracle["command"] for oracle in oracle_results]
                self.assertEqual(len(oracle_commands), len(set(oracle_commands)))
                self.assertEqual(
                    set(scenario["oracle_commands"]),
                    set(oracle_commands),
                )
                self.assertEqual(EXPECTED_ORACLE_COMMANDS, set(oracle_commands))
                oracle_by_command = {
                    oracle["command"]: oracle for oracle in oracle_results
                }
                all_evaluator_commands = [
                    command
                    for command in run["commands"]
                    if command.get("source") == "evaluator"
                ]
                self.assertEqual(
                    len(scenario["oracle_commands"]),
                    len(all_evaluator_commands),
                )
                self.assertEqual(
                    set(scenario["oracle_commands"]),
                    {command["command"] for command in all_evaluator_commands},
                )
                self.assertEqual(
                    set(scenario["oracle_commands"]),
                    set(run["exit_codes"]["oracle_commands"]),
                )
                for oracle_command in scenario["oracle_commands"]:
                    oracle = oracle_by_command[oracle_command]
                    self.assertEqual(0, oracle["exit_code"])
                    self.assertTrue(oracle["summary"].strip())
                    evaluator_commands = [
                        command
                        for command in run["commands"]
                        if command.get("source") == "evaluator"
                        and command["command"] == oracle_command
                    ]
                    self.assertEqual(1, len(evaluator_commands))
                    evaluator_command = evaluator_commands[0]
                    self.assertEqual(oracle["exit_code"], evaluator_command["exit_code"])
                    self.assertEqual(
                        oracle["summary"],
                        evaluator_command["observed_result"],
                    )
                    self.assertEqual(
                        oracle["exit_code"],
                        run["exit_codes"]["oracle_commands"][oracle_command],
                    )

                rubric_results = run["rubric_results"]
                self.assertEqual(3, len(rubric_results))
                self.assertEqual(
                    set(scenario["rubrics"]),
                    {rubric["rubric_file"] for rubric in rubric_results},
                )
                self.assertEqual(
                    {Path(name).stem for name in scenario["rubrics"]},
                    {rubric["rubric_id"] for rubric in rubric_results},
                )
                automatic_failure = run["automatic_failure"]
                self.assertIsInstance(automatic_failure["triggered"], bool)
                self.assertEqual(
                    automatic_failure["triggered"],
                    bool(automatic_failure["reasons"]),
                )
                for rubric in rubric_results:
                    self.assertIn(rubric["score"], {0, 1, 2})
                    self.assertTrue(rubric["evidence"])
                    self.assertTrue(rubric["reason"].strip())
                    self.assertEqual(
                        automatic_failure["triggered"],
                        rubric["automatic_failure_applied"],
                    )

                eligibility = run["comparison_eligibility"]
                quality_eligible = eligibility["eligible_for_quality_comparison"]
                primary_eligible = eligibility[
                    "eligible_for_primary_effect_comparison"
                ]
                quality_reasons = eligibility["quality_comparison_reasons"]
                primary_reasons = eligibility["primary_effect_comparison_reasons"]
                self.assertEqual(not quality_eligible, bool(quality_reasons))
                self.assertEqual(not primary_eligible, bool(primary_reasons))
                if automatic_failure["triggered"]:
                    self.assertFalse(quality_eligible)
                    self.assertFalse(primary_eligible)
                else:
                    self.assertTrue(quality_eligible)
                    self.assertEqual(run["arm_id"] in PRIMARY_ARM_IDS, primary_eligible)

                loaded_references = run["loaded_skill_references"]
                if run["arm_id"] == "skill-v0.1.0":
                    self.assertTrue(loaded_references)
                    self.assertEqual("0.1.0", run["skill_version"])
                    self.assertFalse(primary_eligible)
                else:
                    self.assertEqual([], loaded_references)
                    self.assertEqual("not loaded", run["skill_version"])

        source_worktrees = [
            run["environment"]["source_worktree"] for run in runs
        ]
        self.assertEqual(28, len(set(source_worktrees)))
        replacement_run = next(
            run
            for run in runs
            if run["run_id"] == "concurrency-side-effects-control-r02"
        )
        original_source = (
            "skill-eval-v020-baseline-concurrency-side-effects-control-r02"
        )
        replacement_source = f"{original_source}-replacement"
        self.assertEqual(
            replacement_source,
            replacement_run["environment"]["source_worktree"],
        )
        self.assertNotIn(original_source, source_worktrees)

        exclusions = result["excluded_runs"]
        self.assertEqual(1, len(exclusions))
        exclusion = exclusions[0]
        self.assertEqual(
            "concurrency-side-effects-control-r02-original-protocol-deviation",
            exclusion["exclusion_id"],
        )
        self.assertEqual(
            "concurrency-side-effects-control-r02",
            exclusion["semantic_run_id"],
        )
        self.assertEqual(original_source, exclusion["source_worktree"])
        self.assertEqual(
            replacement_source,
            exclusion["replacement_source_worktree"],
        )
        self.assertFalse(exclusion["included_in_runs"])

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn('"not-run"', serialized)
        self.assertNotIn("\ufffd", serialized)
        self.assert_no_aggregate_scores(result)

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
