from __future__ import annotations

from evals.harness.anonymizer import RUBRIC_IDS
from evals.harness.manifest import PROFILE_COMPARISON_ARMS
from evals.harness.models import BenchmarkManifest

PROFILE_IDS = ("csharp", "python", "typescript", "react")
EVIDENCE_GAP_REASONS = {
    "candidate_incomplete",
    "invalid_claim",
    "skill_not_used",
    "environment_error",
    "harness_error",
    "dependency_cache_error",
    "cli_runner_error",
    "infrastructure_oracle_timeout",
    "oracle_timeout_unclassified",
}
INCOMPLETE_TERMINAL_STATES = {"timeout", "infrastructure_failure"}


def build_profile_outcomes(
    manifest: BenchmarkManifest,
    run_documents: list[dict[str, object]],
) -> list[dict[str, object]]:
    if manifest.repetitions != 1:
        raise ValueError("profile pilot outcomes require exactly one repetition")
    documents_by_id = {
        str(document.get("run_id", "")): document for document in run_documents
    }
    if len(documents_by_id) != len(run_documents):
        raise ValueError("profile outcomes require unique run documents")

    scenarios_by_profile: dict[str, list[dict[str, object]]] = {}
    for scenario in manifest.scenarios:
        profile_id = scenario.get("profile_under_test")
        if not isinstance(profile_id, str):
            raise ValueError("profile outcome scenario is missing a profile")
        scenarios_by_profile.setdefault(profile_id, []).append(scenario)
    if set(scenarios_by_profile) != set(PROFILE_IDS):
        raise ValueError("profile outcomes require the four pilot profiles")

    return [
        _build_profile_outcome(
            profile_id,
            scenarios_by_profile[profile_id],
            documents_by_id,
        )
        for profile_id in PROFILE_IDS
    ]


def _build_profile_outcome(
    profile_id: str,
    scenarios: list[dict[str, object]],
    documents_by_id: dict[str, dict[str, object]],
) -> dict[str, object]:
    if len(scenarios) != 2:
        raise ValueError(f"profile outcome requires two scenarios: {profile_id}")
    comparator_ids = {str(item["direct_comparator"]) for item in scenarios}
    treatment_ids = {str(item["treatment_arm"]) for item in scenarios}
    if len(comparator_ids) != 1 or len(treatment_ids) != 1:
        raise ValueError(f"profile comparison arms are inconsistent: {profile_id}")
    comparator_id = next(iter(comparator_ids))
    treatment_id = next(iter(treatment_ids))
    if (comparator_id, treatment_id) != PROFILE_COMPARISON_ARMS[profile_id]:
        raise ValueError(f"profile comparison arms are invalid: {profile_id}")

    scenario_ids: list[str] = []
    comparator_run_ids: list[str] = []
    treatment_run_ids: list[str] = []
    criteria_evidence: list[dict[str, object]] = []
    evidence_gaps: list[str] = []
    treatment_failures: list[str] = []

    for scenario in scenarios:
        scenario_id = str(scenario["id"])
        scenario_ids.append(scenario_id)
        comparator_run_id = f"{scenario_id}--{comparator_id}--r01"
        treatment_run_id = f"{scenario_id}--{treatment_id}--r01"
        comparator_run_ids.append(comparator_run_id)
        treatment_run_ids.append(treatment_run_id)
        comparator = documents_by_id.get(comparator_run_id)
        treatment = documents_by_id.get(treatment_run_id)
        if comparator is None or treatment is None:
            evidence_gaps.append(f"missing direct comparison run: {scenario_id}")

        expected_criteria = [str(item) for item in scenario["incremental_criteria"]]
        comparator_scores = _criterion_scores(comparator, expected_criteria)
        treatment_scores = _criterion_scores(treatment, expected_criteria)
        if comparator_scores is None or treatment_scores is None:
            evidence_gaps.append(f"incomplete blind review: {scenario_id}")

        for criterion in expected_criteria:
            comparator_score = (
                comparator_scores.get(criterion)
                if comparator_scores is not None
                else None
            )
            treatment_score = (
                treatment_scores.get(criterion)
                if treatment_scores is not None
                else None
            )
            criteria_evidence.append(
                {
                    "scenario_id": scenario_id,
                    "criterion": criterion,
                    "comparator_run_id": comparator_run_id,
                    "treatment_run_id": treatment_run_id,
                    "comparator_score": comparator_score,
                    "treatment_score": treatment_score,
                    "delta": (
                        treatment_score - comparator_score
                        if comparator_score is not None
                        and treatment_score is not None
                        else None
                    ),
                }
            )

        for label, document in (
            ("comparator", comparator),
            ("treatment", treatment),
        ):
            if document is None:
                continue
            state = str(document.get("terminal_state", ""))
            reasons = document.get("automatic_failure_reasons", [])
            if state in INCOMPLETE_TERMINAL_STATES:
                evidence_gaps.append(f"{label} execution incomplete: {scenario_id}")
            if isinstance(reasons, list) and any(
                str(reason) in EVIDENCE_GAP_REASONS for reason in reasons
            ):
                evidence_gaps.append(f"{label} evidence gap: {scenario_id}")

        if treatment is not None:
            treatment_reasons = treatment.get("automatic_failure_reasons", [])
            has_gate_reason = isinstance(treatment_reasons, list) and any(
                str(reason) not in EVIDENCE_GAP_REASONS
                for reason in treatment_reasons
            )
            if treatment.get("terminal_state") != "passed" or has_gate_reason:
                treatment_failures.append(f"treatment gate failed: {scenario_id}")

    deltas = [
        item["delta"]
        for item in criteria_evidence
        if isinstance(item["delta"], int)
    ]
    regressions = [delta for delta in deltas if delta < 0]
    if evidence_gaps:
        outcome = "inconclusive"
        decision_reasons = sorted(set(evidence_gaps))
    elif treatment_failures or regressions:
        outcome = "failed"
        decision_reasons = [*treatment_failures]
        if regressions:
            decision_reasons.append("treatment review score regressed")
    elif deltas and any(delta > 0 for delta in deltas):
        outcome = "passed"
        decision_reasons = ["treatment improved without a criteria regression"]
    else:
        outcome = "no_difference"
        decision_reasons = ["no attributable criteria improvement was observed"]

    return {
        "profile_id": profile_id,
        "stage": "pilot",
        "direct_comparator": comparator_id,
        "treatment_arm": treatment_id,
        "scenario_ids": scenario_ids,
        "comparator_run_ids": comparator_run_ids,
        "treatment_run_ids": treatment_run_ids,
        "outcome": outcome,
        "criteria_evidence": criteria_evidence,
        "decision_reasons": decision_reasons,
        "limitations": [
            "Single-repetition pilot under pinned model, client, fixtures, and prompts.",
            "Only the declared direct comparator and treatment arms inform maturity.",
        ],
    }


def _criterion_scores(
    document: dict[str, object] | None,
    expected_criteria: list[str],
) -> dict[str, int] | None:
    if document is None:
        return None
    review = document.get("review")
    if not isinstance(review, dict) or set(review) != {
        "rubrics",
        "incremental_criteria",
    }:
        return None
    rubrics = review.get("rubrics")
    if not isinstance(rubrics, dict) or set(rubrics) != set(RUBRIC_IDS):
        return None
    for value in rubrics.values():
        if not isinstance(value, dict) or set(value) != {"score", "reason"}:
            return None
        score = value.get("score")
        reason = value.get("reason")
        if (
            not isinstance(score, int)
            or isinstance(score, bool)
            or score not in {0, 1, 2}
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            return None
    raw_criteria = review.get("incremental_criteria")
    if not isinstance(raw_criteria, list) or len(raw_criteria) != len(
        expected_criteria
    ):
        return None
    scores: dict[str, int] = {}
    for index, item in enumerate(raw_criteria):
        if not isinstance(item, dict) or set(item) != {
            "criterion",
            "score",
            "reason",
        }:
            return None
        criterion = item.get("criterion")
        score = item.get("score")
        reason = item.get("reason")
        if (
            criterion != expected_criteria[index]
            or not isinstance(score, int)
            or isinstance(score, bool)
            or score not in {0, 1, 2}
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            return None
        scores[str(criterion)] = score
    if len(scores) != len(expected_criteria):
        return None
    return scores
