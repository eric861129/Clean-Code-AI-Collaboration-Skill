# Composable Language and Framework Profiles v0.5.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將單一 `clean-code-ai-collaboration` Core Skill 升級為可依 Changed Module 組合 C#、Python、TypeScript 與 React Profile 的 `v0.5.0`，並提供可驗證的 Metadata、Routing、Generated Docs 與未發布 C# Specialist Package。

**Architecture:** Profile YAML 是維護、CI 與 Packaging 的 Registry；Consumer Runtime 只讀取由 Registry 產生的 Markdown Runtime Profile Index，再按 Changed Module 載入必要 Reference。Core 授權、風險路徑與輸出契約維持單一來源；Packager 只從已驗證來源建立可重現、可追蹤且不覆寫既有目錄的 Specialist Package。

**Tech Stack:** Agent Skills specification、Markdown、YAML、JSON Schema Draft 2020-12、Python 3.12 `unittest`、PyYAML 6.0.3、jsonschema 4.26.0、`agentskills` validator、GitHub Actions、Git。

**Spec:** `docs/superpowers/specs/2026-09-04-composable-language-framework-profile-architecture-design.md`

## Global Constraints

- 執行本計畫前，先用 `superpowers:using-git-worktrees` 從本機 `main` 建立 `codex/v0.5.0-composable-profiles`，Worktree 放在 Repository 同層的 `Clean-Code-AI-Collaboration-Skill-v0.5.0`；不得把個人絕對路徑寫入公共文件。
- 建立 Python 3.12 的 Worktree-local `.venv`；只從 `requirements-dev.txt` 安裝精確 Pin 的 `skills-ref==0.1.1`、`PyYAML==6.0.3`、`jsonschema==4.26.0`，不得寫入 System Python，也不得由 Repository Script 自動安裝。
- Preflight 必須先讓 `test_published_result_replays_from_public_receipts` 通過；不得改寫 `evals/results/v0.4.0-strategy-full-run.json`、`evals/manifests/v0.4.0-strategy-full-run.json` 或任何既有 Receipt。
- Profile Schema 使用 JSON Schema Draft 2020-12；根節點與結構化子物件都設 `additionalProperties: false`。
- Catalog 順序固定為 `csharp`、`python`、`typescript`、`react`、`go`、`rust`、`java`、`vue`；M0-A 全部為 `planned`，只有在完整 Reference 與 Tests 同一步完成時才能切換為 `experimental`。
- Consumer Runtime 不解析 YAML；`SKILL.md` 只加入 `profile-selection.md` 路由，Body 必須維持既有 525-word Contract。
- Profile Reference 使用英文且以約 1,500 個英文單字為目標上限；SPEC、`CONTEXT.md`、README 與 Authoring Guide 使用台灣繁體中文並保留正式英文術語。
- `requires` 傳遞展開、`recommends` 只提示、`conflicts` 必須雙向；無法安全組合時回到 Core Only，關鍵行為差異則 `blocked`。
- Validator Read-only；Generator 只修改兩個唯一 Marker Region；Packager 只寫入執行開始時不存在的明確 Output Directory，失敗時逐檔清理本次建立內容並以非遞迴 `rmdir()` 移除空目錄。
- Packaging Tool 不存取網路、不安裝依賴、不 Commit／Tag／Push／Release，也不修改 Consumer Repository。
- `dist/` 與 `.venv/` 必須 Git ignored；`v0.5.0` 只生成 `dist/clean-code-ai-csharp/`，不建立 ZIP、不 Commit、不公開發布。
- 每個 Task 都先確認 RED 的失敗原因，再完成最小 GREEN、相關回歸、`git diff --check` 與 Conventional Commit。
- 本計畫只授權本機 Worktree、Branch、Commits、Tests 與 Review；不得 Push、建立 PR、Merge、Tag、GitHub Release、執行 M2 Pilot 或實作 M3 References。

## File Map

| Path | Responsibility |
| --- | --- |
| `evals/v040_strategy_full_run.py` | 以 Published Skill Version 對應 Tag 的 Git Blob Bytes 重播歷史 Result |
| `tests/test_v040_strategy_full_run.py` | Preflight 歷史 Revision、EOL 與 Worktree-independent Regression |
| `requirements-dev.txt` | Python 驗證工具的精確 Direct Dependency Pins |
| `.gitignore` | 排除 `.venv/`、`dist/` 與既有暫存輸出 |
| `profiles/profile.schema.json` | Profile Metadata 的 Draft 2020-12 單檔結構契約 |
| `profiles/catalog.yaml` | 有序 Profile Metadata 相對路徑清單 |
| `profiles/*.yaml` | 八個 Profile 各自的狀態、Detection、Composition、Ownership 與 Evidence 真實來源 |
| `scripts/__init__.py` | 讓三個 Script 的核心函式可由 `unittest` 直接 Import |
| `scripts/validate_profiles.py` | Read-only Schema／Catalog／Cross-file Validator 與 Routing Fixture Oracle |
| `scripts/generate_profile_matrix.py` | 只更新 README Matrix 與 Runtime Profile Index Marker Region |
| `scripts/package-manifest.schema.json` | Specialist Package Manifest 的獨立 Draft 2020-12 契約 |
| `scripts/build_skill_package.py` | Release／Worktree Source Reader、Profile Composition、Package Builder 與安全清理 |
| `clean-code-ai-collaboration/SKILL.md` | 維持精簡的 Core Entry Point 與 Profile Selection 入口 |
| `clean-code-ai-collaboration/references/profile-selection.md` | Agent Runtime 的 Changed Module、Detection、Composition 與輸出路由契約 |
| `clean-code-ai-collaboration/references/language-csharp.md` | C#／.NET 語言與標準 Runtime 語意風險 |
| `clean-code-ai-collaboration/references/language-python.md` | Python 語言與標準 Runtime 語意風險 |
| `clean-code-ai-collaboration/references/language-typescript.md` | TypeScript 編譯器與型別語意風險 |
| `clean-code-ai-collaboration/references/framework-react.md` | Renderer-neutral React 與條件式 React DOM 行為風險 |
| `README.md` | 使用方式、成熟度、Generated Profile Matrix 與 Sample Package 限制 |
| `docs/profile-authoring.md` | Planned 到 Experimental 的原子貢獻流程與 Reviewer Checklist |
| `tests/test_profile_contract.py` | Schema、Catalog、Composition、Evidence、Reference 與 CLI Contract Tests |
| `tests/test_profile_routing.py` | Changed Module、Explicit Override、Planned／Conflict 與 Polyglot Fixtures |
| `tests/test_profile_packaging.py` | Source Mode、Composition、Manifest、可重現性與安全失敗測試 |
| `tests/fixtures/profile-routing/` | 不安裝、不 Build 的最小 Routing Catalog 與案例 |
| `tests/fixtures/profile-packaging/csharp/` | 跨平台 Canonical Manifest／Digest Fixture |
| `tests/test_skill_contract.py` | Core Reference、版本、篇幅、README 與 Workflow 整合契約 |
| `.github/workflows/validate.yml` | Ubuntu／Windows Python 3.12 Matrix、Generated Drift 與 Package Validation |

---

### Task 1: Preflight—讓 v0.4.0 Public Result 從歷史 Git Blob 重播

**Files:**
- Modify: `tests/test_v040_strategy_full_run.py:1-370`
- Modify: `evals/v040_strategy_full_run.py:277-803`
- Do not modify: `evals/results/v0.4.0-strategy-full-run.json`
- Do not modify: `evals/manifests/v0.4.0-strategy-full-run.json`

**Interfaces:**
- Consumes: Published Result 的 `skill_version`、Repository Tag `v0.4.0`、既有 `file_sha256()` 與穩定大小寫不敏感 POSIX Path Order。
- Produces: `resolve_version_revision(repository_root: Path, skill_version: str) -> str`、`git_blob_bytes(repository_root: Path, revision: str, relative_path: str) -> bytes`、`git_tree_sha256(repository_root: Path, revision: str, relative_root: str) -> str`。

- [ ] **Step 1: 寫歷史 Blob 與 Worktree-independent RED Tests**

在 `tests/test_v040_strategy_full_run.py` Import 三個新函式，新增：

```python
def test_v040_git_blob_hash_reconstructs_published_skill_tree(self) -> None:
    revision = resolve_version_revision(ROOT, "0.4.0")

    self.assertEqual("d0b5282362c136d09311c2fedc5a5692aa99ea90", revision)
    self.assertEqual(
        "4c1d6eaf19f321e6ba2e0360aede7077c6853688f5d4c7f086c0178209b64135",
        git_tree_sha256(ROOT, revision, "clean-code-ai-collaboration"),
    )

def test_v040_historical_replay_ignores_skill_source_worktree(self) -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        unrelated_skill = Path(temporary_directory) / "skill"
        unrelated_skill.mkdir()
        (unrelated_skill / "SKILL.md").write_text("changed", encoding="utf-8")
        with mock.patch(
            "evals.v040_strategy_full_run.SKILL_SOURCE",
            unrelated_skill,
        ):
            verification = verify_public_result(
                ROOT / "evals" / "results" / "v0.4.0-strategy-full-run.json"
            )

    self.assertEqual({"status": "passed", "failures": []}, verification)

def test_v040_git_reader_rejects_unsafe_revision_and_paths(self) -> None:
    revision = resolve_version_revision(ROOT, "0.4.0")
    for unsafe_revision in {"--help", "deadbeef"}:
        with self.subTest(revision=unsafe_revision):
            with self.assertRaisesRegex(ValueError, "full lowercase commit SHA"):
                git_blob_bytes(ROOT, unsafe_revision, "clean-code-ai-collaboration/SKILL.md")
    for unsafe_path in {"/absolute/SKILL.md", "../SKILL.md"}:
        with self.subTest(path=unsafe_path):
            with self.assertRaisesRegex(ValueError, "repository-relative"):
                git_blob_bytes(ROOT, revision, unsafe_path)
            with self.assertRaisesRegex(ValueError, "repository-relative"):
                git_tree_sha256(ROOT, revision, unsafe_path)
```

- [ ] **Step 2: 執行 RED，確認缺的是歷史 Git Reader**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_v040_strategy_full_run.V040StrategyFullRunTests.test_v040_git_blob_hash_reconstructs_published_skill_tree `
  tests.test_v040_strategy_full_run.V040StrategyFullRunTests.test_v040_historical_replay_ignores_skill_source_worktree `
  tests.test_v040_strategy_full_run.V040StrategyFullRunTests.test_v040_git_reader_rejects_unsafe_revision_and_paths `
  tests.test_v040_strategy_full_run.V040StrategyFullRunTests.test_published_result_replays_from_public_receipts `
  -v
```

Expected: ImportError 或新 Hash Tests FAIL，且既有 Public Receipt Test 仍因目前 Worktree Skill Hash 不同而 FAIL；不能修改 Expected Hash 讓它通過。Test File 同步加入 `from unittest import mock`。

- [ ] **Step 3: 實作只讀 Git Blob Helpers**

在 `evals/v040_strategy_full_run.py` 加入：

```python
def _git_bytes(repository_root: Path, arguments: list[str]) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git command failed: {message}")
    return completed.stdout


def resolve_version_revision(repository_root: Path, skill_version: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", skill_version):
        raise ValueError("skill version must be a semantic version")
    revision = _git_bytes(
        repository_root,
        ["rev-parse", "--verify", f"refs/tags/v{skill_version}^{{}}"],
    ).decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("skill version tag did not resolve to a commit")
    return revision


def git_blob_bytes(
    repository_root: Path,
    revision: str,
    relative_path: str,
) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision must be a full lowercase commit SHA")
    normalized = PurePosixPath(relative_path)
    if normalized.is_absolute() or not normalized.parts or ".." in normalized.parts:
        raise ValueError("git blob path must be repository-relative")
    return _git_bytes(repository_root, ["show", f"{revision}:{normalized.as_posix()}"])


def git_tree_sha256(
    repository_root: Path,
    revision: str,
    relative_root: str,
) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision must be a full lowercase commit SHA")
    normalized_root = PurePosixPath(relative_root)
    if normalized_root.is_absolute() or not normalized_root.parts or ".." in normalized_root.parts:
        raise ValueError("git tree path must be repository-relative")
    root = normalized_root.as_posix().rstrip("/")
    raw_paths = _git_bytes(
        repository_root,
        ["ls-tree", "-r", "--name-only", "-z", revision, "--", root],
    )
    paths = [value.decode("utf-8") for value in raw_paths.split(b"\0") if value]
    paths.sort(key=lambda value: (value.casefold(), value))
    digest = hashlib.sha256()
    for path in paths:
        relative_path = path.removeprefix(f"{root}/")
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(git_blob_bytes(repository_root, revision, path))
        digest.update(b"\0")
    return digest.hexdigest()
```

同時新增 `import subprocess` 與 `from pathlib import PurePosixPath`。不要 Checkout Tag、建立暫存 Worktree，或把 Git Blob 先寫入磁碟。

- [ ] **Step 4: 將 `verify_public_result()` 的固定證據改成歷史 Revision**

在讀取 Published Result 後，先計算：

```python
historical_revision = resolve_version_revision(ROOT, result["skill_version"])
historical_skill_file_sha256 = hashlib.sha256(
    git_blob_bytes(
        ROOT,
        historical_revision,
        "clean-code-ai-collaboration/SKILL.md",
    )
).hexdigest()
historical_skill_tree_sha256 = git_tree_sha256(
    ROOT,
    historical_revision,
    "clean-code-ai-collaboration",
)
historical_manifest_sha256 = hashlib.sha256(
    git_blob_bytes(
        ROOT,
        historical_revision,
        "evals/manifests/v0.4.0-strategy-full-run.json",
    )
).hexdigest()
historical_harness_sha256 = hashlib.sha256(
    git_blob_bytes(ROOT, historical_revision, "evals/v040_strategy_full_run.py")
).hexdigest()
```

讓 Root Metadata、Manifest／Harness Hash 與 Skill Arm 的 `expected_dispatch` 使用上述歷史值；Baseline Arm 維持 `None`。`build_prompt()`、Subject Result 與 Terminal Replay 規則不變。

- [ ] **Step 5: 執行 GREEN 與完整 Regression**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_v040_strategy_full_run -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q evals/harness evals/v040_strategy_full_run.py
git diff --check
```

Expected: 原有 102 項加上本 Task 新增的 3 項，共 105 項測試全部 PASS；Published Result、Manifest 與 Receipt 檔案沒有 Diff。

- [ ] **Step 6: Commit Preflight 修復**

```powershell
git add evals/v040_strategy_full_run.py tests/test_v040_strategy_full_run.py
git diff --cached --check
git diff --cached
git commit -m "fix(evals): replay v040 receipts from git blobs"
```

---

### Task 2: M0-A—建立 Profile Schema、Catalog、Planned Metadata 與 Validator

**Files:**
- Modify: `requirements-dev.txt`
- Modify: `.gitignore`
- Create: `scripts/__init__.py`
- Create: `scripts/validate_profiles.py`
- Create: `profiles/profile.schema.json`
- Create: `profiles/catalog.yaml`
- Create: `profiles/csharp.yaml`
- Create: `profiles/python.yaml`
- Create: `profiles/typescript.yaml`
- Create: `profiles/react.yaml`
- Create: `profiles/go.yaml`
- Create: `profiles/rust.yaml`
- Create: `profiles/java.yaml`
- Create: `profiles/vue.yaml`
- Create: `tests/test_profile_contract.py`

**Interfaces:**
- Consumes: `profiles/catalog.yaml` 的有序相對路徑與 `profiles/profile.schema.json`。
- Produces: `Diagnostic(path: str, field: str, code: str, message: str)`、`load_registry(source_root: Path) -> Sequence[dict[str, Any]]`、`validate_repository(source_root: Path) -> Sequence[Diagnostic]`、`main(argv: Sequence[str] | None = None) -> int`。

- [ ] **Step 1: Pin 開發相依並建立隔離環境**

將 `requirements-dev.txt` 固定為：

```text
skills-ref==0.1.1
PyYAML==6.0.3
jsonschema==4.26.0
```

在 `.gitignore` 保留既有規則並加入：

```gitignore
.venv/
dist/
```

Run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Expected: 安裝成功；`git status --short` 不顯示 `.venv/`。

- [ ] **Step 2: 寫 Schema、Catalog 與 Cross-file RED Tests**

在 `tests/test_profile_contract.py` 建立 `unittest.TestCase`，至少加入下列可執行契約：

```python
from pathlib import Path
import tempfile
import unittest

from scripts.validate_profiles import load_registry, main, validate_repository


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PROFILE_HEADINGS = (
    "## Use This Profile When",
    "## Repository Facts to Inspect",
    "## Version-Sensitive Facts",
    "## Language or Framework Semantic Risks",
    "## Clean Code Misapplications",
    "## Behavior and Boundary Contracts",
    "## Repository-Native Gate Discovery",
    "## When Another Option Fits Better",
    "## Common Agent Failure Modes",
    "## Stop and Escalation Conditions",
    "## Output Additions",
    "## Evidence Status",
)


class ProfileContractTests(unittest.TestCase):
    def test_catalog_has_the_fixed_v050_order(self) -> None:
        profiles = load_registry(ROOT)
        self.assertEqual(
            ["csharp", "python", "typescript", "react", "go", "rust", "java", "vue"],
            [profile["id"] for profile in profiles],
        )

    def test_initial_registry_is_valid_and_all_profiles_are_planned(self) -> None:
        self.assertEqual([], list(validate_repository(ROOT)))
        for profile in load_registry(ROOT):
            with self.subTest(profile=profile["id"]):
                self.assertEqual("planned", profile["status"])
                self.assertNotIn("reference", profile)
                self.assertEqual(["eric861129"], profile["ownership"]["maintainers"])
                self.assertEqual("not_started", profile["evidence"]["benchmark_status"])

    def test_validator_cli_is_read_only_and_returns_zero(self) -> None:
        before = {
            path.relative_to(ROOT).as_posix(): path.read_bytes()
            for path in (ROOT / "profiles").rglob("*")
            if path.is_file()
        }
        self.assertEqual(0, main(["--source-root", str(ROOT)]))
        after = {
            path.relative_to(ROOT).as_posix(): path.read_bytes()
            for path in (ROOT / "profiles").rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)
```

另以暫存 Source Root 寫入最小錯誤 Registry，測試 Unknown Field、重複 ID、缺 Maintainer、Planned 帶 Reference、Requires Cycle、不對稱 Conflict、Evidence Hash 不符、大小寫衝突都回傳 Exit Code `1`，且 Diagnostic 依 `path`、`field`、`code` 排序。再分別建立 Beta 與 Stable 測試資料，證明 Beta 至少需要一筆有效、公開且 `passed` 的 Pilot Result，Stable 至少需要一筆有效、公開且 `passed` 的 Full Run Result；`failed`、`no_difference`、`inconclusive` 都保留但不能當成成熟度依據。

- [ ] **Step 3: 執行 RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract -v
```

Expected: FAIL，原因是 `scripts.validate_profiles`、Schema 與 Catalog 尚不存在；不能是第三方套件 Import Error。

- [ ] **Step 4: 建立 Draft 2020-12 Profile Schema**

`profiles/profile.schema.json` 的 Root 必須要求：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/eric861129/Clean-Code-AI-Collaboration-Skill/profiles/profile.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version", "id", "kind", "display_name", "status",
    "suite_version", "detection", "routing", "composition",
    "ownership", "evidence"
  ]
}
```

補齊下列精確子契約：

- `schema_version` 固定 `"1.0"`；`id` 符合 `^[a-z][a-z0-9-]*$`；`kind` 為 `language|framework`；`status` 為 `planned|experimental|beta|stable|deprecated`；`suite_version` 固定 `"0.5.0"`。
- `reference` 是 Repository-relative `.md` Path；`planned` 必須沒有 `reference`，其餘狀態必須有。
- `detection` 必須包含 `owning_manifests`、`supporting_files`、`file_extensions`、`dependency_markers`、`supporting_dependencies`。Owning Item 只含 `pattern` 與 `boundary`，Boundary 為 `project|package|workspace`；所有 Array 設 `uniqueItems: true`。
- `routing` 只含 `scope: changed-module` 與非負整數 `load_order`。
- `composition` 只含 `requires`、`recommends`、`conflicts`，每個 ID 都符合 Profile ID Pattern 且不可重複。
- `ownership.maintainers` 至少一個非空字串。
- `evidence.benchmark_status` 為 `not_started|pilot_recorded|full_run_recorded`；`manifests` 是唯一 Repository-relative Path Array；`results` 每筆只含 `stage`、`outcome`、`path`、64 位小寫 Hex `sha256`、Boolean `public`。`stage` 只能是 `pilot|full_run`；`outcome` 只能是 `passed|failed|no_difference|inconclusive`。
- `deprecation` 只含必填 `reason` 與選填 `replacement`、`removal_version`；只有 `deprecated` 可以出現。

- [ ] **Step 5: 建立有序 Catalog 與八個 Planned Metadata**

`profiles/catalog.yaml` 固定為：

```yaml
schema_version: "1.0"
profiles:
  - csharp.yaml
  - python.yaml
  - typescript.yaml
  - react.yaml
  - go.yaml
  - rust.yaml
  - java.yaml
  - vue.yaml
```

八份 Metadata 都使用 `schema_version: "1.0"`、`status: planned`、`suite_version: "0.5.0"`、`scope: changed-module`、Maintainer `eric861129`、空 Composition／Evidence，且沒有 `reference`。Detection 與 Load Order 固定為：

| ID | Kind | Owning manifests | Supporting files | Extensions | Candidate dependencies | Supporting dependencies | Load order |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `csharp` | language | `*.csproj/project` | `*.sln`, `*.slnx`, `Directory.Build.props`, `Directory.Build.targets`, `global.json` | `.cs` | none | none | 100 |
| `python` | language | `pyproject.toml/project`, `setup.py/project`, `setup.cfg/project` | `requirements*.txt`, `Pipfile`, `poetry.lock`, `uv.lock` | `.py`, `.pyi` | none | none | 100 |
| `typescript` | language | `package.json/package`, `tsconfig.json/project`, `tsconfig.*.json/project` | none | `.ts`, `.tsx`, `.mts`, `.cts` | none | none | 100 |
| `react` | framework | `package.json/package` | none | `.jsx`, `.tsx` | `react` | `react-dom`, `react-native` | 200 |
| `go` | language | `go.mod/project` | `go.work` | `.go` | none | none | 100 |
| `rust` | language | `Cargo.toml/project` | `Cargo.lock` | `.rs` | none | none | 100 |
| `java` | language | `pom.xml/project`, `build.gradle/project`, `build.gradle.kts/project` | `settings.gradle`, `settings.gradle.kts` | `.java` | none | none | 100 |
| `vue` | framework | `package.json/package` | none | `.vue` | `vue` | none | 200 |

`react.composition.recommends` 固定為 `[typescript]`；其他 M0-A Composition Array 保持空白。

- [ ] **Step 6: 實作 Read-only Validator 與固定 CLI**

在 `scripts/validate_profiles.py` 使用 `yaml.safe_load()` 與 `Draft202012Validator.iter_errors()`。核心流程固定為：

```python
from dataclasses import dataclass, field as dataclass_field


@dataclass(frozen=True, order=True)
class Diagnostic:
    path: str
    field: str
    code: str
    message: str = dataclass_field(compare=False)
```

同檔案實作 `load_registry(source_root: Path) -> Sequence[dict[str, Any]]`、`validate_repository(source_root: Path) -> Sequence[Diagnostic]` 與 `main(argv: Sequence[str] | None = None) -> int`。`validate_repository()` 除 Schema 外必須檢查 Catalog Schema／順序／唯一性、Case-insensitive ID／Reference／Package Name、Reference 存在性、Composition 引用、Self-reference、Requires Cycle、Conflict 對稱、Dependency Marker 重複、Evidence Path／SHA-256／Maturity、Deprecation 條件。所有 Path 先解析並確認仍位於 Source Root；Diagnostic 最後用 Dataclass Order 排序。

CLI 只接受必要 `--source-root`。成功回傳 `0`；Contract Failure 每行輸出 `path:field:code: message` 並回傳 `1`；Argparse 用法錯誤維持 `2`。一般資料錯誤不得輸出 Traceback。

- [ ] **Step 7: 執行 GREEN、完整回歸與 CLI Gate**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract -v
.\.venv\Scripts\python.exe scripts/validate_profiles.py --source-root .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
```

Expected: 全部 PASS；八個 Profile 仍為 Planned；`clean-code-ai-collaboration/references/` 沒有新增空白 Profile Reference。

- [ ] **Step 8: Commit M0-A Structural Contract**

```powershell
git add .gitignore requirements-dev.txt profiles scripts/__init__.py scripts/validate_profiles.py tests/test_profile_contract.py
git diff --cached --check
git diff --cached
git commit -m "feat(profiles): add metadata registry contract"
```

---

### Task 3: M0-B—建立 Runtime Index、Generated Regions 與 Changed Module Routing

**Files:**
- Modify: `scripts/validate_profiles.py`
- Create: `scripts/generate_profile_matrix.py`
- Create: `clean-code-ai-collaboration/references/profile-selection.md`
- Modify: `clean-code-ai-collaboration/SKILL.md`
- Modify: `README.md`
- Modify: `tests/test_skill_contract.py`
- Modify: `tests/test_profile_contract.py`
- Create: `tests/test_profile_routing.py`
- Create: `tests/fixtures/profile-routing/catalog/`
- Create: `tests/fixtures/profile-routing/csharp/`
- Create: `tests/fixtures/profile-routing/python/`
- Create: `tests/fixtures/profile-routing/typescript-react/`
- Create: `tests/fixtures/profile-routing/javascript-react/`
- Create: `tests/fixtures/profile-routing/typescript-vue-planned/`
- Create: `tests/fixtures/profile-routing/polyglot/`
- Create: `tests/fixtures/profile-routing/root-sln-frontend/`
- Create: `tests/fixtures/profile-routing/core-only/`
- Create: `tests/fixtures/profile-routing/explicit-core-only/`
- Create: `tests/fixtures/profile-routing/conflict-blocked/`

**Interfaces:**
- Consumes: Task 2 的有效 `Profile Registry` 與 Technology-specific Detection Metadata。
- Produces: `route_changed_files(repository_root: Path, profiles: Sequence[Mapping[str, Any]], changed_files: Sequence[str], explicit_profiles: Sequence[str] = ()) -> dict[str, Any]`、`render_profile_matrix()`、`render_runtime_index()`、`synchronize_generated_regions(source_root: Path, check: bool) -> Sequence[Diagnostic]`。

- [ ] **Step 1: 寫 Routing 與 Generator RED Tests**

在 `tests/test_profile_routing.py` 逐一載入每個 Case 的 `expected.json`，呼叫 `route_changed_files()`，只比對結構化欄位。至少固定：

```python
def test_typescript_react_selects_language_then_framework(self) -> None:
    result = self.route_case("typescript-react")
    self.assertEqual("selected", result["outcome"])
    self.assertEqual(["typescript", "react"], result["modules"][0]["profiles"])

def test_javascript_react_does_not_invent_typescript(self) -> None:
    result = self.route_case("javascript-react")
    self.assertEqual(["react"], result["modules"][0]["profiles"])

def test_root_solution_does_not_pollute_frontend_module(self) -> None:
    result = self.route_case("root-sln-frontend")
    self.assertNotIn("csharp", result["modules"][0]["profiles"])

def test_conflict_with_critical_behavior_is_blocked(self) -> None:
    result = self.route_case("conflict-blocked")
    self.assertEqual("blocked", result["outcome"])
    self.assertIn("profile-conflict", result["modules"][0]["reason_codes"])
```

在 `tests/test_profile_contract.py` 新增 Marker 缺少／重複／交錯、一般模式只改 Region、`--check` 不寫檔且 Drift 回傳 `1` 的測試。

- [ ] **Step 2: 執行 RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_routing tests.test_profile_contract -v
```

Expected: FAIL，原因是 Routing Function、Generator、Runtime Index 與 Fixtures 尚不存在。

- [ ] **Step 3: 建立 Test-only Catalog 與最小 Routing Cases**

`tests/fixtures/profile-routing/catalog/` 複製必要 Schema 形狀，但將 C#、Python、TypeScript、React 設為 `experimental`，並提供包含全部 12 個固定章節、每章至少一個具體規則或例子的最小完整 Profile Reference；Vue 保持 `planned`。Conflict Case 使用兩個測試專用 Experimental Profile，雙向宣告 `conflicts`。

每個 Case 的 `expected.json` 固定包含：

```json
{
  "changed_files": ["frontend/src/App.tsx"],
  "explicit_profiles": [],
  "outcome": "selected",
  "modules": [
    {
      "root": "frontend",
      "profiles": ["typescript", "react"],
      "unavailable_profiles": [],
      "reason_codes": ["extension-match", "dependency-match"],
      "unknowns": []
    }
  ]
}
```

其他 Case 只調整真實 Changed Files、Manifest、Dependencies、Outcome 與 Reason Code；不得保存完整人類說明或安裝真正套件。

- [ ] **Step 4: 實作 Deterministic Routing Fixture Oracle**

在 `scripts/validate_profiles.py` 加入 `route_changed_files()`，固定執行順序：

1. 正規化並驗證 Changed File 為 Repository-relative POSIX Path。
2. 忽略未被明確列為 Changed File 的 Generated／Vendor／Build Output。
3. 對每個 Changed File 向上尋找 `owning_manifests`；先比距離，再比 `project > package > workspace`，最後比 Metadata 宣告順序。
4. 共享 Owner 的檔案分為同一 Module；無 Owner 時使用 Repository Policy 或 Root Fallback。
5. Language 由 Extension 建立 Candidate；Framework 必須命中 `dependency_markers`，並與 Changed File／Import／Manifest Diff 有關。
6. 移除 Planned、Deprecated、缺 Reference、不適用候選；Planned 記入 `unavailable_profiles`。
7. 套用合法 Explicit Profile／Core Only，再展開傳遞式 `requires`；`recommends` 不自動選取。
8. 驗證 Conflict、依 `load_order`、`kind`、`id` 排序；非關鍵失敗為 `core_only`，Critical Conflict 為 `blocked`。

Function 只服務 Fixture 與 Contract Test，不取代 Agent 對 Expected／Actual Diff、Repository Policy 與 Critical Unknown 的判斷。

- [ ] **Step 5: 建立 Runtime Profile Selection Reference**

`clean-code-ai-collaboration/references/profile-selection.md` 使用英文，包含以下實際章節與規則：

```markdown
# Profile Selection

## Use This Reference When
Use this reference for repository code changes where language or framework semantics may change the approach, behavior boundary, or validation.

## Changed Module Discovery
Group candidate changed files by their nearest owning manifest. Prefer the shortest directory distance, then project over package over workspace, then metadata order. Root evidence is supplemental.

## Candidate Detection
Language extensions are primary signals. Framework syntax is auxiliary; a framework candidate requires its dependency marker or explicit repository policy.

## Availability and Composition
Bundled means available, not automatically applied. Reject planned, deprecated, missing-reference, inapplicable, conflicted, or incomplete profiles. Expand requires transitively; treat recommends as advice only. Use Core Only when no applicable profile remains.

## Explicit Selection
Honor a valid explicit profile or Core Only request, but never use explicit selection to bypass availability, applicability, dependency, conflict, risk, or authorization gates.

## Stage Evidence
Planning uses Expected Diff. Implementation compares Expected and Actual Diff. Review uses Actual Diff first and reports deviations.

## Output Additions
Standard output records Profiles Applied and Profile Basis per Changed Module. Full Audit records references, facts, and unknowns in the existing sections. Core Only records Profiles Applied: none.

## Runtime Profile Index
<!-- runtime-profile-index:generated:start -->
<!-- runtime-profile-index:generated:end -->
```

- [ ] **Step 6: 實作唯一 Marker Generator 與 Read-only Check Mode**

`scripts/generate_profile_matrix.py` 固定 Marker：

```python
README_MARKERS = (
    "<!-- profile-matrix:generated:start -->",
    "<!-- profile-matrix:generated:end -->",
)
RUNTIME_MARKERS = (
    "<!-- runtime-profile-index:generated:start -->",
    "<!-- runtime-profile-index:generated:end -->",
)
```

同檔案提供 `replace_generated_region(document: str, markers: tuple[str, str], body: str) -> str`、`render_profile_matrix(profiles: Sequence[Mapping[str, Any]]) -> str`、`render_runtime_index(profiles: Sequence[Mapping[str, Any]]) -> str`、`synchronize_generated_regions(source_root: Path, check: bool) -> Sequence[Diagnostic]` 與 `main(argv: Sequence[str] | None = None) -> int`。

`render_profile_matrix()` 依 Catalog 順序輸出 `Profile | Kind | Status | Reference | Benchmark` 五欄；只有可用 Reference 產生相對連結，Planned 顯示 `Not available`。`render_runtime_index()` 依 Catalog 順序為每個 Profile 輸出 ID、Kind、Status／Availability、Load Order、Owning Manifests、Supporting Files、Extensions、Candidate Dependencies、Supporting Dependencies、Requires／Recommends／Conflicts 與 Evidence Status；空集合使用 `none`，不得省略 Owning／Supporting 角色差異，也不得輸出個人絕對路徑。

一般模式只有內容不同時才分別 `write_text(encoding="utf-8", newline="\n")`；`--check` 不呼叫任何 Write API。Marker Count 不是各一個、順序錯誤或交錯時回傳 `1`，不重寫整份文件。

Generator CLI 固定接受 `--source-root` 與選填 `--check`：同步完成或 Check 無漂移回傳 `0`；Marker Contract／Generated Drift 回傳 `1` 並輸出排序後 Diagnostic；Usage Error 回傳 `2`，一般 Contract Failure 不輸出 Traceback。

- [ ] **Step 7: 更新 Core Entry Point、README Marker 與動態 Reference Test**

將 `SKILL.md` Metadata Version 改為 `"0.5.0"`。把 Reference Routing 開頭縮為：

```markdown
Read only relevant references:

- Profile selection for repository code changes: `references/profile-selection.md`
- Agent legibility: `references/clean-code-for-agent-legibility.md`
```

實際寫入 `SKILL.md` 時，以上兩個 Path 都使用與既有 Entry 相同的 Markdown 相對連結格式。保留其他既有 Reference Links，刪除被上述兩行取代的舊引導句。執行篇幅測試，不得提高 525 上限。

在 README 的 Profile 說明段放入：

```markdown
<!-- profile-matrix:generated:start -->
<!-- profile-matrix:generated:end -->
```

將 `tests/test_skill_contract.py` 的固定 Reference Set 拆成 `CORE_REFERENCE_NAMES`（包含既有七份與 `profile-selection.md`）以及從 Catalog 讀取的非 Planned／非 Deprecated `reference`；仍逐一驗證檔案存在與 Entry Point／Runtime Index 可達，不得刪除完整性 Assertion。

- [ ] **Step 8: 產生兩個 Region 並執行 GREEN**

```powershell
.\.venv\Scripts\python.exe scripts/generate_profile_matrix.py --source-root .
.\.venv\Scripts\python.exe scripts/generate_profile_matrix.py --source-root . --check
.\.venv\Scripts\python.exe -m unittest tests.test_profile_routing tests.test_profile_contract tests.test_skill_contract -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\agentskills.exe validate clean-code-ai-collaboration
git diff --check
```

Expected: 全部 PASS；Runtime Index 與 README 顯示八個 Planned／Unavailable Profile；Skill Body 不超過 525 words。

- [ ] **Step 9: Commit M0-B Routing Contract**

```powershell
git add clean-code-ai-collaboration/SKILL.md clean-code-ai-collaboration/references/profile-selection.md README.md scripts/generate_profile_matrix.py scripts/validate_profiles.py tests/test_skill_contract.py tests/test_profile_contract.py tests/test_profile_routing.py tests/fixtures/profile-routing
git diff --cached --check
git diff --cached
git commit -m "feat(profiles): add changed-module routing contract"
```

---

### Task 4: M1-A—完成 C# Experimental Profile

**Files:**
- Modify: `profiles/csharp.yaml`
- Create: `clean-code-ai-collaboration/references/language-csharp.md`
- Modify: `tests/test_profile_contract.py`
- Modify: `tests/test_profile_routing.py`
- Modify: `README.md`
- Modify: `clean-code-ai-collaboration/references/profile-selection.md`

**Interfaces:**
- Consumes: Task 3 的 Profile Reference Contract、C# Detection Metadata 與 Generated Regions。
- Produces: `csharp.status: experimental`、`reference: clean-code-ai-collaboration/references/language-csharp.md`，以及 C# Routing／Semantic Contracts。

- [ ] **Step 1: 寫 C# Profile RED Tests**

在 `tests/test_profile_contract.py` 新增：

```python
def test_csharp_profile_has_complete_semantic_contract(self) -> None:
    content = (
        ROOT / "clean-code-ai-collaboration" / "references" / "language-csharp.md"
    ).read_text(encoding="utf-8")
    for heading in REQUIRED_PROFILE_HEADINGS:
        self.assertIn(heading, content)
    for term in {
        "Nullable", "CancellationToken", "IDisposable", "IAsyncDisposable",
        "deferred execution", "multiple enumeration", "equality", "DI lifetime",
        "TargetFramework", "LangVersion",
    }:
        with self.subTest(term=term):
            self.assertIn(term.lower(), content.lower())
    self.assertNotIn("ASP.NET Core is required", content)
```

再 Assert `csharp` 為 Experimental、Reference 存在、C# Fixture 選取 `csharp`，而其他七個真實 Profile 狀態不變。

- [ ] **Step 2: 執行 RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract tests.test_profile_routing -v
```

Expected: FAIL，原因是 C# Reference 尚不存在且 Metadata 仍為 Planned。

- [ ] **Step 3: 撰寫 C# Reference 並原子升級 Metadata**

`language-csharp.md` 必須完整使用固定 12 個 Profile Headings。內容明確要求先讀 `TargetFramework`、`Nullable`、`LangVersion`、Analyzer／Warnings、鄰近 Tests、Resource Ownership 與 Repository 已存在的 DI Registration；Version Unknown 時保守回報。

Semantic Sections 必須給出條件與反例：Nullable Annotation 不等於 Runtime Validation；CancellationToken 要沿既有可取消邊界傳遞但不能擅改公開 API；`using`／`await using` 依 Ownership 與 Async Disposal；LINQ Deferred Execution／Multiple Enumeration 可能改變 I/O、時間點與例外；Class／Record／Value Object Equality 依領域契約；DI Lifetime 只有 Repository 已使用 Container 時適用。禁止把 ASP.NET Core、特定 Container 或 Repository Pattern 寫成 C# 通則。

將 `profiles/csharp.yaml` 同一步改為：

```yaml
status: experimental
reference: clean-code-ai-collaboration/references/language-csharp.md
```

Evidence 維持 `not_started` 與空 Results，不宣稱 Pilot。

- [ ] **Step 4: 重新產生 Docs 並執行 GREEN**

```powershell
.\.venv\Scripts\python.exe scripts/generate_profile_matrix.py --source-root .
.\.venv\Scripts\python.exe scripts/validate_profiles.py --source-root .
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract tests.test_profile_routing tests.test_skill_contract -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\agentskills.exe validate clean-code-ai-collaboration
git diff --check
```

Expected: C# 顯示 Experimental／Available／Not started；其餘仍 Planned；全部 Tests PASS。

- [ ] **Step 5: Commit M1-A C# Profile**

```powershell
git add profiles/csharp.yaml clean-code-ai-collaboration/references/language-csharp.md clean-code-ai-collaboration/references/profile-selection.md README.md tests/test_profile_contract.py tests/test_profile_routing.py
git diff --cached --check
git diff --cached
git commit -m "feat(profiles): add experimental csharp guidance"
```

---

### Task 5: M1-B—完成 Python Experimental Profile

**Files:**
- Modify: `profiles/python.yaml`
- Create: `clean-code-ai-collaboration/references/language-python.md`
- Modify: `tests/test_profile_contract.py`
- Modify: `tests/test_profile_routing.py`
- Modify: `README.md`
- Modify: `clean-code-ai-collaboration/references/profile-selection.md`

**Interfaces:**
- Consumes: Task 3 的 Python Detection 與 Task 4 已驗證的原子成熟度流程。
- Produces: `python.status: experimental`、完整 Python Reference 與 Python Routing／Semantic Contracts。

- [ ] **Step 1: 寫 Python Profile RED Tests**

新增 `test_python_profile_has_complete_semantic_contract()`，逐一 Assert 固定 Headings 與：

```python
required_terms = {
    "pyproject.toml",
    "Python version",
    "dynamic typing",
    "mutable default",
    "aliasing",
    "asyncio",
    "cancellation",
    "context manager",
    "exception boundary",
    "type checker",
}
```

Assert Reference 不把 FastAPI、Django、Pydantic 或特定 Type Checker 寫成必要通則，並驗證 Python Fixture 只選 `python`。

- [ ] **Step 2: 執行 RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract tests.test_profile_routing -v
```

Expected: FAIL，原因是 Python Reference 不存在且 Metadata 尚未 Experimental。

- [ ] **Step 3: 撰寫 Python Reference 並原子升級 Metadata**

Reference 必須先查 Python／Packaging Version、`pyproject.toml`／Setup Config、Formatter／Linter／Type Checker／Test Runner 設定、Async Boundary、Context Manager 與鄰近型別慣例。

Semantic Sections 明確涵蓋 Dynamic Typing 與 Runtime Boundary、Mutable Default／Aliasing、Iterator／Generator 單次消耗、`asyncio` Cancellation、Context Manager／Cleanup、Exception Translation 與 `raise NewError(message) from original_error`。Type Hint 只在既有工具與 Boundary 有價值時使用；不得把 FastAPI、Django、Pydantic、mypy 或 pyright 當成所有 Python Repository 的必要選擇。

將 Metadata 改成 Experimental 並加入 `language-python.md` Reference；Evidence 保持 Not started。

- [ ] **Step 4: 重新產生 Docs 並執行 GREEN**

```powershell
.\.venv\Scripts\python.exe scripts/generate_profile_matrix.py --source-root .
.\.venv\Scripts\python.exe scripts/validate_profiles.py --source-root .
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract tests.test_profile_routing tests.test_skill_contract -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\agentskills.exe validate clean-code-ai-collaboration
git diff --check
```

Expected: C#／Python Experimental；其他六個 Planned；全部 PASS。

- [ ] **Step 5: Commit M1-B Python Profile**

```powershell
git add profiles/python.yaml clean-code-ai-collaboration/references/language-python.md clean-code-ai-collaboration/references/profile-selection.md README.md tests/test_profile_contract.py tests/test_profile_routing.py
git diff --cached --check
git diff --cached
git commit -m "feat(profiles): add experimental python guidance"
```

---

### Task 6: M1-C—完成 TypeScript 與 React Experimental Profiles

**Files:**
- Modify: `profiles/typescript.yaml`
- Modify: `profiles/react.yaml`
- Create: `clean-code-ai-collaboration/references/language-typescript.md`
- Create: `clean-code-ai-collaboration/references/framework-react.md`
- Modify: `tests/test_profile_contract.py`
- Modify: `tests/test_profile_routing.py`
- Modify: `README.md`
- Modify: `clean-code-ai-collaboration/references/profile-selection.md`

**Interfaces:**
- Consumes: TypeScript Language Candidate、React `react` Dependency Candidate、`react-dom`／`react-native` Supporting Dependencies 與非自動 `recommends`。
- Produces: 兩份分離 Reference、TypeScript React 雙層 Composition 與 JavaScript React 單層 Contract。

- [ ] **Step 1: 寫 TypeScript／React 分離 RED Tests**

新增兩個 Semantic Contract Tests。TypeScript 必須包含：

```python
typescript_terms = {
    "strict", "exactOptionalPropertyTypes", "noUncheckedIndexedAccess",
    "structural typing", "union", "narrowing", "Promise",
    "moduleResolution", "target", "runtime validation",
}
```

React 必須包含：

```python
react_terms = {
    "Hooks", "stale closure", "Effect cleanup", "state identity",
    "controlled", "key", "error", "loading", "react-dom", "renderer",
}
```

Routing Tests 必須同時證明 `.tsx + react` 選 `[typescript, react]`、`.jsx + react` 只選 `[react]`、只有 `react-dom` 不選 React、同 Package 非 React `.ts` 工具只選 TypeScript、React Native 只套用 Renderer-neutral 規則。

- [ ] **Step 2: 執行 RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract tests.test_profile_routing -v
```

Expected: FAIL，原因是兩份 Reference 不存在且真實 Metadata 仍 Planned。

- [ ] **Step 3: 撰寫 TypeScript Language Reference**

Reference 必須檢查 TypeScript Version、`tsconfig*` 的 `strict`、`exactOptionalPropertyTypes`、`noUncheckedIndexedAccess`、`moduleResolution`、`target`、Project References、Package Type／Exports 與既有 Typecheck／Test Gate。

Semantic Sections 明確區分 Compile-time 與 Runtime：Structural Typing、Optional／Undefined、Narrowing／Discriminated Union、Readonly 不保證 Runtime Immutability、Promise Error／Cancellation、Module Interop、Declaration／Public Type Compatibility。不得把 React、Vue、Zod、ESLint 或某一 Bundler 當成 TypeScript 通則。

- [ ] **Step 4: 撰寫 React Framework Reference**

Reference 必須先確認 `react` Dependency、Version、Renderer、Strict Mode、Test Library 與 Changed Module 是否真的涉及 React。Renderer-neutral Sections 涵蓋 Hook Order、Stale Closure、Effect Dependency／Cleanup、State Identity／Immutability、Derived State、Stable Keys、Error／Loading 與 Concurrent Rendering Assumptions。

Controlled Input 與 DOM-specific Event／Test 建議只有 `react-dom` 存在時適用；`react-native` 只允許共通 React 語意，平台 API 明確 Out of Scope。不得把 `.tsx`、JSX Syntax 或 `react-dom` 單獨當成 React Candidate。

- [ ] **Step 5: 原子升級兩份 Metadata 並更新 Generated Docs**

```yaml
# profiles/typescript.yaml
status: experimental
reference: clean-code-ai-collaboration/references/language-typescript.md

# profiles/react.yaml
status: experimental
reference: clean-code-ai-collaboration/references/framework-react.md
```

React `recommends: [typescript]` 保留，但 Routing 不因 Recommendation 自動套用 TypeScript。兩份 Evidence 都維持 Not started。

- [ ] **Step 6: 執行 GREEN 與完整 Regression**

```powershell
.\.venv\Scripts\python.exe scripts/generate_profile_matrix.py --source-root .
.\.venv\Scripts\python.exe scripts/generate_profile_matrix.py --source-root . --check
.\.venv\Scripts\python.exe scripts/validate_profiles.py --source-root .
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract tests.test_profile_routing tests.test_skill_contract -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\agentskills.exe validate clean-code-ai-collaboration
git diff --check
```

Expected: C#、Python、TypeScript、React 為 Experimental；Go、Rust、Java、Vue 為 Planned；JavaScript React 不誤套 TypeScript；全部 PASS。

- [ ] **Step 7: Commit M1-C TypeScript／React Profiles**

```powershell
git add profiles/typescript.yaml profiles/react.yaml clean-code-ai-collaboration/references/language-typescript.md clean-code-ai-collaboration/references/framework-react.md clean-code-ai-collaboration/references/profile-selection.md README.md tests/test_profile_contract.py tests/test_profile_routing.py
git diff --cached --check
git diff --cached
git commit -m "feat(profiles): add typescript and react guidance"
```

---

### Task 7: M1-D1—建立可重現且 Fail-closed 的 Specialist Packager

**Files:**
- Create: `scripts/package-manifest.schema.json`
- Create: `scripts/build_skill_package.py`
- Create: `tests/test_profile_packaging.py`
- Create: `tests/fixtures/profile-packaging/csharp/input/`
- Create: `tests/fixtures/profile-packaging/csharp/expected-manifest.json`
- Create: `tests/fixtures/profile-packaging/csharp/expected-digest.txt`

**Interfaces:**
- Consumes: Valid Registry、選取的 Profile IDs、Core Files、Source Mode 與不存在的 Output Directory。
- Produces: `build_package(source_root: Path, output: Path, source_mode: Literal["release", "worktree"], profile_ids: Sequence[str]) -> dict[str, Any]`、`canonical_json_bytes(value: Mapping[str, Any]) -> bytes`、`compose_profiles()`、`main()`。

- [ ] **Step 1: 寫 Packaging RED Tests**

在 `tests/test_profile_packaging.py` 的 `setUp()` 建立 `TemporaryDirectory`，把 `self.temporary_root` 指向該目錄、`self.output` 指向尚不存在的 `package` 子目錄；`tearDown()` 關閉 TemporaryDirectory。`build_worktree_package(*profile_ids)` 固定呼叫 `build_package(ROOT, self.output, "worktree", profile_ids)`。至少固定：

```python
def test_csharp_package_contains_only_core_and_selected_profile(self) -> None:
    manifest = self.build_worktree_package("csharp")
    paths = {entry["path"] for entry in manifest["files"]}
    self.assertIn("SKILL.md", paths)
    self.assertIn("references/language-csharp.md", paths)
    self.assertNotIn("references/language-python.md", paths)

def test_react_does_not_implicitly_package_typescript(self) -> None:
    manifest = self.build_worktree_package("react")
    self.assertEqual(["react"], manifest["profile_ids"])

def test_generated_skill_keeps_bundled_profiles_conditional(self) -> None:
    self.build_worktree_package("csharp")
    skill = (self.output / "SKILL.md").read_text(encoding="utf-8")
    adapter = (self.output / "agents" / "openai.yaml").read_text(encoding="utf-8")
    selection = (self.output / "references" / "profile-selection.md").read_text(
        encoding="utf-8"
    )
    self.assertIn("profile-selection.md", skill)
    self.assertIn("Bundled means available, not automatically applied", selection)
    self.assertIn("allow_implicit_invocation: false", adapter)
    self.assertIn("$clean-code-ai-csharp", adapter)

def test_existing_output_directory_fails_without_mutation(self) -> None:
    output = self.temporary_root / "existing"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with self.assertRaisesRegex(FileExistsError, "output directory already exists"):
        build_package(ROOT, output, "worktree", ["csharp"])
    self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))
```

另測 Release Mode Dirty Worktree Fail、Planned Target Fail、Missing Requires Fail、Recommendation 不自動加入、Manifest Schema、Input／File Hash、無 Timestamp／Absolute Path／OS、Canonical Fixture 固定 Digest、Worktree Source Symlink 指向 Source Root 外時在建立 Output 前失敗，以及注入寫檔失敗時只刪本次檔案且不使用 Recursive Delete。

- [ ] **Step 2: 執行 RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_packaging -v
```

Expected: FAIL，原因是 Package Schema、Builder 與 Fixture 尚不存在。

- [ ] **Step 3: 建立 Package Manifest Schema**

`scripts/package-manifest.schema.json` 使用 Draft 2020-12、`additionalProperties: false`，必填：

```json
[
  "schema_version",
  "source_commit",
  "source_mode",
  "suite_version",
  "packager_version",
  "profile_ids",
  "inputs",
  "files",
  "overall_digest"
]
```

`source_commit` 是 40 位小寫 Git SHA；`source_mode` 為 `release|worktree`；`profile_ids` 唯一且已排序；`inputs`／`files` 每筆只含 Repository／Package-relative POSIX `path` 與 64 位小寫 SHA-256；`overall_digest` 同為 SHA-256。Schema Version 與 Packager Version 起始都為 `"1.0"`。

- [ ] **Step 4: 實作 Source Readers、Composition 與安全 Output Boundary**

`build_skill_package.py` 必須提供：

```python
def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


```

同檔案實作 `compose_profiles(profiles_by_id: Mapping[str, Mapping[str, Any]], selected_ids: Sequence[str]) -> Sequence[str]` 與 `build_package(source_root: Path, output: Path, source_mode: Literal["release", "worktree"], profile_ids: Sequence[str]) -> dict[str, Any]`。Release Mode 先確認 `git status --porcelain` 空白，解析 HEAD SHA，所有 Input 用 `git show HEAD:path` 讀取；Worktree Mode 仍記錄目前 HEAD SHA，但每個 Input 都必須是 Repository-relative POSIX Path、不是 Symlink，且 `resolve(strict=True)` 後仍位於解析後的 Source Root，才可用 `Path.read_bytes()`。兩種模式都正規化 LF 的 Generator-owned Text Output，不改寫複製來源的 Bytes。

Composition 只展開傳遞式 `requires`；不加入 `recommends`。Planned、Deprecated、缺 Reference、Conflict、Self／Cycle 或 Unknown ID 一律在建立 Output 前失敗。

Output 必須在開始時不存在。先在記憶體完成 Source／Manifest 驗證，再逐一建立目錄與檔案並記錄 `created_files`、`created_directories`；每個檔案以 Exclusive Create Mode `xb` 寫入，競態下已存在也不得覆寫。Exception 時只對 `created_files` 呼叫 `unlink()`，再依深度反向對空目錄呼叫非遞迴 `rmdir()`；不使用 `shutil.rmtree()`、Glob Delete 或 Shell Delete。

- [ ] **Step 5: 產生 Skill、Adapter、Runtime Index 與 Manifest**

Package 只包含：Generated `SKILL.md`、Generated `agents/openai.yaml`、必要 Core References、Package-specific `profile-selection.md`、Selected／Required Profile References、`LICENSE` 與 `PACKAGE-MANIFEST.json`。

Generated Skill Name 使用 `clean-code-ai-<sorted-profile-slug>`；C# Sample 固定為 `clean-code-ai-csharp`。其 Frontmatter Version 為 `0.5.0`，Core Body 保留，但 Runtime Index 只列 Bundled Profiles。Adapter 的 Display Name／Prompt 對應 Generated Skill Name，並固定保留 `policy.allow_implicit_invocation: false`；Default Prompt 仍要求依 Changed Module 判斷適用性與遵守 Core 授權邊界。

Manifest `inputs`／`files` 依 `(path.casefold(), path)` 排序；`files` 不列 Manifest 自身。先建立沒有 `overall_digest` 的 Manifest，對 Canonical JSON Bytes 計算 SHA-256，再加入 Digest 並寫入。最後用 `Draft202012Validator` 驗證實際 Manifest，重新計算所有 File Hash。

Packager CLI 固定使用 SPEC 的 `--source-root`、`--output`、`--source-mode` 與可重複 `--profile`；成功回傳 `0`，已知 Validation／Composition／Source／Output Contract Failure 回傳 `1` 並輸出排序後 Diagnostic，Usage Error 回傳 `2`，一般 Contract Failure 不輸出 Traceback。

- [ ] **Step 6: 建立跨平台 Canonical Fixture**

`tests/fixtures/profile-packaging/csharp/input/` 保存小型固定 Core、C# Reference、Metadata 與 LICENSE；`expected-manifest.json` 的 Source Commit 使用固定 40 位測試 SHA。`expected-digest.txt` 保存對同一 Input 以 Canonical JSON 算出的唯一 Digest。測試直接呼叫 Pure Manifest Builder，不依目前 Repository HEAD，因此 Windows 與 Ubuntu 能比較同一常數。

- [ ] **Step 7: 執行 GREEN、Open Standard 與完整 Regression**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_packaging -v
.\.venv\Scripts\python.exe scripts/build_skill_package.py --source-root . --output dist/clean-code-ai-csharp --source-mode release --profile csharp
.\.venv\Scripts\agentskills.exe validate dist/clean-code-ai-csharp
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
git status --short
```

Expected: Package Validation PASS；`dist/` 不出現在 Git Status；Source Repository 沒有其他 Generated Output。

- [ ] **Step 8: Commit M1-D1 Packager**

```powershell
git add scripts/package-manifest.schema.json scripts/build_skill_package.py tests/test_profile_packaging.py tests/fixtures/profile-packaging
git diff --cached --check
git diff --cached
git commit -m "feat(packaging): build reproducible specialist skills"
```

---

### Task 8: M1-D2—完成 Authoring Guide、README 與雙平台 CI

**Files:**
- Create: `docs/profile-authoring.md`
- Modify: `README.md`
- Modify: `.github/workflows/validate.yml`
- Modify: `tests/test_profile_contract.py`
- Modify: `tests/test_profile_packaging.py`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: Tasks 2–7 的 Validator、Generator、Packager、四個 Experimental／四個 Planned Profiles。
- Produces: Contributor Workflow、公開狀態說明、Ubuntu／Windows 相同 Canonical Digest Gate 與 Sample Package Validation。

- [ ] **Step 1: 寫 Docs 與 Workflow RED Tests**

新增 Contract Tests，確認 `docs/profile-authoring.md` 包含 Planned／Experimental 原子邊界、固定 Headings、Ownership、Evidence Outcome、Suite SemVer、Originality／Attribution、Generator、Validator、Packaging／Release 限制與 Reviewer Checklist；README 包含 Core Only、Changed Module、Language／Framework Composition、Explicit Profile、成熟度限制與未發布 Sample Package。

Workflow Test 必須 Assert：

```python
for term in {
    "ubuntu-latest",
    "windows-latest",
    'python-version: "3.12"',
    "scripts/validate_profiles.py --source-root .",
    "scripts/generate_profile_matrix.py --source-root . --check",
    "scripts/build_skill_package.py",
    "agentskills validate clean-code-ai-collaboration",
    "agentskills validate dist/clean-code-ai-csharp",
}:
    self.assertIn(term, workflow)
```

- [ ] **Step 2: 執行 RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_contract tests.test_profile_packaging tests.test_skill_contract -v
```

Expected: FAIL，原因是 Authoring Guide、README 說明與 Windows Matrix 尚未完成。

- [ ] **Step 3: 撰寫唯一 Profile Authoring Guide**

`docs/profile-authoring.md` 使用台灣繁體中文，依序說明：先新增 Planned Metadata 與 Catalog；只有完整 Reference、Routing／Semantic Tests、Generated Docs 同一變更時才能升 Experimental；固定 12 個英文 Headings；Detection Ownership／Supporting 分離；Composition 與 Conflict；Maintainer；Evidence 四種 Outcome 全部保留；Suite SemVer 與 Profile Maturity 分離，純相容修正為 Patch、增加相容 Profile／Detection Selection 為 Minor、破壞 ID／Schema／Composition／Selection／Output Contract 為 Major；Reference 必須原創或保留必要 License／Attribution，且不得重製書籍或第三方內容；Validator／Generator Commands；Experimental 不等於效果已證明；Package／Push／Release 需要額外授權。

Guide 必須連回 SPEC 與 `CONTEXT.md`，不複製 Schema 全欄位或另建 Roadmap。

- [ ] **Step 4: 完成 README 使用說明與 Generated Matrix 周邊文字**

在 Generated Matrix 前後明確說明：預設呼叫仍是 `$clean-code-ai-collaboration`；Agent 依 Changed Module 套用可用 Language／Framework Profile；Core Only 是有效結果；Explicit Profile 不能繞過 Availability／Applicability／Conflict；四個 Experimental 只有文件與 Contract Tests，尚未完成 M2 Pilot；四個 Planned 不可用。

Specialist Package 段落只示範本機產生 `dist/clean-code-ai-csharp/`，標明 Git ignored、沒有 ZIP、未發布、不能從 Package 名稱推論每個任務都套用 C#。貢獻入口只連到 `docs/profile-authoring.md`。

- [ ] **Step 5: 將 CI 改成 Ubuntu／Windows Python 3.12 Matrix**

`.github/workflows/validate.yml` 的 Job 固定使用：

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-latest, windows-latest]
runs-on: ${{ matrix.os }}
```

兩個平台共同執行 Dependencies、Full Tests、`compileall`、Profile Validator、Generated `--check`、Release Mode C# Sample Build、Core 與 Sample `agentskills validate`。Canonical Fixture Test 在兩個 Runner 都比對 `expected-digest.txt`；不靠跨 Job 暫存 Artifact 才能得知結果。

- [ ] **Step 6: 執行本機 GREEN 與完整 Integration Gate**

```powershell
.\.venv\Scripts\python.exe scripts/validate_profiles.py --source-root .
.\.venv\Scripts\python.exe scripts/generate_profile_matrix.py --source-root . --check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q evals/harness evals/v040_strategy_full_run.py scripts
.\.venv\Scripts\agentskills.exe validate clean-code-ai-collaboration
.\.venv\Scripts\agentskills.exe validate dist/clean-code-ai-csharp
git diff --check
```

Expected: Windows Local Gates 全部 PASS；GitHub Actions 尚未執行，因此只能記錄為 Pending，不能宣稱跨平台 CI 已通過。

- [ ] **Step 7: Commit M1-D2 Docs 與 CI**

```powershell
git add docs/profile-authoring.md README.md .github/workflows/validate.yml tests/test_profile_contract.py tests/test_profile_packaging.py tests/test_skill_contract.py
git diff --cached --check
git diff --cached
git commit -m "docs(profiles): publish authoring and validation workflow"
```

---

### Task 9: Release Boundary—執行 SPEC Compliance 與 Code Review

**Files:**
- Verify: `clean-code-ai-collaboration/**`
- Verify: `profiles/**`
- Verify: `scripts/**`
- Verify: `tests/**`
- Verify: `README.md`
- Verify: `docs/profile-authoring.md`
- Verify: `.github/workflows/validate.yml`
- Do not modify: `evals/results/**`
- Do not modify: `evals/manifests/v0.4.0-strategy-full-run.json`

**Interfaces:**
- Consumes: Tasks 1–8 的本機 Commits。
- Produces: Local Gate、Spec Compliance、Code Review、Remote Divergence 與 CI Pending／Observed 狀態；不產生 Release。

- [ ] **Step 1: 執行全部本機 Gates**

```powershell
.\.venv\Scripts\python.exe scripts/validate_profiles.py --source-root .
.\.venv\Scripts\python.exe scripts/generate_profile_matrix.py --source-root . --check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q evals/harness evals/v040_strategy_full_run.py scripts
.\.venv\Scripts\agentskills.exe validate clean-code-ai-collaboration
git diff --check
git status --short --branch
```

若 `dist/clean-code-ai-csharp/` 已由 Task 7 建立，再驗證它；若不存在，以新的明確 Output Directory建立一次後驗證。不得為重跑而遞迴刪除既有 `dist/`。

- [ ] **Step 2: 驗證 Profile 狀態、Reference 篇幅與 Core 篇幅**

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; import yaml; root=Path('profiles'); print([(p.name, yaml.safe_load(p.read_text(encoding='utf-8'))['status']) for p in sorted(root.glob('*.yaml')) if p.name != 'catalog.yaml'])"
.\.venv\Scripts\python.exe -c "from pathlib import Path; p=Path('clean-code-ai-collaboration/SKILL.md'); body=p.read_text(encoding='utf-8').split('---',2)[2]; print(len(body.split()))"
.\.venv\Scripts\python.exe -c "from pathlib import Path; refs=sorted(Path('clean-code-ai-collaboration/references').glob('language-*.md')) + sorted(Path('clean-code-ai-collaboration/references').glob('framework-*.md')); print([(p.name, len(p.read_text(encoding='utf-8').split())) for p in refs])"
```

Expected: C#、Python、TypeScript、React 是 Experimental；Go、Rust、Java、Vue 是 Planned；Core Body 不超過 525 words。逐一檢查四份 Profile Reference 約 1,500 英文單字內，超出者先消除 Core 重複內容。

- [ ] **Step 3: 證明歷史 Evidence 未被改寫**

```powershell
git diff --name-only 7328417..HEAD -- evals/results evals/manifests/v0.4.0-strategy-full-run.json
git diff 7328417..HEAD -- evals/v040_strategy_full_run.py tests/test_v040_strategy_full_run.py
```

Expected: 第一個命令沒有輸出；第二個 Diff 只包含從 v0.4.0 Tag Git Blob 重播的 Preflight 修復與 Tests。

- [ ] **Step 4: 執行 SPEC Compliance Review**

逐條對照 SPEC 的 31 項驗收條件並記錄對應 Test／Command。特別確認：Consumer Runtime 不需 YAML；Planned 不 Routing／Packaging；Supporting Fact 不成為 Owner；React Recommendation 不自動帶入 TypeScript；Generated Marker `--check` 唯讀；Package Manifest 可重算；Output Directory Fail Closed；沒有 M2／M3 Reference 或虛假 Evidence。

- [ ] **Step 5: 執行 Code Review 與安全檢查**

Review `7328417..HEAD`，優先檢查 Path Traversal、Symlink Escape、YAML Unsafe Load、JSON Schema Format 未啟用卻誤信、Git Argument Injection、Recursive Delete、Output Overwrite、EOL／排序非決定性、Exception 後誤刪、Profile ID Hard-code 與 Diagnostic 不穩定。

Run:

```powershell
rg -n "yaml\.load\(|rmtree|Remove-Item|rm -rf|shell=True|FIXME|PLACEHOLDER|NotImplemented|pass\s*$" scripts tests profiles clean-code-ai-collaboration docs/profile-authoring.md README.md
git diff --check 7328417..HEAD
```

Expected: 不存在 Unsafe YAML、Recursive Delete、Shell Invocation、Placeholder 或個人絕對路徑；正常文字命中逐筆判讀。

- [ ] **Step 6: 確認 Commit Boundary 與 Remote 狀態**

```powershell
git log --oneline --decorate 7328417..HEAD
git diff --stat 7328417..HEAD
git rev-list --left-right --count HEAD...origin/main
git status --short --branch
```

Expected: Preflight、M0-A、M0-B、M1-A、M1-B、M1-C、M1-D1、M1-D2 可分開 Review；Worktree 沒有未提交實作檔案。Remote Divergence 與 CI 狀態只照實回報。

- [ ] **Step 7: 只修正真實 Gate Failure，然後停在外部授權前**

若 Review 發現缺陷，先補能重現問題的 Test，確認 RED，再做最小修正、重跑全部 Gates，並依責任使用例如 `fix(packaging): reject escaped output paths` 的 Conventional Commit。若所有 Local Gates 通過，不建立空 Commit。

最終回報必須分開列出 Local Tests、Compile、Open Standard、Generated Check、Spec Review、Code Review、Git Status、Remote Divergence 與 GitHub Actions 狀態。未取得新授權前，不 Push、不建立 PR／Tag／Release、不公開 `dist/`、不執行 M2 Pilot，也不開始 Go／Rust／Java／Vue Reference。
