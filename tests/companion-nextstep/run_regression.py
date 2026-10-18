"""Eight focused offline methods, gated by Main's frozen candidate; no real model grade."""
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import replace
from contextlib import closing
import copy
import hashlib
import importlib.util
import io
import json
import sqlite3
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests/ai-companion')]
RECORDS = []
REBUILD = [('inspect', {'object_id': oid}) for oid in
           ('r1_record', 'r1_microscope', 'sample_slide', 'r1_clock', 'r1_cabinet', 'r1_door')]
REBUILD += [('interact', {'target_id': 'r1_door'}), ('inspect', {'object_id': 'r1_plaque'}),
            ('move', {'destination_id': 'R2'}), ('inspect', {'object_id': 'r2_maintenance'})]


def read(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def make_tests(original, quality):
    class NextStepHTTP(quality):
        def setUp(self):
            super().setUp()
            from backend.app.ai.runtime import Runtime
            native = Runtime.run
            self.runtime_results = []

            async def capture(runtime, start, callbacks):
                result = await native(runtime, start, callbacks)
                self.runtime_results.append(copy.deepcopy(result.data))
                return result

            intercept = patch.object(Runtime, 'run', capture)
            intercept.start()
            self.addCleanup(intercept.stop)

        def rebuild(self):
            for tool, args in REBUILD:
                self.action(tool, args)
            state = self.state()
            self.assertEqual(state['room']['room_id'], 'R2')
            self.assertEqual(state['inventory'], [])
            self.assertEqual(state['puzzle_states']['microscope'], 'EMPTY')
            self.assertEqual(state['device_states']['powerbox'], 'CLOSED')
            self.assertEqual(state['device_states']['computer'], 'OFF')
            self.assertEqual({c['clue_id'] for c in state['clues']},
                             {'r1_record_clue', 'r1_clock_clue', 'r1_plaque_clue', 'r2_maintenance_clue'})
            return state

        def wire(self):
            return json.loads(next(m['content'] for m in self.calls[-1]['messages'] if m['role'] == 'user'))

        def fixed_trace(self, trace, code):
            errors = [item for item in trace if item.get('kind') == 'runtime_error']
            self.assertEqual(len(errors), 1)
            self.assertEqual({k: v for k, v in errors[0].items() if v is not None},
                             {'kind': 'runtime_error', 'code': code})
            self.assertEqual(set(errors[0]), {'kind', 'code', 'call_id', 'cost_upper_cny',
                                            'reported_model', 'requested_model', 'usage'})

        def test_actual_public_stage_nextstep_then_explanation_delivery(self):
            self.rebuild()
            answer = '电源箱现在仍关着，可以先观察它，了解箱体当前提供哪些操作。电脑还没有供电，暂时不需要猜登录信息。'
            self.steps = [original.reply(answer)]
            data, _ = self.accepted('下一步怎么做')
            self.assertEqual(data['answer'], answer)
            self.assertEqual(self.runtime_results[-1]['answer'], answer)
            context = self.wire()
            self.assertEqual(context['known_evidence'], [])
            self.assertEqual(context['allowed_clue_refs'], [])
            self.assertEqual(context['related_topics'], [])
            self.assertEqual({x['name'] for x in context['visible_object_catalog']},
                             {x['name'] for x in self.state()['objects']})
            follow = '先看电源箱，是因为电脑还没供电，而箱体当前尚未打开。观察它能确认眼前有哪些可用操作，之后再决定怎么继续。'
            self.steps = [original.reply(follow)]
            self.accepted('为什么先看这件东西')
            self.assertTrue(any(x.get('answer') == answer for x in self.wire()['recent_history']))
            self.assertEqual(self.runtime_results[-1]['answer'], follow)
            self.assertEqual(self.wire()['known_evidence'], [])
            self.assertEqual(self.wire()['allowed_clue_refs'], [])
            self.assertEqual(self.wire()['director']['available_action'], '观察')
            RECORDS.append({'check': 'reconstructed-public-stage-and-followup', 'first_context': context,
                            'followup_context': self.wire(), 'first_answer': answer, 'followup_answer': follow,
                            'actual_user_raw_reproduction': False})

        def test_clock_observation_allowed_but_password_and_unknown_times_rejected(self):
            self.action('inspect', {'object_id': 'r1_clock'})
            good = '墙钟显示21:17，这是你已经观察到的时间。可以先区分小时与分钟各自代表什么。'
            question = '墙钟显示的时间是什么意思？'
            for store in (False, True):
                with self.subTest(kind='known-clock', store=store):
                    before = self.state()
                    if store:
                        with self.forge(good, ['r1_clock_clue']):
                            data, _ = self.turn(question)
                        self.assertEqual(data['status'], 'no_suggestion')
                        self.assertEqual(self.state()['statistics']['hint_count'], before['statistics']['hint_count'] + 1)
                    else:
                        self.steps = [original.reply(good, ['r1_clock_clue'])]
                        data, _ = self.accepted(question)
                        self.assertEqual(self.runtime_results[-1]['status'], 'no_suggestion')
                    self.assertEqual(data['answer'], good)
                    self.assertIsNone(data['proposal'])
            bad = ['柜码是4217。', '完整密码是2117。', '登录密码就是21:17。',
                   '如果要登录，密码就是21:17。', '密码可以用这个时间21:17。',
                   '实验室的登录账号是LAB42。', '墙钟显示21:18。']
            for answer in bad:
                for store in (False, True):
                    with self.subTest(answer=answer, store=store):
                        self.rejected(answer, question, store=store)
                        if not store:
                            self.assertEqual(self.runtime_results[-1]['status'], 'stopped')
            # A fresh public state has not discovered the valid clock time yet.
            from backend.app.domain import graybox_rules as rules
            from backend.app.ai.companion import validate_companion_reply
            fresh = rules.visible_state('qa-unobserved-clock', rules.initial_state())
            with self.assertRaises(ValueError):
                validate_companion_reply(fresh, {'answer': good, 'clue_refs': []}, question, allowed_refs=[])
            RECORDS.append({'check': 'known-clock-vs-password-and-unknown-time', 'allowed': good,
                            'rejected': bad, 'unobserved_clock_rejected': True})

        def test_strict_delivery_and_store_failures_leave_all_state_unchanged(self):
            self.rebuild()
            for raw in ('先观察电源箱。', '{"answer":"先观察电源箱。","answer":"重复键。","clue_refs":[]}'):
                with self.subTest(raw=raw):
                    before = self.state()
                    self.steps = [replace(original.reply(), content=raw)]
                    data, _ = self.turn('下一步怎么做')
                    self.assertEqual(self.runtime_results[-1]['stop_reason'], 'MODEL_INVALID_OUTPUT')
                    self.assertEqual(data['status'], 'stopped')
                    self.assertIsNone(data['proposal'])
                    self.assertEqual(self.state(), before)
                    with closing(sqlite3.connect(self.db)) as db:
                        saved = json.loads(db.execute('SELECT trace_json FROM ai_turns WHERE turn_id=?',
                                                      (data['turn_id'],)).fetchone()[0])
                    self.fixed_trace(saved, 'COMPANION_FORMAT')
                    self.assertNotIn(raw, json.dumps(saved, ensure_ascii=False))
                    RECORDS.append({'check': 'persisted-fixed-rejection-category-no-raw', 'trace': saved})
            for answer, refs in [('我帮你打开电源箱。', []), ('当前状态是CLOSED。', []),
                                 ('先观察电源箱。', ['r2_maintenance_clue'])]:
                for store in (False, True):
                    with self.subTest(answer=answer, refs=refs, store=store):
                        self.rejected(answer, '下一步怎么做', refs, store=store)
                        if not store:
                            self.assertEqual(self.runtime_results[-1]['status'], 'stopped')
                            with closing(sqlite3.connect(self.db)) as db:
                                trace = json.loads(db.execute('SELECT trace_json FROM ai_turns ORDER BY rowid DESC LIMIT 1').fetchone()[0])
                            category = 'COMPANION_REFERENCE' if refs else 'COMPANION_CONTENT'
                            self.fixed_trace(trace, category)
                            self.assertNotIn(answer, json.dumps(trace, ensure_ascii=False))
                            RECORDS.append({'check': 'persisted-fixed-rejection-category-no-raw', 'trace': trace})
            RECORDS.append({'check': 'strict-runtime-and-separate-store-no-state-delta',
                            'full_visible_state_compared': True, 'paid_calls': 0})

    return NextStepHTTP


class PublicStages(unittest.TestCase):
    def test_dynamic_nextstep_and_explicit_relation_intent(self):
        from backend.app.domain import graybox_rules as rules
        from backend.app.ai.companion import build_companion_context, provider_companion_context
        route = read('evidence/documentation/gameplay-walkthrough-20261018/verification.json')['route_steps']
        state = rules.initial_state()
        stages = {0: ('实验记录', '观察'), 4: ('样本玻片', '观察'), 5: ('样本玻片', '拿'),
                  6: ('样本玻片', '显微镜'), 7: ('显微镜', '观察'), 10: ('储物柜', '拉开柜门'),
                  18: ('电源箱', '观察'), 20: ('电源箱', '打开'), 21: ('电源箱', '移开护板'),
                  22: ('保险丝', '电源箱'), 34: ('电源箱', '合上总闸'), 37: ('电脑', '启动'),
                  38: ('电脑', '继续启动'), 40: ('电脑', '读取')}
        records = []
        for count in range(41):
            if count:
                step = route[count - 1]
                state, _ = rules.apply_action(state, step['tool'], step['arguments'])
            if count not in stages:
                continue
            public = rules.visible_state('qa-nextstep-public-matrix', state)
            for question in ('下一步怎么做', '现在该做什么', '接下来怎么办'):
                wire = provider_companion_context(build_companion_context(public, question), public)
                guidance = json.dumps(wire.get('director'), ensure_ascii=False)
                with self.subTest(stage=count, question=question):
                    for word in stages[count]:
                        self.assertIn(word, guidance)
                    self.assertTrue({x['clue_id'] for x in wire['known_evidence']} <= set(wire['allowed_clue_refs']))
                    for private in ('4217', '2117', 'LAB42', 'ventilation', 'r1_sample_clue'):
                        self.assertNotIn(private, guidance)
                records.append({'stage': count, 'question': question, 'guidance': wire.get('director')})
        # An explicit factual relationship must retain its discovered sources.
        state = rules.initial_state()
        for tool, args in REBUILD:
            state, _ = rules.apply_action(state, tool, args)
        public = rules.visible_state('qa-explicit-relation', state)
        question = '墙钟与维护说明的时间格式有什么关系？'
        wire = provider_companion_context(build_companion_context(public, question), public)
        self.assertTrue({'r1_clock_clue', 'r2_maintenance_clue'} <= {x['clue_id'] for x in wire['known_evidence']})
        self.assertNotIn('activity', wire.get('director') or {})
        why = '为什么下一步要对照墙钟与维护说明的时间格式？'
        why_wire = provider_companion_context(build_companion_context(public, why), public)
        self.assertTrue({'r1_clock_clue', 'r2_maintenance_clue'} <= {x['clue_id'] for x in why_wire['known_evidence']})
        RECORDS.append({'check': 'public-matrix-and-relation-branch', 'matrix': records, 'relation_context': wire})


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: run_regression.py <Main frozen candidate JSON>; no network/paid calls')
    candidate_path = sys.argv[1]
    candidate = read(candidate_path)
    source = candidate['source_sha256']
    before = {p: sha(p) for p in source}
    assert before == source, 'Frozen source mismatch'
    prep = read('evidence/integration/companion-nextstep/qa/preparation.json')
    assert all(sha(p) == h for p, h in prep['preserved_sha256'].items()), 'Historical file mismatch'
    from tests.api import test_ai_companion as original
    from tests.api import test_hint_flow as preset
    from tests.api import test_play_ai_settings as legacy
    from tests.api import test_r1 as capture
    from fake_runtime import create_test_runtime
    prior = load('nextstep_prior_quality', 'tests/ai-companion-quality/run_regression.py')
    quality = prior.make_tests(original)
    current = make_tests(original, quality)
    suite = unittest.TestSuite([PublicStages('test_dynamic_nextstep_and_explicit_relation_intent')])
    for name in ('test_actual_public_stage_nextstep_then_explanation_delivery',
                 'test_clock_observation_allowed_but_password_and_unknown_times_rejected',
                 'test_strict_delivery_and_store_failures_leave_all_state_unchanged'):
        suite.addTest(current(name))
    suite.addTest(original.CompanionAcceptance('test_full_guess_confirmation_is_not_a_no_digits_bypass'))
    suite.addTest(quality('test_user_pass_words_are_clue_content_and_known_refs_remain_guarded'))
    suite.addTest(preset.HintFlowHTTP('test_initial_observation_valid_repeat_replay_stale_and_failed_provider'))
    suite.addTest(legacy.PlayAiSettings('test_real_selection_is_fixed_offline_redacted_and_request_is_idempotent'))
    folder = ROOT / 'evidence/integration/companion-nextstep/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-offline')
    folder.mkdir(parents=True)
    output = io.StringIO()
    started = datetime.now(timezone.utc)
    with patch('backend.app.ai.runtime.create_request_runtime', create_test_runtime):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = {p: sha(p) for p in source}
    preserved = all(sha(p) == h for p, h in prep['preserved_sha256'].items())
    code = 0 if result.wasSuccessful() and before == after and preserved else 1
    def safe(value):
        if isinstance(value, dict): return {k: safe(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)): return [safe(v) for v in value]
        if isinstance(value, str):
            for sentinel in capture.SECRETS | {original.KEY, legacy.KEY_A, legacy.KEY_B}:
                value = value.replace(sentinel, '[REDACTED]')
        return value
    (folder / 'unittest.txt').write_text(safe(output.getvalue()), encoding='utf-8')
    (folder / 'checks.json').write_text(json.dumps(safe(RECORDS + prior.RECORDS + original.RECORDS), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'candidate': candidate_path, 'candidate_file_sha256': sha(candidate_path),
               'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
               'started_at': started.isoformat(), 'ended_at': datetime.now(timezone.utc).isoformat(),
               'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'source_sha256_before': before, 'source_sha256_after': after, 'preserved_unchanged': preserved,
               'qa_script_sha256': sha('tests/companion-nextstep/run_regression.py'),
               'paid_calls': 0, 'external_network': False, 'canonical_budget_access': False,
               'builds': 0, 'UI_runs': 0,
               'limitations': ['Synthetic responses verify context and guard delivery, not real model quality.',
                               'Reconstructed public state is not a reproduction of unavailable user raw response.']}
    (folder / 'run.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(safe(output.getvalue()))
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'methods': result.testsRun,
                      'failures': len(result.failures), 'errors': len(result.errors)}))
    return code


if __name__ == '__main__':
    sys.exit(main())
