from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path
from uuid import uuid4

from evals.harness.models import (
    ArmDefinition,
    BenchmarkManifest,
    HarnessPaths,
    RunSlot,
    Workspace,
)
from evals.harness.process import run_process
from evals.harness.execution_provenance import verify_staged_tree


def build_workspace(
    slot: RunSlot,
    manifest: BenchmarkManifest,
    paths: HarnessPaths,
) -> Workspace:
    scenario = _scenario_for(manifest, slot.scenario_id)
    arm = _arm_for(manifest, slot.arm_id)
    canonical_staging = manifest.subject_executor.get("protocol_version") == "desktop-subject-v5"
    staging_provenance: dict[str, object] = {}
    workspace_root = paths.runs_root / "workspaces" / slot.run_id
    artifact_dir = paths.runs_root / "artifacts" / slot.run_id
    if workspace_root.exists() or artifact_dir.exists():
        raise FileExistsError(f"run workspace already exists: {slot.run_id}")

    _verify_revision(
        paths.fixture_clone,
        manifest.fixture_commit,
        manifest.fixture_commit,
        manifest.fixture_timeout_seconds,
    )
    _verify_revision(
        paths.skill_repository,
        manifest.skill_tag,
        manifest.skill_commit,
        manifest.fixture_timeout_seconds,
    )

    workspace_root.mkdir(parents=True)
    artifact_dir.mkdir(parents=True)
    _export_tree(
        repository=paths.fixture_clone,
        treeish=f"{manifest.fixture_commit}:{scenario['fixture_path']}",
        destination=workspace_root,
        cache_root=paths.runs_root / "cache" / "archives",
        timeout_seconds=manifest.fixture_timeout_seconds,
        canonical_lf=canonical_staging,
    )
    if canonical_staging:
        staging_provenance["fixture"] = verify_staged_tree(
            paths.fixture_clone, manifest.fixture_commit,
            str(scenario["fixture_path"]), workspace_root,
        )
    _write_workspace_gitignore(workspace_root, canonical_lf=canonical_staging)

    if arm.skill is not None:
        skill_root = workspace_root / ".agents" / "skills" / arm.skill
        skill_root.mkdir(parents=True)
        _export_tree(
            repository=paths.skill_repository,
            treeish=f"{manifest.skill_commit}:{arm.skill}",
            destination=skill_root,
            cache_root=paths.runs_root / "cache" / "archives",
            timeout_seconds=manifest.fixture_timeout_seconds,
            canonical_lf=canonical_staging,
        )
        if canonical_staging:
            staging_provenance["skill"] = verify_staged_tree(
                paths.skill_repository, manifest.skill_commit, arm.skill, skill_root,
            )

    _install_dependencies(
        workspace_root,
        str(scenario["language"]),
        paths.runs_root,
        manifest.fixture_timeout_seconds,
    )
    if canonical_staging:
        # 安裝依賴後再驗證原始檔案，避免把安裝程序的修改當成固定基線。
        verify_staged_tree(
            paths.fixture_clone, manifest.fixture_commit,
            str(scenario["fixture_path"]), workspace_root, allow_extra=True,
        )
        if arm.skill is not None:
            verify_staged_tree(
                paths.skill_repository, manifest.skill_commit, arm.skill, skill_root,
            )
    _run_checked(
        ["git", "init", "--initial-branch=main"],
        workspace_root,
        manifest.fixture_timeout_seconds,
    )
    if canonical_staging:
        _run_checked(
            ["git", "config", "core.autocrlf", "false"],
            workspace_root, manifest.fixture_timeout_seconds,
        )
    _run_checked(
        ["git", "config", "user.name", "Benchmark Runner"],
        workspace_root,
        manifest.fixture_timeout_seconds,
    )
    _run_checked(
        ["git", "config", "user.email", "benchmark@example.invalid"],
        workspace_root,
        manifest.fixture_timeout_seconds,
    )
    _run_checked(
        ["git", "add", "-A"],
        workspace_root,
        manifest.fixture_timeout_seconds,
    )
    _run_checked(
        ["git", "commit", "-m", "benchmark baseline"],
        workspace_root,
        manifest.fixture_timeout_seconds,
    )
    baseline_commit = _run_checked(
        ["git", "rev-parse", "HEAD"],
        workspace_root,
        manifest.fixture_timeout_seconds,
    ).stdout.strip()
    status = _run_checked(
        ["git", "status", "--short"],
        workspace_root,
        manifest.fixture_timeout_seconds,
    )
    if status.stdout.strip():
        raise RuntimeError(f"baseline workspace is not clean: {status.stdout}")
    if canonical_staging:
        (artifact_dir / "staging-provenance.json").write_text(
            json.dumps({
                "schema_version": "staging-provenance/v1",
                "fixture_commit": manifest.fixture_commit,
                "skill_commit": manifest.skill_commit,
                "baseline_commit": baseline_commit,
                **staging_provenance,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
    return Workspace(workspace_root, artifact_dir, baseline_commit)


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


def _arm_for(manifest: BenchmarkManifest, arm_id: str) -> ArmDefinition:
    try:
        return next(arm for arm in manifest.arms if arm.id == arm_id)
    except StopIteration as error:
        raise ValueError(f"unknown arm: {arm_id}") from error


def _verify_revision(
    repository: Path,
    treeish: str,
    expected_commit: str,
    timeout_seconds: int,
) -> None:
    resolved = _run_checked(
        ["git", "rev-parse", f"{treeish}^{{}}"],
        repository,
        timeout_seconds,
    ).stdout.strip()
    if resolved != expected_commit:
        raise ValueError(
            f"revision mismatch for {treeish}: expected {expected_commit}, "
            f"got {resolved}"
        )


def _export_tree(
    repository: Path,
    treeish: str,
    destination: Path,
    cache_root: Path,
    timeout_seconds: int,
    *,
    canonical_lf: bool = False,
) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    archive = cache_root / f"{uuid4().hex}.tar"
    try:
        # 子樹匯出不繼承根目錄屬性；v5 明確停用 Host 的 CRLF 轉換。
        git = ["git", "-c", "core.autocrlf=false"] if canonical_lf else ["git"]
        _run_checked(
            [*git, "archive", "--format=tar", f"--output={archive}", treeish],
            repository,
            timeout_seconds,
        )
        with tarfile.open(archive) as source:
            source.extractall(destination, filter="data")
    finally:
        archive.unlink(missing_ok=True)


def _write_workspace_gitignore(workspace_root: Path, *, canonical_lf: bool = False) -> None:
    (workspace_root / ".gitignore").write_text(
        "node_modules/\n"
        ".venv/\n"
        ".pytest_cache/\n"
        ".ruff_cache/\n"
        "__pycache__/\n"
        "*.pyc\n"
        "bin/\n"
        "obj/\n"
        ".benchmark-oracle/\n"
        ".benchmark-subject-report.json\n",
        encoding="utf-8",
        newline="\n" if canonical_lf else None,
    )


def _install_dependencies(
    workspace_root: Path,
    language: str,
    runs_root: Path,
    timeout_seconds: int,
) -> None:
    if language in {"typescript", "typescript-react"}:
        npm_cache = runs_root / "cache" / "npm"
        npm_cache.mkdir(parents=True, exist_ok=True)
        _run_checked(
            [
                "npm",
                "ci",
                "--cache",
                str(npm_cache),
                "--prefer-offline",
                "--no-audit",
                "--no-fund",
            ],
            workspace_root,
            timeout_seconds,
        )
        return

    if language == "csharp":
        dotnet = shutil.which("dotnet")
        if dotnet is None:
            raise ValueError("required .NET SDK executable is unavailable")
        public_projects = sorted(workspace_root.glob("tests/**/*.csproj"))
        if len(public_projects) != 1:
            raise ValueError("C# fixture must contain exactly one public test project")
        project = public_projects[0].relative_to(workspace_root).as_posix()
        _run_checked(
            [dotnet, "restore", project, "--locked-mode", "--nologo"],
            workspace_root,
            timeout_seconds,
        )
        return

    if language != "python-fastapi":
        raise ValueError(f"unsupported fixture language: {language}")
    lockfile = workspace_root / "requirements.lock"
    lock_digest = hashlib.sha256(lockfile.read_bytes()).hexdigest()
    wheel_cache = runs_root / "cache" / "pip" / lock_digest
    wheel_cache.mkdir(parents=True, exist_ok=True)
    _run_checked(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--disable-pip-version-check",
            "-r",
            str(lockfile),
            "-d",
            str(wheel_cache),
        ],
        workspace_root,
        timeout_seconds,
    )
    _run_checked(
        [sys.executable, "-m", "venv", ".venv"],
        workspace_root,
        timeout_seconds,
    )
    python = _workspace_python(workspace_root)
    _run_checked(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-index",
            "--find-links",
            str(wheel_cache),
            "-r",
            str(lockfile),
        ],
        workspace_root,
        timeout_seconds,
    )


def _workspace_python(workspace_root: Path) -> Path:
    windows = workspace_root / ".venv" / "Scripts" / "python.exe"
    return windows if windows.exists() else workspace_root / ".venv" / "bin" / "python"


def _run_checked(
    args: list[str], cwd: Path, timeout_seconds: int
):
    result = run_process(args, cwd, timeout_seconds)
    if result.exit_code != 0:
        raise RuntimeError(
            f"command failed ({result.classification}): {args}\n{result.stderr}"
        )
    return result
