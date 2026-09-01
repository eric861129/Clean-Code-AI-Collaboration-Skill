from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evals.harness.diff_boundary import DIFF_PATHS
from evals.harness.models import SubjectObservation, Workspace
from evals.harness.process import run_process


def record_subject_evidence(
    observation: SubjectObservation,
    workspace: Workspace,
) -> Path:
    status = _git_output(["status", "--short"], workspace)
    diff = _git_output(
        [
            "diff",
            "--binary",
            "--no-ext-diff",
            workspace.baseline_commit,
            "--",
            *DIFF_PATHS,
        ],
        workspace,
    )
    terminal_state = _terminal_state(observation)
    command = observation.command
    evidence = {
        "schema_version": "1.0",
        "run_id": observation.run_id,
        "terminal_state": terminal_state,
        "prompt_sha256": observation.prompt_sha256,
        "executor": observation.executor,
        "completion_outcome": observation.completion_outcome,
        "command": _command_evidence(command),
        "raw_jsonl": {
            "path": _path_name(observation.raw_jsonl_path),
            "sha256": _file_sha256(observation.raw_jsonl_path),
        },
        "last_message": {
            "path": _path_name(observation.last_message_path),
            "sha256": _file_sha256(observation.last_message_path),
        },
        "desktop_dispatch": {
            "path": _path_name(observation.dispatch_path),
            "sha256": observation.dispatch_sha256,
        },
        "desktop_report": {
            "path": _path_name(observation.report_path),
            "sha256": observation.report_sha256,
        },
        "subject_thread_id": observation.subject_thread_id or "not_available",
        "git_status": status,
        "diff": diff,
        "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        "telemetry": (
            observation.telemetry
            if observation.executor == "codex-desktop-collaboration"
            else _read_telemetry(observation.raw_jsonl_path)
        ),
    }
    path = workspace.artifact_dir / "subject-evidence.json"
    serialized = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8") as output:
            output.write(serialized)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != serialized:
            raise FileExistsError("subject evidence is immutable and differs")
    return path


def _git_output(args: list[str], workspace: Workspace) -> str:
    result = run_process(["git", *args], workspace.root, timeout_seconds=30)
    if result.exit_code != 0:
        raise RuntimeError(f"git evidence command failed: {args}\n{result.stderr}")
    return result.stdout


def _file_sha256(path: Path | None) -> str:
    if path is None or not path.is_file():
        return "not_available"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_telemetry(path: Path | None) -> dict[str, object]:
    if path is None:
        return {
            "token_usage": "not_available",
            "tool_call_count": "not_available",
            "files_inspected": "not_available",
        }
    token_usage: dict[str, int] | str = "not_available"
    tool_call_count = 0
    tool_call_seen = False
    files_inspected: list[str] | str = "not_available"
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = event.get("usage")
        if isinstance(usage, dict) and all(
            isinstance(key, str) and isinstance(value, int)
            for key, value in usage.items()
        ):
            token_usage = usage
        if event.get("type") == "tool_call":
            tool_call_count += 1
            tool_call_seen = True
        event_files = event.get("files_inspected")
        if isinstance(event_files, list) and all(
            isinstance(item, str) for item in event_files
        ):
            files_inspected = event_files
    return {
        "token_usage": token_usage,
        "tool_call_count": tool_call_count if tool_call_seen else "not_available",
        "files_inspected": files_inspected,
    }


def _terminal_state(observation: SubjectObservation) -> str:
    if observation.executor == "codex-desktop-collaboration":
        return observation.completion_outcome
    if observation.command is None:
        return "subject_failed"
    return (
        "timeout"
        if observation.command.timed_out
        else "completed"
        if observation.command.exit_code == 0
        else "subject_failed"
    )


def _command_evidence(command: object) -> dict[str, object]:
    if command is None:
        return {
            "args": "not_available",
            "exit_code": "not_available",
            "elapsed_seconds": "not_available",
            "timed_out": "not_available",
            "classification": "not_available",
            "attempt": "not_available",
        }
    return {
        "args": list(command.args),
        "exit_code": command.exit_code,
        "elapsed_seconds": command.elapsed_seconds,
        "timed_out": command.timed_out,
        "classification": command.classification,
        "attempt": command.attempt,
    }


def _path_name(path: Path | None) -> str:
    return path.name if path is not None else "not_available"
