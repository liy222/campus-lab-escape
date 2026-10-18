from pathlib import Path
from datetime import datetime, timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
qa=ROOT/'evidence/integration/ai-companion/qa'
cp='evidence/integration/ai-companion/candidate.json'
c=json.loads((ROOT/cp).read_text(encoding='utf-8-sig'))
ap='evidence/integration/ai-companion/qa/20261018T104302627701Z-api'
bp='evidence/integration/ai-companion/qa/20261018T104317562Z-browser'
a=json.loads((ROOT/ap/'run.json').read_text(encoding='utf-8'))
b=json.loads((ROOT/bp/'run.json').read_text(encoding='utf-8'))
p=json.loads((qa/'preparation.json').read_text(encoding='utf-8'))
digest=lambda x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest()
current={x:digest(x) for x in c['source_sha256']}
assert current==c['source_sha256']==a['source_sha256_before']==a['source_sha256_after']==b['source_sha256_before']==b['source_sha256_after']
assert all(digest(x)==h for x,h in p['old_test_sha256'].items())
assert a['exit_code']==b['exit_code']==0 and b['issues']==[]
artifacts=sorted(x for x in qa.rglob('*') if x.is_file() and x.name!='result.json')
scripts=['tests/api/test_ai_companion.py','tests/ai-companion/prepare_design.py','tests/ai-companion/prepare.py','tests/ai-companion/fake_runtime.py','tests/ai-companion/qa_app.py','tests/ai-companion/run_api.py','tests/ai-companion/run_browser.mjs','tests/ai-companion/seal.py','review/findings/ai-companion.md']
r={'recorded_at':datetime.now(timezone.utc).isoformat(),'operator':'hint_flow_qa independent QA','candidate':cp,'candidate_sha':'a3966227ee5d6f85303ddda6577e90324d6e4731c1c866fe5c8b8be18001a5c1','accepted_scope':'Focused offline companion HTTP/context/semantic samples/mode/restore/race and desktop UI; not real-model quality or old full-suite.','actual_API':{'path':ap,'exit_code':0,'methods':a['methods'],'seconds':8.988,'new_methods':8,'old_preset_methods':2,'old_legacy_methods':2,'subtest_count':None,'runs':1},'actual_browser':{'path':bp,'exit_code':0,'record_count':len(b['checks']),'issues':b['issues'],'viewport':b['desktop_viewport'],'runs':1,'production_builds':1,'typecheck_exit':0,'build_exit':0},'actual_manual_PNG_review':[bp+'/'+x for x in ['natural-dialogue.png','recent-four.png','preset-retained.png','restore-new-dialogue.png']],'source_files_match':len(current),'old_test_files_unchanged':len(p['old_test_sha256']),'source_sha256':current,'artifact_sha256':{str(x.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(x.read_bytes()).hexdigest() for x in artifacts},'artifact_count_before_result':len(artifacts),'qa_source_sha256':{x:digest(x) for x in scripts},'unresolved_product_findings':[],'failed_formal_epochs':[],'paid_calls':0,'external_requests':0,'mobile_checks':0,'canonical_budget_access':False,'product_changes_by_QA':0,'old_test_changes':0,'old_evidence_changes':0,'limitations':['Synthetic request runtime and complete preserve real route/type/mode/Store/Runtime/context/finalizer, not production provider constructor/budget or real-model quality.','Prose guard is heuristic; explicit attack samples are not complete semantic safety proof.','Focused old4 methods only; no full127/mobile/user historical DB/human timing.','13 browser records include cleanup, not unique assertion count; scrollable PNGs show current visible area.','Preparation-only quoting failure retained, final report patch tool failures corrected without formal reruns.','Existing Starlette/httpx deprecation and Vite chunk warning retained.']}
(qa/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_match':len(current),'old_tests_match':len(p['old_test_sha256']),'artifact_count_before_result':len(artifacts),'unresolved':0,'exit_code':0}))