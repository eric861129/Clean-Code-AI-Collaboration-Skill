import json
import unittest
from pathlib import Path

from evals.harness.manifest import validate_manifest
from evals.harness.planner import build_run_slots


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ".agents/skills/clean-code-ai-collaboration"
APPLIED_PROFILES = {
    "control": [],
    "generic-clean-code": [],
    "core-only": [],
    "core-plus-csharp": ["csharp"],
    "core-plus-python": ["python"],
    "core-plus-typescript": ["typescript"],
    "core-plus-typescript-plus-react": ["typescript", "react"],
}


def legacy_manifest():
    return json.loads(
        (ROOT / "evals/manifests/v0.5.1-profile-pilot.json").read_text("utf-8")
    )


def policy_manifest():
    raw = legacy_manifest()
    raw["benchmark_version"] = "0.5.2-profile-pilot"
    raw["execution"]["subject_executor"]["protocol_version"] = "desktop-subject-v5"
    for arm in raw["arms"]:
        arm["inspection_policy"] = "required-subset/v1"
        arm["applied_profiles"] = APPLIED_PROFILES[arm["id"]].copy()
        arm["required_skill_inspection_paths"].sort()
        arm["allowed_skill_inspection_paths"] = sorted(
            arm["required_skill_inspection_paths"]
            + ([f"{SKILL_ROOT}/references/testing-and-change-safety.md"]
               if arm.get("skill") else [])
        )
    return raw


class ArmInspectionPolicyTests(unittest.TestCase):
    def test_fixed_skill_and_non_skill_arms_cannot_exchange_roles(self):
        raw = policy_manifest()
        core = raw["arms"][2]
        del core["skill"]
        del core["version"]
        core["required_skill_inspection_paths"] = []
        core["allowed_skill_inspection_paths"] = []
        with self.assertRaises(ValueError):
            validate_manifest(raw)
        raw = policy_manifest()
        raw["arms"][0] = dict(raw["arms"][2], id="control")
        with self.assertRaises(ValueError):
            validate_manifest(raw)

    def test_legacy_arm_mapping_and_profile_path_order_are_unchanged(self):
        raw = legacy_manifest()
        manifest = validate_manifest(raw)
        self.assertEqual(dict(manifest.arms[0]), {"id": "control", "instruction": ""})
        self.assertEqual(dict(manifest.arms[3]), raw["arms"][3])
        self.assertIsNone(manifest.arms[3].inspection_policy)
        self.assertEqual(len(build_run_slots(manifest)), 34)

    def test_canary_name_retains_profile_attribution_and_exact_eleven_slots(self):
        raw = policy_manifest()
        raw["benchmark_version"] = "0.5.2-profile-protocol-canary"
        canary_arms = {
            "csharp-overdue-rule": ["core-only", "core-plus-csharp"],
            "fastapi-provider-boundary": ["core-only", "core-plus-python"],
            "typescript-runtime-validation": ["control", "generic-clean-code", "core-only", "core-plus-typescript"],
            "react-state-error-retention": ["core-only", "core-plus-typescript", "core-plus-typescript-plus-react"],
        }
        raw["scenarios"] = [scenario for scenario in raw["scenarios"] if scenario["id"] in canary_arms]
        for scenario in raw["scenarios"]:
            scenario["comparison_arms"] = canary_arms[scenario["id"]]
        self.assertEqual(len(build_run_slots(validate_manifest(raw))), 11)
        del raw["scenarios"][0]["profile_under_test"]
        with self.assertRaises(ValueError):
            validate_manifest(raw)

    def test_applied_profiles_are_fixed_to_the_arm_and_its_required_references(self):
        for index, profiles in ((0, ["python"]), (2, ["python"]), (4, ["go"]),
                                (4, []), (4, ["python", "python"]),
                                (4, "python"), (4, None), (4, [False]),
                                (6, ["react", "typescript"])):
            with self.subTest(index=index, profiles=profiles):
                raw = policy_manifest()
                raw["arms"][index]["applied_profiles"] = profiles
                with self.assertRaises(ValueError):
                    validate_manifest(raw)
        for forbidden in ("language-python.md", "language-go.md", "framework-vue.md",
                          "Framework-React.md"):
            with self.subTest(forbidden=forbidden):
                raw = policy_manifest()
                paths = raw["arms"][2]["allowed_skill_inspection_paths"]
                paths.append(f"{SKILL_ROOT}/references/{forbidden}")
                paths.sort()
                with self.assertRaises(ValueError):
                    validate_manifest(raw)
        for missing in ("language-python.md", "profile-selection.md"):
            with self.subTest(missing=missing):
                raw = policy_manifest()
                raw["arms"][4]["required_skill_inspection_paths"].remove(
                    f"{SKILL_ROOT}/references/{missing}"
                )
                with self.assertRaises(ValueError):
                    validate_manifest(raw)

    def test_v5_paths_are_explicit_safe_sorted_unique_and_required_are_allowed(self):
        invalid_paths = [
            None, "not-an-array", [False], [],
            [f"{SKILL_ROOT}/SKILL.md"] * 2,
            [f"{SKILL_ROOT}/references/profile-selection.md", f"{SKILL_ROOT}/SKILL.md"],
            [f"{SKILL_ROOT}/SKILL.md", f"{SKILL_ROOT}/../secret.md"],
            [f"{SKILL_ROOT}/SKILL.md", "C:/secret.md"],
            [f"{SKILL_ROOT}/SKILL.md", "/secret.md"],
            [f"{SKILL_ROOT}/SKILL.md", f"{SKILL_ROOT}/references\\extra.md"],
            [f"{SKILL_ROOT}/SKILL.md", f"{SKILL_ROOT}/references/./extra.md"],
            [f"{SKILL_ROOT}/SKILL.md", f"{SKILL_ROOT}/references/*.md"],
            [f"{SKILL_ROOT}/SKILL.md", f"{SKILL_ROOT}/references/extra.md:secret"],
            [f"{SKILL_ROOT}/SKILL.md", f"{SKILL_ROOT}/references/extra\u0000.md"],
        ]
        for field in ("required_skill_inspection_paths", "allowed_skill_inspection_paths"):
            for paths in invalid_paths:
                with self.subTest(field=field, paths=paths):
                    raw = policy_manifest()
                    raw["arms"][2][field] = paths
                    with self.assertRaises(ValueError):
                        validate_manifest(raw)
        raw = policy_manifest()
        raw["arms"][2]["allowed_skill_inspection_paths"] = [f"{SKILL_ROOT}/SKILL.md"]
        with self.assertRaises(ValueError):
            validate_manifest(raw)

    def test_version_selection_never_silently_downgrades_policy(self):
        for protocol in ("desktop-subject-v6", None, [], {}):
            with self.subTest(protocol=protocol):
                raw = legacy_manifest()
                raw["execution"]["subject_executor"]["protocol_version"] = protocol
                with self.assertRaises(ValueError):
                    validate_manifest(raw)
        for field in ("inspection_policy", "allowed_skill_inspection_paths", "applied_profiles",
                      "required_skill_inspection_paths"):
            with self.subTest(missing_v5_field=field):
                raw = policy_manifest()
                del raw["arms"][0][field]
                with self.assertRaises(ValueError):
                    validate_manifest(raw)
        for field in ("inspection_policy", "allowed_skill_inspection_paths", "applied_profiles"):
            with self.subTest(unexpected_v4_field=field):
                raw = legacy_manifest()
                raw["arms"][0][field] = policy_manifest()["arms"][0][field]
                with self.assertRaises(ValueError):
                    validate_manifest(raw)
        raw = policy_manifest()
        raw["arms"][0]["inspection_policy"] = "exact-set"
        with self.assertRaises(ValueError):
            validate_manifest(raw)

    def test_v5_preserves_explicit_policy_and_allows_extra_core_references(self):
        manifest = validate_manifest(policy_manifest())
        core = next(arm for arm in manifest.arms if arm.id == "core-only")
        self.assertEqual(core.inspection_policy, "required-subset/v1")
        self.assertEqual(core.applied_profiles, ())
        self.assertEqual(
            core.allowed_skill_inspection_paths,
            (f"{SKILL_ROOT}/SKILL.md",
             f"{SKILL_ROOT}/references/profile-selection.md",
             f"{SKILL_ROOT}/references/testing-and-change-safety.md"),
        )
        self.assertEqual(dict(manifest.arms[0])["required_skill_inspection_paths"], [])
        self.assertEqual(len(build_run_slots(manifest)), 34)


if __name__ == "__main__":
    unittest.main()
