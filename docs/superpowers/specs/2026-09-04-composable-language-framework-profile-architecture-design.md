# Clean Code AI Collaboration Skill v0.5.0 可組合語言與框架 Profile 架構設計規格

## 文件狀態

- 日期：2026-09-04
- 狀態：聊天室架構設計已核准；等待 Codex 依本規格制定實作計畫並分階段開發
- 目標版本：`v0.5.0`
- 目前版本：`v0.4.0`
- Repository：`Clean-Code-AI-Collaboration-Skill`
- 主要決策：採用單一 Monorepo、保留一個 Core Skill，透過 Language Profile 與 Framework Profile 擴充

## 版本與實作範圍

本文件同時描述長期完整架構與分階段 Roadmap，但 `v0.5.0` 的正式實作範圍只包含：

1. Profile Metadata Schema、Catalog 與驗證工具。
2. Changed Module 為中心的 Profile Selection Contract。
3. Core Skill 的最小 Routing 調整與向後相容性。
4. C#、Python、TypeScript 與 React 四個 `experimental` Profile。
5. Go、Rust、Java 與 Vue 的 `planned` Metadata 與 Roadmap，不建立空白 Reference。
6. README、Profile Authoring Guide 與一個可重現的 Specialist Package 範例。

本文件後段的 Profile Pilot、Full Run、Go、Rust、Java 與 Vue Reference 實作屬於 `v0.5.0` 後續工作。除非另有明確核准，不應把 M2、M3 自動納入第一個 Codex Implementation Plan。

## 背景

目前 `clean-code-ai-collaboration` 已經不是單純的 Clean Code 語法指南。它具備下列跨語言能力：

- Lightweight、Standard 與 Full Audit 三層風險路徑。
- Prototype 與 Production-Ready 的交付成熟度判斷。
- Repository Facts、Assumptions、Unknowns、Expected Diff 與行為邊界。
- `development_rhythm` 與 `validation_profile` 指令契約。
- Authorization Gate、Repository-native Gate 與統一 Review Output Contract。
- Tests、Evals、Benchmark Harness 與可稽核的結果文件。

這些能力大多與程式語言無關，應繼續由單一 Core Skill 維護。另一方面，C#、Go、Rust、Python、Java 與 TypeScript 各自具有不同的型別系統、錯誤模型、資源生命週期、並行語意與測試慣例；React 與 Vue 則是建立在 JavaScript／TypeScript 生態系上的框架，具有 Effect、Reactivity、Component Contract 與 UI Lifecycle 等額外風險。

若為每一種語言建立完全獨立的 Repository 或複製一套完整 Skill，Core 規則、測試、輸出契約、授權邊界與 Benchmark 基礎設施會快速漂移。若只保留一份完全通用的 Skill，又不足以可靠處理各生態系的語意風險。

因此 `v0.5.0` 要建立一個可組合架構：

```text
Core Skill
  + Language Profile
  + Framework Profile
  + Repository Policy
  + Repository-native Gates
```

本設計參考語言專用 Clean Code 指南的價值，但不把本專案做成多份靜態教學文件。Profile 的目的，是讓 Coding Agent 在實際 Repository 任務中取得更精確的判斷線索、停止條件與驗證入口。

## 問題定義

本版本需要解決六個問題：

1. **共用規則重複**：多 Repository 或多套完整 Skill 會複製 Core 規則並造成版本漂移。
2. **語言語意不足**：通用 Clean Code 原則無法充分涵蓋 Ownership、Cancellation、Goroutine、Nullability、Effect Lifecycle 等差異。
3. **框架與語言混淆**：React 與 Vue 不是程式語言，不應與 C#、Go、Rust 等放在同一分類層。
4. **Polyglot Repository 路由**：大型 Repository 可能同時包含後端、前端與自動化程式，不能只依根目錄判斷一次。
5. **Context 成本**：Agent 不應在每次任務中載入所有語言與框架內容。
6. **證據誠實性**：新增 Profile 不等於已證明有效，必須分開標示文件存在、Pilot 通過與 Full Run 完成。

## 架構決策摘要

`v0.5.0` 固定採用以下決策：

1. Repository 繼續採用 **Monorepo**，不為每種語言建立獨立 Repository。
2. 保留 `clean-code-ai-collaboration` 作為唯一正式 Core Skill 入口。
3. 語言差異放入 **Language Profile**；框架差異放入 **Framework Profile**。
4. C#、Go、Rust、Python、Java、TypeScript 屬於 Language Profile。
5. React、Vue 屬於 Framework Profile；TypeScript 納入正式規劃，作為前端共用語言層。
6. 使用者預設只需要呼叫 `$clean-code-ai-collaboration`，由 Agent 依 Repository Facts 選擇適用 Profile。
7. Source of Truth 只保留一份。未來可由 CI 產生可獨立安裝的 Specialist Skill，但不得手動維護重複的 Core 內容。
8. `v0.5.0` 不改 Repository 名稱、不改 Core Skill 名稱，也不改既有明確呼叫政策。
9. 新增 Profile 不授權安裝工具、修改依賴、改動公開契約或執行破壞性操作。
10. 已完成 Reference 與 Contract Test 的新 Profile 從 `experimental` 開始；只有 Roadmap Metadata 的 Profile 使用 `planned`，兩者都必須經過對應 Evidence Gate 才能升級。

## 目標

1. 建立可擴充且不複製 Core 規則的 Profile 架構。
2. 保留 `v0.4.0` Prompt、安裝路徑、Skill 名稱與輸出行為的向後相容性。
3. 讓 Agent 依本次 Expected Diff 所在模組選擇 Language 與 Framework Profile。
4. 支援單一語言、語言加框架，以及多模組 Polyglot 任務。
5. 定義一致的 Profile Metadata、Reference Contract、成熟度與驗證規則。
6. 讓 Profile 只補充生態系原生判斷，不重寫 CLEAN、風險路徑、授權與輸出契約。
7. 先完成 C#、Python、TypeScript 與 React 四個 Profile，再依序擴充 Go、Rust、Java 與 Vue。
8. 建立 Core Only 與 Core + Profile 的可比較 Benchmark 契約。
9. 為未來 Specialist Skill 與 Plugin Suite 的自動打包保留清楚邊界。
10. 讓外部貢獻者能依固定模板新增 Profile，而不必理解全部 Benchmark Harness 內部實作。

## 非目標

1. 不在 `v0.5.0` 一次完成八個 Production-Ready Profile。
2. 不把 React 或 Vue 定義成程式語言。
3. 不把 ASP.NET Core、FastAPI、Spring Boot、Axum、Django 等框架規則混入語言 Profile。
4. 不為每個 Profile 建立獨立 Repository、Issue Tracker 或 Release 流程。
5. 不在 Consumer Repository 建立必要的 `config.yml` 或 Profile Parser。
6. 不要求所有 Repository 採用相同 Formatter、Linter、Analyzer、Test Framework 或 Architecture Pattern。
7. 不因偵測到某個生態系，就自行安裝工具、升級套件或改寫專案結構。
8. 不把既有 `v0.2.0`、`v0.3.0` 或 `v0.4.0` Benchmark 結果重寫成 Profile 效果證據。
9. 不在本版本完成公開 Plugin Marketplace 發布或多 Repository Mirror。
10. 不直接翻譯或複製《Clean Code》或第三方語言指南中的受保護文字與範例。

## 名詞定義

### Core Skill

所有語言共同使用的決策流程，包含 CLEAN、路徑選擇、交付成熟度、Repository Facts、行為保留、授權邊界、開發節奏、驗證策略與輸出契約。

### Language Profile

補充某一程式語言或其基礎執行生態系的語意風險，例如 C# Nullable、Go Context、Rust Ownership、Python Dynamic Typing 或 Java Exception Contract。

### Framework Profile

補充建立在語言之上的框架生命週期、公開介面、狀態、Dependency Injection 或 UI 行為，例如 React Effect 與 Vue Reactivity。

### Repository Policy

Consumer Repository 已確認的命名、架構、測試、授權、工具與團隊規範，通常放在 `AGENTS.md` 或 Client 支援的 Repository Instruction 中。

### Repository-native Gate

Repository 既有且可執行的 Formatter、Linter、Static Analysis、Build、Unit／Integration／Contract／E2E Test、Security Scan、Architecture Test 或其他驗證入口。

### Specialist Skill

由 Core 與單一或少數 Profile 自動組裝的獨立安裝產物。它是 Distribution Artifact，不是另一份手動維護的 Source of Truth。

## 分層責任

四層責任必須保持分離：

| 層級 | 負責內容 | 不得取代 |
| --- | --- | --- |
| Core Skill | 跨語言決策流程、風險路徑、授權、行為保留、驗證與輸出契約 | 不得猜測語言或 Repository 特有規則 |
| Language Profile | 語言型別、錯誤、資源、並行、慣例與原生 Gate 線索 | 不得重寫 Core，也不得塞入特定 Web Framework 規則 |
| Framework Profile | Framework Lifecycle、Component／Route Contract、狀態與副作用 | 不得把 Framework 慣例宣稱成所有該語言專案的規則 |
| Repository Policy／Gate | 專案實際規範與可機器執行的門檻 | 不得由通用 Skill 或 Profile 自行發明 |

選擇與衝突的優先順序固定為：

```text
User 明確要求與授權
        ↓
Repository Policy / AGENTS.md
        ↓
本次 Expected Diff 與鄰近 Repository Facts
        ↓
Framework Profile
        ↓
Language Profile
        ↓
Core Clean Code Heuristics
```

較上層可以限制或覆寫較下層，但不能取消安全、授權、公開契約與必要驗證 Gate。

## 方案比較與選擇

### 方案 A：每個語言一個 Repository

優點是品牌與搜尋入口清楚，也容易讓不同維護者獨立管理。缺點是 Core 文件、測試、Version、Issue、CI、授權與輸出契約會重複；同一個 Core 修正必須同步到多個 Repository。

**決策：不採用。** 只有在未來維護權責、Release Cadence 與社群治理真正分離時才重新評估。

### 方案 B：單一 Repository，但每個語言放一套完整 Skill

比多 Repository 容易集中管理，但仍會產生大量 Core 複製，且多個 Skill 的觸發描述容易互相重疊。Full-stack Repository 也會讓使用者不知道該同時呼叫幾個 Skill。

**決策：不作為 Source 架構。** 未來可由 CI 產生這種獨立安裝產物，但來源仍必須由 Core + Profile 組裝。

### 方案 C：Monorepo + Core + Composable Profiles

Core 只維護一次，Profile 只補充真正不同的語意與 Gate。Agent 可以依 Changed Module 載入必要內容，也能在 Full-stack Repository 同時套用不同組合。

**決策：採用。**

## 邏輯架構

```text
User Prompt / Repository Instruction
                 │
                 ▼
     clean-code-ai-collaboration
             Core Skill
                 │
                 ▼
       Profile Selection Contract
          │                  │
          ▼                  ▼
 Language Profile(s)   Framework Profile(s)
          │                  │
          └─────────┬────────┘
                    ▼
        Repository-native Gates
                    │
                    ▼
       Unified Review Output Contract
```

Core Skill 永遠存在。Profile 是條件式補充，不會獨立取代 Core。

## Repository 結構

### `v0.5.0` 實際 Source 結構

`v0.5.0` 採取「先相容、再擴充」策略。既有七份 Core Reference 不在本版本重新命名，避免同時製造大量無價值 Diff；只建立首批四個 Profile Reference。

```text
Clean-Code-AI-Collaboration-Skill/
├── README.md
├── LICENSE
├── .github/
│   └── workflows/
│       └── validate.yml
│
├── clean-code-ai-collaboration/
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   └── references/
│       ├── clean-code-for-agent-legibility.md
│       ├── code-readability.md
│       ├── collaboration-and-estimation.md
│       ├── design-and-dependency-boundaries.md
│       ├── repository-context-template.md
│       ├── review-output-contract.md
│       ├── testing-and-change-safety.md
│       ├── profile-selection.md
│       ├── language-csharp.md
│       ├── language-python.md
│       ├── language-typescript.md
│       └── framework-react.md
│
├── profiles/
│   ├── profile.schema.json
│   ├── catalog.yaml
│   ├── csharp.yaml
│   ├── go.yaml
│   ├── rust.yaml
│   ├── python.yaml
│   ├── java.yaml
│   ├── typescript.yaml
│   ├── react.yaml
│   └── vue.yaml
│
├── scripts/
│   ├── validate_profiles.py
│   ├── build_skill_package.py
│   └── generate_profile_matrix.py
│
├── tests/
│   ├── test_skill_contract.py
│   ├── test_profile_contract.py
│   ├── test_profile_routing.py
│   ├── test_profile_packaging.py
│   └── existing tests...
│
├── evals/
│   └── existing benchmark assets...
│
└── dist/                         # Generated、Git ignored
    ├── clean-code-ai-collaboration/
    └── sample specialist package...
```

Go、Rust、Java 與 Vue 在 `v0.5.0` 只有 Planned Metadata。不得建立空白或只有標題的 `language-go.md`、`language-rust.md`、`language-java.md`、`framework-vue.md`，也不得把未完成 Reference 放入可安裝產物。

### 後續完整結構

Go、Rust、Java 與 Vue 進入 Experimental 時，才加入：

```text
clean-code-ai-collaboration/references/
├── language-go.md
├── language-rust.md
├── language-java.md
└── framework-vue.md

evals/profiles/
├── shared/
├── csharp/
├── python/
├── typescript-react/
├── go/
├── rust/
├── java/
└── vue/
```

### 目錄規則

1. `clean-code-ai-collaboration/` 是可直接安裝的正式 Core Skill。
2. `profiles/*.yaml` 是本 Repository 的 Profile Registry，不是 Consumer Repository 的設定檔。
3. Profile Markdown 放在既有 `references/` 內，讓 `SKILL.md` 能以相對連結漸進式載入。
4. `dist/` 只能由 Script 產生，不得手動修改或作為 Source of Truth。
5. Planned Profile 可以先存在於 `catalog.yaml` 與 Metadata；未有完整 Reference 時不得被打包或宣稱為可用。
6. 本版本不搬動既有 Benchmark 歷史結果，也不改寫已發布 Result 的路徑。

## Core Skill 修改範圍

`SKILL.md` 必須保持精簡，只新增 Profile Routing 入口，不把八個 Profile 的細節直接塞入 Entry Point。

建議加入以下責任：

1. 對 Repository Code Change，先確認本次 Expected Diff 所在模組。
2. 需要生態系判斷時讀取 `references/profile-selection.md`。
3. 依 Profile Selection 結果，只讀取適用的 Language／Framework Reference。
4. 在 Standard 與 Full Audit 回報實際套用的 Profile；Lightweight 只有在 Profile 改變判斷時才需要回報。
5. 沒有符合 Profile 時，繼續使用 Core，不得阻擋一般 Repository 任務。
6. Profile 不能降低風險路徑、授權、行為保留或 Repository Gate。

`SKILL.md` Body 應繼續受到既有篇幅測試限制。若新增 Profile Routing 後超過限制，應把演算法留在 `profile-selection.md`，而不是放寬 Entry Point 上限。

## Profile Metadata Contract

每個 Profile 都有一份 YAML Metadata，並通過 `profiles/profile.schema.json`。Planned Profile 可省略尚未存在的 Reference；其他狀態必須連結實際檔案。

以下為 Language Profile 範例：

```yaml
schema_version: "1.0"
id: csharp
kind: language
display_name: "C# / .NET"
status: experimental
suite_version: "0.5.0"
reference: clean-code-ai-collaboration/references/language-csharp.md

detection:
  manifest_files:
    - "*.sln"
    - "*.csproj"
  file_extensions:
    - ".cs"
  dependency_markers: []

routing:
  scope: changed-module
  load_order: 100

composition:
  requires: []
  recommends: []
  conflicts: []

evidence:
  benchmark_status: not_started
  manifests: []
  results: []
```

Framework Profile 範例：

```yaml
schema_version: "1.0"
id: react
kind: framework
display_name: "React"
status: experimental
suite_version: "0.5.0"
reference: clean-code-ai-collaboration/references/framework-react.md

detection:
  manifest_files:
    - "package.json"
  file_extensions:
    - ".jsx"
    - ".tsx"
  dependency_markers:
    - "react"
    - "react-dom"

routing:
  scope: changed-module
  load_order: 200

composition:
  requires: []
  recommends:
    - typescript
  conflicts: []

evidence:
  benchmark_status: not_started
  manifests: []
  results: []
```

`load_order` 只控制已選 Profile 的載入與 Review 順序：Language 通常先於 Framework。它不是 Winner-Takes-All 分數，也不得因數值較高就排除其他相關 Profile。

### Planned Profile 範例

```yaml
schema_version: "1.0"
id: go
kind: language
display_name: "Go"
status: planned
suite_version: "0.5.0"

detection:
  manifest_files:
    - "go.mod"
  file_extensions:
    - ".go"
  dependency_markers: []

routing:
  scope: changed-module
  load_order: 100

composition:
  requires: []
  recommends: []
  conflicts: []

evidence:
  benchmark_status: not_started
  manifests: []
  results: []
```

Planned Metadata 用來鎖定 ID、分類與 Roadmap，不代表 Runtime 支援。Routing 與 Packaging 必須忽略 Planned Profile。

### 必要欄位

| 欄位 | 說明 |
| --- | --- |
| `schema_version` | Profile Metadata Schema 版本，與 Skill SemVer 分開 |
| `id` | 穩定、全小寫、不可重複的 Profile ID |
| `kind` | 只能是 `language` 或 `framework` |
| `display_name` | README 與產物顯示名稱 |
| `status` | `planned`、`experimental`、`beta`、`stable` 或 `deprecated` |
| `suite_version` | 目前所屬 Skill Suite 版本 |
| `reference` | 非 Planned Profile 的 Markdown 路徑；Planned 必須省略 |
| `detection` | Manifest、Extension 與 Dependency 訊號 |
| `routing` | Changed Module 選擇策略與載入順序 |
| `composition` | Requires、Recommends 與 Conflicts |
| `evidence` | Benchmark 狀態與可稽核路徑 |

### Schema 規則

1. `id` 必須符合 `^[a-z][a-z0-9-]*$`。
2. 非 `planned` Profile 必須存在 `reference`，且該檔案可讀。
3. `planned` Profile 必須省略 `reference`，避免指向空白或不存在的文件。
4. `stable` 必須至少連結一份公開 Full Run Result。
5. `beta` 必須至少連結通過的 Pilot 或等價證據。
6. `experimental` 可以只有文件與 Contract Test，但 README 必須明確標示未完成效果驗證。
7. `deprecated` 必須提供 Replacement 或移除原因。
8. `requires`、`recommends`、`conflicts` 只能引用 Catalog 中存在的 ID。
9. Profile ID、Reference Path 與產物名稱必須在大小寫不敏感檔案系統上仍保持唯一。
10. Planned Profile 不得進入正式打包清單，也不得由 Routing 自動選取。

## Profile Reference Contract

每份 Profile Markdown 必須使用相同章節，避免各語言文件退化成風格偏好清單：

```markdown
# <Profile Display Name> Profile

## Use This Profile When
## Repository Facts to Inspect
## Language or Framework Semantic Risks
## Clean Code Misapplications
## Behavior and Boundary Contracts
## Repository-Native Gate Discovery
## When Another Option Fits Better
## Common Agent Failure Modes
## Stop and Escalation Conditions
## Output Additions
## Evidence Status
```

### 章節責任

- **Use This Profile When**：正面訊號與不適用範圍。
- **Repository Facts to Inspect**：Agent 在下判斷前應查閱的 Manifest、設定、鄰近測試與既有模式。
- **Semantic Risks**：該生態系真正可能改變行為的語意，不是單純排版。
- **Clean Code Misapplications**：常見的機械式重構，例如過度抽象、錯誤套用繼承、為消除警告破壞生命週期。
- **Behavior and Boundary Contracts**：API、資料、錯誤、副作用、資源與生命週期邊界。
- **Repository-Native Gate Discovery**：應優先尋找哪些既有工具，但不得自行安裝。
- **When Another Option Fits Better**：不同慣例適用的條件，避免把偏好寫成絕對規則。
- **Common Agent Failure Modes**：可追蹤且能以測試或 Repository Facts 判斷的失敗模式。
- **Stop and Escalation Conditions**：Profile 特有的高風險停止條件。
- **Output Additions**：只有本 Profile 額外要求的回報內容。
- **Evidence Status**：明確區分已觀察、推論、未知與未完成評測。

### 內容限制

1. 每份 Profile 目標上限為約 1,500 英文單字或相當篇幅的中文，超過時應拆分或刪除重複 Core 內容。
2. 不重複 CLEAN、三層路徑、Authorization Gate 或完整 Output Contract。
3. 不把特定 Library、Architecture Pattern 或團隊慣例寫成語言必然規則。
4. 每項建議必須說明何時適用、何時不適用，以及可能改變的行為。
5. 範例必須原創、最小化，而且用來說明語意差異，不建立大型教學專案。
6. Formatter 能完全決定的排版規則不應占據主要篇幅。

## Profile Selection Contract

### 選擇原則

Profile Selection 必須以本次任務的 Changed Module 與 Expected Diff 為中心，而不是只掃描 Repository Root。

```text
1. 讀取 User Prompt 與 Repository Instruction
2. 確認 Expected Diff 或最可能修改的模組
3. 尋找該模組最近的 Manifest 與設定檔
4. 以檔案副檔名確認主要語言候選
5. 以 Dependency Marker 確認 Framework 候選
6. 移除 Planned、Deprecated 或不相容候選
7. 套用零到多個 Language／Framework Profile
8. 依 load_order 載入已選 Profile
9. 保留 Core、Repository Policy 與既有 Gate
10. 回報實際套用 Profile 與無法確定的訊號
```

Metadata Validator／Routing Fixture 負責驗證預期選擇；實際 Agent 執行仍必須讀取 Repository Facts。Script 的靜態推導不能取代 Agent 對 Expected Diff、Ownership 與行為邊界的判斷。

### 選擇優先順序

1. User 對本次任務的明確 Profile 指示。
2. Repository Policy 對特定目錄或模組的明確規定。
3. Expected Diff 中的檔案類型與最近 Manifest。
4. 該模組 Manifest 中的 Framework Dependency。
5. Repository Root 訊號，只能作為補充，不能覆蓋更接近 Changed Module 的事實。
6. 無充分訊號時使用 Core Only。

`v0.5.0` 不新增必要的 Consumer Profile 設定檔。使用者可用自然語言或 Repository Instruction 明確指定 Profile，但不要求額外 Parser，也不新增另一組穩定 YAML 指令契約。

### 單一技術棧

例如 ASP.NET Core 專案在本版本只有 C# Profile 時：

```text
Core + C#
```

ASP.NET Core Framework Profile 未實作前，不得把尚未存在的規則包裝成已支援能力。

### 語言加框架

TypeScript React 專案：

```text
Core + TypeScript + React
```

TypeScript Vue 專案在 Vue 仍為 Planned 時：

```text
Core + TypeScript
Vue Profile: not available in v0.5.0
```

Vue 進入 Experimental 後才可使用：

```text
Core + TypeScript + Vue
```

純 JavaScript React 專案允許：

```text
Core + React
```

純 JavaScript Vue 專案要等 Vue Profile 進入 Experimental 後才允許：

```text
Core + Vue
```

此時不可宣稱已套用 TypeScript 型別規則。React／Vue 對 TypeScript 是 `recommends`，不是硬性 `requires`。

### Polyglot Repository

若任務同時修改：

```text
backend/    C# / .NET
frontend/   TypeScript / React
automation/ Python
```

Agent 應依模組分開套用：

```text
backend/*    → Core + C#
frontend/*   → Core + TypeScript + React
automation/* → Core + Python
```

不得因 Repository Root 存在 `.sln`，就把 C# Profile 套用到所有前端或 Python Diff。

### 模糊與衝突處理

1. 多個 Profile 同時符合且都與 Expected Diff 有關時，可以組合使用。
2. 多個 Profile 符合但任務範圍不清楚時，先查閱鄰近 Manifest、測試與 Repository Instruction。
3. 仍無法確認，而 Profile 差異會影響公開行為、資料、資源或副作用時，列為 Unknown 並停止在需要人類確認的邊界。
4. 差異只影響非關鍵 Review 視角時，可以 Core Only 繼續，但必須回報未套用 Profile 的原因。
5. Metadata `conflicts` 命中時不得自行選一個；必須依 User／Repository Policy 解決，否則停止。
6. 找不到支援 Profile 不是錯誤；Core Skill 必須保持可用。
7. Planned Profile 命中偵測訊號時，只能回報「規劃中」，不得讀取不存在的 Reference 或假裝套用。

## Profile 套用後的輸出

Profile 不新增另一套完整輸出格式。

- **Lightweight**：只有 Profile 確實改變選擇或驗證時，才在簡短回報中說明。
- **Standard**：在 `Decision Basis` 或 `Selected Approach` 內列出 `Profiles Applied`。
- **Full Audit**：把 Profile 選擇的 Repository Facts、Unknowns 與 Evidence 納入既有追蹤契約。

建議格式：

```text
Profiles Applied: language=csharp; framework=none
Profile Basis: nearest project file is src/App/App.csproj; Expected Diff is limited to .cs files under src/App
```

Profile 選擇本身不是成功證據。實際行為仍由 Diff、Repository Gate 與獨立 Oracle 支持。

## 首批 Profile 範圍

### C# / .NET Language Profile

核心議題：

- Nullable Reference Types 與既有 Null Contract。
- `async`／`await`、同步封鎖與 async-over-sync。
- `CancellationToken` 傳遞、取消語意與公開 API 相容性。
- `IDisposable`／`IAsyncDisposable` 與 Resource Lifetime。
- LINQ Deferred Execution、Enumeration 次數與 Side Effect。
- `record`、Class、Value Equality 與 Serialization Contract。
- Dependency Injection Lifetime 與 Scope Boundary。
- Exception Type、Result Mapping、HTTP Status 與失敗語意。
- Analyzer、Formatter、Build、Test、Architecture Test 的既有入口。

不得把 ASP.NET Core、EF Core 或特定 Clean Architecture 模板寫成所有 C# 專案的規則；這些應由後續 Framework Profile 或 Repository Policy 負責。

### Python Language Profile

核心議題：

- Dynamic Typing、Type Hint 與實際 Runtime Contract。
- Mutable Default、共享狀態與 Import-time Side Effect。
- Context Manager、Generator Cleanup 與 Resource Lifetime。
- Sync／Async Boundary、Coroutine 遺漏與 Event Loop 語意。
- Exception Boundary、錯誤 Mapping 與過度捕捉。
- Protocol、Dependency Injection 與 Duck Typing 的適用條件。
- Package Boundary、Circular Import 與 `__init__` Side Effect。
- Pytest、Ruff、Formatter、Type Checker 與 Repository 既有 Gate。

FastAPI、Django 等框架行為不得全部塞入 Python Profile。

### TypeScript Language Profile

核心議題：

- Structural Typing 與意外相容。
- Union Narrowing、Exhaustiveness 與 `never`。
- `undefined`、`null`、Optional Property 與序列化差異。
- Promise、未處理拒絕、Async Return Contract。
- Public Type、Runtime Validation 與 Compile-time Guarantee 的邊界。
- Module Boundary、Type-only Import 與 Circular Dependency。
- Type Assertion、`any`、`unknown` 與安全降級。
- Type Check、Lint、Unit Test 與 Build Gate。

TypeScript Profile 不包含 React Hook 或 Vue Reactivity 規則。

### React Framework Profile

核心議題：

- Render、Effect 與 Cleanup Lifecycle。
- Dependency Array、Callback／Object Identity 與 Stale Closure。
- Request Abort、Race Condition 與已取消結果覆蓋。
- State Ownership、Derived State 與 Single Source of Truth。
- Controlled／Uncontrolled Component Contract。
- Props、Context、Error、Loading 與 UI 行為保留。
- Strict Mode 下的副作用與測試假設。
- React Testing Library、Component Test、Type Check、Lint 與 E2E Gate。

不得為消除 Hook Warning 而偷偷改變使用者可觀察行為，也不得在沒有需求時導入新的 State Management Library。

## 後續 Profile 範圍

以下內容定義 Roadmap 與未來 Reference 邊界，不屬於首個 `v0.5.0` Implementation Plan。

### Go Language Profile

- Error Value、Wrapping、Sentinel 與錯誤比對。
- `context.Context` 傳遞、取消與 Deadline。
- Goroutine Ownership、Leak、Channel Close 與 Backpressure。
- `nil` Interface、Zero Value 與 Pointer／Value Receiver。
- Interface Placement、Package Boundary 與過度抽象。
- Table-driven Test、Race Detector、Vet、Lint 與 Repository Gate。

### Rust Language Profile

- Ownership、Borrowing、Lifetime 與 Clone 成本。
- `Result`、`Option`、Error Conversion 與 Panic Boundary。
- Trait Boundary、Generic／Dynamic Dispatch 取捨。
- `unsafe` Safety Invariant、FFI 與 Escalation Gate。
- `Send`／`Sync`、Async Runtime 與 Concurrency。
- Cargo Check、Clippy、Fmt、Test、Miri 或 Repository 既有工具。

### Java Language Profile

- Nullability、Optional 與 API Contract。
- Checked／Unchecked Exception 與 Mapping Boundary。
- Record、Class、Equality 與 Serialization。
- Stream Lazy Evaluation、Side Effect 與 Parallel Stream。
- Resource Management 與 `try-with-resources`。
- Thread Safety、Immutability 與 Concurrency。
- Maven／Gradle、Compiler、Static Analysis 與 Test Gate。

Spring Boot、JPA Transaction 等應由 Framework Profile 處理。

### Vue Framework Profile

- `ref`、`reactive` 與 Identity。
- `computed`、`watch`、`watchEffect` 的責任與 Cleanup。
- Composition API Lifecycle 與 Async Side Effect。
- Props、Emits、Slot 與 Public Component Contract。
- Local State、Composable、Pinia 與 Ownership Boundary。
- Deep Watch、Template Reactivity 與不必要重新計算。
- Component Test、Type Check、Lint 與 E2E Gate。

## 成熟度模型

| 狀態 | 進入條件 | 可公開宣稱 |
| --- | --- | --- |
| `planned` | 已列入 Roadmap，只有 Metadata | 僅宣稱規劃中，不可自動路由或打包 |
| `experimental` | Reference、Metadata 與 Contract Test 完成 | 可供試用；未證明相對 Core 的額外效果 |
| `beta` | 固定 Fixture 與 Pilot 通過，Result／限制可稽核 | 已通過有限情境 Pilot，不外推到所有 Repository |
| `stable` | Full Run、公開 Result、回歸 Gate 與維護 Owner 完整 | 在已記錄條件下具備穩定證據，仍不宣稱普遍保證 |
| `deprecated` | 有替代方案或停止維護決策 | 明確標示 Replacement、遷移與移除版本 |

首批 C#、Python、TypeScript、React 在程式碼合併時一律先標為 `experimental`。Go、Rust、Java、Vue 在 `v0.5.0` 維持 `planned`。既有 .NET、TypeScript／React 與 Python Benchmark 可以作為 Fixture 與研究方法基礎，但不能直接把新 Profile 升級成 `beta`，因為過去比較的是 Core Skill，不是 Core + Profile 的增量效果。

## Versioning

1. Core Skill 與所有 Profile 使用同一個 Suite SemVer。
2. Profile Metadata 的 `suite_version` 必須與 Release 版本一致。
3. Profile 成熟度不等於 SemVer；例如 `v0.5.0` 可以同時包含 Experimental 與 Planned Profile。
4. 新增向後相容 Profile 屬於 Minor Release。
5. 修正文句、偵測訊號或不改變契約的 Profile Bug 屬於 Patch Release。
6. 改變 Profile ID、選擇優先權、公開輸出契約或移除既有 Profile，需要依相容性決定 Major Release。
7. Benchmark Version、Fixture Version 與 Profile Schema Version 分開管理，不能以 Skill Version 取代。

## Source 與 Distribution

### Source of Truth

以下只能在 Monorepo 內維護一次：

- Core `SKILL.md`。
- Core References。
- Profile Markdown。
- Profile Metadata。
- Schema、Tests、Evals 與 Packaging Scripts。

### Core Package

`clean-code-ai-collaboration/` 繼續是主要可安裝產物。它包含所有非 Planned、非 Deprecated 的 Profile Reference，但透過漸進式路由避免每次載入全部內容。

### Specialist Package

未來可以產生：

```text
clean-code-ai-csharp
clean-code-ai-go
clean-code-ai-rust
clean-code-ai-python
clean-code-ai-java
clean-code-ai-typescript
clean-code-ai-react
clean-code-ai-vue
```

每個 Specialist Package 可以複製必要 Core 文件以確保獨立安裝，但只能由 `build_skill_package.py` 產生。生成檔案應包含來源 Commit、Suite Version、Profile ID 與內容雜湊，避免產物無法追蹤。

`v0.5.0` 的 Definition of Done 不要求公開發行全部 Specialist Package。至少要完成一個可重現的範例打包與 Contract Test，證明架構可行；正式發布應等待對應 Profile 至少達到 `beta`。

### Plugin Suite

Plugin Manifest、Marketplace 發布與完整 Suite 安裝屬於後續版本。`v0.5.0` 只保留 Packaging Boundary，不把 Plugin 當成核心開發阻礙。

## 向後相容性

`v0.5.0` 必須保證：

1. 既有 `$clean-code-ai-collaboration` 呼叫方式不變。
2. 既有 `development_rhythm` 與 `validation_profile` 優先順序不變。
3. Consumer Repository 不需要新增 Profile 設定檔。
4. 找不到 Profile 時，Core Skill 繼續工作。
5. `allow_implicit_invocation: false` 維持不變，除非另有獨立觸發評測與設計規格。
6. 既有 Core Reference Path 在 `v0.5.0` 不重新命名。
7. 既有 Benchmark Result、Manifest 與 Receipt 不因新 Profile 改寫。
8. Profile 不得讓原本 Standard 任務自動升級成 Full Audit；只有實際發現的風險事實可以升級。
9. Profile 不得把原本未授權的外部操作變成已授權。
10. Planned Profile 不得改變既有 Core 行為。

## 驗證與 CI

### Profile Contract Tests

至少驗證：

- 所有 YAML 通過 JSON Schema。
- ID、Reference Path 與 Generated Package Name 唯一。
- 非 Planned Reference 實際存在。
- Planned Profile 沒有 `reference`。
- Required／Recommended／Conflict ID 可解析。
- Stable／Beta 的 Evidence 路徑與狀態符合成熟度規則。
- Planned Profile 不會進入 Routing 或 Packaging。
- Profile Markdown 具備所有必要章節。
- Profile 與 Core 文件不存在未完成占位內容。
- Entry Point 仍低於既有篇幅限制。

### Routing Tests

使用小型 Fixture 驗證：

1. 純 C# 模組只選 `csharp`。
2. Python 模組只選 `python`。
3. TypeScript React 模組選 `typescript + react`。
4. JavaScript React 模組只選 `react`，不得假裝套用 TypeScript。
5. TypeScript Vue 模組在 `v0.5.0` 只選 `typescript`，並把 Vue 標示為 Planned／Unavailable。
6. Vue 進入 Experimental 後，相同 Fixture 才選 `typescript + vue`。
7. Polyglot Repository 依 Changed Module 分開選擇。
8. 根目錄 `.sln` 不得污染前端 Changed Module。
9. 無支援語言時回到 Core Only。
10. User／Repository 明確指定優先於自動訊號。
11. Conflict 無法解析時 Fail Closed。
12. Planned Profile 命中訊號時不會被載入或打包。

### Packaging Tests

- 同一 Source Commit 產生相同檔案與內容雜湊。
- Specialist Package 只包含 Core 與選定 Profile 所需檔案。
- Generated `SKILL.md` Frontmatter 名稱與 Metadata 一致。
- Generated Package 可通過 `agentskills validate`。
- `dist/` 不是手動 Source，乾淨 Checkout 可重新產生。
- Planned Profile 無法作為 Packaging Target。

### Existing Regression Tests

既有 `test_skill_contract.py`、Benchmark Harness Test、Strategy Full Run Verification 與 Open Standard Validation 必須繼續通過。若需要重構固定的 `REFERENCE_NAMES`，測試應改成「Core Reference + Catalog 中可用的 Profile Reference」契約，不得單純刪除完整性檢查。

### CI 建議流程

```text
1. Install validation dependencies
2. Run repository unit tests
3. Validate profile schema and catalog
4. Validate profile reference contract
5. Run routing fixtures
6. Build deterministic sample package
7. Validate Core Skill open standard
8. Validate generated sample Specialist Skill
9. Compile benchmark harness
```

## Profile Benchmark 設計

Profile Benchmark 屬於 M2，不是首個 `v0.5.0` Implementation Plan 的完成條件；本節先固定研究方法，避免日後先看結果再決定比較方式。

### 單一 Profile 的最低比較組

對只有一個 Profile 的 Scenario，至少包含：

1. `control`：只有任務與 Repository Instruction。
2. `generic-clean-code`：額外要求遵守 Clean Code。
3. `core-only`：載入相同版本 Core Skill，但禁止 Profile。
4. `core-plus-profile`：載入相同版本 Core Skill與指定 Profile。

只有比較第 3、4 組，才能回答該 Profile 是否提供 Core 之外的增量價值。

### 複合技術棧的歸因

TypeScript + React 不能只比較 `core-only` 與 `core-plus-typescript-react`，然後分別宣稱 TypeScript 或 React 有效。至少需要：

1. `core-only`
2. `core-plus-typescript`
3. `core-plus-typescript-plus-react`

TypeScript 的增量效果比較第 1、2 組；React 的增量效果比較第 2、3 組。Control 與 Generic Clean Code 仍可保留作廣義 Baseline。

若純 JavaScript React Scenario 要測 React，可比較：

```text
core-only
core-plus-react
```

每份公開 Result 必須明確說明它評估的是單一 Profile、Profile Pack，或整個組合，不得把組合結果錯誤歸因給其中一層。

### Scenario 類型

每個 Profile 至少需要：

1. **Shared Business Scenario**：與其他語言共用相同業務規則，例如時間邊界、狀態轉換、錯誤契約或外部副作用。
2. **Ecosystem-native Scenario**：專門測量該語言或框架的語意，例如 Cancellation、Goroutine Leak、Ownership、Effect Cleanup。

不同 Profile 可以共用 Fixture Repository 與業務題目，但 Treatment Arm、Allowed Diff、Oracle 與歸因邊界必須能區分。

### 建議矩陣

| Profile | Shared Scenario | Ecosystem-native Scenario |
| --- | --- | --- |
| C# | High Priority 時間邊界 | Cancellation／Async Disposal／DI Lifetime |
| Python | High Priority 時間邊界 | Async Cleanup／Protocol／Dependency Override |
| TypeScript | Public Work Item Contract | Union Narrowing／Runtime Validation |
| React | UI 狀態與錯誤保留 | Effect Lifecycle／Abort／Stale Closure |
| Go | 狀態與錯誤契約 | Context Cancellation／Goroutine Leak |
| Rust | 狀態與錯誤契約 | Ownership／Error Propagation／Unsafe Boundary |
| Java | 狀態與錯誤契約 | Resource／Exception／Concurrency |
| Vue | UI 狀態與錯誤保留 | Watch Cleanup／Reactivity Identity |

### 歷史證據邊界

- `v0.2.0` Repository Benchmark 保持歷史結果。
- `v0.3.0` Cross-language Benchmark 保持 Core Skill 外部效度研究，不改標成 Profile Benchmark。
- `v0.4.0` Strategy Decision-Conformance 保持策略契約研究。
- Profile Benchmark 使用新的 Manifest、Version 與 Result 路徑。
- 新 Profile 未完成 Full Run 前，README 不得使用「已證明支援所有該語言專案」等敘述。

## Documentation 設計

實作完成後，README 應新增：

1. Core + Profile 架構簡介。
2. Supported Profile Matrix。
3. Language 與 Framework 的分類說明。
4. 自動選擇與 Explicit Instruction 的使用方式。
5. Polyglot Repository 範例。
6. Profile 成熟度與 Evidence Link。
7. 貢獻新 Profile 的入口。
8. Specialist Package 尚未正式發布時的清楚限制。

`v0.5.0` 發布時建議矩陣：

| Profile | Kind | Status | Reference | Benchmark |
| --- | --- | --- | --- | --- |
| C# / .NET | Language | Experimental | Available | Not started |
| Python | Language | Experimental | Available | Not started |
| TypeScript | Language | Experimental | Available | Not started |
| React | Framework | Experimental | Available | Not started |
| Go | Language | Planned | Not available | Not started |
| Rust | Language | Planned | Not available | Not started |
| Java | Language | Planned | Not available | Not started |
| Vue | Framework | Planned | Not available | Not started |

矩陣必須由 `catalog.yaml` 產生或至少由 CI 驗證一致，避免 README 與真實狀態漂移。

## 貢獻者契約

新增 Experimental Profile 的 Pull Request 必須同時提供：

1. Profile Metadata。
2. 符合固定章節的 Profile Reference。
3. Detection 與 Routing Fixture。
4. Contract Test。
5. README Matrix 更新或可重現的自動生成結果。
6. Evidence Status 與未完成項目，不得空白省略。
7. 原創內容或清楚授權與 Attribution。
8. 不重複 Core 規則的自我檢查。

只新增 Planned Profile 時，可以只有 Metadata 與 Catalog 更新，但必須省略 `reference`，且不得啟用 Routing／Packaging。

Profile Reviewer 至少檢查：

- 語意是否真正屬於該語言／框架。
- 是否把個人偏好寫成絕對規則。
- 是否保留替代方案與適用條件。
- 是否可能讓 Agent 擅自擴張 Diff、安裝依賴或更改公開行為。
- 是否有可執行 Gate 或明確 Blind Spot。

## 著作權與 Attribution

本專案可以受到《Clean Code》與公開語言指南啟發，但必須遵守以下規則：

1. 使用自己的組織、文字與範例表達原則。
2. 不大量複製書籍文字、章節或範例。
3. 不把第三方 Repository 的內容直接翻譯後宣稱為本專案原創。
4. 若實際衍生自 MIT 或其他授權內容，必須保留要求的 Copyright、License 與 Attribution。
5. Profile 的主要價值應是 AI Agent 工作流程、Repository Context、行為邊界與驗證設計，而不是重製既有 Clean Code 書籍。

## 實作里程碑

### M0-A：Profile Structural Contract

範圍：

- 新增 `profile.schema.json` 與 `catalog.yaml`。
- 加入八個 Profile Metadata；首批四個為 `experimental`，其餘為 `planned`。
- 新增 Profile Contract Tests。
- 不修改 Core Routing 行為。

完成條件：

- Schema、Catalog、ID、Status、Reference 與 Composition 驗證全數通過。
- Planned Profile 不可被 Routing 或 Packaging 使用。
- Planned Profile 不建立空白 Reference。

### M0-B：Profile Selection 與 Core Routing

範圍：

- 新增 `references/profile-selection.md`。
- 在 `SKILL.md` 加入最小 Routing 入口。
- 新增 Changed Module 與 Polyglot Fixtures。
- 更新 Output Contract 的 Profile 回報規則。

完成條件：

- 既有 Prompt 不需修改。
- 無 Profile 時維持 Core 行為。
- TypeScript React 能選出兩層 Profile。
- Planned Vue 不會被誤載入。
- Entry Point 篇幅與所有既有測試通過。

### M1-A：C# Profile

範圍：

- 完成 `language-csharp.md`。
- 增加 C# Routing 與 Semantic Contract Tests。
- 標示為 `experimental`。

完成條件：

- 不包含 ASP.NET Core 專屬規則。
- 能明確處理 Nullability、Cancellation、Resource、LINQ、Equality 與 DI Lifetime 風險。

### M1-B：Python Profile

範圍：

- 完成 `language-python.md`。
- 增加 Python Routing 與 Semantic Contract Tests。
- 標示為 `experimental`。

完成條件：

- 不把 FastAPI 或 Django 當成 Python 通則。
- 能涵蓋 Dynamic Typing、Mutable State、Async、Cleanup 與 Exception Boundary。

### M1-C：TypeScript 與 React Profiles

範圍：

- 完成 `language-typescript.md` 與 `framework-react.md`。
- 驗證 TypeScript React 與 JavaScript React 的不同組合。
- 標示為 `experimental`。

完成條件：

- TypeScript 規則與 React Lifecycle 規則分離。
- JavaScript React 不會誤報 TypeScript Profile。
- 既有 React Benchmark Fixture 可作後續 Profile Pilot 基礎。

### M1-D：README、Authoring Guide 與 Sample Packaging

範圍：

- 新增 Profile Matrix 與使用說明。
- 新增 Profile Authoring Guide。
- 完成至少一個可重現 Specialist Package 範例。

完成條件：

- README 狀態與 Catalog 一致。
- Generated Package 通過 Open Standard Validation。
- 不公開發布未達 Beta 的 Specialist Package。

### `v0.5.0` Release Boundary

M0-A、M0-B、M1-A、M1-B、M1-C 與 M1-D 是 `v0.5.0` 的實作與驗收範圍。完成後先進行規格對照、測試與 Release Review；不要在同一個未重新核准的計畫中自動接續 M2 或 M3。

### M2：Profile Pilot

範圍：

- 為首批四個 Profile 建立 Core Only、Core + Language 與必要的 Core + Language + Framework 比較。
- 固定 Fixture、Prompt、Allowed Diff、Oracle、Rubric 與歸因邊界。
- 公開 Pilot Result 與限制。

完成條件：

- 只有通過固定 Pilot 的 Profile 可升級為 `beta`。
- 失敗與無差異結果同樣保留，不因結果不理想而重寫契約。
- 複合 Stack 結果不錯誤歸因給單一 Profile。

### M3：Go、Rust、Java、Vue

順序建議：

1. Go：驗證低抽象、Context 與 Goroutine 邊界。
2. Rust：驗證 Ownership、Error 與 Unsafe 邊界。
3. Java：驗證企業型語言的 Exception、Resource 與 Concurrency。
4. Vue：建立在 TypeScript Profile 與前端 Routing 經驗上。

每個 Profile 仍走 Planned → Experimental → Pilot → Beta → Full Run → Stable，不得因文件完成直接跳級。

## Codex 執行邊界

Codex 開始開發前應先：

1. 讀取本規格、目前 `SKILL.md`、所有既有 Core Reference、Tests、CI 與 Benchmark Contract。
2. 盤點本規格與目前 Repository 的實際差異，不假設目錄或工具已存在。
3. 產生獨立 Implementation Plan，將 M0-A 至 M1-D 拆成可驗證的小步驟。
4. 保留現有 Tests 與公開 Result，不以重寫歷史證據來讓新 Contract 通過。
5. 對依賴安裝、Release、Tag、外部 Repository、正式 Benchmark Run 或其他外部操作保留 Authorization Gate。
6. 在未取得下一階段核准前停止於 `v0.5.0` Release Boundary。

## 驗收條件

`v0.5.0` 架構層完成時，必須同時符合：

1. Repository 仍只有一個手動維護的 Core Skill。
2. `$clean-code-ai-collaboration` 與既有設定契約保持相容。
3. Profile Metadata、Schema、Catalog 與 Markdown Contract 完整。
4. C#、Python、TypeScript、React 四個 Experimental Profile 可被正確選取。
5. Go、Rust、Java、Vue 以 Planned 狀態存在，沒有空白 Reference，且不會被誤用。
6. Polyglot Routing 使用 Changed Module，不依 Root 一次套用全部。
7. Core Only Fallback 可用。
8. Profile 不重複或覆蓋 Core 授權、路徑與輸出契約。
9. Existing Tests、Profile Tests、Routing Tests、Packaging Sample 與 `agentskills validate` 全數通過。
10. README 不把 Experimental／Planned 描述成 Stable Support。
11. 既有 Benchmark Result 未被改寫。
12. 文件與 Metadata 沒有未完成占位內容、空白 Evidence 宣稱或不可解析的 Profile 引用。
13. TypeScript + React Benchmark 設計具備可分離的 Profile 歸因邊界。
14. M2、M3 未在沒有下一階段核准的情況下被提前實作。

## 風險與緩解

### 風險：Profile 文件大量重複 Core

緩解：固定 Reference Contract、篇幅上限、Reviewer Checklist 與重複內容檢查；Core 概念以連結引用，不重新解釋。

### 風險：自動偵測選錯技術棧

緩解：以 Changed Module 與最近 Manifest 為主；Root 只作補充；允許 Core Only；關鍵衝突 Fail Closed。

### 風險：Planned Profile 被當成已支援

緩解：Planned 必須省略 Reference；Routing、Packaging 與 README Contract Test 都要阻止誤用。

### 風險：Profile 過度規範生態系

緩解：每項規則必須說明適用條件、替代方案與 Repository Facts；禁止把特定 Pattern 當成普遍答案。

### 風險：Context 膨脹

緩解：`SKILL.md` 只路由，不內嵌 Profile；每次只讀本次模組相關 Reference；Profile 設定篇幅上限。

### 風險：Profile 存在但沒有證據

緩解：成熟度模型與 Evidence 欄位強制分離；已實作 Profile 從 Experimental 開始；README 顯示真實狀態。

### 風險：Benchmark 錯誤歸因

緩解：Language 與 Framework 使用階梯式 Treatment Arm；公開 Result 明確標示評估的是單一 Profile 或 Profile Pack。

### 風險：Generated Specialist Skill 漂移

緩解：禁止手動修改 `dist/`；生成內容保存 Commit、Version 與 Hash；CI 驗證可重現。

### 風險：一次開發八個 Profile 導致品質下降

緩解：`v0.5.0` 只完成 Architecture 與四個首批 Profile；Go、Rust、Java、Vue 在前一批 Contract 穩定並重新核准後加入。

## 未來拆分 Repository 的條件

只有符合多數下列條件時才重新評估：

- 某 Profile 已有獨立 Maintainer 與明確 Ownership。
- Release Cadence 與 Core 長期不同。
- Issue／PR 流量已無法在 Monorepo 有效分類。
- Profile 已形成不同 Workflow，而不只是 Reference 補充。
- 需要不同 License、治理或安全審查。
- Profile 的 Tests、Evals、Docs 與 Release 能獨立運作。
- 社群確實需要獨立品牌與入口。

即使拆分，優先採用由 Monorepo 自動同步的 Distribution Repository，而不是建立兩份可寫 Source。

## 最終決策

`Clean-Code-AI-Collaboration-Skill` 將以 Monorepo 繼續發展。`clean-code-ai-collaboration` 保持單一 Core Skill，Language Profile 與 Framework Profile 依 Changed Module 組合使用；TypeScript 作為 React／Vue 共同語言層，React 與 Vue 保持 Framework 分類。

`v0.5.0` 完成 Profile Contract、Routing、C#、Python、TypeScript 與 React，並只為 Go、Rust、Java、Vue 建立 Planned Metadata。獨立 Specialist Skill 只作自動生成的 Distribution Artifact，不作新的手動維護來源。

Profile Pilot、正式結果與剩餘 Profile 屬於下一階段。這個設計的核心不是增加更多規則，而是讓共用判斷維持一致、讓語言差異只在需要時被載入，並讓每個「支援」主張都能對應到清楚的 Repository Facts、驗證與 Evidence Boundary。
