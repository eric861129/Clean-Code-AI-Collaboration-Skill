from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from evals.harness.models import DiffEvidence, Rename, Workspace
from evals.harness.process import run_process

SUBJECT_REPORT_PATHSPEC = ":(exclude).benchmark-subject-report.json"
DIFF_PATHS = (".", SUBJECT_REPORT_PATHSPEC)


def classify_paths(
    changed: Iterable[str],
    renamed: Iterable[Rename],
    allowed_exact: set[str],
    allowed_patterns: tuple[str, ...],
) -> DiffEvidence:
    changed_paths = tuple(sorted({_normalize_path(path) for path in changed}))
    renamed_paths = tuple(
        Rename(_normalize_path(item.source), _normalize_path(item.destination))
        for item in renamed
    )
    paths_to_check = set(changed_paths)
    for item in renamed_paths:
        paths_to_check.add(item.source)
        paths_to_check.add(item.destination)
    outside = tuple(
        sorted(
            path
            for path in paths_to_check
            if not _is_allowed(path, allowed_exact, allowed_patterns)
        )
    )
    return DiffEvidence(
        diff="",
        diff_sha256=hashlib.sha256(b"").hexdigest(),
        changed_paths=changed_paths,
        renamed_paths=renamed_paths,
        outside_boundary=outside,
    )


def capture_diff(
    workspace: Workspace,
    scenario: dict[str, object],
) -> DiffEvidence:
    _run_git(["add", "-N", "--", "."], workspace)
    # 不依賴 .gitignore：Subject report 永遠不屬於 Candidate Diff。
    diff = _run_git(
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
    name_status = _run_git(
        [
            "diff",
            "--name-status",
            "-M",
            workspace.baseline_commit,
            "--",
            *DIFF_PATHS,
        ],
        workspace,
    )
    changed: list[str] = []
    renamed: list[Rename] = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        if parts[0].startswith("R") and len(parts) == 3:
            renamed.append(Rename(parts[1], parts[2]))
        elif len(parts) >= 2:
            changed.append(parts[-1])

    classified = classify_paths(
        changed=changed,
        renamed=renamed,
        allowed_exact={str(path) for path in scenario["allowed_diff"]},
        allowed_patterns=tuple(
            str(pattern) for pattern in scenario["allowed_diff_patterns"]
        ),
    )
    return DiffEvidence(
        diff=diff,
        diff_sha256=hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        changed_paths=classified.changed_paths,
        renamed_paths=classified.renamed_paths,
        outside_boundary=classified.outside_boundary,
    )


def _run_git(args: list[str], workspace: Workspace) -> str:
    result = run_process(["git", *args], workspace.root, timeout_seconds=30)
    if result.exit_code != 0:
        raise RuntimeError(f"git diff command failed: {args}\n{result.stderr}")
    return result.stdout


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    return normalized[2:] if normalized.startswith("./") else normalized


def _is_allowed(
    path: str,
    allowed_exact: set[str],
    allowed_patterns: tuple[str, ...],
) -> bool:
    normalized_exact = {_normalize_path(item) for item in allowed_exact}
    return path in normalized_exact or any(
        re.fullmatch(pattern, path) is not None for pattern in allowed_patterns
    )
