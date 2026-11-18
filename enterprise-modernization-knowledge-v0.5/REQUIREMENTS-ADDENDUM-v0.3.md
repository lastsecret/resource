> **v0.5 policy notice:** 歷史描述僅作背景參考；規則分類、是否可以修正與 Java 版本政策，請以 `EVIDENCE-POLICY.md`、`catalog.json`、`rules/*.yaml` 為準。不可依舊版 `evidence_class` 判定可自動修復。

# Enterprise Modernization Requirements v0.3 補充條款

> 這是 v0.1/v0.2 的增補，不替代原始內容；持續架構中立。

| ID | 新增需求 | 優先度 |
|---|---|---|
| KB-11 | 對套件建立精確版本矩陣；區分核心 library、Spring integration、Boot starter 及 BOM | P0 |
| KB-12 | Rule 必須明確標示已證實版本差異或候選風險；不得將風險盤點冒充 Breaking Change | P0 |
| KB-13 | Rule 適用性需包含專案實際使用路徑；缺依賴時為 NOT_APPLICABLE | P0 |
| SEC-01 | 每個 Security Finding 綁定有效 SecurityFilterChain、路徑、HTTP method、使用者角色與 Profile | P0 |
| SEC-02 | 登入/Token/Session 的舊資料相容性測試不能只測新 Token | P0 |
| SEC-03 | 未核准不得放寬授權、關閉 CSRF、跳過 JWT 檢查或改變 401/403 policy | P0 |
| DB-01 | MyBatis Mapper/TypeHandler/SQL/Transaction 產生行為可追溯證據；資料庫測試辨識 DB dialect | P0 |
| DB-02 | 認出多 DataSource 的 Mapper→SqlSessionFactory→TransactionManager 實際關聯 | P0 |
| ECO-01 | springdoc/Cloud/Batch 之類第三方 Starter 要使用官方版本矩陣和既有行為雙重驗證 | P0 |
| UI-01 | 產品不必自建 IDE；以 GUI 引導與 Artifact Review 為第一期的足夠交付 | P1 |
| UI-02 | GUI 控制 Agent 需通過 Session Pause/Resume/Approval 的 Spike 後才進入開發 | P0 |
| UI-03 | 有條件允許 GUI 完全只讀；原生 Claude Code 操作不是 MVP 失敗 | P0 |
| UI-04 | 不得根據 CLI 的自由文字宣稱階段完成；以可驗證檔案、Git SHA 和 Quality Gate 產出確定狀態 | P0 |
| UI-05 | 原有 Agent Plugin 升級導致契約改變時，標示 UNSUPPORTED；不要沿用舊報告 PASS | P0 |
