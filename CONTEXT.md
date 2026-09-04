# Clean Code AI Collaboration

本文件定義 `Clean-Code-AI-Collaboration-Skill` 的穩定領域術語。完整架構、契約與驗收規則以版本化 SPEC 為準。

## Language

**Core Skill**:
所有支援技術棧共同使用的 Clean Code 決策、授權、驗證與輸出契約。
_Avoid_: Generic Skill, Base Profile

**Profile**:
依 Repository Facts 條件式補充 Core Skill 的技術棧知識單元。
_Avoid_: Rule Pack, Standalone Skill

**Profile Candidate**:
Detection 訊號顯示可能適用，但尚未完成狀態、相依與衝突檢查的 Profile。
_Avoid_: Applied Profile, Selected Profile

**Applied Profile**:
已通過狀態、相依與衝突檢查，並實際用於目前 Changed Module 的 Profile。
_Avoid_: Profile Candidate, Enabled Profile

**Language Profile**:
涵蓋一種程式語言、標準 Runtime、標準 Library 與 Project System 語意風險的 Profile。
_Avoid_: Framework Profile, Ecosystem Guide

**Framework Profile**:
涵蓋建立在語言之上的 Framework Lifecycle、狀態、副作用與公開介面風險的 Profile。
_Avoid_: Language Profile, Library Checklist

**Changed Module**:
本次 Expected Diff 或 Actual Diff 所屬、由最近 Owning Manifest 與 Repository Policy 界定的模組。
_Avoid_: Repository Root, Entire Repository

**Owning Manifest**:
從候選 Changed File 向 Repository Root 尋找時，最接近且能界定其 Project 或 Package 邊界的 Manifest。
_Avoid_: Root Manifest, Any Manifest

**Supporting Detection Fact**:
可補強語言、Framework、Renderer、版本或 Workspace 判斷，但不能單獨界定 Changed Module 或啟用 Profile 的檔案、依賴或 Repository Fact。
_Avoid_: Owning Manifest, Sufficient Detection Signal

**Module Boundary**:
Owning Manifest 所界定的 `project`、`package` 或 `workspace` 範圍；同距離時依此順序由具體到廣泛選擇。
_Avoid_: Repository Root, Arbitrary Directory

**Version-Sensitive Fact**:
從 TFM、Runtime、Compiler Config 或 Dependency Version 取得，用來判斷某項 Profile 建議是否適用的 Repository Fact。
_Avoid_: Latest-version Assumption, Global Minimum Version

**Runtime Profile Index**:
從 Profile Metadata 產生並隨 Core Package 提供的可讀索引，讓 Agent 在不解析 YAML 的情況下辨識 Profile 狀態與 Detection 摘要。
_Avoid_: Profile Registry, Consumer Configuration

**Profile Composition**:
Applied Profile 經 `requires`、`recommends`、`conflicts` 與穩定載入順序解析後形成的組合。
_Avoid_: Profile Candidate List, Arbitrary Profile Set

**Core Only**:
Core Skill 未套用任何 Profile 的有效執行狀態，適用於無充分訊號、使用者明確指定或非關鍵組合無法成立時。
_Avoid_: Unsupported, Failed Routing

**Consumer Repository**:
安裝並使用 Core Skill 的外部 Repository，其 Policy 與 Repository-native Gates 優先於通用 Profile 建議。
_Avoid_: Source Repository, Fixture Repository

**Core Package**:
主要可安裝產物，包含 Core Skill 與所有可用 Profile Reference，並以漸進式路由控制載入。
_Avoid_: Specialist Package, Source Repository

**Specialist Package**:
由 Core 與指定 Profile 自動組裝的 Distribution Artifact，內含一個可獨立安裝的 Skill。
_Avoid_: Specialist Skill, Manual Fork

**Bundled Profile**:
已包含於某個 Core 或 Specialist Package、可供 Runtime 選擇的 Profile；Bundled 不代表它必定適用或已套用於目前 Changed Module。
_Avoid_: Applied Profile, Always Enabled Profile

**Package Manifest**:
記錄 Specialist Package 來源模式、來源版本、Suite／Packager 版本、排序後 Profile ID、輸入雜湊與實際 Package File 雜湊的可機器驗證清單。
_Avoid_: Profile Metadata, Release Notes

**Reason Code**:
Routing Fixture 與 Diagnostic 使用的穩定機器代碼，用來驗證決策分支而不綁定可調整的人類敘述。
_Avoid_: Full Error Message, Display Copy

**Profile Maturity**:
Profile 的證據狀態，依序為 `planned`、`experimental`、`beta`、`stable` 或 `deprecated`，與 Suite SemVer 分開管理。
_Avoid_: Suite Version, Feature Flag
