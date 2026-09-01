from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from evals.harness.models import (
    BenchmarkManifest,
    RunSlot,
    SubjectDispatch,
    SubjectObservation,
    Workspace,
)
from evals.harness.process import run_process
from evals.harness.subject_runner import build_prompt

DISPATCH_SCHEMA_VERSION = "desktop-subject-dispatch/v3"
LEGACY_DISPATCH_SCHEMA_VERSION = "desktop-subject-dispatch/v1"
PROMPT_ENCODING = "utf-8"
PROMPT_LINE_ENDINGS = "lf"
REPORT_SCHEMA_VERSION = "desktop-subject-report/v1"
REPORT_FILENAME = ".benchmark-subject-report.json"
REPORT_TEMPLATE_FILENAME = "subject-report.template.json"
MAX_REPORT_BYTES = 64 * 1024
DESKTOP_EXECUTOR = "codex-desktop-collaboration"
DESKTOP_DISPATCH_MODE = "external-collaboration-subagent"


class DesktopSubjectValidationError(ValueError):
    """表示 Subject 證據違反不可重跑的候選契約。"""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        if reason not in {"candidate_incomplete", "invalid_claim"}:
            raise ValueError(f"invalid desktop candidate failure reason: {reason}")
        self.reason = reason


@dataclass(frozen=True)
class LegacyPendingNewlineDefect:
    """僅描述 v1 Windows 換行 hash 缺陷的待收集 dispatch。"""

    dispatch_id: str
    logical_run_id: str
    physical_run_id: str
    scenario_id: str
    generation: int
    attempt: int
    workspace_root: Path
    artifact_directory: Path
    baseline_commit: str
    prompt_path: Path
    report_path: Path
    prompt_sha256: str
    prompt_bytes_sha256: str
    contract_sha256: str
    scenario_contract_sha256: str
    dispatch_sha256: str


def stage_desktop_subject(
    slot: RunSlot,
    manifest: BenchmarkManifest,
    workspace: Workspace,
    generation: int,
    attempt: int,
    physical_run_id: str,
    contract_sha256: str,
    scenario_contract_sha256: str,
    controller_dispatch_root: Path,
) -> SubjectDispatch:
    """寫入 Subject staged artifacts 與私有 controller dispatch。"""

    if manifest.client != DESKTOP_EXECUTOR:
        raise ValueError("Desktop staging requires the Desktop collaboration client")
    if generation <= 0 or attempt <= 0:
        raise ValueError("generation and attempt must be positive")
    _require_sha256(contract_sha256, "contract")
    _require_sha256(scenario_contract_sha256, "scenario contract")

    executor = manifest.subject_executor
    if (
        executor.get("kind") != DESKTOP_EXECUTOR
        or executor.get("dispatch_mode") != DESKTOP_DISPATCH_MODE
        or executor.get("network_enforcement") != "not_available"
        or executor.get("telemetry") != "not_available"
    ):
        raise ValueError("Desktop subject executor contract is invalid")
    report_relative_path = str(executor.get("report_relative_path", ""))
    if report_relative_path != REPORT_FILENAME:
        raise ValueError("Desktop report path is invalid")
    report_path = workspace.root / report_relative_path
    if report_path.exists():
        raise FileExistsError(f"subject report already exists: {report_path}")

    prompt = build_prompt(_scenario_for(manifest, slot.scenario_id), slot.arm_id)
    prompt_bytes = _utf8_lf_bytes(prompt)
    prompt_sha256 = _sha256_bytes(prompt_bytes)
    prompt_path = workspace.artifact_dir / "prompt.md"
    report_template_path = workspace.artifact_dir / REPORT_TEMPLATE_FILENAME
    staged_legacy_dispatch_path = workspace.artifact_dir / "desktop-dispatch.json"
    dispatch_id = f"desktop-dispatch-{slot.run_id}--g{generation:02d}--a{attempt:02d}"
    _require_private_controller_dispatch_root(controller_dispatch_root, workspace)
    dispatch_path = controller_dispatch_root / f"{dispatch_id}.json"
    if (
        prompt_path.exists()
        or report_template_path.exists()
        or staged_legacy_dispatch_path.exists()
        or dispatch_path.exists()
    ):
        raise FileExistsError("desktop subject dispatch already exists")

    payload: dict[str, object] = {
        "schema_version": DISPATCH_SCHEMA_VERSION,
        "dispatch_id": dispatch_id,
        "logical_run_id": slot.run_id,
        "physical_run_id": physical_run_id,
        "scenario_id": slot.scenario_id,
        "generation": generation,
        "attempt": attempt,
        "workspace_root": str(workspace.root),
        "artifact_directory": str(workspace.artifact_dir),
        "baseline_commit": workspace.baseline_commit,
        "prompt_encoding": PROMPT_ENCODING,
        "prompt_line_endings": PROMPT_LINE_ENDINGS,
        "prompt_sha256": prompt_sha256,
        "contract_sha256": contract_sha256,
        "scenario_contract_sha256": scenario_contract_sha256,
        "fixture_commit": manifest.fixture_commit,
        "skill_commit": manifest.skill_commit,
        "model": manifest.model,
        "reasoning_effort": manifest.reasoning_effort,
        "executor": dict(executor),
        "report_relative_path": report_relative_path,
        "report_template_relative_path": REPORT_TEMPLATE_FILENAME,
    }
    dispatch_sha256 = _sha256_json(payload)
    payload["dispatch_sha256"] = dispatch_sha256
    prompt_path.write_bytes(prompt_bytes)
    controller_dispatch_root.mkdir(parents=True, exist_ok=True)
    dispatch_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report_template_path.write_text(
        json.dumps(
            _report_template(
                baseline_commit=workspace.baseline_commit,
                prompt_sha256=prompt_sha256,
                contract_sha256=contract_sha256,
                scenario_contract_sha256=scenario_contract_sha256,
                dispatch_sha256=dispatch_sha256,
                generation=generation,
                attempt=attempt,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return SubjectDispatch(
        dispatch_id=dispatch_id,
        logical_run_id=slot.run_id,
        physical_run_id=str(payload["physical_run_id"]),
        scenario_id=slot.scenario_id,
        generation=generation,
        attempt=attempt,
        workspace=workspace,
        prompt_path=prompt_path,
        report_template_path=report_template_path,
        report_path=report_path,
        report_relative_path=report_relative_path,
        dispatch_path=dispatch_path,
        prompt_sha256=prompt_sha256,
        contract_sha256=contract_sha256,
        scenario_contract_sha256=scenario_contract_sha256,
        dispatch_sha256=dispatch_sha256,
    )


def desktop_subject_instruction(dispatch: SubjectDispatch) -> str:
    """提供給外層 Sol 派發新鮮 Desktop Subject 的最小指令。"""

    return "\n".join(
        (
            "你是獨立 Benchmark Subject。",
            f"只能在此 Workspace 工作：{dispatch.workspace.root}",
            (
                "可讀取 Workspace 內完成任務所需的檔案；不可讀取其他 Run、"
                "Harness、Fixture 原始庫、Evaluator 或 Review 資料。"
            ),
            "Workspace 外唯一允許讀取的例外，僅限下列 staged 檔案：",
            f"- 任務 Prompt：{dispatch.prompt_path}",
            f"- 已預填不可變欄位的 Report Template：{dispatch.report_template_path}",
            (
                "若 Prompt 明確指定某個 Skill，才可讀取 Workspace 已 staged 的"
                "該 Skill，以及其直接引用、完成任務所必要的 references；"
                "不得讀取其他 Skill。"
            ),
            "不得修改 .git、Benchmark 控制檔或其他 Workspace。",
            f"完成後，寫入此 ignored JSON report：{dispatch.report_path}",
            (
                "請以 Report Template 為起點，只補齊可變的執行結果欄位；不得更動"
                "其中已預填的 hash、baseline、generation 或 attempt。"
            ),
            (
                "report 必須含 dispatch_sha256、baseline_commit、prompt_sha256、"
                "contract_sha256、scenario_contract_sha256、generation、attempt、"
                "completion、summary、files_inspected、files_modified_claimed、"
                "commands_claimed 與 telemetry=not_available。"
            ),
            (
                "files_inspected 與 files_modified_claimed 僅接受 Workspace "
                "repository-relative POSIX path；不得使用絕對路徑、.. 或反斜線。"
            ),
            (
                "Workspace 外 staged Prompt 或 Report Template 不得列入"
                " files_inspected 或 files_modified_claimed。"
            ),
            (
                'commands_claimed=[{"command":"...","outcome":'
                '"passed|failed|not_run"}]；沒有執行命令時使用空陣列。'
            ),
        )
    )


def validate_desktop_report(dispatch: SubjectDispatch) -> dict[str, object]:
    """驗證 Subject 報告只引用當次不可變 dispatch。"""

    path = dispatch.report_path
    if not path.is_file():
        raise DesktopSubjectValidationError(
            "candidate_incomplete", "desktop subject report is missing"
        )
    if path.stat().st_size > MAX_REPORT_BYTES:
        raise DesktopSubjectValidationError(
            "candidate_incomplete", "desktop subject report exceeds maximum size"
        )
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DesktopSubjectValidationError(
            "candidate_incomplete", "desktop subject report is invalid JSON"
        ) from error
    if not isinstance(report, dict):
        raise DesktopSubjectValidationError(
            "candidate_incomplete", "desktop subject report must be an object"
        )

    required = {
        "schema_version",
        "dispatch_sha256",
        "baseline_commit",
        "prompt_sha256",
        "contract_sha256",
        "scenario_contract_sha256",
        "generation",
        "attempt",
        "completion",
        "summary",
        "files_inspected",
        "files_modified_claimed",
        "commands_claimed",
        "telemetry",
    }
    missing = required - set(report)
    if missing:
        raise DesktopSubjectValidationError(
            "candidate_incomplete",
            f"desktop subject report missing fields: {sorted(missing)}",
        )
    if report["schema_version"] != REPORT_SCHEMA_VERSION:
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject report schema is invalid"
        )
    if report["dispatch_sha256"] != dispatch.dispatch_sha256:
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject report dispatch hash mismatch"
        )
    if report["baseline_commit"] != dispatch.workspace.baseline_commit:
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject report baseline mismatch"
        )
    if report["prompt_sha256"] != dispatch.prompt_sha256:
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject report prompt hash mismatch"
        )
    if report["contract_sha256"] != dispatch.contract_sha256:
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject report contract hash mismatch"
        )
    if report["scenario_contract_sha256"] != dispatch.scenario_contract_sha256:
        raise DesktopSubjectValidationError(
            "invalid_claim",
            "desktop subject report scenario contract hash mismatch",
        )
    if report["generation"] != dispatch.generation:
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject report generation mismatch"
        )
    if report["attempt"] != dispatch.attempt:
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject report attempt mismatch"
        )
    if report["completion"] != "completed":
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject report completion is invalid"
        )
    if not isinstance(report["summary"], str):
        raise DesktopSubjectValidationError(
            "candidate_incomplete", "desktop subject report summary must be text"
        )
    try:
        _validate_workspace_relative_paths(
            report["files_inspected"], "files_inspected", dispatch.workspace.root
        )
        _validate_workspace_relative_paths(
            report["files_modified_claimed"],
            "files_modified_claimed",
            dispatch.workspace.root,
        )
        _validate_commands(report["commands_claimed"])
    except ValueError as error:
        raise DesktopSubjectValidationError(
            "candidate_incomplete", str(error)
        ) from error
    if report["telemetry"] != "not_available":
        raise DesktopSubjectValidationError(
            "invalid_claim", "Desktop telemetry must be not_available"
        )
    return report


def build_desktop_observation(
    dispatch: SubjectDispatch,
    outcome: str,
    elapsed_seconds: float | None,
    subject_thread_id: str | None,
    validate: bool = True,
) -> SubjectObservation:
    """將外層編排觀察轉成可保存的 Subject 證據。"""

    if outcome not in {
        "completed",
        "timeout",
        "infrastructure_failure",
        "candidate_failure",
    }:
        raise ValueError(f"invalid Desktop subject outcome: {outcome}")
    report_sha256 = "not_available"
    if validate:
        _validate_workspace_baseline(dispatch.workspace)
    if outcome == "completed" and validate:
        validate_desktop_report(dispatch)
        report_sha256 = _sha256_file(dispatch.report_path)
    elif dispatch.report_path.is_file():
        report_sha256 = _sha256_file(dispatch.report_path)
    return SubjectObservation(
        run_id=dispatch.physical_run_id,
        command=None,
        prompt_sha256=dispatch.prompt_sha256,
        raw_jsonl_path=None,
        last_message_path=None,
        executor=DESKTOP_EXECUTOR,
        completion_outcome=outcome,
        elapsed_seconds=elapsed_seconds,
        dispatch_path=dispatch.dispatch_path,
        dispatch_sha256=dispatch.dispatch_sha256,
        report_path=dispatch.report_path if dispatch.report_path.is_file() else None,
        report_sha256=report_sha256,
        subject_thread_id=subject_thread_id,
        telemetry="not_available",
    )


def write_attempt_receipt(
    dispatch: SubjectDispatch,
    receipts_root: Path,
    outcome: str,
    reason: str,
    elapsed_seconds: float | None,
    subject_thread_id: str | None,
    artifact_directory: str | None = None,
    subject_evidence: str | None = None,
) -> Path:
    """保存一次 Desktop 交付觀察；同一 Attempt 不可覆寫。"""

    if not reason.strip():
        raise ValueError("attempt receipt reason must not be empty")
    if outcome not in {
        "completed",
        "timeout",
        "infrastructure_failure",
        "candidate_failure",
    }:
        raise ValueError(f"invalid Desktop receipt outcome: {outcome}")
    path = receipts_root / dispatch.logical_run_id / (
        f"g{dispatch.generation:02d}--a{dispatch.attempt:02d}.json"
    )
    if path.exists():
        raise FileExistsError(f"attempt receipt already exists: {path}")
    report_sha256 = (
        _sha256_file(dispatch.report_path)
        if dispatch.report_path.is_file()
        else "not_available"
    )
    payload = {
        "schema_version": "desktop-subject-attempt/v1",
        "dispatch_id": dispatch.dispatch_id,
        "dispatch_sha256": dispatch.dispatch_sha256,
        "logical_run_id": dispatch.logical_run_id,
        "physical_run_id": dispatch.physical_run_id,
        "scenario_id": dispatch.scenario_id,
        "generation": dispatch.generation,
        "attempt": dispatch.attempt,
        "outcome": outcome,
        "reason": reason.strip(),
        "elapsed_seconds": elapsed_seconds
        if elapsed_seconds is not None
        else "not_available",
        "subject_thread_id": subject_thread_id or "not_available",
        "report_sha256": report_sha256,
        "artifact_directory": artifact_directory or "not_available",
        "subject_evidence": subject_evidence or "not_available",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def load_desktop_dispatch(path: Path) -> SubjectDispatch:
    """由私有 dispatch 檔重新建立 collect 所需的資料。"""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("desktop dispatch must be an object")
    expected_hash = payload.get("dispatch_sha256")
    unsigned = dict(payload)
    unsigned.pop("dispatch_sha256", None)
    if not isinstance(expected_hash, str) or expected_hash != _sha256_json(unsigned):
        raise ValueError("desktop dispatch hash mismatch")
    if payload.get("schema_version") != DISPATCH_SCHEMA_VERSION:
        raise ValueError("desktop dispatch schema is unsupported; v3 is required")
    required_strings = (
        "dispatch_id",
        "logical_run_id",
        "physical_run_id",
        "scenario_id",
        "workspace_root",
        "artifact_directory",
        "baseline_commit",
        "prompt_encoding",
        "prompt_line_endings",
        "prompt_sha256",
        "contract_sha256",
        "scenario_contract_sha256",
        "report_relative_path",
        "report_template_relative_path",
    )
    if not all(isinstance(payload.get(name), str) for name in required_strings):
        raise ValueError("desktop dispatch has invalid string fields")
    if not isinstance(payload.get("generation"), int) or not isinstance(
        payload.get("attempt"), int
    ):
        raise ValueError("desktop dispatch has invalid generation or attempt")
    if payload["generation"] <= 0 or payload["attempt"] <= 0:
        raise ValueError("desktop dispatch generation and attempt must be positive")
    if payload["prompt_encoding"] != PROMPT_ENCODING:
        raise ValueError("desktop dispatch prompt encoding is invalid")
    if payload["prompt_line_endings"] != PROMPT_LINE_ENDINGS:
        raise ValueError("desktop dispatch prompt line endings are invalid")
    _require_sha256(str(payload["prompt_sha256"]), "prompt")
    _require_sha256(str(payload["contract_sha256"]), "contract")
    _require_sha256(str(payload["scenario_contract_sha256"]), "scenario contract")
    executor = payload.get("executor")
    if (
        not isinstance(executor, dict)
        or executor.get("kind") != DESKTOP_EXECUTOR
        or executor.get("dispatch_mode") != DESKTOP_DISPATCH_MODE
        or executor.get("network_enforcement") != "not_available"
        or executor.get("telemetry") != "not_available"
    ):
        raise ValueError("desktop dispatch executor is invalid")
    workspace = Workspace(
        root=Path(str(payload["workspace_root"])),
        artifact_dir=Path(str(payload["artifact_directory"])),
        baseline_commit=str(payload["baseline_commit"]),
    )
    prompt_path = workspace.artifact_dir / "prompt.md"
    if not prompt_path.is_file():
        raise ValueError("desktop dispatch prompt hash mismatch")
    prompt_bytes = prompt_path.read_bytes()
    try:
        prompt_bytes.decode(PROMPT_ENCODING)
    except UnicodeDecodeError as error:
        raise ValueError("desktop dispatch prompt is not UTF-8") from error
    if b"\r" in prompt_bytes or _sha256_bytes(prompt_bytes) != str(
        payload["prompt_sha256"]
    ):
        raise ValueError("desktop dispatch prompt hash mismatch")
    report_relative_path = str(payload["report_relative_path"])
    if report_relative_path != REPORT_FILENAME:
        raise ValueError("desktop dispatch report path is invalid")
    report_template_relative_path = str(payload["report_template_relative_path"])
    if report_template_relative_path != REPORT_TEMPLATE_FILENAME:
        raise ValueError("desktop dispatch report template path is invalid")
    report_template_path = workspace.artifact_dir / report_template_relative_path
    if not report_template_path.is_file():
        raise ValueError("desktop dispatch report template is missing")
    if _paths_overlap(path.resolve(), workspace.root.resolve()) or _paths_overlap(
        path.resolve(), workspace.artifact_dir.resolve()
    ):
        raise ValueError("desktop dispatch must remain outside subject-readable paths")
    dispatch = SubjectDispatch(
        dispatch_id=str(payload["dispatch_id"]),
        logical_run_id=str(payload["logical_run_id"]),
        physical_run_id=str(payload["physical_run_id"]),
        scenario_id=str(payload["scenario_id"]),
        generation=int(payload["generation"]),
        attempt=int(payload["attempt"]),
        workspace=workspace,
        prompt_path=prompt_path,
        report_template_path=report_template_path,
        report_path=workspace.root / report_relative_path,
        report_relative_path=report_relative_path,
        dispatch_path=path,
        prompt_sha256=str(payload["prompt_sha256"]),
        contract_sha256=str(payload["contract_sha256"]),
        scenario_contract_sha256=str(payload["scenario_contract_sha256"]),
        dispatch_sha256=str(expected_hash),
    )
    _validate_report_template(dispatch)
    return dispatch


def inspect_legacy_pending_newline_defect(
    path: Path,
) -> LegacyPendingNewlineDefect:
    """嚴格辨識唯一可恢復的 v1 Windows 換行 hash 缺陷。

    v1 dispatch 不可再進入一般 collect 流程。這個檢查只提供給明確的
    pre-collection invalidation，任何不完全符合已知簽章的資料都會拒絕。
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("legacy desktop dispatch is invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("legacy desktop dispatch must be an object")
    expected_hash = payload.get("dispatch_sha256")
    unsigned = dict(payload)
    unsigned.pop("dispatch_sha256", None)
    if not isinstance(expected_hash, str) or expected_hash != _sha256_json(unsigned):
        raise ValueError("legacy desktop dispatch hash mismatch")
    if payload.get("schema_version") != LEGACY_DISPATCH_SCHEMA_VERSION:
        raise ValueError("legacy desktop dispatch must use v1")

    required_strings = (
        "dispatch_id",
        "logical_run_id",
        "physical_run_id",
        "scenario_id",
        "workspace_root",
        "artifact_directory",
        "baseline_commit",
        "prompt_sha256",
        "contract_sha256",
        "scenario_contract_sha256",
        "report_relative_path",
        "report_template_relative_path",
    )
    if not all(isinstance(payload.get(name), str) for name in required_strings):
        raise ValueError("legacy desktop dispatch has invalid string fields")
    generation = payload.get("generation")
    attempt = payload.get("attempt")
    if (
        not isinstance(generation, int)
        or not isinstance(attempt, int)
        or generation <= 0
        or attempt <= 0
    ):
        raise ValueError("legacy desktop dispatch has invalid generation or attempt")
    _require_sha256(str(payload["prompt_sha256"]), "legacy prompt")
    _require_sha256(str(payload["contract_sha256"]), "legacy contract")
    _require_sha256(
        str(payload["scenario_contract_sha256"]), "legacy scenario contract"
    )
    if re.fullmatch(r"[0-9a-f]{40}", str(payload["baseline_commit"])) is None:
        raise ValueError("legacy desktop dispatch baseline is invalid")
    _validate_desktop_executor(payload.get("executor"), "legacy desktop dispatch")

    workspace_root = Path(str(payload["workspace_root"]))
    artifact_directory = Path(str(payload["artifact_directory"]))
    prompt_path = artifact_directory / "prompt.md"
    if not prompt_path.is_file():
        raise ValueError("legacy desktop dispatch prompt is missing")
    prompt_bytes = prompt_path.read_bytes()
    if b"\r\n" not in prompt_bytes or b"\r" in prompt_bytes.replace(b"\r\n", b""):
        raise ValueError(
            "legacy desktop dispatch does not have the Windows newline defect"
        )
    try:
        prompt_text = prompt_bytes.decode(PROMPT_ENCODING)
    except UnicodeDecodeError as error:
        raise ValueError("legacy desktop dispatch prompt is not UTF-8") from error
    prompt_bytes_sha256 = _sha256_bytes(prompt_bytes)
    prompt_sha256 = str(payload["prompt_sha256"])
    legacy_logical_sha256 = _sha256_text(
        prompt_text.replace("\r\n", "\n").replace("\r", "\n")
    )
    if (
        prompt_sha256 != legacy_logical_sha256
        or prompt_sha256 == prompt_bytes_sha256
    ):
        raise ValueError(
            "legacy desktop dispatch does not have the Windows newline defect"
        )

    if payload["report_relative_path"] != REPORT_FILENAME:
        raise ValueError("legacy desktop dispatch report path is invalid")
    if payload["report_template_relative_path"] != REPORT_TEMPLATE_FILENAME:
        raise ValueError("legacy desktop dispatch report template path is invalid")
    report_path = workspace_root / REPORT_FILENAME
    _validate_legacy_report(
        report_path,
        dispatch_sha256=str(expected_hash),
        baseline_commit=str(payload["baseline_commit"]),
        prompt_sha256=prompt_sha256,
        contract_sha256=str(payload["contract_sha256"]),
        scenario_contract_sha256=str(payload["scenario_contract_sha256"]),
        generation=generation,
        attempt=attempt,
    )
    return LegacyPendingNewlineDefect(
        dispatch_id=str(payload["dispatch_id"]),
        logical_run_id=str(payload["logical_run_id"]),
        physical_run_id=str(payload["physical_run_id"]),
        scenario_id=str(payload["scenario_id"]),
        generation=generation,
        attempt=attempt,
        workspace_root=workspace_root,
        artifact_directory=artifact_directory,
        baseline_commit=str(payload["baseline_commit"]),
        prompt_path=prompt_path,
        report_path=report_path,
        prompt_sha256=prompt_sha256,
        prompt_bytes_sha256=prompt_bytes_sha256,
        contract_sha256=str(payload["contract_sha256"]),
        scenario_contract_sha256=str(payload["scenario_contract_sha256"]),
        dispatch_sha256=str(expected_hash),
    )


def _validate_legacy_report(
    path: Path,
    *,
    dispatch_sha256: str,
    baseline_commit: str,
    prompt_sha256: str,
    contract_sha256: str,
    scenario_contract_sha256: str,
    generation: int,
    attempt: int,
) -> None:
    if not path.is_file() or path.stat().st_size > MAX_REPORT_BYTES:
        raise ValueError("legacy desktop dispatch report is missing or oversized")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("legacy desktop dispatch report is invalid JSON") from error
    if not isinstance(report, dict):
        raise ValueError("legacy desktop dispatch report must be an object")
    expected = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "dispatch_sha256": dispatch_sha256,
        "baseline_commit": baseline_commit,
        "prompt_sha256": prompt_sha256,
        "contract_sha256": contract_sha256,
        "scenario_contract_sha256": scenario_contract_sha256,
        "generation": generation,
        "attempt": attempt,
        "completion": "completed",
        "telemetry": "not_available",
    }
    for field, value in expected.items():
        if report.get(field) != value:
            raise ValueError(f"legacy desktop dispatch report {field} mismatch")
    if not isinstance(report.get("summary"), str):
        raise ValueError("legacy desktop dispatch report summary is invalid")
    for field in (
        "files_inspected",
        "files_modified_claimed",
        "commands_claimed",
    ):
        if not isinstance(report.get(field), list):
            raise ValueError(f"legacy desktop dispatch report {field} is invalid")


def _validate_desktop_executor(value: object, label: str) -> None:
    if (
        not isinstance(value, dict)
        or value.get("kind") != DESKTOP_EXECUTOR
        or value.get("dispatch_mode") != DESKTOP_DISPATCH_MODE
        or value.get("network_enforcement") != "not_available"
        or value.get("telemetry") != "not_available"
    ):
        raise ValueError(f"{label} executor is invalid")


def _scenario_for(
    manifest: BenchmarkManifest, scenario_id: str
) -> dict[str, object]:
    try:
        return next(
            scenario
            for scenario in manifest.scenarios
            if scenario["id"] == scenario_id
        )
    except StopIteration as error:
        raise ValueError(f"unknown scenario: {scenario_id}") from error


def _validate_workspace_relative_paths(
    value: object,
    field: str,
    workspace_root: Path,
) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"desktop subject report {field} must be a string list")
    resolved_workspace_root = workspace_root.resolve()
    for item in value:
        candidate = PurePosixPath(item)
        if (
            not item
            or "\\" in item
            or candidate.is_absolute()
            or ".." in candidate.parts
            or re.match(r"^[A-Za-z]:", item) is not None
            or not candidate.parts
            or candidate == PurePosixPath(".")
            or not _is_within(
                (resolved_workspace_root / candidate).resolve(),
                resolved_workspace_root,
            )
        ):
            raise ValueError(
                f"desktop subject report {field} contains a non-relative path"
            )


def _require_private_controller_dispatch_root(
    controller_dispatch_root: Path,
    workspace: Workspace,
) -> None:
    root = controller_dispatch_root.resolve()
    if _paths_overlap(root, workspace.root.resolve()) or _paths_overlap(
        root, workspace.artifact_dir.resolve()
    ):
        raise ValueError(
            "desktop controller dispatch root overlaps subject-readable paths"
        )


def _paths_overlap(first: Path, second: Path) -> bool:
    return _is_within(first, second) or _is_within(second, first)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_commands(value: object) -> None:
    if not isinstance(value, list):
        raise ValueError("desktop subject report commands_claimed must be a list")
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("desktop subject report command must be an object")
        if not isinstance(item.get("command"), str):
            raise ValueError("desktop subject report command text is invalid")
        if item.get("outcome") not in {"passed", "failed", "not_run"}:
            raise ValueError("desktop subject report command outcome is invalid")


def _validate_workspace_baseline(workspace: Workspace) -> None:
    result = run_process(
        ["git", "rev-parse", "HEAD"], workspace.root, timeout_seconds=30
    )
    if result.exit_code != 0 or result.stdout.strip() != workspace.baseline_commit:
        raise DesktopSubjectValidationError(
            "invalid_claim", "desktop subject workspace baseline mismatch"
        )


def _report_template(
    *,
    baseline_commit: str,
    prompt_sha256: str,
    contract_sha256: str,
    scenario_contract_sha256: str,
    dispatch_sha256: str,
    generation: int,
    attempt: int,
) -> dict[str, object]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "dispatch_sha256": dispatch_sha256,
        "baseline_commit": baseline_commit,
        "prompt_sha256": prompt_sha256,
        "contract_sha256": contract_sha256,
        "scenario_contract_sha256": scenario_contract_sha256,
        "generation": generation,
        "attempt": attempt,
        "completion": "completed",
        "summary": "",
        "files_inspected": [],
        "files_modified_claimed": [],
        "commands_claimed": [],
        "telemetry": "not_available",
    }


def _validate_report_template(dispatch: SubjectDispatch) -> None:
    try:
        template = json.loads(dispatch.report_template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("desktop dispatch report template is invalid JSON") from error
    if not isinstance(template, dict):
        raise ValueError("desktop dispatch report template must be an object")
    expected = _report_template(
        baseline_commit=dispatch.workspace.baseline_commit,
        prompt_sha256=dispatch.prompt_sha256,
        contract_sha256=dispatch.contract_sha256,
        scenario_contract_sha256=dispatch.scenario_contract_sha256,
        dispatch_sha256=dispatch.dispatch_sha256,
        generation=dispatch.generation,
        attempt=dispatch.attempt,
    )
    for field, value in expected.items():
        if template.get(field) != value:
            raise ValueError(f"desktop dispatch report template {field} mismatch")


def _require_sha256(value: str, label: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"desktop {label} hash is invalid")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def canonical_prompt_sha256(value: str) -> str:
    """以 v2 dispatch 的 UTF-8/LF 實體 bytes 計算 Prompt hash。"""

    return _sha256_bytes(_utf8_lf_bytes(value))


def _utf8_lf_bytes(value: str) -> bytes:
    return value.replace("\r\n", "\n").replace("\r", "\n").encode(PROMPT_ENCODING)


def _sha256_json(value: dict[str, object]) -> str:
    return _sha256_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
