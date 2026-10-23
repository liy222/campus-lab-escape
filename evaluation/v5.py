"""Fixed-root V5 evaluator adapter; target material is read only, never executed."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import tempfile
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from .common import PROJECT_ROOT, EvaluationError, identifier, json_bytes, sha256, strict_json
from .engine import Evaluator
from .provider import MockProvider
from .reader import EvidenceTools, safe_read

RELEASE='v5.0-engineering'
CONTRACT='campus-lab-v5-engineering'
VERSION='1.0.0'
CLAIMS=('V5-C1','V5-C2','V5-C3')
# Main alone fills this after the actual registration is final. None never means wildcard.
REGISTRATION_RAW_SHA256='80b312f31b73d3cef3a29575e07d1ca8f4f84d114490edd8289779aa7cb7a63d'
INSTALLATION_PINS={'evaluation/common.py': '91509d55058126319117b45f7e256aec5f46d35f97cd6bda7cbe6472f8227ab8', 'evaluation/engine.py': '2e9778f186c8191a475db9fa359a06dea8725cd4733872c450bf261d0cbfb74c', 'evaluation/provider.py': '438178cb8e3575b9172cb98f5df3ee84a5ec20874840c8af8ccf0dab4856a4dd', 'evaluation/reader.py': '050a8f6deb3e7ca209fde3362cd617274f0941cd5968662606bc2a6e282c5e7b', 'evaluation/schemas/output.schema.json': '19a0062cdb3a2990178bac3ebdb078e29c898691f034c9adcca3dcdd7bc9c6b8', 'evaluation/schemas/suggestion.schema.json': 'b009e075e956c5c276bc27495d13223d8c0293271b23d2184b29163fd132a05b', 'evaluation/trust.py': '8f8e02c1734d37263bbac3a0203f94c5b1f24fdea7f104c34ff53a0d67c38a14', 'evaluation/v5/contract.json': '85a3b4ac3d0e3c9b6b55a0d9cba531e8ca06fe144b7e38d209aad1885ef2b744', 'evaluation/v5/fixture-contract.json': '8cebb1a471255fd2ff884f53b97bfb4fc7308a7d2287d92a9bb75e345b250aea', 'evaluation/v5/fixtures/failure.json': '0a01591fa9207f1775c3dac2795fefc2e05abbddbde3aa14298d2d376f212fbf', 'evaluation/v5/fixtures/injection.json': '28922151828991230f07529f2fc826aee0c0f3a51af62293d5f92331ba4fd1fd', 'evaluation/v5/fixtures/na.json': '096d9f87b6fcfbf65b51fab9cd827b1e9fd4240c2c005ec9460e9aad89bc88fb', 'evaluation/v5/fixtures/self-claim.json': '7847b0eb7939b30560cbb9af186ab8244a381aeeaf0562d6f4b25623de63156a', 'evaluation/v5/fixtures/source.json': '78b2168fbb2df8e03760f4e522df3b00018ccfcedf1b672d973c00e91cba533e', 'evaluation/v5/fixtures/support.json': 'c6278c3855a0f1475a0dead5eead50f49b124bc493b0620345c48339ad45fc66', 'evaluation/v5/registration.schema.json': '5e2b8f6248d8bba29d89371c6f90c8243d653049e6b0972ba27cd611f5f77860'}
ROOT='evaluation/v5/'
HASH=re.compile(r'^[0-9a-f]{64}$')


def _json(path,root=PROJECT_ROOT):
    return strict_json(safe_read(root,path))


def _installation():
    for path,digest in INSTALLATION_PINS.items():
        if sha256(safe_read(PROJECT_ROOT,path))!=digest:
            raise EvaluationError('V5_INSTALLATION_PIN_MISMATCH')
    # Loader/CLI are evaluator-owned trust roots. Snapshot their raw bytes too,
    # closing dispatch/judgement races without a self-referential registration hash.
    return {p:sha256(safe_read(PROJECT_ROOT,p)) for p in
            (*INSTALLATION_PINS,'evaluation/v5.py','evaluation/cli.py')}


def _claim(cid,release,refs,criterion=None,na=False):
    return {'claim_id':cid,'criterion_id':criterion or cid,'release_id':release,
            'statement':'Evaluate only the registered finite '+(criterion or cid)+' scope.',
            'declared_scope':'Main-pinned source/evidence only; no wider safety, AI quality or human approval claim.',
            'declared_na':na,'evidence_refs':refs,'known_scope_status':'EVIDENCE_REQUIRED'}


def _semantic(criterion,value):
    """Validate registered observations, not target prose or instructions."""
    failures,gaps=[],[]
    checks=value.get('checks')
    if not isinstance(checks,dict):return [],['MISSING_OBSERVATION_CHECKS']
    def records(key):
        rows=checks.get(key)
        if not isinstance(rows,list) or not rows or any(not isinstance(r,dict) for r in rows):
            gaps.append('MISSING_OR_INVALID_'+key.upper());return []
        return rows
    def yes(row,key):
        if type(row.get(key)) is not bool:gaps.append('MISSING_BOOLEAN_'+key)
        elif not row[key]:failures.append('OBSERVED_FALSE_'+key)
    def equal(row,a,b):
        if not all(isinstance(row.get(k),str) and HASH.fullmatch(row[k]) for k in (a,b)):
            gaps.append('MISSING_OR_INVALID_HASH_'+a)
        elif row[a]!=row[b]:failures.append('OBSERVED_HASH_DIFFERENCE_'+a+'_'+b)
    if criterion=='V5-C1':
        admissions=records('admissions');wanted={(n,d) for n in (1,2,3) for d in ('easy','normal','hard')}
        actual=[(r.get('room_count'),r.get('difficulty')) for r in admissions]
        if any(type(n) is not int or not isinstance(d,str) for n,d in actual) or len(actual)!=9 or set(actual)!=wanted or len(set(actual))!=len(actual):gaps.append('NINE_DISTINCT_ROOM_DIFFICULTY_REPLAYS_REQUIRED')
        for r in admissions:
            yes(r,'admitted');yes(r,'replay_won')
            if type(r.get('steps')) is not int:gaps.append('MISSING_REPLAY_STEPS')
            elif r['steps']<=0:failures.append('OBSERVED_NO_REPLAY_ACTIONS')
        rejected=records('rejections');ids=[r.get('case_id') for r in rejected]
        if len(rejected)!=20 or any(not isinstance(v,str) or not v for v in ids) or len(set(str(v) for v in ids))!=20:gaps.append('TWENTY_DISTINCT_REJECTION_CASES_REQUIRED')
        if any(sum(r.get('category')==cat for r in rejected)!=5 for cat in ('reference','dependency','semantic','layout')):gaps.append('FIVE_REJECTIONS_PER_CATEGORY_REQUIRED')
        for r in rejected:yes(r,'rejected')
    elif criterion=='V5-C2':
        owner,intruder=checks.get('owner_id'),checks.get('intruder_id')
        if not isinstance(owner,str) or not owner or not isinstance(intruder,str) or not intruder:gaps.append('TWO_ACCOUNT_IDENTITIES_REQUIRED')
        elif owner==intruder:failures.append('OBSERVED_SAME_ACCOUNT')
        requests=records('requests')
        if not {'read','restore'}<=set(str(r.get('operation')) for r in requests):gaps.append('READ_AND_RESTORE_REQUESTS_REQUIRED')
        for r in requests:
            if type(r.get('http_status')) is not int:gaps.append('MISSING_HTTP_STATUS')
            elif r['http_status']!=404:failures.append('OBSERVED_NON404_'+str(r.get('operation')))
            equal(r,'target_before_sha256','target_after_sha256')
    elif criterion=='V5-C3':
        definition=checks.get('original_definition_sha256')
        if not isinstance(definition,str) or not HASH.fullmatch(definition):gaps.append('ORIGINAL_DEFINITION_HASH_REQUIRED')
        restores=records('restores')
        if len(restores)!=3 or len({str(r.get('moment_id')) for r in restores})!=3 or len({str(r.get('saved_state_sha256')) for r in restores})!=3:gaps.append('THREE_DISTINCT_SAVED_MOMENTS_REQUIRED')
        for r in restores:
            if not isinstance(r.get('moment_id'),str) or not r['moment_id']:gaps.append('MOMENT_ID_REQUIRED')
            equal(r,'saved_state_sha256','restored_state_sha256')
            restored=r.get('restored_definition_sha256')
            if not isinstance(restored,str) or not HASH.fullmatch(restored):gaps.append('RESTORED_DEFINITION_HASH_REQUIRED')
            elif isinstance(definition,str) and HASH.fullmatch(definition) and restored!=definition:failures.append('OBSERVED_DEFINITION_CHANGED')
        for r in records('bad_saves'):
            yes(r,'rejected');equal(r,'current_before_sha256','current_after_sha256')
    else:gaps.append('UNKNOWN_V5_CRITERION')
    return sorted(set(failures)),sorted(set(gaps))


class V5Context:
    def __init__(self,root,registration,installation,claims,*,ready=True,registration_pin=None):
        self.root,self.registration,self.installation,self.claims=root,registration,installation,claims
        self.ready,self.registration_pin=ready,registration_pin
        self.release_id=registration['release_id'];self.event_id='v5-finite-engineering'
        self.product_commit=registration['candidate_id'];self.input_sha256=sha256(json_bytes(registration))
        self.coverage={c['claim_id']:{'status':'partial','gaps':['NO_REGISTERED_RUNTIME_EVIDENCE']} for c in claims}

    def precheck(self,tools):
        issues=[];bindings=[];findings=[];identities={}
        def issue(code,**more):issues.append({'code':code,**more})
        if not self.ready:issue('V5_REGISTRATION_NOT_READY')
        try:
            for p,digest in self.installation.items():
                if sha256(safe_read(PROJECT_ROOT,p))!=digest:raise EvaluationError('V5_INSTALLATION_CHANGED')
            if self.registration_pin and sha256(safe_read(PROJECT_ROOT,ROOT+'registration.json'))!=self.registration_pin:raise EvaluationError('V5_REGISTRATION_CHANGED')
        except EvaluationError as e:issue(e.code)
        source_map=self.registration['sources'];raw={};evidence={r['evidence_id']:r for r in tools.manifests[self.release_id]['evidence']}
        for path,digest in source_map.items():
            try:
                observed=sha256(safe_read(self.root,path,source=True))
                if observed!=digest:raise EvaluationError('V5_SOURCE_RAW_MISMATCH')
                identities[path]={'observed_raw_sha256':observed,'raw_equal':True}
            except EvaluationError as e:issue(e.code,path=path)
        for eid,r in evidence.items():
            try:
                data=safe_read(self.root,r['path'])
                if sha256(data)!=r['artifact_raw_sha256']:raise EvaluationError('V5_EVIDENCE_RAW_MISMATCH')
                raw[eid]=data
                for snippet,w in tools.windows[eid].items():
                    if w['kind']=='json_fields':
                        v=strict_json(data)
                        if not isinstance(v,dict) or not set(w['fields'])<=set(v):raise EvaluationError('V5_WINDOW_FIELDS_MISSING')
                    elif w['kind']=='lines':
                        if w['start']+w['count']-1>len(data.decode('utf-8').splitlines()):raise EvaluationError('V5_WINDOW_LINES_MISSING')
                    tools.read_evidence(eid,snippet)
            except (EvaluationError,UnicodeError) as e:issue(e.code if isinstance(e,EvaluationError) else 'NON_UTF8_EVIDENCE',evidence_id=eid)
        runtimes={}
        for record in self.registration['runtime_records']:
            eid=record['evidence_id']
            try:
                if eid not in raw:raise EvaluationError('V5_RUNTIME_EVIDENCE_UNAVAILABLE')
                value=strict_json(raw[eid]);required=[record[k] for k in ('release_field','candidate_field','before_field','after_field','exit_field')]
                if not isinstance(value,dict) or not set(required)<=set(value):raise EvaluationError('V5_RUNTIME_FIELDS_MISSING')
                if value[record['release_field']]!=self.release_id or value[record['candidate_field']]!=self.product_commit:raise EvaluationError('V5_RUNTIME_VERSION_MISMATCH')
                before,after=value[record['before_field']],value[record['after_field']]
                if not isinstance(before,dict) or not before or before!=after:raise EvaluationError('V5_RUNTIME_SOURCE_CHANGED_OR_EMPTY')
                if before!=source_map:raise EvaluationError('V5_RUNTIME_SOURCE_MAP_NOT_EXACT')
                if type(value[record['exit_field']]) is not int:raise EvaluationError('V5_RUNTIME_EXIT_INVALID')
                runtimes[eid]=(value,value[record['exit_field']])
            except EvaluationError as e:issue(e.code,evidence_id=eid)
        for c in self.claims:
            gaps=[];has_runtime=False
            for ref in c['evidence_refs']:
                eid,snippet=ref['evidence_id'],ref['snippet']
                if eid not in evidence or snippet not in tools.windows.get(eid,{}):issue('V5_REQUIRED_WINDOW_UNREGISTERED',claim_id=c['claim_id']);continue
                if eid not in runtimes:continue
                window=tools.windows[eid][snippet]
                runtime=next(r for r in self.registration['runtime_records'] if r['evidence_id']==eid)
                required_fields={'claim_id','checks','provenance',runtime['release_field'],runtime['candidate_field'],runtime['exit_field']}
                if window['kind']!='json_fields' or not required_fields<=set(window['fields']):
                    issue('V5_REQUIRED_PROOF_WINDOW_FIELDS_MISSING',claim_id=c['claim_id']);continue
                value,exit_code=runtimes[eid];has_runtime=True
                if value.get('claim_id')!=c['criterion_id'] and c['criterion_id']!='NA-DEMO':gaps.append('RUNTIME_CRITERION_NOT_BOUND');continue
                fails,missing=_semantic(c['criterion_id'],value) if c['criterion_id']!='NA-DEMO' else ([],[])
                if self.release_id==RELEASE:
                    provenance=value.get('provenance')
                    if not isinstance(provenance,dict) or not all(isinstance(provenance.get(k),str) and provenance[k].strip() for k in ('operator','command')):
                        missing.append('ACTUAL_OPERATOR_AND_COMMAND_REQUIRED')
                    if value.get('synthetic') is True or isinstance(provenance,dict) and (provenance.get('synthetic') is True or provenance.get('actual_product_execution') is False):
                        missing.append('SYNTHETIC_OBSERVATIONS_NOT_REAL_RELEASE_EVIDENCE')
                gaps.extend(missing);findings.extend({'claim_id':c['claim_id'],'evidence_id':eid,'code':f} for f in fails)
                bindings.append({'evidence_id':eid,'exit_code':1 if fails else exit_code,'recorded_exit_code':exit_code,'release_id':self.release_id,'product_commit':self.product_commit,'source_before':source_map,'source_after':source_map,'source_count':len(source_map),'artifact_raw_sha256':evidence[eid]['artifact_raw_sha256']})
            if not has_runtime:gaps.append('NO_REGISTERED_RUNTIME_EVIDENCE')
            self.coverage[c['claim_id']]={'status':'partial' if gaps else 'complete','gaps':sorted(set(gaps))}
        for path,digest in [(p,d) for p,d in source_map.items()]+[(r['path'],r['artifact_raw_sha256']) for r in evidence.values()]:
            try:
                if sha256(safe_read(self.root,path,source=path in source_map))!=digest:issue('V5_IDENTITY_CHANGED_DURING_PRECHECK',path=path)
            except EvaluationError as e:issue(e.code,path=path)
        return {'release_id':self.release_id,'event_id':self.event_id,'product_commit':self.product_commit,'status':'READY' if self.ready and not issues else 'NOT_READY','issues':issues,'source_identities':identities,'runtime_source_bindings':bindings,'deterministic_findings':findings,'historical_unbound_records':[],'generated_runtime_only':[],'scope':'Read/hash registered data only; no target imports, subprocess, AGENTS execution, credentials or ledger.'}


def _tools(root,contract,registration,installation,claims,*,ready=True,registration_pin=None):
    records=[];windows={};seen=set()
    for r in registration['evidence']:
        eid=identifier(r['evidence_id'])
        if eid in seen:raise EvaluationError('V5_DUPLICATE_EVIDENCE_ID')
        seen.add(eid);windows[eid]=r['windows']
        records.append({'evidence_id':eid,'release_id':registration['release_id'],'path':r['path'],'artifact_raw_sha256':r['raw_sha256'],'artifact_binding':'raw_equal'})
    tools=EvidenceTools(root,contract,{registration['release_id']:{'release_id':registration['release_id'],'sources':registration['sources'],'evidence':records}},windows)
    context=V5Context(root,registration,installation,claims,ready=ready,registration_pin=registration_pin)
    tools.event_contexts={registration['release_id']:context}
    files={p:_json('evaluation/'+p) for p in ('schemas/output.schema.json','schemas/suggestion.schema.json')}
    return files,tools,context


def load_v5():
    installation=_installation();contract=_json(ROOT+'contract.json')
    if contract['contract_id']!=CONTRACT or contract['version']!=VERSION or set(contract['criteria'])!=set(CLAIMS) or contract['approved_na'] or any(c['na_allowed'] for c in contract['criteria'].values()):raise EvaluationError('V5_REAL_CONTRACT_MISMATCH')
    raw=safe_read(PROJECT_ROOT,ROOT+'registration.json');registration=strict_json(raw)
    try:Draft202012Validator(_json(ROOT+'registration.schema.json')).validate(registration)
    except ValidationError:raise EvaluationError('V5_REGISTRATION_SCHEMA_INVALID') from None
    ready=REGISTRATION_RAW_SHA256 is not None
    if ready and sha256(raw)!=REGISTRATION_RAW_SHA256:raise EvaluationError('V5_MAIN_REGISTRATION_PIN_MISMATCH')
    if ready and registration['status']!='READY':raise EvaluationError('V5_MAIN_REGISTRATION_NOT_READY')
    if ready:
        runtime_ids=[r['evidence_id'] for r in registration['runtime_records']]
        if len(runtime_ids)!=len(set(runtime_ids)):raise EvaluationError('V5_DUPLICATE_RUNTIME_ID')
        if not set(INSTALLATION_PINS)<=set(registration['installation']) or any(registration['installation'][p]!=INSTALLATION_PINS[p] for p in INSTALLATION_PINS):raise EvaluationError('V5_REGISTERED_INSTALLATION_NOT_EXACT')
        # Merge captured loader/CLI raw identities; no self-referential hash cycle.
        installation.update(registration['installation'])
    else:
        registration={'release_id':RELEASE,'candidate_id':'UNREGISTERED','sources':{},'evidence':[],'runtime_records':[],'claims':{cid:{'refs':[]} for cid in CLAIMS}}
    claims=[_claim(cid,RELEASE,registration['claims'][cid]['refs']) for cid in CLAIMS]
    return _tools(PROJECT_ROOT,contract,registration,installation,claims,ready=ready,registration_pin=REGISTRATION_RAW_SHA256)


def _fixture_tools(root):
    contract=_json(ROOT+'fixture-contract.json');source=ROOT+'fixtures/source.json';sources={source:sha256(safe_read(root,source))};release='v5-calibration';records=[];runtime=[]
    for name in ('support','failure','injection','na','self-claim'):
        path=ROOT+'fixtures/'+name+'.json';eid=release+':'+('NA' if name=='na' else name);fields=['statement'] if name=='self-claim' else ['claim_id','release_id','candidate_id','exit_code','checks','provenance']
        if name=='injection':fields.append('untrusted_instruction')
        records.append({'evidence_id':eid,'path':path,'raw_sha256':sha256(safe_read(root,path)),'windows':{'summary':{'kind':'json_fields','fields':fields}}})
        if name!='self-claim':runtime.append({'evidence_id':eid,'release_field':'release_id','candidate_field':'candidate_id','before_field':'source_before','after_field':'source_after','exit_field':'exit_code'})
    def ref(name):return [{'evidence_id':release+':'+name,'snippet':'summary'}]
    claims=[_claim('K1',release,ref('support'),'V5-C1'),_claim('K2',release,ref('failure'),'V5-C1'),_claim('K3',release,ref('self-claim'),'V5-C1'),_claim('K4',release,ref('injection'),'V5-C1'),_claim('K5',release,ref('support'),'V5-C1'),_claim('K6-legal',release,ref('NA'),'NA-DEMO',True),_claim('K6-illegal',release,ref('support'),'V5-C1',True)]
    registration={'release_id':release,'candidate_id':'synthetic-v1','sources':sources,'evidence':records,'runtime_records':runtime}
    return _tools(root,contract,registration,_installation(),claims)


def _script(claim,status='PASS',*,fake=False):
    return {'claim_id':claim['claim_id'],'release_id':claim['release_id'],'status':status,'evidence_refs':[{'evidence_id':'fabricated:ref','snippet':'summary'}] if fake else copy.deepcopy(claim['evidence_refs']),'reason':'Explicit synthetic scripted judgement; not real model or product validation.','missing_check':['Supply actual evidence and approved semantic judgement.'] if status=='INSUFFICIENT_EVIDENCE' else []}


async def calibrate_v5(mode):
    rows=[];expected=['PASS','FAIL','INSUFFICIENT_EVIDENCE','FAIL','INSUFFICIENT_EVIDENCE','NOT_APPLICABLE','INSUFFICIENT_EVIDENCE']
    folder=PROJECT_ROOT/'evidence/upgrade/v5.0/evaluator-owner';folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='isolated-calibration-',dir=folder) as temporary:
        root=Path(temporary);root.resolve().relative_to(folder.resolve())
        for name in ('source','support','failure','injection','na','self-claim'):
            p=ROOT+'fixtures/'+name+'.json';dest=root/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(safe_read(PROJECT_ROOT,p))
        files,tools,context=_fixture_tools(root)
        for claim,wanted in zip(context.claims,expected):
            provider=MockProvider([_script(claim,fake=claim['claim_id']=='K5')]) if mode=='mock' else None
            result,audit=await Evaluator(tools,files,provider).evaluate(claim,tools.contract['contract_id'],VERSION)
            wanted=wanted if mode=='mock' or wanted!='PASS' else 'INSUFFICIENT_EVIDENCE'
            rows.append({'case_id':claim['claim_id'],'expected':wanted,'actual':result['status'],'matches_expected':result['status']==wanted,'output':result,'audit':audit,'synthetic':True})
        claim=context.claims[0]
        for attack,path in [('source-hash',ROOT+'fixtures/source.json'),('evidence-hash',ROOT+'fixtures/support.json')]:
            old=(root/path).read_bytes();(root/path).write_bytes(old+b' ')
            result,audit=await Evaluator(tools,files,MockProvider([_script(claim)])).evaluate(claim,tools.contract['contract_id'],VERSION)
            (root/path).write_bytes(old)
            rows.append({'case_id':'A-'+attack,'expected':'INSUFFICIENT_EVIDENCE','actual':result['status'],'matches_expected':result['status']=='INSUFFICIENT_EVIDENCE','output':result,'audit':audit,'synthetic':True})
        result,audit=await Evaluator(tools,files,MockProvider([_script(claim)])).evaluate(claim,tools.contract['contract_id'],'9.0.0')
        rows.append({'case_id':'A-contract-version','expected':'INSUFFICIENT_EVIDENCE','actual':result['status'],'matches_expected':result['status']=='INSUFFICIENT_EVIDENCE','output':result,'audit':audit,'synthetic':True})
        support=root/(ROOT+'fixtures/support.json');old=support.read_bytes();v=strict_json(old);v['release_id']='wrong-release';support.write_bytes(json_bytes(v))
        record=next(r for r in tools.manifests['v5-calibration']['evidence'] if r['evidence_id']=='v5-calibration:support');old_hash=record['artifact_raw_sha256'];record['artifact_raw_sha256']=sha256(support.read_bytes())
        result,audit=await Evaluator(tools,files,MockProvider([_script(claim)])).evaluate(claim,tools.contract['contract_id'],VERSION)
        support.write_bytes(old);record['artifact_raw_sha256']=old_hash
        rows.append({'case_id':'A-runtime-version','expected':'INSUFFICIENT_EVIDENCE','actual':result['status'],'matches_expected':result['status']=='INSUFFICIENT_EVIDENCE','output':result,'audit':audit,'synthetic':True})
        for attack,field,new_value in [('empty-source-map','source_before',{}),('source-before-after','source_after',{})]:
            v=strict_json(old);v[field]=new_value;support.write_bytes(json_bytes(v));record['artifact_raw_sha256']=sha256(support.read_bytes())
            result,audit=await Evaluator(tools,files,MockProvider([_script(claim)])).evaluate(claim,tools.contract['contract_id'],VERSION)
            support.write_bytes(old);record['artifact_raw_sha256']=old_hash
            rows.append({'case_id':'A-'+attack,'expected':'INSUFFICIENT_EVIDENCE','actual':result['status'],'matches_expected':result['status']=='INSUFFICIENT_EVIDENCE','output':result,'audit':audit,'synthetic':True})
        for attack,changed_path in [('source-during-judgement',ROOT+'fixtures/source.json'),('evidence-during-judgement',ROOT+'fixtures/support.json')]:
            changed=root/changed_path;original=changed.read_bytes()
            class MutatingMock(MockProvider):
                async def complete(self,messages):
                    changed.write_bytes(original+b' ')
                    return await super().complete(messages)
            result,audit=await Evaluator(tools,files,MutatingMock([_script(claim)])).evaluate(claim,tools.contract['contract_id'],VERSION)
            changed.write_bytes(original)
            rows.append({'case_id':'A-'+attack,'expected':'INSUFFICIENT_EVIDENCE','actual':result['status'],'matches_expected':result['status']=='INSUFFICIENT_EVIDENCE','output':result,'audit':audit,'synthetic':True})
    return rows


async def run_v5(args):
    mode=getattr(args,'mode','deterministic');started=datetime.now(timezone.utc).isoformat()
    folder=PROJECT_ROOT/'evidence/upgrade/v5.0/evaluator-owner/runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder.mkdir(parents=True,exist_ok=False)
    report={'command':[sys.executable,'-m','evaluation.cli',*sys.argv[1:]],'started':started,'mode':mode,'target_code_executed':False,'actual_paid_calls':0,'actual_network_calls':0,'credentials_accessed':False,'ledger_opened':False,'synthetic':mode=='mock' or args.action=='calibrate','human_signoff':None,'teacher_approval':None,'limitations':['Synthetic calibration is not independent QA or real semantic evaluation.','Three historical unknown calls keep paid evaluation strictly blocked.']}
    source_paths=(*INSTALLATION_PINS,'evaluation/v5.py','evaluation/cli.py')
    report['evaluator_source_before']={p:sha256(safe_read(PROJECT_ROOT,p)) for p in source_paths}
    code=2
    try:
        if mode=='paid':raise EvaluationError('PRIOR_CALL_UNKNOWN_STOP')
        if args.action=='calibrate':
            if args.fixture_set!='v5-k1-k6-v1':raise EvaluationError('UNKNOWN_FIXTURE_SET')
            _installation();rows=await calibrate_v5(mode);report['results']=rows;report['calibration']={'case_count':len(rows),'matches':sum(r['matches_expected'] for r in rows),'false_pass':[r['case_id'] for r in rows if r['actual']=='PASS' and r['expected']!='PASS'],'synthetic_inputs':True,'real_paid_calibration':False}
            code=0 if all(r['matches_expected'] for r in rows) else 1
        else:
            files,tools,context=load_v5();precheck=context.precheck(tools);report['precheck']=precheck
            if args.action=='precheck':code=0 if not precheck['issues'] else 2
            else:
                rows=[];audits=[];evaluator=Evaluator(tools,files)
                for claim in context.claims:
                    evaluator.provider=MockProvider([_script(claim,'INSUFFICIENT_EVIDENCE')]) if mode=='mock' else None
                    result,audit=await evaluator.evaluate(claim,CONTRACT,VERSION);rows.append(result);audits.append(audit)
                final=context.precheck(tools)
                if final['issues']:
                    for row in rows:row.update(status='INSUFFICIENT_EVIDENCE',evidence_refs=[],reason='V5_IDENTITY_NOT_READY_OR_CHANGED',missing_check=['Main must register exact actual candidate/source/evidence and required windows.'])
                report.update(results=rows,audits=audits,final_precheck=final)
                code=1 if any(r['status']=='FAIL' for r in rows) else 2 if any(r['status']=='INSUFFICIENT_EVIDENCE' for r in rows) else 0
    except (EvaluationError,UnicodeError) as e:
        report['error_code']=e.code if isinstance(e,EvaluationError) else 'NON_UTF8_TRUSTED_DATA';code=2
    report['evaluator_source_after']={p:sha256(safe_read(PROJECT_ROOT,p)) for p in source_paths}
    if report['evaluator_source_before']!=report['evaluator_source_after']:
        report['error_code']='V5_EVALUATOR_CHANGED_DURING_RUN';code=2
        for row in report.get('results',[]):
            output=row.get('output',row);output.update(status='INSUFFICIENT_EVIDENCE',evidence_refs=[],reason='V5_EVALUATOR_CHANGED_DURING_RUN',missing_check=['Refreeze the changed evaluator and rerun only affected checks.'])
            if 'actual' in row:
                row['actual']='INSUFFICIENT_EVIDENCE';row['matches_expected']=row['actual']==row['expected']
        if 'calibration' in report:
            rows=report['results'];report['calibration'].update(matches=sum(r['matches_expected'] for r in rows),false_pass=[r['case_id'] for r in rows if r['actual']=='PASS' and r['expected']!='PASS'])
    report['exit_code']=code;report['ended']=datetime.now(timezone.utc).isoformat();path=folder/'report.json';path.write_bytes(json_bytes(report))
    print('V5 evidence:',path);print('Exit:',code,'; paid/network calls: 0');return code
