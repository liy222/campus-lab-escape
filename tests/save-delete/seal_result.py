"""Seal joint focused evidence without rerunning accepted scopes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
load=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
qa='evidence/integration/save-delete/qa';candidate_path='evidence/integration/save-delete/candidate.json'
candidate=load(candidate_path);plan=load('evidence/integration/save-delete/plan.json')
source={p:sha(p) for p in candidate['source_sha256']};assert source==candidate['source_sha256']
oldtests={p:sha(p) for p in plan['old_test_sha256']};assert oldtests==plan['old_test_sha256']
runs={k:f'{qa}/{v}/run.json' for k,v in {'api':'20261014T095405258321-api','build':'20261014T095424861071-build','browser_first':'20261014T095444716Z-browser','browser_remaining':'20261014T095644685Z-browser'}.items()}
reports={k:load(p) for k,p in runs.items()}
assert reports['api']['exit_code']==0 and reports['api']['methods']==20 and reports['api']['subtests']==33
assert reports['build']['exit_code']==0 and reports['build']['process_exit_code']==0
assert reports['browser_first']['exit_code']==1 and len(reports['browser_first']['issues'])==1
assert reports['browser_remaining']['exit_code']==0 and not reports['browser_remaining']['issues']
for r in reports.values():assert r['source_sha256_before']==source and r['source_sha256_after']==source
viewed=[f'{qa}/20261014T095444716Z-browser/delete-dialog-1280.png',*[f'{qa}/20261014T095644685Z-browser/{n}.png' for n in ['delete-dialog-375','last-deleted-empty-375','post-win-deleted-375']]]
new_source_paths=['tests/api/test_save_delete.py','tests/save-delete/run_api.py','tests/save-delete/run_build.py','tests/save-delete/run_browser.mjs','tests/save-delete/seal_result.py','review/findings/save-delete.md']
artifacts={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/qa).rglob('*')) if p.is_file() and p.name!='result.json'}
result={'recorded_at':datetime.now(timezone.utc).isoformat(),'operator':'save_delete_qa independent assigned QA','status':'PASS joint scoped evidence; SOURCE STOP',
    'candidate':candidate_path,'candidate_sha256':sha(candidate_path),'source_sha256':source,'old_test_sha256':oldtests,'new_qa_source_sha256':{p:sha(p) for p in new_source_paths},
    'runs':{k:{'path':p,'sha256':sha(p),'exit_code':reports[k]['exit_code']} for k,p in runs.items()},'artifacts_sha256':artifacts,'artifact_count':len(artifacts),
    'api':{'methods':20,'new_delete_methods':11,'unchanged_archive_methods':9,'subtests':33,'seconds':11.757,'exit_code':0,'paid_calls':0},
    'build':{'count':1,'exit_code':0},'browser':{'joint_scoped_pass':True,'single_full_green_claim':False,'first_raw_checks':len(reports['browser_first']['checks']),'remaining_raw_checks':len(reports['browser_remaining']['checks']),'failed_adapter_epochs':1,'product_fix_count':0,'repeated_counts_summed':False,'no_resend':'Static production source inspection; no dynamic dispatch-count claim.'},
    'actual_viewed_png_sha256':{p:sha(p) for p in viewed},'unresolved_product_findings':[],
    'commands_exit_codes':[{**c} for c in reports['api']['commands']]+[{'command':reports['build']['command'],'exit_code':reports['build']['process_exit_code']}]+[{'command':reports[k]['command'],'exit_code':reports[k]['exit_code']} for k in ['browser_first','browser_remaining']],
    'limitations':['Phone375 is computer Chrome viewport/touch emulation only; no physical mobile device or mobile App testing.','No user DB, paid provider, human timing, OS restart, root launcher or 127-method suite.','Game win progression is API fixture only; actual UI covers archive/delete/read/reload/process-restart/post-win desktop and mobile.','Existing Starlette/httpx deprecation warning remains.','One QA fixture failure retained; first and remaining browser runs jointly cover scopes without repeated sums.','Main acceptance and Git synchronization remain outside independent QA ownership.']}
(ROOT/qa/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':f'{qa}/result.json','sha256':sha(f'{qa}/result.json'),'source_count':len(source),'old_test_count':len(oldtests),'artifact_count':len(artifacts),'exit_code':0}));sys.exit(0)
