from __future__ import annotations

import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from evals.v040_strategy_full_run import (
    collect_run,
    build_prompt,
    build_baseline_slots,
    build_slots,
    evaluate_subject_result,
    load_manifest,
    stage_run,
    tree_sha256,
    verify_public_result,
    verify_runs,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "evals" / "manifests" / "v0.4.0-strategy-full-run.json"


class V040StrategyFullRunTests(unittest.TestCase):
    def test_manifest_covers_the_complete_strategy_matrix(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)

        self.assertEqual("0.4.0-strategy-full-run-v2", manifest["benchmark_version"])
        self.assertEqual(4, manifest["full_run_generation"])
        self.assertEqual("0.4.0", manifest["skill_version"])
        self.assertEqual("gpt-5.6-sol", manifest["model"])
        self.assertEqual("high", manifest["reasoning_effort"])
        self.assertEqual(2, manifest["repetitions"])
        self.assertEqual(9, len(manifest["scenarios"]))

        development_values = {
            scenario["input"]["current_prompt"].get("development_rhythm", "auto")
            for scenario in manifest["scenarios"]
        }
        validation_values = {
            scenario["input"]["current_prompt"].get("validation_profile", "auto")
            for scenario in manifest["scenarios"]
        }
        self.assertEqual(
            {"auto", "direct", "tdd", "tcr", "characterization-first"},
            development_values,
        )
        self.assertEqual(
            {
                "auto",
                "focused",
                "repository",
                "acceptance-e2e",
                "mutation-assisted",
            },
            validation_values,
        )

    def test_planner_builds_eighteen_unique_full_run_slots(self) -> None:
        slots = build_slots(load_manifest(MANIFEST_PATH))

        self.assertEqual(18, len(slots))
        self.assertEqual(18, len({slot["run_id"] for slot in slots}))
        self.assertEqual({1, 2}, {slot["repetition"] for slot in slots})

    def test_planner_builds_nine_no_skill_baseline_slots(self) -> None:
        slots = build_baseline_slots(load_manifest(MANIFEST_PATH))

        self.assertEqual(9, len(slots))
        self.assertEqual(9, len({slot["run_id"] for slot in slots}))
        self.assertTrue(all(slot["arm"] == "baseline" for slot in slots))

    def test_manifest_rejects_an_incomplete_expected_contract(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        del manifest["scenarios"][0]["expected"]["mandatory_gates_preserved"]

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "expected contract"):
                load_manifest(path)

    def test_subject_prompt_hides_the_expected_decision(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        scenario = manifest["scenarios"][0]
        prompt = build_prompt(
            run_id="example--r01",
            scenario=scenario,
            skill_relative_path="skill/clean-code-ai-collaboration/SKILL.md",
            result_relative_path="subject-result.json",
        )

        self.assertIn("skill/clean-code-ai-collaboration/SKILL.md", prompt)
        self.assertIn("subject-result.json", prompt)
        self.assertIn(json.dumps(scenario["input"], ensure_ascii=False), prompt)
        self.assertNotIn(json.dumps(scenario["expected"], ensure_ascii=False), prompt)

    def test_baseline_prompt_does_not_load_or_reveal_the_skill(self) -> None:
        scenario = load_manifest(MANIFEST_PATH)["scenarios"][0]
        prompt = build_prompt(
            run_id="example--baseline--r01",
            scenario=scenario,
            skill_relative_path=None,
            result_relative_path="subject-result.json",
        )

        self.assertNotIn("clean-code-ai-collaboration/SKILL.md", prompt)
        self.assertNotIn("testing-and-change-safety.md", prompt)
        self.assertNotIn(json.dumps(scenario["expected"], ensure_ascii=False), prompt)
        self.assertIn("不得讀取或使用本次未提供的 Skill", prompt)

    def test_oracle_accepts_an_exact_decision_and_rejects_silent_substitution(self) -> None:
        scenario = next(
            item
            for item in load_manifest(MANIFEST_PATH)["scenarios"]
            if item["id"] == "explicit-tcr-without-version-control-authority"
        )
        expected = scenario["expected"]
        valid = {
            **expected,
            "schema_version": "1.0",
            "run_id": "explicit-tcr-without-version-control-authority--r01",
            "files_inspected": [
                "skill/clean-code-ai-collaboration/SKILL.md",
                "skill/clean-code-ai-collaboration/references/testing-and-change-safety.md",
            ],
            "skill_sha256": "a" * 64,
            "rationale": "TCR needs explicit Commit and Revert authority.",
        }

        self.assertEqual([], evaluate_subject_result(scenario, valid))

        substituted = {**valid, "status": "ready", "effective_development_rhythm": "tdd"}
        failures = evaluate_subject_result(scenario, substituted)
        self.assertTrue(any("status" in failure for failure in failures))
        self.assertTrue(
            any("effective_development_rhythm" in failure for failure in failures)
        )

    def test_oracle_requires_auditable_skill_inspection(self) -> None:
        scenario = load_manifest(MANIFEST_PATH)["scenarios"][0]
        result = {
            **scenario["expected"],
            "schema_version": "1.0",
            "run_id": "explicit-tdd-and-acceptance-e2e--r01",
            "files_inspected": [],
            "skill_sha256": "invalid",
            "rationale": "",
        }

        failures = evaluate_subject_result(scenario, result)

        self.assertTrue(any("files_inspected" in failure for failure in failures))
        self.assertTrue(any("skill_sha256" in failure for failure in failures))
        self.assertTrue(any("rationale" in failure for failure in failures))

    def test_oracle_rejects_unknown_subject_fields(self) -> None:
        scenario = load_manifest(MANIFEST_PATH)["scenarios"][0]
        result = {
            **scenario["expected"],
            "schema_version": "1.0",
            "run_id": "explicit-tdd-and-acceptance-e2e--skill-v0.4.0--r01",
            "files_inspected": [
                "skill/clean-code-ai-collaboration/SKILL.md",
                "skill/clean-code-ai-collaboration/references/testing-and-change-safety.md",
            ],
            "skill_sha256": "a" * 64,
            "rationale": "The requested strategy is feasible.",
            "controller_owned_expected_answer": "forged",
        }

        failures = evaluate_subject_result(scenario, result)

        self.assertTrue(any("unknown fields" in failure for failure in failures))

    def test_oracle_rejects_an_unknown_prerequisite_id(self) -> None:
        scenario = load_manifest(MANIFEST_PATH)["scenarios"][0]
        expected = {
            **scenario["expected"],
            "missing_prerequisites": ["invented-prerequisite"],
        }
        result = {
            **expected,
            "schema_version": "1.0",
            "run_id": "unknown-prerequisite--r01",
            "files_inspected": [
                "skill/clean-code-ai-collaboration/SKILL.md",
                "skill/clean-code-ai-collaboration/references/testing-and-change-safety.md",
            ],
            "skill_sha256": "a" * 64,
            "rationale": "The prerequisite is unavailable.",
        }

        failures = evaluate_subject_result({**scenario, "expected": expected}, result)

        self.assertTrue(any("missing_prerequisites" in failure for failure in failures))

    def test_skill_tree_hash_includes_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "SKILL.md").write_text("skill", encoding="utf-8")
            references = root / "references"
            references.mkdir()
            reference = references / "testing.md"
            reference.write_text("first", encoding="utf-8")
            before = tree_sha256(root)

            reference.write_text("second", encoding="utf-8")

            self.assertNotEqual(before, tree_sha256(root))

    def test_manifest_and_generated_prompts_are_utf8(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "prompt.md"
            path.write_text(
                build_prompt(
                    run_id="utf8--r01",
                    scenario=manifest["scenarios"][0],
                    skill_relative_path="skill/clean-code-ai-collaboration/SKILL.md",
                    result_relative_path="subject-result.json",
                ),
                encoding="utf-8",
            )
            self.assertIn("開發節奏", path.read_text(encoding="utf-8"))

    def test_collection_rejects_modified_prompt_or_dispatch(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = build_slots(manifest)[0]
        scenario = next(
            item for item in manifest["scenarios"] if item["id"] == slot["scenario_id"]
        )

        for mutation in {"prompt", "dispatch"}:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary_directory:
                runs_root = Path(temporary_directory)
                staged = stage_run(slot["run_id"], runs_root=runs_root)
                workspace = Path(staged["workspace"])
                dispatch_path = workspace / "dispatch.json"
                dispatch = json.loads(dispatch_path.read_text(encoding="utf-8"))
                result = {
                    **scenario["expected"],
                    "schema_version": "1.0",
                    "run_id": slot["run_id"],
                    "files_inspected": [
                        "skill/clean-code-ai-collaboration/SKILL.md",
                        "skill/clean-code-ai-collaboration/references/testing-and-change-safety.md",
                    ],
                    "skill_sha256": dispatch["skill_file_sha256"],
                    "rationale": "The staged strategy contract supports this decision.",
                }
                (workspace / "subject-result.json").write_text(
                    json.dumps(result, ensure_ascii=False), encoding="utf-8"
                )

                if mutation == "prompt":
                    (workspace / "prompt.md").write_text(
                        "tampered prompt", encoding="utf-8"
                    )
                else:
                    dispatch["scenario_id"] = "forged-scenario"
                    dispatch_path.write_text(
                        json.dumps(dispatch, ensure_ascii=False), encoding="utf-8"
                    )

                with self.assertRaisesRegex(ValueError, "provenance"):
                    collect_run(slot["run_id"], runs_root=runs_root)

    def test_staging_records_the_fixed_manifest_hash(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = build_slots(manifest)[0]

        with tempfile.TemporaryDirectory() as temporary_directory:
            runs_root = Path(temporary_directory)
            staged = stage_run(slot["run_id"], runs_root=runs_root)
            dispatch = json.loads(
                (Path(staged["workspace"]) / "dispatch.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(
            hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
            dispatch["manifest_sha256"],
        )

    def test_verification_replays_the_subject_oracle(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slot = build_slots(manifest)[0]
        scenario = next(
            item for item in manifest["scenarios"] if item["id"] == slot["scenario_id"]
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            runs_root = Path(temporary_directory)
            staged = stage_run(slot["run_id"], runs_root=runs_root)
            workspace = Path(staged["workspace"])
            dispatch = json.loads(
                (workspace / "dispatch.json").read_text(encoding="utf-8")
            )
            result = {
                **scenario["expected"],
                "schema_version": "1.0",
                "run_id": slot["run_id"],
                "files_inspected": [
                    "skill/clean-code-ai-collaboration/SKILL.md",
                    "skill/clean-code-ai-collaboration/references/testing-and-change-safety.md",
                ],
                "skill_sha256": dispatch["skill_file_sha256"],
                "rationale": "The staged strategy contract supports this decision.",
            }
            result_path = workspace / "subject-result.json"
            result_path.write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8"
            )
            collect_run(slot["run_id"], runs_root=runs_root)

            result["status"] = "forged-after-collection"
            result_path.write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8"
            )

            verification = verify_runs(runs_root=runs_root)

            self.assertTrue(
                any(slot["run_id"] in failure for failure in verification["replay_failures"])
            )

    def test_published_result_replays_from_public_receipts(self) -> None:
        verification = verify_public_result(
            ROOT / "evals" / "results" / "v0.4.0-strategy-full-run.json"
        )

        self.assertEqual({"status": "passed", "failures": []}, verification)

    def test_published_result_rejects_tampered_root_metadata(self) -> None:
        published = json.loads(
            (ROOT / "evals" / "results" / "v0.4.0-strategy-full-run.json").read_text(
                encoding="utf-8"
            )
        )
        mutations = {
            "schema_version": "forged",
            "status": "forged",
            "skill_tree_sha256": "0" * 64,
            "baseline_conforming_count": published["baseline_run_count"],
            "scenario_count": published["scenario_count"] - 1,
            "repetitions": published["repetitions"] - 1,
        }

        for field, value in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                tampered = {**published, field: value}
                result_path = Path(directory) / "result.json"
                result_path.write_text(
                    json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
                )

                verification = verify_public_result(result_path)

                self.assertEqual("failed", verification["status"])
                self.assertTrue(verification["failures"])


if __name__ == "__main__":
    unittest.main()
