from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from evals.harness.models import CommandResult


def run_process(
    args: list[str],
    cwd: Path,
    timeout_seconds: int,
    stdin: str | None = None,
    attempt: int = 1,
) -> CommandResult:
    resolved_args = list(args)
    executable = shutil.which(resolved_args[0])
    if executable is not None:
        resolved_args[0] = executable

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            resolved_args,
            cwd=cwd,
            input=stdin,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            shell=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        return CommandResult(
            args=tuple(args),
            exit_code=None,
            stdout=_timeout_output(error.stdout),
            stderr=_timeout_output(error.stderr),
            elapsed_seconds=time.perf_counter() - started,
            timed_out=True,
            classification="timeout",
            attempt=attempt,
        )
    except OSError as error:
        return CommandResult(
            args=tuple(args),
            exit_code=None,
            stdout="",
            stderr=str(error),
            elapsed_seconds=time.perf_counter() - started,
            timed_out=False,
            classification="launch_error",
            attempt=attempt,
        )

    return CommandResult(
        args=tuple(args),
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        elapsed_seconds=time.perf_counter() - started,
        timed_out=False,
        classification="success" if completed.returncode == 0 else "nonzero_exit",
        attempt=attempt,
    )


def _timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
