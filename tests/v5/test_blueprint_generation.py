"""Independent synthetic QA for the accepted Host-structure/AI-content epoch.

The old complete-Draft prompt tests belong to their sealed source epochs. These
cases test the newly accepted internal content contract, without paid calls.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# This import establishes isolated import-time database paths before main.
from tests.v5.conftest import (Actor, CANARY, assert_error, make_fixture,
                              private_game_hash, replay, rid)
import httpx
import pytest
from jsonschema import Draft202012Validator
from backend.app.ai.budget import BudgetLedger
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits
from backend.app.ai.v5 import GenerationService, ServiceError
from backend.app.domain import blueprints
from backend.app.domain import generation_content_v2 as current_content
from backend.app.domain.generated import Draft, GeneratedRules, compile_level
from tests.v5.test_generation import wire_body

SHAPES = [(1, 'easy', 2, 0, 1), (1, 'normal', 3, 1, 1),
          (1, 'hard', 4, 2, 3), (2, 'easy', 3, 0, 1),
          (2, 'normal', 4, 1, 1), (2, 'hard', 5, 2, 3),
          (3, 'easy', 4, 0, 1), (3, 'normal', 5, 1, 1),
          (3, 'hard', 6, 2, 3)]
QA_ROOT = ROOT / 'evidence/upgrade/v5.0/blueprint-generation/qa'


def observation(name, value):
    directory = os.environ.get('BLUEPRINT_QA_OUTPUT')
    if not directory:
        return
    destination = Path(directory).resolve()
    destination.relative_to(QA_ROOT.resolve())
    assert Path(name).name == name and name.endswith('.json')
    destination.mkdir(parents=True, exist_ok=True)
    (destination / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def synthetic_content(bp, alternate=False):
    """QA-owned model reply; independent values, never a production fixture."""
    parameters = ({'digits': list('2759'), 'positions': [3, 1, 4, 2]}
                  if bp.family == 'position_v1' else
                  {'code_symbols': list('CADB'), 'digit_map': dict(zip('ABCD', '2759'))})
    if len(bp.puzzles) >= 3:
        if bp.family == 'position_v1':
            parameters['devices'] = ['device_c', 'device_a', 'device_d', 'device_b']
        else:
            parameters.update(sequence_symbols=list('GEHF'), device_map=dict(zip(
                'EFGH', ['device_c', 'device_a', 'device_d', 'device_b'])))
    if len(bp.puzzles) >= 5:
        parameters['extra_digits'] = list('6813')
    if len(bp.puzzles) >= 6:
        parameters['extra_devices'] = ['device_b', 'device_d', 'device_a', 'device_c']
    if alternate:
        if bp.family == 'position_v1':
            parameters['digits'] = list('8264')
            parameters['positions'] = [2, 4, 1, 3]
            if 'devices' in parameters:
                parameters['devices'] = ['device_a', 'device_b', 'device_c', 'device_d']
        else:
            parameters['code_symbols'] = list('BDAC')
            parameters['digit_map'] = dict(zip('ABCD', '8264'))
            if 'device_map' in parameters:
                parameters['sequence_symbols'] = list('FHEG')
                parameters['device_map'] = dict(zip('EFGH', ['device_a', 'device_b', 'device_c', 'device_d']))
        if 'extra_digits' in parameters:
            parameters['extra_digits'] = list('4072')
        if 'extra_devices' in parameters:
            parameters['extra_devices'] = ['device_d', 'device_c', 'device_b', 'device_a']
    return {'content_version': '1.0.0', 'blueprint_id': bp.blueprint_id,
            'title': '合成校园档案', 'story': '雨后的校园保存着一次活动的记录。',
            'rooms': {key: {'name': '校园活动室', 'description': '桌面摆着整理后的活动材料。'} for key in bp.room_ids},
            'objects': {obj.object_id: {'name': '校园记录物件', 'description': '请结合公开资料查看。'} for obj in bp.objects},
            'parameters': parameters}


def blueprint_for_messages(messages):
    value = json.loads(messages[1]['content'])
    selected = value['schema']['properties']['blueprint_id']['const']
    matches = [current_content.select_blueprint(rooms, difficulty, seed=seed)
               for seed in (0, 1, 2, 3) for rooms, difficulty, *_ in SHAPES]
    return next(bp for bp in matches if bp.blueprint_id == selected)


def synthetic_model_content(bp, version='2.0.0'):
    """Explicit QA synthetic reply for the chosen model contract, never real raw repair."""
    assert version in {'1.0.0', '2.0.0'}
    value = synthetic_content(bp)
    value['content_version'] = version
    if version == '2.0.0':
        value['objects'] = {key: {'name': row['name']} for key, row in value['objects'].items()}
    return value


def content_for_messages(messages):
    value = json.loads(messages[1]['content'])
    version = value['schema']['properties']['content_version']['const']
    return synthetic_model_content(blueprint_for_messages(messages), version)


def expected_answers(bp, params):
    if bp.family == 'position_v1':
        code = ''.join(params['digits'][index - 1] for index in params['positions'])
        sequence = ([params['devices'][index - 1] for index in params['positions']]
                    if 'devices' in params else None)
    else:
        code = ''.join(params['digit_map'][key] for key in params['code_symbols'])
        sequence = ([params['device_map'][key] for key in params['sequence_symbols']]
                    if 'device_map' in params else None)
    result = {'puzzle_1': code}
    if sequence is not None:
        result['puzzle_2'] = sequence
    if 'extra_digits' in params:
        result['puzzle_4'] = ''.join(params['extra_digits'])
    if 'extra_devices' in params:
        result['puzzle_5'] = params['extra_devices']
    return result


def assert_structure(compiled, rooms, count, combos, depth):
    definition = compiled.draft
    assert len(definition.rooms) == rooms and len(definition.puzzles) == count
    objects = [obj for room in definition.rooms for obj in room.objects]
    assert all(len(room.objects) <= 8 for room in definition.rooms)
    assert all(len({obj.slot for obj in room.objects}) == len(room.objects) for room in definition.rooms)
    assert sum(obj.kind == 'item' for obj in objects) <= 4
    puzzles = {p.puzzle_id: p for p in definition.puzzles}
    def dependency_depth(key):
        return 1 + max([dependency_depth(p) for p in puzzles[key].prerequisite_ids] or [0])
    assert max(map(dependency_depth, puzzles)) >= depth
    assert sum(p.mechanism in {'code', 'sequence'} and len(p.clue_ids) >= 2 for p in definition.puzzles) >= combos
    if rooms > 1:
        clue_room = {obj.clue_id: room.room_id for room in definition.rooms for obj in room.objects if obj.clue_id}
        item_room = {obj.item_id: room.room_id for room in definition.rooms for obj in room.objects if obj.item_id}
        assert any(any(clue_room[key] != p.room_id for key in p.clue_ids) or
                   (p.required_item_id and item_room[p.required_item_id] != p.room_id) for p in definition.puzzles)
    if rooms == 1 and count == 4:
        assert len(objects) == 8
        assert sorted(obj.kind for obj in objects) == ['clue'] * 3 + ['item'] + ['puzzle'] * 4
    if count >= 4:
        assert {p.mechanism for p in definition.puzzles} == {'item', 'code', 'sequence', 'circuit'}


@pytest.mark.parametrize('seed,family', [(0, 'position_v1'), (1, 'mapping_v1')])
@pytest.mark.parametrize('rooms,difficulty,count,combos,depth', SHAPES)
def test_eighteen_structures_and_model_parameters_have_actual_answers(seed, family, rooms, difficulty, count, combos, depth):
    bp = blueprints.select_blueprint(rooms, difficulty, seed=seed)
    assert bp.family == family and bp.content_version == '1.0.0'
    records = []
    for alternate in (False, True):
        content = synthetic_content(bp, alternate)
        schema = blueprints.content_schema(bp)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(content)
        before = copy.deepcopy(content)
        compiled = compile_level(blueprints.assemble_draft(bp, json.dumps(content)), rooms, difficulty)
        assert content == before
        assert_structure(compiled, rooms, count, combos, depth)
        assert compiled.answers == expected_answers(bp, content['parameters'])
        rules = GeneratedRules(compiled)
        state = rules.initial_state()
        for action in compiled.witness:
            state, _ = rules.apply_action(state, action['tool'], action['arguments'])
        assert compiled.witness and state.status == 'won' and state.room_id == 'EXIT'
        records.append({'definition_hash': compiled.definition_hash, 'witness_steps': len(compiled.witness),
                        'answers_sha256': hashlib.sha256(json.dumps(compiled.answers, sort_keys=True).encode()).hexdigest(),
                        'actual_rule_replay': 'won', 'object_counts': [len(r.objects) for r in compiled.draft.rooms]})
    assert records[0]['definition_hash'] != records[1]['definition_hash']
    assert records[0]['answers_sha256'] != records[1]['answers_sha256']
    observation(f'structure-{family}-{rooms}-{difficulty}.json', {'scope': 'synthetic content, not real model quality',
                'family': family, 'rooms': rooms, 'difficulty': difficulty, 'variants': records, 'paid_calls': 0})


@pytest.mark.parametrize('seed', [0, 1])
def test_extra_parameters_are_independent_and_selected_contract_is_exact(seed):
    bp = blueprints.select_blueprint(3, 'hard', seed=seed)
    content = synthetic_content(bp)
    original = compile_level(blueprints.assemble_draft(bp, content), 3, 'hard')
    for parameter, target, replacement in [('extra_digits', 'puzzle_4', list('4072')),
                                          ('extra_devices', 'puzzle_5', ['device_d', 'device_c', 'device_b', 'device_a'])]:
        changed = copy.deepcopy(content)
        changed['parameters'][parameter] = replacement
        result = compile_level(blueprints.assemble_draft(bp, changed), 3, 'hard')
        assert result.answers[target] != original.answers[target]
        assert {key: value for key, value in result.answers.items() if key != target} == {key: value for key, value in original.answers.items() if key != target}
    wrong = copy.deepcopy(content)
    wrong['blueprint_id'] = blueprints.select_blueprint(3, 'hard', seed=1-seed).blueprint_id
    with pytest.raises(ValueError):
        blueprints.assemble_draft(bp, wrong)
    returned = blueprints.content_schema(bp)
    returned['properties']['title']['maxLength'] = 999
    assert blueprints.content_schema(bp)['properties']['title']['maxLength'] == 40


def invalid_contents(bp):
    valid = synthetic_content(bp)
    for key in valid:
        bad = copy.deepcopy(valid); del bad[key]
        yield 'missing-' + key, bad
    for key in ('answer', 'rooms2', 'tools', 'witness', 'prerequisite_ids'):
        bad = copy.deepcopy(valid); bad[key] = []
        yield 'extra-' + key, bad
    for container in ('rooms', 'objects', 'parameters'):
        bad = copy.deepcopy(valid); bad[container]['unknown_slot'] = {'name': '多余', 'description': '多余'}
        yield 'extra-slot-' + container, bad
        bad = copy.deepcopy(valid); del bad[container][next(iter(bad[container]))]
        yield 'missing-slot-' + container, bad
    for text in ('<script>alert(1)</script>', 'https://example.invalid', 'file:private',
                 'C:\\private', 'DROP TABLE records', 'eval(secret)', 'javascript:alert(1)', '/private'):
        bad = copy.deepcopy(valid); bad['story'] = text
        yield 'unsafe-' + str(len(text)), bad
    for text in ('', '文' * 41, 17, None, True):
        bad = copy.deepcopy(valid); bad['title'] = text
        yield 'bad-title-' + repr(text)[:5], bad
    for key, value in valid['parameters'].items():
        for replacement in (None, True, 'bad', []):
            bad = copy.deepcopy(valid); bad['parameters'][key] = replacement
            yield 'bad-type-' + key, bad
        if isinstance(value, list):
            for replacement in (value[:-1], value + [value[0]], [value[0]] * 4):
                if 'digits' in key and len(replacement) == 4:
                    continue  # Repeated digits are legal; permutations must be unique.
                bad = copy.deepcopy(valid); bad['parameters'][key] = replacement
                yield 'bad-list-' + key, bad
            for replacement in (False, 1.0, '1', 0, 5, 'device_z', '９'):
                bad = copy.deepcopy(valid); bad['parameters'][key][0] = replacement
                if key in {'digits', 'extra_digits'} and replacement == '1':
                    continue
                yield 'bad-item-' + key, bad
        else:
            bad = copy.deepcopy(valid); del bad['parameters'][key][next(iter(value))]
            yield 'missing-map-entry-' + key, bad
            bad = copy.deepcopy(valid); bad['parameters'][key]['unknown'] = '1'
            yield 'extra-map-entry-' + key, bad
            for replacement in (True, 1, None, 'bad', 'device_z', '９'):
                bad = copy.deepcopy(valid); bad['parameters'][key][next(iter(value))] = replacement
                yield 'bad-map-value-' + key, bad
    if 'device_map' in valid['parameters']:
        bad = copy.deepcopy(valid); bad['parameters']['device_map']['F'] = bad['parameters']['device_map']['E']
        yield 'duplicate-device-map-values', bad


@pytest.mark.parametrize('seed', [0, 1])
def test_strict_typed_rejections_without_mutation(seed):
    bp = blueprints.select_blueprint(3, 'hard', seed=seed)
    rejected = []
    for label, content in invalid_contents(bp):
        before = copy.deepcopy(content)
        with pytest.raises((ValueError, TypeError)):
            blueprints.assemble_draft(bp, content)
        assert content == before, label
        rejected.append(label)
    observation(f'rejections-{bp.family}.json', {'rejected_cases': rejected, 'count': len(rejected), 'repair': False})


@pytest.mark.parametrize('raw', ['{"title":"a","title":"b"}', '{"nested":{"x":1,"x":2}}',
                                '{"n":NaN}', '{"n":Infinity}', '[' * 34 + '0' + ']' * 34,
                                ' ' * 65537, '{', '[]', 'null'],
                         ids=['duplicate-root', 'duplicate-nested', 'nan', 'infinity',
                              'depth34', 'raw-size65537', 'truncated', 'array-root', 'null-root'])
def test_raw_duplicate_nonfinite_depth_size_and_shape_rejected(raw):
    with pytest.raises((ValueError, TypeError, RecursionError)):
        blueprints.assemble_draft(blueprints.select_blueprint(1, 'easy', seed=0), raw)


@pytest.mark.parametrize('rooms,difficulty,seed', [(True, 'easy', 0), (1.0, 'easy', 0), (0, 'easy', 0),
                                                (4, 'easy', 0), (1, 'other', 0), (1, 'easy', True),
                                                (1, 'easy', -1), (1, 'easy', 1.0)])
def test_blueprint_selection_rejects_out_of_contract_inputs(rooms, difficulty, seed):
    with pytest.raises(ValueError):
        blueprints.select_blueprint(rooms, difficulty, seed=seed)


def test_internal_schema_is_reproducible_and_public_contracts_keep_their_roles():
    from contracts.v2.build_generation_content import build
    artifact = json.loads((ROOT / 'contracts/v2/generation-content.schema.json').read_text(encoding='utf-8'))
    assert artifact == build() and len(artifact['oneOf']) == 18
    Draft202012Validator.check_schema(artifact)
    for seed in (0, 1):
        for rooms, difficulty, *_ in SHAPES:
            content = synthetic_content(blueprints.select_blueprint(rooms, difficulty, seed=seed))
            Draft202012Validator(artifact).validate(content)
    assert len(json.loads((ROOT / 'contracts/v2/routes.json').read_text())['routes']) == 20
    # The sealed classic contract has 13 routes; the earlier QA expectation of 8
    # confused a historical interface count with this unchanged current artifact.
    assert len(json.loads((ROOT / 'contracts/routes.json').read_text())['routes']) == 13


@pytest.mark.parametrize('rooms,difficulty,seed', [(2, 'normal', 0), (3, 'hard', 1)])
def test_production_service_adapter_api_admission_witness_save_restore_and_owner_boundary(tmp_path, monkeypatch, rooms, difficulty, seed):
    from backend.app.main import create_v5_app
    from backend.app.domain import generated
    selected = current_content.select_blueprint(rooms, difficulty, seed=seed)
    content = synthetic_model_content(selected)
    compiled = compile_level(current_content.assemble_draft(selected, content), rooms, difficulty)
    selected_calls = []
    def choose(*args, **kwargs):
        selected_calls.append((args, kwargs))
        assert args == (rooms, difficulty) and kwargs == {}
        return selected
    monkeypatch.setattr(current_content, 'select_blueprint', choose)
    def forbidden_fixture(*args, **kwargs):
        raise AssertionError('Production generation reached make_fixture')
    monkeypatch.setattr(generated, 'make_fixture', forbidden_fixture)
    ledger = BudgetLedger(tmp_path / 'synthetic-production-budget.sqlite')
    sends = []
    def handler(request):
        sends.append(request)
        assert request.url == httpx.URL('https://api.deepseek.com/chat/completions')
        assert request.headers['authorization'] == 'Bearer ' + CANARY
        assert CANARY.encode() not in request.content
        payload = json.loads(request.content)
        supplied = json.loads(payload['messages'][1]['content'])
        assert supplied['schema'] == current_content.content_schema(selected)
        assert supplied['schema']['properties']['blueprint_id']['const'] == selected.blueprint_id
        assert payload['max_tokens'] == 6000 and payload['response_format'] == {'type': 'json_object'}
        assert not {'tools', 'tool_choice'} & payload.keys()
        return httpx.Response(200, json=wire_body(json.dumps(content)))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    service = GenerationService(lambda key: provider)
    app = create_v5_app(tmp_path / 'game-v5.sqlite', generation_service=service)
    actor = Actor(app).authenticate('blueprint_owner')
    intruder = Actor(app).authenticate('blueprint_other')
    body = {'request_id': rid(), 'theme': '校园记录 ' + CANARY, 'room_count': rooms, 'difficulty': difficulty}
    response = actor.post('/level-generations', body, headers={'X-AI-Api-Key': CANARY})
    assert response.status_code == 202, response.text
    jid = response.json()['data']['job']['job_id']
    job = actor.get('/level-generations/' + jid).json()['data']['job']
    assert job['status'] == 'ready' and job['level_id']
    repeated = actor.post('/level-generations', body, headers={'X-AI-Api-Key': CANARY})
    assert repeated.status_code == 200 and repeated.json()['data']['job']['job_id'] == jid
    assert len(sends) == 1 and len(selected_calls) == 1
    state = actor.session('generated', job['level_id']); sid = state['session_id']
    assert state['definition_hash'] == compiled.definition_hash
    db = app.state.v5_database
    principal = db.authenticate(actor.client.cookies.get('campus_v5_session'))
    fields = db.owned(principal, sid).rules.game_fields
    saved_hash = private_game_hash(db, sid, fields)
    saved = actor.post(f'/sessions/{sid}/saves', actor.versioned(state, name='蓝图早期'))
    assert saved.status_code == 201, saved.text
    save_id = saved.json()['data']['slot']['save_id']
    owner_before = actor.state(sid)
    for path in ('/level-generations/' + jid, '/levels/' + job['level_id'], f'/sessions/{sid}/state', f'/sessions/{sid}/saves'):
        assert_error(intruder.get(path), 404, 'NOT_FOUND')
    assert actor.state(sid) == owner_before
    state = replay(actor, state, compiled)
    assert state['status'] == 'won' and state['room_id'] == 'EXIT'
    def forbidden_reselection(*args, **kwargs):
        raise AssertionError('Restore/reopen attempted to generate or choose a new blueprint')
    monkeypatch.setattr(current_content, 'select_blueprint', forbidden_reselection)
    restored = actor.post(f'/sessions/{sid}/saves/{save_id}/restore', actor.versioned(state))
    assert restored.status_code == 200, restored.text
    state = restored.json()['data']['visible_state']
    assert state['definition_hash'] == compiled.definition_hash
    assert private_game_hash(db, sid, fields) == saved_hash
    reopened = create_v5_app(db.path, generation_service=service)
    actor = Actor(reopened).authenticate('blueprint_owner', False)
    state = actor.state(sid)
    restored = actor.post(f'/sessions/{sid}/saves/{save_id}/restore', actor.versioned(state))
    assert restored.status_code == 200 and restored.json()['data']['visible_state']['definition_hash'] == compiled.definition_hash
    assert len(sends) == 1 and ledger.snapshot()['calls'] == 1
    with sqlite3.connect(db.path) as connection:
        assert CANARY not in '\n'.join(connection.iterdump())
    with sqlite3.connect(ledger.path) as connection:
        assert CANARY not in '\n'.join(connection.iterdump())
        assert connection.execute('SELECT scope,state FROM budget_calls').fetchone() == ('v5_generation', 'settled')
    assert CANARY not in json.dumps(job)
    observation(f'api-production-{selected.family}-{rooms}-{difficulty}.json', {
        'scope': 'Production service/DeepSeekProvider with synthetic MockTransport and isolated accounts/DB/ledger',
        'blueprint_id': selected.blueprint_id, 'definition_hash': compiled.definition_hash,
        'model_dispatches': len(sends), 'blueprint_selections': len(selected_calls),
        'worker_admission': 'ready', 'actual_api_witness': 'won', 'witness_steps': len(compiled.witness),
        'save_restore_game_hash_match': True, 'factory_reopen_restore': True,
        'cross_owner_resources': '404 and owner unchanged', 'canary_in_game_or_budget_db': False, 'paid_calls': 0})


@pytest.mark.parametrize('kind', ['typed', 'extra', 'missing', 'wrong_blueprint', 'credential', 'full_draft', 'duplicate', 'depth', 'size', 'unsafe'])
def test_invalid_model_reply_is_rejected_after_one_send_without_repair_retry_or_fallback(tmp_path, monkeypatch, kind):
    selected = current_content.select_blueprint(1, 'hard', seed=0)
    monkeypatch.setattr(current_content, 'select_blueprint', lambda *args, **kwargs: selected)
    content = synthetic_model_content(selected)
    if kind == 'typed': content['parameters']['positions'][0] = True
    elif kind == 'extra': content['answer'] = 'ignored'
    elif kind == 'missing': del content['objects']['obj_relation']
    elif kind == 'wrong_blueprint': content['blueprint_id'] = 'mapping_v1-r1-hard'
    elif kind == 'credential': content['story'] = CANARY
    elif kind == 'full_draft': content = make_fixture(1, 'hard')
    elif kind == 'unsafe': content['story'] = '<script>test</script>'
    raw = json.dumps(content)
    if kind == 'duplicate': raw = '{"title":"x","title":"y"}'
    elif kind == 'depth': raw = '[' * 34 + '0' + ']' * 34
    elif kind == 'size': raw = ' ' * 65537
    ledger = BudgetLedger(tmp_path / 'synthetic-invalid-budget.sqlite'); sends = []
    def handler(request):
        sends.append(request)
        return httpx.Response(200, json=wire_body(raw))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    service = GenerationService(lambda key: provider)
    with pytest.raises(ServiceError) as error:
        asyncio.run(service.generate(theme='校园', room_count=1, difficulty='hard', api_key=CANARY, draft_schema=Draft.model_json_schema()))
    assert error.value.code == 'MODEL_INVALID_OUTPUT'
    assert len(sends) == 1 and ledger.snapshot()['calls'] == 1
    assert CANARY not in str(error.value)


def test_worker_rejection_does_not_publish_a_playable_level(tmp_path):
    from backend.app.main import create_v5_app
    ledger = BudgetLedger(tmp_path / 'synthetic-rejected-budget.sqlite'); sends = []
    def handler(request):
        sends.append(request)
        content = content_for_messages(json.loads(request.content)['messages'])
        content['parameters'] = {}
        return httpx.Response(200, json=wire_body(json.dumps(content)))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    app = create_v5_app(tmp_path / 'game-v5.sqlite', generation_service=GenerationService(lambda key: provider))
    actor = Actor(app).authenticate('blueprint_reject')
    response = actor.post('/level-generations', {'request_id': rid(), 'theme': '校园', 'room_count': 1, 'difficulty': 'easy'}, headers={'X-AI-Api-Key': CANARY})
    assert response.status_code == 202
    jid = response.json()['data']['job']['job_id']
    job = actor.get('/level-generations/' + jid).json()['data']['job']
    assert job['status'] == 'rejected' and job['error_code'] == 'MODEL_INVALID_OUTPUT' and job['level_id'] is None
    assert actor.get('/levels').json()['data']['levels'] == [] and len(sends) == 1


def test_preblueprint_full_definition_and_archive_restore_without_new_selection(actor, system, monkeypatch):
    from backend.app.main import create_v5_app
    # The old synthetic full-Draft injector is deliberate historical-format setup,
    # not a production fallback. It predates the new content contract entirely.
    app, generator = system
    job = actor.generate(2, 'normal')
    state = actor.session('generated', job['level_id']); sid = state['session_id']
    original_hash = state['definition_hash']
    saved = actor.post(f'/sessions/{sid}/saves', actor.versioned(state, name='旧完整定义'))
    assert saved.status_code == 201
    save_id = saved.json()['data']['slot']['save_id']
    compiled = compile_level(make_fixture(2, 'normal'), 2, 'normal')
    state = replay(actor, state, compiled, compiled.witness[:3])
    def no_new_blueprint(*args, **kwargs):
        raise AssertionError('Historical restore attempted new blueprint generation')
    monkeypatch.setattr(blueprints, 'select_blueprint', no_new_blueprint)
    reopened = create_v5_app(app.state.v5_database.path, generation_service=GenerationService(lambda key: pytest.fail('Restore attempted a provider')))
    actor = Actor(reopened).authenticate('qa_alpha', False)
    state = actor.state(sid)
    restored = actor.post(f'/sessions/{sid}/saves/{save_id}/restore', actor.versioned(state))
    assert restored.status_code == 200, restored.text
    assert restored.json()['data']['visible_state']['definition_hash'] == original_hash == compiled.definition_hash
    assert len(generator.calls) == 1
    observation('historical-definition-restore.json', {'setup': 'explicit QA-only old complete-Draft injection',
        'definition_hash': original_hash, 'restored_without_blueprint_or_provider': True,
        'old_format_versions_unchanged': True, 'paid_calls': 0})


@pytest.mark.parametrize('key', ['', ' ', 'bad key', '\u4e2d\u6587', 'x' * 257])
def test_missing_or_invalid_key_does_not_select_or_dispatch(key, monkeypatch):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append('called')
        pytest.fail('Invalid key reached selection/provider')
    monkeypatch.setattr(current_content, 'select_blueprint', forbidden)
    with pytest.raises(ServiceError) as error:
        asyncio.run(GenerationService(forbidden).generate(theme='校园', room_count=1, difficulty='easy', api_key=key, draft_schema=Draft.model_json_schema()))
    assert error.value.code == 'AI_KEY_REQUIRED' and calls == []


def main():
    """Run only after Main freeze/GO; retain each attempt in a fresh directory."""
    import argparse
    from datetime import datetime, timezone
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--scope', default='')
    args = parser.parse_args()
    args.output.resolve().relative_to(QA_ROOT.resolve())
    args.output.mkdir(parents=True, exist_ok=False)
    candidate = json.loads(args.candidate.read_text(encoding='utf-8-sig'))
    expected = candidate.get('source_sha256', candidate.get('source_hashes', {}))
    if not expected:
        raise ValueError('Candidate must contain nonempty source hash map')
    source_map = lambda: {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in expected}
    before = source_map()
    command = [sys.executable, '-m', 'pytest', 'tests/v5/test_blueprint_generation.py',
               'tests/v5/test_generation.py', 'tests/v5/test_prompt_fixed.py', '-q',
               '-p', 'no:cacheprovider', '--junitxml=' + str(args.output / 'junit.xml')]
    if args.scope:
        command.extend(['-k', args.scope])
    environment = os.environ.copy()
    environment.update(PYTHONUTF8='1', AI_PROVIDER='mock', GAMEPLAY_VERSION='v5',
                       SQLITE_PATH=str(args.output / 'isolated-import.sqlite'),
                       BLUEPRINT_QA_OUTPUT=str(args.output / 'observations'))
    environment.pop('V5_QA_OUTPUT', None)
    report = {'candidate': str(args.candidate), 'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
              'command': command, 'source_before': before, 'started_at': datetime.now(timezone.utc).isoformat(),
              'operator': 'independent QA agent', 'paid_calls': 0, 'real_network_calls': 0,
              'canonical_ledger_access': False, 'exit_code': None}
    try:
        assert before == expected, 'Candidate source mismatch before execution'
        process = subprocess.run(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=300)
        (args.output / 'output.txt').write_bytes(process.stdout)
        report['exit_code'] = process.returncode
    except subprocess.TimeoutExpired as error:
        (args.output / 'output.txt').write_bytes(error.stdout or b'')
        report.update(exit_code=124, error='QA test subprocess exceeded 300 seconds')
    except Exception as error:
        report.update(exit_code=1, error=str(error))
    report.update(source_after=source_map(), ended_at=datetime.now(timezone.utc).isoformat())
    report['source_unchanged'] = report['source_before'] == report['source_after']
    if not report['source_unchanged']:
        report['exit_code'] = 1
    (args.output / 'run.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'evidence': str(args.output), 'exit_code': report['exit_code']}))
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
