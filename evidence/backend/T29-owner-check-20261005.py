"""T29 backend owner checks; no provider, HTTP server, real DB or formal QA."""
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import threading
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.domain.models import GameState
from backend.app.domain.rules import CODES, LEVEL_VERSION, SCHEMA_VERSION, validate_invariants
from backend.app.storage.sqlite import Store, canonical, checksum
from backend.app.storage.ai import public_validator
from backend.app.ai.types import ProposalCandidate, TurnResult, Version

OUT = ROOT / 'evidence/backend/T29-owner-check-20261005.json'
records = []
checks = 0

def verify(condition, label):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(label)

def result(name, **data):
    records.append({'check': name, 'result': 'passed', **data})

KEY = ('use_item', {'item_id': 'emergency_key', 'target_id': 'r2_door'})
ROUTE = [
    ('inspect', {'object_id': 'r1_note'}), ('inspect', {'object_id': 'r1_cabinet'}),
    ('submit_code', {'target_id': 'r1_cabinet', 'code': CODES['r1_cabinet']}),
    ('take', {'item_id': 'access_card'}), ('use_item', {'item_id': 'access_card', 'target_id': 'r1_door'}),
    ('move', {'destination_id': 'R2'}), ('take', {'item_id': 'fuse'}),
    ('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}),
    ('inspect', {'object_id': 'r2_monitor'}), ('inspect', {'object_id': 'r2_drawer'}),
    ('submit_code', {'target_id': 'r2_drawer', 'code': CODES['r2_drawer']}),
    ('take', {'item_id': 'emergency_key'}), KEY, ('move', {'destination_id': 'R3'}),
    ('inspect', {'object_id': 'r3_checklist'}), ('inspect', {'object_id': 'r3_panel'}),
    ('submit_code', {'target_id': 'r3_panel', 'code': CODES['r3_panel']}),
    ('move', {'destination_id': 'EXIT'}),
]

class Fixture:
    def __init__(self, path):
        self.store = Store(path)
        status, body = self.store.create({})
        verify(status == 201, 'session creation')
        public_validator('create_response').validate(body)
        self.sid, self.token = body['data']['session_id'], body['data']['token']

    def state(self):
        status, body = self.store.read(self.sid, self.token)
        verify(status == 200, 'state read')
        public_validator('state_response').validate(body)
        return body['data']['visible_state']

    def version(self, state=None):
        state = state or self.state()
        return {'request_id': uuid4().hex, 'revision': state['revision'], 'generation': state['generation']}

    def request(self, tool, arguments, state=None):
        return {**self.version(state), 'tool': tool, 'arguments': arguments}

    def send(self, request):
        status, body = self.store.action(self.sid, self.token, request)
        public_validator('action_response' if body['ok'] else 'error_response').validate(body)
        return status, body

    def action(self, tool, arguments):
        status, body = self.send(self.request(tool, arguments))
        verify(status == 200, 'successful local action')
        return body['data']

    def reject(self, tool, arguments, code):
        before = self.state()
        status, body = self.send(self.request(tool, arguments))
        verify(status == 409 and body['error']['code'] == code, 'expected rule rejection')
        verify(self.state() == before, 'rule failure leaves state unchanged')
        return body

    def route(self, start=0, end=18):
        return [self.action(tool, arguments) for tool, arguments in ROUTE[start:end]]

    def control(self, operation, code=None):
        before = self.state()
        status, body = self.store.control(self.sid, self.token, operation, self.version(before))
        public_validator('error_response' if code else 'control_response').validate(body)
        if code:
            verify(status == 409 and body['error']['code'] == code, 'expected control rejection')
            verify(self.state() == before, 'restore rejection leaves state unchanged')
        else:
            verify(status == 200, 'successful control')
        return body

    def propose(self):
        before = self.state()
        begun = self.store.begin_ai(self.sid, self.token, {**self.version(before), 'message': 'backend owner injected fixture; no model call'})
        verify(isinstance(begun, tuple) and not isinstance(begun[0], int), 'AI reservation')
        start, callbacks = begun
        candidate = ProposalCandidate(*KEY, (), '使用应急钥匙开门，等待确认。')
        expected = Version.from_state(before)
        precheck = asyncio.run(callbacks.precheck_proposal(expected, candidate))
        verify(precheck.ok and self.state() == before, 'copy-only proposal precheck')
        injected = TurnResult({'answer': '建议使用应急钥匙，等待确认。', 'clue_refs': [], 'status': 'completed', 'stop_reason': None,
                               'usage': {'provider': 'unavailable', 'model': None, 'input_tokens': None, 'output_tokens': None, 'model_calls': 0, 'read_tool_calls': 0}},
                              candidate, (), expected)
        status, body = self.store.finish_ai(self.sid, start.turn_id, injected)
        verify(status == 200 and self.state() == before, 'proposal does not consume key')
        return body['data']['proposal']['proposal_id']

    def confirm(self, pid):
        status, body = self.store.proposal_operation(self.sid, self.token, pid, 'confirm', {})
        public_validator('action_response' if body['ok'] else 'error_response').validate(body)
        return status, body

    def consumptions(self):
        with closing(self.store.connect()) as db:
            rows = db.execute("SELECT operation,result_json FROM events WHERE session_id=? AND outcome='committed'", (self.sid,)).fetchall()
        return [(row['operation'], json.loads(row['result_json'])['data']['receipt']) for row in rows
                if json.loads(row['result_json']).get('data', {}).get('receipt', {}).get('consumed_item_ids') == ['emergency_key']]

    def raw_state(self):
        with closing(self.store.connect()) as db:
            row = db.execute('SELECT state_json FROM sessions WHERE session_id=?', (self.sid,)).fetchone()
        return GameState.model_validate(json.loads(row[0]))

    def snapshot(self):
        with closing(self.store.connect()) as db:
            row = db.execute('SELECT snapshot_json FROM saves WHERE session_id=?', (self.sid,)).fetchone()
        return json.loads(row[0])

    def replace_snapshot(self, snapshot):
        with closing(self.store.connect()) as db:
            db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?', (canonical(snapshot), self.sid))


def run():
    with TemporaryDirectory(prefix='ch01-backend-owner-') as tmp:
        serial = 0
        def fixture():
            nonlocal serial
            serial += 1
            return Fixture(Path(tmp) / f'check-{serial}.sqlite')

        f = fixture()
        initial = f.state()
        verify((initial['schema_version'], initial['level_version']) == ('1.0.0', '2.0.0'), 'separate public versions')
        route = f.route()
        for step, data in enumerate(route, 1):
            verify(data['receipt']['revision_after'] == step and data['receipt']['changed'], '18-step revisions')
            verify(data['receipt']['consumed_item_ids'] == (['fuse'] if step == 8 else ['emergency_key'] if step == 13 else []), 'exact route consumption')
            if step == 13:
                verify('消耗' in data['receipt']['message'], 'committed message describes consumption')
        won = f.state()
        verify(won['status'] == 'won' and won['revision'] == 18, 'normal route won')
        verify([item['item_id'] for item in won['inventory']] == ['access_card'], 'final inventory card retained, fuse and key consumed')
        validate_invariants(f.raw_state())
        result('normal_18_route', revision=18, status='won', key_consumption_events=len(f.consumptions()), final_inventory=['access_card'])

        f = fixture()
        f.route(end=6)
        f.reject(*KEY, 'PRECONDITION_FAILED')
        f.reject('take', {'item_id': 'emergency_key'}, 'NOT_VISIBLE')
        f.route(start=6, end=11)
        f.reject(*KEY, 'PRECONDITION_FAILED')
        f.action(*ROUTE[11])
        f.reject('use_item', {'item_id': 'emergency_key', 'target_id': 'r2_powerbox'}, 'PRECONDITION_FAILED')
        f.reject('use_item', {'item_id': 'emergency_key', 'target_id': 'r1_door'}, 'NOT_VISIBLE')
        validate_invariants(f.raw_state())
        request = f.request(*KEY)
        status, first = f.send(request)
        verify(status == 200 and first['data']['receipt']['consumed_item_ids'] == ['emergency_key'], 'first consumption')
        unlocked = f.state()
        verify('emergency_key' not in [i['item_id'] for i in unlocked['inventory']], 'key absent from inventory')
        verify('emergency_key' not in [o['object_id'] for o in unlocked['objects']], 'key not respawned')
        verify(next(e for e in unlocked['exits'] if e['destination_id'] == 'R3')['unlocked'], 'door permanently unlocked')
        status, replay = f.send(deepcopy(request))
        verify(status == 200 and replay['data']['replayed'] and replay['data']['receipt'] == first['data']['receipt'], 'action replay immutable receipt')
        verify(replay['data']['visible_state'] == unlocked, 'action replay current projection')
        noop = f.action(*KEY)
        verify(not noop['receipt']['changed'] and noop['receipt']['consumed_item_ids'] == [] and noop['visible_state'] == unlocked, 'new request reuse without key')
        f.reject('take', {'item_id': 'emergency_key'}, 'ALREADY_TAKEN')
        f.reject('inspect', {'object_id': 'emergency_key'}, 'NOT_VISIBLE')
        drawer = f.action('inspect', {'object_id': 'r2_drawer'})
        verify('应急钥匙已使用。' in drawer['receipt']['observation'] and '内有' not in drawer['receipt']['observation'], 'drawer no false key contents')
        inventory = f.action('get_inventory', {})
        verify('应急钥匙' not in inventory['receipt']['observation'], 'inventory observation key absent')
        f.action('move', {'destination_id': 'R3'})
        f.reject(*KEY, 'NOT_VISIBLE')
        f.action('move', {'destination_id': 'R2'})
        f.action('move', {'destination_id': 'R3'})
        f.action('move', {'destination_id': 'R2'})
        verify(len(f.consumptions()) == 1, 'single consumption after replay reuse roundtrips')
        result('failures_replay_reuse_visibility_roundtrip', key_consumption_events=1, replay_receipt_equal=True, retake_error='ALREADY_TAKEN')

        # Exercise public AI reads using server callbacks, without invoking a Provider.
        before = f.state()
        start, callbacks = f.store.begin_ai(f.sid, f.token, {**f.version(before), 'message': 'read current drawer and inventory'})
        read = asyncio.run(callbacks.read_tool(Version.from_state(before), 'inspect', {'object_id': 'r2_drawer'}))
        verify(read.ok and '已使用' in read.observation and '内有' not in read.observation, 'AI drawer dynamic observation')
        inv = asyncio.run(callbacks.read_tool(Version.from_state(read.visible_state), 'get_inventory', {}))
        verify(inv.ok and '应急钥匙' not in inv.observation and inv.visible_state['inventory'] == before['inventory'], 'AI inventory shares truth')
        f.store.abandon_ai(f.sid, start.turn_id)
        result('AI_public_read_projection_no_provider', actual_model_calls=0, drawer_key_absent=True, inventory_key_absent=True)

        f = fixture()
        f.route(end=12)
        saved = f.control('save')['data']['visible_state']
        verify(saved['save']['level_version'] == '2.0.0' and saved['save']['schema_version'] == '1.0.0', 'save version projection')
        old_request = f.request(*KEY)
        f.send(old_request)
        before_restore = f.state()
        restored = f.control('restore')['data']['visible_state']
        verify(restored['generation'] != before_restore['generation'] and restored['revision'] == before_restore['revision'] + 1, 'restore new version')
        verify('emergency_key' in [i['item_id'] for i in restored['inventory']], 'before unlock save restores held key')
        status, stale = f.send(old_request)
        verify(status == 409 and stale['error']['code'] == 'STALE_GENERATION', 'old action after restore rejected')
        verify(f.state() == restored, 'stale replay no state change')
        fresh = f.action(*KEY)
        verify(fresh['receipt']['consumed_item_ids'] == ['emergency_key'], 'explicit restore permits new first unlock')
        f.control('save')
        after_save = f.state()
        f.action('move', {'destination_id': 'R3'})
        f.store = Store(f.store.path)
        restart = f.state()
        verify(restart['room']['room_id'] == 'R3', 'Store replacement persisted state')
        restored = f.control('restore')['data']['visible_state']
        verify(restored['room']['room_id'] == after_save['room']['room_id'] and restored['inventory'] == after_save['inventory'], 'post unlock save restore no key')
        verify('emergency_key' not in [o['object_id'] for o in restored['objects']], 'post unlock restore no respawn')
        validate_invariants(f.raw_state())
        result('v2_before_after_save_restore_store_restart', explicit_restore_consumptions=len(f.consumptions()), snapshot_level=f.snapshot()['level_version'], old_action_error='STALE_GENERATION')

        baseline = f.snapshot()
        mutations = [
            ('v1_level', lambda s: s.update(level_version='1.0.0'), 'SNAPSHOT_VERSION_MISMATCH'),
            ('retained_key_after_unlock', lambda s: s['game_fields']['inventory'].append('emergency_key'), 'INVALID_SNAPSHOT'),
            ('unlocked_without_drawer', lambda s: s['game_fields']['opened_containers'].remove('r2_drawer'), 'INVALID_SNAPSHOT'),
            ('unlocked_without_power', lambda s: s['game_fields']['flags'].update(power_on=False), 'INVALID_SNAPSHOT'),
            ('bad_checksum', lambda s: s.update(checksum='0' * 64), 'INVALID_SNAPSHOT'),
        ]
        for name, mutate, expected in mutations:
            damaged = deepcopy(baseline)
            mutate(damaged)
            if name != 'bad_checksum':
                damaged['checksum'] = checksum(damaged)
            f.replace_snapshot(damaged)
            f.control('restore', expected)
            result('snapshot_' + name, error=expected, current_state_unchanged=True)
        f.replace_snapshot(baseline)
        f.control('restore')

        f = fixture()
        f.route(end=12)
        pre_unlock = f.raw_state()
        validate_invariants(pre_unlock)
        f.action(*KEY)
        post_unlock = f.raw_state()
        validate_invariants(post_unlock)
        invalid = [
            ('retained_key', lambda s: s.inventory.append('emergency_key')),
            ('missing_drawer', lambda s: s.opened_containers.remove('r2_drawer')),
            ('missing_power', lambda s: s.flags.update(power_on=False)),
        ]
        for name, mutate in invalid:
            bad = post_unlock.model_copy(deep=True)
            mutate(bad)
            try:
                validate_invariants(bad)
            except ValueError:
                result('invariant_' + name, rejected=True)
            else:
                raise AssertionError('Invalid consumed-key invariant accepted: ' + name)
        result('valid_before_and_after_unlock_invariants', before_key_held=True, after_key_absent=True)

        f = fixture()
        f.route(end=12)
        pid = f.propose()
        before = f.state()
        status, cancelled = f.store.proposal_operation(f.sid, f.token, pid, 'cancel', {})
        verify(status == 200 and f.state() == before, 'cancel keeps held key and closed door')
        status, rejected = f.confirm(pid)
        verify(status == 409 and rejected['error']['code'] == 'PROPOSAL_CANCELLED', 'cancelled cannot consume')
        pid = f.propose()
        barrier = threading.Barrier(2)
        def confirm_once(_):
            barrier.wait(timeout=10)
            return f.confirm(pid)
        with ThreadPoolExecutor(max_workers=2) as pool:
            confirmations = list(pool.map(confirm_once, range(2)))
        verify(all(status == 200 for status, _ in confirmations), 'concurrent same proposal succeeds/replays')
        verify(sorted(body['data']['replayed'] for _, body in confirmations) == [False, True], 'one original one replay')
        verify(confirmations[0][1]['data']['receipt'] == confirmations[1][1]['data']['receipt'], 'confirm receipts identical')
        verify(confirmations[0][1]['data']['receipt']['consumed_item_ids'] == ['emergency_key'], 'confirm consumption real')
        verify(f.state()['revision'] == before['revision'] + 1 and len(f.consumptions()) == 1, 'concurrent confirm consumes once')
        f.control('save')
        f.control('restore')
        after_restore = f.state()
        status, invalidated = f.confirm(pid)
        verify(status == 409 and invalidated['error']['code'] == 'PROPOSAL_INVALIDATED' and f.state() == after_restore, 'committed proposal invalidated after restore')
        result('proposal_precheck_cancel_concurrent_confirm_restore', actual_model_calls=0, key_consumption_events=1, concurrent_replayed=[False, True], old_confirm_error='PROPOSAL_INVALIDATED')

        f = fixture()
        f.route(end=12)
        current = f.state()
        requests = [f.request(*KEY, state=current), f.request(*KEY, state=current)]
        barrier = threading.Barrier(2)
        def action_once(request):
            barrier.wait(timeout=10)
            return f.send(request)
        with ThreadPoolExecutor(max_workers=2) as pool:
            actions = list(pool.map(action_once, requests))
        verify(sorted(status for status, _ in actions) == [200, 409], 'same-version different requests one commit')
        verify(next(body for status, body in actions if status == 409)['error']['code'] == 'STALE_STATE', 'concurrent loser stale')
        verify(f.state()['revision'] == current['revision'] + 1 and len(f.consumptions()) == 1, 'different request concurrency consumes once')
        result('different_request_concurrent_first_unlock', statuses=[200, 409], error='STALE_STATE', key_consumption_events=1)

        f = fixture()
        f.route(end=12)
        request = f.request(*KEY)
        barrier = threading.Barrier(2)
        def same_action(_):
            barrier.wait(timeout=10)
            return f.send(deepcopy(request))
        with ThreadPoolExecutor(max_workers=2) as pool:
            actions = list(pool.map(same_action, range(2)))
        verify(all(status == 200 for status, _ in actions), 'identical concurrent actions successful')
        verify(sorted(body['data']['replayed'] for _, body in actions) == [False, True], 'identical action one replay')
        verify(actions[0][1]['data']['receipt'] == actions[1][1]['data']['receipt'] and len(f.consumptions()) == 1, 'identical action immutable receipt single consumption')
        result('identical_request_concurrent_first_unlock', statuses=[200, 200], replayed=[False, True], key_consumption_events=1)

        f = fixture()
        f.route(end=12)
        pid = f.propose()
        f.action('move', {'destination_id': 'R1'})
        before = f.state()
        status, body = f.confirm(pid)
        verify(status == 409 and body['error']['code'] == 'PROPOSAL_INVALIDATED' and f.state() == before, 'manual change rejects pending old proposal')
        result('manual_change_invalidates_pending_key_proposal', error='PROPOSAL_INVALIDATED', key_consumption_events=len(f.consumptions()))

try:
    run()
except Exception as exc:
    # No raw fixture response, tokens, snapshots or private DB exported.
    records.append({'check': 'owner_run', 'result': 'failed', 'exception_type': type(exc).__name__, 'message': str(exc)[:500]})
    exit_code = 1
else:
    exit_code = 0

source = ROOT / 'backend/app/domain/rules.py'
archive = ROOT / 'release/archives/baseline_v1/backend/app/domain/rules.py'
index = ROOT / 'evidence/integration/E1-source-archive-20261005.json'
report = {'task': 'T29', 'scope': 'backend local owner checks, not independent formal QA',
          'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'python_executable': sys.executable,
          'level_version': LEVEL_VERSION, 'schema_version': SCHEMA_VERSION, 'exit_code': exit_code,
          'assertion_count': checks, 'scenarios': records,
          'actual_model_calls': 0, 'network_calls': 0, 'persisted_raw_sensitive_logs': False,
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'frozen_archive_rules_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'frozen_archive_index_sha256': hashlib.sha256(index.read_bytes()).hexdigest(),
          'limits': ['No formal QA acceptance assigned.', 'No actual HTTP server/browser checks in this owner run.',
                     'Store replacement checks SQLite persistence; real process stop/restart left to QA/Delivery.',
                     'v1 independent data-dir rollback remains Main/Delivery work.',
                     'No actual AI Provider or paid calls; proposals use explicit backend TurnResult injection.',
                     'QA-owned baseline tests unchanged; known v1 expectations require v2 adaptation.']}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
diff = ''.join(difflib.unified_diff(archive.read_text(encoding='utf-8').splitlines(keepends=True), source.read_text(encoding='utf-8').splitlines(keepends=True), fromfile='baseline_v1/backend/app/domain/rules.py', tofile='v2/backend/app/domain/rules.py'))
(ROOT / 'evidence/backend/T29-rules-20261005.diff').write_text(diff, encoding='utf-8')
print(json.dumps({'exit_code': exit_code, 'assertion_count': checks, 'scenario_count': len(records), 'report': str(OUT), 'source_sha256': report['source_sha256']}, ensure_ascii=False))
raise SystemExit(exit_code)
