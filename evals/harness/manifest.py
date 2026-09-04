from __future__ import annotations

import json
import re
from pathlib import Path

from evals.harness.models import ArmDefinition, BenchmarkManifest

DESKTOP_EXECUTOR_KIND = "codex-desktop-collaboration"
DESKTOP_REPORT_PATH = ".benchmark-subject-report.json"
DESKTOP_DISPATCH_MODE = "external-collaboration-subagent"
FREEZE_POLICIES = {"post_pilot", "pre_execution"}
PROFILE_SCENARIO_TYPES = {"shared_business", "ecosystem_native"}
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
    arms = _arm_definitions(_required_mapping_sequence(raw, "arms"))
    freeze_policy = str(raw.get("freeze_policy", "post_pilot"))
    if freeze_policy not in FREEZE_POLICIES:
        raise ValueError("freeze policy is invalid")
    scenarios = _scenario_definitions(
        _required_mapping_sequence(raw, "scenarios"),
        arm_ids=tuple(arm.id for arm in arms),
        requires_profile_attribution=(
            freeze_policy == "pre_execution"
            or "profile-pilot" in str(raw.get("benchmark_version", ""))
        ),
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
    if subject_executor.get("protocol_version") != "desktop-subject-v4":
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


def _arm_definitions(raw_arms: list[dict[str, object]]) -> tuple[ArmDefinition, ...]:
    arms: list[ArmDefinition] = []
    seen_ids: set[str] = set()
    for raw_arm in raw_arms:
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
            not isinstance(skill, str) or not skill.strip()
        ):
            raise ValueError(f"arm Skill is invalid: {arm_id}")
        version = raw_arm.get("version")
        if version is not None and (
            not isinstance(version, str) or not version.strip()
        ):
            raise ValueError(f"arm version is invalid: {arm_id}")
        arms.append(
            ArmDefinition(
                id=arm_id,
                instruction=instruction,
                skill=skill,
                version=version,
            )
        )
        seen_ids.add(arm_id)
    if "control" not in seen_ids:
        raise ValueError("manifest must define a control arm")
    return tuple(arms)


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
