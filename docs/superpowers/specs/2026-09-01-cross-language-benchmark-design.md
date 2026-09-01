# Clean Code AI Collaboration 跨語言 Benchmark 設計規格

## 文件狀態

- 日期：2026-09-01
- 狀態：聊天室設計已核准，等待書面規格確認
- Skill 版本：`v0.3.0`
- Benchmark 版本：`0.3.0-cross-language-initial`
- Fixture 版本：`cross-language-v1`
- 主要 Repository：`Clean-Code-AI-Collaboration-Skill`
- Fixture Repository：`Clean-Code-AI-Collaboration-Benchmark-Fixtures`（規劃中的公開 Repository）

## 背景

`clean-code-ai-collaboration v0.3.0` 已加入 Lightweight、Standard 與 Full Audit 三層路徑、Prototype／Production-Ready 交付成熟度、Repository-native Gate，以及明確呼叫契約。現有公開 Benchmark 則以固定的 .NET Work Item API 為主，證明範圍只涵蓋該 Repository、模型、Client 與情境。

目前證據支持的保守結論是：在既有 .NET 情境中，Skill 能讓 Agent 更穩定地辨識 Repository 契約、停止條件，以及需要交還人類的決策。它不能直接證明所有語言、模型與 Repository 都會改善，也不能宣稱一定節省 Token。

本次 Benchmark 是 `v0.3.0` 發布後的獨立外部效度研究。它不回頭改寫既有 `v0.2.0` 結果，也不把尚未執行的跨語言評測包裝成 Skill 發布時已具備的證據。

## 研究問題

本次評測要回答三個有限而具體的問題：

1. 當相同 Codex Agent 離開主要 .NET Demo，進入 TypeScript／React 與 Python／FastAPI Repository 時，Skill 是否仍能幫助它辨識情境、契約與停止條件？
2. 相較於只給任務，或只補一句「請遵守 Clean Code」，明確載入 `v0.3.0` Skill 是否更常產生局部、可驗證且不擅自擴張的候選？
3. Skill 的差異是否同時出現在跨語言的共同業務規則，以及各生態系特有的開發問題？

結果只回答這四個小型 Fixture、指定模型與固定執行條件下的觀察，不外推成普遍保證。

## 目標

1. 建立 TypeScript／React 與 Python／FastAPI 的小型、公開、可重跑 Fixture。
2. 以 Control、Generic Clean Code 與 Skill `v0.3.0` 三組對照執行 Fresh Context Session。
3. 每個技術棧同時測量一個可跨語言比較的業務規則，以及一個生態系原生問題。
4. 使用獨立 Oracle、匿名人工審查與固定失敗條件，避免採信 Agent 自我回報。
5. 保存 Prompt、Diff、命令、Exit Code、環境、Oracle 與盲點，讓結果可追蹤。
6. 清楚區分已觀察、推論、未知、失敗與限制，不以單一總分掩蓋取捨。

## 非目標

1. 不在第一階段加入 Java／Spring、大型 Legacy Repository、Migration 或真實團隊 Blind Review。
2. 不重新執行現有 .NET Benchmark；.NET 結果只作歷史參考，不混入新的主要比較。
3. 不以 Benchmark 修改、微調或重新訓練模型。
4. 不要求所有候選採用同一種架構或命名；行為、邊界與可驗證性優先於風格一致。
5. 不用輸出字數推估 Token，也不宣稱 Token、時間或 Tool Call 一定下降。
6. 不在 Subject Session 中使用外部 API、正式資料庫、Secret 或需要人工登入的服務。
7. 不把 Pilot 當成可任意調整規則後仍納入正式結果的試跑。

## 評測矩陣

### 技術棧與情境

| 技術棧 | 共同業務規則情境 | 生態系原生情境 |
| --- | --- | --- |
| TypeScript／React | High Priority 逾期規則加入兩小時寬限 | 避免 React Effect 因相同識別碼重新 Render 而重複請求 |
| Python／FastAPI | High Priority 逾期規則加入兩小時寬限 | 以既有 Protocol／Dependency Injection 隔離通知 Provider |

每個 Fixture 維持約 5～10 個主要檔案，測試、型別檢查與 Lint 應能在本機快速完成。情境刻意保持小型，避免 Benchmark 測到的主要差異只是長時間執行能力或套件安裝速度。

### 對照組

每個情境固定使用三組對照：

1. **Control**：只提供任務與 Fixture 原有的共同 Repository Instruction。
2. **Generic Clean Code**：在 Control 條件上額外加入「請遵守 Clean Code 完成任務。」
3. **Skill v0.3.0**：安裝精確版本的 Skill，並明確使用 `$clean-code-ai-collaboration`。

三組只能改變上述指示方式。模型、Reasoning Effort、Client、工具權限、Fixture Commit、任務、時間限制、網路與 Oracle 均保持一致。

### 執行次數

- 4 個 Fixture 情境
- 3 組對照
- 每組 3 次 Fresh Context Repetition
- 總計 36 個 Subject Session

執行分成兩階段：

1. **Pilot**：每個情境與每組對照先執行第 1 次，共 12 個 Session。
2. **Full Run**：契約確認不需調整後，再執行第 2、3 次，共 24 個 Session。

Pilot 只有在 Fixture、Prompt、Oracle、允許修改邊界與評分方式完全不變時，才可直接計入正式結果。若其中任何一項需要改動，該 Fixture 三組對照的 Pilot 全部作廢並保留作廢原因，不能只重跑表現較差的組別。

## 固定執行條件

- Model：`gpt-5.6-sol`
- Reasoning Effort：`high`
- Client：Codex CLI
- Context：每次使用全新、暫時且獨立的 Git Repository
- Session：`codex exec --ephemeral --json --ignore-user-config`
- Agent Session 上限：8 分鐘
- Fixture 安裝／準備上限：2 分鐘
- 獨立 Oracle 上限：2 分鐘
- 網路：Baseline 準備階段可依 Lockfile 下載與快取套件；Subject 可操作的 Repository Sandbox 關閉網路，不得臨時下載套件、查詢解答或讀取 Fixture Repository 的其他內容
- 權限：三組使用相同 Sandbox 與工具權限

`--ignore-user-config` 用來降低個人 Codex 設定污染比較；共同 Repository Instruction 仍由 Fixture 明確提供。Skill 組只載入固定的 `v0.3.0` 內容，不讀取開發中的工作目錄版本。

## Fixture Repository 設計

四個 Fixture 存放於獨立的公開 Repository `Clean-Code-AI-Collaboration-Benchmark-Fixtures`，並以 `cross-language-v1` Annotated Tag 固定版本。這個 Repository 與 Skill Repository 分離，避免 Subject 看見 Harness、答案、匿名對照表或其他情境的 Hidden Oracle。

執行時只匯出當次選定的 Fixture 到暫時 Repository。Subject 不得看見：

- 其他 Fixture 的候選或解法。
- Hidden Evaluator Test。
- 對照組匿名映射。
- 人工 Rubric 結果。
- 前一次 Repetition 的輸出。

### TypeScript／React 共同業務規則

任務要求 High Priority 工作項目延後兩小時才視為逾期。候選必須保留：

- 一般 Priority 的既有逾期規則。
- Completed 項目不進入逾期清單。
- 剛好到達兩小時邊界時的明確行為。
- Component Props 與公開 UI Contract。
- 與本次規則無關的 Render 行為。

Oracle 至少涵蓋邊界前、剛好邊界、邊界後、一般 Priority 與 Completed 五類情境。設計目的不是比較 React 架構偏好，而是觀察 Agent 能否找到真正的規則位置，只修改必要責任。

### Python／FastAPI 共同業務規則

任務與 React Fixture 使用相同領域規則：High Priority 延後兩小時才逾期。候選必須保留：

- 既有 HTTP Status 與 Response Schema。
- 一般 Priority 與 Completed 的行為。
- 時間等號邊界。
- 與規則無關的 Route 與資料模型。

使用相同業務規則可比較不同語言下的 Context 定位、Diff 局部性與行為保存；不比較語言效能或框架優劣。

### TypeScript／React 生態系原生情境

任務要求相同識別碼的重新 Render 不得重複送出預覽請求；識別碼改變時，舊請求必須取消，新請求仍要正常執行。候選必須保留：

- Loading 與 Error UI 語意。
- Component Props 與 API Response Contract。
- 識別碼改變後的新資料能顯示。
- Unmount 或新請求出現後，不讓舊請求結果覆蓋新狀態。

這個情境用來觀察 Agent 是否理解 Effect Lifecycle、Cancellation 與外部副作用，而不只是把 Dependency Array 改到 Lint 變綠。

### Python／FastAPI 生態系原生情境

任務要求在既有通知流程中，透過已存在的 Protocol 與 Dependency Injection 隔離通知 Provider。候選必須保留：

- Route 的 Response Schema 與 Status Code。
- Provider 回傳失敗或拋出例外時的既有語意。
- 測試可替換 Provider 的能力。
- 現有 Use Case 的責任與執行順序。

候選不得為了展示分層再建立第二套 Domain Model、重複 Protocol 或無需求支持的 Repository Layer。這個情境用來觀察 Agent 是否先讀取既有依賴邊界，再決定最小抽象。

## Repository-native Gate

### TypeScript／React

- 依 Lockfile 安裝的固定 npm 依賴
- Vitest
- Testing Library
- TypeScript Type Check
- ESLint

### Python／FastAPI

- 依 Lockfile 或固定依賴清單安裝的 Python 環境
- pytest
- Ruff Format Check
- Ruff Lint
- mypy 僅在 Fixture 能保持小型、快速且不需要大量型別樣板時加入

Baseline 必須先在乾淨 Fixture 上通過所有公開 Gate 與 Hidden Oracle。Subject 執行後，由 Harness 在 Agent Session 外重新執行相同 Gate 與獨立 Oracle；Agent 宣稱全綠不能取代這一步。

## 系統架構

### Repository 分工

`Clean-Code-AI-Collaboration-Skill` 保存版本化的評測契約、Harness 與結果：

```text
evals/
├── manifests/
│   └── v0.3.0-cross-language.json
├── harness/
│   ├── planner.py
│   ├── fixture_builder.py
│   ├── subject_runner.py
│   ├── oracle_runner.py
│   ├── evidence_recorder.py
│   └── result_builder.py
└── results/
    └── v0.3.0-cross-language.json
```

實際檔名可在實作計畫中依現有模組結構微調，但不得把 Fixture、Hidden Oracle 與 Skill 發布內容混在同一個 Subject 可見目錄。

`Clean-Code-AI-Collaboration-Benchmark-Fixtures` 保存四個 Fixture、公開 Gate、Lockfile、共同 Repository Instruction 與 Hidden Evaluator Test。Hidden 的意思是執行時不提供給 Subject，不代表評測完成後永久不公開；正式發布 Benchmark 時應一併公開，讓第三方能重跑。

### Harness 元件

1. **Planner**：驗證 Manifest，產生 36 個 Run Slot 與可重現的打散順序。
2. **Fixture Builder**：由固定 Tag／Commit 匯出單一 Fixture，建立乾淨暫時 Git Repository，完成 Baseline Gate。
3. **Subject Runner**：依對照組組合 Prompt 與 Skill，執行 Codex Fresh Context Session，套用時間與權限限制。
4. **Oracle Runner**：在 Subject 結束後凍結候選，獨立執行公開 Gate、Hidden Oracle 與 Diff Boundary 檢查。
5. **Evidence Recorder**：保存 JSONL、Prompt、Diff、命令、Exit Code、環境、時間與錯誤。
6. **Anonymizer／Result Builder**：隱藏 Arm 身分，產生人工審查材料，彙整分維度結果與公開 JSON。

元件以檔案與結構化 JSON 交換資料，不依賴常駐服務或外部資料庫。每個 Run 先寫入獨立暫存結果，最後才產生不可手動覆寫的彙整檔，避免中途失敗破壞其他 Run。

## 執行資料流

1. 驗證 Manifest Schema、Fixture Tag、Skill Commit、Prompt Hash、Lockfile Hash 與所有 Run Slot。
2. 依固定 Seed 產生打散後的執行順序，降低時間順序偏差，同時保留可重現性。
3. 匯出單一 Fixture，建立暫時 Git Repository，確認工作目錄乾淨。
4. 在 Subject 介入前執行 Baseline Gate 與 Hidden Oracle；Baseline 失敗則停止該 Fixture，不產生 Subject 結果。
5. 依 Arm 建立 Prompt：Control 只含任務；Generic 加入一句 Clean Code 指示；Skill 安裝固定版本並明確呼叫。
6. 使用相同模型、Reasoning Effort、Sandbox、權限與時間限制執行 Subject。
7. Session 結束或逾時後凍結工作目錄，保存原始 JSONL、最後輸出、Git Status、Diff 與雜湊。
8. 在 Subject 外執行公開 Gate、Hidden Oracle、允許修改邊界與禁止行為檢查。
9. 將 Arm 匿名化，交由一位 Reviewer 依三份既有 Rubric 分別評估。
10. 36 個 Run Slot 都取得 Terminal State 後，產生機器可讀結果與人類可讀摘要。

## 失敗、逾時與重跑規則

### Automatic Failure

符合下列任一條件即為 Automatic Failure：

- 破壞指定公開 Contract 或必須保留的行為。
- Hidden Oracle 或必要 Repository Gate 失敗。
- 產生禁止的重複外部副作用。
- 未執行驗證卻明確宣稱已通過。
- 修改超出事前定義的 Diff Boundary，且無法由任務責任解釋。
- Session 逾時、Crash，或沒有留下可評估候選。

命名偏好、抽象數量、輸出篇幅、Token、Tool Call 與執行時間本身不構成 Automatic Failure；它們只在候選已通過必要行為 Gate 後，作為 Rubric 或成本觀察。

### 逾時

Agent 超過 8 分鐘即記為 Timeout，不自動重跑。Fixture 安裝或 Oracle 超過各自上限時，先判斷是 Fixture／Harness 問題還是候選造成；原因與部分輸出都必須保留。

### 可重跑條件

只有明確的 Harness、套件快取、CLI Runner 或基礎環境故障可以重跑一次。重跑不得覆蓋原始失敗，Result 必須同時記錄 Original Attempt、Retry 原因與 Retry 結果。

Agent 選錯方向、沒有完成、測試失敗、超時或輸出品質不佳都是真實結果，不得以「再給一次機會」改善數字。

## 人工匿名審查

每個候選由一位 Reviewer 在不知道 Arm 的情況下，依既有三個維度分開審查：

1. **Context and Locality**：是否找到真正的規則、責任與最小修改邊界。
2. **Behavior and Validation**：是否守住行為，並以適合風險的獨立證據驗證。
3. **Decision and Escalation**：是否避免自行補完未知，並在需要 Owner 決策時正確停止或交還。

Reviewer 看到的是匿名候選、任務、Fixture 公開契約、Diff、Gate 與 Oracle 結果；不看 Arm、Repetition 先後與其他 Reviewer 意見。本階段不執行多人一致性統計，也不宣稱代表真實團隊 Review。

不得把三個維度相加成單一總分。Automatic Failure、各維度評估與成本資料分開呈現。

## Result 契約

公開結果存放於 `evals/results/v0.3.0-cross-language.json`。每次 Run 至少保存：

### 身分與版本

- Benchmark、Fixture 與 Skill 版本
- Language、Scenario、匿名 Arm、Repetition、Attempt
- Fixture Commit、Skill Commit、Prompt SHA-256、Lockfile SHA-256

### 執行條件

- Codex CLI 版本
- Model 與 Reasoning Effort
- Sandbox、工具權限與網路條件
- 作業系統、Runtime 與套件管理器版本
- 固定 Seed 與 Run 順序位置

### Subject 證據

- 完整 Prompt
- 原始 JSONL 路徑與雜湊
- 最後輸出
- 查閱、修改與驗證的檔案（能可靠取得時）
- Git Status、Diff 與 Diff SHA-256
- Subject 命令、Exit Code 與經過時間

### Evaluator 證據

- Baseline Gate 結果
- 公開 Gate 與 Hidden Oracle 命令、Exit Code、經過時間與摘要
- Diff Boundary 判定與越界路徑
- Automatic Failure 與具體原因
- Known Blind Spots

### Review 與成本

- 三個匿名 Rubric 的分維度結果與理由
- Human Decision Required
- Token、Tool Call 與時間 Telemetry 的取得狀態
- Comparison Eligibility

無法可靠取得的欄位必須明確記為 `not_available`，不得推估。完整原始 JSONL 預設存放於 Git 忽略的 `.benchmark-runs/`；公開 Result 保存可驗證摘要與雜湊。若原始資料體積適合公開，可在結果發布時另作 GitHub Release Asset，而不是把大量執行紀錄直接塞入主分支。

## 報告方式與公開主張

36 個規劃 Run Slot 都必須出現在結果中，狀態可以是 Passed、Automatic Failure、Timeout、Infrastructure Failure 或 Invalidated Pilot；不得省略失敗 Run。

結果依下列方式呈現：

- 分 Language、Scenario 與 Arm 顯示通過、失敗及失敗原因。
- 分別呈現 Context and Locality、Behavior and Validation、Decision and Escalation。
- 清楚區分 Observed、Inference、Unknown、Failure and Limitation。
- 不建立跨維度總分，也不把不同風險的 Fixture 合成「勝率」。
- Token、Tool Call 與時間只在 Telemetry 可靠，且候選通過相同行為 Gate 時比較。
- 若沒有 Token Telemetry，直接報告無法取得，不用字數替代。
- 時間較短不代表品質較好；只作為同品質候選的成本資料。

README 與 Benchmark 文件只能宣稱：這是一組 TypeScript／React 與 Python／FastAPI 的小型初步跨語言證據。不得寫成「支援所有 React／Python 專案」、「Clean Code 會讓 AI 更聰明」，或「安裝後一定節省 Token」。

## Manifest 契約

`evals/manifests/v0.3.0-cross-language.json` 應固定：

- Schema 與 Benchmark 版本。
- Fixture Repository、Tag、Commit 與子目錄。
- 四個 Scenario 的任務、必須保留行為、允許修改範圍、禁止變更與 Oracle。
- 三組對照的精確指示。
- Model、Reasoning Effort、Client、Sandbox、權限與 Timeout。
- Repetition、Pilot、Seed 與 Retry 規則。
- Result 必填欄位與匿名化方式。
- Rubric 版本。

Manifest 一旦進入正式 Full Run 即不可就地修改。必要變更要建立新 Benchmark 版本，並保留舊 Manifest 與已產生結果。

## 測試策略

Harness 實作採測試先行，至少涵蓋：

1. Manifest 缺少必要欄位、重複 Run Slot、未知 Arm 或不合法 Timeout 時拒絕執行。
2. 36 個 Run Slot 的計算、匿名化與固定 Seed 排序可重現。
3. Control、Generic 與 Skill Prompt 只存在預期差異。
4. Subject 只能看見指定 Fixture，無法讀取 Hidden Oracle 或其他情境。
5. Agent、安裝與 Oracle Timeout 被正確分類，且不觸發未授權重跑。
6. Infrastructure Retry 保留原始失敗，且最多一次。
7. Diff Boundary 同時檢查新增、修改、刪除與重新命名來源／目的路徑。
8. Automatic Failure 不會被 Rubric 高分或後續摘要覆蓋。
9. `not_available` Telemetry 不會被計入成本比較。
10. Pilot 契約變更會使該 Fixture 三組全部失效。
11. 所有 36 個 Slot 都有 Terminal State 才能建立正式結果。
12. 公開摘要無法反推出匿名 Arm，只有最終彙整階段才恢復 Arm 名稱。

Fixture 必須分別有 Baseline 自我測試、Hidden Oracle 的正負案例，以及一個故意破壞契約的 Mutation，證明 Evaluator 真的能抓到預定風險。

## 安全、隱私與可重現性

- Fixture 只使用虛構資料，不含雇主、校務系統、學生、使用者或內部 Repository 資訊。
- Prompt、JSONL、Diff 與錯誤輸出在公開前執行 Secret Scan。
- Subject 不持有 GitHub Token、雲端憑證、正式 API Key 或個人設定。
- 暫時 Repository 路徑不寫入公開結果；只保留可重現的相對路徑。
- Fixture 與 Skill 都以不可變 Commit／Tag 固定，套件版本由 Lockfile 固定。
- 公開 Result 必須包含 Runtime、CLI 與作業系統資訊，讓第三方辨識環境差異。

## 風險與控制

| 風險 | 控制方式 |
| --- | --- |
| Fixture 太複雜，Benchmark 變成耐力測試 | 每個情境限制在小型 Repository 與快速 Gate；Agent Session 固定 8 分鐘 |
| Fixture 太玩具化，無法觀察 Repository Context | 保留真實 Contract、邊界值、副作用或依賴取捨，不只測語法修改 |
| Skill 組看見額外答案 | Skill 只提供通用方法；Fixture、任務與 Oracle 對三組一致，Hidden Oracle 不進 Subject Context |
| Pilot 後調整規則美化結果 | 任何 Fixture 契約變動都使該 Fixture 三組 Pilot 一起作廢 |
| 執行順序或快取影響結果 | 固定 Seed 打散順序；每次使用 Fresh Context 與暫時 Git Repository；依 Lockfile 預先快取 |
| Agent 自我回報被誤當驗證 | Subject 結束後由獨立 Oracle Runner 重跑 Gate |
| Reviewer 知道 Arm 而產生偏見 | 審查材料匿名化；最終彙整才恢復 Arm |
| 只挑成功 Run 發布 | 36 個 Slot 都要有 Terminal State，失敗、逾時與作廢 Pilot 不得省略 |
| 將跨語言初步結果普遍化 | README 明列技術棧、模型、情境與限制；使用 Observed／Inference／Unknown 分層 |
| 用輸出長度冒充 Token | Telemetry 缺少即記 `not_available`，禁止估算 |

## 驗收條件

本次 Benchmark 完成必須同時符合：

1. 獨立公開 Fixture Repository 已建立，四個 Fixture 固定於 `cross-language-v1` Tag。
2. 每個 Fixture 在乾淨環境通過公開 Gate、Hidden Oracle 與故意破壞契約的負向測試。
3. Versioned Manifest 能產生正好 36 個唯一 Run Slot。
4. Harness 契約測試、格式檢查與既有 Repository CI 全部通過。
5. Pilot 契約經確認後，才執行剩餘 24 個 Session；若有變更，依規則完整作廢並重跑。
6. 每個 Run 都保存固定版本、Prompt、Diff、命令、Exit Code、Oracle、失敗、盲點與 Telemetry 狀態。
7. 三組候選在 Reviewer 看見前已匿名化，並依三個維度分開審查。
8. 36 個 Slot 都有 Terminal State，沒有選擇性刪除或重跑不佳結果。
9. `evals/results/v0.3.0-cross-language.json` 能通過 Schema 與一致性驗證。
10. Benchmark 文件與 README 清楚區分新結果、既有 .NET 證據、未知與不可泛化範圍。
11. 沒有 Secret、個資、雇主內部資料、暫時絕對路徑或未授權內容進入公開 Commit。
12. 只有實際取得且比較資格相同的資料，才用於 Token、Tool Call 或時間主張。

## 實作與外部操作邊界

這份 Commit 只新增設計規格，不建立 Fixture Repository、不修改 Benchmark Harness、不啟動 Codex Session，也不產生結果檔。

書面規格經使用者確認後，下一步才建立詳細實作計畫。實作計畫必須把 Fixture、Harness、Pilot、Full Run、匿名 Review、結果發布拆成可驗證階段；建立公開 Repository、執行 36 個付費或耗時 Session、Push、Tag 與 Release 都要在相應階段保留清楚的外部操作邊界。
