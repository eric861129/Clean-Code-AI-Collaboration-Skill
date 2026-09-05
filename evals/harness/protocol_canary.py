"""協定 Canary 只檢查操作證據，不計算 Profile 效果或成熟度。"""

CANARY_ARMS = {
    "csharp-overdue-rule": ("core-only", "core-plus-csharp"),
    "fastapi-provider-boundary": ("core-only", "core-plus-python"),
    "typescript-runtime-validation": ("control", "generic-clean-code", "core-only", "core-plus-typescript"),
    "react-state-error-retention": ("core-only", "core-plus-typescript", "core-plus-typescript-plus-react"),
}


def validate_protocol_canary(documents: list[dict[str, object]]) -> dict[str, object]:
    expected = {f"{scenario}--{arm}--r01": (scenario, arm) for scenario, arms in CANARY_ARMS.items() for arm in arms}
    if len(documents) != 11 or {d.get("run_id") for d in documents} != set(expected):
        raise ValueError("protocol canary requires exactly the eleven fixed slots")
    failed = []
    for document in documents:
        run_id = str(document["run_id"])
        if (document.get("scenario_id"), document.get("arm_id")) != expected[run_id] or document.get("repetition") != 1:
            raise ValueError("protocol canary identity mismatch")
        if (document.get("terminal_state") not in {"passed", "automatic_failure"}
                or document.get("inspection_diagnostics") != []
                or document.get("oracle_skipped_reason") != "not_applicable"
                or not document.get("oracle_results")
                or set(document.get("automatic_failure_reasons", [])) & {"invalid_claim", "skill_not_used", "candidate_incomplete"}):
            failed.append(run_id)
    return {"schema_version": "profile-protocol-canary/v1", "status": "failed" if failed else "passed", "expected_slots": 11, "completed_slots": len(documents), "failed_run_ids": sorted(failed), "behavior_scores_used": False}
