# 每次 Migration 可動態指定 Java 版本

## 目的

同一套 Spring Boot 3→4 Knowledge Rules 可重用於 Java 17、Java 21 或其他已驗證版本；JDK 是 **執行上下文**，不是規則的固定前提。`source.java.feature_version` 必須是實際來源專案 JDK 的調查結果，不能推測。

## Config 欄位

| 路徑 | 用途 |
|---|---|
| `source.java.feature_version` | 原專案實際使用的 Java feature version（例如 17、21） |
| `source.java.evidence` | 推導來源，建議含 POM、CI、執行時 JDK 觀察 |
| `target.java.mode` | `preserve` 或 `explicit` |
| `target.java.feature_version` | 僅 `explicit` 模式指定 |
| `target.java.change_approved` | 來源與目標 JDK 不同時，必須有人工核准 |
| `toolchain.migration_tool_jdk` | 執行 Maven/OpenRewrite 等遷移工具的 JDK，**與應用目標 JDK 分開** |
| `toolchain.compiler_release` | 編譯目標 Release |
| `toolchain.runtime_jdk` | 預期部署 Runtime JDK；需另外實測 |
| `toolchain.ci_jdk` / `docker_jdk` | CI、容器目標 JDK，缺少資訊應要求人工確認 |
| `components[]` | 解析出的確切框架與依賴版本；參考實作只覆蓋矩陣列明的版本線 |

## 重要原則

1. **Preserve 是預設策略**：來源 Java 17 → 目標 Java 17；來源 21 → 目標 21，不因為 Boot 4 自行強迫升 JDK。
2. **不是所有來源 JDK 都符合 Boot 4**：例如來源 Java 11 → preserve Java 11 會被 Boot 4.0 的最低 Java 17 限制阻擋，不能假裝相容。
3. **Explicit 必須審核**：來源 Java 17 → 目標 Java 21 是另外一項明確決策，不能由 Agent 擅自修改。
4. **靜態版本檢查 != 完整相容性證明**：還要解析 Transitive Dependencies、私有 Starter Bytecode、Annotation Processor、Maven/Gradle、CI、Docker，並在真實目標 Runtime 執行測試。
5. **版本不明不等於相容**：無法判斷某套件實際版本、適用矩陣或自訂執行環境，結果為 `REVIEW_REQUIRED`。
6. **工具 JDK 和產品 JDK 分離**：允許用 JDK 21 跑改寫工具，但必須以 `--release 17` 編譯，並在 Java 17 上啟動、測試，才能接受 Java 17 目標。
7. **保持舊行為**：升級過程仍需依來源專案的 Effective Configuration 與既有測試決定行為相容性修復，例如 Jackson 的 null/primitive 反序列化設定。
8. **知識範圍**：本包涵蓋 Spring Boot 3.5.x → 4.0.x；將 Spring Boot 4.1.x 作為目標時，Preflight 應先提示需要增加對應規則。

## 範例

- `examples/java17-preserve.json`: 來源 17、目標保持 17；工具使用 21 不影響程式 Runtime。
- `examples/java21-preserve.json`: 來源 21、目標保持 21。
- `examples/java11-incompatible.json`: Java 11 保持不升 → Spring Boot 4.0 阻擋。
- `examples/java17-to21-unapproved.json`: 17→21 未核准 → 阻擋。
- `examples/java17-to21-approved.json`: 17→21 有核准 → 僅通過版本預檢，仍需回歸測試。

## 下游整合

1. GUI/TUI/Agent 先收集 Migration Config 與有效 Maven/Gradle/CI 配置。
2. 版本引擎回傳靜態預檢的結果 (`PRECHECK_PASS`, `BLOCK`, `REVIEW_REQUIRED`) 及證據。
3. 同一份 Config 傳給 Compatibility Analyzer、OpenRewrite 策略選擇與 Quality Gate。
4. Quality Gate 對照 `target_java`、Baseline Git SHA、Dependency Lock 與實際 Build/Runtime 證據，不依賴 AI 主觀聲稱。

參考資料：
- Spring Boot 4.0 system requirements: https://docs.spring.io/spring-boot/4.0/system-requirements.html
- Spring Security 7.0 prerequisites: https://docs.spring.io/spring-security/reference/7.0/prerequisites.html
- Hibernate ORM 7.0 migration guide: https://docs.hibernate.org/orm/7.0/migration-guide/
- MyBatis Starter requirements: https://mybatis.org/spring-boot-starter/mybatis-spring-boot-autoconfigure/
