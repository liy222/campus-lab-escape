"""Main preparation only: exact 49 first-attempt gate and credential-free payload preview."""
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
def encoded(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def main():
    qa_rel='evidence/qa/T24-continuation-20261005T113100Z/result.json'
    raw=(ROOT/qa_rel).read_bytes();assert sha(raw)=='4d9a25587db93ec25976c4bcfeb02f244284660aa506bc598f8195faed33d534'
    qa=json.loads(raw);assert qa['checks']==qa['passed']==449 and not qa['failures']
    assert qa['sources_before']==qa['sources_after']
    for p,h in qa['sources_before'].items():assert sha((ROOT/p).read_bytes())==h,p
    assert qa['protected_before']==qa['protected_after']
    module_path=ROOT/'experiments/runs/E1-continuation-executor-v1/executor.py'
    spec=importlib.util.spec_from_file_location('main_reviewed_continuation',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    plan=module.prepare()
    saved=json.loads((ROOT/'experiments/runs/20261005T110033349203Z-continuation-plan-50250a53/plan.json').read_bytes())
    assert plan==saved and sha(encoded(plan))=='791fe5976735e4378c658c1c13544e9dda92e0222f8a52f0df9f0f255184ab6e'
    assert plan['reservation_sum_units']==5_299_680_000
    with sqlite3.connect((ROOT/'data/ai-budget.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('SELECT id,cap,frozen FROM budget_config').fetchall()==[(1,10_000_000_000,0)]
        rows=db.execute('SELECT id,state,charged FROM budget_calls').fetchall()
    assert len(rows)==35 and sum(r[2] for r in rows)==277_602_960 and all(r[1]=='settled' for r in rows)
    timestamp=datetime.now(timezone.utc);ident='E1-continuation-'+timestamp.strftime('%Y%m%dT%H%M%SZ')
    pricing='evidence/integration/pricing-check-20261005-live.json'
    closure='evidence/integration/timeout-human-fee-20261005-applied.json'
    gate={'id':ident,'approved_by':'Main','approved':True,'kind':module.KIND,'phase':'continuation','max_calls':49,
          'additional_upper_cap_units':5_300_000_000,'expires_at':(timestamp+timedelta(hours=12)).isoformat(),
          'plan_hash':sha(encoded(plan)),'original_freeze_hash':module.FREEZE_SHA,'original_plan_hash':module.PLAN_SHA,
          'origin_run_id':plan['origin_run_id'],'selected_identity_hash':plan['selected_identity_hash'],
          'execution_sources_hash':sha(encoded(plan['execution_sources'])),'archive_index_sha256':module.ARCHIVE_SHA,
          'baseline_manifest_sha256':module.MANIFEST_SHA,'dependencies_hash':sha(encoded(plan['dependencies'])),
          'pricing_evidence':pricing,'pricing_sha256':sha((ROOT/pricing).read_bytes()),
          'pilot_run_id':'20261005T052822923700Z-pilot-real-0378672e',
          'pilot_summary_sha256':sha((ROOT/'experiments/runs/20261005T052822923700Z-pilot-real-0378672e/summary.json').read_bytes()),
          'pilot_review_accepted':True,'candidate_qa_evidence':qa_rel,'candidate_qa_sha256':sha(raw),'candidate_qa_accepted':True,
          'accounting_closure_evidence':closure,'accounting_closure_sha256':sha((ROOT/closure).read_bytes()),'accounting_closure_accepted':True,
          'note':'At most one first attempt for each of the exact original49 not_called units. Never resend original22 responses/timeout. Original shared CNY10 only; another uncertainty stops. Execution still subject to normal approval review.',
          'budget_snapshot':{'calls':35,'charged_upper_units':277_602_960,'remaining_units':9_722_397_040,'cap_units':10_000_000_000}}
    module.validate_gate(gate,plan,module.read_ledger())
    requests=[]
    for row in plan['rows']:
        wire=module.wire_bytes(json.loads((module.ORIGIN/'inputs'/(row['row_id']+'.json')).read_bytes()))
        assert sha(wire)==row['input_hash']
        requests.append({'row_id':row['row_id'],'original_order':row['order'],'wire_sha256':sha(wire),'payload':json.loads(wire)})
    preview=ROOT/'evidence/integration/continuation-payload-preview-20261005.json'
    with preview.open('x',encoding='utf-8') as f:json.dump({'destination':'https://api.deepseek.com/chat/completions','credentials_included':False,
        'purpose':'Exact original visible-game inputs only; hidden ground truth remains offline. No request dispatched by this preparation.',
        'max_calls':49,'additional_upper_cap_cny':5.30,'actual_network_calls':0,'requests':requests},f,ensure_ascii=False,indent=2);f.write('\n')
    path=ROOT/'experiments/authorizations'/(ident+'.json');path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(gate,f,ensure_ascii=False,indent=2);f.write('\n')
    result={'authorization':str(path.relative_to(ROOT)),'authorization_raw_sha256':sha(path.read_bytes()),'gate':gate,
            'payload_preview':str(preview.relative_to(ROOT)),'payload_preview_sha256':sha(preview.read_bytes()),
            'actual_network_calls':0,'independent_review_checks':449,'sources_verified':qa['sources_before']}
    with (ROOT/f'evidence/integration/{ident}-preparation.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['gate','sources_verified']},ensure_ascii=False))
if __name__=='__main__':main()
