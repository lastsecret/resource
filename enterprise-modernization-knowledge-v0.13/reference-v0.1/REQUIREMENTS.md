> **v0.5 policy notice:** 歷史描述僅作背景參考；規則分類、是否可以修正與 Java 版本政策，請以 `EVIDENCE-POLICY.md`、`catalog.json`、`rules/*.yaml` 為準。不可依舊版 `evidence_class` 判定可自動修復。

# Enterprise Modernization｜架構中立需求規格 v0.1

> 狀態：需求初稿（待確認／待實驗驗證）；日期：2026-11-13  
> 原則：本文件是**產品與行為契約**，不是實作設計。CLI、IDE、Web、Desktop、Claude Code、其他 Agent、OpenRewrite、JDT LS 都是可替換的技術選項。  
> 首個參考場景：由 Migration Config 指定 Java 來源與目標版本、Spring Boot 3.5.x → 4.0.x，包含 Jackson 2→3、Hibernate 6→7 等相容性議題。其他版本路徑必須明確申告適用性，不能推定支援。

## 0. 核心定義

**核心目的**：基於**原專案真正生效的設定與既有行為**，識別來源／目標技術版本的差異，產生最小必要的變更，並以可追溯證據證明升級後行為符合相容性要求。

- **Source Baseline**：升級前的固定程式碼版本、依賴版本、執行環境、啟動參數、配置和行為測試結果。
- **Effective Configuration**：對某個環境、Profile、Bean／Mapper、路徑或情境，實際生效的設定值；不是掃描到的任意設定值。
- **Behavior Contract**：在指定輸入、環境與條件下，外部可觀察的結果（回應、錯誤、持久化副作用等）。
- **Knowledge Rule**：記錄版本差異、適用條件、預設值、偵測策略、證據與驗證方法的版本化資料；不應直接等同自動修改指令。
- **Finding**：某項 Knowledge Rule 與專案現況交叉比對後的發現，包含信心、範圍與實際證據。
- **Quality Gate**：可重現且有明確通過準則的驗證關卡；未知狀態不可視為通過。
- **Compatibility Goal**：預設為「行為保持一致」，但允許人工明確核准刻意改變行為，並留下理由和測試。

## 1. 產品目標與邊界

| ID | 需求 | 優先度 |
|---|---|---|
| GOAL-01 | 針對既有專案做版本升級分析、規劃、修改與驗證，而不只令程式編譯成功 | P0 |
| GOAL-02 | 在無法訪問公開文件／GitHub／Maven Central 的受限企業環境，仍能使用預先準備的知識與工具 | P0 |
| GOAL-03 | 保留既有行為，尤其是**預設值、設定覆寫和隱性行為差異** | P0 |
| GOAL-04 | 保留架構選擇自由：工作流程與知識規則不依賴特定 Agent、UI、Plugin 或 Parser | P0 |
| GOAL-05 | 讓一般工程師可視化地操作與審查；未來可用 GUI，但 GUI 不應是執行引擎的唯一入口 | P1 |
| GOAL-06 | 形成可於不同系統、模組與專案沿用的 Knowledge Pack、基準測試及審核流程 | P0 |

**不以 v0.1 承諾的範圍**：通用 IDE 編輯／除錯器、任意程式語言全自動遷移、所有情境百分百自動判定、所有業務行為可用單元測試完全證明、完全離線運行任何雲端模型。

## 2. 使用者與情境

- **工程師**：載入專案、設定升級目標、檢視相容性問題、審核修改與驗證結果。
- **技術主管／Reviewer**：批准升級策略、接受有意識的行為差異、檢視風險與證據。
- **平台／維運工程師**：準備離線知識、私有依賴倉庫與執行環境；維護版本化資源包。
- **知識維護者**：更新官方規則、公司內部慣例、誤判修正、驗證案例及來源證據。

### 主要使用旅程

1. 指定專案根目錄與升級目標；建立固定的 Source Baseline。
2. Preflight 檢查 JDK、建置工具、Repository、可執行依賴、設定缺口及必要的模型連線。
3. 收集依賴圖、實際配置、程式碼使用點、Bean／Mapper／Client、啟動路徑與行為測試。
4. 從 Knowledge Pack 取得適用版本的 Breaking／Behavioral Changes，與專案事實交集比對。
5. 產生 Findings、影響範圍、決策建議、修正計畫和待確認問題。
6. 在隔離工作副本執行候選修正；每次變更都保留可追溯紀錄。
7. 執行編譯、單元／整合／契約／行為差異測試；未過關則修復、回退或人工審查。
8. 輸出 Evidence Report、剩餘風險與簽核紀錄；必要時可恢復工作階段。

## 3. 功能性需求

### 3.1 專案解析與 Baseline

| ID | 需求 | 優先度 |
|---|---|---|
| PRJ-01 | 偵測版本、JDK、建置方式、Maven/Gradle、多模組依賴與實際解析結果 | P0 |
| PRJ-02 | 固定 Source Commit／檔案指紋、目標版本、知識包版本、工具版本與執行環境 | P0 |
| PRJ-03 | 掃描 `application.yml/.yaml/.properties`、Profile、外部設定、環境變數、系統屬性、啟動參數及其來源 | P0 |
| PRJ-04 | 識別程式碼配置：`@Bean`、自訂 Mapper／Customizer、模組註冊、註解、Converter、Deserializer 等 | P0 |
| PRJ-05 | 允許多套實際執行環境／Profile，有獨立的有效設定快照 | P0 |
| PRJ-06 | 能辨識同一專案多個 Mapper／Bean／Client，並對應到具體業務呼叫路徑；不可預設全系統只用一個 Mapper | P0 |
| PRJ-07 | 無法取得外部配置或環境時標記缺口，不得推論為「未設定」 | P0 |
| PRJ-08 | 保留 Baseline 測試輸入、輸出與參數；測試資料須去識別與脫敏 | P0 |

### 3.2 Knowledge Pack（架構中立資料規範）

| ID | 需求 | 優先度 |
|---|---|---|
| KB-01 | 可離線保存官方遷移指南、Release Notes、API 文件、公司升級經驗及來源連結／版本／擷取時間 | P0 |
| KB-02 | 規則須包含**適用來源／目標版本範圍**，不可僅以「Jackson 3」等粗粒度標籤判定 | P0 |
| KB-03 | 規則可描述「舊版預設值」「新版預設值」「明確配置可覆寫」「適用上下文」及其證據 | P0 |
| KB-04 | 規則必須區分 Breaking API、配置名稱變更、Default Change、Runtime Behavior Change、Dependency、Security 等 | P0 |
| KB-05 | 每條規則可連接偵測策略、候選修正、必要測試、風險和不能自動處理的條件 | P0 |
| KB-06 | 知識包可版本控管、稽核、簽核、回退；可與專案掃描結果分離 | P0 |
| KB-07 | 同一主題若有來源衝突或版本範圍未涵蓋，應標示爭議／缺口，不任意選一條當真 | P0 |
| KB-08 | 可先用結構化規則＋全文檢索實現，RAG／向量索引屬可替代的搜尋能力 | P1 |
| KB-09 | 支援企業自訂套件、私有 Starter、內部慣例和公司驗證案例 | P0 |
| KB-10 | 保留文件使用權限、來源與授權資訊；不能假定所有網頁可不受限制地完整複製進公司倉庫 | P1 |

### 3.3 Effective Configuration 與行為差異分析（關鍵）

| ID | 需求 | 優先度 |
|---|---|---|
| CFG-01 | 在每個環境／Profile／實際執行路徑解析**來源版本有效設定** | P0 |
| CFG-02 | 評估框架外部組態覆寫順序、程式碼客製化、設定初始化時機、Mapper／Bean 優先次序 | P0 |
| CFG-03 | 如果來源專案**明確設定**，以實際生效值為準；不可直接以套件預設值替代 | P0 |
| CFG-04 | 如果確認**未設定且沒有其他覆寫路徑**，才查來源套件／框架的預設值 | P0 |
| CFG-05 | 比對新版本「在相同環境與新設定下」的有效行為，而非僅對比兩版預設值 | P0 |
| CFG-06 | 規則依實際命中情境提出 no-change／config-change／code-change／test-only／manual-review 建議 | P0 |
| CFG-07 | 無法確認設定來源、版本行為、Mapper 選用或建置實際依賴時，結果為 UNKNOWN／REVIEW_REQUIRED | P0 |
| CFG-08 | 修正方案以**最小必要變更**保留契約，且考慮影響範圍；不可為單一 API 問題盲目改全域設定 | P0 |
| CFG-09 | 支援明確批准的行為變更（Approved Deviation），保留前後對照、理由與簽核者 | P1 |
| CFG-10 | 區分「無配置」「配置存在但未生效」「配置相互覆寫」「無法觀測」四種情況 | P0 |

### 3.4 升級流程、調度與人工介入

| ID | 需求 | 優先度 |
|---|---|---|
| WF-01 | 支援初始化→Preflight→Assess→Delta→Plan→Pilot→Uplift→Verify→Report 等邏輯階段 | P0 |
| WF-02 | 可沿用官方 Code Modernization 的階段與既有產物，但核心資料格式應能由其他 Workflow Adapter 實作 | P0 |
| WF-03 | 每階段有輸入、輸出、狀態、執行紀錄、可續跑／可重新計算的條件 | P0 |
| WF-04 | 重要關卡需人工批准：改動策略、Pilot Diff、接受行為差異、最終合格結論 | P0 |
| WF-05 | 自動修改操作只能在隔離工作樹／副本上進行；原專案預設不得直接覆寫 | P0 |
| WF-06 | 可整合確定性工具（例如 Recipe）和 Agent 修復，但不得把工具選擇硬編進 Knowledge Rule 的基本事實 | P0 |
| WF-07 | 可追溯每一個變更來自何項 Finding／Rule／人工決策／工具呼叫 | P0 |
| WF-08 | 未知、失敗、人工暫停需保留為不同狀態；不能以「流程跑完」冒充驗證通過 | P0 |

### 3.5 驗證與證據

| ID | 需求 | 優先度 |
|---|---|---|
| VFY-01 | Baseline 和 Target 針對相同輸入與可比的外部條件執行行為測試 | P0 |
| VFY-02 | 至少支援編譯、Unit、Integration、Contract 和 Before/After Differential Test | P0 |
| VFY-03 | 比對資料包含回應內容／狀態碼、例外類型、持久化副作用和必要的日誌／事件 | P0 |
| VFY-04 | 對時間、隨機 ID、序號及環境相依值，採**經核准的正規化／比對策略**，不可粗暴忽略差異 | P0 |
| VFY-05 | 測試無法執行、資料不足或結果不穩定皆不可標成 PASS | P0 |
| VFY-06 | 能將每個 Knowledge Finding 對應到一項或多項驗證證據 | P0 |
| VFY-07 | 針對隱性行為退化（例如 JSON null→primitive int）須有可重現的 Golden Test | P0 |
| VFY-08 | AI 可提出修正，但不得私自更改舊版 Golden Expected Results 使測試通過 | P0 |
| VFY-09 | 顯示尚未涵蓋的風險，不能因已通過的測試全綠就宣稱功能完全一致 | P0 |

### 3.6 操作介面、輸出與稽核

| ID | 需求 | 優先度 |
|---|---|---|
| UX-01 | 使用者可不用記住底層 CLI 指令，而以階段、任務與成果操作 | P1 |
| UX-02 | 可顯示官方或替代工作流程的階段、目前動作、等待互動與成功／失敗狀態 | P1 |
| UX-03 | 可瀏覽分析檔、Knowledge Rule、程式碼 Diff、測試／品質關卡與人工決策 | P1 |
| UX-04 | 工作階段可暫停、恢復、重新執行失敗階段；防止套用過期結果 | P1 |
| OUT-01 | 產出人類可讀報告與機器可讀的 Findings、Decisions、Evidence、Run Manifest | P0 |
| OUT-02 | 每項結果有來源、適用範圍、信心、修正、驗證和最後狀態 | P0 |
| OUT-03 | 可輸出與分享去敏感化的 Demo／驗證報告，不暴露公司原始碼或憑證 | P1 |

## 4. 重要決策演算法（不依賴任何工具）

對每一項 Rule × 實際使用範圍 × Environment／Profile／Mapper：

1. **鎖定版本**：查明來源／目標的實際 artifact 與 framework 版本。
2. **確認命中**：比對專案是否有使用相關功能、API 或行為路徑；未命中不產生自動修正。
3. **解析來源有效設定**：收集配置檔、環境／啟動覆寫、Bean 客製化及 Runtime Probe；記錄來源和可見性。
4. **套用來源預設值**：僅在已確認沒有其他生效覆寫時，才以該版本 Knowledge Rule 的預設值補足。
5. **解析目標有效設定**：以遷移後實際設定和目標框架行為推導／測試。
6. **比較行為契約**：相同則 `NO_CHANGE`；不一致則生成局部最小修正候選；不足以判定則 `UNKNOWN`。
7. **建立候選修正**：列出影響範圍、風險、替代方案、預期行為及相對應驗證。
8. **隔離套用與驗證**：執行測試；產生 Evidence；差異需修正或明確簽核。

> 兩個不可混淆的概念：`NOT_CONFIGURED` 必須有充分掃描證據；`NOT_OBSERVED` 只代表目前看不到，不能直接採預設值。對 Spring Boot 等外部化配置，正確優先順序需依該版本框架規則解析。

## 5. Jackson `null` → Java primitive `int` 驗證範例

**術語**：此案例為反序列化（deserialize），不是序列化（serialize）。  
**已確認的套件預設差異**：Jackson 2 `FAIL_ON_NULL_FOR_PRIMITIVES=false`；Jackson 3 `true`。但專案可能透過 Mapper、Customizer、Profile 等改變有效行為。

### 判斷矩陣

| 來源實際生效情境 | 來源行為 | 目標初始行為（假定使用 Jackson 3 預設） | 處理 |
|---|---|---|---|
| 沒有任何覆寫，確定使用 Jackson 2 預設 | 對 JSON `null` 產生 Java `0` | 拋出例外 | 使目標行為回到 `0`，並驗證 |
| 已明確設定 `false` 且確實生效 | `0` | 拋出例外 | 保留該設定語意，轉寫為正確的目標設定或局部轉換 |
| 已明確設定 `true` 且確實生效 | 拋出例外 | 拋出例外 | 一般不需為此項修改，但須確認目標 Mapper |
| 設定檔 `true`，後續 Bean 自訂覆寫為 `false` | `0` | 未知 | 以實際生效 Mapper 為準，不能只讀設定檔 |
| 部分 Profile `true`、部分 `false` | 依環境不同 | 依環境不同 | 每個環境獨立比較，不得全域套設定 |
| 無法取得生產環境配置 | 未知 | 未知 | `UNKNOWN`；補取觀測或人工審核 |
| 同時存在 Jackson 2 `ObjectMapper` 與 Jackson 3 `JsonMapper` | 依呼叫路徑 | 依呼叫路徑 | 先解析實際使用者／路徑；不可只看 classpath |

### 最小 Golden Cases

1. `{"quantity": null}` → Java `int quantity`：比對接受／拒絕、值、例外與 HTTP 錯誤映射。
2. `{}`（缺欄位）：獨立驗證，**不得假定**與明確 JSON `null` 等價。
3. `{"quantity": 0}`：正常零值不得誤判為 null。
4. `{"quantity": ""}`／型別錯誤：按現有契約決定是否納入比較。
5. 每個相關 Profile、Mapper／Converter／`@RequestBody` 路徑都要有可對應的案例。

**重要約束**：Spring Boot 4 的 `spring.jackson.use-jackson2-defaults=true` 是「使 auto-configured JsonMapper 盡量對齊 Jackson 2 預設」的候選策略，不是保證等價的通用修復，更不是看到 Jackson 3 就強制加上的設定。

## 6. 核心資料契約（Schema 概念）

無論最終採 JSON、YAML、資料庫或其他格式，都必須可表示以下六種獨立資料；每個物件都有穩定 ID、Schema Version、時間戳及關聯 ID。

| 資料類別 | 必要欄位 | 用途 |
|---|---|---|
| `MigrationRun` | runId, sourceRevision, sourceVersions, targetVersions, environments, knowledgePackVersion, status | 一次可重現的升級執行 |
| `KnowledgeRule` | ruleId, appliesTo, changeKind, defaults, predicates, references, proposedChecks, reviewStatus | 版本差異與候選檢查／修正的知識 |
| `ConfigObservation` | observationId, scope, keyOrBehavior, observedValue, origin, precedence, effectiveStatus, evidenceRef | 實際配置與生效性證據 |
| `CompatibilityFinding` | findingId, ruleRef, usageRef, sourceEffective, targetEffective, assessment, confidence, evidenceRefs | 某專案特定情境的風險與判定 |
| `MigrationDecision` | decisionId, findingRefs, action, rationale, affectedScope, approval, patchRef | 修改／不修改／接受差異決策 |
| `VerificationEvidence` | evidenceId, runRef, testCase, baselineResult, targetResult, comparisonPolicy, status, artifactRefs | 可追溯的驗證結果 |

### 標準狀態與語義

- Finding：`NOT_APPLICABLE`／`NO_CHANGE`／`CHANGE_REQUIRED`／`UNKNOWN`／`REVIEW_REQUIRED`／`ACCEPTED_DEVIATION`。
- 執行：`NOT_STARTED`／`RUNNING`／`WAITING_APPROVAL`／`FAILED`／`COMPLETED`／`CANCELLED`。
- Gate：`PASS`／`FAIL`／`UNKNOWN`／`NOT_RUN`／`BLOCKED`；`NOT_RUN` 和 `UNKNOWN` **絕不等於 PASS**。
- 證據來源：`OFFICIAL_DOC`／`PROJECT_STATIC`／`RUNTIME_OBSERVATION`／`TEST_EXECUTION`／`HUMAN_APPROVAL`／`AGENT_INFERENCE`；需區分可證實與推測。

詳細機器可讀的 Jackson 規則樣本與測試案例見同目錄 `jackson-null-primitives.example.yaml`。示例是**資料模型與需求測試樣本**，不是可直接執行的 OpenRewrite Recipe。

## 7. 非功能性與企業環境需求

| ID | 需求 | 優先度 |
|---|---|---|
| NFR-01 | 無公開網路時仍可讀取本地 Knowledge Pack、分析原始碼與執行本地工具；若模型不可達，明確標示 Agent 能力不可用 | P0 |
| NFR-02 | 所有工具／知識／建置相依版本可鎖定且可匯出 manifest，支持內網封裝或鏡像 | P0 |
| NFR-03 | 不應自動上傳程式碼、設定、憑證或測試資料；外部模型／服務須依公司授權與資料治理政策 | P0 |
| NFR-04 | 秘密遮蔽、可審計操作、可撤回變更；提供讀取／寫入／執行工具的權限隔離 | P0 |
| NFR-05 | 斷線、測試失敗或中斷後，可在版本與輸入未改變時恢復；失效的證據必須重新產生 | P1 |
| NFR-06 | 模型、OpenRewrite、LSP、IDE 等執行能力可替換；Knowledge Pack 不攜帶特定廠商的必要依賴 | P0 |
| NFR-07 | 執行時間、偵測率、誤判、修復率、重跑穩定性等指標需收集；量化門檻待基準測試確立 | P1 |

## 8. 可驗收條件（Acceptance Scenarios）

| ID | 可重現情境 | 預期 |
|---|---|---|
| AT-01 | Jackson 2 未設定 null→primitive 行為 | 找到預設差異並建議保留原行為；測試成功 |
| AT-02 | Jackson 2 明確設定為 true | 不盲目添加「允許 null」的設定；維持例外行為 |
| AT-03 | 同一份設定在兩個 Profile 結果不同 | 產生兩個 Scope 的分析結果，不做一刀切全域修改 |
| AT-04 | Java 自訂 Mapper 覆寫 YAML 設定 | 依有效設定判斷；如無法確認則 UNKNOWN |
| AT-05 | 無法取得外部環境設定 | 不得標成「未設定」或 PASS |
| AT-06 | Jackson 2/3 並存且不同 Controller/Client 選用不同 Mapper | 各路徑分開驗證 |
| AT-07 | 目標版本編譯成功，但 JSON 行為不同 | Regression Gate 為 FAIL，禁止自動宣告完成 |
| AT-08 | 故意接受新的行為契約 | 需明確批准、紀錄差異及新測試 |
| AT-09 | 無外網且官方文件無法即時查詢 | 本地 Knowledge Pack 可完成有來源的差異分析 |
| AT-10 | Knowledge Rule 不適用指定 Patch 版或來源互相矛盾 | REVIEW_REQUIRED，不得捏造確定結論 |
| AT-11 | 升級後原始碼被手動變更 | 先前 Verification Evidence 標成過期並重新驗證 |
| AT-12 | 不使用 Claude Code，而換成另一個 Agent 或 CLI | 同一 Knowledge Rule 與驗收案例仍能使用 |
| AT-13 | AI 嘗試修改 Golden Expected Results 以通過測試 | 阻止或要求單獨人工核准；保留原基準 |
| AT-14 | 無法取得公司私有 Maven Artifact／Recipe | Preflight 明確 BLOCKED，並指出缺少的 Artifact |

## 9. 建議優先順序

**P0（第一個可驗證 PoC）**：Baseline、Jackson Rule、Effective Configuration、條件式決策、Golden Test、Quality Gate、離線 Knowledge Pack、Finding/Evidence 格式。  
**P1（期末展示完整體驗）**：視覺化階段、Artifact/Diff、人工審核、Knowledge 管理、報告、可恢復執行。  
**P2（平台擴充）**：更多版本與框架、Java LSP、跨服務契約測試、Recipe 管理、企業知識治理、其他 Agent Adapter。

## 10. 尚待決策，不阻礙本規格使用

1. 第一波覆蓋哪些公司共用技術組合及精確版本？
2. 需要掃描哪些環境／Profile？哪些外部設定能以安全方式取得？
3. 既有測試與 Golden Sample 的取得策略是什麼？哪些資料能離線使用？
4. 最終使用 CLI、VS Code Extension、Electron、Web，或多種前端？
5. 能否經核准使用 Claude 模型或企業模型 Gateway？若完全不能，Agent 能力如何替代？
6. 公司內部 Knowledge 維護者、審核流程、保密等級和發布機制為何？
7. 第一個 Demo 是否只支持單一模組及單一 Profile，後續再增加矩陣驗證？

## 11. 參考資料（知識來源，不是直接可執行的遷移規則）

- Jackson 3 `DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES`：https://javadoc.io/static/tools.jackson.core/jackson-databind/3.0.0/tools.jackson.databind/tools/jackson/databind/DeserializationFeature.html
- Jackson 2 同項預設值：https://fasterxml.github.io/jackson-databind/javadoc/2.0/com/fasterxml/jackson/databind/DeserializationFeature.html
- Spring Boot 4 Jackson 配置與 Mapper：https://docs.spring.io/spring-boot/reference/features/json.html
- Spring Boot 外部化設定順序：https://docs.spring.io/spring-boot/reference/features/external-config.html
- Spring Boot 4 Migration Guide：https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide

