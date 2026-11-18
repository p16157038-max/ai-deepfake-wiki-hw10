"""Render the offline practice page from authored, traceable teaching content.

This renderer preserves teaching text, resolves existing manifest citations, and
does not retrieve sources, generate new teaching claims, or report test results.
"""
import html
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def esc(value):
    return html.escape(str(value), quote=True)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def anchor(url, label, css=""):
    return f'<a href="{esc(url)}" class="{esc(css)}">{esc(label)}</a>'


def wiki_url(path, claim=None):
    path = path.removeprefix("wiki/")
    return "wiki.html#page=" + quote(path, safe="") + ("&claim=" + quote(claim, safe="") if claim else "")


def require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")


def local_file(path):
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or not resolved.is_file():
        raise ValueError("Missing or invalid local reference: " + path)


def validate(data, pages, claims):
    require_text(data.get("title"), "title")
    require_text(data.get("description"), "description")
    cases = data.get("cases", [])
    if [case.get("id") for case in cases] != [f"P{i:02}" for i in range(1, 6)]:
        raise ValueError("Practice must contain exactly P01–P05 in order")
    for case in cases:
        cid = case["id"]
        for key in ("title", "category", "context", "question", "takeaway"):
            require_text(case.get(key), cid + "." + key)
        options = case.get("options", [])
        if len(options) != 3 or sum(option.get("correct") is True for option in options) != 1:
            raise ValueError(cid + " must have three options and one recommended first action")
        for option in options:
            require_text(option.get("text"), cid + ".option.text")
            require_text(option.get("feedback"), cid + ".option.feedback")
            if not isinstance(option.get("correct"), bool):
                raise ValueError(cid + ".option.correct must be boolean")
        if len(case.get("lesson", [])) != 4:
            raise ValueError(cid + " must have four authored learning steps")
        for step in case["lesson"]:
            require_text(step.get("title"), cid + ".lesson.title")
            require_text(step.get("text"), cid + ".lesson.text")
        if not case.get("citations"):
            raise ValueError(cid + " requires traceable citations")
        for citation in case["citations"]:
            path = citation["wiki"].removeprefix("wiki/")
            if path not in pages:
                raise ValueError(cid + " cites unknown Wiki " + path)
            allowed = {claim["id"] for claim in pages[path].get("claims", [])}
            if not citation.get("claims"):
                raise ValueError(cid + " must identify citation claims")
            for claim in citation["claims"]:
                if claim not in claims or claim not in allowed:
                    raise ValueError(cid + " has invalid claim " + claim)
        for query in case.get("query_ids", []):
            local_file("queries/" + query + ".json")
        for path in case.get("card_paths", []):
            local_file(path)
        explain = case.get("explain", {})
        require_text(explain.get("prompt"), cid + ".explain.prompt")
        require_text(explain.get("reference"), cid + ".explain.reference")
        if len(explain.get("checkpoints", [])) != 3:
            raise ValueError(cid + " requires three authored self-check criteria")
        for criterion in explain["checkpoints"]:
            require_text(criterion, cid + ".explain.checkpoint")


def render_case(case, claims):
    cid = case["id"]
    options = "".join(
        f'<button type="button" class="practice-option" data-correct="{str(option["correct"]).lower()}" data-option-index="{i}" aria-pressed="false"><span class="option-letter" aria-hidden="true">{"ABC"[i]}</span><span>{esc(option["text"])}</span><span class="option-arrow" aria-hidden="true">↗</span></button>'
        for i, option in enumerate(case["options"])
    )
    rationales = "".join(
        f'<li class="choice-rationale" data-choice-index="{i}"><span class="rationale-marker">{"ABC"[i]}</span><div><p class="rationale-label">{"建議的第一步" if option["correct"] else "為什麼先不選這個"}<span class="selected-choice" hidden> · 你的選擇</span></p><h4>{esc(option["text"])}</h4><p>{esc(option["feedback"])}</p></div></li>'
        for i, option in enumerate(case["options"])
    )
    steps = "".join(
        f'<li><span class="lesson-number" aria-hidden="true">{i:02}</span><div><h4>{esc(step["title"])}</h4><p>{esc(step["text"])}</p></div></li>'
        for i, step in enumerate(case["lesson"], 1)
    )
    citations = ""
    seen = set()
    for citation in case["citations"]:
        label = citation.get("label") or "閱讀相關知識"
        citations += f'<div class="practice-citation"><p>{anchor(wiki_url(citation["wiki"]), label + " →", "text-link")}</p><ul>'
        for claim_id in citation["claims"]:
            if claim_id in seen:
                continue
            seen.add(claim_id)
            claim = claims[claim_id]
            citations += f'<li><span class="id-chip">{esc(claim_id)}</span><span>{esc(claim["text"])}</span><div>{anchor(wiki_url(citation["wiki"], claim_id), "Wiki 主張")}{anchor(claim["url"], claim["source_title"] + " ↗")}</div></li>'
        citations += "</ul></div>"
    trace_links = "".join(anchor("queries/" + query + ".json", query + " 查詢") for query in case.get("query_ids", []))
    trace_links += "".join(anchor(path, Path(path).stem + " 證據卡") for path in case.get("card_paths", []))
    explain = case["explain"]
    criteria = "".join(f'<li>{esc(item)}</li>' for item in explain["checkpoints"])
    reasoning = f'''<section class="lesson-section practice-reasoning"><div class="lesson-heading"><p class="eyebrow">03 / 換你說明理由</p><h3>先寫自己的判斷，再對照。</h3></div><label for="practice-reason">{esc(explain['prompt'])}</label><textarea id="practice-reason" rows="3" maxlength="600" aria-describedby="practice-reason-help" placeholder="用這個虛構情境作答即可。"></textarea><p id="practice-reason-help" class="reason-help">不用填真實姓名、帳號或認證碼。文字只留在本頁，不送出，也不自動評分。</p><details class="reason-reference"><summary>展開參考判準與示範回答</summary><ul>{criteria}</ul><p class="reason-example"><b>示範回答：</b>{esc(explain['reference'])}</p></details></section>'''
    return f'''<article class="practice-case" data-case="{esc(cid)}" aria-labelledby="practice-case-title">
<header class="practice-case-heading"><div class="case-eyebrow"><span class="id-chip">{esc(cid)}</span><span>{esc(case['category'])}</span></div><h2 id="practice-case-title" tabindex="-1">{esc(case['title'])}</h2><p class="case-learning-goal"><b>這題要學會：</b>{esc(case.get('lesson_goal', '讀懂情境中的要求，選出第一步，再看完整處理流程。'))}</p></header>
<section class="practice-scene" aria-labelledby="scene-heading"><div class="scene-chrome"><span><i aria-hidden="true"></i> 情境卡</span><span class="simulation-label">教學模擬</span></div><div class="scene-person"><span class="scene-avatar" aria-hidden="true">?</span><div><h3 id="scene-heading">如果是你遇到這件事</h3><p>以下為虛構情境，沒有真實音訊或影像</p></div></div><div class="scene-message"><p>{esc(case['context'])}</p></div><p class="scene-footer"><span aria-hidden="true">↳</span> 先看對方要你做什麼，再決定下一步。</p></section>
<section class="practice-question" aria-labelledby="practice-question-title"><p class="eyebrow">01 / 選一個第一步</p><h3 id="practice-question-title">{esc(case['question'])}</h3><p class="question-hint">點選後會顯示理由與四步處理流程；可以重新選擇。</p><div class="practice-options">{options}</div></section>
<div id="practice-feedback" class="practice-feedback" role="status" aria-live="polite" aria-atomic="true" tabindex="-1" hidden><span class="feedback-icon" aria-hidden="true"></span><div><h3 class="feedback-title"></h3><p class="feedback-text"></p></div></div>
<div id="practice-lesson" class="practice-lesson" hidden><section class="lesson-section"><div class="lesson-heading"><p class="eyebrow">02 / 接下來怎麼做</p><h3>帶著情境，走完四個步驟。</h3></div><ol class="practice-steps">{steps}</ol><aside class="practice-takeaway"><span class="tiny-label">這一題，記住這件事</span><p>{esc(case['takeaway'])}</p></aside><details class="choice-explanations"><summary>展開三個選項的完整理由</summary><ol class="choice-rationales">{rationales}</ol></details></section>{reasoning}<section class="lesson-section practice-evidence"><div class="lesson-heading"><p class="eyebrow">04 / 想知道依據</p><h3>回到 Wiki，也能直接看官方來源。</h3><p>下列主張支持本題的判斷與處理步驟；情境本身是教學模擬。</p></div>{citations}<details class="practice-trace"><summary>查看查詢與證據卡</summary><div class="trace-links">{trace_links}</div></details></section></div>
<footer class="practice-case-footer"><button type="button" class="button button-small" data-practice-reset>重練這個情境 ↺</button><button type="button" class="button button-primary button-small" data-practice-next>換下一個情境 →</button></footer></article>'''


def build():
    data = load("teaching/practice.json")
    manifest = load("raw/manifest.json")["sources"]
    pages = {page["path"]: page for page in load("wiki/catalog.json")["pages"]}
    claims = {claim["id"]: {**claim, "url": source["url"], "source_title": source["title"]} for source in manifest for claim in source["claims"]}
    validate(data, pages, claims)
    payload = [{"id": case["id"], "title": case["title"], "options": case["options"], "html": render_case(case, claims)} for case in data["cases"]]
    options = "".join(f'<option value="{case["id"]}">{case["id"]} · {esc(case["title"])}</option>' for case in data["cases"])
    case_buttons = []
    for i, case in enumerate(data["cases"]):
        current_attr = ' aria-current="true"' if i == 0 else ""
        case_buttons.append(f'<button type="button" class="practice-case-tab" data-practice-case="{case["id"]}"{current_attr}><span class="case-tab-number">{i + 1:02}</span><span><span class="case-tab-category">{esc(case["category"])}</span><b>{esc(case["title"])}</b><span class="case-attempted" hidden>已練習</span></span><span class="case-tab-arrow" aria-hidden="true">↗</span></button>')
    case_list = "".join(case_buttons)
    nav_links = []
    for key, url, name in [("home", "index.html", "首頁"), ("deck", "deck.html", "開始上課"), ("practice", "practice.html", "情境練習"), ("wiki", "wiki.html", "知識 Wiki"), ("evidence", "evidence.html", "證據對照"), ("workflow", "workflow.html", "製作流程")]:
        current_attr = ' aria-current="page"' if key == "practice" else ""
        nav_links.append(f'<a href="{url}"{current_attr}>{name}</a>')
    nav = "".join(nav_links)
    css = (ROOT / "assets/portal.css").read_text(encoding="utf-8") + "\n" + (ROOT / "assets/practice.css").read_text(encoding="utf-8")
    js = (ROOT / "assets/practice.js").read_text(encoding="utf-8")
    safe_data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    output = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{esc(data['description'])}"><title>{esc(data['title'])}｜先查證</title><style>{css}</style></head><body class="portal-page practice-page"><a class="skip-link" href="#main">跳至主要內容</a><header class="site-header"><div class="header-inner"><a class="brand" href="index.html"><span class="brand-symbol" aria-hidden="true">S<span>／</span></span><span>先查證<small>AI 深偽與社群詐騙</small></span></a><nav aria-label="主要導覽">{nav}</nav></div></header><main id="main"><section class="practice-hero wrap"><div><p class="eyebrow"><span class="status-dot"></span> 五個情境 · 一次練一個第一步</p><h1>{esc(data['title'])}</h1><p class="lead">{esc(data['description'])}</p><p class="practice-scope">這是教學模擬，沒有真實音訊或影像輸入，也不會自動偵測真假。練習重點是：看懂要求、說出理由、知道下一步。</p></div><aside class="practice-hero-note"><span aria-hidden="true">↗</span><p>不只選一個答案。<br><b>先說出理由，再對照判準。</b></p></aside></section><section class="practice-route wrap" aria-label="如何使用情境練習"><ol><li><span>01</span><b>先看情境</b></li><li><span>02</span><b>選第一步</b></li><li><span>03</span><b>看處理流程</b></li><li><span>04</span><b>說理由、看判準</b></li></ol></section><section class="practice-workspace wrap" aria-label="開始情境練習"><aside class="practice-sidebar"><div class="practice-sidebar-top"><p class="eyebrow">PRACTICE / 情境選單</p><h2>你想先練哪一個？</h2><p id="practice-progress" role="status" aria-live="polite" data-attempted="0" data-total="5">已練習 0 / 5</p><p class="practice-progress-note">計算本次開啟中作答過的情境數；不是分數，也不代表已學會。</p></div><div class="practice-select-wrap"><label for="practice-select">切換情境</label><select id="practice-select">{options}</select></div><nav class="practice-case-list" aria-label="五個練習情境">{case_list}</nav><a class="practice-back-to-course" href="deck.html">想先理解概念？回到 14 頁教學 →</a></aside><div id="practice-panel">{payload[0]['html']}</div></section><noscript><p class="wrap practice-noscript">互動練習需要 JavaScript。仍可閱讀 <a href="teaching/practice.json">五個情境與解說</a>，或開啟 <a href="deck.html">教學簡報</a>。</p></noscript></main><footer class="site-footer wrap"><div><b>看懂內容，也看得見依據。</b><p>成大 P16157038 系統碩一 陳世豐 · 第十週作業 1110</p></div><div class="footer-links">{anchor('deck.html', '教學簡報')}{anchor('wiki.html', '知識 Wiki')}{anchor('evidence.html', '成果與證據')}{anchor('README.md', '使用與重現')}</div><p class="footer-note">{esc(data.get('source_note', '本頁使用已核讀來源與既有 Wiki 的教學內容。'))} 離線閱讀與互動不需登入或 API 金鑰；官方原文連結需網路。練習不保證能辨識或防堵所有詐騙。</p></footer><script type="application/json" id="practice-data">{safe_data}</script><script>{js}</script></body></html>'''
    (ROOT / "practice.html").write_text(output, encoding="utf-8",newline="\n")
    print("Built practice.html: 5 authored teaching simulations, inline CSS/JS, manifest-resolved citations; no tests or approval claimed.")


if __name__ == "__main__":
    build()
