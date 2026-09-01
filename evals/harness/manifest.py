from __future__ import annotations

import json
import re
from pathlib import Path

from evals.harness.models import BenchmarkManifest

EXPECTED_ARM_IDS = {"control", "generic-clean-code", "skill-v0.3.0"}
EXPECTED_SCENARIO_IDS = {
    "react-overdue-rule",
    "react-effect-lifecycle",
    "fastapi-overdue-rule",
    "fastapi-provider-boundary",
}
DESKTOP_EXECUTOR_KIND = "codex-desktop-collaboration"
DESKTOP_REPORT_PATH = ".benchmark-subject-report.json"
DESKTOP_DISPATCH_MODE = "external-collaboration-subagent"
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
    arms = _required_mapping_sequence(raw, "arms")
    scenarios = _required_mapping_sequence(raw, "scenarios")

    fixture_commit = str(fixture_repository.get("commit", ""))
    if re.fullmatch(r"[0-9a-f]{40}", fixture_commit) is None:
        raise ValueError("fixture commit must be a 40-character fixture commit")

    skill_commit = str(skill.get("commit", ""))
    if re.fullmatch(r"[0-9a-f]{40}", skill_commit) is None:
        raise ValueError("skill commit must be a 40-character skill commit")

    arm_ids = [str(arm.get("id", "")) for arm in arms]
    unknown_arms = set(arm_ids) - EXPECTED_ARM_IDS
    if unknown_arms:
        raise ValueError(f"unknown arm: {sorted(unknown_arms)}")
    if set(arm_ids) != EXPECTED_ARM_IDS or len(arm_ids) != len(EXPECTED_ARM_IDS):
        raise ValueError("manifest must define each expected arm exactly once")

    scenario_ids = [str(scenario.get("id", "")) for scenario in scenarios]
    if set(scenario_ids) != EXPECTED_SCENARIO_IDS or len(scenario_ids) != len(
        EXPECTED_SCENARIO_IDS
    ):
        raise ValueError("manifest must define each expected scenario exactly once")
    for scenario in scenarios:
        missing = REQUIRED_SCENARIO_FIELDS - set(scenario)
        if missing:
            raise ValueError(
                f"scenario {scenario.get('id', '<unknown>')} missing fields: "
                f"{sorted(missing)}"
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

    repetitions = _positive_integer(execution, "repetitions")
    if repetitions != 3:
        raise ValueError("cross-language benchmark requires exactly 3 repetitions")

    if execution.get("client") != DESKTOP_EXECUTOR_KIND:
        raise ValueError("cross-language benchmark requires Desktop collaboration")
    if subject_executor.get("kind") != DESKTOP_EXECUTOR_KIND:
        raise ValueError("subject executor must be Desktop collaboration")
    if subject_executor.get("protocol_version") != "desktop-subject-v2":
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
        scenarios=tuple(scenarios),
        arms=tuple(arms),
    )


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
