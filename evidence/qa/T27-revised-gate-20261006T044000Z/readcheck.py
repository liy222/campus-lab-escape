"""Static/data-only Main helper review, not evaluation engine certification."""
import ast,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
pins={}
def raw(n):
    b=(ROOT/n).read_bytes();pins[n]=sha(b);return b
def read(n):return json.loads(raw(n))
checks=[]
def check(n,v):checks.append({'name':n,'passed':bool(v)})
helper=raw('evidence/integration/authorize_revised_evaluation.py').decode('utf-8-sig');tree=ast.parse(helper)
human=read('evidence/integration/revised-evaluation-human-approved-20261006.json')
preview=read('evidence/integration/revised-evaluation-payload-preview-20261006.json')
qa=read('evidence/qa/T27-prompt-fix-20261005T163034187429Z/result.json')
pricing=read('evidence/integration/pricing-check-20261005-live.json')
gates=read('evaluation/trusted/paid-gates.json')
freeze=read('evaluation/trusted/freeze.json');registry=read('evaluation/trusted/events-registry-v1.json')
engine=raw('evaluation/engine.py')
check('concrete approval record exists/exact human',human['human_reply_exact']=='批准这 8 项新版评价载荷外发')
check('required approval guard before writes',helper.index('assert approval.is_file()')<helper.index("with output.open('x'"))
check('approval+preview raw exact pin',human['preview_raw_sha256']==pins['evidence/integration/revised-evaluation-payload-preview-20261006.json']=='43c4a515c4570a2f5fdb3e383c44b09d2a3ef6f60d1be2877953d386cb15d30f')
check('exact eight count+sum',human['maximum_requests']==len(preview['requests'])==8 and human['reservation_sum_units']==preview['reservation_sum_units']==sum(r['reservation_units'] for r in preview['requests'])==2181664000)
check('approved destination/no credential preview',preview['destination']==human['destination']=='https://api.deepseek.com/chat/completions' and preview['credentials_included'] is False and preview['network_calls']==preview['gate_or_ledger_changes']==0)
check('engine exact pin only / not recertification',sha(engine)==preview['engine_raw_sha256']=='2e9778f186c8191a475db9fa359a06dea8725cd4733872c450bf261d0cbfb74c')
check('other Agent 223 checks/81 unchanged stored evidence',qa['exit_code']==0 and len(qa['checks'])==223 and all(c['passed'] for c in qa['checks']) and not qa['failures'] and qa['source_before']==qa['source_after'] and len(qa['source_after'])==81)
actual81={n:sha((ROOT/n).read_bytes()) for n in qa['source_after']}
check('current81 exact independentQA source map',actual81==qa['source_after'])
check('helper pins223 and81 before gates',"len(qa['checks'])==223" in helper and "len(qa['source_after'])==81" in helper and helper.index("for name,digest in qa['source_after'].items()")<helper.index("with output.open('x'"))
check('original root DB read-only fixedpath',"(ROOT/'data/ai-budget.sqlite').as_uri()+'?mode=ro'" in helper and "uri=True" in helper)
check('no create reset budget/write SQL',all(s not in helper.upper() for s in ['CREATE TABLE','UPDATE BUDGET','INSERT INTO','DELETE FROM','DROP TABLE']))
check('original cap10/config frozen guard',"[(1,10000000000,0)]" in helper and "WHERE state!='settled'" in helper)
check('all-scope unknown/reserved reject',"SELECT COUNT(*) FROM budget_calls WHERE state!='settled'" in helper and 'scope=' not in helper)
check('fresh count/total budget runtimeguard',"assert calls>=93 and total>=668423280 and total+2181664000<10000000000" in helper)
check('recorded snapshot budget cap margin only',668423280+2181664000<10000000000 and human['original_project_budget_cny']==10)
now=datetime.now(timezone.utc);age=(now-datetime.fromisoformat(pricing['checked_at_utc'])).total_seconds()
check('existing pricing snapshot younger than24h at read',0<=age<86400)
check('helper runtimepricing exact24h check',"0<=(stamp-datetime.fromisoformat(pricing['checked_at_utc'])).total_seconds()<86400" in helper)
check('pricing fixed peak bound rates',pricing['http_status']==200 and pricing['base_url']=='https://api.deepseek.com' and pricing['peak_cny_per_million']=={'input_miss':2,'input_hit':0.04,'output':8})
check('original four gates retained identities',len(gates['approvals'])==4 and [g['approval_id'] for g in gates['approvals']]==['K1K6-20261005T110203Z','K4rem-20261005T155623Z','E1eval-20261005T155623Z','CH01eval-20261005T155623Z'])
check('append extension preserves complete originals',"gates['approvals'].extend(row['gate'] for row in jobs)" in helper and "gates['approvals']=" not in helper)
check('append-only evidence/output exclusive',"with output.open('x',encoding='utf-8')" in helper)
check('gateonly no provider constructor/model call',all(n not in helper for n in ['PaidProvider(','.complete(','.credential(','.env','os.environ','httpx','urllib']))
check('fixed gate params',all(s in helper for s in ["'max_tokens':1000","'timeout_seconds':20","timedelta(hours=12)","'model':'deepseek-flash'","'base_url':'https://api.deepseek.com'"]))
check('gate builtin validation/pinned input',"validate_gate(gate,input_hash=input_hash)" in helper and "freeze['fixture_set_sha256'] if purpose=='calibration' else tools.event_contexts[job].input_sha256" in helper)
jobs=['revised-calibration','E1-formal-review-v2','CH01-adversarial-review-v3']
check('group count3/2/3',[sum(r['job']==j for r in preview['requests']) for j in jobs]==[3,2,3])
check('calibration exact selected cases',[r['fixture_case_id'] for r in preview['requests'][:3]]==['K1-real-valid-evidence','K2-explicit-failure','K4-failure-with-injection'])
check('event exact claims',[r['claim_id'] for r in preview['requests'][3:]]==['E1-formal-review-v2:A24','E1-formal-review-v2:A26','CH01-adversarial-review-v3:A27','CH01-adversarial-review-v3:A21','CH01-adversarial-review-v3:A23'])
eventpins={e['release_id']:e['event_freeze_raw_sha256'] for e in registry['events']}
check('all input fixture/event hashes exact',freeze['fixture_set_sha256']=='58423418e0f336899fbeffc1439f007f73bd4206d54f09e10121235dc56fabe1' and eventpins=={'E1-formal-review-v2':'6ac8f14b3b8f4abf38fcc1e60327062540fc1678c9feb04546c34f61fd918a84','CH01-adversarial-review-v3':'5eb36ad053d05a5285fd6dd22fe25983d575c5597abe5d8441fb5ed6457aee6d'})
for i,r in enumerate(preview['requests'],1):
    payload=r['payload'];encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    check(str(i)+' exact approved provider serialization/hash',sha(encoded)==r['wire_sha256'] and set(payload)=={'model','messages','max_tokens','thinking','stream'} and payload['model']=='deepseek-flash' and payload['max_tokens']==1000 and payload['thinking']=={'type':'disabled'} and payload['stream'] is False)
    check(str(i)+' conservative reservation bytesbound',r['reservation_units']==(len(encoded)*4+8192)*2000+1000*8000)
for n,h in pins.items():check('before/after '+n,sha((ROOT/n).read_bytes())==h)
check('81source before/after stable',all(sha((ROOT/n).read_bytes())==h for n,h in actual81.items()))
result={'role':'Independent static review of Main gate helper only; not evaluation engine QA','checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'source_hashes_before_after':pins,'independent_QA81_raw_hashes':actual81,'existing_gate_count':4,'approved_request_counts':[3,2,3],'new_reservation_units':2181664000,'pricing_age_seconds_at_read':age,'read_at_utc':now.isoformat(),'helper_executed':False,'network_calls':0,'environment_read':False,'live_ledger_opened':False,'limitations':['Runtime approval/budget/unknown/price freshness assertions statically inspected, not executed.','No live DB query or gate mutation. 93 settled / upper668423280 are Main stored snapshot facts, not a new independent query.','Existing price evidence freshness checked at read; helper rejects when age reaches24h.','Output uses exclusive-create then gate write; no transactional filesystem/crash simulation in this read-only task.','Eight revised payloads are newly explicitly approved versions, not old-source result correction.']}
(OUT/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':result['checks'],'passed':result['passed'],'failed':result['failed'],'helper_sha256':pins['evidence/integration/authorize_revised_evaluation.py'],'result_sha256':sha((OUT/'result.json').read_bytes())},ensure_ascii=False))
raise SystemExit(0 if not result['failed'] else 1)
