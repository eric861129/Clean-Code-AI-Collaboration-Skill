"""新 Campaign 的固定來源與跨平台位元組驗證；不改變歷史 Hash。"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


def _git(repository: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=repository, capture_output=True, timeout=30,
    )
    if result.returncode:
        raise ValueError(f"provenance Git command failed: {args[0]}")
    return result.stdout


def _input_paths(repository: Path, revision: str, manifest: str) -> list[str]:
    tracked = _git(repository, "ls-tree", "-r", "--name-only", "-z", revision)
    return _select_inputs(tracked.decode("utf-8").split("\0"), manifest)


def _select_inputs(paths: list[str], manifest: str) -> list[str]:
    selected = {
        path for path in paths
        if (
            (path.startswith("evals/harness/") and path.endswith(".py"))
            or (path.startswith("evals/rubrics/") and path.endswith(".md"))
            or (path.startswith("evals/") and path.endswith(".schema.json"))
            or path in {manifest, "evals/v040_strategy_full_run.py",
                        "requirements-dev.txt", ".gitattributes"}
        )
    }
    if manifest not in selected:
        raise ValueError("execution manifest must exist in the pinned commit")
    return sorted(selected)


def build_execution_provenance(
    repository: Path,
    manifest_path: Path,
    revision: str | None = None,
    *,
    require_clean: bool = True,
) -> dict[str, Any]:
    """凍結明確輸入清單及其 Git 版本，Manifest 不須內嵌自己的 Commit。"""
    repository = repository.resolve()
    manifest = manifest_path.resolve().relative_to(repository).as_posix()
    if revision is not None and re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("execution revision must be a full commit SHA")
    if require_clean and _git(repository, "status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("execution freeze requires a clean committed source")
    execution_commit = _git(
        repository, "rev-parse", "--verify", f"{revision or 'HEAD'}^{{commit}}",
    ).decode().strip()
    inputs = {
        path: hashlib.sha256(_git(repository, "cat-file", "blob", f"{execution_commit}:{path}")).hexdigest()
        for path in _input_paths(repository, execution_commit, manifest)
    }
    result = {
        "schema_version": "execution-provenance/v1",
        "execution_commit": execution_commit,
        "manifest_path": manifest,
        "input_sha256": inputs,
        "inputs_sha256": hashlib.sha256(json.dumps(
            inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest(),
    }
    verify_execution_provenance(repository, result)
    return result


def verify_execution_provenance(repository: Path, receipt: dict[str, Any]) -> None:
    """對原凍結 Commit 重驗目前執行輸入；結果發布 Commit 不改變來源身分。"""
    revision = receipt["execution_commit"]
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("execution revision must be a full commit SHA")
    manifest = receipt["manifest_path"]
    paths = _input_paths(repository, revision, manifest)
    current = _git(repository, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if _select_inputs(current.decode("utf-8").split("\0"), manifest) != paths:
        raise ValueError("source input list drift")
    expected = {
        path: hashlib.sha256(_git(repository, "cat-file", "blob", f"{revision}:{path}")).hexdigest()
        for path in paths
    }
    if receipt["input_sha256"] != expected:
        raise ValueError("execution receipt does not match pinned Git inputs")
    digest = hashlib.sha256(json.dumps(
        expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    if receipt["inputs_sha256"] != digest:
        raise ValueError("execution receipt input digest mismatch")
    for path, expected_hash in expected.items():
        source = repository / path
        if (
            not source.is_file() or source.is_symlink()
            or not source.resolve().is_relative_to(repository.resolve())
        ):
            raise ValueError(f"source input drift: {path}")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError(f"source input drift: {path}")
        _require_lf_text(data, path)


def _tree_digest(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(files[path])
        digest.update(b"\0")
    return digest.hexdigest()


def _require_lf_text(data: bytes, path: str) -> None:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"input must use UTF-8 LF bytes: {path}") from error
    if b"\r" in data or b"\0" in data or data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"input must use UTF-8 LF bytes: {path}")


def canonical_tree_sha256(root: Path) -> str:
    """以 POSIX、大小寫敏感順序計算實際檔案位元組，不隱藏換行差異。"""
    if not root.is_dir() or root.is_symlink():
        raise ValueError("canonical tree root must be a real directory")
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("canonical tree may not contain symlinks")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            _require_lf_text(data, relative)
            files[relative] = data
    return _tree_digest(files)


def verify_staged_tree(
    repository: Path,
    revision: str,
    subtree: str,
    staged_root: Path,
    *,
    allow_extra: bool = False,
) -> dict[str, Any]:
    """核對匯出的 Fixture／Skill／Evaluator 與固定 Git Blob 完全相符。"""
    entries = _git(repository, "ls-tree", "-r", "--name-only", "-z", f"{revision}:{subtree}")
    files = {
        path: _git(repository, "cat-file", "blob", f"{revision}:{subtree}/{path}")
        for path in sorted(entries.decode("utf-8").rstrip("\0").split("\0")) if path
    }
    if not allow_extra:
        staged_files = {
            path.relative_to(staged_root).as_posix()
            for path in staged_root.rglob("*") if path.is_file() or path.is_symlink()
        }
        if staged_files != set(files):
            raise ValueError(f"staged file list mismatch: {subtree}")
    for path, blob in files.items():
        _require_lf_text(blob, f"{subtree}/{path}")
        staged = staged_root / path
        if (
            not staged.is_file() or staged.is_symlink()
            or not staged.resolve().is_relative_to(staged_root.resolve())
            or staged.read_bytes() != blob
        ):
            raise ValueError(f"staged byte mismatch: {subtree}/{path}")
    return {
        "tree_sha256": _tree_digest(files),
        "file_sha256": {path: hashlib.sha256(blob).hexdigest() for path, blob in files.items()},
    }
