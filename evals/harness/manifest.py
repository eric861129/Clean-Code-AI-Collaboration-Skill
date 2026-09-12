from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from evals.harness.models import ArmDefinition, BenchmarkManifest

DESKTOP_EXECUTOR_KIND = "codex-desktop-collaboration"
DESKTOP_REPORT_PATH = ".benchmark-subject-report.json"
DESKTOP_DISPATCH_MODE = "external-collaboration-subagent"
FREEZE_POLICIES = {"post_pilot", "pre_execution"}
PROFILE_SCENARIO_TYPES = {"shared_business", "ecosystem_native"}
PROFILE_COMPARISON_ARMS = {
    "csharp": ("core-only", "core-plus-csharp"),
    "python": ("core-only", "core-plus-python"),
    "typescript": ("core-only", "core-plus-typescript"),
    "react": (
        "core-plus-typescript",
        "core-plus-typescript-plus-react",
    ),
}
PROFILE_ARM_ASSIGNMENTS = {
    "control": (),
    "generic-clean-code": (),
    "core-only": (),
    "core-plus-csharp": ("csharp",),
    "core-plus-python": ("python",),
    "core-plus-typescript": ("typescript",),
    "core-plus-typescript-plus-react": ("typescript", "react"),
}
PROFILE_REFERENCE_FILES = {
    "csharp": "language-csharp.md",
    "python": "language-python.md",
    "typescript": "language-typescript.md",
    "react": "framework-react.md",
}
IDENTIFIER_PATTERN = r"[a-z0-9]+(?:[.-][a-z0-9]+)*"
REQUIRED_SCENARIO_FIELDS = {
    "id",
    "language",
    "fixture_path",
    "evaluator_path",
    "task",
    "must_preserve",
    "allowed_diff",
    "allowed_diff_patterns",
    "prohibited_changes",
    "commands",
    "expected_baseline_red_markers",
    "expected_baseline_failure_count",
}


def load_manifest(path: Path) -> BenchmarkManifest:
    return validate_manifest(json.loads(path.read_text(encoding="utf-8")))


def validate_manifest(raw: dict[str, object]) -> BenchmarkManifest:
    fixture_repository = _required_mapping(raw, "fixture_repository")
    skill = _required_mapping(raw, "skill")
    execution = _required_mapping(raw, "execution")
    subject_executor = _required_mapping(execution, "subject_executor")
    freeze_policy = str(raw.get("freeze_policy", "post_pilot"))
    if freeze_policy not in FREEZE_POLICIES:
        raise ValueError("freeze policy is invalid")
    requires_profile_contract = (
        freeze_policy == "pre_execution"
        or "profile-pilot" in str(raw.get("benchmark_version", ""))
    )
    arms = _arm_definitions(
        _required_mapping_sequence(raw, "arms"),
        require_explicit_inspection_paths=requires_profile_contract,
        protocol_version=subject_executor.get("protocol_version"),
    )
    _validate_arm_skill_contract(arms, skill)
    scenarios = _scenario_definitions(
        _required_mapping_sequence(raw, "scenarios"),
        arm_ids=tuple(arm.id for arm in arms),
        requires_profile_attribution=requires_profile_contract,
    )

    fixture_commit = str(fixture_repository.get("commit", ""))
    if re.fullmatch(r"[0-9a-f]{40}", fixture_commit) is None:
        raise ValueError("fixture commit must be a 40-character fixture commit")

    skill_commit = str(skill.get("commit", ""))
    if re.fullmatch(r"[0-9a-f]{40}", skill_commit) is None:
        raise ValueError("skill commit must be a 40-character skill commit")

    repetitions = _positive_integer(execution, "repetitions")

    if execution.get("client") != DESKTOP_EXECUTOR_KIND:
        raise ValueError("cross-language benchmark requires Desktop collaboration")
    if subject_executor.get("kind") != DESKTOP_EXECUTOR_KIND:
        raise ValueError("subject executor must be Desktop collaboration")
    if subject_executor.get("protocol_version") not in (
        "desktop-subject-v4", "desktop-subject-v5"
    ):
        raise ValueError("subject executor protocol version is invalid")
    if subject_executor.get("dispatch_mode") != DESKTOP_DISPATCH_MODE:
        raise ValueError("subject executor dispatch mode is invalid")
    if subject_executor.get("report_relative_path") != DESKTOP_REPORT_PATH:
        raise ValueError("subject executor report path is invalid")
    if subject_executor.get("network_enforcement") != "not_available":
        raise ValueError("Desktop network enforcement must be not_available")
    if subject_executor.get("telemetry") != "not_available":
        raise ValueError("Desktop telemetry must be not_available")

    return BenchmarkManifest(
        schema_version=str(raw.get("schema_version", "")),
        benchmark_version=str(raw.get("benchmark_version", "")),
        fixture_url=str(fixture_repository.get("url", "")),
        fixture_tag=str(fixture_repository.get("tag", "")),
        fixture_commit=fixture_commit,
        skill_tag=str(skill.get("tag", "")),
        skill_commit=skill_commit,
        model=str(execution.get("model", "")),
        reasoning_effort=str(execution.get("reasoning_effort", "")),
        client=str(execution.get("client", "")),
        subject_executor=subject_executor,
        subject_timeout_seconds=_positive_integer(
            execution, "subject_timeout_seconds"
        ),
        fixture_timeout_seconds=_positive_integer(
            execution, "fixture_timeout_seconds"
        ),
        oracle_timeout_seconds=_positive_integer(execution, "oracle_timeout_seconds"),
        repetitions=repetitions,
        random_seed=_positive_integer(execution, "random_seed"),
        freeze_policy=freeze_policy,
        scenarios=scenarios,
        arms=arms,
    )


def _arm_definitions(
    raw_arms: list[dict[str, object]],
    *,
    require_explicit_inspection_paths: bool,
    protocol_version: object,
) -> tuple[ArmDefinition, ...]:
    arms: list[ArmDefinition] = []
    seen_ids: set[str] = set()
    for raw_arm in raw_arms:
        policy_fields = {
            "inspection_policy", "allowed_skill_inspection_paths", "applied_profiles"
        }
        if protocol_version == "desktop-subject-v5":
            missing = (policy_fields | {"required_skill_inspection_paths"}) - raw_arm.keys()
            if missing:
                raise ValueError(f"v5 arm is missing inspection policy fields: {sorted(missing)}")
            if raw_arm["inspection_policy"] != "required-subset/v1":
                raise ValueError("v5 arm inspection policy is invalid")
        elif policy_fields & raw_arm.keys():
            raise ValueError("legacy arm cannot declare v5 inspection policy fields")
        arm_id = raw_arm.get("id")
        if not isinstance(arm_id, str) or re.fullmatch(IDENTIFIER_PATTERN, arm_id) is None:
            raise ValueError("arm ID is invalid")
        if arm_id in seen_ids:
            raise ValueError(f"duplicate arm: {arm_id}")
        instruction = raw_arm.get("instruction")
        if not isinstance(instruction, str):
            raise ValueError(f"arm instruction is invalid: {arm_id}")
        skill = raw_arm.get("skill")
        if skill is not None and (
            not isinstance(skill, str)
            or re.fullmatch(IDENTIFIER_PATTERN, skill) is None
        ):
            raise ValueError(f"arm Skill is invalid: {arm_id}")
        version = raw_arm.get("version")
        if version is not None and (
            not isinstance(version, str) or not version.strip()
        ):
            raise ValueError(f"arm version is invalid: {arm_id}")
        if skill is None and version is not None:
            raise ValueError(f"arm without a Skill cannot declare a version: {arm_id}")
        required_skill_inspection_paths = _arm_inspection_paths(
            raw_arm,
            arm_id,
            skill,
            require_explicit=require_explicit_inspection_paths,
        )
        allowed_skill_inspection_paths: tuple[str, ...] = ()
        applied_profiles: tuple[str, ...] = ()
        if protocol_version == "desktop-subject-v5":
            allowed_skill_inspection_paths = _arm_inspection_paths(
                {"required_skill_inspection_paths": raw_arm["allowed_skill_inspection_paths"]},
                arm_id,
                skill,
                require_explicit=True,
            )
            for paths in (required_skill_inspection_paths, allowed_skill_inspection_paths):
                _validate_canonical_policy_paths(paths, arm_id)
            if not set(required_skill_inspection_paths) <= set(allowed_skill_inspection_paths):
                raise ValueError(f"required Skill inspection paths must be allowed: {arm_id}")
            applied_profiles = _arm_applied_profiles(
                raw_arm["applied_profiles"], arm_id, skill,
                required_skill_inspection_paths, allowed_skill_inspection_paths,
            )
        arms.append(
            ArmDefinition(
                id=arm_id,
                instruction=instruction,
                skill=skill,
                version=version,
                required_skill_inspection_paths=required_skill_inspection_paths,
                inspection_policy=raw_arm.get("inspection_policy") if protocol_version == "desktop-subject-v5" else None,
                allowed_skill_inspection_paths=allowed_skill_inspection_paths,
                applied_profiles=applied_profiles,
            )
        )
        seen_ids.add(arm_id)
    if "control" not in seen_ids:
        raise ValueError("manifest must define a control arm")
    return tuple(arms)


def _validate_canonical_policy_paths(paths: tuple[str, ...], arm_id: str) -> None:
    """新協定使用跨平台一致、已展開且排序的精確檔案路徑。"""
    if paths != tuple(sorted(paths)):
        raise ValueError(f"v5 inspection paths must be sorted: {arm_id}")
    for path in paths:
        if any(character in path for character in ':*?[]<>|"') or any(
            ord(character) < 32 or ord(character) == 127 for character in path
        ):
            raise ValueError(f"v5 inspection path is invalid: {arm_id}")


def _arm_applied_profiles(
    value: object,
    arm_id: str,
    skill: str | None,
    required_paths: tuple[str, ...],
    allowed_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """固定 Pilot 組別、Profile 相依順序與查閱 Reference 的同一份契約。"""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"applied profiles must be a string array: {arm_id}")
    profiles = tuple(value)
    if profiles != PROFILE_ARM_ASSIGNMENTS.get(arm_id):
        raise ValueError(f"applied profiles do not match the fixed pilot arm: {arm_id}")
    if (skill is None) != (arm_id in {"control", "generic-clean-code"}):
        raise ValueError(f"Skill presence does not match the fixed pilot arm: {arm_id}")
    if skill is None:
        if profiles:
            raise ValueError(f"arm without a Skill cannot apply profiles: {arm_id}")
        return profiles
    reference_root = f".agents/skills/{skill}/references"
    profile_paths = {f"{reference_root}/{PROFILE_REFERENCE_FILES[profile]}" for profile in profiles}
    minimum_paths = profile_paths | {f"{reference_root}/profile-selection.md"}
    if not minimum_paths <= set(required_paths):
        raise ValueError(f"required inspection paths are missing assigned profile references: {arm_id}")
    for path in allowed_paths:
        if PurePosixPath(path).name.lower().startswith(("language-", "framework-")) and path not in profile_paths:
            raise ValueError(f"allowed inspection paths contain an unassigned profile reference: {arm_id}")
    return profiles


def _validate_arm_skill_contract(
    arms: tuple[ArmDefinition, ...], skill: dict[str, object]
) -> None:
    expected_name = skill.get("name")
    allowed_versions = {
        value
        for value in (skill.get("version"), skill.get("tag"))
        if isinstance(value, str) and value
    }
    for arm in arms:
        if arm.skill is None:
            continue
        if arm.version is None:
            raise ValueError(f"Skill arm must declare a version: {arm.id}")
        if (
            isinstance(expected_name, str)
            and expected_name
            and arm.skill != expected_name
        ):
            raise ValueError(f"arm Skill does not match pinned Skill: {arm.id}")
        if arm.version not in allowed_versions:
            raise ValueError(f"arm version does not match pinned Skill: {arm.id}")


def _arm_inspection_paths(
    raw_arm: dict[str, object],
    arm_id: str,
    skill: object,
    *,
    require_explicit: bool,
) -> tuple[str, ...]:
    if "required_skill_inspection_paths" not in raw_arm:
        if require_explicit:
            raise ValueError(
                f"profile arm must declare required Skill inspection paths: {arm_id}"
            )
        if isinstance(skill, str):
            return (f".agents/skills/{skill}/SKILL.md",)
        return ()
    raw_paths = raw_arm["required_skill_inspection_paths"]
    if raw_paths is None:
        raise ValueError(f"arm inspection paths are invalid: {arm_id}")
    if not isinstance(raw_paths, list) or not all(
        isinstance(path, str) and path for path in raw_paths
    ):
        raise ValueError(f"arm inspection paths are invalid: {arm_id}")
    if len(raw_paths) != len(set(raw_paths)):
        raise ValueError(f"duplicate arm inspection path: {arm_id}")
    if skill is None:
        if raw_paths:
            raise ValueError(f"arm without a Skill cannot inspect Skill files: {arm_id}")
        return ()
    if not raw_paths:
        raise ValueError(f"Skill arm inspection paths must not be empty: {arm_id}")

    skill_root = PurePosixPath(".agents") / "skills" / str(skill)
    entrypoint = skill_root / "SKILL.md"
    paths: list[str] = []
    for value in raw_paths:
        path = PurePosixPath(value)
        if (
            "\\" in value
            or path.is_absolute()
            or PureWindowsPath(value).is_absolute()
            or ".." in path.parts
            or value != path.as_posix()
        ):
            raise ValueError(
                f"arm inspection path must be a repository-relative POSIX path: {arm_id}"
            )
        if path == skill_root or skill_root not in path.parents:
            raise ValueError(
                f"arm inspection path must stay inside staged Skill root: {arm_id}"
            )
        paths.append(value)
    if entrypoint.as_posix() not in paths:
        raise ValueError(f"arm inspection paths must include Skill entrypoint: {arm_id}")
    return tuple(paths)


def _scenario_definitions(
    raw_scenarios: list[dict[str, object]],
    *,
    arm_ids: tuple[str, ...],
    requires_profile_attribution: bool,
) -> tuple[dict[str, object], ...]:
    scenarios: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for raw_scenario in raw_scenarios:
        scenario = dict(raw_scenario)
        scenario_id = scenario.get("id")
        if (
            not isinstance(scenario_id, str)
            or re.fullmatch(IDENTIFIER_PATTERN, scenario_id) is None
        ):
            raise ValueError("scenario ID is invalid")
        if scenario_id in seen_ids:
            raise ValueError(f"duplicate scenario: {scenario_id}")
        missing = REQUIRED_SCENARIO_FIELDS - set(scenario)
        if missing:
            raise ValueError(
                f"scenario {scenario_id} missing fields: {sorted(missing)}"
            )
        commands = scenario["commands"]
        if not isinstance(commands, dict) or set(commands) != {
            "public",
            "preservation",
            "acceptance",
        }:
            raise ValueError(
                "scenario commands must define public, preservation, acceptance"
            )
        expected_failure_count = scenario["expected_baseline_failure_count"]
        if (
            not isinstance(expected_failure_count, int)
            or isinstance(expected_failure_count, bool)
            or expected_failure_count <= 0
        ):
            raise ValueError("expected baseline failure count must be positive")
        comparison_arms = _comparison_arms(scenario, arm_ids)
        scenario["comparison_arms"] = comparison_arms
        if requires_profile_attribution:
            _validate_profile_attribution(scenario, comparison_arms)
        scenarios.append(scenario)
        seen_ids.add(scenario_id)
    return tuple(scenarios)


def _comparison_arms(
    scenario: dict[str, object], arm_ids: tuple[str, ...]
) -> tuple[str, ...]:
    raw_comparison_arms = scenario.get("comparison_arms")
    if raw_comparison_arms is None:
        return arm_ids
    if (
        not isinstance(raw_comparison_arms, list)
        or not raw_comparison_arms
        or not all(isinstance(arm_id, str) for arm_id in raw_comparison_arms)
    ):
        raise ValueError("comparison arms must not be empty")
    comparison_arms = tuple(raw_comparison_arms)
    if len(set(comparison_arms)) != len(comparison_arms):
        raise ValueError("duplicate comparison arm")
    unknown_arms = set(comparison_arms) - set(arm_ids)
    if unknown_arms:
        raise ValueError(f"unknown comparison arm: {sorted(unknown_arms)}")
    return comparison_arms


def _validate_profile_attribution(
    scenario: dict[str, object], comparison_arms: tuple[str, ...]
) -> None:
    profile_under_test = scenario.get("profile_under_test")
    if not isinstance(profile_under_test, str) or not profile_under_test.strip():
        raise ValueError("profile under test is required")
    expected_comparison = PROFILE_COMPARISON_ARMS.get(profile_under_test)
    if expected_comparison is None:
        raise ValueError("profile under test is not part of the fixed pilot")
    if scenario.get("scenario_type") not in PROFILE_SCENARIO_TYPES:
        raise ValueError("scenario type is invalid")
    direct_comparator = scenario.get("direct_comparator")
    if direct_comparator not in comparison_arms:
        raise ValueError("direct comparator is not a scenario comparison arm")
    treatment_arm = scenario.get("treatment_arm")
    if treatment_arm not in comparison_arms:
        raise ValueError("treatment arm is not a scenario comparison arm")
    if direct_comparator == treatment_arm:
        raise ValueError("direct comparator and treatment arm must differ")
    if (direct_comparator, treatment_arm) != expected_comparison:
        raise ValueError(
            f"profile comparison arms are invalid: {profile_under_test}"
        )
    incremental_criteria = scenario.get("incremental_criteria")
    if (
        not isinstance(incremental_criteria, list)
        or not incremental_criteria
        or not all(
            isinstance(criterion, str) and criterion.strip()
            for criterion in incremental_criteria
        )
    ):
        raise ValueError("incremental criteria must be a non-empty string array")


def _required_mapping(raw: dict[str, object], name: str) -> dict[str, object]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _required_mapping_sequence(
    raw: dict[str, object], name: str
) -> list[dict[str, object]]:
    value = raw.get(name)
    if not isinstance(value, list) or not all(
        isinstance(item, dict) for item in value
    ):
        raise ValueError(f"{name} must be an array of objects")
    return value


def _positive_integer(raw: dict[str, object], name: str) -> int:
    value = raw.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value
