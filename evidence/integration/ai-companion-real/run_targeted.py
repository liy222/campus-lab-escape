"""One new paid sample on the fixed source, not a retry of the old request.

Reuses the sealed production-path executor with one explicit case and a stricter
CNY0.20 cap. Initial seven-call results are never overwritten or replayed.
"""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import hashlib
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('paid_playtest_executor', HERE / 'run_playtest.py')
executor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(executor)
TARGET = HERE / 'targeted'
TARGET.mkdir(exist_ok=True)
QUESTION = '输入后柜门没有自动打开。是不是只有储物柜能继续观察？请结合当前可见物件范围和柜子的状态解释下一步思路，不列密码，也不要替我操作。'


def prepare():
    from backend.app.ai.companion import SYSTEM, build_companion_context
    baseline = json.loads((HERE / '20261018T110144068872Z-real/result.json').read_text(encoding='utf-8'))
    assert baseline['actual_provider_dispatches'] == 7 and baseline['new_unknown_count'] == 0
    context = build_companion_context(executor.projection(10), QUESTION)
    assert context['allowed_clue_refs'] == []
    assert len(context['visible_object_catalog']) > 1
    body = executor.request_body([{'role': 'system', 'content': SYSTEM},
                                  {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}])
    plan = {'recorded_at': datetime.now(timezone.utc).isoformat(),
            'authorization': 'One additional targeted paid sample within original user request, total eight calls and <=CNY1.50.',
            'endpoint': 'https://api.deepseek.com/chat/completions', 'model': 'deepseek-flash',
            'baseline_source_sha256': executor.source_map(),
            'initial_result': 'evidence/integration/ai-companion-real/20261018T110144068872Z-real/result.json',
            'initial_result_sha256': hashlib.sha256((HERE / '20261018T110144068872Z-real/result.json').read_bytes()).hexdigest(),
            'executor_sha256': hashlib.sha256((HERE / 'run_playtest.py').read_bytes()).hexdigest(),
            'planned_real_calls': 1, 'maximum_real_calls': 1, 'targeted_limit_cny': 0.20,
            'overall_limit_cny': 1.50, 'overall_paid_calls': 8,
            'cases': [{'case_id': 'C08', 'kind': 'targeted_state_and_catalog', 'legal_route_prefix': 10,
                       'external_dispatch': True, 'body': body, 'offline_bound_cny': executor.bound(body)}],
            'limits': ['This sample tests the cabinet stage and public object scope; it cannot re-certify every initial case.',
                       'No automatic retries; new unknown/freeze or clear raw disclosure stops.']}
    executor.dump(TARGET / 'payload-preview.json', plan)
    print(json.dumps({'case': 'C08', 'calls': 1, 'reservation_upper_cny': executor.bound(body),
                      'preview': str(TARGET / 'payload-preview.json')}, ensure_ascii=False))


if __name__ == '__main__':
    if sys.argv[1:] == ['--prepare']:
        prepare()
    elif sys.argv[1:] == ['--execute']:
        plan = json.loads((TARGET / 'payload-preview.json').read_text(encoding='utf-8'))
        assert hashlib.sha256((HERE / 'run_playtest.py').read_bytes()).hexdigest() == plan['executor_sha256']
        initial = json.loads((HERE / '20261018T110144068872Z-real/result.json').read_text(encoding='utf-8'))
        assert initial['actual_provider_dispatches'] == 7 and initial['actual_charged_cny'] + 0.20 <= 1.50
        assert not list(TARGET.glob('*-real')), 'One targeted execution only; do not replay'
        executor.OUT = TARGET
        executor.LIMIT = 0.20
        executor.CASES = [('C08', 10, 'targeted_state_and_catalog', QUESTION)]
        sys.exit(executor.execute())
    else:
        raise SystemExit('Use --prepare (offline) or --execute (one paid sample)')
