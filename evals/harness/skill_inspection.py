"""新版協定共用的唯讀查閱與完整診斷，不修改 Subject 的原始紀錄。"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from evals.harness.models import SubjectDispatch

POLICY = "required-subset/v1"


def resolve_skill_file(workspace: Path, skill_root: str | None, value: str) -> Path:
    """只解析指定 Skill 內的正規 POSIX 檔案，包含實際連結邊界檢查。"""
    path = PurePosixPath(value)
    if (not skill_root or not value or "\\" in value or ":" in value
            or path.is_absolute() or PureWindowsPath(value).drive
            or ".." in path.parts or value != path.as_posix()
            or PurePosixPath(skill_root) not in path.parents):
        raise ValueError("invalid Skill path")
    resolved_workspace = workspace.resolve()
    root = (workspace / skill_root).resolve()
    target = (workspace / path).resolve()
    if (not root.is_relative_to(resolved_workspace)
            or not target.is_relative_to(root) or not target.is_file()):
        raise ValueError("invalid Skill path")
    return target


def inspect_skill(dispatch: SubjectDispatch, paths: list[str]) -> list[dict[str, str]]:
    """驗證整批指定路徑後才讀取；不補 required、不建立成功報告。"""
    if dispatch.inspection_policy != POLICY:
        raise ValueError("inspect-skill requires a v5 inspection policy")
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("inspect-skill requires unique explicit paths")
    targets = []
    for path in paths:
        if path not in dispatch.allowed_skill_inspection_paths:
            raise ValueError("Skill file is not permitted by the fixed Arm")
        targets.append(resolve_skill_file(dispatch.workspace.root, dispatch.skill_root, path))
    records = []
    for path, target in zip(paths, targets, strict=True):
        content = target.read_bytes()
        records.append({"path": path, "sha256": hashlib.sha256(content).hexdigest(), "content": content.decode("utf-8")})
    return records


def inspection_diagnostics(report: dict[str, object], dispatch: SubjectDispatch) -> list[dict[str, str]]:
    """收集全部證據違規，公開摘要不包含非法路徑或主機資訊。"""
    diagnostics: set[tuple[str, str]] = set()

    def add(code: str, path: str = "") -> None:
        diagnostics.add((code, path))

    claims: dict[str, list[object]] = {}
    raw = report.get("skill_inspection_claims")
    if not isinstance(raw, list):
        add("invalid_skill_claim")
        raw = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"} or not isinstance(item.get("path"), str):
            add("invalid_skill_claim")
            continue
        path = item["path"]
        if path in claims:
            add("duplicate_skill_claim")
        claims.setdefault(path, []).append(item["sha256"])

    inspected_raw = report.get("files_inspected")
    if not isinstance(inspected_raw, list) or not all(isinstance(p, str) for p in inspected_raw):
        add("inspection_record_mismatch")
        inspected_raw = []
    inspected = {p for p in inspected_raw if p.startswith(".agents/skills/")}
    if len(inspected_raw) != len(set(inspected_raw)) or inspected != set(claims):
        add("inspection_record_mismatch")
    for path in sorted(set(claims) | inspected):
        try:
            target = resolve_skill_file(dispatch.workspace.root, dispatch.skill_root, path)
        except (ValueError, OSError):
            add("invalid_skill_path")
            continue
        if path not in dispatch.allowed_skill_inspection_paths:
            name = PurePosixPath(path).name
            code = "profile_contamination" if name.startswith(("language-", "framework-")) else "unexpected_skill_file"
            add(code, path)
        expected = hashlib.sha256(target.read_bytes()).hexdigest()
        for claimed in claims.get(path, []):
            if not isinstance(claimed, str) or re.fullmatch(r"[0-9a-f]{64}", claimed) is None or claimed != expected:
                add("skill_hash_mismatch", path)
    for missing in sorted(set(dispatch.required_skill_inspection_paths) - (set(claims) & inspected)):
        add("missing_required_skill_file", missing)
    if report.get("applied_profiles") != list(dispatch.applied_profiles):
        add("applied_profiles_mismatch")
    return [{"code": code, **({"path": path} if path else {})} for code, path in sorted(diagnostics)]
