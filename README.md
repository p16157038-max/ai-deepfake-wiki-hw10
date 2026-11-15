# AI 深偽與社群詐騙教學 LLM Wiki

第十週作業1110；成大 P16157038 系統碩一 陳世豐。

先開 `index.html`，選「開始上課」「閱讀 Wiki」或「看工作流程」。`deck.html` 是十四頁教學簡報，直接用瀏覽器雙擊可讀；方向鍵換頁，情境題可選答案看解說。免登入、免金鑰，靜態成果不需伺服器維持連線。

此 LLM Wiki 是 Codex 研究代理逐篇讀官方資料、編寫來源及綜合知識、保留連結與日誌的成果；不是把普通搜尋功能假稱為聊天模型。網頁搜尋只做本機關鍵字篩選。新增知識時需 coding agent 依 `AGENTS.md` 讀來源並寫入；重跑以下腳本只重現資料與輸出，不會自行呼叫 LLM。

```text
python tools/wiki.py lint
python tools/wiki.py query Q01 "深偽 仿聲 基本概念"
python tools/render.py
python tools/check.py
```

實作順序和每階段證據在 `evidence/`、Git 提交、`wiki/log.md`；來源清單位於 `raw/manifest.json`，來源擷取不可修改。完整官方網頁快取留在作者工作區，公開 raw 為有出處、日期、短摘與限制的封存節錄，不冒充全文。查詢產生的段落紀錄在 `queries/`；投影片用的證據卡在 `cards/`。

需求摘要尚待本人確認，見 `planning/discussion.md`。使用者在缺席期間明確允許 AI 依暫定方案繼續，但沒有把 AI 自擬方案寫成已獲本人核准。先完成可審閱版本，回來確認後才消除這項待辦。

## 重跑瀏覽器檢查（僅開發者）

既有成果直接開啟不需要安裝任何套件。若要重新執行瀏覽器測試，另外安裝 Node.js、Playwright 與 Chrome，再跑 `node tools/browser_check.cjs`；預設測本機HTML，`HW10_TEST_URL` 可指定已發布的 deck.html。請用隔離的 headless profile，不使用個人登入資料。實際本機與公開網站紀錄分別保存在 `evidence/browser-local.json` 與 `evidence/browser-checks.json`。

.gitattributes 固定文字檔 LF，讓 Windows checkout 不會改變已封存 raw 的 SHA256。
