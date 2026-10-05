"""Main registers E2/E3 together with complete actual API/browser source bindings."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2]
PRODUCT='242ecfc4d9f7bf1a8480508de701d9efc7822fe7'
EVENT='ch01-adversarial-review-v3'
RELEASE='CH01-adversarial-review-v3'
BROWSER='evidence/qa/T30-20261005T062357488Z-CH01-browser'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads((ROOT/p).read_bytes())
def git(*args):return subprocess.check_output(['git','-c','safe.directory=D:/深度能力',*args],cwd=ROOT)
def write_new(p,obj):
    f=ROOT/p;f.parent.mkdir(parents=True,exist_ok=True)
    with f.open('x',encoding='utf-8') as s:json.dump(obj,s,ensure_ascii=False,indent=2);s.write('\n')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--api-run',required=True);parser.add_argument('--process',required=True)
    args=parser.parse_args();api=load(args.api_run);browser=load(BROWSER+'/run.json');process=load(args.process)
    assert api['exit_code']==0 and api['tests_run']==54 and not api['failures'] and not api['errors']
    assert api['source_sha256_before']==api['source_sha256_after']
    assert browser['exit_code']==0 and browser['source_sha256_before']==browser['source_sha256_after']
    maps={'API':api['source_sha256_before'],'BROWSER':browser['source_sha256_before']}
    source_hashes={}
    for mapping in maps.values():
        for p,h in mapping.items():
            assert sha((ROOT/p).read_bytes())==h,p
            assert p not in source_hashes or source_hashes[p]==h,p
            source_hashes[p]=h
    evidence_commit=git('rev-parse','HEAD').decode().strip()
    sources={}
    for p,h in source_hashes.items():
        raw=(ROOT/p).read_bytes();blob=git('show',evidence_commit+':'+p)
        canonical=raw.decode('utf-8').replace('\r\n','\n').encode()
        assert canonical==blob.decode('utf-8').replace('\r\n','\n').encode(),p
        sources[p]={'candidate_runtime_raw_sha256':h,'git_blob_sha256':sha(blob),
                    'git_blob_oid':git('rev-parse',evidence_commit+':'+p).decode().strip(),
                    'utf8_lf_v1_sha256':sha(canonical),'binding':'raw_equal' if raw==blob else 'approved_crlf_to_lf_only',
                    'evidence':[RELEASE+':'+k+'-IDENTITY' for k,v in maps.items() if p in v]}
    artifacts=[('API',args.api_run,'execution',{'result':{'kind':'json_fields','fields':['candidate','schema_version','level_version','started','ended','provider','tests_run','failures','errors','source_unchanged','exit_code','limits']}}),
               ('BROWSER',BROWSER+'/run.json','execution',{'result':{'kind':'json_fields','fields':['candidate','provider','started','ended','browsers','widths','exit_code','privacy']}}),
               ('TEST-OUTPUT',str(Path(args.api_run).parent.as_posix())+'/unittest-output.txt','support',{'tests':{'kind':'lines','start':20,'count':40}}),
               ('TEST-SOURCE','tests/api/test_ch01.py','support',{'assertions':{'kind':'lines','start':1,'count':200}}),
               ('REPORT','review/findings/T30-report-20261005.md','support',{'results':{'kind':'lines','start':20,'count':29}}),
               ('FINAL-PROCESS',args.process,'support',{'process':{'kind':'lines','start':1,'count':50}}),
               ('FREEZE','evidence/integration/CH01_v2-manifest.json','support',{'version':{'kind':'json_fields','fields':['release_id','commit','tree','versions','unbound_prior_source_records','limitations']}})]
    observations=[]
    statepath=BROWSER+'/chrome-390-states.json'
    for i,row in enumerate(load(statepath)):
        receipt=row.get('receipt') or {};state=row.get('visible_state') or {}
        if row.get('stage')!='manual-action' or receipt.get('tool')=='use_item' and receipt.get('arguments',{}).get('item_id')=='emergency_key':
            observations.append({'source_row_0_based':i,'stage':row.get('stage'),'receipt':receipt,
                                 'replayed':row.get('replayed'),'proposal':row.get('proposal'),
                                 'state':{k:state.get(k) for k in ['level_version','schema_version','revision','generation','status','room','inventory','exits','progress']}})
    selection='evidence/integration/event-'+EVENT+'-public-selection.json'
    write_new(selection,{'derived_by':'Main selection, not a new test execution','original_path':statepath,
                         'original_raw_sha256':sha((ROOT/statepath).read_bytes()),'observations':observations})
    artifacts.append(('PUBLIC-SELECTION',selection,'support',{'state':{'kind':'json_fields','fields':['derived_by','original_path','original_raw_sha256','observations']}}))
    for label,mapping in maps.items():
        exec_path=args.api_run if label=='API' else BROWSER+'/run.json'
        identity={'release_id':RELEASE,'product_commit':PRODUCT,'exit_code':0,'source_before':mapping,'source_after':mapping,
                  'artifact_hashes':{RELEASE+':'+label:sha((ROOT/exec_path).read_bytes())},
                  'provenance':{'source_maps':'Exact complete actual execution before/after fields, equality independently recorded and Main re-read.',
                                'product_binding':'CH01 v2 core accepted at product commit; additional QA and Delivery inputs bind separately to current integration Git blobs.',
                                'evidence_commit':evidence_commit,'historical_api_gap':'Earlier API/check maps had unrelated prior browser helper bytes; kept historical. Fresh API identity here does not rewrite them.',
                                'process':args.process if label=='API' else 'Original final browser run.command and exit_code, T30-command-ledger-20261005.json'},
                  'derived_by':'Main identity association, not invented execution or human signoff','teacher_approval':None,'human_signoff':None}
        path='evidence/integration/event-'+EVENT+'-'+label.lower()+'-identity.json';write_new(path,identity)
        artifacts.append((label+'-IDENTITY',path,'identity',{'scope':{'kind':'json_fields','fields':['release_id','product_commit','exit_code','provenance']}}))
    evidence=[];windows={};roles={};runtime=[]
    for label,p,role,window in artifacts:
        eid=RELEASE+':'+label;raw=(ROOT/p).read_bytes()
        evidence.append({'evidence_id':eid,'path':p,'release_id':RELEASE,'artifact_raw_sha256':sha(raw),'artifact_binding':'raw_equal'})
        windows[eid]=window;roles[eid]=role
        if role=='execution':runtime.append({'evidence_id':eid,'identity_evidence_id':eid+'-IDENTITY','release_id_field':'release_id',
            'commit_field':'product_commit','exit_code_field':'exit_code','source_before_field':'source_before','source_after_field':'source_after',
            'artifact_hashes_field':'artifact_hashes','source_paths':sorted(maps[label])})
    refs=[{'evidence_id':RELEASE+':'+label,'snippet':snippet,'expected_raw_sha256':next(x['artifact_raw_sha256'] for x in evidence if x['evidence_id']==RELEASE+':'+label)}
          for label,snippet in [('API','result'),('BROWSER','result'),('TEST-OUTPUT','tests'),('TEST-SOURCE','assertions'),('REPORT','results'),('PUBLIC-SELECTION','state')]]
    contract=load('evaluation/trusted/contract.json')
    claims=[{'claim_id':RELEASE+':'+criterion,'criterion_id':criterion,'release_id':RELEASE,
             'statement':contract['criteria'][criterion]['must_observe'],'declared_scope':'CH01 v2 fixed scripted/mock engineering checks and six actual browser routes; no real-language model robustness or human gameplay/signature claim.',
             'declared_na':False,'evidence_refs':refs,'known_scope_status':'MAIN_ACCEPTED_T30_ENGINEERING_SCOPE_REVIEW_PENDING'} for criterion in ['A27','A21','A23']]
    locations={p:{'archive_release_id':'baseline_v1','archive_path':p,'raw_sha256':h} for p,h in source_hashes.items() if p.startswith('release/archives/baseline_v1/')}
    registration={'schema_id':'event-registration-v1','event_id':EVENT,'release_id':RELEASE,'product_commit':PRODUCT,
                  'approved_by':'Main','approved_at':datetime.now(timezone.utc).isoformat(),
                  'manifest':{'release_id':RELEASE,'commit':PRODUCT,'sources':sources,'evidence':evidence,'teacher_approval':None,'human_signoff':None,
                              'limitations':['E2/E3 combined event, exact actual source identities; original historical gaps retained.','Only engineered scripted scope, no general natural-language or human acceptance.']},
                  'claims':{'release_id':RELEASE,'claims':claims},'windows':windows,'evidence_roles':roles,'runtime_records':runtime,
                  'coverage':[{'claim_id':c['claim_id'],'criterion_id':c['criterion_id'],'status':'full','gaps':[],
                               'required_refs':[{'evidence_id':r['evidence_id'],'snippet':r['snippet']} for r in refs]} for c in claims],
                  'source_locations':locations,'teacher_approval':None,'human_signoff':None}
    archived={};all_locations={};copies={}
    for original,record in sources.items():
        archive_path=original if original.startswith("release/archives/baseline_v1/") else "release/archives/CH01_v2/"+original
        raw=(ROOT/original).read_bytes()
        if archive_path!=original:
            target=ROOT/archive_path
            if target.exists():raise ValueError("immutable CH01 archive path already exists: "+archive_path)
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            copies[original]={"archive_path":archive_path,"raw_sha256":sha(raw),"git_blob_oid":record["git_blob_oid"],"git_blob_sha256":record["git_blob_sha256"]}
        assert sha((ROOT/archive_path).read_bytes())==record["candidate_runtime_raw_sha256"]
        archived[archive_path]=record
        all_locations[original]={"archive_release_id":"baseline_v1" if archive_path==original else "CH01_v2","archive_path":archive_path,"raw_sha256":sha(raw)}
    registration["manifest"]["sources"]=archived
    registration["source_locations"]=all_locations
    write_new("evidence/integration/CH01-event-source-archive-20261005.json",{"derived_by":"Main actual raw copy and readback","product_commit":PRODUCT,"source_git_commit":evidence_commit,"new_raw_copies":copies,"count_new":len(copies),"alias_count":len(all_locations),"scope":"Copy/hash only, no code execution. Existing 102 baseline aliases and all original execution maps preserved. New actual integration input archive avoids mixed direct/archive loader ambiguity."})
    Draft202012Validator(load('evaluation/schemas/event-registration-v1.schema.json')).validate(registration)
    path='evidence/integration/event-'+EVENT+'-registration.json';write_new(path,registration)
    print(json.dumps({'path':path,'raw_sha256':sha((ROOT/path).read_bytes()),'sources':len(sources),'claims':len(claims),'actual_paid_calls':0}))
if __name__=='__main__':main()
