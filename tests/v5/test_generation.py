"""N03/N04/A04/A06: jobs, fake-transport production pipeline and reservations."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import threading
import time
from pathlib import Path
import httpx
import pytest
from .conftest import Actor, CANARY, rid, assert_error, make_fixture
from backend.app.ai.v5 import GenerationService, CompanionService, ServiceError
from backend.app.ai.provider import DeepSeekProvider, DeepSeekConfig, CallLimits, GenerationLimits, V5CompanionLimits, ProviderError
from backend.app.ai.budget import BudgetLedger
from backend.app.domain.generated import Draft, compile_level
from backend.app.api.v5 import GenerationRequest
from backend.app.storage.v5 import V5Database

def wire_body(content,usage=True,finish='stop'):
    body={'model':'deepseek-flash','choices':[{'finish_reason':finish,'message':{'role':'assistant','content':content}}]}
    if usage: body['usage']={'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}
    return body

def test_real_adapter_fake_httpx_generation_profile_and_secret_boundary(tmp_path):
    """Production GenerationService/DeepSeekProvider, entirely injected HTTPX transport."""
    seen=[]; ledger=BudgetLedger(tmp_path/'fake-only-budget.sqlite')
    def handler(request):
        seen.append(request)
        assert request.url==httpx.URL('https://api.deepseek.com/chat/completions')
        assert request.headers['authorization']=='Bearer '+CANARY
        assert CANARY.encode() not in request.content
        return httpx.Response(200,json=wire_body(json.dumps(make_fixture(1,'easy'))))
    provider=DeepSeekProvider(DeepSeekConfig(CANARY),ledger,transport=httpx.MockTransport(handler))
    service=GenerationService(lambda key:provider)
    result=asyncio.run(service.generate(theme='校园 '+CANARY,room_count=1,difficulty='easy',api_key=CANARY,draft_schema=Draft.model_json_schema()))
    assert compile_level(result,1,'easy').witness
    assert len(seen)==1
    payload=json.loads(seen[0].content)
    assert payload['max_tokens']==6000 and payload['response_format']=={'type':'json_object'}
    assert not {'tools','tool_choice'}&payload.keys()
    assert CallLimits().max_tokens==1000 and CallLimits().timeout_seconds==20
    assert GenerationLimits().timeout_seconds==60
    assert V5CompanionLimits().max_tokens==600 and V5CompanionLimits().timeout_seconds==20
    with sqlite3.connect(ledger.path) as c:
        assert c.execute('SELECT scope,state FROM budget_calls').fetchone()==('v5_generation','settled')
        assert CANARY not in '\n'.join(c.iterdump())

def test_companion_full_serialized_payload_cap_and_profile_scope(tmp_path):
    from backend.app.ai.v5 import bounded_messages,public_context
    from backend.app.domain.generated import GeneratedRules
    from backend.app.ai.budget import cost_units
    compiled=compile_level(make_fixture(1,'easy'),1,'easy')
    rules=GeneratedRules(compiled); state=rules.visible_state('private',rules.initial_state())
    calls=[]
    history=[{'kind':'dialogue','question':'问题'*150,'answer':'解释'*180} for _ in range(3)]
    history += [{'kind':'action','tool':'inspect','arguments':{'private':'must not forward'}} for _ in range(3)]
    with pytest.raises(ServiceError) as error:
        bounded_messages(public_context(state,'下一步？',history))
    assert error.value.code=='AI_LIMIT_REACHED' and calls==[]
    # A shorter equivalent synthetic history must still fit and send at most once.
    short=[{'kind':'dialogue','question':'局部问题','answer':'公开的简短解释'} for _ in range(3)]
    short += history[3:]
    messages,allowed=bounded_messages(public_context(state,'下一步？',short))
    payload={'model':'deepseek-flash','messages':messages,'max_tokens':600,'thinking':{'type':'disabled'},'stream':False,'response_format':{'type':'json_object'}}
    assert cost_units(len(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode())*4+8192,600)<=50_000_000
    assert 'must not forward' not in json.dumps(messages)
    assert len(json.loads(messages[1]['content'])['recent_history'])<=6
    ledger=BudgetLedger(tmp_path/'fake-only-budget.sqlite')
    def handler(request):
        calls.append(request); return httpx.Response(200,json=wire_body('{"answer":"先看看公开物件。","clue_refs":[]}'))
    provider=DeepSeekProvider(DeepSeekConfig(CANARY),ledger,transport=httpx.MockTransport(handler))
    reply=asyncio.run(provider.complete(messages,[],V5CompanionLimits(),scope='v5_companion',tool_choice='none'))
    assert len(calls)==1 and json.loads(calls[0].content)['max_tokens']==600
    for limits,scope,choice in [(GenerationLimits(),'game','none'),(GenerationLimits(),'v5_generation','auto'),(V5CompanionLimits(),'game','none'),(CallLimits(max_tokens=6000),'game','none')]:
        with pytest.raises(ProviderError): asyncio.run(provider.complete(messages,[],limits,scope=scope,tool_choice=choice))
    assert len(calls)==1

def test_fake_budget_and_oversize_limits_prevent_send(tmp_path):
    ledger=BudgetLedger(tmp_path/'fake-only-budget.sqlite',cap_units=1); sends=[]
    transport=httpx.MockTransport(lambda request:sends.append(request) or httpx.Response(500))
    provider=DeepSeekProvider(DeepSeekConfig(CANARY),ledger,transport=transport)
    with pytest.raises(ProviderError) as error: asyncio.run(provider.complete([{'role':'user','content':'test'}],[],GenerationLimits(),scope='v5_generation',tool_choice='none'))
    assert error.value.code=='AI_BUDGET_EXHAUSTED' and sends==[]
    provider=DeepSeekProvider(DeepSeekConfig(CANARY),BudgetLedger(tmp_path/'fake-budget-2.sqlite'),transport=transport)
    with pytest.raises(ProviderError) as error: asyncio.run(provider.complete([{'role':'user','content':'x'*300000}],[],GenerationLimits(),scope='v5_generation',tool_choice='none'))
    assert error.value.code=='INPUT_TOO_LARGE' and sends==[]

@pytest.mark.parametrize('kind,expected', [('empty','MODEL_INVALID_OUTPUT'),('truncated','MODEL_INVALID_OUTPUT'),('auth','MODEL_OUTCOME_UNKNOWN'),('timeout','MODEL_OUTCOME_UNKNOWN'),('missing_usage','MODEL_OUTCOME_UNKNOWN')])
def test_fake_provider_failures_conservative_one_send_and_unknown_charge(tmp_path,kind,expected):
    count=0; ledger=BudgetLedger(tmp_path/'fake-only-budget.sqlite')
    def handler(request):
        nonlocal count; count+=1
        if kind=='auth': return httpx.Response(401,json={'error':{'message':'synthetic'}})
        if kind=='timeout': raise httpx.ReadTimeout('synthetic',request=request)
        return httpx.Response(200,json=wire_body('' if kind=='empty' else '{' if kind=='truncated' else json.dumps(make_fixture(1,'easy')),usage=kind!='missing_usage'))
    provider=DeepSeekProvider(DeepSeekConfig(CANARY),ledger,transport=httpx.MockTransport(handler))
    service=GenerationService(lambda key:provider)
    with pytest.raises(ServiceError) as error:
        asyncio.run(service.generate(theme='offline',room_count=1,difficulty='easy',api_key=CANARY,draft_schema=Draft.model_json_schema()))
    assert error.value.code==expected
    assert count==1
    with sqlite3.connect(ledger.path) as c:
        row=c.execute('SELECT state,reserved,charged FROM budget_calls').fetchone()
        assert row and row[2]>0
        if kind in {'auth','timeout','missing_usage'}: assert row[0]=='unknown' and row[1]==row[2]

@pytest.mark.parametrize('code,status',[('MODEL_TIMEOUT','failed'),('MODEL_UNAVAILABLE','failed'),('MODEL_INVALID_OUTPUT','rejected'),('MODEL_OUTCOME_UNKNOWN','unknown'),('AI_LIMIT_REACHED','failed')])
def test_jobs_failure_states_and_same_id_never_dispatch_again(actor,system,code,status):
    generator=system[1]; generator.error=ServiceError(code)
    body={'request_id':rid(),'theme':'offline','room_count':1,'difficulty':'easy'}
    first=actor.post('/level-generations',body,headers={'X-AI-Api-Key':CANARY}); assert first.status_code==202
    jid=first.json()['data']['job']['job_id']
    job=actor.get('/level-generations/'+jid).json()['data']['job']; assert job['status']==status and job['level_id'] is None
    same=actor.post('/level-generations',body,headers={'X-AI-Api-Key':'SYNTHETIC-DIFFERENT-KEY'})
    assert same.status_code==200 and same.json()['data']['job']['job_id']==jid
    assert len(generator.calls)==1
    assert_error(actor.post('/level-generations',{**body,'theme':'changed'},headers={'X-AI-Api-Key':CANARY}),409,'REQUEST_ID_CONFLICT')

def test_pending_generating_validating_restart_no_resend(actor,system):
    db=system[0].state.v5_database; uid=actor.auth['user']['user_id']; identifiers=[]
    for phase in ['pending','generating','validating']:
        request=GenerationRequest(request_id=rid(),theme='restart',room_count=1,difficulty='easy')
        status,item,_=db.reserve_job(uid,request); assert status==202
        identifiers.append(item['job_id']); db.job_phase(item['job_id'],phase)
        # Permit preparing isolated rows without claiming real simultaneous dispatch.
        if phase!='validating': db.job_phase(item['job_id'],'failed')
    for jid,phase in zip(identifiers,['pending','generating','validating']): db.job_phase(jid,phase)
    reopened=V5Database(db.path)
    for jid,status in zip(identifiers,['failed','unknown','failed']):
        job=reopened.jobs(uid,jid); assert job['status']==status and job['error_code']=='PROCESS_RESTARTED'
    assert system[1].calls==[]

def test_concurrent_jobs_per_user_global_and_replay(system):
    app,_=system; a=Actor(app).authenticate('qa_alpha'); b=Actor(app).authenticate('qa_beta'); c=Actor(app).authenticate('qa_gamma')
    release=threading.Event(); starts=threading.Condition(); count=0
    class Blocking:
        async def generate(self,**kw):
            nonlocal count
            with starts: count+=1; starts.notify_all()
            assert await asyncio.to_thread(release.wait,10),'QA rendezvous timed out'
            return make_fixture(1,'easy')
    app.state.generation_service=Blocking()
    body={'request_id':rid(),'theme':'concurrency','room_count':1,'difficulty':'easy'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1=pool.submit(a.post,'/level-generations',body,headers={'X-AI-Api-Key':CANARY})
        try:
            with starts: assert starts.wait_for(lambda:count==1,timeout=5)
            assert a.post('/level-generations',body,headers={'X-AI-Api-Key':CANARY}).status_code==200
            assert_error(a.post('/level-generations',{**body,'request_id':rid()},headers={'X-AI-Api-Key':CANARY}),429,'GENERATION_LIMIT_REACHED')
            f2=pool.submit(b.post,'/level-generations',{**body,'request_id':rid()},headers={'X-AI-Api-Key':CANARY})
            with starts: assert starts.wait_for(lambda:count==2,timeout=5)
            assert_error(c.post('/level-generations',{**body,'request_id':rid()},headers={'X-AI-Api-Key':CANARY}),429,'GENERATION_LIMIT_REACHED')
        finally: release.set()
        assert f1.result(timeout=10).status_code==202 and f2.result(timeout=10).status_code==202
    assert count==2 and c.get('/level-generations').json()['data']['jobs']==[]

def test_generation_ten_minute_and_day_limits(actor,system):
    db=system[0].state.v5_database; uid=actor.auth['user']['user_id']
    for _ in range(3): actor.generate()
    body={'request_id':rid(),'theme':'limited','room_count':1,'difficulty':'easy'}
    assert_error(actor.post('/level-generations',body,headers={'X-AI-Api-Key':CANARY}),429,'GENERATION_LIMIT_REACHED')
    # Retain today's records outside 10m; then create the remainder by the same reservation API.
    with db.transaction() as c: c.execute('UPDATE level_generations SET created_at=?',(time.time()-601,))
    for _ in range(7):
        status,item,_=db.reserve_job(uid,GenerationRequest(**{**body,'request_id':rid()})); assert status==202
        db.job_phase(item['job_id'],'failed')
        with db.transaction() as c: c.execute('UPDATE level_generations SET created_at=? WHERE job_id=?',(time.time()-601,item['job_id']))
    assert_error(actor.post('/level-generations',{**body,'request_id':rid()},headers={'X-AI-Api-Key':CANARY}),429,'GENERATION_LIMIT_REACHED')

def test_generation_finished_after_identity_switch_stays_with_original_owner(actor,system):
    app,_=system; b=Actor(app).authenticate('qa_beta'); db=app.state.v5_database
    old_token=actor.client.cookies.get('campus_v5_session')
    class Switched:
        async def generate(self,**kwargs):
            # Synthetic identity change while the injected generator is in flight.
            db.rotate(b.auth['user']['user_id'],old_token)
            return make_fixture(1,'easy')
    app.state.generation_service=Switched()
    response=actor.post('/level-generations',{'request_id':rid(),'theme':'late original owner','room_count':1,'difficulty':'easy'},headers={'X-AI-Api-Key':CANARY})
    assert response.status_code==202
    jid=response.json()['data']['job']['job_id']
    assert_error(actor.get('/level-generations/'+jid),401,'AUTH_REQUIRED')
    assert_error(b.get('/level-generations/'+jid),404,'NOT_FOUND')
    assert b.get('/levels').json()['data']['levels']==[]
    original=Actor(app).authenticate('qa_alpha',False)
    job=original.get('/level-generations/'+jid).json()['data']['job']
    assert job['status']=='ready'
    assert original.session('generated',job['level_id'])['mode']=='generated'
