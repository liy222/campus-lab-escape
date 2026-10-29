"""SP-01 independent synthetic checks. Formal execution requires Main GO.
Only explicit owned TEMP may hold synthetic compiled/witness browser cache.
"""
from __future__ import annotations
import asyncio
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile

import httpx
import pytest
from tests.v5.conftest import Actor, CANARY, FixtureGenerator, private_game_hash, rid
from tests.v5.test_blueprint_generation import SHAPES, synthetic_content, synthetic_model_content
from tests.v5.test_generation import wire_body
from backend.app.ai.budget import BudgetLedger, cost_units
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
from backend.app.ai.v5 import GenerationService
from backend.app.domain import blueprints as legacy
from backend.app.domain import generation_content_v2 as content
from backend.app.domain import puzzle_purpose as purpose
from backend.app.domain import structure_variants as structures
from backend.app.domain.generated import Draft, GeneratedRules, compile_level, make_fixture

CELLS = [(n, d, seed) for n, d, *_ in SHAPES for seed in range(4)]


def cache_root():
    directory = Path(os.environ['SP_CACHE_DIR']).resolve()
    assert directory.is_relative_to(Path(tempfile.gettempdir()).resolve())
    assert directory.name.startswith('campus-visual-sp-') and directory.is_dir()
    return directory


def valid_content(bp):
    raw = synthetic_model_content(bp)
    effects = purpose.puzzle_effects(bp)
    for i, obj in enumerate(bp.objects):
        if obj.kind == 'puzzle':
            effect = effects[obj.object_id]
            label = ('门禁供电箱' if effect['purpose'] == 'passage_control' else '线路供电箱') if obj.art_id == 'circuit' else ('门禁终端' if effect['purpose'] == 'passage_control' else '校验终端')
        else:
            label = '黄铜钥匙' if obj.kind == 'item' else '观察资料'
        raw['objects'][obj.object_id]['name'] = label + str(i) if obj.kind != 'puzzle' else '前厅' + str(i) + label
    for i, rid_ in enumerate(bp.room_ids):
        raw['rooms'][rid_]['name'] = '合成校园房间' + str(i + 1)
    return raw


def ancestors(bp, pid):
    puzzles = {p.puzzle_id: p for p in bp.puzzles}
    result = set()
    def walk(key):
        for parent in puzzles[key].prerequisite_ids:
            if parent not in result:
                result.add(parent); walk(parent)
    walk(pid)
    return result


def mechanical(draft):
    if isinstance(draft, dict):
        return {k: mechanical(v) for k, v in draft.items() if k not in {'name', 'title', 'story', 'description'}}
    if isinstance(draft, list):
        return [mechanical(x) for x in draft]
    return draft


@pytest.mark.parametrize('rooms,difficulty,seed', CELLS)
def test_36_purposes_are_actual_topology_and_mechanics_unchanged(rooms, difficulty, seed):
    bp = content.select_blueprint(rooms, difficulty, seed=seed)
    before = copy.deepcopy(bp)
    effects = purpose.puzzle_effects(bp)
    manifest = content.request_manifest(bp)
    assert len(effects) == len(bp.puzzles)
    pobjects = {o.reference_id: o for o in bp.objects if o.kind == 'puzzle'}
    for i, room in enumerate(bp.room_ids):
        local = {p.puzzle_id for p in bp.puzzles if p.room_id == room}
        finals = [pid for pid in local if local - {pid} <= ancestors(bp, pid)]
        assert len(finals) == 1
        for pid in local:
            obj = pobjects[pid]; effect = effects[obj.object_id]
            assert effect['carrier'] == obj.art_id
            assert effect['purpose'] == ('passage_control' if pid == finals[0] else 'puzzle_control')
            if pid == finals[0]:
                assert effect['destination_room_slot'] == (bp.room_ids[i + 1] if i + 1 < rooms else 'EXIT')
            else:
                assert 'destination_room_slot' not in effect
            expected = {o.object_id for o in bp.objects if o.kind in {'clue', 'item'} and o.room_id == room and pid in o.locked_by and set(o.locked_by) - {pid} <= ancestors(bp, pid)}
            assert set(effect['unlocks_material_slots']) == expected
    assert {row['object_slot']: row['effect'] for row in manifest['puzzles']} == effects
    raw = valid_content(bp); snapshot = copy.deepcopy(raw)
    assembled = content.assemble_draft(bp, json.dumps(raw, ensure_ascii=False))
    old = synthetic_content(bp)
    old.update({key: copy.deepcopy(raw[key]) for key in ('title', 'story', 'rooms')})
    old['objects'] = {key: {'name': value['name'], 'description': '旧完整定义合成说明。'} for key, value in raw['objects'].items()}
    baseline = legacy.assemble_draft(bp, old)
    assert mechanical(assembled) == mechanical(baseline)
    assert raw == snapshot and bp == before
    names = {rid_: row['name'] for rid_, row in raw['rooms'].items()}
    for room in assembled['rooms']:
        for obj in room['objects']:
            if obj['object_id'] in effects:
                assert obj['description'].endswith(purpose.describe_effect(effects[obj['object_id']], names))


@pytest.mark.parametrize('seed', [0, 3])
def test_renamed_reordered_topology_does_not_follow_ids_or_tuple_order(seed):
    from tests.v5.test_structure_variants import renamed
    bp = content.select_blueprint(3, 'hard', seed=seed)
    altered = renamed(bp)
    a, b = purpose.puzzle_effects(bp), purpose.puzzle_effects(altered)
    def normalized(x, effects):
        objects = {o.object_id: o for o in x.objects}
        return sorted((x.room_ids.index(objects[key].room_id), next(p.mechanism for p in x.puzzles if p.puzzle_id == objects[key].reference_id), value['purpose'], value['carrier'], 'EXIT' if value.get('destination_room_slot') == 'EXIT' else x.room_ids.index(value['destination_room_slot']) if 'destination_room_slot' in value else None, len(value['unlocks_material_slots'])) for key, value in effects.items())
    assert normalized(bp, a) == normalized(altered, b)
    assert structures.structure_signatures(bp) == structures.structure_signatures(altered)


@pytest.mark.parametrize('mechanism', ['code', 'sequence', 'circuit', 'item'])
def test_passage_carrier_names_reject_cabinet_identity_preserve_location(mechanism):
    chosen = next((bp, obj) for n, d, seed in CELLS for bp in [content.select_blueprint(n, d, seed=seed)] for obj in bp.objects if obj.kind == 'puzzle' and next(p.mechanism for p in bp.puzzles if p.puzzle_id == obj.reference_id) == mechanism and purpose.puzzle_effects(bp)[obj.object_id]['purpose'] == 'passage_control')
    bp, obj = chosen
    good = valid_content(bp)
    for name in (['门禁供电箱', '柜旁门禁供电箱'] if mechanism == 'circuit' else ['门禁终端', '柜旁门禁终端', '储物柜旁的通行控制台']):
        raw = copy.deepcopy(good); raw['objects'][obj.object_id]['name'] = name
        before = json.dumps(raw, ensure_ascii=False)
        draft = content.assemble_draft(bp, before)
        assert next(o for r in draft['rooms'] for o in r['objects'] if o['object_id'] == obj.object_id)['name'] == name
        assert json.dumps(raw, ensure_ascii=False) == before
    for name in ['前厅储物柜锁', '门禁储物柜控制器', '柜子门禁终端']:
        raw = copy.deepcopy(good); raw['objects'][obj.object_id]['name'] = name
        with pytest.raises(ValueError, match='^GENERATION_PUZZLE_NAME_INVALID$'):
            content.assemble_draft(bp, json.dumps(raw))


@pytest.mark.parametrize('kind,expected', [('duplicate', 'DUPLICATE_KEY'), ('schema', 'GENERATION_CONTENT_INVALID'), ('name', 'GENERATION_PUZZLE_NAME_INVALID')])
def test_strict_schema_name_gate_precedes_assembly_and_keeps_raw(monkeypatch, kind, expected):
    bp = content.select_blueprint(1, 'easy', seed=0); value = valid_content(bp)
    def forbidden(*args, **kwargs): pytest.fail('Invalid new reply reached legacy Host assembler')
    monkeypatch.setattr(content.v1, 'assemble_draft', forbidden)
    if kind == 'duplicate': raw = '{"title":"a","title":"b"}'
    else:
        if kind == 'schema': value['objects'][next(iter(value['objects']))]['description'] = 'extra forbidden'
        else:
            oid = next(key for key, effect in purpose.puzzle_effects(bp).items() if effect['purpose'] == 'passage_control')
            value['objects'][oid]['name'] = '储物柜锁'
        raw = json.dumps(value, ensure_ascii=False)
    original = raw
    with pytest.raises(ValueError, match='^' + expected + '$'):
        content.assemble_draft(bp, raw)
    assert raw == original


@pytest.mark.parametrize('rooms,seed', [(1, 0), (3, 3)])
def test_two_representative_original_compile_witness_exit_and_cache(rooms, seed):
    bp = content.select_blueprint(rooms, 'hard', seed=seed); raw = valid_content(bp)
    draft = content.assemble_draft(bp, raw); compiled = compile_level(draft, rooms, 'hard')
    rules = GeneratedRules(compiled); state = rules.initial_state(); moves = []
    for action in compiled.witness:
        before = rules.visible_state('synthetic_passage_session', state)
        if action['tool'] == 'move':
            dest = action['arguments']['destination_id']
            assert next(x for x in before['exits'] if x['destination_id'] == dest)['unlocked']
            moves.append(dest)
        state, _ = rules.apply_action(state, action['tool'], action['arguments'])
    assert state.status == 'won' and state.room_id == 'EXIT' and len(moves) == rooms
    if os.environ.get('SP_CACHE_DIR'):
        payload = {'rooms': rooms, 'seed': seed, 'draft': Draft.model_validate(draft).model_dump(), 'witness': compiled.witness, 'definition_hash': compiled.definition_hash}
        with (cache_root() / f'R{rooms}.json').open('x', encoding='utf-8') as stream: json.dump(payload, stream, ensure_ascii=False)


def test_old_full_definition_restore_and_reload_never_calls_new_guard(tmp_path, monkeypatch):
    from backend.app.main import create_v5_app
    generator = FixtureGenerator(); generator.output = make_fixture(1, 'easy')
    app = create_v5_app(tmp_path / 'game-v5.sqlite', generation_service=generator)
    actor = Actor(app).authenticate('old_passage_owner'); job = actor.generate(1, 'easy')
    state = actor.session('generated', job['level_id']); sid = state['session_id']; db = app.state.v5_database
    fields = db.owned(db.authenticate(actor.client.cookies.get('campus_v5_session')), sid).rules.game_fields
    old_hash = private_game_hash(db, sid, fields)
    with db.transaction() as con: before = con.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0]
    response = actor.post(f'/sessions/{sid}/saves', actor.versioned(state, name='旧完整定义'))
    assert response.status_code == 201; save_id = response.json()['data']['slot']['save_id']
    def forbidden(*args, **kwargs): pytest.fail('Old full definition tried new purpose/guard/provider')
    monkeypatch.setattr(content, 'assemble_draft', forbidden); monkeypatch.setattr(content, 'validate_puzzle_names', forbidden); monkeypatch.setattr(purpose, 'puzzle_effects', forbidden); monkeypatch.setattr(generator, 'generate', forbidden)
    reopened = create_v5_app(db.path, generation_service=generator); actor = Actor(reopened).authenticate('old_passage_owner', False)
    current = actor.state(sid); response = actor.post(f'/sessions/{sid}/saves/{save_id}/restore', actor.versioned(current))
    assert response.status_code == 200 and response.json()['data']['visible_state']['definition_hash'] == state['definition_hash']
    assert private_game_hash(reopened.state.v5_database, sid, fields) == old_hash
    with db.transaction() as con: assert con.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0] == before


def test_wrong_purpose_reply_is_single_mock_dispatch_rejected_no_level(tmp_path, monkeypatch):
    from backend.app.main import create_v5_app
    bp = content.select_blueprint(1, 'easy', seed=0); raw = valid_content(bp)
    oid = next(key for key, effect in purpose.puzzle_effects(bp).items() if effect['purpose'] == 'passage_control'); raw['objects'][oid]['name'] = '前厅储物柜锁'
    monkeypatch.setattr(content, 'select_blueprint', lambda *a, **kw: bp)
    sends = []; ledger = BudgetLedger(tmp_path / 'synthetic-budget.sqlite')
    def handler(request):
        sends.append(True); assert request.headers['authorization'] == 'Bearer ' + CANARY and CANARY.encode() not in request.content
        return httpx.Response(200, json=wire_body(json.dumps(raw)))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    app = create_v5_app(tmp_path / 'game-v5.sqlite', generation_service=GenerationService(lambda key: provider)); actor = Actor(app).authenticate('purpose_reject')
    response = actor.post('/level-generations', {'request_id': rid(), 'theme': '合成校园', 'room_count': 1, 'difficulty': 'easy'}, headers={'X-AI-Api-Key': CANARY}); assert response.status_code == 202
    jid = response.json()['data']['job']['job_id']; job = actor.get('/level-generations/' + jid).json()['data']['job']
    assert job['status'] == 'rejected' and job['error_code'] == 'MODEL_INVALID_OUTPUT' and job['level_id'] is None
    assert actor.get('/levels').json()['data']['levels'] == [] and len(sends) == ledger.snapshot()['calls'] == 1


if os.environ.get('SP_BROWSER_FIXTURE') == '1':
    directory = cache_root(); db = directory / 'game-v5.sqlite'
    assert not db.exists(), 'Browser fixture requires fresh owned database'
    os.environ.update(SQLITE_PATH=str(db), GAMEPLAY_VERSION='v5', AI_PROVIDER='mock')
    from backend.app.main import create_v5_app
    class CachedGenerator:
        async def generate(self, *, room_count, **kwargs):
            assert room_count in (1, 3)
            return json.loads((directory / f'R{room_count}.json').read_text(encoding='utf-8'))['draft']
    browser_app = create_v5_app(db, generation_service=CachedGenerator())
