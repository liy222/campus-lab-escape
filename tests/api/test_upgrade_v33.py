"""Independent v3.3 manual mini-game acceptance derived from public projections."""
import asyncio
import copy
import itertools
import json
from pathlib import Path
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient
from tests.api.test_r1 import HTTPFixture, sanitize
from tests.api.test_upgrade_v32 import ROUTE32, gameplay32
from tests.api.test_m3 import Scripted, reply, call, final

CHECKS33 = []
SIDES = ('N', 'E', 'S', 'W')
DELTAS = ((-1, 0), (0, 1), (1, 0), (0, -1))


def public_ports(module, rotation=None):
    """Public instruction: I0=N/S, L0=N/E, clockwise quarter turns."""
    angle = module['rotation'] if rotation is None else rotation
    base = (0, 2) if module['shape'] == 'I' else (0, 1)
    return {(side + angle) % 4 for side in base}


def connected_public(board, rotations=None):
    modules = {m['module_id']: m for m in board['modules']}
    positions = {(m['row'], m['column']): m['module_id'] for m in board['modules']}
    ports = {key: public_ports(module, (rotations or {}).get(key, module['rotation'])) for key, module in modules.items()}
    source, sink = board['source'], board['sink']
    if SIDES.index(source['side']) not in ports[source['module_id']] or SIDES.index(sink['side']) not in ports[sink['module_id']]:
        return False
    frontier, visited = [source['module_id']], set()
    while frontier:
        current = frontier.pop()
        if current in visited:
            continue
        visited.add(current)
        if current == sink['module_id']:
            return True
        module = modules[current]
        for side in ports[current]:
            dr, dc = DELTAS[side]
            neighbor = positions.get((module['row'] + dr, module['column'] + dc))
            if neighbor is not None and (side + 2) % 4 in ports[neighbor] and neighbor not in visited:
                frontier.append(neighbor)
    return False


def derive_public_circuit(board):
    modules = board['modules']
    # I has two distinct physical port orientations; L has four.
    for angles in itertools.product(*(range(2) if m['shape'] == 'I' else range(4) for m in modules)):
        candidate = dict(zip((m['module_id'] for m in modules), angles))
        if connected_public(board, candidate):
            return candidate
    raise AssertionError('Public circuit has no source-to-sink reciprocal-port path')


def derive_public_sequence(state):
    """Combine discovered R1 symbols, R2 one-based indices, R3 public devices."""
    import re
    facts = lambda obj: '\n'.join(c['text'] for c in state['clues'] if c['object_id'] == obj)
    symbols = re.findall(r'[▲●■★]', facts('r1_symbols'))
    positions = [int(value) for value in re.findall(r'\d+', facts('research_strip'))]
    legend = facts('r3_legend')
    devices = state['minigames']['sequence']['devices']
    assert len(symbols) == len(positions) == len(devices) == 4
    assert sorted(positions) == [1, 2, 3, 4]
    mapping = {device['symbol']: device['device_id'] for device in devices}
    assert len(mapping) == 4 and all(symbol in legend for symbol in symbols)
    # Device labels and symbols must both be discoverable in the local legend.
    assert all(device['label'] in legend for device in devices)
    return [mapping[symbols[position - 1]] for position in positions]


class UpgradeV33Acceptance(HTTPFixture):
    def setUp(self):
        super().setUp()
        self.client.__exit__(None, None, None)
        from backend.app.main import create_app
        self.db = Path(self.temp.name) / 'v33.sqlite'
        self.client = TestClient(create_app(self.db, gameplay_version='v3.3'), raise_server_exceptions=False)
        self.client.__enter__()
        self.session = self.create()
        self.network = patch('httpx.AsyncClient.send', side_effect=AssertionError('Paid/model network forbidden in independent v3.3 QA'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        super().tearDown()

    def exchange(self, method, path, **kwargs):
        status, body = super().exchange(method, path, **kwargs)
        if method == 'POST' and path != '/api/sessions':
            state = body.get('data', {}).get('visible_state') if body.get('ok') else body.get('visible_state')
            if state:
                compact = {'room': state['room']['room_id'], 'devices': state['device_states'], 'slots': state['puzzle_states'], 'progress': state['progress'],
                    'mini': {k: None if v is None else {'status': v['status'], **({'rotations': [m['rotation'] for m in v['modules']]} if k == 'circuit' else {})} for k,v in state['minigames'].items()}}
                if not body.get('ok') or compact != getattr(self, '_last_compact', None) or path.endswith(('/save', '/restore', '/reset')):
                    CHECKS33.append({'test': self._testMethodName, 'operation': (kwargs.get('json') or {}).get('tool') or path.rsplit('/',1)[-1], 'http_status': status, 'error': body.get('error',{}).get('code'), **compact})
                self._last_compact = compact
        return status, body

    def route32(self, begin=0, end=None):
        for tool, arguments in ROUTE32[begin:end]:
            self.action(tool, arguments)

    def version(self, state=None):
        state = state or self.state()
        return {'request_id': uuid.uuid4().hex, 'revision': state['revision'], 'generation': state['generation']}

    def control(self, operation, expected=200, code=None):
        status, body = self.exchange('POST', f"/api/sessions/{self.session['session_id']}/{operation}", headers=self.headers(), json=self.version(), definition='control_response')
        self.assertEqual(status, expected, sanitize(body))
        if code:
            self.assertEqual(body['error']['code'], code)
        return body['data']['visible_state'] if body.get('ok') else body

    def reopen(self):
        self.client.__exit__(None, None, None)
        from backend.app.main import create_app
        self.client = TestClient(create_app(self.db, gameplay_version='v3.3'), raise_server_exceptions=False)
        self.client.__enter__()

    def assert_real_progress(self, before):
        after = self.state()
        for key in ('progress','device_states','puzzle_states','inventory','room','status'):
            self.assertEqual(after[key], before[key])

    def circuit_ready_to_edit(self):
        self.route32(end=22)
        state = self.state()
        self.assertEqual(state['device_states']['powerbox'], 'FUSE_INSTALLED')
        self.assertFalse(state['progress']['power_on'])
        self.assertIsNotNone(state['minigames']['circuit'])
        return state['minigames']['circuit']

    def rotate_to(self, candidate):
        for module in self.state()['minigames']['circuit']['modules']:
            for _ in range((candidate[module['module_id']] - module['rotation']) % 4):
                self.action('rotate_circuit', {'target_id':'r2_powerbox','module_id':module['module_id']})

    def finish_circuit(self, alternate=False):
        board = self.state()['minigames']['circuit']
        candidate = derive_public_circuit(board)
        if alternate:
            module = next(m for m in board['modules'] if m['shape']=='I')
            candidate[module['module_id']] = (candidate[module['module_id']] + 2) % 4
            self.assertTrue(connected_public(board,candidate))
        self.rotate_to(candidate)
        self.action('submit_circuit', {'target_id':'r2_powerbox'})
        self.assertEqual(self.state()['device_states']['powerbox'],'CIRCUIT_READY')
        self.assertFalse(self.state()['progress']['power_on'])
        return candidate

    def sequence_ready_to_edit(self):
        self.circuit_ready_to_edit(); self.finish_circuit()
        self.route32(23,42)
        self.assertEqual(self.state()['device_states']['exit'],'FINAL_CHECK')
        self.assertIsNotNone(self.state()['minigames']['sequence'])
        return self.state()

    def test_unknown_boards_stay_null_and_wrong_room_manual_actions_reject(self):
        initial=self.state()
        self.assertEqual((initial['schema_version'],initial['level_version']),('1.3.0','3.3.0'))
        self.assertEqual(initial['minigames'],{'circuit':None,'sequence':None})
        for tool,args in [('rotate_circuit',{'target_id':'r2_powerbox','module_id':'c00'}),('submit_circuit',{'target_id':'r2_powerbox'}),('submit_sequence',{'target_id':'r3_panel','device_ids':['cooling','lighting','safety','ventilation']})]:
            with self.subTest(tool=tool): self.reject(self.request(tool,args),'NOT_VISIBLE')
        self.route32(14,17); self.action('inspect',{'object_id':'r2_powerbox'})
        self.assertEqual(self.state()['minigames'],{'circuit':None,'sequence':None})
        self.reject(self.request('submit_circuit',{'target_id':'r2_powerbox'}),'PRECONDITION_FAILED')
        self.route32(33,39)
        self.assertEqual(self.state()['minigames'],{'circuit':None,'sequence':None})

    def test_partial_rotations_save_restore_reopen_and_full_route_independent_derivation(self):
        board=self.circuit_ready_to_edit()
        self.assertEqual((board['rows'],board['columns'],len(board['modules'])),(3,3,9))
        self.assertEqual({m['module_id'] for m in board['modules']},{f'c{row}{column}' for row in range(3) for column in range(3)})
        before=self.state(); module=board['modules'][0]
        rotated=self.action('rotate_circuit',{'target_id':'r2_powerbox','module_id':module['module_id']})['visible_state']
        self.assert_real_progress(before)
        self.assertEqual(next(m['rotation'] for m in rotated['minigames']['circuit']['modules'] if m['module_id']==module['module_id']),(module['rotation']+1)%4)
        saved=self.control('save'); self.control('reset'); restored=self.control('restore')
        self.assertEqual(gameplay32(saved),gameplay32(restored)); self.reopen(); self.assertEqual(self.state(),restored)
        solution=self.finish_circuit(); saved=self.control('save'); self.control('reset'); self.control('restore'); self.reopen()
        self.assertEqual(gameplay32(self.state()),gameplay32(saved))
        self.route32(23,42); sequence=derive_public_sequence(self.state())
        self.action('submit_sequence',{'target_id':'r3_panel','device_ids':sequence})
        self.assertTrue(self.state()['progress']['check_done']); self.assertEqual(self.state()['minigames']['sequence']['status'],'completed')
        saved=self.control('save'); self.control('reset'); restored=self.control('restore'); self.reopen()
        self.assertEqual(gameplay32(saved),gameplay32(restored)); self.assertEqual(self.state(),restored)
        self.route32(43); self.assertEqual(self.state()['status'],'won')
        CHECKS33.append({'test':self._testMethodName,'public_derived_rotations':solution,'public_derived_sequence':sequence,'partial_and_completed_stages_saved_restored_reopened':True,'final_room':'EXIT'})

    def test_alternate_valid_connection_accepted_without_exact_orientation_array(self):
        board=self.circuit_ready_to_edit(); base=derive_public_circuit(board); alternate=self.finish_circuit(alternate=True)
        self.assertNotEqual(base,alternate)
        self.assertTrue(connected_public(board,base)); self.assertTrue(connected_public(board,alternate))
        CHECKS33.append({'test':self._testMethodName,'alternate_public_port_equivalent':True,'base':base,'alternate':alternate})

    def test_unconnected_submit_interact_numeric_and_client_solved_cannot_bypass(self):
        board=self.circuit_ready_to_edit()
        self.assertFalse(connected_public(board))
        self.reject(self.request('submit_circuit',{'target_id':'r2_powerbox'}),'WRONG_CODE')
        self.reject(self.request('interact',{'target_id':'r2_powerbox'}),'PRECONDITION_FAILED')
        for extra in [{'solved':True},{'rotations':[0]*9},{'state':'CIRCUIT_READY'}]:
            with self.subTest(extra=extra): self.reject(self.request('submit_circuit',{'target_id':'r2_powerbox',**extra}),'BAD_ARGUMENT',422)
        before=self.state()
        for _ in range(4): self.action('rotate_circuit',{'target_id':'r2_powerbox','module_id':board['modules'][0]['module_id']})
        self.assertEqual(self.state()['minigames'],before['minigames']); self.assert_real_progress(before)
        self.finish_circuit()
        self.reject(self.request('rotate_circuit',{'target_id':'r2_powerbox','module_id':board['modules'][0]['module_id']}),'PRECONDITION_FAILED')
        self.reject(self.request('submit_circuit',{'target_id':'r2_powerbox'}),'PRECONDITION_FAILED')
        self.route32(23,42)
        self.reject(self.request('submit_code',{'target_id':'r3_panel','code':'4792'}),'PRECONDITION_FAILED')
        self.reject(self.request('interact',{'target_id':'r3_panel'}),'PRECONDITION_FAILED')

    def test_strict_rotate_and_submit_shapes_reject_invalid_modules_angles_and_extras(self):
        self.circuit_ready_to_edit()
        cases=[{}, {'target_id':'r2_powerbox'}, {'target_id':'r2_powerbox','module_id':'c33'}, {'target_id':'r2_powerbox','module_id':0}, {'target_id':'r2_powerbox','module_id':'c00','angle':45}, {'target_id':'r2_powerbox','module_id':'c00','rotation':0}, {'target_id':'r2_powerbox','module_id':'c00','clockwise':True}, {'target_id':'r2_powerbox','module_id':' c00'}]
        for args in cases:
            with self.subTest(args=args): self.reject(self.request('rotate_circuit',args),'BAD_ARGUMENT',422)
        for args in [{},{'target_id':'r2_powerbox','module_id':'c00'},{'target_id':'r2_powerbox','solved':True}]:
            with self.subTest(submit=args): self.reject(self.request('submit_circuit',args),'BAD_ARGUMENT',422)
        before=self.state(); request=self.request('rotate_circuit',{'target_id':'r2_powerbox','module_id':'c00'})
        first_status,first=self.post(request); second_status,second=self.post(request)
        self.assertEqual((first_status,second_status),(200,200)); self.assertTrue(second['data']['replayed'])
        self.assertEqual(first['data']['receipt'],second['data']['receipt']); self.assertEqual(second['data']['visible_state'],first['data']['visible_state'])
        self.assertEqual(self.state()['revision'],before['revision']+1); self.assert_real_progress(before)

    def test_sequence_derivation_wrong_order_length_duplicate_unknown_and_freeze(self):
        state=self.sequence_ready_to_edit(); correct=derive_public_sequence(state)
        wrong=correct[1:]+correct[:1]
        self.reject(self.request('submit_sequence',{'target_id':'r3_panel','device_ids':wrong}),'WRONG_CODE')
        cases=[{}, {'target_id':'r3_panel'}, {'target_id':'r3_panel','device_ids':correct[:3]}, {'target_id':'r3_panel','device_ids':correct+[correct[0]]}, {'target_id':'r3_panel','device_ids':[correct[0]]*4}, {'target_id':'r3_panel','device_ids':['unknown',*correct[1:]]}, {'target_id':'r3_panel','device_ids':[0,*correct[1:]]}, {'target_id':'r3_panel','device_ids':correct,'solved':True}, {'target_id':'r3_panel','device_ids':','.join(correct)}]
        for args in cases:
            with self.subTest(args=args): self.reject(self.request('submit_sequence',args),'BAD_ARGUMENT',422)
        self.action('submit_sequence',{'target_id':'r3_panel','device_ids':correct})
        self.assertTrue(self.state()['progress']['check_done'])
        self.reject(self.request('submit_sequence',{'target_id':'r3_panel','device_ids':correct}),'PRECONDITION_FAILED')

    def test_cross_version_snapshots_rejected_without_overwriting_current_progress(self):
        import sqlite3
        from contextlib import closing
        from tests.api.test_m2 import digest
        self.circuit_ready_to_edit(); self.action('rotate_circuit',{'target_id':'r2_powerbox','module_id':'c00'}); self.control('save')
        with closing(sqlite3.connect(self.db)) as db:
            raw=db.execute('SELECT snapshot_json FROM saves WHERE session_id=?',(self.session['session_id'],)).fetchone()[0]
        original=json.loads(raw)
        for schema,level in [('1.0.0','2.0.0'),('1.1.0','3.1.0'),('1.2.0','3.2.0')]:
            with self.subTest(level=level):
                broken=copy.deepcopy(original); broken.update(schema_version=schema,level_version=level); broken['checksum']=digest(broken)
                tampered=json.dumps(broken,ensure_ascii=False)
                with closing(sqlite3.connect(self.db)) as db:
                    db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?',(tampered,self.session['session_id'])); db.commit()
                before=self.state(); self.control('restore',409,'SNAPSHOT_VERSION_MISMATCH'); self.assertEqual(self.state(),before)
                with closing(sqlite3.connect(self.db)) as db:
                    self.assertEqual(db.execute('SELECT snapshot_json FROM saves WHERE session_id=?',(self.session['session_id'],)).fetchone()[0],tampered)
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('UPDATE saves SET snapshot_json=? WHERE session_id=?',(raw,self.session['session_id'])); db.commit()
        self.control('restore')

    def test_ai_read_guard_cannot_mutate_circuit_sequence_or_reveal_unknown_board(self):
        from backend.app.ai.runtime import Runtime
        from backend.app.ai.types import TurnStart, Snapshot, ReadResult
        initial=self.state(); sentinel='QA_UNSEEN_MINIGAME_SENTINEL'
        cases=[('unknown-circuit',initial,'r1_door',lambda s:s['minigames'].update(circuit=copy.deepcopy(circuit['minigames']['circuit']))),('unknown-sequence',initial,'r1_door',lambda s:s['minigames'].update(sequence=copy.deepcopy(sequence['minigames']['sequence'])))]
        self.circuit_ready_to_edit(); circuit=self.state()
        cases.extend([('rotate-read',circuit,'r2_monitor',lambda s:s['minigames']['circuit']['modules'][0].update(rotation=(s['minigames']['circuit']['modules'][0]['rotation']+1)%4)),('solved-read',circuit,'r2_monitor',lambda s:s['minigames']['circuit'].update(status='completed'))])
        self.finish_circuit(); self.route32(23,42); sequence=self.state()
        cases.append(('sequence-device-read',sequence,'r3_legend',lambda s:s['minigames']['sequence']['devices'][0].update(device_id=sentinel)))
        actual_store=self.state()
        for name,before,target,mutate in cases:
            with self.subTest(case=name):
                forged=copy.deepcopy(before)
                if target not in forged['observed_object_ids']:
                    forged['observed_object_ids'].append(target); forged['revision']+=1
                mutate(forged)
                class ForgedCallbacks:
                    read_happened=False
                    async def snapshot(self,expected): return Snapshot(copy.deepcopy(forged if self.read_happened else before))
                    async def read_tool(self,expected,tool,arguments):
                        self.read_happened=True; return ReadResult(True,copy.deepcopy(forged),'中性观察。',())
                    async def precheck_proposal(self,expected,candidate): raise AssertionError('Forged read must stop before precheck')
                provider=Scripted([reply(calls=[call('inspect',{'object_id':target})]),final()])
                result=asyncio.run(Runtime(provider).run(TurnStart('qa-mini-read','观察当前房间',copy.deepcopy(before)),ForgedCallbacks()))
                self.assertEqual(result.data['status'],'stopped'); self.assertEqual(provider.calls,1)
                self.assertNotIn(sentinel,json.dumps(provider.contexts,ensure_ascii=False)); self.assertEqual(self.state(),actual_store)
                CHECKS33.append({'test':self._testMethodName,'forged_callback_case':name,'stopped':result.data['stop_reason'],'no_second_provider_call_or_store_mutation':True})

    def test_ai_legitimate_read_preserves_partial_board_and_manual_only_tools(self):
        from backend.app.ai.runtime import Runtime
        self.circuit_ready_to_edit(); self.action('rotate_circuit',{'target_id':'r2_powerbox','module_id':'c00'}); before=self.state()
        provider=Scripted([reply(calls=[call('inspect',{'object_id':'r2_monitor'})]),final()]); self.client.app.state.ai_runtime=Runtime(provider)
        status,body=self.exchange('POST',f"/api/sessions/{self.session['session_id']}/ai/turns",headers=self.headers(),json={**self.version(),'message':'观察已见设备'},definition='ai_turn_response')
        self.assertEqual(status,200,sanitize(body)); self.assertEqual(body['data']['status'],'no_suggestion')
        self.assertEqual(body['data']['visible_state']['minigames'],before['minigames']); self.assertEqual(provider.calls,2)
        tools=json.loads(Path('contracts/tools.json').read_text(encoding='utf-8'))
        names=[tool.get('function',tool).get('name') for tool in tools] if isinstance(tools,list) else str(tools)
        for new_tool in ('rotate_circuit','submit_circuit','submit_sequence'): self.assertNotIn(new_tool,names)