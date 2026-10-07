"""Independent v3.1 state-chain acceptance; owned temp DBs and offline AI only."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from tests.api.test_r1 import HTTPFixture, sanitize
from tests.api.test_m2 import digest
from tests.api.test_m3 import Scripted, final, reply, call

# An explicit independent route, not imported from production rule tables.
ROUTE31 = [
    ('inspect', {'object_id': 'r1_note'}), ('inspect', {'object_id': 'r1_cabinet'}),
    ('submit_code', {'target_id': 'r1_cabinet', 'code': '382'}),
    ('interact', {'target_id': 'r1_cabinet'}), ('inspect', {'object_id': 'access_card'}),
    ('take', {'item_id': 'access_card'}), ('inspect', {'object_id': 'r1_door'}),
    ('use_item', {'item_id': 'access_card', 'target_id': 'r1_door'}), ('move', {'destination_id': 'R2'}),
    ('inspect', {'object_id': 'r2_fuse'}), ('take', {'item_id': 'fuse'}),
    ('inspect', {'object_id': 'r2_powerbox'}), ('interact', {'target_id': 'r2_powerbox'}),
    ('interact', {'target_id': 'r2_powerbox'}), ('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}),
    ('interact', {'target_id': 'r2_powerbox'}), ('interact', {'target_id': 'r2_powerbox'}),
    ('inspect', {'object_id': 'r2_monitor'}), ('interact', {'target_id': 'r2_monitor'}),
    ('interact', {'target_id': 'r2_monitor'}), ('inspect', {'object_id': 'r2_monitor'}),
    ('inspect', {'object_id': 'r2_drawer'}), ('submit_code', {'target_id': 'r2_monitor', 'code': '724'}),
    ('interact', {'target_id': 'r2_monitor'}), ('submit_code', {'target_id': 'r2_drawer', 'code': '724'}),
    ('inspect', {'object_id': 'emergency_key'}), ('take', {'item_id': 'emergency_key'}),
    ('inspect', {'object_id': 'r2_door'}), ('use_item', {'item_id': 'emergency_key', 'target_id': 'r2_door'}),
    ('move', {'destination_id': 'R3'}), ('inspect', {'object_id': 'r3_checklist'}),
    ('inspect', {'object_id': 'r3_panel'}), ('inspect', {'object_id': 'exit_door'}),
    ('use_item', {'item_id': 'access_card', 'target_id': 'exit_door'}),
    ('interact', {'target_id': 'exit_door'}), ('submit_code', {'target_id': 'r3_panel', 'code': '231'}),
    ('interact', {'target_id': 'exit_door'}), ('interact', {'target_id': 'exit_door'}),
    ('move', {'destination_id': 'EXIT'}),
]
DEVICES = {'cabinet': 'r1_cabinet', 'powerbox': 'r2_powerbox', 'computer': 'r2_monitor', 'exit': 'exit_door'}
CHAIN = {
    'cabinet': ['LOCKED', 'CODE_ACCEPTED', 'OPEN', 'ITEM_TAKEN'],
    'powerbox': ['CLOSED', 'OPEN', 'MISSING_FUSE', 'FUSE_INSTALLED', 'CIRCUIT_READY', 'POWER_ON'],
    'computer': ['OFF', 'BOOTING', 'LOGIN_LOCKED', 'UNLOCKED', 'DATA_READ'],
    'exit': ['LOCKED', 'CARD_ACCEPTED', 'FINAL_CHECK', 'UNLOCKED', 'OPEN'],
}

def semantic(state):
    return {k: v for k, v in state.items() if k not in {'revision', 'generation', 'save'}}


class UpgradeV31Acceptance(HTTPFixture):
    def setUp(self):
        super().setUp()
        self.client.__exit__(None, None, None)
        from backend.app.main import create_app
        self.db = Path(self.temp.name) / 'upgrade.sqlite'
        self.client = TestClient(create_app(self.db, gameplay_version='v3.1'), raise_server_exceptions=False)
        self.client.__enter__()
        self.session = self.create()
        self.network = patch('httpx.AsyncClient.send', side_effect=AssertionError('Paid/network calls forbidden'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        super().tearDown()

    def route(self, begin=0, end=None):
        return [self.action(tool, args) for tool, args in ROUTE31[begin:end]]

    def version(self, state=None):
        state = state or self.state()
        return {'request_id': uuid.uuid4().hex, 'revision': state['revision'], 'generation': state['generation']}

    def control(self, operation, expected=200, code=None):
        status, body = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/{operation}",
            headers=self.headers(), json=self.version(), definition='control_response')
        self.assertEqual(status, expected, sanitize(body))
        if code:
            self.assertEqual(body['error']['code'], code)
        return body

    def reopen(self):
        self.client.__exit__(None, None, None)
        from backend.app.main import create_app
        self.client = TestClient(create_app(self.db, gameplay_version='v3.1'), raise_server_exceptions=False)
        self.client.__enter__()

    def ai(self, steps):
        from backend.app.ai.runtime import Runtime
        provider = Scripted(steps)
        self.client.app.state.ai_runtime = Runtime(provider)
        status, body = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/ai/turns",
            headers=self.headers(), json={**self.version(), 'message': '根据已发现信息建议'}, definition='ai_turn_response')
        self.assertEqual(status, 200, sanitize(body))
        return body['data'], provider

    def decide(self, proposal):
        return self.exchange('POST', f"/api/sessions/{self.session['session_id']}/proposals/{proposal['proposal_id']}/confirm",
            headers=self.headers(), json={}, definition='action_response')

    def test_all_four_chains_save_restore_and_store_reopen(self):
        seen = {name: {} for name in CHAIN}
        messages = {name: [] for name in CHAIN}
        def capture(state):
            for name, object_id in DEVICES.items():
                obj = next((obj for obj in state['objects'] if obj['object_id'] == object_id), None)
                if obj:
                    seen[name].setdefault(state['device_states'][name], obj)
        capture(self.state())
        for tool, args in ROUTE31:
            before = self.state()
            result = self.action(tool, args)
            state = result['visible_state']
            self.assertEqual(state['schema_version'], '1.1.0')
            self.assertEqual(state['level_version'], '3.1.0')
            self.assertEqual(state['revision'], before['revision'] + int(result['receipt']['changed']))
            capture(state)
            changed = [name for name in CHAIN if state['device_states'][name] != before['device_states'][name]]
            for name in changed:
                messages[name].append(result['receipt']['message'])
            if changed:
                self.control('save')
                saved = self.state()
                self.assertEqual(saved['save']['level_version'], '3.1.0')
                self.control('reset')
                restored = self.control('restore')['data']['visible_state']
                self.assertEqual(semantic(restored), semantic(saved))
                self.assertNotEqual(restored['generation'], saved['generation'])
                self.reopen()
                self.assertEqual(self.state(), restored)
        self.assertEqual(self.state()['status'], 'won')
        self.assertEqual(self.state()['room']['room_id'], 'EXIT')
        for name, stages in CHAIN.items():
            self.assertEqual(set(seen[name]), set(stages), name)
            self.assertEqual(len({v['description'] for v in seen[name].values()}), len(stages), name)
            self.assertEqual(len(messages[name]), len(set(messages[name])), name)
            # Progressive affordances must expose the relevant server operation.
        self.assertIn('interact', [a['tool'] for a in seen['cabinet']['CODE_ACCEPTED']['actions']])
        self.assertNotIn('submit_code', [a['tool'] for a in seen['computer']['BOOTING']['actions']])
        self.assertIn('submit_code', [a['tool'] for a in seen['computer']['LOGIN_LOCKED']['actions']])
        self.assertNotIn('interact', [a['tool'] for a in seen['powerbox']['MISSING_FUSE']['actions']])

    def test_no_old_verb_bypass_and_wrong_attempts_preserve_state(self):
        self.reject(self.request('interact', {'target_id': 'r1_cabinet'}), 'PRECONDITION_FAILED')
        self.route(end=3)
        self.reject(self.request('take', {'item_id': 'access_card'}), 'NOT_VISIBLE')
        self.route(3, 12)
        self.reject(self.request('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}), 'PRECONDITION_FAILED')
        self.action('inspect', {'object_id': 'r2_monitor'})
        self.reject(self.request('interact', {'target_id': 'r2_monitor'}), 'PRECONDITION_FAILED')
        self.reject(self.request('submit_code', {'target_id': 'r2_monitor', 'code': '724'}), 'PRECONDITION_FAILED')
        self.route(12, 15)
        self.assertFalse(self.state()['progress']['power_on'])
        self.reject(self.request('use_item', {'item_id': 'access_card', 'target_id': 'r2_powerbox'}), 'PRECONDITION_FAILED')
        self.route(15, 19)
        self.reject(self.request('submit_code', {'target_id': 'r2_monitor', 'code': '724'}), 'PRECONDITION_FAILED')
        self.route(19, 22)
        self.reject(self.request('submit_code', {'target_id': 'r2_drawer', 'code': '724'}), 'PRECONDITION_FAILED')
        self.reject(self.request('submit_code', {'target_id': 'r2_monitor', 'code': '000'}), 'WRONG_CODE')
        self.route(22, 24)
        self.reject(self.request('submit_code', {'target_id': 'r2_drawer', 'code': '000'}), 'WRONG_CODE')
        self.route(24, 33)
        self.reject(self.request('submit_code', {'target_id': 'r3_panel', 'code': '231'}), 'PRECONDITION_FAILED')
        self.reject(self.request('move', {'destination_id': 'EXIT'}), 'PRECONDITION_FAILED')
        self.route(33, 35)
        self.reject(self.request('interact', {'target_id': 'exit_door'}), 'PRECONDITION_FAILED')
        self.reject(self.request('submit_code', {'target_id': 'r3_panel', 'code': '000'}), 'WRONG_CODE')
        self.route(35, 36)
        self.reject(self.request('move', {'destination_id': 'EXIT'}), 'PRECONDITION_FAILED')
        self.route(36, 37)
        self.reject(self.request('move', {'destination_id': 'EXIT'}), 'PRECONDITION_FAILED')
        self.route(37)

    def test_strict_interact_auth_replay_and_stale_versions(self):
        self.route(end=3)
        for arguments in [{}, {'object_id': 'r1_cabinet'}, {'target_id': 'r1_cabinet', 'state': 'OPEN'}, {'target_id': 1}, {'target_id': None}]:
            self.reject(self.request('interact', arguments), 'BAD_ARGUMENT', 422)
        request = self.request('interact', {'target_id': 'r1_cabinet'})
        before = self.state()
        foreign = self.create()
        for headers in [{}, self.headers(foreign), {'X-Session-Token': 'not-valid'}]:
            status, body = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/actions", headers=headers,
                json=request, definition='action_response')
            self.assertEqual(status, 403)
            self.assertIsNone(body['visible_state'])
            self.assertEqual(self.state(), before)
        status, first = self.post(request)
        self.assertEqual(status, 200)
        self.action('inspect', {'object_id': 'access_card'})
        status, replay = self.post(request)
        self.assertEqual(status, 200)
        self.assertTrue(replay['data']['replayed'])
        self.assertEqual(first['data']['receipt'], replay['data']['receipt'])
        self.assertEqual(replay['data']['visible_state'], self.state())
        self.reject({**request, 'arguments': {'target_id': 'r1_note'}}, 'REQUEST_ID_CONFLICT')
        self.reject(self.request('interact', {'target_id': 'r1_cabinet'}, state=before), 'STALE_STATE')
        self.control('save')
        stale = self.request('take', {'item_id': 'access_card'})
        self.control('restore')
        self.reject(stale, 'STALE_GENERATION')

    def test_corrupted_and_cross_version_snapshots_never_overwrite_session(self):
        self.route(end=24)
        self.control('save')
        with closing(sqlite3.connect(self.db)) as db:
            raw = db.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (self.session['session_id'],)).fetchone()[0]
        baseline = json.loads(raw)
        cases = [
            ('checksum', lambda s: s.update(checksum='0' * 64), 'INVALID_SNAPSHOT'),
            ('legacy-version', lambda s: s.update(schema_version='1.0.0', level_version='2.0.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('future-version', lambda s: s.update(level_version='3.2.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('owner', lambda s: s.update(session_id='another-session'), 'INVALID_SNAPSHOT'),
            ('unknown-device', lambda s: s['game_fields']['device_states'].update(computer='HACKED'), 'INVALID_SNAPSHOT'),
            ('extra-device', lambda s: s['game_fields']['device_states'].update(extra='OPEN'), 'INVALID_SNAPSHOT'),
            ('flags-power', lambda s: s['game_fields']['flags'].update(power_on=False), 'INVALID_SNAPSHOT'),
            ('duplicate-observation', lambda s: s['game_fields']['observed_object_ids'].append('r2_monitor'), 'INVALID_SNAPSHOT'),
            ('unknown-observation', lambda s: s['game_fields']['observed_object_ids'].append('hidden_device'), 'INVALID_SNAPSHOT'),
            ('card-lifecycle', lambda s: s['game_fields']['device_states'].update(cabinet='LOCKED'), 'INVALID_SNAPSHOT'),
            ('fuse-lifecycle', lambda s: s['game_fields']['consumed_item_ids'].remove('fuse'), 'INVALID_SNAPSHOT'),
            ('future-exit', lambda s: s['game_fields']['device_states'].update(exit='OPEN'), 'INVALID_SNAPSHOT'),
            ('marker', lambda s: s['game_fields'].update(level_version='2.0.0'), 'INVALID_SNAPSHOT'),
            ('client-state', lambda s: s['game_fields'].update(revision=0), 'INVALID_SNAPSHOT'),
            ('missing-devices', lambda s: s['game_fields'].pop('device_states'), 'INVALID_SNAPSHOT'),
        ]
        for name, mutate, code in cases:
            with self.subTest(case=name):
                broken = copy.deepcopy(baseline)
                mutate(broken)
                if name != 'checksum':
                    broken['checksum'] = digest(broken)
                value = json.dumps(broken, ensure_ascii=False)
                with closing(sqlite3.connect(self.db)) as db:
                    db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (value, self.session['session_id']))
                    db.commit()
                    session_before = db.execute('SELECT state_json FROM sessions WHERE session_id=?', (self.session['session_id'],)).fetchone()[0]
                before = self.state()
                self.control('restore', 409, code)
                self.assertEqual(self.state(), before)
                with closing(sqlite3.connect(self.db)) as db:
                    self.assertEqual(db.execute('SELECT state_json FROM sessions WHERE session_id=?', (self.session['session_id'],)).fetchone()[0], session_before)
                    self.assertEqual(db.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (self.session['session_id'],)).fetchone()[0], value)
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (raw, self.session['session_id']))
            db.commit()
        self.control('restore')

    def test_ai_read_callbacks_precheck_confirmation_and_new_generation(self):
        # The read callback must reveal observation affordances using upgrade rules.
        data, provider = self.ai([reply(calls=[call('inspect', {'object_id': 'r1_cabinet'})]),
            final('submit_code', {'target_id': 'r1_cabinet', 'code': '382'})])
        self.assertIn('r1_cabinet', data['visible_state']['observed_object_ids'])
        self.assertEqual(data['usage']['read_tool_calls'], 1)
        proposal = data['proposal']
        self.assertIsNotNone(proposal)
        status, accepted = self.decide(proposal)
        self.assertEqual(status, 200)
        self.assertEqual(accepted['data']['visible_state']['device_states']['cabinet'], 'CODE_ACCEPTED')
        self.assertNotIn('access_card', [i['item_id'] for i in self.state()['inventory']])
        before = self.state()
        data, _ = self.ai([final('take', {'item_id': 'access_card'})])
        self.assertIsNone(data['proposal'])
        self.assertEqual(self.state(), before)
        self.action('interact', {'target_id': 'r1_cabinet'})
        self.action('inspect', {'object_id': 'access_card'})
        data, _ = self.ai([final('take', {'item_id': 'access_card'})])
        proposal = data['proposal']
        self.assertIsNotNone(proposal)
        self.control('save')
        self.control('restore')
        status, rejected = self.decide(proposal)
        self.assertEqual(status, 409)
        self.assertEqual(rejected['error']['code'], 'PROPOSAL_INVALIDATED')
        self.route(5, 12)
        before = self.state()
        data, _ = self.ai([final('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'})])
        self.assertIsNone(data['proposal'])
        self.assertEqual(self.state(), before)
        self.route(12, 14)
        data, _ = self.ai([final('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'})])
        self.assertIsNotNone(data['proposal'])
        status, confirmed = self.decide(data['proposal'])
        self.assertEqual(status, 200)
        self.assertEqual(confirmed['data']['visible_state']['device_states']['powerbox'], 'FUSE_INSTALLED')
        self.assertFalse(self.state()['progress']['power_on'])
        for begin, end, tool, args in [
            (15, 19, 'submit_code', {'target_id': 'r2_monitor', 'code': '724'}),
            (19, 22, 'submit_code', {'target_id': 'r2_drawer', 'code': '724'}),
        ]:
            self.route(begin, end)
            before = self.state()
            data, _ = self.ai([final(tool, args)])
            self.assertIsNone(data['proposal'])
            self.assertEqual(self.state(), before)
        self.route(22, 33)
        data, _ = self.ai([final('submit_code', {'target_id': 'r3_panel', 'code': '231'})])
        self.assertIsNone(data['proposal'])
        self.route(33, 35)
        data, _ = self.ai([final('submit_code', {'target_id': 'r3_panel', 'code': '231'})])
        self.assertIsNotNone(data['proposal'])
        status, confirmed = self.decide(data['proposal'])
        self.assertEqual(status, 200)
        self.assertEqual(confirmed['data']['visible_state']['device_states']['exit'], 'FINAL_CHECK')
        self.assertTrue(confirmed['data']['visible_state']['progress']['check_done'])
        data, _ = self.ai([final('move', {'destination_id': 'EXIT'})])
        self.assertIsNone(data['proposal'])
        self.assertEqual(self.state()['status'], 'playing')

    def test_checksum_valid_final_check_without_panel_observation_is_rejected(self):
        self.route(end=36)
        self.control('save')
        with closing(sqlite3.connect(self.db)) as db:
            raw = db.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (self.session['session_id'],)).fetchone()[0]
            state_before = db.execute('SELECT state_json FROM sessions WHERE session_id=?', (self.session['session_id'],)).fetchone()[0]
        broken = json.loads(raw)
        fields = broken['game_fields']
        self.assertTrue(fields['flags']['check_done'])
        fields['observed_object_ids'].remove('r3_panel')
        fields['discovered_clue_ids'] = [clue for clue in fields['discovered_clue_ids'] if clue not in {'r3_panel_clue', 'r3_panel_observation'}]
        broken['checksum'] = digest(broken)
        tampered = json.dumps(broken, ensure_ascii=False)
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (tampered, self.session['session_id']))
            db.commit()
        before = self.state()
        self.control('restore', 409, 'INVALID_SNAPSHOT')
        self.assertEqual(self.state(), before)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT state_json FROM sessions WHERE session_id=?', (self.session['session_id'],)).fetchone()[0], state_before)
            self.assertEqual(db.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (self.session['session_id'],)).fetchone()[0], tampered)

    def test_upgrade_provider_settings_same_ledger_and_ephemeral_credentials(self):
        from backend.app.ai.provider import DeepSeekProvider
        from tests.api.test_play_ai_settings import KEY_A, KEY_B, final as provider_final
        seen = []
        async def complete(provider, messages, tools, limits, **kwargs):
            seen.append((provider.config, copy.deepcopy(messages), limits))
            return provider_final()
        request = {**self.version(), 'message': '合成问句 ' + KEY_A}
        url = f"/api/sessions/{self.session['session_id']}/ai/turns"
        headers = {**self.headers(), 'X-AI-Provider': 'deepseek', 'X-AI-Api-Key': KEY_A}
        before = self.state()
        with patch.object(DeepSeekProvider, 'complete', complete):
            first = self.client.post(url, headers=headers, json=request)
            repeat = self.client.post(url, headers={**headers, 'X-AI-Api-Key': KEY_B}, json={**request, 'message': '合成问句 ' + KEY_B})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(first.json()['data']['turn_id'], repeat.json()['data']['turn_id'])
        self.assertEqual(len(seen), 1)
        config, messages, limits = seen[0]
        self.assertEqual(config.api_key, KEY_A)
        self.assertEqual(config.model, 'deepseek-flash')
        self.assertEqual(config.base_url, 'https://api.deepseek.com')
        self.assertLessEqual(limits.max_tokens, 1000)
        self.assertLessEqual(limits.timeout_seconds, 20)
        self.assertEqual(self.state(), before)
        with closing(sqlite3.connect(self.db)) as db:
            dump = '\n'.join(db.iterdump())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ai_turns').fetchone()[0], 1)
        public_and_messages = json.dumps([first.json(), repeat.json(), messages], ensure_ascii=False)
        for key in [KEY_A, KEY_B]:
            self.assertNotIn(key, public_and_messages)
            self.assertNotIn(key, dump)
            self.assertNotIn(key.encode(), self.db.read_bytes())
        invalid = self.client.post(url, headers={**self.headers(), 'X-AI-Provider': 'deepseek'}, json={**self.version(), 'message': '没有密钥'})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(self.state(), before)
        free = self.client.post(url, headers={**self.headers(), 'X-AI-Provider': 'mock'}, json={**self.version(), 'message': '免费离线'})
        self.assertEqual(free.status_code, 200)
        self.assertEqual(free.json()['data']['usage']['provider'], 'mock')
