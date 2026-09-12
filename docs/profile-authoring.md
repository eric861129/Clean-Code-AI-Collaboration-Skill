# Profile Authoring Guide

本文件是新增與維護 Language／Framework Profile 的唯一貢獻入口。領域術語以 [CONTEXT.md](../CONTEXT.md) 為準；架構、不變量與驗收條件以 [Composable Language／Framework Profile Architecture SPEC](superpowers/specs/2026-09-04-composable-language-framework-profile-architecture-design.md) 為準。本文件不另建 Roadmap，也不重複列出 Schema 的全部欄位。

## 生命週期與原子變更

每個新 Profile 都必須先以 **Planned Metadata** 進入 `profiles/catalog.yaml`。Planned 只能描述身分、偵測候選、組合關係、Maintainer 與尚未開始的 Evidence；不得提供 `reference`，也不得被 Runtime Routing 或 Specialist Packaging 選用。

只有同一個變更同時完成下列項目，才能從 Planned 升為 **Experimental**：

1. 一份完整、原創且符合固定章節契約的 Reference。
2. Changed Module Routing 與狀態、組合、衝突的 Contract Tests。
3. 該技術棧最重要語意風險的 Semantic Tests。
4. 由 Generator 更新的 README Matrix 與 Runtime Profile Index。
5. Validator、Generated `--check` 與完整測試全部通過。

Experimental 只表示文件與 Contract Tests 已具備，不代表效果已由 M2 Pilot 證明。Beta、Stable 與 Deprecated 必須遵守 SPEC 的證據與相容性門檻；不得只改狀態文字來提高成熟度。

## Reference 固定章節

每份可用 Profile Reference 必須依下列順序保留 12 個英文 Headings。內容應補充技術棧特有判斷，不重述 Core 通用規則：

1. `## Use This Profile When`
2. `## Repository Facts to Inspect`
3. `## Version-Sensitive Facts`
4. `## Language or Framework Semantic Risks`
5. `## Clean Code Misapplications`
6. `## Behavior and Boundary Contracts`
7. `## Repository-Native Gate Discovery`
8. `## When Another Option Fits Better`
9. `## Common Agent Failure Modes`
10. `## Stop and Escalation Conditions`
11. `## Output Additions`
12. `## Evidence Status`

## Detection Ownership

Detection 必須區分能界定模組邊界的 Owner 與只能補強判斷的 Supporting Fact：

- **Owning Manifests**：從 Changed File 向上找到最近的 Project、Package 或 Workspace Manifest，負責界定 Changed Module。
- **Supporting Files**：例如 Solution、共用設定或版本檔，只能補強判斷，不能成為 Owner。
- **Candidate Dependencies**：Metadata 的 `dependency_markers`，可在已確定的 Changed Module 內提出 Framework Candidate。
- **Supporting Dependencies**：只能確認 Renderer、工具鏈或相鄰能力，不能單獨啟用 Profile。

新增 Pattern 前，先提供正例、反例、同距離 Tie-break 與 Monorepo 邊界測試。不得把 Repository Root 的檔案、任意顯示文字或 Supporting Fact 當成 Owning Manifest。

## Composition and Conflict

`requires` 是封裝與套用前必須傳遞式成立的硬相依；`recommends` 只提供建議，不能自動加入；`conflicts` 必須對稱。Unknown ID、Self／Cycle、不可用 Requirement 或 Conflict 都要 Fail Closed。Bundled 只代表可選，仍須依 Changed Module 判斷 Applicability；Explicit Profile 也不能繞過 Availability、Applicability、Conflict、Repository Gate 或授權邊界。

## Ownership and Maintainer

`ownership.maintainers` 至少要有一位可追蹤的 **Maintainer**。Maintainer 負責 Metadata、Reference、測試與 Evidence 的一致性，但不能單方面略過 Reviewer、CI 或 Release 授權。變更 Detection、Composition 或輸出契約時，Reviewer 應能從同一個 Diff 看出原因、風險與相容性影響。

## Evidence Outcome

Evidence Result 的四種 Outcome 必須全部保留：`passed`、`failed`、`no_difference`、`inconclusive`。不得移除不利結果、把 Infrastructure 或觀察限制改寫成成功，也不得用另一個 Profile 或舊版本結果代替本 Profile 的 Pilot／Full Run。`benchmark_status` 只能反映已有 Manifest、Result、SHA-256 與公開狀態支持的階段。

每筆 Metadata Evidence 都必須指向通過 Public Result Schema 驗證的公開結果，保存正確的 `stage`、`outcome`、Repository-relative Path、實際檔案 SHA-256 與 `public` 狀態。Validator 必須用 Public Result 的 `profile_id`、`stage` 與 `outcome` 反向核對 Metadata，不能只相信 YAML 宣告。`pilot_recorded` 表示 Pilot 證據已完整保存，不等於 Outcome 為 `passed`，也不必然等於 `beta`；只有實際 Outcome `passed` 才能把 Experimental Profile 升為 Beta。

## Suite SemVer and Profile Maturity

同一 Profile 的不同 Campaign Evidence 必須追加保存，不能覆蓋原有 Result 或 Outcome。結果 Schema 僅接受 Repository 白名單中的 `profile-pilot-result/v1` 與 `profile-pilot-result/v2`，Package Input Hash 應包含實際使用的 Schema。v2 另保存 `execution_commit`、執行輸入 Hash、查閱診斷與 Oracle 未執行原因；詳細執行契約見 [Benchmark](../evals/benchmark.md)。

v0.5.2 Campaign 受測來源固定為已發布 Skill v0.5.1，不是 Candidate 的持續修改內容。Suite Metadata 更新不代表重新測過不同的 Profile 語意；Canary 只驗證協定，不參與成熟度判定。未完成正式發布前，安裝命令保持指向已發布 Tag。

**Suite SemVer** 與 Profile Maturity 分開管理：

- 純相容修正、錯字或不改變選擇契約的澄清使用 Patch。
- 新增相容 Profile、Detection 或 Selection 能力使用 Minor。
- 破壞 Profile ID、Schema、Composition、Selection 或 Output Contract 使用 Major。

`planned`、`experimental`、`beta`、`stable`、`deprecated` 描述的是證據成熟度，不由 Suite 版本數字自動推導。Deprecated 必須提供原因；若有 Replacement 或 Removal Version，也要能由 Validator 驗證。

## Originality and Attribution

Reference 必須是維護者的原創整理。若不可避免地使用第三方規格、範例或相容內容，必須保留必要 License 與 **Attribution**，並確認可再散布。不得重製書籍、付費課程、第三方文章或其他 Skill 的大段內容；引用只保留支持技術判斷所需的最小範圍。

## Validator and Generator

先執行 Profile Validator，再確認 Generated Region 沒有漂移：

```powershell
python scripts/validate_profiles.py --source-root .
python scripts/generate_profile_matrix.py --source-root . --check
python -m unittest discover -s tests -v
```

需要更新 Generated Region 時，先執行不含 `--check` 的 Generator，審查實際 Diff，再重跑 `--check`。不得手改 Marker 內的 README Matrix 或 Runtime Profile Index。Consumer Runtime 讀取產生後的 Markdown Index，不要求 Consumer 解析 YAML。

## Packaging and Release Boundary

本機 Specialist Package 可用下列命令建立；Release Mode 要求乾淨工作樹，並從 `HEAD` Git Blob 讀取所有輸入：

```powershell
python scripts/build_skill_package.py --source-root . --output dist/clean-code-ai-csharp --source-mode release --profile csharp
agentskills validate dist/clean-code-ai-csharp
```

Output Directory 必須不存在，Packager 不會覆寫既有內容。Package 只展開 `requires`，不自動加入 `recommends`。`dist/` 是本機 Git-ignored 產物；建立 Package 不等於已發布。**Package／Push／Release 需要額外授權**，也不得因完成 M1 文件與 Contract Tests 就開始 M2 Pilot 或 M3 Promotion。

## Reviewer Checklist

- [ ] Catalog 順序、ID、Kind、Suite Version 與 Maintainer 正確。
- [ ] Planned 沒有 Reference、Routing 或 Packaging；升 Experimental 的變更具原子性。
- [ ] 12 個 Headings 完整，內容聚焦技術棧語意且沒有重複 Core。
- [ ] Owning Manifests 與 Supporting Files／Dependencies 沒有混用。
- [ ] `requires`、`recommends`、`conflicts` 的方向、循環與對稱性有測試。
- [ ] Evidence 的成功、失敗、無差異與不確定結果都保留，沒有誇大結論。
- [ ] Originality、License 與 Attribution 可追溯。
- [ ] Validator、Generator `--check`、完整測試、Compile 與 Open Standard Validation 通過。
- [ ] Specialist Package 可重算 Manifest，沒有時間戳、絕對路徑或 OS 依賴。
- [ ] 未把本機 Package、Local Gate 或文件完成誤報成 CI、Pilot、Push 或 Release。
