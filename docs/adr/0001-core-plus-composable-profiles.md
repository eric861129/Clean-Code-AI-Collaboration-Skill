# ADR-0001：單一 Core 與可組合 Profiles

- 狀態：Accepted
- 日期：2026-09-04
- 決策者：Repository Maintainer
- 完整規格：[v0.5.0 可組合語言與框架 Profile 架構設計](../superpowers/specs/2026-09-04-composable-language-framework-profile-architecture-design.md)
- 術語：[CONTEXT.md](../../CONTEXT.md)

## 背景

既有 `clean-code-ai-collaboration` 已提供跨語言的 Clean Code、風險路徑、授權、驗證與輸出契約。若為每個語言或框架手動複製一份完整 Skill，Core 規則、版本、測試與證據會逐漸漂移；若把所有技術棧內容直接加入 Entry Point，又會增加每次任務的 Context 成本。

## 決策

Repository 維持 Monorepo 與單一手動維護的 Core Skill。語言與框架差異以 Language Profile、Framework Profile 表達，依 Changed Module、Repository Facts、成熟度與 Composition Contract 選擇；無充分適用事實時維持 Core Only。

Profile Metadata 是維護、CI 與 Packaging 的 Registry。Consumer Runtime 讀取由 Metadata 產生的 Markdown Runtime Profile Index，不需要解析 YAML。可獨立安裝的 Specialist Package 只能由 Packager 從相同 Source of Truth 產生，不成為另一份可寫來源。

## 主要取捨

### 接受的代價

- 新增 Profile 必須同時維護 Metadata、Reference、Routing／Semantic Tests 與 Generated Docs。
- Routing、Composition、Evidence 與 Packaging 需要額外 Schema 和跨平台測試。
- Specialist Package 的建立速度讓位給可重現性、來源追蹤與 Fail-closed 安全邊界。

### 得到的好處

- Core 授權、風險與輸出契約只有一份，不因技術棧分叉。
- Agent 只載入目前 Changed Module 需要的 Reference，限制 Context 膨脹。
- Language 與 Framework 可分層組合，也能在 Polyglot Repository 逐模組判斷。
- Planned、Experimental、Beta、Stable 與 Deprecated 有可驗證的 Evidence Boundary。

## 未採用方案

1. **每個技術棧維護獨立 Skill Repository**：初期入口直接，但 Core 內容、Release 與測試容易分叉。
2. **把所有技術棧規則放入 Core Entry Point**：部署簡單，但破壞漸進式載入與既有篇幅 Contract。
3. **讓 Consumer Runtime 直接解析 Profile YAML**：能共用 Metadata，但迫使安裝 YAML Runtime Dependency，增加可攜性與供應鏈成本。
4. **只靠檔案副檔名自動選擇 Framework**：實作簡單，但 `.tsx` 等訊號不足以證明 React／Vue Dependency 與行為相關性。

## 邊界

本 ADR 核准 `v0.5.0` 的 Preflight、Profile Contract、Routing、C#／Python／TypeScript／React Experimental Profiles、四個 Planned Profiles 與一個未發布的 C# Sample Package。Profile Pilot、Go／Rust／Java／Vue Reference、Push、Tag、Release 與公開發布都需要後續獨立核准。
