# Public Benchmark Contract

## Purpose

本 Benchmark 保存不同版本、不同目的的公開評測。`v0.2.0` 使用公開、唯讀的 `AI-CleanCode-API-Demo` 固定 Commit 觀察 Repository 任務；`v0.4.0` 則以小型決策案例驗證開發節奏與驗證範圍的策略契約。兩者都提供可重跑的契約，不宣稱結果可普遍化，也不能彼此替代。

## Comparison Arms

每個情境使用三組對照：

1. `control`：只提供任務與 Repository 原有指示。
2. `generic-clean-code`：額外提供「請遵守 Clean Code 完成任務。」
3. `skill-v0.2.0`：明確載入 `clean-code-ai-collaboration v0.2.0`。

`v0.1.0` 可作版本回歸參考，但不混入這三組的主要比較。

本節描述的是 `v0.2.0` Repository 評測；`v0.4.0` 的比較組與結果另列於後文。

## Fixed Variables

同一 Scenario 的 Repository URL、Commit SHA、任務、模型、Reasoning Effort、Client、工具權限與 Subject 執行環境必須一致。Subject 階段唯一刻意改變的變因是對照組指示方式；Evaluator Procedure 的已知差異另列於限制。Demo Repository 僅作唯讀 Fixture。

Micro-eval 的每組對照各執行五個情境；每組完整 Repository Scenario 執行三次。缺少 Token Telemetry 時記錄 `not available`，不得推估或以文字長度替代。

## Execution Order

1. 依 `manifest.json` checkout 指定 Commit，確認工作目錄狀態並建立 Run ID。
2. 以固定 Prompt 與執行條件分別跑三組對照，逐次保存原始輸出、查閱檔案、修改檔案、命令、環境、Exit Code、產物與 Diff。
3. 執行 Scenario 指定 Oracle Commands，記錄結果與未執行項目。
4. 依三份 Rubric 進行人工評分，記錄 Blind Spots、授權問題與 Human Decisions Required。
5. 只有已通過相同行為與品質 Gate 的候選，才可比較 Token、Tool Call、經過時間與生成行數。

## Multi-Dimensional Report

每次結果必須分別報告任務正確性、Context 定位、修改局部性、行為穩定性、驗證品質、決策品質與執行成本。不得把這些維度壓成單一總分。

每筆結果必須在同一筆 Evidence 中完整填入 `manifest.json` 的 `result_required_fields`，包括模型、Reasoning Effort、Client、工具權限、完整 Prompt、Diff、命令、Exit Code 與 Blind Spots，讓每個 Fresh Context 的條件可稽核。結果只支持該記錄條件下的觀察；不得據此保證 Skill 效果、品質、成本節省或外部採用狀態。

## Contract Boundaries

公開契約、外部副作用、Gold Behavior、取消、儲存、Retry 與 Lost ACK 必須依 Scenario 的 `must_preserve` 與 Rubric 檢查。未授權變更公開契約、未執行卻宣稱通過、遺失外部副作用或破壞 Gold Behavior 均為 Automatic Failure。

## Semantic Diff Boundary

修改範圍不以單一預測檔名判定。每個 Scenario 同時保留精確的 `allowed_diff`，以及針對 Provider、Contract Test、Coordinator、Registry 等責任角色的 `allowed_diff_patterns`。Pattern 使用大小寫敏感的 Python `re.fullmatch`，只接受 Repository-relative POSIX path；重新命名時，來源與目的路徑都必須通過。

每筆 Result 都要保存 exact list、Pattern snapshot、逐路徑放行依據與真正越界的路徑。Pattern 通過只表示修改仍在任務外圍，不能取代人工檢查 Diff、Repository 事實與責任歸屬。`scripts/`、共用 HTTP Contract 或無關架構層不會因檔名看起來相似而自動獲准。

早期 v0.1 Baseline 曾以固定檔名誤判合理的 Provider Contract Test 與競態協調類別。`rescoring_history` 保留舊邊界、舊分數與重評原因；原始 Diff、雜湊、Oracle、Automatic Failure 與比較資格不因這次契約修正而改寫。

## v0.4.0 Strategy Decision-Conformance Full Run

完整機器可讀結果存放於 [`results/v0.4.0-strategy-full-run.json`](results/v0.4.0-strategy-full-run.json)。這輪評測回答一個窄而重要的問題：Controller 分派 Subject 載入 Skill 後，能不能穩定判斷使用者要求的開發節奏與驗證範圍，並在前提不足時停止，不自行換成另一種做法？公開收據可重播 Prompt、輸出與決策 Oracle，但無法獨立認證 Subject 的 Context 或服務端模型身分。

評測包含 9 種決策情境：Prompt 覆寫 Repository Policy、由 Repository Policy 提供預設值、`auto` 選擇直接修改或特性測試、明確 TDD 搭配 E2E、TCR 具備完整條件、缺少版本控制授權、缺少快速測試回饋或隔離工作樹，以及缺少變異測試工具。每個 Skill 情境重複兩次，因此共有 18 組 Full Run；另有 9 組無 Skill 對照，各執行一次。

### Observed

- 9 組無 Skill 對照有 5／9 符合預先固定的決策契約；偏差出現在 `auto` 的來源歸屬、驗證設定名稱，以及阻擋後是否提出最近的可行替代方案。
- v0.4.0 Skill 的 18／18 次執行全部通過，且都保留 Repository 必要 Gate，沒有把使用者明確但不可執行的選項偷偷換掉。
- 阻擋案例實際涵蓋測試回饋速度、隔離工作樹、版本控制授權，以及 Mutation 工具／安裝授權；`reliable-test-oracle` 雖屬正式前置條件 ID，本輪沒有獨立情境，因此不能把結果擴張成所有阻擋前提都已驗證。
- 開發期間的早期 Run 曾發現「Prompt 明寫 `auto`」的來源定義不夠清楚，後續獨立 Review 又找出收據重播與 TCR 前提覆蓋不足。這些調校記錄目前只保留在本機 Benchmark Workspace，沒有納入公開 Result；公開 Checkout 能驗證的是最終 Skill Run、無 Skill 對照的偏差，以及其中內嵌的收據，不能回放早期 Generation。

### Claim Boundary

這輪 Full Run 只驗證策略決策契約是否被一致解讀。它不衡量程式碼品質、不比較實際 Diff，也不宣稱節省 Token、時間或費用；9 組小型案例也不能推論所有語言、模型、Client 與 Repository 都會得到相同結果。

公開 Result 內嵌每次執行的固定 Prompt、Controller Dispatch、原始 Subject JSON 與重播後 Terminal，並保存 Manifest、Harness 與 Skill 快照雜湊。乾淨 Checkout 可執行 `py -3 -m evals.v040_strategy_full_run verify-result`，重新比對固定情境與每一筆決策。`model` 與 `reasoning_effort` 是 Controller 啟動 Subject 時的要求值，不是第三方簽章；公開收據無法獨立證明服務端實際模型身分。

`v0.3.0` 的跨語言程式碼 Benchmark 是另一條證據線，Full Run 尚未完成，也不納入 v0.4.0 的結果。補齊公開 Result 與收據前，不用本機進度數字替代可稽核的發布證據。

## v0.5.1 Profile Pilot M2

M2 使用 [`v0.5.1-profile-pilot.json`](manifests/v0.5.1-profile-pilot.json) 固定 C#、Python、TypeScript 與 React 的八個 Scenario、34 個單次執行 Slot、`gpt-5.6-sol`／`high`、公開 Fixture `profile-pilot-v1`，以及已發布的 Skill `v0.5.0`。第一個 Subject Stage 前必須先建立 `pre_execution` Freeze；Manifest、Harness、Fixture、Evaluator、Prompt、Skill 或 Rubric 任一 Hash 漂移，都會使既有 Freeze 失效，不能只重跑結果較弱的 Arm。

Language Profile 只比較 `core-only` 與對應的 Core + Language Treatment。React Profile 採階梯式歸因，只比較 `core-plus-typescript` 與 `core-plus-typescript-plus-react`；`control` 與 `generic-clean-code` 不參與成熟度 Outcome。匿名 Reviewer 依 [`profile-increment.md`](rubrics/profile-increment.md) 對單一 Candidate 的固定 Criteria 評分，不得看到 Arm Mapping 或比較其他 Candidate。

四個 Profile Outcome 只能由完整 Terminal State、匿名 Review 與固定直接比較組重算為 `passed`、`failed`、`no_difference` 或 `inconclusive`。Pilot 尚未產生公開 Result 前，這一節只描述事前契約，不代表 Profile 已通過，也不改變 `v0.5.0` 的正式發布狀態。

## Initial v0.2.0 Results

完整機器可讀結果存放於 [`results/v0.2.0-initial.json`](results/v0.2.0-initial.json)。以下結論刻意區分實際觀察、推論、未知與失敗，避免把單一模型、單一 Repository 的初步結果寫成普遍保證。

### Observed

- 12 次 Skill Repository Run 都通過獨立 Evaluator 執行的完整測試與格式 Oracle，沒有出現公開契約漂移、外部副作用遺失或 Gold Behavior 破壞，因此 Automatic Failure 為 0。
- 9 次 Run 完全落在事前固定的 Semantic Diff Boundary。3 次並行案例各新增一個與競態責任直接相關的類別，但檔名沒有通過預先宣告的 Pattern；這三次的 `Context and Locality` 只記為部分支持，不事後放寬規則。
- `behavior-validation` 的 3 次 Run 都辨識出 Prompt 與 Repository Retry 契約衝突，只補不衝突的驗收測試，並把通知去重與冪等決策交還 Owner。
- `dependency-boundary` 的 3 次 Run 都找到既有的 Consumer Port，沒有新增同義介面或另一套 Production 架構，只補跨 Provider Contract Test。
- `concurrency-side-effects` 的 3 次 Run 都先重現 HTTP 與 Background Worker 的同 Process 競態，再實作 Process-local 保護；三次都明確拒絕把這份證據宣稱成跨 Process 保證。
- 與固定的 `generic-clean-code` Baseline 相比，完整支持的 Run 數從 `6/12` 提升到 `9/12`（Context and Locality）、從 `7/12` 提升到 `12/12`（Behavior and Validation）、從 `1/12` 提升到 `12/12`（Decision and Escalation）。這些是分維度結果，不是總分。
- 15 份 Micro-eval 輸出都被人工判為適合該任務。Skill Arm 的 5 個情境皆正確啟用，並依風險選擇 Lightweight 或 Full Path；但 Control 與 Generic Arm 的輸出也很強，因此 Micro-eval 沒有建立一般性的回答品質優勢。

### Inference

- 初步證據最支持的價值，是 Skill 讓 Agent 更穩定地辨識 Repository 契約、停止條件與需要交還人類的決策，尤其是在 Prompt 與既有行為衝突時。
- Context and Locality 有改善，但三個並行類別名稱揭露了 Benchmark Pattern 仍可能漏接語意相關的實作。這既是候選的範圍訊號，也是評測工具需要持續校準的限制。
- 目前不能把改善歸因為「Clean Code 讓模型更聰明」。較保守的說法是：結構化的 Repository 情境、行為 Gate、設計邊界與可稽核輸出，讓相同 Agent 比較不容易在未知處自行補答案。

### Unknown

- 結果是否能轉移到其他模型、Reasoning Effort、Client、語言、Repository 規模與部署拓樸。
- Token 與 Tool Call Telemetry 無法取得，因此沒有成本、速度或 Token 節省結論。
- 三份並行候選只驗證單一 Process；資料庫 Claim、Outbox 或 Provider Idempotency 所需的跨 Process 保證尚未測試。

### Failure and Limitation

- Micro-eval 沒有呈現 Skill 相對 Control／Generic Arm 的分數優勢，只證明路由與參考資料選擇符合預期。
- 事前固定的 Diff Pattern 漏掉三個任務相關的並行類別名稱。結果保留這三筆偏差，沒有在看到輸出後修改規則美化數字。
- 部分 Fresh Fixture 的 Subject-side `dotnet test` 曾先因 Restore 或 Runner 環境失敗；修復執行環境後，獨立 Evaluator 的固定 Test 與 Format Oracle 全部通過。這只能證明最終候選，不應改寫成每一步都成功。
- v0.1 Baseline 的 Oracle 是在 Testhost Cache 修復後依序執行；v0.2 Skill Arm 改由 Subject 結束後的獨立 Root Evaluator 執行。命令與固定 Commit 相同，但 Evaluator Procedure 並非完全相同，因此比較結果仍可能包含 Harness 差異。
- 6 筆 Subject Report 沒有保存完整 `files_inspected`。公開結果只依 Subject 的 `repository_facts` 回補其確實引用的 Manifest Gold Files，並以 `files_inspected_complete=false` 標記為已知下限，不把它冒充完整查閱清單。

## External Validity Expansion Matrix

這張表區分目前公開 Evidence 與後續研究方向。沒有 Result 的項目不得寫成已驗證，也不得由格式相容推論成行為相容。

| Dimension | Status | Evidence or next gate |
| --- | --- | --- |
| public .NET Demo | 已驗證 | 固定 Repository、模型、Client 與明確載入條件；見 [v0.2.0 initial result](results/v0.2.0-initial.json) |
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
