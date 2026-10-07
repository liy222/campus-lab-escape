"""Independent v3.4 public hint/statistics/settlement acceptance; no paid calls."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from tests.api.test_r1 import HTTPFixture, sanitize
from tests.api import test_upgrade_v33 as manual33
from tests.api.test_m3 import reply, call

CHECKS34=[]


def core(state):
    return {key:copy.deepcopy(value) for key,value in state.items() if key not in {'statistics','settlement','revision','generation','save'}}


def stable(state):
    value=copy.deepcopy(state)
    value.get('statistics',{}).pop('elapsed_seconds',None)
    return value


def game(state):
    value=stable(state)
    for key in ('revision','generation','save'):value.pop(key,None)
    return value


def public_options(messages):
    result=[]
    def visit(value):
        if isinstance(value,dict):
            if isinstance(value.get('topic'),str) and isinstance(value.get('clue_refs'),list):result.append(value)
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    for message in messages:
        try:visit(json.loads(message.get('content') or ''))
        except (ValueError,TypeError):pass
    return result


class CapturedHintProvider:
    provider_name,model_name='mock','qa-hint-selector'
    def __init__(self,mutate=None,error=None):self.contexts=[];self.tools=[];self.kwargs=[];self.mutate=mutate;self.error=error
    async def complete(self,messages,tools,limits,**kwargs):
        self.contexts.append(copy.deepcopy(messages));self.tools.append(copy.deepcopy(tools));self.kwargs.append(kwargs)
        if self.error:raise self.error
        options=public_options(messages)
        assert options,'Public provider context must expose known selectable topic/ref pairs'
        selected={'topic':options[0]['topic'],'clue_refs':options[0]['clue_refs']}
        if self.mutate:
            selected=self.mutate(selected)
            if not isinstance(selected,dict):return selected
        return reply(json.dumps(selected,ensure_ascii=False))


class UpgradeV34Acceptance(HTTPFixture):
    # Reuse helpers through the module; do not inherit/recollect its 9 test methods.
    route32=manual33.UpgradeV33Acceptance.route32
    version=manual33.UpgradeV33Acceptance.version
    control=manual33.UpgradeV33Acceptance.control
    assert_real_progress=manual33.UpgradeV33Acceptance.assert_real_progress
    circuit_ready_to_edit=manual33.UpgradeV33Acceptance.circuit_ready_to_edit
    rotate_to=manual33.UpgradeV33Acceptance.rotate_to
    finish_circuit=manual33.UpgradeV33Acceptance.finish_circuit

    def setUp(self):
        super().setUp();self.client.__exit__(None,None,None)
        self.clock=datetime(2026,10,7,tzinfo=timezone.utc)
        self.clock_patch=patch('backend.app.domain.graybox_rules.utc_now',side_effect=lambda:self.clock.isoformat().replace('+00:00','Z'));self.clock_patch.start()
        from backend.app.main import create_app
        self.db=Path(self.temp.name)/'v34.sqlite'
        self.client=TestClient(create_app(self.db,gameplay_version='v3.4'),raise_server_exceptions=False);self.client.__enter__();self.session=self.create()
        self.network=patch('httpx.AsyncClient.send',side_effect=AssertionError('Paid/model network forbidden in v3.4 QA'));self.network.start()

    def tearDown(self):
        self.network.stop();self.clock_patch.stop();super().tearDown()

    def reopen(self):
        self.client.__exit__(None,None,None)
        from backend.app.main import create_app
        self.client=TestClient(create_app(self.db,gameplay_version='v3.4'),raise_server_exceptions=False);self.client.__enter__()

    def exchange(self,method,path,**kwargs):
        status,body=super().exchange(method,path,**kwargs)
        if method=='POST' and path!='/api/sessions':
            state=body.get('data',{}).get('visible_state') if body.get('ok') else body.get('visible_state')
            data=body.get('data',{})
            if state and (not body.get('ok') or path.endswith(('/save','/restore','/reset','/turns')) or state['statistics']!=getattr(self,'_last_stats',None)):
                CHECKS34.append({'test':self._testMethodName,'operation':(kwargs.get('json') or {}).get('tool') or path.rsplit('/',1)[-1],'http_status':status,'error':body.get('error',{}).get('code'),'room':state['room']['room_id'],'statistics':state['statistics'],'settlement':state['settlement'],'ai_status':data.get('status'),'stop_reason':data.get('stop_reason')})
                self._last_stats=state['statistics']
        return status,body

    def reject_unchanged(self,tool,args,code,status=409,request=None,headers=None):
        before=self.state();actual,body=self.exchange('POST',f"/api/sessions/{self.session['session_id']}/actions",headers=headers or self.headers(),json=request or self.request(tool,args),definition='action_response')
        self.assertEqual(actual,status);self.assertEqual(body['error']['code'],code);self.assertEqual(stable(self.state()),stable(before));return body

    def meaningful(self,tool,args,code):
        before=self.state();request=self.request(tool,args)
        status,body=self.post(request);self.assertEqual(status,409);self.assertEqual(body['error']['code'],code)
        after=self.state();self.assertEqual(core(after),core(before));self.assertEqual(after['generation'],before['generation'])
        self.assertEqual(after['revision'],before['revision']+1);self.assertEqual(after['statistics']['mistake_count'],before['statistics']['mistake_count']+1)
        for key in ('started_at','finished_at','hint_count','current_hint_level'):self.assertEqual(after['statistics'][key],before['statistics'][key])
        status2,body2=self.post(request);self.assertEqual(status2,409);self.assertEqual(body2['event_id'],body['event_id']);self.assertEqual(stable(self.state()),stable(after))
        CHECKS34.append({'test':self._testMethodName,'meaningful_error':tool,'error':code,'counted_once':True,'progress_inventory_unchanged':True});return after

    def install(self,provider):
        from backend.app.ai.runtime import Runtime
        self.client.app.state.ai_runtime=Runtime(provider);return provider

    def ask(self,level=1,message='只依据已发现事实给方向',request=None,expected=200,headers=None):
        payload=request or {**self.version(),'message':message,'hint_level':level}
        status,body=self.exchange('POST',f"/api/sessions/{self.session['session_id']}/ai/turns",headers=headers or self.headers(),json=payload,definition='ai_turn_response')
        self.assertEqual(status,expected,sanitize(body.get('error',{})));return body.get('data',body),payload

    def accepted_hint(self,level=1,message='根据已发现事实提示'):
        before=self.state();provider=self.install(CapturedHintProvider());data,request=self.ask(level,message)
        self.assertEqual(data['status'],'no_suggestion');self.assertIsNone(data['proposal']);self.assertTrue(data['answer'].strip())
        after=self.state();self.assertEqual(core(after),core(before));self.assertEqual(after['statistics']['hint_count'],before['statistics']['hint_count']+1);self.assertEqual(after['statistics']['current_hint_level'],level);self.assertEqual(after['statistics']['mistake_count'],before['statistics']['mistake_count'])
        self.assertEqual(len(provider.contexts),1);self.assertEqual(provider.tools,[[]]);self.assertEqual(provider.kwargs[0]['tool_choice'],'none')
        self.assertEqual(data['usage']['read_tool_calls'],0)
        return data,provider,request

    def win_route(self,hidden=0):
        self.route32(end=14)
        if hidden>=1:self.action('inspect',{'object_id':'r1_photo'})
        self.route32(14,22);self.finish_circuit();self.action(*manual33.ROUTE32[23])
        if hidden>=2:self.action('inspect',{'object_id':'r2_service_label'})
        self.route32(24,42);derived=manual33.derive_public_sequence(self.state())
        self.action('submit_sequence',{'target_id':'r3_panel','device_ids':derived});self.route32(43)
        self.assertEqual(self.state()['status'],'won');return self.state()

    def test_initial_fixed_statistics_no_future_boards_and_no_hint_paid_request(self):
        before=self.state();stats=before['statistics']
        self.assertEqual((before['schema_version'],before['level_version']),('1.4.0','3.4.0'))
        self.assertEqual((stats['clues_total'],stats['hidden_total'],stats['hint_count'],stats['mistake_count']),(10,2,0,0));self.assertIsNone(stats['finished_at']);self.assertIsNone(before['settlement']);self.assertNotIn('elapsed_seconds',stats)
        provider=self.install(CapturedHintProvider());data,_=self.ask(3)
        self.assertEqual(data['status'],'no_suggestion');self.assertIsNone(data['proposal']);self.assertEqual(data['usage']['model_calls'],0);self.assertEqual(provider.contexts,[]);self.assertEqual(stable(self.state()),stable(before))
        self.clock+=timedelta(seconds=90);self.assertEqual(self.state(),before)

    def test_three_levels_only_known_context_no_auto_inspect_no_private_full_solution(self):
        self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'});known=self.state();answers=[]
        for level in (1,2,3):
            data,provider,_=self.accepted_hint(level,message='玩家自己输入4217，请不要扩展未知事实')
            answers.append(data['answer']);payload=json.dumps(provider.contexts,ensure_ascii=False)
            self.assertNotIn('4217',payload);self.assertNotIn('21:17',payload)
            self.assertEqual(set(public_options(provider.contexts[0])[0]['clue_refs']),{'r1_clock_clue','r1_record_clue'})
            for unknown in ('r1_sample_clue','r2_indices_clue','r3_legend_clue','LAB SAMPLE 42','4792'):
                self.assertNotIn(unknown,payload);self.assertNotIn(unknown,data['answer'])
            self.assertNotIn('4217',data['answer']);self.assertEqual(set(data['clue_refs']),{c['clue_id'] for c in known['clues']})
            self.assertEqual(data['visible_state']['observed_object_ids'],known['observed_object_ids'])
        self.assertEqual(len(set(answers)),3);self.assertEqual(self.state()['statistics']['hint_count'],3)

    def test_hint_replay_stale_invalid_level_settings_failures_do_not_increment(self):
        self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'});data,provider,request=self.accepted_hint(2);after=self.state()
        repeated,_=self.ask(request=request);self.assertEqual(len(provider.contexts),1);self.assertEqual(repeated['answer'],data['answer']);self.assertEqual(stable(self.state()),stable(after))
        for level in (0,4,True,'2'):
            with self.subTest(level=level):self.ask(request={**self.version(),'message':'提示','hint_level':level},expected=422);self.assertEqual(stable(self.state()),stable(after))
        self.ask(headers={**self.headers(),'X-AI-Provider':'unknown'},expected=422);self.assertEqual(stable(self.state()),stable(after))
        stale={**self.version(),'message':'提示','hint_level':2};self.action('inspect',{'object_id':'r1_plaque'});before=self.state()
        self.ask(request=stale,expected=409);self.assertEqual(stable(self.state()),stable(before))
        from backend.app.ai.provider import ProviderError
        failed=self.install(CapturedHintProvider(error=ProviderError('MODEL_UNAVAILABLE')));result,_=self.ask(2);self.assertEqual(result['status'],'stopped');self.assertEqual(stable(self.state()),stable(before));self.assertEqual(len(failed.contexts),1)

    def test_runtime_selection_injection_unknown_refs_free_answer_and_autoread_stop(self):
        self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'});self.accepted_hint(3);before=self.state();sentinel='QA_PRIVATE_FUTURE_SENTINEL'
        cases={
            'unknown-topic':lambda selected:{**selected,'topic':'qa_future_topic'},
            'unknown-ref':lambda selected:{**selected,'clue_refs':['r3_legend_clue']},
            'freeanswer':lambda selected:{**selected,'answer':sentinel+' 4792'},
            'toolcall':lambda selected:reply(calls=[call('inspect',{'object_id':'r2_monitor'})]),
        }
        for name,mutate in cases.items():
            with self.subTest(case=name):
                provider=self.install(CapturedHintProvider(mutate=mutate));data,_=self.ask(3)
                self.assertEqual(data['status'],'stopped');self.assertIsNone(data['proposal']);self.assertNotIn(sentinel,data['answer']);self.assertEqual(stable(self.state()),stable(before));self.assertEqual(len(provider.contexts),1)
                CHECKS34.append({'test':self._testMethodName,'injected_case':name,'stopped':data['stop_reason'],'count_unchanged':True})

    def test_store_finalizer_rechecks_fake_runtime_answer_refs_proposal_and_stale(self):
        from backend.app.ai.types import TurnResult,Version,ProposalCandidate
        self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'});baseline,provider,_=self.accepted_hint(2);accepted=self.state()
        valid_option=public_options(provider.contexts[0])[0];sentinel='QA_FAKE_RUNTIME_FUTURE_SENTINEL'
        mutations=['freeanswer','future-ref','proposal','stale','stopped-prose','autoread']
        for case in mutations:
            with self.subTest(case=case):
                before=self.state()
                class FakeRuntime:
                    async def run(fake,start,callbacks):
                        payload={key:copy.deepcopy(value) for key,value in baseline.items() if key not in {'visible_state','proposal','turn_id','replayed'}}
                        payload['answer']=sentinel+' 4792';payload['clue_refs']=valid_option['clue_refs']
                        candidate=None;version=Version.from_state(start.visible_state)
                        if case=='future-ref':payload['clue_refs']=['r3_legend_clue']
                        if case=='stopped-prose':payload.update(status='stopped',stop_reason='MODEL_INVALID_OUTPUT')
                        if case=='autoread':
                            blocked=await callbacks.read_tool(version,'inspect',{'object_id':'r1_plaque'})
                            self.assertFalse(blocked.ok);self.assertEqual(blocked.error_code,'INVALID_TOOL')
                        if case=='proposal':candidate=ProposalCandidate('submit_code',{'target_id':'r1_cabinet','code':'4217'},tuple(valid_option['clue_refs']),sentinel)
                        if case=='stale':version=Version(version.revision+1,version.generation)
                        return TurnResult(payload,candidate,(),version)
                self.client.app.state.ai_runtime=FakeRuntime();data,_=self.ask(3)
                self.assertIsNone(data.get('proposal'));self.assertNotIn(sentinel,json.dumps(data,ensure_ascii=False));self.assertNotIn('4792',data.get('answer',''));self.assertEqual(core(self.state()),core(before))
                if data.get('status')=='stopped':self.assertEqual(self.state()['statistics']['hint_count'],before['statistics']['hint_count'])
                else:self.assertEqual(data['status'],'no_suggestion');self.assertEqual(self.state()['statistics']['hint_count'],before['statistics']['hint_count']+1)
                CHECKS34.append({'test':self._testMethodName,'fake_runtime_case':case,'status':data.get('status'),'private_answer_never_returned':True})

    def test_meaningful_numeric_login_circuit_sequence_wrong_item_count_once_only(self):
        self.route32(end=6)
        self.meaningful('use_item',{'item_id':'sample_slide','target_id':'r1_clock'},'PRECONDITION_FAILED')
        self.route32(6,9);self.meaningful('submit_code',{'target_id':'r1_cabinet','code':'0000'},'WRONG_CODE')
        self.route32(9,22);self.meaningful('submit_circuit',{'target_id':'r2_powerbox'},'WRONG_CODE');self.finish_circuit();self.route32(23,27)
        self.meaningful('submit_login',{'target_id':'r2_monitor','username':'LAB-42','password':'0000'},'WRONG_CODE');self.route32(27,42)
        sequence=manual33.derive_public_sequence(self.state());wrong=sequence[1:]+sequence[:1]
        self.meaningful('submit_sequence',{'target_id':'r3_panel','device_ids':wrong},'WRONG_CODE')
        self.assertEqual(self.state()['statistics']['mistake_count'],5)

    def test_rotations_reads_bad_schema_auth_stale_unseen_targets_do_not_count(self):
        self.route32(end=6);before=self.state()
        self.reject_unchanged('use_item',{'item_id':'sample_slide','target_id':'r2_monitor'},'NOT_VISIBLE')
        self.reject_unchanged('submit_code',{'target_id':'r1_cabinet','code':False},'BAD_ARGUMENT',422)
        self.reject_unchanged('inspect',{'object_id':'r1_clock'},'FORBIDDEN_SESSION',403,headers={'X-Session-Token':'QA_NOT_AN_AUTH_TOKEN'})
        stale=self.request('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_door'})
        self.reject_unchanged('inspect',{'object_id':'r1_clock'},'STALE_STATE',request=stale)
        self.route32(6,22);before=self.state();self.action('rotate_circuit',{'target_id':'r2_powerbox','module_id':'c00'});self.action('inspect',{'object_id':'r2_monitor'})
        self.assertEqual(self.state()['statistics']['mistake_count'],before['statistics']['mistake_count']);self.assertEqual(self.state()['statistics']['hint_count'],before['statistics']['hint_count'])

    def test_optional_story_objects_visibility_discoveries_total_ten_and_win_score(self):
        initial=self.state();self.assertNotIn('r1_photo',[o['object_id'] for o in initial['objects']]);self.reject_unchanged('inspect',{'object_id':'r1_photo'},'NOT_VISIBLE')
        won=self.win_route(hidden=2);stats=won['statistics'];score=won['settlement']
        self.assertEqual((stats['clues_found'],stats['clues_total'],stats['hidden_found'],stats['hidden_total']),(10,10,2,2))
        self.assertEqual(score['rating'],'S');self.assertEqual(score['hint_count'],0);self.assertEqual(score['mistake_count'],0)
        self.assertEqual({c['clue_id'] for c in won['clues']} & {'r1_photo_clue','r2_service_clue'},{'r1_photo_clue','r2_service_clue'})

    def test_server_UTC_offline_elapsed_reset_saved_run_restore_and_win_freeze(self):
        start=self.state()['statistics']['started_at'];self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'});self.accepted_hint(3)
        saved=self.control('save');self.clock+=timedelta(seconds=125);self.control('reset')
        reset=self.state();self.assertNotEqual(reset['statistics']['started_at'],start);self.assertEqual(reset['statistics']['hint_count'],0);self.assertIsNotNone(reset['save'])
        restored=self.control('restore');self.assertEqual(game(restored),game(saved));self.reopen();self.assertEqual(stable(self.state()),stable(restored))
        won=self.win_route();self.assertEqual(won['statistics']['started_at'],start);self.assertEqual(won['settlement']['elapsed_seconds'],125)
        finish=won['statistics']['finished_at'];self.assertTrue(start.endswith('Z') and finish.endswith('Z'));self.clock+=timedelta(seconds=600);self.reopen();self.assertEqual(self.state()['settlement'],won['settlement']);self.assertEqual(self.state()['statistics']['finished_at'],finish)
        CHECKS34.append({'test':self._testMethodName,'controlled_server_utc_seconds':125,'offline_elapsed_included':True,'win_elapsed_frozen_after_extra_seconds':600,'human_timing_claim':False})

    def test_all_S_A_B_C_ratings_are_settlement_only_without_exit_gate(self):
        for expected,hidden,hints in [('S',1,0),('A',0,0),('B',0,4),('C',0,9)]:
            with self.subTest(rating=expected):
                if expected!='S':self.control('reset')
                self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'})
                for _ in range(hints):self.accepted_hint(1)
                won=self.win_route(hidden=hidden);self.assertEqual(won['settlement']['rating'],expected);self.assertEqual(won['room']['room_id'],'EXIT');self.assertEqual(won['status'],'won')
                CHECKS34.append({'test':self._testMethodName,'rating':expected,'clues':won['settlement']['clues_found'],'hints':hints,'exit_not_gated':True})

    def test_new_statistics_survive_save_restore_reset_slot_and_cross_version_rejection(self):
        import sqlite3
        from contextlib import closing
        from tests.api.test_m2 import digest
        self.route32(end=9);self.meaningful('submit_code',{'target_id':'r1_cabinet','code':'0000'},'WRONG_CODE');self.accepted_hint(2);saved=self.control('save')
        self.clock+=timedelta(seconds=60);self.control('reset');self.assertEqual(self.state()['statistics']['mistake_count'],0)
        restored=self.control('restore');self.assertEqual(game(restored),game(saved));self.reopen();self.assertEqual(self.state(),restored)
        with closing(sqlite3.connect(self.db)) as db:raw=db.execute('SELECT snapshot_json FROM saves WHERE session_id=?',(self.session['session_id'],)).fetchone()[0]
        for schema,level in [('1.0.0','2.0.0'),('1.1.0','3.1.0'),('1.2.0','3.2.0'),('1.3.0','3.3.0')]:
            with self.subTest(version=level):
                damaged=json.loads(raw);damaged.update(schema_version=schema,level_version=level);damaged['checksum']=digest(damaged);encoded=json.dumps(damaged,ensure_ascii=False)
                with closing(sqlite3.connect(self.db)) as db:db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?',(encoded,self.session['session_id']));db.commit()
                before=self.state();self.control('restore',409,'SNAPSHOT_VERSION_MISMATCH');self.assertEqual(self.state(),before)
                with closing(sqlite3.connect(self.db)) as db:self.assertEqual(db.execute('SELECT snapshot_json FROM saves WHERE session_id=?',(self.session['session_id'],)).fetchone()[0],encoded)
    def test_hint_concurrent_duplicate_inflight_stale_generation_and_timeout_never_double_count(self):
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        import threading
        from backend.app.ai.runtime import Runtime,RuntimeLimits
        for scenario in ('accepted','manual-stale','restore-generation'):
            with self.subTest(scenario=scenario):
                if scenario!='accepted':self.clock+=timedelta(seconds=1);self.control('reset')
                self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'})
                before=self.state();entered=threading.Event();release=threading.Event()
                class Gated(CapturedHintProvider):
                    async def complete(provider,messages,tools,limits,**kwargs):
                        entered.set()
                        if not await asyncio.to_thread(release.wait,3):raise AssertionError('Owned synthetic gate not released')
                        return await super().complete(messages,tools,limits,**kwargs)
                provider=self.install(Gated());request={**self.version(),'message':'只选择已发现topic','hint_level':1}
                if scenario=='restore-generation':self.control('save')
                with ThreadPoolExecutor(1) as pool:
                    pending=pool.submit(self.ask,request=request)
                    try:
                        self.assertTrue(entered.wait(2),'Synthetic provider did not enter')
                        if scenario=='accepted':
                            duplicate,_=self.ask(request=request,expected=503)
                            self.assertEqual(duplicate['error']['code'],'MODEL_UNAVAILABLE');self.assertEqual(self.state()['statistics']['hint_count'],before['statistics']['hint_count'])
                        elif scenario=='manual-stale':self.action('inspect',{'object_id':'r1_plaque'})
                        else:self.control('restore')
                    finally:release.set()
                    data,_=pending.result(timeout=5)
                after=self.state();self.assertEqual(len(provider.contexts),1)
                if scenario=='accepted':
                    self.assertEqual(data['status'],'no_suggestion');self.assertEqual(after['statistics']['hint_count'],before['statistics']['hint_count']+1)
                    self.ask(request=request);self.assertEqual(len(provider.contexts),1);self.assertEqual(self.state(),after)
                else:
                    self.assertEqual(data['status'],'stopped');self.assertEqual(data['stop_reason'],'STALE_STATE');self.assertEqual(after['statistics']['hint_count'],before['statistics']['hint_count'])
                CHECKS34.append({'test':self._testMethodName,'inflight_case':scenario,'model_calls':len(provider.contexts),'hint_count_delta':after['statistics']['hint_count']-before['statistics']['hint_count']})
        class Slow(CapturedHintProvider):
            async def complete(provider,*args,**kwargs):
                await asyncio.sleep(.15)
                return await super().complete(*args,**kwargs)
        self.clock+=timedelta(seconds=1);self.control('reset');self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'})
        before=self.state();self.client.app.state.ai_runtime=Runtime(Slow(),RuntimeLimits(call_seconds=.03,total_seconds=.05))
        data,_=self.ask(1);self.assertEqual(data['status'],'stopped');self.assertEqual(data['stop_reason'],'MODEL_TIMEOUT');self.assertEqual(self.state()['statistics']['hint_count'],before['statistics']['hint_count']);self.assertEqual(core(self.state()),core(before))
        CHECKS34.append({'test':self._testMethodName,'timeout_limits_seconds':{'call':.03,'total':.05},'hint_count_unchanged':True,'production_timeout_claim':False})
