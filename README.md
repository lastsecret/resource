# 學習手記

純靜態 HTML 網站，直接用瀏覽器開啟 `index.html` 即可。無須安裝套件或建置。

- `index.html`：主題索引
- `mattpocock.html`：27 個官方 README skills、用途與社群流程
- `superpowers.html`：15 個官方 README skills、用途與社群流程
- `claude-code.html`：Claude Code CLI 命令、參數、slash commands 與 MCP / Plugin 子指令
- `claude-code.js`：指令搜尋、結果計數與搜尋快捷鍵
- `styles.css`：共用樣式與行動版版面
- `notes.js`：主題搜尋、skill 搜尋與分類篩選（不影響無 JavaScript 時閱讀）

## 新增主題

1. 新增獨立 HTML 檔，沿用共用樣式、頁首與頁尾。
2. 在 `index.html` 的 `#topics` 內複製一個 `.topic` 區塊。
3. 更新 `href`、主題名稱、摘要、標籤與 `data-topic` 搜尋關鍵字。
4. 更新首頁主題數量。

## 更新 skills 筆記

依頁尾來源重新核對 README 的 Reference 清單與分類；更新用途、數量（HTML；搜尋總數由 notes.js 自動計算）、查閱日期。第三方流程應保留來源，與官方功能分開描述。

可部署至 GitHub Pages 等靜態主機。所有內部連結均為相對路徑。
