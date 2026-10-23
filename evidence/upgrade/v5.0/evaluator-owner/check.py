"""Evaluator Owner checks; synthetic inputs, not independent QA."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys
from jsonschema import Draft202012Validator
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from evaluation.v5 import _semantic,load_v5,REGISTRATION_RAW_SHA256
from evaluation.reader import safe_read
from evaluation.common import EvaluationError,PROJECT_ROOT
root=PROJECT_ROOT;checks=[]
def record(name,actual,expected):
    checks.append({'name':name,'actual':actual,'expected':expected,'pass':actual==expected})
h=lambda s:hashlib.sha256(s.encode()).hexdigest()
c2={'checks':{'owner_id':'A','intruder_id':'B','requests':[{'operation':op,'http_status':404,'target_before_sha256':h('a'),'target_after_sha256':h('a')} for op in ('read','restore')]}}
record('C2-complete',_semantic('V5-C2',c2),([],[]))
c2['checks']['requests'][1]['http_status']=200
record('C2-observed-authority-failure',bool(_semantic('V5-C2',c2)[0]),True)
c3={'checks':{'original_definition_sha256':h('definition'),'restores':[{'moment_id':str(i),'saved_state_sha256':h(str(i)),'restored_state_sha256':h(str(i)),'restored_definition_sha256':h('definition')} for i in range(3)],'bad_saves':[{'case_id':'corrupt','rejected':True,'current_before_sha256':h('current'),'current_after_sha256':h('current')}]}}
record('C3-complete',_semantic('V5-C3',c3),([],[]))
c3['checks']['bad_saves'][0]['current_after_sha256']=h('overwritten')
record('C3-observed-overwrite-failure',bool(_semantic('V5-C3',c3)[0]),True)
record('C1-no-execution-coverage',bool(_semantic('V5-C1',{'checks':{}})[1]),True)
for path in ('../AGENTS.md','.env','data/api-key.json','https://example.com/test.json'):
    try:safe_read(root,path);actual='READ'
    except EvaluationError as e:actual=e.code
    record('reader-reject-'+path,actual in {'UNSAFE_PATH','SECRET_OR_BINARY_PATH'},True)
files,tools,context=load_v5();record('registration-main-pin-unset',REGISTRATION_RAW_SHA256,None)
record('real-contract-no-NA',tools.contract['approved_na'],[])
record('real-claims-only',sorted(c['criterion_id'] for c in context.claims),['V5-C1','V5-C2','V5-C3'])
record('unregistered-precheck',context.precheck(tools)['status'],'NOT_READY')
record('only-existing-output-schemas',sorted(files),['schemas/output.schema.json','schemas/suggestion.schema.json'])
Draft202012Validator(json.loads((root/'evaluation/v5/registration.schema.json').read_text(encoding='utf-8'))).validate(json.loads((root/'evaluation/v5/registration.json').read_text(encoding='utf-8')))
record('not-ready-registration-schema',True,True)
module=ast.parse((root/'evaluation/v5.py').read_text(encoding='utf-8'))
imports=[n.module for n in ast.walk(module) if isinstance(n,ast.ImportFrom)]+[a.name for n in ast.walk(module) if isinstance(n,ast.Import) for a in n.names]
record('no-target-ledger-network-imports',not any(x and x.split('.')[0] in {'backend','subprocess','sqlite3','socket','httpx','requests','os'} for x in imports),True)
unchanged=['evaluation/engine.py','evaluation/reader.py','evaluation/provider.py','evaluation/common.py','evaluation/trust.py','evaluation/fixtures/cases.json','evaluation/trusted/contract.json','evaluation/trusted/freeze.json']
old={}
for path in unchanged:
    r=subprocess.run(['git','show','HEAD:'+path],cwd=root,capture_output=True)
    if r.returncode:old[path]={'git_exit':r.returncode};continue
    old[path]={'head_sha256':hashlib.sha256(r.stdout).hexdigest(),'current_sha256':hashlib.sha256((root/path).read_bytes()).hexdigest()}
    record('legacy-bytes-'+path,old[path]['head_sha256']==old[path]['current_sha256'],True)
report={'kind':'Evaluator Owner synthetic/identity checks; not independent QA','command':[sys.executable,*sys.argv],'checks':checks,'legacy_identity':old,'paid_calls':0,'network_calls':0,'exit_code':0 if all(c['pass'] for c in checks) else 1}
(root/'evidence/upgrade/v5.0/evaluator-owner/check-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':len(checks),'exit_code':report['exit_code']},ensure_ascii=False));raise SystemExit(report['exit_code'])
