"""Narrow prompt-repair checks; examples and provider replies are synthetic.

No real model-quality claim, network connection or canonical budget access.
"""
import asyncio
import copy
import hashlib
import json

import httpx
import pytest
from jsonschema import Draft202012Validator

from backend.app.ai.budget import BudgetLedger, cost_units
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits
from backend.app.ai.v5 import GenerationService, ServiceError
from backend.app.domain.generated import Draft, GeneratedRules, compile_level
from .conftest import CANARY, observed_output


def without_annotation_titles(schema):
    """Ignore schema labels while preserving data property/definition names."""
    if isinstance(schema, list):
        return [without_annotation_titles(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    result = {}
    for key, value in schema.items():
        if key == 'title':
            continue
        if key in {'properties', '$defs', 'patternProperties', 'dependentSchemas'}:
            result[key] = {name: without_annotation_titles(child) for name, child in value.items()}
        else:
            result[key] = without_annotation_titles(value)
    return result


# Accepted plan: rooms + easy1/normal2/hard3, cap6; normal1/hard2 combinations,
# hard dependency depth3. Explicit cases avoid deriving expectations from product.
@pytest.mark.parametrize('rooms,difficulty,puzzles,combos,depth', [
    (1, 'easy', 2, 0, 1), (1, 'normal', 3, 1, 1), (1, 'hard', 4, 2, 3),
    (2, 'easy', 3, 0, 1), (2, 'normal', 4, 1, 1), (2, 'hard', 5, 2, 3),
    (3, 'easy', 4, 0, 1), (3, 'normal', 5, 1, 1), (3, 'hard', 6, 2, 3),
])
def test_numeric_requirements_requested_example_and_schema_preserved(rooms, difficulty, puzzles, combos, depth):
    schema = Draft.model_json_schema()
    original = copy.deepcopy(schema)
    messages = GenerationService.messages(theme='独立合成校园主题', room_count=rooms,
        difficulty=difficulty, draft_schema=schema)
    assert schema == original, 'Caller-owned schema was mutated'
    assert [message['role'] for message in messages] == ['system', 'user']
    value = json.loads(messages[1]['content'])
    assert value['room_count'] == rooms and value['difficulty'] == difficulty
    assert value['requirements'] == {'room_count': rooms, 'puzzle_count': puzzles,
        'minimum_two_material_puzzles': combos, 'minimum_dependency_depth': depth}
    assert all(type(number) is int for number in value['requirements'].values())
    emitted = value['schema']
    assert without_annotation_titles(emitted) == without_annotation_titles(original)
    assert 'title' in emitted['properties'] and 'title' in emitted['required']
    Draft202012Validator.check_schema(emitted)
    example = value['shape_example_only']
    Draft202012Validator(original).validate(example)
    Draft202012Validator(emitted).validate(example)
    assert len(example['rooms']) == rooms and len(example['puzzles']) == puzzles
    compiled = compile_level(example, rooms, difficulty)
    rules = GeneratedRules(compiled)
    state = rules.initial_state()
    for action in compiled.witness:
        state, _ = rules.apply_action(state, action['tool'], action['arguments'])
    assert compiled.witness and state.status == 'won'
    observed_output(f'prompt-{rooms}-{difficulty}.json', {'room_count': rooms,
        'difficulty': difficulty, 'requirements': value['requirements'],
        'caller_schema_unchanged': schema == original,
        'schema_semantics_preserved': True, 'synthetic_example_replay_won': True,
        'witness_steps': len(compiled.witness), 'definition_hash': compiled.definition_hash,
        'payload_sha256': hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode()).hexdigest(),
        'real_model_calls': 0})


def test_maximum_four_byte_unicode_theme_rejected_before_reservation_or_send(tmp_path):
    # The API accepts up to 2000 Unicode characters. Four UTF-8 bytes per
    # character must be accounted for by the actual provider's whole payload.
    theme = '\U0001f9ea' * 2000
    assert len(theme) == 2000 and len(theme.encode('utf-8')) == 8000
    messages = GenerationService.messages(theme=theme, room_count=3,
        difficulty='hard', draft_schema=Draft.model_json_schema())
    limits = GenerationLimits()
    payload = {'model': 'deepseek-flash', 'messages': messages,
        'max_tokens': limits.max_tokens, 'thinking': {'type': 'disabled'}, 'stream': False,
        'response_format': {'type': 'json_object'}}
    full_size = len(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode())
    input_bound = full_size * 4 + 8192
    bound = cost_units(input_bound, limits.max_tokens)
    assert input_bound < 1_000_000 and bound > 200_000_000
    assert limits.max_cost_units == 200_000_000
    ledger = BudgetLedger(tmp_path / 'synthetic-prompt-budget.sqlite')
    initial = ledger.snapshot()
    sends = []

    def handler(request):
        sends.append(request)
        raise AssertionError('Over-cap payload reached the synthetic HTTP transport')

    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    service = GenerationService(lambda key: provider)
    with pytest.raises(ServiceError) as error:
        asyncio.run(service.generate(theme=theme, room_count=3, difficulty='hard',
            api_key=CANARY, draft_schema=Draft.model_json_schema()))
    assert error.value.code == 'AI_LIMIT_REACHED'
    assert sends == [] and ledger.snapshot() == initial and initial['calls'] == 0
    assert provider.last_response_metadata is None
    observed_output('prompt-unicode-cap.json', {'theme_characters': len(theme),
        'theme_utf8_bytes': len(theme.encode()), 'whole_payload_bytes': full_size,
        'upper_cost_units': bound, 'cap_units': limits.max_cost_units,
        'rejection': error.value.code, 'transport_sends': len(sends),
        'synthetic_ledger_calls_before_after': [initial['calls'], ledger.snapshot()['calls']],
        'real_model_calls': 0})
