"""Render offline portal views from saved knowledge and evidence, without new facts.

No LLM calls, tests, source edits or approval actions occur in this renderer.
"""
import base64
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def esc(value):
    return html.escape(str(value), quote=True)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def link(url, label, css=""):
    return '<a href="' + esc(url) + '" class="' + css + '">' + esc(label) + '</a>'


def wiki_url(path, claim=None):
    return 'wiki.html#page=' + quote(path, safe='') + ('&claim=' + quote(claim, safe='') if claim else '')


def stamp(value):
    return str(value).replace('T', ' ').split('.')[0].replace('+00:00', '').replace('Z', '') + ' UTC' if value else '未記錄時間'


def data_script(name, value):
    safe = json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('&', '\\u0026')
    return f'<script id="{name}" type="application/json">{safe}</script>'


def shell(title, body, active='', data=''):
    css = (ROOT / 'assets/portal.css').read_text(encoding='utf-8')
    js = (ROOT / 'assets/portal.js').read_text(encoding='utf-8')
    nav = ''
    for key, url, name in [('deck', 'deck.html', '開始上課'), ('practice', 'practice.html', '情境練習'), ('wiki', 'wiki.html', '知識 Wiki'), ('evidence', 'evidence.html', '證據對照'), ('workflow', 'workflow.html', '製作流程')]:
        current = ' aria-current="page"' if key == active else ''
        nav += f'<a href="{url}"{current}>{name}</a>'
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="給在臺灣生活的初學者：透過教學簡報、知識 Wiki 與逐頁證據，認識 AI 深偽和社群詐騙。"><title>{esc(title)}｜AI 深偽與社群詐騙</title><style>{css}</style></head><body class="portal-page"><a class="skip-link" href="#main">跳至主要內容</a><header class="site-header"><div class="header-inner"><a class="brand" href="index.html"><span class="brand-symbol" aria-hidden="true">S<span>／</span></span><span>先查證<small>AI 深偽與社群詐騙</small></span></a><nav aria-label="主要導覽">{nav}</nav></div></header><main id="main">{body}</main><footer class="site-footer wrap"><div><b>看懂內容，也看得見依據。</b><p>成大 P16157038 系統碩一 陳世豐 · 第十週作業 1110</p></div><div class="footer-links">{link('practice.html','五個情境練習')}{link('AGENTS.md','協作規則')}{link('README.md','使用與重現')}{link('reflection.md','執行反思')}{link('evidence.html','成果與證據')}</div><p class="footer-note">來源查閱日 2026-11-15。這是教學與查證練習，不保證辨識或防堵所有詐騙。離線閱讀不需登入或 API 金鑰。</p></footer>{data}<script>{js}</script></body></html>'''


def markdown(text, current):
    def inline(line):
        line = esc(line)

        def convert(match):
            target = html.unescape(match[2])
            url = target
            if not target.startswith(('https://', 'http://')):
                resolved = ((ROOT / 'wiki' / current).parent / target.split('#')[0]).resolve()
                try:
                    url = wiki_url(resolved.relative_to((ROOT / 'wiki').resolve()).as_posix())
                except ValueError:
                    url = resolved.relative_to(ROOT.resolve()).as_posix()
            return f'<a href="{esc(url)}">{match[1]}</a>'

        line = re.sub(r'\[([^]]+)\]\(([^)]+)\)', convert, line)
        line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', line)

    result, in_list = [], False
    for line in text.splitlines():
        if line.startswith('- '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append('<li>' + inline(line[2:]) + '</li>')
            continue
        if in_list:
            result.append('</ul>')
            in_list = False
        if not line.strip():
            continue
        heading = re.match(r'^(#{1,4}) (.*)', line)
        result.append(f'<h{len(heading[1])}>{inline(heading[2])}</h{len(heading[1])}>' if heading else '<p>' + inline(line) + '</p>')
    return ''.join(result) + ('</ul>' if in_list else '')


def wiki_article(page, catalog, sources):
    kind = '跨來源知識' if page['kind'] == 'concept' else '逐篇來源整理'
    tags = ''.join(link(wiki_url(f'sources/{sid}.md'), sid, 'id-chip') for sid in page['sources'])
    original = markdown((ROOT / 'wiki' / page['path']).read_text(encoding='utf-8'), page['path'])
    claims = ''
    for claim in page.get('claims', []):
        cid = claim['id']
        source = sources[cid.split('-')[0]]
        claims += f'<li id="claim-{esc(cid)}" class="claim-item"><div><span class="id-chip">{esc(cid)}</span><span class="small-label">{esc(claim.get("locator", claim.get("location", "")))}</span></div><p>{esc(claim["text"])}</p><div class="trace-links">{link(wiki_url("sources/"+cid.split("-")[0]+".md"),"到來源頁核對 →","subtle-link")}{link(source["url"],"官方原文 ↗","subtle-link")}</div></li>'
    profile = ''
    if page['kind'] == 'source':
        source = sources[page['id']]
        date = source.get('published_at') or source.get('updated_at') or '原文未標示'
        limits = ''.join('<li>' + esc(x) + '</li>' for x in source.get('does_not_support', []))
        profile = f'''<section class="source-profile"><div class="profile-row"><span>發布機構</span><b>{esc(source['issuer'])}</b></div><div class="profile-row"><span>原文日期</span><b>{esc(date)}</b></div><div class="profile-row"><span>日期依據</span><p>{esc(source.get('date_basis','未另列'))}</p></div><div class="profile-row"><span>查閱日期</span><b>{esc(source['accessed_at'])}</b></div><div class="source-actions">{link(source['url'],'開啟官方原文 ↗','button button-small')}{link(source['raw_path'],'檢視封存節錄','text-link')}</div></section><aside class="boundary"><span class="small-label">閱讀界線</span><h2>這份來源不能用來證明什麼？</h2><ul>{limits}</ul></aside>'''
    related = [p for p in catalog if p['path'] != page['path'] and (p['path'] in page.get('related', []) or (page['kind'] == 'source' and p['kind'] == 'concept' and page['id'] in p['sources']))]
    related_html = ''.join(link(wiki_url(p['path']), p['title'] + ' ↗', 'related-link') for p in related)
    related_html = '<section class="related-section"><h2>延伸閱讀與來源回鏈</h2>' + related_html + '</section>' if related else ''
    return f'''<div class="article-tools"><span class="type-label">{kind}</span><span class="muted">Wiki 更新 {esc(page.get('updated','未標示'))}</span>{link('wiki/'+page['path'],'Markdown 原檔 ↗','subtle-link')}</div><div class="document">{original}</div>{profile}<section class="claim-section"><div class="section-heading"><div><span class="eyebrow">CHECK THE CLAIM</span><h2>這頁用到哪些依據？</h2></div><div class="chip-row">{tags}</div></div><p class="muted">主張編號連回來源與原文位置。下列文字是整理後的主張，並非原文逐字引文。</p><ol class="claim-list">{claims}</ol></section>{related_html}'''


def build_wiki(catalog, sources):
    pages = [{**p, 'html': wiki_article(p, catalog, sources)} for p in catalog]
    first = next(p for p in pages if p['kind'] == 'concept')
    initial = ''.join(link(wiki_url(p['path']), p['id']+' '+p['title'], 'wiki-nav-link') for p in pages)
    body = f'''<section class="wrap wiki-intro"><div><p class="eyebrow">KNOWLEDGE WIKI</p><p class="page-heading">先找到概念，再回到原文。</p><p class="intro-copy">來源與整理分開看。每頁保留主張編號、原文位置和適用界線，方便你追問「這句話從哪裡來」。</p></div><a class="inline-callout" href="evidence.html">想對照某張投影片？<b>看逐頁證據 →</b></a></section><div class="wrap wiki-layout"><aside class="wiki-sidebar"><div class="sidebar-top"><label for="wiki-search">搜尋知識或來源</label><div class="search-box"><span aria-hidden="true">⌕</span><input id="wiki-search" type="search" placeholder="例如：LINE、聲音、預錄" autocomplete="off"></div><p id="wiki-result-count" class="meta" aria-live="polite">{len(pages)} 頁可閱讀</p></div><nav id="wiki-list" aria-label="知識頁面">{initial}</nav><div class="sidebar-footer">{link('wiki/index.md','原始索引')}{link('wiki/log.md','處理日誌')}<p>這是本機關鍵字搜尋。新增知識由 AI 依協作規則核讀來源後編寫。</p></div></aside><article id="wiki-article" class="wiki-article" aria-live="polite">{first['html']}</article></div>'''
    (ROOT / 'wiki.html').write_text(shell('知識 Wiki', body, 'wiki', data_script('wiki-data', pages)), encoding='utf-8')


def build_home(catalog, sources, deck):
    chat = next(s for s in deck['slides'] if s['id'] == 's07')['chat'][0]
    steps = next(s for s in deck['slides'] if s['id'] == 's11')['items']
    cards = ''.join(f'<article class="verify-step"><span>{esc(x["title"])}</span><p>{esc(x["text"])}</p></article>' for x in steps)
    wave = ''.join(f'<i style="--bar:{h}px"></i>' for h in [10,22,35,17,42,29,48,25,15,33,42,20,12,26,38,18,30,14])
    body = f'''<section class="home-hero wrap"><div class="hero-copy"><p class="eyebrow"><span class="status-dot"></span> 給在臺灣生活的 GEN Z</p><h1>聲音很像，<br>也先別急著<span>相信。</span></h1><p class="hero-lead">一堂看懂 AI 深偽與社群詐騙的入門課。從熟悉的聲音、帳號與影片，練習先查證，再決定下一步。</p><div class="actions">{link('deck.html','開始 14 頁教學 ↗','button button-primary')}{link('practice.html','直接練習 5 個情境 ↗','button')}{link('evidence.html#slide=s06','看內容依據 →','text-link')}</div><p class="hero-note">14 頁課程含 2 題；情境練習區共 5 題（含原 2 題）</p></div><div class="signal-demo" aria-label="教學模擬：自稱室友的急迫轉帳訊息"><div class="demo-top"><span class="tiny-label">一段熟悉的聲音</span><span class="demo-chip">教學模擬</span></div><div class="contact-row"><span class="avatar" aria-hidden="true">?</span><div><b>{esc(chat['sender'])}</b><span>熟悉，不等於已驗證</span></div><span class="voice-mark" aria-hidden="true">◉</span></div><div class="voice-bubble"><div class="wave" aria-hidden="true">{wave}</div><p>「{esc(chat['text'])}」</p></div><div class="signal-flags"><span>急著付款</span><span>更換聯絡方式</span><span>不要告訴別人</span></div><div class="demo-answer"><span aria-hidden="true">↗</span><p><b>先離開對方的查證路線。</b>使用原本已知的電話，另外聯絡本人。</p></div><p class="demo-caption">情境來自第 7 頁練習，並非真實聊天室或受害者紀錄。</p></div></section><section class="wrap learning-route"><div class="section-heading"><div><p class="eyebrow">YOUR LEARNING PATH</p><h2>先學會判斷，再練習查證。</h2></div><p>三個入口，各自回答一個問題。</p></div><div class="entry-grid"><a href="deck.html" class="entry-card"><span class="entry-index">01 / LEARN</span><h3>遇到這種訊息，我該怎麼做？</h3><p>從概念、案例到情境題，學會辨識要求與選擇下一步。</p><b>進入教學簡報 ↗</b></a><a href="wiki.html" class="entry-card"><span class="entry-index">02 / UNDERSTAND</span><h3>我想再弄懂一個概念。</h3><p>從六個綜合主題閱讀，也能回看八份來源的日期與限制。</p><b>閱讀知識 Wiki ↗</b></a><a href="evidence.html" class="entry-card entry-evidence"><span class="entry-index">03 / VERIFY</span><h3>這些內容有什麼依據？</h3><p>選一張投影片，沿著知識頁、主張和來源逐項核對。</p><b>打開證據對照 ↗</b></a></div></section><section class="wrap fact-strip"><div><b>{len(sources):02}</b><span>份已核讀官方資料</span></div><div><b>{sum(p['kind']=='concept' for p in catalog):02}</b><span>頁跨來源知識</span></div><div><b>{len(deck['slides']):02}</b><span>頁有來源的教學</span></div><div><b>05</b><span>道可選模擬情境</span></div></section><section class="wrap verification-block"><div class="section-heading"><div><p class="eyebrow">TAKE IT WITH YOU</p><h2>把查證變成四個動作。</h2></div>{link('deck.html#s11','在課程裡練習 →','text-link')}</div><div class="verify-grid">{cards}</div><p class="meta">本課依官方建議整理的教學口訣；不是官方既有品牌，也不保證能阻擋所有詐騙。</p></section>'''
    (ROOT / 'index.html').write_text(shell('先查證，再決定', body), encoding='utf-8')


def trace_payload(catalog, sources, deck, trace):
    pages = {p['path']: p for p in catalog}
    claims = {c['id']: {**c, 'source_id': s['id'], 'source_title': s['title'], 'issuer': s['issuer'], 'date': s.get('published_at') or s.get('updated_at') or '原文未標示', 'url': s['url'], 'raw_path': s['raw_path']} for s in sources for c in s['claims']}
    slides = {s['id']: s for s in deck['slides']}
    result = []
    for row in trace['slides']:
        slide = slides[row['slide']]
        if row['title'] != slide['title']:
            raise ValueError('Trace title differs from actual slide: ' + row['slide'])
        queries = []
        for qid in row['queries']:
            q, card = load(f'queries/{qid}.json'), load(f'cards/{qid}.json')
            queries.append({'id': qid, 'question': q['question'], 'answer': q.get('answer', '未保存回答'), 'query_path': f'queries/{qid}.json', 'card_path': f'cards/{qid}.json', 'card_answer': card['answer'], 'pages': q['pages']})
        result.append({'slide': slide['id'], 'title': slide['title'], 'lead': slide.get('lead',''), 'note': slide.get('note',''), 'claims': [claims[c] for c in row['claim_ids']], 'pages': [{'path':p,'title':pages[p]['title'],'id':pages[p]['id']} for p in row['wiki_pages']], 'queries':queries, 'draft_path':f'drafts/{slide["id"]}.json'})
    return result


def screenshot_panel(number, title, preferred, fallback, alt, description):
    filename = preferred if (ROOT / 'evidence/screenshots' / preferred).exists() else fallback
    if filename and (ROOT / 'evidence/screenshots' / filename).exists():
        data = base64.b64encode((ROOT / 'evidence/screenshots' / filename).read_bytes()).decode('ascii')
        visual = f'<a href="evidence/screenshots/{esc(filename)}" class="proof-image-link"><img src="data:image/png;base64,{data}" alt="{esc(alt)}" loading="lazy"></a>'
        note = '保存的實際畫面；檢查範圍與日期以相應紀錄為準。' if filename == preferred else '這是 2026-11-15 保存的既有畫面，僅證明當時版本；新版介面需另行驗收。'
    else:
        visual = '<div class="proof-placeholder"><span aria-hidden="true">↗</span><p>直接核對本頁資料與執行紀錄。<br>新版畫面尚未保存，不以示意圖充當驗收。</p></div>'
        note = '沒有對應截圖時，保留實際資料與操作入口。'
    return f'<figure class="proof-card" id="proof-{number}"><div class="proof-title"><span>{number:02}</span><h3>{esc(title)}</h3></div>{visual}<figcaption><b>{esc(description)}</b><p>{note}</p></figcaption></figure>'


def build_evidence(catalog, sources, deck):
    browser_path = next(path for path in ['evidence/browser-checks-redesign.json', 'evidence/browser-local-redesign.json', 'evidence/browser-checks.json'] if (ROOT / path).exists())
    browser, checks, review = load(browser_path), load('evidence/checks.json'), load('evidence/independent-review.json')
    trace = trace_payload(catalog, list(sources.values()), deck, load('evidence/traceability.json'))
    options = ''.join('<option value="' + x['slide'] + '"' + (' selected' if x['slide']=='s06' else '') + '>' + f'{i:02} · ' + esc(x['title']) + '</option>' for i,x in enumerate(trace,1))
    reqs = [('01','有自己的知識主題','給在臺灣生活的初學者，認識深偽、社群冒用與查證。','index.html','看課程目的','主題與讀者清楚'),('02','先建立可累積的 Wiki','八份來源整理成六頁綜合知識，保留索引與日誌。','wiki.html','開啟知識庫','來源、概念互相連結'),('03','由 Wiki 製作教學 HTML','十四頁都有可追溯依據，另有情境題解說。','deck.html','開始教學','可瀏覽的教學成果'),('04','說清楚 Loop / Graph','交代資料如何取得、整理、檢查，錯誤退回最近節點。','workflow.html','看流程圖','有檢查點與停止條件'),('05','保存實際執行結果','程式、獨立審查與瀏覽器操作分開記錄，不互相代替。','#run-results','讀執行摘要','可查日期與原始結果'),('06','根據真實問題反思','來源擷取、報告產物依賴與換行 hash 保留真實處理紀錄。','reflection.md','讀執行反思','說明檢查如何前移')]
    requirements = ''.join(f'<article class="requirement-card"><span class="entry-index">要求 {n}</span><h3>{esc(t)}</h3><p>{esc(desc)}</p><span class="result-line">{esc(result)}</span>{link(url,action+" →","text-link")}</article>' for n,t,desc,url,action,result in reqs)
    cases = ''
    names = {'B01_deck_14_and_navigation':('十四頁與導覽','上一頁、下一頁與鍵盤切換。'),'B04_Wiki_citation_search_and_origin':('Wiki 引用與搜尋','從投影片開 Wiki、讀來源；搜尋命中與無結果。'),'B05_print_all_slides':('列印閱讀','列印樣式顯示全部十四頁。'),'B06_mobile_deck_and_Wiki':('390px 行動版模擬','題目、Wiki 可操作，沒有整頁水平溢出；非實體手機測試。'),'R01_navigation':('十四頁與導覽','實際操作上下頁按鈕與鍵盤。'),'R04_Wiki_source_search':('Wiki 來源、原文與搜尋','從第六頁開 Wiki，核對主張、官方原文與搜尋狀態。'),'R05_print':('列印閱讀','列印樣式顯示全部十四頁。'),'R06_home_navigation':('首頁與導覽入口','首頁可開啟教學、Wiki、證據與流程。'),'R07_evidence_all14_traces':('十四頁逐頁證據','核對實際標題、主張、查詢及來源連結。'),'R08_workflow_nodes_and_returns':('流程節點與局部回退','查看各節點、輸入輸出與失敗退回說明。'),'R09_evidence_results_readable':('執行結果可閱讀','頁面呈現保存的日期、範圍與原始紀錄入口。'),'R10_mobile_four_surfaces':('390px 四種頁面模擬','教學、Wiki、證據與流程無整頁水平溢出；非實體手機測試。')}
    for case in browser.get('cases', []):
        cid = case['id']
        if cid.startswith(('B02_s', 'R02_s')):
            title, detail = '第 '+str(int(cid.split('_')[1][1:]))+' 頁桌面閱讀與出處', '內容不溢出畫面，來源頁尾可見。'
        elif cid.startswith(('B03_', 'R03_')):
            title, detail = '情境題選項、回饋與重設', '實際選錯誤與正確答案，檢查解釋後再重新作答。'
        else:
            title, detail = names.get(cid, (case.get('name', cid), case.get('description', '檢查範圍與觀察結果請開啟保存紀錄。')))
        passed = case['status'] == 'passed'
        status = '通過' if passed else '未通過'
        cls = 'pass' if passed else 'fail'
        cases += f'<tr><td>{esc(title)}</td><td>{esc(detail)}</td><td><span class="test-status {cls}">{status}</span></td></tr>'
    summary = browser['summary']
    semantic = '沒有重大未解問題' if review.get('blocking_issues') == 0 else '仍有待處理問題'
    proofs = ''.join([screenshot_panel(1,'來源與 Wiki 對照','17_來源知識對照.png','15_Wiki與來源對照.png','實際 Wiki 畫面，含來源、日期與主張對照','證明能從知識頁看見來源與限制；不單靠來源數字。'),screenshot_panel(2,'單頁內容的證據鏈','18_單頁證據追溯.png','06_教學投影片.png','實際單頁追溯畫面；完整對照請操作上方選單','用頁碼、知識頁與主張逐項核對；上方選單讀取實際資料。'),screenshot_panel(3,'情境作答後的處理步驟','22_LINE投票情境練習.png','19_互動題作答.png','LINE情境作答後的四步處理與重點原則','不只判對錯，也顯示下一步怎麼做；內容另經獨立審查。'),screenshot_panel(4,'執行結果與日期','20_執行結果總覽.png',None,'執行紀錄摘要與日期','把程式、語意、操作三種檢查分開，保留原檔。')])
    practice_record = ROOT / 'evidence/practice-browser-public.json'
    practice_count = len(load('teaching/practice.json')['cases']) if (ROOT / 'teaching/practice.json').exists() else 0
    practice_status = '尚待本次瀏覽器驗收'
    if practice_record.exists():
        pr = load('evidence/practice-browser-public.json')
        practice_status = f"公開操作 {pr['summary']['passed']}/{pr['summary']['total']} 項通過，時間 {stamp(pr.get('performed_at'))}"
    practice_evidence = f'<section class="wrap section"><div class="section-heading"><div><p class="eyebrow">PRACTICE THE NEXT STEP</p><h2>五個情境，練習處理方法。</h2></div>{link("practice.html","進入情境練習 →","button")}</div><p>原簡報兩題加上 LINE、TikTok、Instagram 三題；共 {practice_count} 題。選答後解釋每個選項，再提供完整處理步驟和依據。練習次數不是學習成效或防詐準確率。</p><p class="meta">{esc(practice_status)}</p><div class="link-row">{link("evidence/practice-traceability.json","五題的 Wiki 與來源對應")}{link("evidence/practice-semantic-review.json","新增內容的獨立審查")}{link("evidence/practice-browser-public.json","情境實際操作紀錄") if practice_record.exists() else ""}</div></section>' if practice_count else ''
    body = f'''<section class="wrap page-hero evidence-hero"><div><p class="eyebrow">OPEN THE EVIDENCE</p><h1>每一頁，<br>都有路徑可以核對。</h1><p class="lead">先看要求如何對應成果，再選一張投影片，沿著 Wiki、主張與原始來源查回去。不用一句「已完成」代替證據。</p></div><div class="evidence-stamp"><span class="tiny-label">成果範圍</span><b>{len(sources)} 份來源<br>{len(deck['slides'])} 頁教學</b><span>來源查閱 2026-11-15</span>{link('evidence/traceability.json','完整對照原檔 ↗','subtle-link')}</div></section><section class="wrap section"><div class="section-heading"><div><p class="eyebrow">REQUIREMENT → RESULT</p><h2>要求、成果，和怎麼查。</h2></div><p>六項繳交內容都有實際入口。</p></div><div class="requirement-grid">{requirements}</div></section>{practice_evidence}<section class="wrap section trace-section" id="slide-trace"><div class="section-heading"><div><p class="eyebrow">FOLLOW ONE SLIDE</p><h2>選一頁，逐項追溯。</h2></div><p>每個選項都對應保存的真實投影片。</p></div><div class="trace-control"><label for="trace-select">要核對哪張投影片？</label><select id="trace-select">{options}</select><span>14 頁皆可對照</span></div><div id="trace-panel" aria-live="polite"></div><noscript><p>互動對照需要 JavaScript；可直接開啟 {link('evidence/traceability.json','完整對照資料')} 與 {link('deck.html','教學簡報')}。</p></noscript></section><section class="wrap section" id="run-results"><div class="section-heading"><div><p class="eyebrow">WHAT WAS ACTUALLY CHECKED</p><h2>檢查做了什麼，也說清楚範圍。</h2></div></div><div class="check-grid"><article class="check-card"><span class="type-label">01 / 程式檢查</span><h3>{checks.get('slide_citation_coverage',0)} / {checks.get('slides',0)} 頁可追溯</h3><p>{checks.get('local_link_checks',0)} 個本機連結、來源雜湊與渲染文字已檢查。結果：{'通過' if checks.get('passed') else '尚有錯誤'}。</p><time>{esc(stamp(checks.get('performed_at')))}</time>{link('evidence/checks.json','檢查原始結果 ↗','subtle-link')}</article><article class="check-card"><span class="type-label">02 / 獨立語意審查</span><h3>{semantic}</h3><p>新上下文對照來源、十四頁文字與題目解說。程式結構通過，不直接等於事實正確。</p><time>{esc(stamp(review.get('performed_at')))}</time>{link('evidence/independent-review.md','閱讀審查說明 ↗','subtle-link')}</article><article class="check-card"><span class="type-label">03 / 實際瀏覽器操作</span><h3>{summary.get('passed',0)} / {summary.get('total',0)} 項紀錄通過</h3><p>保存紀錄的版本與檢查範圍，請對照下方日期及逐項內容。</p><time>{esc(stamp(browser.get('performed_at')))}</time>{link(browser_path,'操作紀錄原檔 ↗','subtle-link')}</article></div><p class="record-boundary">介面改版日為 2026-11-16。上方日期讀自保存紀錄；新版是否通過，以更新後的實際驗收為準，不能只憑舊畫面判定。</p><details class="record-details"><summary>展開 {summary.get('total',0)} 項操作，看看實際查了什麼</summary><div class="table-wrap"><table><thead><tr><th>操作項目</th><th>檢查範圍</th><th>保存結果</th></tr></thead><tbody>{cases}</tbody></table></div></details></section><section class="wrap section"><div class="section-heading"><div><p class="eyebrow">PROOF YOU CAN OPEN</p><h2>四種畫面，四種證明。</h2></div><p>畫面用來看見成果；通過與否仍對照日期和紀錄。</p></div><div class="proof-grid">{proofs}</div></section><section class="wrap section provenance-note"><h2>來源與檢查的界線</h2><p>八份來源皆有正文核讀與限制記錄；其中七份有 HTTP 全文快取。FTC 直接擷取回 404，另經官方網頁閱讀器核讀，不把失敗寫成下載成功。公開 raw 是附出處的封存短摘與整理，不冒稱原文全文。</p><div class="link-row">{link('raw/manifest.json','來源清單')}{link('evidence/source-acquisition.json','來源取得結果')}{link('evidence/workflow-run.json','一次執行紀錄')}{link('wiki/log.md','Ingest 與查詢日誌')}{link('evidence/independent-review.json','語意審查原檔')}{link('reflection.md','真實問題與反思')}</div></section>'''
    (ROOT / 'evidence.html').write_text(shell('成果與證據對照',body,'evidence',data_script('trace-data',trace)),encoding='utf-8')


def build_workflow():
    nodes = [('N0','需求與邊界','使用者目標、讀者與資料','planning/discussion.md','需求摘要','先記錄讀者、語言、來源標準與成果範圍。','改範圍只重跑受影響節點。'),('N1','取得與核讀來源','官方原文、日期與讀取結果','raw/manifest.json','來源與主張清單','至少五份不同資料；區分正文可讀與全文快取。','無法核實，回到該份來源。'),('N2','整理進知識 Wiki','已核讀來源與封存節錄','wiki/index.md','來源頁、概念與索引','原始節錄不可覆寫；主張保留位置、限制與相關頁。','範圍判讀錯，只修對應知識頁。'),('N3','檢查結構與涵蓋率','Wiki、來源 ID 與 hash','evidence/wiki-lint.json','Wiki 檢查結果','查來源數、連結、編號與原始內容完整性。','結構錯回該頁；知識不足回來源。'),('N4','查詢與證據卡','先看索引，再讀命中段落','queries/Q02.json','查詢紀錄與證據卡','只用命中 Wiki，不憑記憶補外部主張。','證據不足先補檢索，不直接寫投影片。'),('N5','大綱與逐頁稿','教學大綱及對應卡片','teaching/outline.md','十四頁逐頁稿','每頁一個重點，保留引用；不重寫無關頁。','缺子題回檢索；文字太多只退該頁。'),('N6','獨立忠實度審查','成品與來源，新上下文審閱','evidence/independent-review.md','逐頁語意審查','查數字、地域、年份、適用範圍與題目解釋。','稿錯退該稿；卡錯退該卡。'),('N7','渲染為 HTML','已通過的逐頁文字','deck.html','教學 HTML','渲染器負責版面，不順手改字或補結論。','排版錯局部修；內容過長回稿。'),('N8','實際操作與閱讀','HTML、瀏覽器及不同寬度','evidence/browser-checks.json','操作紀錄與畫面','按導覽、作答、開引用、搜尋、列印及手機模擬。','失敗只修對應功能，再檢查。'),('N9','交付與反思','通過項目、真實問題及待辦','reflection.md','成果、紀錄與反思','達上限、資料不足或重大問題未解就停止並列待辦。','不補造來源，不把未做檢查稱為通過。')]
    graph = ''
    for number, title, group in [('01','取得資料',nodes[:3]),('02','編成知識與教材',nodes[3:6]),('03','檢查後交付',nodes[6:])]:
        boxes = ''
        for i, (n,t,_,_,out,_,_) in enumerate(group):
            boxes += f'<a href="#detail-{n}" class="graph-node"><span>{n}</span><b>{esc(t)}</b><small>{esc(out)}</small></a>'
            if i < len(group)-1:
                boxes += '<span class="graph-arrow" aria-hidden="true">↓</span>'
        graph += f'<section class="graph-phase"><header><span>{number}</span><h3>{title}</h3></header><div>{boxes}</div></section>'
    details = ''
    for n,t,inp,path,out,check,back in nodes:
        pending = '<p class="process-pending">本階段界定教學對象、語言、來源規格與成果形式；需求與設計決策記錄於規劃文件。</p>' if n == 'N0' else ''
        details += f'<details class="node-detail" id="detail-{n}"><summary><span>{n}</span>{esc(t)}</summary><div class="node-content"><dl><div><dt>讀取什麼</dt><dd>{esc(inp)}</dd></div><div><dt>交出什麼</dt><dd>{link(path,out+" ↗")}</dd></div><div><dt>完成前檢查</dt><dd>{esc(check)}</dd></div><div><dt>失敗退回</dt><dd>{esc(back)}</dd></div></dl>{pending}</div></details>'
    error = load('evidence/checks-round1.json').get('errors',['未保存錯誤內容'])[0]
    body = f'''<section class="wrap page-hero"><p class="eyebrow">HOW THE WORK GETS DONE</p><h1>錯在哪裡，<br>就回到最近的節點。</h1><p class="lead">先把來源整理成 Wiki，再用它寫教材。Graph 說明大步驟，局部 Loop 負責發現問題後修正，讓小錯不必重做整份簡報。</p></section><section class="wrap section graph-section"><div class="section-heading"><div><h2>從原文走到教學，共十個節點。</h2><p>點選任一節點，查看它能讀什麼、交出什麼，以及失敗退去哪裡。</p></div></div><div class="graph-board">{graph}</div><div class="return-lanes"><a href="#detail-N1"><span>↩</span> 來源不夠 → 回取得資料</a><a href="#detail-N4"><span>↩</span> 引用不對 → 回卡片或該頁稿</a><a href="#detail-N7"><span>↩</span> 閱讀溢出 → 先局部排版</a></div></section><section class="wrap section"><div class="section-heading"><div><p class="eyebrow">INPUT · OUTPUT · CHECK</p><h2>每一關的工作範圍。</h2></div></div><div class="node-list">{details}</div></section><section class="wrap section"><div class="section-heading"><div><p class="eyebrow">A REAL REPAIR</p><h2>一次真實錯誤，怎麼局部修好？</h2></div>{link('reflection.md','讀完整反思 →','text-link')}</div><div class="repair-grid"><article><span>發現</span><h3>報告還沒產生，就先檢查它的連結。</h3><code>{esc(error)}</code>{link('evidence/checks-round1.json','第一次實際失敗 ↗','subtle-link')}</article><article><span>回退與調整</span><h3>只修檢查器的產物順序。</h3><p>先查其他連結，產生報告後再核對自身輸出。沒有因此重寫十四頁教材。</p></article><article><span>再驗收</span><h3>保存第二輪結果，不抹掉第一輪。</h3><p>修正後的紀錄保留，可與原失敗直接比對。</p>{link('evidence/checks-round2.json','修正後的實際結果 ↗','subtle-link')}</article></div></section><section class="wrap section stop-rules"><div><h2>知道何時繼續，也知道何時停下。</h2><p>新來源、查詢或文字改動會觸發檢查。來源至少五份、內容可追溯、重大問題已處理，才往交付走。</p></div><div><b>局部最多 2 輪</b><b>整體最多 3 輪</b><p>這是本專案自訂上限，不是要跑滿的次數。來源不足或到上限仍有問題，就停止並列待辦。</p></div></section><section class="wrap section"><div class="section-heading"><h2>把過程打開給你看。</h2></div><div class="link-row">{link('planning/discussion.md','需求與暫定決策')}{link('teaching/outline.md','十四頁大綱')}{link('AGENTS.md','AI 協作規則')}{link('evidence/workflow-run.json','實際執行紀錄')}{link('wiki/log.md','Ingest 與查詢日誌')}{link('evidence.html','成果與證據對照')}</div></section>'''
    (ROOT / 'workflow.html').write_text(shell('製作流程與局部回退',body,'workflow'),encoding='utf-8')


def build():
    catalog = load('wiki/catalog.json')['pages']
    sources = {s['id']:s for s in load('raw/manifest.json')['sources']}
    deck = load('teaching/deck.json')
    build_home(catalog,sources,deck)
    build_wiki(catalog,sources)
    build_workflow()
    build_evidence(catalog,sources,deck)
    print('Built offline home, Wiki, workflow and exact evidence views from saved artifacts; no new test or approval claimed.')


if __name__ == '__main__':
    build()
