"""Owner development checks, not independent QA; no network or persistent game DB."""
import ast
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from backend.app.ai.hints import available_topics, bounded_render, TEMPLATES, NO_HINT
from backend.app.ai.mock import DeterministicMockProvider
from backend.app.ai.runtime import Runtime
from backend.app.ai.types import Snapshot, TurnStart
from backend.app.domain import graybox_rules as rules
from backend.app.storage.sqlite import Store

OUT = Path(__file__).parent
trace = json.loads((ROOT/'evidence/documentation/gameplay-walkthrough-20261018/verification.json').read_text(encoding='utf-8'))['route_steps']
old_source = subprocess.check_output(['git', '-c', 'safe.directory=D:/深度能力', 'show', 'HEAD:backend/app/ai/hints.py'], cwd=ROOT, text=True, encoding='utf-8')
old_templates = next(ast.literal_eval(n.value) for n in ast.parse(old_source).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TEMPLATES' for t in n.targets))
assert old_templates == TEMPLATES
checks = []
snapshots = []
state = rules.initial_state()

def snap(label):
    visible = rules.visible_state('owner-memory-check', state)
    snapshots.append((label, deepcopy(visible)))
    return visible

def step(number):
    global state
    entry = trace[number-1]
    state, _ = rules.apply_action(state, entry['tool'], entry['arguments'])
    return snap('route-'+str(number))

snap('initial')
for number in range(1, len(trace)+1):
    step(number)
assert state.status == 'won'
original_rendered = set()
for label, visible in snapshots:
    before = deepcopy(visible)
    topics = available_topics(visible)
    assert len([t for t in topics if not t['clue_refs']]) <= 1
    if any(t['topic'] == 'circuit' for t in topics):
        assert not any(t['topic'] == 'next_step' for t in topics)
    rendered = {}
    for option in topics:
        assert set(option['clue_refs']) <= {c['clue_id'] for c in visible['clues']}
        for level in (1, 2, 3):
            current = deepcopy(visible)
            current['statistics']['current_hint_level'] = level
            answer, refs = bounded_render(current, option['clue_refs'], option['topic'])
            assert (answer, refs) == bounded_render(current, option['clue_refs'])
            assert not any(value in answer for value in ('4217', 'LAB-42', '2117', '4792', '231', 'ventilation, cooling, lighting, safety', '通风 → 冷却 → 照明 → 安全'))
            if option['topic'] in TEMPLATES:
                assert answer == TEMPLATES[option['topic']][level-1]
                original_rendered.add((option['topic'], level))
            rendered.setdefault(option['topic'], []).append(answer)
    assert visible == before
    checks.append({'snapshot':label, 'room':visible['room']['room_id'], 'topics':topics, 'rendered':rendered})
assert len(original_rendered) == 18
assert all(available_topics(v) for _, v in snapshots if v['status'] == 'playing')
assert not available_topics(snapshots[-1][1])

class Callbacks:
    def __init__(self, visible): self.visible = visible
    async def snapshot(self, expected): return Snapshot(deepcopy(self.visible))
    async def read_tool(self, *args): raise AssertionError('Hint must not read')
    async def precheck_proposal(self, *args): raise AssertionError('Hint must not propose')

async def runtime_check(visible):
    before = deepcopy(visible)
    result = await Runtime(DeterministicMockProvider()).run(TurnStart('owner-check', 'fixed-message', deepcopy(visible), ()), Callbacks(visible))
    assert visible == before
    assert result.candidate is None
    assert result.data['usage']['model_calls'] == result.data['usage']['read_tool_calls'] == 0
    return result

rotation = []
async def rotation_checks():
    for label in ('route-2', 'route-8', 'route-39'):
        original = next(v for name, v in snapshots if name == label)
        topics = available_topics(original)
        assert len(topics) >= 2
        for count in range(len(topics)*2):
            visible = deepcopy(original)
            visible['statistics']['hint_count'] = count
            result = await runtime_check(visible)
            selected = topics[count % len(topics)]
            answer, refs = bounded_render(visible, selected['clue_refs'], selected['topic'])
            assert result.data['answer'] == answer and result.data['clue_refs'] == refs
        rotation.append({'snapshot':label, 'topics':[t['topic'] for t in topics], 'full_cycles':2})
asyncio.run(rotation_checks())

# Actual legal guessed-code branch skips the R1 inference observations.
state = rules.initial_state()
for n in (9,10,11,12,13,14,16,17,18): step(n)
for n in range(19,40): step(n)
v = rules.visible_state('owner-memory-check', state)
assert v['device_states']['computer'] == 'LOGIN_LOCKED'
assert '实验准备室' in bounded_render({**v, 'statistics':{**v['statistics'], 'current_hint_level':3}}, [])[0]
state, _ = rules.apply_action(state, 'move', {'destination_id':'R1'})
v = rules.visible_state('owner-memory-check', state)
assert '铭牌' in bounded_render({**v, 'statistics':{**v['statistics'], 'current_hint_level':3}}, [])[0]
state, _ = rules.apply_action(state, 'inspect', {'object_id':'r1_plaque'})
v = rules.visible_state('owner-memory-check', state)
assert '墙钟' in bounded_render({**v, 'statistics':{**v['statistics'], 'current_hint_level':3}}, [])[0]
state, _ = rules.apply_action(state, 'inspect', {'object_id':'r1_clock'})
state, _ = rules.apply_action(state, 'move', {'destination_id':'R2'})
state, _ = rules.apply_action(state, 'submit_login', trace[39]['arguments'])
state, _ = rules.apply_action(state, 'move', {'destination_id':'R1'})
v = rules.visible_state('owner-memory-check', state)
assert '设备实验室' in bounded_render({**v, 'statistics':{**v['statistics'], 'current_hint_level':3}}, [])[0]
assert 'r1_sample_clue' not in {c['clue_id'] for c in v['clues']}

store_checks = []
async def store_probe():
    with tempfile.TemporaryDirectory(prefix='hint-flow-owner-') as directory:
        store = Store(Path(directory)/'temporary.sqlite', rules=rules)
        code, body = store.create({})
        assert code == 201
        session = body['data']
        sid, token = session['session_id'], session['token']
        def current(): return store.read(sid, token)[1]['data']['visible_state']
        async def ask(level=3, forge=False):
            before = current()
            request = {'request_id':uuid4().hex, 'revision':before['revision'], 'generation':before['generation'], 'message':'fixed-message', 'hint_level':level}
            start, callbacks = store.begin_ai(sid, token, request)
            result = await Runtime(DeterministicMockProvider()).run(start, callbacks)
            if forge:
                result = replace(result, data={**result.data, 'answer':'UNTRUSTED RUNTIME PROSE'})
            code, body = store.finish_ai(sid, start.turn_id, result)
            assert code == 200 and body['data']['stop_reason'] is None
            assert body['data']['answer'] != 'UNTRUSTED RUNTIME PROSE'
            after = current()
            assert after['statistics']['hint_count'] == before['statistics']['hint_count']+1
            first_event = body['event_id']
            replay_code, replay = store.begin_ai(sid, token, request)
            assert replay_code == 200 and replay['event_id'] == first_event
            assert current()['statistics']['hint_count'] == after['statistics']['hint_count']
            store_checks.append({'new_hint_counted_once':True, 'replay_count_unchanged':True, 'forged_prose_ignored':forge, 'answer':body['data']['answer'], 'clue_refs':body['data']['clue_refs']})
        await ask(forge=True)
        for number in (1,2):
            v = current(); entry = trace[number-1]
            code, result = store.action(sid, token, {'request_id':uuid4().hex, 'revision':v['revision'], 'generation':v['generation'], 'tool':entry['tool'], 'arguments':entry['arguments']})
            assert code == 200
        await ask()
        await ask()
        # Finish the true route through Store; no state injection or saved DB.
        for number in range(3, len(trace)+1):
            v = current(); entry = trace[number-1]
            code, result = store.action(sid, token, {'request_id':uuid4().hex, 'revision':v['revision'], 'generation':v['generation'], 'tool':entry['tool'], 'arguments':entry['arguments']})
            assert code == 200, (number, result.get('error'))
        before = current()
        request = {'request_id':uuid4().hex, 'revision':before['revision'], 'generation':before['generation'], 'message':'fixed-message', 'hint_level':1}
        code, body = store.begin_ai(sid, token, request)
        assert code == 200 and body['data']['answer'] == NO_HINT
        assert body['data']['usage']['model_calls'] == 0
        assert current()['statistics']['hint_count'] == before['statistics']['hint_count']
        store_checks.append({'won_no_topic_no_call_no_count':True})
asyncio.run(store_probe())

paths = ['backend/app/ai/hints.py', 'backend/app/storage/ai.py', 'docs/SPEC.md', 'docs/level_design.md']
report = {'recorded_at':datetime.now(timezone.utc).isoformat(), 'operator':'Backend/AI Owner development check', 'command':[sys.executable, '-B', '-X', 'utf8', 'evidence/integration/hint-flow/backend/probe.py'], 'exit_code':0, 'original_templates_unchanged':True, 'original_variants_rendered':len(original_rendered), 'actual_primary_route_snapshots':59, 'rotation':rotation, 'store_checks':store_checks, 'snapshots':checks, 'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}, 'model_calls':0, 'paid_calls':0, 'limitations':['Owner development checks, not independent QA or frontend/browser acceptance.', 'No real provider invoked; its bounded selection code is unchanged.', 'No API/snapshot/schema/provider/auth/budget or old tests changed.', 'Temporary Store DB was created only under TemporaryDirectory and removed; no credentials or raw DB logs retained.', 'Exact user question does not select the default template; the free Mock UI supplies a fixed message.']}
(OUT/'probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'exit_code':0,'primary_snapshots':59,'original_variants':18,'rotation_groups':len(rotation),'store_records':len(store_checks),'model_calls':0}, ensure_ascii=False))
