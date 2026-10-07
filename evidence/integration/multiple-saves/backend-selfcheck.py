"""Owner archive self-check using isolated temporary DBs; not formal QA."""
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
temporary = tempfile.TemporaryDirectory(prefix='campus-multiple-saves-')
os.environ['SQLITE_PATH'] = str(Path(temporary.name) / 'module.sqlite')
os.environ['GAMEPLAY_VERSION'] = 'v3.4'

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from backend.app.main import create_app
from backend.app.storage.sqlite import checksum

validator = Draft202012Validator(json.loads((ROOT / 'contracts/api.schema.json').read_text(encoding='utf-8')), format_checker=FormatChecker())
checks = []


class Session:
    def __init__(self, name, version='v3.4'):
        self.path, self.version = Path(temporary.name) / (name + '.sqlite'), version
        self.app = create_app(db_path=self.path, gameplay_version=version)
        self.client = TestClient(self.app)
        created = self.client.post('/api/sessions', json={})
        assert created.status_code == 201
        validator.validate(created.json())
        data = created.json()['data']
        self.id, self.headers, self.state = data['session_id'], {'X-Session-Token': data['token']}, data['visible_state']

    def version_body(self):
        return {'request_id': uuid4().hex, 'revision': self.state['revision'], 'generation': self.state['generation']}

    def call(self, suffix, extra=None, *, raw=None, code=200, error=None, method='POST', headers=None):
        body = raw if raw is not None else {**self.version_body(), **(extra or {})}
        if method == 'GET':
            response = self.client.get(f'/api/sessions/{self.id}/{suffix}', headers=headers or self.headers)
        else:
            response = self.client.post(f'/api/sessions/{self.id}/{suffix}', headers=headers or self.headers, json=body)
        payload = response.json()
        assert response.status_code == code, (suffix, response.status_code, payload.get('error'))
        validator.validate(payload)
        if error:
            assert payload['error']['code'] == error
        projection = payload.get('data', {}).get('visible_state') or payload.get('visible_state')
        if projection:
            self.state = projection
        checks.append({'route': suffix if not suffix.startswith('saves/') else 'saves/{id}/restore', 'http': code, 'error': error})
        return payload, body

    def slots(self):
        return self.call('saves', method='GET')[0]['data']['slots']

    def save(self, name=None):
        return self.call('saves', {} if name is None else {'name': name}, code=201)

    def restore(self, save_id, **kwargs):
        return self.call(f'saves/{save_id}/restore', **kwargs)

    def action(self, tool, args, **kwargs):
        return self.call('actions', {'tool': tool, 'arguments': args}, **kwargs)

    def inspect(self, target):
        return self.action('inspect', {'object_id': target})

    def interact(self, target):
        return self.action('interact', {'target_id': target})

    def reopen(self):
        self.client.close()
        self.app = create_app(db_path=self.path, gameplay_version=self.version)
        self.client = TestClient(self.app)
        payload = self.client.get(f'/api/sessions/{self.id}/state', headers=self.headers)
        assert payload.status_code == 200
        validator.validate(payload.json())
        self.state = payload.json()['data']['visible_state']

    def rows(self, table):
        with closing(sqlite3.connect(self.path)) as connection:
            return connection.execute(f'SELECT * FROM {table}').fetchall()


game = Session('archives')
assert game.slots() == []
initial = game.state
a, create_a = game.save('开始时刻')
a_id = a['data']['slot']['save_id']
assert a['data']['slot']['clues_found'] == 0 and game.state == initial
game.call('saves', raw=create_a, code=201)
assert len(game.slots()) == 1
game.call('saves', raw={**create_a, 'name': '替换名称'}, code=409, error='REQUEST_ID_CONFLICT')
for name in ('x' * 41, 1, None):
    game.call('saves', {'name': name}, code=422, error='BAD_ARGUMENT')
game.call('saves', {'extra': True}, code=422, error='BAD_ARGUMENT')
game.inspect('r1_clock')
game.inspect('r1_record')
game.inspect('r1_cabinet')
game.action('submit_code', {'target_id': 'r1_cabinet', 'code': '0000'}, code=409, error='WRONG_CODE')
b, _ = game.save('推理时刻')
b_id = b['data']['slot']['save_id']
b_stats = game.state['statistics']
assert b_stats['mistake_count'] == 1 and b['data']['slot']['clues_found'] == 2
game.call('save')
old_rows, old_projection = game.rows('saves'), game.state['save']
with patch('backend.app.storage.sqlite.utc_now', lambda: '2026-10-07T12:00:00Z'):
    c, _ = game.save('同名时刻')
    d, _ = game.save('同名时刻')
assert c['data']['slot']['save_id'] != d['data']['slot']['save_id']
assert game.rows('saves') == old_rows and game.state['save'] == old_projection
ordered = game.slots()
pair = [slot['save_id'] for slot in ordered if slot['name'] == '同名时刻']
assert pair == [d['data']['slot']['save_id'], c['data']['slot']['save_id']]
assert ordered[-1]['save_id'] == 'legacy' and ordered[-1]['room_id'] is None and ordered[-1]['clues_found'] is None
game.call('reset')
assert len(game.slots()) == 5 and game.state['statistics']['mistake_count'] == 0
create_replay, _ = game.call('saves', raw=create_a, code=201)
assert create_replay['data']['slot']['save_id'] == a_id and create_replay['data']['replayed']
assert len(game.slots()) == 5
before = game.state
loaded, restore_a = game.restore(a_id)
assert game.state['revision'] == before['revision'] + 1 and game.state['generation'] != before['generation']
assert game.state['statistics']['mistake_count'] == 0 and game.state['clues'] == []
game.inspect('r1_plaque')
after_action = game.state
replay, _ = game.restore(a_id, raw=restore_a)
assert replay['event_id'] == loaded['event_id'] and replay['data']['replayed'] and game.state == after_action
game.restore(b_id, raw=restore_a, code=409, error='REQUEST_ID_CONFLICT')
game.restore(b_id, raw={**restore_a, 'request_id': uuid4().hex}, code=409, error='STALE_GENERATION')
game.restore(b_id)
assert game.state['statistics'] == b_stats and len(game.state['clues']) == 2
game.restore('legacy')
assert game.state['statistics'] == b_stats and game.rows('saves') == old_rows
game.reopen()
assert len(game.slots()) == 5 and game.state['statistics'] == b_stats
# Real visible state/physical item route to a partial circuit archive.
game.action('submit_code', {'target_id': 'r1_cabinet', 'code': '4217'})
game.interact('r1_cabinet')
game.inspect('r1_fuse')
game.action('take', {'item_id': 'fuse'})
game.inspect('r1_door')
game.interact('r1_door')
game.action('move', {'destination_id': 'R2'})
game.inspect('r2_powerbox')
game.interact('r2_powerbox')
game.interact('r2_powerbox')
game.action('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'})
game.action('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': 'c00'})
partial = game.state['minigames']['circuit']
partial_reply, _ = game.save('部分线路')
partial_id = partial_reply['data']['slot']['save_id']
game.action('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': 'c11'})
game.restore(a_id)
game.restore(partial_id)
assert game.state['minigames']['circuit'] == partial
game.reopen()
assert game.state['minigames']['circuit'] == partial and len(game.slots()) == 6
for save_id in ('missing',):
    before = game.state
    game.restore(save_id, code=404, error='SAVE_NOT_FOUND')
    assert game.state == before
other = Session('other')
other.restore(a_id, code=404, error='SAVE_NOT_FOUND')
before = game.state
game.call('saves', method='GET', headers=other.headers, code=403, error='FORBIDDEN_SESSION')
assert game.state == before
# Corruption/version boundary on a temporary archive only; no real history DB.
with closing(sqlite3.connect(game.path)) as connection:
    row = connection.execute('SELECT snapshot_json FROM save_slots WHERE save_id=?', (partial_id,)).fetchone()
    original_snapshot = row[0]
    connection.execute('UPDATE save_slots SET snapshot_json=? WHERE save_id=?', ('{}', partial_id))
    connection.commit()
before = game.state
game.restore(partial_id, code=409, error='INVALID_SNAPSHOT')
assert game.state == before
with closing(sqlite3.connect(game.path)) as connection:
    changed = json.loads(original_snapshot)
    changed['level_version'] = '3.3.0'
    changed['checksum'] = checksum(changed)
    connection.execute('UPDATE save_slots SET snapshot_json=? WHERE save_id=?', (json.dumps(changed), partial_id))
    connection.commit()
game.restore(partial_id, code=409, error='SNAPSHOT_VERSION_MISMATCH')
assert game.state == before
with closing(sqlite3.connect(game.path)) as connection:
    connection.execute('UPDATE save_slots SET snapshot_json=? WHERE save_id=?', (original_snapshot, partial_id))
    connection.commit()
for version in ('legacy', 'v3.1', 'v3.2', 'v3.3'):
    old = Session('old-' + version, version)
    reply, _ = old.save()
    old_id = reply['data']['slot']['save_id']
    old.call('reset')
    old.restore(old_id)
    old.call('save')
    assert old.slots()[-1]['save_id'] == 'legacy'
    old.client.close()
game.client.close()
other.client.close()
temporary.cleanup()
paths = ['backend/app/domain/save_models.py', 'backend/app/storage/saves.py', 'backend/app/storage/sqlite.py',
         'backend/app/api/routes.py', 'contracts/build_contracts.py', 'contracts/check_contracts.py', 'contracts/api.schema.json',
         'contracts/routes.json', 'docs/SPEC.md', 'evidence/integration/multiple-saves/backend-selfcheck.py']
report = {'owner': 'Backend', 'status': 'SOURCE STOP; targeted Owner self-check passed; independent QA pending',
          'files': paths, 'raw_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths},
          'commands': [{'command': 'C:/Users/liyh/.conda/envs/1/python.exe contracts/build_contracts.py', 'exit': 0},
                       {'command': 'C:/Users/liyh/.conda/envs/1/python.exe contracts/check_contracts.py --output evidence/integration/multiple-saves/contracts-owner.json', 'exit': 0},
                       {'command': 'C:/Users/liyh/.conda/envs/1/python.exe evidence/integration/multiple-saves/backend-selfcheck.py', 'exit': 1,
                        'result': 'Initial self-check assertions completed, temporary cleanup failed WinError32: self-check sqlite context managers committed but did not close handles. Owner harness repaired with explicit closing; product APIs did not fail.'},
                       {'command': 'C:/Users/liyh/.conda/envs/1/python.exe evidence/integration/multiple-saves/backend-selfcheck.py', 'exit': 0}],
          'evidence': ['evidence/integration/multiple-saves/backend.json', 'evidence/integration/multiple-saves/contracts-owner.json'],
          'checks': checks,
          'summary': ['strict JSON Schema validates all API responses', 'distinct immutable time slots with same-name/time persistence',
                      'new save does not alter old slot/state', 'selected restore recovers exact stats/partial rotations with rev+1/new generation',
                      'completed save/restore receipt replay after generation change has no duplicate/reapply', 'old slot listing/restore compatible',
                      'reset/reopen retain archives', 'unknown/foreign/corrupt/cross-version/stale/conflict/invalid-name inputs preserve live state',
                      'same routes work for explicit legacy/3.1/3.2/3.3 entries'],
          'limitations': ['Owner targeted self-check, not independent formal QA', 'no whole gameplay regression/browser/build/OS process restart',
                          'AI/proposal invalidation reuses existing generation and invalidate_pending, independent QA follows',
                          'temporary databases only; no historical user database access', 'no paid calls/commit/spawn/visual work']}
(ROOT / 'evidence/integration/multiple-saves/backend.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'api_checks': len(checks), 'evidence': report['evidence']}, ensure_ascii=False))
