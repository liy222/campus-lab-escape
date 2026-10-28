"""Offline theme plumbing/metadata checks, not a semantic-quality guarantee.

Synthetic model replies, isolated temporary stores and a fake HTTP transport.
No real credentials, player data or project budget ledger are read.
"""
import asyncio
import json
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

from tests.v5.conftest import Actor, CANARY, rid
from tests.v5.test_blueprint_generation import synthetic_model_content
from tests.v5.test_generation import wire_body
from backend.app.ai.budget import BudgetLedger, cost_units
from backend.app.ai.provider import DeepSeekConfig, DeepSeekProvider, GenerationLimits
from backend.app.ai.v5 import GenerationService
from backend.app.api.v5 import COOKIE
from backend.app.domain import generation_content_v2 as content

THEME = '雨夜里的天文社旧活动室,寻找封存的观测记录'


def test_original_theme_and_original_model_text_survive_one_fake_transport(tmp_path, monkeypatch):
    # Text is deliberately supplied by this test, not authored/repaired by Host.
    bp = content.select_blueprint(3, 'hard', seed=3)
    raw = synthetic_model_content(bp)
    raw['title'] = '雨夜观测档案'
    raw['story'] = '雨声包围天文社旧活动室，封存的观测记录留在社团的旧资料中。'
    for index, room in enumerate(raw['rooms'].values()):
        room.update(name=f'观测记录室{index + 1}', description='雨水滑过旧窗，观测笔记静静留在室内。')
    for index, obj in enumerate(bp.objects):
        raw['objects'][obj.object_id]['name'] = f'观测物件{index + 1}'
    monkeypatch.setattr(content, 'select_blueprint', lambda *args, **kwargs: bp)
    sends = []
    ledger = BudgetLedger(tmp_path / 'fake-budget.sqlite')

    def handler(request):
        sends.append(request)
        payload = json.loads(request.content)
        user = json.loads(payload['messages'][1]['content'])
        assert user['theme'] == THEME
        assert user['blueprint'] == content.request_manifest(bp)
        assert payload['max_tokens'] == 6000
        assert payload['response_format'] == {'type': 'json_object'}
        assert not {'tools', 'tool_choice'} & payload.keys()
        assert CANARY.encode() not in request.content
        return httpx.Response(200, json=wire_body(json.dumps(raw, ensure_ascii=False)))

    provider = DeepSeekProvider(DeepSeekConfig(CANARY), ledger, transport=httpx.MockTransport(handler))
    draft = asyncio.run(GenerationService(lambda key: provider).generate(
        theme=THEME, room_count=3, difficulty='hard', api_key=CANARY, draft_schema={}))
    assert len(sends) == 1
    assert draft['title'] == raw['title'] and draft['story'] == raw['story']
    for room in draft['rooms']:
        original = raw['rooms'][room['room_id']]
        assert (room['name'], room['description']) == (original['name'], original['description'])
        for obj in room['objects']:
            assert obj['name'] == raw['objects'][obj['object_id']]['name']
    # Complete actual wire bytes, including system prompt/schema: one request,
    # not a matrix or a measured real provider token count.
    size = len(sends[0].content)
    bound = cost_units(size * 4 + 8192, 6000)
    limits = GenerationLimits()
    assert (limits.max_tokens, limits.timeout_seconds, limits.max_cost_units) == (6000, 60, 200_000_000)
    assert bound <= limits.max_cost_units
    print(f'THEME_PAYLOAD rooms=3 difficulty=hard seed=3 bytes={size} input_bound={size * 4 + 8192} upper_cost_units={bound} cap_units={limits.max_cost_units} paid_calls=0')


@pytest.mark.parametrize('extreme', [False, True], ids=['original-theme-with-secret-redaction', 'shortest-key-redaction-bound'])
def test_level_metadata_theme_is_owned_redacted_and_does_not_rewrite_definition(system, actor, extreme):
    app, generator = system
    cookie = actor.client.cookies.get(COOKIE)
    key = '~' if extreme else CANARY
    source = '~' * 2000 if extreme else THEME + ' ' + key + ' ' + cookie
    expected = '[REDACTED]' * 2000 if extreme else THEME + ' [REDACTED] [REDACTED]'
    response = actor.post('/level-generations', {
        'request_id': rid(), 'theme': source, 'room_count': 1, 'difficulty': 'easy',
    }, headers={'X-AI-Api-Key': key})
    assert response.status_code == 202
    job = actor.get('/level-generations/' + response.json()['data']['job']['job_id']).json()['data']['job']
    assert job['status'] == 'ready'
    assert generator.calls[0]['theme'] == expected
    lid = job['level_id']
    db = app.state.v5_database
    with db.transaction() as connection:
        before = tuple(connection.execute('SELECT definition_json,metadata_json FROM generated_levels WHERE level_id=?', (lid,)).fetchone())
    stored_metadata = json.loads(before[1])
    assert 'theme' not in stored_metadata
    schema = json.loads((Path(__file__).resolve().parents[2] / 'contracts/v2/api.schema.json').read_text(encoding='utf-8-sig'))
    # Existing metadata without the optional field remains a valid contract.
    Draft202012Validator({'$defs': schema['$defs'], '$ref': '#/$defs/level'}).validate(stored_metadata)
    public = actor.get('/levels/' + lid).json()['data']['level']
    assert public == {**stored_metadata, 'theme': expected}
    assert actor.get('/levels').json()['data']['levels'] == [public]
    assert cookie not in public['theme'] and key not in public['theme']
    if extreme:
        assert len(public['theme']) == 20000
    other = Actor(app).authenticate('theme_other')
    assert other.get('/levels').json()['data']['levels'] == []
    assert other.get('/levels/' + lid).status_code == 404
    with db.transaction() as connection:
        after = tuple(connection.execute('SELECT definition_json,metadata_json FROM generated_levels WHERE level_id=?', (lid,)).fetchone())
    assert after == before
    assert len(generator.calls) == 1  # Reading an old level never regenerates it.
    # An unrelated job cannot supply a theme to an otherwise owned level.
    with db.transaction() as connection:
        connection.execute('UPDATE level_generations SET level_id=? WHERE job_id=?', ('unrelated_level', job['job_id']))
    assert actor.get('/levels/' + lid).json()['data']['level'] == stored_metadata
