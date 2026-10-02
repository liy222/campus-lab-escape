"""Backend owner local verification; no paid model calls or persisted credentials."""
import copy
import hashlib
import json
import sqlite3
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from backend.app.main import create_app
from backend.app.storage.sqlite import canonical, checksum

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'evidence' / 'backend' / 'm2-local-20261002-stable.json'
SCHEMA = json.loads((ROOT / 'contracts' / 'api.schema.json').read_text(encoding='utf-8'))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
CHECKS = []
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


def checked(name):
    CHECKS.append({'check': name, 'passed': True})


class Player:
    def __init__(self, client):
        self.client = client
        response = client.post('/api/sessions', json={})
        body = self.validate(response, 201)
        self.session = body['data']['session_id']
        self.headers = {'X-Session-Token': body['data']['token']}
        self.state = body['data']['visible_state']
        self.serial = 0

    def validate(self, response, status=200):
        assert response.status_code == status, (response.status_code, response.json().get('error'))
        body = response.json()
        VALIDATOR.validate(body)
        return body

    def request(self, tool=None, arguments=None, operation='actions', expected=None, raw=None, request_id=None):
        self.serial += 1
        if raw is None:
            raw = {'request_id': request_id or f'local_{self.serial}', 'revision': self.state['revision'], 'generation': self.state['generation']}
            if tool is not None:
                raw.update(tool=tool, arguments=arguments or {})
        response = self.client.post(f'/api/sessions/{self.session}/{operation}', headers=self.headers, json=raw)
        status = 200 if expected is None else (404 if expected == 'SAVE_NOT_FOUND' else 422 if expected in {'BAD_ARGUMENT', 'INVALID_TOOL'} else 409)
        body = self.validate(response, status)
        if expected:
            assert body['error']['code'] == expected, body['error']
        state = body['data']['visible_state'] if body['ok'] else body['visible_state']
        if state is not None:
            self.state = state
        return body, raw

    def read(self):
        self.state = self.validate(self.client.get(f'/api/sessions/{self.session}/state', headers=self.headers))['data']['visible_state']
        return self.state


def run():
    with tempfile.TemporaryDirectory(prefix='backend-m2-local-') as directory:
        db = Path(directory) / 'local.sqlite'
        client = TestClient(create_app(db))
        player = Player(client)
        assert player.state['save'] is None and player.state['revision'] == 0
        player.request('take', {'item_id': 'access_card'}, expected='NOT_VISIBLE')
        player.request('use_item', {'item_id': 'access_card', 'target_id': 'r1_door'}, expected='PRECONDITION_FAILED')
        player.request('move', {'destination_id': 'R2'}, expected='PRECONDITION_FAILED')
        player.request('move', {'destination_id': 'R3'}, expected='PRECONDITION_FAILED')
        player.request('submit_code', {'target_id': 'r1_cabinet', 'code': '999'}, expected='WRONG_CODE')
        player.request(operation='restore', expected='SAVE_NOT_FOUND')
        assert player.state['revision'] == 0
        checked('initial hidden item, missing card, locked/nonadjacent move, wrong code and missing save fail without progress')

        for index, (tool, arguments) in enumerate(ROUTE, 1):
            result, raw = player.request(tool, arguments)
            assert result['data']['receipt']['revision_after'] == index
            assert player.state['revision'] == index
            if index == 1:
                original_receipt = copy.deepcopy(result['data']['receipt'])
                replay, _ = player.request(raw=raw)
                assert replay['data']['replayed'] and replay['data']['receipt'] == original_receipt
                repeated, _ = player.request(tool, arguments)
                assert not repeated['data']['receipt']['changed'] and player.state['revision'] == 1
            if index == 4:
                player.request('take', arguments, expected='ALREADY_TAKEN')
            if index == 6:
                monitor, _ = player.request('inspect', {'object_id': 'r2_monitor'})
                assert monitor['data']['receipt']['observation'] == '当前无显示'
                assert monitor['data']['receipt']['new_clue_ids'] == [] and player.state['revision'] == 6
                player.request('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}, expected='PRECONDITION_FAILED')
                player.request('take', {'item_id': 'emergency_key'}, expected='NOT_VISIBLE')
                player.request('submit_code', {'target_id': 'r2_drawer', 'code': '724'}, expected='PRECONDITION_FAILED')
                player.request('move', {'destination_id': 'R3'}, expected='PRECONDITION_FAILED')
                checked('R2 unpowered screen discovers nothing, missing fuse/key and unpowered code reject')
            if index == 8:
                assert result['data']['receipt']['consumed_item_ids'] == ['fuse']
                assert 'fuse' not in [item['item_id'] for item in player.state['inventory']]
                assert 'r2_monitor_clue' not in [clue['clue_id'] for clue in player.state['clues']]
                player.request('take', {'item_id': 'fuse'}, expected='ALREADY_TAKEN')
                reused, _ = player.request('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'})
                assert not reused['data']['receipt']['changed'] and reused['data']['receipt']['consumed_item_ids'] == []
                wrong, failed_raw = player.request('submit_code', {'target_id': 'r2_drawer', 'code': '999'}, expected='WRONG_CODE')
                failure_id = wrong['event_id']
                assert '724' not in wrong['error']['message'] and all('724' not in obj['description'] for obj in wrong['visible_state']['objects'])
                checked('fuse consumed once; installed reuse unchanged; power does not auto-discover screen clue')
            if index == 9:
                failed_replay, _ = player.request(raw=failed_raw, expected='WRONG_CODE')
                assert failed_replay['event_id'] == failure_id and failed_replay['visible_state']['revision'] == 9
            if index == 12:
                player.request('take', {'item_id': 'emergency_key'}, expected='ALREADY_TAKEN')
            if index == 13:
                assert 'emergency_key' in [item['item_id'] for item in player.state['inventory']]
                assert result['data']['receipt']['consumed_item_ids'] == []
                checked('baseline key retained and wrong-code failure replay keeps original event with current projection')
            if index == 14:
                player.request('move', {'destination_id': 'EXIT'}, expected='PRECONDITION_FAILED')
                wrong, _ = player.request('submit_code', {'target_id': 'r3_panel', 'code': '999'}, expected='WRONG_CODE')
                assert '231' not in wrong['error']['message'] and all('231' not in obj['description'] for obj in wrong['visible_state']['objects'])
            checked(f'standard manual route step {index}, revision {index}')
        assert player.state['status'] == 'won' and player.state['room']['room_id'] == 'EXIT'
        assert len(player.state['clues']) == 6 and not player.state['objects'] and not player.state['exits']
        for tool, arguments in ROUTE[2:6]:
            player.request(tool, arguments, expected='GAME_FINISHED')
        player.request('inspect', {'object_id': 'exit_door'}, expected='NOT_VISIBLE')
        inventory, _ = player.request('get_inventory', {})
        assert not inventory['data']['receipt']['changed']
        checked('won blocks four progress tools; inventory remains readable and no objects can be inspected')

        saved, save_raw = player.request(operation='save')
        saved_summary = player.state['save']
        assert saved_summary['source_revision'] == 18 and player.state['revision'] == 18
        replay, _ = player.request(operation='save', raw=save_raw)
        assert replay['data']['replayed'] and player.state['save'] == saved_summary
        player.request('get_inventory', {}, request_id=save_raw['request_id'], expected='REQUEST_ID_CONFLICT')
        checked('save leaves revision unchanged, replays original slot and shares request namespace with actions')
        generation = player.state['generation']
        reset_result, reset_raw = player.request(operation='reset')
        assert player.state['revision'] == 19 and player.state['generation'] != generation and player.state['save'] == saved_summary
        assert player.state['room']['room_id'] == 'R1' and not player.state['inventory'] and not player.state['clues']
        player.request(operation='reset', raw=reset_raw, expected='STALE_GENERATION')
        player.request(operation='save', raw=save_raw, expected='STALE_GENERATION')
        failed, _ = player.request('take', {'item_id': 'access_card'}, expected='NOT_VISIBLE')
        assert failed['visible_state']['save'] == saved_summary
        checked('reset increments current revision, changes generation, clears progress and preserves slot; old retries rejected')

        rebuilt = TestClient(create_app(db))
        player.client = rebuilt
        assert player.read()['revision'] == 19 and player.state['save'] == saved_summary
        previous_generation = player.state['generation']
        restored, restore_raw = player.request(operation='restore')
        assert player.state['revision'] == 20 and player.state['generation'] != previous_generation
        assert player.state['status'] == 'won' and len(player.state['clues']) == 6 and player.state['save'] == saved_summary
        player.request(operation='restore', raw=restore_raw, expected='STALE_GENERATION')
        with closing(sqlite3.connect(db)) as connection, connection:
            events_before = connection.execute('SELECT MAX(sequence) FROM events').fetchone()[0]
            assert connection.execute('SELECT COUNT(*) FROM events WHERE operation IN (\'save\',\'reset\',\'restore\')').fetchone()[0] >= 4
        checked('rebuilt service retains session and slot; restore takes current revision plus one, fresh generation and ordered clues')

        # Corruption probes alter only the private temporary local slot, never project databases.
        with closing(sqlite3.connect(db)) as connection, connection:
            valid_snapshot = json.loads(connection.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (player.session,)).fetchone()[0])
        mutations = [
            ('bad hash', lambda s: s.update(checksum='0' * 64), 'INVALID_SNAPSHOT'),
            ('foreign owner', lambda s: s.update(session_id='another_session'), 'INVALID_SNAPSHOT'),
            ('schema mismatch', lambda s: s.update(schema_version='9.0.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('level mismatch', lambda s: s.update(level_version='2.0.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('duplicate inventory', lambda s: s['game_fields']['inventory'].append('access_card'), 'INVALID_SNAPSHOT'),
            ('unknown item', lambda s: s['game_fields']['inventory'].append('unknown_item'), 'INVALID_SNAPSHOT'),
            ('held installed fuse', lambda s: s['game_fields']['inventory'].append('fuse'), 'INVALID_SNAPSHOT'),
            ('baseline missing key', lambda s: s['game_fields']['inventory'].remove('emergency_key'), 'INVALID_SNAPSHOT'),
            ('status inconsistency', lambda s: s['game_fields'].update(status='playing'), 'INVALID_SNAPSHOT'),
            ('unknown flag', lambda s: s['game_fields']['flags'].update(won=True), 'INVALID_SNAPSHOT'),
            ('wrong flag type', lambda s: s['game_fields']['flags'].update(power_on=1), 'INVALID_SNAPSHOT'),
            ('extra revision field', lambda s: s['game_fields'].update(revision=0), 'INVALID_SNAPSHOT'),
            ('unopened cabinet with card', lambda s: s['game_fields']['opened_containers'].remove('r1_cabinet'), 'INVALID_SNAPSHOT'),
            ('unopened drawer with key', lambda s: s['game_fields']['opened_containers'].remove('r2_drawer'), 'INVALID_SNAPSHOT'),
            ('unpowered screen clue', lambda s: s['game_fields']['flags'].update(power_on=False), 'INVALID_SNAPSHOT'),
            ('missing field', lambda s: s['game_fields'].pop('inventory'), 'INVALID_SNAPSHOT'),
            ('wrong saved timestamp', lambda s: s.update(saved_at='yesterday'), 'INVALID_SNAPSHOT'),
        ]
        for name, mutate, expected in mutations:
            corrupt = copy.deepcopy(valid_snapshot)
            mutate(corrupt)
            if name != 'bad hash':
                corrupt['checksum'] = checksum(corrupt)
            with closing(sqlite3.connect(db)) as connection, connection:
                connection.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (canonical(corrupt), player.session))
            before = copy.deepcopy(player.read())
            failed, raw = player.request(operation='restore', expected=expected)
            first_event = failed['event_id']
            assert player.state == before
            replayed, _ = player.request(operation='restore', raw=raw, expected=expected)
            assert replayed['event_id'] == first_event and player.state == before
            checked('corrupt snapshot rejected and immutable failure replay: ' + name)
        with closing(sqlite3.connect(db)) as connection, connection:
            connection.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (canonical(valid_snapshot), player.session))
        player.request(operation='reset')
        player.request(operation='restore')
        with closing(sqlite3.connect(db)) as connection, connection:
            assert connection.execute('SELECT MAX(sequence) FROM events').fetchone()[0] > events_before
        checked('event sequence continues across controls and corruption rejections')

        other = Player(rebuilt)
        assert other.state['save'] is None
        other.request(operation='restore', expected='SAVE_NOT_FOUND')
        for operation in ('actions', 'save', 'reset', 'restore'):
            raw = {'request_id': 'foreign', 'revision': player.state['revision'], 'generation': player.state['generation']}
            if operation == 'actions':
                raw.update(tool='get_inventory', arguments={})
            body = other.validate(rebuilt.post(f'/api/sessions/{player.session}/{operation}', headers=other.headers, json=raw), 403)
            assert body['visible_state'] is None and body['error']['code'] == 'FORBIDDEN_SESSION'
        checked('single slot isolation and all four mutations reject foreign capabilities')
        for operation in ('save', 'reset', 'restore'):
            raw = {'request_id': 'invalid_' + operation, 'revision': other.state['revision'], 'generation': other.state['generation'], 'game_fields': {'status': 'won'}}
            failed, _ = other.request(operation=operation, raw=raw, expected='BAD_ARGUMENT')
            assert failed['visible_state'] is None and other.state['revision'] == 0
        other.request('get_inventory', {'flags': {'power_on': True}}, expected='BAD_ARGUMENT')
        checked('strict control/action input forbids uploaded snapshots and client flags')

        concurrent = Player(rebuilt)
        requests = [{'request_id': f'parallel_{index}', 'revision': 0, 'generation': concurrent.state['generation'], 'tool': 'inspect', 'arguments': {'object_id': object_id}} for index, object_id in enumerate(('r1_note', 'r1_cabinet'))]
        def send(raw):
            response = rebuilt.post(f'/api/sessions/{concurrent.session}/actions', headers=concurrent.headers, json=raw)
            body = response.json()
            VALIDATOR.validate(body)
            return response.status_code, body
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(send, requests))
        assert sorted(status for status, _ in responses) == [200, 409]
        assert [body['error']['code'] for _, body in responses if not body['ok']] == ['STALE_STATE']
        assert concurrent.read()['revision'] == 1
        checked('same-version concurrent changed actions commit once and reject loser as STALE_STATE')
        simultaneous = {'request_id': 'same_request', 'revision': 1, 'generation': concurrent.state['generation'], 'tool': 'get_inventory', 'arguments': {}}
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(send, [simultaneous, simultaneous]))
        assert all(status == 200 for status, _ in responses)
        assert sorted(body['data']['replayed'] for _, body in responses) == [False, True]
        assert responses[0][1]['data']['receipt'] == responses[1][1]['data']['receipt']
        checked('concurrent same request has one immutable receipt and one replay')

        # Save replay returns current slot, including later overwrite, not old summary.
        saved, original_save = concurrent.request(operation='save')
        old_summary = concurrent.state['save']
        new_object = 'r1_cabinet' if concurrent.state['clues'][0]['object_id'] == 'r1_note' else 'r1_note'
        concurrent.request('inspect', {'object_id': new_object})
        concurrent.request(operation='save')
        current_summary = concurrent.state['save']
        assert current_summary != old_summary
        replay, _ = concurrent.request(operation='save', raw=original_save)
        assert replay['data']['replayed'] and replay['data']['visible_state']['save'] == current_summary
        checked('save replay projects current overwritten slot, not stale saved summary')
        client.close()
        rebuilt.close()


if __name__ == '__main__':
    started = datetime.now(timezone.utc).isoformat()
    result = {'scope': 'Backend owner local verification for T09/T11/T12; not independent T13 QA', 'command': r'C:\Users\liyh\.conda\envs\1\python.exe -m evidence.backend.m2_local', 'started_at': started, 'paid_model_calls': 0, 'checks': CHECKS}
    try:
        run()
    except Exception as error:
        result.update(exit_code=1, failure_type=type(error).__name__)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
    else:
        result.update(exit_code=0, finished_at=datetime.now(timezone.utc).isoformat(), source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / 'backend/app/domain/rules.py', ROOT / 'backend/app/storage/sqlite.py', ROOT / 'backend/app/api/routes.py')})
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'PASS: {len(CHECKS)} local checks; 18-step route revision18; no paid model calls')



