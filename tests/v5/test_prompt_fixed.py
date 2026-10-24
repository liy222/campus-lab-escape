"""Prompt checks for accepted Host-structure/AI-content contract v1.0.0.

Supersedes only complete-Draft example expectations of the earlier prompt source
epoch. Its sealed reports remain historical. Key, whole-payload budget, exact
schema, numeric requirements and one-call guarantees remain asserted.
No real model-quality claim, network connection or canonical ledger access.
"""
import asyncio
import copy
import hashlib
import json

import httpx
import pytest
from jsonschema import Draft202012Validator

from backend.app.ai.budget import BudgetLedger, cost_units
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits, ProviderError
from backend.app.ai.v5 import GenerationService, ServiceError
from backend.app.domain import blueprints
from backend.app.domain.generated import Draft
from .conftest import CANARY
from .test_generation import wire_body
from .test_blueprint_generation import SHAPES, content_for_messages, observation, synthetic_content


@pytest.mark.parametrize('rooms,difficulty,puzzles,combos,depth', SHAPES)
def test_numeric_requirements_selected_content_schema_and_compatibility_argument_preserved(rooms, difficulty, puzzles, combos, depth):
    legacy_schema = Draft.model_json_schema()
    original = copy.deepcopy(legacy_schema)
    for seed in (0, 1):
        blueprint = blueprints.select_blueprint(rooms, difficulty, seed=seed)
        messages = GenerationService.messages(theme='独立合成校园主题', room_count=rooms,
            difficulty=difficulty, draft_schema=legacy_schema, blueprint=blueprint)
        assert legacy_schema == original, 'Caller-owned legacy Draft schema was mutated'
        assert [message['role'] for message in messages] == ['system', 'user']
        value = json.loads(messages[1]['content'])
        assert set(value) == {'theme', 'room_count', 'difficulty', 'requirements', 'blueprint', 'schema'}
        assert value['room_count'] == rooms and value['difficulty'] == difficulty
        assert value['requirements'] == {'room_count': rooms, 'puzzle_count': puzzles,
            'minimum_two_material_puzzles': combos, 'minimum_dependency_depth': depth}
        assert all(type(number) is int for number in value['requirements'].values())
        assert value['schema'] == blueprints.content_schema(blueprint)
        assert value['blueprint'] == blueprints.request_manifest(blueprint)
        assert value['schema'] != original and 'shape_example_only' not in value
        assert 'title' in value['schema']['properties'] and 'title' in value['schema']['required']
        Draft202012Validator.check_schema(value['schema'])
        Draft202012Validator(value['schema']).validate(synthetic_content(blueprint))
        assert not {'answers', 'witness', 'definition_hash'} & value['blueprint'].keys()
        observation(f'prompt-{blueprint.family}-{rooms}-{difficulty}.json', {
            'requirements': value['requirements'], 'caller_schema_unchanged': True,
            'model_contract': 'Host blueprint content v1.0.0', 'selected_blueprint': blueprint.blueprint_id,
            'payload_sha256': hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode()).hexdigest(),
            'supersedes': 'complete-LevelDraft example/schema expectations only; old evidence unchanged',
            'real_model_calls': 0})


@pytest.mark.parametrize('seed', [0, 1])
def test_four_byte_unicode_theme_whole_payload_budget_is_measured_without_raising_cap(tmp_path, monkeypatch, seed):
    theme = '\U0001f9ea' * 2000
    assert len(theme) == 2000 and len(theme.encode('utf-8')) == 8000
    selected = blueprints.select_blueprint(3, 'hard', seed=seed)
    monkeypatch.setattr(blueprints, 'select_blueprint', lambda *args, **kwargs: selected)
    messages = GenerationService.messages(theme=theme, room_count=3, difficulty='hard', blueprint=selected)
    limits = GenerationLimits()
    payload = {'model': 'deepseek-flash', 'messages': messages, 'max_tokens': limits.max_tokens,
        'thinking': {'type': 'disabled'}, 'stream': False, 'response_format': {'type': 'json_object'}}
    full_size = len(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode())
    input_bound = full_size * 4 + 8192
    bound = cost_units(input_bound, limits.max_tokens)
    assert limits.max_cost_units == 200_000_000 and limits.max_tokens == 6000
    ledger = BudgetLedger(tmp_path / 'synthetic-prompt-budget.sqlite')
    initial = ledger.snapshot(); sends = []
    def handler(request):
        sends.append(request)
        assert CANARY.encode() not in request.content
        return httpx.Response(200, json=wire_body(json.dumps(content_for_messages(json.loads(request.content)['messages']))))
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    service = GenerationService(lambda key: provider)
    if bound > limits.max_cost_units or input_bound > 1_000_000:
        with pytest.raises(ServiceError) as error:
            asyncio.run(service.generate(theme=theme, room_count=3, difficulty='hard', api_key=CANARY, draft_schema=Draft.model_json_schema()))
        assert error.value.code == 'AI_LIMIT_REACHED'
        assert sends == [] and ledger.snapshot() == initial and provider.last_response_metadata is None
        result = 'rejected before reserve/send'
    else:
        result = asyncio.run(service.generate(theme=theme, room_count=3, difficulty='hard', api_key=CANARY, draft_schema=Draft.model_json_schema()))
        Draft.model_validate(result)
        assert len(sends) == 1 and ledger.snapshot()['calls'] == 1
        assert len(sends[0].content) == full_size
        result = 'legal input sent exactly once through synthetic transport'
    observation(f'prompt-unicode-budget-{selected.family}.json', {
        'theme_characters': len(theme), 'theme_utf8_bytes': len(theme.encode()),
        'whole_payload_bytes': full_size, 'input_bound': input_bound, 'upper_cost_units': bound,
        'cap_units': limits.max_cost_units, 'result': result, 'transport_sends': len(sends),
        'synthetic_ledger_calls_before_after': [initial['calls'], ledger.snapshot()['calls']], 'paid_calls': 0})


def test_actual_over_cap_payload_is_refused_before_provider_reservation_or_send(tmp_path):
    # Deliberately beyond API theme max: this checks unchanged provider accounting.
    messages = [{'role': 'system', 'content': 'Only json.'}, {'role': 'user', 'content': '界' * 6500}]
    limits = GenerationLimits()
    payload = {'model': 'deepseek-flash', 'messages': messages, 'max_tokens': 6000,
        'thinking': {'type': 'disabled'}, 'stream': False, 'response_format': {'type': 'json_object'}}
    full_size = len(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode())
    bound = cost_units(full_size * 4 + 8192, 6000)
    assert full_size * 4 + 8192 < 1_000_000 and bound > 200_000_000
    ledger = BudgetLedger(tmp_path / 'synthetic-over-cap-budget.sqlite')
    initial = ledger.snapshot(); sends = []
    def handler(request):
        sends.append(request)
        raise AssertionError('Over-cap payload reached transport')
    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError) as error:
        asyncio.run(provider.complete(messages, [], limits, scope='v5_generation', tool_choice='none'))
    assert error.value.code == 'AI_LIMIT_REACHED'
    assert sends == [] and ledger.snapshot() == initial and provider.last_response_metadata is None
    observation('prompt-actual-over-cap.json', {'whole_payload_bytes': full_size, 'upper_cost_units': bound,
        'cap_units': 200_000_000, 'rejection': error.value.code, 'transport_sends': 0,
        'reservation_delta': 0, 'scope': 'provider boundary; theme intentionally outside API max', 'paid_calls': 0})
