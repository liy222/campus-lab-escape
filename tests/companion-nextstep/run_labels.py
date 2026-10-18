"""Two label-only methods after the paid epoch; no real model retest."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import importlib.util
import io
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('nextstep_label_base', ROOT / 'tests/companion-nextstep/run_regression.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
RECORDS = []


class Labels(unittest.TestCase):
    def test_wire_click_labels_and_original_public_affordances_unchanged(self):
        from backend.app.domain import graybox_rules as rules
        from backend.app.ai.companion import SYSTEM, build_companion_context, provider_companion_context
        self.assertIn('直接点击', SYSTEM)
        self.assertIn('观察按钮', SYSTEM)
        self.assertIn('目镜', SYSTEM)
        route = base.read('evidence/documentation/gameplay-walkthrough-20261018/verification.json')['route_steps']
        for prefix in (0, 5, 10, 20):
            state = rules.initial_state()
            for step in route[:prefix]:
                state, _ = rules.apply_action(state, step['tool'], step['arguments'])
            public = rules.visible_state('qa-label-only', state)
            before = copy.deepcopy(public)
            context = build_companion_context(public, '下一步怎么做')
            wire = provider_companion_context(context, public)
            original_objects = {obj['name']: obj for obj in public['objects']}
            for obj in wire['visible_objects']:
                expected = ['点击' + obj['name'] + '查看' if action['tool'] == 'inspect' else action['label']
                            for action in original_objects[obj['name']]['actions']]
                self.assertEqual(obj['actions'], expected)
            goal = context['director']
            if goal and goal['kind'] == 'observe':
                name = next(obj['name'] for obj in public['objects'] if obj['object_id'] == goal['focus']['object_id'])
                self.assertEqual(wire['director']['available_action'], '点击' + name + '查看')
            self.assertEqual(public, before, 'Model prose conversion must not mutate API affordances')
            self.assertTrue(all(next(a for a in obj['actions'] if a['tool'] == 'inspect')['label'] == '观察'
                                for obj in public['objects']))
            RECORDS.append({'check': 'label-only-wire-public-api-unchanged', 'route_prefix': prefix,
                            'director': wire['director'], 'visible_objects': wire['visible_objects']})


def make_http(original, current):
    class LabelHTTP(current):
        def test_actual_stage_click_object_reply_through_runtime_and_store(self):
            self.rebuild()
            answer = '可以直接点击电源箱查看，先确认它的外观和当前提供的操作，再决定怎样继续。'
            self.steps = [original.reply(answer)]
            data, _ = self.accepted('下一步怎么做')
            self.assertEqual(data['answer'], answer)
            self.assertEqual(self.runtime_results[-1]['answer'], answer)
            self.assertEqual(self.runtime_results[-1]['status'], 'no_suggestion')
            wire = self.wire()
            self.assertEqual(wire['director']['available_action'], '点击电源箱查看')
            self.assertEqual(wire['visible_objects'][0]['actions'], ['点击电源箱查看'])
            self.assertEqual(wire['known_evidence'], [])
            self.assertEqual(wire['allowed_clue_refs'], [])
            self.assertIsNone(data['proposal'])
            self.assertEqual(data['usage']['read_tool_calls'], 0)
            RECORDS.append({'check': 'synthetic-click-prose-delivery', 'answer': answer,
                            'context': wire, 'actual_model_retest': False})
    return LabelHTTP


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: run_labels.py <Main final label candidate>; no paid call')
    candidate_path = sys.argv[1]
    candidate = base.read(candidate_path)
    previous = base.read('evidence/integration/companion-nextstep/candidate.json')
    source = candidate['source_sha256']
    before = {p: base.sha(p) for p in source}
    assert before == source
    assert set(source) == set(previous['source_sha256'])
    assert [p for p in source if source[p] != previous['source_sha256'][p]] == ['backend/app/ai/companion.py']
    prep = base.read('evidence/integration/companion-nextstep/qa/preparation.json')
    assert all(base.sha(p) == h for p, h in prep['preserved_sha256'].items())
    offline = base.read('evidence/integration/companion-nextstep/qa/offline-review.json')
    historic_scripts = {p: h for p, h in offline['qa_source_sha256'].items() if p.endswith('.py')}
    assert all(base.sha(p) == h for p, h in historic_scripts.items())
    paid = base.read('evidence/integration/companion-nextstep/qa/real-review.json')
    assert all(base.sha(p) == h for p, h in paid['artifact_sha256'].items())
    from tests.api import test_ai_companion as original
    from tests.api import test_r1 as capture
    from fake_runtime import create_test_runtime
    prior = base.load('label_prior_quality', 'tests/ai-companion-quality/run_regression.py')
    current = base.make_tests(original, prior.make_tests(original))
    http = make_http(original, current)
    suite = unittest.TestSuite([Labels('test_wire_click_labels_and_original_public_affordances_unchanged'),
                               http('test_actual_stage_click_object_reply_through_runtime_and_store')])
    folder = ROOT / 'evidence/integration/companion-nextstep/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-labels')
    folder.mkdir(parents=True)
    output = io.StringIO()
    started = datetime.now(timezone.utc)
    with patch('backend.app.ai.runtime.create_request_runtime', create_test_runtime):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = {p: base.sha(p) for p in source}
    preserved = all(base.sha(p) == h for p, h in prep['preserved_sha256'].items())
    code = 0 if result.wasSuccessful() and before == after and preserved else 1
    def safe(v):
        if isinstance(v, dict): return {k: safe(x) for k, x in v.items()}
        if isinstance(v, (tuple, list)): return [safe(x) for x in v]
        if isinstance(v, str):
            for token in capture.SECRETS | {original.KEY}:
                v = v.replace(token, '[REDACTED]')
        return v
    (folder / 'unittest.txt').write_text(safe(output.getvalue()), encoding='utf-8')
    (folder / 'checks.json').write_text(json.dumps(safe(RECORDS), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'candidate': candidate_path, 'candidate_file_sha256': base.sha(candidate_path),
               'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
               'started_at': started.isoformat(), 'ended_at': datetime.now(timezone.utc).isoformat(),
               'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'source_sha256_before': before, 'source_sha256_after': after, 'old219_unchanged': preserved,
               'prior_QA_scripts_unchanged': historic_scripts,
               'qa_script_sha256': base.sha('tests/companion-nextstep/run_labels.py'),
               'paid_artifacts_unchanged': True, 'paid_calls': 0, 'external_network': False,
               'canonical_budget_access': False, 'builds': 0, 'UI_runs': 0,
               'limitations': ['Final wire/prompt label tweak has no real-model retest.',
                               'Old eight-method/one-method runs and two paid samples belong to preceding source epoch.']}
    (folder / 'run.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(safe(output.getvalue()))
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'methods': result.testsRun}))
    return code


if __name__ == '__main__':
    sys.exit(main())
