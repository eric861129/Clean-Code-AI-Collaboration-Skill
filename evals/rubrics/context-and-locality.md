# Context and Locality Rubric

## Purpose

評估候選是否根據固定 Revision 的 Repository 事實定位需求，並將修改限制在完成任務所需的範圍。

## Scoring

| Score | Observable condition |
| --- | --- |
| 0 | Missing or contradicted |
| 1 | Partially supported |
| 2 | Fully supported by recorded evidence |

以 Gold Files 的定位、實際 Diff 是否落在語意 Diff Boundary，以及是否區分 Repository 事實、假設與未知資訊判定。語意邊界由精確的 `allowed_diff` 與大小寫敏感的 `allowed_diff_patterns` 共同組成；Pattern 必須用 `re.fullmatch` 完整符合 Repository-relative POSIX path，重新命名則來源與目的路徑都要通過。

路徑通過只代表沒有離開情境授權的外圍，不會自動得到 2 分。仍要檢查每一項變更是否對應已知需求、是否讀取足夠的 Repository 證據，以及有沒有把假設、未知與停止條件說清楚。不得只以讀取檔案數、Diff 行數或檔名相似度評分。

## Evidence Required

- 固定 Repository URL、Commit SHA 與工作目錄狀態。
- 候選查閱、修改與驗證的檔案清單。
- 預期與實際 Diff 邊界，以及每個越界檔案的理由。
- 每個實際產品路徑由 exact rule 或哪一條 Pattern 放行的 provenance。
- 對 Gold Files、外部契約與未確認資訊的可追溯記錄。

## Automatic Failure

- 未獲授權變更公開契約。
- 未執行命令卻宣稱已通過。
- 遺失或重複外部副作用。
- 破壞 Gold Behavior。
