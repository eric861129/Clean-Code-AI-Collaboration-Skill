# Behavior and Validation Rubric

## Purpose

評估候選是否保留指定行為邊界，並以獨立 Oracle、回歸與靜態檢查驗證成功、失敗與副作用情境。

## Scoring

| Score | Observable condition |
| --- | --- |
| 0 | Missing or contradicted |
| 1 | Partially supported |
| 2 | Fully supported by recorded evidence |

以 Oracle 結果、失敗語意、取消、儲存、Retry、Lost ACK 與副作用行為的證據判定。全綠測試本身不足以證明所有行為已受驗證。

## Evidence Required

- 每個 Oracle Command 的命令、環境、Exit Code 與產物。
- 初始失敗、回歸、靜態檢查與未執行項目的紀錄。
- HTTP、資料、通知、取消、儲存與並行行為的保留證據。
- 已知 Blind Spots 與仍需人工判定的事項。

## Automatic Failure

- 未獲授權變更公開契約。
- 未執行命令卻宣稱已通過。
- 遺失或重複外部副作用。
- 破壞 Gold Behavior。
