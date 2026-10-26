"""TXT-C1--C5: synthetic content2 QA, after Main frozen-candidate GO only.

The real saved model replies/private proofs are deliberately not inputs here.
Eighteen cases use pure assembly; actual compile/API proof is limited to the
two existing representative production-adapter cases selected by the runner.
"""
from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from backend.app.domain import blueprints as v1
from backend.app.domain import generation_content_v2 as v2
from backend.app.domain.generated import CompiledLevel, Draft, GeneratedRules, derive
from tests.v5.conftest import Actor, private_game_hash, rid
from tests.v5.test_blueprint_generation import SHAPES, expected_answers, synthetic_content, synthetic_model_content

ROOT = Path(__file__).resolve().parents[2]
EPOCH = ROOT / 'evidence/upgrade/v5.0/text-authority-v2'


def observe(name, value):
    directory = os.environ.get('TEXT_AUTHORITY_QA_OUTPUT')
    if directory:
        target = Path(directory).resolve()
        target.relative_to((EPOCH / 'qa').resolve())
        assert Path(name).name == name and name.endswith('.json')
        target.mkdir(parents=True, exist_ok=True)
        destination = target / name
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')


def content(bp, alternate=False):
    # This is explicitly authored synthetic content, not a converted real reply.
    result = synthetic_model_content(bp)
    if alternate:
        result['parameters'] = synthetic_content(bp, alternate=True)['parameters']
    letters = '甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳'
    for index, row in enumerate(result['objects'].values()):
        row['name'] = '合成校园物件' + letters[index]
    return result


def without_object_descriptions(draft):
    result = copy.deepcopy(draft)
    for room in result['rooms']:
        for obj in room['objects']:
            del obj['description']
    return result


def memory_rules(draft):
    model = Draft.model_validate(draft)
    clues = {clue.clue_id: clue for clue in model.clues}
    answers = {p.puzzle_id: derive(p, clues) for p in model.puzzles
               if p.mechanism in {'code', 'sequence'}}
    # No compile/proof/solver; these states test the original public projection.
    compiled = CompiledLevel(model, answers, [])
    return GeneratedRules(compiled), answers


@pytest.mark.parametrize('seed', [0, 1])
@pytest.mark.parametrize('rooms,difficulty,count,combos,depth', SHAPES)
def test_eighteen_v2_contracts_preserve_structure_parameters_and_v1_history(seed, rooms, difficulty, count, combos, depth):
    bp = v2.select_blueprint(rooms, difficulty, seed=seed)
    legacy = v1.select_blueprint(rooms, difficulty, seed=seed)
    assert bp.content_version == '2.0.0' and replace(bp, content_version='1.0.0') == legacy
    schema = v2.content_schema(bp)
    Draft202012Validator.check_schema(schema)
    assert set(schema['properties']['objects']['required']) == {obj.object_id for obj in bp.objects}
    assert schema['$defs']['object_name'] == {
        'type': 'object', 'properties': {'name': {'type': 'string', 'minLength': 1, 'maxLength': 40}},
        'required': ['name'], 'additionalProperties': False}
    normalized = copy.deepcopy(schema)
    normalized['properties']['content_version'] = {'const': '1.0.0'}
    del normalized['$defs']['object_name']
    normalized['properties']['objects']['properties'] = {
        key: {'$ref': '#/$defs/slot_text'} for key in schema['properties']['objects']['properties']}
    assert normalized == v1.content_schema(legacy)
    texts = []
    for alternate in (False, True):
        raw = content(bp, alternate)
        original = copy.deepcopy(raw)
        Draft202012Validator(schema).validate(raw)
        result = v2.assemble_draft(bp, json.dumps(raw, ensure_ascii=False))
        old = synthetic_content(legacy, alternate)
        old.update(title=raw['title'], story=raw['story'], rooms=copy.deepcopy(raw['rooms']))
        for oid, row in old['objects'].items():
            row['name'] = raw['objects'][oid]['name']
        baseline = v1.assemble_draft(legacy, old)
        assert without_object_descriptions(result) == without_object_descriptions(baseline)
        rules, actual = memory_rules(result)
        assert actual == expected_answers(bp, raw['parameters'])
        assert len(rules.d.rooms) == rooms and len(rules.d.puzzles) == count
        assert raw == original and v2.content_schema(bp) == schema
        texts.append({obj.object_id: obj.description for room in rules.d.rooms for obj in room.objects})
    assert texts[0] == texts[1], 'Host descriptions must not depend on typed answer values'
    fresh = v2.content_schema(bp)
    fresh['$defs']['object_name']['properties']['name']['maxLength'] = 1
    assert v2.content_schema(bp) == schema
    observe(f'pure-{seed}-{rooms}-{difficulty}.json', {
        'blueprint_id': bp.blueprint_id, 'content_contract': '2.0.0',
        'parameter_sets': 2, 'v1_structure_and_derived_answers_equal': True,
        'typed_values_do_not_change_Host_descriptions': True, 'new_solver_calls': 0})


@pytest.mark.parametrize('seed', [0, 1])
def test_strict_v2_rejects_before_helper_and_valid_conversion_keeps_raw_untouched(monkeypatch, seed):
    bp = v2.select_blueprint(3, 'hard', seed=seed)
    valid = content(bp)
    before = copy.deepcopy(valid)
    calls = []
    original_helper = v1.assemble_draft
    def helper(chosen, value):
        calls.append(copy.deepcopy(value))
        assert chosen is bp
        assert value['content_version'] == '1.0.0'
        assert value['parameters'] == valid['parameters']
        assert all(set(row) == {'name', 'description'} for row in value['objects'].values())
        return original_helper(chosen, value)
    monkeypatch.setattr(v1, 'assemble_draft', helper)
    v2.assemble_draft(bp, valid)
    assert len(calls) == 1 and valid == before
    calls.clear()
    bad = []
    def changed(label, mutate):
        value = copy.deepcopy(valid); mutate(value); bad.append((label, value))
    changed('old-version', lambda x: x.update(content_version='1.0.0'))
    changed('description-is-forbidden', lambda x: x['objects']['obj_key'].update(description='不得丢弃的合成原文'))
    changed('missing-name', lambda x: x['objects']['obj_key'].pop('name'))
    changed('wrong-name-type', lambda x: x['objects']['obj_key'].update(name=True))
    changed('long-name', lambda x: x['objects']['obj_key'].update(name='名' * 41))
    changed('extra-object', lambda x: x['objects'].update(unrequested={'name': '多余'}))
    changed('missing-extra-object', lambda x: x['objects'].pop('obj_extra_code_a'))
    changed('wrong-blueprint', lambda x: x.update(blueprint_id='position_v1-r1-easy'))
    changed('extra-root', lambda x: x.update(witness=[]))
    changed('unsafe-name', lambda x: x['objects']['obj_key'].update(name='<script>'))
    for key, value in valid['parameters'].items():
        changed('wrong-type-' + key, lambda x, k=key: x['parameters'].__setitem__(k, None))
        if isinstance(value, list):
            changed('short-' + key, lambda x, k=key: x['parameters'].__setitem__(k, x['parameters'][k][:-1]))
            if key not in {'digits', 'extra_digits'}:
                changed('duplicate-' + key, lambda x, k=key: x['parameters'].__setitem__(k, [x['parameters'][k][0]] * 4))
            for invalid in (True, 1.0, '９'):
                changed('typed-item-' + key, lambda x, k=key, v=invalid: x['parameters'][k].__setitem__(0, v))
        else:
            first = next(iter(value))
            for invalid in (True, 1, None, '９', 'invalid'):
                changed('typed-map-' + key, lambda x, k=key, f=first, v=invalid: x['parameters'][k].__setitem__(f, v))
    if 'device_map' in valid['parameters']:
        changed('duplicate-map-values', lambda x: x['parameters']['device_map'].__setitem__('F', x['parameters']['device_map']['E']))
    for label, value in bad:
        untouched = copy.deepcopy(value)
        # The original strict JSON safety boundary precedes schema validation.
        expected_error = 'UNSAFE_TEXT' if label == 'unsafe-name' else 'GENERATION_CONTENT_INVALID'
        with pytest.raises(ValueError, match=expected_error):
            v2.assemble_draft(bp, value)
        assert value == untouched and calls == [], label
    for operation in (v2.content_schema, v2.request_manifest):
        with pytest.raises(ValueError, match='BLUEPRINT_CONTENT_VERSION'):
            operation(v1.select_blueprint(3, 'hard', seed=seed))
    observe(f'strict-{seed}.json', {'valid_v2_helper_calls': 1, 'invalid_variants': len(bad),
        'invalid_helper_calls': 0, 'raw_and_blueprint_untouched': True, 'repair_or_fallback': False})


@pytest.mark.parametrize('raw', ['{"title":"x","title":"y"}', '{"a":{"b":1,"b":2}}',
    '{"n":NaN}', '{"n":Infinity}', '[' * 34 + '0' + ']' * 34, ' ' * 65537, '{', '[]', 'null'],
    ids=['duplicate-root', 'duplicate-nested', 'nan', 'infinity', 'depth34', 'size65537', 'truncated', 'array', 'null'])
def test_raw_invalid_v2_never_reaches_v1_helper(monkeypatch, raw):
    bp = v2.select_blueprint(1, 'easy', seed=0)
    v2.assemble_draft(bp, content(bp))  # A valid v2 baseline must work first.
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid model content reached the internal v1 helper')
    monkeypatch.setattr(v1, 'assemble_draft', forbidden)
    with pytest.raises((ValueError, TypeError, RecursionError)):
        v2.assemble_draft(bp, raw)


@pytest.mark.parametrize('seed', [0, 1])
def test_role_text_reference_renaming_decoy_and_maximum_name(seed):
    bp = v2.select_blueprint(3, 'hard', seed=seed)
    item = next(obj for obj in bp.objects if obj.kind == 'item')
    actual = replace(item, object_id='renamed_real_key', reference_id='renamed_inventory_key')
    decoy = replace(item, slot=max(obj.slot for obj in bp.objects if obj.room_id == item.room_id) + 1)
    bp = replace(bp, objects=(decoy,) + tuple(actual if obj == item else obj for obj in bp.objects),
                 puzzles=tuple(replace(p, required_item_id=actual.reference_id) if p.mechanism == 'item' else p for p in bp.puzzles))
    raw = content(bp)
    raw['objects'][actual.object_id]['name'] = '真实关联钥匙' + '名' * 34  # Exactly 40 characters.
    raw['objects'][decoy.object_id]['name'] = '旧槽诱饵物件'
    original = copy.deepcopy(raw)
    assembled = v2.assemble_draft(bp, raw)
    objects = {obj['object_id']: obj for room in assembled['rooms'] for obj in room['objects']}
    item_puzzle = next(p for p in bp.puzzles if p.mechanism == 'item')
    puzzle_object = next(obj for obj in bp.objects if obj.reference_id == item_puzzle.puzzle_id and obj.kind == 'puzzle')
    assert raw['objects'][actual.object_id]['name'] in objects[puzzle_object.object_id]['description']
    assert raw['objects'][decoy.object_id]['name'] not in objects[puzzle_object.object_id]['description']
    for obj in bp.objects:
        text = objects[obj.object_id]['description']
        assert 0 < len(text) <= 240
        assert not any(word in text for word in ('放回', '挂回', '归还', '清单', '资料袋', '字母排序', '按字母'))
        if obj.kind == 'item':
            assert '背包' in text and '保留' in text
        if obj.role in {'code_source', 'device_source'}:
            assert '源序' in text
            if bp.family == 'mapping_v1': assert '符号' in text
            else: assert ('数字' if obj.role == 'code_source' else '设备') in text
        if obj.role == 'reading_positions': assert '位置' in text
        if obj.role == 'symbol_mapping': assert '对应' in text
        if obj.role.startswith('extra_'):
            assert '片段' in text and ('数字' if 'code' in obj.role else '设备') in text
            assert not any(word in text for word in ('前两', '后两', '第一', '第二', '左侧', '右侧'))
        if obj.kind == 'puzzle' and obj.role in {'code', 'sequence', 'circuit'}:
            assert {'code': '数字', 'sequence': '设备', 'circuit': '线路'}[obj.role] in text
    assert raw == original
    observe(f'roles-{seed}.json', {'actual_item_reference_after_rename_and_decoy': True,
        'name_length': len(raw['objects'][actual.object_id]['name']), 'roles_checked': len(objects),
        'mechanisms': sorted({p.mechanism for p in bp.puzzles}), 'private_real_content_used': False})


@pytest.mark.parametrize('seed', [0, 1])
def test_original_discovery_gate_keeps_answers_out_of_Host_descriptions(seed):
    bp = v2.select_blueprint(3, 'hard', seed=seed)
    raw = content(bp)
    rules, answers = memory_rules(v2.assemble_draft(bp, raw))
    state = rules.initial_state()
    puzzle = next(p for p in rules.d.puzzles if p.mechanism == 'code')
    target = next(o for room in rules.d.rooms for o in room.objects if o.puzzle_id == puzzle.puzzle_id)
    facts = [next(o for room in rules.d.rooms for o in room.objects if o.clue_id == cid) for cid in puzzle.clue_ids]
    stages = []
    def check(expected_clues, relationship_visible):
        projected = rules.visible_state('synthetic-projection', state)
        assert {c['clue_id'] for c in projected['clues']} == set(expected_clues)
        descriptions = [o['description'] for o in projected['objects']]
        assert all(answers[puzzle.puzzle_id] not in text for text in descriptions)
        current = next(o for o in projected['objects'] if o['object_id'] == target.object_id)
        assert ('资料组合次序：' in current['description']) is relationship_visible
        if not relationship_visible:
            assert all(cid not in current['description'] for cid in puzzle.clue_ids)
        assert all(o['object_id'] not in {obj.object_id for room in rules.d.rooms[1:] for obj in room.objects}
                   for o in projected['objects'])
        stages.append({'discovered_clues': len(expected_clues), 'combination_relation_visible': relationship_visible})
    check([], False)
    state, _ = rules.apply_action(state, 'inspect', {'object_id': target.object_id})
    check([], False)
    state, _ = rules.apply_action(state, 'inspect', {'object_id': facts[0].object_id})
    check([puzzle.clue_ids[0]], False)
    state, _ = rules.apply_action(state, 'inspect', {'object_id': facts[1].object_id})
    check(puzzle.clue_ids, True)
    for clue, _ in zip(facts, puzzle.clue_ids):
        assert clue.description == next(o['description'] for o in rules.visible_state('synthetic-projection', state)['objects'] if o['object_id'] == clue.object_id)
    observe(f'discovery-{seed}.json', {'stages': stages, 'original_projection_rules_unchanged': True,
        'early_answer_text': False, 'future_room_objects_leaked': False, 'solver_calls': 0})


def test_v2_static_contract_build_and_frozen_v1_sources():
    from contracts.v2.build_generation_content_v2 import build
    from contracts.v2.build_generation_content import build as old_build
    artifact = json.loads((ROOT / 'contracts/v2/generation-content-v2.schema.json').read_text(encoding='utf-8'))
    assert artifact == build() and len(artifact['oneOf']) == 18
    Draft202012Validator.check_schema(artifact)
    for seed in (0, 1):
        for rooms, difficulty, *_ in SHAPES:
            bp = v2.select_blueprint(rooms, difficulty, seed=seed)
            Draft202012Validator(artifact).validate(content(bp))
    historical = json.loads((ROOT / 'contracts/v2/generation-content.schema.json').read_text(encoding='utf-8'))
    assert historical == old_build() and historical['content_contract_version'] == '1.0.0'
    plan = json.loads((EPOCH / 'plan.json').read_text(encoding='utf-8'))
    for name, digest in plan['frozen_raw'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    observe('contracts-frozen.json', {'new_variants': 18, 'historical_variants': 18,
        'new_and_old_builder_exact': True, 'frozen_sources': len(plan['frozen_raw']), 'all_match': True})


@pytest.mark.parametrize('kind', ['old-model-version', 'forbidden-object-description'])
def test_production_service_rejects_non_v2_model_reply_once_without_fallback(tmp_path, monkeypatch, kind):
    import asyncio
    import httpx
    from backend.app.ai.budget import BudgetLedger
    from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
    from backend.app.ai.v5 import GenerationService, ServiceError
    from tests.v5.conftest import CANARY
    from tests.v5.test_generation import wire_body
    bp = v2.select_blueprint(1, 'easy', seed=0)
    valid = content(bp)
    v2.assemble_draft(bp, valid)
    bad = copy.deepcopy(valid)
    if kind == 'old-model-version':
        bad = synthetic_content(v1.select_blueprint(1, 'easy', seed=0))
    else:
        bad['objects']['obj_key']['description'] = '明确禁止模型新增的合成说明'
    monkeypatch.setattr(v2, 'select_blueprint', lambda *args, **kwargs: bp)
    sends = []
    ledger = BudgetLedger(tmp_path / 'synthetic-v2-rejection-budget.sqlite')
    def handler(request):
        sends.append(request)
        assert CANARY.encode() not in request.content
        return httpx.Response(200, json=wire_body(json.dumps(bad, ensure_ascii=False)))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    with pytest.raises(ServiceError) as error:
        asyncio.run(GenerationService(lambda key: provider).generate(theme='合成校园', room_count=1,
            difficulty='easy', api_key=CANARY, draft_schema=Draft.model_json_schema()))
    assert error.value.code == 'MODEL_INVALID_OUTPUT' and CANARY not in str(error.value)
    assert len(sends) == 1 and ledger.snapshot()['calls'] == 1


def test_saved_full_v1_definition_text_and_hash_restore_reload_without_content_service(actor, system, monkeypatch):
    from backend.app.ai.v5 import GenerationService
    from backend.app.main import create_v5_app
    app, generator = system
    # The old complete-Draft fixture is isolated setup, never a product fallback.
    old = v1.assemble_draft(v1.select_blueprint(1, 'easy', seed=0), synthetic_content(v1.select_blueprint(1, 'easy', seed=0)))
    old['rooms'][0]['objects'][0]['description'] = '历史定义的特定原说明应原样保留。'
    generator.output = old
    job = actor.generate(1, 'easy')
    state = actor.session('generated', job['level_id']); sid = state['session_id']
    db = app.state.v5_database
    principal = db.authenticate(actor.client.cookies.get('campus_v5_session'))
    fields = db.owned(principal, sid).rules.game_fields
    original_hash = state['definition_hash']; game_hash = private_game_hash(db, sid, fields)
    with db.transaction() as connection:
        definition_before = connection.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0]
    saved = actor.post(f'/sessions/{sid}/saves', actor.versioned(state, name='历史完整定义'))
    assert saved.status_code == 201
    save_id = saved.json()['data']['slot']['save_id']
    def forbidden(*args, **kwargs):
        pytest.fail('Old definition restore/reload attempted new content generation')
    monkeypatch.setattr(v1, 'select_blueprint', forbidden)
    monkeypatch.setattr(v2, 'select_blueprint', forbidden)
    reopened = create_v5_app(db.path, generation_service=GenerationService(forbidden))
    owner = Actor(reopened).authenticate('qa_alpha', False)
    restored = owner.post(f'/sessions/{sid}/saves/{save_id}/restore', owner.versioned(owner.state(sid)))
    assert restored.status_code == 200
    current = restored.json()['data']['visible_state']
    assert current['definition_hash'] == original_hash
    assert private_game_hash(reopened.state.v5_database, sid, fields) == game_hash
    assert current['objects'][0]['description'] == old['rooms'][0]['objects'][0]['description']
    with db.transaction() as connection:
        assert connection.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0] == definition_before
        session_before = connection.execute('SELECT state_json FROM sessions WHERE session_id=?', (sid,)).fetchone()[0]
        connection.execute('UPDATE generated_levels SET definition_hash=? WHERE level_id=?', ('0' * 64, job['level_id']))
    rejected = owner.post(f'/sessions/{sid}/saves/{save_id}/restore', owner.versioned(current))
    assert rejected.status_code == 409
    with db.transaction() as connection:
        assert connection.execute('SELECT state_json FROM sessions WHERE session_id=?', (sid,)).fetchone()[0] == session_before
    assert len(generator.calls) == 1
    observe('historical-definition.json', {'setup': 'explicit synthetic complete v1 Draft',
        'original_definition_hash': original_hash, 'text_and_definition_bytes_preserved': True,
        'restore_reload_without_model': True, 'bad_definition_hash_rejected_without_state_write': True})
