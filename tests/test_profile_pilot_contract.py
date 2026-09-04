import copy
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jsonschema import Draft202012Validator

import evals.harness.cli as harness_cli
import evals.harness.fixture_builder as fixture_builder
import evals.harness.oracle_runner as oracle_runner
from evals.harness.anonymizer import build_review_packet
from evals.harness.cli import main as harness_main
from evals.harness.desktop_subject import (
    DesktopSubjectValidationError,
    canonical_prompt_sha256,
    desktop_subject_instruction,
    stage_desktop_subject,
    validate_desktop_report,
    write_attempt_receipt,
)
from evals.harness.fixture_builder import build_workspace
from evals.harness.manifest import load_manifest, validate_manifest
from evals.harness.models import (
    CommandResult,
    HarnessPaths,
    RunSlot,
    SubjectDispatch,
    Workspace,
)
from evals.harness.planner import build_run_slots
from evals.harness.profile_outcomes import build_profile_outcomes
from evals.harness.result_builder import (
    _public_oracle_results,
    build_public_result,
    validate_profile_pilot_result,
)
from evals.harness.subject_runner import IMPLEMENTATION_AUTHORIZATION, build_prompt


SKILL_NAME = "clean-code-ai-collaboration"
SKILL_ROOT = f".agents/skills/{SKILL_NAME}"
CORE_INSPECTION_PATHS = (
    f"{SKILL_ROOT}/SKILL.md",
    f"{SKILL_ROOT}/references/profile-selection.md",
)
ARM_INSPECTION_PATHS = {
    "control": (),
    "generic-clean-code": (),
    "core-only": CORE_INSPECTION_PATHS,
    "core-plus-csharp": (
        *CORE_INSPECTION_PATHS,
        f"{SKILL_ROOT}/references/language-csharp.md",
    ),
    "core-plus-python": (
        *CORE_INSPECTION_PATHS,
        f"{SKILL_ROOT}/references/language-python.md",
    ),
    "core-plus-typescript": (
        *CORE_INSPECTION_PATHS,
        f"{SKILL_ROOT}/references/language-typescript.md",
    ),
    "core-plus-typescript-plus-react": (
        *CORE_INSPECTION_PATHS,
        f"{SKILL_ROOT}/references/language-typescript.md",
        f"{SKILL_ROOT}/references/framework-react.md",
    ),
}


def _terminal_documents(
    slots: tuple[RunSlot, ...], terminal_state: str = "passed"
) -> list[dict[str, object]]:
    return [
        {
            "run_id": slot.run_id,
            "scenario_id": slot.scenario_id,
            "language": slot.language,
            "arm_id": slot.arm_id,
            "repetition": slot.repetition,
            "order_index": slot.order_index,
            "terminal_state": terminal_state,
            "contract_sha256": "a" * 64,
            "scenario_contract_sha256": "b" * 64,
            "prompt_sha256": "c" * 64,
            "diff_sha256": "d" * 64,
            "automatic_failure_reasons": [],
            "oracle_results": [],
            "telemetry": "not_available",
        }
        for slot in slots
    ]


def _review_with_scores(
    criteria: list[str], scores: list[int]
) -> dict[str, object]:
    return {
        "rubrics": {
            rubric_id: {"score": 1, "reason": "review evidence"}
            for rubric_id in (
                "context-and-locality",
                "behavior-and-validation",
                "decision-and-escalation",
            )
        },
        "incremental_criteria": [
            {
                "criterion": criterion,
                "score": score,
                "reason": "criterion evidence",
            }
            for criterion, score in zip(criteria, scores, strict=True)
        ],
    }


def _profile_documents(manifest) -> list[dict[str, object]]:
    documents = _terminal_documents(build_run_slots(manifest))
    scenarios = {str(item["id"]): item for item in manifest.scenarios}
    for document in documents:
        scenario = scenarios[str(document["scenario_id"])]
        criteria = list(scenario["incremental_criteria"])
        score = 2 if document["arm_id"] == scenario["treatment_arm"] else 1
        document["review"] = _review_with_scores(criteria, [score] * len(criteria))
        document["automatic_failure_reasons"] = []
    return documents


PROFILE_PILOT_MATRIX = (
    (
        "csharp-overdue-rule",
        "csharp",
        "csharp",
        "shared_business",
        ("control", "generic-clean-code", "core-only", "core-plus-csharp"),
        "core-only",
        "core-plus-csharp",
    ),
    (
        "csharp-cancellation-cleanup",
        "csharp",
        "csharp",
        "ecosystem_native",
        ("control", "generic-clean-code", "core-only", "core-plus-csharp"),
        "core-only",
        "core-plus-csharp",
    ),
    (
        "fastapi-overdue-rule",
        "python-fastapi",
        "python",
        "shared_business",
        ("control", "generic-clean-code", "core-only", "core-plus-python"),
        "core-only",
        "core-plus-python",
    ),
    (
        "fastapi-provider-boundary",
        "python-fastapi",
        "python",
        "ecosystem_native",
        ("control", "generic-clean-code", "core-only", "core-plus-python"),
        "core-only",
        "core-plus-python",
    ),
    (
        "typescript-overdue-rule",
        "typescript",
        "typescript",
        "shared_business",
        ("control", "generic-clean-code", "core-only", "core-plus-typescript"),
        "core-only",
        "core-plus-typescript",
    ),
    (
        "typescript-runtime-validation",
        "typescript",
        "typescript",
        "ecosystem_native",
        ("control", "generic-clean-code", "core-only", "core-plus-typescript"),
        "core-only",
        "core-plus-typescript",
    ),
    (
        "react-state-error-retention",
        "typescript-react",
        "react",
        "shared_business",
        (
            "control",
            "generic-clean-code",
            "core-only",
            "core-plus-typescript",
            "core-plus-typescript-plus-react",
        ),
        "core-plus-typescript",
        "core-plus-typescript-plus-react",
    ),
    (
        "react-effect-lifecycle",
        "typescript-react",
        "react",
        "ecosystem_native",
        (
            "control",
            "generic-clean-code",
            "core-only",
            "core-plus-typescript",
            "core-plus-typescript-plus-react",
        ),
        "core-plus-typescript",
        "core-plus-typescript-plus-react",
    ),
)

PROFILE_INCREMENTAL_CRITERIA = {
    "csharp-overdue-rule": (
        "DateTimeOffset comparison preserves the exact two-hour UTC boundary",
        "Completed and Normal Priority branches retain their existing semantics",
    ),
    "csharp-cancellation-cleanup": (
        "Caller CancellationToken reaches provider open and send operations",
        "OperationCanceledException remains cancellation rather than provider failure",
        "The asynchronous provider session is disposed exactly once",
    ),
    "fastapi-overdue-rule": (
        "High Priority applies the exact two-hour timezone-aware boundary",
        "HTTP status, response schema, Completed, and Normal behavior remain unchanged",
    ),
    "fastapi-provider-boundary": (
        "The route reuses NotificationSender through FastAPI dependency injection",
        "Dependency override replaces the provider without duplicating the domain boundary",
        "The 202, 404, 502, and 503 failure semantics remain distinct",
    ),
    "typescript-overdue-rule": (
        "High Priority uses the exact two-hour boundary through the existing WorkItem model",
        "Completed and Normal Priority branches remain typed and unchanged",
    ),
    "typescript-runtime-validation": (
        "The unknown payload is narrowed by runtime guards before WorkItem construction",
        "The existing WorkItem type is reused without any or unsafe assertion",
        "Accepted and rejected results use exhaustive discriminated-union handling",
    ),
    "react-state-error-retention": (
        "Still-valid content remains visible while retry is loading",
        "Earlier success or failure cannot overwrite the latest request state",
        "Public loading, error, success, and props contracts remain unchanged",
    ),
    "react-effect-lifecycle": (
        "Effect identity follows workItemId rather than callback or presentation props",
        "An identity change aborts the prior request through AbortSignal",
        "An aborted request cannot overwrite the current success or error state",
    ),
}


def _profile_pilot_manifest_raw() -> dict[str, object]:
    arms = [
        {
            "id": "control",
            "instruction": "",
            "required_skill_inspection_paths": [],
        },
        {
            "id": "generic-clean-code",
            "instruction": "請遵守 Clean Code 完成任務。",
            "required_skill_inspection_paths": [],
        },
        {
            "id": "core-only",
            "instruction": "請使用 $clean-code-ai-collaboration Core 完成任務。",
        },
        {
            "id": "core-plus-csharp",
            "instruction": "請使用 $clean-code-ai-collaboration Core 與 C# Profile 完成任務。",
        },
        {
            "id": "core-plus-python",
            "instruction": "請使用 $clean-code-ai-collaboration Core 與 Python Profile 完成任務。",
        },
        {
            "id": "core-plus-typescript",
            "instruction": "請使用 $clean-code-ai-collaboration Core 與 TypeScript Profile 完成任務。",
        },
        {
            "id": "core-plus-typescript-plus-react",
            "instruction": "請使用 $clean-code-ai-collaboration Core、TypeScript 與 React Profile 完成任務。",
        },
    ]
    for arm in arms:
        arm_id = str(arm["id"])
        inspection_paths = ARM_INSPECTION_PATHS[arm_id]
        arm["required_skill_inspection_paths"] = list(inspection_paths)
        if inspection_paths:
            arm["skill"] = SKILL_NAME
            arm["version"] = "v0.5.0"
    scenarios = []
    for (
        scenario_id,
        language,
        profile,
        scenario_type,
        comparison_arms,
        direct_comparator,
        treatment_arm,
    ) in PROFILE_PILOT_MATRIX:
        scenarios.append(
            {
                "id": scenario_id,
                "language": language,
                "fixture_path": f"fixtures/{scenario_id}",
                "evaluator_path": f"evaluators/{scenario_id}",
                "task": f"完成 {scenario_id}。",
                "must_preserve": ["公開契約"],
                "allowed_diff": ["src/target.txt"],
                "allowed_diff_patterns": ["^src/target[.]txt$"],
                "prohibited_changes": ["不得修改工具鏈"],
                "commands": {
                    "public": [["echo", "public"]],
                    "preservation": [["echo", "preservation"]],
                    "acceptance": [["echo", "acceptance"]],
                },
                "expected_baseline_red_markers": ["expected red"],
                "expected_baseline_failure_count": 1,
                "comparison_arms": list(comparison_arms),
                "profile_under_test": profile,
                "scenario_type": scenario_type,
                "direct_comparator": direct_comparator,
                "treatment_arm": treatment_arm,
                "incremental_criteria": [f"{profile} incremental criterion"],
            }
        )
    return {
        "schema_version": "1.0",
        "benchmark_version": "0.5.1-profile-pilot",
        "freeze_policy": "pre_execution",
        "fixture_repository": {
            "url": "https://example.test/fixtures.git",
            "tag": "profile-pilot-v1",
            "commit": "a" * 40,
        },
        "skill": {"tag": "v0.5.0", "commit": "b" * 40},
        "execution": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
            "client": "codex-desktop-collaboration",
            "subject_executor": {
                "kind": "codex-desktop-collaboration",
                "protocol_version": "desktop-subject-v4",
                "dispatch_mode": "external-collaboration-subagent",
                "report_relative_path": ".benchmark-subject-report.json",
                "network_enforcement": "not_available",
                "telemetry": "not_available",
            },
            "subject_timeout_seconds": 480,
            "fixture_timeout_seconds": 120,
            "oracle_timeout_seconds": 120,
            "repetitions": 1,
            "random_seed": 560501,
        },
        "arms": arms,
        "scenarios": scenarios,
    }


class ProfilePilotHarnessContractTests(unittest.TestCase):
    def test_public_oracle_results_remove_absolute_command_paths(self) -> None:
        public = _public_oracle_results(
            [
                {
                    "group": "public",
                    "commands": [
                        {
                            "args": [
                                r"C:\Program Files\dotnet\dotnet.EXE",
                                "test",
                                "/home/example/project/tests.csproj",
                            ],
                            "exit_code": 0,
                            "stdout": "private",
                            "stderr": "private",
                        }
                    ],
                }
            ]
        )

        command = public[0]["commands"][0]
        self.assertEqual(
            ["dotnet.EXE", "test", "tests.csproj"],
            command["args"],
        )
        self.assertNotIn("stdout", command)
        self.assertNotIn("stderr", command)

    def test_profile_fixture_runtime_supports_typescript_and_csharp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs_root = root / "runs"
            typescript_root = root / "typescript"
            typescript_root.mkdir()
            with patch.object(fixture_builder, "_run_checked") as run_checked:
                fixture_builder._install_dependencies(
                    typescript_root,
                    "typescript",
                    runs_root,
                    120,
                )
            self.assertEqual("npm", run_checked.call_args.args[0][0])

            csharp_root = root / "csharp"
            project = csharp_root / "tests" / "PublicTests" / "PublicTests.csproj"
            project.parent.mkdir(parents=True)
            project.write_text("<Project />", encoding="utf-8")
            with (
                patch.object(fixture_builder.shutil, "which", return_value="dotnet"),
                patch.object(fixture_builder, "_run_checked") as run_checked,
            ):
                fixture_builder._install_dependencies(
                    csharp_root,
                    "csharp",
                    runs_root,
                    120,
                )
            self.assertEqual(
                [
                    "dotnet",
                    "restore",
                    "tests/PublicTests/PublicTests.csproj",
                    "--locked-mode",
                    "--nologo",
                ],
                run_checked.call_args.args[0],
            )

            fixture_builder._write_workspace_gitignore(csharp_root)
            workspace_ignore = (csharp_root / ".gitignore").read_text(
                encoding="utf-8"
            )
            self.assertIn("bin/", workspace_ignore)
            self.assertIn("obj/", workspace_ignore)

    def test_profile_oracle_expands_the_dotnet_tool_token(self) -> None:
        with patch.object(oracle_runner.shutil, "which", return_value="dotnet"):
            self.assertEqual(
                ["dotnet", "test", "PublicTests.csproj"],
                oracle_runner._expand_command(
                    ["{dotnet}", "test", "PublicTests.csproj"],
                    Path("workspace"),
                ),
            )

    def test_profile_preflight_counts_traditional_chinese_dotnet_failures(
        self,
    ) -> None:
        result = CommandResult(
            args=("dotnet", "test"),
            exit_code=1,
            stdout=(
                "失敗 CsharpOverdueRule.AcceptanceTests."
                "HighPriorityItemIsOverdueAtTwoHourBoundary\n"
                "失敗! - 失敗:     1，通過:     1，略過:     0，總計:     2"
            ),
            stderr="",
            elapsed_seconds=1.0,
            timed_out=False,
            classification="nonzero_exit",
            attempt=1,
        )

        self.assertTrue(
            oracle_runner.baseline_acceptance_is_expected(
                (result,),
                ("HighPriorityItemIsOverdueAtTwoHourBoundary",),
                1,
            )
        )

    def test_committed_profile_pilot_manifest_freezes_the_real_m2_matrix(
        self,
    ) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        manifest_path = (
            repository_root / "evals" / "manifests" / "v0.5.1-profile-pilot.json"
        )
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = load_manifest(manifest_path)

        self.assertEqual("0.5.1-profile-pilot", manifest.benchmark_version)
        self.assertEqual("pre_execution", manifest.freeze_policy)
        self.assertEqual(
            "https://github.com/eric861129/"
            "Clean-Code-AI-Collaboration-Benchmark-Fixtures.git",
            manifest.fixture_url,
        )
        self.assertEqual("profile-pilot-v1", manifest.fixture_tag)
        self.assertEqual(
            "6ed8712f2b3d4eaf902dbe1470a8740f92700878",
            manifest.fixture_commit,
        )
        self.assertEqual("v0.5.0", manifest.skill_tag)
        self.assertEqual(
            "bd895776a80566381003182bfdb24f0f02784731",
            manifest.skill_commit,
        )
        self.assertEqual(1, manifest.repetitions)
        self.assertEqual("gpt-5.6-sol", manifest.model)
        self.assertEqual("high", manifest.reasoning_effort)
        self.assertEqual(480, manifest.subject_timeout_seconds)
        self.assertEqual(120, manifest.fixture_timeout_seconds)
        self.assertEqual(120, manifest.oracle_timeout_seconds)
        self.assertEqual(
            tuple(ARM_INSPECTION_PATHS), tuple(arm.id for arm in manifest.arms)
        )
        self.assertEqual(
            {
                "name": SKILL_NAME,
                "version": "0.5.0",
                "tag": "v0.5.0",
                "commit": "bd895776a80566381003182bfdb24f0f02784731",
            },
            raw["skill"],
        )

        slots = build_run_slots(manifest)
        self.assertEqual(34, len(slots))
        self.assertEqual(34, len({slot.run_id for slot in slots}))
        scenarios = {str(item["id"]): item for item in manifest.scenarios}
        for (
            scenario_id,
            language,
            profile,
            scenario_type,
            comparison_arms,
            direct_comparator,
            treatment_arm,
        ) in PROFILE_PILOT_MATRIX:
            with self.subTest(scenario_id=scenario_id):
                scenario = scenarios[scenario_id]
                self.assertEqual(language, scenario["language"])
                self.assertEqual(profile, scenario["profile_under_test"])
                self.assertEqual(scenario_type, scenario["scenario_type"])
                self.assertEqual(comparison_arms, scenario["comparison_arms"])
                self.assertEqual(direct_comparator, scenario["direct_comparator"])
                self.assertEqual(treatment_arm, scenario["treatment_arm"])
                self.assertEqual(
                    PROFILE_INCREMENTAL_CRITERIA[scenario_id],
                    tuple(scenario["incremental_criteria"]),
                )
                self.assertEqual(
                    {
                        f"{scenario_id}--{arm_id}--r01"
                        for arm_id in comparison_arms
                    },
                    {
                        slot.run_id
                        for slot in slots
                        if slot.scenario_id == scenario_id
                    },
                )

        rubric = (
            repository_root / "evals" / "rubrics" / "profile-increment.md"
        ).read_text(encoding="utf-8")
        for required_text in (
            "single candidate",
            "0",
            "1",
            "2",
            "Diff",
            "Oracle",
            "incremental_criteria",
            "不得比較",
        ):
            self.assertIn(required_text, rubric)

    def test_profile_pilot_result_schema_requires_complete_public_evidence(
        self,
    ) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        slots = build_run_slots(manifest)
        documents = _profile_documents(manifest)
        documents[0]["oracle_results"] = [
            {
                "group": "public",
                "commands": [
                    {
                        "args": ["python", "-m", "unittest"],
                        "exit_code": 0,
                        "elapsed_seconds": 0.1,
                        "timed_out": False,
                        "classification": "passed",
                        "attempt": 1,
                        "stdout_sha256": "3" * 64,
                        "stderr_sha256": "4" * 64,
                        "stdout": "complete private raw output",
                        "stderr": "private diagnostic output",
                    }
                ],
            }
        ]
        source_revisions = {
            "fixture_tag": "profile-pilot-v1",
            "fixture_commit": "a" * 40,
            "skill_tag": "v0.5.0",
            "skill_commit": "b" * 40,
            "manifest_path": "evals/manifests/v0.5.1-profile-pilot.json",
            "manifest_sha256": "c" * 64,
            "harness_sha256": "d" * 64,
            "contract_sha256": "a" * 64,
            "prompts": {
                f"{slot.scenario_id}/{slot.arm_id}": "c" * 64 for slot in slots
            },
            "evaluators": {
                str(scenario["id"]): "1" * 64 for scenario in manifest.scenarios
            },
            "rubrics": {"evals/rubrics/profile-increment.md": "2" * 64},
        }
        expected_scenario_contracts = {
            str(scenario["id"]): "b" * 64 for scenario in manifest.scenarios
        }
        execution = {
            "model": manifest.model,
            "reasoning_effort": manifest.reasoning_effort,
            "client": manifest.client,
            "subject_executor": manifest.subject_executor,
            "subject_timeout_seconds": manifest.subject_timeout_seconds,
            "fixture_timeout_seconds": manifest.fixture_timeout_seconds,
            "oracle_timeout_seconds": manifest.oracle_timeout_seconds,
            "repetitions": manifest.repetitions,
            "random_seed": manifest.random_seed,
        }
        review_metadata = {
            "anonymization": "single-candidate",
            "reviewer_model": "gpt-5.6-terra",
            "reviewer_reasoning_effort": "max",
            "expected_candidates": 34,
            "completed_candidates": 34,
            "rubric_ids": [
                "context-and-locality",
                "behavior-and-validation",
                "decision-and-escalation",
            ],
            "incremental_criteria_scored": True,
        }
        result = build_public_result(
            slots,
            documents,
            benchmark_version=manifest.benchmark_version,
            source_revisions=source_revisions,
            execution=execution,
            review_metadata=review_metadata,
            profile_outcomes=build_profile_outcomes(manifest, documents),
        )
        schema = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "evals"
                / "profile-pilot-result.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        self.assertEqual([], list(validator.iter_errors(result)))
        validate_profile_pilot_result(
            result,
            manifest,
            schema,
            expected_source_revisions=source_revisions,
            expected_scenario_contracts=expected_scenario_contracts,
        )
        public_command = result["runs"][0]["oracle_results"][0]["commands"][0]
        self.assertNotIn("stdout", public_command)
        self.assertNotIn("stderr", public_command)
        self.assertEqual("3" * 64, public_command["stdout_sha256"])
        self.assertEqual("4" * 64, public_command["stderr_sha256"])

        invalid_results = []
        extra = copy.deepcopy(result)
        extra["unexpected"] = True
        invalid_results.append(extra)
        missing_run = copy.deepcopy(result)
        missing_run["runs"].pop()
        invalid_results.append(missing_run)
        duplicate_profile = copy.deepcopy(result)
        duplicate_profile["profile_outcomes"][0]["profile_id"] = "react"
        invalid_results.append(duplicate_profile)
        invalid_hash = copy.deepcopy(result)
        invalid_hash["source_revisions"]["manifest_sha256"] = "not-a-hash"
        invalid_results.append(invalid_hash)
        for invalid in invalid_results:
            with self.subTest(invalid=invalid):
                self.assertTrue(list(validator.iter_errors(invalid)))

        run_id_drift = copy.deepcopy(result)
        run_id_drift["runs"][0]["run_id"] = "different-run-id"
        with self.assertRaisesRegex(ValueError, "run IDs"):
            validate_profile_pilot_result(
                run_id_drift,
                manifest,
                schema,
                expected_source_revisions=source_revisions,
                expected_scenario_contracts=expected_scenario_contracts,
            )

        outcome_drift = copy.deepcopy(result)
        outcome_drift["profile_outcomes"][0]["outcome"] = "no_difference"
        with self.assertRaisesRegex(ValueError, "do not replay"):
            validate_profile_pilot_result(
                outcome_drift,
                manifest,
                schema,
                expected_source_revisions=source_revisions,
                expected_scenario_contracts=expected_scenario_contracts,
            )

        revision_drift = copy.deepcopy(result)
        revision_drift["source_revisions"]["fixture_commit"] = "9" * 40
        with self.assertRaisesRegex(ValueError, "source revisions"):
            validate_profile_pilot_result(
                revision_drift,
                manifest,
                schema,
                expected_source_revisions=source_revisions,
                expected_scenario_contracts=expected_scenario_contracts,
            )

        hash_drift = copy.deepcopy(result)
        hash_drift["source_revisions"]["manifest_sha256"] = "9" * 64
        with self.assertRaisesRegex(ValueError, "source revisions"):
            validate_profile_pilot_result(
                hash_drift,
                manifest,
                schema,
                expected_source_revisions=source_revisions,
                expected_scenario_contracts=expected_scenario_contracts,
            )

        for field, value, message in (
            ("contract_sha256", "9" * 64, "contract hash"),
            ("scenario_contract_sha256", "8" * 64, "scenario contract hash"),
            ("prompt_sha256", "7" * 64, "prompt hash"),
        ):
            with self.subTest(field=field):
                run_hash_drift = copy.deepcopy(result)
                run_hash_drift["runs"][0][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    validate_profile_pilot_result(
                        run_hash_drift,
                        manifest,
                        schema,
                        expected_source_revisions=source_revisions,
                        expected_scenario_contracts=expected_scenario_contracts,
                    )

    def test_dynamic_result_requires_exact_profile_pilot_slot_identities(
        self,
    ) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        slots = build_run_slots(manifest)
        documents = _terminal_documents(slots)

        result = build_public_result(
            slots,
            documents,
            benchmark_version=manifest.benchmark_version,
        )
        self.assertEqual(34, len(result["runs"]))

        cases = (
            ("terminal states", documents[:-1]),
            ("unique run IDs", [*documents[:-1], copy.deepcopy(documents[0])]),
            (
                "invalid terminal state",
                [
                    {**document, "terminal_state": "pending"}
                    if index == 0
                    else document
                    for index, document in enumerate(documents)
                ],
            ),
            (
                "aggregate score",
                [
                    {**document, "aggregate_score": 6}
                    if index == 0
                    else document
                    for index, document in enumerate(documents)
                ],
            ),
            (
                "identity mismatch",
                [
                    {**document, "arm_id": "not-the-arm"}
                    if index == 0
                    else document
                    for index, document in enumerate(documents)
                ],
            ),
        )
        for message, invalid_documents in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_public_result(
                        slots,
                        invalid_documents,
                        benchmark_version=manifest.benchmark_version,
                    )

    def test_profile_review_packet_exposes_criteria_without_treatment_identity(
        self,
    ) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        scenario = next(
            item
            for item in manifest.scenarios
            if item["id"] == "react-effect-lifecycle"
        )
        run_id = (
            "react-effect-lifecycle--core-plus-typescript-plus-react--r01"
        )
        run_document = {
            "run_id": run_id,
            "scenario_id": scenario["id"],
            "language": scenario["language"],
            "arm_id": scenario["treatment_arm"],
            "task": scenario["task"],
            "must_preserve": scenario["must_preserve"],
            "diff": " ".join(
                [
                    run_id,
                    f"{run_id}.json",
                    *(arm.id for arm in manifest.arms),
                    *(f"{arm.id}.patch" for arm in manifest.arms),
                    *(f"artifact-{arm.id}-output.json" for arm in manifest.arms),
                    f".benchmark-runs/workspaces/{run_id}/candidate.patch",
                    f"/workspace/{run_id}/candidate.patch",
                    "C:/Users/Eric Huang/workspace/private.patch",
                    SKILL_NAME,
                    "AbortController",
                ]
            ),
            "oracle_results": [],
            "automatic_failure_reasons": [],
            "blind_spots": ["single fixture"],
        }

        packet = build_review_packet(
            run_document,
            candidate_id="candidate-a1b2c3d4",
            manifest=manifest,
        )
        self.assertEqual("typescript-react", packet["language"])
        self.assertEqual("react", packet["profile_under_test"])
        self.assertEqual("ecosystem_native", packet["scenario_type"])
        self.assertEqual(
            [
                {"criterion": criterion, "score": None, "reason": ""}
                for criterion in scenario["incremental_criteria"]
            ],
            packet["incremental_criteria"],
        )
        self.assertNotIn("direct_comparator", packet)
        self.assertNotIn("treatment_arm", packet)
        self.assertNotIn("run_id", packet)
        serialized = json.dumps(packet, ensure_ascii=False).casefold()
        for arm in manifest.arms:
            self.assertIsNone(
                re.search(
                    rf"(?<![a-z0-9_.-]){re.escape(arm.id)}(?![a-z0-9_.-])",
                    serialized,
                )
            )
        self.assertNotIn(SKILL_NAME, serialized)
        self.assertNotIn(".benchmark-runs", serialized)
        self.assertNotIn("/workspace/", serialized)
        self.assertNotIn("eric huang", serialized)
        self.assertNotIn("huang/workspace", serialized)
        self.assertNotIn(run_id, serialized)
        self.assertIn("AbortController", packet["diff"])

    def test_profile_outcome_priority_and_direct_comparators(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())

        def outcomes_for(documents: list[dict[str, object]]):
            return {
                item["profile_id"]: item
                for item in build_profile_outcomes(manifest, documents)
            }

        documents = _profile_documents(manifest)
        outcomes = outcomes_for(documents)
        self.assertEqual(
            {"csharp", "python", "typescript", "react"}, set(outcomes)
        )
        self.assertTrue(
            all(item["outcome"] == "passed" for item in outcomes.values())
        )
        react = outcomes["react"]
        self.assertEqual("core-plus-typescript", react["direct_comparator"])
        self.assertEqual(
            "core-plus-typescript-plus-react", react["treatment_arm"]
        )
        self.assertTrue(
            all(
                "--core-plus-typescript--" in run_id
                for run_id in react["comparator_run_ids"]
            )
        )
        self.assertTrue(
            all(
                "--core-plus-typescript-plus-react--" in run_id
                for run_id in react["treatment_run_ids"]
            )
        )

        control_document = next(
            item
            for item in documents
            if item["scenario_id"] == "react-effect-lifecycle"
            and item["arm_id"] == "control"
        )
        control_document["terminal_state"] = "automatic_failure"
        control_document["automatic_failure_reasons"] = ["outside_boundary"]
        self.assertEqual("passed", outcomes_for(documents)["react"]["outcome"])

        treatment = next(
            item
            for item in documents
            if item["scenario_id"] == "csharp-overdue-rule"
            and item["arm_id"] == "core-plus-csharp"
        )
        treatment.pop("review")
        self.assertEqual(
            "inconclusive", outcomes_for(documents)["csharp"]["outcome"]
        )

        documents = _profile_documents(manifest)
        treatment = next(
            item
            for item in documents
            if item["scenario_id"] == "csharp-overdue-rule"
            and item["arm_id"] == "core-plus-csharp"
        )
        treatment["review"].pop("rubrics")
        self.assertEqual(
            "inconclusive", outcomes_for(documents)["csharp"]["outcome"]
        )

        documents = _profile_documents(manifest)
        treatment = next(
            item
            for item in documents
            if item["scenario_id"] == "csharp-overdue-rule"
            and item["arm_id"] == "core-plus-csharp"
        )
        treatment["terminal_state"] = "automatic_failure"
        treatment["automatic_failure_reasons"] = ["acceptance_failed"]
        self.assertEqual("failed", outcomes_for(documents)["csharp"]["outcome"])

        documents = _profile_documents(manifest)
        treatment = next(
            item
            for item in documents
            if item["scenario_id"] == "csharp-overdue-rule"
            and item["arm_id"] == "core-plus-csharp"
        )
        treatment["review"]["incremental_criteria"][0]["score"] = 0
        self.assertEqual("failed", outcomes_for(documents)["csharp"]["outcome"])

        documents = _profile_documents(manifest)
        for document in documents:
            if document["arm_id"] in {
                "core-only",
                "core-plus-csharp",
            }:
                scenario = next(
                    item
                    for item in manifest.scenarios
                    if item["id"] == document["scenario_id"]
                )
                if scenario["profile_under_test"] == "csharp":
                    for criterion in document["review"]["incremental_criteria"]:
                        criterion["score"] = 1
        self.assertEqual(
            "no_difference", outcomes_for(documents)["csharp"]["outcome"]
        )

    def test_profile_outcome_treats_infrastructure_and_evidence_gaps_first(
        self,
    ) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        documents = _profile_documents(manifest)
        csharp_treatment = next(
            item
            for item in documents
            if item["scenario_id"] == "csharp-cancellation-cleanup"
            and item["arm_id"] == "core-plus-csharp"
        )
        csharp_treatment["terminal_state"] = "infrastructure_failure"
        csharp_treatment["automatic_failure_reasons"] = ["environment_error"]
        outcomes = {
            item["profile_id"]: item
            for item in build_profile_outcomes(manifest, documents)
        }
        self.assertEqual("inconclusive", outcomes["csharp"]["outcome"])

        documents = _profile_documents(manifest)
        csharp_treatment = next(
            item
            for item in documents
            if item["scenario_id"] == "csharp-cancellation-cleanup"
            and item["arm_id"] == "core-plus-csharp"
        )
        csharp_treatment["terminal_state"] = "automatic_failure"
        csharp_treatment["automatic_failure_reasons"] = [
            "outside_boundary",
            "skill_not_used",
        ]
        outcomes = {
            item["profile_id"]: item
            for item in build_profile_outcomes(manifest, documents)
        }
        self.assertEqual("inconclusive", outcomes["csharp"]["outcome"])

    def test_profile_arms_drive_prompt_and_complete_inspection_sets(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        scenario = manifest.scenarios[0]
        task = str(scenario["task"]) + IMPLEMENTATION_AUTHORIZATION

        for arm in manifest.arms:
            with self.subTest(arm_id=arm.id):
                expected_prompt = task
                if arm.instruction:
                    expected_prompt += f"\n\n{arm.instruction}"
                actual_prompt = build_prompt(scenario, arm.id, manifest)
                self.assertEqual(expected_prompt, actual_prompt)
                self.assertNotIn("\r", actual_prompt)
                self.assertEqual(
                    hashlib.sha256(expected_prompt.encode("utf-8")).hexdigest(),
                    canonical_prompt_sha256(actual_prompt),
                )
                self.assertEqual(
                    ARM_INSPECTION_PATHS[arm.id],
                    arm.required_skill_inspection_paths,
                )

        with self.assertRaisesRegex(ValueError, "unknown arm"):
            build_prompt(scenario, "unknown-arm", manifest)

        self.assertEqual(
            "f7fedc39b00f5e895c2015e8d9cb1d5894dfbd89ca4a89187b0784f26779c545",
            canonical_prompt_sha256(
                build_prompt(scenario, "core-plus-csharp", manifest)
            ),
        )

        raw = _profile_pilot_manifest_raw()
        raw["scenarios"][0]["task"] = "第一行\r\n第二行\r第三行"
        raw["arms"][3]["instruction"] = "C# 第一行\r\nC# 第二行"
        normalized_manifest = validate_manifest(raw)
        normalized_prompt = build_prompt(
            normalized_manifest.scenarios[0],
            "core-plus-csharp",
            normalized_manifest,
        )
        self.assertNotIn("\r", normalized_prompt)
        self.assertIn("第一行\n第二行\n第三行", normalized_prompt)
        self.assertIn("C# 第一行\nC# 第二行", normalized_prompt)

    def test_profile_arm_inspection_paths_fail_closed(self) -> None:
        cases = (
            (
                "duplicate",
                lambda arm: arm["required_skill_inspection_paths"].append(
                    arm["required_skill_inspection_paths"][0]
                ),
            ),
            (
                "repository-relative POSIX",
                lambda arm: arm["required_skill_inspection_paths"].__setitem__(
                    0, f"{SKILL_ROOT}/references/../SKILL.md"
                ),
            ),
            (
                "repository-relative POSIX",
                lambda arm: arm["required_skill_inspection_paths"].__setitem__(
                    0, "C:/outside/SKILL.md"
                ),
            ),
            (
                "inside staged Skill root",
                lambda arm: arm["required_skill_inspection_paths"].__setitem__(
                    0, ".agents/skills/another-skill/SKILL.md"
                ),
            ),
        )
        for expected_message, mutate in cases:
            with self.subTest(expected_message=expected_message):
                raw = _profile_pilot_manifest_raw()
                arm = raw["arms"][2]
                mutate(arm)
                with self.assertRaisesRegex(ValueError, expected_message):
                    validate_manifest(raw)

        raw = _profile_pilot_manifest_raw()
        raw["arms"][0]["required_skill_inspection_paths"] = [
            f"{SKILL_ROOT}/SKILL.md"
        ]
        with self.assertRaisesRegex(ValueError, "without a Skill"):
            validate_manifest(raw)

        raw = _profile_pilot_manifest_raw()
        raw["arms"].append(
            {
                "id": "unsafe-skill",
                "instruction": "unsafe",
                "skill": "../outside",
                "version": "v0.5.0",
            }
        )
        with self.assertRaisesRegex(ValueError, "arm Skill is invalid"):
            validate_manifest(raw)

        raw = _profile_pilot_manifest_raw()
        raw["arms"][0]["version"] = "v0.5.0"
        with self.assertRaisesRegex(ValueError, "without a Skill"):
            validate_manifest(raw)

        raw = _profile_pilot_manifest_raw()
        del raw["arms"][-1]["required_skill_inspection_paths"]
        with self.assertRaisesRegex(ValueError, "must declare required Skill"):
            validate_manifest(raw)

        raw = _profile_pilot_manifest_raw()
        raw["arms"][-1]["required_skill_inspection_paths"] = None
        with self.assertRaisesRegex(ValueError, "inspection paths are invalid"):
            validate_manifest(raw)

        raw = _profile_pilot_manifest_raw()
        raw["arms"][-1]["version"] = "v9.9.9"
        with self.assertRaisesRegex(ValueError, "does not match pinned Skill"):
            validate_manifest(raw)

        raw = _profile_pilot_manifest_raw()
        del raw["arms"][-1]["version"]
        with self.assertRaisesRegex(ValueError, "must declare a version"):
            validate_manifest(raw)

    def test_workspace_stages_skill_for_every_declared_skill_arm(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())

        def export_tree(**kwargs: object) -> None:
            destination = Path(str(kwargs["destination"]))
            destination.mkdir(parents=True, exist_ok=True)

        def run_checked(args: list[str], *_args: object) -> SimpleNamespace:
            stdout = "c" * 40 if args[:2] == ["git", "rev-parse"] else ""
            return SimpleNamespace(stdout=stdout)

        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            paths = HarnessPaths(
                repository_root=repository_root,
                runs_root=repository_root / ".benchmark-runs" / "profile-pilot",
                fixture_clone=repository_root / "fixture-source",
                skill_repository=repository_root / "skill-source",
            )
            for arm in manifest.arms:
                slot = RunSlot(
                    run_id=f"csharp-overdue-rule--{arm.id}--r01",
                    scenario_id="csharp-overdue-rule",
                    language="csharp",
                    arm_id=arm.id,
                    repetition=1,
                    order_index=0,
                )
                with (
                    patch.object(fixture_builder, "_verify_revision"),
                    patch.object(
                        fixture_builder, "_export_tree", side_effect=export_tree
                    ) as exported,
                    patch.object(fixture_builder, "_install_dependencies"),
                    patch.object(
                        fixture_builder, "_run_checked", side_effect=run_checked
                    ),
                ):
                    workspace = build_workspace(slot, manifest, paths)

                skill_root = workspace.root / SKILL_ROOT
                if arm.skill is None:
                    self.assertFalse(skill_root.parent.exists(), arm.id)
                    self.assertEqual(1, exported.call_count)
                else:
                    self.assertTrue(skill_root.is_dir(), arm.id)
                    self.assertEqual(2, exported.call_count)
                    skill_export = exported.call_args_list[1].kwargs
                    self.assertEqual(paths.skill_repository, skill_export["repository"])
                    self.assertEqual(
                        f"{manifest.skill_commit}:{SKILL_NAME}",
                        skill_export["treeish"],
                    )

    def test_react_profile_dispatch_requires_exact_multi_file_skill_evidence(
        self,
    ) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        arm_id = "core-plus-typescript-plus-react"
        required_paths = ARM_INSPECTION_PATHS[arm_id]
        slot = RunSlot(
            run_id=f"react-state-error-retention--{arm_id}--r01",
            scenario_id="react-state-error-retention",
            language="typescript-react",
            arm_id=arm_id,
            repetition=1,
            order_index=0,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            controller_root = root / "controller"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            for index, relative_path in enumerate(required_paths):
                path = workspace_root / Path(relative_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"profile evidence {index}\n", encoding="utf-8")
            workspace = Workspace(workspace_root, artifact_dir, "a" * 40)

            dispatch = stage_desktop_subject(
                slot,
                manifest,
                workspace,
                generation=1,
                attempt=1,
                physical_run_id="run-profileinspection",
                contract_sha256="b" * 64,
                scenario_contract_sha256="c" * 64,
                controller_dispatch_root=controller_root,
            )
            self.assertEqual(required_paths, dispatch.required_skill_inspection_paths)
            instruction = desktop_subject_instruction(dispatch)
            for relative_path in required_paths:
                self.assertIn(relative_path, instruction)

            exact_claims = [
                {
                    "path": relative_path,
                    "sha256": hashlib.sha256(
                        (workspace_root / Path(relative_path)).read_bytes()
                    ).hexdigest(),
                }
                for relative_path in required_paths
            ]

            def validate_with(
                files_inspected: list[str], claims: list[dict[str, str]]
            ) -> dict[str, object]:
                result = json.loads(
                    dispatch.report_template_path.read_text(encoding="utf-8")
                )
                result.update(
                    {
                        "summary": "完成 profile treatment。",
                        "files_inspected": files_inspected,
                        "skill_inspection_claims": claims,
                    }
                )
                dispatch.report_path.write_text(
                    json.dumps(result, ensure_ascii=False), encoding="utf-8"
                )
                return validate_desktop_report(dispatch)

            with self.assertRaises(DesktopSubjectValidationError) as missing_file:
                validate_with(list(required_paths[:-1]), exact_claims)
            self.assertEqual("skill_not_used", missing_file.exception.reason)

            with self.assertRaises(DesktopSubjectValidationError) as missing_claim:
                validate_with(list(required_paths), exact_claims[:-1])
            self.assertEqual("skill_not_used", missing_claim.exception.reason)

            with self.assertRaises(DesktopSubjectValidationError) as duplicate_claim:
                validate_with(list(required_paths), [*exact_claims, exact_claims[0]])
            self.assertEqual("invalid_claim", duplicate_claim.exception.reason)

            with self.assertRaises(DesktopSubjectValidationError) as extra_claim:
                validate_with(
                    list(required_paths),
                    [
                        *exact_claims,
                        {"path": "undeclared.md", "sha256": "d" * 64},
                    ],
                )
            self.assertEqual("invalid_claim", extra_claim.exception.reason)

            mismatched_claims = copy.deepcopy(exact_claims)
            mismatched_claims[-1]["sha256"] = "e" * 64
            with self.assertRaises(DesktopSubjectValidationError) as hash_mismatch:
                validate_with(list(required_paths), mismatched_claims)
            self.assertEqual("invalid_claim", hash_mismatch.exception.reason)

            merged = validate_with(list(required_paths), exact_claims)
            self.assertTrue(merged["skill_inspection_verified"])

    def test_profile_dispatch_rejects_missing_or_escaping_required_skill_file(
        self,
    ) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        arm_id = "core-plus-typescript-plus-react"
        slot = RunSlot(
            run_id=f"react-effect-lifecycle--{arm_id}--r01",
            scenario_id="react-effect-lifecycle",
            language="typescript-react",
            arm_id=arm_id,
            repetition=1,
            order_index=0,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            artifact_dir = root / "artifacts"
            workspace_root.mkdir()
            artifact_dir.mkdir()
            required_paths = ARM_INSPECTION_PATHS[arm_id]
            for relative_path in required_paths[:-1]:
                path = workspace_root / Path(relative_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("profile evidence\n", encoding="utf-8")
            workspace = Workspace(workspace_root, artifact_dir, "a" * 40)

            with self.assertRaisesRegex(ValueError, "required staged Skill file"):
                stage_desktop_subject(
                    slot,
                    manifest,
                    workspace,
                    generation=1,
                    attempt=1,
                    physical_run_id="run-profilemissing",
                    contract_sha256="b" * 64,
                    scenario_contract_sha256="c" * 64,
                    controller_dispatch_root=root / "controller-missing",
                )

            outside = root / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            escaping_path = workspace_root / Path(required_paths[-1])
            try:
                escaping_path.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink creation is unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "escapes staged Skill root"):
                stage_desktop_subject(
                    slot,
                    manifest,
                    workspace,
                    generation=1,
                    attempt=1,
                    physical_run_id="run-profileescape",
                    contract_sha256="b" * 64,
                    scenario_contract_sha256="c" * 64,
                    controller_dispatch_root=root / "controller-escape",
                )

    def test_implicit_legacy_comparison_arms_keep_manifest_declaration_order(
        self,
    ) -> None:
        raw = _profile_pilot_manifest_raw()
        raw["benchmark_version"] = "0.3.1-legacy-order"
        raw["freeze_policy"] = "post_pilot"
        raw["arms"] = [
            raw["arms"][0],
            raw["arms"][3],
            raw["arms"][2],
            raw["arms"][1],
            raw["arms"][4],
            raw["arms"][5],
            raw["arms"][6],
        ]
        for scenario in raw["scenarios"]:
            scenario.pop("comparison_arms")
            scenario.pop("profile_under_test")
            scenario.pop("scenario_type")
            scenario.pop("direct_comparator")
            scenario.pop("treatment_arm")
            scenario.pop("incremental_criteria")

        manifest = validate_manifest(raw)

        expected_arm_order = tuple(arm["id"] for arm in raw["arms"])
        self.assertEqual(
            {expected_arm_order},
            {tuple(scenario["comparison_arms"]) for scenario in manifest.scenarios},
        )

    def test_scenario_specific_arms_expand_to_the_complete_m2_run_matrix(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        slots = build_run_slots(manifest)

        self.assertEqual("pre_execution", manifest.freeze_policy)
        self.assertEqual(34, len(slots))
        self.assertEqual(34, len({slot.run_id for slot in slots}))
        self.assertEqual({1}, {slot.repetition for slot in slots})
        self.assertEqual(
            tuple(arm.id for arm in manifest.arms),
            (
                "control",
                "generic-clean-code",
                "core-only",
                "core-plus-csharp",
                "core-plus-python",
                "core-plus-typescript",
                "core-plus-typescript-plus-react",
            ),
        )

        slots_by_scenario = {
            scenario_id: {
                slot.run_id
                for slot in slots
                if slot.scenario_id == scenario_id
            }
            for scenario_id, *_ in PROFILE_PILOT_MATRIX
        }
        scenarios_by_id = {scenario["id"]: scenario for scenario in manifest.scenarios}
        for (
            scenario_id,
            _language,
            _profile,
            _scenario_type,
            comparison_arms,
            direct_comparator,
            treatment_arm,
        ) in PROFILE_PILOT_MATRIX:
            with self.subTest(scenario_id=scenario_id):
                scenario = scenarios_by_id[scenario_id]
                self.assertEqual(comparison_arms, tuple(scenario["comparison_arms"]))
                self.assertEqual(direct_comparator, scenario["direct_comparator"])
                self.assertEqual(treatment_arm, scenario["treatment_arm"])
                self.assertEqual(
                    {
                        f"{scenario_id}--{arm_id}--r01"
                        for arm_id in comparison_arms
                    },
                    slots_by_scenario[scenario_id],
                )

    def test_profile_pilot_manifest_rejects_invalid_campaign_matrix(self) -> None:
        cases = (
            ("duplicate arm", lambda raw: raw["arms"].append(copy.deepcopy(raw["arms"][0]))),
            (
                "unknown comparison arm",
                lambda raw: raw["scenarios"][0]["comparison_arms"].append("unknown"),
            ),
            (
                "comparison arms must not be empty",
                lambda raw: raw["scenarios"][0].__setitem__("comparison_arms", []),
            ),
            (
                "direct comparator",
                lambda raw: raw["scenarios"][0].__setitem__(
                    "direct_comparator", "core-plus-python"
                ),
            ),
            (
                "treatment arm",
                lambda raw: raw["scenarios"][0].__setitem__(
                    "treatment_arm", "core-plus-python"
                ),
            ),
            (
                "duplicate scenario",
                lambda raw: raw["scenarios"][1].__setitem__(
                    "id", raw["scenarios"][0]["id"]
                ),
            ),
            (
                "scenario type",
                lambda raw: raw["scenarios"][0].__setitem__(
                    "scenario_type", "unknown"
                ),
            ),
            (
                "profile comparison arms",
                lambda raw: (
                    raw["scenarios"][6].__setitem__("direct_comparator", "control"),
                    raw["scenarios"][6].__setitem__(
                        "treatment_arm", "generic-clean-code"
                    ),
                ),
            ),
        )
        for expected_message, mutate in cases:
            with self.subTest(expected_message=expected_message):
                raw = _profile_pilot_manifest_raw()
                mutate(raw)
                with self.assertRaisesRegex(ValueError, expected_message):
                    validate_manifest(raw)

    def test_reviews_reject_duplicate_candidates_for_one_evidence_id(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        slot = build_run_slots(manifest)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review_key_path = root / "review-key.json"
            reviews_root = root / "reviews"
            reviews_root.mkdir()
            review_key_path.write_text(
                json.dumps(
                    {
                        "candidates": {
                            "candidate-one": {"evidence_id": "evidence-one"},
                            "candidate-two": {"evidence_id": "evidence-one"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            for candidate_id in ("candidate-one", "candidate-two"):
                (reviews_root / f"{candidate_id}.json").write_text(
                    json.dumps({"rubrics": {}}), encoding="utf-8"
                )
            paths = SimpleNamespace(
                review_key_path=review_key_path,
                reviews_root=reviews_root,
            )
            with (
                patch.object(harness_cli, "build_run_slots", return_value=(slot,)),
                patch.object(
                    harness_cli,
                    "_read_run_document",
                    return_value={"evidence_id": "evidence-one"},
                ),
            ):
                with self.assertRaisesRegex(ValueError, "duplicate review candidate"):
                    harness_cli._reviews_by_run(manifest, paths)

    def test_cli_uses_repository_relative_manifest_and_campaign_runs_root(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            manifest_path = (
                repository_root / "evals" / "manifests" / "profile-pilot.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps({}), encoding="utf-8")
            expected_runs_root = (
                repository_root / ".benchmark-runs" / "profile-pilot"
            )

            with (
                patch.object(harness_cli, "ROOT", repository_root),
                patch.object(harness_cli, "load_manifest", return_value=manifest) as load,
                patch.object(harness_cli, "_verify_freeze") as verify,
            ):
                self.assertEqual(
                    0,
                    harness_main(
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "--runs-root",
                            ".benchmark-runs/profile-pilot",
                            "verify-freeze",
                        ]
                    ),
                )

            load.assert_called_once_with(manifest_path.resolve())
            verify.assert_called_once()
            actual_manifest, actual_paths = verify.call_args.args
            self.assertIs(manifest, actual_manifest)
            self.assertEqual(repository_root.resolve(), actual_paths.repository_root)
            self.assertEqual(expected_runs_root.resolve(), actual_paths.runs_root)
            self.assertEqual(
                expected_runs_root.resolve() / "sources" / "fixtures",
                actual_paths.fixture_clone,
            )

    def test_cli_build_result_uses_a_safe_repository_relative_output(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            manifest_path = (
                repository_root / "evals" / "manifests" / "profile-pilot.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps({}), encoding="utf-8")
            result_root = repository_root / "evals" / "results"
            result_root.mkdir(parents=True)
            expected_output = result_root / "profile-pilot.json"

            with (
                patch.object(harness_cli, "ROOT", repository_root),
                patch.object(harness_cli, "load_manifest", return_value=manifest),
                patch.object(harness_cli, "_write_result") as write_result,
            ):
                self.assertEqual(
                    0,
                    harness_main(
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "--runs-root",
                            ".benchmark-runs/profile-pilot",
                            "build-result",
                            "--output",
                            "evals/results/profile-pilot.json",
                        ]
                    ),
                )

            self.assertEqual(expected_output.resolve(), write_result.call_args.args[2])

    def test_cli_rejects_unsafe_campaign_and_result_paths(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            manifest_path = (
                repository_root / "evals" / "manifests" / "profile-pilot.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps({}), encoding="utf-8")
            (manifest_path.with_suffix(".txt")).write_text("{}", encoding="utf-8")
            result_root = repository_root / "evals" / "results"
            result_root.mkdir(parents=True)
            existing_output = result_root / "existing.json"
            existing_output.write_text("{}", encoding="utf-8")

            with (
                patch.object(harness_cli, "ROOT", repository_root),
                patch.object(harness_cli, "load_manifest", return_value=manifest),
                patch.object(harness_cli, "_write_result"),
            ):
                unsafe_arguments = (
                    (
                        [
                            "--manifest",
                            str(manifest_path.resolve()),
                            "verify-freeze",
                        ],
                        ValueError,
                        "repository-relative",
                    ),
                    (
                        ["--manifest", "../profile-pilot.json", "verify-freeze"],
                        ValueError,
                        "repository-relative",
                    ),
                    (
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.txt",
                            "verify-freeze",
                        ],
                        ValueError,
                        "JSON",
                    ),
                    (
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "--runs-root",
                            "runs/profile-pilot",
                            "verify-freeze",
                        ],
                        ValueError,
                        "inside .benchmark-runs",
                    ),
                    (
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "--runs-root",
                            ".benchmark-runs/../shared",
                            "verify-freeze",
                        ],
                        ValueError,
                        "repository-relative",
                    ),
                    (
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "build-result",
                            "--output",
                            str((result_root / "absolute.json").resolve()),
                        ],
                        ValueError,
                        "repository-relative",
                    ),
                    (
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "build-result",
                            "--output",
                            "evals/results/../outside.json",
                        ],
                        ValueError,
                        "repository-relative",
                    ),
                    (
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "build-result",
                            "--output",
                            "evals/output/outside.json",
                        ],
                        ValueError,
                        "inside evals/results",
                    ),
                    (
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "build-result",
                            "--output",
                            "evals/results/existing.json",
                        ],
                        FileExistsError,
                        "refusing to overwrite result",
                    ),
                )
                for arguments, error_type, expected_message in unsafe_arguments:
                    with self.subTest(arguments=arguments):
                        with self.assertRaisesRegex(error_type, expected_message):
                            harness_main(arguments)

                outside_root = repository_root / "outside"
                outside_root.mkdir()
                escaped_link = result_root / "escaped"
                try:
                    escaped_link.symlink_to(outside_root, target_is_directory=True)
                except OSError as error:
                    self.assertIn("1314", str(error.winerror))
                else:
                    with self.assertRaisesRegex(ValueError, "inside evals/results"):
                        harness_main(
                            [
                                "--manifest",
                                "evals/manifests/profile-pilot.json",
                                "build-result",
                                "--output",
                                "evals/results/escaped/result.json",
                            ]
                        )

    def test_pre_execution_freeze_precedes_pilot_and_uses_campaign_runs_root(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        contract = {"schema_version": "test-contract"}
        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            manifest_path = (
                repository_root / "evals" / "manifests" / "profile-pilot.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps({}), encoding="utf-8")
            runs_root = repository_root / ".benchmark-runs" / "profile-pilot"

            with (
                patch.object(harness_cli, "ROOT", repository_root),
                patch.object(harness_cli, "load_manifest", return_value=manifest),
                patch.object(harness_cli, "_require_preflight") as require_preflight,
                patch.object(harness_cli, "_verify_runs") as verify_runs,
                patch.object(
                    harness_cli,
                    "_freeze_document",
                    return_value=contract,
                ),
            ):
                self.assertEqual(
                    0,
                    harness_main(
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "--runs-root",
                            ".benchmark-runs/profile-pilot",
                            "freeze",
                            "--phase",
                            "pilot",
                            "--decision-note",
                            "approved before subject execution",
                        ]
                    ),
                )

            require_preflight.assert_called_once()
            verify_runs.assert_not_called()
            freeze_paths = list((runs_root / "contract-freezes").glob("*.json"))
            self.assertEqual(1, len(freeze_paths))
            receipt = json.loads(freeze_paths[0].read_text(encoding="utf-8"))
            self.assertEqual("pre_execution", receipt["freeze_policy"])
            self.assertEqual("pilot", receipt["phase"])
            self.assertEqual(contract, receipt["contract"])

    def test_pilot_stage_invalidates_drift_without_overwriting_prior_freeze(self) -> None:
        manifest = validate_manifest(_profile_pilot_manifest_raw())
        prior_contract = {"schema_version": "prior-contract"}
        replacement_contract = {"schema_version": "replacement-contract"}
        prior_contract_sha256 = harness_cli._canonical_sha256(prior_contract)
        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            manifest_path = (
                repository_root / "evals" / "manifests" / "profile-pilot.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps({}), encoding="utf-8")
            runs_root = repository_root / ".benchmark-runs" / "profile-pilot"
            freeze_path = (
                runs_root / "contract-freezes" / f"{prior_contract_sha256}.json"
            )
            freeze_path.parent.mkdir(parents=True)
            freeze_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "contract_sha256": prior_contract_sha256,
                        "contract": prior_contract,
                        "freeze_policy": "pre_execution",
                        "phase": "pilot",
                        "decision_note": "approved",
                    }
                ),
                encoding="utf-8",
            )
            prior_bytes = freeze_path.read_bytes()

            with (
                patch.object(harness_cli, "ROOT", repository_root),
                patch.object(harness_cli, "load_manifest", return_value=manifest),
                patch.object(harness_cli, "_require_preflight"),
                patch.object(
                    harness_cli,
                    "_freeze_document",
                    return_value=replacement_contract,
                ),
                patch.object(harness_cli, "_ensure_fixture_clone") as ensure_fixture,
                patch.object(harness_cli, "build_workspace") as build_workspace,
            ):
                with self.assertRaisesRegex(FileNotFoundError, "contract freeze is missing"):
                    harness_main(
                        [
                            "--manifest",
                            "evals/manifests/profile-pilot.json",
                            "--runs-root",
                            ".benchmark-runs/profile-pilot",
                            "stage",
                            "--phase",
                            "pilot",
                        ]
                    )

            self.assertEqual(prior_bytes, freeze_path.read_bytes())
            invalidations = list((runs_root / "invalidations").glob("*.json"))
            self.assertEqual(1, len(invalidations))
            invalidation = json.loads(invalidations[0].read_text(encoding="utf-8"))
            self.assertEqual("contract_hash_drift", invalidation["reason"])
            self.assertEqual(prior_contract_sha256, invalidation["prior_contract_sha256"])
            ensure_fixture.assert_not_called()
            build_workspace.assert_not_called()

    def test_cli_rejects_two_campaigns_sharing_one_state_file(self) -> None:
        first_manifest = validate_manifest(_profile_pilot_manifest_raw())
        second_raw = _profile_pilot_manifest_raw()
        second_raw["benchmark_version"] = "0.5.1-profile-pilot-alternate"
        second_manifest = validate_manifest(second_raw)
        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            manifests_root = repository_root / "evals" / "manifests"
            manifests_root.mkdir(parents=True)
            for name in ("first.json", "second.json"):
                (manifests_root / name).write_text(json.dumps({}), encoding="utf-8")

            def load_for_path(path: Path):
                return first_manifest if path.name == "first.json" else second_manifest

            with (
                patch.object(harness_cli, "ROOT", repository_root),
                patch.object(harness_cli, "load_manifest", side_effect=load_for_path),
                patch.object(harness_cli, "_prepare"),
            ):
                self.assertEqual(
                    0,
                    harness_main(
                        [
                            "--manifest",
                            "evals/manifests/first.json",
                            "--runs-root",
                            ".benchmark-runs/profile-pilot",
                            "prepare",
                        ]
                    ),
                )
                with self.assertRaisesRegex(RuntimeError, "another campaign"):
                    harness_main(
                        [
                            "--manifest",
                            "evals/manifests/second.json",
                            "--runs-root",
                            ".benchmark-runs/profile-pilot",
                            "prepare",
                        ]
                    )

    def test_two_harness_paths_scope_every_private_campaign_artifact(self) -> None:
        """同一程序的兩個 Campaign 不能共用任何 private evidence root。"""

        manifest = validate_manifest(_profile_pilot_manifest_raw())
        slots = build_run_slots(manifest)
        timeout_slot = next(slot for slot in slots if slot.arm_id == "control")
        invalidated_scenario_id = "fastapi-overdue-rule"
        invalidated_slots = tuple(
            slot for slot in slots if slot.scenario_id == invalidated_scenario_id
        )
        contract = {"schema_version": "scoped-contract"}
        contract_sha256 = harness_cli._canonical_sha256(contract)
        timeout_contract_sha256 = "a" * 64
        prior_contract_sha256 = "b" * 64
        prior_scenario_contract_sha256 = "c" * 64
        replacement_scenario_contract_sha256 = "d" * 64

        def terminal_document(
            slot: object,
            scenario_contract_sha256: str,
            *,
            contract_sha256: str,
            reasons: list[str] | None = None,
        ) -> dict[str, object]:
            run_slot = slot
            return {
                "run_id": run_slot.run_id,
                "scenario_id": run_slot.scenario_id,
                "language": run_slot.language,
                "arm_id": run_slot.arm_id,
                "repetition": run_slot.repetition,
                "order_index": run_slot.order_index,
                "terminal_state": "infrastructure_failure",
                "contract_sha256": contract_sha256,
                "scenario_contract_sha256": scenario_contract_sha256,
                "evidence_id": f"{run_slot.run_id}--g01",
                "automatic_failure_reasons": reasons or [],
            }

        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            manifest_path = (
                repository_root / "evals" / "manifests" / "profile-pilot.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text("{}", encoding="utf-8")
            paths_by_name = {
                name: HarnessPaths(
                    repository_root=repository_root,
                    runs_root=repository_root / ".benchmark-runs" / name,
                    fixture_clone=(
                        repository_root
                        / ".benchmark-runs"
                        / name
                        / "sources"
                        / "fixtures"
                    ),
                    skill_repository=repository_root,
                    manifest_path=manifest_path,
                )
                for name in ("campaign-a", "campaign-b")
            }

            for paths in paths_by_name.values():
                self.assertEqual(
                    paths.runs_root / "run-documents",
                    paths.run_documents_root,
                )
                self.assertEqual(
                    paths.runs_root / "desktop-dispatches",
                    paths.desktop_dispatch_root,
                )
                self.assertEqual(
                    paths.runs_root / "desktop-controller-dispatches",
                    paths.controller_dispatch_root,
                )
                self.assertEqual(
                    paths.runs_root / "desktop-attempt-receipts",
                    paths.attempt_receipts_root,
                )
                self.assertEqual(
                    paths.runs_root / "campaign-state.json",
                    paths.campaign_state_path,
                )
                self.assertEqual(
                    paths.runs_root / "invalidations",
                    paths.invalidations_root,
                )
                self.assertEqual(
                    paths.runs_root / "timeout-adjudications",
                    paths.timeout_adjudications_root,
                )
                self.assertEqual(
                    paths.runs_root / "review-packets",
                    paths.review_packets_root,
                )
                self.assertEqual(paths.runs_root / "reviews", paths.reviews_root)
                self.assertEqual(
                    paths.runs_root / "preflights",
                    paths.preflights_root,
                )
                self.assertEqual(
                    paths.runs_root / "contract-freezes",
                    paths.contract_freezes_root,
                )

                harness_cli._claim_campaign_state_file(manifest, paths)
                harness_cli._write_json(
                    harness_cli._preflight_path(contract_sha256, paths),
                    {"status": "passed", "contract_sha256": contract_sha256},
                )
                with patch.object(
                    harness_cli,
                    "_freeze_document",
                    return_value=contract,
                ):
                    harness_cli._write_freeze(
                        manifest,
                        paths,
                        "scoped pre-execution freeze",
                        "pilot",
                    )

                harness_cli._write_json(
                    harness_cli._run_document_path(timeout_slot, 1, paths),
                    terminal_document(
                        timeout_slot,
                        timeout_contract_sha256,
                        contract_sha256=timeout_contract_sha256,
                        reasons=["oracle_timeout_unclassified"],
                    ),
                )
                dispatch_id = harness_cli._desktop_dispatch_id(timeout_slot, 1, 1)
                physical_run_id = f"run-{paths.runs_root.name[-1]}" + "a" * 15
                workspace = Workspace(
                    paths.workspaces_root / physical_run_id,
                    paths.artifacts_root / physical_run_id,
                    "e" * 40,
                )
                workspace.root.mkdir(parents=True)
                workspace.artifact_dir.mkdir(parents=True)
                report_path = workspace.root / ".benchmark-subject-report.json"
                report_path.write_text("{}", encoding="utf-8")
                dispatch = SubjectDispatch(
                    dispatch_id=dispatch_id,
                    logical_run_id=timeout_slot.run_id,
                    physical_run_id=physical_run_id,
                    scenario_id=timeout_slot.scenario_id,
                    arm_id=timeout_slot.arm_id,
                    generation=1,
                    attempt=1,
                    workspace=workspace,
                    prompt_path=workspace.artifact_dir / "prompt.md",
                    report_template_path=(
                        workspace.artifact_dir / "subject-report.template.json"
                    ),
                    report_path=report_path,
                    report_relative_path=".benchmark-subject-report.json",
                    dispatch_path=(
                        paths.controller_dispatch_root / f"{dispatch_id}.json"
                    ),
                    prompt_sha256="f" * 64,
                    contract_sha256=timeout_contract_sha256,
                    scenario_contract_sha256=timeout_contract_sha256,
                    required_skill_inspection_paths=(),
                    dispatch_sha256="0" * 64,
                )
                dispatch.dispatch_path.parent.mkdir(parents=True)
                dispatch.dispatch_path.write_text("{}", encoding="utf-8")
                index_path = harness_cli._write_dispatch_index(dispatch, paths)
                with patch.object(
                    harness_cli,
                    "load_desktop_dispatch",
                    return_value=dispatch,
                ):
                    self.assertEqual(
                        dispatch,
                        harness_cli._load_dispatch_by_id(dispatch_id, paths),
                    )
                receipt_path = write_attempt_receipt(
                    dispatch,
                    paths.attempt_receipts_root,
                    outcome="completed",
                    reason="scoped receipt",
                    elapsed_seconds=1.0,
                    subject_thread_id=None,
                )

                with patch.object(
                    harness_cli,
                    "_scenario_contract_sha256",
                    return_value=timeout_contract_sha256,
                ):
                    harness_cli._adjudicate_timeout(
                        manifest,
                        paths,
                        timeout_slot.run_id,
                        "candidate",
                        "scoped adjudication",
                    )
                    with patch.object(
                        harness_cli,
                        "_phase_slots",
                        return_value=(timeout_slot,),
                    ):
                        harness_cli._write_review_packets(
                            manifest,
                            paths,
                            "pilot",
                        )

                mapping = json.loads(
                    paths.review_key_path.read_text(encoding="utf-8")
                )
                candidate_id = next(iter(mapping["candidates"]))
                review_path = paths.reviews_root / f"{candidate_id}.json"
                review_path.parent.mkdir(parents=True)
                review_path.write_text(
                    json.dumps(
                        {
                            "rubrics": {
                                rubric_id: {
                                    "score": 1,
                                    "reason": "scoped review",
                                }
                                for rubric_id in harness_cli.RUBRIC_IDS
                            },
                            "incremental_criteria": [
                                {
                                    "criterion": criterion,
                                    "score": 1,
                                    "reason": "scoped profile review",
                                }
                                for criterion in next(
                                    scenario
                                    for scenario in manifest.scenarios
                                    if scenario["id"] == timeout_slot.scenario_id
                                )["incremental_criteria"]
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                with (
                    patch.object(
                        harness_cli,
                        "build_run_slots",
                        return_value=(timeout_slot,),
                    ),
                    patch.object(
                        harness_cli,
                        "_scenario_contract_sha256",
                        return_value=timeout_contract_sha256,
                    ),
                ):
                    harness_cli._verify_reviews(manifest, paths)

                state = json.loads(
                    paths.campaign_state_path.read_text(encoding="utf-8")
                )
                state["scenarios"][invalidated_scenario_id] = {"generation": 1}
                harness_cli._replace_json(paths.campaign_state_path, state)
                for slot in invalidated_slots:
                    harness_cli._write_json(
                        harness_cli._run_document_path(slot, 1, paths),
                        terminal_document(
                            slot,
                            prior_scenario_contract_sha256,
                            contract_sha256=prior_contract_sha256,
                        ),
                    )
                with (
                    patch.object(
                        harness_cli,
                        "_freeze_document",
                        return_value={"schema_version": "replacement-contract"},
                    ),
                    patch.object(
                        harness_cli,
                        "_scenario_contract_sha256",
                        return_value=replacement_scenario_contract_sha256,
                    ),
                ):
                    harness_cli._invalidate_pilot(
                        manifest,
                        paths,
                        invalidated_scenario_id,
                        "scoped invalidation",
                    )

                expected_paths = (
                    paths.campaign_state_path,
                    harness_cli._preflight_path(contract_sha256, paths),
                    paths.contract_freezes_root / f"{contract_sha256}.json",
                    harness_cli._run_document_path(timeout_slot, 1, paths),
                    dispatch.dispatch_path,
                    index_path,
                    receipt_path,
                    paths.timeout_adjudications_root
                    / f"{timeout_slot.run_id}--g01.json",
                    paths.review_key_path,
                    paths.review_packets_root / f"{candidate_id}.json",
                    review_path,
                )
                invalidations = list(paths.invalidations_root.glob("*.json"))
                self.assertEqual(1, len(invalidations))
                for artifact_path in (*expected_paths, *invalidations):
                    with self.subTest(artifact_path=artifact_path):
                        self.assertTrue(artifact_path.is_file())
                        self.assertTrue(
                            harness_cli._is_within(
                                artifact_path,
                                paths.runs_root,
                            )
                        )

            first_paths, second_paths = paths_by_name.values()
            self.assertFalse(
                harness_cli._is_within(
                    first_paths.run_documents_root,
                    second_paths.runs_root,
                )
            )
            self.assertFalse(
                harness_cli._is_within(
                    second_paths.run_documents_root,
                    first_paths.runs_root,
                )
            )


if __name__ == "__main__":
    unittest.main()
