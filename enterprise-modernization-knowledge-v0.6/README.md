# Enterprise Modernization Knowledge Pack v0.6 — Jackson Effective Mapper Edition

**Based on v0.5 Evidence-Based + v0.4 Dynamic Java. Architecture independent.**

本版在**保留原始 63 條規則 ID 與原有 Java Runtime Policy** 的前提下，重新標定每條規則的 `rule_type`、`migration_evidence_v0_5` 與禁止自動修復的條件。新增 HikariCP 6→7（6 條）與 Oracle JDBC 23.7→23.9（8 條），原有 **77 條規則完整保留**；新增 2 條 Jackson 預設行為差異規則與 1 條 Mapper 建立來源盤點規則，合計 **80 條**。

## 先讀這幾份

2. `JACKSON-EFFECTIVE-CONFIG.md` — Jackson `null → primitive`、屬性排序與自行建構 Mapper 的專屬判定流程。
3. `EVIDENCE-POLICY.md` — v0.5 核心政策（含 v0.6 Jackson 增補）與 Go/No-Go Gate。
3. `catalog.json` — 所有規則的索引、分類、證據狀態與自動修正禁令。
4. `migration-rules.yaml` — 有公開文件支持差異的候選規則索引（仍需要逐項查證及專案命中）。
5. `verification-catalog.yaml` — **只執行驗證，不得修改程式碼** 的規則 ID 索引。
6. `rules/*.yaml` — 唯一完整規則資料（包含舊版 ID 與新欄位）。
7. `recipes/recipe-availability.yaml` — 專用／通用 OpenRewrite Recipe 可用性。
8. `acceptance-cases.yaml` — 案例與政策負向測試規格，均為 NOT_RUN。
9. `MIGRATION-CONFIG-GUIDE.md` — 動態 Java 17/21 版本 policy（沿用 v0.4）。

## 規則統計

{'BEHAVIOR_CHANGE': 17, 'VALIDATION_ONLY': 40, 'BREAKING_CHANGE': 22, 'REGRESSION': 1}

*舊版 evidence_class 已改名為 legacy_evidence_class_v0_4，僅供歷史追溯，新版判斷一律看 `rule_type` + `migration_evidence_v0_5.evidence_status`。*

## 本版的安全預設

- `automatic_patch=false`，對 **全部規則** 都成立。
- `VALIDATION_ONLY` 不得提出無明確已證實差異的設定／程式碼修正。
- 所有來源版本、目標版本、JDK、有效設定和實際測試都必須在專案層重新確認。
- 過去不精確的推定版本差異被降級為驗證項目；來源僅有一般文件且尚未逐項核對者為 `REQUIRES_CLAIM_LEVEL_SOURCE_REVIEW`。
- `REQUIRES_CLAIM_LEVEL_SOURCE_REVIEW` 不得進入自動修改流程。
- `REGRESSION` 限已知受影響版本；HikariCP 7.0.0 的 `setSchema` 案例不適用 7.0.1+。

## 自動檢查

```bash
python3 tools/verify_policy.py
python3 -m unittest discover -s tests -v
```

只需標準 Python + PyYAML（讀取 YAML 資料；不涉及 Maven 或實際修改）。

## 已做／尚未做

已做：重分類、規則資料格式化、索引與驗收案例關聯、Recipe 候選清單、靜態驗證。

**未做：** 對每個現存規則的官網條文逐條深入審計、實際 Maven 專案掃描、OpenRewrite 真實執行、功能回歸及 Oracle DB 驗證。請勿把 `OFFICIAL_DOC_SECTION_CHECKED` 當成專案升級成功的證據。


## v0.6 新增與整合

- `rules/jackson-2-to-3-effective-config.yaml`: `JCK3-NULL-PRIMITIVES-001`、`JCK3-POJO-ORDER-002`、`JCK3-MAPPER-TOPOLOGY-003`.
- 原有 `SB4-JACKSON-MODULE-005` / `SB4-JACKSON-API-006` 增補手動 new / builder / factory / custom Bean 的 Mapper 來源追蹤要求，ID 不變。
- 原有 `reference-v0.1/jackson-null-primitives.example.yaml` 保留並指向新標準規則。
- `acceptance-cases.yaml` 加入 15 個新情境：來源顯式覆寫、新版自行 new、Spring 設定不套用、POJO vs Map、`@JsonPropertyOrder`、多 Profile。
- 規則一律 `automatic_patch=false`; 一律先查有效來源與舊系統 Baseline 再提出修改。
- `sources.yaml` 增加 Jackson 官方原始碼與 Boot JSON 文件可追溯來源。

*本資料包的 JSON/YAML 結構及單元測試已檢查；實際 Java 回歸測試尚未執行。*
