# Profile Increment Rubric

## Purpose

對一個匿名 single candidate 的 `incremental_criteria` 逐項評分。Reviewer 只能依 Review Packet 中的 Task、Must Preserve、Diff、Oracle、Automatic Failure 與 Blind Spots 作成判斷；不得推測 Arm，也不得比較其他 Candidate。

## Scoring

| Score | Observable condition |
| --- | --- |
| 0 | Diff 或 Oracle 明確違反 Criterion，或證據顯示行為不存在。 |
| 1 | 有部分可觀察支持，但關鍵分支、保留行為或驗證仍有缺口。 |
| 2 | Diff 與 Oracle 完整支持 Criterion，且沒有相反證據。 |

每個 Criterion 都必須保存 `score` 與非空白 `reason`。Reason 必須指出可觀察的 Diff、Oracle、Repository Fact 或 Subject Report 證據；只寫「看起來正確」、引用 Profile 名稱或猜測使用了哪個 Skill，不算有效證據。

## Evidence Required

- 每一項 Criterion 的 `score` 與非空白 `reason`。
- Reason 必須連結 Review Packet 中可觀察的 Diff、Oracle、Repository Fact 或 Subject Report 證據。
- 證據不足時必須明列缺口，不得用 Profile 名稱、Skill 猜測或主觀印象補足。

## Blind Review Boundary

- 每次只評一個 Candidate，不得比較、排序或計算總分。
- 不得尋找或推測 Arm、Run ID、執行順序、私有 Mapping、Agent 或 Thread 身分。
- 不得在解盲後新增、刪除、改寫 Criterion 或分數門檻。
- 缺少完成判斷所需的 Diff、Oracle 或行為證據時，保留證據缺口；Controller 會將對應 Profile Outcome 判為 `inconclusive`。
- 通用三份 Rubric 與 `incremental_criteria` 分開評分，不得以其中一組分數代替另一組。

## Automatic Failure

Automatic Failure 由 Harness 依既有固定契約判定。Reviewer 不覆寫該狀態；仍需如實評分可觀察 Criterion，並在 reason 說明受到哪些失敗或 Blind Spot 限制。
