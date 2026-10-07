"""Independent v3.2 public-contract QA; no production answer tables or paid calls."""
import asyncio
import copy
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from tests.api.test_r1 import HTTPFixture, sanitize, semantic_text
from tests.api.test_m2 import digest
from tests.api.test_m3 import Scripted, final, reply, call

CHECKS32 = []
# Answers come from the accepted public puzzle design, not production constants.
ROUTE32 = [
    ('inspect', {'object_id': 'r1_clock'}), ('inspect', {'object_id': 'r1_record'}),
    ('inspect', {'object_id': 'r1_plaque'}), ('inspect', {'object_id': 'r1_microscope'}),
    ('inspect', {'object_id': 'sample_slide'}), ('take', {'item_id': 'sample_slide'}),
    ('use_item', {'item_id': 'sample_slide', 'target_id': 'r1_microscope'}),
    ('inspect', {'object_id': 'r1_microscope'}), ('inspect', {'object_id': 'r1_cabinet'}),
    ('submit_code', {'target_id': 'r1_cabinet', 'code': '4217'}), ('interact', {'target_id': 'r1_cabinet'}),
    ('inspect', {'object_id': 'r1_symbols'}), ('inspect', {'object_id': 'r1_fuse'}), ('take', {'item_id': 'fuse'}),
    ('inspect', {'object_id': 'r1_door'}), ('interact', {'target_id': 'r1_door'}), ('move', {'destination_id': 'R2'}),
    ('inspect', {'object_id': 'r2_maintenance'}), ('inspect', {'object_id': 'r2_powerbox'}),
    ('interact', {'target_id': 'r2_powerbox'}), ('interact', {'target_id': 'r2_powerbox'}),
    ('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}),
    ('interact', {'target_id': 'r2_powerbox'}), ('interact', {'target_id': 'r2_powerbox'}),
    ('inspect', {'object_id': 'r2_monitor'}), ('interact', {'target_id': 'r2_monitor'}),
    ('interact', {'target_id': 'r2_monitor'}),
    ('submit_login', {'target_id': 'r2_monitor', 'username': 'LAB-42', 'password': '2117'}),
    ('interact', {'target_id': 'r2_monitor'}),
    ('inspect', {'object_id': 'research_strip'}), ('take', {'item_id': 'research_strip'}),
    ('inspect', {'object_id': 'access_card'}), ('take', {'item_id': 'access_card'}),
    ('inspect', {'object_id': 'r2_door'}), ('interact', {'target_id': 'r2_door'}), ('move', {'destination_id': 'R3'}),
    ('inspect', {'object_id': 'r3_legend'}), ('inspect', {'object_id': 'r3_panel'}), ('inspect', {'object_id': 'exit_door'}),
    ('use_item', {'item_id': 'research_strip', 'target_id': 'r3_panel'}),
    ('use_item', {'item_id': 'access_card', 'target_id': 'exit_door'}), ('interact', {'target_id': 'exit_door'}),
    ('submit_code', {'target_id': 'r3_panel', 'code': '4792'}),
    ('interact', {'target_id': 'exit_door'}), ('interact', {'target_id': 'exit_door'}), ('move', {'destination_id': 'EXIT'}),
]

def gameplay32(state):
    return {key: value for key, value in state.items() if key not in {'revision', 'generation', 'save'}}


class UpgradeV32Acceptance(HTTPFixture):
    def setUp(self):
        super().setUp()
        self.client.__exit__(None, None, None)
        from backend.app.main import create_app
        self.db = Path(self.temp.name) / 'v32.sqlite'
        self.client = TestClient(create_app(self.db, gameplay_version='v3.2'), raise_server_exceptions=False)
        self.client.__enter__()
        self.session = self.create()
        self.network = patch('httpx.AsyncClient.send', side_effect=AssertionError('Network forbidden in independent v3.2 QA'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        super().tearDown()

    def exchange(self, method, path, **kwargs):
        status, body = super().exchange(method, path, **kwargs)
        if method == 'POST' and path != '/api/sessions':
            tool = (kwargs.get('json') or {}).get('tool')
            state = body.get('data', {}).get('visible_state') if body.get('ok') else body.get('visible_state')
            stages = {key: state.get(key) for key in ('device_states', 'puzzle_states', 'progress')} if state else None
            previous = getattr(self, '_last_logged_stages', None)
            if not body.get('ok') or stages != previous or path.endswith(('/save', '/restore', '/reset')):
                CHECKS32.append({'test': self._testMethodName, 'operation': tool or path.rsplit('/', 1)[-1],
                    'target': (kwargs.get('json') or {}).get('arguments', {}).get('target_id'),
                    'http_status': status, 'error': body.get('error', {}).get('code'),
                    'room': state['room']['room_id'] if state else None, 'stages': stages})
            self._last_logged_stages = stages
        return status, body

    def route(self, begin=0, end=None):
        return [self.action(tool, args) for tool, args in ROUTE32[begin:end]]

    def version(self, state=None):
        state = state or self.state()
        return {'request_id': uuid.uuid4().hex, 'revision': state['revision'], 'generation': state['generation']}

    def control(self, operation, expected=200, code=None):
        status, body = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/{operation}",
            headers=self.headers(), json=self.version(), definition='control_response')
        self.assertEqual(status, expected, sanitize(body))
        if code:
            self.assertEqual(body['error']['code'], code)
        return body['data']['visible_state'] if body.get('ok') else body

    def reopen(self):
        self.client.__exit__(None, None, None)
        from backend.app.main import create_app
        self.client = TestClient(create_app(self.db, gameplay_version='v3.2'), raise_server_exceptions=False)
        self.client.__enter__()

    def clue_text(self, object_id):
        return '\n'.join(clue['text'] for clue in self.state()['clues'] if clue['object_id'] == object_id)

    def ai(self, steps):
        from backend.app.ai.runtime import Runtime
        provider = Scripted(steps)
        self.client.app.state.ai_runtime = Runtime(provider)
        status, body = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/ai/turns",
            headers=self.headers(), json={**self.version(), 'message': '根据已发现事实继续观察'}, definition='ai_turn_response')
        self.assertEqual(status, 200, sanitize(body))
        return body['data'], provider

    def decide(self, proposal):
        return self.exchange('POST', f"/api/sessions/{self.session['session_id']}/proposals/{proposal['proposal_id']}/confirm",
            headers=self.headers(), json={}, definition='action_response')

    def test_public_clues_independently_derive_all_three_answers(self):
        initial = self.state()
        self.assertEqual(initial['level_version'], '3.2.0')
        self.assertEqual(initial['schema_version'], '1.2.0')
        self.assertEqual(initial['clues'], [])
        for answer in ('4217', '2117', '4792'):
            self.assertNotIn(answer, semantic_text(initial))
        self.route(end=4)
        self.assertNotIn('42', self.clue_text('r1_microscope'))
        clock = re.search(r'(\d{2})[:：](\d{2})', self.clue_text('r1_clock'))
        self.assertIsNotNone(clock)
        self.assertIn('分钟', self.clue_text('r1_record'))
        plaque = re.search(r'LAB-\d+', self.clue_text('r1_plaque'))
        self.assertIsNotNone(plaque)
        self.route(4, 8)
        sample = re.search(r'(?:SAMPLE|样本)[^\d]*(\d+)', self.clue_text('r1_microscope'), re.I)
        self.assertIsNotNone(sample)
        cabinet = sample.group(1) + clock.group(2)
        password = clock.group(1) + clock.group(2)
        self.assertEqual(cabinet, '4217')
        self.assertEqual((plaque.group(0), password), ('LAB-42', '2117'))
        self.action(*ROUTE32[8])
        self.action('submit_code', {'target_id': 'r1_cabinet', 'code': cabinet})
        self.route(10, 28)
        self.assertEqual(self.state()['device_states']['computer'], 'UNLOCKED')
        self.route(28, 40)
        symbols = ''.join(re.findall(r'[▲●■★]', self.clue_text('r1_symbols')))
        positions = [int(value) for value in re.findall(r'\d+', self.clue_text('research_strip'))]
        self.assertEqual(symbols, '▲●■★')
        self.assertEqual(positions, [3, 1, 4, 2])
        legend = self.clue_text('r3_legend')
        mapping = {}
        for symbol in '▲●■★':
            number = re.search(re.escape(symbol) + r'[^▲●■★\d]*(\d)', legend)
            self.assertIsNotNone(number, legend)
            mapping[symbol] = number.group(1)
        derived = ''.join(mapping[symbols[position - 1]] for position in positions)
        self.assertEqual(derived, '4792')
        self.route(40, 42)
        self.action('submit_code', {'target_id': 'r3_panel', 'code': derived})
        self.route(43)
        self.assertEqual(self.state()['status'], 'won')
        CHECKS32.append({'test': self._testMethodName, 'derived': {'cabinet': cabinet, 'username': plaque.group(0), 'password': password, 'final': derived}, 'facts': 'public discovered clues only'})

    def test_three_rooms_are_explorable_before_items_power_or_login(self):
        for tool, args in [
            ('inspect', {'object_id': 'r1_door'}), ('interact', {'target_id': 'r1_door'}), ('move', {'destination_id': 'R2'}),
            ('inspect', {'object_id': 'r2_door'}), ('interact', {'target_id': 'r2_door'}), ('move', {'destination_id': 'R3'}),
            ('inspect', {'object_id': 'r3_legend'}), ('inspect', {'object_id': 'r3_panel'}), ('inspect', {'object_id': 'exit_door'}),
        ]:
            self.action(tool, args)
        state = self.state()
        self.assertEqual(state['inventory'], [])
        self.assertEqual(state['device_states'], {'cabinet': 'LOCKED', 'powerbox': 'CLOSED', 'computer': 'OFF', 'exit': 'LOCKED'})
        self.assertFalse(state['progress']['power_on'])
        self.assertTrue(self.clue_text('r3_legend'))
        self.reject(self.request('submit_code', {'target_id': 'r3_panel', 'code': '4792'}), 'PRECONDITION_FAILED')
        self.reject(self.request('move', {'destination_id': 'EXIT'}), 'PRECONDITION_FAILED')
        self.action('move', {'destination_id': 'R2'})
        self.action('move', {'destination_id': 'R1'})
        self.assertEqual(self.state()['room']['room_id'], 'R1')

    def test_main_route_every_puzzle_and_device_stage_save_restore_reopen(self):
        reached = {'microscope': set(), 'panel': set()}
        items_used = set()
        for tool, arguments in ROUTE32:
            before = self.state()
            if tool == 'use_item':
                wrong_target = next(obj['object_id'] for obj in before['objects'] if obj['object_id'] != arguments['target_id'] and obj['object_id'] in before['observed_object_ids'])
                self.reject(self.request('use_item', {'item_id': arguments['item_id'], 'target_id': wrong_target}), 'PRECONDITION_FAILED')
            result = self.action(tool, arguments)
            after = result['visible_state']
            self.assertEqual(after['revision'], before['revision'] + int(result['receipt']['changed']))
            for name, stage in after['puzzle_states'].items():
                reached[name].add(stage)
            if tool == 'use_item':
                items_used.add(arguments['item_id'])
            if after['device_states'] != before['device_states'] or after['puzzle_states'] != before['puzzle_states'] or after['progress'] != before['progress']:
                saved = self.control('save')
                self.assertEqual(saved['save']['level_version'], '3.2.0')
                self.control('reset')
                restored = self.control('restore')
                self.assertEqual(gameplay32(restored), gameplay32(saved))
                self.assertNotEqual(restored['generation'], saved['generation'])
                self.reopen()
                self.assertEqual(self.state(), restored)
        self.assertEqual(reached, {'microscope': {'EMPTY', 'SLIDE_PLACED'}, 'panel': {'EMPTY', 'STRIP_INSERTED'}})
        self.assertEqual(items_used, {'sample_slide', 'fuse', 'research_strip', 'access_card'})
        self.assertEqual(self.state()['status'], 'won')
        self.assertEqual(self.state()['room']['room_id'], 'EXIT')
        CHECKS32.append({'test': self._testMethodName, 'route_actions': len(ROUTE32), 'items_used': sorted(items_used), 'all_stages_saved_restored_reopened': True})

    def test_wrong_inputs_no_stage_bypass_and_strict_manual_login(self):
        self.route(end=9)
        self.reject(self.request('submit_code', {'target_id': 'r1_cabinet', 'code': '382'}), 'WRONG_CODE')
        self.route(9, 19)
        self.reject(self.request('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}), 'PRECONDITION_FAILED')
        self.action('inspect', {'object_id': 'r2_monitor'})
        self.reject(self.request('submit_login', {'target_id': 'r2_monitor', 'username': 'LAB-42', 'password': '2117'}), 'PRECONDITION_FAILED')
        self.route(19, 22)
        self.assertFalse(self.state()['progress']['power_on'])
        self.route(22, 27)
        for args in [{}, {'target_id': 'r2_monitor', 'username': 'LAB-42'},
            {'target_id': 'r2_monitor', 'username': 42, 'password': '2117'},
            {'target_id': 'r2_monitor', 'username': 'LAB-42', 'password': '2117', 'state': 'UNLOCKED'}]:
            self.reject(self.request('submit_login', args), 'BAD_ARGUMENT', 422)
        for args in [{'target_id': 'r2_monitor', 'username': 'LAB-42 ', 'password': '2117'}, {'target_id': 'r2_monitor', 'username': 'LAB-42', 'password': '2117 '}]:
            self.reject(self.request('submit_login', args), 'BAD_ARGUMENT', 422)
        for username, password in [('lab-42', '2117'), ('LAB-41', '2117'), ('LAB-42', '0000')]:
            before = self.state()
            status, body = self.post(self.request('submit_login', {'target_id': 'r2_monitor', 'username': username, 'password': password}))
            self.assertEqual(status, 409)
            self.assertEqual(body['error']['code'], 'WRONG_CODE')
            self.assertEqual(self.state(), before)
        self.reject(self.request('submit_code', {'target_id': 'r2_monitor', 'code': '2117'}), 'PRECONDITION_FAILED')
        self.route(27, 39)
        self.reject(self.request('submit_code', {'target_id': 'r3_panel', 'code': '4792'}), 'PRECONDITION_FAILED')
        self.action(*ROUTE32[40])  # card accepted, no paper installed or door opened
        self.assertEqual(self.state()['device_states']['exit'], 'CARD_ACCEPTED')
        self.reject(self.request('move', {'destination_id': 'EXIT'}), 'PRECONDITION_FAILED')
        self.action(*ROUTE32[41])
        self.reject(self.request('submit_code', {'target_id': 'r3_panel', 'code': '4792'}), 'PRECONDITION_FAILED')
        self.action(*ROUTE32[39])
        self.reject(self.request('submit_code', {'target_id': 'r3_panel', 'code': '231'}), 'WRONG_CODE')
        self.action(*ROUTE32[42])
        self.reject(self.request('move', {'destination_id': 'EXIT'}), 'PRECONDITION_FAILED')
        self.action(*ROUTE32[43])
        self.reject(self.request('move', {'destination_id': 'EXIT'}), 'PRECONDITION_FAILED')
        self.route(44)

    def test_cross_version_and_checksum_valid_corruption_no_session_or_slot_overwrite(self):
        self.route(end=43)
        self.control('save')
        with closing(sqlite3.connect(self.db)) as db:
            raw = db.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (self.session['session_id'],)).fetchone()[0]
        baseline = json.loads(raw)
        cases = [
            ('legacy', lambda s: s.update(schema_version='1.0.0', level_version='2.0.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('v31', lambda s: s.update(schema_version='1.1.0', level_version='3.1.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('bad-checksum', lambda s: s.update(checksum='0' * 64), 'INVALID_SNAPSHOT'),
            ('unknown-puzzle', lambda s: s['game_fields']['puzzle_states'].update(panel='HACKED'), 'INVALID_SNAPSHOT'),
            ('verified-without-strip', lambda s: s['game_fields']['consumed_item_ids'].remove('research_strip'), 'INVALID_SNAPSHOT'),
            ('installed-slide-missing', lambda s: s['game_fields']['puzzle_states'].update(microscope='EMPTY'), 'INVALID_SNAPSHOT'),
            ('missing-puzzle-field', lambda s: s['game_fields'].pop('puzzle_states'), 'INVALID_SNAPSHOT'),
            ('wrong-internal-version', lambda s: s['game_fields'].update(level_version='3.1.0'), 'INVALID_SNAPSHOT'),
            ('missing-panel-observation', lambda s: s['game_fields']['observed_object_ids'].remove('r3_panel'), 'INVALID_SNAPSHOT'),
            ('duplicate-observation', lambda s: s['game_fields']['observed_object_ids'].append('r1_clock'), 'INVALID_SNAPSHOT'),
        ]
        for name, mutate, code in cases:
            with self.subTest(case=name):
                broken = copy.deepcopy(baseline); mutate(broken)
                if name != 'bad-checksum':
                    broken['checksum'] = digest(broken)
                tampered = json.dumps(broken, ensure_ascii=False)
                with closing(sqlite3.connect(self.db)) as db:
                    db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (tampered, self.session['session_id'])); db.commit()
                    state_before = db.execute('SELECT state_json FROM sessions WHERE session_id=?', (self.session['session_id'],)).fetchone()[0]
                before = self.state()
                self.control('restore', 409, code)
                self.assertEqual(self.state(), before)
                with closing(sqlite3.connect(self.db)) as db:
                    self.assertEqual(db.execute('SELECT state_json FROM sessions WHERE session_id=?', (self.session['session_id'],)).fetchone()[0], state_before)
                    self.assertEqual(db.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (self.session['session_id'],)).fetchone()[0], tampered)
                CHECKS32.append({'test': self._testMethodName, 'snapshot_case': name, 'code': code, 'session_and_slot_unchanged': True})
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (raw, self.session['session_id'])); db.commit()
        self.control('restore')

    def test_ai_neutral_inspect_receipts_and_confirm_share_current_rules(self):
        data, provider = self.ai([reply(calls=[call('inspect', {'object_id': 'r1_door'})]), final()])
        self.assertEqual(data['status'], 'no_suggestion')
        self.assertEqual(data['usage']['read_tool_calls'], 1)
        self.assertEqual(data['visible_state']['revision'], 1)
        self.assertEqual(data['visible_state']['observed_object_ids'], ['r1_door'])
        self.assertEqual(data['visible_state']['clues'], [])
        self.assertEqual(provider.calls, 2)
        observed = self.state()
        inventory_data, _ = self.ai([reply(calls=[call('get_inventory', {})]), final()])
        self.assertEqual(inventory_data['status'], 'no_suggestion')
        self.assertEqual(inventory_data['visible_state'], observed)
        self.assertEqual(inventory_data['usage']['read_tool_calls'], 1)
        self.route(end=9)
        before = self.state()
        data, _ = self.ai([final('take', {'item_id': 'fuse'})])
        self.assertIsNone(data['proposal'])
        self.assertEqual(self.state(), before)
        data, _ = self.ai([final('submit_code', {'target_id': 'r1_cabinet', 'code': '4217'})])
        self.assertIsNotNone(data['proposal'])
        status, accepted = self.decide(data['proposal'])
        self.assertEqual(status, 200)
        self.assertEqual(accepted['data']['visible_state']['device_states']['cabinet'], 'CODE_ACCEPTED')
        self.action(*ROUTE32[10]); self.route(11, 19)
        before = self.state()
        data, _ = self.ai([final('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'})])
        self.assertIsNone(data['proposal']); self.assertEqual(self.state(), before)
        self.route(19, 21)
        data, _ = self.ai([final('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'})])
        self.assertIsNotNone(data['proposal'])
        status, accepted = self.decide(data['proposal']); self.assertEqual(status, 200)
        self.assertEqual(accepted['data']['visible_state']['device_states']['powerbox'], 'FUSE_INSTALLED')
        self.assertFalse(self.state()['progress']['power_on'])
        repeat_status, repeat = self.decide(data['proposal']); self.assertEqual(repeat_status, 200)
        self.assertTrue(repeat['data']['replayed'])
        self.assertEqual(repeat['data']['receipt'], accepted['data']['receipt'])
        self.route(22, 39)
        data, _ = self.ai([final('move', {'destination_id': 'EXIT'})])
        self.assertIsNone(data['proposal'])
        self.action(*ROUTE32[39]); self.action(*ROUTE32[40]); self.action(*ROUTE32[41])
        data, _ = self.ai([final('submit_code', {'target_id': 'r3_panel', 'code': '4792'})])
        proposal = data['proposal']; self.assertIsNotNone(proposal)
        self.control('save'); self.control('restore')
        status, expired = self.decide(proposal); self.assertEqual(status, 409)
        self.assertEqual(expired['error']['code'], 'PROPOSAL_INVALIDATED')

    def test_ai_read_callback_cannot_forge_observations_future_clues_or_inventory(self):
        from backend.app.ai.runtime import Runtime
        from backend.app.ai.types import TurnStart, Snapshot, ReadResult
        self.action('inspect', {'object_id': 'r1_clock'})
        initial = self.state()
        sentinel = 'UNSEEN_FUTURE_FACT_SENTINEL'
        cases = {
            'unrelated-observation': lambda s: s['observed_object_ids'].extend(['r1_door', 'r1_record']),
            'future-observation': lambda s: s['observed_object_ids'].extend(['r1_door', 'r3_legend']),
            'removed-observation': lambda s: s.update(observed_object_ids=['r1_door']),
            'future-clue': lambda s: (s['observed_object_ids'].append('r1_door'), s['clues'].append({'clue_id': 'qa_future_clue', 'object_id': 'r3_legend', 'title': '伪造未来线索', 'text': sentinel})),
            'future-object': lambda s: (s['observed_object_ids'].append('r1_door'), s['objects'].append({'object_id': 'r3_legend', 'name': '设备对应表', 'kind': 'clue', 'description': sentinel, 'actions': [{'tool': 'inspect', 'label': '观察', 'arguments': {'object_id': 'r3_legend'}, 'requires_code': False}]})),
            'object-identity': lambda s: (s['observed_object_ids'].append('r1_door'), s['objects'][0].update(name='伪造墙钟')),
            'duplicate-existing-clue': lambda s: (s['observed_object_ids'].append('r1_door'), s['clues'].append(copy.deepcopy(s['clues'][0]))),
            'existing-clue-future-fact': lambda s: (s['observed_object_ids'].append('r1_door'), s['clues'][0].update(text=sentinel)),
            'room-injection': lambda s: (s['observed_object_ids'].append('r1_door'), s['room'].update(room_id='R2')),
            'device-progress': lambda s: (s['observed_object_ids'].append('r1_door'), s['device_states'].update(computer='BOOTING')),
            'panel-progress': lambda s: (s['observed_object_ids'].append('r1_door'), s['puzzle_states'].update(panel='STRIP_INSERTED')),
            'read-adds-item': lambda s: (s['observed_object_ids'].append('r1_door'), s['inventory'].append({'item_id': 'sample_slide', 'name': '合成样本', 'description': '伪造只读获得', 'usable_targets': []})),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                forged = copy.deepcopy(initial); forged['revision'] += 1; mutate(forged)
                class ForgedCallbacks:
                    read_happened = False
                    async def snapshot(self, expected):
                        return Snapshot(copy.deepcopy(forged if self.read_happened else initial))
                    async def read_tool(self, expected, tool, arguments):
                        self.read_happened = True
                        old_ids = {clue['clue_id'] for clue in initial['clues']}
                        added_ids = tuple(clue['clue_id'] for clue in forged['clues'] if clue['clue_id'] not in old_ids)
                        return ReadResult(True, copy.deepcopy(forged), '中性观察。', added_ids)
                    async def precheck_proposal(self, expected, candidate):
                        raise AssertionError('Forged read must stop before proposal precheck')
                provider = Scripted([reply(calls=[call('inspect', {'object_id': 'r1_door'})]), final()])
                result = asyncio.run(Runtime(provider).run(TurnStart('qa-read-boundary', '仅观察当前门', copy.deepcopy(initial)), ForgedCallbacks()))
                self.assertEqual(result.data['status'], 'stopped')
                self.assertIn(result.data['stop_reason'], {'STALE_STATE', 'MODEL_INVALID_OUTPUT'})
                self.assertEqual(provider.calls, 1)
                self.assertNotIn(sentinel, json.dumps(provider.contexts, ensure_ascii=False))
                self.assertEqual(self.state(), initial)
                CHECKS32.append({'test': self._testMethodName, 'forged_callback_case': name, 'stopped': result.data['stop_reason'], 'no_second_provider_call_or_store_mutation': True})

    def test_ai_installed_microscope_read_is_legitimate_knowledge_discovery(self):
        self.route(end=7)
        before = self.state()
        self.assertEqual(before['puzzle_states']['microscope'], 'SLIDE_PLACED')
        data, provider = self.ai([reply(calls=[call('inspect', {'object_id': 'r1_microscope'})]), final()])
        self.assertEqual(data['status'], 'no_suggestion')
        self.assertEqual(data['visible_state']['puzzle_states'], before['puzzle_states'])
        self.assertEqual(data['visible_state']['revision'], before['revision'] + 1)
        self.assertEqual(data['visible_state']['inventory'], before['inventory'])
        self.assertEqual(data['visible_state']['device_states'], before['device_states'])
        self.assertEqual(data['visible_state']['room'], before['room'])
        self.assertIn('42', self.clue_text('r1_microscope'))
        self.assertEqual(provider.calls, 2)
        self.assertEqual(data['usage']['read_tool_calls'], 1)
        CHECKS32.append({'test': self._testMethodName, 'legitimate_knowledge_discovery': 'sample clue acquired with installed slide; slots unchanged', 'read_calls': 1, 'inventory_room_devices_unchanged': True})
