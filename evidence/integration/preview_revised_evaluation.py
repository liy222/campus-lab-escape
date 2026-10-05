"""Preview new-version calibration and event payloads only; no gates, credentials or dispatch."""
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
    assert sha((ROOT/'evaluation/engine.py').read_bytes())=='2e9778f186c8191a475db9fa359a06dea8725cd4733872c450bf261d0cbfb74c'
    freeze,files,tools=load_tools();rows=[];fixture=None
    class Capture(MockProvider):
        async def complete(self,messages):
            payload={'model':'deepseek-flash','messages':messages,'max_tokens':1000,'thinking':{'type':'disabled'},'stream':False}
            wire=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
            rows.append({'job':job,'fixture_case_id':fixture,'claim_id':claim['claim_id'],'wire_sha256':sha(wire),
                         'reservation_units':cost_units(len(wire)*4+8192,1000),'payload':payload})
            return await super().complete(messages)
    job='revised-calibration'
    for case in files['fixtures/cases.json']['cases']:
        fixture=case['case_id'];claim=case['claim']
        await Evaluator(tools,files,Capture([case['mock_suggestion']])).evaluate(claim,case['contract_id'],case['contract_version'])
    fixture=None
    for job in ['E1-formal-review-v2','CH01-adversarial-review-v3']:
        for claim in tools.event_contexts[job].claims:
            script={'claim_id':claim['claim_id'],'release_id':claim['release_id'],'status':'INSUFFICIENT_EVIDENCE',
                    'evidence_refs':[{'evidence_id':r['evidence_id'],'snippet':r['snippet']} for r in claim['evidence_refs']],
                    'reason':'Preview only; no judgement.','missing_check':['Approved actual judgement.']}
            await Evaluator(tools,files,Capture([script])).evaluate(claim)
    assert [sum(r['job']==j for r in rows) for j in ['revised-calibration','E1-formal-review-v2','CH01-adversarial-review-v3']]==[3,2,3]
    value={'created_at':datetime.now(timezone.utc).isoformat(),'destination':'https://api.deepseek.com/chat/completions',
           'credentials_included':False,'network_calls':0,'gate_or_ledger_changes':0,'requests':rows,
           'reservation_sum_units':sum(r['reservation_units'] for r in rows),'original_budget_cap_cny':10,
           'engine_raw_sha256':sha((ROOT/'evaluation/engine.py').read_bytes()),
           'purpose':'New prompt version explicitly enumerates registered citation IDs and output schema. Same frozen evidence and expected cases; all old failures retained. New-version K1/K2/K4 plus two original E1 and three CH01 claims; not an old-payload retry. No score or human signoff.',
           'authorization':'Preview only. Actual dispatch needs applicable concrete authorization and independent source acceptance.'}
    out=ROOT/'evidence/integration/revised-evaluation-payload-preview-20261006.json'
    with out.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'payloads':len(rows),'reservation_sum_units':value['reservation_sum_units'],'preview':str(out.relative_to(ROOT))}))
if __name__=='__main__':asyncio.run(main())
