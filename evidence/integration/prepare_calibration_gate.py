"""Main: admit one frozen calibration invocation against the original allowance."""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sha = lambda b: hashlib.sha256(b).hexdigest()

async def main():
    qa_path = ROOT/'evidence/qa/T27-evaluation-events-20261005T105300Z/result.json'
    qa_raw = qa_path.read_bytes()
    assert sha(qa_raw) == 'a5e5b418895c7597932b9792199a9f73b09cc37baf57784825c39c9aab6188d9'
    qa = json.loads(qa_raw)
    assert qa['checks'] == qa['passed'] == 168 and not qa['failures']
    sources = qa['evaluator_sources_before']
    assert sources == qa['evaluator_sources_after'] and len(sources) == 48
    for name, digest in sources.items():
        assert sha((ROOT/name).read_bytes()) == digest, name
    relay = ROOT/'evidence/integration/run_paid_evaluation.py'
    assert sha(relay.read_bytes()) == 'a1561ac38f8756856642a1d7e991d9545d04c5afa591b71d281987f3ab6ebd41'
    with sqlite3.connect((ROOT/'data/ai-budget.sqlite').as_uri()+'?mode=ro', uri=True) as db:
        assert db.execute('SELECT id,cap,frozen FROM budget_config').fetchall() == [(1,10_000_000_000,0)]
        assert db.execute("SELECT COUNT(*) FROM budget_calls WHERE state IN ('unknown','reserved')").fetchone()[0] == 0
        calls,total = db.execute('SELECT COUNT(*),SUM(charged) FROM budget_calls').fetchone()
    assert calls == 35 and total == 277_602_960
    from evaluation.trust import load_tools
    from evaluation.engine import Evaluator
    from evaluation.provider import MockProvider, cost_units
    freeze, files, tools = load_tools()
    captures = []
    class Capture(MockProvider):
        async def complete(self, messages):
            payload = {'model':'deepseek-flash','messages':messages,'max_tokens':1000,
                       'thinking':{'type':'disabled'},'stream':False}
            raw = json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
            bound = len(raw)*4+8192
            captures.append({'case_id':case['case_id'],'wire_sha256':sha(raw),
                             'wire_bytes':len(raw),'input_bound':bound,'reservation_units':cost_units(bound,1000)})
            return await super().complete(messages)
    for case in files['fixtures/cases.json']['cases']:
        provider = Capture([case['mock_suggestion']])
        await Evaluator(tools,files,provider).evaluate(case['claim'],case['contract_id'],case['contract_version'])
    assert [c['case_id'] for c in captures] == ['K1-real-valid-evidence','K2-explicit-failure','K4-failure-with-injection']
    bound = sum(c['reservation_units'] for c in captures)
    assert bound <= 220_000_000 and total+bound <= 10_000_000_000
    timestamp = datetime.now(timezone.utc)
    approval = 'K1K6-'+timestamp.strftime('%Y%m%dT%H%M%SZ')
    gate = {'approval_id':approval,'approved_by':'Main','purpose':'calibration',
            'input_sha256':freeze['fixture_set_sha256'],'max_calls':3,'max_cost_units':220_000_000,
            'max_tokens':1000,'timeout_seconds':20,'expires_at':(timestamp+timedelta(hours=12)).isoformat(),
            'credential_env':'EVALUATION_MODEL_API_KEY','base_url':'https://api.deepseek.com','model':'deepseek-flash'}
    gate_path=ROOT/'evaluation/trusted/paid-gates.json'
    assert json.loads(gate_path.read_bytes())['approvals'] == []
    for name,digest in sources.items():
        assert sha((ROOT/name).read_bytes()) == digest, name
    record={'approved_at':timestamp.isoformat(),'approval':gate,'independent_qa':str(qa_path.relative_to(ROOT)),
            'independent_qa_raw_sha256':sha(qa_raw),'sources_before':sources,'payload_bounds':captures,
            'sum_reservation_units':bound,'original_ledger_before':{'calls':calls,'charged_upper_units':total,'cap_units':10_000_000_000},
            'scope':'One invocation, at most K1/K2/K4 network requests; other eight fixtures deterministic. No retry, no fresh allowance, no human signature.',
            'credential_value_recorded':False,'price_evidence':'evidence/integration/pricing-check-20261005-live.json',
            'allowed_change':'Main finite paid-gates.json only; all evaluator code and 17 original frozen files unchanged.'}
    record_path=ROOT/f'evidence/integration/calibration-{approval}-approval.json'
    with record_path.open('x',encoding='utf-8') as f: json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
    gate_path.write_text(json.dumps({'approvals':[gate],'note':'Finite Main calibration GO within original user CNY10 project budget.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'approval_id':approval,'reservation_units':bound,'gate_raw_sha256':sha(gate_path.read_bytes()),'record':str(record_path.relative_to(ROOT))}))

if __name__=='__main__':asyncio.run(main())
