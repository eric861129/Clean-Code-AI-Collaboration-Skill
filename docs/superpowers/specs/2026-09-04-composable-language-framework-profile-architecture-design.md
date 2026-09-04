# Clean Code AI Collaboration Skill v0.5.0 可組合語言與框架 Profile 架構設計規格

## 文件狀態

- 日期：2026-09-04
- 狀態：設計已核准；下一步制定 Implementation Plan，計畫再次核准後才開始開發
- 目標版本：`v0.5.0`
- 目前版本：`v0.4.0`
- Repository：`Clean-Code-AI-Collaboration-Skill`
- 主要決策：採用單一 Monorepo、保留一個 Core Skill，透過 Language Profile 與 Framework Profile 擴充

## 版本與實作範圍

本文件同時描述長期完整架構與分階段 Roadmap，但 `v0.5.0` 的正式實作範圍只包含：

正式實作前必須先修復 v0.4.0 歷史驗證器，使它依 Receipt 指定的歷史 Revision 與 Git Blob Bytes 驗證，不再依賴目前 Worktree 或 Checkout EOL；既有 Result、Manifest 與 Receipt 保持不變。

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
7. Source of Truth 只保留一份。未來可由 CI 產生可獨立安裝的 Specialist Package，但不得手動維護重複的 Core 內容。
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
9. 為未來 Specialist Package 與 Plugin Suite 的自動打包保留清楚邊界。
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

補充某一程式語言、標準 Runtime、標準 Library 與 Project System 的語意風險，例如 C# Nullable、Go Context、Rust Ownership、Python Dynamic Typing 或 Java Exception Contract。選用的 DI、Container 或其他生態系機制只有在 Repository Facts 證明已使用時才能成為檢查對象；Language Profile 不得規定特定實作。

### Framework Profile

補充建立在語言之上的框架生命週期、公開介面、狀態、Dependency Injection 或 UI 行為，例如 React Effect 與 Vue Reactivity。

### Repository Policy

Consumer Repository 已確認的命名、架構、測試、授權、工具與團隊規範，通常放在 `AGENTS.md` 或 Client 支援的 Repository Instruction 中。

### Repository-native Gate

Repository 既有且可執行的 Formatter、Linter、Static Analysis、Build、Unit／Integration／Contract／E2E Test、Security Scan、Architecture Test 或其他驗證入口。

### Specialist Package

由 Core 與單一或少數 Profile 自動組裝的 Distribution Artifact，內含一個可獨立安裝的 Skill；它不是另一份手動維護的 Source of Truth。

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
│   ├── generate_profile_matrix.py
│   └── package-manifest.schema.json
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
    └── clean-code-ai-csharp/     # v0.5.0 唯一 Sample Package
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
2. `profiles/*.yaml` 是本 Repository 在維護、CI 與 Packaging 階段使用的 Profile Registry，不是 Consumer Repository 的設定檔，也不是 Runtime 必須解析的輸入。
3. `scripts/generate_profile_matrix.py` 必須從 Catalog 與 Metadata 產生 `references/profile-selection.md` 的 Runtime Profile Index 與 README 的 Supported Profile Matrix；兩個 Checked-in 區塊使用下列唯一固定 Marker，CI 以 `--check` 驗證沒有漂移。產生區塊不得手動修改或成為第二份 Source of Truth。

```markdown
<!-- profile-matrix:generated:start -->
<!-- profile-matrix:generated:end -->

<!-- runtime-profile-index:generated:start -->
<!-- runtime-profile-index:generated:end -->
```

一般模式只能替換成對 Marker 之間的內容；`--check` 完全 Read-only。Marker 缺失、重複、交錯或 End 先於 Start 時必須 Fail Closed，不得重寫整份文件。
4. Consumer Runtime 只讀取 `SKILL.md` 與相關 Markdown Reference，不需要 YAML Parser。
5. Profile Markdown 放在既有 `references/` 內，讓 `SKILL.md` 能以相對連結漸進式載入。
6. `dist/` 必須加入 `.gitignore`，只能由 Script 產生，不得手動修改、Commit 或作為 Source of Truth。
7. Planned Profile 可以先存在於 `catalog.yaml` 與 Metadata；未有完整 Reference 時不得被打包或宣稱為可用。
8. 本版本不搬動既有 Benchmark 歷史結果，也不改寫已發布 Result 的路徑。

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

Metadata 與 Catalog 驗證使用 Python 3.12，並在 `requirements-dev.txt` 直接 Pin `PyYAML` 與 `jsonschema`；不得依賴間接相依套件或自行實作 YAML Parser。JSON Schema 使用 Draft 2020-12。

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
  owning_manifests:
    - pattern: "*.csproj"
      boundary: project
  supporting_files:
    - "*.sln"
    - "*.slnx"
    - "Directory.Build.props"
    - "Directory.Build.targets"
    - "global.json"
  file_extensions:
    - ".cs"
  dependency_markers: []
  supporting_dependencies: []

routing:
  scope: changed-module
  load_order: 100

composition:
  requires: []
  recommends: []
  conflicts: []

ownership:
  maintainers:
    - eric861129

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
  owning_manifests:
    - pattern: "package.json"
      boundary: package
  supporting_files: []
  file_extensions:
    - ".jsx"
    - ".tsx"
  dependency_markers:
    - "react"
  supporting_dependencies:
    - "react-dom"
    - "react-native"

routing:
  scope: changed-module
  load_order: 200

composition:
  requires: []
  recommends:
    - typescript
  conflicts: []

ownership:
  maintainers:
    - eric861129

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
  owning_manifests:
    - pattern: "go.mod"
      boundary: project
  supporting_files:
    - "go.work"
  file_extensions:
    - ".go"
  dependency_markers: []
  supporting_dependencies: []

routing:
  scope: changed-module
  load_order: 100

composition:
  requires: []
  recommends: []
  conflicts: []

ownership:
  maintainers:
    - eric861129

evidence:
  benchmark_status: not_started
  manifests: []
  results: []
```

Planned Metadata 用來鎖定 ID、分類與 Roadmap，不代表 Runtime 支援。Routing 與 Packaging 必須忽略 Planned Profile。

### Detection Metadata Semantics

1. `owning_manifests` 是有序物件清單；每筆包含檔名 `pattern` 與 `boundary`。`boundary` 只能是 `project`、`package` 或 `workspace`。
2. `supporting_files` 只能補強語言、版本、Workspace 或 Project 設定事實，不能單獨建立 Changed Module 或啟用 Profile。
3. `file_extensions` 是 Language Candidate 的主要訊號；Framework 的 Extension 只作與 Changed Module 相關性的輔助證據。
4. `dependency_markers` 建立 Framework Candidate；`supporting_dependencies` 只能辨識 Renderer 或補強適用範圍。
5. Package Dependency 只從 `dependencies`、`devDependencies`、`peerDependencies` 與 `optionalDependencies` 尋找；Lockfile 不參與 Marker 查找。
6. Metadata 中的 Pattern 使用大小寫敏感的 POSIX-style 相對名稱比對；Validator 必須另外拒絕會在大小寫不敏感檔案系統衝突的宣告。

同一候選檔案命中多個 Owning Manifest 時，先選目錄距離最近者，再依 `project`、`package`、`workspace` 的順序選較具體 Boundary，最後依 Metadata 宣告順序決定。不同候選檔案若得到不同 Owner，就拆成不同 Changed Module，不得為了只套用一次 Profile 而合併。

### Catalog Contract

`profiles/catalog.yaml` 只保存 Catalog Schema Version 與有序的 Profile Metadata 相對路徑，不重複 ID、Status、Reference 或 Evidence：

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

各 Profile YAML 是自身狀態的唯一真實來源，並使用結構化 `ownership`、`deprecation` 與 `evidence`。JSON Schema 驗證單檔形狀；Python Validator 驗證 Catalog 順序與唯一性、跨檔引用、相依 Cycle、檔案路徑及成熟度／Evidence 關係。

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
| `detection` | Owning Manifest、Supporting Fact、Extension 與 Dependency 訊號 |
| `routing` | Changed Module 選擇策略與載入順序 |
| `composition` | Requires、Recommends 與 Conflicts |
| `ownership` | 至少一位負責維護 Metadata、Reference 與 Evidence 的 Maintainer |
| `evidence` | Benchmark 狀態與可稽核路徑 |
| `deprecation` | 僅 `deprecated` Profile 必須提供的結構化淘汰資訊 |

### Ownership、Deprecation 與 Evidence Contract

1. 所有 Profile（包含 `planned`）都必須有非空白的 `ownership.maintainers`；值使用可穩定辨識的 Repository Maintainer ID。
2. 只有 `deprecated` Profile 可以有 `deprecation`。`deprecation.reason` 必填；`replacement` 與 `removal_version` 選填，但若存在就必須可解析且符合對應格式。
3. `evidence.benchmark_status` 只能是 `not_started`、`pilot_recorded` 或 `full_run_recorded`。
4. 每筆 `evidence.results` 必須包含 `stage`、`outcome`、Repository 內相對 `path`、該檔案的 SHA-256 `sha256` 與布林值 `public`。
5. `outcome` 只能是 `passed`、`failed`、`no_difference` 或 `inconclusive`。失敗、無差異與無法判定的結果都必須保留，不能只登錄通過結果。
6. `beta` 必須至少有一筆有效、公開且通過的 Pilot Result；`stable` 必須至少有一筆有效、公開且通過的 Full Run Result。Metadata Validator 必須重新計算 Evidence 檔案雜湊，不能只相信欄位文字。

### Schema 規則

1. Schema 根節點與結構化子物件預設使用 `additionalProperties: false`，未定義欄位必須明確拒絕。
2. `id` 必須符合 `^[a-z][a-z0-9-]*$`。
3. 非 `planned` Profile 必須存在 `reference`，且該檔案可讀。
4. `planned` Profile 必須省略 `reference`，避免指向空白或不存在的文件。
5. `stable` 必須至少連結一份公開 Full Run Result。
6. `beta` 必須至少連結通過的 Pilot 或等價證據。
7. `experimental` 可以只有文件與 Contract Test，但 README 必須明確標示未完成效果驗證。
8. `deprecated` 必須提供 Replacement 或移除原因。
9. `requires`、`recommends`、`conflicts` 只能引用 Catalog 中存在的 ID。
10. Profile ID、Reference Path 與產物名稱必須在大小寫不敏感檔案系統上仍保持唯一。
11. Planned Profile 不得進入正式打包清單，也不得由 Routing 自動選取。
12. `ownership.maintainers` 必須存在且至少包含一個非空白 Maintainer ID。
13. 非 `deprecated` Profile 不得提供 `deprecation`；`deprecated` Profile 必須提供非空白 `deprecation.reason`。
14. `evidence.benchmark_status` 必須與登錄的 Result Stage 一致，不得在沒有對應 Result 時宣稱已完成 Pilot 或 Full Run。
15. Evidence Result 的 `path` 必須存在於 Repository 內，`sha256` 必須與檔案內容相符，`public` 必須明確為布林值。
16. Profile 成熟度升級必須符合 Evidence Contract；`failed`、`no_difference` 與 `inconclusive` 不得當成升級依據。
17. `owning_manifests` 每筆都必須有合法 `pattern` 與 `boundary`；`supporting_files` 不得被 Validator 或 Routing 提升為 Owner。
18. `dependency_markers` 與 `supporting_dependencies` 不得在同一 Profile 重複相同 Package Name。

## Profile Reference Contract

每份 Profile Markdown 必須使用相同章節，避免各語言文件退化成風格偏好清單：

```markdown
# <Profile Display Name> Profile

## Use This Profile When
## Repository Facts to Inspect
## Version-Sensitive Facts
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
- **Version-Sensitive Facts**：列出可驗證的版本來源、版本未知時的保守行為，以及只適用於特定版本的判斷。
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
7. Profile Reference 延續既有 Core Reference，使用英文；SPEC、根目錄 `CONTEXT.md` 與 README 主體使用台灣繁體中文，並保留正式英文術語。
8. `Version-Sensitive Facts` 不得把目前最新版當成隱含基準；版本無法確認時必須記錄 Unknown，而不是把不確定規則寫成強制要求。

## Profile Selection Contract

### 選擇原則

Profile Selection 必須以本次任務的 Changed Module 為中心，不得只掃描 Repository Root。

```text
1. 讀取 User Prompt 與 Repository Instruction
2. 依目前工作階段確認 Expected Diff、Actual Diff 或兩者
3. 為每個候選檔案尋找最近的 Owning Manifest，並依 Manifest 所在目錄分組
4. 以檔案副檔名確認主要語言候選
5. 以 Dependency Marker 確認 Framework 候選
6. 移除 Planned、Deprecated 或不相容候選
7. 套用零到多個 Language／Framework Profile
8. 依 load_order 載入已選 Profile
9. 保留 Core、Repository Policy 與既有 Gate
10. 回報實際套用 Profile 與無法確定的訊號
```

Metadata Validator／Routing Fixture 負責驗證預期選擇；實際 Agent 執行仍必須讀取 Repository Facts。Script 的靜態推導不能取代 Agent 對 Expected Diff、Ownership 與行為邊界的判斷。

### Changed Module Boundary

1. 每個候選 Changed File 從自身目錄向 Repository Root 尋找最近的 Owning Manifest。
2. 共享同一個最近 Owning Manifest 的檔案屬於同一 Changed Module；不同 Manifest 目錄分開處理。
3. 找不到 Owning Manifest 時，先查 Repository Policy，再把 Root Manifest 當作補充訊號。
4. Generated、Vendor 與 Build Output 預設不參與偵測，除非它們本身是明確 Expected Diff。
5. Manifest、設定檔或新檔案本身是 Expected Diff 時，以該 Manifest 的目錄作為 Changed Module，並用鄰近原始碼與 Repository Policy補足語言事實。

### Detection Semantics

1. Language Profile 以 Changed File Extension 為主要訊號；Owning Manifest 用於設定檔型 Diff 與候選確認。
2. Framework Profile 必須由 Owning Manifest 的 Dependency Marker 或 Repository Policy 證明；`.jsx`、`.tsx` 或其他語法外觀只能作輔助訊號。
3. `package.json` 的 `dependencies`、`devDependencies`、`peerDependencies` 與 `optionalDependencies` 都可提供 Dependency Marker。
4. Lockfile 只能補強已存在的 Manifest／Policy 事實，不能單獨決定 Framework。
5. Repository Root 訊號不得覆蓋 Changed File Extension、最近 Owning Manifest 或更具體的 Repository Policy。

Metadata 必須透過 `owning_manifests`、`supporting_files`、`dependency_markers` 與 `supporting_dependencies` 保存 Owning／Supporting 差異；Runtime Profile Index 必須呈現這些角色，不能把所有命中檔案或套件當成同等 Module Owner／Candidate Marker。

### Technology-Specific Detection Contract

| Profile | 主要語言／Framework 訊號 | Owning Manifest | Supporting Facts | v0.5.0 行為 |
| --- | --- | --- | --- | --- |
| C# | `.cs` | 最近的 `.csproj` | `.sln`、`.slnx`、`Directory.Build.props`、`Directory.Build.targets`、`global.json` | 可選取 `csharp` |
| Python | `.py`、`.pyi` | 依距離選擇 `pyproject.toml`、`setup.py` 或 `setup.cfg` | `requirements*.txt`、`Pipfile`、`poetry.lock`、`uv.lock`；`.ipynb` 不自動分析 | 可選取 `python` |
| TypeScript | `.ts`、`.tsx`、`.mts`、`.cts` | 最近的 `package.json`；最近的 `tsconfig.json` 或 `tsconfig.*.json` 界定 TypeScript Project／Config-only Diff | `.js`、`.jsx` 不構成 TypeScript 訊號 | 可選取 `typescript` |
| React | `react` Dependency Marker 加上 Changed File、Import、Repository Policy 或 Manifest Diff 的相關性 | 提供 Dependency Marker 的最近 `package.json` | `react-dom`、`react-native` 只辨識 Renderer；`.jsx`、`.tsx` 只作輔助 | 可選取 `react` |
| Go | `.go` | 最近的 `go.mod` | `go.work` 只作 Workspace 補充 | 只回報 Planned／Unavailable |
| Rust | `.rs` | 最近的 `Cargo.toml` | `Cargo.lock` 只作補充 | 只回報 Planned／Unavailable |
| Java | `.java` | 最近的 `pom.xml`、`build.gradle` 或 `build.gradle.kts` | `settings.gradle`、`settings.gradle.kts` 只作 Root 補充 | 只回報 Planned／Unavailable |
| Vue | `vue` Dependency Marker 與 `.vue` | 提供 Dependency Marker 的最近 `package.json` | JavaScript／TypeScript 訊號另由對應 Language Profile 判斷 | 只回報 Planned／Unavailable |

補充規則：

1. C# 找不到 `.csproj` 時，`.sln`／`.slnx` 只能協助定位 Solution 範圍，不得覆蓋更接近的其他技術棧 Owning Manifest。
2. Python Lockfile 與 Requirements File 不單獨界定 Changed Module。
3. TypeScript 的 `package.json` 界定 Package；`tsconfig*` 界定該 Package 內的 TypeScript Project。兩者同時存在時，以候選檔案最近且最具體的 Project Boundary 分組，但 Dependency Marker 仍從對應 Package 取得。
4. `react` 是 React Framework Candidate 的必要且足夠 Dependency Marker；`react-dom` 或 `react-native` 單獨存在都不能啟用 React Profile。
5. React Candidate 還必須與本次 Changed Module 的行為相關。只修改同 Package 內非 React 工具程式時，只套用適用的 Language Profile。
6. React Profile 涵蓋 Renderer-neutral 的 Component、Hook、State、Effect 與 Lifecycle；DOM 規則只在 `react-dom` 證據存在時套用。React Native 平台 API 不屬於 `v0.5.0` Reference 範圍。
7. Planned Profile 命中上述訊號時只記錄 Planned／Unavailable，不讀取 Reference、不參與 Composition，也不成為 Packaging Target。

### Version-Sensitive Facts

Profile 不設定一組脫離 Repository 的通用最低版本。每次套用時，必須盡可能從 TFM、Language Version、Runtime Version、Compiler Config 與 Dependency Version 判斷適用語意；Reference 對版本差異使用條件式表述。版本無法確認時記錄為 Unknown，不假設最新版本，也不把不確定規則當成強制要求。

### Stage-Specific Diff Evidence

- Planning 使用 Expected Diff。
- Implementation 同時追蹤 Expected Diff 與 Actual Diff，並回報偏離。
- Review 以 Actual Diff 為主要選擇依據，再與 Expected Diff 比對範圍。
- Expected Diff 尚未完全確定時，可以提出最可能模組並標示 Assumption；若不同答案會改變公開行為、資料、資源或副作用，必須列為 Critical Unknown。

### 選擇優先順序

1. User 對本次任務的明確 Profile 或 Core Only 指示。
2. Repository Policy 對特定目錄或模組的明確規定。
3. Expected Diff 中的檔案類型與最近 Manifest。
4. 該模組 Manifest 中的 Framework Dependency。
5. Repository Root 訊號，只能作為補充，不能覆蓋更接近 Changed Module 的事實。
6. 無充分訊號時使用 Core Only。

`v0.5.0` 不新增必要的 Consumer Profile 設定檔。使用者可用自然語言或 Repository Instruction 明確指定可用 Profile 或 Core Only，但不要求額外 Parser，也不新增另一組穩定 YAML 指令契約。明確指定可以優先於自動偵測，仍不得啟用 Planned、Deprecated、缺少 Reference、相依未滿足、衝突或與 Changed Module 明顯不適用的 Profile；此時應回報無法套用的理由並依風險決定 Core Only 或停止。

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

### Composition Semantics

1. `requires` 依傳遞關係展開；任何必要 Profile 缺少、不可用或不適用時，該 Profile 組合無效。
2. `recommends` 只提供組合提示，不會單憑 Metadata 自動套用；被建議的 Profile 仍須有獨立 Repository Facts。
3. `conflicts` 必須由雙方 Metadata 對稱宣告；命中時不得自行選擇其中一方。
4. Self-reference、`requires` Cycle 與不對稱 Conflict 都是 Metadata 驗證錯誤。
5. `load_order` 相同時，依 `kind` 再依 `id` 排序，確保結果穩定。
6. Conflict 只阻止有衝突的 Profile 組合；非關鍵情境可回到 Core Only 並回報原因。若不同 Profile 會改變公開行為、資料、資源或副作用，必須停止並取得人類決策。

## Profile 套用後的輸出

Profile 不新增另一套完整輸出格式。

- **Lightweight**：只有 Profile 確實改變選擇或驗證時，才在簡短回報中說明。
- **Standard**：固定在 `Decision Basis` 內依 Changed Module 列出 `Profiles Applied` 與 `Profile Basis`；Core Only 明確記錄 `Profiles Applied: none`。
- **Full Audit**：Profile Reference 放入 `Applicable References`，選擇證據放入 `Repository Facts Used`，無法確定的訊號放入 `Unknowns`；Core Only 明確記錄 `Profiles Applied: none`。

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
5. 純文字修正，或讓實作重新符合既有 Detection／Routing 契約且不改變選取結果的 Bug Fix，屬於 Patch Release。
6. 新增向後相容 Detection 訊號，或使既有 Repository Facts 產生新的相容 Profile Selection 結果，屬於 Minor Release。
7. 破壞既有 Profile ID、Schema、Composition、選擇優先權、公開輸出契約，或移除既有 Profile，屬於 Major Release。
8. Benchmark Version、Fixture Version 與 Profile Schema Version 分開管理，不能以 Skill Version 取代。

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

`scripts/build_skill_package.py` 接受可重複的 `--profile <id>`。每個明確選取的 Profile 都必須遞迴納入其 `requires`，但不會因 `recommends` 自動增加 Profile。只指定 `react` 是有效請求；要產生 TypeScript React Package，呼叫端必須同時指定 `--profile typescript --profile react`。

每個 Specialist Package 只包含：

1. 由 Packager 產生、名稱與選擇結果一致的 `SKILL.md` 與必要 OpenAI Adapter。
2. 所有必要 Core References。
3. 只描述此 Package 所含 Profile 的 Runtime Profile Index。
4. 明確選取的 Profile、它們傳遞式 `requires`，以及對應 Profile References。
5. Repository 的 `LICENSE`。
6. 可機器驗證的 `PACKAGE-MANIFEST.json`。

已被 Bundled 不代表每個任務都會套用該 Profile。Specialist Package 仍必須依 Changed Module 判斷適用性；若 Bundled Profile 對目前任務不適用，就以 Core Only 執行並回報理由，不得為了符合 Package 名稱而強制套用。

長期可以產生：

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

### Reproducible Package Manifest

Release Mode 只能在乾淨 Worktree 執行，所有輸入都從目前 `HEAD` 的 Git Blob Bytes 讀取；不得混入未 Commit 檔案、Checkout EOL 或平台特有內容。Development／Test Mode 必須明確接收 Source Root，使用目前 Worktree Bytes，並在 Manifest 記錄 `source_mode: worktree`，不得冒充 Release Artifact。

`PACKAGE-MANIFEST.json` 同時記錄來源與實際產物，至少包含：

- Manifest Schema Version。
- `source_commit` 與 `source_mode`。
- Suite Version 與 Packager Version。
- 依穩定規則排序的 Profile ID。
- 排序後的 `inputs`，每筆包含 Repository 相對路徑與 SHA-256。
- 排序後的 `files`，每筆包含 Package 相對路徑與 SHA-256。
- Package Overall Digest；計算時排除 Manifest 自身的 Overall Digest 欄位。

Manifest 與產物不得包含 Timestamp、Absolute Path、OS 名稱或其他會讓相同輸入產生不同 Bytes 的環境資訊。Canonical JSON 使用 UTF-8、LF、遞迴排序 Object Key、固定 Array 順序與無多餘空白的 Serialization。Overall Digest 是移除 `overall_digest` 欄位後之 Canonical Manifest JSON 的 SHA-256；`files` 不列入 `PACKAGE-MANIFEST.json` 自身，避免自我雜湊循環。Ubuntu 與 Windows 必須對同一個 Canonical Fixture 產生相同 Digest。

`scripts/package-manifest.schema.json` 使用 JSON Schema Draft 2020-12 與 `additionalProperties: false` 驗證這份產物。它的 Schema Version 與 `profiles/profile.schema.json`、Suite SemVer 分開管理，避免 Packaging Contract 與 Profile Metadata 綁死。

`v0.5.0` 只在 Git ignored 的 `dist/clean-code-ai-csharp/` 產生一個 C# Sample Package 並執行 Contract Test；不建立 ZIP、不 Commit `dist/`，也不公開發布。正式發布任何 Specialist Package 必須等待其中所有 Profile 至少達到 `beta`，並另行取得 Release 授權。

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

## 非功能需求與工具安全

### Context Budget

1. 不設定會掩蓋任務差異的任意全域 Token 上限；Routing 以 Changed Module 為單位，只載入實際相關的 Profile Reference。
2. 每份 Profile Reference 目標上限約為 1,500 個英文單字；超過時必須先消除重複 Core 說明，或提出具體理由接受 Review。
3. Core `SKILL.md` 必須持續符合既有 525-word Contract，不得用提高上限掩蓋 Routing 膨脹。

### Portability 與 CI Matrix

Profile Contract、Routing、Generated Region 與 Packaging Tests 必須同時在 Ubuntu 與 Windows 執行，並對相同 Canonical Fixture 驗證相同 Package Digest。Core Skill 的 `agentskills validate` 至少在 Ubuntu 執行；若 Windows Runner 可取得相同 CLI，也一併驗證，但不得因工具不可取得而改寫 Contract。

### Tool Mutation Boundary

1. `validate_profiles.py` 是 Read-only，不得修改任何檔案。
2. `generate_profile_matrix.py` 只能改寫 README 與 `profile-selection.md` 中各自唯一、明確標記的 Generated Region；Marker 缺失、重複或順序錯誤時必須停止，不能重寫整份文件。
3. `build_skill_package.py` 只能寫入呼叫端明確指定、執行開始時尚不存在的 Output Directory；已存在時必須 Fail Closed，不能覆寫或清空。
4. Packaging 失敗時，只能逐一刪除本次執行實際建立且有明確路徑的檔案，再由最深層開始非遞迴移除已空目錄；不得使用 Recursive Delete、Glob Delete 或清理執行前已存在的內容。
5. 這些工具不得存取網路、安裝依賴、Commit、Tag、Push、建立 Release，或修改 Consumer Repository。

### Script API 與 CLI Contract

三個 Script 的核心邏輯必須是可 Import、可用暫存 Fixture 測試且不直接結束 Process 的 Python Function；CLI 只負責參數解析、呼叫核心邏輯與呈現已排序的 Diagnostic。固定 CLI 為：

```text
python scripts/validate_profiles.py --source-root <path>
python scripts/generate_profile_matrix.py --source-root <path> [--check]
python scripts/build_skill_package.py --source-root <path> --output <new-path> --source-mode <release|worktree> --profile <id> [--profile <id> ...]
```

所有 Diagnostic 依 Repository 相對檔案路徑、欄位路徑與錯誤代碼穩定排序，不輸出 Traceback 作為一般 Contract Failure 介面。Exit Code 固定為：

- `0`：成功，或 `--check` 確認無漂移。
- `1`：Schema、Contract、Validation、Generated Drift 或 Packaging 前置條件失敗。
- `2`：缺少參數、非法選項或其他 CLI Usage Error。

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

每個案例放在 `tests/fixtures/profile-routing/<case>/`，只保存最小 Manifest、代表性 Source Stub 與 `expected.json`。Fixture 不安裝套件、不連網、不 Build，也不複製完整範例應用程式。

`expected.json` 至少包含 `changed_files`、選填的 `explicit_profiles`、整體 `outcome`、各 Changed Module 的 `root`／`profiles`／`unavailable_profiles`、穩定的 `reason_codes` 與預期 `unknowns`。`outcome` 只能是 `selected`、`core_only` 或 `blocked`。測試不得比對完整人類敘述，避免純文案修正破壞 Routing Contract。

使用這些小型 Fixture 驗證：

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

跨平台 Canonical Fixture 獨立放在 `tests/fixtures/profile-packaging/csharp/`，不得與 Routing Fixture 共用預期結果或讓兩種測試責任互相依賴。

- Release Mode 從同一 Source Commit 產生逐 Byte 相同的檔案、輸入雜湊與 Overall Digest。
- Windows 與 Ubuntu 對同一 Canonical Fixture 產生相同 Overall Digest。
- Development／Test Mode 明確標記 `source_mode: worktree`，不得宣稱為 Release Artifact。
- Specialist Package 只包含 Core、明確選定 Profile 與其傳遞式 `requires` 所需檔案，不自動納入 `recommends`。
- `react` 單獨打包有效；TypeScript React 必須明確同時選取 `typescript` 與 `react`。
- Bundled Profile 對 Changed Module 不適用時回到 Core Only，不會強制套用。
- Generated `SKILL.md` Frontmatter 名稱與 Metadata 一致。
- Generated Package 可通過 `agentskills validate`。
- `PACKAGE-MANIFEST.json` 通過獨立 Schema，不含 Timestamp、Absolute Path 或 OS，並可重新計算每個 Input Hash、Package File Hash 與 Overall Digest。
- 已存在的 Output Directory 必須 Fail Closed；失敗清理不得刪除執行前內容或使用 Recursive Delete。
- `dist/` 是 Git ignored 的 Generated Output，乾淨 Checkout 可重新產生。
- Planned Profile 無法作為 Packaging Target。

### Existing Regression Tests

既有 `test_skill_contract.py`、Benchmark Harness Test、Strategy Full Run Verification 與 Open Standard Validation 必須繼續通過。若需要重構固定的 `REFERENCE_NAMES`，測試應改成「Core Reference + Catalog 中可用的 Profile Reference」契約，不得單純刪除完整性檢查。

在新增 Profile 前，必須先修復 v0.4.0 Strategy Full Run Verification：歷史 Result 應依其 Receipt 所指向的固定 Revision 讀取 Git Blob Bytes，不得以目前 `SKILL_SOURCE`、目前 Worktree Bytes 或平台 EOL 作比較基準。這項修復不得改寫既有公開 Result、Manifest 或 Receipt。

### CI 建議流程

Profile Contract、Routing、Generated Region 與 Packaging 步驟在 Ubuntu 與 Windows Matrix 執行；兩個平台使用同一份 Canonical Fixture Digest Assertion。`agentskills validate` 至少在 Ubuntu 執行，Windows 有相同 CLI 時再加入同一 Gate。

```text
1. Install validation dependencies
2. Run repository unit tests
3. Validate profile schema and catalog
4. Check generated Runtime Profile Index and README Profile Matrix
5. Validate profile reference contract
6. Run routing fixtures
7. Build deterministic sample package
8. Validate Core Skill open standard
9. Validate the Skill inside the generated sample Specialist Package
10. Compile benchmark harness
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

本主題只維護以下權威文件：

1. 本 SPEC 是完整架構與驗收規則的唯一來源，所有設計確認直接更新本檔。
2. 根目錄 `CONTEXT.md` 只保存穩定術語，不保存實作細節。
3. 架構確認後只建立 `docs/adr/0001-core-plus-composable-profiles.md`，記錄 Monorepo、單一 Core 與 Composable Profiles 的決策與取捨，並連回本 SPEC。
4. SPEC 經使用者核准後只建立 `docs/superpowers/plans/2026-09-04-composable-language-framework-profile-architecture.md`；不另建 Summary、Decision Log、Roadmap 或 Handoff 文件。

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

矩陣與 `profile-selection.md` 的 Runtime Profile Index 必須由 `scripts/generate_profile_matrix.py` 從 Catalog／Metadata 產生為分別使用 `profile-matrix:generated` 與 `runtime-profile-index:generated` Marker 的 Checked-in 區塊；CI 使用 Read-only `--check` 模式拒絕漂移，人工不得直接修改產生區塊。

## 貢獻者契約

只有 `planned` Metadata 可以先獨立提交。從 `planned` 升為 `experimental` 的同一筆變更必須原子地提供：

1. Profile Metadata。
2. 符合固定章節的 Profile Reference。
3. Detection 與 Routing Fixture。
4. Contract Test。
5. Runtime Profile Index 與 README Matrix 的可重現 Generated Region 更新。
6. Evidence Status 與未完成項目，不得空白省略。
7. 原創內容或清楚授權與 Attribution。
8. 不重複 Core 規則的自我檢查。

只新增 Planned Profile 時，可以只有 Metadata 與 Catalog 更新，但必須省略 `reference`，且不得啟用 Routing／Packaging。不得提交空白 Reference、TODO／TBD 占位、缺少測試的可用狀態，或先宣稱 `experimental` 再於後續變更補齊契約。

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

### Preflight：v0.4.0 Historical Verification Integrity

範圍：

- 讓 v0.4.0 Strategy Full Run Verification 從 Receipt 指定的歷史 Revision 取得 Git Blob Bytes。
- 排除目前 Worktree、CRLF／LF 與後續 Profile Reference 對歷史驗證結果的影響。
- 保留既有 Result、Manifest 與 Receipt。

完成條件：

- 相同歷史 Revision 在不同 Checkout EOL 下得到相同驗證結果。
- v0.4.0 公開 Receipt 可重播，且不依賴目前 Skill Tree。
- 全部既有 Regression Tests 回到綠燈後，才開始 M0-A。

### M0-A：Profile Structural Contract

範圍：

- 新增 `profile.schema.json` 與 `catalog.yaml`。
- 加入八個 `planned` Profile Metadata。
- 新增 Profile Contract Tests。
- 不修改 Core Routing 行為。

完成條件：

- Schema、Catalog、ID、Status 與 Composition 驗證全數通過。
- Planned Profile 不可被 Routing 或 Packaging 使用。
- Planned Profile 不建立空白 Reference。

### M0-B：Profile Selection 與 Core Routing

範圍：

- 新增 `references/profile-selection.md`。
- 在 `SKILL.md` 加入最小 Routing 入口。
- 以 `tests/fixtures/profile-routing/<case>/` 的測試專用 Catalog、最小 Manifest、Source Stub 與 `expected.json` 新增 Changed Module 與 Polyglot Routing Contract Tests。
- 更新 Output Contract 的 Profile 回報規則。

完成條件：

- 既有 Prompt 不需修改。
- 無 Profile 時維持 Core 行為。
- 測試專用 Fixture 中的 TypeScript React 能選出兩層 Profile。
- 真實 Catalog 中的八個 Planned Profile 都不會被載入或打包。
- Entry Point 篇幅與所有既有測試通過。

### M1-A：C# Profile

範圍：

- 完成 `language-csharp.md`。
- 增加 C# Routing 與 Semantic Contract Tests，並在同一步把 C# Metadata 標示為 `experimental`。

完成條件：

- 不包含 ASP.NET Core 專屬規則。
- Reference 明確涵蓋 Nullability、Cancellation、Resource、LINQ、Equality，以及 Repository 已使用 DI 時的 Lifetime 風險。

### M1-B：Python Profile

範圍：

- 完成 `language-python.md`。
- 增加 Python Routing 與 Semantic Contract Tests，並在同一步把 Python Metadata 標示為 `experimental`。

完成條件：

- 不把 FastAPI 或 Django 當成 Python 通則。
- Reference 明確涵蓋 Dynamic Typing、Mutable State、Async、Cleanup 與 Exception Boundary。

### M1-C：TypeScript 與 React Profiles

範圍：

- 完成 `language-typescript.md` 與 `framework-react.md`。
- 驗證 TypeScript React 與 JavaScript React 的不同組合，並在同一步把 TypeScript 與 React Metadata 標示為 `experimental`。

完成條件：

- TypeScript 規則與 React Lifecycle 規則分離。
- 固定 Routing Fixture 證明 JavaScript React 不會選取 TypeScript Profile。
- React Profile 只涵蓋 Renderer-neutral 語意與有 `react-dom` 證據的條件式 DOM 規則，不把 React Native 平台 API 納入 `v0.5.0`。
- 識別既有 Pinned React Benchmark Fixture，僅作後續 M2 Profile Pilot 的候選基礎，不宣稱已驗證 Profile 效果。

### M1-D：README、Authoring Guide 與 Sample Packaging

範圍：

- 新增 Profile Matrix 與使用說明。
- 新增 Profile Authoring Guide。
- 在 Git ignored 的 `dist/clean-code-ai-csharp/` 完成唯一的可重現 C# Specialist Package 範例。

完成條件：

- README 狀態與 Catalog 一致。
- Generated Package 通過 Open Standard Validation。
- Ubuntu 與 Windows 對 `tests/fixtures/profile-packaging/csharp/` 產生相同 Package Digest。
- Sample Package 不建立 ZIP、不 Commit，也不公開發布。
- 不公開發布未達 Beta 的 Specialist Package。

### `v0.5.0` Release Boundary

Preflight、M0-A、M0-B、M1-A、M1-B、M1-C 與 M1-D 是 `v0.5.0` 的實作與驗收範圍。完成後先進行規格對照、測試與 Release Review；不要在同一個未重新核准的計畫中自動接續 M2 或 M3。

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
3. 產生獨立 Implementation Plan，將 Preflight 至 M1-D 拆成可驗證的小步驟；每個 Task 明列檔案、先寫的失敗測試、最小實作、驗證命令、完成條件與 Commit Boundary。
4. 保留現有 Tests 與公開 Result，不以重寫歷史證據來讓新 Contract 通過。
5. Implementation Plan 必須先交由使用者核准；核准前不得建立開發 Worktree 或修改實作檔案。
6. 計畫核准後，從包含核准設計與計畫的本機 `main` 建立 `codex/v0.5.0-composable-profiles` Branch，以及位於 Repository 同層、目錄名稱為 `Clean-Code-AI-Collaboration-Skill-v0.5.0` 的隔離 Worktree；公共文件不得保存使用者的絕對路徑。
7. 開發採 TDD，依 Preflight、M0-A、M0-B、M1-A、M1-B、M1-C、M1-D 順序小步實作；每個里程碑通過指定 Gate 後建立一個可獨立回復的本機 Commit。
8. 計畫核准後，允許在隔離 Worktree 的本機虛擬環境安裝 `requirements-dev.txt` 精確 Pin 的開發相依；不得寫入 System Python、由 Repository Script 自動安裝或 Commit `.venv`。
9. Preflight 必須先讓完整 Regression 回到綠燈；不得先開發 Profile、降低 Assertion 或改寫既有 Result／Manifest／Receipt。
10. 對 Push、PR、Merge、Tag、GitHub Release、公開 Specialist Package、外部 Repository、正式 Benchmark Run、M2 或 M3 保留新的 Authorization Gate。
11. 在未取得下一階段核准前停止於 `v0.5.0` Release Boundary。

### Validation 與交付狀態

`v0.5.0` 完成宣稱必須依序提供 Targeted Tests、Windows 完整 Repository Tests、Benchmark Harness Compile、Core 與 Sample Package Open Standard Validation、Generated Region `--check`、Canonical Package 跨平台 CI、SPEC Compliance Review 與 Code Review 證據。本機通過不等於 CI 通過；CI 通過也不等於已 Push、Merge、Tag 或發布。

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
15. 所有 Profile 都有明確 Maintainer；Beta／Stable 宣稱可由公開且通過的 Evidence Result 驗證，其他 Outcome 仍完整保留。
16. Ubuntu 與 Windows 對 Canonical Packaging Fixture 產生相同 Digest，產物不包含 Timestamp、Absolute Path 或 OS 差異。
17. v0.5.0 只產生 Git ignored 的 `dist/clean-code-ai-csharp/`，不建立 ZIP、不 Commit，也不公開發布。
18. Validator、Generator 與 Packager 符合各自 Mutation Boundary，錯誤路徑不使用 Recursive Delete 或覆寫既有 Output Directory。
19. C#、Python、TypeScript、React 與四個 Planned Profile 都遵守 Technology-Specific Detection Contract；Supporting File 不會被誤當成同等 Owning Manifest。
20. Profile 對版本敏感規則讀取 Repository Facts；版本未知時明確記錄 Unknown，不假設最新版。
21. Routing 與 Packaging Fixture 分離，且都不需安裝依賴或 Build 完整範例應用程式。
22. Detection Metadata 結構化區分 Owning／Supporting File 與 Candidate／Supporting Dependency，Routing 不依 Profile ID 寫死例外。
23. 多重 Owning Manifest 依距離、Boundary Specificity 與 Metadata 順序產生穩定結果。
24. 三個 Script 提供可 Import 的核心邏輯、固定 CLI、穩定 Diagnostic 排序與 `0`／`1`／`2` Exit Code。
25. Generated Region 使用唯一固定 Marker；`--check` Read-only，異常 Marker Fail Closed。
26. Routing `expected.json` 使用穩定 Outcome 與 Reason Code，不比對完整人類文案。
27. `PACKAGE-MANIFEST.json` 同時驗證 Input 與 Package File，通過獨立 Schema，並依 Canonical JSON 計算 Overall Digest。
28. Planned Metadata 可獨立提交；升級 Experimental 必須原子包含 Metadata、完整 Reference、Tests 與 Generated Docs。
29. Implementation Plan 經使用者核准後才建立隔離 Worktree 並開始開發。
30. 開發依 Preflight 至 M1-D 採 TDD 與里程碑本機 Commit；不自動 Push、PR、Merge、Tag 或發布。
31. 完成報告明確區分本機 Gates、跨平台 CI、Review 與 Release 狀態。

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

緩解：`SKILL.md` 只路由，不內嵌 Profile；每個 Changed Module 只讀相關 Reference；Profile Reference 目標不超過約 1,500 個英文單字，Core Entry Point 持續遵守 525-word Contract。

### 風險：Profile 存在但沒有證據

緩解：成熟度模型與 Evidence 欄位強制分離；已實作 Profile 從 Experimental 開始；README 顯示真實狀態。

### 風險：Benchmark 錯誤歸因

緩解：Language 與 Framework 使用階梯式 Treatment Arm；公開 Result 明確標示評估的是單一 Profile 或 Profile Pack。

### 風險：Generated Specialist Package 漂移

緩解：`dist/` 必須 Git ignored；Release Mode 從 HEAD Git Blob Bytes 生成；Manifest 排除非決定性資訊；Ubuntu／Windows 對同一 Fixture 驗證相同 Digest。

### 風險：生成工具覆寫或誤刪使用者檔案

緩解：Validator Read-only；Generator 只改固定 Marker；Packager 只接受不存在的明確 Output Directory；失敗時逐檔清理本次建立內容，禁止 Recursive Delete。

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

`v0.5.0` 完成 Profile Contract、Routing、C#、Python、TypeScript 與 React，並只為 Go、Rust、Java、Vue 建立 Planned Metadata。獨立 Specialist Package 只作自動生成的 Distribution Artifact，不作新的手動維護來源。

Profile Pilot、正式結果與剩餘 Profile 屬於下一階段。這個設計的核心不是增加更多規則，而是讓共用判斷維持一致、讓語言差異只在需要時被載入，並讓每個「支援」主張都能對應到清楚的 Repository Facts、驗證與 Evidence Boundary。
