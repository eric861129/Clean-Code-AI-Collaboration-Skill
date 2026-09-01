from __future__ import annotations

import re
import shutil
from pathlib import Path

from evals.harness.models import CommandResult, OracleEvidence, Workspace
from evals.harness.process import run_process


def run_oracles(
    workspace: Workspace,
    scenario: dict[str, object],
    evaluator_source: Path,
    timeout_seconds: int,
    expect_acceptance_red: bool = False,
) -> OracleEvidence:
    oracle_root = workspace.root / ".benchmark-oracle"
    if oracle_root.exists():
        raise FileExistsError("benchmark oracle already exists in workspace")
    shutil.copytree(evaluator_source, oracle_root)

    commands = scenario["commands"]
    if not isinstance(commands, dict):
        raise ValueError("scenario commands must be an object")
    public = _run_commands(commands["public"], workspace, timeout_seconds)
    preservation = _run_commands(
        commands["preservation"], workspace, timeout_seconds
    )
    acceptance = _run_commands(commands["acceptance"], workspace, timeout_seconds)
    failures: list[str] = []
    if any(
        result.timed_out
        for group in (public, preservation, acceptance)
        for result in group
    ):
        failures.append("oracle_timeout_unclassified")
    if not public or any(result.exit_code != 0 for result in public):
        failures.append("public_gate_failed")
    if not preservation or any(result.exit_code != 0 for result in preservation):
        failures.append("preservation_oracle_failed")

    if expect_acceptance_red:
        markers = [str(item) for item in scenario["expected_baseline_red_markers"]]
        expected_red = baseline_acceptance_is_expected(
            acceptance,
            tuple(markers),
            int(scenario["expected_baseline_failure_count"]),
        )
        if not expected_red:
            failures.append("acceptance_oracle_not_expected_red")
    elif not acceptance or any(result.exit_code != 0 for result in acceptance):
        failures.append("acceptance_oracle_failed")

    return OracleEvidence(
        public=public,
        preservation=preservation,
        acceptance=acceptance,
        automatic_failure_reasons=tuple(failures),
    )


def baseline_acceptance_is_expected(
    acceptance: tuple[CommandResult, ...],
    markers: tuple[str, ...],
    expected_failure_count: int,
) -> bool:
    if (
        not acceptance
        or any(result.exit_code in {None, 0} for result in acceptance)
        or any(result.timed_out for result in acceptance)
    ):
        return False
    output = "\n".join(
        result.stdout + "\n" + result.stderr for result in acceptance
    )
    if not all(marker in output for marker in markers):
        return False
    if re.search(
        r"(?:ERROR collecting|Unhandled Error|Failed to load|\b\d+ errors?\b)",
        output,
        flags=re.IGNORECASE,
    ):
        return False
    counts = [
        int(match.group(1))
        for match in re.finditer(
            r"(?:\bTests\s+)?\b(\d+)\s+failed\b",
            output,
            flags=re.IGNORECASE,
        )
    ]
    return bool(counts) and max(counts) == expected_failure_count


def _run_commands(
    raw_commands: object,
    workspace: Workspace,
    timeout_seconds: int,
) -> tuple[CommandResult, ...]:
    if not isinstance(raw_commands, list):
        raise ValueError("oracle command group must be an array")
    return tuple(
        run_process(
            _expand_command(command, workspace.root),
            workspace.root,
            timeout_seconds,
        )
        for command in raw_commands
    )


def _expand_command(raw_command: object, workspace_root: Path) -> list[str]:
    if not isinstance(raw_command, list) or not all(
        isinstance(argument, str) for argument in raw_command
    ):
        raise ValueError("oracle command must be an array of strings")
    python = _workspace_python(workspace_root)
    return [
        str(python) if argument == "{python}" else argument
        for argument in raw_command
    ]


def _workspace_python(workspace_root: Path) -> Path:
    windows = workspace_root / ".venv" / "Scripts" / "python.exe"
    return windows if windows.exists() else workspace_root / ".venv" / "bin" / "python"
