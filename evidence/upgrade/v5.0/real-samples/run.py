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
RUN_ID='v5-real-samples-single-run-v1'
CASES=(
    {'case_id':'G1','theme':'夜间校园图书馆闭馆巡查：找齐借阅资料并检查离馆装置，在一间阅览室内有序离开。','room_count':1,'difficulty':'easy','cap_units':200_000_000},
    {'case_id':'G2','theme':'校园天文社观测资料交接：在观测准备室与资料室之间核对记录、复用交接道具，完成关闭前的检查。','room_count':2,'difficulty':'normal','cap_units':200_000_000},
    {'case_id':'G3','theme':'校园生态实验楼标本交接：三间相连实验室保留采样资料与维护装置，需要跨房间核对材料后完成离楼检查。','room_count':3,'difficulty':'hard','cap_units':200_000_000},
)
QUESTIONS={'A1':'请解释眼前装置的操作说明与我已发现资料之间的一个局部关系，不要给完整输入。','A2':'你刚才说的这个关系为什么成立？请结合相同的已发现资料再解释一步，仍不要给完整输入。'}

def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(value): return hashlib.sha256(value).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat()
def source_map():
    files=list((ROOT/'backend/app').rglob('*.py'))+[ROOT/'backend/requirements.in',ROOT/'backend/requirements.lock.txt',ROOT/'frontend/src/assets/generated-catalog.json',Path(__file__)]
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

def prepare():
    preview_path=OUT/'offline-preview-v4.json'
    if preview_path.exists() or (OUT/'execute-started.json').exists(): raise StopRun('PREVIEW_OR_EXECUTION_ALREADY_EXISTS')
    from backend.app.ai.v5 import GenerationService,public_context,bounded_messages
    from backend.app.domain.generated import Draft,make_fixture,compile_level,GeneratedRules
    generations=[]
    for case in CASES:
        messages=GenerationService.messages(theme=case['theme'],room_count=case['room_count'],difficulty=case['difficulty'],draft_schema=Draft.model_json_schema())
        body=payload(messages,6000); bound=estimate(body,6000)
        if bound['cost_upper_units']>case['cap_units']: raise StopRun('GENERATION_PREVIEW_BOUND_EXCEEDED')
        generations.append({**case,'scope':'v5_generation','json_mode':True,'timeout_seconds':60,'payload':body,'bound':bound})
    # Explicit placeholder, never represented as a successful real generated level.
    rules=GeneratedRules(compile_level(make_fixture(2,'normal'),2,'normal')); state=rules.initial_state()
    for action in rules.compiled.witness:
        if action['tool']=='inspect': state,_=rules.apply_action(state,action['tool'],action['arguments'])
        if state.discovered_clue_ids: break
    public=rules.visible_state('PLACEHOLDER_SESSION',state)
    placeholders=[]
    history=[]
    for ident in ('A1','A2'):
        if ident=='A2': history=[{'kind':'dialogue','question':QUESTIONS['A1'],'answer':'[占位回复：实际执行必须使用A1真实成功回复，不会发送本占位内容]','clue_refs':[]}]
        messages,allowed=bounded_messages(public_context(public,QUESTIONS[ident],history)); body=payload(messages,600); bound=estimate(body,600)
        if bound['cost_upper_units']>50_000_000: raise StopRun('COMPANION_PREVIEW_BOUND_EXCEEDED')
        placeholders.append({'case_id':ident,'placeholder_only':True,'not_authorized_actual_payload':True,'question':QUESTIONS[ident],'stage_source':'PRIVATE_FIXTURE_PLACEHOLDER_ONLY','previous_reply_source':'PLACEHOLDER_ONLY' if ident=='A2' else None,'payload':body,'bound':bound,'allowed_refs':sorted(allowed)})
    sources=source_map()
    value={'kind':'offline_preview_not_execution','prepared_utc':stamp(),'run_id':RUN_ID,'candidate_sha256':sha(canonical(sources).encode()),'source':sources,'generation_cases':generations,'companion_placeholders':placeholders,'fixed_limits':{'maximum_cases':5,'generation_case_cap_cny':0.20,'companion_case_cap_cny':0.05,'sum_reserved_upper_cny':0.70,'automatic_retries':0,'historical_unknown_calls_required':3,'evaluation_calls_allowed':0},'execute_prerequisites':['Independent QA read-only approval of this file and preview; Main executes personally.','Exact source hashes unchanged since preview.','Official config deepseek-flash/api.deepseek.com; original canonical 10CNY ledger only.','Pre/post read-only historical unknown identities unchanged (3), pending0, not frozen.','A1 stage comes from an actual successful generated level via API; A2 requires successful A1 actual history.','Every exact outgoing payload and its bound are written before its one dispatch.'],'safety':{'prepare_reads_key':False,'prepare_opens_ledger':False,'prepare_network_calls':0,'prepare_game_database':False,'execute_game_database':'TEMP game-v5.sqlite only','reports_auth_headers':False,'keys_and_cookies':'Memory only; exact redaction and stop on forbidden content','evaluators':'Never invoked'}}
    raw_write(preview_path,value)
    print(canonical({'status':'prepared_only','preview':str(preview_path.relative_to(ROOT)),'candidate_sha256':value['candidate_sha256'],'generation_upper_cny':[g['bound']['cost_upper_cny'] for g in generations],'companion_placeholder_upper_cny':[g['bound']['cost_upper_cny'] for g in placeholders],'network_calls':0,'ledger_opened':False,'key_loaded':False}))


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
        allowed='v5_generation' if ident in {'G1','G2','G3'} else 'v5_companion'
        max_tokens=6000 if ident in {'G1','G2','G3'} else 600
        cap=200_000_000 if max_tokens==6000 else 50_000_000
        if self.stopped or ident not in {'G1','G2','G3','A1','A2'} or ident in self.attempts: raise StopRun('STOPPED_OR_DUPLICATE_CASE')
        if source_map()!=self.preview['source']: raise StopRun('SOURCE_CHANGED')
        if tools or tool_choice!='none' or scope!=allowed or limits.max_tokens!=max_tokens or not limits.json_mode: raise StopRun('UNAPPROVED_PROFILE')
        body=payload(messages,max_tokens); bound=estimate(body,max_tokens)
        if self.secret_present(body): self.stopped='SECRET_IN_MODEL_PAYLOAD'; raise StopRun(self.stopped)
        if bound['cost_upper_units']>cap or self.reserved_units+bound['cost_upper_units']>700_000_000 or len(self.attempts)>=5: raise StopRun('RUN_BOUND_EXCEEDED')
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
    marker=OUT/'execute-started.json'
    fd=os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try: os.write(fd,canonical({'run_id':RUN_ID,'utc':stamp(),'single_use_no_resume_or_retry':True,'candidate_sha256':preview['candidate_sha256']}).encode()); os.fsync(fd)
    finally: os.close(fd)
    controller=None; cases=[]; exit_code=1
    try:
        # Only execution may load the already-approved configuration/ledger.
        from backend.app.ai.provider import DeepSeekConfig
        from backend.app.ai.budget import BudgetLedger,PROJECT_LEDGER
        from backend.app.ai.v5 import GenerationService,CompanionService
        config=DeepSeekConfig.from_environment()
        if not config.api_key.strip() or config.model!=MODEL or config.base_url.rstrip('/')!='https://api.deepseek.com': raise StopRun('MISSING_OR_UNAPPROVED_PROVIDER_CONFIG')
        baseline=ledger_readonly()
        if baseline['cap_units']!=10_000_000_000 or baseline['frozen'] or baseline['unknown_calls']!=3 or baseline['pending_calls']: raise StopRun('INITIAL_LEDGER_UNSAFE')
        controller=Controller(preview,config.api_key,baseline)
        controller.save('ledger-before.json',public_snapshot(baseline))
        ledger=BudgetLedger(PROJECT_LEDGER)
        def factory(key):
            if key!=config.api_key: raise StopRun('REQUEST_KEY_CHANGED')
            return CaptureProvider(config,ledger,controller)
        with tempfile.TemporaryDirectory(prefix='v5-approved-real-samples-') as tmp:
            os.environ['GAMEPLAY_VERSION']='v5'; os.environ['SQLITE_PATH']=str(Path(tmp)/'game-v5.sqlite'); os.environ['AI_PROVIDER']='mock'
            from backend.app.main import create_v5_app
            from fastapi.testclient import TestClient
            app=create_v5_app(generation_service=GenerationService(factory),companion_service=CompanionService(factory))
            client=TestClient(app,base_url='http://127.0.0.1:8001',headers={'Origin':'http://127.0.0.1:8001'})
            csrf=client.get('/api/v2/auth/csrf').json()['data']['csrf_token']; controller.add_secret(csrf); client.headers['X-CSRF-Token']=csrf
            password=secrets.token_urlsafe(24); controller.add_secret(password)
            auth=client.post('/api/v2/auth/register',json={'username':'real_sample_fixture','password':password})
            if auth.status_code!=201: raise StopRun('TEMP_AUTH_FAILED')
            auth_data=auth.json()['data']; controller.add_secret(auth_data['csrf_token'])
            for value in client.cookies.values(): controller.add_secret(value)
            client.headers.update({'X-CSRF-Token':auth_data['csrf_token'],'X-Auth-Context':auth_data['auth_context']})
            def version(state): return {'request_id':str(uuid4()),'revision':state['revision'],'generation':state['generation']}
            successful=[]
            for case in CASES:
                controller.safe_ledger(); controller.current_case=case['case_id']
                response=client.post('/api/v2/level-generations',json={'request_id':'real-'+case['case_id'],'theme':case['theme'],'room_count':case['room_count'],'difficulty':case['difficulty']},headers={'X-AI-Api-Key':config.api_key})
                record={'case_id':case['case_id'],'api_status':response.status_code,'theme':case['theme'],'room_count':case['room_count'],'difficulty':case['difficulty'],'real_model_attempted':case['case_id'] in controller.attempts}
                data=response.json().get('data',{}); job=data.get('job')
                if job:
                    job_response=client.get('/api/v2/level-generations/'+job['job_id']); job=job_response.json()['data']['job']; record['job']=job
                if job and job['status']=='ready':
                    response=client.post('/api/v2/sessions',json={'request_id':'play-'+case['case_id'],'mode':'generated','level_id':job['level_id']})
                    if response.status_code not in {200,201}: raise StopRun('GENERATED_SESSION_FAILED')
                    sid=response.json()['data']['session_id']; state=response.json()['data']['visible_state']
                    owner=app.state.v5_database.authenticate(client.cookies.get('campus_v5_session'))
                    store=app.state.v5_database.owned(owner,sid); witness=store.rules.compiled.witness
                    for action in witness:
                        result=client.post(f'/api/v2/sessions/{sid}/actions',json={**version(state),**action})
                        if result.status_code!=200: raise StopRun('REAL_WITNESS_REPLAY_FAILED')
                        state=result.json()['data']['visible_state']
                    if state['status']!='won': raise StopRun('REAL_WITNESS_NOT_EXIT')
                    record.update(status='ready_and_replayed',definition_hash=store.rules.compiled.definition_hash,definition_version=store.rules.compiled.version,witness_actions=len(witness),witness_sha256=sha(canonical(witness).encode()),settlement=state['settlement'])
                    successful.append({'case_id':case['case_id'],'sid':sid,'state':state,'witness':witness,'level_id':job['level_id']})
                else: record['status']='not_successful'; record['error_code']=response.json().get('error',{}).get('code') or (job or {}).get('error_code')
                cases.append(record); controller.save(case['case_id']+'-api-result.json',record)
                controller.safe_ledger()
                if controller.stopped: raise StopRun(controller.stopped)
            if successful:
                chosen=next((s for s in successful if s['case_id']=='G2'),successful[0]); sid=chosen['sid']; state=chosen['state']
                result=client.post(f'/api/v2/sessions/{sid}/reset',json=version(state))
                if result.status_code!=200: raise StopRun('COMPANION_STAGE_RESET_FAILED')
                state=result.json()['data']['visible_state']
                for action in chosen['witness']:
                    result=client.post(f'/api/v2/sessions/{sid}/actions',json={**version(state),**action})
                    if result.status_code!=200: raise StopRun('COMPANION_STAGE_ACTION_FAILED')
                    state=result.json()['data']['visible_state']
                    if state['clues'] and any(o.get('kind')=='puzzle' and o['object_id'] in state['observed_object_ids'] and not o.get('completed') for o in state['objects']): break
                if state['status']!='playing' or not state['clues']: raise StopRun('COMPANION_PUBLIC_STAGE_UNAVAILABLE')
                controller.save('companion-actual-stage.json',{'fictional_test_content':True,'source_generation_case':chosen['case_id'],'level_id':chosen['level_id'],'visible_state':state,'placeholder':False})
                a1_ok=False
                for ident in ('A1','A2'):
                    if ident=='A2' and not a1_ok:
                        cases.append({'case_id':'A2','status':'skipped','reason':'A1_NOT_SUCCESSFUL'}); break
                    controller.safe_ledger(); controller.current_case=ident
                    result=client.post(f'/api/v2/sessions/{sid}/ai/turns',json={**version(state),'message':QUESTIONS[ident],'hint_level':2},headers={'X-AI-Provider':'deepseek','X-AI-Api-Key':config.api_key})
                    value=result.json(); record={'case_id':ident,'api_status':result.status_code,'source_generation_case':chosen['case_id'],'real_model_attempted':ident in controller.attempts,'response':value}
                    data=value.get('data',{}); ok=result.status_code==200 and value.get('ok') is True and data.get('usage',{}).get('model_calls')==1
                    record['status']='successful' if ok else 'not_successful'; cases.append(record); controller.save(ident+'-api-result.json',record)
                    if ok:
                        state=data['visible_state']
                        if ident=='A1': a1_ok=True; controller.previous_answer=data['answer']
                    controller.safe_ledger()
                    if controller.stopped: raise StopRun(controller.stopped)
            else:
                cases.extend([{'case_id':i,'status':'skipped','reason':'NO_SUCCESSFUL_GENERATED_STAGE'} for i in ('A1','A2')])
            controller.safe_ledger()
            exit_code=0 if len(cases)==5 and all(c.get('status') in {'ready_and_replayed','successful'} for c in cases) else 1
    except BaseException as error:
        code=getattr(error,'code','SANITIZED_RUN_FAILURE')
        if not isinstance(code,str) or not re.fullmatch('[A-Z_]{1,64}',code): code='SANITIZED_RUN_FAILURE'
        if controller:
            controller.stopped=controller.stopped or code
            controller.save('run-failure.json',{'error_code':code,'utc':stamp(),'no_retry':True})
        else: raw_write(OUT/'run-failure.json',{'error_code':code,'utc':stamp(),'no_retry':True})
        exit_code=1
    finally:
        result={'kind':'actual_paid_validation_run','run_id':RUN_ID,'candidate_sha256':preview['candidate_sha256'],'end_utc':stamp(),'exit_code':exit_code,'cases':cases,'attempted_case_ids':controller.attempts if controller else [],'sum_reserved_upper_cny':controller.reserved_units/1e9 if controller else 0,'stopped_reason':controller.stopped if controller else 'PRE_DISPATCH_FAILURE','automatic_retries':0,'evaluation_invoked':False,'game_database':'TEMP only; removed after run','source_after':source_map()}
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
    preview=json.loads((OUT/'offline-preview-v4.json').read_text(encoding='utf-8'))
    if preview.get('run_id')!=RUN_ID: raise StopRun('UNAPPROVED_RUN_ID')
    return execute(preview)
if __name__=='__main__':
    try: raise SystemExit(main())
    except StopRun as error: print(canonical({'status':'stopped','error_code':error.code,'no_retry':True})); raise SystemExit(1)
