"""Export only the three frozen evaluator request payloads for human review; no network."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
async def main():
    from evaluation.trust import load_tools
    from evaluation.engine import Evaluator
    from evaluation.provider import MockProvider
    freeze,files,tools=load_tools()
    output=ROOT/'evidence/integration/calibration-payload-preview-20261005.json'
    if output.exists():raise ValueError('immutable preview already exists')
    requests=[]
    class Capture(MockProvider):
        async def complete(self,messages):
            payload={'model':'deepseek-flash','messages':messages,'max_tokens':1000,'thinking':{'type':'disabled'},'stream':False}
            raw=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
            requests.append({'case_id':case['case_id'],'destination':'https://api.deepseek.com/chat/completions',
                             'wire_sha256':hashlib.sha256(raw).hexdigest(),'payload':payload})
            return await super().complete(messages)
    for case in files['fixtures/cases.json']['cases']:
        await Evaluator(tools,files,Capture([case['mock_suggestion']])).evaluate(case['claim'],case['contract_id'],case['contract_version'])
    assert len(requests)==3
    approval=json.loads((ROOT/'evidence/integration/calibration-K1K6-20261005T110203Z-approval.json').read_bytes())
    assert [r['wire_sha256'] for r in requests]==[r['wire_sha256'] for r in approval['payload_bounds']]
    output.write_text(json.dumps({'purpose':'Human review only; no dispatch performed','requests':requests,
                                 'credentials_included':False,'actual_network_calls':0},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Created credential-free frozen payload preview:',output)
if __name__=='__main__':asyncio.run(main())
