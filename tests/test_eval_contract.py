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
MICRO_SCENARIO_IDS = {
    "local-naming-refactor",
    "external-side-effect-change",
    "architecture-review",
    "estimation",
    "low-risk-formatting",
}
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
IGNORED_MARKDOWN_PARTS = {".benchmark-runs", ".git", ".superpowers"}
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
AGGREGATE_SCORE_KEYS = {
    "aggregate_score",
    "composite_score",
    "overall_score",
    "rubric_total",
    "total_score",
}
DIFF_BOUNDARY_PATTERN_VERSION = "regex-fullmatch-v1"


class EvalContractTests(unittest.TestCase):
    def test_hash_inputs_use_repository_forced_lf_endings(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

        for pattern in {"*.md", "*.py", "*.json", "*.yaml", "*.yml"}:
            with self.subTest(pattern=pattern):
                self.assertIn(f"{pattern} text eol=lf", attributes)

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

    def assert_repository_relative_posix_path(self, path: str) -> None:
        self.assertTrue(path)
        self.assertNotIn("\\", path)
        self.assertFalse(path.startswith("/"))
        self.assertNotRegex(path, r"^[A-Za-z]:")
        self.assertNotIn("\x00", path)
        self.assertNotIn("", path.split("/"))
        self.assertTrue({".", ".."}.isdisjoint(path.split("/")))

    def match_diff_path(self, path: str, scenario: dict) -> dict | None:
        self.assert_repository_relative_posix_path(path)
        if path in scenario["allowed_diff"]:
            return {"kind": "exact", "rule": path}

        for pattern in scenario["allowed_diff_patterns"]:
            if re.fullmatch(pattern, path):
                return {"kind": "pattern", "rule": pattern}
        return None

    def assert_diff_pattern_contract(self, manifest: dict) -> None:
        semantics = manifest["diff_boundary_pattern_semantics"]
        self.assertEqual(DIFF_BOUNDARY_PATTERN_VERSION, semantics["version"])
        self.assertEqual("python-re", semantics["engine"])
        self.assertEqual("repository-relative-posix", semantics["path_format"])
        self.assertIs(True, semantics["case_sensitive"])
        self.assertEqual("fullmatch", semantics["match_mode"])
        self.assertIs(True, semantics["check_rename_source_and_destination"])

        forbidden_broad_patterns = {
            "^src/.*$",
            "^tests/.*$",
            "^src/WorkItems[.]Api/.*$",
            "^tests/WorkItems[.]Api[.]Tests/.*$",
        }
        allowed_pattern_prefixes = (
            "^src/WorkItems[.]Api/",
            "^tests/WorkItems[.]Api[.]Tests/",
        )
        for scenario in manifest["scenarios"]:
            patterns = scenario["allowed_diff_patterns"]
            self.assertTrue(patterns)
            self.assertEqual(len(patterns), len(set(patterns)))
            self.assertTrue(forbidden_broad_patterns.isdisjoint(patterns))
            for pattern in patterns:
                self.assertTrue(pattern.startswith("^"), pattern)
                self.assertTrue(pattern.endswith("$"), pattern)
                self.assertTrue(pattern.startswith(allowed_pattern_prefixes), pattern)
                self.assertNotRegex(
                    pattern,
                    r"\(\?[A-Za-z-]*i[A-Za-z-]*(?::|\))",
                    "inline case-insensitive regex flags are forbidden",
                )
                re.compile(pattern)
            for path in scenario["boundary_negative_examples"]:
                self.assertIsNone(self.match_diff_path(path, scenario), path)

    def assert_diff_boundary_contract(self, run: dict, scenario: dict) -> None:
        boundary = run["diff_boundary"]
        allowed_diff = boundary["allowed_diff"]
        allowed_diff_patterns = boundary["allowed_diff_patterns"]
        actual_product_paths = boundary["actual_product_paths"]
        outside_allowed_diff = boundary["outside_allowed_diff"]
        allowed_by = boundary["allowed_by"]
        renamed_product_paths = boundary["renamed_product_paths"]

        self.assertEqual(scenario["allowed_diff"], allowed_diff)
        self.assertEqual(scenario["allowed_diff_patterns"], allowed_diff_patterns)
        self.assertEqual(run["files_modified"], actual_product_paths)
        for paths in (
            allowed_diff,
            allowed_diff_patterns,
            actual_product_paths,
            outside_allowed_diff,
        ):
            self.assertEqual(len(paths), len(set(paths)))

        diff_header_paths: list[str] = []
        expected_renamed_product_paths: list[dict[str, str]] = []
        for line in run["diff"].splitlines():
            if not line.startswith("diff --git a/"):
                continue
            header_paths = line.removeprefix("diff --git a/").split(" b/", 1)
            self.assertEqual(2, len(header_paths), line)
            old_path, new_path = header_paths
            self.assert_repository_relative_posix_path(old_path)
            self.assert_repository_relative_posix_path(new_path)
            diff_header_paths.append(new_path)
            if old_path != new_path:
                expected_renamed_product_paths.append(
                    {"from": old_path, "to": new_path}
                )

        self.assertEqual(len(diff_header_paths), len(set(diff_header_paths)))
        self.assertEqual(set(actual_product_paths), set(diff_header_paths))
        self.assertEqual(expected_renamed_product_paths, renamed_product_paths)
        rename_pairs = [
            (rename["from"], rename["to"])
            for rename in renamed_product_paths
        ]
        self.assertEqual(len(rename_pairs), len(set(rename_pairs)))

        evaluated_paths = list(actual_product_paths)
        for rename in renamed_product_paths:
            for path in (rename["from"], rename["to"]):
                if path not in evaluated_paths:
                    evaluated_paths.append(path)
        expected_allowed_by = {
            path: match
            for path in evaluated_paths
            if (match := self.match_diff_path(path, scenario)) is not None
        }
        expected_outside_allowed_diff = [
            path for path in evaluated_paths if path not in expected_allowed_by
        ]
        self.assertEqual(expected_allowed_by, allowed_by)
        self.assertEqual(expected_outside_allowed_diff, outside_allowed_diff)
        for rename in renamed_product_paths:
            self.assertEqual({"from", "to"}, set(rename))
            self.assertIsNotNone(self.match_diff_path(rename["from"], scenario))
            self.assertIsNotNone(self.match_diff_path(rename["to"], scenario))

    def test_manifest_defines_fixed_arms_and_scenarios(self) -> None:
        manifest = self.load_manifest()
        self.assert_diff_pattern_contract(manifest)
        self.assertEqual(ARM_IDS, {item["id"] for item in manifest["arms"]})
        self.assertEqual(
            SCENARIO_IDS,
            {item["id"] for item in manifest["scenarios"]},
        )
        self.assertEqual(5, manifest["run_counts"]["micro_scenarios_per_arm"])
        self.assertEqual(
            3,
            manifest["run_counts"]["repository_repetitions_per_scenario_arm"],
        )

    def test_every_scenario_is_reproducible(self) -> None:
        for scenario in self.load_manifest()["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                self.assertRegex(scenario["commit"], r"^[0-9a-f]{40}$")
                self.assertTrue(scenario["task"].strip())
                self.assertTrue(scenario["gold_files"])
                self.assertTrue(scenario["allowed_diff"])
                self.assertTrue(scenario["allowed_diff_patterns"])
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

    def test_semantic_diff_boundaries_allow_role_names_without_allowing_drift(self) -> None:
        manifest = self.load_manifest()
        scenarios = {item["id"]: item for item in manifest["scenarios"]}

        allowed_examples = {
            "behavior-validation": (
                "tests/WorkItems.Api.Tests/ProcessOverdueAcceptanceTests.cs"
            ),
            "dependency-boundary": (
                "src/WorkItems.Api/Notifications/NotificationProvider.cs"
            ),
            "concurrency-side-effects": (
                "src/WorkItems.Api/OverdueProcessingCoordinator.cs"
            ),
        }
        for scenario_id, path in allowed_examples.items():
            with self.subTest(scenario=scenario_id, path=path):
                match = self.match_diff_path(path, scenarios[scenario_id])
                self.assertEqual("pattern", match["kind"])

        rejected_examples = {
            "behavior-validation": "scripts/test-series-baseline-api.ps1",
            "dependency-boundary": (
                "src/WorkItems.Api/Contracts/WorkItemContracts.cs"
            ),
            "concurrency-side-effects": "src/WorkItems.Api/Telemetry.cs",
        }
        for scenario_id, path in rejected_examples.items():
            with self.subTest(scenario=scenario_id, path=path):
                self.assertIsNone(self.match_diff_path(path, scenarios[scenario_id]))

        telemetry_drift = {
            "dependency-boundary": [
                "src/WorkItems.Api/Notifications/NotificationTelemetryProvider.cs",
                "src/WorkItems.Api/Contracts/NotificationTelemetryContract.cs",
            ],
            "concurrency-side-effects": [
                "src/WorkItems.Api/OverdueTelemetryCoordinator.cs",
                "tests/WorkItems.Api.Tests/OverdueTelemetryConcurrencyTests.cs",
            ],
        }
        for scenario_id, paths in telemetry_drift.items():
            for path in paths:
                with self.subTest(scenario=scenario_id, telemetry=path):
                    self.assertIsNone(
                        self.match_diff_path(path, scenarios[scenario_id])
                    )

    def test_semantic_diff_boundary_rejects_forged_provenance_and_rename_escape(self) -> None:
        manifest = self.load_manifest()
        scenario = next(
            item for item in manifest["scenarios"] if item["id"] == "dependency-boundary"
        )
        result = json.loads(
            (EVAL_ROOT / "results" / "v0.1.0-baseline.json").read_text(
                encoding="utf-8"
            )
        )
        run = next(
            item
            for item in result["runs"]
            if item["run_id"] == "dependency-boundary-control-r01"
        )

        forged = deepcopy(run)
        forged["diff_boundary"]["allowed_by"] = {}
        with self.assertRaises(AssertionError):
            self.assert_diff_boundary_contract(forged, scenario)

        rename_escape = deepcopy(run)
        rename_escape["diff_boundary"]["renamed_product_paths"] = [
            {
                "from": "src/WorkItems.Api/Notifications/NotificationProvider.cs",
                "to": "scripts/NotificationProvider.cs",
            }
        ]
        with self.assertRaises(AssertionError):
            self.assert_diff_boundary_contract(rename_escape, scenario)

        unbacked_allowed_rename = deepcopy(run)
        unbacked_allowed_rename["diff_boundary"]["renamed_product_paths"] = [
            {
                "from": "src/WorkItems.Api/Notifications/NotificationGateway.cs",
                "to": "src/WorkItems.Api/Notifications/NotificationProvider.cs",
            }
        ]
        with self.assertRaises(AssertionError):
            self.assert_diff_boundary_contract(unbacked_allowed_rename, scenario)

        duplicated_rename = deepcopy(unbacked_allowed_rename)
        duplicated_rename["diff_boundary"]["renamed_product_paths"] *= 2
        with self.assertRaises(AssertionError):
            self.assert_diff_boundary_contract(duplicated_rename, scenario)

        backed_rename = deepcopy(run)
        rename_from = "src/WorkItems.Api/Notifications/NotificationGateway.cs"
        rename_to = "src/WorkItems.Api/Notifications/NotificationProvider.cs"
        backed_rename["diff"] = f"diff --git a/{rename_from} b/{rename_to}\n"
        backed_rename["files_modified"] = [rename_to]
        backed_rename["diff_boundary"]["actual_product_paths"] = [rename_to]
        backed_rename["diff_boundary"]["renamed_product_paths"] = [
            {"from": rename_from, "to": rename_to}
        ]
        backed_rename["diff_boundary"]["allowed_by"] = {
            rename_to: self.match_diff_path(rename_to, scenario),
            rename_from: self.match_diff_path(rename_from, scenario),
        }
        backed_rename["diff_boundary"]["outside_allowed_diff"] = []
        self.assert_diff_boundary_contract(backed_rename, scenario)

    def test_semantic_diff_boundary_rejects_overbroad_patterns_and_invalid_paths(self) -> None:
        manifest = self.load_manifest()
        overbroad = deepcopy(manifest)
        overbroad["scenarios"][0]["allowed_diff_patterns"] = ["^.*$"]
        with self.assertRaises(AssertionError):
            self.assert_diff_pattern_contract(overbroad)

        case_insensitive = deepcopy(manifest)
        case_insensitive["scenarios"][2]["allowed_diff_patterns"] = [
            "^src/WorkItems[.]Api/Notifications/(?i:OverdueNotificationProvider)[.]cs$"
        ]
        with self.assertRaises(AssertionError):
            self.assert_diff_pattern_contract(case_insensitive)

        scenario = manifest["scenarios"][0]
        for invalid_path in (
            "C:/src/WorkItems.Api/Program.cs",
            "/src/WorkItems.Api/Program.cs",
            "src\\WorkItems.Api\\Program.cs",
            "src/../Program.cs",
            "src//Program.cs",
        ):
            with self.subTest(path=invalid_path):
                with self.assertRaises(AssertionError):
                    self.match_diff_path(invalid_path, scenario)

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
        self.assertEqual(
            manifest["diff_boundary_pattern_semantics"],
            result["diff_boundary_pattern_semantics"],
        )
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

        rescoring_history = result["rescoring_history"]
        self.assertEqual(1, len(rescoring_history))
        rescoring = rescoring_history[0]
        self.assertEqual("exact-allowed-diff-v1", rescoring["from_matcher"])
        self.assertEqual(DIFF_BOUNDARY_PATTERN_VERSION, rescoring["to_matcher"])
        self.assertEqual(17, len(rescoring["changes"]))
        self.assertEqual(
            17,
            len({change["run_id"] for change in rescoring["changes"]}),
        )

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

        run_by_id = {run["run_id"]: run for run in runs}
        for change in rescoring["changes"]:
            with self.subTest(rescored_run=change["run_id"]):
                run = run_by_id[change["run_id"]]
                context_rubric = next(
                    rubric
                    for rubric in run["rubric_results"]
                    if rubric["rubric_id"] == "context-and-locality"
                )
                self.assertEqual(
                    run["diff_boundary"]["outside_allowed_diff"],
                    change["rescored_outside_allowed_diff"],
                )
                self.assertEqual(
                    context_rubric["score"],
                    change["rescored_context_and_locality_score"],
                )
                self.assertEqual(context_rubric["reason"], change["rescored_reason"])
                self.assertEqual(
                    run["blind_spots"],
                    change["rescored_blind_spots"],
                )
                self.assertTrue(
                    change["previous_outside_allowed_diff"]
                    != change["rescored_outside_allowed_diff"]
                    or change["previous_context_and_locality_score"]
                    != change["rescored_context_and_locality_score"]
                    or change["previous_reason"] != change["rescored_reason"]
                    or change["previous_blind_spots"]
                    != change["rescored_blind_spots"]
                )

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

        outside_by_run = {
            run["run_id"]: run["diff_boundary"]["outside_allowed_diff"]
            for run in runs
            if run["diff_boundary"]["outside_allowed_diff"]
        }
        self.assertEqual(
            {
                "behavior-validation-generic-clean-code-r02": [
                    "scripts/test-series-baseline-api.ps1"
                ],
                "dependency-boundary-generic-clean-code-r01": [
                    "src/WorkItems.Api/Contracts/WorkItemContracts.cs"
                ],
            },
            outside_by_run,
        )

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

    def test_v020_initial_results_cover_skill_arm_and_micro_matrix(self) -> None:
        result_path = EVAL_ROOT / "results" / "v0.2.0-initial.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        manifest = self.load_manifest()
        scenario_by_id = {
            scenario["id"]: scenario for scenario in manifest["scenarios"]
        }

        self.assertEqual("complete", result["status"])
        self.assertEqual("1.0", result["schema_version"])
        self.assertEqual("0.2.0", result["benchmark_version"])
        self.assertEqual("0.2.0", result["skill_version"])
        self.assertEqual(
            manifest["diff_boundary_pattern_semantics"],
            result["diff_boundary_pattern_semantics"],
        )

        runs = result["runs"]
        self.assertEqual(12, len(runs))
        self.assertEqual(12, len({run["run_id"] for run in runs}))
        self.assertEqual(
            {
                (scenario_id, repetition)
                for scenario_id in SCENARIO_IDS
                for repetition in range(1, 4)
            },
            {(run["scenario_id"], run["repetition"]) for run in runs},
        )
        expected_outside_by_run = {
            "concurrency-side-effects-skill-v0.2.0-r01": [
                "src/WorkItems.Api/InFlightWorkItemProcessingGate.cs"
            ],
            "concurrency-side-effects-skill-v0.2.0-r02": [
                "src/WorkItems.Api/CoalescingOverdueWorkItemProcessor.cs"
            ],
            "concurrency-side-effects-skill-v0.2.0-r03": [
                "src/WorkItems.Api/InProcessOverdueNotificationGuard.cs"
            ],
        }
        for run in runs:
            with self.subTest(repository_run=run["run_id"]):
                scenario = scenario_by_id[run["scenario_id"]]
                self.assertTrue(RESULT_REQUIRED_FIELDS.issubset(run))
                self.assertEqual("skill-v0.2.0", run["arm_id"])
                self.assertEqual("0.2.0", run["skill_version"])
                self.assertEqual("gpt-5.6-sol", run["model"])
                self.assertEqual("high", run["reasoning_effort"])
                self.assertEqual("Codex collaboration subject", run["client"])
                self.assertEqual(scenario["commit"], run["commit"])
                self.assertEqual(scenario["task"], run["prompt"])
                self.assertTrue(run["raw_output"].strip())
                self.assertNotIn("System.Object[]", run["raw_output"])
                self.assertTrue(run["files_inspected"])
                self.assertIn(
                    run["files_inspected_provenance"],
                    {
                        "subject report files_inspected",
                        "reconstructed from manifest gold_files whose contents are cited in subject repository_facts",
                    },
                )
                self.assertEqual(
                    run["files_inspected_complete"],
                    run["files_inspected_provenance"]
                    == "subject report files_inspected",
                )
                self.assertTrue(run["loaded_skill_references"])
                self.assertIn(
                    "clean-code-ai-collaboration/SKILL.md",
                    run["loaded_skill_references"],
                )
                self.assertEqual(
                    hashlib.sha256(run["diff"].encode("utf-8")).hexdigest(),
                    run["diff_sha256"],
                )
                self.assert_diff_boundary_contract(
                    run,
                    scenario,
                )
                self.assertEqual(
                    expected_outside_by_run.get(run["run_id"], []),
                    run["diff_boundary"]["outside_allowed_diff"],
                )
                self.assertEqual(
                    "standalone shallow repository with one fixed commit",
                    run["environment"]["fixture"],
                )
                self.assertEqual(1, run["environment"]["history_commit_count"])
                self.assertIs(False, run["environment"]["shared_refs_present"])
                self.assertEqual(
                    "independent root evaluator after subject completion",
                    run["environment"]["oracle_execution"],
                )
                self.assertEqual(2, len(run["oracle_results"]))
                self.assertEqual(
                    EXPECTED_ORACLE_COMMANDS,
                    {oracle["command"] for oracle in run["oracle_results"]},
                )
                evaluator_commands = {
                    command["command"]: command
                    for command in run["commands"]
                    if command.get("source") == "evaluator"
                }
                self.assertEqual(EXPECTED_ORACLE_COMMANDS, set(evaluator_commands))
                self.assertEqual(
                    EXPECTED_ORACLE_COMMANDS,
                    set(run["exit_codes"]["oracle_commands"]),
                )
                for oracle in run["oracle_results"]:
                    self.assertEqual(0, oracle["exit_code"])
                    self.assertEqual("passed", oracle["classification"])
                    self.assertTrue(oracle["summary"].strip())
                    evaluator_command = evaluator_commands[oracle["command"]]
                    self.assertEqual(oracle["exit_code"], evaluator_command["exit_code"])
                    self.assertEqual(
                        oracle["summary"], evaluator_command["observed_result"]
                    )
                    self.assertEqual(
                        oracle["exit_code"],
                        run["exit_codes"]["oracle_commands"][oracle["command"]],
                    )
                self.assertIs(False, run["automatic_failure"]["triggered"])
                self.assertEqual([], run["automatic_failure"]["reasons"])
                eligibility = run["comparison_eligibility"]
                self.assertTrue(eligibility["eligible_for_quality_comparison"])
                self.assertTrue(
                    eligibility["eligible_for_primary_effect_comparison"]
                )
                self.assertEqual([], eligibility["quality_comparison_reasons"])
                self.assertEqual([], eligibility["primary_effect_comparison_reasons"])
                scores = {
                    rubric["rubric_id"]: rubric["score"]
                    for rubric in run["rubric_results"]
                }
                expected_context_score = (
                    1 if run["run_id"] in expected_outside_by_run else 2
                )
                self.assertEqual(expected_context_score, scores["context-and-locality"])
                self.assertEqual(2, scores["behavior-and-validation"])
                self.assertEqual(2, scores["decision-and-escalation"])
                self.assertTrue(
                    all(
                        rubric["automatic_failure_applied"] is False
                        for rubric in run["rubric_results"]
                    )
                )
                self.assertTrue(all(isinstance(item, dict) for item in run["artifacts"]))
                self.assertEqual("not available", run["token_telemetry"])
                self.assertEqual("not available", run["tool_calls"])

        structured_raw_run = next(
            run
            for run in runs
            if run["run_id"] == "context-locality-skill-v0.2.0-r03"
        )
        structured_raw_output = json.loads(structured_raw_run["raw_output"])
        self.assertIn("outcome_and_status", structured_raw_output)
        self.assertIn("applicable_references", structured_raw_output)
        self.assertIn("behavior_that_must_not_change", structured_raw_output)

        comparison = result["comparison"]
        baseline = json.loads(
            (EVAL_ROOT / "results" / "v0.1.0-baseline.json").read_text(
                encoding="utf-8"
            )
        )
        generic_runs = [
            run for run in baseline["runs"] if run["arm_id"] == "generic-clean-code"
        ]
        generic_full_support = {
            "context_and_locality": sum(
                1
                for run in generic_runs
                if next(
                    rubric
                    for rubric in run["rubric_results"]
                    if rubric["rubric_id"] == "context-and-locality"
                )["score"]
                == 2
            ),
            "behavior_and_validation": sum(
                1
                for run in generic_runs
                if next(
                    rubric
                    for rubric in run["rubric_results"]
                    if rubric["rubric_id"] == "behavior-and-validation"
                )["score"]
                == 2
            ),
            "decision_and_escalation": sum(
                1
                for run in generic_runs
                if next(
                    rubric
                    for rubric in run["rubric_results"]
                    if rubric["rubric_id"] == "decision-and-escalation"
                )["score"]
                == 2
            ),
        }
        self.assertEqual(12, len(generic_runs))
        self.assertEqual(
            sum(1 for run in generic_runs if run["automatic_failure"]["triggered"]),
            comparison["generic_baseline"]["automatic_failures"],
        )
        self.assertEqual(
            generic_full_support,
            comparison["generic_baseline"]["full_support_by_rubric"],
        )
        self.assertEqual(0, comparison["skill_v0_2_0"]["automatic_failures"])
        self.assertEqual(
            {
                "context_and_locality": 9,
                "behavior_and_validation": 12,
                "decision_and_escalation": 12,
            },
            comparison["skill_v0_2_0"]["full_support_by_rubric"],
        )
        self.assertEqual(
            "not available", comparison["token_and_tool_call_comparison"]
        )

        micro_runs = result["micro_runs"]
        self.assertEqual(15, len(micro_runs))
        self.assertEqual(15, len({run["run_id"] for run in micro_runs}))
        self.assertEqual(
            {
                (scenario_id, arm_id)
                for scenario_id in MICRO_SCENARIO_IDS
                for arm_id in ARM_IDS
            },
            {(run["scenario_id"], run["arm_id"]) for run in micro_runs},
        )
        expected_skill_paths = {
            "local-naming-refactor": "lightweight",
            "external-side-effect-change": "full",
            "architecture-review": "full",
            "estimation": "full",
            "low-risk-formatting": "lightweight",
        }
        for run in micro_runs:
            with self.subTest(micro_run=run["run_id"]):
                self.assertEqual("gpt-5.6-sol", run["model"])
                self.assertEqual("high", run["reasoning_effort"])
                self.assertTrue(run["prompt"].strip())
                self.assertTrue(run["raw_output"].strip())
                self.assertIn(run["trigger_result"], {"activated", "not-activated"})
                self.assertIn(run["selected_path"], {"lightweight", "full", "none"})
                self.assertIsInstance(run["loaded_references"], list)
                self.assertIn(run["human_score"], {0, 1, 2})
                self.assertTrue(run["score_reason"].strip())
                if run["arm_id"] == "skill-v0.2.0":
                    self.assertEqual("activated", run["trigger_result"])
                    self.assertEqual(
                        expected_skill_paths[run["scenario_id"]],
                        run["selected_path"],
                    )
                    self.assertIn(
                        "clean-code-ai-collaboration/SKILL.md",
                        run["loaded_references"],
                    )
                else:
                    self.assertEqual("not-activated", run["trigger_result"])
                    self.assertEqual("none", run["selected_path"])
                    self.assertEqual([], run["loaded_references"])

        self.assertTrue(all(run["human_score"] == 2 for run in micro_runs))
        self.assertEqual(
            {arm_id: 5 for arm_id in ARM_IDS},
            {
                arm_id: sum(1 for run in micro_runs if run["arm_id"] == arm_id)
                for arm_id in ARM_IDS
            },
        )
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotRegex(serialized, r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
        self.assertNotIn("\ufffd", serialized)
        self.assert_no_aggregate_scores(result)

    def test_repository_markdown_is_utf8_and_local_links_exist(self) -> None:
        failures: list[str] = []
        windows_personal_path_pattern = re.compile(
            r"(?i)(?<![A-Za-z0-9])[A-Za-z]:[\\/]+(?:Users|MySelf|Project)[\\/]+"
        )
        unix_home_pattern = re.compile(r"(?<![A-Za-z0-9._-])/(?:Users|home)/")

        self.assertRegex(r"C:\Users\example\project", windows_personal_path_pattern)
        self.assertRegex("/home/example/project", unix_home_pattern)
        self.assertNotRegex(r"C:\path\to\project", windows_personal_path_pattern)
        self.assertNotRegex("docs/Users/guide.md", unix_home_pattern)

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
            if windows_personal_path_pattern.search(content):
                failures.append(f"{relative_path}: contains a Windows personal path")
            if unix_home_pattern.search(content):
                failures.append(f"{relative_path}: contains a Unix personal path")

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

    def test_benchmark_external_validity_matrix_separates_evidence_from_plans(
        self,
    ) -> None:
        content = (EVAL_ROOT / "benchmark.md").read_text(encoding="utf-8")
        section = content.split("## External Validity Expansion Matrix", maxsplit=1)[1]

        for state in {"已驗證", "規劃中", "尚未支持"}:
            with self.subTest(state=state):
                self.assertIn(state, section)

        for dimension in {
            "public .NET Demo",
            "large .NET Legacy",
            "TypeScript / React",
            "Python",
            "Java / Spring",
            "AGENTS.md",
            "Blind Review",
        }:
            with self.subTest(dimension=dimension):
                self.assertIn(dimension, section)

        self.assertIn("v0.2.0-initial.json", section)
        self.assertIn("沒有 Result 的項目不得寫成已驗證", section)

    def test_public_result_files_do_not_expose_personal_paths(self) -> None:
        result_paths = sorted((EVAL_ROOT / "results").glob("*.json"))
        unix_home_pattern = r"(?<![A-Za-z0-9._-])/(?:Users|home)/"

        self.assertTrue(result_paths)
        self.assertRegex('"/home/example/project"', unix_home_pattern)
        self.assertRegex('"cd /Users/example/project"', unix_home_pattern)
        self.assertNotRegex('"src/home/index.cs"', unix_home_pattern)
        self.assertNotRegex('"docs/Users/guide.md"', unix_home_pattern)
        for result_path in result_paths:
            serialized = result_path.read_text(encoding="utf-8")
            with self.subTest(result=result_path.name):
                self.assertNotRegex(
                    serialized,
                    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]",
                )
                self.assertNotRegex(serialized, unix_home_pattern)

    def test_v040_strategy_full_run_result_is_complete(self) -> None:
        result_path = EVAL_ROOT / "results" / "v0.4.0-strategy-full-run.json"
        self.assertTrue(result_path.is_file())
        result = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual("complete", result["status"])
        self.assertEqual("0.4.0", result["skill_version"])
        self.assertEqual(9, result["baseline_run_count"])
        self.assertEqual(5, result["baseline_conforming_count"])
        self.assertEqual(18, result["full_run_count"])
        self.assertEqual(18, result["passed_full_run_count"])
        self.assertEqual(64, len(result["manifest_sha256"]))
        self.assertEqual(64, len(result["skill_tree_sha256"]))
        self.assertEqual(9, len(result["baseline_runs"]))
        self.assertEqual(18, len(result["full_runs"]))
        self.assertEqual(27, len(result["receipts"]))
        self.assertFalse(
            result["execution_attestation"]["independent_runtime_identity_verified"]
        )
        self.assertNotIn("fresh Codex subjects", result["claim_boundary"])
        self.assertIn("controller-dispatched subjects", result["claim_boundary"])
        self.assertIn(
            "fresh Context",
            result["execution_attestation"]["limitation"],
        )
        self.assertTrue(
            any(
                "selected blocked prerequisites" in observation
                for observation in result["observations"]
            )
        )
        self.assertFalse(
            any(
                "blocked prerequisites were all represented" in observation
                for observation in result["observations"]
            )
        )
        for receipt in result["receipts"]:
            self.assertEqual(
                {"run_id", "prompt", "dispatch", "subject_result", "terminal"},
                set(receipt),
            )
        self.assertTrue(
            all(run["terminal_state"] == "passed" for run in result["full_runs"])
        )
        self.assertIn("does not measure code quality", result["claim_boundary"])

    def test_v040_strategy_result_is_explained_without_overclaiming(self) -> None:
        benchmark = (EVAL_ROOT / "benchmark.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for content in {benchmark, readme}:
            with self.subTest(document="benchmark" if content is benchmark else "readme"):
                self.assertIn("v0.4.0-strategy-full-run.json", content)
                self.assertIn("18／18", content)
                self.assertIn("不衡量程式碼品質", content)
                self.assertIn("不宣稱節省 Token", content)

        self.assertIn("9 組無 Skill 對照", benchmark)
        self.assertIn("5／9", benchmark)
        self.assertIn("v0.3.0", benchmark)
        self.assertIn("Full Run 尚未完成", benchmark)
        self.assertIn("不納入 v0.4.0", benchmark)


if __name__ == "__main__":
    unittest.main()
