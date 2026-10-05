"""R1 black-box acceptance based on SPEC 1.0.0, never private implementation."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'contracts/api.schema.json').read_text(encoding='utf-8'))
EXCHANGES, SECRETS = [], set()


def semantic_text(value):
    """Scan actual public content; random IDs/hashes can coincidentally be codes.

    Full unmodified exchanges are still recorded and separately schema/token
    checked. Only unguessable tracking metadata is excluded from answer scans.
    """
    tracking = {'session_id', 'generation', 'source_generation', 'event_id', 'request_id',
                'turn_id', 'proposal_id', 'message_sha256', 'expires_at', 'saved_at'}
    def project(item):
        if isinstance(item, dict):
            return {k: project(v) for k, v in item.items() if k not in tracking}
        if isinstance(item, list):
            return [project(v) for v in item]
        return item
    return json.dumps(project(value), ensure_ascii=False)


def sanitize(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if k.lower() in {'token', 'x-session-token', 'authorization'} else sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        for token in SECRETS:
            value = value.replace(token, '[REDACTED]')
    return value


class HTTPFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='campus-qa-r1-')
        os.environ['AI_PROVIDER'] = 'mock'
        os.environ['SQLITE_PATH'] = str(Path(self.temp.name) / 'default.sqlite')
        from backend.app.main import create_app
        self.client = TestClient(create_app(sqlite_path=Path(self.temp.name) / 'test.sqlite'), raise_server_exceptions=False)
        self.client.__enter__()
        self.session = self.create()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        resolved = Path(self.temp.name).resolve()
        self.assertEqual(resolved.parent, Path(tempfile.gettempdir()).resolve(), 'Fixture cleanup escaped owned temp root')
        self.assertTrue(resolved.name.startswith('campus-qa-r1-'), 'Fixture cleanup lacks QA-owned prefix')
        self.temp.cleanup()

    def exchange(self, method, path, *, definition=None, headers=None, **kwargs):
        response = self.client.request(method, path, headers=headers, **kwargs)
        try:
            payload = response.json()
        except ValueError:
            self.fail('HTTP response was not JSON')
        if path == '/api/sessions' and payload.get('ok'):
            SECRETS.add(payload['data']['token'])
        EXCHANGES.append(sanitize({'test': self.id(), 'method': method, 'path': path, 'request': kwargs, 'http_status': response.status_code, 'response': payload}))
        name = definition if payload.get('ok') else 'error_response'
        self.assertIsNotNone(name, 'Missing success response definition')
        validator = Draft202012Validator({'$ref': f'#/$defs/{name}', '$defs': SCHEMA['$defs']}, format_checker=FormatChecker())
        errors = list(validator.iter_errors(payload))
        self.assertFalse(errors, 'Frozen public schema mismatch: ' + '; '.join(str(e.path) + ' ' + sanitize(e.message) for e in errors))
        if path != '/api/sessions':
            self.assertTrue(all(token not in json.dumps(payload) for token in SECRETS), 'Session capability leaked')
        return response.status_code, payload

    def create(self):
        status, body = self.exchange('POST', '/api/sessions', json={}, definition='create_response')
        self.assertEqual(status, 201)
        return body['data']

    def headers(self, session=None):
        return {'X-Session-Token': (session or self.session)['token']}

    def state(self, session=None):
        session = session or self.session
        status, body = self.exchange('GET', f"/api/sessions/{session['session_id']}/state", headers=self.headers(session), definition='state_response')
        self.assertEqual(status, 200)
        return body['data']['visible_state']

    def request(self, tool, arguments, state=None, request_id=None):
        state = state or self.state()
        return {'request_id': request_id or uuid.uuid4().hex, 'revision': state['revision'], 'generation': state['generation'], 'tool': tool, 'arguments': arguments}

    def post(self, request):
        return self.exchange('POST', f"/api/sessions/{self.session['session_id']}/actions", headers=self.headers(), json=request, definition='action_response')

    def action(self, tool, arguments):
        status, body = self.post(self.request(tool, arguments))
        self.assertEqual(status, 200, sanitize(body))
        return body['data']

    def reject(self, request, code, status=409):
        before = self.state()
        actual, body = self.post(request)
        self.assertEqual(actual, status, sanitize(body))
        self.assertEqual(body['error']['code'], code)
        self.assertEqual(self.state(), before, 'Rejected request altered visible state')
        return body

    def to_r2(self):
        for tool, args in [('inspect', {'object_id': 'r1_note'}), ('inspect', {'object_id': 'r1_cabinet'}), ('submit_code', {'target_id': 'r1_cabinet', 'code': '382'}), ('take', {'item_id': 'access_card'}), ('use_item', {'item_id': 'access_card', 'target_id': 'r1_door'}), ('move', {'destination_id': 'R2'})]:
            self.action(tool, args)

class R1Acceptance(HTTPFixture):
    def test_A01_new_and_independent_sessions(self):
        first, other = self.state(), self.create()
        second = self.state(other)
        self.assertNotEqual(first['session_id'], second['session_id'])
        self.assertNotEqual(first['generation'], second['generation'])
        for s in (first, second):
            self.assertEqual(s['room']['room_id'], 'R1')
            self.assertEqual(s['revision'], 0)
            self.assertEqual(s['status'], 'playing')
            self.assertEqual(s['inventory'], [])
            self.assertEqual(s['clues'], [])
            self.assertEqual(s['progress'], {'power_on': False, 'check_done': False})
            self.assertIsNone(s['save'])
            self.assertEqual({o['object_id'] for o in s['objects']}, {'r1_note', 'r1_cabinet', 'r1_door'})
            self.assertEqual([(e['destination_id'], e['unlocked']) for e in s['exits']], [('R2', False)])
        self.action('inspect', {'object_id': 'r1_note'})
        self.assertEqual(self.state(other), second)

    def test_A03_missing_card_and_locked_move(self):
        self.reject(self.request('use_item', {'item_id': 'access_card', 'target_id': 'r1_door'}), 'PRECONDITION_FAILED')
        self.reject(self.request('move', {'destination_id': 'R2'}), 'PRECONDITION_FAILED')

    def test_A04_wrong_code_no_answer_leak(self):
        body = self.reject(self.request('submit_code', {'target_id': 'r1_cabinet', 'code': '000'}), 'WRONG_CODE')
        self.assertNotIn('382', semantic_text(body))
        self.assertNotIn('access_card', json.dumps(body, ensure_ascii=False))

    def test_A10_visibility_and_hidden_ids(self):
        text = semantic_text(self.state())
        for hidden in ['382', '724', '231', '三角记为3', '柜门标签从左到右', '青色7', '冷却对应2', 'access_card', 'emergency_key', 'game_fields', 'opened_containers', 'discovered_clue_ids']:
            self.assertNotIn(hidden, text)
        self.reject(self.request('take', {'item_id': 'access_card'}), 'NOT_VISIBLE')
        for target in ['access_card', 'r2_monitor', 'r3_panel', 'nonexistent']:
            with self.subTest(target=target):
                self.reject(self.request('inspect', {'object_id': target}), 'NOT_VISIBLE')
        self.reject(self.request('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}), 'NOT_VISIBLE')

    def test_manual_R1_route_repeats_and_return(self):
        first = self.action('inspect', {'object_id': 'r1_note'})
        self.assertEqual(first['receipt']['new_clue_ids'], ['r1_note_clue'])
        self.assertEqual(first['visible_state']['revision'], 1)
        repeat = self.action('inspect', {'object_id': 'r1_note'})
        self.assertFalse(repeat['receipt']['changed'])
        self.assertEqual(repeat['visible_state']['revision'], 1)
        cabinet = self.action('inspect', {'object_id': 'r1_cabinet'})
        self.assertEqual([c['clue_id'] for c in cabinet['visible_state']['clues']], ['r1_note_clue', 'r1_cabinet_clue'])
        opened = self.action('submit_code', {'target_id': 'r1_cabinet', 'code': '382'})
        self.assertEqual(opened['visible_state']['revision'], 3)
        self.assertIn('access_card', {o['object_id'] for o in opened['visible_state']['objects']})
        self.assertEqual(opened['visible_state']['inventory'], [])
        noop = self.action('submit_code', {'target_id': 'r1_cabinet', 'code': '382'})
        self.assertFalse(noop['receipt']['changed'])
        self.assertEqual(noop['visible_state']['revision'], 3)
        taken = self.action('take', {'item_id': 'access_card'})
        self.assertEqual([i['item_id'] for i in taken['visible_state']['inventory']], ['access_card'])
        self.assertNotIn('access_card', {o['object_id'] for o in taken['visible_state']['objects']})
        self.reject(self.request('take', {'item_id': 'access_card'}), 'ALREADY_TAKEN')
        door = self.action('use_item', {'item_id': 'access_card', 'target_id': 'r1_door'})
        self.assertTrue(door['visible_state']['exits'][0]['unlocked'])
        self.assertEqual(door['receipt']['consumed_item_ids'], [])
        moved = self.action('move', {'destination_id': 'R2'})
        self.assertEqual(moved['visible_state']['room']['room_id'], 'R2')
        self.assertEqual(moved['visible_state']['revision'], 6)
        returned = self.action('move', {'destination_id': 'R1'})
        self.assertEqual(returned['visible_state']['room']['room_id'], 'R1')
        self.assertEqual(len(returned['visible_state']['clues']), 2)

    def test_A05_success_replay_and_same_ID_conflict(self):
        request = self.request('inspect', {'object_id': 'r1_note'}, request_id='qa-replay')
        status, first = self.post(request)
        self.assertEqual(status, 200)
        status, again = self.post(copy.deepcopy(request))
        self.assertEqual(status, 200)
        self.assertTrue(again['data']['replayed'])
        self.assertEqual(first['data']['receipt'], again['data']['receipt'])
        self.assertEqual(self.state()['revision'], 1)
        request['arguments']['object_id'] = 'r1_cabinet'
        self.reject(request, 'REQUEST_ID_CONFLICT')

    def test_A05_failure_replay_keeps_event_and_current_state(self):
        request = self.request('submit_code', {'target_id': 'r1_cabinet', 'code': '000'}, request_id='qa-failure')
        first = self.reject(request, 'WRONG_CODE')
        self.action('inspect', {'object_id': 'r1_note'})
        again = self.reject(copy.deepcopy(request), 'WRONG_CODE')
        self.assertEqual(first['event_id'], again['event_id'])
        self.assertEqual(again['visible_state']['revision'], 1)
        request['arguments']['code'] = '001'
        self.reject(request, 'REQUEST_ID_CONFLICT')

    def test_A06_stale_revision_and_generation(self):
        initial = self.state()
        self.action('inspect', {'object_id': 'r1_note'})
        self.reject(self.request('inspect', {'object_id': 'r1_cabinet'}, state=initial), 'STALE_STATE')
        request = self.request('inspect', {'object_id': 'r1_cabinet'})
        request['generation'] = str(uuid.uuid4())
        self.reject(request, 'STALE_GENERATION')

    def test_A14_foreign_missing_invalid_capabilities(self):
        other = self.create()
        target, before = other['session_id'], self.state(other)
        for token in [None, 'invalid-capability', self.session['token']]:
            for method, suffix in [('GET', 'state'), ('POST', 'actions')]:
                with self.subTest(method=method, suffix=suffix, capability_case='missing' if token is None else 'invalid-or-foreign'):
                    headers = {} if token is None else {'X-Session-Token': token}
                    kwargs = {} if method == 'GET' else {'json': self.request('inspect', {'object_id': 'r1_note'}, state=before)}
                    status, body = self.exchange(method, f'/api/sessions/{target}/{suffix}', headers=headers, **kwargs)
                    self.assertEqual(status, 403)
                    self.assertEqual(body['error']['code'], 'FORBIDDEN_SESSION')
                    self.assertIsNone(body['visible_state'])
                    self.assertNotIn(target, json.dumps(body))
        status, body = self.exchange('GET', '/api/sessions/does-not-exist/state', headers=self.headers())
        self.assertEqual(status, 403)
        self.assertEqual(body['error']['code'], 'FORBIDDEN_SESSION')
        self.assertIsNone(body['visible_state'])
        self.assertEqual(self.state(other), before)

    def test_strict_tool_arguments(self):
        cases = [('inspect', {'object_id': 'r1_note', 'flags': {'won': True}}), ('inspect', {}), ('inspect', {'object_id': 1}), ('inspect', {'object_id': '../rules'}), ('get_inventory', {'extra': True}), ('take', {'item_id': 'access_card', 'extra': True}), ('use_item', {'item_id': 'access_card', 'target_id': 'r1_door', 'extra': True}), ('move', {'destination_id': 'R2', 'extra': True}), ('move', {'destination_id': 'UNKNOWN'})]
        for tool, args in cases:
            with self.subTest(tool=tool, arguments=args):
                self.reject(self.request(tool, args), 'BAD_ARGUMENT', 422)
        for code in ['', ' 382', '382 ', '+382', '٣٨٢', '3.82', 'x', '0' * 17, 382, True, None]:
            with self.subTest(code=code):
                self.reject(self.request('submit_code', {'target_id': 'r1_cabinet', 'code': code}), 'BAD_ARGUMENT', 422)
        self.reject(self.request('execute_python', {'code': 'print(1)'}), 'INVALID_TOOL', 422)

    def test_strict_request_envelope(self):
        good = self.request('get_inventory', {})
        for key, value in [('revision', True), ('revision', -1), ('revision', '0'), ('generation', 'bad'), ('request_id', ''), ('request_id', '../bad'), ('request_id', 'a' * 101), ('arguments', []), ('flags', {'won': True}), ('won', True)]:
            request = copy.deepcopy(good)
            request[key] = value
            with self.subTest(key=key, value=value):
                self.reject(request, 'BAD_ARGUMENT', 422)
        for key in good:
            request = copy.deepcopy(good)
            del request[key]
            with self.subTest(missing=key):
                self.reject(request, 'BAD_ARGUMENT', 422)

    def test_malformed_JSON_and_non_object_body(self):
        for raw in ['{', '[]', 'null', '"text"']:
            before = self.state()
            status, body = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/actions", headers=self.headers(), content=raw)
            self.assertEqual(status, 422)
            self.assertEqual(body['error']['code'], 'BAD_ARGUMENT')
            self.assertIsNone(body['visible_state'])
            self.assertEqual(self.state(), before)
        status, body = self.exchange('POST', '/api/sessions', json={'won': True})
        self.assertEqual(status, 422)
        self.assertEqual(body['error']['code'], 'BAD_ARGUMENT')

    def test_GET_and_inventory_have_no_knowledge_side_effect(self):
        before = self.state()
        self.assertEqual(self.state(), before)
        result = self.action('get_inventory', {})
        self.assertFalse(result['receipt']['changed'])
        self.assertEqual(result['visible_state'], before)

    def test_R2_boundary_missing_items_unpowered_monitor(self):
        self.to_r2()
        self.reject(self.request('use_item', {'item_id': 'fuse', 'target_id': 'r2_powerbox'}), 'PRECONDITION_FAILED')
        self.reject(self.request('use_item', {'item_id': 'emergency_key', 'target_id': 'r2_door'}), 'PRECONDITION_FAILED')
        before = self.state()
        monitor = self.action('inspect', {'object_id': 'r2_monitor'})
        self.assertEqual(monitor['visible_state'], before)
        self.assertEqual(monitor['receipt']['new_clue_ids'], [])
        self.assertIn('当前无显示', monitor['receipt']['observation'])
        self.reject(self.request('take', {'item_id': 'emergency_key'}), 'NOT_VISIBLE')
        self.reject(self.request('inspect', {'object_id': 'r1_note'}), 'NOT_VISIBLE')
        self.action('move', {'destination_id': 'R1'})
