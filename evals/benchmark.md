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

同一 Scenario 的 Repository URL、Commit SHA、任務、模型、Reasoning Effort、Client、工具權限與執行環境必須一致。唯一可改變的變因是對照組指示方式。Demo Repository 僅作唯讀 Fixture。

每組 Micro-eval 執行五次；每組完整 Repository Scenario 執行三次。缺少 Token Telemetry 時記錄 `not available`，不得推估或以文字長度替代。

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
