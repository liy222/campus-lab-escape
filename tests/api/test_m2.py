"""T13 independent manual baseline, transaction and snapshot acceptance."""
import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

import httpx

from tests.api.test_r1 import HTTPFixture, EXCHANGES, ROOT, sanitize

ROUTE = [
    ('inspect', {'object_id': 'r1_note'}), ('inspect', {'object_id': 'r1_cabinet'}),
    ('submit_code', {'target_id': 'r1_cabinet', 'code': '382'}), ('take', {'item_id': 'access_card'}),
    ('use_item', {'item_id': 'access_card', 'target_id': 'r1_door'}), ('move', {'destination_id': 'R2'}),
    ('take', {'item_id': 'fuse'}), ('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}),
    ('inspect', {'object_id': 'r2_monitor'}), ('inspect', {'object_id': 'r2_drawer'}),
    ('submit_code', {'target_id': 'r2_drawer', 'code': '724'}), ('take', {'item_id': 'emergency_key'}),
    ('use_item', {'item_id': 'emergency_key', 'target_id': 'r2_door'}), ('move', {'destination_id': 'R3'}),
    ('inspect', {'object_id': 'r3_checklist'}), ('inspect', {'object_id': 'r3_panel'}),
    ('submit_code', {'target_id': 'r3_panel', 'code': '231'}), ('move', {'destination_id': 'EXIT'}),
]


def gameplay(state):
    return {k: state[k] for k in ['status', 'room', 'objects', 'inventory', 'clues', 'exits', 'progress']}


def digest(snapshot):
    # Independent implementation of SPEC checksum, not server checksum utility.
    value = {k: v for k, v in snapshot.items() if k != 'checksum'}
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


class M2Acceptance(HTTPFixture):
    def route(self, begin=0, end=18):
        results = []
        for tool, arguments in ROUTE[begin:end]:
            results.append(self.action(tool, arguments))
        return results

    def version(self, state=None, request_id=None):
        state = state or self.state()
        return {'request_id': request_id or uuid.uuid4().hex, 'revision': state['revision'], 'generation': state['generation']}

    def control_post(self, operation, request):
        return self.exchange('POST', f"/api/sessions/{self.session['session_id']}/{operation}", headers=self.headers(), json=request, definition='control_response')

    def control(self, operation):
        status, body = self.control_post(operation, self.version())
        self.assertEqual(status, 200, body)
        return body['data']

    def control_reject(self, operation, request, code, status=409):
        before = self.state()
        actual, body = self.control_post(operation, request)
        self.assertEqual(actual, status, body)
        self.assertEqual(body['error']['code'], code)
        self.assertEqual(self.state(), before)
        return body

    def test_A02_exact_18_step_route_and_baseline_key(self):
        results = self.route()
        for step, result in enumerate(results, 1):
            with self.subTest(step=step):
                self.assertEqual(result['visible_state']['revision'], step)
                self.assertEqual(result['receipt']['revision_before'], step - 1)
                self.assertEqual(result['receipt']['revision_after'], step)
                self.assertTrue(result['receipt']['changed'])
                self.assertIsNone(result['proposal'])
                self.assertEqual(result['receipt']['consumed_item_ids'], ['fuse'] if step == 8 else [])
        won = results[-1]['visible_state']
        self.assertEqual(won['room']['room_id'], 'EXIT')
        self.assertEqual(won['status'], 'won')
        self.assertEqual(won['progress'], {'power_on': True, 'check_done': True})
        self.assertEqual([i['item_id'] for i in won['inventory']], ['access_card', 'emergency_key'])
        self.assertEqual(won['objects'], [])
        self.assertEqual(won['exits'], [])
        self.assertEqual([c['clue_id'] for c in won['clues']], ['r1_note_clue', 'r1_cabinet_clue', 'r2_monitor_clue', 'r2_drawer_clue', 'r3_checklist_clue', 'r3_panel_clue'])

    def test_A03_A04_A10_R2_power_and_wrong_code(self):
        self.route(end=6)
        self.reject(self.request('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}), 'PRECONDITION_FAILED')
        self.reject(self.request('use_item', {'item_id': 'emergency_key', 'target_id': 'r2_door'}), 'PRECONDITION_FAILED')
        self.reject(self.request('submit_code', {'target_id': 'r2_drawer', 'code': '724'}), 'PRECONDITION_FAILED')
        self.reject(self.request('take', {'item_id': 'emergency_key'}), 'NOT_VISIBLE')
        self.reject(self.request('move', {'destination_id': 'R3'}), 'PRECONDITION_FAILED')
        before = self.state()
        observed = self.action('inspect', {'object_id': 'r2_monitor'})
        self.assertEqual(observed['visible_state'], before)
        self.assertEqual(observed['receipt']['new_clue_ids'], [])
        self.assertIn('当前无显示', observed['receipt']['observation'])
        self.assertNotIn('青色7', json.dumps(observed, ensure_ascii=False))
        self.route(begin=6, end=8)
        self.assertNotIn('r2_monitor_clue', [c['clue_id'] for c in self.state()['clues']])
        self.assertNotIn('青色7', json.dumps(self.state(), ensure_ascii=False))
        wrong = self.reject(self.request('submit_code', {'target_id': 'r2_drawer', 'code': '000'}), 'WRONG_CODE')
        self.assertNotIn('724', json.dumps(wrong, ensure_ascii=False))

    def test_R3_exit_preconditions_wrong_panel_and_won_rules(self):
        self.route(end=14)
        self.reject(self.request('move', {'destination_id': 'EXIT'}), 'PRECONDITION_FAILED')
        self.reject(self.request('move', {'destination_id': 'R1'}), 'PRECONDITION_FAILED')
        wrong = self.reject(self.request('submit_code', {'target_id': 'r3_panel', 'code': '000'}), 'WRONG_CODE')
        self.assertNotIn('231', json.dumps(wrong, ensure_ascii=False))
        self.route(begin=14)
        for tool, args in [('take', {'item_id': 'fuse'}), ('use_item', {'item_id': 'emergency_key', 'target_id': 'r2_door'}), ('submit_code', {'target_id': 'r3_panel', 'code': '231'}), ('move', {'destination_id': 'R3'})]:
            with self.subTest(tool=tool):
                self.reject(self.request(tool, args), 'GAME_FINISHED')
        self.action('get_inventory', {})
        self.reject(self.request('inspect', {'object_id': 'exit_door'}), 'NOT_VISIBLE')
        self.control('save')
        restored = self.control('restore')['visible_state']
        self.assertEqual(restored['status'], 'won')
        reset = self.control('reset')['visible_state']
        self.assertEqual(reset['status'], 'playing')
        self.assertEqual(reset['room']['room_id'], 'R1')

    def test_consumption_replays_and_reuse_never_return_fuse(self):
        self.route(end=7)
        request = self.request(*ROUTE[7], request_id='qa-install-fuse')
        status, first = self.post(request)
        self.assertEqual(status, 200)
        status, replay = self.post(copy.deepcopy(request))
        self.assertEqual(status, 200)
        self.assertTrue(replay['data']['replayed'])
        self.assertEqual(first['data']['receipt'], replay['data']['receipt'])
        noop = self.action(*ROUTE[7])
        self.assertFalse(noop['receipt']['changed'])
        self.assertEqual(noop['receipt']['consumed_item_ids'], [])
        self.assertNotIn('fuse', [i['item_id'] for i in self.state()['inventory']])
        self.reject(self.request('take', {'item_id': 'fuse'}), 'ALREADY_TAKEN')
        self.route(begin=8, end=13)
        noop = self.action(*ROUTE[12])
        self.assertFalse(noop['receipt']['changed'])
        self.assertEqual(noop['receipt']['consumed_item_ids'], [])
        self.assertIn('emergency_key', [i['item_id'] for i in noop['visible_state']['inventory']])
        self.action('move', {'destination_id': 'R3'})
        self.action('move', {'destination_id': 'R2'})
        self.action('move', {'destination_id': 'R3'})

    def test_A12_single_slot_restore_reset_and_current_version(self):
        self.route(end=10)
        initial = self.state()
        saved = self.control('save')['visible_state']
        self.assertEqual(gameplay(saved), gameplay(initial))
        self.assertEqual(saved['revision'], initial['revision'])
        self.assertEqual(saved['generation'], initial['generation'])
        self.assertEqual(set(saved['save']), {'schema_version', 'level_version', 'saved_at', 'source_revision', 'source_generation'})
        self.route(begin=10, end=12)
        progressed = self.state()
        restored = self.control('restore')['visible_state']
        self.assertEqual(gameplay(restored), gameplay(saved))
        self.assertEqual(restored['revision'], progressed['revision'] + 1)
        self.assertNotEqual(restored['generation'], progressed['generation'])
        self.assertEqual(restored['save'], saved['save'])
        reset = self.control('reset')['visible_state']
        self.assertEqual(reset['room']['room_id'], 'R1')
        self.assertEqual(reset['inventory'], [])
        self.assertEqual(reset['clues'], [])
        self.assertEqual(reset['save'], saved['save'])
        self.assertEqual(reset['revision'], restored['revision'] + 1)
        self.assertNotEqual(reset['generation'], restored['generation'])
        again = self.control('restore')['visible_state']
        self.assertEqual(gameplay(again), gameplay(saved))
        self.route(begin=10, end=12)
        second_slot = self.control('save')['visible_state']
        self.assertGreater(second_slot['save']['source_revision'], saved['save']['source_revision'])
        self.control('reset')
        second_restore = self.control('restore')['visible_state']
        self.assertIn('emergency_key', [i['item_id'] for i in second_restore['inventory']])

    def test_A05_control_replay_cross_operation_ID_namespace(self):
        request = self.version(request_id='qa-save-shared')
        status, first = self.control_post('save', request)
        self.assertEqual(status, 200)
        self.action('inspect', {'object_id': 'r1_note'})
        status, again = self.control_post('save', copy.deepcopy(request))
        self.assertEqual(status, 200)
        self.assertTrue(again['data']['replayed'])
        self.assertEqual(again['data']['request_id'], first['data']['request_id'])
        self.assertEqual(again['data']['visible_state']['revision'], 1)
        for operation in ['reset', 'restore']:
            self.control_reject(operation, copy.deepcopy(request), 'REQUEST_ID_CONFLICT')
        action_request = self.request('get_inventory', {}, request_id=request['request_id'])
        self.reject(action_request, 'REQUEST_ID_CONFLICT')
        action_request = self.request('inspect', {'object_id': 'r1_cabinet'}, request_id='qa-action-shared')
        self.post(action_request)
        control_request = {k: action_request[k] for k in ['request_id', 'revision', 'generation']}
        for operation in ['save', 'reset', 'restore']:
            self.control_reject(operation, control_request, 'REQUEST_ID_CONFLICT')

    def test_A06_control_stale_versions_and_reset_replay(self):
        self.control('save')
        old = self.version()
        self.action('inspect', {'object_id': 'r1_note'})
        for operation in ['save', 'restore', 'reset']:
            self.control_reject(operation, self.version(self.session['visible_state']), 'STALE_STATE')
        reset_request = self.version(request_id='qa-reset')
        status, body = self.control_post('reset', reset_request)
        self.assertEqual(status, 200)
        self.control_reject('reset', reset_request, 'STALE_GENERATION')
        for operation in ['save', 'restore', 'reset']:
            request = self.version()
            request['generation'] = old['generation']
            self.control_reject(operation, request, 'STALE_GENERATION')
        action_request = self.request('get_inventory', {})
        action_request['generation'] = old['generation']
        self.reject(action_request, 'STALE_GENERATION')

    def test_strict_control_parameters_and_no_client_snapshot(self):
        for operation in ['save', 'restore', 'reset']:
            for key, value in [('game_fields', {'status': 'won'}), ('revision', True), ('generation', 'bad'), ('request_id', '../bad')]:
                request = self.version()
                request[key] = value
                with self.subTest(operation=operation, key=key):
                    self.control_reject(operation, request, 'BAD_ARGUMENT', 422)
            request = self.version()
            del request['revision']
            self.control_reject(operation, request, 'BAD_ARGUMENT', 422)
        self.control_reject('restore', self.version(), 'SAVE_NOT_FOUND', 404)

    def test_A14_all_implemented_routes_foreign_session(self):
        other = self.create()
        before = self.state(other)
        for operation in ['state', 'actions', 'save', 'restore', 'reset']:
            for token in [None, 'invalid-capability', self.session['token']]:
                with self.subTest(operation=operation, capability_case='missing' if token is None else 'invalid-or-foreign'):
                    method = 'GET' if operation == 'state' else 'POST'
                    request = self.request('get_inventory', {}, state=before) if operation == 'actions' else self.version(before)
                    kwargs = {} if method == 'GET' else {'json': request}
                    headers = {} if token is None else {'X-Session-Token': token}
                    status, body = self.exchange(method, f"/api/sessions/{other['session_id']}/{operation}", headers=headers, **kwargs)
                    self.assertEqual(status, 403)
                    self.assertEqual(body['error']['code'], 'FORBIDDEN_SESSION')
                    self.assertIsNone(body['visible_state'])
        self.assertEqual(self.state(other), before)

    def test_concurrent_same_version_actions_commit_only_once(self):
        self.route(end=7)
        current = self.state()
        barrier = threading.Barrier(2)
        requests = [self.request(*ROUTE[7], state=current), self.request('move', {'destination_id': 'R1'}, state=current)]
        def invoke(request):
            barrier.wait(timeout=5)
            return self.post(request)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(invoke, requests))
        self.assertEqual(sorted(status for status, body in results), [200, 409])
        failure = next(body for status, body in results if status == 409)
        self.assertEqual(failure['error']['code'], 'STALE_STATE')
        self.assertEqual(self.state()['revision'], current['revision'] + 1)

    def test_concurrent_identical_consumption_request_replays_one_receipt(self):
        self.route(end=7)
        request = self.request(*ROUTE[7], request_id='qa-concurrent-fuse')
        barrier = threading.Barrier(2)
        def invoke(index):
            barrier.wait(timeout=5)
            return self.post(copy.deepcopy(request))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(invoke, range(2)))
        self.assertEqual([status for status, body in results], [200, 200])
        self.assertEqual(sorted(body['data']['replayed'] for status, body in results), [False, True])
        self.assertEqual(results[0][1]['data']['receipt'], results[1][1]['data']['receipt'])
        self.assertEqual(self.state()['revision'], 8)
        self.assertNotIn('fuse', [i['item_id'] for i in self.state()['inventory']])

    def test_A13_snapshot_integrity_owner_versions_types_and_invariants(self):
        self.route(end=10)
        self.control('save')
        db_path = Path(self.temp.name) / 'test.sqlite'
        # Only the fixture-owned temp DB is mutated; no raw database/snapshot exported.
        with closing(sqlite3.connect(db_path)) as db:
            row = db.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (self.session['session_id'],)).fetchone()
        baseline = json.loads(row[0])
        self.assertEqual(baseline['checksum'], digest(baseline))
        cases = [
            ('other-owner', lambda s: s.update(session_id='another-session'), 'INVALID_SNAPSHOT'),
            ('bad-checksum', lambda s: s.update(checksum='0' * 64), 'INVALID_SNAPSHOT'),
            ('schema-mismatch', lambda s: s.update(schema_version='9.0.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('level-mismatch', lambda s: s.update(level_version='2.0.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('version-type', lambda s: s.update(level_version=1), 'INVALID_SNAPSHOT'),
            ('timestamp', lambda s: s.update(saved_at='not-a-date'), 'INVALID_SNAPSHOT'),
            ('unknown-top-field', lambda s: s.update(extra=True), 'INVALID_SNAPSHOT'),
            ('client-revision', lambda s: s['game_fields'].update(revision=0), 'INVALID_SNAPSHOT'),
            ('duplicate-item', lambda s: s['game_fields']['inventory'].append('access_card'), 'INVALID_SNAPSHOT'),
            ('unknown-item', lambda s: s['game_fields']['inventory'].append('unknown'), 'INVALID_SNAPSHOT'),
            ('unopened-card', lambda s: s['game_fields'].update(opened_containers=[]), 'INVALID_SNAPSHOT'),
            ('power-and-fuse', lambda s: s['game_fields']['inventory'].append('fuse'), 'INVALID_SNAPSHOT'),
            ('monitor-without-power', lambda s: s['game_fields']['flags'].update(power_on=False), 'INVALID_SNAPSHOT'),
            ('won-R2', lambda s: s['game_fields'].update(status='won'), 'INVALID_SNAPSHOT'),
            ('R3-locked', lambda s: s['game_fields'].update(room_id='R3'), 'INVALID_SNAPSHOT'),
            ('flag-type', lambda s: s['game_fields']['flags'].update(power_on='true'), 'INVALID_SNAPSHOT'),
            ('duplicate-clue', lambda s: s['game_fields']['discovered_clue_ids'].append('r1_note_clue'), 'INVALID_SNAPSHOT'),
            ('unknown-clue', lambda s: s['game_fields']['discovered_clue_ids'].append('unknown'), 'INVALID_SNAPSHOT'),
        ]
        for name, mutate, code in cases:
            broken = copy.deepcopy(baseline)
            mutate(broken)
            if name != 'bad-checksum':
                broken['checksum'] = digest(broken)
            with self.subTest(case=name):
                with closing(sqlite3.connect(db_path)) as db:
                    db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (json.dumps(broken, ensure_ascii=False), self.session['session_id']))
                    db.commit()
                self.control_reject('restore', self.version(), code)
        for raw in ['{', 'null', '[]']:
            with self.subTest(raw_kind=raw):
                with closing(sqlite3.connect(db_path)) as db:
                    db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (raw, self.session['session_id']))
                    db.commit()
                self.control_reject('restore', self.version(), 'INVALID_SNAPSHOT')
        with closing(sqlite3.connect(db_path)) as db:
            db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (json.dumps(baseline, ensure_ascii=False), self.session['session_id']))
            db.commit()
        self.control('restore')

    def test_A12_real_service_stop_restart_restore_and_event_sequence(self):
        with socket.socket() as port_socket:
            port_socket.bind(('127.0.0.1', 0))
            port = port_socket.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        environment = os.environ.copy()
        environment.update(AI_PROVIDER='mock', SQLITE_PATH=str(Path(self.temp.name) / 'test.sqlite'))
        command = [sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log']
        direct_client, process = self.client, None
        def start():
            child = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise AssertionError('QA-owned service exited during startup')
                try:
                    if httpx.get(url + '/api/health', timeout=0.5).status_code == 200:
                        EXCHANGES.append({'test': self.id(), 'stage': 'actual_service_start', 'pid': child.pid, 'command': command, 'provider': 'mock'})
                        return child
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            child.terminate()
            child.wait(timeout=5)
            raise AssertionError('QA-owned service startup timeout')
        def stop(child):
            child.terminate()
            output, _ = child.communicate(timeout=10)
            EXCHANGES.append(sanitize({'test': self.id(), 'stage': 'actual_service_stop', 'pid': child.pid, 'process_returncode_after_termination': child.returncode, 'startup_only_output_no_access_log': output}))
            self.assertIsNotNone(child.poll())
        try:
            process = start()
            self.client = httpx.Client(base_url=url, timeout=10)
            self.route(end=10)
            saved = self.control('save')['visible_state']
            self.route(begin=10, end=12)
            progressed = self.state()
            with closing(sqlite3.connect(Path(self.temp.name) / 'test.sqlite')) as db:
                sequence_before = db.execute('SELECT MAX(sequence) FROM events').fetchone()[0]
            self.client.close()
            stop(process)
            process = None
            process = start()
            self.client = httpx.Client(base_url=url, timeout=10)
            self.assertEqual(self.state(), progressed)
            restored = self.control('restore')['visible_state']
            self.assertEqual(gameplay(restored), gameplay(saved))
            self.assertEqual(restored['revision'], progressed['revision'] + 1)
            self.assertNotEqual(restored['generation'], progressed['generation'])
            with closing(sqlite3.connect(Path(self.temp.name) / 'test.sqlite')) as db:
                sequence_after = db.execute('SELECT MAX(sequence) FROM events').fetchone()[0]
            self.assertGreater(sequence_after, sequence_before)
            EXCHANGES.append({'test': self.id(), 'stage': 'event_sequence_across_real_restart', 'before': sequence_before, 'after': sequence_after})
        finally:
            if self.client is not direct_client:
                self.client.close()
            if process is not None:
                stop(process)
            self.client = direct_client
