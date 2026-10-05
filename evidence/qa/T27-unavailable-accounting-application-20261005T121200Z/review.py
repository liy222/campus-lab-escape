"""Independent postapply ledger read only; never import or invoke the helper."""
import hashlib,json,sqlite3,sys
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
PRE=ROOT/'evidence/qa/T27-unavailable-accounting-20261005T120700Z/result.json'
RECORD=ROOT/'evidence/integration/unavailable-human-fee-20261005-applied.json'
HELPER=ROOT/'evidence/integration/reconcile_unavailable_upper.py'
CALL='6dfc591c79c54544afe6d70eec6d697b';BOUND=94536000
COLS='id,scope,created_at,reserved,charged,state,reason,prompt_tokens,completion_tokens,cache_hit_tokens'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def snapshot():
    ledger=ROOT/'data/ai-budget.sqlite'
    with closing(sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None)) as ro:
        return dict(config=ro.execute('SELECT id,cap,frozen FROM budget_config ORDER BY id').fetchall(),all_calls=ro.execute('SELECT '+COLS+' FROM budget_calls ORDER BY id').fetchall(),totals=ro.execute('SELECT COUNT(*),SUM(charged) FROM budget_calls').fetchone(),states=ro.execute('SELECT state,COUNT(*) FROM budget_calls GROUP BY state ORDER BY state').fetchall(),schema_triggers=ro.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall())
checks=[]
def check(n,v,d=None):checks.append(dict(name=n,passed=bool(v),details=d))
pre=load(PRE);record=load(RECORD);now=snapshot();old=pre['original_ledger_before'];oldrows={r[0]:r for r in old['all_calls']};newrows={r[0]:list(r) for r in now['all_calls']}
expected=list(oldrows[CALL]);expected[5:7]=['settled','HUMAN_FEE_REPORTED_UPPER_RETAINED']
check('preQA130_pinned_pass',pre['checks']==pre['passed']==130 and not pre['failures'] and pre['original_ledger_before']==pre['original_ledger_after'])
check('exact83_unique_same_IDs',len(newrows)==len(oldrows)==83 and set(newrows)==set(oldrows))
for id,row in oldrows.items():check('exact_row:'+id,newrows.get(id)==(expected if id==CALL else row))
check('fullbound_tokensNULL_unchanged',newrows[CALL][3:5]==[BOUND,BOUND] and newrows[CALL][7:]==[None,None,None])
check('totals83_448961840_retained',list(now['totals'])==old['totals']==[83,448961840])
check('config_cap10_frozen0_unchanged',now['config']==[(1,10000000000,0)] and [list(r) for r in now['config']]==old['config'])
check('settled83_pending0',now['states']==[('settled',83)] and not any(r[5] in ('unknown','reserved') for r in now['all_calls']))
check('triggers_unchanged',[list(r) for r in now['schema_triggers']]==old['schema_triggers'])
check('Main_actual_record_target_only',record['applied'] is True and record['already_closed'] is False and record['call_id']==CALL and record['before']==oldrows[CALL] and record['after']==expected)
check('Main_actual_record_fullupper_no_invoice',record['calls']==83 and record['charged_upper_units']==448961840 and record['cap_units']==10000000000 and record['retained_charge_units']==BOUND and record['human_reported_cost_units']==90000000 and record['provider_usage_known'] is False and record['provider_invoice_independently_verified'] is False)
check('helper_exact_reviewed151b_pin',sha(HELPER)==record['helper_raw_sha256']==pre['helper_raw_sha256']=='151b30144e1f440e3abb8c7901d3e27c180601d742fcfcb24f15d7e5989175b8')
check('prior_timeout_helper_fee_raw_evidence_preserved',all(sha(ROOT/p)==h for p,h in pre['protected_prior_files'].items()))
check('post_readonly_snapshot_stable',now==snapshot())
result=dict(task='T27-unavailable-accounting-postapply-independent',created_at=datetime.now(timezone.utc).isoformat(),actual_command=[sys.executable,'-B','-X','utf8',str(Path(__file__).relative_to(ROOT))],checks=len(checks),passed=sum(c['passed'] for c in checks),failures=[c for c in checks if not c['passed']],preQA_result_raw_sha256=sha(PRE),Main_applied_record_raw_sha256=sha(RECORD),helper_raw_sha256=sha(HELPER),QA_review_raw_sha256=sha(Path(__file__)),original_preapply=old,original_postapply=now,original_ledger_mode='ro',original_apply_executed_by_QA=False,actual_paid_calls=0,actual_network_calls=0,provider_invoice_independently_verified=False,limits=['Main apply actual exit0/chunk9eb52f supplied by Main; QA independently observes record plus exact postapply ledger, not Main process live.','Only target state/reason changed across all83 full rows compared with actual preQA snapshot.','NULL usage/HTTP uncertainty and full upper retained; human0.09 is not independent invoice.'])
save(OUT/'checks.json',checks);save(OUT/'result.json',result)
print(json.dumps(dict(checks=result['checks'],passed=result['passed'],failed=len(result['failures']),result_sha256=sha(OUT/'result.json'),review_sha256=sha(Path(__file__)),applied_record_sha256=sha(RECORD))))
raise SystemExit(bool(result['failures']))
