"""Build offline-capable Wiki and workflow views from completed source artifacts."""
import json,html,re
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
def esc(s):return html.escape(str(s),quote=True)
STYLE='''*{box-sizing:border-box}body{margin:0;background:#f7f6f2;color:#1b2332;font:17px/1.75 "Microsoft JhengHei",sans-serif}a{color:#4e3bc6;text-underline-offset:4px}button,input{font:inherit}button,a,input{outline-offset:4px}a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid #9765eb}header{padding:20px max(24px,calc((100vw - 1160px)/2));border-bottom:1px solid #d5d5d0;display:flex;gap:24px;flex-wrap:wrap}header a{font-size:15px}main{max-width:1160px;margin:auto;padding:48px 24px}h1{font-size:clamp(32px,5vw,58px);line-height:1.25;letter-spacing:-.04em;margin:12px 0 24px}h2{font-size:27px;margin-top:32px}h3{font-size:21px;margin-bottom:8px}p{max-width:86ch}.eyebrow{font-size:13px;letter-spacing:.15em;color:#625880}.lead{font-size:22px;color:#444c5b}.actions{display:flex;flex-wrap:wrap;gap:16px;margin:30px 0}.actions a{padding:12px 22px;border:1px solid #4e3bc6;border-radius:8px;text-decoration:none}.actions a:first-child{background:#4e3bc6;color:white}.facts{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;border-block:1px solid #ccc;padding:28px 0;margin:36px 0}.facts strong{font-size:42px;color:#4e3bc6;display:block}.notice{padding:16px 20px;border-left:4px solid #d5ac24;background:#fff8dd}.layout{display:grid;grid-template-columns:290px minmax(0,1fr);gap:40px}.side input{width:100%;padding:10px;border:1px solid #c9c9d2;border-radius:6px}.side nav a{display:block;margin:10px 0;font-size:14px}.side{min-width:0}.article{background:#fff;border:1px solid #ddd;padding:28px;min-width:0;overflow-wrap:anywhere}.article h1{font-size:30px}.article h2{font-size:22px}.article h3{font-size:18px}.article ul{padding-left:24px}.meta{font-size:14px;color:#5d6371}.graph{display:grid;gap:12px;margin:28px 0}.node{display:grid;grid-template-columns:60px 1fr 1fr;gap:18px;border-bottom:1px solid #ccc;padding:16px 12px}.node .number{color:#5d3cce;font-size:22px}.return{color:#a3481e;font-size:14px}.arrow{text-align:center;color:#7863b7;font-size:22px;line-height:1}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:10px;border:1px solid #ccc;vertical-align:top}th{background:#eeecf4}.scroll{overflow:auto}code{font-family:Consolas,monospace;font-size:.9em;background:#eeeaf6;padding:2px 4px}footer{font-size:14px;color:#616673;margin-top:40px;border-top:1px solid #ccc;padding-top:20px}@media(max-width:750px){.layout,.facts{grid-template-columns:1fr}.node{grid-template-columns:40px 1fr}.node>div:last-child{grid-column:2}main{padding:30px 20px}.article{padding:20px}.side nav{max-height:230px;overflow:auto}h1{font-size:34px}}@media print{header,.side,.actions{display:none}.layout{display:block}.article{border:0}main{padding:0}}'''
NAV='<header><a href="index.html">作業入口</a><a href="deck.html">開始上課</a><a href="wiki.html">閱讀 Wiki</a><a href="workflow.html">流程與證據</a></header>'
def shell(title,body,script=''):
 return f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{STYLE}</style></head><body>{NAV}<main>{body}</main>{script}</body></html>'
def markdown(text,current):
 def links(line):
  line=esc(line)
  def sub(m):
   target=html.unescape(m[2]);url=target
   if not target.startswith(('https://','http://')):
    resolved=(ROOT/'wiki'/current).parent/target.split('#')[0]
    try:rel=resolved.resolve().relative_to((ROOT/'wiki').resolve());url='wiki.html#page='+quote(rel.as_posix(),safe='')
    except ValueError:url=resolved.resolve().relative_to(ROOT.resolve()).as_posix()
   return f'<a href="{esc(url)}">{m[1]}</a>'
  return re.sub(r'\[([^]]+)\]\(([^)]+)\)',sub,line)
 out=[];inlist=False
 for line in text.splitlines():
  if line.startswith('- '):
   if not inlist:out.append('<ul>');inlist=True
   out.append('<li>'+links(line[2:])+'</li>');continue
  if inlist:out.append('</ul>');inlist=False
  if not line.strip():continue
  match=re.match(r'^(#{1,3}) (.*)',line)
  if match:out.append(f'<h{len(match[1])}>{links(match[2])}</h{len(match[1])}>')
  else:out.append('<p>'+links(line)+'</p>')
 if inlist:out.append('</ul>')
 return ''.join(out)
def build():
 catalog=json.loads((ROOT/'wiki/catalog.json').read_text(encoding='utf-8'))
 manifest=json.loads((ROOT/'raw/manifest.json').read_text(encoding='utf-8'))
 pages=[]
 for p in catalog['pages']:
  pages.append({**p,'html':markdown((ROOT/'wiki'/p['path']).read_text(encoding='utf-8'),p['path'])})
 data=json.dumps(pages,ensure_ascii=False).replace('<','\\u003c')
 body='<p class="eyebrow">LLM WIKI · INGEST → QUERY → LINT</p><h1>先累積知識，再產生教材</h1><p class="lead">8份官方資料，6頁跨來源知識，保留主張與限制。</p><p class="meta">Wiki由Codex編寫維護；下方搜尋是本機關鍵字篩選，不是即時AI聊天。</p><div class="layout"><aside class="side"><label for="wiki-search">搜尋頁面</label><input id="wiki-search" type="search" placeholder="例如：LINE、聲音、預錄"><nav id="wiki-list" aria-label="知識頁面"></nav><p><a href="wiki/index.md">Markdown索引</a> · <a href="wiki/log.md">處理日誌</a></p></aside><article id="wiki-article" class="article" aria-live="polite"></article></div>'
 script='<script id="wiki-data" type="application/json">'+data+'</script>'+'''<script>(()=>{const pages=JSON.parse(document.getElementById('wiki-data').textContent);const list=document.getElementById('wiki-list'),article=document.getElementById('wiki-article'),search=document.getElementById('wiki-search');function nav(){list.replaceChildren();let n=0;for(const p of pages){if(!(p.title+' '+p.summary+' '+p.sources.join(' ')).toLowerCase().includes(search.value.toLowerCase()))continue;const a=document.createElement('a');a.textContent=p.id+' '+p.title;a.href='#page='+encodeURIComponent(p.path);list.appendChild(a);n++}if(!n)list.textContent='沒有符合的頁面，請改用較短關鍵字。'}function show(){const key=new URLSearchParams(location.hash.slice(1)).get('page');const p=pages.find(p=>p.path===key)||pages.find(p=>p.kind==='concept');article.innerHTML=p.html;document.title=p.title+'｜LLM Wiki'}search.addEventListener('input',nav);window.addEventListener('hashchange',show);nav();show()})();</script>'''
 (ROOT/'wiki.html').write_text(shell('AI深偽與社群詐騙 LLM Wiki',body,script),encoding='utf-8')
 nodes=[('N0','需求與假設','planning/discussion.md','本人確認仍待辦；依缺席授權先產可審閱版。'),('N1','取得與核讀來源','raw/manifest.json','來源不實或缺漏 → 只退來源取得。'),('N2','LLM ingest 與綜合','wiki/ index/log/來源/概念','原始節錄不可覆寫；至少五份來源。'),('N3','Lint 與涵蓋率關卡','evidence/wiki-lint.json','ID、雜湊、連結錯 → 修對應頁。'),('N4','查詢與證據卡','queries/、cards/','證據不足 → 補檢索，不憑記憶補文。'),('N5','大綱與逐頁稿','teaching/outline.md、drafts/','本人確認待辦；暫定稿由獨立AI審查。'),('N6','新上下文忠實度審查','evidence/independent-review.json','事實錯 → 該頁稿；卡片錯 → 該卡片。'),('N7','不改字的HTML渲染','deck.html、wiki.html','版面錯 → 局部排版；文太多 → 回逐頁稿。'),('N8','真實瀏覽器檢查','evidence/browser-checks.json','導覽、引用、題目、手機、列印；失敗只修對應功能。'),('N9','打包與反思','submission/、evidence/','全過或達上限停止；待確認項目不冒充完成。')]
 graph=''.join((f'<div class="node"><span class="number">{n}</span><div><strong>{t}</strong><div class="meta">輸出：{esc(o)}</div></div><div class="return">{esc(r)}</div></div>'+('<div class="arrow" aria-hidden="true">↓</div>' if n!='N9' else '')) for n,t,o,r in nodes)
 sources=''.join(f'<tr><td>{s["id"]}</td><td><a href="{esc(s["url"])}">{esc(s["title"])}</a></td><td>{s.get("published_at") or s.get("updated_at") or "未標示"}</td></tr>' for s in manifest['sources'])
 body='<p class="eyebrow">WORKFLOW PROTOTYPE</p><h1>把錯誤退回最近的節點</h1><p class="lead">Graph固定大流程；每個小Loop最多兩輪，整體最多三輪。</p><p class="notice">需求摘要與大綱尚待本人確認。使用者允許缺席期間先做可審閱版本；圖中沒有把此授權寫成已完成確認。</p><div class="graph">'+graph+'</div><h2>每個角色能讀什麼、改什麼</h2><div class="scroll"><table><tr><th>角色</th><th>允許</th><th>禁止</th></tr><tr><td>證據卡作者</td><td>讀命中Wiki頁，寫對應卡片</td><td>加入外部常識</td></tr><tr><td>逐頁稿作者</td><td>讀大綱與卡片，寫指定頁</td><td>重寫無關頁</td></tr><tr><td>HTML渲染器</td><td>讀通過的文字，排版</td><td>改字或補結論</td></tr><tr><td>檢查者</td><td>讀成品與來源，提出問題</td><td>自行修改被審稿</td></tr></table></div><h2>可檢視的執行證據</h2><ul><li><a href="evidence/source-acquisition.json">來源取得：7個HTTP快取成功，FTC直接擷取404；另由官方網頁閱讀器核讀</a></li><li><a href="evidence/wiki-lint.json">Wiki lint</a> · <a href="wiki/log.md">Ingest/query/log</a></li><li><a href="evidence/independent-review.json">獨立語意審查</a></li><li><a href="evidence/checks.json">程式檢查</a> · <a href="evidence/browser-checks.json">瀏覽器檢查</a></li><li><a href="reflection.md">依真實紀錄撰寫的反思</a></li></ul><h2>來源清單</h2><p>來源日期保留原年份，不稱為最新統計；平台復原未登入實測。公開raw是封存節錄與轉述，不是原文全文。</p><div class="scroll"><table><tr><th>ID</th><th>原始官方文件</th><th>發布或更新</th></tr>'+sources+'</table></div>'
 (ROOT/'workflow.html').write_text(shell('工作流程與證據',body),encoding='utf-8')
 body='<p class="eyebrow">HW10 1110 · 成大 P16157038 系統碩一 陳世豐</p><h1>AI 深偽與社群詐騙</h1><p class="lead">給Gen Z的一堂入門課：看懂風險，練習查證，知道向誰求助。</p><div class="actions"><a href="deck.html">開始14頁教學</a><a href="wiki.html">閱讀LLM Wiki</a><a href="workflow.html">看流程與檢查</a></div><div class="facts"><div><strong>8</strong>份官方來源已ingest</div><div><strong>6</strong>頁跨來源綜合知識</div><div><strong>2</strong>道有解說的情境題</div></div><h2>先有Wiki，才有簡報</h2><p>研究代理先讀官方資料，Codex依規則編寫持續連結的Wiki，保存索引、處理日誌與原文位置。再查詢Wiki、寫證據卡與逐頁稿；每頁下方可點回Wiki、查到來源。</p><h2>怎麼使用</h2><p>教學頁用上一頁／下一頁或左右方向鍵切換。情境題點選答案看解說，可重新作答。Wiki提供本機關鍵字搜尋；流程頁列出局部退回規則與真實檢查紀錄。這些靜態成果不需API金鑰或登入。</p><p class="notice">此為依使用者缺席授權完成的可審閱版本，需求摘要與大綱仍待本人確認。教學情境是模擬；兩個官方案例另有日期和地域限制。</p><footer><a href="AGENTS.md">協作規則</a> · <a href="README.md">重現方式</a> · <a href="reflection.md">執行反思</a><p>資料查閱日2026-11-15。未展示真實性影像或製作人物深偽。新增知識需coding agent讀來源；本機搜尋與渲染工具不會自行呼叫LLM。</p></footer>'
 (ROOT/'index.html').write_text(shell('AI深偽與社群詐騙 HW10',body),encoding='utf-8')
 print('Built offline-capable home, Wiki and workflow pages from existing artifacts.')
if __name__=='__main__':build()
