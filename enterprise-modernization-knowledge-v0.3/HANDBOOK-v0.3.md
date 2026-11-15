# Spring Boot 3 → 4 Knowledge Pack v0.3 新增說明

> 對應 Spring Boot 3.5.x → 4.0.x、Java 21。既有 v0.2 文件原樣保留；本文件為新增規則索引與解讀重點。**規則文件不是已通過測試的遷移 Recipe。**

## 1. 根本判斷原則

1. 確認來源與目標的確切 Dependency Tree，包括 BOM / 私有 Nexus / 排除與強制版本。
2. 按 Feature Presence 確認原專案確實使用該套件功能，必要時解析 Mapper / HttpSecurity FilterChain / Endpoint。
3. 先取得來源有效設定（Profiles、External Config、@Bean、Customizer、Runtime）；版本預設值只能在不存在有效覆寫時引用。
4. 產生 `Finding` 與候選修正；不能因規則被偵測就直接全域修復。
5. 對所有重要變更執行 Build、Startup、Contract / Differential；安全授權變更需人工簽核。
6. `DOCUMENTED_CHANGE` 代表**該版本差異有官方文件支持**，不是本專案一定受影響；`COMPATIBILITY_ASSESSMENT` 代表**值得查驗的風險**，不主張官方一定改變預設。

## 2. MyBatis（9 條）

- MyBatis Core 仍在 3.5.x；Boot 4.0 使用 Starter 4.0.x、MyBatis-Spring 4.0.x。切換到 Boot 4.1 時要重新解版本矩陣。
- `@MapperScan`/XML/SqlSessionFactory、ConfigurationCustomizer、ResultMap、TypeHandler、Batch、DataSource/Transaction、Plugins 要確認原專案有效行為。
- 特別強調 `mybatis.configuration.*` 與 `mybatis.config-location` 的限制；多 DataSource 手動建置時 SpringBootVFS 等需自行考慮。
- MyBatis-Plus 為不同 Boot Major 提供不同 Starter，避免與官方 Starter 重複加入造成依賴或 Bean 衝突。

## 3. Spring Security（12 條）

- 條件性 API 變更：Lambda DSL、Access Decision 相容模組、Dispatcher Matcher、Method Security Metadata、Security Jackson Modules。
- 隱性行為與高風險安全契約：JWT typ validator、JWK fetch timeout、Opaque Introspection Credential Encoding、Filter SecurityContext、CSRF/CORS/Cookie。
- **不可讓 Agent 在未經批准下改成 permitAll、全域關閉 CSRF、降低 JWT 驗證，或延長安全系統 timeout。**
- 每次修改至少測匿名、一般使用者、管理者、無效/過期 Token、未授權資料存取；有 Session 時再做跨版本老 Session 讀取。

## 4. 生態系（12 條）

- `springdoc-openapi` 2→3（Boot 4.0 搭配 springdoc 3.0.x）；除了 Swagger UI 還需比較 `/v3/api-docs` 的 JSON Schema。
- `Spring Cloud` Release Train 要依 Boot 線更新，不能只升父 POM。
- `Spring Batch` 若原使用 JDBC Metadata，Boot 4 需確認使用 `spring-boot-starter-batch-jdbc`，否則重啟語意可能失效。
- Redis Session/Serializer、GraphQL Enum、Validation、Observability、MockMvc 等按 **來源有效行為** 進行最小差異驗證。

## 5. 展示規則實際價值的三組案例

1. **明確設定 vs 預設值**：MyBatis 來源 `mapUnderscoreToCamelCase=false`；即使有團隊慣例，不能盲目改 true。
2. **Build 綠但權限破口**：Security DSL 編譯通過，`/admin` 變匿名可訪問；Authorization Matrix Gate 必須 FAIL。
3. **看似無關的 Batch Starter**：升 Boot 4 後 Job 仍可執行，但歷史 execution metadata 沒寫入原資料庫；即使 Build PASS 也不能宣稱相容。

## 6. 說明文件與對照來源

請以 `sources.yaml` 為唯一來源索引，規則用 `sources` ID 引用；來源只表明框架事實，尚須結合專案證據。

## 7. 實測狀態

本次僅整理文獻與編寫機器可讀規則、驗收案例；**未執行 Maven/DB/Endpoint/Agent Workflow 的實測**。所有自動生成案例的 `actual_result` 都是 `NOT_RUN`。
