"""Main one-shot relay for the exact approved, previously uncalled K4; no K1/K2 replay."""
import asyncio
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sha=lambda raw:hashlib.sha256(raw).hexdigest()

async def main():
    from evidence.integration.run_paid_evaluation import credential
    from evaluation.trust import load_tools
    from evaluation.engine import Evaluator
    from evaluation.provider import PaidProvider
    auth=json.loads((ROOT/'evidence/integration/remaining-evaluation-human-authorized-20261005.json').read_bytes())
    assert auth['human_reply_exact']=='批准这6个评价载荷外发'
    preview_path=ROOT/auth['preview'];raw=preview_path.read_bytes()
    assert sha(raw)==auth['preview_raw_sha256']
    row=next(r for r in json.loads(raw)['requests'] if r['job']=='K4-remaining')
    gate=next(j['gate'] for j in auth['jobs'] if j['job']=='K4-remaining')
    assert gate in json.loads((ROOT/'evaluation/trusted/paid-gates.json').read_bytes())['approvals']
    prior=json.loads((ROOT/'evaluation/runs/20261005T120430742113Z/report.json').read_bytes())
    old=next(a for a in prior['audits'] if a['case_id']=='K4-failure-with-injection')
    assert old['provider_metadata'] is None and old['validation_errors']==['PRIOR_CALL_UNKNOWN_STOP']
    with sqlite3.connect((ROOT/'data/ai-budget.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute("SELECT COUNT(*) FROM budget_calls WHERE id LIKE ?",('eval_'+gate['approval_id']+'_%',)).fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM budget_calls WHERE state!='settled'").fetchone()[0]==0
    out=ROOT/'evidence/integration/remaining-k4-20261005.json';started=out.with_name(out.stem+'-started.json')
    assert not out.exists() and not started.exists()
    before={p.name:sha(p.read_bytes()) for p in (ROOT/'evaluation').glob('*.py')}
    freeze,files,tools=load_tools()
    case=next(c for c in files['fixtures/cases.json']['cases'] if c['case_id']=='K4-failure-with-injection')
    class ExactProvider(PaidProvider):
        async def complete(self,messages):
            payload={'model':'deepseek-flash','messages':messages,'max_tokens':1000,'thinking':{'type':'disabled'},'stream':False}
            encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
            assert sha(encoded)==row['wire_sha256'] and payload==row['payload']
            return await super().complete(messages)
    metadata={'created_at':datetime.now(timezone.utc).isoformat(),'approval_id':gate['approval_id'],
              'human_reply_exact':auth['human_reply_exact'],'wire_sha256':row['wire_sha256'],
              'previous_k4_network_calls':0,'scope':'One exact remaining K4 only; all original K1/K2 reports unchanged.'}
    with started.open('x',encoding='utf-8') as f:json.dump(metadata,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    previous=os.environ.get('EVALUATION_MODEL_API_KEY')
    try:
        os.environ['EVALUATION_MODEL_API_KEY']=credential()
        provider=ExactProvider(gate,freeze['fixture_set_sha256'])
        result,audit=await Evaluator(tools,files,provider).evaluate(case['claim'],case['contract_id'],case['contract_version'])
    finally:
        if previous is None:os.environ.pop('EVALUATION_MODEL_API_KEY',None)
        else:os.environ['EVALUATION_MODEL_API_KEY']=previous
    after={p.name:sha(p.read_bytes()) for p in (ROOT/'evaluation').glob('*.py')}
    code=0 if result['status']==case['expected'] and before==after else 1
    record={**metadata,'ended_at':datetime.now(timezone.utc).isoformat(),'case_id':case['case_id'],'expected':case['expected'],
            'result':result,'audit':audit,'actual_paid_calls':provider.calls,'exit_code':code,
            'evaluator_sources_before':before,'evaluator_sources_after':after,'source_unchanged':before==after,
            'limits':'Deterministic FAIL may dominate an invalid/unavailable model suggestion. This never changes original10/11 calibration or supplies a human signature.'}
    with out.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'record':str(out.relative_to(ROOT)),'exit_code':code,'actual_paid_calls':provider.calls,'status':result['status']}))
    return code
if __name__=='__main__':raise SystemExit(asyncio.run(main()))
