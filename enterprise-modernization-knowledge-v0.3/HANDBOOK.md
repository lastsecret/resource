# Spring Boot 3 → 4：相容性 Knowledge Pack v0.2

> 2026-11-13。**架構中立的規格與待驗證候選規則，不是自動修改 Recipe 或已完成的測試結果。**
> 起始適用：Spring Boot **3.5.x → 4.0.x**；請先解析實際 Spring Boot、Hibernate、Jackson、Spring Security、Servlet 容器與 JDBC Driver 版本，不能憑框架主版本推定所有依賴。

## 0. 共同判定契約

1. `Source Baseline`：鎖定 Git SHA、建置依賴圖、JDK、DB/Driver、Server、Profile、環境變數、配置檔與 Golden Results。
2. `Feature Presence`：確認專案真的使用特定 API / DB / Server；只命中依賴名稱不等於會發生業務行為變更。
3. `Effective Source`：解析原專案**實際生效**的設定與行為。Config 檔 → 外部配置/啟動參數 → 程式碼 Customizer → Runtime Probe；覆寫順序依各框架版本而定，不能只按此清單順序推斷。
4. `Version Default`：僅在確認沒有生效覆寫時，才引用該**具體版本**的預設。無法取得的設定標 `UNKNOWN`。
5. `Target Candidate`：先產生候選改動，不直接修改正式原專案；支援可追溯 rollback 與人工批准。
6. `Behavior Differential`：同輸入、同環境、同資料狀態比較源／目標的回應、錯誤、儲存副作用、SQL、資源與管理端點。
7. `Result`：`NO_CHANGE / CHANGE_REQUIRED / REVIEW_REQUIRED / APPROVED_DEVIATION`，品質關卡 `PASS / FAIL / UNKNOWN / NOT_RUN`，後三者絕對不可視為 PASS。

## 1. Undertow → Tomcat（4 條規則）

### WEB-UNDERTOW-001：平台相容性

**確認的版本事實**：Spring Boot 4 因 Servlet 6.1 baseline 而移除內嵌 Undertow 支援。官方支援內嵌 Tomcat 11 與 Jetty 12.1。Tomcat 是本計畫建議目標，但不代表可任意等價轉換設定。

**必要採集**：原始 POM 是否排除 tomcat、是否使用 `spring-boot-starter-undertow`、內部 `UndertowServletWebServerFactory`、`UndertowBuilderCustomizer`、`HttpHandler`、XNIO API、WebSocket，以及是否為 JAR/WAR。確定容器對 Spring Web MVC 的責任範圍。

**候選修正**：移除 Undertow Starter 和特定 Customizer，提供相容的 Tomcat Starter（或審核 Jetty）、重新檢查 Servlet Filter 和 WebSocket；優先在工作樹測試 `mvn clean verify` 和啟動，再做 HTTP 契約比對。

### WEB-UNDERTOW-002：Thread/Queue 不可盲目轉換

Undertow 的 `server.undertow.threads.io`、`server.undertow.threads.worker` 與 Tomcat 的 `server.tomcat.threads.max`、`server.tomcat.max-connections`、`server.tomcat.accept-count` **沒有可保證的數值一對一對應**。

**掃描點**：同步慢 HTTP、序號鎖 `synchronized`、`@Transactional`、同步等待 Future、Worker 數、Endpoint QPS、長連線比例、Ingress/Probe；Tomcat 有沒有啟用 Virtual Threads 也會影響執行緒設定解讀。

**驗證**：重現相同負載（含 Normal/Slow API 比例）；採集 P95/P99、成功／拒絕、active threads、排隊、CPU、Heap/Direct Memory、健康檢查及 Graceful Shutdown。不能僅因 Tomcat Worker 變成 200 就認定已提升穩定性。

### WEB-UNDERTOW-003/004：HTTP 與部署契約

逐項比對：URI `%2F`、Path/Query 編碼、Forwarded Headers、Cookie 數、Request Headers 與大小、Multipart、Request/Response Charset、錯誤碼、Access Log、Keep-Alive、連線 Timeout。重點是實測**舊版有效設定**和新版結果，不能把 `server.undertow.*` 字串機械式替換為 `server.tomcat.*`。`server.max-http-request-header-size` 的設置含義需以實際 Web Server 實現確認。

## 2. Hibernate 6 → 7（12 條規則）

### HIB7-NATIVE-DATETIME-001：Native Query 時間型別差異

**官方確認**：沒有 `@SqlResultSetMapping` 時，Hibernate 7 的 Native Query 日期/時間 scalar 預設回傳 `LocalDate / LocalTime / LocalDateTime`；Hibernate 6 原本傾向 `java.sql.Date / Time / Timestamp`。若要保留舊映射，可評估 `hibernate.query.native.prefer_jdbc_datetime_types=true`，但先確認來源實際行為、目標結果與設定影響範圍。

**區分必須清楚**：`@Query(nativeQuery=true)` / `EntityManager.createNativeQuery()` / `@SqlResultSetMapping` / JPQL `@Query` / Entity `@Column` 映射 / DTO projection。這些**不是同一條轉換路徑**。如果 Java 宣告 `LocalDate`，不要只看到 Oracle `DATE` 就判定一定失敗；要看 ORM 走的轉換路徑和 JDBC metadata。

### HIB7-ORACLE-DATE-002：Oracle DATE ↔ Java 日期語義

Oracle `DATE` 可存日期加時分秒，並非 ANSI SQL 的單純日期型別。`LocalDate` 只表達日期；若舊專案曾把有時分秒的 Oracle DATE 轉成 LocalDate，必須知道何處丟棄時間，是否原本就已丟失。比較：DB Schema、實際資料、Driver、Native vs JPQL、`@JdbcTypeCode`、Converter、Method Return Type、Timezone/Session 設定。

**最小驗證**：同一張 Oracle 表存兩筆 `DATE`（00:00:00、23:59:59），另測 null；原版／新版分別走 Entity、JPQL、Native Scalar、DTO 四條路徑，記錄 Java Runtime Class、實際值、例外、SQL、binding。H2 Oracle Mode 僅可作語法輔助，**不是 Oracle JDBC 相容性證據**。

### HIB7-CASCADE-MAPSID-003 / DETACHED-004

- `@MapsId / @Id` 關聯的隱含 `cascade=PERSIST` 被移除：需看原有 cascade、Entity state、交易與保存次序，不能無條件補 `cascade=ALL`。
- `refresh/lock` 對 Detached Entity 的行為轉向標準規範；測試 Managed vs Detached、是否在 Transaction 中、期待的異常及狀態回寫。

### HIB7-RAW-HQL-005 / IMMUTABLE-006

- HQL `createQuery("from X, Y")` 之類未顯式 SELECT、也未指定結果型別的查詢可能不再接受；候選是明確 SELECT 或 Typed Query，必須再比較結果 shape。
- Immutable Entity 的 bulk update/delete，預設由允許／警告轉為丟例外；可以評估 `hibernate.query.immutable_entity_update_query_handling_mode=allow` 暫時維持，但不能以全域 `allow` 掩蓋違反設計意圖的修改。

### HIB7-STATELESS-007 / API-REMOVAL-008

- `StatelessSession` 的二級快取行為改變；舊 `hibernate.jdbc.batch_size` 不再直接控制它的 batching。要看已生效的 Cache Mode、SQL 批次數與一致性。
- `Session.load/save/update/saveOrUpdate/delete` 移除後，依實際 transient/detached/managed 狀態，分別使用 `getReference/persist/merge/remove`。**`merge` 並非簡單替代 `update` 的逐字改名。**

### HIB7-ORACLE-DDL-009 / ARRAY-010

- Oracle `TIMESTAMP` 的預設 DDL precision 變成 9；`float/double` 新預設型別可變 `binary_float / binary_double`。官方指出 Timestamp Precision 影響的是 DDL 產生，不應直接宣稱所有讀取語義都變了。正式庫 DDL 變更需要明確 DBA 審核。
- MySQL/MariaDB Basic Array 的預設 mapping 可能從 VARBINARY 改成 JSON_ARRAY；若有舊資料需要考慮雙向讀寫及資料轉換，**不得自動 DROP / ALTER 正式欄位**。

### HIB7-CRITERIA-011 / VALIDATION-012

- Criteria Path/Join 對 subtype 專屬屬性不再隱式 Treat，需檢查 Entity Inheritance 實際模型。
- `ValidationMode.AUTO` + Provider 建立失敗，Hibernate 7 會將錯誤上拋；需確認啟動與例外契約。

## 3. Spring Boot 4 常見項目（14 條規則）

1. `SB4-MODULAR-001`：Starter/Auto Configuration 模組化；特別看 Flyway、Liquibase、RestClient、GraphQL、JPA 等。`starter-classic` 可作短期過渡，不作最終最佳實務。
2. `SB4-PACKAGE-002`：`org.springframework.boot.autoconfigure.*` 中的類別依技術模組移位；要做 Symbol Map 並實際 Compile。
3. `SB4-TEST-003`：技術專屬 Test Starter；不因測試可以 Compile 就假設所有 Slice Test 可啟動。
4. `SB4-PROPERTIES-004`：Properties 改名/移除；在受限環境取得所有 Profile/外部配置後才改，`spring-boot-properties-migrator` 只作暫時診斷。
5. `SB4-JACKSON-MODULE-005`：Jackson classpath module auto-discovery 變更，實際 Mapper 可能有 Serializer/Deserializer 行為差異。
6. `SB4-JACKSON-API-006`：Jackson 3 核心 package 改 `tools.jackson`、Boot 的 Component/Customizer 改名；`jackson-annotations` 是例外。保持 v0.1 的 null→primitive Rule，不強制全域 Jackson 2 defaults。
7. `SB4-HTTP-CONVERTER-007`：自訂 HttpMessageConverter Bean 的處理有差異；分開確認 Client 與 Server。
8. `SB4-RESTCLIENT-008`：RestTemplate/RestClient 專屬 Starter、Builder、Converter、Timeout、Trace Header 傳遞確認。
9. `SB4-ACTUATOR-009`：Liveness/Readiness 預設啟用，驗證暴露路徑、Security 與 K8s Probe。
10. `SB4-ENTITYSCAN-010`：`@EntityScan` package 搬移，exception translation 設定改名。
11. `SB4-SECURITY-011`：Security 7 的 Jackson 3 模組序列化設定與 Session/Token 相容性。
12. `SB4-SESSION-012`：Spring Session Redis Config 變更；關注 TTL/Serializer/Namespace。
13. `SB4-SERVLET-013`：Servlet 6.1 / Framework 7 / 容器與 WebSocket 相容性。
14. `SB4-TOMCAT-WAR-014`：外部 Tomcat WAR 的 Runtime Starter 要區分於 Embedded JAR。

## 4. 決策範例（同一條 Rule，不同專案結果不同）

| Rule | Source Effective | Target Initial | 結論 |
|---|---|---|---|
| HIB7-NATIVE-DATETIME | Native Scalar 回傳 `java.sql.Timestamp`，程式強轉該類型 | 實測為 `LocalDateTime` | 建立局部轉換或經審核保留舊型別，重新驗證 |
| HIB7-NATIVE-DATETIME | JPQL 映射 `LocalDate`，沒有 Native SQL | JPQL 正常 | 此 Native Rule **NOT_APPLICABLE** |
| HIB7-ORACLE-DATE | Oracle DATE 含非零時分秒；Java DTO `LocalDate` | 目標讀取時間精度不同 | 不自動改成 `LocalDateTime`；先確認舊契約與業務允許的精度 |
| WEB-UNDERTOW | Undertow 已使用特殊 XNIO Handler | Tomcat 缺少該 Handler | 需要架構處理／人工審核，非單純 Maven 改版 |
| WEB-UNDERTOW | IO Worker 8 / Worker 32 | Tomcat threads.max=32 | **UNKNOWN**，沒有基準測試前不可說等價 |
| SB4-JACKSON-MODULE | 原專案明確註冊自訂 Module | 目標已自動註冊且重複 | 比對有無重複模組影響，局部修正 |
| SB4-PROPERTIES | 某 property 在外部檔案中，但檔案無法取得 | 無資訊 | **REVIEW_REQUIRED**，不可當成沒有設定 |

## 5. 驗證設計與品質閘門

- **Gate A Preflight**：Plugin/工具、私有 Maven Artifact、JDK、Target Dependency、Server、資料庫／驅動、Knowledge Pack 均就緒。
- **Gate B Source Baseline**：固定 Commit + Configuration Manifest + 部署模式 + Golden Tests；未能取得配置須標記缺口。
- **Gate C Migration Change Review**：每個修改對應 Rule/Finding/Decision/Patch，不能有沒有理由的全域替換。
- **Gate D Build & Boot**：Maven build、Context 啟動、Auto Configuration 狀態、DB 連線與遷移。
- **Gate E Differential**：HTTP 行為、ORM 寫入/讀取、Session、錯誤碼、Performance under load，按風險適當取樣。
- **Gate F Approval**：只有所有必要 Gate `PASS` 或有核准的例外，才能標示升級完成；`NOT_RUN/UNKNOWN` 不可冒充 PASS。

## 6. 完成狀態

目前為 **規則規格初稿**，已整理官方文件支持的版本差異和工程風險，但**未取得任何公司專案、沒有執行 Maven、Oracle、Hibernate 7 或容器遷移測試**。所有 `acceptance-cases.yaml` 的 `actual_result` 初始均為 `NOT_RUN`。Knowledge Pack 可用於後續實作 Agent / CLI / UI 的統一資料契約，不能直接認定是已驗證的自動修復配方。

## 7. 官方來源

- Spring Boot 4 Migration Guide：https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide
- Spring Boot 3.5 Properties：https://docs.spring.io/spring-boot/3.5/appendix/application-properties/
- Spring Boot 4 Properties：https://docs.spring.io/spring-boot/4.0/appendix/application-properties/
- Spring Boot System Requirements：https://docs.spring.io/spring-boot/system-requirements.html
- Hibernate 7 Migration Guide：https://docs.hibernate.org/orm/7.0/migration-guide/
- Hibernate 7 Oracle DATE Notes：https://docs.hibernate.org/orm/7.1/introduction/html_single/
- Spring Framework 7 Release Notes：https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes
- Spring Security 7 Migration：https://docs.spring.io/spring-security/reference/migration/
- Spring Boot Modularization：https://spring.io/blog/2025/10/28/modularizing-spring-boot/
