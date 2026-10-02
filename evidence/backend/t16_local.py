"""T16 Backend owner checks with explicit local mock/Fake injections only."""
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
import sqlite3
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

os.environ['AI_PROVIDER'] = 'mock'
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from backend.app.ai.mock import DeterministicMockProvider
from backend.app.ai.provider import ProviderError, ProviderResult
from backend.app.ai.runtime import Runtime, RuntimeLimits, UnavailableProvider, create_provider
from backend.app.ai.provider import DeepSeekConfig
from backend.app.ai.types import ProposalCandidate, TurnResult, Version
from backend.app.main import create_app
from backend.app.storage.sqlite import Store, canonical

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'contracts/api.schema.json').read_text(encoding='utf-8'))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
CHECKS = []


def check(name):
    CHECKS.append({'check': name, 'passed': True})


class CountingMock(DeterministicMockProvider):
    def __init__(self):
        self.calls = 0
        self.messages = []
    async def complete(self, messages, tools, limits, **kwargs):
        self.calls += 1
        self.messages.append(copy.deepcopy(messages))
        return await super().complete(messages, tools, limits, **kwargs)


class GateProvider:
    provider_name = 'mock'
    model_name = 'local-gated'
    def __init__(self):
        self.calls = 0
        self.entered, self.release = threading.Event(), threading.Event()
    async def complete(self, messages, tools, limits, **kwargs):
        self.calls += 1
        self.entered.set()
        while not self.release.is_set():
            await asyncio.sleep(0.01)
        return ProviderResult(json.dumps({'answer': '当前信息待确认。', 'clue_refs': [], 'proposal': None}), (), None, 'mock', self.model_name, self.model_name, 'stop')


class FaultProvider:
    provider_name = 'mock'
    model_name = 'local-fault'
    def __init__(self, kind):
        self.kind, self.calls = kind, 0
    async def complete(self, messages, tools, limits, **kwargs):
        self.calls += 1
        if self.kind == 'timeout':
            await asyncio.sleep(0.05)
        if self.kind == 'unavailable':
            raise ProviderError('MODEL_UNAVAILABLE')
        if self.kind == 'bad_code':
            content = {'answer': '尝试建议。', 'clue_refs': [], 'proposal': {'tool': 'submit_code', 'arguments': {'target_id': 'r1_cabinet', 'code': '999'}, 'clue_refs': [], 'summary': '尝试。'}}
        elif self.kind == 'unknown_refs':
            content = {'answer': '引用。', 'clue_refs': ['invented_clue'], 'proposal': None}
        else:
            return ProviderResult('invalid json', (), {'prompt_tokens': 2, 'completion_tokens': 1}, 'mock', self.model_name, self.model_name, 'stop')
        return ProviderResult(json.dumps(content), (), None, 'mock', self.model_name, self.model_name, 'stop')


class ExplodingRuntime:
    def __init__(self):
        self.calls = 0
    async def run(self, start, callbacks):
        self.calls += 1
        raise RuntimeError('not copied upstream content')


class FakeResultRuntime:
    def __init__(self, mode):
        self.mode, self.calls = mode, 0
    async def run(self, start, callbacks):
        self.calls += 1
        usage = {'provider': 'mock', 'model': 'local-result', 'input_tokens': None, 'output_tokens': None, 'model_calls': 0, 'read_tool_calls': 0}
        data = {'answer': '未执行任何动作。', 'clue_refs': [], 'status': 'completed', 'stop_reason': None, 'usage': usage}
        candidate = ProposalCandidate('submit_code', {'target_id': 'r1_cabinet', 'code': '999'}, (), '错误提案') if self.mode == 'bad_candidate' else None
        if self.mode == 'injected_state':
            data['visible_state'] = {'status': 'won'}
        if self.mode == 'bad_usage':
            data['usage'] = {'raw_provider_secret': 'must not persist'}
        return TurnResult(data, candidate, ({'kind': 'provider_error', 'raw': 'must not persist', 'token': 'must not persist'},), Version.from_state(start.visible_state))


class Session:
    def __init__(self, client):
        self.client, self.n = client, 0
        data = self.valid(client.post('/api/sessions', json={}), 201)['data']
        self.sid, self.token, self.state = data['session_id'], data['token'], data['visible_state']
        self.headers = {'X-Session-Token': self.token}
    def valid(self, response, expected=200):
        assert response.status_code == expected, (response.status_code, response.json().get('error'))
        value = response.json()
        VALIDATOR.validate(value)
        if hasattr(self, 'state'):
            state = value['data'].get('visible_state') if value['ok'] else value['visible_state']
            if state:
                self.state = state
        return value
    def version(self, key=None):
        self.n += 1
        return {'request_id': key or f'request_{self.n}', 'revision': self.state['revision'], 'generation': self.state['generation']}
    def action(self, tool, arguments, expected=200, raw=None):
        raw = raw or {**self.version(), 'tool': tool, 'arguments': arguments}
        return self.valid(self.client.post(f'/api/sessions/{self.sid}/actions', headers=self.headers, json=raw), expected)
    def control(self, operation):
        return self.valid(self.client.post(f'/api/sessions/{self.sid}/{operation}', headers=self.headers, json=self.version()))
    def ai(self, raw=None, expected=200, message='给一个下一步建议。'):
        raw = {**self.version(), 'message': message} if raw is None else raw
        return self.valid(self.client.post(f'/api/sessions/{self.sid}/ai/turns', headers=self.headers, json=raw), expected), raw
    def proposal(self, pid, operation='confirm', expected=200, raw=None):
        return self.valid(self.client.post(f'/api/sessions/{self.sid}/proposals/{pid}/{operation}', headers=self.headers, json={} if raw is None else raw), expected)
    def read(self):
        return self.valid(self.client.get(f'/api/sessions/{self.sid}/state', headers=self.headers))


def run():
    with tempfile.TemporaryDirectory(prefix='backend-t16-owner-') as temp:
        temp = Path(temp)
        provider = CountingMock()
        db = temp / 'game.sqlite'
        client = TestClient(create_app(db, provider=provider))
        player = Session(client)
        answer, first_raw = player.ai(message='看看值班室。 ' + player.token)
        assert answer['data']['status'] == 'completed' and player.state['revision'] == 2
        first = answer['data']['proposal']
        assert first['status'] == 'pending' and first['revision'] == 2
        assert answer['data']['usage']['provider'] == 'mock' and answer['data']['usage']['input_tokens'] is None
        assert all(player.token not in json.dumps(messages) for messages in provider.messages)
        first_calls = provider.calls
        replay, _ = player.ai(raw=first_raw)
        assert provider.calls == first_calls and replay['data']['turn_id'] == answer['data']['turn_id'] and replay['data']['proposal']['proposal_id'] == first['proposal_id']
        check('mock own inspect advances server cursor to rev2; proposal is pending; same-ID finished replay neither calls provider nor creates second proposal')
        with closing(sqlite3.connect(db)) as connection:
            assert player.token not in ''.join(row[0] for row in connection.execute('SELECT result_json FROM events'))
            assert player.token not in ''.join(row[0] or '' for row in connection.execute('SELECT request_json FROM events'))
        confirmed = player.proposal(first['proposal_id'])
        assert confirmed['data']['receipt']['changed'] and player.state['revision'] == 3
        repeated = player.proposal(first['proposal_id'])
        assert repeated['data']['replayed'] and repeated['data']['receipt'] == confirmed['data']['receipt'] and player.state['revision'] == 3
        assert player.proposal(first['proposal_id'], 'cancel', 409)['error']['code'] == 'PROPOSAL_REJECTED'
        replay, _ = player.ai(raw=first_raw)
        assert replay['data']['proposal']['status'] == 'committed' and replay['data']['visible_state']['revision'] == 3
        check('confirm executes stored arguments once; repeat returns immutable receipt/current state; committed cancel rejects; turn replay reads current proposal status')
        next_turn, _ = player.ai()
        pid = next_turn['data']['proposal']['proposal_id']
        cancelled = player.proposal(pid, 'cancel')
        assert cancelled['data']['proposal']['status'] == 'cancelled' and player.state['revision'] == 3
        assert player.proposal(pid, 'cancel')['data']['proposal']['status'] == 'cancelled'
        assert player.proposal(pid, expected=409)['error']['code'] == 'PROPOSAL_CANCELLED'
        check('cancel and repeated cancel do not progress; cancelled confirmation refuses')
        one, _ = player.ai()
        two, _ = player.ai()
        assert one['data']['proposal']['proposal_id'] != two['data']['proposal']['proposal_id']
        assert player.proposal(one['data']['proposal']['proposal_id'], expected=409)['error']['code'] == 'PROPOSAL_INVALIDATED'
        with closing(sqlite3.connect(db)) as connection:
            assert connection.execute("SELECT COUNT(*) FROM proposals WHERE session_id=? AND json_extract(proposal_json,'$.status')='pending'", (player.sid,)).fetchone()[0] == 1
        check('one pending proposal per session; new legal proposal invalidates previous pending')
        pid = two['data']['proposal']['proposal_id']
        assert player.proposal(pid, raw={'code': '999'}, expected=422)['error']['code'] == 'BAD_ARGUMENT'
        player.action('take', {'item_id': 'access_card'})
        assert player.proposal(pid, expected=409)['error']['code'] == 'PROPOSAL_INVALIDATED'
        check('fixed empty confirm body rejects client replacement; actual manual mutation invalidates pending')
        # Full AI path after initial manual card pickup: every progress receipt comes from confirm.
        for _ in range(20):
            if player.state['status'] == 'won':
                break
            turn, _ = player.ai()
            assert turn['data']['status'] != 'stopped', turn['data']['stop_reason']
            proposal = turn['data']['proposal']
            assert proposal is not None
            before = player.state['revision']
            commit = player.proposal(proposal['proposal_id'])
            assert commit['data']['receipt']['revision_before'] == before
        assert player.state['status'] == 'won' and player.state['room']['room_id'] == 'EXIT'
        assert 'emergency_key' in [item['item_id'] for item in player.state['inventory']]
        assert 'fuse' not in [item['item_id'] for item in player.state['inventory']]
        check('complete three-room AI mock route via fixed proposals/confirm; fuse consumed and baseline key retained')
        with client.app.state.store.transaction() as connection:
            current = client.app.state.store.authenticate(connection, player.sid, player.token)
            history = client.app.state.store.safe_history(connection, player.sid, current)
            assert len(history) > 12 and any(entry['kind'] == 'ai_turn' for entry in history)
            assert all('token' not in entry and 'game_fields' not in entry for entry in history)
            traces = [json.loads(row['trace_json']) for row in connection.execute("SELECT trace_json FROM ai_turns WHERE session_id=? AND phase='completed'", (player.sid,))]
            first_trace = traces[0]
            started_trace = next(entry for entry in first_trace if entry['kind'] == 'turn_started')
            assert started_trace['revision'] == 0 and started_trace['generation'] == first['generation']
            assert started_trace['limits']['model_calls'] == 3 and started_trace['context_mode'] == 'full_history'
            read_trace = next(entry for entry in first_trace if entry['kind'] == 'read_tool')
            assert read_trace['arguments'] and read_trace['observation'] is not None and 'revision' in read_trace
            final_trace = next(entry for entry in first_trace if entry['kind'] == 'turn_finished')
            assert final_trace['usage']['model_calls'] == answer['data']['usage']['model_calls']
            assert all(player.token not in json.dumps(trace) and 'opened_containers' not in json.dumps(trace) for trace in traces)
        check('current-generation full public history exceeds 12 records; trace retains actual versions/limits/tool inputs/results/usage while excluding capability/private fields')
        player.control('save')
        assert player.state['save'] is not None
        player.control('reset')
        assert player.proposal(first['proposal_id'], expected=409)['error']['code'] == 'PROPOSAL_INVALIDATED'
        assert player.proposal(first['proposal_id'], 'cancel', 409)['error']['code'] == 'PROPOSAL_INVALIDATED'
        assert player.ai(raw=first_raw, expected=409)[0]['error']['code'] == 'STALE_GENERATION'
        restored = player.control('restore')
        assert player.state['status'] == 'won' and restored['data']['visible_state']['save'] is not None
        check('reset/restore invalidate even committed proposal generations; old turn replay denied; save metadata projects through AI and errors')
        # Every provider context contains only public state/history fields.
        for messages in provider.messages:
            context = json.loads(next(message['content'] for message in messages if message['role'] == 'user'))
            assert not ({'flags', 'opened_containers', 'game_fields', 'checksum', 'token'} & set(context['visible_state']))
            text = json.dumps(messages, ensure_ascii=False)
            assert player.token not in text and 'game_fields' not in text and 'opened_containers' not in text
        check('context spy sees public projections only; current capability never enters model or events')
        client.close()

        # Pending reservation and external mutation: no writer lock during provider await.
        gate = GateProvider()
        race_db = temp / 'race.sqlite'
        race_client = TestClient(create_app(race_db, provider=gate))
        race = Session(race_client)
        raw = {**race.version('gated'), 'message': '读取状态。'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(race.ai, raw)
            assert gate.entered.wait(3)
            pending, _ = race.ai(raw=raw, expected=503)
            assert pending['error']['code'] == 'MODEL_UNAVAILABLE' and gate.calls == 1
            conflict = {**race.version('gated'), 'tool': 'get_inventory', 'arguments': {}}
            assert race.action('get_inventory', {}, 409, conflict)['error']['code'] == 'REQUEST_ID_CONFLICT'
            race.action('inspect', {'object_id': 'r1_note'})
            gate.release.set()
            stopped, _ = future.result(timeout=5)
        assert stopped['data']['status'] == 'stopped' and stopped['data']['stop_reason'] == 'STALE_STATE' and stopped['data']['proposal'] is None
        assert stopped['data']['usage']['model_calls'] == 1 and stopped['data']['usage']['input_tokens'] is None
        assert stopped['data']['visible_state']['revision'] == 1
        race.ai(raw=raw)
        assert gate.calls == 1
        check('pending duplicate gets 503 without second call; shared namespace conflict; manual action commits during network wait and stale turn stops with true usage')
        # Direct expected-version spoof must not hop over manual updates.
        store = race_client.app.state.store
        new_raw = {**race.version('callback_boundary'), 'message': '只读。'}
        start, callbacks = store.begin_ai(race.sid, race.token, new_raw)
        async def boundary_checks():
            snapshot = await callbacks.snapshot(Version.from_state(start.visible_state))
            rejected = await callbacks.read_tool(Version.from_state(snapshot.visible_state), 'take', {'item_id': 'access_card'})
            assert not rejected.ok and rejected.error_code == 'INVALID_TOOL'
            first_read = await callbacks.read_tool(Version.from_state(snapshot.visible_state), 'inspect', {'object_id': 'r1_cabinet'})
            assert first_read.ok and first_read.visible_state['revision'] == 2
            try:
                await callbacks.snapshot(Version(3, first_read.visible_state['generation']))
            except Exception as error:
                assert getattr(error, 'code', None) == 'STALE_STATE'
            else:
                raise AssertionError('cursor spoof allowed')
        asyncio.run(boundary_checks())
        store.abandon_ai(race.sid, start.turn_id)
        race_client.close()
        rebuilt_provider = CountingMock()
        rebuilt = TestClient(create_app(race_db, provider=rebuilt_provider))
        race.client = rebuilt
        assert race.ai(raw=new_raw, expected=503)[0]['error']['code'] == 'MODEL_UNAVAILABLE'
        assert rebuilt_provider.calls == 0
        check('callbacks reject progress tools and forged expected cursor; abandoned durable claim stays tombstoned after service reconstruction')
        rebuilt.close()

        restore_gate = GateProvider()
        restore_client = TestClient(create_app(temp / 'restore-race.sqlite', provider=restore_gate))
        restore_player = Session(restore_client)
        restore_player.control('save')
        restore_raw = {**restore_player.version('inflight_restore'), 'message': '等待。'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(restore_player.ai, restore_raw)
            assert restore_gate.entered.wait(3)
            restore_player.control('reset')
            restore_player.control('restore')
            new_generation = restore_player.state['generation']
            restore_gate.release.set()
            stopped, _ = future.result(timeout=5)
        assert stopped['data']['status'] == 'stopped' and stopped['data']['proposal'] is None and stopped['data']['stop_reason'] == 'STALE_STATE'
        assert stopped['data']['visible_state']['generation'] == new_generation and stopped['data']['visible_state']['revision'] == 2
        assert stopped['data']['usage']['model_calls'] == 1 and stopped['data']['visible_state']['save'] is not None
        assert restore_player.ai(raw=restore_raw, expected=409)[0]['error']['code'] == 'STALE_GENERATION'
        check('reset/restore during model await stop old turn, retain truthful call count/current slot/new generation and forbid old request replay')
        restore_client.close()

        # Factory configuration faults are synthetic and cannot read .env or send
        # any network request: from_environment is patched with local dataclasses.
        for label, config in [('missing_credentials', DeepSeekConfig('')), ('invalid_model', DeepSeekConfig('synthetic-not-a-real-key', model='unapproved-local')), ('invalid_base', DeepSeekConfig('synthetic-not-a-real-key', base_url='https://invalid.local'))]:
            with patch.dict(os.environ, {'AI_PROVIDER': 'deepseek'}), patch('backend.app.ai.runtime.DeepSeekConfig.from_environment', return_value=config):
                unavailable = create_provider()
                assert isinstance(unavailable, UnavailableProvider)
                app = create_app(temp / ('config-' + label + '.sqlite'), provider=unavailable)
                local = TestClient(app)
                assert local.get('/api/health').status_code == 200
                target = Session(local)
                target.action('inspect', {'object_id': 'r1_note'})
                result, _ = target.ai()
                assert result['data']['stop_reason'] == 'MODEL_UNAVAILABLE' and result['data']['usage']['provider'] == 'deepseek'
                assert target.state['revision'] == 1 and result['data']['usage']['input_tokens'] is None
                local.close()
            check('synthetic factory fault preserves health/session/manual action and returns truthful AI unavailable: ' + label)
        with patch.dict(os.environ, {'AI_PROVIDER': 'unknown-synthetic'}):
            unavailable = create_provider()
            assert isinstance(unavailable, UnavailableProvider)
            local = TestClient(create_app(temp / 'config-unknown.sqlite', provider=unavailable))
            target = Session(local)
            target.action('inspect', {'object_id': 'r1_note'})
            result, _ = target.ai()
            assert result['data']['usage']['provider'] == 'unavailable' and result['data']['stop_reason'] == 'MODEL_UNAVAILABLE'
            local.close()
        check('unknown provider configuration remains explicit unavailable, with manual progress intact')

        # Provider malformed/timeout/unavailable and untrusted runtime data.
        for kind in ('timeout', 'unavailable', 'bad_json', 'unknown_refs', 'bad_code'):
            fault = FaultProvider(kind)
            runtime = Runtime(provider=fault, limits=RuntimeLimits(call_seconds=0.02, total_seconds=1))
            local = TestClient(create_app(temp / (kind + '.sqlite'), runtime=runtime))
            target = Session(local)
            result, request = target.ai()
            assert result['data']['status'] == 'stopped' and result['data']['proposal'] is None and target.state['revision'] == 0
            assert result['data']['usage']['model_calls'] == fault.calls and fault.calls <= 3
            before = fault.calls
            target.ai(raw=request)
            assert fault.calls == before
            check('stopped fault turn records true calls/current state and immutable replay: ' + kind)
            local.close()
        for mode in ('bad_candidate', 'injected_state', 'bad_usage'):
            runtime = FakeResultRuntime(mode)
            local = TestClient(create_app(temp / (mode + '.sqlite'), runtime=runtime))
            target = Session(local)
            result, request = target.ai(expected=502 if mode == 'bad_usage' else 200)
            if mode != 'bad_usage':
                assert result['data']['status'] == 'stopped' and result['data']['proposal'] is None
            assert target.state['revision'] == 0 and target.state['status'] == 'playing'
            with closing(sqlite3.connect(temp / (mode + '.sqlite'))) as connection:
                trace = connection.execute('SELECT trace_json FROM ai_turns').fetchone()[0]
                assert 'must not persist' not in trace and 'raw_provider_secret' not in trace
            check('backend independently refuses untrusted runtime result: ' + mode)
            local.close()
        explosive = ExplodingRuntime()
        unknown_db = temp / 'unknown.sqlite'
        local = TestClient(create_app(unknown_db, runtime=explosive))
        target = Session(local)
        target.ai(expected=503)
        replay_raw = {'request_id': 'request_1', 'revision': 0, 'generation': target.state['generation'], 'message': '给一个下一步建议。'}
        target.ai(raw=replay_raw, expected=503)
        assert explosive.calls == 1
        check('unexpected runtime error creates durable unknown tombstone; same ID never restarts upstream work')
        local.close()

        # TTL, ownership, cancellation and confirmation races on real stored proposals.
        local = TestClient(create_app(temp / 'proposals.sqlite', provider=CountingMock()))
        target, foreign = Session(local), Session(local)
        result, _ = target.ai()
        pid = result['data']['proposal']['proposal_id']
        assert foreign.proposal(pid, expected=404)['error']['code'] == 'PROPOSAL_NOT_FOUND'
        with closing(sqlite3.connect(temp / 'proposals.sqlite')) as connection, connection:
            proposal = json.loads(connection.execute('SELECT proposal_json FROM proposals WHERE proposal_id=?', (pid,)).fetchone()[0])
            proposal['expires_at'] = '2000-01-01T00:00:00Z'
            connection.execute('UPDATE proposals SET proposal_json=? WHERE proposal_id=?', (canonical(proposal), pid))
        assert target.proposal(pid, expected=409)['error']['code'] == 'PROPOSAL_EXPIRED'
        assert target.proposal(pid, 'cancel', 409)['error']['code'] == 'PROPOSAL_EXPIRED'
        result, _ = target.ai()
        pid = result['data']['proposal']['proposal_id']
        def confirm():
            response = local.post(f'/api/sessions/{target.sid}/proposals/{pid}/confirm', headers=target.headers, json={})
            value = response.json()
            VALIDATOR.validate(value)
            return response.status_code, value
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: confirm(), range(2)))
        assert all(status == 200 for status, _ in responses)
        assert sorted(value['data']['replayed'] for _, value in responses) == [False, True]
        assert responses[0][1]['data']['receipt'] == responses[1][1]['data']['receipt']
        target.read()
        assert target.state['revision'] == 3
        check('foreign proposal is not found; expired confirm/cancel refuse; concurrent confirm has exactly one committed receipt')
        result, _ = target.ai()
        pid = result['data']['proposal']['proposal_id']
        def either(operation):
            response = local.post(f'/api/sessions/{target.sid}/proposals/{pid}/{operation}', headers=target.headers, json={})
            value = response.json()
            VALIDATOR.validate(value)
            return operation, response.status_code, value
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(either, ('confirm', 'cancel')))
        assert sorted(status for _, status, _ in responses) == [200, 409]
        loser = [value for _, status, value in responses if status == 409][0]
        assert loser['error']['code'] in {'PROPOSAL_CANCELLED', 'PROPOSAL_REJECTED'}
        check('confirm/cancel race has one terminal winner and no second progress')
        for raw in ({}, {**target.version(), 'message': ''}, {**target.version(), 'message': 'x' * 2001}, {**target.version(), 'message': 'ok', 'scenario': 'client-controlled'}):
            assert target.ai(raw=raw, expected=422)[0]['error']['code'] == 'BAD_ARGUMENT'
        check('strict AI envelope rejects missing/empty/oversize message and HTTP scenario injection')
        local.close()

        # Run actual exported old M2 Store, not a simulated schema.
        legacy_path = ROOT / 'data/integration/m2-legacy-sqlite-165a961.py'
        assert hashlib.sha256(legacy_path.read_bytes()).hexdigest() == '21d992feb895ce5535c6b0b3d731887be9619171351a551935e1d10fc2bfae22'
        spec = importlib.util.spec_from_file_location('backend.app.storage.m2_legacy', legacy_path)
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        migration_db = temp / 'legacy.sqlite'
        old = legacy.Store(migration_db)
        _, create = old.create({})
        sid, token = create['data']['session_id'], create['data']['token']
        original = create['data']['visible_state']
        action_raw = {'request_id': 'm2_action', 'revision': 0, 'generation': original['generation'], 'tool': 'inspect', 'arguments': {'object_id': 'r1_note'}}
        _, old_action = old.action(sid, token, action_raw)
        save_raw = {'request_id': 'm2_save', 'revision': 1, 'generation': original['generation']}
        _, old_save = old.control(sid, token, 'save', save_raw)
        failure_raw = {'request_id': 'm2_failure', 'revision': 1, 'generation': original['generation'], 'tool': 'submit_code', 'arguments': {'target_id': 'r1_cabinet', 'code': '999'}}
        old_failure_status, old_failure = old.action(sid, token, failure_raw)
        with closing(sqlite3.connect(migration_db)) as connection:
            assert len(connection.execute('PRAGMA table_info(action_receipts)').fetchall()) == 6
        migrated = Store(migration_db)
        migrated_again = Store(migration_db)
        _, replay_action = migrated.action(sid, token, action_raw)
        _, replay_save = migrated.control(sid, token, 'save', save_raw)
        failure_status, replay_failure = migrated.action(sid, token, failure_raw)
        assert failure_status == old_failure_status and replay_failure['event_id'] == old_failure['event_id'] and replay_failure['visible_state']['save'] is not None
        assert replay_action['data']['replayed'] and replay_action['data']['receipt'] == old_action['data']['receipt']
        assert replay_save['data']['replayed'] and replay_save['data']['visible_state']['save'] == old_save['data']['visible_state']['save']
        fresh = {'request_id': 'after_migration', 'revision': 1, 'generation': original['generation'], 'tool': 'inspect', 'arguments': {'object_id': 'r1_cabinet'}}
        status, fresh_response = migrated_again.action(sid, token, fresh)
        assert status == 200 and fresh_response['data']['visible_state']['revision'] == 2
        with closing(sqlite3.connect(migration_db)) as connection:
            assert connection.execute("SELECT COUNT(*) FROM action_receipts WHERE phase='completed'").fetchone()[0] == 4
            assert len(connection.execute('PRAGMA table_info(action_receipts)').fetchall()) == 7
        check('actual Git-exported M2 six-column Store generated DB migrates idempotently; old action/save/failure receipts replay unchanged; new explicit-column inserts work')


if __name__ == '__main__':
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'evidence/backend' / ('t16-local-' + stamp + '.json')
    record = {'scope': 'Backend owner local mock checks; not formal T18 QA', 'command': r'C:\Users\liyh\.conda\envs\1\python.exe -m evidence.backend.t16_local', 'started_at': stamp, 'paid_model_calls': 0, 'explicit_local_provider': True, 'checks': CHECKS}
    try:
        run()
    except Exception as error:
        record.update(exit_code=1, failure_type=type(error).__name__)
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
    else:
        paths = [ROOT / 'backend/app/storage/ai.py', ROOT / 'backend/app/storage/sqlite.py', ROOT / 'backend/app/domain/models.py', ROOT / 'backend/app/api/routes.py', ROOT / 'backend/app/main.py']
        record.update(exit_code=0, source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'PASS {len(CHECKS)} Backend T16 local checks; evidence {output.name}; no paid calls')



