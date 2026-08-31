# Clean Code AI Collaboration Skill v0.3.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 `clean-code-ai-collaboration` 升級為三層風險路徑、明確呼叫、可區分 Prototype 與 Production-Ready，並能依 Repository 既有工具形成驗證閉環的 `v0.3.0` Skill。

**Architecture:** `SKILL.md` 只保留三層路由、交付成熟度、CLEAN Lens、Authorization Gate 與 Reference 入口；`review-output-contract.md` 作為 Standard 與 Full Audit 的唯一輸出契約。驗證工具的選擇放進既有 Legibility 與 Testing Reference，公開狀態與外部效度矩陣分別由 README 與 `evals/benchmark.md` 維護，不新增 Result、Fixture 或重複 Roadmap。

**Tech Stack:** Agent Skills specification、Markdown、YAML、Python 3.12 `unittest`、`agentskills` validator、Git。

**Spec:** `docs/superpowers/specs/2026-08-31-clean-code-ai-collaboration-v0.3.0-design.md`

## Global Constraints

- 目標版本固定為 `0.3.0`；現有 `v0.2.0` Benchmark Result 保留為歷史證據，不改寫成 `v0.3.0` 結果。
- `SKILL.md` Body 維持 500 個英文單字以內；Frontmatter Description 只描述觸發條件，不摘要工作流程。
- 風險路徑依 Full Audit → Standard → Lightweight 的順序判斷；發現高風險或關鍵未知時只能升級。
- Prototype／Production-Ready 只標示交付成熟度，不降低 Authorization Gate、正式資料、安全、公開契約或外部副作用門檻。
- Standard 不強迫空白 Heading 或 `F1/A1/U1/O1/E1`；Full Audit 必須保留 `v0.2.0` 的完整追蹤契約。
- Codex Adapter 固定使用 `allow_implicit_invocation: false`；`v0.3.0` 的正式使用方式是明確指定 `$clean-code-ai-collaboration`。
- 優先使用 Repository 既有且與本次風險相關的 Formatter、Linter、Static Analysis、Build、Test 與其他 Gate；未經授權不安裝工具、不改 CI、不新增依賴。
- 沒有可靠 Oracle 時，不以 Linter、Coverage、全綠測試或 Agent 自述代替需求正確性。
- Benchmark 新增內容只標示已驗證、規劃中與尚未支持；沒有 Token Telemetry 時不宣稱節省 Token。
- 所有檔案使用 UTF-8；不得加入 Token、Secret、內部 Repository 資料或不可公開 Evidence。
- 每個 Task 都先完成 RED，再做最小 GREEN、完整回歸與 Conventional Commit。
- 未經 User 指示不得 Push、建立 Tag、發布 Release 或執行尚未核准的跨 Repository／跨模型 Benchmark。

## File Map

| Path | Responsibility |
| --- | --- |
| `clean-code-ai-collaboration/SKILL.md` | 三層路徑、交付成熟度、不適用情境、CLEAN、Authorization 與輸出路由 |
| `clean-code-ai-collaboration/references/review-output-contract.md` | Standard 精簡輸出與 Full Audit 完整追蹤契約的唯一來源 |
| `clean-code-ai-collaboration/references/clean-code-for-agent-legibility.md` | Clean Code 對 Agent 理解成本、過度抽象與驗證入口的判斷 |
| `clean-code-ai-collaboration/references/testing-and-change-safety.md` | Repository 工具鏈、Oracle、測試策略與 Gate 選擇 |
| `clean-code-ai-collaboration/agents/openai.yaml` | Codex UI Metadata、Default Prompt 與 explicit-only policy |
| `README.md` | 三層路徑、交付成熟度、明確呼叫、工具鏈與公開限制 |
| `evals/benchmark.md` | 既有結果、外部效度狀態矩陣與後續評測順序 |
| `tests/test_skill_contract.py` | Skill、輸出契約、Adapter、README 與版本的一致性測試 |
| `tests/test_eval_contract.py` | Benchmark 狀態矩陣、證據邊界與既有結果不可改寫的契約測試 |

---

### Task 1: 建立三層風險路徑與雙層輸出契約

**Files:**
- Modify: `tests/test_skill_contract.py:21-159,328-352`
- Modify: `clean-code-ai-collaboration/SKILL.md:1-52`
- Modify: `clean-code-ai-collaboration/references/review-output-contract.md:1-68`

**Interfaces:**
- Consumes: `v0.2.0` 的 Lightweight／Full Path、Authorization Gate 與 Full Review Heading。
- Produces: `Lightweight Path`、`Standard Path`、`Full Audit Path` 路由，以及 Standard／Full Audit 共用的 `review-output-contract.md`。

- [ ] **Step 1: 先將版本、路徑與輸出契約測試改成 `v0.3.0` 預期**

在 `tests/test_skill_contract.py` 將 `test_entrypoint_has_lightweight_and_full_paths` 替換為：

```python
def test_entrypoint_defines_three_risk_paths_and_one_way_escalation(self) -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")

    for path_name in {"Lightweight Path", "Standard Path", "Full Audit Path"}:
        with self.subTest(path_name=path_name):
            self.assertIn(path_name, content)

    self.assertIn("public contract", content)
    self.assertIn("external side effect", content)
    self.assertIn("critical unknown", content)
    self.assertIn("upgrade", content.lower())
    self.assertIn("must not downgrade", content.lower())
```

新增：

```python
def test_standard_output_is_concise_and_full_audit_remains_traceable(self) -> None:
    content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
        encoding="utf-8"
    )
    standard, full_audit = content.split("## Full Audit Output Contract", maxsplit=1)

    self.assertIn("## Standard Output Contract", standard)
    for field in {
        "Outcome and Status",
        "Decision Basis",
        "Selected Approach",
        "Behavior, Diff, and Validation",
        "Stop or Human Decision",
    }:
        with self.subTest(standard_field=field):
            self.assertIn(field, standard)

    self.assertNotIn("`None; Sources checked: ...`", standard)
    self.assertNotIn("`Not investigated`", standard)
    for term in {
        "F1",
        "A1",
        "U1",
        "O1",
        "E1",
        "`None; Sources checked: ...`",
        "`Not investigated`",
        "Validation Blind Spots",
        "Human Decisions Required",
    }:
        with self.subTest(full_audit_term=term):
            self.assertIn(term, full_audit)
```

將 `test_review_contract_leads_with_status_and_keeps_blind_spots` 改成只檢查 Full Audit 區段，並配合巢狀 Heading：

```python
def test_full_audit_contract_leads_with_status_and_keeps_blind_spots(self) -> None:
    content = (SKILL_ROOT / "references" / "review-output-contract.md").read_text(
        encoding="utf-8"
    )
    full_audit = content.split("## Full Audit Output Contract", maxsplit=1)[1]

    self.assertLess(
        full_audit.index("### Outcome and Status"),
        full_audit.index("### Repository Facts Used"),
    )
    self.assertIn("### Validation Blind Spots", full_audit)
    self.assertIn("### Human Decisions Required", full_audit)
```

將 `test_v020_metadata_and_clean_lenses_are_discoverable` 改名為 `test_v030_metadata_and_clean_lenses_are_discoverable`，並把唯一的版本預期改成：

```python
'version: "0.3.0"',
```

- [ ] **Step 2: 執行 RED，確認失敗原因是缺少 Standard 與 `v0.3.0`**

Run:

```powershell
py -3 -m unittest `
  tests.test_skill_contract.SkillContractTests.test_entrypoint_defines_three_risk_paths_and_one_way_escalation `
  tests.test_skill_contract.SkillContractTests.test_standard_output_is_concise_and_full_audit_remains_traceable `
  tests.test_skill_contract.SkillContractTests.test_v030_metadata_and_clean_lenses_are_discoverable `
  -v
```

Expected: FAIL；分別指出 `Standard Path`、`Full Audit Output Contract` 與 `version: "0.3.0"` 尚不存在。不能是 Python Syntax Error、檔案路徑錯誤或編碼錯誤。

- [ ] **Step 3: 更新 Skill Description、版本與三層路由**

將 Frontmatter Description 與版本改為：

```yaml
description: Use when repository changes require contextual trade-offs about behavior preservation, test adequacy, change locality, dependency boundaries, side effects, or review evidence.
metadata:
  author: eric861129
  version: "0.3.0"
```

以以下內容替換 `## Path Selection`：

```markdown
## Path Selection

Evaluate Full Audit first, then Standard, then Lightweight. New evidence may upgrade a path; it must not downgrade one to shorten the report.

- **Full Audit Path:** use for a public contract, production data or migration, external side effect, third-party dependency change, concurrency, security, privilege, CI, infrastructure, deployment, destructive action, unclear authority, formal audit, material trade-off, or critical unknown. Read `repository-context-template.md`.
- **Standard Path:** use for a repository feature, test, defect, refactor, or internal design change with known ownership, authorization, behavior boundary, and executable gates.
- **Lightweight Path:** use only for a local, reversible readability change with no behavior, contract, data, side effect, dependency, ownership, or deployment impact and one obvious option.
```

在 `Reference Routing` 將 Full 專用輸出列改成：

```markdown
- Standard or Full Audit output: `review-output-contract.md`
```

以以下內容替換 `## Required Output`：

```markdown
## Required Output

- **Lightweight Path:** report the facts used, behavior boundary, change, validation, and only applicable human decisions.
- **Standard Path:** follow the Standard Output Contract and omit non-material sections.
- **Full Audit Path:** follow every Full Audit heading and traceability rule in `review-output-contract.md`.
```

寫回 `SKILL.md` 時，以上三個 inline-code 檔名必須改成 Markdown Link：`repository-context-template.md` 的 target 固定為 `references/repository-context-template.md`；兩個 `review-output-contract.md` 的 target 固定為 `references/review-output-contract.md`。

- [ ] **Step 4: 將既有 Review Contract 分成 Standard 與 Full Audit**

將 `review-output-contract.md` 開頭替換為：

```markdown
# Review Output Contract

## Standard Output Contract

Use this contract for a Standard Path. Report the following headings in order. The first four are required; include Stop or Human Decision only when a stop, unresolved authority, or Owner decision affects the result. Omit non-material fields instead of emitting empty placeholders, but never omit a known risk or required investigation.

### Outcome and Status

State the outcome first, using `planned`, `implemented`, `verified-within-scope`, `blocked`, or `not-investigated`. Name the behavior and Diff boundary covered by that status.

### Decision Basis

List only Repository facts that changed the decision. Add assumptions or unknowns only when they affect the conclusion, validation, authorization, or safe boundary.

### Selected Approach

State the selected approach and why it fits this Repository. When another viable approach exists, state the observable condition that would make it fit better.

### Behavior, Diff, and Validation

State behavior that must not change, expected and actual Diff boundaries, executed validation, evidence limitations, and remaining blind spots.

### Stop or Human Decision

When applicable, state the stop condition, responsible Owner, external state left unchanged, and exact decision or evidence needed to resume.

## Full Audit Output Contract

Use this contract on the Full Audit Path. Return every heading below, including headings with no applicable item. Link conclusions with stable `F`, `A`, `U`, `O`, and `E` identifiers so a reviewer can trace evidence, uncertainty, options, and validation without inferring missing facts.
```

把目前 `review-output-contract.md` 第 3 行起的空白調查規則與 16 個既有欄位放在新 Full Audit 開頭之後。欄位文字內容保持不變，Heading 由 `##` 改成 `###`，讓它們真正隸屬 `## Full Audit Output Contract`；同時把文件內的 `Full Path` 改成 `Full Audit Path`。

- [ ] **Step 5: 執行 GREEN、完整回歸與入口長度檢查**

Run:

```powershell
py -3 -m unittest discover -s tests -v
agentskills validate clean-code-ai-collaboration
$skillBody = ((Get-Content -Raw 'clean-code-ai-collaboration\SKILL.md') -split '---', 3)[2]
($skillBody -split '\s+' | Where-Object { $_ }).Count
```

Expected: 33 項既有測試加上新測試全部 PASS；Validator 顯示 Skill 有效；Body word count 不超過 `500`。

- [ ] **Step 6: Commit 三層路由與輸出契約**

```powershell
git add clean-code-ai-collaboration/SKILL.md clean-code-ai-collaboration/references/review-output-contract.md tests/test_skill_contract.py
git diff --cached --check
git diff --cached
git commit -m "feat(skill): add standard and full audit paths"
```

---

### Task 2: 加入交付成熟度與 Repository 驗證工具鏈

**Files:**
- Modify: `tests/test_skill_contract.py`
- Modify: `clean-code-ai-collaboration/SKILL.md`
- Modify: `clean-code-ai-collaboration/references/clean-code-for-agent-legibility.md:7-30`
- Modify: `clean-code-ai-collaboration/references/testing-and-change-safety.md:11-54`

**Interfaces:**
- Consumes: Task 1 的三層風險路徑與既有 Testing Reference。
- Produces: 與風險路徑正交的 Prototype／Production-Ready 標示，以及 Repository-native Gate 選擇規則。

- [ ] **Step 1: 寫 Delivery Readiness 與 Toolchain RED Tests**

在 `tests/test_skill_contract.py` 新增：

```python
def test_delivery_readiness_does_not_lower_risk_or_authority(self) -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")
    section = content.split("## Delivery Readiness", maxsplit=1)[1]
    section = section.split("## ", maxsplit=1)[0]

    for term in {"Prototype", "Production-Ready", "Full Audit", "authorization"}:
        with self.subTest(term=term):
            self.assertIn(term, section)

def test_testing_reference_routes_repository_native_gates(self) -> None:
    content = (
        SKILL_ROOT / "references" / "testing-and-change-safety.md"
    ).read_text(encoding="utf-8")
    gate_section = content.split("## Executable Gate Routing", maxsplit=1)[1]
    gate_section = gate_section.split("## ", maxsplit=1)[0]

    for term in {
        "Formatter",
        "Linter",
        "Static Analysis",
        "Build",
        "Unit",
        "Integration",
        "E2E",
        "Security",
        "Mutation",
        "blind spot",
        "authorization",
    }:
        with self.subTest(term=term):
            self.assertIn(term.lower(), gate_section.lower())
```

- [ ] **Step 2: 執行 RED**

Run:

```powershell
py -3 -m unittest `
  tests.test_skill_contract.SkillContractTests.test_delivery_readiness_does_not_lower_risk_or_authority `
  tests.test_skill_contract.SkillContractTests.test_testing_reference_routes_repository_native_gates `
  -v
```

Expected: ERROR 或 FAIL；原因是兩個新 Heading 尚不存在。

- [ ] **Step 3: 在 Skill Core 加入精簡 Delivery Readiness**

在 `Path Selection` 後加入：

```markdown
## Delivery Readiness

- **Prototype:** answer one isolated, disposable question with a repeatable Oracle; report which Production-Ready gates remain.
- **Production-Ready:** satisfy repository policy and all relevant executable gates; report deployment, UAT, and validation blind spots.

Delivery readiness never lowers the selected risk path or authorization. A Prototype that touches production data, public contracts, providers, security, or external effects still uses Full Audit.
```

- [ ] **Step 4: 補強 Agent Legibility 的抽象成本判斷**

在 `clean-code-for-agent-legibility.md` 的 `## Counter-Effects` 後加入：

```markdown
## Delivery-Stage Judgment

A Prototype needs enough naming, cohesion, and executable evidence to make the experiment understandable and repeatable; it does not need speculative production abstractions. Production-Ready work must satisfy repository policy and relevant quality gates. In both stages, reject an abstraction that only adds navigation, mapping, synchronization, or Context cost without protecting a known change source.
```

- [ ] **Step 5: 在 Testing Reference 建立 Executable Gate Routing**

在 `## Selection Rules` 前加入：

```markdown
## Executable Gate Routing

Inventory existing repository gates before selecting validation. Use the smallest set that observes the actual risk; do not install a fashionable tool or change CI without authorization.

| Gate | Use it for | It does not prove |
| --- | --- | --- |
| Formatter and Linter | Repository-defined formatting and mechanical style | Behavior, data, or side-effect correctness |
| Static Analysis and Architecture Test | Type, dependency, complexity, nullability, security, or layer rules the analyzer actually implements | Requirements absent from the configured rules |
| Build | Compilation, packaging, and configured build checks | Runtime behavior or deployment success |
| Unit, Integration, Contract, and E2E Test | Observable behavior at the boundary each test executes | Untested failures, environments, or consumers |
| Dependency and Security Scan | Known issues in the scanned dependency and configuration scope | Unknown vulnerabilities or authorization to upgrade |
| Coverage and Mutation Test | Execution reach and whether selected code changes are detected | A reliable Oracle or correct business expectation |

A Prototype requires a repeatable Oracle for its experiment and a list of Production-Ready gates not run. Production-Ready work runs all repository-required gates relevant to the Diff. Record every executed command, environment, exit code, result, and limitation; record a required gate not run as a validation blind spot.
```

保留既有 Direct／TDD／TCR／Characterization／Acceptance／Mutation 選擇表，不把 TDD 改成所有任務的固定流程。

- [ ] **Step 6: 執行 GREEN 與完整回歸**

```powershell
py -3 -m unittest discover -s tests -v
agentskills validate clean-code-ai-collaboration
git diff --check
```

Expected: PASS；Skill Body 仍不超過 500 個英文單字；Reference 沒有把 SonarQube、ESLint 或特定語言工具寫成必要依賴。

- [ ] **Step 7: Commit Delivery Readiness 與 Toolchain**

```powershell
git add clean-code-ai-collaboration/SKILL.md clean-code-ai-collaboration/references/clean-code-for-agent-legibility.md clean-code-ai-collaboration/references/testing-and-change-safety.md tests/test_skill_contract.py
git diff --cached --check
git diff --cached
git commit -m "feat(skill): route delivery readiness through repository gates"
```

---

### Task 3: 收斂 Skill 觸發並改成明確呼叫

**Files:**
- Modify: `tests/test_skill_contract.py:21-31,307-326`
- Modify: `clean-code-ai-collaboration/SKILL.md`
- Modify: `clean-code-ai-collaboration/agents/openai.yaml:1-6`

**Interfaces:**
- Consumes: Task 1 的新 Frontmatter Description 與 Task 2 的風險／成熟度路由。
- Produces: 可明確判斷的不適用情境，以及 Codex `allow_implicit_invocation: false` 契約。

- [ ] **Step 1: 寫排除條件與 Adapter RED Tests**

在 `tests/test_skill_contract.py` 新增：

```python
def test_entrypoint_excludes_tasks_without_repository_tradeoffs(self) -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")
    section = content.split("## Do Not Use", maxsplit=1)[1]
    section = section.split("## ", maxsplit=1)[0]

    for term in {
        "syntax",
        "conceptual explanation",
        "standalone example",
        "formatter",
        "more specialized Skill",
    }:
        with self.subTest(term=term):
            self.assertIn(term.lower(), section.lower())
```

在 `test_codex_adapter_exposes_open_core_work_types_and_guardrails` 的 `required_terms` 中，把：

```python
"allow_implicit_invocation: true",
```

替換為：

```python
"allow_implicit_invocation: false",
```

- [ ] **Step 2: 執行 RED**

```powershell
py -3 -m unittest `
  tests.test_skill_contract.SkillContractTests.test_entrypoint_excludes_tasks_without_repository_tradeoffs `
  tests.test_skill_contract.SkillContractTests.test_codex_adapter_exposes_open_core_work_types_and_guardrails `
  -v
```

Expected: ERROR 或 FAIL；`Do Not Use` 尚不存在，Adapter 仍為 `true`。

- [ ] **Step 3: 在 Skill 加入不適用情境**

在 `Core Principle` 後加入：

```markdown
## Do Not Use

Do not use this Skill for syntax-only questions, repository-free conceptual explanations, standalone example code, formatting fully decided by an existing formatter, or work fully covered by a more specialized Skill with no additional behavior, boundary, side-effect, or Clean Code trade-off.
```

- [ ] **Step 4: 關閉 Codex implicit invocation**

只修改 `agents/openai.yaml` 的 Policy：

```yaml
policy:
  allow_implicit_invocation: false
```

保留現有 `display_name`、`short_description` 與明確包含 `$clean-code-ai-collaboration` 的 `default_prompt`。

- [ ] **Step 5: 執行 GREEN、Validator 與入口長度檢查**

```powershell
py -3 -m unittest discover -s tests -v
agentskills validate clean-code-ai-collaboration
$skillBody = ((Get-Content -Raw 'clean-code-ai-collaboration\SKILL.md') -split '---', 3)[2]
($skillBody -split '\s+' | Where-Object { $_ }).Count
```

Expected: PASS；Adapter 只允許明確呼叫，Skill Body 不超過 500 個英文單字。

- [ ] **Step 6: Commit 觸發邊界**

```powershell
git add clean-code-ai-collaboration/SKILL.md clean-code-ai-collaboration/agents/openai.yaml tests/test_skill_contract.py
git diff --cached --check
git diff --cached
git commit -m "feat(skill): require explicit repository-aware invocation"
```

---

### Task 4: 對齊 README 與 Benchmark 外部效度邊界

**Files:**
- Modify: `tests/test_skill_contract.py:214-305`
- Modify: `tests/test_eval_contract.py`
- Modify: `README.md:7-225`
- Modify: `evals/benchmark.md:49-end`

**Interfaces:**
- Consumes: Tasks 1 至 3 的三層路徑、交付成熟度、工具鏈與 explicit-only 契約。
- Produces: 公開可用的路由說明，以及不把規劃中評測冒充成 Evidence 的狀態矩陣。

- [ ] **Step 1: 寫 README 與外部效度 RED Tests**

在 `tests/test_skill_contract.py` 的 `test_readme_documents_portability_evidence_and_limits` 增加：

```python
for term in {
    "Lightweight",
    "Standard",
    "Full Audit",
    "Prototype",
    "Production-Ready",
    "allow_implicit_invocation: false",
    "明確指定 `$clean-code-ai-collaboration`",
    "Repository 既有",
}:
    with self.subTest(v030_readme_term=term):
        self.assertIn(term, readme)

self.assertNotIn(
    "自動偵測、implicit invocation 與重新啟動行為尚待實機驗證",
    readme,
)
```

在 `tests/test_eval_contract.py` 新增：

```python
def test_benchmark_external_validity_matrix_separates_evidence_from_plans(
    self,
) -> None:
    content = (EVAL_ROOT / "benchmark.md").read_text(encoding="utf-8")
    section = content.split("## External Validity Expansion Matrix", maxsplit=1)[1]

    for state in {"已驗證", "規劃中", "尚未支持"}:
        with self.subTest(state=state):
            self.assertIn(state, section)

    for dimension in {
        "public .NET Demo",
        "large .NET Legacy",
        "TypeScript / React",
        "Python",
        "Java / Spring",
        "AGENTS.md",
        "Blind Review",
    }:
        with self.subTest(dimension=dimension):
            self.assertIn(dimension, section)

    self.assertIn("v0.2.0-initial.json", section)
    self.assertIn("沒有 Result 的項目不得寫成已驗證", section)
```

- [ ] **Step 2: 執行 RED**

```powershell
py -3 -m unittest `
  tests.test_skill_contract.SkillContractTests.test_readme_documents_portability_evidence_and_limits `
  tests.test_eval_contract.EvalContractTests.test_benchmark_external_validity_matrix_separates_evidence_from_plans `
  -v
```

Expected: FAIL；README 尚未列出新路徑與 `false` Policy，Benchmark 尚無 Expansion Matrix。

- [ ] **Step 3: 在 README 說明三層路徑與交付成熟度**

在 `Skill、Repository Policy 與自動化 Gate 的分工` 後、`安裝` 前加入：

```markdown
## 如何選擇執行深度與交付成熟度

先依風險選路徑，再標示成果準備被怎麼使用：

| 判斷 | 適用情境 |
| --- | --- |
| Lightweight | 局部、可逆，而且不影響行為與邊界的可讀性修改 |
| Standard | 已知 Repository 邊界內的一般功能、測試、修正與重構 |
| Full Audit | 公開契約、正式資料、外部副作用、第三方依賴、並行、安全、部署、權責不明或正式稽核 |
| Prototype | 回答一個隔離且可丟棄的問題；必須列出尚未通過的正式 Gate |
| Production-Ready | 準備合併、發布或長期維護；必須完成 Repository 要求且與修改相關的 Gate |

Prototype／Production-Ready 不會覆蓋風險路徑。實驗若碰到正式資料、Provider、安全或公開契約，仍需 Full Audit 與對應授權。
```

在自動化 Gate 的說明後補充：

```markdown
Skill 會優先盤點 Repository 既有的 Formatter、Linter、Static Analysis、Build、Test、Dependency／Security Scan 與其他 Gate，再選擇真正能觀察本次風險的工具。它不會因為某項工具流行就自行安裝，也不會把全綠結果擴張成未被 Oracle 涵蓋的保證。
```

- [ ] **Step 4: 將安裝與 Client 狀態改成 explicit-only**

將目前安裝段落的自動偵測說明替換為：

```markdown
`v0.3.0` 的正式使用方式是明確指定 `$clean-code-ai-collaboration`。Codex adapter 設定為 `allow_implicit_invocation: false`；安裝後若 Skill 清單沒有出現，請重新啟動 Client，再確認安裝路徑與 Skill Frontmatter。
```

在 Client 支援表的 Codex 列，將 implicit invocation 狀態改為：

```text
核心評測已完成，adapter 結構已驗證；v0.3.0 採 explicit-only，尚未以觸發準確率評測重新開啟 implicit invocation
```

保留三個使用 Prompt 對 `$clean-code-ai-collaboration` 的明確指定。

- [ ] **Step 5: 在既有 Benchmark 加入外部效度狀態矩陣**

在 `evals/benchmark.md` 的 `Initial v0.2.0 Results` 與限制之後加入：

```markdown
## External Validity Expansion Matrix

這張表區分目前公開 Evidence 與後續研究方向。沒有 Result 的項目不得寫成已驗證，也不得由格式相容推論成行為相容。

| Dimension | Status | Evidence or next gate |
| --- | --- | --- |
| public .NET Demo | 已驗證 | 固定 Repository、模型、Client 與明確載入條件；見 `v0.2.0 initial result` |
| large .NET Legacy | 規劃中 | 需要可公開或經授權的固定 Fixture、Characterization Oracle 與小型／Migration 情境 |
| TypeScript / React | 規劃中 | 需要固定 Lint、Type Check、Unit／Component／E2E Gate 與可重現 Diff Boundary |
| Python | 規劃中 | 需要固定 Formatter、Linter、Type Check、Test 與 Package Boundary 情境 |
| Java / Spring | 尚未支持 | 前三種技術棧完成後，再依可維護 Fixture 與外部貢獻決定優先順序 |
| with / without AGENTS.md | 規劃中 | 對照 Repository Instruction 是否改變 Context 定位、停止判斷與誤觸率 |
| strong / weak test suite | 規劃中 | 對照可靠 Oracle、缺少測試與錯誤測試資料下的行為與 Blind Spot |
| additional models and clients | 規劃中 | 固定其他變因後，分開測量模型與 Client；格式相容不算完成 |
| real-team Blind Review | 規劃中 | 固定候選材料並隱藏實驗組別，測量風險發現率、誤判與 Reviewer 決策時間 |

### Expansion Order

1. 先驗證 Lightweight／Standard／Full Audit 的路由、必要欄位遺漏與輸出成本。
2. 再加入 large .NET Legacy、TypeScript / React 與 Python Repository。
3. 執行契約穩定後才比較其他模型、Reasoning Effort 與 Client。
4. 最後執行 real-team Blind Review。

缺少 Token Telemetry 時只記錄可取得的輸出長度、Tool Call 與經過時間，不換算或宣稱 Token 節省。
```

寫回 `evals/benchmark.md` 時，將 `v0.2.0 initial result` 寫成 Markdown Link，target 固定為 `results/v0.2.0-initial.json`。

README 的 Benchmark 段落補上一句：`v0.3.0` 的三層路由尚未產生新 Result，現有數字仍來自 `v0.2.0` 固定情境。

- [ ] **Step 6: 執行 GREEN、完整回歸與連結檢查**

```powershell
py -3 -m unittest discover -s tests -v
agentskills validate clean-code-ai-collaboration
git diff --check
```

Expected: PASS；`evals/results/v0.2.0-initial.json`、`evals/manifest.json` 與既有 Rubric 沒有被修改。

- [ ] **Step 7: Commit 公開契約與外部效度矩陣**

```powershell
git add README.md evals/benchmark.md tests/test_skill_contract.py tests/test_eval_contract.py
git diff --cached --check
git diff --cached
git commit -m "docs: explain v0.3 routing and evaluation limits"
```

---

### Task 5: 執行 `v0.3.0` 整合驗證並停在發布授權前

**Files:**
- Verify: `clean-code-ai-collaboration/**`
- Verify: `README.md`
- Verify: `evals/benchmark.md`
- Verify: `tests/**`
- Do not modify: `evals/manifest.json`
- Do not modify: `evals/results/**`

**Interfaces:**
- Consumes: Tasks 1 至 4 的四個獨立 Commit。
- Produces: 可供 User 決定是否 Push、執行 Fresh Context 評測或準備 Release 的驗證狀態。

- [ ] **Step 1: 執行所有本機 Gate**

```powershell
py -3 -m unittest discover -s tests -v
agentskills validate clean-code-ai-collaboration
git diff --check
git status --short --branch
```

Expected: 全部測試與 Validator PASS；工作目錄沒有未提交的實作變更。

- [ ] **Step 2: 驗證 Skill 長度、版本與 explicit-only 契約**

```powershell
$skill = Get-Content -Raw 'clean-code-ai-collaboration\SKILL.md'
$skillBody = ($skill -split '---', 3)[2]
($skillBody -split '\s+' | Where-Object { $_ }).Count
rg -n 'version: "0\.3\.0"|Lightweight Path|Standard Path|Full Audit Path|allow_implicit_invocation: false' clean-code-ai-collaboration README.md tests
```

Expected: Body word count 不超過 `500`；Skill、Adapter、README 與 Tests 能找到 `v0.3.0` 三層路徑與 `false` Policy。`v0.2.0` 只出現在歷史 Benchmark、Result、Manifest Arm 或版本比較。

- [ ] **Step 3: 確認沒有偽造新的 Benchmark Evidence**

```powershell
git diff --name-only 44f3058..HEAD -- evals/manifest.json evals/results
git diff 44f3058..HEAD -- evals/benchmark.md
```

Expected: 第一個命令沒有輸出；第二個命令只包含狀態矩陣、擴充順序與主張邊界，沒有新增 `v0.3.0` 成功率、Token 節省或跨語言完成宣稱。

- [ ] **Step 4: 檢查公開內容與 Secret**

```powershell
git diff --stat 44f3058..HEAD
rg -n 'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|[A-Za-z]:[\\/][^[:space:]]+' clean-code-ai-collaboration README.md evals tests
```

Expected: 沒有 Token、Private Key、個人電腦絕對路徑或內部 Repository 資料。正常教學文字命中時逐筆人工判讀，不以 Match Count 直接宣告失敗。

- [ ] **Step 5: Review Commit 邊界與 Remote Divergence**

```powershell
git log --oneline --decorate 44f3058..HEAD
git diff --stat 44f3058..HEAD
git rev-list --left-right --count HEAD...@{upstream}
```

Expected: 三層路由、交付成熟度／工具鏈、觸發邊界、公開文件各自有獨立 Commit；Remote Divergence 如實回報。

- [ ] **Step 6: 只修正真實 Gate Failure，不建立空 Commit**

若 Step 1 至 Step 5 發現真實缺陷：先新增或收斂能重現缺陷的測試，確認 RED，再修改最小負責檔案、重跑全部 Gate，使用 `fix(skill): ...` 或 `test: ...` 建立獨立 Commit。若所有 Gate 已通過，保持工作目錄乾淨，不建立空 Commit。

- [ ] **Step 7: 停在下一項授權前**

回報：

- 四個實作 Commit 與全部 Gate 結果。
- 三層路徑、交付成熟度、工具鏈與 explicit-only 契約是否一致。
- `v0.2.0` Evidence 與 `v0.3.0` 尚未驗證項目的清楚邊界。
- Local／Remote Divergence。
- 下一步選項：Push、執行 Fresh Context 行為評測，或準備 `v0.3.0` Release。

未取得 User 明確指示前，不執行 Push、Tag、Release、跨 Repository Benchmark 或外部宣傳。
