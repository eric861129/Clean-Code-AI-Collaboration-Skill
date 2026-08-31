# Clean Code AI Collaboration Skill v0.2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 `clean-code-ai-collaboration` 升級為跨平台、可驗證、具公開對照評測的 Agent Skill，並用可查核結果說明 Clean Code 如何改善 AI Coding 的定位、修改、驗證與停止判斷。

**Architecture:** `SKILL.md` 保留風險分流、CLEAN Review Lens、Authorization Gate 與輸出路由；七份 Reference 按任務載入詳細判準。Repository 根目錄保存 Benchmark Manifest、Rubric、原始結果與 CI 契約，評測資料不隨 Skill 安裝進入 Agent Context。

**Tech Stack:** Agent Skills open specification、Markdown、YAML、JSON、Python 3.12 `unittest`、`skills-ref==0.1.1`、GitHub Actions、Git、公開 `AI-CleanCode-API-Demo` .NET Repository。

**Spec:** `docs/superpowers/specs/2026-08-31-clean-code-ai-collaboration-v0.2.0-design.md`

## Global Constraints

- 目標版本固定為 `0.2.0`；尚未達到書面規格的 `v1.0.0` Gate 時，不使用成熟或主流的保證式宣稱。
- Skill 核心遵循 Agent Skills 開放規格；Codex 專屬資訊只放在 `agents/openai.yaml` 與平台安裝說明。
- `SKILL.md` Body 維持 500 個英文單字以內，並只載入會改變當前決策的 Reference。
- Repository 事實優先於 Skill 範例；Evidence 不會擴張授權範圍。
- Token、Tool Call、經過時間與生成行數只比較已通過相同行為與品質 Gate 的候選。
- 目前 Working Tree 的 `README.md` 安裝路徑修改屬於既有 User 內容；實作必須以該內容為基礎，不得覆蓋或遺失。
- `D:\MySelf\AI-CleanCode\AI-CleanCode-API-Demo` 在本計畫中只作唯讀 Benchmark Fixture。除非 User 另行授權，不修改、Commit 或 Push 該 Repository。
- Agent 行為測試使用 Fresh Context，完整記錄模型、Reasoning Effort、Client、工具權限、Repository Commit、Prompt、Diff、命令、Exit Code、Oracle 與 Blind Spot。
- 缺少 Token Telemetry 時記錄 `not available`，不以字數或估算值替代。
- 所有檔案使用 UTF-8；不得加入 Token、Secret、內部資料或無法公開的 Evidence。
- 每個 Task 完成自己的 RED、GREEN、回歸驗證與 Conventional Commit；未經 User 指示不得 Push、建立 Release 或 Tag。

## File Map

| Path | Responsibility |
| --- | --- |
| `clean-code-ai-collaboration/SKILL.md` | Skill Discovery、風險分流、CLEAN Lens、Authorization Gate 與輸出路由 |
| `clean-code-ai-collaboration/agents/openai.yaml` | Codex 顯示資訊、預設 Prompt 與隱式啟用設定 |
| `clean-code-ai-collaboration/references/clean-code-for-agent-legibility.md` | Clean Code 對 Agent 導航、理解、修改與驗證的作用機制與反效果 |
| `clean-code-ai-collaboration/references/code-readability.md` | 命名、註解、函式、Model、Class 與閱讀成本判斷 |
| `clean-code-ai-collaboration/references/testing-and-change-safety.md` | Oracle、測試節奏、失敗路徑、副作用與高風險變更 |
| `clean-code-ai-collaboration/references/design-and-dependency-boundaries.md` | Simple Design、SOLID、依賴方向、外部邊界與並行視窗 |
| `clean-code-ai-collaboration/references/collaboration-and-estimation.md` | Ownership、Handoff、平行工作、估算與人類承諾 |
| `clean-code-ai-collaboration/references/repository-context-template.md` | 決策前要查證的 Repository 事實與 Critical Unknown 判準 |
| `clean-code-ai-collaboration/references/review-output-contract.md` | Full Path 固定輸出順序與 `F/A/U/O/E` Traceability |
| `evals/manifest.json` | 三組對照、四個固定情境、不可變 Commit、Gold Files 與 Oracle |
| `evals/benchmark.md` | Benchmark 執行方式、作用範圍、評分方法與限制 |
| `evals/rubrics/*.md` | Context、Diff、Behavior、Validation、Decision 與 Escalation 評分契約 |
| `evals/results/*.json` | RED 基準、`v0.2.0` 結果、原始輸出、Diff 與人工評分 |
| `tests/test_skill_contract.py` | Skill 封裝、Frontmatter、Reference 路由、Authorization 與 UI Contract |
| `tests/test_eval_contract.py` | Manifest、Rubric、Result、Markdown Link 與 UTF-8 Contract |
| `requirements-dev.txt` | CI 使用的固定版 Agent Skills Validator |
| `.github/workflows/validate.yml` | Unit Tests、`skills-ref` 與公開封裝驗證 |
| `README.md` | 價值、安裝、平台支援、使用 Prompt、Benchmark 結果與貢獻方式 |

---

### Task 1: 建立公開 Benchmark Contract

**Files:**
- Create: `tests/test_eval_contract.py`
- Create: `evals/manifest.json`
- Create: `evals/benchmark.md`
- Create: `evals/rubrics/context-and-locality.md`
- Create: `evals/rubrics/behavior-and-validation.md`
- Create: `evals/rubrics/decision-and-escalation.md`

**Interfaces:**
- Consumes: Design Spec 的三組對照、四種情境與多維評測指標。
- Produces: `manifest.json` Schema、固定 Scenario ID、Rubric 檔名與後續 Result 必須引用的欄位。

- [ ] **Step 1: 先寫缺少評測檔案時會失敗的 Contract Test**

在 `tests/test_eval_contract.py` 建立以下測試骨架：

```python
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals"
MANIFEST_PATH = EVAL_ROOT / "manifest.json"
RUBRIC_NAMES = {
    "context-and-locality.md",
    "behavior-and-validation.md",
    "decision-and-escalation.md",
}
ARM_IDS = {"control", "generic-clean-code", "skill-v0.2.0"}
SCENARIO_IDS = {
    "context-locality",
    "behavior-validation",
    "dependency-boundary",
    "concurrency-side-effects",
}


class EvalContractTests(unittest.TestCase):
    def load_manifest(self) -> dict:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_defines_fixed_arms_and_scenarios(self) -> None:
        manifest = self.load_manifest()
        self.assertEqual(ARM_IDS, {item["id"] for item in manifest["arms"]})
        self.assertEqual(
            SCENARIO_IDS,
            {item["id"] for item in manifest["scenarios"]},
        )
        self.assertEqual(5, manifest["repetitions"]["micro"])
        self.assertEqual(3, manifest["repetitions"]["repository"])

    def test_every_scenario_is_reproducible(self) -> None:
        for scenario in self.load_manifest()["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                self.assertRegex(scenario["commit"], r"^[0-9a-f]{40}$")
                self.assertTrue(scenario["task"].strip())
                self.assertTrue(scenario["gold_files"])
                self.assertTrue(scenario["allowed_diff"])
                self.assertIn("dotnet test AiCleanCode.sln --no-restore", scenario["oracle_commands"])
                self.assertEqual(RUBRIC_NAMES, set(scenario["rubrics"]))

    def test_rubric_files_exist_and_define_scoring(self) -> None:
        actual = {path.name for path in (EVAL_ROOT / "rubrics").glob("*.md")}
        self.assertEqual(RUBRIC_NAMES, actual)
        for path in (EVAL_ROOT / "rubrics").glob("*.md"):
            content = path.read_text(encoding="utf-8")
            self.assertIn("## Scoring", content)
            self.assertIn("## Evidence Required", content)
            self.assertIn("## Automatic Failure", content)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試並確認 RED 原因正確**

Run:

```powershell
py -3 -m unittest tests.test_eval_contract -v
```

Expected: `ERROR` 或 `FAIL`，原因是 `evals/manifest.json` 與 Rubric 尚不存在；不能是 Import Error 或 Syntax Error。

- [ ] **Step 3: 建立固定 Manifest**

`evals/manifest.json` 必須包含以下頂層結構與固定 Revision：

```json
{
  "schema_version": "1.0",
  "benchmark_version": "0.2.0",
  "repository": {
    "url": "https://github.com/eric861129/AI-CleanCode-API-Demo.git",
    "read_only": true
  },
  "repetitions": {
    "micro": 5,
    "repository": 3
  },
  "arms": [
    {
      "id": "control",
      "instruction": ""
    },
    {
      "id": "generic-clean-code",
      "instruction": "請遵守 Clean Code 完成任務。"
    },
    {
      "id": "skill-v0.2.0",
      "skill": "clean-code-ai-collaboration",
      "version": "0.2.0"
    }
  ],
  "scenarios": []
}
```

`scenarios` 填入以下四筆資料；每筆都加入三份 Rubric 與 `dotnet test AiCleanCode.sln --no-restore`、`dotnet format AiCleanCode.sln --verify-no-changes --no-restore`：

| ID | Tag | Commit | Task focus | Gold files |
| --- | --- | --- | --- | --- |
| `context-locality` | `day-06-comments-formatting` | `1583af33b5e517530871ff3ee724cdcad4e4c5c0` | High Priority 工作項目延後兩小時才逾期；保留 HTTP Contract、通知、取消與儲存順序 | `WorkItemsController.cs`、`ProcessOverdueBehaviorTests.cs` |
| `behavior-validation` | `day-13-clean-acceptance-tests-baseline` | `9b8c94c79a18eea24645aaee268e81783d94886f` | 補上剛好到期、通知失敗仍儲存、重跑不重複副作用的可讀驗收測試 | `OverdueWorkItemProcessor.cs`、`ProcessOverdueBehaviorTests.cs` |
| `dependency-boundary` | `day-16-solid-lsp-isp-dip-baseline` | `ccbc136daa59cfcd430d44ebd4cb62b57b4ab72d` | 新增可替換通知 Provider；保留既有 API、失敗語意與 Consumer 所需契約 | `NotificationGateway.cs`、`OverdueWorkItemProcessor.cs`、相關 Contract Tests |
| `concurrency-side-effects` | `day-18-continuous-design` | `be987152555b651532e4ba68ba1029aa777fb40e` | HTTP 與 Background Worker 同時處理同一筆 Work Item 時避免重複通知；保留 Retry 與 Lost ACK 語意 | `OverdueWorkItemProcessor.cs`、`OverdueProcessingWorker.cs`、`WorkItemsDbContext.cs`、相關 Tests |

每個 Scenario 的 `task` 寫成完整需求，並包含 `must_preserve`、`gold_files`、`allowed_diff`、`allowed_diff_patterns`、`boundary_negative_examples`、`oracle_commands`、`rubrics`。`allowed_diff` 保留已知的精確 Production／Test 路徑；`allowed_diff_patterns` 以大小寫敏感的 Python `re.fullmatch` 接受語意等價的 Provider、Contract Test、Coordinator 或 Registry 命名。兩者都不能放寬成整個 `src/` 或 `tests/`，而且 Pattern 通過不代表自動取得完整 Locality 分數。

Manifest 頂層加入 `diff_boundary_pattern_semantics`，固定 Repository-relative POSIX path、完整匹配，以及重新命名來源與目的路徑都要驗證。Baseline 每筆 Run 必須快照 exact list、Patterns、逐路徑 provenance 與真正越界路徑；修正衍生評分時保留 `rescoring_history`，不得改寫原始 Diff、雜湊、Oracle、Automatic Failure 或比較資格。

- [ ] **Step 4: 寫完三份 Rubric 與 Benchmark 說明**

每份 Rubric 使用相同結構：

```markdown
# Context and Locality Rubric

## Purpose

## Scoring

| Score | Observable condition |
| --- | --- |
| 0 | Missing or contradicted |
| 1 | Partially supported |
| 2 | Fully supported by recorded evidence |

## Evidence Required

## Automatic Failure
```

`Automatic Failure` 至少涵蓋未授權公開契約變更、未執行卻宣稱通過、遺失外部副作用與破壞 Gold Behavior。`evals/benchmark.md` 說明三組對照、固定變因、執行順序、多維報告、不能使用單一總分，以及結果只支持記錄條件。

- [ ] **Step 5: 執行 Contract Tests**

Run:

```powershell
py -3 -m unittest discover -s tests -v
```

Expected: 現有 10 項 Skill Contract 與新增 Eval Contract 全部通過。

- [ ] **Step 6: Commit Benchmark Contract**

```powershell
git add tests/test_eval_contract.py evals/manifest.json evals/benchmark.md evals/rubrics
git diff --cached --check
git diff --cached
git commit -m "test(evals): define public benchmark contract"
```

---

### Task 2: 執行無 v0.2.0 Skill 的 RED 行為基準

**Files:**
- Create: `evals/results/v0.1.0-baseline.json`

**Interfaces:**
- Consumes: Task 1 的 Manifest、Rubric、Control 與 Generic Clean Code Arm。
- Produces: 後續 `v0.2.0` 必須改善或至少不退步的可查 RED 行為資料。

- [ ] **Step 1: 固定執行資訊與 Result Schema**

Result JSON 使用以下結構：

```json
{
  "schema_version": "1.0",
  "benchmark_version": "0.2.0",
  "skill_version": "0.1.0",
  "status": "complete",
  "environment": {
    "client": "Codex",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "high",
    "tool_permissions": "workspace-scoped",
    "recorded_at": "2026-08-31T12:00:00+08:00"
  },
  "runs": []
}
```

實作時將範例時間換成真實執行時間。每個 Run 包含 `run_id`、`scenario_id`、`arm_id`、`repetition`、`prompt`、`files_read`、`files_changed`、`raw_output`、`diff`、`commands`、`exit_codes`、`oracle`、`rubric_scores`、`blind_spots` 與 `human_decision`。

- [ ] **Step 2: 為每個 Run 建立隔離 Worktree**

對每個 Scenario 的固定 Commit 使用：

```powershell
$runId = "context-locality-control-r01"
$commitSha = "1583af33b5e517530871ff3ee724cdcad4e4c5c0"
$runRoot = Join-Path $env:TEMP "clean-code-skill-eval-$runId"
git -C "D:\MySelf\AI-CleanCode\AI-CleanCode-API-Demo" worktree add --detach $runRoot $commitSha
```

每次執行都從 Manifest 讀取對應的 Run ID 與固定 Commit。工作結束後先確認 Diff 已寫入 Result，再使用 `git worktree remove` 移除該 Worktree；不可刪除 Demo Repository 或共用資料夾。

- [ ] **Step 3: 執行 Control 與 Generic Clean Code Arm**

四個 Scenario、兩個 Arm、每組三次，共 24 個 Fresh Agent Run。每次只提供 Manifest 中的 Task 與該 Arm 指示，不提供本 Skill、預期答案或其他 Run 結論。

每次完成後：

1. 保存 Agent 原始回覆與完整 Diff。
2. 在 Worktree 重新執行 Manifest Oracle。
3. 由主流程依三份 Rubric 評分。
4. 明確記錄未執行項目與環境限制。
5. 將 Result 寫入 `runs`，再進入下一次 Fresh Context。

- [ ] **Step 4: 加入 `v0.1.0` 回歸參考 Run**

每個 Scenario 使用目前 `v0.1.0` Skill 執行一次，共四次。這四筆使用 `arm_id: "skill-v0.1.0"`，只用來判斷版本是否退步，不加入主要三組效果比較。

- [ ] **Step 5: 驗證 Result 完整性**

在 `tests/test_eval_contract.py` 新增：

```python
def test_baseline_results_are_complete(self) -> None:
    path = EVAL_ROOT / "results" / "v0.1.0-baseline.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    self.assertEqual("complete", result["status"])
    runs = result["runs"]
    primary = [run for run in runs if run["arm_id"] in {"control", "generic-clean-code"}]
    regression = [run for run in runs if run["arm_id"] == "skill-v0.1.0"]
    self.assertEqual(24, len(primary))
    self.assertEqual(4, len(regression))
    for run in runs:
        self.assertTrue(run["raw_output"].strip())
        self.assertIn("oracle", run)
        self.assertIn("blind_spots", run)
        self.assertIn("human_decision", run)
```

Run:

```powershell
py -3 -m unittest tests.test_eval_contract -v
```

Expected: PASS，且 Result 沒有 `not-run`、空白原始輸出或遺失 Oracle。

- [ ] **Step 6: Commit RED Baseline**

```powershell
git add evals/results/v0.1.0-baseline.json tests/test_eval_contract.py
git diff --cached --check
git diff --cached --stat
git commit -m "test(evals): capture pre-v0.2 behavior baseline"
```

---

### Task 3: 用 RED Contract 升級 Skill Core 與 Agent Legibility Reference

**Files:**
- Modify: `tests/test_skill_contract.py`
- Modify: `clean-code-ai-collaboration/SKILL.md`
- Create: `clean-code-ai-collaboration/references/clean-code-for-agent-legibility.md`

**Interfaces:**
- Consumes: Task 2 已觀察的定位、過度修改、驗證與停止失敗。
- Produces: `v0.2.0` Frontmatter、七份 Reference 路由、CLEAN Lens 與 Agent Legibility 判斷入口。

- [ ] **Step 1: 新增會因 `v0.1.0` 缺少契約而失敗的測試**

更新 `REFERENCE_NAMES`，加入 `clean-code-for-agent-legibility.md`，並新增：

```python
def test_v020_metadata_and_clean_lenses_are_discoverable(self) -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")
    frontmatter = re.match(
        r"---\n(?P<frontmatter>.*?)\n---\n",
        content,
        re.DOTALL,
    ).group("frontmatter")
    required = {
        "license: MIT",
        "compatibility:",
        'version: "0.2.0"',
        "C — Context-Aware Code",
        "L — Localized Change",
        "E — Explicit Intent and Boundaries",
        "A — Auditable by Evidence",
        "N — Non-Surprising Behavior",
        "clean-code-for-agent-legibility.md",
    }
    for term in required:
        with self.subTest(term=term):
            self.assertIn(term, content)
```

- [ ] **Step 2: 執行 RED**

Run:

```powershell
py -3 -m unittest tests.test_skill_contract.SkillContractTests.test_v020_metadata_and_clean_lenses_are_discoverable -v
```

Expected: FAIL，明確指出 `license`、`compatibility`、`version`、CLEAN Labels 或新 Reference 缺少。

- [ ] **Step 3: 更新 Frontmatter 與 Skill Core**

Frontmatter 使用：

```yaml
---
name: clean-code-ai-collaboration
description: Use when a coding agent must plan, implement, refactor, or review repository changes where readability, behavior preservation, tests, design boundaries, side effects, dependencies, handoffs, or estimates require repository-aware Clean Code judgment.
license: MIT
compatibility: Agent Skills-compatible coding agents. Optional Codex metadata is provided in agents/openai.yaml.
metadata:
  author: eric861129
  version: "0.2.0"
---
```

Body 保留以下固定區塊：

1. Core Principle：Repository 提供事實，Clean Code 提供品質判斷，CLEAN 控制 User 與 Agent 的協作責任。
2. Path Selection：維持 Lightweight Path 與 Full Path 的可觀察風險條件。
3. Reference Routing：Agent Legibility 先提供共同機制，其餘依 Code、Tests、Design、Collaboration 載入。
4. CLEAN Lenses：五個完整英文與中文名稱，各自對應 Context、Expected Diff、Intent、Evidence、Behavior。
5. Authorization Gate：保留 `evidence does not grant authority` 與現有高風險停止條件。
6. Required Output：Lightweight 報告最小結果；Full Path 依 `review-output-contract.md`。

Skill Body 不加入 Benchmark 結果、長篇 Clean Code 教學或平台安裝內容。

- [ ] **Step 4: 建立 Agent Legibility Reference**

`clean-code-for-agent-legibility.md` 使用以下章節：

```markdown
# Clean Code for Agent Legibility

## Use This Reference When
## Mechanisms to Evaluate
## Counter-Effects
## Evidence Questions
## Claim Boundaries
## Stop Conditions
```

`Mechanisms to Evaluate` 涵蓋命名與搜尋、內聚與 Context 範圍、依賴邊界與 Diff、測試與 Oracle、持續整理與 Pattern 複製。`Counter-Effects` 涵蓋過度抽象、錯誤命名、失效註解、脆弱測試與文件漂移。`Claim Boundaries` 明定不保證 Token 降低、任務正確、跨模型泛化或免除人工責任。

- [ ] **Step 5: 執行 GREEN 與完整回歸**

Run:

```powershell
py -3 -m unittest discover -s tests -v
py -3 "C:\Users\erichuang\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\clean-code-ai-collaboration"
```

Expected: 全部 Unit Tests PASS，Validator 顯示 `Skill is valid!`，Skill Body 不超過 500 個英文單字。

- [ ] **Step 6: Commit Skill Core**

```powershell
git add clean-code-ai-collaboration/SKILL.md clean-code-ai-collaboration/references/clean-code-for-agent-legibility.md tests/test_skill_contract.py
git diff --cached --check
git diff --cached
git commit -m "feat(skill): add agent legibility decision path"
```

---

### Task 4: 深化 Clean Code References 與 Full Review Contract

**Files:**
- Modify: `clean-code-ai-collaboration/references/code-readability.md`
- Modify: `clean-code-ai-collaboration/references/testing-and-change-safety.md`
- Modify: `clean-code-ai-collaboration/references/design-and-dependency-boundaries.md`
- Modify: `clean-code-ai-collaboration/references/collaboration-and-estimation.md`
- Modify: `clean-code-ai-collaboration/references/repository-context-template.md`
- Modify: `clean-code-ai-collaboration/references/review-output-contract.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: Task 3 的 Routing 與 CLEAN Lens。
- Produces: 每種決策都有適用條件、替代方案、反例、停止條件與可掃讀輸出順序。

- [ ] **Step 1: 寫出 Reference Decision Contract 的 RED Test**

新增：

```python
def test_decision_references_define_tradeoffs_and_stop_conditions(self) -> None:
    names = {
        "code-readability.md",
        "testing-and-change-safety.md",
        "design-and-dependency-boundaries.md",
        "collaboration-and-estimation.md",
    }
    for name in names:
        content = (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
        with self.subTest(reference=name):
            self.assertIn("## Use This Reference When", content)
            self.assertIn("## Selection Rules", content)
            self.assertIn("## When Another Option Fits Better", content)
            self.assertIn("## Common Misjudgments", content)
            self.assertIn("## Stop Conditions", content)

def test_review_contract_leads_with_status_and_keeps_blind_spots(self) -> None:
    content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
        encoding="utf-8"
    )
    self.assertLess(content.index("## Outcome and Status"), content.index("## Repository Facts Used"))
    self.assertIn("## Validation Blind Spots", content)
    self.assertIn("## Human Decisions Required", content)
```

- [ ] **Step 2: 執行 RED**

Run:

```powershell
py -3 -m unittest tests.test_skill_contract -v
```

Expected: FAIL，指出現有 References 缺少一致的選擇與停止章節，Review Contract 缺少前置狀態或獨立 Blind Spots。

- [ ] **Step 3: 依責任深化四份 Decision Reference**

每份 Reference 套用測試要求的五個固定章節，但保留各自技術內容：

- Readability：Naming Policy、Comment Evidence、Stepdown、CQS、DRY、DTO／Persistence／Domain、Class Cohesion，以及過度拆分的 Navigation Cost。
- Testing：Observable Behavior、3A、TDD／TCR／Characterization／Acceptance／Mutation 的選擇條件，Oracle Reliability、Failure Windows 與高風險升級條件。
- Design：Simple Design、SOLID 五原則、Port／Adapter／Gateway、Dependency Rule、Concurrency、Outbox／Idempotency／Compensation 與 Pattern Cost。
- Collaboration：Ownership、Contract、Integration Order、Handoff、Small Cycle、Estimate Range、Confidence、Human Commitment 與多 Agent 重疊風險。

每份 `When Another Option Fits Better` 至少提供兩組條件式替代方案。`Common Misjudgments` 必須對應已觀察的 Agent Failure，不建立通用 Pattern 排名。

- [ ] **Step 4: 強化 Context 與 Review Output Contract**

`repository-context-template.md` 新增 Evidence Freshness、Source Authority、Current Revision、Executable Oracle 與 Context Budget；Critical Unknown 仍以是否改變行為、資料、安全、依賴、部署或人類決策判斷。

`review-output-contract.md` 固定以下順序：

```markdown
## Outcome and Status
## Applicable References
## Repository Facts Used
## Assumptions
## Unknowns
## Options Considered
## Selected Option and Reason
## When Other Options Fit Better
## Behavior That Must Not Change
## Expected Diff Boundary
## Actual Diff Boundary and Deviations
## Validation Plan
## Evidence Produced
## Validation Blind Spots
## Stop or Escalation Conditions
## Human Decisions Required
```

保留 `F/A/U/O/E` Identifier 與 Sources Checked 規則。Outcome 只能使用 `planned`、`implemented`、`verified-within-scope`、`blocked` 或 `not-investigated`，避免使用沒有證據範圍的 `done`。

- [ ] **Step 5: 執行 GREEN 與回歸**

```powershell
py -3 -m unittest discover -s tests -v
```

Expected: PASS；既有 Authorization、Path、Traceability 與 Reference Exact Set Tests 仍通過。

- [ ] **Step 6: Commit References**

```powershell
git add clean-code-ai-collaboration/references tests/test_skill_contract.py
git diff --cached --check
git diff --cached --stat
git commit -m "feat(skill): strengthen contextual Clean Code decisions"
```

---

### Task 5: 對齊 Codex Adapter 與跨平台 Metadata

**Files:**
- Modify: `clean-code-ai-collaboration/agents/openai.yaml`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: Task 3 的 Skill Name、Version 與三種工作類型。
- Produces: Codex 可讀的 Display Name、Short Description、Default Prompt；其他 Client 可忽略此 Adapter。

- [ ] **Step 1: 寫 UI Contract RED Test**

```python
def test_codex_adapter_covers_plan_implement_and_review(self) -> None:
    content = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    self.assertIn('display_name: "Clean Code AI Collaboration"', content)
    self.assertIn("$clean-code-ai-collaboration", content)
    for term in {"plan", "implement", "review", "repository facts", "behavior gates"}:
        with self.subTest(term=term):
            self.assertIn(term, content.lower())
    self.assertIn("allow_implicit_invocation: true", content)
```

- [ ] **Step 2: 執行 RED**

```powershell
py -3 -m unittest tests.test_skill_contract.SkillContractTests.test_codex_adapter_covers_plan_implement_and_review -v
```

Expected: FAIL，指出目前 Default Prompt 沒有完整涵蓋三種工作類型或必要關鍵字。

- [ ] **Step 3: 更新 `openai.yaml`**

使用：

```yaml
interface:
  display_name: "Clean Code AI Collaboration"
  short_description: "Use repository-aware Clean Code judgment for AI coding"
  default_prompt: "Use $clean-code-ai-collaboration to plan, implement, or review this change from repository facts. Preserve behavior gates, compare viable options, keep the Diff local, report validation blind spots, and stop at authorization boundaries."
policy:
  allow_implicit_invocation: true
```

- [ ] **Step 4: 執行 GREEN 與 Validator**

```powershell
py -3 -m unittest discover -s tests -v
py -3 "C:\Users\erichuang\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\clean-code-ai-collaboration"
```

Expected: PASS；Validator 顯示 `Skill is valid!`。

- [ ] **Step 5: Commit Adapter**

```powershell
git add clean-code-ai-collaboration/agents/openai.yaml tests/test_skill_contract.py
git diff --cached --check
git commit -m "feat(skill): align Codex adapter with open core"
```

---

### Task 6: 把官方格式、Manifest 與 Link Contract 加入 CI

**Files:**
- Create: `requirements-dev.txt`
- Modify: `.github/workflows/validate.yml`
- Modify: `tests/test_eval_contract.py`

**Interfaces:**
- Consumes: Agent Skills `skills-ref` CLI、Task 1 Manifest 與 Repository Markdown。
- Produces: PR／Push 可重跑的結構 Gate；不宣稱模型行為已驗證。

- [ ] **Step 1: 加入 UTF-8 與相對連結 RED Test**

在 `tests/test_eval_contract.py` 新增：

```python
import re


def test_markdown_files_are_utf8_and_local_links_resolve(self) -> None:
    markdown_files = [
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts and "evals/results" not in path.as_posix()
    ]
    link_pattern = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)#]+)(?:#[^)]+)?\)")
    for path in markdown_files:
        content = path.read_text(encoding="utf-8")
        self.assertNotIn("\ufffd", content, path)
        for target in link_pattern.findall(content):
            resolved = (path.parent / target).resolve()
            with self.subTest(source=path, target=target):
                self.assertTrue(resolved.exists(), resolved)
```

- [ ] **Step 2: 執行 RED 或確認現況**

```powershell
py -3 -m unittest tests.test_eval_contract -v
```

Expected: 若有失效相對連結則 FAIL 並顯示精確來源；若現況已通過，保留測試作回歸 Gate，記錄這項 Contract 沒有新的 RED Failure。

- [ ] **Step 3: 固定 Validator 版本**

`requirements-dev.txt`：

```text
skills-ref==0.1.1
```

- [ ] **Step 4: 更新 GitHub Actions**

`.github/workflows/validate.yml` 保留 Python 3.12，Steps 依序為：

```yaml
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: python -m pip install -r requirements-dev.txt
      - name: Unit and Contract Tests
        run: python -m unittest discover -s tests -v
      - name: Agent Skills Specification
        run: skills-ref validate clean-code-ai-collaboration
```

Workflow Name 維持 `Validate Skill Structural Contract`，Job Name 改為 `Open Standard and Repository Contracts`，避免把 CI 誤寫成 Agent Behavior Benchmark。

- [ ] **Step 5: 執行本機 CI 等價命令**

```powershell
py -3 -m pip install -r requirements-dev.txt
py -3 -m unittest discover -s tests -v
skills-ref validate clean-code-ai-collaboration
```

Expected: 全部 PASS；若 CLI 名稱實際為 `agentskills`，先用 `Get-Command skills-ref, agentskills` 查證 `skills-ref==0.1.1` 安裝結果，再讓 CI 與本機使用同一個已存在命令。

- [ ] **Step 6: Commit CI Contract**

```powershell
git add requirements-dev.txt .github/workflows/validate.yml tests/test_eval_contract.py
git diff --cached --check
git diff --cached
git commit -m "ci: validate skill and benchmark contracts"
```

---

### Task 7: 執行 `v0.2.0` GREEN 行為評測

**Files:**
- Create: `evals/results/v0.2.0-initial.json`
- Modify: `evals/benchmark.md`
- Modify: `tests/test_eval_contract.py`
- Conditional Modify: `clean-code-ai-collaboration/SKILL.md`
- Conditional Modify: `clean-code-ai-collaboration/references/*.md`

**Interfaces:**
- Consumes: Task 2 RED Baseline、Task 3 至 Task 6 的 Skill 與 CI。
- Produces: 三組主要對照的完整初始結果、可公開限制與 Skill 行為回歸證據。

- [ ] **Step 1: 先加入 Initial Result RED Test**

```python
def test_v020_initial_results_cover_skill_arm(self) -> None:
    path = EVAL_ROOT / "results" / "v0.2.0-initial.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    self.assertEqual("complete", result["status"])
    runs = result["runs"]
    skill_runs = [run for run in runs if run["arm_id"] == "skill-v0.2.0"]
    self.assertEqual(12, len(skill_runs))
    self.assertEqual(SCENARIO_IDS, {run["scenario_id"] for run in skill_runs})
    for run in skill_runs:
        self.assertTrue(run["raw_output"].strip())
        self.assertIn("rubric_scores", run)
        self.assertIn("human_decision", run)
```

- [ ] **Step 2: 執行 RED**

```powershell
py -3 -m unittest tests.test_eval_contract.EvalContractTests.test_v020_initial_results_cover_skill_arm -v
```

Expected: ERROR，原因是 `v0.2.0-initial.json` 尚不存在。

- [ ] **Step 3: 執行五次 Trigger／Output Micro-eval**

每個 Arm 使用五個 Fresh Context，任務覆蓋「局部命名重構」、「外部副作用變更」、「架構 Review」、「估算」與「低風險格式調整」。記錄 Skill 是否正確啟用、是否選對 Path、是否載入必要 Reference、是否產出適合該 Path 的輸出。

Micro-eval 不修改 Repository。結果放入 `v0.2.0-initial.json` 的 `micro_runs`，每筆包含完整 Prompt、Arm、啟用結果、Path、References、輸出與人工評分。

- [ ] **Step 4: 執行十二個 Skill Repository Run**

四個 Scenario 各執行三次 `skill-v0.2.0` Arm，共十二次。使用 Task 2 相同 Worktree、Fresh Context、模型、Reasoning Effort、工具權限、Oracle 與 Rubric。不得把 RED Baseline 的錯誤或預期答案告訴執行 Agent。

- [ ] **Step 5: 比較行為並執行最多兩輪針對性 REFACTOR**

比較條件：

1. Skill Arm 不得降低 Oracle Pass Rate。
2. 未授權 Contract 或副作用漂移必須為零；出現即自動失敗。
3. Context、Diff、Validation 或 Escalation 至少一項比 Generic Clean Code Arm 改善，才能寫成初始正向結果。
4. Token 與 Tool Call 只在同品質 Run 之間比較。

若發現 Skill 特有失敗：先把失敗轉成最小 Contract 或 Micro-eval，確認 RED，再修改最小一段 Skill／Reference，重跑受影響 Scenario 與全部 Unit Tests。最多進行兩輪；仍未改善時保留失敗結果，停止宣稱該能力已加強。

- [ ] **Step 6: 寫入初始結果與限制**

`evals/benchmark.md` 新增 `## Initial v0.2.0 Results`，使用每個維度的 Run 數、通過數與限制，不建立單一總分。將以下內容分開：

- Observed：直接由 Result 與 Oracle 支持。
- Inference：作者從固定條件推導的解釋。
- Unknown：模型、Client、Repository 或任務改變後的未知。
- Failure：Skill 沒改善或造成額外成本的項目。

- [ ] **Step 7: 執行 GREEN 與回歸**

```powershell
py -3 -m unittest discover -s tests -v
skills-ref validate clean-code-ai-collaboration
git diff --check
```

Expected: PASS；Initial Result 有 12 筆 Skill Repository Run 與 15 筆 Micro Run。

- [ ] **Step 8: Commit Initial Benchmark**

```powershell
git add evals/results/v0.2.0-initial.json evals/benchmark.md tests/test_eval_contract.py clean-code-ai-collaboration
git diff --cached --check
git diff --cached --stat
git commit -m "test(evals): publish v0.2 initial benchmark"
```

若 Step 5 產生 Skill 修正，先用獨立 Commit 提交修正，例如 `fix(skill): correct dependency-boundary escalation`，再建立 Benchmark Commit；不要把規則修正與結果資料混在同一個 Commit。

---

### Task 8: 完成跨平台 README 與公開採用說明

**Files:**
- Modify: `README.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: User 既有 `.agents/skills` 安裝修改、Task 7 的真實結果與限制。
- Produces: 可供 Codex、GitHub Copilot、Claude Code 與其他相容 Client 使用的安裝、Prompt、Benchmark 與貢獻入口。

- [ ] **Step 1: 寫 README Public Contract RED Test**

```python
def test_readme_documents_portability_evidence_and_limits(self) -> None:
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    required = {
        ".agents\\skills",
        "Codex",
        "GitHub Copilot",
        "Claude Code",
        "Clean Code 如何改善 AI Coding",
        "CLEAN 五原則",
        "Benchmark",
        "不保證",
        "規劃",
        "實作",
        "Review",
        "貢獻",
    }
    for term in required:
        with self.subTest(term=term):
            self.assertIn(term, readme)
```

- [ ] **Step 2: 執行 RED**

```powershell
py -3 -m unittest tests.test_skill_contract.SkillContractTests.test_readme_documents_portability_evidence_and_limits -v
```

Expected: FAIL，指出目前 README 缺少平台、Benchmark、限制、三種 Prompt 或貢獻說明；既有 `.agents\skills` 安裝內容應已存在。

- [ ] **Step 3: 以目前 Working Tree README 為底稿重寫**

README 固定使用以下順序：

```markdown
# Clean Code AI Collaboration Skill
## 這個 Skill 解決什麼問題
## Clean Code 如何改善 AI Coding
## CLEAN 五原則
## Skill、Repository Policy 與自動化 Gate 的分工
## 安裝
### Project Skill
### Personal Skill
### Client 支援狀態
## 使用方式
### 規劃
### 實作
### Review
## Benchmark
## 已知限制與不保證事項
## Repository 結構
## 貢獻評測情境
## 來源、非官方聲明與授權
```

`Client 支援狀態` 使用表格區分「Agent Skills 格式相容」與「本專案已實測」。沒有執行過的 Client 標示「尚未實測」，不可由規格相容推論成行為相容。

`Benchmark` 只引用 Task 7 實際數字與 `evals/benchmark.md`。若 Result 未支持正向效果，直接寫出未改善維度，不使用「提升、加強、節省」等結論。

三個 Prompt 必須明確使用 `$clean-code-ai-collaboration`，並分別要求 Plan、Implement、Review；每個 Prompt 都保留 Repository Context、Behavior Gate 與授權邊界。

- [ ] **Step 4: 驗證 README 沒有覆蓋 User 修改**

```powershell
git diff v0.1.0 -- README.md
```

確認 Personal Skill 安裝仍使用 `$env:USERPROFILE\.agents\skills`，並保留「通常自動偵測，必要時重新啟動」的說明。

- [ ] **Step 5: 執行完整驗證**

```powershell
py -3 -m unittest discover -s tests -v
skills-ref validate clean-code-ai-collaboration
git diff --check
```

Expected: 全部 PASS；README 相對連結存在，UTF-8 無 Replacement Character。

- [ ] **Step 6: Commit Public Documentation**

```powershell
git add README.md tests/test_skill_contract.py
git diff --cached --check
git diff --cached
git commit -m "docs: explain cross-platform use and benchmark evidence"
```

---

### Task 9: Release Readiness Review

**Files:**
- Verify only; modify the smallest responsible file only if a failing Gate exposes a real defect.

**Interfaces:**
- Consumes: Tasks 1 至 8 的 Commits。
- Produces: 可供 User 決定是否 Push、Tag 或發布 `v0.2.0` 的完整狀態。

- [ ] **Step 1: 執行全部本機 Gate**

```powershell
py -3 -m unittest discover -s tests -v
skills-ref validate clean-code-ai-collaboration
git diff --check
git status --short
```

Expected: Tests 與 Validator PASS；除 User 已知且已整合的變更外，工作目錄乾淨。

- [ ] **Step 2: 檢查版本與公開封裝一致性**

```powershell
rg -n '0\.1\.0|0\.2\.0|clean-code-ai-collaboration|\.agents\\skills' README.md clean-code-ai-collaboration tests evals
```

確認 Current Version、Metadata、Result 與 README 都使用 `0.2.0`；`v0.1.0` 只出現在歷史比較與 Baseline。

- [ ] **Step 3: 檢查 Secret、暫存資料與不可公開路徑**

```powershell
git diff v0.1.0 -- .
git status --short --ignored
rg -n 'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|D:\\Project\\Kcislk' .
```

Expected: 沒有 Secret、雇主內部路徑、未追蹤 Raw Worktree 或 `__pycache__` 被納入 Commit。正常文章／文件文字命中需人工判讀，不能只靠 Match Count。

- [ ] **Step 4: Review Commit Boundaries 與 Remote 狀態**

```powershell
git log --oneline --decorate v0.1.0..HEAD
git diff --stat v0.1.0..HEAD
git rev-list --left-right --count HEAD...@{u}
```

確認 Design、Plan、Eval Contract、Baseline、Skill Core、References、Adapter、CI、Benchmark 與 README 的 Commit 可獨立 Review。

- [ ] **Step 5: 停在發布授權前**

回報：

- 已通過 Gate。
- Benchmark 支持與不支持的能力。
- 尚未驗證的 Client 或 Repository。
- Local／Remote Divergence。
- 建議 Release Version 與 Tag。

未取得 User 明確指示前，不執行 `git push`、`git tag`、GitHub Release 或外部宣傳。
