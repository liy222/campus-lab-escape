"""Independent archive deletion QA; isolated SQLite and paid-network forbidden."""
import copy
import hashlib
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from jsonschema import Draft202012Validator, FormatChecker
from tests.api.test_r1 import HTTPFixture
from tests.api import test_r1 as base
from tests.api import test_multiple_saves as archives

CHECKS_DELETE = []

class SaveDeleteAcceptance(HTTPFixture):
    def setUp(self):
        super().setUp();self.client.__exit__(None,None,None)
        self.clock=datetime(2026,10,14,tzinfo=timezone.utc)
        self.clock_patch=patch('backend.app.domain.graybox_rules.utc_now',side_effect=lambda:self.clock.isoformat().replace('+00:00','Z'))
        self.clock_patch.start();self.db=Path(self.temp.name)/'save-delete.sqlite'
        self.reopen(first=True);self.session=self.create()
        self.network=patch('httpx.AsyncClient.send',side_effect=AssertionError('Paid network forbidden in deletion QA'));self.network.start()

    def tearDown(self):
        self.network.stop();self.clock_patch.stop();super().tearDown()

    reopen = archives.MultipleSavesAcceptance.reopen
    version = archives.MultipleSavesAcceptance.version
    control = archives.MultipleSavesAcceptance.control
    append = archives.MultipleSavesAcceptance.append
    archive_http = archives.MultipleSavesAcceptance.archive_http
    slots = archives.MultipleSavesAcceptance.slots
    restore_archive = archives.MultipleSavesAcceptance.restore_archive
    rows = archives.MultipleSavesAcceptance.rows
    route32 = archives.MultipleSavesAcceptance.route32
    finish_circuit = archives.MultipleSavesAcceptance.finish_circuit
    rotate_to = archives.MultipleSavesAcceptance.rotate_to
    win_route = archives.MultipleSavesAcceptance.win_route

    def delete(self, save_id, request=None, expected=200, code=None, session=None, headers=None):
        owner = session or self.session
        request = copy.deepcopy(request or self.version(self.state(owner)))
        status, body = self.exchange('POST', f"/api/sessions/{owner['session_id']}/saves/{save_id}/delete",
            headers=headers if headers is not None else self.headers(owner), json=request, definition='delete_save_response')
        self.assertEqual(status, expected, base.sanitize(body))
        if code: self.assertEqual(body['error']['code'], code)
        if body['ok']:
            self.assertEqual(set(body['data']), {'request_id','replayed','save_id','message','visible_state'})
            self.assertEqual(body['data']['save_id'], save_id)
            self.assertEqual(body['data']['request_id'], request['request_id'])
        CHECKS_DELETE.append({'test':self._testMethodName,'http_status':status,'code':body.get('error',{}).get('code'),
            'replayed':body.get('data',{}).get('replayed'),'save_id':save_id})
        return body

    def sql(self, statement, parameters=()):
        with closing(sqlite3.connect(self.db)) as db:
            result=db.execute(statement, parameters).fetchall(); db.commit(); return result

    def unchanged(self, before, rows):
        self.assertEqual(self.state(),before)
        self.assertEqual(self.rows(),rows)

    def test_only_selected_archive_removed_durable_legacy_and_live_unchanged(self):
        self.control('save')
        old=self.sql('SELECT snapshot_json,summary_json FROM saves')
        one=self.append('第一时刻')['data']['slot']; two=self.append('第二时刻')['data']['slot']
        self.action('inspect',{'object_id':'r1_clock'});before=self.state()
        other_row=next(r for r in self.rows() if r[0]==two['save_id'])
        self.delete(one['save_id'])
        self.assertEqual(self.rows(),[other_row]);self.assertEqual(self.state(),before)
        self.assertEqual(self.sql('SELECT snapshot_json,summary_json FROM saves'),old)
        self.reopen();self.assertEqual(self.state(),before);self.assertEqual(self.rows(),[other_row])
        self.restore_archive(one['save_id'],expected=404,code='SAVE_NOT_FOUND')
        self.restore_archive(two['save_id']);self.delete(two['save_id'])
        self.assertEqual([s['kind'] for s in self.slots()],['legacy'])
        self.delete('legacy',expected=404,code='SAVE_NOT_FOUND')
        self.assertEqual(self.sql('SELECT snapshot_json,summary_json FROM saves'),old)

    def test_auth_foreign_owner_and_bad_identifiers_fields_unchanged(self):
        one=self.append('保留')['data']['slot'];other=self.create();before=self.state();other_before=self.state(other);rows=self.rows()
        self.delete(one['save_id'],session=other,expected=404,code='SAVE_NOT_FOUND')
        for headers in ({},{'X-Session-Token':'QA_BAD_TOKEN'}):
            with self.subTest(auth=bool(headers)):
                rejected=self.delete(one['save_id'],headers=headers,expected=403,code='FORBIDDEN_SESSION')
                self.assertIsNone(rejected['visible_state'])
        for invalid in ('bad.identifier','x'*129):
            with self.subTest(invalid_length=len(invalid)):self.delete(invalid,expected=422,code='BAD_ARGUMENT')
        for mutation in ({'revision':True},{'extra':1},{'generation':'bad'},{'request_id':False}):
            with self.subTest(fields=list(mutation)):
                self.delete(one['save_id'],request={**self.version(),**mutation},expected=422,code='BAD_ARGUMENT')
        r=self.client.post(f"/api/sessions/{self.session['session_id']}/saves/{one['save_id']}/delete",headers={**self.headers(),'Content-Type':'application/json'},content='{bad JSON')
        self.assertEqual(r.status_code,422);self.assertEqual(r.json()['error']['code'],'BAD_ARGUMENT')
        self.unchanged(before,rows);self.assertEqual(self.state(other),other_before)

    def test_missing_error_receipt_replay_current_state_and_conflict(self):
        request=self.version();first=self.delete('missing_QA_archive',request,404,'SAVE_NOT_FOUND')
        self.control('reset');before=self.state()
        replay=self.delete('missing_QA_archive',request,404,'SAVE_NOT_FOUND')
        self.assertEqual(replay['event_id'],first['event_id']);self.assertEqual(replay['visible_state'],before)
        self.delete('different_QA_archive',request,409,'REQUEST_ID_CONFLICT')
        self.assertEqual(self.state(),before)

    def test_stale_revision_generation_no_deletion_and_prior_error_replays(self):
        one=self.append('保留')['data']['slot'];stale=self.version();self.action('inspect',{'object_id':'r1_clock'})
        before=self.state();rows=self.rows();first=self.delete(one['save_id'],stale,409,'STALE_STATE');self.unchanged(before,rows)
        self.control('reset');before=self.state();replay=self.delete(one['save_id'],stale,409,'STALE_STATE')
        self.assertEqual(first['event_id'],replay['event_id']);self.assertEqual(replay['visible_state'],before)
        self.delete(one['save_id'],{**stale,'request_id':self.version()['request_id']},409,'STALE_GENERATION')
        self.unchanged(before,rows)

    def test_completed_replay_before_generation_and_crossoperation_conflict(self):
        one=self.append('删除一')['data']['slot'];two=self.append('保留二')['data']['slot'];request=self.version();first=self.delete(one['save_id'],request)
        self.control('reset');self.action('inspect',{'object_id':'r1_clock'});before=self.state();rows=self.rows()
        replay=self.delete(one['save_id'],request);self.assertTrue(replay['data']['replayed']);self.assertEqual(first['event_id'],replay['event_id'])
        self.assertEqual(replay['data']['visible_state'],before)
        self.delete(two['save_id'],request,409,'REQUEST_ID_CONFLICT')
        self.append(request=request,expected=409,code='REQUEST_ID_CONFLICT')
        self.restore_archive(two['save_id'],request,409,'REQUEST_ID_CONFLICT');self.unchanged(before,rows)

    def test_prior_pending_receipt_does_not_delete_or_reexecute(self):
        one=self.append('保留')['data']['slot'];request=self.version();before=self.state();rows=self.rows()
        normalized={'operation':'archive_delete',**request,'save_id':one['save_id']}
        encoded=json.dumps(normalized,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        digest=hashlib.sha256(encoded.encode()).hexdigest()
        self.sql('INSERT INTO action_receipts (session_id,request_id,request_hash,generation,response_json,http_status,phase) VALUES (?,?,?,?,?,?,?)',
            (self.session['session_id'],request['request_id'],digest,request['generation'],'{}',200,'pending'))
        response=self.client.post(f"/api/sessions/{self.session['session_id']}/saves/{one['save_id']}/delete",headers=self.headers(),json=request)
        self.assertGreaterEqual(response.status_code,400);self.assertEqual(response.json()['error']['code'],'MODEL_UNAVAILABLE')
        self.unchanged(before,rows)
        CHECKS_DELETE.append({'test':self._testMethodName,'http_status':response.status_code,'code':'MODEL_UNAVAILABLE','synthetic_fixture':'pending receipt'})

    def test_transaction_rollback_on_postdelete_event_failure_then_retry_once(self):
        one=self.append('回滚保留')['data']['slot'];request=self.version();before=self.state();rows=self.rows()
        from backend.app.storage.sqlite import Store
        original=Store.event
        def fail_event(store,connection,event_id,session_id,operation,*args,**kwargs):
            if operation=='archive_delete':raise RuntimeError('QA synthetic postdelete rollback probe')
            return original(store,connection,event_id,session_id,operation,*args,**kwargs)
        with patch.object(Store,'event',fail_event):
            r=self.client.post(f"/api/sessions/{self.session['session_id']}/saves/{one['save_id']}/delete",headers=self.headers(),json=request)
        self.assertEqual(r.status_code,500);self.unchanged(before,rows)
        self.assertEqual(self.sql('SELECT request_id FROM action_receipts WHERE session_id=? AND request_id=?',(self.session['session_id'],request['request_id'])),[])
        self.delete(one['save_id'],request);self.assertEqual(self.rows(),[]);self.assertEqual(self.state(),before)

    def test_corrupt_snapshot_and_metadata_can_delete_without_loading_content(self):
        good=self.append('保留好档')['data']['slot'];bad=self.append('坏档')['data']['slot'];before=self.state()
        goodrow=next(r for r in self.rows() if r[0]==good['save_id'])
        self.sql('UPDATE save_slots SET snapshot_json=?,metadata_json=? WHERE save_id=?',('{invalid snapshot','{invalid metadata',bad['save_id']))
        self.delete(bad['save_id']);self.assertEqual(self.rows(),[goodrow]);self.assertEqual(self.state(),before)
        self.assertEqual([s['save_id'] for s in self.slots()],[good['save_id']])

    def test_won_and_reset_deletion_available_without_changing_settlement(self):
        one=self.append('开始')['data']['slot'];self.win_route();won=self.state();two=self.append('通关')['data']['slot']
        self.delete(one['save_id']);self.assertEqual(self.state(),won)
        self.control('reset');before=self.state();self.delete(two['save_id']);self.assertEqual(self.state(),before);self.assertEqual(self.slots(),[])

    def test_contract_routes_schema_and_strict_delete_response_instances(self):
        routes=json.loads((base.ROOT/'contracts/routes.json').read_text(encoding='utf-8'))['routes']
        self.assertEqual(len(routes),13);self.assertEqual(len({(r['method'],r['path']) for r in routes}),13)
        schema=base.SCHEMA;Draft202012Validator.check_schema(schema)
        route=next(r for r in routes if r['path'].endswith('/delete'))
        self.assertEqual(route['request'],'version_request');self.assertEqual(route['response'],'delete_save_response')
        slot=self.append()['data']['slot'];body=self.delete(slot['save_id'])
        validator=Draft202012Validator({'$ref':'#/$defs/delete_save_response','$defs':schema['$defs']},format_checker=FormatChecker())
        for mutate in ('extra_top','extra_data','missing_save_id','bad_replayed'):
            with self.subTest(mutation=mutate):
                bad=copy.deepcopy(body)
                if mutate=='extra_top':bad['extra']=True
                elif mutate=='extra_data':bad['data']['extra']=True
                elif mutate=='missing_save_id':del bad['data']['save_id']
                else:bad['data']['replayed']='true'
                self.assertTrue(list(validator.iter_errors(bad)))

    def test_concurrent_identical_delete_commits_once_and_returns_replay(self):
        one=self.append('并发删除')['data']['slot'];request=self.version();before=self.state();barrier=threading.Barrier(2)
        def send(_):barrier.wait(timeout=4);return self.delete(one['save_id'],request)
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(send,range(2)))
        self.assertEqual(sorted(r['data']['replayed'] for r in results),[False,True])
        self.assertEqual(results[0]['event_id'],results[1]['event_id']);self.assertEqual(self.state(),before);self.assertEqual(self.rows(),[])
        self.assertEqual(len(self.sql('SELECT request_id FROM action_receipts WHERE session_id=? AND request_id=?',(self.session['session_id'],request['request_id']))),1)
        self.assertEqual(len(self.sql("SELECT event_id FROM events WHERE session_id=? AND operation='archive_delete' AND outcome='committed'",(self.session['session_id'],))),1)
