# Clean Code AI Collaboration Cross-Language Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立四個小型 TypeScript／React 與 Python／FastAPI Fixture、可重現的本機 Codex Benchmark Harness，以及 36 次匿名評測結果，為 `clean-code-ai-collaboration v0.3.0` 產生第一份跨語言初步證據。

**Architecture:** Fixture 與 Hidden Evaluator 存放在獨立公開 Repository；每次 Run 只匯出單一 Subject Fixture 到獨立 Git 工作區。Skill Repository 保存版本化 Manifest、Planner、Desktop Subject stage／collect Protocol、Oracle Runner、匿名 Review Packet 與公開 Result。Dispatch、Report、Attempt Receipt 與 Workspace 留在 Git 忽略的 `.benchmark-runs/`；Desktop 不產生可由 Harness 取得的 JSONL，Telemetry 明確標示 `not_available`。

**Tech Stack:** Python 3.12+ 標準函式庫與 `unittest`、Codex Desktop collaboration SubAgent、`gpt-5.6-sol`／`high`、Git、Node.js 24、React 19、TypeScript 6、Vitest 4、Testing Library、ESLint 10、FastAPI 0.141、Pydantic 2.13、pytest 9、Ruff 0.16。

**Spec:** `docs/superpowers/specs/2026-09-01-cross-language-benchmark-design.md`

## Global Constraints

- Benchmark 版本固定為 `0.3.0-cross-language-desktop-subject-v3`；Fixture Tag 固定為 `cross-language-v3`；Skill 固定使用已發布的 `v0.3.0`，不得改用工作目錄中的新版本。
- 主要比較只有 TypeScript／React 與 Python／FastAPI；既有 .NET 結果只作歷史參考；Java／Spring 不進入本次執行。
- 固定 4 個 Scenario、3 個 Arm、3 次 Repetition，共 36 個 Fresh Context Session；Pilot 先跑 12 次，契約不變才計入正式結果。
- Model 固定為 `gpt-5.6-sol`，Reasoning Effort 固定為 `high`，Subject 由 Codex Desktop collaboration 的 Fresh Context SubAgent 執行；Harness 只負責 Stage／Collect，不啟動 nested CLI。
- Agent Session 上限 480 秒，Fixture 準備上限 120 秒，Oracle 上限 120 秒；Agent Timeout、功能失敗或品質不佳不自動重跑。
- 只有 Harness、Desktop 編排、套件快取或明確基礎環境故障可重跑一次；原始失敗必須保留。
- Desktop 的 Sandbox、網路與 Tool／Token Telemetry 無法由 Harness 強制或驗證，固定為 `not_available`；不得把 Desktop 執行條件誤報為 CLI `workspace-write` Sandbox。
- Baseline 公開 Gate 與 Preservation Oracle 必須通過；Acceptance Oracle 必須因預期需求缺口呈現 RED；候選完成後三者都必須通過。
- Automatic Failure、三份 Rubric 與成本資料分開報告；不得建立跨維度總分或「勝率」。
- Token、Tool Call 或時間 Telemetry 無法可靠取得時記為 `not_available`；不得用輸出字數推估 Token。
- Fixture、Prompt、Oracle、Diff Boundary、Rubric 或評分方式在 Pilot 後若改變，該 Fixture 三個 Arm 的 Pilot 全部作廢。
- 四個 Fixture 使用虛構資料；所有公開 Prompt、Diff 與錯誤輸出都要通過 Secret 與個人路徑掃描。
- Benchmark 建立的 Run 工作區與原始證據先保留，不自動批次刪除；需要清理時另列明確路徑並取得授權。
- 每個程式 Task 都先完成 RED，再做最小 GREEN、完整回歸與 Conventional Commit。
- 建立公開 Repository、Push、Tag、Release Asset 與執行 36 次 Session 都是明列的外部操作；只在對應 Task 到達且前置 Gate 通過後執行。

## 2026-09-01 Desktop Subject Protocol v3（首輪 Pilot 已稽核作廢）

Desktop 內 nested Codex CLI 的 Workspace 寫入已實機確認會被強制唯讀，因此原先
CLI Subject Runner 不可作為正式跨語言評測執行器。以下流程取代本計畫後續所有
`pilot`／`full` 直接啟動 Subject 的指令；舊 CLI Evidence 與既有 Invalidation 保留，
不覆寫也不重新解釋。

1. 先通過既有 Baseline Preflight，然後執行：

   ```powershell
   py -3 -m evals.harness.cli stage --phase pilot --run-id <logical-run-id>
   ```

   Stage 建立唯一 Workspace、Prompt、已預填不可變欄位的
   `subject-report.template.json`、Controller-only Dispatch 和 Controller-only Dispatch Index。它們都不可覆寫，並綁定
   Benchmark／Scenario／Prompt Hash、Baseline Commit、Generation、Attempt 與實體 Run ID。

2. 外層 Sol 編排者以 fresh context 啟動一個 `gpt-5.6-sol`／`high` Desktop
   collaboration SubAgent。SubAgent 可在外層指令指定的 Workspace 讀寫任務所需檔案；
   Workspace 外只有 staged Prompt 與 Report Template 兩個明確路徑會交付給 Subject。
   Controller Dispatch 路徑不寫入 Subject instruction，避免主動洩漏 Arm 與 treatment metadata。
   若 Prompt 要求 Skill，只能讀取 Workspace 中 staged 的固定版本。完成後在 Workspace
   根目錄寫入 ignored 的
   `.benchmark-subject-report.json`。Report 的檔案欄位只接受 Workspace-relative POSIX
   path；外部 staged 檔案不得列入。Report 是交接資料，不是驗收證據。

3. 編排者帶回完成、Timeout 或 Infrastructure Failure 狀態，再執行：

   ```powershell
   py -3 -m evals.harness.cli collect --dispatch-id <dispatch-id> --outcome <completed|timeout|infrastructure_failure>
   ```

   Collect 重新驗證 Dispatch／Prompt／Benchmark／Scenario Hash、實際 Git Baseline、
   Generation、Attempt 與 Report；接著由 Harness 擷取 Diff 並重跑獨立 Oracle。Report
   遺漏／不完整標為 `candidate_incomplete`，Hash、Baseline 或自行 Commit 不符標為
   `invalid_claim`，兩者都直接 Automatic Failure 且不可重跑。超過 480 秒的回報一律列為
   Timeout。第一個明確 Infrastructure Failure 可以產生第二次 Attempt；Timeout 與候選失敗不可重跑。

4. `pilot` 與 `full` 現在刻意 fail closed，訊息會要求使用上述 stage／外部
   SubAgent／collect 順序，絕不自動退回 nested CLI。正式 Pilot、Capability Probe
   與 Full Run 必須由主責代理在這份實作通過驗收後另行授權。

5. 匿名 Packet 與公開 Result 不得包含 Dispatch ID、Thread ID、完整 Report 或絕對
   Workspace 路徑。Desktop 無法可靠取得的網路強制、Token、Tool Call 與檔案查閱
   telemetry 固定為 `not_available`，不得推估；JSONL 不作為 Desktop 流程的 Evidence 要求。

6. 首輪 Pilot 使用的 `cross-language-v1` 與 Desktop Subject Protocol v2 已完整作廢；
   第二輪 `cross-language-v2` 又因盲審找到 React Effect Acceptance Oracle 漏測而不得 Freeze。
   修正版 Fixture v3 與 Protocol v3 先在本機完成驗證；只有 `cross-language-v3` 的
   Annotated Tag 推送到公開 Fixture Repository，且 Manifest 能由遠端解析到相同 Commit
   後，才可重新執行 12 組 Pilot。`prepare` 必須對既有 Fixture Cache 明確 fetch 指定 Tag，
   再驗證 dereferenced Tag 與 Manifest Commit 完全相同；不能因 Cache 已存在就跳過更新。

> **隔離限制：** Desktop collaboration 沒有提供可由 Harness 證明的 OS ACL 或獨立帳號
> Sandbox。Protocol v3 能驗證的是 Subject-visible Prompt、Instruction 與 staged artifacts
> 沒有主動揭露額外 treatment metadata；不能宣稱 Subject 在檔案系統層級絕對無法掃描其他
> 路徑。公開結果必須保留這項限制，並與人工 Reviewer 的匿名 Packet 分開描述。

> **Follow-up（未納入本次修正）：** Result Builder 目前維持既有公開結果欄位；待完成
> Capability Probe／Pilot 後，再決定是否以不洩漏 Dispatch 的方式揭露 Desktop Protocol
> 執行中繼資料。此項不影響本次 stage／collect 的 fail-closed 契約。

## File Map

### `Clean-Code-AI-Collaboration-Benchmark-Fixtures`

| Path | Responsibility |
| --- | --- |
| `README.md` | Fixture 目的、執行方式、Baseline RED／GREEN 契約與限制 |
| `.github/workflows/validate.yml` | 在 Node 24 與 Python 3.12 重跑四個 Fixture 契約 |
| `fixture-contract.json` | 四個 Scenario、Subject 目錄、Evaluator 目錄與命令的唯一索引 |
| `tools/validate_fixtures.py` | 驗證公開 Gate、Preservation Green、Acceptance Red 與 Mutation Detection |
| `tests/test_fixture_contract.py` | Fixture 索引、路徑隔離與命令分類的結構測試 |
| `fixtures/react-overdue-rule/**` | React 共同業務規則 Subject Fixture |
| `evaluators/react-overdue-rule/**` | React 共同業務規則的 Preservation、Acceptance 與 Mutation |
| `fixtures/react-effect-lifecycle/**` | React Effect／Cancellation Subject Fixture |
| `evaluators/react-effect-lifecycle/**` | React Effect 情境的 Preservation、Acceptance 與 Mutation |
| `fixtures/fastapi-overdue-rule/**` | FastAPI 共同業務規則 Subject Fixture |
| `evaluators/fastapi-overdue-rule/**` | FastAPI 共同業務規則的 Preservation、Acceptance 與 Mutation |
| `fixtures/fastapi-provider-boundary/**` | FastAPI Protocol／Dependency Injection Subject Fixture |
| `evaluators/fastapi-provider-boundary/**` | FastAPI Provider 邊界的 Preservation、Acceptance 與 Mutation |

### `Clean-Code-AI-Collaboration-Skill`

| Path | Responsibility |
| --- | --- |
| `evals/manifests/v0.3.0-cross-language.json` | 固定 Fixture、Arm、Prompt、模型、Timeout、Oracle 與 Result 必填欄位 |
| `evals/harness/models.py` | RunSlot、CommandResult、Workspace、Desktop SubjectDispatch、SubjectObservation、DiffEvidence 與 OracleEvidence 型別 |
| `evals/harness/manifest.py` | Manifest 載入與 Fail-closed 驗證 |
| `evals/harness/planner.py` | 36 個唯一 Slot 與固定 Seed 打散順序 |
| `evals/harness/process.py` | 無 Shell 字串插值的命令執行與 Timeout 分類 |
| `evals/harness/fixture_builder.py` | 匯出單一 Fixture、安裝固定依賴、建立 Baseline Commit 與 Skill Arm |
| `evals/harness/subject_runner.py` | 建立所有 Arm 共用的已授權實作 Prompt；保留歷史 CLI Evidence／測試相容性 |
| `evals/harness/desktop_subject.py` | Stage 不可覆寫 Dispatch、提供外部 Desktop SubAgent 指令、驗證 ignored Report 與保存 immutable Attempt Receipt |
| `evals/harness/diff_boundary.py` | 擷取新增、修改、刪除、重新命名與允許範圍 |
| `evals/harness/oracle_runner.py` | 注入 Evaluator 後重跑公開 Gate、Preservation 與 Acceptance |
| `evals/harness/evidence_recorder.py` | 保存 Desktop Dispatch／Report Hash、Git Status、Diff、可取得的時間與 Terminal State；不可取得欄位為 `not_available` |
| `evals/harness/anonymizer.py` | 建立 Reviewer 看不出 Arm 的候選識別碼與私有映射 |
| `evals/harness/result_builder.py` | 驗證 36 個 Terminal State，恢復 Arm 並產生公開 Result |
| `evals/harness/cli.py` | `prepare`、fail-closed `pilot`／`full`、`stage`、`collect`、`review-packets`、`build-result` 入口 |
| `tests/test_cross_language_harness.py` | Harness 單元與契約測試 |
| `evals/results/v0.3.0-cross-language.json` | 完成 36 次 Run 與匿名審查後的公開結果 |
| `evals/benchmark.md` | 執行方法、觀察、推論、未知、失敗與限制 |
| `README.md` | 連結新 Result，保留小型初步證據的主張邊界 |

---

### Task 1: 建立 Fixture Repository 的可驗證契約

**Files:**
- Create in sibling repository: `README.md`
- Create in sibling repository: `LICENSE`
- Create in sibling repository: `.gitignore`
- Create in sibling repository: `fixture-contract.json`
- Create in sibling repository: `tools/validate_fixtures.py`
- Create in sibling repository: `tests/test_fixture_contract.py`

**Interfaces:**
- Consumes: 設計規格中的四個 Scenario ID 與 Baseline／Preservation／Acceptance 區分。
- Produces: `FixtureContract.load(root: Path) -> FixtureContract` 與 `validate_fixture(root: Path, fixture_id: str) -> FixtureValidation`，後續四個 Fixture 共用。Command Array 中的 `{python}` 是正式 Token，由 Validator 依 Windows 的 `.venv/Scripts/python.exe` 或 POSIX 的 `.venv/bin/python` 解析，不交給 Shell 展開。

- [ ] **Step 1: 初始化本機 sibling Repository，不建立遠端**

建立 sibling 目錄 `../Clean-Code-AI-Collaboration-Benchmark-Fixtures`，執行：

```powershell
git init --initial-branch=main
git config user.name "Huang Chi-Yu"
git config user.email "eric861129@users.noreply.github.com"
```

Expected: `git status --short --branch` 顯示 `No commits yet on main`；此步不呼叫 `gh repo create`。

- [ ] **Step 2: 先寫 Fixture Contract RED Test**

建立 `tests/test_fixture_contract.py`，核心測試固定為：

```python
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = {
    "react-overdue-rule",
    "react-effect-lifecycle",
    "fastapi-overdue-rule",
    "fastapi-provider-boundary",
}


class FixtureContractTests(unittest.TestCase):
    def test_contract_lists_four_isolated_fixtures(self) -> None:
        contract = json.loads(
            (ROOT / "fixture-contract.json").read_text(encoding="utf-8")
        )
        fixtures = {item["id"]: item for item in contract["fixtures"]}
        self.assertEqual(EXPECTED_IDS, set(fixtures))
        for fixture_id, fixture in fixtures.items():
            subject = ROOT / fixture["subject_path"]
            evaluator = ROOT / fixture["evaluator_path"]
            self.assertTrue(subject.is_dir(), fixture_id)
            self.assertTrue(evaluator.is_dir(), fixture_id)
            self.assertNotEqual(subject, evaluator)
            self.assertNotIn("evaluators", subject.parts)
            self.assertEqual(
                {"public", "preservation", "acceptance", "mutation"},
                set(fixture["commands"]),
            )

    def test_subject_trees_do_not_contain_evaluator_files(self) -> None:
        for path in (ROOT / "fixtures").rglob("*"):
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("benchmark-oracle", path.as_posix())
                self.assertNotIn("ACCEPTANCE_ORACLE_ONLY", content)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 執行 RED**

```powershell
py -3 -m unittest discover -s tests -v
```

Expected: FAIL，原因是 `fixture-contract.json` 與四個目錄尚不存在；不能是編碼或 Python Syntax Error。

- [ ] **Step 4: 建立最小 Root Contract 與 Validator 型別**

`fixture-contract.json` 使用以下固定頂層結構；每個 Fixture Task 只填入自己的命令與路徑：

```json
{
  "schema_version": "1.0",
  "fixture_version": "cross-language-v3",
  "fixtures": []
}
```

`tools/validate_fixtures.py` 定義：

```python
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class CommandObservation:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class FixtureValidation:
    fixture_id: str
    public_green: bool
    preservation_green: bool
    acceptance_red: bool
    mutation_detected: bool


@dataclass(frozen=True)
class FixtureDefinition:
    id: str
    runtime: str
    subject_path: str
    evaluator_path: str
    commands: dict[str, tuple[tuple[str, ...], ...]]
    expected_baseline_red_markers: tuple[str, ...]


@dataclass(frozen=True)
class FixtureContract:
    schema_version: str
    fixture_version: str
    fixtures: tuple[FixtureDefinition, ...]

    @classmethod
    def load(cls, root: Path) -> "FixtureContract":
        raw = json.loads(
            (root / "fixture-contract.json").read_text(encoding="utf-8")
        )
        fixtures = tuple(
            FixtureDefinition(
                id=item["id"],
                runtime=item["runtime"],
                subject_path=item["subject_path"],
                evaluator_path=item["evaluator_path"],
                commands={
                    kind: tuple(tuple(command) for command in commands)
                    for kind, commands in item["commands"].items()
                },
                expected_baseline_red_markers=tuple(
                    item["expected_baseline_red_markers"]
                ),
            )
            for item in raw["fixtures"]
        )
        return cls(raw["schema_version"], raw["fixture_version"], fixtures)


def run_command(command: list[str], cwd: Path) -> CommandObservation:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return CommandObservation(
        tuple(command), completed.returncode, completed.stdout, completed.stderr
    )


def python_executable(subject_root: Path) -> Path:
    windows = subject_root / ".venv" / "Scripts" / "python.exe"
    return windows if windows.exists() else subject_root / ".venv" / "bin" / "python"
```

`validate_fixture` 解析 Contract 中的 Subject／Evaluator，複製到獨立 Validation Workspace，把 Evaluator 放入 `.benchmark-oracle`，將 `{python}` Token 換成 `python_executable(...)` 的絕對路徑，再依 Public、Preservation、Acceptance、Mutation 順序產生 `FixtureValidation`。

Validator 必須以 JSON command array 執行，不接受拼接後的 Shell 字串；Acceptance 只有在 Exit Code 非 0 且輸出包含 Fixture 宣告的 `expected_baseline_red_markers` 時才算預期 RED。

- [ ] **Step 5: 建立 README、MIT LICENSE 與忽略規則**

`.gitignore` 至少包含：

```gitignore
node_modules/
.venv/
.pytest_cache/
.ruff_cache/
__pycache__/
*.pyc
.benchmark-oracle/
.fixture-validation-runs/
```

README 明確說明：Subject 只取得 `fixtures/{fixture_id}`；Evaluator 在 Session 後才注入；公開 Gate／Preservation 在 Baseline 必須 Green；Acceptance 在 Baseline 必須因指定需求缺口 Red。

- [ ] **Step 6: 暫時建立四個空 Subject／Evaluator 目錄標記並讓結構測試通過**

每個目錄加入 `.gitkeep`，並在 `fixture-contract.json` 建立四筆 ID、路徑與空的四種 command array。這只讓結構測試 Green；Task 2～5 會逐筆加入「命令不可為空」測試後再實作 Fixture。

- [ ] **Step 7: 執行 GREEN 並 Commit Root Contract**

```powershell
py -3 -m unittest discover -s tests -v
git add README.md LICENSE .gitignore fixture-contract.json tools tests fixtures evaluators
git diff --cached --check
git diff --cached
git commit -m "test(fixtures): define cross-language fixture contract"
```

---

### Task 2: 建立 React High Priority 逾期規則 Fixture

**Files:**
- Create: `fixtures/react-overdue-rule/package.json`
- Create: `fixtures/react-overdue-rule/package-lock.json`
- Create: `fixtures/react-overdue-rule/tsconfig.json`
- Create: `fixtures/react-overdue-rule/eslint.config.js`
- Create: `fixtures/react-overdue-rule/AGENTS.md`
- Create: `fixtures/react-overdue-rule/src/workItem.ts`
- Create: `fixtures/react-overdue-rule/src/overdue.ts`
- Create: `fixtures/react-overdue-rule/src/WorkItemList.tsx`
- Create: `fixtures/react-overdue-rule/src/overdue.public.test.tsx`
- Create: `evaluators/react-overdue-rule/preservation.test.tsx`
- Create: `evaluators/react-overdue-rule/acceptance.test.ts`
- Create: `evaluators/react-overdue-rule/completed-status.patch`
- Modify: `fixture-contract.json`
- Modify: `tests/test_fixture_contract.py`

**Interfaces:**
- Produces: `isOverdue(item: WorkItem, now: Date): boolean` 與 `WorkItemList({ items, now }): JSX.Element`。
- Oracle contract: Normal Priority 到期即逾期；Completed 永不逾期；High Priority 在 `dueAtUtc + 2h <= now` 才逾期。

- [ ] **Step 1: 寫命令完整性 RED Test**

在 Root Contract Test 增加：

```python
def test_react_overdue_commands_are_executable_arrays(self) -> None:
    contract = json.loads(
        (ROOT / "fixture-contract.json").read_text(encoding="utf-8")
    )
    fixture = next(
        item for item in contract["fixtures"]
        if item["id"] == "react-overdue-rule"
    )
    for command_kind, commands in fixture["commands"].items():
        with self.subTest(command_kind=command_kind):
            self.assertTrue(commands)
            self.assertTrue(all(isinstance(command, list) for command in commands))
```

Run: `py -3 -m unittest tests.test_fixture_contract -v`

Expected: FAIL，因四種命令目前為空。

- [ ] **Step 2: 建立固定 Node 專案與 Baseline Code**

`package.json` 固定依賴版本：React／React DOM `19.2.8`、TypeScript `6.0.3`、Vite `8.2.2`、Vitest `4.1.11`、Testing Library React `16.3.3`、Jest DOM `7.0.1`、ESLint `10.9.1`、typescript-eslint `8.69.0`、jsdom `30.0.1`。TypeScript 固定在 `6.0.3`，因 `typescript-eslint 8.69.0` 的 Peer Dependency 上限為 `<6.1.0`；Benchmark 不使用 `--force` 或 `--legacy-peer-deps` 繞過工具鏈契約。Scripts 固定為：

```json
{
  "test": "vitest run",
  "typecheck": "tsc --noEmit",
  "lint": "eslint ."
}
```

`package.json` 寫入後執行 `npm install --package-lock-only --ignore-scripts --no-audit --no-fund` 產生固定 Lockfile，接著才使用 `npm ci` 驗證。Lockfile 是 Fixture 契約的一部分，不手動編輯。

`src/workItem.ts`：

```typescript
export type WorkItemPriority = "Normal" | "High";
export type WorkItemStatus = "Open" | "Completed";

export interface WorkItem {
  id: string;
  title: string;
  priority: WorkItemPriority;
  status: WorkItemStatus;
  dueAtUtc: string;
}
```

`src/overdue.ts` 的 Baseline：

```typescript
import type { WorkItem } from "./workItem";

export function isOverdue(item: WorkItem, now: Date): boolean {
  return (
    item.status !== "Completed" &&
    new Date(item.dueAtUtc).getTime() <= now.getTime()
  );
}
```

`WorkItemList.tsx` 只使用 `isOverdue` 篩選並顯示 Title，不複製規則。

- [ ] **Step 3: 建立公開測試、Preservation 與 Acceptance Oracle**

公開測試驗證 Normal 到期與 Completed 排除；`preservation.test.ts` 再鎖定 `WorkItemList` Props 與顯示內容。`acceptance.test.ts` 使用固定時間：

```typescript
import { describe, expect, it } from "vitest";
import { isOverdue } from "../src/overdue";
import type { WorkItem } from "../src/workItem";

const high: WorkItem = {
  id: "W-100",
  title: "Review payment",
  priority: "High",
  status: "Open",
  dueAtUtc: "2026-09-01T08:00:00Z",
};

describe("High Priority grace period", () => {
  it("is not overdue one minute before the two-hour boundary", () => {
    expect(isOverdue(high, new Date("2026-09-01T09:59:00Z"))).toBe(false);
  });

  it("is overdue exactly at the two-hour boundary", () => {
    expect(isOverdue(high, new Date("2026-09-01T10:00:00Z"))).toBe(true);
  });
});
```

`AGENTS.md` 只描述執行命令、公開 Contract 與禁止改動範圍，不提 Skill 或答案。

- [ ] **Step 4: 固定 Fixture Commands 與 Mutation**

四種命令固定為：

```json
{
  "public": [["npm", "test", "--", "src/overdue.public.test.tsx"], ["npm", "run", "typecheck"], ["npm", "run", "lint"]],
  "preservation": [["npm", "test", "--", ".benchmark-oracle/preservation.test.tsx"]],
  "acceptance": [["npm", "test", "--", "--reporter=verbose", ".benchmark-oracle/acceptance.test.ts"]],
  "mutation": [["git", "apply", ".benchmark-oracle/completed-status.patch"], ["npm", "test", "--", ".benchmark-oracle/preservation.test.tsx"]]
}
```

`completed-status.patch` 只把 `item.status !== "Completed"` 改成 `true`；Preservation 必須因此失敗。Validator 在 `.fixture-validation-runs/{fixture_id}/{validation_run_id}` 建立工作區副本，不能在來源 Fixture 上套 Patch，也不自動批次刪除驗證工作區。

- [ ] **Step 5: 驗證 Baseline Green／Expected RED／Mutation Detection**

```powershell
npm ci --prefix fixtures/react-overdue-rule --no-audit --no-fund
py -3 tools/validate_fixtures.py react-overdue-rule
```

Expected: Public Green、Preservation Green、Acceptance Red，且 Red 輸出同時包含兩個 High Priority test name；Mutation Detected 為 `true`。

- [ ] **Step 6: Commit React 共同規則 Fixture**

```powershell
git add fixtures/react-overdue-rule evaluators/react-overdue-rule fixture-contract.json tests/test_fixture_contract.py
git diff --cached --check
git diff --cached
git commit -m "feat(fixtures): add React overdue-rule scenario"
```

---

### Task 3: 建立 React Effect Lifecycle Fixture

**Files:**
- Create: `fixtures/react-effect-lifecycle/**`
- Create: `evaluators/react-effect-lifecycle/**`
- Modify: `fixture-contract.json`
- Modify: `tests/test_fixture_contract.py`

**Interfaces:**
- Produces: `WorkItemPreview` 與 `LoadPreview = (id: string, signal: AbortSignal) => Promise<Preview>`。
- Oracle contract: 相同 ID 的 ordinary rerender 不重送請求；ID 改變會取消舊請求並送新請求；Loading、Error、Props 與 Response 顯示不漂移。

- [ ] **Step 1: 複製相同 Node Toolchain，但不要共用 Source**

使用 Task 2 相同固定依賴與 Scripts，各 Fixture 保有自己的 `package-lock.json`、`tsconfig.json`、ESLint 與 `AGENTS.md`。寫入 `package.json` 後同樣執行 `npm install --package-lock-only --ignore-scripts --no-audit --no-fund`。Root Test 必須檢查兩個 React Fixture 的 Lockfile SHA 不為空，且 Subject Tree 不含 Evaluator。

- [ ] **Step 2: 寫 Effect Baseline 與公開測試**

Baseline Component 已具備 AbortController，但錯把只影響顯示密度的 `density` 放進請求 Effect Dependency；因此 Parent 以同一個 ID 切換 UI 密度時會重送。這能穩定重現 ordinary rerender，又不會因 Effect 內部更新 State 形成無限迴圈：

```typescript
export type Preview = { id: string; summary: string };
export type LoadPreview = (
  id: string,
  signal: AbortSignal,
) => Promise<Preview>;

export function WorkItemPreview({ workItemId, density, loadPreview }: Props) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    void loadPreview(workItemId, controller.signal)
      .then((preview) => setState({ kind: "ready", preview }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ kind: "error", message: String(error) });
        }
      });
    return () => controller.abort();
  }, [density, loadPreview, workItemId]);

  return <section data-density={density}>{renderState(state)}</section>;
}
```

`Props` 固定含 `density: "compact" | "comfortable"`。公開測試鎖定 Loading、成功內容與 Error；Preservation Oracle 鎖定密度仍正確顯示，以及 ID 改變時第一個 Signal 被 Abort、第二個 ID 確實送出。

- [ ] **Step 3: 寫 Acceptance Oracle**

```typescript
it("does not request the same preview again on an ordinary rerender", async () => {
  const loadPreview = vi.fn().mockResolvedValue({ id: "W-1", summary: "Ready" });
  const view = render(
    <WorkItemPreview
      workItemId="W-1"
      density="compact"
      loadPreview={loadPreview}
    />,
  );
  await screen.findByText("Ready");
  view.rerender(
    <WorkItemPreview
      workItemId="W-1"
      density="comfortable"
      loadPreview={loadPreview}
    />,
  );
  expect(loadPreview).toHaveBeenCalledTimes(1);
});
```

測試不要用 React StrictMode 當唯一重現方式，因為本情境要測 ordinary rerender，不把開發模式的刻意雙重 Effect 混入變因。

- [ ] **Step 4: 建立 Cancellation Mutation**

Mutation Patch 只移除 Cleanup 的 `controller.abort()`；Preservation Oracle 必須因 ID 改變後舊 Signal 沒被取消而失敗。Acceptance Baseline 必須因相同 ID 呼叫兩次而失敗。

- [ ] **Step 5: 驗證並 Commit**

```powershell
npm ci --prefix fixtures/react-effect-lifecycle --no-audit --no-fund
py -3 tools/validate_fixtures.py react-effect-lifecycle
py -3 -m unittest discover -s tests -v
git add fixtures/react-effect-lifecycle evaluators/react-effect-lifecycle fixture-contract.json tests/test_fixture_contract.py
git diff --cached --check
git diff --cached
git commit -m "feat(fixtures): add React effect-lifecycle scenario"
```

Expected: Public／Preservation Green、Acceptance Red、Mutation Detected。

---

### Task 4: 建立 FastAPI High Priority 逾期規則 Fixture

**Files:**
- Create: `fixtures/fastapi-overdue-rule/pyproject.toml`
- Create: `fixtures/fastapi-overdue-rule/requirements.lock`
- Create: `fixtures/fastapi-overdue-rule/AGENTS.md`
- Create: `fixtures/fastapi-overdue-rule/app/__init__.py`
- Create: `fixtures/fastapi-overdue-rule/app/models.py`
- Create: `fixtures/fastapi-overdue-rule/app/overdue.py`
- Create: `fixtures/fastapi-overdue-rule/app/main.py`
- Create: `fixtures/fastapi-overdue-rule/tests/test_public_api.py`
- Create: `evaluators/fastapi-overdue-rule/test_preservation.py`
- Create: `evaluators/fastapi-overdue-rule/test_acceptance.py`
- Create: `evaluators/fastapi-overdue-rule/completed-status.patch`
- Modify: `fixture-contract.json`
- Modify: `tests/test_fixture_contract.py`

**Interfaces:**
- Produces: `is_overdue(item: WorkItem, now: datetime) -> bool` 與 `POST /overdue` 的固定 Response Model。
- Oracle contract: 與 React 共同規則完全一致，另鎖定 HTTP Status、JSON 欄位與順序無關的 ID 集合。

- [ ] **Step 1: 固定 Python 依賴與 Ruff 契約**

`requirements.lock`：

```text
fastapi==0.141.1
httpx==0.28.1
pydantic==2.13.5
pytest==9.1.1
ruff==0.16.5
uvicorn==0.52.4
```

`pyproject.toml` 固定 Python `>=3.12`、Ruff line length `88`，測試路徑為 `tests`。不加入 mypy，因本 Fixture 的小型 Protocol 與 Pydantic 型別已可由測試和 Ruff 覆蓋，避免額外樣板成為主要成本。

- [ ] **Step 2: 建立 Baseline Model、規則與 API**

`app/overdue.py` Baseline：

```python
from datetime import datetime

from app.models import WorkItem


def is_overdue(item: WorkItem, now: datetime) -> bool:
    return item.status != "Completed" and item.due_at_utc <= now
```

`POST /overdue` 接收 `items` 與 `now`，回傳 `{"overdue_ids": [...]}`；使用 Pydantic Request／Response Model，Route 只呼叫 `is_overdue`，不複製規則。

- [ ] **Step 3: 寫 Public、Preservation 與 Acceptance Test**

Public／Preservation 鎖定 HTTP `200`、`overdue_ids` 欄位、Normal Priority 與 Completed。Acceptance：

```python
def test_high_priority_waits_until_two_hour_boundary() -> None:
    item = WorkItem(
        id="W-100",
        title="Review payment",
        priority="High",
        status="Open",
        due_at_utc=datetime.fromisoformat("2026-09-01T08:00:00+00:00"),
    )
    assert not is_overdue(
        item, datetime.fromisoformat("2026-09-01T09:59:00+00:00")
    )
    assert is_overdue(
        item, datetime.fromisoformat("2026-09-01T10:00:00+00:00")
    )
```

- [ ] **Step 4: 固定命令與 Mutation**

Public commands：`python -m pytest -q tests`、`python -m ruff check .`、`python -m ruff format --check .`；Evaluator commands 指向 `.benchmark-oracle/test_preservation.py` 與 `test_acceptance.py`。Mutation 移除 Completed Guard，Preservation 必須失敗。

- [ ] **Step 5: 驗證並 Commit**

```powershell
py -3 -m venv fixtures/fastapi-overdue-rule/.venv
fixtures/fastapi-overdue-rule/.venv/Scripts/python -m pip install -r fixtures/fastapi-overdue-rule/requirements.lock
py -3 tools/validate_fixtures.py fastapi-overdue-rule
py -3 -m unittest discover -s tests -v
git add fixtures/fastapi-overdue-rule evaluators/fastapi-overdue-rule fixture-contract.json tests/test_fixture_contract.py
git diff --cached --check
git diff --cached
git commit -m "feat(fixtures): add FastAPI overdue-rule scenario"
```

---

### Task 5: 建立 FastAPI Provider Boundary Fixture

**Files:**
- Create: `fixtures/fastapi-provider-boundary/**`
- Create: `evaluators/fastapi-provider-boundary/**`
- Modify: `fixture-contract.json`
- Modify: `tests/test_fixture_contract.py`
- Create: `.github/workflows/validate.yml`

**Interfaces:**
- Produces: `NotificationSender` Protocol、`notify_work_item(item, sender) -> bool` 與 `POST /work-items/{id}/notifications`。
- Oracle contract: 使用既有 Protocol 與 FastAPI Dependency Override 替換 Provider；保留 `202`、`404`、`502` 與 Exception 語意；不得建立第二套 Domain Model 或同義 Protocol。

- [ ] **Step 1: 建立 Baseline，保留可觀察的依賴缺口**

`app/notifications.py` 已定義：

```python
class NotificationSender(Protocol):
    def send(self, work_item: WorkItem) -> bool: ...


class ConsoleNotificationSender:
    def send(self, work_item: WorkItem) -> bool:
        return work_item.id != "W-FAIL"
```

`app/use_case.py` 接受 `NotificationSender`；Baseline Route 卻直接建立 `ConsoleNotificationSender()`。Public Tests 鎖定 `404`、成功 `202` 與 Provider `false` 時的 `502`，可透過 `monkeypatch` 替換 Route Module 的 Class 保留既有失敗語意。

- [ ] **Step 2: 寫 Acceptance Oracle，要求 Framework-native DI**

Acceptance Oracle 先從 Route Module 讀取候選應新增的 `get_notification_sender`，使用：

```python
from fastapi.testclient import TestClient

from app import main as main_module
from app.models import WorkItem


app = main_module.app


class StubSender:
    def __init__(self, result: bool) -> None:
        self.result = result
        self.calls: list[str] = []

    def send(self, work_item: WorkItem) -> bool:
        self.calls.append(work_item.id)
        return self.result


def test_route_uses_fastapi_dependency_override() -> None:
    sender = StubSender(result=True)
    dependency = getattr(main_module, "get_notification_sender", None)
    assert dependency is not None, "get_notification_sender is required"
    app.dependency_overrides[dependency] = lambda: sender
    try:
        response = TestClient(app).post("/work-items/W-1/notifications")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert sender.calls == ["W-1"]
```

Baseline 應因 `get_notification_sender is required` 呈現 RED；Subject 的任務明確指出 Protocol 已存在，不得新增第二個介面。

- [ ] **Step 3: 建立 Failure-Semantics Mutation**

Mutation 只把 Provider `false` 的 HTTP `502`／`{"detail": "notification_failed"}` 改成 `202`；Preservation Oracle 必須抓到。另一個 Preservation Case 固定 Provider Exception 為 HTTP `503`／`{"detail": "provider_unavailable"}`，避免 Agent 在導入 DI 時順手改變失敗語意。

- [ ] **Step 4: 建立跨平台 Fixture CI**

Workflow 使用 Node `24`、Python `3.12`，分別安裝兩個 React Lockfile 與兩個 FastAPI `requirements.lock`，最後執行：

```yaml
- name: Validate fixture contracts
  run: python tools/validate_fixtures.py --all
- name: Validate repository tests
  run: python -m unittest discover -s tests -v
```

Acceptance Baseline RED 由 Validator 轉成「符合預期」的成功狀態；CI 不能用 `continue-on-error` 吞掉不明失敗。

- [ ] **Step 5: 執行四個 Fixture 完整回歸**

```powershell
py -3 tools/validate_fixtures.py --all
py -3 -m unittest discover -s tests -v
git diff --check
```

Expected: 四個 Fixture 都是 Public Green、Preservation Green、Expected Acceptance Red、Mutation Detected；沒有 Evaluator 檔案位於任何 Subject Tree。

- [ ] **Step 6: Commit Fixture Repository 完整基準**

```powershell
git add fixtures/fastapi-provider-boundary evaluators/fastapi-provider-boundary fixture-contract.json tests/test_fixture_contract.py .github/workflows/validate.yml
git diff --cached --check
git diff --cached
git commit -m "feat(fixtures): add FastAPI provider-boundary scenario"
```

---

### Task 6: 發布 Fixture Repository 並固定不可變版本

**Files:**
- Verify only: sibling Fixture Repository entire tree
- External create: `eric861129/Clean-Code-AI-Collaboration-Benchmark-Fixtures`
- External tag: `cross-language-v3`（`cross-language-v1` 與 `cross-language-v2` 保留為作廢契約）

**Interfaces:**
- Consumes: Tasks 1～5 的四個已驗證 Fixture。
- Produces: 公開 Repository URL、Default Branch SHA、Annotated Tag SHA 與成功 CI Run，供 Manifest 固定。

- [ ] **Step 1: 在發布前重跑所有 Fixture Gate 與 Secret Scan**

```powershell
py -3 tools/validate_fixtures.py --all
py -3 -m unittest discover -s tests -v
git diff --check
git status --short --branch
$privatePathPattern = '[A-Za-z]:[\\/]' + '(Users|MySelf|Project)[\\/]'
rg -n "AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|$privatePathPattern" .
```

Expected: Gate 全部通過、工作目錄乾淨、Secret／個人絕對路徑無命中。為避免 Markdown 將 Regex 誤判成 Link，實作命令把個人路徑的群組部分存成另一個 PowerShell 變數後再串接，不在 Markdown 中形成 `](`。

- [ ] **Step 2: 建立公開 GitHub Repository，不切換全域帳號**

```powershell
$benchmarkGhToken = gh auth token --user eric861129
$env:GH_TOKEN = $benchmarkGhToken
try {
    gh repo create eric861129/Clean-Code-AI-Collaboration-Benchmark-Fixtures `
        --public `
        --source . `
        --remote origin `
        --push `
        --description "Small reproducible fixtures for the Clean Code AI Collaboration cross-language benchmark"
}
finally {
    Remove-Item Env:\GH_TOKEN -ErrorAction SilentlyContinue
}
```

Expected: Repository 為 Public，`origin/main` 與本機 `main` SHA 相同；Token 不輸出、不寫入檔案。

- [ ] **Step 3: 建立並推送 Annotated Tag**

```powershell
git tag -a cross-language-v3 -m "Cross-language benchmark fixtures v3"
git push origin cross-language-v3
git rev-parse HEAD
git rev-parse 'cross-language-v3^{}'
```

Expected: HEAD 與 Dereferenced Tag 都是相同 40 字元 Commit SHA。記錄這個 SHA，Task 7 必須逐字寫入 Manifest。

- [ ] **Step 4: 驗證 Remote 與 CI**

```powershell
gh repo view eric861129/Clean-Code-AI-Collaboration-Benchmark-Fixtures --json url,visibility,defaultBranchRef
gh run list --repo eric861129/Clean-Code-AI-Collaboration-Benchmark-Fixtures --limit 3
```

Expected: `visibility` 為 `PUBLIC`，Default Branch SHA 與 Tag Commit 一致，Validate Workflow 成功。

---

### Task 7: 建立 Versioned Manifest 與 36 個 Run Slot Planner

**Files:**
- Create: `evals/manifests/v0.3.0-cross-language.json`
- Create: `evals/harness/__init__.py`
- Create: `evals/harness/models.py`
- Create: `evals/harness/manifest.py`
- Create: `evals/harness/planner.py`
- Create: `tests/test_cross_language_harness.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `load_manifest(path: Path) -> BenchmarkManifest`、`build_run_slots(manifest) -> tuple[RunSlot, ...]`、`pilot_slots(...)` 與 `full_slots(...)`。
- `RunSlot` fields: `run_id`, `scenario_id`, `language`, `arm_id`, `repetition`, `order_index`。匿名 Candidate ID 到 Task 9 才以不可公開的隨機映射建立，不能由 Planner Seed 推回。

- [ ] **Step 1: 先寫 Manifest 與 Planner RED Tests**

```python
class CrossLanguageHarnessTests(unittest.TestCase):
    def test_manifest_builds_exactly_36_unique_slots(self) -> None:
        manifest = load_manifest(MANIFEST_PATH)
        slots = build_run_slots(manifest)
        self.assertEqual(36, len(slots))
        self.assertEqual(36, len({slot.run_id for slot in slots}))
        self.assertEqual(12, len(pilot_slots(slots)))
        self.assertEqual(24, len(full_slots(slots)))

    def test_manifest_rejects_unknown_arm_and_missing_fixture_sha(self) -> None:
        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        raw["arms"][0]["id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown arm"):
            validate_manifest(raw)

        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        raw["fixture_repository"]["commit"] = ""
        with self.assertRaisesRegex(ValueError, "40-character fixture commit"):
            validate_manifest(raw)
```

- [ ] **Step 2: 執行 RED**

```powershell
py -3 -m unittest tests.test_cross_language_harness -v
```

Expected: FAIL，因 Manifest 與 Harness Modules 尚不存在。

- [ ] **Step 3: 定義不可變 Models**

`models.py` 使用 `@dataclass(frozen=True)` 定義：

```python
@dataclass(frozen=True)
class RunSlot:
    run_id: str
    scenario_id: str
    language: str
    arm_id: str
    repetition: int
    order_index: int


@dataclass(frozen=True)
class BenchmarkManifest:
    benchmark_version: str
    fixture_url: str
    fixture_tag: str
    fixture_commit: str
    skill_tag: str
    model: str
    reasoning_effort: str
    random_seed: int
    scenarios: tuple[dict[str, object], ...]
    arms: tuple[dict[str, object], ...]
```

Planner 以 `random.Random(manifest.random_seed).shuffle(slots)` 產生固定順序；Repetition `1` 為 Pilot，`2`、`3` 為 Full Run。

- [ ] **Step 4: 寫入完整 Manifest**

Manifest 必須使用 Task 6 的真實 Fixture Commit，不接受空字串、Branch 名或任何示意值。先執行：

```powershell
$fixtureCommit = git -C ../Clean-Code-AI-Collaboration-Benchmark-Fixtures rev-parse 'cross-language-v3^{}'
if ($fixtureCommit -notmatch '^[0-9a-f]{40}$') {
    throw "Fixture Tag 沒有解析成固定 Commit：$fixtureCommit"
}
```

使用 `apply_patch` 把這次實際輸出的 40 字元值逐字寫進 `fixture_repository.commit`；寫完立刻執行 `validate_manifest`。其餘固定欄位為：

```json
{
  "schema_version": "1.0",
  "benchmark_version": "0.3.0-cross-language-desktop-subject-v3",
  "fixture_repository": {
    "url": "https://github.com/eric861129/Clean-Code-AI-Collaboration-Benchmark-Fixtures.git",
    "tag": "cross-language-v3"
  },
  "skill": {"tag": "v0.3.0", "version": "0.3.0"},
  "execution": {
    "model": "gpt-5.6-sol",
    "reasoning_effort": "high",
    "client": "codex-desktop-collaboration",
    "subject_timeout_seconds": 480,
    "fixture_timeout_seconds": 120,
    "oracle_timeout_seconds": 120,
    "repetitions": 3,
    "random_seed": 560301
  }
}
```

上面是固定欄位摘要；正式 Manifest 必須另外包含已寫入真實值的 `fixture_repository.commit`。`validate_manifest` 要以 Regex `^[0-9a-f]{40}$` 拒絕未固定值。四個 Scenario 必須逐筆寫入 Task、Must Preserve、Allowed Diff exact list／regex、Public／Preservation／Acceptance Commands 與預期 Baseline RED marker。

- [ ] **Step 5: GREEN、回歸與 Commit**

```powershell
py -3 -m unittest discover -s tests -v
git diff --check
git add evals/manifests evals/harness/__init__.py evals/harness/models.py evals/harness/manifest.py evals/harness/planner.py tests/test_cross_language_harness.py .gitignore
git diff --cached
git commit -m "feat(evals): define cross-language run manifest"
```

`.gitignore` 加入 `.benchmark-runs/`；不得修改 `evals/manifest.json` 與既有 `v0.1.0`／`v0.2.0` Result。

---

### Task 8: 建立 Fixture Builder、Process Runner 與 Subject Evidence（歷史 CLI 實作）

> **已由 Desktop Subject Protocol 取代。** 本 Task 的 CLI Subject Command 與 JSONL
> Stub 是保留舊 Evidence／單元測試相容性的歷史實作，不得用於新的 Pilot 或 Full
> Run。正式執行只使用本計畫前段的 `stage` → 外部 Fresh Context Desktop SubAgent →
> `collect` 流程。

**Files:**
- Create: `evals/harness/process.py`
- Create: `evals/harness/fixture_builder.py`
- Create: `evals/harness/subject_runner.py`
- Create: `evals/harness/evidence_recorder.py`
- Modify: `evals/harness/models.py`
- Modify: `tests/test_cross_language_harness.py`

**Interfaces:**
- Produces: `run_process(args: list[str], cwd: Path, timeout_seconds: int, stdin: str | None = None, attempt: int = 1) -> CommandResult`、`build_prompt(scenario: dict[str, object], arm_id: str) -> str`、`build_workspace(slot: RunSlot, manifest: BenchmarkManifest, paths: HarnessPaths) -> Workspace`、`run_subject(...) -> SubjectObservation`、`record_subject_evidence(...) -> Path`。
- Workspace 路徑固定為 `.benchmark-runs/workspaces/{run_id}`；Artifacts 固定為 `.benchmark-runs/artifacts/{run_id}`。

- [ ] **Step 1: 寫 Timeout、Prompt Arm 與隔離 RED Tests**

```python
def test_process_timeout_is_terminal_and_not_automatically_retried(self) -> None:
    result = run_process(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        cwd=ROOT,
        timeout_seconds=1,
    )
    self.assertTrue(result.timed_out)
    self.assertEqual("timeout", result.classification)
    self.assertEqual(1, result.attempt)

def test_arm_prompts_only_contain_the_declared_difference(self) -> None:
    manifest = load_manifest(MANIFEST_PATH)
    scenario = manifest.scenarios[0]
    control = build_prompt(scenario, "control")
    generic = build_prompt(scenario, "generic-clean-code")
    skill = build_prompt(scenario, "skill-v0.3.0")
    self.assertEqual(control + "\n\n請遵守 Clean Code 完成任務。", generic)
    self.assertIn("$clean-code-ai-collaboration", skill)
    self.assertNotIn("$clean-code-ai-collaboration", control)
    self.assertNotIn("$clean-code-ai-collaboration", generic)
```

- [ ] **Step 2: 實作安全 Process Runner**

在 `models.py` 新增：

```python
@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    elapsed_seconds: float
    timed_out: bool
    classification: str
    attempt: int


@dataclass(frozen=True)
class Workspace:
    root: Path
    artifact_dir: Path
    baseline_commit: str


@dataclass(frozen=True)
class HarnessPaths:
    repository_root: Path
    runs_root: Path
    fixture_clone: Path
    skill_repository: Path


@dataclass(frozen=True)
class SubjectObservation:
    run_id: str
    command: CommandResult
    prompt_sha256: str
    raw_jsonl_path: Path
    last_message_path: Path
```

`run_process` 使用 `subprocess.run(args: list[str], shell=False, text=True, capture_output=True, timeout=...)`。`TimeoutExpired` 轉成 Exit Code `None`、`timed_out=True`，保留部分 stdout／stderr；命令參數與環境以結構資料保存，不把 Prompt 拼進 Shell Command。

- [ ] **Step 3: 實作 Workspace Builder**

流程固定為：

1. 由本機只讀 Fixture Clone 的固定 Commit，使用 `git archive` 匯出 `fixtures/{scenario_id}`。
2. 建立新 Git Repository 與本機作者設定。
3. React 執行 `npm ci --cache .benchmark-runs/cache/npm --prefer-offline --no-audit --no-fund`；Python 先以 `pip download -r requirements.lock -d .benchmark-runs/cache/pip/{lockfile_sha256}` 準備 Wheel Cache，再建立 `.venv` 並使用 `--no-index --find-links` 安裝。
4. Skill Arm 由 Skill Repository 的 `v0.3.0` Tag 匯出 `clean-code-ai-collaboration` 到 `.agents/skills/clean-code-ai-collaboration`。
5. 建立 Baseline Commit，確認 `git status --short` 只包含被忽略的依賴目錄。

Builder 不刪除既有 Run Workspace；若目標路徑已存在就 Fail Closed，避免覆蓋前一次證據。

- [x] **Step 4: 歷史 Codex CLI Subject Command（已由 Desktop Protocol 取代）**

> 以下 Argument List 只用來說明已保存的舊 CLI Evidence 如何產生，不得再用於
> 新的 Pilot／Full Run。新的有效執行一律採用本文件開頭的 Stage → Desktop
> SubAgent → Collect Protocol。

固定 Argument List：

```python
[
    "codex", "exec",
    "--ephemeral",
    "--json",
    "--ignore-user-config",
    "--strict-config",
    "--sandbox", "workspace-write",
    "--model", "gpt-5.6-sol",
    "--config", 'model_reasoning_effort="high"',
    "--config", 'approval_policy="never"',
    "--config", 'sandbox_workspace_write.network_access=false',
    "--cd", str(workspace.root),
    "--output-last-message", str(artifact_dir / "last-message.md"),
    "-",
]
```

Prompt 由 stdin 傳入。執行前保存 Prompt、SHA-256、CLI Version、Runtime Version、Sandbox／Network Config、工具權限與 Git Baseline SHA；執行後保存 stdout JSONL、stderr、Exit Code、Timeout 與 elapsed seconds。Evidence Recorder 只在 JSONL 事件確實提供資料時解析 Token、Tool Call 與 Files Inspected；缺少欄位時寫入 `not_available`，不從文字長度或 Diff 猜測。

- [ ] **Step 5: 執行 GREEN 與假 Runner 整合測試**

測試以 Python Stub Command 取代真實 Codex，輸出兩行 JSONL 並修改一個允許檔案；確認 Evidence 檔、last message、Diff 與 Terminal State 產生。此 Task 不啟動付費 Codex Session。

```powershell
py -3 -m unittest discover -s tests -v
git diff --check
git add evals/harness tests/test_cross_language_harness.py
git diff --cached
git commit -m "feat(evals): run isolated benchmark subjects"
```

---

### Task 9: 建立 Diff Boundary、Oracle、匿名審查與 Result Builder

**Files:**
- Create: `evals/harness/diff_boundary.py`
- Create: `evals/harness/oracle_runner.py`
- Create: `evals/harness/anonymizer.py`
- Create: `evals/harness/result_builder.py`
- Create: `evals/harness/cli.py`
- Modify: `evals/harness/models.py`
- Modify: `tests/test_cross_language_harness.py`
- Modify: `.github/workflows/validate.yml`

**Interfaces:**
- Produces: `capture_diff(workspace, scenario) -> DiffEvidence`、`run_oracles(...) -> OracleEvidence`、`build_review_packet(...) -> dict[str, object]`、`write_review_packet(...) -> Path`、`build_public_result(..., benchmark_version=...) -> dict[str, object]`。
- Reviewer 私有映射固定在 `.benchmark-runs/review-key.json`，不進 Git；Review Packet 固定在 `.benchmark-runs/review-packets/`。

- [x] **Step 1: 寫 Diff、Retry、匿名與 Terminal State RED Tests**

至少加入：

```python
def test_rename_requires_source_and_destination_to_be_allowed(self) -> None:
    evidence = classify_paths(
        changed=["src/allowed.ts"],
        renamed=[Rename("src/allowed.ts", "scripts/escape.ts")],
        allowed_exact={"src/allowed.ts"},
        allowed_patterns=(),
    )
    self.assertEqual(["scripts/escape.ts"], evidence.outside_boundary)

def test_result_requires_all_36_terminal_states(self) -> None:
    manifest = load_manifest(MANIFEST_PATH)
    slots = build_run_slots(manifest)
    with self.assertRaisesRegex(ValueError, "36 terminal states"):
        build_public_result(
            slots,
            run_documents=[],
            benchmark_version=manifest.benchmark_version,
        )

def test_review_packet_does_not_reveal_arm(self) -> None:
    sample_run = {
        "run_id": "react-overdue-rule-skill-v0.3.0-r01",
        "arm_id": "skill-v0.3.0",
        "task": "Change the High Priority overdue boundary.",
        "diff": "diff --git a/src/overdue.ts b/src/overdue.ts",
        "oracle_results": [],
    }
    packet = build_review_packet(sample_run, candidate_id="candidate-7f2a")
    serialized = json.dumps(packet, ensure_ascii=False)
    self.assertNotIn("skill-v0.3.0", serialized)
    self.assertNotIn("generic-clean-code", serialized)
```

- [x] **Step 2: 實作 Diff Capture**

在 `models.py` 新增：

```python
@dataclass(frozen=True)
class Rename:
    source: str
    destination: str


@dataclass(frozen=True)
class DiffEvidence:
    diff: str
    diff_sha256: str
    changed_paths: tuple[str, ...]
    renamed_paths: tuple[Rename, ...]
    outside_boundary: tuple[str, ...]


@dataclass(frozen=True)
class OracleEvidence:
    public: tuple[CommandResult, ...]
    preservation: tuple[CommandResult, ...]
    acceptance: tuple[CommandResult, ...]
    automatic_failure_reasons: tuple[str, ...]
```

Subject 結束、Evaluator 注入前執行 `git add -N -- .`，再以 `git diff --binary --no-ext-diff HEAD` 與 `git diff --name-status -M HEAD` 擷取新增、修改、刪除與重新命名。每個路徑使用 Repository-relative POSIX format；exact 或 Python `re.fullmatch` 才能放行；Rename 來源與目的都要通過。

- [x] **Step 3: 實作 Oracle Runner**

Oracle Runner 將指定 Evaluator 複製到 Subject Workspace 的 `.benchmark-oracle/`，但 Diff 必須已在注入前凍結。依序執行：

1. Public Gate。
2. Preservation Oracle。
3. Acceptance Oracle。

Candidate 任一必要 Gate 非 0 即 Automatic Failure。Baseline 階段則要求 Public／Preservation Exit 0、Acceptance Exit 非 0 且包含所有預期 Marker。

- [x] **Step 4: 實作 Infrastructure Retry 判斷**

Retry 只接受列舉值：`harness_error`、`dependency_cache_error`、`cli_runner_error`、`environment_error`。`timeout`、`candidate_test_failure`、`candidate_incomplete`、`invalid_claim` 與 `outside_boundary` 禁止重跑。第二次 Attempt 必須保留第一次 Evidence Path 與原因。

- [x] **Step 5: 實作匿名 Review Packet**

使用 `secrets.token_hex(4)` 產生不可由公開 Seed 推回 Arm 的 Candidate ID；Private Mapping 只存在 `.benchmark-runs/review-key.json`。Packet 只含任務、Must Preserve、匿名 ID、Diff、命令、Oracle、Automatic Failure、Blind Spots 與三份空白 Rubric 欄位；不得包含 Arm、Repetition 順序或 Skill 載入路徑。

- [x] **Step 6: 實作 Result Builder 與 CLI**

Result Builder 驗證：36 個目前有效 Generation 的 Slot 全部存在、Run ID 唯一、Terminal State 合法、舊的作廢 Generation 不得進入結果、無 Aggregate Score Key、Telemetry 缺少時為 `not_available`。CLI：

```text
python -m evals.harness.cli prepare
python -m evals.harness.cli stage --phase pilot --run-id <logical-run-id>
python -m evals.harness.cli collect --dispatch-id <dispatch-id> --outcome <completed|timeout|infrastructure_failure>
python -m evals.harness.cli freeze --decision-note "..."
python -m evals.harness.cli invalidate-pilot --scenario <id> --reason "..."
python -m evals.harness.cli adjudicate-timeout --run-id <id> --source <candidate|infrastructure> --reason "..."
python -m evals.harness.cli stage --phase full --run-id <logical-run-id>
python -m evals.harness.cli review-packets
python -m evals.harness.cli build-result
python -m evals.harness.cli verify
python -m evals.harness.cli verify-freeze
python -m evals.harness.cli verify-reviews
```

`stage --phase pilot` 只選 Repetition 1；`stage --phase full` 只選 Repetition 2、3。
舊的 `pilot`／`full` 命令會刻意 Fail Closed，避免誤啟動 nested CLI；`build-result`
在 Rubric 尚未填完或不足 36 個 Terminal State 時同樣 Fail Closed。

- [x] **Step 7: 把 Harness 契約加入 CI 並 Commit**

```powershell
py -3 -m unittest discover -s tests -v
agentskills validate clean-code-ai-collaboration
git diff --check
git add evals/harness tests/test_cross_language_harness.py .github/workflows/validate.yml
git diff --cached
git commit -m "feat(evals): evaluate and anonymize benchmark runs"
```

CI 只跑 Harness Unit／Contract Test，不啟動 Codex Session、不 Clone Fixture、不要求帳號 Token。

---

### Task 10: 執行 12 次 Pilot 並凍結契約

**Files:**
- Create ignored evidence: `.benchmark-runs/**`
- Modify only if contract is unchanged: no tracked file
- If contract changes: modify exact Fixture／Manifest／Harness files, invalidate all three Pilot Arms for the affected Scenario, Commit the fix, then rerun that Scenario Pilot trio

**Interfaces:**
- Consumes: 固定 Fixture Tag、Manifest、Harness 與 Skill `v0.3.0`。
- Produces: 12 個 Pilot Terminal State、12 份匿名 Review Packet，以及是否能直接計入正式結果的凍結決策。

- [ ] **Step 1: 執行 Preflight，不啟動 Subject**

```powershell
py -3 -m evals.harness.cli prepare
py -3 -m unittest discover -s tests -v
agentskills validate clean-code-ai-collaboration
codex --version
git status --short --branch
```

Expected: 四個 Baseline Public／Preservation Green、Acceptance Expected Red；Fixture Commit、Skill Tag、Prompt Hash、Lockfile Hash、CLI、模型與 12 個 Pilot Slot 全部列出。

- [ ] **Step 2: 執行 Pilot**

依固定 Planner 順序，逐一處理每個 Pilot Slot；一個 Slot 完整結束後，才開始下一個：

```powershell
py -3 -m evals.harness.cli stage --phase pilot --run-id <logical-run-id>
# 依 stage 輸出的 instruction，以一個 fresh Desktop Subject 完成單一 Workspace。
py -3 -m evals.harness.cli collect --dispatch-id <dispatch-id> --outcome <completed|timeout|infrastructure_failure>
```

每次 `stage` 都必須對應一個 fresh Subject；不可批次派發後共用 Context，也不可直接執行
`pilot`。Expected: 12 個 Slot 各自取得 Passed、Automatic Failure、Timeout 或 Infrastructure
Failure；Report 遺漏／不完整或不可變欄位不符會直接成為不可重跑的 Automatic Failure。單一
Session 最多 480 秒，Harness 每完成一個 Slot 即落盤 Dispatch、Attempt Receipt、Diff 與 Evidence。

- [ ] **Step 3: 驗證 Pilot 完整性與匿名材料**

```powershell
py -3 -m evals.harness.cli review-packets --phase pilot
py -3 -m evals.harness.cli verify --phase pilot
```

Expected: 12 個 Terminal State、12 個匿名 Candidate ID、Arm 不出現在 Packet；所有 Prompt、Controller-only Dispatch、Report 與 Diff 都有可驗證 Hash，Desktop 不要求 JSONL。Controller Dispatch 不主動交付，也不列入 Subject instruction。

- [ ] **Step 4: 做契約凍結判斷**

逐一回答：Baseline RED 是否只來自需求缺口？Oracle 是否抓到真正風險？允許修改範圍是否誤判合理責任？Prompt 三組是否只有預定差異？若全部為是，在 `.benchmark-runs/contract-freezes/` 建立以 Contract SHA 命名的凍結紀錄，內容含 Manifest、Harness、Codex CLI、Fixture、Skill、Prompt、Oracle 與 Rubric Hash。若 Oracle Timeout 尚未判明是 Candidate 還是 Infrastructure，必須先執行 `adjudicate-timeout`，不得直接凍結。

若四項都成立，明確執行 `freeze --decision-note "..."`；`pilot` 本身不得自動凍結。若任一項需修正，不能只重跑單一 Arm。先執行 `invalidate-pilot --scenario <id> --reason "..."`，保存該 Scenario 三個 Pilot Run 的 Hash 與作廢原因，再以 TDD 修正並建立獨立 Commit。Harness 會提升該情境的 Generation，且只有 Scenario Contract Hash 確實改變後，才允許重新執行三個 Arm。舊 Generation 永遠保留，不得進入最終 Result。

- [ ] **Step 5: 停在 Full Run 前回報 Pilot**

回報 12 個狀態、契約是否凍結、Invalidation／Retry 是否發生、已使用時間與無法取得的 Telemetry。此時不建立公開 Result，也不先跑剩餘 24 次。

---

### Task 11: 執行剩餘 24 次 Full Run 與匿名人工審查

**Files:**
- Create ignored evidence: `.benchmark-runs/**`
- Create ignored reviewer inputs: `.benchmark-runs/reviews/*.json`
- No tracked result until all 36 slots and reviews complete

**Interfaces:**
- Consumes: Task 10 的 Contract Freeze 與有效 Pilot。
- Produces: 36 個完整 Terminal State 與每個候選三個分維度匿名 Review。

- [ ] **Step 1: 驗證 Contract Freeze 未漂移**

```powershell
py -3 -m evals.harness.cli verify-freeze
```

Expected: Manifest、Fixture、Prompt、Oracle、Rubric SHA 全部與 Pilot Freeze 相同；任何差異都停止 Full Run。

- [ ] **Step 2: 執行 Full Run**

依固定 Planner 順序，對每個剩餘 Full Slot 重複「單一 `stage` → fresh Desktop Subject →
單一 `collect`」：

```powershell
py -3 -m evals.harness.cli stage --phase full --run-id <logical-run-id>
# 依 stage 輸出的 instruction，以一個 fresh Desktop Subject 完成單一 Workspace。
py -3 -m evals.harness.cli collect --dispatch-id <dispatch-id> --outcome <completed|timeout|infrastructure_failure>
```

不可直接執行 `full`，也不可讓同一個 Subject 接續處理多個 Slot。Expected: 新增 24 個
Terminal State；與有效 Pilot 合計 36。Harness 中斷後重新執行只能跳過已有 Terminal State 的
Slot，不覆寫或刪除舊 Evidence。

- [ ] **Step 3: 產生 36 份匿名 Review Packet**

```powershell
py -3 -m evals.harness.cli review-packets --phase all
```

Expected: 每份 Packet 都不含 Arm；Automatic Failure 仍保留，不能因後續 Rubric 而取消。

- [ ] **Step 4: 由同一位 Reviewer 完成三份 Rubric**

Reviewer 對每個 Candidate 分別填寫：

```json
{
  "context-and-locality": {"score": 0, "reason": "具體證據理由"},
  "behavior-and-validation": {"score": 0, "reason": "具體證據理由"},
  "decision-and-escalation": {"score": 0, "reason": "具體證據理由"}
}
```

實際 Score 只能是 `0`、`1`、`2`；上例的 `0` 是 Schema 範例，不是預填結果。Reviewer 必須依匿名材料判定，不讀 Private Mapping；每個 Reason 要引用 Diff、Oracle、候選決策或盲點。

- [ ] **Step 5: 驗證 Review 完整性**

```powershell
py -3 -m evals.harness.cli verify-reviews
```

Expected: 36 份 Review、每份三個維度、無 Aggregate Score、無空理由；Private Mapping 未被改寫。

---

### Task 12: 產生公開 Result、更新文件並發布原始證據 Asset

**Files:**
- Create: `evals/results/v0.3.0-cross-language.json`
- Modify: `evals/benchmark.md`
- Modify: `README.md`
- Modify: `tests/test_eval_contract.py`
- Optional generated archive outside Git: `.benchmark-runs/releases/v0.3.0-cross-language-evidence.zip`

**Interfaces:**
- Consumes: 36 個 Terminal State、匿名 Review、Private Mapping 與 Contract Freeze。
- Produces: Machine-readable Result、Observed／Inference／Unknown／Failure and Limitation 摘要，以及可選的 Release Asset。

- [ ] **Step 1: 先寫 Result Contract RED Test**

在 `tests/test_eval_contract.py` 新增：

```python
def test_cross_language_result_is_complete_and_non_aggregate(self) -> None:
    path = EVAL_ROOT / "results" / "v0.3.0-cross-language.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    self.assertEqual(
        "0.3.0-cross-language-desktop-subject-v3",
        result["benchmark_version"],
    )
    for field in (
        "fixture_repository",
        "skill",
        "execution",
        "contract_sha256",
    ):
        self.assertIn(field, result)
    self.assertEqual(36, len(result["runs"]))
    self.assertEqual(36, len({run["run_id"] for run in result["runs"]}))
    self.assertEqual(
        {"control", "generic-clean-code", "skill-v0.3.0"},
        {run["arm_id"] for run in result["runs"]},
    )
    self.assert_no_aggregate_scores(result)
    for run in result["runs"]:
        self.assertIn(run["terminal_state"], {
            "passed", "automatic_failure", "timeout",
            "infrastructure_failure",
        })
        self.assertEqual(3, len(run["rubric_results"]))
```

Run: `py -3 -m unittest tests.test_eval_contract -v`

Expected: FAIL，因 Result 尚未建立。

- [ ] **Step 2: 產生 Result，不手動改寫 Run 數據**

```powershell
py -3 -m evals.harness.cli build-result `
    --output evals/results/v0.3.0-cross-language.json
```

Builder 恢復 Arm 名稱、保留 Attempt History 與失敗，依 Language／Scenario／Arm 彙整分維度資料；不得加入 `total_score`、`overall_score`、`win_rate` 或同義欄位。

- [ ] **Step 3: 更新 Benchmark 文件**

`evals/benchmark.md` 新增 `Cross-Language v0.3.0 Initial Results`，依序寫：

1. Fixed Conditions。
2. Observed。
3. Inference。
4. Unknown。
5. Failure and Limitation。

只寫 Result 可直接支持的數字。若 Token／Tool Call 為 `not_available`，明確說無法比較；即使 Skill Arm 表現較好，也只能宣稱四個小型 Fixture、單一模型／Client 下的初步觀察。

- [ ] **Step 4: 更新 README，保留歷史與新證據邊界**

README 同時連結既有 `v0.2.0` .NET Result 與新的跨語言 Result。不得把兩批不同 Harness／Fixture 合併成單一成功率，也不得寫「所有 React／Python Repository 已驗證」。

- [ ] **Step 5: 執行完整 Repository Gate 與 Secret Scan**

```powershell
py -3 -m unittest discover -s tests -v
agentskills validate clean-code-ai-collaboration
git diff --check
$privatePathPattern = '[A-Za-z]:[\\/]' + '(Users|MySelf|Project)[\\/]'
rg -n "AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|$privatePathPattern" README.md evals tests
```

Expected: 全部 Gate 通過；公開 JSON 不含個人絕對路徑、Token、完整本機 Artifact Path 或 Private Mapping。

- [ ] **Step 6: Commit 公開 Result 與文件**

```powershell
git add evals/results/v0.3.0-cross-language.json evals/benchmark.md README.md tests/test_eval_contract.py
git diff --cached --check
git diff --cached
git commit -m "docs(evals): publish cross-language benchmark results"
```

- [ ] **Step 7: 封裝原始 Evidence 並停在發布授權前**

以 Archive 只收錄可公開的 Prompt、Report 摘要、Diff、命令、Exit Code、Oracle 與匿名 Review；排除 Private Mapping、私有 Controller Dispatch、完整 Subject Report、暫時 Workspace、認證資料與個人絕對路徑。產生 SHA-256，回報 Archive Path、Size 與 Hash。

未再次取得 User 指示前，不 Push Skill Repository、不建立新的 Skill Tag／Release，也不上傳 Evidence Asset。Fixture Repository 的修正版契約固定為 `cross-language-v3`；`cross-language-v1` 與 `cross-language-v2` 保留為作廢契約，不覆寫也不刪除。

---

## Final Verification Checklist

- [ ] Fixture Public Repository、Tag、Commit 與 CI 都可公開讀取且一致。
- [ ] 四個 Baseline 都是 Public／Preservation Green、Acceptance Expected Red、Mutation Detected。
- [ ] Manifest 產生 36 個唯一 Slot，Pilot 12 與 Full 24 不重疊。
- [ ] 每個 Slot 都有固定版本、Prompt、私有 Controller Dispatch、Report、Diff、Command、Exit Code、Oracle、Terminal State 與 Blind Spot；Desktop 無法取得的 JSONL 與 Telemetry 明確標示 `not_available`。
- [ ] 只有明確 Infrastructure Failure 最多 Retry 一次，原始 Attempt 沒被覆寫。
- [ ] Reviewer Materials 不揭露 Arm，36 份 Review 都有三個分維度理由。
- [ ] Result 沒有 Aggregate Score、選擇性省略、Token 推估或跨情境「勝率」。
- [ ] 既有 .NET Result 與新跨語言 Result 分開報告，不偽造可直接比較的總結。
- [ ] Repository 全部既有測試、新 Harness Tests、Agent Skill Validator、Fixture CI 與 `git diff --check` 全部通過。
- [ ] 公開檔案沒有 Secret、個資、雇主內部資料、Private Mapping 或個人絕對路徑。
- [ ] Run Workspaces 與 Raw Evidence 保留；沒有執行未授權的批次刪除。
