"""Run the executable verification part of the recorded workflow, not an LLM API."""
from pathlib import Path
from datetime import datetime,timezone
import sys,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
records=[]
for args in [['tools/wiki.py','lint'],['tools/render.py'],['tools/build_portal.py'],['tools/check.py']]:
    p=subprocess.run([sys.executable,'-X','utf8',*args],cwd=ROOT,text=True,encoding='utf-8',capture_output=True)
    records.append({'command':['python',*args],'performed_at':datetime.now(timezone.utc).isoformat(),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode:break
result={'performed_at':datetime.now(timezone.utc).isoformat(),'scope':'Executable checks/rebuild over already LLM-authored Wiki and drafts; does not call an LLM or fake new ingest/review.','commands':records,'passed':all(r['exit_code']==0 for r in records) and len(records)==4,'artifacts':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['deck.html','wiki.html','workflow.html','teaching/deck.json']},'local_repair_history':{'first_check':'evidence/checks-round1.json','corrected_check':'evidence/checks-round2.json','cause':'self-report dependency checked before generation','unrelated_slides_rewritten':False},'limits':{'local_max_rounds':2,'overall_max_rounds':3},'human_requirements_confirmation':'pending; user explicitly authorized provisional work during absence'}
(ROOT/'evidence/workflow-run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':result['passed'],'commands':len(records)},ensure_ascii=False))
raise SystemExit(0 if result['passed'] else 1)
