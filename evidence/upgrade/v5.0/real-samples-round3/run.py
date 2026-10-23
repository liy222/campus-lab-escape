"""One reviewed v5 real-sample run. --prepare is strictly offline.

Only Main may execute after independent review. --execute is single-use: a durable
marker and pre-dispatch journal consume each fixed case, including failures. This
file never retries, substitutes a ledger, or invokes the evaluator.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys
import tempfile
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
OUT=Path(__file__).resolve().parent
MODEL='deepseek-flash'
# Exact current DeepSeekProvider reported-model allowlist; source hashes freeze it.
APPROVED_REPORTED_MODELS=frozenset({'deepseek-flash','deepseek-v4.1-flash','DeepSeek-V4.1-Flash','deepseek-v4.1-flash-1017','DeepSeek-V4.1-Flash-1017'})
RUN_ID='v5-real-samples-round3-pending-approval'
CASES=(
    {'case_id':'G2','theme':'校园天文社观测资料交接：在观测准备室与资料室之间核对记录、复用交接道具，完成关闭前的检查。','room_count':2,'difficulty':'normal','cap_units':200_000_000},
    {'case_id':'G3','theme':'校园生态实验楼标本交接：三间相连实验室保留采样资料与维护装置，需要跨房间核对材料后完成离楼检查。','room_count':3,'difficulty':'hard','cap_units':200_000_000},
)
HISTORICAL_INPUT_SHA256={'evidence/upgrade/v5.0/real-samples-round2/G1-provider-result.json': 'b7a2139acbe4bcc95e37320b6cd7dcf8606f21358cd0c1606530f46581725a29', 'evidence/upgrade/v5.0/real-samples-round2/G1-api-result.json': '748c8bcf0fd938d4f0d1be09ecdd0a45960f4b60f0e6d088615ddfaec205f4bd', 'evidence/upgrade/v5.0/real-samples-round2/companion-actual-stage.json': '52a86785516d2c14a5df96996cdf28c4a13b6e05fe41a9d7287aff8357db579b', 'evidence/upgrade/v5.0/real-samples-round2/A1-exact-payload.json': '3590994aaf6a1480433dfcfaad887826eb9f282f2d11000a4a4976a11eb7e28d'}
HISTORICAL_RUNNER_SHA256='f833068ad200c41b4016d1fa7e3f1b502bea2704ecfa0a2237b965a05bef185c'
QUESTIONS={'A1':'请解释眼前装置的操作说明与我已发现资料之间的一个局部关系，不要给完整输入。','A2':'你刚才说的这个关系为什么成立？请结合相同的已发现资料再解释一步，仍不要给完整输入。'}

def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(value): return hashlib.sha256(value).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat()
def source_map():
    files=list((ROOT/'backend/app').rglob('*.py'))+[ROOT/'backend/requirements.in',ROOT/'backend/requirements.lock.txt',ROOT/'frontend/src/assets/generated-catalog.json',Path(__file__)]+[ROOT/p for p in HISTORICAL_INPUT_SHA256]
    return {str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes()) for p in sorted(files)}
def payload(messages,max_tokens):
    return {'model':MODEL,'messages':messages,'max_tokens':max_tokens,'thinking':{'type':'disabled'},'stream':False,'response_format':{'type':'json_object'}}
def estimate(body,max_tokens):
    from backend.app.ai.budget import cost_units
    # Exactly DeepSeekProvider's encoding and conservative full-payload formula.
    encoded=json.dumps(body,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
    bound=len(encoded)*4+8192
    return {'payload_utf8_bytes':len(encoded),'input_token_bound':bound,'output_token_bound':max_tokens,'cost_upper_units':cost_units(bound,max_tokens),'cost_upper_cny':cost_units(bound,max_tokens)/1e9,'payload_sha256':sha(encoded)}
def raw_write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

class StopRun(Exception):
    def __init__(self,code): self.code=code; super().__init__(code)

def verify_historical_inputs():
    for filename,expected in HISTORICAL_INPUT_SHA256.items():
        if sha((ROOT/filename).read_bytes())!=expected: raise StopRun('HISTORICAL_INPUT_HASH_MISMATCH')
    old_runner=ROOT/'evidence/upgrade/v5.0/real-samples-round2/run.py'
    if sha(old_runner.read_bytes())!=HISTORICAL_RUNNER_SHA256: raise StopRun('HISTORICAL_RUNNER_CHANGED')


def version_body(state):
    return {'request_id':str(uuid4()),'revision':state['revision'],'generation':state['generation']}


def historical_projection(state):
    """Ignore only recreated account/run identities and actual start timestamp."""
    value=json.loads(canonical(state))
    for key in ('session_id','level_id','generation'): value.pop(key,None)
    value['statistics'].pop('started_at',None)
    return value


def gameplay_projection(state):
    """Allow only established hint metadata changes; retain every gameplay fact."""
    value=json.loads(canonical(state))
    value.pop('revision',None)
    for key in ('hint_count','current_hint_level'): value['statistics'].pop(key,None)
    return value


def make_temp_client(app,add_secret):
    from fastapi.testclient import TestClient
    client=TestClient(app,base_url='http://127.0.0.1:8001',headers={'Origin':'http://127.0.0.1:8001'})
    csrf=client.get('/api/v2/auth/csrf').json()['data']['csrf_token']; add_secret(csrf)
    for value in client.cookies.values(): add_secret(value)
    client.headers['X-CSRF-Token']=csrf
    password=secrets.token_urlsafe(24); add_secret(password)
    response=client.post('/api/v2/auth/register',json={'username':'round3_replay_fixture','password':password})
    if response.status_code!=201: raise StopRun('TEMP_AUTH_FAILED')
    data=response.json()['data']
    add_secret(data['csrf_token']); add_secret(data['auth_context'])
    for value in client.cookies.values(): add_secret(value)
    client.headers.update({'X-CSRF-Token':data['csrf_token'],'X-Auth-Context':data['auth_context']})
    return client,data['user']['user_id']


def rebuild_historical_stage(app,client,user_id):
    """Historical real definition replay fixture; no LLM, edited draft or state injection."""
    verify_historical_inputs()
    old=ROOT/'evidence/upgrade/v5.0/real-samples-round2'
    captured=json.loads((old/'G1-provider-result.json').read_text(encoding='utf-8'))
    original=json.loads((old/'G1-api-result.json').read_text(encoding='utf-8'))
    prior_stage=json.loads((old/'companion-actual-stage.json').read_text(encoding='utf-8'))['visible_state']
    old_a1=json.loads((old/'A1-exact-payload.json').read_text(encoding='utf-8'))
    prior_action_labels=json.loads(old_a1['payload']['messages'][-1]['content'])['recent_history']
    if sha(captured['content_redacted'].encode())!=captured['content_raw_sha256'] or captured.get('secret_detected'):
        raise StopRun('HISTORICAL_CAPTURE_CONTENT_HASH_MISMATCH')
    from backend.app.domain.generated import compile_level
    from backend.app.api.v5 import GenerationRequest
    from backend.app.ai.v5 import public_context,bounded_messages
    compiled=compile_level(captured['content_redacted'],1,'easy')
    if original['status']!='ready_and_replayed' or compiled.definition_hash!=original['definition_hash'] or sha(canonical(compiled.witness).encode())!=original['witness_sha256'] or len(compiled.witness)!=original['witness_actions']:
        raise StopRun('HISTORICAL_DEFINITION_OR_WITNESS_MISMATCH')
    request=GenerationRequest(request_id='historical-round2-G1-reconstruction',theme='Historical real round2 G1 replay fixture; not a new model generation.',room_count=1,difficulty='easy')
    db=app.state.v5_database
    status,job,dispatch=db.reserve_job(user_id,request)
    if status!=202 or not dispatch: raise StopRun('HISTORICAL_FIXTURE_RESERVATION_FAILED')
    db.job_phase(job['job_id'],'validating'); db.commit_level(job['job_id'],compiled)
    job=db.jobs(user_id,job['job_id']); level_id=job['level_id']
    response=client.post('/api/v2/sessions',json={'request_id':'historical-round2-G1-session','mode':'generated','level_id':level_id})
    if response.status_code!=201: raise StopRun('HISTORICAL_SESSION_CREATE_FAILED')
    sid=response.json()['data']['session_id']; state=response.json()['data']['visible_state']
    for action in compiled.witness:
        response=client.post(f'/api/v2/sessions/{sid}/actions',json={**version_body(state),**action})
        if response.status_code!=200: raise StopRun('HISTORICAL_FULL_WITNESS_REPLAY_FAILED')
        state=response.json()['data']['visible_state']
    if state['status']!='won': raise StopRun('HISTORICAL_REPLAY_NOT_EXIT')
    response=client.post(f'/api/v2/sessions/{sid}/reset',json=version_body(state))
    if response.status_code!=200: raise StopRun('HISTORICAL_STAGE_RESET_FAILED')
    state=response.json()['data']['visible_state']; prefix=[]
    for action in compiled.witness:
        response=client.post(f'/api/v2/sessions/{sid}/actions',json={**version_body(state),**action})
        if response.status_code!=200: raise StopRun('HISTORICAL_STAGE_LEGAL_ACTION_FAILED')
        prefix.append(action['tool']); state=response.json()['data']['visible_state']
        if historical_projection(state)==historical_projection(prior_stage): break
    if historical_projection(state)!=historical_projection(prior_stage): raise StopRun('HISTORICAL_PUBLIC_PROJECTION_MISMATCH')
    with db.transaction() as connection:
        rows=connection.execute("SELECT result_json FROM events WHERE session_id=? AND generation=? AND operation='action' AND outcome='committed' ORDER BY sequence DESC LIMIT 3",(sid,state['generation'])).fetchall()
    history=[]
    for row in reversed(rows):
        receipt=json.loads(row['result_json']).get('data',{}).get('receipt',{})
        if receipt.get('tool') not in compiled_rules_tools(): raise StopRun('UNEXPECTED_HISTORICAL_ACTION_TOOL')
        history.append({'kind':'action','tool':receipt['tool']})
    if [entry['tool'] for entry in history]!=['inspect','take','inspect']: raise StopRun('HISTORICAL_ACTION_HISTORY_MISMATCH')
    context=public_context(state,QUESTIONS['A1'],history)
    if context['recent_history']!=prior_action_labels: raise StopRun('HISTORICAL_ACTION_LABEL_MISMATCH')
    messages,allowed=bounded_messages(context)
    if json.loads(messages[-1]['content'])['recent_history']!=prior_action_labels: raise StopRun('BOUNDED_ACTION_LABEL_MISMATCH')
    report={'kind':'historical_real_definition_offline_reconstruction_fixture','new_real_generation':False,'production_fallback':False,'placeholder':False,'historical_source':'round2 G1 actual provider content','historical_input_sha256':HISTORICAL_INPUT_SHA256,'definition_hash':compiled.definition_hash,'witness_sha256':sha(canonical(compiled.witness).encode()),'witness_actions':len(compiled.witness),'full_witness_replayed_through_api_to_exit':True,'stage_rebuilt_through_legal_api_prefix':prefix,'state_injected':False,'public_projection_matches_original':True,'ignored_recreated_projection_fields':['session_id','level_id','generation','statistics.started_at'],'public_projection_sha256':sha(canonical(historical_projection(state)).encode()),'action_history':history,'bounded_action_labels':prior_action_labels,'setup_reservations':1,'historical_visible_state':prior_stage,'current_visible_state':state}
    return {'sid':sid,'state':state,'history':history,'messages':messages,'allowed_refs':sorted(allowed),'report':report}


def compiled_rules_tools():
    from backend.app.domain.generated import TOOL_MODELS
    return TOOL_MODELS


def authorization_matches(value,preview,preview_sha256):
    return (isinstance(value,dict) and value.get('approved') is True
            and value.get('run_id')==RUN_ID
            and value.get('preview_file_sha256')==preview_sha256
            and value.get('candidate_sha256')==preview['candidate_sha256']
            and value.get('scope')==['G2','G3','A1','A2']
            and type(value.get('max_calls')) is int and value['max_calls']==4
            and type(value.get('max_reserved_units')) is int and value['max_reserved_units']==500_000_000
            and isinstance(value.get('actual_user_approval_reference'),str) and bool(value['actual_user_approval_reference'].strip()))


def require_authorization(preview):
    try:
        value=json.loads((OUT/'user-authorization.json').read_text(encoding='utf-8'))
        matches=authorization_matches(value,preview,sha((OUT/'offline-preview-v1.json').read_bytes()))
    except (OSError,ValueError,TypeError): raise StopRun('FRESH_EXPLICIT_AUTHORIZATION_REQUIRED') from None
    if not matches: raise StopRun('AUTHORIZATION_SCOPE_OR_BINDING_MISMATCH')
    return {'authorization_sha256':sha((OUT/'user-authorization.json').read_bytes()),'actual_user_approval_reference':value['actual_user_approval_reference']}


def prepare():
    preview_path=OUT/'offline-preview-v1.json'
    if preview_path.exists() or (OUT/'execute-started.json').exists(): raise StopRun('PREVIEW_OR_EXECUTION_ALREADY_EXISTS')
    from backend.app.ai.v5 import GenerationService,public_context,bounded_messages
    from backend.app.domain.generated import Draft
    generations=[]
    for case in CASES:
        messages=GenerationService.messages(theme=case['theme'],room_count=case['room_count'],difficulty=case['difficulty'],draft_schema=Draft.model_json_schema())
        body=payload(messages,6000); bound=estimate(body,6000)
        if bound['cost_upper_units']>case['cap_units']: raise StopRun('GENERATION_PREVIEW_BOUND_EXCEEDED')
        generations.append({**case,'scope':'v5_generation','json_mode':True,'timeout_seconds':60,'payload':body,'bound':bound})
    class NoProviderDuringPrepare:
        async def generate(self,**kwargs): raise StopRun('PREPARE_PROVIDER_PROHIBITED')
        async def turn(self,**kwargs): raise StopRun('PREPARE_PROVIDER_PROHIBITED')
    with tempfile.TemporaryDirectory(prefix='v5-round3-offline-reconstruction-') as tmp:
        os.environ['GAMEPLAY_VERSION']='v5'; os.environ['SQLITE_PATH']=str(Path(tmp)/'game-v5.sqlite'); os.environ['AI_PROVIDER']='mock'
        from backend.app.main import create_v5_app
        app=create_v5_app(generation_service=NoProviderDuringPrepare(),companion_service=NoProviderDuringPrepare())
        transient=[]; client,user_id=make_temp_client(app,transient.append)
        historical=rebuild_historical_stage(app,client,user_id)
        a1_body=payload(historical['messages'],600); a1_bound=estimate(a1_body,600)
        if a1_bound['cost_upper_units']>50_000_000: raise StopRun('A1_PREVIEW_BOUND_EXCEEDED')
        placeholder_history=[{'kind':'dialogue','question':QUESTIONS['A1'],'answer':'[占位：未来A1若成功，必须使用实际经API与Store守卫交付的回答；此占位不会发送]','clue_refs':[]}]+historical['history']
        a2_messages,a2_allowed=bounded_messages(public_context(historical['state'],QUESTIONS['A2'],placeholder_history))
        a2_body=payload(a2_messages,600); a2_bound=estimate(a2_body,600)
        if a2_bound['cost_upper_units']>50_000_000: raise StopRun('A2_PLACEHOLDER_BOUND_EXCEEDED')
        companion=[{'case_id':'A1','placeholder':False,'source':'exact historical round2 G1 public facts and actual reconstructed event history','payload':a1_body,'bound':a1_bound,'allowed_refs':historical['allowed_refs'],'not_authorized_for_paid_dispatch':True},
                   {'case_id':'A2','placeholder':True,'actual_payload_reviewed':False,'not_authorized_actual_payload':True,'source':'placeholder only; actual A1 API-delivered answer required at execute','payload':a2_body,'bound':a2_bound,'allowed_refs':sorted(a2_allowed)}]
        sources=source_map()
        value={'kind':'offline_preview_not_execution','prepared_utc':stamp(),'run_id':RUN_ID,'candidate_sha256':sha(canonical(sources).encode()),'source':sources,'generation_cases':generations,'companion_cases':companion,'historical_reconstruction':historical['report'],'fixed_limits':{'maximum_cases':4,'scope':['G2','G3','A1','A2'],'generation_case_cap_cny':0.20,'companion_case_cap_cny':0.05,'sum_reserved_upper_units':500_000_000,'sum_reserved_upper_cny':0.50,'automatic_retries':0,'historical_unknown_calls_required':3,'evaluation_calls_allowed':0,'historical_setup_reservations':1,'new_generation_reservations':2},'execute_prerequisites':['Independent QA read-only preflight, then a NEW explicit finite user approval. Main dispatches personally.','Main creates user-authorization.json only after the actual approval, binding this preview SHA/candidate/fixed scope/max4/.50. The file is not independent proof of human approval; retain actual reply reference.','Authorization gate runs before marker creation, credential/config loading or canonical ledger access.','Exact source and four historical capture hashes unchanged.','Canonical 10CNY ledger only, old3unknown identities unchanged, pending0, not frozen; newunknown/model anomaly/secret stops.','A1/A2 use only historical reconstructed G1, independent of new G2/G3 admission; A2 requires newly delivered successful A1.'],'safety':{'prepare_key_loaded':False,'prepare_canonical_ledger_opened':False,'prepare_provider_or_network_calls':0,'prepare_game_database':'TEMP game-v5.sqlite only, removed after reconstruction','reports_auth_values':False,'actual_paid_dispatch':False,'evaluation_invoked':False}}
        serialized=canonical(value)
        if any(secret and secret in serialized for secret in transient): raise StopRun('PREPARATION_SECRET_LEAK')
        raw_write(preview_path,value)
    preview_sha=sha(preview_path.read_bytes())
    report={'kind':'round3_offline_preparation_source_stop','prepared_utc':stamp(),'runner_sha256':sha(Path(__file__).read_bytes()),'preview_sha256':preview_sha,'candidate_sha256':value['candidate_sha256'],'reviewed_round2_runner_sha256':HISTORICAL_RUNNER_SHA256,'historical_input_sha256':HISTORICAL_INPUT_SHA256,'generation_upper_cny':[g['bound']['cost_upper_cny'] for g in generations],'exact_A1_upper_cny':a1_bound['cost_upper_cny'],'A2_placeholder_upper_cny':a2_bound['cost_upper_cny'],'A2_actual_payload_preapproved':False,'historical_fixture_definition_and_witness_match':True,'public_projection_and_actual_3_action_labels_match':True,'authorization_file_created':False,'future_Main_authorization_format':{'approved':False,'run_id':RUN_ID,'preview_file_sha256':preview_sha,'candidate_sha256':value['candidate_sha256'],'scope':['G2','G3','A1','A2'],'max_calls':4,'max_reserved_units':500_000_000,'actual_user_approval_reference':'Main supplies reference to a future actual explicit user approval; do not infer approval from this template.'},'actual_command':"python -B -X utf8 evidence/upgrade/v5.0/real-samples-round3/run.py --prepare",'exit_code':0,'key_or_config_loaded':False,'canonical_ledger_opened':False,'network_calls':0,'paid_calls':0,'product_or_old_artifacts_modified':False,'limitations':['Historical real G1 is an offline reconstruction fixture, not a new real generation or product fallback.','A2 remains placeholder and is replaced only by current API-delivered A1 history with its own <=.05 bound.','No fresh paid authorization exists at preparation; no execute command was invoked.','Companion quality requires actual later delivery and finite manual review, never a paid evaluator.']}
    raw_write(OUT/'preparation-report.json',report)
    print(canonical({'status':'prepared_only','preview':str(preview_path.relative_to(ROOT)),'candidate_sha256':value['candidate_sha256'],'generation_upper_cny':report['generation_upper_cny'],'exact_A1_upper_cny':a1_bound['cost_upper_cny'],'A2_placeholder_upper_cny':a2_bound['cost_upper_cny'],'historical_definition_rebuilt_via_API':True,'actual_history_tools':[x['tool'] for x in historical['history']],'key_loaded':False,'canonical_ledger_opened':False,'network_calls':0,'authorization_created':False}))


def ledger_readonly():
    from backend.app.ai.budget import PROJECT_LEDGER
    if not PROJECT_LEDGER.is_file(): raise StopRun('CANONICAL_LEDGER_MISSING')
    db=sqlite3.connect(PROJECT_LEDGER.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        db.execute('PRAGMA query_only=ON')
        cap,frozen=db.execute('SELECT cap,frozen FROM budget_config WHERE id=1').fetchone()
        rows=db.execute('SELECT id,state,charged FROM budget_calls ORDER BY id').fetchall()
    finally: db.close()
    unknown=[(ident,state) for ident,state,_ in rows if state=='unknown']
    return {'cap_units':cap,'frozen':bool(frozen),'charged_upper_units':sum(r[2] for r in rows),'calls':len(rows),'unknown_calls':len(unknown),'pending_calls':sum(r[1]=='reserved' for r in rows),'unknown_identity_sha256':sha(canonical(unknown).encode()),'_all_ids':{r[0] for r in rows}}

def public_snapshot(value): return {k:v for k,v in value.items() if not k.startswith('_')}

class Controller:
    def __init__(self,preview,key,baseline):
        self.preview=preview; self.secrets={key}; self.key=key; self.baseline=baseline
        self.reserved_units=0; self.attempts=[]; self.stopped=None; self.current_case=None; self.call_ids=set(); self.previous_answer=None
    def add_secret(self,value):
        if isinstance(value,str) and value: self.secrets.add(value)
    def scrub(self,value):
        if isinstance(value,str):
            for secret in sorted(self.secrets,key=len,reverse=True): value=value.replace(secret,'[REDACTED]')
            return value
        if isinstance(value,list): return [self.scrub(x) for x in value]
        if isinstance(value,tuple): return [self.scrub(x) for x in value]
        if isinstance(value,dict): return {self.scrub(str(k)):self.scrub(v) for k,v in value.items()}
        return value
    def secret_present(self,value):
        text=canonical(value)
        return any(secret and secret in text for secret in self.secrets)
    def save(self,name,value): raw_write(OUT/name,self.scrub(value))
    def journal(self,value):
        line=canonical(self.scrub(value))+'\n'
        fd=os.open(OUT/'dispatch-journal.jsonl',os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        try: os.write(fd,line.encode()); os.fsync(fd)
        finally: os.close(fd)
    def safe_ledger(self):
        current=ledger_readonly()
        if current['cap_units']!=10_000_000_000 or current['frozen'] or current['pending_calls'] or current['unknown_calls']!=3 or current['unknown_identity_sha256']!=self.baseline['unknown_identity_sha256']:
            self.stopped='LEDGER_UNSAFE_OR_NEW_UNKNOWN'; raise StopRun(self.stopped)
        foreign=current['_all_ids']-self.baseline['_all_ids']-self.call_ids
        if foreign: self.stopped='CONCURRENT_LEDGER_CHANGE'; raise StopRun(self.stopped)
        return current
    def begin(self,messages,tools,limits,scope,tool_choice):
        ident=self.current_case
        allowed='v5_generation' if ident in {'G2','G3'} else 'v5_companion'
        max_tokens=6000 if ident in {'G2','G3'} else 600
        cap=200_000_000 if max_tokens==6000 else 50_000_000
        if self.stopped or ident not in {'G2','G3','A1','A2'} or ident in self.attempts: raise StopRun('STOPPED_OR_DUPLICATE_CASE')
        if source_map()!=self.preview['source']: raise StopRun('SOURCE_CHANGED')
        if tools or tool_choice!='none' or scope!=allowed or limits.max_tokens!=max_tokens or not limits.json_mode: raise StopRun('UNAPPROVED_PROFILE')
        body=payload(messages,max_tokens); bound=estimate(body,max_tokens)
        if self.secret_present(body): self.stopped='SECRET_IN_MODEL_PAYLOAD'; raise StopRun(self.stopped)
        if bound['cost_upper_units']>cap or self.reserved_units+bound['cost_upper_units']>500_000_000 or len(self.attempts)>=4: raise StopRun('RUN_BOUND_EXCEEDED')
        if ident=='A1' and bound['payload_sha256']!=self.preview['companion_cases'][0]['bound']['payload_sha256']: raise StopRun('A1_PAYLOAD_DIFFERS_FROM_REVIEWED_PREVIEW')
        if ident=='A2':
            actual_context=json.loads(messages[-1]['content'])
            if not self.previous_answer or not any(e.get('kind')=='dialogue' and e.get('answer')==self.previous_answer for e in actual_context.get('recent_history',[])): raise StopRun('A2_MISSING_REAL_A1_HISTORY')
        before=self.safe_ledger()
        self.save(ident+'-exact-payload.json',{'case_id':ident,'source_candidate_sha256':self.preview['candidate_sha256'],'placeholder':False,'scope':scope,'payload':body,'bound':bound,'ledger_before':public_snapshot(before)})
        self.attempts.append(ident); self.reserved_units+=bound['cost_upper_units']
        self.journal({'phase':'before_dispatch','case_id':ident,'utc':stamp(),'bound':bound,'attempt_number':len(self.attempts),'sum_reserved_upper_units':self.reserved_units,'automatic_retry':False})
        return ident,bound

class CaptureProvider:
    def __init__(self,config,ledger,controller):
        from backend.app.ai.provider import DeepSeekProvider
        self.inner=DeepSeekProvider(config,ledger=ledger); self.controller=controller; self.last_response_metadata=None
    def check_model_anomaly(self,reply=None):
        metadata=self.inner.last_response_metadata
        models=[]
        if isinstance(metadata,dict) and 'reported_model' in metadata:
            models.append(metadata['reported_model'])
        if reply is not None:
            models.append(reply.reported_model)
        if any(model not in APPROVED_REPORTED_MODELS for model in models):
            self.controller.stopped='MODEL_ANOMALY_STOP'
            return True
        return False
    async def complete(self,messages,tools,limits,*,scope,tool_choice):
        c=self.controller; ident,bound=c.begin(messages,tools,limits,scope,tool_choice)
        try:
            reply=await self.inner.complete(messages,tools,limits,scope=scope,tool_choice=tool_choice)
            self.last_response_metadata=self.inner.last_response_metadata
            if reply.call_id: c.call_ids.add(reply.call_id)
            if self.check_model_anomaly(reply): raise StopRun('MODEL_ANOMALY_STOP')
            contains_secret=c.secret_present(reply.content or '')
            c.save(ident+'-provider-result.json',{'case_id':ident,'fictional_test_content':True,'content_redacted':reply.content,'content_raw_sha256':sha((reply.content or '').encode()),'usage':reply.usage,'requested_model':reply.requested_model,'reported_model':reply.reported_model,'finish_reason':reply.finish_reason,'call_id':reply.call_id,'cost_upper_cny':reply.cost_upper_cny,'secret_detected':contains_secret})
            after=c.safe_ledger()
            c.journal({'phase':'after_dispatch','case_id':ident,'utc':stamp(),'outcome':'response','usage':reply.usage,'ledger_after':public_snapshot(after)})
            if contains_secret: c.stopped='SECRET_IN_MODEL_RESPONSE'; raise StopRun(c.stopped)
            return reply
        except BaseException as error:
            self.last_response_metadata=self.inner.last_response_metadata
            call_id=getattr(error,'call_id',None) or (self.last_response_metadata or {}).get('call_id')
            if call_id: c.call_ids.add(call_id)
            anomaly=self.check_model_anomaly()
            code='MODEL_ANOMALY_STOP' if anomaly or c.stopped=='MODEL_ANOMALY_STOP' else getattr(error,'code','INTERRUPTED_OR_INTERNAL')
            if not isinstance(code,str) or not re.fullmatch('[A-Z_]{1,64}',code): code='SANITIZED_PROVIDER_FAILURE'
            try: after=public_snapshot(c.safe_ledger())
            except BaseException: after={'status':'unsafe_or_unavailable'}
            c.journal({'phase':'after_dispatch','case_id':ident,'utc':stamp(),'outcome':'failed','error_code':code,'ledger_after':after})
            raise


def execute(preview):
    if source_map()!=preview['source']: raise StopRun('SOURCE_CHANGED_SINCE_REVIEWED_PREVIEW')
    # Fresh actual user approval must be bound before marker/config/Key/ledger access.
    authorization=require_authorization(preview)
    marker=OUT/'execute-started.json'
    try: fd=os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError: raise StopRun('RUN_ALREADY_STARTED_NO_RETRY') from None
    try: os.write(fd,canonical({'run_id':RUN_ID,'utc':stamp(),'single_use_no_resume_or_retry':True,'candidate_sha256':preview['candidate_sha256'],'authorization_sha256':authorization['authorization_sha256']}).encode()); os.fsync(fd)
    finally: os.close(fd)
    controller=None; cases=[]; exit_code=1
    try:
        from backend.app.ai.provider import DeepSeekConfig
        from backend.app.ai.budget import BudgetLedger,PROJECT_LEDGER
        from backend.app.ai.v5 import GenerationService,CompanionService
        config=DeepSeekConfig.from_environment()
        if not config.api_key.strip() or config.model!=MODEL or config.base_url.rstrip('/')!='https://api.deepseek.com': raise StopRun('MISSING_OR_UNAPPROVED_PROVIDER_CONFIG')
        baseline=ledger_readonly()
        if baseline['cap_units']!=10_000_000_000 or baseline['frozen'] or baseline['unknown_calls']!=3 or baseline['pending_calls']: raise StopRun('INITIAL_LEDGER_UNSAFE')
        controller=Controller(preview,config.api_key,baseline)
        controller.save('authorization-binding.json',authorization)
        controller.save('ledger-before.json',public_snapshot(baseline))
        ledger=BudgetLedger(PROJECT_LEDGER)
        def factory(key):
            if key!=config.api_key: raise StopRun('REQUEST_KEY_CHANGED')
            return CaptureProvider(config,ledger,controller)
        with tempfile.TemporaryDirectory(prefix='v5-round3-approved-real-samples-') as tmp:
            os.environ['GAMEPLAY_VERSION']='v5'; os.environ['SQLITE_PATH']=str(Path(tmp)/'game-v5.sqlite'); os.environ['AI_PROVIDER']='mock'
            from backend.app.main import create_v5_app
            app=create_v5_app(generation_service=GenerationService(factory),companion_service=CompanionService(factory))
            client,user_id=make_temp_client(app,controller.add_secret)
            historical=rebuild_historical_stage(app,client,user_id)
            controller.save('historical-G1-stage-reconstruction.json',historical['report'])
            # One historical setup reservation plus exactly two requested generations.
            for case in CASES:
                controller.safe_ledger(); controller.current_case=case['case_id']
                response=client.post('/api/v2/level-generations',json={'request_id':'round3-'+case['case_id'],'theme':case['theme'],'room_count':case['room_count'],'difficulty':case['difficulty']},headers={'X-AI-Api-Key':config.api_key})
                record={'case_id':case['case_id'],'api_status':response.status_code,'theme':case['theme'],'room_count':case['room_count'],'difficulty':case['difficulty'],'real_model_attempted':case['case_id'] in controller.attempts}
                job=response.json().get('data',{}).get('job')
                if job:
                    job=client.get('/api/v2/level-generations/'+job['job_id']).json()['data']['job']; record['job']=job
                if job and job['status']=='ready':
                    response=client.post('/api/v2/sessions',json={'request_id':'round3-play-'+case['case_id'],'mode':'generated','level_id':job['level_id']})
                    if response.status_code not in {200,201}: raise StopRun('GENERATED_SESSION_FAILED')
                    sid=response.json()['data']['session_id']; state=response.json()['data']['visible_state']
                    owner=app.state.v5_database.authenticate(client.cookies.get('campus_v5_session'))
                    store=app.state.v5_database.owned(owner,sid); witness=store.rules.compiled.witness
                    for action in witness:
                        replay=client.post(f'/api/v2/sessions/{sid}/actions',json={**version_body(state),**action})
                        if replay.status_code!=200: raise StopRun('REAL_WITNESS_REPLAY_FAILED')
                        state=replay.json()['data']['visible_state']
                    if state['status']!='won': raise StopRun('REAL_WITNESS_NOT_EXIT')
                    record.update(status='ready_and_replayed',definition_hash=store.rules.compiled.definition_hash,definition_version=store.rules.compiled.version,witness_actions=len(witness),witness_sha256=sha(canonical(witness).encode()),settlement=state['settlement'])
                else:
                    record.update(status='not_successful',error_code=response.json().get('error',{}).get('code') or (job or {}).get('error_code'))
                cases.append(record); controller.save(case['case_id']+'-api-result.json',record)
                controller.safe_ledger()
                if controller.stopped: raise StopRun(controller.stopped)
            # This stage is independent of either new generation's admission result.
            sid=historical['sid']; state=client.get(f'/api/v2/sessions/{sid}/state').json()['data']['visible_state']
            if historical_projection(state)!=historical_projection(historical['state']): raise StopRun('HISTORICAL_STAGE_CHANGED_BEFORE_A1')
            a1_delivered=False
            for ident in ('A1','A2'):
                if ident=='A2' and not a1_delivered:
                    cases.append({'case_id':'A2','status':'skipped','reason':'NEW_A1_NOT_API_DELIVERED'}); break
                controller.safe_ledger(); controller.current_case=ident
                before=json.loads(canonical(state))
                response=client.post(f'/api/v2/sessions/{sid}/ai/turns',json={**version_body(state),'message':QUESTIONS[ident],'hint_level':2},headers={'X-AI-Provider':'deepseek','X-AI-Api-Key':config.api_key})
                value=response.json(); data=value.get('data',{})
                delivered=(response.status_code==200 and value.get('ok') is True and data.get('usage',{}).get('provider')=='deepseek' and data.get('usage',{}).get('model_calls')==1 and data.get('status') in {'completed','no_suggestion'})
                current=client.get(f'/api/v2/sessions/{sid}/state')
                if current.status_code!=200: raise StopRun('COMPANION_POST_STATE_UNAVAILABLE')
                after=current.json()['data']['visible_state']
                facts_equal=gameplay_projection(before)==gameplay_projection(after)
                metadata={'revision_before':before['revision'],'revision_after':after['revision'],'hint_count_before':before['statistics']['hint_count'],'hint_count_after':after['statistics']['hint_count'],'current_hint_level_before':before['statistics']['current_hint_level'],'current_hint_level_after':after['statistics']['current_hint_level'],'rule':'Successful generated-mode model hint increments hint_count/revision once; existing generated current_hint_level projection remains unchanged. Failure does not count as a delivered hint.'}
                record={'case_id':ident,'api_status':response.status_code,'source_generation_case':'HISTORICAL_ROUND2_G1','not_current_real_generation':True,'real_model_attempted':ident in controller.attempts,'api_storeguard_delivered':delivered,'status':'successful' if delivered else 'not_successful','response':value,'before_visible_state':before,'after_visible_state':after,'gameplay_facts_unchanged':facts_equal,'allowed_metadata_changes':metadata,'raw_provider_success_alone_is_not_delivery':True}
                cases.append(record); controller.save(ident+'-api-result.json',record)
                if not facts_equal: raise StopRun('COMPANION_ADVANCED_GAMEPLAY_FACTS')
                expected=1 if delivered else 0
                if after['revision']-before['revision']!=expected or after['statistics']['hint_count']-before['statistics']['hint_count']!=expected or after['statistics']['current_hint_level']!=before['statistics']['current_hint_level']:
                    raise StopRun('COMPANION_HINT_METADATA_DELTA_MISMATCH')
                state=after
                if delivered and ident=='A1':
                    a1_delivered=True; controller.previous_answer=data['answer']
                controller.safe_ledger()
                if controller.stopped: raise StopRun(controller.stopped)
            controller.safe_ledger()
            exit_code=0 if len(cases)==4 and all(c.get('status') in {'ready_and_replayed','successful'} for c in cases) else 1
    except BaseException as error:
        code=getattr(error,'code','SANITIZED_RUN_FAILURE')
        if not isinstance(code,str) or not re.fullmatch('[A-Z_]{1,64}',code): code='SANITIZED_RUN_FAILURE'
        if controller:
            controller.stopped=controller.stopped or code
            controller.save('run-failure.json',{'error_code':code,'utc':stamp(),'no_retry':True})
        else: raw_write(OUT/'run-failure.json',{'error_code':code,'utc':stamp(),'no_retry':True})
        exit_code=1
    finally:
        result={'kind':'actual_paid_validation_round3','run_id':RUN_ID,'candidate_sha256':preview['candidate_sha256'],'end_utc':stamp(),'exit_code':exit_code,'scope':['G2','G3','A1','A2'],'cases':cases,'attempted_case_ids':controller.attempts if controller else [],'sum_reserved_upper_cny':controller.reserved_units/1e9 if controller else 0,'maximum_reserved_upper_cny':0.50,'stopped_reason':controller.stopped if controller else 'PRE_DISPATCH_FAILURE','automatic_retries':0,'evaluation_invoked':False,'historical_G1_is_new_real_generation':False,'historical_G1_role':'Offline replay fixture from exact already-real-generated capture; companion stage independent of current G2/G3 results.','game_database':'TEMP only; removed after run','source_after':source_map()}
        if controller:
            try: controller.save('ledger-after.json',public_snapshot(ledger_readonly()))
            except BaseException: result['ledger_after_status']='unavailable'
            controller.save('result.json',result)
        else: raw_write(OUT/'result.json',result)
        print(canonical({'run_id':RUN_ID,'exit_code':exit_code,'attempted_case_ids':result['attempted_case_ids'],'sum_reserved_upper_cny':result['sum_reserved_upper_cny'],'automatic_retries':0}))
    return exit_code


def main():
    os.chdir(ROOT)
    parser=argparse.ArgumentParser(); modes=parser.add_mutually_exclusive_group(required=True); modes.add_argument('--prepare',action='store_true'); modes.add_argument('--execute',action='store_true'); args=parser.parse_args()
    if args.prepare: prepare(); return 0
    preview=json.loads((OUT/'offline-preview-v1.json').read_text(encoding='utf-8'))
    if preview.get('run_id')!=RUN_ID: raise StopRun('UNAPPROVED_RUN_ID')
    return execute(preview)
if __name__=='__main__':
    try: raise SystemExit(main())
    except StopRun as error: print(canonical({'status':'stopped','error_code':error.code,'no_retry':True})); raise SystemExit(1)
