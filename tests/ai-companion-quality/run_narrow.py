"""New epoch only: JSON-mode wire, strict rejection and procedural context."""
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import replace
import asyncio
import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests/ai-companion')]
RECORDS = []


def read(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


class ProviderWire(unittest.TestCase):
    def test_json_mode_only_optin_real_body_temporary_ledger(self):
        import httpx
        from backend.app.ai.budget import BudgetLedger
        from backend.app.ai.provider import CallLimits, DeepSeekConfig, DeepSeekProvider, ProviderError
        seen = []

        async def handler(request):
            seen.append({'url': str(request.url), 'body': json.loads(request.content)})
            return httpx.Response(200, json={'model': 'deepseek-flash',
                'choices': [{'message': {'role': 'assistant', 'content': '{"answer":"可以先解释眼前反馈。","clue_refs":[]}'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 2, 'completion_tokens': 1, 'total_tokens': 3, 'prompt_cache_hit_tokens': 0}})

        with tempfile.TemporaryDirectory(prefix='companion-quality-jsonmode-') as temp:
            ledger = BudgetLedger(path=Path(temp) / 'isolated.sqlite')
            provider = DeepSeekProvider(DeepSeekConfig('QA_SYNTHETIC_NEVER_REAL'), ledger, transport=httpx.MockTransport(handler))
            messages = [{'role': 'user', 'content': 'Return a JSON object for this isolated transport test.'}]
            asyncio.run(provider.complete(messages, [], CallLimits(100, 5), scope='qa-jsonmode'))
            asyncio.run(provider.complete(messages, [], CallLimits(100, 5, json_mode=True), scope='qa-jsonmode', tool_choice='none'))
            self.assertEqual(len(seen), 2)
            self.assertNotIn('response_format', seen[0]['body'])
            self.assertEqual(seen[1]['body']['response_format'], {'type': 'json_object'})
            self.assertTrue(all(r['url'] == 'https://api.deepseek.com/chat/completions' for r in seen))
            self.assertTrue(all(r['body']['model'] == 'deepseek-flash' for r in seen))
            snapshot = ledger.snapshot()
            with self.assertRaises(ProviderError) as error:
                asyncio.run(provider.complete(messages, [], CallLimits(100, 5, json_mode=1), scope='qa-jsonmode'))
            self.assertEqual(error.exception.code, 'INVALID_CALL_LIMITS')
            self.assertEqual(ledger.snapshot(), snapshot, 'Non-bool option rejected before reserve')
            self.assertEqual(len(seen), 2)
            self.assertEqual(snapshot['calls'], 2)
            self.assertEqual(snapshot['unknown_or_pending_calls'], 0)
            self.assertFalse(snapshot['frozen'])
            RECORDS.append({'check': 'real-provider-optin-request-body', 'intercepted_requests': seen,
                            'temporary_ledger': snapshot, 'external_network': False, 'canonical_ledger': False})


def make_http(original, base):
    class NarrowHTTP(base):
        def setUp(self):
            super().setUp()
            self.runtime_results = []
            from backend.app.ai.runtime import Runtime
            native = Runtime.run

            async def capture(runtime, start, callbacks):
                result = await native(runtime, start, callbacks)
                self.runtime_results.append(copy.deepcopy(result.data))
                return result

            intercept = patch.object(Runtime, 'run', capture)
            intercept.start()
            self.addCleanup(intercept.stop)

        def test_strict_raw_bad_json_and_direct_runtime_guards(self):
            first = 'evidence/integration/ai-companion-quality/paid/20261018T113949130750Z-real/'
            raw = [read(first + cid + '-provider.json')['raw_content'] for cid in ('Q01', 'Q03')]
            malformed = raw + ['{"answer":"解释到这里。","clue_refs":[],}',
                '{"answer":"解释到这里。","answer":"重复键。","clue_refs":[]}',
                '先说一句。{"answer":"解释到这里。","clue_refs":[]}',
                '```json\n{"answer":"解释到这里。","clue_refs":[]}\n```']
            for value in malformed:
                with self.subTest(raw=value):
                    before = self.state()
                    self.steps = [replace(original.reply(), content=value)]
                    data, _ = self.turn('请解释眼前的反馈。')
                    self.assertEqual(data['status'], 'stopped')
                    self.assertEqual(self.runtime_results[-1]['status'], 'stopped')
                    self.assertEqual(self.runtime_results[-1]['stop_reason'], 'MODEL_INVALID_OUTPUT')
                    self.assertEqual(self.state(), before)
                    self.assertTrue(self.calls[-1]['limits']['json_mode'])
                    RECORDS.append({'check': 'strict-format-direct-runtime', 'raw': value,
                                    'runtime': self.runtime_results[-1], 'final_status': data['status']})
            self.rejected('当前阶段为CODE_ACCEPTED。')
            self.assertEqual(self.runtime_results[-1]['status'], 'stopped')
            answer = '可以先从你已经注意到的一个物件说起，再指出其中让你疑惑的一点。'
            self.steps = [original.reply(answer)]
            self.accepted('我还不知道怎么整理观察。')
            self.rejected(answer, '刚才没明白，为什么要从那里开始？')
            self.assertEqual(self.runtime_results[-1]['status'], 'stopped')
            self.rejected('当前阶段为CODE_ACCEPTED。', store=True)
            self.rejected(answer, '刚才没明白，为什么要从那里开始？', store=True)
            RECORDS.append({'check': 'direct-runtime-and-forged-store-guards', 'runtime_rejections': 2, 'Store_rejections': 2})

        def test_logged_in_procedural_context_noise_removed_and_valid_natural_reply(self):
            for tool, args in original.ROUTE[:40]: self.action(tool, args)
            self.assertEqual(self.state()['device_states']['computer'], 'UNLOCKED')
            question = '我已经登录了，屏幕没再要求输入信息。现在是还要解密码，还是应该换一种观察方式？'
            answer = '登录已经通过，账号和密码这一关完成了。屏幕现在等的是读取封存记录，可以先区分“获准进入”和“看过内容”这两件事。'
            self.steps = [original.reply(answer)]
            data, _ = self.accepted(question)
            self.assertEqual(data['answer'], answer)
            self.assertEqual(self.runtime_results[-1]['answer'], answer)
            self.assertEqual(self.runtime_results[-1]['status'], 'no_suggestion')
            context = json.loads(next(m['content'] for m in self.calls[-1]['messages'] if m['role'] == 'user'))
            self.assertEqual(context['known_evidence'], [])
            self.assertEqual(context['allowed_clue_refs'], [])
            self.assertEqual(context['related_topics'], [])
            self.assertEqual({o['name'] for o in context['visible_object_catalog']}, {o['name'] for o in self.state()['objects']})
            details = json.dumps({k: v for k, v in context.items() if k != 'visible_object_catalog'}, ensure_ascii=False)
            for value in ('几代人', '日期和签字', 'USER使用', '格式为HHMM'):
                self.assertNotIn(value, details)
            self.assertIn('封存研究记录等待读取', details)
            self.assertTrue(self.calls[-1]['limits']['json_mode'])
            RECORDS.append({'check': 'logged-in-focused-wire-and-direct-runtime-success', 'context': context,
                            'runtime_answer': self.runtime_results[-1], 'final_answer': data['answer']})
    return NarrowHTTP


def main():
    cp = sys.argv[1]
    candidate = read(cp)
    source = candidate['source_sha256']
    before = {p: sha(p) for p in source}
    assert before == source
    preserved = dict(read('evidence/integration/ai-companion-quality/qa/preparation.json')['preserved_sha256'])
    for p in ('evidence/integration/ai-companion-quality/qa/20261018T113757609101Z-offline/run.json',
              'evidence/integration/ai-companion-quality/qa/20261018T113757609101Z-offline/checks.json',
              'evidence/integration/ai-companion-quality/qa/20261018T113757609101Z-offline/unittest.txt',
              'evidence/integration/ai-companion-quality/paid/20261018T113949130750Z-real/result.json',
              'evidence/integration/ai-companion-quality/qa/first-retest-review.json'):
        preserved[p] = sha(p)
    first = read('evidence/integration/ai-companion-quality/paid/20261018T113949130750Z-real/result.json')
    preserved.update(first['artifact_sha256'])
    assert all(sha(p) == h for p, h in preserved.items())
    from tests.api import test_ai_companion as original
    from tests.api import test_r1 as capture
    from fake_runtime import create_test_runtime
    spec = importlib.util.spec_from_file_location('quality_base', ROOT / 'tests/ai-companion-quality/run_regression.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    http = make_http(original, module.make_tests(original))
    suite = unittest.TestSuite([ProviderWire('test_json_mode_only_optin_real_body_temporary_ledger'),
        http('test_strict_raw_bad_json_and_direct_runtime_guards'),
        http('test_logged_in_procedural_context_noise_removed_and_valid_natural_reply')])
    folder = ROOT / 'evidence/integration/ai-companion-quality/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-fixed-narrow')
    folder.mkdir(parents=True)
    output = io.StringIO()
    with patch('backend.app.ai.runtime.create_request_runtime', create_test_runtime):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = {p: sha(p) for p in source}
    unchanged = all(sha(p) == h for p, h in preserved.items())
    code = 0 if result.wasSuccessful() and before == after and unchanged else 1
    def safe(v):
        if isinstance(v, dict): return {k: safe(x) for k, x in v.items()}
        if isinstance(v, (tuple, list)): return [safe(x) for x in v]
        if isinstance(v, str):
            for sentinel in capture.SECRETS | {original.KEY}: v = v.replace(sentinel, '[REDACTED]')
        return v
    (folder / 'unittest.txt').write_text(safe(output.getvalue()), encoding='utf-8')
    (folder / 'checks.json').write_text(json.dumps(safe(RECORDS + module.RECORDS), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'candidate': cp, 'candidate_sha256': sha(cp), 'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
               'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'source_sha256_before': before, 'source_sha256_after': after, 'preserved_sha256': preserved,
               'preserved_unchanged': unchanged, 'paid_calls': 0, 'canonical_budget_access': False, 'external_network': False,
               'qa_script_sha256': sha('tests/ai-companion-quality/run_narrow.py'), 'builds': 0, 'UI_runs': 0,
               'limitations': ['Synthetic transport verifies requested JSON mode, not actual model compliance/semantic quality.',
                   'First 15 methods and first three-call paid batch are preserved; this is a separate narrow source epoch.']}
    (folder / 'run.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(safe(output.getvalue()))
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}))
    return code


if __name__ == '__main__':
    sys.exit(main())
