"""Independent append/list/selected-restore acceptance; owned SQLite and mock only."""
import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from unittest.mock import patch

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from tests.api.test_r1 import HTTPFixture, SECRETS
from tests.api import test_r1 as base
from tests.api import test_upgrade_v33 as minis
from tests.api import test_upgrade_v34 as graybox
from tests.api.test_m2 import digest

CHECKS_SAVES = []
SLOT_KEYS = {'save_id','name','saved_at','schema_version','level_version','source_revision',
             'source_generation','room_id','status','clues_found','kind'}


def game(state):
    return {key:value for key,value in state.items() if key not in {'revision','generation','save'}}


class MultipleSavesAcceptance(HTTPFixture):
    # Module references and helper assignment avoid collecting any old test twice.
    route32 = minis.UpgradeV33Acceptance.route32
    version = minis.UpgradeV33Acceptance.version
    control = minis.UpgradeV33Acceptance.control
    finish_circuit = minis.UpgradeV33Acceptance.finish_circuit
    rotate_to = minis.UpgradeV33Acceptance.rotate_to
    win_route = graybox.UpgradeV34Acceptance.win_route
    install = graybox.UpgradeV34Acceptance.install
    ask = graybox.UpgradeV34Acceptance.ask
    accepted_hint = graybox.UpgradeV34Acceptance.accepted_hint

    def setUp(self):
        super().setUp();self.client.__exit__(None,None,None)
        self.clock = datetime(2026,10,7,tzinfo=timezone.utc)
        self.clock_patch = patch('backend.app.domain.graybox_rules.utc_now',side_effect=lambda:self.clock.isoformat().replace('+00:00','Z'))
        self.clock_patch.start()
        self.db = Path(self.temp.name)/'multiple-saves.sqlite'
        self.reopen(first=True);self.session=self.create()
        self.network = patch('httpx.AsyncClient.send',side_effect=AssertionError('Paid network forbidden in multiple-saves QA'))
        self.network.start()

    def tearDown(self):
        self.network.stop();self.clock_patch.stop();super().tearDown()

    def reopen(self,first=False):
        if not first:self.client.__exit__(None,None,None)
        from backend.app.main import create_app
        self.client=TestClient(create_app(self.db,gameplay_version='v3.4'),raise_server_exceptions=False)
        self.client.__enter__()

    def archive_http(self,method,suffix='',payload=None,expected=200,code=None,session=None,headers=None):
        owner=session or self.session
        response=self.client.request(method,f"/api/sessions/{owner['session_id']}/saves{suffix}",
            headers=headers if headers is not None else self.headers(owner),**({'json':payload} if payload is not None else {}))
        body=response.json()
        self.assertEqual(response.status_code,expected,body.get('error',{}))
        self.assertTrue(all(secret not in json.dumps(body) for secret in SECRETS),'Session capability leaked')
        self.assertEqual(set(body),{'ok','event_id','data'} if body.get('ok') else {'ok','event_id','error','visible_state'})
        definition=('list_saves_response' if method=='GET' else 'save_slot_response') if body.get('ok') else 'error_response'
        validator=Draft202012Validator({'$ref':f'#/$defs/{definition}','$defs':base.SCHEMA['$defs']},format_checker=FormatChecker())
        self.assertFalse(list(validator.iter_errors(body)),'New save response violates generated public schema')
        if code:self.assertEqual(body['error']['code'],code)
        if body.get('ok'):
            data=body['data'];self.assertEqual(set(data),{'slots','visible_state'} if method=='GET' else {'request_id','replayed','slot','visible_state','message'})
            for slot in data.get('slots',[data.get('slot')]):
                self.assertIsInstance(slot,dict);self.assertEqual(set(slot),SLOT_KEYS)
                self.assertIn(slot['kind'],{'archive','legacy'});self.assertLessEqual(len(slot['name']),40)
                self.assertTrue(slot['saved_at'].endswith('Z'))
        state=body.get('data',{}).get('visible_state') if body.get('ok') else body.get('visible_state')
        CHECKS_SAVES.append({'test':self._testMethodName,'operation':method+(' list/create' if not suffix else ' selected-restore'),
            'http_status':response.status_code,'error':body.get('error',{}).get('code'),
            'slot_count':len(body.get('data',{}).get('slots',[])) if method=='GET' and body.get('ok') else None,
            'replayed':body.get('data',{}).get('replayed'),'room':state['room']['room_id'] if state else None,
            'revision':state.get('revision') if state else None,'statistics':state.get('statistics') if state else None,
            'settlement':state.get('settlement') if state else None})
        return body

    def slots(self,session=None):
        return self.archive_http('GET',session=session)['data']['slots']

    def append(self,name=None,request=None,expected=201,code=None):
        payload=copy.deepcopy(request or self.version())
        if name is not None:payload['name']=name
        return self.archive_http('POST',payload=payload,expected=expected,code=code)

    def restore_archive(self,save_id,request=None,expected=200,code=None):
        return self.archive_http('POST','/'+save_id+'/restore',request or self.version(),expected,code)

    def assert_restored(self,before,saved,after):
        self.assertEqual(game(after),game(saved),'Selected restore changed saved gameplay/statistics')
        self.assertEqual(after['revision'],before['revision']+1)
        self.assertNotEqual(after['generation'],before['generation'])

    def rows(self):
        with closing(sqlite3.connect(self.db)) as db:
            return db.execute('SELECT save_id,session_id,snapshot_json,metadata_json FROM save_slots ORDER BY save_id').fetchall()

    def test_append_immutable_three_moments_restore_stats_reset_and_reopen(self):
        self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'});self.accepted_hint(2)
        early=self.state();first=self.append('开始时刻')['data']['slot'];self.assertEqual(self.state(),early)
        self.route32(end=22);self.action('rotate_circuit',{'target_id':'r2_powerbox','module_id':'c00'})
        mid=self.state();second=self.append('线路中期')['data']['slot'];self.assertEqual(self.state(),mid)
        self.clock+=timedelta(seconds=125);self.finish_circuit();self.route32(23,42)
        self.action('submit_sequence',{'target_id':'r3_panel','device_ids':minis.derive_public_sequence(self.state())});self.route32(43)
        won=self.state();self.assertEqual(won['settlement']['elapsed_seconds'],125)
        third=self.append('通关时刻')['data']['slot'];frozen=self.rows()
        self.assertEqual({s['save_id'] for s in self.slots()},{first['save_id'],second['save_id'],third['save_id']})
        self.assertEqual(self.state(),won);self.assertIsNone(won['save'])
        self.clock+=timedelta(seconds=600);self.control('reset');self.assertEqual(len(self.slots()),3)
        for slot,saved in [(first,early),(second,mid),(third,won)]:
            with self.subTest(moment=slot['name']):
                before=self.state();result=self.restore_archive(slot['save_id']);after=result['data']['visible_state']
                self.assert_restored(before,saved,after);self.reopen();self.assertEqual(self.state(),after)
                self.assertEqual(self.rows(),frozen)
        self.assertEqual(self.state()['settlement'],won['settlement'])

    def test_same_timestamp_name_revision_append_is_distinct_but_concurrent_request_once(self):
        from unittest.mock import patch as mockpatch
        with mockpatch('backend.app.storage.sqlite.utc_now',return_value='2026-10-07T00:00:00Z'):
            request={**self.version(),'name':'同一时刻'}
            barrier=threading.Barrier(2)
            def send(_):barrier.wait(timeout=4);return self.append(request=request)
            with ThreadPoolExecutor(2) as pool:results=list(pool.map(send,range(2)))
            self.assertEqual(sorted(r['data']['replayed'] for r in results),[False,True])
            self.assertEqual(results[0]['data']['slot'],results[1]['data']['slot']);self.assertEqual(len(self.slots()),1)
            different=self.append('同一时刻')['data']['slot'];self.assertNotEqual(different['save_id'],results[0]['data']['slot']['save_id'])
            self.assertEqual([s['save_id'] for s in self.slots()],[different['save_id'],results[0]['data']['slot']['save_id']])
        state=self.state();rows=self.rows();self.append(request={**request,'name':'替换'},expected=409,code='REQUEST_ID_CONFLICT')
        self.assertEqual(self.state(),state);self.assertEqual(self.rows(),rows)

    def test_names_default_unicode_boundary_no_private_metadata_and_error_receipt_replay(self):
        before=self.state()
        for name in (None,'','界'*40,'<img src=x onerror=QA_INJECTION>'):
            with self.subTest(name_type='default' if not name else 'named'):
                slot=self.append(name)['data']['slot'];self.assertTrue(slot['name'])
                if name:self.assertEqual(slot['name'],name)
                self.assertEqual(self.state(),before)
        self.assertEqual(len(self.slots()),4)
        request=self.version();first=self.restore_archive('missing_archive',request,404,'SAVE_NOT_FOUND')
        rows=self.rows();self.control('reset');current=self.state()
        replay=self.restore_archive('missing_archive',request,404,'SAVE_NOT_FOUND')
        self.assertEqual(first['event_id'],replay['event_id']);self.assertEqual(self.state(),current);self.assertEqual(self.rows(),rows)
        self.restore_archive('bad.identifier',expected=422,code='BAD_ARGUMENT')
        self.assertEqual(self.state(),current)

    def test_completed_new_restore_replay_before_generation_but_old_control_generation_first(self):
        first=self.append('早期')['data']['slot'];self.action('inspect',{'object_id':'r1_record'})
        second=self.append('另一时刻')['data']['slot'];request=self.version();one=self.restore_archive(first['save_id'],request)
        after=self.state();replay=self.restore_archive(first['save_id'],request)
        self.assertTrue(replay['data']['replayed']);self.assertEqual(one['event_id'],replay['event_id']);self.assertEqual(self.state(),after)
        self.action('inspect',{'object_id':'r1_clock'});current=self.state()
        replay=self.restore_archive(first['save_id'],request);self.assertTrue(replay['data']['replayed'])
        self.assertEqual(replay['data']['visible_state'],current);self.assertEqual(self.state(),current)
        self.restore_archive(second['save_id'],request,409,'REQUEST_ID_CONFLICT');self.append(request=request,expected=409,code='REQUEST_ID_CONFLICT')
        old_request=self.version();self.exchange('POST',f"/api/sessions/{self.session['session_id']}/save",headers=self.headers(),json=old_request,definition='control_response')
        self.control('reset');before=self.state()
        status,body=self.exchange('POST',f"/api/sessions/{self.session['session_id']}/save",headers=self.headers(),json=old_request,definition='control_response')
        self.assertEqual(status,409);self.assertEqual(body['error']['code'],'STALE_GENERATION');self.assertEqual(self.state(),before)

    def test_missing_foreign_auth_bad_fields_stale_requests_do_not_change_archives(self):
        first=self.append('保留')['data']['slot'];other=self.create();other_before=self.state(other)
        self.assertEqual(self.slots(other),[])
        self.archive_http('POST','/'+first['save_id']+'/restore',self.version(other_before),404,'SAVE_NOT_FOUND',session=other)
        self.archive_http('GET',headers={'X-Session-Token':'QA_BAD_TOKEN'},expected=403,code='FORBIDDEN_SESSION')
        before=self.state();rows=self.rows();self.restore_archive('missing_QA_archive',expected=404,code='SAVE_NOT_FOUND')
        for mutation in [{'name':'x'*41},{'name':True},{'name':4},{'extra':'blocked'},{'revision':True}]:
            with self.subTest(fields=list(mutation)):
                self.append(request={**self.version(),**mutation},expected=422,code='BAD_ARGUMENT')
                self.assertEqual(self.state(),before);self.assertEqual(self.rows(),rows)
        stale=self.version();self.action('inspect',{'object_id':'r1_clock'});current=self.state()
        first_stale=self.append(request=stale,expected=409,code='STALE_STATE');self.assertEqual(self.state(),current)
        self.control('reset');new=self.state()
        replay=self.append(request=stale,expected=409,code='STALE_STATE');self.assertEqual(replay['event_id'],first_stale['event_id'])
        self.append(request={**stale,'request_id':self.version()['request_id']},expected=409,code='STALE_GENERATION')
        self.assertEqual(self.state(),new);self.assertEqual(self.rows(),rows);self.assertEqual(self.state(other),other_before)

    def test_legacy_slot_list_restore_old_database_without_rewriting_snapshot(self):
        self.action('inspect',{'object_id':'r1_record'});old=self.control('save')
        with closing(sqlite3.connect(self.db)) as db:
            raw=db.execute('SELECT snapshot_json,summary_json FROM saves WHERE session_id=?',(self.session['session_id'],)).fetchone()
            # This owned synthetic file now has the previous single-slot schema.
            db.execute('DROP TABLE save_slots');db.commit()
        self.reopen();legacy=self.slots()[0];self.assertEqual(legacy['save_id'],'legacy');self.assertEqual(legacy['kind'],'legacy')
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT snapshot_json,summary_json FROM saves WHERE session_id=?',(self.session['session_id'],)).fetchone(),raw)
        self.assertEqual((legacy['room_id'],legacy['status'],legacy['clues_found']),(None,None,None))
        self.append('独立命名档');self.action('inspect',{'object_id':'r1_clock'});self.control('save')
        newer=self.state();self.control('reset');before=self.state();restored=self.restore_archive('legacy')['data']['visible_state'];self.assert_restored(before,newer,restored)
        self.assertEqual(len(self.slots()),2)
        # The pre-migration old slot was readable; later old /save intentionally overwrote only that slot.
        self.assertEqual(game(old)['statistics']['clues_found'],1)
        self.assertTrue(raw[0] and raw[1])

    def test_owned_corrupt_crossversion_snapshot_rejection_preserves_live_and_other_archives(self):
        good=self.append('正确档')['data']['slot'];bad=self.append('注入测试档')['data']['slot'];self.control('save')
        original=next(row[2] for row in self.rows() if row[0]==bad['save_id'])
        fixtures=[('checksum',lambda s:s.update(checksum='bad'),'INVALID_SNAPSHOT'),
                  ('version',lambda s:s.update(level_version='3.3.0',schema_version='1.3.0'),'SNAPSHOT_VERSION_MISMATCH'),
                  ('owner',lambda s:s.update(session_id='foreign_owner'),'INVALID_SNAPSHOT'),
                  ('fields',lambda s:s['game_fields'].update(unexpected_field=True),'INVALID_SNAPSHOT'),
                  ('invariant',lambda s:s['game_fields']['statistics'].update(hint_count=-1),'INVALID_SNAPSHOT')]
        for name,mutate,code in fixtures:
            with self.subTest(damage=name):
                value=json.loads(original);mutate(value)
                if name!='checksum':value['checksum']=digest(value)
                encoded=json.dumps(value,ensure_ascii=False)
                with closing(sqlite3.connect(self.db)) as db:
                    db.execute('UPDATE save_slots SET snapshot_json=? WHERE session_id=? AND save_id=?',(encoded,self.session['session_id'],bad['save_id']));db.commit()
                before=self.state();rows=self.rows();self.restore_archive(bad['save_id'],expected=409,code=code)
                self.assertEqual(self.state(),before);self.assertEqual(self.rows(),rows)
                self.restore_archive(good['save_id']);self.assertIsNotNone(self.state()['save'])

    def test_selected_restore_expires_pending_mock_hint_without_stats_mutation(self):
        self.action('inspect',{'object_id':'r1_clock'});self.action('inspect',{'object_id':'r1_record'})
        slot=self.append('提示前')['data']['slot'];saved=self.state();entered=threading.Event();release=threading.Event()
        class Gated(graybox.CapturedHintProvider):
            async def complete(provider,*args,**kwargs):
                entered.set()
                if not await asyncio.to_thread(release.wait,3):raise AssertionError('Synthetic QA gate unreleased')
                return await super().complete(*args,**kwargs)
        self.install(Gated());request={**self.version(),'message':'只依据已发现事实','hint_level':1}
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(self.ask,request=request)
            try:
                self.assertTrue(entered.wait(2));self.restore_archive(slot['save_id']);restored=self.state()
            finally:release.set()
            data,_=pending.result(timeout=5)
        self.assertEqual(data['status'],'stopped');self.assertEqual(data['stop_reason'],'STALE_STATE')
        self.assertEqual(self.state(),restored);self.assertEqual(game(restored),game(saved))

    def test_additive_archive_routes_preserve_explicit_old_mode_entries(self):
        from backend.app.main import create_app
        for mode,level in [('legacy','2.0.0'),('v3.1','3.1.0'),('v3.2','3.2.0'),('v3.3','3.3.0')]:
            with self.subTest(mode=mode):
                self.client.__exit__(None,None,None)
                self.client=TestClient(create_app(Path(self.temp.name)/(mode+'.sqlite'),gameplay_version=mode),raise_server_exceptions=False)
                self.client.__enter__();self.session=self.create();before=self.state()
                self.assertEqual(before['level_version'],level);self.assertNotIn('statistics',before)
                request=self.version();created=self.append(request=request)['data']['slot']
                self.control('save');self.control('reset');reset=self.state()
                replay=self.append(request=request);self.assertTrue(replay['data']['replayed']);self.assertEqual(self.state(),reset)
                restored=self.restore_archive(created['save_id'])['data']['visible_state'];self.assertEqual(game(restored),game(before))
                self.assertEqual([s['kind'] for s in self.slots()],['archive','legacy'])
                if mode=='legacy':
                    from tests.api.test_m2 import ROUTE
                    from tests.api.test_m3 import Scripted, final
                    for tool,args in ROUTE[:12]:self.action(tool,args)
                    bound=self.append('提议之前')['data']['slot']
                    self.install(Scripted([final('use_item',{'item_id':'emergency_key','target_id':'r2_door'})]))
                    status,body=self.exchange('POST',f"/api/sessions/{self.session['session_id']}/ai/turns",
                        headers=self.headers(),json={**self.version(),'message':'根据已发现事实继续'},definition='ai_turn_response')
                    self.assertEqual(status,200);proposal=body['data']['proposal'];self.assertIsNotNone(proposal)
                    self.restore_archive(bound['save_id']);current=self.state()
                    status,body=self.exchange('POST',f"/api/sessions/{self.session['session_id']}/proposals/{proposal['proposal_id']}/confirm",
                        headers=self.headers(),json={},definition='action_response')
                    self.assertEqual(status,409);self.assertEqual(body['error']['code'],'PROPOSAL_INVALIDATED');self.assertEqual(self.state(),current)
