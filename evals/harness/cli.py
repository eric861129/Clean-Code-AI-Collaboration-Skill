from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import subprocess
from pathlib import Path
from typing import Any

from evals.harness.anonymizer import RUBRIC_IDS, write_review_packet
from evals.harness.diff_boundary import capture_diff
from evals.harness.evidence_recorder import record_subject_evidence
from evals.harness.fixture_builder import build_workspace
from evals.harness.manifest import load_manifest
from evals.harness.models import (
    BenchmarkManifest,
    CommandResult,
    HarnessPaths,
    RunSlot,
)
from evals.harness.oracle_runner import run_oracles
from evals.harness.planner import build_run_slots, full_slots, pilot_slots
from evals.harness.process import run_process
from evals.harness.result_builder import build_public_result, can_retry
from evals.harness.subject_runner import build_prompt, run_subject

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "evals" / "manifests" / "v0.3.0-cross-language.json"
RUNS_ROOT = ROOT / ".benchmark-runs"
FIXTURE_CLONE = RUNS_ROOT / "sources" / "fixtures"
RUN_DOCUMENTS = RUNS_ROOT / "run-documents"
PREFLIGHT_ROOT = RUNS_ROOT / "preflights"
FREEZE_ROOT = RUNS_ROOT / "contract-freezes"
CAMPAIGN_STATE_PATH = RUNS_ROOT / "campaign-state.json"
INVALIDATIONS_ROOT = RUNS_ROOT / "invalidations"
TIMEOUT_ADJUDICATIONS_ROOT = RUNS_ROOT / "timeout-adjudications"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    manifest = load_manifest(MANIFEST_PATH)
    paths = HarnessPaths(
        repository_root=ROOT,
        runs_root=RUNS_ROOT,
        fixture_clone=FIXTURE_CLONE,
        skill_repository=ROOT,
    )
    command = args.command
    if command == "prepare":
        _prepare(manifest, paths)
    elif command == "pilot":
        _require_preflight(manifest, paths)
        _run_slots(manifest, paths, pilot_slots(build_run_slots(manifest)))
    elif command == "freeze":
        _write_freeze(manifest, paths, args.decision_note)
    elif command == "invalidate-pilot":
        _invalidate_pilot(manifest, paths, args.scenario, args.reason)
    elif command == "adjudicate-timeout":
        _adjudicate_timeout(
            manifest,
            paths,
            args.run_id,
            args.source,
            args.reason,
        )
    elif command == "full":
        _verify_freeze(manifest, paths)
        _run_slots(manifest, paths, full_slots(build_run_slots(manifest)))
    elif command == "review-packets":
        _write_review_packets(manifest, paths, args.phase)
    elif command == "build-result":
        _write_result(manifest, paths, Path(args.output))
    elif command == "verify":
        _verify_runs(manifest, paths, args.phase)
    elif command == "verify-freeze":
        _verify_freeze(manifest, paths)
    elif command == "verify-reviews":
        _verify_reviews(manifest)
    else:  # pragma: no cover - argparse prevents this branch
        parser.error(f"unknown command: {command}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-language Benchmark Harness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare")
    subparsers.add_parser("pilot")
    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--decision-note", required=True)
    invalidation = subparsers.add_parser("invalidate-pilot")
    invalidation.add_argument("--scenario", required=True)
    invalidation.add_argument("--reason", required=True)
    adjudication = subparsers.add_parser("adjudicate-timeout")
    adjudication.add_argument("--run-id", required=True)
    adjudication.add_argument(
        "--source",
        choices=("candidate", "infrastructure"),
        required=True,
    )
    adjudication.add_argument("--reason", required=True)
    subparsers.add_parser("full")

    packets = subparsers.add_parser("review-packets")
    packets.add_argument("--phase", choices=("pilot", "all"), default="all")

    result = subparsers.add_parser("build-result")
    result.add_argument(
        "--output",
        default=str(ROOT / "evals" / "results" / "v0.3.0-cross-language.json"),
    )

    verify = subparsers.add_parser("verify")
    verify.add_argument("--phase", choices=("pilot", "all"), default="all")
    subparsers.add_parser("verify-freeze")
    subparsers.add_parser("verify-reviews")
    return parser


def _prepare(manifest: BenchmarkManifest, paths: HarnessPaths) -> None:
    _ensure_fixture_clone(manifest, paths)
    _verify_skill_revision(manifest, paths)
    contract = _freeze_document(manifest, paths)
    contract_sha256 = _canonical_sha256(contract)
    preflight_path = _preflight_path(contract_sha256)
    if preflight_path.exists():
        preflight = _read_json(preflight_path)
        if preflight.get("status") != "passed":
            raise RuntimeError("existing preflight is not passed")
        if preflight.get("contract_sha256") != contract_sha256:
            raise RuntimeError("existing preflight belongs to another contract")
        print(_console_json(preflight))
        return

    results: list[dict[str, object]] = []
    for scenario in manifest.scenarios:
        scenario_id = str(scenario["id"])
        slot = RunSlot(
            run_id=f"preflight--{scenario_id}--{contract_sha256[:12]}",
            scenario_id=scenario_id,
            language=str(scenario["language"]),
            arm_id="control",
            repetition=0,
            order_index=len(results),
        )
        workspace = build_workspace(slot, manifest, paths)
        evidence = run_oracles(
            workspace,
            scenario,
            paths.fixture_clone / str(scenario["evaluator_path"]),
            manifest.oracle_timeout_seconds,
            expect_acceptance_red=True,
        )
        oracle_evidence = _save_oracle_evidence(
            evidence,
            workspace.artifact_dir,
        )
        results.append(
            {
                "scenario_id": scenario_id,
                "status": (
                    "passed" if not evidence.automatic_failure_reasons else "failed"
                ),
                "automatic_failure_reasons": list(
                    evidence.automatic_failure_reasons
                ),
                "oracle_results": _serialize_oracles(evidence, workspace.root),
                "oracle_evidence": str(
                    oracle_evidence.relative_to(paths.runs_root)
                ).replace("\\", "/"),
            }
        )
    status = (
        "passed"
        if all(item["status"] == "passed" for item in results)
        else "failed"
    )
    document = {
        "schema_version": "1.0",
        "status": status,
        "fixture_commit": manifest.fixture_commit,
        "skill_commit": manifest.skill_commit,
        "model": manifest.model,
        "reasoning_effort": manifest.reasoning_effort,
        "contract_sha256": contract_sha256,
        "contract": contract,
        "codex_version": _codex_version(),
        "pilot_run_ids": [
            slot.run_id for slot in pilot_slots(build_run_slots(manifest))
        ],
        "scenarios": results,
    }
    _write_json(preflight_path, document)
    print(_console_json(document))
    if status != "passed":
        raise RuntimeError("preflight failed")


def _run_slots(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    slots: tuple[RunSlot, ...],
) -> None:
    _ensure_fixture_clone(manifest, paths)
    _verify_skill_revision(manifest, paths)
    contract_sha256 = _canonical_sha256(_freeze_document(manifest, paths))
    for index, slot in enumerate(slots, start=1):
        if contract_sha256 != _canonical_sha256(_freeze_document(manifest, paths)):
            raise RuntimeError("benchmark contract changed during execution")
        generation = _active_generation(slot.scenario_id)
        scenario_contract_sha256 = _scenario_contract_sha256(
            manifest,
            paths,
            slot.scenario_id,
        )
        _require_generation_contract_change(
            slot.scenario_id,
            scenario_contract_sha256,
        )
        document_path = _run_document_path(slot, generation)
        if document_path.is_file():
            document = _read_json(document_path)
            _validate_terminal_document(
                slot,
                document,
                scenario_contract_sha256,
            )
            print(f"[{index}/{len(slots)}] skip completed {slot.run_id}")
            continue
        print(f"[{index}/{len(slots)}] run {slot.run_id}", flush=True)
        document = _execute_slot(
            manifest,
            paths,
            slot,
            contract_sha256,
            scenario_contract_sha256,
            generation,
        )
        _write_json(document_path, document)
        print(
            f"[{index}/{len(slots)}] {slot.run_id}: "
            f"{document['terminal_state']}",
            flush=True,
        )


def _execute_slot(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    logical_slot: RunSlot,
    contract_sha256: str,
    scenario_contract_sha256: str,
    generation: int,
) -> dict[str, object]:
    attempts: list[dict[str, object]] = []
    last_reason = ""
    for attempt in (1, 2):
        physical_slot = RunSlot(
            run_id=_physical_run_id(
                logical_slot.run_id,
                generation,
                scenario_contract_sha256,
                attempt,
            ),
            scenario_id=logical_slot.scenario_id,
            language=logical_slot.language,
            arm_id=logical_slot.arm_id,
            repetition=logical_slot.repetition,
            order_index=logical_slot.order_index,
        )
        try:
            workspace = build_workspace(physical_slot, manifest, paths)
            observation = run_subject(
                physical_slot,
                manifest,
                workspace,
                attempt=attempt,
            )
            subject_evidence = record_subject_evidence(observation, workspace)
            diff = capture_diff(workspace, _scenario_for(manifest, logical_slot))
            attempt_document: dict[str, object] = {
                "attempt": attempt,
                "physical_run_id": physical_slot.run_id,
                "artifact_directory": str(
                    workspace.artifact_dir.relative_to(paths.runs_root)
                ).replace("\\", "/"),
                "subject_evidence": subject_evidence.name,
                "subject": _serialize_command(
                    observation.command,
                    workspace.root,
                ),
            }
            attempts.append(attempt_document)

            if observation.command.timed_out:
                return _run_document(
                    manifest,
                    logical_slot,
                    contract_sha256,
                    scenario_contract_sha256,
                    generation,
                    diff,
                    attempts,
                    terminal_state="timeout",
                    reasons=["timeout"],
                    oracle_results=[],
                    telemetry=_read_subject_telemetry(subject_evidence),
                )
            if observation.command.exit_code != 0:
                last_reason = "cli_runner_error"
                if can_retry(last_reason, attempt):
                    continue
                return _run_document(
                    manifest,
                    logical_slot,
                    contract_sha256,
                    scenario_contract_sha256,
                    generation,
                    diff,
                    attempts,
                    terminal_state="infrastructure_failure",
                    reasons=[last_reason],
                    oracle_results=[],
                    telemetry=_read_subject_telemetry(subject_evidence),
                )

            scenario = _scenario_for(manifest, logical_slot)
            oracle = run_oracles(
                workspace,
                scenario,
                paths.fixture_clone / str(scenario["evaluator_path"]),
                manifest.oracle_timeout_seconds,
            )
            oracle_evidence = _save_oracle_evidence(
                oracle,
                workspace.artifact_dir,
            )
            attempt_document["oracle_evidence"] = str(
                oracle_evidence.relative_to(workspace.artifact_dir)
            ).replace("\\", "/")
            reasons = list(oracle.automatic_failure_reasons)
            if diff.outside_boundary:
                reasons.append("outside_boundary")
            return _run_document(
                manifest,
                logical_slot,
                contract_sha256,
                scenario_contract_sha256,
                generation,
                diff,
                attempts,
                terminal_state=(
                    "infrastructure_failure"
                    if "oracle_timeout_unclassified" in reasons
                    else "automatic_failure"
                    if reasons
                    else "passed"
                ),
                reasons=reasons,
                oracle_results=_serialize_oracles(oracle, workspace.root),
                telemetry=_read_subject_telemetry(subject_evidence),
            )
        except FileExistsError:
            raise
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            last_reason = "harness_error"
            attempts.append(
                {
                    "attempt": attempt,
                    "physical_run_id": physical_slot.run_id,
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
            if can_retry(last_reason, attempt):
                continue
            return _infrastructure_document(
                manifest,
                logical_slot,
                contract_sha256,
                scenario_contract_sha256,
                generation,
                attempts,
                last_reason,
            )
    return _infrastructure_document(
        manifest,
        logical_slot,
        contract_sha256,
        scenario_contract_sha256,
        generation,
        attempts,
        last_reason or "harness_error",
    )


def _run_document(
    manifest: BenchmarkManifest,
    slot: RunSlot,
    contract_sha256: str,
    scenario_contract_sha256: str,
    generation: int,
    diff: Any,
    attempts: list[dict[str, object]],
    terminal_state: str,
    reasons: list[str],
    oracle_results: list[dict[str, object]],
    telemetry: object,
) -> dict[str, object]:
    scenario = _scenario_for(manifest, slot)
    return {
        "schema_version": "1.0",
        "run_id": slot.run_id,
        "scenario_id": slot.scenario_id,
        "language": slot.language,
        "arm_id": slot.arm_id,
        "repetition": slot.repetition,
        "order_index": slot.order_index,
        "contract_sha256": contract_sha256,
        "scenario_contract_sha256": scenario_contract_sha256,
        "generation": generation,
        "evidence_id": f"{slot.run_id}--g{generation:02d}",
        "prompt_sha256": _sha256_text(build_prompt(scenario, slot.arm_id)),
        "task": scenario["task"],
        "must_preserve": scenario["must_preserve"],
        "prohibited_changes": scenario["prohibited_changes"],
        "terminal_state": terminal_state,
        "automatic_failure_reasons": reasons,
        "diff": diff.diff,
        "diff_sha256": diff.diff_sha256,
        "changed_paths": list(diff.changed_paths),
        "renamed_paths": [
            {"source": item.source, "destination": item.destination}
            for item in diff.renamed_paths
        ],
        "outside_boundary": list(diff.outside_boundary),
        "oracle_results": oracle_results,
        "telemetry": telemetry,
        "blind_spots": [
            "小型 Fixture 不能代表所有真實 Repository。",
            "固定單一模型與 Client，不能推論其他模型會得到相同結果。",
        ],
        "attempts": attempts,
    }


def _infrastructure_document(
    manifest: BenchmarkManifest,
    slot: RunSlot,
    contract_sha256: str,
    scenario_contract_sha256: str,
    generation: int,
    attempts: list[dict[str, object]],
    reason: str,
) -> dict[str, object]:
    scenario = _scenario_for(manifest, slot)
    return {
        "schema_version": "1.0",
        "run_id": slot.run_id,
        "scenario_id": slot.scenario_id,
        "language": slot.language,
        "arm_id": slot.arm_id,
        "repetition": slot.repetition,
        "order_index": slot.order_index,
        "contract_sha256": contract_sha256,
        "scenario_contract_sha256": scenario_contract_sha256,
        "generation": generation,
        "evidence_id": f"{slot.run_id}--g{generation:02d}",
        "prompt_sha256": _sha256_text(build_prompt(scenario, slot.arm_id)),
        "task": scenario["task"],
        "must_preserve": scenario["must_preserve"],
        "prohibited_changes": scenario["prohibited_changes"],
        "terminal_state": "infrastructure_failure",
        "automatic_failure_reasons": [reason],
        "diff": "",
        "diff_sha256": hashlib.sha256(b"").hexdigest(),
        "changed_paths": [],
        "renamed_paths": [],
        "outside_boundary": [],
        "oracle_results": [],
        "telemetry": "not_available",
        "blind_spots": ["Subject 未完成，因此無法評估候選實作。"],
        "attempts": attempts,
    }


def _write_review_packets(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    phase: str,
) -> None:
    slots = _phase_slots(manifest, phase)
    randomized_slots = list(slots)
    secrets.SystemRandom().shuffle(randomized_slots)
    for slot in randomized_slots:
        document = _read_run_document(slot)
        _validate_terminal_document(
            slot,
            document,
            _scenario_contract_sha256(manifest, paths, slot.scenario_id),
        )
        packet = write_review_packet(document, RUNS_ROOT)
        if not packet.is_file():  # pragma: no cover - writer guarantees this
            raise FileNotFoundError("review packet was not written")
    print(f"review packets: {len(slots)}")


def _verify_runs(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    phase: str,
) -> None:
    slots = _phase_slots(manifest, phase)
    states: dict[str, int] = {}
    for slot in slots:
        document = _read_run_document(slot)
        _validate_terminal_document(
            slot,
            document,
            _scenario_contract_sha256(manifest, paths, slot.scenario_id),
        )
        if "oracle_timeout_unclassified" in document.get(
            "automatic_failure_reasons", []
        ):
            raise ValueError(f"oracle timeout needs adjudication: {slot.run_id}")
        state = str(document["terminal_state"])
        states[state] = states.get(state, 0) + 1
    print(json.dumps({"count": len(slots), "states": states}, indent=2))


def _write_result(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    output: Path,
) -> None:
    _verify_runs(manifest, paths, "all")
    _verify_reviews(manifest)
    slots = build_run_slots(manifest)
    documents = [_read_run_document(slot) for slot in slots]
    reviews = _reviews_by_run(manifest)
    for document in documents:
        document["review"] = reviews[str(document["run_id"])]
    result = build_public_result(slots, documents)
    _write_json(output, result)
    print(output)


def _verify_reviews(manifest: BenchmarkManifest) -> None:
    slots = build_run_slots(manifest)
    reviews = _reviews_by_run(manifest)
    expected = {slot.run_id for slot in slots}
    if set(reviews) != expected:
        missing = sorted(expected - set(reviews))
        extra = sorted(set(reviews) - expected)
        raise ValueError(f"reviews mismatch; missing={missing}, extra={extra}")
    for run_id, review in reviews.items():
        rubrics = review.get("rubrics")
        if not isinstance(rubrics, dict) or set(rubrics) != set(RUBRIC_IDS):
            raise ValueError(f"invalid rubrics for {run_id}")
        for rubric_id, value in rubrics.items():
            if not isinstance(value, dict):
                raise ValueError(f"invalid rubric {rubric_id} for {run_id}")
            if value.get("score") not in {0, 1, 2}:
                raise ValueError(f"invalid score for {run_id}/{rubric_id}")
            reason = value.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"empty reason for {run_id}/{rubric_id}")
        if any("aggregate" in key or "total" in key for key in review):
            raise ValueError(f"aggregate score is not allowed for {run_id}")
    print(f"reviews verified: {len(reviews)}")


def _reviews_by_run(
    manifest: BenchmarkManifest,
) -> dict[str, dict[str, object]]:
    current_evidence = {
        str(document["evidence_id"]): slot.run_id
        for slot in build_run_slots(manifest)
        for document in [_read_run_document(slot)]
    }
    mapping = _read_json(RUNS_ROOT / "review-key.json")
    candidates = mapping.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("invalid private review mapping")
    reviews_root = RUNS_ROOT / "reviews"
    reviews: dict[str, dict[str, object]] = {}
    for candidate_id, identity in candidates.items():
        if not isinstance(identity, dict):
            raise ValueError("invalid private review identity")
        evidence_id = str(
            identity.get("evidence_id", identity.get("run_id", ""))
        )
        if evidence_id not in current_evidence:
            continue
        path = reviews_root / f"{candidate_id}.json"
        if not path.is_file():
            continue
        run_id = current_evidence[evidence_id]
        reviews[run_id] = _read_json(path)
    return reviews


def _invalidate_pilot(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    scenario_id: str,
    reason: str,
) -> None:
    if not reason.strip():
        raise ValueError("invalidation reason must not be empty")
    scenario_ids = {str(item["id"]) for item in manifest.scenarios}
    if scenario_id not in scenario_ids:
        raise ValueError(f"unknown scenario: {scenario_id}")
    contract = _freeze_document(manifest, paths)
    contract_sha256 = _canonical_sha256(contract)
    if _freeze_path(contract_sha256).exists():
        raise RuntimeError("cannot invalidate a frozen contract")
    scenario_contract_sha256 = _scenario_contract_sha256(
        manifest,
        paths,
        scenario_id,
    )
    generation = _active_generation(scenario_id)
    slots = tuple(
        slot
        for slot in pilot_slots(build_run_slots(manifest))
        if slot.scenario_id == scenario_id
    )
    evidence: list[dict[str, object]] = []
    for slot in slots:
        path = _run_document_path(slot, generation)
        if not path.is_file():
            continue
        document = _read_run_document(slot)
        _validate_terminal_document(slot, document, scenario_contract_sha256)
        evidence.append(
            {
                "run_id": slot.run_id,
                "generation": generation,
                "path": str(path.relative_to(RUNS_ROOT)).replace("\\", "/"),
                "sha256": _file_sha256(path),
            }
        )
    if not evidence:
        raise FileNotFoundError(
            f"scenario has no completed pilot evidence: {scenario_id}"
        )
    invalidation = {
        "schema_version": "1.0",
        "scenario_id": scenario_id,
        "generation": generation,
        "partial_generation": len(evidence) != len(slots),
        "contract_sha256": contract_sha256,
        "scenario_contract_sha256": scenario_contract_sha256,
        "reason": reason.strip(),
        "runs": evidence,
    }
    invalidation_path = (
        INVALIDATIONS_ROOT
        / f"{scenario_id}--g{generation:02d}--{secrets.token_hex(4)}.json"
    )
    _write_json(invalidation_path, invalidation)

    state = _campaign_state()
    scenarios = state.setdefault("scenarios", {})
    if not isinstance(scenarios, dict):
        raise ValueError("invalid campaign state")
    scenarios[scenario_id] = {
        "generation": generation + 1,
        "must_change_from": scenario_contract_sha256,
        "invalidation": str(invalidation_path.relative_to(RUNS_ROOT)).replace(
            "\\", "/"
        ),
    }
    _replace_json(CAMPAIGN_STATE_PATH, state)
    print(f"invalidated {scenario_id} generation {generation}")


def _adjudicate_timeout(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    run_id: str,
    source: str,
    reason: str,
) -> None:
    if not reason.strip():
        raise ValueError("timeout adjudication reason must not be empty")
    try:
        slot = next(
            item for item in build_run_slots(manifest) if item.run_id == run_id
        )
    except StopIteration as error:
        raise ValueError(f"unknown run ID: {run_id}") from error
    generation = _active_generation(slot.scenario_id)
    path = _run_document_path(slot, generation)
    document = _read_json(path)
    _validate_terminal_document(
        slot,
        document,
        _scenario_contract_sha256(manifest, paths, slot.scenario_id),
    )
    reasons = document.get("automatic_failure_reasons", [])
    if "oracle_timeout_unclassified" not in reasons:
        raise ValueError("run does not contain an unclassified oracle timeout")
    evidence_id = str(document["evidence_id"])
    adjudication = {
        "schema_version": "1.0",
        "evidence_id": evidence_id,
        "run_id": run_id,
        "source": source,
        "reason": reason.strip(),
        "run_document_sha256": _file_sha256(path),
    }
    adjudication_path = TIMEOUT_ADJUDICATIONS_ROOT / f"{evidence_id}.json"
    _write_json(adjudication_path, adjudication)
    print(f"timeout adjudicated: {run_id} -> {source}")


def _apply_timeout_adjudication(
    document: dict[str, object],
) -> dict[str, object]:
    reasons = document.get("automatic_failure_reasons", [])
    if "oracle_timeout_unclassified" not in reasons:
        return document
    evidence_id = str(document.get("evidence_id", ""))
    path = TIMEOUT_ADJUDICATIONS_ROOT / f"{evidence_id}.json"
    if not path.is_file():
        return document
    adjudication = _read_json(path)
    source = adjudication.get("source")
    if source not in {"candidate", "infrastructure"}:
        raise ValueError(f"invalid timeout adjudication: {evidence_id}")
    updated = dict(document)
    updated["automatic_failure_reasons"] = [
        (
            "candidate_oracle_timeout"
            if source == "candidate"
            else "infrastructure_oracle_timeout"
        )
        if item == "oracle_timeout_unclassified"
        else item
        for item in reasons
    ]
    updated["terminal_state"] = (
        "automatic_failure" if source == "candidate" else "infrastructure_failure"
    )
    updated["timeout_adjudication"] = adjudication
    return updated


def _write_freeze(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    decision_note: str,
) -> None:
    if not decision_note.strip():
        raise ValueError("freeze decision note must not be empty")
    _require_preflight(manifest, paths)
    _verify_runs(manifest, paths, "pilot")
    contract = _freeze_document(manifest, paths)
    freeze = {
        "schema_version": "1.0",
        "contract_sha256": _canonical_sha256(contract),
        "contract": contract,
        "decision_note": decision_note.strip(),
    }
    freeze_path = _freeze_path(str(freeze["contract_sha256"]))
    if freeze_path.is_file():
        existing = _read_json(freeze_path)
        if existing != freeze:
            raise ValueError("contract freeze differs from existing freeze")
        return
    _write_json(freeze_path, freeze)
    print(f"contract freeze: {freeze_path}")


def _verify_freeze(manifest: BenchmarkManifest, paths: HarnessPaths) -> None:
    actual = _freeze_document(manifest, paths)
    contract_sha256 = _canonical_sha256(actual)
    freeze_path = _freeze_path(contract_sha256)
    if not freeze_path.is_file():
        raise FileNotFoundError("contract freeze is missing")
    freeze = _read_json(freeze_path)
    if (
        freeze.get("contract") != actual
        or freeze.get("contract_sha256") != _canonical_sha256(actual)
    ):
        raise ValueError("contract freeze verification failed")
    print("contract freeze verified")


def _freeze_document(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
) -> dict[str, object]:
    prompts: dict[str, str] = {}
    evaluators: dict[str, str] = {}
    for scenario in manifest.scenarios:
        scenario_id = str(scenario["id"])
        for arm in manifest.arms:
            arm_id = str(arm["id"])
            prompt = build_prompt(scenario, arm_id)
            prompts[f"{scenario_id}/{arm_id}"] = _sha256_text(prompt)
        evaluators[scenario_id] = _tree_sha256(
            paths.fixture_clone / str(scenario["evaluator_path"])
        )
    return {
        "schema_version": "1.0",
        "manifest_sha256": _file_sha256(MANIFEST_PATH),
        "harness_sha256": _source_tree_sha256(ROOT / "evals" / "harness"),
        "codex_version": _codex_version(),
        "fixture_commit": manifest.fixture_commit,
        "skill_commit": manifest.skill_commit,
        "prompts": prompts,
        "evaluators": evaluators,
        "rubrics": {
            str(path.relative_to(ROOT)).replace("\\", "/"): _file_sha256(path)
            for path in sorted((ROOT / "evals" / "rubrics").glob("*.md"))
        },
    }


def _scenario_contract_sha256(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    scenario_id: str,
) -> str:
    contract = _freeze_document(manifest, paths)
    scenario = next(
        item for item in manifest.scenarios if item["id"] == scenario_id
    )
    prompts = contract["prompts"]
    evaluators = contract["evaluators"]
    if not isinstance(prompts, dict) or not isinstance(evaluators, dict):
        raise ValueError("invalid contract prompt or evaluator mapping")
    scenario_contract = {
        "schema_version": "1.0",
        "harness_sha256": contract["harness_sha256"],
        "codex_version": contract["codex_version"],
        "fixture_commit": manifest.fixture_commit,
        "skill_commit": manifest.skill_commit,
        "model": manifest.model,
        "reasoning_effort": manifest.reasoning_effort,
        "client": manifest.client,
        "subject_timeout_seconds": manifest.subject_timeout_seconds,
        "oracle_timeout_seconds": manifest.oracle_timeout_seconds,
        "repetitions": manifest.repetitions,
        "random_seed": manifest.random_seed,
        "scenario": scenario,
        "prompts": {
            key: value
            for key, value in prompts.items()
            if str(key).startswith(f"{scenario_id}/")
        },
        "evaluator_sha256": evaluators[scenario_id],
        "rubrics": contract["rubrics"],
    }
    return _canonical_sha256(scenario_contract)


def _ensure_fixture_clone(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
) -> None:
    if not paths.fixture_clone.exists():
        paths.fixture_clone.parent.mkdir(parents=True, exist_ok=True)
        _run_checked(
            [
                "git",
                "clone",
                "--no-checkout",
                manifest.fixture_url,
                str(paths.fixture_clone),
            ],
            ROOT,
            manifest.fixture_timeout_seconds,
        )
    resolved = _run_checked(
        ["git", "rev-parse", f"{manifest.fixture_tag}^{{}}"],
        paths.fixture_clone,
        manifest.fixture_timeout_seconds,
    ).stdout.strip()
    if resolved != manifest.fixture_commit:
        raise ValueError("fixture tag does not resolve to pinned commit")
    _run_checked(
        ["git", "checkout", "--detach", manifest.fixture_commit],
        paths.fixture_clone,
        manifest.fixture_timeout_seconds,
    )


def _verify_skill_revision(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
) -> None:
    resolved = _run_checked(
        ["git", "rev-parse", f"{manifest.skill_tag}^{{}}"],
        paths.skill_repository,
        manifest.fixture_timeout_seconds,
    ).stdout.strip()
    if resolved != manifest.skill_commit:
        raise ValueError("skill tag does not resolve to pinned commit")


def _serialize_oracles(
    evidence: Any,
    workspace_root: Path,
) -> list[dict[str, object]]:
    groups = (
        ("public", evidence.public),
        ("preservation", evidence.preservation),
        ("acceptance", evidence.acceptance),
    )
    return [
        {
            "group": group,
            "commands": [
                _serialize_command(
                    command,
                    workspace_root,
                    include_output=True,
                )
                for command in commands
            ],
        }
        for group, commands in groups
    ]


def _serialize_command(
    command: CommandResult,
    workspace_root: Path,
    include_output: bool = False,
) -> dict[str, object]:
    document: dict[str, object] = {
        "args": [
            _sanitize_persisted_text(argument, workspace_root)
            for argument in command.args
        ],
        "exit_code": command.exit_code,
        "elapsed_seconds": command.elapsed_seconds,
        "timed_out": command.timed_out,
        "classification": command.classification,
        "attempt": command.attempt,
        "stdout_sha256": _sha256_text(command.stdout),
        "stderr_sha256": _sha256_text(command.stderr),
    }
    if include_output:
        document["stdout"] = _sanitize_persisted_text(
            command.stdout,
            workspace_root,
        )
        document["stderr"] = _sanitize_persisted_text(
            command.stderr,
            workspace_root,
        )
    return document


def _save_oracle_evidence(evidence: Any, artifact_dir: Path) -> Path:
    root = artifact_dir / "oracle-evidence"
    if root.exists():
        raise FileExistsError(f"refusing to overwrite oracle evidence: {root}")
    root.mkdir(parents=True)
    index: dict[str, object] = {"schema_version": "1.0", "groups": []}
    groups = (
        ("public", evidence.public),
        ("preservation", evidence.preservation),
        ("acceptance", evidence.acceptance),
    )
    serialized_groups: list[dict[str, object]] = []
    for group, commands in groups:
        command_entries: list[dict[str, object]] = []
        for position, command in enumerate(commands, start=1):
            stdout_name = f"{group}-{position:02d}.stdout.txt"
            stderr_name = f"{group}-{position:02d}.stderr.txt"
            (root / stdout_name).write_text(command.stdout, encoding="utf-8")
            (root / stderr_name).write_text(command.stderr, encoding="utf-8")
            command_entries.append(
                {
                    "position": position,
                    "stdout": stdout_name,
                    "stdout_sha256": _sha256_text(command.stdout),
                    "stderr": stderr_name,
                    "stderr_sha256": _sha256_text(command.stderr),
                    "exit_code": command.exit_code,
                    "timed_out": command.timed_out,
                }
            )
        serialized_groups.append({"group": group, "commands": command_entries})
    index["groups"] = serialized_groups
    index_path = root / "index.json"
    _write_json(index_path, index)
    return index_path


def _sanitize_persisted_text(value: str, workspace_root: Path) -> str:
    redacted = value
    replacements = (
        (workspace_root, "{workspace}"),
        (RUNS_ROOT, "{runs_root}"),
        (ROOT, "{repository_root}"),
    )
    for path, placeholder in replacements:
        variants = {str(path), str(path).replace("\\", "/")}
        for variant in sorted(variants, key=len, reverse=True):
            redacted = re.sub(
                re.escape(variant),
                placeholder,
                redacted,
                flags=re.IGNORECASE,
            )
    return redacted


def _read_subject_telemetry(path: Path) -> object:
    document = _read_json(path)
    return document.get("telemetry", "not_available")


def _phase_slots(
    manifest: BenchmarkManifest,
    phase: str,
) -> tuple[RunSlot, ...]:
    slots = build_run_slots(manifest)
    return pilot_slots(slots) if phase == "pilot" else slots


def _read_run_document(slot: RunSlot) -> dict[str, object]:
    generation = _active_generation(slot.scenario_id)
    path = _run_document_path(slot, generation)
    if not path.is_file():
        raise FileNotFoundError(f"missing run document: {slot.run_id}")
    document = _read_json(path)
    return _apply_timeout_adjudication(document)


def _run_document_path(slot: RunSlot, generation: int) -> Path:
    return (
        RUN_DOCUMENTS
        / slot.scenario_id
        / f"{slot.run_id}--g{generation:02d}.json"
    )


def _physical_run_id(
    logical_run_id: str,
    generation: int,
    scenario_contract_sha256: str,
    attempt: int,
) -> str:
    identity = (
        f"{logical_run_id}|{generation}|{scenario_contract_sha256}|{attempt}"
    )
    return f"run-{_sha256_text(identity)[:16]}"


def _active_generation(scenario_id: str) -> int:
    state = _campaign_state()
    scenarios = state.get("scenarios", {})
    if not isinstance(scenarios, dict):
        raise ValueError("invalid campaign state")
    scenario = scenarios.get(scenario_id, {})
    if not isinstance(scenario, dict):
        raise ValueError("invalid campaign scenario state")
    generation = scenario.get("generation", 1)
    if not isinstance(generation, int) or generation <= 0:
        raise ValueError("invalid campaign generation")
    return generation


def _campaign_state() -> dict[str, object]:
    if not CAMPAIGN_STATE_PATH.is_file():
        return {"schema_version": "1.0", "scenarios": {}}
    return _read_json(CAMPAIGN_STATE_PATH)


def _require_generation_contract_change(
    scenario_id: str,
    scenario_contract_sha256: str,
) -> None:
    state = _campaign_state()
    scenarios = state.get("scenarios", {})
    if not isinstance(scenarios, dict):
        raise ValueError("invalid campaign state")
    scenario = scenarios.get(scenario_id, {})
    if not isinstance(scenario, dict):
        raise ValueError("invalid campaign scenario state")
    if scenario.get("must_change_from") == scenario_contract_sha256:
        raise RuntimeError(
            f"scenario contract must change before rerun: {scenario_id}"
        )


def _validate_terminal_document(
    slot: RunSlot,
    document: dict[str, object],
    scenario_contract_sha256: str,
) -> None:
    if document.get("run_id") != slot.run_id:
        raise ValueError(f"run document ID mismatch: {slot.run_id}")
    if document.get("terminal_state") not in {
        "passed",
        "automatic_failure",
        "timeout",
        "infrastructure_failure",
    }:
        raise ValueError(f"run is not terminal: {slot.run_id}")
    if document.get("scenario_contract_sha256") != scenario_contract_sha256:
        raise ValueError(f"run belongs to another contract: {slot.run_id}")


def _require_preflight(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
) -> None:
    contract_sha256 = _canonical_sha256(_freeze_document(manifest, paths))
    preflight_path = _preflight_path(contract_sha256)
    if not preflight_path.is_file():
        raise FileNotFoundError("run prepare before pilot")
    preflight = _read_json(preflight_path)
    if preflight.get("status") != "passed":
        raise RuntimeError("preflight is not passed")
    if preflight.get("contract_sha256") != contract_sha256:
        raise RuntimeError("preflight belongs to another contract")


def _scenario_for(
    manifest: BenchmarkManifest,
    slot: RunSlot,
) -> dict[str, object]:
    return next(
        scenario
        for scenario in manifest.scenarios
        if scenario["id"] == slot.scenario_id
    )


def _preflight_path(contract_sha256: str) -> Path:
    return PREFLIGHT_ROOT / f"{contract_sha256}.json"


def _freeze_path(contract_sha256: str) -> Path:
    return FREEZE_ROOT / f"{contract_sha256}.json"


def _codex_version() -> str:
    result = run_process(["codex", "--version"], ROOT, timeout_seconds=30)
    return result.stdout.strip() if result.exit_code == 0 else "not_available"


def _run_checked(args: list[str], cwd: Path, timeout_seconds: int) -> CommandResult:
    result = run_process(args, cwd, timeout_seconds)
    if result.exit_code != 0:
        raise RuntimeError(f"command failed: {args}\n{result.stderr}")
    return result


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).replace("\\", "/").encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _source_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    for path in paths:
        digest.update(str(path.relative_to(root)).replace("\\", "/").encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_sha256(value: dict[str, object]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(payload)


def _console_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2)


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write_json(path: Path, value: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _replace_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.{secrets.token_hex(4)}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
