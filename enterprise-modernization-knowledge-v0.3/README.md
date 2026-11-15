# Enterprise Modernization Knowledge Pack v0.3

- 版本：**v0.3 / 2026-11-13**
- 核心情境：Java 21、Spring Boot 3.5.x → 4.0.x；不能直接套到 4.1.x，需再驗證規則適用性。
- **63 條候選規則**（沿用 v0.2 的 30 條，新增 33 條）、**65 個待執行驗收案例**（v0.2 的 24 個，新增 41 個）。
- 所有驗收狀態：`NOT_RUN`；本包是規格與調查知識，**不是經實測的全自動升級 Recipe**。

## 開啟順序

1. `HANDBOOK.md`：v0.2 的原始 30 條規則說明。
2. `HANDBOOK-v0.3.md`：新加 MyBatis、Security、生態系的規則重點與判定策略。
3. `rules/`：YAML 規則；v0.3 新增 `mybatis-3-to-4.yaml`、`spring-security-6-to-7.yaml`、`spring-boot-4-ecosystem.yaml`。
4. `WORKBENCH-RISK-ASSESSMENT.md`：GUI/IDE 開發風險、Go-No-Go、最小 MVP。
5. `REQUIREMENTS-ADDENDUM-v0.3.md`：架構中立增補需求。
6. `sources.yaml`：官方文件 URL；`catalog.json`：供 Agent/介面索引的概覽。
7. `acceptance-cases.yaml`：驗收情境；尚未執行。
8. `reference-v0.1/`：原始 Requirements 與 Jackson 規則（保留不變）。

## 原則

- 從**來源有效設定與行為**出發；沒有有效覆寫才對照版本預設。
- 已文件確認的元件變更，不等於每個專案都有 Breaking Change。
- 所有 Rule 先檢查 Feature Presence，再找版本差異與修正策略。
- No Change 與 Not Applicable 也是有效結論；Unknown / Not Run 不能當 Pass。
- 一律隔離修改、Diff 審核、保留證據；Security 變更須明確人工核准。
- Workbench 作為**可替換的 UI**，不是 Knowledge 或 Verification 的必要依賴。
