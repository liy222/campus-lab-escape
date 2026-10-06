"""Independent gameplay credential boundaries; synthetic sentinels, no network."""
import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

os.environ['AI_PROVIDER'] = 'mock'  # Never load .env or instantiate a paid default.
from fastapi.testclient import TestClient
from backend.app.ai.provider import DeepSeekProvider, ProviderError, ProviderResult
from backend.app.ai.runtime import Runtime
from backend.app.main import create_app

KEY_A = 'SYNTHETIC_QA_SENTINEL_A_NOT_A_REAL_KEY'
KEY_B = 'SYNTHETIC_QA_SENTINEL_B_NOT_A_REAL_KEY'
ROOT = Path(__file__).resolve().parents[2]


def final(provider='deepseek'):
    return ProviderResult(json.dumps({'answer': '请继续观察已发现线索。', 'clue_refs': [], 'proposal': None}, ensure_ascii=False),
                          (), {'prompt_tokens': 11, 'completion_tokens': 7}, provider,
                          'deepseek-flash' if provider == 'deepseek' else 'qa-injected',
                          'deepseek-flash' if provider == 'deepseek' else 'qa-injected', 'stop')


class Injected:
    provider_name, model_name = 'mock', 'qa-injected'
    def __init__(self):
        self.calls = 0
    async def complete(self, *args, **kwargs):
        self.calls += 1
        return final('mock')


class PlayAiSettings(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='play-ai-offline-qa-')
        self.db = Path(self.temp.name) / 'game.sqlite'
        self.injected = Injected()
        self.app = create_app(self.db, runtime=Runtime(self.injected))
        self.client = TestClient(self.app)
        self.sessions = [self.client.post('/api/sessions', json={}).json()['data'] for _ in range(2)]
        self.network = patch('httpx.AsyncClient.send', side_effect=AssertionError('Network forbidden in independent QA'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        self.client.close()
        self.temp.cleanup()

    def state(self, index=0):
        s = self.sessions[index]
        return self.client.get(f"/api/sessions/{s['session_id']}/state", headers={'X-Session-Token': s['token']}).json()['data']['visible_state']

    def body(self, index=0, message='下一步建议', request_id=None):
        state = self.state(index)
        return {'request_id': request_id or uuid.uuid4().hex, 'generation': state['generation'], 'revision': state['revision'], 'message': message}

    def turn(self, provider=None, key=None, index=0, body=None, extras=()):
        s = self.sessions[index]
        headers = [('X-Session-Token', s['token'])]
        if provider is not None:
            headers.append(('X-AI-Provider', provider))
        if key is not None:
            headers.append(('X-AI-Api-Key', key))
        return self.client.post(f"/api/sessions/{s['session_id']}/ai/turns", headers=headers + list(extras), json=body or self.body(index))

    def assert_no_secrets(self, *values):
        encoded = json.dumps(values, ensure_ascii=False)
        self.assertFalse(any(k in encoded for k in (KEY_A, KEY_B)), 'Synthetic credential entered public/model content')
        with closing(sqlite3.connect(self.db)) as db:
            dump = '\n'.join(db.iterdump())
        self.assertFalse(any(k in dump for k in (KEY_A, KEY_B)), 'Synthetic credential entered SQLite content')
        self.assertFalse(any(k.encode() in self.db.read_bytes() for k in (KEY_A, KEY_B)), 'Synthetic credential entered SQLite bytes')

    def test_explicit_mock_is_free_offline_and_does_not_use_injected_runtime(self):
        with patch.object(DeepSeekProvider, 'complete', side_effect=AssertionError('Mock reached real adapter')):
            r = self.turn('mock', KEY_A)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['usage']['provider'], 'mock')
        self.assertEqual(self.injected.calls, 0)
        self.assert_no_secrets(r.json())

    def test_absent_headers_preserve_existing_runtime_injection(self):
        r = self.turn()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['usage']['model'], 'qa-injected')
        self.assertEqual(self.injected.calls, 1)

    def test_invalid_settings_auth_then_422_no_reservation_or_secrets(self):
        cases = [('deepseek', None, ()), ('deepseek', '', ()), ('bogus', KEY_A, ()),
                 ('deepseek', 'x' * 513, ()), ('deepseek', 'bad\tkey', ()),
                 (None, KEY_A, ()), ('x' * 17, KEY_A, ()),
                 ('mock', None, (('X-AI-Provider', 'deepseek'),)),
                 ('deepseek', KEY_A, (('X-AI-Api-Key', KEY_B),))]
        for provider, key, extra in cases:
            with self.subTest(case=cases.index((provider, key, extra))):
                before = self.state()
                with closing(sqlite3.connect(self.db)) as db:
                    initial = db.execute('SELECT COUNT(*) FROM ai_turns').fetchone()[0]
                r = self.turn(provider, key, extras=extra)
                self.assertEqual(r.status_code, 422, 'Invalid AI setting status')
                self.assertEqual(r.json()['error']['code'], 'BAD_ARGUMENT')
                self.assertEqual(self.state(), before)
                with closing(sqlite3.connect(self.db)) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM ai_turns').fetchone()[0], initial)
                self.assert_no_secrets(r.json())
        r = self.client.post(f"/api/sessions/{self.sessions[0]['session_id']}/ai/turns", headers={'X-AI-Provider': 'bogus'}, json=self.body())
        self.assertEqual(r.status_code, 403, 'Authentication must precede settings validation')

    def test_real_selection_is_fixed_offline_redacted_and_request_is_idempotent(self):
        seen = []
        async def complete(provider, messages, tools, limits, **kwargs):
            seen.append((provider.config, copy.deepcopy(messages), limits))
            return final()
        request = self.body(message='问句误粘 ' + KEY_A, request_id='qa-same-real-id')
        with patch.object(DeepSeekProvider, 'complete', complete):
            first = self.turn('deepseek', KEY_A, body=request)
            repeat = self.turn('deepseek', KEY_B, body={**request, 'message': '问句误粘 ' + KEY_B})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(first.json()['data']['turn_id'], repeat.json()['data']['turn_id'])
        self.assertEqual(len(seen), 1, 'Replay called model again')
        config, messages, limits = seen[0]
        self.assertEqual(config.api_key, KEY_A)
        self.assertEqual(config.model, 'deepseek-flash')
        self.assertEqual(config.base_url, 'https://api.deepseek.com')
        self.assertLessEqual(limits.max_tokens, 1000)
        self.assertLessEqual(limits.timeout_seconds, 20)
        self.assert_no_secrets(messages, first.json(), repeat.json())

    def test_two_sessions_parallel_different_keys_no_shared_runtime_mutation(self):
        seen, barrier = [], threading.Barrier(2)
        lock = threading.Lock()
        async def complete(provider, messages, tools, limits, **kwargs):
            with lock:
                seen.append((provider.config.api_key, copy.deepcopy(messages), id(provider)))
            await asyncio.to_thread(barrier.wait, 5)
            return final()
        with patch.object(DeepSeekProvider, 'complete', complete):
            with ThreadPoolExecutor(2) as pool:
                a = pool.submit(self.turn, 'deepseek', KEY_A, 0)
                b = pool.submit(self.turn, 'deepseek', KEY_B, 1)
                responses = [a.result(10), b.result(10)]
        self.assertEqual([r.status_code for r in responses], [200, 200])
        self.assertEqual(set(x[0] for x in seen), {KEY_A, KEY_B})
        self.assertEqual(len(set(x[2] for x in seen)), 2)
        self.assertIs(self.app.state.ai_runtime.provider, self.injected)
        self.assert_no_secrets([x[1] for x in seen], [r.json() for r in responses])
        self.assertEqual(self.turn().status_code, 200)
        self.assertEqual(self.injected.calls, 1)

    def test_real_failure_stops_once_without_retry_and_keeps_manual_gameplay(self):
        calls = []
        async def complete(provider, *args, **kwargs):
            calls.append(True)
            raise ProviderError('MODEL_TIMEOUT')
        request = self.body(request_id='qa-failed-once')
        before = self.state()
        with patch.object(DeepSeekProvider, 'complete', complete):
            r = self.turn('deepseek', KEY_A, body=request)
            repeat = self.turn('deepseek', KEY_A, body=request)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['stop_reason'], 'MODEL_TIMEOUT')
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.state(), before)
        manual = {k: v for k, v in self.body().items() if k != 'message'}
        manual.update(tool='inspect', arguments={'object_id': 'r1_note'})
        s = self.sessions[0]
        action = self.client.post(f"/api/sessions/{s['session_id']}/actions", headers={'X-Session-Token': s['token']}, json=manual)
        self.assertEqual(action.status_code, 200)
        self.assert_no_secrets(r.json(), repeat.json(), action.json())

    def test_selection_keeps_canonical_budget_and_ignores_environment_override(self):
        seen = []
        async def complete(provider, *args, **kwargs):
            seen.append((provider.ledger.path, provider.ledger.snapshot()))
            return final()
        canonical = ROOT / 'data' / 'ai-budget.sqlite'
        before = hashlib.sha256(canonical.read_bytes()).hexdigest() if canonical.exists() else None
        with patch.dict(os.environ, {'MODEL_BASE_URL': 'https://invalid.example', 'MODEL_NAME': 'unapproved', 'AI_BUDGET_PATH': str(Path(self.temp.name) / 'override.sqlite')}):
            with patch.object(DeepSeekProvider, 'complete', complete):
                self.assertEqual(self.turn('deepseek', KEY_A).status_code, 200)
                self.assertEqual(self.turn('mock').status_code, 200)
                self.assertEqual(self.turn('deepseek', KEY_B).status_code, 200)
        self.assertEqual([p for p, _ in seen], [canonical.resolve(), canonical.resolve()])
        self.assertEqual(seen[0][1], seen[1][1])
        self.assertFalse((Path(self.temp.name) / 'override.sqlite').exists())
        if before:
            self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(), before, 'Existing canonical budget changed during selection')


if __name__ == '__main__':
    unittest.main(verbosity=2)
