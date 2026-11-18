# Enterprise Modernization Knowledge Pack v0.5

**Based on v0.4 Dynamic Java. Architecture independent.**

本版在**保留原始 63 條規則 ID 與原有 Java Runtime Policy** 的前提下，重新標定每條規則的 `rule_type`、`migration_evidence_v0_5` 與禁止自動修復的條件。新增 HikariCP 6→7（6 條）與 Oracle JDBC 23.7→23.9（8 條），合計 **77 條**。

## 先讀這幾份

1. `EVIDENCE-POLICY.md` — v0.5 最終權威政策與 Go/No-Go Gate。
2. `catalog.json` — 所有規則的索引、分類、證據狀態與自動修正禁令。
3. `migration-rules.yaml` — 有公開文件支持差異的候選規則索引（仍需要逐項查證及專案命中）。
4. `verification-catalog.yaml` — **只執行驗證，不得修改程式碼** 的規則 ID 索引。
5. `rules/*.yaml` — 唯一完整規則資料（包含舊版 ID 與新欄位）。
6. `recipes/recipe-availability.yaml` — 專用／通用 OpenRewrite Recipe 可用性。
7. `acceptance-cases.yaml` — 案例與政策負向測試規格，均為 NOT_RUN。
8. `MIGRATION-CONFIG-GUIDE.md` — 動態 Java 17/21 版本 policy（沿用 v0.4）。

## 規則統計

{"BEHAVIOR_CHANGE": 15, "VALIDATION_ONLY": 39, "BREAKING_CHANGE": 22, "REGRESSION": 1}

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
