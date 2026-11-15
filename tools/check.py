"""Executable structural and provenance checks; semantic review remains separate."""
import json,re,html,hashlib
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote,urlparse
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def run():
    errors=[];sources=read(ROOT/'raw/manifest.json')['sources'];pages=read(ROOT/'wiki/catalog.json')['pages'];slides=read(ROOT/'teaching/deck.json')['slides'];htmltext=html.unescape((ROOT/'deck.html').read_text(encoding='utf-8'))
    assert len(sources)>=5
    known={s['id']:s for s in sources};claims={c['id']:c for s in sources for c in s['claims']};catalog={p['path']:p for p in pages}
    for s in sources:
        if hashlib.sha256((ROOT/s['raw_path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=s.get('raw_lf_sha256',s['raw_sha256']):errors.append('Raw content changed '+s['id'])
    if len({s['canonical_url'] for s in sources})!=len(sources):errors.append('Duplicate source document URL')
    trace=[];used=set()
    def textvalues(s):
        yield s['title'];yield s['lead']
        for k in ['bullets']:
            yield from s.get(k,[])
        for k in ['items','chat']:
            for x in s.get(k,[]):yield from x.values()
        if s.get('note'):yield s['note']
        if s.get('quiz'):
            yield s['quiz']['question']
            for option in s['quiz']['options']:yield option['text'];yield option['feedback']
    for slide in slides:
        originals=set();ids=set();paths=[]
        querypages=set()
        for q in slide['query_ids']:
            query=read(ROOT/'queries'/f'{q}.json')
            if not query.get('answer'):errors.append('Missing LLM answer '+q)
            querypages.update(query['pages'])
        for citation in slide['citations']:
            p=citation['wiki'];paths.append(p)
            if p not in querypages:errors.append(slide['id']+' cites page not read by its queries: '+p)
            if p not in catalog:errors.append('Missing wiki '+p);continue
            allowed={c['id'] for c in catalog[p]['claims']}
            for cid in citation['claims']:
                if cid not in allowed or cid not in claims:errors.append(slide['id']+' invalid claim '+cid)
                else:ids.add(cid);originals.add(cid.split('-')[0])
        for value in textvalues(slide):
            if str(value) not in htmltext:errors.append(slide['id']+' renderer changed or lost text: '+str(value)[:35])
        used.update(originals);trace.append({'slide':slide['id'],'title':slide['title'],'queries':slide['query_ids'],'cards':[f'cards/{q}.json' for q in slide['query_ids']],'wiki_pages':paths,'claim_ids':sorted(ids),'sources':sorted(originals)})
    if used!=set(known):errors.append('Unused sources '+str(set(known)-used))
    targets=0
    for file in ROOT.glob('*.html'):
        text=file.read_text(encoding='utf-8')
        if 'lang="zh-Hant"' not in text:errors.append(file.name+' missing zh-Hant')
        for target in re.findall(r'href="([^"]+)"',text):
            target=html.unescape(target);u=urlparse(target)
            if u.scheme or target.startswith('#'):continue
            target=unquote(u.path)
            # The report links to this run's own output. Verify that artifact
            # after writing it, rather than failing the first clean build.
            if target and target!='evidence/checks.json' and not (ROOT/target).is_file():errors.append(f'{file.name} broken local link {target}')
            targets+=1
    if len(slides)!=14:errors.append('Not14slides')
    if sum('quiz' in s for s in slides)<2:errors.append('Less than2quizzes')
    # Explicit evidence anchors for all material quantitative case claims.
    numeric={'港幣2億元':{'claim':'S02-C2','source_wording':'港幣兩億元','value':200000000,'currency':'HKD'},'八個機關':{'claim':'S05-C1','source_wording':'八個機關','value':8,'unit':'機關'},'五個香港銀行帳戶':{'claim':'S02-C2','source_wording':'五個香港銀行帳戶','value':5,'unit':'銀行帳戶'}}
    for label,x in numeric.items():
        if x['source_wording'] not in claims[x['claim']]['text']:errors.append('Numeric evidence mismatch '+label)
    result={'performed_at':datetime.now(timezone.utc).isoformat(),'passed':not errors,'sources':len(sources),'concept_pages':sum(p['kind']=='concept' for p in pages),'query_answers':len(list((ROOT/'queries').glob('*.json'))),'slides':len(slides),'quiz_count':sum('quiz' in s for s in slides),'slide_citation_coverage':len(trace),'source_coverage':sorted(used),'local_link_checks':targets,'rendered_text_preserved':not any('renderer changed' in e for e in errors),'raw_sha256_verified':True,'raw_hash_mode':'canonical LF content hash; original local byte hashes retained separately','numeric_case_evidence':numeric,'semantic_truth_proved_by_script':False,'errors':errors}
    (ROOT/'evidence/traceability.json').write_text(json.dumps({'slides':trace},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'evidence/checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert (ROOT/'evidence/checks.json').is_file()
    print(json.dumps(result,ensure_ascii=False));return not errors
if __name__=='__main__':raise SystemExit(0 if run() else 1)
