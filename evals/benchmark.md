# Public Benchmark Contract

## Purpose

本 Benchmark 以公開、唯讀的 `AI-CleanCode-API-Demo` 固定 Commit 作為 Fixture，記錄 `clean-code-ai-collaboration v0.2.0` 在指定條件下的觀察。它提供可重跑的契約，不宣稱任何結果可普遍化。

## Comparison Arms

每個情境使用三組對照：

1. `control`：只提供任務與 Repository 原有指示。
2. `generic-clean-code`：額外提供「請遵守 Clean Code 完成任務。」
3. `skill-v0.2.0`：明確載入 `clean-code-ai-collaboration v0.2.0`。

`v0.1.0` 可作版本回歸參考，但不混入這三組的主要比較。

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
