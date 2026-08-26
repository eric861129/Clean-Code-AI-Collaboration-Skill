# Clean Code AI Collaboration Skill

`clean-code-ai-collaboration` 是一個給 Codex 使用的開源 Skill。它把 Clean Code 的程式碼、設計、架構與軟體工藝觀念，整理成 AI Coding 時可以重複使用的判斷流程。

它不會替 Repository 發明規則，也不會把某一次實驗的勝出方案當成標準答案。它要求 Agent 先讀取專案情境，再交代選項、取捨、行為邊界、驗證方法，以及什麼情況應該改採其他做法。

## 安裝

將 Repository 下載後，把 `clean-code-ai-collaboration` 資料夾複製到 Codex 的 Skills 目錄：

```powershell
Copy-Item -LiteralPath ".\clean-code-ai-collaboration" -Destination "$env:USERPROFILE\.codex\skills\clean-code-ai-collaboration" -Recurse
```

重新啟動 Codex 後，可以在任務中明確指定：

```text
請使用 $clean-code-ai-collaboration，依 Repository 情境規劃、實作並審查這次修改。
```

## Skill 會做什麼

- 先分清楚 Repository 事實、假設與未知資訊。
- 依任務載入最少且適用的程式碼、測試、設計或協作參考文件。
- 比較可行方案，說明當下選擇與其他方案適用的情境。
- 先守住行為、資料、副作用與依賴邊界，再比較 Token 或工具呼叫成本。
- 依固定輸出契約留下可審查的決策與驗證紀錄。

## 結構契約驗證

這組測試確認 Skill 的封裝、路由、授權閘門與輸出欄位存在，不把全綠解讀為 Agent 行為品質已被完整證明。實際效果仍要透過固定任務、對照組、獨立 Oracle 與人工 Review 評估。

```powershell
py -3 -m unittest discover -s tests -v
```

## 來源與定位

這個 Skill 來自「Clean Code × AI Coding」系列實驗：從《無瑕的程式碼 第二版》的觀念出發，結合實際使用 AI Agent 開發的經驗，再以 CLEAN 五原則整理 User 駕馭 Agent 的方法。

本專案是個人整理與實驗成果，不是 Robert C. Martin、原出版商或 OpenAI 的官方作品。Skill 只提供決策流程，專案規則與實際風險仍以 Repository 與負責人判斷為準。

## 授權

MIT License。詳見 [LICENSE](LICENSE)。
