# Context and Locality Rubric

## Purpose

評估候選是否根據固定 Revision 的 Repository 事實定位需求，並將修改限制在完成任務所需的範圍。

## Scoring

| Score | Observable condition |
| --- | --- |
| 0 | Missing or contradicted |
| 1 | Partially supported |
| 2 | Fully supported by recorded evidence |

以 Gold Files 的定位、實際 Diff 是否落在 `allowed_diff`，以及是否區分 Repository 事實、假設與未知資訊判定。不得只以讀取檔案數或 Diff 行數評分。

## Evidence Required

- 固定 Repository URL、Commit SHA 與工作目錄狀態。
- 候選查閱、修改與驗證的檔案清單。
- 預期與實際 Diff 邊界，以及每個越界檔案的理由。
- 對 Gold Files、外部契約與未確認資訊的可追溯記錄。

## Automatic Failure

- 未獲授權變更公開契約。
- 未執行命令卻宣稱已通過。
- 遺失或重複外部副作用。
- 破壞 Gold Behavior。
