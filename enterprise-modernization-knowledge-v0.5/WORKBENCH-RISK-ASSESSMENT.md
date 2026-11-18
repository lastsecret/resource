# Workbench UI 技術風險與決策 — v0.3

> 此文件是實作風險分析，不強制 Electron、VS Code、Tauri、Web 或 Claude Agent SDK。

## 決策結論

- **高風險的不是 UI 元件，而是 Agent Workflow 的可控性、恢復性與安全性。**
- **不得**把官方 Plugin 的 Markdown/Agent 輸出當成穩定的機器 API；需用 Adapter 和版本鎖定。
- 第一期不做完整 IDE，也不承諾取代 Claude Code CLI 的所有多 Agent 功能。
- 期末展示最合理的最小產品：**GUI 做專案啟動／檢視階段／閱讀 Artifacts／比對 Diff／查看 Quality Gates；複雜核准先保留原生 Claude Code**。

## 技術選擇與風險（主觀評估，非測得機率）

| 選項 | 產品面積 | 整合風險 | 初期用途 |
|---|---|---|---|
| A. 只讀 Web Dashboard + 原生 Claude Code CLI | 低 | 低～中 | **優先做**：快速證明階段與 Evidence 展示能力 |
| B. Web UI / VS Code Webview + CLI Adapter（安全受控操作） | 中 | 中 | 使用者點按啟動單階段，複雜問答回 CLI |
| C. VS Code Extension + 原生 Claude Code 整合 | 中 | 中～高 | 後期日常開發體驗，避免重做 Editor |
| D. Electron 全功能 GUI + Agent SDK + 人工核准路由 | 高 | 高 | 僅在可續跑/核准 Spike 成功後考慮 |
| E. 自製 IDE / 自製 Workflow Engine | 非常高 | 非常高 | 不建議期末 PoC |

## 五個風險熱點

1. **階段控制 / 非決定性輸出**：官方 Plugin 的斷點、Command、子 Agent、Workflow 與 Live Pane 可能隨版本變；外層必須保存階段狀態及 Artifact 校驗，不要單靠對話文字。
2. **AskUserQuestion 與批准**：Preflight、Pilot、Brief、Diff、Deviation、Final Sign-off 可能要求不同互動，不能用無條件 approve；GUI 要處理 Session ID、事件、工具權限與 Resume。
3. **中斷與續跑**：多 Agent、背景 Workflow、檔案變更、長時間 Maven Job 必須能以 Artifact + Git SHA 恢復；需實際斷電/kill 測試。
4. **檔案與執行安全**：來源只讀、候選改動隔離、拒絕跨工作區 shell 寫入、遮罩 secret；若在受限公司電腦使用 Claude，要有核准網關。
5. **資料契約漂移**：固定 Plugin commit/版本；以 Adapter 解析官方 Artifacts，儲存原始檔與標準化資料；無法辨識時顯示 UNKNOWN，不猜 PASS。

## P0 Spike：先證明能接，不是先做 UI

- [ ] 以離線可安裝的 Claude Code + 官方 Plugin，原生 CLI 完成 preflight → assess → uplift pilot → verify 中最小路徑。
- [ ] CLI 或 SDK adapter 可**受控啟動單一階段**，逐步接收原始事件與輸出，取得 Session ID。
- [ ] 遇到需要人回答的 preflight 或批准，UI **不得自動替使用者回答**。先證明能可靠暫停、由人批准、恢復原 Session。
- [ ] 強制終止程序後，保留原本 Artifact，重啟可顯示正確階段與原始變更。
- [ ] 測試 prompt injection / tools permission，確認 Source Repository 無法被改寫；shell 的寫入權限也須納入保護。
- [ ] 當官方 Plugin 升級造成輸出格式變化，Adapter 回報 ERROR/UNSUPPORTED，而不是顯示舊 PASS。

## 停損／轉換條件（Go / No-Go）

- 若**階段啟動與只讀 Artifact** 穩定，先交付 A（只讀 UI）；依此可做完整 Demo。
- 若**人工核准和 Resume** 經過 Kill/Restart 測試穩定，再開 B（GUI 控制單階段）。
- 若 Agent SDK 無法正確承接官方特殊 Workflow，**不要 Fork 全流程硬改**；暫保留原生 Claude Code 互動，GUI 只顯示狀態與資料。
- 不以全功能 GUI 成功作為 Knowledge Pack / Quality Gate 的交付前提。

## 第一版畫面（不做 IDE）

1. Workspace Picker：選擇 Legacy Source、目標 Spring Boot、Knowledge Pack 版本。
2. Stage Timeline：INTENT → PREFLIGHT → ASSESS → DELTA → PILOT → VERIFY → REPORT；狀態由檔案與證據計算。
3. Artifacts：瀏覽官方 Markdown / HTML / JSON，顯示來源與最近更新。
4. Diff Viewer：呼叫 Git diff/檔案比對，顯示新增/刪除及審核註記。
5. Evidence Panel：Build、Tests、Regression、Unknown、Reviewer decision。
6. Open in Claude Code：複雜 Agent 交互先回到原生 CLI。

## 實作建議（不是強制架構）

- 後端提供 `start_stage`, `list_artifacts`, `get_run`, `get_findings`, `get_diffs`, `record_approval` 等清楚 API；不讓 UI 直接依賴 Plugin 路徑。
- 標準事件：`RUN_STARTED`, `STAGE_STARTED`, `STAGE_WAITING_HUMAN`, `ARTIFACT_CREATED`, `GATE_FAILED`, `STAGE_COMPLETED`, `RUN_INTERRUPTED`。
- 工作執行狀態與品質認證狀態**分離**。例如 Workflow 完成不代表 Quality Gate PASS。
- 第一版無需 Monaco 的 IDE 編輯功能；展示 Markdown Viewer + Git Diff 就夠。
- Dashboard 可讀取既有 `analysis/`、`modernized/`，但避免誤把 mtime 新當作證據新；需對照 source SHA, target SHA, artifact hash, knowledge-pack version。

## 官方能力的實際依據

- Official Code Modernization README: https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-modernization/README.md
- Official Uplift Command: https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-modernization/commands/modernize-uplift.md
- API/SDK/CLI 選擇需以專案實際使用版本可用的參數驗證，不能假設所有 CLI/SDK 都支援完全一樣的 Workflow 或權限事件。
