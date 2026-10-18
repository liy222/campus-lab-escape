"""Independent frozen-candidate offline quality boundaries; never a real-model grade."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests/ai-companion')]
RECORDS = []


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_tests(original):
    class QualityHTTP(original.CompanionAcceptance):
        def forge(self, answer, refs=()):
            from backend.app.ai.types import TurnResult, Version

            class Fake:
                async def run(fake, start, callbacks):
                    value = {'answer': answer, 'clue_refs': list(refs), 'status': 'no_suggestion', 'stop_reason': None,
                             'usage': {'provider': 'deepseek', 'model': 'qa-fake', 'input_tokens': 1,
                                       'output_tokens': 1, 'model_calls': 1, 'read_tool_calls': 0}}
                    return TurnResult(value, None, (), Version.from_state(start.visible_state))

            return patch('backend.app.ai.runtime.create_request_runtime', return_value=Fake())

        def rejected(self, answer, question='请结合当前状态解释，不要输出内部字段。', refs=(), *, store=False):
            before = self.state()
            self.steps = [original.reply(answer, refs)]
            if store:
                with self.forge(answer, refs):
                    data, _ = self.turn(question)
            else:
                data, _ = self.turn(question)
            self.assertEqual(data['status'], 'stopped')
            self.assertEqual(data['stop_reason'], 'MODEL_INVALID_OUTPUT')
            self.assertNotIn(answer, data['answer'])
            self.assertIsNone(data['proposal'])
            self.assertEqual(self.state(), before, 'Rejected prose must preserve revision/count/progress/level')
            RECORDS.append({'check': 'rejected-no-state-delta', 'boundary': 'Store' if store else 'Runtime',
                            'answer': answer, 'question': question, 'refs': list(refs), 'stop_reason': data['stop_reason']})

        def test_internal_codes_both_boundaries_without_overblocking_natural_state(self):
            for answer in ('柜子当前是CODE_ACCEPTED。', '当前阶段为STRIP_INSERTED。',
                           'public_progress中的check_done还是false。', 'visible_object_catalog显示墙钟。',
                           '当前director的focus是r1_cabinet。'):
                for store in (False, True):
                    with self.subTest(answer=answer, store=store):
                        self.rejected(answer, store=store)
            for tool, args in original.ROUTE[:10]:
                self.action(tool, args)
            self.assertEqual(self.state()['device_states']['cabinet'], 'CODE_ACCEPTED')
            answer = '数字锁已经接受输入，绿灯亮起，但柜门仍合着。可以先看柜门目前提供的操作。'
            self.steps = [original.reply(answer)]
            data, _ = self.accepted('为什么绿灯亮了但门仍没开？')
            self.assertEqual(data['answer'], answer)
            context = json.loads(next(m['content'] for m in self.calls[-1]['messages'] if m['role'] == 'user'))
            wire = json.dumps(context, ensure_ascii=False)
            for value in ('CODE_ACCEPTED', 'STRIP_INSERTED', '"r1_cabinet"', '"r1_clock"', '"object_id"', '"check_done"'):
                self.assertNotIn(value, wire)
            self.assertEqual({o['name'] for o in context['visible_object_catalog']}, {o['name'] for o in self.state()['objects']})
            RECORDS.append({'check': 'natural-public-state-allowed-and-wire-humanized', 'answer': answer, 'context': context})

        def test_exact_duplicate_both_boundaries_no_progress_and_restore_generation(self):
            answer = '可以先描述你注意到的一个物件，再指出你对它的哪一处感到疑惑。'
            self.steps = [original.reply(answer)]
            self.accepted('我现在不知道该问什么。')
            for store in (False, True):
                with self.subTest(store=store):
                    self.rejected(answer, '你刚才的意思能换个角度解释吗？', store=store)
            self.steps = [original.reply('刚才建议是为了先缩小疑问；你也可以选择墙钟，先说说哪一点最让你困惑。')]
            data, _ = self.accepted('我问的是为什么，不是要你重复同一句。')
            context = json.loads(next(m['content'] for m in self.calls[-1]['messages'] if m['role'] == 'user'))
            self.assertEqual(context['question'], '我问的是为什么，不是要你重复同一句。')
            self.assertTrue(any(h.get('answer') == answer for h in context['recent_history']))
            system = next(m['content'] for m in self.calls[-1]['messages'] if m['role'] == 'system')
            self.assertIn('追问', system)
            self.assertIn('解释', system)
            self.assertIn('照抄', system)
            RECORDS.append({'check': 'followup-context-policy', 'context': context,
                            'system': system})
            self.control('save')
            future = '保存后的未来对话独有句。先把注意到的细节分成确定和不确定两类。'
            self.steps = [original.reply(future)]
            self.accepted('存档之后的问题标记。')
            self.control('restore')
            self.reopen()
            self.steps = [original.reply(future)]
            self.accepted('恢复后重新开始讨论。')
            restored_context = json.loads(next(m['content'] for m in self.calls[-1]['messages'] if m['role'] == 'user'))
            self.assertEqual([x for x in restored_context['recent_history'] if x.get('kind') == 'dialogue'], [])
            RECORDS.append({'check': 'restore-generation-clears-duplicate-history', 'context': restored_context})
            long_answer = '先把已经看到的事实与还没确认的判断分开，再选一个疑问说清楚。' * 11
            self.assertGreater(len(long_answer), 300)
            self.assertLessEqual(len(long_answer), 360)
            self.steps = [original.reply(long_answer)]
            self.accepted('我想继续整理已经看到的信息。')
            for store in (False, True):
                with self.subTest(store=store, length=len(long_answer)):
                    self.rejected(long_answer, '刚才还是没明白，能具体解释吗？', store=store)

        def test_user_pass_words_are_clue_content_and_known_refs_remain_guarded(self):
            for tool, args in original.ROUTE:
                self.action(tool, args)
                if any(c['clue_id'] == 'r2_maintenance_clue' for c in self.state()['clues']):
                    break
            self.assertTrue(any(c['clue_id'] == 'r2_maintenance_clue' for c in self.state()['clues']))
            answer = '维护说明里的USER和PASS分别是在说明用户名与密码的填写格式。可以先分清两栏各自要求哪一种信息。'
            self.steps = [original.reply(answer, ['r2_maintenance_clue'])]
            data, _ = self.accepted('维护说明中USER/PASS这两栏格式是什么意思？')
            self.assertEqual(data['answer'], answer)
            for store in (False, True):
                with self.subTest(store=store):
                    self.rejected('可以先看看装置当前提供的操作。', '线路相邻两块的端口应该怎样理解？',
                                  ['r1_cabinet_clue'], store=store)
            RECORDS.append({'check': 'known-USER-PASS-prose-allowed', 'answer': answer, 'refs': data['clue_refs']})

    return QualityHTTP


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: run_regression.py <Main frozen candidate JSON>; no real provider access')
    candidate_path = sys.argv[1]
    candidate = read(candidate_path)
    source = candidate['source_sha256']
    before = {p: digest(p) for p in source}
    assert before == source, 'Frozen source mismatch'
    prep = read('evidence/integration/ai-companion-quality/qa/preparation.json')
    assert all(digest(p) == h for p, h in prep['preserved_sha256'].items()), 'Old QA/evidence mismatch'
    from tests.api import test_ai_companion as original
    from tests.api import test_hint_flow as preset
    from tests.api import test_play_ai_settings as legacy
    from tests.api import test_r1 as capture
    from fake_runtime import create_test_runtime
    prior = load_module('prior_quality_context', 'tests/ai-companion-real/run_regression.py')
    qa_class = make_tests(original)
    suite = unittest.TestSuite()
    for name in unittest.defaultTestLoader.getTestCaseNames(original.CompanionAcceptance):
        suite.addTest(qa_class(name))
    for name in ('test_internal_codes_both_boundaries_without_overblocking_natural_state',
                 'test_exact_duplicate_both_boundaries_no_progress_and_restore_generation',
                 'test_user_pass_words_are_clue_content_and_known_refs_remain_guarded'):
        suite.addTest(qa_class(name))
    suite.addTest(prior.QualityContext('test_catalog_procedural_emptyrefs_unknown_reject_and_normal_relations'))
    for name in prep['old_preset_methods']:
        suite.addTest(preset.HintFlowHTTP(name))
    for name in prep['old_legacy_methods']:
        suite.addTest(legacy.PlayAiSettings(name))
    folder = ROOT / 'evidence/integration/ai-companion-quality/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-offline')
    folder.mkdir(parents=True)
    output = io.StringIO()
    started = datetime.now(timezone.utc)
    with patch('backend.app.ai.runtime.create_request_runtime', create_test_runtime):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = {p: digest(p) for p in source}
    preserved = all(digest(p) == h for p, h in prep['preserved_sha256'].items())
    code = 0 if result.wasSuccessful() and before == after and preserved else 1

    def safe(v):
        if isinstance(v, dict): return {k: safe(x) for k, x in v.items()}
        if isinstance(v, (tuple, list)): return [safe(x) for x in v]
        if isinstance(v, str):
            for sentinel in capture.SECRETS | {original.KEY, legacy.KEY_A, legacy.KEY_B}:
                v = v.replace(sentinel, '[REDACTED]')
        return v

    (folder / 'unittest.txt').write_text(safe(output.getvalue()), encoding='utf-8')
    (folder / 'checks.json').write_text(json.dumps(safe(RECORDS + original.RECORDS + prior.RECORDS), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'candidate': candidate_path, 'candidate_file_sha256': digest(candidate_path), 'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
               'started_at': started.isoformat(), 'ended_at': datetime.now(timezone.utc).isoformat(), 'exit_code': code,
               'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'source_sha256_before': before, 'source_sha256_after': after, 'preserved_unchanged': preserved,
               'qa_script_sha256': digest('tests/ai-companion-quality/run_regression.py'), 'paid_calls': 0,
               'canonical_budget_access': False, 'builds': 0, 'UI_runs': 0,
               'fixture_adapter': None,
               'limitations': ['Offline pipeline/guard/context regression does not certify actual model relevance, tone or followup quality.',
                               'Free-prose validation is heuristic, not an exhaustive language safety proof.']}
    (folder / 'run.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(safe(output.getvalue()))
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}))
    return code


if __name__ == '__main__':
    sys.exit(main())
