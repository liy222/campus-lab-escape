"""Main: record explicit human approvals; verify final candidate and exact calibration bytes."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sha = lambda value: hashlib.sha256(value).hexdigest()

async def main():
    path = ROOT/'evidence/qa/T27-CH01-event-20261005T115700Z/result.json'
    raw = path.read_bytes()
    assert sha(raw) == '958c67a1c3fb3d54e1f1af48b14cd8aa57dc1d58e66f187f0ec6e8bd3d9810e0'
    qa = json.loads(raw)
    assert qa['checks'] == qa['passed'] == 79 and not qa['failures']
    sources = qa['sources_before']
    assert len(sources) == 52 and sources == qa['sources_after']
    for name, digest in sources.items():
        assert sha((ROOT/name).read_bytes()) == digest, name
    from evaluation.trust import load_tools
    from evaluation.engine import Evaluator
    from evaluation.provider import MockProvider
    freeze, files, tools = load_tools()
    preview = json.loads((ROOT/'evidence/integration/calibration-payload-preview-20261005.json').read_bytes())
    captures = []
    class Capture(MockProvider):
        async def complete(self, messages):
            payload = {'model':'deepseek-flash','messages':messages,'max_tokens':1000,
                       'thinking':{'type':'disabled'},'stream':False}
            wire = json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
            captures.append({'case_id':case['case_id'],'wire_sha256':sha(wire),'payload':payload})
            return await super().complete(messages)
    for case in files['fixtures/cases.json']['cases']:
        await Evaluator(tools,files,Capture([case['mock_suggestion']])).evaluate(case['claim'],case['contract_id'],case['contract_version'])
    assert len(captures) == 3
    for actual, accepted in zip(captures, preview['requests'], strict=True):
        assert all(actual[key] == accepted[key] for key in actual)
        assert accepted['destination'] == 'https://api.deepseek.com/chat/completions'
    gates = json.loads((ROOT/'evaluation/trusted/paid-gates.json').read_bytes())
    gate = gates['approvals'][0]
    assert len(gates['approvals']) == 1 and gate['approval_id'] == 'K1K6-20261005T110203Z'
    assert gate['input_sha256'] == freeze['fixture_set_sha256']
    assert datetime.now(timezone.utc) < datetime.fromisoformat(gate['expires_at'])
    record = {'recorded_at':datetime.now(timezone.utc).isoformat(),
              'human_answers':{'49_continuation':'批准这49个实验载荷外发','3_calibration':'批准这三个校准载荷外发'},
              'destination':'https://api.deepseek.com/chat/completions','original_project_cap_cny':10,
              'continuation_max_calls':49,'continuation_additional_cap_cny':5.30,
              'calibration_max_calls':3,'calibration_additional_cap_cny':0.22,
              'previews':{name:sha((ROOT/name).read_bytes()) for name in [
                  'evidence/integration/continuation-payload-preview-20261005.json',
                  'evidence/integration/calibration-payload-preview-20261005.json']},
              'new_candidate_qa':str(path.relative_to(ROOT)),'new_candidate_qa_sha256':sha(raw),
              'current_sources':sources,'calibration_wire_hashes':[c['wire_sha256'] for c in captures],
              'scope':'Actual user answers authorize only these 52 exact payloads. No replay of original 22 responses or timeout; no extra allowance. Unknown usage stops. This verification performs no network call or ledger write.'}
    output = ROOT/'evidence/integration/external-payload-human-approval-20261005.json'
    with output.open('x',encoding='utf-8') as handle:
        json.dump(record,handle,ensure_ascii=False,indent=2); handle.write('\n')
    print(json.dumps({'verified_sources':len(sources),'exact_calibration_payloads':len(captures),'network_calls':0,'record':str(output.relative_to(ROOT))}))

if __name__ == '__main__':
    asyncio.run(main())
