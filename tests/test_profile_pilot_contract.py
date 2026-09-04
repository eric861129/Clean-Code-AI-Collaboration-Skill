import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import evals.harness.cli as harness_cli
from evals.harness.cli import main as harness_main
from evals.harness.desktop_subject import write_attempt_receipt
from evals.harness.manifest import validate_manifest
from evals.harness.models import HarnessPaths, SubjectDispatch, Workspace
from evals.harness.planner import build_run_slots


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


def _profile_pilot_manifest_raw() -> dict[str, object]:
    arms = [
        {"id": "control", "instruction": ""},
        {"id": "generic-clean-code", "instruction": "請遵守 Clean Code 完成任務。"},
        {"id": "core-only", "instruction": "請使用 Core Only 完成任務。"},
        {"id": "core-plus-csharp", "instruction": "請使用 Core 與 C# Profile 完成任務。"},
        {"id": "core-plus-python", "instruction": "請使用 Core 與 Python Profile 完成任務。"},
        {
            "id": "core-plus-typescript",
            "instruction": "請使用 Core 與 TypeScript Profile 完成任務。",
        },
        {
            "id": "core-plus-typescript-plus-react",
            "instruction": "請使用 Core、TypeScript 與 React Profile 完成任務。",
        },
    ]
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
        )
        for expected_message, mutate in cases:
            with self.subTest(expected_message=expected_message):
                raw = _profile_pilot_manifest_raw()
                mutate(raw)
                with self.assertRaisesRegex(ValueError, expected_message):
                    validate_manifest(raw)

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
                            }
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
