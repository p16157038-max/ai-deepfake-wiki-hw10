/* Offline portal enhancements. Source and evidence JSON are embedded by the renderer. */
(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const read = (id) => { const n = byId(id); return n ? JSON.parse(n.textContent) : null; };
  const make = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
  const anchor = (href, text, cls = "subtle-link") => { const n = make("a", text, cls); n.href = href; return n; };
  const wikiHref = (path, claim) => `wiki.html#page=${encodeURIComponent(path)}${claim ? `&claim=${encodeURIComponent(claim)}` : ""}`;
  const params = () => new URLSearchParams(location.hash.slice(1));
  const pages = read("wiki-data");
  if (pages) {
    const search = byId("wiki-search"), list = byId("wiki-list"), article = byId("wiki-article");
    let selected;
    const navigation = () => {
      const value = search.value.normalize("NFKC").toLocaleLowerCase("zh-Hant").trim();
      const matching = pages.filter((p) => [p.id, p.title, p.summary, ...p.sources, ...p.claims.map((c) => `${c.id} ${c.text}`)].join(" ").normalize("NFKC").toLocaleLowerCase("zh-Hant").includes(value));
      list.replaceChildren();
      for (const [kind, label] of [["concept", "六個綜合主題"], ["source", "逐篇官方來源"]]) {
        const group = matching.filter((p) => p.kind === kind);
        if (!group.length) continue;
        list.append(make("p", label, "nav-group-title"));
        for (const p of group) {
          const a = anchor(wikiHref(p.path), undefined, "wiki-nav-link");
          a.append(make("span", p.id), document.createTextNode(p.title));
          if (p.path === selected?.path) a.setAttribute("aria-current", "page");
          list.append(a);
        }
      }
      if (!matching.length) list.append(make("p", "沒有符合的頁面，請改用較短關鍵字。", "meta"));
      byId("wiki-result-count").textContent = `${matching.length} 頁符合，共 ${pages.length} 頁`;
    };
    const show = (shouldScroll = false) => {
      selected = pages.find((p) => p.path === params().get("page")) || pages.find((p) => p.kind === "concept");
      // HTML is compiled from local, escaped source Markdown; no user input enters it.
      article.innerHTML = selected.html;
      document.title = `${selected.title}｜知識 Wiki`;
      navigation();
      const claim = params().get("claim");
      const target = claim ? byId(`claim-${claim}`) : null;
      if (target) { target.classList.add("is-highlighted"); target.scrollIntoView({ block: "center" }); }
      else if (shouldScroll && innerWidth <= 720) article.scrollIntoView({ block: "start" });
    };
    search.addEventListener("input", navigation);
    search.addEventListener("search", navigation);
    addEventListener("hashchange", () => show(true));
    show();
  }

  const trace = read("trace-data");
  if (trace) {
    const select = byId("trace-select"), panel = byId("trace-panel");
    const draw = (id) => {
      const item = trace.find((x) => x.slide === id) || trace.find((x) => x.slide === "s06") || trace[0];
      select.value = item.slide;
      panel.replaceChildren();
      const header = make("div", undefined, "trace-title");
      const top = make("div", undefined, "trace-title-top");
      top.append(make("span", item.slide.toUpperCase(), "id-chip"), make("span", "實際教學頁面", "small-label"));
      header.append(top, make("h3", item.title));
      if (item.lead) header.append(make("p", item.lead));
      const actions = make("div", undefined, "trace-links");
      actions.append(anchor(`deck.html#${item.slide}`, "打開這張投影片 ↗", "button button-small"), anchor(item.draft_path, "逐頁稿原檔 ↗"));
      header.append(actions);
      panel.append(header);

      const path = make("div", undefined, "trace-path");
      const stage1 = make("div", undefined, "trace-stage");
      stage1.append(make("span", "01 / 先讀知識"), make("b", "使用的 Wiki 頁"));
      for (const p of item.pages) stage1.append(anchor(wikiHref(p.path), `${p.id} · ${p.title} ↗`));
      const stage2 = make("div", undefined, "trace-stage");
      stage2.append(make("span", "02 / 查詢與整理"), make("b", "保存的問題與證據卡"));
      for (const q of item.queries) stage2.append(anchor(q.card_path, `${q.id} · ${q.question} ↗`));
      const stage3 = make("div", undefined, "trace-stage");
      stage3.append(make("span", "03 / 寫成教材"), make("b", "引用對應到這一頁"), anchor(`deck.html#${item.slide}`, `${item.slide.toUpperCase()} · 開啟實際 HTML ↗`));
      path.append(stage1, stage2, stage3); panel.append(path);

      panel.append(make("h3", "主張、原文位置與日期", "trace-subtitle"));
      const claims = make("div", undefined, "trace-claims");
      for (const claim of item.claims) {
        const box = make("article", undefined, "trace-claim");
        const meta = make("div", undefined, "claim-meta");
        meta.append(make("span", claim.id, "id-chip"), make("span", `來源日期 ${claim.date}`, "small-label"));
        box.append(meta, make("p", claim.text), make("div", `原文位置：${claim.location || claim.locator || "未另列"}`, "claim-location"));
        const cite = make("div", undefined, "source-cite");
        cite.append(make("span", claim.source_id), anchor(claim.url, `${claim.source_title} ↗`));
        box.append(cite, make("p", claim.issuer, "meta"));
        const links = make("div", undefined, "trace-links");
        links.append(anchor(wikiHref(`sources/${claim.source_id}.md`, claim.id), "Wiki 來源與限制 ↗"), anchor(claim.raw_path, "封存節錄 ↗"));
        box.append(links); claims.append(box);
      }
      panel.append(claims, make("h3", "當時問了什麼，整理出什麼？", "trace-subtitle"));
      const queries = make("div", undefined, "query-list");
      for (const q of item.queries) {
        const box = make("article", undefined, "query-card");
        box.append(make("span", q.id, "id-chip"), make("h4", q.question), make("p", q.answer));
        const details = make("details");
        details.append(make("summary", "查看保存的證據卡摘要"), make("p", q.card_answer));
        const links = make("div", undefined, "trace-links");
        links.append(anchor(q.query_path, `${q.id} 查詢紀錄 ↗`), anchor(q.card_path, `${q.id} 證據卡檔案 ↗`));
        box.append(details, links); queries.append(box);
      }
      panel.append(queries);
      if (item.note) { const n = make("p", item.note, "record-boundary"); panel.append(n); }
    };
    select.addEventListener("change", () => { history.replaceState(null, "", `#slide=${select.value}`); draw(select.value); });
    addEventListener("hashchange", () => { const id = params().get("slide"); if (id) draw(id); });
    draw(params().get("slide") || select.value);
  }

  const revealNode = () => {
    if (!location.hash.startsWith("#detail-")) return;
    const node = byId(location.hash.slice(1));
    if (node?.tagName === "DETAILS") node.open = true;
  };
  addEventListener("hashchange", revealNode);
  revealNode();
})();
