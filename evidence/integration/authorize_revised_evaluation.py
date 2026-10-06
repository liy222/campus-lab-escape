"""Main trusted finite gates for the eight new-version explicitly human-approved payloads."""
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def main():
    approval=ROOT/'evidence/integration/revised-evaluation-human-approved-20261006.json'
    assert approval.is_file(), 'Concrete human approval required before gate mutation'
    human=json.loads(approval.read_bytes())
    assert human['maximum_requests']==8 and human['preview_raw_sha256']=='43c4a515c4570a2f5fdb3e383c44b09d2a3ef6f60d1be2877953d386cb15d30f'
    preview_path=ROOT/'evidence/integration/revised-evaluation-payload-preview-20261006.json'
    raw=preview_path.read_bytes();preview=json.loads(raw)
    assert preview['destination']=='https://api.deepseek.com/chat/completions'
    assert sha(raw)==human['preview_raw_sha256']
    assert len(preview['requests'])==8 and preview['reservation_sum_units']==2181664000
    assert sha((ROOT/'evaluation/engine.py').read_bytes())==preview['engine_raw_sha256']=='2e9778f186c8191a475db9fa359a06dea8725cd4733872c450bf261d0cbfb74c'
    qa=json.loads((ROOT/'evidence/qa/T27-prompt-fix-20261005T163034187429Z/result.json').read_bytes())
    assert qa['exit_code']==0 and len(qa['checks'])==223 and all(c['passed'] for c in qa['checks']) and not qa['failures']
    assert qa['source_before']==qa['source_after'] and len(qa['source_after'])==81
    for name,digest in qa['source_after'].items():assert sha((ROOT/name).read_bytes())==digest,name
    from evaluation.trust import load_tools
    from evaluation.provider import cost_units,validate_gate
    freeze,files,tools=load_tools()
    with sqlite3.connect((ROOT/'data/ai-budget.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('SELECT id,cap,frozen FROM budget_config').fetchall()==[(1,10000000000,0)]
        assert db.execute("SELECT COUNT(*) FROM budget_calls WHERE state!='settled'").fetchone()[0]==0
        calls,total=db.execute('SELECT COUNT(*),SUM(charged) FROM budget_calls').fetchone()
    assert calls>=93 and total>=668423280 and total+2181664000<10000000000
    stamp=datetime.now(timezone.utc);jobs=[]
    pricing=json.loads((ROOT/'evidence/integration/pricing-check-20261005-live.json').read_bytes())
    assert 0<=(stamp-datetime.fromisoformat(pricing['checked_at_utc'])).total_seconds()<86400
    for prefix,job,purpose in [('Kfix','revised-calibration','calibration'),('E1fix','E1-formal-review-v2','claims'),('CHfix','CH01-adversarial-review-v3','claims')]:
        rows=[row for row in preview['requests'] if row['job']==job]
        assert len(rows)==(3 if prefix=='Kfix' else 2 if prefix=='E1fix' else 3)
        for row in rows:
            encoded=json.dumps(row['payload'],ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
            assert sha(encoded)==row['wire_sha256']
            assert row['reservation_units']==cost_units(len(encoded)*4+8192,1000)
        input_hash=freeze['fixture_set_sha256'] if purpose=='calibration' else tools.event_contexts[job].input_sha256
        gate={'approval_id':prefix+'-'+stamp.strftime('%Y%m%dT%H%M%SZ'),'approved_by':'Main','purpose':purpose,'input_sha256':input_hash,
              'max_calls':len(rows),'max_cost_units':sum(row['reservation_units'] for row in rows),'max_tokens':1000,'timeout_seconds':20,
              'expires_at':(stamp+timedelta(hours=12)).isoformat(),'credential_env':'EVALUATION_MODEL_API_KEY',
              'base_url':'https://api.deepseek.com','model':'deepseek-flash'}
        validate_gate(gate,input_hash=input_hash)
        jobs.append({'job':job,'gate':gate})
    gate_path=ROOT/'evaluation/trusted/paid-gates.json';before=gate_path.read_bytes();gates=json.loads(before)
    assert len(gates['approvals'])==4 and gates['approvals'][0]['approval_id']=='K1K6-20261005T110203Z'
    output=ROOT/'evidence/integration/revised-evaluation-gates-20261006.json'
    with output.open('x',encoding='utf-8') as f:
        json.dump({'created_at':stamp.isoformat(),'human_reply_exact':human['human_reply_exact'],'human_approval_record':str(approval.relative_to(ROOT)),
                   'preview':str(preview_path.relative_to(ROOT)),'preview_raw_sha256':sha(raw),'jobs':jobs,
                   'budget_before':{'calls':calls,'charged_upper_units':total,'original_cap_units':10000000000},
                   'gate_before_raw_sha256':sha(before),'maximum_new_requests':8,'reservation_sum_units':2181664000,
                   'limits':'One attempt per exact payload. Old-version evaluation and experiment failure records retained without replay. These are explicitly approved new prompt versions. No supplier fees asserted; full maximum retained for failures. A new uncertainty stops the current job. No score or human signoff.'},f,ensure_ascii=False,indent=2);f.write('\n')
    gates['approvals'].extend(row['gate'] for row in jobs)
    gates['note']='Finite Main gates for exact explicitly approved eight new-version payloads; original used gate preserved, original CNY10 shared cap unchanged.'
    gate_path.write_text(json.dumps(gates,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'jobs':jobs,'record':str(output.relative_to(ROOT))},ensure_ascii=False))
if __name__=='__main__':main()
