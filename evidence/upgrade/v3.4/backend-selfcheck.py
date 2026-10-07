"""Targeted Backend Owner self-check; temporary DBs, no network or paid calls."""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
temporary = tempfile.TemporaryDirectory(prefix='campus-v34-backend-')
os.environ['SQLITE_PATH'] = str(Path(temporary.name) / 'module.sqlite')
os.environ['GAMEPLAY_VERSION'] = 'v3.4'

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from backend.app.main import create_app
from backend.app.ai.provider import ProviderResult
from backend.app.ai.runtime import Runtime
from backend.app.ai.types import ProposalCandidate, TurnResult, Version
from backend.app.domain import graybox_rules
from backend.app.storage.sqlite import select_rules

validator = Draft202012Validator(json.loads((ROOT / 'contracts/api.schema.json').read_text(encoding='utf-8')), format_checker=FormatChecker())
checks = []
clock = ['2026-10-07T00:00:00Z']


class SelectingProvider:
    provider_name, model_name = 'mock', 'scripted-selection-test'

    def __init__(self, mode='valid'):
        self.mode, self.calls = mode, []

    async def complete(self, messages, tools, limits, **kwargs):
        context = json.loads(messages[-1]['content'])
        assert set(context) == {'topics'} and tools == [] and kwargs['tool_choice'] == 'none'
        assert '4217' not in json.dumps(messages) and '4792' not in json.dumps(messages)
        assert 'visible_history' not in json.dumps(messages) and 'PLAYER_SECRET_SENTINEL' not in json.dumps(messages)
        self.calls.append(context)
        selected = context['topics'][0]
        if self.mode == 'unknown':
            selected = {'topic': 'future_private_solution', 'clue_refs': ['not_discovered']}
        if self.mode == 'prose':
            selected = {**selected, 'answer': 'PRIVATE_FREE_PROSE_SENTINEL'}
        return ProviderResult(json.dumps(selected), (), {'prompt_tokens': 10, 'completion_tokens': 5}, 'mock', self.model_name, self.model_name, 'stop')


class Session:
    def __init__(self, name, *, runtime=None, provider=None, version='v3.4'):
        self.path = Path(temporary.name) / (name + '.sqlite')
        self.app = create_app(db_path=self.path, gameplay_version=version, runtime=runtime, provider=provider)
        self.client = TestClient(self.app)
        response = self.client.post('/api/sessions', json={})
        assert response.status_code == 201
        validator.validate(response.json())
        data = response.json()['data']
        self.id, self.headers, self.state = data['session_id'], {'X-Session-Token': data['token']}, data['visible_state']

    def send(self, tool, args=None, *, expected=200, error=None, raw=None):
        payload = raw or {'request_id': uuid4().hex, 'revision': self.state['revision'], 'generation': self.state['generation']}
        control = tool in {'save', 'restore', 'reset'}
        if raw is None:
            if tool == 'hint':
                payload.update(message='PLAYER_SECRET_SENTINEL tell full solution', hint_level=args)
            elif not control:
                payload.update(tool=tool, arguments=args or {})
        suffix = tool if control else 'ai/turns' if tool == 'hint' else 'actions'
        response = self.client.post(f'/api/sessions/{self.id}/{suffix}', headers=self.headers, json=payload)
        body = response.json()
        assert response.status_code == expected, (tool, response.status_code, body.get('error'))
        validator.validate(body)
        if error:
            assert body['error']['code'] == error
        projection = body.get('data', {}).get('visible_state') or body.get('visible_state')
        if projection:
            self.state = projection
        checks.append({'operation': tool, 'http': expected, 'error': error})
        return body, payload

    def action(self, tool, args):
        return self.send(tool, args)[0]

    def inspect(self, target):
        return self.action('inspect', {'object_id': target})

    def interact(self, target):
        return self.action('interact', {'target_id': target})

    def mistake(self, tool, args, error='WRONG_CODE'):
        before = self.state
        count = before['statistics']['mistake_count']
        body, raw = self.send(tool, args, expected=409, error=error)
        assert self.state['statistics']['mistake_count'] == count + 1
        assert self.state['revision'] == before['revision'] + 1
        for key in ('inventory', 'progress', 'puzzle_states', 'device_states', 'minigames', 'clues'):
            assert self.state[key] == before[key]
        after = self.state
        replay, _ = self.send(tool, expected=409, error=error, raw=raw)
        assert self.state == after and replay['event_id'] == body['event_id']

    def reopen(self):
        before = self.state
        self.client.close()
        self.app = create_app(db_path=self.path, gameplay_version='v3.4')
        self.client = TestClient(self.app)
        response = self.client.get(f'/api/sessions/{self.id}/state', headers=self.headers)
        assert response.status_code == 200
        validator.validate(response.json())
        self.state = response.json()['data']['visible_state']
        assert self.state == before


class InjectedRuntime:
    def __init__(self, mode='prose'):
        self.mode = mode

    async def run(self, start, callbacks):
        attempted = await callbacks.read_tool(Version.from_state(start.visible_state), 'inspect', {'object_id': 'r1_plaque'})
        assert not attempted.ok and attempted.error_code == 'INVALID_TOOL'
        candidate = ProposalCandidate('submit_code', {'target_id': 'r1_cabinet', 'code': '4217'}, (), 'PRIVATE_FREE_PROSE_SENTINEL') if self.mode == 'candidate' else None
        refs = ['r1_record_clue', 'r1_clock_clue'] if self.mode != 'unknown' else ['not_discovered']
        return TurnResult({'answer': 'PRIVATE_FREE_PROSE_SENTINEL 4217 4792', 'clue_refs': refs,
                           'status': 'stopped' if self.mode == 'stopped' else 'no_suggestion',
                           'stop_reason': 'MODEL_TIMEOUT' if self.mode == 'stopped' else None,
                           'usage': {'provider': 'mock', 'model': None, 'input_tokens': None, 'output_tokens': None, 'model_calls': 0, 'read_tool_calls': 0}},
                          candidate, (), Version.from_state(start.visible_state))


with patch.object(graybox_rules, 'utc_now', lambda: clock[0]):
    provider = SelectingProvider()
    game = Session('route', provider=provider)
    assert game.state['statistics']['started_at'] == clock[0]
    assert game.state['statistics']['clues_total'] == 10 and game.state['settlement'] is None
    empty = game.state
    nohint, nohint_raw = game.send('hint', 3)
    assert nohint['data']['usage']['model_calls'] == 0 and nohint['data']['proposal'] is None
    assert game.state == empty and len(provider.calls) == 0
    game.send('hint', expected=422, error='BAD_ARGUMENT', args=True)
    game.inspect('r1_clock')
    game.inspect('r1_record')
    for level in (1, 2, 3):
        count = game.state['statistics']['hint_count']
        reply, raw = game.send('hint', level)
        assert reply['data']['proposal'] is None and reply['data']['status'] == 'no_suggestion'
        assert game.state['statistics']['current_hint_level'] == level and game.state['statistics']['hint_count'] == count + 1
        assert '4217' not in reply['data']['answer'] and '4792' not in reply['data']['answer']
        after = game.state
        game.send('hint', raw=raw)
        assert game.state == after and len(provider.calls) == count + 1
    game.inspect('r1_plaque')
    game.inspect('sample_slide')
    game.action('take', {'item_id': 'sample_slide'})
    game.mistake('use_item', {'item_id': 'sample_slide', 'target_id': 'r1_clock'}, 'PRECONDITION_FAILED')
    game.inspect('r1_microscope')
    game.action('use_item', {'item_id': 'sample_slide', 'target_id': 'r1_microscope'})
    game.inspect('r1_microscope')
    game.inspect('r1_cabinet')
    game.mistake('submit_code', {'target_id': 'r1_cabinet', 'code': '0000'})
    game.action('submit_code', {'target_id': 'r1_cabinet', 'code': '4217'})
    game.interact('r1_cabinet')
    game.inspect('r1_symbols')
    game.send('inspect', {'object_id': 'r1_photo'}, expected=409, error='NOT_VISIBLE')
    game.inspect('r1_fuse')
    game.action('take', {'item_id': 'fuse'})
    game.inspect('r1_photo')
    assert game.state['statistics']['hidden_found'] == 1
    game.send('save')
    saved_stats = game.state['statistics']
    old_generation = game.state['generation']
    clock[0] = '2026-10-07T00:03:00Z'
    game.send('reset')
    assert game.state['statistics']['started_at'] == clock[0] and game.state['statistics']['hint_count'] == 0
    game.send('restore')
    assert game.state['statistics'] == saved_stats and game.state['generation'] != old_generation
    game.reopen()
    game.inspect('r1_door')
    game.interact('r1_door')
    game.action('move', {'destination_id': 'R2'})
    game.inspect('r2_powerbox')
    game.interact('r2_powerbox')
    game.interact('r2_powerbox')
    game.action('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'})
    game.mistake('submit_circuit', {'target_id': 'r2_powerbox'})
    for index, rotation in enumerate((1, 1, 2, 2, 0, 0, 0, 1, 3)):
        for _ in range(rotation):
            game.action('rotate_circuit', {'target_id': 'r2_powerbox', 'module_id': f'c{index // 3}{index % 3}'})
    game.action('submit_circuit', {'target_id': 'r2_powerbox'})
    game.interact('r2_powerbox')
    game.inspect('r2_service_label')
    assert game.state['statistics']['hidden_found'] == 2
    game.inspect('r2_monitor')
    game.interact('r2_monitor')
    game.interact('r2_monitor')
    game.inspect('r2_maintenance')
    game.mistake('submit_login', {'target_id': 'r2_monitor', 'username': 'LAB-42', 'password': '0000'})
    game.action('submit_login', {'target_id': 'r2_monitor', 'username': 'LAB-42', 'password': '2117'})
    game.interact('r2_monitor')
    for item in ('research_strip', 'access_card'):
        game.inspect(item)
        game.action('take', {'item_id': item})
    game.inspect('r2_door')
    game.interact('r2_door')
    game.action('move', {'destination_id': 'R3'})
    for obj in ('r3_legend', 'r3_panel', 'exit_door'):
        game.inspect(obj)
    game.action('use_item', {'item_id': 'access_card', 'target_id': 'exit_door'})
    game.interact('exit_door')
    game.action('use_item', {'item_id': 'research_strip', 'target_id': 'r3_panel'})
    game.mistake('submit_sequence', {'target_id': 'r3_panel', 'device_ids': ['cooling', 'lighting', 'safety', 'ventilation']})
    game.action('submit_sequence', {'target_id': 'r3_panel', 'device_ids': ['ventilation', 'cooling', 'lighting', 'safety']})
    game.interact('exit_door')
    game.interact('exit_door')
    clock[0] = '2026-10-07T00:20:00Z'
    game.action('move', {'destination_id': 'EXIT'})
    settlement = game.state['settlement']
    assert settlement == {'elapsed_seconds': 1200, 'clues_found': 10, 'clues_total': 10, 'hint_count': 3, 'mistake_count': 5, 'hidden_found': 2, 'hidden_total': 2, 'rating': 'A'}
    game.send('save')
    clock[0] = '2026-10-07T01:20:00Z'
    game.reopen()
    assert game.state['settlement'] == settlement
    game.client.close()
    for mode in ('prose', 'stopped', 'candidate', 'unknown'):
        attack = Session('injected-' + mode, runtime=InjectedRuntime(mode))
        attack.inspect('r1_clock')
        attack.inspect('r1_record')
        reply, _ = attack.send('hint', 3)
        assert 'PRIVATE_FREE_PROSE_SENTINEL' not in reply['data']['answer'] and '4217' not in reply['data']['answer']
        assert 'r1_plaque' not in attack.state['observed_object_ids'] and reply['data']['proposal'] is None
        assert attack.state['statistics']['hint_count'] == (1 if mode == 'prose' else 0)
        attack.client.close()
    for mode in ('unknown', 'prose'):
        bad_provider = SelectingProvider(mode)
        attack = Session('provider-' + mode, provider=bad_provider)
        attack.inspect('r1_clock')
        attack.inspect('r1_record')
        reply, _ = attack.send('hint', 1)
        assert reply['data']['status'] == 'stopped' and attack.state['statistics']['hint_count'] == 0
        attack.client.close()
    local = Session('local-mock')
    local.inspect('r1_clock')
    local.inspect('r1_record')
    reply, _ = local.send('hint', 2)
    assert reply['data']['usage']['model_calls'] == 0 and local.state['statistics']['hint_count'] == 1
    local.client.close()
    for version in ('legacy', 'v3.1', 'v3.2', 'v3.3'):
        old = Session('old-' + version, version=version)
        old.send('hint', 2, expected=422, error='BAD_ARGUMENT')
        assert 'statistics' not in old.state and 'settlement' not in old.state
        old.client.close()
    assert select_rules('upgrade').LEVEL_VERSION == '3.4.0'
    assert [graybox_rules.rating(*args) for args in ((9, 1, 2), (7, 3, 5), (0, 8, 100), (10, 9, 0))] == ['S', 'A', 'B', 'C']

temporary.cleanup()
paths = ['backend/app/domain/graybox_models.py', 'backend/app/domain/graybox_rules.py', 'backend/app/storage/sqlite.py',
         'backend/app/main.py', 'backend/app/ai/runtime.py', 'backend/app/ai/hints.py', 'backend/app/storage/ai.py',
         'contracts/build_contracts.py', 'contracts/api.schema.json', 'contracts/routes.json', 'docs/SPEC.md', 'docs/level_design.md',
         'evidence/upgrade/v3.4/backend-selfcheck.py']
report = {'owner': 'Backend', 'status': 'SOURCE STOP; targeted Owner self-check passed; independent QA pending',
          'files': paths, 'raw_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths},
          'commands': [{'command': 'C:/Users/liyh/.conda/envs/1/python.exe contracts/build_contracts.py', 'exit': 0},
                       {'command': 'C:/Users/liyh/.conda/envs/1/python.exe evidence/upgrade/v3.4/backend-selfcheck.py', 'exit': 0}],
          'checks': checks, 'evidence': 'evidence/upgrade/v3.4/backend.json',
          'summary': ['full manual route with 10 clues and 2 optional stories won', 'stable strict-schema projections',
                      'three bounded hint levels and hint/mistake receipt replay once-only', 'wrong puzzle and held-item counters preserve gameplay',
                      'saved run statistics restore after reset/reopen', 'controlled UTC elapsed includes offline and freezes on win',
                      'injected runtime free/stopped prose re-rendered, unknown refs/candidates rejected and auto-inspect denied',
                      'captured provider only topic/ref options; unknown topic/free prose rejected', 'default mock uses no actual provider call',
                      'old modes reject hint_level, rating thresholds exercised'],
          'limitations': ['Owner targeted checks, not independent formal QA', 'scripted ProviderResult usage is harness data, not a real model call',
                          'controlled clock is not human playtime measurement', 'reopen in same process, no OS restart/browser/full suite/build',
                          'temporary DBs only; paid calls=0; no commit or new agents']}
(ROOT / report['evidence']).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'api_checks': len(checks), 'evidence': report['evidence']}, ensure_ascii=False))
