"""Focused synthetic checks for finite puzzle-name guidance and diagnostics."""
import asyncio
import copy
import json
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest

from backend.app.ai.budget import BudgetLedger
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
from backend.app.ai.v5 import GenerationService, ServiceError
from backend.app.domain import blueprints as v1
from backend.app.domain import generation_content_v2 as content
from backend.app.domain import puzzle_purpose as purpose
from backend.app.domain.generation_observability import NAME_REASONS, REASONS
from backend.app.domain.generated import compile_level
from pathlib import Path
from tests.v5.conftest import CANARY
from tests.v5.test_blueprint_generation import SHAPES, synthetic_content, synthetic_model_content
from tests.v5.test_generation import wire_body


def _valid_names(bp, raw):
    effects = purpose.puzzle_effects(bp)
    for obj in bp.objects:
        if obj.kind != 'puzzle':
            continue
        requirement = purpose.name_requirements(effects[obj.object_id])
        access = '门禁甲' if requirement['require_access_word'] else '主题甲'
        raw['objects'][obj.object_id]['name'] = access + requirement['allowed_suffixes'][0]
    return effects


def _mechanics_only(draft):
    result = copy.deepcopy(draft)
    for room in result['rooms']:
        for obj in room['objects']:
            obj.pop('description', None)
    return result


@pytest.mark.parametrize('rooms,difficulty,count,combos,depth', SHAPES)
@pytest.mark.parametrize('seed', [0, 1, 2, 3])
def test_manifest_name_guidance_covers_supported_puzzle_slots_and_validator_vocabulary(
        rooms, difficulty, count, combos, depth, seed):
    bp = content.select_blueprint(rooms, difficulty, seed=seed)
    manifest = content.request_manifest(bp)
    expected = {obj.object_id: obj for obj in bp.objects if obj.kind == 'puzzle'}
    assert len(manifest['puzzles']) == len(expected)
    by_slot = {row['object_slot']: row for row in manifest['puzzles']}
    assert set(by_slot) == set(expected)
    effects = purpose.puzzle_effects(bp)
    for object_id, obj in expected.items():
        row = by_slot[object_id]
        requirements = row['name_requirements']
        assert row['effect'] == effects[object_id]
        assert requirements == purpose.name_requirements(effects[object_id])
        assert requirements['allowed_suffixes'] == list(purpose._HEADS[obj.art_id])
        assert requirements['allowed_access_words'] == list(purpose._ACCESS_WORDS)
        assert requirements['must_end_with'] is True
        assert requirements['require_access_word'] == (effects[object_id]['purpose'] == 'passage_control')
        assert requirements['examples']


@pytest.mark.parametrize('rooms,difficulty,seed', [(1, 'easy', 0), (2, 'normal', 1), (3, 'hard', 3)])
def test_legal_names_are_admitted_without_changing_mechanics(rooms, difficulty, seed):
    bp = content.select_blueprint(rooms, difficulty, seed=seed)
    raw = synthetic_model_content(bp)
    effects = _valid_names(bp, raw)
    content.validate_puzzle_names(bp, {key: row['name'] for key, row in raw['objects'].items()
                                        if key in effects}, effects)
    original = copy.deepcopy(raw)
    accepted = content.assemble_draft(bp, json.dumps(raw, ensure_ascii=False))
    legacy_bp = replace(bp, content_version=v1.CONTENT_VERSION)
    old = synthetic_content(legacy_bp)
    old.update(title=raw['title'], story=raw['story'], rooms=copy.deepcopy(raw['rooms']))
    for object_id, row in raw['objects'].items():
        old['objects'][object_id]['name'] = row['name']
    baseline = v1.assemble_draft(legacy_bp, old)
    assert _mechanics_only(accepted) == _mechanics_only(baseline)
    assert raw == original
    compiled = compile_level(accepted, rooms, difficulty)
    assert compiled.witness


@pytest.mark.parametrize('reason,bad_name', [
    ('name_suffix', '私有合成名称-PRIVATE-7dd'),
    ('name_suffix', '私有合成名称-PRIVATE-7dd'),
    ('name_access', '校验甲终端'),
    ('name_container', '门禁储物柜锁'),
])
def test_invalid_names_have_exact_private_safe_diagnostic(reason, bad_name):
    bp = content.select_blueprint(1, 'easy', seed=0)
    raw = synthetic_model_content(bp)
    effects = _valid_names(bp, raw)
    target_id = next(object_id for object_id, effect in effects.items()
                     if effect['purpose'] == 'passage_control')
    target_obj = next(obj for obj in bp.objects if obj.object_id == target_id)
    if reason == 'name_access':
        bad_name = '校验甲' + purpose._HEADS[target_obj.art_id][0]
    raw['objects'][target_id]['name'] = bad_name
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError) as error:
        content.assemble_draft(bp, json.dumps(raw, ensure_ascii=False))
    assert str(error.value) == 'GENERATION_PUZZLE_NAME_INVALID'
    assert error.value.generation_diagnostic == reason
    assert bad_name not in str(error.value)
    assert raw == before
    assert reason in NAME_REASONS and reason in REASONS


def test_prompt_carries_name_constraints_without_return_requirement():
    bp = content.select_blueprint(3, 'hard', seed=0)
    messages = GenerationService.messages(theme='隔离合成主题', room_count=3, difficulty='hard', blueprint=bp)
    prompt = messages[0]['content']
    payload = json.loads(messages[1]['content'])
    assert 'must_end_with=true' in prompt or 'must_end_with=true' in prompt.replace(' ', '')
    assert 'allowed_suffixes' in prompt and 'require_access_word=true' in prompt
    assert '不得要求玩家归位、归还或放回' in prompt
    assert 'name_requirements' in payload['blueprint']['puzzles'][0]
    assert all(row['name_requirements']['allowed_suffixes'] for row in payload['blueprint']['puzzles'])
    assert all('name_requirements' in row for row in payload['blueprint']['puzzles'])


def test_narrative_guard_still_rejects_return_requirement():
    bp = content.select_blueprint(1, 'easy', seed=0)
    raw = synthetic_model_content(bp)
    _valid_names(bp, raw)
    raw['story'] = '离开前必须归还所有资料。'
    with pytest.raises(ValueError, match='^UNSUPPORTED_NARRATIVE_OPERATION$') as error:
        content.assemble_draft(bp, json.dumps(raw, ensure_ascii=False))
    assert error.value.generation_diagnostic == 'narrative'


def test_mocktransport_name_rejection_is_safe_and_never_retried(tmp_path, monkeypatch):
    bp = content.select_blueprint(1, 'easy', seed=0)
    raw = synthetic_model_content(bp)
    effects = _valid_names(bp, raw)
    target_id = next(object_id for object_id, effect in effects.items()
                     if effect['purpose'] == 'passage_control')
    target_obj = next(obj for obj in bp.objects if obj.object_id == target_id)
    private_name = 'SYNTHETIC_PRIVATE_INVALID_NAME_82ac'
    raw['objects'][target_id]['name'] = private_name
    monkeypatch.setattr(content, 'select_blueprint', lambda *args, **kwargs: bp)
    requests = []

    def handler(request):
        requests.append(request)
        assert CANARY.encode() not in request.content
        return httpx.Response(200, json=wire_body(json.dumps(raw, ensure_ascii=False)))

    ledger = BudgetLedger(tmp_path / 'synthetic-name-diagnostic-ledger.sqlite')
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    with pytest.raises(ServiceError) as error:
        asyncio.run(GenerationService(lambda key: provider).generate(
            theme='主题', room_count=1, difficulty='easy', api_key=CANARY, draft_schema={}))
    assert error.value.code == 'MODEL_INVALID_OUTPUT'
    assert error.value.generation_diagnostic == 'name_suffix'
    assert private_name not in str(error.value)
    assert len(requests) == ledger.snapshot()['calls'] == 1


def test_finite_reliability_runner_rejects_invalid_approval_before_sensitive_access(tmp_path, monkeypatch):
    import asyncio
    import scripts.generation_reliability as runner
    from backend.app.ai import budget, provider

    stage = tmp_path / 'isolated-stage'
    preview_dir = stage / 'automated' / 'preflight-test'
    preview_dir.mkdir(parents=True)
    preview_path = preview_dir / 'preview.json'
    approval_path = preview_dir / 'approval.json'
    preview_path.write_text(json.dumps({'offline_test_only': True}), encoding='utf-8')
    preview_digest = runner.sha(preview_path.read_bytes())
    monkeypatch.setattr(runner, 'STAGE', stage)

    sensitive_calls = {'credentials': 0, 'ledger': 0, 'source_map': 0, 'payloads': 0}
    def forbidden_credentials(*args, **kwargs):
        sensitive_calls['credentials'] += 1
        pytest.fail('Invalid approval reached credential loading')
    def forbidden_ledger(*args, **kwargs):
        sensitive_calls['ledger'] += 1
        pytest.fail('Invalid approval reached real ledger construction')
    def forbidden_source_map(*args, **kwargs):
        sensitive_calls['source_map'] += 1
        pytest.fail('Invalid approval scanned current production source map')
    def forbidden_payloads(*args, **kwargs):
        sensitive_calls['payloads'] += 1
        pytest.fail('Invalid approval prepared runtime payloads')

    monkeypatch.setattr(provider.DeepSeekConfig, 'from_environment', forbidden_credentials)
    monkeypatch.setattr(budget, 'BudgetLedger', forbidden_ledger)
    monkeypatch.setattr(runner, 'source_map', forbidden_source_map)
    monkeypatch.setattr(runner, 'cases_and_payloads', forbidden_payloads)

    valid_fields = {'approved': True, 'preview_sha256': preview_digest,
        'max_calls': runner.MAX_CALLS, 'max_total_units': runner.MAX_TOTAL_UNITS,
        'actual_user_approval_reference': 'synthetic-invalid-approval-test'}
    invalid_approvals = [
        {'approved': False, **{k: v for k, v in valid_fields.items() if k != 'approved'}},
        {**valid_fields, 'preview_sha256': '0' * 64},
        {**valid_fields, 'max_calls': runner.MAX_CALLS - 1},
        {**valid_fields, 'max_total_units': runner.MAX_TOTAL_UNITS - 1},
    ]
    marker = preview_dir / 'execute-started.json'
    for approval in invalid_approvals:
        approval_path.write_text(json.dumps(approval), encoding='utf-8')
        with pytest.raises(ValueError, match='^APPROVAL_OR_PREVIEW_MISMATCH$'):
            asyncio.run(runner.execute(preview_path, approval_path))
        assert not marker.exists()
        assert list((stage / 'automated').glob('real-*')) == []
    assert sensitive_calls == {'credentials': 0, 'ledger': 0, 'source_map': 0, 'payloads': 0}
