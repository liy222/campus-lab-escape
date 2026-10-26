"""NG2 finite synthetic policy checks; formal execution requires Main freeze.

The public bad sentence comes from the frozen policy examples, never a real
provider/private artifact. No claim of arbitrary-language semantic correctness.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess

import httpx
import pytest

from backend.app.ai.budget import BudgetLedger
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits
from backend.app.ai.v5 import GenerationService
from backend.app.domain import blueprints as v1
from backend.app.domain import generation_content_v2 as v2
from tests.v5.conftest import Actor, CANARY, private_game_hash, rid
from tests.v5.test_blueprint_generation import synthetic_content, synthetic_model_content
from tests.v5.test_generation import wire_body

ROOT = Path(__file__).resolve().parents[2]
EPOCH = ROOT / 'evidence/upgrade/v5.0/narrative-guard'
PLAN = json.loads((EPOCH / 'plan.json').read_text(encoding='utf-8'))
REJECT = tuple(PLAN['frozen_known_pairs']['reject'])
PRESERVE = tuple(PLAN['frozen_known_pairs']['preserve'])
assert len(REJECT) == 8 and len(PRESERVE) == 10
FIELDS = ('story', 'G1', 'G2', 'G3')


def observe(name, value):
    output = os.environ.get('NARRATIVE_GUARD_QA_OUTPUT')
    if output:
        folder = Path(output).resolve()
        folder.relative_to((EPOCH / 'qa').resolve())
        assert Path(name).name == name and name.endswith('.json')
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / name).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')


def valid_content(bp):
    """Only established QA-owned synthetic names/parameters, no real raw input."""
    result = synthetic_model_content(bp)
    result['story'] = '窗外下着小雨，校园活动室里保存着活动记录。'
    for room in result['rooms'].values():
        room['description'] = '窗边摆着旧桌椅，地面映着柔和的灯光。'
    return result


def put_field(value, field, text):
    if field == 'story':
        value['story'] = text
    else:
        value['rooms'][field]['description'] = text


def expected_with_ambient(base, field, text):
    result = copy.deepcopy(base)
    if field == 'story':
        result['story'] = text
    else:
        next(room for room in result['rooms'] if room['room_id'] == field)['description'] = text
    return result


PAIRS = [(True, index, text) for index, text in enumerate(REJECT, 1)] + [(False, index, text) for index, text in enumerate(PRESERVE, 1)]


@pytest.mark.parametrize('reject,index,text', PAIRS,
    ids=[f'reject-{index:02d}' for index in range(1, 9)] + [f'preserve-{index:02d}' for index in range(1, 11)])
def test_frozen_policy_pairs_each_story_and_each_room_field(monkeypatch, reject, index, text):
    bp = v2.select_blueprint(3, 'hard', seed=1)
    good = valid_content(bp)
    base = v2.assemble_draft(bp, good)
    helper = v1.assemble_draft
    calls = []
    def track(chosen, value):
        calls.append(True)
        return helper(chosen, value)
    monkeypatch.setattr(v1, 'assemble_draft', track)
    for field in FIELDS:
        raw = copy.deepcopy(good)
        put_field(raw, field, text)
        before = copy.deepcopy(raw)
        calls.clear()
        if reject:
            with pytest.raises(ValueError, match='^UNSUPPORTED_NARRATIVE_OPERATION$'):
                v2.assemble_draft(bp, raw)
            assert calls == []
        else:
            result = v2.assemble_draft(bp, raw)
            assert len(calls) == 1
            assert result == expected_with_ambient(base, field, text)
        assert raw == before
    observe(f'pair-{"reject" if reject else "preserve"}-{index:02d}.json', {
        'classification': 'reject' if reject else 'preserve', 'policy_example_index': index,
        'fields_checked': 4, 'raw_unchanged': True, 'helper_calls_per_input': 0 if reject else 1,
        'valid_params_structure_and_Host_text_unchanged_for_preserved_inputs': not reject,
        'synthetic_only_no_real_model_result': True})


@pytest.mark.parametrize('target', ['title', 'room-names', 'object-names'])
def test_excluded_name_fields_are_not_scanned(monkeypatch, target):
    bp = v2.select_blueprint(3, 'hard', seed=1)
    raw = valid_content(bp)
    v2.assemble_draft(bp, raw)
    phrase = '所有材料都要归位'
    if target == 'title':
        raw['title'] = phrase
    elif target == 'room-names':
        for room in raw['rooms'].values(): room['name'] = phrase
    else:
        for obj in raw['objects'].values(): obj['name'] = phrase
    before = copy.deepcopy(raw)
    result = v2.assemble_draft(bp, raw)
    assert raw == before and result['story'] == before['story']
    if target == 'title': assert result['title'] == phrase
    elif target == 'room-names': assert all(room['name'] == phrase for room in result['rooms'])
    else: assert all(obj['name'] == phrase for room in result['rooms'] for obj in room['objects'])
    observe(f'excluded-{target}.json', {'field_scope_preserved': True,
        'not_a_claim_that_names_are_semantically_safe': True})


@pytest.mark.parametrize('kind', ['item', 'clue'])
def test_actual_material_names_are_targets_after_rename(kind):
    bp = v2.select_blueprint(3, 'hard', seed=1)
    raw = valid_content(bp)
    obj = next(slot for slot in bp.objects if slot.kind == kind)
    raw['objects'][obj.object_id]['name'] = '校验通行卡'
    v2.assemble_draft(bp, raw)
    for field in ('story', 'G3'):
        bad = copy.deepcopy(raw)
        put_field(bad, field, '离楼前请把校验通行卡放回原处。')
        before = copy.deepcopy(bad)
        with pytest.raises(ValueError, match='^UNSUPPORTED_NARRATIVE_OPERATION$'):
            v2.assemble_draft(bp, bad)
        assert bad == before
    raw['story'] = '这里无需归还校验通行卡。'
    assert v2.assemble_draft(bp, raw)['story'] == raw['story']


@pytest.mark.parametrize('kind', ['item', 'clue'])
def test_material_name_regex_characters_are_literal(kind):
    bp = v2.select_blueprint(3, 'hard', seed=1)
    raw = valid_content(bp)
    target = next(slot for slot in bp.objects if slot.kind == kind)
    raw['objects'][target.object_id]['name'] = '甲乙[丙]+'
    v2.assemble_draft(bp, raw)
    raw['story'] = '请把甲乙[丙]+归还。'
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError, match='^UNSUPPORTED_NARRATIVE_OPERATION$'):
        v2.assemble_draft(bp, raw)
    assert raw == before
    # An unescaped regex would wrongly match this different, unknown target.
    raw['story'] = '请把甲乙丙归还。'
    assert v2.assemble_draft(bp, raw)['story'] == raw['story']


@pytest.mark.parametrize('kind', ['item', 'clue'])
def test_action_word_inside_material_name_does_not_hide_real_instruction(kind):
    bp = v2.select_blueprint(3, 'hard', seed=1)
    raw = valid_content(bp)
    target = next(slot for slot in bp.objects if slot.kind == kind)
    raw['objects'][target.object_id]['name'] = '归位卡'
    v2.assemble_draft(bp, raw)
    raw['story'] = '请把归位卡放回原处。'
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError, match='^UNSUPPORTED_NARRATIVE_OPERATION$'):
        v2.assemble_draft(bp, raw)
    assert raw == before
    raw['story'] = '请核对归位卡。'
    before = copy.deepcopy(raw)
    assert v2.assemble_draft(bp, raw)['story'] == raw['story'] and raw == before


@pytest.mark.parametrize('kind', ['item', 'clue'])
def test_instruction_like_alias_cannot_mask_scanned_prose_and_names_remain_unscanned(kind):
    bp = v2.select_blueprint(3, 'hard', seed=1)
    raw = valid_content(bp)
    target = next(slot for slot in bp.objects if slot.kind == kind)
    raw['objects'][target.object_id]['name'] = '所有材料都要归位'
    before = copy.deepcopy(raw)
    accepted = v2.assemble_draft(bp, raw)
    assert raw == before
    accepted_object = next(obj for room in accepted['rooms'] for obj in room['objects']
                           if obj['object_id'] == target.object_id)
    assert accepted_object['name'] == before['objects'][target.object_id]['name']
    for field in ('story', 'G2'):
        bad = copy.deepcopy(raw)
        put_field(bad, field, '所有材料都要归位。')
        before_bad = copy.deepcopy(bad)
        with pytest.raises(ValueError, match='^UNSUPPORTED_NARRATIVE_OPERATION$'):
            v2.assemble_draft(bp, bad)
        assert bad == before_bad
    raw['objects'][target.object_id]['name'] = '钥匙归位卡'
    raw['story'] = '请核对钥匙归位卡。'
    before = copy.deepcopy(raw)
    assert v2.assemble_draft(bp, raw)['story'] == raw['story'] and raw == before


@pytest.mark.parametrize('text', ['离楼前请\n把钥匙放回原处。', '请\n把材料归位。'],
                         ids=['linebreak-key-return', 'linebreak-material-return'])
def test_line_break_formatting_does_not_split_one_explicit_instruction(text):
    bp = v2.select_blueprint(3, 'hard', seed=1)
    good = valid_content(bp)
    v2.assemble_draft(bp, good)
    for field in FIELDS:
        raw = copy.deepcopy(good)
        put_field(raw, field, text)
        before = copy.deepcopy(raw)
        with pytest.raises(ValueError, match='^UNSUPPORTED_NARRATIVE_OPERATION$'):
            v2.assemble_draft(bp, raw)
        assert raw == before


def test_matching_normalization_never_rewrites_preserved_prose():
    bp = v2.select_blueprint(3, 'hard', seed=1)
    raw = valid_content(bp)
    raw['story'] = '　旧牌上写着ＡＢＣ，\n窗外下着小雨。'
    raw['rooms']['G2']['description'] = '旧纸盒标为ＤＥＦ，\n墙边映着灯光。'
    before = copy.deepcopy(raw)
    result = v2.assemble_draft(bp, raw)
    assert raw == before and result['story'] == before['story']
    assert next(room for room in result['rooms'] if room['room_id'] == 'G2')['description'] == before['rooms']['G2']['description']


def test_whitespace_material_names_do_not_create_empty_regex_targets():
    bp = v2.select_blueprint(3, 'hard', seed=1)
    raw = valid_content(bp)
    for obj in bp.objects:
        if obj.kind in {'item', 'clue'}:
            raw['objects'][obj.object_id]['name'] = ' \t\u3000'
    # Current schema permits nonempty whitespace strings; this is not a name
    # quality claim or permission to relax the existing empty-name boundary.
    assert v1._IntegerValidator(v2.content_schema(bp)).is_valid(raw)
    raw['story'] = '请把摆钟归位。'  # Unknown nonmaterial target, outside this finite subset.
    before = copy.deepcopy(raw)
    assert v2.assemble_draft(bp, raw)['story'] == raw['story'] and raw == before
    raw['story'] = '请把材料归位。'
    with pytest.raises(ValueError, match='^UNSUPPORTED_NARRATIVE_OPERATION$'):
        v2.assemble_draft(bp, raw)


@pytest.mark.parametrize('kind,error', [('duplicate', 'DUPLICATE_KEY'), ('raw-size', 'OUTPUT_SIZE'),
    ('unsafe', 'UNSAFE_TEXT'), ('extra-description', 'GENERATION_CONTENT_INVALID'),
    ('missing-object', 'GENERATION_CONTENT_INVALID'), ('typed-bool', 'GENERATION_CONTENT_INVALID'),
    ('empty-name', 'GENERATION_CONTENT_INVALID')])
def test_original_strict_json_schema_precede_narrative_guard(monkeypatch, kind, error):
    bp = v2.select_blueprint(3, 'hard', seed=0)
    valid = valid_content(bp)
    v2.assemble_draft(bp, valid)
    value = copy.deepcopy(valid)
    value['story'] = REJECT[0]
    if kind == 'duplicate': raw = '{"story":"x","story":"y"}'
    elif kind == 'raw-size': raw = ' ' * 65537
    elif kind == 'unsafe':
        value['story'] = '<script> ' + REJECT[0]; raw = json.dumps(value)
    else:
        if kind == 'extra-description': value['objects']['obj_key']['description'] = '额外字段'
        if kind == 'missing-object': del value['objects']['obj_key']
        if kind == 'typed-bool': value['parameters']['positions'][0] = True
        if kind == 'empty-name': value['objects']['obj_key']['name'] = ''
        raw = json.dumps(value)
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        pytest.fail('Bad raw/schema input reached narrative guard or Host helper')
    monkeypatch.setattr(v2, '_guard_narrative', forbidden)
    monkeypatch.setattr(v1, 'assemble_draft', forbidden)
    with pytest.raises(ValueError, match='^' + error + '$'):
        v2.assemble_draft(bp, raw)
    assert calls == []


def test_revision_policy_and_frozen_existing_source_boundaries():
    assert v2.NARRATIVE_GUARD_REVISION == PLAN['policy_revision'].split(';', 1)[0] == '1'
    baseline = subprocess.run(['git', 'show', PLAN['baseline_head'] + ':backend/app/domain/generation_content_v2.py'],
                              capture_output=True, check=True).stdout.decode('utf-8-sig')
    before = ast.parse(baseline)
    after = ast.parse((ROOT / 'backend/app/domain/generation_content_v2.py').read_text('utf-8-sig'))
    for name in ('select_blueprint', 'content_schema', 'request_manifest', '_describe'):
        old = next(node for node in before.body if isinstance(node, ast.FunctionDef) and node.name == name)
        new = next(node for node in after.body if isinstance(node, ast.FunctionDef) and node.name == name)
        assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False)
    sources = json.loads((ROOT / PLAN['baseline_source_map']).read_text('utf-8'))['source']
    allowed = set(PLAN['allowed_product_source_deltas'])
    for name, value in sources.items():
        if name not in allowed:
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value, name
    observe('scope.json', {'policy_revision': '1', 'frozen_examples': [8, 10],
        'four_unchanged_v2_function_ASTs': True, 'other_prior_source_entries_unchanged': len(sources) - len(allowed),
        'old_source_map_is_historical_not_current_whole_bundle': True})


def test_one_production_mock_send_rejected_worker_publishes_no_level(tmp_path, monkeypatch):
    from backend.app.main import create_v5_app
    from backend.app.api import v5 as api_v5
    bp = v2.select_blueprint(3, 'hard', seed=1)
    raw = valid_content(bp)
    v2.assemble_draft(bp, raw)
    raw['story'] = REJECT[0]
    selected = []
    def choose(*args, **kwargs):
        selected.append(True); return bp
    monkeypatch.setattr(v2, 'select_blueprint', choose)
    def forbidden(*args, **kwargs):
        pytest.fail('Rejected narrative reached helper/compiler')
    monkeypatch.setattr(v1, 'assemble_draft', forbidden)
    monkeypatch.setattr(api_v5, 'compile_level', forbidden)
    sends = []
    ledger = BudgetLedger(tmp_path / 'synthetic-narrative-budget.sqlite')
    def handler(request):
        sends.append(request)
        assert request.headers['authorization'] == 'Bearer ' + CANARY
        assert CANARY.encode() not in request.content
        body = json.loads(request.content)
        assert body['max_tokens'] == 6000 and body['response_format'] == {'type': 'json_object'}
        assert not {'tools', 'tool_choice'} & body.keys()
        return httpx.Response(200, json=wire_body(json.dumps(raw, ensure_ascii=False)))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    service = GenerationService(lambda key: provider)
    app = create_v5_app(tmp_path / 'synthetic-game-v5.sqlite', generation_service=service)
    actor = Actor(app).authenticate('narrative_owner')
    response = actor.post('/level-generations', {'request_id': rid(), 'theme': '合成校园 ' + CANARY,
        'room_count': 3, 'difficulty': 'hard'}, headers={'X-AI-Api-Key': CANARY})
    assert response.status_code == 202
    job = actor.get('/level-generations/' + response.json()['data']['job']['job_id']).json()['data']['job']
    assert job['status'] == 'rejected' and job['error_code'] == 'MODEL_INVALID_OUTPUT' and job['level_id'] is None
    assert actor.get('/levels').json()['data']['levels'] == []
    assert len(sends) == len(selected) == 1 and ledger.snapshot()['calls'] == 1
    assert GenerationLimits().max_cost_units == 200000000 and GenerationLimits().timeout_seconds == 60
    for path in (app.state.v5_database.path, ledger.path):
        with sqlite3.connect(path) as connection: assert CANARY not in '\n'.join(connection.iterdump())
    observe('production-rejection.json', {'synthetic_model_sends': 1, 'Host_selections': 1,
        'worker_status': 'rejected', 'error_code': 'MODEL_INVALID_OUTPUT', 'published_levels': 0,
        'helper_or_compile_after_rejection': False, 'real_paid_calls': 0})


def test_old_full_definition_archive_ignores_new_generation_guard(actor, system, monkeypatch):
    from backend.app.main import create_v5_app
    app, generator = system
    bp = v1.select_blueprint(1, 'easy', seed=0)
    old = v1.assemble_draft(bp, synthetic_content(bp))
    old['story'] = REJECT[0]
    generator.output = old  # Explicit historical-format QA setup, no model/v2 fallback.
    job = actor.generate(1, 'easy')
    state = actor.session('generated', job['level_id']); sid = state['session_id']
    db = app.state.v5_database
    principal = db.authenticate(actor.client.cookies.get('campus_v5_session'))
    fields = db.owned(principal, sid).rules.game_fields
    before_hash = private_game_hash(db, sid, fields)
    before_definition_hash = state['definition_hash']
    saved = actor.post(f'/sessions/{sid}/saves', actor.versioned(state, name='旧定义不重审'))
    assert saved.status_code == 201
    save_id = saved.json()['data']['slot']['save_id']
    with db.transaction() as connection:
        old_bytes = connection.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0]
        assert json.loads(old_bytes)['draft']['story'] == REJECT[0]
    def forbidden(*args, **kwargs):
        pytest.fail('Restore/reload reprocessed old complete definition with current generation guard')
    monkeypatch.setattr(v2, '_guard_narrative', forbidden)
    monkeypatch.setattr(v2, 'assemble_draft', forbidden)
    monkeypatch.setattr(v2, 'select_blueprint', forbidden)
    reopened = create_v5_app(db.path, generation_service=GenerationService(forbidden))
    owner = Actor(reopened).authenticate('qa_alpha', False)
    current = owner.state(sid)
    restored = owner.post(f'/sessions/{sid}/saves/{save_id}/restore', owner.versioned(current))
    assert restored.status_code == 200
    restored_state = restored.json()['data']['visible_state']
    assert restored_state['definition_hash'] == before_definition_hash
    assert private_game_hash(reopened.state.v5_database, sid, fields) == before_hash
    with db.transaction() as connection:
        assert connection.execute('SELECT definition_json FROM generated_levels WHERE level_id=?', (job['level_id'],)).fetchone()[0] == old_bytes
    assert len(generator.calls) == 1
    observe('old-definition.json', {'setup': 'explicit synthetic old full Draft containing known rejected story',
        'old_definition_hash': before_definition_hash, 'old_bytes_state_preserved': True,
        'no_new_guard_or_model_on_restore_reload': True, 'not_a_story_quality_pass': True})
