# Enterprise Modernization Knowledge Pack v0.4 — Dynamic Java Target

- **內容沿用 v0.3**：63 條候選規則，涵蓋 Spring Boot 3.5.x → 4.0.x、Jackson、Hibernate、Undertow/Tomcat、MyBatis、Security 等。
- **不預設 Java 17 或 Java 21**：Java 版本由各次 `Migration Config` 輸入，預設策略是 `preserve`，即維持來源專案的 Java 版本。
- **驗收案例：74 個**（文件規格，`NOT_RUN`）；新增通用 Java 相容性測試。
- **資料仍為知識與驗收規格，不是自動執行的 OpenRewrite Recipe**。

## 起點

1. 閱讀 `MIGRATION-CONFIG-GUIDE.md`。
2. 複製 `examples/java17-preserve.json`、`examples/java21-preserve.json` 或自行建立 Config。
3. 編輯每次遷移的來源、目標、工具鏈、依賴版本；應由真實專案解析結果填寫，範例不是實測。
4. 使用 `python3 tools/validate_migration.py <config.json>` 做**靜態相容性預檢**。
5. 再執行真正的 Maven/Gradle、Java Runtime、CI/Docker、Golden Regression Test；通過 Config 預檢並不等於已成功升級。

```bash
python3 tools/validate_migration.py examples/java17-preserve.json
python3 tools/validate_migration.py examples/java21-preserve.json
python3 -m unittest discover -s tests -v
```

## 重要檔案

- `constraints/java-runtime-policy.yaml`：目標 Java 推導、最低版本檢查、變更批准策略（架構中立）。
- `compatibility/java-minimums.json`：已確認特定套件版本線最低 Java 版本與官方來源。
- `schemas/migration-config.schema.json`：供 CLI、TUI、Herdr Mods 或 GUI 使用的輸入資料契約。
- `tools/validate_migration.py`：最小參考實作（Python 標準函式庫，不依賴 Agent）。
- `acceptance-cases.yaml`：通用 JDK 版本的驗收案例。
- `rules/`：既有相容性分析 Knowledge Rules。

## 規則治理原則

先觀察來源專案的 Effective Configuration 與 Baseline 行為；若無覆寫再對照版本預設值；若有差異，採取最小修改並留下證據。目標套件版本不在相容性矩陣中時標記 `REVIEW_REQUIRED`，**不能當作通過**。本包主要覆蓋 Spring Boot 4.0.x；要升 4.1.x 應增加對應 Knowledge Rules 與相容性驗證。
