"""Run the executable verification part of the recorded workflow, not an LLM API."""
from pathlib import Path
from datetime import datetime,timezone
import sys,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
records=[]
commands=[['tools/wiki.py','lint'],['tools/render.py']]
if (ROOT/'teaching/practice.json').exists():commands.append(['tools/build_practice.py'])
commands += [['tools/check.py','--trace-only'],['tools/build_portal.py'],['tools/check.py']]
for args in commands:
    p=subprocess.run([sys.executable,'-X','utf8',*args],cwd=ROOT,text=True,encoding='utf-8',capture_output=True)
    records.append({'command':['python',*args],'performed_at':datetime.now(timezone.utc).isoformat(),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode:break
artifacts=['deck.html','wiki.html','workflow.html','evidence.html','teaching/deck.json']
if (ROOT/'practice.html').exists():artifacts+=['practice.html','teaching/practice.json']
confirmation_path=ROOT/'planning/confirmation-20261118.json'
confirmation=json.loads(confirmation_path.read_text(encoding='utf-8')) if confirmation_path.exists() else {'status':'not_recorded'}
result={'performed_at':datetime.now(timezone.utc).isoformat(),'scope':'Executable checks/rebuild over saved LLM-authored Wiki, drafts and practice; no new LLM ingest or semantic review.','commands':records,'passed':all(r['exit_code']==0 for r in records) and len(records)==len(commands),'artifacts':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in artifacts},'artifact_lf_sha256':{name:hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name in artifacts},'local_repair_history':{'first_check':'evidence/checks-round1.json','corrected_check':'evidence/checks-round2.json','cause':'self-report dependency checked before generation','unrelated_slides_rewritten':False},'limits':{'local_max_rounds':2,'overall_max_rounds':3},'human_requirements_confirmation':{'status':confirmation['status'],'version':confirmation.get('version'),'confirmed_at':confirmation.get('confirmed_at'),'record':'planning/confirmation-20261118.json' if confirmation_path.exists() else None,'historical_boundary':'Only this revision is confirmed; initial provisional work is not retroactively approved.'}}
(ROOT/'evidence/workflow-run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':result['passed'],'commands':len(records)},ensure_ascii=False))
raise SystemExit(0 if result['passed'] else 1)
