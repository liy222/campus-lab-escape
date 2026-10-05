"""Credential-free payload preview only. Never writes gates, ledger, environment or dispatches."""
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sha=lambda raw:hashlib.sha256(raw).hexdigest()

async def main():
    from evaluation.trust import load_tools
    from evaluation.engine import Evaluator
    from evaluation.provider import MockProvider,cost_units
    freeze,files,tools=load_tools()
    rows=[]
    class Capture(MockProvider):
        async def complete(self,messages):
            payload={'model':'deepseek-flash','messages':messages,'max_tokens':1000,'thinking':{'type':'disabled'},'stream':False}
            raw=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
            rows.append({'job':job,'claim_id':claim['claim_id'],'wire_sha256':sha(raw),
                         'reservation_units':cost_units(len(raw)*4+8192,1000),'payload':payload})
            return await super().complete(messages)
    job='K4-remaining'
    case=next(c for c in files['fixtures/cases.json']['cases'] if c['case_id']=='K4-failure-with-injection')
    claim=case['claim']
    prior=json.loads((ROOT/'evaluation/runs/20261005T120430742113Z/report.json').read_bytes())
    audit=next(a for a in prior['audits'] if a['case_id']==case['case_id'])
    assert audit['provider_metadata'] is None and audit['validation_errors']==['PRIOR_CALL_UNKNOWN_STOP']
    await Evaluator(tools,files,Capture([case['mock_suggestion']])).evaluate(claim,case['contract_id'],case['contract_version'])
    approved=json.loads((ROOT/'evidence/integration/calibration-payload-preview-20261005.json').read_bytes())
    old=next(r for r in approved['requests'] if r['case_id']==case['case_id'])
    assert rows[0]['wire_sha256']==old['wire_sha256'] and rows[0]['payload']==old['payload']
    for job in ['E1-formal-review-v2','CH01-adversarial-review-v3']:
        for claim in tools.event_contexts[job].claims:
            script={'claim_id':claim['claim_id'],'release_id':claim['release_id'],'status':'INSUFFICIENT_EVIDENCE',
                    'evidence_refs':[{'evidence_id':r['evidence_id'],'snippet':r['snippet']} for r in claim['evidence_refs']],
                    'reason':'Preview only; no model judgement.','missing_check':['Actual approved judgement.']}
            await Evaluator(tools,files,Capture([script])).evaluate(claim)
    assert [sum(r['job']==j for r in rows) for j in ['K4-remaining','E1-formal-review-v2','CH01-adversarial-review-v3']]==[1,2,3]
    out=ROOT/'evidence/integration/remaining-evaluation-payload-preview-20261005.json'
    record={'created_at':datetime.now(timezone.utc).isoformat(),'destination':'https://api.deepseek.com/chat/completions',
            'requests':rows,'maximum_requests':6,'reservation_sum_units':sum(r['reservation_units'] for r in rows),
            'original_project_cap_cny':10,'credentials_included':False,'network_calls':0,
            'gate_mutations':0,'ledger_reads_or_writes':0,
            'purpose':'One previously approved but uncalled K4 exact payload; two original stopped E1 review claims and three CH01 engineering review claims. Public registered evidence only; no secret or token. E1 does not certify new merged outcomes.',
            'authorization':'Preview only; no new dispatch authorization, trusted gate or model result is created.'}
    with out.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'preview':str(out.relative_to(ROOT)),'payloads':len(rows),'reservation_sum_units':record['reservation_sum_units'],'network_calls':0,'gate_changes':0}))
if __name__=='__main__':asyncio.run(main())
