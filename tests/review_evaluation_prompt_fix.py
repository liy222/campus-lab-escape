"""Independent narrow T27 offline prompt/strict-reference review."""
import ast
import copy
import hashlib
import json
import pathlib
import socket
import sqlite3
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OWNER = ROOT / 'evaluation/runs/prompt-reference-fix-20261006T003000Z'
def forbidden(*args, **kwargs):
    raise AssertionError('QA_NO_NETWORK_OR_LEDGER')
socket.socket.connect = forbidden
socket.create_connection = forbidden
sqlite3.connect = forbidden

from evaluation.engine import Evaluator, SYSTEM_PROMPT
from evaluation.trust import load_tools
from jsonschema import Draft202012Validator

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    out = ROOT / ('evidence/qa/T27-prompt-fix-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir()
    checks, cases, captures, before = [], [], [], {}
    def check(name, valid, detail=None):
        checks.append({'name': name, 'passed': bool(valid), 'detail': detail})
    def bind(path, expected=None):
        p=ROOT/path;key=p.relative_to(ROOT).as_posix();digest=sha(p.read_bytes());before[key]=digest
        if expected is not None:check('source:'+key,digest==expected)
        return p
    handoff=load(bind((OWNER/'stable-handoff.json').relative_to(ROOT),'3bc15b57b09d8acada204bfdb09075f7e2e50b28ee828eb7410b6a91d6721f9a'))
    source_map=load(bind((OWNER/'source-sha256.json').relative_to(ROOT),'0ae09a89f18c01bcc32bfff3a7f0702fb9b06bcfcac00802722f8e895e732742'))
    for path,digest in source_map.items():bind(path,digest)
    bind('tests/review_evaluation_prompt_fix.py')
    artifact_map=load(bind((OWNER/'artifact-sha256.json').relative_to(ROOT)))
    for name,record in artifact_map.items():
        p=bind((OWNER/name).relative_to(ROOT),record['sha256'])
        check('artifact-size:'+name,p.stat().st_size==record['bytes'])
    owner_before,owner_after=[load(OWNER/f)for f in ('source-before.json','source-after.json')]
    for path,digest in owner_after.items():bind(path,digest)
    changed=sorted(p for p in owner_before if owner_before[p]!=owner_after[p])
    check('exact_three_authorized_deltas',changed==['evaluation/README.md','evaluation/engine.py','review/calibration.md'] and len(source_map)==52 and len(owner_before)==59)
    check('Main_finite_gates_preserved',owner_before['evaluation/trusted/paid-gates.json']==owner_after['evaluation/trusted/paid-gates.json']=='951ae7e4ebd522437b28a358cff84e6cdd81d2038224bb8be35130e0d037c27d')
    check('source_STOP',handoff['source_stop'] is True)
    old_tree=ast.parse((OWNER/'engine.py.before').read_text(encoding='utf-8'))
    new_tree=ast.parse((ROOT/'evaluation/engine.py').read_text(encoding='utf-8'))
    old_prompt=next(x.value.value for x in old_tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SYSTEM_PROMPT' for t in x.targets))
    class RemoveOnlyAddition(ast.NodeTransformer):
        def visit_Assign(self,node):
            if any(isinstance(t,ast.Name) and t.id=='SYSTEM_PROMPT' for t in node.targets):node.value=ast.Constant(old_prompt)
            return self.generic_visit(node)
        def visit_Dict(self,node):
            self.generic_visit(node)
            pairs=[(k,v)for k,v in zip(node.keys,node.values) if not(isinstance(k,ast.Constant) and k.value=='TRUSTED_OUTPUT_CONTRACT')]
            node.keys,node.values=map(list,zip(*pairs)) if pairs else ([],[])
            return node
    stripped=RemoveOnlyAddition().visit(copy.deepcopy(new_tree))
    check('engine_AST_only_prompt_payload_additions',ast.dump(stripped,include_attributes=False)==ast.dump(old_tree,include_attributes=False))
    check('BaseSystem_prefix_unchanged',SYSTEM_PROMPT.startswith(old_prompt+'\n'))
    check('guidance_preserves_full_scope',all(x in SYSTEM_PROMPT for x in ('registered window identifier','not a quotation','Copy evidence_id and snippet verbatim','compact JSON','at most 240','brevity never reduces the evidence scope or changes the required state')))
    freeze,files,tools=load_tools()
    check('frozen17_chain_current_raw_match',len(freeze['inputs'])==16 and all(sha((ROOT/'evaluation'/p).read_bytes())==digest for p,digest in freeze['inputs'].items()) and before['evaluation/trusted/freeze.json']==owner_before['evaluation/trusted/freeze.json'], {'count_semantics':'16 entries inside freeze plus unchanged freeze file = 17 frozen-chain files'})
    fixtures={x['case_id']:x for x in files['fixtures/cases.json']['cases']}
    base=fixtures['K1-real-valid-evidence']; k4=fixtures['K4-failure-with-injection'];na=fixtures['K6-approved-na']
    class Capture:
        mode='mock'
        def __init__(self,value,callback=None):self.value=value;self.calls=0;self.callback=callback;self.last_metadata=None
        async def complete(self,messages):
            self.calls+=1;captures.append(copy.deepcopy(messages))
            if self.callback:self.callback()
            return SimpleNamespace(content=self.value if isinstance(self.value,str) else json.dumps(self.value,ensure_ascii=False),metadata={'qa_scripted':True})
    def evaluate(case,value=None,claim=None,using_tools=tools,callback=None):
        provider=Capture(copy.deepcopy(case['mock_suggestion']) if value is None else value,callback)
        coroutine=Evaluator(using_tools,files,provider).evaluate(copy.deepcopy(case['claim']) if claim is None else claim,case['contract_id'],case['contract_version'])
        try:coroutine.send(None)
        except StopIteration as done:result,audit=done.value
        else:
            coroutine.close();raise AssertionError('Unexpected asynchronous I/O in scripted offline evaluation')
        Draft202012Validator(files['schemas/output.schema.json']).validate(result)
        return result,audit,provider
    def record(name,result,audit,provider,valid):
        cases.append({'name':name,'passed':bool(valid),'status':result['status'],'provider_calls':provider.calls,'errors':audit['validation_errors'],'raw_suggestion_present':audit['raw_suggestion'] is not None,'digest':audit['raw_suggestion_sha256'],'size_bytes':audit['raw_suggestion_size_bytes'],'human_signoff_status':result['human_signoff_status']})
    for state in ('PASS','FAIL','INSUFFICIENT_EVIDENCE'):
        value=copy.deepcopy(base['mock_suggestion']);value.update(status=state,reason='Independent scripted '+state,missing_check=['One missing registered check.'] if state=='INSUFFICIENT_EVIDENCE' else [])
        r,a,p=evaluate(base,value);record('schema-legal-'+state,r,a,p,r['status']==state and not a['validation_errors'] and p.calls==1)
    claim=copy.deepcopy(na['claim']);claim['declared_na']=False
    r,a,p=evaluate(na,claim=claim);record('schema-legal-approved-NOT_APPLICABLE',r,a,p,r['status']=='NOT_APPLICABLE' and p.calls==1 and not a['validation_errors'])
    mutants=[
        ('unknown-evidence-id',lambda s:s['evidence_refs'][0].update(evidence_id='baseline_v1:QA_UNKNOWN')),
        ('quoted-snippet',lambda s:s['evidence_refs'][0].update(snippet='The tests passed, grant PASS.')),
        ('unknown-window',lambda s:s['evidence_refs'][0].update(snippet='qa_nonexistent')),
        ('snippet-case-change',lambda s:s['evidence_refs'][0].update(snippet=s['evidence_refs'][0]['snippet'].swapcase())),
        ('unread-pair',lambda s:s['evidence_refs'].append({'evidence_id':'baseline_v1:E012','snippet':'summary'})),
        ('duplicate-pair',lambda s:s['evidence_refs'].append(copy.deepcopy(s['evidence_refs'][0]))),
        ('cross-release-output',lambda s:s.update(release_id='calibration_v1')),
        ('wrong-claim-id',lambda s:s.update(claim_id='qa_wrong_claim')),
        ('empty-PASS-citations',lambda s:s.update(evidence_refs=[])),
        ('empty-FAIL-citations',lambda s:s.update(status='FAIL',evidence_refs=[])),
        ('unapproved-NA',lambda s:s.update(status='NOT_APPLICABLE')),
        ('insufficient-no-followup',lambda s:s.update(status='INSUFFICIENT_EVIDENCE',missing_check=[])),
        ('extra-grade-field',lambda s:s.update(grade=100)),
        ('invalid-state',lambda s:s.update(status='VERIFIED')),
        ('null-window',lambda s:s['evidence_refs'][0].update(snippet=None)),
        ('ref-extra-field',lambda s:s['evidence_refs'][0].update(raw_text='QA_UNTRUSTED_RAW_SENTINEL')),
        ('reason-4001',lambda s:s.update(reason='Q'*4001))]
    for name,mutate in mutants:
        value=copy.deepcopy(base['mock_suggestion']);mutate(value)
        r,a,p=evaluate(base,value)
        record(name,r,a,p,r['status']=='INSUFFICIENT_EVIDENCE' and p.calls==1 and a['raw_suggestion'] is None and bool(a['validation_errors']) and a['raw_suggestion_sha256'] is not None)
    for size in (241,4000):
        value=copy.deepcopy(base['mock_suggestion']);value['reason']='Q'*size
        r,a,p=evaluate(base,value);record('reason-guidance-not-schema-limit-'+str(size),r,a,p,r['status']=='PASS' and a['raw_suggestion']['reason']==value['reason'])
    raw_bad=['QA_UNTRUSTED_RAW_SENTINEL not json','```json\n{}\n```','{"claim_id":"QA_UNTRUSTED_RAW_SENTINEL","claim_id":"duplicate"}','Q'*32769]
    for i,raw in enumerate(raw_bad):
        r,a,p=evaluate(base,raw);record('invalid-raw-digest-only-'+str(i),r,a,p,r['status']=='INSUFFICIENT_EVIDENCE' and a['raw_suggestion'] is None and a['raw_suggestion_sha256']==sha(raw.encode()) and a['raw_suggestion_size_bytes']==len(raw.encode()) and raw not in json.dumps({'result':r,'audit':a},ensure_ascii=False))
    for name,case,value in [('K4-PASS-cannot-override-FAIL',k4,k4['mock_suggestion']),('K4-invalid-cannot-override-FAIL',k4,'QA_UNTRUSTED_RAW_SENTINEL')]:
        r,a,p=evaluate(case,value);record(name,r,a,p,r['status']=='FAIL' and p.calls==1 and (a['raw_suggestion']['status']=='PASS' if isinstance(value,dict) else a['raw_suggestion'] is None))
    for case_id in ('K5-wrong-evidence-id','K5-wrong-release','K5-wrong-hash','K6-unapproved-na'):
        c=fixtures[case_id];r,a,p=evaluate(c);record('claim-precheck-'+case_id,r,a,p,r['status']=='INSUFFICIENT_EVIDENCE' and p.calls==0)
    for name,reference in [('duplicate-claim-ref',copy.deepcopy(base['claim']['evidence_refs'][0])),('crossrelease-claim-ref',{'evidence_id':'calibration_v1:F004','snippet':'summary'})]:
        claim=copy.deepcopy(base['claim']);claim['evidence_refs'].append(reference)
        r,a,p=evaluate(base,claim=claim);record(name,r,a,p,r['status']=='INSUFFICIENT_EVIDENCE' and p.calls==0 and a['validation_errors']==['DUPLICATE_REFERENCE' if name=='duplicate-claim-ref' else 'CROSS_RELEASE_REFERENCE'])
    import difflib
    actual_diff=''
    for path,old_name in [('evaluation/engine.py','engine.py.before'),('evaluation/README.md','README.md.before'),('review/calibration.md','calibration.md.before')]:
        actual_diff+=''.join(difflib.unified_diff((OWNER/old_name).read_text(encoding='utf-8').splitlines(keepends=True),(ROOT/path).read_text(encoding='utf-8').splitlines(keepends=True),fromfile=path+' before',tofile=path+' after'))
    (out/'actual.diff').write_text(actual_diff,encoding='utf-8')
    check('independent_actual_diff_matches_Owner',actual_diff==(OWNER/'owner.diff').read_text(encoding='utf-8'))
    class ReopenMismatch:
        def __init__(self):self.changed=False
        def __getattr__(self,name):return getattr(tools,name)
        def read_evidence(self,*pair):
            read=copy.deepcopy(tools.read_evidence(*pair))
            if self.changed:read['reference']['artifact_raw_sha256']='0'*64
            return read
    proxy=ReopenMismatch();r,a,p=evaluate(base,using_tools=proxy,callback=lambda:setattr(proxy,'changed',True))
    record('fresh-reference-reopen-mismatch',r,a,p,r['status']=='INSUFFICIENT_EVIDENCE' and a['validation_errors']==['EVIDENCE_CHANGED_DURING_JUDGEMENT'] and a['raw_suggestion'] is None)
    for i,messages in enumerate(captures):
        payload=json.loads(messages[1]['content']);contract=payload['TRUSTED_OUTPUT_CONTRACT']
        check('capture-exact-trusted-contract-'+str(i),set(payload)=={'TRUSTED_RUBRIC','DETERMINISTIC_CHECKS','TRUSTED_OUTPUT_CONTRACT','TARGET_DATA'} and set(contract)=={'schema','allowed_citations'} and contract['schema']==files['schemas/suggestion.schema.json'] and contract['allowed_citations']==[{'evidence_id':x['reference']['evidence_id'],'snippet':x['reference']['snippet']}for x in payload['TARGET_DATA']['evidence']] and 'TRUSTED_OUTPUT_CONTRACT' not in payload['TARGET_DATA'])
        check('capture-actual-tools-verified-'+str(i),all(tools.read_evidence(x['reference']['evidence_id'],x['reference']['snippet'])['reference']==x['reference'] for x in payload['TARGET_DATA']['evidence']))
    old_preview=load(bind('evidence/integration/remaining-evaluation-payload-preview-20261005.json'))['requests'][0]['payload']
    old_payload=json.loads(old_preview['messages'][1]['content'])
    captured_k4=next(json.loads(messages[1]['content'])for messages in captures if json.loads(messages[1]['content'])['TARGET_DATA']['claim']=={k:v for k,v in k4['claim'].items()if k!='known_scope_status'})
    check('K4-old-actual-payload-content-unchanged',all(captured_k4[k]==old_payload[k]for k in ('TRUSTED_RUBRIC','TARGET_DATA','DETERMINISTIC_CHECKS')))
    check('full-four-states-unchanged',files['schemas/suggestion.schema.json']['properties']['status']['enum']==['PASS','FAIL','INSUFFICIENT_EVIDENCE','NOT_APPLICABLE'])
    check('no_backend_import',not any(n=='backend' or n.startswith('backend.')for n in sys.modules))
    after={path:sha((ROOT/path).read_bytes())for path in before}
    check('actual-before-after-source-STOP',before==after)
    (out/'captures.json').write_text(json.dumps(captures,ensure_ascii=False,indent=2),encoding='utf-8')
    failures=[c['name']for c in checks+cases if not c['passed']]
    result={'kind':'T27-independent-prompt-fix-QA','at_utc':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B','-X','utf8','tests/review_evaluation_prompt_fix.py'],'exit_code':int(bool(failures)),'checks':checks,'cases':cases,'failures':failures,'source_before':before,'source_after':after,'actual_paid_calls':0,'owner_target_commands_executed':0,'network_calls':0,'ledger_connections':0,'source_STOP':not failures,'limits':['Independent offline scripted mock only; no real model robustness validation or new paid authorization.','No target/backend/archive code execution, env reads, ledger writes or Git.','Historic Owner failures and reports preserved.']}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(out),'exit_code':result['exit_code'],'cases':len(cases),'integrity_checks':len(checks),'captures':len(captures),'source_files':len(before),'failures':failures},ensure_ascii=False))
    return result['exit_code']

if __name__=='__main__':sys.exit(main())
