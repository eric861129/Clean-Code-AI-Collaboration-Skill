# Clean Code AI Collaboration Skill v0.3.0 設計規格

## 文件狀態

- 日期：2026-08-31
- 狀態：聊天室設計已核准，等待書面規格確認
- 目標版本：`v0.3.0`
- 目前版本：`v0.2.0`
- Repository：`Clean-Code-AI-Collaboration-Skill`

## 背景

`v0.2.0` 已具備 Lightweight 與 Full 兩條路徑、完整的 Review Output Contract、Codex Adapter，以及固定條件下的 Repository Benchmark。它能在高風險任務保留事實、假設、未知、選項、驗證與人工決策的追蹤關係。

目前設計仍有三項實務限制：

1. Full Path 要求每個 Heading、空白調查結果與 `F1/A1/U1/O1/E1` 識別碼，中型修改容易產生超過決策需要的報告。
2. Skill 的觸發描述涵蓋大量 Coding 工作，Codex Adapter 又允許 implicit invocation，但公開評測只驗證明確呼叫，尚未證明自動觸發的準確率。
3. Benchmark 已清楚限制結論只能套用於固定模型、Client、Repository 與情境；下一步需要可追蹤的外部效度擴充順序，而不是擴大宣稱。

`v0.3.0` 的重點是降低一般任務的流程成本、收斂觸發範圍，並為後續跨 Repository 驗證建立誠實的擴充矩陣。這個版本不以增加更多 Clean Code 規則為目標。

## 目標

1. 將任務路徑調整為 Lightweight、Standard 與 Full Audit 三層。
2. 讓 Standard 成為一般 Repository 修改的主要路徑，不強迫輸出空白段落或追蹤識別碼。
3. 保留 Full Audit 的完整可追溯性，不因降低一般任務成本而削弱高風險審查。
4. 在 implicit invocation 尚未通過觸發評測前，將 Codex Adapter 改為明確呼叫。
5. 補上清楚的不適用情境，避免概念問答、獨立範例與純格式工作誤用本 Skill。
6. 在既有 Benchmark 文件內建立外部效度擴充矩陣，分開標示已驗證、規劃中與尚未支持。
7. 區分 Prototype 與 Production-Ready 的交付成熟度，但不讓開發階段覆蓋風險、授權與行為 Gate。
8. 將 Repository 既有的 Formatter、Linter、Static Analysis、Build、Test 與其他可執行 Gate 接入驗證閉環。

## 非目標

1. 不在 `v0.3.0` 完成所有語言、模型、Client 與真實團隊的外部評測。
2. 不因新增 Standard Path 而刪除 Full Audit 的 Heading、空白調查規則或穩定識別碼。
3. 不建立第二份 Benchmark Roadmap；擴充範圍仍由 `evals/benchmark.md` 維護。
4. 不以輸出字數、Token、Tool Call 或執行時間單獨判定路徑品質。
5. 不把明確呼叫改寫成永久限制；implicit invocation 可在觸發準確率有證據後重新評估。
6. 不新增跨語言或跨模型結果檔，也不把規劃中的評測寫成已觀察證據。
7. 不把 Prototype 當成跳過安全、資料、外部副作用或授權限制的理由。
8. 不要求所有 Repository 安裝同一套 Linter、SonarQube、TDD 或其他工具；優先使用專案既有且與風險相關的 Gate。

## 三層路徑設計

路徑依風險由高到低判斷。只要命中 Full Audit 條件，就不能因期待簡短輸出而降級；未命中 Full Audit、但工作超出局部可逆的可讀性修改時，使用 Standard。只有所有條件都屬低風險時，才使用 Lightweight。

| 路徑 | 適用條件 | 調查深度 | 輸出方式 |
| --- | --- | --- | --- |
| Lightweight | 局部、可逆的命名、註解、格式或可讀性修改；沒有行為、公開契約、資料、副作用、依賴、權責或部署影響；只有一個明顯選項 | 確認必要 Repository 事實、行為邊界與最小驗證 | 簡短回報事實、修改、原因、驗證與必要的人工作業；不適用項目省略 |
| Standard | 已知邊界內的一般功能、測試、缺陷修正、重構或內部設計調整；Owner、授權與驗證方式已知；風險可由現有 Gate 控制 | 調查會改變選擇的事實、可行方案、行為與 Diff 邊界 | 使用精簡固定順序，只保留本次有內容或會影響決策的欄位；不要求穩定識別碼 |
| Full Audit | 公開契約、正式資料或 Migration、外部副作用、第三方依賴變更、並行、安全性、權限、CI、基礎設施、部署、破壞性操作、權責不明、重大取捨、正式稽核或關鍵未知 | 完整建立 Repository Context、選項、授權、行為、驗證與停止條件 | 保留所有 Heading、`F1/A1/U1/O1/E1` 與空白調查結果的來源說明 |

「內部依賴調整」只有在不新增或替換第三方套件、不改公開契約，而且既有架構與 Owner 足以判斷時，才可留在 Standard。外部 Provider、套件版本、依賴方向或部署行為可能改變時，使用 Full Audit。

### Standard 不是 Full Audit 的摘要模式

Standard 與 Full Audit 的差異不只是篇幅。Standard 針對已知邊界內的修改蒐集決策必要資訊；Full Audit 則為高風險或正式 Review 建立可逐項追溯的調查紀錄。

若先執行 Standard，過程中發現公開契約、資料、副作用、授權衝突或關鍵未知，必須升級成 Full Audit。路徑只能因新證據升級，不能為了縮短報告而降級。

## 交付成熟度與風險路徑分開判斷

Prototype 與 Production-Ready 不是第四、第五條路徑。三層路徑決定風險、調查深度與輸出契約；交付成熟度則說明這份成果準備被怎麼使用，以及需要通過哪些 Gate。兩者分開後，Prototype 可以保持敏捷，卻不能用「只是實驗」規避正式資料、外部副作用或安全限制。

| 交付成熟度 | 適用條件 | Clean Code 期待 | 最低交付說明 |
| --- | --- | --- | --- |
| Prototype | 用來回答可行性、介面或設計問題；環境隔離、結果可丟棄、不承諾正式使用 | 名稱與責任足以讓實驗可理解；只建立回答問題所需的結構，避免提前抽象化 | 說明實驗問題、可執行 Oracle、可丟棄範圍、未達 Production-Ready 的 Gate 與下一步 |
| Production-Ready | 準備合併、發布、部署，或成為後續正式維護基礎 | 遵守 Repository Policy、行為契約、依賴邊界與維護性要求；完成與風險相稱的驗證 | 說明實際 Diff、完整相關 Gate、Blind Spot、部署／UAT 邊界及仍需人類承諾的事項 |

「Prototype」不等於髒亂 Code，也不等於必須補齊正式架構。它應保持足以重現與判斷的清楚程度，並明確標示不可直接當成正式成果。若 Prototype 需要連接正式 Provider、處理真實資料、改變公開契約或測試安全邊界，仍依風險選擇 Full Audit 並取得授權。

額外抽象與 Token 成本通常來自機械套用 Pattern，不是 Clean Code 要求抽象越多越好。Skill 必須檢查抽象是否保護真實變更來源；若只是增加跳轉、Mapping 或同步點，應保留較簡單結構或停止重構。

## 輸出契約

`review-output-contract.md` 保持唯一輸出契約來源，不新增另一份 Standard 文件。內容分成 Standard Output Contract 與 Full Audit Output Contract，避免兩份文件日後出現欄位漂移。

### Standard Output Contract

輸出依下列順序組成；只有前四項必須出現，其餘項目只在確實影響決策時加入：

1. **Outcome and Status**：先說結果、目前狀態，以及已涵蓋的行為與 Diff 範圍。
2. **Decision Basis**：列出真正改變選擇的 Repository 事實；假設或未知會影響結論時才列出。
3. **Selected Approach**：說明選擇與原因；存在合理替代方案時，補充其適用條件。
4. **Behavior, Diff, and Validation**：交代不可漂移的行為、預期與實際修改範圍、已執行驗證及盲點。
5. **Stop or Human Decision**：只有遇到停止條件、未授權範圍或需要 Owner 決策時才出現。

Standard 不使用裸露的 `None`，也不要求 `None; Sources checked: ...`、`Not investigated` 或穩定識別碼。省略欄位表示它不影響本次決策，不得用省略隱藏已知風險或未完成的必要調查。

### Full Audit Output Contract

Full Audit 延續 `v0.2.0` 契約：

- 每個 Heading 都必須出現。
- 使用 `F1/A1/U1/O1/E1` 連結事實、假設、未知、選項與 Evidence。
- 沒有適用項目時，只有在具名來源完成調查後才可填寫 `None; Sources checked: ...`。
- 未完成相關調查時填寫 `Not investigated`。
- 結果必須區分已執行 Evidence、規劃中的驗證、Blind Spot、授權邊界與 Human Decisions Required。

## 驗證工具鏈閉環

Prompt 與 Skill 負責情境、選擇、停止條件與主張邊界；能被機械判斷的品質條件交給 Repository 工具。Agent 先盤點既有工具，再依任務風險選擇相關 Gate，不因工具名稱流行就安裝新依賴。

```text
Repository facts and policy
        ↓
Implementation or review
        ↓
Relevant executable gates
        ↓
Evidence and blind spots
        ↓
Human decision or safe continuation
```

可用 Gate 包含 Formatter、Linter、Static Analysis、Build、Unit／Integration／Contract／E2E Test、Architecture Test、Dependency／Security Scan、Coverage 與 Mutation Test。SonarQube、ESLint 或特定框架只是實例，實際命令以 Repository 現況為準。

選擇規則如下：

- 先使用 Repository 已存在、能觀察本次風險的 Gate；不要只跑最容易變綠的命令。
- Prototype 至少要有能回答實驗問題的可執行 Oracle，並列出尚未通過的正式 Gate。
- Production-Ready 必須執行 Repository 要求且與修改相關的格式、靜態檢查、Build、Test 與發布前 Gate；未執行項目列為 Blind Spot。
- TDD 適合新規則、缺陷、邊界值或狀態轉換能先寫成有意義 Red Test 的情境；未知 Legacy 行為優先 Characterization Test，跨邊界結果使用 Acceptance／E2E，測試品質疑慮才考慮 Mutation Test。
- 沒有可靠 Oracle 時，Linter、Coverage 或全綠測試不能替需求正確性背書。
- 新增工具、修改 CI、下載付費服務、變更依賴或擴大掃描範圍前，必須取得相應授權。
- Evidence 記錄實際命令、環境、Exit Code、結果與限制；計畫執行的 Gate 不能寫成已通過。

這個閉環降低軟性規則被忽略的機率，但不保證工具本身的規則正確。Repository Owner 仍需決定品質門檻、例外與風險接受。

## 觸發與不適用情境

### Frontmatter Description

Description 改成只描述觸發條件，不列舉 Skill 的完整工作流程。建議語意為：

> Use when repository changes require contextual trade-offs about behavior preservation, test adequacy, change locality, dependency boundaries, side effects, or review evidence.

這個描述聚焦在「需要 Repository-aware 取捨」的症狀，不用 Plan、Implement、Refactor、Review、Handoff 與 Estimate 的工作種類清單吸引所有 Coding 任務。

### 不適用情境

`SKILL.md` 必須明確說明以下任務不應啟用：

- 純語法、單一 API 用法或不涉及 Repository 的概念解釋。
- 單純產生獨立範例、教學片段或一次性示意程式碼。
- 只有格式調整，而且專案既有 Formatter 已完整定義結果。
- 已被更專門 Skill 完整涵蓋，且沒有額外的行為、邊界、副作用或 Clean Code 取捨。

若專門 Skill 只負責技術操作，而任務仍有跨邊界的品質與行為取捨，兩者可以併用；本 Skill 不得取代更專門 Skill 的領域契約。

### Codex Adapter

`agents/openai.yaml` 改為：

```yaml
policy:
  allow_implicit_invocation: false
```

README 將明確呼叫列為 `v0.3.0` 的正式使用方式，不再同時保留「允許自動觸發」與「尚未驗證 implicit invocation」的張力。重新開啟 implicit invocation 前，必須先有包含正例與反例的觸發評測，至少報告誤觸、漏觸與額外輸出成本。

## Benchmark 外部效度擴充

既有 `evals/benchmark.md` 繼續作為唯一 Benchmark 方法與限制來源。新增擴充矩陣時，每個維度都標示 `已驗證`、`規劃中` 或 `尚未支持`，並連結實際 Result；沒有 Result 的項目不得使用完成語氣。

### 建議執行順序

| 階段 | 目的 | 主要變因 | 主要觀察 |
| --- | --- | --- | --- |
| 1. 路由與輸出成本 | 驗證三層路徑是否選對，Standard 是否降低無效報告 | Lightweight／Standard／Full Audit、正例與反例任務 | 路徑正確率、誤觸／漏觸、必要欄位遺漏、輸出長度、Reviewer 找到結論的時間 |
| 2. Repository 多樣性 | 檢查結果能否離開主要 Demo | 大型 .NET Legacy、TypeScript／React、Python；有無 `AGENTS.md`；測試完整度 | 契約辨識、Diff 局部性、行為漂移、停止判斷、驗證盲點 |
| 3. 任務與執行環境 | 檢查不同工作規模與 Agent 環境 | 小型修正、大型 Migration、不同模型、Reasoning Effort 與 Client | 品質 Gate、重工、工具呼叫、可重現性與平台差異 |
| 4. 真實團隊 Blind Review | 檢查 Skill 是否幫助人類更快做出可靠決策 | 不揭露實驗組別的候選與報告 | 風險發現率、誤判、Reviewer 決策時間與分歧 |

Java／Spring 保留在外部效度矩陣，但不列為第一批 Repository，避免同一版本同時維護過多語言 Fixture。完成前述三種技術棧後，再依貢獻者與可重現 Fixture 決定是否提升優先順序。

### 指標與主張邊界

- 觸發評測同時包含應啟用與不應啟用的任務，分別記錄誤觸與漏觸。
- Standard 與 Full Audit 先通過相同行為與品質 Gate，才比較輸出長度、Tool Call 或執行時間。
- Reviewer 決策時間必須有固定起點、終點與可比較材料，不能以主觀感受替代。
- 沒有 Token Telemetry 時，不以字數推估 Token，也不宣稱節省 Token。
- 跨 Repository、模型或 Client 的結果，只支持實際執行組合，不外推到「所有 AI Coding」。

## 測試先行策略

正式修改採 RED、GREEN、REFACTOR：

### RED

先修改或新增契約測試，讓 `v0.2.0` 因缺少下列行為而失敗：

1. 三層路徑與由高到低的升級條件。
2. Standard 必要輸出及可省略欄位。
3. Full Audit 保留所有 Heading、識別碼與空白調查規則。
4. 明確的不適用情境。
5. `allow_implicit_invocation: false`。
6. README、Metadata 與版本一致為 `v0.3.0`。
7. Benchmark 擴充矩陣能區分已驗證、規劃中與尚未支持。
8. Prototype／Production-Ready 不會改寫三層風險路徑或授權 Gate。
9. 驗證流程會選擇 Repository 既有且與風險相關的工具，並揭露未執行 Gate。

測試應檢查可觀察契約，不把整段自然語言或特定排版鎖死。每個失敗都要確認是因為缺少新契約，而不是路徑、編碼或測試本身錯誤。

本次問題已有兩項實際 RED 證據：Full Path 的強制空白段落造成報告過重，以及設定允許 implicit invocation、公開說明卻尚未驗證的契約張力。若要宣稱新的 Standard 指示確實改善 Agent 行為，仍需另行執行 Fresh Context 行為評測；只有結構測試全綠時，不做這項宣稱。

### GREEN

只修改通過新契約所需的最少內容：

- `clean-code-ai-collaboration/SKILL.md`
- `clean-code-ai-collaboration/references/review-output-contract.md`
- `clean-code-ai-collaboration/references/clean-code-for-agent-legibility.md`
- `clean-code-ai-collaboration/references/testing-and-change-safety.md`
- `clean-code-ai-collaboration/agents/openai.yaml`
- `README.md`
- `evals/benchmark.md`
- `tests/test_skill_contract.py`
- 必要時修改 `tests/test_eval_contract.py`

不新增 Reference、Result JSON 或跨語言 Fixture。`evals/manifest.json` 只有在真正新增可執行情境時才修改。

### REFACTOR

1. 移除三條路徑之間重複的說明。
2. 確認 `SKILL.md` 仍在 500 個英文單字以內。
3. 確認 Standard 沒有變成逃避 Full Audit 的漏洞。
4. 確認 Prototype 沒有被寫成降低安全、授權或正式資料門檻的例外。
5. 確認工具鏈規則優先採用 Repository 既有 Gate，沒有硬綁特定語言或產品。
6. 確認 README、Adapter、Skill 版本與呼叫方式一致。
7. 執行 Python 契約測試、Agent Skills 格式驗證、Markdown 連結與既有 CI Gate。

## 版本與相容性

這次會改變路徑選擇、輸出契約與 Codex 呼叫政策，屬於新的次版本，目標版本為 `v0.3.0`。

- 明確使用 `$clean-code-ai-collaboration` 的既有 Prompt 仍可使用。
- Lightweight Path 保留，但輸出可省略不適用項目。
- 原 Full Path 改名為 Full Audit；其嚴謹度與追蹤欄位不變。
- 依賴 implicit invocation 的使用方式在 `v0.3.0` 不受支持，必須改成明確呼叫。
- `v0.2.0` Result 保留為歷史證據，不重新標記成 Standard 或 Full Audit。

## 風險與控制

| 風險 | 控制方式 |
| --- | --- |
| Standard 被當成跳過調查的捷徑 | 固定升級條件；發現高風險或關鍵未知時必須轉 Full Audit |
| 三層路由增加判斷成本 | 依 Full Audit → Standard → Lightweight 的單向順序判斷，不建立交叉例外表 |
| Full Audit 因改名而遺失既有契約 | 契約測試先鎖定 Heading、識別碼、空白項目與 Blind Spot 規則 |
| 關閉 implicit invocation 降低發現率 | README 與 default prompt 提供明確呼叫；完成觸發評測後再重新決定 |
| Benchmark Roadmap 被誤認為結果 | 每個維度標示狀態；沒有 Result 就不得使用已驗證語氣 |
| 以輸出較短推論品質較好 | 先通過相同行為 Gate，再比較輸出成本與 Reviewer 決策時間 |
| Skill 因排除情境而漏接跨領域風險 | 專門 Skill 未涵蓋行為、邊界或副作用取捨時，允許明確併用 |
| Prototype 成為品質與授權捷徑 | 將交付成熟度與風險路徑分開；涉及正式邊界仍必須使用 Full Audit |
| 強迫所有專案採用同一套工具 | 先盤點 Repository 現有 Gate，工具缺口只提出建議，未經授權不安裝或修改 CI |
| TDD 被機械套用到所有任務 | 依可觀察行為選擇 Direct、TDD、Characterization、Acceptance 或 Mutation，不以儀式取代 Oracle |

## 驗收條件

`v0.3.0` 實作完成時必須符合：

1. `SKILL.md` 清楚區分 Lightweight、Standard 與 Full Audit，且路徑升級規則沒有歧義。
2. Standard 回報必要決策資訊，但不強迫空白 Heading 或穩定識別碼。
3. Full Audit 仍保留 `v0.2.0` 的完整 Heading、`F1/A1/U1/O1/E1`、空白調查規則與 Blind Spot。
4. Frontmatter、Adapter、README 與測試都以明確呼叫為正式契約，`allow_implicit_invocation` 為 `false`。
5. 不適用情境能排除純語法、概念問答、獨立範例、純格式及已被專門 Skill 完整涵蓋的工作。
6. Benchmark 清楚列出目前已驗證範圍與後續擴充順序，不增加未執行結果或普遍性保證。
7. Prototype 與 Production-Ready 能標示交付成熟度，且不會降低風險路徑、Authorization Gate 或正式行為要求。
8. Skill 會優先使用 Repository 既有且與任務相關的工具鏈，並將未執行 Gate 留在 Blind Spot。
9. 新測試曾在正式修改前因缺少 `v0.3.0` 契約而正確失敗，修改後全部通過。
10. Agent Skills 格式、Markdown 連結、UTF-8 與現有 CI Gate 通過。
11. 沒有 Token、Secret、內部 Repository 資料或不可公開 Evidence 進入 Commit。
12. 只有完成 Fresh Context 行為評測後，才能宣稱 Standard、新觸發規則或工具鏈路由改善實際 Agent 表現。

## 實作邊界

本次只修改 `Clean-Code-AI-Collaboration-Skill` Repository。設計規格 Commit 只包含本文件，不推送、不建立 Tag，也不發布 Release。

書面規格獲得確認後，才建立詳細實作計畫。正式實作不得在計畫前開始，也不得把 Benchmark 規劃項目包裝成已完成的外部驗證。
