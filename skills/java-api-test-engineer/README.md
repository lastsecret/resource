# Java API Test Engineer

Java REST API 探勘、固定測例執行、JaCoCo 覆蓋率及 A/B 回歸比較的模組化 CLI。

**版本：0.1.0（可執行 MVP）**。核心採用 Python 標準函式庫；靜態 Java AST 掃描使用 JDK 17+ 的 Compiler Tree API。工具執行不需要 LLM、不會修改被測 Java 專案，所有流程均可獨立執行。

## 1. 安裝

要求：Python 3.10+；靜態掃描額外需要完整 JDK 17+。macOS、Windows、Linux 均可使用。

```bash
cd java-api-test-engineer
python3 -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
# YAML 規格輸入另外安裝：python -m pip install -e '.[yaml]'

japi --help
python -m pytest -q  # 開發者測試：需先安裝 pytest
```

離線環境可直接 `python -m japi --help`，無需 pip 安裝。ZIP 不包含 Python、JDK、JaCoCo JAR 或 Schemathesis 執行檔。

## 2. Endpoint 探勘

先做純靜態偵測，不啟動 Spring、Maven 或 Gradle：

```bash
japi inspect --project /path/to/java-service --output out/inspection
```

讀取 `out/inspection/capabilities.json`，再決定方案：

```bash
# 已有 OpenAPI 3.x：直接匯入
japi discover --mode openapi-file --openapi ./openapi.json --output out/discovery

# 純靜態 Java 分析：使用 JDK AST，不需編譯目標專案
japi discover --mode static-jdk --project /path/to/java-service --output out/discovery

# Springdoc Runtime：服務必須已啟動，不會自行啟動
japi discover --mode springdoc-runtime --docs-url http://127.0.0.1:8080/v3/api-docs --output out/discovery
```

產物：`endpoints.json`（method/path/parameters/request/response schemas）、`discovery-decision.json`。OpenAPI 輸入支援 v3.0/v3.1 JSON、YAML（需 PyYAML）；會保留 `$ref`。Springdoc Runtime 不需要被測程式碼，但需已啟動的應用。

**靜態分析限制：** JDK AST 能解析原始碼中的標準 Spring MVC Controller 與簡單 DTO，但沒有執行 Spring Bean 或完成 classpath symbol resolution。同一掃描範圍內的非泛型介面／父類別路由繼承已支援（包含方法與參數註解，Controller 自身註解優先）。泛型或外部依賴的父型別、record、Lombok、Jackson 客製轉換、複數路由、SpEL、WebFlux functional endpoints 可能有遺漏，系統會產生警示，不保證與實際 Runtime Schema 完全相同。

## 3. 固定 Request Case

```bash
# 預設僅 GET
japi generate --catalog out/discovery/endpoints.json --output out/cases

# 明確允許其他 HTTP methods，並產生兩組變體
japi generate --catalog out/discovery/endpoints.json \
  --methods GET,POST --variants 2 --output out/cases

# 指定已知測試值，避免猜測 Path ID（JSON key = "METHOD /path:name"）
japi generate --catalog out/discovery/endpoints.json \
  --fixtures fixtures.json --output out/cases
```

輸出：`cases.jsonl`、`case-quality.json`。Case ID 由 Endpoint 與變體編號生成，在輸入 Endpoint 順序改變時保持穩定。

信心度說明：

| 等級 | 條件 | 預設執行 |
|---|---|---|
| High | 有具體 Fixture / 成功狀態碼規格 | 允許 |
| Medium | OpenAPI Example/Enum/Default | 允許 |
| Low | 推測值或非刻意 `null` / `[]` | 允許，但警告 |
| Unknown | 尚無足夠資訊 | 視是否能構造必要欄位 |

非刻意 `null`、`[]` 會產生 `UNINTENDED_NULL`、`UNINTENDED_EMPTY_ARRAY`；只有在 `intentional_special_values` 指定欄位路徑、原因、預期行為時才豁免。GET 缺少 Body 不會被判定為 Null。必要參數無法推導會被標記 `blocked_reason`，禁止執行。

## 4. 執行 Request

```bash
japi execute --cases out/cases/cases.jsonl \
  --base-url http://127.0.0.1:8080 --output out/run-a

# 無法接受低信心資料時
japi execute --cases out/cases/cases.jsonl \
  --base-url http://127.0.0.1:8080 --block-low-confidence --output out/run-a

# 外部測試環境需明確允許；有狀態改變的方法亦需明確允許
japi execute --cases out/cases/cases.jsonl --base-url https://test.example.org \
  --allow-remote --allow-mutation --header 'Authorization=env:JAPI_TOKEN'
```

輸出：`results.jsonl`、`summary.json`。不跟隨 HTTP Redirect；預設回應 Body 上限 2MB，截斷或連線失敗不會當作成功比較。HTTP 錯誤（例如 404）仍保存回應內容。原始回應以 Base64 儲存供重播，**可能含敏感資料，需妥善保護輸出資料夾**。Auth Header 不會寫入結果檔。預設只連線 localhost；遠端目標需 `--allow-remote`。**GET 也可能有業務副作用，請僅對允許測試的環境執行。**

### 本機自動啟動與 JaCoCo

```bash
japi execute --cases out/cases/cases.jsonl \
  --base-url http://127.0.0.1:8080 \
  --launch-jar ./app.jar \
  --jacoco-agent ./jacocoagent.jar \
  --jacoco-cli ./jacococli.jar \
  --output out/run-local
```

此流程啟動一個本機 Java Process，掛載 JaCoCo TCP Server（127.0.0.1:6300），HTTP 測試結束後 Dump `jacoco.exec`，並停止該 Process。**只對顯式指定的 JAR 生效；不會自行改寫其他執行中的 Java Process。** 可選擇 `--app-arg` 傳入應用參數。

既有 JVM 若已掛載 JaCoCo agent 且使用 `output=tcpserver,address=127.0.0.1,port=6300`：

```bash
japi coverage dump --jacoco-cli ./jacococli.jar --exec out/coverage/jacoco.exec
japi coverage report --jacoco-cli ./jacococli.jar \
  --exec out/coverage/jacoco.exec \
  --classes ./target/classes --sources ./src/main/java --output out/coverage
japi coverage summarize --xml out/coverage/jacoco.xml --output out/coverage
```

輸出 XML/HTML JaCoCo Report，以及包含 Instructions、Branch、Line、Method 等 Counters 的 `coverage-summary.json`。各 Counter 是否存在依 JaCoCo 實際報表而定。

## 5. A/B Response Diff

```bash
# A/B 使用完全相同、已凍結的 Request
japi compare --cases out/cases/cases.jsonl \
  --a-url http://127.0.0.1:8080 \
  --b-url http://127.0.0.1:8081 \
  --rules examples/comparison-rules.yaml --output out/ab

# 亦可在完全不連網的狀態下比較兩份結果
japi compare --a-results out/run-a/results.jsonl \
  --b-results out/run-b/results.jsonl --output out/ab
```

輸出：`diff.json`、`diff.html`、`summary.json`；直接執行 A/B 時另存 `a-results.jsonl`、`b-results.jsonl`。

模式：

- `raw_exact`：回應原始 bytes 完全相同；搭配 HTTP status 與指定 Headers。
- `json_exact`：JSON 型別、值、陣列順序相同；物件欄位宣告順序無關。
- `semantic`（預設）：等同嚴格語意比較，但可額外開啟指定規則。
- `custom`：組合忽略字串大小寫、忽略指定陣列順序、指定 JSONPath 忽略、Null 與 Missing 等價、字串 trim、數值容差等。

忽略陣列排序採用多重集合匹配，**不丟失重複元素次數**。JSONPath 支援 `$.field`, `$.items[0]`, `$.items[*]`, `$.items[*].field` 與簡單欄位萬用字元，不支援完整 JSONPath 運算式。被規則掩蓋的嚴格比較差異會標記 `suppressed_by_policy`。

即使 A/B 相同，若 Case 信心度不足，仍顯示在 Diff 報表中；連線錯誤、測例遭阻擋、Body 截斷，一律回報 `inconclusive`，不得視為 PASS。

## 6. 進階探索（選配）

使用已有的 Schemathesis CLI（`st`）進行 GET 正向與 Fuzzing 探索：

```bash
japi explore --openapi ./openapi.json --base-url http://127.0.0.1:8080 \
  --max-time 30 --max-failures 10 --output out/exploration
```

輸出 Schemathesis 原生的 JUnit、HAR 等報表；**探索模式的隨機請求不會自動納入 A/B 固定測例庫**。非 GET 方法需 `--allow-mutation`；工具不會自行安裝 Schemathesis。

## 7. Agent 進階測例（選配）

```bash
japi enrich --project /path/to/java-service \
  --catalog out/discovery/endpoints.json \
  --coverage-xml out/coverage/jacoco.xml --output out/enrich
```

輸出 `context-bundle.json`，僅包含受限制的原始碼片段與未覆蓋行，供使用者選擇的 Coding Agent 產生候選測例。**CLI 本身不呼叫 LLM、不自動執行建議測例**。

## 8. Exit Code

- `0`：成功，且沒有差異／測試失敗。
- `2`：輸入、設定或工具執行錯誤。
- `3`：A/B 發現差異，或測試的 HTTP Status 不符預期規格。
- `4`：HTTP 執行錯誤／測例遭阻擋，或 Schemathesis 工具失敗。

## 9. 已知限制與開發狀態

核心 CLI 功能已實作並有自動化測試；仍不包含：每 Endpoint/每 Case 隔離 JaCoCo、完整 Java symbol/type resolution、Spring 動態路由完整解析、Schemathesis HAR 自動轉成凍結測例、資料庫 Fixture 生命周期管理、Schema breaking-change（oasdiff）整合，以及 Agent 自動產生測例。這些屬於後續版本，不應視為已完成能力。JaCoCo 真實 JAR 啟動整合需使用者在本機 Spring Boot 專案進行驗收。
