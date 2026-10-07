"""Owner-directed checks only; isolated DBs, no real provider or credentials."""
import asyncio
import copy
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

ROUTE = [
 ('inspect', {'object_id': 'r1_clock'}), ('inspect', {'object_id': 'r1_record'}), ('inspect', {'object_id': 'r1_plaque'}),
 ('inspect', {'object_id': 'sample_slide'}), ('take', {'item_id': 'sample_slide'}), ('inspect', {'object_id': 'r1_microscope'}),
 ('use_item', {'item_id': 'sample_slide', 'target_id': 'r1_microscope'}), ('inspect', {'object_id': 'r1_microscope'}),
 ('inspect', {'object_id': 'r1_cabinet'}), ('submit_code', {'target_id': 'r1_cabinet', 'code': '4217'}), ('interact', {'target_id': 'r1_cabinet'}),
 ('inspect', {'object_id': 'r1_fuse'}), ('take', {'item_id': 'fuse'}), ('inspect', {'object_id': 'r1_symbols'}),
 ('inspect', {'object_id': 'r1_door'}), ('interact', {'target_id': 'r1_door'}), ('move', {'destination_id': 'R2'}),
 ('inspect', {'object_id': 'r2_powerbox'}), ('interact', {'target_id': 'r2_powerbox'}), ('interact', {'target_id': 'r2_powerbox'}),
 ('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}), ('interact', {'target_id': 'r2_powerbox'}), ('interact', {'target_id': 'r2_powerbox'}),
 ('inspect', {'object_id': 'r2_monitor'}), ('interact', {'target_id': 'r2_monitor'}), ('interact', {'target_id': 'r2_monitor'}),
 ('inspect', {'object_id': 'r2_maintenance'}), ('submit_login', {'target_id': 'r2_monitor', 'username': 'LAB-42', 'password': '2117'}),
 ('interact', {'target_id': 'r2_monitor'}), ('inspect', {'object_id': 'research_strip'}), ('take', {'item_id': 'research_strip'}),
 ('inspect', {'object_id': 'access_card'}), ('take', {'item_id': 'access_card'}),
 ('inspect', {'object_id': 'r2_door'}), ('interact', {'target_id': 'r2_door'}), ('move', {'destination_id': 'R3'}),
 ('inspect', {'object_id': 'r3_legend'}), ('inspect', {'object_id': 'r3_panel'}), ('inspect', {'object_id': 'exit_door'}),
 ('use_item', {'item_id': 'access_card', 'target_id': 'exit_door'}), ('interact', {'target_id': 'exit_door'}),
 ('use_item', {'item_id': 'research_strip', 'target_id': 'r3_panel'}), ('submit_code', {'target_id': 'r3_panel', 'code': '4792'}),
 ('interact', {'target_id': 'exit_door'}), ('interact', {'target_id': 'exit_door'}), ('move', {'destination_id': 'EXIT'})]

def semantic(state):
    return {key: value for key, value in state.items() if key not in {'revision', 'generation', 'save'}}

with tempfile.TemporaryDirectory(prefix='campus-v32-owner-') as temporary:
    os.environ['SQLITE_PATH'] = str(Path(temporary) / 'module.sqlite')
    os.environ['AI_PROVIDER'] = 'mock'
    from app.main import create_app
    from app.storage.sqlite import canonical, select_rules
    from app.domain import puzzle_rules
    from app.ai.runtime import Runtime
    from app.ai.types import TurnStart, Snapshot, ReadResult, CheckResult
    from app.ai.provider import ProviderResult
    schema = json.loads((ROOT / 'contracts/api.schema.json').read_text(encoding='utf-8'))
    validator = Draft202012Validator(schema)
    path = Path(temporary) / 'route.sqlite'
    application = create_app(path, gameplay_version='upgrade')
    client = TestClient(application)
    created = client.post('/api/sessions', json={})
    assert created.status_code == 201
    validator.validate(created.json())
    data = created.json()['data']
    sid, headers, state = data['session_id'], {'X-Session-Token': data['token']}, data['visible_state']
    assert state['schema_version'] == '1.2.0' and state['level_version'] == '3.2.0'
    assert not state['clues'] and not any(code in json.dumps(state) for code in ('4217', '2117', '4792'))
    count = {'actions': 0, 'save_reopen_restore': 0, 'rejects': 0}
    stages = {field: {value} for field, value in state['device_states'].items()}

    def request(operation, extra=None, expected=200, code=None):
        global state
        before = copy.deepcopy(state)
        body = {'request_id': uuid4().hex, 'revision': state['revision'], 'generation': state['generation'], **(extra or {})}
        result = client.post(f'/api/sessions/{sid}/{operation}', json=body, headers=headers)
        assert result.status_code == expected, (operation, extra, result.status_code, result.json())
        validator.validate(result.json())
        if code:
            assert result.json()['error']['code'] == code, result.json()
            # Format rejection may intentionally omit projection; read authoritative state.
            assert client.get(f'/api/sessions/{sid}/state', headers=headers).json()['data']['visible_state'] == before
            count['rejects'] += 1
        else:
            state = result.json()['data']['visible_state']
        return result.json()

    for index, (tool, args) in enumerate(ROUTE):
        if index == 0:
            request('actions', {'tool': 'inspect', 'arguments': {'object_id': 'research_strip'}}, 409, 'NOT_VISIBLE')
        if index == 6:
            assert 'r1_sample_clue' not in {clue['clue_id'] for clue in state['clues']}
            request('actions', {'tool': 'use_item', 'arguments': {'item_id': 'sample_slide', 'target_id': 'r1_cabinet'}}, 409, 'PRECONDITION_FAILED')
        if tool == 'submit_login':
            for username, password, expected, code in [('LAB-42', '0000', 409, 'WRONG_CODE'), ('LAB-42 ', '2117', 422, 'BAD_ARGUMENT'), ('LAB-42', '21:17', 422, 'BAD_ARGUMENT')]:
                request('actions', {'tool': tool, 'arguments': {'target_id': 'r2_monitor', 'username': username, 'password': password}}, expected, code)
            request('actions', {'tool': tool, 'arguments': {**args, 'extra': True}}, 422, 'BAD_ARGUMENT')
        response = request('actions', {'tool': tool, 'arguments': args})
        assert response['data']['receipt']['changed']
        count['actions'] += 1
        for field, value in state['device_states'].items():
            stages[field].add(value)
        # Every actual puzzle step is saved, DB reopened, and restored in a new generation.
        request('save')
        saved = copy.deepcopy(state)
        application = create_app(path, gameplay_version='v3.2')
        client = TestClient(application)
        reopened = client.get(f'/api/sessions/{sid}/state', headers=headers)
        assert reopened.status_code == 200
        validator.validate(reopened.json())
        assert reopened.json()['data']['visible_state'] == saved
        restored = request('restore')
        assert semantic(state) == semantic(saved) and state['generation'] != saved['generation']
        count['save_reopen_restore'] += 1
    assert state['status'] == 'won' and [item['item_id'] for item in state['inventory']] == ['access_card']
    assert len(state['clues']) == 8
    assert sum(map(len, stages.values())) == 20
    store = application.state.store
    with closing(store.connect()) as connection:
        snapshot = json.loads(connection.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (sid,)).fetchone()[0])
    # Checksum-valid corruption and cross-version snapshots must not overwrite live state or saved content.
    mutations = [
        lambda s: s['game_fields'].pop('puzzle_states'),
        lambda s: s['game_fields']['puzzle_states'].pop('panel'),
        lambda s: s['game_fields'].pop('device_states'),
        lambda s: s['game_fields'].pop('taken_item_ids'),
        lambda s: s['game_fields']['observed_object_ids'].remove('r3_panel'),
        lambda s: s['game_fields']['consumed_item_ids'].remove('research_strip'),
        lambda s: s['game_fields']['puzzle_states'].update(microscope='SAMPLE_READ'),
        lambda s: s.update(level_version='3.1.0'),
    ]
    for mutation in mutations:
        corrupt = copy.deepcopy(snapshot)
        mutation(corrupt)
        corrupt['checksum'] = hashlib.sha256(canonical({key: value for key, value in corrupt.items() if key != 'checksum'}).encode()).hexdigest()
        raw = canonical(corrupt)
        with closing(store.connect()) as connection:
            connection.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (raw, sid))
        request('restore', expected=409, code='SNAPSHOT_VERSION_MISMATCH' if corrupt['level_version'] != '3.2.0' else 'INVALID_SNAPSHOT')
        with closing(store.connect()) as connection:
            assert connection.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (sid,)).fetchone()[0] == raw
    for version, expected in [('legacy', '2.0.0'), ('v3.1', '3.1.0')]:
        other = TestClient(create_app(Path(temporary) / f'{version}.sqlite', gameplay_version=version)).post('/api/sessions', json={})
        assert other.status_code == 201
        validator.validate(other.json())
        assert other.json()['data']['visible_state']['level_version'] == expected
    # Early cross-room exploration requires ordinary doors only, no power or login.
    early = puzzle_rules.initial_state()
    for tool, args in [('inspect', {'object_id': 'r1_door'}), ('interact', {'target_id': 'r1_door'}), ('move', {'destination_id': 'R2'}), ('inspect', {'object_id': 'r2_door'}), ('interact', {'target_id': 'r2_door'}), ('move', {'destination_id': 'R3'}), ('inspect', {'object_id': 'r3_legend'}), ('move', {'destination_id': 'R2'}), ('move', {'destination_id': 'R1'})]:
        early, _ = puzzle_rules.apply_action(early, tool, args)
    assert early.device_states.computer == 'OFF' and not early.flags['power_on']

    class ReadProvider:
        provider_name, model_name = 'mock', 'owner-read-script'
        def __init__(self, target):
            self.target, self.called = target, False
        async def complete(self, *args, **kwargs):
            if not self.called:
                self.called = True
                calls = ({'id': 'owner_inspect', 'type': 'function', 'function': {'name': 'inspect', 'arguments': json.dumps({'object_id': self.target})}},)
                return ProviderResult(None, calls, None, 'mock', self.model_name, self.model_name, 'tool_calls')
            return ProviderResult(json.dumps({'answer': '已观察当前对象。', 'clue_refs': [], 'proposal': None}), (), None, 'mock', self.model_name, self.model_name, 'stop')

    class Callbacks:
        def __init__(self, target, mutate=None, initial=None):
            self.initial = initial or puzzle_rules.initial_state()
            self.state = puzzle_rules.visible_state('owner_callback', self.initial)
            self.target, self.mutate = target, mutate
        async def snapshot(self, expected):
            return Snapshot(copy.deepcopy(self.state))
        async def read_tool(self, expected, tool, arguments):
            if self.target in {obj['object_id'] for obj in self.state['objects']}:
                after, receipt = puzzle_rules.apply_action(self.initial, tool, arguments)
                result = puzzle_rules.visible_state('owner_callback', after)
                ids = tuple(receipt['new_clue_ids'])
            else:
                result, ids = copy.deepcopy(self.state), ()
            if self.mutate:
                self.mutate(result)
            self.state = result
            return ReadResult(True, result, '观察结果。', ids)
        async def precheck_proposal(self, *args):
            return CheckResult(False)

    async def read_case(target, mutate=None, initial=None, stopped=False):
        callbacks = Callbacks(target, mutate, initial)
        result = await Runtime(provider=ReadProvider(target)).run(TurnStart(uuid4().hex, '观察', copy.deepcopy(callbacks.state)), callbacks)
        assert (result.data['stop_reason'] == 'STALE_STATE') == stopped, result.data
    asyncio.run(read_case('r1_cabinet'))  # legal neutral observation, no clue
    asyncio.run(read_case('r1_clock'))
    asyncio.run(read_case('r1_cabinet', lambda s: s['observed_object_ids'].append('r3_panel'), stopped=True))
    asyncio.run(read_case('r1_cabinet', lambda s: s['progress'].update(power_on=True), stopped=True))
    asyncio.run(read_case('r1_cabinet', lambda s: s['objects'].append({'object_id': 'r3_panel', 'name': '未来控制台', 'kind': 'device', 'description': '不可见对象', 'actions': []}), stopped=True))
    asyncio.run(read_case('r1_symbols', lambda s: (s['observed_object_ids'].append('r1_symbols'), s.update(revision=1)), stopped=True))
    installed = puzzle_rules.initial_state()
    for tool, args in ROUTE[3:7]:
        installed, _ = puzzle_rules.apply_action(installed, tool, args)
    asyncio.run(read_case('r1_microscope', initial=installed))
    # Real Store callback through HTTP, using a free scripted provider, observation only.
    neutral = TestClient(create_app(Path(temporary) / 'neutral.sqlite', gameplay_version='v3.2', provider=ReadProvider('r1_cabinet')))
    neutral_data = neutral.post('/api/sessions', json={}).json()['data']
    neutral_state = neutral_data['visible_state']
    turn = neutral.post(f"/api/sessions/{neutral_data['session_id']}/ai/turns", headers={'X-Session-Token': neutral_data['token']}, json={'request_id': uuid4().hex, 'revision': neutral_state['revision'], 'generation': neutral_state['generation'], 'message': '观察柜门外观'})
    assert turn.status_code == 200, turn.json()
    validator.validate(turn.json())
    assert turn.json()['data']['stop_reason'] is None
    assert turn.json()['data']['visible_state']['observed_object_ids'] == ['r1_cabinet']
    assert turn.json()['data']['visible_state']['revision'] == 1 and not turn.json()['data']['visible_state']['clues']
    result = {'scope': 'owner-directed, not formal QA', 'counts': count, 'device_stages': {key: sorted(values) for key, values in stages.items()}, 'clues_at_finish': 8, 'early_exploration_actions': 9, 'mock_callback_cases': 7, 'neutral_inspect_http_ai': True, 'paid_calls': 0, 'result': 'pass'}
    (Path(__file__).parent / 'owner-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
