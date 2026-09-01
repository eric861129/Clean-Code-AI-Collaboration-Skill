from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evals.harness.models import SubjectObservation, Workspace
from evals.harness.process import run_process


def record_subject_evidence(
    observation: SubjectObservation,
    workspace: Workspace,
) -> Path:
    status = _git_output(["status", "--short"], workspace)
    diff = _git_output(
        ["diff", "--binary", "--no-ext-diff", workspace.baseline_commit],
        workspace,
    )
    terminal_state = (
        "timeout"
        if observation.command.timed_out
        else "completed"
        if observation.command.exit_code == 0
        else "subject_failed"
    )
    evidence = {
        "schema_version": "1.0",
        "run_id": observation.run_id,
        "terminal_state": terminal_state,
        "prompt_sha256": observation.prompt_sha256,
        "command": {
            "args": list(observation.command.args),
            "exit_code": observation.command.exit_code,
            "elapsed_seconds": observation.command.elapsed_seconds,
            "timed_out": observation.command.timed_out,
            "classification": observation.command.classification,
            "attempt": observation.command.attempt,
        },
        "raw_jsonl": {
            "path": observation.raw_jsonl_path.name,
            "sha256": _file_sha256(observation.raw_jsonl_path),
        },
        "last_message": {
            "path": observation.last_message_path.name,
            "sha256": _file_sha256(observation.last_message_path),
        },
        "git_status": status,
        "diff": diff,
        "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        "telemetry": _read_telemetry(observation.raw_jsonl_path),
    }
    path = workspace.artifact_dir / "subject-evidence.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _git_output(args: list[str], workspace: Workspace) -> str:
    result = run_process(["git", *args], workspace.root, timeout_seconds=30)
    if result.exit_code != 0:
        raise RuntimeError(f"git evidence command failed: {args}\n{result.stderr}")
    return result.stdout


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        return "not_available"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_telemetry(path: Path) -> dict[str, object]:
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
