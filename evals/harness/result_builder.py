from __future__ import annotations

from jsonschema import Draft202012Validator

from evals.harness.models import BenchmarkManifest, RunSlot
from evals.harness.planner import build_run_slots
from evals.harness.profile_outcomes import build_profile_outcomes

RETRYABLE_INFRASTRUCTURE_REASONS = {
    "harness_error",
    "dependency_cache_error",
    "cli_runner_error",
    "environment_error",
}
TERMINAL_STATES = {
    "passed",
    "automatic_failure",
    "timeout",
    "infrastructure_failure",
}


def can_retry(reason: str, attempt: int) -> bool:
    return attempt == 1 and reason in RETRYABLE_INFRASTRUCTURE_REASONS


def build_public_result(
    slots: tuple[RunSlot, ...],
    run_documents: list[dict[str, object]],
    *,
    benchmark_version: str,
    source_revisions: dict[str, object] | None = None,
    execution: dict[str, object] | None = None,
    review_metadata: dict[str, object] | None = None,
    profile_outcomes: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    profile_fields = (
        source_revisions,
        execution,
        review_metadata,
        profile_outcomes,
    )
    is_profile_result = any(value is not None for value in profile_fields)
    if is_profile_result and any(value is None for value in profile_fields):
        raise ValueError("profile result metadata must be complete")
    expected_count = len(slots)
    if not slots or len(run_documents) != expected_count:
        raise ValueError(f"result requires {expected_count} terminal states")
    slot_ids = {slot.run_id for slot in slots}
    if len(slot_ids) != expected_count:
        raise ValueError("result slots must have unique run IDs")
    documents_by_id = {str(item.get("run_id", "")): item for item in run_documents}
    if len(documents_by_id) != expected_count or set(documents_by_id) != slot_ids:
        raise ValueError(
            f"result requires {expected_count} terminal states with unique run IDs"
        )

    public_runs: list[dict[str, object]] = []
    for slot in sorted(slots, key=lambda item: item.order_index):
        document = documents_by_id[slot.run_id]
        terminal_state = str(document.get("terminal_state", ""))
        if terminal_state not in TERMINAL_STATES:
            raise ValueError(f"invalid terminal state: {terminal_state}")
        if "aggregate_score" in document:
            raise ValueError("aggregate score is not allowed")
        expected_identity = {
            "run_id": slot.run_id,
            "scenario_id": slot.scenario_id,
            "language": slot.language,
            "arm_id": slot.arm_id,
            "repetition": slot.repetition,
            "order_index": slot.order_index,
        }
        actual_identity = {
            key: document.get(key) for key in expected_identity
        }
        if actual_identity != expected_identity:
            raise ValueError(f"result run identity mismatch: {slot.run_id}")
        public_runs.append(
            {
                **expected_identity,
                "terminal_state": terminal_state,
                "contract_sha256": document.get(
                    "contract_sha256", "not_available"
                ),
                "scenario_contract_sha256": document.get(
                    "scenario_contract_sha256", "not_available"
                ),
                "prompt_sha256": document.get(
                    "prompt_sha256", "not_available"
                ),
                "automatic_failure_reasons": document.get(
                    "automatic_failure_reasons", []
                ),
                "diff_sha256": document.get("diff_sha256", "not_available"),
                "oracle_results": _public_oracle_results(
                    document.get("oracle_results", [])
                )
                if is_profile_result
                else document.get("oracle_results", []),
                "telemetry": document.get("telemetry", "not_available"),
                "review": document.get("review", "not_available"),
            }
        )
    result: dict[str, object] = {
        "schema_version": "1.0",
        "benchmark_version": benchmark_version,
        "status": "complete",
        "execution_limitations": [
            "Desktop collaboration telemetry is not available and is not inferred.",
            "Desktop network enforcement is not available from this harness.",
        ],
        "runs": public_runs,
    }
    if is_profile_result:
        if len(slots) != 34:
            raise ValueError("profile result requires 34 terminal states")
        assert source_revisions is not None
        assert execution is not None
        assert review_metadata is not None
        assert profile_outcomes is not None
        profile_ids = [str(item.get("profile_id", "")) for item in profile_outcomes]
        if len(profile_ids) != 4 or len(set(profile_ids)) != 4:
            raise ValueError("profile result requires four unique outcomes")
        result.update(
            {
                "schema_version": "profile-pilot-result/v1",
                "source_revisions": source_revisions,
                "execution": execution,
                "review_metadata": review_metadata,
                "profile_outcomes": profile_outcomes,
            }
        )
    return result


def validate_profile_pilot_result(
    result: dict[str, object],
    manifest: BenchmarkManifest,
    schema: dict[str, object],
    *,
    expected_source_revisions: dict[str, object],
    expected_scenario_contracts: dict[str, str],
) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(result),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise ValueError(f"profile result schema validation failed: {errors[0].message}")
    if result.get("benchmark_version") != manifest.benchmark_version:
        raise ValueError("profile result benchmark version mismatch")

    slots = build_run_slots(manifest)
    expected_slots = sorted(slots, key=lambda slot: slot.order_index)
    runs = result.get("runs")
    if not isinstance(runs, list) or not all(isinstance(run, dict) for run in runs):
        raise ValueError("profile result runs are invalid")
    if [run.get("run_id") for run in runs] != [slot.run_id for slot in expected_slots]:
        raise ValueError("profile result run IDs do not match the manifest")
    for slot, run in zip(expected_slots, runs, strict=True):
        expected_identity = {
            "run_id": slot.run_id,
            "scenario_id": slot.scenario_id,
            "language": slot.language,
            "arm_id": slot.arm_id,
            "repetition": slot.repetition,
            "order_index": slot.order_index,
        }
        if {key: run.get(key) for key in expected_identity} != expected_identity:
            raise ValueError(f"profile result run identity mismatch: {slot.run_id}")

    source_revisions = result.get("source_revisions")
    if not isinstance(source_revisions, dict):
        raise ValueError("profile result source revisions are invalid")
    expected_revisions = {
        "fixture_tag": manifest.fixture_tag,
        "fixture_commit": manifest.fixture_commit,
        "skill_tag": manifest.skill_tag,
        "skill_commit": manifest.skill_commit,
    }
    if {
        key: source_revisions.get(key) for key in expected_revisions
    } != expected_revisions:
        raise ValueError("profile result source revisions do not match the manifest")
    if source_revisions != expected_source_revisions:
        raise ValueError("profile result source revisions do not match current evidence")

    prompts = source_revisions.get("prompts")
    expected_prompt_keys = {
        f"{slot.scenario_id}/{slot.arm_id}" for slot in expected_slots
    }
    if not isinstance(prompts, dict) or set(prompts) != expected_prompt_keys:
        raise ValueError("profile result prompt hashes do not cover the manifest")
    expected_scenario_ids = {str(scenario["id"]) for scenario in manifest.scenarios}
    evaluators = source_revisions.get("evaluators")
    if not isinstance(evaluators, dict) or set(evaluators) != expected_scenario_ids:
        raise ValueError("profile result evaluator hashes do not cover the manifest")
    if set(expected_scenario_contracts) != expected_scenario_ids:
        raise ValueError("expected scenario contracts do not cover the manifest")
    contract_sha256 = source_revisions.get("contract_sha256")
    for run in runs:
        run_id = str(run["run_id"])
        scenario_id = str(run["scenario_id"])
        prompt_key = f"{scenario_id}/{run['arm_id']}"
        if run.get("contract_sha256") != contract_sha256:
            raise ValueError(f"profile result run contract hash mismatch: {run_id}")
        if run.get("scenario_contract_sha256") != expected_scenario_contracts.get(
            scenario_id
        ):
            raise ValueError(
                f"profile result run scenario contract hash mismatch: {run_id}"
            )
        if run.get("prompt_sha256") != prompts.get(prompt_key):
            raise ValueError(f"profile result run prompt hash mismatch: {run_id}")

    execution = result.get("execution")
    if not isinstance(execution, dict):
        raise ValueError("profile result execution contract is invalid")
    expected_execution = {
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
    if execution != expected_execution:
        raise ValueError("profile result execution contract does not match the manifest")

    expected_outcomes = build_profile_outcomes(manifest, runs)
    if result.get("profile_outcomes") != expected_outcomes:
        raise ValueError("profile outcomes do not replay from public runs")


def _public_oracle_results(value: object) -> object:
    if not isinstance(value, list):
        return value
    groups: list[object] = []
    for group in value:
        if not isinstance(group, dict):
            groups.append(group)
            continue
        public_group = dict(group)
        commands = group.get("commands")
        if isinstance(commands, list):
            public_group["commands"] = [
                {
                    key: item
                    for key, item in command.items()
                    if key not in {"stdout", "stderr"}
                }
                if isinstance(command, dict)
                else command
                for command in commands
            ]
        groups.append(public_group)
    return groups
