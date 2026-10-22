"""Main-operated AI development check; synthetic transport and temporary ledger."""
from pathlib import Path
import asyncio
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
import httpx
from backend.app.ai.budget import BudgetLedger
from backend.app.ai.provider import CallLimits, GenerationLimits, DeepSeekConfig, DeepSeekProvider, ProviderError
from backend.app.ai.v5 import GenerationService, CompanionService, ServiceError
from backend.app.domain.generated import Draft, make_fixture, compile_level, GeneratedRules


async def run():
    checks = []
    with tempfile.TemporaryDirectory(prefix='campus-v5-ai-owner-') as temp:
        ledger = BudgetLedger(Path(temp) / 'fake-budget.sqlite')
        calls = []
        content = [json.dumps(make_fixture(1, 'easy'), ensure_ascii=False)]
        key = 'SYNTHETIC_ONLY_OWNER_CANARY'
        def handle(request):
            body = json.loads(request.content)
            assert request.url == httpx.URL('https://api.deepseek.com/chat/completions')
            assert request.headers['Authorization'] == 'Bearer ' + key
            assert key not in request.content.decode()
            assert body['response_format'] == {'type': 'json_object'}
            assert 'tools' not in body
            calls.append(body)
            return httpx.Response(200, json={'model': 'deepseek-flash', 'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': content.pop(0)}}],
                'usage': {'prompt_tokens': 100, 'completion_tokens': 30, 'total_tokens': 130, 'prompt_cache_hit_tokens': 0}})
        factory = lambda supplied: DeepSeekProvider(DeepSeekConfig(supplied), ledger, transport=httpx.MockTransport(handle))
        generated = await GenerationService(factory).generate(theme='校园档案 ' + key, room_count=1, difficulty='easy', api_key=key, draft_schema=Draft.model_json_schema())
        assert generated == make_fixture(1, 'easy') and calls[0]['max_tokens'] == 6000
        checks.append('generation: one synthetic dispatch, JSON6000, Key absent from content')
        for kwargs in ({'max_tokens': 1001}, {'timeout_seconds': 21}):
            try:
                CallLimits(**kwargs).validate()
            except ProviderError:
                pass
            else:
                raise AssertionError('legacy limit widened')
        count = len(calls)
        try:
            await factory(key).complete([{'role': 'user', 'content': 'json'}], [], GenerationLimits(), scope='game', tool_choice='none')
        except ProviderError:
            pass
        else:
            raise AssertionError('generation profile used in wrong scope')
        assert len(calls) == count
        checks.append('legacy 1000/20 unchanged; generation scope cannot be selected by old calls')
        compiled = compile_level(generated, 1, 'easy')
        rules = GeneratedRules(compiled)
        state = rules.visible_state('owner-test', rules.initial_state())
        companion = CompanionService(factory)
        local = await companion.turn(public_state=state, message='ignored', provider='mock', hint_level=2)
        assert local['usage']['model_calls'] == 0 and len(calls) == count
        content.append(json.dumps({'answer': '可以先点击眼前的资料，看看其中提供了哪些信息。', 'clue_refs': []}, ensure_ascii=False))
        answer = await companion.turn(public_state=state, message='下一步 ' + key, api_key=key, provider='deepseek')
        assert answer['usage']['model_calls'] == 1 and calls[-1]['max_tokens'] == 600
        checks.append('preset zero calls; companion public-only JSON600, real-prose pipeline via fake transport')
        refused = await companion.turn(public_state=state, message='密码1234对吗', api_key=key, provider='deepseek')
        assert refused['count_hint'] is False and refused['usage']['model_calls'] == 0
        checks.append('complete-guess request refused locally without dispatch')
        assert ledger.snapshot()['calls'] == 2
        return {'operator': 'Main', 'kind': 'development check, not independent QA', 'exit_code': 0, 'checks': checks,
                'actual_network_calls': 0, 'synthetic_transport_calls': len(calls), 'canonical_budget_opened': False,
                'limitations': ['Synthetic protocol/guard checks do not certify real model quality.']}


if __name__ == '__main__':
    result = asyncio.run(run())
    destination = Path(__file__).with_name('result.json')
    if destination.exists():
        raise SystemExit('Refusing to overwrite existing owner evidence')
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
