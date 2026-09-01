from __future__ import annotations

from evals.harness.models import RunSlot

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
) -> dict[str, object]:
    if len(slots) != 36 or len(run_documents) != 36:
        raise ValueError("result requires 36 terminal states")
    documents_by_id = {str(item.get("run_id", "")): item for item in run_documents}
    if len(documents_by_id) != 36 or set(documents_by_id) != {
        slot.run_id for slot in slots
    }:
        raise ValueError("result requires 36 terminal states with unique run IDs")

    public_runs: list[dict[str, object]] = []
    for slot in sorted(slots, key=lambda item: item.order_index):
        document = documents_by_id[slot.run_id]
        terminal_state = str(document.get("terminal_state", ""))
        if terminal_state not in TERMINAL_STATES:
            raise ValueError(f"invalid terminal state: {terminal_state}")
        if "aggregate_score" in document:
            raise ValueError("aggregate score is not allowed")
        public_runs.append(
            {
                "run_id": slot.run_id,
                "scenario_id": slot.scenario_id,
                "language": slot.language,
                "arm_id": slot.arm_id,
                "repetition": slot.repetition,
                "order_index": slot.order_index,
                "terminal_state": terminal_state,
                "automatic_failure_reasons": document.get(
                    "automatic_failure_reasons", []
                ),
                "diff_sha256": document.get("diff_sha256", "not_available"),
                "oracle_results": document.get("oracle_results", []),
                "telemetry": document.get("telemetry", "not_available"),
                "review": document.get("review", "not_available"),
            }
        )
    return {
        "schema_version": "1.0",
        "benchmark_version": "0.3.0-cross-language-initial",
        "status": "complete",
        "runs": public_runs,
    }
