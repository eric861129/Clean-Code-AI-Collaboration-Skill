from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from evals.harness.anonymizer import RUBRIC_IDS, write_review_packet
from evals.harness.desktop_subject import (
    DesktopSubjectValidationError,
    build_desktop_observation,
    desktop_subject_instruction,
    load_desktop_dispatch,
    stage_desktop_subject,
    write_attempt_receipt,
)
from evals.harness.diff_boundary import capture_diff
from evals.harness.evidence_recorder import record_subject_evidence
from evals.harness.fixture_builder import build_workspace
from evals.harness.manifest import load_manifest
from evals.harness.models import (
    BenchmarkManifest,
    CommandResult,
    DiffEvidence,
    HarnessPaths,
    RunSlot,
    SubjectDispatch,
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
DISPATCH_ROOT = RUNS_ROOT / "desktop-dispatches"
ATTEMPT_RECEIPTS_ROOT = RUNS_ROOT / "desktop-attempt-receipts"


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
        _desktop_execution_requires_stage_collect(manifest, "pilot")
    elif command == "stage":
        _stage_desktop_slots(manifest, paths, args.phase, args.run_id)
    elif command == "collect":
        _collect_desktop_dispatch(
            manifest,
            paths,
            args.dispatch_id,
            args.outcome,
            args.reason,
            args.elapsed_seconds,
            args.subject_thread_id,
        )
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
        _desktop_execution_requires_stage_collect(manifest, "full")
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
    stage = subparsers.add_parser("stage")
    stage.add_argument("--phase", choices=("pilot", "full"), required=True)
    stage.add_argument("--run-id")
    collect = subparsers.add_parser("collect")
    collect.add_argument("--dispatch-id", required=True)
    collect.add_argument(
        "--outcome",
        choices=("completed", "timeout", "infrastructure_failure"),
        required=True,
    )
    collect.add_argument("--reason", default="desktop_subject_completed")
    collect.add_argument("--elapsed-seconds", type=float)
    collect.add_argument("--subject-thread-id")
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
        **_subject_client_contract(manifest),
        "pilot_run_ids": [
            slot.run_id for slot in pilot_slots(build_run_slots(manifest))
        ],
        "scenarios": results,
    }
    _write_json(preflight_path, document)
    print(_console_json(document))
    if status != "passed":
        raise RuntimeError("preflight failed")


def _desktop_execution_requires_stage_collect(
    manifest: BenchmarkManifest,
    phase: str,
) -> None:
    if manifest.client == "codex-desktop-collaboration":
        raise RuntimeError(
            "Desktop collaboration subjects require explicit "
            f"stage --phase {phase} and collect; {phase} cannot launch "
            "nested Codex CLI sessions."
        )
    raise RuntimeError("this benchmark only supports Desktop collaboration")


def _stage_desktop_slots(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    phase: str,
    run_id: str | None,
) -> None:
    if manifest.client != "codex-desktop-collaboration":
        raise RuntimeError("stage requires the Desktop collaboration executor")
    if phase == "pilot":
        _require_preflight(manifest, paths)
        slots = pilot_slots(build_run_slots(manifest))
    else:
        _verify_freeze(manifest, paths)
        slots = full_slots(build_run_slots(manifest))
    if run_id is not None:
        slots = tuple(slot for slot in slots if slot.run_id == run_id)
        if not slots:
            raise ValueError(f"run is not in {phase}: {run_id}")

    _ensure_fixture_clone(manifest, paths)
    _verify_skill_revision(manifest, paths)
    contract_sha256 = _canonical_sha256(_freeze_document(manifest, paths))
    staged: list[dict[str, object]] = []
    pending: list[str] = []
    skipped: list[str] = []
    for slot in slots:
        if contract_sha256 != _canonical_sha256(_freeze_document(manifest, paths)):
            raise RuntimeError("benchmark contract changed during Desktop staging")
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
        run_document = _run_document_path(slot, generation)
        if run_document.is_file():
            _validate_terminal_document(
                slot,
                _read_json(run_document),
                scenario_contract_sha256,
            )
            skipped.append(slot.run_id)
            continue
        attempt = _next_desktop_attempt(slot, generation)
        dispatch_id = _desktop_dispatch_id(slot, generation, attempt)
        dispatch_index = _dispatch_index_path(dispatch_id)
        if dispatch_index.is_file():
            if not _attempt_receipt_path(slot, generation, attempt).is_file():
                pending.append(dispatch_id)
                continue
            raise RuntimeError(
                "Desktop dispatch already has a receipt but was not finalized: "
                f"{dispatch_id}"
            )
        physical_slot = RunSlot(
            run_id=_physical_run_id(
                slot.run_id,
                generation,
                scenario_contract_sha256,
                attempt,
            ),
            scenario_id=slot.scenario_id,
            language=slot.language,
            arm_id=slot.arm_id,
            repetition=slot.repetition,
            order_index=slot.order_index,
        )
        workspace = build_workspace(physical_slot, manifest, paths)
        dispatch = stage_desktop_subject(
            slot,
            manifest,
            workspace,
            generation=generation,
            attempt=attempt,
            physical_run_id=physical_slot.run_id,
            contract_sha256=contract_sha256,
            scenario_contract_sha256=scenario_contract_sha256,
        )
        _write_dispatch_index(dispatch)
        staged.append(
            {
                "dispatch_id": dispatch.dispatch_id,
                "dispatch_path": str(
                    dispatch.dispatch_path.relative_to(paths.runs_root)
                ).replace("\\", "/"),
                "instruction": desktop_subject_instruction(dispatch),
            }
        )
    print(
        _console_json(
            {
                "phase": phase,
                "staged": staged,
                "pending": pending,
                "skipped_terminal": skipped,
            }
        )
    )


def _collect_desktop_dispatch(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    dispatch_id: str,
    outcome: str,
    reason: str,
    elapsed_seconds: float | None,
    subject_thread_id: str | None,
) -> None:
    if elapsed_seconds is not None and elapsed_seconds < 0:
        raise ValueError("desktop subject elapsed seconds cannot be negative")
    dispatch = _load_dispatch_by_id(dispatch_id)
    slot = _slot_for_run_id(manifest, dispatch.logical_run_id)
    generation = _active_generation(slot.scenario_id)
    scenario_contract_sha256 = _scenario_contract_sha256(
        manifest,
        paths,
        slot.scenario_id,
    )
    if dispatch.generation != generation:
        raise ValueError("desktop dispatch generation is no longer active")
    if dispatch.attempt not in {1, 2}:
        raise ValueError("desktop dispatch attempt is invalid")
    if dispatch.scenario_contract_sha256 != scenario_contract_sha256:
        raise ValueError("desktop dispatch belongs to another scenario contract")
    contract_sha256 = _canonical_sha256(_freeze_document(manifest, paths))
    if dispatch.contract_sha256 != contract_sha256:
        raise ValueError("desktop dispatch belongs to another benchmark contract")
    if _run_document_path(slot, generation).is_file():
        raise FileExistsError("terminal run document already exists")
    receipt_path = _attempt_receipt_path(slot, generation, dispatch.attempt)
    if receipt_path.is_file():
        raise FileExistsError("desktop dispatch already has an immutable receipt")

    effective_outcome = (
        "timeout"
        if elapsed_seconds is not None
        and elapsed_seconds > manifest.subject_timeout_seconds
        else outcome
    )
    effective_reason = reason.strip() or "desktop_subject_completed"
    if effective_outcome == "timeout":
        effective_reason = "timeout"
    candidate_failure_reason: str | None = None
    try:
        observation = build_desktop_observation(
            dispatch,
            outcome=effective_outcome,
            elapsed_seconds=elapsed_seconds,
            subject_thread_id=subject_thread_id,
        )
    except DesktopSubjectValidationError as error:
        candidate_failure_reason = error.reason
        observation = build_desktop_observation(
            dispatch,
            outcome="candidate_failure",
            elapsed_seconds=elapsed_seconds,
            subject_thread_id=subject_thread_id,
            validate=False,
        )
    except ValueError:
        if effective_outcome != "completed":
            raise
        effective_outcome = "infrastructure_failure"
        effective_reason = "environment_error"
        observation = build_desktop_observation(
            dispatch,
            outcome=effective_outcome,
            elapsed_seconds=elapsed_seconds,
            subject_thread_id=subject_thread_id,
        )

    artifact_directory = str(
        dispatch.workspace.artifact_dir.relative_to(paths.runs_root)
    ).replace("\\", "/")
    if candidate_failure_reason is not None:
        try:
            subject_evidence = record_subject_evidence(observation, dispatch.workspace)
            diff = capture_diff(dispatch.workspace, _scenario_for(manifest, slot))
            subject_evidence_name = subject_evidence.name
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
            diff = _empty_diff()
            subject_evidence_name = "not_available"
        _finalize_desktop_candidate_failure(
            manifest,
            slot,
            dispatch,
            contract_sha256,
            scenario_contract_sha256,
            generation,
            candidate_failure_reason,
            elapsed_seconds,
            subject_thread_id,
            artifact_directory,
            subject_evidence_name,
            diff,
        )
        return
    try:
        subject_evidence = record_subject_evidence(observation, dispatch.workspace)
        diff = capture_diff(dispatch.workspace, _scenario_for(manifest, slot))
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
        _finalize_desktop_infrastructure_failure(
            manifest,
            paths,
            slot,
            dispatch,
            contract_sha256,
            scenario_contract_sha256,
            generation,
            "harness_error",
            elapsed_seconds,
            subject_thread_id,
            artifact_directory,
            "not_available",
        )
        return

    if effective_outcome == "infrastructure_failure":
        _finalize_desktop_infrastructure_failure(
            manifest,
            paths,
            slot,
            dispatch,
            contract_sha256,
            scenario_contract_sha256,
            generation,
            effective_reason,
            elapsed_seconds,
            subject_thread_id,
            artifact_directory,
            subject_evidence.name,
        )
        return

    if effective_outcome == "completed":
        scenario = _scenario_for(manifest, slot)
        try:
            oracle = run_oracles(
                dispatch.workspace,
                scenario,
                paths.fixture_clone / str(scenario["evaluator_path"]),
                manifest.oracle_timeout_seconds,
            )
            oracle_evidence = _save_oracle_evidence(
                oracle,
                dispatch.workspace.artifact_dir,
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
            _finalize_desktop_infrastructure_failure(
                manifest,
                paths,
                slot,
                dispatch,
                contract_sha256,
                scenario_contract_sha256,
                generation,
                "harness_error",
                elapsed_seconds,
                subject_thread_id,
                artifact_directory,
                subject_evidence.name,
            )
            return

    write_attempt_receipt(
        dispatch,
        ATTEMPT_RECEIPTS_ROOT,
        outcome=effective_outcome,
        reason=effective_reason,
        elapsed_seconds=elapsed_seconds,
        subject_thread_id=subject_thread_id,
        artifact_directory=artifact_directory,
        subject_evidence=subject_evidence.name,
    )
    attempts = _desktop_attempts(slot, generation)
    if effective_outcome == "timeout":
        document = _run_document(
            manifest,
            slot,
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
    else:
        reasons = list(oracle.automatic_failure_reasons)
        if diff.outside_boundary:
            reasons.append("outside_boundary")
        document = _run_document(
            manifest,
            slot,
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
            oracle_results=_serialize_oracles(oracle, dispatch.workspace.root),
            telemetry=_read_subject_telemetry(subject_evidence),
        )
        document["attempts"][-1]["oracle_evidence"] = str(
            oracle_evidence.relative_to(dispatch.workspace.artifact_dir)
        ).replace("\\", "/")
    _write_json(_run_document_path(slot, generation), document)
    print(
        _console_json(
            {
                "dispatch_id": dispatch.dispatch_id,
                "terminal_state": document["terminal_state"],
            }
        )
    )


def _finalize_desktop_infrastructure_failure(
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
    slot: RunSlot,
    dispatch: SubjectDispatch,
    contract_sha256: str,
    scenario_contract_sha256: str,
    generation: int,
    reason: str,
    elapsed_seconds: float | None,
    subject_thread_id: str | None,
    artifact_directory: str,
    subject_evidence: str,
) -> None:
    write_attempt_receipt(
        dispatch,
        ATTEMPT_RECEIPTS_ROOT,
        outcome="infrastructure_failure",
        reason=reason,
        elapsed_seconds=elapsed_seconds,
        subject_thread_id=subject_thread_id,
        artifact_directory=artifact_directory,
        subject_evidence=subject_evidence,
    )
    attempts = _desktop_attempts(slot, generation)
    if can_retry(reason, dispatch.attempt):
        print(
            _console_json(
                {
                    "dispatch_id": dispatch.dispatch_id,
                    "state": "retry_required",
                    "next_attempt": dispatch.attempt + 1,
                }
            )
        )
        return
    document = _infrastructure_document(
        manifest,
        slot,
        contract_sha256,
        scenario_contract_sha256,
        generation,
        attempts,
        reason,
    )
    _write_json(_run_document_path(slot, generation), document)
    print(
        _console_json(
            {
                "dispatch_id": dispatch.dispatch_id,
                "terminal_state": document["terminal_state"],
            }
        )
    )


def _finalize_desktop_candidate_failure(
    manifest: BenchmarkManifest,
    slot: RunSlot,
    dispatch: SubjectDispatch,
    contract_sha256: str,
    scenario_contract_sha256: str,
    generation: int,
    reason: str,
    elapsed_seconds: float | None,
    subject_thread_id: str | None,
    artifact_directory: str,
    subject_evidence: str,
    diff: Any,
) -> None:
    """不可變 Subject 契約被違反時，直接留下不可重跑的失敗證據。"""

    if reason not in {"candidate_incomplete", "invalid_claim"}:
        raise ValueError(f"invalid desktop candidate failure reason: {reason}")
    write_attempt_receipt(
        dispatch,
        ATTEMPT_RECEIPTS_ROOT,
        outcome="candidate_failure",
        reason=reason,
        elapsed_seconds=elapsed_seconds,
        subject_thread_id=subject_thread_id,
        artifact_directory=artifact_directory,
        subject_evidence=subject_evidence,
    )
    attempts = _desktop_attempts(slot, generation)
    document = _run_document(
        manifest,
        slot,
        contract_sha256,
        scenario_contract_sha256,
        generation,
        diff,
        attempts,
        terminal_state="automatic_failure",
        reasons=[reason],
        oracle_results=[],
        telemetry="not_available",
    )
    _write_json(_run_document_path(slot, generation), document)
    print(
        _console_json(
            {
                "dispatch_id": dispatch.dispatch_id,
                "terminal_state": document["terminal_state"],
            }
        )
    )


def _empty_diff() -> DiffEvidence:
    return DiffEvidence(
        diff="",
        diff_sha256=hashlib.sha256(b"").hexdigest(),
        changed_paths=(),
        renamed_paths=(),
        outside_boundary=(),
    )


def _next_desktop_attempt(
    slot: RunSlot,
    generation: int,
    receipts_root: Path = ATTEMPT_RECEIPTS_ROOT,
) -> int:
    receipts = _desktop_attempts(slot, generation, receipts_root)
    if not receipts:
        return 1
    last = receipts[-1]
    attempt = last.get("attempt")
    reason = last.get("reason")
    if isinstance(attempt, int) and isinstance(reason, str) and can_retry(
        reason, attempt
    ):
        return attempt + 1
    raise RuntimeError(
        "Desktop run has a non-retryable attempt but no terminal document"
    )


def _desktop_attempts(
    slot: RunSlot,
    generation: int,
    receipts_root: Path = ATTEMPT_RECEIPTS_ROOT,
) -> list[dict[str, object]]:
    attempts: list[dict[str, object]] = []
    for attempt in (1, 2):
        path = _attempt_receipt_path(slot, generation, attempt, receipts_root)
        if not path.is_file():
            continue
        receipt = _read_json(path)
        if (
            receipt.get("logical_run_id") != slot.run_id
            or receipt.get("generation") != generation
            or receipt.get("attempt") != attempt
        ):
            raise ValueError("desktop attempt receipt does not match its run")
        attempts.append(
            {
                "attempt": attempt,
                "physical_run_id": receipt.get("physical_run_id"),
                "outcome": receipt.get("outcome"),
                "reason": receipt.get("reason"),
                "artifact_directory": receipt.get("artifact_directory"),
                "subject_evidence": receipt.get("subject_evidence"),
                "receipt": str(path.relative_to(receipts_root.parent)).replace(
                    "\\", "/"
                ),
            }
        )
    return attempts


def _require_no_inflight_desktop_attempts(
    slot: RunSlot,
    generation: int,
    dispatch_root: Path = DISPATCH_ROOT,
    receipts_root: Path = ATTEMPT_RECEIPTS_ROOT,
    run_documents_root: Path = RUN_DOCUMENTS,
) -> None:
    """作廢 Generation 前，拒絕遺漏任何正在進行或等待重試的 Attempt。"""

    terminal = (
        run_documents_root
        / slot.scenario_id
        / f"{slot.run_id}--g{generation:02d}.json"
    )
    if terminal.is_file():
        return

    receipts: list[dict[str, object]] = []
    for attempt in (1, 2):
        dispatch = dispatch_root / (
            f"{_desktop_dispatch_id(slot, generation, attempt)}.json"
        )
        receipt_path = receipts_root / slot.run_id / (
            f"g{generation:02d}--a{attempt:02d}.json"
        )
        if dispatch.is_file() and not receipt_path.is_file():
            raise RuntimeError(
                f"cannot invalidate a pending Desktop dispatch: {dispatch.stem}"
            )
        if receipt_path.is_file() and not dispatch.is_file():
            raise RuntimeError("Desktop attempt receipt has no dispatch index")
        if receipt_path.is_file():
            receipts.append(_read_json(receipt_path))

    if not receipts:
        return
    latest = receipts[-1]
    attempt = latest.get("attempt")
    reason = latest.get("reason")
    if isinstance(attempt, int) and isinstance(reason, str) and can_retry(
        reason, attempt
    ):
        raise RuntimeError("cannot invalidate a retry-required Desktop attempt")
    raise RuntimeError("Desktop attempt receipt has no terminal run document")


def _attempt_receipt_path(
    slot: RunSlot,
    generation: int,
    attempt: int,
    receipts_root: Path = ATTEMPT_RECEIPTS_ROOT,
) -> Path:
    return receipts_root / slot.run_id / (
        f"g{generation:02d}--a{attempt:02d}.json"
    )


def _desktop_dispatch_id(slot: RunSlot, generation: int, attempt: int) -> str:
    return f"desktop-dispatch-{slot.run_id}--g{generation:02d}--a{attempt:02d}"


def _dispatch_index_path(dispatch_id: str) -> Path:
    if re.fullmatch(r"desktop-dispatch-[A-Za-z0-9_.-]+", dispatch_id) is None:
        raise ValueError("invalid desktop dispatch ID")
    return DISPATCH_ROOT / f"{dispatch_id}.json"


def _write_dispatch_index(dispatch: SubjectDispatch) -> Path:
    dispatch_id = dispatch.dispatch_id
    path = _dispatch_index_path(dispatch_id)
    _write_json(
        path,
        {
            "schema_version": "desktop-dispatch-index/v1",
            "dispatch_id": dispatch_id,
            "dispatch_sha256": str(dispatch.dispatch_sha256),
            "dispatch_path": str(
                dispatch.dispatch_path.relative_to(RUNS_ROOT)
            ).replace("\\", "/"),
        },
    )
    return path


def _load_dispatch_by_id(dispatch_id: str) -> SubjectDispatch:
    index = _read_json(_dispatch_index_path(dispatch_id))
    if index.get("dispatch_id") != dispatch_id:
        raise ValueError("desktop dispatch index ID mismatch")
    dispatch_path = index.get("dispatch_path")
    if not isinstance(dispatch_path, str):
        raise ValueError("desktop dispatch index path is invalid")
    relative_path = PurePosixPath(dispatch_path.replace("\\", "/"))
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("desktop dispatch index path must be relative")
    dispatch = load_desktop_dispatch(RUNS_ROOT.joinpath(*relative_path.parts))
    if dispatch.dispatch_id != dispatch_id:
        raise ValueError("desktop dispatch ID mismatch")
    if index.get("dispatch_sha256") != dispatch.dispatch_sha256:
        raise ValueError("desktop dispatch index hash mismatch")
    expected_workspace = RUNS_ROOT / "workspaces" / dispatch.physical_run_id
    expected_artifact = RUNS_ROOT / "artifacts" / dispatch.physical_run_id
    expected_dispatch = expected_artifact / "desktop-dispatch.json"
    if (
        dispatch.workspace.root.resolve() != expected_workspace.resolve()
        or dispatch.workspace.artifact_dir.resolve() != expected_artifact.resolve()
        or dispatch.dispatch_path.resolve() != expected_dispatch.resolve()
    ):
        raise ValueError("desktop dispatch path does not match its physical run")
    return dispatch


def _slot_for_run_id(manifest: BenchmarkManifest, run_id: str) -> RunSlot:
    try:
        return next(slot for slot in build_run_slots(manifest) if slot.run_id == run_id)
    except StopIteration as error:
        raise ValueError(f"unknown run ID: {run_id}") from error


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
        _require_no_inflight_desktop_attempts(slot, generation)
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
        **_subject_client_contract(manifest),
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
        "client": contract["client"],
        "client_version": contract["client_version"],
        "subject_executor": contract["subject_executor"],
        "fixture_commit": manifest.fixture_commit,
        "skill_commit": manifest.skill_commit,
        "model": manifest.model,
        "reasoning_effort": manifest.reasoning_effort,
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


def _subject_client_contract(manifest: BenchmarkManifest) -> dict[str, object]:
    return {
        "client": manifest.client,
        "client_version": "not_available",
        "subject_executor": dict(manifest.subject_executor),
    }


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
