# Clean Code AI Collaboration Skill

`clean-code-ai-collaboration` 是一套開源 Agent Skill。它把 Clean Code 的程式碼、設計、架構與軟體工藝觀念，整理成 AI Coding 可以重複使用的判斷流程。

這個 Skill 不會替 Repository 發明規則，也不會把某次實驗勝出的方案當成所有專案的標準答案。它要求 Agent 先讀懂專案情境，再交代選項、取捨、行為邊界、驗證方式，以及什麼情況應該改採其他做法。

## 這個 Skill 解決什麼問題

只對 Agent 說「請遵守 Clean Code」，通常不夠具體。Agent 可能把函式拆得很短，卻增加大量跳轉；也可能建立漂亮的分層，卻順手改掉 API Contract、資料語意或副作用順序。

這個 Skill 把模糊的品質期待轉成一套工作流程：

- 分清楚 Repository 事實、推測與未知資訊。
- 依風險選擇輕量或完整流程，不把所有任務都做成大型重構。
- 比較可行方案，說明當下選擇與其他方案適用的情境。
- 先守住行為、資料、副作用與依賴邊界，再比較 Token 或工具呼叫成本。
- 留下實際執行的測試、工具輸出、盲點與人工決策。

它要改善的不是 Agent「會不會生成程式碼」，而是 User 能不能掌握 Agent 為什麼這樣改、改了什麼，以及我們憑什麼相信結果。

## Clean Code 如何改善 AI Coding

Clean Code 原本是為了讓人更容易閱讀、理解與維護程式碼。到了 AI Coding 時代，這些價值沒有消失，因為 Agent 同樣需要讀取名稱、責任、依賴、測試與領域語言，才能判斷修改位置與影響範圍。

當程式碼能清楚表達意圖時，Agent 較容易：

- 找到真正負責該行為的程式碼，而不是在多個相似位置碰運氣。
- 從名稱、型別與邊界理解規則，少靠推測補完需求。
- 把 Diff 控制在必要範圍，降低連帶修改與行為漂移。
- 透過可讀的測試確認系統答案，而不是只相信「Build 成功」。
- 在下一輪修改時重新取得情境，不必每次都從混亂的實作反推意圖。

這不代表 Clean Code 會讓模型突然變聰明，也不保證每次都能節省 Token。它真正提供的是較清楚的理解線索、修改邊界與驗證入口；是否省下成本，仍取決於專案規模、任務類型、模型與工具環境。

## CLEAN 五原則

CLEAN 是本專案從 Clean Code 精神與 AI Coding 實務歸納出的協作原則。它規範 User 如何駕馭 Agent，而不是把五個字母當成 Agent 自己作答的考卷。

| 原則 | 中文名稱 | 在 AI Coding 中負責什麼 |
| --- | --- | --- |
| C — Context-Aware Code | 情境感知 | 先掌握真實需求、Repository 規則、領域語言與既有行為，不用「一般都這樣做」補完空白。 |
| L — Localized Change | 局部變更 | 限制修改範圍、Diff 與副作用，讓每一行變更都能對應這次任務。 |
| E — Explicit Intent and Boundaries | 意圖明確 | 說清楚名稱、型別、角色、邊界、停止條件與授權範圍。 |
| A — Auditable by Evidence | 實據可審 | 保留 Prompt、Diff、測試、工具輸出、盲點與人工判斷，不把 Agent 自述當成證據。 |
| N — Non-Surprising Behavior | 符合預期 | 守住 API、資料、錯誤、副作用與失敗路徑，避免品質整理偷偷換掉系統答案。 |

## Skill、Repository Policy 與自動化 Gate 的分工

三者都能約束 Agent，但責任不同：

| 機制 | 適合放什麼 | 不適合取代什麼 |
| --- | --- | --- |
| Skill | 跨專案可重複使用的判斷流程、提問方式、Review 視角與輸出契約 | 不能猜出某個 Repository 的特有規則 |
| Repository Policy | 團隊已確認且相對穩定的命名、架構、測試與授權規範 | 不能取代需要權衡情境的工程判斷 |
| 自動化 Gate | Formatter、Lint、Build、Test、架構規則與其他可機器判定的門檻 | 不能證明未被測試涵蓋的需求一定正確 |

實務上可以讓 Skill 指引 Agent 如何判斷，把專案特有規則留在 `AGENTS.md` 或其他 Repository Instruction，再由自動化 Gate 執行不能靠提醒帶過的檢查。

## 安裝

先取得 Repository：

```powershell
git clone https://github.com/eric861129/Clean-Code-AI-Collaboration-Skill.git
Set-Location .\Clean-Code-AI-Collaboration-Skill
```

macOS／Linux：

```bash
git clone https://github.com/eric861129/Clean-Code-AI-Collaboration-Skill.git
cd Clean-Code-AI-Collaboration-Skill
```

真正需要安裝的只有 `clean-code-ai-collaboration` 資料夾；`evals`、`tests`、`docs` 與 `.github` 是評測、驗證與維護資料。

### Project Skill

如果只想讓目前專案使用，請把 Skill 放到該專案的 `.agents/skills`。

Windows PowerShell：

```powershell
$skillSource = (Resolve-Path ".\clean-code-ai-collaboration").Path
$projectRoot = "C:\path\to\your-project"
$skillsRoot = Join-Path $projectRoot ".agents\skills"
$target = Join-Path $skillsRoot "clean-code-ai-collaboration"

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) {
    throw "找不到目標專案：$projectRoot"
}

if (Test-Path -LiteralPath $target) {
    throw "安裝目標已存在：$target。請先確認內容，不要直接覆寫。"
}

New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
Copy-Item -LiteralPath $skillSource -Destination $target -Recurse
```

macOS／Linux：

```bash
skill_source="$(pwd)/clean-code-ai-collaboration"
project_root="/path/to/your-project"
skills_root="$project_root/.agents/skills"
target="$skills_root/clean-code-ai-collaboration"

if [ ! -d "$project_root" ]; then
  echo "找不到目標專案：$project_root" >&2
  exit 1
fi

if [ -e "$target" ]; then
  echo "安裝目標已存在：$target。請先確認內容，不要直接覆寫。" >&2
  exit 1
fi

mkdir -p "$skills_root"
cp -R "$skill_source" "$target"
```

### Personal Skill

如果要讓同一位 User 的多個專案使用，可以安裝到個人 `.agents/skills`。

Windows PowerShell：

```powershell
$skillsRoot = Join-Path $env:USERPROFILE ".agents\skills"
$target = Join-Path $skillsRoot "clean-code-ai-collaboration"

if (Test-Path -LiteralPath $target) {
    throw "安裝目標已存在：$target。請先確認內容，不要直接覆寫。"
}

New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
Copy-Item -LiteralPath ".\clean-code-ai-collaboration" -Destination $target -Recurse
```

macOS／Linux：

```bash
skills_root="$HOME/.agents/skills"
target="$skills_root/clean-code-ai-collaboration"

if [ -e "$target" ]; then
  echo "安裝目標已存在：$target。請先確認內容，不要直接覆寫。" >&2
  exit 1
fi

mkdir -p "$skills_root"
cp -R "./clean-code-ai-collaboration" "$target"
```

Codex 通常會自動偵測新加入的 Skill；如果 Skill 清單沒有出現，再重新啟動 Codex。

### Client 支援狀態

Agent Skills 的檔案格式可以攜帶內容，不代表每個 Client 的載入、觸發與工具行為都相同。

| Client | 內容與格式 | 本專案驗證狀態 |
| --- | --- | --- |
| Codex | 可使用 Skill 核心與 Codex adapter | 已以 `gpt-5.6-sol`、`high` 完成目前公開評測 |
| GitHub Copilot | 核心 Markdown 內容可移植 | 尚未完成實機驗證；安裝位置與觸發方式請以 Client 官方文件為準 |
| Claude Code | 核心 Markdown 內容可移植 | 尚未完成實機驗證；安裝位置與觸發方式請以 Client 官方文件為準 |
| 其他 Agent Skills 相容 Client | 原則與參考文件可移植 | 尚未驗證，不宣稱工具、授權或輸出行為相容 |

## 使用方式

以下 Prompt 刻意分成規劃、實作與 Review。User 仍應補上真實需求、Repository 路徑、可修改範圍與驗收方式。

### 規劃

```text
請使用 $clean-code-ai-collaboration 規劃這次修改。
先列出 Repository 事實、假設與未知資訊，再比較可行方案、行為風險、Diff 邊界與停止條件。
目前只需要規劃，不要修改檔案、Commit、Push 或部署。
```

### 實作

```text
請使用 $clean-code-ai-collaboration 實作這個需求。
先確認既有行為與測試，將修改限制在必要範圍；完成後回報 Diff、實際執行的驗證、未涵蓋風險與人工決策。
未經授權不要 Commit、Push、部署或修改正式資料。
```

### Review

```text
請使用 $clean-code-ai-collaboration Review 這次變更。
依 Repository 證據檢查意圖、責任、依賴、測試、行為漂移與副作用；先列出可重現的問題，再說明盲點與建議。
不要只依作者摘要或「測試全綠」判定可以接受。
```

## Benchmark

評測的目的不是替 Skill 創造一個總分，而是讓讀者看見它在哪些公開情境改善了決策流程、哪裡沒有改善，以及我們沒有量到什麼。

- [Benchmark 說明](evals/benchmark.md)
- [評測情境與契約](evals/manifest.json)
- [v0.1.0 行為基準](evals/results/v0.1.0-baseline.json)
- [v0.2.0 初始評測](evals/results/v0.2.0-initial.json)

目前 Repository 情境評測的觀察如下：

| 評測組 | 執行數 | 自動失敗 | 情境證據完整支持 | 行為證據完整支持 | 決策理由完整支持 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 通用 Prompt 基準 | 12 | 2 | 6／12 | 7／12 | 1／12 |
| v0.2.0 Skill | 12 | 0 | 9／12 | 12／12 | 12／12 |

這組數字只適用於預先宣告的四種 Repository 情境與固定執行規約。並行情境有 3 次輸出超出預先宣告的語意 Diff Pattern，結果仍完整保留，沒有改寫成失敗或從資料中移除。Micro-eval 沒有顯示普遍的答案品質優勢；Token 與工具呼叫數也因執行環境未提供可靠資料而未比較。

兩組歷史結果的評估程序並非完全相同，公開資料已保留這項限制。因此這些結果適合用來重現與提出新假設，不適合宣稱 Skill 已在所有專案或 Client 上勝出。

## 已知限制與不保證事項

- 不保證所有 Repository、語言、模型、Client 或任務都得到相同結果。
- 不保證一定節省 Token、時間或費用；品質 Gate 也可能增加短期執行成本。
- Build 與 Test 通過，只能證明已執行範圍內的結果，不等於已部署、正式環境正確或完成 UAT。
- Process-local 的並行保護不等於跨程序、跨節點或 Exactly-once 保證。
- Skill 不會替 User 擴張授權；Commit、Push、部署、刪除檔案與正式資料修改仍需明確授權。
- Repository 事實不足時，正確結果可能是停止、揭露未知資訊並請 User 決定，而不是繼續生成程式碼。

## Repository 結構

```text
clean-code-ai-collaboration/  # 可安裝的 Skill
evals/                        # 公開情境、原始輸出與 Benchmark
tests/                        # Skill 與評測契約測試
.github/workflows/            # 自動驗證
docs/                         # 設計、計畫與維護文件
```

結構契約測試會確認 Skill 的封裝、路由、授權閘門與輸出欄位存在，但不會把全綠解讀為 Agent 行為品質已被完整證明：

```powershell
py -3 -m unittest discover -s tests -v
```

## 貢獻評測情境

歡迎補充可公開重現的情境。新的 Benchmark 應至少提供：

- 固定 Repository 與 Commit、Prompt、模型、Client、工具和授權範圍。
- 預先宣告的 Gold Files、允許的 Diff Boundary 與必須保留的行為。
- 與候選輸出分離的 Oracle 或驗收條件。
- 原始輸出、Diff、命令、Exit Code、盲點、失敗與人工決策。
- 清楚區分 `Observed`、`Inference`、`Unknown` 與 `Failure`。

請保留不利結果，不要只上傳成功案例，也不要用單一加權總分掩蓋不同面向的差異。

## 來源、非官方聲明與授權

這個 Skill 來自「Clean Code × AI Coding」系列實驗：從《無瑕的程式碼 第二版》的觀念出發，結合實際使用 AI Agent 開發的經驗，再以 CLEAN 五原則整理 User 駕馭 Agent 的方法。

本專案是個人整理與實驗成果，不是 Robert C. Martin、原出版商、OpenAI、GitHub 或 Anthropic 的官方作品。Skill 提供的是決策流程，不是特定專案的正確答案。

MIT License。詳見 [LICENSE](LICENSE)。
