"""Only rerun the new trace-schema method after correcting QA's null-field expectation."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import io
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('nextstep_focused_runner', ROOT / 'tests/companion-nextstep/run_regression.py')
focused = importlib.util.module_from_spec(spec)
spec.loader.exec_module(focused)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: run_narrow.py <Main frozen candidate>; only one new QA method')
    candidate_path = sys.argv[1]
    candidate = focused.read(candidate_path)
    source = candidate['source_sha256']
    before = {p: focused.sha(p) for p in source}
    assert before == source
    prep = focused.read('evidence/integration/companion-nextstep/qa/preparation.json')
    assert all(focused.sha(p) == h for p, h in prep['preserved_sha256'].items())
    from tests.api import test_ai_companion as original
    from tests.api import test_r1 as capture
    from fake_runtime import create_test_runtime
    prior = focused.load('nextstep_narrow_prior_quality', 'tests/ai-companion-quality/run_regression.py')
    current = focused.make_tests(original, prior.make_tests(original))
    suite = unittest.TestSuite([current('test_strict_delivery_and_store_failures_leave_all_state_unchanged')])
    folder = ROOT / 'evidence/integration/companion-nextstep/qa' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-trace-narrow')
    folder.mkdir(parents=True)
    output = io.StringIO()
    started = datetime.now(timezone.utc)
    with patch('backend.app.ai.runtime.create_request_runtime', create_test_runtime):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    after = {p: focused.sha(p) for p in source}
    preserved = all(focused.sha(p) == h for p, h in prep['preserved_sha256'].items())
    code = 0 if result.wasSuccessful() and before == after and preserved else 1
    def safe(v):
        if isinstance(v, dict): return {k: safe(x) for k, x in v.items()}
        if isinstance(v, (tuple, list)): return [safe(x) for x in v]
        if isinstance(v, str):
            for token in capture.SECRETS | {original.KEY}:
                v = v.replace(token, '[REDACTED]')
        return v
    (folder / 'unittest.txt').write_text(safe(output.getvalue()), encoding='utf-8')
    (folder / 'checks.json').write_text(json.dumps(safe(focused.RECORDS + prior.RECORDS), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'candidate': candidate_path, 'candidate_file_sha256': focused.sha(candidate_path),
               'command': [sys.executable, '-B', '-X', 'utf8', *sys.argv],
               'started_at': started.isoformat(), 'ended_at': datetime.now(timezone.utc).isoformat(),
               'exit_code': code, 'methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'source_sha256_before': before, 'source_sha256_after': after, 'preserved_unchanged': preserved,
               'qa_script_sha256': {p: focused.sha(p) for p in ('tests/companion-nextstep/run_regression.py', 'tests/companion-nextstep/run_narrow.py')},
               'reason': 'New QA expected an exact two-key trace while Store sanitization adds fixed null metadata fields; product unchanged.',
               'prior_run': 'evidence/integration/companion-nextstep/qa/20261018T153045999137Z-offline/run.json',
               'paid_calls': 0, 'external_network': False, 'canonical_budget_access': False, 'builds': 0, 'UI_runs': 0,
               'limitations': ['This is a one-method correction epoch, not a second full-green eight-method suite.']}
    (folder / 'run.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(safe(output.getvalue()))
    print(json.dumps({'evidence': str(folder), 'exit_code': code, 'methods': result.testsRun}))
    return code


if __name__ == '__main__':
    sys.exit(main())
