"""Main-only normalization of already executed independent QA; no target execution."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from evaluation.v5 import INSTALLATION_PINS, _semantic
from jsonschema import Draft202012Validator

OUT=Path(__file__).parent
if len(sys.argv)!=3: raise SystemExit('candidate JSON and successful finite QA run directory required')
CANDIDATE_PATH=sys.argv[1]
P=C=sys.argv[2].rstrip('/')+'/'
RELEASE='v5.0-engineering'
def read(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def write(path,value):
    path=OUT/path
    if path.exists(): raise ValueError('Refusing to overwrite registration derivation')
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    candidate=read(CANDIDATE_PATH)
    summaries=[read(P+'summary.json'),read(C+'summary.json')]
    for report in summaries:
        assert report['exit_code']==0 and report['source_unchanged'] is True
        assert report['candidate_id']==candidate['candidate_id']
        assert report['source_before']==report['source_after']==candidate['source_sha256']
    test_paths={'tests/v5/__init__.py','tests/v5/conftest.py','tests/v5/test_planner_fixed.py',
                'tests/v5/test_security.py','tests/v5/test_integration.py','tests/v5/test_material_auth_fixed.py','scripts/check_v5.py',
                'frontend/src/assets/generated-catalog.json'}
    sources={p:d for p,d in candidate['source_sha256'].items()
             if p.startswith('backend/') and p!='backend/app/ai/v5.py' and Path(p).suffix in {'.py','.in','.txt'}
             or p.startswith('contracts/v2/') or p in test_paths}
    assert sources and all(sha(p)==d for p,d in sources.items())
    admission=read(P+'C1-admission-affected.json')
    ownership=read(C+'C2-observations.json')
    moments=read(C+'C3-moments.json')
    bad=read(C+'C3-bad-checksum.json')
    data={
        'V5-C1':{'admissions':admission['admissions'],'rejections':admission['rejections']},
        'V5-C2':{k:ownership[k] for k in ('owner_id','intruder_id','requests')},
        'V5-C3':{'original_definition_sha256':moments['original_definition_sha256'],
                 'restores':moments['restores'],'bad_saves':[bad]},
    }
    paths={
        'V5-C1':[P+'summary.json',P+'C1-admission-affected.json',
                 'evidence/upgrade/v5.0/experiments-owner/run1/inputs.json'],
        'V5-C2':[C+'summary.json',C+'C2-observations.json'],
        'V5-C3':[C+'summary.json',C+'C3-moments.json',C+'C3-bad-checksum.json'],
    }
    proof_fields=['claim_id','release_id','candidate_id','exit_code','checks','provenance']
    registration={'schema_version':'1.0.0','status':'READY','release_id':RELEASE,
                  'contract_id':'campus-lab-v5-engineering','contract_version':'1.0.0',
                  'candidate_id':candidate['candidate_id'],'sources':sources,
                  'installation':copy.deepcopy(INSTALLATION_PINS),
                  'evidence':[],'runtime_records':[],'claims':{}}
    for index,cid in enumerate(('V5-C1','V5-C2','V5-C3')):
        report=summaries[0 if cid=='V5-C1' else 1]
        proof={'kind':'Main normalized observations from actual independent QA',
               'claim_id':cid,'release_id':RELEASE,'candidate_id':candidate['candidate_id'],
               'exit_code':report['exit_code'],'checks':data[cid],
               'source_before':sources,'source_after':sources,
               'provenance':{'operator':'Independent QA agent executed the original command; Main only filtered and registered observations.',
                   'command':' '.join(report['command']),'actual_product_execution':True,
                   'input_origin':'Offline synthetic definitions/accounts; actual compiler, rules and authenticated API. No model quality inference.',
                   'original_candidate_manifest':CANDIDATE_PATH,
                   'source_projection':'Exact subset of equal full401 before/after runtime maps. Backend/contracts and relevant tests only, excluding AI/v5.py: the recorded commands inject FixtureGenerator and execute no admitted AI turn or production AI service invocation, so production prompts/model quality are outside C1/C2/C3. UI/evaluator/CMD/binary sources are also outside these finite claims. Current prompt repair is a separate source epoch, not relabelled as part of these executions.',
                   'raw_artifacts':[{'path':p,'raw_sha256':sha(p)} for p in paths[cid]],
                   'historical_seven_suites_relabelled':False,
                   'bad_save_fixture':'Separate isolated fixture; not the three-moment session.' if cid=='V5-C3' else None},
               'limitations':['These finite observations are not universal solvability, universal security, real AI generation or real semantic judgement.'],
               'human_signoff':None,'teacher_approval':None}
        failures,gaps=_semantic(cid,proof)
        assert not failures and not gaps,(cid,failures,gaps)
        filename=cid+'.json';write(filename,proof)
        relative=(OUT/filename).relative_to(ROOT).as_posix();eid=RELEASE+':'+cid
        registration['evidence'].append({'evidence_id':eid,'path':relative,'raw_sha256':sha(relative),
            'windows':{'summary':{'kind':'json_fields','fields':proof_fields}}})
        registration['runtime_records'].append({'evidence_id':eid,'release_field':'release_id',
            'candidate_field':'candidate_id','before_field':'source_before','after_field':'source_after','exit_field':'exit_code'})
        registration['claims'][cid]={'refs':[{'evidence_id':eid,'snippet':'summary'}]}
    raw_windows={
        P+'summary.json':['candidate_id','command','exit_code','scope','source_unchanged'],
        C+'summary.json':['candidate_id','command','exit_code','scope','source_unchanged'],
        P+'C1-admission-affected.json':['frozen_input_file_sha256','scope','admissions','rejections'],
        C+'C2-observations.json':['hash_method','owner_id','intruder_id','requests'],
        C+'C3-moments.json':['hash_method','original_definition_sha256','restores'],
        C+'C3-bad-checksum.json':['hash_method','case_id','rejected','http_status','current_before_sha256','current_after_sha256'],
    }
    for index,(path,fields) in enumerate(raw_windows.items()):
        value=read(path);assert set(fields)<=set(value)
        registration['evidence'].append({'evidence_id':RELEASE+':RAW'+str(index+1),'path':path,
            'raw_sha256':sha(path),'windows':{'identity':{'kind':'json_fields','fields':fields}}})
    input_path=paths['V5-C1'][-1]
    registration['evidence'].append({'evidence_id':RELEASE+':INPUTS','path':input_path,
        'raw_sha256':sha(input_path),'windows':{'identity':{'kind':'lines','start':1,'count':2}}})
    Draft202012Validator(read('evaluation/v5/registration.schema.json')).validate(registration)
    write('registration-ready.json',registration)
    write('derivation.json',{'operator':'Main evidence normalization; no target code executed by this builder',
        'utc':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,str(Path(__file__).relative_to(ROOT))],
        'exit_code':0,'source_count':len(sources),'candidate_id':candidate['candidate_id'],
        'claims':list(data),'actual_paid_calls':0,'network_calls':0,'active_trusted_registration_changed':False,
        'active_pin_changed':False,'registration_sha256':sha((OUT/'registration-ready.json').relative_to(ROOT).as_posix()),
        'limitations':['Main normalized registered data is derived evidence, not a new QA run or semantic PASS.','Trusted installation/pin handoff remains a separate reviewed epoch.']})
    print(json.dumps({'exit_code':0,'claims':3,'sources':len(sources),'evidence':len(registration['evidence']),'active_pin_changed':False}))
if __name__=='__main__': main()
