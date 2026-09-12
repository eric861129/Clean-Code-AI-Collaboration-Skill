# Clean Code AI Collaboration Skill

`clean-code-ai-collaboration` 是一套開源 Agent Skill。它把 Clean Code 的程式碼、設計、架構與軟體工藝觀念，整理成 AI Coding 可以重複使用的判斷流程。

這個 Skill 不會替 Repository 發明規則，也不會把某次實驗勝出的方案當成所有專案的標準答案。它要求 Agent 先讀懂專案情境，再交代選項、取捨、行為邊界、驗證方式，以及什麼情況應該改採其他做法。

## 三十秒快速開始

1. 依照[安裝說明](#安裝)，把 `clean-code-ai-collaboration` 資料夾放進 Project 或個人的 `.agents/skills`。
2. 在任務 Prompt 明確寫出 `$clean-code-ai-collaboration`。
3. 不確定要用哪一種開發方式時，先保留 `auto`；已有明確需求時，再指定 TDD、TCR 或其他節奏。
4. 檢查 Agent 是否回報實際採用的節奏、驗證範圍、執行結果與未涵蓋風險。

可以先從這個 Prompt 開始：

```text
請使用 $clean-code-ai-collaboration 實作這個需求。
development_rhythm: auto
validation_profile: auto

先讀取 Repository 規則與既有測試，再決定適合的開發節奏與驗證範圍。
保留必要 Gate，完成後回報實際驗證結果與仍未涵蓋的風險。
```

如果沒有填寫兩個設定，Skill 也會使用 `auto`。一般使用者不必先理解所有模式才能開始。

## 這個 Skill 解決什麼問題

只對 Agent 說「請遵守 Clean Code」，通常不夠具體。Agent 可能把函式拆得很短，卻增加大量跳轉；也可能建立漂亮的分層，卻順手改掉 API Contract、資料語意或副作用順序。

這個 Skill 把模糊的品質期待轉成一套工作流程：

- 分清楚 Repository 事實、推測與未知資訊。
- 依風險選擇輕量或完整流程，不把所有任務都做成大型重構。
- 比較可行方案，說明當下選擇與其他方案適用的情境。
- 先守住行為、資料、副作用與依賴邊界，再比較 Token 或工具呼叫成本。
- 留下實際執行的測試、工具輸出、盲點與人工決策。

它要改善的不是 Agent「會不會生成程式碼」，而是 User 能不能掌握 Agent 為什麼這樣改、改了什麼，以及我們憑什麼相信結果。

## Clean Code 如何改善 AI Coding

Clean Code 原本是為了讓人更容易閱讀、理解與維護程式碼。到了 AI Coding 時代，這些價值沒有消失，因為 Agent 同樣需要讀取名稱、責任、依賴、測試與領域語言，才能判斷修改位置與影響範圍。

當程式碼能清楚表達意圖時，Agent 較容易：

- 找到真正負責該行為的程式碼，而不是在多個相似位置碰運氣。
- 從名稱、型別與邊界理解規則，少靠推測補完需求。
- 把 Diff 控制在必要範圍，降低連帶修改與行為漂移。
- 透過可讀的測試確認系統答案，而不是只相信「Build 成功」。
- 在下一輪修改時重新取得情境，不必每次都從混亂的實作反推意圖。

這不代表 Clean Code 會讓模型突然變聰明，也不保證每次都能節省 Token。它真正提供的是較清楚的理解線索、修改邊界與驗證入口；是否省下成本，仍取決於專案規模、任務類型、模型與工具環境。

## CLEAN 五原則

CLEAN 是本專案從 Clean Code 精神與 AI Coding 實務歸納出的協作原則。它規範 User 如何駕馭 Agent，而不是把五個字母當成 Agent 自己作答的考卷。

| 原則 | 中文名稱 | 在 AI Coding 中負責什麼 |
| --- | --- | --- |
| C — Context-Aware Code | 情境感知 | 先掌握真實需求、Repository 規則、領域語言與既有行為，不用「一般都這樣做」補完空白。 |
| L — Localized Change | 局部變更 | 限制修改範圍、Diff 與副作用，讓每一行變更都能對應這次任務。 |
| E — Explicit Intent and Boundaries | 意圖明確 | 說清楚名稱、型別、角色、邊界、停止條件與授權範圍。 |
| A — Auditable by Evidence | 實據可審 | 保留 Prompt、Diff、測試、工具輸出、盲點與人工判斷，不把 Agent 自述當成證據。 |
| N — Non-Surprising Behavior | 符合預期 | 守住 API、資料、錯誤、副作用與失敗路徑，避免品質整理偷偷換掉系統答案。 |

## Skill、Repository Policy 與自動化 Gate 的分工

三者都能約束 Agent，但責任不同：

| 機制 | 適合放什麼 | 不適合取代什麼 |
| --- | --- | --- |
| Skill | 跨專案可重複使用的判斷流程、提問方式、Review 視角與輸出契約 | 不能猜出某個 Repository 的特有規則 |
| Repository Policy | 團隊已確認且相對穩定的命名、架構、測試與授權規範 | 不能取代需要權衡情境的工程判斷 |
| 自動化 Gate | Formatter、Lint、Build、Test、架構規則與其他可機器判定的門檻 | 不能證明未被測試涵蓋的需求一定正確 |

實務上可以讓 Skill 指引 Agent 如何判斷，把專案特有規則留在 `AGENTS.md` 或其他 Repository Instruction，再由自動化 Gate 執行不能靠提醒帶過的檢查。

Skill 會先盤點 Repository 既有的 Formatter、Linter、Static Analysis、Build、Test、Dependency／Security Scan 與其他 Gate，再選擇真正能觀察這次風險的工具。它不會因為某項工具流行就自行安裝，也不會把全綠結果擴張成 Oracle 未涵蓋的保證。

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

## 自己選擇開發節奏與驗證範圍

`v0.4.0` 把「怎麼開發」與「驗證到多深」拆成兩個設定。TDD、TCR 屬於開發節奏；E2E、Mutation Testing 屬於驗證方式。兩者可以自由搭配，例如使用 TDD 開發，再用 E2E 驗證跨邊界的使用者結果。

```yaml
development_rhythm: auto
validation_profile: auto
```

這兩個欄位是 Skill 使用的**指令契約**，目前沒有額外的 `config.yml` 需要建立。請依使用範圍放在下列位置：

| 使用範圍 | 設定位置 | 適合情境 |
| --- | --- | --- |
| 只套用一次任務 | 當次 User Prompt | 這次要使用 TDD、TCR，或需要不同的驗證深度 |
| 作為整個 Repository 的預設值 | Repository 根目錄的 `AGENTS.md` | 團隊希望後續任務採用一致的預設節奏與驗證範圍 |
| 只套用特定子目錄 | 該子目錄內的 `AGENTS.md`，並從該目錄啟動 Codex 或將它設為目前工作目錄 | 前端、後端或 Legacy 模組需要不同策略 |
| 其他 Agent Client | 該 Client 支援的 Repository Instruction | 檔名與載入規則須以 Client 官方文件為準 |

請勿直接修改安裝後的 `clean-code-ai-collaboration/SKILL.md` 來設定單一專案。這會改變 Skill 本身，後續更新也可能覆蓋你的設定。

### 單次任務：直接寫在 Prompt

以下 Prompt 要求 Agent 使用 TDD，並加入跨邊界的 E2E 驗證：

```text
請使用 $clean-code-ai-collaboration 實作這個需求。
development_rhythm: tdd
validation_profile: acceptance-e2e

先確認 RED 的失敗原因符合需求缺口，再完成最小 GREEN。
保留 Repository 既有 Gate，並回報尚未涵蓋的外部環境與副作用。
```

若這次要使用 TCR，除了選擇 `tcr`，還要明確授權版本控制操作：

```text
請使用 $clean-code-ai-collaboration 處理這次高風險重構。
development_rhythm: tcr
validation_profile: repository

我授權 Agent 在這次任務中：
1. 每個通過測試的小步驟可以 Commit。
2. 測試失敗時，可以 Revert 該步驟由 Agent 建立的變更。
3. 不得復原或覆蓋任務開始前已存在的使用者變更。
```

`development_rhythm: tcr` 本身不等於 Commit／Revert 授權。缺少快速可靠的測試、隔離工作樹或當次明確授權時，Skill 會回報阻礙並提出可行替代方案。

### 專案預設值：寫入 Repository 的 AGENTS.md

例如，團隊希望平常由 Skill 判斷開發節奏，並至少執行 Repository 規定的驗證，可以在 Repository 根目錄的 `AGENTS.md` 加入：

````markdown
## Clean Code AI Collaboration Policy

```yaml
development_rhythm: auto
validation_profile: repository
```

- 保留 Repository 既有的 Build、Test、Lint 與 Architecture Gate。
- 回報實際採用的開發節奏、驗證範圍與尚未涵蓋的風險。
````

如果專案的功能大多適合先寫測試，也可以把預設節奏改成：

```yaml
development_rhythm: tdd
validation_profile: repository
```

Repository Policy 可以指定偏好，仍然不能長期預先授權所有 TCR 的 Commit／Revert。執行 TCR 時，請在當次 Prompt 重新確認範圍與版本控制授權。

如果不同模組需要不同預設值，可以使用巢狀 `AGENTS.md`。例如：

```text
my-repository/
├─ AGENTS.md
├─ backend/
│  └─ AGENTS.md
└─ frontend/
   └─ AGENTS.md
```

根目錄的 `AGENTS.md` 可以保留整個專案都要遵守的 Gate；`backend/AGENTS.md` 則只放後端模組要覆寫的偏好：

````markdown
## Clean Code AI Collaboration Policy

```yaml
development_rhythm: characterization-first
validation_profile: repository
```
````

以 Codex 為例，`AGENTS.md` 不是根據「準備修改哪一個檔案」動態載入。Codex 每次啟動時，會從 Repository 根目錄一路讀到目前工作目錄（CWD）；越接近 CWD 的指示會排在後面，發生衝突時也由它覆寫上層偏好。因此，要使用 `backend/AGENTS.md`，請把 `backend` 設為這次任務的工作目錄，或先進入該目錄再啟動 Codex：

```powershell
Set-Location .\backend
codex
```

如果從 Repository 根目錄啟動，Codex 不會因為後來修改了 `backend` 內的檔案，就自動補載入 `backend/AGENTS.md`。其他 Agent Client 的搜尋路徑與覆寫規則可能不同，請以該 Client 的文件為準。Codex 的完整規則可參考[官方 `AGENTS.md` 說明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

### 怎麼選擇 TDD、TCR 或其他節奏？

`development_rhythm` 支援下列設定：

| 設定 | 建議使用情境 | 不適合時的處理方式 |
| --- | --- | --- |
| `auto` | 尚未決定節奏，希望 Skill 依風險、Oracle、測試速度、工作樹與授權判斷 | Agent 必須回報最後採用哪一種節奏及原因 |
| `direct` | 修改範圍小、行為已知、容易復原，現有測試能快速觀察結果 | 新規則、Bug 邊界或狀態轉換能先形成 RED 時，改用 TDD |
| `tdd` | 可以在修改正式程式碼前，用失敗測試清楚描述預期行為 | Legacy 行為尚未釐清時，先用 `characterization-first` |
| `tcr` | 高風險修改可切成極小步驟，測試快速可靠，而且工作樹已隔離 | 缺少任一前提時先停止；常見替代方案是 TDD |
| `characterization-first` | Legacy Code 的現有行為不明，重構前需要先固定可觀察結果 | 已有清楚的新需求與獨立 Oracle 時，可改用 TDD |

通常可依下列方式快速判斷：

- 一般需求或 Bug，而且能先寫出有意義的失敗測試：選 `tdd`。
- 高風險重構、每一步都要能立即丟棄，而且測試夠快：選 `tcr`。
- Legacy Code 行為不清楚：選 `characterization-first`。
- 很小、可逆、已有快速測試的修改：選 `direct`。
- 無法確定：保留 `auto`，讓 Skill 根據 Repository 證據判斷。

### 常見任務可以怎麼搭配？

下表提供起點，最後仍以 Repository 的風險、工具與必要 Gate 為準：

| 任務情境 | `development_rhythm` | `validation_profile` | 原因 |
| --- | --- | --- | --- |
| 小型、可逆，而且已有快速測試的修正 | `direct` | `focused` | 避免為低風險修改製造多餘流程 |
| 新增業務規則、邊界值或修正 Bug | `tdd` | `focused` 或 `repository` | 先用 RED 說清楚需求缺口，再完成最小 GREEN |
| 影響 UI、API、資料庫或外部服務的使用者流程 | `tdd` | `acceptance-e2e` | 同時保留測試驅動節奏與跨邊界驗收 |
| 高風險重構，而且每一步都能快速驗證與安全復原 | `tcr` | `repository` | 用極小 Checkpoint 限制錯誤累積；仍需當次版本控制授權 |
| Legacy Code 行為不明，準備重構或移轉 | `characterization-first` | `repository` | 先記錄現有可觀察行為，避免整理時誤改系統答案 |
| 已有重要測試，但不確定 Assertion 能否抓到錯誤 | `tdd` 或 `auto` | `mutation-assisted` | 用 Mutation Testing 檢查既有 Oracle 的偵錯能力 |

### 驗證範圍是另一個設定

`validation_profile` 支援：

| 設定 | 驗證範圍 |
| --- | --- |
| `auto` | 依實際風險與 Repository 現有工具選擇 |
| `focused` | 執行最小且能觀察本次行為的 Test、Build、Lint 或 Contract Check |
| `repository` | 執行 Repository 對本次 Diff 規定的完整 Gate |
| `acceptance-e2e` | 加入跨 UI、API、Persistence、Messaging 或 Provider 的使用者結果驗證 |
| `mutation-assisted` | 用範圍受控的 Mutation Testing 檢查重要測試能否抓到錯誤變化 |

這個設定只能增加或選擇適合的檢查，不能略過 Repository 規定的必要 Gate。例如選擇 `focused`，而 `AGENTS.md` 規定合併前必須跑完整測試與 Lint，Agent 仍要執行這些 Gate。

### 設定優先順序

Skill 依下列順序解析：

1. 當次 User Prompt 的明確設定。
2. 距離目前工作目錄最近、且已被 Client 載入的巢狀 Repository Policy。
3. Repository 根目錄或更上層已載入的 Policy。
4. 上述來源都沒指定時使用 `auto`。

這是 Skill 的設定解析順序；實際載入哪些 Repository Instruction，仍由 Agent Client 決定。當次 Prompt 或較近工作目錄的 Policy 可以覆寫開發節奏與驗證 Profile 的偏好，仍然無法取消必要 Gate、安全限制或授權邊界。明確指定的策略無法執行時，Skill 必須停止、說明缺少的條件並提出替代方案，等使用者決定是否更換節奏。

執行開始前或結果回報中，應該看得到：

- 要求的 `development_rhythm`、設定來源與實際採用值。
- 要求的 `validation_profile`、設定來源與實際採用值。
- 缺少的前提、無法執行的原因與建議替代方案。
- Repository 必要 Gate 是否保留，以及仍未驗證的風險。

### 常見設定問題

#### 一定要選 TDD 或 TCR 嗎？

不用。保留 `development_rhythm: auto`，Skill 會根據行為是否明確、Oracle 是否可靠、測試速度、工作樹狀態與現有授權提出選擇。

#### 設定一定要寫成 YAML 嗎？

不用。欄位名稱固定即可，可以直接寫在一般 Prompt，也可以放在 `AGENTS.md` 的 YAML Code Block。它們是給 Agent 讀取的指令契約，目前沒有另外執行設定檔解析器。

#### `AGENTS.md` 已設定 TDD，這次可以改用 Direct 嗎？

可以。當次 Prompt 的明確設定優先於 Repository 預設值。Agent 仍需確認 Direct 符合目前情境，而且不能略過 Repository 必要 Gate。

#### `AGENTS.md` 設定 TCR 後，Agent 就能自行 Commit 與 Revert 嗎？

不能。TCR 的偏好與版本控制授權分開處理。每次執行 TCR 都要在當次任務確認可操作的工作樹、Commit 範圍與 Revert 邊界。

#### 選擇 `focused` 會不會只跑一項測試？

不一定。`focused` 代表先選擇最能觀察本次風險的最小驗證集合。Repository 若規定完整測試、Lint 或其他 Gate，這些檢查仍然要執行。

#### Skill 為什麼阻擋我的 TCR 要求？

常見原因包括測試回饋太慢、測試 Oracle 不可靠、工作樹沒有隔離，或尚未授權 Commit／Revert。Skill 會列出缺少的前提與替代方案，再由使用者決定是否調整節奏。

## 可組合的 Language／Framework Profiles

預設呼叫方式仍是 `$clean-code-ai-collaboration`。Repository Code Change 會以本次 Changed Module 為單位，依可驗證的檔案、最近 Owning Manifest 與 Dependency Marker，組合適用且可用的 Language／Framework Profile；找不到適用 Profile 時，Core Only 也是有效結果。Explicit Profile（明確指定 Profile）仍不能繞過 Availability、Applicability、相依、衝突、Repository Gate、風險或授權邊界。

[v0.5.2 M2 Pilot](evals/results/v0.5.2-profile-pilot.json) 已保存全新 34 組執行與匿名 Review：C# 為 `no_difference`、Python 為 `inconclusive`、TypeScript 為 `failed`，三者維持 Experimental；React 為 `passed`，升為 Beta。React 的改善只出現在本輪固定比較中的舊請求狀態覆寫防護，不能推論所有 React 任務都優於比較組。Go、Rust、Java 與 Vue 仍是 Planned 不可用，不能 Routing 或 Packaging。

本輪受測 Skill 固定為已發布 v0.5.1；v0.5.2 僅更新協定與證據，未修改四份 Profile Reference 的技術指引語意。Beta 是單次 Pilot 的證據成熟度，尚非 Stable／Full Run；[v0.5.1 歷史結果](evals/results/v0.5.1-profile-pilot.json) 原樣保留。協定、失敗原因與限制見 [Benchmark](evals/benchmark.md#v052-profile-evidence-remediation-pilot)。

目前 Profile 狀態由下列 Generated Matrix 呈現；Generated Region 只能由 Repository Script 更新。

<!-- profile-matrix:generated:start -->
| Profile | Kind | Status | Reference | Benchmark |
| --- | --- | --- | --- | --- |
| C# / .NET | language | experimental | [Open](clean-code-ai-collaboration/references/language-csharp.md) | pilot_recorded |
| Python | language | experimental | [Open](clean-code-ai-collaboration/references/language-python.md) | pilot_recorded |
| TypeScript | language | experimental | [Open](clean-code-ai-collaboration/references/language-typescript.md) | pilot_recorded |
| React | framework | beta | [Open](clean-code-ai-collaboration/references/framework-react.md) | pilot_recorded |
| Go | language | planned | Not available | not_started |
| Rust | language | planned | Not available | not_started |
| Java | language | planned | Not available | not_started |
| Vue | framework | planned | Not available | not_started |
<!-- profile-matrix:generated:end -->

### 本機 Specialist Package

下列命令會從乾淨的目前 Commit，建立只 Bundled C# Profile 的本機 Sample Package：

```powershell
.\.venv\Scripts\python.exe scripts\build_skill_package.py --source-root . --output dist/clean-code-ai-csharp --source-mode release --profile csharp
.\.venv\Scripts\agentskills.exe validate dist/clean-code-ai-csharp
```

`dist/clean-code-ai-csharp/` 是 Git ignored 的本機產物；目前沒有 ZIP、未發布，也不能從 Package 名稱推論每個任務都套用 C#。Bundled Profile 仍要依 Changed Module 判斷，Core Only 仍是有效結果。

Profile 貢獻入口只有 [Profile Authoring Guide](docs/profile-authoring.md)；該文件定義生命週期、Reference、Evidence、驗證與發布邊界。

## 安裝

此版本的固定安裝 Tag 為 `v0.5.2`，Skill 版本為 `0.5.2`。React 為 Beta；C#、Python 與 TypeScript 維持 Experimental。正式發布不代表所有 Profile 效果通過；實際 Outcome 與限制見 [v0.5.2 Pilot 結果](evals/results/v0.5.2-profile-pilot.json)。

先取得 Repository：

```powershell
git clone https://github.com/eric861129/Clean-Code-AI-Collaboration-Skill.git
Set-Location .\Clean-Code-AI-Collaboration-Skill
```

macOS／Linux：

```bash
git clone https://github.com/eric861129/Clean-Code-AI-Collaboration-Skill.git
cd Clean-Code-AI-Collaboration-Skill
```

如果要安裝此正式版本 `v0.5.2`，請先切換到對應 Tag，避免日後 `main` 更新時安裝到不同版本：

```shell
git fetch --tags
git checkout v0.5.2
```

接著確認 Skill Frontmatter 的版本：

Windows PowerShell：

```powershell
Select-String -LiteralPath ".\clean-code-ai-collaboration\SKILL.md" -Pattern 'version: "0.5.2"'
```

macOS／Linux：

```bash
grep 'version: "0.5.2"' ./clean-code-ai-collaboration/SKILL.md
```

真正需要安裝的只有 `clean-code-ai-collaboration` 資料夾；`evals`、`tests`、`docs` 與 `.github` 是評測、驗證與維護資料。

### Project Skill

如果只想讓目前專案使用，請把 Skill 放到該專案的 `.agents/skills`。

Windows PowerShell：

```powershell
$skillSource = (Resolve-Path ".\clean-code-ai-collaboration").Path
$projectRoot = "C:\path\to\your-project"
$skillsRoot = Join-Path $projectRoot ".agents\skills"
$target = Join-Path $skillsRoot "clean-code-ai-collaboration"

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) {
    throw "找不到目標專案：$projectRoot"
}

if (Test-Path -LiteralPath $target) {
    throw "安裝目標已存在：$target。請先確認內容，不要直接覆寫。"
}

New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
Copy-Item -LiteralPath $skillSource -Destination $target -Recurse
```

macOS／Linux：

```bash
skill_source="$(pwd)/clean-code-ai-collaboration"
project_root="/path/to/your-project"
skills_root="$project_root/.agents/skills"
target="$skills_root/clean-code-ai-collaboration"

if [ ! -d "$project_root" ]; then
  echo "找不到目標專案：$project_root" >&2
  exit 1
fi

if [ -e "$target" ]; then
  echo "安裝目標已存在：$target。請先確認內容，不要直接覆寫。" >&2
  exit 1
fi

mkdir -p "$skills_root"
cp -R "$skill_source" "$target"
```

### Personal Skill

如果要讓同一位 User 的多個專案使用，可以安裝到個人 `.agents/skills`。

Windows PowerShell：

```powershell
$skillsRoot = Join-Path $env:USERPROFILE ".agents\skills"
$target = Join-Path $skillsRoot "clean-code-ai-collaboration"

if (Test-Path -LiteralPath $target) {
    throw "安裝目標已存在：$target。請先確認內容，不要直接覆寫。"
}

New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
Copy-Item -LiteralPath ".\clean-code-ai-collaboration" -Destination $target -Recurse
```

macOS／Linux：

```bash
skills_root="$HOME/.agents/skills"
target="$skills_root/clean-code-ai-collaboration"

if [ -e "$target" ]; then
  echo "安裝目標已存在：$target。請先確認內容，不要直接覆寫。" >&2
  exit 1
fi

mkdir -p "$skills_root"
cp -R "./clean-code-ai-collaboration" "$target"
```

安裝完成後，建議先在任務中明確指定 `$clean-code-ai-collaboration`；這也是 `v0.4.0` 的正式使用方式。Codex adapter 設定為 `allow_implicit_invocation: false`。如果 Skill 清單沒有出現，請重新啟動 Client，再確認安裝路徑與 Skill Frontmatter。

### Client 支援狀態

Agent Skills 的檔案格式可以攜帶內容，不代表每個 Client 的載入、觸發與工具行為都相同。

| Client | 內容與格式 | 本專案驗證狀態 |
| --- | --- | --- |
| Codex | Skill 核心可用，並提供 Codex adapter | 核心評測已完成，adapter 結構已驗證；v0.4.0 採 explicit-only，尚未以觸發準確率評測重新開啟 implicit invocation |
| GitHub Copilot | 核心 Markdown 內容可移植 | 尚未完成實機驗證；安裝位置與觸發方式請以 Client 官方文件為準 |
| Claude Code | 核心 Markdown 內容可移植 | 尚未完成實機驗證；安裝位置與觸發方式請以 Client 官方文件為準 |
| 其他 Agent Skills 相容 Client | 原則與參考文件可移植 | 尚未驗證，不宣稱工具、授權或輸出行為相容 |

## 使用方式

以下 Prompt 刻意分成規劃、實作與 Review。User 仍應補上真實需求、Repository 路徑、可修改範圍與驗收方式。

### 規劃

```text
請使用 $clean-code-ai-collaboration 規劃這次修改。
先列出 Repository 事實、假設與未知資訊，再比較可行方案、行為風險、Diff 邊界與停止條件。
目前只需要規劃，不要修改檔案、Commit、Push 或部署。
```

### 實作

```text
請使用 $clean-code-ai-collaboration 實作這個需求。
先確認既有行為與測試，將修改限制在必要範圍；完成後回報 Diff、實際執行的驗證、未涵蓋風險與人工決策。
未經授權不要 Commit、Push、部署或修改正式資料。
```

### Review

```text
請使用 $clean-code-ai-collaboration Review 這次變更。
依 Repository 證據檢查意圖、責任、依賴、測試、行為漂移與副作用；先列出可重現的問題，再說明盲點與建議。
不要只依作者摘要或「測試全綠」判定可以接受。
```

## Benchmark

評測的目的不是替 Skill 創造一個總分，而是讓讀者看見它在哪些公開情境改善了決策流程、哪裡沒有改善，以及我們沒有量到什麼。

- [Benchmark 說明](evals/benchmark.md)
- [評測情境與契約](evals/manifest.json)
- [v0.1.0 行為基準](evals/results/v0.1.0-baseline.json)
- [v0.2.0 初始評測](evals/results/v0.2.0-initial.json)
- [v0.4.0 Strategy Decision-Conformance Manifest](evals/manifests/v0.4.0-strategy-full-run.json)
- [v0.4.0 Strategy Decision-Conformance Harness](evals/v040_strategy_full_run.py)
- [v0.4.0 Strategy Decision-Conformance Full Run Result](evals/results/v0.4.0-strategy-full-run.json)

`v0.4.0 Strategy Decision-Conformance Full Run` 專門驗證 Subject 能否一致解讀 `development_rhythm` 與 `validation_profile`。9 組無 Skill 對照中有 5／9 符合預先固定的決策契約；Controller 分派載入 v0.4.0 Skill 的執行後，9 種情境各重複兩次，共 18／18 通過。涵蓋 Prompt 優先權、Repository Policy 預設值、`auto` 推導、TCR 權限與執行前提、必要 Gate，以及不可執行時的阻擋與替代建議。

這項結果只支持「固定情境下的策略契約解讀較一致」。它不衡量程式碼品質、不比較實作結果，也不宣稱節省 Token、時間或費用。`v0.3.0 Cross-language Full Run` 維持獨立狀態，目前尚未完成；不能拿 v0.4.0 的決策測試代替，也不把未發布的進度寫成正式結果。

公開 Result 會保存固定 Prompt、Controller Dispatch、原始 Subject JSON、重播後 Terminal，以及 Manifest、Harness、Skill 快照雜湊。可在乾淨 Checkout 重播決策 Oracle：

Windows PowerShell：

```powershell
py -3 -m evals.v040_strategy_full_run verify-result
```

macOS／Linux：

```bash
python3 -m evals.v040_strategy_full_run verify-result
```

`18／18` 是 Controller 觀察到且可重播的契約結果；公開收據無法獨立證明 Subject 是否屬於全新 Context，也無法認證服務端實際模型身分。`model` 與 `reasoning_effort` 只代表 Controller 分派時的要求值。

下列 Repository 情境數字仍來自 `v0.2.0` 的固定情境：

目前 Repository 情境評測的觀察如下：

| 評測組 | 執行數 | 自動失敗 | 情境證據完整支持 | 行為證據完整支持 | 決策理由完整支持 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 通用 Prompt 基準 | 12 | 2 | 6／12 | 7／12 | 1／12 |
| v0.2.0 Skill | 12 | 0 | 9／12 | 12／12 | 12／12 |

這組數字只適用於預先宣告的四種 Repository 情境與固定執行規約。並行情境有 3 次輸出超出預先宣告的語意 Diff Pattern，結果仍完整保留，沒有改寫成失敗或從資料中移除。Micro-eval 沒有顯示普遍的答案品質優勢；Token 與工具呼叫數也因執行環境未提供可靠資料而未比較。

兩組歷史結果的評估程序並非完全相同，公開資料已保留這項限制。因此這些結果適合用來重現與提出新假設，不適合宣稱 Skill 已在所有專案或 Client 上勝出。

## 已知限制與不保證事項

- 不保證所有 Repository、語言、模型、Client 或任務都得到相同結果。
- 不保證一定節省 Token、時間或費用；品質 Gate 也可能增加短期執行成本。
- Build 與 Test 通過，只能證明已執行範圍內的結果，不等於已部署、正式環境正確或完成 UAT。
- Process-local 的並行保護不等於跨程序、跨節點或 Exactly-once 保證。
- Skill 不會替 User 擴張授權；Commit、Push、部署、刪除檔案與正式資料修改仍需明確授權。
- Repository 事實不足時，正確結果可能是停止、揭露未知資訊並請 User 決定，而不是繼續生成程式碼。

## Repository 結構

```text
clean-code-ai-collaboration/  # 可安裝的 Skill
evals/                        # 公開情境、原始輸出與 Benchmark
tests/                        # Skill 與評測契約測試
.github/workflows/            # 自動驗證
docs/                         # 設計、計畫與維護文件
```

結構契約測試會確認 Skill 的封裝、路由、授權閘門與輸出欄位存在，但不會把全綠解讀為 Agent 行為品質已被完整證明：

```powershell
py -3 -m unittest discover -s tests -v
```

## 貢獻評測情境

歡迎補充可公開重現的情境。新的 Benchmark 應至少提供：

- 固定 Repository 與 Commit、Prompt、模型、Client、工具和授權範圍。
- 預先宣告的 Gold Files、允許的 Diff Boundary 與必須保留的行為。
- 與候選輸出分離的 Oracle 或驗收條件。
- 原始輸出、Diff、命令、Exit Code、盲點、失敗與人工決策。
- 清楚區分 `Observed`、`Inference`、`Unknown` 與 `Failure`。

請保留不利結果，不要只上傳成功案例，也不要用單一加權總分掩蓋不同面向的差異。

## 來源、非官方聲明與授權

這個 Skill 來自「Clean Code × AI Coding」系列實驗：從《無瑕的程式碼 第二版》的觀念出發，結合實際使用 AI Agent 開發的經驗，再以 CLEAN 五原則整理 User 駕馭 Agent 的方法。

本專案是個人整理與實驗成果，不是 Robert C. Martin、原出版商、OpenAI、GitHub 或 Anthropic 的官方作品。Skill 提供的是決策流程，不是特定專案的正確答案。

MIT License。詳見 [LICENSE](LICENSE)。
