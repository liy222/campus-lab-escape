"""Backend Owner development probe; all provider replies are offline fakes."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from backend.app.ai.companion import build_companion_context,validate_companion_reply,looks_like_solution,POLICY_REPLY,_normalized,is_solution_check
from backend.app.ai.hints import available_topics,bounded_render,_next_step
from backend.app.ai.provider import ProviderResult
from backend.app.ai.runtime import Runtime,resolve_turn_mode
from backend.app.ai.types import Version,TurnResult
from backend.app.domain import graybox_rules as rules
from backend.app.storage.sqlite import Store
from backend.app.storage.ai import encoded
OUT=Path(__file__).parent
records=[]
trace=json.loads((ROOT/'evidence/documentation/gameplay-walkthrough-20261018/verification.json').read_text(encoding='utf-8'))['route_steps']
old=types.ModuleType('backend.app.ai._owner_baseline_hints');old.__package__='backend.app.ai'
source=subprocess.check_output(['git','-c','safe.directory=D:/深度能力','show','HEAD:backend/app/ai/hints.py'],text=True,encoding='utf-8')
exec(compile(source,'HEAD:hints.py','exec'),old.__dict__)
state=rules.initial_state();baseline_states=0
for index in range(len(trace)+1):
    if index:
        e=trace[index-1];state,_=rules.apply_action(state,e['tool'],e['arguments'])
    visible=rules.visible_state('owner-preset-compat',state)
    assert available_topics(visible)==old.available_topics(visible)
    for level in (1,2,3):
        v=deepcopy(visible);v['statistics']['current_hint_level']=level
        for option in available_topics(v):
            assert bounded_render(v,option['clue_refs'],option['topic'])==old.bounded_render(v,option['clue_refs'],option['topic'])
    if visible['status']=='playing':
        goal=_next_step(visible,as_goal=True)
        assert goal is None or set(goal)=={'kind','focus','teaching_goal'}
    baseline_states+=1
assert state.status=='won'
records.append({'check':'preset-baseline-byte-text-semantics','actual_domain_states':baseline_states,'levels_each':3})
v=rules.visible_state('owner-guard',rules.initial_state())
for text in ('等电源接通后再观察。','终检完成后再继续。','电源接通了吗？'):
    validate_companion_reply(v,{'answer':text,'clue_refs':[]})
blocked=('电源已经接通。','终检已经完成。','我已经帮你打开柜门。','柜底凹槽里有一张旧合照。','样本编号是四十二。','4217','４ ２ １ ７','肆 贰 壹 柒','LAB-42','通风、冷却、照明、安全','▲ ● ■ ★','[1,2,3,0,1,2,3,0,1]')
for text in blocked:
    try:validate_companion_reply(v,{'answer':text,'clue_refs':[]})
    except ValueError:pass
    else:raise AssertionError(('guard failed',text))
try:validate_companion_reply(v,{'answer':'是的，你猜对了。','clue_refs':[]},'4217对吗？')
except ValueError:pass
else:raise AssertionError('Guess confirmation bypass')
assert _normalized('四十二')=='42'
assert is_solution_check('4217对吗？')
assert not is_solution_check('墙钟21:17是什么意思？')
assert not is_solution_check('我输入4217没反应怎么办？')
records.append({'check':'guard-controls','conditional_accepted':3,'unsafe_blocked':len(blocked)+1,'normalized_digits_correct':True})

class FakeProvider:
    provider_name='mock';model_name='owner-offline-companion'
    def __init__(self):self.calls=[]
    async def complete(self,messages,tools,limits,**kwargs):
        context=json.loads(messages[1]['content']);self.calls.append(deepcopy(context))
        assert tools==[] and kwargs['tool_choice']=='none'
        assert limits.max_tokens<=600
        answer='先观察显微镜，看看当前还有什么可用操作。你已经仔细看过它了吗？' if '显微镜' in context['question'] else '可以先看看实验记录。你最想确认它提到了什么？'
        return ProviderResult(json.dumps({'answer':answer,'clue_refs':[]},ensure_ascii=False),(),{'prompt_tokens':7,'completion_tokens':9},'mock',self.model_name,self.model_name,'stop')

async def store_checks():
    with tempfile.TemporaryDirectory(prefix='companion-owner-') as directory:
        store=Store(Path(directory)/'owner.sqlite',rules=rules)
        status,created=store.create({});assert status==201
        sid=created['data']['session_id'];token=created['data']['token']
        def current():return store.read(sid,token)[1]['data']['visible_state']
        def request(question):
            v=current();return {'request_id':uuid4().hex,'revision':v['revision'],'generation':v['generation'],'message':question,'hint_level':3}
        provider=FakeProvider();runtime=Runtime(provider)
        async def ask(question):
            before=current();req=request(question)
            start,cb=store.begin_ai(sid,token,req,behavior_mode='companion')
            assert start.mode=='companion'
            assert not store.ai_read(sid,start.turn_id,Version.from_state(start.visible_state),'inspect',{'object_id':'r1_record'}).ok
            result=await runtime.run(start,cb)
            assert result.data['stop_reason'] is None,result.data
            result=replace(result,trace=result.trace+({'kind':'answer','answer':'REJECTED_TRACE_SENTINEL'},{'kind':'provider_result','answer':'REJECTED_TRACE_SENTINEL','observation':'REJECTED_TRACE_SENTINEL','provider':'mock'}))
            code,body=store.finish_ai(sid,start.turn_id,result)
            assert code==200 and body['data']['stop_reason'] is None,body
            assert body['data']['answer']==result.data['answer']
            after=current();assert after['statistics']['hint_count']==before['statistics']['hint_count']+1
            assert after['statistics']['current_hint_level']==before['statistics']['current_hint_level']==1
            count=len(provider.calls)
            code,replay=store.begin_ai(sid,token,req,behavior_mode='companion')
            assert code==200 and replay['event_id']==body['event_id'] and current()==after
            assert len(provider.calls)==count
            code,conflict=store.begin_ai(sid,token,req,behavior_mode='preset')
            assert code==409 and conflict['error']['code']=='REQUEST_ID_CONFLICT'
            with store.transaction() as connection:
                row=connection.execute('SELECT trace_json,behavior_mode FROM ai_turns WHERE turn_id=?',(start.turn_id,)).fetchone()
                assert row['behavior_mode']=='companion' and 'REJECTED_TRACE_SENTINEL' not in row['trace_json']
            return body['data']['answer']
        first=await ask('我该先观察哪里？')
        second=await ask('显微镜怎么用？')
        assert first!=second
        third=await ask('我先看实验记录可以吗？')
        before=current();oldcalls=len(provider.calls)
        for _ in range(13):
            code,local=store.begin_ai(sid,token,request('4217对吗？'),behavior_mode='companion')
            assert code==200 and local['data']['answer']==POLICY_REPLY
            assert local['data']['usage']['model_calls']==0 and local['data']['usage']['provider']=='unavailable'
            assert local['data']['usage']['model'] is None and current()==before
        assert len(provider.calls)==oldcalls
        with store.transaction() as connection:
            private=store.authenticate(connection,sid,token)
            history=store.companion_history(connection,sid,private)
        assert len([e for e in history if e['kind']=='dialogue'])==3
        assert all('4217' not in json.dumps(e,ensure_ascii=False) for e in history)
        start,cb=store.begin_ai(sid,token,request('想讨论实验记录'),behavior_mode='companion')
        result=await runtime.run(start,cb)
        zero=replace(result,data={**result.data,'usage':{**result.data['usage'],'model_calls':0}})
        count=current()['statistics']['hint_count']
        code,body=store.finish_ai(sid,start.turn_id,zero)
        assert body['data']['status']=='stopped' and current()['statistics']['hint_count']==count
        # Preset durable mode ignores a fake deepseek usage label and free prose.
        req=request('fixed-preset');start,cb=store.begin_ai(sid,token,req,behavior_mode='preset')
        refs=available_topics(start.visible_state)[0]['clue_refs']
        fake=TurnResult({'answer':'UNTRUSTED_PRESET_PROSE','clue_refs':refs,'status':'no_suggestion','stop_reason':None,'usage':{'provider':'deepseek','model':None,'input_tokens':None,'output_tokens':None,'model_calls':1,'read_tool_calls':0}},None,(),Version.from_state(start.visible_state))
        code,body=store.finish_ai(sid,start.turn_id,fake)
        assert code==200, body.get('error')
        assert body['data']['answer']!='UNTRUSTED_PRESET_PROSE'
        # Historical completed receipt digest replay remains compatible.
        old_normalized={'operation':'ai_turn',**req}
        with store.transaction() as connection:
            connection.execute("UPDATE ai_turns SET behavior_mode='existing' WHERE turn_id=?",(start.turn_id,))
            connection.execute('UPDATE action_receipts SET request_hash=? WHERE session_id=? AND request_id=?',(hashlib.sha256(encoded(old_normalized).encode()).hexdigest(),sid,req['request_id']))
        code,replayed=store.begin_ai(sid,token,req,behavior_mode='companion')
        assert code==200 and replayed['event_id']==body['event_id']
        # Reserve then perform a legal action: final Store must stop the old reply.
        start,cb=store.begin_ai(sid,token,request('先看哪里'),behavior_mode='companion')
        result=await runtime.run(start,cb)
        vv=current();action={'request_id':uuid4().hex,'revision':vv['revision'],'generation':vv['generation'],'tool':'inspect','arguments':{'object_id':'r1_record'}}
        assert store.action(sid,token,action)[0]==200
        count=current()['statistics']['hint_count']
        code,body=store.finish_ai(sid,start.turn_id,result)
        assert body['data']['stop_reason']=='STALE_STATE' and current()['statistics']['hint_count']==count
        context=provider.calls[1]
        assert context['question']=='显微镜怎么用？'
        assert context['director'] and '教学' not in str(context['director']['focus'])
        assert all(not any(k in e for k in ('arguments','observation')) for e in context['recent_history'])
        assert '4217' not in json.dumps(context,ensure_ascii=False)
        assert len(json.dumps(context,ensure_ascii=False).encode())<=24576
        records.append({'check':'temporary-store','accepted_natural_discussions':3,'different_question_different_reply':True,'replay_once':True,'mode_conflict':True,'local_no_call_no_count_reminders':13,'last_three_successful_history_preserved':True,'zero_call_prose_rejected':True,'preset_result_mode_spoof_ignored':True,'old_receipt_digest_replayed':True,'manual_action_stale_stop':True,'trace_raw_text_removed':True,'actual_fake_provider_calls':len(provider.calls)})
asyncio.run(store_checks())

paths=['backend/app/ai/companion.py','backend/app/ai/hints.py','backend/app/ai/runtime.py','backend/app/ai/types.py','backend/app/storage/ai.py','backend/app/api/routes.py']
report={'recorded_at':datetime.now(timezone.utc).isoformat(),'operator':'Backend/AI Owner development only','command':[sys.executable,'-B','-X','utf8','evidence/integration/ai-companion/backend/probe.py'],'exit_code':0,'checks':records,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'real_provider_calls':0,'paid_calls':0,'HTTP_requests':0,'limitations':['This is Owner development evidence, not independent QA.','Fake provider calls prove plumbing/context/count boundaries, not real natural reply quality.','The local natural-language guard is heuristic; no perfect semantic anti-spoiler/factuality claim.','No browser/build/full legacy suite or actual paid network call.','Old-receipt compatibility branch used a deliberately seeded historical digest/mode in a temporary DB, not a user database.']}
(OUT/'probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exit_code':0,'checks':len(records),'preset_states':baseline_states,'paid_calls':0,'real_provider_calls':0},ensure_ascii=False))
