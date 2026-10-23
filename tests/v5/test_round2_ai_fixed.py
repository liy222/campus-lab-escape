"""AI-only repair checks. Real captures stay immutable; all replies sent by
MockTransport here are explicitly synthetic, with an isolated fake ledger.
"""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import re
import sqlite3

import httpx
import pytest

from backend.app.ai.budget import BudgetLedger, cost_units
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider
from backend.app.ai.v5 import CompanionService, public_context, validate_reply
from .conftest import CANARY, observed_output
from .test_generation import wire_body

CAPTURES = Path(__file__).resolve().parents[2] / 'evidence/upgrade/v5.0/real-samples-round2'
INPUT_HASHES = {
    'companion-actual-stage.json': '52a86785516d2c14a5df96996cdf28c4a13b6e05fe41a9d7287aff8357db579b',
    'A1-exact-payload.json': '3590994aaf6a1480433dfcfaad887826eb9f282f2d11000a4a4976a11eb7e28d',
    'A1-provider-result.json': '31c67b4d4d4b2825cb9a92a9ce1cf55c4907b990bbd8c9ab7107ec83e9f47a16',
}


def capture(name):
    raw = (CAPTURES / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == INPUT_HASHES[name]
    return json.loads(raw)


def stage_and_question():
    state = capture('companion-actual-stage.json')['visible_state']
    prior_context = json.loads(capture('A1-exact-payload.json')['payload']['messages'][-1]['content'])
    return state, prior_context


def recorded_actions(prior_context):
    # Reconstruct only these recorded public operation labels, not private event
    # data. The canary argument is synthetic and must never enter model context.
    operations = {'点击查看': 'inspect', '拿取': 'take', '使用背包物件': 'use_item',
                  '通过通路': 'move', '操作装置': 'interact'}
    history = prior_context['recent_history']
    assert len(history) == 3 and all(entry['kind'] == 'action' for entry in history)
    return [{'kind': 'action', 'tool': operations[entry['operation']],
             'arguments': {'synthetic_private_argument': CANARY}} for entry in history]


class GuardedPublicState(dict):
    private_keys = {'definition', 'draft', 'answers', 'hidden_name_map', 'private_storage'}

    def get(self, key, default=None):
        assert key not in self.private_keys, 'Projection queried a private field'
        return super().get(key, default)

    def __getitem__(self, key):
        assert key not in self.private_keys, 'Projection queried a private field'
        return super().__getitem__(key)


def test_real_public_stage_natural_labels_refs_facts_and_nonmutation():
    state, prior = stage_and_question()
    before = copy.deepcopy(state)
    guarded = GuardedPublicState(state)
    guarded.update({key: CANARY for key in guarded.private_keys})
    context = public_context(guarded, prior['question'], recorded_actions(prior))
    names = {obj['object_id']: obj['name'] for obj in state['objects']}
    assert context['allowed_clue_refs'] == [clue['clue_id'] for clue in state['clues']]
    for clue, projected in zip(state['clues'], context['known_evidence']):
        assert projected['clue_id'] == clue['clue_id'] and projected['text'] == clue['text']
        assert names[clue['object_id']] in projected['title']
        assert clue['clue_id'] not in projected['title']
    descriptions = ' '.join(obj['description'] for obj in context['visible_objects'])
    for evidence in context['known_evidence']:
        assert evidence['title'] in descriptions
        assert '资料 ' + evidence['clue_id'] not in descriptions
    assert context['recent_history'] == prior['recent_history']
    assert CANARY not in json.dumps(context, ensure_ascii=False)
    assert state == before
    observed_output('round2-public-projection.json', {'input_sha256': INPUT_HASHES,
        'public_refs_preserved': True, 'public_fact_text_preserved': True,
        'natural_visible_names': True, 'private_fields_not_queried': True,
        'caller_state_unchanged': True, 'real_model_calls': 0})


def test_known_cross_room_material_gets_public_fallback_without_hidden_lookup():
    state, prior = stage_and_question()
    missing = state['clues'][1]
    state['objects'] = [obj for obj in state['objects'] if obj['object_id'] != missing['object_id']]
    before = copy.deepcopy(state)
    guarded = GuardedPublicState(state)
    guarded['hidden_name_map'] = {missing['object_id']: CANARY}
    context = public_context(guarded, prior['question'], [])
    projected = context['known_evidence'][1]
    assert projected['title'] == '第二份资料'
    assert projected['clue_id'] == missing['clue_id'] and projected['text'] == missing['text']
    assert projected['title'] in ' '.join(obj['description'] for obj in context['visible_objects'])
    assert missing['clue_id'] in context['allowed_clue_refs']
    assert CANARY not in json.dumps(context, ensure_ascii=False) and state == before


def test_overlapping_ids_and_eighteen_chinese_labels_preserve_machine_refs():
    state, _ = stage_and_question()
    state['objects'] = [
        {'object_id': 'visible_one', 'name': '甲资料', 'description': '公开材料。', 'actions': []},
        {'object_id': 'visible_ten', 'name': '乙资料', 'description': '公开材料。', 'actions': []},
        {'object_id': 'visible_puzzle', 'name': '当前装置',
         'description': '资料 C10 → 资料 C1；资料 C100；资料 C10_extra。', 'actions': []},
    ]
    state['clues'] = [{'clue_id': f'C{index}', 'object_id': 'visible_one' if index == 1 else 'visible_ten' if index == 10 else f'earlier_object_{index}',
        'title': f'资料 C{index}', 'text': '已发现的公开资料。'} for index in range(1, 19)]
    state['observed_object_ids'] = ['visible_one', 'visible_ten', 'visible_puzzle']
    before = copy.deepcopy(state)
    context = public_context(state, '请解释一个公开的局部关系。', [])
    evidence = context['known_evidence']
    assert len({clue['title'] for clue in evidence}) == 18
    assert all(not re.search(r'\d', clue['title']) for clue in evidence)
    assert evidence[0]['title'] == '第一份资料（甲资料）'
    assert evidence[9]['title'] == '第十份资料（乙资料）'
    assert evidence[17]['title'] == '第十八份资料'
    expected = '第十份资料（乙资料） → 第一份资料（甲资料）；资料 C100；资料 C10_extra。'
    assert context['visible_objects'][2]['description'] == expected
    assert context['allowed_clue_refs'] == [f'C{index}' for index in range(1, 19)]
    reply = {'answer': '第十八份资料已经在笔记中，可以先按公开说明核对材料。', 'clue_refs': ['C18']}
    assert validate_reply(state, reply)['clue_refs'] == ['C18']
    assert state == before
    observed_output('round2-alias-boundaries.json', {'known_material_count': 18,
        'unique_chinese_labels': 18, 'machine_refs_complete': True,
        'C1_C10_exact_boundary': True, 'unknown_longer_ids_untouched': True,
        'fallback_prose_passes_unchanged_validator': True, 'real_model_calls': 0})


def test_classic_public_evidence_and_descriptions_remain_unchanged():
    from backend.app.domain import graybox_rules
    private = graybox_rules.initial_state()
    private, _ = graybox_rules.apply_action(private, 'inspect', {'object_id': 'r1_clock'})
    state = graybox_rules.visible_state('synthetic_classic_context', private)
    state['mode'] = 'classic'
    before = copy.deepcopy(state)
    context = public_context(state, '当前可以核对哪份公开资料？', [])
    assert state['level_version'] == '3.4.0' and state['clues']
    assert context['known_evidence'] == [{key: clue[key] for key in ('clue_id', 'title', 'text') if key in clue} for clue in state['clues']]
    assert [obj['description'] for obj in context['visible_objects']] == [obj.get('description', '') for obj in state['objects']]
    assert state == before


def synthetic_name_control(state):
    # Original paid reply stays blocked. Only this in-memory copy is synthetic.
    original = json.loads(capture('A1-provider-result.json')['content_redacted'])
    result = copy.deepcopy(original)
    names = {obj['object_id']: obj['name'] for obj in state['objects']}
    for clue in state['clues']:
        result['answer'] = result['answer'].replace(clue['clue_id'], names[clue['object_id']])
    return original, result


def test_original_real_reply_stays_rejected_and_synthetic_name_control_valid():
    state, prior = stage_and_question()
    original, synthetic = synthetic_name_control(state)
    with pytest.raises(ValueError, match='^COMPANION_CONTENT$'):
        validate_reply(state, original, prior['question'], recorded_actions(prior))
    assert validate_reply(state, synthetic, prior['question'], recorded_actions(prior)) == synthetic
    assert synthetic['clue_refs'] == original['clue_refs']
    assert json.loads(capture('A1-provider-result.json')['content_redacted']) == original


def test_production_companion_fake_httpx_natural_reply_full_payload_and_secret_boundary(tmp_path):
    state, prior = stage_and_question()
    before = copy.deepcopy(state)
    _, synthetic = synthetic_name_control(state)
    ledger = BudgetLedger(tmp_path / 'synthetic-round2-companion-budget.sqlite')
    seen = []
    bounds = []

    def handler(request):
        seen.append(request)
        assert request.url == httpx.URL('https://api.deepseek.com/chat/completions')
        assert request.headers['authorization'] == 'Bearer ' + CANARY
        assert CANARY.encode() not in request.content
        body = json.loads(request.content)
        assert body['max_tokens'] == 600 and body['response_format'] == {'type': 'json_object'}
        assert not {'tools', 'tool_choice'} & body.keys()
        bound = cost_units(len(request.content) * 4 + 8192, 600)
        bounds.append(bound)
        assert bound <= 50_000_000
        context = json.loads(body['messages'][-1]['content'])
        assert context['recent_history'] == prior['recent_history']
        assert context['room'] == {key: state['room'][key] for key in ('name', 'description')}
        assert {clue['clue_id']: clue['text'] for clue in context['known_evidence']} == {clue['clue_id']: clue['text'] for clue in state['clues']}
        assert context['allowed_clue_refs'] == synthetic['clue_refs']
        assert all('C_borrow' not in clue['title'] and 'C_order' not in clue['title'] for clue in context['known_evidence'])
        assert 'definition_hash' not in json.dumps(context) and 'answers' not in json.dumps(context)
        return httpx.Response(200, json=wire_body(json.dumps(synthetic, ensure_ascii=False)))

    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    service = CompanionService(lambda key: provider)
    result = asyncio.run(service.turn(public_state=state, message=prior['question'],
        history=recorded_actions(prior), api_key=CANARY, provider='deepseek', hint_level=2))
    assert len(seen) == 1 and result['status'] == 'completed'
    assert result['answer'] == synthetic['answer'] and result['clue_refs'] == synthetic['clue_refs']
    assert result['usage']['model_calls'] == 1 and state == before
    with sqlite3.connect(ledger.path) as db:
        assert db.execute('SELECT scope,state FROM budget_calls').fetchall() == [('v5_companion', 'settled')]
        assert CANARY not in '\n'.join(db.iterdump())
    observed_output('round2-companion-fake-httpx.json', {'synthetic_reply_only': True,
        'transport_sends': len(seen), 'whole_payload_upper_cost_units': bounds[0],
        'cap_units': 50_000_000, 'actual_captured_action_history_entries': 3,
        'synthetic_model_calls': result['usage']['model_calls'], 'real_model_calls': 0,
        'canonical_refs_and_public_fact_text_preserved': True,
        'caller_state_unchanged': True, 'credential_absent_from_payload_and_fake_ledger': True})
