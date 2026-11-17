# 架構中立需求增補 v0.2

此文件延續 `reference-v0.1/REQUIREMENTS.md`，不修改既有 ID，新增：

| ID | 需求 | 驗收重點 |
|---|---|---|
| WEB-REQ-01 | 能分析受支援的 Servlet Container 與部屬方式（JAR/WAR） | 偵測內嵌 Undertow，避免只刪掉 dependency |
| WEB-REQ-02 | Web Server 設定對應必須是語意/可量測比較，不是屬性名稱換字串 | Worker/Queue/Connection/Request limits 需測試 |
| WEB-REQ-03 | 完整保留 HTTP/Proxy/Security/Probe 行為測試 | encoded path、header、body、forwarded、overload |
| DB-REQ-01 | 分辨 Entity、JPQL、Native Query、DTO、SQL ResultSet Mapping 路徑 | 無明確映射的 Native Date Rule 不誤用於 JPQL |
| DB-REQ-02 | 綁定 DB Vendor、Driver、Schema、實際欄位/結果型別 | Oracle DATE 需真 Oracle DB 驗證，不把 H2 當等價 |
| DB-REQ-03 | 升級會改 DDL 時必須人工審核、與程式碼變更分開批准 | 絕不自動修改正式庫 schema |
| DB-REQ-04 | Entity state / Cascade / Transaction 需有行為追蹤 | Detached、@MapsId、bulk update、rollback |
| BOOT-REQ-01 | 檢查 Boot 模組化造成的 missing starter / test starter | Dependency graph 與 Context 啟動 |
| BOOT-REQ-02 | 掃描 Servlet / Actuator / Jackson / Security / Session 配置與對應風險 | 每個有效環境獨立判斷 |
| KB-REQ-01 | 每條 Rule 附官方來源、證據分類與需要驗證的上下文 | 官方變更 ≠ 專案已受影響 |
| KB-REQ-02 | 缺資料時維持 UNKNOWN/REVIEW_REQUIRED | 未提供外部配置時禁止自動選預設 |
| VFY-REQ-01 | Acceptance case 有 SPEC 與 ACTUAL 分離狀態 | 未執行測試不可宣稱通過 |

## 優先開發／驗證案例

1. Undertow + 同步慢 HTTP：HTTP Contract + Resource Baseline + Tomcat 對照。
2. Hibernate 7 Native Query Temporal Scalar：有/無 `@SqlResultSetMapping`、Oracle DATE 真 DB。
3. Hibernate Detached/Cascade：`@MapsId` 無顯式 Cascade 的建立流程。
4. Spring Boot 模組化導致某 Starter/Auto Configuration 缺漏。
5. Jackson Null Primitive：續用 v0.1 的 Effective Configuration 與 Golden Tests。

## 交付邊界

本包只提供架構中立知識，未實作 Agent、CLI、IDE、OpenRewrite Recipe 或測試執行程式。
