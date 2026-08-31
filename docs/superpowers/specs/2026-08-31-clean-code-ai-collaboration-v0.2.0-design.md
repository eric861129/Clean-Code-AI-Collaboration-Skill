# Clean Code AI Collaboration Skill v0.2.0 設計規格

## 文件狀態

- 日期：2026-08-31
- 狀態：聊天室設計已核准，等待書面規格確認
- 目標版本：`v0.2.0`
- 目前版本：`v0.1.0`
- Repository：`Clean-Code-AI-Collaboration-Skill`

## 背景

`v0.1.0` 已具備有效的 Agent Skills 封裝、精簡入口、六份按需載入的 Reference、Codex UI Metadata、授權閘門與 Review Output Contract。現有十項測試能確認檔案、欄位與路由存在，也通過 Skill 格式驗證。

目前驗證只涵蓋結構契約。它尚未回答以下問題：

1. Agent 是否會在正確任務啟用這個 Skill。
2. Skill 是否幫助 Agent 找到正確的 Repository Context。
3. Clean Code 判斷是否讓修改更局部、行為更穩定、結果更容易驗證。
4. Agent 面對模糊需求、時間壓力或全綠測試時，是否仍會暴露假設、盲點與停止條件。
5. Codex 以外的 Agent Skills 相容工具能否採用核心流程。

`v0.2.0` 將 Skill 從「可安裝的決策文件」提升成「跨平台、可驗證、可比較的 AI Coding 協作能力」。

## 產品定位

這個 Skill 適用於 AI Coding 的規劃、實作與 Review。它協助 Agent 依 Repository 事實運用 Clean Code 的程式碼、測試、設計、架構與軟體工藝判斷，並用 CLEAN 五原則控制情境、範圍、意圖、證據與行為。

Skill 不替 Repository 發明業務規則，也不把單一 Clean Code 寫法升格成通用答案。它提供可重複的決策流程；Repository 提供事實與可執行關卡；User 與責任 Owner 保留授權、風險、優先順序及最終承諾。

## 目標

1. 遵循 Agent Skills 開放規格，讓核心流程可被多個相容 Coding Agent 使用。
2. 保留 `agents/openai.yaml`，提供 Codex 專用顯示資訊與預設 Prompt。
3. 以 Progressive Disclosure 控制載入內容，避免 Skill 本身排擠任務與 Repository Context。
4. 把 Clean Code 與 AI Coding 的關係寫成可查核機制，不使用無條件的 Token 節省或品質保證。
5. 建立無 Skill、一般 Clean Code 提示與完整 Skill 的對照評測。
6. 用行為 Oracle、Diff 邊界、Context 定位、驗證完整度與停止判斷評估效果。
7. 讓公開使用者能重跑評測、檢查限制並提交新的失敗情境。

## 非目標

1. 不建立自動重寫整個 Repository 的 Refactoring Engine。
2. 不把 Clean Code 轉成單一分數或固定架構模板。
3. 不要求所有任務同時套用 CLEAN 五項原則或全部 Reference。
4. 不用檔案數、行數、Interface 數、Token 或 Tool Call 單獨判定品質。
5. 不宣稱結構測試全綠即可證明 Agent 行為可靠。
6. 不在 `v0.2.0` 宣稱已成為主流 Skill；公開採用與外部回饋屬於後續證據。

## 設計原則

### 開放標準核心與平台轉接層

Skill 根目錄維持標準 `SKILL.md`、`references/` 與必要資源。Agent Skills 相容工具可以忽略不認識的 `agents/openai.yaml`；Codex 則使用該檔案取得顯示名稱、簡介與預設 Prompt。

核心流程不得依賴 Codex 專屬工具名稱。平台差異只能出現在安裝說明、UI Metadata 或明確標示的平台附錄。

### 短入口與按需載入

`SKILL.md` 保留共同流程、風險分流、CLEAN 檢查、Authorization Gate 與必要輸出。詳細判斷留在 Reference。Agent 只讀取會改變當前決策的檔案。

### Context 優先於通用範例

Repository 的程式碼、測試、契約、文件、歷史與負責人決策優先於 Skill 範例。缺少會改變外部行為、資料完整性、安全、依賴方向或交付決策的資訊時，Agent 必須停止並取得答案。

### 可執行關卡優先承擔機械規則

格式、靜態分析、測試、相依性掃描與其他可機械判斷的條件應交給工具。Skill 負責情境選擇、取捨、盲點、停止條件與人工決策點。

### 品質關卡先於成本比較

Token、Tool Call、經過時間與生成行數只能比較已通過相同行為與品質關卡的候選。失敗候選不得因成本較低而勝出。

## Clean Code 如何影響 AI Coding

`v0.2.0` 將以下內容視為待驗證的作用機制：

| Clean Code 能力 | 對 Agent 的預期作用 | 必須觀察的反效果 |
| --- | --- | --- |
| 領域一致且揭露意圖的命名 | 提高搜尋與定位正確率，減少從實作細節猜規則 | 名稱過長、錯誤領域詞或註解與 Code 衝突會誤導 Context |
| 內聚的函式與類別 | 讓任務需要的責任能在較小範圍內理解與修改 | 過度拆分增加跳轉與跨檔案 Context |
| 明確的資料與依賴邊界 | 限制 Diff 擴散，協助 Agent 分辨政策與機制 | 為了展示 Pattern 新增抽象會增加 Mapping 與同步成本 |
| 可讀的測試與行為 Oracle | 讓 Agent 驗證不能被偷偷改變的答案 | 測試可能保存舊誤解，也可能只覆蓋成功路徑 |
| 小週期與持續整理 | 縮小失敗時的回退範圍，避免錯誤 Pattern 快速複製 | 測試過慢或切分沒有獨立價值時會增加流程成本 |
| 可查的決策與 Evidence | 讓下一位 Agent 能重建原因、限制與未知 | 文件失效或證據來源不明會形成新的錯誤 Context |

評測結果只能支持固定 Repository、任務、模型、工具與版本下的觀察。README 必須把機制、結果、推論與限制分開呈現。

## Skill 封裝

```text
clean-code-ai-collaboration/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── clean-code-for-agent-legibility.md
    ├── code-readability.md
    ├── testing-and-change-safety.md
    ├── design-and-dependency-boundaries.md
    ├── collaboration-and-estimation.md
    ├── repository-context-template.md
    └── review-output-contract.md
```

### `SKILL.md`

入口負責：

1. 判斷任務是否符合啟用條件。
2. 依可觀察風險選擇 Lightweight Path 或 Full Path。
3. 路由最少 Reference。
4. 用 CLEAN 五原則定義 Context、Diff、Intent、Evidence 與 Behavior。
5. 在任何修改前套用 Authorization Gate。
6. 依選定路徑交付固定輸出。

入口維持 500 個英文單字以內。Frontmatter 新增 `license`、`compatibility` 與字串型 `metadata`，版本標示為 `0.2.0`。

### `clean-code-for-agent-legibility.md`

新增 Reference 負責：

- 說明 Clean Code 對 Agent 導航、理解、修改與驗證的作用機制。
- 說明過度抽象、失效文件、錯誤命名與脆弱測試的反效果。
- 提供「可讀性改善是否值得」的選擇問題。
- 固定公開主張邊界，避免把單次實驗寫成普遍定律。

### 現有判斷 References

- `code-readability.md`：名稱、註解、格式、函式、Model 與 Class。
- `testing-and-change-safety.md`：Oracle、TDD、TCR、Characterization、Acceptance、Mutation 與高風險變更。
- `design-and-dependency-boundaries.md`：Simple Design、SOLID、元件、架構、並行與外部邊界。
- `collaboration-and-estimation.md`：Ownership、平行工作、Handoff、估算與人類承諾。

每份 Reference 都要包含適用條件、選擇判準、替代方案何時更好、常見誤判與停止條件。內容不能把某次系列實驗的選擇永久固定成唯一答案。

### Context 與輸出契約

`repository-context-template.md` 收集會改變決策的 Repository 事實。`review-output-contract.md` 使用穩定識別碼連結事實、假設、未知、選項與驗證結果。

Full Path 的回報順序固定，讓使用者能快速找到：

1. 結論與目前狀態。
2. Repository Facts、Assumptions 與 Unknowns。
3. Options、Selected Option 與其他方案適用條件。
4. Behavior Boundary、Expected Diff 與 Actual Diff。
5. Validation、Evidence、Blind Spots 與停止條件。
6. Human Decisions Required。

## CLEAN 五原則在 Skill 中的責任

| 原則 | Skill 必須產生的結果 |
| --- | --- |
| C — Context-Aware Code 情境感知 | 列出決策所用 Repository 事實，區分假設與未知 |
| L — Localized Change 局部變更 | 定義預期 Diff 邊界，完成後回報偏差與原因 |
| E — Explicit Intent and Boundaries 意圖明確 | 說清楚目標、禁止事項、契約、Owner 與停止條件 |
| A — Auditable by Evidence 實據可審 | 提供命令、環境、Exit Code、產物、限制與未執行項目 |
| N — Non-Surprising Behavior 符合預期 | 固定不可漂移的行為、失敗語意、副作用順序與驗證 Oracle |

CLEAN 是同層 Review Lens，沒有固定執行順序。Lightweight Path 只回報本次真正需要的項目；Full Path 必須完整交代適用結果。

## 評測架構

Repository 根目錄新增：

```text
evals/
├── benchmark.md
├── manifest.json
├── rubrics/
│   ├── context-and-locality.md
│   ├── behavior-and-validation.md
│   └── decision-and-escalation.md
└── results/
    ├── v0.1.0-baseline.json
    └── v0.2.0-initial.json

tests/
├── test_skill_contract.py
└── test_eval_contract.py
```

評測資源留在 Repository 根目錄，不隨安裝複製到 Agent Context。Skill 使用者只取得執行所需內容，維護者則能重跑公開 Benchmark。

### 三組對照

每個完整情境使用相同 Repository Revision、任務、模型、Reasoning Effort、工具權限與執行環境，只改變指示方式：

1. Control：只提供任務與 Repository 原有指示。
2. Generic Clean Code：額外要求「請遵守 Clean Code」，不提供本 Skill。
3. Skill：明確載入 `clean-code-ai-collaboration v0.2.0`。

`v0.1.0` 保留為版本回歸參考，不混入主要三組的 Clean Code 效果比較。

### 評測情境

初版至少涵蓋四種固定情境：

1. **Context 與局部修改**：模糊命名或大型函式下新增局部規則，檢查定位與 Diff 擴散。
2. **測試與行為邊界**：現有測試全綠但缺少失敗路徑，檢查 Agent 是否誤把綠燈當完整證明。
3. **設計與依賴方向**：Provider 或 Persistence 細節滲入 Use Case，檢查抽象是否保護真實變更來源。
4. **並行與外部副作用**：重試、Lost ACK 或競態條件可能重複通知，檢查 Agent 是否辨識失敗視窗與冪等需求。

情境優先使用 `AI-CleanCode-API-Demo` 的公開、不可變 Commit。`manifest.json` 必須記錄 Repository URL、Commit SHA、任務、允許修改範圍、Oracle、必要命令與人工 Rubric。

### 評測指標

結果使用多維報告，不壓成單一總分：

| 維度 | 指標 |
| --- | --- |
| 任務正確性 | Build、Tests、Acceptance 或其他獨立 Oracle |
| Context 定位 | Gold Files 的 Recall、非必要檔案載入與錯誤規則引用 |
| 修改局部性 | 預期與實際 Diff、越界檔案、未授權契約變更 |
| 行為穩定性 | API、資料、通知、失敗、取消、並行與副作用漂移 |
| 驗證品質 | 初始失敗、回歸、Static Check、Blind Spot 與未執行項目 |
| 決策品質 | 事實、假設、未知、選項、替代條件與停止判斷 |
| 執行成本 | Token、Tool Call、經過時間與重工次數，僅作次要比較 |

每個 Release 的短句觸發與輸出形狀 Micro-eval 每組至少執行五次。完整 Repository 情境初版每組至少執行三次，原始輸出逐次保存。`v1.0.0` 前將完整情境提高到每組至少五次，並加入外部使用者案例。

### Evidence 格式

每次 Run 至少記錄：

- Run ID、日期與執行者。
- Skill 版本與對照組。
- 模型、Reasoning Effort、Client 與工具權限。
- Repository URL、Commit SHA 與工作目錄狀態。
- 完整 Prompt、載入的 Skill／Reference 與原始輸出。
- Agent 查閱、修改與驗證的檔案。
- Diff、命令、環境、Exit Code 與產物。
- Oracle 結果、Rubric 結果、Blind Spot 與人工決策。

缺少 Token Telemetry 時填寫 `not available`，不得推估或以文字長度替代。

## RED、GREEN、REFACTOR 驗證流程

### RED

1. 先新增會因 `v0.1.0` 缺少新契約而失敗的結構測試。
2. 使用沒有 Skill 的 Fresh Agent 執行固定情境，保存定位錯誤、過度修改、盲點或停止失敗。
3. 對觸發描述與輸出契約執行無指示 Control，確認問題真實存在。

### GREEN

1. 只加入能修正已觀察失敗的 Skill 指示、Reference 與契約。
2. 執行相同情境，確認 Agent 行為與結構測試改善。
3. 執行現有回歸測試，確保 Authorization Gate、兩條路徑與原有輸出欄位仍存在。

### REFACTOR

1. 找出新出現的錯誤套用、規則跳過與輸出歧義。
2. 依失敗形狀選擇條件式規則、結構欄位或正向輸出 Recipe。
3. 移除重複與沒有改變決策的文字。
4. 重跑 Micro-eval、完整情境與 CI。

## CI 與驗證

`.github/workflows/validate.yml` 將執行：

1. Python Unit Tests。
2. Agent Skills 格式驗證。
3. Skill 入口長度、Reference 路由與 Metadata 一致性。
4. Eval Manifest Schema、固定 Commit 與必要 Rubric 欄位驗證。
5. Markdown 相對連結與 UTF-8 檢查。

CI 不直接宣稱 Agent 行為通過。需要模型執行的 Benchmark 在 Release 前獨立完成，結果與限制提交到 `evals/results/`。

## README 與公開採用

README 將保留目前尚未提交的 `.agents/skills` 安裝修改，並擴充：

1. 一句話價值與適用任務。
2. Clean Code、CLEAN、Repository Policy、可執行 Gate 與 Skill 的責任圖。
3. Project Skill 與 Personal Skill 安裝方式。
4. Codex、GitHub Copilot、Claude Code 等相容 Client 的路徑與已驗證狀態。
5. 三個可直接使用的 Prompt：規劃、實作與 Review。
6. Benchmark 方法、初始結果與限制。
7. 如何提交失敗情境、Fixture、Rubric 或平台相容性回報。
8. 非官方作品聲明、來源邊界與 MIT License。

未實際驗證的平台只能標示為「符合格式，尚未完成 Client 實測」。

## 版本策略

### `v0.2.0`

- 開放標準核心與 Codex Adapter。
- Clean Code 對 Agent Legibility 的作用機制。
- 三組對照 Benchmark 與初始結果。
- 結構、Manifest 與連結 CI。
- 跨平台安裝與貢獻文件。

### `v1.0.0` Gate

必須同時具備：

1. 結構與格式驗證全綠。
2. 四種固定情境每組至少五次結果。
3. 至少兩種 Agent Skills 相容 Client 完成實測。
4. 至少一項外部 Repository 或外部貢獻情境。
5. 發現限制、失敗案例與不適用條件皆有公開記錄。
6. 沒有依賴未公開資料才能重跑的主要宣稱。

## 風險與控制

| 風險 | 控制方式 |
| --- | --- |
| Skill 變成 Clean Code 百科全書 | 入口維持短小，Reference 只保留會改變決策的內容 |
| Agent 機械套用 Pattern | 每個方案都要說明 Repository 證據、成本與替代條件 |
| Benchmark 偏向 Skill 已知答案 | Oracle、Rubric 與任務固定；保留 Control；公開原始輸出 |
| 測試全綠被誤寫成行為可靠 | CI 與 Agent Benchmark 分開報告 |
| Token 節省被誇大 | Token 只作同品質候選的次要資料，缺資料就明確標示 |
| 平台相容宣稱過度 | 分開標示格式相容與實際 Client 驗證 |
| User 未提交 README 被覆蓋 | 以目前 Working Tree 內容作為實作基礎，修改前後逐段 Review |
| Public Skill 擴大修改權限 | Authorization Gate 永遠留在入口，Evidence 不能取代 Authority |

## 驗收條件

`v0.2.0` 完成時必須符合：

1. Skill 通過 Agent Skills 格式與既有結構測試。
2. 新增測試曾在實作前因缺少新契約而正確失敗。
3. `SKILL.md` 能正確路由七份 Reference，且維持 500 個英文單字以內。
4. Frontmatter、`openai.yaml`、README 與安裝路徑一致。
5. 四種情境、三組對照、指標與 Evidence Schema 可被第三方理解並重跑。
6. 初始 Benchmark 清楚分開結果、推論與限制。
7. README 說明 Clean Code 能改善哪些 Agent 能力，也說明反效果與不保證事項。
8. Repository 中沒有 Token、Secret、暫存輸出或不可公開的 Evidence。
9. 現有 README 未提交修改沒有遺失。
10. `v0.2.0` 尚未達到 `v1.0.0` Gate 時，不使用成熟或主流的保證式宣稱。

## 實作邊界

本次只修改 `Clean-Code-AI-Collaboration-Skill` Repository。`AI-CleanCode-API-Demo` 僅作公開、固定 Revision 的評測 Fixture；除非另行授權，不修改該 Repository。

設計規格 Commit 只包含本文件。Skill、Tests、CI、README 與 Eval Harness 的實作會在書面規格確認後開始，並保留不同責任的 Commit 邊界。
