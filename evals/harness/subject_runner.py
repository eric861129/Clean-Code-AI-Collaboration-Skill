from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

from evals.harness.models import (
    BenchmarkManifest,
    RunSlot,
    SubjectObservation,
    Workspace,
)
from evals.harness.process import run_process


def build_prompt(scenario: dict[str, object], arm_id: str) -> str:
    task = str(scenario["task"])
    if arm_id == "control":
        return task
    if arm_id == "generic-clean-code":
        return task + "\n\n請遵守 Clean Code 完成任務。"
    if arm_id == "skill-v0.3.0":
        return task + "\n\n請使用 $clean-code-ai-collaboration 完成任務。"
    raise ValueError(f"unknown arm: {arm_id}")


def run_subject(
    slot: RunSlot,
    manifest: BenchmarkManifest,
    workspace: Workspace,
    command_override: list[str] | None = None,
) -> SubjectObservation:
    scenario = _scenario_for(manifest, slot.scenario_id)
    prompt = build_prompt(scenario, slot.arm_id)
    prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    workspace.artifact_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = workspace.artifact_dir / "prompt.md"
    raw_jsonl_path = workspace.artifact_dir / "subject.jsonl"
    stderr_path = workspace.artifact_dir / "subject.stderr.txt"
    last_message_path = workspace.artifact_dir / "last-message.md"
    environment_path = workspace.artifact_dir / "subject-environment.json"
    prompt_path.write_text(prompt, encoding="utf-8")

    if command_override is None:
        command = _codex_command(manifest, workspace.root, last_message_path)
        version = run_process(
            ["codex", "--version"],
            workspace.root,
            min(manifest.fixture_timeout_seconds, 30),
        )
        cli_version = (
            version.stdout.strip() if version.exit_code == 0 else "not_available"
        )
    else:
        command = command_override
        cli_version = "stub"

    environment_path.write_text(
        json.dumps(
            {
                "run_id": slot.run_id,
                "fixture_commit": manifest.fixture_commit,
                "skill_commit": manifest.skill_commit,
                "baseline_commit": workspace.baseline_commit,
                "prompt_sha256": prompt_sha256,
                "cli_version": cli_version,
                "python_version": sys.version,
                "operating_system": platform.platform(),
                "model": manifest.model,
                "reasoning_effort": manifest.reasoning_effort,
                "sandbox": "workspace-write",
                "network_access": False,
                "approval_policy": "never",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    command_result = run_process(
        command,
        workspace.root,
        manifest.subject_timeout_seconds,
        stdin=prompt,
    )
    raw_jsonl_path.write_text(command_result.stdout, encoding="utf-8")
    stderr_path.write_text(command_result.stderr, encoding="utf-8")
    return SubjectObservation(
        run_id=slot.run_id,
        command=command_result,
        prompt_sha256=prompt_sha256,
        raw_jsonl_path=raw_jsonl_path,
        last_message_path=last_message_path,
    )


def _codex_command(
    manifest: BenchmarkManifest,
    workspace_root: Path,
    last_message_path: Path,
) -> list[str]:
    return [
        "codex",
        "exec",
        "--ephemeral",
        "--json",
        "--ignore-user-config",
        "--strict-config",
        "--sandbox",
        "workspace-write",
        "--model",
        manifest.model,
        "--config",
        f'model_reasoning_effort="{manifest.reasoning_effort}"',
        "--config",
        'approval_policy="never"',
        "--config",
        "sandbox_workspace_write.network_access=false",
        "--cd",
        str(workspace_root),
        "--output-last-message",
        str(last_message_path),
        "-",
    ]


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
