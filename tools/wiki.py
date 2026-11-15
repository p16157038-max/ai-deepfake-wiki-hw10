"""Reproducible bookkeeping around actual coding-LLM ingest/query work; no hidden API."""
import argparse,json,hashlib,re
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def log(kind,text):
    p=ROOT/'wiki/log.md';p.parent.mkdir(exist_ok=True)
    with p.open('a',encoding='utf-8') as f:f.write(f'\n## [{now()}] {kind}\n\n{text}\n')
def catalog():
    p=ROOT/'wiki/catalog.json'
    return read(p) if p.exists() else {'pages':[]}
def index(data):
    text=['# 知識索引','', '由 LLM 核讀來源後編寫，來源、概念與查詢彼此連結。','']
    for kind,name in [('concept','概念與跨來源綜合'),('source','逐篇來源')]:
        text+=['## '+name,'']+[f"- [{p['title']}]({p['path']}) — {p['summary']}" for p in data['pages'] if p['kind']==kind]+['']
    text+=['## 使用紀錄','','- [處理日誌](log.md)','- [維護規則](../AGENTS.md)']
    (ROOT/'wiki/index.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    save(ROOT/'wiki/catalog.json',data)
def ingest(ids):
    manifest=read(ROOT/'raw/manifest.json')['sources'];data=catalog()
    for s in manifest:
        if s['id'] not in ids:continue
        raw=ROOT/s['raw_path'];assert hashlib.sha256(raw.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==s.get('raw_lf_sha256',s['raw_sha256'])
        page={'id':s['id'],'path':f"sources/{s['id']}.md",'title':s['title'],'kind':'source','sources':[s['id']],'summary':s['teaching_use'],'claims':[{**c,'sources':[s['id']],'locator':c['location']} for c in s['claims']]}
        page['updated']='2026-11-15'
        lines=[f"# {s['id']} {s['title']}",'','Wiki更新日期：2026-11-15',f"原文：[{s['issuer']}]({s['url']})",f"原文日期：{s.get('published_at') or s.get('updated_at') or '未標示'}；查閱：{s['accessed_at']}",f"封存節錄：[raw/{s['id']}.md](../../raw/{s['id']}.md)",'','## LLM 整理的可支持主張']
        lines += [f"\n### {c['id']}\n\n{c['text']}\n\n依據位置：{c['location']}。" for c in s['claims']]
        lines+=['','## 範圍與不能推論的內容']+['- '+x for x in s['does_not_support']]+['','## 知識連結','- [回知識索引](../index.md)']
        p=ROOT/'wiki'/page['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        data['pages']=[x for x in data['pages'] if x['id']!=s['id']]+[page]
        log('ingest',f"{s['id']}：已讀官方原文及封存節錄，寫來源頁與限制，更新索引。raw SHA256={s['raw_sha256']}。研究代理負責來源核讀；此腳本負責可重現的編排與日誌。")
    index(data);print(f'Ingested {len(ids)} sources; catalog now {len(data["pages"])} pages.')
def topics():
    data=catalog();drafts=read(ROOT/'ingest_drafts/topics.json')['pages']
    existing={c['id'] for p in data['pages'] for c in p['claims']}
    for page in drafts:
        assert all(c in existing for c in page['claim_ids']),page['id']
        claims=[c for p in data['pages'] if p['kind']=='source' for c in p['claims'] if c['id'] in page['claim_ids']]
        page={**page,'kind':'concept','claims':claims,'updated':'2026-11-15'}
        text=[f"# {page['id']} {page['title']}",'','Wiki更新日期：2026-11-15',page['summary'],'','## 跨來源知識']
        text += [f"\n### {section['title']}\n\n{section['text']}\n\n依據："+'、'.join(section['claims'])+'。' for section in page['sections']]
        text+=['','## 原始來源']+[f"- [{s}](../sources/{s}.md)" for s in page['sources']]+['','## 相關知識']+[f"- [{x}](../{x})" for x in page['related']]+['- [回知識索引](../index.md)']
        p=ROOT/'wiki'/page['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(text)+'\n',encoding='utf-8')
        data['pages']=[x for x in data['pages'] if x['id']!=page['id']]+[page]
        log('synthesis',f"{page['id']}：LLM 依 {','.join(page['sources'])} 綜合，保留 {len(claims)} 項主張及限制。")
    index(data);print(f'Compiled {len(drafts)} cross-linked concept pages.')
def lint():
    data=catalog();m=read(ROOT/'raw/manifest.json')['sources'];errors=[]
    if sum(p['kind']=='source' for p in data['pages'])<5:errors.append('Fewer than 5 sources ingested.')
    if sum(p['kind']=='concept' for p in data['pages'])<3:errors.append('Fewer than 3 related concept pages.')
    for s in m:
        if hashlib.sha256((ROOT/s['raw_path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=s.get('raw_lf_sha256',s['raw_sha256']):errors.append('Raw content changed: '+s['id'])
    ids=[p['id'] for p in data['pages']]
    if len(ids)!=len(set(ids)):errors.append('Duplicate page ID')
    for p in (ROOT/'wiki').rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if not target.startswith(('http:','https:','#')) and not (p.parent/target.split('#')[0]).resolve().exists():errors.append(f'Broken {p.relative_to(ROOT)} -> {target}')
    result={'performed_at':now(),'source_count':sum(p['kind']=='source' for p in data['pages']),'concept_count':sum(p['kind']=='concept' for p in data['pages']),'raw_immutable':True,'errors':errors,'semantic_truth_proved_by_script':False}
    save(ROOT/'evidence/wiki-lint.json',result);log('lint',json.dumps(result,ensure_ascii=False))
    print(json.dumps(result,ensure_ascii=False));return not errors
def query(qid,question):
    # Literal lexical retrieval over an already LLM-compiled wiki. It is not an LLM chatbot.
    data=catalog();terms=question.split();scored=[]
    for p in data['pages']:
        if p['kind']!='concept':continue
        body=(ROOT/'wiki'/p['path']).read_text(encoding='utf-8')
        score=sum(body.lower().count(t.lower()) for t in terms)
        if score:scored.append((score,p))
    selected=[p for score,p in sorted(scored,key=lambda x:-x[0])[:4]]
    result={'id':qid,'performed_at':now(),'question':question,'method':'index-first lexical retrieval of LLM-written Wiki; LLM synthesizes answers from retrieved pages afterward','pages':[p['path'] for p in selected],'claims':list(dict.fromkeys(c['id'] for p in selected for c in p['claims'])),'retrieved_sections':[{'page':p['path'],'summary':p['summary'],'sections':p['sections']} for p in selected]}
    save(ROOT/'queries'/f'{qid}.json',result);log('query',f"{qid}：{question} → {','.join(result['pages'])}。")
    print(json.dumps(result,ensure_ascii=False));return result
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('command',choices=['ingest','topics','lint','query']);a.add_argument('args',nargs='*');v=a.parse_args()
    if v.command=='ingest':ingest(v.args)
    elif v.command=='topics':topics()
    elif v.command=='lint':raise SystemExit(0 if lint() else 1)
    else:query(v.args[0],' '.join(v.args[1:]))
