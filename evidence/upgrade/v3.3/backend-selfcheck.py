"""Backend Owner targeted self-check, temporary databases only; not formal QA."""
import hashlib
import itertools
import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ['GAMEPLAY_VERSION'] = 'v3.3'
temporary = tempfile.TemporaryDirectory(prefix='campus-v33-backend-')
os.environ['SQLITE_PATH'] = str(Path(temporary.name) / 'module-import.sqlite')

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from backend.app.main import create_app
from backend.app.domain import circuit, mini_rules
from backend.app.storage.sqlite import select_rules

validator = Draft202012Validator(json.loads((ROOT / 'contracts/api.schema.json').read_text(encoding='utf-8')))
checks = []
db = Path(temporary.name) / 'selfcheck.sqlite'
client = TestClient(create_app(db_path=db, gameplay_version='v3.3'))
created = client.post('/api/sessions', json={})
assert created.status_code == 201
validator.validate(created.json())
credentials = created.json()['data']
session = credentials['session_id']
headers = {'X-Session-Token': credentials['token']}
state = credentials['visible_state']


def call(tool, arguments=None, code=200, error=None):
    global state
    raw = {'request_id': uuid4().hex, 'revision': state['revision'], 'generation': state['generation']}
    if tool not in {'save', 'restore', 'reset'}:
        raw.update(tool=tool, arguments=arguments or {})
    response = client.post(f'/api/sessions/{session}/' + (tool if tool in {'save', 'restore', 'reset'} else 'actions'), headers=headers, json=raw)
    assert response.status_code == code, (tool, response.status_code, response.json())
    body = response.json()
    validator.validate(body)
    if error:
        assert body['error']['code'] == error, body
    projected = body.get('data', {}).get('visible_state') or body.get('visible_state')
    if projected:
        state = projected
    checks.append({'tool': tool, 'http': code, 'error': error})
    return body


def inspect(target):
    return call('inspect', {'object_id': target})


def interact(target):
    return call('interact', {'target_id': target})


def unchanged(tool, arguments, error='PRECONDITION_FAILED', code=409):
    before = dict(state)
    call(tool, arguments, code, error)
    assert state == before


assert state['minigames'] == {'circuit': None, 'sequence': None}
assert [select_rules(version).LEVEL_VERSION for version in ('legacy', 'v3.1', 'v3.2', 'v3.3', 'upgrade')] == ['2.0.0', '3.1.0', '3.2.0', '3.3.0', '3.3.0']
unchanged('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': 'c00'}, 'NOT_VISIBLE')
for target in ('r1_clock', 'r1_record', 'r1_plaque', 'sample_slide'):
    inspect(target)
call('take', {'item_id': 'sample_slide'})
inspect('r1_microscope')
call('use_item', {'item_id': 'sample_slide', 'target_id': 'r1_microscope'})
inspect('r1_microscope')
inspect('r1_cabinet')
call('submit_code', {'target_id': 'r1_cabinet', 'code': '4217'})
interact('r1_cabinet')
inspect('r1_symbols')
inspect('r1_fuse')
call('take', {'item_id': 'fuse'})
inspect('r1_door')
interact('r1_door')
call('move', {'destination_id': 'R2'})
inspect('r2_powerbox')
interact('r2_powerbox')
interact('r2_powerbox')
assert state['minigames']['circuit'] is None
call('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'})
assert state['minigames']['circuit']['status'] == 'editing'
unchanged('interact', {'target_id': 'r2_powerbox'})
unchanged('submit_circuit', {'target_id': 'r2_powerbox'}, 'WRONG_CODE')
unchanged('submit_circuit', {'target_id': 'r2_powerbox', 'solved': True}, 'BAD_ARGUMENT', 422)
unchanged('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': 'bad'}, 'BAD_ARGUMENT', 422)
call('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': 'c00'})
partial = state['minigames']['circuit']
call('save')
call('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': 'c11'})
old_generation = state['generation']
call('restore')
assert state['generation'] != old_generation and state['minigames']['circuit'] == partial
client.close()
client = TestClient(create_app(db_path=db, gameplay_version='v3.3'))
reopened = client.get(f'/api/sessions/{session}/state', headers=headers)
assert reopened.status_code == 200
validator.validate(reopened.json())
state = reopened.json()['data']['visible_state']
assert state['minigames']['circuit'] == partial
# Exhaustive candidate search verifies connectivity accepts more than one layout.
solutions = (values for values in itertools.product(range(4), repeat=9) if circuit.connected(values))
first, second = next(solutions), next(solutions)
assert first != second and circuit.connected(first) and circuit.connected(second)
half_turn = list(second)
half_turn[0] = (half_turn[0] + 2) % 4
assert half_turn != list(second) and circuit.connected(half_turn)
for index, wanted in enumerate(half_turn):
    module = state['minigames']['circuit']['modules'][index]
    for _ in range((wanted - module['rotation']) % 4):
        call('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': module['module_id']})
call('submit_circuit', {'target_id': 'r2_powerbox'})
assert state['device_states']['powerbox'] == 'CIRCUIT_READY' and not state['progress']['power_on']
unchanged('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': 'c00'})
unchanged('submit_circuit', {'target_id': 'r2_powerbox'})
interact('r2_powerbox')
assert state['progress']['power_on']
inspect('r2_monitor')
interact('r2_monitor')
interact('r2_monitor')
inspect('r2_maintenance')
call('submit_login', {'target_id': 'r2_monitor', 'username': 'LAB-42', 'password': '2117'})
interact('r2_monitor')
for item in ('research_strip', 'access_card'):
    inspect(item)
    call('take', {'item_id': item})
inspect('r2_door')
interact('r2_door')
call('move', {'destination_id': 'R3'})
assert state['minigames'] == {'circuit': None, 'sequence': None}
inspect('r3_legend')
assert '设备数字' not in state['clues'][-1]['text']
inspect('r3_panel')
inspect('exit_door')
call('use_item', {'item_id': 'access_card', 'target_id': 'exit_door'})
interact('exit_door')
sequence = ['ventilation', 'cooling', 'lighting', 'safety']
unchanged('submit_sequence', {'target_id': 'r3_panel', 'device_ids': sequence})
call('use_item', {'item_id': 'research_strip', 'target_id': 'r3_panel'})
assert state['minigames']['sequence']['status'] == 'editing'
unchanged('submit_code', {'target_id': 'r3_panel', 'code': '4792'})
unchanged('submit_sequence', {'target_id': 'r3_panel', 'device_ids': ['cooling', 'lighting', 'safety', 'ventilation']}, 'WRONG_CODE')
unchanged('submit_sequence', {'target_id': 'r3_panel', 'device_ids': ['cooling'] * 4}, 'BAD_ARGUMENT', 422)
call('submit_sequence', {'target_id': 'r3_panel', 'device_ids': sequence})
assert state['progress']['check_done']
unchanged('submit_sequence', {'target_id': 'r3_panel', 'device_ids': sequence})
call('save')
call('reset')
call('restore')
assert state['progress']['check_done'] and state['minigames']['sequence']['status'] == 'completed'
interact('exit_door')
interact('exit_door')
call('move', {'destination_id': 'EXIT'})
assert state['status'] == 'won' and state['minigames'] == {'circuit': None, 'sequence': None}
call('save')
client.close()
client = TestClient(create_app(db_path=db, gameplay_version='v3.3'))
final = client.get(f'/api/sessions/{session}/state', headers=headers)
validator.validate(final.json())
assert final.json()['data']['visible_state']['status'] == 'won'
client.close()
temporary.cleanup()
paths = ['backend/app/domain/mini_models.py', 'backend/app/domain/circuit.py', 'backend/app/domain/mini_rules.py',
         'backend/app/storage/sqlite.py', 'backend/app/main.py', 'backend/app/ai/runtime.py',
         'contracts/build_contracts.py', 'contracts/api.schema.json', 'contracts/routes.json',
         'docs/SPEC.md', 'docs/level_design.md', 'evidence/upgrade/v3.3/backend-selfcheck.py']
report = {'owner': 'Backend', 'status': 'targeted self-check passed; SOURCE STOP, independent QA pending',
          'files': paths, 'raw_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths},
          'commands': [{'command': 'C:/Users/liyh/.conda/envs/1/python.exe contracts/build_contracts.py', 'exit': 0},
                       {'command': 'C:/Users/liyh/.conda/envs/1/python.exe evidence/upgrade/v3.3/backend-selfcheck.py', 'exit': 0},
                       {'command': 'git diff --check -- <Backend owned paths>; git diff --stat -- <old rule/provider paths>',
                        'exit': 1, 'result': 'Git treated this invocation as --no-index; no repository diff obtained. Main owns final Git validation.'}],
          'evidence': 'evidence/upgrade/v3.3/backend.json', 'checks': checks,
          'summary': ['full manual API route won', 'strict public schema validates every response',
                      'partial circuit save/restore/reopen', 'completed sequence save/reset/restore and won-state reopen',
                      'alternate valid port-connectivity layouts, explicitly c00 I rotated 180 degrees accepted via API', 'manual bypass/wrong/extra-field/frozen-board rejection',
                      'explicit old-version selectors retained'],
          'limits': ['Owner self-check, not independent formal QA', 'no browser/build/full regression run',
                     'application reopen in same process; OS restart reserved for QA', 'temporary databases only, no paid calls',
                     'no commit or further agents']}
(ROOT / 'evidence/upgrade/v3.3/backend.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'api_checks': len(checks), 'evidence': report['evidence']}, ensure_ascii=False))
