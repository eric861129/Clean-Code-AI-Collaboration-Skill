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

IMPLEMENTATION_AUTHORIZATION = (
    "\n\n你已獲授權在目前提供的獨立 Repository 直接實作這項需求。"
    "只修改完成任務所需的檔案，保留既有契約與行為；"
    "完成後執行 Repository Gate，並如實回報未完成或無法驗證的部分。"
)


def build_prompt(
    scenario: dict[str, object], arm_id: str, manifest: BenchmarkManifest
) -> str:
    try:
        arm = next(arm for arm in manifest.arms if arm.id == arm_id)
    except StopIteration as error:
        raise ValueError(f"unknown arm: {arm_id}") from error
    task = _normalize_lf(str(scenario["task"])) + IMPLEMENTATION_AUTHORIZATION
    instruction = _normalize_lf(arm.instruction)
    return task if not instruction else task + f"\n\n{instruction}"


def canonical_prompt_bytes(prompt: str) -> bytes:
    return _normalize_lf(prompt).encode("utf-8")


def _normalize_lf(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def run_subject(
    slot: RunSlot,
    manifest: BenchmarkManifest,
    workspace: Workspace,
    command_override: list[str] | None = None,
    attempt: int = 1,
) -> SubjectObservation:
    scenario = _scenario_for(manifest, slot.scenario_id)
    prompt = build_prompt(scenario, slot.arm_id, manifest)
    prompt_bytes = canonical_prompt_bytes(prompt)
    prompt_sha256 = hashlib.sha256(prompt_bytes).hexdigest()
    workspace.artifact_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = workspace.artifact_dir / "prompt.md"
    raw_jsonl_path = workspace.artifact_dir / "subject.jsonl"
    stderr_path = workspace.artifact_dir / "subject.stderr.txt"
    last_message_path = workspace.artifact_dir / "last-message.md"
    environment_path = workspace.artifact_dir / "subject-environment.json"
    prompt_path.write_bytes(prompt_bytes)

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
        attempt=attempt,
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
