"""Narrow offline Owner checks, deliberately not independent QA or paid calibration."""
import asyncio,ast,copy,hashlib,json,socket,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
OUT=Path(__file__).resolve().parent
def forbidden(*a,**k):raise AssertionError('NO_NETWORK_OR_LEDGER_ALLOWED')
socket.socket.connect=forbidden;socket.create_connection=forbidden;sqlite3.connect=forbidden
from evaluation.trust import load_tools
from evaluation.engine import Evaluator,SYSTEM_PROMPT
from evaluation.provider import MockProvider
sha=lambda b:hashlib.sha256(b).hexdigest()
checks=[];payloads=[]
def check(name,ok):checks.append({'name':name,'passed':bool(ok)})
class Capture(MockProvider):
    async def complete(self,messages):
        payloads.append(json.loads(messages[1]['content']))
        return await super().complete(messages)
async def main():
    freeze,files,tools=load_tools()
    cases=files['fixtures/cases.json']['cases'];byid={c['case_id']:c for c in cases}
    for c in cases:
        provider=Capture([c['mock_suggestion']])
        r,a=await Evaluator(tools,files,provider).evaluate(c['claim'],c['contract_id'],c['contract_version'])
        check('frozen '+c['case_id'],r['status']==c['expected'])
        if c['case_id']=='K4-failure-with-injection':
            k4payload=payloads[-1]
            check('K4 mockPASS preserved / finalFAIL dominates',provider.calls==1 and a['raw_suggestion']['status']=='PASS' and r['status']=='FAIL')
    old=json.loads((ROOT/'evidence/integration/remaining-evaluation-payload-preview-20261005.json').read_bytes())['requests'][0]['payload']
    oldpayload=json.loads(old['messages'][1]['content'])
    k4=k4payload
    check('original system prefix unchanged',SYSTEM_PROMPT.startswith(old['messages'][0]['content']+'\n'))
    check('original trusted rubric and target unchanged',all(k4[k]==oldpayload[k] for k in ['TRUSTED_RUBRIC','TARGET_DATA','DETERMINISTIC_CHECKS']))
    for i,p in enumerate(payloads):
        check('payload '+str(i)+' exacttrustedcontract',set(p)=={'TRUSTED_RUBRIC','DETERMINISTIC_CHECKS','TRUSTED_OUTPUT_CONTRACT','TARGET_DATA'} and set(p['TRUSTED_OUTPUT_CONTRACT'])=={'schema','allowed_citations'} and p['TRUSTED_OUTPUT_CONTRACT']['schema']==files['schemas/suggestion.schema.json'] and p['TRUSTED_OUTPUT_CONTRACT']['allowed_citations']==[{'evidence_id':r['reference']['evidence_id'],'snippet':r['reference']['snippet']} for r in p['TARGET_DATA']['evidence']])
        check('payload '+str(i)+' fresh tool hashverified',all(tools.read_evidence(r['reference']['evidence_id'],r['reference']['snippet'])['reference']==r['reference'] for r in p['TARGET_DATA']['evidence']))
    c=byid['K1-real-valid-evidence']
    mutations=[('quoted snippet',lambda s:s['evidence_refs'][0].update(snippet='This is quoted evidence, not a registered ID.'),'MODEL_FAKE_OR_UNREAD_REFERENCE'),('unknown ID',lambda s:s['evidence_refs'][0].update(evidence_id='baseline_v1:UNKNOWN'),'MODEL_FAKE_OR_UNREAD_REFERENCE'),('unread pair',lambda s:s['evidence_refs'].append({'evidence_id':'baseline_v1:E012','snippet':'summary'}),'MODEL_FAKE_OR_UNREAD_REFERENCE'),('crossversion',lambda s:s.update(release_id='calibration_v1'),'MODEL_CLAIM_RELEASE_MISMATCH'),('extra field',lambda s:s.update(confidence=1),'MODEL_SCHEMA_OR_PROVIDER_ERROR'),('duplicate ref',lambda s:s['evidence_refs'].append(copy.deepcopy(s['evidence_refs'][0])),'MODEL_FAKE_OR_UNREAD_REFERENCE')]
    for name,mutate,error in mutations:
        s=copy.deepcopy(c['mock_suggestion']);mutate(s)
        provider=Capture([s]);r,a=await Evaluator(tools,files,provider).evaluate(c['claim'],c['contract_id'],c['contract_version'])
        check(name+' strict unchanged',provider.calls==1 and r['status']=='INSUFFICIENT_EVIDENCE' and a['validation_errors']==[error] and a['raw_suggestion'] is None)
    for state in ['PASS','INSUFFICIENT_EVIDENCE']:
        s=copy.deepcopy(c['mock_suggestion']);s.update(status=state,reason='R'*241,missing_check=['Provide the missing check.'] if state=='INSUFFICIENT_EVIDENCE' else [])
        r,a=await Evaluator(tools,files,Capture([s])).evaluate(c['claim'],c['contract_id'],c['contract_version'])
        check('legal '+state+' / brevity guidance only',r['status']==state and a['validation_errors']==[] and a['raw_suggestion']['reason']==s['reason'])
    c=byid['K2-explicit-failure'];r,a=await Evaluator(tools,files,Capture([c['mock_suggestion']])).evaluate(c['claim'],c['contract_id'],c['contract_version'])
    check('legal model FAIL',r['status']=='FAIL' and a['validation_errors']==[])
    c=byid['K6-approved-na'];claim=copy.deepcopy(c['claim']);claim['declared_na']=False
    provider=Capture([c['mock_suggestion']]);r,a=await Evaluator(tools,files,provider).evaluate(claim,c['contract_id'],c['contract_version'])
    check('legal model NOT_APPLICABLE trusted approval',provider.calls==1 and r['status']=='NOT_APPLICABLE' and a['validation_errors']==[])
    before=json.loads((OUT/'source-before.json').read_bytes());after={n:sha((ROOT/n).read_bytes()) for n in before}
    changed=[n for n in before if before[n]!=after[n]]
    check('only three authorized source files changed',changed==['evaluation/README.md','evaluation/engine.py','review/calibration.md'])
    check('frozen17 chain unchanged',all(before['evaluation/'+n]==after['evaluation/'+n]==h for n,h in freeze['inputs'].items()) and before['evaluation/trusted/freeze.json']==after['evaluation/trusted/freeze.json'])
    check('Main finitegates retained not cleared',before['evaluation/trusted/paid-gates.json']==after['evaluation/trusted/paid-gates.json'] and len(json.loads((ROOT/'evaluation/trusted/paid-gates.json').read_bytes())['approvals'])>0)
    check('no backend module imported',not any(n=='backend' or n.startswith('backend.') for n in sys.modules))
    (OUT/'source-after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf-8')
    (OUT/'captured-messages.json').write_text(json.dumps(payloads,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    result={'checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':[c for c in checks if not c['passed']],'changed':changed,'actual_paid_calls':0,'mode':'offline scripted mock Owner verification','limits':'No provider network/ledger/credentials/target code. Not independent QA; no new real-model verification.'}
    (OUT/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False));return 0 if not result['failed'] else 1
coro=main()
try:
    coro.send(None)
except StopIteration as completed:
    raise SystemExit(completed.value)
else:
    coro.close()
    raise AssertionError('MOCK_CHECK_UNEXPECTED_ASYNC_IO')
